"""Лига и тур строки-комментария: распознавание и его отказ угадывать.

Строки носителя `all_vk_seasons_matches.json` приходили без поля `league`, и сборка ставила их
все в «Высшую лигу» с туром «Плей-офф / Кубок». Из-за этого фильтра псевдо-кубковых строк
игры не было на странице сезона — она жила только в историях игроков. Проверено на реальных
текстах комментариев Сезонов 2–7.
"""

from portal.comment_origin import from_carrier_stage, from_comment, origin_of

TOP_TOUR = "Высшая лига. 3 тур\nectoPower vs BOP213 - 4:4 (7-6 пенальти)\nBOP213 vs ectoPower - 0-5"


def test_league_and_tour_come_from_the_comment():
    assert from_comment("2 Тур. Средняя лига. Италия\nDune vs Wenderfit 6 - 6 PK 5:4", 6, 6) == \
        ("Средняя лига", "2 Тур")
    assert from_comment("Дворовая лига, 4 тур\nChocopie Vs Aeris 4:1", 4, 1) == ("Дворовая лига", "4 Тур")
    assert from_comment("Вышка. 6 тур.\nectoPower vs mafuta 4:4 (PK 7:8)", 4, 4) == ("Высшая лига", "6 Тур")
    assert from_comment("вл.9тур.\nectoPower vs Huba: 1-1", 1, 1) == ("Высшая лига", "9 Тур")


def test_frame_is_inherited_by_the_lines_below():
    """Рамка названа один раз над списком ног — счёта на строке рамки нет, и это не мешает."""
    assert from_comment(TOP_TOUR, 4, 4) == ("Высшая лига", "3 Тур")
    assert from_comment(TOP_TOUR, 0, 5) == ("Высшая лига", "3 Тур")


def test_cup_stage_is_not_a_league_round():
    for text, scores, stage in (
        ("Кубок Лиг, 1/8 финала.\nDr1N vs Dopi 3-1", (3, 1), "1/8 финала"),
        ("1/4 finals\nRomix vs Memori - 0:4", (0, 4), "1/4 финала"),
        ("1/2 mafuta vs Memori 4:0", (4, 0), "1/2 финала"),
        ("Финал Кубка. mafuta vs Kunio 5:2", (5, 2), "Финал"),
    ):
        assert from_comment(text, *scores) == ("Кубок лиг", stage), text


def test_comment_about_another_score_is_not_evidence():
    """Пара сыграла в комментарии другие ноги: чужую рамку на эту строку вешать нельзя.

    Так случается, когда архивный указатель приводит к обсуждению по паре без счёта: текст
    настоящий, а игра в нём — другая.
    """
    assert from_comment(TOP_TOUR, 3, 2) is None
    assert from_comment("Вышка. 4 тур\nizzzotope vs mafuta 8:7", 4, 0) is None


def test_tour_without_league_stays_unproven():
    """«7 тур» без дивизиона — это не доказательство лиги: в сезоне их три, и выбор был бы догадкой."""
    assert from_comment("7 тур\nHuba Buba - mafuta 4:4 (PK 6:7)", 4, 4) is None


def test_two_frames_for_the_same_score_stay_unproven():
    text = "Высшая лига. 2 тур\nA vs B 1:0\nСредняя лига. 2 тур\nA vs B 1:0"
    assert from_comment(text, 1, 0) is None


def test_carrier_stage_marks_division_and_playoff():
    assert from_carrier_stage("Средняя лига") == ("Средняя лига", "Регулярный сезон")
    assert from_carrier_stage("Плей-офф") == ("Кубок лиг", "Плей-офф")
    assert from_carrier_stage("Регулярный чемпионат") is None
    assert from_carrier_stage(None) is None


def test_comment_beats_the_carrier_mark():
    """Коллекционер подписал строку «Плей-офф», а комментарий называет регулярку: верим тексту."""
    assert origin_of("Плей-офф", "Высшая лига. 8 тур\nKunio vs izzzotope 1:6", 1, 6) == ("Высшая лига", "8 Тур")
    assert origin_of("Плей-офф", "", 1, 6) == ("Кубок лиг", "Плей-офф")
