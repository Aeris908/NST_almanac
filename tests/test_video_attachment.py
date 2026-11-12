"""Видео добавляется отдельно от других источников и входит в атомарное решение задачи."""
import pytest
from db import api,edit,review

URL='https://vk.com/video-66162180_456239999'
def links(con,mid):return [(r[0],r[1]) for r in con.execute('select kind,url from match_links where match_id=? order by id',(mid,))]
def task(con):
    t=con.execute("select id,matched_match_id from incoming where verdict='conflict' and batch!='team_archive_review' and matched_match_id is not null limit 1").fetchone()
    return {'task_id':t[0],'match_id':t[1],'note':'Видео сверено с протоколом','outcome':'regular','s1':2,'s2':1}

def test_append_video_preserves_sources_is_idempotent_and_undoes(con):
    mid=task(con)['match_id'];before=links(con,mid)
    result=edit.add_video(con,mid,URL,'tester')
    assert set(before)<=set(links(con,mid)) and ('video',URL) in links(con,mid)
    again=edit.add_video(con,mid,URL,'tester')
    assert not again['journal']
    edit.undo(con,'op:'+result['op']);assert links(con,mid)==before

@pytest.mark.parametrize('url',['javascript:alert(1)','file:///video.mp4','https://','https://user:pass@example.com/video','https://example.com/a b'])
def test_invalid_video_does_not_change_archive(con,url):
    mid=task(con)['match_id'];before=links(con,mid)
    with pytest.raises(edit.EditError,match='полную ссылку'):edit.add_video(con,mid,url,'tester')
    assert links(con,mid)==before

def test_api_video_preview_does_not_write_and_save_returns_links(con,db_path):
    mid=task(con)['match_id'];before=links(con,mid)
    preview=api.mutate('add-video',{'match_id':mid,'url':URL},'tester',db_path=db_path)
    assert not preview['persisted'] and links(con,mid)==before
    saved=api.mutate('add-video',{'match_id':mid,'url':URL},'tester',db_path=db_path,persist=True,expect=preview['revision'])
    assert saved['persisted'] and {'kind':'video','url':URL} in saved['match']['links']

def test_existing_decision_adds_video_and_undo_restores_task(con):
    args=task(con);mid=args['match_id'];before=links(con,mid)
    result=review.resolve_existing(con,{**args,'video_url':URL},'tester')
    assert ('video',URL) in links(con,mid) and set(before)<=set(links(con,mid))
    edit.undo(con,'op:'+result['op']);assert links(con,mid)==before
    assert con.execute('select verdict from incoming where id=?',(args['task_id'],)).fetchone()[0]=='conflict'

def test_invalid_video_rolls_back_score_and_verdict(con):
    args=task(con);mid=args['match_id'];before=tuple(con.execute('select score from match_sides where match_id=? order by side_index',(mid,)).fetchall())
    with pytest.raises(edit.EditError):review.resolve_existing(con,{**args,'video_url':'not a link'},'tester')
    assert tuple(con.execute('select score from match_sides where match_id=? order by side_index',(mid,)).fetchall())==before
    assert con.execute('select verdict from incoming where id=?',(args['task_id'],)).fetchone()[0]=='conflict'

def test_team_decision_video_belongs_to_its_game(con):
    t=con.execute("select id from incoming where batch='team_archive_review' and verdict='conflict' and matched_match_id is null limit 1").fetchone()[0]
    game={'doc_key':'team_champ_5','sides':['Kunio & Memori','ectoPower & Davitel'],'s1':3,'s2':1,'stage':'Групповой этап','tour':'Тест видео','video_url':URL}
    result=review.apply(con,{'task_id':t,'decision':'save','note':'Сверено видео','games':[game,{**game,'video_url':''}]},'tester')
    assert ('video',URL) in links(con,result['created'][0])
    assert ('video',URL) not in links(con,result['created'][1])


def test_editing_team_game_keeps_earlier_video_and_sources(con):
    t=con.execute("select id,matched_match_id from incoming where batch='team_archive_review' and verdict='conflict' and matched_match_id is not null limit 1").fetchone()
    mid=t[1];old='https://youtu.be/older-recording'
    edit.add_video(con,mid,old,'tester');before=links(con,mid)
    sides=[edit.roster_of(con,r['id']) for r in edit.sides_of(con,mid)]
    doc=con.execute('select d.doc_key from matches m join tournament_docs d on d.id=m.doc_id where m.id=?',(mid,)).fetchone()[0]
    result=review.apply(con,{'task_id':t[0],'decision':'save','note':'Дополнена видеозапись','games':[{'match_id':mid,'doc_key':doc,'sides':sides,'s1':4,'s2':2,'stage':'Групповой этап','video_url':URL}]},'tester')
    assert set(before)<=set(links(con,mid)) and ('video',URL) in links(con,mid)
    edit.undo(con,'op:'+result['op']);assert links(con,mid)==before
