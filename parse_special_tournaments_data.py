import csv, json, re, os, sys

sys.stdout.reconfigure(encoding='utf-8')

# 1. Alias cleaner
ALIAS_MAP = {
    'pacnythuk': 'PacnyTHuK', 'распутник': 'PacnyTHuK', 'rasputnyk': 'PacnyTHuK', 'rasputnik': 'PacnyTHuK',
    'ectopower': 'ectoPower', 'екто': 'ectoPower', 'экто': 'ectoPower',
    'bzk': 'BZK', 'cyneprepou4uk': 'BZK', 'супергеройчик': 'BZK',
    'mafuta': 'mafuta', 'мафута': 'mafuta',
    'tymoschuk': 'Tymoschuk', 'тимощук': 'Tymoschuk', 'тимоха': 'Tymoschuk',
    'kunio': 'Kunio', 'кунио': 'Kunio',
    'romix': 'Romix', 'ромикс': 'Romix',
    'rvd': 'RVD', 'рвд': 'RVD',
    'edexy': 'edexy', 'эдекси': 'edexy',
    'memori': 'Memori', 'мемори': 'Memori',
    'alpharushin': 'Alpharushin', 'альфа': 'Alpharushin',
    'dune': 'Dune', 'дюн': 'Dune',
    'jgunishka': 'Jgunishka', 'жгунишка': 'Jgunishka',
    'bop95': 'BOP95', 'вор95': 'BOP95', 'bop': 'BOP95',
    'kubik': 'Kubik', 'кубик': 'Kubik',
    'aoshi': 'Aoshi', 'аоши': 'Aoshi',
    'centurion': 'Centurion', 'центурион': 'Centurion', 'centzloy': 'Centurion',
    'ric25': 'Ric25', 'рик25': 'Ric25', 'рик': 'Ric25',
    'davitel': 'Davitel', 'давитель': 'Davitel',
    'kot-from-ussr': 'Kot-from-ussr', 'кот': 'Kot-from-ussr',
    'fc pushistik': 'FC Pushistik', 'пушистик': 'FC Pushistik',
    'lipton': 'LiptOn', 'липтон': 'LiptOn',
    'rock': 'Rock', 'рок': 'Rock',
    'jamlight': 'Jamlight', 'джем': 'Jamlight',
    'buts': 'Буц', 'буц': 'Буц',
    'transistor': 'Transistor', 'транзистор': 'Transistor',
    'izzzotope': 'izzzotope', 'изотоп': 'izzzotope',
    'aeris': 'Aeris', 'аэрис': 'Aeris',
    'juliy_cezar': 'Juliy_Cezar', 'yuliy_cezar': 'Juliy_Cezar', 'цезарь': 'Juliy_Cezar',
    'wanchous': 'wanchous', 'ванчоус': 'wanchous',
    'leonudomlya': 'leonudomlya', 'леонудомля': 'leonudomlya',
    'dopi': 'Dopi', 'допи': 'Dopi',
    'kipriot': 'Kipriot', 'киприот': 'Kipriot',
    'chocopie': 'Chocopie', 'чокопай': 'Chocopie',
    'gilmour': 'Gilmour', 'гилмор': 'Gilmour',
}

def clean_player_name(raw):
    s = raw.strip()
    s = re.sub(r'^[0-9]+[\.\)\s]+', '', s)
    s = re.sub(r'[\U00010000-\U0010ffff]', '', s) # remove emoji
    s = s.strip()
    k = s.lower()
    return ALIAS_MAP.get(k, s)

special_tournaments = []

