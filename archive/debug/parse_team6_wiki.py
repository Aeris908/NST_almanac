import urllib.request, re, sys, html

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for name, pid in [("Высшая лига", "53638616"), ("Средняя лига", "53638617")]:
    req = urllib.request.Request(f'https://vk.com/page-66162180_{pid}', headers=headers)
    raw = urllib.request.urlopen(req, timeout=10).read().decode('cp1251', errors='ignore')
    # find all match pairs and scores
    print(f"\n==================== VI Командный: {name} ====================")
    rows = re.findall(r'([^<>]+?)\s*vs\s*([^<>]+?)\s*</td>.*?<b>(\d+:\d+|ТП)</b>', raw, re.DOTALL)
    print(f"Found matches with scores: {len(rows)}")
    for t1, t2, sc in rows[:15]:
        t1_c = re.sub(r'\s+', ' ', html.unescape(t1)).strip()
        t2_c = re.sub(r'\s+', ' ', html.unescape(t2)).strip()
        print(f"  {t1_c} vs {t2_c} -> {sc}")
