"""Карточка каждого игрока: итоги карьеры, рейтинг движка, значки и аватар.

Рейтинг здесь не считается. Единственный движок — portal/elo.py, его числа кладёт
portal/master_table.py в power_rankings мастер-таблицы. Для игрока из пула все пять
рейтинговых полей (active_elo, peak_elo, decay_penalty, years_inactive, last_season)
берутся дословно из записи движка — без калибровки, без пола 1050, без округлений и без
справочной подмены пика.

Правило для игроков вне пула (есть только каталожные партии): нет рейтинговых партий —
нет рейтинга. active_elo и peak_elo равны None, decay_penalty = 0.0, признак rated = False.
Обоснование: докстринг portal/elo.py прямо говорит, что старт из вывески лиги
(1600/1350/1050) убран, потому что рейтинг зарабатывается партиями, а не классификацией;
возвращать выдуманное число из вывески для этих игроков значило бы оставить ту самую
вторую модель. Исключение — легенды Зала славы вне пула: у них сохраняется курируемый
peak_elo из HOF_PEAK_ELO как архивная почётная величина, но active_elo тоже None.

CURRENT_YEAR, SEASON_YEAR_MAP и last_activity обслуживают только биографию карточек
вне пула (years_inactive и last_season — это биография, не рейтинг); рейтинговый год
отсчёта и таблица сезонов живут в portal/master_tables.py и читаются движком.
"""

import re

from portal.names import profile_sort_order
from portal.quote_tables import CANONICAL_PLAYER_QUOTES
from portal.roster_tables import (
    CLUB_TEAMS_FILTER,
    CORE_ACTIVE_COMMUNITY,
    DEFAULT_AVATARS,
    HALL_OF_FAME_LEGENDS,
    HOF_PEAK_ELO,
    HOF_REASONS,
)

# Только для биографии карточек вне пула (см. докстринг модуля): рейтинговый год отсчёта
# и таблица сезонов берутся движком из portal/master_tables.py, а не отсюда.
CURRENT_YEAR = 2024.5
SEASON_YEAR_MAP = {
    1: 2015.5,
    2: 2016.0,
    3: 2016.5,
    4: 2017.0,
    5: 2017.5,
    6: 2018.0,
    7: 2021.0,
    8: 2023.0,
    9: 2024.5,
}
MAJOR_FINALISTS = ("WiSe", "Huba Buba", "izzzotope", "Transistor", "mafuta")
HOF_FALLBACK_REASON = "Легендарный ветеран Высшей лиги NST."
AVATAR_FALLBACK = "https://api.dicebear.com/7.x/bottts/svg?seed={name}&backgroundColor=183c5c"
SEASON_IN_TEXT = re.compile(r"Season\s*(\d+)", re.I)
YEAR_IN_TEXT = re.compile(r"20\d\d")


def league_players(player_matches, master_profiles):
    """Все, кто когда-либо играл: ядро ростера, легенды и любой ник с сыгранными партиями."""
    names = set(CORE_ACTIVE_COMMUNITY + HALL_OF_FAME_LEGENDS + list(master_profiles))
    for nickname, history in player_matches.items():
        if nickname in CLUB_TEAMS_FILTER or not history:
            continue
        if "&" in nickname or "/" in nickname:
            continue
        names.add(nickname)
    return names


def career_stats(matches, addon):
    technical_losses = sum(1 for m in matches if m.get("is_technical") and "ПОРАЖЕНИЕ" in m.get("result", ""))
    played = len(matches) - technical_losses
    wins = sum(1 for m in matches if m.get("result") in ["ПОБЕДА", "ТП (ПОБЕДА)"])
    clutch_wins = addon["ot_w"] + addon["pk_w"]
    clutch_total = clutch_wins + addon["ot_l"] + addon["pk_l"]
    return {
        "total": len(matches),
        "played": played,
        "wins": wins,
        "losses": sum(1 for m in matches if m.get("result") == "ПОРАЖЕНИЕ"),
        "draws": sum(1 for m in matches if m.get("result") == "НИЧЬЯ"),
        "goals_for": sum(m.get("score_for", 0) for m in matches if not m.get("is_technical")),
        "goals_against": sum(m.get("score_against", 0) for m in matches if not m.get("is_technical")),
        "win_rate": round(wins / played * 100, 1) if played > 0 else 0.0,
        "clean_sheets": sum(1 for m in matches if m.get("score_against") == 0),
        "clutch_wins": clutch_wins,
        "clutch_total": clutch_total,
        "clutch_win_rate": round(clutch_wins / clutch_total * 100, 1) if clutch_total > 0 else 0.0,
        "ot_matches": addon["ot_w"] + addon["ot_l"],
        "ot_wins": addon["ot_w"],
        "ot_losses": addon["ot_l"],
    }