# ==========================================
# 1. 2-й Молодёжный Чемпионат по Goal 3
# ==========================================
youth2_tables = {
    "Кометы": [
        {"team": "lenin1st & ectoPower", "games": 6, "w": 17, "wp": 1, "lp": 0, "l": 6, "pts": 53},
        {"team": "Bender & mafuta", "games": 6, "w": 15, "wp": 1, "lp": 2, "l": 6, "pts": 49},
        {"team": "Daria_P & Memori", "games": 6, "w": 11, "wp": 2, "lp": 4, "l": 7, "pts": 41},
        {"team": "SaikoDelph & Jgunishka", "games": 6, "w": 8, "wp": 3, "lp": 2, "l": 11, "pts": 32},
        {"team": "Thorogood & Ric25", "games": 6, "w": 9, "wp": 2, "lp": 0, "l": 13, "pts": 31},
        {"team": "Aoshi & Aeris", "games": 6, "w": 8, "wp": 1, "lp": 2, "l": 13, "pts": 28},
        {"team": "Dynamik & Dune", "games": 6, "w": 6, "wp": 0, "lp": 0, "l": 18, "pts": 18}
    ],
    "Метеоры": [
        {"team": "sokol & PacnyTHuK", "games": 5, "w": 19, "wp": 1, "lp": 0, "l": 0, "pts": 59},
        {"team": "E_not & Tymoschuk", "games": 5, "w": 12, "wp": 2, "lp": 0, "l": 6, "pts": 40},
        {"team": "Islambolt Pornce & Kunio", "games": 5, "w": 9, "wp": 1, "lp": 0, "l": 10, "pts": 29},
        {"team": "Kubik & Juliy_Cezar", "games": 5, "w": 6, "wp": 0, "lp": 2, "l": 12, "pts": 20},
        {"team": "Palka Palych & XakoFEAR", "games": 5, "w": 6, "wp": 0, "lp": 1, "l": 13, "pts": 19},
        {"team": "Metallist & BZK", "games": 5, "w": 4, "wp": 0, "lp": 1, "l": 15, "pts": 13}
    ]
}

youth2_playoff = [
    {"stage": "1/4 финала", "t1": "lenin1st & ectoPower", "t2": "Kubik & Juliy_Cezar", "score": "5:0"},
    {"stage": "1/4 финала", "t1": "E_not & Tymoschuk", "t2": "Daria_P & Memori", "score": "5:0"},
    {"stage": "1/4 финала", "t1": "sokol & PacnyTHuK", "t2": "SaikoDelph & Jgunishka", "score": "5:0"},
    {"stage": "1/4 финала", "t1": "Bender & mafuta", "t2": "Islambolt Pornce & Kunio", "score": "5:2"},
    {"stage": "1/2 финала", "t1": "lenin1st & ectoPower", "t2": "E_not & Tymoschuk", "score": "0:5"},
    {"stage": "1/2 финала", "t1": "sokol & PacnyTHuK", "t2": "Bender & mafuta", "score": "5:0"},
    {"stage": "Матч за 3-е место", "t1": "lenin1st & ectoPower", "t2": "Bender & mafuta", "score": "5:6"},
    {"stage": "ФИНАЛ", "t1": "E_not & Tymoschuk", "t2": "sokol & PacnyTHuK", "score": "2:6"}
]

special_tournaments.append({
    "id": "youth_championship_2",
    "title": "2-й Молодёжный Чемпионат по Goal 3",
    "category": "Молодёжные турниры",
    "season_year": "2018-2019",
    "game": "Goal 3 (NES)",
    "format": "2x2 (Наставник + Новичок)",
    "champion": "sokol & PacnyTHuK",
    "runner_up": "E_not & Tymoschuk",
    "bronze": "Bender & mafuta",
    "fourth": "lenin1st & ectoPower",
    "description": "Официальный командный турнир парного формата: опытные мастера лиги объединились с начинающими игроками (молодёжью) для передачи турнирного опыта. 13 команд в двух дивизионах («Кометы» и «Метеоры»), групповой этап и серия плей-офф до 5-6 побед.",
    "groups": youth2_tables,
    "playoff": youth2_playoff,
    "key_players": ["PacnyTHuK", "Tymoschuk", "mafuta", "ectoPower", "Kunio", "Memori", "Kubik", "Ric25", "Aoshi", "Dune", "Jgunishka", "BZK", "Juliy_Cezar"]
})

