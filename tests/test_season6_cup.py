"""Кубок лиг Сезона 6: справочник страницы обязан совпадать с сеткой источника.

Источник — Google-таблица «Кубок 6», которую владелец назвал сам:
`1fG1ZaZmjzOUYplUwVKjAe-P4RgPeGE6HuNt9MmQpzMc`, лист `1344056972` (единственный заполненный,
«Лист2» и «Лист3» пусты). CSV лежит в `data/gsheet_season6/`, поэтому тестам не нужна сеть.

Прежний справочник нёс 14 встреч вместо 15 и перепутал половины сетки: в 1/4 стояли
«Transistor — Tymoschuk 4:1» и «mafuta — Centurion 4:0», а в 1/2 «ectoPower — Memori» и
«Transistor — mafuta». По источнику Tymoschuk играл с mafuta, Huba Buba с Transistor,
а полуфиналы были «mafuta — ectopower 2:4» и «Transistor — Memori 4:1». Centurion в кубке
не участвовал вовсе, а встреча «Cyneprepou4uk — Dune» и «Huba Buba — Cyneprepou4uk» пропали.

Сетка источника внутренне непротиворечива: посев 9–16 входит в 1/16, посев 5–8 в 1/8,
посев 1–4 в 1/4, и победитель каждой встречи играет в следующей. Прежняя сетка этому не
удовлетворяла: Romix и Centurion стояли в 1/4, не сыграв ни одной встречи 1/8.
"""

import csv
import importlib
import sys
from itertools import pairwise
from pathlib import Path

import pytest

from portal.cup_tables import HISTORIC_CUPS_DATA
from portal.names import clean_alias

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "data" / "gsheet_season6" / "1344056972.csv"

# Колонки листа: у каждого раунда своя тройка «посев, имя, счёт», пары стоят соседними строками.
ROUNDS = [
    ("1/16 финала", 0, 1, 5),
    ("1/8 финала", 7, 8, 12),
    ("1/4 финала", 14, 15, 19),
    ("1/2 финала", None, 22, 26),
    ("Финал", None, 29, 33),
]
PAIRS = [(5, 6), (8, 9), (11, 12), (14, 15)]
CUP = HISTORIC_CUPS_DATA["Season 6"]


def source_bracket():
    """Сетка листа: по две строки на встречу, посев подписан только у вошедшего в раунд."""
    with open(SHEET, encoding="utf-8-sig") as handle:
        raw = list(csv.reader(handle))
    out = []
    for tour, seed_col, name_col, score_col in ROUNDS:
        for top, bottom in PAIRS:
            a, b = raw[top], raw[bottom]
            left, right = a[name_col].strip(), b[name_col].strip()
            ls, rs = a[score_col].strip(), b[score_col].strip()
            if not (left and right and ls and rs):
                continue
            seeds = [row[seed_col].strip() for row in (a, b)] if seed_col is not None else ["", ""]
            out.append({"tour": tour, "p1": left, "p2": right, "s1": int(ls), "s2": int(rs),
                        "seeds": [int(s) for s in seeds if s]})
    return out


def meeting(g):
    """Встреча без ориентации: источник и справочник пишут стороны в разном порядке."""
    a, b = clean_alias(g["p1"]), clean_alias(g["p2"])
    sides = sorted([(a, g["s1"]), (b, g["s2"])])
    return (g["tour"], sides[0][0], sides[0][1], sides[1][0], sides[1][1])


def winner(g):
    return clean_alias(g["p1"] if g["s1"] > g["s2"] else g["p2"])


def test_сетка_справочника_совпадает_с_листом_источника():
    sheet = source_bracket()
    assert len(sheet) == 15
    assert len(CUP["matches"]) == len(sheet)
    assert {meeting(g) for g in CUP["matches"]} == {meeting(g) for g in sheet}


def test_каждая_встреча_источника_встречается_ровно_однажды():
    keys = [meeting(g) for g in CUP["matches"]]
    assert len(keys) == len(set(keys))


def test_посев_входит_в_свой_раунд():
    sheet = source_bracket()
    by_round = {}
    for g in sheet:
        by_round.setdefault(g["tour"], set()).update(g["seeds"])
    assert by_round["1/16 финала"] == set(range(9, 17))
    assert by_round["1/8 финала"] == {5, 6, 7, 8}
    assert by_round["1/4 финала"] == {1, 2, 3, 4}
    assert by_round["1/2 финала"] == set()
    assert by_round["Финал"] == set()


def test_победитель_каждой_встречи_играет_в_следующей():
    sheet = source_bracket()
    order = [r[0] for r in ROUNDS]
    for earlier, later in pairwise(order):
        winners = {winner(g) for g in sheet if g["tour"] == earlier}
        next_sides = {clean_alias(g[p]) for g in sheet if g["tour"] == later for p in ("p1", "p2")}
        assert winners <= next_sides, f"{earlier}: победители не прошли в {later}"


