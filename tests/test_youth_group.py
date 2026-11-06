"""Молодёжный II: календарь группового этапа не теряет встречи.

Сводка источника даёт паре Den B. & Romix ноль встреч, ноль ног и ноль очков: команда снялась,
и её игры не зачтены никому. Две такие встречи выложены в комментарии и потому попали в базу как
«ТП обоим», а четыре не выкладывал никто — разборщик их не видел, и в Метеорах оставалось 17
встреч из 21. Витрина обязана показывать и несыгранное: строка с техническим результатом честнее,
чем дыра в календаре, о которой знает только лист источника.

Листы (`data/gsheet_youth/`) и тема обсуждений лежат в репозитории, поэтому тестам не нужна сеть.
"""

import json
from collections import defaultdict
from pathlib import Path

from db.import_live import YOUTH_SHEET
from portal.youth_sources import TOPIC_ID, group_stage

ROOT = Path(__file__).resolve().parent.parent
WITHDRAWN = ("Den B.", "Romix")


def stage():
    dump = max((ROOT / "data").glob("vk_dump_*"))
    comments = json.loads((dump / "comments" / f"{TOPIC_ID}.json").read_text(encoding="utf-8"))
    return group_stage(YOUTH_SHEET, comments["comments"])


def meetings(games):
    """Встреча — это пара команд в дивизионе: ноги одной встречи не должны считаться разными."""
    seen = defaultdict(set)
    for game in games:
        sides = frozenset({tuple(game["team_a"]), tuple(game["team_b"])})
        seen[game["division"]].add(sides)
    return seen


def test_every_calendar_meeting_reaches_the_showcase():
    """По семь команд в дивизионе — 21 встреча; календарь источника полон, база не должна быть пустее."""
    games, _ = stage()
    seen = meetings(games)
    assert len(seen["Кометы"]) == 21
    assert len(seen["Метеоры"]) == 21


def test_meetings_of_a_withdrawn_pair_are_technical_for_both_sides():
    """Снявшаяся пара не получает побед, и соперник тоже: зачтённой встречи не было ни у кого."""
    games, report = stage()
    rows = [game for game in games
            if WITHDRAWN in (tuple(game["team_a"]), tuple(game["team_b"]))]
    assert len(rows) == 6
    unplayed = [game for game in rows if game["score_text"].startswith("ТП обоим: встреча не сыграна")]
    assert len(unplayed) == 4
    for game in unplayed:
        assert game["tp"] is True
        assert game["counted"] is False
        assert game["outcome"] == ["none", "none"]
        assert game["score"] == [None, None]
        assert game["tour"] in ("Тур 1", "Тур 2", "Тур 3", "Тур 4")
        assert not game.get("review"), "решать нечего: сводка сама даёт паре ноль встреч"
    assert len(report["withdrawn"]) == 4


def test_published_legs_of_the_withdrawn_pair_keep_their_note():
    """Две выложенные встречи остаются как были: ноги в подписи есть, в зачёт они не идут."""
    games, _ = stage()
    rows = [game for game in games
            if WITHDRAWN in (tuple(game["team_a"]), tuple(game["team_b"]))
            and "ноги:" in game["score_text"]]
    assert len(rows) == 2
    for game in rows:
        assert game["tp"] is True
        assert game["counted"] is False
        assert game["comment_url"].endswith(("#post22505", "#post22534"))


def test_withdrawn_meetings_do_not_move_the_summary():
    """Ноль встреч в сводки остаётся нулём: несыгранное не должно дорисовывать таблице очки."""
    _, report = stage()
    assert report["totals"]["сходимость со сводкой"] == "полная"
    team = next(row for row in report["teams"] if row["team"] == " & ".join(WITHDRAWN))
    assert team["по_таблице"]["meetings"] == 0
    assert team["по_комментариям"]["meetings"] == 0