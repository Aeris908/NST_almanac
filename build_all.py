"""Build every page of the NST Almanac and assemble the deployable bundle in deploy/.

Run with ``python build_all.py`` (or double-click build.bat on Windows).
Add ``--from-store`` to publish the store as it stands: the three steps that regenerate
``data/nst.db`` are skipped, so manual edits survive the build.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from db import store
from portal.env_file import secret

ROOT = Path(__file__).resolve().parent
DEPLOY_DIR = ROOT / "deploy"

BUILDERS = (
    ("Scanning audio library and refreshing manifests", "scan_audio.py"),
    ("Syncing the rating pool into the match database", "db/build_db.py"),
    ("Importing season, special and team matches into the database", "db/import_stores.py"),
    ("Loading live VK results (data/vk_live_matches.json) into the database", "db/import_live.py"),
    ("Refreshing lore review of rating dates", "db/elo_review_queue.py"),
    ("Validating the match database", "db/validate.py"),
    ("Rebuilding the master table (nekketsu_master_table.json)", "build_master_table.py"),
    ("Building soccer portal (soccer.html)", "build_nekketsu_portal_v2.py"),
    ("Building quotes almanac (quotes.html)", "build_quotes_page.py"),
    ("Building landing hub (index.html)", "build_landing_page.py"),
    ("Building player catalog (players.html)", "build_players_page.py"),
    ("Building lore review queue (queue.html)", "build_queue_page.py"),
)
# Шаги, которые пересоздают срез. Их немного, и они всегда идут первыми: пропуск означает
# «читать базу такой, какая она есть», а не «собрать её заново из носителей».
STORE_STEPS = ("db/build_db.py", "db/import_stores.py", "db/import_live.py")

PAGES = ("index.html", "soccer.html", "quotes.html", "players.html", "queue.html")
ASSETS = ("favicon.svg", "audio-player.js", "audio-player.css", "soccer.css", "soccer.js", "editor.js", "editor.css",
          "players.js", "players.css", "queue.js", "queue.css", "site-data.js", "report-helper.js")


def build_pages(from_store=False):
    for title, script in BUILDERS:
        if from_store and script in STORE_STEPS:
            continue
        if script == 'db/elo_review_queue.py' and not from_store and os.environ.get('VERCEL') == '1' and (secret('NST_POSTGRES_URL') or secret('DATABASE_URL')):
            print("\n--> Reading the current editor database from Postgres")
            # Схема подготовлена импортом; pull читает сервер одним согласованным срезом.
            # Ошибка чтения останавливает публикацию, чтобы не выкатить устаревший архив.
            subprocess.run([sys.executable, str(ROOT / 'db/sync.py'), 'pull'], cwd=ROOT, check=True)
        print(f"\n--> {title} ({script})")
        subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, check=True)


def copy_to_deploy():
    DEPLOY_DIR.mkdir(exist_ok=True)
    for name in (*PAGES, *ASSETS):
        source = ROOT / name
        if source.exists():
            target = DEPLOY_DIR / name
            for attempt in range(5):
                try:
                    shutil.copy2(source, target)
                    break
                except OSError:
                    if attempt == 4:
                        raise
                    import time
                    time.sleep(0.4)
    if (ROOT / "audio").exists():
        shutil.copytree(ROOT / "audio", DEPLOY_DIR / "audio", dirs_exist_ok=True)
    if (ROOT / 'site-data').exists():
        shutil.copytree(ROOT / 'site-data', DEPLOY_DIR / 'site-data', dirs_exist_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Собрать страницы альманаха и уложить готовый бандл в deploy/.")
    parser.add_argument("--from-store", action="store_true",
                        help="не перегенерировать data/nst.db: собрать сайт из того среза, "
                             "который уже лежит в базе")
    args = parser.parse_args()
    if args.from_store and not store.DB_PATH.exists():
        sys.exit("базы data/nst.db нет: --from-store читает готовый срез, а не создаёт его — "
                 "сначала обычный прогон python build_all.py")
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== BUILDING FULL NEKKETSU ALMANAC SUITE ==="
          + (" (from the existing store)" if args.from_store else ""))
    build_pages(from_store=args.from_store)
    print("\n--> Copying the finished bundle to deploy/")
    copy_to_deploy()
    print(f"\n=== deploy/ is ready for hosting: {DEPLOY_DIR}")
    for name in (*PAGES, *ASSETS):
        print(f"  - deploy/{name}")
    print("  - deploy/audio/playlist.json + playlist-manifest.js (auto-generated)")
    print("  - deploy/audio/<discipline>/ (drop your own .mp3 files here)")


if __name__ == "__main__":
    main()