# ==========================================
# 2. Клубный Чемпионат по Goal 4 (МЕЖСЕЗОНЬЕ)
# ==========================================
club_premier_table = [
    {"club": "Рединский отряд", "roster": "Tymoschuk (к), Romix, PacnyTHuK", "battles": 8, "w": 8, "games": 29, "gw": 22, "gwp": 2, "glp": 1, "gl": 4, "gf": 166, "ga": 103, "diff": "+63", "pts": 24},
    {"club": "Пластиковый татарин", "roster": "Memori (к), BZK (Cyneprepou4uk), Alpharushin", "battles": 8, "w": 6, "games": 28, "gw": 20, "gwp": 0, "glp": 1, "gl": 7, "gf": 139, "ga": 97, "diff": "+42", "pts": 18},
    {"club": "Яжежал", "roster": "mafuta (к), izzzotope, Буц (Buts)", "battles": 8, "w": 3, "games": 26, "gw": 10, "gwp": 1, "glp": 0, "gl": 15, "gf": 55, "ga": 67, "diff": "-12", "pts": 9},
    {"club": "Геймклуб", "roster": "FC Pushistik (к), Kunio, ectoPower", "battles": 8, "w": 3, "games": 29, "gw": 12, "gwp": 1, "glp": 2, "gl": 14, "gf": 125, "ga": 139, "diff": "-14", "pts": 9},
    {"club": "Мегадрайв", "roster": "Гостевой клуб", "battles": 8, "w": 0, "games": 24, "gw": 0, "gwp": 0, "glp": 0, "gl": 24, "gf": 26, "ga": 105, "diff": "-79", "pts": 0}
]

club_youth_table = [
    {"club": "Пластиковый татарин (мол.)", "roster": "Aeris, Palka Palych", "battles": 7, "w": 7, "games": 25, "gw": 17, "gwp": 4, "glp": 1, "gl": 3, "gf": 82, "ga": 37, "diff": "+45", "pts": 21},
    {"club": "Яжежал (мол.)", "roster": "Dune, Wenderfit", "battles": 8, "w": 5, "games": 27, "gw": 16, "gwp": 1, "glp": 1, "gl": 9, "gf": 104, "ga": 77, "diff": "+27", "pts": 15},
    {"club": "Геймклуб (мол.)", "roster": "Jorko, Jamlight", "battles": 6, "w": 3, "games": 20, "gw": 9, "gwp": 1, "glp": 1, "gl": 9, "gf": 79, "ga": 80, "diff": "-1", "pts": 9},
    {"club": "Рединский отряд (мол.)", "roster": "Juliy_Cezar, Kot-from-ussr", "battles": 5, "w": 1, "games": 19, "gw": 7, "gwp": 0, "glp": 1, "gl": 11, "gf": 69, "ga": 79, "diff": "-10", "pts": 3},
    {"club": "Мегадрайв (мол.)", "roster": "Гостевая молодёжка", "battles": 8, "w": 1, "games": 25, "gw": 3, "gwp": 0, "glp": 2, "gl": 20, "gf": 46, "ga": 107, "diff": "-61", "pts": 3}
]

special_tournaments.append({
    "id": "club_offseason_goal4",
    "title": "Клубный Чемпионат по Goal 4. МЕЖСЕЗОНЬЕ",
    "category": "Межсезонье",
    "season_year": "2018 (Межсезонье)",
    "game": "Goal 4 (Kunio Kun no Nekketsu Soccer League)",
    "format": "Клубная система (Премьер-Лига + Молодёжная лига)",
    "champion": "Рединский отряд (Премьер-Лига) / Пластиковый татарин (Молодёжка)",
    "runner_up": "Пластиковый татарин (Премьер-Лига) / Яжежал (Молодёжка)",
    "bronze": "Яжежал & Геймклуб",
    "description": "Уникальный межсезонный клубный чемпионат NST. Впервые клубы выставили два параллельных эшелона: основной состав (Премьер-Лига звезд) и молодёжные составы клубов. Сыграно более 100 матчей между клубами в сериях мини-баттлов до 3 побед.",
    "premier_league": club_premier_table,
    "youth_league": club_youth_table,
    "key_players": ["Tymoschuk", "Romix", "PacnyTHuK", "Memori", "BZK", "Alpharushin", "mafuta", "Kunio", "ectoPower", "Dune", "Jamlight", "Kot-from-ussr", "Aeris", "Juliy_Cezar", "Буц"]
})

