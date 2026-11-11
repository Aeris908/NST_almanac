"""API правки базы: операция — и дельта по затронутым числам, а не весь payload страницы.

Контракт для шага 5 (карандаши в UI). Один вызов делает три вещи: применяет правку тем же кодом,
что и `db/edit.py`, пересчитывает payload страницы (`portal.build_soccer.compose_payload`) и
возвращает только то, что в нём сдвинулось — вместо 3.9 МБ. Предпросмотр (`persist=False`) считает
по копии базы и живую не трогает: «что сдвинется» и «что станет» считает один и тот же код, другого
способа не будет.

Дельта повторяет форму payload: лист — это `[было, стало]`, а списки словарей с опознавательным
полем (`player`, `id`, `name`) разбираются по нему, поэтому правка счёта приезжает как
«ectoPower: active_elo 1725 → 1719», а не как новый массив из 92 профилей. Порядок в таких списках
тоже данные (место в мастер-таблице = ранг), поэтому перестановка уезжает в `__order__`. Тяжёлые списки —
истории игроков и таблицы матчей — в снимке свёрнуты в длину: изменённая строка едет в поле `match`,
а если список изменился по составу, приходит `{«__length__»: [было, стало]}` — значит, нужен пересбор.

`expect` — ревизия из предпросмотра. Между «посмотрел» и «записал» база может измениться под другим
редактором; тогда запись отклоняется, а не перетирает чужую правку.

Транспорта здесь нет намеренно: страница публичная, поэтому личность редактора обязана
проверяться на сервере в каждом вызове, а `editor` обязан приходить из этой проверки, а не из
запроса. Лицом API служит `db/serve.py`; CLI ниже печатает ровно тот JSON, который вернёт
обработчик.

    python db/api.py show 2928                                  # ревизия и строка глазами страницы
    python db/api.py set-score 2928 5 1 --editor aeros           # предпросмотр, база цела
    python db/api.py set-score 2928 5 1 --editor aeros --apply   # запись
    python db/api.py undo last --editor aeros --apply --expect <revision>
    python db/api.py undo op:<метка> --editor aeros --apply   # операцию целиком, какой бы старой она ни была
"""

import argparse
import contextlib
import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import (
    edit,
    store,
)
from portal.build_soccer import compose_payload
from portal.names import clean_alias

DB_PATH = store.DB_PATH
# Десять тысяч строк на игрока: в общий снимок попадает только длина, а сами строки — для тех
# игроков, у которых действительно что-то сдвинулось (см. `_attach_history`).
HEAVY_FIELDS = ("match_history",)
# Поле, по которому список словарей однозначен: один элемент — один ключ.
IDENTITY_FIELDS = ("player", "id", "name", "doc_key", "rivalry", "club", "team", "stage")

REVISION_MATCHES_SQL = """
select m.id, m.status, m.hidden_by, m.duplicate_of, m.manual
from matches m order by m.id
"""
REVISION_SCORES_SQL = """
select s.match_id, s.score from match_sides s
order by s.match_id, s.side_index
"""


def revision(db_path=DB_PATH):
    """Отпечаток того, что правится: статус матча, его скрытость, метка ручной правки и счета сторон.

    По содержимому, а не по часам: две правки в одну секунду дали бы одинаковый `updated_at`, а
    пересборка неизменного содержимого ревизию не сдвигает. Строку склеивает Python, а не
    `group_concat`: у второго порядок зависит от плана запроса и от версии SQLite, а ревизия,
    которая прыгает без правки, ломает optimistic lock — панель начинает отказывать в записи сама
    у себя.
    """
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        scores = {}
        for match_id, score in con.execute(REVISION_SCORES_SQL):
            if score is not None:  # пустой счёт источника в склейку не входит, как и раньше
                scores.setdefault(match_id, []).append(str(score))
        lines = [f"{row['id']}|{row['status']}|{row['hidden_by'] or ''}|{row['duplicate_of'] or ''}"
                 f"|{row['manual']}|{'/'.join(scores.get(row['id'], []))}"
                 for row in con.execute(REVISION_MATCHES_SQL)]
    finally:
        con.close()
    return hashlib.sha256(";".join(lines).encode()).hexdigest()[:16]


@contextlib.contextmanager
def _quiet():
    """Сборка страницы печатает отчёты в stdout. Для API это не ответ, а мусор: уводим их в stderr —
    чтобы `python db/api.py ... | jq` работал и чтобы ни одна строчка не потерялась, в том числе
    когда пересчёт упал на середине."""
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            yield
    finally:
        sys.stderr.write(buffer.getvalue())


