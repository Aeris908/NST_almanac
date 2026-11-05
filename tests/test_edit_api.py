"""Слой правки над ядром: предпросмотр не трогает базу, `expect` ловит чужую операцию, а
`locate` узнаёт строку по тому, что видит человек на странице.

Здесь проверяется то, чего на `db/edit.py` не проверить: договоренности ответа, по которым живёт
интерфейс (`created`, `op`, `journal`, дельта), и отказы там, где браузер прислал не то поле.
"""

import pytest
from db import api, edit, serve
from support import SCOREFUL, card, rosters, sides


@pytest.fixture
def preview(db_path):
    """`mutate` с `persist=False` обязан оставить базу ровно такой, какая была: смотреть, что
    сдвинется, и менять — один и тот же код."""
    def _call(operation, args):
        before = api.revision(db_path)
        answer = api.mutate(operation, args, "tester", persist=False, db_path=db_path)
        assert answer["persisted"] is False
        assert answer["journal"] == [], "предпросмотр оставил записи журнала"
        assert api.revision(db_path) == before, "предпросмотр изменил базу"
        return answer
    return _call


def test_preview_of_a_score_shows_base_fields_and_delta(find, preview):
    match_id = find(SCOREFUL, what="матч с числами")
    answer = preview("set-score", {"match_id": match_id, "s1": 0, "s2": 5})
    fields = {(item["table"], item["field"]) for item in answer["changes"]}
    assert ("match_sides", "score") in fields
    assert ("match_sides", "outcome") in fields
    assert answer["delta"], "правка счёта не сдвинула ни одной числа на витрине"


def test_preview_reports_cards_that_would_be_created(con, find, preview):
    """Опечатка в нике родит карточку, и человек обязан увидеть это до записи."""
    match_id = find(SCOREFUL, what="матч с числами")
    answer = preview("set-players", {"match_id": match_id,
                                     "sides": ["Новый Ник Раз", "Новый Ник Два"]})
    assert set(answer["created"]) == {"Новый Ник Раз", "Новый Ник Два"}
    assert con.execute("select count(*) from players where nick like 'Новый Ник%'").fetchone()[0] == 0


def test_write_applies_and_undoes_through_the_api(con, find, db_path):
    match_id = find(SCOREFUL, what="матч с числами")
    revision = api.revision(db_path)
    answer = api.mutate("set-score", {"match_id": match_id, "s1": 1, "s2": 4}, "tester",
                        persist=True, expect=revision, db_path=db_path)
    assert answer["persisted"] and answer["journal"] and answer["op"]
    assert sides(con, match_id)[0]["score"] == 1
    back = api.mutate("undo", {"what": "last"}, "tester", persist=True, db_path=db_path)
    assert len(back["reverted"]) == len(answer["journal"])
    assert api.revision(db_path) == revision, "откат не вернул исходную ревизию"


def test_expect_refuses_to_overwrite_another_editor(con, find, db_path):
    """Между «посмотрел» и «записал» база могла измениться под другим редактором."""
    match_id = find(SCOREFUL, what="матч с числами")
    was = sides(con, match_id)[0]["score"]
    with pytest.raises(edit.EditError) as error:
        api.mutate("set-score", {"match_id": match_id, "s1": 2, "s2": 0}, "tester",
                   persist=True, expect="0123456789abcdef", db_path=db_path)
    assert "база изменилась с момента предпросмотра" in str(error.value)
    assert sides(con, match_id)[0]["score"] == was


def test_locate_finds_the_row_by_nicks_behind_the_caption(con, find, db_path):
    """Страница сезона рисует ники карточек, а источник писал свою подпись: клик находит оба."""
    match_id = find("""select m.id from matches m
        join match_sides a on a.match_id = m.id and a.side_index = 0
        join match_sides b on b.match_id = m.id and b.side_index = 1
        where m.hidden_by is null and m.row_set = 'catalog' and a.score is not null
          and m.tour is not null limit 1""", what="строка каталога с туром")
    names = rosters(con, match_id)
    found = api.locate(names[0], names[1], tour=card(con, match_id)["tour"], db_path=db_path)
    ids = {candidate["id"] for candidate in found} | {
        linked for candidate in found for linked in (candidate.get("linked") or [])}
    assert match_id in ids