# ==========================================
# 3. Сольный Турнир Goal 3 Осень 2021 (1x1)
# ==========================================
solo_2021_matches = [
    # 1/16
    {"stage": "1/16 финала", "p1": "Jamlight", "p2": "Taeda", "score": "3:1", "games": "2:0, 1:2, 3:1, 3:0"},
    {"stage": "1/16 финала", "p1": "Hanter", "p2": "Dune", "score": "3:2", "games": "0:4, 3:6, 1:0, 3:2, 4:3"},
    {"stage": "1/16 финала", "p1": "Kubik", "p2": "ruby", "score": "3:1", "games": "1:0, 0:2, 2:1, 2:0"},
    {"stage": "1/16 финала", "p1": "Juliy_Cezar", "p2": "Ryumaru", "score": "3:0", "games": "2:0, 5:2, 2:1"},
    # 1/8
    {"stage": "1/8 финала", "p1": "Memori", "p2": "Jamlight", "score": "3:1", "games": "Серия до 3 побед"},
    {"stage": "1/8 финала", "p1": "Ric25", "p2": "Hanter", "score": "3:0", "games": "2:0, 1:0, 2:1"},
    {"stage": "1/8 финала", "p1": "leonudomlya", "p2": "Kubik", "score": "3:2", "games": "Серия до 3 побед"},
    {"stage": "1/8 финала", "p1": "Aeris", "p2": "Juliy_Cezar", "score": "3:1", "games": "5:3, 1:4, 1:0, 2:0"},
    # 1/4
    {"stage": "1/4 финала", "p1": "Kunio", "p2": "Memori", "score": "4:2", "games": "Серия до 4 побед"},
    {"stage": "1/4 финала", "p1": "Rock", "p2": "Ric25", "score": "4:1", "games": "Серия до 4 побед"},
    {"stage": "1/4 финала", "p1": "ectoPower", "p2": "leonudomlya", "score": "4:0", "games": "Серия до 4 побед"},
    {"stage": "1/4 финала", "p1": "Romix", "p2": "Aeris", "score": "4:0", "games": "Серия до 4 побед"},
    # 1/2
    {"stage": "1/2 финала", "p1": "Rock", "p2": "Kunio", "score": "4:1", "games": "3:1, 11:10, 1:3, 2:0, 2:1"},
    {"stage": "1/2 финала", "p1": "ectoPower", "p2": "Romix", "score": "4:0", "games": "5:3, 4:3, 2:1, 3:2"},
    # Финал
    {"stage": "ФИНАЛ", "p1": "ectoPower", "p2": "Rock", "score": "5:0", "games": "5:1, 5:0, 3:0, 5:3, 4:1"}
]

special_tournaments.append({
    "id": "solo_goal3_autumn_2021",
    "title": "Сольный Турнир Goal 3 (Осень 2021)",
    "category": "Сольные турниры",
    "season_year": "2021 (Осень)",
    "game": "Goal 3 (NES)",
    "format": "1x1 Плей-офф (Сетка 16 игроков)",
    "champion": "ectoPower",
    "runner_up": "Rock",
    "bronze": "Kunio & Romix",
    "description": "Большой сольный турнир осени 2021 года. Сетка на 16 сильнейших игроков сообщества, многосетовые битвы от 3 до 5 побед с подробным протоколом каждого забитого гола. Безоговорочный триумф ectoPower, не отдавший в плей-офф ни одного сета в полуфинале и финале (9-0 по матчам!).",
    "matches": solo_2021_matches,
    "key_players": ["ectoPower", "Rock", "Kunio", "Romix", "Memori", "Ric25", "Kubik", "Dune", "Jamlight", "Aeris", "Juliy_Cezar"]
})

