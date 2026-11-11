"""Атомарное решение задачи командного архива: игры и вердикт в одной операции журнала."""
import json
import uuid

from db import edit, store


class BatchConnection:
    """Вложенные операции edit записывают журнал, внешний вызов фиксирует всё вместе."""
    def __init__(self, connection):
        self.connection = connection

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def commit(self):
        pass


def apply(con, args, editor):
    task_id = args.get('task_id')
    decision = args.get('decision')
    note = str(args.get('note') or '').strip()
    if decision not in ('save', 'confirm', 'reject') or not note:
        raise edit.EditError('Укажите решение и обоснование вердикта')
    rows = args.get('games') or []
    if not isinstance(rows, list) or len(rows) > 30:
        raise edit.EditError('Один отчёт содержит не более 30 игр')
    if decision == 'save' and not rows:
        raise edit.EditError('Добавьте хотя бы одну игру либо выберите подтверждение без изменений')
    if decision != 'save' and rows:
        raise edit.EditError('Для закрытия без изменения данных список игр должен быть пуст')
    pg = hasattr(con, '_raw')
    con.execute('BEGIN' if pg else 'BEGIN IMMEDIATE')
    try:
        task = con.execute('select * from incoming where id = ?' + (' FOR UPDATE' if pg else ''), (task_id,)).fetchone()
        if not task or task['batch'] != 'team_archive_review':
            raise edit.EditError('Задача командного архива не найдена')
        if task['verdict'] != 'conflict':
            raise edit.EditError('Задача уже решена; обновите очередь')
        payload = store.parse_json(task['payload'], default={})
        batch = BatchConnection(con)
        journal_ids = []
        results = []
        match_ids = []
        seen_ids = set()
        for game_index, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                raise edit.EditError('Каждая игра должна быть объектом')
            sides = row.get('sides') or []
            if len(sides) != 2 or any(len(edit.canonical_roster(s)) != 2 for s in sides):
                raise edit.EditError('Укажите двух игроков для каждой стороны 2×2')
            rosters = [edit.canonical_roster(s) for s in sides]
            for roster in rosters:
                for index, nick in enumerate(roster):
                    found = con.execute("select nick from players where kind='player' "
                                        "and fold(nick)=fold(?)", (nick,)).fetchone()
                    if not found:
                        raise edit.EditError(f'Игрок «{nick}» не найден. Выберите ник из подсказок')
                    roster[index] = found[0]
            if len(set(rosters[0] + rosters[1])) != 4:
                raise edit.EditError('В игре 2×2 должны участвовать четыре разных игрока')
            sides = [' & '.join(roster) for roster in rosters]
            if set(rosters[0]) & set(rosters[1]):
                raise edit.EditError('Игрок не может играть против самого себя')
            scores = [row.get('s1'), row.get('s2')]
            if any(type(v) is not int or v < 0 or v > 99 for v in scores):
                raise edit.EditError('Счёт игры — целые числа от 0 до 99')
            phase = row.get('phase', 'regular')
            if phase not in ('regular','overtime','penalties'):
                raise edit.EditError('Неизвестная фаза игры')
            shown = f'{scores[0]}:{scores[1]}'
            outcomes = ['win','loss'] if scores[0]>scores[1] else ['loss','win'] if scores[0]<scores[1] else ['draw','draw']
            if scores[0] == scores[1] and phase == 'penalties':
                pk = [row.get('pk1'), row.get('pk2')]
                if any(type(v) is not int or v < 0 or v > 99 for v in pk) or pk[0] == pk[1]:
                    raise edit.EditError('При равном счёте укажите разные результаты буллитов')
                shown += f' (ПК {pk[0]}:{pk[1]})'
                outcomes = ['win','loss'] if pk[0]>pk[1] else ['loss','win']
            if scores[0] == scores[1] and phase == 'overtime':
                raise edit.EditError('Победа в овертайме требует неравного счёта')
            spec = {**row, 'sides':sides, 'note':shown,'source_text':payload.get('как_выглядит',''),
                    'links':[['vk_post',url] for url in payload.get('ссылки',[]) if str(url).startswith(('http://','https://'))]}
            mid = row.get('match_id')
            if mid:
                if type(mid) is not int or mid in seen_ids:
                    raise edit.EditError('Некорректный или повторный номер игры')
                seen_ids.add(mid)
                found = con.execute('select m.source_ref,d.doc_key from matches m left join tournament_docs d on d.id=m.doc_id where m.id=?',(mid,)).fetchone()
                prefix = str(payload.get('match_ref') or '').rsplit(':line-',1)[0]
                if not found or not (mid == task['matched_match_id'] or (prefix and str(found['source_ref'] or '').startswith(prefix+':line-'))):
                    raise edit.EditError('Эта игра не относится к выбранной задаче')
                if row.get('doc_key') and row['doc_key'] != found['doc_key']:
                    raise edit.EditError('Для существующей игры нельзя менять турнир этим решением')
                results.append(edit.set_players(batch, mid, sides, editor))
                results.append(edit.set_score(batch, mid, *scores, editor))
                results.append(edit.set_place(batch, mid, editor, row.get('tour',''),row.get('league',''),row.get('stage','')))
                results.append(edit.set_source(batch, mid, editor, shown, spec['links']))
            else:
                if not row.get('doc_key'):
                    raise edit.EditError('Выберите турнир для новой игры')
                spec['tour'] = str(spec.get('tour') or 'Отчёт') + f' · Игра {game_index}'
                result = edit.add_match(batch, spec, editor)
                results.append(result); mid=result['match_id']
            changes=[]
            for current in edit.pair_ids(con,mid):
                for side, outcome in zip(edit.sides_of(con,current),outcomes):
                    if side['outcome'] != outcome:
                        changes.append(('match_sides',side['id'],'outcome',side['outcome'],outcome))
            journal_ids.extend(edit.journal(batch,editor,changes,edit.pair_ids(con,mid),uuid.uuid4().hex[:12]))
            results.append(edit.set_phase(batch,mid,editor,phase,bool(row.get('playoff'))))
            match_ids.append(mid)
        updated = {**payload,'вердикт_редактора':{'decision':decision,'note':note,'editor':editor,'match_ids':match_ids}}
        changes=[('incoming',task_id,'payload',task['payload'],json.dumps(updated,ensure_ascii=False)),
                 ('incoming',task_id,'verdict',task['verdict'],'rejected' if decision=='reject' else 'same')]
        op=uuid.uuid4().hex[:12]
        journal_ids.extend(edit.journal(batch,editor,changes,[],op))
        journal_ids.extend(entry for result in results for entry in result.get('journal', []))
        placeholders = ','.join('?' for _ in journal_ids)
        con.execute(f'update corrections set op = ? where id in ({placeholders})', (op,*journal_ids))
        journal=[r[0] for r in con.execute('select id from corrections where op = ? order by id',(op,))]
        con.commit()
        return {'operation':'review-task','match_id':match_ids[0] if match_ids else task['matched_match_id'],
                'changes':changes,'journal':journal,'op':op,'linked':match_ids,'created':match_ids}
    except Exception:
        con.rollback()
        raise
