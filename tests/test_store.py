"""Точка подключения и миграция схемы: то, на чём держится перенос записи на серверную базу.

`db/store.py` — единственное место, где проект решает, с какой базой он работает. `id` у
`side_players` и `player_aliases` — то, без чего ядро записи не переедет на Postgres: скрытого
rowid там нет. Оба обещания легко потерять при следующей правке, поэтому здесь они проверены
текстом модулей и настоящими срезами базы.

Живой `data/nst.db` не пишется: миграция смотрятся на копиях, сборка — на подменённом
`subprocess.run`.
"""

import ast
import re
import sqlite3
from pathlib import Path

import build_all
import pytest
from db import build_db, edit, store

# Так в коде выглядит путь к базе, собранный самим модулем. В тексте отказов путь печатается
# словами (`"Нет базы data/nst.db"`) — проверка на такие строки не смотрит.
OWNED_PATH = ('ROOT / "data" / "nst.db"', 'Path("data/nst.db")', 'parent.parent / "data"')

# Прежний вид таблиц, который миграция должна пережить. Обратная миграция нужна затем, чтобы
# проверка шла от состояния человека (база собрана прошлой версией кода), а не от свежего файла.
OLD_SHAPE = {
    "player_aliases": """create table player_aliases (
        alias       TEXT PRIMARY KEY,
        player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        source      TEXT
    )""",
    "side_players": """create table side_players (
        side_id     INTEGER NOT NULL REFERENCES match_sides(id) ON DELETE CASCADE,
        player_id   INTEGER NOT NULL REFERENCES players(id),
        seat_index  INTEGER NOT NULL DEFAULT 0,
        primary key (side_id, player_id)
    )""",
}


def _drop_surrogate_key(con, table):
    """Возвращает таблицу к прежнему виду, сохраняя номера строк: rowid в SQLite вписывается прямо."""
    columns = [row[1] for row in con.execute(f"pragma table_info({table})") if row[1] != "id"]
    kept = ", ".join(columns)
    con.execute(f"alter table {table} rename to {table}_old")
    con.execute(OLD_SHAPE[table])
    con.execute(f"insert into {table}(rowid, {kept}) select rowid, {kept} from {table}_old")
    con.execute(f"drop table {table}_old")


def _keyed(con, table):
    """Снимок таблицы вместе с адресом строки: `id`, а в старом виде — rowid."""
    columns = [row[1] for row in con.execute(f"pragma table_info({table})")]
    key = "id" if "id" in columns else "rowid"
    rest = [name for name in columns if name != key]
    return [tuple(row) for row in con.execute(
        f"select {key}, {', '.join(rest)} from {table} order by {key}")]


def test_no_module_opens_the_database_except_store():
    """Ни один модуль не зовёт драйвер сам: иначе Postgres пришлось бы подключать в 26 местах."""
    root = Path(build_all.ROOT)
    offenders = []
    for folder in ("db", "api", "portal"):
        for path in sorted((root / folder).rglob("*.py")):
            if path.name == "store.py":
                continue
            hits = re.findall(r"sqlite3\.\w+\(", path.read_text(encoding="utf-8"))
            if any(call.startswith(("sqlite3.connect", "sqlite3.backup")) for call in hits):
                offenders.append(f"{path.relative_to(root)}: {hits}")
    assert not offenders, "прямые вызовы драйвера остались в " + ", ".join(offenders)


def test_store_import_is_a_statement_and_not_part_of_a_query():
    """Импорт `store` — инструкция, а не подстрочник внутри SQL, и стоит он после `sys.path.insert`.

    Обе ловушки уже случались при механической правке текстов: SQL-строки этих модулей начинаются
    со слов `from` и `import`, а модуль `db` становится видим только после вставки в `sys.path`.
    """
    for path in sorted((Path(build_all.ROOT) / "db").glob("*.py")):
        if path.name == "store.py":
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        textual = [i for i, line in enumerate(lines, 1) if line.startswith("from db import store")]
        if not textual:
            continue
        tree = ast.parse(text)
        real = [node.lineno for node in tree.body if isinstance(node, ast.ImportFrom)
                and node.module == "db" and any(item.name == "store" for item in node.names)]
        assert textual == real, f"{path.name}: импорт есть в тексте ({textual}), но не в коде ({real})"
        seam = [i for i, line in enumerate(lines, 1) if line.startswith("sys.path.insert(")]
        assert not seam or textual[0] > seam[0], f"{path.name}: импорт до sys.path.insert"


def test_default_path_of_every_module_belongs_to_store():
    """Путь по умолчанию один: модули берут его у `store`, а не собирают из `ROOT` сами."""
    for path in sorted((Path(build_all.ROOT) / "db").glob("*.py")):
        if path.name == "store.py":
            continue
        text = path.read_text(encoding="utf-8")
        built = [needle for needle in OWNED_PATH if needle in text]
        assert not built, f"{path.name}: путь к базе собран в обход store — {built}"
        found = re.search(r"^DB_PATH = (.+)$", text, re.MULTILINE)
        if found:
            assert found.group(1).strip() == "store.DB_PATH", f"{path.name}: {found.group(1)}"


def test_connect_without_argument_opens_the_default_file():
    """`store.connect()` без аргумента открывает именно `DB_PATH` — на этом держится режим базы."""
    con = store.connect()
    try:
        assert Path(con.execute("pragma database_list").fetchone()[2]) == store.DB_PATH
    finally:
        con.close()


