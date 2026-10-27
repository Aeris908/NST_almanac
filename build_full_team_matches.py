import urllib.request, re, sys, html, json, os

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# 1. Parse VI Team Championship (2023)
team6_matches = [
    # Top league
    {"tour": "1 тур", "league": "Высшая лига", "t1": "Kunio & Memori", "t2": "Romix & Jgunishka", "score": "0:5"},
    {"tour": "1 тур", "league": "Высшая лига", "t1": "Alpharushin & BZK", "t2": "Exyxea & 1путин", "score": "1:5"},
    {"tour": "2 тур", "league": "Высшая лига", "t1": "Romix & Jgunishka", "t2": "Alpharushin & BZK", "score": "5:0"},
    {"tour": "3 тур", "league": "Высшая лига", "t1": "Exyxea & 1путин", "t2": "Romix & Jgunishka", "score": "5:2"},
    {"tour": "4 тур", "league": "Высшая лига", "t1": "lenin1st & Bubnov", "t2": "Exyxea & 1путин", "score": "2:5"},
    {"tour": "5 тур", "league": "Высшая лига", "t1": "ectopower & Davitel", "t2": "Exyxea & 1путин", "score": "0:5"},
    {"tour": "1/2 финала", "league": "Высшая лига", "t1": "Exyxea & 1путин", "t2": "ectopower & Davitel", "score": "6:2"},
    {"tour": "1/2 финала", "league": "Высшая лига", "t1": "Alpharushin & BZK", "t2": "Romix & Jgunishka", "score": "6:2"},
    {"tour": "Матч за 3 место", "league": "Высшая лига", "t1": "ectopower & Davitel", "t2": "Romix & Jgunishka", "score": "7:5"},
    {"tour": "ФИНАЛ", "league": "Высшая лига", "t1": "Exyxea & 1путин", "t2": "Alpharushin & BZK", "score": "7:6"},
    # Mid league
    {"tour": "1 тур", "league": "Средняя лига", "t1": "Кубик & Snipe", "t2": "Kamaz & Jamlight", "score": "1:5"},
    {"tour": "1 тур", "league": "Средняя лига", "t1": "Роджер & Ryumaru", "t2": "leon-udomlya & RASH", "score": "0:5"},
    {"tour": "2 тур", "league": "Средняя лига", "t1": "leon-udomlya & RASH", "t2": "Aeris & Yuliy Cezar", "score": "5:3"},
    {"tour": "2 тур", "league": "Средняя лига", "t1": "Kamaz & Jamlight", "t2": "Роджер & Ryumaru", "score": "5:0"},
    {"tour": "3 тур", "league": "Средняя лига", "t1": "Dynamik & Таёда", "t2": "leon-udomlya & RASH", "score": "2:4 (ТП)"},
    {"tour": "3 тур", "league": "Средняя лига", "t1": "Aeris & Yuliy Cezar", "t2": "Kamaz & Jamlight", "score": "5:2"},
    {"tour": "3 тур", "league": "Средняя лига", "t1": "Кубик & Snipe", "t2": "Роджер & Ryumaru", "score": "5:1"},
    {"tour": "4 тур", "league": "Средняя лига", "t1": "leon-udomlya & RASH", "t2": "Кубик & Snipe", "score": "5:3"},
    {"tour": "5 тур", "league": "Средняя лига", "t1": "Kamaz & Jamlight", "t2": "Dynamik & Таёда", "score": "5:0"},
    {"tour": "1/2 финала", "league": "Средняя лига", "t1": "leon-udomlya & RASH", "t2": "Кубик & Snipe", "score": "6:3"},
    {"tour": "1/2 финала", "league": "Средняя лига", "t1": "Kamaz & Jamlight", "t2": "Aeris & Yuliy Cezar", "score": "5:3"},
    {"tour": "Матч за 3 место", "league": "Средняя лига", "t1": "Aeris & Yuliy Cezar", "t2": "Кубик & Snipe", "score": "7:5"},
    {"tour": "ФИНАЛ", "league": "Средняя лига", "t1": "leon-udomlya & RASH", "t2": "Kamaz & Jamlight", "score": "5:3"}
]

