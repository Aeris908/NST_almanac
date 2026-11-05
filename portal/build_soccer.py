"""Build the Goal 3 football almanac page (soccer.html)."""

import json
from dataclasses import replace
from pathlib import Path

from db.catalog import catalog_from_db, cup_rows_from_db
from db.pool import DB_PATH
from portal import dataset, master_table
from portal.env_file import secret
from portal.league_analytics import build as build_analytics
from portal.player_profiles import build as build_profiles
from portal.player_records import build as build_records
from portal.quotes import player_quotes_by_author
from portal.season_pages import build as build_seasons
from portal.site_payload import build as build_payload, headline_tokens
from portal.templates import render

OUTPUT_PATH = Path("soccer.html")
HEADLINE_STATS_PATH = Path("data/headline_stats.json")
DATA_PLACEHOLDER = "__DATA_PLACEHOLDER__"
# Локальная сборка правит через `python db/serve.py` рядом с сайтом; на Vercel функция обработки
# живёт по тому же адресу, что и сам сайт, и сборке туда указывает NST_EDITOR_API=".".
EDITOR_API_DEFAULT = "http://127.0.0.1:8090"


def editor_api():
    """Адрес сервера правки для `<meta name="nst-editor-api">` — значение подставляет сборка."""
    return secret("NST_EDITOR_API") or EDITOR_API_DEFAULT


def compose_payload(db_path=DB_PATH):
    """Payload страницы, посчитанный с этой базы.

    `db/api.py` вызывает её же для предпросмотра правки (по копии базы), поэтому «что сдвинется»
    и «что увидит сайт» считает один и тот же код. Мастер-таблица пересчитывается in-memory, а не
    берётся из файла: правка в пуле обязана быть видна до ближайшей сборки.

    Игры Кубка лиг добавляются к каталогу здесь, а не внутри `season_pages`: так они попадают и в
    историю игрока, и в таблицы сезона из одного места, и порядок в списке сезона не меняется —
    кубок всегда шёл после строк носителя.
    """
    data = dataset.load(db_path)
    data = replace(data, master_db=master_table.build_payload(data.base_matches))
    combined_matches = catalog_from_db(db_path) + cup_rows_from_db(db_path)
    player_matches, player_stats_addon = build_records(data, combined_matches)
    profiles = build_profiles(
        data, player_matches, player_stats_addon, player_quotes_by_author(data.quotes)
    )
    seasons = build_seasons(data, combined_matches, profiles)
    analytics = build_analytics(profiles, seasons["seasons_list"])
    return build_payload(data, seasons["combined_matches"], profiles, seasons, analytics)


def main():
    print("Rebuilding Nekketsu Portal with Clean Human-Readable Russian Interface...")
    payload = compose_payload()
    save_headline_stats(payload["headline"])

    html = render("soccer_page.html",
                  {**headline_tokens(payload["headline"]), "EDITOR_API": editor_api()})
    final_html = html.replace(DATA_PLACEHOLDER, json.dumps(payload, ensure_ascii=False))
    OUTPUT_PATH.write_text(final_html, encoding="utf-8")
    print(f"Redesigned Portal successfully written to: {OUTPUT_PATH.resolve()}")
    print(f"Final File Size: {len(final_html) / 1024:.1f} KB")


def save_headline_stats(headline):
    """Publish the headline numbers for the landing hub (it has no data payload of its own)."""
    HEADLINE_STATS_PATH.parent.mkdir(exist_ok=True)
    HEADLINE_STATS_PATH.write_text(
        json.dumps(headline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
