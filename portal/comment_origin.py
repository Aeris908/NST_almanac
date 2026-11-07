"""Лига и тур строки-комментария: что о ней говорит источник, а не подставка сборщика.

Носитель `all_vk_seasons_matches.json` приходит без поля `league`: у него есть только `stage`
(«Регулярный чемпионат», «Средняя лига», «Плей-офф» …) да пара со счётом. Раньше любая такая
строка ложилась в «Высшую лигу» с туром «Плей-офф / Кубок» — независимо от того, что в
комментарии стояло «Средняя лига. 8 Тур» или «Кубок лиг, 1/4 финала». У этого ведра был и
второй эффект: фильтр псевдо-кубковых строк снимает игру со страницы сезона, и строка
оставалась только в историях игроков.

Здесь правило, которое расставляет по комментариям лигу и тур и ничего не придумывает: без
доказательства строка остаётся как есть и уходит в отчёт сборки.
"""

import re

# Разговорные названия дивизионов в комментариях: «вышка», «ВЛ», «Высшая Soccer League».
LEAGUE_MARKS = (
    (re.compile(r"высш|вышк|(?<![a-zа-я])вл(?![a-zа-я])", re.IGNORECASE), "Высшая лига"),
    (re.compile(r"средн", re.IGNORECASE), "Средняя лига"),
    (re.compile(r"дворов", re.IGNORECASE), "Дворовая лига"),
    (re.compile(r"младш", re.IGNORECASE), "Младшая лига"),
)
# Стадия сетки по номеру круга: «1/4 finals» и «1/4 финала» — одно и то же.
CUP_STAGE_MARKS = (("1/16", "1/16 финала"), ("1/8", "1/8 финала"), ("1/4", "1/4 финала"),
                   ("1/2", "1/2 финала"))
TOUR_MARK = re.compile(r"(\d+)\s*[.\-–]?\s*(?:й\s*)?тур\b", re.IGNORECASE)
CUP_FINAL = re.compile(r"кубок.*финал|финал.*кубка", re.IGNORECASE)
REGULAR_TOUR = "Регулярный сезон"
CUP_LEAGUE = "Кубок лиг"
# Так коллекционер подписывает дивизион и сетку в самом носителе.
CARRIER_LEAGUES = {league.lower(): league for _rx, league in LEAGUE_MARKS}
CARRIER_STAGE_LEAGUES = {"плей-офф": CUP_LEAGUE, "кубок": CUP_LEAGUE}


def score_in_text(text, s1, s2):
    """Встречается ли этот счёт в тексте — в любую сторону.

    Без этого комментарию нельзя верить: указатель архива иногда приводит к обсуждению, где та
    же пара сыграла другие ноги, и рамка оттуда относится к другой игре.
    """
    if not text:
        return False
    return bool(re.search(rf"(?<!\d){s1}\s*[:\-–]\s*{s2}(?!\d)|(?<!\d){s2}\s*[:\-–]\s*{s1}(?!\d)",
                          str(text)))


SERIES_IN_BRACKETS = re.compile(r"[(\[]\s*(\d{1,2})\s*[:\-–]\s*(\d{1,2})[^)\]]*[)\]]")


def shootout_of(text, s1, s2):
    """Серия буллитов ноги, названная в скобках после ничейного счёта: «4-4 (3-1)», «1:1 (4:3 PK)».

    Носитель приходит с `pk: false` даже там, где комментарий серию называет, — нога теряла
    исход и выглядела ничьей. Скобки смотрим только при равном счёте: после неравного там стоит
    пояснение или счёт другой ноги, а не доигровка. Та же конвенция, что в разборе ячейки счёта
    (`portal.player_records.parse_score_cell`): серия решает ничью, но не подменяет счёт.
    """
    if s1 != s2 or not text:
        return None
    for line in str(text).splitlines():
        if not score_in_text(line, s1, s2):
            continue
        found = SERIES_IN_BRACKETS.search(line)
        if found:
            return int(found.group(1)), int(found.group(2))
    return None


def stage_of(line):
    """Кубковая стадия, названная в строке, — или ничего."""
    stage = next((name for mark, name in CUP_STAGE_MARKS if mark in line), None)
    return stage or ("Финал" if CUP_FINAL.search(line) else None)


def frame_of(line, frame):
    """Рамка «лига — тур» после строки: что строка сама называет, остальное наследуется сверху."""
    stage = stage_of(line)
    league = next((name for rx, name in LEAGUE_MARKS if rx.search(line)), None)
    tour = TOUR_MARK.search(line)
    return {
        "league": CUP_LEAGUE if stage else league or frame["league"],
        "tour": stage or (f"{tour.group(1)} Тур" if tour else frame["tour"]),
    }


def from_comment(text, s1, s2):
    """(лига, тур) по строкам комментария, где сыграна именно эта нога; None — без доказательства.

    Комментарий называет рамку один раз («Высшая лига. 9 тур»), а ноги перечисляет ниже, поэтому
    рамка наследуется вниз по строкам. Если одна и та же пара со этим счётом показана в двух
    рамках — выбирать нечем, и строка остаётся неподтверждённой.
    """
    if not score_in_text(text, s1, s2):
        return None
    frame = {"league": None, "tour": None}
    places = set()
    for line in str(text).splitlines():
        frame = frame_of(line, frame)
        if score_in_text(line, s1, s2):
            places.add((frame["league"], frame["tour"]))
    if len(places) != 1:
        return None
    league, tour = places.pop()
    if not league:
        return None
    return league, tour or REGULAR_TOUR


def from_carrier_stage(stage):
    """Пометка коллекционера: «Средняя лига» — дивизион, «Плей-офф» — кубковая сетка."""
    lowered = str(stage or "").strip().lower()
    if lowered in CARRIER_LEAGUES:
        return CARRIER_LEAGUES[lowered], REGULAR_TOUR
    if lowered in CARRIER_STAGE_LEAGUES:
        return CARRIER_STAGE_LEAGUES[lowered], "Плей-офф"
    return None


def origin_of(stage, text, s1, s2):
    """Куда ставится строка: комментарий важнее пометки коллекционера, без доказательств — None."""
    return from_comment(text, s1, s2) or from_carrier_stage(stage)
