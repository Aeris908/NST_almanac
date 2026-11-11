"""Per-player match history and win-type tallies across every tournament branch."""

import re
from collections import defaultdict

from portal.names import clean_alias, match_sort_key
from portal.vk_sources import enrich_vk_source

VK_FIELDS = ("vk_url", "video_url", "vk_text", "vk_date", "vk_page")
# Исход стороны, который база хранит отдельно от счёта: нога может кончиться вничью по голам
# и всё равно иметь победителя — его решает серия буллитов (`db/import_stores.py: import_league`).
RESULT_BY_OUTCOME = {"win": "ПОБЕДА", "loss": "ПОРАЖЕНИЕ", "draw": "НИЧЬЯ"}


def parse_scores(raw_score):
    """``"3:1"`` to ``(3, 1)``, or ``None`` when the score is missing or malformed."""
    parsed = parse_score_cell(raw_score)
    return parsed[:2] if parsed else None


def parse_score_cell(raw_score):
    """Ячейка счёта целиком: ``(s1, s2, серия_a, серия_b)`` или None.

    Молодёжный записывает ногу с серией в той же ячейке — «1:1 (PK 2:3)», «3:3 (4:3 PK)».
    Прежний разбор на `split(":")` на такой ячейке падал, а `None` по ней значило бы «игры
    нет», хотя игра есть: исход её решает серия, и в истории игрока она обязана идти победой
    или поражением, а не ничьей. Серию смотрим только когда основные счётники равны — иначе
    «(Тур 9)» и «6-5(ПК)» дали бы пенальтийную там, где нога кончилась в основном времени.
    """
    text = str(raw_score or "").strip()
    match = re.match(r"^(\d+)\s*[:\-]\s*(\d+)", text)
    if not match:
        return None
    scores = [int(match.group(1)), int(match.group(2))]
    if scores[0] == scores[1]:
        tail = re.findall(r"(\d{1,2})\s*[:\-]\s*(\d{1,2})", text[match.end():])
        if tail:
            scores += [int(tail[0][0]), int(tail[0][1])]
    return scores


def result_of(score_for, score_against, series=None):
    if series and score_for == score_against:
        return "ПОБЕДА" if series[0] > series[1] else "ПОРАЖЕНИЕ"
    if score_for > score_against:
        return "ПОБЕДА"
    if score_for < score_against:
        return "ПОРАЖЕНИЕ"
    return "НИЧЬЯ"


def parse_pair(raw_team):
    """Split a 2x2 team string on ``&`` or ``/`` and clean both nicknames."""
    separator = "&" if "&" in raw_team else "/" if "/" in raw_team else None
    members = raw_team.split(separator) if separator else [raw_team]
    return [name for name in (clean_alias(member) for member in members) if name]


def match_record(
    *,
    category,
    cat_label,
    tournament,
    season,
    season_num,
    stage,
    league,
    partner,
    opponent,
    score_for,
    score_against,
    result,
    ot,
    pk,
):
    return {
        "category": category,
        "cat_label": cat_label,
        "tournament": tournament,
        "season": season,
        "season_num": season_num,
        "stage": stage,
        "league": league,
        "partner": partner,
        "opponent": opponent,
        "score_for": score_for,
        "score_against": score_against,
        "result": result,
        "ot": ot,
        "pk": pk,
    }