def _identity(items):
    """Поле, по которому список словарей можно сопоставить элемент с элементом, или None."""
    if not items or not all(isinstance(item, dict) for item in items):
        return None
    for field in IDENTITY_FIELDS:
        if all(field in item for item in items):
            keys = [str(item[field]) for item in items]
            if len(set(keys)) == len(keys):
                return field
    return None


def _light(value):
    """Снимок payload: тяжёлые списки сворачиваются в `<поле>_count`, остальное — как в странице."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in HEAVY_FIELDS and isinstance(item, list):
                out[f"{key}_count"] = len(item)
            else:
                out[key] = _light(item)
        return out
    if isinstance(value, list):
        return [_light(item) for item in value]
    return value


def snapshot(db_path=DB_PATH):
    """Payload страницы в сравнимом виде — за один пересчёт, тем же кодом, что публикует сайт.

    Истории игроков вынесены отдельно: в общий снимок они не влезают (4 МБ на 92 игрока), но
    дельта по двум затронутым игрокам стоит ровно нескольких строк.
    """
    with _quiet():
        payload = compose_payload(db_path)
    return {"view": _light(payload),
            "history": {p["player"]: p.get("match_history") or [] for p in payload["profiles"]}}


def _attach_history(delta, before, after):
    """Для игроков, у которых сдвинулись числа, добавить и сдвинувшиеся строки истории."""
    for name, changes in delta.get("profiles", {}).items():
        if not isinstance(changes, dict):
            # Состав профилей изменился (завелся новый игрок или пропал последний матч): это
            # `__length__` или `[было, стало]`, а не набор полей — строк истории тут не бывает.
            continue
        rows = _diff_list(before["history"].get(name, []), after["history"].get(name, []))
        if rows:
            changes["match_history"] = rows


def diff(before, after):
    """Дерево изменений: только то, что разное. Пустой словарь = правка не сдвинула ничего видимого."""
    if before == after:
        return {}
    if isinstance(before, dict) and isinstance(after, dict):
        out = {}
        for key in sorted(set(before) | set(after), key=str):
            if key not in before or key not in after:
                out[key] = [before.get(key), after.get(key)]
                continue
            nested = diff(before[key], after[key])
            if nested:
                out[key] = nested
        return out
    if isinstance(before, list) and isinstance(after, list):
        return _diff_list(before, after)
    return [before, after]


def _diff_list(before, after):
    field = _identity(before)
    if field is not None and field == _identity(after):
        return _diff_keyed(before, after, field)
    if len(before) != len(after):
        # Состав изменился (строку скрыли, вернули, добавили). Позиционное сравнение показало бы
        # хвост целиком, поэтому честно: этот список нужно пересобрать, а не латать.
        return {"__length__": [len(before), len(after)]}
    out = {}
    for index, (old, new) in enumerate(zip(before, after)):
        nested = diff(old, new)
        if nested:
            out[str(index)] = nested
    return out


def _diff_keyed(before, after, field):
    old_items = {str(item[field]): item for item in before}
    new_items = {str(item[field]): item for item in after}
    out = {}
    # Порядок в таблицах сам по себе данные: мастер-таблица и лидеры читаются по месту в списке.
    # Поэтому перестановка уезжает в `__order__`, а не остаётся незамеченной.
    order_before = [str(item[field]) for item in before]
    order_after = [str(item[field]) for item in after]
    if order_before != order_after:
        out["__order__"] = [order_before, order_after]
    for key in sorted(old_items.keys() | new_items.keys()):
        old, new = old_items.get(key), new_items.get(key)
        if old is None or new is None:
            out[key] = [old, new]
            continue
        nested = diff(old, new)
        if nested:
            out[key] = nested
    return out


LOCATE_SELECT = """
select m.id, m.row_set, m.status, m.manual, m.hidden_by, m.tour, m.league, m.note,
       m.in_rating_pool, m.phase, m.is_playoff, m.played_on, m.date_precision,
       m.source, m.source_ref, m.source_locator, m.source_page, m.source_text, m.source_date_raw,
       t.season, t.name as tournament, st.name as stage, d.doc_key,
       disc.name as discipline, disc.slug as discipline_slug,
       sa.label as label_a, sb.label as label_b, sa.score as score_a, sb.score as score_b,
       sa.outcome as outcome_a, sb.outcome as outcome_b,
       sa.id as side_a, sb.id as side_b,
       -- Редактор правит строку, не открывая базу: пусть карточка сразу показывает, откуда она
       -- взялась (ссылки источника) и что с ней не так (задача из очереди редактуры).
       (select json_group_array(json_object('kind', l.kind, 'url', l.url))
          from match_links l
         where l.match_id = m.id
            or (m.duplicate_of is not null and l.match_id = m.duplicate_of)) as links,
       (select i.payload from incoming i
          where (i.matched_match_id = m.id
             or (m.duplicate_of is not null and i.matched_match_id = m.duplicate_of))
            and i.verdict = 'conflict' limit 1) as review
