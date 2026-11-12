"""Отказы важнее разрешений: правка, которая прошла молча и разъела архив, стоит дороже, чем
неудобный диалог. Здесь — ровно те границы, на которых редактор обязан сказать «нет» и объяснить
почему, а не положить в базу строку, на которой потом споткнётся валидатор.

Текст отказа сверяется намеренно: лоровед читает именно его, и «IntegrityError: constraint
failed» ему не скажет ни о чём.
"""

import pytest
from db import api, edit
from support import SCOREFUL, SCORELESS, SINGLES, WITH_PAIR, card, rosters, sides


def test_date_must_be_a_real_calendar_date(con, find):
    """Форма «ГГГГ-ММ-ДД» сама по себе пропускает 45 июня: дату проверяет календарь."""
    match_id = find("select id from matches where hidden_by is null limit 1", what="строка матча")
    for wrong in ("2024-13-45", "15.06.2024", "июнь 2024", "24-06-15", "2024-6"):
        with pytest.raises(edit.EditError) as error:
            edit.set_date(con, match_id, "tester", played_on=wrong)
        assert "ГГГГ" in str(error.value)


def test_set_place_needs_at_least_one_place(con, find):
    match_id = find("select id from matches where hidden_by is null limit 1", what="строка матча")
    with pytest.raises(edit.EditError) as error:
        edit.set_place(con, match_id, "tester")
    assert "--tour" in str(error.value)


def test_phase_must_be_known_and_named(con, find):
    match_id = find("select id from matches where hidden_by is null limit 1", what="строка матча")
    with pytest.raises(edit.EditError) as error:
        edit.set_phase(con, match_id, "tester", phase="shootout")
    assert "фаза бывает" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        edit.set_phase(con, match_id, "tester")
    assert "phase" in str(error.value)


@pytest.mark.parametrize(("s1", "s2", "outcome_a", "outcome_b", "phase", "expected"), [
    (3, 0, "win", "loss", "penalties", None),
    (3, 0, "draw", "draw", "penalties", "исходы не следуют за счётом"),
    (3, 0, "win", "none", "overtime", "исходы не следуют за счётом"),
    (2, 2, "win", "loss", "overtime", None),
    (2, 2, "draw", "draw", "penalties", None),
    (2, 2, "none", "none", "penalties", "при равном счёте исходы обязаны быть ничьей"),
    (3, 0, "draw", "draw", "regular", None),
    (None, None, "none", "none", "penalties", None),
])
def test_phase_problem_mirrors_the_validator(s1, s2, outcome_a, outcome_b, phase, expected):
    """`phase_problem` повторяет инварианты `db/validate.py`: отказ обязан приходить здесь, а не
    падением сборки. Равный счёт прощается не-regular-этапу — его решает серия."""
    result = edit.phase_problem(s1, s2, outcome_a, outcome_b, phase)
    if expected is None:
        assert result is None
    else:
        assert result and expected in result


def test_set_phase_refuses_a_row_whose_outcomes_lie(con, find):
    """Строка берётся с числами и НЕ в фазе буллитов: правка фазы, равной текущей, ничего не
    сверяет — она ничего не меняет. Такие строки появились в базе сами собой, когда часть
    доигровок Сезонов 8-9 перестала быть овертаймом."""
    match_id = find("""select m.id from matches m
        join match_sides a on a.match_id = m.id and a.side_index = 0
        join match_sides b on b.match_id = m.id and b.side_index = 1
        where m.hidden_by is null and a.score is not null and b.score is not null
          and a.score > b.score and m.phase <> 'penalties' limit 1""",
                    what="матч с числами не в фазе буллитов")
    con.execute("update match_sides set outcome = 'none' where match_id = ? and side_index = 1",
                (match_id,))
    con.commit()
    with pytest.raises(edit.EditError) as error:
        edit.set_phase(con, match_id, "tester", phase="penalties")
    assert "не сходится с этой партией" in str(error.value)


def test_provenance_refuses_a_key_someone_else_holds(con, find):
    """Ключ источника — опознавательный знак строки для импортёра: два носителя с одним ключом
    слились бы в одну строку, и правка обязана это увидеть до записи."""
    holder, other = find("""select k.id, m.id from matches m
        join matches k on k.source = m.source and k.source_ref is not null and k.hidden_by is null
        where m.source_ref is null and m.hidden_by is null and k.id <> m.id limit 1""",
        what="носитель со строкой с ключом и строкой без ключа")
    with pytest.raises(edit.EditError) as error:
        edit.set_provenance(con, other, "tester", source_ref=card(con, holder)["source_ref"])
    assert f"уже носит строка #{holder}" in str(error.value)


