"""Medal tally, clean-sheet, clutch, style and longevity leaderboards."""

from collections import defaultdict

from portal.names import norm_medalist_name

MIN_HEAD_TO_HEAD_MATCHES = 3
MIN_CLUTCH_MATCHES = 3
SPECTACLE_MIN_MATCHES = 15
NO_MEDALS = {"gold": 0, "silver": 0, "bronze": 0, "finals": 0, "titles": []}

VETERANS_LONGEVITY = [
    {
        "player": "Kunio",
        "span": "2015 → 2026 (11 лет)",
        "matches": 190,
        "desc": "Бессменный титан Высшей лиги со дня основания сообщества.",
    },
    {
        "player": "Memori",
        "span": "2015 → 2026 (11 лет)",
        "matches": 175,
        "desc": "Архивариус и оплот лиги, участник всех официальных турниров.",
    },
    {
        "player": "ectoPower",
        "span": "2015 → 2026 (11 лет)",
        "matches": 210,
        "desc": "Главный рекордсмен лиги по матчам, победам и трофеям.",
    },
    {
        "player": "Ric25",
        "span": "2015 → 2026 (11 лет)",
        "matches": 163,
        "desc": "Ветеран 1-го сезона, прошедший через все дивизионы.",
    },
    {
        "player": "PacnyTHuK",
        "span": "2015 → 2026 (11 лет)",
        "matches": 89,
        "desc": "Один из лучших командных бойцов и кубковых триумфаторов.",
    },
    {
        "player": "WiSe",
        "span": "2015 → 2016 (1 сезон)",
        "matches": 18,
        "desc": "Бронзовый призёр исторического 1-го сезона NST.",
    },
    {
        "player": "Буц",
        "span": "2015 → 2026 (11 лет)",
        "matches": 115,
        "desc": "Первопроходец Сезона 1 (LiptOn) и бессменный ветеран всех 9 сезонов лиги.",
    },
]


def count_medals(seasons_list):
    """Gold, silver, bronze and final appearances from official championships and cups."""
    medals = defaultdict(lambda: {"gold": 0, "silver": 0, "bronze": 0, "finals": 0, "titles": []})
    for season in seasons_list:
        title = season.get("title") or season.get("name")
        for champion in str(season.get("champion") or "").split("/"):
            champion = norm_medalist_name(champion)
            if champion:
                medals[champion]["gold"] += 1
                medals[champion]["finals"] += 1
                medals[champion]["titles"].append(f"🥇 Чемпион {title}")
        runner_up = norm_medalist_name(season.get("runner_up"))
        if runner_up:
            medals[runner_up]["silver"] += 1
            medals[runner_up]["finals"] += 1
        third = norm_medalist_name(season.get("third_place"))
        if third:
            medals[third]["bronze"] += 1
        cup_winner = norm_medalist_name(season.get("cup_winner"))
        if cup_winner:
            medals[cup_winner]["gold"] += 1
            medals[cup_winner]["titles"].append(f"🏆 Кубок Лиги {title}")
    return medals


def season_matches(profile, skip_technical=True):
    matches = profile.get("match_history", [])
    return [
        m for m in matches if m.get("category") == "season" and not (skip_technical and m.get("is_technical"))
    ]


def _win_rate(tallies):
    return tallies["w"] / tallies["tot"]


def head_to_head_rivalries(matches):
    """The opponent a player fears most and the one they most beat."""
    stats = defaultdict(lambda: {"w": 0, "l": 0, "d": 0, "tot": 0})
    for m in matches:
        opponent = m.get("opponent")
        if not opponent:
            continue
        stats[opponent]["tot"] += 1
        result = m.get("result")
        key = "w" if result == "ПОБЕДА" else "l" if result == "ПОРАЖЕНИЕ" else "d"
        stats[opponent][key] += 1
    rivalries = [
        (name, tallies) for name, tallies in stats.items() if tallies["tot"] >= MIN_HEAD_TO_HEAD_MATCHES
    ]
    if not rivalries:
        return None, None
    kryptonite = min(rivalries, key=lambda x: (_win_rate(x[1]), -x[1]["tot"]))
    client = max(rivalries, key=lambda x: (_win_rate(x[1]), x[1]["tot"]))
    return _rivalry_row(kryptonite), _rivalry_row(client)


