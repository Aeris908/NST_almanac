"""Диагностика воспроизводит рабочий движок и не меняет источник данных."""
from collections import Counter
from audit_elo import audit,simulate
from db import api
from db.pool import pool_from_db
from portal.master_table import replay


def test_audit_keeps_legacy_start_and_multipliers():
    matches=[{'id':1,'p1':'A','p2':'B','s1':4,'s2':1,'season':'Season 9','row_set':'pool'}]
    result=simulate(matches)
    assert result['ratings']=={'A':1536.0,'B':1464.0}
    assert result['games']=={'A':1,'B':1}


def test_audit_is_read_only_and_covers_every_rated_player(db_path):
    before=api.publication_revision(db_path)
    result=audit(db_path)
    assert api.publication_revision(db_path)==before
    expected=set(replay(pool_from_db(db_path)).elo)
    assert {p['player'] for p in result['players']}==expected
    counts=Counter(name for m in pool_from_db(db_path)
                   if not (m.get('is_technical') and m.get('technical_loser')) for name in (m['p1'],m['p2']))
    assert all(p['rated_games']==counts[p['player']] for p in result['players'])


def test_result_weight_variant_has_no_negative_win_and_bounded_k(db_path):
    result=simulate(pool_from_db(db_path),'result_weight')
    changes=[c for values in result['changes'].values() for c in values]
    assert max(c['k'] for c in changes)<=32
    assert not any(c['win_lost_points'] or c['loss_gained_points'] for c in changes)