def test_provenance_needs_a_field(con, find):
    match_id = find("select id from matches where hidden_by is null limit 1", what="строка матча")
    with pytest.raises(edit.EditError) as error:
        edit.set_provenance(con, match_id, "tester")
    assert "происхождения" in str(error.value)


def test_rename_refuses_a_slug_another_player_carries(con, find):
    """Один slug на двух игроков — это две карточки на одну ссылку в адресе."""
    owner = find("""select nick from players where nick <> upper(nick)
        and slug = lower(replace(nick, ' ', '-')) limit 1""", what="игрок с латинским ником")
    victim = find("select id from players where nick <> ? limit 1", (owner,), what="другой игрок")
    with pytest.raises(edit.EditError) as error:
        edit.rename_player(con, victim, owner.upper(), "tester")
    assert "уже носит" in str(error.value)


def test_rename_refuses_empty_nick_and_unknown_player(con):
    with pytest.raises(edit.EditError):
        edit.rename_player(con, 1, "   ", "tester")
    with pytest.raises(edit.EditError) as error:
        edit.rename_player(con, 10_000_000, "Кто-то", "tester")
    assert "в базе нет" in str(error.value)


def test_merge_refuses_rivals_and_itself(con, find):
    """Слияние тех, кто сходился в одной партии, посадило бы игрока по обе стороны игры."""
    keep, drop = find("""select spa.player_id, spb.player_id from match_sides sa
        join side_players spa on spa.side_id = sa.id
        join match_sides sb on sb.match_id = sa.match_id and sb.side_index <> sa.side_index
        join side_players spb on spb.side_id = sb.id
        where spa.player_id <> spb.player_id limit 1""", what="двое, игравшие друг против друга")
    with pytest.raises(edit.EditError) as error:
        edit.merge_player(con, keep, drop, "tester")
    assert "уже играл против" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        edit.merge_player(con, keep, keep, "tester")
    assert "саму с собой" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        edit.merge_player(con, keep, 10_000_000, "tester")
    assert "должны существовать" in str(error.value)


def test_drop_match_refuses_a_row_another_points_at(con, find):
    match_id = find(WITH_PAIR, what="строка со своей копией")
    pair = edit.pair_ids(con, match_id)
    twin = next(current for current in pair if current != match_id)
    third = find("""select id from matches where hidden_by is null
        and id not in ({}) limit 1""".format(", ".join(str(x) for x in pair)),
        what="третья строка матча")
    con.execute("update matches set duplicate_of = ? where id = ?", (twin, third))
    con.commit()
    with pytest.raises(edit.EditError) as error:
        edit.drop_match(con, match_id, "tester")
    assert "сначала разбери дубли" in str(error.value)


def test_drop_tournament_refuses_while_games_remain(con, find):
    doc_key, games = find("""select d.doc_key, count(m.id) from tournament_docs d
        join matches m on m.doc_id = d.id group by d.id having count(m.id) > 0 limit 1""",
        what="турнир с играми")
    with pytest.raises(edit.EditError) as error:
        edit.drop_tournament(con, doc_key, "tester")
    assert f"ещё {games} игр" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        edit.drop_tournament(con, "net_takogo_doc", "tester")
    assert "в базе нет" in str(error.value)


def test_add_match_refuses_a_game_that_already_exists(con, find):
    """Дубль отсекается до вставки: правьте существующую строку, а не заводите вторую."""
    doc_key, tour, nick_a, nick_b, s1, s2 = find("""select d.doc_key, m.tour, pa.nick, pb.nick,
            a.score, b.score
        from matches m
        join tournament_docs d on d.id = m.doc_id
        join match_sides a on a.match_id = m.id and a.side_index = 0
        join match_sides b on b.match_id = m.id and b.side_index = 1
        join side_players spa on spa.side_id = a.id join players pa on pa.id = spa.player_id
        join side_players spb on spb.side_id = b.id join players pb on pb.id = spb.player_id
        where m.hidden_by is null and d.kind = 'special' and a.score is not null
          and (select count(*) from side_players where side_id = a.id) = 1
          and (select count(*) from side_players where side_id = b.id) = 1 limit 1""",
        what="игра спецтурнира 1×1")
    with pytest.raises(edit.EditError) as error:
        edit.add_match(con, {"doc_key": doc_key, "tour": tour, "sides": [nick_a, nick_b],
                             "s1": s1, "s2": s2}, "tester")
    assert "уже есть в базе" in str(error.value)