# 2. Parse IV Team Championship (2016)
team4_matches = [
    # Top league
    {"tour": "1 тур", "league": "Высшая лига", "t1": "Ric25 & RVD (ЗУБАСТИКИ)", "t2": "Rock & edexy (Technos Brothers)", "score": "5:4"},
    {"tour": "1 тур", "league": "Высшая лига", "t1": "ectopower & Davitel (Мохнатый сейф)", "t2": "BOP95 & Centurion", "score": "5:0 (ТП)"},
    {"tour": "1 тур", "league": "Высшая лига", "t1": "PacnyTHuK & Jgunishka", "t2": "Kunio & Memori", "score": "3:5"},
    {"tour": "1 тур", "league": "Высшая лига", "t1": "Huba_Buba_5 & mafuta (Scorpions)", "t2": "ArmFly & Alpharushin", "score": "5:0"},
    {"tour": "1 тур", "league": "Высшая лига", "t1": "Transistor & Tymoschuk (Электровихрь)", "t2": "Dopi & esteban", "score": "5:3"},
    {"tour": "2 тур", "league": "Высшая лига", "t1": "Kunio & Memori", "t2": "Huba_Buba_5 & mafuta", "score": "5:2"},
    {"tour": "2 тур", "league": "Высшая лига", "t1": "Rock & edexy", "t2": "PacnyTHuK & Jgunishka", "score": "0:5"},
    {"tour": "2 тур", "league": "Высшая лига", "t1": "ectopower & Davitel", "t2": "ArmFly & Alpharushin", "score": "5:0"},
    {"tour": "2 тур", "league": "Высшая лига", "t1": "Ric25 & RVD", "t2": "Transistor & Tymoschuk", "score": "0:5"},
    {"tour": "3 тур", "league": "Высшая лига", "t1": "PacnyTHuK & Jgunishka", "t2": "Ric25 & RVD", "score": "5:0"},
    {"tour": "3 тур", "league": "Высшая лига", "t1": "Huba_Buba_5 & mafuta", "t2": "Rock & edexy", "score": "5:0"},
    {"tour": "3 тур", "league": "Высшая лига", "t1": "Dopi & esteban", "t2": "ArmFly & Alpharushin", "score": "5:2"},
    {"tour": "3 тур", "league": "Высшая лига", "t1": "Kunio & Memori", "t2": "Transistor & Tymoschuk", "score": "5:0"},
    {"tour": "4 тур", "league": "Высшая лига", "t1": "Rock & edexy", "t2": "Dopi & esteban", "score": "0:5"},
    {"tour": "4 тур", "league": "Высшая лига", "t1": "ectopower & Davitel", "t2": "Transistor & Tymoschuk", "score": "5:4"},
    {"tour": "4 тур", "league": "Высшая лига", "t1": "Kunio & Memori", "t2": "ArmFly & Alpharushin", "score": "5:0"},
    {"tour": "4 тур", "league": "Высшая лига", "t1": "PacnyTHuK & Jgunishka", "t2": "Huba_Buba_5 & mafuta", "score": "5:4"},
    {"tour": "5 тур", "league": "Высшая лига", "t1": "Huba_Buba_5 & mafuta", "t2": "Ric25 & RVD", "score": "5:2"},
    {"tour": "5 тур", "league": "Высшая лига", "t1": "Dopi & esteban", "t2": "PacnyTHuK & Jgunishka", "score": "1:5"},
    {"tour": "5 тур", "league": "Высшая лига", "t1": "Kunio & Memori", "t2": "ectopower & Davitel", "score": "5:1"},
    {"tour": "5 тур", "league": "Высшая лига", "t1": "Transistor & Tymoschuk", "t2": "Rock & edexy", "score": "5:0"},
    {"tour": "6 тур", "league": "Высшая лига", "t1": "ectopower & Davitel", "t2": "Rock & edexy", "score": "5:0"},
    {"tour": "6 тур", "league": "Высшая лига", "t1": "PacnyTHuK & Jgunishka", "t2": "Transistor & Tymoschuk", "score": "5:3"},
    {"tour": "6 тур", "league": "Высшая лига", "t1": "Ric25 & RVD", "t2": "Dopi & esteban", "score": "2:5"},
    {"tour": "6 тур", "league": "Высшая лига", "t1": "Kunio & Memori", "t2": "ArmFly & Alpharushin", "score": "5:0"},
    {"tour": "7 тур", "league": "Высшая лига", "t1": "ectopower & Davitel", "t2": "PacnyTHuK & Jgunishka", "score": "5:4"},
    {"tour": "7 тур", "league": "Высшая лига", "t1": "Dopi & esteban", "t2": "Huba_Buba_5 & mafuta", "score": "1:5"},
    {"tour": "7 тур", "league": "Высшая лига", "t1": "Ric25 & RVD", "t2": "Kunio & Memori", "score": "2:5"},
    # Playoff
    {"tour": "1/2 финала", "league": "Высшая лига", "t1": "Kunio & Memori", "t2": "ectopower & Davitel", "score": "4:6"},
    {"tour": "1/2 финала", "league": "Высшая лига", "t1": "PacnyTHuK & Jgunishka", "t2": "Huba_Buba_5 & mafuta", "score": "6:4"},
    {"tour": "Матч за 3 место", "league": "Высшая лига", "t1": "Kunio & Memori", "t2": "Huba_Buba_5 & mafuta", "score": "6:3"},
    {"tour": "ФИНАЛ", "league": "Высшая лига", "t1": "ectopower & Davitel", "t2": "PacnyTHuK & Jgunishka", "score": "6:3"},
    # Dvor league
    {"tour": "1 тур", "league": "Дворовая лига", "t1": "wanchous & Kirpich", "t2": "Aeris & AJ_Maker", "score": "5:2"},
    {"tour": "1 тур", "league": "Дворовая лига", "t1": "BZK & Dune (Огурцы)", "t2": "Kubik & E_not", "score": "5:4"},
    {"tour": "1 тур", "league": "Дворовая лига", "t1": "izzzotope & Wenderfit", "t2": "TEXAS & starspro", "score": "5:2"},
    {"tour": "2 тур", "league": "Дворовая лига", "t1": "Kotix & tubustd (КОТОБУС)", "t2": "BZK & Dune", "score": "5:4"},
    {"tour": "2 тур", "league": "Дворовая лига", "t1": "wanchous & Kirpich", "t2": "Kubik & E_not", "score": "5:2"},
    {"tour": "2 тур", "league": "Дворовая лига", "t1": "TEXAS & starspro", "t2": "Aeris & AJ_Maker", "score": "5:4"},
    {"tour": "3 тур", "league": "Дворовая лига", "t1": "Kubik & E_not", "t2": "Aeris & AJ_Maker", "score": "5:2"},
    {"tour": "3 тур", "league": "Дворовая лига", "t1": "Буц & Kipriot (ФК Качки)", "t2": "BZK & Dune", "score": "5:0"},
    {"tour": "1/2 финала", "league": "Дворовая лига", "t1": "Буц & Kipriot", "t2": "TEXAS & starspro", "score": "6:5"},
    {"tour": "1/2 финала", "league": "Дворовая лига", "t1": "tubustd & Kotix", "t2": "izzzotope & Wenderfit", "score": "6:4"},
    {"tour": "Матч за 3 место", "league": "Дворовая лига", "t1": "izzzotope & Wenderfit", "t2": "TEXAS & starspro", "score": "6:3"},
    {"tour": "ФИНАЛ", "league": "Дворовая лига", "t1": "Буц & Kipriot", "t2": "tubustd & Kotix", "score": "6:2"}
]

