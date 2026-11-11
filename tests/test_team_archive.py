"""Командные протоколы из носителя доходят до истории участников."""

from collections import defaultdict

from portal.player_records import add_team_records


def test_team_carrier_field_reaches_all_four_players():
    histories = defaultdict(list)
    match = {"t1": "Kunio & Memori", "t2": "ectoPower & Davitel",
             "score": "6:2", "stage": "1/2 финала"}
    add_team_records(histories, 0, {"title": "Командный чемпионат", "season_year": 2020,
                                   "playoff_matches": [match]})
    assert len(histories) == 4
    assert sum(len(rows) for rows in histories.values()) == 4
    assert all(rows[0]["stage"] == "1/2 финала" for rows in histories.values())


def test_team_match_arrays_are_not_counted_twice():
    histories = defaultdict(list)
    match = {"t1": "Kunio & Memori", "t2": "ectoPower & Davitel", "score": "6:2"}
    add_team_records(histories, 0, {"matches": [match], "playoff_matches": [match]})
    assert sum(len(rows) for rows in histories.values()) == 4


def test_penalty_result_and_source_reach_history():
    histories = defaultdict(list)
    add_team_records(histories, 0, {"playoff_matches": [{
        "t1": "Kunio & Memori", "t2": "ectoPower & Davitel",
        "score": "4:4 (ПК 7:6)", "vk_url": "https://example.org/source",
    }]})
    assert histories["Kunio"][0]["result"] == "ПОБЕДА"
    assert histories["ectoPower"][0]["result"] == "ПОРАЖЕНИЕ"
    assert histories["Kunio"][0]["pk"]
    assert histories["Kunio"][0]["vk_url"] == "https://example.org/source"
