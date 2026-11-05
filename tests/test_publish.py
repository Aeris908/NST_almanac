"""Очередь публикаций: запрос живёт рядом с журналом правок, но не в нём.

Здесь проверяются три вещи:
  * запрос несёт тот же отпечаток базы и то же число живых правок, что показывает панель
    (`db/api.py`), — иначе лоровед сверял бы две разные цифры;
  * отказы формулируются по-русски и по делу: нечего публиковать, второй запрос на тот же срез;
  * таблица строится шагом схемы (`db/schema.sql`, секция steps) и переживает повторную сборку.

Живой `data/nst.db` тесты не трогают: все операции идут на копию из фикстуры `db_path`, а сборка
базы вызывается тем же кодом, что и `python db/build_db.py`, только на этой копии. Строки берутся
свойством (`support.SCOREFUL`), фиксированных id в тесте нет.
"""

import importlib
import io
import json
import sys
import types
from email.message import Message

import pytest
from db import api, edit, publish, serve
from support import SCOREFUL

TOKEN = "test-token-0123456789"
EDITOR = "лоровед"
BUILDER = "сборщик"


@pytest.fixture
def build_db(monkeypatch):
    """`db/build_db.py` без настоящего поставщика строк.

    `build_final_analytics` при импорте проверяет соединение с ВК и читает снапшот Sportcup
    относительно рабочего каталога, а тесту нужен ровно один кусок сборки — применение схемы к
    копии базы. Поэтому в `sys.modules` на время теста встаёт заглушка с пустым пулом: `main()`
    от этого ничего не теряет, путь базы подменяется отдельно.
    """
    stub = types.ModuleType("build_final_analytics")
    stub.all_matches = []
    stub.CUP_TOURNAMENT = "Кубок лиг"
    stub.REGULAR_STAGE = "Регулярный сезон"
    monkeypatch.setitem(sys.modules, "build_final_analytics", stub)
    sys.modules.pop("db.build_db", None)
    module = importlib.import_module("db.build_db")
    yield module
    # Заглушка не должна пережить тест: следующий импорт обязан получить настоящую сборку.
    sys.modules.pop("db.build_db", None)


@pytest.fixture
def applied(con, build_db):
    """Копия базы с применённым шагом схемы: таблица очереди появляется так же, как в сборке."""
    build_db.apply_schema(con)
    con.commit()
    return con


@pytest.fixture
def cli(applied, db_path, monkeypatch):
    """CLI этой же проверки смотрит на копию базы теста: соединение открывается на каждый вызов.

    `main()` закрывает соединение сам, поэтому подменяется именно `edit.connect`, а не путь: иначе
    вторая подкоманда того же теста работала бы с уже закрытой базой.
    """
    real = edit.connect
    monkeypatch.setattr(publish.edit, "connect", lambda *args, **kwargs: real(db_path))
    return applied


def _edited(con, find, delta=4):
    """Живая правка счёта: отпечаток базы сдвигается, правка попадает в журнал.

    Значение берётся от текущего счёта строки, а не выдумывается: тест не должен зависеть от того,
    что принесла сборка.
    """
    match_id = find(SCOREFUL, what="матч с числами")
    current = con.execute("select score from match_sides where match_id = ? and side_index = 0",
                          (match_id,)).fetchone()[0]
    edit.set_score(con, match_id, current + delta, 0, EDITOR)
    return match_id


def _find(con):
    """Та же «нашла или skip» семантика, что у фикстуры, но на отдельном соединении."""
    def finder(sql, params=(), what="нужная строка"):
        row = con.execute(sql, params).fetchone()
        if row is None:
            pytest.skip(f"в копии базы нет: {what}")
        return row[0] if len(row) == 1 else tuple(row)
    return finder


class _Buffer:
    """Куда обработчик пишет ответ: вместо сокета — байты в памяти, порт никто не занимает."""

    def __init__(self):
        self.data = bytearray()

    def write(self, payload):
        self.data += payload
        return len(payload)


def _bound(db_path):
    """Как Vercel-функция: все вызовы `db/api.py` идут с явным путём базы теста."""

    class _Bound:
        def __init__(self, path):
            self.path = path

        def __getattr__(self, name):
            call = getattr(api, name)

            def bound(*args, **kwargs):
                kwargs.setdefault("db_path", self.path)
                return call(*args, **kwargs)

            return bound

    return _Bound(db_path)


