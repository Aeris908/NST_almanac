"""Нога, сыгранная вничью и решённая серией буллитов, — победа и поражение, а не ничья.

Источник называет серию рядом с ничейным счётом: «4:4 (8:6)», «5-5 (ПК 2-5)», «6-6 PK 5:4»,
«2:2 7:6пен.». Прежде разборщик знал только скобки с числами сразу после них, а исход ноги никуда
не нёс: `portal/player_records.py` звал `result_of(s1, s2)` без серии, нога уходила в историю
ничьей и в зачёт `draws`. Шесть ног вики Сезона 6 лежали при этом ещё и в фазе `regular`, хотя
серия названа, — валидатор базы разрешает победу при равном счёте только вне regular-этапа.

Ориентация сторон обязательна: комментарий пишет «Mcfly- Dune 4-4 (5-6)», а база хранит первой
стороной Dune — без сверки имён победа досталась бы не тому. Серия берётся только когда обе
стороны узнаны в строке (или в шапке встречи, если строка имён не несёт). Иначе нога остаётся
ничьей: угадывать победителя нельзя.
"""

import importlib
import re
import sys
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.comment_origin import shootout_of

TALLY = {"reg_w": 0, "ot_w": 0, "pk_w": 0, "reg_l": 0, "ot_l": 0, "pk_l": 0, "draws": 0}


# --- разборщик: какие записи серии источник действительно использует ---

def test_скобки_с_тем_же_счётом_серией_не_становятся():
    """«E_not - WiSe (3 - 3)»: в скобках счёт самой ноги, а не доигровка.

    Ранний архив пишет ногу в скобках, и разборщик принимал её за серию буллитов: четыре ноги
    Сезона 1 получали признак буллитов там, где доигровки не было. Серия всегда с победителем,
    поэтому равная пара в скобках — не серия.
    """
    assert shootout_of("Soccer League Tournament. 3 Тур.\nWiSe - E_not (2 - 2)\n"
                       "E_not - WiSe (3 - 3)", 3, 3) is None
    assert shootout_of("4 тур \nWiSE - Ric25 (2 - 2)\nRic25 - WiSe (5 - 2)", 2, 2) is None
    assert shootout_of("7 тур \nWenderfit - WiSe (2 - 2) \nWiSe - Wenderfit (3 - 0)", 2, 2) is None


def test_пометка_перед_числами_в_скобках_не_прячет_серию():
    """«(PK 6:7)», «(ПК 2-5)», «(пк: 9-7)» — та же серия, что «(6:7)», с пометкой впереди."""
    assert shootout_of("Huba Buba - mafuta 4:4 (PK 6:7)", 4, 4) == (6, 7)
    assert shootout_of("FC Pushistik - Romix 5-5 (ПК 2-5)", 5, 5) == (2, 5)
    assert shootout_of("4-4 (пк: 9-7)", 4, 4) == (9, 7)


def test_серия_без_скобок_читается_по_пометке_рядом():
    """Регламент темы допускает запись без скобок: «6-6 PK 5:4» и «2:2 7:6пен.»."""
    assert shootout_of("Dune vs Wenderfit 6 - 6 PK 5:4", 6, 6) == (5, 4)
    assert shootout_of("Wenderfit vs Dune 3 - 3 PK 3:4", 3, 3) == (3, 4)
    assert shootout_of("legnahar vs Веселый Роджер- 2:2 7:6пен.  1  матч по пенальти", 2, 2) == (7, 6)


def test_из_скобок_берётся_серия_а_не_следующая_нога():
    """«4:4(8:6),3:0» — вторая нога встречи идёт после запятой, серией первой ноги быть не может."""
    assert shootout_of("mafuta vs Сenturion 4:4(8:6),3:0", 4, 4) == (8, 6)
    assert shootout_of("5-й сольный. Вышка. 4 тур. изотоп vs мафута 3:3(4:5PK), 2:1", 3, 3) == (4, 5)


# --- ориентация: чья победа ---

