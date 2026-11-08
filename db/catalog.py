"""Чтение каталога матчей из единой базы — в той же форме, в какой его строит `portal.match_catalog`.

Это точка, где сборка перестаёт читать `early_seasons_matches.json`,
`all_vk_seasons_matches.json` и `wiki_seasons_matches.json`: ключи и порядок ключей здесь такие,
чтобы конвейер `season_pages` → `site_payload` получил те же словари. Правки в базе
(изменение счёта, удаление строки, новая игра) проходят сюда без посредников.
"""

import sqlite3
from pathlib import Path

from db.fields import flags_of
from db import store

DB_PATH = store.DB_PATH

BASE_SQL = """
select m.id, t.season, m.league, m.tour, s.name as stage,
       pa.nick as p1, pb.nick as p2, sa.score as s1, sb.score as s2,
       sa.outcome as outcome_a, sb.outcome as outcome_b,
       m.phase, m.source, m.source_locator, m.source_page, m.source_text, m.source_date_raw,
       m.status, m.note, m.is_playoff
from matches m
join tournaments t on t.id = m.tournament_id
join stages s on s.id = m.stage_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
join side_players a on a.side_id = sa.id
join side_players b on b.side_id = sb.id
join players pa on pa.id = a.player_id
join players pb on pb.id = b.player_id
where m.row_set = 'catalog'
  and t.discipline_id = 1
  -- второй показ той же игры на витрине (тот же документ источника, тот же тур, та же пара и
  -- счёт). Ставится при импорте в hidden_by и только внутри среза 'catalog': строки, чей двойник
  -- — матч рейтингового пула, остаются: пул сам на страницу не выводится.
  and m.hidden_by is null
  -- «снять с зачёта» значит «этой игры не было»: её нет ни в таблицах, ни в числах, ни в
  -- истории игрока. Строка при этом остаётся в базе — статус обратим, журнал помнит почему.
  and m.status <> 'void'
  -- игры Кубка лиг Сезонов 2–7 читаются отдельно (`cup_rows_from_db`): у них другая форма строки
  -- и свой порядок в списке сезона.
  and m.source <> 'cup_tables'
order by m.order_in_source
"""

# Строка кубкового справочника: сезон, лига, тур, пары, счёт и подпись источника — и больше
# ничего. Ключей `stage`, `ot`, `pk`, `source` у неё нет, а `vk_url`/`vk_page` пустые, но
# присутствуют: страница сериализует словарь как есть, и форма строки здесь такая же, какой её
# всегда видел payload. Ники берём из подписей сторон, а не из `players.nick`: справочник пишет
# игроков так, как их помнит кубок («Tymoschuk» рядом с «Bubnov» — это решение человека, а не
# нормализации), и сводить их молча читатель не имеет права.
CUP_SQL = """
select t.season, m.league, m.tour, m.source_text, m.source_date_raw,
       sa.label as p1, sb.label as p2, sa.score as s1, sb.score as s2
from matches m
join tournaments t on t.id = m.tournament_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
where m.source = 'cup_tables' and t.discipline_id = 1 and m.hidden_by is null
  -- см. `catalog_from_db`: снятый с зачёта матч не показывается нигде
  and m.status <> 'void'
order by m.order_in_source
"""

# Источник хранится нормализованным бакетом; сборка ожидает исходную строку носителя.
RAW_SOURCE_BY_BUCKET = {"vk_wiki": "source_locator", "early_archive": "source_locator"}
SPORTCUP_SOURCE = "sportcup_api"


def raw_source(source, locator):
    if RAW_SOURCE_BY_BUCKET.get(source) == "source_locator" and locator:
        return locator
    return source


def number(value):
    """Столбцы TEXT хранят id страниц и дату как строки; конвейер ждёт их числами."""
    text = str(value)
    return int(text) if text.lstrip("-").isdigit() else value


def connect(db_path):
    if not Path(db_path).exists():
        raise SystemExit(
            f"Нет базы {db_path}. Соберите её: python db/build_db.py && python db/import_stores.py"
        )
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def cup_rows_from_db(db_path=DB_PATH):
    """Игры Кубка лиг Сезонов 2–7 — строкой ровно той формы, что их всегда видел payload."""
    con = connect(db_path)
    rows = [
        {
            "season": record["season"],
            "league": record["league"],
            "tour": record["tour"],
            "p1": record["p1"],
            "p2": record["p2"],
            "s1": record["s1"],
            "s2": record["s2"],
            "vk_text": record["source_text"],
            "vk_url": "",
            "vk_date": record["source_date_raw"],
            "vk_page": "",
        }
        for record in con.execute(CUP_SQL)
    ]
    con.close()
    return rows


def catalog_from_db(db_path=DB_PATH):
    """Список словарей-матчей: тот же набор ключей, что отдаёт `match_catalog.build`."""
    con = connect(db_path)
    posts = dict(con.execute("select match_id, url from match_links where kind = 'vk_post'"))
    videos = dict(con.execute("select match_id, url from match_links where kind = 'video'"))
    rows = []
    for record in con.execute(BASE_SQL):
        overtime, penalties = flags_of(record["phase"])
        row = {
            "season": record["season"],
            "league": record["league"],
            "tour": record["tour"],
            "stage": record["stage"],
            "p1": record["p1"],
            "p2": record["p2"],
            "s1": record["s1"],
            "s2": record["s2"],
            "ot": overtime,
            "pk": penalties,
            "source": raw_source(record["source"], record["source_locator"]),
        }
        if record["s1"] == record["s2"] and record["outcome_a"] in ("win", "loss"):
            # Счёт равный, а победитель есть: ногу решила серия. Исход сторон знает то, чего счёт
            # не говорит, и без него история игрока показала бы ничью там, где матч выигран.
            row["outcome"] = [record["outcome_a"], record["outcome_b"]]
        if record["source"] == SPORTCUP_SOURCE:
            # from_sportcup_api выдаёт эти три ключа всегда, а не только для технических строк:
            # убирать их у обычных матчей — значит менять payload страницы.
            technical = record["status"] == "technical"
            row["is_technical"] = technical
            row["is_forfeit"] = technical
            row["note"] = record["note"]
            if technical:
                row["technical_loser"] = next(
                    (nick for nick, outcome in ((record["p1"], record["outcome_a"]),
                                                (record["p2"], record["outcome_b"]))
                     if outcome == "none"),
                    None,
                )
        match_id = record["id"]
        if match_id in posts:
            row["vk_url"] = posts[match_id]
        if match_id in videos:
            row["video_url"] = videos[match_id]
        if record["source_text"]:
            row["vk_text"] = record["source_text"]
        if record["source_date_raw"] is not None:
            row["vk_date"] = number(record["source_date_raw"])
        if record["source_page"]:
            row["vk_page"] = number(record["source_page"])
        rows.append(row)
    con.close()
    if not rows:
        raise SystemExit(
            f"В базе {db_path} нет каталога матчей — запустите python db/import_stores.py."
        )
    return rows
