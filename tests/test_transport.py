"""Vercel-функция правки отвечает ровно тем же, что `python db/serve.py`.

Сверка без портов и без живого Vercel: класс-обработчик вызывается напрямую, с буфером вместо
сокета. Одна и та же сборка запроса проходит сначала через `serve.Handler` (так сервер отвечает
локально), затем через `api/handler.py` (так его вызывает Vercel). Своим у функции может быть
только путь, который маршрутизатор подменяет именем функции, и адрес базы — на них тесты и
смотрят; токен, источник, лимит тела, коды и тексты отказов принадлежат `db/serve.py`.
"""

import io
import json
import shutil
from email.message import Message
from urllib.parse import urlencode

import pytest
from api import handler as transport
from db import api, serve
from support import SCOREFUL, sides

TOKEN = "test-token-0123456789"
WRONG_TOKEN = "wrong-token-0123456789"
EDITOR = "проверяющий"
OWN_ORIGIN = "http://127.0.0.1:8000"
FOREIGN_ORIGIN = "https://chuzhoy.example"
# Часы ответа и таймер пересчёта различаются у двух прогонов по определению; метка операции
# случайна на каждую правку — её форма сверяется отдельно, а не равенством ответов.
VOLATILE_HEADERS = ("Date",)
VOLATILE_FIELDS = ("recomputed_in_ms", "op")


class _Buffer:
    """Куда обработчик пишет ответ: вместо сокета — байты в памяти."""

    def __init__(self):
        self.data = bytearray()

    def write(self, payload):
        self.data += payload
        return len(payload)


def _ask(cls, method, path, *, token=TOKEN, origin=None, body=None, raw=None, extra=None):
    """Запрос сквозь класс-обработчик: (код, заголовки, тело) — как у живого HTTP-сервера."""
    payload = raw if raw is not None else json.dumps(
        {} if body is None else body, ensure_ascii=False).encode("utf-8")
    sent = b"" if method == "GET" else payload
    fields = {"Authorization": f"Bearer {token}" if token else None,
              "Origin": origin,
              "Content-Length": None if method == "GET" else str(len(sent))}
    fields.update(extra or {})
    headers = Message()
    for name, value in fields.items():
        if value:
            headers[name] = value
    request = object.__new__(cls)
    request.command = method
    request.path = path
    request.requestline = f"{method} {path} HTTP/1.1"
    request.request_version = "HTTP/1.1"
    request.close_connection = True
    request.headers = headers
    request.rfile = io.BytesIO(sent)
    request.wfile = _Buffer()
    getattr(request, f"do_{method}")()
    head, _, rest = bytes(request.wfile.data).partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    text = rest.decode("utf-8")
    return {"statusCode": int(lines[0].split(" ", 2)[1]),
            "headers": {name: value for name, value in
                        (pair.split(": ", 1) for pair in lines[1:] if ": " in pair)
                        if name not in VOLATILE_HEADERS},
            "body": json.loads(text) if text[:1] == "{" else text}


def served(method, path, **kwargs):
    """Эталон: так же сборку запроса обслуживает локальный `python db/serve.py`."""
    return _ask(serve.Handler, method, path, **kwargs)


def function(method, path, **kwargs):
    """Проверяемое: та же сборка запроса, дошедшая до точки входа Vercel."""
    return _ask(transport.handler, method, path, **kwargs)


def _stable(answer):
    """Ответ так, как он сравним у двух прогонов: без метки операции и без таймера пересчёта."""
    if isinstance(answer["body"], dict):
        answer = dict(answer, body={key: value for key, value in answer["body"].items()
                                    if key not in VOLATILE_FIELDS})
    return answer


def matches(method, path, **kwargs):
    """Один вход на двух обработчиках: функция обязана отдать ровно то, что отдал бы `db/serve.py`."""
    reference, answer = served(method, path, **kwargs), function(method, path, **kwargs)
    assert _stable(answer) == _stable(reference), f"{method} {path}: {answer} != {reference}"
    return answer, reference


@pytest.fixture(scope="module", autouse=True)
def live_db_untouched():
    """Живая `data/nst.db` — только на чтение: функция работает с копией из `NST_DB_PATH`."""
    was = api.revision(api.DB_PATH) if api.DB_PATH.exists() else None
    try:
        yield
    finally:
        if was is not None:
            assert api.revision(api.DB_PATH) == was, "функция правит живую базу"


@pytest.fixture(autouse=True)
def editor_env(monkeypatch, db_path):
    """Один токен, одна подпись и один allowlist на обе стороны сверки; база — копия теста."""
    monkeypatch.setenv("NST_EDITOR_TOKEN", TOKEN)
    monkeypatch.setenv("NST_EDITOR_NAME", EDITOR)
    monkeypatch.setenv("NST_EDITOR_ORIGINS", OWN_ORIGIN)
    monkeypatch.setattr(serve, "api", api)
    monkeypatch.setattr(transport, "_bound", [""])
    transport.bind_database(db_path)
    return db_path


