import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import math
from collections import defaultdict
import build_final_analytics

all_matches = build_final_analytics.all_matches

SEASON_YEAR = {
    "Season 4": 2017.0,
    "Season 5": 2017.5,
    "Season 6": 2018.0,
    "Season 7": 2022.0,
    "Season 8": 2024.0,
    "Season 9": 2025.5,
}
CURRENT_YEAR = 2025.5

LEAGUE_TIERS = {
    "ectoPower": "Высшая", "mafuta": "Высшая", "Kunio": "Высшая",
    "PacnyTHuK": "Высшая", "Romix": "Высшая", "Transistor": "Высшая",
    "RVD (МГБ)": "Высшая", "Rock": "Высшая", "Ric25": "Высшая",
    "Cyneprepou4uk": "Высшая", "leonudomlya": "Высшая", "Memori": "Высшая",
    "Kipriot": "Высшая", "izzzotope": "Высшая", "FC Pushistik": "Высшая",
    
    "Буц": "Средняя", "Aeris": "Средняя", "Yuliy_Cezar": "Средняя",
    "Kubik": "Средняя", "Jamlight": "Средняя",
    "Dune": "Средняя", "E_not": "Средняя", "RASH": "Средняя", "Кирпич57": "Средняя",
    "Sokol": "Дворовая", "Hanter": "Дворовая", "Ryumaru": "Дворовая",
    "frzz": "Дворовая", "yoxter": "Дворовая", "ruby": "Дворовая",
    "Taeda": "Дворовая", "Сахарок": "Дворовая", 
    "Веселый Роджер": "Дворовая", "Spartacus": "Дворовая", "mikr84": "Дворовая",
    "TBP_Machiavelli": "Дворовая", "BigPlay": "Дворовая", "daz": "Дворовая",
}

BASE_RATINGS = {"Высшая": 1600.0, "Средняя": 1350.0, "Дворовая": 1050.0}

SEASON_ORDER = ["Season 4", "Season 5", "Season 6", "Season 7", "Season 8", "Season 9"]
matches_by_season = defaultdict(list)
for m in all_matches:
    matches_by_season[m["season"]].append(m)

elo = {}
peak_elo = {}
lowest_elo = {}
last_active_year = {}

matches_played = defaultdict(int)
wins = defaultdict(int)
losses = defaultdict(int)
draws = defaultdict(int)
goals_for = defaultdict(int)
goals_against = defaultdict(int)
clean_sheets = defaultdict(int)
failed_to_score = defaultdict(int)

# OT / PK stats
ot_matches = defaultdict(int)
ot_wins = defaultdict(int)
ot_losses = defaultdict(int)
pk_wins = defaultdict(int)
pk_losses = defaultdict(int)

# Playoff stats
playoff_matches = defaultdict(int)
playoff_wins = defaultdict(int)
playoff_losses = defaultdict(int)

# Head-to-Head
h2h = defaultdict(lambda: defaultdict(lambda: {"w": 0, "l": 0, "gf": 0, "ga": 0, "ot_w": 0, "ot_l": 0}))

# Blowouts & Thrillers trackers
all_blowouts = []
all_thrillers = []

for p, tier in LEAGUE_TIERS.items():
    elo[p] = BASE_RATINGS[tier]
    peak_elo[p] = BASE_RATINGS[tier]
    lowest_elo[p] = BASE_RATINGS[tier]
    last_active_year[p] = 2017.0

