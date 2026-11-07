"""#85 (вариант А): снятая вторая модель рейтинга из portal/player_profiles.py.

История, не рабочий код. В сборке сайта не участвует, никто его не импортирует
(см. archive/README.md). Здесь дословно сохранено то, что надстраивалось поверх числа
движка portal/elo.py и убрано решением владельца «мастер-таблица авторитетна»:

- собственный штраф за простой (25 + 35/год) вместо движкового (25 + 40/год);
- выдуманное число из вывески лиги DIVISION_BASE_ELO для игроков без рейтинговых партий;
- калибровка confidence/calibrated_skill, пол 1050 и округление поверх полей движка;
- справочная подмена пика HOF_PEAK_ELO на рейтинговом пути пуловых игроков;
- прежние рейтинговые поля provisional_profile и прежняя сортировка, падавшая на None.

НЕ снимались и остались в portal/player_profiles.py: CURRENT_YEAR, SEASON_YEAR_MAP и
last_activity — они обслуживают только биографию карточек вне пула (years_inactive и
last_season), которую владелец велел сохранить «как посчитана». Рейтинговый год отсчёта
и таблица сезонов живут в portal/master_tables.py и читаются движком.

Запускать нельзя: это снимок старой логики, а не генератор. Актуальный рейтинг считает
portal/elo.py, кладёт в мастер-таблицу portal/master_table.py, а карточка страницы
берёт поля движка дословно.
"""

DIVISION_BASE_ELO = {"Высшая": 1400.0, "Средняя": 1300.0, "Дворовая": 1200.0}


def decay_penalty(years_inactive, is_active):
    if is_active or years_inactive <= 0.5:
        return 0.0
    if years_inactive <= 1.5:
        return 25.0
    return round(25.0 + (years_inactive - 1.5) * 35.0, 1)


# --- прежний блок build() (дословно): калибровка, пол, округление, подмена пика ---
#
#         last_year, last_season = last_activity(matches, is_active)
#         years_inactive = max(0.0, round(CURRENT_YEAR - last_year, 1)) if not is_active else 0.0
#         decay = decay_penalty(years_inactive, is_active)
#
#         if name in master_profiles:
#             p = dict(master_profiles[name])
#             league = p.get("league", "Средняя")
#             raw_peak = p.get("peak_elo", 1400.0)
#             raw_active = p.get("active_elo", 1400.0)
#         else:
#             league = playstyle_league(matches, is_hall_of_famer)
#             raw_peak = DIVISION_BASE_ELO[league] + (stats["win_rate"] - 50.0) * 3.0
#             raw_active = raw_peak
#             p = provisional_profile(name, league, stats, years_inactive, decay, last_season)
#
#         confidence = min(1.0, stats["total"] / 20.0) if stats["total"] > 0 else 0.0
#         calibrated_skill = 1200.0 + (raw_peak - 1200.0) * confidence
#         peak_elo = HOF_PEAK_ELO.get(name, max(round(calibrated_skill, 1), round(raw_peak, 1)))
#         if is_active:
#             active_elo = round(max(1050.0, raw_active), 1)
#             decay = 0.0
#         else:
#             active_elo = round(max(1050.0, calibrated_skill - decay), 1)
#         p["active_elo"] = active_elo
#         p["peak_elo"] = peak_elo
#         p["decay_penalty"] = decay
#         p["years_inactive"] = years_inactive
#         p["last_season"] = last_season
#
# --- прежняя подмена пика в apply_status_badges (рейтинговый путь пуловых легенд) ---
#
#         p["peak_elo"] = HOF_PEAK_ELO.get(name, p["peak_elo"])
#
# --- прежние рейтинговые поля provisional_profile (сигнатура брала decay) ---
#
# def provisional_profile(name, league, stats, years_inactive, decay, last_season):
#         "active_elo": 1200.0,
#         "peak_elo": 1200.0,
#         "decay_penalty": decay,
#
# --- прежняя сортировка build(), падавшая на None после введения rated ---
#
#     profiles.sort(key=lambda p: (1 if p["is_active"] else 0, p["active_elo"]), reverse=True)