import json
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

group_id = '66162180'

with open('vk_soccer_comments_cache.json', 'r', encoding='utf-8') as f:
    comments_by_topic = json.load(f)

print(f"Loaded {len(comments_by_topic)} topics from cache.")

ALIASES = {
    "веселый роджер": "веселый роджер", "весёлый роджер": "веселый роджер", "роджер": "веселый роджер",
    "палка палыч": "pacnythuk", "palka palych": "pacnythuk", "распутник": "pacnythuk", "палыч": "pacnythuk", "палка": "pacnythuk", "pacnythuk": "pacnythuk",
    "fc pushistik": "fc pushistik", "пушистик": "fc pushistik", "pushistik": "fc pushistik",
    "rustin cohle": "rustin cohle", "rustin_cohle": "rustin cohle", "rustinchole": "rustin cohle", "растин": "rustin cohle", "cohle": "rustin cohle", "rustin": "rustin cohle",
    "huba buba 5": "huba buba", "huba-buba 5": "huba buba", "huba_buba_5": "huba buba", "huba buba": "huba buba", "huba-buba": "huba buba", "huba_buba": "huba buba", "hubabuba": "huba buba", "exponat": "huba buba", "буба": "huba buba", "huba": "huba buba",
    "leon-udomlya": "leonudomlya", "leonudomlya": "leonudomlya", "леон": "leonudomlya", "леонид": "leonudomlya",
    "zupka knorra": "zupka knorra", "knorra": "zupka knorra",
    "santa claus": "santa claus", "claus": "santa claus",
    "joe duffy": "joe duffy", "joeduffy": "joe duffy", "duffy": "joe duffy",
    "mag.of.shadow": "mag.of.shadow", "shadow": "mag.of.shadow",
    "дядюшка ау": "дядюшка ау", "дядюшка_ау": "дядюшка ау",
    "супергеройчик": "cyneprepou4uk", "cyneprepou4uk": "cyneprepou4uk", "bzk": "cyneprepou4uk",
    "rvd (мгб)": "rvd (мгб)", "fierykelsen": "rvd (мгб)", "fieryrvd": "rvd (мгб)", "xakofear": "rvd (мгб)", "рвд": "rvd (мгб)", "мгб": "rvd (мгб)", "rvd": "rvd (мгб)",
    "knucklesss": "aeris", "knuckles": "aeris", "наклз": "aeris", "aeris": "aeris",
    "transsister": "transistor", "transistor": "transistor", "транзистор": "transistor",
    "кирпич57": "кирпич57", "kirpich57": "кирпич57", "кирпич": "кирпич57", "kirpich": "кирпич57",
    "centurion": "centurion", "сenturion": "centurion", "centzloy": "centurion", "цент": "centurion", "cent": "centurion",
    "bop95": "boр95", "вор95": "boр95", "bop213": "boр95", "вор": "boр95",
    "yuliy_cezar": "yuliy_cezar", "yuliy cezar": "yuliy_cezar", "juliy cezar": "yuliy_cezar", "juliy_cezar": "yuliy_cezar", "цезарь": "yuliy_cezar", "юлий": "yuliy_cezar",
    "kot-from-ussr": "kot-from-ussr", "ussr": "kot-from-ussr",
    "kipriot91": "kipriot", "киприот": "kipriot", "kipriot": "kipriot",
    "tubustd": "tubustd", "тубус": "tubustd",
    "bubnov": "bubnov", "tymoschuk": "bubnov", "тимощук": "bubnov", "бубнов": "bubnov",
    "dan_lavis": "dan_lavis", "danlavis": "dan_lavis",
    "chocopie": "chocopie", "chokopie": "chocopie", "шокопай": "chocopie",
    "aj_maker": "aj_maker", "ajmaker": "aj_maker", "aj maker": "aj_maker",
    "wenderfit": "wenderfit", "wendefit": "wenderfit", "вендер": "wenderfit",
    "ectopower": "ectopower", "эктоповер": "ectopower", "экто": "ectopower",
    "jamlight": "jamlight", "джем": "jamlight",
    "кубик": "kubik", "kubik": "kubik",
    "дюныч": "dune", "дюн": "dune", "dune": "dune",
    "рок": "rock", "rock": "rock",
    "мемори": "memori", "memori": "memori",
    "мафута": "mafuta", "mafuta": "mafuta",
    "кунио": "kunio", "kunio": "kunio",
    "ромикс": "romix", "romix": "romix",
    "сокол": "sokol", "sokol": "sokol",
    "енот": "e_not", "enot": "e_not", "e_not": "e_not",
    "даз": "daz", "daz": "daz",
    "таёда": "taeda", "таеда": "taeda", "taeda": "taeda",
    "рик25": "ric25", "ric25": "ric25", "рик": "ric25",
    "вайз": "wise", "wise": "wise",
    "допи": "dopi", "dopi": "dopi",
    "дрин": "dr1n", "dr1n": "dr1n", "дрын": "dr1n",
    "хантэр": "hanter", "хантер": "hanter", "hanter": "hanter",
    "ленин1st": "lenin1st", "ленин": "lenin1st", "lenin1st": "lenin1st",
    "анубис": "anubis", "anubis": "anubis",
    "раш": "rash", "rash": "rash",
    "к-р": "k-r", "k-r": "k-r",
    "буц": "буц",
    "ромол": "romol", "romol": "romol", "ромэль": "romol",
    "руби": "ruby", "ruby": "ruby",
    "динамик": "dynamik", "dynamik": "dynamik",
    "аоши": "aoshi", "aoshi": "aoshi",
    "давитель": "davitel", "davitel": "davitel",
    "эг_ор3": "eg_or3", "eg_or3": "eg_or3", "egor3": "eg_or3",
    "йокстер": "yoxter", "yoxter": "yoxter",
    "липтон": "lipton", "lipton": "lipton", "lipt0n": "lipton",
    "техас": "texas", "texas": "texas",
    "псих": "psycho", "psycho": "psycho",
    "сталин": "stalin", "stalin": "stalin",
    "изотоп": "izzzotope", "izzzotope": "izzzotope", "izzotop": "izzzotope",
    "ванчоус": "wanchous", "wanchous": "wanchous",
    "легнахар": "legnahar", "legnahar": "legnahar",
    "artemis": "artemis", "atremis": "artemis",
    "mcfly": "mcfly", "msfly": "mcfly",
    "armfly": "armfly",
    "flash": "flash",
    "kamaz": "kamaz", "камаз": "kamaz",
    "damian": "damian",
    "gilmour": "gilmour",
    "romario": "romario",
    "3abuctb": "3abuctb", "зависть": "3abuctb",
    "ryumaru": "ryumaru", "рюмару": "ryumaru",
    "alpharushin": "alpharushin",
    "christian": "christian",
    "lipetsk": "lipetsk",
    "вася": "вася", "vasya": "вася",
}

