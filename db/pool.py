"""Чтение пула матчей из единой базы в той же форме, что его ждёт сборка."""

import sqlite3
from pathlib import Path
from db import store

DB_PATH = store.DB_PATH

READ_SQL = """
select id, season, tournament, stage, p1, p2, s1, s2, ot, pk, is_playoff,
       is_technical, technical_loser, note, order_in_source,
       played_on, source_date_raw, row_set, source, doc_year, doc_key
from v_rating_pool
order by order_in_source
"""

FIELDS = ("id", "season", "tournament", "stage", "p1", "p2", "s1", "s2", "ot", "pk",
          "is_playoff", "is_technical", "technical_loser", "note", "order_in_source",
          # Из чего движок рейтинга выводит год партии: сезонные строки дат не имеют, у строк
          # турниров года нет в названии, но есть сезон в рамке документа.
          "played_on", "source_date_raw", "row_set", "source", "doc_year", "doc_key")


def pool_from_db(db_path=DB_PATH):
    """Рейтинговый пул: ровно те строки, у которых в базе стоит флаг in_rating_pool."""
    if not Path(db_path).exists():
        raise SystemExit(
            f"Нет базы {db_path}. Соберите её: python db/build_db.py (или просто python build_all.py)."
        )
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    pool = []
    for row in con.execute(READ_SQL):
        match = {key: row[key] for key in FIELDS}
        for key in ("ot", "pk", "is_playoff", "is_technical"):
            match[key] = bool(match[key])
        match["is_forfeit"] = match["is_technical"]
        pool.append(match)
    con.close()
    if not pool:
        raise SystemExit(
            f"В базе {db_path} нет ни одного матча рейтингового пула — запустите python db/build_db.py."
        )
    return pool
