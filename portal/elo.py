"""Формула Elo архива: один проход по играм, которые помечены рейтинговыми.

Зачем отдельный модуль. Рейтинг на сайте считался внутри мастер-таблицы, и у него было три
неприятных свойства: старт брался из вывески лиги (1600/1350/1050 из справочника, который ведёт
человек), порядок партий — из порядка сезонов, а разница мячей на рейтинг не влияла вообще
(12:0 и 1:0 считались одним событием). Плюс вторая модель жила в `build_final_analytics` для
дашборда; сайтом она не читается. Формула сайта живёт здесь; исторический аналитический
дашборд `build_final_analytics.py` пока сохраняет отдельную модель.

    E1 = 1 / (1 + 10 ** ((R2 - R1) / SCALE))          ожидание, классика FIDE
    S1 = 1 | 0.75 | 0.5 | 0.25 | 0                    победа | в ОТ или по буллитам | ничья
    K  = K[вес] * (1.5 пока партий < 15) * MOV(|rd|)  вес соревнования, новичок, разгром
    MOV(d) = min(1 + ln(1 + d), 2.0)
    R1' = R1 + K * (S1 - E1)                          округление до 0.1

Старт для всех 1500: рейтинг зарабатывается партиями, а не классификацией лиги. Пока у игрока
меньше LEARNING_WINDOW партий, K полуторный — иначе новичок ползёт к своему уровню через сотню
игр, и его рейтинг в это время вранье. Разгром входит через логарифм и ограничен сверху:
двухкратная прибавка за счёт — это потолок, а не линия, иначе рейтинг начинает гонять по
матчу 12:0.

Порядок партий важен: Elo считается последовательно, поэтому игре нужен год. Его даёт
`rating_year`: точная дата строки, дата источника, сезон («Season 9»), год документа турнира.
Игры без года в рейтинг не берутся — иначе порядок оказался бы произвольным, а с ним и рейтинг.
"""

import math
import re

R0 = 1500.0
SCALE = 400.0
K_BY_WEIGHT = {"league": 24.0, "playoff": 32.0, "other": 16.0}
LEARNING_WINDOW = 15
PROVISIONAL_K = 1.5
MOV_CAP = 2.0

WIN_SCORE = 1.0
OVERTIME_WIN_SCORE = 0.75
DRAW_SCORE = 0.5
OVERTIME_LOSS_SCORE = 0.25
LOSS_SCORE = 0.0

DECAY_FREE_YEARS = 0.5
DECAY_STEP_YEARS = 1.5
DECAY_BASE_PENALTY = 25.0
DECAY_YEAR_RATE = 40.0
RATING_FLOOR = 1050.0

ISO_YEAR = re.compile(r"^(\d{4})-(\d{2})?")
SECONDS_PER_YEAR = 365.2425 * 86400

# Год сезона берётся из той же таблицы, что и штраф за простой: вторая таблица неминуемо
# разъехалась бы с первой. Сезонов без года в ней нет — для них работает дата строки.
from portal.master_tables import SEASON_YEAR  # noqa: E402  (цикла здесь нет: master_tables — константы)


class EloError(ValueError):
    """Игру нельзя взять в рейтинг: не из чего считать год, или стороны не 1×1."""


def expected(rating, opponent):
    """Доля ожидаемого результата для `rating` против `opponent`."""
    return 1.0 / (1.0 + 10.0 ** ((opponent - rating) / SCALE))


def actual_score(s1, s2, overtime=False, penalties=False):
    """Очки сторон по счёту: ничья 0.5, победа в ОТ или по буллитам — 0.75 против 0.25."""
    if s1 == s2:
        return DRAW_SCORE, DRAW_SCORE
    if overtime or penalties:
        return (OVERTIME_WIN_SCORE, OVERTIME_LOSS_SCORE) if s1 > s2 else (OVERTIME_LOSS_SCORE,
                                                                          OVERTIME_WIN_SCORE)
    return (WIN_SCORE, LOSS_SCORE) if s1 > s2 else (LOSS_SCORE, WIN_SCORE)


