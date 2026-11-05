"""Наполнение единой базы матчей: current pool (Sportcup-снапшот + рукописные блоки) -> data/nst.db.

Идемпотентно: повторный запуск ничего не дублирует (ключ — source + source_ref).
``--rebuild`` пересоздаёт файл базы и отказывается это делать, если в базе есть правки.
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_final_analytics as bfa  # noqa: E402
from db.fields import phase_of  # noqa: E402
from portal.name_tables import ALIAS_MAP  # noqa: E402
from db import store  # noqa: E402

DB_PATH = store.DB_PATH
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

KNOCKOUT_ORDER = [
    bfa.REGULAR_STAGE, "1/32 финала", "1/16 финала", "1/8 финала", "1/4 финала",
    "1/2 финала", "Финал", "Финал Кубка", "Малый финал",
]


def slugify(nick):
    """'RVD (МГБ)' -> 'rvd-mgb'; 'Сokol 9' -> 'sokol-9'. Только для ссылок в UI."""
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9а-яё]+", "-", nick.lower())).strip("-")


def stage_order(name):
    return KNOCKOUT_ORDER.index(name) if name in KNOCKOUT_ORDER else len(KNOCKOUT_ORDER)


VIEW_MARKER = "-- === views ==="
STEP_MARKER = "-- === steps ==="
VIEWS = ("v_singles_pool", "v_rating_pool")
# Для шага достройки существующей базы это значит «уже сделано», а не поломку.
HARMLESS = ("duplicate column name", "already exists")
# Таблицы без `id`: строка журнала правок адресовала их по скрытому SQLite rowid, а у Postgres
# такого понятия нет. Им выдаётся обычный id, и адресация в db/edit.py становится одинаковой
# на обоих движках.
SURROGATE_KEY_TABLES = ("side_players", "player_aliases")


def apply_steps(con, steps):
    """Достаёт из секции «steps» то, чего в базе ещё нет: новые таблицы и новые колонки."""
    for statement in (part.strip() for part in steps.split(";")):
        if not statement:
            continue
        try:
            con.execute(statement)
        except sqlite3.OperationalError as error:
            if not any(marker in str(error) for marker in HARMLESS):
                raise


def table_ddl(body, table):
    """Описание таблицы из db/schema.sql — оно же источник для перестройки на месте."""
    found = re.search(rf"CREATE TABLE {table} \(.*?\n\);", body, re.IGNORECASE | re.DOTALL)
    if not found:
        raise RuntimeError(f"в db/schema.sql не нашлось описания таблицы {table}")
    return found.group(0)


def ensure_surrogate_keys(con, body):
    """Перестраивает таблицы без `id`, если схема уже требует его.

    `alter table add column` не умеет добавлять PRIMARY KEY, поэтому таблица собирается заново
    из актуального описания, а строки переезжают под своими прежними номерами: `rowid`
    становится `id`, и старые снимки журнала продолжают указывать на те же строки. Идемпотентно —
    если `id` уже на месте, вызов ничего не делает.
    """
    for table in SURROGATE_KEY_TABLES:
        columns = [row[1] for row in con.execute(f"pragma table_info({table})")]
        if not columns or "id" in columns:
            continue
        kept = ", ".join(columns)
        con.execute(f"alter table {table} rename to {table}_mig")
        con.execute(table_ddl(body, table))
        con.execute(f"insert into {table}(id, {kept}) select rowid, {kept} from {table}_mig")
        con.execute(f"drop table {table}_mig")


def apply_schema(con):
    """Схема применяется в обоих состояниях базы: тело — при первой сборке, секции «steps»,
    достройка id и вьюхи — всегда. Поэтому правка схемы не требует `--rebuild` и не выбрасывает
    правки редактора вместе со старым файлом."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    body, rest = schema.split(STEP_MARKER, 1)
    steps, views = rest.split(VIEW_MARKER, 1)
    if not con.execute(
        "select count(*) from sqlite_master where type = 'table' and name = 'matches'"
    ).fetchone()[0]:
        con.executescript(body)
    # Вьюхи падают на `no such table`, если их переживёт перестройка таблицы, поэтому снимаются
    # до шагов и собираются после — порядок, а не экономия: они пересоздаются всегда.
    con.executescript("".join(f"drop view if exists {name};\n" for name in VIEWS))
    apply_steps(con, steps)
    ensure_surrogate_keys(con, body)
    con.executescript(views)


def open_db(path, rebuild=False):
    if rebuild and path.exists():
        con = store.connect(path)
        # Отменённая правка — уже не правка: её откат вернул строке состояние носителя, и терять
        # при пересборке нечего. Живая запись журнала, наоборот, блокирует пересоздание файла.
        live = con.execute("select count(*) from corrections where reverted_at is null").fetchone()[0]
        con.close()
        if live:
            sys.exit(f"В базе {live} действующих записей журнала правок — пересоздание уничтожит их. "
                     f"Отмените их (`python db/edit.py undo last`) либо сделайте резервную копию файла.")
        path.unlink()
    con = store.connect(path)
    apply_schema(con)
    return con