"""

LOCATE_FROM = """
from matches m
join tournaments t on t.id = m.tournament_id
join disciplines disc on disc.id = t.discipline_id
join stages st on st.id = m.stage_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
left join tournament_docs d on d.id = m.doc_id
"""

LOCATE_SQL = LOCATE_SELECT + LOCATE_FROM


def _with_rosters(con, rows):
    """Строки `LOCATE_SQL` без состава сторон — вместе с ним: порядок задаёт `seat_index`.

    Раньше список собирал `group_concat`, и порядок в нём зависел то ли от плана запроса, то ли от
    версии SQLite: на 264 сторонах панель показывала состав перевёрнутым относительно подписи
    источника, а человек правил не то, что видит. Здесь порядок берётся из того же места, откуда
    его читает ядро, — из мест игроков.
    """
    found = edit.rosters(con, [value for row in rows for value in (row["side_a"], row["side_b"])])
    out = []
    for row in rows:
        item = dict(row)
        item["players_a"] = found.get(row["side_a"], "")
        item["players_b"] = found.get(row["side_b"], "")
        out.append(item)
    return out


def _norm(text):
    """Написание как маска: тот же регистр и пробелы, что считает `fold()` внутри базы."""
    return store.fold(str(text or "").replace("&", " "))


def _sides(row):
    """Обе стороны строки: как её показал источник и как её помнит база. Порядок не важен —
    страница рисует пару то так, то эдак."""
    left = {_side_names(row["label_a"]), _side_names(row["players_a"])}
    right = {_side_names(row["label_b"]), _side_names(row["players_b"])}
    return left, right


def _side_names(text):
    """Сторона как состав карточек: «Bubnov & E_not», «E_not & Bubnov», «E_not & Tymoschuk» — одно.

    Порядок игроков страница меняет (в истории партнёр идёт за игроком), а написание — тем более:
    таблица турнира показывает слово источника, карточка — каноник из справочника. Сверять клик
    строкой означало бы «в базе нет такой строки» ровно там, где человек смотрит чаще всего.
    """
    names = {clean_alias(part.strip()).lower() for part in str(text or "").split("&") if part.strip()}
    return " ".join(sorted(names))


def _shown(row):
    """Что строка показывает в колонке счёта, или None — если сверять клик не по чему.

    Строка без счёта (суперфинал Сольного по пенальти, выводные встречи молодёжки) рисует не
    «N:N», а свою заметку. Сверять такой клик по цифрам означало бы «ничего не найдено» ровно
    на тех строках, ради которых человек и открывает редактор.
    """
    if row["score_a"] is not None and row["score_b"] is not None:
        return {f"{row['score_a']}:{row['score_b']}", f"{row['score_b']}:{row['score_a']}"}
    note = (row["note"] or "").strip()
    return {note.replace(" ", "")} if note else None


def _pair_matches(want, left, right):
    """Пара указана верно в любую сторону: страница рисует «A vs B» и «B vs A» одним матчем.

    Каждая сторона сравнивается со всеми своими написаниями (подпись источника и ники из базы).
    """
    a, b = sorted(want)
    return (a in left and b in right) or (a in right and b in left)


def locate(a, b, *, season=None, tour=None, score=None, include_hidden=False, db_path=DB_PATH):
    """Строки базы, похожие на то, что редактор увидел на странице.

    Идентификатора у строки в payload страницы нет, поэтому редактор указывает на неё текстом
    (пара, счёт, тур), а наружу отдаются **все** кандидаты: если под описание подходит две строки,
    выбирает человек, а не совпадение по первому.
    """
    want = {_side_names(a), _side_names(b)}
    score = str(score or "").strip() or None
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    found = []
    for row in _with_rosters(con, con.execute(LOCATE_SQL).fetchall()):
        left, right = _sides(row)
        if not _pair_matches(want, left, right):
            continue
        if season and _norm(row["season"]) != _norm(season):
            continue
        if tour and _norm(tour) not in (_norm(row["tour"]), _norm(row["stage"])):
            continue
        shown = _shown(row)
        if score and shown is not None and score.replace(" ", "") not in shown:
            continue
        if row["hidden_by"] and not include_hidden:
            continue
        found.append(_candidate(row))
    con.close()
    return _group_pairs(found, db_path)


def _candidate(row):
    """Строка LOCATE_SQL в том виде, в котором её показывает панель редактора."""
    return dict(row, display=_display(row),
                links=store.parse_json(row["links"], default=[]),
                review=store.parse_json(row["review"]),
                sides=[
            {"side_index": 0, "label": row["label_a"], "players": row["players_a"],
             "score": row["score_a"], "outcome": row["outcome_a"]},
            {"side_index": 1, "label": row["label_b"], "players": row["players_b"],
             "score": row["score_b"], "outcome": row["outcome_b"]},
        ])


# Порядок, по которому из связки выбирается «та самая» строка: сначала то, что показывает страница.
VISIBLE_FIRST = {"catalog": 0, "special": 1, "team": 2, "pool": 3}


def _group_pairs(rows, con_path):
    """Собрать связки в один кандидат: игра Сезона 8–9 лежит в базе двумя строками, и редактор
    должен видеть одну игру, а не гадать, какую из двух копий править."""
    if not rows:
        return rows
    con = store.connect(con_path)
    groups = {}
    for row in rows:
        key = tuple(sorted(edit.pair_ids(con, row["id"])))
        groups.setdefault(key, []).append(row)
    con.close()

    ordered = []
    for key, members in groups.items():
        # Победителем связки обязан стать тот показ игры, который видит витрина: иначе поиск со
        # скрытыми дублями молча подсовывал бы карточку второго показа вместо нужной строки.
        winner = min(members, key=lambda row: (bool(row["hidden_by"]),
                                               VISIBLE_FIRST.get(row["row_set"], 9), row["id"]))
        winner["linked"] = [other for other in key if other != winner["id"]]
        if winner["linked"]:
            winner["display"] += f" · связка #{', #'.join(str(other) for other in winner['linked'])}"
        ordered.append(winner)
    return sorted(ordered, key=lambda row: (bool(row["hidden_by"]),
                                            VISIBLE_FIRST.get(row["row_set"], 9)))


def _display(row):
    score = (f"{row['score_a']}:{row['score_b']}" if row["score_a"] is not None
             else (row["note"] or "—"))
    place = row["tour"] or row["stage"] or ""
    icon = {"basketball": "🏀 ", "hockey": "🏒 ", "dodgeball": "🏐 "}.get(row.get("discipline_slug"), "")
    prefix = f"[{icon}{row['discipline']}] " if row.get("discipline_slug") and row["discipline_slug"] != "soccer" else ""
    teams_str = f"{row['label_a'] or row['players_a']} {score} {row['label_b'] or row['players_b']}"
    return prefix + " • ".join(part for part in (row["season"], place, teams_str) if part)


def _like(text):
    """Написание человека как маска LIKE: `%` и `_` внутри ника или турнира — обычные символы.

    Без этого «Sokol_5» нашёл бы половину архива, а случайный `%` в запросе превратился бы в
    «покажи всё».
    """
    escaped = str(text or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


# Условия поиска по категориям архива. Пустое поле = «не фильтруем», поэтому одну и ту же фразу
# собирают и список строк, и счётчик: иначе «показано 60 из …» считалось бы по другому набору.
SEARCH_FILTER = """
     (?1 = '' or fold(t.season) like ?6 escape '\\')
 and (?2 = '' or fold(t.name) like ?7 escape '\\')
 and (?3 = '' or fold(m.tour) like ?8 escape '\\'
      or fold(st.name) like ?8 escape '\\')
 and (?4 = '' or exists (
        select 1 from match_sides s
        join side_players sp on sp.side_id = s.id
        join players p on p.id = sp.player_id
       where s.match_id = m.id
         and (fold(p.nick) like ?9 escape '\\'
              or fold(s.label) like ?9 escape '\\')))
 and (?5 = 1 or m.hidden_by is null)
