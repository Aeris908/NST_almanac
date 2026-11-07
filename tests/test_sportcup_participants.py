"""#80: восемь партий CentZloy переприписаны с замены E_not по теме 52002075.

Сезон 8, Средняя лига: CentZloy (id85380069) сыграл четыре тура и снялся, а его слот в снапшоте
Sportcup переименовали в замену — E_not. Владелец решил верить ВКонтакте: комментарий 31124
называет замену прямо, комментарии 31175, 31180, 31232 и 31235 дают счета всех восьми партий.
Решение лежит в `data/sportcup_decisions.json` (ключ `participant_override`) и применяется
в `build_final_analytics.fetch_sportcup_matches` только к названной стороне.

Две партии тема называет сериями буллитов («1-1(4-3 пен)» и «5:4 (пен)»), а не овертаймами:
счёт строки остаётся счётом серии (конвенция `tiebreak_penalties`), правда об основном времени
ложится в пометку. Партия «3:1 (OT)» овертайм сохраняет — источник назвал его прямо.

Все проверки офлайновые: сборочные модули импортируются с подменённым секретом, пул читается
из замороженного снапшота, сборка базы идёт только на временной копии. Строки ищутся по uuid
и свойствам, фиксированных id базы в тестах нет.
"""

import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "data" / "sportcup_decisions.json"
SNAPSHOT = ROOT / "data" / "sportcup_games.json"
MIDDLE_LEAGUE_8 = {"season": "Season 8", "league": "Средняя",
                   "uuid": "5500f1f3-db8b-400e-9838-1f90981db281"}

# Восемь партий: uuid -> (сторона E_not в снапшоте, соперник, счёт первой стороны, счёт второй).
# Счета и стороны сверены со снапшотом и комментариями темы 52002075 (пробник scratch/s80_sources.py).
GAMES = {
    "f1f6e481-7510-4952-89d2-78128354dd09": (1, "Aeris", 3, 1),     # комментарий 31175, овертайм
    "7efdd81b-eaeb-496e-bf16-36128b3c10be": (2, "Aeris", 3, 0),     # комментарий 31175, вторая нога
    "19aaced0-1808-422a-806e-bad08f38ebab": (2, "Jamlight", 2, 3),  # комментарий 31180
    "c7b829f1-3209-4c8e-907e-0cf2829f2f67": (1, "Jamlight", 4, 3),  # комментарий 31180, буллиты
    "f01cd1d1-f047-4551-8375-add1832a15e3": (2, "Rash", 6, 3),     # комментарий 31235
    "63cb16d3-2c3c-4afb-8c64-3d0b1ea25f8b": (1, "Rash", 1, 2),     # комментарий 31235
    "dc4e0391-f806-404a-bf3f-45d52e17b5c0": (1, "Буц", 0, 4),      # комментарий 31232
    "2ba3bc6d-f1a5-40a2-b1a2-80b3c8cce47d": (2, "Буц", 5, 4),      # комментарий 31232, буллиты
}
SHOOTOUTS = {
    "c7b829f1-3209-4c8e-907e-0cf2829f2f67": ("1:1 в основное время, 4:3 по буллитам", "31180"),
    "2ba3bc6d-f1a5-40a2-b1a2-80b3c8cce47d": ("5:4 по буллитам", "31232"),
}
OVERTIME_KEPT = "f1f6e481-7510-4952-89d2-78128354dd09"


