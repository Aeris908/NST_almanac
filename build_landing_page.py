"""Build the landing hub page (index.html) with the headline numbers from the soccer build."""

import json
import sys
from pathlib import Path

from portal.site_payload import headline_tokens
from portal.templates import render

sys.stdout.reconfigure(encoding="utf-8")

HEADLINE_STATS_PATH = Path("data/headline_stats.json")
OUTPUT_PATH = Path("index.html")


def main():
    if not HEADLINE_STATS_PATH.exists():
        sys.exit(
            f"{HEADLINE_STATS_PATH} не найден — соберите сначала футбольный портал: "
            f"python build_nekketsu_portal_v2.py"
        )
    headline = json.loads(HEADLINE_STATS_PATH.read_text(encoding="utf-8"))
    html_content = render("landing_page.html", headline_tokens(headline))

    OUTPUT_PATH.write_text(html_content, encoding="utf-8")
    print(f"Landing hub written to {OUTPUT_PATH.resolve()} ({len(html_content) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
