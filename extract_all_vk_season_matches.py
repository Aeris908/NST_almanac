import urllib.request, json, sys, re
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

token = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
group_id = '66162180'

topics = {
    "Season 2": (33103100, 410),
    "Season 3": (33967365, 390),
    "Season 4": (34973011, 280),
    "Season 5": (36630593, 160),
    "Season 6": (39660451, 290),
    "Season 7": (49054760, 220),
}

NAME_ALIASES = {
    "knucklesss": "Aeris",
    "knuckles": "Aeris",
    "наклз": "Aeris",
    "aeris": "Aeris",
    "мгб": "RVD (МГБ)",
    "rvd": "RVD (МГБ)",
    "рвд": "RVD (МГБ)",
    "палка палыч": "PacnyTHuK",
    "palka palych": "PacnyTHuK",
    "палыч": "PacnyTHuK",
    "кубик": "Kubik",
    "kubik": "Kubik",
    "дюн": "Dune",
    "dune": "Dune",
    "рок": "Rock",
    "rock": "Rock",
    "экто": "ectoPower",
    "ectopower": "ectoPower",
    "мафута": "mafuta",
    "mafuta": "mafuta",
    "мемори": "Memori",
    "memori": "Memori",
    "ромикс": "Romix",
    "romix": "Romix",
    "сокол": "Sokol",
    "sokol": "Sokol",
    "кирпич": "Кирпич57",
    "кирпич57": "Кирпич57",
    "енот": "E_not",
    "enot": "E_not",
    "e_not": "E_not",
    "даз": "daz",
    "daz": "daz",
    "таёда": "Taeda",
    "таеда": "Taeda",
    "taeda": "Taeda",
    "роджер": "Веселый Роджер",
    "веселый роджер": "Веселый Роджер",
    "леонид": "leonudomlya",
    "leonudomlya": "leonudomlya",
    "рик25": "Ric25",
    "ric25": "Ric25",
    "рик": "Ric25",
    "транзистор": "Transistor",
    "transistor": "Transistor",
    "transsister": "Transistor",
    "вайз": "WiSe",
    "wise": "WiSe",
    "вендер": "Wenderfit",
    "wenderfit": "Wenderfit",
    "допи": "Dopi",
    "dopi": "Dopi",
    "дрин": "Dr1N",
    "dr1n": "Dr1N",
    "хуба": "Huba Buba",
    "huba buba": "Huba Buba",
    "хантэр": "Hanter",
    "хантер": "Hanter",
    "hanter": "Hanter",
    "джем": "Jamlight",
    "jamlight": "Jamlight",
    "юлий": "Yuliy_Cezar",
    "цезарь": "Yuliy_Cezar",
    "juliy cezar": "Yuliy_Cezar",
    "yuliy cezar": "Yuliy_Cezar",
    "yuliy_cezar": "Yuliy_Cezar",
    "ленин": "lenin1st",
    "ленинст": "lenin1st",
    "lenin1st": "lenin1st",
    "анубис": "Anubis",
    "anubis": "Anubis",
    "раш": "RASH",
    "rash": "RASH",
    "к-р": "K-R",
    "k-r": "K-R",
    "буц": "Буц",
    "ромэль": "Romol",
    "romol": "Romol",
    "руби": "ruby",
    "ruby": "ruby",
    "динамик": "Dynamik",
    "dynamik": "Dynamik",
}

def clean_name(n):
    n = n.strip().strip('*.,_()[]')
    low = n.lower()
    return NAME_ALIASES.get(low, n)

# Fetch all comments for a topic
def fetch_topic_comments(tid):
    comments = []
    offset = 0
    while True:
        url = f"https://api.vk.ru/method/board.getComments?group_id={group_id}&topic_id={tid}&count=100&offset={offset}&access_token={token}&v=5.199"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
        items = resp.get('response', {}).get('items', [])
        if not items:
            break
        comments.extend(items)
        if len(items) < 100:
            break
        offset += 100
    return comments

