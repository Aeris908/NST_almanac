"""Имена для поиска и подтверждённые связи задач с турнирами."""

import re

from db import store


def player_aliases(db_path=store.DB_PATH):
    con = store.connect(db_path)
    try:
        result = {}
        for nick, alias in con.execute('select p.nick,a.alias from player_aliases a '
                                       'join players p on p.id=a.player_id order by a.id'):
            result.setdefault(nick, []).append(alias)
        return result
    finally:
        con.close()


def review_document_key(task, docs):
    text = str(task or '')
    for doc in docs:
        if text.startswith(doc['title']):
            return doc['doc_key']
    # Ранние чемпионаты хранятся в одном документе, задачи именуют их по отдельности.
    if re.match(r'^(?:I|II) командный\b', text, re.I):
        return next((d['doc_key'] for d in docs if d['doc_key'] == 'team_champ_1_2'), '')
    return ''


def archive_reviews(db_path=store.DB_PATH):
    con = store.connect(db_path)
    try:
        docs = [{'doc_key':key, 'title':title} for key,title in con.execute(
            "select doc_key,title from tournament_docs where kind='team'")]
        counts = {d['doc_key']:0 for d in docs}
        for (raw,) in con.execute("select payload from incoming where batch='team_archive_review' and verdict='conflict'"):
            key = review_document_key(store.parse_json(raw, default={}).get('задача'), docs)
            if key:
                counts[key] += 1
        return counts
    finally:
        con.close()