for season in SEASON_ORDER:
    season_year = SEASON_YEAR[season]
    season_matches = matches_by_season[season]
    
    for m in season_matches:
        p1 = m["p1"]
        p2 = m["p2"]
        s1 = m["s1"]
        s2 = m["s2"]
        ot = m.get("ot", False)
        pk = m.get("pk", False)
        is_playoff = m.get("is_playoff", False)
        tourn = m["tournament"]
        stage = m.get("stage", "Регулярный сезон")

        is_tech = m.get("is_technical", False) or m.get("is_forfeit", False) or (season == "Season 8" and (p1 == "RVD (МГБ)" or p2 == "RVD (МГБ)"))
        if is_tech:
            # Technical forfeit due to tournament withdrawal:
            # Winner gets official match on paper, but Elo and phantom losses are NOT applied to withdrawn player
            winner = p2 if p1 == "RVD (МГБ)" else p1
            wins[winner] += 1
            matches_played[winner] += 1
            goals_for[winner] += 3
            last_active_year[winner] = season_year
            continue

        last_active_year[p1] = season_year
        last_active_year[p2] = season_year

        matches_played[p1] += 1
        matches_played[p2] += 1
        goals_for[p1] += s1
        goals_against[p1] += s2
        goals_for[p2] += s2
        goals_against[p2] += s1

        if s2 == 0: clean_sheets[p1] += 1
        if s1 == 0: clean_sheets[p2] += 1
        if s1 == 0: failed_to_score[p1] += 1
        if s2 == 0: failed_to_score[p2] += 1

        # Track thrillers
        tot_goals = s1 + s2
        all_thrillers.append({
            "p1": p1, "p2": p2, "s1": s1, "s2": s2,
            "total_goals": tot_goals, "tournament": tourn, "stage": stage, "season": season
        })

        # Track blowouts
        diff = abs(s1 - s2)
        winner = p1 if s1 > s2 else (p2 if s2 > s1 else None)
        loser = p2 if s1 > s2 else (p1 if s2 > s1 else None)
        if winner:
            all_blowouts.append({
                "winner": winner, "loser": loser,
                "score_winner": max(s1, s2), "score_loser": min(s1, s2),
                "diff": diff, "tournament": tourn, "stage": stage, "season": season
            })

        # H2H stats
        h2h[p1][p2]["gf"] += s1
        h2h[p1][p2]["ga"] += s2
        h2h[p2][p1]["gf"] += s2
        h2h[p2][p1]["ga"] += s1

        # OT / PK tracking
        if ot or pk:
            ot_matches[p1] += 1
            ot_matches[p2] += 1

        if is_playoff:
            playoff_matches[p1] += 1
            playoff_matches[p2] += 1

        if s1 > s2:
            wins[p1] += 1
            losses[p2] += 1
            h2h[p1][p2]["w"] += 1
            h2h[p2][p1]["l"] += 1
            if ot:
                ot_wins[p1] += 1
                ot_losses[p2] += 1
                h2h[p1][p2]["ot_w"] += 1
                h2h[p2][p1]["ot_l"] += 1
            elif pk:
                pk_wins[p1] += 1
                pk_losses[p2] += 1
                ot_wins[p1] += 1
                ot_losses[p2] += 1
                h2h[p1][p2]["ot_w"] += 1
                h2h[p2][p1]["ot_l"] += 1
            if is_playoff:
                playoff_wins[p1] += 1
                playoff_losses[p2] += 1
            w_score, l_score = (0.75, 0.25) if (ot or pk) else (1.0, 0.0)
        elif s2 > s1:
            wins[p2] += 1
            losses[p1] += 1
            h2h[p2][p1]["w"] += 1
            h2h[p1][p2]["l"] += 1
            if ot:
                ot_wins[p2] += 1
                ot_losses[p1] += 1
                h2h[p2][p1]["ot_w"] += 1
                h2h[p1][p2]["ot_l"] += 1
            elif pk:
                pk_wins[p2] += 1
                pk_losses[p1] += 1
                ot_wins[p2] += 1
                ot_losses[p1] += 1
                h2h[p2][p1]["ot_w"] += 1
                h2h[p1][p2]["ot_l"] += 1
            if is_playoff:
                playoff_wins[p2] += 1
                playoff_losses[p1] += 1
            w_score, l_score = (0.75, 0.25) if (ot or pk) else (1.0, 0.0)
        else:
            draws[p1] += 1
            draws[p2] += 1
            w_score, l_score = 0.5, 0.5

        r1, r2 = elo[p1], elo[p2]
        e1 = 1.0 / (1.0 + 10.0 ** ((r2 - r1) / 400.0))
        e2 = 1.0 / (1.0 + 10.0 ** ((r1 - r2) / 400.0))

        if is_playoff: k = 32
        elif "Высшая" in tourn: k = 24
        elif "Средняя" in tourn: k = 20
        else: k = 16

        score1 = w_score if s1 >= s2 else l_score
        score2 = w_score if s2 >= s1 else l_score

        elo[p1] = round(r1 + k * (score1 - e1), 1)
        elo[p2] = round(r2 + k * (score2 - e2), 1)

        peak_elo[p1] = max(peak_elo[p1], elo[p1])
        peak_elo[p2] = max(peak_elo[p2], elo[p2])
        lowest_elo[p1] = min(lowest_elo[p1], elo[p1])
        lowest_elo[p2] = min(lowest_elo[p2], elo[p2])

