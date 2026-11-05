"""HTTP-лицо правки базы: то же, что `db/api.py`, но для страницы с карандашами.

Десять ручек, ни одна не работает без токена:

    GET  /api/state                 ревизия базы, сколько строк, сколько живых правок, очередь
    GET  /api/log?limit=20          журнал правок (для панели «откатить»)
    GET  /api/queue                 неразобранные задачи редактуры вместе с их строками
    GET  /api/containers            чем можно принять новую игру: турниры-документы и сезоны
    GET  /api/doc?doc_key=…         рамка турнира для правки
    GET  /api/players?q=…           карточки игроков по нику — для переименования и слияния
    GET  /api/search?season=…       строки по сезону, турниру, туру и игроку — когда кликать некуда
    GET  /api/publish               очередь публикаций: что ждёт выката и сколько правок живо
    POST /api/locate {a, b, ...}    какие строки базы подходят под то, что редактор видит на странице
    POST /api/edit {operation, args, persist, expect}   предпросмотр (persist=false) или запись

`editor` в журнале берётся из `NST_EDITOR_NAME`, а не из запроса: подпись в журнале должна
принадлежать проверенной учётной записи, а не тому, что напечатал клиент. Токен — только из
переменной окружения, в репозитории его нет.

Запускается локально, рядом со статическим сайтом:

    python db/serve.py --port 8090   # секрет берётся из .env (NST_EDITOR_TOKEN) или из окружения
    python -m http.server 8000        # сама страница
    http://127.0.0.1:8000/soccer.html?edit=1

На Vercel этот же `db/api.py` вызовется из функции, а вместе с ним и Neon: менять интерфейс
запросов ради этого не нужно — UI обращается по относительному пути `/api/...`, если сервер
задан в `<meta name="nst-editor-api">`.
"""

import argparse
import hmac
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import api, edit, store  # noqa: E402
from portal.env_file import secret  # noqa: E402

TOKEN_ENV = "NST_EDITOR_TOKEN"
NAME_ENV = "NST_EDITOR_NAME"
ORIGINS_ENV = "NST_EDITOR_ORIGINS"
DEFAULT_ORIGINS = "http://127.0.0.1:8000 http://localhost:8000"
MAX_BODY = 64 * 1024
OPERATIONS = ("set-score", "set-players", "set-source", "set-place", "set-date", "set-phase",
              "set-provenance", "set-rating", "rate-scope", "add-match", "add-tournament",
              "set-doc", "drop-match", "drop-tournament", "rename-player", "merge-player",
              "void", "unvoid", "unhide", "publish-request", "undo")
# Что обязано приехать в args: у каждой операции свой идентификатор, и отсутствие match_id у
# правки игрока — это не «забыли», а перепутанная ручка.
REQUIRED_ARGS = {
    "set-score": ("match_id", "s1", "s2"),
    "set-players": ("match_id", "sides"),
    "set-source": ("match_id",),
    "set-place": ("match_id",),
    "set-date": ("match_id",),
    "set-phase": ("match_id",),
    "set-provenance": ("match_id",),
    "set-rating": ("match_id",),
    "add-match": ("sides",),
    "add-tournament": ("doc_key", "title"),
    "set-doc": ("doc_key",),
    "drop-match": ("match_id",),
    "drop-tournament": ("doc_key",),
    "rename-player": ("player_id", "nick"),
    "merge-player": ("keep_id", "drop_id"),
    "void": ("match_id",), "unvoid": ("match_id",), "unhide": ("match_id",),
    # Откат обязан называть, что именно откатывать: `last`, `op:<метка>` или id записи.
    "undo": ("what",),
    # У запроса на выкат обязательных полей нет: `note` — пояснение для человека, его может не быть.
    "publish-request": (),
}


def allowed_origins():
    return set((secret(ORIGINS_ENV) or DEFAULT_ORIGINS).replace(",", " ").split())


def token():
    return secret(TOKEN_ENV)


def editor_name():
    return secret(NAME_ENV) or "owner"


