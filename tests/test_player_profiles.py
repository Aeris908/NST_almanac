"""#85 (вариант А): мастер-таблица авторитетна, второго пересчёта рейтинга нет.

Проверяем правило на свойствах, а не на id строк: для игрока из пула все пять рейтинговых
полей берутся дословно у движка, для игрока без рейтинговых партий рейтинга нет вовсе
(active_elo/peak_elo = None, decay_penalty = 0.0, rated = False), а биография остаётся.
Селекторы — по имени игрока и по признаку rated, номера строк базы не используются.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal import player_profiles as pp
from portal.names import profile_sort_order
from portal.roster_tables import HOF_PEAK_ELO

RATING_FIELDS = ("active_elo", "peak_elo", "decay_penalty", "years_inactive", "last_season")
ADDON = {"reg_w": 1, "reg_l": 0, "ot_w": 0, "ot_l": 0, "pk_w": 0, "pk_l": 0}


def match(season="Season 5", result="ПОБЕДА", gf=3, ga=1, league="Высшая лига", technical=False):
    """Каталожная партия карточки: только то, что читают career_stats и last_activity."""
    return {"season": season, "result": result, "score_for": gf, "score_against": ga,
            "is_technical": technical, "league": league}


def engine_row(name, **kw):
    """Запись движка (форма portal.master_table.build_profiles) с рейтинговыми полями."""
    row = {"player": name, "league": "Дворовая", "status": "Инактив", "archetype": "ветеран",
           "playstyle": "классика", "active_elo": 1537.4, "peak_elo": 1576.5,
           "decay_penalty": 105.0, "years_inactive": 3.5, "last_season": "Season 7",
           "rated_games": 30, "provisional": False}
    row.update(kw)
    return row


def run_build(monkeypatch, engine_rows, matches_by_name, active=(), hof=()):
    """Собирает профили на игрушечном ростере: активные и легенды задаются явно."""
    monkeypatch.setattr(pp, "CORE_ACTIVE_COMMUNITY", list(active))
    monkeypatch.setattr(pp, "HALL_OF_FAME_LEGENDS", list(hof))
    names = set(list(active) + list(hof) + [r["player"] for r in engine_rows] + list(matches_by_name))
    player_matches = {name: list(matches_by_name.get(name, [])) for name in names}
    addon = {name: dict(ADDON) for name in names}
    data = SimpleNamespace(master_db={"power_rankings": engine_rows}, avatars={})
    return pp.build(data, player_matches, addon, {})


def by_name(profiles, name):
    return next(p for p in profiles if p["player"] == name)


def test_pool_inactive_takes_engine_fields_verbatim(monkeypatch):
    """Инактив из пула: ни калибровки, ни своего штрафа, ни пересчёта годов."""
    rows = [engine_row("Veteran", active_elo=1537.4, peak_elo=1576.5,
                       decay_penalty=105.0, years_inactive=3.5, last_season="Season 7")]
    profiles = run_build(monkeypatch, rows, {"Veteran": [match(season="Season 5")]})
    p = by_name(profiles, "Veteran")
    assert p["active_elo"] == 1537.4
    assert p["peak_elo"] == 1576.5
    assert p["decay_penalty"] == 105.0
    assert p["years_inactive"] == 3.5
    assert p["last_season"] == "Season 7"
    assert p["rated"] is True


def test_pool_active_peak_not_calibrated(monkeypatch):
    """Актив из пула: пик не сжимается калибровкой по числу каталожных партий."""
    rows = [engine_row("Hero", active_elo=1747.8, peak_elo=1805.4,
                       decay_penalty=0.0, years_inactive=0.0, last_season="Season 9")]
    profiles = run_build(monkeypatch, rows, {"Hero": [match()]}, active=("Hero",))
    p = by_name(profiles, "Hero")
    assert p["active_elo"] == 1747.8
    assert p["peak_elo"] == 1805.4
    assert p["rated"] is True


def test_pool_value_below_floor_and_unrounded_is_kept(monkeypatch):
    """Поля движка берутся как есть: без пола 1050 и без округления."""
    rows = [engine_row("Low", active_elo=1000.04, peak_elo=1000.04,
                       decay_penalty=0.0, years_inactive=0.0, last_season="Season 9")]
    profiles = run_build(monkeypatch, rows, {"Low": [match()]}, active=("Low",))
    p = by_name(profiles, "Low")
    assert p["active_elo"] == 1000.04
    assert p["peak_elo"] == 1000.04


def test_pool_hof_legend_peak_comes_from_engine(monkeypatch):
    """Легенда в пуле: справочная подмена пика снята с рейтингового пути."""
    rows = [engine_row("mafuta", active_elo=1520.4, peak_elo=1657.1,
                       decay_penalty=105.0, years_inactive=3.5, last_season="Season 7")]
    profiles = run_build(monkeypatch, rows, {"mafuta": [match()]}, hof=("mafuta",))
    p = by_name(profiles, "mafuta")
    assert p["is_hall_of_fame"] is True
    assert p["peak_elo"] == 1657.1
    assert p["peak_elo"] != HOF_PEAK_ELO["mafuta"]
    assert p["rated"] is True


def test_outside_veteran_has_no_rating(monkeypatch):
    """Ветеран только с каталожными партиями: нет рейтинговых партий — нет рейтинга."""
    profiles = run_build(monkeypatch, [], {"Catalog": [match(season="Season 2")]})
    p = by_name(profiles, "Catalog")
    assert p["active_elo"] is None
    assert p["peak_elo"] is None
    assert p["decay_penalty"] == 0.0
    assert p["rated"] is False
    # Биография остаётся: это не рейтинг.
    assert p["years_inactive"] is not None
    assert p["last_season"]


def test_outside_hof_legend_keeps_archival_peak_only(monkeypatch):
    """Легенда вне пула: почётный архивный пик есть, активного рейтинга нет."""
    profiles = run_build(monkeypatch, [], {"WiSe": [match(season="Season 1")]}, hof=("WiSe",))
    p = by_name(profiles, "WiSe")
    assert p["is_hall_of_fame"] is True
    assert p["active_elo"] is None
    assert p["peak_elo"] == HOF_PEAK_ELO["WiSe"]
    assert p["decay_penalty"] == 0.0
    assert p["rated"] is False


def test_sort_rated_desc_then_unrated(monkeypatch):
    """Сначала рейтингованные по убыванию active_elo, затем без рейтинга; None не роняет сортировку."""
    rows = [engine_row("High", active_elo=1700.0, peak_elo=1750.0, decay_penalty=0.0,
                       years_inactive=0.0, last_season="Season 9"),
            engine_row("Low", active_elo=1200.0, peak_elo=1250.0, decay_penalty=0.0,
                       years_inactive=0.0, last_season="Season 9")]
    matches = {"High": [match()], "Low": [match()], "Catalog": [match(season="Season 2")]}
    profiles = run_build(monkeypatch, rows, matches)
    order = [p["player"] for p in profiles]
    assert order.index("High") < order.index("Low") < order.index("Catalog")
    assert profiles[-1]["player"] == "Catalog"
    assert profiles[-1]["active_elo"] is None


def test_profile_sort_order_tolerates_missing_rating():
    """Ключ сортировки карточек не падает на None и ставит рейтингованных раньше."""
    unrated = {"is_active": False, "is_hall_of_fame": False, "active_elo": None, "matches": 5}
    rated = {"is_active": False, "is_hall_of_fame": False, "active_elo": 1200.0, "matches": 5}
    key_unrated = profile_sort_order(unrated)
    key_rated = profile_sort_order(rated)
    assert isinstance(key_unrated, tuple)
    assert key_rated < key_unrated


# --- потребитель: soccer.js ---

SOCCER_JS = ROOT / "soccer.js"


def test_soccer_js_has_no_direct_tostring_on_rating():
    """Страница не зовёт .toFixed прямо на рейтинге: при None она бы упала."""
    text = SOCCER_JS.read_text(encoding="utf-8")
    assert "function formatElo" in text
    assert not re.search(r"\.active_elo\.toFixed\(", text)
    assert not re.search(r"\.peak_elo\.toFixed\(", text)
    # Строка штрафа больше не печатает «-0 очков», когда штрафа нет.
    assert ';">-${p.decay_penalty} очков' not in text


@pytest.mark.skipif(shutil.which("node") is None, reason="node не установлен — только статическая проверка")
def test_soccer_js_formatelo_handles_null(tmp_path):
    """Форматтер рейтинга: null/undefined -> «—», число -> один знак после точки."""
    harness = tmp_path / "p85_formatelo.cjs"
    harness.write_text(
        "const fs = require('fs');\n"
        "const src = fs.readFileSync(process.argv[2], 'utf8');\n"
        "const m = src.match(/function formatElo\\(value\\) \\{[\\s\\S]*?\\n    \\}/);\n"
        "if (!m) { console.error('нет formatElo'); process.exit(2); }\n"
        "const f = new Function(m[0] + '; return formatElo;')();\n"
        "console.log(JSON.stringify([f(null), f(undefined), f(1537.4), f(0)]));\n",
        encoding="utf-8",
    )
    out = subprocess.run(["node", str(harness), str(SOCCER_JS)],
                         check=False, capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout) == ["—", "—", "1537.4", "0.0"]


# --- сквозная проверка на копии боевой базы ---

def test_page_profiles_equal_engine_on_real_db(db_path):
    """Каждый пуловый профиль страницы равен движку по пяти полям; вне пула рейтинга нет."""
    from db.rating_history import rating_history_from_db
    from portal import master_table
    from portal.build_soccer import compose_payload

    engine = {p["player"]: p for p in
              master_table.build_payload(rating_history_from_db(db_path))["power_rankings"]}
    profiles = compose_payload(db_path)["profiles"]
    assert engine, "в копии базы нет рейтингового пула"
    seen_pool = 0
    for p in profiles:
        name = p["player"]
        if name in engine:
            seen_pool += 1
            assert p["rated"] is True, name
            for field in RATING_FIELDS:
                assert p[field] == engine[name][field], (name, field)
        else:
            assert p["rated"] is False, name
            assert p["active_elo"] is None, name
            assert p["decay_penalty"] == 0.0, name
            if p["is_hall_of_fame"]:
                assert p["peak_elo"] == HOF_PEAK_ELO.get(name), name
            else:
                assert p["peak_elo"] is None, name
    assert seen_pool == len(engine)