def add_season_records(player_matches, addon, m):
    # Имя в историю идёт каноническим: справочник кубка помнит «LiptOn» и «Tymoschuk», а архив —
    # «Буц» и «Bubnov». Без сверки игрок заводился бы двумя строками (92 профиля становились 98).
    # Таблицу сезона это не касается: там остаётся написание источника.
    p1, p2 = clean_alias(m["p1"]) or m["p1"], clean_alias(m["p2"]) or m["p2"]
    s1, s2 = m["s1"], m["s2"]
    ot, pk = m.get("ot", False), m.get("pk", False)
    season = m.get("season", "Season 1")
    digits = re.findall(r"\d+", season)
    s_num = int(digits[0]) if digits else 1
    league = m.get("league", "Высшая лига")
    # Игра Кубка лиг — не матч чемпионата: в истории она подписывается кубком (как спецтурниры),
    # и в сезонные лидеры не попадает. Раньше кубок в историю не шёл вовсе, хотя в таблицы
    # сезона и в общие числа витрины входил, — один и тот же матч считался и не считался.
    is_cup = "кубок" in league.lower()
    is_tech = m.get("is_technical", False) or m.get("is_forfeit", False)
    tech_loser = m.get("technical_loser") if is_tech else None
    decided = m.get("outcome")

    if is_tech:
        p1_res = "ТП (ПОРАЖЕНИЕ)" if p1 == tech_loser else "ТП (ПОБЕДА)"
        p2_res = "ТП (ПОРАЖЕНИЕ)" if p2 == tech_loser else "ТП (ПОБЕДА)"
    elif decided:
        p1_res, p2_res = (RESULT_BY_OUTCOME[outcome] for outcome in decided)
    else:
        p1_res, p2_res = result_of(s1, s2), result_of(s2, s1)

    common = {
        "category": "cup" if is_cup else "season",
        "cat_label": "🏆 Кубок лиг" if is_cup else f"🏆 Сезон {s_num}",
        "tournament": f"Кубок лиг (Сезон {s_num})" if is_cup else f"Официальный Чемпионат (Сезон {s_num})",
        "season": season,
        "season_num": s_num + 0.5 if is_cup else s_num,
        "stage": m.get("stage") or m.get("tour") or "Матч",
        "league": league,
        "ot": ot,
        "pk": pk,
    }
    for player, opponent, score_for, score_against, outcome in (
        (p1, p2, s1, s2, p1_res),
        (p2, p1, s2, s1, p2_res),
    ):
        record = match_record(
            partner=None,
            opponent=opponent,
            score_for=score_for,
            score_against=score_against,
            result=outcome,
            **common,
        )
        if is_tech:
            record["is_technical"] = True
            record["note"] = m.get("note", "Техническое поражение (снят с турнира)")
        record.update({field: m[field] for field in VK_FIELDS if m.get(field)})
        player_matches[player].append(record)

    if is_tech:
        if tech_loser in (p1, p2):
            winner = p2 if tech_loser == p1 else p1
            addon[tech_loser]["tech_l"] = addon[tech_loser].get("tech_l", 0) + 1
            addon[winner]["reg_w"] += 1
    elif s1 > s2:
        tally_winnable_match(addon, p1, p2, pk=pk, ot=ot)
    elif s2 > s1:
        tally_winnable_match(addon, p2, p1, pk=pk, ot=ot)
    elif decided:
        # Ничья по голам, решённая серией: в зачёт идёт победитель серии, а не ничья обеим.
        winner, loser = (p1, p2) if decided[0] == "win" else (p2, p1)
        tally_winnable_match(addon, winner, loser, pk=pk, ot=ot)
    else:
        addon[p1]["draws"] += 1
        addon[p2]["draws"] += 1


def tally_winnable_match(addon, winner, loser, *, pk, ot):
    kind = "pk" if pk else "ot" if ot else "reg"
    addon[winner][f"{kind}_w"] += 1
    addon[loser][f"{kind}_l"] += 1


def special_category(title):
    """Tournament kind and label, resolved in the same order as the archive titles."""
    lowered = title.lower()
    if "пенальт" in lowered:
        return "penalty", "🥅 Пенальти"
    if "межсез" in lowered or "клубн" in lowered:
        return "club", "🏖️ Межсезонье"
    if "молодёж" in lowered:
        return "youth", "🌱 Молодёжка"
    if "блиц" in lowered:
        return "blitz", "⚡ Блиц"
    return "special", "⚡ Спецтурнир"


