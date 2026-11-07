"""Пакет А (решение владельца 2026-11-08): встреча в истории игрока — одна строка, сводка серии.

Кубок Сезонов 2–7 описан двумя списками: справочник `portal/cup_tables.py` даёт итог встречи
(«3:0», «4:2», «5:4»), а носитель комментариев — её ноги. Фильтр `without_mislabelled_cup_rows`
снимал ноги с таблиц сезона, но истории собирались ДО него, и одна встреча выглядела четырьмя
строками (3aBuCTb ↔ FC Pushistik, Сезон 4, 1/16: сводка 3:0 плюс ноги 2:1, 7:2, 4:3).

Второй дефект того же фильтра: он снимал всякую строку носителя с кубковым ярлыком, не проверяя,
есть ли чем её заменить. Ярлык «Плей-офф / Кубок» — подставка сборщика для строки, о которой
комментарий не назвал дивизион, а не доказательство кубка: 14 таких партий регулярки пропадали
со страницы молча. Теперь снятие доказано сводкой той же встречи.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.cup_tables import HISTORIC_CUPS_DATA
from portal.match_catalog import append_vk_playoff_comments
from portal.names import clean_alias
from portal.season_pages import is_cup_row, without_mislabelled_cup_rows


def test_строка_без_сводки_не_снимается_даже_с_кубковым_ярлыком():
    """Ярлык «Плей-офф / Кубок» — подставка сборщика, а не доказательство: сводки нет — игра остаётся.

    Комментарий называет тур («11 Тур»), но не дивизион, поэтому строка уходит в отчёт сборки
    неподтверждённой. Прежде фильтр принимал ярлык за факт и снимал игру совсем: так молча
    терялись 14 партий регулярки. Носитель при этом пишет «Регулярный чемпионат» — это его
    ярлык по умолчанию (908 строк из 938), доказательством он не является и не используется.
    """
    rows = [{"season": "Season 2", "stage": "Регулярный чемпионат", "p1": "mafuta",
             "p2": "FieryKelsen", "s1": 5, "s2": 3, "ot": False, "pk": False,
             "vk_text": "Досрочный матч. 11 Тур.\nmafuta - FieryKelsen - 5:3\n"
                        "FieryKelsen - mafuta - 6:8 PK"}]
    combined = []
    append_vk_playoff_comments(rows, combined, {})
    assert len(combined) == 1
    assert is_cup_row(combined[0]), "ярлык остался кубковым — проверка сторожит именно этот случай"
    assert without_mislabelled_cup_rows(combined) == combined


def test_нога_снимается_только_когда_сводка_той_же_встречи_есть():
    leg = {"season": "Season 4", "league": "Кубок лиг", "tour": "1/4 финала",
           "p1": "mafuta", "p2": "izzzotope", "s1": 4, "s2": 0, "source": "vk_comments_playoff"}
    summary = {"season": "Season 4", "league": "Кубок лиг", "tour": "1/4 финала",
               "p1": "mafuta", "p2": "izzzotope", "s1": 4, "s2": 0}
    assert without_mislabelled_cup_rows([leg, summary]) == [summary]
    assert without_mislabelled_cup_rows([leg]) == [leg]
    # Сводка другой встречи той же пары в другом сезоне не заменяет эту ногу.
    other = dict(summary, season="Season 5")
    assert without_mislabelled_cup_rows([leg, other]) == [leg, other]


def meeting(season, a, b, s1, s2):
    """Встреча без ориентации сторон: справочник и носитель пишут их вразнобой."""
    return (season, tuple(sorted([clean_alias(a) or a, clean_alias(b) or b])),
            tuple(sorted([s1, s2])))


def test_всякая_снятая_кубковая_нога_имеет_сводку(db_path):
    """Фильтр не имеет права снять встречу, которой нечем заменить: это потеряшка, а не дубль."""
    from db.catalog import catalog_from_db, cup_rows_from_db

    catalog, cup = catalog_from_db(db_path), cup_rows_from_db(db_path)
    summaries = {meeting(m["season"], m["p1"], m["p2"], m["s1"], m["s2"]) for m in cup}
    pairs = {(m["season"], tuple(sorted([clean_alias(m["p1"]) or m["p1"],
                                         clean_alias(m["p2"]) or m["p2"]]))) for m in cup}
    combined = catalog + cup
    dropped = [m for m in combined if m not in without_mislabelled_cup_rows(combined)]
    lost = [m for m in dropped
            if meeting(m["season"], m["p1"], m["p2"], m["s1"], m["s2"]) not in summaries
            and (m["season"], tuple(sorted([clean_alias(m["p1"]) or m["p1"],
                                            clean_alias(m["p2"]) or m["p2"]]))) not in pairs]
    assert not lost, f"снято без сводки: {[(m['season'], m['p1'], m['s1'], m['s2'], m['p2']) for m in lost]}"
    assert dropped, "фильтр перестал снимать ноги — проверка ничего не сторожит"


@pytest.fixture
def payload(db_path):
    """Payload страницы с копии базы: тот же код, что читает сайт и предпросмотр правки."""
    from portal.build_soccer import compose_payload

    return compose_payload(db_path)


def history(payload, player):
    return next(p for p in payload["profiles"] if p["player"] == player)["match_history"]


def cup_rows(payload, player, season, opponent):
    return [m for m in history(payload, player)
            if m["category"] == "cup" and m["season"] == season and m["opponent"] == opponent]


def test_встреча_со_сводкой_это_одна_строка_истории(payload):
    """3aBuCTb ↔ FC Pushistik, Сезон 4, 1/16: сводка 3:0, ноги 2:1, 7:2, 4:3 — одна встреча."""
    rows = cup_rows(payload, "3aBuCTb", "Season 4", "FC Pushistik")
    assert len(rows) == 1, (
        f"встреча показана {len(rows)} строками: "
        f"{[(m['stage'], m['score_for'], m['score_against']) for m in rows]}")
    assert (rows[0]["score_for"], rows[0]["score_against"]) == (3, 0)
    assert rows[0]["result"] == "ПОБЕДА"


def test_ноги_финала_кубка_не_удваивают_встречу_в_истории(payload):
    """Финал Кубка Сезона 6: девять ног в пуле, в истории — одна сводка 5:4."""
    rows = cup_rows(payload, "ectoPower", "Season 6", "Transistor")
    assert len(rows) == 1
    assert (rows[0]["score_for"], rows[0]["score_against"]) == (5, 4)


def test_сводка_без_ног_остаётся_одной_строкой(payload):
    """Transistor ↔ wanchous, Сезон 2, 1/16: ног в каталоге нет, сводка 3:0 обязана остаться."""
    rows = cup_rows(payload, "Transistor", "Season 2", "wanchous")
    assert len(rows) == 1
    assert (rows[0]["score_for"], rows[0]["score_against"]) == (3, 0)


def test_история_и_таблицы_сезона_показывают_одни_и_те_же_встречи(payload):
    """Один список кормит и карточки, и таблицы: кубковая строка истории обязана быть в таблице."""
    served = set()
    for season in payload["seasons"]:
        if season["name"] not in HISTORIC_CUPS_DATA:
            continue
        for m in season["matches"]:
            if "кубок" in str(m.get("league", "")).lower() or "кубок" in str(m.get("tour", "")).lower():
                served.add(meeting(season["name"], m["p1"], m["p2"], m["s1"], m["s2"]))
    missing = []
    for profile in payload["profiles"]:
        for m in profile["match_history"]:
            if m["category"] != "cup" or m["season"] not in HISTORIC_CUPS_DATA:
                continue
            key = meeting(m["season"], profile["player"], m["opponent"],
                          m["score_for"], m["score_against"])
            if key not in served:
                missing.append((profile["player"], m["season"], m["stage"], key[1], key[2]))
    assert not missing, f"в истории есть встречи, которых нет в таблице сезона: {missing[:8]}"