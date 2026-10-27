import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from collections import defaultdict
import build_final_analytics

# Load base data
with open("nekketsu_master_table.json", "r", encoding="utf-8") as f:
    master_db = json.load(f)

# Load avatars
with open("player_avatars.json", "r", encoding="utf-8") as f:
    avatars = json.load(f)

all_matches = build_final_analytics.all_matches

# Enhance players with match breakdown: reg_w, ot_w, pk_w, reg_l, ot_l, pk_l, matches list
player_matches = defaultdict(list)
player_stats_addon = defaultdict(lambda: {
    "reg_w": 0, "ot_w": 0, "pk_w": 0,
    "reg_l": 0, "ot_l": 0, "pk_l": 0,
    "draws": 0
})

for m in all_matches:
    p1 = m["p1"]
    p2 = m["p2"]
    s1 = m["s1"]
    s2 = m["s2"]
    ot = m.get("ot", False)
    pk = m.get("pk", False)
    season = m.get("season", "Unknown")
    tourn = m.get("tournament", "")
    stage = m.get("stage", "Матч")

    # For p1
    p1_res = "W" if s1 > s2 else ("L" if s1 < s2 else "D")
    p2_res = "W" if s2 > s1 else ("L" if s2 < s1 else "D")

    player_matches[p1].append({
        "season": season, "tournament": tourn, "stage": stage,
        "opponent": p2, "score_for": s1, "score_against": s2,
        "result": p1_res, "ot": ot, "pk": pk
    })
    player_matches[p2].append({
        "season": season, "tournament": tourn, "stage": stage,
        "opponent": p1, "score_for": s2, "score_against": s1,
        "result": p2_res, "ot": ot, "pk": pk
    })

    if s1 > s2:
        if pk: player_stats_addon[p1]["pk_w"] += 1; player_stats_addon[p2]["pk_l"] += 1
        elif ot: player_stats_addon[p1]["ot_w"] += 1; player_stats_addon[p2]["ot_l"] += 1
        else: player_stats_addon[p1]["reg_w"] += 1; player_stats_addon[p2]["reg_l"] += 1
    elif s2 > s1:
        if pk: player_stats_addon[p2]["pk_w"] += 1; player_stats_addon[p1]["pk_l"] += 1
        elif ot: player_stats_addon[p2]["ot_w"] += 1; player_stats_addon[p1]["ot_l"] += 1
        else: player_stats_addon[p2]["reg_w"] += 1; player_stats_addon[p1]["reg_l"] += 1
    else:
        player_stats_addon[p1]["draws"] += 1
        player_stats_addon[p2]["draws"] += 1