@pytest.mark.parametrize("spec, expected", [
    ({"doc_key": "net_takogo", "sides": ["А", "Б"]}, "в базе нет"),
    ({"sides": ["А"], "season": "Season 9"}, "обе стороны"),
    ({"sides": ["А", "Б"]}, "doc_key"),
    ({"season": "Season 9", "sides": ["А", "Б"], "s1": -1, "s2": 2}, "неотрицательное"),
    ({"season": "Season 9", "sides": ["А", "Б"], "phase": "shootout"}, "неизвестная фаза"),
])
def test_add_match_refuses_nonsense(con, spec, expected):
    with pytest.raises(edit.EditError) as error:
        edit.add_match(con, spec, "tester")
    assert expected in str(error.value)


@pytest.mark.parametrize("spec, expected", [
    ({"doc_key": "", "title": "Кубок"}, "нужны `doc_key` и `title`"),
    ({"doc_key": "x_1", "title": "  "}, "нужны `doc_key` и `title`"),
    ({"doc_key": "x_1", "title": "Кубок", "kind": "league"}, "новый турнир бывает"),
])
def test_add_tournament_refuses_nonsense(con, spec, expected):
    with pytest.raises(edit.EditError) as error:
        edit.add_tournament(con, spec, "tester")
    assert expected in str(error.value)


def test_add_tournament_refuses_a_key_already_taken(con, find):
    doc_key = find("select doc_key from tournament_docs limit 1", what="документ турнира")
    with pytest.raises(edit.EditError) as error:
        edit.add_tournament(con, {"doc_key": doc_key, "title": "Второй раз"}, "tester")
    assert "уже заведён" in str(error.value)


def test_set_doc_refuses_a_frame_without_the_game_key(con, find):
    """Сотруть `matches` из рамки — и турнир осиротеет: читатель навешивает игры по этому ключу."""
    doc_key = find("select doc_key from tournament_docs where kind = 'special' limit 1",
                   what="документ турнира")
    with pytest.raises(edit.EditError) as error:
        edit.set_doc(con, doc_key, "tester", frame={"title": "Без игр"})
    assert "игры турнира исчезнут" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        edit.set_doc(con, "net_takogo", "tester", title="Х")
    assert "в базе нет" in str(error.value)


def test_set_players_refuses_empty_sides_and_same_twice(con, find):
    match_id = find(SCOREFUL, what="матч с числами")
    for wrong in ([], ["Один"], ["Один", ""], ["Один", " & "]):
        with pytest.raises(edit.EditError) as error:
            edit.set_players(con, match_id, wrong, "tester")
        assert "обе стороны" in str(error.value)
    nick = find("select nick from players limit 1", what="ник игрока")
    with pytest.raises(edit.EditError) as error:
        edit.set_players(con, match_id, [f"{nick} & {nick}", "Другой"], "tester")
    assert "назван на одной стороне дважды" in str(error.value)


def test_set_players_refuses_a_nick_whose_slug_is_taken(con, find):
    """Новое написание не должно рождать вторую карточку на уже занятый адрес."""
    match_id, nick_a, _ = find(SINGLES.format(where="m.doc_id is null"),
                               what="матч каталога 1×1")
    for (nick,) in con.execute("select nick from players where instr(nick, '_') > 0 order by id"):
        variant = nick.replace("_", "-")
        if con.execute("select 1 from players where nick = ?", (variant,)).fetchone():
            continue
        if edit.canonical_roster(variant) != [variant]:
            continue  # справочник сворачивает написание в существующую карточку — не наш случай
        break
    else:
        pytest.skip("в базе нет написания, которое давало бы чужой slug")
    with pytest.raises(edit.EditError) as error:
        edit.set_players(con, match_id, [nick_a, variant], "tester")
    assert "тот же slug" in str(error.value)


