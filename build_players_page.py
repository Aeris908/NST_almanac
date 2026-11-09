# build_players_page.py
"""Build the NST player catalog page (players.html) — школьный выпускной альбом."""
import json
import sys
from pathlib import Path

from db import store
from portal.players_dataset import build_players_dataset
from portal.templates import render

sys.stdout.reconfigure(encoding="utf-8")
OUTPUT_PATH = Path("players.html")


def build_html(dataset):
    """Шаблон альбома с встроенным каталогом; render бросит KeyError на лишний маркер."""
    return render("players_page.html", {
        "PLAYERS_JSON": json.dumps(dataset, ensure_ascii=False),
    })


def main(db_path=store.DB_PATH):
    dataset = build_players_dataset(db_path)
    html = build_html(dataset)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    stats = dataset["stats"]
    print(f"Players page written to {OUTPUT_PATH.resolve()} ({len(html) / 1024:.1f} KB) | "
          f"игроков {stats['total_players']}, дисциплин {stats['disciplines_count']}")


if __name__ == "__main__":
    main()