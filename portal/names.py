"""Normalisation and ordering helpers shared by every build stage."""

import re

from portal.name_tables import ALIAS_MAP, ALIAS_MAP_LOWER, PLAYER_CLEAN_MAP
from portal.roster_tables import SEASON_ROSTERS

PLAYER_ID_LINK = re.compile(r"\[id\d+\|([^\]]+)\]")
BRACKETED_TAG = re.compile(r"^\s*[\(\[]\s*[A-Za-z0-9_]{1,4}\s*[\)\]]")
BRACKETED_SUFFIX = re.compile(r"[\(\[]\s*[A-Za-z0-9_]{1,4}\s*[\)\]]\s*$")
TEAM_SUFFIX = re.compile(r"\s*\([^)]*\)")
CUP_STAGE_MARKERS = ("финал", "1/16", "1/8", "1/4", "1/2")
LEAGUE_MARKERS = (("Дворов", "Дворовая лига"), ("Средн", "Средняя лига"), ("Высш", "Высшая лига"))
MEDALIST_CANONICAL = {
    "ectopower": "ectoPower",
    "экто": "ectoPower",
    "mafuta": "mafuta",
    "мафута": "mafuta",
    "bop95": "BOР95",
    "вор95": "BOР95",
    "huba_buba": "Huba Buba",
    "huba buba": "Huba Buba",
    "huba_buba_5": "Huba Buba",
    "rvd": "RVD (МГБ)",
    "рвд": "RVD (МГБ)",
    "davitel": "Davitel",
    "давитель": "Davitel",
    "leon-udomlya": "leonudomlya",
    "леон": "leonudomlya",
    "centurion": "Centurion",
    "centzloy": "Centurion",
}


def clean_tok_name(s):
    """VK nickname to canonical form: strips mention markup, team tags and decoration."""
    if not s:
        return ""
    s = PLAYER_ID_LINK.sub(r"\1", str(s))
    s = BRACKETED_TAG.sub("", s)
    s = BRACKETED_SUFFIX.sub("", s)
    s = s.strip().strip("*.,_()[]-–:").lower()
    return PLAYER_CLEAN_MAP.get(s, s)


def clean_alias(name):
    """Nickname to canonical form, following the alias table and dropping team suffixes."""
    if not name:
        return name
    n = str(name).strip()
    if n in ALIAS_MAP:
        return ALIAS_MAP[n]
    if n.lower() in ALIAS_MAP_LOWER:
        return ALIAS_MAP_LOWER[n.lower()]
    if "(" in n and "мгб" not in n.lower():
        stripped = TEAM_SUFFIX.sub("", n).strip()
        # Рекурсия только когда хвост действительно снялся: незакрытая скобка («Rock (») не
        # меняет строку, а повторный вызов на ней ушёл бы в бесконечность.
        if stripped and stripped != n:
            return clean_alias(stripped)
    return n


def norm_season(s):
    """``"8 сезон"``/``"S8"`` to ``"Season 8"``; anything without a digit is kept as-is."""
    s = str(s).strip()
    digits = re.search(r"(\d+)", s)
    return f"Season {digits.group(1)}" if digits else s


def league_and_round(m, season_name, p1, p2):
    """League and round of a Sportcup row, falling back to the season roster."""
    tournament = str(m.get("tournament") or "")
    league = str(m.get("league") or "")
    stage = str(m.get("stage") or "")
    round_name = m.get("tour") or stage or "Регулярный сезон"

    is_cup = (
        "Кубок" in tournament
        or "Кубок" in league
        or m.get("is_playoff")
        or any(marker in stage.lower() for marker in CUP_STAGE_MARKERS)
    )
    if is_cup:
        return "Кубок лиг", stage if stage and stage != "Регулярный сезон" else "Кубок лиг"

    for marker, name in LEAGUE_MARKERS:
        if marker in tournament or marker in league:
            return name, round_name
    return _league_from_roster(season_name, p1, p2), round_name


def _league_from_roster(season_name, p1, p2):
    roster = SEASON_ROSTERS.get("8" if "8" in season_name else "9", {})
    divisions = {name: {x.lower().strip() for x in players} for name, players in roster.items()}
    both = p1.lower().strip(), p2.lower().strip()
    for division, nicknames in divisions.items():
        if all(player in nicknames for player in both):
            return division
    for division, nicknames in divisions.items():
        if any(player in nicknames for player in both):
            return division
    return "Высшая лига"


def match_sort_key(m):
    """Chronological order of a player's history; playoff and cup rows sort last within a season."""
    season_num = m.get("season_num", 999)
    stage = str(m.get("stage", ""))
    digits = re.findall(r"\d+", stage)
    if digits:
        tour_num = int(digits[0])
    elif any(word in stage.lower() for word in ("плей", "кубок", "финал")):
        tour_num = 150
    else:
        tour_num = 99
    return (season_num, tour_num, stage)


def profile_sort_order(p):
    return (0 if p["is_active"] else (1 if p["is_hall_of_fame"] else 2), -p["active_elo"], -p["matches"])


def norm_medalist_name(raw):
    if not raw:
        return ""
    raw = str(raw).strip()
    if "(" in raw and "мгб" not in raw.lower():
        raw = TEAM_SUFFIX.sub("", raw).strip()
    return MEDALIST_CANONICAL.get(raw.lower(), raw)
