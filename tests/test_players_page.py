# tests/test_players_page.py
"""Сборка страницы каталога: шаблон рендерится без маркеров, данные встроены, ассеты на месте."""
import json
import re
import shutil

import pytest

from portal.players_dataset import build_players_dataset


@pytest.fixture(scope="module")
def page_db(tmp_path_factory, source_db):
    target = tmp_path_factory.mktemp("players_page") / "nst.db"
    shutil.copy(source_db, target)
    return target


@pytest.fixture(scope="module")
def html(page_db):
    from build_players_page import build_html
    return build_html(build_players_dataset(page_db))


def test_маркеры_не_остаются(html):
    assert not re.findall(r"@@[A-Z0-9_]+@@", html)


def test_players_встроен_и_парсится(html):
    m = re.search(r"const PLAYERS = (.+);", html)
    assert m, "const PLAYERS не встроен"
    data = json.loads(m.group(1))
    assert {"stats", "disciplines", "players"} <= set(data)
    assert data["players"], "каталог пуст"


def test_ассеты_и_сетка(html):
    assert 'href="players.css"' in html
    assert 'src="players.js"' in html
    assert 'id="playersGrid"' in html