"""Мастер-таблица сайта (``nekketsu_master_table.json``): документ целиком считается из пула матчей.

Elo считается не здесь, а в `portal.elo` — там формула, её параметры и порядок партий. Здесь
остается то, что мастер-таблица и собирает: статистика за карьеру, титулы, индексы и разделы
документа.
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from portal import elo
from portal.master_tables import (
    COMMUNITY_URL,
    CURRENT_YEAR,
    DEFAULT_TITLE,
    DEFAULT_TIER,
    DOCUMENT_TITLE,
    GAME,
    LEAGUE_TIERS,
    NEMESIS_MATCHUPS,
    PLATFORM,
    SEASON_ORDER,
    SEASON_YEAR,
    TITLES,
)

OUTPUT_PATH = Path("nekketsu_master_table.json")

TIER_MULTIPLIER = {"Высшая": 1.0, "Средняя": 0.6}
DEFAULT_TIER_MULTIPLIER = 0.3
ACTIVITY_FLOOR = 0.25
ACTIVITY_PER_YEAR = 0.1

RECORDS_LIMIT = 15
MIN_MATCHES_FOR_INDEX = 15
MIN_OT_MATCHES_FOR_CLUTCH = 3


@dataclass
class Tally:
    """Всё, что накопляется за один проход пула по порядку."""

    elo: dict = field(default_factory=dict)
    peak_elo: dict = field(default_factory=dict)
    # Сколько партий игрок провёл именно в рейтинговом пуле: по ним движок решает, новичок ли
    # он (у новичка K полуторный), и по ним же страница может показать, что рейтинг ещё шаткий.
    rated_games: dict = field(default_factory=dict)
    calibration: dict = field(default_factory=dict)
    last_active_year: dict = field(default_factory=dict)
    last_played_season: dict = field(default_factory=dict)
    matches_played: dict = field(default_factory=lambda: defaultdict(int))
    wins: dict = field(default_factory=lambda: defaultdict(int))
    losses: dict = field(default_factory=lambda: defaultdict(int))
    goals_for: dict = field(default_factory=lambda: defaultdict(int))
    goals_against: dict = field(default_factory=lambda: defaultdict(int))
    scored_games: dict = field(default_factory=lambda: defaultdict(int))
    clean_sheets: dict = field(default_factory=lambda: defaultdict(int))
    failed_to_score: dict = field(default_factory=lambda: defaultdict(int))
    ot_matches: dict = field(default_factory=lambda: defaultdict(int))
    ot_wins: dict = field(default_factory=lambda: defaultdict(int))
    ot_losses: dict = field(default_factory=lambda: defaultdict(int))
    playoff_matches: dict = field(default_factory=lambda: defaultdict(int))
    playoff_wins: dict = field(default_factory=lambda: defaultdict(int))
    playoff_losses: dict = field(default_factory=lambda: defaultdict(int))
    head_to_head: dict = field(default_factory=lambda: defaultdict(
        lambda: defaultdict(lambda: {"w": 0, "l": 0, "gf": 0, "ga": 0, "ot_w": 0, "ot_l": 0})
    ))
    blowouts: list = field(default_factory=list)
    thrillers: list = field(default_factory=list)


def technical_winner(match):
    """Сторона, которой засчитана техническая победа, либо None: тогда матч считается сыгранным.

    Победителя берёт из поля ``technical_loser`` — по имени игрока решение принимать нельзя,
    иначе правка справочника молча переписывает чужие результаты.
    """
    if not (match.get("is_technical") or match.get("is_forfeit")):
        return None
    loser = match.get("technical_loser")
    if loser == match["p1"]:
        return match["p2"]
    if loser == match["p2"]:
        return match["p1"]
    return None


def replay(matches):
    """Прогон рейтингового пула в хронологическом порядке: Elo от порядка зависит.

    Порядок берётся не из перечня сезонов, а из года самой партии (`portal.elo.rating_year`),
    поэтому в рейтинг можно взять и строку вики, и помеченную вручную игру турнира — с тем же
    правилом, что и для пула.
    """
    tally = Tally()
    for match in elo.order_matches(matches):
        season_year = elo.rating_year(match)
        p1, p2 = match["p1"], match["p2"]
        s1, s2 = match["s1"], match["s2"]
        ot, pk = match.get("ot", False), match.get("pk", False)
        is_playoff = match.get("is_playoff", False)
        season = match["season"]

        winner = technical_winner(match)
        if match.get("is_technical") and not winner:
            print(f"Warning: technical row names no side of this match: "
                  f"{match.get('technical_loser')} not in ({p1}, {p2}) — {match['tournament']}")
        if winner:
            # Несыгранный матч: в зачёт идёт только формальная победа по счёту источника.
            # Ни Elo, ни поражение снявшегося игрока сюда не попадают намеренно.
            tally.wins[winner] += 1
            tally.matches_played[winner] += 1
            tally.goals_for[winner] += (s1 if winner == p1 else s2)
            tally.goals_against[winner] += (s2 if winner == p1 else s1)
            tally.last_active_year[winner] = season_year
            continue

        tally.last_active_year[p1] = season_year
        tally.last_active_year[p2] = season_year
        tally.last_played_season[p1]=season;tally.last_played_season[p2]=season
        tally.matches_played[p1] += 1
        tally.matches_played[p2] += 1
        actual_goals=not match.get('is_series')
        g1,g2=(s1,s2) if actual_goals else (0,0)
        tally.goals_for[p1] += g1
        tally.goals_against[p1] += g2
        tally.goals_for[p2] += g2
        tally.goals_against[p2] += g1
        if actual_goals:
            tally.scored_games[p1]+=1;tally.scored_games[p2]+=1

        if actual_goals and s2 == 0:
            tally.clean_sheets[p1] += 1
        if actual_goals and s1 == 0:
            tally.clean_sheets[p2] += 1
        if actual_goals and s1 == 0:
            tally.failed_to_score[p1] += 1
        if actual_goals and s2 == 0:
            tally.failed_to_score[p2] += 1

        if actual_goals:tally.thrillers.append({"p1": p1, "p2": p2, "s1": s1, "s2": s2,
                                "total_goals": s1 + s2, "tournament": match["tournament"],
                                "stage": match.get("stage", "Регулярный сезон"), "season": season})

        if actual_goals and s1 != s2:
            top, bottom = (p1, p2) if s1 > s2 else (p2, p1)
            tally.blowouts.append({"winner": top, "loser": bottom,
                                   "score_winner": max(s1, s2), "score_loser": min(s1, s2),
                                   "diff": abs(s1 - s2), "tournament": match["tournament"],
                                   "stage": match.get("stage", "Регулярный сезон"), "season": season})

        tally.head_to_head[p1][p2]["gf"] += g1
        tally.head_to_head[p1][p2]["ga"] += g2
        tally.head_to_head[p2][p1]["gf"] += g2
        tally.head_to_head[p2][p1]["ga"] += g1

        if ot or pk:
            tally.ot_matches[p1] += 1
            tally.ot_matches[p2] += 1
        if is_playoff:
            tally.playoff_matches[p1] += 1
            tally.playoff_matches[p2] += 1

        previous_calibration={name:tally.calibration.get(name,{}).get('calibrated',False) for name in (p1,p2)}
        tally.elo[p1], tally.elo[p2] = elo.play(match, tally.elo, tally.rated_games,tally.calibration)
        for name in (p1,p2):
            first=tally.calibration[name]['calibrated'] and not previous_calibration[name]
            tally.peak_elo[name]=tally.elo[name] if first else max(tally.peak_elo.get(name,tally.elo[name]),tally.elo[name])

        decided=match.get('outcome_a') in ('win','loss') and match.get('outcome_b') in ('win','loss')
        if s1 != s2 or decided:
            top, bottom = ((p1,p2) if match['outcome_a']=='win' else (p2,p1)) if decided else ((p1,p2) if s1>s2 else (p2,p1))
            tally.wins[top] += 1
            tally.losses[bottom] += 1
            tally.head_to_head[top][bottom]["w"] += 1
            tally.head_to_head[bottom][top]["l"] += 1
            if ot or pk:
                tally.ot_wins[top] += 1
                tally.ot_losses[bottom] += 1
                tally.head_to_head[top][bottom]["ot_w"] += 1
                tally.head_to_head[bottom][top]["ot_l"] += 1
            if is_playoff:
                tally.playoff_wins[top] += 1
                tally.playoff_losses[bottom] += 1

    return tally


def decay(tally):
    """Совместимый интерфейс: в v2 простой не меняет оценку силы."""
    active_elo, penalties = {}, {}
    for name, rating in tally.elo.items():
        penalty = elo.decay_penalty(max(0.0, CURRENT_YEAR - tally.last_active_year[name]))
        penalties[name] = round(penalty, 1)
        active_elo[name] = elo.active_rating(rating, penalty)
    return active_elo, penalties


def last_season_of(last_active_year):
    for season in reversed(SEASON_ORDER):
        if last_active_year >= SEASON_YEAR[season] - 0.5:
            return season
    return "?"


def build_profiles(tally, active_elo, penalties):
    profiles = []
    for name in tally.matches_played:
        gp = tally.matches_played[name]
        scored=tally.scored_games[name]
        tier = tally.calibration.get(name,{}).get('tier') or 'Не подтверждена'
        titles = TITLES.get(name, DEFAULT_TITLE)
        years_inactive = max(0.0,round(CURRENT_YEAR - tally.last_active_year[name], 1))
        tier_mult = TIER_MULTIPLIER.get(tier, DEFAULT_TIER_MULTIPLIER)
        activity_mult = max(ACTIVITY_FLOOR, 1.0 - (years_inactive * ACTIVITY_PER_YEAR))
        goal_diff = tally.goals_for[name] - tally.goals_against[name]
        ot_gp = tally.ot_matches[name]

        dominator = round(
            ((active_elo[name] - 1000) * 0.8
             + titles["premier"] * 80
             + titles["cup"] * 60
             + titles["minor"] * 20
             + titles["finals"] * 25
             + goal_diff * tier_mult * 0.5
             + tally.wins[name] * tier_mult * 2.0) * activity_mult,
            1,
        )

        profiles.append({
            "player": name,
            "league": tier,
            "status": titles["status"],
            "archetype": titles["archetype"],
            "playstyle": titles["playstyle"],
            "active_elo": active_elo[name],
            "peak_elo": tally.peak_elo[name],
            "rated_games": tally.rated_games.get(name, 0),
            "provisional": tally.rated_games.get(name, 0) < elo.LEARNING_WINDOW or not tally.calibration.get(name,{}).get('calibrated'),
            "rating_model":elo.MODEL_VERSION,
            "rating_calibrated":bool(tally.calibration.get(name,{}).get('calibrated')),
            "decay_penalty": penalties[name],
            "years_inactive": years_inactive,
            "last_season": tally.last_played_season.get(name,last_season_of(tally.last_active_year[name])),
            "matches": gp,
            "wins": tally.wins[name],
            "losses": tally.losses[name],
            "win_rate": round(tally.wins[name] / gp * 100, 1) if gp > 0 else 0,
            "goals_for": tally.goals_for[name],
            "goals_against": tally.goals_against[name],
            "goal_diff": goal_diff,
            "gpg": round(tally.goals_for[name] / scored, 2) if scored > 0 else 0,
            "gapg": round(tally.goals_against[name] / scored, 2) if scored > 0 else 0,
            "spectacle_factor": round((tally.goals_for[name] + tally.goals_against[name]) / scored, 2) if scored > 0 else 0,
            "ot_matches": ot_gp,
            "ot_wins": tally.ot_wins[name],
            "ot_losses": tally.ot_losses[name],
            "ot_win_rate": round(tally.ot_wins[name] / ot_gp * 100, 1) if ot_gp > 0 else 0.0,
            "playoff_matches": tally.playoff_matches[name],
            "playoff_wins": tally.playoff_wins[name],
            "playoff_losses": tally.playoff_losses[name],
            "playoff_win_rate": round(tally.playoff_wins[name] / tally.playoff_matches[name] * 100, 1)
            if tally.playoff_matches[name] > 0 else 0.0,
            "clean_sheets": tally.clean_sheets[name],
            "clean_sheet_pct": round(tally.clean_sheets[name] / scored * 100, 1) if scored > 0 else 0.0,
            "failed_to_score": tally.failed_to_score[name],
            "failed_to_score_pct": round(tally.failed_to_score[name] / scored * 100, 1) if scored > 0 else 0.0,
            "premier_titles": titles["premier"],
            "cup_titles": titles["cup"],
            "minor_titles": titles["minor"],
            "major_finals": titles["finals"],
            "dominator_score": dominator,
        })

    profiles.sort(key=lambda row: row["active_elo"], reverse=True)
    return profiles


def build_indexes(profiles):
    clutch = [p for p in profiles if p["ot_matches"] >= MIN_OT_MATCHES_FOR_CLUTCH]
    clutch.sort(key=lambda x: (x["ot_win_rate"], x["ot_wins"]), reverse=True)

    regulars = [p for p in profiles if p["matches"] >= MIN_MATCHES_FOR_INDEX]
    defensive = sorted(regulars, key=lambda x: (x["gapg"], -x["clean_sheets"]))
    offensive = sorted(regulars, key=lambda x: (-x["gpg"], -x["goals_for"]))
    spectacle = sorted(regulars, key=lambda x: -x["spectacle_factor"])
    return clutch, defensive, offensive, spectacle


def build_records(tally):
    blowouts = sorted(tally.blowouts, key=lambda x: x["diff"], reverse=True)[:RECORDS_LIMIT]
    thrillers = sorted(tally.thrillers, key=lambda x: x["total_goals"], reverse=True)[:RECORDS_LIMIT]
    return {"top_blowouts": blowouts, "top_thrillers": thrillers}


def rivalry_record(matchup, head_to_head):
    if matchup["record"] is not None:
        return matchup["record"]
    p1, p2 = matchup["p1"], matchup["p2"]
    left, right = head_to_head[p1][p2], head_to_head[p2][p1]
    return f"{left['w']}W - {right['w']}W (голы {left['gf']}:{left['ga']})"


def build_rivalries(head_to_head):
    return [
        {"rivalry": m["rivalry"], "p1": m["p1"], "p2": m["p2"],
         "record": rivalry_record(m, head_to_head), "notes": m["notes"]}
        for m in NEMESIS_MATCHUPS
    ]


def pool_fingerprint(matches):
    """Отпечаток пула вместо метки времени: сборка остаётся детерминированной, но правка
    любого матча меняет его, и по файлу видно, из каких данных он собран."""
    canonical = json.dumps(
        [[m["season"], m["tournament"], m.get("stage", ""), m["p1"], m["p2"], m["s1"], m["s2"],
          bool(m.get("ot")), bool(m.get("pk")), bool(m.get("is_playoff")), bool(technical_winner(m)),
          m.get('league'),m.get('played_on'),m.get('outcome_a'),m.get('outcome_b'),bool(m.get('is_series')),elo.MODEL_VERSION]
         for m in matches],
        ensure_ascii=False, sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()[:12]


def build_payload(matches):
    tally = replay(matches)
    active_elo, penalties = decay(tally)
    profiles = build_profiles(tally, active_elo, penalties)
    clutch, defensive, offensive, spectacle = build_indexes(profiles)
    scored_matches=[m for m in matches if not m.get('is_series')]
    total_goals = sum(m["s1"] + m["s2"] for m in scored_matches)

    return {
        "title": DOCUMENT_TITLE,
        "source_fingerprint": pool_fingerprint(matches),
        "metadata": {
            "game": GAME,
            "platform": PLATFORM,
            "community_url": COMMUNITY_URL,
            "total_matches_analyzed": len(matches),
            "total_players_tracked": len(profiles),
            "total_goals_recorded": total_goals,
            "total_ot_pk_matches": sum(1 for m in matches if m.get("ot") or m.get("pk")),
            "avg_goals_per_match": round(total_goals / len(scored_matches), 2) if scored_matches else 0,
            "rating_model":elo.MODEL_VERSION,
        },
        "power_rankings": profiles,
        "divisions": {
            "premier_league": [p for p in profiles if p["league"] == "Высшая"],
            "middle_league": [p for p in profiles if p["league"] == "Средняя"],
            "yard_league": [p for p in profiles if p["league"] == "Дворовая"],
        },
        "clutch_and_overtime_index": clutch,
        "defensive_walls_index": defensive,
        "offensive_blitz_index": offensive,
        "spectacle_index": spectacle,
        "all_time_records": build_records(tally),
        "kryptonite_rivalries": build_rivalries(tally.head_to_head),
    }


def main(matches, output_dir=Path(".")):
    payload = build_payload(matches)
    output_path = Path(output_dir) / OUTPUT_PATH
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"Master table regenerated from {len(matches)} matches "
          f"(pool {payload['source_fingerprint']}) -> {output_path.resolve()}")
    return payload
