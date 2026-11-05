"""Правка применяется к копии базы и откатывается: база обязана вернуться к исходному срезу.

Каждый тест проверяет три факта, а не «функция вызывается без исключения»: изменилось именно то
поле, которым операция владеет; связка строк одной игры не разъехалась; `undo last` вернул
исходный срез целиком — включая строки, которые операция удалила или завела.

Где полный возврат принципиально невозможен, это сказано в тесте открыто: пересборка состава после
отката вставляет строки `side_players` заново (rowid у них новые), а карточка игрока, заведённая
при правке, после отката остаётся — страница её не показывает, пока у игрока нет матчей.
"""

import json

from db import edit
from support import (SINGLES, SCOREFUL, SCORELESS, WITH_PAIR, card, links, rosters, sides)


def test_set_score_swaps_outcomes_and_undoes(con, find, fingerprint, undone):
    """Счёт правится вместе с исходами: иначе база ездит с парой «3:0 и ничья»."""
    match_id = find(SCOREFUL, what="матч, где первая сторона выиграла")
    before = fingerprint()
    edit.set_score(con, match_id, 0, 3, "tester")
    result = sides(con, match_id)
    assert (result[0]["score"], result[1]["score"]) == (0, 3)
    assert (result[0]["outcome"], result[1]["outcome"]) == ("loss", "win")
    assert card(con, match_id)["manual"] == 1
    undone(before)


def test_set_score_into_scoreless_row_moves_caption(con, find, fingerprint, undone):
    """Строка без счёта показывает в таблице свою подпись — числа обязаны увести её за собой."""
    match_id = find(SCORELESS, what="строка турнира без счёта")
    caption = card(con, match_id)["note"]
    before = fingerprint()
    edit.set_score(con, match_id, 7, 4, "tester")
    assert card(con, match_id)["note"] == "7:4"
    assert sides(con, match_id)[0]["score"] == 7
    undone(before)
    assert card(con, match_id)["note"] == caption


def test_set_place_rewrites_whole_pair_and_remembers_source_place(con, find, fingerprint, undone):
    """Перенос идёт по всей связке, а импортёру остаётся память о прежнем месте.

    Без `source_place` следующий импорт не узнал бы строку в новом туре и принёс бы ту же игру
    вторым рядом — на витрине появился бы видимый дубль.
    """
    match_id = find(WITH_PAIR, what="строка страницы со своей рейтинговой копией")
    pair = edit.pair_ids(con, match_id)
    keyless = [current for current in pair if card(con, current)["source_ref"] is None]
    old_place = {current: (card(con, current)["tour"] or card(con, current)["league"])
                 for current in keyless}
    before = fingerprint()
    edit.set_place(con, match_id, "tester", tour="Тестовый тур")
    for current in pair:
        assert card(con, current)["tour"] == "Тестовый тур"
    for current in keyless:
        assert card(con, current)["source_place"] == old_place[current]
    undone(before)


def test_set_place_to_existing_stage_creates_no_new_stage(con, find, fingerprint, undone):
    """Этап выбирается по названию через `ensure_stage`: на одну строку сезона не плодятся стадии."""
    match_id, stage = find("""select m.id, st.name from matches m
        join stages st on st.id = m.stage_id where m.hidden_by is null limit 1""",
        what="строка с этапом")
    stages_before = con.execute("select count(*) from stages").fetchone()[0]
    before = fingerprint()
    edit.set_place(con, match_id, "tester", stage=stage, league="Тестовый дивизион")
    assert card(con, match_id)["league"] == "Тестовый дивизион"
    assert con.execute("select count(*) from stages").fetchone()[0] == stages_before, \
        "существовавший этап завёл новую стадию"
    undone(before)


def test_set_date_precision_follows_the_shape(con, find, fingerprint, undone):
    """Точность выводится из формы даты: враньё в `date_precision` искажает порядок партий в Elo."""
    match_id = find("select id from matches where hidden_by is null limit 1", what="любая строка")
    for value, precision in (("2024", "season"), ("2024-06", "month"), ("2024-06-15", "exact")):
        before = fingerprint()
        edit.set_date(con, match_id, "tester", played_on=value)
        row = card(con, match_id)
        assert (row["played_on"], row["date_precision"]) == (value, precision)
        undone(before)


