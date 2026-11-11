"""Отложенные данные, конфликты и предпросмотр не теряют содержимое архива."""
import copy
import json
import subprocess
from pathlib import Path

import pytest
from db import api,edit,review
from portal.lazy_data import soccer_summary,catalog_summary
from test_review_decisions import game,unresolved


def test_lazy_chunks_reconstruct_history_and_distinguish_identical_games(tmp_path):
    payload={'profiles':[{'player':'X','match_history':[{'score':'2:1'}]}],
             'seasons':[{'id':'1','name':'Первый','matches':[{'p1':'A','p2':'B','s1':1,'s2':0}]*2}]}
    original=copy.deepcopy(payload)
    summary=soccer_summary(payload,tmp_path)
    assert payload==original
    assert 'match_history' not in summary['profiles'][0]
    history=json.loads((tmp_path/Path(summary['profiles'][0]['lazy_url']).name).read_text(encoding='utf-8'))
    assert history['match_history']==payload['profiles'][0]['match_history']
    season=json.loads((tmp_path/Path(summary['seasons'][0]['lazy_url']).name).read_text(encoding='utf-8'))
    assert len({m['_anchor'] for m in season['matches']})==2
    changed=copy.deepcopy(payload);changed['seasons'][0]['matches'][0]['s1']=9
    updated=soccer_summary(changed,tmp_path)
    other=json.loads((tmp_path/Path(updated['seasons'][0]['lazy_url']).name).read_text(encoding='utf-8'))
    assert other['matches'][0]['_anchor']==season['matches'][0]['_anchor']


def test_catalog_keeps_metrics_and_last_five_results():
    data={'players':[{'career':{'matches':50},'matches':[{'res_type':'win','text':'large'}]*10}]}
    result=catalog_summary(data)
    assert result['players'][0]['career']['matches']==50
    assert result['players'][0]['matches']==[{'res_type':'win'}]*5
    assert len(data['players'][0]['matches'])==10


def test_review_version_accepts_current_and_refuses_changed_stage(con,db_path):
    task=next(t for t in api.queue(db_path) if t['batch']=='team_archive_review' and t['review_matches'])
    args={'task_id':task['id'],'task_expect':task['edit_version'],'decision':'confirm','note':'Проверено','games':[]}
    # Текущая версия из карточки совпадает с проверкой в транзакции.
    answer=api.mutate('review-task',args,'tester',db_path=db_path)
    assert not answer['persisted']
    edit.set_place(con,task['review_matches'][0]['id'],'other',stage='Новое подтверждённое место')
    with pytest.raises(edit.EditError,match='REVIEW_CONFLICT'):
        review.apply(con,args,'tester')


def test_unconfirmed_proposal_cannot_be_saved(con):
    with pytest.raises(edit.EditError,match='Подтвердите'):
        review.apply(con,{'task_id':unresolved(con),'decision':'save','note':'Источник',
                         'games':[{**game(),'from_report':True,'confirmed':False}]},'tester')


def test_preview_shows_actual_before_and_after(con,db_path):
    task=next(t for t in api.queue(db_path) if t['batch']=='team_archive_review' and t['review_matches'])
    match=task['review_matches'][0]
    row={**game(),'match_id':match['id'],'doc_key':match['doc_key'],
         'sides':[s['players'] for s in match['sides']]}
    result=api.mutate('review-task',{'task_id':task['id'],'decision':'save','note':'Сверено','games':[row]},'tester',db_path=db_path)
    comparison=result['comparison'][0]
    assert comparison['before']['sides'][0]['score']==match['sides'][0]['score']
    assert comparison['after']['sides'][0]['score']==99
    assert api.match_row(con,match['id'])['sides'][0]['score']==match['sides'][0]['score']


def test_report_parser_requires_unambiguous_names_and_flags_duplicates():
    code="""const {parse}=require('./report-helper.js');const p=['Kunio','Memori','ectoPower','Davitel'].map(n=>({nick:n}));console.log(JSON.stringify(parse('Kunio & Memori vs ectoPower & Davitel 4:4 (ПК 7-6)\\nКорея - Англия 2:1\\nКорея - Англия 2:1\\nНеясный итог',p)));"""
    data=json.loads(subprocess.check_output(['node','-e',code],text=True,encoding='utf-8'))
    assert data['games'][0]['sides']==[['Kunio','Memori'],['ectoPower','Davitel']]
    assert (data['games'][0]['pk1'],data['games'][0]['pk2'])==(7,6)
    assert data['games'][1]['sides'] is None
    assert any('дубль' in text for text in data['games'][2]['warnings'])
    assert len(data['unparsed'])==1
