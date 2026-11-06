"""Групповой этап 2-го Молодёжного Чемпионата: листы источника и отчёты в теме ВК.

Три куска источника складываются в одну сетку, и каждый отвечает за своё:

* лист «КАЛЕНДАРЬ ГРУППОВОГО ЭТАПА» — кто с кем и в каком туре: 21 встреча на дивизион,
  каждый с каждым по одному разу, по четыре ноги во встрече;
* лист «ГРУППОВОЙ ЭТАП» — сводка по команде: встреч, ног, побед, побед и поражений по
  пенальти, очков. Это результат турнира, по нему сверяется всё остальное;
* тема 41270759 — счёта отдельных ног. Только здесь видно, сколько забили.

Комментариев на все встречи не хватает, и это видно до импорта: четыре встречи «Кометов»
никто не выложил, а Den B. & Romix снялись — в сводке у пары нули, две выложенные встречи
источник не зачислил и четыре не выложил никто. Поэтому `group_stage` возвращает вместе с ногами
и `report`: что подтверждено комментарием, что выведено из сводки, что осталось неопределённым
и чего не было вовсе. Встречу без опубликованных счётов в базу кладёт одна строка без счёта:
рисовать четыре ноги с выдуманными голами — значит врать там, где источник промолчал.

Порядок сторон в строке — как в комментарии: «0:6» относится к той паре, которую автор
назвал первой. Повторную публикацию той же встречи склеиваем с проверкой: второй автор
мог переставить стороны, тогда ноги переворачиваются и только потом сравниваются.
"""

import csv
import re
import unicodedata
from pathlib import Path

TOPIC_ID = 41270759
TOURNAMENT = "2-й Молодёжный Чемпионат по Goal 3"
LEGS_PER_MEETING = 4
GROUP = 66162180
TOPIC_URL = f"https://vk.com/topic-{GROUP}_{TOPIC_ID}"
SHEET_URL = ("https://docs.google.com/spreadsheets/d/"
             "1a9ZAEqTTB4R_k6ib54MrZZ70FRLTrXjd9CfxD07tkVo")

CALENDAR_COLUMNS = (1, 5)  # календарь лежит в две колонки туров
DIVISIONS = {"кометы": "Кометы", "метеоры": "Метеоры"}

LEG = re.compile(r"(\d{1,2})\s*[:\-]\s*(\d{1,2})\s*(?:[(（]([^)）]*)[)）])?")
PK_WORD = re.compile(r"\b(pk|рк|пк)\b|пенальт", re.IGNORECASE)
SUMMARY_PAREN = re.compile(r"[(（][^()）]*(?:общ|итог)[^()）]*[)）]", re.IGNORECASE)
TOUR_MARK = re.compile(r"(\d{1,2})\s*(?:тур|ТУР|Тур)")
SEPARATOR = re.compile(r"\s+(?:vs|VS|Vs|-)\s+", re.IGNORECASE)
URL = re.compile(r"https?://\S+")
MARKUP = re.compile(r"\[id(\d+)\|([^\]]+)\]")

# «Metallist Balalaykin» в отчётах сокращают до «Metallist», Кубик пишется по-латински.
SPELLING_ALIAS = {
    "kubik": "кубик",
    "yuliy": "juliy",
    "leninist": "lenin1st",
}
RESULTS = ("meetings", "legs", "wins", "pk_wins", "pk_losses", "losses")


def norm(text):
    """Ник для сравнения: без pictogram, пробелов и регистра, с типовыми написаниями."""
    cleaned = "".join(ch for ch in str(text or "") if not unicodedata.category(ch).startswith("S"))
    token = re.sub(r"[^0-9a-zа-яё]", "", cleaned.lower())
    for needle, replacement in SPELLING_ALIAS.items():
        if token.startswith(needle):
            return replacement + token[len(needle):]
    return token


def members(side_text):
    """Фамилии стороны: «RVD & Palka Palych» → оба нормализованных ника."""
    return {norm(part) for part in re.split(r"&|/| и ", str(side_text or "")) if norm(part)}