@pytest.fixture(scope="module")
def engine():
    """Сборочные модули офлайн: секрет подменён пустым, соединение с ВК не проверяется.

    `build_final_analytics` при импорте проверяет соединение с ВК и читает пул; без подмены
    секрета тест ушёл бы в сеть. Все шесть стейджей есть в снапшоте, поэтому чтение пула
    сетевого не делает. Подмена живёт ровно до конца модуля и не переживает его.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("portal.env_file.secret", lambda name, path=None: "")
        patch.delitem(sys.modules, "build_final_analytics", raising=False)
        patch.delitem(sys.modules, "db.build_db", raising=False)
        bfa = importlib.import_module("build_final_analytics")
        builder = importlib.import_module("db.build_db")
        yield bfa, builder


def middle_league_rows(bfa):
    """Строки пула Средней лиги Сезона 8, ключ — uuid снапшота."""
    return {row["source_ref"]: row for row in bfa.fetch_sportcup_matches([MIDDLE_LEAGUE_8])}


def test_decisions_reassign_exactly_the_eight_games():
    """Носитель решений переприписывает ровно восемь партий и только сторону замены."""
    raw = json.loads(DECISIONS.read_text(encoding="utf-8"))
    entries = raw.get("participant_override", [])
    assert len(entries) == 8, "переприписано не восемь партий"
    assert {entry["uuid"] for entry in entries} == set(GAMES)
    for entry in entries:
        side = GAMES[entry["uuid"]][0]
        assert entry["side"] == side, f"{entry['uuid']}: переприписана не та сторона"
        assert entry["player"] == "CentZloy", "имя в решении — как в источнике"
        assert entry.get("match"), "нет человекочитаемой подписи"
        assert "52002075" in entry.get("reason", ""), "обоснование без ссылки на тему"


def test_override_targets_the_renamed_slot():
    """Каждая запись ссылается на существующую игру, и указанная сторона — именно слот E_not."""
    blob = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    games = {game["uuid"]: game for stage in blob["stages"]
             for game in stage["response"].get("list", [])}
    raw = json.loads(DECISIONS.read_text(encoding="utf-8"))
    for entry in raw.get("participant_override", []):
        game = games[entry["uuid"]]
        assert game.get("resultStatus") == "FINAL"
        mine = game["member1"] if entry["side"] == 1 else game["member2"]
        other = game["member2"] if entry["side"] == 1 else game["member1"]
        assert mine["title"] == "E_not", f"{entry['uuid']}: сторона не слот замены"
        assert other["title"] != "E_not", f"{entry['uuid']}: обе стороны — замена?"


def test_loader_reads_participant_override(engine):
    """Загрузчик решений отдаёт переприписывание как uuid -> {сторона: игрок}."""
    bfa, _ = engine
    decisions = bfa.load_sportcup_decisions()
    assert decisions.participants == {
        uuid: {side: "CentZloy"} for uuid, (side, _, _, _) in GAMES.items()
    }


@pytest.mark.parametrize("side", [0, 3, None, "1"])
def test_loader_rejects_a_bad_side(engine, tmp_path, monkeypatch, side):
    """Сторона обязательна и равна 1 или 2: иначе правка молча легла бы не туда."""
    bfa, _ = engine
    entry = {"uuid": "f1f6e481-7510-4952-89d2-78128354dd09", "player": "CentZloy"}
    if side is not None:
        entry["side"] = side
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps({"participant_override": [entry]}, ensure_ascii=False),
                    encoding="utf-8")
    monkeypatch.setattr(bfa, "DECISIONS_PATH", path)
    with pytest.raises(ValueError, match="сторона"):
        bfa.load_sportcup_decisions()


def test_decisions_without_overrides_load_empty(engine, tmp_path, monkeypatch):
    """Носитель без ключа `participant_override` читается как раньше: переприписываний нет."""
    bfa, _ = engine
    path = tmp_path / "decisions.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bfa, "DECISIONS_PATH", path)
    assert bfa.load_sportcup_decisions().participants == {}


def test_pool_rows_belong_to_centurion_on_the_overridden_side(engine):
    """Пул несёт Centurion на переприписанной стороне; счёт и соперник не тронуты.

    Имя решения сворачивается тем же `norm`, что и имя снапшота: «CentZloy» -> «Centurion»,
    поэтому строка сразу ложится на канонического игрока.
    """
    bfa, _ = engine
    rows = middle_league_rows(bfa)
    for uuid, (side, opponent, s1, s2) in GAMES.items():
        row = rows[uuid]
        assert (row["s1"], row["s2"]) == (s1, s2), f"{uuid}: счёт изменён"
        if side == 1:
            assert row["p1"] == "Centurion", f"{uuid}: первая сторона не Centurion"
            assert row["p2"] == bfa.norm(opponent), f"{uuid}: соперник изменён"
        else:
            assert row["p2"] == "Centurion", f"{uuid}: вторая сторона не Centurion"
            assert row["p1"] == bfa.norm(opponent), f"{uuid}: соперник изменён"


def test_replacement_own_games_stay(engine):
    """Собственные партии E_not (туры 5-9 и 14-18) остаются за замену: решение точечное."""
    bfa, _ = engine
    rows = middle_league_rows(bfa)
    own = [row for row in rows.values() if "E_not" in (row["p1"], row["p2"])]
    assert len(own) == 8, "у замены должно остаться восемь собственных партий лиги"
    assert not any(row["source_ref"] in GAMES for row in own)


def test_overtime_stays_and_shootouts_become_penalties(engine):
    """«3:1 (OT)» остаётся овертаймом; две серии становятся буллитами с пометкой источника.

    Счёт строки остаётся счётом серии (4:3 и 5:4): конвенция репозитория хранит серию счётом,
    а правду об основном времени — пометкой. Менять счёт на 1:1 значило бы выбросить победу.
    """
    bfa, _ = engine
    rows = middle_league_rows(bfa)
    kept = rows[OVERTIME_KEPT]
    assert kept["ot"] is True and kept["pk"] is False
    for uuid, (note_part, comment) in SHOOTOUTS.items():
        row = rows[uuid]
        assert row["ot"] is False and row["pk"] is True, f"{uuid}: серия легла овертаймом"
        assert note_part in row["note"], f"{uuid}: пометка без правды об основном времени"
        assert comment in row["note"] and "52002075" in row["note"]
    for uuid in set(GAMES) - set(SHOOTOUTS) - {OVERTIME_KEPT}:
        row = rows[uuid]
        assert row["ot"] is False and row["pk"] is False, f"{uuid}: доигровка выдумана"


def test_fresh_build_lands_on_centurion_card(engine, tmp_path):
    """Свежая сборка кладёт восемь партий на карточку Centurion, E_not остаётся с 12 партиями.

    Это путь `--rebuild`: строка пула вставляется один раз, поэтому переприписывание доходит
    до базы только пересозданием среза. Сборка идёт на временном файле, живая база не тронута.
    """
    bfa, builder = engine
    con = builder.open_db(tmp_path / "fresh.db", rebuild=True)
    try:
        # Тот же шаг, что в db/build_db.py: main(): турниры ссылаются на дисциплину.
        con.execute("insert or ignore into disciplines(id, slug, name) values (1, 'soccer', 'Футбол Goal 3')")
        builder.import_pool(con, bfa.all_matches)
        builder.import_aliases(con)
        con.commit()
        for uuid, (side, _, _, _) in GAMES.items():
            nick = con.execute(
                "select p.nick from matches m"
                " join match_sides ms on ms.match_id = m.id and ms.side_index = ?"
                " join side_players sp on sp.side_id = ms.id"
                " join players p on p.id = sp.player_id"
                " where m.source = 'sportcup_api' and m.source_ref = ?",
                (side - 1, uuid)).fetchone()
            assert nick is not None and nick[0] == "Centurion", f"{uuid}: сторона не Centurion"
            phase = con.execute(
                "select phase from matches where source = 'sportcup_api' and source_ref = ?",
                (uuid,)).fetchone()[0]
            want = "penalties" if uuid in SHOOTOUTS else (
                "overtime" if uuid == OVERTIME_KEPT else "regular")
            assert phase == want, f"{uuid}: фаза {phase} вместо {want}"
        enot = con.execute(
            "select count(*) from v_rating_pool where p1 = 'E_not' or p2 = 'E_not'").fetchone()[0]
        cent = con.execute(
            "select count(*) from v_rating_pool where p1 = 'Centurion' or p2 = 'Centurion'"
        ).fetchone()[0]
        assert enot == 12, f"у E_not {enot} партий вместо 12"
        assert cent == 8, f"у Centurion {cent} партий вместо 8"
    finally:
        con.close()