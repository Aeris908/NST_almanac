"""Кубковая серия не обрезается на четырёх встречах: ноги до пяти побед — это до девяти строк.

Сезон 5, 1/4 Кубка: комментарий 14980 темы 36630593 перечисляет шесть ног
(5-8, 5-4, 6-4, 6-3, 4-3, 4-4 (3-1)). Прежний разборщик пропускал строку, когда у пары в сезоне
уже набралось четыре встречи, и две последние ноги терялись — в каталоге их не было вовсе.
Сводка серии (4:2) при этом лежала и в справочнике, и в рейтинговом пуле, так что потеря
оставалась невидимой: встреча выглядела сыгранной, а двух её ног не существовало.
"""

from portal.match_catalog import append_vk_playoff_comments

COMMENT = (
    "Кубок. 1/4 финала\n"
    "ectoPower vs RVD - 5-8\n"
    "RVD vs ectoPower - 5-4\n"
    "ectoPower vs RVD - 6-4\n"
    "RVD vs ectoPower - 6-3\n"
    "ectoPower vs RVD - 4-3\n"
    "RVD vs ectoPower - 4-4 (3-1)"
)
LEGS = [("ectoPower", "RVD (МГБ)", 5, 8), ("RVD (МГБ)", "ectoPower", 5, 4),
        ("ectoPower", "RVD (МГБ)", 6, 4), ("RVD (МГБ)", "ectoPower", 6, 3),
        ("ectoPower", "RVD (МГБ)", 4, 3), ("RVD (МГБ)", "ectoPower", 4, 4)]


def carrier():
    return [{"season": "Season 5", "stage": "Регулярный чемпионат", "p1": a, "p2": b,
             "s1": s1, "s2": s2, "ot": False, "pk": False, "vk_text": COMMENT}
            for a, b, s1, s2 in LEGS]


def test_все_шесть_ног_серии_доходят_до_каталога():
    combined = []
    append_vk_playoff_comments(carrier(), combined, {})
    assert [(m["p1"], m["p2"], m["s1"], m["s2"]) for m in combined] == LEGS


def test_раунд_и_лига_взяты_у_комментария_а_не_у_пометки_носителя():
    combined = []
    append_vk_playoff_comments(carrier(), combined, {})
    assert all(m["league"] == "Кубок лиг" and m["tour"] == "1/4 финала" for m in combined)


def test_повторный_прогон_не_удваивает_ноги():
    combined = []
    append_vk_playoff_comments(carrier(), combined, {})
    append_vk_playoff_comments(carrier(), combined, {})
    assert len(combined) == 6


def test_девятая_нога_серии_до_пяти_побед_тоже_доходит():
    """Финал Кубка Сезона 6 игрался до пяти побед и растянулся на девять ног."""
    final = [("ectoPower", "Transistor", 6, 5), ("Transistor", "ectoPower", 4, 1),
             ("ectoPower", "Transistor", 7, 6), ("Transistor", "ectoPower", 5, 4),
             ("Transistor", "ectoPower", 5, 4), ("ectoPower", "Transistor", 5, 3),
             ("Transistor", "ectoPower", 4, 2), ("ectoPower", "Transistor", 7, 4),
             ("ectoPower", "Transistor", 8, 1)]
    text = "Кубок лиг. Финал\n" + "\n".join(f"{a} vs {b} - {s1}-{s2}" for a, b, s1, s2 in final)
    rows = [{"season": "Season 6", "stage": "Плей-офф", "p1": a, "p2": b, "s1": s1, "s2": s2,
             "ot": False, "pk": False, "vk_text": text} for a, b, s1, s2 in final]
    combined = []
    append_vk_playoff_comments(rows, combined, {})
    # Ноги 4 и 5 — один и тот же счёт 5:4 в одну сторону: различить их нечем, и повтор
    # отбрасывается как уже известный. Остальные восемь обязаны дойти.
    assert len(combined) == 8
    assert (combined[0]["s1"], combined[0]["s2"]) == (6, 5)
    assert (combined[-1]["s1"], combined[-1]["s2"]) == (8, 1)

def test_нога_с_серией_после_ничьей_получает_признак_буллитов():
    """Источник: «RVD vs ectoPower - 4-4 (3-1)». Носитель помечает pk=false, скобки называет серия."""
    combined = []
    append_vk_playoff_comments(carrier(), combined, {})
    last = combined[-1]
    assert (last["s1"], last["s2"]) == (4, 4)
    assert last["pk"] is True
    assert not any(m["pk"] for m in combined[:-1]), "буллиты приписаны ногам, где их не было"


def test_скобки_после_неравного_счёта_буллитами_не_становятся():
    from portal.comment_origin import shootout_of

    assert shootout_of("Кубок. 1/4 финала\nRVD vs ectoPower - 4-4 (3-1)", 4, 4) == (3, 1)
    assert shootout_of("ruby - rodger 1:1 (4:3 PK)", 1, 1) == (4, 3)
    assert shootout_of("Vasya1995 - ruby 0:0 (1:5 PEN)", 0, 0) == (1, 5)
    assert shootout_of("ectoPower vs RVD - 5-8 (перенос)", 5, 8) is None
    assert shootout_of("RVD vs ectoPower - 4-4", 4, 4) is None
    assert shootout_of(None, 4, 4) is None
