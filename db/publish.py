"""Очередь публикаций: правки накоплены и видны, выкат по-прежнему делает сборка.

Смысл ровно один — дать лороведу без терминала увидеть, что его правки ждут выката. Публикация
остаётся `python build_all.py`: перерисовывать прод-сайт по клику нельзя, владелец этого сознательно
не просил. Поэтому запрос здесь — запись в очередь, а не действие: он помнит отпечаток базы
(тот же, что отдаёт `db/api.py:revision`) и число действующих правок на момент постановки.

`corrections` модуль не трогает: запрос публикации — не редактура архива, он не пишется в журнал
правок и не откатывается `undo`. Таблица `publish_requests` меняется только операциями ниже —
`request`, `claim`, `fail`, `close_queued`.

    python db/publish.py request --note "сезон 9 разобран до последней строки"
    python db/publish.py list
    python db/publish.py apply            # взять самый старый запрос и запустить сборку
    python db/publish.py close            # закрыть очередь после ручного python build_all.py
"""

import argparse
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import api, edit, store  # noqa: E402

DB_PATH = store.DB_PATH
QUEUED, APPLIED, FAILED = "queued", "applied", "failed"
# Причина провала держится текстом, а не отдельным запросом к сборке: человеку нужны последние
# строки её вывода, а не весь лог.
TAIL_LINES = 25
# Таблица очереди строит шаг схемы (`db/schema.sql`, секция steps), а его применяет сборка. Пока
# человек не пересобрал базу, чтение отдаёт пустую очередь, а запись отказывает — молчать панель
# не имеет права.
MISSING_TABLE = ("таблицы очереди публикаций в базе нет: шаг схемы ещё не применён — "
                 "сначала python db/build_db.py (или python build_all.py)")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _has_table(con):
    return bool(con.execute("select 1 from sqlite_master where type = 'table'"
                            " and name = 'publish_requests'").fetchone())


def _db_path(con):
    """Файл базы, к которому открыто соединение: отпечаток считается по пути, а не по своему SQL.

    `db/api.py` уже умеет считать ревизию, и панель показывает именно её. Своя копия вычисления
    разъехалась бы с панелью на первом же изменении схемы — очередь обязана называть те же числа,
    что видит редактор.
    """
    found = con.execute("pragma database_list").fetchone()
    path = found[2] if found else ""
    if not path:
        raise edit.EditError("очередь публикаций работает с файлом базы: у соединения в памяти "
                             "отпечатка нет")
    return Path(path)


def live_corrections(con):
    """Сколько правок действует сейчас — ровно то, что показывает `python db/api.py` в состоянии."""
    return api.state(_db_path(con))["corrections_live"]


def request(con, editor, note=""):
    """Поставить запрос в очередь: отпечаток и число живых правок берутся у `db/api.py`.

    Два отказа, а не пустая строка в очереди:
      * живых правок нет — публиковать нечего, запрос только замусорил бы очередь;
      * на этот же отпечаток уже стоит незакрытый запрос — вторая такая же запись ничего не
        изменит, сборка закроет первую.
    """
    if not editor:
        raise edit.EditError("запрос публикации без подписи редактора не ставится")
    if not _has_table(con):
        raise edit.EditError(MISSING_TABLE)
    facts = api.state(_db_path(con))
    revision, live = facts["revision"], facts["corrections_live"]
    if not live:
        raise edit.EditError("публиковать нечего: в базе нет ни одной действующей правки")
    clash = con.execute(
        "select id from publish_requests where revision = ? and status = ? order by id limit 1",
        (revision, QUEUED)).fetchone()
    if clash:
        raise edit.EditError(f"запрос #{clash[0]} на ревизию {revision} ещё не закрыт — "
                             f"второй на тот же срез базы ставить смысла нет")
    con.execute(
        "insert into publish_requests(revision, corrections_live, editor, note) values (?, ?, ?, ?)",
        (revision, live, str(editor), str(note or "").strip()))
    con.commit()
    row = con.execute("select * from publish_requests where id = last_insert_rowid()").fetchone()
    return dict(row)


