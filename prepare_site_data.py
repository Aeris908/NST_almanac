"""Player match histories and the season-by-season recaps that the soccer portal renders."""

import sys
from collections import defaultdict

from db.pool import pool_from_db

sys.stdout.reconfigure(encoding="utf-8")

UNKNOWN_SEASON = "Unknown"
DEFAULT_MATCH_STAGE = "Матч"

# Win/loss buckets per player, counted separately for overtime and penalty shoot-outs.
EMPTY_TALLY = {"reg_w": 0, "ot_w": 0, "pk_w": 0, "reg_l": 0, "ot_l": 0, "pk_l": 0, "draws": 0}


def _outcome(score, opponent_score):
    """'W'/'L'/'D' seen from one side of a finished game."""
    if score > opponent_score:
        return "W"
    if score < opponent_score:
        return "L"
    return "D"


def _match_record(season, tournament, stage, opponent, score_for, score_against, ot, pk):
    """One row of a player's personal game log."""
    return {
        "season": season,
        "tournament": tournament,
        "stage": stage,
        "opponent": opponent,
        "score_for": score_for,
        "score_against": score_against,
        "result": _outcome(score_for, score_against),
        "ot": ot,
        "pk": pk,
    }


def _count_decision(addon, winner, loser, ot, pk):
    """Credit both sides with the right flavour of win/loss: penalty, overtime or regular."""
    if pk:
        win_key, loss_key = "pk_w", "pk_l"
    elif ot:
        win_key, loss_key = "ot_w", "ot_l"
    else:
        win_key, loss_key = "reg_w", "reg_l"
    addon[winner][win_key] += 1
    addon[loser][loss_key] += 1


def build_player_stats(matches):
    """Personal game logs and overtime/penalty-aware win-loss tallies for every player."""
    player_matches = defaultdict(list)
    player_stats_addon = defaultdict(lambda: dict(EMPTY_TALLY))

    for match in matches:
        p1 = match["p1"]
        p2 = match["p2"]
        s1 = match["s1"]
        s2 = match["s2"]
        ot = match.get("ot", False)
        pk = match.get("pk", False)
        season = match.get("season", UNKNOWN_SEASON)
        tournament = match.get("tournament", "")
        stage = match.get("stage", DEFAULT_MATCH_STAGE)

        player_matches[p1].append(_match_record(season, tournament, stage, p2, s1, s2, ot, pk))
        player_matches[p2].append(_match_record(season, tournament, stage, p1, s2, s1, ot, pk))

        if s1 > s2:
            _count_decision(player_stats_addon, p1, p2, ot, pk)
        elif s2 > s1:
            _count_decision(player_stats_addon, p2, p1, ot, pk)
        else:
            player_stats_addon[p1]["draws"] += 1
            player_stats_addon[p2]["draws"] += 1

    return player_matches, player_stats_addon


SEASON_RECAPS = [
    {
        "id": "1",
        "name": "Season 1",
        "year": "2015",
        # Призовые места первого сезона в источниках не названы: регламент отдаёт их плей-офф,
        # а в теме 32593813 есть только четвертьфиналы (комментарий 3339) и полуфиналы (3359).
        # Ссылка на страницу первого турнира на стене группы названа утерянной. Выдумывать
        # чемпиона здесь нечем: mafuta, названный ранее, в состав сезона не входит, а WiSe не
        # вышел из дивизиона в сетку.
        "champion": None,
        "runner_up": None,
        "third_place": None,
        "cup_winner": None,
        "participants": 20,
        "format": "Два дивизиона по 10 игроков, 2 круга, 18 туров + сетка плей-офф (по 4 от дивизиона)",
        "emulator": "Mednafen NES 0.9.x / FCEUX (чистый ром Goal 3)",
        "summary": "Исторический первый турнир сообщества NST: КОМЕТЫ и МЕТЕОРЫ играли круговой этап по четыре встречи на пару, в туре — две игры со сменой сторон. По итогам дивизионы совмещались в одну лигу только для определения призера круговой стадии, а места разыгрывал плей-офф. Результаты кругового этапа взяты из google-таблиц турнира, сетка — из отчётов темы; финал и матч за третье место источниками не подтверждены.",
        "highlights": [
            "332 игры регулярного чемпионата и 1855 мячей — в среднем 5,6 гола за матч.",
            "Круговые стадии выиграли Memori среди КОМЕТОВ (92 очка, +94) и Tymoschuk среди МЕТЕОРОВ (85 очков, +101).",
            "Плей-офф известен до полуфиналов: Memori 4:3 BOР95 и Tymoschuk 4:0 Dr1N (комментарии 3339 и 3359); чем закончился финал — источники молчат.",
        ],
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
            "Введение жесткого регламента по пингу и сетевым задержкам.",
        ],
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
            "Ric25 выигрывает тяжелейший матч за 3-е место.",
        ],
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
            "Рекордные 34 участника в турнирной таблице.",
        ],
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
            "Восхождение PacnyTHuK как стабильного финалиста мейджоров.",
        ],
    },
    {
        "id": "6",
        "name": "Season 6",
        "year": "2018",
        "champion": "ectoPower",
        "runner_up": "Transistor",
        # Бронзы источник не называет: PacnyTHuK шёл в заявку как «Распутник», но снялся до
        # старта — его место в Высшей лиге занял Transistor по уайлд-кард (комментарий 17542
        # темы 39660451), и ни одной игры в сезоне он не сыграл. Матча за третье место в
        # кубковой сетке нет. Выдуманного призёра убираем, как в Сезоне 1, а не подменяем.
        "third_place": None,
        "cup_winner": "ectoPower",
        "participants": 26,
        "format": "Регулярка + Кубок Лиг",
        "emulator": "Mednafen Netplay",
        "summary": "Год «золотого дубля» ectoPower. В финале Кубка Лиг состоялся один из самых драматичных матчей в истории: ectoPower и Transistor дважды сыграли вничью (3:3 и 5:5), и победитель определялся в эпической серии буллитов (5:4 по пенальти).",
        "highlights": [
            "Легендарный буллитный триллер: ectoPower побеждает Transistor 5:4 по пенальти.",
            "Золотой дубль ectoPower (Чемпионат + Кубок в один сезон).",
            "Последний активный сольный сезон Транзистора перед длительным инактивом.",
        ],
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
            "Romix берет бронзовые медали турнира.",
        ],
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
            "Aeris показывает топ-класс в Средней лиге (победы над Dune 3:0 и Jamlight 4:2, 3:1).",
        ],
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
            "Hanter выигрывает Дворовую лигу с феноменальным винрейтом 85.7%.",
        ],
    },
]


def enrich_recaps_with_chronicles(recaps):
    """Merge the deep VK community chronicles into the season recaps, in place."""
    try:
        import tournament_chronicles_data

        for recap in recaps:
            chronicle = tournament_chronicles_data.SEASONS_CHRONICLES.get(str(recap.get("id")))
            if chronicle:
                recap.update(chronicle)
    except Exception as error:
        print("Warning enriching seasons_data:", error)
    return recaps


player_matches, player_stats_addon = build_player_stats(pool_from_db())
seasons_data = enrich_recaps_with_chronicles(SEASON_RECAPS)

print("Data structures ready!", file=sys.stderr)
