"""Инварианты единой базы: то, что сборка обязана проверить до генерации страниц.

Каждая проверка — запрос, который должен вернуть ноль строк. Плюс сверка с читателем
(`db.catalog`): сколько матчей витрина реально отдаёт, и чтобы счётчики не расходились
с тем, что лежит в таблицах. Запуск: `python db/validate.py` (ненулевой код выхода = проблемы).
"""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "nst.db"

# (что проверяем, запрос: должен вернуть пустоту, максимум строк в отчёте)
CHECKS = [
    ("матч без сторон", """
        select m.id from matches m
        left join match_sides s on s.match_id = m.id
        group by m.id having count(s.id) = 0"""),
    ("стороны пронумерованы не подряд (0..n-1)", """
        select m.id from matches m join match_sides s on s.match_id = m.id
        group by m.id
        having min(s.side_index) <> 0 or max(s.side_index) <> count(s.id) - 1"""),
    ("исход не согласован со счётом", """
        select m.id from matches m
        join match_sides a on a.match_id = m.id and a.side_index = 0
        join match_sides b on b.match_id = m.id and b.side_index = 1
        where a.outcome <> 'none' and b.outcome <> 'none' and a.score is not null and b.score is not null
          and not (a.score = b.score and m.phase <> 'regular')
          and case when a.score > b.score then 'win'
                   when a.score < b.score then 'loss' else 'draw' end <> a.outcome"""),
    # Нога может кончиться вничью по голам и всё равно иметь победителя: её решает серия.
    # Равный счёт обязывает исход быть либо честной ничьей, либо парой победа/поражение.
    ("равный счёт в не regular-этапе с левым исходом", """
        select m.id from matches m
        join match_sides a on a.match_id = m.id and a.side_index = 0
        join match_sides b on b.match_id = m.id and b.side_index = 1
        where m.phase <> 'regular' and a.score is not null and a.score = b.score
          and not ((a.outcome = 'draw' and b.outcome = 'draw')
                or (a.outcome = 'win' and b.outcome = 'loss')
                or (a.outcome = 'loss' and b.outcome = 'win'))"""),
    ("ничья помечена как победа (или наоборот)", """
        select m.id from matches m
        join match_sides a on a.match_id = m.id and a.side_index = 0
        join match_sides b on b.match_id = m.id and b.side_index = 1
        where (a.outcome = 'draw') <> (b.outcome = 'draw')
           or (a.outcome = 'draw' and a.score <> b.score)"""),
    ("технический матч без снявшейся стороны", """
        select m.id from matches m join match_sides s on s.match_id = m.id
        where m.status = 'technical'
        -- ТП быват двух видов: снялась одна сторона (у неё `none`, у второй `win`) и «ТП обоим»
        -- (встреча есть в источнике, но в сводку она не легла — тогда `none` у обеих).
        group by m.id having sum(s.outcome = 'none') not in (1, 2)
                          or sum(s.outcome = 'win') <> 2 - sum(s.outcome = 'none')"""),
    ("цепочка скрытий (спрятанная строка прячет другую)", """
        select m.id from matches m join matches t on t.id = m.hidden_by
        where t.hidden_by is not null"""),
    ("hidden_by указывает на другой срез", """
        select m.id from matches m join matches t on t.id = m.hidden_by
        where t.row_set <> m.row_set"""),
    ("source_ref повторяется", """
        select source_ref from matches where source_ref is not null
        group by source_ref having count(*) > 1"""),
    ("строка пула без source_ref — импорт не идемпотентен", """
        select id from matches where row_set = 'pool' and source_ref is null"""),
    ("дата в будущем", """
        select id from matches where date(played_on) > date('now')"""),
    ("дата раньше 2000 года (год вместо unix-секунд?)", """
        select id from matches where date(played_on) < '2000-01-01'"""),
    ("точность даты не согласована с самой датой", """
        select id from matches where (date_precision = 'exact' and played_on is null)
          or (date_precision <> 'exact' and played_on is not null)"""),
    ("стадия принадлежит другому турниру", """
        select m.id from matches m join stages s on s.id = m.stage_id
        join tournaments t on t.id = m.tournament_id
        where s.tournament_id <> m.tournament_id or s.tournament_id is null"""),
    ("один и тот же игрок в обеих сторонах матча", """
        select s1.match_id from match_sides s1
        join match_sides s2 on s2.match_id = s1.match_id and s2.side_index > s1.side_index
        join side_players p1 on p1.side_id = s1.id
        join side_players p2 on p2.side_id = s2.id and p2.player_id = p1.player_id"""),
    ("ник игрока повторяется", """
        select nick from players group by nick having count(*) > 1"""),
    ("сторона без игрока и без подписи", """
        select s.id from match_sides s
        left join side_players sp on sp.side_id = s.id
        where sp.side_id is null and (s.label is null or s.label = '')"""),
    ("матч спецтурнира или каталога без счёта и без пометки", """
        select m.id from matches m
        join match_sides s on s.match_id = m.id and s.side_index = 0
        where m.row_set in ('pool', 'catalog') and s.score is null"""),
    ("игра турнира не привязана к документу — рамка её не покажет", """
        select id from matches where row_set in ('special', 'team') and doc_id is null"""),
    ("пул или каталог приписан документу турнира", """
        select id from matches where row_set in ('pool', 'catalog') and doc_id is not null"""),
    ("срез строки не совпадает с видом её документа", """
        select m.id from matches m join tournament_docs d on d.id = m.doc_id
        where m.row_set <> d.kind"""),
    ("строка документа без сторон 0 и 1 — читатель потеряет игру", """
        select m.id from matches m
        join tournament_docs d on d.id = m.doc_id
        left join match_sides s0 on s0.match_id = m.id and s0.side_index = 0
        left join match_sides s1 on s1.match_id = m.id and s1.side_index = 1
        where s0.id is null or s1.id is null"""),
]

