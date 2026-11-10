# tests/test_queue_page.py
"""Сборка страницы кабинета лороведа: шаблон рендерится без маркеров, задачи встроены, ассеты на месте."""

import json
import re
from pathlib import Path

from db import api, store


def test_queue_page_renders_cleanly():
    """Сборка queue.html: не остаётся незаполненных маркеров @@...@@."""
    from build_queue_page import build_html
    tasks = api.queue(store.DB_PATH)
    html = build_html(tasks)
    markers = re.findall(r"@@[A-Z0-9_]+@@", html)
    assert not markers, f"В шаблоне остались маркеры: {markers}"


def test_queue_data_is_embedded_and_valid_json():
    """Снимок очереди встроен в HTML и парсится как валидный список задач."""
    from build_queue_page import build_html
    tasks = api.queue(store.DB_PATH)
    html = build_html(tasks)
    match = re.search(r"window\.__INITIAL_QUEUE__\s*=\s*(.+?);\s*</script>", html, re.DOTALL)
    assert match, "window.__INITIAL_QUEUE__ не найден в HTML"
    embedded = json.loads(match.group(1))
    assert isinstance(embedded, list)
    assert len(embedded) == len(tasks)
    # Проверяем ключевые поля в задачах
    first = embedded[0]
    assert "id" in first and "batch" in first and "task" in first


def test_queue_assets_exist_and_linked():
    """Файлы queue.css и queue.js существуют и подключены к странице."""
    from build_queue_page import build_html
    tasks = api.queue(store.DB_PATH)
    html = build_html(tasks)
    assert 'href="queue.css"' in html
    assert 'src="queue.js"' in html
    assert Path("queue.css").exists()
    assert Path("queue.js").exists()
