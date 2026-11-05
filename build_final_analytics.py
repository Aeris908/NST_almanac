"""Collect the Goal 3 match pool, rate it with Elo and export the master table plus dashboard."""

import json
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

sys.stdout.reconfigure(encoding="utf-8")

from portal.env_file import secret  # noqa: E402

VK_METHOD_URL = "https://api.vk.com/method/{method}"
VK_GROUP_GET_METHOD = "groups.getById"
VK_GROUP_SLUG = "nekketsu"
VK_GROUP_NAME_FALLBACK = "NEKKETSU SPORTS TOURNAMENTS"
SPORTCUP_GAMES_URL = "https://sportcup.org/rest/public/tournaments/{uuid}/games?stageId=1"
SPORTCUP_SNAPSHOT_PATH = Path("data/sportcup_games.json")
HTTP_TIMEOUT_SECONDS = 10
SPORTCUP_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
URLLIB_FALLBACK_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Read from the environment (see .env.example); without it the build stays offline
# and the group name falls back to the constant above.
VK_API_TOKEN = secret("VK_API_TOKEN")
API_VERSION = "5.199"
GROUP_ID = 66162180

COMMUNITY_NAME = "NEKKETSU SPORTS TOURNAMENTS"
COMMUNITY_URL = "https://vk.ru/nekketsu"
GAME_TITLE = "Kunio-kun no Nekketsu Soccer League (Goal 3)"
# This module writes the analytics snapshot behind the Markdown dashboard. The master table
# the site reads (nekketsu_master_table.json, at the repo root) is regenerated from the same
# match pool by build_master_table.py — see portal/master_table.py for its rating model.
ANALYTICS_TABLE_PATH = Path("data/analytics_master_table.json")
# Override to reproduce the pool before the Season 8 corrections (point at a missing file
# to disable them entirely) — used by the parity check in the migration to a database.
DECISIONS_PATH = Path(os.environ.get("SPORTCUP_DECISIONS", "data/sportcup_decisions.json"))
DASHBOARD_PATH = Path("nekketsu_dashboard.md")
GENERATION_DATE = "2026-10-24"
TOP_DOMINATORS_LIMIT = 10
MIN_MATCHES_FOR_DEFENSIVE = 30

SEASON_8 = "Season 8"
SEASON_9 = "Season 9"
CUP_TOURNAMENT = "Кубок лиг"
REGULAR_STAGE = "Регулярный сезон"
TECHNICAL_DEFEAT_NOTE = "Техническое поражение (снят с турнира)"

NAME_MAP = {
    "ectopower": "ectoPower",
    "ecto": "ectoPower",
    "pacnythuk": "PacnyTHuK",
    "распутник": "PacnyTHuK",
    "распутhuk": "PacnyTHuK",
    "1путин": "PacnyTHuK",
    "1putin": "PacnyTHuK",
    "1-путин": "PacnyTHuK",
    "1_путин": "PacnyTHuK",
    "kunio": "Kunio",
    "кунио": "Kunio",
    "mafuta": "mafuta",
    "мафута": "mafuta",
    "transistor": "Transistor",
    "транзистор": "Transistor",
    "romix": "Romix",
    "ромикс": "Romix",
    "ric25": "Ric25",
    "рик25": "Ric25",
    "рик": "Ric25",
    "rock": "Rock",
    "рок": "Rock",
    "fc rock": "Rock",
    "leonudomlya": "leonudomlya",
    "леонудомля": "leonudomlya",
    "aeris": "Aeris",
    "аэрис": "Aeris",
    "knucklesss": "Aeris",
    "knuckles": "Aeris",
    "наклз": "Aeris",
    "наклс": "Aeris",
    "izzzotope": "izzzotope",
    "изотоп": "izzzotope",
    "jamlight": "Jamlight",
    "джамлайт": "Jamlight",
    "буц": "Буц",
    "buts": "Буц",
    "kubik": "Kubik",
    "кубик": "Kubik",
    "memori": "Memori",
    "мемори": "Memori",
    "hanter": "Hanter",
    "хантер": "Hanter",
    "ryumaru": "Ryumaru",
    "рюмару": "Ryumaru",
    "yoxter": "yoxter",
    "йокстер": "yoxter",
    "dune": "Dune",
    "дюна": "Dune",
    "дюныч": "Dune",
    "k-r": "Kubik",
    "к-р": "Kubik",
    "k_r": "Kubik",
    "kr": "Kubik",
    "sokol": "Sokol",
    "сокол": "Sokol",
    "yuliy_cezar": "Yuliy_Cezar",
    "juliy_cezar": "Yuliy_Cezar",
    "juliy cezar": "Yuliy_Cezar",
    "juliycezar": "Yuliy_Cezar",
    "cezar": "Yuliy_Cezar",
    "цезарь": "Yuliy_Cezar",
    "ruby": "ruby",
    "руби": "ruby",
    "taeda": "Taeda",
    "таеда": "Taeda",
    "таёда": "Taeda",
    "кирпич57": "Кирпич57",
    "кирпич": "Кирпич57",
    "kirpich": "Кирпич57",
    "fc pushistik": "FC Pushistik",
    "пушистик": "FC Pushistik",
    "cyneprepou4uk": "Cyneprepou4uk",
    "супергеройчик": "Cyneprepou4uk",
    "e_not": "E_not",
    "енот": "E_not",
    "romol": "Romol",
    "ромол": "Romol",
    "lipton": "Буц",
    "липтон": "Буц",
    "lipt0n": "Буц",
    "lipt-on": "Буц",
    "LiptOn": "Буц",
    "kipriot": "Kipriot",
    "киприот": "Kipriot",
    "centurion": "Centurion",
    "сenturion": "Centurion",
    "цент": "Centurion",
    "centzloy": "Centurion",
    "flash": "Flash",
    "флэш": "Flash",
    "wanchous": "wanchous",
    "ванчоус": "wanchous",
    "rash": "RASH",
    "раш": "RASH",
    "spartacus": "Spartacus",
    "спартакус": "Spartacus",
    "mikr84": "mikr84",
    "микр": "mikr84",
    "микр84": "mikr84",
    "веселый роджер": "Веселый Роджер",
    "роджер": "Веселый Роджер",
    "frzz": "frzz",
    "blanco": "ruby",
    "blanko": "ruby",
    "бланко": "ruby",
    "daz": "daz",
    "texas": "Texas",
    "rvd": "RVD (МГБ)",
    "мгб": "RVD (МГБ)",
    "xakofear": "RVD (МГБ)",
    "fierykelsen": "RVD (МГБ)",
    "fierykeles": "RVD (МГБ)",
    "fieryrvd": "RVD (МГБ)",
    "fiery": "RVD (МГБ)",
    "exyxea": "RVD (МГБ)",
    "ехухеа": "RVD (МГБ)",
    "tubustd": "tubustd",
    "high": "high",
    "3abuctb": "3aBuCTb",
    "stalin": "Stalin",
    "сталин": "Stalin",
    "chocopie": "Chocopie",
    "aoshi": "Aoshi",
    "аоши": "Aoshi",
    "greyson": "Greyson",
    "грейсон": "Greyson",
    "tymoschuk": "Tymoschuk",
    "тимощук": "Tymoschuk",
    "dynamik": "dynamik",
    "kot-from-ussr": "kot-from-ussr",
    "palka palych": "Palka Palych",
    "дядюшка ау": "Дядюшка АУ",
    "armfly": "ArmFly",
    "dopi": "Dopi",
    "bop95": "BOР95",
    "exponat": "eXponat",
    "dr1n": "Dr1N",
    "vasya1995": "Vasya1995",
    "lenin1st": "Lenin1st",
    "bigplay": "BigPlay",
    "tbp_machiavelli": "TBP_Machiavelli",
    "сахарок": "Сахарок",
    "gagagatch": "gagagatch",
}