def read_calendar(path):
    """Лист календаря → фикстуры в порядке листа: дивизион, тур и обе стороны."""
    rows = list(csv.reader(Path(path).read_text(encoding="utf-8-sig").splitlines()))
    state = {base: {"division": "", "tour": ""} for base in CALENDAR_COLUMNS}
    fixtures = []
    for row in rows:
        for base in CALENDAR_COLUMNS:
            cells = [cell.strip() for cell in row[base:base + 3]]
            if len(cells) < 3 or not cells[0]:
                continue
            head, middle, tail = cells
            if middle.lower() == "vs" and tail:
                fixtures.append({**state[base], "raw_a": head, "raw_b": tail})
                continue
            mark = TOUR_MARK.search(head)
            if mark:
                state[base]["tour"] = f"Тур {int(mark.group(1))}"
            elif head.lower() in DIVISIONS:
                state[base]["division"] = DIVISIONS[head.lower()]
    return fixtures


def read_standings(path):
    """Лист сводки → по строке на команду, в том же порядке, что перечислил источник."""
    rows = list(csv.reader(Path(path).read_text(encoding="utf-8-sig").splitlines()))
    division, standing = "", []
    for row in rows:
        cells = [cell.strip() for cell in row]
        if len(cells) < 10:
            continue
        if cells[1].lower() in DIVISIONS:
            division = DIVISIONS[cells[1].lower()]
        elif not re.fullmatch(r"\d+", cells[1] or ""):
            continue
        else:
            values = dict(zip(RESULTS, (int(value) for value in cells[3:10])))
            standing.append({"division": division, "team": cells[2], "points": int(cells[9]), **values})
    return standing


def read_pairs(topic_text):
    """Список участников из шапки темы: пары, написания ников одного id и все известные ники.

    Один человек вписан в шапку дважды под разными никами ([id91885454|RVD] в списке
    наставников и [id91885454|XakoFEAR] в составе пары) — по id написания склеиваются,
    и «RVD & Palka Palych» узнаётся как пара Palka Palych & XakoFEAR без ручных алиасов.
    Третий словарь — все упомянутые в шапке ники: по нему видно, что «E_not & Буц» — это
    замена (Буц стоит в списке запасных), а не неизвестный игрок.
    """
    spellings, pairs, by_nick = {}, [], {}
    for line in str(topic_text or "").splitlines():
        marks = MARKUP.findall(line)
        for player_id, nick in marks:
            by_nick.setdefault(norm(nick), (player_id, nick.strip()))
        if len(marks) != 2 or "&" not in line:
            continue
        for player_id, nick in marks:
            nick = nick.strip()
            spellings.setdefault(player_id, set()).update({norm(nick), norm(nick.split()[0])})
        pairs.append({"names": [marks[0][1].strip(), marks[1][1].strip()],
                      "ids": (marks[0][0], marks[1][0])})
    return pairs, spellings, by_nick


def pair_lookup(pairs, spellings):
    """Токен любой из двух фамилий (целиком или первым словом) → номер официальной пары."""
    tokens = {}
    for index, pair in enumerate(pairs):
        for player_id in pair["ids"]:
            for token in spellings[player_id]:
                tokens[token] = index
    return tokens


def side_key(side_text, tokens):
    """Какая официальная пара стоит за строкой отчёта; None — если это не одна пара (не угадываем)."""
    found = {tokens[token] for token in members(side_text) if token in tokens}
    return found.pop() if len(found) == 1 else None


