"""Правила, которые снимают строку темы с расхождений, не трогая базу.

Сверка сравнивает комментарий и строку, но источник успевает сам себя отменить: в той же теме
появляется переигровка или итог серии. Если этого не видеть, отчёт год за годом показывает
выдуманные конфликты, а человек по ним правит то, что и так верно.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.vk_reconcile import (  # noqa: E402
    REPLAY_MARK,
    namesake_season,
    season_owner,
    series_total,
)

# Архивная карта обсуждений: у каждого номерного сезона лиги уже есть своё обсуждение.
LEAGUE_MAP = {
    "32593813": ("сезон", "1", "goal3"),
    "33967365": ("сезон", "3", "goal3"),
    "34973011": ("сезон", "4", "goal3"),
    "51265748": ("сольный", "1", "goal3"),
}


def test_a_season_number_owned_by_another_topic_is_not_the_championship():
    """«Soccer (сезон 3)» 2023 года — перевыпуск рома Soccer (JU) на сетке challonge.

    Чемпионат 2016-го живёт в теме 33967365, и сверка не вправе отдавать строки первой темы
    второй: тогда ноги чужого соревнования каждый год ложатся в раздел «счёт расходится» против
    лиги, где этих игроков нет.
    """
    owner = season_owner(LEAGUE_MAP)
    assert namesake_season(("сезон", "3", "goal3"), "49948732", owner) == "33967365"
    assert namesake_season(("сезон", "4", "goal3"), "50374687", owner) == "34973011"


def test_the_owning_topic_is_never_a_namesake():
    """Правило ловит только претендента: владелица номера сверяется с собой, как и раньше."""
    assert not namesake_season(("сезон", "3", "goal3"), "33967365", season_owner(LEAGUE_MAP))


def test_the_rule_touches_nothing_but_numbered_league_seasons():
    """Формат без номера, кубок, сольник и незанятый сезон под правило не попадают."""
    owner = season_owner(LEAGUE_MAP)
    assert not namesake_season(("сезон", "", "goal3"), "49948732", owner)
    assert not namesake_season(("кубок", "4", "goal3"), "1", owner)
    assert not namesake_season(("сольный", "1", "goal3"), "9", owner)
    assert not namesake_season(("сезон", "7", "goal3"), "1", owner)


def pair(left, right):
    """Стороны так, как их отдаёт разбор комментария: порядок левой и правой стороны сохранён."""
    return (tuple(sorted(left)), tuple(sorted(right)))


def row(p1, p2, s1, s2, **kw):
    """Строка базы в том виде, как её отдаёт `load_base`: стороны — кортежи ников, дубли помечены."""
    return {"scores": (s1, s2),
            "sides": (tuple(sorted(p1.split(" & "))), tuple(sorted(p2.split(" & ")))),
            "duplicate_of": kw.get("dup"), "hidden_by": kw.get("hidden")}


def test_replay_marker_reads_the_words_the_topic_uses():
    """Слово переигровки и вопрос «в итоге?» — те же формулировки, что в темах Сезонов 8, 9 и 1."""
    for line in ("ПЕРЕИГРОВКА!!!\nТур 2 Высшая лига\nRic25 vs leonudomlya 0 - 2",
                 "в первом матче были не выставлены быстрые боты, нужно будет переиграть этот матч",
                 "Romario - yoxter 3-6 что с этим матчем в итоге?",
                 "тур 3, после переигровки одного из матчей:\nRomario - yoxter 3:9"):
        assert REPLAY_MARK.search(line), line


def test_replay_marker_stays_quiet_on_an_ordinary_report():
    """Обычный отчёт тура не называется переигровкой: правило не должно глотать спорные счета."""
    for line in ("Тур 2 Высшая лига Аргентина - Трава / Земля\nRic25 vs leonudomlya 1 -4",
                 "средняя, тур 1\nYuliy_Cezar vs yoxter 1:1 (ПК 5:3)"):
        assert not REPLAY_MARK.search(line), line


def test_series_score_is_recognised_from_its_own_legs():
    """«3 - 0» над тремя выигранными играми — итог серии, а не четвёртая игра (коммент 32977)."""
    legs = [row("Yuliy_Cezar", "Ryumaru", 2, 0), row("Yuliy_Cezar", "Ryumaru", 5, 2),
            row("Yuliy_Cezar", "Ryumaru", 2, 1)]
    assert series_total(pair(("Yuliy_Cezar",), ("Ryumaru",)), (3, 0), legs)


def test_series_score_in_the_other_orientation_is_the_mirror():
    """Та же серия, названная наоборот, читается так же: порядок сторон берётся из строки темы."""
    legs = [row("Yuliy_Cezar", "Ryumaru", 2, 0), row("Yuliy_Cezar", "Ryumaru", 5, 2),
            row("Yuliy_Cezar", "Ryumaru", 2, 1)]
    assert series_total(pair(("Ryumaru",), ("Yuliy_Cezar",)), (0, 3), legs)


def test_a_two_sided_form_is_read_by_members_not_by_letters():
    """Форма 2×2: сторона — состав, и сравнивается она с составом, а не с одной буквой ника."""
    legs = [row("lenin1st & ectoPower", "Aoshi & Aeris", 3, 1),
            row("lenin1st & ectoPower", "Aoshi & Aeris", 2, 0)]
    sides = pair(("lenin1st", "ectoPower"), ("Aoshi", "Aeris"))
    assert series_total(sides, (2, 0), legs)


def test_lost_single_game_is_not_a_series():
    """Одна нога со счётом 3:1 итогом серии быть не может: 3+1 не равно числу игр."""
    assert not series_total(pair(("Jamlight",), ("Taeda",)), (3, 1),
                            [row("Jamlight", "Taeda", 2, 0)])


def test_series_with_a_drawn_leg_is_not_claimed():
    """Если одна из игр серии ничейна, счёт побед по ногам не восстановить — спор остаётся."""
    legs = [row("Jamlight", "Taeda", 2, 0), row("Jamlight", "Taeda", 1, 1)]
    assert not series_total(pair(("Jamlight",), ("Taeda",)), (1, 1), legs)


def test_twin_rows_of_one_game_are_not_counted_twice():
    """Дубль страницы не удваивает число ног: итог серии считается по независимым строкам."""
    legs = [row("Yuliy_Cezar", "Ryumaru", 2, 0), row("Yuliy_Cezar", "Ryumaru", 5, 2),
            row("Yuliy_Cezar", "Ryumaru", 2, 1),
            row("Yuliy_Cezar", "Ryumaru", 2, 0, dup=1), row("Yuliy_Cezar", "Ryumaru", 5, 2, dup=1)]
    assert series_total(pair(("Yuliy_Cezar",), ("Ryumaru",)), (3, 0), legs)
