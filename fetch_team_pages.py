import urllib.request, re, sys, html, os

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0'}

os.makedirs("team_tournaments", exist_ok=True)

pages = [
    ("team4_calendar", "50560019"),
    ("team6_premier", "53638616"),
    ("team6_mid", "53638617"),
]

for key, pid in pages:
    req = urllib.request.Request(f"https://vk.com/page-66162180_{pid}", headers=headers)
    h = urllib.request.urlopen(req, timeout=10).read().decode('cp1251', errors='ignore')
    body = re.search(r'<div class="wk_text">(.*?)</div>\s*</div>', h, re.DOTALL)
    if body:
        txt = html.unescape(re.sub(r'<[^>]+>', ' ', body.group(1)))
        txt = re.sub(r'\s+', ' ', txt)
        with open(f"team_tournaments/{key}.txt", "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"Saved team_tournaments/{key}.txt: {len(txt)} chars")
