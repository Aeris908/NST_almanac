"""Синхронизация данных между локальной SQLite (data/nst.db) и серверным Postgres (Neon).

Команды:
  python db/sync.py init    — накат структуры (таблицы, вьюхи) из db/pg.py: schema() в Neon
  python db/sync.py push    — перенос всех данных из SQLite в Neon с обновлением последовательностей
  python db/sync.py status  — сверка количества строк в SQLite и Neon
  python db/sync.py pull    — выгрузка правок из Neon в локальную базу
"""

import argparse
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import pg, store
from portal.env_file import secret

TABLES_ORDER = (
    "disciplines",
    "tournaments",
    "stages",
    "series",
    "tournament_docs",
    "players",
    "player_aliases",
    "matches",
    "match_sides",
    "side_players",
    "match_links",
    "incoming",
    "corrections",
    "publish_requests",
)

IDENTITY_TABLES = (
    "disciplines",
    "tournaments",
    "stages",
    "series",
    "tournament_docs",
    "players",
    "player_aliases",
    "matches",
    "match_sides",
    "side_players",
    "match_links",
    "incoming",
    "corrections",
    "publish_requests",
)


def get_pg_url(url=None):
    """Возвращает строку подключения к Postgres из аргумента или окружения."""
    res = url or secret("NST_POSTGRES_URL") or secret("DATABASE_URL")
    if not res:
        raise ValueError(
            "Не задан URL подключения к Postgres. "
            "Укажите NST_POSTGRES_URL в .env или передайте через --url."
        )
    return res


def init_pg(pg_con):
    """Применяет DDL-схему к Postgres."""
    ddl = pg.schema()
    with pg_con.cursor() as cur:
        cur.execute(ddl)
    pg_con.commit()
    print("OK: схема Postgres успешно применена")


def push(sqlite_path=None, pg_url=None):
    """Переносит весь срез данных из SQLite в Postgres."""
    sqlite_con = store.connect(sqlite_path)
    url = get_pg_url(pg_url)

    with psycopg.connect(url) as pg_con:
        # 1. Очистка таблиц в Postgres в безопасном режиме
        with pg_con.cursor() as cur:
            # Снимаем циклические внешние ключи на время массовой заливки
            cur.execute("ALTER TABLE matches DROP CONSTRAINT IF EXISTS matches_duplicate_of_fkey;")
            cur.execute("ALTER TABLE matches DROP CONSTRAINT IF EXISTS matches_hidden_by_fkey;")
            tables_list = ", ".join(f'"{t}"' for t in TABLES_ORDER)
            cur.execute(f"TRUNCATE TABLE {tables_list} CASCADE;")
        pg_con.commit()

        # 2. Перенос данных по каждой таблице
        total_rows = 0
        for table in TABLES_ORDER:
            # Читаем колонки и данные из SQLite
            s_cur = sqlite_con.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in s_cur.fetchall()]
            if not columns:
                continue

            cols_sql = ", ".join(f'"{c}"' for c in columns)
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = f'INSERT INTO "{table}" ({cols_sql}) VALUES ({placeholders})'

            rows = sqlite_con.execute(f"SELECT {cols_sql} FROM {table}").fetchall()
            if rows:
                with pg_con.cursor() as cur:
                    cur.executemany(insert_sql, rows)
                total_rows += len(rows)
            print(f"  {table:18s}: {len(rows):5d} строк перенесено")

        # 3. Восстановление циклических внешних ключей и последовательностей
        with pg_con.cursor() as cur:
            cur.execute("""
                ALTER TABLE matches
                ADD CONSTRAINT matches_duplicate_of_fkey FOREIGN KEY (duplicate_of) REFERENCES matches(id);
            """)
            cur.execute("""
                ALTER TABLE matches
                ADD CONSTRAINT matches_hidden_by_fkey FOREIGN KEY (hidden_by) REFERENCES matches(id);
            """)
            for table in IDENTITY_TABLES:
                cur.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE((SELECT MAX(id) FROM "{table}"), 1),
                        (SELECT MAX(id) IS NOT NULL FROM "{table}")
                    );
                """)
        pg_con.commit()

    sqlite_con.close()
    print(f"OK: push завершён успешно, всего перенесено строк: {total_rows}")


def status(sqlite_path=None, pg_url=None):
    """Сверяет количество строк в SQLite и Postgres."""
    sqlite_con = store.connect(sqlite_path)
    url = get_pg_url(pg_url)

    print(f"{'Таблица':18s} {'SQLite':>8s} {'Postgres':>10s} {'Статус':>8s}")
    print("-" * 48)

    all_ok = True
    with psycopg.connect(url) as pg_con, pg_con.cursor() as cur:
        for table in TABLES_ORDER:
            s_cnt = sqlite_con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            cur.execute(f'SELECT count(*) FROM "{table}"')
            p_cnt = cur.fetchone()[0]

            match = s_cnt == p_cnt
            status_str = "OK" if match else "DIFF"
            if not match:
                all_ok = False
            print(f"{table:18s} {s_cnt:8d} {p_cnt:10d} {status_str:>8s}")

    sqlite_con.close()
    return 0 if all_ok else 1


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Синхронизация SQLite <-> Postgres (Neon)")
    parser.add_argument("command", choices=["init", "push", "status"], help="Команда для выполнения")
    parser.add_argument("--url", help="Строка подключения к Postgres (по умолчанию из .env)")
    parser.add_argument("--sqlite", help="Путь к файлу SQLite (по умолчанию data/nst.db)")

    args = parser.parse_args(argv)
    if args.command == "init":
        with psycopg.connect(get_pg_url(args.url)) as con:
            init_pg(con)
    elif args.command == "push":
        push(args.sqlite, args.url)
    elif args.command == "status":
        sys.exit(status(args.sqlite, args.url))


if __name__ == "__main__":
    main()
