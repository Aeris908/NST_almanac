"""Демонстрационные записи дисциплин (баскетбол, хоккей, доджбол).

Показывают, что:
1. База nst.db единая, но турниры и матчи строго привязаны к своей дисциплине (disciplines.id).
2. Таблица игроков (players) общая: игроки сообщества (Romix, ectoPower, mafuta и т.д.)
   участвуют в разных видах спорта под одной личностью.
3. Футбольная витрина (soccer.html) изолирована и не захватывает матчи других дисциплин.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import store

DB_PATH = store.DB_PATH

DISCIPLINES = [
    (1, "soccer", "Футбол Goal 3"),
    (2, "basketball", "Баскетбол Dunk Heroes"),
    (3, "hockey", "Хоккей Ike Ike!"),
    (4, "dodgeball", "Доджбол / Вышибалы"),
]

DEMO_GAMES = [
    {
        "discipline_id": 2,
        "season": "Сезон 1",
        "kind": "league",
        "tournament": "Сезон 1 Баскетбол Dunk Heroes",
        "stage": "Регулярный сезон",
        "tour": "1 Тур",
        "p1": "Romix",
        "p2": "ectoPower",
        "s1": 18,
        "s2": 14,
        "note": "18:14",
    },
    {
        "discipline_id": 3,
        "season": "Сезон 1",
        "kind": "league",
        "tournament": "Сезон 1 Хоккей Ike Ike!",
        "stage": "Регулярный сезон",
        "tour": "1 Тур",
        "p1": "mafuta",
        "p2": "izzzotope",
        "s1": 5,
        "s2": 3,
        "note": "5:3",
    },
    {
        "discipline_id": 4,
        "season": "2026",
        "kind": "cup",
        "tournament": "Кубок Вышибал 2026",
        "stage": "Плей-офф",
        "tour": "Финал",
        "p1": "Kunio",
        "p2": "Sokol",
        "s1": 2,
        "s2": 1,
        "note": "2:1",
    },
]


def ensure_demo_disciplines(con):
    """Регистрирует дисциплины и по одной тестовой встрече для проверки редактора."""
    # 1. Дисциплины
    for d_id, slug, name in DISCIPLINES:
        con.execute(
            "insert into disciplines(id, slug, name) values (?, ?, ?)"
            " on conflict(id) do update set name = excluded.name, slug = excluded.slug",
            (d_id, slug, name),
        )

    # 2. Демо-матчи
    for game in DEMO_GAMES:
        d_id = game["discipline_id"]
        # Турнир
        con.execute(
            "insert or ignore into tournaments(discipline_id, season, kind, name) values (?, ?, ?, ?)",
            (d_id, game["season"], game["kind"], game["tournament"]),
        )
        t_id = con.execute(
            "select id from tournaments where discipline_id = ? and name = ?",
            (d_id, game["tournament"]),
        ).fetchone()[0]

        # Стадия
        con.execute(
            "insert or ignore into stages(tournament_id, name, order_index) values (?, ?, 1)",
            (t_id, game["stage"]),
        )
        s_id = con.execute(
            "select id from stages where tournament_id = ? and name = ?",
            (t_id, game["stage"]),
        ).fetchone()[0]

        # Игроки (должны быть в общей таблице players)
        p1_row = con.execute("select id from players where nick = ?", (game["p1"],)).fetchone()
        p2_row = con.execute("select id from players where nick = ?", (game["p2"],)).fetchone()
        if not p1_row or not p2_row:
            continue
        p1_id, p2_id = p1_row[0], p2_row[0]

        # Матч (проверяем, заведён ли уже)
        existing = con.execute(
            "select id from matches where tournament_id = ? and source = 'demo'", (t_id,)
        ).fetchone()
        if existing:
            continue

        con.execute(
            """insert into matches(tournament_id, stage_id, row_set, tour, phase, order_in_source,
                                   status, note, source, source_locator, manual)
               values (?, ?, 'catalog', ?, 'regular', 1, 'played', ?, 'demo', 'demo_seed', 1)""",
            (t_id, s_id, game["tour"], game["note"]),
        )
        match_id = con.execute("select last_insert_rowid()").fetchone()[0]

        # Стороны
        out1 = "win" if game["s1"] > game["s2"] else ("loss" if game["s1"] < game["s2"] else "draw")
        out2 = "loss" if out1 == "win" else ("win" if out1 == "loss" else "draw")

        con.execute(
            "insert into match_sides(match_id, side_index, outcome, score, label) values (?, 0, ?, ?, ?)",
            (match_id, out1, game["s1"], game["p1"]),
        )
        side1_id = con.execute("select last_insert_rowid()").fetchone()[0]
        con.execute("insert into side_players(side_id, player_id) values (?, ?)", (side1_id, p1_id))

        con.execute(
            "insert into match_sides(match_id, side_index, outcome, score, label) values (?, 1, ?, ?, ?)",
            (match_id, out2, game["s2"], game["p2"]),
        )
        side2_id = con.execute("select last_insert_rowid()").fetchone()[0]
        con.execute("insert into side_players(side_id, player_id) values (?, ?)", (side2_id, p2_id))

    con.commit()


def main(db_path=DB_PATH):
    sys.stdout.reconfigure(encoding="utf-8")
    con = store.connect(db_path)
    ensure_demo_disciplines(con)
    discs = con.execute("select id, slug, name from disciplines").fetchall()
    print("дисциплины в базе:", discs)
    demos = con.execute(
        "select m.id, d.name, t.name, m.tour, sa.score, sb.score, sa.label, sb.label "
        "from matches m "
        "join tournaments t on t.id = m.tournament_id "
        "join disciplines d on d.id = t.discipline_id "
        "join match_sides sa on sa.match_id = m.id and sa.side_index = 0 "
        "join match_sides sb on sb.match_id = m.id and sb.side_index = 1 "
        "where m.source = 'demo'"
    ).fetchall()
    print(f"демо-матчей других дисциплин: {len(demos)}")
    for row in demos:
        print(f"  #{row[0]} [{row[1]}] {row[2]} • {row[3]}: {row[6]} {row[4]}:{row[5]} {row[7]}")


if __name__ == "__main__":
    main()
