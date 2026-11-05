"""Доказанные зеркальные дубли раннего архива: одна игра, записанная в обе стороны.

Сезон 1 пришёл из Google-таблицы матрицей «строка × столбец», и при переносе каждая встреча
получилась двумя строками: [#403 `Memori 4:0 Ric25`] и [#412 `Ric25 0:4 Memori`]. Счёт второй
строки — не вторая нога, а зеркало первой: стороны поменялись местами, числа перевернулись.
Владелец решил так: «матчи с очевидно дублирующим счётом — исключаем», основу берём из таблиц.

Механика — `hidden_by` на вторую строку: витрина её больше не печатает, но строка остаётся в
базе со своим источником и датой, и снять решение можно одним движением. `duplicate_of` тут не
подходит: он ничего не прячет, а рейтинг от этих строк и так не зависит (Сезон 1 не в пуле).

Признак доказуемый и узкий: тот же турнир, тот же тур, те же два игрока, счёт ровно зеркальный,
и таких строк в туре ровно две. Всё остальное — например настоящая серия из двух одинаковых
ног — остаётся нетронутым и попадает в отчёт.

Срез намеренно ограничен `early_archive`: правило работает только для переноса матрицы
«строка × столбец». В Сезонах 8–9 две встречи одной пары в одном туре — обычный двойной круг,
и зеркальный счёт там значит «ноги кончились одинаково», а не «строка продублирована»;
прятать такую игру означало бы удалить историю.
"""

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.names import clean_alias  # noqa: E402
from db import store  # noqa: E402

DB_PATH = store.DB_PATH

SIDES_SQL = """
select m.id, m.tournament_id, coalesce(m.tour, s.name) as tour,
       coalesce(sa.label, (select p.nick from side_players sp join players p on p.id = sp.player_id
                            where sp.side_id = sa.id limit 1)) as a,
       coalesce(sb.label, (select p.nick from side_players sp join players p on p.id = sp.player_id
                            where sp.side_id = sb.id limit 1)) as b,
       sa.score as s1, sb.score as s2
from matches m
join stages s on s.id = m.stage_id
join match_sides sa on sa.match_id = m.id and sa.side_index = 0
join match_sides sb on sb.match_id = m.id and sb.side_index = 1
where m.row_set = 'catalog' and m.source = 'early_archive'
  and m.hidden_by is null and m.status <> 'void' and m.in_rating_pool = 0
  and (select count(*) from side_players sp where sp.side_id = sa.id) = 1
  and (select count(*) from side_players sp where sp.side_id = sb.id) = 1
"""


def side(name):
    return (clean_alias(name) or name or "").strip().lower()


def key_of(row):
    """Пара без ориентации внутри одного тура одного турнира."""
    return (row["tournament_id"], (row["tour"] or "").strip().lower(),
            tuple(sorted([side(row["a"]), side(row["b"])])))


def is_mirror(first, second):
    return first["s1"] == second["s2"] and first["s2"] == second["s1"] and side(first["a"]) != side(first["b"])


def main(db_path=DB_PATH):
    sys.stdout.reconfigure(encoding="utf-8")
    con = store.connect(db_path)
    con.row_factory = sqlite3.Row
    groups = defaultdict(list)
    for row in con.execute(SIDES_SQL):
        groups[key_of(row)].append(dict(row))

    hidden, suspicious = 0, []
    for key, rows in sorted(groups.items(), key=lambda kv: min(r["id"] for r in kv[1])):
        if len(rows) == 2 and is_mirror(*rows):
            first, second = sorted(rows, key=lambda r: r["id"])
            con.execute("update matches set hidden_by = ? where id = ?", (first["id"], second["id"]))
            hidden += 1
        elif len(rows) > 2:
            suspicious.append((key[0], key[1], len(rows)))

    con.commit()
    seasons = {row["tournament_id"] for row in con.execute("select distinct tournament_id from matches where hidden_by is not null and row_set='catalog'")}
    print(f"\nзеркальных дублей скрыто: {hidden} (турниров затронуто: {len(seasons)})")
    if suspicious:
        print(f"групп с >2 строк (не трогали, смотреть глазами): {len(suspicious)}")
        for tournament, tour, count in suspicious[:8]:
            print(f"   турнир {tournament} · тур {tour!r} · строк {count}")
    return hidden


if __name__ == "__main__":
    main()