def test_score_and_roster_refuse_a_match_with_three_sides(con, find):
    """Баттл (N сторон) счёт править нельзя: `sides_of` возвращает стороны, а не игроков."""
    match_id = find(SCOREFUL, what="матч с числами")
    con.execute("insert into match_sides(match_id, side_index, outcome, score)"
                " values (?, 2, 'none', 0)", (match_id,))
    con.commit()
    with pytest.raises(edit.EditError) as error:
        edit.set_score(con, match_id, 2, 1, "tester")
    assert "сторон" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        edit.set_players(con, match_id, ["Один", "Два"], "tester")
    assert "сторон" in str(error.value)


@pytest.mark.parametrize(("links", "expected"), [
    ([["note", "https://example.com"]], "ссылка бывает одной из"),
    ([["vk_post", "vk.com/x"]], "не похоже на адрес"),
    ([["vk_post", "https://example.com"], ["vk_post", "https://example.com"]], "одинаковые ссылки"),
])
def test_links_refusals(con, find, links, expected):
    match_id = find("select id from matches where hidden_by is null limit 1", what="строка матча")
    with pytest.raises(edit.EditError) as error:
        edit.set_source(con, match_id, "tester", links=links)
    assert expected in str(error.value)


def test_unknown_match_id_refuses_instead_of_silence(con):
    """Id строк меняет каждая пересборка: молчаливое «уже так» обмануло бы редактора."""
    for call in (lambda: edit.pair_ids(con, 10_000_000),
                 lambda: edit.set_score(con, 10_000_000, 1, 0, "tester"),
                 lambda: edit.set_place(con, 10_000_000, "tester", tour="X"),
                 lambda: edit.set_date(con, 10_000_000, "tester", played_on="2024"),
                 lambda: edit.set_phase(con, 10_000_000, "tester", phase="overtime"),
                 lambda: edit.set_provenance(con, 10_000_000, "tester", source_text="X"),
                 lambda: edit.drop_match(con, 10_000_000, "tester")):
        with pytest.raises(edit.EditError) as error:
            call()
        assert "откройте строку заново" in str(error.value)


def test_rating_refuses_rows_that_are_not_1x1_or_have_no_year(con, find):
    """Отказ по причине, а не молчание: «не считается» без объяснения читается как баг витрины."""
    two_by_two = find("""select m.id from matches m
        join match_sides a on a.match_id = m.id and a.side_index = 0
        where m.hidden_by is null and (select count(*) from side_players where side_id = a.id) > 1
        limit 1""", what="пара 2×2")
    with pytest.raises(edit.EditError) as error:
        edit.set_rating(con, two_by_two, True, "tester")
    assert "1×1" in str(error.value)

    no_score = find(SCORELESS, what="строка без счёта")
    with pytest.raises(edit.EditError) as error:
        edit.set_rating(con, no_score, True, "tester")
    assert "числового счёта" in str(error.value)


def test_rate_scope_needs_exactly_one_scope(con, find):
    season = find("select distinct season from tournaments limit 1", what="сезон")
    with pytest.raises(edit.EditError) as error:
        edit.set_rating_scope(con, True, "tester")
    assert "что-то одно" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        edit.set_rating_scope(con, True, "tester", season=season, doc_key="x")
    assert "что-то одно" in str(error.value)


def test_undo_refuses_unknown_and_reverted_entry(con, find):
    with pytest.raises(edit.EditError) as error:
        edit.undo(con, "424242")
    assert "в журнале нет" in str(error.value)

    match_id = find(SCOREFUL, what="матч с числами")
    result = edit.set_score(con, match_id, 1, 0, "tester")
    entry = result["journal"][0]
    edit.undo(con, str(entry))
    with pytest.raises(edit.EditError) as error:
        edit.undo(con, str(entry))
    assert "уже отменена" in str(error.value)


def test_undo_last_on_a_clean_journal_is_harmless(con):
    con.execute("delete from corrections")  # только копия базы этого теста
    con.commit()
    assert edit.undo(con, "last")["entries"] == []


def test_two_operations_do_not_revert_together(con, find):
    """`corrections.op` — метка операции: без неё два изменения в одну секунду откатывались бы
    одним `undo last`, и человек терял бы правку, которую не просил отменять."""
    baseline=con.execute("select count(*) from corrections where reverted_at is null").fetchone()[0]
    first = find(SCOREFUL, what="матч с числами")
    second = find("""select id from matches where id <> ? and hidden_by is null
        and row_set <> 'pool' limit 1""", (first,), what="второй матч")
    was_second = sides(con, second)[0]["score"]
    one = edit.set_score(con, first, 2, 1, "tester")
    two = edit.set_score(con, second, 3, 0, "tester")
    assert one["op"] != two["op"]

    edit.undo(con, "last")
    assert sides(con, second)[0]["score"] == was_second, "откат не вернул счёт второй игры"
    assert sides(con, first)[0]["score"] == 2, "откат второй операции съел первую"
    assert con.execute("select count(*) from corrections where reverted_at is null").fetchone()[0] \
        == baseline+len(one["journal"])