# ==========================================
# 4. 3-й Турнир по пенальти (Апрель-Май 2016)
# ==========================================
penalty3_matches = [
    {"stage": "Winners 1/8", "p1": "RVD", "p2": "Ric25", "score": "7:3"},
    {"stage": "Winners 1/8", "p1": "PacnyTHuK", "p2": "edexy", "score": "7:0"},
    {"stage": "Winners 1/8", "p1": "Tymoschuk", "p2": "Alpharushin", "score": "7:1"},
    {"stage": "Winners 1/8", "p1": "mafuta", "p2": "Dopi", "score": "7:0"},
    {"stage": "Winners 1/8", "p1": "Huba", "p2": "Dynamik", "score": "7:1"},
    {"stage": "Winners 1/8", "p1": "ectoPower", "p2": "Kunio", "score": "7:4"},
    {"stage": "Winners 1/8", "p1": "Memori", "p2": "Transistor", "score": "7:6"},
    {"stage": "Winners 1/8", "p1": "Davitel", "p2": "Kubik", "score": "7:1"},
    # Winners 1/4
    {"stage": "Winners 1/4", "p1": "PacnyTHuK", "p2": "RVD", "score": "7:1"},
    {"stage": "Winners 1/4", "p1": "mafuta", "p2": "Tymoschuk", "score": "7:2"},
    {"stage": "Winners 1/4", "p1": "ectoPower", "p2": "Huba", "score": "7:0"},
    {"stage": "Winners 1/4", "p1": "Davitel", "p2": "Memori", "score": "7:5"},
    # Winners 1/2
    {"stage": "Winners 1/2", "p1": "PacnyTHuK", "p2": "mafuta", "score": "7:6"},
    {"stage": "Winners 1/2", "p1": "ectoPower", "p2": "Davitel", "score": "7:6"},
    # Winners Final
    {"stage": "Winners Final", "p1": "PacnyTHuK", "p2": "ectoPower", "score": "7:5"},
    # Losers key matches
    {"stage": "Losers Round", "p1": "Kunio", "p2": "Tymoschuk", "score": "7:2"},
    {"stage": "Losers Round", "p1": "Kunio", "p2": "mafuta", "score": "7:4"},
    {"stage": "Losers Round", "p1": "Kunio", "p2": "Davitel", "score": "7:2"},
    {"stage": "Losers Final", "p1": "Kunio", "p2": "ectoPower", "score": "7:5"},
    # Superfinal
    {"stage": "СУПЕРФИНАЛ", "p1": "PacnyTHuK", "p2": "Kunio", "score": "7:4"}
]

special_tournaments.append({
    "id": "penalty_tournament_3",
    "title": "3-й Сольный Турнир по пенальти",
    "category": "Сольные турниры",
    "season_year": "2016 (Весна)",
    "game": "Goal 3 (Серия пенальти)",
    "format": "Double Elimination (до 7 побед)",
    "champion": "PacnyTHuK",
    "runner_up": "Kunio",
    "bronze": "ectoPower",
    "fourth": "mafuta",
    "description": "Легендарный сольный турнир мастеров серии пенальти по системе Double Elimination. Участвовала вся элита сообщества (16 игроков). PacnyTHuK прошел турнир без единого поражения по верхней сетке, одолев edexy, RVD, mafuta, ectoPower и Kunio в суперфинале.",
    "matches": penalty3_matches,
    "key_players": ["PacnyTHuK", "Kunio", "ectoPower", "mafuta", "Tymoschuk", "RVD", "Memori", "Kubik", "Ric25", "Alpharushin", "Davitel", "edexy"]
})