def served_get(path, *, token=TOKEN):
    """Один GET сквозь сам `db/serve.py`: ровно так локальный сервер отвечает панели."""
    request = object.__new__(serve.Handler)
    headers = Message()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request.command = "GET"
    request.path = path
    request.requestline = f"GET {path} HTTP/1.1"
    request.request_version = "HTTP/1.1"
    request.close_connection = True
    request.headers = headers
    request.rfile = io.BytesIO()
    request.wfile = _Buffer()
    request.do_GET()
    head, _, rest = bytes(request.wfile.data).partition(b"\r\n\r\n")
    status = int(head.decode("latin-1").split(" ", 2)[1])
    return status, json.loads(rest.decode("utf-8")) if rest else None


def test_request_carries_the_revision_the_panel_shows(applied, find, db_path):
    """Отпечаток и число живых правок берутся у `db/api.py`: своя копия вычисления разъехалась бы."""
    _edited(applied, find)
    made = publish.request(applied, EDITOR, "сезон 9 разобран до последней строки")
    facts = api.state(db_path)
    assert made["revision"] == facts["revision"]
    assert made["corrections_live"] == facts["corrections_live"] > 0
    assert made["status"] == "queued"
    assert made["editor"] == EDITOR and made["note"] == "сезон 9 разобран до последней строки"
    assert made["applied_at"] is None and made["detail"] == ""


def test_request_without_live_corrections_is_refused(applied, db_path):
    """Публиковать нечего — в очереди не появляется пустая запись."""
    with pytest.raises(edit.EditError, match="публиковать нечего"):
        publish.request(applied, EDITOR, "нечего публиковать")
    assert publish.pending(db_path) == []


def test_request_without_signature_is_refused(applied, find, db_path):
    """Подпись обязательна: без неё непонятно, кто просил выкат."""
    _edited(applied, find)
    with pytest.raises(edit.EditError, match="без подписи"):
        publish.request(applied, "", "анонимный выкат")
    assert publish.pending(db_path) == []


def test_second_open_request_on_the_same_revision_is_refused(applied, find, db_path):
    """Дубликат по тому же отпечатку не нужен: сборка закроет первый, второй только мешает."""
    _edited(applied, find)
    made = publish.request(applied, EDITOR, "первый запрос")
    with pytest.raises(edit.EditError, match=f"запрос #{made['id']} "):
        publish.request(applied, EDITOR, "тот же срез базы")
    assert [row["id"] for row in publish.pending(db_path)] == [made["id"]]


def test_closed_request_frees_the_way_for_a_new_one(applied, find, db_path):
    """Отказ от дубликата держится только пока запрос незакрыт: взятый сборкой не мешает новому."""
    _edited(applied, find)
    made = publish.request(applied, EDITOR, "ждёт сборки")
    publish.claim(applied, BUILDER)
    again = publish.request(applied, EDITOR, "снова те же правки")
    assert again["revision"] == made["revision"]
    assert {row["id"]: row["status"] for row in publish.pending(db_path)} == {
        made["id"]: "applied", again["id"]: "queued"}


def test_pending_lists_requests_in_order_of_creation(applied, find, db_path):
    """Очередь для панели: по порядку появления, со временем, автором, числом правок и статусом."""
    _edited(applied, find, delta=4)
    first = publish.request(applied, EDITOR, "первая партия правок")
    _edited(applied, find, delta=5)
    second = publish.request(applied, EDITOR, "вторая партия правок")
    rows = publish.pending(db_path)
    assert [row["id"] for row in rows] == sorted(row["id"] for row in rows) == [first["id"], second["id"]]
    assert [row["note"] for row in rows] == ["первая партия правок", "вторая партия правок"]
    assert all(row["created_at"] and row["editor"] == EDITOR for row in rows)
    assert all(row["status"] == "queued" for row in rows)
    assert rows[1]["corrections_live"] >= rows[0]["corrections_live"]


