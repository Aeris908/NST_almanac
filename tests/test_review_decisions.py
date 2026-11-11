"""Решение задачи: настоящее создание/изменение, закрытие, откат и атомарный отказ."""

import pytest

from db import api, edit, review


def unresolved(con):
    return con.execute("select id from incoming where batch='team_archive_review' "
                       "and verdict='conflict' and matched_match_id is null limit 1").fetchone()[0]


def game():
    return {"doc_key": "team_champ_5", "sides": ["Kunio & Memori", "ectoPower & Davitel"],
            "s1": 99, "s2": 98, "tour": "Проверка редактора", "stage": "Групповой этап",
            "league": "Высшая лига", "phase": "regular", "playoff": False}


def test_create_close_and_undo_one_operation(con):
    task = unresolved(con)
    before = con.execute("select count(*) from matches").fetchone()[0]
    result = review.apply(con, {"task_id": task, "decision": "save", "note": "Сверено с источником",
                                "games": [game()]}, "tester")
    assert con.execute("select count(*) from matches").fetchone()[0] == before + 1
    assert con.execute("select verdict from incoming where id=?", (task,)).fetchone()[0] == "same"
    assert con.execute("select manual from matches where id=?", (result["match_id"],)).fetchone()[0] == 1
    edit.undo(con, "op:" + result["op"])
    assert con.execute("select count(*) from matches").fetchone()[0] == before
    assert con.execute("select verdict from incoming where id=?", (task,)).fetchone()[0] == "conflict"


def test_second_invalid_game_rolls_back_first_and_task(con):
    task = unresolved(con)
    before = con.execute("select count(*) from matches").fetchone()[0]
    journal = con.execute("select count(*) from corrections").fetchone()[0]
    with pytest.raises(edit.EditError):
        review.apply(con, {"task_id": task, "decision": "save", "note": "Источник",
                           "games": [game(), {**game(), "s1": -1}]}, "tester")
    assert con.execute("select count(*) from matches").fetchone()[0] == before
    assert con.execute("select count(*) from corrections").fetchone()[0] == journal
    assert con.execute("select verdict from incoming where id=?", (task,)).fetchone()[0] == "conflict"


def test_reject_requires_note_and_cannot_resolve_twice(con):
    task = unresolved(con)
    with pytest.raises(edit.EditError):
        review.apply(con, {"task_id": task, "decision": "reject", "note": ""}, "tester")
    review.apply(con, {"task_id": task, "decision": "reject", "note": "Это цитата старого отчёта"}, "tester")
    with pytest.raises(edit.EditError, match="уже решена"):
        review.apply(con, {"task_id": task, "decision": "reject", "note": "Повтор"}, "tester")


def test_preview_does_not_write_and_apply_closes_task(db_path):
    con = edit.connect(db_path)
    task = unresolved(con)
    con.close()
    args = {"task_id": task, "decision": "save", "note": "Проверено", "games": [game()]}
    revision = api.revision(db_path)
    preview = api.mutate("review-task", args, "tester", db_path=db_path)
    assert not preview["persisted"]
    assert api.revision(db_path) == revision
    result = api.mutate("review-task", args, "tester", persist=True, expect=revision, db_path=db_path)
    assert result["persisted"]
    assert task not in [row["id"] for row in api.queue(db_path)]


def test_existing_game_edits_all_fields_and_undo_restores(con):
    task = con.execute("select id,matched_match_id from incoming where batch='team_archive_review' "
                       "and verdict='conflict' and matched_match_id is not null limit 1").fetchone()
    mid = task[1]
    old = con.execute("select tour from matches where id=?", (mid,)).fetchone()[0]
    sides = edit.sides_of(con, mid)
    rosters = [edit.roster_of(con, side["id"]) for side in sides]
    doc_key = con.execute("select d.doc_key from matches m join tournament_docs d on d.id=m.doc_id "
                          "where m.id=?", (mid,)).fetchone()[0]
    result = review.apply(con, {"task_id": task[0], "decision": "save", "note": "Проверены составы и тур",
                                "games": [{**game(), "match_id": mid, "sides": rosters, "doc_key": doc_key,
                                           "tour": "Уточнённый тур"}]}, "tester")
    assert con.execute("select tour from matches where id=?", (mid,)).fetchone()[0] == "Уточнённый тур"
    assert [r[0] for r in con.execute("select score from match_sides where match_id=? order by side_index", (mid,))] == [99, 98]
    edit.undo(con, "op:" + result["op"])
    assert con.execute("select tour from matches where id=?", (mid,)).fetchone()[0] == old


def test_two_new_games_with_same_score_are_separate_legs(con):
    task = unresolved(con)
    result = review.apply(con, {"task_id": task, "decision": "save", "note": "Две отдельные игры",
                                "games": [game(), game()]}, "tester")
    assert len(result["created"]) == 2
    assert len(set(result["created"])) == 2