# ==========================================
# 5. 2-й Сольный Турнир по пенальти (Июль 2015)
# ==========================================
penalty2_matches = [
    {"stage": "1/8 финала", "p1": "PacnyTHuK", "p2": "Davitel", "score": "7:3"},
    {"stage": "1/8 финала", "p1": "ectoPower", "p2": "Kotix", "score": "7:3"},
    {"stage": "1/8 финала", "p1": "edexy", "p2": "PacnyTHuK", "score": "7:6"},
    {"stage": "1/8 финала", "p1": "Jgunishka", "p2": "Davitel", "score": "7:3"},
    {"stage": "1/4 финала", "p1": "RVD", "p2": "PacnyTHuK", "score": "7:3"},
    {"stage": "1/4 финала", "p1": "Alpharushin", "p2": "BOP95", "score": "7:3"},
    {"stage": "1/4 финала", "p1": "ectoPower", "p2": "Centurion", "score": "7:1"},
    {"stage": "1/4 финала", "p1": "edexy", "p2": "Jgunishka", "score": "7:6"},
    {"stage": "1/2 финала", "p1": "RVD", "p2": "Alpharushin", "score": "7:4"},
    {"stage": "1/2 финала", "p1": "edexy", "p2": "ectoPower", "score": "7:0"},
    {"stage": "Матч за 3-е место", "p1": "ectoPower", "p2": "Alpharushin", "score": "7:5"},
    {"stage": "ФИНАЛ", "p1": "RVD", "p2": "edexy", "score": "7:4"}
]

special_tournaments.append({
    "id": "penalty_tournament_2",
    "title": "2-й Сольный Турнир по пенальти",
    "category": "Сольные турниры",
    "season_year": "2015 (Лето)",
    "game": "Goal 3 (Серия пенальти)",
    "format": "Олимпийская сетка (до 7 побед)",
    "champion": "RVD",
    "runner_up": "edexy",
    "bronze": "ectoPower",
    "fourth": "Alpharushin",
    "description": "Второй чемпионат сообщества по пенальти. Организаторы RVD и Kotix. RVD подтвердил статус чемпиона пенальти, победив Alpharushin и edexy в финале.",
    "matches": penalty2_matches,
    "key_players": ["RVD", "edexy", "ectoPower", "Alpharushin", "PacnyTHuK", "BOP95", "Centurion", "Jgunishka", "Davitel"]
})

# ==========================================
# 6. X Юбилейный Блиц-турнир по Goal 3
# ==========================================
blitz10_matches = [
    {"stage": "Квалификация", "p1": "Chocopie", "p2": "Gilmour", "score": "2:1"},
    {"stage": "Квалификация", "p1": "Aoshi", "p2": "Kot-from-ussr", "score": "2:0"},
    {"stage": "Квалификация", "p1": "Tymoschuk", "p2": "Jamlight", "score": "2:0"},
    {"stage": "1 раунд", "p1": "Chocopie", "p2": "wanchous", "score": "2:0"},
    {"stage": "1 раунд", "p1": "Romix", "p2": "Aoshi", "score": "2:0"},
    {"stage": "1 раунд", "p1": "FC Pushistik", "p2": "Centurion", "score": "2:1"},
    {"stage": "1 раунд", "p1": "Tymoschuk", "p2": "Flash", "score": "2:0"},
    {"stage": "2 раунд", "p1": "BOP95", "p2": "Chocopie", "score": "2:0"},
    {"stage": "2 раунд", "p1": "LiptOn", "p2": "Romix", "score": "2:1"},
    {"stage": "2 раунд", "p1": "ectoPower", "p2": "Dopi", "score": "2:1"},
    {"stage": "2 раунд", "p1": "Tymoschuk", "p2": "Kunio", "score": "2:1"},
    {"stage": "1/4 финала", "p1": "BOP95", "p2": "Ric25", "score": "2:0"},
    {"stage": "1/4 финала", "p1": "mafuta", "p2": "LiptOn", "score": "2:0"},
    {"stage": "1/4 финала", "p1": "ectoPower", "p2": "FC Pushistik", "score": "2:0"},
    {"stage": "1/4 финала", "p1": "Tymoschuk", "p2": "Kipriot", "score": "2:0"},
    {"stage": "1/2 финала", "p1": "mafuta", "p2": "BOP95", "score": "3:1"},
    {"stage": "1/2 финала", "p1": "Tymoschuk", "p2": "ectoPower", "score": "3:1"},
    {"stage": "Матч за 3-е место", "p1": "BOP95", "p2": "ectoPower", "score": "3:2"},
    {"stage": "ФИНАЛ", "p1": "mafuta", "p2": "Tymoschuk", "score": "5:3"}
]

