"""Сезон 1: носитель обязан совпадать со снимками таблиц, а не жить своей жизнью.

Ранний чемпионат переносился из матрицы «строка × столбец», и в архиве оказывалась одна-две ноги
из четырёх: витрина печатала 144 игры там, где два листа согласованно дают 332. Чтобы это не
вернулось молча, проверка живёт в тестах, а не в памяти о том, как считали в прошлый раз.

Снимки листов (`data/gsheet_season1/`) лежат в репозитории, поэтому тестам не нужна сеть.
"""

import json
from collections import defaultdict

from collectors.build_season1_archive import (
    CARRIER,
    NOTES,
    TOURNAMENT,
    build_rows,
    calendar_legs,
    matrix_legs,
)

DIVISIONS = ("Кометы", "Метеоры")
COLUMNS = ("И", "В", "Н", "П", "Мз", "Мп", "О")


def carrier_rows():
    carrier = json.loads(CARRIER.read_text(encoding="utf-8"))
    return [row for row in carrier if row.get("tournament") == TOURNAMENT]


def test_matrix_recount_rebuilds_the_sheet_own_standings():
    """Разбор матрицы доказан только тогда, когда из ног снова собирается её же таблица.

    Итоговые колонки — независимое свидетельство: их лист считает по всем четырём играм пары, и
    сойтись они могут лишь если ноги взяты с правильной площадки и без пропусков.
    """
    for division in DIVISIONS:
        legs, standings = matrix_legs(division)
        tally = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])
        for (_, host, guest), (hg, ag) in legs.items():
            for nick, scored, missed in ((host, hg, ag), (guest, ag, hg)):
                total = tally[nick]
                total[0] += 1
                total[4] += scored
                total[5] += missed
                if scored > missed:
                    total[1] += 1
                    total[6] += 3
                elif scored == missed:
                    total[2] += 1
                    total[6] += 1
                else:
                    total[3] += 1
        recomputed = {p: tuple(tally[p]) for p in standings}
        wrong = {p: (standings[p], recomputed[p]) for p in standings
                 if recomputed[p] != standings[p]}
        assert not wrong, f"{division}: не сходятся {COLUMNS} у {sorted(wrong)}"


def test_carrier_holds_every_leg_both_sheets_agree_on():
    """Носитель = все ноги матрицы, подтверждённые календарём: ни лишней, ни потерянной."""
    notes = json.loads(NOTES.read_text(encoding="utf-8"))
    fresh, _ = build_rows(calendar_legs(), notes)
    current = carrier_rows()
    assert len(fresh) == len(current), (
        f"в носителе {len(current)} строк Сезона 1, листы дают {len(fresh)}")
    missing = [row for row in fresh if row not in current]
    extra = [row for row in current if row not in fresh]
    assert not missing and not extra, f"расхождение: нет в носителе {missing[:3]}, " \
                                      f"лишних {extra[:3]}"


def test_a_pair_plays_at_one_venue_per_tour():
    """В туре пара играет на одной площадке — на этом держится правило зеркальных дублей.

    `db/close_early_mirrors.py` прячет строку, если в туре у пары ровно две строки с
    перевёрнутыми сторонами и счётом. Если бы календарь ставил пару в один тур на две площадки,
    под правило могла попасть настоящая игра.
    """
    venues = defaultdict(set)
    for (host, guest), entries in calendar_legs().items():
        for _, tour, _, _, _ in entries:
            venues[(tuple(sorted((host, guest))), int(tour))].add((host, guest))
    split = {key: sorted(value) for key, value in venues.items() if len(value) > 1}
    assert not split, f"пары, играющие в одном туре на двух площадках: {list(split)[:5]}"
