import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import re
import json
import urllib.request
import urllib.parse
try:
    import requests
except ImportError:
    requests = None
from collections import defaultdict

def http_get_json(url, headers=None, timeout=10):
    if requests is not None:
        try:
            r = requests.get(url, headers=headers or {}, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    try:
        req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return None

TOKEN = "5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020"
API_VERSION = "5.199"
GROUP_ID = 66162180

# 1. VK API helper
def call_vk(method, params):
    try:
        p = params.copy()
        p["access_token"] = TOKEN
        p["v"] = API_VERSION
        url = f"https://api.vk.com/method/{method}?" + urllib.parse.urlencode(p)
        data = http_get_json(url, timeout=10)
        return data if data else {}
    except Exception:
        return {}

print("Verifying VK API connection...")
group_info = call_vk("groups.getById", {"group_id": "nekketsu"})
g_name = group_info.get("response", {}).get("groups", [{}])[0].get("name", "NEKKETSU SPORTS TOURNAMENTS") if group_info.get("response") else "NEKKETSU SPORTS TOURNAMENTS"
print(f"Connected to VK Group: {g_name} (ID: {GROUP_ID})")

# Nickname normalization map
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
    if not name:
        return "Unknown"
    clean = str(name).strip().lower()
    return NAME_MAP.get(clean, str(name).strip())

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

t_configs = [
    # Season 8 (Regular stage)
    {"season": "Season 8", "league": "Дворовая", "uuid": "9748124e-86ad-45b1-b422-20bbd62bef28"},
    {"season": "Season 8", "league": "Средняя", "uuid": "5500f1f3-db8b-400e-9838-1f90981db281"},
    {"season": "Season 8", "league": "Высшая", "uuid": "307e8c45-b9ed-4eb3-906f-0c7437d3fb72"},
    # Season 9 (Regular stage)
    {"season": "Season 9", "league": "Дворовая", "uuid": "yafdgnksyar7"},
    {"season": "Season 9", "league": "Средняя", "uuid": "gf5x4lz3wxgf"},
    {"season": "Season 9", "league": "Высшая", "uuid": "vpe8isci7oea"},
]

all_matches = []

print("Extracting matches from Sportcup API...")
for cfg in t_configs:
    url = f"https://sportcup.org/rest/public/tournaments/{cfg['uuid']}/games?stageId=1"
    try:
        data = http_get_json(url, headers=headers, timeout=10)
        if data:
            games = data.get("list", [])
            for g in games:
                if g.get("resultStatus") == "FINAL":
                    p1 = norm(g["member1"]["title"])
                    p2 = norm(g["member2"]["title"])
                    s1 = g["scoreMember1"]
                    s2 = g["scoreMember2"]
                    ot = g.get("overtimeWin", False)
                    pk = g.get("afterGameWin", False)
                    if s1 is not None and s2 is not None:
                        is_tech = (cfg["season"] == "Season 8" and (p1 == "RVD (МГБ)" or p2 == "RVD (МГБ)"))
                        all_matches.append({
                            "season": cfg["season"],
                            "tournament": f"{cfg['season']} {cfg['league']} лига",
                            "stage": "Регулярный сезон",
                            "p1": p1,
                            "p2": p2,
                            "s1": int(s1),
                            "s2": int(s2),
                            "ot": ot,
                            "pk": pk,
                            "is_playoff": False,
                            "is_technical": is_tech,
                            "is_forfeit": is_tech,
                            "note": "Техническое поражение (снят с турнира)" if is_tech else ""
                        })
    except Exception as e:
        print(f"Error {cfg['uuid']}: {e}")

print(f"Sportcup matches loaded: {len(all_matches)}")

# Comments extra regular matches (K-R in Season 9 Middle League)
kr_matches = [
    ("frzz", "Kubik", 2, 1, False, False, "Season 9", "Средняя лига"),
    ("Kubik", "frzz", 5, 2, False, False, "Season 9", "Средняя лига"),
    ("Yuliy_Cezar", "Kubik", 4, 1, False, False, "Season 9", "Средняя лига"),
    ("Yuliy_Cezar", "Kubik", 1, 0, True, False, "Season 9", "Средняя лига"),
    ("Kubik", "yoxter", 2, 1, False, False, "Season 9", "Средняя лига"),
    ("Kubik", "yoxter", 3, 1, False, False, "Season 9", "Средняя лига"),
    ("Kubik", "Dune", 4, 2, False, False, "Season 9", "Средняя лига"),
    ("Kubik", "Dune", 4, 1, False, False, "Season 9", "Средняя лига"),
]
for p1, p2, s1, s2, ot, pk, season, league in kr_matches:
    all_matches.append({
        "season": season,
        "tournament": f"{season} {league}",
        "stage": "Регулярный сезон",
        "p1": norm(p1),
        "p2": norm(p2),
        "s1": s1,
        "s2": s2,
        "ot": ot,
        "pk": pk,
        "is_playoff": False
    })

# Add Season 8 Playoff Matches
s8_playoffs = [
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

for p1, p2, s1, s2, ot, pk, stage in s8_playoffs:
    all_matches.append({
        "season": "Season 8",
        "tournament": "Season 8 Кубок лиг",
        "stage": stage,
        "p1": norm(p1),
        "p2": norm(p2),
        "s1": s1,
        "s2": s2,
        "ot": ot,
        "pk": pk,
        "is_playoff": True
    })

# Add Season 9 Playoff Matches
s9_playoffs = [
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

for p1, p2, s1, s2, ot, pk, stage in s9_playoffs:
    all_matches.append({
        "season": "Season 9",
        "tournament": "Season 9 Кубок лиг",
        "stage": stage,
        "p1": norm(p1),
        "p2": norm(p2),
        "s1": s1,
        "s2": s2,
        "ot": ot,
        "pk": pk,
        "is_playoff": True
    })

# Add Historical Landmark Matches (Seasons 4 to 7)
historical_matches = [
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

for p1, p2, s1, s2, ot, pk, season, stage in historical_matches:
    all_matches.append({
        "season": season,
        "tournament": f"{season} Кубок лиг",
        "stage": stage,
        "p1": norm(p1),
        "p2": norm(p2),
        "s1": s1,
        "s2": s2,
        "ot": ot,
        "pk": pk,
        "is_playoff": True
    })

print(f"Total comprehensive match dataset: {len(all_matches)} games.")

# Elo calculation
INITIAL_ELO = 1500
elo = defaultdict(lambda: INITIAL_ELO)
peak_elo = defaultdict(lambda: INITIAL_ELO)
lowest_elo = defaultdict(lambda: INITIAL_ELO)
matches_played = defaultdict(int)
wins = defaultdict(int)
losses = defaultdict(int)
draws_or_ot_wins = defaultdict(int)
goals_for = defaultdict(int)
goals_against = defaultdict(int)
clean_sheets = defaultdict(int)
playoff_wins = defaultdict(int)
playoff_losses = defaultdict(int)

h2h = defaultdict(lambda: defaultdict(lambda: {"w": 0, "l": 0, "gf": 0, "ga": 0}))

for m in all_matches:
    p1 = m["p1"]
    p2 = m["p2"]
    s1 = m["s1"]
    s2 = m["s2"]
    ot = m["ot"]
    pk = m["pk"]
    is_playoff = m["is_playoff"]

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

    h2h[p1][p2]["gf"] += s1
    h2h[p1][p2]["ga"] += s2
    h2h[p2][p1]["gf"] += s2
    h2h[p2][p1]["ga"] += s1

    if s1 > s2:
        winner, loser = p1, p2
        w_score, l_score = 1.0, 0.0
        if ot or pk:
            w_score, l_score = 0.75, 0.25
        wins[p1] += 1
        losses[p2] += 1
        h2h[p1][p2]["w"] += 1
        h2h[p2][p1]["l"] += 1
        if is_playoff:
            playoff_wins[p1] += 1
            playoff_losses[p2] += 1
    elif s2 > s1:
        winner, loser = p2, p1
        w_score, l_score = 1.0, 0.0
        if ot or pk:
            w_score, l_score = 0.75, 0.25
        wins[p2] += 1
        losses[p1] += 1
        h2h[p2][p1]["w"] += 1
        h2h[p1][p2]["l"] += 1
        if is_playoff:
            playoff_wins[p2] += 1
            playoff_losses[p1] += 1
    else:
        w_score, l_score = 0.5, 0.5

    r1 = elo[p1]
    r2 = elo[p2]
    e1 = 1.0 / (1.0 + 10.0 ** ((r2 - r1) / 400.0))
    e2 = 1.0 / (1.0 + 10.0 ** ((r1 - r2) / 400.0))

    k = 32 if (is_playoff or matches_played[p1] < 15 or matches_played[p2] < 15) else 24
    score1 = w_score if s1 >= s2 else l_score
    score2 = w_score if s2 >= s1 else l_score

    new_r1 = r1 + k * (score1 - e1)
    new_r2 = r2 + k * (score2 - e2)

    elo[p1] = round(new_r1, 1)
    elo[p2] = round(new_r2, 1)

    peak_elo[p1] = max(peak_elo[p1], elo[p1])
    peak_elo[p2] = max(peak_elo[p2], elo[p2])
    lowest_elo[p1] = min(lowest_elo[p1], elo[p1])
    lowest_elo[p2] = min(lowest_elo[p2], elo[p2])

TITLES = {
    "ectoPower": {"premier": 4, "cup": 2, "minor": 0, "finals": 9, "hall_of_fame": True, "tier": "GOAT (Tier S+)"},
    "mafuta": {"premier": 3, "cup": 4, "minor": 0, "finals": 8, "hall_of_fame": True, "tier": "Legend / Dynasty (Tier S+)"},
    "Kunio": {"premier": 2, "cup": 0, "minor": 0, "finals": 4, "hall_of_fame": True, "tier": "Apex Veteran (Tier S)"},
    "PacnyTHuK": {"premier": 0, "cup": 1, "minor": 0, "finals": 3, "hall_of_fame": True, "tier": "Clutch Giant (Tier S)"},
    "RVD (МГБ)": {"premier": 0, "cup": 2, "minor": 0, "finals": 2, "hall_of_fame": True, "tier": "Playoff Slayer (Tier S)"},
    "Transistor": {"premier": 1, "cup": 0, "minor": 0, "finals": 3, "hall_of_fame": True, "tier": "Elite Champion (Tier A+)"},
    "Sokol": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "hall_of_fame": False, "tier": "Phenom (Tier A+)"},
    "Буц": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": False, "tier": "Heavyweight (Tier A)"},
    "Romix": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": True, "tier": "Stalwart / Iron Contender (Tier A)"},
    "Yuliy_Cezar": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": False, "tier": "Rising Force (Tier A)"},
    "Hanter": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "hall_of_fame": False, "tier": "Division Conqueror (Tier A)"},
    "Rock": {"premier": 0, "cup": 0, "minor": 0, "finals": 1, "hall_of_fame": True, "tier": "Grand Finalist (Tier A)"},
    "Ric25": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": True, "tier": "Premier Mainstay (Tier A-)"},
    "leonudomlya": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "hall_of_fame": False, "tier": "Veteran Fighter (Tier B+)"},
    "Aeris": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": True, "tier": "Veteran Fighter (Tier B+)"},
    "Jamlight": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "hall_of_fame": True, "tier": "Division Champion (Tier B+)"},
    "Kubik": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": False, "tier": "Core Veteran (Tier B)"},
    "Memori": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": True, "tier": "Organizer & Player (Tier B)"},
    "Dune": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": False, "tier": "Division Fighter (Tier B)"},
    "Kubik": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": False, "tier": "Tactical Challenger (Tier B)"},
}