def test_undo_of_one_field_leaves_its_pair(con, find):
    """Откат по id записи возвращает ровно одно поле — задокументированная ловушка: `nick`
    вернётся, `slug` нет. Целиком операцию откатывает `undo last`."""
    from db.build_db import slugify

    player_id, nick, slug = find(
        "select id, nick, slug from players where nick <> '' order by id limit 1", what="игрок")
    new_nick = f"{nick} Тест"
    result = edit.rename_player(con, player_id, new_nick, "tester")
    assert len(result["journal"]) == 2

    def now():
        return tuple(con.execute("select nick, slug from players where id = ?",
                                 (player_id,)).fetchone())

    edit.undo(con, str(result["journal"][0]))
    assert now() == (nick, slugify(new_nick)), "частичный откат вернул бы оба поля — тогда `last` не нужен"
    edit.undo(con, "last")
    assert now() == (nick, slug)


def test_manual_flag_survives_until_the_last_edit_is_reverted(con, find):
    """`manual` — защита строки от импортёра: он спадает, только когда действующих правок на всей
    связке не осталось (и правка происхождения касается одной строки, а флаг ставит обеим)."""
    match_id = find(WITH_PAIR, what="строка со своей копией в пуле")
    pair = edit.pair_ids(con, match_id)
    edit.set_provenance(con, match_id, "tester", source_text="сказано человеком")
    edit.set_date(con, match_id, "tester", played_on="2024-06")
    assert all(card(con, current)["manual"] == 1 for current in pair)
    edit.undo(con, "last")
    assert all(card(con, current)["manual"] == 1 for current in pair), \
        "флаг снят, хотя на связке висит другая правка"
    edit.undo(con, "last")
    assert all(card(con, current)["manual"] == 0 for current in pair)
    assert set(rosters(con, match_id)) == {0, 1}


# Матч с числами из другой связки: его правка остаётся применённой, когда откатывают первую.
OUTSIDE_PAIR = """select m.id from matches m
    join match_sides a on a.match_id = m.id and a.side_index = 0
    join match_sides b on b.match_id = m.id and b.side_index = 1
    where m.hidden_by is null and a.score is not null and b.score is not null
      and not exists (select 1 from matches p where p.id in ({marks})
          and (p.id = m.id or p.duplicate_of = m.id or p.hidden_by = m.id
                or m.duplicate_of = p.id or m.hidden_by = p.id))
    limit 1"""


def another_match(con, find, linked):
    """Строка игры, чья связка не пересекается с данной: две правки не задевают друг друга."""
    marks = ", ".join("?" * len(linked))
    return find(OUTSIDE_PAIR.format(marks=marks), tuple(linked), what="матч из другой связки")


def test_undo_by_label_reverts_the_older_operation_whole(con, find, fingerprint, unchanged):
    """`undo op:<метка>` откатывает операцию целиком, какой бы старой она ни была: возвращаются все
    её поля, а правка, легшая поверх, остаётся применённой.

    Без метки старую операцию пришлось бы откатывать по одной записи, и база ездила бы с
    половинчатой правкой: дата вернулась, а точность даты осталась новой.
    """
    baseline=con.execute("select count(*) from corrections where reverted_at is null").fetchone()[0]
    first = find(SCOREFUL, what="матч с числами")
    linked = edit.pair_ids(con, first)
    second = another_match(con, find, linked)
    was = {current: (card(con, current)["played_on"], card(con, current)["date_precision"])
           for current in linked}
    before = fingerprint()

    one = edit.set_date(con, first, "tester", played_on="2024-06-15")
    two = edit.set_score(con, second, 3, 0, "tester")
    result = edit.undo(con, f"op:{one['op']}")

    assert len(result["entries"]) == len(one["journal"]), "откат по метке вернул не все поля"
    assert {current: (card(con, current)["played_on"], card(con, current)["date_precision"])
            for current in linked} == was, "правка даты вернулась не целиком"
    assert all(card(con, current)["manual"] == 0 for current in linked), \
        "флаг снят с одной строки — связка осталась ручной"
    live = con.execute("select count(*) from corrections where reverted_at is null").fetchone()[0]
    assert live == baseline+len(two["journal"]), "откат старой операции тронул записи новой"
    assert (sides(con, second)[0]["score"], sides(con, second)[1]["score"]) == (3, 0), \
        "откат старой операции съел правку, сделанную поверх"
    assert card(con, second)["manual"] == 1

    # `last` от новой ветки не меняется: последней остаётся живая операция, и после её отката база
    # сходится к срезу до обеих правок.
    edit.undo(con, "last")
    unchanged(fingerprint(), before)


