import json, sys

sys.stdout.reconfigure(encoding='utf-8')

for fname in ["wiki_seasons_matches.json", "vk_seasons_matches.json", "season_all_matches.json"]:
    try:
        data = json.load(open(fname, encoding='utf-8'))
        d_matches = [m for m in data if 'davit' in str(m).lower() or 'давит' in str(m).lower()]
        print(f"{fname}: found {len(d_matches)} matches with Davitel")
        for m in d_matches[:5]:
            print("  ", m)
    except Exception as e:
        print(f"{fname}: error {e}")
