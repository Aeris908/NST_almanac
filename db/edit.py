"""Единственный путь правки базы — запись с журналом и откатом; интерфейс зовёт эти же функции.

Каждая операция пишет в таблицу `corrections` по одной строке на изменённое поле (старое значение,
новое, редактор, время) и помечает затронутый матч `manual = 1` — после этого импортёр его не
трогает. Откатывает по записям журнала: `undo last` возвращает все поля последней операции,
`undo op:<метка>` — все поля операции, сделанной раньше неё (метка лежит в колонке `corrections.op`),
`undo <id>` — одно конкретное поле.

Ядро операций — функции `set_score`, `set_status`, `unhide`, `undo`: они берут соединение,
возвращают словарь и ничего не печатают. Из них же строит ответы `db/api.py`, поэтому CLI и API
правят базу одним и тем же кодом.

Примеры:
    python db/edit.py show 4412
    python db/edit.py set-score 4412 4 2 --editor aeros
    python db/edit.py set-players 4412 "ectoPower" "sokol & PacnyTHuK" --editor aeros
    python db/edit.py set-source 4412 --note "5:2" --link vk_post=https://vk.com/… --editor aeros
    python db/edit.py add-match "A" "B" --doc blitz_10 --stage Финал --score 3:1 --editor aeros
    python db/edit.py add-tournament my_cup_2026 "Кубок 2026" --category "Спецтурниры" --editor aeros
    python db/edit.py set-doc my_cup_2026 --frame '{"matches": [], "description": "…"}' --editor aeros
    python db/edit.py log
    python db/edit.py undo last
    python db/edit.py undo op:1a2b3c4d5e6f
    python db/edit.py void 4412 --reason "матч не игрался"
    python db/edit.py unhide 4412
"""

import argparse
import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.fields import outcome_of  # noqa: E402
from db import store  # noqa: E402

DB_PATH = store.DB_PATH
TABLES = ("matches", "match_sides", "players", "tournaments", "stages", "match_links",
          "tournament_docs", "side_players", "player_aliases", "incoming")
# Каждая таблица журнала адресуется по `id`: у side_players и player_aliases он появился не зря —
# скрытый SQLite rowid серверная база не повторяет.

# Порядок возврата удалённых строк: родитель раньше детей, иначе FOREIGN KEY не пустит вставку.
RESTORE_ORDER = {"players": 0, "player_aliases": 0, "tournaments": 0, "stages": 0,
                 "tournament_docs": 0, "matches": 2, "match_sides": 3, "side_players": 4,
                 "match_links": 4}
# Псевдо-поле «эта строка появилась (или исчезла) правкой». Журнал умеет обновлять колонки, а
# создание и удаление игры, документа или ссылки он описывает этим полем: значение — снимок
# строки, откат по нему и работает.
EXISTS = "exists"
LINK_KINDS = ("vk_post", "video", "wiki", "api")   # те же значения, что разрешает CHECK в схеме
DOC_MATCH_FIELD = {"special": "matches", "team": "playoff_matches"}
DOC_ROW_KEYS = {"special": ["stage", "p1", "p2", "score"],
                "team": ["league", "t1", "t2", "score"]}


class EditError(ValueError):
    """Правка невозможна: нет матча, другое число сторон, запись уже отменена."""


def connect(db_path=DB_PATH):
    if not store.is_pg(db_path) and not Path(db_path).exists():
        raise EditError(f"Нет базы {db_path}. Сначала: python db/build_db.py && python db/import_stores.py")
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


def journal(con, editor, changes, match_ids, op=""):
    """changes: [(table, row_id, field, old, new)] — записывает и применяет по одному UPDATE.

    Затронутые матчи помечаются manual = 1: после этого импортёр их не пересоздаёт.
    Возвращает id записей журнала — по ним потом откатывать; `op` — метка операции, по которой
    откат забирает её целиком.
    """
    ids = []
    for table, row_id, field, old, new in changes:
        if table not in TABLES:
            raise EditError(f"неизвестная таблица {table}")
        con.execute(
            "insert into corrections(table_name, row_id, field, old_value, new_value, editor, op)"
            " values (?, ?, ?, ?, ?, ?, ?)",
            (table, row_id, field, _text(old), _text(new), editor, op),
        )
        ids.append(con.execute("select last_insert_rowid()").fetchone()[0])
        if field == EXISTS:
            continue  # строку уже вставил или удалил сам вызывающий код — запись нужна для отката
        con.execute(f"update {table} set {field} = ? where id = ?", (_store(new), row_id))
    for match_id in match_ids:
        con.execute("update matches set manual = 1, updated_at = ? where id = ?", (_now(), match_id))
    return ids


def row_json(con, table, row_id):
    """Снимок строки для журнала: по нему откат вернёт удалённую ссылку, игрока или игру.

    Снимок берётся целиком, вместе с `id`: откат вставляет строку на её прежнее место, и номера
    строк состава не съезжают.
    """
    row = con.execute(f"select * from {table} where id = ?", (row_id,)).fetchone()
    if row is None:
        raise EditError(f"строки {table} #{row_id} в базе нет")
    return json.dumps({column: row[column] for column in row.keys()}, ensure_ascii=False)


def restore_row(con, entry):
    """Откат записи `exists`: создание отменяется удалением строки, удаление — возвратом снимка.

    Знак у записи читается из `new_value`: он заполнен, когда правка строку создала, и пуст,
    когда удалила (тогда снимок лежит в `old_value`).
    """
    table, row_id = entry["table_name"], entry["row_id"]
    if entry["new_value"] is not None:
        con.execute(f"delete from {table} where id = ?", (row_id,))
        return
    row = json.loads(entry["old_value"])
    known = {column[1] for column in con.execute(f"pragma table_info({table})")}
    columns = [name for name in row if name != "id" and name in known]
    con.execute(f"insert into {table}(id, {', '.join(columns)}) "
                f"values (?, {', '.join('?' * len(columns))})",
                [row_id] + [row[name] for name in columns])


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _text(value):
    return None if value is None else str(value)


def _store(value):
    if isinstance(value, bool):
        return int(value)
    return value


SIDES_SQL = """
select s.id, s.match_id, s.side_index, s.outcome, s.score, s.label
from match_sides s where s.match_id = ? order by s.side_index
"""

ROSTER_BY_SIDES_SQL = """
select sp.side_id, p.nick from side_players sp join players p on p.id = sp.player_id
where sp.side_id in ({}) order by sp.side_id, sp.seat_index, p.nick
"""


def rosters(con, side_ids):
    """Кто стоит на сторонах — подписью по местам, а не по порядку вставки.

    Один запрос на весь список сторон: `locate` и `search` перебирают связки десятками, и
    выспрашивать состав каждой стороны отдельным подзапросом значило бы платить за каждый ряд.
    """
    wanted = [key for key in dict.fromkeys(side_ids) if key is not None]
    if not wanted:
        return {}
    marks = ", ".join("?" * len(wanted))
    found: dict[int, list] = {}
    for side_id, nick in con.execute(ROSTER_BY_SIDES_SQL.format(marks), wanted):
        found.setdefault(side_id, []).append(str(nick))
    return {key: " & ".join(value) for key, value in found.items()}


def sides_of(con, match_id):
    """Одна строка на сторону. У пары 2×2 на стороне два игрока, и считать их отдельными
    сторонами нельзя: счёт и итог у стороны один.

    Состав читается одним запросом и склеивается здесь, а не `group_concat(... order by ...)`:
    вторая форма требует SQLite не старше 3.44, а версия движка в рантайме публикации — не то,
    от чего должно зависеть то, как человек видит состав.
    """
    cursor = con.execute(SIDES_SQL, (match_id,))
    # Имена колонок берутся у курсора, а не из `sqlite3.Row`: стороны читают и соединения с
    # row_factory, и простые — например сверку очередей.
    names = [column[0] for column in cursor.description]
    sides = [dict(zip(names, values)) for values in cursor]
    found = rosters(con, [side["id"] for side in sides])
    for side in sides:
        side["players"] = found.get(side["id"], "")
    return sides


PAIR_SQL = """
select id from matches
where id = ?
   or duplicate_of = ?
   or hidden_by = ?
   or id in (select duplicate_of from matches where id = ?)
   or id in (select hidden_by from matches where id = ?)
"""


def pair_ids(con, match_id):
    """Все строки одной игры: сама, тот, на кого она указывает, и те, кто указывает на неё.

    Правка обязана идти по всей связке. Игра Сезонов 8–9 лежит в базе двумя строками —
    рейтинговый пул и строка страницы, склеенные uuid: если менять только видимую, таблица
    обновится, а Elo продолжит считать старую. То же со скрытым вторым показом: его вернёт
    `unhide`, и он обязан вернуться исправленным.

    Строки пересоздаются сборкой, поэтому id из старой вкладки редактора уже может ничего не
    означать: без этого отказа правка молчала бы «уже так — ничего не меняю».
    """
    found = [row[0] for row in con.execute(
        PAIR_SQL, (match_id, match_id, match_id, match_id, match_id))]
    if match_id not in found:
        raise EditError(f"Матча {match_id} в базе нет — id строк меняет пересборка, "
                        f"откройте строку заново")
    return found


