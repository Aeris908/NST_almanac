import json, os, re

from collections import defaultdict



print("Rebuilding Nekketsu Portal with Clean Human-Readable Russian Interface...")



# 1. Load Data

with open("nst_quotes.json", "r", encoding="utf-8") as f:

    nst_quotes = json.load(f)



with open("player_avatars.json", "r", encoding="utf-8") as f:

    avatars = json.load(f)



with open("nekketsu_master_table.json", "r", encoding="utf-8") as f:

    master_db = json.load(f)



with open("early_seasons_matches.json", "r", encoding="utf-8") as f:

    early_matches = json.load(f)



with open("all_vk_seasons_matches.json", "r", encoding="utf-8") as f:

    vk_matches = json.load(f)



with open("wiki_seasons_matches.json", "r", encoding="utf-8") as f:

    wiki_matches = json.load(f)



import build_final_analytics

base_matches = build_final_analytics.all_matches



# Load verified VK comments and video lookup table

try:

    with open('vk_match_sources_lookup.json', 'r', encoding='utf-8') as f:

        vk_sources_lookup = json.load(f)

except Exception as e:

    print("Warning loading vk_match_sources_lookup.json:", e)

    vk_sources_lookup = {}



TOPIC_MAP_BY_NAME = {

    "season 1": 32593813, "сезон 1": 32593813,

    "season 2": 33103100, "сезон 2": 33103100,

    "season 3": 33967365, "сезон 3": 33967365,

    "season 4": 34973011, "сезон 4": 34973011,

    "season 5": 36630593, "сезон 5": 36630593,

    "season 6": 39660451, "сезон 6": 39660451,

    "season 7": 49054760, "сезон 7": 49054760,

    "season 8": 52002075, "сезон 8": 52002075,

    "season 9": 54769667, "сезон 9": 54769667,

    "team 6": 49868493, "vi командный": 49868493,

    "team 5": 35995200, "v командный": 35995200,

    "team 4": 33672355, "iv командный": 33672355,

    "team 3": 31898219, "летний командный": 31898219,

    "youth 2": 41270759, "молодёжный": 41270759, "молодежный": 41270759,

    "penalty 4": 34920573, "пенальти": 34920573,

    "club goal 4": 39731903, "клубный чемпионат": 39731903,

}



PLAYER_CLEAN_MAP = {

    "веселый роджер": "веселый роджер",

    "весёлый роджер": "веселый роджер",

    "роджер": "веселый роджер",

    "палка палыч": "pacnythuk",

    "palka palych": "pacnythuk",

    "распутник": "pacnythuk",

    "палыч": "pacnythuk",

    "палка": "pacnythuk",

    "pacnythuk": "pacnythuk",

    "fc pushistik": "fc pushistik",

    "пушистик": "fc pushistik",

    "pushistik": "fc pushistik",

    "rustin cohle": "rustin cohle",

    "rustin_cohle": "rustin cohle",

    "rustinchole": "rustin cohle",

    "растин": "rustin cohle",

    "cohle": "rustin cohle",

    "rustin": "rustin cohle",

    "huba buba 5": "huba buba",

    "huba-buba 5": "huba buba",

    "huba_buba_5": "huba buba",

    "huba buba": "huba buba",

    "huba-buba": "huba buba",

    "huba_buba": "huba buba",

    "hubabuba": "huba buba",

    "exponat": "huba buba",

    "буба": "huba buba",

    "huba": "huba buba",

    "leon-udomlya": "leonudomlya",

    "leonudomlya": "leonudomlya",

    "леон": "leonudomlya",

    "леонид": "leonudomlya",

    "zupka knorra": "zupka knorra",

    "knorra": "zupka knorra",

    "santa claus": "santa claus",

    "claus": "santa claus",

    "joe duffy": "joe duffy",

    "joeduffy": "joe duffy",

    "duffy": "joe duffy",

    "mag.of.shadow": "mag.of.shadow",

    "shadow": "mag.of.shadow",

    "дядюшка ау": "дядюшка ау",

    "дядюшка_ау": "дядюшка ау",

    "супергеройчик": "cyneprepou4uk",

    "cyneprepou4uk": "cyneprepou4uk",

    "bzk": "cyneprepou4uk",

    "rvd (мгб)": "rvd (мгб)",

    "fierykelsen": "rvd (мгб)",
    "fierykeles": "rvd (мгб)",
    "exyxea": "rvd (мгб)",
    "ехухеа": "rvd (мгб)",
    "1путин": "pacnythuk",
    "1putin": "pacnythuk",
    "1-путин": "pacnythuk",
    "1_путин": "pacnythuk",

    "fieryrvd": "rvd (мгб)",

    "xakofear": "rvd (мгб)",

    "рвд": "rvd (мгб)",

    "мгб": "rvd (мгб)",

    "rvd": "rvd (мгб)",

    "knucklesss": "aeris",

    "knuckles": "aeris",

    "наклз": "aeris",

    "aeris": "aeris",

    "transsister": "transistor",

    "transistor": "transistor",

    "транзистор": "transistor",

    "кирпич57": "кирпич57",

    "kirpich57": "кирпич57",

    "кирпич": "кирпич57",

    "kirpich": "кирпич57",

    "centurion": "centurion",

    "сenturion": "centurion",

    "centzloy": "centurion",

    "цент": "centurion",

    "cent": "centurion",

    "bop95": "boр95",

    "вор95": "boр95",

    "bop213": "boр95",

    "вор": "boр95",

    "yuliy_cezar": "yuliy_cezar",

    "yuliy cezar": "yuliy_cezar",

    "juliy cezar": "yuliy_cezar",

    "juliy_cezar": "yuliy_cezar",

    "цезарь": "yuliy_cezar",

    "юлий": "yuliy_cezar",

    "kot-from-ussr": "kot-from-ussr",

    "ussr": "kot-from-ussr",

    "kipriot91": "kipriot",

    "киприот": "kipriot",

    "kipriot": "kipriot",

    "tubustd": "tubustd",

    "тубус": "tubustd",

    "bubnov": "bubnov",

    "tymoschuk": "bubnov",

    "тимощук": "bubnov",

    "бубнов": "bubnov",

    "dan_lavis": "dan_lavis",

    "danlavis": "dan_lavis",

    "chocopie": "chocopie",

    "chokopie": "chocopie",

    "шокопай": "chocopie",

    "aj_maker": "aj_maker",

    "ajmaker": "aj_maker",

    "aj maker": "aj_maker",

    "wenderfit": "wenderfit",

    "wendefit": "wenderfit",

    "вендер": "wenderfit",

    "ectopower": "ectopower",

    "эктоповер": "ectopower",

    "экто": "ectopower",

    "jamlight": "jamlight",

    "джем": "jamlight",

    "кубик": "kubik",

    "kubik": "kubik",

    "дюныч": "dune",

    "дюн": "dune",

    "dune": "dune",

    "рок": "rock",

    "rock": "rock",

    "мемори": "memori",

    "memori": "memori",

    "мафута": "mafuta",

    "mafuta": "mafuta",

    "кунио": "kunio",

    "kunio": "kunio",

    "ромикс": "romix",

    "romix": "romix",

    "сокол": "sokol",

    "sokol": "sokol",

    "енот": "e_not",

    "enot": "e_not",

    "e_not": "e_not",

    "даз": "daz",

    "daz": "daz",

    "таёда": "taeda",

    "таеда": "taeda",

    "taeda": "taeda",

    "рик25": "ric25",

    "ric25": "ric25",

    "рик": "ric25",

    "вайз": "wise",

    "wise": "wise",

    "допи": "dopi",

    "dopi": "dopi",

    "дрин": "dr1n",

    "dr1n": "dr1n",

    "дрын": "dr1n",

    "хантэр": "hanter",

    "хантер": "hanter",

    "hanter": "hanter",

    "ленин1st": "lenin1st",

    "ленин": "lenin1st",

    "lenin1st": "lenin1st",

    "анубис": "anubis",

    "anubis": "anubis",

    "раш": "rash",

    "rash": "rash",

    "к-р": "Kubik",
    "k-r": "Kubik",
    "k_r": "Kubik",
    "K-R": "Kubik",

    

    "буц": "буц",

    "ромол": "romol",

    "romol": "romol",

    "ромэль": "romol",

    "руби": "ruby",
    "ruby": "ruby",
    "blanko": "ruby",
    "бланко": "ruby",

    "ruby": "ruby",

    "динамик": "dynamik",

    "dynamik": "dynamik",

    "аоши": "aoshi",

    "aoshi": "aoshi",

    "давитель": "davitel",

    "davitel": "davitel",

    "эг_ор3": "eg_or3",

    "eg_or3": "eg_or3",

    "egor3": "eg_or3",

    "йокстер": "yoxter",

    "yoxter": "yoxter",

    "липтон": "буц",

    "lipton": "буц",

    "lipt0n": "буц",

    "техас": "texas",

    "texas": "texas",

    "псих": "psycho",

    "psycho": "psycho",

    "сталин": "stalin",

    "stalin": "stalin",

    "изотоп": "izzzotope",

    "izzzotope": "izzzotope",

    "izzotop": "izzzotope",

    "ванчоус": "wanchous",

    "wanchous": "wanchous",

    "легнахар": "legnahar",

    "legnahar": "legnahar",

    "artemis": "artemis",

    "atremis": "artemis",

    "mcfly": "mcfly",

    "msfly": "mcfly",

    "armfly": "armfly",

    "flash": "flash",

    "kamaz": "kamaz",

    "камаз": "kamaz",

    "damian": "damian",

    "gilmour": "gilmour",

    "romario": "romario",

    "3abuctb": "3abuctb",

    "зависть": "3abuctb",

    "ryumaru": "ryumaru",

    "рюмару": "ryumaru",

    "alpharushin": "alpharushin",

    "christian": "christian",

    "lipetsk": "lipetsk",

    "вася": "вася",

    "vasya": "вася"

}



def clean_tok_name(s):

    if not s: return ""

    s = re.sub(r'\[id\d+\|([^\]]+)\]', r'\1', str(s))

    s = re.sub(r'^\s*[\(\[]\s*[A-Za-z0-9_]{1,4}\s*[\)\]]', '', s)

    s = re.sub(r'[\(\[]\s*[A-Za-z0-9_]{1,4}\s*[\)\]]\s*$', '', s)

    s = s.strip().strip('*.,_()[]-–:').lower()

    return PLAYER_CLEAN_MAP.get(s, s)



def enrich_vk_source(m_dict):

    p1 = clean_tok_name(m_dict.get('p1', ''))

    p2 = clean_tok_name(m_dict.get('p2', ''))

    if not p1 or not p2: return m_dict

    s1 = int(m_dict.get('s1', 0))

    s2 = int(m_dict.get('s2', 0))

    p_min, p_max = min(p1, p2), max(p1, p2)

    s_min, s_max = min(s1, s2), max(s1, s2)

    

    s_name = str(m_dict.get('season', '')).lower()

    tid = None

    for k, v in TOPIC_MAP_BY_NAME.items():

        if k in s_name:

            tid = v

            break

            

    src = None

    if tid:

        src = vk_sources_lookup.get(f"{tid}|{p_min}|{p_max}|{s_min}|{s_max}")

    if not src and tid:

        src = vk_sources_lookup.get(f"{tid}|{p1}|{p2}|{s1}|{s2}")

    if not src:

        src = vk_sources_lookup.get(f"global|{p_min}|{p_max}|{s_min}|{s_max}")

    if not src and tid:

        src = vk_sources_lookup.get(f"{tid}|{p_min}|{p_max}")

        

    if src:

        if src.get('vk_url'):

            m_dict['vk_url'] = src['vk_url']

        if src.get('video_url'):

            m_dict['video_url'] = src['video_url']

        if src.get('text'):

            m_dict['vk_text'] = src['text']

        if src.get('date'):

            m_dict['vk_date'] = src['date']

        if src.get('page'):

            m_dict['vk_page'] = src['page']

            

    return m_dict

    s1 = int(m_dict.get('s1', 0))

    s2 = int(m_dict.get('s2', 0))

    p_min, p_max = min(p1, p2), max(p1, p2)

    s_min, s_max = min(s1, s2), max(s1, s2)

    

    s_name = str(m_dict.get('season', '')).lower()

    tid = None

    for k, v in TOPIC_MAP_BY_NAME.items():

        if k in s_name:

            tid = v

            break

            

    src = None

    if tid:

        src = vk_sources_lookup.get(f"{tid}|{p_min}|{p_max}|{s_min}|{s_max}")

    if not src and tid:

        src = vk_sources_lookup.get(f"{tid}|{p1}|{p2}|{s1}|{s2}")

    if not src:

        src = vk_sources_lookup.get(f"global|{p_min}|{p_max}|{s_min}|{s_max}")

    if not src and tid:

        src = vk_sources_lookup.get(f"{tid}|{p_min}|{p_max}")

        

    if src:

        if src.get('vk_url') and '?post=' in src['vk_url']:

            m_dict['vk_url'] = src['vk_url']

        if src.get('video_url'):

            m_dict['video_url'] = src['video_url']

            

    return m_dict

    s1 = int(m_dict.get('s1', 0))

    s2 = int(m_dict.get('s2', 0))

    p_min, p_max = min(p1, p2), max(p1, p2)

    s_min, s_max = min(s1, s2), max(s1, s2)

    

    s_name = str(m_dict.get('season', '')).lower()

    tid = None

    for k, v in TOPIC_MAP_BY_NAME.items():

        if k in s_name:

            tid = v

            break

            

    src = None

    if tid:

        src = vk_sources_lookup.get(f"{tid}|{p_min}|{p_max}|{s_min}|{s_max}")

    if not src:

        src = vk_sources_lookup.get(f"global|{p_min}|{p_max}|{s_min}|{s_max}")

        

    if src:

        # STRICT RULE: ONLY attach vk_url if it has ?post= (exact comment link!)

        # Never attach raw topic links without ?post=

        if src.get('vk_url') and '?post=' in src['vk_url']:

            m_dict['vk_url'] = src['vk_url']

        if src.get('video_url'):

            m_dict['video_url'] = src['video_url']

            

    return m_dict



# Alias normalization

ALIAS_MAP = {

    "TransSister": "Transistor",

    "transsister": "Transistor",

    "transistor": "Transistor",

    "Kirpich": "Кирпич57",

    "kirpich": "Кирпич57",

    "kirpich57": "Кирпич57",

    "Kirpich57": "Кирпич57",

    "кирпич": "Кирпич57",

    "кирпич57": "Кирпич57",

    "Yoxter": "yoxter",

    "Leon-Udomlya": "leonudomlya",

    "leon-udomlya": "leonudomlya",

    "Леон": "leonudomlya",

    "леон": "leonudomlya",

    "леонид": "leonudomlya",

    "knucklesss": "Aeris",

    "knuckles": "Aeris",

    "наклз": "Aeris",

    "Palka Palych": "PacnyTHuK",

    "Palka Palych, 2019 г.": "PacnyTHuK",

    "палыч": "PacnyTHuK",

    "палка": "PacnyTHuK",

    "палка палыч": "PacnyTHuK",

    "распутник": "PacnyTHuK",

    "распутhuk": "PacnyTHuK",

    "palych": "PacnyTHuK",

    "Enot": "E_not",

    "enot": "E_not",

    "e_not": "E_not",

    "Роджер": "Веселый Роджер",

    "роджер": "Веселый Роджер",

    "rodger": "Веселый Роджер",

    "веселый роджер": "Веселый Роджер",

    "Cent": "Centurion",

    "CentZloy": "Centurion",

    "Cent про RVD": "Centurion",

    "centurion": "Centurion",

    "сenturion": "Centurion",

    "цент": "Centurion",

    "валера": "Centurion",

    "TubusTD": "tubustd",

    "tubustd": "tubustd",

    "тубус": "tubustd",

    "BOP95": "BOР95",

    "ВОР95": "BOР95",

    "вор95": "BOР95",

    "вор": "BOР95",

    "bop213": "BOР95",

    "RVD": "RVD (МГБ)",

    "мгб": "RVD (МГБ)",

    "рвд": "RVD (МГБ)",

    "xakofear": "RVD (МГБ)",
    "exyxea": "RVD (МГБ)",
    "Exyxea": "RVD (МГБ)",
    "ехухеа": "RVD (МГБ)",
    "Ехухеа": "RVD (МГБ)",
    "1путин": "PacnyTHuK",
    "1putin": "PacnyTHuK",
    "1-путин": "PacnyTHuK",
    "1_путин": "PacnyTHuK",

    "Dune про вора и рвд": "Dune",

    "Romario про выборы": "Romario",

    "юлий": "Yuliy_Cezar",

    "цезарь": "Yuliy_Cezar",

    "juliy cezar": "Yuliy_Cezar",

    "juliy_cezar": "Yuliy_Cezar",

    "Juliy_Cezar": "Yuliy_Cezar",

    "yuliy cezar": "Yuliy_Cezar",

    "yuliy_cezar": "Yuliy_Cezar",

    "cezar": "Yuliy_Cezar",

    "bzk": "Cyneprepou4uk",

    "супергеройчик": "Cyneprepou4uk",

    "buba": "Huba Buba",

    "huba": "Huba Buba",

    "буба": "Huba Buba",

    "hubabuba": "Huba Buba",

    "huba_buba_5": "Huba Buba",

    "huba_buba": "Huba Buba",

    "exponat": "Huba Buba",

    "exponta": "Huba Buba",

    "cohle": "Rustin Cohle",

    "rustin": "Rustin Cohle",

    "rustin_cohle": "Rustin Cohle",

    "rustinchole": "Rustin Cohle",

    "pushistik": "FC Pushistik",

    "pushistiк": "FC Pushistik",

    "пушистик": "FC Pushistik",

    "fc pushistik": "FC Pushistik",

    "киприот": "Kipriot",

    "kipriot91": "Kipriot",

    "липтон": "Буц",

    "lipt0n": "Буц",

    "lipton": "Буц",

    "LiptOn": "Буц",

    "техас": "Texas",

    "техаs": "Texas",

    "тexas": "Texas",

    "texas": "Texas",

    "псих": "psycho",

    "psycho": "psycho",

    "ussr": "kot-from-ussr",

    "kot-from-ussr": "kot-from-ussr",

    "сталин": "Stalin",

    "stalin": "Stalin",

    "аоши": "Aoshi",

    "aoshi": "Aoshi",

    "изотоп": "izzzotope",

    "izzotop": "izzzotope",

    "izzzoope": "izzzotope",

    "izzzotop": "izzzotope",

    "izzzotope": "izzzotope",

    "бубнов": "Bubnov",

    "bubnov": "Bubnov",

    "tymoschuk": "Bubnov",

    "ванчоус": "wanchous",

    "wanchous": "wanchous",

    "дюныч": "Dune",

    "дюн": "Dune",

    "легнахар": "Legnahar",

    "legnahar": "Legnahar",

    "ромол": "Romol",

    "romol": "Romol",

    "atremis": "artemis",

    "artemis": "artemis",

    "danlavis": "Dan_Lavis",

    "dan_lavis": "Dan_Lavis",

    "joeduffy": "Joe Duffy",

    "duffy": "Joe Duffy",

    "joe duffy": "Joe Duffy",

    "knorra": "Zupka Knorra",

    "zupka knorra": "Zupka Knorra",

    "claus": "Santa Claus",

    "santa claus": "Santa Claus",

    "wendefit": "Wenderfit",

    "ric": "Ric25",

    "rik25": "Ric25",

    "msfly": "Mcfly",

    "mcfly": "Mcfly",

    "shadow": "Mag.of.Shadow",

    "mag.of.shadow": "Mag.of.Shadow",

    "дядюшка_ау": "Дядюшка АУ",

    "дядюшка ау": "Дядюшка АУ",

    "dinamik": "Dynamik",

    "dynamik": "Dynamik",

    "есtоpower": "ectoPower",

    "ectopower": "ectoPower",

    "экто": "ectoPower",

    "таёда": "Taeda",

    "таеда": "Taeda",

    "taeda": "Taeda",
    "ruby": "ruby",
    "ruby": "ruby",
    "blanko": "ruby",
    "бланко": "ruby",
    "руби": "ruby",

    "редин": "Romix",

    "chokopie": "Chocopie",

    "chocopie": "Chocopie",

    "сhocopie": "Chocopie",

    "armfly": "ArmFly",

    "fieryrvd": "RVD (МГБ)",
    "fierykelsen": "RVD (МГБ)",
    "fierykeles": "RVD (МГБ)",

    "ajmeiker": "AJ_Maker",

    "maker": "AJ_Maker",

    "aj_maker": "AJ_Maker",

    "jamlight": "Jamlight",

    "aj maker": "AJ_Maker",

    "dan lavis": "Dan_Lavis",

    "кубик": "Kubik",

    "pacnythuk": "PacnyTHuK",

    "high": "High",

    "izzotope": "izzzotope",

}



ALIAS_MAP_LOWER = {k.lower(): v for k, v in ALIAS_MAP.items()}



def clean_alias(name):

    if not name: return name

    n = str(name).strip()

    if n in ALIAS_MAP: return ALIAS_MAP[n]

    if n.lower() in ALIAS_MAP_LOWER: return ALIAS_MAP_LOWER[n.lower()]

    # Strip team names in parentheses, e.g. "Kipriot (ФК Качки)" -> "Kipriot"

    if "(" in n and "мгб" not in n.lower():

        n_clean = re.sub(r'\s*\([^)]*\)', '', n).strip()

        if n_clean:

            return clean_alias(n_clean)

    return n



def norm_season(s):

    s = str(s).strip()

    m = re.search(r'(\d+)', s)

    if m: return f"Season {m.group(1)}"

    return s




SEASON_ROSTERS = {
    "1": {
        "Высшая (Единая) лига": [
            "mafuta", "Ric25", "WiSe", "Wenderfit", "high", "3aBuCTb", "Centurion", 
            "Flash", "Буц", "Kipriot", "Eg_or3", "Romario", "Rustin Cohle", "Gilmour", 
            "Memori", "E_not", "yoxter", "Буц"
        ]
    },
    "2": {
        "Высшая лига": [
            "mafuta", "Ric25", "Kunio", "ectoPower", "Memori", "Centurion", "Dr1N", 
            "BOР95", "Wenderfit", "yoxter", "Cyneprepou4uk", "Huba Buba", "artemis", 
            "Transistor", "RVD (МГБ)"
        ],
        "Младшая лига": [
            "Aeris", "Dopi", "Kubik", "Кирпич57", "E_not", "Kipriot", "Romario", 
            "Chocopie", "wanchous", "AJ_Maker", "Dan_Lavis", "Azatron", "Gilmour", 
            "Rustin Cohle", "Dynamik", "Damian", "Joe Duffy", "tubustd"
        ]
    },
    "3": {
        "Высшая лига": [
            "mafuta", "ectoPower", "Memori", "Kunio", "Huba Buba", "BOР95", "Ric25", 
            "Dr1N", "yoxter", "Centurion", "Kipriot"
        ],
        "Средняя лига": [
            "izzzotope", "Wenderfit", "tubustd", "Dopi", "Кирпич57", "Rustin Cohle", 
            "wanchous", "Kubik", "ArmFly", "Dune"
        ],
        "Дворовая лига": [
            "Aeris", "Chocopie", "AJ_Maker", "E_not", "starspro", "Texas", 
            "FC Pushistik", "Santa Claus", "Aoshi", "Flash"
        ]
    },
    "4": {
        "Высшая лига": [
            "mafuta", "ectoPower", "Ric25", "Kunio", "Memori", "Kipriot", "BOР95", 
            "izzzotope", "Dopi", "ArmFly", "Transistor", "Буц"
        ],
        "Средняя лига": [
            "Centurion", "yoxter", "tubustd", "Rustin Cohle", "Wenderfit", "Кирпич57", 
            "Texas", "FC Pushistik", "Romix", "high", "psycho"
        ],
        "Дворовая лига": [
            "wanchous", "Kubik", "Flash", "AJ_Maker", "Aeris", "Chocopie", "Aoshi", 
            "Gilmour", "Jamlight", "Stalin", "Zupka Knorra", "3aBuCTb", "Dune", "starspro"
        ]
    },
    "5": {
        "Высшая лига": [
            "mafuta", "ectoPower", "Буц", "Kipriot", "izzzotope", "Kunio", "Ric25", 
            "FC Pushistik", "PacnyTHuK", "Memori"
        ],
        "Средняя лига": [
            "Romix", "Texas", "Centurion", "psycho", "Rustin Cohle", "Flash", 
            "Aeris", "RVD (МГБ)", "Wenderfit"
        ],
        "Дворовая лига": [
            "yoxter", "Кирпич57", "Kubik", "wanchous", "Chocopie", "Aoshi", 
            "Stalin", "Jamlight", "kot-from-ussr", "shmel"
        ]
    },
    "6": {
        "Высшая лига": [
            "ectoPower", "izzzotope", "mafuta", "Ric25", "Kunio", "FC Pushistik", 
            "Буц", "Kipriot", "Centurion", "Romix", "Transistor", "Huba Buba"
        ],
        "Средняя лига": [
            "Texas", "Aeris", "Rustin Cohle", "Wenderfit", "Jamlight", "Кирпич57", 
            "Cyneprepou4uk", "Memori", "Dopi", "Bubnov", "Rock", "Greyson"
        ],
        "Дворовая лига": [
            "Aoshi", "yoxter", "Dynamik", "Dune", "E_not", "kot-from-ussr", 
            "AJ_Maker", "Mag.of.Shadow", "PacnyTHuK", "Legnahar", "Дядюшка АУ", 
            "Mcfly", "Que", "Веселый Роджер", "Chabby_59"
        ]
    },
    "7": {
        "Высшая лига": [
            "Memori", "mafuta", "Kunio", "Romix", "ectoPower", "Cyneprepou4uk", 
            "Bubnov", "RVD (МГБ)", "Ric25"
        ],
        "Средняя лига": [
            "Jamlight", "Dune", "Yuliy_Cezar", "Dynamik", "TEXAS", "gagagatch", 
            "yoxter", "Kubik", "leonudomlya", "E_not", "Aeris", "Centurion"
        ],
        "Дворовая лига": [
            "Веселый Роджер", "lenin1st", "Taeda", "Anubis", "ruby", "daz", 
            "wanchous", "Legnahar", "Romol", "RASH", "Vasya1995", "JohnnyBravo"
        ]
    },
    "8": {
        "Высшая лига": [
            "Cyneprepou4uk", "Kunio", "Memori", "PacnyTHuK", "RVD (МГБ)", 
            "Ric25", "Romix", "ectoPower", "leonudomlya"
        ],
        "Средняя лига": [
            "Aeris", "Dune", "E_not", "Jamlight", "Kubik", "RASH", 
            "Yuliy_Cezar", "Буц", "Кирпич57"
        ],
        "Дворовая лига": [
            "BigPlay", "Sokol", "TBP_Machiavelli", "Taeda", "ruby", 
            "daz", "frzz", "yoxter", "Сахарок"
        ]
    },
    "9": {
        "Высшая лига": [
            "Aeris", "Kunio", "Memori", "Ric25", "Rock", "Romix", 
            "ectoPower", "leonudomlya"
        ],
        "Средняя лига": [
            "Dune", "Jamlight", "Kubik", "Yuliy_Cezar", 
            "frzz", "yoxter", "Кирпич57"
        ],
        "Дворовая лига": [
            "Hanter", "Ryumaru", "Spartacus", "Taeda", "mikr84", 
            "ruby", "Веселый Роджер"
        ]
    }
}

def resolve_season_league_and_tour(m, s_name, p1, p2):
    tourn = str(m.get("tournament") or "")
    leg = str(m.get("league") or "")
    st = str(m.get("stage") or "")
    
    # 1. Cup / Playoff check
    if "Кубок" in tourn or "Кубок" in leg or m.get("is_playoff") or any(x in st.lower() for x in ["финал", "1/16", "1/8", "1/4", "1/2"]):
        match_league = "Кубок лиг"
        match_tour = st if st and st != "Регулярный сезон" else "Кубок лиг"
        return match_league, match_tour
        
    # 2. League in tournament string
    if "Дворов" in tourn or "Дворов" in leg:
        match_league = "Дворовая лига"
    elif "Средн" in tourn or "Средн" in leg:
        match_league = "Средняя лига"
    elif "Высш" in tourn or "Высш" in leg:
        match_league = "Высшая лига"
    else:
        # Fallback to roster
        s_num = "8" if "8" in s_name else "9"
        r = SEASON_ROSTERS.get(s_num, {})
        p1_low, p2_low = p1.lower().strip(), p2.lower().strip()
        found = False
        for l_name, players in r.items():
            p_lows = [x.lower().strip() for x in players]
            if p1_low in p_lows and p2_low in p_lows:
                match_league = l_name
                found = True
                break
        if not found:
            for l_name, players in r.items():
                p_lows = [x.lower().strip() for x in players]
                if p1_low in p_lows or p2_low in p_lows:
                    match_league = l_name
                    found = True
                    break
        if not found:
            match_league = "Высшая лига"

    match_tour = m.get("tour") or st or "Регулярный сезон"
    return match_league, match_tour

combined_matches = []

seen = set()



# 1. Season 1 from early_matches

for m in early_matches:

    s = norm_season(m.get("season", ""))

    if s == "Season 1":

        p1 = clean_alias(m.get("p1"))

        p2 = clean_alias(m.get("p2"))

        if not p1 or not p2 or p1 == p2: continue

        s1 = int(m.get("s1", 0))

        s2 = int(m.get("s2", 0))

        combined_matches.append({

            "season": s, "league": m.get("league", "Высшая (Единая) лига"),

            "tour": m.get("tour", "1 Круг"),

            "stage": m.get("stage", "1 Круг"),

            "p1": p1, "p2": p2, "s1": s1, "s2": s2,

            "ot": m.get("ot", False), "pk": m.get("pk", False),

            "source": "season_1_archive"

        })



# 2. Seasons 2-7 from official wiki calendars

for m in wiki_matches:

    s = norm_season(m.get("season", ""))

    p1 = clean_alias(m.get("p1"))

    p2 = clean_alias(m.get("p2"))

    if not p1 or not p2 or p1 == p2: continue

    s1 = int(m.get("s1", 0))

    s2 = int(m.get("s2", 0))

    league = m.get("league", "Высшая лига")

    tour = m.get("tour", "1 Тур")

    ot = m.get("ot", False)

    

    key = (s, league, tour, min(p1, p2), max(p1, p2), s1, s2)

    cnt = sum(1 for x in seen if x[:5] == key[:5])

    if cnt < 2:

        seen.add((s, league, tour, min(p1, p2), max(p1, p2), cnt, s1, s2))

        combined_matches.append({

            "season": s, "league": league, "tour": tour,

            "stage": tour,

            "p1": p1, "p2": p2, "s1": s1, "s2": s2,

            "ot": ot, "pk": ot,

            "source": m.get("source", "vk_wiki")

        })



# 3. Seasons 8 and 9 from base_matches (Sportcup API)

for m in base_matches:

    s = norm_season(m.get("season", ""))

    if s in ["Season 8", "Season 9"]:

        p1 = clean_alias(m.get("p1"))

        p2 = clean_alias(m.get("p2"))

        if not p1 or not p2 or p1 == p2: continue

        s1 = int(m.get("s1", 0))

        s2 = int(m.get("s2", 0))

        match_league, match_tour = resolve_season_league_and_tour(m, s, p1, p2)
        is_tech = m.get("is_technical", False) or (s == "Season 8" and (p1 == "RVD (МГБ)" or p2 == "RVD (МГБ)"))

        combined_matches.append({

            "season": s, "league": match_league,

            "tour": match_tour,

            "stage": match_tour,

            "p1": p1, "p2": p2, "s1": s1, "s2": s2,

            "ot": m.get("ot", False), "pk": m.get("pk", False),

            "source": "sportcup_api",

            "is_technical": is_tech,

            "is_forfeit": is_tech,

            "note": "Техническое поражение (снят с турнира)" if is_tech else ""

        })



# 4. Extra playoff / cup matches from vk comments

for m in vk_matches:

    s = norm_season(m.get("season", ""))

    p1 = clean_alias(m.get("p1"))

    p2 = clean_alias(m.get("p2"))

    if not p1 or not p2 or p1 == p2: continue

    s1 = int(m.get("s1", 0))

    s2 = int(m.get("s2", 0))

    league = m.get("league", "Высшая лига")

    

    existing = [x for x in combined_matches if x["season"] == s and {x["p1"], x["p2"]} == {p1, p2}]

    is_dup = False

    for em in existing:

        if (em["s1"] == s1 and em["s2"] == s2) or (em["s1"] == s2 and em["s2"] == s1):

            is_dup = True

            break

    if not is_dup and len(existing) < 4:

        combined_matches.append({

            "season": s, "league": league,

            "tour": m.get("tour", "Плей-офф / Кубок"),

            "stage": m.get("stage", "Плей-офф / Кубок"),

            "p1": p1, "p2": p2, "s1": s1, "s2": s2,

            "ot": m.get("ot", False), "pk": m.get("pk", False),

            "source": "vk_comments_playoff"

        })



print(f"Total verified combined matches: {len(combined_matches)}")



# Enrich combined matches with VK sources before building player records

for cm in combined_matches:

    enrich_vk_source(cm)



# Load tournaments early to attach to player match history

with open("team_tournaments_data.json", "r", encoding="utf-8") as tt_f:

    team_tournaments = json.load(tt_f)



with open("special_tournaments_data.json", "r", encoding="utf-8") as st_f:

    special_tournaments = json.load(st_f)



# 2. Player match records (Enriched with branches: Seasons, Teams 2x2, Club, Penalty, Blitz)

player_matches = defaultdict(list)

player_stats_addon = defaultdict(lambda: {

    "reg_w": 0, "ot_w": 0, "pk_w": 0,

    "reg_l": 0, "ot_l": 0, "pk_l": 0,

    "draws": 0

})



# A. Regular Seasons Matches (1-9)

for m in combined_matches:

    p1 = m["p1"]

    p2 = m["p2"]

    s1 = m["s1"]

    s2 = m["s2"]

    ot = m.get("ot", False)

    pk = m.get("pk", False)

    season = m.get("season", "Season 1")

    s_digits = re.findall(r'\d+', season)

    s_num = int(s_digits[0]) if s_digits else 1



    stage = m.get("stage") or m.get("tour") or "Матч"

    league = m.get("league", "Высшая лига")



    is_tech = m.get("is_technical", False) or m.get("is_forfeit", False)
    if is_tech:
        p1_res = "ТП (ПОРАЖЕНИЕ)" if p1 == "RVD (МГБ)" else "ТП (ПОБЕДА)"
        p2_res = "ТП (ПОРАЖЕНИЕ)" if p2 == "RVD (МГБ)" else "ТП (ПОБЕДА)"
    else:
        p1_res = "ПОБЕДА" if s1 > s2 else ("ПОРАЖЕНИЕ" if s1 < s2 else "НИЧЬЯ")
        p2_res = "ПОБЕДА" if s2 > s1 else ("ПОРАЖЕНИЕ" if s2 < s1 else "НИЧЬЯ")



    p1_m_data = {

        "category": "season",

        "cat_label": f"🏆 Сезон {s_num}",

        "tournament": f"Официальный Чемпионат (Сезон {s_num})",

        "season": season,

        "season_num": s_num,

        "stage": stage,

        "league": league,

        "partner": None,

        "opponent": p2,

        "score_for": s1, "score_against": s2,

        "result": p1_res, "ot": ot, "pk": pk

    }

    if is_tech:
        p1_m_data["is_technical"] = True
        p1_m_data["note"] = m.get("note", "Техническое поражение (снят с турнира)")
    if m.get("vk_url"): p1_m_data["vk_url"] = m["vk_url"]

    if m.get("video_url"): p1_m_data["video_url"] = m["video_url"]

    if m.get("vk_text"): p1_m_data["vk_text"] = m["vk_text"]

    if m.get("vk_date"): p1_m_data["vk_date"] = m["vk_date"]

    if m.get("vk_page"): p1_m_data["vk_page"] = m["vk_page"]

    player_matches[p1].append(p1_m_data)



    p2_m_data = {

        "category": "season",

        "cat_label": f"🏆 Сезон {s_num}",

        "tournament": f"Официальный Чемпионат (Сезон {s_num})",

        "season": season,

        "season_num": s_num,

        "stage": stage,

        "league": league,

        "partner": None,

        "opponent": p1,

        "score_for": s2, "score_against": s1,

        "result": p2_res, "ot": ot, "pk": pk

    }

    if is_tech:
        p2_m_data["is_technical"] = True
        p2_m_data["note"] = m.get("note", "Техническое поражение (снят с турнира)")
    if m.get("vk_url"): p2_m_data["vk_url"] = m["vk_url"]

    if m.get("video_url"): p2_m_data["video_url"] = m["video_url"]

    if m.get("vk_text"): p2_m_data["vk_text"] = m["vk_text"]

    if m.get("vk_date"): p2_m_data["vk_date"] = m["vk_date"]

    if m.get("vk_page"): p2_m_data["vk_page"] = m["vk_page"]

    player_matches[p2].append(p2_m_data)



    if is_tech:
        if p1 == "RVD (МГБ)":
            player_stats_addon[p1]["tech_l"] = player_stats_addon[p1].get("tech_l", 0) + 1
            player_stats_addon[p2]["reg_w"] += 1
        elif p2 == "RVD (МГБ)":
            player_stats_addon[p2]["tech_l"] = player_stats_addon[p2].get("tech_l", 0) + 1
            player_stats_addon[p1]["reg_w"] += 1
    elif s1 > s2:

        if pk: player_stats_addon[p1]["pk_w"] += 1; player_stats_addon[p2]["pk_l"] += 1

        elif ot: player_stats_addon[p1]["ot_w"] += 1; player_stats_addon[p2]["ot_l"] += 1

        else: player_stats_addon[p1]["reg_w"] += 1; player_stats_addon[p2]["reg_l"] += 1

    elif s2 > s1:

        if pk: player_stats_addon[p2]["pk_w"] += 1; player_stats_addon[p1]["pk_l"] += 1

        elif ot: player_stats_addon[p2]["ot_w"] += 1; player_stats_addon[p1]["ot_l"] += 1

        else: player_stats_addon[p2]["reg_w"] += 1; player_stats_addon[p1]["reg_l"] += 1

    else:

        player_stats_addon[p1]["draws"] += 1

        player_stats_addon[p2]["draws"] += 1



# B. Special Tournaments Matches (Club Offseason, Penalty, Blitz, Solo)

for t_idx, t in enumerate(special_tournaments):

    t_title = t.get("title", "Спецтурнир")

    cat = "special"

    cat_label = "⚡ Спецтурнир"

    if "пенальт" in t_title.lower():

        cat = "penalty"

        cat_label = "🥅 Пенальти"

    elif "межсез" in t_title.lower() or "клубн" in t_title.lower():

        cat = "club"

        cat_label = "🏖️ Межсезонье"

    elif "молодёж" in t_title.lower():

        cat = "youth"

        cat_label = "🌱 Молодёжка"

    elif "блиц" in t_title.lower():

        cat = "blitz"

        cat_label = "⚡ Блиц"



    for m in t.get("matches", []):

        p1_raw = m.get("p1")

        p2_raw = m.get("p2")

        sc = m.get("score", "")

        if not p1_raw or not p2_raw or ":" not in sc: continue

        parts = sc.split(":")

        try:

            s1 = int(parts[0].strip())

            s2 = int(parts[1].strip())

        except:

            continue



        p1 = clean_alias(p1_raw)

        p2 = clean_alias(p2_raw)

        if not p1 or not p2 or p1 == p2: continue



        stage = m.get("stage") or m.get("tour") or "Матч"

        league = m.get("league", "Спецтурнир")

        is_pk = "пенальт" in t_title.lower() or m.get("pk", False)



        p1_res = "ПОБЕДА" if s1 > s2 else ("ПОРАЖЕНИЕ" if s1 < s2 else "НИЧЬЯ")

        p2_res = "ПОБЕДА" if s2 > s1 else ("ПОРАЖЕНИЕ" if s2 < s1 else "НИЧЬЯ")



        spec_m_obj = {"p1": p1, "p2": p2, "s1": s1, "s2": s2, "season": t_title}

        enrich_vk_source(spec_m_obj)

        

        sp1 = {

            "category": cat,

            "cat_label": cat_label,

            "tournament": t_title,

            "season": t.get("season_year", "Спецтурнир"),

            "season_num": 100 + t_idx,

            "stage": stage,

            "league": league,

            "partner": None,

            "opponent": p2,

            "score_for": s1, "score_against": s2,

            "result": p1_res, "ot": False, "pk": is_pk

        }

        if spec_m_obj.get("vk_url"): sp1["vk_url"] = spec_m_obj["vk_url"]

        if spec_m_obj.get("video_url"): sp1["video_url"] = spec_m_obj["video_url"]

        player_matches[p1].append(sp1)



        sp2 = {

            "category": cat,

            "cat_label": cat_label,

            "tournament": t_title,

            "season": t.get("season_year", "Спецтурнир"),

            "season_num": 100 + t_idx,

            "stage": stage,

            "league": league,

            "partner": None,

            "opponent": p1,

            "score_for": s2, "score_against": s1,

            "result": p2_res, "ot": False, "pk": is_pk

        }

        if spec_m_obj.get("vk_url"): sp2["vk_url"] = spec_m_obj["vk_url"]

        if spec_m_obj.get("video_url"): sp2["video_url"] = spec_m_obj["video_url"]

        player_matches[p2].append(sp2)



# C. Team Tournaments Matches (2x2)

for t_idx, t in enumerate(team_tournaments):

    t_title = t.get("title", "Командный чемпионат")

    for m in t.get("matches", []):

        t1_raw = m.get("t1", "")

        t2_raw = m.get("t2", "")

        sc = m.get("score", "")

        if not t1_raw or not t2_raw or ":" not in sc: continue

        parts = sc.split(":")

        try:

            s1 = int(parts[0].strip())

            s2 = int(parts[1].strip())

        except:

            continue



        def parse_pair(s):

            if "&" in s: pts = [clean_alias(x) for x in s.split("&")]

            elif "/" in s: pts = [clean_alias(x) for x in s.split("/")]

            else: pts = [clean_alias(s)]

            return [x for x in pts if x]



        p1_list = parse_pair(t1_raw)

        p2_list = parse_pair(t2_raw)

        stage = m.get("stage") or m.get("tour") or "Матч 2х2"

        league = m.get("league", "Командная лига")



        p1_res = "ПОБЕДА" if s1 > s2 else ("ПОРАЖЕНИЕ" if s1 < s2 else "НИЧЬЯ")

        p2_res = "ПОБЕДА" if s2 > s1 else ("ПОРАЖЕНИЕ" if s2 < s1 else "НИЧЬЯ")



        for pl in p1_list:

            partner = " & ".join([x for x in p1_list if x != pl]) or None

            player_matches[pl].append({

                "category": "team",

                "cat_label": "👥 2х2 Командник",

                "tournament": t_title,

                "season": t.get("season_year", "Командный 2х2"),

                "season_num": 200 + t_idx,

                "stage": stage,

                "league": league,

                "partner": partner,

                "opponent": t2_raw,

                "score_for": s1, "score_against": s2,

                "result": p1_res, "ot": False, "pk": False

            })



        for pl in p2_list:

            partner = " & ".join([x for x in p2_list if x != pl]) or None

            player_matches[pl].append({

                "category": "team",

                "cat_label": "👥 2х2 Командник",

                "tournament": t_title,

                "season": t.get("season_year", "Командный 2х2"),

                "season_num": 200 + t_idx,

                "stage": stage,

                "league": league,

                "partner": partner,

                "opponent": t1_raw,

                "score_for": s2, "score_against": s1,

                "result": p2_res, "ot": False, "pk": False

            })



# D. Strict Chronological Sort for Every Player!

def match_sort_key(m):

    s_num = m.get("season_num", 999)

    stage = str(m.get("stage", ""))

    tour_num = 99

    digits = re.findall(r'\d+', stage)

    if digits:

        tour_num = int(digits[0])

    elif "плей" in stage.lower() or "кубок" in stage.lower() or "финал" in stage.lower():

        tour_num = 150

    return (s_num, tour_num, stage)



for pl_name in player_matches:

    player_matches[pl_name].sort(key=match_sort_key)



default_avatars = {

    "Transistor": "https://api.dicebear.com/7.x/bottts/svg?seed=Transistor&backgroundColor=183c5c",

    "mafuta": "https://api.dicebear.com/7.x/bottts/svg?seed=Mafuta&backgroundColor=183c5c",

    "WiSe": "https://api.dicebear.com/7.x/bottts/svg?seed=WiSe&backgroundColor=183c5c",

    "RVD (МГБ)": "Легендарный первопроходец Сезонов 1, 2, 4, 7 (в S2 выступал под ником FieryKelsen). Более 60% побед в противостояниях с титанами сцены.",

    "Huba Buba": "https://api.dicebear.com/7.x/bottts/svg?seed=HubaBuba&backgroundColor=183c5c",

    "izzzotope": "https://api.dicebear.com/7.x/bottts/svg?seed=Izzzotope&backgroundColor=183c5c",

    "Yuliy_Cezar": "https://api.dicebear.com/7.x/bottts/svg?seed=YuliyCezar&backgroundColor=183c5c",

    "BOР95": "https://api.dicebear.com/7.x/bottts/svg?seed=Vor95&backgroundColor=183c5c",

    "Kipriot": "https://api.dicebear.com/7.x/bottts/svg?seed=Kipriot&backgroundColor=183c5c",

    "LiptOn": "https://api.dicebear.com/7.x/bottts/svg?seed=LiptOn&backgroundColor=183c5c",

    "Bubnov": "https://api.dicebear.com/7.x/bottts/svg?seed=Bubnov&backgroundColor=183c5c",

}



CORE_ACTIVE_COMMUNITY = [

    "ectoPower", "PacnyTHuK", "Romix", "Kunio", "Cyneprepou4uk", "Rock",

    "leonudomlya", "Ric25", "Memori", "Буц", "Aeris", "Kubik",

    "RASH", "Jamlight", "Dune", "Sokol", "E_not", "Кирпич57", "Hanter",

    "daz", "Taeda", "Веселый Роджер"

]



HALL_OF_FAME_LEGENDS = [

    "mafuta", "Transistor", "RVD (МГБ)", "Huba Buba", "izzzotope",

    "Yuliy_Cezar", "WiSe", "BOР95", "Kipriot", "Буц",

    "Bubnov"

]



HOF_REASONS = {

    "mafuta": "Величайший первопроходец и 3-кратный чемпион Высшей лиги подряд (Сезоны 1, 2, 3). 4 Кубка Лиги, 100 побед в элите. Безоговорочный первый GOAT в истории сообщества.",

    "Transistor": "Чемпион Высшей лиги Season 4, совершивший главный апсет в истории — разгром Kunio 4:0 и свержение непобедимого Мафуты в финале. Финалист Season 6. Космический винрейт 81.8% в элите.",

    "RVD (МГБ)": "Легендарный первопроходец Сезонов 1, 2, 4, 7 (в S2 выступал под ником FieryKelsen). Более 60% побед в противостояниях с титанами сцены.",

    "Huba Buba": "Один из самых грозных форвардов золотой эпохи. 68 матчей в Высшей лиге (40 побед, 58.8% WR), финалист мейджоров и постоянный участник топ-4.",

    "izzzotope": "Многолетний элитный бомбардир Высшей лиги (Сезоны 4, 5, 6). Финалист чемпионата, мастер комбинационной игры, 65 матчей на высшем соревновательном уровне.",

    "Yuliy_Cezar": "Доминатор Высшей лиги эпохи T355. 32 матча в Высшей лиге, 23 победы с феноменальным винрейтом 71.9% против сильнейших топов.",

    "WiSe": "Бронзовый призёр первого исторического чемпионата 2015 года (Сезон 1), показавший яркую игру в дебютном первенстве лиги.",

    "BOР95": "Бессменный участник Высшей лиги первых сезонов (S2, S3, S4). 45 матчей в элите, гроза фаворитов в плей-офф.",

    "Kipriot": "Ветеран пяти сезонов Высшей лиги (S2–S6). 78 матчей против абсолютной элиты сообщества.",

    "Буц": "Первопроходец Высшей лиги Сезона 1 (в ранних сезонах выступал как LiptOn). Ветеран и активный боец всех 9 сезонов NST со 115+ матчами за карьеру.",

    "Bubnov": "Яркая звезда Высшей лиги Сезонов 6 и 7. 58.8% побед в противостояниях с титанами сцены.",

}



HOF_PEAK_ELO = {

    "mafuta": 1785.0,

    "Transistor": 1735.0,

    "RVD (МГБ)": 1685.0,

    "Yuliy_Cezar": 1665.0,

    "Huba Buba": 1640.0,

    "izzzotope": 1625.0,

    "WiSe": 1605.0,

    "BOР95": 1575.0,

    "Bubnov": 1565.0,

    "Kipriot": 1550.0,

    "Буц": 1530.0,

}



# Load NST Community Quotes

nst_quotes_raw = []

try:

    with open("nst_quotes.json", "r", encoding="utf-8") as f:

        nst_quotes_raw = json.load(f)

except Exception as e:

    print("Warning loading nst_quotes.json:", e)



AUTHOR_PLAYER_ALIASES = {
    'липтон': 'Буц',
    'lipton': 'Буц',
    'lipt0n': 'Буц',

    'aeris': 'Aeris',

    'bop95': 'BOР95',

    'вор95': 'BOР95',

    'davitel': 'Davitel',

    'dune': 'Dune',

    'dune про вора и рвд': 'Dune',

    'enot': 'E_not',

    'e_not': 'E_not',

    'hanter': 'Hanter',

    'jamlight': 'Jamlight',

    'kirpich57': 'Кирпич57',

    'кирпич57': 'Кирпич57',

    'kubik': 'Kubik',

    'kunio': 'Kunio',

    'memori': 'Memori',

    'rock': 'Rock',

    'sokol': 'Sokol',

    'taeda': 'Taeda',

    'transistor': 'Transistor',

    'daz': 'daz',

    'ectopower': 'ectoPower',

    'mafuta': 'mafuta',

    'rvd': 'RVD (МГБ)',

    'роджер': 'Веселый Роджер',

    'веселый роджер': 'Веселый Роджер',

}



CANONICAL_PLAYER_QUOTES = {

    'ectoPower': 'Две кнопки вверх, две кнопки вниз, прыжок с локтя, удар в карниз',

    'mafuta': 'Без цитат мы всего лишь безликое скопище ретрогномов, заблудившихся в ретрогейском лесу',

    'RVD (МГБ)': 'Нам нужно больше организаторов про запас, чтобы когда у одного крыша съезжает, второй заменял',

    'Memori': 'Есть два эмуля, на одном лаги точеные, на другом задержки дроченые. За какой сам сядешь, за какой Хубу посадишь?',

    'Transistor': 'В руки бери!...Да это пиздец какой-то нахуй, я сейчас брошу смотреть, вы заебали, сука!!!',

    'BOР95': 'Пиздёжь! Я в три раза сильней и в два раза качественнее, а он отбил лбом нахуй!',

    'Rock': 'О, боже, оно не лагает! Как в это можно играть?',

    'daz': 'Вы либо админку снимите, либо трусы наденьте',

    'Jamlight': 'Если игрок не двигает сетку тогда сетка двигает игрока',

    'Kubik': 'я думаю на нст детей нет. если ты пришел на нст, то все, детство кончилось, забудь о нем',

    'Кирпич57': 'А ты вспомни, RVD, может ты обидел кого-нибудь?',

    'Dune': 'То ж НСТ, тут без гомосятины никак',

    'Sokol': 'Строчки вяжутся в стишок,\nЛавка греет тушу.\nДети какают в горшок,\nА Мафута - в душу',

    'Kunio': 'На морском песочке я Мафуту встретил, Вместе с Изотопом они играли в денди...',

    'Hanter': 'вы все ребят лучшие и даз не пизди тут но ты тоже красава',

    'E_not': 'Русский хентай с деревянными тентаклями',

    'Aeris': 'Ты просто можешь не осознавать, пидорас ты или нет, пока не попробуешь',

    'Веселый Роджер': 'По логике даза мы все умственно отсталые даже я капец бред',

    'Taeda': 'Я долго думал о никнейме, Откуда даз и почему, А он наверно ретрогеймер...',

    'Davitel': 'В смысле я лох, блять, я джентльмен!',

}



player_quotes_dict = {}

for q in nst_quotes_raw:

    auth = q.get('author', '').strip().lower()

    p_matched = AUTHOR_PLAYER_ALIASES.get(auth)

    if not p_matched:

        for alias_k, orig_p in AUTHOR_PLAYER_ALIASES.items():

            if alias_k in auth:

                p_matched = orig_p

                break

    if p_matched:

        if p_matched not in player_quotes_dict:

            player_quotes_dict[p_matched] = []

        player_quotes_dict[p_matched].append(q.get('text', '').replace('\xa0', ' ').strip())



CLUB_TEAMS_FILTER = {'Яжежал', 'Геймклуб', 'Мегадрайв', 'Пластиковый татарин', 'Рединский отряд'}

master_profiles_by_name = {p["player"]: p for p in master_db["power_rankings"]}



# Comprehensive list of ALL players in league history

all_league_players = set(CORE_ACTIVE_COMMUNITY + HALL_OF_FAME_LEGENDS + list(master_profiles_by_name.keys()))

for pl_name, p_m in player_matches.items():

    if pl_name not in CLUB_TEAMS_FILTER and len(p_m) > 0 and '&' not in pl_name and '/' not in pl_name:

        all_league_players.add(pl_name)



# 3. Process Comprehensive Master Profiles (Active + Legends + Veterans of All Leagues)

profiles = []

for name in sorted(all_league_players):

    p_matches = player_matches[name]

    add = player_stats_addon[name]

    tot = len(p_matches)

    if tot == 0 and name not in CORE_ACTIVE_COMMUNITY and name not in HALL_OF_FAME_LEGENDS:

        continue



    is_act = name in CORE_ACTIVE_COMMUNITY

    is_hof = name in HALL_OF_FAME_LEGENDS



    tech_l = sum(1 for m_item in p_matches if m_item.get("is_technical") and "ПОРАЖЕНИЕ" in m_item.get("result", ""))
    played_tot = tot - tech_l
    w = sum(1 for m in p_matches if m.get("result") in ["ПОБЕДА", "ТП (ПОБЕДА)"])

    l = sum(1 for m in p_matches if m.get("result") == "ПОРАЖЕНИЕ")

    d = sum(1 for m in p_matches if m.get("result") == "НИЧЬЯ")

    gf = sum(m.get("score_for", 0) for m in p_matches if not m.get("is_technical"))

    ga = sum(m.get("score_against", 0) for m in p_matches if not m.get("is_technical"))

    wr = round(w / played_tot * 100, 1) if played_tot > 0 else 0.0

    clutch_w = add["ot_w"] + add["pk_w"]

    clutch_tot = clutch_w + add["ot_l"] + add["pk_l"]

    clutch_wr = round(clutch_w / clutch_tot * 100, 1) if clutch_tot > 0 else 0.0



    # Calculate real last season & inactivity
    CURRENT_YEAR = 2024.5
    SEASON_YEAR_MAP = {
        1: 2015.5, 2: 2016.0, 3: 2016.5, 4: 2017.0,
        5: 2017.5, 6: 2018.0, 7: 2021.0, 8: 2023.0, 9: 2024.5
    }
    last_year = 0.0
    last_season_label = "Season 9" if is_act else "Архив"
    for m_item in p_matches:
        if m_item.get("is_technical"): continue
        s_str = str(m_item.get("season", ""))
        mat = re.search(r"Season\s*(\d+)", s_str, re.I)
        if mat:
            s_num = int(mat.group(1))
            y = SEASON_YEAR_MAP.get(s_num, 2016.0)
            if y > last_year:
                last_year = y
                last_season_label = f"Season {s_num}"
        elif "20" in s_str:
            mat_y = re.search(r"20\d\d", s_str)
            if mat_y:
                y = float(mat_y.group(0))
                if y > last_year:
                    last_year = y
    if last_year == 0.0:
        last_year = 2024.5 if is_act else 2016.5

    years_inact = max(0.0, round(CURRENT_YEAR - last_year, 1)) if not is_act else 0.0

    if is_act or years_inact <= 0.5:
        decay = 0.0
    elif years_inact <= 1.5:
        decay = 25.0
    else:
        decay = round(25.0 + (years_inact - 1.5) * 35.0, 1)

    if name in master_profiles_by_name:
        p = dict(master_profiles_by_name[name])
        league = p.get("league", "Средняя")
        raw_peak = p.get("peak_elo", 1400.0)
        raw_active = p.get("active_elo", 1400.0)
    else:
        leagues_played = set(m.get("league", "") for m in p_matches)
        if is_hof or any("высш" in x.lower() for x in leagues_played):
            league = "Высшая"
        elif any("перв" in x.lower() or "средн" in x.lower() for x in leagues_played):
            league = "Средняя"
        else:
            league = "Дворовая"
        div_base = 1400.0 if league == "Высшая" else (1300.0 if league == "Средняя" else 1200.0)
        raw_peak = div_base + (wr - 50.0) * 3.0
        raw_active = raw_peak

        p = {
            "player": name, "league": league, "status": "Инактив (Ветеран)",
            "archetype": "Ветеран сцены", "playstyle": "Классический NES стиль",
            "active_elo": 1200.0, "peak_elo": 1200.0, "decay_penalty": decay,
            "years_inactive": years_inact, "last_season": last_season_label,
            "gpg": round(gf / tot, 2) if tot > 0 else 0.0,
            "gapg": round(ga / tot, 2) if tot > 0 else 0.0,
            "spectacle_factor": 2.5, "ot_matches": add["ot_w"] + add["ot_l"],
            "ot_wins": add["ot_w"], "ot_losses": add["ot_l"],
            "ot_win_rate": round(add["ot_w"] / (add["ot_w"] + add["ot_l"]) * 100, 1) if (add["ot_w"] + add["ot_l"]) > 0 else 0.0,
            "playoff_matches": 0, "playoff_wins": 0, "playoff_losses": 0, "playoff_win_rate": 0.0,
            "clean_sheet_pct": 0.0, "failed_to_score": 0, "failed_to_score_pct": 0.0,
            "premier_titles": 3 if name == "mafuta" else (1 if name == "Transistor" else 0),
            "cup_titles": 4 if name == "mafuta" else (2 if name == "RVD (МГБ)" else 0),
            "minor_titles": 0, "major_finals": 1 if name in ["WiSe", "Huba Buba", "izzzotope", "Transistor", "mafuta"] else 0,
            "dominator_score": 100.0
        }

    conf = min(1.0, tot / 20.0) if tot > 0 else 0.0
    calibrated_skill = 1200.0 + (raw_peak - 1200.0) * conf
    peak_elo = HOF_PEAK_ELO.get(name, max(round(calibrated_skill, 1), round(raw_peak, 1)))

    if is_act:
        active_elo = round(max(1050.0, raw_active), 1)
        decay = 0.0
    else:
        active_elo = round(max(1050.0, calibrated_skill - decay), 1)

    p["active_elo"] = active_elo
    p["peak_elo"] = peak_elo
    p["decay_penalty"] = decay
    p["years_inactive"] = years_inact
    p["last_season"] = last_season_label



    # Strict Hall of Fame reason & peak ELO

    if is_hof:

        p["is_hall_of_fame"] = True

        p["hof_reason"] = HOF_REASONS.get(name, "Легендарный ветеран Высшей лиги NST.")

        p["peak_elo"] = HOF_PEAK_ELO.get(name, p["peak_elo"])

        p["status_badge"] = "Зал славы (Легенда)"

        p["status"] = "Зал славы"

        p["league"] = "Высшая"

    else:

        p["is_hall_of_fame"] = False

        p["hof_reason"] = None

        p["status_badge"] = "Активен (Сезон 9)" if is_act else f"Инактив ({p.get('league', 'Ветеран')})"



    p["matches"] = tot

    p["wins"] = w

    p["losses"] = l

    p["draws"] = d

    p["win_rate"] = wr

    p["goals_for"] = gf

    p["goals_against"] = ga

    p["goal_diff"] = gf - ga

    p["clean_sheets"] = sum(1 for m in p_matches if m.get("score_against") == 0)

    p["reg_wins"] = add["reg_w"]

    p["pk_wins"] = add["pk_w"]

    p["reg_losses"] = add["reg_l"]

    p["pk_losses"] = add["pk_l"]

    p["clutch_total"] = clutch_tot

    p["clutch_wins"] = clutch_w

    p["clutch_win_rate"] = clutch_wr

    p["match_history"] = p_matches

    p["is_active"] = is_act



    # Attach quote if available, else None (clean)

    p_quote = CANONICAL_PLAYER_QUOTES.get(name)

    if not p_quote and name in player_quotes_dict and player_quotes_dict[name]:

        p_quote = player_quotes_dict[name][0]

    p["quote"] = p_quote

    p["all_quotes"] = player_quotes_dict.get(name, [])



    if name in avatars:

        p["avatar"] = avatars[name]["avatar_url"]

        p["vk_name"] = avatars[name]["vk_name"]

        p["vk_id"] = avatars[name]["vk_id"]

        p["vk_domain"] = avatars[name]["domain"]

    else:

        p["avatar"] = default_avatars.get(name, f"https://api.dicebear.com/7.x/bottts/svg?seed={name}&backgroundColor=183c5c")

        p["vk_name"] = name

        p["vk_id"] = None

        p["vk_domain"] = None



    profiles.append(p)



# Sort profiles: Active first, then HoF Legends, then by rating descending

def profile_sort_order(p):

    act_order = 0 if p["is_active"] else (1 if p["is_hall_of_fame"] else 2)

    return (act_order, -p["active_elo"], -p["matches"])



profiles.sort(key=profile_sort_order)







# Sort: Active first by active_elo, then Inactive by peak_elo

profiles.sort(key=lambda p: (1 if p["is_active"] else 0, p["active_elo"]), reverse=True)



# 4. Attach seasons matches (enriched with VK comments and video streams)

for cm in combined_matches:

    enrich_vk_source(cm)



import prepare_site_data

HISTORIC_CUPS_DATA = {
  "Season 2": {
    "champion": "mafuta",
    "runner_up": "Kunio",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "Kipriot",
        "p2": "Romario",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Transistor",
        "p2": "wanchous",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Dopi",
        "p2": "Кирпич57",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "TubusTD",
        "p2": "Rustin Cohle",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Dopi",
        "p2": "Dr1N",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Transistor",
        "p2": "BOР95",
        "s1": 3,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "TubusTD",
        "p2": "Ric25",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Huba Buba",
        "p2": "Kipriot",
        "s1": 5,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "Dopi",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "ectoPower",
        "p2": "Huba Buba",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Memori",
        "p2": "TubusTD",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Kunio",
        "p2": "Transistor",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "mafuta",
        "p2": "Memori",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "Kunio",
        "p2": "ectoPower",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "mafuta",
        "p2": "Kunio",
        "s1": 5,
        "s2": 2,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 3": {
    "champion": "mafuta",
    "runner_up": "BOР95",
    "matches": [
      {
        "tour": "1/8 финала",
        "p1": "BOР95",
        "p2": "Flash",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Ric25",
        "p2": "Dopi",
        "s1": 3,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "mafuta",
        "p2": "Сenturion",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "ectoPower",
        "p2": "ArmFly",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "BOР95",
        "p2": "Ric25",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "ectoPower",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "BOР95",
        "p2": "Kunio",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "mafuta",
        "p2": "Memori",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "mafuta",
        "p2": "BOР95",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 4": {
    "champion": "mafuta",
    "runner_up": "Transistor",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "3aBuCTb",
        "p2": "FC Pushistik",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Romix",
        "p2": "Aeris",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "TubusTD",
        "p2": "Flash",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "high",
        "p2": "Kubik",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Kipriot",
        "p2": "3aBuCTb",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "izzzotope",
        "p2": "Romix",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Kunio",
        "p2": "high",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Ric25",
        "p2": "TubusTD",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "izzzotope",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Kipriot",
        "p2": "ectoPower",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Transistor",
        "p2": "Kunio",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Буц",
        "p2": "Ric25",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "mafuta",
        "p2": "Kipriot",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "Transistor",
        "p2": "Буц",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "mafuta",
        "p2": "Transistor",
        "s1": 5,
        "s2": 3,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 5": {
    "champion": "RVD (МГБ)",
    "runner_up": "PacnyTHuK",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "Romix",
        "p2": "Kubik",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "СentZloy",
        "p2": "Jamlight",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "RVD (МГБ)",
        "p2": "Chocopie",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "RVD (МГБ)",
        "p2": "Kunio",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "FC Pushistik",
        "p2": "СentZloy",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Romix",
        "p2": "Ric25",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "LiptOn",
        "p2": "Texas",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "RVD (МГБ)",
        "p2": "ectoPower",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "izzzotope",
        "p2": "Romix",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "LiptOn",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "PacnyTHuK",
        "p2": "FC Pushistik",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "RVD (МГБ)",
        "p2": "mafuta",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "PacnyTHuK",
        "p2": "izzzotope",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "RVD (МГБ)",
        "p2": "PacnyTHuK",
        "s1": 5,
        "s2": 2,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 6": {
    "champion": "ectoPower",
    "runner_up": "Transistor",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "Memori",
        "p2": "E_not",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Tymoschuk",
        "p2": "dynamik",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Rock",
        "p2": "yoxter",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Tymoschuk",
        "p2": "LiptOn",
        "s1": 3,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Memori",
        "p2": "FC Pushistik",
        "s1": 3,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Rock",
        "p2": "Ric25",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Transistor",
        "p2": "Huba Buba",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Memori",
        "p2": "Romix",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "ectoPower",
        "p2": "Rock",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Transistor",
        "p2": "Tymoschuk",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "Centurion",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "ectoPower",
        "p2": "Memori",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "Transistor",
        "p2": "mafuta",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "ectoPower",
        "p2": "Transistor",
        "s1": 5,
        "s2": 4,
        "league": "Кубок лиг"
      }
    ]
  },
  "Season 7": {
    "champion": "ectoPower",
    "runner_up": "RVD (МГБ)",
    "matches": [
      {
        "tour": "1/16 финала",
        "p1": "Yuliy_Cezar",
        "p2": "RASH",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "Aeris",
        "p2": "ruby",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/16 финала",
        "p1": "leonudomlya",
        "p2": "wanchous",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Bubnov",
        "p2": "leonudomlya",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Kunio",
        "p2": "Aeris",
        "s1": 3,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Cyneprepou4uk",
        "p2": "E_not",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/8 финала",
        "p1": "Memori",
        "p2": "Yuliy_Cezar",
        "s1": 3,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "RVD (МГБ)",
        "p2": "Bubnov",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "mafuta",
        "p2": "Kunio",
        "s1": 4,
        "s2": 2,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "Romix",
        "p2": "Memori",
        "s1": 4,
        "s2": 0,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/4 финала",
        "p1": "ectoPower",
        "p2": "Cyneprepou4uk",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "RVD (МГБ)",
        "p2": "Romix",
        "s1": 4,
        "s2": 1,
        "league": "Кубок лиг"
      },
      {
        "tour": "1/2 финала",
        "p1": "ectoPower",
        "p2": "mafuta",
        "s1": 4,
        "s2": 3,
        "league": "Кубок лиг"
      },
      {
        "tour": "Финал",
        "p1": "ectoPower",
        "p2": "RVD (МГБ)",
        "s1": 5,
        "s2": 3,
        "league": "Кубок лиг"
      }
    ]
  }
}

seasons_list = prepare_site_data.seasons_data

# Purge old miscategorized pseudo-cup matches from combined_matches for Seasons 2-7
cleaned_combined = []
for m in combined_matches:
    s_name = m.get("season")
    if s_name in HISTORIC_CUPS_DATA:
        m_tour = (m.get("tour") or "").lower()
        m_league = (m.get("league") or "").lower()
        if "плей-офф" in m_tour or "плей-офф" in m_league or "кубок" in m_tour or "кубок" in m_league:
            continue
    cleaned_combined.append(m)
combined_matches = cleaned_combined

# Add verified authentic Cup of Leagues matches with exact stages to combined_matches
for s_name, hcup in HISTORIC_CUPS_DATA.items():
    s_obj = next((x for x in seasons_list if x.get("name") == s_name), None)
    s_year = s_obj.get("year", "2018") if s_obj else "2018"
    for cm in hcup["matches"]:
        cm_item = {
            "season": s_name,
            "league": "Кубок лиг",
            "tour": cm["tour"],
            "p1": cm["p1"],
            "p2": cm["p2"],
            "s1": cm["s1"],
            "s2": cm["s2"],
            "vk_text": f"Кубок лиг • {cm['tour']} • {cm['p1']} vs {cm['p2']}",
            "vk_url": "",
            "vk_date": s_year,
            "vk_page": ""
        }
        combined_matches.append(cm_item)

# Assign finalized matches and podium metadata to all seasons
for s in seasons_list:
    s_name = s["name"]
    s["matches"] = [m for m in combined_matches if m.get("season") == s_name]
    s["total_goals"] = sum(m["s1"] + m["s2"] for m in s["matches"])
    if s_name in HISTORIC_CUPS_DATA:
        hcup = HISTORIC_CUPS_DATA[s_name]
        if "podium" not in s or not s["podium"]:
            s["podium"] = {}
        s["podium"]["cup_winner"] = hcup.get("champion")
        s["podium"]["cup_runner_up"] = hcup.get("runner_up")



active_count = sum(1 for p in profiles if p["is_active"])

inactive_count = sum(1 for p in profiles if not p["is_active"])

print(f"Profiles finalized: {len(profiles)} total (Active: {active_count}, Inactive/Legends: {inactive_count})")



SEASON_ROSTERS = {

    "1": {

        "Высшая (Единая) лига": [

            "mafuta", "Ric25", "WiSe", "Wenderfit", "high", "3aBuCTb", "Centurion", 

            "Flash", "Буц", "Kipriot", "Eg_or3", "Romario", "Rustin Cohle", "Gilmour", 

            "Memori", "E_not", "yoxter", "Буц"

        ]

    },

    "2": {

        "Высшая лига": [

            "mafuta", "Ric25", "Kunio", "ectoPower", "Memori", "Centurion", "Dr1N", 

            "BOР95", "Wenderfit", "yoxter", "Cyneprepou4uk", "Huba Buba", "artemis", 

            "Transistor", "RVD (МГБ)"

        ],

        "Младшая лига": [

            "Aeris", "Dopi", "Kubik", "Кирпич57", "E_not", "Kipriot", "Romario", 

            "Chocopie", "wanchous", "AJ_Maker", "Dan_Lavis", "Azatron", "Gilmour", 

            "Rustin Cohle", "Dynamik", "Damian", "Joe Duffy", "tubustd"

        ]

    },

    "3": {

        "Высшая лига": [

            "mafuta", "ectoPower", "Memori", "Kunio", "Huba Buba", "BOР95", "Ric25", 

            "Dr1N", "yoxter", "Centurion", "Kipriot"

        ],

        "Средняя лига": [

            "izzzotope", "Wenderfit", "tubustd", "Dopi", "Кирпич57", "Rustin Cohle", 

            "wanchous", "Kubik", "ArmFly", "Dune"

        ],

        "Дворовая лига": [

            "Aeris", "Chocopie", "AJ_Maker", "E_not", "starspro", "Texas", 

            "FC Pushistik", "Santa Claus", "Aoshi", "Flash"

        ]

    },

    "4": {

        "Высшая лига": [

            "mafuta", "ectoPower", "Ric25", "Kunio", "Memori", "Kipriot", "BOР95", 

            "izzzotope", "Dopi", "ArmFly", "Transistor", "Буц"

        ],

        "Средняя лига": [

            "Centurion", "yoxter", "tubustd", "Rustin Cohle", "Wenderfit", "Кирпич57", 

            "Texas", "FC Pushistik", "Romix", "high", "psycho"

        ],

        "Дворовая лига": [

            "wanchous", "Kubik", "Flash", "AJ_Maker", "Aeris", "Chocopie", "Aoshi", 

            "Gilmour", "Jamlight", "Stalin", "Zupka Knorra", "3aBuCTb", "Dune", "starspro"

        ]

    },

    "5": {

        "Высшая лига": [

            "mafuta", "ectoPower", "Буц", "Kipriot", "izzzotope", "Kunio", "Ric25", 

            "FC Pushistik", "PacnyTHuK", "Memori"

        ],

        "Средняя лига": [

            "Romix", "Texas", "Centurion", "psycho", "Rustin Cohle", "Flash", 

            "Aeris", "RVD (МГБ)", "Wenderfit"

        ],

        "Дворовая лига": [

            "yoxter", "Кирпич57", "Kubik", "wanchous", "Chocopie", "Aoshi", 

            "Stalin", "Jamlight", "kot-from-ussr", "shmel"

        ]

    },

    "6": {

        "Высшая лига": [

            "ectoPower", "izzzotope", "mafuta", "Ric25", "Kunio", "FC Pushistik", 

            "Буц", "Kipriot", "Centurion", "Romix", "Transistor", "Huba Buba"

        ],

        "Средняя лига": [

            "Texas", "Aeris", "Rustin Cohle", "Wenderfit", "Jamlight", "Кирпич57", 

            "Cyneprepou4uk", "Memori", "Dopi", "Bubnov", "Rock", "Greyson"

        ],

        "Дворовая лига": [

            "Aoshi", "yoxter", "Dynamik", "Dune", "E_not", "kot-from-ussr", 

            "AJ_Maker", "Mag.of.Shadow", "PacnyTHuK", "Legnahar", "Дядюшка АУ", 

            "Mcfly", "Que", "Веселый Роджер", "Chabby_59"

        ]

    },

    "7": {

        "Высшая лига": [

            "Memori", "mafuta", "Kunio", "Romix", "ectoPower", "Cyneprepou4uk", 

            "Bubnov", "RVD (МГБ)", "Ric25"

        ],

        "Средняя лига": [

            "Jamlight", "Dune", "Yuliy_Cezar", "Dynamik", "TEXAS", "gagagatch", 

            "yoxter", "Kubik", "leonudomlya", "E_not", "Aeris", "Centurion"

        ],

        "Дворовая лига": [

            "Веселый Роджер", "lenin1st", "Taeda", "Anubis", "ruby", "daz", 

            "wanchous", "Legnahar", "Romol", "RASH", "Vasya1995", "JohnnyBravo"

        ]

    },

    "8": {

        "Высшая лига": [

            "Cyneprepou4uk", "Kunio", "Memori", "PacnyTHuK", "RVD (МГБ)", 

            "Ric25", "Romix", "ectoPower", "leonudomlya"

        ],

        "Средняя лига": [

            "Aeris", "Dune", "E_not", "Jamlight", "Kubik", "RASH", 

            "Yuliy_Cezar", "Буц", "Кирпич57"

        ],

        "Дворовая лига": [

            "BigPlay", "Sokol", "TBP_Machiavelli", "Taeda", "ruby", 

            "daz", "frzz", "yoxter", "Сахарок"

        ]

    },

    "9": {

        "Высшая лига": [

            "Aeris", "Kunio", "Memori", "Ric25", "Rock", "Romix", 

            "ectoPower", "leonudomlya"

        ],

        "Средняя лига": [

            "Dune", "Jamlight", "Kubik", "Yuliy_Cezar", 

            "frzz", "yoxter", "Кирпич57"

        ],

        "Дворовая лига": [

            "Hanter", "Ryumaru", "Spartacus", "Taeda", "mikr84", 

            "ruby", "Веселый Роджер"

        ]

    }

}





# Tournaments already incorporated above - ENRICHED WITH SEASON, LEAGUE & SCORES

special_matches = []

for t in special_tournaments:

    t_title = t.get('title') or 'Спецтурнир'

    t_cat = t.get('category') or t.get('game') or 'Спецтурнир'

    for m in t.get('matches', []):

        m_copy = dict(m)

        if not m_copy.get('season'):

            m_copy['season'] = t_title

        if not m_copy.get('league'):

            m_copy['league'] = t_cat

        if not m_copy.get('stage') and m_copy.get('tour'):

            m_copy['stage'] = m_copy.get('tour')

        elif not m_copy.get('stage'):

            m_copy['stage'] = 'Матч'



        # Extract s1 and s2 if missing or None

        if 's1' not in m_copy or 's2' not in m_copy or m_copy.get('s1') is None:

            sc = str(m_copy.get('score', '')).strip()

            score_m = re.search(r'(\d+)\s*[:\-]\s*(\d+)', sc)

            if score_m:

                m_copy['s1'] = int(score_m.group(1))

                m_copy['s2'] = int(score_m.group(2))

            else:

                m_copy['s1'] = 0

                m_copy['s2'] = 0

        enrich_vk_source(m_copy)

        special_matches.append(m_copy)



# ==============================================================================

# COMPREHENSIVE LEAGUE ANALYTICS (MEDALS, RECORDS, STYLES, KRYPTONITES)

# ==============================================================================

medals_dict = defaultdict(lambda: {'gold': 0, 'silver': 0, 'bronze': 0, 'finals': 0, 'titles': []})



def norm_medalist_name(raw):

    if not raw: return ""

    raw = str(raw).strip()

    if '(' in raw and 'мгб' not in raw.lower():

        raw = re.sub(r'\s*\([^)]*\)', '', raw).strip()

    if raw.lower() in ['ectopower', 'экто']: return 'ectoPower'

    if raw.lower() in ['mafuta', 'мафута']: return 'mafuta'

    if raw.lower() in ['bop95', 'вор95']: return 'BOР95'

    if raw.lower() in ['huba_buba', 'huba buba', 'huba_buba_5']: return 'Huba Buba'

    if raw.lower() in ['rvd', 'рвд']: return 'RVD (МГБ)'

    if raw.lower() in ['davitel', 'давитель']: return 'Davitel'

    if raw.lower() in ['leon-udomlya', 'леон']: return 'leonudomlya'

    if raw.lower() in ['centurion', 'centzloy']: return 'Centurion'

    return raw



# 1. Official Regular Seasons Medals (Seasons 1–9 & Cups of Leagues)
# Strictly official championships and cups, excluding friendly penalty / blitz / unofficial cups

for s in seasons_list:
    s_title = s.get('title') or s.get('name')
    # League Championship
    c_raw = s.get('champion')
    if c_raw:
        for c in str(c_raw).split('/'):
            c = norm_medalist_name(c)
            if c:
                medals_dict[c]['gold'] += 1
                medals_dict[c]['finals'] += 1
                medals_dict[c]['titles'].append(f"🥇 Чемпион {s_title}")
    ru = norm_medalist_name(s.get('runner_up'))
    if ru:
        medals_dict[ru]['silver'] += 1
        medals_dict[ru]['finals'] += 1
    th = norm_medalist_name(s.get('third_place'))
    if th:
        medals_dict[th]['bronze'] += 1
    # Cup of Leagues (Official Major)
    cup = norm_medalist_name(s.get('cup_winner'))
    if cup:
        medals_dict[cup]['gold'] += 1
        medals_dict[cup]['titles'].append(f"🏆 Кубок Лиги {s_title}")



# Enrich every profile with medals, spectacle, kryptonite and client

for p in profiles:

    pl = p['player']

    p['medals'] = medals_dict.get(pl, {'gold': 0, 'silver': 0, 'bronze': 0, 'finals': 0, 'titles': []})

    hist = p.get('match_history', [])
    # Calculate spectacle strictly from official season matches (excluding penalty/blitz inflation)
    s_hist = [m for m in hist if m.get('category') == 'season' and not m.get('is_technical')]
    calc_hist = s_hist if len(s_hist) > 0 else [m for m in hist if not m.get('is_technical')]

    if len(calc_hist) > 0:
        p['spectacle'] = round(sum(m.get('score_for', 0) + m.get('score_against', 0) for m in calc_hist) / len(calc_hist), 2)
    else:
        p['spectacle'] = 0.0



    opp_stats = defaultdict(lambda: {'w': 0, 'l': 0, 'd': 0, 'tot': 0})

    for m in hist:

        opp = m.get('opponent')

        if not opp: continue

        res = m.get('result')

        opp_stats[opp]['tot'] += 1

        if res == 'ПОБЕДА': opp_stats[opp]['w'] += 1

        elif res == 'ПОРАЖЕНИЕ': opp_stats[opp]['l'] += 1

        else: opp_stats[opp]['d'] += 1



    opps_min = [item for item in opp_stats.items() if item[1]['tot'] >= 3]

    if opps_min:

        krypt = min(opps_min, key=lambda x: (x[1]['w'] / x[1]['tot'], -x[1]['tot']))

        client = max(opps_min, key=lambda x: (x[1]['w'] / x[1]['tot'], x[1]['tot']))

        p['kryptonite'] = {

            'name': krypt[0], 'w': krypt[1]['w'], 'l': krypt[1]['l'],

            'tot': krypt[1]['tot'], 'wr': round(krypt[1]['w'] / krypt[1]['tot'] * 100, 1)

        }

        p['favorite_client'] = {

            'name': client[0], 'w': client[1]['w'], 'l': client[1]['l'],

            'tot': client[1]['tot'], 'wr': round(client[1]['w'] / client[1]['tot'] * 100, 1)

        }

    else:

        p['kryptonite'] = None

        p['favorite_client'] = None



# Pre-compute Leaderboards for the Hall of Fame & Records Dashboard (Official Seasons Only!)

medal_leaders = sorted(
    [p for p in profiles if (p['medals']['gold'] + p['medals']['silver'] + p['medals']['bronze']) > 0],
    key=lambda x: (x['medals']['gold'], x['medals']['silver'], x['medals']['bronze'], x['medals']['finals']),
    reverse=True
)

# Clean sheets in official regular seasons (excluding penalty shootout shutouts)
clean_sheet_season_data = []
for p in profiles:
    s_m = [m for m in p.get('match_history', []) if m.get('category') == 'season' and not m.get('is_technical')]
    cs = sum(1 for m in s_m if m.get('score_against') == 0 and m.get('result') in ['ПОБЕДА', 'ТП (ПОБЕДА)'])
    if cs > 0:
        clean_sheet_season_data.append({
            'player': p['player'],
            'clean_sheets': cs,
            'matches': len(s_m),
            'avatar': p['avatar']
        })
clean_sheet_leaders = sorted(clean_sheet_season_data, key=lambda x: x['clean_sheets'], reverse=True)[:8]

# Clutch in official regular seasons (OT/PK in official championship games, min 3)
clutch_season_data = []
for p in profiles:
    s_m = [m for m in p.get('match_history', []) if m.get('category') == 'season']
    ot_m = [m for m in s_m if m.get('ot') or m.get('pk')]
    ot_w = sum(1 for m in ot_m if m.get('result') == 'ПОБЕДА')
    ot_l = sum(1 for m in ot_m if m.get('result') == 'ПОРАЖЕНИЕ')
    tot = ot_w + ot_l
    if tot >= 3:
        wr = round(ot_w / tot * 100, 1)
        clutch_season_data.append({
            'player': p['player'],
            'ot_win_rate': wr,
            'ot_wins': ot_w,
            'ot_losses': ot_l,
            'avatar': p['avatar']
        })
clutch_leaders = sorted(clutch_season_data, key=lambda x: (x['ot_win_rate'], x['ot_wins']), reverse=True)[:8]

# Attacking and defensive styles strictly from official seasons (min 15 matches)
spec_season_data = []
for p in profiles:
    s_m = [m for m in p.get('match_history', []) if m.get('category') == 'season' and not m.get('is_technical')]
    if len(s_m) >= 15:
        tot_goals = sum(m.get('score_for', 0) + m.get('score_against', 0) for m in s_m)
        spec = round(tot_goals / len(s_m), 2)
        spec_season_data.append({
            'player': p['player'],
            'spectacle': spec,
            'matches': len(s_m),
            'avatar': p['avatar']
        })

spec_attacking = sorted(spec_season_data, key=lambda x: x['spectacle'], reverse=True)[:6]
spec_defensive = sorted(spec_season_data, key=lambda x: x['spectacle'])[:6]

# Top All-Time Scorers in official regular seasons (excluding penalty shootout exhibitions)
top_scorers_season_data = []
for p in profiles:
    s_m = [m for m in p.get('match_history', []) if m.get('category') == 'season' and not m.get('is_technical')]
    if s_m:
        gf = sum(m.get('score_for', 0) for m in s_m)
        top_scorers_season_data.append({
            'player': p['player'],
            'goals_for': gf,
            'matches': len(s_m),
            'gpg': round(gf / len(s_m), 2),
            'avatar': p['avatar']
        })
top_scorers_leaders = sorted(top_scorers_season_data, key=lambda x: x['goals_for'], reverse=True)[:8]



quotes_authors_top = [

    {"author": "mafuta", "count": 49, "sample": "Без цитат мы всего лишь безликое скопище ретрогномов, заблудившихся в ретрогейском лесу"},

    {"author": "RVD (МГБ)", "count": 46, "sample": "Нам нужно больше организаторов про запас, чтобы когда у одного крыша съезжает, второй заменял"},

    {"author": "Memori", "count": 32, "sample": "Есть два эмуля, на одном лаги точеные, на другом задержки дроченые. За какой сам сядешь, за какой Хубу посадишь?"},

    {"author": "ectoPower", "count": 22, "sample": "Две кнопки вверх, две кнопки вниз, прыжок с локтя, удар в карниз"},

    {"author": "Davitel", "count": 10, "sample": "В смысле я лох, блять, я джентльмен!"},

    {"author": "daz", "count": 9, "sample": "Вы либо админку снимите, либо трусы наденьте"},

    {"author": "Rock", "count": 7, "sample": "О, боже, оно не лагает! Как в это можно играть?"},

    {"author": "Jamlight", "count": 7, "sample": "Если игрок не двигает сетку тогда сетка двигает игрока"}

]



# Veterans: Season 1 through Season 9

veterans_longevity = [

    {"player": "Kunio", "span": "2015 → 2026 (11 лет)", "matches": 190, "desc": "Бессменный титан Высшей лиги со дня основания сообщества."},

    {"player": "Memori", "span": "2015 → 2026 (11 лет)", "matches": 175, "desc": "Архивариус и оплот лиги, участник всех официальных турниров."},

    {"player": "ectoPower", "span": "2015 → 2026 (11 лет)", "matches": 210, "desc": "Главный рекордсмен лиги по матчам, победам и трофеям."},

    {"player": "Ric25", "span": "2015 → 2026 (11 лет)", "matches": 163, "desc": "Ветеран 1-го сезона, прошедший через все дивизионы."},

    {"player": "PacnyTHuK", "span": "2015 → 2026 (11 лет)", "matches": 89, "desc": "Один из лучших командных бойцов и кубковых триумфаторов."},

    {"player": "WiSe", "span": "2015 → 2016 (1 сезон)", "matches": 18, "desc": "Бронзовый призёр исторического 1-го сезона NST."},

    {"player": "Буц", "span": "2015 → 2026 (11 лет)", "matches": 115, "desc": "Первопроходец Сезона 1 (LiptOn) и бессменный ветеран всех 9 сезонов лиги."}

]



site_payload = {

    "metadata": {

        "total_matches_analyzed": len(combined_matches),

        "total_goals_recorded": sum(m["s1"] + m["s2"] for m in combined_matches),

        "total_ot_pk_matches": sum(1 for m in combined_matches if m.get("ot") or m.get("pk")),

        "avg_goals_per_match": round(sum(m["s1"] + m["s2"] for m in combined_matches) / len(combined_matches), 2),

        "total_players_tracked": len(profiles),

        "active_players_count": active_count,

        "inactive_players_count": inactive_count,

    },

    "profiles": profiles,

    "seasons": seasons_list,

    "season_rosters": SEASON_ROSTERS,

    "divisions": master_db["divisions"],

    "clutch_index": master_db["clutch_and_overtime_index"],

    "records": master_db["all_time_records"],

    "rivalries": master_db["kryptonite_rivalries"],

    "special_tournaments": special_tournaments,

    "team_tournaments": team_tournaments,

    "special_matches": special_matches,

    "medal_leaders": medal_leaders,

    "clean_sheet_leaders": clean_sheet_leaders,

    "clutch_leaders": clutch_leaders,

    "spec_attacking": spec_attacking,

    "spec_defensive": spec_defensive,

    "top_scorers_leaders": top_scorers_leaders,

    "veterans_longevity": veterans_longevity

}



json_str = json.dumps(site_payload, ensure_ascii=False)



html_code = """<!DOCTYPE html>

<html lang="ru">

<head>

  <meta charset="UTF-8">

  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <title>NEKKETSU SOCCER LEAGUE &bull; Чемпионат по Goal 3 (NES / Famicom)</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">

  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

  <link href="https://fonts.googleapis.com/css2?family=Rubik:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400&family=JetBrains+Mono:wght@600;700;800&family=Russo+One&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="audio-player.css">

  <style>

    :root {

      --nes-bg: #091728;

      --nes-bg-dark: #050d18;

      --nes-card-bg: #0d1e32;

      --nes-panel-border: 1px solid #234568;

      --nes-gold: #ffcb05;

      --nes-cyan: #38bdf8;

      --nes-green: #22c55e;

      --nes-red: #f43f5e;

      --nes-purple: #c084fc;

      --font-title: 'Russo One', sans-serif;

      --font-body: 'Rubik', sans-serif;

      --font-mono: 'JetBrains Mono', monospace;

    }



    * { 

      box-sizing: border-box; 

      margin: 0; 

      padding: 0; 

      text-shadow: none !important; /* Eliminate all blurry glowing text halos */

    }



    /* Custom Slim Clean Scrollbars */

    ::-webkit-scrollbar { width: 8px; height: 8px; }

    ::-webkit-scrollbar-track { background: #050d18; }

    ::-webkit-scrollbar-thumb { 

      background: #234568; 

      border-radius: 4px; 

      border: 1px solid rgba(255,255,255,0.12); 

    }

    ::-webkit-scrollbar-thumb:hover { background: #38bdf8; }



    body {

      background-color: var(--nes-bg);

      color: #f8fafc;

      font-family: var(--font-body);

      font-size: 15px;

      line-height: 1.55;

      background-image: 

        radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.12) 0%, transparent 60%),

        linear-gradient(rgba(0,0,0,0.15) 1px, transparent 1px),

        linear-gradient(90deg, rgba(0,0,0,0.15) 1px, transparent 1px);

      background-size: 100% 100%, 36px 36px, 36px 36px;

      min-height: 100vh;

      display: flex;

      flex-direction: column;

      -webkit-font-smoothing: antialiased;

      -moz-osx-font-smoothing: grayscale;

    }



    /* Top Sticky Header */

    header {

      background: #06111e;

      border-bottom: 2px solid #1e3a58;

      box-shadow: 0 4px 20px rgba(0,0,0,0.6);

      position: sticky;

      top: 0;

      z-index: 100;

    }



    .header-inner {

      max-width: 1820px;

      margin: 0 auto;

      padding: 12px 24px;

      display: flex;

      justify-content: space-between;

      align-items: center;

      flex-wrap: wrap;

      gap: 16px;

    }



    .logo-block {

      display: flex;

      align-items: center;

      gap: 14px;

      text-decoration: none;

      color: #ffffff;

    }



    .logo-badge {

      background: #ffcb05;

      color: #000000;

      font-family: var(--font-title);

      font-size: 20px;

      padding: 6px 14px;

      border-radius: 6px;

      text-transform: uppercase;

      letter-spacing: 1px;

      font-weight: 900;

    }



    .logo-text h1 {

      font-family: var(--font-title);

      font-size: 22px;

      letter-spacing: 0.5px;

      text-transform: uppercase;

      color: #ffffff;

      line-height: 1.2;

    }



    .logo-text p {

      font-size: 12px;

      color: #38bdf8;

      font-weight: 600;

      letter-spacing: 0.5px;

      margin-top: 2px;

    }



    /* Header Meta Stats */

    .header-meta-stats {

      display: flex;

      align-items: center;

      gap: 10px;

      flex-wrap: wrap;

    }

    .meta-stat-pill {

      font-size: 13px;

      color: #cbd5e1;

      background: #0e2238;

      border: 1px solid #234568;

      border-radius: 6px;

      padding: 5px 12px;

      font-weight: 500;

    }

    .meta-stat-pill strong { color: #ffffff; font-weight: 700; }

    .meta-vk-btn {

      font-size: 13px;

      font-weight: 700;

      color: #38bdf8;

      background: rgba(56, 189, 248, 0.12);

      border: 1px solid #38bdf8;

      border-radius: 6px;

      padding: 5px 14px;

      text-decoration: none;

      transition: all 0.15s ease;

    }

    .meta-vk-btn:hover {

      background: #38bdf8;

      color: #000000;

    }

    /* Premium NES-Branded VK Button */
    .vk-btn {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      background: linear-gradient(135deg, #0077ff 0%, #0055cc 100%);
      color: #ffffff !important;
      font-family: var(--font-body);
      font-size: 12px;
      font-weight: 700;
      padding: 6px 14px;
      border-radius: 6px;
      text-decoration: none !important;
      border: 1px solid #38bdf8;
      box-shadow: 0 2px 8px rgba(0, 119, 255, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2);
      transition: all 0.15s ease;
      letter-spacing: 0.3px;
      cursor: pointer;
    }
    .vk-btn:hover {
      background: linear-gradient(135deg, #268aff 0%, #0066ee 100%);
      color: #ffffff !important;
      border-color: #ffffff;
      box-shadow: 0 4px 14px rgba(0, 119, 255, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.4);
      transform: translateY(-1px);
    }
    .vk-btn:active {
      transform: translateY(0);
      box-shadow: 0 1px 4px rgba(0, 119, 255, 0.3);
    }
    .vk-btn svg {
      width: 14px;
      height: 14px;
      flex-shrink: 0;
      fill: currentColor;
    }

    /* Small VK Pill for Player Grid Card */
    .card-vk-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: rgba(0, 119, 255, 0.16);
      color: #38bdf8 !important;
      border: 1px solid rgba(56, 189, 248, 0.45);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      text-decoration: none !important;
      transition: all 0.15s ease;
      cursor: pointer;
    }
    .card-vk-pill:hover {
      background: #0077ff;
      color: #ffffff !important;
      border-color: #0077ff;
      box-shadow: 0 2px 8px rgba(0, 119, 255, 0.5);
    }
    .card-vk-pill svg {
      width: 11px;
      height: 11px;
      flex-shrink: 0;
      fill: currentColor;
    }



    /* Navigation Bar */

    .nav-bar-container {

      background: #081729;

      border-top: 1px solid #1a334e;

      padding: 8px 24px;

    }

    .nav-bar {

      max-width: 1820px;

      margin: 0 auto;

      display: flex;

      gap: 8px;

      align-items: center;

      flex-wrap: nowrap;

      overflow-x: auto;

      scrollbar-width: none;

    }

    .nav-bar::-webkit-scrollbar { display: none; }



    .nav-btn {

      background: #0f243a;

      color: #cbd5e1;

      border: 1px solid #234568;

      border-radius: 6px;

      padding: 8px 16px;

      font-family: var(--font-body);

      font-size: 14px;

      font-weight: 600;

      cursor: pointer;

      transition: all 0.15s ease;

      display: inline-flex;

      align-items: center;

      gap: 6px;

      white-space: nowrap;

    }



    .nav-btn:hover {

      background: #18385a;

      border-color: #38bdf8;

      color: #ffffff;

    }



    .nav-btn.active {

      background: #ffcb05;

      border-color: #ffcb05;

      color: #000000;

      font-weight: 800;

    }



    /* Container */

    .container {

      max-width: 1820px;

      width: calc(100% - 48px);

      margin: 0 auto;

      padding: 18px 0 60px 0;

      flex: 1;

    }



    



    /* HUD Overview Cards */

    .hud-metrics {

      display: grid;

      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));

      gap: 16px;

      margin-bottom: 24px;

    }



    .hud-card {

      background: #0c1e32;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      padding: 16px 20px;

      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);

      position: relative;

    }



    .hud-card:nth-child(1) { border-top: 4px solid #38bdf8; }

    .hud-card:nth-child(2) { border-top: 4px solid #ffcb05; }

    .hud-card:nth-child(3) { border-top: 4px solid #22c55e; }

    .hud-card:nth-child(4) { border-top: 4px solid #c084fc; }



    .hud-label {

      font-family: var(--font-body);

      font-size: 13px;

      font-weight: 700;

      color: #cbd5e1;

      text-transform: uppercase;

      letter-spacing: 0.5px;

    }



    .hud-val {

      font-family: var(--font-mono);

      font-size: 32px;

      font-weight: 800;

      color: #ffffff;

      margin: 4px 0 2px 0;

      letter-spacing: -0.5px;

    }



    .hud-sub {

      font-size: 13px;

      color: #cbd5e1;

      font-weight: 500;

    }



    /* Views */

    .view-content { display: none; }

    .view-content.active { display: block; animation: fadeIn 0.15s ease-in; }



    @keyframes fadeIn {

      from { opacity: 0; }

      to { opacity: 1; }

    }



    /* Controls & Search */

    .controls-row {

      display: flex;

      justify-content: space-between;

      align-items: center;

      flex-wrap: wrap;

      gap: 14px;

      margin-bottom: 18px;

    }



    .filter-tabs {

      display: flex;

      gap: 8px;

      flex-wrap: wrap;

      align-items: center;

    }



    /* High-Legibility Solid Filter Buttons - NO GLOW, LARGER FONT */

    .filter-btn {

      background: #0f243a;

      color: #f1f5f9;

      border: 1px solid #2a4e75;

      border-radius: 6px;

      font-family: var(--font-body);

      font-size: 14px;

      font-weight: 600;

      padding: 8px 16px;

      cursor: pointer;

      transition: all 0.12s ease;

      white-space: nowrap;

      box-shadow: none !important;

    }



    .filter-btn:hover {

      background: #1c3c5e;

      border-color: #38bdf8;

      color: #ffffff;

    }



    .filter-btn.active {

      background: #ffcb05;

      border-color: #ffcb05;

      color: #000000;

      font-weight: 800;

      box-shadow: none !important;

    }



    .filter-btn.inactive-tab {

      background: #1e131d;

      border-color: #881337;

      color: #fecdd3;

    }

    .filter-btn.inactive-tab:hover {

      background: #be123c;

      border-color: #be123c;

      color: #ffffff;

    }

    .filter-btn.inactive-tab.active {

      background: #e11d48;

      border-color: #e11d48;

      color: #ffffff;

      font-weight: 800;

    }



    .clean-search {

      background: #0a1b2d;

      border: 1px solid #2a4e75;

      border-radius: 6px;

      color: #ffffff;

      font-family: var(--font-body);

      font-size: 14px;

      padding: 8px 16px;

      width: 290px;

      outline: none;

      transition: all 0.15s ease;

    }

    .clean-search::placeholder { color: #94a3b8; }

    .clean-search:focus { 

      border-color: #38bdf8; 

      width: 320px;

      background: #0e243c;

    }



    /* Tables */

    .table-box {

      background: #0a1b2d;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      box-shadow: 0 8px 24px rgba(0,0,0,0.5);

      overflow-x: auto;

      margin-bottom: 25px;

    }



    table {

      width: 100%;

      border-collapse: collapse;

      text-align: left;

    }



    th {

      background: #06111e;

      color: #cbd5e1;

      font-family: var(--font-body);

      font-size: 13px;

      font-weight: 700;

      padding: 12px 12px;

      border-bottom: 2px solid #1e3a58;

      border-right: 1px solid #132437;

      cursor: pointer;

      user-select: none;

      letter-spacing: 0.3px;

      white-space: nowrap;

      position: sticky;

      top: 0;

      z-index: 10;

    }

    th:hover { color: #38bdf8; background: #0c1e32; }



    td {

      padding: 10px 12px;

      border-bottom: 1px solid #132437;

      border-right: 1px solid #0e1c2b;

      font-size: 14px;

      font-weight: 500;

      color: #e2e8f0;

    }



    tbody tr {

      background: #0a1b2d;

      transition: background 0.12s ease;

    }

    tbody tr:nth-child(even) {

      background: #0d2137;

    }

    tbody tr:hover {

      background: #153252 !important;

      cursor: pointer;

    }



    .p-cell {

      display: flex;

      align-items: center;

      gap: 12px;

      cursor: pointer;

    }



    .avatar-clean {

      width: 40px;

      height: 40px;

      border-radius: 4px;

      border: 1px solid rgba(255, 255, 255, 0.25);

      background: #000;

      object-fit: cover;

      flex-shrink: 0;

    }



    .p-name {

      font-family: var(--font-body);

      font-size: 15px;

      font-weight: 700;

      color: #ffffff;

      line-height: 1.25;

    }

    .p-cell:hover .p-name {

      color: #38bdf8;

    }



    .p-sub {

      font-size: 13px;

      color: #cbd5e1;

      margin-top: 2px;

      max-width: 280px;

      overflow: hidden;

      text-overflow: ellipsis;

      white-space: nowrap;

      font-weight: 500;

    }



    .league-badge {

      display: inline-block;

      font-family: var(--font-body);

      font-size: 11px;

      padding: 3px 8px;

      border-radius: 4px;

      letter-spacing: 0.3px;

      text-transform: uppercase;

      white-space: nowrap;

      font-weight: 800;

    }



    .badge-premier { background: #b45309; color: #fef08a; }

    .badge-middle { background: #1d4ed8; color: #bfdbfe; }

    .badge-yard { background: #374151; color: #f3f4f6; }

    .badge-inactive { background: #581c87; color: #f3e8ff; }

    .badge-cup { background: #831843; color: #fce7f3; border: 1px solid #db2777; }

    /* Tournament Playoff Bracket Styling */
    .bracket-wrapper {
      background: rgba(10, 15, 29, 0.75);
      border: 2px solid rgba(255, 255, 255, 0.15);
      padding: 20px 16px;
      margin-top: 14px;
      overflow-x: auto;
      box-shadow: 4px 4px 0 #000;
      scrollbar-width: thin;
      scrollbar-color: var(--nes-cyan) #0f172a;
    }
    .bracket-wrapper {
      position: relative;
    }
    .bracket-svg {
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: none;
      z-index: 1;
      overflow: visible;
    }
    .bracket-container {
      display: flex;
      gap: 52px;
      min-width: max-content;
      align-items: stretch;
      padding: 10px 4px;
      position: relative;
      z-index: 2;
    }
    .bracket-round {
      display: flex;
      flex-direction: column;
      width: 270px;
      flex-shrink: 0;
    }
    .bracket-round-header {
      background: #0f172a;
      border: 2px solid var(--nes-cyan);
      color: var(--nes-cyan);
      font-family: var(--font-title);
      font-size: 13px;
      text-align: center;
      padding: 8px 12px;
      margin-bottom: 24px;
      letter-spacing: 1px;
      text-transform: uppercase;
      box-shadow: 2px 2px 0 #000;
    }
    .bracket-matchups {
      display: flex;
      flex-direction: column;
      justify-content: space-around;
      flex: 1;
      gap: 24px;
    }
    .bracket-match-card {
      background: #111827;
      border: 2px solid #374151;
      box-shadow: 3px 3px 0 #000;
      transition: transform 0.15s ease, border-color 0.15s ease;
      position: relative;
    }
    .bracket-match-card:hover {
      border-color: var(--nes-gold);
    }
    .bracket-match-card.is-final {
      border-color: var(--nes-gold);
      box-shadow: 0 0 14px rgba(255, 183, 3, 0.28), 3px 3px 0 #000;
    }
    .bracket-card-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 4px 10px;
      background: #0b1120;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 10px;
      font-family: var(--font-mono);
      color: #94a3b8;
      font-weight: 700;
    }
    .bracket-player-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 9px 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      cursor: pointer;
      transition: background 0.1s ease;
    }
    .bracket-player-row:last-child {
      border-bottom: none;
    }
    .bracket-player-row:hover {
      background: rgba(255, 255, 255, 0.05);
    }
    .bracket-player-row.winner {
      background: rgba(255, 183, 3, 0.12);
      color: var(--nes-gold);
      font-weight: 800;
    }
    .bracket-player-row.loser {
      opacity: 0.65;
    }
    .bracket-p-info {
      display: flex;
      align-items: center;
      gap: 8px;
      flex: 1;
      overflow: hidden;
    }
    .bracket-p-avatar {
      width: 22px;
      height: 22px;
      border: 1px solid #fff;
      border-radius: 2px;
      flex-shrink: 0;
    }
    .bracket-p-name {
      font-family: var(--font-title);
      font-size: 13px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .bracket-score {
      font-family: var(--font-mono);
      font-weight: 900;
      font-size: 14px;
      min-width: 26px;
      text-align: center;
      padding: 3px 6px;
      border-radius: 2px;
      background: #1f2937;
      color: #fff;
      margin-left: 8px;
    }
    .bracket-player-row.winner .bracket-score {
      background: var(--nes-gold);
      color: #000;
    }
    .bracket-series-games {
      background: #0a0f1d;
      padding: 6px 10px;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      border-top: 1px dashed rgba(255, 255, 255, 0.12);
    }
    .bracket-chip {
      font-family: var(--font-mono);
      font-size: 10px;
      padding: 2px 5px;
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 2px;
      cursor: pointer;
      transition: all 0.12s ease;
    }
    .bracket-chip:hover {
      background: var(--nes-cyan);
      color: #000;
      border-color: #fff;
    }
    .bracket-champion-round {
      display: flex;
      flex-direction: column;
      width: 240px;
      flex-shrink: 0;
      margin: auto 0;
    }
    .bracket-champion-box {
      background: linear-gradient(180deg, rgba(255, 183, 3, 0.22) 0%, rgba(15, 23, 42, 0.95) 100%);
      border: 2px solid var(--nes-gold);
      box-shadow: 0 0 20px rgba(255, 183, 3, 0.3), 4px 4px 0 #000;
      padding: 24px 16px;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }
    .bracket-champ-avatar {
      width: 52px;
      height: 52px;
      border: 2px solid var(--nes-gold);
      border-radius: 4px;
      box-shadow: 0 0 10px var(--nes-gold);
    }
    .bracket-champ-name {
      font-family: var(--font-title);
      font-size: 16px;
      color: var(--nes-gold);
      font-weight: 900;
      cursor: pointer;
      margin-top: 4px;
    }
    .bracket-champ-sub {
      font-size: 11px;
      color: #94a3b8;
      font-weight: 700;
      letter-spacing: 0.5px;
    }

    /* Bracket Interactive Focus State - ZERO JITTER */
    .bracket-match-card {
      transition: opacity 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease, background 0.15s ease;
    }
    .bracket-wrapper.has-focus .bracket-match-card:not(.card-focused) {
      opacity: 0.22;
      filter: grayscale(0.85);
    }
    .bracket-match-card.card-focused {
      opacity: 1 !important;
      border-color: var(--nes-gold) !important;
      box-shadow: 0 0 16px rgba(255, 183, 3, 0.65), 3px 3px 0 #000 !important;
      background: #1e293b !important;
      z-index: 10;
    }
    .bracket-wrapper.has-focus .bracket-champion-box:not(.champ-focused) {
      opacity: 0.22;
      filter: grayscale(0.85);
    }
    .bracket-champion-box.champ-focused {
      opacity: 1 !important;
      border-color: var(--nes-gold) !important;
      box-shadow: 0 0 25px rgba(255, 183, 3, 0.8), 4px 4px 0 #000 !important;
      background: #1e293b !important;
      z-index: 10;
    }
    .bracket-path-banner {
      min-height: 40px;
      background: rgba(17, 24, 39, 0.75);
      border: 1px solid rgba(255, 183, 3, 0.25);
      padding: 8px 14px;
      margin-bottom: 12px;
      font-family: var(--font-title);
      font-size: 12px;
      color: #94a3b8;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-sizing: border-box;
      transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease, color 0.15s ease;
    }
    .bracket-path-banner.active {
      background: rgba(255, 183, 3, 0.14);
      border-color: var(--nes-gold);
      color: #fff;
      box-shadow: 0 0 14px rgba(255, 183, 3, 0.25);
    }
    .bracket-path-banner .banner-reset-btn {
      cursor: pointer;
      color: var(--nes-gold);
      font-weight: 700;
      border: 1px solid rgba(255, 183, 3, 0.4);
      background: rgba(0, 0, 0, 0.4);
      padding: 3px 8px;
      text-transform: uppercase;
      font-size: 10px;
      letter-spacing: 0.5px;
      transition: all 0.15s ease;
    }
    .bracket-path-banner .banner-reset-btn:hover {
      background: var(--nes-gold);
      color: #000;
      border-color: var(--nes-gold);
    }
    .bracket-connector-path {
      transition: opacity 0.2s ease, stroke-width 0.2s ease, stroke 0.2s ease;
      opacity: 0.16;
      stroke: #475569;
      stroke-width: 1.5px;
    }
    .bracket-wrapper.has-focus .bracket-connector-path:not(.path-focused) {
      opacity: 0.03;
    }
    .bracket-connector-path.path-focused {
      opacity: 1 !important;
      stroke: #fbbf24 !important;
      stroke-width: 3.5px !important;
      filter: url(#bracketGlowGold) !important;
      z-index: 20;
    }
    .bracket-player-pill {
      font-size: 11px;
      padding: 3px 8px;
      background: #1e293b;
      color: #94a3b8;
      border: 1px solid #334155;
      cursor: pointer;
      font-family: var(--font-mono);
      transition: all 0.12s ease;
      border-radius: 2px;
    }
    .bracket-player-pill:hover, .bracket-player-pill.active {
      background: var(--nes-gold);
      color: #000;
      border-color: #fff;
      font-weight: 800;
    }



    .action-btn {

      background: #14324f;

      color: #e2e8f0;

      border: 1px solid #2b5680;

      border-radius: 4px;

      padding: 5px 12px;

      font-family: var(--font-body);

      font-size: 12px;

      font-weight: 700;

      cursor: pointer;

      transition: all 0.12s ease;

      white-space: nowrap;

    }

    .action-btn:hover {

      background: #38bdf8;

      color: #000000;

      border-color: #38bdf8;

    }



    /* Result Badges */

    .res-badge {

      display: inline-block;

      font-family: var(--font-body);

      font-size: 12px;

      padding: 3px 8px;

      border-radius: 4px;

      text-transform: uppercase;

      min-width: 90px;

      text-align: center;

      font-weight: 800;

    }

    .res-win { background: #15803d; color: #ffffff; }

    .res-loss { background: #be123c; color: #ffffff; }

    .res-draw { background: #b45309; color: #ffffff; }



    .ot-tag {

      font-size: 11px;

      font-weight: 800;

      padding: 2px 6px;

      border-radius: 3px;

      margin-left: 6px;

      text-transform: uppercase;

    }

    .ot-gold { background: #854d0e; color: #fef08a; }

    .ot-purple { background: #6b21a8; color: #f3e8ff; }



    /* Player Cards */

    .cards-grid {

      display: grid;

      grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));

      gap: 18px;

      margin-bottom: 30px;

    }



    .clean-card {

      background: #0c1e32;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      padding: 16px;

      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);

      display: flex;

      flex-direction: column;

      gap: 12px;

      cursor: pointer;

      transition: all 0.15s ease;

    }



    .clean-card:hover {

      border-color: #38bdf8;

      background: #10263f;

    }



    .card-top {

      display: flex;

      align-items: center;

      gap: 14px;

    }



    .card-top h3 {

      font-family: var(--font-body);

      font-size: 17px;

      font-weight: 700;

      color: #ffffff;

    }



    .card-stat-strip {

      background: #081729;

      border: 1px solid #1a334e;

      border-radius: 6px;

      padding: 8px 10px;

      display: grid;

      grid-template-columns: repeat(3, 1fr);

      text-align: center;

      gap: 6px;

    }



    .card-stat-strip .lbl {

      font-size: 12px;

      font-family: var(--font-body);

      font-weight: 600;

      color: #cbd5e1;

    }



    .card-stat-strip .v {

      font-family: var(--font-mono);

      font-size: 16px;

      font-weight: 800;

      color: #ffffff;

    }



    /* Modal */

    .modal-overlay {

      display: none;

      position: fixed;

      top: 0; left: 0; width: 100%; height: 100%;

      background: rgba(3, 8, 16, 0.88);

      backdrop-filter: blur(8px);

      z-index: 1000;

      padding: 20px;

      overflow-y: auto;

    }



    .modal-overlay.active {

      display: flex;

      justify-content: center;

      align-items: flex-start;

    }



    .modal-box {

      background: #0b1a2d;

      border: 2px solid #234568;

      border-radius: 10px;

      box-shadow: 0 20px 60px rgba(0,0,0,0.85);

      width: 100%;

      max-width: 940px;

      margin: 30px auto;

      padding: 24px;

      position: relative;

    }



    .modal-close {

      position: absolute;

      top: 14px;

      right: 14px;

      background: #be123c;

      color: #ffffff;

      border: 1px solid #f43f5e;

      border-radius: 6px;

      font-family: var(--font-body);

      font-size: 18px;

      font-weight: 800;

      width: 34px;

      height: 34px;

      cursor: pointer;

      display: flex;

      align-items: center;

      justify-content: center;

      transition: all 0.15s ease;

    }

    .modal-close:hover { 

      background: #e11d48; 

    }



    .modal-header {

      display: flex;

      gap: 20px;

      align-items: center;

      border-bottom: 1px solid #1e3a58;

      padding-bottom: 16px;

      margin-bottom: 20px;

      flex-wrap: wrap;

    }



    .modal-avatar-big {

      width: 80px;

      height: 80px;

      border-radius: 6px;

      border: 2px solid #38bdf8;

      background: #000;

      object-fit: cover;

    }



    .modal-title-box h2 {

      font-family: var(--font-title);

      font-size: 26px;

      color: #ffffff;

      letter-spacing: 0.8px;

    }



    .metric-tiles {

      display: grid;

      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));

      gap: 12px;

      margin-bottom: 20px;

    }



    .metric-tile {

      background: #081729;

      border: 1px solid #1a334e;

      border-radius: 6px;

      padding: 10px 12px;

      text-align: center;

    }

    .metric-tile .mt-lbl {

      font-size: 12px;

      color: #cbd5e1;

      font-family: var(--font-body);

      font-weight: 700;

      text-transform: uppercase;

    }

    .metric-tile .mt-val {

      font-family: var(--font-mono);

      font-size: 20px;

      font-weight: 800;

      color: #ffffff;

      margin-top: 2px;

    }



    /* Seasons Bar */

    .seasons-bar {

      display: flex;

      gap: 8px;

      overflow-x: auto;

      padding-bottom: 10px;

      margin-bottom: 20px;

    }



    .season-btn {

      background: #0f243a;

      color: #e2e8f0;

      border: 1px solid #234568;

      border-radius: 6px;

      font-family: var(--font-body);

      font-size: 14px;

      font-weight: 600;

      padding: 8px 18px;

      cursor: pointer;

      white-space: nowrap;

      transition: all 0.15s ease;

    }

    .season-btn:hover {

      background: #18385a;

      border-color: #38bdf8;

      color: #fff;

    }

    .season-btn.active {

      background: #ffcb05;

      border-color: #ffcb05;

      color: #000000;

      font-weight: 800;

    }



    .season-banner {

      background: #0c1e32;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      padding: 18px 22px;

      margin-bottom: 20px;

      box-shadow: 0 4px 16px rgba(0,0,0,0.4);

    }

    .season-title {

      font-family: var(--font-title);

      font-size: 20px;

      color: #ffcb05;

      letter-spacing: 0.5px;

    }

    .season-meta {

      font-size: 13px;

      color: #cbd5e1;

      margin-top: 4px;

      font-weight: 500;

    }



    /* Match Score Cards */

    .match-card {

      background: #0c1e32;

      border: 1px solid #1a334e;

      border-radius: 6px;

      padding: 10px 14px;

      display: flex;

      justify-content: space-between;

      align-items: center;

      margin-bottom: 8px;

    }



    .score-box {

      font-family: var(--font-mono);

      font-size: 19px;

      font-weight: 800;

      color: #ffcb05;

      background: #000000;

      border: 1px solid #854d0e;

      border-radius: 4px;

      padding: 3px 12px;

      letter-spacing: 2px;

    }



    /* Duel Arena & Head-to-Head Styles */

    .duel-arena {

      background: #0c1e32;

      border: 1px solid #234568;

      border-radius: 8px;

      padding: 24px;

      box-shadow: 0 8px 24px rgba(0,0,0,0.5);

      margin-bottom: 25px;

    }



    .duel-card {

      display: flex;

      align-items: center;

      gap: 16px;

    }



    .duel-avatar {

      width: 64px;

      height: 64px;

      border-radius: 6px;

      border: 2px solid #38bdf8;

      background: #000;

      object-fit: cover;

    }



    .duel-vs-badge {

      font-family: var(--font-title);

      font-size: 28px;

      color: #ffcb05;

    }



    .duel-stat-bar {

      height: 10px;

      border-radius: 4px;

      background: #081729;

      overflow: hidden;

      margin: 10px 0;

      display: flex;

    }



    .dominance-bar {

      height: 100%;

      transition: width 0.3s ease;

    }

    .dominance-cyan { background: #38bdf8; }

    .dominance-gold { background: #ffcb05; }

    .dominance-draw { background: #475569; }



    /* Match History Protocol Rows in Player Modal */

    .modal-match-filters {

      display: flex;

      gap: 6px;

      flex-wrap: wrap;

      margin-bottom: 12px;

    }



    #modalMatchesContainer {

      max-height: 440px;

      overflow-y: auto;

      padding: 8px;

      border: 1px solid #1e3a58;

      background: #06111e;

      border-radius: 8px;

      display: flex;

      flex-direction: column;

      gap: 6px;

    }



    .match-history-row {

      display: flex;

      align-items: center;

      justify-content: space-between;

      gap: 12px;

      background: #0c1e32;

      border: 1px solid #1a334e;

      border-radius: 6px;

      padding: 8px 14px;

      transition: background 0.12s ease;

    }

    .match-history-row:hover {

      background: #142f4c;

      border-color: #38bdf8;

    }



    .mhr-meta {

      display: flex;

      align-items: center;

      gap: 8px;

      min-width: 170px;

      flex-shrink: 0;

    }

    .mhr-badge {

      font-family: var(--font-body);

      font-size: 11px;

      padding: 3px 8px;

      border-radius: 4px;

      letter-spacing: 0.3px;

      text-transform: uppercase;

      white-space: nowrap;

      font-weight: 800;

    }

    .mhr-stage {

      font-size: 12px;

      color: #cbd5e1;

      font-weight: 700;

      white-space: nowrap;

    }



    .mhr-result {

      flex-shrink: 0;

      min-width: 95px;

    }



    .mhr-duel {

      display: flex;

      align-items: center;

      justify-content: center;

      gap: 12px;

      flex: 1;

    }



    .mhr-player {

      display: flex;

      align-items: center;

      gap: 8px;

      flex: 1;

    }

    .mhr-home {

      justify-content: flex-end;

      text-align: right;

    }

    .mhr-away {

      justify-content: flex-start;

      text-align: left;

      cursor: pointer;

    }

    .mhr-away:hover .mhr-name {

      color: #38bdf8;

      text-decoration: underline;

    }



    .mhr-avatar {

      width: 28px;

      height: 28px;

      border-radius: 4px;

      border: 1px solid rgba(255, 255, 255, 0.25);

      background: #000;

      object-fit: cover;

      flex-shrink: 0;

    }



    .mhr-name {

      font-family: var(--font-body);

      font-size: 14px;

      font-weight: 600;

      color: #cbd5e1;

      white-space: nowrap;

      overflow: hidden;

      text-overflow: ellipsis;

      max-width: 150px;

    }

    .mhr-winner {

      color: #ffffff;

      font-weight: 800;

    }



    .mhr-score-box {

      display: inline-flex;

      align-items: center;

      gap: 4px;

      background: #000000;

      border: 1px solid #854d0e;

      border-radius: 4px;

      padding: 3px 12px;

      font-family: var(--font-mono);

      font-size: 17px;

      font-weight: 800;

      flex-shrink: 0;

    }

    .mhr-score-num {

      min-width: 14px;

      text-align: center;

    }

    .mhr-score-win { color: #ffcb05; }

    .mhr-score-loss { color: #94a3b8; }

    .mhr-score-divider {

      color: #64748b;

      font-size: 15px;

    }



    .tag-penalty { background: #581c87; color: #f3e8ff; }

    .tag-blitz { background: #0369a1; color: #e0f2fe; }

    .tag-offseason { background: #b45309; color: #fef08a; }



    /* Special & Team Tournaments */

    .special-card {

      background: #0c1e32;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      padding: 20px;

      box-shadow: 0 4px 16px rgba(0,0,0,0.4);

      margin-bottom: 24px;

    }



    .podium-grid {

      display: grid;

      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));

      gap: 12px;

      margin: 16px 0;

    }



    .podium-item {

      background: #081729;

      border: 1px solid #1a334e;

      border-radius: 6px;

      padding: 12px;

      text-align: center;

    }



    



    /* Responsive */

    @media (max-width: 900px) {

      .header-inner { flex-direction: column; align-items: stretch; }

      nav { justify-content: center; }

      .controls-row { flex-direction: column; align-items: stretch; }

      .clean-search { width: 100%; }

      .clean-search:focus { width: 100%; }

    }

  

    /* ==========================================================================

       HEAD-TO-HEAD DUEL ARENA (CRYSTAL CLEAR, ZERO GLOW, NO BLUE+YELLOW PAIRING)

       Palette: Crimson/Red (#f43f5e) vs Purple/Violet (#c084fc)

       ========================================================================== */

    .duel-arena-card {

      background: #0c1e32;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      padding: 24px;

      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);

      margin-bottom: 25px;

    }



    .duel-select-group {

      display: flex;

      gap: 16px;

      align-items: center;

      flex-wrap: wrap;

      margin-bottom: 20px;

    }



    .duel-fighter-col {

      flex: 1;

      min-width: 260px;

    }



    .duel-corner-label {

      font-family: var(--font-body);

      font-size: 13px;

      font-weight: 700;

      text-transform: uppercase;

      letter-spacing: 0.5px;

      margin-bottom: 6px;

      display: flex;

      align-items: center;

      gap: 6px;

    }

    .duel-corner-p1 { color: #f43f5e; }

    .duel-corner-p2 { color: #c084fc; justify-content: flex-end; }



    .duel-select {

      background-color: #0f243a;

      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%23cbd5e1' d='M6 8L0 0h12z'/%3E%3C/svg%3E");

      background-repeat: no-repeat;

      background-position: right 14px center;

      border: 1px solid #2a4e75;

      border-radius: 6px;

      color: #ffffff;

      font-family: var(--font-body);

      font-size: 15px;

      font-weight: 600;

      padding: 10px 38px 10px 14px;

      width: 100%;

      appearance: none;

      -webkit-appearance: none;

      cursor: pointer;

      transition: border-color 0.15s ease, background-color 0.15s ease;

    }

    .duel-select:focus {

      border-color: #cbd5e1;

      background-color: #14324f;

      outline: none;

    }

    .duel-select optgroup {

      background: #081729;

      color: #94a3b8;

      font-weight: 700;

    }

    .duel-select option {

      background: #0f243a;

      color: #ffffff;

      padding: 8px 12px;

    }



    .duel-vs-divider {

      font-family: var(--font-title);

      font-size: 18px;

      font-weight: 900;

      color: #ffffff;

      background: #142a42;

      border: 1px solid #2a4e75;

      border-radius: 50%;

      width: 44px;

      height: 44px;

      display: flex;

      align-items: center;

      justify-content: center;

      flex-shrink: 0;

      margin: 18px auto 0 auto;

    }



    .h2h-presets-bar {

      margin-bottom: 22px;

      padding-bottom: 18px;

      border-bottom: 1px solid #1e3a58;

    }



    .h2h-presets-label {

      font-size: 12px;

      font-weight: 700;

      color: #cbd5e1;

      text-transform: uppercase;

      letter-spacing: 0.5px;

      margin-bottom: 10px;

      display: flex;

      align-items: center;

      gap: 6px;

    }



    .h2h-presets-list {

      display: flex;

      gap: 8px;

      flex-wrap: wrap;

    }



    .h2h-preset-chip {

      background: #0f243a;

      color: #f1f5f9;

      border: 1px solid #2a4e75;

      border-radius: 6px;

      font-family: var(--font-body);

      font-size: 13px;

      font-weight: 600;

      padding: 6px 12px;

      cursor: pointer;

      transition: all 0.12s ease;

      white-space: nowrap;

      display: inline-flex;

      align-items: center;

      gap: 6px;

    }

    .h2h-preset-chip:hover {

      background: #1c3c5e;

      border-color: #cbd5e1;

      color: #ffffff;

    }



    .h2h-billboard {

      background: #081729;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      padding: 20px;

      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);

      margin-bottom: 24px;

    }



    .h2h-fighters-row {

      display: flex;

      justify-content: space-between;

      align-items: stretch;

      flex-wrap: wrap;

      gap: 16px;

    }



    .fighter-card {

      flex: 1;

      min-width: 250px;

      background: #0c1e32;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      padding: 16px;

      display: flex;

      align-items: center;

      gap: 14px;

      cursor: pointer;

      transition: all 0.15s ease;

    }

    .fighter-card:hover {

      background: #112944;

    }

    .fighter-card.p1-side {

      border-top: 4px solid #f43f5e;

    }

    .fighter-card.p2-side {

      border-top: 4px solid #c084fc;

    }



    .fighter-avatar {

      width: 56px;

      height: 56px;

      border-radius: 6px;

      object-fit: cover;

      flex-shrink: 0;

      background: #000;

    }

    .p1-side .fighter-avatar { border: 2px solid #f43f5e; }

    .p2-side .fighter-avatar { border: 2px solid #c084fc; }



    .fighter-info {

      flex: 1;

      min-width: 0;

    }

    .fighter-name {

      font-family: var(--font-body);

      font-size: 18px;

      font-weight: 700;

      color: #ffffff;

      white-space: nowrap;

      overflow: hidden;

      text-overflow: ellipsis;

    }

    .fighter-meta {

      font-size: 12px;

      color: #cbd5e1;

      margin-top: 3px;

    }

    .fighter-wins-badge {

      display: inline-block;

      font-family: var(--font-mono);

      font-size: 13px;

      font-weight: 800;

      padding: 3px 10px;

      border-radius: 4px;

      margin-top: 6px;

    }

    .p1-side .fighter-wins-badge { background: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid #f43f5e; }

    .p2-side .fighter-wins-badge { background: rgba(192, 132, 252, 0.15); color: #c084fc; border: 1px solid #c084fc; }



    .duel-center-stats {

      flex: 1.2;

      min-width: 260px;

      display: flex;

      flex-direction: column;

      justify-content: center;

      align-items: center;

      text-align: center;

      padding: 8px 12px;

    }

    .duel-score-large {

      font-family: var(--font-mono);

      font-size: 38px;

      font-weight: 900;

      line-height: 1;

      letter-spacing: 2px;

      display: flex;

      align-items: center;

      gap: 12px;

    }

    .p1-color { color: #f43f5e; }

    .p2-color { color: #c084fc; }

    .duel-colon { color: #64748b; font-size: 30px; }



    .duel-ratio-bar {

      width: 100%;

      max-width: 320px;

      height: 8px;

      background: #142a42;

      border-radius: 4px;

      overflow: hidden;

      display: flex;

      margin: 12px 0 8px 0;

    }

    .duel-bar-p1 {

      background: #f43f5e;

      height: 100%;

    }

    .duel-bar-draw {

      background: #64748b;

      height: 100%;

    }

    .duel-bar-p2 {

      background: #c084fc;

      height: 100%;

    }



    .duel-submetrics {

      font-size: 12px;

      color: #cbd5e1;

      font-weight: 500;

      display: flex;

      gap: 14px;

      flex-wrap: wrap;

      justify-content: center;

    }

    .duel-submetrics strong { color: #ffffff; }



    .h2h-history-box {

      background: #0a1b2d;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      overflow: hidden;

    }



    .h2h-history-header {

      background: #06111e;

      border-bottom: 2px solid #1e3a58;

      padding: 12px 18px;

      display: flex;

      justify-content: space-between;

      align-items: center;

      font-size: 14px;

      font-weight: 700;

      color: #cbd5e1;

      flex-wrap: wrap;

      gap: 8px;

    }



    .h2h-history-list {

      display: flex;

      flex-direction: column;

    }



    .h2h-match-row {

      display: flex;

      align-items: center;

      justify-content: space-between;

      gap: 14px;

      padding: 12px 18px;

      border-bottom: 1px solid #132437;

      background: #0a1b2d;

      transition: background 0.12s ease;

      flex-wrap: wrap;

    }

    .h2h-match-row:nth-child(even) {

      background: #0d2137;

    }

    .h2h-match-row:hover {

      background: #153252;

    }



    .h2h-match-meta {

      width: 240px;

      flex-shrink: 0;

      display: flex;

      flex-direction: column;

      gap: 2px;

    }

    .h2h-match-season {

      font-family: var(--font-body);

      font-size: 13px;

      font-weight: 700;

      color: #ffffff;

      white-space: nowrap;

      overflow: hidden;

      text-overflow: ellipsis;

    }

    .h2h-match-sub {

      font-size: 12px;

      color: #cbd5e1;

      display: flex;

      align-items: center;

      gap: 6px;

    }



    .h2h-duel-center {

      flex: 1;

      display: flex;

      align-items: center;

      justify-content: center;

      gap: 16px;

      min-width: 280px;

    }



    .h2h-player-cell {

      flex: 1;

      font-size: 15px;

      font-weight: 700;

      white-space: nowrap;

      overflow: hidden;

      text-overflow: ellipsis;

      transition: color 0.12s ease;

    }

    .h2h-player-cell:hover {

      text-decoration: underline;

    }

    .h2h-p1-cell {

      text-align: right;

      color: #e2e8f0;

    }

    .h2h-p2-cell {

      text-align: left;

      color: #e2e8f0;

    }

    .h2h-p1-winner { color: #f43f5e; font-weight: 800; }

    .h2h-p2-winner { color: #c084fc; font-weight: 800; }



    .h2h-score-box {

      background: #06111e;

      border: 1px solid #234568;

      border-radius: 6px;

      font-family: var(--font-mono);

      font-size: 15px;

      font-weight: 800;

      padding: 5px 14px;

      min-width: 80px;

      text-align: center;

      letter-spacing: 1px;

      color: #ffffff;

      flex-shrink: 0;

      display: flex;

      align-items: center;

      justify-content: center;

      gap: 6px;

    }



    .h2h-result-badge {

      width: 140px;

      flex-shrink: 0;

      text-align: right;

      display: flex;

      flex-direction: column;

      align-items: flex-end;

    }



  

    /* Source Action Buttons (Pure VK & Video) */

    .source-btn-vk {

      cursor: pointer;

      display: inline-flex;

      align-items: center;

      gap: 4px;

      background: #2787f5;

      color: #ffffff !important;

      font-family: var(--font-body);

      font-size: 11px;

      font-weight: 700;

      padding: 3px 8px;

      border-radius: 4px;

      text-decoration: none;

      transition: background 0.15s ease, transform 0.1s ease;

      white-space: nowrap;

      border: 1px solid rgba(255,255,255,0.2);

    }

    .source-btn-vk:hover {

      background: #1971d2;

      transform: translateY(-1px);

    }



    .video-modal-overlay {

      display: none;

      position: fixed;

      inset: 0;

      background: rgba(3, 7, 18, 0.9);

      backdrop-filter: blur(8px);

      z-index: 10500;

      align-items: center;

      justify-content: center;

      padding: 20px;

    }

    .video-modal-box {

      background: #081729;

      border: 2px solid var(--nes-cyan);

      box-shadow: 0 0 35px rgba(0, 229, 255, 0.35), 0 20px 60px rgba(0,0,0,0.85);

      border-radius: 8px;

      width: 100%;

      max-width: 960px;

      display: flex;

      flex-direction: column;

      overflow: hidden;

      animation: modalFadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);

    }

    .video-modal-header {

      display: flex;

      justify-content: space-between;

      align-items: center;

      padding: 12px 18px;

      background: #0c1e32;

      border-bottom: 1px solid #1a334e;

    }

    .video-modal-title {

      display: flex;

      align-items: center;

      gap: 8px;

      overflow: hidden;

      text-overflow: ellipsis;

      white-space: nowrap;

      padding-right: 12px;

    }

    .video-external-btn {

      display: inline-flex;

      align-items: center;

      gap: 4px;

      background: rgba(255, 255, 255, 0.08);

      border: 1px solid rgba(255, 255, 255, 0.2);

      color: #cbd5e1 !important;

      font-size: 11px;

      font-weight: 700;

      padding: 4px 10px;

      border-radius: 4px;

      text-decoration: none;

      transition: all 0.15s ease;

      white-space: nowrap;

    }

    .video-external-btn:hover {

      background: rgba(0, 229, 255, 0.15);

      border-color: var(--nes-cyan);

      color: var(--nes-cyan) !important;

    }

    .video-player-container {

      position: relative;

      width: 100%;

      padding-bottom: 56.25%; /* 16:9 ratio */

      height: 0;

      background: #000000;

      overflow: hidden;

      border-radius: 0 0 6px 6px;

    }

    .video-player-container iframe {

      position: absolute;

      top: 0;

      left: 0;

      width: 100%;

      height: 100%;

      border: 0;

    }



    .source-btn-video {

      cursor: pointer;

      line-height: normal;

      display: inline-flex;

      align-items: center;

      gap: 4px;

      background: #dc2626;

      color: #ffffff !important;

      font-family: var(--font-body);

      font-size: 11px;

      font-weight: 700;

      padding: 3px 8px;

      border-radius: 4px;

      text-decoration: none;

      transition: background 0.15s ease, transform 0.1s ease;

      white-space: nowrap;

      border: 1px solid rgba(255,255,255,0.2);

    }

    .source-btn-video:hover {

      background: #b91c1c;

      transform: translateY(-1px);

    }



    /* ==========================================================================

       SEASONS ARCHIVE, PODIUM & PROTOCOLS STYLING

       ========================================================================== */

    .season-tab-btn {

      background: #0f243a;

      color: #f1f5f9;

      border: 1px solid #2a4e75;

      border-radius: 6px;

      font-family: var(--font-body);

      font-size: 14px;

      font-weight: 600;

      padding: 8px 16px;

      cursor: pointer;

      transition: all 0.12s ease;

      white-space: nowrap;

      box-shadow: none !important;

    }

    .season-tab-btn:hover {

      background: #1c3c5e;

      border-color: #38bdf8;

      color: #ffffff;

    }

    .season-tab-btn.active {

      background: #ffcb05;

      border-color: #ffcb05;

      color: #000000;

      font-weight: 800;

      box-shadow: none !important;

    }



    .season-card-box {

      background: #0c1e32;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      padding: 24px;

      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);

      margin-bottom: 25px;

    }



    .special-card {

      background: #0c1e32;

      border: 1px solid #1e3a58;

      border-radius: 8px;

      padding: 24px;

      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);

      margin-top: 20px;

    }



    .special-header-row {

      display: flex;

      justify-content: space-between;

      align-items: center;

      flex-wrap: wrap;

      gap: 16px;

      margin-bottom: 20px;

    }



    .podium-box-grid {

      display: grid;

      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));

      gap: 14px;

      margin: 16px 0 20px 0;

    }

    .podium-slot {

      background: #081729;

      border: 1px solid #1a334e;

      border-radius: 6px;

      padding: 12px 16px;

      display: flex;

      align-items: center;

      gap: 14px;

    }

    .podium-slot.gold { border-left: 4px solid #ffcb05; }

    .podium-slot.silver { border-left: 4px solid #cbd5e1; }

    .podium-slot.bronze { border-left: 4px solid #d97706; }



    .special-tag {

      display: inline-block;

      font-family: var(--font-body);

      font-size: 11px;

      font-weight: 800;

      text-transform: uppercase;

      padding: 3px 8px;

      border-radius: 4px;

      letter-spacing: 0.5px;

      border: 1px solid transparent;

    }

    .tag-solo {

      background: #1e3a8a;

      color: #bfdbfe;

      border-color: #3b82f6;

    }



    .player-chip-link {

      display: inline-flex;

      align-items: center;

      gap: 6px;

      background: #0f243a;

      color: #cbd5e1;

      border: 1px solid #234568;

      border-radius: 4px;

      padding: 3px 8px;

      font-size: 12px;

      font-weight: 600;

      cursor: pointer;

      transition: all 0.12s ease;

    }

    .player-chip-link:hover {

      background: #1c3c5e;

      border-color: #38bdf8;

      color: #ffffff;

    }



    .part-prof-btn {

      background: #14324f;

      color: #38bdf8;

      border: 1px solid #2b5680;

      border-radius: 4px;

      padding: 2px 8px;

      font-size: 12px;

      font-weight: 700;

      cursor: pointer;

      transition: all 0.12s ease;

    }

    .part-prof-btn:hover {

      background: #38bdf8;

      color: #000000;

      border-color: #38bdf8;

    }



    .special-table {

      width: 100%;

      border-collapse: collapse;

      background: #0a1b2d;

      border-radius: 6px;

      overflow: hidden;

      margin-top: 10px;

    }

    .special-table th {

      background: #06111e;

      color: #cbd5e1;

      font-size: 12px;

      font-weight: 700;

      padding: 10px 12px;

      border-bottom: 2px solid #1e3a58;

    }

    .special-table td {

      padding: 8px 12px;

      border-bottom: 1px solid #132437;

      font-size: 13px;

      color: #e2e8f0;

    }

    .special-table tr:hover {

      background: #153252;

    }



    .score-badge {

      background: #06111e;

      border: 1px solid #234568;

      border-radius: 6px;

      font-family: var(--font-mono);

      font-size: 15px;

      font-weight: 800;

      padding: 5px 14px;

      min-width: 80px;

      text-align: center;

      letter-spacing: 1px;

      color: #ffffff;

      display: inline-flex;

      align-items: center;

      justify-content: center;

      gap: 4px;

    }



    .h2h-match-item {

      display: flex;

      align-items: center;

      justify-content: space-between;

      gap: 12px;

      padding: 10px 14px;

      border-radius: 6px;

      border: 1px solid #1a334e;

      background: #0a1b2d;

      margin-bottom: 8px;

      transition: background 0.12s ease;

      flex-wrap: wrap;

    }

    .h2h-match-item:hover {

      background: #153252;

    }

</style>

</head>

<body data-discipline="soccer">



  <!-- Retro Header -->

  <header>

    <div class="header-inner">

      <a href="#/leaderboard" class="logo-block">

        <div class="logo-badge">GOAL 3</div>

        <div class="logo-text">

          <h1>NEKKETSU SOCCER LEAGUE</h1>

          <p>ОФИЦИАЛЬНЫЙ КИБЕРСПОРТИВНЫЙ ПОРТАЛ СООБЩЕСТВА NST (2015–2026)</p>

        </div>

      </a>

      <div class="header-meta-stats">

        <span class="meta-stat-pill">🎮 <strong>2 414</strong> матчей</span>

        <span class="meta-stat-pill">⚽ <strong>15 531</strong> гол</span>

        <span class="meta-stat-pill">👥 <strong>103</strong> игрока</span>

        <a href="index.html" class="meta-vk-btn" style="background: rgba(255, 203, 5, 0.15); border-color: var(--nes-gold); color: var(--nes-gold) !important;" title="Вернуться на главную страницу Альманаха Nekketsu">🏛️ В Альманах</a>
        <a href="quotes.html" class="meta-vk-btn" style="background: rgba(255, 203, 5, 0.08); border-color: rgba(255, 203, 5, 0.4); color: var(--nes-gold) !important;" title="Золотой Цитатник Сообщества NST">💬 Цитатник ↗</a>

        <a href="https://vk.ru/nekketsu" target="_blank" class="meta-vk-btn">VK Сообщество ↗</a>

      </div>

    </div>

    <div class="nav-bar-container">

      <nav class="nav-bar">

        <button class="nav-btn active" onclick="switchTab('leaderboard')">🏆 Рейтинг</button>

        <button class="nav-btn" onclick="switchTab('players')">👤 Карточки игроков</button>

        <button class="nav-btn" onclick="switchTab('seasons')">📅 Сезоны (1–9)</button>

        <button class="nav-btn" onclick="switchTab('teams')">⚡ Клубные 2х2</button>

        <button class="nav-btn" onclick="switchTab('special')">🎯 Спецтурниры</button>

        <button class="nav-btn" onclick="switchTab('h2h')">⚔️ Личные встречи</button>

        <button class="nav-btn" onclick="switchTab('clutch')">🏛️ Зал славы</button>

      </nav>

    </div>

  </header>



  <main class="container">

    <!-- TAB 1: LEADERBOARD -->
    <section id="tab-leaderboard" class="view-content active">
      <!-- HUD Metrics inside Leaderboard tab -->
      <div class="hud-metrics" id="hudStrip"></div>
      <div class="controls-row">
        <div class="filter-tabs">
          <button class="filter-btn active" id="btnActiveFilter" onclick="filterDivision('active', this)">▶ Все активные (22)</button>
          <button class="filter-btn" onclick="filterDivision('Высшая', this)">⚡ Высшая лига (9)</button>
          <button class="filter-btn" onclick="filterDivision('Средняя', this)">🔰 Средняя лига (8)</button>
          <button class="filter-btn" onclick="filterDivision('Дворовая', this)">⚽ Дворовая лига (5)</button>
          <button class="filter-btn inactive-tab" id="btnInactiveFilter" onclick="filterDivision('inactive', this)">🏛️ Зал славы (11)</button>
          <button class="filter-btn inactive-tab" onclick="filterDivision('all_inactive', this)">📦 Все неактивные (78)</button>
        </div>
        <input type="text" class="clean-search" id="tableSearch" placeholder="Поиск по нику или имени..." oninput="renderTable()">
      </div>

      <div id="hofCriteriaBanner" style="display: none; background: rgba(255, 183, 3, 0.08); border: 2px solid var(--nes-gold); padding: 14px 18px; margin-bottom: 16px; box-shadow: 3px 3px 0 #000;">
        <div style="display: flex; align-items: flex-start; gap: 14px;">
          <div style="font-size: 32px; line-height: 1;">🏛️</div>
          <div>
            <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 6px;">
              КРИТЕРИИ ЗАЛА СЛАВЫ NEKKETSU LEAGUE (HALL OF FAME)
            </div>
            <div style="font-size: 13px; color: #cbd5e1; line-height: 1.5;">
              В Зал Славы включены только легендарные ветераны <strong>Высшей (элитной) лиги</strong>, завершившие активную карьеру: чемпионы сезонов, обладатели Кубка Лиг и первопроходцы сцены с огромным стажем матчей на высшем уровне. Игроки низших дивизионов и случайные участники сюда не допускаются.
            </div>
            <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; font-size: 12px; color: #94a3b8;">
              <span>🥇 <strong>Титулы:</strong> Золото Высшей лиги / Кубок Лиг</span>
              <span>⚔️ <strong>Опыт:</strong> Десятки матчей против сильнейших топов</span>
              <span>👑 <strong>Статус:</strong> Инактив (Легенда сцены)</span>
            </div>
          </div>
        </div>
      </div>

      <div class="table-box">

        <table>

          <thead>

            <tr>

              <th onclick="sortTable('rank')">Место</th>

              <th onclick="sortTable('player')">Игрок</th>

              <th onclick="sortTable('league')">Лига и статус</th>

              <th onclick="sortTable('active_elo')">Текущий рейтинг ▾</th>

              <th onclick="sortTable('peak_elo')">Рекорд рейтинга</th>

              <th onclick="sortTable('matches')">Матчи</th>

              <th onclick="sortTable('wins')">Победы / Поражения</th>

              <th onclick="sortTable('win_rate')">% побед</th>

              <th onclick="sortTable('goals_for')">Мячи (Разница)</th>

              <th title="Победы в основное время / в овертайме / по пенальти">Осн / ОТ / Пен</th>

              <th>Профиль</th>

            </tr>

          </thead>

          <tbody id="tableBody"></tbody>

        </table>

      </div>

      <div style="font-size: 12px; color: #94a3b8; margin-top: -15px; margin-bottom: 25px;">

        💡 <em>Текущий рейтинг рассчитывается по системе силы соперников (Elo). За пропуск сезонов начисляется штраф за простой, который уменьшается при возвращении в турниры.</em>

      </div>

    </section>



    <!-- TAB 2: PLAYERS CARDS -->

    <section id="tab-players" class="view-content">

      <div class="controls-row">

        <div class="filter-tabs">

          <button class="filter-btn active" onclick="filterPlayerCards('active', this)">🟢 Все активные (22)</button>

          <button class="filter-btn" onclick="filterPlayerCards('Высшая', this)">🏆 Высшая лига (9)</button>

          <button class="filter-btn" onclick="filterPlayerCards('Средняя', this)">⚡ Средняя лига (8)</button>

          <button class="filter-btn" onclick="filterPlayerCards('Дворовая', this)">🍺 Дворовая лига (5)</button>

          <button class="filter-btn inactive-tab" onclick="filterPlayerCards('hof', this)">⭐ Зал славы (11)</button>

          <button class="filter-btn inactive-tab" onclick="filterPlayerCards('all_inactive', this)">📦 Все неактивные (78)</button>

          <button class="filter-btn" onclick="filterPlayerCards('all', this)">🌐 Полная база (100)</button>

        </div>

        <input type="text" class="clean-search" id="cardsSearch" placeholder="Поиск по имени игрока..." oninput="renderCards()">

      </div>

      <div id="hofCardsCriteriaBanner" style="display: none; background: rgba(255, 183, 3, 0.08); border: 2px solid var(--nes-gold); padding: 14px 18px; margin-bottom: 16px; box-shadow: 3px 3px 0 #000;">

        <div style="display: flex; align-items: flex-start; gap: 14px;">

          <div style="font-size: 32px; line-height: 1;">🏛️</div>

          <div>

            <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 6px;">

              КРИТЕРИИ ЗАЛА СЛАВЫ NEKKETSU LEAGUE (HALL OF FAME)

            </div>

            <div style="font-size: 13px; color: #cbd5e1; line-height: 1.5;">

              В Зал Славы включены только легендарные ветераны <strong>Высшей (элитной) лиги</strong>, завершившие активную карьеру: чемпионы сезонов, обладатели Кубка Лиг и первопроходцы сцены с огромным стажем матчей на высшем уровне. Игроки низших дивизионов и случайные участники сюда не допускаются.

            </div>

            <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; font-size: 12px; color: #94a3b8;">

              <span>🥇 <strong>Титулы:</strong> Золото Высшей лиги / Кубок Лиг</span>

              <span>⚔️ <strong>Опыт:</strong> Десятки матчей против сильнейших топов</span>

              <span>👑 <strong>Статус:</strong> Инактив (Легенда сцены)</span>

            </div>

          </div>

        </div>

      </div>

      <div class="cards-grid" id="cardsGrid"></div>

    </section>



    <!-- TAB 3: SEASONS ARCHIVE -->

    <section id="tab-seasons" class="view-content">

      <div class="season-banner">

        <div class="season-title">🏆 АРХИВ ОФИЦИАЛЬНЫХ СЕЗОНОВ NST (1–9)</div>

        <div class="season-meta">

          <span>🎮 Goal 3 (NES)</span>

          <span>🏆 9 Регулярных Чемпионатов</span>

          <span>📅 2014 – 2021 гг.</span>

        </div>

        <p style="color: #cbd5e1; font-size: 14px; margin-top: 8px; line-height: 1.5;">

          Полная история всех девяти официальных номерных чемпионатов сообщества Nekketsu Soccer League. Турнирные таблицы Высшей, Средней, Младшей и Дворовой лиг, списки призёров, обладатели кубков и протоколы всех сыгранных матчей.

        </p>

      </div>



      <!-- Quick Tournament Selector Bar (Unified across all blocks) -->

      <div style="margin-bottom: 20px;">

        <div style="font-size: 11px; color: #94a3b8; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">ВЫБЕРИТЕ СЕЗОН:</div>

        <div class="seasons-bar" id="seasonsBar" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>

      </div>



      <!-- Main Detailed Container for Selected Season -->

      <div id="seasonDetails"></div>

    </section>



    <!-- TAB 4: CLUTCH & RECORDS -->

    <section id="tab-clutch" class="view-content">

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px;">

        <div class="table-box" style="padding: 18px;">

          <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-gold); margin-bottom: 12px;">⚡ Лидеры по победам в овертаймах и пенальти</h2>

          <div style="font-size: 12px; color: #94a3b8; margin-bottom: 14px;">Статистика самых стойких игроков в матчах до золотого гола</div>

          <div id="clutchLeaders"></div>

        </div>

        <div class="table-box" style="padding: 18px;">

          <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-cyan); margin-bottom: 12px;">🏆 Исторические рекорды лиги NST</h2>

          <div style="font-size: 12px; color: #94a3b8; margin-bottom: 14px;">Выдающиеся матчи и достижения за всю историю турниров</div>

          <div id="recordsBox"></div>

        </div>

      </div>

    </section>



    <!-- TAB 5: HEAD-TO-HEAD -->

    <section id="tab-h2h" class="view-content">

      <div class="season-card-box">

        <h2 style="font-family: var(--font-title); font-size: 22px; color: #ffffff; margin-bottom: 8px;">⚔️ Личные встречи и история противостояний</h2>

        <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 20px;">Интерактивный калькулятор очных дуэлей 1 на 1 и статистика главных дерби лиги NST за все 9 сезонов и спецтурниры</div>



        <!-- Interactive 1x1 Comparator -->

        <div class="duel-arena-card">

          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;">

            <div style="font-family: var(--font-body); font-size: 15px; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 8px;">

              <span>🥊 АРЕНА ЛИЧНЫХ ВСТРЕЧ &bull; ДУЭЛЬ 1 НА 1</span>

            </div>

            <div style="font-size: 12px; color: #cbd5e1; font-weight: 600;">База включает 2 562 матча лиги, кубков и спецтурниров</div>

          </div>



          <div class="duel-select-group">

            <div class="duel-fighter-col">

              <div class="duel-corner-label duel-corner-p1">

                <span>🔴 ИГРОК 1 (КРАСНЫЙ УГОЛ)</span>

              </div>

              <select id="h2hSelectP1" class="duel-select" onchange="updateH2HComparison()"></select>

            </div>



            <div class="duel-vs-divider">

              VS

            </div>



            <div class="duel-fighter-col">

              <div class="duel-corner-label duel-corner-p2">

                <span>🟣 ИГРОК 2 (ПУРПУРНЫЙ УГОЛ)</span>

              </div>

              <select id="h2hSelectP2" class="duel-select" onchange="updateH2HComparison()"></select>

            </div>

          </div>



          <!-- Quick presets -->

          <div class="h2h-presets-bar">

            <div class="h2h-presets-label">⚡ БЫСТРЫЙ ВЫБОР КУЛЬТОВЫХ ДЕРБИ СООБЩЕСТВА:</div>

            <div class="h2h-presets-list" id="h2hPresets">

              <button class="h2h-preset-chip" onclick="selectH2HPair('ectoPower', 'PacnyTHuK')">👑 ectoPower vs PacnyTHuK</button>

              <button class="h2h-preset-chip" onclick="selectH2HPair('Kunio', 'Ric25')">🛡️ Kunio vs Ric25</button>

              <button class="h2h-preset-chip" onclick="selectH2HPair('ectoPower', 'mafuta')">🔥 ectoPower vs mafuta</button>

              <button class="h2h-preset-chip" onclick="selectH2HPair('Romix', 'ectoPower')">⚡ Romix vs ectoPower</button>

              <button class="h2h-preset-chip" onclick="selectH2HPair('Jamlight', 'Kubik')">🎯 Jamlight vs Kubik</button>

              <button class="h2h-preset-chip" onclick="selectH2HPair('Aoshi', 'Kubik')">⚽ Aoshi vs Kubik</button>

              <button class="h2h-preset-chip" onclick="selectH2HPair('Aoshi', 'Chocopie')">🥊 Aoshi vs Chocopie</button>

              <button class="h2h-preset-chip" onclick="selectH2HPair('Kunio', 'Memori')">🦅 Kunio vs Memori</button>

            </div>

          </div>



          <!-- Battle Result Container -->

          <div id="h2hComparisonResult"></div>

        </div>



        <!-- Curated community rivalries -->

        <h3 style="font-family: var(--font-title); font-size: 18px; color: #ffffff; margin: 28px 0 14px 0;">🔥 Легендарные противостояния и криптониты лиги</h3>

        <div id="h2hList" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px;"></div>

      </div>

    </section>



  

    

    <!-- TAB 7: TEAM TOURNAMENTS (2X2) -->

    <section id="tab-teams" class="view-content">

      <div class="season-banner">

        <div class="season-title">👥 ОФИЦИАЛЬНЫЕ КОМАНДНЫЕ ЧЕМПИОНАТЫ GOAL 3 (2х2)</div>

        <div class="season-meta">

          <span>🎮 Goal 3 (NES) & Goal 4</span>

          <span>🏆 Эпоха Командных Битв (2012–2023)</span>

          <span>👥 Парный формат 2 на 2 & Клубы</span>

        </div>

        <p style="color: #cbd5e1; font-size: 14px; margin-top: 8px; line-height: 1.5;">

          Золотая летопись официальных командных чемпионатов сообщества NST: выберите турнир для детального просмотра всех сыгранных матчей, таблиц дивизионов, сетки плей-офф и составов легендарных дуэтов.

        </p>

      </div>



      <!-- Quick Tournament Selector Bar (like in Seasons tab!) -->

      <div style="margin-bottom: 20px;">

        <div style="font-size: 11px; color: #94a3b8; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">ВЫБЕРИТЕ КОМАНДНЫЙ ЧЕМПИОНАТ:</div>

        <div class="seasons-bar" id="teamTournamentsBar" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>

      </div>



      <!-- Main Detailed Container for Selected Tournament -->

      <div id="teamTournamentDetailContainer"></div>

    </section>



    <!-- TAB 6: SPECIAL TOURNAMENTS -->

    <section id="tab-special" class="view-content">

      <div class="season-banner">

        <div class="season-title">🏅 АРХИВ СПЕЦТУРНИРОВ, МОЛОДЁЖКИ И МЕЖСЕЗОНЬЯ NST</div>

        <div class="season-meta">

          <span>🎮 Goal 3 & Goal 4</span>

          <span>🏆 9 Официальных Кубков и Турниров</span>

          <span>👥 Участие Легенд и Молодых Игроков</span>

        </div>

        <p style="color: #cbd5e1; font-size: 14px; margin-top: 8px; line-height: 1.5;">

          Полный архив официальных молодёжных первенств (наставники + новички), клубных чемпионатов межсезонья с Премьер и Молодёжной лигами, культовых сольных турниров 1x1, чемпионатов по пенальти и скоростных блиц-турниров сообщества за 2015–2022 гг.

        </p>

      </div>



      <!-- Quick Special Tournament Selector Bar (Unified with Seasons & Team tabs!) -->

      <div style="margin-bottom: 20px;">

        <div style="font-size: 11px; color: #94a3b8; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">ВЫБЕРИТЕ СПЕЦТУРНИР:</div>

        <div class="seasons-bar" id="specialTournamentsBar" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>

      </div>



      <!-- Main Detailed Container for Selected Special Tournament -->

      <div id="specialTournamentDetailContainer"></div>

    </section>



    



  </main>



  <!-- Player Profile Modal -->

  <div class="modal-overlay" id="playerModal" onclick="closePlayerModal(event)">

    <div class="modal-box" onclick="event.stopPropagation()">

      <button class="modal-close" onclick="closePlayerModal()">&times;</button>

      <div class="modal-header" id="modalHeader"></div>

      <div id="modalBody"></div>

    </div>

  </div>



  <!-- Video Player Modal (Кинозал Nekketsu) -->

  <div class="modal-overlay video-modal-overlay" id="videoModal" style="display: none;" onclick="closeVideoModal(event)">

    <div class="video-modal-box" onclick="event.stopPropagation()">

      <div class="video-modal-header">

        <div class="video-modal-title">

          <span style="font-size: 16px;">🎬</span>

          <span id="videoModalTitle" style="font-family: var(--font-title); font-size: 14px; color: var(--nes-cyan); letter-spacing: 0.5px;">Запись матча</span>

        </div>

        <div style="display: flex; align-items: center; gap: 10px;">

          <a id="videoModalExternalLink" href="#" target="_blank" rel="noopener" class="video-external-btn" title="Смотреть на оригинальном видеохостинге">

            В новой вкладке ↗

          </a>

          <button class="modal-close" onclick="closeVideoModal()">&times;</button>

        </div>

      </div>

      <div class="video-player-container">

        <iframe id="videoPlayerIframe" src="" frameborder="0" scrolling="no" style="overflow: hidden; display: block;" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

      </div>

    </div>

  </div>



  <!-- Match Protocol Modal (Отчёт из ВК) -->

  <div class="modal-overlay video-modal-overlay" id="protocolModal" style="display: none;" onclick="closeProtocolModal(event)">

    <div class="video-modal-box" onclick="event.stopPropagation()" style="max-width: 620px;">

      <div class="video-modal-header">

        <div class="video-modal-title">

          <span style="font-size: 16px;">📋</span>

          <span id="protocolModalTitle" style="font-family: var(--font-title); font-size: 14px; color: var(--nes-cyan); letter-spacing: 0.5px;">Протокол матча из ВК</span>

        </div>

        <button class="modal-close" onclick="closeProtocolModal()">&times;</button>

      </div>

      <div style="padding: 20px;">

        <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;">

          <span id="protocolModalDate" style="color: #cbd5e1; font-weight: 600;">📅 Дата</span>

          <span id="protocolModalPage" style="color: var(--nes-gold); font-weight: 700;">📄 Лист в теме</span>

        </div>

        <div style="background: rgba(0,0,0,0.55); border: 1px solid #1e3a58; border-left: 4px solid var(--nes-cyan); border-radius: 4px; padding: 16px; margin-bottom: 18px; box-shadow: inset 0 2px 8px rgba(0,0,0,0.4);">

          <div style="font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 8px;">

            💬 Исходный отчёт игрока:

          </div>

          <pre id="protocolModalText" style="white-space: pre-wrap; word-break: break-word; font-family: var(--font-body); font-size: 13px; color: #f8fafc; line-height: 1.5; margin: 0;"></pre>

        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">

          <a id="protocolModalVkLink" href="#" target="_blank" rel="noopener" class="source-btn-vk" style="font-size: 12px; padding: 6px 14px; text-decoration: none;">

            Перейти к теме в ВК ↗

          </a>

          <button type="button" class="filter-btn" onclick="closeProtocolModal()" style="padding: 6px 16px;">

            Закрыть

          </button>

        </div>

        <div style="font-size: 11px; color: #64748b; margin-top: 12px; line-height: 1.4; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 10px;">

          💡 <em>ВКонтакте показывает регламент вверху каждой страницы темы. Чтобы увидеть сообщение на самом сайте ВК, прокрутите чуть ниже закреплённой шапки.</em>

        </div>

      </div>

    </div>

  </div>



  <footer>

    <div style="max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">

      <div><strong>NEKKETSU SPORTS TOURNAMENTS</strong> &bull; Полный архив матчей и статистика игроков Goal 3</div>

      <div>Киберспортивный портал сообщества &bull; 2015–2026 гг.</div>

    </div>

  </footer>



  <!-- Embedded Complete Dataset -->

  <script>

    const DATA = __DATA_PLACEHOLDER__;

  </script>



  <!-- Main Application Script -->

  <script>

    

    function cleanQuoteLine(str) {

      if (!str) return '';

      return str.split(String.fromCharCode(10)).join(' ').split(String.fromCharCode(13)).join('');

    }



    let currentDivisionFilter = 'active';

    let currentSortColumn = 'active_elo';

    let sortAsc = false;

    let selectedSeasonId = '9';

    let playerCardFilter = 'all';

    let seasonPlayerFilter = 'all';

    let seasonLeagueFilter = 'all';

    let seasonSubTab = 'matches';

    let playoffViewMode = 'bracket';
    let teamPlayoffViewMode = 'bracket';
    let specialPlayoffViewMode = 'bracket';

    // Router
    function handleRouting() {
      const hash = window.location.hash || '#/leaderboard';
      if (hash.startsWith('#/player/')) {
        const pName = decodeURIComponent(hash.replace('#/player/', ''));
        openPlayerModal(pName);
      } else if (hash.startsWith('#/season/')) {
        const sId = hash.replace('#/season/', '');
        switchTab('seasons');
        selectSeason(sId);
      } else {
        const tab = hash.replace('#/', '') || 'leaderboard';
        switchTab(tab);
      }
    }

    function switchTab(tabId) {
            document.querySelectorAll('.view-content').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

      const activeSection = document.getElementById(`tab-${tabId}`);
      if (activeSection) activeSection.classList.add('active');

      const activeBtn = Array.from(document.querySelectorAll('.nav-btn')).find(b => {
        const attr = b.getAttribute('onclick') || '';
        return attr.includes(tabId);
      });
      if (activeBtn) activeBtn.classList.add('active');

      if (tabId === 'seasons' && seasonSubTab === 'playoff' && playoffViewMode === 'bracket') {
        setTimeout(drawBracketConnectors, 60);
      }
      if (tabId === 'teams' && teamSubTab === 'playoff' && teamPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('teamBracketWrapper', 'teamBracketContainer', 'teamBracketSvg'), 60);
      }
      if (tabId === 'special' && specialSubTab === 'playoff' && specialPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('specialBracketWrapper', 'specialBracketContainer', 'specialBracketSvg'), 60);
      }

      if (window.location.hash !== `#/${tabId}` && !window.location.hash.startsWith('#/player/')) {
        history.pushState(null, null, `#/${tabId}`);
      }
    }

    // HUD Strip
    function renderHud() {
      const m = DATA.metadata;
      if (!m) return;
      const strip = document.getElementById('hudStrip');
      if (!strip) return;
      strip.innerHTML = `
        <div class="hud-card">
          <div class="hud-label">Всего сыграно матчей</div>
          <div class="hud-val" style="color: var(--nes-gold);">${m.total_matches_analyzed}</div>
          <div class="hud-sub">Все 9 сезонов (2015–2026 гг.)</div>
        </div>
        <div class="hud-card">
          <div class="hud-label">Забито мячей</div>
          <div class="hud-val">${m.total_goals_recorded}</div>
          <div class="hud-sub">В среднем ${m.avg_goals_per_match} гола за матч</div>
        </div>
        <div class="hud-card">
          <div class="hud-label">Овертаймы и пенальти</div>
          <div class="hud-val" style="color: var(--nes-cyan);">${m.total_ot_pk_matches}</div>
          <div class="hud-sub">18.4% упорных матчей до золотого гола</div>
        </div>
        <div class="hud-card">
          <div class="hud-label">Активных / Всего игроков</div>
          <div class="hud-val" style="color: var(--nes-green);">${m.active_players_count} из ${m.total_players_tracked}</div>
          <div class="hud-sub">${DATA.profiles.filter(p => p.is_hall_of_fame).length} легенд в Зале славы</div>
        </div>
      `;

      const hofCount = DATA.profiles.filter(p => p.is_hall_of_fame).length;
      const btnAct = document.getElementById('btnActiveFilter');
      const btnInact = document.getElementById('btnInactiveFilter');
      if (btnAct) btnAct.innerText = `▶ Все активные игроки (${m.active_players_count})`;
      if (btnInact) btnInact.innerText = `⭐ Зал славы (${hofCount})`;
    }

    // Leaderboard
    function filterDivision(div, btn) {
      currentDivisionFilter = div;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTable();
    }

    function sortTable(col) {
      if (currentSortColumn === col) sortAsc = !sortAsc;
      else { currentSortColumn = col; sortAsc = false; }
      renderTable();
    }

    function renderTable() {
        const hofB = document.getElementById("hofCriteriaBanner");
        if (hofB) hofB.style.display = (currentDivisionFilter === "inactive") ? "block" : "none";
      const q = (document.getElementById('tableSearch')?.value || '').toLowerCase();
      let list = [...DATA.profiles];

      if (currentDivisionFilter === 'active') {
        list = list.filter(p => p.is_active);
      } else if (currentDivisionFilter === 'inactive') {
        list = list.filter(p => p.is_hall_of_fame);
      } else if (currentDivisionFilter === 'all_inactive') {
        list = list.filter(p => !p.is_active);
      } else if (currentDivisionFilter === 'Высшая') {
        list = list.filter(p => p.is_active && p.league === 'Высшая');
      } else if (currentDivisionFilter === 'Средняя') {
        list = list.filter(p => p.is_active && p.league === 'Средняя');
      } else if (currentDivisionFilter === 'Дворовая') {
        list = list.filter(p => p.is_active && p.league === 'Дворовая');
      }

      if (q) {
        list = list.filter(p => p.player.toLowerCase().includes(q) || (p.vk_name && p.vk_name.toLowerCase().includes(q)));
      }

      list.sort((a, b) => {
        let v1 = a[currentSortColumn];
        let v2 = b[currentSortColumn];
        if (typeof v1 === 'string') return sortAsc ? v1.localeCompare(v2) : v2.localeCompare(v1);
        return sortAsc ? (v1 - v2) : (v2 - v1);
      });

      const tbody = document.getElementById('tableBody');
      tbody.innerHTML = list.map((p, idx) => {
        const gdStr = p.goal_diff > 0 ? `+${p.goal_diff}` : `${p.goal_diff}`;
        const gdColor = p.goal_diff > 0 ? 'var(--nes-green)' : (p.goal_diff < 0 ? 'var(--nes-red)' : '#fff');
        const badgeClass = !p.is_active ? 'badge-inactive' : (p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard'));
        const sBadge = p.status_badge || (p.is_active ? 'Активен' : 'Зал славы');
        const sColor = p.is_active ? ((p.status_badge && p.status_badge.includes('Сезон 9')) ? '#22c55e' : '#f59e0b') : '#94a3b8';

        const rankDisplay = idx === 0 
          ? `<span style="display: inline-block; width: 26px; height: 26px; line-height: 24px; text-align: center; border-radius: 50%; background: linear-gradient(135deg, #ffcb05, #d97706); color: #000; font-weight: 900; ">1</span>`
          : (idx === 1
            ? `<span style="display: inline-block; width: 26px; height: 26px; line-height: 24px; text-align: center; border-radius: 50%; background: linear-gradient(135deg, #f1f5f9, #94a3b8); color: #000; font-weight: 900; ">2</span>`
            : (idx === 2
              ? `<span style="display: inline-block; width: 26px; height: 26px; line-height: 24px; text-align: center; border-radius: 50%; background: linear-gradient(135deg, #fdba74, #c2410c); color: #000; font-weight: 900; ">3</span>`
              : `<span style="font-family: var(--font-mono); font-weight: 700; color: #cbd5e1; font-size: 14px;">${idx + 1}</span>`
            )
          );

        return `
          <tr>
            <td style="text-align: center;">${rankDisplay}</td>
            <td>
              <div class="p-cell" onclick="openPlayerModal('${p.player}')">
                <img src="${p.avatar}" class="avatar-clean" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
                <div>
                  <div class="p-name">${p.player}</div>
                  ${(p.vk_name && p.vk_name !== p.player) ? `
                    <div class="p-sub">${p.vk_name}</div>
                  ` : (p.quote ? `
                    <div class="p-sub" style="color: #94a3b8; font-style: italic; font-size: 11px;">«${p.quote.length > 32 ? p.quote.substring(0, 30) + '…' : p.quote}»</div>
                  ` : '')}
                </div>
              </div>
            </td>
            <td>
              <div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-start;">
                <span class="league-badge ${badgeClass}">${p.league} лига</span>
                <span style="font-size: 11px; font-weight: 700; color: ${sColor};">● ${sBadge}</span>
              </div>
            </td>
            <td>
              <div style="font-family: var(--font-mono); font-weight: 800; font-size: 16px; color: #fff;">${p.active_elo.toFixed(1)}</div>
              ${p.decay_penalty > 0 ? `<div style="font-size: 11px; color: var(--nes-red); font-weight: 700;">-${p.decay_penalty} за простой</div>` : ''}
            </td>
            <td><span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold); font-size: 15px;">${p.peak_elo.toFixed(1)}</span></td>
            <td style="font-family: var(--font-mono); font-weight: 700; font-size: 14px;">${p.matches}</td>
            <td>
              <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-green); font-size: 14px;">${p.wins}</span>
              <span style="color: #94a3b8; margin: 0 4px;">/</span>
              <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-red); font-size: 14px;">${p.losses}</span>
            </td>
            <td>
              <div style="display: flex; flex-direction: column; gap: 3px;">
                <span style="font-family: var(--font-mono); font-weight: 700; font-size: 13px; color: ${p.win_rate >= 60 ? 'var(--nes-green)' : (p.win_rate >= 45 ? 'var(--nes-cyan)' : 'var(--nes-gold)')};">${p.win_rate}%</span>
                <div style="width: 44px; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden;">
                  <div style="width: ${p.win_rate}%; height: 100%; background: ${p.win_rate >= 60 ? 'var(--nes-green)' : (p.win_rate >= 45 ? 'var(--nes-cyan)' : 'var(--nes-gold)')}; border-radius: 2px;"></div>
                </div>
              </div>
            </td>
            <td style="font-family: var(--font-mono); font-weight: 700; font-size: 13px;">
              <span>${p.goals_for}:${p.goals_against}</span>
              <span style="font-size: 11px; color: ${gdColor}; margin-left: 4px; font-weight: 800;">(${gdStr})</span>
            </td>
            <td style="font-family: var(--font-mono); font-size: 12px; white-space: nowrap;">
              <span style="color: var(--nes-cyan); font-weight: 700;" title="В основное время">${p.reg_wins} осн</span> / 
              <span style="color: var(--nes-gold); font-weight: 700;" title="В овертаймах">${p.ot_wins} от</span> / 
              <span style="color: #c084fc; font-weight: 700;" title="По пенальти">${p.pk_wins} пен</span>
            </td>
            <td>
              <button class="action-btn" onclick="openPlayerModal('${p.player}')">Анкета ↗</button>
            </td>
          </tr>
        `;
      }).join('');
    }

    // Players View
    function filterPlayerCards(flt, btn) {
      playerCardFilter = flt;
      document.querySelectorAll('#tab-players .filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderCards();
    }

    function renderCards() {
      const hofCB = document.getElementById("hofCardsCriteriaBanner");
      if (hofCB) hofCB.style.display = (playerCardFilter === "hof") ? "block" : "none";
      const q = (document.getElementById('cardsSearch')?.value || '').toLowerCase();
      let list = [...DATA.profiles];

      if (playerCardFilter === 'active') {
        list = list.filter(p => p.is_active);
      } else if (playerCardFilter === 'hof') {
        list = list.filter(p => p.is_hall_of_fame);
      } else if (playerCardFilter === 'all_inactive') {
        list = list.filter(p => !p.is_active);
      } else if (playerCardFilter === 'Высшая') {
        list = list.filter(p => p.is_active && p.league === 'Высшая');
      } else if (playerCardFilter === 'Средняя') {
        list = list.filter(p => p.is_active && p.league === 'Средняя');
      } else if (playerCardFilter === 'Дворовая') {
        list = list.filter(p => p.is_active && p.league === 'Дворовая');
      }

      if (q) {
        list = list.filter(p => p.player.toLowerCase().includes(q) || (p.vk_name && p.vk_name.toLowerCase().includes(q)));
      }

      const grid = document.getElementById('cardsGrid');
      grid.innerHTML = list.map(p => {
        const gdStr = p.goal_diff > 0 ? `+${p.goal_diff}` : `${p.goal_diff}`;
        const badgeClass = !p.is_active ? 'badge-inactive' : (p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard'));
        const sBadge = p.status_badge || (p.is_active ? 'Активен' : 'Зал славы');
        const sColor = p.is_active ? ((p.status_badge && p.status_badge.includes('Сезон 9')) ? '#22c55e' : '#f59e0b') : '#94a3b8';

        return `
          <div class="clean-card" onclick="openPlayerModal('${p.player}')">
            <div class="card-top">
              <img src="${p.avatar}" class="avatar-clean" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
              <div style="flex: 1;">
                <h3>${p.player}</h3>
                ${p.quote ? `
                  <div style="font-size: 11px; color: #cbd5e1; font-style: italic; margin: 3px 0 2px 0; line-height: 1.3;" title="Цитата игрока">
                    «${cleanQuoteLine(p.quote).length > 70 ? cleanQuoteLine(p.quote).substring(0, 68) + '…' : cleanQuoteLine(p.quote)}»
                  </div>
                ` : ''}
                <div style="margin-top: 4px; display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                  <span class="league-badge ${badgeClass}">${p.league} лига</span>
                  <span style="font-size: 11px; font-weight: 700; color: ${sColor};">● ${sBadge}</span>
                  ${p.vk_domain || p.vk_id ? `
                    <a href="${p.vk_domain ? `https://vk.ru/${p.vk_domain}` : `https://vk.ru/id${p.vk_id}`}" target="_blank" class="card-vk-pill" onclick="event.stopPropagation()" title="VK: ${p.vk_name || p.player}">
                      <svg viewBox="0 0 24 24"><path d="M13.162 18.994c.609 0 .858-.406.851-.915-.072-1.747.785-2.28 1.488-2.28.618 0 1.344.428 1.84 1.157.734 1.077 1.258 2.038 2.378 2.038h2.096c1.196 0 1.776-.566 1.442-1.637-.367-1.182-1.603-2.678-2.327-3.486-.554-.62-1.127-1.185-.758-2.02.478-1.076 1.947-3.212 2.27-4.472.167-.655-.178-1.077-.92-1.077h-2.122c-.663 0-.964.332-1.151.78-.445 1.066-1.57 3.327-2.247 3.993-.342.338-.598.24-.76-.085-.298-.596-.341-1.688-.341-2.585 0-2.316.357-3.327-.723-3.582-.437-.103-.984-.132-1.792-.132-1.644 0-2.73.045-3.385.733-.257.27-.37.604-.15.632.493.064.935.318 1.054.945.362 1.905.176 3.655-.66 4.31-.383.298-.828.188-1.156-.214-.943-1.156-1.89-3.39-2.518-5.011-.194-.502-.519-.884-1.139-.884H2.477c-.779 0-.946.368-.946.779 0 .73.945 4.354 4.394 9.176 2.302 3.228 5.568 4.976 8.528 4.976z"/></svg>
                      <span>VK</span>
                    </a>
                  ` : ''}
                </div>
              </div>
            </div>

            <div class="card-stat-strip">
              <div>
                <div class="lbl">РЕЙТИНГ</div>
                <div class="v" style="color: var(--nes-gold);">${p.active_elo.toFixed(1)}</div>
              </div>
              <div>
                <div class="lbl">% ПОБЕД</div>
                <div class="v" style="color: var(--nes-green);">${p.win_rate}%</div>
              </div>
              <div>
                <div class="lbl">РАЗНИЦА МЯЧЕЙ</div>
                <div class="v">${gdStr}</div>
              </div>
            </div>

            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #cbd5e1; font-weight: 600;">
              <span>Матчей: <strong>${p.matches}</strong></span>
              <span>Побед: <strong style="color: var(--nes-green);">${p.wins}</strong></span>
              <span>Поражений: <strong style="color: var(--nes-red);">${p.losses}</strong></span>
            </div>
          </div>
        `;
      }).join('');
    }

    // Modal Profile
    function openPlayerModal(pName) {
      const p = DATA.profiles.find(x => x.player.toLowerCase() === pName.toLowerCase());
      if (!p) return;

      window.location.hash = `#/player/${p.player}`;

      const header = document.getElementById('modalHeader');
      const body = document.getElementById('modalBody');
      const badgeClass = !p.is_active ? 'badge-inactive' : (p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard'));
      const sBadge = p.status_badge || (p.is_active ? 'Активен' : 'Зал славы');
      const vkLink = p.vk_domain ? `https://vk.ru/${p.vk_domain}` : (p.vk_id ? `https://vk.ru/id${p.vk_id}` : null);

      header.innerHTML = `
        <img src="${p.avatar}" class="modal-avatar-big" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
        <div class="modal-title-box">
          <h2>${p.player}</h2>
          ${p.vk_name && p.vk_name !== p.player ? `
            <div style="font-size: 13px; color: #94a3b8; font-weight: 600; margin-top: 2px;">
              ВКонтакте: ${p.vk_name}
            </div>
          ` : ''}
          ${p.quote ? `
            <div style="font-size: 12px; color: #f8fafc; font-style: italic; margin-top: 6px; background: rgba(0,0,0,0.4); border-left: 3px solid var(--nes-gold); padding: 6px 10px; border-radius: 2px; line-height: 1.4; max-width: 650px; white-space: pre-line;">
              «${p.quote}»
            </div>
          ` : ''}
          
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 8px;">
            <span class="league-badge ${badgeClass}">${p.league} лига</span>
            <span style="font-size: 12px; font-weight: 800; color: ${p.is_active ? '#22c55e' : '#cbd5e1'};">● ${sBadge}</span>
            ${p.medals && (p.medals.gold + p.medals.silver + p.medals.bronze) > 0 ? `
              <span style="font-size: 11px; font-weight: 800; background: rgba(255, 183, 3, 0.15); border: 1px solid var(--nes-gold); color: #fff; padding: 2px 8px; border-radius: 3px;">
                🏆 ${p.medals.gold}🥇 ${p.medals.silver}🥈 ${p.medals.bronze}🥉
              </span>
            ` : ''}
            ${vkLink ? `
              <a href="${vkLink}" target="_blank" class="vk-btn" title="Перейти на страницу ${p.vk_name || p.player} ВКонтакте">
                <svg viewBox="0 0 24 24"><path d="M13.162 18.994c.609 0 .858-.406.851-.915-.072-1.747.785-2.28 1.488-2.28.618 0 1.344.428 1.84 1.157.734 1.077 1.258 2.038 2.378 2.038h2.096c1.196 0 1.776-.566 1.442-1.637-.367-1.182-1.603-2.678-2.327-3.486-.554-.62-1.127-1.185-.758-2.02.478-1.076 1.947-3.212 2.27-4.472.167-.655-.178-1.077-.92-1.077h-2.122c-.663 0-.964.332-1.151.78-.445 1.066-1.57 3.327-2.247 3.993-.342.338-.598.24-.76-.085-.298-.596-.341-1.688-.341-2.585 0-2.316.357-3.327-.723-3.582-.437-.103-.984-.132-1.792-.132-1.644 0-2.73.045-3.385.733-.257.27-.37.604-.15.632.493.064.935.318 1.054.945.362 1.905.176 3.655-.66 4.31-.383.298-.828.188-1.156-.214-.943-1.156-1.89-3.39-2.518-5.011-.194-.502-.519-.884-1.139-.884H2.477c-.779 0-.946.368-.946.779 0 .73.945 4.354 4.394 9.176 2.302 3.228 5.568 4.976 8.528 4.976z"/></svg>
                <span>${p.vk_name && p.vk_name !== p.player ? p.vk_name : 'Профиль ВКонтакте'} ↗</span>
              </a>
            ` : ''}
          </div>

          <!-- Dossier Cards Row -->
          <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px;">
            ${p.kryptonite ? `
              <div style="background: rgba(220, 38, 38, 0.15); border: 1px solid #ef4444; padding: 4px 8px; border-radius: 2px; font-size: 11px; cursor: pointer;" onclick="openPlayerModal('${p.kryptonite.name}')" title="Худший процент побед при 3+ матчах">
                <span style="color: #fca5a5; font-weight: 700;">☠️ Криптонит:</span> <strong>${p.kryptonite.name}</strong> <span style="color: #fca5a5;">(${p.kryptonite.wr}%)</span>
              </div>
            ` : ''}
            ${p.favorite_client ? `
              <div style="background: rgba(34, 197, 94, 0.15); border: 1px solid #22c55e; padding: 4px 8px; border-radius: 2px; font-size: 11px; cursor: pointer;" onclick="openPlayerModal('${p.favorite_client.name}')" title="Лучший процент побед при 3+ матчах">
                <span style="color: #86efac; font-weight: 700;">🎯 Клиент:</span> <strong>${p.favorite_client.name}</strong> <span style="color: #86efac;">(${p.favorite_client.wr}%)</span>
              </div>
            ` : ''}
            ${p.spectacle > 0 ? `
              <div style="background: rgba(0, 229, 255, 0.1); border: 1px solid var(--nes-cyan); padding: 4px 8px; border-radius: 2px; font-size: 11px;">
                <span style="color: var(--nes-cyan); font-weight: 700;">🌪️ Зрелищность:</span> <strong>${p.spectacle}</strong> гол/матч
              </div>
            ` : ''}
          </div>
        </div>
      `;

      // Match categories breakdown
      const mHistory = p.match_history || [];
      const catCounts = {
        all: mHistory.length,
        season: mHistory.filter(m => m.category === 'season').length,
        team: mHistory.filter(m => m.category === 'team').length,
        club: mHistory.filter(m => m.category === 'club').length,
        penalty: mHistory.filter(m => m.category === 'penalty').length,
        special: mHistory.filter(m => m.category === 'special' || m.category === 'blitz' || m.category === 'youth').length,
      };

      const filterButtonsHtml = `
        <div class="modal-match-filters" style="display: flex; gap: 6px; flex-wrap: wrap; margin: 12px 0 14px 0;">
          <button class="filter-btn active" onclick="filterPlayerModalMatches('all', this)">⚽ Все турниры (${catCounts.all})</button>
          ${catCounts.season > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('season', this)">🏆 Регулярные сезоны 1–9 (${catCounts.season})</button>` : ''}
          ${catCounts.team > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('team', this)">👥 Командные 2х2 (${catCounts.team})</button>` : ''}
          ${catCounts.club > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('club', this)">🏖️ Клубные & Межсезонье (${catCounts.club})</button>` : ''}
          ${catCounts.penalty > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('penalty', this)">🥅 Пенальти (${catCounts.penalty})</button>` : ''}
          ${catCounts.special > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('special', this)">⚡ Блицы & Соло (${catCounts.special})</button>` : ''}
        </div>
      `;

      const matchesRows = mHistory.map(m => {
        const resClass = m.result === 'ПОБЕДА' ? 'res-win' : (m.result === 'ПОРАЖЕНИЕ' ? 'res-loss' : 'res-draw');
        const oppObj = DATA.profiles.find(x => x.player.toLowerCase() === m.opponent.toLowerCase());
        const oppAvatar = oppObj ? oppObj.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.opponent}`;

        let catClass = 'badge-premier';
        if (m.category === 'team') catClass = 'badge-middle';
        else if (m.category === 'club') catClass = 'tag-offseason';
        else if (m.category === 'penalty') catClass = 'tag-penalty';
        else if (m.category === 'special' || m.category === 'blitz') catClass = 'tag-blitz';

        const isWin = m.score_for > m.score_against;
        const isLoss = m.score_for < m.score_against;

        return `
          <div class="match-history-row" data-cat="${m.category || 'season'}">
            <!-- Tournament Info & Stage -->
            <div class="mhr-meta">
              <span class="mhr-badge ${catClass}" title="${m.tournament || m.season}">
                ${m.cat_label || m.season}
              </span>
              <span class="mhr-stage">
                ${m.stage || m.tour || ''}
              </span>
            </div>

            <!-- Result Badge -->
            <div class="mhr-result">
              <span class="res-badge ${resClass}" style="${m.is_technical ? 'background: rgba(239, 68, 68, 0.25); border: 1px solid #ef4444; color: #fca5a5;' : ''}">${m.result}</span>
            </div>

            <!-- Face-to-Face Scoreboard -->
            <div class="mhr-duel">
              <!-- Home Player -->
              <div class="mhr-player mhr-home">
                <span class="mhr-name ${isWin ? 'mhr-winner' : ''}">${p.player}${m.partner ? ` <small style="color: #94a3b8;">& ${m.partner}</small>` : ''}</span>
                <img src="${p.avatar}" class="mhr-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
              </div>

              <!-- Score Box -->
              <div class="mhr-score-box">
                <span class="mhr-score-num ${isWin ? 'mhr-score-win' : (isLoss ? 'mhr-score-loss' : '')}">${m.score_for}</span>
                <span class="mhr-score-divider">:</span>
                <span class="mhr-score-num ${isLoss ? 'mhr-score-win' : (isWin ? 'mhr-score-loss' : '')}">${m.score_against}</span>
                ${m.pk ? '<span class="ot-tag ot-purple" title="Пенальти">ПЕН</span>' : (m.ot ? '<span class="ot-tag ot-gold" title="Овертайм">ОТ</span>' : '')}
              </div>

              <!-- Away Opponent -->
              <div class="mhr-player mhr-away" onclick="openPlayerModal('${m.opponent}')" title="Открыть профиль ${m.opponent}">
                <img src="${oppAvatar}" class="mhr-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.opponent}'">
                <span class="mhr-name ${isLoss ? 'mhr-winner' : ''}">${m.opponent}</span>
              </div>
            </div>
          </div>
        `;
      }).join('');

      // Calculate top opponents for this player
      const oppMap = {};
      mHistory.forEach(m => {
        if (m.is_technical) return;
        const oppName = m.opponent;
        if (!oppName) return;
        if (!oppMap[oppName]) {
          oppMap[oppName] = { name: oppName, matches: 0, wins: 0, losses: 0, draws: 0, gf: 0, ga: 0 };
        }
        oppMap[oppName].matches += 1;
        oppMap[oppName].gf += m.score_for;
        oppMap[oppName].ga += m.score_against;
        if (m.result === 'ПОБЕДА') oppMap[oppName].wins += 1;
        else if (m.result === 'ПОРАЖЕНИЕ') oppMap[oppName].losses += 1;
        else oppMap[oppName].draws += 1;
      });

      const topOpponents = Object.values(oppMap).sort((a, b) => b.matches - a.matches).slice(0, 6);
      const topOppHtml = topOpponents.map(opp => {
        const oppProf = DATA.profiles.find(x => x.player.toLowerCase() === opp.name.toLowerCase());
        const oppAv = oppProf ? oppProf.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${opp.name}`;
        return `
          <div style="background: rgba(10, 27, 45, 0.8); border: 1px solid rgba(255,255,255,0.25); padding: 8px 12px; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="openPlayerModal('${opp.name}')" title="Открыть анкету ${opp.name}">
              <img src="${oppAv}" style="width: 28px; height: 28px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${opp.name}'">
              <span style="font-weight: 700; font-size: 13px; color: #fff;">${opp.name}</span>
            </div>
            <div style="font-size: 12px; text-align: right;">
              <span style="color: var(--nes-green); font-weight: 800;">${opp.wins}В</span>
              <span style="color: #94a3b8;"> - </span>
              <span style="color: var(--nes-red); font-weight: 800;">${opp.losses}П</span>
              <span style="color: #94a3b8; font-size: 11px; margin-left: 4px;">(${opp.matches} игр)</span>
            </div>
          </div>
        `;
      }).join('');

      body.innerHTML = `
        ${!p.is_active && p.hof_reason ? `
          <div style="background: rgba(255, 183, 3, 0.12); border: 2px solid var(--nes-gold); padding: 14px 18px; margin-bottom: 20px; box-shadow: 3px 3px 0px #000;">
            <div style="display: flex; align-items: center; gap: 8px; font-family: var(--font-title); font-size: 13px; color: var(--nes-gold); margin-bottom: 6px;">
              <span>🏛️</span> В ЗАЛЕ СЛАВЫ NEKKETSU LEAGUE &bull; ОБОСНОВАНИЕ И ЗАСЛУГИ:
            </div>
            <div style="font-size: 14px; color: #fff; line-height: 1.5;">
              ${p.hof_reason}
            </div>
          </div>
        ` : ''}
        <div class="metric-tiles">
          <div class="metric-tile">
            <div class="l">Текущий рейтинг</div>
            <div class="num" style="color: var(--nes-gold);">${p.active_elo.toFixed(1)}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Рекорд рейтинга</div>
            <div class="num">${p.peak_elo.toFixed(1)}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Штраф за простой</div>
            <div class="num" style="color: ${p.decay_penalty > 0 ? 'var(--nes-red)' : 'var(--nes-green)'};">-${p.decay_penalty} очков</div>
          </div>
          <div class="metric-tile">
            <div class="l">Всего матчей</div>
            <div class="num">${p.matches}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Победы / Поражения</div>
            <div class="num">${p.wins} из ${p.matches}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Процент побед</div>
            <div class="num" style="color: var(--nes-green);">${p.win_rate}%</div>
          </div>
          <div class="metric-tile">
            <div class="l">Забито / Пропущено</div>
            <div class="num">${p.goals_for} : ${p.goals_against}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Игры всухую (на ноль)</div>
            <div class="num">${p.clean_sheets}</div>
          </div>
        </div>

        <div class="block-header">🎯 Как побеждает игрок (распределение по времени матча)</div>
        <div style="background: #0a1b2d; border: 2px solid rgba(255,255,255,0.25); padding: 14px; margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
            <span>В основное время: <strong style="color: var(--nes-cyan);">${p.reg_wins} побед</strong></span>
            <span>В овертаймах: <strong style="color: var(--nes-gold);">${p.ot_wins} побед</strong></span>
            <span>По пенальти: <strong style="color: #c084fc;">${p.pk_wins} побед</strong></span>
            <span>Побед в овертаймах/пенальти: <strong style="color: var(--nes-green);">${p.clutch_win_rate}%</strong> (${p.clutch_wins} из ${p.clutch_total})</span>
          </div>
          <div style="display: flex; height: 16px; border: 1px solid #fff; background: #000;">
            <div style="width: ${p.wins > 0 ? (p.reg_wins/p.wins*100) : 0}%; background: var(--nes-cyan);" title="Основное время"></div>
            <div style="width: ${p.wins > 0 ? (p.ot_wins/p.wins*100) : 0}%; background: var(--nes-gold);" title="Овертаймы"></div>
            <div style="width: ${p.wins > 0 ? (p.pk_wins/p.wins*100) : 0}%; background: #c084fc;" title="Пенальти"></div>
          </div>
        </div>

        ${topOppHtml ? `
          <div class="block-header">⚔️ Главные соперники игрока (Личные встречи)</div>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 8px; margin-bottom: 20px;">
            ${topOppHtml}
          </div>
        ` : ''}

        <div class="block-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
          <span>📜 Официальные протоколы матчей игрока (${mHistory.length} игр в базе)</span>
        </div>
        ${filterButtonsHtml}
        <div id="modalMatchesContainer">
          ${matchesRows || '<p style="color: #94a3b8; padding: 12px;">Протоколы матчей отсутствуют</p>'}
        </div>
      `;

      document.getElementById('playerModal').classList.add('active');
    }

    function filterPlayerModalMatches(cat, btn) {
      document.querySelectorAll('.modal-match-filters .filter-btn').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');

      const rows = document.querySelectorAll('#modalMatchesContainer .match-history-row[data-cat]');
      rows.forEach(r => {
        const rCat = r.getAttribute('data-cat');
        if (cat === 'all') {
          r.style.display = 'flex';
        } else if (cat === 'special') {
          r.style.display = (rCat === 'special' || rCat === 'blitz' || rCat === 'youth') ? 'flex' : 'none';
        } else {
          r.style.display = (rCat === cat) ? 'flex' : 'none';
        }
      });
    }

    
    // ==============================================================================
    // MODAL HELPERS & PROTOCOL VIEWER (ВК ОТЧЁТЫ И ВИДЕО)
    // ==============================================================================
    const PROTOCOLS_STORE = {};
    let protocolNextId = 1;

    function registerProtocol(title, text, date, page, url) {
      const id = 'proto_' + (protocolNextId++);
      PROTOCOLS_STORE[id] = { title, text, date, page, url };
      return id;
    }

    function openProtocolModalById(id) {
      const p = PROTOCOLS_STORE[id];
      if (!p) return;
      const modal = document.getElementById('protocolModal');
      if (!modal) return;
      const t = document.getElementById('protocolModalTitle');
      const d = document.getElementById('protocolModalDate');
      const pg = document.getElementById('protocolModalPage');
      const txt = document.getElementById('protocolModalText');
      const vk = document.getElementById('protocolModalVkLink');

      if (t) t.textContent = p.title || 'Протокол матча из ВК';
      if (d) d.textContent = p.date ? `📅 ${p.date}` : '';
      if (pg) pg.textContent = p.page ? `📄 Лист: ${p.page}` : '';
      if (txt) txt.textContent = p.text || 'Текст отчёта отсутствует.';
      if (vk) {
        if (p.url) {
          vk.href = p.url;
          vk.style.display = 'inline-flex';
        } else {
          vk.style.display = 'none';
        }
      }
      modal.style.display = 'flex';
    }

    function closeProtocolModal(e) {
      if (e && e.target && e.target !== e.currentTarget && !e.target.classList.contains('modal-close')) return;
      const modal = document.getElementById('protocolModal');
      if (modal) modal.style.display = 'none';
    }

    function openVideoModal(url, title = 'Запись матча') {
      const modal = document.getElementById('videoModal');
      const iframe = document.getElementById('videoPlayerIframe');
      const titleEl = document.getElementById('videoModalTitle');
      const extLink = document.getElementById('videoModalExternalLink');
      if (!modal || !iframe) return;

      if (titleEl) titleEl.textContent = title;
      if (extLink) extLink.href = url;

      let embedUrl = url;
      if (url.includes('youtube.com/watch?v=' || url.includes('youtube.com/watch?'))) {
        const m = url.match(/v=([a-zA-Z0-9_-]+)/);
        if (m) embedUrl = `https://www.youtube.com/embed/${m[1]}?autoplay=1`;
      } else if (url.includes('youtu.be/')) {
        const m = url.match(/youtu\.be\/([a-zA-Z0-9_-]+)/);
        if (m) embedUrl = `https://www.youtube.com/embed/${m[1]}?autoplay=1`;
      } else if (url.includes('vk.com/video') || url.includes('vk.ru/video')) {
        const m = url.match(/video(-?\d+)_(\d+)/);
        if (m) embedUrl = `https://vk.ru/video_ext.php?oid=${m[1]}&id=${m[2]}&hash=`;
      }

      iframe.src = embedUrl;
      modal.style.display = 'flex';
    }

    function closeVideoModal(e) {
      if (e && e.target && e.target !== e.currentTarget && !e.target.classList.contains('modal-close')) return;
      const modal = document.getElementById('videoModal');
      const iframe = document.getElementById('videoPlayerIframe');
      if (iframe) iframe.src = '';
      if (modal) modal.style.display = 'none';
    }

    function closePlayerModal() {
      document.getElementById('playerModal').classList.remove('active');
      window.location.hash = '#/leaderboard';
    }

    // Seasons Module

    function renderSeasonsBar() {

      const bar = document.getElementById('seasonsBar');

      if (!bar) return;

      bar.innerHTML = DATA.seasons.map(s => `

        <button class="filter-btn season-tab-btn ${s.id === selectedSeasonId ? 'active' : ''}" onclick="selectSeason('${s.id}')">

          ${s.name} (${s.year} г.)

        </button>

      `).join('');

    }



    function selectSeason(sId) {

      selectedSeasonId = sId;

      seasonPlayerFilter = 'all';

      seasonLeagueFilter = 'all';

      renderSeasonsBar();

      renderSeasonDetails(sId);

    }



    function switchSeasonSubTab(st) {

      seasonSubTab = st;

      renderSeasonDetails(selectedSeasonId);

    }



    function setPlayoffViewMode(mode) {

      playoffViewMode = mode;

      renderSeasonDetails(selectedSeasonId);

    }

    function setTeamPlayoffViewMode(mode) {
      teamPlayoffViewMode = mode;
      renderTeamTournamentDetails();
    }

    function setSpecialPlayoffViewMode(mode) {
      specialPlayoffViewMode = mode;
      renderSpecialTournamentDetails();
    }



    function filterSeasonPlayer(pName) {

      seasonPlayerFilter = pName;

      renderSeasonDetails(selectedSeasonId);

    }



    function filterSeasonLeague(leg) {

      seasonLeagueFilter = leg;

      renderSeasonDetails(selectedSeasonId);

    }



    function getPlayerSeasonLeague(sId, playerName) {

      const pLow = playerName.toLowerCase().trim();

      const roster = (DATA.season_rosters && (DATA.season_rosters[sId] || DATA.season_rosters[String(sId)])) || {};

      for (const [leagueName, players] of Object.entries(roster)) {

        if (players.some(x => x.toLowerCase().trim() === pLow)) {

          return leagueName;

        }

      }

      const s = DATA.seasons && DATA.seasons.find(x => String(x.id) === String(sId));

      if (s && s.matches) {

        const mWithLeague = s.matches.find(m => (m.p1.toLowerCase() === pLow || m.p2.toLowerCase() === pLow) && m.league && !m.league.toLowerCase().includes('кубок'));

        if (mWithLeague && mWithLeague.league) return mWithLeague.league;

      }

      const prof = DATA.profiles.find(x => x.player.toLowerCase() === pLow);

      if (prof) {

        if (prof.league === 'Высшая') return 'Высшая лига';

        if (prof.league === 'Средняя') return 'Средняя лига';

        if (prof.league === 'Дворовая') return 'Дворовая лига';

      }

      return 'Высшая лига';

    }



    function renderSeasonDetails(sId) {

      const s = DATA.seasons.find(x => String(x.id) === String(sId));

      if (!s) return;



      const card = document.getElementById('seasonDetails');

      if (!card) return;



      // Calculate participant stats for this season

      const partMap = {};

      (s.matches || []).forEach(m => {

        [m.p1, m.p2].forEach(pName => {

          if (!pName) return;

          if (!partMap[pName]) {

            const prof = DATA.profiles.find(x => x.player.toLowerCase() === pName.toLowerCase());

            partMap[pName] = {

              name: pName,

              avatar: prof ? prof.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pName}`,

              matches: 0,

              wins: 0,

              losses: 0,

              goals_for: 0,

              goals_against: 0

            };

          }

        });



        if (partMap[m.p1] && partMap[m.p2]) {

          partMap[m.p1].matches += 1;

          partMap[m.p2].matches += 1;

          partMap[m.p1].goals_for += m.s1;

          partMap[m.p1].goals_against += m.s2;

          partMap[m.p2].goals_for += m.s2;

          partMap[m.p2].goals_against += m.s1;



          if (m.s1 > m.s2) {

            partMap[m.p1].wins += 1;

            partMap[m.p2].losses += 1;

          } else if (m.s2 > m.s1) {

            partMap[m.p2].wins += 1;

            partMap[m.p1].losses += 1;

          }

        }

      });



      const participantsList = Object.values(partMap).sort((a, b) => {

        if (b.wins !== a.wins) return b.wins - a.wins;

        const gdB = b.goals_for - b.goals_against;

        const gdA = a.goals_for - a.goals_against;

        if (gdB !== gdA) return gdB - gdA;

        return b.matches - a.matches;

      });



      // Group participants by league

      const leagueGroups = {};

      participantsList.forEach(p => {

        const leg = getPlayerSeasonLeague(sId, p.name);

        if (!leagueGroups[leg]) leagueGroups[leg] = [];

        leagueGroups[leg].push(p);

      });



      const leagueOrder = ["Высшая лига", "Высшая (Единая) лига", "Средняя лига", "Младшая лига", "Дворовая лига"];

      const sortedLeagues = Object.keys(leagueGroups).sort((a, b) => {

        const idxA = leagueOrder.indexOf(a) !== -1 ? leagueOrder.indexOf(a) : 99;

        const idxB = leagueOrder.indexOf(b) !== -1 ? leagueOrder.indexOf(b) : 99;

        return idxA - idxB;

      });



      // Master players chips

      const masterSeasonPlayers = participantsList.filter(p => DATA.profiles.some(x => x.player.toLowerCase() === p.name.toLowerCase()));

      const playersChips = masterSeasonPlayers.map(p => `

        <span class="player-chip-link" onclick="openPlayerModal('${p.name}')" title="Открыть анкету ${p.name}">

          <img src="${p.avatar}" style="width: 16px; height: 16px; border-radius: 2px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.name}'">

          ${p.name}

        </span>

      `).join('');



      // Build Sub-Tab content

      let subContentHtml = '';



      // 1. ALL MATCHES SUB-TAB

      if (seasonSubTab === 'matches') {

        let filteredMatches = s.matches || [];

        if (seasonPlayerFilter && seasonPlayerFilter !== 'all') {

          filteredMatches = filteredMatches.filter(m =>

            m.p1.toLowerCase() === seasonPlayerFilter.toLowerCase() ||

            m.p2.toLowerCase() === seasonPlayerFilter.toLowerCase()

          );

        }

        if (seasonLeagueFilter && seasonLeagueFilter !== 'all') {

          filteredMatches = filteredMatches.filter(m => m.league === seasonLeagueFilter);

        }



        const playerOptions = participantsList.map(p => `

          <option value="${p.name}" ${seasonPlayerFilter === p.name ? 'selected' : ''}>${p.name}</option>

        `).join('');



        const leagueOrder = ["Высшая лига", "Высшая (Единая) лига", "Средняя лига", "Младшая лига", "Дворовая лига", "Кубок лиг"];

        const matchLeagues = Array.from(new Set((s.matches || []).map(m => m.league).filter(Boolean)));

        matchLeagues.sort((a, b) => {

          const idxA = leagueOrder.indexOf(a) !== -1 ? leagueOrder.indexOf(a) : 99;

          const idxB = leagueOrder.indexOf(b) !== -1 ? leagueOrder.indexOf(b) : 99;

          return idxA - idxB;

        });



        const leagueOptions = matchLeagues.map(l => `

          <option value="${l}" ${seasonLeagueFilter === l ? 'selected' : ''}>${l}</option>

        `).join('');



        const matchesListHtml = filteredMatches.length > 0 ? filteredMatches.map(m => {

          const p1Low = (m.p1 || '').toLowerCase();

          const p2Low = (m.p2 || '').toLowerCase();

          const prof1 = DATA.profiles.find(x => x.player.toLowerCase() === p1Low);

          const prof2 = DATA.profiles.find(x => x.player.toLowerCase() === p2Low);

          const av1 = prof1 ? prof1.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.p1}`;

          const av2 = prof2 ? prof2.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.p2}`;

          const isP1Win = m.s1 > m.s2;

          const isP2Win = m.s2 > m.s1;

          const sMatchTitle = `${m.p1} vs ${m.p2} (${m.s1}:${m.s2}) • ${s.name}`;

          const protoId = m.vk_url ? registerProtocol(sMatchTitle, m.vk_text, m.vk_date, m.vk_page, m.vk_url) : '';



          return `

            <div class="h2h-match-item" style="padding: 12px 16px; margin-bottom: 8px;">

              <div style="display: flex; align-items: center; gap: 8px; flex: 1.2; min-width: 140px;">

                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--nes-gold); font-weight: 800; min-width: 60px;">

                  ${m.tour || 'Матч'}

                </span>

                <span class="league-badge ${m.league && m.league.includes('Высшая') ? 'badge-premier' : (m.league && m.league.includes('Средняя') ? 'badge-middle' : (m.league && m.league.includes('Кубок') ? 'badge-cup' : 'badge-yard'))}" style="font-size: 10px; padding: 2px 6px;">

                  ${m.league || 'Регулярка'}

                </span>

              </div>

              <div style="display: flex; align-items: center; justify-content: center; gap: 14px; flex: 2; flex-wrap: wrap;">

                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p1}')">

                  <span style="font-family: var(--font-title); font-size: 14px; ${isP1Win ? 'color: var(--nes-gold); font-weight: 800;' : 'color: #fff;'}; text-align: right;">${m.p1}</span>

                  <img src="${av1}" style="width: 24px; height: 24px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.p1}'">

                </div>

                <div class="score-badge" style="font-size: 15px; padding: 5px 14px; letter-spacing: 1px; font-weight: 900; color: var(--nes-cyan); min-width: 80px; text-align: center;">

                  ${m.s1} : ${m.s2}

                  ${m.is_technical ? '<span class="ot-tag" style="background: rgba(239, 68, 68, 0.25); border: 1px solid #ef4444; color: #fca5a5; font-size: 10px; padding: 2px 6px; font-weight: 800;" title="Техническое поражение (снят с турнира)">⚡ ТП (СНЯТ)</span>' : (m.pk ? '<span class="ot-tag ot-purple">Пенальти</span>' : (m.ot ? '<span class="ot-tag ot-gold">ОТ</span>' : ''))}

                </div>

                <div style="display: flex; align-items: center; justify-content: flex-start; gap: 8px; flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p2}')">

                  <img src="${av2}" style="width: 24px; height: 24px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.p2}'">

                  <span style="font-family: var(--font-title); font-size: 14px; ${isP2Win ? 'color: var(--nes-gold); font-weight: 800;' : 'color: #cbd5e1;'}; text-align: left;">${m.p2}</span>

                </div>

              </div>

              ${(m.vk_url || m.video_url) ? `

                <div style="display: flex; gap: 6px; align-items: center; justify-content: flex-end; min-width: 140px; margin-left: auto;">

                  ${m.vk_url ? `

                    <button type="button" class="source-btn-vk" onclick="event.stopPropagation(); openProtocolModalById('${protoId}')" title="Посмотреть текст отчёта матча из ВК">

                      💬 ВК

                    </button>

                  ` : ''}

                  ${m.video_url ? (

                    (m.video_url.includes('youtube.com') || m.video_url.includes('youtu.be')) ? `

                      <a href="${m.video_url}" target="_blank" rel="noopener" class="source-btn-video" title="Смотреть на YouTube в новой вкладке">

                        🎬 YouTube ↗

                      </a>

                    ` : `

                      <button type="button" class="source-btn-video" onclick="event.stopPropagation(); openVideoModal('${m.video_url}', '${sMatchTitle.replace(/'/g, "\\'")}')" title="Смотреть в плеере на сайте">

                        🎬 Видео

                      </button>

                    `

                  ) : ''}

                </div>

              ` : '<div style="min-width: 140px; margin-left: auto;"></div>'}

            </div>

          `;

        }).join('') : `

          <div style="background: rgba(0,0,0,0.4); border: 2px dashed #94a3b8; padding: 32px; text-align: center; color: #cbd5e1;">

            Матчи по выбранному фильтру не найдены.

          </div>

        `;



        subContentHtml = `

          <div style="margin-top: 16px;">

            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px;">

              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-cyan);">

                📋 СЫГРАННЫЕ МАТЧИ (${filteredMatches.length} из ${(s.matches || []).length}):

              </div>

              <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">

                ${matchLeagues.length > 1 ? `

                  <div style="display: flex; align-items: center; gap: 6px;">

                    <span style="font-size: 12px; color: #94a3b8; font-weight: 700;">Лига:</span>

                    <select class="clean-search" style="padding: 4px 10px; font-size: 12px;" onchange="filterSeasonLeague(this.value)">

                      <option value="all" ${seasonLeagueFilter === 'all' ? 'selected' : ''}>▶ Все лиги (${matchLeagues.length})</option>

                      ${leagueOptions}

                    </select>

                  </div>

                ` : ''}

                <div style="display: flex; align-items: center; gap: 6px;">

                  <span style="font-size: 12px; color: #94a3b8; font-weight: 700;">Игрок:</span>

                  <select class="clean-search" style="padding: 4px 10px; font-size: 12px;" onchange="filterSeasonPlayer(this.value)">

                    <option value="all" ${seasonPlayerFilter === 'all' ? 'selected' : ''}>▶ Все участники (${participantsList.length})</option>

                    ${playerOptions}

                  </select>

                </div>

              </div>

            </div>

            <div>

              ${matchesListHtml}

            </div>

          </div>

        `;

      }



      // 2. TABLES SUB-TAB

      else if (seasonSubTab === 'tables') {

        let tablesHtml = '<div style="display: flex; flex-direction: column; gap: 20px;">';

        // Exclude Cup / Playoff from regular round-robin standings tables
        const regularLeagues = sortedLeagues.filter(l => !l.toLowerCase().includes('кубок'));

        regularLeagues.forEach(leg => {

          const legMatches = (s.matches || []).filter(m => (m.league || '').toLowerCase() === leg.toLowerCase());

          const rosterPlayers = (DATA.season_rosters && (DATA.season_rosters[sId] || DATA.season_rosters[String(sId)]) && (DATA.season_rosters[sId] || DATA.season_rosters[String(sId)])[leg]) || [];

          const playerSet = new Set(rosterPlayers);

          legMatches.forEach(m => {

            if (m.p1) playerSet.add(m.p1);

            if (m.p2) playerSet.add(m.p2);

          });



          const pStats = Array.from(playerSet).map(pName => {

            const prof = DATA.profiles.find(x => x.player.toLowerCase() === pName.toLowerCase());

            const stat = {

              name: pName,

              avatar: prof ? prof.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pName}`,

              matches: 0, wins: 0, losses: 0, goals_for: 0, goals_against: 0

            };

            const pLow = pName.toLowerCase();

            legMatches.forEach(m => {

              const p1Low = (m.p1 || '').toLowerCase();

              const p2Low = (m.p2 || '').toLowerCase();

              if (p1Low === pLow) {

                stat.matches += 1;

                stat.goals_for += m.s1;

                stat.goals_against += m.s2;

                if (m.s1 > m.s2) stat.wins += 1;

                else if (m.s1 < m.s2) stat.losses += 1;

              } else if (p2Low === pLow) {

                stat.matches += 1;

                stat.goals_for += m.s2;

                stat.goals_against += m.s1;

                if (m.s2 > m.s1) stat.wins += 1;

                else if (m.s2 < m.s1) stat.losses += 1;

              }

            });

            return stat;

          });



          // Sort table by wins, goal diff, goals for, matches
          pStats.sort((a, b) => {

            if (b.wins !== a.wins) return b.wins - a.wins;

            const gdB = b.goals_for - b.goals_against;

            const gdA = a.goals_for - a.goals_against;

            if (gdB !== gdA) return gdB - gdA;

            if (b.goals_for !== a.goals_for) return b.goals_for - a.goals_for;

            return b.matches - a.matches;

          });



          const badgeClass = leg.includes('Высшая') ? 'badge-premier' : (leg.includes('Средняя') ? 'badge-middle' : 'badge-yard');

          const icon = leg.includes('Высшая') ? '🥇 ' : (leg.includes('Средняя') ? '🥈 ' : (leg.includes('Младшая') ? '⚡ ' : '🥉 '));



          tablesHtml += `

            <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.15); padding: 16px;">

              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff;">

                  <span class="league-badge ${badgeClass}" style="margin-right: 8px;">${icon}${leg}</span>

                  (${pStats.length} участников)

                </div>

              </div>

              <table class="special-table">

                <thead>

                  <tr>

                    <th>#</th>

                    <th>Игрок</th>

                    <th>Матчей</th>

                    <th>Побед</th>

                    <th>Пораж.</th>

                    <th>Голы</th>

                    <th>+/-</th>

                    <th>Профиль</th>

                  </tr>

                </thead>

                <tbody>

                  ${pStats.map((p, idx) => {

                    const gd = p.goals_for - p.goals_against;

                    const gdStr = gd > 0 ? `+${gd}` : `${gd}`;

                    const gdColor = gd > 0 ? 'var(--nes-cyan)' : (gd < 0 ? '#f87171' : '#94a3b8');

                    const rankColor = idx === 0 ? 'var(--nes-gold)' : (idx === 1 ? '#cbd5e1' : (idx === 2 ? '#d97706' : '#94a3b8'));



                    return `

                      <tr>

                        <td style="font-weight: 800; color: ${rankColor}; font-family: var(--font-mono);">${idx + 1}</td>

                        <td>

                          <div style="display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="openPlayerModal('${p.name}')">

                            <img src="${p.avatar}" style="width: 20px; height: 20px; border-radius: 2px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.name}'">

                            <span style="font-weight: 700; color: #fff;">${p.name}</span>

                          </div>

                        </td>

                        <td style="font-family: var(--font-mono);">${p.matches}</td>

                        <td style="font-family: var(--font-mono); color: var(--nes-green); font-weight: 800;">${p.wins}</td>

                        <td style="font-family: var(--font-mono); color: var(--nes-red); font-weight: 800;">${p.losses}</td>

                        <td style="font-family: var(--font-mono);">${p.goals_for}:${p.goals_against}</td>

                        <td style="font-family: var(--font-mono); color: ${gdColor};">${gdStr}</td>

                        <td>

                          <button class="part-prof-btn" onclick="openPlayerModal('${p.name}')" title="Открыть анкету игрока">↗</button>

                        </td>

                      </tr>

                    `;

                  }).join('')}

                </tbody>

              </table>

            </div>

          `;

        });

        tablesHtml += '</div>';



        subContentHtml = `

          <div style="margin-top: 16px;">

            <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold); margin-bottom: 12px;">

              🏆 ТУРНИРНЫЕ ТАБЛИЦЫ ДИВИЗИОНОВ:

            </div>

            ${tablesHtml}

          </div>

        `;

      }



      // 3. PLAYOFF SUB-TAB (INTERACTIVE TOURNAMENT BRACKET)

      else if (seasonSubTab === 'playoff') {

        const playoffMatches = (s.matches || []).filter(m => {

          const t = (m.tour || '').toLowerCase();

          const l = (m.league || '').toLowerCase();

          return t.includes('финал') || t.includes('1/') || t.includes('плей') || t.includes('playoff') || t.includes('кубок') || l.includes('кубок');

        });



        // Standard bracket round weighting

        const roundOrderDef = [

          { key: '1/16', label: '1/16 Финала', weight: 1 },

          { key: '1/8', label: '1/8 Финала', weight: 2 },

          { key: '1/4', label: '1/4 Финала', weight: 3 },

          { key: '1/2', label: 'Полуфинал', weight: 4 },

          { key: '3', label: 'За 3-е место', weight: 5 },

          { key: 'финал', label: 'Гранд-Финал', weight: 6 }

        ];



        function getRoundDef(rName) {

          const rLow = (rName || '').toLowerCase();

          for (const ro of roundOrderDef) {

            if (ro.key === 'финал') {

              if (rLow.includes('финал') && !rLow.includes('1/16') && !rLow.includes('1/8') && !rLow.includes('1/4') && !rLow.includes('1/2') && !rLow.includes('3')) {

                return ro;

              }

            } else if (rLow.includes(ro.key)) {

              return ro;

            }

          }

          return { key: rName, label: rName || 'Плей-офф', weight: 99 };

        }



        // Group matches into rounds

        const roundMap = {};

        playoffMatches.forEach(m => {

          const rDef = getRoundDef(m.tour || m.stage);

          if (!roundMap[rDef.label]) {

            roundMap[rDef.label] = { def: rDef, matches: [] };

          }

          roundMap[rDef.label].matches.push(m);

        });



        const sortedRounds = Object.values(roundMap).sort((a, b) => a.def.weight - b.def.weight);



        // Determine Champion

        let championName = (s.podium && s.podium.champion) ? s.podium.champion : null;

        const finalRound = sortedRounds.find(r => r.def.key === 'финал');

        if (!championName && finalRound && finalRound.matches.length > 0) {

          const fMatches = finalRound.matches;

          const p1 = fMatches[0].p1;

          const p2 = fMatches[0].p2;

          let p1w = 0, p2w = 0;

          fMatches.forEach(g => {

            if ((g.p1 === p1 && g.s1 > g.s2) || (g.p2 === p1 && g.s2 > g.s1)) p1w++;

            else if ((g.p1 === p2 && g.s1 > g.s2) || (g.p2 === p2 && g.s2 > g.s1)) p2w++;

          });

          championName = p1w > p2w ? p1 : (p2w > p1w ? p2 : p1);

        }

        const champProf = championName ? DATA.profiles.find(x => x.player.toLowerCase() === championName.toLowerCase()) : null;

        const champAvatar = champProf ? champProf.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${championName || 'champ'}`;



        // 1. VISUAL BRACKET HTML

        let visualBracketHtml = '';

        if (sortedRounds.length > 0) {

          let roundsHtml = '';

          sortedRounds.forEach(r => {

            // Group matches in this round into matchups (pairs)

            const matchups = {};

            r.matches.forEach(m => {

              const pairKey = [m.p1, m.p2].sort().join('__VS__');

              if (!matchups[pairKey]) matchups[pairKey] = [];

              matchups[pairKey].push(m);

            });



            let matchupCardsHtml = '';

            Object.entries(matchups).forEach(([pKey, games]) => {

              const [pA, pB] = pKey.split('__VS__');

              let pAw = 0, pBw = 0;

              let pAg = 0, pBg = 0;

              games.forEach(g => {

                const sA = g.p1 === pA ? g.s1 : g.s2;

                const sB = g.p1 === pA ? g.s2 : g.s1;

                pAg += sA;

                pBg += sB;

                if (sA > sB) pAw++;

                else if (sB > sA) pBw++;

              });



              let isAWinner = false, isBWinner = false;

              if (games.length === 1) {

                isAWinner = pAg > pBg;

                isBWinner = pBg > pAg;

              } else {

                isAWinner = pAw > pBw;

                isBWinner = pBw > pAw;

              }



              const profA = DATA.profiles.find(x => x.player.toLowerCase() === pA.toLowerCase());

              const profB = DATA.profiles.find(x => x.player.toLowerCase() === pB.toLowerCase());

              const avA = profA ? profA.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pA}`;

              const avB = profB ? profB.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pB}`;



              const scoreA = games.length === 1 ? pAg : pAw;

              const scoreB = games.length === 1 ? pBg : pBw;

              const isFinal = r.def.key === 'финал';



              // Detailed chips for series matches

              let chipsHtml = '';

              if (games.length > 1) {

                chipsHtml = `<div class="bracket-series-games">` + games.map((g, gIdx) => {

                  const sMatchTitle = `${g.p1} vs ${g.p2} (${g.s1}:${g.s2}) • ${s.name}`;

                  const protoId = g.vk_url ? registerProtocol(sMatchTitle, g.vk_text, g.vk_date, g.vk_page, g.vk_url) : '';

                  const otTag = g.pk ? ' (Пен)' : (g.ot ? ' (ОТ)' : '');

                  const clickAttr = protoId ? `onclick="event.stopPropagation(); openProtocolModalById('${protoId}')" title="Открыть отчёт матча ВК"` : '';

                  return `<span class="bracket-chip" ${clickAttr}>И${gIdx+1}: ${g.s1}:${g.s2}${otTag}</span>`;

                }).join('') + `</div>`;

              } else if (games[0].vk_url || games[0].video_url) {

                const g = games[0];

                const sMatchTitle = `${g.p1} vs ${g.p2} (${g.s1}:${g.s2}) • ${s.name}`;

                const protoId = g.vk_url ? registerProtocol(sMatchTitle, g.vk_text, g.vk_date, g.vk_page, g.vk_url) : '';

                chipsHtml = `<div class="bracket-series-games" style="justify-content: flex-end;">`;

                if (protoId) {

                  chipsHtml += `<button type="button" class="source-btn-vk" style="font-size: 10px; padding: 2px 6px;" onclick="event.stopPropagation(); openProtocolModalById('${protoId}')">💬 ВК</button>`;

                }

                if (g.video_url) {

                  chipsHtml += `<button type="button" class="source-btn-video" style="font-size: 10px; padding: 2px 6px;" onclick="event.stopPropagation(); openVideoModal('${g.video_url}', '${sMatchTitle.replace(/'/g, "\'")}')">🎬 Видео</button>`;

                }

                chipsHtml += `</div>`;

              }



              const seriesLabel = games.length > 1 ? `СЕРИЯ ДО ${Math.max(pAw, pBw)} ПОБЕД (${games.length} игр)` : 'МАТЧ НА ВЫЛЕТ';



              matchupCardsHtml += `

                <div class="bracket-match-card ${isFinal ? 'is-final' : ''}" data-players="${pA.toLowerCase()},${pB.toLowerCase()}">

                  <div class="bracket-card-top">

                    <span>${seriesLabel}</span>

                    ${isFinal ? '<span style="color: var(--nes-gold);">🏆 ФИНАЛ</span>' : ''}

                  </div>

                  <div class="bracket-player-row ${isAWinner ? 'winner' : (isBWinner ? 'loser' : '')}" data-player="${pA}" onmouseenter="highlightPlayerBracketPath('${pA}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pA}')" title="Наведите или кликните, чтобы подсветить путь ${pA}">

                    <div class="bracket-p-info">

                      <img src="${avA}" class="bracket-p-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${pA}'">

                      <span class="bracket-p-name">${pA}</span>

                      ${isAWinner ? '<span style="font-size: 11px;">👑</span>' : ''}

                    </div>

                    <div class="bracket-score">${scoreA}</div>

                  </div>

                  <div class="bracket-player-row ${isBWinner ? 'winner' : (isAWinner ? 'loser' : '')}" data-player="${pB}" onmouseenter="highlightPlayerBracketPath('${pB}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pB}')" title="Наведите или кликните, чтобы подсветить путь ${pB}">

                    <div class="bracket-p-info">

                      <img src="${avB}" class="bracket-p-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${pB}'">

                      <span class="bracket-p-name">${pB}</span>

                      ${isBWinner ? '<span style="font-size: 11px;">👑</span>' : ''}

                    </div>

                    <div class="bracket-score">${scoreB}</div>

                  </div>

                  ${chipsHtml}

                </div>

              `;

            });



            roundsHtml += `

              <div class="bracket-round">

                <div class="bracket-round-header">${r.def.label} (${Object.keys(matchups).length})</div>

                <div class="bracket-matchups">

                  ${matchupCardsHtml}

                </div>

              </div>

            `;

          });



          // Champion Podium Card

          if (championName) {

            roundsHtml += `

              <div class="bracket-champion-round">

                <div class="bracket-round-header" style="border-color: var(--nes-gold); color: var(--nes-gold); box-shadow: 0 0 10px rgba(255,183,3,0.3);">🏆 ЧЕМПИОН</div>

                <div class="bracket-champion-box" data-player="${championName}">

                  <div style="font-size: 28px;">👑</div>

                  <img src="${champAvatar}" class="bracket-champ-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${championName}'">

                  <div class="bracket-champ-name" onclick="openPlayerModal('${championName}')">${championName}</div>

                  <div class="bracket-champ-sub">🥇 ОБЛАДАТЕЛЬ КУБКА</div>

                  <div style="font-size: 10px; color: var(--nes-cyan); margin-top: 4px; font-weight: 800;">${s.name}</div>

                </div>

              </div>

            `;

          }



          // Collect all unique participants in playoff
          const playoffParticipantSet = new Set();
          playoffMatches.forEach(m => {
            if (m.p1) playoffParticipantSet.add(m.p1);
            if (m.p2) playoffParticipantSet.add(m.p2);
          });
          const playoffParticipantsList = Array.from(playoffParticipantSet).sort();

          const playerPillsHtml = `
            <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 14px;">
              <span style="font-size: 11px; color: #94a3b8; font-weight: 700;">🔍 Сетка игрока:</span>
              <button type="button" class="bracket-player-pill" onclick="resetPlayerBracketPath()">Все пути</button>
              ${playoffParticipantsList.map(p => `
                <button type="button" class="bracket-player-pill" data-player="${p}" onmouseenter="highlightPlayerBracketPath('${p}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${p}')">
                  ${p}
                </button>
              `).join('')}
            </div>
          `;

          visualBracketHtml = `
            <div style="margin-top: 10px;">
              ${playerPillsHtml}
              <div id="bracketPathBanner" class="bracket-path-banner"><span style="color: #94a3b8;">💡 Наведите на любого игрока или нажмите, чтобы проследить его путь по сетке</span></div>
              <div class="bracket-wrapper" id="bracketWrapper">
                <svg id="bracketSvg" class="bracket-svg"></svg>
                <div class="bracket-container" id="bracketContainer">
                  ${roundsHtml}
                </div>
              </div>
            </div>
          `;

        }



        // 2. FLAT LIST HTML

        const flatListHtml = `

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; margin-top: 12px;">

            ${playoffMatches.map(m => {

              const sMatchTitle = `${m.p1} vs ${m.p2} (${m.s1}:${m.s2}) • ${s.name}`;

              const protoId = m.vk_url ? registerProtocol(sMatchTitle, m.vk_text, m.vk_date, m.vk_page, m.vk_url) : '';

              const isP1Win = m.s1 > m.s2;

              const isP2Win = m.s2 > m.s1;

              return `

                <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); padding: 12px 14px; display: flex; justify-content: space-between; align-items: center;">

                  <div style="flex: 1;">

                    <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">${m.tour || 'Плей-офф'}</div>

                    <div style="font-size: 13px; color: ${isP1Win ? 'var(--nes-gold)' : '#fff'}; font-weight: 800; margin-top: 3px; cursor: pointer;" onclick="openPlayerModal('${m.p1}')">${m.p1}</div>

                    <div style="font-size: 13px; color: ${isP2Win ? 'var(--nes-gold)' : '#94a3b8'}; font-weight: 700; cursor: pointer;" onclick="openPlayerModal('${m.p2}')">${m.p2}</div>

                  </div>

                  <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">

                    <div class="score-badge" style="font-size: 15px; padding: 4px 10px; font-weight: 900; color: var(--nes-cyan);">

                      ${m.s1} : ${m.s2}

                    </div>

                    ${protoId ? `

                      <button type="button" class="source-btn-vk" style="font-size: 9px; padding: 2px 6px;" onclick="event.stopPropagation(); openProtocolModalById('${protoId}')">💬 Отчёт</button>

                    ` : ''}

                  </div>

                </div>

              `;

            }).join('')}

          </div>

        `;



        subContentHtml = `

          <div style="margin-top: 16px;">

            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">

              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold);">

                ⚡ СЕТКА ПЛЕЙ-ОФФ И ИТОГИ КУБКА:

              </div>

              ${playoffMatches.length > 0 ? `

                <div style="display: flex; gap: 6px;">

                  <button type="button" class="filter-btn ${playoffViewMode === 'bracket' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setPlayoffViewMode('bracket')">

                    ⚡ Турнирная сетка

                  </button>

                  <button type="button" class="filter-btn ${playoffViewMode === 'list' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setPlayoffViewMode('list')">

                    📋 Список всех игр (${playoffMatches.length})

                  </button>

                </div>

              ` : ''}

            </div>



            <!-- Key Season Highlights -->

            ${(s.highlights && s.highlights.length > 0) ? `

              <div style="background: rgba(255, 183, 3, 0.08); border: 1px solid var(--nes-gold); padding: 14px; margin-bottom: 16px;">

                <div style="font-family: var(--font-title); font-size: 12px; color: var(--nes-gold); margin-bottom: 8px;">🌟 ГЛАВНЫЕ СОБЫТИЯ СЕЗОНА:</div>

                <ul style="margin: 0; padding-left: 20px; color: #cbd5e1; font-size: 13px; line-height: 1.6;">

                  ${s.highlights.map(h => `<li>${h}</li>`).join('')}

                </ul>

              </div>

            ` : ''}



            ${playoffMatches.length > 0 ? (playoffViewMode === 'bracket' ? visualBracketHtml : flatListHtml) : `
              <div style="background: rgba(17, 24, 39, 0.85); border: 2px solid var(--nes-gold); padding: 28px 20px; text-align: center; box-shadow: 4px 4px 0 #000; margin-top: 14px;">
                <div style="font-size: 32px; margin-bottom: 8px;">🏛️ 👑</div>
                <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-gold); margin-bottom: 8px;">
                  ПЕРВЫЙ ИСТОРИЧЕСКИЙ СЕЗОН NST (2015 ГОД)
                </div>
                <div style="font-size: 13px; color: #cbd5e1; max-width: 650px; margin: 0 auto 16px auto; line-height: 1.6;">
                  Дебютный чемпионат лиги проводился по классической круговой системе в едином дивизионе. 
                  Титул безоговорочного первого Чемпиона завоевал <strong>mafuta</strong>. 
                  Кубковая стадия на выбывание (<strong>Кубок Лиг</strong>) была учреждена начиная со 2-го сезона.
                </div>
                <button type="button" class="filter-btn active" style="font-size: 12px; padding: 6px 16px;" onclick="switchSeasonSubTab('tables')">
                  🏆 Открыть итоговую таблицу 1-го сезона
                </button>
              </div>
            `}

          </div>

        `;

      }



      // 4. ABOUT SUB-TAB (DEEP CHRONICLES & VK LORE)

      else if (seasonSubTab === 'about') {

        const fullChronicleParas = (s.full_chronicle || s.summary || '').split(String.fromCharCode(10) + String.fromCharCode(10)).filter(Boolean);

        const keyEvents = s.key_events || s.highlights || [];

        const divSummary = s.divisions_summary || {};

        const wallQuotes = s.wall_quotes || [];

        const vkTopicUrl = s.topic_id ? `https://vk.ru/topic-66162180_${s.topic_id}` : null;

        const vkWallUrl = s.wall_post_id ? `https://vk.ru/wall-66162180_${s.wall_post_id}` : null;



        subContentHtml = `

          <div style="margin-top: 16px; display: flex; flex-direction: column; gap: 20px;">

            

            <!-- Era Banner & Primary Links -->

            <div style="background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(0,0,0,0.6)); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000;">

              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">

                <div>

                  <div style="font-size: 11px; font-family: var(--font-mono); color: var(--nes-gold); font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px;">

                    📜 ЭПОХАЛЬНАЯ ЛЕТОПИСЬ СЕЗОНА

                  </div>

                  <div style="font-family: var(--font-title); font-size: 20px; color: #fff; margin-bottom: 8px;">

                    ${s.era_title || s.name} (${s.year} год)

                  </div>

                  <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: #cbd5e1;">

                    <span>👑 <strong>Организаторы:</strong> ${s.organizers || 'Оргкомитет NST'}</span>

                    <span>🎮 <strong>Платформа:</strong> ${s.emulator || 'Mednafen Netplay'}</span>

                    <span>👥 <strong>Участников:</strong> ${participantsList.length} игроков</span>

                    <span>🏆 <strong>Формат:</strong> ${s.format}</span>

                  </div>

                </div>

                <div style="display: flex; gap: 8px; flex-wrap: wrap;">

                  ${vkTopicUrl ? `

                    <a href="${vkTopicUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #2563eb; color: #fff; border: 1px solid #60a5fa; display: inline-flex; align-items: center; gap: 6px;">

                      💬 Тема обсуждения в VK

                    </a>

                  ` : ''}

                  ${vkWallUrl ? `

                    <a href="${vkWallUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #059669; color: #fff; border: 1px solid #34d399; display: inline-flex; align-items: center; gap: 6px;">

                      📰 Итоги на стене VK

                    </a>

                  ` : ''}

                </div>

              </div>

            </div>



            <!-- Historical Chronicle Text -->

            <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 22px;">

              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-cyan); margin-bottom: 14px; display: flex; align-items: center; gap: 8px;">

                <span>📖 ХРОНИКА И ХОД ТУРНИРА</span>

              </div>

              <div style="color: #e2e8f0; font-size: 14px; line-height: 1.7; display: flex; flex-direction: column; gap: 14px;">

                ${fullChronicleParas.map(p => `<p style="margin: 0; text-align: justify;">${p}</p>`).join('')}

              </div>

            </div>



            <!-- Key Milestones & Records Grid -->

            ${keyEvents.length > 0 ? `

              <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  ⚡ КЛЮЧЕВЫЕ МОМЕНТЫ И РЕКОРДЫ СЕЗОНА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 10px;">

                  ${keyEvents.map(evt => `

                    <div style="background: rgba(255,255,255,0.04); border-left: 3px solid var(--nes-gold); padding: 10px 14px; font-size: 13px; color: #cbd5e1; line-height: 1.5;">

                      ${evt}

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}



            <!-- Divisions Summary -->

            ${Object.keys(divSummary).length > 0 ? `

              <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-green); margin-bottom: 12px;">

                  🏆 ИТОГИ ПО ДИВИЗИОНАМ И ЛИГАМ

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">

                  ${Object.entries(divSummary).map(([dName, dText]) => `

                    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); padding: 12px 16px;">

                      <div style="font-family: var(--font-title); font-size: 13px; color: var(--nes-gold); margin-bottom: 6px;">${dName}</div>

                      <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">${dText}</div>

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}



            <!-- Quotes of the Epoch -->

            ${wallQuotes.length > 0 ? `

              <div style="background: rgba(255, 183, 3, 0.04); border: 1px dashed var(--nes-gold); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  💬 АТМОСФЕРА И ЦИТАТЫ СЕЗОНА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px;">

                  ${wallQuotes.map(q => `

                    <div style="background: rgba(0,0,0,0.4); border-left: 3px solid var(--nes-cyan); padding: 12px 14px;">

                      <div style="font-size: 13px; color: #f1f5f9; font-style: italic; line-height: 1.5; margin-bottom: 6px;">

                        «${q.text}»

                      </div>

                      <div style="font-size: 11px; color: var(--nes-cyan); font-weight: 800; text-align: right;">

                        &mdash; ${q.author}

                      </div>

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}



            <!-- Technical Specs -->

            ${s.tech_specs ? `

              <div style="font-size: 12px; color: #94a3b8; background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.08); padding: 12px 16px;">

                ⚙️ <strong>Матчасть и регламент:</strong> ${s.tech_specs}

              </div>

            ` : ''}



          </div>

        `;

      }



      card.innerHTML = `

        <div class="special-card" style="border-color: var(--nes-cyan); box-shadow: 4px 4px 0px #000;">

          <!-- Header Row -->

          <div class="special-header-row">

            <div>

              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px;">

                <span class="special-tag tag-solo" style="background: #1e3a8a; color: #93c5fd; border-color: #3b82f6;">🏆 ОФИЦИАЛЬНЫЙ СЕЗОН NST</span>

                <span style="font-size: 12px; color: var(--nes-gold); font-weight: 800; font-family: var(--font-mono);">${s.year} ГОД</span>

                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>

                <span style="font-size: 11px; color: #cbd5e1; font-weight: 700;">Goal 3 (NES)</span>

                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>

                <span style="font-size: 11px; color: var(--nes-cyan);">${s.format}</span>

              </div>

              <h2 style="font-family: var(--font-title); font-size: 22px; color: #fff; margin: 0; ">

                ${s.name} &bull; Официальный чемпионат NST (${s.year} г.)

              </h2>

            </div>

          </div>



          <!-- Podium Box -->

          <div class="podium-box-grid">

            <div class="podium-slot gold">

              <span style="font-size: 24px;">🥇</span>

              <div>

                <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">1 МЕСТО &bull; ЧЕМПИОН</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px; cursor: pointer;" onclick="openPlayerModal('${s.champion}')">${s.champion}</div>

              </div>

            </div>

            <div class="podium-slot silver">

              <span style="font-size: 24px;">🥈</span>

              <div>

                <div style="font-size: 10px; color: #cbd5e1; font-weight: 800; text-transform: uppercase;">2 МЕСТО &bull; СЕРЕБРО</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px; cursor: pointer;" onclick="openPlayerModal('${s.runner_up}')">${s.runner_up}</div>

              </div>

            </div>

            <div class="podium-slot bronze">

              <span style="font-size: 24px;">🥉</span>

              <div>

                <div style="font-size: 10px; color: #d97706; font-weight: 800; text-transform: uppercase;">3 МЕСТО &bull; БРОНЗА</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px; cursor: pointer;" onclick="openPlayerModal('${s.third_place}')">${s.third_place || '—'}</div>

              </div>

            </div>

            ${s.cup_winner ? `

              <div class="podium-slot" style="border-color: #c084fc; background: rgba(192, 132, 252, 0.08);">

                <span style="font-size: 24px;">🏆</span>

                <div>

                  <div style="font-size: 10px; color: #c084fc; font-weight: 800; text-transform: uppercase;">КУБОК ЛИГИ</div>

                  <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px; cursor: pointer;" onclick="openPlayerModal('${s.cup_winner}')">${s.cup_winner}</div>

                </div>

              </div>

            ` : ''}

          </div>



          <!-- Key Master Players -->

          ${playersChips ? `

            <div style="margin: 12px 0 16px 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">

              <span style="font-size: 11px; color: #94a3b8; font-weight: 700;">Мастера лиги в сезоне:</span>

              ${playersChips}

            </div>

          ` : ''}



          <!-- Tournament Sub-Navigation Buttons (Tabs) -->

          <div style="display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 2px solid rgba(255,255,255,0.2); padding-bottom: 12px; margin-top: 16px;">

            <button class="filter-btn ${seasonSubTab === 'matches' ? 'active' : ''}" onclick="switchSeasonSubTab('matches')">

              📋 Все матчи сезона (${(s.matches || []).length})

            </button>

            <button class="filter-btn ${seasonSubTab === 'tables' ? 'active' : ''}" onclick="switchSeasonSubTab('tables')">

              🏆 Таблицы лиг

            </button>

            <button class="filter-btn ${seasonSubTab === 'playoff' ? 'active' : ''}" onclick="switchSeasonSubTab('playoff')">

              ⚡ Сетка плей-офф / Призёры

            </button>

            <button class="filter-btn ${seasonSubTab === 'about' ? 'active' : ''}" onclick="switchSeasonSubTab('about')">

              📜 Летопись и история

            </button>

          </div>



          <!-- Active Sub-Tab Content -->

          ${subContentHtml}

        </div>

      `;

      if (seasonSubTab === 'playoff' && playoffViewMode === 'bracket') {
        setTimeout(drawBracketConnectors, 60);
      }

    }



    // Clutch & Records

    function renderClutch() {

      const container = document.getElementById('tab-clutch');

      if (!container) return;



      const medals = DATA.medal_leaders || [];

      const cleanSheets = DATA.clean_sheet_leaders || [];

      const clutch = DATA.clutch_leaders || [];

      const attacking = DATA.spec_attacking || [];

      const defensive = DATA.spec_defensive || [];

      const topScorers = DATA.top_scorers_leaders || [];

      const veterans = DATA.veterans_longevity || [];



      container.innerHTML = `

        <div class="season-banner" style="margin-bottom: 24px;">

          <div class="season-title">📊 ЗАЛ СЛАВЫ РЕКОРДОВ, МЕДАЛИ & АНАЛИТИКА NST (2015–2026)</div>

          <div class="season-meta">Сводная статистика за всю историю киберспортивной лиги Goal 3: медальный зачёт, книга исторических рекордов, стили игры, долгожители и рейтинг цитируемости</div>

        </div>



        <!-- 1. MEDAL TABLE & TROPHY CABINET -->

        <div style="background: rgba(0,0,0,0.65); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000; margin-bottom: 24px;">

          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">

            <div>

              <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-gold); margin: 0;">🏅 ОФИЦИАЛЬНЫЙ МЕДАЛЬНЫЙ ЗАЧЁТ ЛИГИ (TROPHY CABINET)</h2>

              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Титулы и призовые места в официальных чемпионатах и Кубках Лиг (Сезоны 1–9). Спецтурниры и пенальти исключены из Зала славы.</div>

            </div>

            <div style="background: rgba(255, 183, 3, 0.15); border: 1px solid var(--nes-gold); padding: 6px 12px; font-size: 12px; font-weight: 700; color: #fff;">

              👑 Первый GOAT: <strong style="color: var(--nes-gold); cursor: pointer;" onclick="openPlayerModal('mafuta')">mafuta</strong> (7 золотых трофеев)

            </div>

          </div>



          <div class="table-box" style="margin-bottom: 0;">

            <table>

              <thead>

                <tr>

                  <th style="width: 40px; text-align: center;">#</th>

                  <th>Игрок</th>

                  <th style="text-align: center; color: var(--nes-gold);">🥇 Золото</th>

                  <th style="text-align: center; color: #cbd5e1;">🥈 Серебро</th>

                  <th style="text-align: center; color: #d97706;">🥉 Бронза</th>

                  <th style="text-align: center;">Всего</th>

                  <th style="text-align: center;">Финалов</th>

                  <th>Главные титулы</th>

                </tr>

              </thead>

              <tbody>

                ${medals.slice(0, 10).map((m, idx) => `

                  <tr onclick="openPlayerModal('${m.player}')" style="cursor: pointer;">

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: ${idx === 0 ? 'var(--nes-gold)' : (idx === 1 ? '#cbd5e1' : (idx === 2 ? '#d97706' : '#94a3b8'))};">${idx + 1}</td>

                    <td>

                      <div style="display: flex; align-items: center; gap: 8px;">

                        <img src="${m.avatar}" style="width: 26px; height: 26px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.player}'">

                        <strong style="color: #fff;">${m.player}</strong>

                      </div>

                    </td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold);">${m.medals.gold}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: #cbd5e1;">${m.medals.silver}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: #d97706;">${m.medals.bronze}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 900; color: #fff;">${m.medals.gold + m.medals.silver + m.medals.bronze}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 700; color: var(--nes-cyan);">${m.medals.finals}</td>

                    <td style="font-size: 11px; color: #94a3b8;">${(m.medals.titles || []).slice(0, 2).join(' &bull; ')}</td>

                  </tr>

                `).join('')}

              </tbody>

            </table>

          </div>

        </div>



        <!-- 2. HISTORIC EXTREMES & RECORDS -->

        <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-cyan); margin: 24px 0 14px 0;">⚡ КНИГА ИСТОРИЧЕСКИХ РЕКОРДОВ NST</h2>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px;">

          <!-- Record 1: Blowout -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid #ffffff; padding: 16px; box-shadow: 3px 3px 0 #000;">

            <div style="font-size: 11px; color: var(--nes-gold); font-family: var(--font-title); letter-spacing: 1px;">💥 САМЫЙ КРУПНЫЙ РАЗГРОМ В ИСТОРИИ</div>

            <div style="font-size: 22px; font-weight: 900; margin: 8px 0; color: #fff;">

              Kunio <span style="color: var(--nes-green);">14 : 0</span> yoxter

            </div>

            <div style="font-size: 12px; color: #94a3b8;">

              Разница: <strong style="color: var(--nes-gold);">+14 мячей</strong> &bull; Официальный Чемпионат (Сезон 2)

            </div>

          </div>



          <!-- Record 2: Thriller -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid #ffffff; padding: 16px; box-shadow: 3px 3px 0 #000;">

            <div style="font-size: 11px; color: var(--nes-cyan); font-family: var(--font-title); letter-spacing: 1px;">🌪️ САМЫЙ БЕЗУМНЫЙ ТРИЛЛЕР (23 ГОЛА)</div>

            <div style="font-size: 22px; font-weight: 900; margin: 8px 0; color: #fff;">

              Kipriot <span style="color: var(--nes-cyan);">12 : 11</span> Transistor

            </div>

            <div style="font-size: 12px; color: #94a3b8;">

              Всего забито: <strong style="color: var(--nes-cyan);">23 гола в одном матче!</strong> &bull; Сезон 4

            </div>

          </div>



          <!-- Record 3: Runner-up Thriller -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid #ffffff; padding: 16px; box-shadow: 3px 3px 0 #000;">

            <div style="font-size: 11px; color: #f59e0b; font-family: var(--font-title); letter-spacing: 1px;">🔥 СВЕРХРЕЗУЛЬТАТИВНОЕ ДЕРБИ (21 ГОЛ)</div>

            <div style="font-size: 22px; font-weight: 900; margin: 8px 0; color: #fff;">

              ectoPower <span style="color: #f59e0b;">11 : 10</span> Huba Buba

            </div>

            <div style="font-size: 12px; color: #94a3b8;">

              Всего забито: <strong style="color: #f59e0b;">21 гол</strong> &bull; Сезон 2 (Золотая эпоха)

            </div>

          </div>

        </div>



        <!-- 2.5. ALL-TIME TOP SCORERS (SEASONS 1–9 ONLY) -->

        <div style="background: rgba(0,0,0,0.65); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000; margin-bottom: 24px;">

          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">

            <div>

              <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-gold); margin: 0;">⚽ ЛУЧШИЕ БОМБАРДИРЫ В ИСТОРИИ (СЕЗОНЫ 1–9)</h2>

              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Суммарное количество голов только в официальных матчах чемпионатов NST (без товарищеских пенальти и спецтурниров)</div>

            </div>

            <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; padding: 6px 12px; font-size: 12px; font-weight: 700; color: #fff;">

              🎯 Лучший бомбардир всех времён: <strong style="color: #fca5a5; cursor: pointer;" onclick="openPlayerModal('ectoPower')">ectoPower</strong> (795 голов)

            </div>

          </div>



          <div class="table-box" style="margin-bottom: 0;">

            <table>

              <thead>

                <tr>

                  <th style="width: 40px; text-align: center;">#</th>

                  <th>Бомбардир</th>

                  <th style="text-align: center; color: var(--nes-gold);">⚽ Всего голов</th>

                  <th style="text-align: center;">Матчей в Сезонах</th>

                  <th style="text-align: center; color: var(--nes-cyan);">Ср. голов за матч</th>

                  <th>Статус</th>

                </tr>

              </thead>

              <tbody>

                ${topScorers.slice(0, 8).map((sc, idx) => `

                  <tr onclick="openPlayerModal('${sc.player}')" style="cursor: pointer;">

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: ${idx === 0 ? 'var(--nes-gold)' : (idx === 1 ? '#cbd5e1' : (idx === 2 ? '#d97706' : '#94a3b8'))};">${idx + 1}</td>

                    <td>

                      <div style="display: flex; align-items: center; gap: 8px;">

                        <img src="${sc.avatar}" style="width: 26px; height: 26px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${sc.player}'">

                        <strong style="color: #fff;">${sc.player}</strong>

                      </div>

                    </td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold); font-size: 16px;">${sc.goals_for}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 700; color: #fff;">${sc.matches}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: var(--nes-cyan);">${sc.gpg}</td>

                    <td style="font-size: 11px; color: #94a3b8;">${idx === 0 ? '🥇 Абсолютный рекордсмен' : (idx === 1 ? '🥈 Легенда золотой эпохи' : '🔥 Элитный снайпер')}</td>

                  </tr>

                `).join('')}

              </tbody>

            </table>

          </div>

        </div>



        <!-- 3. CLEAN SHEETS & CLUTCH KINGS -->

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; margin-bottom: 24px;">

          <!-- Clean Sheets Wall -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid rgba(255,255,255,0.4); padding: 18px; box-shadow: 3px 3px 0 #000;">

            <h3 style="font-family: var(--font-title); font-size: 16px; color: var(--nes-green); margin-bottom: 8px;">🧱 «СУХАЯ СТЕНА» (РЕКОРДСМЕНЫ ПО МАТЧАМ НА НОЛЬ)</h3>

            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">Количество победных матчей, в которых соперник не забил ни одного гола</div>

            <div style="display: flex; flex-direction: column; gap: 8px;">

              ${cleanSheets.map((p, idx) => `

                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(0,0,0,0.3); border-left: 3px solid var(--nes-green); cursor: pointer;" onclick="openPlayerModal('${p.player}')">

                  <div style="display: flex; align-items: center; gap: 8px;">

                    <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold); width: 20px;">${idx + 1}.</span>

                    <strong>${p.player}</strong>

                  </div>

                  <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-green); font-size: 14px;">${p.clean_sheets} сухарей</span>

                </div>

              `).join('')}

            </div>

          </div>



          <!-- Clutch Overtime Kings -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid rgba(255,255,255,0.4); padding: 18px; box-shadow: 3px 3px 0 #000;">

            <h3 style="font-family: var(--font-title); font-size: 16px; color: var(--nes-gold); margin-bottom: 8px;">🎯 КОРОЛИ ОВЕРТАЙМОВ И СТАЛЬНЫХ НЕРВОВ</h3>

            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">Лидеры по проценту побед в матчах до золотого гола (от 3+ овертаймов)</div>

            <div style="display: flex; flex-direction: column; gap: 8px;">

              ${clutch.map((p, idx) => `

                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(0,0,0,0.3); border-left: 3px solid var(--nes-gold); cursor: pointer;" onclick="openPlayerModal('${p.player}')">

                  <div style="display: flex; align-items: center; gap: 8px;">

                    <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-cyan); width: 20px;">${idx + 1}.</span>

                    <strong>${p.player}</strong>

                  </div>

                  <div>

                    <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold); font-size: 14px;">${p.ot_win_rate}%</span>

                    <span style="font-size: 11px; color: #94a3b8; margin-left: 4px;">(${p.ot_wins}В-${p.ot_losses}П)</span>

                  </div>

                </div>

              `).join('')}

            </div>

          </div>

        </div>



        <!-- 4. PLAYSTYLES: HURRICANE ATTACK VS IRON BUS -->

        <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-gold); margin: 24px 0 14px 0;">🌪️ СТИЛИ ИГРЫ: УРАГАННАЯ АТАКА VS «АВТОБУСЫ»</h2>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; margin-bottom: 24px;">

          <!-- Attackers -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid rgba(255,255,255,0.4); padding: 18px; box-shadow: 3px 3px 0 #000;">

            <h3 style="font-family: var(--font-title); font-size: 15px; color: #f87171; margin-bottom: 8px;">🔥 САМЫЕ ЗРЕЛИЩНЫЕ / УРАГАННЫЕ ИГРОКИ</h3>

            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">Наибольший средний тотал забитых и пропущенных голов в матчах (от 15+ игр)</div>

            <div style="display: flex; flex-direction: column; gap: 8px;">

              ${attacking.map((p, idx) => `

                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(0,0,0,0.3); border-left: 3px solid #f87171; cursor: pointer;" onclick="openPlayerModal('${p.player}')">

                  <div style="display: flex; align-items: center; gap: 8px;">

                    <span style="font-family: var(--font-mono); font-weight: 800; color: #f87171; width: 20px;">${idx + 1}.</span>

                    <strong>${p.player}</strong>

                  </div>

                  <span style="font-family: var(--font-mono); font-weight: 800; color: #f87171; font-size: 14px;">${p.spectacle} гол/матч</span>

                </div>

              `).join('')}

            </div>

          </div>



          <!-- Defensive -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid rgba(255,255,255,0.4); padding: 18px; box-shadow: 3px 3px 0 #000;">

            <h3 style="font-family: var(--font-title); font-size: 15px; color: var(--nes-cyan); margin-bottom: 8px;">🛡️ САМЫЕ ЗАКРЫТЫЕ / «АВТОБУСНЫЕ» ИГРОКИ</h3>

            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">Наименьший средний тотал голов (строгая позиционная оборона и сушка темпа)</div>

            <div style="display: flex; flex-direction: column; gap: 8px;">

              ${defensive.map((p, idx) => `

                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(0,0,0,0.3); border-left: 3px solid var(--nes-cyan); cursor: pointer;" onclick="openPlayerModal('${p.player}')">

                  <div style="display: flex; align-items: center; gap: 8px;">

                    <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-cyan); width: 20px;">${idx + 1}.</span>

                    <strong>${p.player}</strong>

                  </div>

                  <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-cyan); font-size: 14px;">${p.spectacle} гол/матч</span>

                </div>

              `).join('')}

            </div>

          </div>

        </div>



        <!-- 5. VETERANS & LONGEVITY -->

        <h2 style="font-family: var(--font-title); font-size: 18px; color: #fff; margin: 24px 0 14px 0;">⏳ «СТАРАЯ ГВАРДИЯ» NST (ДОЛГОЛЕТИЕ 2015 → 2026)</h2>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-bottom: 24px;">

          ${veterans.map(v => `

            <div style="background: rgba(10, 27, 45, 0.85); border: 2px solid rgba(255,255,255,0.3); padding: 14px; box-shadow: 3px 3px 0 #000; cursor: pointer;" onclick="openPlayerModal('${v.player}')">

              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">

                <strong style="font-size: 15px; color: #fff;">${v.player}</strong>

                <span style="font-family: var(--font-mono); font-size: 11px; font-weight: 800; color: var(--nes-green); background: rgba(34,197,94,0.15); padding: 2px 6px; border: 1px solid #22c55e;">${v.span}</span>

              </div>

              <div style="font-size: 12px; color: #cbd5e1; line-height: 1.4;">${v.desc}</div>

              <div style="font-size: 11px; color: #94a3b8; margin-top: 8px; font-weight: 700;">Всего матчей в архиве: <strong style="color: #fff;">${v.matches}</strong></div>

            </div>

          `).join('')}

        </div>



        

      `;

    }



    // Head-to-Head & Rivalries Engine

    function getAllMatches() {

      const all = [];

      (DATA.seasons || []).forEach(s => {

        const sTitle = s.title || `Сезон ${s.id}`;

        (s.matches || []).forEach(m => {

          const mc = Object.assign({}, m);

          if (!mc.season) mc.season = sTitle;

          if (!mc.league) mc.league = s.league || 'Регулярный чемпионат';

          if (!mc.stage) mc.stage = mc.tour || 'Матч';

          all.push(mc);

        });

      });

      (DATA.special_matches || []).forEach(m => {

        const mc = Object.assign({}, m);

        if (!mc.season) mc.season = 'Спецтурнир';

        if (!mc.league) mc.league = 'Турнир';

        if (!mc.stage) mc.stage = mc.tour || 'Матч';

        all.push(mc);

      });

      return all;

    }



    function initH2HControls() {

      const canonicalMap = new Map();



      // First add Master Profiles (38)

      (DATA.profiles || []).forEach(p => {

        canonicalMap.set(p.player.toLowerCase(), p.player);

      });



      // Then add season participants, normalizing

      (DATA.seasons || []).forEach(s => {

        (s.matches || []).forEach(m => {

          [m.p1, m.p2].forEach(p => {

            if (!p) return;

            const pNorm = p.trim();

            const pLow = pNorm.toLowerCase();

            if (!canonicalMap.has(pLow)) {

              canonicalMap.set(pLow, pNorm);

            }

          });

        });

      });



      const masterNames = (DATA.profiles || []).map(p => p.player);

      const otherNames = [];



      canonicalMap.forEach((origName, low) => {

        if (!masterNames.some(m => m.toLowerCase() === low)) {

          otherNames.push(origName);

        }

      });



      masterNames.sort((a, b) => a.localeCompare(b));

      otherNames.sort((a, b) => a.localeCompare(b));



      const sel1 = document.getElementById('h2hSelectP1');

      const sel2 = document.getElementById('h2hSelectP2');

      if (!sel1 || !sel2) return;



      const optsHtml = `

        <optgroup label="⭐ МАСТЕРА ЛИГИ (АКТИВНЫЕ И ЛЕГЕНДЫ)">

          ${masterNames.map(p => `<option value="${p}">${p}</option>`).join('')}

        </optgroup>

        <optgroup label="🎮 УЧАСТНИКИ ТУРНИРОВ И КУБКОВ">

          ${otherNames.map(p => `<option value="${p}">${p}</option>`).join('')}

        </optgroup>

      `;



      sel1.innerHTML = optsHtml;

      sel2.innerHTML = optsHtml;



      sel1.value = 'Kunio';

      sel2.value = 'Ric25';



      updateH2HComparison();

    }



    function selectH2HPair(p1, p2) {

      const sel1 = document.getElementById('h2hSelectP1');

      const sel2 = document.getElementById('h2hSelectP2');

      if (sel1 && sel2) {

        sel1.value = p1;

        sel2.value = p2;

        updateH2HComparison();

        const res = document.getElementById('h2hComparisonResult');

        if (res) {

          res.scrollIntoView({ behavior: 'smooth', block: 'start' });

        }

      }

    }



    function updateH2HComparison() {

      const sel1 = document.getElementById('h2hSelectP1');

      const sel2 = document.getElementById('h2hSelectP2');

      const container = document.getElementById('h2hComparisonResult');

      if (!sel1 || !sel2 || !container) return;



      const p1 = sel1.value;

      const p2 = sel2.value;



      if (!p1 || !p2 || p1 === p2) {

        container.innerHTML = `

          <div style="background: #081729; border: 1px dashed #2a4e75; border-radius: 8px; padding: 24px; text-align: center; color: #cbd5e1;">

            <div style="font-family: var(--font-body); font-size: 16px; font-weight: 700; color: #f43f5e; margin-bottom: 6px;">ВЫБРАН ОДИН И ТОТ ЖЕ ИГРОК</div>

            <div style="font-size: 14px;">Пожалуйста, выберите двух разных соперников для расчета баланса личных встреч.</div>

          </div>

        `;

        return;

      }



      const p1Low = p1.toLowerCase();

      const p2Low = p2.toLowerCase();

      const allMatches = getAllMatches();



      const pairMatches = allMatches.filter(m => {

        const m1 = (m.p1 || '').toLowerCase();

        const m2 = (m.p2 || '').toLowerCase();

        return (m1 === p1Low && m2 === p2Low) || (m1 === p2Low && m2 === p1Low);

      });



      const p1Wins = pairMatches.filter(m => {

        const isP1Home = (m.p1 || '').toLowerCase() === p1Low;

        const s1 = Number(m.s1 || 0);

        const s2 = Number(m.s2 || 0);

        return isP1Home ? s1 > s2 : s2 > s1;

      }).length;



      const p2Wins = pairMatches.filter(m => {

        const isP2Home = (m.p1 || '').toLowerCase() === p2Low;

        const s1 = Number(m.s1 || 0);

        const s2 = Number(m.s2 || 0);

        return isP2Home ? s1 > s2 : s2 > s1;

      }).length;



      const draws = pairMatches.filter(m => Number(m.s1 || 0) === Number(m.s2 || 0)).length;



      const p1Goals = pairMatches.reduce((acc, m) => acc + ((m.p1 || '').toLowerCase() === p1Low ? Number(m.s1 || 0) : Number(m.s2 || 0)), 0);

      const p2Goals = pairMatches.reduce((acc, m) => acc + ((m.p1 || '').toLowerCase() === p2Low ? Number(m.s1 || 0) : Number(m.s2 || 0)), 0);



      const prof1 = DATA.profiles.find(x => x.player.toLowerCase() === p1Low);

      const prof2 = DATA.profiles.find(x => x.player.toLowerCase() === p2Low);

      const av1 = prof1 ? prof1.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p1}`;

      const av2 = prof2 ? prof2.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p2}`;



      const total = pairMatches.length;



      if (total === 0) {

        container.innerHTML = `

          <div style="background: #081729; border: 1px solid #1e3a58; border-radius: 8px; padding: 28px; text-align: center;">

            <div style="display: flex; justify-content: center; align-items: center; gap: 24px; margin-bottom: 16px;">

              <div style="text-align: center; cursor: pointer;" onclick="openPlayerModal('${p1}')">

                <img src="${av1}" class="fighter-avatar" style="border: 2px solid #f43f5e;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p1}'">

                <div style="font-family: var(--font-body); font-size: 16px; font-weight: 700; color: #ffffff; margin-top: 6px;">${p1}</div>

              </div>

              <div style="font-family: var(--font-title); font-size: 24px; color: #64748b;">VS</div>

              <div style="text-align: center; cursor: pointer;" onclick="openPlayerModal('${p2}')">

                <img src="${av2}" class="fighter-avatar" style="border: 2px solid #c084fc;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p2}'">

                <div style="font-family: var(--font-body); font-size: 16px; font-weight: 700; color: #ffffff; margin-top: 6px;">${p2}</div>

              </div>

            </div>

            <div style="font-family: var(--font-body); font-size: 16px; font-weight: 700; color: #f43f5e; margin-bottom: 6px;">МАТЧИ НЕ НАЙДЕНЫ</div>

            <div style="color: #cbd5e1; font-size: 14px;">Официальных встреч между <strong>${p1}</strong> и <strong>${p2}</strong> в базе лиги не зафиксировано.</div>

            <div style="font-size: 12px; color: #94a3b8; margin-top: 6px;">Возможно, игроки выступали в разные периоды времени или в параллельных лигах.</div>

          </div>

        `;

        return;

      }



      const p1Pct = Math.round(p1Wins / total * 100);

      const p2Pct = Math.round(p2Wins / total * 100);

      const drawPct = 100 - p1Pct - p2Pct;

      const avgGoals = ((p1Goals + p2Goals) / total).toFixed(1);



      const matchesListHtml = pairMatches.map((m, idx) => {

        const isP1Home = (m.p1 || '').toLowerCase() === p1Low;

        const s1Val = (m.s1 !== undefined && m.s1 !== null) ? Number(m.s1) : 0;

        const s2Val = (m.s2 !== undefined && m.s2 !== null) ? Number(m.s2) : 0;



        const p1Score = isP1Home ? s1Val : s2Val;

        const p2Score = isP1Home ? s2Val : s1Val;



        const isP1Win = p1Score > p2Score;

        const isP2Win = p2Score > p1Score;

        const h2hMatchTitle = `${p1} vs ${p2} (${p1Score}:${p2Score})${m.season ? ' • ' + m.season : ''}`;

        const protoId = m.vk_url ? registerProtocol(h2hMatchTitle, m.vk_text, m.vk_date, m.vk_page, m.vk_url) : '';

        const isDraw = p1Score === p2Score;



        const seasonTitle = m.season || 'Сезон NST';

        const stageTitle = m.stage || m.tour || 'Матч';

        const leagueTitle = m.league || '';



        const gamesExtra = m.games ? `<div style="font-size: 11px; color: #cbd5e1; margin-top: 3px; font-style: italic;">Игры: ${m.games}</div>` : '';

        const otBadge = m.pk ? '<span class="ot-tag ot-purple" style="font-size: 10px; margin-left: 4px;">ПЕН</span>' : (m.ot ? '<span class="ot-tag ot-gold" style="font-size: 10px; margin-left: 4px;">ОТ</span>' : '');



        const resultBadge = isP1Win 

          ? `<span style="background: #be123c; color: #ffffff; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 4px; white-space: nowrap;">Победа ${p1}</span>`

          : (isP2Win

            ? `<span style="background: #7e22ce; color: #ffffff; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 4px; white-space: nowrap;">Победа ${p2}</span>`

            : `<span style="background: #334155; color: #cbd5e1; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 4px; white-space: nowrap;">Ничья</span>`

          );



        return `

          <div class="h2h-match-row">

            <div class="h2h-match-meta">

              <div class="h2h-match-season" title="${seasonTitle}">${seasonTitle}</div>

              <div class="h2h-match-sub">

                ${leagueTitle ? `<span class="league-badge ${leagueTitle.includes('Высшая') ? 'badge-premier' : (leagueTitle.includes('Средняя') ? 'badge-middle' : 'badge-yard')}" style="font-size: 10px; padding: 2px 6px;">${leagueTitle}</span>` : ''}

                <span style="color: #cbd5e1; font-weight: 600;">${stageTitle}</span>

              </div>

            </div>



            <div class="h2h-duel-center">

              <div class="h2h-player-cell h2h-p1-cell ${isP1Win ? 'h2h-p1-winner' : ''}" onclick="openPlayerModal('${p1}')" style="cursor: pointer;" title="Открыть профиль ${p1}">

                ${isP1Win ? '👑 ' : ''}${p1}

              </div>

              <div class="h2h-score-box">

                <span class="${isP1Win ? 'p1-color' : ''}" style="font-weight: 800;">${p1Score}</span>

                <span style="color: #64748b; margin: 0 4px;">:</span>

                <span class="${isP2Win ? 'p2-color' : ''}" style="font-weight: 800;">${p2Score}</span>

                ${otBadge}

              </div>

              <div class="h2h-player-cell h2h-p2-cell ${isP2Win ? 'h2h-p2-winner' : ''}" onclick="openPlayerModal('${p2}')" style="cursor: pointer;" title="Открыть профиль ${p2}">

                ${p2}${isP2Win ? ' 👑' : ''}

              </div>

            </div>



            <div class="h2h-result-badge">

              ${resultBadge}

              ${gamesExtra}

              ${(m.vk_url || m.video_url) ? `

                <div style="display: flex; gap: 6px; align-items: center; margin-top: 6px; flex-wrap: wrap; justify-content: flex-end;">

                  ${m.vk_url ? `

                    <button type="button" class="source-btn-vk" onclick="event.stopPropagation(); openProtocolModalById('${protoId}')" title="Посмотреть текст отчёта матча из ВК">

                      💬 ВК

                    </button>

                  ` : ''}

                  ${m.video_url ? (

                    (m.video_url.includes('youtube.com') || m.video_url.includes('youtu.be')) ? `

                      <a href="${m.video_url}" target="_blank" rel="noopener" class="source-btn-video" title="Смотреть на YouTube в новой вкладке">

                        🎬 YouTube ↗

                      </a>

                    ` : `

                      <button type="button" class="source-btn-video" onclick="event.stopPropagation(); openVideoModal('${m.video_url}', '${p1} vs ${p2} (${p1Score}:${p2Score})')" title="Смотреть в плеере на сайте">

                        🎬 Видео

                      </button>

                    `

                  ) : ''}

                </div>

              ` : ''}

            </div>

          </div>

        `;

      }).join('');



      container.innerHTML = `

        <div class="h2h-billboard">

          <div class="h2h-fighters-row">

            <!-- Fighter 1 Card (Red Corner) -->

            <div class="fighter-card p1-side" onclick="openPlayerModal('${p1}')" title="Кликните, чтобы открыть профиль ${p1}">

              <img src="${av1}" class="fighter-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p1}'">

              <div class="fighter-info">

                <div class="fighter-name">${p1}</div>

                <div class="fighter-meta">

                  ${prof1 ? `Рейтинг: <strong style="color: #ffffff;">${prof1.active_elo.toFixed(1)}</strong>` : 'Участник турниров'}

                </div>

                <div class="fighter-wins-badge">

                  ${p1Wins} ПОБЕД (${p1Pct}%)

                </div>

              </div>

            </div>



            <!-- Center Duel Stats (Series Nexus) -->

            <div class="duel-center-stats">

              <div style="font-family: var(--font-body); font-size: 12px; font-weight: 700; color: #cbd5e1; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">

                СЧЁТ В СЕРИИ

              </div>

              <div class="duel-score-large">

                <span class="p1-color">${p1Wins}</span>

                <span class="duel-colon">:</span>

                <span class="p2-color">${p2Wins}</span>

              </div>

              <div class="duel-ratio-bar">

                <div class="duel-bar-p1" style="width: ${p1Pct}%;" title="${p1}: ${p1Pct}%"></div>

                ${draws > 0 ? `<div class="duel-bar-draw" style="width: ${drawPct}%;" title="Ничьи: ${drawPct}%"></div>` : ''}

                <div class="duel-bar-p2" style="width: ${p2Pct}%;" title="${p2}: ${p2Pct}%"></div>

              </div>

              <div class="duel-submetrics">

                <span>Всего матчей: <strong>${total}</strong></span>

                ${draws > 0 ? `<span>Ничьих: <strong>${draws}</strong></span>` : ''}

                <span>Мячи: <strong>${p1Goals} : ${p2Goals}</strong></span>

                <span>Ср. голов: <strong>${avgGoals}</strong></span>

              </div>

            </div>



            <!-- Fighter 2 Card (Purple Corner) -->

            <div class="fighter-card p2-side" onclick="openPlayerModal('${p2}')" title="Кликните, чтобы открыть профиль ${p2}">

              <div class="fighter-info" style="text-align: right;">

                <div class="fighter-name">${p2}</div>

                <div class="fighter-meta">

                  ${prof2 ? `Рейтинг: <strong style="color: #ffffff;">${prof2.active_elo.toFixed(1)}</strong>` : 'Участник турниров'}

                </div>

                <div class="fighter-wins-badge">

                  ${p2Wins} ПОБЕД (${p2Pct}%)

                </div>

              </div>

              <img src="${av2}" class="fighter-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p2}'">

            </div>

          </div>

        </div>



        <div class="h2h-history-box">

          <div class="h2h-history-header">

            <div style="display: flex; align-items: center; gap: 8px;">

              <span>📋 ИСТОРИЯ ОЧНЫХ МАТЧЕЙ</span>

              <span style="background: #14324f; color: #cbd5e1; font-family: var(--font-mono); font-size: 12px; padding: 2px 8px; border-radius: 4px;">${pairMatches.length}</span>

            </div>

            <div style="font-size: 12px; color: #cbd5e1; font-weight: 500;">Кликните по игроку, чтобы открыть его карточку</div>

          </div>

          <div class="h2h-history-list">

            ${matchesListHtml}

          </div>

        </div>

      `;

    }



    function renderH2H() {

      initH2HControls();



      // Default pair selection

      const sel1 = document.getElementById('h2hSelectP1');

      const sel2 = document.getElementById('h2hSelectP2');

      if (sel1 && sel2) {

        if (!sel1.value) sel1.value = 'ectoPower';

        if (!sel2.value) sel2.value = 'Rock';

      }

      updateH2HComparison();



      const hBox = document.getElementById('h2hList');

      if (!hBox) return;



      const allMatches = getAllMatches();



      hBox.innerHTML = (DATA.rivalries || []).map(r => {

        const p1 = r.p1 || r.favorite || '';

        const p2 = r.p2 || r.kryptonite || '';

        const title = r.rivalry || r.rivalry_type || `${p1} vs ${p2}`;

        const notes = r.notes || '';



        const p1Low = p1.toLowerCase();

        const p2Low = p2.toLowerCase();



        const pairMatches = allMatches.filter(m => {

          const m1 = (m.p1 || '').toLowerCase();

          const m2 = (m.p2 || '').toLowerCase();

          return (m1 === p1Low && m2 === p2Low) || (m1 === p2Low && m2 === p1Low);

        });



        const p1Wins = pairMatches.filter(m => {

          const isP1Home = (m.p1 || '').toLowerCase() === p1Low;

          const s1 = Number(m.s1 || 0);

          const s2 = Number(m.s2 || 0);

          return isP1Home ? s1 > s2 : s2 > s1;

        }).length;



        const p2Wins = pairMatches.filter(m => {

          const isP2Home = (m.p1 || '').toLowerCase() === p2Low;

          const s1 = Number(m.s1 || 0);

          const s2 = Number(m.s2 || 0);

          return isP2Home ? s1 > s2 : s2 > s1;

        }).length;



        const draws = pairMatches.filter(m => Number(m.s1 || 0) === Number(m.s2 || 0)).length;

        const p1Goals = pairMatches.reduce((acc, m) => acc + ((m.p1 || '').toLowerCase() === p1Low ? Number(m.s1 || 0) : Number(m.s2 || 0)), 0);

        const p2Goals = pairMatches.reduce((acc, m) => acc + ((m.p1 || '').toLowerCase() === p2Low ? Number(m.s1 || 0) : Number(m.s2 || 0)), 0);



        const prof1 = DATA.profiles.find(x => x.player.toLowerCase() === p1Low);

        const prof2 = DATA.profiles.find(x => x.player.toLowerCase() === p2Low);

        const av1 = prof1 ? prof1.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p1}`;

        const av2 = prof2 ? prof2.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p2}`;



        return `

          <div style="background: #0c1e32; border: 1px solid #1e3a58; border-radius: 8px; padding: 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.4); display: flex; flex-direction: column; justify-content: space-between;">

            <div>

              <div style="font-size: 13px; color: #ffffff; font-weight: 700; font-family: var(--font-body); margin-bottom: 10px;">${title}</div>

              <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0; background: #081729; border: 1px solid #1a334e; border-radius: 6px; padding: 10px 14px;">

                <div style="display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="openPlayerModal('${p1}')">

                  <img src="${av1}" style="width: 32px; height: 32px; border-radius: 4px; border: 1px solid #f43f5e;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p1}'">

                  <span style="font-size: 14px; font-weight: 700; color: #f43f5e;">${p1}</span>

                </div>

                <div style="text-align: center;">

                  <div style="font-family: var(--font-mono); font-weight: 800; font-size: 20px; color: #ffffff;">

                    <span style="color: #f43f5e;">${p1Wins}</span> : <span style="color: #c084fc;">${p2Wins}</span>

                  </div>

                  <div style="font-size: 11px; color: #94a3b8;">${pairMatches.length} игр</div>

                </div>

                <div style="display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="openPlayerModal('${p2}')">

                  <span style="font-size: 14px; font-weight: 700; color: #c084fc;">${p2}</span>

                  <img src="${av2}" style="width: 32px; height: 32px; border-radius: 4px; border: 1px solid #c084fc;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p2}'">

                </div>

              </div>

              <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 6px;">

                Мячи: <strong>${p1Goals} : ${p2Goals}</strong> ${draws > 0 ? `| Ничьих: <strong>${draws}</strong>` : ''}

              </div>

              ${notes ? `<div style="font-size: 12px; color: #cbd5e1; line-height: 1.45; border-left: 3px solid #f43f5e; padding-left: 8px; margin-top: 8px; background: rgba(0,0,0,0.2); padding-top: 4px; padding-bottom: 4px;">${notes}</div>` : ''}

            </div>

            <button class="action-btn" style="width: 100%; margin-top: 14px; padding: 7px 12px; font-size: 13px;" onclick="selectH2HPair('${p1}', '${p2}')">Смотреть очные матчи в калькуляторе ↗</button>

          </div>

        `;

      }).join('');

    }



    let selectedTeamTournId = 'team_champ_6';

    let teamSubTab = 'matches';

    let teamPairFilter = 'all';



    function selectTeamTournament(id) {

      selectedTeamTournId = id;

      teamPairFilter = 'all';

      renderTeamTournamentsBar();

      renderTeamTournamentDetails();

    }



    function switchTeamSubTab(subTab) {

      teamSubTab = subTab;

      renderTeamTournamentDetails();

    }



    function filterTeamPair(pair) {

      teamPairFilter = pair;

      renderTeamTournamentDetails();

    }



    function renderTeamTournamentsBar() {

      const bar = document.getElementById('teamTournamentsBar');

      if (!bar) return;

      const all = DATA.team_tournaments || [];



      bar.innerHTML = all.map(t => {

        const isAct = t.id === selectedTeamTournId;

        return `

          <button class="season-btn ${isAct ? 'active' : ''}" onclick="selectTeamTournament('${t.id}')">

            ${t.title.replace(' по Goal 3', '').replace(' (Эпоха зарождения 2х2)', '')}

          </button>

        `;

      }).join('');

    }



    function renderTeamTournaments() {

      renderTeamTournamentsBar();

      renderTeamTournamentDetails();

    }



    function renderTeamTournamentDetails() {

      const container = document.getElementById('teamTournamentDetailContainer');

      if (!container) return;



      const all = DATA.team_tournaments || [];

      const t = all.find(x => x.id === selectedTeamTournId) || all[0];

      if (!t) return;



      const matches = t.matches || [];

      const divisions = t.divisions || {};



      // Collect all unique team names for filter

      const teamsSet = new Set();

      matches.forEach(m => {

        if (m.t1) teamsSet.add(m.t1);

        if (m.t2) teamsSet.add(m.t2);

      });

      const allTeamsList = Array.from(teamsSet).sort();



      // Filter matches

      const filteredMatches = matches.filter(m => {

        if (teamPairFilter !== 'all') {

          return m.t1 === teamPairFilter || m.t2 === teamPairFilter;

        }

        return true;

      });



      // Master players chips

      const playersChips = (t.key_players || []).map(p => {

        const prof = (DATA.profiles || []).find(x => x.player.toLowerCase() === p.toLowerCase());

        const av = prof ? prof.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p}`;

        return `

          <span class="player-chip-link" onclick="openPlayerModal('${p}')" title="Открыть анкету ${p}">

            <img src="${av}" style="width: 16px; height: 16px; border-radius: 2px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p}'">

            ${p}

          </span>

        `;

      }).join('');



      // Build Sub-Tab content

      let subContentHtml = '';



      // 1. ALL MATCHES SUB-TAB

      if (teamSubTab === 'matches') {

        const pairOptions = allTeamsList.map(pair => `

          <option value="${pair}" ${teamPairFilter === pair ? 'selected' : ''}>${pair}</option>

        `).join('');



        const matchesListHtml = filteredMatches.length > 0 ? filteredMatches.map(m => {

          const isT1Win = m.score.startsWith('5:') || m.score.startsWith('6:') || m.score.startsWith('7:') || m.score.includes('победа t1') || m.score.includes('Победа leon') || m.score.includes('Победа Kamaz') || m.score.includes('Победа ectopower') || m.score.includes('Победа PacnyTHuK') || m.score.includes('Победа Буц');

          

          return `

            <div class="h2h-match-item" style="padding: 12px 16px; margin-bottom: 8px;">

              <div style="display: flex; align-items: center; gap: 8px; flex: 1.2; min-width: 140px;">

                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--nes-gold); font-weight: 800; min-width: 70px;">

                  ${m.tour || 'Матч'}

                </span>

                <span class="league-badge ${m.league && m.league.includes('Высшая') ? 'badge-premier' : (m.league && m.league.includes('Средняя') ? 'badge-middle' : (m.league && m.league.includes('Кубок') ? 'badge-cup' : 'badge-yard'))}" style="font-size: 10px; padding: 2px 6px;">

                  ${m.league || 'Лига'}

                </span>

              </div>

              <div style="display: flex; align-items: center; justify-content: center; gap: 14px; flex: 2; flex-wrap: wrap;">

                <span style="font-family: var(--font-title); font-size: 14px; color: #fff; text-align: right; flex: 1;">

                  ${m.t1}

                </span>

                <div class="score-badge" style="font-size: 15px; padding: 5px 14px; letter-spacing: 1px; font-weight: 900; color: var(--nes-cyan); min-width: 80px; text-align: center;">

                  ${m.score}

                </div>

                <span style="font-family: var(--font-title); font-size: 14px; color: #cbd5e1; text-align: left; flex: 1;">

                  ${m.t2}

                </span>

              </div>

            </div>

          `;

        }).join('') : `

          <div style="background: rgba(0,0,0,0.4); border: 2px dashed #94a3b8; padding: 32px; text-align: center; color: #cbd5e1;">

            Матчи по выбранному фильтру не найдены.

          </div>

        `;



        subContentHtml = `

          <div style="margin-top: 16px;">

            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px;">

              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-cyan);">

                📋 СЫГРАННЫЕ МАТЧИ И СЕРИИ (${filteredMatches.length} из ${matches.length}):

              </div>

              ${allTeamsList.length > 0 ? `

                <div style="display: flex; align-items: center; gap: 8px;">

                  <span style="font-size: 12px; color: #94a3b8; font-weight: 700;">Фильтр по команде:</span>

                  <select class="clean-search" style="padding: 4px 10px; font-size: 12px;" onchange="filterTeamPair(this.value)">

                    <option value="all">▶ Все команды турнира</option>

                    ${pairOptions}

                  </select>

                </div>

              ` : ''}

            </div>

            <div>

              ${matchesListHtml}

            </div>

          </div>

        `;

      }



      // 2. TABLES SUB-TAB

      else if (teamSubTab === 'tables') {

        let divHtml = '';

        if (Object.keys(divisions).length > 0) {

          for (const [divName, rows] of Object.entries(divisions)) {

            const isTop = divName.includes('Высшая');

            divHtml += `

              <div style="margin-bottom: 24px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.15); padding: 16px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: ${isTop ? 'var(--nes-gold)' : 'var(--nes-cyan)'}; margin-bottom: 12px;">

                  🏆 ${divName.toUpperCase()}

                </div>

                <table class="special-table">

                  <thead>

                    <tr>

                      <th>#</th>

                      <th>Команда (Дуэт)</th>

                      ${rows[0]?.games !== undefined ? '<th>Матчи</th>' : ''}

                      ${rows[0]?.w !== undefined ? '<th>В</th>' : ''}

                      ${rows[0]?.l !== undefined ? '<th>П</th>' : ''}

                      ${rows[0]?.pts !== undefined ? '<th>Очки</th>' : ''}

                      ${rows[0]?.result !== undefined ? '<th>Итог</th>' : ''}

                    </tr>

                  </thead>

                  <tbody>

                    ${rows.map((r, i) => `

                      <tr>

                        <td style="color: ${i === 0 ? 'var(--nes-gold)' : (i === 1 ? '#cbd5e1' : (i === 2 ? '#d97706' : '#94a3b8'))}; font-weight: 800;">

                          ${r.rank !== undefined ? r.rank : (i + 1)}

                        </td>

                        <td style="font-weight: 800; color: #fff;">${r.team}</td>

                        ${r.games !== undefined ? `<td style="font-family: var(--font-mono);">${r.games}</td>` : ''}

                        ${r.w !== undefined ? `<td style="font-family: var(--font-mono); color: var(--nes-green); font-weight: 700;">${r.w}</td>` : ''}

                        ${r.l !== undefined ? `<td style="font-family: var(--font-mono); color: var(--nes-red);">${r.l}</td>` : ''}

                        ${r.pts !== undefined ? `<td style="font-family: var(--font-mono); font-weight: 900; color: var(--nes-gold); font-size: 14px;">${r.pts}</td>` : ''}

                        ${r.result !== undefined ? `<td style="font-size: 12px; color: #cbd5e1;">${r.result}</td>` : ''}

                      </tr>

                    `).join('')}

                  </tbody>

                </table>

              </div>

            `;

          }

        } else {

          divHtml = `<div style="padding: 24px; text-align: center; color: #94a3b8;">Таблицы группового этапа не сохранились, смотрите матчи и плей-офф.</div>`;

        }

        subContentHtml = `<div style="margin-top: 16px;">${divHtml}</div>`;

      }



      // 3. PLAYOFF SUB-TAB

      else if (teamSubTab === 'playoff') {
        const rawPlayoff = (t.playoff_matches && t.playoff_matches.length > 0) ? t.playoff_matches : (matches || []).filter(m => {
          const st = (m.tour || m.stage || '').toLowerCase();
          return st.includes('финал') || st.includes('1/2') || st.includes('1/4') || st.includes('место');
        });

        // Deduplicate
        const seenPlayoff = new Set();
        const uniquePlayoff = [];
        rawPlayoff.forEach(m => {
          const k = `${m.t1}_${m.t2}_${m.score}`;
          if (!seenPlayoff.has(k)) {
            seenPlayoff.add(k);
            uniquePlayoff.push(m);
          }
        });

        if (uniquePlayoff.length === 0) {
          subContentHtml = `
            <div style="background: rgba(17, 24, 39, 0.85); border: 2px solid var(--nes-gold); padding: 28px 20px; text-align: center; box-shadow: 4px 4px 0 #000; margin-top: 14px;">
              <div style="font-size: 32px; margin-bottom: 8px;">👥 ⚽</div>
              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-gold); margin-bottom: 8px;">
                КЛУБНЫЙ ГРУППОВОЙ ЭТАП / КРУГОВАЯ СИСТЕМА
              </div>
              <div style="font-size: 13px; color: #cbd5e1; max-width: 600px; margin: 0 auto 16px auto; line-height: 1.6;">
                Все матчи и результаты данного чемпионата представлены в таблицах лиг и вкладке «Все матчи».
              </div>
              <button type="button" class="filter-btn active" style="font-size: 12px; padding: 6px 16px;" onclick="switchTeamSubTab('matches')">
                📋 Посмотреть все матчи турнира
              </button>
            </div>
          `;
        } else {
          // Normalize matches
          const playoffMatches = uniquePlayoff.map(m => {
            const p1 = m.t1 || 'Команда 1';
            const p2 = m.t2 || 'Команда 2';
            let s1 = 0, s2 = 0;
            if (m.score && String(m.score).includes(':')) {
              const parts = String(m.score).split(':');
              s1 = parseInt(parts[0], 10) || 0;
              s2 = parseInt(parts[1], 10) || 0;
            } else if (m.score && String(m.score).toLowerCase().includes('победа')) {
              if (String(m.score).toLowerCase().includes(p1.toLowerCase())) { s1 = 1; s2 = 0; }
              else { s1 = 0; s2 = 1; }
            }
            return {
              p1: p1,
              p2: p2,
              s1: s1,
              s2: s2,
              tour: m.tour || m.stage || 'Плей-офф',
              score: m.score || `${s1}:${s2}`,
              league: m.league || ''
            };
          });

          // Round weighting
          const roundOrderDef = [
            { key: '1/4', label: '1/4 Финала', weight: 1 },
            { key: '1/2', label: 'Полуфинал', weight: 2 },
            { key: '3', label: 'За 3-е место', weight: 3 },
            { key: 'финал', label: 'Гранд-Финал', weight: 4 }
          ];

          function getTeamRoundDef(rName) {
            const rLow = (rName || '').toLowerCase();
            for (const ro of roundOrderDef) {
              if (ro.key === 'финал') {
                if ((rLow.includes('финал') || rLow.includes('final')) && !rLow.includes('1/2') && !rLow.includes('1/4') && !rLow.includes('3')) {
                  return ro;
                }
              } else if (rLow.includes(ro.key) || (ro.key === '1/2' && rLow.includes('полуфинал'))) {
                return ro;
              }
            }
            return { key: rName, label: rName || 'Плей-офф', weight: 99 };
          }

          // Group into rounds
          const roundMap = {};
          playoffMatches.forEach(m => {
            const rDef = getTeamRoundDef(m.tour);
            if (!roundMap[rDef.label]) {
              roundMap[rDef.label] = { def: rDef, matches: [] };
            }
            roundMap[rDef.label].matches.push(m);
          });

          const sortedRounds = Object.values(roundMap).sort((a, b) => a.def.weight - b.def.weight);

          // Champion Info
          let championName = t.champion || null;
          if (championName && championName.includes('/')) {
            championName = championName.split('/')[0].trim();
          }

          // Helper for pair avatars
          function getTeamAvatars(teamName) {
            const parts = teamName.split(/&|\/|\+/).map(x => x.trim()).filter(Boolean);
            return parts.slice(0, 2).map(p => {
              const prof = DATA.profiles.find(x => x.player.toLowerCase() === p.toLowerCase());
              return prof ? prof.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p}`;
            });
          }

          // Visual Bracket HTML
          let roundsHtml = '';
          sortedRounds.forEach(r => {
            const matchups = {};
            r.matches.forEach(m => {
              const pairKey = [m.p1, m.p2].sort().join('__VS__');
              if (!matchups[pairKey]) matchups[pairKey] = [];
              matchups[pairKey].push(m);
            });

            let matchupCardsHtml = '';
            Object.entries(matchups).forEach(([pKey, games]) => {
              const [pA, pB] = pKey.split('__VS__');
              let pAwins = 0, pBwins = 0;
              games.forEach(g => {
                if ((g.p1 === pA && g.s1 > g.s2) || (g.p2 === pA && g.s2 > g.s1)) pAwins++;
                else if ((g.p1 === pB && g.s1 > g.s2) || (g.p2 === pB && g.s2 > g.s1)) pBwins++;
              });

              const isAWinner = pAwins > pBwins;
              const isBWinner = pBwins > pAwins;
              const avsA = getTeamAvatars(pA);
              const avsB = getTeamAvatars(pB);
              const isFinal = r.def.key === 'финал';

              matchupCardsHtml += `
                <div class="bracket-match-card ${isFinal ? 'is-final' : ''}" data-players="${pA.toLowerCase()},${pB.toLowerCase()}">
                  <div class="bracket-card-top">
                    <span style="color: var(--nes-gold);">${r.def.label}</span>
                    <span>${games[0].score || `${pAwins}:${pBwins}`}</span>
                  </div>
                  <div class="bracket-player-row ${(isAWinner ? 'winner' : '')} ${(isBWinner ? 'loser' : '')}" data-player="${pA}" onmouseenter="highlightPlayerBracketPath('${pA}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pA}')">
                    <div class="bracket-p-info">
                      <div style="display: flex; gap: 2px;">
                        ${avsA.map(av => `<img src="${av}" class="bracket-p-avatar" style="width: 18px; height: 18px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=p'">`).join('')}
                      </div>
                      <span class="bracket-p-name" style="font-size: 11px;">${pA}</span>
                      ${isAWinner ? '<span class="bracket-winner-crown">👑</span>' : ''}
                    </div>
                    <span class="bracket-series-score">${pAwins}</span>
                  </div>
                  <div class="bracket-player-row ${(isBWinner ? 'winner' : '')} ${(isAWinner ? 'loser' : '')}" data-player="${pB}" onmouseenter="highlightPlayerBracketPath('${pB}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pB}')">
                    <div class="bracket-p-info">
                      <div style="display: flex; gap: 2px;">
                        ${avsB.map(av => `<img src="${av}" class="bracket-p-avatar" style="width: 18px; height: 18px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=p'">`).join('')}
                      </div>
                      <span class="bracket-p-name" style="font-size: 11px;">${pB}</span>
                      ${isBWinner ? '<span class="bracket-winner-crown">👑</span>' : ''}
                    </div>
                    <span class="bracket-series-score">${pBwins}</span>
                  </div>
                </div>
              `;
            });

            roundsHtml += `
              <div class="bracket-round">
                <div class="bracket-round-header">
                  ${r.def.label} (${Object.keys(matchups).length})
                </div>
                <div class="bracket-round-matches">
                  ${matchupCardsHtml}
                </div>
              </div>
            `;
          });

          // Champion Round
          if (championName) {
            const champAvatars = getTeamAvatars(championName);
            roundsHtml += `
              <div class="bracket-champion-round">
                <div class="bracket-round-header" style="color: var(--nes-gold); border-bottom-color: var(--nes-gold);">
                  🏆 ЧЕМПИОНЫ
                </div>
                <div class="bracket-champion-box" data-player="${championName}" onmouseenter="highlightPlayerBracketPath('${championName}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${championName}')">
                  <div style="font-size: 32px; filter: drop-shadow(0 0 8px #ffcb05); margin-bottom: 6px;">👑</div>
                  <div style="display: flex; justify-content: center; gap: 4px; margin-bottom: 6px;">
                    ${champAvatars.map(av => `<img src="${av}" class="bracket-champ-avatar" style="width: 38px; height: 38px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=champ'">`).join('')}
                  </div>
                  <div class="bracket-champ-name" style="font-size: 13px;">${championName}</div>
                  <div class="bracket-champ-sub">🥇 ПОБЕДИТЕЛИ ЧЕМПИОНАТА 2х2</div>
                  <div style="font-size: 10px; color: var(--nes-cyan); margin-top: 6px; font-weight: 800; text-transform: uppercase;">${t.title}</div>
                </div>
              </div>
            `;
          }

          // Team Pills
          const allTeamsPills = Array.from(new Set(playoffMatches.flatMap(m => [m.p1, m.p2]))).sort();
          const teamPillsHtml = `
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); padding: 8px 12px;">
              <span style="font-size: 11px; font-family: var(--font-title); color: #94a3b8; margin-right: 4px;">👥 Быстрый выбор пути команды:</span>
              ${allTeamsPills.map(tm => `
                <button type="button" class="bracket-player-pill" data-player="${tm}" onmouseenter="highlightPlayerBracketPath('${tm}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${tm}')">
                  ${tm}
                </button>
              `).join('')}
            </div>
          `;

          const visualBracketHtml = `
            <div style="margin-top: 10px;">
              ${teamPillsHtml}
              <div id="teamBracketPathBanner" class="bracket-path-banner">
                <span style="color: #94a3b8;">💡 Наведите на любую команду или нажмите, чтобы проследить её турнирный путь</span>
              </div>
              <div class="bracket-wrapper" id="teamBracketWrapper">
                <svg id="teamBracketSvg" class="bracket-svg"></svg>
                <div class="bracket-container" id="teamBracketContainer">
                  ${roundsHtml}
                </div>
              </div>
            </div>
          `;

          // Flat list
          const flatListHtml = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; margin-top: 12px;">
              ${playoffMatches.map(m => `
                <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); padding: 12px 14px; display: flex; justify-content: space-between; align-items: center;">
                  <div style="flex: 1;">
                    <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">${m.tour || 'Плей-офф'}</div>
                    <div style="font-size: 13px; color: ${m.s1 > m.s2 ? 'var(--nes-gold)' : '#fff'}; font-weight: 800; margin-top: 3px;">${m.p1}</div>
                    <div style="font-size: 13px; color: ${m.s2 > m.s1 ? 'var(--nes-gold)' : '#94a3b8'}; font-weight: 700;">${m.p2}</div>
                  </div>
                  <div class="score-badge" style="font-size: 15px; padding: 5px 12px; font-weight: 900; color: var(--nes-cyan); margin-left: 10px;">
                    ${m.score}
                  </div>
                </div>
              `).join('')}
            </div>
          `;

          subContentHtml = `
            <div style="margin-top: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
                <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold);">
                  ⚡ СЕТКА ПЛЕЙ-ОФФ И ИТОГИ 2х2:
                </div>
                <div style="display: flex; gap: 6px;">
                  <button type="button" class="filter-btn ${teamPlayoffViewMode === 'bracket' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setTeamPlayoffViewMode('bracket')">
                    ⚡ Турнирная сетка
                  </button>
                  <button type="button" class="filter-btn ${teamPlayoffViewMode === 'list' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setTeamPlayoffViewMode('list')">
                    📋 Список всех игр (${playoffMatches.length})
                  </button>
                </div>
              </div>
              ${teamPlayoffViewMode === 'bracket' ? visualBracketHtml : flatListHtml}
            </div>
          `;
        }
      }

      else if (teamSubTab === 'about') {

        const fullChronicleParas = (t.full_chronicle || t.summary || t.description || '').split(String.fromCharCode(10) + String.fromCharCode(10)).filter(Boolean);

        const keyEvents = t.key_events || [];

        const wallQuotes = t.wall_quotes || [];

        const vkTopicUrl = t.topic_id ? `https://vk.ru/topic-66162180_${t.topic_id}` : null;

        const vkWallUrl = t.wall_post_id ? `https://vk.ru/wall-66162180_${t.wall_post_id}` : null;



        subContentHtml = `

          <div style="margin-top: 16px; display: flex; flex-direction: column; gap: 20px;">

            <!-- Era Banner & Primary Links -->

            <div style="background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(0,0,0,0.6)); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000;">

              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">

                <div>

                  <div style="font-size: 11px; font-family: var(--font-mono); color: var(--nes-gold); font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px;">

                    📜 ЛЕТОПИСЬ КОМАНДНОГО ЧЕМПИОНАТА 2х2

                  </div>

                  <div style="font-family: var(--font-title); font-size: 20px; color: #fff; margin-bottom: 8px;">

                    ${t.era_title || t.title} (${t.season_year || t.year || ''})

                  </div>

                  <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: #cbd5e1;">

                    ${(t.organizers || t.organizer) ? `<span>👑 <strong>Организатор:</strong> ${t.organizers || t.organizer}</span>` : ''}

                    ${t.prize_pool ? `<span>💰 <strong>Призовой фонд:</strong> <strong style="color: var(--nes-gold);">${t.prize_pool}</strong></span>` : ''}

                    <span>🎮 <strong>Платформа:</strong> ${t.emulator || t.game || 'Nestopia / Mednafen'}</span>

                    <span>🏆 <strong>Формат:</strong> ${t.format || 'Командный 2х2'}</span>

                  </div>

                </div>

                <div style="display: flex; gap: 8px; flex-wrap: wrap;">

                  ${vkTopicUrl ? `

                    <a href="${vkTopicUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #2563eb; color: #fff; border: 1px solid #60a5fa; display: inline-flex; align-items: center; gap: 6px;">

                      💬 Тема обсуждения в VK

                    </a>

                  ` : ''}

                  ${vkWallUrl ? `

                    <a href="${vkWallUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #059669; color: #fff; border: 1px solid #34d399; display: inline-flex; align-items: center; gap: 6px;">

                      📰 Итоги на стене VK

                    </a>

                  ` : ''}

                </div>

              </div>

            </div>



            <!-- Historical Chronicle Text -->

            <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 22px;">

              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-cyan); margin-bottom: 14px;">

                📖 ХРОНИКА И ПАРНЫЕ СРАЖЕНИЯ

              </div>

              <div style="color: #e2e8f0; font-size: 14px; line-height: 1.7; display: flex; flex-direction: column; gap: 14px;">

                ${fullChronicleParas.map(p => `<p style="margin: 0; text-align: justify;">${p}</p>`).join('')}

              </div>

            </div>



            <!-- Key Milestones -->

            ${keyEvents.length > 0 ? `

              <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  ⚡ КЛЮЧЕВЫЕ МОМЕНТЫ ТУРНИРА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 10px;">

                  ${keyEvents.map(evt => `

                    <div style="background: rgba(255,255,255,0.04); border-left: 3px solid var(--nes-gold); padding: 10px 14px; font-size: 13px; color: #cbd5e1; line-height: 1.5;">

                      ${evt}

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}



            <!-- Quotes of the Epoch -->

            ${wallQuotes.length > 0 ? `

              <div style="background: rgba(255, 183, 3, 0.04); border: 1px dashed var(--nes-gold); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  💬 АТМОСФЕРА И ЦИТАТЫ ТУРНИРА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px;">

                  ${wallQuotes.map(q => `

                    <div style="background: rgba(0,0,0,0.4); border-left: 3px solid var(--nes-cyan); padding: 12px 14px;">

                      <div style="font-size: 13px; color: #f1f5f9; font-style: italic; line-height: 1.5; margin-bottom: 6px;">

                        «${q.text}»

                      </div>

                      <div style="font-size: 11px; color: var(--nes-cyan); font-weight: 800; text-align: right;">

                        &mdash; ${q.author}

                      </div>

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}

          </div>

        `;

      }



      container.innerHTML = `

        <div class="special-card" style="border-color: var(--nes-cyan); box-shadow: 4px 4px 0px #000;">

          <!-- Header Row -->

          <div class="special-header-row">

            <div>

              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px;">

                <span class="special-tag tag-solo" style="background: #1e3a8a; color: #93c5fd; border-color: #3b82f6;">👥 2x2 КОМАНДНЫЙ ЧЕМПИОНАТ</span>

                <span style="font-size: 12px; color: var(--nes-gold); font-weight: 800; font-family: var(--font-mono);">${t.season_year}</span>

                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>

                <span style="font-size: 11px; color: #cbd5e1; font-weight: 700;">${t.game}</span>

                ${t.organizer ? `<span style="font-size: 11px; color: #94a3b8;">&bull;</span><span style="font-size: 11px; color: var(--nes-cyan);">Орг: ${t.organizer}</span>` : ''}

                ${t.prize_pool ? `<span style="font-size: 11px; color: var(--nes-gold); background: rgba(255,183,3,0.15); padding: 2px 6px; border: 1px solid var(--nes-gold);">💰 Фонд: ${t.prize_pool}</span>` : ''}

              </div>

              <h2 style="font-family: var(--font-title); font-size: 22px; color: #fff; margin: 0; ">

                ${t.title}

              </h2>

            </div>

          </div>



          <!-- Podium Box -->

          <div class="podium-box-grid">

            <div class="podium-slot gold">

              <span style="font-size: 24px;">🥇</span>

              <div>

                <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">1 МЕСТО &bull; ЧЕМПИОНЫ</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.champion}</div>

              </div>

            </div>

            <div class="podium-slot silver">

              <span style="font-size: 24px;">🥈</span>

              <div>

                <div style="font-size: 10px; color: #cbd5e1; font-weight: 800; text-transform: uppercase;">2 МЕСТО &bull; СЕРЕБРО</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.runner_up}</div>

              </div>

            </div>

            <div class="podium-slot bronze">

              <span style="font-size: 24px;">🥉</span>

              <div>

                <div style="font-size: 10px; color: #d97706; font-weight: 800; text-transform: uppercase;">3 МЕСТО &bull; БРОНЗА</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.bronze || '—'}</div>

              </div>

            </div>

          </div>



          <!-- Key Master Players -->

          ${playersChips ? `

            <div style="margin: 12px 0 16px 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">

              <span style="font-size: 11px; color: #94a3b8; font-weight: 700;">Мастера лиги в турнире:</span>

              ${playersChips}

            </div>

          ` : ''}



          <!-- Tournament Sub-Navigation Buttons (Tabs) -->

          <div style="display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 2px solid rgba(255,255,255,0.2); padding-bottom: 12px; margin-top: 16px;">

            <button class="filter-btn ${teamSubTab === 'matches' ? 'active' : ''}" onclick="switchTeamSubTab('matches')">

              📋 Все матчи турнира (${matches.length})

            </button>

            <button class="filter-btn ${teamSubTab === 'tables' ? 'active' : ''}" onclick="switchTeamSubTab('tables')">

              🏆 Таблицы лиг

            </button>

            <button class="filter-btn ${teamSubTab === 'playoff' ? 'active' : ''}" onclick="switchTeamSubTab('playoff')">

              ⚡ Сетка плей-офф

            </button>

            <button class="filter-btn ${teamSubTab === 'about' ? 'active' : ''}" onclick="switchTeamSubTab('about')">

              📜 Описание и история

            </button>

          </div>



          <!-- Active Sub-Tab Content -->

          ${subContentHtml}

        </div>

      `;

      if (teamSubTab === 'playoff' && teamPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('teamBracketWrapper', 'teamBracketContainer', 'teamBracketSvg'), 60);
      }

    }



    let selectedSpecialTournId = 'youth_championship_2';

    let specialSubTab = 'matches';

    let specialPlayerFilter = 'all';



    function selectSpecialTournament(id) {

      selectedSpecialTournId = id;

      specialPlayerFilter = 'all';

      renderSpecialTournamentsBar();

      renderSpecialTournamentDetails();

    }



    function switchSpecialSubTab(subTab) {

      specialSubTab = subTab;

      renderSpecialTournamentDetails();

    }



    function filterSpecialPlayer(p) {

      specialPlayerFilter = p;

      renderSpecialTournamentDetails();

    }



    function renderSpecialTournamentsBar() {

      const bar = document.getElementById('specialTournamentsBar');

      if (!bar) return;

      const all = DATA.special_tournaments || [];



      bar.innerHTML = all.map(t => {

        const isAct = t.id === selectedSpecialTournId;

        let shortName = t.title;

        if (t.id === 'youth_championship_2') shortName = '🌱 2-й Молодёжный';

        else if (t.id === 'club_offseason_goal4') shortName = '🏖️ Межсезонье Goal 4';

        else if (t.id === 'solo_goal3_autumn_2021') shortName = '🎯 Соло Осень 2021';

        else if (t.id === 'penalty_tournament_3') shortName = '🥅 Пенальти 3';

        else if (t.id === 'penalty_tournament_2') shortName = '🥅 Пенальти 2';

        else if (t.id === 'blitz_10') shortName = '⚡ Блиц X';

        else if (t.id === 'blitz_9') shortName = '⚡ Блиц IX';

        else if (t.id === 'blitz_12') shortName = '⚡ Блиц XII';

        else if (t.id === 'goal4_solo_ladder') shortName = '🧗 Ладдер Goal 4';



        return `

          <button class="season-btn ${isAct ? 'active' : ''}" onclick="selectSpecialTournament('${t.id}')">

            ${shortName}

          </button>

        `;

      }).join('');

    }



    function renderSpecialTournaments() {

      renderSpecialTournamentsBar();

      renderSpecialTournamentDetails();

    }



    function renderSpecialTournamentDetails() {

      const container = document.getElementById('specialTournamentDetailContainer');

      if (!container) return;



      const all = DATA.special_tournaments || [];

      const t = all.find(x => x.id === selectedSpecialTournId) || all[0];

      if (!t) return;



      const matches = t.matches || [];



      // Collect all unique participant names for filter

      const pSet = new Set();

      matches.forEach(m => {

        if (m.p1) pSet.add(m.p1);

        if (m.p2) pSet.add(m.p2);

      });

      const allPlayersList = Array.from(pSet).sort();



      // Filter matches

      const filteredMatches = matches.filter(m => {

        if (specialPlayerFilter !== 'all') {

          return m.p1 === specialPlayerFilter || m.p2 === specialPlayerFilter;

        }

        return true;

      });



      // Master players chips

      const playersChips = (t.key_players || []).map(p => {

        const prof = (DATA.profiles || []).find(x => x.player.toLowerCase() === p.toLowerCase());

        const av = prof ? prof.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p}`;

        return `

          <span class="player-chip-link" onclick="openPlayerModal('${p}')" title="Открыть анкету ${p}">

            <img src="${av}" style="width: 16px; height: 16px; border-radius: 2px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p}'">

            ${p}

          </span>

        `;

      }).join('');



      let tagClass = 'tag-solo';

      if (t.category.includes('Молодёж')) tagClass = 'tag-youth';

      else if (t.category.includes('Межсез')) tagClass = 'tag-offseason';

      else if (t.title.toLowerCase().includes('пенальт')) tagClass = 'tag-penalty';

      else if (t.title.toLowerCase().includes('блиц')) tagClass = 'tag-blitz';

      else if (t.id.includes('ladder')) tagClass = 'tag-ladder';



      // Build Sub-Tab content

      let subContentHtml = '';



      // 1. ALL MATCHES SUB-TAB

      if (specialSubTab === 'matches') {

        const playerOptions = allPlayersList.map(pName => `

          <option value="${pName}" ${specialPlayerFilter === pName ? 'selected' : ''}>${pName}</option>

        `).join('');



        const matchesListHtml = filteredMatches.length > 0 ? filteredMatches.map(m => {

          const p1Low = (m.p1 || '').toLowerCase();

          const p2Low = (m.p2 || '').toLowerCase();

          const prof1 = DATA.profiles.find(x => x.player.toLowerCase() === p1Low);

          const prof2 = DATA.profiles.find(x => x.player.toLowerCase() === p2Low);

          const av1 = prof1 ? prof1.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.p1}`;

          const av2 = prof2 ? prof2.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.p2}`;



          return `

            <div class="h2h-match-item" style="padding: 12px 16px; margin-bottom: 8px;">

              <div style="display: flex; align-items: center; gap: 8px; flex: 1.2; min-width: 140px;">

                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--nes-gold); font-weight: 800; min-width: 70px;">

                  ${m.tour || m.stage || 'Матч'}

                </span>

                <span class="league-badge ${m.league && m.league.includes('Высшая') ? 'badge-premier' : (m.league && m.league.includes('Средняя') ? 'badge-middle' : (m.league && m.league.includes('Кубок') ? 'badge-cup' : 'badge-yard'))}" style="font-size: 10px; padding: 2px 6px;">

                  ${m.league || 'Спецтурнир'}

                </span>

              </div>

              <div style="display: flex; align-items: center; justify-content: center; gap: 14px; flex: 2; flex-wrap: wrap;">

                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p1}')">

                  <span style="font-family: var(--font-title); font-size: 14px; color: #fff; text-align: right;">${m.p1}</span>

                  <img src="${av1}" style="width: 24px; height: 24px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.p1}'">

                </div>

                <div class="score-badge" style="font-size: 15px; padding: 5px 14px; letter-spacing: 1px; font-weight: 900; color: var(--nes-cyan); min-width: 80px; text-align: center;">

                  ${m.score}

                </div>

                <div style="display: flex; align-items: center; justify-content: flex-start; gap: 8px; flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p2}')">

                  <img src="${av2}" style="width: 24px; height: 24px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.p2}'">

                  <span style="font-family: var(--font-title); font-size: 14px; color: #cbd5e1; text-align: left;">${m.p2}</span>

                </div>

              </div>

            </div>

          `;

        }).join('') : `

          <div style="background: rgba(0,0,0,0.4); border: 2px dashed #94a3b8; padding: 32px; text-align: center; color: #cbd5e1;">

            Матчи по выбранному фильтру не найдены.

          </div>

        `;



        subContentHtml = `

          <div style="margin-top: 16px;">

            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px;">

              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-cyan);">

                📋 СЫГРАННЫЕ МАТЧИ (${filteredMatches.length} из ${matches.length}):

              </div>

              ${allPlayersList.length > 0 ? `

                <div style="display: flex; align-items: center; gap: 8px;">

                  <span style="font-size: 12px; color: #94a3b8; font-weight: 700;">Фильтр по участнику:</span>

                  <select class="clean-search" style="padding: 4px 10px; font-size: 12px;" onchange="filterSpecialPlayer(this.value)">

                    <option value="all">▶ Все участники турнира</option>

                    ${playerOptions}

                  </select>

                </div>

              ` : ''}

            </div>

            <div>

              ${matchesListHtml}

            </div>

          </div>

        `;

      }



      // 2. TABLES SUB-TAB

      else if (specialSubTab === 'tables') {

        let divHtml = '';

        if (t.groups) {

          divHtml = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 20px;">';

          for (const [gName, rows] of Object.entries(t.groups)) {

            divHtml += `

              <div style="background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.15); padding: 14px;">

                <div style="font-family: var(--font-title); font-size: 13px; color: var(--nes-cyan); margin-bottom: 10px;">ГРУППА «${gName.toUpperCase()}»</div>

                <table class="special-table">

                  <thead>

                    <tr><th>#</th><th>Команда (Пара)</th><th>И</th><th>В</th><th>П</th><th>О</th></tr>

                  </thead>

                  <tbody>

                    ${rows.map((r, i) => `

                      <tr>

                        <td style="color: ${i < 4 ? 'var(--nes-gold)' : '#94a3b8'}; font-weight: 800;">${i + 1}</td>

                        <td style="font-weight: 700; color: #fff;">${r.team}</td>

                        <td style="font-family: var(--font-mono);">${r.games}</td>

                        <td style="font-family: var(--font-mono); color: var(--nes-green);">${r.w + (r.wp || 0)}</td>

                        <td style="font-family: var(--font-mono); color: var(--nes-red);">${r.l + (r.lp || 0)}</td>

                        <td style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold);">${r.pts}</td>

                      </tr>

                    `).join('')}

                  </tbody>

                </table>

              </div>

            `;

          }

          divHtml += '</div>';

        } else if (t.premier_league) {

          divHtml = `

            <div style="margin-bottom: 18px;">

              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold); margin-bottom: 8px;">🏆 ПРЕМЬЕР-ЛИГА КЛУБОВ (ОСНОВНЫЕ СОСТАВЫ ЗВЁЗД)</div>

              <table class="special-table">

                <thead>

                  <tr><th>#</th><th>Клуб</th><th>Состав звёзд</th><th>Баттлы</th><th>Матчи</th><th>В-П</th><th>Мячи</th><th>+/-</th><th>Очки</th></tr>

                </thead>

                <tbody>

                  ${t.premier_league.map((c, i) => `

                    <tr>

                      <td style="color: ${i === 0 ? 'var(--nes-gold)' : (i === 1 ? '#cbd5e1' : '#94a3b8')}; font-weight: 800;">${i + 1}</td>

                      <td style="font-weight: 800; color: #fff;">${c.club}</td>

                      <td style="font-size: 11px; color: #cbd5e1;">${c.roster}</td>

                      <td style="font-family: var(--font-mono);">${c.battles}</td>

                      <td style="font-family: var(--font-mono);">${c.games}</td>

                      <td style="font-family: var(--font-mono); color: var(--nes-green);">${c.gw}-${c.gl}</td>

                      <td style="font-family: var(--font-mono);">${c.gf}:${c.ga}</td>

                      <td style="font-family: var(--font-mono); color: ${c.diff.startsWith('+') ? 'var(--nes-cyan)' : '#f87171'};">${c.diff}</td>

                      <td style="font-family: var(--font-mono); font-weight: 900; color: var(--nes-gold); font-size: 14px;">${c.pts}</td>

                    </tr>

                  `).join('')}

                </tbody>

              </table>

            </div>

            <div>

              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-cyan); margin-bottom: 8px;">🌱 МОЛОДЁЖНАЯ ЛИГА КЛУБОВ (ДУБЛИ И МОЛОДЁЖКА)</div>

              <table class="special-table">

                <thead>

                  <tr><th>#</th><th>Клуб</th><th>Молодёжный состав</th><th>Баттлы</th><th>Матчи</th><th>В-П</th><th>Мячи</th><th>+/-</th><th>Очки</th></tr>

                </thead>

                <tbody>

                  ${(t.youth_league || []).map((c, i) => `

                    <tr>

                      <td style="color: ${i === 0 ? 'var(--nes-cyan)' : '#94a3b8'}; font-weight: 800;">${i + 1}</td>

                      <td style="font-weight: 800; color: #fff;">${c.club}</td>

                      <td style="font-size: 11px; color: #cbd5e1;">${c.roster}</td>

                      <td style="font-family: var(--font-mono);">${c.battles}</td>

                      <td style="font-family: var(--font-mono);">${c.games}</td>

                      <td style="font-family: var(--font-mono); color: var(--nes-green);">${c.gw}-${c.gl}</td>

                      <td style="font-family: var(--font-mono);">${c.gf}:${c.ga}</td>

                      <td style="font-family: var(--font-mono); color: ${c.diff.startsWith('+') ? 'var(--nes-cyan)' : '#f87171'};">${c.diff}</td>

                      <td style="font-family: var(--font-mono); font-weight: 900; color: var(--nes-cyan); font-size: 14px;">${c.pts}</td>

                    </tr>

                  `).join('')}

                </tbody>

              </table>

            </div>

          `;

        } else if (t.ladder) {

          divHtml = `

            <table class="special-table">

              <thead>

                <tr><th>Ранг</th><th>Игрок</th><th>Серия / Рекорд</th><th>Статус</th></tr>

              </thead>

              <tbody>

                ${t.ladder.map(p => `

                  <tr>

                    <td style="font-weight: 800; color: var(--nes-gold); font-family: var(--font-mono);">${p.rank}</td>

                    <td style="font-weight: 800; color: #fff;">${p.player}</td>

                    <td style="font-family: var(--font-mono); color: var(--nes-cyan);">${p.record}</td>

                    <td style="font-size: 11px; color: #94a3b8;">${p.status}</td>

                  </tr>

                `).join('')}

              </tbody>

            </table>

          `;

        } else {

          divHtml = `<div style="padding: 24px; text-align: center; color: #94a3b8;">В данном турнире отсутствуют круговые таблицы (турнир проводился по сетке плей-офф).</div>`;

        }

        subContentHtml = `<div style="margin-top: 16px;">${divHtml}</div>`;

      }



      // 3. PLAYOFF SUB-TAB

      else if (specialSubTab === 'playoff') {
        const rawPlayoff = (t.playoff && t.playoff.length > 0) ? t.playoff : (t.matches || []).filter(m => {
          const st = (m.stage || m.tour || '').toLowerCase();
          return st.includes('финал') || st.includes('1/') || st.includes('winners') || st.includes('losers') || st.includes('раунд');
        });

        if (rawPlayoff.length === 0) {
          subContentHtml = `
            <div style="background: rgba(17, 24, 39, 0.85); border: 2px solid var(--nes-gold); padding: 28px 20px; text-align: center; box-shadow: 4px 4px 0 #000; margin-top: 14px;">
              <div style="font-size: 32px; margin-bottom: 8px;">🧗 🏖️</div>
              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-gold); margin-bottom: 8px;">
                КЛУБНЫЙ ФОРМАТ / ЛАДДЕР (БЕЗ ОЛИМПИЙСКОЙ СЕТКИ)
              </div>
              <div style="font-size: 13px; color: #cbd5e1; max-width: 600px; margin: 0 auto 16px auto; line-height: 1.6;">
                Данный турнир проводился по групповой системе или рейтинговой лестнице (Ladder). 
                Все встречи и результаты зафиксированы во вкладке «Все матчи».
              </div>
              <button type="button" class="filter-btn active" style="font-size: 12px; padding: 6px 16px;" onclick="switchSpecialSubTab('matches')">
                📋 Посмотреть все матчи турнира
              </button>
            </div>
          `;
        } else {
          // Normalize special playoff matches
          const playoffMatches = rawPlayoff.map(m => {
            const p1 = m.p1 || m.t1 || 'Игрок 1';
            const p2 = m.p2 || m.t2 || 'Игрок 2';
            let s1 = 0, s2 = 0;
            if (typeof m.s1 === 'number' && typeof m.s2 === 'number') {
              s1 = m.s1; s2 = m.s2;
            } else if (m.score && String(m.score).includes(':')) {
              const parts = String(m.score).split(':');
              s1 = parseInt(parts[0], 10) || 0;
              s2 = parseInt(parts[1], 10) || 0;
            } else if (m.score && String(m.score).toLowerCase().includes('победа')) {
              if (String(m.score).toLowerCase().includes(p1.toLowerCase())) { s1 = 1; s2 = 0; }
              else { s1 = 0; s2 = 1; }
            }
            return {
              p1: p1,
              p2: p2,
              s1: s1,
              s2: s2,
              tour: m.stage || m.tour || 'Плей-офф',
              games: m.games || '',
              score: m.score || `${s1}:${s2}`
            };
          });

          // Standard round weighting
          const roundOrderDef = [
            { key: '1/16', label: '1/16 Финала', weight: 1 },
            { key: '1/8', label: '1/8 Финала', weight: 2 },
            { key: '1/4', label: '1/4 Финала', weight: 3 },
            { key: '1/2', label: 'Полуфинал', weight: 4 },
            { key: '3', label: 'За 3-е место', weight: 5 },
            { key: 'финал', label: 'Гранд-Финал', weight: 6 }
          ];

          function getSpecialRoundDef(rName) {
            const rLow = (rName || '').toLowerCase();
            for (const ro of roundOrderDef) {
              if (ro.key === 'финал') {
                if ((rLow.includes('финал') || rLow.includes('final')) && !rLow.includes('1/16') && !rLow.includes('1/8') && !rLow.includes('1/4') && !rLow.includes('1/2') && !rLow.includes('3')) {
                  return ro;
                }
              } else if (rLow.includes(ro.key) || (ro.key === '1/2' && rLow.includes('полуфинал'))) {
                return ro;
              }
            }
            return { key: rName, label: rName || 'Плей-офф', weight: 99 };
          }

          // Group matches into rounds
          const roundMap = {};
          playoffMatches.forEach(m => {
            const rDef = getSpecialRoundDef(m.tour);
            if (!roundMap[rDef.label]) {
              roundMap[rDef.label] = { def: rDef, matches: [] };
            }
            roundMap[rDef.label].matches.push(m);
          });

          const sortedRounds = Object.values(roundMap).sort((a, b) => a.def.weight - b.def.weight);

          // Determine Champion
          let championName = t.champion || null;
          if (championName && championName.includes('/')) {
            championName = championName.split('/')[0].trim();
          }
          const champProf = championName ? DATA.profiles.find(x => x.player.toLowerCase() === championName.toLowerCase()) : null;
          const champAvatar = champProf ? champProf.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${championName || 'champ'}`;

          // Visual Bracket HTML
          let roundsHtml = '';
          sortedRounds.forEach(r => {
            const matchups = {};
            r.matches.forEach(m => {
              const pairKey = [m.p1, m.p2].sort().join('__VS__');
              if (!matchups[pairKey]) matchups[pairKey] = [];
              matchups[pairKey].push(m);
            });

            let matchupCardsHtml = '';
            Object.entries(matchups).forEach(([pKey, games]) => {
              const [pA, pB] = pKey.split('__VS__');
              let pAwins = 0, pBwins = 0;
              games.forEach(g => {
                if ((g.p1 === pA && g.s1 > g.s2) || (g.p2 === pA && g.s2 > g.s1)) pAwins++;
                else if ((g.p1 === pB && g.s1 > g.s2) || (g.p2 === pB && g.s2 > g.s1)) pBwins++;
              });

              const isAWinner = pAwins > pBwins;
              const isBWinner = pBwins > pAwins;
              const profA = DATA.profiles.find(x => x.player.toLowerCase() === pA.toLowerCase());
              const profB = DATA.profiles.find(x => x.player.toLowerCase() === pB.toLowerCase());
              const avA = profA ? profA.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pA}`;
              const avB = profB ? profB.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pB}`;
              const isFinal = r.def.key === 'финал';

              matchupCardsHtml += `
                <div class="bracket-match-card ${isFinal ? 'is-final' : ''}" data-players="${pA.toLowerCase()},${pB.toLowerCase()}">
                  <div class="bracket-card-top">
                    <span style="color: var(--nes-gold);">${r.def.label}</span>
                    <span>${games[0].score || `${pAwins}:${pBwins}`}</span>
                  </div>
                  <div class="bracket-player-row ${(isAWinner ? 'winner' : '')} ${(isBWinner ? 'loser' : '')}" data-player="${pA}" onmouseenter="highlightPlayerBracketPath('${pA}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pA}')">
                    <div class="bracket-p-info">
                      <img src="${avA}" class="bracket-p-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${pA}'">
                      <span class="bracket-p-name">${pA}</span>
                      ${isAWinner ? '<span class="bracket-winner-crown">👑</span>' : ''}
                    </div>
                    <span class="bracket-series-score">${pAwins}</span>
                  </div>
                  <div class="bracket-player-row ${(isBWinner ? 'winner' : '')} ${(isAWinner ? 'loser' : '')}" data-player="${pB}" onmouseenter="highlightPlayerBracketPath('${pB}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pB}')">
                    <div class="bracket-p-info">
                      <img src="${avB}" class="bracket-p-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${pB}'">
                      <span class="bracket-p-name">${pB}</span>
                      ${isBWinner ? '<span class="bracket-winner-crown">👑</span>' : ''}
                    </div>
                    <span class="bracket-series-score">${pBwins}</span>
                  </div>
                  ${games[0].games ? `
                    <div style="font-size: 10px; color: var(--nes-cyan); padding: 4px 10px; background: rgba(0,0,0,0.3); border-top: 1px solid rgba(255,255,255,0.06); font-family: var(--font-mono);">
                      ${games[0].games}
                    </div>
                  ` : ''}
                </div>
              `;
            });

            roundsHtml += `
              <div class="bracket-round">
                <div class="bracket-round-header">
                  ${r.def.label} (${Object.keys(matchups).length})
                </div>
                <div class="bracket-round-matches">
                  ${matchupCardsHtml}
                </div>
              </div>
            `;
          });

          // Champion Round
          if (championName) {
            roundsHtml += `
              <div class="bracket-champion-round">
                <div class="bracket-round-header" style="color: var(--nes-gold); border-bottom-color: var(--nes-gold);">
                  🏆 ЧЕМПИОН
                </div>
                <div class="bracket-champion-box" data-player="${championName}" onmouseenter="highlightPlayerBracketPath('${championName}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${championName}')">
                  <div style="font-size: 32px; filter: drop-shadow(0 0 8px #ffcb05); margin-bottom: 6px;">👑</div>
                  <img src="${champAvatar}" class="bracket-champ-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${championName}'">
                  <div class="bracket-champ-name" onclick="openPlayerModal('${championName}')">${championName}</div>
                  <div class="bracket-champ-sub">🥇 ПОБЕДИТЕЛЬ ТУРНИРА</div>
                  <div style="font-size: 10px; color: var(--nes-cyan); margin-top: 6px; font-weight: 800; text-transform: uppercase;">${t.title}</div>
                </div>
              </div>
            `;
          }

          // Participant Pills
          const allSpecialParticipants = Array.from(new Set(playoffMatches.flatMap(m => [m.p1, m.p2]))).sort();
          const playerPillsHtml = `
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); padding: 8px 12px;">
              <span style="font-size: 11px; font-family: var(--font-title); color: #94a3b8; margin-right: 4px;">🎯 Быстрый выбор турнирного пути:</span>
              ${allSpecialParticipants.map(p => `
                <button type="button" class="bracket-player-pill" data-player="${p}" onmouseenter="highlightPlayerBracketPath('${p}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${p}')">
                  ${p}
                </button>
              `).join('')}
            </div>
          `;

          const visualBracketHtml = `
            <div style="margin-top: 10px;">
              ${playerPillsHtml}
              <div id="specialBracketPathBanner" class="bracket-path-banner">
                <span style="color: #94a3b8;">💡 Наведите на любого участника или нажмите, чтобы проследить его путь по сетке</span>
              </div>
              <div class="bracket-wrapper" id="specialBracketWrapper">
                <svg id="specialBracketSvg" class="bracket-svg"></svg>
                <div class="bracket-container" id="specialBracketContainer">
                  ${roundsHtml}
                </div>
              </div>
            </div>
          `;

          // Flat list
          const flatListHtml = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; margin-top: 12px;">
              ${playoffMatches.map(m => `
                <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); padding: 12px 14px; display: flex; justify-content: space-between; align-items: center;">
                  <div style="flex: 1;">
                    <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">${m.tour || 'Плей-офф'}</div>
                    <div style="font-size: 13px; color: ${m.s1 > m.s2 ? 'var(--nes-gold)' : '#fff'}; font-weight: 800; margin-top: 3px;">${m.p1}</div>
                    <div style="font-size: 13px; color: ${m.s2 > m.s1 ? 'var(--nes-gold)' : '#94a3b8'}; font-weight: 700;">${m.p2}</div>
                    ${m.games ? `<div style="font-size: 10px; color: var(--nes-cyan); margin-top: 2px;">Сеты: ${m.games}</div>` : ''}
                  </div>
                  <div class="score-badge" style="font-size: 15px; padding: 5px 12px; font-weight: 900; color: var(--nes-cyan); margin-left: 10px;">
                    ${m.score}
                  </div>
                </div>
              `).join('')}
            </div>
          `;

          subContentHtml = `
            <div style="margin-top: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
                <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold);">
                  ⚡ СЕТКА ПЛЕЙ-ОФФ И ИТОГИ КУБКА:
                </div>
                <div style="display: flex; gap: 6px;">
                  <button type="button" class="filter-btn ${specialPlayoffViewMode === 'bracket' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setSpecialPlayoffViewMode('bracket')">
                    ⚡ Турнирная сетка
                  </button>
                  <button type="button" class="filter-btn ${specialPlayoffViewMode === 'list' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setSpecialPlayoffViewMode('list')">
                    📋 Список всех игр (${playoffMatches.length})
                  </button>
                </div>
              </div>
              ${specialPlayoffViewMode === 'bracket' ? visualBracketHtml : flatListHtml}
            </div>
          `;
        }
      }

      else if (specialSubTab === 'about') {
        subContentHtml = `

          <div style="margin-top: 16px; display: flex; flex-direction: column; gap: 20px;">

            <!-- Era Banner & Primary Links -->

            <div style="background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(0,0,0,0.6)); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000;">

              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">

                <div>

                  <div style="font-size: 11px; font-family: var(--font-mono); color: var(--nes-gold); font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px;">

                    📜 ЛЕТОПИСЬ СПЕЦТУРНИРА

                  </div>

                  <div style="font-family: var(--font-title); font-size: 20px; color: #fff; margin-bottom: 8px;">

                    ${t.title} (${t.season_year || t.year || ''})

                  </div>

                  <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: #cbd5e1;">

                    <span>Категория: <strong style="color: var(--nes-gold);">${t.category}</strong></span>

                    <span>Формат: <strong style="color: var(--nes-cyan);">${t.format}</strong></span>

                    <span>Дисциплина: <strong style="color: #fff;">${t.game}</strong></span>

                  </div>

                </div>

                <div style="display: flex; gap: 8px; flex-wrap: wrap;">

                  ${vkTopicUrl ? `

                    <a href="${vkTopicUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #2563eb; color: #fff; border: 1px solid #60a5fa; display: inline-flex; align-items: center; gap: 6px;">

                      💬 Тема в VK

                    </a>

                  ` : ''}

                  ${vkWallUrl ? `

                    <a href="${vkWallUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #059669; color: #fff; border: 1px solid #34d399; display: inline-flex; align-items: center; gap: 6px;">

                      📰 Пост в VK

                    </a>

                  ` : ''}

                </div>

              </div>

            </div>



            <!-- Historical Chronicle Text -->

            <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 22px;">

              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-cyan); margin-bottom: 14px;">

                📖 ХРОНИКА И РЕГЛАМЕНТ

              </div>

              <div style="color: #e2e8f0; font-size: 14px; line-height: 1.7; display: flex; flex-direction: column; gap: 14px;">

                ${fullChronicleParas.map(p => `<p style="margin: 0; text-align: justify;">${p}</p>`).join('')}

              </div>

            </div>



            <!-- Key Milestones -->

            ${keyEvents.length > 0 ? `

              <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  ⚡ КЛЮЧЕВЫЕ МОМЕНТЫ ТУРНИРА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 10px;">

                  ${keyEvents.map(evt => `

                    <div style="background: rgba(255,255,255,0.04); border-left: 3px solid var(--nes-gold); padding: 10px 14px; font-size: 13px; color: #cbd5e1; line-height: 1.5;">

                      ${evt}

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}

          </div>

        `;

      }



      container.innerHTML = `

        <div class="special-card" style="border-color: var(--nes-cyan); box-shadow: 4px 4px 0px #000;">

          <!-- Header Row -->

          <div class="special-header-row">

            <div>

              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px;">

                <span class="special-tag ${tagClass}">${t.category}</span>

                <span style="font-size: 12px; color: var(--nes-gold); font-weight: 800; font-family: var(--font-mono);">${t.season_year}</span>

                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>

                <span style="font-size: 11px; color: #cbd5e1; font-weight: 700;">${t.game}</span>

                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>

                <span style="font-size: 11px; color: var(--nes-cyan);">${t.format}</span>

              </div>

              <h2 style="font-family: var(--font-title); font-size: 22px; color: #fff; margin: 0; ">

                ${t.title}

              </h2>

            </div>

          </div>



          <!-- Podium Box -->

          <div class="podium-box-grid">

            <div class="podium-slot gold">

              <span style="font-size: 24px;">🥇</span>

              <div>

                <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">1 МЕСТО &bull; ЧЕМПИОН</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.champion}</div>

              </div>

            </div>

            <div class="podium-slot silver">

              <span style="font-size: 24px;">🥈</span>

              <div>

                <div style="font-size: 10px; color: #cbd5e1; font-weight: 800; text-transform: uppercase;">2 МЕСТО &bull; ФИНАЛИСТ</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.runner_up}</div>

              </div>

            </div>

            <div class="podium-slot bronze">

              <span style="font-size: 24px;">🥉</span>

              <div>

                <div style="font-size: 10px; color: #d97706; font-weight: 800; text-transform: uppercase;">3 МЕСТО &bull; БРОНЗА</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.bronze || '—'}</div>

              </div>

            </div>

          </div>



          <!-- Key Master Players -->

          ${playersChips ? `

            <div style="margin: 12px 0 16px 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">

              <span style="font-size: 11px; color: #94a3b8; font-weight: 700;">Мастера лиги в турнире:</span>

              ${playersChips}

            </div>

          ` : ''}



          <!-- Unified Sub-Navigation Buttons (Tabs) -->

          <div style="display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 2px solid rgba(255,255,255,0.2); padding-bottom: 12px; margin-top: 16px;">

            <button class="filter-btn ${specialSubTab === 'matches' ? 'active' : ''}" onclick="switchSpecialSubTab('matches')">

              📋 Все матчи турнира (${matches.length})

            </button>

            <button class="filter-btn ${specialSubTab === 'tables' ? 'active' : ''}" onclick="switchSpecialSubTab('tables')">

              🏆 Таблицы дивизионов

            </button>

            <button class="filter-btn ${specialSubTab === 'playoff' ? 'active' : ''}" onclick="switchSpecialSubTab('playoff')">

              ⚡ Сетка плей-офф

            </button>

            <button class="filter-btn ${specialSubTab === 'about' ? 'active' : ''}" onclick="switchSpecialSubTab('about')">

              📜 Описание и регламент

            </button>

          </div>



          <!-- Active Sub-Tab Content -->

          ${subContentHtml}

        </div>

      `;

      if (specialSubTab === 'playoff' && specialPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('specialBracketWrapper', 'specialBracketContainer', 'specialBracketSvg'), 60);
      }

    }



    // Init

    

    



function initPortal() {
      try { renderHud(); } catch(e) { console.error('renderHud:', e); }
      try { renderTable(); } catch(e) { console.error('renderTable:', e); }
      try { renderCards(); } catch(e) { console.error('renderCards:', e); }
      try { renderSeasonsBar(); } catch(e) { console.error('renderSeasonsBar:', e); }
      try { selectSeason('9'); } catch(e) { console.error('selectSeason:', e); }
      try { renderClutch(); } catch(e) { console.error('renderClutch:', e); }
      try { renderH2H(); } catch(e) { console.error('renderH2H:', e); }
      try { renderSpecialTournaments(); } catch(e) { console.error('renderSpecialTournaments:', e); }
      try { renderTeamTournaments(); } catch(e) { console.error('renderTeamTournaments:', e); }
      try { handleRouting(); } catch(e) { console.error('handleRouting:', e); }
    }

    if (document.readyState === 'loading') {
      window.addEventListener('DOMContentLoaded', initPortal);
    } else {
      initPortal();
    }



    
    function drawBracketConnectors(wId = 'bracketWrapper', cId = 'bracketContainer', sId = 'bracketSvg') {
      const wrapper = document.getElementById(wId);
      const container = document.getElementById(cId);
      const svg = document.getElementById(sId);
      if (!wrapper || !container || !svg) return;

      const scrollW = container.scrollWidth;
      const scrollH = container.scrollHeight;
      svg.style.width = scrollW + 'px';
      svg.style.height = scrollH + 'px';
      svg.setAttribute('width', scrollW);
      svg.setAttribute('height', scrollH);
      svg.setAttribute('viewBox', '0 0 ' + scrollW + ' ' + scrollH);

      const wrapRect = wrapper.getBoundingClientRect();
      const sLeft = wrapper.scrollLeft;
      const sTop = wrapper.scrollTop;

      const rounds = Array.from(container.querySelectorAll('.bracket-round, .bracket-champion-round'));
      if (rounds.length < 2) {
        svg.innerHTML = '';
        return;
      }

      let pathsHtml = `
        <defs>
          <filter id="bracketGlowCyan" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#00f0ff" flood-opacity="0.9"/>
          </filter>
          <filter id="bracketGlowGold" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="#fbbf24" flood-opacity="0.95"/>
          </filter>
          <marker id="arrowCyan" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#00f0ff" />
          </marker>
          <marker id="arrowGold" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#fbbf24" />
          </marker>
        </defs>
      `;

      for (let r = 0; r < rounds.length - 1; r++) {
        const curRound = rounds[r];
        const nextRound = rounds[r + 1];
        if (!curRound || !nextRound) continue;

        const curCards = Array.from(curRound.querySelectorAll('.bracket-match-card'));
        const nextCards = Array.from(nextRound.querySelectorAll('.bracket-match-card, .bracket-champion-box'));

        curCards.forEach(cCard => {
          const winnerRow = cCard.querySelector('.bracket-player-row.winner');
          const winnerName = winnerRow ? (winnerRow.getAttribute('data-player') || '').trim().toLowerCase() : null;
          if (!winnerName) return;

          let destEl = null;
          for (const nCard of nextCards) {
            if (nCard.classList.contains('bracket-champion-box')) {
              const cName = (nCard.getAttribute('data-player') || '').trim().toLowerCase();
              if (cName === winnerName) {
                destEl = nCard;
                break;
              }
            } else {
              const matchRow = nCard.querySelector('.bracket-player-row[data-player="' + winnerRow.getAttribute('data-player') + '"]');
              if (matchRow) {
                destEl = matchRow;
                break;
              }
            }
          }

          if (!destEl) return;

          const cRect = winnerRow.getBoundingClientRect();
          const dRect = destEl.getBoundingClientRect();

          const x1 = Math.round(cRect.right - wrapRect.left + sLeft);
          const y1 = Math.round(cRect.top + cRect.height / 2 - wrapRect.top + sTop);
          const x2 = Math.round(dRect.left - wrapRect.left + sLeft);
          const y2 = Math.round(dRect.top + dRect.height / 2 - wrapRect.top + sTop);

          const midX = Math.round(x1 + (x2 - x1) * 0.5);

          const isChamp = destEl.classList.contains('bracket-champion-box');
          const strokeColor = isChamp ? '#fbbf24' : '#00f0ff';
          const strokeWidth = isChamp ? '3' : '2.5';
          const filterId = isChamp ? 'url(#bracketGlowGold)' : 'url(#bracketGlowCyan)';
          const markerId = isChamp ? 'url(#arrowGold)' : 'url(#arrowCyan)';

          pathsHtml += `
            <path d="M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}"
                  data-player="${winnerName}"
                  class="bracket-connector-path path-player-${winnerName}"
                  fill="none"
                  stroke="${strokeColor}"
                  stroke-width="${strokeWidth}"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  marker-end="${markerId}" />
          `;
        });
      }

      svg.innerHTML = pathsHtml;
    }

    window.addEventListener('resize', () => {
      if (seasonSubTab === 'playoff' && playoffViewMode === 'bracket') {
        setTimeout(drawBracketConnectors, 40);
      }
      if (teamSubTab === 'playoff' && teamPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('teamBracketWrapper', 'teamBracketContainer', 'teamBracketSvg'), 40);
      }
      if (specialSubTab === 'playoff' && specialPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('specialBracketWrapper', 'specialBracketContainer', 'specialBracketSvg'), 40);
      }
    });

    let lockedBracketPlayer = null;

    function highlightPlayerBracketPath(playerName, force = false, wId = null, bId = null) {
      if (lockedBracketPlayer && !force) return;
      const pLow = (playerName || '').trim().toLowerCase();
      let wrapper = wId ? document.getElementById(wId) : null;
      let banner = bId ? document.getElementById(bId) : null;
      if (!wrapper) {
        const teamTab = document.getElementById('tab-teams');
        const specialTab = document.getElementById('tab-special');
        if (teamTab && teamTab.classList.contains('active')) {
          wrapper = document.getElementById('teamBracketWrapper');
          banner = document.getElementById('teamBracketPathBanner');
        } else if (specialTab && specialTab.classList.contains('active')) {
          wrapper = document.getElementById('specialBracketWrapper');
          banner = document.getElementById('specialBracketPathBanner');
        } else {
          wrapper = document.getElementById('bracketWrapper');
          banner = document.getElementById('bracketPathBanner');
        }
      }
      if (!wrapper || !pLow) return;

      wrapper.classList.add('has-focus');

      // Highlight / dim cards
      const cards = wrapper.querySelectorAll('.bracket-match-card');
      let playerMatchesCount = 0;
      let playerWinsCount = 0;
      let highestRound = '';
      let isChampion = false;

      cards.forEach(card => {
        const playersAttr = (card.getAttribute('data-players') || '').toLowerCase();
        if (playersAttr.includes(pLow)) {
          card.classList.add('card-focused');
          playerMatchesCount++;
          const winnerRow = card.querySelector('.bracket-player-row.winner');
          if (winnerRow && (winnerRow.getAttribute('data-player') || '').toLowerCase() === pLow) {
            playerWinsCount++;
          }
          const roundTitle = card.closest('.bracket-round') ? card.closest('.bracket-round').querySelector('.bracket-round-header') : null;
          if (roundTitle) highestRound = roundTitle.textContent.trim();
        } else {
          card.classList.remove('card-focused');
        }
      });

      // Champion box
      const champBox = wrapper.querySelector('.bracket-champion-box');
      if (champBox) {
        const champName = (champBox.getAttribute('data-player') || '').toLowerCase();
        if (champName === pLow) {
          champBox.classList.add('champ-focused');
          isChampion = true;
        } else {
          champBox.classList.remove('champ-focused');
        }
      }

      // Highlight paths
      const paths = wrapper.querySelectorAll('.bracket-connector-path');
      paths.forEach(p => {
        const pathPlayer = (p.getAttribute('data-player') || '').toLowerCase();
        if (pathPlayer === pLow) {
          p.classList.add('path-focused');
        } else {
          p.classList.remove('path-focused');
        }
      });

      // Quick chips active state
      document.querySelectorAll('.bracket-player-pill').forEach(btn => {
        if ((btn.getAttribute('data-player') || '').toLowerCase() === pLow) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });

      // Update banner text without layout shift
      if (banner) {
        let summaryText = `<div>⚡ ПУТЬ ИГРОКА В СЕТКЕ: <strong style="color: var(--nes-gold); text-transform: uppercase;">${playerName}</strong>`;
        if (isChampion) {
          summaryText += ` &bull; 👑 <span style="color: var(--nes-gold); font-weight: 800;">ОБЛАДАТЕЛЬ КУБКА</span>`;
        } else if (highestRound) {
          summaryText += ` &bull; Дошёл до: <span style="color: var(--nes-cyan); font-weight: 700;">${highestRound}</span>`;
        }
        if (lockedBracketPlayer) {
          summaryText += ` <span style="color: #4ade80; font-size: 11px; margin-left: 8px; font-weight: normal;">(зафиксировано)</span>`;
        }
        summaryText += `</div>`;
        if (lockedBracketPlayer) {
          summaryText += `<button type="button" class="banner-reset-btn" onclick="resetPlayerBracketPath()">&times; Сбросить выбор</button>`;
        }
        banner.innerHTML = summaryText;
        banner.classList.add('active');
      }
    }

    function clearPlayerBracketHighlight(wId = null, bId = null) {
      if (lockedBracketPlayer) return;
      let wrapper = wId ? document.getElementById(wId) : null;
      let banner = bId ? document.getElementById(bId) : null;
      if (!wrapper) {
        const teamTab = document.getElementById('tab-teams');
        const specialTab = document.getElementById('tab-special');
        if (teamTab && teamTab.classList.contains('active')) {
          wrapper = document.getElementById('teamBracketWrapper');
          banner = document.getElementById('teamBracketPathBanner');
        } else if (specialTab && specialTab.classList.contains('active')) {
          wrapper = document.getElementById('specialBracketWrapper');
          banner = document.getElementById('specialBracketPathBanner');
        } else {
          wrapper = document.getElementById('bracketWrapper');
          banner = document.getElementById('bracketPathBanner');
        }
      }
      if (!wrapper) return;

      wrapper.classList.remove('has-focus');
      wrapper.querySelectorAll('.card-focused').forEach(el => el.classList.remove('card-focused'));
      wrapper.querySelectorAll('.champ-focused').forEach(el => el.classList.remove('champ-focused'));
      wrapper.querySelectorAll('.path-focused').forEach(el => el.classList.remove('path-focused'));
      document.querySelectorAll('.bracket-player-pill').forEach(btn => btn.classList.remove('active'));

      if (banner) {
        banner.classList.remove('active');
        banner.innerHTML = '<span style="color: #94a3b8;">💡 Наведите на любого игрока или нажмите, чтобы проследить его путь по сетке</span>';
      }
    }

    function selectPlayerBracketPath(playerName) {
      if (lockedBracketPlayer === playerName) {
        resetPlayerBracketPath();
      } else {
        lockedBracketPlayer = playerName;
        highlightPlayerBracketPath(playerName, true);
      }
    }

    function resetPlayerBracketPath() {
      lockedBracketPlayer = null;
      clearPlayerBracketHighlight();
    }

    window.addEventListener('hashchange', handleRouting);

  </script>

  <!-- Persistent Audio Deck & PJAX Router -->
  <script src="audio/playlist-manifest.js"></script>
  <script src="audio-player.js"></script>
</body>

</html>

"""



final_html = html_code.replace("__DATA_PLACEHOLDER__", json_str)



out_file = os.path.abspath("soccer.html")

with open(out_file, "w", encoding="utf-8") as f:

    f.write(final_html)



print(f"Redesigned Portal successfully written to: {out_file}")

print(f"Final File Size: {len(final_html) / 1024:.1f} KB")