# Витрина теряет вкладку молча, если соответствующий срез документов пуст: ни одного документа
# не бывает, а «документ без игр» — норма (лидер-рейтинг, чемпионаты без плей-офф).
MIN_DOCS = {"special": 1, "team": 1}


def doc_counts(con):
    return dict(con.execute("select kind, count(*) from tournament_docs group by kind"))


def _year_problem(elo, match):
    """None — год партии определён; иначе причина, по которой движок рейтинга её не возьмёт."""
    try:
        elo.rating_year(match)
    except elo.EloError as error:
        return str(error)
    return None


def run(path=DB_PATH):
    con = sqlite3.connect(path)
    problems = []
    for name, sql in CHECKS:
        try:
            bad = con.execute(sql).fetchall()
        except sqlite3.Error as error:
            problems.append((f"{name} — запрос не выполнился", [str(error)]))
            continue
        if bad:
            problems.append((name, [row[0] for row in bad[:8]]))

    from db.catalog import catalog_from_db
    from db.pool import pool_from_db
    # Читатели вызываются с путём: валидатор часто гоняют на копии базы (предпросмотр правки,
    # тесты), и молча сверять её с живой базой — значит не заметить ровно то, что ищут.
    served = len(catalog_from_db(path))
    pool_rows = len(pool_from_db(path))
    if served == 0:
        problems.append(("витрина не получает ни одного матча", []))
    if pool_rows == 0:
        problems.append(("рейтинговый пул пуст", []))

    # Порядок партий решает, чей Elo какой: строка без года встала бы в ряд наугад, и сборка
    # мастер-таблицы упала бы на ней уже после валидатора. Проверка здесь — чтобы редактор
    # получил внятный отказ до генерации страниц.
    from portal import elo

    undated = [row["id"] for row in pool_from_db(path)
               if _year_problem(elo, row) is not None]
    if undated:
        problems.append(("рейтинговая партия без года — порядок Elo не определить", undated))
    docs = doc_counts(con)
    for kind, least in MIN_DOCS.items():
        if docs.get(kind, 0) < least:
            problems.append((f"документов турнира «{kind}» меньше {least} — вкладка пуста", []))

    # Каноник не должен сам вести в другой каноник: если алиас переименовывает уже заведённого
    # игрока, база хранит два имени одного человека, и карточка разъезжается. Так «Sokol» из
    # лиги чуть не уехал в «ZaSashku» из молодёжки — написание с заглавной теперь прописан явно.
    from portal.names import clean_alias

    renamed = [row[0] for row in con.execute("select nick from players") if clean_alias(row[0]) != row[0]]
    if renamed:
        problems.append(("алиас переименовывает уже заведённого игрока", renamed[:8]))

    total = con.execute("select count(*) from matches").fetchone()[0]
    dupes = con.execute("select count(*) from matches where duplicate_of is not null").fetchone()[0]
    hidden = con.execute("select count(*) from matches where hidden_by is not null").fetchone()[0]
    doc_games = con.execute("select count(*) from matches where doc_id is not null").fetchone()[0]
    print(f"база {path.name}: строк {total}, дублей записано {dupes}, скрыто от витрины {hidden}, "
          f"матчей витрины {served}, пул {pool_rows}")
    print(f"документов турнира {sum(docs.values())} "
          f"({', '.join(f'{kind}: {count}' for kind, count in sorted(docs.items()))}), "
          f"игр привязано к ним {doc_games}")

    if problems:
        print(f"FAIL: проблемных проверок {len(problems)}")
        for name, ids in problems:
            print(f"  ✗ {name}: {', '.join(str(i) for i in ids) if ids else '—'}")
        return 1
    print(f"OK: все {len(CHECKS)} инвариантов выполнены")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(run())
