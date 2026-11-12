"""Версия конкретной задачи учитывает составы, стадию, исходы и текст источника."""
import hashlib
import json
from db import store, edit


def version(task_id, verdict, payload, rows):
    games=[]
    for row in sorted(rows,key=lambda r:r['id']):
        games.append({**{key:row.get(key) or None for key in ('id','doc_key','tour','league','stage','note','status','phase','is_playoff','played_on')},
                      'links':sorted((link.get('kind'),link.get('url')) for link in row.get('links',[])),
                      'sides':[{key:side.get(key) for key in ('players','score','outcome')} for side in row.get('sides',[])]})
    content=[task_id,verdict,payload,games]
    return hashlib.sha256(json.dumps(content,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()[:20]


def check(con, task, expected):
    if not expected:return
    from db.api import match_row
    payload=store.parse_json(task['payload'],default={})
    prefix=str(payload.get('match_ref') or '').rsplit(':line-',1)[0]
    ids=set()
    if task['matched_match_id']:ids.add(task['matched_match_id'])
    if task['batch']=='team_archive_review' and prefix:
        ids.update(r[0] for r in con.execute('select id from matches where source_ref like ?', (prefix+':line-%',)))
    rows=[match_row(con,mid) for mid in sorted(ids)]
    if version(task['id'],task['verdict'],payload,[r for r in rows if r])!=expected:
        raise edit.EditError('REVIEW_CONFLICT: данные этой задачи изменились. Сравните серверную версию с черновиком.')