def test_серия_переворачивается_когда_база_хранит_стороны_наоборот():
    """Две ноги Сезона 6 записаны в тексте обратной стороной: без переворота победа стала бы поражением."""
    from portal.comment_origin import series_for_sides

    assert series_for_sides("Mcfly- Dune 4-4 (5-6)", 4, 4, "Dune", "Mcfly") == (6, 5)
    assert series_for_sides("dynamik 4-4 Dune (4-5)", 4, 4, "Dune", "Dynamik") == (5, 4)


def test_прямой_порядок_сторон_сохраняется():
    from portal.comment_origin import series_for_sides

    assert series_for_sides("Kunio VS Romix - 2:2 (4:6)", 2, 2, "Kunio", "Romix") == (4, 6)
    assert series_for_sides("Transistor VS Kunio - 4:4 (10:11)", 4, 4, "Transistor", "Kunio") == (10, 11)


def test_стороны_узнаются_по_написаниям_справочника():
    """Источник пишет «XakoFEAR», «BOP213», «МГБ», «Сenturion» — справочник алиасов знает их все."""
    from portal.comment_origin import series_for_sides

    assert series_for_sides("XakoFEAR - TEXAS - 4:4 (4-3 ПК)", 4, 4, "RVD (МГБ)", "Texas") == (4, 3)
    assert series_for_sides("ectoPower vs BOP213 - 4:4 (7-6 пенальти)", 4, 4, "ectoPower", "BOР95") == (7, 6)
    assert series_for_sides("МГБ - ectoPower - 4 - 4 (9-10 ПК)", 4, 4, "RVD (МГБ)", "ectoPower") == (9, 10)
    assert series_for_sides("ruby - rodger 1:1 (4:3 PK)", 1, 1, "ruby", "Веселый Роджер") == (4, 3)


def test_шапка_встречи_даёт_порядок_сторон_строке_без_имён():
    """Sportcup перечисляет ноги под шапкой «ectoPower vs Romix:» — сама строка счёта имён не несёт."""
    from portal.comment_origin import series_for_sides

    text = "1/2 финала\nectoPower vs Romix:\n5-4\n3-2\n4-3\n2-3\n4-4 (пк: 9-7)"
    assert series_for_sides(text, 4, 4, "ectoPower", "Romix") == (9, 7)


def test_неузнанная_сторона_оставляет_ногу_ничьей():
    """Счёт 7:6 стоит в порядке одной стороны, а текст называет победителем другую.

    «Веселый Роджер -kot-from-uss2:2 (7:6 кот Юсер выиграл … матч 2 по пенальти»: имя обрезано,
    обе стороны не узнаются, и источник противоречит сам себе. Выбирать победителя угадыванием
    нельзя — нога остаётся ничьей и уходит в отчёт сборки.
    """
    from portal.comment_origin import series_for_sides

    text = ("Веселый Роджер -kot-from-uss2:2 (7:6 кот Юсер выиграл 1 матч в основное время "
            "и матч 2 по пенальти")
    assert series_for_sides(text, 2, 2, "kot-from-ussr", "Веселый Роджер") is None


def test_без_серии_исход_не_появляется():
    from portal.comment_origin import series_for_sides

    assert series_for_sides("Wenderfit vs Memori - 3:3", 3, 3, "Wenderfit", "Memori") is None
    assert series_for_sides("Memori vs Ric25 - 4:0", 4, 0, "Memori", "Ric25") is None
    assert series_for_sides(None, 3, 3, "Wenderfit", "Memori") is None


# --- база: исход стороны и фаза ---

@pytest.fixture
def fresh_db(tmp_path):
    """Пустая база по штатной схеме; сборочные модули импортируются офлайн.

    `db/build_db.py` при импорте тянет `build_final_analytics`, а тот проверяет соединение с ВК:
    без подмены секрета тест ушёл бы в сеть. Схема применяется штатным `apply_schema` — в файле
    после тела идут шаги достройки, и `executescript` целиком падает на повторной колонке.
    """
    from db import store

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("portal.env_file.secret", lambda name, path=None: "")
        patch.delitem(sys.modules, "build_final_analytics", raising=False)
        patch.delitem(sys.modules, "db.build_db", raising=False)
        builder = importlib.import_module("db.build_db")
        path = tmp_path / "fresh.db"
        con = store.connect(path)
        builder.apply_schema(con)
        con.commit()
        con.close()
        yield path