def test_set_phase_roundtrip(con, find, fingerprint, undone):
    """Фаза и цена плей-офф — это веса Elo: 0.75 за победу в серии и K=32 в плей-офф."""
    match_id = find(SCOREFUL, what="матч с числовым счётом")
    pair = edit.pair_ids(con, match_id)
    before = fingerprint()
    edit.set_phase(con, match_id, "tester", phase="penalties", playoff=True)
    for current in pair:
        row = card(con, current)
        assert (row["phase"], row["is_playoff"]) == ("penalties", 1)
    undone(before)


def test_set_provenance_touches_only_the_addressed_row(con, find, fingerprint, undone):
    """Происхождение — свойство носителя: у связки два ключа, и общий встал бы в UNIQUE."""
    match_id = find(WITH_PAIR, what="строка с копией в пуле")
    other = next(current for current in edit.pair_ids(con, match_id) if current != match_id)
    other_ref = card(con, other)["source_ref"]
    before = fingerprint()
    edit.set_provenance(con, match_id, "tester", source_ref="ZZ-TEST-1",
                        source_text="сказано человеком")
    assert card(con, match_id)["source_ref"] == "ZZ-TEST-1"
    assert card(con, match_id)["source_text"] == "сказано человеком"
    assert card(con, other)["source_ref"] == other_ref, "ключ чужой строки перезаписан"
    undone(before)


def test_set_players_writes_label_only_where_the_reader_takes_it(con, find, fingerprint, undone):
    """Таблица турнира печатает `label`, каталог сезона — ник карточки.

    Подпись правится там, где читатель имя действительно берёт: иначе правка легла бы в базу
    мёртвым грузом, а витрина продолжала бы показывать старое написание.
    """
    for where, label_expected_to_move in (("m.doc_id is not null", True),
                                          ("m.doc_id is null and m.row_set = 'catalog'", False)):
        match_id, nick_a, nick_b = find(SINGLES.format(where=where),
                                        what="матч 1×1 с карточками на обеих сторонах")
        label_before = {index: sides(con, match_id)[index]["label"] for index in (0, 1)}
        assert {nick_a, nick_b} == set(rosters(con, match_id).values())
        before = fingerprint()
        edit.set_players(con, match_id, [nick_b, nick_a], "tester")
        assert set(rosters(con, match_id).values()) == {nick_a, nick_b}
        assert rosters(con, match_id)[0] == nick_b
        moved = sides(con, match_id)[0]["label"] != label_before[0]
        assert moved is label_expected_to_move, (
            f"написание стороны у {where} поехало бы не туда: читатель берёт его из другого места")
        undone(before)
        assert {index: sides(con, match_id)[index]["label"] for index in (0, 1)} == label_before


def test_set_players_new_nick_creates_card_and_undo_leaves_it(con, find):
    """Опечатка в нике родит карточку, и откат её не убирает — правка обязана предупредить до
    записи (это делает предпросмотр в ответе `created`)."""
    match_id = find(SCOREFUL, what="матч с числовым счётом")
    nick_before = rosters(con, match_id)[0]
    players_before = con.execute("select count(*) from players").fetchone()[0]
    result = edit.set_players(con, match_id, ["Тестовый Ник Один", "Тестовый Ник Два"], "tester")
    assert set(result["created"]) == {"Тестовый Ник Один", "Тестовый Ник Два"}
    assert con.execute("select count(*) from players").fetchone()[0] == players_before + 2
    edit.undo(con, "last")
    assert rosters(con, match_id)[0] == nick_before
    assert con.execute("select count(*) from players").fetchone()[0] == players_before + 2


def test_set_source_replaces_links_wholesale(con, find, fingerprint, undone):
    """Ссылки заменяются списком целиком: что вписано, то и есть доказательства игры."""
    match_id = find("""select m.id from matches m join match_links l on l.match_id = m.id
        where m.hidden_by is null group by m.id having count(*) > 1 limit 1""",
        what="матч с двумя и более ссылками")
    had = links(con, match_id)
    before = fingerprint()
    wanted = [("vk_post", "https://vk.com/topic-1#post1"), ("video", "https://vk.com/video-1")]
    edit.set_source(con, match_id, "tester", note="7:4 по протоколу", links=wanted)
    assert links(con, match_id) == set(wanted)
    assert card(con, match_id)["note"] == "7:4 по протоколу"
    undone(before)
    assert links(con, match_id) == had


