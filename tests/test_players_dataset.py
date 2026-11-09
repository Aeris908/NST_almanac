"""Каталог игроков всех дисциплин — чистый архив: демо и дубли не считаются.

`portal/players_dataset.py` собирает карьеру игрока по всем дисциплинам прямо из базы.
Проверки идут по свойствам собранного каталога и по чистым хелперам исхода/фазы, а не по
номерам строк: их пересоздаёт каждая сборка. Демо-записи (#92) исключены решением владельца —
каталог показывает архив, а не синтетические встречи; дубли (`duplicate_of`) не удваивают счёт.
Исход стороны берётся из `outcome`/статуса базы, а не из подстроки в подписи.
"""

import shutil
import sqlite3

import pytest

from portal.players_dataset import build_players_dataset, get_match_result

CANONICAL_MATCHES = """
select count(distinct m.id) from matches m
join tournaments t on t.id = m.tournament_id
join disciplines d on d.id = t.discipline_id
join match_sides ms on ms.match_id = m.id
join side_players sp on sp.side_id = ms.id
join players p on p.id = sp.player_id
where m.status <> 'void' and m.hidden_by is null
  and m.duplicate_of is null and m.source <> 'demo'
"""


@pytest.fixture(scope="module")
def catalog_db(tmp_path_factory, source_db):
    target = tmp_path_factory.mktemp("players_catalog") / "nst.db"
    shutil.copy(source_db, target)
    return target


@pytest.fixture(scope="module")
def dataset(catalog_db):
    return build_players_dataset(catalog_db)


@pytest.fixture(scope="module")
def catalog_ids(dataset):
    return {m["id"] for p in dataset["players"] for m in p["matches"]}


def test_каталог_имеет_форму_справочника(dataset):
    """Ответ — справочник: сводка, дисциплины и карточки с карьерой, турнирами и историей."""
    assert set(dataset) == {"stats", "disciplines", "players"}
    assert dataset["players"], "каталог пуст — проверка ничего не сторожит"
    for card in dataset["players"]:
        assert {"nick", "career", "disciplines", "tournaments", "matches", "top_rivals"} <= set(card)
        assert {"matches", "wins", "draws", "losses", "goals_for", "goals_against"} <= set(card["career"])


def test_демо_встречи_не_попадают_в_каталог(catalog_db, catalog_ids):
    """Демо-посев (#92) — синтетика для редактора, не архив: ни одна его игра не в карьере."""
    con = sqlite3.connect(str(catalog_db))
    demo = {r[0] for r in con.execute("select id from matches where source = 'demo'")}
    con.close()
    assert demo, "в базе нет демо-строк — проверка ничего не сторожит"
    assert not (catalog_ids & demo), f"демо-игры в каталоге: {sorted(catalog_ids & demo)}"


def test_дубли_не_удваивают_счёт(catalog_db, catalog_ids):
    """Помеченная дублем строка — не вторая игра: каноническая остаётся, копия не считается."""
    con = sqlite3.connect(str(catalog_db))
    dup = {r[0] for r in con.execute("select id from matches where duplicate_of is not null")}
    con.close()
    assert dup, "в базе нет дублей — проверка ничего не сторожит"
    assert not (catalog_ids & dup), f"дубли в каталоге: {sorted(catalog_ids & dup)[:8]}"


def test_всего_матчей_равно_канонической_выборке_базы(dataset, catalog_db):
    """Сводка считает ровно канонические строки: не void, не скрытые, не дубли, не демо."""
    con = sqlite3.connect(str(catalog_db))
    expected = con.execute(CANONICAL_MATCHES).fetchone()[0]
    con.close()
    assert dataset["stats"]["total_matches"] == expected


def test_активные_игроки_идут_первыми(dataset):
    """Порядок витрины: сначала активные, затем Зал славы, затем ветераны."""
    flags = [(p["is_active"], p["is_hall_of_famer"]) for p in dataset["players"]]
    assert flags == sorted(flags, reverse=True)


def test_career_сходится_с_историей(dataset):
    """Победы/ничьи/поражения карьеры считаются по той же истории, что лежит в карточке."""
    for card in dataset["players"]:
        history = card["matches"]
        career = card["career"]
        assert career["matches"] == len(history)
        assert career["wins"] == sum(1 for m in history if m["res_type"] == "win")
        assert career["draws"] == sum(1 for m in history if m["res_type"] == "draw")
        assert career["losses"] == sum(1 for m in history if m["res_type"] == "loss")


def test_исход_при_равном_счёте_решает_outcome():
    """Нога 4:4 с outcome win — победа по буллитам (#88), а не ничья по голам."""
    assert get_match_result(4, 4, "win") == ("ПОБЕДА", "win")
    assert get_match_result(4, 4, "loss") == ("ПОРАЖЕНИЕ", "loss")
    assert get_match_result(4, 4, "draw") == ("НИЧЬЯ", "draw")


def test_исход_без_outcome_берётся_из_счёта():
    """Нет исхода сторон — победителя говорит счёт; равный счёт без исхода — ничья."""
    assert get_match_result(5, 3) == ("ПОБЕДА", "win")
    assert get_match_result(2, 3) == ("ПОРАЖЕНИЕ", "loss")
    assert get_match_result(3, 3) == ("НИЧЬЯ", "draw")


def test_технический_результат_по_статусу_строки():
    """Статус technical даёт подпись ТП поверх исхода стороны."""
    assert get_match_result(5, 3, "win", "technical") == ("ТП (ПОБЕДА)", "win")
    assert get_match_result(1, 5, "loss", "technical") == ("ТП (ПОРАЖЕНИЕ)", "loss")


def test_технический_результат_не_выдумывается_из_подстроки():
    """Четвёртый аргумент — статус строки, а не подпись: «тп» не есть статус technical.

    Технический результат определяется точным статусом базы, а не поиском букв «тп»/«тех»
    в тексте: иначе обычная победа с заметкой, содержащей эти буквы, стала бы technical.
    """
    assert get_match_result(5, 3, "win", "тп") == ("ПОБЕДА", "win")


def test_без_данных_исход_не_определён():
    """Ни исхода, ни счёта — сторона без результата, а не выдуманная ничья."""
    assert get_match_result(None, None) == ("—", "none")


def test_флаги_периода_из_фазы():
    """ОТ и буллиты — из фазы матча, а не из поиска «pk»/«буллит» в подписи."""
    from portal.players_dataset import period_flags

    assert period_flags("penalties") == (False, True)
    assert period_flags("overtime") == (True, False)
    assert period_flags("overtime_penalties") == (True, True)
    assert period_flags("regular") == (False, False)
    assert period_flags(None) == (False, False)