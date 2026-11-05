"""Доказанные тождества «строка Кубка лиг ↔ матч рейтингового пула».

Кубок Сезонов 2–7 описан в архиве двумя человеческими списками: таблицей игр (справочник
`portal/cup_tables.py`, он же питает строки страницы) и перечнем ног в рейтинговом пуле
(`HISTORICAL_MATCHES`). Часть игр в них — одна и та же игра, и это видно по «сезон + пара + счёт
+ тур». Такие пары склеиваются: строка страницы получает `duplicate_of` на матч пула.

Склейка ничего не меняет в числах: `duplicate_of` — запись о том, что игра в базе уже есть,
витрину она не прячет (для этого есть `hidden_by`), а в Elo по-прежнему считает пуловая строка.
Меняется только очередь просмотра: доказанные пары из неё уходят, а недоказанные остаются — их
слишком много, чтобы угадывать. В кубковой серии одна и та же пара реально может дважды выдать
один и тот же счёт в разных раундах, поэтому несовпадение подписи раунда — стоп-сигнал.
"""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.names import clean_alias  # noqa: E402

DB_PATH = ROOT / "data" / "nst.db"
CUP_SEASONS = tuple(f"Season {n}" for n in range(2, 8))
CUP_SOURCE = "cup_tables"

LEGS_SQL = """
select m.id, t.season, coalesce(m.tour, s.name) as round,
       coalesce(sa.label, (select p.nick from side_players sp join players p on p.id = sp.player_id
                            where sp.side_id = sa.id limit 1)) as a,
       coalesce(sb.label, (select p.nick from side_players sp join players p on p.id = sp.player_id
                            where sp.side_id = sb.id limit 1)) as b,
       sa.score as s1, sb.score as s2, m.duplicate_of
from matches m
join tournaments t on t.id = m.tournament_id
join stages s on s.id = m.stage_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
where t.season in ({seasons}) and {which}
  and (select count(*) from side_players sp where sp.side_id = sa.id) = 1
  and (select count(*) from side_players sp where sp.side_id = sb.id) = 1
"""

PAGE_SQL = LEGS_SQL.format(seasons="?," * (len(CUP_SEASONS) - 1) + "?", which=f"m.source = '{CUP_SOURCE}'")
POOL_SQL = LEGS_SQL.format(seasons="?," * (len(CUP_SEASONS) - 1) + "?", which="m.in_rating_pool = 1")


def side(name):
    return (clean_alias(name) or name or "").strip().lower()


def signature(leg):
    """Пара без порядка + счёт без ориентации: страница и пул пишут стороны вразнобой."""
    return (leg["season"], tuple(sorted([side(leg["a"]), side(leg["b"])])), tuple(sorted([leg["s1"], leg["s2"]])))


def normalize_round(label):
    """Раунд так, как его подписывают оба списка: «Финал Кубка» и «Финал» — один раунд."""
    text = " ".join(str(label or "").lower().split())
    return text.replace(" кубка", "").replace("кубка", "").strip()


def rounds_agree(page_leg, pool_leg):
    return normalize_round(page_leg["round"]) == normalize_round(pool_leg["round"])


def main(db_path=DB_PATH):
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    pool = {}
    for leg in con.execute(POOL_SQL, CUP_SEASONS):
        pool.setdefault(signature(leg), []).append(leg)

    closed, ambiguous = 0, 0
    for page_leg in con.execute(PAGE_SQL, CUP_SEASONS):
        candidates = [leg for leg in pool.get(signature(page_leg), []) if leg["duplicate_of"] is None]
        agreed = [leg for leg in candidates if rounds_agree(page_leg, leg)]
        if len(agreed) != 1:
            ambiguous += len(candidates)
            continue
        con.execute("update matches set duplicate_of = ? where id = ?", (agreed[0]["id"], page_leg["id"]))
        closed += 1

    con.commit()
    print(f"\nкубковых тождеств записано: {closed} | не доказано (остались в очереди): {ambiguous}")
    return closed


if __name__ == "__main__":
    main()