def last_activity(matches, is_active):
    """Метка сезона и середина года последней нетехнической партии — биография карточки."""
    last_year = 0.0
    label = "Season 9" if is_active else "Архив"
    for m in matches:
        if m.get("is_technical"):
            continue
        season = str(m.get("season", ""))
        found = SEASON_IN_TEXT.search(season)
        if found:
            season_num = int(found.group(1))
            year = SEASON_YEAR_MAP.get(season_num, 2016.0)
            if year > last_year:
                last_year, label = year, f"Season {season_num}"
        elif "20" in season:
            found_year = YEAR_IN_TEXT.search(season)
            if found_year and float(found_year.group(0)) > last_year:
                last_year = float(found_year.group(0))
    if last_year == 0.0:
        last_year = CURRENT_YEAR if is_active else 2016.5
    return last_year, label


def playstyle_league(matches, is_hall_of_famer):
    """Высший дивизион, которого достиг игрок без архивного профиля, — классификация, не рейтинг."""
    leagues = {m.get("league", "") for m in matches}
    if is_hall_of_famer or any("высш" in league.lower() for league in leagues):
        return "Высшая"
    if any("перв" in league.lower() or "средн" in league.lower() for league in leagues):
        return "Средняя"
    return "Дворовая"


def provisional_profile(name, league, stats, years_inactive, last_season):
    """Карточка игрока вне пула: биография и итоги есть, рейтинга нет (rated = False).

    Рейтинговые поля намеренно пусты: active_elo/peak_elo = None, decay_penalty = 0.0.
    Почётный архивный пик легенды подставляется вызывающим из HOF_PEAK_ELO, не здесь.
    """
    total = stats["total"]
    return {
        "player": name,
        "league": league,
        "status": "Инактив (Ветеран)",
        "archetype": "Ветеран сцены",
        "playstyle": "Классический NES стиль",
        "active_elo": None,
        "peak_elo": None,
        "decay_penalty": 0.0,
        "rated": False,
        "years_inactive": years_inactive,
        "last_season": last_season,
        "gpg": round(stats["goals_for"] / total, 2) if total > 0 else 0.0,
        "gapg": round(stats["goals_against"] / total, 2) if total > 0 else 0.0,
        "spectacle_factor": 2.5,
        "ot_matches": stats["ot_matches"],
        "ot_wins": stats["ot_wins"],
        "ot_losses": stats["ot_losses"],
        "ot_win_rate": round(stats["ot_wins"] / stats["ot_matches"] * 100, 1)
        if stats["ot_matches"] > 0
        else 0.0,
        "playoff_matches": 0,
        "playoff_wins": 0,
        "playoff_losses": 0,
        "playoff_win_rate": 0.0,
        "clean_sheet_pct": 0.0,
        "failed_to_score": 0,
        "failed_to_score_pct": 0.0,
        # Числа взяты из подиумов сезонов (см. portal/master_tables.TITLES): у mafuta два титула
        # и три Кубка лиги — Сезона 1 он не выигрывал, победитель той сетки источниками не назван.
        "premier_titles": 2 if name == "mafuta" else (1 if name == "Transistor" else 0),
        "cup_titles": 3 if name == "mafuta" else (2 if name == "RVD (МГБ)" else 0),
        "minor_titles": 0,
        "major_finals": 1 if name in MAJOR_FINALISTS else 0,
        "dominator_score": 100.0,
    }


def apply_status_badges(p, name, is_active, is_hall_of_famer):
    """Значки статуса и Зала славы. Пик не подменяет: рейтинговый путь берёт число движка."""
    if is_hall_of_famer:
        p["is_hall_of_fame"] = True
        p["hof_reason"] = HOF_REASONS.get(name, HOF_FALLBACK_REASON)
        p["status_badge"] = "Зал славы (Легенда)"
        p["status"] = "Зал славы"
        p["league"] = "Высшая"
    else:
        p["is_hall_of_fame"] = False
        p["hof_reason"] = None
        p["status_badge"] = "Активен (Сезон 9)" if is_active else f"Инактив ({p.get('league', 'Ветеран')})"