def leg(p1, p2, s1, s2, text, **extra):
    return dict({"season": "Season 6", "league": "Высшая лига", "tour": "1 Тур",
                 "p1": p1, "p2": p2, "s1": s1, "s2": s2, "ot": False, "pk": False,
                 "source": "vk_comments_playoff", "vk_text": text}, **extra)


def stored_side_outcomes(path):
    from db import store

    con = store.connect(path)
    try:
        return [tuple(row) for row in con.execute(
            """select m.phase, sa.outcome, sb.outcome from matches m
               join match_sides sa on sa.match_id = m.id and sa.side_index = 0
               join match_sides sb on sb.match_id = m.id and sb.side_index = 1
               order by m.order_in_source""")]
    finally:
        con.close()


def import_legs(path, rows):
    from db import store
    from db.import_stores import Importer, import_league

    con = store.connect(path)
    try:
        import_league(Importer(con), rows)
        con.commit()
    finally:
        con.close()


def test_импорт_кладёт_исход_серии_в_стороны_и_фазу_буллитов(fresh_db):
    """Носитель помечает pk=false, а комментарий серию называет: фаза и исход обязаны следовать за ней."""
    import_legs(fresh_db, [leg("mafuta", "Centurion", 4, 4,
                               "Высшая Soccer League. Сезон 6. 1 тур. mafuta vs Сenturion 4:4(8:6),3:0")])
    assert stored_side_outcomes(fresh_db) == [("penalties", "win", "loss")]


def test_импорт_не_отдаёт_победу_не_той_стороне(fresh_db):
    """Текст «Mcfly- Dune 4-4 (5-6)», база хранит первой стороной Dune — выиграл Dune, а не Mcfly."""
    import_legs(fresh_db, [leg("Dune", "Mcfly", 4, 4, "2 тур двор\nDune - Mcfly 2 1\nMcfly- Dune 4-4 (5-6)")])
    assert stored_side_outcomes(fresh_db) == [("penalties", "win", "loss")]


def test_импорт_оставляет_честную_ничью_ничьей(fresh_db):
    """Серии нет — исход ничья, и фаза не становится буллитной."""
    import_legs(fresh_db, [leg("Wenderfit", "Memori", 3, 3, "5 тур.\nWenderfit vs Memori - 3:3")])
    assert stored_side_outcomes(fresh_db) == [("regular", "draw", "draw")]


def test_импорт_не_угадывает_исход_при_неузнанной_стороне(fresh_db):
    import_legs(fresh_db, [leg("kot-from-ussr", "Веселый Роджер", 2, 2,
                               "Веселый Роджер -kot-from-uss2:2 (7:6 кот Юсер выиграл по пенальти")])
    assert stored_side_outcomes(fresh_db) == [("regular", "draw", "draw")]


def test_читатель_отдаёт_исход_решённой_ноги(fresh_db):
    """История игрока собирается из базы: без ключа в строке читатель исход не узнает."""
    from db.catalog import catalog_from_db

    import_legs(fresh_db, [leg("mafuta", "Centurion", 4, 4, "1 тур. mafuta vs Сenturion 4:4(8:6),3:0"),
                         leg("Wenderfit", "Memori", 3, 3, "5 тур. Wenderfit vs Memori - 3:3")])
    rows = catalog_from_db(fresh_db)
    decided = next(m for m in rows if m["p1"] == "mafuta")
    honest = next(m for m in rows if m["p1"] == "Wenderfit")
    assert decided["outcome"] == ["win", "loss"]
    assert decided["pk"] is True
    assert "outcome" not in honest, "честной ничьей исход счёта не подменяется"


# --- история игрока и зачёт ---

def records(match):
    from portal.player_records import add_season_records

    player_matches, addon = defaultdict(list), defaultdict(lambda: dict(TALLY))
    add_season_records(player_matches, addon, match)
    return player_matches, addon


