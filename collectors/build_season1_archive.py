"""Сезон 1: регулярный чемпионат целиком — из матрицы, с туром из календаря.

Сезон 1 играется в четыре игры на пару: две встречи, каждая по две игры. Основой архива всегда
была турнирная матрица (`data/gsheet_season1/31265171.csv` — КОМЕТЫ, `1579784569.csv` — МЕТЕОРЫ),
но в неё заносили по одной-две ноги на пару, и архив досчитывал 157 игр из 332.

Здесь носитель собирается по листам целиком, и каждый шаг проверяется по самим же листам:

* нога берётся из матрицы, где скобка значит «гостевая», а «13т» — что игра перенесена и её не было;
* тот же счёт ищет в календаре (`573947369.csv`) — если календарь молчит или называет другой счёт,
  генератор падает, а не додумывает: два листа уже сверены между собой, расхождение значит дефект;
* тур и дата приходят из календаря, а не выдумываются как «3 Круг»;
* из итоговой таблицы матрицы пересчитываются И, В, Н, П, Мз, Мп и О — разбор считается доказанным,
  только если все семь колонок сходятся у каждого из двадцати игроков;
* `data/season1_topic_notes.json` (снимок живой темы) добавляет в `note_leg` спорные случаи: тема
  называет другой тур или другой счёт — это остаётся человеку, а не генератору.

Запуск:

    python collectors/build_season1_archive.py --check   # сверить носитель с листами
    python collectors/build_season1_archive.py           # перезаписать строки Сезона 1
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.names import clean_alias  # noqa: E402

SNAPSHOT = ROOT / "data" / "gsheet_season1"
CARRIER = ROOT / "early_seasons_matches.json"
NOTES = ROOT / "data" / "season1_topic_notes.json"
DIVISIONS = ("Кометы", "Метеоры")
MATRIX = {"Кометы": "31265171", "Метеоры": "1579784569"}
TOURNAMENT = "Season 1 Регулярный чемпионат"
STAGE = "Круговой этап"
SCORE = re.compile(r"^\s*(\d{1,2})\s*[:\-]\s*(\d{1,2})\s*$")
PAREN = re.compile(r"^\s*\(\s*(\d{1,2})\s*[:\-]\s*(\d{1,2})\s*\)\s*$")
TOURMARK = re.compile(r"^\s*\(?\s*(\d{1,2})\s*[тT]\s*\)?\s*$")
HEADERS = {"м", "команда", "о", "оп", "и", "в", "н", "п", "мз", "мп", "мр", "мср", "№".lower()}


def token(name):
    return clean_alias(name or "").lower()


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def matrix_legs(division):
    """{(игра, хозяин, гость): (голы хозяина, голы гостя)} и итоговая таблица того же листа.

    Игрок занимает два физических ряда и две колонки на соперника, поэтому на пару приходится до
    четырёх ног. Ориентацию задаёт не порядок колонок, а скобка: без неё играет хозяин строки.
    """
    table = read(SNAPSHOT / f"{MATRIX[division]}.csv")
    columns = []
    for index, cell in enumerate(table[0]):
        nick = clean_alias(cell.strip())
        if not nick or (not columns and nick.lower() in HEADERS):
            continue
        if nick.lower() in HEADERS or not re.search(r"[a-zA-Zа-яА-Я]", nick):
            break
        columns.append((nick, index, index + 1))
    blocks, owner = {}, None
    for row in table[1:]:
        if len(row) < 3:
            continue
        named = clean_alias(row[1].strip()) if row[1].strip() else ""
        if named:
            owner = named
            blocks[owner] = [row]
        elif owner and len(blocks[owner]) < 2:
            blocks[owner].append(row)
    legs = {}
    for owner, rows in blocks.items():
        for game, row in enumerate(rows[:2], start=1):
            for other, first, second in columns:
                if token(other) == token(owner):
                    continue
                for cell in (row[first] if first < len(row) else "",
                             row[second] if second < len(row) else ""):
                    text = cell.strip()
                    hit = SCORE.match(text)
                    if hit:
                        legs[(game, owner, other)] = (int(hit.group(1)), int(hit.group(2)))
                        continue
                    hit = PAREN.match(text)
                    if hit:
                        legs[(game, other, owner)] = (int(hit.group(2)), int(hit.group(1)))
    standings = {}
    for row in table[1:]:
        if len(row) < 12 or not row[1].strip():
            continue
        numbers = [row[i].strip() for i in (4, 5, 6, 7, 8, 9, 2)]
        if all(v.isdigit() for v in numbers):
            standings[clean_alias(row[1].strip())] = tuple(int(v) for v in numbers)
    return legs, standings


def calendar_legs():
    """{(хозяин, гость): [(игра, тур, дата, голы хозяина, голы гостя), ...]}

    Ключи — написания ниже регистра: два листа называют игроков одними и теми же словами, но
    строчную/заглавную букву и дефисы печатают по-своему («yoxter» против «Yoxter»).

    Первая игра встречи лежит в тройке колонок `Счет1` (голы, «:», голы), вторая — в служебной
    колонке `С2`, где счёт уже приведён к порядку «хозяин строки первым». Сырая `Счет2` переворачивает
    вторую игру и потому с матрицей не сходится.
    """
    table = read(SNAPSHOT / "573947369.csv")
    col = {name: index for index, name in enumerate(table[0]) if name.strip()}
    out = defaultdict(list)
    for row in table[1:]:
        if len(row) <= col["Гость"]:
            continue
        host, guest = clean_alias(row[col["Хозяин"]]), clean_alias(row[col["Гость"]])
        if not host or not guest:
            continue
        tour, date = row[col["Тур"]].strip(), row[col["Дата"]].strip()
        first = row[col["Счет1"]:col["Счет1"] + 3]
        cells = [(1, f"{first[0]}:{first[2]}" if len(first) > 2 else ""),
                 (2, row[col["С2"]])]
        for game, text in cells:
            hit = SCORE.match(text.strip())
            if hit:
                out[(token(host), token(guest))].append(
                    (game, tour, date, int(hit.group(1)), int(hit.group(2))))
    return dict(out)


def check_standings(division, legs, standings):
    """Разбор доказан, только если семь колонок итоговой таблицы сходятся у каждого игрока."""
    tally = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])
    for (_, host, guest), (hg, ag) in legs.items():
        for nick, scored, missed in ((host, hg, ag), (guest, ag, hg)):
            total = tally[nick]
            total[0] += 1
            total[4] += scored
            total[5] += missed
            if scored > missed:
                total[1] += 1
                total[6] += 3
            elif scored == missed:
                total[2] += 1
                total[6] += 1
            else:
                total[3] += 1
    wrong = {p: (standings[p], tally[p]) for p in standings if tuple(tally[p]) != standings[p]}
    if wrong:
        detail = ", ".join(f"{p}: лист {want} != пересчёт {got}"
                           for p, (want, got) in list(wrong.items())[:4])
        sys.exit(f"{division}: разбор матрицы не сходится с её же итоговой таблицей — {detail}")


def build_rows(calendars, notes):
    """Строки носителя: одна на ногу матрицы, тур и дата — из календаря."""
    notes_by_pair = defaultdict(list)
    for note in notes:
        notes_by_pair[tuple(sorted(note["pair"]))].append(note)
    collected, disputes = [], 0
    for division in DIVISIONS:
        legs, standings = matrix_legs(division)
        check_standings(division, legs, standings)
        for (game, host, guest), (hg, ag) in legs.items():
            found = [entry for entry in calendars.get((token(host), token(guest)), [])
                     if (entry[3], entry[4]) == (hg, ag)]
            if not found:
                sys.exit(f"{division}: календарь не знает игры {host} {hg}:{ag} {guest} — "
                         "два листа расходятся, вносить нечего")
            if len({entry[1] for entry in found}) > 1:
                sys.exit(f"{division}: календарь даёт игре {host} {hg}:{ag} {guest} "
                         f"несколько туров ({sorted({entry[1] for entry in found})})")
            _, tour, date, _, _ = found[0]
            collected.append((division, game, host, guest, hg, ag, int(tour), date))

    # В туре пара играет две игры на одной площадке. Тема часто успевает назвать только одну из
    # них, и её счёт для этой же пары и тура — не спор с листами, а вторая игра. Их надо знать
    # заранее, иначе примечание вводило бы человека в заблуждение.
    siblings = defaultdict(set)
    for _, _, host, guest, hg, ag, tour, _ in collected:
        siblings[(tuple(sorted((token(host), token(guest)))), tour)].add(tuple(sorted((hg, ag))))

    rows = []
    for division, game, host, guest, hg, ag, tour, date in collected:
        note = note_text(notes_by_pair, siblings, host, guest, hg, ag, tour)
        disputes += note != "матрица + календарь"
        row = {"season": "Season 1", "tournament": TOURNAMENT}
        if division == "Метеоры":
            row["league"] = division
        row.update({"stage": STAGE, "tour": f"Тур {tour}", "p1": host, "p2": guest,
                    "s1": hg, "s2": ag, "ot": False, "pk": False, "is_playoff": False,
                    "note_leg": note})
        rows.append((row, division, tour, game))
    rows.sort(key=lambda item: (DIVISIONS.index(item[1]), item[2], item[3],
                                 token(item[0]["p1"]), token(item[0]["p2"])))
    return [row for row, *_ in rows], disputes


def note_text(notes_by_pair, siblings, host, guest, hg, ag, tour):
    """Что говорит тема про эту ногу, если её версия не совпадает с обоими листами."""
    pair = tuple(sorted((token(host), token(guest))))
    scores = tuple(sorted((hg, ag)))
    base = "матрица + календарь"
    for note in notes_by_pair.get(pair, []):
        if tuple(sorted(note["scores"])) == scores:
            if note["tours"] and tour not in note["tours"]:
                return (f"{base}; тема называет тур "
                        f"{'/'.join(str(t) for t in note['tours'])} "
                        f"(коммент {note['comments'][0]})")
            return base
    clash = [n for n in notes_by_pair.get(pair, [])
             if tour in n["tours"] and tuple(sorted(n["scores"])) not in siblings[(pair, tour)]]
    if clash:
        return (f"{base}; тема для этого тура даёт счёт "
                f"{clash[0]['scores'][0]}:{clash[0]['scores'][1]} (коммент "
                f"{clash[0]['comments'][0]})")
    return base


def main():
    parser = argparse.ArgumentParser(description="Строки Сезона 1 из снимков google-таблиц")
    parser.add_argument("--check", action="store_true", help="только сверить, ничего не писать")
    args = parser.parse_args()

    notes = (json.loads(NOTES.read_text(encoding="utf-8")) if NOTES.exists() else [])
    rows, disputes = build_rows(calendar_legs(), notes)
    goals = sum(row["s1"] + row["s2"] for row in rows)
    carrier = json.loads(CARRIER.read_text(encoding="utf-8"))
    others = [row for row in carrier if row.get("tournament") != TOURNAMENT]
    fresh = rows
    print(f"ног собрано {len(fresh)}, голов {goals}, тур "
          f"{len({row['tour'] for row in fresh})}, споров с темой {disputes}; "
          f"в носителе строк Сезона 1 {len(carrier) - len(others)}, прочих {len(others)}")
    if args.check:
        same = [row for row in carrier if row.get("tournament") == TOURNAMENT] == fresh
        print("носитель совпадает с листами" if same else "НОСИТЕЛЬ ОТСТАЛ от листов")
        return 0 if same else 1
    CARRIER.write_text(json.dumps(others + fresh, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print(f"записано {len(fresh)} строк Сезона 1, всего в носителе {len(others) + len(fresh)}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