def side_names(side_text, pair, pairs, by_nick):
    """Состав стороны так, как его написал автор отчёта: на встречу мог выйти запасной.

    Имена берутся из шапки (там «Metallist Balalaykin», а не «Metallist»), меняем только
    доказанную подмену: известен и id человека, и то, что в этой паре его нет. «E_not & Буц»
    → сторона играется Енотом и Буцем, а очками по-прежнему владеет пара E_not & Tymoschuk —
    так считает сводка источника. Сокращения («Metallist & Cyneprepou4uk») подменой не считаются:
    там нечего менять, второй id пары просто не назван.
    """
    names = list(pairs[pair]["names"])
    ids = list(pairs[pair]["ids"])
    known = [by_nick.get(norm(member)) for member in str(side_text).split("&")]
    in_side = {player[0] for player in known if player}
    extra = [player for player in known if player and player[0] not in ids]
    missing = [index for index, player_id in enumerate(ids) if player_id not in in_side]
    if len(extra) == 1 and len(missing) == 1:
        names[missing[0]] = extra[0][1]
        return names, extra[0][1]
    return names, None


def split_meeting(line):
    """Строка отчёта → тур, обе стороны и текст счётов; None, если строка не про матч."""
    line = line.strip()
    mark = TOUR_MARK.search(line)
    body = line[mark.end():].strip(" :.-") if mark else line
    parts = SEPARATOR.split(body, maxsplit=1)
    if len(parts) != 2 or not parts[0].strip():
        return None
    side_a, rest = parts[0].strip(), parts[1]
    first = LEG.search(rest)
    if not first:
        return None
    side_b = rest[:first.start()].strip(" ,.-—(")
    if not side_b:
        return None
    return {
        "tour": f"Тур {int(mark.group(1))}" if mark else "",
        "raw_a": side_a,
        "raw_b": side_b,
        "text": rest[first.start():],
        "links": URL.findall(line),
    }


def legs_of(text):
    """Ноги строки: базовый счёт, серия по пенальти и как это записал источник."""
    legs = []
    for score_a, score_b, paren in LEG.findall(SUMMARY_PAREN.sub(" ", text)):
        base = (int(score_a), int(score_b))
        series = None
        inside = LEG.search(paren or "")
        if inside and (PK_WORD.search(paren) or base[0] == base[1]):
            series = (int(inside.group(1)), int(inside.group(2)))
        shown = f"{base[0]}:{base[1]}"
        if series and base[0] == base[1]:
            shown = f"{shown} ({paren.strip()})"
        legs.append({"base": base, "series": series, "shown": shown})
    return legs


def flip(leg):
    """Нога с точностью до порядка сторон."""
    series = leg["series"]
    return {"base": tuple(reversed(leg["base"])),
            "series": tuple(reversed(series)) if series else None,
            "shown": leg["shown"]}


def outcome_of(leg):
    """Исход ноги: счёт, а при ничьей — серия. Обычной ничьей в этом турнире не бывает."""
    winner = leg["base"][0] - leg["base"][1] or (leg["series"] or (0, 0))[0] - (leg["series"] or (0, 0))[1]
    if winner > 0:
        return "win", "loss"
    if winner < 0:
        return "loss", "win"
    return "draw", "draw"