def set_score(con, match_id, s1, s2, editor):
    """Новый счёт игры: стороны и их исходы пересчитываются, правка идёт по всей связке строк."""
    sides_by_match = {}
    for current in pair_ids(con, match_id):
        match = con.execute("select id, status, note from matches where id = ?", (current,)).fetchone()
        sides = sides_of(con, current)
        if len(sides) != 2:
            raise EditError(f"У матча {current} {len(sides)} сторон — "
                            f"счёт правится только у двухсторонних")
        sides_by_match[current] = (match, sides)

    changes = []
    for current, (match, side_rows) in sides_by_match.items():
        withdrawn = next((index for index, side in enumerate(side_rows) if side["outcome"] == "none"), None)
        if match["status"] == "technical" and withdrawn is not None:
            # Снявшаяся сторона не выиграла и не проиграла: `none` остаётся на ней, иначе
            # «ТП (поражение)» превращается в обычное поражение и портит win_rate.
            outcome_a, outcome_b = ("none", "win") if withdrawn == 0 else ("win", "none")
        else:
            outcome_a, outcome_b = outcome_of(s1, s2)
        for side, score, outcome in zip(side_rows, (s1, s2), (outcome_a, outcome_b)):
            if side["score"] != score:
                changes.append(("match_sides", side["id"], "score", side["score"], score))
            if side["outcome"] != outcome:
                changes.append(("match_sides", side["id"], "outcome", side["outcome"], outcome))
        if all(side["score"] is None for side in side_rows):
            # Строка без счётов показывает в таблице турнира свою подпись («счёт не опубликован…»),
            # а не числа. Как только человек вписал счёт, подпись обязана уйти за ним: иначе правка
            # лежит в базе, а витрина продолжает рассказывать, что счёта нет.
            shown = f"{s1}:{s2}"
            if (match["note"] or "") != shown:
                changes.append(("matches", current, "note", match["note"], shown))
    return _write(con, editor, "set-score", match_id, changes, sorted(sides_by_match))


def roster_of(con, side_id):
    """Состав стороны как текст — ники по местам, через « & ». Порядок детерминированный,
    потому что этот текст ложится в журнал и по нему же состав восстанавливается при откате."""
    return " & ".join(row[0] for row in con.execute(
        """select p.nick from side_players sp join players p on p.id = sp.player_id
            where sp.side_id = ? order by sp.seat_index, p.nick""", (side_id,)))


def canonical_roster(text):
    """Подпись стороны → ники карточек: «sokol & PacnyTHuK» → ['Sokol', 'PacnyTHuK']."""
    from portal.names import clean_alias  # noqa: PLC0415 — один нормализатор на весь проект

    names = [part.strip() for part in str(text or "").split("&") if part.strip()]
    return [clean_alias(name) for name in names]


def sync_side_players(con, side_id, nicks):
    """Пересобрать `side_players` по составу, который вписал человек; вернуть (игроков, новых).

    Пустая сторона невозможна: каталог сезона и рейтинговый пул читают игроков JOIN'ом, и строка
    с пустым составом просто исчезла бы со страницы — молча.
    """
    from db.build_db import ensure_player  # noqa: PLC0415 — тянуть аналитику ради одной вставки нельзя

    seen, created = [], []
    for seat, nick in enumerate(nicks):
        found = con.execute("select id from players where nick = ?", (nick,)).fetchone()
        if found:
            player_id = found[0]
        else:
            try:
                player_id = ensure_player(con, nick, {}, kind="player")
            except SystemExit as error:  # slug уже занят другим ником — двойника не заводим
                raise EditError(str(error)) from None
            created.append(nick)
        if player_id in seen:
            raise EditError(f"игрок «{nick}» назван на одной стороне дважды")
        seen.append(player_id)
        con.execute("insert into side_players(side_id, player_id, seat_index) values (?, ?, ?)",
                    (side_id, player_id, seat))
    return seen, created


def resync_rosters(con, match_ids):
    """Прогнать `match_sides.roster` через `side_players` — после записи и после отката.

    Состав человека и список карточек обязаны оставаться одним и тем же фактом: журнал умеет
    менять только колонки, поэтому откатывает он подпись, а игроков пересобирает этот шаг.
    Возвращает ники, для которых карточку пришлось завести: опечатка в нике создаёт нового
    игрока, и человек обязан увидеть это до того, как удивится двойнику в списке.
    """
    created = []
    for match_id in match_ids:
        rows = con.execute(
            "select id, roster from match_sides where match_id = ? and roster is not null",
            (match_id,)).fetchall()
        for side in rows:
            con.execute("delete from side_players where side_id = ?", (side["id"],))
            _, fresh = sync_side_players(con, side["id"], canonical_roster(side["roster"]))
            created.extend(nick for nick in fresh if nick not in created)
    return created


def shown_by_label(con, match_id):
    """Откуда страница берёт имя этой стороны: из подписи источника или из карточки игрока.

    Таблица турнира (`db/docs.py`) и кубковый справочник печатают `match_sides.label`, каталог
    сезона и рейтинговый пул — `players.nick` через `side_players`. Правка «не тот ник» обязана
    попасть туда, где читатель имя действительно берёт, иначе она ляжет в базу мёртвым грузом.
    """
    row = con.execute("select doc_id, source from matches where id = ?", (match_id,)).fetchone()
    return row["doc_id"] is not None or row["source"] == "cup_tables"


def set_players(con, match_id, sides, editor):
    """Кто играл на каждой стороне: одна подпись человека — и два следствия в базе.

    `side_players` пересобирается по каноническим никам (это карточки, Elo и история сезона), а
    `label` меняется только там, где имени больше неоткуда взять, — и ровно так, как его написал
    человек: он теперь авторитетнее опечатки источника. В журнал старого значения `roster`
    кладывается фактический состав, а не NULL: откат обязан вернуть игроков источника, а не
    оставить сторону пустой.
    """
    linked = pair_ids(con, match_id)
    typed = [re.sub(r"\s+", " ", str(text or "")).strip() for text in (sides or [])]
    rosters = [canonical_roster(text) for text in typed]
    if len(rosters) != 2 or not all(rosters):
        raise EditError('нужны обе стороны: set-players <матч> "A" "B" (пара 2×2 — через « & »)')

    changes = []
    for current in linked:
        side_rows = sides_of(con, current)
        if len(side_rows) != 2:
            raise EditError(f"у матча {current} {len(side_rows)} сторон — состав правится "
                            f"только у двухсторонних")
        label_wins = shown_by_label(con, current)
        for side, text, names in zip(side_rows, typed, rosters):
            roster = " & ".join(names)
            if label_wins and (side["label"] or "") != text:
                changes.append(("match_sides", side["id"], "label", side["label"], text))
            if roster_of(con, side["id"]) != roster:
                changes.append(("match_sides", side["id"], "roster", roster_of(con, side["id"]), roster))
    created = []

    def rebuild():
        created.extend(resync_rosters(con, linked))

    result = _write(con, editor, "set-players", match_id, changes, linked, after=rebuild)
    result["created"] = created
    return result


def side_nicks(con, side_id):
    """Игроки стороны по местам — канонические ники карточек."""
    return [row[0] for row in con.execute(
        """select p.nick from side_players sp join players p on p.id = sp.player_id
            where sp.side_id = ? order by sp.seat_index, p.nick""", (side_id,))]


def container_of(con, spec):
    """Куда ложится новая игра: документ турнира или сезонный бакет — тем же способом, что и импортёр.

    Формы у носителей разные: спецтурнир живёт в `category`, командный в `season_year`, сезон — в
    «Сезон N Высшая лига». Ошибка в этом месте не ломает сборку, а прячет игру на другой странице.
    """
    if spec.get("doc_key"):
        doc = con.execute("select id, kind, title, payload from tournament_docs where doc_key = ?",
                          (spec["doc_key"],)).fetchone()
        if not doc:
            raise EditError(f"Турнира {spec['doc_key']!r} в базе нет — заведите его сначала")
        frame = store.parse_json(doc["payload"], default={})
        if doc["kind"] == "special":
            season = frame.get("category") or "Спецтурниры"
        else:
            season = frame.get("season_year") or "—"
        return {"doc_id": doc["id"], "kind": doc["kind"], "tournament": doc["title"],
                "season": season, "row_set": doc["kind"]}
    season = str(spec.get("season") or "").strip()
    if not season:
        raise EditError("нужен `doc_key` турнира или `season` сезона")
    league = str(spec.get("league") or "").strip()
    return {"doc_id": None, "kind": "cup" if "Кубок" in league else "league",
            "tournament": f"{season} {league or 'лига'}", "season": season, "row_set": "catalog"}


def twin_match(con, container, place, names, s1, s2):
    """Игра с теми же сторонами, туром и счётом уже есть — её правят, а не заводят вторую.

    Ориентация пар не важна: «A 3:2 B» и «B 2:3 A» — одна и та же запись источника.
    """
    key, value = (("m.doc_id", container["doc_id"]) if container["doc_id"]
                  else ("m.tournament_id", None))
    if value is None:
        return None
    rows = con.execute(
        f"""select m.id, sa.id as side_a, sb.id as side_b, sa.score as s1, sb.score as s2
            from matches m
            join match_sides sa on sa.match_id = m.id and sa.side_index = 0
            join match_sides sb on sb.match_id = m.id and sb.side_index = 1
            where m.hidden_by is null and {key} = ? and coalesce(m.tour, '') = ?""",
        (value, place)).fetchall()
    want = frozenset([*names[0], *names[1]])
    for row in rows:
        if frozenset([*side_nicks(con, row["side_a"]), *side_nicks(con, row["side_b"])]) != want:
            continue
        if {row["s1"], row["s2"]} == {s1, s2}:
            return row["id"]
    return None