def test_claim_takes_the_oldest_queued_and_marks_it_applied(applied, find, db_path):
    """Самый старый запрос идёт в сборку первым; взятый помечен `applied` со временем."""
    _edited(applied, find, delta=4)
    older = publish.request(applied, EDITOR, "старый")
    _edited(applied, find, delta=5)
    newer = publish.request(applied, EDITOR, "новый")
    taken = publish.claim(applied, BUILDER)
    assert taken["id"] == older["id"] and taken["status"] == "applied" and taken["applied_at"]
    rows = {row["id"]: row for row in publish.pending(db_path)}
    assert rows[older["id"]]["status"] == "applied"
    assert rows[newer["id"]]["status"] == "queued"


def test_claim_without_queued_requests_refuses_in_russian(applied):
    """Взять нечего — и это сказано текстом, а не молчанием: `apply` на пустой очереди отказывает."""
    with pytest.raises(edit.EditError, match="нет незакрытых запросов"):
        publish.claim(applied, BUILDER)


def test_fail_leaves_the_reason_in_the_queue(applied, find, db_path):
    """Провал сборки — статус `failed` и причина: человек видит, почему очередь не двинулась."""
    _edited(applied, find)
    made = publish.request(applied, EDITOR, "сборка не прошла")
    publish.claim(applied, BUILDER)
    failed = publish.fail(applied, "сборка упала на валидации: инварианты не сошлись")
    assert failed["id"] == made["id"] and failed["status"] == "failed"
    row = publish.pending(db_path)[0]
    assert row["status"] == "failed" and "валидации" in row["detail"]


def test_fail_without_a_taken_request_refuses(applied):
    """Провал бывает у взятого сборок запроса: помечать нечего — отказ, а не тихая запись."""
    with pytest.raises(edit.EditError, match="помечать провал нечем"):
        publish.fail(applied, "сборки не было")


def test_close_queued_finishes_requests_made_while_the_build_ran(applied, find, db_path):
    """Сборка публикует базу целиком: запрос, поставленный пока она шла, закрывает этот же выкат."""
    _edited(applied, find, delta=1)
    first = publish.request(applied, EDITOR, "первый ждёт")
    taken = publish.claim(applied, EDITOR)
    assert taken["id"] == first["id"], "очередь обслуживается не по старшинству"
    _edited(applied, find, delta=2)
    second = publish.request(applied, EDITOR, "поставлен, пока сборка шла")
    assert publish.close_queued(applied) == [second["id"]]
    states = {row["id"]: row["status"] for row in publish.pending(db_path)}
    assert states == {first["id"]: "applied", second["id"]: "applied"}


def test_close_queued_closes_a_request_while_its_edits_stay_live(applied, find, db_path):
    """Правки после выката остаются живыми — они защищают строку от импортёра.

    Поэтому закрытие по признаку «ноль действующих правок» не сработало бы никогда: очередь
    закрывается по факту сборки, а не по опустевшему журналу.
    """
    _edited(applied, find)
    made = publish.request(applied, EDITOR, "выкат с живой правкой")
    assert api.state(db_path)["corrections_live"] > 0
    assert publish.close_queued(applied) == [made["id"]]
    assert api.state(db_path)["corrections_live"] > 0, "закрытие запроса тронуло журнал правок"
    assert publish.pending(db_path)[0]["status"] == "applied"


def test_close_queued_after_a_manual_build_closes_everything(applied, find, db_path):
    """Ручной `python build_all.py` без кнопки: оператор сказал, что выкат был, — закрыто всё."""
    _edited(applied, find, delta=1)
    first = publish.request(applied, EDITOR, "первый")
    _edited(applied, find, delta=2)
    second = publish.request(applied, EDITOR, "второй")
    assert publish.close_queued(applied) == [first["id"], second["id"]]
    assert {row["status"] for row in publish.pending(db_path)} == {"applied"}


def test_close_queued_on_an_empty_queue_returns_nothing(applied):
    assert publish.close_queued(applied) == []


def test_api_operation_puts_the_request_into_the_queue(applied, find, db_path):
    """Операция `publish-request` идёт через тот же слой, что и остальные правки панели."""
    _edited(applied, find)
    made = api._apply(applied, "publish-request", EDITOR, {"note": "через api"})
    assert made["status"] == "queued" and made["note"] == "через api"
    assert [row["id"] for row in publish.pending(db_path)] == [made["id"]]


