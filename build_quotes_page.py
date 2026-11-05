"""Build the NST quotes page (quotes.html) with quotes and avatars injected as JSON."""

import json
import sys
from pathlib import Path

from portal.templates import group_thousands, render

sys.stdout.reconfigure(encoding="utf-8")

QUOTES_PATH = Path("nst_quotes.json")
AVATARS_PATH = Path("player_avatars.json")
OUTPUT_PATH = Path("quotes.html")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    quotes = load_json(QUOTES_PATH)
    avatars = {name.lower(): avatar for name, avatar in load_json(AVATARS_PATH).items()}

    html_content = render("quotes_page.html", {
        "QUOTES_JSON": json.dumps(quotes, ensure_ascii=False),
        "AVATARS_JSON": json.dumps(avatars, ensure_ascii=False),
        "QUOTES": group_thousands(len(quotes)),
    })

    OUTPUT_PATH.write_text(html_content, encoding="utf-8")
    print(f"Quotes page written to {OUTPUT_PATH.resolve()} ({len(html_content) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
