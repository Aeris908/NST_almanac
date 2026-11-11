"""Живые результаты ВКонтакте в базе: регулярка командных чемпионатов и групповой тур молодёжки.

Два шага, и оба можно перепроверить глазами:

    python db/import_live.py --extract   # из data/vk_dump_<дата>/ → data/vk_live_matches.json
    python db/import_live.py             # из носителя → matches (шаг сборки)

Сырой дамп в git не попадает и живёт только на машине выгрузки, поэтому посредник —
`data/vk_live_matches.json`: он читается человеком и делает сборку воспроизводимой без сети
(тот же приём, что с снапшотом `data/sportcup_games.json`). Повтор `--extract` с новым дампом
список перезаписывает, `build_all.py` после этого просто пересобирает базу.

В базе эти строки — отдельный срез по признаку `source = 'vk_live'`: обычный импорт шести
носителей их не трогает (`reset_previous_imports` их исключает), а собственный сброс здесь
снимает только невручную нарисованные строки, чтобы повтор прогона не удваивал игры.

Календари вики дают встречи командных чемпионатов, групповой тур 2-го Молодёжного разбирается
из листов источника и отчётов в теме (`portal/youth_sources`) — те же строки носителя, только
`kind`/`row_set` у них свои и часть строк без счёта: счёта ног источник не опубликовал.
Клубный Goal 4 (`portal/club_sources`) целиком живёт здесь: его статическая рамка игр не несёт,
потому что протокол требует и ТП обоим для несыгранных баттлов, и буллиты, а рамка спецтурнира
принимает только девять ключей и ни того ни другого выразить не может.
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.live_sources import load_pages, team_meetings  # noqa: E402
from portal.penalty_sources import penalty_games  # noqa: E402
from portal.club_sources import GID_MATCHES, SHEET_DIR as CLUB_SHEET, TOURNAMENT as CLUB_TOURNAMENT, club_games  # noqa: E402
from portal.youth_sources import TOPIC_ID, TOURNAMENT, group_stage  # noqa: E402
from db import store  # noqa: E402

CARRIER = ROOT / "data" / "vk_live_matches.json"
YOUTH_REPORT = ROOT / "data" / "youth2_group_report.json"
YOUTH_SHEET = ROOT / "data" / "gsheet_youth"
PENALTY_REPORT = ROOT / "data" / "penalty_report.json"
CLUB_REPORT = ROOT / "data" / "club_goal4_report.json"
DB_PATH = store.DB_PATH
SOURCE = "vk_live"
TEAM_REVIEW_BATCH = "team_archive_review"
YOUTH_SEASON = "Молодёжные турниры"

# Какие страницы какого турнира какой лиги. Берётся заголовком страницы, а не угадывается:
# «VI Командный турнир по Soccer League. Календарь высшей лиги» → турнир VI, лига «Высшая».
CALENDARS = {
    "53638616": ("VI Командный Чемпионат по Goal 3", "Высшая лига"),
    "53638617": ("VI Командный Чемпионат по Goal 3", "Средняя лига"),
    # IV лежит одной страницей и двумя колонками: лигу берёт заголовок колонки, а не страница.
    "50560019": ("IV Командный Чемпионат по Goal 3", ""),
}


def normalize_league(text, fallback):
    """Заголовок колонки «Высшая Лига» → «Высшая лига», как поле `league` в базе."""
    label = re.sub(r"\s+", " ", str(text or "").strip())
    if not label:
        return fallback
    if not label.lower().endswith("лига"):
        return label
    return re.sub(r"\s+", " ", label[:-4].title() + " лига").strip()


def dump_dir():
    folders = sorted((ROOT / "data").glob("vk_dump_*"))
    return folders[-1] if folders else None


def youth_rows():
    """Групповой тур молодёжки: листы источника + отчёты темы → строки носителя и отчёт."""
    out = dump_dir()
    comments_path = out / "comments" / f"{TOPIC_ID}.json" if out else None
    if not (comments_path and comments_path.exists() and (YOUTH_SHEET / "1526661752.csv").exists()):
        return [], {}
    comments = json.loads(comments_path.read_text(encoding="utf-8"))["comments"]
    games, report = group_stage(YOUTH_SHEET, comments)
    rows = [{
        "tournament": game["tournament"],
        "league": game["division"],
        "tour": game["tour"],
        "team_a": game["team_a"],
        "team_b": game["team_b"],
        "score": game["score"],
        "score_text": game["score_text"],
        "source_line": game["source_line"],
        "source_ref": game["source_ref"],
        "page_url": game["comment_url"],
        "links": game["links"],
        "note": game["score_text"],
        # Спецтурнир лежит в другом разрезе и другом документе, чем календари командных:
        # у ноги есть исход при равном счёте (его решает серия), а встречи без опубликованного
        # счёта помнят, что их должен доделать человек (`review` → очередь редактуры).
        "kind": "special",
        "row_set": "special",
        "season": YOUTH_SEASON,
        "stage": "Групповой этап",
        "phase": game["phase"],
        "outcome": game["outcome"],
        "series": game["series"],
        "counted": game["counted"],
        "tp": game.get("tp", False),
        "review": game.get("review"),
        "source_text": game["source_line"],
        "source_page": f"topic-{TOPIC_ID}",
    } for game in games]
    return rows, report


def penalty_rows():
    """Турниры по пенальти: сетка источника + отчёты темы → строки носителя и отчёт."""
    out = dump_dir()
    if not out:
        return [], {}
    return penalty_games(out)


def club_rows():
    """Клубный Goal 4: листы источника → строки носителя и отчёт о сходимости с таблицами.

    Игр этого турнира статическая рамка не несёт: она принимает только девять ключей и не
    умеет выразить ни ТП обоим, ни буллиты, а протоколу нужно и то и другое.
    """
    if not (CLUB_SHEET / f"{GID_MATCHES}.csv").exists():
        return [], {}
    return club_games(CLUB_SHEET)


def extract():
    """Календари и тема молодёжки → носитель: встречи с турами, счётом, составом и ссылками."""
    out = dump_dir()
    if not out:
        sys.exit("нет data/vk_dump_* — сначала collectors/vk_recheck.py и браузерный обход вики")
    pages = load_pages(out)
    games = []
    stats = {}
    for pid, (tournament, league) in CALENDARS.items():
        page = pages.get(pid)
        if not page:
            stats[tournament] = "страница не выгружена"
            continue
        meetings, unscored = team_meetings(page)
        stats[f"{tournament} · {league or 'календарь'}"] = f"встреч {len(meetings)}, без счёта {unscored}"
        for index, meeting in enumerate(meetings, 1):
            games.append({
                "tournament": tournament,
                "league": normalize_league(meeting.get("league"), league),
                "tour": meeting["tour"] or "Регулярный тур",
                "team_a": meeting["names_a"],
                "team_b": meeting["names_b"],
                "score": list(meeting["scores"]),
                # `note` документа — то, как источник показывает счёт («5:4», «ТП», «Победа X/Y»);
                # без него читатель подставит в ячейку счёта текст состава, а стороны — None.
                "score_text": meeting["note"] or f"{meeting['scores'][0]}:{meeting['scores'][1]}",
                "source_line": meeting["line"],
                "source_ref": f"page-{pid}#{index}",
                "page_url": f"https://vk.com/page-66162180_{pid}",
                "links": [url for url in meeting["links"] if url.startswith("http")],
                "note": meeting["line"][:120],
            })
    youth, report = youth_rows()
    games += youth
    if report:
        YOUTH_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        stats[TOURNAMENT] = " | ".join(f"{key}: {value}" for key, value in report["totals"].items())
    penalty, penalty_report = penalty_rows()
    games += penalty
    if penalty_report:
        PENALTY_REPORT.write_text(json.dumps(penalty_report, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
        for title, numbers in penalty_report["турниры"].items():
            stats[title] = " | ".join(f"{key}: {value}" for key, value in numbers.items())
    club, club_report = club_rows()
    games += club
    if club_report:
        CLUB_REPORT.write_text(json.dumps(club_report, ensure_ascii=False, indent=1), encoding="utf-8")
        stats[CLUB_TOURNAMENT] = " | ".join(f"{key}: {value}" for key, value in club_report["totals"].items())
    CARRIER.write_text(json.dumps(games, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"встреч в носителе: {len(games)} → {CARRIER.name}")
    for key, value in stats.items():
        print(f"   {key:46s} {value}")


REVIEW_PREFIX = "vk_live_review_"


def review_batch(game):
    """Батч очереди по теме-источнику: у каждой темы своя задача редактуры."""
    return REVIEW_PREFIX + str(game.get("source_page") or "").partition("topic-")[2]


def write_review_queue(con, rows):
    """Что человек обязан доделать, — в очередь редактуры вместе со ссылками на источник.

    Строки без опубликованного счёта и встречи «ТП обоим» остаются видными на странице, но
    догадываться за нас источник не обязан. `incoming.verdict = 'conflict'` — именно то, что
    считает панель редактора (`db/api.state`), поэтому работа не теряется: в карточке строки
    видно задачу, а `payload.ссылки` ведёт и на тему, и на гугл-таблицу турнира.
    """
    con.execute("delete from incoming where substr(batch, 1, ?) = ?",
                (len(REVIEW_PREFIX), REVIEW_PREFIX))
    done = {row[0] for row in con.execute("select id from matches where manual = 1")}
    for match_id, game in rows:
        payload = {
            "задача": game["review"]["задача"],
            "ссылки": game["review"]["ссылки"],
            "тур": game["tour"],
            "лига": game.get("league"),
            "стороны": [" & ".join(game["team_a"]), " & ".join(game["team_b"])],
            "как_выглядит": game["score_text"],
            "source_ref": game["source_ref"],
        }
        # Ручная правка на строке = задачу уже сделали: человек нашёл счёт и вписал его. Такую
        # запись оставляем в базе закрытой (`same`), иначе каждый пересборочный прогон возвращал
        # бы сделанное в счётчик очереди.
        verdict = "same" if match_id in done else "conflict"
        con.execute(
            "insert into incoming(batch, source, source_ref, payload, verdict, matched_match_id)"
            " values (?, ?, ?, ?, ?, ?)",
            (review_batch(game), SOURCE, game["source_ref"], json.dumps(payload, ensure_ascii=False),
             verdict, match_id),
        )
    return len(rows)


def renumber_group_first(con, doc_id):
    """Номера строк внутри турнира: читатель отдаёт их по `order_in_source`, групповой тур — раньше плей-офф.

    «Группа H» — это тот же групповой тур, только подписанный по-другому (у пенальти групп восемь,
    а туров нет), поэтому блок считается по обоим написаниям.
    """
    rows = con.execute(
        """
        select id, case when tour like 'Тур %' or tour like 'Группа%' then 0 else 1 end as block,
               coalesce(cast(substr(tour, 5) as integer), 0) as tour_no, order_in_source
        from matches where doc_id = ?
        """, (doc_id,)).fetchall()
    for rank, row in enumerate(
        sorted(rows, key=lambda row: (row["block"], row["tour_no"], row["order_in_source"])), 1
    ):
        con.execute("update matches set order_in_source = ? where id = ?", (rank, row["id"]))


def containers(con):
    """Куда ложится строка носителя: имя турнира → (`doc_id` или пусто, сезон рамки).

    Сезон берётся из рамки, а не из носителя: у строк командных календарей его в носителе нет
    вовсе, и `ensure_tournament` на пустом месте заводил второй контейнер того же чемпионата с
    сезоном «—» — после этого игры темы и игры календаря лежали бы в разных турнирах.
    """
    found = {re.sub(r"\s+", " ", (row["title"] or "")).strip(): (row["id"], row["season"])
             for row in con.execute(
                 "select id, json_extract(payload, '$.title') as title,"
                 " json_extract(payload, '$.season_year') as season from tournament_docs")}
    # Рамки сезонов документов не имеют: строка дивизиона раннего чемпионата ищется по имени
    # турнира, а сезон приходит из самой рамки.
    found.update({row["name"]: (None, row["season"]) for row in
                  con.execute("select name, season from tournaments where kind = 'league'")})
    return found


def write_team_review_queue(con):
    """Хранит сомнения отдельно от матчей и сохраняет вердикты при переимпорте."""
    path = ROOT / "data" / "team_recovery_review.json"
    if not path.exists():
        return 0
    items = json.loads(path.read_text(encoding="utf-8"))
    for item in items:
        found = con.execute("select id from matches where source = ? and source_ref = ?",
                            (SOURCE, item.get("match_ref"))).fetchone()
        match_id = found[0] if found else None
        existing = con.execute("select id, payload from incoming where batch = ? and source_ref = ?",
                               (TEAM_REVIEW_BATCH, item["source_ref"])).fetchone()
        if existing:
            previous = store.parse_json(existing[1], default={})
            if previous.get("вердикт_редактора"):
                item = {**item, "вердикт_редактора": previous["вердикт_редактора"]}
        payload = json.dumps(item, ensure_ascii=False)
        if existing:
            con.execute("update incoming set payload = ?, matched_match_id = ? where id = ?",
                        (payload, match_id, existing[0]))
        else:
            con.execute("insert into incoming(batch, source, source_ref, payload, verdict, matched_match_id) "
                        "values (?, 'team_archive', ?, ?, 'conflict', ?)",
                        (TEAM_REVIEW_BATCH, item["source_ref"], payload, match_id))
    return len(items)


def load(db_path=DB_PATH):
    """Носитель → `matches`: строка привязывается к документу рамки либо к сезонной рамке."""
    if not CARRIER.exists():
        print("файл data/vk_live_matches.json не найден — живые результаты в базу не заносятся")
        return 0
    games = json.loads(CARRIER.read_text(encoding="utf-8"))
    recovered = ROOT / "data" / "team_recovered_matches.json"
    if recovered.exists():
        games.extend(json.loads(recovered.read_text(encoding="utf-8")))
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")

    doomed = [r["id"] for r in con.execute(
        f"select id from matches where source = '{SOURCE}' and manual = 0")]
    if doomed:
        placeholders = ",".join("?" * len(doomed))
        con.execute(f"update incoming set matched_match_id = null where matched_match_id in ({placeholders})", doomed)
        con.execute(f"update matches set duplicate_of = null where duplicate_of in ({placeholders})", doomed)
        con.execute(f"update matches set hidden_by = null where hidden_by in ({placeholders})", doomed)
        con.execute(f"delete from match_links where match_id in ({placeholders})", doomed)
        con.execute(f"delete from match_sides where match_id in ({placeholders})", doomed)
        con.execute(f"delete from matches where id in ({placeholders})", doomed)

    places = containers(con)
    from db.import_stores import Importer

    imp = Importer(con)
    added, skipped, tp = 0, 0, 0
    renumbered = set()
    queued = []
    for game in games:
        found = places.get(game["tournament"])
        if found is None:
            skipped += 1
            continue
        doc_id, doc_season = found
        s1, s2 = game["score"]
        links = [("video", url) for url in game.get("links") or []]
        # Комментарий темы и есть доказательство ноги — ссылку кладём рядом с видео. Для строк
        # сезона и дивизионов другого доказательства нет вовсе: без ссылки строка недоказуема.
        if game.get("kind") in ("special", "league") or game.get("source_ref", "").startswith("team-recovered:"):
            links.append(("vk_post", game["page_url"]))
        label_a = " & ".join(game["team_a"])
        label_b = " & ".join(game["team_b"])
        counted = game.get("counted", True)
        tp += 1 if game.get("tp") else 0
        status = "technical" if game.get("tp") else (None if counted else "void")
        season = game.get("season") or doc_season or "—"
        match_id = imp.add(tournament=game["tournament"], season=season,
                           kind=game.get("kind", "team"), stage=game.get("stage") or game["tour"],
                           names_a=game["team_a"], names_b=game["team_b"],
                           s1=s1, s2=s2, source=SOURCE, source_ref=game["source_ref"],
                           source_locator=f"{SOURCE}:{game['source_ref']}", primary_url=game["page_url"],
                           note=game.get("score_text") or game.get("note", ""), links=links,
                           row_set=game.get("row_set", "team"),
                           label_a=label_a, label_b=label_b,
                           league=game.get("league"), tour=game["tour"], doc_id=doc_id,
                           phase=game.get("phase", "regular"),
                           outcomes=tuple(game["outcome"]) if game.get("outcome") else None,
                           status=status,
                           source_text=game.get("source_text"), source_page=game.get("source_page"))
        added += 1
        if game.get("review"):
            queued.append((match_id, game))
        if game.get("kind") == "special":
            renumbered.add(doc_id)

    for doc_id in sorted(renumbered):
        renumber_group_first(con, doc_id)

    queue = write_review_queue(con, queued)
    team_queue = write_team_review_queue(con)

    con.commit()
    people = con.execute("select count(*) from players where kind = 'player'").fetchone()[0]
    print(f"\nживых строк занесено: {added} (в носителе {len(games)}, без документа пропущено {skipped}, "
          f"ТП обоим {tp}) | игроков {people} | в очередь редактуры {queue}")
    print(f"Задач по командному архиву: {team_queue}")
    if imp.unresolved:
        print("   ники вне справочника (заведены новыми игроками, решить алиасом): "
              + ", ".join(sorted(imp.unresolved)))
    return added


def main():
    parser = argparse.ArgumentParser(description="Живые результаты ВК: разбор календарей и занесение в базу")
    parser.add_argument("--extract", action="store_true", help="перевыделить встречи из дампа в носитель")
    parser.add_argument("--db", default=str(DB_PATH),
                        help="файл базы: по умолчанию data/nst.db; нужен, чтобы прогонять правки на копии")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.extract:
        extract()
    else:
        load(Path(args.db))


if __name__ == "__main__":
    main()
