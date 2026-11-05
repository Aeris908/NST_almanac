"""Чтение `.env`, чтобы секреты не приходилось вывозить в переменные оболочки.

Смысл ровно один: `.env` лежит рядом с кодом, в git не попадает ([.gitignore:74]), а процессы,
которые запускает сборка и редактор, наследуют окружение уже запущенного приложения — то есть
`setx`/переменная пользователя до них не долетает. Без этого файла токен пришлось бы вставлять
прямо в командную строку, а он осел бы в истории оболочки и в логах.

Значения из `.env` никогда не печатаются: наружу отдаётся только сам секрет туда, где его читает
HTTP-запрос, и строка «задан / не задан» для отчётов.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def parse(path=ENV_PATH):
    """Пара ключ → значение из файла; пустые и закомментированные строки пропускаются."""
    if path is None or not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            values[key] = value
    return values


def load(path=ENV_PATH):
    """Дополнить os.environ значениями из `.env`; то, что уже задано в окружении, не перезаписывать."""
    values = parse(path)
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values


def secret(name, path=ENV_PATH):
    """Секрет по имени: сначала окружение, потом `.env`. Пустая строка означает «не задан»."""
    return os.environ.get(name) or load(path).get(name) or ""


def is_set(name, path=ENV_PATH):
    """True/False без раскрытия значения — для отчётов сборки и сообщений об ошибке."""
    return bool(secret(name, path))