def test_add_match_creates_row_and_undo_removes_it(con, find, fingerprint, undone):
    """Новая игра: `manual = 1`, `source = 'editor'`, подпись выводится из счёта — иначе строка
    вышла бы из таблицы турнира с пустой ячейкой, а история игроков её не заметила бы."""
    doc_key, stage, nick_a, nick_b = find("""select d.doc_key, st.name, pa.nick, pb.nick
        from tournament_docs d
        join matches m on m.doc_id = d.id and m.hidden_by is null
        join stages st on st.id = m.stage_id
        join match_sides a on a.match_id = m.id and a.side_index = 0
        join match_sides b on b.match_id = m.id and b.side_index = 1
        join side_players spa on spa.side_id = a.id join players pa on pa.id = spa.player_id
        join side_players spb on spb.side_id = b.id join players pb on pb.id = spb.player_id
        where d.kind = 'special'
          and (select count(*) from side_players where side_id = a.id) = 1
          and (select count(*) from side_players where side_id = b.id) = 1 limit 1""",
        what="спецтурнир со стадией и матчем 1×1")
    doc_id = con.execute("select id from tournament_docs where doc_key = ?", (doc_key,)).fetchone()[0]
    before = fingerprint()
    result = edit.add_match(con, {"doc_key": doc_key, "stage": stage, "sides": [nick_a, nick_b],
                                  "s1": 5, "s2": 2}, "tester")
    match_id = result["match_id"]
    row = card(con, match_id)
    assert (row["note"], row["status"], row["manual"]) == ("5:2", "played", 1)
    assert tuple(con.execute("select source, doc_id from matches where id = ?",
                             (match_id,)).fetchone()) == ("editor", doc_id)
    assert sides(con, match_id)[0]["outcome"] == "win"
    undone(before)
    assert con.execute("select count(*) from matches where id = ?", (match_id,)).fetchone()[0] == 0


def test_add_tournament_then_drop_it_then_undo_both(con, fingerprint, unchanged):
    """Турнир заводится рамкой с пустым списком игр, удаляется только пустой, а откаты идут
    слоями: последний откатывает предыдущий."""
    before = fingerprint()
    edit.add_tournament(con, {"doc_key": "test_cup_1", "title": "Тестовый Кубок",
                              "kind": "special", "frame": {"category": "Спецтурниры"}}, "tester")
    doc = con.execute("select payload, manual, match_field, match_keys from tournament_docs"
                      " where doc_key = 'test_cup_1'").fetchone()
    assert doc["manual"] == 1 and doc["match_field"] == "matches"
    assert json.loads(doc["payload"])["matches"] == [], "список игр обязан остаться пустым"
    assert json.loads(doc["match_keys"]) == ["stage", "p1", "p2", "score"]

    edit.drop_tournament(con, "test_cup_1", "tester")
    assert con.execute("select count(*) from tournament_docs where doc_key = 'test_cup_1'"
                       ).fetchone()[0] == 0
    edit.undo(con, "last")
    assert con.execute("select count(*) from tournament_docs where doc_key = 'test_cup_1'"
                       ).fetchone()[0] == 1
    edit.undo(con, "last")
    assert con.execute("select count(*) from tournament_docs where doc_key = 'test_cup_1'"
                       ).fetchone()[0] == 0
    assert con.execute("select count(*) from corrections where reverted_at is null"
                       ).fetchone()[0] == 0
    unchanged(fingerprint(), before)


def test_set_doc_marks_manual_and_replaces_frame(con, find, fingerprint, undone):
    """Рамку ведёт человек, и носитель больше не должен её перезаписывать: `manual = 1`."""
    doc_key = find("select doc_key from tournament_docs where kind = 'special' limit 1",
                   what="документ турнира")
    payload_before = con.execute("select payload, manual from tournament_docs where doc_key = ?",
                                 (doc_key,)).fetchone()
    before = fingerprint()
    new_frame = json.loads(payload_before["payload"])
    new_frame["description"] = "Описание от лороведа"
    edit.set_doc(con, doc_key, "tester", title="Новый заголовок", frame=new_frame)
    row = con.execute("select title, payload, manual from tournament_docs where doc_key = ?",
                      (doc_key,)).fetchone()
    assert row["manual"] == 1 and row["title"] == "Новый заголовок"
    assert "Описание от лороведа" in row["payload"]
    undone(before)


