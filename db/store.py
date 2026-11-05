"""Единственное место, где проект решает, с какой базой он работает.

Путь по умолчанию — `DB_PATH`, все соединения открываются через `connect()`. Сейчас это файл
`data/nst.db`; серверная база (Postgres) подключится здесь же, и ни один модуль `db/` менять не
придётся — там не осталось ни одного прямого вызова драйвера.

Row factory и `PRAGMA` здесь не ставятся: у читателей они разные, а ядро записи обязан открывать
соединение так, как описано в `db/edit.py`, иначе откат теряет внешние ключи.
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "nst.db"


def fold(text):
    """Регистронезависимость текста базы: у встроенного `lower()` SQLite латиница и всё.

    Подписи туров и ники по-русски через `lower()` не сворачиваются вообще, и поиск по ним
    возвращал бы ноль. В Postgres ту же работу делает его `lower()` (он знает юникод), поэтому
    генератор PG-схемы заменяет `fold(...)` на `lower(...)`.
    """
    return " ".join(str(text or "").split()).lower()


def connect(path=None):
    """Соединение с базой: названный файл или тот, что лежит в `DB_PATH`."""
    con = sqlite3.connect(path or DB_PATH)
    con.create_function("fold", 1, fold, deterministic=True)
    return con