"""

SEARCH_SQL = LOCATE_SQL + " where " + SEARCH_FILTER + " order by m.id limit ?10"
SEARCH_COUNT_SQL = "select count(*)" + LOCATE_FROM + " where " + SEARCH_FILTER
SEARCH_SEASONS_SQL = "select distinct season from tournaments order by season"
SEARCH_TOURNAMENTS_SQL = """
select distinct t.name from tournaments t
where (?1 = '' or fold(t.season) like ?2 escape '\\') order by name
"""


def search(*, season="", tournament="", tour="", player="", include_hidden=False, limit=60,
           db_path=DB_PATH):
    """Строки по сезону, турниру, туру и игроку — когда указателя мышью нет.

    `locate` ищет матч, на который человек показал пальцем на странице; здесь он приходит со
    списком («все игры Сезона 7 в 1/2 финала», «где вообще играл Bubnov»). Связки сворачиваются
    тем же кодом, что и в `locate`: копия строки страницы в пуле не должна плодить вторую карточку.
    Скрытые дубли по умолчанию не показываются — правят то, что видит витрина.
    """
    asked = (_norm(season), _norm(tournament), _norm(tour), _norm(player))
    taken = max(1, min(int(limit), 200))
    params = (*asked, 1 if include_hidden else 0, *(_like(value) for value in asked))
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    total = con.execute(SEARCH_COUNT_SQL, params).fetchone()[0]
    rows = [_candidate(row)
            for row in _with_rosters(con, con.execute(SEARCH_SQL, (*params, taken)).fetchall())]
    facets = {
        "seasons": [row[0] for row in con.execute(SEARCH_SEASONS_SQL)],
        "tournaments": [row[0] for row in con.execute(
            SEARCH_TOURNAMENTS_SQL, (asked[0], _like(asked[0])))],
    }
    con.close()
    collapsed = _group_pairs(rows, db_path)
    # `fetched` — строк до свёртки связок: по нему панель честно говорит, что список обрезан
    # лимитом, а не просто «карточек вышло меньше, чем строк» (связки съедают разницу сами).
    return {"total": total, "shown": taken, "fetched": len(rows), "collapsed": len(collapsed),
            "rows": collapsed, **facets}


def match_row(con, match_id):
    """Строка матча так, как её показывает страница: стороны, счёт, статус, документ."""
    row = con.execute(
        """select m.id, m.row_set, m.status, m.manual, m.note, m.hidden_by, m.source, m.source_ref,
                  t.season, t.name tournament, s.name stage, m.league, m.tour, d.doc_key, d.title doc_title
           from matches m
           join tournaments t on t.id = m.tournament_id
           join stages s on s.id = m.stage_id
           left join tournament_docs d on d.id = m.doc_id
           where m.id = ?""", (match_id,)).fetchone()
    if not row:
        return None
    # sqlite3.Row и PgRow при итерации возвращают значения, поэтому нужны именно keys().
    out = {key: row[key] for key in row.keys() if row[key] not in (None, "")}  # noqa: SIM118
    # Подпись стороны есть не у всех строк (пуловые заводятся ником), а UI рисует именно её:
    # пустое поле заполняем игроками, чтобы форма `sides` не зависела от среза строки.
    out["sides"] = [{"side_index": side["side_index"], "players": side["players"],
                     "label": side["label"] or side["players"], "score": side["score"],
                     "outcome": side["outcome"]}
                    for side in edit.sides_of(con, match_id)]
    return out


def _publish():
    """Слой очереди публикаций: запросы на выкат ставит и закрывает `db/publish.py`.

    Модуль импортируется внутри функции, а не в шапке файла: `db/publish.py` сам зовёт `db/api.py`,
    чтобы считать отпечаток базы тем же кодом, что видит панель. Цикл на уровне модулей оставил бы
    один из двух файлов наполовину загруженным — здесь он возникает только на вызове.
    """
    from db import publish
    return publish


def _apply(con, operation, editor, args):
    """Одна операция на одном соединении — те же функции вызывает CLI `db/edit.py`."""
    if operation == "review-task":
        from db.review import apply
        return apply(con, args, editor)
    if operation == "set-score":
        return edit.set_score(con, args["match_id"], args["s1"], args["s2"], editor)
    if operation == "set-players":
        return edit.set_players(con, args["match_id"], args["sides"], editor)
    if operation == "set-source":
        return edit.set_source(con, args["match_id"], editor, args.get("note"), args.get("links"))
    if operation == "set-place":
        return edit.set_place(con, args["match_id"], editor, args.get("tour"),
                              args.get("league"), args.get("stage"))
    if operation == "set-date":
        return edit.set_date(con, args["match_id"], editor, args.get("played_on"),
                             args.get("source_date_raw"))
    if operation == "set-phase":
        return edit.set_phase(con, args["match_id"], editor, args.get("phase"), args.get("playoff"))
    if operation == "set-provenance":
        return edit.set_provenance(con, args["match_id"], editor, args.get("source"),
                                   args.get("source_ref"), args.get("source_locator"),
                                   args.get("source_page"), args.get("source_text"))
    if operation == "drop-match":
        return edit.drop_match(con, args["match_id"], editor)
    if operation == "drop-tournament":
        return edit.drop_tournament(con, args["doc_key"], editor)
    if operation == "rename-player":
        return edit.rename_player(con, args["player_id"], args["nick"], editor)
    if operation == "merge-player":
        return edit.merge_player(con, args["keep_id"], args["drop_id"], editor)
    if operation == "add-match":
        return edit.add_match(con, args, editor)
    if operation == "add-tournament":
        return edit.add_tournament(con, args, editor)
    if operation == "set-doc":
        return edit.set_doc(con, args["doc_key"], editor, args.get("title"), args.get("frame"))
    if operation == "set-rating":
        return edit.set_rating(con, args["match_id"], bool(args.get("rated", True)), editor)
    if operation == "rate-scope":
        return edit.set_rating_scope(con, bool(args.get("rated", True)), editor,
                                     args.get("season"), args.get("doc_key"))
    if operation == "void":
        return edit.set_status(con, args["match_id"], "void", editor, args.get("reason", ""))
    if operation == "unvoid":
        return edit.set_status(con, args["match_id"], "played", editor)
    if operation == "unhide":
        return edit.unhide(con, args["match_id"], editor)
    if operation == "publish-request":
        # Запрос в очередь публикаций — не редактура архива: журнал правок его не ведёт, таблица
        # меняется только функциями db/publish.py. На витрине этот вызов не меняет ничего — цифры
        # обновит сборка, а не панель.
        return _publish().request(con, editor, args.get("note", ""))
    if operation == "undo":
        return edit.undo(con, args["what"])
    raise edit.EditError(f"неизвестная операция {operation}")


def _clone(db_path, target):
    if store.is_pg(db_path):
        from db.sync import pull
        # Локальный файл даёт только схему: данные предпросмотра должны быть из той же
        # серверной базы, чью ревизию подтвердил редактор, а не из старой сборки сайта.
        if not store.DB_PATH.is_file():
            raise edit.EditError("нет локального шаблона data/nst.db для предпросмотра Postgres")
        _clone(store.DB_PATH, target)
        pull(target, pg_url=str(db_path))
        return
    source = store.connect(db_path)
    destination = store.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


@contextlib.contextmanager
def _preview_db(db_path):
    """Копия базы в temp: предпросмотр правит её, живой файл остаётся нетронутым."""
    folder = Path(tempfile.mkdtemp(prefix="nst-preview-"))
    target = folder / "nst.db"
    try:
        _clone(db_path, target)
        yield target
    finally:
        for leftover in folder.glob("*"):
            leftover.unlink()
        folder.rmdir()


def _apply_and_snapshot(target, operation, editor, args):
    con = edit.connect(target)
    try:
        result = _apply(con, operation, editor, args)
        match_id = result.get("match_id")
        row = match_row(con, match_id) if match_id else None
        after = snapshot(target)
    finally:
        con.close()
    return result, row, after


def mutate(operation, args, editor, *, persist=False, expect=None, db_path=DB_PATH):
    """Предпросмотр или запись правки + дельта по затронутым числам.

    Снимок берётся ДО правки — на живой базе для записи и на копии для предпросмотра: смотреть
    «что сдвинется» надо на том же коде, который потом публикует страницу.
    """
    if not editor:
        raise edit.EditError("не указан редактор: правка без подписи не записывается")

    started = time.perf_counter()
    base = revision(db_path)
    if expect is not None and expect != base:
        raise edit.EditError(
            f"база изменилась с момента предпросмотра: ожидалась {expect}, сейчас {base}. "
            f"Пересмотри правку.")

    before = snapshot(db_path)
    if persist:
        target = db_path if store.is_pg(db_path) else Path(db_path)
        result, row, after = _apply_and_snapshot(target, operation, editor, args)
    else:
        with _preview_db(db_path) as clone:
            result, row, after = _apply_and_snapshot(clone, operation, editor, args)

    changed = diff(before["view"], after["view"])
    _attach_history(changed, before, after)

    return {
        "ok": True,
        "operation": operation,
        "persisted": persist,
        "editor": editor,
        "revision": base,
        "revision_after": revision(db_path),
        "changes": [{"table": table, "row_id": row_id, "field": field, "old": old, "new": new}
                    for table, row_id, field, old, new in result.get("changes", [])],
        "journal": result.get("journal", []) if persist else [],
        "linked": result.get("linked", []),
        "op": result.get("op", ""),
        "created": result.get("created", []),
        "reverted": [entry["id"] for entry in result.get("entries", [])],
        "released": result.get("released", 0),
        "match": row,
        "delta": changed,
        "recomputed_in_ms": int((time.perf_counter() - started) * 1000),
    }


LOG_SQL = """
select c.id, c.table_name, c.row_id, c.field, c.old_value, c.new_value, c.editor, c.created_at,
       c.reverted_at, c.op