def test_state_matches_the_local_server(editor_env):
    answer, _ = matches("GET", "/api/state")
    assert answer["statusCode"] == 200
    assert answer["body"]["revision"] == api.revision(editor_env)


def test_journal_matches_the_local_server():
    for path in ("/api/log", "/api/log?limit=5", "/api/log?limit=500"):
        answer, _ = matches("GET", path)
        assert answer["statusCode"] == 200
    assert len(matches("GET", "/api/log?limit=5")[0]["body"]["entries"]) <= 5


def test_players_with_empty_query_matches_the_local_server():
    answer, _ = matches("GET", "/api/players?q=")
    assert answer["statusCode"] == 200 and answer["body"]["players"]


def test_queue_and_containers_match_the_local_server():
    for path in ("/api/queue", "/api/containers"):
        assert matches("GET", path)[0]["statusCode"] == 200


def test_document_frame_matches_the_local_server(find):
    doc_key = find("select doc_key from tournament_docs where doc_key <> '' limit 1",
                   what="документ турнира")
    answer, _ = matches("GET", f"/api/doc?doc_key={doc_key}")
    assert answer["statusCode"] == 200 and answer["body"]["doc"]


def test_internal_failure_answered_with_json_500_like_the_local_server(monkeypatch):
    """`db/serve.py` защищён от аварии внутри ручки только на записи: на сбое чтения локальный
    сервер рвёт соединение молча, а панель обязана увидеть текст, поэтому функция доотвечает сама."""
    def explode(*args, **kwargs):
        raise RuntimeError("проверка отказа")

    monkeypatch.setattr(serve.api, "state", explode, raising=False)
    with pytest.raises(RuntimeError):
        served("GET", "/api/state")
    answer = function("GET", "/api/state")
    assert answer["statusCode"] == 500 and answer["body"]["ok"] is False
    assert "проверка отказа" in answer["body"]["error"]


def test_failure_during_a_write_refused_with_the_same_text(monkeypatch):
    """Сбой на пути записи `db/serve.py` ловит сам — здесь сверяется ровно тот же отказ."""
    def explode(*args, **kwargs):
        raise RuntimeError("проверка отказа")

    monkeypatch.setattr(serve.api, "mutate", explode, raising=False)
    answer, _ = matches("POST", "/api/edit", body={"operation": "set-score",
                                                  "args": {"match_id": 1, "s1": 0, "s2": 0}})
    assert answer["statusCode"] == 500 and "сервер не справился" in answer["body"]["error"]


def test_preview_of_a_score_matches_the_local_server(con, find, db_path):
    match_id = find(SCOREFUL, what="матч с числами")
    was = api.revision(db_path)
    body = {"operation": "set-score", "args": {"match_id": match_id, "s1": 3, "s2": 0},
            "persist": False}
    answer, reference = matches("POST", "/api/edit", body=body)
    assert answer["statusCode"] == 200 and answer["body"]["persisted"] is False
    assert answer["body"]["delta"], "предпросмотр не вернул дельту: панели нечего показывать"
    # Метка операции своя на каждую правку, но форма обязана совпасть с локальной.
    assert len(answer["body"]["op"]) == len(reference["body"]["op"])
    assert api.revision(db_path) == was, "предпросмотр изменил базу функции"


def test_locate_matches_the_local_server(con, find):
    match_id = find(SCOREFUL, what="матч с числами")
    cards = sides(con, match_id)
    body = {"a": cards[0]["label"] or cards[0]["players"],
            "b": cards[1]["label"] or cards[1]["players"]}
    answer, _ = matches("POST", "/api/locate", body=body)
    assert answer["statusCode"] == 200 and answer["body"]["candidates"]


def test_request_without_token_matches_the_local_server():
    answer, _ = matches("GET", "/api/state", token=None)
    assert answer["statusCode"] == 401 and "токен" in answer["body"]["error"]


def test_wrong_token_matches_the_local_server():
    answer, _ = matches("GET", "/api/state", token=WRONG_TOKEN)
    assert answer["statusCode"] == 401


def test_foreign_origin_matches_the_local_server():
    answer, _ = matches("GET", "/api/state", origin=FOREIGN_ORIGIN)
    assert answer["statusCode"] == 403
    assert "Access-Control-Allow-Origin" not in answer["headers"]


def test_own_origin_gets_cors_headers_like_the_local_server():
    answer, _ = matches("GET", "/api/state", origin=OWN_ORIGIN)
    assert answer["headers"]["Access-Control-Allow-Origin"] == OWN_ORIGIN
    assert answer["headers"]["Vary"] == "Origin"
    assert answer["headers"]["Cache-Control"] == "no-store"