def read_comments(comments, tokens, pairs, by_nick):
    """Комментарии темы → встречи по парам: строки одного комментария складываются в публикацию.

    Отчёт о встрече выкладывают либо одной строкой с четырьмя счётами, либо четырьмя строками
    по ноге (так сделал Memori), либо дважды — по публикации от каждой стороны. Первая по
    номеру комментария публикация задаёт порядок сторон и становится справочной; остальные
    сравниваются с ней и в базу не идут.
    """
    meetings = {}
    unknown = []
    for comment in sorted(comments, key=lambda item: item["id"]):
        postings = {}
        last_pair = None
        for line in str(comment.get("text") or "").splitlines():
            parsed = split_meeting(line)
            if not parsed:
                # Ссылку на запись обычно ставят отдельной строкой под отчётом — она относится
                # к последней встрече этого же комментария, иначе доказательство игры потеряется.
                if last_pair and URL.search(line):
                    postings[last_pair]["links"] += URL.findall(line)
                continue
            key_a, key_b = side_key(parsed["raw_a"], tokens), side_key(parsed["raw_b"], tokens)
            if key_a is None or key_b is None or key_a == key_b:
                unknown.append({"comment_id": comment["id"], "line": line.strip(),
                                "sides": [parsed["raw_a"], parsed["raw_b"]], "keys": [key_a, key_b]})
                continue
            pair = tuple(sorted((key_a, key_b)))
            if pair not in postings:
                names, subs = sides_of_line(parsed, key_a, key_b, pairs, by_nick)
                postings[pair] = {"orientation": (key_a, key_b), "lines": [],
                                  "links": [], "comment_id": comment["id"],
                                  "names": names, "subs": subs}
            posting = postings[pair]
            legs = legs_of(parsed["text"])
            if (key_a, key_b) != posting["orientation"]:
                legs = [flip(leg) for leg in legs]
            posting["lines"].append({"line": line.strip(), "tour": parsed["tour"], "legs": legs})
            posting["links"] += parsed["links"]
            last_pair = pair
        for pair, posting in postings.items():
            meeting = meetings.setdefault(pair, {"pair": pair, "postings": []})
            meeting["postings"].append(posting)
    return meetings, unknown


def sides_of_line(parsed, key_a, key_b, pairs, by_nick):
    """Имена сторон этой публикации + подмены, если автор отчёта назвал запасного."""
    names = {}
    subs = []
    for raw, key in ((parsed["raw_a"], key_a), (parsed["raw_b"], key_b)):
        names[key], sub = side_names(raw, key, pairs, by_nick)
        if sub:
            subs.append(sub)
    return names, subs


def standings_budget(standings, tokens):
    """Сводка по номерам пар: сколько встреч и ног источник зачислил каждой команде."""
    budget = {}
    for row in standings:
        index = side_key(row["team"], tokens)
        if index is not None:
            budget[index] = row
    return budget


def allocate(meetings, budget, fixtures, tokens):
    """Каждая публикация получает статус: зачтена (бюджет сводки ещё есть) или нет.

    Встречу засчитываем обеим сторонам, только если у обеих остались зачётные встречи и ноги.
    Так из таблицы выводится и «неопубликованная» часть, и снятые с зачёта игры Den B. & Romix:
    у них бюджет нулевой, поэтому их опубликованные встречи остаются вне зачёта.
    """
    left = {index: dict(row) for index, row in budget.items()}
    published = {}
    order = sorted(meetings, key=lambda pair: (tour_of(pair, fixtures, tokens), pair))
    for pair in order:
        meeting = meetings[pair]
        meeting["fixture"] = fixtures.get(pair)
        first = meeting["postings"][0]
        meeting["orientation"] = first["orientation"]
        meeting["legs"] = [leg for line in first["lines"] for leg in line["legs"]]
        meeting["line"] = " | ".join(line["line"] for line in first["lines"])
        meeting["comment_id"] = first["comment_id"]
        meeting["links"] = sorted(set(first["links"]))
        meeting["side_names"] = first["names"]
        meeting["subs"] = first["subs"]
        meeting["extra_postings"] = meeting["postings"][1:]
        key_a, key_b = meeting["orientation"]
        enough = all(left.get(key, {}).get("meetings", 0) > 0 and
                     left.get(key, {}).get("legs", 0) >= LEGS_PER_MEETING for key in (key_a, key_b))
        meeting["counted"] = bool(enough and meeting["legs"])
        if meeting["counted"]:
            for key in (key_a, key_b):
                left[key]["meetings"] -= 1
                left[key]["legs"] -= len(meeting["legs"])
            published[pair] = meeting
    return published, left


def tour_of(pair, fixtures, tokens):
    fixture = fixtures.get(pair)
    if not fixture:
        return "Тур 99"
    match = re.search(r"\d+", fixture["tour"] or "")
    return f"{int(match.group()):02d}" if match else "99"