def margin_multiplier(goal_difference):
    """Множитель разгрома: 1.0 за ничью, 1.69 за +1, потолок 2.0."""
    return min(1.0 + math.log(1.0 + abs(int(goal_difference))), MOV_CAP)


def weight_of(match):
    """Вес соревнования: плей-офф, лига или всё остальное (помеченные вручную и кубки)."""
    if match.get("is_playoff"):
        return "playoff"
    return "league" if match.get("row_set") in ("pool", "catalog", None) else "other"


def k_factor(match, games_a, games_b, goal_difference):
    """K этой партии: вес соревнования × поправка новичка × разгром."""
    base = K_BY_WEIGHT[weight_of(match)]
    if games_a < LEARNING_WINDOW or games_b < LEARNING_WINDOW:
        base *= PROVISIONAL_K
    return base * margin_multiplier(goal_difference)


def rating_year(match):
    """Год партии: сезон из таблицы мастер-таблицы, иначе дата строки, иначе дата источника.

    Порядок нужен один и тот же для всех: сезонные строки пула дат не имеют, а рано занесённые
    игры вики и спецтурниров — наоборот, и ставить их в один ряд по названию сезона нельзя.
    """
    season = str(match.get("season") or "")
    for label, year in SEASON_YEAR.items():
        if label in season or season == label.replace("Season ", ""):
            return float(year)
    found = ISO_YEAR.match(str(match.get("played_on") or ""))
    if found:
        month = int(found.group(2) or 6)
        return int(found.group(1)) + (month - 0.5) / 12.0
    raw = str(match.get("source_date_raw") or "").strip()
    if raw.isdigit() and len(raw) == 10:
        return 1970.0 + int(raw) / SECONDS_PER_YEAR        # unix-секунды, как их хранит VK
    if raw.isdigit() and len(raw) == 4:
        return float(raw)                                  # год кубкового справочника
    for text in (str(match.get("doc_year") or ""), str(match.get("tournament") or "")):
        found = re.search(r"(19|20)\d{2}", text)
        if found:
            return float(found.group(0))
    raise EloError("нет года: рейтинг считается последовательно, а эту партию некуда поставить")


def order_matches(matches):
    """Партии в порядке их реального разыгрывания: год, затем порядок внутри источника."""
    dated = [(rating_year(match), match.get("order_in_source") or 0, index, match)
             for index, match in enumerate(matches)]
    return [item[3] for item in sorted(dated, key=lambda item: item[:3])]


def play(match, rating, games):
    """Одна партия: возвращает (new_a, new_b) и обновляет счётчики партий в `games`."""
    p1, p2 = match["p1"], match["p2"]
    r1, r2 = rating.get(p1, R0), rating.get(p2, R0)
    score1, score2 = actual_score(match["s1"], match["s2"], match.get("ot"), match.get("pk"))
    k = k_factor(match, games.get(p1, 0), games.get(p2, 0), abs(match["s1"] - match["s2"]))
    next1 = round(r1 + k * (score1 - expected(r1, r2)), 1)
    next2 = round(r2 + k * (score2 - expected(r2, r1)), 1)
    games[p1] = games.get(p1, 0) + 1
    games[p2] = games.get(p2, 0) + 1
    return next1, next2


def decay_penalty(years_inactive):
    """Штраф за простой: первые полгода ничего, дальше 25 и +40 за каждый лишний год."""
    if years_inactive <= DECAY_FREE_YEARS:
        return 0.0
    if years_inactive <= DECAY_STEP_YEARS:
        return DECAY_BASE_PENALTY
    return DECAY_BASE_PENALTY + (years_inactive - DECAY_STEP_YEARS) * DECAY_YEAR_RATE


def active_rating(rating, penalty):
    """Рейтинг на сегодня: с штрафом за простой и подом, ниже которого отображать нечего."""
    return round(max(RATING_FLOOR, rating - penalty), 1)