def norm(name):
    """Canonical spelling of a nickname, or the trimmed input when it is unmapped."""
    if not name:
        return "Unknown"
    clean = str(name).strip().lower()
    return NAME_MAP.get(clean, str(name).strip())


T_CONFIGS = [
    # Season 8 (Regular stage)
    {"season": "Season 8", "league": "Дворовая", "uuid": "9748124e-86ad-45b1-b422-20bbd62bef28"},
    {"season": "Season 8", "league": "Средняя", "uuid": "5500f1f3-db8b-400e-9838-1f90981db281"},
    {"season": "Season 8", "league": "Высшая", "uuid": "307e8c45-b9ed-4eb3-906f-0c7437d3fb72"},
    # Season 9 (Regular stage)
    {"season": "Season 9", "league": "Дворовая", "uuid": "yafdgnksyar7"},
    {"season": "Season 9", "league": "Средняя", "uuid": "gf5x4lz3wxgf"},
    {"season": "Season 9", "league": "Высшая", "uuid": "vpe8isci7oea"},
]


def http_get_json(url, headers=None, timeout=HTTP_TIMEOUT_SECONDS):
    """Fetch JSON through requests when installed, otherwise through urllib; None on failure."""
    if requests is not None:
        try:
            response = requests.get(url, headers=headers or {}, timeout=timeout)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
    try:
        req = urllib.request.Request(url, headers=headers or URLLIB_FALLBACK_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def call_vk(method, params):
    """Call one VK API method and return its payload, or an empty dict on any error."""
    try:
        request_params = params.copy()
        if VK_API_TOKEN:
            request_params["access_token"] = VK_API_TOKEN
        request_params["v"] = API_VERSION
        url = VK_METHOD_URL.format(method=method) + "?" + urllib.parse.urlencode(request_params)
        data = http_get_json(url, timeout=HTTP_TIMEOUT_SECONDS)
        return data if data else {}
    except Exception:
        return {}


def verify_vk_connection():
    """Probe the VK group the comment archives live in and log its public name."""
    if not VK_API_TOKEN:
        print(f"VK API token not set, skipping the group check (ID: {GROUP_ID})")
        return
    print("Verifying VK API connection...")
    group_info = call_vk(VK_GROUP_GET_METHOD, {"group_id": VK_GROUP_SLUG})
    groups = (group_info.get("response") or {}).get("groups") or [{}]
    group_name = groups[0].get("name", VK_GROUP_NAME_FALLBACK)
    print(f"Connected to VK Group: {group_name} (ID: {GROUP_ID})")


def load_sportcup_snapshot():
    """Frozen Sportcup responses (see collectors/sportcup sync tool); empty when absent."""
    if not SPORTCUP_SNAPSHOT_PATH.exists():
        return {}
    snapshot = json.loads(SPORTCUP_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    return {stage["uuid"]: stage.get("response") for stage in snapshot["stages"]}


def fetch_sportcup_games(config, snapshot):
    """Raw games of one stage: from the snapshot, live only when the snapshot lacks it."""
    if config["uuid"] in snapshot:
        return snapshot[config["uuid"]]
    response = http_get_json(
        SPORTCUP_GAMES_URL.format(uuid=config["uuid"]),
        headers=SPORTCUP_HEADERS,
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    if not response:
        raise RuntimeError(
            f"Sportcup не отдал {config['season']} {config['league']} ({config['uuid']}), "
            f"этого стейджа нет ни в снапшоте, ни в сети. Сборка прервана, чтобы не "
            f"опубликовать часть лиги; обновите снапшот: python collectors/sync_sportcup.py"
        )
    return response


@dataclass(frozen=True)
class SportcupDecisions:
    """Editorial decisions about ambiguous Sportcup rows, kept in data/sportcup_decisions.json."""

    voided: frozenset = frozenset()
    played_as_normal: frozenset = frozenset()
    notes: dict = None

    def __post_init__(self):
        if self.notes is None:
            object.__setattr__(self, "notes", {})


def load_sportcup_decisions():
    """Read which unfinished fixtures are dropped and which technical rows get a custom note."""
    if not DECISIONS_PATH.exists():
        print(f"Warning: {DECISIONS_PATH} not found, every FINAL row stays in the pool.")
        return SportcupDecisions()
    raw = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    return SportcupDecisions(
        voided=frozenset(item["uuid"] for item in raw.get("void", [])),
        played_as_normal=frozenset(item["uuid"] for item in raw.get("played_as_normal", [])),
        notes={item["uuid"]: item["note"] for item in raw.get("technical_note_override", [])},
    )


def technical_loser_of(game):
    """Raw title of the side that lost on technical grounds, or None when the source names no winner."""
    winner = game.get("winner")
    if not winner:
        return None
    for side in (game["member1"], game["member2"]):
        if side.get("uuid") != winner:
            return side.get("title")
    return None


def fetch_sportcup_matches(configs):
    """Load every finished game of the configured Sportcup stages."""
    snapshot = load_sportcup_snapshot()
    print(f"Loading Sportcup matches from "
          f"{SPORTCUP_SNAPSHOT_PATH if snapshot else 'the live API'}...")
    decisions = load_sportcup_decisions()
    matches = []
    voided = 0
    for config in configs:
        data = fetch_sportcup_games(config, snapshot)
        for game in data.get("list", []):
            if game.get("resultStatus") != "FINAL":
                continue
            uuid = game.get("uuid")
            if uuid in decisions.voided:
                voided += 1
                continue
            p1 = norm(game["member1"]["title"])
            p2 = norm(game["member2"]["title"])
            s1 = game["scoreMember1"]
            s2 = game["scoreMember2"]
            if s1 is None or s2 is None:
                continue
            # technicalWin без названного победителя — это «не играли», а не чьё-то поражение:
            # технический результат присваиваем только когда источник указал, кто выиграл.
            loser = norm(technical_loser_of(game))
            is_technical = loser is not None and bool(game.get("technicalWin")) \
                and uuid not in decisions.played_as_normal
            matches.append(
                {
                    "season": config["season"],
                    "tournament": f"{config['season']} {config['league']} лига",
                    "stage": REGULAR_STAGE,
                    "p1": p1,
                    "p2": p2,
                    "s1": int(s1),
                    "s2": int(s2),
                    "ot": game.get("overtimeWin", False),
                    "pk": game.get("afterGameWin", False),
                    "is_playoff": False,
                    "is_technical": is_technical,
                    "is_forfeit": is_technical,
                    "technical_loser": loser if is_technical else None,
                    "note": decisions.notes.get(uuid, TECHNICAL_DEFEAT_NOTE) if is_technical else "",
                    "source": "sportcup_api",
                    "source_ref": uuid,
                }
            )
    print(f"Sportcup matches loaded: {len(matches)}"
          + (f" (снято с зачёта как несыгранных: {voided})" if voided else ""))
    return matches


KR_MATCHES = [
    ("frzz", "Kubik", 2, 1, False, False, "Season 9", "Средняя лига"),
    ("Kubik", "frzz", 5, 2, False, False, "Season 9", "Средняя лига"),
    ("Yuliy_Cezar", "Kubik", 4, 1, False, False, "Season 9", "Средняя лига"),
    ("Yuliy_Cezar", "Kubik", 1, 0, True, False, "Season 9", "Средняя лига"),
    ("Kubik", "yoxter", 2, 1, False, False, "Season 9", "Средняя лига"),
    ("Kubik", "yoxter", 3, 1, False, False, "Season 9", "Средняя лига"),
    ("Kubik", "Dune", 4, 2, False, False, "Season 9", "Средняя лига"),
    ("Kubik", "Dune", 4, 1, False, False, "Season 9", "Средняя лига"),
]

S8_PLAYOFFS = [
    # 1/16
    ("Sokol", "E_not", 2, 0, False, False, "1/16 финала"),
    ("Sokol", "E_not", 3, 1, False, False, "1/16 финала"),
    ("Sokol", "E_not", 3, 2, False, False, "1/16 финала"),
    ("Буц", "yoxter", 0, 1, False, False, "1/16 финала"),
    ("Буц", "yoxter", 4, 0, False, False, "1/16 финала"),
    ("Буц", "yoxter", 2, 1, False, False, "1/16 финала"),
    ("Буц", "yoxter", 3, 0, False, False, "1/16 финала"),
    # 1/8
    ("Sokol", "Ric25", 3, 1, False, False, "1/8 финала"),
    ("Sokol", "Ric25", 3, 2, False, False, "1/8 финала"),
    ("Sokol", "Ric25", 5, 2, True, False, "1/8 финала"),
    ("Буц", "leonudomlya", 3, 1, False, False, "1/8 финала"),
    # 1/4
    ("Kunio", "Sokol", 0, 1, False, False, "1/4 финала"),
    ("Kunio", "Sokol", 5, 0, False, False, "1/4 финала"),
    ("Kunio", "Sokol", 5, 4, False, True, "1/4 финала"),
    ("Kunio", "Sokol", 2, 0, False, False, "1/4 финала"),
    ("Kunio", "Sokol", 2, 1, True, False, "1/4 финала"),
    ("ectoPower", "Memori", 4, 0, False, False, "1/4 финала"),
    ("ectoPower", "Memori", 4, 1, False, False, "1/4 финала"),
    ("ectoPower", "Memori", 5, 1, False, False, "1/4 финала"),
    ("ectoPower", "Memori", 9, 0, False, False, "1/4 финала"),
    ("Romix", "Cyneprepou4uk", 4, 2, False, False, "1/4 финала"),
    ("Romix", "Cyneprepou4uk", 3, 5, False, False, "1/4 финала"),
    ("Romix", "Cyneprepou4uk", 4, 1, False, False, "1/4 финала"),
    ("Romix", "Cyneprepou4uk", 5, 3, False, False, "1/4 финала"),
    ("Romix", "Cyneprepou4uk", 6, 3, False, True, "1/4 финала"),
    ("PacnyTHuK", "Буц", 4, 1, False, False, "1/4 финала"),
    # 1/2
    ("PacnyTHuK", "Kunio", 1, 0, False, False, "1/2 финала"),
    ("PacnyTHuK", "Kunio", 1, 0, False, False, "1/2 финала"),
    ("PacnyTHuK", "Kunio", 5, 4, False, False, "1/2 финала"),
    ("Kunio", "PacnyTHuK", 3, 2, False, False, "1/2 финала"),
    ("Kunio", "PacnyTHuK", 2, 1, False, False, "1/2 финала"),
    ("ectoPower", "Romix", 5, 4, False, False, "1/2 финала"),
    ("ectoPower", "Romix", 3, 2, False, False, "1/2 финала"),
    ("ectoPower", "Romix", 4, 3, False, False, "1/2 финала"),
    ("Romix", "ectoPower", 3, 2, False, False, "1/2 финала"),
    ("ectoPower", "Romix", 4, 4, False, True, "1/2 финала"),
    # Grand Final Season 8
    ("ectoPower", "PacnyTHuK", 3, 1, False, False, "Финал"),
    ("ectoPower", "PacnyTHuK", 4, 2, False, False, "Финал"),
    ("PacnyTHuK", "ectoPower", 3, 1, False, False, "Финал"),
    ("PacnyTHuK", "ectoPower", 4, 0, False, False, "Финал"),
    ("ectoPower", "PacnyTHuK", 1, 0, False, False, "Финал"),
    ("PacnyTHuK", "ectoPower", 6, 1, False, False, "Финал"),
    ("PacnyTHuK", "ectoPower", 4, 2, False, False, "Финал"),
    ("PacnyTHuK", "ectoPower", 2, 1, False, False, "Финал"),
]

S9_PLAYOFFS = [
    # 1/16
    ("Jamlight", "Taeda", 2, 0, False, False, "1/16 финала"),
    ("Hanter", "Dune", 3, 2, False, False, "1/16 финала"),
    ("Kubik", "ruby", 3, 1, False, False, "1/16 финала"),
    ("Yuliy_Cezar", "Ryumaru", 2, 0, False, False, "1/16 финала"),
    ("Yuliy_Cezar", "Ryumaru", 5, 2, False, True, "1/16 финала"),
    ("Yuliy_Cezar", "Ryumaru", 2, 1, False, False, "1/16 финала"),
    # 1/8
    ("Ric25", "Hanter", 3, 0, False, False, "1/8 финала"),
    ("leonudomlya", "Kubik", 3, 2, False, False, "1/8 финала"),
    ("Aeris", "Yuliy_Cezar", 3, 1, False, False, "1/8 финала"),
    ("Memori", "Jamlight", 3, 1, False, False, "1/8 финала"),
    # 1/4
    ("ectoPower", "leonudomlya", 4, 0, False, False, "1/4 финала"),
    ("Romix", "Aeris", 4, 0, False, False, "1/4 финала"),
    ("Kunio", "Memori", 4, 2, False, False, "1/4 финала"),
    ("Rock", "Ric25", 4, 1, False, False, "1/4 финала"),
    # 1/2
    ("Rock", "Kunio", 4, 1, False, False, "1/2 финала"),
    ("ectoPower", "Romix", 4, 0, False, False, "1/2 финала"),
    # Grand Final Season 9
    ("ectoPower", "Rock", 5, 0, False, False, "Финал"),
]

HISTORICAL_MATCHES = [
    # Season 4
    ("mafuta", "Transistor", 4, 2, False, False, "Season 4", "Финал Кубка"),
    ("Transistor", "Kipriot", 4, 1, False, False, "Season 4", "1/2 финала"),
    ("mafuta", "Буц", 4, 2, False, False, "Season 4", "1/2 финала"),
    ("mafuta", "izzzotope", 4, 0, False, False, "Season 4", "1/4 финала"),
    ("Kipriot", "ectoPower", 4, 3, False, False, "Season 4", "1/4 финала"),
    ("Transistor", "Kunio", 4, 0, False, False, "Season 4", "1/4 финала"),
    ("Буц", "Ric25", 4, 3, False, False, "Season 4", "1/4 финала"),
    # Season 5
    ("RVD (МГБ)", "PacnyTHuK", 5, 2, False, False, "Season 5", "Финал Кубка"),
    ("RVD (МГБ)", "mafuta", 5, 2, False, False, "Season 5", "1/2 финала"),
    ("mafuta", "RVD (МГБ)", 8, 5, False, False, "Season 5", "1/2 финала"),
    ("RVD (МГБ)", "mafuta", 9, 5, False, False, "Season 5", "1/2 финала"),
    ("mafuta", "RVD (МГБ)", 5, 2, False, False, "Season 5", "1/2 финала"),
    ("mafuta", "RVD (МГБ)", 8, 5, False, False, "Season 5", "1/2 финала"),
    ("RVD (МГБ)", "mafuta", 5, 4, False, False, "Season 5", "1/2 финала"),
    ("PacnyTHuK", "izzzotope", 4, 2, False, False, "Season 5", "1/2 финала"),
    ("RVD (МГБ)", "ectoPower", 4, 2, False, False, "Season 5", "1/4 финала"),
    ("mafuta", "LiptOn", 4, 1, False, False, "Season 5", "1/4 финала"),
    ("PacnyTHuK", "FC Pushistik", 4, 0, False, False, "Season 5", "1/4 финала"),
    ("izzzotope", "Romix", 4, 1, False, False, "Season 5", "1/4 финала"),
    # Season 6 Epic Series
    ("ectoPower", "Transistor", 3, 3, False, True, "Season 6", "Финал Кубка"),
    ("Transistor", "ectoPower", 4, 1, False, False, "Season 6", "Финал Кубка"),
    ("ectoPower", "Transistor", 5, 5, False, True, "Season 6", "Финал Кубка"),
    ("Transistor", "ectoPower", 5, 4, False, False, "Season 6", "Финал Кубка"),
    ("Transistor", "ectoPower", 5, 4, False, False, "Season 6", "Финал Кубка"),
    ("ectoPower", "Transistor", 5, 3, False, False, "Season 6", "Финал Кубка"),
    ("Transistor", "ectoPower", 4, 2, False, False, "Season 6", "Финал Кубка"),
    ("ectoPower", "Transistor", 7, 4, False, False, "Season 6", "Финал Кубка"),
    ("ectoPower", "Transistor", 8, 1, False, False, "Season 6", "Финал Кубка"),
    ("ectoPower", "Rock", 4, 0, False, False, "Season 6", "1/2 финала"),
    ("Transistor", "Memori", 4, 1, False, False, "Season 6", "1/2 финала"),
    # Season 7 Key Playoff
    ("RVD (МГБ)", "ectoPower", 4, 2, False, False, "Season 7", "Финал Кубка"),
    ("RVD (МГБ)", "mafuta", 4, 1, False, False, "Season 7", "1/2 финала"),
    ("ectoPower", "Romix", 4, 1, False, False, "Season 7", "1/2 финала"),
    ("ectoPower", "leonudomlya", 4, 1, False, False, "Season 7", "1/4 финала"),
    ("mafuta", "E_not", 4, 2, False, False, "Season 7", "1/4 финала"),
]


def _regular_match(season, league, p1, p2, s1, s2, ot, pk):
    """Regular-stage fixture recovered from the VK comments."""
    return {
        "season": season,
        "tournament": f"{season} {league}",
        "stage": REGULAR_STAGE,
        "p1": norm(p1),
        "p2": norm(p2),
        "s1": s1,
        "s2": s2,
        "ot": ot,
        "pk": pk,
        "is_playoff": False,
    }


def _cup_match(season, stage, p1, p2, s1, s2, ot, pk):
    """Cup knockout tie recovered from the VK comments."""
    return {
        "season": season,
        "tournament": f"{season} {CUP_TOURNAMENT}",
        "stage": stage,
        "p1": norm(p1),
        "p2": norm(p2),
        "s1": s1,
        "s2": s2,
        "ot": ot,
        "pk": pk,
        "is_playoff": True,
    }


def load_archived_matches():
    """Manual fixtures Sportcup does not cover, appended in the historical ingestion order."""
    matches = []
    for i, (p1, p2, s1, s2, ot, pk, season, league) in enumerate(KR_MATCHES):
        row = _regular_match(season, league, p1, p2, s1, s2, ot, pk)
        row.update({"source": "manual", "source_ref": f"KR_MATCHES#{i}"})
        matches.append(row)
    for i, (p1, p2, s1, s2, ot, pk, stage) in enumerate(S8_PLAYOFFS):
        row = _cup_match(SEASON_8, stage, p1, p2, s1, s2, ot, pk)
        row.update({"source": "manual", "source_ref": f"S8_PLAYOFFS#{i}"})
        matches.append(row)
    for i, (p1, p2, s1, s2, ot, pk, stage) in enumerate(S9_PLAYOFFS):
        row = _cup_match(SEASON_9, stage, p1, p2, s1, s2, ot, pk)
        row.update({"source": "manual", "source_ref": f"S9_PLAYOFFS#{i}"})
        matches.append(row)
    for i, (p1, p2, s1, s2, ot, pk, season, stage) in enumerate(HISTORICAL_MATCHES):
        row = _cup_match(season, stage, p1, p2, s1, s2, ot, pk)
        row.update({"source": "manual", "source_ref": f"HISTORICAL_MATCHES#{i}"})
        matches.append(row)
    return matches


def fetch_all_matches():
    """Full match pool: live Sportcup data plus the archived fixtures."""
    matches = fetch_sportcup_matches(T_CONFIGS)
    matches.extend(load_archived_matches())
    print(f"Total comprehensive match dataset: {len(matches)} games.")
    return matches


# Elo model: FIDE-style expectation with a heavier K for playoffs and for young accounts.
INITIAL_ELO = 1500
ELO_RATING_SCALE = 400.0
ELO_K_PLAYOFF = 32
ELO_K_REGULAR = 24
ELO_K_LEARNING_WINDOW = 15
DECISIVE_WIN_SCORE = 1.0
DECISIVE_LOSS_SCORE = 0.0
OVERTIME_WIN_SCORE = 0.75
OVERTIME_LOSS_SCORE = 0.25
DRAW_SCORE = 0.5

# Dominator Score weights.
ELO_DOMINATOR_WEIGHT = 1.5
WIN_RATE_DOMINATOR_WEIGHT = 3.5
MAJOR_TITLE_DOMINATOR_WEIGHT = 50
MINOR_TITLE_DOMINATOR_WEIGHT = 20
MAJOR_FINAL_DOMINATOR_WEIGHT = 15
GOAL_DIFF_DOMINATOR_WEIGHT = 0.35
GAMES_PLAYED_DOMINATOR_WEIGHT = 0.25

H2H_KEY_PLAYERS = [
    "ectoPower",
    "PacnyTHuK",
    "Kunio",
    "Romix",
    "mafuta",
    "Sokol",
    "Буц",
    "Yuliy_Cezar",
    "Rock",
    "Ric25",
]

# Season honours per player: league titles, cup titles, minor titles, major finals, Hall of Fame, tier label.
# NOTE: "Kubik" is listed twice in the source table; the later row wins and that is what the portal shows.
TitleRecord = namedtuple("TitleRecord", "premier cup minor finals hall_of_fame tier")
TITLES = {
    "ectoPower": TitleRecord(4, 2, 0, 9, True, "GOAT (Tier S+)"),
    "mafuta": TitleRecord(3, 4, 0, 8, True, "Legend / Dynasty (Tier S+)"),
    "Kunio": TitleRecord(2, 0, 0, 4, True, "Apex Veteran (Tier S)"),
    "PacnyTHuK": TitleRecord(0, 1, 0, 3, True, "Clutch Giant (Tier S)"),
    "RVD (МГБ)": TitleRecord(0, 2, 0, 2, True, "Playoff Slayer (Tier S)"),
    "Transistor": TitleRecord(1, 0, 0, 3, True, "Elite Champion (Tier A+)"),
    "Sokol": TitleRecord(0, 0, 1, 0, False, "Phenom (Tier A+)"),
    "Буц": TitleRecord(0, 0, 0, 0, False, "Heavyweight (Tier A)"),
    "Romix": TitleRecord(0, 0, 0, 0, True, "Stalwart / Iron Contender (Tier A)"),
    "Yuliy_Cezar": TitleRecord(0, 0, 0, 0, False, "Rising Force (Tier A)"),
    "Hanter": TitleRecord(0, 0, 1, 0, False, "Division Conqueror (Tier A)"),
    "Rock": TitleRecord(0, 0, 0, 1, True, "Grand Finalist (Tier A)"),
    "Ric25": TitleRecord(0, 0, 0, 0, True, "Premier Mainstay (Tier A-)"),
    "leonudomlya": TitleRecord(0, 0, 1, 0, False, "Veteran Fighter (Tier B+)"),
    "Aeris": TitleRecord(0, 0, 0, 0, True, "Veteran Fighter (Tier B+)"),
    "Jamlight": TitleRecord(0, 0, 1, 0, True, "Division Champion (Tier B+)"),
    "Memori": TitleRecord(0, 0, 0, 0, True, "Organizer & Player (Tier B)"),
    "Dune": TitleRecord(0, 0, 0, 0, False, "Division Fighter (Tier B)"),
    "Kubik": TitleRecord(0, 0, 0, 0, False, "Tactical Challenger (Tier B)"),
}

UNRANKED_TITLE_RECORD = TitleRecord(0, 0, 0, 0, False, "Challenger")


@dataclass
class PlayerRatings:
    """Per-player aggregates accumulated while replaying the match pool."""

    elo: dict
    peak_elo: dict
    lowest_elo: dict
    matches_played: dict
    wins: dict
    losses: dict
    goals_for: dict
    goals_against: dict
    clean_sheets: dict
    playoff_wins: dict
    playoff_losses: dict
    head_to_head: dict


def _result_scores(s1, s2, ot, pk):
    """Elo target scores of both sides: draws split a point, overtime/penalty wins weigh 0.75."""
    if s1 == s2:
        return DRAW_SCORE, DRAW_SCORE
    if ot or pk:
        winner_score, loser_score = OVERTIME_WIN_SCORE, OVERTIME_LOSS_SCORE
    else:
        winner_score, loser_score = DECISIVE_WIN_SCORE, DECISIVE_LOSS_SCORE
    return (winner_score, loser_score) if s1 > s2 else (loser_score, winner_score)


def build_player_ratings(matches):
    """Replay the pool in order and accumulate Elo ratings, tallies and head-to-head records."""
    elo = defaultdict(lambda: INITIAL_ELO)
    peak_elo = defaultdict(lambda: INITIAL_ELO)
    lowest_elo = defaultdict(lambda: INITIAL_ELO)
    matches_played = defaultdict(int)
    wins = defaultdict(int)
    losses = defaultdict(int)
    goals_for = defaultdict(int)
    goals_against = defaultdict(int)
    clean_sheets = defaultdict(int)
    playoff_wins = defaultdict(int)
    playoff_losses = defaultdict(int)
    head_to_head = defaultdict(lambda: defaultdict(lambda: {"w": 0, "l": 0, "gf": 0, "ga": 0}))

    for match in matches:
        p1 = match["p1"]
        p2 = match["p2"]
        s1 = match["s1"]
        s2 = match["s2"]
        is_playoff = match["is_playoff"]

        matches_played[p1] += 1
        matches_played[p2] += 1
        goals_for[p1] += s1
        goals_against[p1] += s2
        goals_for[p2] += s2
        goals_against[p2] += s1

        if s2 == 0:
            clean_sheets[p1] += 1
        if s1 == 0:
            clean_sheets[p2] += 1

        head_to_head[p1][p2]["gf"] += s1
        head_to_head[p1][p2]["ga"] += s2
        head_to_head[p2][p1]["gf"] += s2
        head_to_head[p2][p1]["ga"] += s1

        if s1 > s2:
            wins[p1] += 1
            losses[p2] += 1
            head_to_head[p1][p2]["w"] += 1
            head_to_head[p2][p1]["l"] += 1
            if is_playoff:
                playoff_wins[p1] += 1
                playoff_losses[p2] += 1
        elif s2 > s1:
            wins[p2] += 1
            losses[p1] += 1
            head_to_head[p2][p1]["w"] += 1
            head_to_head[p1][p2]["l"] += 1
            if is_playoff:
                playoff_wins[p2] += 1
                playoff_losses[p1] += 1

        score1, score2 = _result_scores(s1, s2, match["ot"], match["pk"])

        r1 = elo[p1]
        r2 = elo[p2]
        e1 = 1.0 / (1.0 + 10.0 ** ((r2 - r1) / ELO_RATING_SCALE))
        e2 = 1.0 / (1.0 + 10.0 ** ((r1 - r2) / ELO_RATING_SCALE))

        is_inexperienced = (
            matches_played[p1] < ELO_K_LEARNING_WINDOW or matches_played[p2] < ELO_K_LEARNING_WINDOW
        )
        k = ELO_K_PLAYOFF if (is_playoff or is_inexperienced) else ELO_K_REGULAR

        elo[p1] = round(r1 + k * (score1 - e1), 1)
        elo[p2] = round(r2 + k * (score2 - e2), 1)

        peak_elo[p1] = max(peak_elo[p1], elo[p1])
        peak_elo[p2] = max(peak_elo[p2], elo[p2])
        lowest_elo[p1] = min(lowest_elo[p1], elo[p1])
        lowest_elo[p2] = min(lowest_elo[p2], elo[p2])

    return PlayerRatings(
        elo=elo,
        peak_elo=peak_elo,
        lowest_elo=lowest_elo,
        matches_played=matches_played,
        wins=wins,
        losses=losses,
        goals_for=goals_for,
        goals_against=goals_against,
        clean_sheets=clean_sheets,
        playoff_wins=playoff_wins,
        playoff_losses=playoff_losses,
        head_to_head=head_to_head,
    )


def _dominator_score(ratings, player, win_rate, titles, goal_diff, games_played):
    """Composite ranking value: Elo lead over baseline, win rate, silverware and goal difference."""
    major_titles = titles.premier + titles.cup
    return round(
        (ratings.elo[player] - INITIAL_ELO) * ELO_DOMINATOR_WEIGHT
        + win_rate * WIN_RATE_DOMINATOR_WEIGHT
        + major_titles * MAJOR_TITLE_DOMINATOR_WEIGHT
        + titles.minor * MINOR_TITLE_DOMINATOR_WEIGHT
        + titles.finals * MAJOR_FINAL_DOMINATOR_WEIGHT
        + goal_diff * GOAL_DIFF_DOMINATOR_WEIGHT
        + games_played * GAMES_PLAYED_DOMINATOR_WEIGHT,
        1,
    )


def build_leaderboard(ratings):
    """One row per tracked player, ordered by Elo and then by Dominator Score."""
    leaderboard = []
    for player, games_played in ratings.matches_played.items():
        victories = ratings.wins[player]
        goals_for = ratings.goals_for[player]
        goals_against = ratings.goals_against[player]
        goal_diff = goals_for - goals_against
        win_rate = round((victories / games_played) * 100, 1) if games_played > 0 else 0
        goals_per_game = round(goals_for / games_played, 2) if games_played > 0 else 0
        conceded_per_game = round(goals_against / games_played, 2) if games_played > 0 else 0
        titles = TITLES.get(player, UNRANKED_TITLE_RECORD)
        leaderboard.append(
            {
                "player": player,
                "tier": titles.tier,
                "elo": ratings.elo[player],
                "peak_elo": ratings.peak_elo[player],
                "lowest_elo": ratings.lowest_elo[player],
                "matches": games_played,
                "wins": victories,
                "losses": ratings.losses[player],
                "win_rate": win_rate,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goal_diff": goal_diff,
                "gpg": goals_per_game,
                "gapg": conceded_per_game,
                "clean_sheets": ratings.clean_sheets[player],
                "playoff_wins": ratings.playoff_wins[player],
                "playoff_losses": ratings.playoff_losses[player],
                "premier_titles": titles.premier,
                "cup_titles": titles.cup,
                "minor_titles": titles.minor,
                "total_titles": titles.premier + titles.cup + titles.minor,
                "major_finals": titles.finals,
                "hall_of_fame": titles.hall_of_fame,
                "dominator_score": _dominator_score(
                    ratings, player, win_rate, titles, goal_diff, games_played
                ),
            }
        )

    leaderboard.sort(key=lambda row: (row["elo"], row["dominator_score"]), reverse=True)
    return leaderboard


def build_head_to_head_matrix(ratings):
    """Win-loss balance of the headline rivalries, as `w-l (gf:ga)` strings."""
    matrix = {}
    for player in H2H_KEY_PLAYERS:
        matrix[player] = {}
        for rival in H2H_KEY_PLAYERS:
            if player == rival:
                continue
            record = ratings.head_to_head[player][rival]
            if record["w"] + record["l"] > 0:
                matrix[player][rival] = f"{record['w']}-{record['l']} ({record['gf']}:{record['ga']})"
            else:
                matrix[player][rival] = "-"
    return matrix


CHAMPIONSHIP_CHRONOLOGY = [
    {
        "season": "Season 1",
        "year": "2015",
        "league_champion": "mafuta",
        "cup_winner": "mafuta",
        "format": "Mednafen NES 1x1",
    },
    {
        "season": "Season 2",
        "year": "2016",
        "league_champion": "mafuta",
        "cup_winner": "mafuta",
        "runner_up": "ectoPower",
    },
    {
        "season": "Season 3",
        "year": "2016",
        "league_champion": "mafuta",
        "cup_winner": "mafuta",
        "runner_up": "ectoPower",
        "third_place": "Ric25",
    },
    {
        "season": "Season 4",
        "year": "2017",
        "league_champion": "Transistor",
        "cup_winner": "mafuta",
        "runner_up": "mafuta",
        "third_place": "ectoPower",
    },
    {
        "season": "Season 5",
        "year": "2017",
        "league_champion": "ectoPower",
        "cup_winner": "RVD (МГБ)",
        "cup_finalist": "PacnyTHuK",
    },
    {
        "season": "Season 6",
        "year": "2018",
        "league_champion": "ectoPower",
        "cup_winner": "ectoPower",
        "cup_finalist": "Transistor (5:4)",
    },
    {
        "season": "Season 7",
        "year": "2022",
        "league_champion": "ectoPower",
        "cup_winner": "RVD (МГБ)",
        "runner_up": "mafuta",
        "third_place": "Romix",
    },
    {
        "season": "Season 8",
        "year": "2024",
        "league_champion": "Kunio / ectoPower",
        "cup_winner": "PacnyTHuK",
        "cup_finalist": "ectoPower (5:3)",
    },
    {
        "season": "Season 9",
        "year": "2025",
        "league_champion": "Kunio",
        "cup_winner": "ectoPower",
        "cup_finalist": "Rock (5:0)",
        "third_place": "Romix",
    },
]


def build_master_table_payload(matches, leaderboard, h2h_matrix):
    """The nekketsu_master_table.json document."""
    total_goals = sum(match["s1"] + match["s2"] for match in matches)
    return {
        "game": GAME_TITLE,
        "community": {"name": COMMUNITY_NAME, "url": COMMUNITY_URL, "group_id": GROUP_ID},
        "database_metrics": {
            "total_matches_analyzed": len(matches),
            "total_players_tracked": len(leaderboard),
            "total_goals_recorded": total_goals,
            "avg_goals_per_match": round(total_goals / len(matches), 2),
            "generation_date": GENERATION_DATE,
        },
        "championship_chronology": CHAMPIONSHIP_CHRONOLOGY,
        "leaderboard": leaderboard,
        "head_to_head_matrix": h2h_matrix,
        "dominators_ranking": sorted(leaderboard, key=lambda row: row["dominator_score"], reverse=True)[
            :TOP_DOMINATORS_LIMIT
        ],
    }


# Hand-written snapshot of one dashboard run: the numbers below are NOT derived from the data above.


def group(number):
    """``938`` to ``9 38`` — the digit spacing used throughout the dashboard."""
    return f"{number:,}".replace(",", " ")


def dashboard_insights(board, chronology):
    """The opening bullets, each derived from the pool instead of typed by hand."""
    dominator = max(board, key=lambda r: r["dominator_score"])
    elo_leader = board[0]
    defensive = min(
        (r for r in board if r["matches"] >= MIN_MATCHES_FOR_DEFENSIVE),
        key=lambda r: r["gapg"],
    )
    cup_killer = max(board, key=lambda r: (r["cup_titles"], r["total_titles"]))

    streak_player, streak_length = None, 0
    current_player, run = None, 0
    for season in chronology:
        champion = season.get("league_champion")
        run = run + 1 if champion == current_player else 1
        current_player = champion
        if run > streak_length:
            streak_length, streak_player = run, champion
    dynasty = f"{streak_player} ({streak_length} чемпионских титула подряд)" if streak_player else "—"

    playoff_games = elo_leader["playoff_wins"] + elo_leader["playoff_losses"]
    clutch_rate = round(100 * elo_leader["playoff_wins"] / playoff_games, 1) if playoff_games else 0.0
    return [
        f"1. **Абсолютный Доминатор — {dominator['player']} (Dominator Score: {dominator['dominator_score']}):** "
        f"{dominator['premier_titles']} чемпионских титулов Высшей лиги, {dominator['cup_titles']} Кубка лиг, "
        f"{dominator['major_finals']} выходов в финал; {dominator['wins']} побед и разница мячей "
        f"{dominator['goal_diff']:+d} ({dominator['goals_for']} забито против {dominator['goals_against']} пропущенных).",
        f"2. **Долнейшая чемпионская серия:** {dynasty}.",
        f"3. **Лидер рейтинга — {elo_leader['player']} (Elo {elo_leader['elo']}):** "
        f"винрейт {elo_leader['win_rate']}%, в плей-офф {elo_leader['playoff_wins']}-"
        f"{elo_leader['playoff_losses']} ({clutch_rate}% побед).",
        f"4. **«Железная стена» — {defensive['player']}:** {defensive['gapg']} пропущенных за матч "
        f"при {defensive['matches']} сыгранных матчах (минимум {MIN_MATCHES_FOR_DEFENSIVE}).",
        f"5. **Кубковый специалист — {cup_killer['player']}:** {cup_killer['cup_titles']} Кубков лиги.",
    ]


def render_dashboard(payload):
    """Markdown dashboard generated from the same payload as the master table."""
    board = payload["leaderboard"]
    metrics = payload["database_metrics"]
    out = [
        f"# 🏆 Мастер-таблица и аналитический дашборд: {payload['game']}",
        "",
        f"> Сообщество [{{community}}]({payload['community']['url']}) • "
        f"{metrics['total_matches_analyzed']} матчей • {metrics['total_players_tracked']} игроков • "
        f"{group(metrics['total_goals_recorded'])} голов • средняя результативность "
        f"{metrics['avg_goals_per_match']}".replace("{community}", payload["community"]["name"]),
        "",
        "## 📌 Раздел 1. Блок инсайтов: «Главное»",
        "",
        "> [!IMPORTANT]",
        "> ### Ключевые аналитические инсайты киберспортивной сцены Goal 3:",
        *[f"> {line}" for line in dashboard_insights(board, payload["championship_chronology"])],
        "",
        "## 📊 Раздел 2. Мастер-таблица: Глобальный Elo-рейтинг и игровая статистика",
        "",
        f"*Модель FIDE/Esports: K={ELO_K_PLAYOFF} для плей-офф и матчей новичков, "
        f"K={ELO_K_REGULAR} для регулярки, веса овертаймов и буллитов — "
        f"{OVERTIME_WIN_SCORE}/{DRAW_SCORE}.*",
        "",
        "| № | Игрок | Статус / Тир | Матчи | В | П | Винрейт | Забито | Пропущено | Разница | GPG | "
        "Сухие | Elo | Пик Elo | Dominator |",
        "|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        *[
            f"| {i} | **{r['player']}** | {r['tier']} | {r['matches']} | {r['wins']} | {r['losses']} | "
            f"{r['win_rate']}% | {r['goals_for']} | {r['goals_against']} | {r['goal_diff']:+d} | {r['gpg']} | "
            f"{r['clean_sheets']} | **{r['elo']}** | {r['peak_elo']} | {r['dominator_score']} |"
            for i, r in enumerate(board, 1)
        ],
        "",
        "## 🥊 Раздел 3. Матрица личных встреч (Head-to-Head Top-Tier)",
        "",
    ]
    rivals = list(payload["head_to_head_matrix"])
    out.append("| Игрок | " + " | ".join(rivals) + " |")
    out.append("|:---|" + ":---:|" * len(rivals))
    for player in rivals:
        cells = [payload["head_to_head_matrix"][player].get(other, "—") for other in rivals]
        out.append(f"| **{player}** | " + " | ".join(cells) + " |")

    out += ["", "## 🏛️ Раздел 4. Зал Славы и Хроника Чемпионов", ""]
    for season in payload["championship_chronology"]:
        facts = " • ".join(
            f"{label}: {value}"
            for label, value in (
                ("Чемпион лиги", season.get("league_champion")),
                ("Обладатель Кубка", season.get("cup_winner")),
                ("Финалист", season.get("runner_up")),
                ("Третье место", season.get("third_place")),
            )
            if value
        )
        out.append(f"- **{season['season']}** ({season['year']}, {season.get('format', '—')}) — {facts}")
    legends = [r for r in board if r["hall_of_fame"]]
    out += ["", f"**Зал Славы ({len(legends)})** — " + ", ".join(r["player"] for r in legends), ""]

    out += ["## 🎖️ Раздел 5. Иерархия доминаторов", "", "```mermaid", "graph TD"]
    tiers = {}
    for row in payload["dominators_ranking"]:
        tiers.setdefault(row["tier"], []).append(row)
    for tier, rows in tiers.items():
        out.append(f'    subgraph "{tier}"')
        for row in rows:
            safe = row["player"].replace("_", "")
            out.append(
                f'        {safe}["{row["player"]}<br/>Dominator: {row["dominator_score"]} | '
                f'{row["total_titles"]} титулов | {row["goal_diff"]:+d} GD"]'
            )
        out.append("    end")
    out += ["```", ""]
    return "\n".join(out)


def main(output_dir=Path(".")):
    """Write the analytics snapshot and the generated Markdown dashboard."""
    output_dir = Path(output_dir)
    ratings = build_player_ratings(all_matches)
    leaderboard = build_leaderboard(ratings)
    payload = build_master_table_payload(all_matches, leaderboard, build_head_to_head_matrix(ratings))

    analytics_path = output_dir / ANALYTICS_TABLE_PATH
    dashboard_path = output_dir / DASHBOARD_PATH
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(analytics_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"Analytics snapshot saved at: {analytics_path}")

    with open(dashboard_path, "w", encoding="utf-8") as handle:
        handle.write(render_dashboard(payload))
    print(f"Master Markdown Dashboard saved at: {dashboard_path}")


verify_vk_connection()
all_matches = fetch_all_matches()

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--out-dir":
        main(sys.argv[2])
    else:
        main()
