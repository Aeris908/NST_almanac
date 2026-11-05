"""Закрывает пары «матч рейтингового пула ↔ та же игра, показанная на странице» по uuid.

Склейка не угадывание: `portal.match_catalog.from_sportcup_api` — это проекция пула, строка
в строку, что проверено ниже пофамильно и посчётно. Поэтому k-я строка страницы из Сезона 8/9
соответствует k-й строке пула того же сезона, и uuid берётся из снапшота, а не из похожести
счёта (одинаковые счета в сериях — главная причина, почему «похожесть» для склейки не годится).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build_final_analytics as bfa  # noqa: E402
from portal.match_catalog import from_sportcup_api  # noqa: E402
from db import store  # noqa: E402

DB_PATH = store.DB_PATH
SEASONS = ("Season 8", "Season 9")


def projected_pool():
    """Сезон -> [(uuid, ник-1, ник-2, счёт-1, счёт-2)] в том же порядке, что идёт пул."""
    by_season = {season: [] for season in SEASONS}
    for row in bfa.all_matches:
        if row["season"] not in SEASONS:
            continue
        projected = from_sportcup_api([row])
        if not projected:
            continue
        page_row = projected[0]
        by_season[page_row["season"]].append(
            (row["source_ref"], page_row["p1"], page_row["p2"], page_row["s1"], page_row["s2"])
        )
    return by_season


def page_rows_by_season(con):
    """Страницы, пришедшие из Sportcup, в порядке импорта: candidate-строки для склейки.

    Уже помеченные дублями тоже берём: для этих сезонов uuid — старшинство, и склейка по
    общему посту могла указать не на ту строку (главное — чтобы указала на пуловую).
    """
    rows = con.execute(
        """
        select m.id, t.season, pa.nick, pb.nick, sa.score, sb.score, m.duplicate_of
        from matches m
        join tournaments t on t.id = m.tournament_id
        join match_sides sa on sa.match_id = m.id and sa.side_index = 0
        join match_sides sb on sb.match_id = m.id and sb.side_index = 1
        join side_players a on a.side_id = sa.id
        join side_players b on b.side_id = sb.id
        join players pa on pa.id = a.player_id
        join players pb on pb.id = b.player_id
        where m.source = 'sportcup_api' and m.in_rating_pool = 0
          and (select count(*) from side_players sp where sp.side_id = sa.id) = 1
          and (select count(*) from side_players sp where sp.side_id = sb.id) = 1
        order by m.order_in_source
        """
    ).fetchall()
    grouped = {season: [] for season in SEASONS}
    for match_id, season, n1, n2, s1, s2, existing_dup in rows:
        if season in grouped:
            grouped[season].append((match_id, n1, n2, s1, s2, existing_dup))
    return grouped


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    con = store.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")

    pool_by_uuid = dict(con.execute(
        "select source_ref, id from matches where in_rating_pool = 1 and source_ref is not null"))
    projected = projected_pool()
    on_page = page_rows_by_season(con)

    closed = reassigned = skipped = 0
    for season in SEASONS:
        want, have = projected[season], on_page[season]
        if len(want) != len(have):
            print(f"{season}: расхождение длины — пул {len(want)}, страница {len(have)}; сезон не тронут")
            skipped += len(have)
            continue
        for (uuid, p1, p2, s1, s2), (match_id, n1, n2, t1, t2, existing_dup) in zip(want, have):
            if (p1, p2, s1, s2) != (n1, n2, t1, t2):
                print(f"{season}: позиция не сходится ({p1} {s1}:{s2} {p2} vs {n1} {t1}:{t2}) — пропуск")
                skipped += 1
                continue
            pool_id = pool_by_uuid.get(uuid)
            if pool_id is None:
                print(f"{season}: в базе нет строки пула с uuid {uuid} — пропуск")
                skipped += 1
                continue
            if existing_dup is not None and existing_dup != pool_id:
                reassigned += 1
            con.execute("update matches set duplicate_of = ?, source_locator = coalesce(source_locator,"
                        " 'uuid:' || ?) where id = ?", (pool_id, uuid, match_id))
            closed += 1

    con.commit()
    total = con.execute("select count(*) from matches").fetchone()[0]
    dup = con.execute("select count(*) from matches where duplicate_of is not null").fetchone()[0]
    open_page = con.execute(
        "select count(*) from matches where in_rating_pool = 0 and duplicate_of is null").fetchone()[0]
    print(f"\nсклеено пар по uuid: {closed} (переназначено прежних склеек: {reassigned}) | не склеено: {skipped}")
    print(f"строк {total}, из них помечено дублями {dup}, уникальных {total - dup} (матчей страницы без дубля: {open_page})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
