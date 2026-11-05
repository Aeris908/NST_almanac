"""Канонизация написаний: то, на чём держится «один человек — одна карточка».

`clean_alias` зовёт и импортёр, и путь правки (`set-players`), и сверка с ВК. Две его ловушки
зафиксированы здесь: незакрытая скобка (встречается в строках комментариев, где ник обрывается)
и написания, которые обязаны РАЗВЕСТИ, а не слить — «Palka Palych» и «PacnyTHuK» играли друг
против друга в одной встрече, и склейка ставит одного игрока в обе стороны.
"""

from portal.names import clean_alias


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
