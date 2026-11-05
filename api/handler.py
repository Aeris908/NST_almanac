"""Правка летописи на Vercel: та же ручка, что `python db/serve.py`, но прямо в опубликованном сайте.

Рабочая форма одна: `handler` — потомок `serve.Handler`, который Vercel загружает сам (файл в
`api/` с классом-обработчиком), поэтому список операций, обязательные аргументы, коды ответов и
тексты отказов задаёт `db/serve.py`, а не копия где-то здесь.

Своё здесь три: путь, который маршрутизатор Vercel иногда подменяет именем функции, адрес базы
(`NST_DB_PATH`, по умолчанию — та же `data/nst.db`) и JSON на аварию внутри ручки, которую
`db/serve.py` перехватывает только на записи.

Файловая система функции на Vercel доступна только на чтение, поэтому `persist: true` вернёт 500
с текстом отказа, а предпросмотр работает: он считается на копии базы в временном каталоге.
Постоянной базе записи — серверному Postgres — отведено одно место: `bind_database`.
"""

import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

ROOT = Path(__file__).resolve().parent.parent
# Пакеты репозитория видны и когда файл загружен как `api.handler`, и когда как `handler`.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import api, serve  # noqa: E402
from portal.env_file import secret  # noqa: E402

DB_PATH_ENV = "NST_DB_PATH"
HANDLE_PARAM = "nst_handle"
# Пути, которыми маршрутизатор может заменить исходную ручку: корень и имя самой функции.
OWN_PATHS = ("/api", "/api/", "/api/handler", "/api/handler.py")


class _BoundApi:
    """Вызовы `db/api.py` с явным путём базы: `db/serve.py` умеет обращаться только по умолчанию."""

    def __init__(self, db_path):
        self.db_path = db_path

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        call = getattr(api, name)

        def bound(*args, **kwargs):
            kwargs.setdefault("db_path", self.db_path)
            return call(*args, **kwargs)

        return bound


_bound = [""]


def bind_database(db_path=None):
    """Откуда функция читает базу: `NST_DB_PATH`, иначе — тот же `data/nst.db`, что и локальный сервер.

    Сюда встанет серверный Postgres (Neon): вместо пути — строка подключения и такой же слой
    над `db/api.py`. Драйвера нет сознательно: боевой базы там ещё нет, а непроверенное
    соединение в путь записи летописи вставлять нельзя.
    """
    resolved = str(secret(DB_PATH_ENV) or db_path or api.DB_PATH)
    if _bound[0] != resolved:
        serve.api = _BoundApi(Path(resolved))
        _bound[0] = resolved
    return Path(resolved)


def _matched_handle(header):
    """Ручка из `x-now-route-matches`: именованная группа `(?<handle>.*)` из маршрута."""
    for key, value in parse_qsl(header or "", keep_blank_values=True):
        if key in ("handle", "rest", "path"):
            return value
    return ""


def _restored_path(request):
    """Исходная ручка, если маршрутизатор стёр её именем функции: сначала `nst_handle`, затем заголовок."""
    path, _, query = request.path.partition("?")
    if path not in OWN_PATHS:
        return request.path
    pairs = parse_qsl(query, keep_blank_values=True)
    given = dict(pairs).get(HANDLE_PARAM) or _matched_handle(request.headers.get("x-now-route-matches"))
    if not given:
        return request.path
    if not given.startswith("/"):
        given = "/api/" + given.lstrip("/")
    rest = [(key, value) for key, value in pairs if key != HANDLE_PARAM]
    return f"{given}?{urlencode(rest)}" if rest else given


class handler(serve.Handler):
    """Точка входа Vercel: поведение `db/serve.py` целиком, плюс две страховки функции.

    Авария внутри ручки (и всё, что не поймал сам `db/serve.py`) обязана закончиться JSON: панель
    показывает текст отказа, а не «HTTP 500». Второй ответ поверх уже отправленного ломает
    соединение, поэтому он идёт только пока ничего не ушло.
    """

    def do_GET(self):  # noqa: N802 — имя метода задаёт http.server
        return self._guarded(super().do_GET)

    def do_POST(self):  # noqa: N802 — имя метода задаёт http.server
        return self._guarded(super().do_POST)

    def _reply(self, status, payload, *, origin=None):
        self.answered = True
        return super()._reply(status, payload, origin=origin)

    def _guarded(self, handle):
        """Вызов ручки: то, что не поймал `db/serve.py`, всё равно должно кончиться JSON-ответом."""
        self.path = _restored_path(self)
        try:
            return handle()
        except Exception as error:  # noqa: BLE001 — соединение не должно обрываться без ответа
            if getattr(self, "answered", False):
                raise
            sys.stderr.write(f"500 {self.path}: {type(error).__name__}: {error}\n")
            return self._reply(500, {"ok": False, "error": f"ручка не ответила: {error}"},
                               origin=self._origin() or None)


bind_database()
