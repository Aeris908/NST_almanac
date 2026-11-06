"""Импортёры не плодят контейнеры: у документа одна турнирная рамка.

Живые календари командных чемпионатов приехали в базу позже её же игр из темы обсуждения, и
сезона у строки носителя нет. Пока импортёр подставлял «—», `ensure_tournament` заводил второй
«VI Командный Чемпионат по Goal 3»: игры календаря и игры обсуждения одного турнира лежали в
разных контейнерах, а фасет по сезону в панели показывал половину чемпионата отдельно.

Проверка идёт по свойствам собранной базы, а не по номерам строк: их пересоздаёт каждая сборка.
"""

import sqlite3

from db import import_live
from portal.live_sources import divisions
from portal.names import clean_alias

DOCS_ONE_TOURNAMENT = """
select doc_id from matches
where doc_id is not null and tournament_id is not null
group by doc_id having count(distinct tournament_id) > 1
"""

LIVE_ROWS_OUTSIDE_DOC_SEASON = """
select m.id from matches m
join tournament_docs d on d.id = m.doc_id
join tournaments t on t.id = m.tournament_id
where m.source = 'vk_live' and m.row_set = 'team'
  and json_extract(d.payload, '$.season_year') is not null
  and t.season <> json_extract(d.payload, '$.season_year')
"""


def test_every_document_keeps_its_games_in_one_tournament(con):
    """Один документ — один турнир-контейнер: рамка читает сезон и этап именно у него."""
    split = [row[0] for row in con.execute(DOCS_ONE_TOURNAMENT)]
    assert not split, f"документы с двумя контейнерами: {split}"


def test_alias_slice_follows_the_reference_table(con):
    """Срез алиасов — проекция справочника: изменилось направление, меняется и строка базы.

    `import_aliases` вставлял запись и больше к ней не возвращался, поэтому правка написания в
    `portal/name_tables.py` жила в базе по-старому: «валера» продолжал числиться за Centurion,
    когда справочник уже ведёт его к Буцу. Молчаливая ложь в срезе хуже пустого места — её читает
    и сверка, и поиск панели.
    """
    stale = []
    for alias, nick in con.execute(
        "select a.alias, p.nick from player_aliases a join players p on p.id = a.player_id"
        " where a.source = 'name_tables'"
    ):
        if clean_alias(alias) != nick:
            stale.append((alias, nick, clean_alias(alias)))
    assert not stale, f"срез алиасов отстал от справочника: {stale[:6]}"


def test_live_calendar_rows_sit_in_the_season_of_their_document(con):
    """Сезон строки календаря — тот, что записан в рамке турнира, иначе строка уедет в чужой фасет."""
    lost = [row[0] for row in con.execute(LIVE_ROWS_OUTSIDE_DOC_SEASON)]
    assert not lost, f"игр календаря вне сезона своего документа: {len(lost)}"


NAVIGATION = """НАВИГАЦИЯ
УЧАСТНИКИ:

DIVISION METEORS
[id178285783|ВОР95]
[id234043623|Tymoschuk]
[id40657539|DanLavis]

DIVISION COMETS
[id286855730|Memori]
[id693390|yoxter]

ОБЩАЯ ИНФОРМАЦИЯ
Количество участников - 20
ПРИМЕР ВЫКЛАДЫВАНИЯ РЕЗУЛЬТАТОВ:
1 Тур.
ВОР95 - Tymoschuk - 5:1
"""

REPORT = "9 тур, метеоры\nBZK - BOР95 7-5"


def test_divisions_are_read_from_the_roster_of_the_topic():
    """Шапка темы называет дивизион и аккаунт: принадлежность ноги берётся оттуда, а не из догадки.

    Списки обрезаются по первой строке вне блока, иначе «ОБЩАЯ ИНФОРМАЦИЯ» и образец выкладки
    доехали бы до состава, а строка-пример («ВОР95 - Tymoschuk - 5:1») стала бы игрой.
    """
    found = divisions([{"text": NAVIGATION}, {"text": REPORT}])
    assert found == {"Метеоры": ["BOР95", "Bubnov", "Dan_Lavis"], "Кометы": ["Memori", "yoxter"]}
    assert divisions([{"text": REPORT}]) == {}


def test_season_frames_have_no_document_but_have_a_season(db_path):
    """Рамка сезона — не документ: строка дивизиона привязывается по имени и берёт сезон из рамки."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        found = import_live.containers(con)
        season_row = con.execute("select name, season from tournaments where kind = 'league' limit 1").fetchone()
        assert season_row, "в собранной базе нет ни одной сезонной рамки"
        assert found[season_row["name"]] == (None, season_row["season"])
        doc = con.execute("select id, json_extract(payload, '$.title') as title,"
                          " json_extract(payload, '$.season_year') as season from tournament_docs"
                          " where kind = 'team' limit 1").fetchone()
        assert found[doc["title"].strip()] == (doc["id"], doc["season"])
    finally:
        con.close()
