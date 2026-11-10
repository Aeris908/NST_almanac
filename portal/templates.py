"""Static HTML templates rendered by the build scripts.

Templates live in the repository-level ``templates/`` directory and use
``@@NAME@@`` markers for the values injected at build time.
"""

import json
import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
TOKEN_PATTERN = re.compile(r"@@([A-Z0-9_]+)@@")


def json_for_script(value):
    """JSON для вставки внутрь <script>.

    Экранирует <, >, & и разделители строк U+2028/U+2029, чтобы строка из данных
    (например, цитата с ``</script>``) не разорвала script-элемент при HTML-парсинге.
    """
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def load_template(name):
    """Return a template's text with newline handling normalised to ``\\n``."""
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def group_thousands(number):
    """``2504`` to the ``2 504`` spelling the templates print."""
    return f"{number:,}".replace(",", " ")


def render(name, values):
    """Substitute ``@@TOKEN@@`` markers; refuse to ship a page with an unfilled marker."""
    html = load_template(name)
    for key, value in values.items():
        html = html.replace(f"@@{key}@@", str(value))
    leftover = sorted(set(TOKEN_PATTERN.findall(html)))
    if leftover:
        raise KeyError(f"{name}: маркеры без значений: {', '.join(leftover)}")
    return html