def tally_of(meetings, pairs):
    """Сводка по командам из разобранных ног: встреч, ног, побед, серий, поражений."""
    tally = {index: dict.fromkeys(RESULTS, 0) for index in range(len(pairs))}
    for meeting in meetings.values():
        if not meeting["counted"]:
            continue
        key_a, key_b = meeting["orientation"]
        decided_by_series = [leg["base"][0] == leg["base"][1] for leg in meeting["legs"]]
        for leg, series_leg in zip(meeting["legs"], decided_by_series):
            result_a, result_b = outcome_of(leg)
            for key, result in ((key_a, result_a), (key_b, result_b)):
                tally[key]["legs"] += 1
                if result == "win":
                    tally[key]["pk_wins" if series_leg else "wins"] += 1
                elif result == "loss":
                    tally[key]["pk_losses" if series_leg else "losses"] += 1
        for key in (key_a, key_b):
            tally[key]["meetings"] += 1
    return tally


def deduce(uncovered, residual):
    """Неопубликованные встречи, чей делёж ног однозначен: остаток команды отдаётся её встрече.

    Пока у команды одна непокрытая встреча, делить нечего — все оставшиеся ноги достаются ей.
    Такие встречи закрываются по одной, и после этого у второй стороны остаток тоже может
    стать одиночным. Если у обеих сторон непокрытых встреч несколько, делёж не определён —
    она уходит в отчёт, а не в базу.
    """
    open_fixtures = list(uncovered)
    resolved = []
    while open_fixtures:
        progressed = False
        for fixture in list(open_fixtures):
            key_a, key_b = fixture["pair"]
            for key, other in ((key_a, key_b), (key_b, key_a)):
                alone = [item for item in open_fixtures if key in item["pair"]]
                if len(alone) != 1:
                    continue
                wins = residual[key]["wins"] + residual[key]["pk_wins"]
                losses = residual[key]["losses"] + residual[key]["pk_losses"]
                if wins + losses != LEGS_PER_MEETING:
                    continue
                first_is_key = fixture["orientation"][0] == key
                share = (wins, losses) if first_is_key else (losses, wins)
                resolved.append({**fixture, "deduced": share})
                for touched, value in ((key, (wins, losses)), (other, (losses, wins))):
                    residual[touched]["wins"] -= value[0]
                    residual[touched]["losses"] -= value[1]
                    residual[touched]["meetings"] -= 1
                open_fixtures.remove(fixture)
                progressed = True
                break
        if not progressed:
            break
    return resolved, open_fixtures


