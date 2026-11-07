"""Клубный Goal 4 в живом импорте: протокол доезжает до базы целиком, без потеряшек.

Статическая рамка турнира больше не несёт игр (`matches: []` + `row_keys`) — их приносит
разбор листов источника, тот же путь, что у группового тура молодёжки и у пенальти.
Причина: рамка спецтурнира принимает только девять ключей и не умеет выразить ни ТП обоим,
ни буллиты, а протоколу нужно и то и другое.

Главная проверка — сквозная: в протоколе 35 повторов «тот же тур, та же пара, тот же счёт»,
и ключ дублей импортёра их не различает. Если защиты нет, 35 игр из 126 молча уходят в
`hidden_by`, а витрина показывает 91 игру вместо 126 и врёт о мячах.
"""

import sqlite3

from db import import_live
from portal.club_sources import TOURNAMENT

DOC_KEY = "club_offseason_goal4"


def test_club_rows_reads_the_committed_sheets():
    rows, report = import_live.club_rows()
    assert len(rows) == 129
    assert report["totals"]["игр сыграно"] == 126
    assert report["totals"]["не сыграно (ТП обоим)"] == 3
    assert report["totals"]["сходимость с таблицами"] == "полная"
    assert all(row["tournament"] == TOURNAMENT for row in rows)


def test_club_rows_is_silent_without_the_sheets(tmp_path, monkeypatch):
    """Выгрузки листов нет — разбор молчит, а не роняет сборку (как у молодёжки и пенальти)."""
    monkeypatch.setattr(import_live, "CLUB_SHEET", tmp_path)
    assert import_live.club_rows() == ([], {})


def test_club_document_carries_the_whole_protocol(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        doc = con.execute("select id from tournament_docs where doc_key = ?", (DOC_KEY,)).fetchone()
        assert doc, "рамка клубного турнира обязана быть в базе"
        rows = con.execute(
            "select status, hidden_by, duplicate_of from matches where doc_id = ?", (doc["id"],)
        ).fetchall()
        assert len(rows) == 129
        assert all(row["hidden_by"] is None for row in rows), "ни одна игра протокола не потеряна"
        assert all(row["duplicate_of"] is None for row in rows)
        assert sum(row["status"] == "technical" for row in rows) == 3
        assert sum(row["status"] == "played" for row in rows) == 126
    finally:
        con.close()


def test_club_goals_match_the_source_tables(db_path):
    """Мячи считаются как в таблице источника — вместе с буллитами: 511 Премьер + 380 молодёжка."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        doc = con.execute("select id from tournament_docs where doc_key = ?", (DOC_KEY,)).fetchone()
        goals = con.execute(
            """select m.league, sum(s.score) as goals from matches m
               join match_sides s on s.match_id = m.id
               where m.doc_id = ? and m.status = 'played' and m.hidden_by is null
               group by m.league""", (doc["id"],)
        ).fetchall()
        assert {row["league"]: row["goals"] for row in goals} == {
            "Премьер-лига": 511, "Молодёжная лига": 380
        }
    finally:
        con.close()
