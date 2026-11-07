"""Архивный указатель комментариев: какими написаниями строка находит свой комментарий.

Ключи `vk_match_sources_lookup.json` записаны так, как ник написал игрок, — со строчных букв и
в той смеси латиницы и кириллицы, которая попалась в комментарии. Носитель и база помнят свою
каноническую форму, и без складки гомоглифов такие строки оставались бы без ссылки и без текста:
проверять игру глазами было бы нечем. Точное совпадение ключа при этом остаётся первым — иначе
строка получила бы другой комментарий там, где всегда получала нужный.

Написания собраны из кодов букв: на глаз кириллическая «х» и латинская не различаются, а
различие здесь — весь предмет проверки.
"""

from portal.vk_sources import enrich_vk_source, folded_view

CYR_X = "х"  # кириллическая «х» — так ник записан в архиве
ARCHIVE_NAME = CYR_X + "yz"
LATIN_NAME = "xyz"  # то же начертание латиницей — так его помнит база

ARCHIVE_ENTRY = (f"34973011|a1|{ARCHIVE_NAME}|0|6",
                 {"vk_url": "https://vk.ru/topic-66162180_34973011?offset=40#post10109",
                  "text": "a1 vs xyz - 0:6"})
EXACT_ENTRY = (f"34973011|a1|{LATIN_NAME}|0|6",
               {"vk_url": "https://vk.ru/точное-совпадение", "text": "ключ совпал буквально"})

ONLY_ARCHIVE = dict([ARCHIVE_ENTRY])
ROW = {"season": "Season 4", "p1": "a1", "p2": LATIN_NAME}


def test_folded_spelling_finds_the_comment():
    """Точного ключа нет, и складка доводит строку до комментария: ссылка и текст появляются."""
    row = enrich_vk_source({**ROW, "s1": 0, "s2": 6}, ONLY_ARCHIVE)
    assert row["vk_url"] == ARCHIVE_ENTRY[1]["vk_url"]
    assert row["vk_text"] == "a1 vs xyz - 0:6"


def test_swapped_score_reaches_the_same_comment():
    row = enrich_vk_source({**ROW, "s1": 6, "s2": 0}, ONLY_ARCHIVE)
    assert row["vk_url"] == ARCHIVE_ENTRY[1]["vk_url"]


def test_exact_key_wins_over_the_folded_copy():
    """Складка — второй шаг, а не первый: найденное точно не имеет права переехать."""
    row = enrich_vk_source({**ROW, "s1": 0, "s2": 6}, dict([EXACT_ENTRY, ARCHIVE_ENTRY]))
    assert row["vk_url"] == EXACT_ENTRY[1]["vk_url"]


def test_folded_view_collapses_spellings_of_one_player():
    """Два написания одного игрока на одном месте — одна ветка; остаётся первая запись файла."""
    view = folded_view(dict([ARCHIVE_ENTRY, EXACT_ENTRY]))
    assert len(view) == 1
    assert view[f"34973011|a1|{LATIN_NAME}|0|6"] is ARCHIVE_ENTRY[1]