special_tournaments.append({
    "id": "blitz_10",
    "title": "X Юбилейный Блиц-турнир по Goal 3",
    "category": "Сольные турниры",
    "season_year": "2017 (Весна)",
    "game": "Goal 3 (NES)",
    "format": "Сольный блиц (1x1, сетка на 19 участников)",
    "champion": "mafuta",
    "runner_up": "Tymoschuk",
    "bronze": "BOP95",
    "fourth": "ectoPower",
    "description": "Юбилейный 10-й онлайн блиц-турнир сообщества, собравший 19 игроков в один вечер. mafuta выиграл золотой кубок, одолев в ярком суперфинале Tymoschuk со счетом 5:3.",
    "matches": blitz10_matches,
    "key_players": ["mafuta", "Tymoschuk", "BOP95", "ectoPower", "Kunio", "Romix", "Ric25", "Aoshi", "Kot-from-ussr", "Jamlight", "LiptOn", "FC Pushistik"]
})

# ==========================================
# 7. IX Блиц-турнир по Goal 3
# ==========================================
blitz9_matches = [
    {"stage": "1/8 финала", "p1": "BZK", "p2": "Jamlight", "score": "2:0"},
    {"stage": "1/8 финала", "p1": "izzzotope", "p2": "Dune", "score": "2:0"},
    {"stage": "1/8 финала", "p1": "RVD", "p2": "Kipriot", "score": "2:0"},
    {"stage": "1/8 финала", "p1": "tubustd", "p2": "FC Pushistik", "score": "2:0"},
    {"stage": "1/8 финала", "p1": "BOP95", "p2": "wanchous", "score": "2:0"},
    {"stage": "1/8 финала", "p1": "Буц", "p2": "Kirpich", "score": "2:0"},
    {"stage": "1/8 финала", "p1": "Transistor", "p2": "Ric25", "score": "2:0"},
    {"stage": "1/8 финала", "p1": "Centurion", "p2": "Aoshi", "score": "2:0"},
    {"stage": "1/4 финала", "p1": "BZK", "p2": "izzzotope", "score": "2:0"},
    {"stage": "1/4 финала", "p1": "RVD", "p2": "tubustd", "score": "2:0"},
    {"stage": "1/4 финала", "p1": "Буц", "p2": "BOP95", "score": "2:0"},
    {"stage": "1/4 финала", "p1": "Transistor", "p2": "Centurion", "score": "2:1"},
    {"stage": "1/2 финала", "p1": "RVD", "p2": "BZK", "score": "3:2"},
    {"stage": "1/2 финала", "p1": "Transistor", "p2": "Буц", "score": "3:0"},
    {"stage": "Матч за 3-е место", "p1": "BZK", "p2": "Буц", "score": "0:3"},
    {"stage": "ФИНАЛ", "p1": "Буц", "p2": "Transistor", "score": "5:0"}
]

special_tournaments.append({
    "id": "blitz_9",
    "title": "IX Блиц-турнир по Goal 3",
    "category": "Сольные турниры",
    "season_year": "2017 (Зима)",
    "game": "Goal 3 (NES)",
    "format": "Сольный блиц (1x1, сетка на 16 игроков)",
    "champion": "Буц",
    "runner_up": "Transistor",
    "bronze": "BZK",
    "fourth": "RVD",
    "description": "Классический 9-й сольный блиц кубок. Сенсационная победа Буца, разгромившего соперников в финальных стадиях турнира.",
    "matches": blitz9_matches,
    "key_players": ["Буц", "Transistor", "BZK", "RVD", "BOP95", "Centurion", "Ric25", "Aoshi", "Dune", "Jamlight", "FC Pushistik", "izzzotope"]
})