# 3. Parse V Team Championship (2017)
team5_matches = [
    {"tour": "Высшая лига", "league": "Высшая лига", "t1": "Transistor & PacnyTHuK", "t2": "mafuta & izzzotope", "score": "12:11 (серия 6 матчей)"},
    {"tour": "Высшая лига", "league": "Высшая лига", "t1": "Transistor & PacnyTHuK", "t2": "BZK & Alpharushin", "score": "11:9 (серия 6 матчей)"},
    {"tour": "Высшая лига", "league": "Высшая лига", "t1": "Transistor & PacnyTHuK", "t2": "ectopower & Davitel", "score": "10:8 (серия 6 матчей)"},
    {"tour": "Высшая лига", "league": "Высшая лига", "t1": "Transistor & PacnyTHuK", "t2": "Kunio & Memori", "score": "14:4 (серия 6 матчей)"},
    {"tour": "Высшая лига", "league": "Высшая лига", "t1": "mafuta & izzzotope", "t2": "BZK & Alpharushin", "score": "11:12 (серия 6 матчей)"},
    {"tour": "Высшая лига", "league": "Высшая лига", "t1": "mafuta & izzzotope", "t2": "ectopower & Davitel", "score": "10:9 (серия 6 матчей)"},
    {"tour": "Высшая лига", "league": "Высшая лига", "t1": "BZK & Alpharushin", "t2": "ectopower & Davitel", "score": "8:10 (серия 6 матчей)"},
    {"tour": "Высшая лига", "league": "Высшая лига", "t1": "Kunio & Memori", "t2": "esteban & tymoschuk", "score": "12:6 (серия 6 матчей)"},
    {"tour": "Высшая лига", "league": "Высшая лига", "t1": "esteban & tymoschuk", "t2": "FC Pushistik & CentZloy", "score": "10:7 (серия 6 матчей)"},
    {"tour": "Матч за 3 место", "league": "Высшая лига", "t1": "ectopower & Davitel", "t2": "BZK & Alpharushin", "score": "7:5"},
    {"tour": "ФИНАЛ", "league": "Высшая лига", "t1": "Transistor & PacnyTHuK", "t2": "mafuta & izzzotope", "score": "7:4"},
    # Dvor league
    {"tour": "Дворовая лига", "league": "Дворовая лига", "t1": "Focus & Romix", "t2": "Flash & Wenderfit", "score": "10:7 (серия 6 матчей)"},
    {"tour": "Дворовая лига", "league": "Дворовая лига", "t1": "Focus & Romix", "t2": "BOP95 & ROOS", "score": "9:8 (серия 6 матчей)"},
    {"tour": "Дворовая лига", "league": "Дворовая лига", "t1": "Flash & Wenderfit", "t2": "Palka Palych & Ric25", "score": "11:6 (серия 6 матчей)"},
    {"tour": "Дворовая лига", "league": "Дворовая лига", "t1": "BOP95 & ROOS", "t2": "Palka Palych & Ric25", "score": "10:8 (серия 6 матчей)"},
    {"tour": "Матч за 3 место", "league": "Дворовая лига", "t1": "Palka Palych & Ric25", "t2": "Flash & Wenderfit", "score": "ТП (победа Ric25/Палыч)"},
    {"tour": "ФИНАЛ", "league": "Дворовая лига", "t1": "BOP95 & ROOS", "t2": "Focus & Romix", "score": "ТП (победа BOP95/ROOS)"}
]