def group_stage(sheet_dir, comments):
    """Листы источника и комментарии → ноги группового этапа и отчёт о подтверждениях."""
    fixtures_raw = read_calendar(Path(sheet_dir) / "1526661752.csv")
    standings = read_standings(Path(sheet_dir) / "102454828.csv")
    header = next((comment["text"] for comment in comments if comment["id"] == 22125), "")
    pairs, spellings, by_nick = read_pairs(header)
    tokens = pair_lookup(pairs, spellings)

    fixtures = {}
    unpaired = []
    for fixture in fixtures_raw:
        key_a, key_b = side_key(fixture["raw_a"], tokens), side_key(fixture["raw_b"], tokens)
        if key_a is None or key_b is None or key_a == key_b:
            unpaired.append(fixture)
            continue
        fixtures[tuple(sorted((key_a, key_b)))] = {
            "pair": (key_a, key_b), "orientation": (key_a, key_b), "division": fixture["division"],
            "tour": fixture["tour"], "raw_a": fixture["raw_a"], "raw_b": fixture["raw_b"],
        }

    budget = standings_budget(standings, tokens)
    meetings, unknown = read_comments(
        [comment for comment in comments if comment["id"] != 22125], tokens, pairs, by_nick)
    published, left = allocate(meetings, budget, fixtures, tokens)
    tally = tally_of(published, pairs)

    residual = {}
    for index, row in budget.items():
        residual[index] = {field: row[field] - tally[index][field] for field in RESULTS}

    uncovered = [fixture for pair, fixture in sorted(fixtures.items())
                 if pair not in published
                 and all(left.get(key, {}).get("meetings", 0) > 0 for key in pair)]
    resolved, ambiguous = deduce(uncovered, residual)
    # Выложенная, но не зачтённая встреча в `published` не попадает — она живёт как «ТП обоим»
    # с ногами в подписи. Считать её несыгранной значило бы дать одной встрече две строки.
    posted = set(published) | {tuple(sorted(meeting["orientation"])) for meeting in meetings.values()}
    withdrawn = [fixture for pair, fixture in sorted(fixtures.items())
                 if pair not in posted
                 and any(key in budget and budget[key]["meetings"] == 0 for key in pair)]

    games, report = [], {
        "unknown_lines": unknown,
        "calendar_unpaired": unpaired,
        "reposts": [],
        "wrong_leg_count": [],
        "void_meetings": [],
        "deduced": [],
        "ambiguous": [],
        "withdrawn": [],
        "teams": [],
        "unreconciled": [],
        "substitutions": [],
    }
    for pair in sorted(published, key=lambda item: (tour_of(item, fixtures, tokens), item)):
        meeting = published[pair]
        if len(meeting["legs"]) != LEGS_PER_MEETING:
            report["wrong_leg_count"].append(describe(meeting, pairs))
        for posting in meeting["extra_postings"]:
            legs = [leg for line in posting["lines"] for leg in line["legs"]]
            entry = describe(meeting, pairs)
            entry.update({
                "kept_comment": meeting["comment_id"],
                "second_comment": posting["comment_id"],
                "second_legs": [leg["shown"] for leg in legs],
                "agrees": [(leg["base"], leg["series"]) for leg in legs]
                          == [(leg["base"], leg["series"]) for leg in meeting["legs"]],
            })
            report["reposts"].append(entry)
        games += leg_rows(meeting, pairs)
        if meeting.get("subs"):
            report["substitutions"].append({**describe(meeting, pairs), "запасные": meeting["subs"],
                                            "ноги": [leg["shown"] for leg in meeting["legs"]]})

    for meeting in meetings.values():
        if meeting["counted"]:
            continue
        entry = describe(meeting, pairs)
        entry["legs"] = [leg["shown"] for leg in meeting["legs"]]
        report["void_meetings"].append(entry)
        games.append(tp_row(meeting, pairs, entry["legs"]))

    for fixture in resolved:
        games.append(deduced_row(fixture, pairs))
        report["deduced"].append({
            "division": fixture["division"], "tour": fixture["tour"],
            "pair": names(fixture["orientation"], pairs),
            "legs_won": list(fixture["deduced"]),
        })
    for fixture in ambiguous:
        report["ambiguous"].append({
            "division": fixture["division"], "tour": fixture["tour"],
            "pair": names(fixture["orientation"], pairs),
            "residual": {key: residual[key] for key in fixture["pair"]},
        })
    for fixture in withdrawn:
        walked = [names((key,), pairs)[0] for key in fixture["pair"]
                  if key in budget and budget[key]["meetings"] == 0]
        games.append(withdrawn_row(fixture, pairs, walked))
        report["withdrawn"].append({
            "division": fixture["division"], "tour": fixture["tour"],
            "pair": names(fixture["orientation"], pairs), "снялась": walked,
        })

    after = {index: dict(tally[index]) for index in tally}
    for fixture in resolved:
        key_a, key_b = fixture["orientation"]
        wins_a, wins_b = fixture["deduced"]
        for key, share in ((key_a, (wins_a, wins_b)), (key_b, (wins_b, wins_a))):
            after[key]["meetings"] += 1
            after[key]["legs"] += LEGS_PER_MEETING
            after[key]["wins"] += share[0]
            after[key]["losses"] += share[1]

    for index, row in sorted(budget.items()):
        gap = {field: (row[field], tally[index][field]) for field in RESULTS
               if row[field] != tally[index][field]}
        unreconciled = {field: (row[field], after[index][field]) for field in RESULTS
                        if row[field] != after[index][field]}
        report["teams"].append({
            "team": names((index,), pairs)[0], "division": row["division"],
            "по_таблице": {field: row[field] for field in RESULTS},
            "по_комментариям": {field: tally[index][field] for field in RESULTS},
            "пробел_комментариев": gap,
        })
        if unreconciled:
            report["unreconciled"].append({
                "team": names((index,), pairs)[0], "division": row["division"],
                "расхождение": {field: list(values) for field, values in unreconciled.items()},
            })
    report["totals"] = {
        "фикстур в календаре": len(fixtures),
        "встреч с опубликованными ногами": len(published),
        "встреч выведено из сводки": len(resolved),
        "встреч без определённого счёта": len(ambiguous),
        "не зачтено источником": len(report["void_meetings"]),
        "не сыграно (команда снялась)": len(report["withdrawn"]),
        "строк ног в базу": len(games),
        "сходимость со сводкой": "полная" if not report["unreconciled"] else "не сходится",
    }
    return games, report