def _rivalry_row(rivalry):
    name, tallies = rivalry
    return {
        "name": name,
        "w": tallies["w"],
        "l": tallies["l"],
        "tot": tallies["tot"],
        "wr": round(tallies["w"] / tallies["tot"] * 100, 1),
    }


def enrich_profiles(profiles, medals):
    for p in profiles:
        p["medals"] = medals.get(p["player"], dict(NO_MEDALS))
        history = p.get("match_history", [])
        spectacle_pool = season_matches(p) or [m for m in history if not m.get("is_technical")]
        p["spectacle"] = _average_goals(spectacle_pool)
        p["kryptonite"], p["favorite_client"] = head_to_head_rivalries(history)


def _average_goals(matches):
    if not matches:
        return 0.0
    total = sum(m.get("score_for", 0) + m.get("score_against", 0) for m in matches)
    return round(total / len(matches), 2)


def clean_sheet_leaders(profiles):
    rows = []
    for p in profiles:
        matches = season_matches(p)
        shutouts = sum(
            1 for m in matches if m.get("score_against") == 0 and m.get("result") in ["ПОБЕДА", "ТП (ПОБЕДА)"]
        )
        if shutouts > 0:
            rows.append(
                {
                    "player": p["player"],
                    "clean_sheets": shutouts,
                    "matches": len(matches),
                    "avatar": p["avatar"],
                }
            )
    return sorted(rows, key=lambda x: x["clean_sheets"], reverse=True)[:8]


def clutch_leaders(profiles):
    rows = []
    for p in profiles:
        decided = [m for m in season_matches(p, skip_technical=False) if m.get("ot") or m.get("pk")]
        wins = sum(1 for m in decided if m.get("result") == "ПОБЕДА")
        losses = sum(1 for m in decided if m.get("result") == "ПОРАЖЕНИЕ")
        total = wins + losses
        if total >= MIN_CLUTCH_MATCHES:
            rows.append(
                {
                    "player": p["player"],
                    "ot_win_rate": round(wins / total * 100, 1),
                    "ot_wins": wins,
                    "ot_losses": losses,
                    "avatar": p["avatar"],
                }
            )
    return sorted(rows, key=lambda x: (x["ot_win_rate"], x["ot_wins"]), reverse=True)[:8]


def spectacle_leaders(profiles):
    """Most entertaining and most defensive players; both need a minimum of season matches."""
    rows = []
    for p in profiles:
        matches = season_matches(p)
        if len(matches) >= SPECTACLE_MIN_MATCHES:
            rows.append(
                {
                    "player": p["player"],
                    "spectacle": _average_goals(matches),
                    "matches": len(matches),
                    "avatar": p["avatar"],
                }
            )
    attacking = sorted(rows, key=lambda x: x["spectacle"], reverse=True)[:6]
    defensive = sorted(rows, key=lambda x: x["spectacle"])[:6]
    return attacking, defensive


def top_scorers(profiles):
    rows = []
    for p in profiles:
        matches = season_matches(p)
        if matches:
            goals = sum(m.get("score_for", 0) for m in matches)
            rows.append(
                {
                    "player": p["player"],
                    "goals_for": goals,
                    "matches": len(matches),
                    "gpg": round(goals / len(matches), 2),
                    "avatar": p["avatar"],
                }
            )
    return sorted(rows, key=lambda x: x["goals_for"], reverse=True)[:8]


def build(profiles: list, seasons_list: list) -> dict:
    medals = count_medals(seasons_list)
    enrich_profiles(profiles, medals)
    medal_leaders = sorted(
        [p for p in profiles if sum(p["medals"][key] for key in ("gold", "silver", "bronze")) > 0],
        key=lambda x: (
            x["medals"]["gold"],
            x["medals"]["silver"],
            x["medals"]["bronze"],
            x["medals"]["finals"],
        ),
        reverse=True,
    )
    spec_attacking, spec_defensive = spectacle_leaders(profiles)
    return {
        "medal_leaders": medal_leaders,
        "clean_sheet_leaders": clean_sheet_leaders(profiles),
        "clutch_leaders": clutch_leaders(profiles),
        "spec_attacking": spec_attacking,
        "spec_defensive": spec_defensive,
        "top_scorers_leaders": top_scorers(profiles),
        "veterans_longevity": VETERANS_LONGEVITY,
    }
