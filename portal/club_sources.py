"""Клубный Чемпионат по Goal 4 (межсезонье 2019): протокол двух эшелонов из листов источника.

Шапка темы 39731903 ссылается короткими адресами vk.cc на регламент и таблицы; сами таблицы
лежат в одном Google-документе четырьмя листами. Выгрузка закоммичена в `data/gsheet_club_goal4/`,
поэтому разбор и сборка работают без сети.

    python db/import_live.py --extract   # листы → data/vk_live_matches.json
    python db/import_live.py             # носитель → matches (шаг сборки)

Мячи считаются так, как их считает сама таблица источника: вместе с буллитными (853 основных
+ 38 буллитных = 891). Несыгранный баттл — одна строка «ТП обоим», а не пять пустых строк листа.
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEET_DIR = ROOT / "data" / "gsheet_club_goal4"
SHEET_ID = "1L9cdKCwKo90dx709FhhC45C8l6gKP5dJjWhRSEwtIkY"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
TOPIC_ID = 39731903
TOPIC_URL = f"https://vk.com/topic-66162180_{TOPIC_ID}"
TOURNAMENT = "Клубный Чемпионат по Goal 4. МЕЖСЕЗОНЬЕ"
SEASON = "Межсезонье"

GID_MATCHES = "1594898980"
GID_PREMIER = "414538934"
GID_YOUTH = "1489881286"
GID_STATS = "1766610579"

PREMIER = "Премьер-лига"
YOUTH = "Молодёжная лига"
LEAGUE_BY_MARK = {"в": PREMIER, "н": YOUTH}
GAMES_PER_BATTLE = 5


def sheet_rows(sheet_dir, gid):
    """Лист выгрузки как таблица ячеек: пустые строки и хвост листа остаются на месте."""
    path = Path(sheet_dir) / f"{gid}.csv"
    return list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))


def cell_int(text):
    """Число из ячейки счёта: «5 (9)» -> 5, пусто -> None."""
    match = re.match(r"\s*(\d+)", text or "")
    return int(match.group(1)) if match else None


def protocol_games(sheet_dir):
    """Лист «Матчи» → игры протокола в порядке источника.

    Колонки: 0 номер, 2 хост, 3/4 счёт как его показывает лист, 5 клиент, 6/7 основные мячи,
    8/9 буллиты, 15 итог баттла, 16 эшелон («в» — Премьер-лига, «н» — молодёжка).
    Пустая ячейка счёта и «0:0» означают одно и то же: игра не сыграна (баттл уже решён).
    """
    games = []
    tour = ""
    for index, row in enumerate(sheet_rows(sheet_dir, GID_MATCHES)[1:], 2):
        if not row or not row[0].strip():
            continue
        if not row[0].strip().isdigit():
            tour = row[0].strip()
            continue
        if len(row) < 17:
            continue
        shown_a, shown_b = cell_int(row[3]), cell_int(row[4])
        games.append({
            "n": int(row[0]),
            "sheet_row": index,
            "tour": tour,
            "host": row[2].strip(),
            "client": row[5].strip(),
            "league": LEAGUE_BY_MARK[row[16].strip()],
            "hm": cell_int(row[6]) or 0,
            "am": cell_int(row[7]) or 0,
            "hpk": cell_int(row[8]) or 0,
            "apk": cell_int(row[9]) or 0,
            "series_text": row[15].strip(),
            "played": shown_a is not None and (shown_a, shown_b) != (0, 0),
        })
    return games


def battles_of(games):
    """Баттл — пять игр листа до трёх побед; итог серии стоит в первой строке пятёрки."""
    battles = []
    for start in range(0, len(games), GAMES_PER_BATTLE):
        chunk = games[start:start + GAMES_PER_BATTLE]
        if len(chunk) != GAMES_PER_BATTLE:
            raise SystemExit(f"лист «Матчи»: неполный баттл с игры №{chunk[0]['n']}")
        keys = {(g["tour"], g["league"], tuple(sorted((g["host"], g["client"])))) for g in chunk}
        if len(keys) != 1:
            raise SystemExit(f"лист «Матчи»: баттл с игры №{chunk[0]['n']} смешивает туры, лиги или стороны")
        first = chunk[0]
        battles.append({
            "tour": first["tour"], "league": first["league"],
            "host": first["host"], "client": first["client"],
            "series_text": first["series_text"], "first": first["n"], "games": chunk,
        })
    return battles


def table_totals(sheet_dir, gid):
    """Лист эшелона → итоги турнира.

    Баттл и игру считают ОБА клуба, поэтому суммы делятся на два. Мячи делить нельзя: каждый
    мяч записан один раз как «Мз» забившего клуба. Буллитные мячи таблица включает в «Мз».
    """
    clubs = [row for row in sheet_rows(sheet_dir, gid)[1:]
             if len(row) > 10 and row[1].strip() and row[2].strip().isdigit()]
    if not clubs:
        raise SystemExit(f"лист {gid}: таблица эшелона пуста")
    return {
        "баттлов": sum(int(row[2]) for row in clubs) // 2,
        "игр": sum(int(row[4]) for row in clubs) // 2,
        "мячей": sum(int(row[9]) for row in clubs),
    }


def source_ref_of(number):
    return f"club-{TOPIC_ID}-sheet-{GID_MATCHES}#{number}"


def describe(game, battle):
    """Текст источника для провенанса.

    Счёт здесь намеренно записан словами («мячи 8 и 4»), а не «8:4»: адрес у всех строк один
    (тема турнира), и `expected_games` импортёра спрятал бы повтор той же игры, если текст
    перечисляет её счёт в двоеточие. В протоколе 34 такие пары — это настоящие разные игры.
    """
    return (
        f"лист «Матчи» (gid {GID_MATCHES}), строка {game['sheet_row']}, игра №{game['n']}, "
        f"баттл с игры №{battle['first']} · {game['tour']}, {game['league']} · "
        f"{game['host']} (хост) — {game['client']} (клиент) · "
        f"мячи {game['hm']} и {game['am']}, буллиты {game['hpk']} и {game['apk']}"
    )


def game_row(game, battle):
    """Сыгранная игра → строка носителя. Счёт — суммарный, как его считает таблица источника."""
    total_a = game["hm"] + game["hpk"]
    total_b = game["am"] + game["apk"]
    shootout = bool(game["hpk"] or game["apk"])
    outcome = (["win", "loss"] if total_a > total_b else
               ["loss", "win"] if total_a < total_b else ["draw", "draw"])
    return {
        "tournament": TOURNAMENT,
        "season": SEASON,
        "kind": "special",
        "row_set": "special",
        "league": game["league"],
        "tour": game["tour"],
        "stage": game["tour"],
        "team_a": [game["host"]],
        "team_b": [game["client"]],
        "score": [total_a, total_b],
        "series": [game["hpk"], game["apk"]] if shootout else None,
        "outcome": outcome,
        "phase": "penalties" if shootout else "regular",
        "counted": True,
        "score_text": f"{total_a}:{total_b}" + (f" (ПК {game['hpk']}:{game['apk']})" if shootout else ""),
        "source_ref": source_ref_of(game["n"]),
        "source_line": describe(game, battle),
        "source_text": describe(game, battle),
        "source_page": f"topic-{TOPIC_ID}",
        "page_url": TOPIC_URL,
        "links": [],
        "note": f"{total_a}:{total_b}",
    }


def tp_row(battle):
    """Несыгранный баттл → одна строка «ТП обоим», а не пять пустых строк листа.

    Источник сам помечает такую встречу переносом («Тур 9») и не зачитывает её никому:
    у Рединского отряда в молодёжке 5 баттлов из 8, у Геймклуба 6. Голы придумывать нельзя.
    """
    first = battle["games"][0]
    text = (
        f"лист «Матчи» (gid {GID_MATCHES}), строки {first['sheet_row']}–{first['sheet_row'] + 4}, "
        f"баттл с игры №{battle['first']} · {battle['tour']}, {battle['league']} · "
        f"{battle['host']} (хост) — {battle['client']} (клиент) · все пять игр пусты, "
        f"таблица эшелона помечает встречу переносом «{battle['series_text']}» и не зачитывает её"
    )
    return {
        "tournament": TOURNAMENT,
        "season": SEASON,
        "kind": "special",
        "row_set": "special",
        "league": battle["league"],
        "tour": battle["tour"],
        "stage": battle["tour"],
        "team_a": [battle["host"]],
        "team_b": [battle["client"]],
        "score": [None, None],
        "series": None,
        "outcome": ["none", "none"],
        "phase": "regular",
        "tp": True,
        "counted": False,
        "score_text": f"ТП обоим: баттл не сыгран (источник помечает переносом «{battle['series_text']}»)",
        "source_ref": source_ref_of(f"b{battle['first']}"),
        "source_line": text,
        "source_text": text,
        "source_page": f"topic-{TOPIC_ID}",
        "page_url": TOPIC_URL,
        "links": [],
        "note": "ТП обоим",
    }


def club_games(sheet_dir=SHEET_DIR):
    """Листы источника → строки живого носителя и отчёт о сходимости с таблицами эшелонов."""
    games = protocol_games(sheet_dir)
    battles = battles_of(games)
    rows = []
    for battle in battles:
        played = [game for game in battle["games"] if game["played"]]
        if not played:
            rows.append(tp_row(battle))
            continue
        rows.extend(game_row(game, battle) for game in played)

    report = {"leagues": [], "unreconciled": [], "totals": {}}
    for league, gid in ((PREMIER, GID_PREMIER), (YOUTH, GID_YOUTH)):
        table = table_totals(sheet_dir, gid)
        mine = [row for row in rows if row["league"] == league and row["score"][0] is not None]
        protocol = {
            "баттлов": sum(1 for b in battles if b["league"] == league
                           and any(g["played"] for g in b["games"])),
            "игр": len(mine),
            "мячей": sum(sum(row["score"]) for row in mine),
        }
        gap = {key: (table[key], protocol[key]) for key in table if table[key] != protocol[key]}
        report["leagues"].append({"лига": league, "по_таблице": table,
                                  "по_протоколу": protocol, "расхождение": gap})
        if gap:
            report["unreconciled"].append({"лига": league, "расхождение": gap})

    scored = [row for row in rows if row["score"][0] is not None]
    report["totals"] = {
        "баттлов в протоколе": len(battles),
        "игр сыграно": len(scored),
        "строк в базу": len(rows),
        "не сыграно (ТП обоим)": sum(1 for row in rows if row.get("tp")),
        "игр решено буллитами": sum(1 for row in scored if row["phase"] == "penalties"),
        "мячей всего": sum(sum(row["score"]) for row in scored),
        "сходимость с таблицами": "полная" if not report["unreconciled"] else "не сходится",
    }
    return rows, report