def test_rename_player_moves_nick_and_slug_together(con, find, fingerprint, undone):
    """Slug правится вместе с ником: иначе ссылка в адресе начнёт вести в чужую карточку."""
    player_id, nick, slug = find(
        "select id, nick, slug from players where nick is not null and nick <> '' order by id limit 1",
        what="игрок")
    from db.build_db import slugify
    new_nick = f"{nick} Тест"
    assert slugify(new_nick) != slug, "ник должен давать новый адрес, иначе тест ничего не проверяет"
    before = fingerprint()
    edit.rename_player(con, player_id, new_nick, "tester")
    row = con.execute("select nick, slug from players where id = ?", (player_id,)).fetchone()
    assert (row["nick"], row["slug"]) == (new_nick, slugify(new_nick))
    undone(before)


def test_merge_player_moves_sides_alias_and_side_ids(con, find, fingerprint, unchanged):
    """Слияние: партии переезжают, ушедшее написание становится алиасом, карточка исчезает.

    Откат возвращает всё — включая id строк состава: журнал адресует `side_players` именно по
    нему, и «вернулся тот же состав под другими номерами» для массовой правки неприемлем.
    """
    keep, drop = find("""
        with counts as (select p.id, (select count(*) from side_players sp
                                      where sp.player_id = p.id) n from players p)
        select a.id, b.id from counts a join counts b on a.id < b.id
        where a.n between 1 and 4 and b.n between 1 and 4
          and not exists (select 1 from match_sides sa
             join side_players spa on spa.side_id = sa.id
             join match_sides sb on sb.match_id = sa.match_id and sb.side_index <> sa.side_index
             join side_players spb on spb.side_id = sb.id
             where spa.player_id = a.id and spb.player_id = b.id)
        order by a.n + b.n, a.id limit 1""", what="двое, кто никогда не играл друг против друга")
    drop_nick = con.execute("select nick from players where id = ?", (drop,)).fetchone()[0]
    rowids_before = sorted(row[0] for row in con.execute(
        "select rowid from side_players where player_id = ?", (drop,)))
    players_before = con.execute("select count(*) from players").fetchone()[0]
    before = fingerprint()

    edit.merge_player(con, keep, drop, "tester")
    assert con.execute("select count(*) from players where id = ?", (drop,)).fetchone()[0] == 0
    assert con.execute("select count(*) from side_players where player_id = ?",
                       (drop,)).fetchone()[0] == 0
    alias = con.execute("select player_id, source from player_aliases where alias = ?",
                        (drop_nick,)).fetchone()
    assert alias is not None and alias[0] == keep and alias[1] == "editor"

    edit.undo(con, "last")
    assert con.execute("select count(*) from players").fetchone()[0] == players_before
    assert sorted(row[0] for row in con.execute(
        "select rowid from side_players where player_id = ?", (drop,))) == rowids_before
    assert con.execute("select count(*) from player_aliases where alias = ?",
                       (drop_nick,)).fetchone()[0] == 0
    unchanged(fingerprint(), before)


def test_drop_match_cascades_and_undo_restores_everything(con, find, fingerprint, unchanged):
    """Удаление игры уносит стороны, состав и ссылки (каскад по FK), откат возвращает связку
    байт-в-байт — вместе с указателями `duplicate_of`/`hidden_by` внутри неё."""
    match_id = find("""select m.id from matches m
        join match_sides a on a.match_id = m.id and a.side_index = 0
        join match_sides b on b.match_id = m.id and b.side_index = 1
        left join matches t on (t.duplicate_of = m.id or t.hidden_by = m.id) and t.id <> m.id
        where m.hidden_by is null and t.id is null and m.row_set <> 'pool'
          and (select count(*) from incoming i where i.matched_match_id = m.id) = 0 limit 1""",
        what="игра, на которую никто не ссылается")
    pair = edit.pair_ids(con, match_id)
    pointers = [(current, card(con, current)["duplicate_of"], card(con, current)["hidden_by"])
                for current in pair]
    before = fingerprint()
    edit.drop_match(con, match_id, "tester")
    for current in pair:
        for table, column in (("matches", "id"), ("match_sides", "match_id"),
                              ("match_links", "match_id")):
            assert con.execute(f"select count(*) from {table} where {column} = ?",
                               (current,)).fetchone()[0] == 0

    edit.undo(con, "last")
    for current, duplicate_of, hidden_by in pointers:
        row = card(con, current)
        assert (row["duplicate_of"], row["hidden_by"]) == (duplicate_of, hidden_by)
    unchanged(fingerprint(), before)


