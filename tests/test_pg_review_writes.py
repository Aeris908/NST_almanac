"""Интеграция с отдельным локальным PostgreSQL; адреса удалённых серверов запрещены."""
import os
import uuid
from urllib.parse import urlsplit
import pytest
from db import edit,pg,review,store,sync

pytestmark=pytest.mark.skipif(not os.environ.get('NST_PG_TEST_URL'),reason='Нужен отдельный локальный Postgres в NST_PG_TEST_URL')

@pytest.fixture
def pg_copy():
    import psycopg
    from psycopg import sql
    url=os.environ['NST_PG_TEST_URL']
    assert urlsplit(url).hostname in ('127.0.0.1','localhost','::1'), 'Запись тестов разрешена только на локальный сервер'
    name='nst_test_review_'+uuid.uuid4().hex
    raw=psycopg.connect(url)
    local=store.connect()
    try:
        raw.execute(sql.SQL('create schema {}').format(sql.Identifier(name)))
        raw.execute(sql.SQL('set search_path to {}, pg_catalog').format(sql.Identifier(name)))
        raw.execute(pg.schema())
        for table in sync.TABLES_ORDER:
            columns=[r[1] for r in local.execute('pragma table_info('+table+')')]
            with raw.cursor().copy(sql.SQL('copy {} ({}) from stdin').format(sql.Identifier(table),sql.SQL(',').join(map(sql.Identifier,columns)))) as copy:
                for row in local.execute('select * from '+table):copy.write_row(tuple(row))
        for table in sync.IDENTITY_TABLES:
            raw.execute(sql.SQL("select setval(pg_get_serial_sequence(%s, 'id'),coalesce((select max(id) from {}),1),(select max(id) is not null from {}))").format(sql.Identifier(table),sql.Identifier(table)),(name+'.'+table,))
        raw.commit()
        con=pg.PgConnection(raw)
        from urllib.parse import quote
        con._test_url=url+("&" if "?" in url else "?")+"options="+quote("-csearch_path="+name+",pg_catalog")
        yield con
    finally:
        raw.rollback()
        raw.execute(sql.SQL('drop schema if exists {} cascade').format(sql.Identifier(name)))
        raw.commit();raw.close();local.close()

def test_postgres_existing_decision_creates_stage_commits_and_undoes(pg_copy):
    con=pg_copy
    task=con.execute("select id,matched_match_id from incoming where verdict='conflict' and batch!='team_archive_review' and matched_match_id is not null limit 1").fetchone()
    mid=task[1];before=con.execute('select stage_id,note from matches where id=?',(mid,)).fetchone()
    result=review.resolve_existing(con,{'task_id':task[0],'match_id':mid,'note':'PG isolated check','stage':'Postgres review regression','outcome':'regular','s1':2,'s2':1},'test')
    assert con.execute('select verdict from incoming where id=?',(task[0],)).fetchone()[0]=='same'
    assert con.execute('select name from stages where id=(select stage_id from matches where id=?)',(mid,)).fetchone()[0]=='Postgres review regression'
    from db.build_db import ensure_stage
    tid=con.execute('select tournament_id from matches where id=?',(mid,)).fetchone()[0]
    assert ensure_stage(con,tid,'Postgres review regression',{})==ensure_stage(con,tid,'Postgres review regression',{})
    con.commit()
    edit.undo(con,'op:'+result['op'])
    assert tuple(con.execute('select stage_id,note from matches where id=?',(mid,)).fetchone())==tuple(before)
    assert con.execute('select verdict from incoming where id=?',(task[0],)).fetchone()[0]=='conflict'

def new_game():
    return {'doc_key':'team_champ_5','sides':['Kunio & Memori','ectoPower & Davitel'],'s1':3,'s2':2,'tour':'PG check','stage':'Postgres new stage','league':'Высшая лига','phase':'regular','playoff':False}

def test_postgres_team_decision_adds_game_commits_and_undoes(pg_copy):
    con=pg_copy
    task=con.execute("select id from incoming where batch='team_archive_review' and verdict='conflict' and matched_match_id is null limit 1").fetchone()[0]
    before=con.execute('select count(*) from matches').fetchone()[0]
    result=review.apply(con,{'task_id':task,'decision':'save','note':'PG isolated check','games':[new_game()]},'test')
    assert con.execute('select count(*) from matches').fetchone()[0]==before+1
    assert con.execute('select verdict from incoming where id=?',(task,)).fetchone()[0]=='same'
    edit.undo(con,'op:'+result['op'])
    assert con.execute('select count(*) from matches').fetchone()[0]==before
    assert con.execute('select verdict from incoming where id=?',(task,)).fetchone()[0]=='conflict'

def test_postgres_failed_second_game_rolls_back_everything(pg_copy):
    con=pg_copy
    task=con.execute("select id from incoming where batch='team_archive_review' and verdict='conflict' and matched_match_id is null limit 1").fetchone()[0]
    before=con.execute('select count(*) from matches').fetchone()[0]
    with pytest.raises(edit.EditError):
        review.apply(con,{'task_id':task,'decision':'save','note':'PG rollback check','games':[new_game(),{**new_game(),'s1':-1}]},'test')
    assert con.execute('select count(*) from matches').fetchone()[0]==before
    assert con.execute('select verdict from incoming where id=?',(task,)).fetchone()[0]=='conflict'


def test_postgres_api_preview_then_persist_and_undo(pg_copy):
    from db import api
    con=pg_copy;url=con._test_url
    task=next(t for t in api.queue(url) if t['batch']!='team_archive_review' and t.get('match_id'))
    args={'task_id':task['id'],'task_expect':task['edit_version'],'match_id':task['match_id'],'note':'PG API integration check','video_url':'https://youtu.be/pg-video-check','stage':'PG API stage','outcome':'regular','s1':3,'s2':2}
    before=api.revision(url)
    preview=api.mutate('review-existing',args,'tester',db_path=url,persist=False)
    assert preview['ok'] and not preview['persisted'] and api.revision(url)==before
    saved=api.mutate('review-existing',args,'tester',db_path=url,persist=True,expect=preview['revision'])
    assert saved['ok'] and saved['persisted'] and saved['comparison']
    assert {'kind':'video','url':'https://youtu.be/pg-video-check'} in saved['match']['links']
    assert task['id'] not in {t['id'] for t in api.queue(url)}
    undone=api.mutate('undo',{'what':'op:'+saved['op']},'tester',db_path=url,persist=True)
    assert undone['ok'] and api.revision(url)==before
    assert task['id'] in {t['id'] for t in api.queue(url)}