# Inactivity Decay Calculation
active_elo = {}
decay_penalties = {}
for p in elo:
    years_inactive = max(0.0, CURRENT_YEAR - last_active_year[p])
    if years_inactive <= 0.5:
        decay = 0.0
    elif years_inactive <= 1.5:
        decay = 25.0
    else:
        decay = 25.0 + (years_inactive - 1.5) * 40.0
    
    decay_penalties[p] = round(decay, 1)
    active_elo[p] = round(max(1050.0, elo[p] - decay), 1)

TITLES = {
    "ectoPower": {"premier": 4, "cup": 2, "minor": 0, "finals": 9, "status": "АКТИВЕН", "archetype": "The Undisputed GOAT (Сверххищник)", "playstyle": "Тотальный блицкриг"},
    "PacnyTHuK": {"premier": 0, "cup": 1, "minor": 0, "finals": 3, "status": "Активен (S8)", "archetype": "Grand Clutch Master (Клатч-машина)", "playstyle": "Тактический контрудар"},
    "Kunio": {"premier": 2, "cup": 0, "minor": 0, "finals": 4, "status": "АКТИВЕН", "archetype": "The Iron Wall (Катеначчо)", "playstyle": "Глухая позиционная оборона"},
    "Romix": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Master of Steel (Академик)", "playstyle": "Сбалансированный прессинг"},
    "mafuta": {"premier": 3, "cup": 4, "minor": 0, "finals": 8, "status": "Инактив (3.5 г.)", "archetype": "Dynasty King (Император)", "playstyle": "Классический контроль поля"},
    "Transistor": {"premier": 1, "cup": 0, "minor": 0, "finals": 3, "status": "Инактив (7.5 л.)", "archetype": "Fallen Titan (Экс-чемпион S4)", "playstyle": "Агрессивный сольный дриблинг"},
    "Rock": {"premier": 0, "cup": 0, "minor": 0, "finals": 1, "status": "АКТИВЕН", "archetype": "Chaos Fighter (Финалист S9)", "playstyle": "Вертикальный силовой футбол"},
    "Cyneprepou4uk": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Heavy Striker (Боец Вышки)", "playstyle": "Открытые перестрелки"},
    "Ric25": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Premier Gatekeeper (Страж)", "playstyle": "Вязкая плотная опека"},
    "leonudomlya": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "status": "АКТИВЕН", "archetype": "Division Climber (Ветеран)", "playstyle": "Контратакующий стиль"},
    "RVD (МГБ)": {"premier": 0, "cup": 2, "minor": 0, "finals": 2, "status": "Инактив (1.5 г.)", "archetype": "Playoff Slayer (Кубковый хищник)", "playstyle": "Ураганная безбашенная атака"},
    "Memori": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Architect (Организатор)", "playstyle": "Позиционный комбинационный"},
    "Буц": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Battering Ram (Тяжеловес)", "playstyle": "Мощный силовой навал"},
    "Aeris": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Bridge (Ветеран двух лиг)", "playstyle": "Универсальный темповый"},
    "Yuliy_Cezar": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "OT Gladiator (Король овертаймов)", "playstyle": "Выносливый затяжной стиль"},
    "Kubik": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Anchor (Старожил Средней)", "playstyle": "Надёжный прагматичный"},
    "Jamlight": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "status": "АКТИВЕН", "archetype": "Division Champion (Чемпион S9)", "playstyle": "Быстрые фланговые прорывы"},
    "Dune": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Midfield Engine (Мотор Средней)", "playstyle": "Плотный прессинг"},
    "E_not": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Tenacious Fighter (Неуступчивый)", "playstyle": "Борьба за подборы"},
    "RASH": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Speedster (Скоростной форвард)", "playstyle": "Быстрые удары издали"},
    "Кирпич57": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Iron Heart (Железное сердце)", "playstyle": "Бескомпромиссная борьба"},
    "Sokol": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Prodigy (Вундеркинд Двора)", "playstyle": "Сокрушительный темп во Дворе"},
    "Hanter": {"premier": 0, "cup": 0, "minor": 1, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Emperor (Триумфатор Двора S9)", "playstyle": "Тотальный контроль новичков"},
    "Ryumaru": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Minimalist (Минималист)", "playstyle": "Низовой сухой футбол"},
    "yoxter": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Stalwart (Ветеран Двора)", "playstyle": "Оборонительный позиционный"},
    "frzz": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Striker (Форвард Двора)", "playstyle": "Контратакующий"},
    "ruby": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Contender (Бронза S9)", "playstyle": "Аккуратная игра от обороны"},
    "Taeda": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Veteran (Боец Двора)", "playstyle": "Упорные низовые матчи"},
    "Сахарок": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Novice (Дебютант)", "playstyle": "Любительский"},
    "blanco": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "Веселый Роджер": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "The Jolly Pirate (Шоумен)", "playstyle": "Хаотичный открытый"},
    "Spartacus": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "mikr84": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "АКТИВЕН", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "TBP_Machiavelli": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "BigPlay": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
    "daz": {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен (S8)", "archetype": "Yard Amateur (Любитель)", "playstyle": "Базовый"},
}