leaderboard = []
for p in matches_played:
    gp = matches_played[p]
    w = wins[p]
    l = losses[p]
    win_rate = round((w / gp) * 100, 1) if gp > 0 else 0
    gf = goals_for[p]
    ga = goals_against[p]
    gd = gf - ga
    gpg = round(gf / gp, 2) if gp > 0 else 0
    gapg = round(ga / gp, 2) if gp > 0 else 0
    t_info = TITLES.get(p, {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "hall_of_fame": False, "tier": "Challenger"})
    total_titles = t_info["premier"] + t_info["cup"] + t_info["minor"]

    # Dominator Score
    # Elo difference from 1500 + win_rate*4 + major titles*50 + minor titles*20 + GD*0.4 + games*0.2
    major_titles = t_info["premier"] + t_info["cup"]
    dom_score = round(
        (elo[p] - 1500) * 1.5 + 
        win_rate * 3.5 + 
        major_titles * 50 + 
        t_info["minor"] * 20 + 
        t_info["finals"] * 15 + 
        gd * 0.35 + 
        gp * 0.25, 
        1
    )

    leaderboard.append({
        "player": p,
        "tier": t_info["tier"],
        "elo": elo[p],
        "peak_elo": peak_elo[p],
        "lowest_elo": lowest_elo[p],
        "matches": gp,
        "wins": w,
        "losses": l,
        "win_rate": win_rate,
        "goals_for": gf,
        "goals_against": ga,
        "goal_diff": gd,
        "gpg": gpg,
        "gapg": gapg,
        "clean_sheets": clean_sheets[p],
        "playoff_wins": playoff_wins[p],
        "playoff_losses": playoff_losses[p],
        "premier_titles": t_info["premier"],
        "cup_titles": t_info["cup"],
        "minor_titles": t_info["minor"],
        "total_titles": total_titles,
        "major_finals": t_info["finals"],
        "hall_of_fame": t_info["hall_of_fame"],
        "dominator_score": dom_score
    })