def names(orientation, pairs):
    return [" & ".join(pairs[index]["names"]) for index in orientation]


def describe(meeting, pairs):
    fixture = meeting.get("fixture") or {}
    return {
        "division": fixture.get("division", ""),
        "tour": fixture.get("tour", ""),
        "pair": names(meeting["orientation"], pairs),
        "comment_id": meeting["comment_id"],
    }


def leg_rows(meeting, pairs):
    """Ноги встречи → строки носителя: стороны, счёт, исход, ссылка на комментарий."""
    key_a, key_b = meeting["orientation"]
    names_a = meeting.get("side_names", {}).get(key_a) or pairs[key_a]["names"]
    names_b = meeting.get("side_names", {}).get(key_b) or pairs[key_b]["names"]
    rows = []
    for index, leg in enumerate(meeting["legs"], 1):
        result_a, result_b = outcome_of(leg)
        rows.append({
            "tournament": TOURNAMENT,
            "division": (meeting.get("fixture") or {}).get("division", ""),
            "tour": (meeting.get("fixture") or {}).get("tour") or meeting.get("tour", ""),
            "team_a": names_a,
            "team_b": names_b,
            "label_a": " & ".join(names_a),
            "label_b": " & ".join(names_b),
            "score": list(leg["base"]),
            "series": list(leg["series"]) if leg["series"] else None,
            "outcome": [result_a, result_b],
            "phase": "penalties" if leg["base"][0] == leg["base"][1] else "regular",
            "score_text": leg["shown"],
            "counted": meeting["counted"],
            "source_ref": f"topic-{TOPIC_ID}#{meeting['comment_id']}#{key_a}-{key_b}#{index}",
            "source_line": meeting["line"][:200],
            "links": meeting["links"],
            "comment_url": f"{TOPIC_URL}#post{meeting['comment_id']}",
        })
    return rows


def tp_row(meeting, pairs, legs):
    """Встреча, которую сводка источника не знает: одна строка с «ТП обоим».

    Игра есть в комментариях, но в таблице её нет ни у одной из пар, поэтому голы не идут в
    счёт, а сторонам записывается техническое поражение без победителя: витрина показывает сам
    факт встречи и опубликованные ноги в подписи, а решает уже человек.
    """
    key_a, key_b = meeting["orientation"]
    names_a = meeting.get("side_names", {}).get(key_a) or pairs[key_a]["names"]
    names_b = meeting.get("side_names", {}).get(key_b) or pairs[key_b]["names"]
    fixture = meeting.get("fixture") or {}
    comment = meeting["comment_id"]
    return {
        "tournament": TOURNAMENT,
        "division": fixture.get("division", ""),
        "tour": fixture.get("tour", ""),
        "team_a": names_a,
        "team_b": names_b,
        "label_a": " & ".join(names_a),
        "label_b": " & ".join(names_b),
        "score": [None, None],
        "series": None,
        "outcome": ["none", "none"],
        "phase": "regular",
        "tp": True,
        "score_text": f"ТП обоим: сводка источника не знает этой встречи (ноги: {', '.join(legs)})",
        "counted": False,
        "source_ref": f"topic-{TOPIC_ID}#{comment}#{key_a}-{key_b}",
        "source_line": meeting["line"][:200],
        "links": meeting["links"],
        "comment_url": f"{TOPIC_URL}#post{comment}",
        "review": {
            "задача": "встреча сыграна и выложена, но не зачислена в сводку — сейчас записана как "
                      "ТП обоим; проверить по итоговой картинке турнира и решить, считать ли ноги",
            "ссылки": [f"{TOPIC_URL}#post{comment}", SHEET_URL],
        },
    }