# Compile Extended Leaderboard
player_profiles = []
for p in matches_played:
    gp = matches_played[p]
    w = wins[p]
    l = losses[p]
    wr = round(w / gp * 100, 1) if gp > 0 else 0
    gf = goals_for[p]
    ga = goals_against[p]
    gd = gf - ga
    gpg = round(gf / gp, 2) if gp > 0 else 0
    gapg = round(ga / gp, 2) if gp > 0 else 0
    spectacle = round((gf + ga) / gp, 2) if gp > 0 else 0
    tier = LEAGUE_TIERS.get(p, "Дворовая")
    t_info = TITLES.get(p, {"premier": 0, "cup": 0, "minor": 0, "finals": 0, "status": "Активен", "archetype": "Боец", "playstyle": "Стандарт"})
    years_inactive = round(CURRENT_YEAR - last_active_year[p], 1)

    # Overtime & Clutch
    ot_g = ot_matches[p]
    ot_w = ot_wins[p]
    ot_l = ot_losses[p]
    ot_wr = round(ot_w / ot_g * 100, 1) if ot_g > 0 else 0.0

    # Playoff stats
    po_g = playoff_matches[p]
    po_w = playoff_wins[p]
    po_l = playoff_losses[p]
    po_wr = round(po_w / po_g * 100, 1) if po_g > 0 else 0.0

    # Shutout percentage
    cs_pct = round(clean_sheets[p] / gp * 100, 1) if gp > 0 else 0.0
    fts_pct = round(failed_to_score[p] / gp * 100, 1) if gp > 0 else 0.0

    # Dominator Score
    tier_mult = 1.0 if tier == "Высшая" else (0.6 if tier == "Средняя" else 0.3)
    activity_mult = max(0.25, 1.0 - (years_inactive * 0.1))
    dom_score = round(
        ((active_elo[p] - 1000) * 0.8 + 
         t_info["premier"] * 80 + 
         t_info["cup"] * 60 + 
         t_info["minor"] * 20 + 
         t_info["finals"] * 25 + 
         gd * tier_mult * 0.5 + 
         w * tier_mult * 2.0) * activity_mult,
        1
    )

    last_season = "?"
    for s in reversed(SEASON_ORDER):
        if last_active_year.get(p, 0) >= SEASON_YEAR[s] - 0.5:
            last_season = s
            break

    player_profiles.append({
        "player": p,
        "league": tier,
        "status": t_info["status"],
        "archetype": t_info["archetype"],
        "playstyle": t_info["playstyle"],
        "active_elo": active_elo[p],
        "peak_elo": peak_elo[p],
        "decay_penalty": decay_penalties[p],
        "years_inactive": years_inactive,
        "last_season": last_season,
        # Performance
        "matches": gp,
        "wins": w,
        "losses": l,
        "win_rate": wr,
        # Scoring
        "goals_for": gf,
        "goals_against": ga,
        "goal_diff": gd,
        "gpg": gpg,
        "gapg": gapg,
        "spectacle_factor": spectacle,
        # Clutch / Overtime
        "ot_matches": ot_g,
        "ot_wins": ot_w,
        "ot_losses": ot_l,
        "ot_win_rate": ot_wr,
        # Playoff
        "playoff_matches": po_g,
        "playoff_wins": po_w,
        "playoff_losses": po_l,
        "playoff_win_rate": po_wr,
        # Goalkeeping & Defense
        "clean_sheets": clean_sheets[p],
        "clean_sheet_pct": cs_pct,
        "failed_to_score": failed_to_score[p],
        "failed_to_score_pct": fts_pct,
        # Trophies
        "premier_titles": t_info["premier"],
        "cup_titles": t_info["cup"],
        "minor_titles": t_info["minor"],
        "major_finals": t_info["finals"],
        "dominator_score": dom_score
    })