def add_match(con, spec, editor):
    """Новая игра там, где её не принёс источник: строка, стороны, игроки, ссылки.

    `source='editor'` и `manual = 1` обязательны: без флага ближайший импорт снёс бы строку как
    немаркированную, а отдельный источник нужен затем, чтобы «ручной» пул прошлых лет
    (`source='manual'`) не смешивался с тем, что сюда внёс человек. Порядок `order_in_source` —
    общий счётчик базы, поэтому новая игра становится в конец своего турнира, а не вставляется в
    середину носителя.
    """
    from db.build_db import ensure_stage, ensure_tournament  # noqa: PLC0415

    container = container_of(con, spec)
    stage = str(spec.get("stage") or spec.get("tour") or "Турнир").strip()
    place = str(spec.get("tour") or "").strip()
    names = [canonical_roster(side) for side in (spec.get("sides") or [])]
    if len(names) != 2 or not all(names):
        raise EditError('нужны обе стороны: sides=["A", "B & C"]')
    s1, s2 = spec.get("s1"), spec.get("s2")
    for score in (s1, s2):
        if score is not None and (not isinstance(score, int) or score < 0):
            raise EditError("счёт — целое неотрицательное число или пусто")
    phase = str(spec.get("phase") or "regular")
    if phase not in ("regular", "overtime", "penalties", "overtime_penalties"):
        raise EditError(f"неизвестная фаза {phase!r}")

    tournament_id = ensure_tournament(con, container["tournament"], container["season"], {},
                                      kind=container["kind"])
    stage_id = ensure_stage(con, tournament_id, stage, {})
    twin = twin_match(con, container, place, names, s1, s2)
    if twin:
        raise EditError(f"такая игра уже есть в базе — строка #{twin}, правьте её")

    order = con.execute("select coalesce(max(order_in_source), 0) + 1 from matches").fetchone()[0]
    outcome_a, outcome_b = outcome_of(s1, s2)
    note = str(spec.get("note") or "").strip()
    if not note:
        # Для строки турнира счёт показывает `note`: читатель берёт числа из сторон только когда
        # подпись похожа на счёт. Оставь её пустой — и игра выйдет из таблицы с пустой ячейкой,
        # а история игроков её вообще не заметит.
        note = f"{s1}:{s2}" if s1 is not None and s2 is not None else ""
    con.execute(
        """insert into matches(tournament_id, stage_id, row_set, doc_id, league, tour, is_playoff,
                               phase, order_in_source, status, note, source, source_ref,
                               source_locator, source_text, manual)
           values (?, ?, ?, ?, ?, ?, ?, ?, ?, 'played', ?, 'editor', ?, ?, ?, 1)""",
        (tournament_id, stage_id, container["row_set"], container["doc_id"],
         spec.get("league"), place or None, int(bool(spec.get("playoff"))), phase, order,
         str(note), None,
         f"editor:{container['tournament']}", str(spec.get("source_text") or "")),
    )
    match_id = con.execute("select last_insert_rowid()").fetchone()[0]
    for index, (side_names, score, outcome) in enumerate(
        zip(names, (s1, s2), (outcome_a, outcome_b))
    ):
        con.execute("insert into match_sides(match_id, side_index, outcome, score, label)"
                    " values (?, ?, ?, ?, ?)",
                    (match_id, index, outcome, score, " & ".join(side_names)))
        side_id = con.execute("select last_insert_rowid()").fetchone()[0]
        sync_side_players(con, side_id, side_names)
    for kind, url in _wanted_links(spec.get("links") or []):
        con.execute("insert into match_links(match_id, kind, url) values (?, ?, ?)",
                    (match_id, kind, url))
    changes = [("matches", match_id, EXISTS, None, row_json(con, "matches", match_id))]
    return _write(con, editor, "add-match", match_id, changes, [match_id])


def _wanted_links(links):
    """Список ссылок человека → пары (вид, адрес) с проверкой вида и адреса."""
    pairs = [(str(kind).strip(), str(url).strip()) for kind, url in links]
    if len(set(pairs)) != len(pairs):
        raise EditError("одинаковые ссылки в списке источников")
    for kind, url in pairs:
        if kind not in LINK_KINDS:
            raise EditError(f"ссылка бывает одной из: {', '.join(LINK_KINDS)}")
        if not url.startswith(("http://", "https://")):
            raise EditError(f"«{url}» не похоже на адрес")
    return pairs


def plan_links(con, match_id, links):
    """Ссылки строки заменяются списком целиком: правка источников — это «вот что есть у игры».

    Удаление и вставка — не UPDATE, поэтому каждая запись идёт псевдо-полем `exists` со снимком
    строки: откат вернёт удалённую ссылку и уберёт добавленную.
    """
    wanted = _wanted_links(links)
    current = con.execute("select id, kind, url from match_links where match_id = ?",
                          (match_id,)).fetchall()
    keep = {(row["kind"], row["url"]) for row in current}
    changes = []
    for row in current:
        if (row["kind"], row["url"]) in set(wanted):
            continue
        changes.append(("match_links", row["id"], EXISTS,
                        row_json(con, "match_links", row["id"]), None))
        con.execute("delete from match_links where id = ?", (row["id"],))
    for kind, url in wanted:
        if (kind, url) in keep:
            continue
        con.execute("insert into match_links(match_id, kind, url) values (?, ?, ?)",
                    (match_id, kind, url))
        new_id = con.execute("select last_insert_rowid()").fetchone()[0]
        changes.append(("match_links", new_id, EXISTS, None, row_json(con, "match_links", new_id)))
    return changes


def set_source(con, match_id, editor, note=None, links=None):
    """Что источник говорит об игре: её подпись в таблице и ссылки-доказательства.

    Подпись правится по всей связке — её читают обе строки. Ссылки остаются у строки, на которую
    смотрел человек: доказательство другой строки (например, матча рейтингового пула, которого на
    странице нет) придумывать нечем, а копирование молча заводило бы лишние строки в `match_links`.
    """
    linked = pair_ids(con, match_id)
    changes = []
    if note is not None:
        for current in linked:
            row = con.execute("select note from matches where id = ?", (current,)).fetchone()
            if (row["note"] or "") != note:
                changes.append(("matches", current, "note", row["note"], note))
    if links is not None:
        changes.extend(plan_links(con, match_id, links))
    return _write(con, editor, "set-source", match_id, changes, linked)


def add_video(con, match_id, url, editor):
    """Добавить видео, не заменяя другие источники; операция журналируется и отменяется."""
    from urllib.parse import urlsplit
    value=str(url or '').strip()
    try:
        parsed=urlsplit(value)
        valid=parsed.scheme in ('http','https') and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:valid=False
    if not valid or len(value)>4096 or any(ch.isspace() for ch in value):
        raise EditError('Вставьте полную ссылку на страницу видео, начиная с https://. Сам файл загружать не нужно.')
    links=[[r['kind'],r['url']] for r in con.execute('select kind,url from match_links where match_id=? order by id',(match_id,))]
    if ['video',value] not in links:links.append(['video',value])
    result=set_source(con,match_id,editor,links=links)
    result['operation']='add-video'
    return result


def add_tournament(con, spec, editor):
    """Новый турнир: рамка-документ с пустым списком игр.

    Список игр в рамке обязан остаться пустым и ключи строк заданы: читатель навешивает игры на
    то же место, а не строит форму сам, — иначе порядок ключей страницы поедет.
    """
    doc_key = str(spec.get("doc_key") or "").strip()
    title = str(spec.get("title") or "").strip()
    kind = str(spec.get("kind") or "special")
    if not doc_key or not title:
        raise EditError("нужны `doc_key` и `title`")
    if kind not in DOC_MATCH_FIELD:
        raise EditError(f"новый турнир бывает {' или '.join(DOC_MATCH_FIELD)}")
    if con.execute("select 1 from tournament_docs where doc_key = ?", (doc_key,)).fetchone():
        raise EditError(f"турнир {doc_key!r} уже заведён")
    field, keys = DOC_MATCH_FIELD[kind], DOC_ROW_KEYS[kind]
    frame = {**dict(spec.get("frame") or {}), "id": doc_key, "title": title,
             "row_keys": keys, field: []}
    order = con.execute("select coalesce(max(order_index), -1) + 1 from tournament_docs where kind = ?",
                        (kind,)).fetchone()[0]
    con.execute(
        """insert into tournament_docs(kind, doc_key, title, payload, match_field, match_keys,
                                      manual, order_index)
           values (?, ?, ?, ?, ?, ?, 1, ?)""",
        (kind, doc_key, title, json.dumps(frame, ensure_ascii=False), field,
         json.dumps(keys, ensure_ascii=False), order),
    )
    doc_id = con.execute("select last_insert_rowid()").fetchone()[0]
    changes = [("tournament_docs", doc_id, EXISTS, None, row_json(con, "tournament_docs", doc_id))]
    return _write(con, editor, "add-tournament", doc_id, changes, [])