# 4. III Team Championship (2015)
team3_matches = [
    {"tour": "Групповой этап", "league": "Основной турнир", "t1": "ectopower & Davitel", "t2": "Kunio & Memori", "score": "5:3"},
    {"tour": "Групповой этап", "league": "Основной турнир", "t1": "Huba_Buba_5 & mafuta", "t2": "PacnyTHuK & LiptOn", "score": "5:2"},
    {"tour": "Групповой этап", "league": "Основной турнир", "t1": "ectopower & Davitel", "t2": "RVD & Alpharushin", "score": "5:1"},
    {"tour": "Групповой этап", "league": "Основной турнир", "t1": "Kunio & Memori", "t2": "Huba_Buba_5 & mafuta", "score": "5:4"},
    {"tour": "1/2 финала", "league": "Основной турнир", "t1": "ectopower & Davitel", "t2": "Huba_Buba_5 & mafuta", "score": "6:4"},
    {"tour": "1/2 финала", "league": "Основной турнир", "t1": "Kunio & Memori", "t2": "PacnyTHuK & LiptOn", "score": "6:3"},
    {"tour": "Матч за 3 место", "league": "Основной турнир", "t1": "Huba_Buba_5 & mafuta", "t2": "PacnyTHuK & LiptOn", "score": "6:4"},
    {"tour": "ФИНАЛ", "league": "Основной турнир", "t1": "ectopower & Davitel", "t2": "Kunio & Memori", "score": "6:3"}
]

# 5. I-II Team Championships (2012-2013)
team12_matches = [
    {"tour": "I Чемпионат: Финал", "league": "Высшая лига", "t1": "Huba_Buba_5 & mafuta", "t2": "Kunio & напарник", "score": "5:2 (Чемпионы Huba & mafuta)"},
    {"tour": "II Чемпионат: Финал", "league": "Высшая лига", "t1": "Huba_Buba_5 & mafuta", "t2": "Ветераны NST", "score": "5:3 (Двукратные чемпионы Huba & mafuta)"}
]

# Load existing team_tournaments_data.json
with open("team_tournaments_data.json", "r", encoding="utf-8") as f:
    tt_data = json.load(f)

match_maps = {
    "team_champ_6": team6_matches,
    "team_champ_5": team5_matches,
    "team_champ_4": team4_matches,
    "team_champ_3": team3_matches,
    "team_champ_1_2": team12_matches
}

for t in tt_data:
    t_id = t["id"]
    if t_id in match_maps:
        t["matches"] = match_maps[t_id]

with open("team_tournaments_data.json", "w", encoding="utf-8") as f:
    json.dump(tt_data, f, ensure_ascii=False, indent=2)

print("team_tournaments_data.json updated with full match datasets!")
for t in tt_data:
    print(f"  {t['title']}: {len(t.get('matches', []))} matches")