sorted_alias_keys = sorted(ALIASES.keys(), key=lambda x: len(x), reverse=True)
alias_pattern = re.compile(
    r'(?<![A-Za-zА-Яа-я0-9_])(' + '|'.join(re.escape(k) for k in sorted_alias_keys) + r')(?![A-Za-zА-Яа-я0-9_])',
    re.IGNORECASE
)

score_re = re.compile(r'(\d{1,2})\s*[:\-–]\s*(\d{1,2})')

# Build offset map for every (tid, cid) based on VK 20 comments per page pagination
offset_map = {}
for tid_str, comments in comments_by_topic.items():
    tid = int(tid_str)
    sorted_c = sorted(comments, key=lambda x: x.get('id', 0))
    for idx, c in enumerate(sorted_c):
        cid = c.get('id')
        offset = (idx // 20) * 20
        offset_map[(tid, cid)] = offset

lookup_table = {}
total_entries = 0

for tid_str, comments in comments_by_topic.items():
    tid = int(tid_str)
    sorted_comms = sorted(comments, key=lambda x: x.get('id', 0))
    first_cid = sorted_comms[0].get('id') if sorted_comms else None

    for c in comments:
        cid = c.get('id')
        txt = c.get('text', '')

        # Skip topic header / rules / reglament comments
        if cid == first_cid:
            continue
        txt_upper = txt.upper()
        if any(w in txt_upper for w in ['РЕГЛАМЕНТ:', 'РЕГЛАМЕНТ ЛИГИ', 'ПРАВИЛА ТУРНИРА', 'ОБЩАЯ ИНФОРМАЦИЯ', 'ПРИМЕР ВЫКЛАДЫВАНИЯ РЕЗУЛЬТАТОВ', 'НАВИГАЦИЯ', 'ПРЕДВАРИТЕЛЬНЫЙ РЕЙТИНГ']):
            continue
        atts = c.get('attachments', [])
        offset = offset_map.get((tid, cid), 0)
        vk_url = f"https://vk.ru/topic-{group_id}_{tid}?offset={offset}#post{cid}"
        
        video_url = None
        for a in atts:
            if a.get('type') == 'video':
                v = a.get('video', {})
                video_url = f"https://vk.ru/video{v.get('owner_id')}_{v.get('id')}"
                break
        if not video_url:
            m_v = re.search(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=[A-Za-z0-9_\-]+|youtu\.be/[A-Za-z0-9_\-]+|twitch\.tv/[A-Za-z0-9_\-]+))', txt)
            if m_v:
                video_url = m_v.group(1)
                
        info = {
            "vk_url": vk_url,
            "video_url": video_url,
            "cid": cid,
            "tid": tid,
            "text": txt.strip(),
            "date": c.get('date'),
            "page": (offset // 20) + 1
        }
        
        lines = txt.split('\n')
        recent_pair = None
        
        for line in lines:
            line_str = line.strip()
            if not line_str: continue
            
            found_aliases = alias_pattern.findall(line_str)
            found_players = []
            for fa in found_aliases:
                canon = ALIASES.get(fa.lower())
                if canon and canon not in found_players:
                    found_players.append(canon)
                    
            clean_line = re.sub(r'https?://\S+', '', line_str)
            scores = []
            for sm in score_re.finditer(clean_line):
                start_pos = sm.start()
                if start_pos > 0 and clean_line[start_pos-1] in '0123456789.':
                    continue
                s1, s2 = int(sm.group(1)), int(sm.group(2))
                if s1 <= 20 and s2 <= 20:
                    scores.append((s1, s2))
                    
            if len(found_players) >= 2:
                p1, p2 = found_players[0], found_players[1]
                recent_pair = (p1, p2)
                p_min, p_max = min(p1, p2), max(p1, p2)
                
                # Register pair-level fallback ONLY if line has scores
                if scores:
                    k_pair = f"{tid}|{p_min}|{p_max}"
                    if k_pair not in lookup_table:
                        lookup_table[k_pair] = info
                
                for s1, s2 in scores:
                    s_min, s_max = min(s1, s2), max(s1, s2)
                    k_tid = f"{tid}|{p_min}|{p_max}|{s_min}|{s_max}"
                    k_glob = f"global|{p_min}|{p_max}|{s_min}|{s_max}"
                    k_dir = f"{tid}|{p1}|{p2}|{s1}|{s2}"
                    
                    if k_tid not in lookup_table or (video_url and not lookup_table[k_tid].get('video_url')):
                        lookup_table[k_tid] = info
                        lookup_table[k_glob] = info
                        lookup_table[k_dir] = info
                    total_entries += 1
            elif len(found_players) == 0 and scores and recent_pair:
                p1, p2 = recent_pair
                p_min, p_max = min(p1, p2), max(p1, p2)
                for s1, s2 in scores:
                    s_min, s_max = min(s1, s2), max(s1, s2)
                    k_tid = f"{tid}|{p_min}|{p_max}|{s_min}|{s_max}"
                    k_glob = f"global|{p_min}|{p_max}|{s_min}|{s_max}"
                    k_dir = f"{tid}|{p1}|{p2}|{s1}|{s2}"
                    if k_tid not in lookup_table or (video_url and not lookup_table[k_tid].get('video_url')):
                        lookup_table[k_tid] = info
                        lookup_table[k_glob] = info
                        lookup_table[k_dir] = info
                    total_entries += 1

print(f"Total entries parsed: {total_entries}")
print(f"Unique keys in lookup table: {len(lookup_table)}")

with open('vk_match_sources_lookup.json', 'w', encoding='utf-8') as f:
    json.dump(lookup_table, f, ensure_ascii=False, indent=2)

print("Saved high-precision vk_match_sources_lookup.json!")
