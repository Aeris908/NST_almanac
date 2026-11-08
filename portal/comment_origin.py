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

from portal.name_tables import ALIAS_MAP
from portal.names import clean_alias, homoglyph_fold

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


# Пометка доигровки, которой источник подписывает серию: «(PK 6:7)», «(ПК 2-5)», «(пк: 9-7)»,
# «6-6 PK 5:4», «2:2 7:6пен.». Словарь тот же, что у сверки комментариев (`collectors/vk_reconcile`).
PENALTY_MARK = r"(?:пк|рк|пен|буллит|pk|rk|shootout)"
SERIES_IN_BRACKETS = re.compile(
    rf"[(\[]\s*(?:{PENALTY_MARK}\s*[:.\-]?\s*)?(\d{{1,2}})\s*[:\-–]\s*(\d{{1,2}})[^)\]]*[)\]]",
    re.IGNORECASE)
SERIES_AFTER_MARK = re.compile(
    rf"{PENALTY_MARK}\s*[:.\-]?\s*(\d{{1,2}})\s*[:\-–]\s*(\d{{1,2}})", re.IGNORECASE)
SERIES_BEFORE_MARK = re.compile(
    rf"(\d{{1,2}})\s*[:\-–]\s*(\d{{1,2}})\s*{PENALTY_MARK}", re.IGNORECASE)
SERIES_PATTERNS = (SERIES_IN_BRACKETS, SERIES_AFTER_MARK, SERIES_BEFORE_MARK)


def shootout_of(text, s1, s2):
    """Серия буллитов ноги, названная рядом с ничейным счётом: «4-4 (3-1)», «1:1 (4:3 PK)».

    Носитель приходит с `pk: false` даже там, где комментарий серию называет, — нога теряла
    исход и выглядела ничьей. Скобки смотрим только при равном счёте: после неравного там стоит
    пояснение или счёт другой ноги, а не доигровка. Та же конвенция, что в разборе ячейки счёта
    (`portal.player_records.parse_score_cell`): серия решает ничью, но не подменяет счёт.

    Порядок сторон здесь НЕ учитывается: функция говорит «серия названа», а чья она — решает
    `series_for_sides`. Признак буллитов от порядка не зависит, исход — зависит.
    """
    if s1 != s2 or not text:
        return None
    for line in str(text).splitlines():
        if not score_in_text(line, s1, s2):
            continue
        for pattern in SERIES_PATTERNS:
            found = pattern.search(line)
            if not found:
                continue
            series = int(found.group(1)), int(found.group(2))
            # Серия всегда с победителем. Равная пара — счёт самой ноги в скобках: ранний архив
            # пишет «E_not - WiSe (3 - 3)», и прежде такая строка получала признак буллитов.
            if series[0] != series[1]:
                return series
    return None


def side_spots(line, p1, p2):
    """Где в строке стоит каждая сторона — по любому написанию справочника; None — не узнана.

    Границы обязательны: короткий алиас «вор» складывается в «bop» и без них находился бы внутри
    «Дворовая лига» и внутри «BOP213», выдавая чужого игрока за сторону этой ноги.
    """
    folded = homoglyph_fold(line)
    spots = []
    for name in (p1, p2):
        canonical = clean_alias(name) or name
        variants = {canonical} | {alias for alias, nick in ALIAS_MAP.items() if nick == canonical}
        hits = []
        for variant in variants:
            found = re.search(rf"(?<!\w){re.escape(homoglyph_fold(variant))}(?!\w)", folded)
            if found:
                hits.append(found.start())
        if not hits:
            return None
        spots.append(min(hits))
    return tuple(spots)


def series_for_sides(text, s1, s2, p1, p2):
    """Серия буллитов ноги в порядке сторон базы: ``(очки p1, очки p2)`` или None.

    Комментарий пишет стороны вразнобой с базой («Mcfly- Dune 4-4 (5-6)» при первой стороне Dune),
    поэтому серия переворачивается по тому, чьё имя стоит в строке раньше. Порядок берётся у самой
    строки, а если она имён не несёт (Sportcup перечисляет ноги под шапкой «ectoPower vs Romix:») —
    у последней строки выше, где названы обе стороны. Когда сторону не узнаёт ни строка, ни шапка,
    серия не возвращается: угадывать победителя нельзя, нога остаётся ничьей и уходит в отчёт.
    """
    series = shootout_of(text, s1, s2)
    if not series:
        return None
    frame = None
    for line in str(text).splitlines():
        spots = side_spots(line, p1, p2)
        if spots:
            frame = spots
        if score_in_text(line, s1, s2) and shootout_of(line, s1, s2) == series:
            order = spots or frame
            if not order:
                return None
            return series if order[0] < order[1] else (series[1], series[0])
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
