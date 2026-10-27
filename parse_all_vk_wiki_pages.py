import urllib.request, ssl, sys, re, json
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

CALENDARS = [
    {"season": "Сезон 2", "league": "Высшая лига", "pid": "50190588"},
    {"season": "Сезон 2", "league": "Младшая лига", "pid": "50190660"},
    {"season": "Сезон 3", "league": "Высшая лига", "pid": "50736711"},
    {"season": "Сезон 3", "league": "Средняя лига", "pid": "50736905"},
    {"season": "Сезон 3", "league": "Дворовая лига", "pid": "50737105"},
    {"season": "Сезон 4", "league": "Высшая лига", "pid": "51689599"},
    {"season": "Сезон 4", "league": "Средняя лига", "pid": "51689710"},
    {"season": "Сезон 4", "league": "Дворовая лига", "pid": "51689714"},
    {"season": "Сезон 5", "league": "Высшая лига", "pid": "52396755"},
    {"season": "Сезон 5", "league": "Средняя лига", "pid": "52396753"},
    {"season": "Сезон 5", "league": "Дворовая лига", "pid": "52396752"},
    {"season": "Сезон 6", "league": "Высшая лига", "pid": "52913184"},
    {"season": "Сезон 6", "league": "Средняя лига", "pid": "52913185"},
    {"season": "Сезон 6", "league": "Дворовая лига", "pid": "52913186"},
    {"season": "Сезон 7", "league": "Высшая лига", "pid": "53570373"},
    {"season": "Сезон 7", "league": "Средняя лига", "pid": "53570375"},
    {"season": "Сезон 7", "league": "Дворовая лига", "pid": "53570376"},
]

# Load existing ALIAS_MAP from build_nekketsu_portal_v2
with open("build_nekketsu_portal_v2.py", "r", encoding="utf-8") as f:
    portal_code = f.read()

# Extract ALIAS_MAP
m = re.search(r'ALIAS_MAP\s*=\s*\{([^}]+)\}', portal_code)
alias_map = {}
if m:
    for line in m.group(1).splitlines():
        line = line.strip()
        km = re.match(r'"([^"]+)":\s*"([^"]+)"', line)
        if km:
            alias_map[km.group(1).lower()] = km.group(2)

def clean_alias(name):
    if not name: return name
    n = str(name).strip()
    return alias_map.get(n.lower(), n)

class CleanParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lines = []
    def handle_data(self, data):
        d = data.strip()
        if d and not d.startswith('\u200c'):
            self.lines.append(d)