def add_special_records(player_matches, t_idx, t, vk_sources_lookup):
    title = t.get("title", "Спецтурнир")
    category, cat_label = special_category(title)
    is_penalty_tournament = "пенальт" in title.lower()
    for m in t.get("matches", []):
        cell = parse_score_cell(m.get("score", ""))
        if not m.get("p1") or not m.get("p2") or cell is None:
            continue
        s1, s2 = cell[:2]
        series = tuple(cell[2:]) if len(cell) > 2 else None
        # Молодёжный чемпионат играется парами («lenin1st & ectoPower»), блиц — один на один.
        # Раньше пара целиком считалась «игроком», а `league_players` пропускает имена с «&»:
        # восемь игр молодёжки числились в таблицах и в общей статистике, но не попадали
        # ни в одну карточку. Разбивка стороны на игроков это и чинит; для 1×1 всё как было.
        sides = [parse_pair(m["p1"]), parse_pair(m["p2"])]
        if not all(sides) or sides[0] == sides[1]:
            continue
        names = [" & ".join(side) for side in sides]
        source = enrich_vk_source(
            {"p1": names[0], "p2": names[1], "s1": s1, "s2": s2, "season": title}, vk_sources_lookup
        )
        common = {
            "category": category,
            "cat_label": cat_label,
            "tournament": title,
            "season": t.get("season_year", "Спецтурнир"),
            "season_num": 100 + t_idx,
            "stage": m.get("stage") or m.get("tour") or "Матч",
            "league": m.get("league", "Спецтурнир"),
            "ot": False,
            "pk": bool(is_penalty_tournament or m.get("pk", False) or series),
        }
        for members, other, score_for, score_against, own_series in (
            (sides[0], sides[1], s1, s2, series),
            (sides[1], sides[0], s2, s1, tuple(reversed(series)) if series else None),
        ):
            for player in members:
                record = match_record(
                    partner=" & ".join(name for name in members if name != player) or None,
                    opponent=" & ".join(other),
                    score_for=score_for,
                    score_against=score_against,
                    result=result_of(score_for, score_against, own_series),
                    **common,
                )
                for field in ("vk_url", "video_url"):
                    if source.get(field):
                        record[field] = source[field]
                player_matches[player].append(record)


def add_team_records(player_matches, t_idx, t):
    title = t.get("title", "Командный чемпионат")
    for m in (t.get("matches") or t.get("playoff_matches") or []):
        scores = parse_scores(m.get("score", ""))
        if not m.get("t1") or not m.get("t2") or scores is None:
            continue
        s1, s2 = scores
        common = {
            "category": "team",
            "cat_label": "👥 2х2 Командник",
            "tournament": title,
            "season": t.get("season_year", "Командный 2х2"),
            "season_num": 200 + t_idx,
            "stage": m.get("stage") or m.get("tour") or "Матч 2х2",
            "league": m.get("league", "Командная лига"),
            "ot": False,
            "pk": False,
        }
        for side, opponent_side, score_for, score_against in (
            (parse_pair(m["t1"]), m["t2"], s1, s2),
            (parse_pair(m["t2"]), m["t1"], s2, s1),
        ):
            for player in side:
                record = match_record(
                    partner=" & ".join(x for x in side if x != player) or None,
                    opponent=opponent_side,
                    score_for=score_for,
                    score_against=score_against,
                    result=result_of(score_for, score_against),
                    **common,
                )
                player_matches[player].append(record)


def build(data, combined_matches: list) -> tuple:
    player_matches = defaultdict(list)
    player_stats_addon = defaultdict(
        lambda: {
            "reg_w": 0,
            "ot_w": 0,
            "pk_w": 0,
            "reg_l": 0,
            "ot_l": 0,
            "pk_l": 0,
            "draws": 0,
        }
    )
    for m in combined_matches:
        add_season_records(player_matches, player_stats_addon, m)
    for t_idx, t in enumerate(data.special_tournaments):
        add_special_records(player_matches, t_idx, t, data.vk_sources_lookup)
    for t_idx, t in enumerate(data.team_tournaments):
        add_team_records(player_matches, t_idx, t)
    for history in player_matches.values():
        history.sort(key=match_sort_key)
    return player_matches, player_stats_addon
