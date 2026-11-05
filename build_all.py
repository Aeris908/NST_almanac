"""Build every page of the NST Almanac and assemble the deployable bundle in deploy/.

Run with ``python build_all.py`` (or double-click build.bat on Windows).
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPLOY_DIR = ROOT / "deploy"

BUILDERS = (
    ("Scanning audio library and refreshing manifests", "scan_audio.py"),
    ("Syncing the rating pool into the match database", "db/build_db.py"),
    ("Importing season, special and team matches into the database", "db/import_stores.py"),
    ("Loading live VK results (data/vk_live_matches.json) into the database", "db/import_live.py"),
    ("Validating the match database", "db/validate.py"),
    ("Rebuilding the master table (nekketsu_master_table.json)", "build_master_table.py"),
    ("Building soccer portal (soccer.html)", "build_nekketsu_portal_v2.py"),
    ("Building quotes almanac (quotes.html)", "build_quotes_page.py"),
    ("Building landing hub (index.html)", "build_landing_page.py"),
)

PAGES = ("index.html", "soccer.html", "quotes.html")
ASSETS = ("audio-player.js", "audio-player.css", "soccer.css", "soccer.js", "editor.js", "editor.css")


def build_pages():
    for title, script in BUILDERS:
        print(f"\n--> {title} ({script})")
        subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, check=True)


def copy_to_deploy():
    DEPLOY_DIR.mkdir(exist_ok=True)
    for name in (*PAGES, *ASSETS):
        source = ROOT / name
        if source.exists():
            shutil.copy2(source, DEPLOY_DIR / name)
    if (ROOT / "audio").exists():
        shutil.copytree(ROOT / "audio", DEPLOY_DIR / "audio", dirs_exist_ok=True)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== BUILDING FULL NEKKETSU ALMANAC SUITE ===")
    build_pages()
    print("\n--> Copying the finished bundle to deploy/")
    copy_to_deploy()
    print(f"\n=== deploy/ is ready for hosting: {DEPLOY_DIR}")
    for name in (*PAGES, *ASSETS):
        print(f"  - deploy/{name}")
    print("  - deploy/audio/playlist.json + playlist-manifest.js (auto-generated)")
    print("  - deploy/audio/<discipline>/ (drop your own .mp3 files here)")


if __name__ == "__main__":
    main()