def test_preflight_matches_the_local_server():
    answer, _ = matches("OPTIONS", "/api/edit", origin=OWN_ORIGIN)
    assert answer["statusCode"] == 204
    assert answer["headers"]["Access-Control-Allow-Methods"] == "GET, POST, OPTIONS"
    assert answer["headers"]["Access-Control-Allow-Headers"] == "Authorization, Content-Type"
    assert answer["headers"]["Vary"] == "Origin"
    refused, _ = matches("OPTIONS", "/api/edit", origin=FOREIGN_ORIGIN)
    assert refused["statusCode"] == 403


def test_unknown_operation_refuses_with_the_list_from_serve():
    answer, _ = matches("POST", "/api/edit", body={"operation": "телепорт", "args": {}})
    assert answer["statusCode"] == 400
    error = answer["body"]["error"]
    assert error.startswith("неизвестная операция") and ", ".join(serve.OPERATIONS) in error


def test_missing_required_argument_names_it_like_the_local_server(con, find):
    match_id = find(SCOREFUL, what="матч с числами")
    body = {"operation": "set-score", "args": {"match_id": match_id}}
    answer, _ = matches("POST", "/api/edit", body=body)
    assert answer["statusCode"] == 400
    assert answer["body"]["error"] == f"в args нет {serve.REQUIRED_ARGS['set-score'][1]}"


def test_unknown_handle_answers_json_404_like_the_local_server():
    for method, path in (("GET", "/api/нет-такой-ручки"), ("POST", "/api/тоже-нет")):
        answer, _ = matches(method, path, body=None if method == "GET" else {})
        assert answer["statusCode"] == 404 and "нет ручки" in answer["body"]["error"]


def test_body_of_the_request_checked_like_the_local_server():
    huge = json.dumps({"operation": "set-score",
                       "args": {"match_id": 1, "s1": 0, "s2": 0,
                                "мусор": "а" * serve.MAX_BODY}}, ensure_ascii=False).encode("utf-8")
    for raw in (huge, "не JSON".encode(), b"[1, 2]"):
        answer, _ = matches("POST", "/api/edit", raw=raw)
        assert answer["statusCode"] == 400, raw[:24]


def test_router_replacement_does_not_change_the_answer():
    """Маршрут `vercel.json` может принести в функцию имя самой функции вместо ручки: ответ
    обязан остаться ответом ручки, включая строку запроса."""
    with_param = f"/api/handler?{urlencode({'nst_handle': '/api/log', 'limit': '3'})}"
    assert function("GET", with_param) == served("GET", "/api/log?limit=3")
    bare = f"/api/handler?{urlencode({'nst_handle': 'players', 'q': 'сокол'})}"
    assert function("GET", bare) == served("GET", f"/api/players?{urlencode({'q': 'сокол'})}")
    header = {"x-now-route-matches": urlencode({"handle": "containers"})}
    assert function("GET", "/api/handler", extra=header) == served("GET", "/api/containers")
    body = {"operation": "set-score", "args": {"match_id": 1}}
    edit = f"/api/handler?{urlencode({'nst_handle': '/api/edit'})}"
    assert function("POST", edit, body=body) == served("POST", "/api/edit", body=body)


def test_function_carries_no_copy_of_the_edit_contract():
    for name in ("OPERATIONS", "REQUIRED_ARGS", "MAX_BODY", "TOKEN_ENV", "NAME_ENV",
                 "ORIGINS_ENV", "DEFAULT_ORIGINS"):
        assert not hasattr(transport, name), f"в функции появился свой {name}"
    assert transport.handler.__mro__[1] is serve.Handler
    verbs = {name for name in dir(serve.Handler) if name.startswith("do_")}
    assert {name for name in dir(transport.handler) if name.startswith("do_")} == verbs


def test_write_through_the_function_matches_the_local_server(con, find, db_path, tmp_path):
    """Запись через функцию даёт тот же ответ и ту же базу, что запись через `db/serve.py`.

    Дважды одну правку не сверить: вторая уже не находит изменений, поэтому эталон пишется в
    зеркальную копию, открытую тем же `bind_database`.
    """
    mirror = tmp_path / "зеркало.db"
    shutil.copy(db_path, mirror)
    match_id = find(SCOREFUL, what="матч с числами")
    body = {"operation": "set-score", "args": {"match_id": match_id, "s1": 7, "s2": 2},
            "persist": True}
    transport.bind_database(mirror)
    reference = served("POST", "/api/edit", body=body)
    transport.bind_database(db_path)
    answer = function("POST", "/api/edit", body=body)
    assert _stable(answer) == _stable(reference)
    assert answer["statusCode"] == 200 and answer["body"]["persisted"] and answer["body"]["journal"]
    assert sides(con, match_id)[0]["score"] == 7
    assert api.revision(db_path) == api.revision(mirror), "база функции разошлась с базой сервера"
    assert function("GET", "/api/state")["body"]["revision"] == api.revision(db_path)


def test_environment_names_the_database(monkeypatch, db_path):
    monkeypatch.setattr(transport, "_bound", [""])
    monkeypatch.setenv(transport.DB_PATH_ENV, str(db_path))
    assert transport.bind_database() == db_path
    assert serve.api.db_path == db_path