class Handler(BaseHTTPRequestHandler):
    server_version = "NSTEditor/1.0"

    def _reply(self, status, payload, *, origin=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _origin(self):
        """Источник запроса: свой — отдаём CORS-заголовок, чужой — не обслуживаем вовсе.

        Заголовок `Origin` шлют браузеры; запрос без него (тот же хост, curl, следующий билд)
        остаётся легитимным — но страница с другого сайта не сможет ни прочитать ответ, ни
        отправить правку.
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return None
        return origin if origin in allowed_origins() else False

    def _authorized(self):
        given = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        # Сравнение постоянное по времени: ответ «похоже, но не совсем» тут ничего не ускоряет,
        # а по времени ответа токен перебирать удобней.
        return bool(token()) and hmac.compare_digest(given, token())

    def do_OPTIONS(self):  # noqa: N802 — имя метода задаёт http.server
        origin = self._origin()
        if origin is False:
            return self._reply(403, {"ok": False, "error": "источник запроса не разрешён"})
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        origin, path = self._origin(), urlparse(self.path).path
        if origin is False:
            return self._reply(403, {"ok": False, "error": "источник запроса не разрешён"})
        if not self._authorized():
            return self._reply(401, {"ok": False, "error": "нужен токен редактора"}, origin=origin)
        if path == "/api/state":
            return self._reply(200, {"ok": True, **api.state()}, origin=origin)
        if path == "/api/log":
            limit = int((parse_qs(urlparse(self.path).query).get("limit") or ["20"])[0])
            return self._reply(200, {"ok": True, "entries": api.journal_entries(max(1, min(limit, 200)))},
                               origin=origin)
        if path == "/api/queue":
            return self._reply(200, {"ok": True, "tasks": api.queue()}, origin=origin)
        if path == "/api/containers":
            return self._reply(200, {"ok": True, **api.containers()}, origin=origin)
        if path == "/api/doc":
            key = (parse_qs(urlparse(self.path).query).get("doc_key") or [""])[0]
            return self._reply(200, {"ok": True, "doc": api.doc_frame(key)}, origin=origin)
        if path == "/api/players":
            found = (parse_qs(urlparse(self.path).query).get("q") or [""])[0]
            return self._reply(200, {"ok": True, "players": api.players(found)}, origin=origin)
        if path == "/api/search":
            asked = parse_qs(urlparse(self.path).query)
            word = {name: (asked.get(name) or [""])[0] for name in
                    ("season", "tournament", "tour", "player")}
            hidden = (asked.get("include_hidden") or [""])[0] in ("1", "true", "yes")
            return self._reply(200, {"ok": True, **api.search(include_hidden=hidden, **word)},
                               origin=origin)
        if path == "/api/publish":
            return self._reply(200, {"ok": True, **api.publish_queue()}, origin=origin)
        return self._reply(404, {"ok": False, "error": f"нет ручки {path}"}, origin=origin)

    def do_POST(self):  # noqa: N802
        origin, path = self._origin(), urlparse(self.path).path
        if origin is False:
            return self._reply(403, {"ok": False, "error": "источник запроса не разрешён"})
        if not self._authorized():
            return self._reply(401, {"ok": False, "error": "нужен токен редактора"}, origin=origin)
        body = self._json_body()
        if body is None:
            return
        try:
            if path == "/api/locate":
                answer = {"ok": True, "candidates": api.locate(
                    body.get("a") or body.get("p1", ""), body.get("b") or body.get("p2", ""),
                    season=body.get("season"), tour=body.get("tour"), score=body.get("score"),
                    include_hidden=bool(body.get("include_hidden")))}
            elif path == "/api/edit":
                answer = _edit(body)
            else:
                return self._reply(404, {"ok": False, "error": f"нет ручки {path}"}, origin=origin)
        except edit.EditError as error:
            return self._reply(400, {"ok": False, "error": str(error)}, origin=origin)
        except (KeyError, TypeError, ValueError) as error:
            return self._reply(400, {"ok": False, "error": f"непонятный запрос: {error}"}, origin=origin)
        except Exception as error:  # noqa: BLE001 — соединение не должно обрываться без ответа
            sys.stderr.write(f"500 {path}: {type(error).__name__}: {error}\n")
            return self._reply(500, {"ok": False, "error": f"сервер не справился: {error}"}, origin=origin)
        self._reply(200, answer, origin=origin)

    def _json_body(self):
        """Тело запроса или None (тогда ответ уже отправлен): размер и формат проверяются здесь."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self._reply(400, {"ok": False, "error": "тело запроса слишком большое или без длины"})
            return None
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError as error:
            self._reply(400, {"ok": False, "error": f"не JSON: {error}"})
            return None
        if not isinstance(body, dict):
            self._reply(400, {"ok": False, "error": "ожидался объект JSON"})
            return None
        return body

    def log_message(self, format, *args):  # noqa: A002 — сигнатура базового класса
        """Один запрос — одна строка в stderr: метод, путь, код. Токены и тела не печатаются."""
        sys.stderr.write(f"{self.command} {urlparse(self.path).path} {args[1] if len(args) > 1 else ''}\n")


def _edit(body):
    operation = body.get("operation")
    if operation not in OPERATIONS:
        raise edit.EditError(f"неизвестная операция {operation!r}; бывают {', '.join(OPERATIONS)}")
    args = body.get("args") or {}
    for name in REQUIRED_ARGS.get(operation, ()):
        if args.get(name) is None:
            raise edit.EditError(f"в args нет {name}")
    if operation == "add-match" and not (args.get("doc_key") or args.get("season")):
        raise edit.EditError("новой игре нужен турнир: doc_key или season")
    if operation == "rate-scope" and not (args.get("season") or args.get("doc_key")):
        raise edit.EditError("для массового флага нужен season или doc_key")
    if operation == "set-score":
        for field in ("s1", "s2"):
            if not isinstance(args.get(field), int) or args[field] < 0:
                raise edit.EditError(f"args.{field} обязан быть неотрицательным числом")
    if operation == "set-players":
        sides = args.get("sides")
        if not isinstance(sides, list) or len(sides) != 2 or not any(str(part).strip() for part in sides):
            raise edit.EditError('args.sides — две подписи сторон, '
                                 'например ["ectoPower", "sokol & PacnyTHuK"]')
    if operation == "set-source":
        links = args.get("links")
        if links is not None and (not isinstance(links, list)
                                  or any(not isinstance(pair, list) or len(pair) != 2
                                         for pair in links)):
            raise edit.EditError('args.links — список пар ["vk_post", "https://…"]')
    # Подпись в журнале — учётная запись, а не то, что прислал браузер.
    return api.mutate(operation, args, editor_name(), persist=bool(body.get("persist")),
                      expect=body.get("expect"))


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args(argv)

    if not token():
        sys.exit(f"Нет {TOKEN_ENV}: сервер правки не поднимается без секрета. "
                 f"Задайте его в окружении (см. .env.example), а не в файлах репозитория.")
    if not store.DB_PATH.exists():
        sys.exit("Нет базы data/nst.db — сначала python build_all.py (или db/build_db.py + import_stores).")

    print(f"правка доступна на http://{args.host}:{args.port}  (операции: {', '.join(OPERATIONS)})")
    print(f"разрешённые источники: {' '.join(sorted(allowed_origins()))}")
    print(f"редактор в журнале: {editor_name()}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
