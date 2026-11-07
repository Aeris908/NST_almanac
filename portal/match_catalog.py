"""Merge the four archived match sources into one verified league calendar."""

from portal.comment_origin import origin_of, shootout_of
from portal.names import clean_alias, league_and_round, norm_season
from portal.vk_sources import enrich_vk_source

# Куда попадает строка-комментарий, о которой источник ничего не говорит: то же самое, что было
# до распознавания. Меняет её только человек в редакторе — по ссылке на комментарий.
UNPROVEN_LEAGUE = "Высшая лига"
UNPROVEN_TOUR = "Плей-офф / Кубок"
# Что носитель умеет говорить о строке сам, когда архивный указатель её не знает.
CARRIER_PROVENANCE = ("source_ref", "vk_url", "vk_text")


def from_early_archive(early_matches):
    """Season 1 rows: the only source for the inaugural championship."""
    rows = []
    for m in early_matches:
        s = norm_season(m.get("season", ""))
        if s != "Season 1":
            continue
        p1 = clean_alias(m.get("p1"))
        p2 = clean_alias(m.get("p2"))
        if not p1 or not p2 or p1 == p2:
            continue
        rows.append(
            {
                "season": s,
                "league": m.get("league", "Высшая (Единая) лига"),
                "tour": m.get("tour", "1 Круг"),
                "stage": m.get("stage", "1 Круг"),
                "p1": p1,
                "p2": p2,
                "s1": int(m.get("s1", 0)),
                "s2": int(m.get("s2", 0)),
                "ot": m.get("ot", False),
                "pk": m.get("pk", False),
                "source": "season_1_archive",
            }
        )
    return rows


def from_wiki_calendars(wiki_matches):
    """Seasons 2-7 rows from the official community wiki calendars (max two per pairing)."""
    rows = []
    seen = set()
    for m in wiki_matches:
        s = norm_season(m.get("season", ""))
        p1 = clean_alias(m.get("p1"))
        p2 = clean_alias(m.get("p2"))
        if not p1 or not p2 or p1 == p2:
            continue
        s1 = int(m.get("s1", 0))
        s2 = int(m.get("s2", 0))
        league = m.get("league", "Высшая лига")
        tour = m.get("tour", "1 Тур")
        ot = m.get("ot", False)
        pairing = (s, league, tour, min(p1, p2), max(p1, p2))
        repeats = sum(1 for x in seen if x[:5] == pairing)
        if repeats >= 2:
            continue
        seen.add((*pairing, repeats, s1, s2))
        rows.append(
            {
                "season": s,
                "league": league,
                "tour": tour,
                "stage": tour,
                "p1": p1,
                "p2": p2,
                "s1": s1,
                "s2": s2,
                "ot": ot,
                "pk": ot,
                "source": m.get("source", "vk_wiki"),
            }
        )
    return rows


def from_sportcup_api(base_matches):
    """Seasons 8-9 rows; technical results come straight from the source flags."""
    rows = []
    for m in base_matches:
        s = norm_season(m.get("season", ""))
        if s not in ["Season 8", "Season 9"]:
            continue
        p1 = clean_alias(m.get("p1"))
        p2 = clean_alias(m.get("p2"))
        if not p1 or not p2 or p1 == p2:
            continue
        match_league, match_tour = league_and_round(m, s, p1, p2)
        is_tech = bool(m.get("is_technical") or m.get("is_forfeit"))
        row = {
            "season": s,
            "league": match_league,
            "tour": match_tour,
            "stage": match_tour,
            "p1": p1,
            "p2": p2,
            "s1": int(m.get("s1", 0)),
            "s2": int(m.get("s2", 0)),
            "ot": m.get("ot", False),
            "pk": m.get("pk", False),
            "source": "sportcup_api",
            "is_technical": is_tech,
            "is_forfeit": is_tech,
            "note": m.get("note", ""),
        }
        if is_tech:
            row["technical_loser"] = clean_alias(m.get("technical_loser"))
        rows.append(row)
    return rows


def append_vk_playoff_comments(vk_matches, combined_matches, sources_lookup):
    """Playoff and cup rows recovered from VK comment threads.

    Rows are appended straight into ``combined_matches`` because every new row has
    to be deduplicated against the rows accepted before it.

    Лигу и тур строка берёт у источника (`portal.comment_origin`), а не из подставки: общий
    ярлык «Высшая лига / Плей-офф / Кубок» и ставил игру в чужой контейнер, и снимал её со
    страницы сезона фильтром псевдо-кубковых строк. Возвращает строки, для которых
    доказательства нет — они остаются как были и уходят в отчёт сборки.
    """
    unproven = []
    for m in vk_matches:
        s = norm_season(m.get("season", ""))
        p1 = clean_alias(m.get("p1"))
        p2 = clean_alias(m.get("p2"))
        if not p1 or not p2 or p1 == p2:
            continue
        s1 = int(m.get("s1", 0))
        s2 = int(m.get("s2", 0))
        # Повтор сторожит счёт, а не число встреч: кубковая серия играется до трёх, четырёх и
        # пяти побед — это до девяти ног. Прежняя обрезка «не больше четырёх встреч на пару»
        # теряла последние ноги серии (#86: в 1/4 Кубка Сезона 5 у RVD (МГБ) — ectoPower
        # пропали 4:3 и 4:4), а сводка 4:2 лежала рядом и делала потерю невидимой.
        already_known = any(
            x["season"] == s and {x["p1"], x["p2"]} == {p1, p2}
            and (x["s1"], x["s2"]) in {(s1, s2), (s2, s1)}
            for x in combined_matches
        )
        if already_known:
            continue
        enrich_vk_source(m, sources_lookup)
        origin = origin_of(m.get("stage"), m.get("vk_text"), s1, s2)
        tour = origin[1] if origin else UNPROVEN_TOUR
        if not origin:
            unproven.append({"season": s, "p1": p1, "p2": p2, "s1": s1, "s2": s2,
                             "stage": m.get("stage"), "vk_url": m.get("vk_url")})
        row = {
            "season": s,
            "league": origin[0] if origin else UNPROVEN_LEAGUE,
            "tour": tour,
            "stage": tour,
            "p1": p1,
            "p2": p2,
            "s1": s1,
            "s2": s2,
            "ot": m.get("ot", False),
            "pk": bool(m.get("pk") or shootout_of(m.get("vk_text"), s1, s2)),
            "source": "vk_comments_playoff",
        }
        # Архивный указатель строку не нашёл, но носитель помнит её собственную ссылку на
        # комментарий (`collectors/vk_row_sources.py`): без неё в карточке проверки сверять
        # нечего, а счёт такой строки человек правит вслепую.
        for field in CARRIER_PROVENANCE:
            if m.get(field):
                row[field] = m[field]
        combined_matches.append(row)
    return unproven


def build(data) -> list:
    combined_matches = [
        *from_early_archive(data.early_matches),
        *from_wiki_calendars(data.wiki_matches),
        *from_sportcup_api(data.base_matches),
    ]
    unproven = append_vk_playoff_comments(data.vk_matches, combined_matches, data.vk_sources_lookup)
    print(f"Total verified combined matches: {len(combined_matches)}")
    if unproven:
        print(f"Комментарных строк без доказательства лиги и тура: {len(unproven)}")
        for row in unproven:
            link = f" {row['vk_url']}" if row.get("vk_url") else " источника нет"
            print(f"  {row['season']} {row['p1']} {row['s1']}:{row['s2']} {row['p2']}"
                  f" (пометка носителя: {row['stage']}){link}")
    for match in combined_matches:
        enrich_vk_source(match, data.vk_sources_lookup)
    return combined_matches
