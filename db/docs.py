"""Спец- и командные турниры как документы базы.

Носитель описывает турнир рамкой — заголовок, категория, хроника, призовой фонд, итоговые
таблицы (groups / divisions / playoff / ladder) — и списком игр. В базе рамка лежит в
`tournament_docs.payload`, а игры — в `matches`: игра живёт в одном месте вместе со сторонами,
ссылками, флагом дубля и журналом правок. Список игр в рамке хранится пустым, читатель
навешивает строки обратно — иначе одна и та же игра существовала бы в базе дважды.

Форма возврата совпадает с носитителем ключ в ключ и в том же порядке: `site_payload`
вкладывает эти словари в JSON страницы, и порядок ключей влияет на байты.
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import store  # noqa: E402

DB_PATH = store.DB_PATH

# Ключ строки игры в документе -> колонка базы. Одно поле на ключ: набор ключей одинаков у всех
# строк документа (это проверяет импортёр), поэтому порядок берёт сам документ.
FIELD_BY_KEY = {
    "tour": "tour",
    "league": "league",
    "stage": "stage",
    "p1": "label_a",
    "p2": "label_b",
    "t1": "label_a",
    "t2": "label_b",
    "games": "series_detail",
}
# Счёт — не колонка: его читатель считает со сторон матча (см. score_text).
COMPUTED_KEYS = ("score",)
SCORE_LINE = re.compile(r"^\d+:\d+$")

DOCS_SQL = """
select id, doc_key, title, payload, match_field, match_keys
from tournament_docs where kind = ?
order by order_index, id
"""

# Играми документа считаются строки, привязанные к нему, в том же порядке, в каком их перечислил
# носитель. Скрытые вторые показатели не отдаём: для витрины это одна и та же игра дважды.
# `{live}` — запор для сверки: `db/verify_db.py` сравнивает документ с носителем и не должен
# видеть строки живого импорта (`source = 'vk_live'`), которых в носителе заведомо нет.
# `{manual}` — то же для игр и правок, которые внёс человек: носитель о них не знает.
DOC_MATCHES_SQL = """
select m.tour, m.league, m.note, m.series_detail, s.name as stage,
       sa.label as label_a, sb.label as label_b,
       sa.score as score_a, sb.score as score_b
from matches m
join stages s on s.id = m.stage_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
where m.doc_id = ? and m.hidden_by is null and m.status <> 'void'{live}{manual}
order by m.order_in_source
"""


def score_text(note, score_a, score_b):
    """Как документ показывает счёт этой игры.

    «5:0» — это про счёт, а не про слова: правка в базе меняет стороны, и строка турнира обязана
    пойти за ней, иначе редактор чинит игру, а таблица турнира продолжает врать. Надпись словами
    («Победа Kunio/Memori», «🥇») остаётся как её записал источник: числам там делать нечего.
    """
    if SCORE_LINE.match(note or "") and score_a is not None and score_b is not None:
        return f"{score_a}:{score_b}"
    return note


def row_value(record, key):
    if key == "score":
        return score_text(record["note"], record["score_a"], record["score_b"])
    return record[FIELD_BY_KEY[key]]


def row_keys(doc, field):
    """Ключи строки игры в порядке носителя.

    Разнородные строки в одном документе читатель воспроизвести не сможет, как и ключ, которого
    нет в FIELD_BY_KEY: оба случая — правка носителя, а не угадывание на сборке.
    """
    rows = doc.get(field) or []
    if not rows:
        # Игр в рамке нет, но они приходят из другого места (живой разбор темы): тогда ключи
        # описаны прямо в документе, иначе читателю не из чего собрать строку.
        return list(doc.get("row_keys") or [])
    keys = list(rows[0])
    uneven = [index for index, row in enumerate(rows) if list(row) != keys]
    if uneven:
        raise SystemExit(
            f"{doc['id']}: строки «{field}» имеют разный набор ключей (первое расхождение — "
            f"индекс {uneven[0]}). Соберите их одинаково в носителе."
        )
    unknown = [key for key in keys if key not in FIELD_BY_KEY and key not in COMPUTED_KEYS]
    if unknown:
        raise SystemExit(f"{doc['id']}: не знаю, из колонки базы взять ключ «{unknown[0]}».")
    return keys


def frame_of(doc, field):
    """Документ без игр: список заменяется пустым на месте, чтобы порядок ключей не сдвинулся.
    Если ключа в документе не было (турнир без плей-офф) — не добавляем: страница его не ждёт."""
    frame = dict(doc)
    if field in frame:
        frame[field] = []
    return frame


def store_docs(con, docs, kind, field):
    """Рамки документов в базу. Возвращает {doc_key: id}.

    Правленая в редакторе рамка (`manual = 1`) не перезаписывается: иначе пересборка базы молча
    стирала бы то, что человек поправил в описании турнира.
    """
    doc_ids = {}
    for order, doc in enumerate(docs):
        keys = row_keys(doc, field)
        con.execute(
            """
            insert into tournament_docs(kind, doc_key, title, payload, match_field, match_keys, order_index)
            values (?, ?, ?, ?, ?, ?, ?)
            on conflict(doc_key) do update set
                kind = excluded.kind, title = excluded.title, payload = excluded.payload,
                match_field = excluded.match_field, match_keys = excluded.match_keys,
                order_index = excluded.order_index
            where tournament_docs.manual = 0
            """,
            (kind, doc["id"], doc["title"], json.dumps(frame_of(doc, field), ensure_ascii=False),
             field, json.dumps(keys, ensure_ascii=False), order),
        )
        doc_ids[doc["id"]] = con.execute(
            "select id from tournament_docs where doc_key = ?", (doc["id"],)
        ).fetchone()[0]
    return doc_ids


def match_rows(con, doc_id, keys, exclude_live=False, exclude_manual=False):
    sql = DOC_MATCHES_SQL.format(live=" and m.source <> 'vk_live'" if exclude_live else "",
                                 manual=" and m.manual = 0" if exclude_manual else "")
    return [{key: row_value(record, key) for key in keys}
            for record in con.execute(sql, (doc_id,))]


def docs_from_db(kind, db_path=DB_PATH, exclude_live=False, exclude_manual=False):
    """Документы турнира того же вида, что лежали в файле-носителе, — в порядке носителя."""
    if not Path(db_path).exists():
        raise SystemExit(
            f"Нет базы {db_path}. Соберите её: python db/build_db.py && python db/import_stores.py"
        )
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    docs = []
    for record in con.execute(DOCS_SQL, (kind,)):
        doc = json.loads(record["payload"])
        field = record["match_field"]
        if field in doc:
            doc[field] = match_rows(con, record["id"], json.loads(record["match_keys"]),
                                    exclude_live, exclude_manual)
        docs.append(doc)
    con.close()
    return docs


def special_from_db(db_path=DB_PATH, exclude_live=False, exclude_manual=False):
    return docs_from_db("special", db_path, exclude_live=exclude_live, exclude_manual=exclude_manual)


def team_from_db(db_path=DB_PATH, exclude_live=False, exclude_manual=False):
    return docs_from_db("team", db_path, exclude_live=exclude_live, exclude_manual=exclude_manual)