def apply_career_stats(p, stats, addon, matches):
    """Итоги карьеры и история партий поверх карточки (рейтинг не трогает)."""
    p["matches"] = stats["total"]
    p["wins"] = stats["wins"]
    p["losses"] = stats["losses"]
    p["draws"] = stats["draws"]
    p["win_rate"] = stats["win_rate"]
    p["goals_for"] = stats["goals_for"]
    p["goals_against"] = stats["goals_against"]
    p["goal_diff"] = stats["goals_for"] - stats["goals_against"]
    p["clean_sheets"] = stats["clean_sheets"]
    p["reg_wins"] = addon["reg_w"]
    p["pk_wins"] = addon["pk_w"]
    p["reg_losses"] = addon["reg_l"]
    p["pk_losses"] = addon["pk_l"]
    p["clutch_total"] = stats["clutch_total"]
    p["clutch_wins"] = stats["clutch_wins"]
    p["clutch_win_rate"] = stats["clutch_win_rate"]
    p["match_history"] = matches


def apply_quotes_and_avatar(p, name, quotes_by_player, avatars):
    """Цитата и аватар карточки: справочник, иначе выгрузка, иначе заглушка."""
    p["quote"] = CANONICAL_PLAYER_QUOTES.get(name) or (quotes_by_player.get(name) or [None])[0]
    p["all_quotes"] = quotes_by_player.get(name, [])
    if name in avatars:
        p["avatar"] = avatars[name]["avatar_url"]
        p["vk_name"] = avatars[name]["vk_name"]
        p["vk_id"] = avatars[name]["vk_id"]
        p["vk_domain"] = avatars[name]["domain"]
    else:
        p["avatar"] = DEFAULT_AVATARS.get(name, AVATAR_FALLBACK.format(name=name))
        p["vk_name"] = name
        p["vk_id"] = None
        p["vk_domain"] = None


def build(
    data, player_matches: dict, player_stats_addon: dict, player_quotes_dict: dict
) -> list:
    """Карточки игроков: рейтинг движка для пула, биография без рейтинга для остальных."""
    master_profiles = {p["player"]: p for p in data.master_db["power_rankings"]}
    profiles = []
    for name in sorted(league_players(player_matches, master_profiles)):
        matches = player_matches[name]
        stats = career_stats(matches, player_stats_addon[name])
        is_active = name in CORE_ACTIVE_COMMUNITY
        is_hall_of_famer = name in HALL_OF_FAME_LEGENDS
        if stats["total"] == 0 and not is_active and not is_hall_of_famer:
            continue

        if name in master_profiles:
            # Пул: все пять рейтинговых полей — дословно из движка, второй модели нет.
            p = dict(master_profiles[name])
            p["rated"] = True
        else:
            # Вне пула: рейтинговых партий нет — нет и рейтинга, остаётся биография.
            league = playstyle_league(matches, is_hall_of_famer)
            last_year, last_season = last_activity(matches, is_active)
            years_inactive = max(0.0, round(CURRENT_YEAR - last_year, 1)) if not is_active else 0.0
            p = provisional_profile(name, league, stats, years_inactive, last_season)
            if is_hall_of_famer:
                # Архивная почётная величина легенды, не рейтинг.
                p["peak_elo"] = HOF_PEAK_ELO.get(name)

        apply_status_badges(p, name, is_active, is_hall_of_famer)
        apply_career_stats(p, stats, player_stats_addon[name], matches)
        p["is_active"] = is_active
        apply_quotes_and_avatar(p, name, player_quotes_dict, data.avatars)
        profiles.append(p)

    profiles.sort(key=profile_sort_order)
    # Сначала рейтингованные по убыванию active_elo, затем без рейтинга: None с числом
    # не сравнивается, поэтому отсутствующий рейтинг вынесен в отдельный младший ключ.
    profiles.sort(key=lambda p: (p["active_elo"] is not None,
                                 p["active_elo"] if p["active_elo"] is not None else 0.0),
                  reverse=True)
    return profiles
