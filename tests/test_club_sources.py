"""Клубный Goal 4 (межсезонье 2019): протокол обоих эшелонов не теряет игры и не врёт лигой.

Прежний носитель нёс 50 строк «Баттл #N (Круг 1)», все подписанные «Молодёжной лигой», хотя
24 из них — игры Премьер-лиги, а список обрывался на Туре 4 из 10. Источник — Google-таблица,
на которую ссылается шапка темы 39731903: лист «Матчи» (200 строк = 40 баттлов по 5 игр),
листы эшелонов и «Статистика». Таблицы сходятся с протоколом до цифры, причём мячи в них
посчитаны ВМЕСТЕ с буллитами — это конвенция источника, а не наша выдумка.

Листы лежат в `data/gsheet_club_goal4/`, поэтому тестам не нужна сеть.
"""

import re
from collections import Counter

from portal.club_sources import SHEET_DIR, TOURNAMENT, club_games

PREMIER = "Премьер-лига"
YOUTH = "Молодёжная лига"


def parsed():
    return club_games(SHEET_DIR)


def played(rows):
    return [r for r in rows if r["score"][0] is not None]


def test_протокол_сходится_с_таблицами_обоих_эшелонов():
    rows, report = parsed()
    assert report["unreconciled"] == []
    leagues = {item["лига"]: item for item in report["leagues"]}
    assert leagues[PREMIER]["по_протоколу"] == leagues[PREMIER]["по_таблице"]
    assert leagues[YOUTH]["по_протоколу"] == leagues[YOUTH]["по_таблице"]
    assert leagues[PREMIER]["по_таблице"] == {"баттлов": 20, "игр": 68, "мячей": 511}
    assert leagues[YOUTH]["по_таблице"] == {"баттлов": 17, "игр": 58, "мячей": 380}


def test_каждая_сыгранная_игра_протокола_становится_строкой():
    rows, report = parsed()
    assert len(played(rows)) == 126
    assert len(rows) == 129
    assert report["totals"]["строк в базу"] == 129


def test_лига_берётся_из_колонки_источника_а_не_подставляется():
    rows, _ = parsed()
    assert Counter(r["league"] for r in played(rows)) == {PREMIER: 68, YOUTH: 58}


def test_тур_назван_источником_а_не_номером_игры():
    rows, _ = parsed()
    assert all(re.fullmatch(r"Тур \d+", r["tour"]) for r in rows)
    assert Counter(r["tour"] for r in played(rows))["Тур 1"] == 15


def test_несыгранные_баттлы_это_ТП_обеим_сторонам():
    rows, report = parsed()
    tp = [r for r in rows if r.get("tp")]
    assert len(tp) == 3
    assert report["totals"]["не сыграно (ТП обоим)"] == 3
    for row in tp:
        assert row["score"] == [None, None]
        assert row["outcome"] == ["none", "none"]
        assert row["counted"] is False
        assert row["league"] == YOUTH
        assert row["score_text"].startswith("ТП обоим:")


def test_мячи_считаются_как_в_таблице_источника_вместе_с_буллитами():
    rows, report = parsed()
    goals = sum(sum(r["score"]) for r in played(rows))
    assert goals == 891
    assert report["totals"]["мячей всего"] == 891
    shootouts = [r for r in played(rows) if r["phase"] == "penalties"]
    assert len(shootouts) == 10
    assert sum(sum(r["series"]) for r in shootouts) == 38
    for row in shootouts:
        assert row["score"][0] != row["score"][1]
        assert row["series"][0] != row["series"][1]


def test_одинаковые_игры_одной_пары_не_сливаются_в_одну():
    """В протоколе одна и та же пара регулярно выдаёт одинаковый счёт дважды: игры №16 и №18 и др.

    Ключ дублей импортёра — адрес + тур + пара + счёт, причём имя связано со своим счётом
    (ориентация не важна), а лиги в ключе нет. По суммарным мячам, которые и заносим, таких
    повторов 35; все они внутри одного эшелона, поэтому лига в ключе число не меняет.
    У каждой строки свой `source_ref`, а текст источника не перечисляет счёт — поэтому ни одна
    из 35 не прячется. Без этой защиты 35 игр из 126 молча ушли бы в скрытые.
    """
    rows, _ = parsed()
    refs = [r["source_ref"] for r in rows]
    assert len(set(refs)) == len(refs)
    games = played(rows)

    def signature(row):
        """Подпись импортёра: имя связано со своим счётом, ориентация стороны не важна."""
        return frozenset([(row["team_a"][0], row["score"][0]), (row["team_b"][0], row["score"][1])])

    without_league = Counter((r["tour"], signature(r)) for r in games)
    with_league = Counter((r["tour"], r["league"], signature(r)) for r in games)
    assert sum(count - 1 for count in without_league.values() if count > 1) == 35
    assert sum(count - 1 for count in with_league.values() if count > 1) == 35


def test_текст_источника_не_перечисляет_счёт_иначе_импортёр_спрячет_повтор():
    """`expected_games` прячет строку, если `source_text` упоминает её счёт меньше раз, чем строк.

    Адрес у всех строк один (тема турнира), поэтому текст источника обязан описывать строку
    листа, а не дублировать счёт в форме «8:4» — иначе повтор той же игры уйдёт в скрытые.
    """
    rows, _ = parsed()
    assert rows
    for row in played(rows):
        s1, s2 = row["score"]
        pattern = re.compile(rf"(?<!\d){s1}\s*[:\-–]\s*{s2}(?!\d)|(?<!\d){s2}\s*[:\-–]\s*{s1}(?!\d)")
        assert not pattern.search(row["source_text"]), row["source_ref"]


def test_строки_несут_турнир_рамки_и_провенанс():
    rows, _ = parsed()
    assert rows
    for row in rows:
        assert row["tournament"] == TOURNAMENT
        assert row["kind"] == "special" and row["row_set"] == "special"
        assert row["source_page"] == "topic-39731903"
        assert row["page_url"].startswith("https://vk.com/topic-66162180_39731903")
        assert row["source_text"]
        assert row["links"] == []