PENDING_SQL = """
select id, revision, corrections_live, editor, note, created_at, status, applied_at, detail
from publish_requests order by id
"""


def pending(db_path=DB_PATH):
    """Очередь для панели: запросы в порядке появления, с временем, автором, статусом.

    Закрытые запросы остаются в списке: лороведу надо видеть не только что ждёт, но и что уже
    ушло в выкат и почему провалилось, иначе очередь выглядит пустой без объяснений.
    """
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        if not _has_table(con):
            return []  # очереди ещё нет: панель получает пустой список, а отказ даст сама запись
        return [dict(row) for row in con.execute(PENDING_SQL)]
    finally:
        con.close()


def claim(con, editor):
    """Взять самый старый незакрытый запрос и пометить его `applied`: сборка по нему пошла.

    Порядок — по id, а не по времени: две постановки в одну секунду отсортировались бы как попало,
    а очередь обязана обслуживаться по старшинству.
    """
    if not editor:
        raise edit.EditError("взять запрос без подписи редактора нельзя: очередь видит, кто его собрал")
    if not _has_table(con):
        raise edit.EditError(MISSING_TABLE)
    row = con.execute("select * from publish_requests where status = ? order by id limit 1",
                      (QUEUED,)).fetchone()
    if row is None:
        raise edit.EditError("в очереди нет незакрытых запросов: сначала "
                             "python db/publish.py request --note \"…\"")
    now = _now()
    con.execute("update publish_requests set status = ?, applied_at = ? where id = ?",
                (APPLIED, now, row["id"]))
    con.commit()
    taken = dict(row)
    taken.update(status=APPLIED, applied_at=now)
    return taken


def fail(con, reason, request_id=None):
    """Пометить запрос `failed` с причиной: хвост вывода сборки, а не «что-то упало».

    Берётся последний взятый (`applied`) запрос, если id не назван: провал относится к той сборке,
    которая его только что брала, а не к запросу из прошлого.
    """
    if not _has_table(con):
        raise edit.EditError(MISSING_TABLE)
    where, params = "status = ?", [APPLIED]
    if request_id is not None:
        where, params = "id = ?", [int(request_id)]
    row = con.execute(f"select * from publish_requests where {where} order by id desc limit 1",
                      params).fetchone()
    if row is None:
        raise edit.EditError("помечать провал нечем: взятых сборок, которые ещё не закрыты, в очереди нет")
    con.execute("update publish_requests set status = ?, detail = ? where id = ?",
                (FAILED, str(reason or "").strip()[:4000], row["id"]))
    con.commit()
    failed = dict(row)
    failed.update(status=FAILED, detail=str(reason or "").strip()[:4000])
    return failed


def close_queued(con):
    """Закрыть все незакрытые запросы: этот выкат забрал базу целиком.

    Сборка не выбирает, что публиковать, — она пересчитывает сайт по текущей базе, поэтому вместе
    со взятым запросом закрываются и все, что стояли в очереди (в том числе поставленные, пока
    сборка шла). Взятого здесь уже нет: `claim` помечает его `applied` до запуска.

    По совпадению отпечатка закрывать нельзя, и вот почему: живые правки после выката остаются
    (иначе импортёр пересоздаст строку), а `revision` считается по id строк, которые пересборка
    меняет, — запрос, который выкат действительно удовлетворил, своему отпечатку уже не равен.
    """
    if not _has_table(con):
        raise edit.EditError(MISSING_TABLE)
    ids = [row[0] for row in con.execute(
        "select id from publish_requests where status = ? order by id", (QUEUED,)).fetchall()]
    if not ids:
        return []
    now = _now()
    con.executemany("update publish_requests set status = ?, applied_at = ? where id = ?",
                    [(APPLIED, now, request_id) for request_id in ids])
    con.commit()
    return ids


