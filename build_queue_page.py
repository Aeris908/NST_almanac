# build_queue_page.py
"""Сборка страницы кабинета лороведа (queue.html) с очередью задач на проверку."""

import sys
from pathlib import Path

from db import api, store
from portal.templates import json_for_script, render

sys.stdout.reconfigure(encoding="utf-8")
OUTPUT_PATH = Path("queue.html")


def build_html(tasks, published_revision=None):
    """Шаблон очереди с встроенным снимком задач; render проверит отсутствие незакрытых маркеров."""
    return render("queue_page.html", {
        "QUEUE_DATA_JSON": json_for_script(tasks),
        "PUBLISHED_REVISION_JSON": json_for_script(published_revision),
    })


def main(db_path=store.DB_PATH):
    tasks = api.queue(db_path)
    html = build_html(tasks, api.publication_revision(db_path))
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Queue page written to {OUTPUT_PATH.resolve()} ({len(html) / 1024:.1f} KB) | "
          f"задач в очереди: {len(tasks)}")


if __name__ == "__main__":
    main()