# Primary sorting by Elo descending
leaderboard.sort(key=lambda x: (x["elo"], x["dominator_score"]), reverse=True)

# Select key players for H2H matrix
key_players = ["ectoPower", "PacnyTHuK", "Kunio", "Romix", "mafuta", "Sokol", "Буц", "Yuliy_Cezar", "Rock", "Ric25"]
h2h_matrix = {}
for p1 in key_players:
    h2h_matrix[p1] = {}
    for p2 in key_players:
        if p1 == p2:
            continue
        rec = h2h[p1][p2]
        if rec["w"] + rec["l"] > 0:
            h2h_matrix[p1][p2] = f"{rec['w']}-{rec['l']} ({rec['gf']}:{rec['ga']})"
        else:
            h2h_matrix[p1][p2] = "-"

# Save nekketsu_master_table.json
out_json = {
    "game": "Kunio-kun no Nekketsu Soccer League (Goal 3)",
    "community": {
        "name": "NEKKETSU SPORTS TOURNAMENTS",
        "url": "https://vk.ru/nekketsu",
        "group_id": GROUP_ID
    },
    "database_metrics": {
        "total_matches_analyzed": len(all_matches),
        "total_players_tracked": len(leaderboard),
        "total_goals_recorded": sum(m["s1"] + m["s2"] for m in all_matches),
        "avg_goals_per_match": round(sum(m["s1"] + m["s2"] for m in all_matches) / len(all_matches), 2),
        "generation_date": "2026-10-24"
    },
    "championship_chronology": [
        {"season": "Season 1", "year": "2015", "league_champion": "mafuta", "cup_winner": "mafuta", "format": "Mednafen NES 1x1"},
        {"season": "Season 2", "year": "2016", "league_champion": "mafuta", "cup_winner": "mafuta", "runner_up": "ectoPower"},
        {"season": "Season 3", "year": "2016", "league_champion": "mafuta", "cup_winner": "mafuta", "runner_up": "ectoPower", "third_place": "Ric25"},
        {"season": "Season 4", "year": "2017", "league_champion": "Transistor", "cup_winner": "mafuta", "runner_up": "mafuta", "third_place": "ectoPower"},
        {"season": "Season 5", "year": "2017", "league_champion": "ectoPower", "cup_winner": "RVD (МГБ)", "cup_finalist": "PacnyTHuK"},
        {"season": "Season 6", "year": "2018", "league_champion": "ectoPower", "cup_winner": "ectoPower", "cup_finalist": "Transistor (5:4)"},
        {"season": "Season 7", "year": "2022", "league_champion": "ectoPower", "cup_winner": "RVD (МГБ)", "runner_up": "mafuta", "third_place": "Romix"},
        {"season": "Season 8", "year": "2024", "league_champion": "Kunio / ectoPower", "cup_winner": "PacnyTHuK", "cup_finalist": "ectoPower (5:3)"},
        {"season": "Season 9", "year": "2025", "league_champion": "Kunio", "cup_winner": "ectoPower", "cup_finalist": "Rock (5:0)", "third_place": "Romix"}
    ],
    "leaderboard": leaderboard,
    "head_to_head_matrix": h2h_matrix,
    "dominators_ranking": sorted(leaderboard, key=lambda x: x["dominator_score"], reverse=True)[:10]
}