def test_locate_finds_a_scoreless_row_by_its_caption(con, find, db_path):
    """Строка без счёта показывает в колонке подпись, а не числа."""
    match_id = find("""select m.id from matches m
        join match_sides a on a.match_id = m.id and a.side_index = 0
        join match_sides b on b.match_id = m.id and b.side_index = 1
        where m.hidden_by is null and a.score is null and b.score is null and m.note <> '' limit 1""",
        what="строка без счёта с подписью")
    labels = [sides(con, match_id)[index]["label"] or sides(con, match_id)[index]["players"]
              for index in (0, 1)]
    found = [candidate["id"] for candidate in api.locate(labels[0], labels[1], db_path=db_path)]
    assert match_id in found


def test_locate_never_makes_a_hidden_double_a_separate_row(con, find, db_path):
    """Скрытый показ той же игры не становится самостоятельным кандидатом: правка идёт по связке,
    и её id виден в `linked` — иначе лоровед правил бы копию, а не то, что показывает страница."""
    hidden = find("""select m.id from matches m
        join match_sides a on a.match_id = m.id and a.side_index = 0
        where m.hidden_by is not null
          and (select count(*) from side_players where side_id = a.id) = 1 limit 1""",
        what="скрытый дубль с игроком на стороне")
    names = rosters(con, hidden)
    plain = api.locate(names[0], names[1], db_path=db_path)
    assert hidden not in {candidate["id"] for candidate in plain}
    assert any(hidden in (candidate.get("linked") or []) for candidate in plain), \
        "связка не собрана: правка ушла бы в одну строку из двух"
    wide = api.locate(names[0], names[1], include_hidden=True, db_path=db_path)
    assert len(wide) >= len(plain)


def test_players_search_treats_wildcards_as_letters(db_path):
    """`%` и `_` в нике — часть написания, а не маска: иначе «Sokol_5» нашёл бы половину архива."""
    assert len(api.players("", db_path=db_path)) > 1
    assert api.players("%", db_path=db_path) == []
    assert api.players("no_such_nick", db_path=db_path) == []


def test_queue_attaches_the_row_behind_a_task(db_path):
    """Задача редактуры без перехода к строке бесполезна: карточка прикладывается к каждой."""
    tasks = api.queue(db_path=db_path)
    if not tasks:
        pytest.skip("очередь пуста")
    assert any(task["row"] for task in tasks), "ни к одной задаче не приложена строка матча"
    assert {"task", "links", "tour", "sides", "row"} <= set(tasks[0])


def test_journal_survives_a_rebuilt_slice(con, find, db_path):
    """Импортёр пересоздаёт срез, и id из журнала указывает вникуда: `/api/log` обязан это
    пережить — запись остаётся, матч просто не подписан.

    Так и моделируется: запись журнала остаётся, а `row_id` уезжает на несуществующую строку
    (удалять саму строку нельзя — на неё смотрит связка).
    """
    match_id = find(SCOREFUL, what="матч с числами")
    answer = api.mutate("set-score", {"match_id": match_id, "s1": 6, "s2": 1}, "tester",
                        persist=True, db_path=db_path)
    con.execute("update corrections set row_id = 999999 where id = ?", (answer["journal"][0],))
    con.commit()
    entries = api.journal_entries(limit=10, db_path=db_path)
    assert entries, "журнал потерял записи"
    moved = [entry for entry in entries if entry["id"] == answer["journal"][0]]
    assert moved and "match" not in moved[0], "запись о несуществующем матче обязана быть без подписи"
    assert all(isinstance(entry, dict) for entry in entries)


def test_http_layer_checks_arguments_before_calling_the_api(find):
    """`serve._edit` — единственная защита от запроса без обязательного поля: ядро упало бы на
    KeyError, а человеку нужен внятный текст отказа."""
    match_id = find(SCOREFUL, what="матч с числами")
    with pytest.raises(edit.EditError) as error:
        serve._edit({"operation": "set-score", "args": {"match_id": match_id}})
    assert "s1" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        serve._edit({"operation": "teleport", "args": {}})
    assert "неизвестная операция" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        serve._edit({"operation": "set-players", "args": {"match_id": match_id, "sides": ["Один"]}})
    assert "sides" in str(error.value)
    with pytest.raises(edit.EditError) as error:
        serve._edit({"operation": "set-source",
                     "args": {"match_id": match_id, "links": ["https://example.com"]}})
    assert "links" in str(error.value)
