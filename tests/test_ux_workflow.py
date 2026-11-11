"""Публикация учитывает изменения без счёта, журнал и откат сохраняют целостность решения."""

import pytest

from db import api, edit, review
from test_review_decisions import game, unresolved
from portal.ux_data import player_aliases, archive_reviews, review_document_key


def test_publication_fingerprint_covers_names_and_verdicts(con, db_path):
    before = api.publication_revision(db_path)
    assert api.publication_revision(db_path) == before
    con.execute("update players set nick='New visible nick' where nick='Kunio'")
    con.commit()
    renamed = api.publication_revision(db_path)
    assert renamed != before
    con.execute("update incoming set verdict='rejected' where id=?", (unresolved(con),))
    con.commit()
    assert api.publication_revision(db_path) != renamed


def test_journal_limit_does_not_cut_an_operation(con, db_path):
    result = review.apply(con, {'task_id':unresolved(con), 'decision':'save',
                               'note':'Проверены игры отчёта', 'games':[game() for _ in range(10)]}, 'tester')
    operations = api.journal_operations(1, db_path)
    assert len(operations) == 1
    assert operations[0]['op'] == result['op']
    assert operations[0]['note'] == 'Проверены игры отчёта'
    assert len(operations[0]['entries']) > 8
    assert len(operations[0]['entries']) == con.execute(
        'select count(*) from corrections where op=?', (result['op'],)).fetchone()[0]


def test_specific_undo_cannot_overwrite_a_later_edit(con):
    result = review.apply(con, {'task_id':unresolved(con), 'decision':'save',
                               'note':'Добавлена игра', 'games':[game()]}, 'first')
    later = edit.set_score(con, result['match_id'], 3, 1, 'second')
    with pytest.raises(edit.EditError, match='более позднее решение'):
        edit.undo(con, 'op:'+result['op'])
    edit.undo(con, 'op:'+later['op'])
    edit.undo(con, 'op:'+result['op'])
    assert con.execute('select 1 from matches where id=?', (result['match_id'],)).fetchone() is None


def test_aliases_and_early_archive_links(db_path):
    assert 'CentZloy' in player_aliases(db_path)['Centurion']
    assert archive_reviews(db_path)['team_champ_3'] > 0
    docs = [{'doc_key':'team_champ_1_2', 'title':'I и II Командные Чемпионаты'}]
    assert review_document_key('II командный: проверить состав', docs) == 'team_champ_1_2'
    assert review_document_key('III командный: проверить состав', docs) == ''


def existing_task(con):
    task = con.execute("select id,matched_match_id from incoming where verdict='conflict' "
                       "and batch != 'team_archive_review' limit 1").fetchone()
    return {'task_id':task[0], 'match_id':task[1], 'note':'Проверен исходный протокол',
            'stage':'Проверенный этап', 'outcome':'regular', 's1':2, 's2':1}


def test_existing_resolution_saves_all_fields_and_undo(con, db_path):
    args = existing_task(con)
    before = api.publication_revision(db_path)
    result = review.resolve_existing(con, args, 'tester')
    assert con.execute('select verdict from incoming where id=?', (args['task_id'],)).fetchone()[0] == 'same'
    assert con.execute('select s.name from stages s join matches m on m.stage_id=s.id where m.id=?',
                       (args['match_id'],)).fetchone()[0] == args['stage']
    assert api.journal_operations(1, db_path)[0]['note'] == args['note']
    edit.undo(con, 'op:'+result['op'])
    assert api.publication_revision(db_path) == before


def test_existing_resolution_invalid_penalties_roll_back(con, db_path):
    args = {**existing_task(con), 'outcome':'penalties', 's1':4, 's2':4, 'pk1':2, 'pk2':2}
    before = api.publication_revision(db_path)
    with pytest.raises(edit.EditError, match='буллитов'):
        review.resolve_existing(con, args, 'tester')
    assert api.publication_revision(db_path) == before


def test_existing_resolution_penalty_winner_and_note(con):
    args = {**existing_task(con), 'outcome':'penalties', 's1':4, 's2':4, 'pk1':7, 'pk2':6}
    review.resolve_existing(con, args, 'tester')
    assert con.execute('select note from matches where id=?', (args['match_id'],)).fetchone()[0] == '4:4 (ПК 7:6)'
    assert [r[0] for r in con.execute('select outcome from match_sides where match_id=? order by side_index',
                                    (args['match_id'],))] == ['win','loss']


def test_lore_reimport_preserves_task_id_note_and_undo(con, db_path):
    from db.lore_review_queue import populate_lore_review
    args = existing_task(con)
    result = review.resolve_existing(con,args,'tester')
    populate_lore_review(con)
    row = con.execute('select verdict,payload from incoming where id=?', (args['task_id'],)).fetchone()
    assert row[0] == 'same'
    assert args['note'] in row[1]
    edit.undo(con,'op:'+result['op'])
    assert con.execute('select verdict from incoming where id=?', (args['task_id'],)).fetchone()[0] == 'conflict'


def test_live_reimport_preserves_task_id_and_note(con):
    import json
    from db.import_live import write_review_queue
    task = con.execute("select id,source_ref,payload,matched_match_id from incoming "
                       "where batch like 'vk_live_review_%' and verdict='conflict' limit 1").fetchone()
    payload = json.loads(task[2])
    args = {**existing_task(con),'task_id':task[0],'match_id':task[3]}
    review.resolve_existing(con,args,'tester')
    batch = con.execute('select batch from incoming where id=?', (task[0],)).fetchone()[0]
    game = {'source_ref':task[1], 'source_page':'topic-'+batch.removeprefix('vk_live_review_'),
            'review':{'задача':payload['задача'],'ссылки':payload['ссылки']},
            'tour':payload['тур'],'team_a':['Kunio'],'team_b':['Memori'],'score_text':'3:1'}
    write_review_queue(con,[(task[3],game)])
    row = con.execute('select verdict,payload from incoming where id=?', (task[0],)).fetchone()
    assert row[0] == 'same'
    assert args['note'] in row[1]
