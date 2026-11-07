"""Канонизация написаний: то, на чём держится «один человек — одна карточка».

`clean_alias` зовёт и импортёр, и путь правки (`set-players`), и сверка с ВК. Две его ловушки
зафиксированы здесь: незакрытая скобка (встречается в строках комментариев, где ник обрывается)
и написания, которые обязаны РАЗВЕСТИ, а не слить — «Palka Palych» и «PacnyTHuK» играли друг
против друга в одной встрече, и склейка ставит одного игрока в обе стороны.
"""

from portal.names import clean_alias, clean_tok_name


def test_unclosed_parenthesis_returns_instead_of_recurising():
    """Хвост команды снимается рекурсией: если скобка не закрылась, повторный вызов — это цикл."""
    assert clean_alias("Rock (") == "Rock ("
    assert clean_alias("Kubik (3 тур") == "Kubik (3 тур"


def test_team_suffix_is_stripped_and_alias_wins_after():
    assert clean_alias("Ric25 (Кометы)") == "Ric25"
    assert clean_alias("палка палыч") == "Palka Palych"


def test_lookalike_players_stay_apart():
    """Два разных человека, чьи ники путают гомоглифы и контекст: склейка = фальшивая карточка."""
    assert clean_alias("Palka Palych") == "Palka Palych"
    assert clean_alias("PacnyTHuK") == "PacnyTHuK"
    assert clean_alias("распутник") == "PacnyTHuK"


def test_homoglyph_spelling_of_one_id_reaches_the_same_card():
    """Кириллическая «С» не имеет права рождать второго человека.

    У id85380069 в темах четыре написания: «Centurion», «CentZloy», «Farmazon» и «СentZloy» с
    кириллической «С» — 93 упоминания против 655 латинских. Пока справочник знал только
    латинское, последние строки доходили до базы отдельной карточкой, и история игрока
    делилась пополам.
    """
    for spelling in ("CentZloy", "centzloy", "СentZloy", "Сentzloy", "Сenturion"):
        assert clean_alias(spelling) == "Centurion", spelling


def test_valera_is_buts_and_not_centurion():
    """«Валера» — id203194115: тот же профиль, что «LiptOn» и «Буц» ([id203194115|Валера], тема 31898219).

    В справочнике это написание вело в Centurion (id85380069), и разбор пенальти обходил его
    локальной таблицей. Оставлять ловушку нельзя: встреча «ВОР95 vs Валера» из Сезона 4
    при первом же занесении записалась бы чужому человеку.
    """
    for spelling in ("Валера", "валера", "Valera"):
        assert clean_alias(spelling) == "Буц", spelling
    assert clean_alias("LiptOn") == "Буц"


def test_bracket_of_a_nick_survives_the_decoration_strip():
    """Скобка ника — часть ника, а не разметка: «RVD (МГБ)» терял правый край.

    `clean_tok_name` срезал её одиночным `strip("()")`, и написание «(МГБ)» распадалось в
    «(мгб»: архивный указатель с таким ключом ничего не находил, и игры этого игрока
    оставались без ссылки и без текста источника (Сезоны 2–7, 23 строки).
    """
    assert clean_tok_name("RVD (МГБ)") == "rvd (мгб)"
    assert clean_tok_name("*RVD (МГБ)*") == "rvd (мгб)"
    assert clean_tok_name("(Ric25)") == "ric25"