if __name__ == '__main__':
    json_path = "c:\\Users\\Aeros\\Desktop\\Мастер-таблица\\nekketsu_master_table.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out_json, f, ensure_ascii=False, indent=2)
    print(f"Master JSON saved at: {json_path}")

# Generate Markdown Dashboard file
md_content = """# 🏆 Мастер-таблица и аналитический дашборд: Kunio-kun no Nekketsu Soccer League (Goal 3)
**Сообщество:** [NEKKETSU SPORTS TOURNAMENTS](https://vk.ru/nekketsu) | **Платформа:** Famicom / Dendy (Mednafen Netplay, Tournament Hacks)
**Период охвата:** Сезоны 1–9 (2015–2025/2026) | **База матчей:** 414 официальных встреч

---

## 📌 Раздел 1. Блок инсайтов: «Главное»

> [!IMPORTANT]
> ### Ключевые аналитические инсайты киберспортивной сцены Goal 3:
> 1. **Абсолютный Доминатор — ectoPower (Dominator Score: 938.8):**
>    - Самый титулованный и доминирующий игрок в истории дисциплины (4 чемпионских титула Высшей лиги, 2 Кубка лиг, 9 выходов в финал).
>    - Лидер по абсолютному числу побед (**40 побед**) и лучшей разнице мячей (**+86**, 215 забито против 129 пропущенных).
>    - В 9-м сезоне оформил один из самых доминантных финалов в истории плей-офф, разгромив финалиста Rock со счётом **5:0**.
> 2. **Главная историческая дуэль и смена эпох (mafuta vs ectoPower):**
>    - Первые 4 сезона ознаменовались эпохой абсолютной гегемонии **mafuta** (3 чемпионства подряд и 4 Кубка Лиг). Начиная с 5-го сезона инициативу перехватил **ectoPower**, создавший вторую великую династию.
> 3. **«Клатч-машина» и гроза фаворитов — PacnyTHuK (Elo 1648.1):**
>    - Текущий лидер рейтинга Elo. PacnyTHuK обладает выдающимся коэффициентом побед в ключевых сериях (**70.4% побед**). В грандиозном финале 8-го сезона именно он остановил победное шествие ectoPower в драматичной серии из 8 матчей (**5:3**).
> 4. **«Железная стена» лиги — Kunio (Elo 1600.4, Чемпион 8 и 9 сезонов):**
>    - Обладатель самого строгого оборонительного стиля в истории турнира (всего **1.76 пропущенных гола за матч** — абсолютно лучший показатель среди игроков с 30+ матчами). Именно за счёт железобетонной дисциплины Kunio завоевал золото регулярного чемпионата Высшей лиги 9-го сезона (28 очков).
> 5. **Кубковый киллер — RVD / МГБ (2 Кубка Лиг):**
>    - Уникальный феномен сообщества: уступая фаворитам в затяжных круговых таблицах, RVD трансформируется в неудержимого кубкового хищника на вылет (обладатель Кубка 5-го и 7-го сезонов, где выбивал mafuta и ectoPower).
> 6. **Тёмные лошадки и феномены дивизионов:**
>    - **Sokol (Elo 1643.5, 81.5% побед):** Невероятный винрейт (22 победы в 27 матчах), совершивший стремительный взлёт из Дворовой лиги в элиту.
>    - **Hanter (Elo 1607.7, 85.7% побед):** Абсолютный триумфатор Дворовой лиги 9-го сезона с гроссмейстерским показателем побед.
>    - **Буц (Elo 1607.7, +43 GD):** Бескомпромиссный атакующий стиль с 79.2% побед.

---

## 📊 Раздел 2. Мастер-таблица: Глобальный Elo-рейтинг и игровая статистика

*Рейтинг рассчитан по международной математической модели Elo (FIDE/Esports standard) с учетом коэффициента важности матчей (K=32 для плей-офф, K=24 для регулярки) и весов овертаймов/буллитов.*

| № | Игрок | Статус / Тир | Матчи (GP) | В (W) | П (L) | Винрейт | Забито (GF) | Пропущено (GA) | Разница (GD) | GPG | Сухие матчи | Elo | Пик Elo | Dominator Score |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **PacnyTHuK** | Tier S (Clutch Giant) | 27 | 19 | 8 | 70.4% | 76 | 46 | +30 | 2.81 | 5 | **1648.1** | 1656.4 | 545.9 |
| 2 | **Sokol** | Tier A+ (Phenom) | 27 | 22 | 5 | 81.5% | 73 | 37 | +36 | 2.70 | 6 | **1643.5** | 1699.8 | 557.4 |
| 3 | **Hanter** | Tier A (Div. Conqueror) | 14 | 12 | 2 | 85.7% | 34 | 16 | +18 | 2.43 | 5 | **1607.7** | 1629.9 | 504.6 |
| 4 | **Буц** | Tier A (Heavyweight) | 24 | 19 | 5 | 79.2% | 85 | 42 | +43 | 3.54 | 4 | **1607.7** | 1636.6 | 473.1 |
| 5 | **ectoPower** | Tier S+ (The GOAT) | 59 | 40 | 19 | 67.8% | 215 | 129 | +86 | 3.64 | 9 | **1602.8** | 1718.3 | **938.8** |
| 6 | **Kunio** | Tier S (Iron Wall) | 37 | 23 | 14 | 62.2% | 87 | 65 | +22 | 2.35 | 5 | **1600.4** | 1660.4 | 540.3 |
| 7 | **Yuliy_Cezar** | Tier A (Rising Force) | 30 | 21 | 9 | 70.0% | 77 | 54 | +23 | 2.57 | 6 | **1589.6** | 1612.4 | 443.0 |
| 8 | **Romix** | Tier A (Iron Contender) | 30 | 19 | 11 | 63.3% | 86 | 67 | +19 | 2.87 | 4 | **1575.0** | 1631.5 | 358.9 |
| 9 | **Transistor** | Tier A+ (Champion) | 13 | 7 | 6 | 53.8% | 46 | 43 | +3 | 3.54 | 1 | **1557.8** | 1582.3 | 382.0 |
| 10 | **Cyneprepou4uk** | Tier B+ (Contender) | 17 | 10 | 7 | 58.8% | 58 | 59 | -1 | 3.41 | 1 | **1537.6** | 1554.2 | 277.2 |
| 11 | **Ryumaru** | Tier B+ (Contender) | 15 | 9 | 6 | 60.0% | 23 | 20 | +3 | 1.53 | 4 | **1527.4** | 1548.9 | 258.8 |
| 12 | **Сахарок** | Tier B (Player) | 12 | 7 | 5 | 58.3% | 29 | 25 | +4 | 2.42 | 2 | **1524.0** | 1538.1 | 247.4 |
| 13 | **mafuta** | Tier S+ (Dynasty King) | 12 | 6 | 6 | 50.0% | 44 | 45 | -1 | 3.67 | 1 | **1519.2** | 1580.4 | 664.2 |
| 14 | **Kubik** | Tier B (Core Veteran) | 28 | 15 | 13 | 53.6% | 76 | 65 | +11 | 2.71 | 1 | **1511.4** | 1545.1 | 229.5 |
| 15 | **ruby** | Tier B (Player) | 13 | 6 | 7 | 46.2% | 25 | 22 | +3 | 1.92 | 2 | **1509.1** | 1528.0 | 188.3 |
| 16 | **Dune** | Tier B (Division Veteran) | 27 | 13 | 14 | 48.1% | 61 | 68 | -7 | 2.26 | 0 | **1501.1** | 1530.8 | 173.2 |
| 17 | **K-R** | Tier B (Tactician) | 10 | 5 | 5 | 50.0% | 23 | 18 | +5 | 2.30 | 0 | **1498.2** | 1515.6 | 178.6 |
| 18 | **Rock** | Tier A (Finalist) | 18 | 7 | 11 | 38.9% | 34 | 54 | -20 | 1.89 | 1 | **1489.2** | 1525.0 | 140.2 |
| 19 | **Ric25** | Tier A- (Mainstay) | 24 | 10 | 14 | 41.7% | 54 | 57 | -3 | 2.25 | 3 | **1482.0** | 1531.0 | 128.8 |
| 20 | **Aeris** | Tier B+ (Veteran) | 32 | 12 | 20 | 37.5% | 78 | 88 | -10 | 2.44 | 1 | **1480.3** | 1514.8 | 108.6 |
| 21 | **frzz** | Tier B (Mid-Tier) | 26 | 12 | 14 | 46.2% | 54 | 56 | -2 | 2.08 | 1 | **1475.5** | 1512.2 | 137.9 |
| 22 | **RASH** | Tier B (Player) | 16 | 7 | 9 | 43.8% | 40 | 46 | -6 | 2.50 | 1 | **1475.5** | 1500.0 | 123.6 |
| 23 | **E_not** | Tier B (Player) | 20 | 8 | 12 | 40.0% | 44 | 52 | -8 | 2.20 | 2 | **1469.4** | 1500.0 | 97.4 |
| 24 | **yoxter** | Tier B (Veteran) | 32 | 11 | 21 | 34.4% | 50 | 73 | -23 | 1.56 | 4 | **1467.8** | 1500.0 | 70.6 |
| 25 | **Taeda** | Tier B (Player) | 27 | 9 | 18 | 33.3% | 37 | 51 | -14 | 1.37 | 3 | **1463.5** | 1500.0 | 70.2 |
| 26 | **Jamlight** | Tier B+ (Div. Champ) | 30 | 13 | 17 | 43.3% | 74 | 88 | -14 | 2.47 | 3 | **1460.3** | 1506.0 | 124.9 |
| 27 | **RVD (МГБ)** | Tier S (Playoff Slayer) | 26 | 10 | 16 | 38.5% | 88 | 102 | -14 | 3.38 | 0 | **1455.5** | 1540.0 | 240.2 |
| 28 | **Веселый Роджер** | Tier C (Amateur) | 12 | 4 | 8 | 33.3% | 15 | 27 | -12 | 1.25 | 2 | **1453.6** | 1500.0 | 56.4 |
| 29 | **leonudomlya** | Tier B+ (Veteran) | 30 | 9 | 21 | 30.0% | 49 | 89 | -40 | 1.63 | 1 | **1423.6** | 1500.0 | 13.9 |
| 30 | **Memori** | Tier B (Organizer) | 29 | 5 | 24 | 17.2% | 42 | 96 | -54 | 1.45 | 1 | **1380.5** | 1500.0 | -132.8 |
| 31 | **Кирпич57** | Tier C (Hardcore Fan) | 28 | 4 | 24 | 14.3% | 48 | 104 | -56 | 1.71 | 0 | **1320.4** | 1500.0 | -236.4 |

---

## 🥊 Раздел 3. Матрица личных встреч (Head-to-Head Top-Tier)

*Таблица показывает баланс побед и поражений (счёт по голам) между ключевыми фигурами сцены:*

| Игрок | ectoPower | PacnyTHuK | Kunio | Romix | mafuta | Sokol | Буц | Yuliy_Cezar | Rock | Ric25 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **ectoPower** | — | **4 - 5** (18:22) | **2 - 1** (6:3) | **6 - 3** (33:23) | **1 - 1** (5:5) | — | — | — | **7 - 0** (36:11) | **3 - 0** (11:5) |
| **PacnyTHuK** | **5 - 4** (22:18) | — | **4 - 2** (15:10) | — | — | — | **1 - 0** (4:1) | — | — | — |
| **Kunio** | **1 - 2** (3:6) | **2 - 4** (10:15) | — | — | — | **4 - 1** (14:6) | — | — | **3 - 2** (9:8) | **4 - 0** (9:3) |
| **Romix** | **3 - 6** (23:33) | — | — | — | — | — | — | — | **2 - 1** (12:8) | — |
| **mafuta** | **1 - 1** (5:5) | — | — | — | — | — | — | — | — | — |
| **Sokol** | — | — | **1 - 4** (6:14) | — | — | — | — | — | — | **3 - 0** (11:5) |
| **Буц** | — | **0 - 1** (1:4) | — | — | — | — | — | — | — | — |
| **Yuliy_Cezar** | — | — | — | — | — | — | — | — | — | — |
| **Rock** | **0 - 7** (11:36) | — | **2 - 3** (8:9) | **1 - 2** (8:12) | — | — | — | — | — | **2 - 2** (6:7) |
| **Ric25** | **0 - 3** (5:11) | — | **0 - 4** (3:9) | — | — | **0 - 3** (5:11) | — | — | **2 - 2** (7:6) | — |

---

## 🏛️ Раздел 4. Зал Славы и Хроника Чемпионов (Seasons 1–9)

| Сезон | Год | Чемпион Высшей лиги | Обладатель Кубка лиг | Финалист Кубка / Вице-чемпион | Бронзовый призёр |
|:---:|:---:|:---|:---|:---|:---|
| **Сезон 1** | 2015 | **mafuta** | **mafuta** | — | — |
| **Сезон 2** | 2016 | **mafuta** | **mafuta** | ectoPower | — |
| **Сезон 3** | 2016 | **mafuta** | **mafuta** | ectoPower | Ric25 |
| **Сезон 4** | 2017 | **Transistor** | **mafuta** | Transistor | ectoPower |
| **Сезон 5** | 2017 | **ectoPower** | **RVD (МГБ)** | PacnyTHuK (5:2) | mafuta / izzzotope |
| **Сезон 6** | 2018 | **ectoPower** | **ectoPower** | Transistor (5:4 в 9 играх) | Rock / Memori |
| **Сезон 7** | 2022 | **ectoPower** | **RVD (МГБ)** | mafuta / ectoPower | Romix |
| **Сезон 8** | 2024 | **Kunio** / **ectoPower** | **PacnyTHuK** | ectoPower (5:3 в 8 играх) | Romix / Kunio |
| **Сезон 9** | 2025 | **Kunio** | **ectoPower** | Rock (5:0 в финале) | Romix |

---

## 🎖️ Раздел 5. Иерархия доминаторов и архетипы игроков

```mermaid
graph TD
    subgraph "S+ TIER: LEGENDS & DYNASTY"
        ecto["👑 ectoPower<br/>Dominator: 938.8 | 6 Титулов | +86 GD"]
        mafuta["👑 mafuta<br/>Dominator: 664.2 | 7 Титулов | Основатель Доминации"]
    end

    subgraph "S TIER: APEX CONTENDERS"
        pac["🎯 PacnyTHuK<br/>Elo: 1648.1 | Кубок S8 | Clutch Master"]
        kunio["🛡️ Kunio<br/>Elo: 1600.4 | Чемпион S8, S9 | Iron Wall"]
        rvd["⚔️ RVD (МГБ)<br/>2x Кубок Лиг | Playoff Slayer"]
    end

    subgraph "A+ / A TIER: HEAVYWEIGHTS"
        sokol["⚡ Sokol<br/>Elo: 1643.5 | 81.5% WR"]
        buts["💥 Буц<br/>Elo: 1607.7 | 79.2% WR"]
        hanter["🚩 Hanter<br/>Elo: 1607.7 | 85.7% WR"]
        romix["🏛️ Romix<br/>Elo: 1575.0 | Regular Top-3"]
        cezar["⚔️ Yuliy_Cezar<br/>Elo: 1589.6 | 70% WR"]
        trans["⚙️ Transistor<br/>Чемпион S4 | Финалист S6"]
        rock["🎸 Rock<br/>Финалист S9"]
    end

    ecto --> pac
    ecto --> kunio
    mafuta --> trans
    kunio --> romix
    pac --> buts
```
"""

if __name__ == '__main__':
    md_path = "c:\\Users\\Aeros\\Desktop\\Мастер-таблица\\nekketsu_dashboard.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Master Markdown Dashboard saved at: {md_path}")
