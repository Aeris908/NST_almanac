"""Season pages: purged pseudo-cup rows, season tables and special matches.

Игры Кубка лиг сюда приходят уже в списке `combined_matches` (см.
`portal/build_soccer.py: compose_payload`) — тогда они попадают и в таблицы сезона, и в
историю игрока, а не только в числа витрины.
"""

import re

from portal.cup_tables import HISTORIC_CUPS_DATA
from portal.names import clean_alias
from portal.roster_tables import SEASON_ROSTERS
from portal.vk_sources import enrich_vk_source

CUP_ROW_MARKERS = ("плей-офф", "кубок")
SCORE_PATTERN = r"(\d+)\s*[:\-]\s*(\d+)"


def is_cup_row(match):
    fields = (match.get("tour") or "", match.get("league") or "")
    return any(marker in field.lower() for field in fields for marker in CUP_ROW_MARKERS)


def meeting_key(match):
    """Встреча без ориентации сторон: справочник и носитель пишут их вразнобой."""
    return (match.get("season"),
            tuple(sorted([clean_alias(match["p1"]) or match["p1"],
                          clean_alias(match["p2"]) or match["p2"]])))


def without_mislabelled_cup_rows(combined_matches):
    """Снимает ноги кубковой встречи, у которой есть проверенная сводка; без сводки — оставляет.

    Сводка приходит из справочника `portal/cup_tables.py` (`db/catalog.py: cup_rows_from_db`),
    и ключа `source` у неё нет — этим она и отличается от строки носителя. Раньше фильтр снимал
    всякую подписанную плей-оффом строку носителя Seasons 2–7, не проверяя, есть ли чем её
    заменить: 14 партий, ошибочно подписанных «Плей-офф / Кубок», пропадали со страницы молча,
    потому что сводки у них не было. Теперь снятие доказано сводкой той же встречи.
    """
    summaries = {meeting_key(m) for m in combined_matches if not m.get("source")}
    return [m for m in combined_matches
            if not (m.get("source") and m.get("season") in HISTORIC_CUPS_DATA and is_cup_row(m)
                    and meeting_key(m) in summaries)]


def attach_matches_and_podiums(seasons_list, combined_matches):
    for season in seasons_list:
        name = season["name"]
        season["matches"] = [m for m in combined_matches if m.get("season") == name]
        season["total_goals"] = sum(m["s1"] + m["s2"] for m in season["matches"])
        cup = HISTORIC_CUPS_DATA.get(name)
        if cup:
            if not season.get("podium"):
                season["podium"] = {}
            season["podium"]["cup_winner"] = cup.get("champion")
            season["podium"]["cup_runner_up"] = cup.get("runner_up")


def complete_match_row(match, title, category):
    """Fill in the season, league, stage and scores a special-tournament row is missing."""
    row = dict(match)
    if not row.get("season"):
        row["season"] = title
    if not row.get("league"):
        row["league"] = category
    if not row.get("stage"):
        row["stage"] = row.get("tour") or "Матч"
    if "s1" not in row or "s2" not in row or row.get("s1") is None:
        # Счёт — только то, что стоит в начале ячейки: «2:2 (РК 3:4)» это 2:2, а строка
        # «счёт ног не опубликован; по сводке — 4 ноги у …» не счёт вовсе, и ловить в ней
        # цифры поиском по всей строке значит рисовать голы там, где их не было.
        scores = re.match(SCORE_PATTERN, str(row.get("score", "")).strip())
        row["s1"] = int(scores.group(1)) if scores else 0
        row["s2"] = int(scores.group(2)) if scores else 0
    return row


def special_match_rows(special_tournaments, vk_sources_lookup):
    rows = []
    for tournament in special_tournaments:
        title = tournament.get("title") or "Спецтурнир"
        category = tournament.get("category") or tournament.get("game") or "Спецтурнир"
        for m in tournament.get("matches", []):
            row = complete_match_row(m, title, category)
            rows.append(enrich_vk_source(row, vk_sources_lookup))
    return rows


def build(data, combined_matches: list, profiles: list) -> dict:
    seasons_list = data.seasons_data
    for match in combined_matches:
        enrich_vk_source(match, data.vk_sources_lookup)

    combined_matches = without_mislabelled_cup_rows(combined_matches)
    attach_matches_and_podiums(seasons_list, combined_matches)

    active_count = sum(1 for p in profiles if p["is_active"])
    inactive_count = sum(1 for p in profiles if not p["is_active"])
    print(
        f"Profiles finalized: {len(profiles)} total "
        f"(Active: {active_count}, Inactive/Legends: {inactive_count})"
    )

    return {
        "seasons_list": seasons_list,
        "combined_matches": combined_matches,
        "season_rosters": SEASON_ROSTERS,
        "special_matches": special_match_rows(data.special_tournaments, data.vk_sources_lookup),
        "active_count": active_count,
        "inactive_count": inactive_count,
    }
