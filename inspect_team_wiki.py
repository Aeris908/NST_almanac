import urllib.request, re, sys, json

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Let's inspect the pages from VI, V, IV championships
pages = [
    ("VI Командный (Регламент)", "53637878"),
    ("VI Командный (Вышка)", "53638616"),
    ("VI Командный (Средняя)", "53638617"),
    ("V Командный (Регламент)", "52082636"),
    ("IV Командный (Регламент)", "50469709"),
    ("IV Командный (Календарь)", "50560019"),
]

for title, pid in pages:
    url = f"https://vk.com/page-66162180_{pid}"
    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, timeout=10).read().decode('cp1251', errors='ignore')
        # find teams, winners or body
        body = re.search(r'<div class="wk_text">(.*?)</div>\s*</div>', html, re.DOTALL)
        if body:
            txt = re.sub(r'<[^>]+>', ' ', body.group(1))
            txt = re.sub(r'\s+', ' ', txt)
            print(f"\n=== {title} (ID {pid}) ===")
            print(txt[:1000])
        else:
            print(f"\n=== {title} (ID {pid}) -> no body ===")
    except Exception as e:
        print(f"\n=== {title} ERR: {e} ===")
