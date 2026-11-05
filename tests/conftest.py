"""Общая обвязка тестов на правку базы: копия боевой базы на каждый тест.

Живой `data/nst.db` тесты не трогают вообще — `edit.connect` открывает копию во временном каталоге, и операция,
которая что-то сломает, останется внутри одного теста. Копия стоит доли секунды (база ~2 МБ),
поэтому соблашна «открыть одну базу на весь прогон» сознательно не было: общее соединение прятало
бы следы правки между тестами.

Строки ищутся свойствами («матч с двумя числами и без дубля»), а не фиксированными id: id
пересоздаёт каждая сборка, и тест с номером строки протух бы в тот день, когда он нужнее всего.
"""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import edit  # noqa: E402

LIVE_DB = ROOT / "data" / "nst.db"
# `updated_at` правка меняет всегда (журнал его пишется), поэтому в сверку «до ↔ после откатa»
# он входить не должен — иначе каждый тест падал бы на колонке, которая и не обещала возврата.
VOLATILE = {"updated_at"}
# Состав стороны восстанавливается пересборкой (`resync_rosters`), и rowid у строк при этом
# новые: сравнивается набор «сторона + игрок + место», а возврат rowid проверяет отдельный тест.
KEYLESS = {"side_players"}
FINGERPRINT_TABLES = ("tournaments", "stages", "players", "player_aliases", "tournament_docs",
                      "matches", "match_sides", "side_players", "match_links")


@pytest.fixture(scope="session")
def source_db():
    if not LIVE_DB.exists():
        pytest.skip(f"нет {LIVE_DB.relative_to(ROOT)} — сначала python build_all.py")
    return LIVE_DB


@pytest.fixture
def db_path(tmp_path, source_db):
    target = tmp_path / "nst.db"
    shutil.copy(source_db, target)
    return target


@pytest.fixture
def con(db_path):
    connection = edit.connect(db_path)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def find(con):
    """Первая строка по запросу или честный skip: «в базе нет такого» — не «тест упал»."""
    def _find(sql, params=(), what="нужная строка"):
        row = con.execute(sql, params).fetchone()
        if row is None:
            pytest.skip(f"в копии базы нет: {what}")
        return row[0] if len(row) == 1 else tuple(row)
    return _find


@pytest.fixture
def fingerprint(con):
    def _fingerprint():
        state = {}
        for table in FINGERPRINT_TABLES:
            columns = [row[1] for row in con.execute(f"pragma table_info({table})")
                       if row[1] not in VOLATILE]
            # rowid везде, кроме таблиц с составным ключом: он ловит и «строка уехала», и
            # «строка вернулась под другим номером» после отката удаления.
            selected = columns if table in KEYLESS else ["rowid"] + columns
            rows = con.execute(f"select {', '.join(selected)} from {table}").fetchall()
            # `str(Row)` печатает адрес объекта, а не значения: снимать надо в tuple.
            state[table] = sorted(str(tuple(row)) for row in rows)
        return state
    return _fingerprint


@pytest.fixture
def unchanged():
    """Сравнение двух снимков с коротким отчётом: на таком объёме данных pytest печатает
    «Full output truncated», а человеку нужна таблица и пара разъехавшихся строк."""
    def _unchanged(before, after):
        if before == after:
            return
        for table in before:
            if before[table] == after[table]:
                continue
            gone = [row for row in before[table] if row not in after[table]][:3]
            fresh = [row for row in after[table] if row not in before[table]][:3]
            raise AssertionError(f"расхождение в {table}: пропало {gone}, появилось {fresh}")
        raise AssertionError("наборы таблиц различаются, хотя каждая таблица совпала")
    return _unchanged


@pytest.fixture
def undone(con, fingerprint, unchanged):
    """Откат последней операции и сверка: база ровно такая, какой была до правки.

    `manual` и `roster` снимаются самим откатом (`release_unedited`), поэтому возврат сверяется
    по всему срезу данных, а не по одному полю.
    """
    def _undone(before):
        result = edit.undo(con, "last")
        assert result["entries"], "откатывать нечего: операция не записала ни одного поля"
        assert con.execute(
            "select count(*) from corrections where reverted_at is null").fetchone()[0] == 0
        unchanged(fingerprint(), before)
        return result
    return _undone
