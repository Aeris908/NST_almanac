import json, sys, re
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding='utf-8')

# 1. Load ALIAS_MAP
with open("build_nekketsu_portal_v2.py", "r", encoding="utf-8") as f:
    portal_code = f.read()

m = re.search(r'ALIAS_MAP\s*=\s*\{([^}]+)\}', portal_code)
alias_map = {}
if m:
    for line in m.group(1).splitlines():
        line = line.strip()
        km = re.match(r'"([^"]+)":\s*"([^"]+)"', line)
        if km:
            alias_map[km.group(1).lower()] = km.group(2)

# Add newly identified aliases
alias_map["jamlight"] = "Jamlight"
alias_map["aj maker"] = "AJ_Maker"
alias_map["dan lavis"] = "Dan_Lavis"
alias_map["кубик"] = "Kubik"
alias_map["pacnythuk"] = "PacnyTHuK"

def clean_alias(name):
    if not name: return name
    n = str(name).strip()
    return alias_map.get(n.lower(), n)

def norm_season(s):
    s = str(s).strip()
    m = re.search(r'(\d+)', s)
    if m:
        return f"Сезон {m.group(1)}"
    return s

# Load sources
with open("early_seasons_matches.json", "r", encoding="utf-8") as f:
    early_matches = json.load(f)

with open("wiki_seasons_matches.json", "r", encoding="utf-8") as f:
    wiki_matches = json.load(f)

with open("all_vk_seasons_matches.json", "r", encoding="utf-8") as f:
    vk_topic_matches = json.load(f)

combined_matches = []
seen = set()

# First add Season 1 from early_matches
for m in early_matches:
    s = norm_season(m.get('season', ''))
    if s == 'Сезон 1':
        p1 = clean_alias(m.get('p1'))
        p2 = clean_alias(m.get('p2'))
        s1 = int(m.get('s1', 0))
        s2 = int(m.get('s2', 0))
        key = (s, min(p1, p2), max(p1, p2), min(s1, s2), max(s1, s2))
        # Season 1 had double-round-robins with potentially same score, so allow 2 occurrences max per pair
        cnt = sum(1 for x in seen if x[0] == s and x[1] == min(p1, p2) and x[2] == max(p1, p2))
        if cnt < 2:
            seen.add((s, min(p1, p2), max(p1, p2), cnt, s1, s2))
            combined_matches.append({
                "season": s,
                "league": m.get('league', 'Высшая лига'),
                "tour": m.get('tour', 'Основной этап'),
                "p1": p1, "p2": p2, "s1": s1, "s2": s2,
                "ot": m.get('ot', False),
                "tech": m.get('tech', False),
                "source": "season_1_archive"
            })

print(f"Season 1 matches added: {len(combined_matches)}")

# Next add all wiki matches (official calendar protocols)
wiki_added = 0
for m in wiki_matches:
    s = norm_season(m.get('season', ''))
    p1 = clean_alias(m.get('p1'))
    p2 = clean_alias(m.get('p2'))
    s1 = int(m.get('s1', 0))
    s2 = int(m.get('s2', 0))
    league = m.get('league', 'Высшая лига')
    tour = m.get('tour', '1 Тур')
    
    # Unique key including tour and scores
    key = (s, league, tour, min(p1, p2), max(p1, p2), s1, s2)
    # A pair might play 2 games in same tour
    cnt = sum(1 for x in seen if x[:5] == key[:5])
    if cnt < 2:
        seen.add((s, league, tour, min(p1, p2), max(p1, p2), cnt, s1, s2))
        combined_matches.append({
            "season": s,
            "league": league,
            "tour": tour,
            "p1": p1, "p2": p2, "s1": s1, "s2": s2,
            "ot": m.get('ot', False),
            "tech": m.get('tech', False),
            "source": m.get('source', 'wiki_page')
        })
        wiki_added += 1

print(f"Wiki matches added: {wiki_added}")

# Next add any extra matches from topic comments if not duplicate
topic_added = 0
for m in vk_topic_matches:
    s = norm_season(m.get('season', ''))
    p1 = clean_alias(m.get('p1'))
    p2 = clean_alias(m.get('p2'))
    s1 = int(m.get('s1', 0))
    s2 = int(m.get('s2', 0))
    league = m.get('league', 'Высшая лига')
    
    # Check if already present in this season between these players
    existing = [x for x in combined_matches if x['season'] == s and {x['p1'], x['p2']} == {p1, p2}]
    # If the score matches an existing match, it's a duplicate report
    is_dup = False
    for em in existing:
        if (em['s1'] == s1 and em['s2'] == s2) or (em['s1'] == s2 and em['s2'] == s1):
            is_dup = True
            break
            
    if not is_dup and len(existing) < 4: # don't over-add beyond plausible playoff games
        combined_matches.append({
            "season": s,
            "league": league,
            "tour": m.get('tour', 'Плей-офф / Доп. матч'),
            "p1": p1, "p2": p2, "s1": s1, "s2": s2,
            "ot": m.get('ot', False),
            "tech": m.get('tech', False),
            "source": "topic_comments"
        })
        topic_added += 1

print(f"Topic comments extra matches added: {topic_added}")
print(f"Total combined matches: {len(combined_matches)}")

season_counts = Counter(x['season'] for x in combined_matches)
for s in sorted(season_counts.keys()):
    leagues = Counter(x['league'] for x in combined_matches if x['season'] == s)
    leagues_str = ", ".join(f"{k}: {v}" for k, v in leagues.items())
    print(f"  {s}: Total {season_counts[s]} matches ({leagues_str})")

aoshi_s5 = [m for m in combined_matches if m['season'] == 'Сезон 5' and (m['p1'] == 'Aoshi' or m['p2'] == 'Aoshi')]
print(f"\nAoshi Season 5 matches: {len(aoshi_s5)}")
for m in aoshi_s5:
    print(f"  [{m['tour']}] {m['p1']} {m['s1']}:{m['s2']} {m['p2']} ({m['source']})")