def set_doc(con, doc_key, editor, title=None, frame=None):
    """Рамка турнира словами человека: заголовок, описание, хроника, итоговые таблицы.

    Список игр в рамке обязан остаться на месте (пустым): читатель навешивает строки по ключу
    документа, и если человек его сотрёт, турнир на странице осиротеет без единого сообщения.
    """
    doc = con.execute("select id, title, payload, manual, match_field from tournament_docs"
                      " where doc_key = ?", (doc_key,)).fetchone()
    if not doc:
        raise EditError(f"Турнира {doc_key!r} в базе нет")
    changes = []
    if title:
        if doc["title"] != title:
            changes.append(("tournament_docs", doc["id"], "title", doc["title"], title))
    if frame is not None:
        if doc["match_field"] not in frame:
            raise EditError(f"в рамке нет ключа «{doc['match_field']}» — игры турнира исчезнут")
        text = json.dumps(frame, ensure_ascii=False)
        if doc["payload"] != text:
            changes.append(("tournament_docs", doc["id"], "payload", doc["payload"], text))
    if changes and not doc["manual"]:
        # Флаг рамки говорит импортёру не перезаписывать документ носителем (db/docs.store_docs).
        changes.append(("tournament_docs", doc["id"], "manual", doc["manual"], 1))
    return _write(con, editor, "set-doc", doc["id"], changes, [])


RATING_CHECK_SQL = """
select t.season, t.name as tournament, m.played_on, m.source_date_raw, m.status, m.hidden_by,
       m.duplicate_of,
       sa.score as s1, sb.score as s2,
       json_extract(d.payload, '$.season_year') as doc_year,
       (select count(*) from side_players sp where sp.side_id = sa.id) as n1,
       (select count(*) from side_players sp where sp.side_id = sb.id) as n2
from matches m
join tournaments t on t.id = m.tournament_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
left join tournament_docs d on d.id = m.doc_id
where m.id = ?
"""


def unrateable_reason(con, match_id):
    """Почему эту строку нельзя взять в рейтинг; None — можно.

    Рейтинг считается последовательно и только по 1×1: партия без года встала бы в ряд наугад,
    партия без счёта не даёт исхода, а 2×2 вьюха пула просто не отдаёт (и игра молча
    «не считается», что хуже честного отказа).
    """
    from portal import elo  # noqa: PLC0415 — год партии знает только движок рейтинга

    row = con.execute(RATING_CHECK_SQL, (match_id,)).fetchone()
    if not row:
        return "такой строки матча нет в базе"
    if row["status"] == "void":
        return "матч снят с зачёта"
    if row["hidden_by"]:
        return "это второй показ той же игры на витрине"
    if row["duplicate_of"]:
        return "эта строка помечена дублем другой — рейтингом считается та, на которую она указывает"
    if row["s1"] is None or row["s2"] is None:
        return "у сторон нет числового счёта"
    if row["n1"] != 1 or row["n2"] != 1:
        return "в рейтинг берутся только матчи 1×1: у 2×2 нет одного соперника на сторону"
    try:
        elo.rating_year({key: row[key] for key in ("season", "tournament", "played_on",
                                                   "source_date_raw", "doc_year")})
    except elo.EloError:
        return "у партии не из чего вывести год — рейтинг считается последовательно"
    return None


def set_rating(con, match_id, rated, editor):
    """Брать ли партию в расчёт Elo: флаг `in_rating_pool` по всей связке строк."""
    linked = pair_ids(con, match_id)
    if rated:
        for current in linked:
            reason = unrateable_reason(con, current)
            if reason:
                raise EditError(f"в рейтинг нельзя: {reason}")
    changes = []
    for current in linked:
        row = con.execute("select in_rating_pool from matches where id = ?", (current,)).fetchone()
        if bool(row["in_rating_pool"]) != bool(rated):
            changes.append(("matches", current, "in_rating_pool", row["in_rating_pool"],
                            1 if rated else 0))
        elif not rated and not con.execute("select 1 from corrections where table_name='matches' "
                "and row_id=? and field='in_rating_pool' and new_value='0' and reverted_at is null limit 1",(current,)).fetchone():
            # v2 автоматически включает сезонные встречи. Явное исключение — отдельное намерение,
            # даже когда старый импортный флаг уже равен 0; undo снимает именно это намерение.
            changes.append(('matches',current,'in_rating_pool',0,0))
    return _write(con, editor, "set-rating", match_id, changes, linked)


def set_rating_scope(con, rated, editor, season=None, doc_key=None):
    """Флаг рейтинга сразу для всего сезона или всего турнира — и отказ по строкам-кандидатам.

    Одиночный переключатель здесь бесполезен: в архиве тысячи подходящих партий, и отмечать их
    кликом никто не будет. Поэтому список берётся целиком, а то, что в рейтинг взять нельзя,
    считается и показывается человеку — молча пропустить такую строку значит оставить сезон
    посчитанным наполовину.
    """
    if bool(season) == bool(doc_key):
        raise EditError("нужно что-то одно: season или doc_key")
    if doc_key:
        rows = con.execute(
            """select m.id from matches m join tournament_docs d on d.id = m.doc_id
                where d.doc_key = ? order by m.order_in_source""", (doc_key,)).fetchall()
    else:
        rows = con.execute(
            """select m.id from matches m join tournaments t on t.id = m.tournament_id
                where t.season = ? order by m.order_in_source""", (season,)).fetchall()

    changes, skipped = [], {}
    for row in rows:
        current = row["id"]
        if rated:
            reason = unrateable_reason(con, current)
            if reason:
                skipped[reason] = skipped.get(reason, 0) + 1
                continue
        state = con.execute("select in_rating_pool from matches where id = ?", (current,)).fetchone()[0]
        if bool(state) != bool(rated):
            changes.append(("matches", current, "in_rating_pool", state, 1 if rated else 0))
        elif not rated and not con.execute("select 1 from corrections where table_name='matches' "
                "and row_id=? and field='in_rating_pool' and new_value='0' and reverted_at is null limit 1",(current,)).fetchone():
            changes.append(('matches',current,'in_rating_pool',0,0))
    result = _write(con, editor, "set-rating", rows[0] if rows else 0, changes,
                    [change[1] for change in changes])
    result["skipped"] = skipped
    result["scope"] = {"season": season, "doc_key": doc_key, "rows": len(rows)}
    return result


def set_place(con, match_id, editor, tour=None, league=None, stage=None):
    """Где игра лежала: тур, дивизион и этап. Правка идёт по всей связке строк.

    Это не косметика: страница группирует строки по туру и дивизиону, а ошибки разбора живут
    именно там — «встреча помечена группой F, а соперник играет в C». Этап выбирается по названию
    через `ensure_stage`, чтобы не плодить сущих стадий на одну и ту же строку сезона.
    """
    from db.build_db import ensure_stage  # noqa: PLC0415 — тяжёлый импорт только при правке этапа

    if tour is None and league is None and stage is None:
        raise EditError("не указано ни одного места: --tour, --league или --stage")
    linked = pair_ids(con, match_id)
    changes, stages = [], {}
    for current in linked:
        row = con.execute(
            """select m.tournament_id, m.tour, m.league, m.stage_id, m.source_ref, m.source_place,
                      s.name as stage
               from matches m join stages s on s.id = m.stage_id where m.id = ?""",
            (current,)).fetchone()
        if tour is not None and (row["tour"] or "") != tour:
            changes.append(("matches", current, "tour", row["tour"], tour))
        if league is not None and (row["league"] or "") != league:
            changes.append(("matches", current, "league", row["league"], league))
        if stage:
            stage_id = ensure_stage(con, row["tournament_id"], stage, stages)
            if row["stage_id"] != stage_id:
                changes.append(("matches", current, "stage_id", row["stage_id"], stage_id))
        moved = tour is not None or stage is not None
        if moved and not row["source_ref"] and not row["source_place"]:
            # Строка носителя опознаётся импортом по «документ + тур + стороны + счёт»: перенесём
            # её в другой тур молча — и следующий импорт принесёт ту же игру вторым рядом.
            # Память о месте источника оставляет импортёру оба ключа.
            changes.append(("matches", current, "source_place", row["source_place"],
                            row["tour"] or row["stage"]))
    return _write(con, editor, "set-place", match_id, changes, linked)


DATE_SHAPES = (("^\\d{4}-\\d{2}-\\d{2}$", "exact", "%Y-%m-%d"),
               ("^\\d{4}-\\d{2}$", "month", "%Y-%m"),
               ("^\\d{4}$", "season", "%Y"))
PHASES = ("regular", "overtime", "penalties", "overtime_penalties")


def _date_shape(value):
    """Формат даты и точность, которую база умеет хранить; None — если строка не дата.

    Регулярка ловит и «2024-13-45», поэтому дата проверяется ещё и календарём: несуществующий
    день человек печатает легко, а `played_on` потом читает Elo как порядок партий.
    """
    text = str(value or "").strip()
    for pattern, precision, fmt in DATE_SHAPES:
        if not re.match(pattern, text):
            continue
        try:
            datetime.strptime(text, fmt)
        except ValueError:
            return None, None
        return text, precision
    return None, None