# ==========================================
# 8. XII Блиц-турнир по Goal 3 (1x1)
# ==========================================
special_tournaments.append({
    "id": "blitz_12",
    "title": "XII Блиц-турнир по Goal 3 (1x1)",
    "category": "Сольные турниры",
    "season_year": "2019 (Осень)",
    "game": "Goal 3 (NES)",
    "format": "Сольный блиц (1x1)",
    "champion": "PacnyTHuK",
    "runner_up": "ectoPower",
    "bronze": "Tymoschuk",
    "fourth": "BZK",
    "description": "12-й сольный блиц-турнир 19 октября 2019 года. Ожесточенная битва суперзвезд высшей лиги: в топ-4 вошли четверо величайших чемпионов сообщества.",
    "matches": [
        {"stage": "1/4 финала", "p1": "PacnyTHuK", "p2": "Romix", "score": "победа PacnyTHuK"},
        {"stage": "1/4 финала", "p1": "ectoPower", "p2": "Kunio", "score": "победа ectoPower"},
        {"stage": "1/4 финала", "p1": "Tymoschuk", "p2": "RVD", "score": "победа Tymoschuk"},
        {"stage": "1/4 финала", "p1": "BZK", "p2": "Alpharushin", "score": "победа BZK"},
        {"stage": "1/2 финала", "p1": "PacnyTHuK", "p2": "Tymoschuk", "score": "победа PacnyTHuK"},
        {"stage": "1/2 финала", "p1": "ectoPower", "p2": "BZK", "score": "победа ectoPower"},
        {"stage": "Матч за 3-е место", "p1": "Tymoschuk", "p2": "BZK", "score": "победа Tymoschuk"},
        {"stage": "ФИНАЛ", "p1": "PacnyTHuK", "p2": "ectoPower", "score": "победа PacnyTHuK"}
    ],
    "key_players": ["PacnyTHuK", "ectoPower", "Tymoschuk", "BZK", "Romix", "Kunio", "RVD", "Alpharushin", "mafuta", "Memori", "Aeris"]
})

# ==========================================
# 9. Сольный рейтинг по Goal 4
# ==========================================
goal4_rating_players = [
    {"player": "Romix", "rank": 1, "record": "4-7", "status": "Участник"},
    {"player": "ectoPower", "rank": 2, "record": "9-6", "status": "Участник"},
    {"player": "mafuta", "rank": 3, "record": "8-8", "status": "Участник"},
    {"player": "Memori", "rank": 4, "record": "8-9", "status": "Участник"},
    {"player": "Rock", "rank": "Выпускник", "record": "1 неделя", "status": "12 место"},
    {"player": "Kot-from-ussr", "rank": "Выпускник", "record": "2 неделя", "status": "22 место"},
    {"player": "Ric25", "rank": "Выпускник", "record": "4 неделя", "status": "9 место"},
    {"player": "Xeamark", "rank": "Выпускник", "record": "4 неделя (2-2)", "status": "4 место"}
]

special_tournaments.append({
    "id": "goal4_solo_ladder",
    "title": "Сольный рейтинг (Ladder) по Goal 4",
    "category": "Сольные турниры",
    "season_year": "2020-2022",
    "game": "Goal 4 (Kunio Kun no Nekketsu Soccer League)",
    "format": "Лестница рейтинга (Solo Ladder)",
    "champion": "Romix & ectoPower",
    "runner_up": "mafuta",
    "bronze": "Memori",
    "description": "Постоянная рейтинговая лестница по Goal 4 между ведущими дуэлянтами сообщества. Учитывает персональные серии и рекорды побед.",
    "ladder": goal4_rating_players,
    "key_players": ["Romix", "ectoPower", "mafuta", "Memori", "Rock", "Kot-from-ussr", "Ric25"]
})

with open("special_tournaments_data.json", "w", encoding="utf-8") as f:
    json.dump(special_tournaments, f, ensure_ascii=False, indent=2)

print(f"Successfully generated special_tournaments_data.json with {len(special_tournaments)} tournaments!")
