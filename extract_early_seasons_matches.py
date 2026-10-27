import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import csv
import json
import re

TOKEN = '5b312f445b312f445b312f44e85875dc6155b315b312f4431ed8ef6bb3494dacba55020'
GROUP_ID = 66162180

# 1. Parse Season 1 (180 matches from Google Sheet matrix)
url_s1 = 'https://docs.google.com/spreadsheets/d/10klGay_ljczw4Rm-wCFxTxT9VcbAH5Lw1WjiYVQIJ3M/gviz/tq?tqx=out:csv'
r_s1 = requests.get(url_s1, timeout=10)
reader_s1 = csv.reader(r_s1.text.splitlines())
rows_s1 = list(reader_s1)

header_s1 = rows_s1[0]
player_cols = {}
for idx, col in enumerate(header_s1):
    c = col.strip()
    if c in ['Memori', 'Ric25', 'WiSe', 'Wenderfit', 'Yoxter', 'E_not', 'Eg_or3', 'Rustin Cohle', 'Romario', 'Gilmour']:
        player_cols[idx] = c

s1_matches = []
seen_s1 = set()
for r in rows_s1[1:]:
    current_player = r[1].strip() if len(r) > 1 and r[1].strip() in player_cols.values() else None
    if current_player:
        for c_idx, opp in player_cols.items():
            if c_idx < len(r) and opp != current_player:
                val = r[c_idx].strip()
                scores = re.findall(r'(\d+):(\d+)', val)
                for s1, s2 in scores:
                    # Avoid exact duplicate inverted
                    s1_matches.append({
                        'season': 'Season 1',
                        'tournament': 'Season 1 Регулярный чемпионат',
                        'stage': 'Круговой этап',
                        'p1': current_player,
                        'p2': opp,
                        's1': int(s1),
                        's2': int(s2),
                        'ot': False, 'pk': False, 'is_playoff': False
                    })

print(f"Season 1 matches parsed: {len(s1_matches)}")

# 2. Season 2 Playoff matches (Sheet 1AJL3iUpmmmbCtOWqMuJeUXpb90kVDHIFu98LSQbZwME)
s2_matches = [
    # 1/16
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/16 финала", "p1": "tubustd", "p2": "Rustin Cohle", "s1": 3, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/16 финала", "p1": "Dopi", "p2": "Kirpich", "s1": 3, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/16 финала", "p1": "Kipriot", "p2": "Romario", "s1": 3, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/16 финала", "p1": "TransSister", "p2": "wanchous", "s1": 3, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    # 1/8
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/8 финала", "p1": "tubustd", "p2": "Ric25", "s1": 3, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/8 финала", "p1": "Dopi", "p2": "Dr1N", "s1": 3, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/8 финала", "p1": "Huba Buba", "p2": "Kipriot", "s1": 3, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/8 финала", "p1": "TransSister", "p2": "BOР95", "s1": 3, "s2": 2, "ot": False, "pk": False, "is_playoff": True},
    # 1/4
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/4 финала", "p1": "Memori", "p2": "tubustd", "s1": 4, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/4 финала", "p1": "mafuta", "p2": "Dopi", "s1": 4, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/4 финала", "p1": "ectoPower", "p2": "Huba Buba", "s1": 4, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/4 финала", "p1": "Kunio", "p2": "TransSister", "s1": 4, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    # 1/2
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/2 финала", "p1": "mafuta", "p2": "Memori", "s1": 4, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "1/2 финала", "p1": "Kunio", "p2": "ectoPower", "s1": 4, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    # Final
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "Гранд-Финал", "p1": "mafuta", "p2": "Kunio", "s1": 5, "s2": 2, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 2", "tournament": "Season 2 Плей-офф", "stage": "Матч за 3 место", "p1": "ectoPower", "p2": "Memori", "s1": 4, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
]
print(f"Season 2 matches: {len(s2_matches)}")

# 3. Season 3 matches (Oball / Topic 33967365)
s3_matches = []
try:
    resp = requests.get('https://api.vk.com/method/board.getComments', params={
        'group_id': GROUP_ID,
        'topic_id': 33967365,
        'access_token': TOKEN,
        'v': '5.199',
        'count': 100
    }, timeout=10).json()
    for c in resp.get('response', {}).get('items', []):
        txt = c.get('text', '')
        # Pattern like: Player1 vs Player2 3:1 or Player1 - Player2 2:0
        m_pairs = re.findall(r'([A-Za-zА-Яа-я0-9_]{3,15})\s*(?:vs|-)\s*([A-Za-zА-Яа-я0-9_]{3,15})\s*[:\s-]*(\d+)\s*[:\s-]\s*(\d+)', txt)
        for p1, p2, s1, s2 in m_pairs:
            s3_matches.append({
                'season': 'Season 3',
                'tournament': 'Season 3 Чемпионат',
                'stage': 'Регулярка/Плей-офф',
                'p1': p1.strip(),
                'p2': p2.strip(),
                's1': int(s1),
                's2': int(s2),
                'ot': False, 'pk': False, 'is_playoff': False
            })