def test_undo_by_label_refuses_an_unknown_operation(con, find):
    match_id = find(SCOREFUL, what="матч с числами")
    edit.set_date(con, match_id, "tester", played_on="2024")
    for wrong in ("op:000000000000", "op:", "op:<метка>", "op: last"):
        with pytest.raises(edit.EditError) as error:
            edit.undo(con, wrong)
        assert "в журнале нет" in str(error.value)


def test_undo_by_label_refuses_an_operation_already_reverted(con, find):
    """Повторный откат по той же метке отказывает: действующих записей у операции не осталось, а
    молчаливый «ничего не отменено» человек прочитал бы как успех."""
    baseline={r[0] for r in con.execute("select id from corrections where reverted_at is null")}
    match_id = find(SCOREFUL, what="матч с числами")
    result = edit.set_date(con, match_id, "tester", played_on="2024-06")
    edit.undo(con, f"op:{result['op']}")
    with pytest.raises(edit.EditError) as error:
        edit.undo(con, f"op:{result['op']}")
    assert "уже отменена" in str(error.value)
    assert {r[0] for r in con.execute("select id from corrections where reverted_at is null")} == baseline


def test_journal_carries_the_operation_label_and_its_live_count(con, find, db_path):
    """Панель отката видит операцию из журнала: `op` — метка, `op_live` — сколько её записей ещё
    действует. По ним и решается, есть ли что откатывать целиком, когда поверх легла другая правка."""
    first = find(SCOREFUL, what="матч с числами")
    linked = edit.pair_ids(con, first)
    second = another_match(con, find, linked)
    one = edit.set_date(con, first, "tester", played_on="2024-06-15")
    two = edit.set_score(con, second, 4, 1, "tester")

    def journal():
        return {item["id"]: item for item in api.journal_entries(limit=50, db_path=db_path)}

    rows = journal()
    for entries, label in ((one["journal"], one["op"]), (two["journal"], two["op"])):
        assert all(rows[item]["op"] == label for item in entries), "журнал не отдаёт метку операции"
        assert all(rows[item]["op_live"] == len(entries) for item in entries)

    edit.undo(con, f"op:{one['op']}")
    rows = journal()
    assert all(rows[item]["op"] == one["op"] for item in one["journal"]), "метка исчезла с отменой"
    assert all(rows[item]["op_live"] == 0 for item in one["journal"]), "откат оставил запись живой"
    assert all(rows[item]["op_live"] == len(two["journal"]) for item in two["journal"]), \
        "живая операция посчитана по чужой метке"


def test_undo_by_entry_id_and_last_keep_their_meaning(con, find):
    """Прежние виды `what` не сдвинулись: числовой id откатывает ровно одну запись и оставляет
    операцию наполовину, `last` забирает её целиком, отказы у них прежние."""
    match_id = find(SCOREFUL, what="матч с числами")
    caption = card(con, match_id)["note"] or ""
    result = edit.set_source(con, match_id, "tester", note=f"{caption} — правка теста",
                             links=[["vk_post", "https://vk.com/test-undo"]])
    assert len(result["journal"]) > 1, "нужны минимум две записи, чтобы проверить `last`"

    single = edit.undo(con, str(result["journal"][0]))
    assert len(single["entries"]) == 1
    with pytest.raises(edit.EditError) as error:
        edit.undo(con, str(result["journal"][0]))
    assert "уже отменена" in str(error.value)

    rest = edit.undo(con, "last")
    assert len(rest["entries"]) == len(result["journal"]) - 1
    assert card(con, match_id)["note"] == caption, "откат `last` добил правку не до конца"
    with pytest.raises(edit.EditError) as error:
        edit.undo(con, "424242")
    assert "в журнале нет" in str(error.value)