# Pattern to parse match results from comments
# Examples:
# "МГБ vs Memori - 2:1"
# "Memori vs МГБ - 6:5 (OT)"
# "Aeris vs Yuliy Cezar - 3:4"
# "ectoPower - МГБ - 2 -2 (7-6 ПК)"
# "Dynamik vs Кубик 5:6 (РК)"
# "Romol - ruby 3-0"
# "Таёда - Romol 0:1"
# "lenin1st - RASH 2-1"

MATCH_REGEXES = [
    # Player1 [vs / -] Player2 [:-] Score1 : Score2 [(OT / PK / пен)]
    re.compile(r'([A-Za-zА-Яа-я0-9_]{3,18})\s+(?:vs|против|\-)\s+([A-Za-zА-Яа-я0-9_]{3,18})\s*[:\-–]\s*(\d+)\s*[:\-–]\s*(\d+)(?:\s*\(([^)]+)\))?', re.IGNORECASE),
    # Player1 [vs / -] Player2 Score1 : Score2
    re.compile(r'([A-Za-zА-Яа-я0-9_]{3,18})\s+(?:vs|против|\-)\s+([A-Za-zА-Яа-я0-9_]{3,18})\s+(\d+)\s*[:\-–]\s*(\d+)(?:\s*\(([^)]+)\))?', re.IGNORECASE),
]

all_extracted_matches = defaultdict(list)

for s_name, (tid, approx_count) in topics.items():
    print(f"Fetching comments for {s_name} (topic {tid})...")
    comments = fetch_topic_comments(tid)
    print(f"  Downloaded {len(comments)} comments.")
    
    matches_found = []
    seen = set()
    
    for c in comments:
        text = c.get('text', '')
        # Split text into lines or clauses
        parts = re.split(r'[\n;,]', text)
        for part in parts:
            part = part.strip()
            if not part: continue
            
            # Check stage if specified
            stage = "Регулярный чемпионат"
            if re.search(r'высшая|вл\b', part, re.IGNORECASE): stage = "Высшая лига"
            elif re.search(r'средняя|сл\b', part, re.IGNORECASE): stage = "Средняя лига"
            elif re.search(r'дворовая|дл\b', part, re.IGNORECASE): stage = "Дворовая лига"
            elif re.search(r'плей-офф|финал|1/[248]', part, re.IGNORECASE): stage = "Плей-офф"
            
            for rx in MATCH_REGEXES:
                for match in rx.finditer(part):
                    p1_raw = match.group(1)
                    p2_raw = match.group(2)
                    s1 = int(match.group(3))
                    s2 = int(match.group(4))
                    note = (match.group(5) or "").lower()
                    
                    # Filter out non-player words like "тур", "матч", "лига", "видео", "тайм", "игра"
                    banned_words = {'тур', 'матч', 'лига', 'тайм', 'счет', 'игра', 'итог', 'видео', 'ютуб', 'первый', 'второй', 'группа'}
                    if p1_raw.lower() in banned_words or p2_raw.lower() in banned_words:
                        continue
                    
                    # Clean names
                    p1 = clean_name(p1_raw)
                    p2 = clean_name(p2_raw)
                    
                    if p1.lower() == p2.lower() or len(p1) < 3 or len(p2) < 3:
                        continue
                    if s1 > 25 or s2 > 25: # suspicious score
                        continue
                    
                    ot = any(k in note for k in ['ot', 'от', 'овертайм'])
                    pk = any(k in note for k in ['pk', 'рк', 'пк', 'пен', 'пенальти', 'буллит'])
                    
                    key = (s_name, min(p1, p2), max(p1, p2), s1, s2, c['id'])
                    if key not in seen:
                        seen.add(key)
                        matches_found.append({
                            "season": s_name,
                            "tournament": f"Чемпионат NST ({s_name})",
                            "stage": stage,
                            "p1": p1,
                            "p2": p2,
                            "s1": s1,
                            "s2": s2,
                            "ot": ot,
                            "pk": pk,
                            "comment_id": c['id']
                        })
    
    print(f"  Parsed {len(matches_found)} verified matches from {s_name} discussions!")
    all_extracted_matches[s_name] = matches_found

print("\nSUMMARY OF EXTRACTED MATCHES PER SEASON:")
for s_name in topics:
    print(f"  {s_name}: {len(all_extracted_matches[s_name])} matches found in VK comments!")
