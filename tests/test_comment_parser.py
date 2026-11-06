"""Разбор комментария темы: что является ногой, а что итогом, серией или образцом.

Сверка живёт из этих ног, и каждая лишняя нога — это ложное «расхождение счёта» в отчёте. Правила
выведены из текстов самих тем: регламент требует ничью доигрывать и писать итог доигровки в скобках
(«5-5 (1-0)» — золотой гол, «1-1 (4-3 пен)» — серия), а перечень ног в скобках значит, что счёт перед
скобкой — итог встречи, а не игра.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.vk_reconcile import legs_of, parse_comment, without_examples  # noqa: E402


def scores(text):
    return [item["scores"] for item in parse_comment(text)]


def test_example_block_is_not_a_result():
    """Блок «ПРИМЕР ВЫКЛАДЫВАНИЯ» шапки темы не даёт ног, а текст после блока остаётся."""
    post = ("Регламент: https://vk.cc/abc\n"
            "ПРИМЕР ВЫКЛАДЫВАНИЯ РЕЗУЛЬТАТОВ:\n"
            "ВЛ 1-й тур. Memori vs Centurion - 3:0, 8:5пен.\n"
            "Это означает, что Memori выиграл 1 матч в основное время\n"
            "*****\n"
            "Высшая лига, 4 тур.\nCenturion vs Memori - 1:6, 2:5.")
    assert scores(post) == [(1, 6), (2, 5)]
    assert "Memori vs Centurion - 3:0" not in without_examples(post)


def test_short_tour_header_does_not_end_the_example_block():
    """Строка «1 Тур.» без счёта — часть образца: блок кончается на первом осмысленном абзаце."""
    post = ("ПРИМЕР ВЫКЛАДЫВАНИЯ РЕЗУЛЬТАТОВ:\n1 Тур.\nВОР95 - Tymoschuk - 5:1\n"
            "Tymoschuk - BOP95 - 6:2\n\nСкачайте Raid Call и заходите в нашу группу")
    assert scores(post) == []


def test_single_score_in_brackets_belongs_to_the_previous_leg():
    """Одна счёт-пара в скобках — доигровка предыдущей ноги: золотой гол или пенальти."""
    assert legs_of("5-5 (1-0)") == [(5, 5)]
    assert legs_of("1-1(4-3 пен)") == [(1, 1)]
    assert legs_of("6-0, 4-4 (8-4)") == [(6, 0), (4, 4)]
    assert legs_of("9:8(PK)") == [(9, 8)]


def test_several_scores_in_brackets_are_the_legs_and_the_rest_is_the_tie():
    """Перечень ног в скобках важнее счёта снаружи: снаружи — итог встречи по ногам."""
    assert legs_of("3:5 (3:1, 4:2, 1:3, 0:2)") == [(3, 1), (4, 2), (1, 3), (0, 2)]
    assert legs_of("2:0 (5:0, 5:0)") == [(5, 0), (5, 0)]


def test_series_word_without_comma_is_not_a_second_leg():
    """Без запятой «PK 5:4» объясняет предыдущую ногу; с запятой — это уже вторая нога."""
    assert legs_of("6 - 6 PK 5:4") == [(6, 6)]
    assert legs_of("3:0, 8:5пен.") == [(3, 0), (8, 5)]
