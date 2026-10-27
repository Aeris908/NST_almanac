import urllib.request, ssl, sys, re, os, csv

sys.stdout.reconfigure(encoding='utf-8')
os.makedirs("special_tournaments", exist_ok=True)

sheets = [
    ("youth2_table", "2-й Молодёжный Чемпионат (Таблица)", "1a9ZAEqTTB4R_k6ib54MrZZ70FRLTrXjd9CfxD07tkVo", "0"),
    ("youth2_playoff", "2-й Молодёжный Чемпионат (Календарь/Плей-офф)", "1a9ZAEqTTB4R_k6ib54MrZZ70FRLTrXjd9CfxD07tkVo", "1526661752"),
    ("club_premier", "Клубное Межсезонье: Премьер-Лига", "1L9cdKCwKo90dx709FhhC45C8l6gKP5dJjWhRSEwtIkY", "1912677786"),
    ("club_youth", "Клубное Межсезонье: Молодёжная лига", "1L9cdKCwKo90dx709FhhC45C8l6gKP5dJjWhRSEwtIkY", "1489881286"),
    ("solo_2021", "Сольный Турнир Goal 3 (Осень 2021)", "1aPMWeE2yk4YiZPgtcXGpAALG4xJpnrJRZAxks6GSL5A", "0"),
    ("penalty3", "3-й Турнир по пенальти", "18lWAb4YTTEbdh8Kk0Q0Y62O0G9lkWxtbQ91tL_AZc4Y", "0"),
    ("blitz10", "X Юбилейный Блиц-турнир", "1o5EMCrZXK-DnioRxn2oh_eh7ZLP3WWCZEhjZ3i8Lx7o", "0"),
    ("blitz9", "IX Блиц-турнир", "1fSHXgvBuJ1NyEfRj8S18OwC_BMV7plGcXGXRoCoKd2E", "0"),
    ("goal4_solo_rating", "Сольный рейтинг Goal 4", "1h9cCMudq8SW_rp3kn5u51kgRyR8Zfwqv5-rKVAMhfM0", "0"),
]

for file_key, name, sid, gid in sheets:
    url = f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&gid={gid}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        content = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        out_path = os.path.join("special_tournaments", f"{file_key}.csv")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        lines = [l for l in content.splitlines() if l.strip()]
        print(f"OK: {name} -> saved {len(lines)} lines to {out_path}")
        for l in lines[:5]:
            print("   ", l[:100])
    except Exception as e:
        print(f"ERR: {name} -> {e}")