def test_в_сетке_ровно_шестнадцать_участников():
    sheet = source_bracket()
    players = {clean_alias(g[p]) for g in sheet for p in ("p1", "p2")}
    assert len(players) == 16
    assert "Centurion" not in players


def test_чемпион_и_финалист_это_стороны_финала():
    final = next(g for g in source_bracket() if g["tour"] == "Финал")
    assert (final["s1"], final["s2"]) == (5, 4)
    assert clean_alias(CUP["champion"]) == winner(final)
    assert clean_alias(CUP["runner_up"]) == clean_alias(
        final["p2"] if final["s1"] > final["s2"] else final["p1"])


def test_финал_сыгран_до_пяти_побед_а_остальные_раунды_до_трёх_и_четырёх():
    sheet = source_bracket()
    caps = {"1/16 финала": 3, "1/8 финала": 3, "1/4 финала": 4, "1/2 финала": 4, "Финал": 5}
    for g in sheet:
        assert max(g["s1"], g["s2"]) == caps[g["tour"]], g


def test_хроника_называет_5_4_счётом_серии_а_не_буллитов():
    """Комментарий 19008 темы 39660451 перечисляет девять ног; 5:4 — их итог.

    Прежняя хроника звала это «серией пенальти со счётом 5:4», хотя буллиты были 6:5 и 7:6
    и только в двух ничейных ногах. Хроника перекрывает `summary` карточки сезона
    (`prepare_site_data.enrich_recaps_with_chronicles`), поэтому сторожить надо её.
    """
    from tournament_chronicles_data import SEASONS_CHRONICLES

    chronicle = SEASONS_CHRONICLES["6"]
    text = " ".join([chronicle["summary"], chronicle["full_chronicle"], chronicle["era_title"]]
                    + chronicle["key_events"])
    legs = ["3:3", "1:4", "5:5", "4:5", "5:3", "2:4", "7:4", "8:1"]
    for leg in legs:
        assert leg in chronicle["full_chronicle"], f"нога {leg} пропала из хроники"
    assert chronicle["full_chronicle"].count("4:5") == 2
    assert "6:5" in text and "7:6" in text
    assert "девять ног" in text
    assert "пенальти 5:4" not in text and "5:4 по пенальти" not in text
    assert "серии пенальти со счетом 5:4" not in text


@pytest.fixture(scope="module")
def engine():
    """Сборочный модуль офлайн: секрет подменён пустым, соединение с ВК не проверяется."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("portal.env_file.secret", lambda name, path=None: "")
        patch.delitem(sys.modules, "build_final_analytics", raising=False)
        yield importlib.import_module("build_final_analytics")


def final_legs(engine):
    """Ноги финала Кубка Сезона 6 из рейтингового пула, в порядке источника."""
    return [m for m in engine.load_archived_matches()
            if m["season"] == "Season 6" and m["stage"] == "Финал Кубка"]


def test_ноги_финала_в_пуле_дают_серию_5_4(engine):
    """Комментарий 19008 и лист «Кубок 6» согласны: серия 5:4, ничьих в зачёте нет.

    Прежние строки хранили счёт основного времени (3:3 и 5:5) с признаком буллитов, а движок
    при равном счёте возвращает ничью независимо от серии — пул считал 3:4 и две ничьи.
    """
    legs = final_legs(engine)
    assert len(legs) == 9
    wins = {"ectoPower": 0, "Transistor": 0}
    for m in legs:
        assert m["s1"] != m["s2"], f"нога {m['s1']}:{m['s2']} осталась ничьей в зачёте"
        winner = m["p1"] if m["s1"] > m["s2"] else m["p2"]
        wins[clean_alias(winner)] += 1
    assert wins == {"ectoPower": 5, "Transistor": 4}


def test_буллитные_ноги_хранят_счёт_серии(engine):
    """Конвенция архива: счётом строки живёт серия буллитов, основное время — в комментарии."""
    legs = final_legs(engine)
    shootouts = [(m["s1"], m["s2"]) for m in legs if m["pk"]]
    assert shootouts == [(6, 5), (7, 6)]
    assert all(m["p1"] == "ectoPower" for m in legs if m["pk"])
    assert not any(m["ot"] for m in legs)


def test_встреча_ectoPower_Rock_это_четвертьфинал(engine):
    """Лист «Кубок 6»: ectopower—Rock 4:0 стоит в 1/4, а не в 1/2 (полуфинал — mafuta—ectopower)."""
    rows = [m for m in engine.load_archived_matches()
            if m["season"] == "Season 6" and {m["p1"], m["p2"]} == {"ectoPower", "Rock"}]
    assert len(rows) == 1
    assert rows[0]["stage"] == "1/4 финала"
    assert (rows[0]["s1"], rows[0]["s2"]) == (4, 0)