def test_нога_с_серией_идёт_в_историю_победой_и_в_зачёт_буллитов():
    player_matches, addon = records({
        "p1": "mafuta", "p2": "Centurion", "s1": 4, "s2": 4, "ot": False, "pk": True,
        "season": "Season 6", "league": "Высшая лига", "tour": "1 Тур", "outcome": ["win", "loss"]})
    assert player_matches["mafuta"][0]["result"] == "ПОБЕДА"
    assert player_matches["Centurion"][0]["result"] == "ПОРАЖЕНИЕ"
    assert (player_matches["mafuta"][0]["score_for"],
            player_matches["mafuta"][0]["score_against"]) == (4, 4), "счёт ноги остаётся ничейным"
    assert addon["mafuta"]["pk_w"] == 1
    assert addon["Centurion"]["pk_l"] == 1
    assert addon["mafuta"]["draws"] == 0
    assert addon["Centurion"]["draws"] == 0


def test_исход_перевёрнутой_стороны_не_меняет_победителя():
    player_matches, addon = records({
        "p1": "Dune", "p2": "Mcfly", "s1": 4, "s2": 4, "ot": False, "pk": True,
        "season": "Season 6", "league": "Дворовая лига", "outcome": ["win", "loss"]})
    assert player_matches["Dune"][0]["result"] == "ПОБЕДА"
    assert player_matches["Mcfly"][0]["result"] == "ПОРАЖЕНИЕ"
    assert addon["Dune"]["pk_w"] == 1


def test_честная_ничья_остаётся_ничьей():
    player_matches, addon = records({
        "p1": "Wenderfit", "p2": "Memori", "s1": 3, "s2": 3, "ot": False, "pk": False,
        "season": "Season 1", "league": "Высшая (Единая) лига"})
    assert player_matches["Wenderfit"][0]["result"] == "НИЧЬЯ"
    assert player_matches["Memori"][0]["result"] == "НИЧЬЯ"
    assert addon["Wenderfit"]["draws"] == 1
    assert addon["Memori"]["draws"] == 1
    assert addon["Wenderfit"]["pk_w"] == 0


# --- витрина: таблицы сезона и дуэли считают ту же победу ---

def test_soccer_js_считает_победу_по_исходу_а_не_только_по_счёту():
    """Таблица сезона и дуэли прежде сравнивали только s1/s2: нога с серией не давала победы никому."""
    text = (ROOT / "soccer.js").read_text(encoding="utf-8")
    assert "function matchWinnerSide" in text
    assert not re.search(r"if \(m\.s1 > m\.s2\) stat\.wins", text)
    assert not re.search(r"return isP1Home \? s1 > s2 : s2 > s1", text)
    assert not re.search(r"Number\(m\.s1 \|\| 0\) === Number\(m\.s2 \|\| 0\)\)\.length", text)


# --- приёмка: в собранной базе не осталось ноги с доказанной серией и ничейным исходом ---

def test_ни_одна_нога_с_доказанной_серией_не_осталась_ничьей(db_path):
    import sqlite3

    from db import store
    from portal.comment_origin import series_for_sides

    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in con.execute(
            """select t.season, m.league, m.tour, pa.nick p1, pb.nick p2,
                      sa.score s1, sb.score s2, sa.outcome o1, m.source_text
               from matches m
               join tournaments t on t.id = m.tournament_id
               join match_sides sa on sa.match_id = m.id and sa.side_index = 0
               join match_sides sb on sb.match_id = m.id and sb.side_index = 1
               join side_players a on a.side_id = sa.id
               join side_players b on b.side_id = sb.id
               join players pa on pa.id = a.player_id
               join players pb on pb.id = b.player_id
               where m.row_set = 'catalog' and m.hidden_by is null and m.status <> 'void'
                 and sa.score is not null and sa.score = sb.score""")]
    finally:
        con.close()
    lost = [(r["season"], r["p1"], r["s1"], r["s2"], r["p2"]) for r in rows
            if r["o1"] == "draw" and series_for_sides(r["source_text"], r["s1"], r["s2"],
                                                      r["p1"], r["p2"])]
    assert not lost, f"серия доказана, а исход ничья: {lost}"