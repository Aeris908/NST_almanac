import json, sys, re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

group_id = '66162180'

with open('vk_soccer_comments_cache.json', 'r', encoding='utf-8') as f:
    comments_by_topic = json.load(f)

print(f"Loaded {len(comments_by_topic)} topics from cache.")

# Aliases
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
    if not n: return ""
    n = n.strip().strip('*.,_()[]')
    low = n.lower()
    return NAME_ALIASES.get(low, n)

MATCH_REGEXES = [
    re.compile(r'([A-Za-zА-Яа-я0-9_]{3,18})\s+(?:vs|против|\-)\s+([A-Za-zА-Яа-я0-9_]{3,18})\s*[:\-–]\s*(\d+)\s*[:\-–]\s*(\d+)', re.IGNORECASE),
    re.compile(r'([A-Za-zА-Яа-я0-9_]{3,18})\s+(?:vs|против|\-)\s+([A-Za-zА-Яа-я0-9_]{3,18})\s+(\d+)\s*[:\-–]\s*(\d+)', re.IGNORECASE),
]

banned_words = {'тур', 'матч', 'лига', 'тайм', 'счет', 'игра', 'итог', 'видео', 'ютуб', 'первый', 'второй', 'группа', 'финал', 'сезон'}

# Build a lookup table from (p1_low, p2_low, s1, s2) -> (vk_url, video_url)
# Also indexed by (p1_low, p2_low) as fallback
match_lookup = {}
pair_fallback_lookup = defaultdict(list)

total_videos_found = 0
total_reports_found = 0

for tid_str, comments in comments_by_topic.items():
    tid = int(tid_str)
    for c in comments:
        cid = c.get('id')
        txt = c.get('text', '')
        atts = c.get('attachments', [])
        vk_url = f"https://vk.com/topic-{group_id}_{tid}?post={cid}"
        
        # Extract video if present
        video_url = None
        for a in atts:
            if a.get('type') == 'video':
                v = a.get('video', {})
                video_url = f"https://vk.com/video{v.get('owner_id')}_{v.get('id')}"
                break
        if not video_url:
            m = re.search(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=[A-Za-z0-9_\-]+|youtu\.be/[A-Za-z0-9_\-]+|twitch\.tv/[A-Za-z0-9_\-]+))', txt)
            if m:
                video_url = m.group(1)
                
        if video_url:
            total_videos_found += 1
            
        parts = re.split(r'[\n;,]', txt)
        for part in parts:
            part = part.strip()
            if not part: continue
            for rx in MATCH_REGEXES:
                for match in rx.finditer(part):
                    p1_raw = match.group(1)
                    p2_raw = match.group(2)
                    s1 = int(match.group(3))
                    s2 = int(match.group(4))
                    if p1_raw.lower() in banned_words or p2_raw.lower() in banned_words:
                        continue
                    p1 = clean_name(p1_raw)
                    p2 = clean_name(p2_raw)
                    if p1.lower() == p2.lower() or len(p1) < 3 or len(p2) < 3:
                        continue
                    if s1 > 25 or s2 > 25:
                        continue
                        
                    total_reports_found += 1
                    p1_low = p1.lower()
                    p2_low = p2.lower()
                    
                    # Direct and inverse keys
                    key1 = (p1_low, p2_low, s1, s2)
                    key2 = (p2_low, p1_low, s2, s1)
                    info = {"vk_url": vk_url, "video_url": video_url, "cid": cid, "tid": tid}
                    
                    # Store, prefer one with video
                    if key1 not in match_lookup or (video_url and not match_lookup[key1].get('video_url')):
                        match_lookup[key1] = info
                        match_lookup[key2] = info
                        
                    pair_key = (min(p1_low, p2_low), max(p1_low, p2_low))
                    pair_fallback_lookup[pair_key].append(info)

print(f"Extracted {total_reports_found} match reports from VK comments!")
print(f"Total video recordings/streams found: {total_videos_found}!")
print(f"Unique score-matched keys: {len(match_lookup)}")

# Save lookup to disk
with open('vk_match_sources_lookup.json', 'w', encoding='utf-8') as f:
    # Serialize tuple keys as string
    serialized = {f"{k[0]}|{k[1]}|{k[2]}|{k[3]}": v for k, v in match_lookup.items()}
    json.dump(serialized, f, ensure_ascii=False, indent=2)

print("Saved lookup to vk_match_sources_lookup.json!")
