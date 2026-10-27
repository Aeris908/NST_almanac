import urllib.request, ssl, sys, os

sys.stdout.reconfigure(encoding='utf-8')

extra_downloads = [
    ("youth2_table", "1a9ZAEqTTB4R_k6ib54MrZZ70FRLTrXjd9CfxD07tkVo", "102454828"),
    ("youth2_playoff", "1a9ZAEqTTB4R_k6ib54MrZZ70FRLTrXjd9CfxD07tkVo", "92507861"),
    ("club_matches", "1L9cdKCwKo90dx709FhhC45C8l6gKP5dJjWhRSEwtIkY", "1594898980"),
]

for key, sid, gid in extra_downloads:
    url = f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&gid={gid}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    content = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    out_path = os.path.join("special_tournaments", f"{key}.csv")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Downloaded {key}.csv: {len(content.splitlines())} lines")