def test_migration_keeps_row_numbers_including_the_gaps(db_path):
    """Перестройка даёт таблицам `id` и сохраняет прежние номера — снимки журнала не съезжают.

    Разрывы проверяются отдельно: уплотнение номеров выглядело бы невинно, но именно оно
    переадресует все старые записи журнала на чужие строки.
    """
    con = sqlite3.connect(db_path)
    for table in OLD_SHAPE:
        _drop_surrogate_key(con, table)
    victim = con.execute("select rowid from side_players order by rowid limit 1 offset 7").fetchone()[0]
    con.execute("delete from side_players where rowid = ?", (victim,))
    before = {table: _keyed(con, table) for table in OLD_SHAPE}

    build_db.apply_schema(con)

    for table in OLD_SHAPE:
        columns = [row[1] for row in con.execute(f"pragma table_info({table})")]
        assert columns[0] == "id", f"{table}: id должен быть первой колонкой, получилось {columns}"
        assert _keyed(con, table) == before[table], f"{table}: разъехались номера или содержимое"
    ids = [row[0] for row in _keyed(con, "side_players")]
    assert victim not in ids, "миграция придумала строку на месте удалённой"
    assert max(ids) - len(ids) > 0, "номера уплотнились — проверка разрывов теряет смысл"
    assert not con.execute("pragma foreign_key_check").fetchall()
    assert con.execute("select count(*) from v_rating_pool").fetchone()[0] > 0
    con.close()


def test_apply_schema_is_idempotent_after_migration(db_path):
    """Второй прогон схемы не двигает ни строк, ни номеров: он случается на каждой сборке сайта."""
    con = sqlite3.connect(db_path)
    _drop_surrogate_key(con, "side_players")
    build_db.apply_schema(con)
    once = _keyed(con, "side_players")
    build_db.apply_schema(con)
    assert _keyed(con, "side_players") == once
    con.close()


def test_fresh_database_matches_the_migrated_one(db_path):
    """Свежая база из схемы и база после миграции совпадают колонками, ключами и типами."""
    migrated = sqlite3.connect(db_path)
    for table in OLD_SHAPE:
        _drop_surrogate_key(migrated, table)
    build_db.apply_schema(migrated)
    fresh = sqlite3.connect(":memory:")
    build_db.apply_schema(fresh)  # тем же путём, что и сборка: тело, шаги, вьюхи
    for table in OLD_SHAPE:
        assert [tuple(row) for row in fresh.execute(f"pragma table_info({table})")] == \
            [tuple(row) for row in migrated.execute(f"pragma table_info({table})")], table
    migrated.close()
    fresh.close()


def test_journal_addresses_restored_roster_rows_by_their_own_id(db_path, find):
    """Слияние игроков возвращает строки состава под теми же id — ровно то, ради чего они появились."""
    con = edit.connect(db_path)
    keep, drop = find("""
        select a.id, b.id from players a join players b on a.id < b.id
        where (select count(*) from side_players sp where sp.player_id = a.id) between 1 and 3
          and (select count(*) from side_players sp where sp.player_id = b.id) between 1 and 3
          and not exists (select 1 from match_sides sa
             join side_players spa on spa.side_id = sa.id
             join match_sides sb on sb.match_id = sa.match_id and sb.side_index <> sa.side_index
             join side_players spb on spb.side_id = sb.id
             where spa.player_id = a.id and spb.player_id = b.id)
        order by a.id, b.id limit 1""", what="двое, кто не играл друг против друга")
    seats = sorted(row[0] for row in con.execute(
        "select id from side_players where player_id = ?", (drop,)))
    assert seats, "слияние проверяется на игроке, у которого есть строки состава"

    edit.merge_player(con, keep, drop, "тест")
    edit.undo(con, "last")

    assert sorted(row[0] for row in con.execute(
        "select id from side_players where player_id = ?", (drop,))) == seats
    con.close()


def _record_runs(monkeypatch):
    called = []
    def _run(command, **kwargs):
        called.append(Path(command[1]).relative_to(build_all.ROOT).as_posix())
    monkeypatch.setattr(build_all.subprocess, "run", _run)
    return called


def test_from_store_skips_the_steps_that_regenerate_the_database(monkeypatch):
    """`--from-store` не зовёт пересборку среза, но валидацию и страницы собирает: правки живы."""
    called = _record_runs(monkeypatch)
    build_all.build_pages(from_store=True)
    assert not set(build_all.STORE_STEPS) & set(called), f"пересборка базы всё же звалась: {called}"
    assert "db/validate.py" in called and "build_nekketsu_portal_v2.py" in called


def test_plain_build_still_regenerates_the_store(monkeypatch):
    """Обычный прогон остаётся обычным: без флага сборка по-прежнему пересобирает срез."""
    called = _record_runs(monkeypatch)
    build_all.build_pages()
    assert set(build_all.STORE_STEPS) <= set(called)


def test_from_store_refuses_without_a_database(tmp_path, monkeypatch):
    """Среза нет — отказ с объяснением, а не молчаливая сборка сайта из пустой базы."""
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "нет-такой-базы.db")
    monkeypatch.setattr(build_all.subprocess, "run",
                        lambda command, **kwargs: pytest.fail("без базы собирать нечего"))
    monkeypatch.setattr(build_all.sys, "argv", ["build_all.py", "--from-store"])
    with pytest.raises(SystemExit) as refused:
        build_all.main()
    assert "--from-store" in str(refused.value)