# Seasons database with full recaps
seasons_data = [
    {
        "id": "1",
        "name": "Season 1",
        "year": "2015",
        "champion": "mafuta",
        "runner_up": "Ric25",
        "third_place": "WiSe",
        "cup_winner": "mafuta",
        "participants": 10,
        "format": "Круговой гладкий чемпионат (Round Robin) + Сетка Кубка",
        "emulator": "Mednafen NES 0.9.x / FCEUX (чистый ром Goal 3)",
        "summary": "Исторический первый турнир сообщества NST, организованный Memori и Ric25. Десять первопроходцев провели затяжную круговую лигу в Google Таблицах. Абсолютное доминирование продемонстрировал mafuta, забравший и чемпионский титул, и Кубок.",
        "highlights": [
            "Memori занял 1-е место в регулярной сетке (92 очка, +94 разница), но mafuta завоевал итоговое чемпионство.",
            "Формирование первых легендарных противостояний: Ric25 vs Memori, WiSe vs Wenderfit.",
            "Открытый стиль игры — команды забивали в среднем по 7–8 мячей за матч."
        ]
    },
    {
        "id": "2",
        "name": "Season 2",
        "year": "2016",
        "champion": "mafuta",
        "runner_up": "Kunio",
        "third_place": "ectoPower",
        "cup_winner": "mafuta",
        "participants": 20,
        "format": "Разделение на Старшую и Младшую лиги + единый Playoff до 3–4 побед",
        "emulator": "Mednafen Netplay",
        "summary": "Второй сольный чемпионат ознаменовался притоком новых игроков и внедрением двухуровневой системы. В плей-офф сошлись представители обеих лиг. Mafuta оформил второй чемпионский титул подряд, сокрушив в гранд-финале молодого Kunio со счётом 5:2.",
        "highlights": [
            "Гранд-финал: mafuta 5 : 2 Kunio — первый крупный финал для будущей легенды Kunio.",
            "Дебют ectoPower на соревновательной арене — бронзовый призер плей-офф.",
            "Введение жесткого регламента по пингу и сетевым задержкам."
        ]
    },
    {
        "id": "3",
        "name": "Season 3",
        "year": "2016",
        "champion": "mafuta",
        "runner_up": "ectoPower",
        "third_place": "Ric25",
        "cup_winner": "mafuta",
        "participants": 31,
        "format": "Трёхдивизионная система на платформе Oball + плей-офф Кубка",
        "emulator": "Mednafen Netplay (хаки с фиксом рассинхрона)",
        "summary": "Пик эпохи Мафуты. На турнир заявился 31 участник. В финале встретились два титана — mafuta и стремительно прогрессирующий ectoPower. В упорнейшей серии mafuta подтвердил статус «короля NES-футбола», завоевав третий титул подряд («хет-трик чемпионств»).",
        "highlights": [
            "«Хет-трик чемпионств» mafuta: три победы в трех сезонах подряд (2015–2016).",
            "Зарождение главного исторического соперничества: mafuta vs ectoPower.",
            "Ric25 выигрывает тяжелейший матч за 3-е место."
        ]
    },
    {
        "id": "4",
        "name": "Season 4",
        "year": "2017",
        "champion": "Transistor",
        "runner_up": "mafuta",
        "third_place": "ectoPower",
        "cup_winner": "mafuta",
        "participants": 34,
        "format": "3 дивизиона + открытая сетка на выбывание (BO5/BO7)",
        "emulator": "Mednafen Netplay (турнирные ромы)",
        "summary": "Сезон великой сенсации. Новичок турнира Transistor продемонстрировал космический микроконтроль и агрессивную контратакующую модель. В плей-офф он с сухим счетом 4:0 разгромил Kunio, а в финале сенсационно сверг бессменного гегемона mafuta. Тем не менее mafuta сумел взять реванш в Кубке Лиг.",
        "highlights": [
            "Конец непобедимой серии mafuta: Транзистор берёт титул чемпиона Высшей лиги.",
            "Дебют Aeris (knucklesss) в элитной соревновательной сетке.",
            "Рекордные 34 участника в турнирной таблице."
        ]
    },
    {
        "id": "5",
        "name": "Season 5",
        "year": "2017",
        "champion": "ectoPower",
        "runner_up": "PacnyTHuK",
        "third_place": "Romix",
        "cup_winner": "RVD (МГБ)",
        "participants": 28,
        "format": "Регулярный сезон + Золотой плей-офф",
        "emulator": "Mednafen Netplay",
        "summary": "Начало эры ectoPower. После ухода mafuta на покой ectoPower впервые в карьере берет золото Высшей лиги. Однако в Кубке грянул главный апсет года: кубковый специалист RVD (МГБ) выбил всех фаворитов и забрал престижный трофей.",
        "highlights": [
            "Первый чемпионский титул ectoPower в Высшей лиге.",
            "Триумф RVD (МГБ) в Кубке Лиг — первый «кубковый киллер» сообщества.",
            "Восхождение PacnyTHuK как стабильного финалиста мейджоров."
        ]
    },
    {
        "id": "6",
        "name": "Season 6",
        "year": "2018",
        "champion": "ectoPower",
        "runner_up": "Transistor",
        "third_place": "PacnyTHuK",
        "cup_winner": "ectoPower",
        "participants": 26,
        "format": "Регулярка + Кубок Лиг",
        "emulator": "Mednafen Netplay",
        "summary": "Год «золотого дубля» ectoPower. В финале Кубка Лиг состоялся один из самых драматичных матчей в истории: ectoPower и Transistor дважды сыграли вничью (3:3 и 5:5), и победитель определялся в эпической серии буллитов (5:4 по пенальти).",
        "highlights": [
            "Легендарный буллитный триллер: ectoPower побеждает Transistor 5:4 по пенальти.",
            "Золотой дубль ectoPower (Чемпионат + Кубок в один сезон).",
            "Последний активный сольный сезон Транзистора перед длительным инактивом."
        ]
    },
    {
        "id": "7",
        "name": "Season 7",
        "year": "2022",
        "champion": "ectoPower",
        "runner_up": "mafuta",
        "third_place": "Romix",
        "cup_winner": "RVD (МГБ)",
        "participants": 24,
        "format": "Возрождение после пандемийной паузы, модифицированный ром T349",
        "emulator": "Mednafen 0.9.48.C0",
        "summary": "Грандиозный камбэк соревновательной сцены NST. Mafuta неожиданно вернулся, чтобы бросить вызов действующему королю ectoPower. В финале ectoPower защитил корону, а RVD (МГБ) вновь подтвердил звание кубкового гения, завоевав свой второй Кубок Лиг.",
        "highlights": [
            "Ностальгический финал: ectoPower побеждает mafuta.",
            "Второй Кубок Лиг для RVD (МГБ).",
            "Romix берет бронзовые медали турнира."
        ]
    },
    {
        "id": "8",
        "name": "Season 8",
        "year": "2024",
        "champion": "Kunio / ectoPower",
        "runner_up": "ectoPower",
        "third_place": "Romix",
        "cup_winner": "PacnyTHuK",
        "participants": 32,
        "format": "Трёхлиговая структура (Высшая, Средняя, Дворовая) + Sportcup API + Большой Кубок Лиг",
        "emulator": "Mednafen Netplay (Ром Goal 3 NST T355)",
        "summary": "Сезон тектонических сдвигов. Введение профессиональной статистики Sportcup. Появление суперзвезды Дворовой лиги Sokol (81.5% WR). В гранд-финале Кубка PacnyTHuK остановил ectoPower в зубодробительной серии из 8 игр (5:3), став национальным героем сцены.",
        "highlights": [
            "PacnyTHuK 5 : 3 ectoPower — свержение гегемона в гранд-финале Кубка.",
            "Взлёт Sokol: 22 победы в 27 матчах и штурм вершин ладдера.",
            "Aeris показывает топ-класс в Средней лиге (победы над Dune 3:0 и Jamlight 4:2, 3:1)."
        ]
    },
    {
        "id": "9",
        "name": "Season 9",
        "year": "2025",
        "champion": "Kunio",
        "runner_up": "Rock",
        "third_place": "Romix",
        "cup_winner": "ectoPower",
        "participants": 30,
        "format": "3 Лиги (Высшая, Средняя, Дворовая) + Кубок Лиг на вылет",
        "emulator": "Mednafen Netplay (Goal 3 NST T355, погодные эффекты и хардкорная физика)",
        "summary": "Современный апогей меты. Kunio выигрывает регулярный чемпионат Высшей лиги с абсолютно непробиваемой обороной (1.76 пропущенных за матч). В финале Кубка ectoPower реабилитируется и учиняет показательный разгром финалисту Rock со счётом 5:0. В Высшей лиге фиксируется абсолютный рекорд результативности: Memori 9 : 8 Ric25 (17 мячей!).",
        "highlights": [
            "Kunio — чемпион Высшей лиги благодаря «железному занавесу» в обороне.",
            "Финал Кубка: ectoPower 5 : 0 Rock — безоговорочный триумф GOAT сцены.",
            "Матч века: Ric25 8 : 9 Memori — рекордные 17 голов в одной встрече.",
            "Hanter выигрывает Дворовую лигу с феноменальным винрейтом 85.7%."
        ]
    }
]

# Enrich seasons_data with deep VK community chronicles and archives
try:
    import tournament_chronicles_data
    for s in seasons_data:
        s_id = str(s.get("id"))
        if s_id in tournament_chronicles_data.SEASONS_CHRONICLES:
            chron = tournament_chronicles_data.SEASONS_CHRONICLES[s_id]
            for k, v in chron.items():
                s[k] = v
except Exception as e:
    print("Warning enriching seasons_data:", e)

print("Data structures ready!")