def set_date(con, match_id, editor, played_on=None, source_date_raw=None):
    """Когда играли: дата человека и дата, как её записал источник.

    Дата — это не только подписанный год: без неё партия не попадает в рейтинг, который считается
    последовательно, и у неё не определяется сезон простоя. `source_date_raw` остаётся дословным
    словом источника (unix-секунды ВК, год кубкового справочника), а `played_on` — тем, что
    увидел человек; точность пишется по форме, иначе `date_precision` врёт.
    """
    linked = pair_ids(con, match_id)
    if played_on is not None:
        text, precision = _date_shape(played_on)
        if text is None:
            raise EditError("дата бывает «ГГГГ», «ГГГГ-ММ» или «ГГГГ-ММ-ДД»")
    changes = []
    for current in linked:
        row = con.execute("select played_on, date_precision, source_date_raw from matches where id = ?",
                          (current,)).fetchone()
        if played_on is not None and (row["played_on"] or "") != text:
            changes.append(("matches", current, "played_on", row["played_on"], text))
            if row["date_precision"] != precision:
                changes.append(("matches", current, "date_precision", row["date_precision"], precision))
        if source_date_raw is not None and (row["source_date_raw"] or "") != source_date_raw:
            changes.append(("matches", current, "source_date_raw", row["source_date_raw"],
                            source_date_raw))
    return _write(con, editor, "set-date", match_id, changes, linked)


def phase_problem(s1, s2, outcome_a, outcome_b, phase):
    """Почему фаза не сходится с исходами; None — сходится.

    Повторяет два инварианта `db/validate.py` («исход не согласован со счётом» и «равный счёт в
    не regular-этапе с левым исходом»): без этого правка прошла бы в базу и роняла бы сборку на
    валидаторе, а человек узнал бы о проблеме только там.
    """
    if phase == "regular" or s1 is None or s2 is None:
        return None
    if s1 == s2:
        pair = {outcome_a, outcome_b}
        if pair not in ({"draw"}, {"win", "loss"}):
            return "при равном счёте исходы обязаны быть ничьей либо парой победа/поражение"
        return None
    winner, loser = (outcome_a, outcome_b) if s1 > s2 else (outcome_b, outcome_a)
    if winner != "win" or loser != "loss":
        return "исходы не следуют за счётом — сначала поправь их через счёт матча"
    return None


def set_phase(con, match_id, editor, phase=None, playoff=None):
    """Цена результата: овертайм, буллиты и то, плей-офф это или регулярка.

    Фаза меняет не только подпись: победа в овертайме или по буллитам стоит 0.75 вместо 1, а
    плей-офф получает K=32. Поэтому правка сверяется с исходами до записи.
    """
    if phase is None and playoff is None:
        raise EditError("не указано ни `phase`, ни `playoff`")
    if phase is not None and phase not in PHASES:
        raise EditError(f"фаза бывает одной из: {', '.join(PHASES)}")
    linked = pair_ids(con, match_id)
    changes = []
    for current in linked:
        row = con.execute(
            """select m.phase, m.is_playoff, sa.score s1, sb.score s2, sa.outcome o1, sb.outcome o2
               from matches m
               join match_sides sa on sa.match_id = m.id and sa.side_index = 0
               join match_sides sb on sb.match_id = m.id and sb.side_index = 1
               where m.id = ?""", (current,)).fetchone()
        if phase is not None and row["phase"] != phase:
            reason = phase_problem(row["s1"], row["s2"], row["o1"], row["o2"], phase)
            if reason:
                raise EditError(f"фаза {phase!r} не сходится с этой партией: {reason}")
            changes.append(("matches", current, "phase", row["phase"], phase))
        if playoff is not None and bool(row["is_playoff"]) != bool(playoff):
            changes.append(("matches", current, "is_playoff", row["is_playoff"], int(bool(playoff))))
    return _write(con, editor, "set-phase", match_id, changes, linked)


def descendants(con, match_id):
    """Снимки всего, что висит на строке матча: стороны, её игроки и ссылки."""
    out = []
    for side in con.execute("select id from match_sides where match_id = ?", (match_id,)):
        out.append(("match_sides", side["id"], EXISTS, row_json(con, "match_sides", side["id"]), None))
        for seat in con.execute("select id from side_players where side_id = ?", (side["id"],)):
            out.append(("side_players", seat["id"], EXISTS,
                        row_json(con, "side_players", seat["id"]), None))
    for link in con.execute("select id from match_links where match_id = ?", (match_id,)):
        out.append(("match_links", link["id"], EXISTS, row_json(con, "match_links", link["id"]), None))
    return out


def drop_match(con, match_id, editor):
    """Удалить игру вместе со сторонами, составом и ссылками; откат возвращает всё.

    Для витрины есть `void` — он обратим и ничего не стирает из архива. Удаление нужно там, где
    строки не должно быть вовсе: задвоенный вручную внесённый матч или ошибка самого редактора.
    Ссылки на строку извне связки (`duplicate_of`, `hidden_by`) оставили бы висячий указатель,
    поэтому здесь отказ; сами же строки связки уходят вместе, и их внутренние указатели гасятся
    заранее — иначе FOREIGN KEY падает на первом же удалении. Задача редактуры, которая смотрела
    на эту игру, остаётся в очереди без строки.
    """
    linked = pair_ids(con, match_id)
    for current in linked:
        pointing = con.execute(
            f"""select count(*) from matches
                 where (duplicate_of = ? or hidden_by = ?)
                   and id not in ({', '.join('?' * len(linked))})""",
            (current, current, *linked)).fetchone()[0]
        if pointing:
            raise EditError(f"на строку #{current} ссылается {pointing} других — "
                            f"сначала разбери дубли, потом удаляй")
    changes = []
    # Сначала гасим указатели по всей связке, потом удаляем: каталожная строка ссылается на
    # пуловую, и удаление их вперемешку ловит FOREIGN KEY на середине обхода.
    for current in linked:
        for field in ("duplicate_of", "hidden_by"):
            held = con.execute(f"select {field} from matches where id = ?", (current,)).fetchone()[0]
            if held is not None and held in linked:
                changes.append(("matches", current, field, held, None))
                con.execute(f"update matches set {field} = null where id = ?", (current,))
        for task in con.execute("select id from incoming where matched_match_id = ?", (current,)):
            changes.append(("incoming", task["id"], "matched_match_id", current, None))
            con.execute("update incoming set matched_match_id = null where id = ?", (task["id"],))
    for current in linked:
        changes.extend(descendants(con, current))
        changes.append(("matches", current, EXISTS, row_json(con, "matches", current), None))
        con.execute("delete from matches where id = ?", (current,))
    return _write(con, editor, "drop-match", match_id, changes, [])


def drop_tournament(con, doc_key, editor):
    """Удалить турнир-документ, в котором не осталось игр."""
    doc = con.execute("select id, title from tournament_docs where doc_key = ?", (doc_key,)).fetchone()
    if not doc:
        raise EditError(f"Турнира {doc_key!r} в базе нет")
    games = con.execute("select count(*) from matches where doc_id = ?", (doc["id"],)).fetchone()[0]
    if games:
        raise EditError(f"в турнире «{doc['title']}» ещё {games} игр — удали их сначала")
    changes = [("tournament_docs", doc["id"], EXISTS, row_json(con, "tournament_docs", doc["id"]), None)]
    con.execute("delete from tournament_docs where id = ?", (doc["id"],))
    return _write(con, editor, "drop-tournament", doc["id"], changes, [])


def rename_player(con, player_id, nick, editor):
    """Новое написание ника у той же карточки: партии, ссылки и история остаются на месте.

    `slug` правится вместе с ником, иначе ссылка в адресе начнёт вести в чужую карточку. Занятый
    чужим игроком slug — отказ: два игрока на один slug это ровно то, из-за чего UI врёт.
    """
    from db.build_db import slugify  # noqa: PLC0415

    nick = str(nick or "").strip()
    if not nick:
        raise EditError("ник не может быть пустым")
    player = con.execute("select id, nick, slug from players where id = ?", (player_id,)).fetchone()
    if not player:
        raise EditError(f"Игрока {player_id} в базе нет")
    slug = slugify(nick)
    clash = con.execute("select nick from players where slug = ? and id <> ?", (slug, player_id)).fetchone()
    if clash:
        raise EditError(f"slug «{slug}» уже носит «{clash[0]}» — было бы две карточки на одну ссылку")
    changes = []
    if player["nick"] != nick:
        changes.append(("players", player_id, "nick", player["nick"], nick))
    if player["slug"] != slug:
        changes.append(("players", player_id, "slug", player["slug"], slug))
    return _write(con, editor, "rename-player", 0, changes, [])