from corrections c
order by c.id desc limit ?
"""

LIVE_BY_OP_SQL = "select op, count(*) from corrections where reverted_at is null group by op"

MATCH_DISPLAY_SQL = """
select t.season, coalesce(m.tour, st.name) as tour, st.name as stage,
       sa.label as label_a, sb.label as label_b, sa.score as score_a, sb.score as score_b,
       sa.outcome as outcome_a, sb.outcome as outcome_b, m.note,
       sa.id as side_a, sb.id as side_b
from matches m
join tournaments t on t.id = m.tournament_id
join stages st on st.id = m.stage_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
where m.id = ?
"""


def _match_of(con, entry):
    """Матч, к которому относится запись журнала: `matches.row_id` или сторона внутри матча.

    Импортёры пересоздают строки, и id из журнала может указать на сторону, которой в новой базе
    уже нет. Запись журнала от этого не перестаёт быть записью — просто не показываем матч.
    """
    if entry["table_name"] == "matches":
        return entry["row_id"]
    if entry["table_name"] == "match_sides":
        side = con.execute("select match_id from match_sides where id = ?", (entry["row_id"],)).fetchone()
        return side[0] if side else None
    return None


def journal_entries(limit=20, db_path=DB_PATH):
    """Журнал правок для панели редактора: кто, что и по какому матчу менял, и жива ли правка.

    `op` — метка операции, `op_live` — сколько её записей действует ещё: по ним панель решает,
    есть ли что откатывать целиком (`undo op:<метка>`), когда поверх лежат более новые правки.
    """
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    # Действующие записи по всем меткам — одним запросом: журнал зовётся на каждый показ панели.
    live_by_op = dict(con.execute(LIVE_BY_OP_SQL))
    entries = []
    for row in con.execute(LOG_SQL, (limit,)):
        item = dict(row)
        item["live"] = item["reverted_at"] is None
        # Запись без метки — сама по себе одна операция: её живой счёт равен ей самой.
        item["op_live"] = live_by_op.get(item["op"], 0) if item["op"] else int(item["live"])
        match_id = _match_of(con, row)
        display = con.execute(MATCH_DISPLAY_SQL, (match_id,)).fetchone() if match_id else None
        if display:
            item["match"] = _display(_with_rosters(con, [display])[0])
        entries.append(item)
    con.close()
    return entries


QUEUE_SQL = """
select id, batch, source, matched_match_id, payload
from incoming where verdict = 'conflict' order by batch, id
"""


def queue(db_path=DB_PATH):
    """Очередь редактуры: задача, ссылки источника и строка, которую ради неё править.

    Задача без перехода к матчу бесполезна — редактор получил бы список и пошёл искать встречу
    руками по таблице турнира. Поэтому к каждой записи прикладывается карточка строки.
    """
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    tasks = []
    pending = list(con.execute(QUEUE_SQL))
    team_cards = {}
    team_docs = [dict(r) for r in con.execute(
        "select doc_key, title from tournament_docs where kind = 'team'")]
    for record in _with_rosters(con, con.execute(
            LOCATE_SQL + " where m.source_ref like 'team-recovered:%'").fetchall()):
        prefix = str(record["source_ref"] or "").rsplit(":line-", 1)[0]
        team_cards.setdefault(prefix, []).append(_candidate(record))
    match_ids = [row["matched_match_id"] for row in pending if row["matched_match_id"]]
    cards = {}
    if match_ids:
        placeholders = ','.join('?' for _ in match_ids)
        records = con.execute(LOCATE_SQL + f" where m.id in ({placeholders})", match_ids).fetchall()
        cards = {record['id']: record for record in _with_rosters(con, records)}
    for row in pending:
        payload = store.parse_json(row["payload"], default={})
        card = cards.get(row["matched_match_id"])
        prefix = str(payload.get("match_ref") or "").rsplit(":line-", 1)[0]
        related = team_cards.get(prefix, [])
        tasks.append({"id": row["id"], "batch": row["batch"], "match_id": row["matched_match_id"],
                      "review_matches": related,
                      "review_documents": team_docs if row["batch"] == "team_archive_review" else [],
                      "review_doc_key": next((d["doc_key"] for d in team_docs
                                              if (payload.get("задача") or "").startswith(d["title"])), ""),
                      "task": payload.get("задача") or "", "links": payload.get("ссылки") or [],
                      "tour": payload.get("тур") or "", "sides": payload.get("стороны") or [],
                      "shown": payload.get("как_выглядит") or "",
                      "algorithm_doubt": payload.get("алгоритм_сомнение") or "",
                      "row": _candidate(card) if card else None})
    con.close()
    return tasks


CONTAINERS_SQL = """
select kind, doc_key, title from tournament_docs order by kind desc, order_index, id
"""


def containers(db_path=DB_PATH):
    """Чем редактор может принять новую игру: документы турниров и сезонные бакеты.

    Сезон берётся из `tournaments`, а не выдумывается: строка обязана попасть в тот же бакет,
    который читает страница сезона, иначе игра просто не покажется.
    """
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    docs = [dict(row) for row in con.execute(CONTAINERS_SQL)]
    seasons = [row[0] for row in con.execute(
        "select distinct season from tournaments order by season")]
    disciplines = [dict(row) for row in con.execute(
        "select id, slug, name from disciplines order by id")]
    con.close()
    return {"docs": docs, "seasons": seasons, "disciplines": disciplines}


def doc_frame(doc_key, db_path=DB_PATH):
    """Рамка турнира глазами редактора: JSON, который он правит, плюс служебные поля читателя."""
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    row = con.execute(
        """select id, kind, doc_key, title, payload, match_field, match_keys, manual
           from tournament_docs where doc_key = ?""", (doc_key,)).fetchone()
    con.close()
    if not row:
        raise edit.EditError(f"Турнира {doc_key!r} в базе нет")
    return {**dict(row), "frame": store.parse_json(row["payload"], default={})}


PLAYERS_SQL = """
select p.id, p.nick, p.slug, p.kind,
       (select count(*) from side_players sp where sp.player_id = p.id) as sides
