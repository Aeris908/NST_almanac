"""Проверка: база воспроизводит пул, из которого сейчас считается сайт, строка в строку."""

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build_final_analytics as bfa  # noqa: E402

FIELDS = ("season", "tournament", "stage", "p1", "p2", "s1", "s2",
          "ot", "pk", "is_playoff", "is_technical", "technical_loser", "note")
BOOLEAN = {"ot", "pk", "is_playoff", "is_technical"}
CARRIER_LIVE = ROOT / "data" / "vk_live_matches.json"

SELECT = """
select season, tournament, stage, p1, p2, s1, s2, ot, pk, is_playoff,
       is_technical, technical_loser, note
from v_rating_pool
order by order_in_source
"""


def pool_row(row):
    """Рукописные строки пула не содержат технических полей — для сравнения это False/None/''."""
    out = {key: row.get(key) for key in FIELDS}
    for key in BOOLEAN:
        out[key] = bool(out[key])
    out["note"] = out["note"] or ""
    return out


def main():
    con = sqlite3.connect(ROOT / "data" / "nst.db")
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(SELECT)]
    pool = [pool_row(row) for row in bfa.all_matches]

    print(f"пул Python: {len(pool)} строк | база: {len(rows)} строк")
    mismatches = 0
    for i, (a, b) in enumerate(zip(pool, rows)):
        for key in FIELDS:
            want, got = a[key], b[key]
            if key in BOOLEAN:
                want, got = bool(want), bool(got)
            if want != got:
                mismatches += 1
                if mismatches <= 10:
                    print(f"  расхождение #{i} {key}: пул={want!r} база={got!r} ({a['p1']} {a['s1']}:{a['s2']} {a['p2']})")
    if len(pool) != len(rows):
        print(f"  разная длина: недосчитано {abs(len(pool) - len(rows))} строк")
        mismatches += abs(len(pool) - len(rows))

    if mismatches:
        print(f"FAIL: {mismatches} расхождений")
        return 1
    print(f"OK: база отдаёт ровно тот пул, из которого собран сайт ({len(pool)} строк, {len(FIELDS)} полей)")

    from db.pool import pool_from_db
    from portal import master_table

    # Python-пул — это Sportcup и рукописные блоки. Всё, что взял в рейтинг редактор
    # (`source='editor'`, помеченные строки вики и турниров), в нём заведомо нет, и требовать его
    # означало бы ронять проверку на каждом отмеченном сезоне.
    db_pool = pool_from_db()
    legacy = [row for row in db_pool if row["source"] in ("sportcup_api", "manual")]
    tree_py = json.dumps(master_table.build_payload(bfa.all_matches), ensure_ascii=False, sort_keys=True)
    tree_db = json.dumps(master_table.build_payload(legacy), ensure_ascii=False, sort_keys=True)
    if tree_py != tree_db:
        print("FAIL: мастер-таблица из базы отличается от мастер-таблицы из Python-пула")
        return 1
    extra = (f" + рейтинговых строк редактора {len(db_pool) - len(legacy)}"
             if len(db_pool) != len(legacy) else "")
    print(f"OK: мастер-таблица, посчитанная из базы, совпала с посчитанной из Python-пула "
          f"({len(tree_py) / 1024:.0f} КБ байт-в-байт){extra}")

    # Рамки документов правятся в файле-носителе и в редакторе, поэтому сверка с носителем —
    # проверка читателя: порядок и набор ключей страницы должны совпасть байт в байт.
    from db.docs import special_from_db, team_from_db

    for name, kind, reader, carrier in (
        ("спецтурниры", "special", special_from_db, "special_tournaments_data.json"),
        ("командные", "team", team_from_db, "team_tournaments_data.json")):
        path = ROOT / carrier
        want = json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False)
        # Сравниваем с базой без живого среза и без правок человека: ни строк `vk_live`, ни
        # внесённых игр, ни правилки рамки в носителе заведомо нет — требовать их означало бы
        # ронять проверку на каждом занесении. Ручные строки при этом считаются и печатаются.
        got = json.dumps(reader(exclude_live=True, exclude_manual=True), ensure_ascii=False)
        if want != got:
            print(f"FAIL: {name} из базы не совпадают с носителем ({len(got)} против {len(want)} байт)")
            return 1
        extra = ""
        if CARRIER_LIVE.exists():
            live = json.loads(CARRIER_LIVE.read_text(encoding="utf-8"))
            tp = len([row for row in live if row.get("tp")])
            counted = len([row for row in live if row.get("counted", True)])
            extra = (f" + живых строк {len(live)}"
                     f" (в зачёте {counted}, ТП обоим {tp})")
        manual = con.execute(
            "select count(*) from matches m join tournament_docs d on d.id = m.doc_id"
            " where m.manual = 1 and d.kind = ?", (kind,)).fetchone()[0]
        frames = con.execute("select count(*) from tournament_docs where manual = 1 and kind = ?",
                             (kind,)).fetchone()[0]
        if manual or frames:
            extra += f" | ручных игр {manual}, правленых рамок {frames}"
        print(f"OK: {name} собраны базой байт-в-байт как в носителе ({len(got)} байт){extra}")

    # Кубок лиг Сезонов 2–7: справочник `portal/cup_tables.py` питает импортёр, страница читает
    # строки из базы. сверка — проверка, что переезд ничего не потерял и не переставил.
    from db.catalog import cup_rows_from_db
    from portal.cup_tables import HISTORIC_CUPS_DATA

    def key(row):
        return (row["season"], row["tour"], row["p1"], row["p2"], row["s1"], row["s2"])

    reference = [key({"season": season, **m})
                 for season, cup in HISTORIC_CUPS_DATA.items() for m in cup["matches"]]
    in_db = cup_rows_from_db()
    if reference != [key(row) for row in in_db]:
        missing = set(reference) - {key(row) for row in in_db}
        print(f"FAIL: Кубка лиг в базе не как в справочнике: строк {len(in_db)} против "
              f"{len(reference)}, первое расхождение — {sorted(missing)[:1]}")
        return 1
    print(f"OK: Кубок лиг — {len(in_db)} игр в базе ровно в том порядке, что в справочнике")
    return 0


if __name__ == "__main__":
    sys.exit(main())
