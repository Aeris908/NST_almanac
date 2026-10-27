import json, csv, sys

sys.stdout.reconfigure(encoding='utf-8')

with open("special_tournaments_data.json", "r", encoding="utf-8") as f:
    st_data = json.load(f)

# 1. Enrich Youth 2
for t in st_data:
    if t["id"] == "youth_championship_2":
        t_matches = []
        for p in t.get("playoff", []):
            t_matches.append({
                "tour": p.get("stage", "Плей-офф"),
                "league": "Плей-офф (до 5-6 побед)",
                "p1": p.get("t1"),
                "p2": p.get("t2"),
                "score": p.get("score")
            })
        t["matches"] = t_matches

    # 2. Enrich Club Offseason Goal 4
    if t["id"] == "club_offseason_goal4":
        club_m = []
        with open("special_tournaments/club_matches.csv", encoding="utf-8") as cf:
            reader = csv.reader(cf)
            next(reader, None)
            for row in reader:
                if len(row) > 6 and row[2] and row[5] and row[3] and row[4]:
                    sc1 = row[3].strip()
                    sc2 = row[4].strip()
                    if sc1.isdigit() and sc2.isdigit() and (int(sc1) > 0 or int(sc2) > 0):
                        lig = "Высшая (Премьер)" if row[15] == 'в' else "Молодёжная лига"
                        club_m.append({
                            "tour": f"Баттл #{row[0]} (Круг {row[1]})",
                            "league": lig,
                            "p1": row[2].strip(),
                            "p2": row[5].strip(),
                            "score": f"{sc1}:{sc2}"
                        })
        t["matches"] = club_m[:50] # Top 50 major club matches

with open("special_tournaments_data.json", "w", encoding="utf-8") as f:
    json.dump(st_data, f, ensure_ascii=False, indent=2)

print("special_tournaments_data.json successfully enriched with matches for Youth 2 and Club Offseason!")
for t in st_data:
    print(f"  {t['title']}: {len(t.get('matches', []))} matches")
