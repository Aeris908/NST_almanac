"""Кандидатов на склейку «страница ↔ рейтинговый пул» — в очередь на просмотр.

Автоматически эти пары не склеиваются. Причина: источники подписывают раунд по-разному
(каталог: «Высшая лига / Плей-офф / Кубок», пул: «Кубок лиг / 1/4 финала»), а в кубковой
серии одна и та же пара может выдать одинаковый счёт дважды — совпадение пары и счёта
доказательством «это одна игра» не является. Решает редактор, поэтому пары лежат в `incoming`
с вердиктом `conflict`, а не в `duplicate_of`.
"""

import json
import sys
from pathlib import Path
from db import store

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = store.DB_PATH
BATCH = "twins_2026-11-03"

ROWS_SQL = """
select m.id, t.season, t.name, s.name, m.tour, pa.nick, sa.score, sb.score, pb.nick, m.row_set, m.duplicate_of
from matches m
join tournaments t on t.id = m.tournament_id
join stages s on s.id = m.stage_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
join side_players a on a.side_id = sa.id
join side_players b on b.side_id = sb.id
join players pa on pa.id = a.player_id
join players pb on pb.id = b.player_id
where (select count(*) from side_players sp where sp.side_id = sa.id) = 1
  and (select count(*) from side_players sp where sp.side_id = sb.id) = 1
"""


def signature(row):
    return (row[1], tuple(sorted([f"{row[5]}|{row[6]}", f"{row[7]}|{row[8]}"])))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    con = store.connect(DB_PATH)
    rows = list(con.execute(ROWS_SQL))
    pool = {}
    for row in rows:
        if row[9] == "pool":
            pool.setdefault(signature(row), row[0])

    candidates = [
        (row, pool[signature(row)])
        for row in rows
        if row[9] == "catalog" and row[10] is None and signature(row) in pool
    ]

    con.execute("delete from incoming where batch = ?", (BATCH,))
    by_id = {row[0]: row for row in rows}
    for catalog_row, pool_row in candidates:
        twin = by_id[pool_row]
        con.execute(
            "insert into incoming(batch, source, source_ref, payload, verdict, matched_match_id)"
            " values (?, 'catalog', ?, ?, 'conflict', ?)",
            (BATCH, str(catalog_row[0]), json.dumps({
                "catalog_id": catalog_row[0],
                "pool_id": pool_row,
                "catalog_label": f"{catalog_row[2]} / {catalog_row[4] or catalog_row[3]}",
                "pool_label": f"{twin[2]} / {twin[3]}",
                "match": f"{catalog_row[5]} {catalog_row[6]}:{catalog_row[7]} {catalog_row[8]}",
            }, ensure_ascii=False), pool_row),
        )
    con.commit()
    print(f"пар-кандидатов на просмотр: {len(candidates)} (batch {BATCH})")
    for catalog_row, pool_row in candidates:
        twin = by_id[pool_row]
        print(f"   {catalog_row[1]} | страница: {catalog_row[2]} / {catalog_row[4] or catalog_row[3]}"
              f" (id {catalog_row[0]}) ↔ пул: {twin[2]} / {twin[3]} (id {pool_row}) | "
              f"{catalog_row[5]} {catalog_row[6]}:{catalog_row[7]} {catalog_row[8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
