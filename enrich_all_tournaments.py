import json
import sys
import tournament_chronicles_data

sys.stdout.reconfigure(encoding='utf-8')

# 1. Enrich team_tournaments_data.json
try:
    with open('team_tournaments_data.json', 'r', encoding='utf-8') as f:
        teams = json.load(f)
    
    count_t = 0
    for t in teams:
        tid = t.get('id')
        if tid in tournament_chronicles_data.TEAM_CHRONICLES:
            data = tournament_chronicles_data.TEAM_CHRONICLES[tid]
            for k, v in data.items():
                if k not in t or not t[k]:
                    t[k] = v
            count_t += 1
            
    with open('team_tournaments_data.json', 'w', encoding='utf-8') as f:
        json.dump(teams, f, ensure_ascii=False, indent=2)
    print(f"Enriched {count_t} team tournaments in team_tournaments_data.json")
except Exception as e:
    print("Error enriching team tournaments:", e)

# 2. Enrich special_tournaments_data.json
try:
    with open('special_tournaments_data.json', 'r', encoding='utf-8') as f:
        specs = json.load(f)
        
    count_s = 0
    for s in specs:
        sid = s.get('id')
        if sid in tournament_chronicles_data.SPECIAL_CHRONICLES:
            data = tournament_chronicles_data.SPECIAL_CHRONICLES[sid]
            for k, v in data.items():
                if k not in s or not s[k]:
                    s[k] = v
            count_s += 1
            
    with open('special_tournaments_data.json', 'w', encoding='utf-8') as f:
        json.dump(specs, f, ensure_ascii=False, indent=2)
    print(f"Enriched {count_s} special tournaments in special_tournaments_data.json")
except Exception as e:
    print("Error enriching special tournaments:", e)