def test_drop_match_unhooks_review_queue(con, find):
    """Задача редактуры не исчезает вместе со строкой: она остаётся в очереди без строки."""
    match_id = find("""select m.id from matches m
        left join matches t on (t.duplicate_of = m.id or t.hidden_by = m.id) and t.id <> m.id
        where m.hidden_by is null and m.row_set <> 'pool' and t.id is null limit 1""",
        what="строка витрины без внешних ссылок")
    task = find("select id from incoming where verdict = 'conflict' limit 1", what="задача очереди")
    con.execute("update incoming set matched_match_id = ? where id = ?", (match_id, task))
    con.commit()

    edit.drop_match(con, match_id, "tester")
    assert con.execute("select matched_match_id from incoming where id = ?",
                       (task,)).fetchone()[0] is None
    edit.undo(con, "last")
    assert con.execute("select matched_match_id from incoming where id = ?",
                       (task,)).fetchone()[0] == match_id


def test_void_and_unhide_roundtrip(con, find, fingerprint, undone):
    """`void` убирает игру из чисел, не стирая строку; `unhide` возвращает на витрину спрятанный
    показ той же игры."""
    match_id = find(SCOREFUL, what="матч с числовым счётом")
    before = fingerprint()
    edit.set_status(con, match_id, "void", "tester", reason="не игралась")
    assert card(con, match_id)["status"] == "void"
    undone(before)

    hidden = find("select id from matches where hidden_by is not null limit 1",
                  what="строка, спрятанная как дубль")
    before = fingerprint()
    edit.unhide(con, hidden, "tester")
    assert card(con, hidden)["hidden_by"] is None
    undone(before)


def test_set_rating_flag_roundtrip(con, find, fingerprint, undone):
    """Флаг «рейтинговая партия» правится по всей связке: в пул смотрит вьюха `v_rating_pool`,
    и половина игры без флага считалась бы рейтингом наполовину."""
    match_id = find("select id from matches where row_set = 'pool' and in_rating_pool = 1 limit 1",
                    what="партия рейтингового пула")
    pair = edit.pair_ids(con, match_id)
    def in_pool():
        return con.execute("select count(*) from v_rating_pool where id = ?",
                           (match_id,)).fetchone()[0]

    assert in_pool() == 1
    before = fingerprint()
    edit.set_rating(con, match_id, False, "tester")
    for current in pair:
        assert card(con, current)["in_rating_pool"] == 0
    assert in_pool() == 0, "снятая партия осталась в рейтинговом пуле"
    undone(before)
    assert in_pool() == 1


def test_rate_scope_marks_a_season_and_one_undo_reverts_it(con, find, fingerprint, unchanged):
    """Массовая правка — одна операция: `undo last` снимает флаг со всех строк сразу, а не с
    последней записи журнала."""
    season = find("""select t.season from matches m join tournaments t on t.id = m.tournament_id
        where m.in_rating_pool = 0 and m.hidden_by is null and m.duplicate_of is null
          and m.played_on is not null and t.season like 'Season%'
        group by t.season having count(*) > 3 order by count(*) desc limit 1""",
        what="сезон с немаркированными играми")
    before = fingerprint()
    marked = edit.set_rating_scope(con, True, "tester", season=season)
    assert len(marked["journal"]) > 1, "ожидались десятки строк, а не одна"
    assert con.execute("select count(*) from corrections where reverted_at is null").fetchone()[0] \
        == len(marked["journal"])
    edit.undo(con, "last")
    assert con.execute("select count(*) from corrections where reverted_at is null").fetchone()[0] == 0
    unchanged(fingerprint(), before)


def test_validate_still_passes_after_edit_and_undo(con, db_path, find):
    """Валидатор обязан принимать базу до правки, во время неё и после отката: на нём падает
    сборка, и лоровед должен получать отказ здесь, а не в страницах."""
    from pathlib import Path

    from db import validate

    assert validate.run(Path(db_path)) == 0
    match_id = find(SCOREFUL, what="матч с числовым счётом")
    edit.set_score(con, match_id, 3, 0, "tester")
    assert validate.run(Path(db_path)) == 0
    edit.undo(con, "last")
    assert validate.run(Path(db_path)) == 0
