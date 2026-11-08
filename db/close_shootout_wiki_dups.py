"""Закрывает дубли строк «вики-календарь с итогом буллитов ↔ комментарий с ничьей и серией».

В чемпионатах Сезонов 2–7 вики-календарь часто записывал итог серии пенальти как счёт игры
(например, 8:6 или 11:10), тогда как комментарий-источник в теме ВК хранил реальный счёт игры
(4:4, 6:6) и рядом в скобках серию буллитов (8:6 PK, 5:4 PK).

Обе строки попадали в срез 'catalog' как сыгранные ноги, в результате чего одна и та же встреча
считалась на витрине дважды, раздувая счётчики матчей и голов.

По решению владельца («скрываем»):
Строка вики помечается ``hidden_by = <id комментария>`` и ``duplicate_of = <id комментария>``.
Витрина показывает первичный комментарий с реальным счётом и значком буллитов/победителем,
а строка вики остаётся в базе со своим провенансом и историей.
"""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import store
from portal.comment_origin import shootout_of

DB_PATH = store.DB_PATH

WIKI_SQL = """
select mw.id, mw.tournament_id, mw.tour, mw.source_locator,
       s0w.score, s1w.score, p0.nick, p1.nick, t.season,
       s0w.outcome, s1w.outcome
from matches mw
join tournaments t on t.id = mw.tournament_id
join match_sides s0w on s0w.match_id = mw.id and s0w.side_index = 0
join match_sides s1w on s1w.match_id = mw.id and s1w.side_index = 1
join side_players sp0 on sp0.side_id = s0w.id
join players p0 on p0.id = sp0.player_id
join side_players sp1 on sp1.side_id = s1w.id
join players p1 on p1.id = sp1.player_id
where mw.source = 'vk_wiki' and mw.phase in ('penalties', 'overtime_penalties')
  and mw.hidden_by is null and mw.row_set = 'catalog'
"""

COMM_SQL = """
select mc.id, mc.tournament_id, mc.tour, mc.source_text,
       s0c.score, s1c.score, p0.nick, p1.nick, t.season,
       s0c.outcome, s1c.outcome
from matches mc
join tournaments t on t.id = mc.tournament_id
join match_sides s0c on s0c.match_id = mc.id and s0c.side_index = 0
join match_sides s1c on s1c.match_id = mc.id and s1c.side_index = 1
join side_players sp0 on sp0.side_id = s0c.id
join players p0 on p0.id = sp0.player_id
join side_players sp1 on sp1.side_id = s1c.id
join players p1 on p1.id = sp1.player_id
where mc.source = 'vk_comments_playoff' and s0c.score = s1c.score
  and mc.row_set = 'catalog'
"""


def find_shootout_wiki_duplicates(con):
    """Находит пары (комментарий, вики-матч), где вики-счёт равен серии буллитов комментария."""
    wms = con.execute(WIKI_SQL).fetchall()
    cms = con.execute(COMM_SQL).fetchall()

    pairs = []
    for cm in cms:
        cid, _tid, ctour, ctext, s0, s1, cp0, cp1, cseason, co0, co1 = cm
        sh = shootout_of(ctext, s0, s1)
        if not sh:
            continue
        for wm in wms:
            wid, _wtid, wtour, _wloc, ws0, ws1, wp0, wp1, wseason, wo0, wo1 = wm
            if wseason != cseason or {wp0, wp1} != {cp0, cp1}:
                continue
            if ctour != "Плей-офф / Кубок" and ctour != wtour:
                continue
            is_exact = ((ws0, ws1) == sh or (ws1, ws0) == sh)
            is_sum = ((ws0, ws1) == (s0 + sh[0], s1 + sh[1]) or (ws1, ws0) == (s0 + sh[0], s1 + sh[1]))
            if not (is_exact or is_sum):
                continue
            c_winner = cp0 if co0 == "win" else (cp1 if co1 == "win" else None)
            w_winner = wp0 if wo0 == "win" else (wp1 if wo1 == "win" else None)
            if c_winner and w_winner and c_winner == w_winner:
                pairs.append((cid, wid))
    return pairs


def main(db_path=DB_PATH):
    sys.stdout.reconfigure(encoding="utf-8")
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row

    pairs = find_shootout_wiki_duplicates(con)
    hidden = 0
    for comm_id, wiki_id in pairs:
        con.execute(
            "update matches set hidden_by = ?, duplicate_of = coalesce(duplicate_of, ?) where id = ?",
            (comm_id, comm_id, wiki_id),
        )
        hidden += 1

    con.commit()
    print(f"дублей «вики vs буллиты в комментариях» скрыто: {hidden}")
    return hidden


if __name__ == "__main__":
    main()