def parse_calendar_page(html, season, league, pid):
    p = CleanParser()
    p.feed(html)
    lines = p.lines
    
    # Ignore initial navigation / header lines until first "Тур" or "ТУРНИРНАЯ ТАБЛИЦА"
    start_idx = 0
    for i, l in enumerate(lines[:60]):
        if re.search(r'\b1\s*Тур\b', l, re.I) or "ТУРНИРНАЯ ТАБЛИЦА" in l:
            start_idx = i
            break
            
    content_lines = lines[start_idx:]
    
    matches = []
    current_tour = "1 Тур"
    i = 0
    n = len(content_lines)
    
    score_re = re.compile(r'^(\d+)\s*[:\-]\s*(\d+)(.*)$')
    
    while i < n:
        line = content_lines[i]
        
        # Check tour header
        tour_m = re.search(r'\b(\d+\s*Тур)\b', line, re.I)
        if tour_m:
            current_tour = tour_m.group(1).title()
            i += 1
            continue
            
        # Check pair on single line: "P1 -- P2" or "P1 - P2"
        # Avoid lines like "1 Тур - 13.09. Монголия" or "Матч 1"
        is_single_pair = False
        p1, p2 = None, None
        
        if ('--' in line or (' - ' in line and not any(k in line.lower() for k in ['тур -', 'турнир', 'правила', 'http']))):
            parts = re.split(r'\s*(?:--|\s-\s)\s*', line)
            if len(parts) == 2 and parts[0] and parts[1]:
                p1, p2 = parts[0].strip(), parts[1].strip()
                # Check that neither is a score or word "Матч"
                if not score_re.match(p1) and not score_re.match(p2) and not 'матч' in p1.lower() and len(p1) < 30 and len(p2) < 30:
                    is_single_pair = True
                    
        # Check pair across 3 lines: P1 \n vs \n P2
        if not is_single_pair and i + 2 < n and content_lines[i+1].lower() in ['vs', 'v']:
            cand1 = content_lines[i].strip()
            cand2 = content_lines[i+2].strip()
            if not score_re.match(cand1) and not score_re.match(cand2) and len(cand1) < 30 and len(cand2) < 30:
                p1, p2 = cand1, cand2
                is_single_pair = True
                i += 2  # skip 'vs' and P2
                
        if is_single_pair:
            p1_clean = clean_alias(p1)
            p2_clean = clean_alias(p2)
            
            # Now inspect subsequent lines for scores (usually 1 or 2 scores)
            j = i + 1
            pair_scores = []
            while j < n and len(pair_scores) < 2:
                sub_line = content_lines[j]
                
                # If we encounter another pair or tour or end, break
                if re.search(r'\b\d+\s*Тур\b', sub_line, re.I) or '--' in sub_line or ' - ' in sub_line or (j+1 < n and content_lines[j+1].lower() in ['vs', 'v']):
                    break
                    
                sm = score_re.match(sub_line)
                if sm:
                    s1 = int(sm.group(1))
                    s2 = int(sm.group(2))
                    extra = sm.group(3).strip().lower()
                    ot = bool(re.search(r'(от|пк|пен|bull|бул)', extra))
                    tech = bool(re.search(r'(тп|техн)', extra))
                    pair_scores.append((s1, s2, ot, tech, sub_line))
                elif any(k in sub_line.lower() for k in ['видео', 'демка', 'video', 'здесь', 'в1', 'в2', '//', 'матч']):
                    pass # ignore media metadata line
                else:
                    # might be empty or unparsed note
                    if not score_re.search(sub_line):
                        # if not score and not media, stop looking for scores for this pair
                        if len(sub_line) > 10:
                            break
                j += 1
                
            for s1, s2, ot, tech, raw_s in pair_scores:
                matches.append({
                    "season": season,
                    "league": league,
                    "tour": current_tour,
                    "p1": p1_clean,
                    "p2": p2_clean,
                    "s1": s1,
                    "s2": s2,
                    "ot": ot,
                    "tech": tech,
                    "source": f"wiki_page_{pid}",
                    "raw": f"{p1} vs {p2}: {raw_s}"
                })
            i = j - 1
            
        i += 1
        
    return matches

all_parsed_matches = []
print(f"{'Season':<10} | {'League':<15} | {'PID':<10} | {'Matches':<8} | {'Sample Match'}")
print("-" * 75)

for cal in CALENDARS:
    url = f"https://vk.ru/page-66162180_{cal['pid']}"
    req = urllib.request.Request(url, headers=headers)
    try:
        html = urllib.request.urlopen(req, context=ctx).read().decode('windows-1251', errors='ignore')
        matches = parse_calendar_page(html, cal['season'], cal['league'], cal['pid'])
        all_parsed_matches.extend(matches)
        sample = matches[0]['raw'] if matches else "NONE"
        print(f"{cal['season']:<10} | {cal['league']:<15} | {cal['pid']:<10} | {len(matches):<8} | {sample[:35]}")
    except Exception as e:
        print(f"{cal['season']:<10} | {cal['league']:<15} | {cal['pid']:<10} | ERROR: {e}")

print("-" * 75)
print(f"Total wiki matches parsed: {len(all_parsed_matches)}")

# Save to wiki_seasons_matches.json
with open("wiki_seasons_matches.json", "w", encoding="utf-8") as f:
    json.dump(all_parsed_matches, f, ensure_ascii=False, indent=2)

# Check Aoshi specifically
aoshi_matches = [m for m in all_parsed_matches if m['p1'] == 'Aoshi' or m['p2'] == 'Aoshi']
print(f"\nTotal Aoshi matches in wiki: {len(aoshi_matches)}")
for am in aoshi_matches:
    print(f"  {am['season']} ({am['league']}) [{am['tour']}]: {am['p1']} {am['s1']}:{am['s2']} {am['p2']} {'(OT)' if am['ot'] else ''}")
