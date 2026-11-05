"""Общие помощники тестов правки: выборки строк свойством, а не id, и чтение среза базы.

Запросы здесь — не «данные теста», а способы найти в копии базы строку нужной формы: матч 1×1,
строку без счёта, строку страницы вместе с её рейтинговой копией. Фиксированные id не годятся:
их меняет каждая пересборка, и тест с номером строки протухал бы ровно тогда, когда он нужнее
всего.
"""

from db import edit

SCOREFUL = """select m.id from matches m
    join match_sides a on a.match_id = m.id and a.side_index = 0
    join match_sides b on b.match_id = m.id and b.side_index = 1
    where m.hidden_by is null and a.score is not null and b.score is not null
      and a.score > b.score limit 1"""

SCORELESS = """select m.id from matches m
    join match_sides a on a.match_id = m.id and a.side_index = 0
    join match_sides b on b.match_id = m.id and b.side_index = 1
    where m.hidden_by is null and a.score is null and b.score is null and m.note <> '' limit 1"""

# Строка страницы + её рейтинговая копия: правка обязана пройти по обеим.
WITH_PAIR = """select m.id from matches m
    join matches t on (t.duplicate_of = m.id or t.hidden_by = m.id)
    where m.hidden_by is null and m.row_set = 'catalog' and t.id <> m.id limit 1"""

# Матч ровно с одним игроком на каждой стороне: такие ники уже живут карточками, поэтому правка
# не заведёт нового игрока и откат сможет вернуть базу байт-в-байт.
SINGLES = """select m.id, pa.nick, pb.nick from matches m
    join match_sides a on a.match_id = m.id and a.side_index = 0
    join match_sides b on b.match_id = m.id and b.side_index = 1
    join side_players spa on spa.side_id = a.id join players pa on pa.id = spa.player_id
    join side_players spb on spb.side_id = b.id join players pb on pb.id = spb.player_id
    where m.hidden_by is null and {where}
      and (select count(*) from side_players where side_id = a.id) = 1
      and (select count(*) from side_players where side_id = b.id) = 1 limit 1"""

CARD_COLUMNS = ("manual", "in_rating_pool", "tour", "league", "played_on", "date_precision",
                "phase", "is_playoff", "source", "source_ref", "source_text", "source_place",
                "source_date_raw", "note", "status", "duplicate_of", "hidden_by")


def sides(con, match_id):
    return {row["side_index"]: row for row in edit.sides_of(con, match_id)}


def card(con, match_id):
    return con.execute(
        f"select {', '.join(CARD_COLUMNS)} from matches where id = ?", (match_id,)).fetchone()


def rosters(con, match_id):
    """Кто стоит на сторонах по карточкам — текстом, через « & »."""
    return {row["side_index"]: row["who"] or "" for row in con.execute(
        """select s.side_index, (select group_concat(p.nick, ' & ') from side_players sp
             join players p on p.id = sp.player_id where sp.side_id = s.id
            order by sp.seat_index) as who
           from match_sides s where s.match_id = ? order by s.side_index""", (match_id,))}


def links(con, match_id):
    return {(row[0], row[1]) for row in
            con.execute("select kind, url from match_links where match_id = ?", (match_id,))}