def _tail(text):
    """Последние строки вывода сборки — ровно столько, чтобы понять причину без чтения лога."""
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return "\n".join(lines[-TAIL_LINES:])


def build_site():
    """Сборка этим же python-процессом: `sys.executable`, рабочий каталог — корень репозитория.

    Возвращает (код возврата, хвост вывода). Из этого модуля сборка сама не стартует: её зовёт
    подкоманда `apply`, и только когда человек явно попросил выкат.
    """
    process = subprocess.run([sys.executable, str(ROOT / "build_all.py")], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = "\n".join(filter(None, [process.stdout or "", process.stderr or ""]))
    return process.returncode, _tail(output)


def cmd_request(con, args):
    made = request(con, args.editor, args.note)
    print(f"запрос #{made['id']}: ревизия {made['revision']}, в выкат уходит {made['corrections_live']} "
          f"живых правок\n{made['note'] or '(без описания)'}")
    print("цифры на сайте обновит сборка: python db/publish.py apply (или python build_all.py)")
    return 0


def cmd_list(con, args):
    rows = pending(_db_path(con))
    if not rows:
        print("очередь публикаций пуста — правки никто не просил выкатывать")
        return 0
    for row in rows:
        stamp = f" · взято {row['applied_at']}" if row["applied_at"] else ""
        print(f"#{row['id']} · {row['created_at']} · {row['status']}{stamp} · {row['editor']} · "
              f"ревизия {row['revision']} · правок {row['corrections_live']} · {row['note'] or '—'}")
        if row["detail"]:
            print(f"    причина провала: {row['detail'].splitlines()[0]}")
    print(f"незакрытых: {len([row for row in rows if row['status'] == QUEUED])}")
    return 0


def cmd_apply(con, args):
    taken = claim(con, args.editor)
    print(f"запрос #{taken['id']} (ревизия {taken['revision']}, правок {taken['corrections_live']}) "
          f"взят сборкой, запускается python build_all.py")
    code, tail = build_site()
    if code == 0:
        closed = close_queued(con)
        if closed:
            print(f"сборка прошла; вместе с #{taken['id']} этот выкат забрал ещё "
                  f"{len(closed)} запросов (#{', #'.join(str(item) for item in closed)})")
        else:
            print("сборка прошла; других незакрытых запросов в очереди не было")
        return 0
    failed = fail(con, tail or f"сборка вернула код {code}", request_id=taken["id"])
    print(f"сборка провалилась (код {code}), запрос #{failed['id']} помечен failed")
    print(tail or "сборка не напечатала ничего")
    return 1


def cmd_close(con, args):
    closed = close_queued(con)
    if not closed:
        print(f"не закрыто ничего: незакрытых запросов в очереди нет "
              f"(живых правок сейчас {live_corrections(con)})")
        return 0
    print(f"закрыто запросов: {len(closed)} (#{', #'.join(str(item) for item in closed)}) — "
          "сборка публикует базу целиком, значит выкат их забрал")
    return 0


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--editor", default="owner", help="кто ставит или берёт запрос (пишется в очередь)")
    commands = parser.add_subparsers(dest="command", required=True)

    sub = commands.add_parser("request", help="поставить запрос на выкат", parents=[common])
    sub.add_argument("--note", default="", help="что публикуем — одной строкой, по-человечески")
    commands.add_parser("list", help="что стоит в очереди и что уже закрыто", parents=[common])
    commands.add_parser("apply", help="взять самый старый запрос и запустить python build_all.py",
                        parents=[common])
    commands.add_parser("close", help="закрыть запросы, чей выкат уже случился", parents=[common])

    handlers = {"request": cmd_request, "list": cmd_list, "apply": cmd_apply, "close": cmd_close}
    args = parser.parse_args(argv)
    try:
        con = edit.connect()
    except edit.EditError as error:
        sys.exit(str(error))
    try:
        return handlers[args.command](con, args)
    except edit.EditError as error:
        con.rollback()
        sys.exit(str(error))
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