def test_publish_handle_answers_exactly_the_queue(applied, find, db_path, monkeypatch):
    """GET `/api/publish` отдаёт `pending()` и число живых правок — то же, что видит панель."""
    _edited(applied, find)
    made = publish.request(applied, EDITOR, "ручка очереди")
    monkeypatch.setenv("NST_EDITOR_TOKEN", TOKEN)
    monkeypatch.setattr(serve, "api", _bound(db_path))
    status, body = served_get("/api/publish")
    assert status == 200 and body["ok"] is True
    assert body["requests"] == publish.pending(db_path) == [dict(made)]
    assert body["corrections_live"] == api.state(db_path)["corrections_live"]


def test_publish_handle_refuses_without_a_token(applied, db_path, monkeypatch):
    """Страница публичная: ручка очереди работает только с токеном, как и остальное."""
    monkeypatch.setenv("NST_EDITOR_TOKEN", TOKEN)
    monkeypatch.setattr(serve, "api", _bound(db_path))
    status, body = served_get("/api/publish", token=None)
    assert status == 401 and "токен" in body["error"]


def test_publish_operation_is_listed_for_the_editor():
    """Список операций и обязательных полей один на сервер и функцию: панель берёт его отсюда."""
    assert "publish-request" in serve.OPERATIONS
    assert serve.REQUIRED_ARGS["publish-request"] == ()


def test_cli_lists_its_commands_and_reports_the_queue(cli, find, capfd):
    """CLI знает `request`/`list`/`apply`/`close` и печатает очередь копией базы тестов."""
    with pytest.raises(SystemExit) as help_exit:
        publish.main(["--help"])
    assert help_exit.value.code == 0
    help_text = capfd.readouterr().out  # один readouterr забирает весь буфер: повторный уже пустой
    assert all(name in help_text for name in ("request", "list", "apply", "close"))
    _edited(cli, find)
    assert publish.main(["request", "--note", "через cli", "--editor", EDITOR]) == 0
    assert "через cli" in capfd.readouterr().out
    assert publish.main(["list"]) == 0
    printed = capfd.readouterr().out
    assert "ревизия" in printed and "незакрытых: 1" in printed


def test_cli_apply_refuses_without_a_request_and_never_builds(cli, monkeypatch):
    """Подкоманда `apply` существует и отказывается без запроса; сборку в проверке не запускаем."""
    def _forbidden():
        raise AssertionError("apply не должен запускать сборку в тестах")

    monkeypatch.setattr(publish, "build_site", _forbidden)
    with pytest.raises(SystemExit) as refused:
        publish.main(["apply"])
    assert "нет незакрытых запросов" in str(refused.value)


def test_cli_close_finishes_the_queue_after_a_manual_build(cli, find, capfd):
    """`close` закрывает очередь после ручного `build_all.py` и говорит, сколько закрыл."""
    _edited(cli, find)
    made = publish.request(cli, EDITOR, "правки ушли в ручной выкат")
    assert publish.main(["close"]) == 0
    printed = capfd.readouterr().out
    assert f"закрыто запросов: 1 (#{made['id']})" in printed
    assert publish.main(["close"]) == 0
    assert "не закрыто ничего" in capfd.readouterr().out


def test_build_db_step_survives_a_second_run(build_db, db_path, monkeypatch):
    """Шаг идемпотентен: второй прогон `python db/build_db.py` на копии не роняет сборку."""
    monkeypatch.setattr(build_db, "DB_PATH", db_path)
    monkeypatch.setattr(sys, "argv", ["build_db.py"])
    printed = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", printed)

    build_db.main()
    con = edit.connect(db_path)
    try:
        _edited(con, _find(con))
        made = publish.request(con, EDITOR, "до пересборки")
    finally:
        con.close()

    build_db.main()  # «already exists» для шага схемы — норма, а не поломка
    rows = publish.pending(db_path)
    assert [row["id"] for row in rows] == [made["id"]]
    assert rows[0]["note"] == "до пересборки"
    printed.flush()
    assert "всего матчей" in printed.buffer.getvalue().decode("utf-8")