from players p
where p.kind = 'player' and (fold(p.nick) like ?1 escape '\\'
   or exists (select 1 from player_aliases a where a.player_id=p.id
              and fold(a.alias) like ?1 escape '\\'))
order by sides desc, p.nick
limit ?2
"""


def players(query="", limit=30, db_path=DB_PATH):
    """Карточки по нику: человек ищет игрока текстом, а не номером строки."""
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = [dict(row) for row in
            con.execute(PLAYERS_SQL, (_like(_norm(query)), max(1, min(int(limit), 200))))]
    con.close()
    return rows


def state(db_path=DB_PATH):
    """Что редактор видит о базе, прежде чем править: ревизия, размер, живые правки, очередь."""
    con = store.connect(db_path)
    try:
        return {
            "revision": revision(db_path),
            "matches": con.execute("select count(*) from matches").fetchone()[0],
            "visible": con.execute("select count(*) from matches where hidden_by is null").fetchone()[0],
            "manual": con.execute("select count(*) from matches where manual = 1").fetchone()[0],
            "corrections_live": con.execute(
                "select count(*) from corrections where reverted_at is null").fetchone()[0],
            "queue": con.execute("select count(*) from incoming where verdict = 'conflict'").fetchone()[0],
        }
    finally:
        con.close()


def publish_queue(db_path=DB_PATH):
    """Очередь публикаций глазами панели: что стоит в очереди и сколько правок ещё живо.

    Число живых правок приходит тем же вызовом, что и состояние базы: человек сверяет запрос
    очереди с той же цифрой, что видит в статус-строке, а не с второй, посчитанной по-своему.
    """
    layer = _publish()
    return {"requests": layer.pending(db_path),
            "corrections_live": state(db_path)["corrections_live"]}


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--editor", default="owner")
    common.add_argument("--apply", action="store_true", help="записать; без него — предпросмотр")
    common.add_argument("--expect", help="ревизия из предпросмотра: не писать, если база изменилась")
    commands = parser.add_subparsers(dest="operation", required=True)

    for name, help_text in (("show", "ревизия и строка глазами страницы"),
                            ("void", "снять матч с зачёта"), ("unvoid", "вернуть матч на зачёт"),
                            ("unhide", "вернуть строку на витрину")):
        sub = commands.add_parser(name, help=help_text, parents=[common])
        sub.add_argument("match_id", type=int)
        if name == "void":
            sub.add_argument("--reason", default="")

    sub = commands.add_parser("set-score", help="править счёт матча", parents=[common])
    sub.add_argument("match_id", type=int)
    sub.add_argument("s1", type=int)
    sub.add_argument("s2", type=int)

    sub = commands.add_parser("set-players", help="править, кто играл в матче", parents=[common])
    sub.add_argument("match_id", type=int)
    sub.add_argument("a", help="состав первой стороны; пара 2×2 — через « & »")
    sub.add_argument("b", help="состав второй стороны")

    sub = commands.add_parser("undo",
                              help="откатить: 'last', op:<метка> операции или id записи журнала",
                              parents=[common])
    sub.add_argument("what", metavar="'last'|op:<метка>|<id>")

    args = parser.parse_args(argv)
    try:
        return _run(args)
    except edit.EditError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1


def _run(args):
    if args.operation == "show":
        con = edit.connect()
        try:
            answer = {"ok": True, "revision": revision(), "match": match_row(con, args.match_id)}
        finally:
            con.close()
        print(json.dumps(answer, ensure_ascii=False, indent=2))
        return 0

    response = mutate(args.operation, _operation_args(args), args.editor,
                      persist=args.apply, expect=args.expect)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


def _operation_args(args):
    if args.operation == "set-score":
        return {"match_id": args.match_id, "s1": args.s1, "s2": args.s2}
    if args.operation == "set-players":
        return {"match_id": args.match_id, "sides": [args.a, args.b]}
    if args.operation == "undo":
        return {"what": args.what}
    if args.operation == "void":
        return {"match_id": args.match_id, "reason": args.reason}
    return {"match_id": args.match_id}


if __name__ == "__main__":
    sys.exit(main())
