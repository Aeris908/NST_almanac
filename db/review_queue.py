"""Обновление очереди без пересоздания идентификаторов и потери ручных решений."""

import json

from db import store


def upsert(con, batch, source, source_ref, payload, verdict, match_id):
    existing = con.execute('select id,payload,verdict from incoming where batch=? and source_ref=?',
                           (batch,source_ref)).fetchone()
    if existing:
        previous = store.parse_json(existing[1], default={})
        if previous.get('вердикт_редактора'):
            payload = {**payload,'вердикт_редактора':previous['вердикт_редактора']}
            verdict = existing[2]
        con.execute('update incoming set payload=?,verdict=?,matched_match_id=? where id=?',
                    (json.dumps(payload,ensure_ascii=False),verdict,match_id,existing[0]))
        return existing[0]
    con.execute('insert into incoming(batch,source,source_ref,payload,verdict,matched_match_id) '
                'values (?,?,?,?,?,?)', (batch,source,source_ref,json.dumps(payload,ensure_ascii=False),verdict,match_id))
    return con.execute('select last_insert_rowid()').fetchone()[0]


def remove_obsolete(con, batches, seen):
    for batch in batches:
        for task_id,ref in con.execute("select id,source_ref from incoming where batch=? and verdict='conflict'",
                                      (batch,)).fetchall():
            if (batch,ref) not in seen and not con.execute(
                    "select 1 from corrections where table_name='incoming' and row_id=? limit 1", (task_id,)).fetchone():
                con.execute('delete from incoming where id=?', (task_id,))
