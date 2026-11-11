"""Общие правила Division Elo v2: уровни, переходы, исходы и охват источников."""
from collections import Counter
import pytest
from db import api,edit
from db.rating_history import rating_history_from_db,rating_history
from db.elo_review_queue import refresh
from portal import elo,master_table
from portal.build_soccer import compose_payload


def match(tier='Дворовая',**values):
    return {'id':1,'season':'Season 9','tournament':'Test season','row_set':'catalog','league':tier+' лига',
            'p1':'A','p2':'B','s1':1,'s2':0,'order_in_source':1,**values}


def test_division_centres_preserve_large_gap():
    high=elo.play(match('Высшая'),{},{},{})
    yard=elo.play(match('Дворовая'),{},{},{})
    assert high[0]-yard[0]==800
    assert elo.expected(1800,1000)==pytest.approx(100/101)
    assert elo.expected(1400,1000)==pytest.approx(10/11)


def test_closed_yard_wins_do_not_create_elite_rating():
    ratings={};games={};cal={}
    for n in range(12):
        row=match(p2='opponent'+str(n),s1=8,s2=0)
        a,b=elo.play(row,ratings,games,cal);ratings['A']=a;ratings[row['p2']]=b
    assert ratings['A']<1200


def test_promotion_does_not_grant_free_points():
    ratings={};games={};cal={}
    a,b=elo.play(match('Средняя',s1=1,s2=1),ratings,games,cal);ratings.update(A=a,B=b)
    promoted=match('Высшая',p2='elite',s1=0,s2=4)
    a,b=elo.play(promoted,ratings,games,cal)
    assert a<1400
    assert cal['A']['adjustment']==0
    assert cal['A']['tier']=='Высшая'


def test_penalty_winner_with_equal_goals_gains_points():
    a,b=elo.play(match('Средняя',s1=4,s2=4,pk=True,outcome_a='win',outcome_b='loss'),{},{},{})
    assert a>1400>b
    assert a+b==2800


def test_no_shared_newcomer_boost_or_activity_deduction():
    row=match('Высшая',is_playoff=True)
    assert elo.k_factor(row,0,100,10)==elo.k_factor(row,100,100,10)<=40
    assert elo.decay_penalty(12)==0
    assert elo.active_rating(1850,300)==1850


def test_unified_league_does_not_invent_an_elite_classification():
    cal={};elo.play(match('Высшая (Единая)',season='Season 1'),{},{},cal)
    assert not cal['A']['calibrated']


def test_wrong_comment_date_does_not_move_an_old_season_forward():
    old=match(season='Season 3',played_on='2025-01-01')
    recent=match(season='Season 9')
    assert elo.order_matches([recent,old])==[old,recent]
    assert elo.exact_year(old) is None


def test_initial_yard_peak_is_not_the_neutral_prior():
    tally=master_table.replay([match()])
    assert tally.peak_elo['A']==tally.elo['A']<1100


def test_full_season_pool_and_rvd_aliases(db_path):
    rows,info=rating_history(db_path)
    assert {str(n) for n in range(1,10)}=={s.removeprefix('Season ') for s in info['seasons']}
    assert sum('RVD (МГБ)' in (row['p1'],row['p2']) for row in rows)>=50
    assert any(p['nick']=='RVD (МГБ)' for p in api.players('FieryKelsen',db_path=db_path))
    assert all(not row['is_technical'] for row in rows)
    assert len({row['id'] for row in rows})==len(rows)


def test_explicit_exclusion_of_auto_included_match_can_be_undone(con,db_path):
    row=next(r for r in rating_history_from_db(db_path) if not r['in_rating_pool'])
    result=edit.set_rating(con,row['id'],False,'tester')
    assert row['id'] not in {r['id'] for r in rating_history_from_db(db_path)}
    edit.undo(con,'op:'+result['op'])
    assert row['id'] in {r['id'] for r in rating_history_from_db(db_path)}


def test_profiles_distinguish_qualification_and_career(db_path):
    profiles={p['player']:p for p in compose_payload(db_path)['profiles']}
    hanter=profiles['Hanter'];rvd=profiles['RVD (МГБ)'];aeris=profiles['Aeris']
    assert hanter['provisional'] and hanter['rating_rank'] is None
    assert rvd['rated_games']>=50 and rvd['active_elo']-hanter['active_elo']>400
    assert aeris['league']=='Высшая' and aeris['active_elo']<1600
    assert profiles['Yuliy_Cezar']['league']=='Средняя'


def test_rating_lore_queue_is_idempotent(db_path):
    refresh(db_path);first=[t['id'] for t in api.queue(db_path) if t['batch']=='elo_review']
    refresh(db_path);second=[t['id'] for t in api.queue(db_path) if t['batch']=='elo_review']
    assert first==second


def test_editor_shows_automatic_rating_and_can_correct_lore_date(con,db_path):
    from db import review
    row=next(r for r in rating_history_from_db(db_path) if not r['in_rating_pool'])
    found=api.locate(row['p1'],row['p2'],season=row['season'],db_path=db_path)
    assert any(r['rating_included'] for r in found if row['id'] in [r['id'],*r['linked']])
    refresh(db_path)
    task=next(t for t in api.queue(db_path) if t['batch']=='elo_review')
    mid=task['match_id'];sides=con.execute('select score from match_sides where match_id=? order by side_index',(mid,)).fetchall()
    previous=con.execute('select played_on from matches where id=?',(mid,)).fetchone()[0]
    result=review.resolve_existing(con,{'task_id':task['id'],'match_id':mid,'note':'Проверка даты по источнику',
        's1':sides[0][0],'s2':sides[1][0],'outcome':'regular','played_on':'2016-05-01'},'tester')
    assert con.execute('select played_on from matches where id=?',(mid,)).fetchone()[0]=='2016-05-01'
    edit.undo(con,'op:'+result['op'])
    assert con.execute('select played_on from matches where id=?',(mid,)).fetchone()[0]==previous


def test_sportcup_projection_cannot_count_twice_when_mirror_marker_is_missing(con,db_path):
    before=rating_history_from_db(db_path)
    con.execute("update matches set duplicate_of=null where row_set='catalog' and source='sportcup_api'")
    con.commit()
    after=rating_history_from_db(db_path)
    assert [r['id'] for r in after]==[r['id'] for r in before]