def deduced_row(fixture, pairs):
    """Выведенная из сводки встреча: одна строка, счёта ног в источнике нет.

    Из остатков сводки известен делёж ног, а голов нет — придумывать их нельзя, поэтому строка
    уходит в очередь редактуры со ссылкой на календарь: человек найдёт запись встречи и правкой
    вернёт ей счёт.
    """
    key_a, key_b = fixture["orientation"]
    wins_a, wins_b = fixture["deduced"]
    label_a, label_b = " & ".join(pairs[key_a]["names"]), " & ".join(pairs[key_b]["names"])
    return {
        "tournament": TOURNAMENT,
        "division": fixture["division"],
        "tour": fixture["tour"],
        "team_a": pairs[key_a]["names"],
        "team_b": pairs[key_b]["names"],
        "label_a": label_a,
        "label_b": label_b,
        "score": [None, None],
        "series": None,
        "outcome": ["none", "none"],
        "phase": "regular",
        "score_text": f"счёт ног не опубликован; по сводке источника — {wins_a}:{wins_b} по ногам",
        "counted": True,
        "source_ref": f"topic-{TOPIC_ID}#calendar#{key_a}-{key_b}",
        "source_line": f"{fixture['raw_a']} vs {fixture['raw_b']} ({fixture['division']}, {fixture['tour']})",
        "links": [],
        "comment_url": TOPIC_URL,
        "review": {
            "задача": f"нет счётов ног: {label_a} против {label_b} — "
                      f"{wins_a}:{wins_b} по ногам известно из сводки, голов нет",
            "ссылки": [SHEET_URL, TOPIC_URL],
        },
    }


def withdrawn_row(fixture, pairs, walked):
    """Встреча, которой не было: команда снялась, и сводка даёт ей ноль встреч.

    Ног никто не выкладывал, соперник не получил ни победы, ни очков — зачтённой встречи нет ни
    у кого. Строка всё равно нужна: календарь источника полон, и дыра в нём читается как «игра
    потерялась», а не как «игру не сыграли». Голов не рисуем, обеим сторонам технический результат,
    в очередь редактуры не отправляем: сводка уже ответила, решать человеку нечего.
    """
    key_a, key_b = fixture["orientation"]
    return {
        "tournament": TOURNAMENT,
        "division": fixture["division"],
        "tour": fixture["tour"],
        "team_a": pairs[key_a]["names"],
        "team_b": pairs[key_b]["names"],
        "label_a": " & ".join(pairs[key_a]["names"]),
        "label_b": " & ".join(pairs[key_b]["names"]),
        "score": [None, None],
        "series": None,
        "outcome": ["none", "none"],
        "phase": "regular",
        "tp": True,
        "score_text": f"ТП обоим: встреча не сыграна — команда {' / '.join(walked)} снялась, "
                      f"сводка даёт ей 0 встреч",
        "counted": False,
        "source_ref": f"topic-{TOPIC_ID}#calendar#{key_a}-{key_b}",
        "source_line": f"{fixture['raw_a']} vs {fixture['raw_b']} ({fixture['division']}, {fixture['tour']})",
        "links": [],
        "comment_url": SHEET_URL,
    }
