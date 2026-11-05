import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('special_tournaments_data.json', 'r', encoding='utf-8') as f:
    spec = json.load(f)

print("Special tournaments:")
for t in spec:
    matches_cnt = len(t.get('matches', []))
    print(f"  {t['id']}: '{t['title']}' | category: '{t['category']}' | matches: {matches_cnt}")

with open('team_tournaments_data.json', 'r', encoding='utf-8') as f:
    teams = json.load(f)

print("\nTeam tournaments:")
for t in teams:
    matches_cnt = len(t.get('matches', []))
    print(f"  {t['id']}: '{t['title']}' | matches: {matches_cnt}")
