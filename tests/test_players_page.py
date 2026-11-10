# tests/test_players_page.py
"""Сборка страницы каталога: шаблон рендерится без маркеров, данные встроены, ассеты на месте.

Каталог — общая витрина по всем дисциплинам с боевыми карточками и досье-модалкой.
"""
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


def test_элементы_витрины_на_месте(html):
    # Поиск, сортировка, фильтр дисциплин, счётчик и досье-модалка — живые элементы каталога.
    for marker in (
        'id="playerSearch"',
        'id="playerSort"',
        'id="disciplineFilters"',
        'id="catalogStats"',
        'id="catalogCount"',
        'id="dossierModal"',
    ):
        assert marker in html, f"нет элемента витрины: {marker}"


def test_тема_каталога_а_не_альбома(html):
    assert "Каталог игроков" in html
    for legacy in ("Выпускной альбом", "album-cover", "album-grid", "Marck+Script", "Playfair"):
        assert legacy not in html, f"остался альбомный артефакт: {legacy}"


def test_шрифты_ретро_семьи(html):
    assert "Russo+One" in html
    assert "JetBrains+Mono" in html


def test_аудио_дека_подключена(html):
    assert 'src="audio-player.js"' in html
    assert 'data-discipline="players"' in html


def test_json_безопасен_внутри_script():
    # Строка из сообщества с </script> не должна разрывать script-элемент на этапе HTML-парсинга.
    from build_players_page import build_html
    hostile = "</script><img src=x onerror=alert(1)>"
    payload = {
        "stats": {}, "disciplines": [],
        "players": [{
            "nick": "X", "featured_quote": hostile, "disciplines": [],
            "career": {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "win_rate": 0,
                       "goals_for": 0, "goals_against": 0, "goal_diff": 0},
        }],
    }
    page = build_html(payload)
    m = re.search(r"const PLAYERS = (.+);", page)
    assert m, "const PLAYERS не встроен"
    assert "</script>" not in m.group(1), "JSON содержит литеральный </script> — breakout"
    assert json.loads(m.group(1))["players"][0]["featured_quote"] == hostile