def merge_player(con, keep_id, drop_id, editor):
    """Слить две карточки в одну: партии переезжают, ушедшее написание становится алиасом.

    Откатывает по журналу целиком: `player_id` у сторон обратно, алиас и карточка возвращаются.
    Если игрок уже играл сам против себя (обе стороны одной встречи), слияние породило бы матч
    против самого себя — такой случай отказывается до записи.
    """
    keep = con.execute("select id, nick from players where id = ?", (keep_id,)).fetchone()
    drop = con.execute("select id, nick from players where id = ?", (drop_id,)).fetchone()
    if not keep or not drop:
        raise EditError("обе карточки должны существовать")
    if keep_id == drop_id:
        raise EditError("нельзя слить карточку саму с собой")
    clash = con.execute(
        """select s.match_id from match_sides s
            join side_players sp on sp.side_id = s.id
           where s.match_id in (select s2.match_id from match_sides s2
                                  join side_players sp2 on sp2.side_id = s2.id
                                 where sp2.player_id = ?)
             and sp.player_id = ?
        """, (keep_id, drop_id)).fetchone()
    if clash:
        raise EditError(f"«{drop['nick']}» уже играл против «{keep['nick']}» (матч #{clash[0]}) — "
                        f"слияние посадило бы игрока по обе стороны одной игры")

    changes = []
    for seat in con.execute("select side_id, id from side_players where player_id = ?", (drop_id,)):
        together = con.execute(
            "select id from side_players where side_id = ? and player_id = ?",
            (seat["side_id"], keep_id)).fetchone()
        if together:
            # оставляемый уже стоит в этой стороне: двух одинаковых строк UNIQUE (side_id,
            # player_id) не пустил бы, поэтому слияние здесь просто убирает лишнюю.
            changes.append(("side_players", seat["id"], EXISTS,
                            row_json(con, "side_players", seat["id"]), None))
            con.execute("delete from side_players where id = ?", (seat["id"],))
        else:
            changes.append(("side_players", seat["id"], "player_id", drop_id, keep_id))
            con.execute("update side_players set player_id = ? where id = ?", (keep_id, seat["id"]))
    alias = (drop["nick"],)
    if not con.execute("select 1 from player_aliases where alias = ?", alias).fetchone():
        con.execute("insert into player_aliases(alias, player_id, source) values (?, ?, 'editor')",
                    (drop["nick"], keep_id))
        row_id = con.execute("select id from player_aliases where alias = ?", alias).fetchone()[0]
        changes.append(("player_aliases", row_id, EXISTS, None,
                        row_json(con, "player_aliases", row_id)))
    changes.append(("players", drop_id, EXISTS, row_json(con, "players", drop_id), None))
    con.execute("delete from players where id = ?", (drop_id,))
    return _write(con, editor, "merge-player", 0, changes, [])


def set_provenance(con, match_id, editor, source=None, source_ref=None, source_locator=None,
                   source_page=None, source_text=None):
    """Что и откуда взялось: источник, его ключ, где искать и как он это описал.

    Это самая опасная правка редактора, и она не запрещена, а объяснена: `source_ref` — ключ, по
    которому импортёр узнаёт строку при следующей сборке. Меняешь его у уже загруженной игры —
    старый ключ свободен, и источник принесёт ту же партию вторым рядом; база тогда спрячет
    копию за ручной строкой, но спор ляжет в очередь редактуры. Предпросмотр это молчит, поэтому
    отказ здесь только на явном повторе ключа.

    Правится одна строка, а не связка: происхождение — это свойство носителя, и у двух строк одной
    игры их два (`(source, source_ref)` в базе уникален — общий ключ связке дал бы конфликт).
    """
    linked = pair_ids(con, match_id)
    fields = {"source": source, "source_ref": source_ref, "source_locator": source_locator,
              "source_page": source_page, "source_text": source_text}
    wanted = {name: value for name, value in fields.items() if value is not None}
    if not wanted:
        raise EditError("не указано ни одного поля происхождения")
    row = con.execute("select source from matches where id = ?", (match_id,)).fetchone()
    if "source_ref" in wanted:
        taken = con.execute(
            "select id from matches where source = ? and source_ref = ? and id <> ?",
            (wanted.get("source") or row["source"], wanted["source_ref"], match_id)).fetchone()
        if taken:
            raise EditError(f"такой ключ источника уже носит строка #{taken['id']}")
    current = con.execute(f"select {', '.join(wanted)} from matches where id = ?",
                          (match_id,)).fetchone()
    changes = [("matches", match_id, name, current[name], value)
               for name, value in wanted.items() if current[name] != value]
    return _write(con, editor, "set-provenance", match_id, changes, linked)


def set_status(con, match_id, status, editor, reason=""):
    """Снять игру с зачёта (`void`) или вернуть её (`played`) — по всей связке строк."""
    linked = pair_ids(con, match_id)
    changes = []
    for current in linked:
        match = con.execute("select id, status, note from matches where id = ?", (current,)).fetchone()
        if match["status"] != status:
            changes.append(("matches", current, "status", match["status"], status))
        if status == "void" and reason and reason != match["note"]:
            changes.append(("matches", current, "note", match["note"], reason))
        if status == "played" and match["status"] == "void":
            changes.append(("matches", current, "note", match["note"], ""))
    return _write(con, editor, "set-status", match_id, changes, linked)


def unhide(con, match_id, editor):
    """Вернуть на витрину строку, скрытую как второй показ той же игры.

    Одну строку, а не всю связку: `hidden_by` и есть «этот показ лишний», и решают по месту.
    """
    match = con.execute("select id, hidden_by from matches where id = ?", (match_id,)).fetchone()
    if not match:
        raise EditError(f"Матча {match_id} нет")
    changes = []
    if match["hidden_by"] is not None:
        changes.append(("matches", match_id, "hidden_by", match["hidden_by"], None))
    return _write(con, editor, "unhide", match_id, changes)


def _write(con, editor, operation, match_id, changes, match_ids=None, after=None):
    """Один шаг правки: журнал, применение, commit. Пустой `changes` — законное «ничего не менять».

    `match_ids` — вся связка строк, которой принадлежит правка (см. `pair_ids`): все они получают
    `manual = 1`, иначе импортёр пересоздаст половину игры и правка разъедется с данными источника.
    Пустой список — правка вообще не про матчи (создание турнира), и он НЕ должен молча
    превращаться в `[match_id]`: там этот номер значит строку матча, а не документа.
    `after` — что сделать с производными таблицами перед commit: состав игроков не колонка, и
    разрыв между «подпись изменена» и «карточки пересобраны» должен быть невидим.
    """
    linked = [match_id] if match_ids is None else match_ids
    op = uuid.uuid4().hex[:12]
    ids = journal(con, editor, changes, linked, op) if changes else []
    if changes and after:
        after()
    con.commit()
    return {"operation": operation, "match_id": match_id, "changes": changes,
            "journal": ids, "linked": linked, "op": op}


def cmd_show(con, args):
    match = con.execute(
        """select m.*, t.season, t.name tournament, s.name stage, d.title doc_title
           from matches m
           join tournaments t on t.id = m.tournament_id
           join stages s on s.id = m.stage_id
           left join tournament_docs d on d.id = m.doc_id
           where m.id = ?""", (args.match_id,)).fetchone()
    if not match:
        raise EditError(f"Матча {args.match_id} нет")
    for key in match.keys():
        if key in ("tournament_id", "stage_id", "doc_id", "doc_title"):
            continue
        print(f"  {key:16} {match[key]!r}")
    if match["doc_title"]:
        print(f"  документ         {match['doc_title']!r} — счёт в таблице турнира читатель берёт "
              f"со сторон, а `note` остаётся надписью источника")
    print("  стороны:")
    for side in sides_of(con, args.match_id):
        print(f"    [{side['side_index']}] {side['players'] or '—':22} подписано={side['label']!r} "
              f"счёт={side['score']!r} итог={side['outcome']}")
    return 0


def _print_changes(result):
    if not result["changes"]:
        print("уже так — ничего не меняю")
        return
    for table, row_id, field, old, new in result["changes"]:
        print(f"  {table}.{row_id} {field}: {old!r} -> {new!r}")
    print(f"записано в журнал: {', '.join(str(i) for i in result['journal'])}; "
          f"откат целиком: python db/edit.py undo op:{result['op']}; "
          f"пересоберите: python build_all.py")


def cmd_set_score(con, args):
    _print_changes(set_score(con, args.match_id, args.s1, args.s2, args.editor))
    return 0


def cmd_set_players(con, args):
    _print_changes(set_players(con, args.match_id, [args.a, args.b], args.editor))
    return 0


def cmd_set_place(con, args):
    _print_changes(set_place(con, args.match_id, args.editor, args.tour, args.league, args.stage))
    return 0


def cmd_set_date(con, args):
    _print_changes(set_date(con, args.match_id, args.editor, args.played_on, args.source_date_raw))
    return 0


def cmd_set_phase(con, args):
    playoff = None if args.playoff is None else int(args.playoff != "no")
    _print_changes(set_phase(con, args.match_id, args.editor, args.phase, playoff))
    return 0


def cmd_set_provenance(con, args):
    _print_changes(set_provenance(con, args.match_id, args.editor, args.source, args.source_ref,
                                  args.source_locator, args.source_page, args.source_text))
    return 0


def cmd_drop_match(con, args):
    _print_changes(drop_match(con, args.match_id, args.editor))
    return 0


def cmd_drop_tournament(con, args):
    _print_changes(drop_tournament(con, args.doc_key, args.editor))
    return 0


def cmd_rename_player(con, args):
    _print_changes(rename_player(con, args.player_id, args.nick, args.editor))
    return 0


def cmd_merge_player(con, args):
    _print_changes(merge_player(con, args.keep_id, args.drop_id, args.editor))
    return 0


def cmd_set_source(con, args):
    links = None
    if args.link is not None:
        links = [pair.split("=", 1) for pair in args.link]
        bad = [pair for pair in links if len(pair) != 2]
        if bad:
            raise EditError("--link пишется как ВИД=АДРЕС, например vk_post=https://vk.com/…")
    _print_changes(set_source(con, args.match_id, args.editor, args.note, links))
    return 0


