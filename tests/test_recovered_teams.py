"""Из первичного текста берём только однозначно подписанные ноги, с их ориентацией."""

from collectors.recover_team_archives import extract_post, score_of
from portal.names import clean_alias


def test_huba_and_exponat_are_opponents_not_aliases():
    assert clean_alias("eXponat") != clean_alias("Huba_Buba_5")


def test_forum_orientation_follows_each_game_header():
    post = {"id": "1", "url": "https://example.org/forum", "text":
            "1. Huba_Buba_5 + mafuta VS esteban + eXponat\nИталия 5:3 Бразилия\n"
            "2. esteban + eXponat VS Huba_Buba_5 + mafuta\nКамерун 4:4 (7:8) Италия\n"
            "Итог: 2:0"}
    rows = extract_post(post, "Турнир", "II чемпионат", early=True)
    assert len(rows) == 2
    assert rows[0]["team_a"] == ["Huba_Buba_5", "mafuta"]
    assert rows[1]["team_a"] == ["esteban", "eXponat"]
    assert rows[1]["outcome"] == ["loss", "win"]


def test_inline_penalty_notation():
    assert score_of("3 (6) : 3 (7)")[:3] == ([3, 3], "3:3 (ПК 6:7)", "penalties")


def test_unidentified_pair_is_not_inferred_from_previous_post():
    assert extract_post({"id": "1", "url": "x", "text": "Англия - Монголия 6:2"},
                        "Турнир", "topic") == []


def test_country_selection_and_series_summary_are_not_goals():
    post = {"id": "1", "url": "x", "text":
            "mafuta & izzzotope vs Буц & Dopi\nАнглия - Монголия 6:2\n"
            "Счет по очкам - 12:6\n2 круг Тай - Мекс"}
    assert len(extract_post(post, "Турнир", "topic")) == 1


def test_review_queue_is_idempotent_and_preserves_verdict(con, tmp_path, monkeypatch):
    import json

    from db import import_live

    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "team_recovery_review.json").write_text(json.dumps([{
        "source_ref": "team-archive-review:test", "match_ref": None,
        "задача": "Уточнить состав", "как_выглядит": "Текст источника",
    }]), encoding="utf-8")
    monkeypatch.setattr(import_live, "ROOT", tmp_path)
    import_live.write_team_review_queue(con)
    con.execute("update incoming set verdict = 'same' where source_ref = 'team-archive-review:test'")
    import_live.write_team_review_queue(con)
    rows = con.execute("select verdict, matched_match_id from incoming "
                       "where source_ref = 'team-archive-review:test'").fetchall()
    assert [tuple(row) for row in rows] == [("same", None)]
