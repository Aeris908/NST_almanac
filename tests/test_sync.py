"""Перенос среза: успешное чтение и откат без доступа к облачной базе."""

import re
import shutil

import pytest

from db import api, store, sync


class Remote:
    """Источник строк для pull; снимок берётся из отдельного SQLite-файла."""

    def __init__(self, path, fail_table=None, corrupt=False):
        self.con = store.connect(path)
        self.fail_table = fail_table
        self.corrupt = corrupt

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.con.close()

    def cursor(self):
        return self

    def execute(self, sql):
        if sql.startswith("SET TRANSACTION"):
            return
        table = re.search(r'FROM "(\w+)"', sql)[1]
        if table == self.fail_table:
            raise RuntimeError("обрыв чтения")
        self.rows = self.con.execute(sql).fetchall()
        if table == "player_aliases" and self.corrupt:
            self.rows = [(row[0], row[1], -999, row[3]) for row in self.rows]

    def fetchall(self):
        return self.rows


def contents(path):
    con = store.connect(path)
    try:
        return {table: con.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()
                for table in sync.TABLES_ORDER}
    finally:
        con.close()


@pytest.mark.parametrize("fail_table,corrupt", [(None, False), ("match_sides", False), (None, True)])
def test_pull_preserves_complete_snapshot_or_rolls_back(db_path, tmp_path, monkeypatch,
                                                       fail_table, corrupt):
    remote_path = tmp_path / "remote.db"
    shutil.copy(db_path, remote_path)
    con = store.connect(remote_path)
    con.execute("UPDATE players SET nick = nick || ' (сервер)' WHERE id = (SELECT min(id) FROM players)")
    con.commit()
    con.close()
    before = contents(db_path)
    expected = contents(remote_path)
    monkeypatch.setattr(sync.psycopg, "connect",
                        lambda _: Remote(remote_path, fail_table, corrupt))
    if fail_table or corrupt:
        with pytest.raises((RuntimeError, ValueError)):
            sync.pull(db_path, "postgresql://test")
        assert contents(db_path) == before
    else:
        sync.pull(db_path, "postgresql://test")
        assert contents(db_path) == expected


def test_push_does_not_commit_truncate_before_copy_finishes(db_path, monkeypatch):
    class BrokenDestination:
        commits = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def cursor(self):
            return self

        def execute(self, sql):
            pass

        def executemany(self, sql, rows):
            raise RuntimeError("обрыв записи")

        def commit(self):
            self.commits += 1

    remote = BrokenDestination()
    monkeypatch.setattr(sync.psycopg, "connect", lambda _: remote)
    with pytest.raises(RuntimeError, match="обрыв записи"):
        sync.push(db_path, "postgresql://test")
    assert remote.commits == 0


def test_postgres_preview_clones_server_rows(db_path, tmp_path, monkeypatch):
    remote_path = tmp_path / "remote.db"
    shutil.copy(db_path, remote_path)
    con = store.connect(remote_path)
    con.execute("UPDATE players SET nick = 'Серверный ник' WHERE id = (SELECT min(id) FROM players)")
    con.commit()
    con.close()
    monkeypatch.setattr(store, "DB_PATH", db_path)
    monkeypatch.setattr(sync.psycopg, "connect", lambda _: Remote(remote_path))
    before = contents(db_path)
    with api._preview_db("postgresql://test") as clone:
        assert contents(clone) == contents(remote_path)
        assert contents(clone) != before
    assert contents(db_path) == before
    assert not clone.exists()


def test_pull_cli_dispatches(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(sync, "pull", lambda *args: calls.append(args))
    sync.main(["pull", "--sqlite", "local.db", "--url", "postgresql://test"])
    assert calls == [("local.db", "postgresql://test")]
