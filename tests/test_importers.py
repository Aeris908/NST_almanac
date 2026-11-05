"""Импортёры не плодят контейнеры: у документа одна турнирная рамка.

Живые календари командных чемпионатов приехали в базу позже её же игр из темы обсуждения, и
сезона у строки носителя нет. Пока импортёр подставлял «—», `ensure_tournament` заводил второй
«VI Командный Чемпионат по Goal 3»: игры календаря и игры обсуждения одного турнира лежали в
разных контейнерах, а фасет по сезону в панели показывал половину чемпионата отдельно.

Проверка идёт по свойствам собранной базы, а не по номерам строк: их пересоздаёт каждая сборка.
"""

DOCS_ONE_TOURNAMENT = """
select doc_id from matches
where doc_id is not null and tournament_id is not null
group by doc_id having count(distinct tournament_id) > 1
"""

LIVE_ROWS_OUTSIDE_DOC_SEASON = """
select m.id from matches m
join tournament_docs d on d.id = m.doc_id
join tournaments t on t.id = m.tournament_id
where m.source = 'vk_live' and m.row_set = 'team'
  and json_extract(d.payload, '$.season_year') is not null
  and t.season <> json_extract(d.payload, '$.season_year')
"""


def test_every_document_keeps_its_games_in_one_tournament(con):
    """Один документ — один турнир-контейнер: рамка читает сезон и этап именно у него."""
    split = [row[0] for row in con.execute(DOCS_ONE_TOURNAMENT)]
    assert not split, f"документы с двумя контейнерами: {split}"


def test_live_calendar_rows_sit_in_the_season_of_their_document(con):
    """Сезон строки календаря — тот, что записан в рамке турнира, иначе строка уедет в чужой фасет."""
    lost = [row[0] for row in con.execute(LIVE_ROWS_OUTSIDE_DOC_SEASON)]
    assert not lost, f"игр календаря вне сезона своего документа: {len(lost)}"