# Sort player profiles by Active Elo
player_profiles.sort(key=lambda x: x["active_elo"], reverse=True)

# Top Blowouts
all_blowouts.sort(key=lambda x: x["diff"], reverse=True)
top_blowouts = all_blowouts[:15]

# Top Thrillers
all_thrillers.sort(key=lambda x: x["total_goals"], reverse=True)
top_thrillers = all_thrillers[:15]

# Clutch Kings ranking (min 3 OT matches)
clutch_ranking = [p for p in player_profiles if p["ot_matches"] >= 3]
clutch_ranking.sort(key=lambda x: (x["ot_win_rate"], x["ot_wins"]), reverse=True)

# Defensive Walls ranking (sorted by lowest GAPG with min 15 matches)
defensive_walls = [p for p in player_profiles if p["matches"] >= 15]
defensive_walls.sort(key=lambda x: (x["gapg"], -x["clean_sheets"]))

# Offensive Blitzkrieg ranking (sorted by highest GPG with min 15 matches)
offensive_blitz = [p for p in player_profiles if p["matches"] >= 15]
offensive_blitz.sort(key=lambda x: (-x["gpg"], -x["goals_for"]))

# Spectacle Ranking (Highest total goals per game)
spectacle_ranking = [p for p in player_profiles if p["matches"] >= 15]
spectacle_ranking.sort(key=lambda x: -x["spectacle_factor"])