def ensure_player(con, nick, cache, kind="player"):
    if nick in cache:
        return cache[nick]
    existing = con.execute("select id from players where nick = ?", (nick,)).fetchone()
    if existing:
        cache[nick] = existing[0]
        return existing[0]
    slug = slugify(nick)
    clash = con.execute("select nick from players where slug = ?", (slug,)).fetchone()
    if clash:
        sys.exit(f"Ник «{nick}» даёт тот же slug, что и «{clash[0]}» ({slug}). "
                 f"Придумайте различающиеся slug — иначе ссылки в UI будут врать.")
    con.execute("insert into players(slug, nick, kind) values (?, ?, ?)", (slug, nick, kind))
    player_id = con.execute("select id from players where slug = ?", (slug,)).fetchone()[0]
    cache[nick] = player_id
    return player_id


def ensure_tournament(con, name, season, cache, kind=None):
    if name in cache:
        return cache[name]
    if kind is None:
        kind = "cup" if bfa.CUP_TOURNAMENT in name else "league"
    con.execute(
        "insert or ignore into tournaments(discipline_id, season, kind, name) values (1, ?, ?, ?)",
        (season, kind, name),
    )
    tournament_id = con.execute(
        "select id from tournaments where season = ? and kind = ? and name = ?", (season, kind, name)
    ).fetchone()[0]
    cache[name] = tournament_id
    return tournament_id


def ensure_stage(con, tournament_id, name, cache):
    if (tournament_id, name) in cache:
        return cache[(tournament_id, name)]
    con.execute("insert or ignore into stages(tournament_id, name, order_index) values (?, ?, ?)",
                (tournament_id, name, stage_order(name)))
    stage_id = con.execute("select id from stages where tournament_id = ? and name = ?",
                           (tournament_id, name)).fetchone()[0]
    cache[(tournament_id, name)] = stage_id
    return stage_id


def side_outcomes(row):
    """(outcome0, outcome1) по сторонам: технический результат — у проигравшего нет зачёта."""
    if row.get("is_technical"):
        loser_is_first = row.get("technical_loser") == row["p1"]
        return ("none", "win") if loser_is_first else ("win", "none")
    if row["s1"] > row["s2"]:
        return "win", "loss"
    if row["s1"] < row["s2"]:
        return "loss", "win"
    return "draw", "draw"


def import_pool(con, pool):
    players, tournaments, stages = {}, {}, {}
    added = skipped = 0
    for index, row in enumerate(pool):
        if con.execute("select 1 from matches where source = ? and source_ref = ?",
                       (row["source"], row["source_ref"])).fetchone():
            skipped += 1
            continue
        tournament_id = ensure_tournament(con, row["tournament"], row["season"], tournaments)
        stage_id = ensure_stage(con, tournament_id, row.get("stage", bfa.REGULAR_STAGE), stages)
        p1_id = ensure_player(con, row["p1"], players)
        p2_id = ensure_player(con, row["p2"], players)
        outcome1, outcome2 = side_outcomes(row)
        con.execute(
            "insert into matches(tournament_id, stage_id, is_playoff, phase, order_in_source, status,"
            " in_rating_pool, row_set, source, source_ref, note) values (?, ?, ?, ?, ?, ?, 1, 'pool', ?, ?, ?)",
            (tournament_id, stage_id, int(bool(row.get("is_playoff"))), phase_of(row), index,
             "technical" if row.get("is_technical") else "played",
             row["source"], row["source_ref"], row.get("note", "")),
        )
        match_id = con.execute("select last_insert_rowid()").fetchone()[0]
        for side_index, (player_id, score, outcome) in enumerate(
            [(p1_id, row["s1"], outcome1), (p2_id, row["s2"], outcome2)]
        ):
            con.execute("insert into match_sides(match_id, side_index, outcome, score) values (?, ?, ?, ?)",
                        (match_id, side_index, outcome, score))
            side_id = con.execute("select last_insert_rowid()").fetchone()[0]
            con.execute("insert into side_players(side_id, player_id) values (?, ?)", (side_id, player_id))
        added += 1
    return added, skipped


def import_aliases(con):
    """Из справочника нормализации: чем источники называют тех же игроков."""
    nicks = dict(con.execute("select nick, id from players"))
    inserted = 0
    for alias, canonical in sorted(ALIAS_MAP.items()):
        player_id = nicks.get(canonical)
        if player_id is None:
            continue
        con.execute("insert or ignore into player_aliases(alias, player_id, source) VALUES (?, ?, 'name_tables')",
                    (alias, player_id))
        inserted += 1
    return inserted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="пересоздать файл базы с нуля")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    con = open_db(DB_PATH, rebuild=args.rebuild)
    con.execute("insert or ignore into disciplines(id, slug, name) values (1, 'soccer', 'Футбол Goal 3')")

    pool = bfa.all_matches
    added, skipped = import_pool(con, pool)
    aliases = import_aliases(con)
    con.commit()

    stored = con.execute("select count(*) from matches").fetchone()[0]
    people = con.execute("select count(*) from players").fetchone()[0]
    print(f"{DB_PATH}: добавлено {added}, уже было {skipped}, всего матчей {stored} | "
          f"игроков {people}, алиасов {aliases}")


if __name__ == "__main__":
    main()