def cmd_add_match(con, args):
    scores = None
    if args.score:
        parts = re.split(r"[:\-\u2013]", args.score)
        if len(parts) != 2 or not all(part.strip().isdigit() for part in parts):
            raise EditError("--score пишется как «5:2»")
        scores = (int(parts[0]), int(parts[1]))
    spec = {"doc_key": args.doc_key, "season": args.season, "league": args.league,
            "stage": args.stage, "tour": args.tour, "sides": [args.a, args.b],
            "s1": scores[0] if scores else None, "s2": scores[1] if scores else None,
            "note": args.note}
    _print_changes(add_match(con, spec, args.editor))
    return 0


def cmd_add_tournament(con, args):
    _print_changes(add_tournament(con, {"doc_key": args.doc_key, "title": args.title,
                                       "kind": args.kind, "frame": {"category": args.category}},
                                 args.editor))
    return 0


def cmd_set_doc(con, args):
    frame = store.parse_json(args.frame) if args.frame else None
    _print_changes(set_doc(con, args.doc_key, args.editor, args.title, frame))
    return 0


def cmd_set_rating(con, args):
    _print_changes(set_rating(con, args.match_id, not args.off, args.editor))
    return 0


def cmd_rate_scope(con, args):
    result = set_rating_scope(con, not args.off, args.editor, args.season, args.doc_key)
    scope = result["scope"]
    print(f"  затронуто строк: {len(result['changes'])} из {scope['rows']} "
          f"({scope['season'] or scope['doc_key']})")
    for reason, count in sorted(result["skipped"].items()):
        print(f"  пропущено {count}: {reason}")
    if not result["changes"]:
        print("уже так — ничего не меняю")
    else:
        print(f"записано в журнал: {', '.join(str(i) for i in result['journal'])}; "
              f"откат целиком: python db/edit.py undo op:{result['op']}; "
              f"пересоберите: python build_all.py")
    return 0


def cmd_status(con, args, status):
    _print_changes(set_status(con, args.match_id, status, args.editor, args.reason))
    return 0


def cmd_unhide(con, args):
    result = unhide(con, args.match_id, args.editor)
    if not result["changes"]:
        print("эта строка и так показывается")
        return 0
    _print_changes(result)
    return 0


def cmd_log(con, args):
    rows = con.execute(
        """select id, table_name, row_id, field, old_value, new_value, editor, created_at,
                  reverted_at, op from corrections order by id desc limit ?""", (args.limit,)).fetchall()
    if not rows:
        print("журнал пуст")
        return 0
    for r in rows:
        flag = f" [отменено {r['reverted_at']}]" if r["reverted_at"] else ""
        print(f"  #{r['id']:<4} {r['created_at']} {r['editor']:<10} {r['table_name']}.{r['row_id']} "
              f"{r['field']}: {r['old_value']!r} -> {r['new_value']!r}{flag} [op:{r['op']}]")
    print("откат целиком: python db/edit.py undo op:<метка>")
    return 0


LIVE_CORRECTIONS_FOR_MATCH = """
select exists(
    select 1 from corrections
    where reverted_at is null and (
        (table_name = 'matches' and row_id = ?)
        or (table_name = 'match_sides'
            and row_id in (select id from match_sides where match_id = ?))
        or (table_name = 'match_links'
            and row_id in (select id from match_links where match_id = ?))
        or (table_name = 'side_players'
            and row_id in (select sp.id from side_players sp
                             join match_sides s on s.id = sp.side_id where s.match_id = ?))
    )
)
"""


# Источники, чьи строки рождаются с `manual = 1` и импортёром не пересоздаются: демо-посев
# (`db/demo_disciplines.py`) и строки, заведённые редактором. Для них флаг — не защита правки,
# а единственная броня от сметки `reset_previous_imports`: снять его после отката значило бы
# отдать строку на удаление ближайшей сборке. Возвращать к носителю такие строки нельзя.
BORN_MANUAL_SOURCES = ("demo", "editor")


def release_unedited(con, match_ids):
    """Снимает `manual` с игры, для которой не осталось ни одной действующей правки.

    Флаг — защита строки от импортёра, а не память о том, что её когда-то трогали: после отката
    строка снова обычная строка носителя, и оставить её «ручной» значило бы, что каждая
    проверочная правка навсегда выламывает кусок витрины из пересборки базы. Исключение —
    строки из `BORN_MANUAL_SOURCES`: они носителями не были и флаг носят с рождения.

    Смотреть надо на всю связку: `manual` ставится всем её строкам, а запись журнала может касаться
    одной (правка происхождения). Откатить дату и снять флаг с парной копии — значит выдать
    импортёру строку, на которой ещё висит чужая правка.
    """
    released = 0
    for match_id in match_ids:
        try:
            linked = pair_ids(con, match_id)
        except EditError:
            linked = [match_id]
        if any(con.execute(LIVE_CORRECTIONS_FOR_MATCH, (current,) * 4).fetchone()[0]
               for current in linked):
            continue
        for current in linked:
            source = con.execute("select source from matches where id = ?", (current,)).fetchone()
            # Флаг ставится на всю связку (`_write`), с него вся связка и возвращается: иначе
            # парная копия осталась бы «ручной» и выпала из пересборки базы навсегда. Строки из
            # `BORN_MANUAL_SOURCES` флаг носят с рождения — с них его не снимаем.
            if not (source and source[0] in BORN_MANUAL_SOURCES):
                released += con.execute("update matches set manual = 0 where id = ?",
                                        (current,)).rowcount
            # Состав, записанный человеком, — такое же право на строку, как и `manual`: раз правок
            # не осталось, строка снова принадлежит импортёру, и колонка не должна помнить тест.
            con.execute("update match_sides set roster = null where match_id = ?", (current,))
    return released


OP_PREFIX = "op:"


def _live_entries(con, op):
    """Действующие записи операции по её метке — их и откатывает `last`, и `op:<метка>`."""
    return con.execute("select * from corrections where op = ? and reverted_at is null"
                       " order by id desc", (op,)).fetchall()


def undo(con, what):
    """Проверка конфликтов и откат выполняются в одной транзакции."""
    try:
        if hasattr(con, '_raw'):
            con.execute('LOCK TABLE corrections IN SHARE ROW EXCLUSIVE MODE')
        elif not con.in_transaction:
            con.execute('BEGIN IMMEDIATE')
        result = _undo(con, what)
        con.commit()
        return result
    except Exception:
        con.rollback()
        raise


def _undo(con, what):
    """Откатить операцию: `last` — все поля последней, `op:<метка>` — все поля операции по её
    метке, `<id>` — одну запись журнала.

    Метка нужна затем: пока человек разбирался с одной правкой, база могла принять другую, и
    откатывать надо ту, которую он назвал, а не ту, что легла последней. Откат по id возвращает
    одно поле и оставляет операцию наполовину применённой — ник вернётся, а его `slug` нет.
    Порядок отката по метке и по `last` один и тот же.
    """
    text = str(what)
    if text == "last":
        newest = con.execute("select op from corrections where reverted_at is null"
                             " order by id desc limit 1").fetchone()
        entries = _live_entries(con, newest[0]) if newest else []
    elif text.startswith(OP_PREFIX):
        label = text[len(OP_PREFIX):].strip()
        if not con.execute("select 1 from corrections where op = ? limit 1", (label,)).fetchone():
            raise EditError(f"Операции с меткой «{label}» в журнале нет — метку печатает `log`")
        entries = _live_entries(con, label)
        if not entries:
            raise EditError(f"Операция с меткой «{label}» уже отменена — действующих записей нет")
    else:
        entry = con.execute("select * from corrections where id = ?", (int(text),)).fetchone()
        if entry is None:
            raise EditError(f"Записи {what} в журнале нет")
        if entry["reverted_at"]:
            raise EditError(f"Запись {what} уже отменена")
        entries = [entry]
    if not entries:
        return {"operation": "undo", "entries": [], "released": 0}

    # Откат старого решения не должен затирать более позднюю работу другого редактора.
    if text.startswith(OP_PREFIX):
        keys = {(e['table_name'], e['row_id']) for e in entries}
        matches = {_entry_match_id(con, e) for e in entries} - {None}
        later = con.execute('select * from corrections where reverted_at is null and id > ? '
                            'and op != ?', (min(e['id'] for e in entries), label)).fetchall()
        for entry in later:
            if (entry['table_name'], entry['row_id']) in keys or _entry_match_id(con, entry) in matches:
                raise EditError('После этого решения те же данные уже изменены. '
                                'Сначала отмените более позднее решение или внесите новую правку.')

    affected = []
    restores, updates = [], []
    for entry in entries:
        if entry["field"] == EXISTS and entry["new_value"] is None:
            restores.append(entry)   # строку удаляла правка: откат возвращает её по снимку
        else:
            updates.append(entry)
    # Сначала возвращаем удалённые строки — и в порядке зависимости, а не журнала: `side_players`
    # нельзя переставить на игрока, которого ещё нет в базе (FOREIGN KEY).
    for entry in sorted(restores, key=lambda item: (RESTORE_ORDER.get(item["table_name"], 9),
                                                    item["id"])):
        restore_row(con, entry)
    for entry in updates:
        if entry["field"] == EXISTS:
            restore_row(con, entry)  # созданную правкой строку откат удаляет
        else:
            con.execute(f"update {entry['table_name']} set {entry['field']} = ? where id = ?",
                        (_restore(entry["old_value"]), entry["row_id"]))
    for entry in entries:
        con.execute("update corrections set reverted_at = ? where id = ?", (_now(), entry["id"]))
        affected.append(_entry_match_id(con, entry))
    touched = {match for match in affected if match}
    # Связку учитывает `release_unedited`: флаг ставится всем строкам игры, а запись журнала может
    # касаться одной. Здесь достаточно матчей, названных в журнале.
    resync_rosters(con, touched)
    released = release_unedited(con, touched)
    con.commit()
    return {
        "operation": "undo",
        "entries": [{"id": e["id"], "table": e["table_name"], "row_id": e["row_id"],
                     "field": e["field"], "old_value": e["old_value"]} for e in entries],
        "released": released,
    }


