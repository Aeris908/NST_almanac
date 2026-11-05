import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('team_tournaments_data.json', encoding='utf-8') as f:
    tt_data = json.load(f)

print(f"Total team tournaments: {len(tt_data)}")
for t in tt_data:
    print(f"- {t.get('title')} ({t.get('year')}) | Matches: {len(t.get('matches', []))} | Playoff: {len(t.get('playoff', []))}")
