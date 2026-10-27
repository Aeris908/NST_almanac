import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('special_tournaments_data.json', encoding='utf-8') as f:
    st_data = json.load(f)

for t in st_data:
    print(f"\n================ {t.get('title')} ({t.get('year')}) ================")
    print(f"Format: {t.get('format')} | Champion: {t.get('champion')} | Runner-up: {t.get('runner_up')}")
    print(f"Groups: {len(t.get('groups', []))} | Playoff: {len(t.get('playoff', []))} | Matches: {len(t.get('matches', []))}")
    if t.get('playoff'):
        print("Sample playoff:", t.get('playoff')[:3])
