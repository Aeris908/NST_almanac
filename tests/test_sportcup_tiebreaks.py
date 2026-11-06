"""Значок «была доигровка» у Sportcup — не про овертайм: серию отличаем по теме.

Sportcup помечает `overtimeWin` игру, решённую чем угодно, и хранит её счётом доигровки:
«1:1 (ПК 5:3)» живёт как 5:3. Ключа `afterGameWin` в снапшоте Сезонов 8-9 нет ни разу, поэтому
без сверки с темой витрина печатает «ОТ» там, где были пенальти. Правило обязано молчать там, где
источник молчит: недоказанная игра остаётся как есть, а не угадывается.
"""

import json

from collectors.sportcup_tiebreaks import DECISIONS, SNAPSHOT, classify, score_forms

LINES = [
    ("Memori vs leonudomlya - 5:4 (PK)", 31171),
    ("Kunio VS ectoPower 2:3 (овертайм)", 31316),
    ("blanco vs Сахарок (0:1, 4:3(PK))", 31375),
    ("Yuliy_Cezar vs yoxter 1:1 (ПК 5:3)", 32791),
    ("leonudomlya - Aeris 1:1, 3:6 пен.", 32854),
    ("Spartacus 1:2 Ryumaru без пометки", 32890),
]


def game(nick1, s1, s2, nick2="leonudomlya"):
    return {"uuid": "u", "member1": {"title": nick1}, "member2": {"title": nick2},
            "scoreMember1": s1, "scoreMember2": s2, "overtimeWin": True}


def test_a_line_that_names_a_series_is_penalties():
    assert classify(game("Memori", 5, 4), LINES)[0] == "penalties"
    assert classify(game("Yuliy_Cezar", 5, 3, "yoxter"), LINES)[0] == "penalties"
    assert classify(game("leonudomlya", 3, 6, "Aeris"), LINES)[0] == "penalties"


def test_the_stored_score_may_be_printed_flipped_or_in_brackets():
    """Счёт серии в теме стоит и в прямой, и в обратной ориентации, и в скобках."""
    assert "4:3" in score_forms(3, 4) and "3-4" in score_forms(3, 4)
    assert classify(game("blanco", 3, 4, "Сахарок"), LINES)[0] == "penalties"


def test_a_line_that_names_overtime_stays_overtime():
    assert classify(game("Kunio", 2, 3, "ectoPower"), LINES)[0] == "overtime"


def test_a_line_without_a_marker_is_unknown_and_not_guessed():
    """Нет слова о серии — нет и правки: молчание темы не превращаем в догадку."""
    assert classify(game("Spartacus", 1, 2, "Ryumaru"), LINES)[0] == "unknown"
    assert classify(game("Kunio", 9, 9, "ectoPower"), LINES)[0] == "unknown"


def test_a_line_about_another_score_is_not_evidence():
    """Совпали игроки, но не счёт игры: это не доказательство, а случайность."""
    assert classify(game("Memori", 7, 6), LINES)[0] == "unknown"


def test_proven_series_are_flagged_games_of_the_snapshot():
    """Носитель решений не имеет права ссылаться на игру, которой снапшот не помечал.

    Иначе правка в `data/sportcup_decisions.json` снимет флаг там, где доигровки источники не
    видели вовсе, и сборки это не заметят: проверка живёт здесь, а не в памяти о прошлом разе.
    """
    flagged = set()
    blob = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    for stage in blob["stages"]:
        for row in stage["response"].get("list", []):
            if row.get("overtimeWin"):
                flagged.add(row["uuid"])
    proven = {row["uuid"] for row in json.loads(DECISIONS.read_text(encoding="utf-8")).get("tiebreak_penalties", [])}
    assert proven, "носитель без единого доказательства серии — правка не работает"
    assert not (proven - flagged), f"серии там, где снапшот flags не ставил: {sorted(proven - flagged)}"


def test_the_pool_stores_a_proven_series_as_penalties(con):
    """База обязана донести то, что сказала тема: фаза `penalties`, а не `overtime`."""
    proven = {row["uuid"] for row in json.loads(DECISIONS.read_text(encoding="utf-8")).get("tiebreak_penalties", [])}
    wrong = []
    for uuid in sorted(proven):
        row = con.execute("select phase from matches where source = 'sportcup_api' and source_ref = ?",
                          (uuid,)).fetchone()
        if row is None:
            wrong.append((uuid, "нет строки"))
        elif row["phase"] != "penalties":
            wrong.append((uuid, row["phase"]))
    assert not wrong, f"доказанные серии легли не как пенальти: {wrong[:5]}"