def _entry_match_id(con, entry):
    """Матч записи журнала; None — если строка уже пересобрана и её id в базе другой."""
    table = entry["table_name"]
    if table == "matches":
        return entry["row_id"]
    if table == "match_links":
        link = con.execute("select match_id from match_links where id = ?", (entry["row_id"],)).fetchone()
        if link:
            return link[0]
        # Ссылку только что удалил откат её создания — матч берём из снимка строки.
        return json.loads(entry["new_value"])["match_id"] if entry["new_value"] else None
    if table == "side_players":
        row = con.execute(
            """select s.match_id from side_players sp join match_sides s on s.id = sp.side_id
                where sp.id = ?""", (entry["row_id"],)).fetchone()
        if row:
            return row[0]
        snapshot = json.loads(entry["new_value"] or entry["old_value"] or "{}")
        side = con.execute("select match_id from match_sides where id = ?",
                           (snapshot.get("side_id"),)).fetchone()
        return side[0] if side else None
    if table == "match_sides":
        side = con.execute("select match_id from match_sides where id = ?", (entry["row_id"],)).fetchone()
        return side[0] if side else None
    return None


def cmd_undo(con, args):
    result = undo(con, args.what)
    if not result["entries"]:
        print("отменять нечего")
        return 0
    for entry in result["entries"]:
        print(f"  откат #{entry['id']}: {entry['table']}.{entry['row_id']} {entry['field']} "
              f"-> {entry['old_value']!r}")
    print(f"отменено записей: {len(result['entries'])}; строок возвращено импортёру: "
          f"{result['released']}; пересоберите: python build_all.py")
    return 0


def _restore(value):
    if value is None or value == "None":
        return None
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--editor", default="owner", help="кто правит (попадает в журнал)")
    commands = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (("show", "показать матч"), ("void", "снять матч с зачёта"),
                            ("unvoid", "вернуть матч на зачёт"), ("unhide", "вернуть строку на витрину")):
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

    sub = commands.add_parser("set-source", help="править подпись игры и её ссылки", parents=[common])
    sub.add_argument("match_id", type=int)
    sub.add_argument("--note", default=None, help="что таблица турнира показывает в колонке счёта")
    sub.add_argument("--link", action="append", default=None, metavar="ВИД=АДРЕС",
                     help="повторяемо; список заменяет ссылки строки целиком")

    sub = commands.add_parser("add-match", help="внести новую игру в турнир или сезон",
                              parents=[common])
    sub.add_argument("a", help="первая сторона (пара 2×2 — через « & »)")
    sub.add_argument("b", help="вторая сторона")
    sub.add_argument("--doc", dest="doc_key", default=None, help="ключ турнира-документа")
    sub.add_argument("--season", default=None, help="сезонный бакет, если игра не из турнира")
    sub.add_argument("--league", default=None)
    sub.add_argument("--stage", default=None, help="этап, как его зовёт база (для турнира — его строка)")
    sub.add_argument("--tour", default=None, help="тур, как его показывает страница")
    sub.add_argument("--score", default=None, metavar="М:Н", help="без него игра заведётся без счёта")
    sub.add_argument("--note", default=None)

    sub = commands.add_parser("add-tournament", help="завести новый турнир", parents=[common])
    sub.add_argument("doc_key")
    sub.add_argument("title")
    sub.add_argument("--kind", default="special", choices=("special", "team"))
    sub.add_argument("--category", default="Спецтурниры", help="раздел, в котором турнир покажется")

    sub = commands.add_parser("set-doc", help="править рамку турнира", parents=[common])
    sub.add_argument("doc_key")
    sub.add_argument("--title", default=None)
    sub.add_argument("--frame", default=None, help="JSON рамки целиком")

    sub = commands.add_parser("set-place", help="перенести игру в другой тур, дивизион или этап",
                              parents=[common])
    sub.add_argument("match_id", type=int)
    sub.add_argument("--tour", default=None, help="как тур подписан на странице: «5 Тур», «Группа F»")
    sub.add_argument("--league", default=None, help="дивизион: «Высшая лига»")
    sub.add_argument("--stage", default=None, help="этап (стадия) матча: «1/4 финала»")

    sub = commands.add_parser("set-rating", help="взять игру в расчёт Elo или снять её",
                              parents=[common])
    sub.add_argument("match_id", type=int)
    sub.add_argument("--off", action="store_true", help="снять с рейтинга (по умолчанию — взять)")

    sub = commands.add_parser("rate-scope",
                              help="отметить рейтинговыми все игры сезона или всего турнира",
                              parents=[common])
    scope = sub.add_mutually_exclusive_group(required=True)
    scope.add_argument("--season", default=None, help="сезон, например «Season 6»")
    scope.add_argument("--doc", dest="doc_key", default=None, help="ключ турнира-документа")
    sub.add_argument("--off", action="store_true", help="снять флаг, а не поставить")

    sub = commands.add_parser("set-date", help="поставить игре дату", parents=[common])
    sub.add_argument("match_id", type=int)
    sub.add_argument("--played-on", dest="played_on", default=None,
                     metavar="ГГГГ[-ММ[-ДД]]", help="дата, которую увидел человек")
    sub.add_argument("--source-date", dest="source_date_raw", default=None,
                     help="дата дословно у источника (unix-секунды ВК, год справочника)")

    sub = commands.add_parser("set-phase", help="отметить овертайм, буллиты или плей-офф",
                              parents=[common])
    sub.add_argument("match_id", type=int)
    sub.add_argument("--phase", default=None, choices=PHASES)
    sub.add_argument("--playoff", default=None, choices=("yes", "no"),
                     help="да — это плей-офф (K=32), нет — регулярка")

    sub = commands.add_parser("set-provenance",
                              help="править, откуда взялась строка (осторожно: это ключ импорта)",
                              parents=[common])
    sub.add_argument("match_id", type=int)
    sub.add_argument("--source", default=None)
    sub.add_argument("--source-ref", dest="source_ref", default=None)
    sub.add_argument("--source-locator", dest="source_locator", default=None)
    sub.add_argument("--source-page", dest="source_page", default=None)
    sub.add_argument("--source-text", dest="source_text", default=None)

    sub = commands.add_parser("drop-match", help="удалить игру вместе со сторонами и ссылками",
                              parents=[common])
    sub.add_argument("match_id", type=int)

    sub = commands.add_parser("drop-tournament", help="удалить турнир, в котором не осталось игр",
                              parents=[common])
    sub.add_argument("doc_key")

    sub = commands.add_parser("rename-player", help="переименовать карточку игрока", parents=[common])
    sub.add_argument("player_id", type=int)
    sub.add_argument("nick")

    sub = commands.add_parser("merge-player", help="слить две карточки в одну", parents=[common])
    sub.add_argument("keep_id", type=int, help="эта остаётся")
    sub.add_argument("drop_id", type=int, help="эта переезжает в первую и становится алиасом")

    sub = commands.add_parser("log", help="последние записи журнала", parents=[common])
    sub.add_argument("--limit", type=int, default=20)

    sub = commands.add_parser("undo",
                              help="откатить операцию: 'last', op:<метка> операции или id записи",
                              parents=[common])
    sub.add_argument("what", metavar="'last'|op:<метка>|<id>",
                     help="`last` — последняя операция целиком; `op:<метка>` — операцию по метке "
                          "из колонки `op` (её печатает каждая правка и `log`); число — одну запись")

    args = parser.parse_args(argv)
    try:
        con = connect()
    except EditError as error:
        sys.exit(str(error))
    handlers = {
        "show": cmd_show, "set-score": cmd_set_score, "set-players": cmd_set_players,
        "set-place": cmd_set_place, "set-date": cmd_set_date, "set-phase": cmd_set_phase,
        "set-provenance": cmd_set_provenance, "drop-match": cmd_drop_match,
        "drop-tournament": cmd_drop_tournament, "rename-player": cmd_rename_player,
        "merge-player": cmd_merge_player,
        "set-source": cmd_set_source, "add-match": cmd_add_match,
        "add-tournament": cmd_add_tournament, "set-doc": cmd_set_doc,
        "set-rating": cmd_set_rating, "rate-scope": cmd_rate_scope,
        "void": lambda c, a: cmd_status(c, a, "void"),
        "unvoid": lambda c, a: cmd_status(c, a, "played"), "unhide": cmd_unhide,
        "log": cmd_log, "undo": cmd_undo,
    }
    try:
        return handlers[args.command](con, args)
    except EditError as error:
        con.rollback()
        sys.exit(str(error))


if __name__ == "__main__":
    sys.exit(main())
