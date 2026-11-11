"""Генераторы не позволяют данным завершить HTML-элемент script."""

import json
import re

from portal import build_soccer

HOSTILE = '</script><img src=x onerror="alert(1)">&\u2028\u2029'


def test_soccer_json_cannot_close_script(tmp_path, monkeypatch):
    output = tmp_path / "soccer.html"
    monkeypatch.setattr(build_soccer, "OUTPUT_PATH", output)
    monkeypatch.setattr(build_soccer, "compose_payload", lambda: {"headline": {}, "quote": HOSTILE})
    monkeypatch.setattr(build_soccer, "save_headline_stats", lambda _: None)
    monkeypatch.setattr(build_soccer, "headline_tokens", lambda _: {})
    monkeypatch.setattr(build_soccer, "editor_api", lambda: '" onload="alert(1)')
    monkeypatch.setattr(build_soccer, "render", lambda _, values:
                        '<meta content="' + values["EDITOR_API"] + '"><script>const DATA = '
                        + build_soccer.DATA_PLACEHOLDER + ';</script>')
    build_soccer.main()
    html = output.read_text(encoding="utf-8")
    encoded = re.search(r"const DATA = (.+);</script>", html)[1]
    assert "<" not in encoded
    assert json.loads(encoded)["quote"] == HOSTILE
    assert 'content="&quot; onload=&quot;alert(1)"' in html


def test_quotes_and_avatars_cannot_close_script(tmp_path, monkeypatch):
    import build_quotes_page as quotes

    output = tmp_path / "quotes.html"
    monkeypatch.setattr(quotes, "OUTPUT_PATH", output)
    monkeypatch.setattr(quotes, "load_json", lambda path:
                        [HOSTILE] if path == quotes.QUOTES_PATH else {"Player": HOSTILE})
    monkeypatch.setattr(quotes, "render", lambda _, values:
                        values["QUOTES_JSON"] + "\n" + values["AVATARS_JSON"])
    quotes.main()
    encoded_quotes, encoded_avatars = output.read_text(encoding="utf-8").splitlines()
    assert "<" not in encoded_quotes + encoded_avatars
    assert json.loads(encoded_quotes) == [HOSTILE]
    assert json.loads(encoded_avatars) == {"player": HOSTILE}