except Exception as e:
    print('S3 error:', e)

# Add curated major Season 3 playoff matches
s3_curated = [
    {"season": "Season 3", "tournament": "Season 3 Плей-офф", "stage": "1/4 финала", "p1": "mafuta", "p2": "tubustd", "s1": 4, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 3", "tournament": "Season 3 Плей-офф", "stage": "1/4 финала", "p1": "ectoPower", "p2": "izzzotope", "s1": 4, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 3", "tournament": "Season 3 Плей-офф", "stage": "1/4 финала", "p1": "Ric25", "p2": "Memori", "s1": 4, "s2": 2, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 3", "tournament": "Season 3 Плей-офф", "stage": "1/4 финала", "p1": "Kunio", "p2": "Dopi", "s1": 4, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 3", "tournament": "Season 3 Плей-офф", "stage": "1/2 финала", "p1": "mafuta", "p2": "Ric25", "s1": 4, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 3", "tournament": "Season 3 Плей-офф", "stage": "1/2 финала", "p1": "ectoPower", "p2": "Kunio", "s1": 4, "s2": 2, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 3", "tournament": "Season 3 Плей-офф", "stage": "Гранд-Финал", "p1": "mafuta", "p2": "ectoPower", "s1": 5, "s2": 3, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 3", "tournament": "Season 3 Плей-офф", "stage": "Матч за 3 место", "p1": "Ric25", "p2": "Kunio", "s1": 4, "s2": 2, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 3", "tournament": "Season 3 Кубок лиг", "stage": "Финал Кубка", "p1": "mafuta", "p2": "Ric25", "s1": 5, "s2": 2, "ot": False, "pk": False, "is_playoff": True},
]
s3_matches.extend(s3_curated)
print(f"Season 3 matches: {len(s3_matches)}")

# 4. Season 4 matches (Sheet 1A82QKKuqsXJwHl-Cflprs3VoEh8Xtzdvx_sr8rcQBP0)
s4_matches = [
    # 1/16
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/16 финала", "p1": "high", "p2": "Kubik", "s1": 3, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/16 финала", "p1": "Romix", "p2": "Aeris", "s1": 3, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/16 финала", "p1": "3aBuCTb", "p2": "FC Pushistik", "s1": 3, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/16 финала", "p1": "tubustd", "p2": "Flash", "s1": 3, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    # 1/8
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/8 финала", "p1": "Kunio", "p2": "high", "s1": 3, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/8 финала", "p1": "izzzotope", "p2": "Romix", "s1": 3, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/8 финала", "p1": "Kipriot", "p2": "3aBuCTb", "s1": 3, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/8 финала", "p1": "Ric25", "p2": "tubustd", "s1": 3, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    # 1/4
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/4 финала", "p1": "Transistor", "p2": "Kunio", "s1": 4, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/4 финала", "p1": "mafuta", "p2": "izzzotope", "s1": 4, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/4 финала", "p1": "Kipriot", "p2": "ectoPower", "s1": 4, "s2": 3, "ot": True, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/4 финала", "p1": "LiptOn", "p2": "Ric25", "s1": 4, "s2": 3, "ot": True, "pk": False, "is_playoff": True},
    # 1/2
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/2 финала", "p1": "Transistor", "p2": "Kipriot", "s1": 4, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "1/2 финала", "p1": "mafuta", "p2": "LiptOn", "s1": 4, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    # Final
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "Гранд-Финал", "p1": "Transistor", "p2": "mafuta", "s1": 4, "s2": 3, "ot": True, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Плей-офф", "stage": "Матч за 3 место", "p1": "ectoPower", "p2": "LiptOn", "s1": 3, "s2": 1, "ot": False, "pk": False, "is_playoff": True},
    {"season": "Season 4", "tournament": "Season 4 Кубок лиг", "stage": "Финал Кубка", "p1": "mafuta", "p2": "LiptOn", "s1": 5, "s2": 0, "ot": False, "pk": False, "is_playoff": True},
]
print(f"Season 4 matches: {len(s4_matches)}")

all_early = s1_matches + s2_matches + s3_matches + s4_matches
with open('early_seasons_matches.json', 'w', encoding='utf-8') as f:
    json.dump(all_early, f, ensure_ascii=False, indent=2)

print(f"Total early matches saved: {len(all_early)}")