# Key H2H Rivalries and Nemesis Matchups
nemesis_matchups = [
    {
        "rivalry": "Финал эпох: ectoPower vs PacnyTHuK",
        "p1": "ectoPower", "p2": "PacnyTHuK",
        "record": f"{h2h['ectoPower']['PacnyTHuK']['w']}W - {h2h['PacnyTHuK']['ectoPower']['w']}W (голы {h2h['ectoPower']['PacnyTHuK']['gf']}:{h2h['ectoPower']['PacnyTHuK']['ga']})",
        "notes": "Единственный игрок в мире, имеющий положительный баланс личных встреч против ectoPower!"
    },
    {
        "rivalry": "Кошмар наяву: Rock vs ectoPower",
        "p1": "Rock", "p2": "ectoPower",
        "record": f"0W - 7L (голы 11:36)",
        "notes": "Абсолютный психологический барьер Рока: 7 матчей, 0 побед, сухой разгром в финале S9 (0:5)."
    },
    {
        "rivalry": "Стена против Стража: Kunio vs Ric25",
        "p1": "Kunio", "p2": "Ric25",
        "record": f"4W - 0L (голы 9:3)",
        "notes": "Рик ни разу не смог вскрыть катеначчо Кунио в официальных встречах Вышки."
    },
    {
        "rivalry": "Битва ветеранов Вышки: Romix vs ectoPower",
        "p1": "Romix", "p2": "ectoPower",
        "record": f"{h2h['Romix']['ectoPower']['w']}W - {h2h['ectoPower']['Romix']['w']}W (голы {h2h['Romix']['ectoPower']['gf']}:{h2h['Romix']['ectoPower']['ga']})",
        "notes": "Ожесточённое противостояние двух старожилов лиги: Ромикс регулярно цепляет победы, но плей-офф за ectoPower."
    },
    {
        "rivalry": "Reality Check: Sokol vs Kunio",
        "p1": "Sokol", "p2": "Kunio",
        "record": f"1W - 4L (голы 6:14)",
        "notes": "Кунио показательно деклассировал доминатора Двора в серии 1/4 финала Кубка Лиг."
    },
    {
        "rivalry": "Reality Check 2: Hanter vs Ric25",
        "p1": "Hanter", "p2": "Ric25",
        "record": f"0W - 3L (голы 0:8)",
        "notes": "Хантер (85.7% побед во Дворе) был сметён Риком всухую в первом же раунде Кубка."
    }
]

# Master JSON export
master_json = {
    "title": "NEKKETSU SPORTS TOURNAMENTS — Kunio-kun no Nekketsu Soccer League Comprehensive Esports Database",
    "generation_timestamp": "2026-10-24T23:55:00",
    "metadata": {
        "game": "Kunio-kun no Nekketsu Soccer League (Goal 3 / 热血足球)",
        "platform": "NES / Famicom / Dendy (Mednafen Netplay)",
        "community_url": "https://vk.ru/nekketsu",
        "total_matches_analyzed": len(all_matches),
        "total_players_tracked": len(player_profiles),
        "total_goals_recorded": sum(m["s1"] + m["s2"] for m in all_matches),
        "total_ot_pk_matches": sum(1 for m in all_matches if m.get("ot") or m.get("pk")),
        "avg_goals_per_match": round(sum(m["s1"] + m["s2"] for m in all_matches) / len(all_matches), 2)
    },
    "power_rankings": player_profiles,
    "divisions": {
        "premier_league": [p for p in player_profiles if p["league"] == "Высшая"],
        "middle_league": [p for p in player_profiles if p["league"] == "Средняя"],
        "yard_league": [p for p in player_profiles if p["league"] == "Дворовая"]
    },
    "clutch_and_overtime_index": clutch_ranking,
    "defensive_walls_index": defensive_walls,
    "offensive_blitz_index": offensive_blitz,
    "spectacle_index": spectacle_ranking,
    "all_time_records": {
        "top_blowouts": top_blowouts,
        "top_thrillers": top_thrillers
    },
    "kryptonite_rivalries": nemesis_matchups
}

with open("c:\\Users\\Aeros\\Desktop\\Мастер-таблица\\nekketsu_master_table.json", "w", encoding="utf-8") as f:
    json.dump(master_json, f, ensure_ascii=False, indent=2)

print("nekketsu_master_table.json updated successfully with ALL modules!")
