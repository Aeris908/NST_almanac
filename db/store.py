"""Единственное место, где проект решает, с какой базой он работает.

Путь по умолчанию — `DB_PATH`, все соединения открываются через `connect()`. Сейчас это файл
`data/nst.db`; серверная база (Postgres) подключается здесь же, и ни один модуль `db/` менять не
придётся — там не осталось ни одного прямого вызова драйвера.

Row factory и `PRAGMA` здесь не ставятся: у читателей они разные, а ядро записи обязано открывать
соединение так, как описано в `db/edit.py`, иначе откат теряет внешние ключи.
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "nst.db"


def is_pg(path):
    """Является ли адрес строкой подключения к Postgres."""
    if not path:
        return False
    text = str(path).strip()
    return text.startswith(("postgresql://", "postgres://"))


def parse_json(value, default=None):
    """Разбор JSON-поля: в SQLite приходит str, в Postgres (через psycopg) уже может быть dict/list."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return default
    text = value.strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def fold(text):
    """Регистронезависимость текста базы: у встроенного `lower()` SQLite латиница и всё.

    Подписи туров и ники по-русски через `lower()` не сворачиваются вообще, и поиск по ним
    возвращал бы ноль. В Postgres ту же работу делает его `lower()` (он знает юникод), поэтому
    генератор PG-схемы заменяет `fold(...)` на `lower(...)`.
    """
    return " ".join(str(text or "").split()).lower()


def connect(path=None):
    """Соединение с базой: названный файл, строка подключения Postgres или `DB_PATH`."""
    target = path or DB_PATH
    if is_pg(target):
        from db import pg
        return pg.connect(str(target))
    con = sqlite3.connect(target)
    con.create_function("fold", 1, fold, deterministic=True)
    return con
