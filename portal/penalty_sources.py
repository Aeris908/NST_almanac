"""Турниры по пенальти: сетка источника и отчёты темы → строки носителя.

Из четырёх изданий «сольного турнира по пенальти» в теме сообщества живут три: 2-й (июль 2015,
итоги только картинкой — её разбирает человек), 3-й (апрель-май 2016: восемь групп и Full Double
Elimination до 7 побед) и 4-й (март 2017, FDE до 5 побед на challonge).

Что здесь источник, а что доказательство:
  * сетка — `special_tournaments/penalty3.csv` (гугл-лист «Goal 3 PK.xls», ссылка в первом
    сообщении темы 3-го) и `data/challonge_penalty4.json` (выгрузка сетки 4-го); они задают
    пары, этап и счёт;
  * комментарии темы — доказательство: ссылка на пост и на запись ноги. Для группового тура
    3-го турнира комментарии — ещё и единственный источник игр: таблицу групп организатор
    держал на Диске, и файл не дожил (ссылка из первого сообщения отдаёт 404).

Плей-офф 3-го турнира приносится целиком, кроме строк, которые носитель уже знает: рамка
документа описана по сетке заранее, и второй ряд той же игры был бы дублем. Правила разбора —
те же, что для молодёжки: первая по номеру публикация задаёт порядок сторон, повтор того же
текста в другом комментарии вторым рядом не идёт, а всё, что не сходится, попадает в отчёт.
"""

import csv
import io
import json
import re
from collections import Counter
from pathlib import Path

from portal.name_tables import ALIAS_MAP
from portal.names import clean_alias

ROOT = Path(__file__).resolve().parent.parent
GROUP = 66162180
SEASON = "Сольные турниры"

# Документ (рамка) и тема на каждое издание. 2-й турнир остаётся в носителе: счётов в теме нет.
TOURNAMENTS = {
    "3-й": {"title": "3-й Сольный Турнир по пенальти", "topic": 33437511, "grid": True},
    "4-й": {"title": "4-й Сольный Турнир по пенальти", "topic": 34920573, "grid": False},
}
GRID_CSV = ROOT / "special_tournaments" / "penalty3.csv"
# Гугл-лист «Goal 3 PK.xls» — тот же лист, что сохранился копией в `penalty3.csv`; ссылка нужна
# задаче редактуры, чтобы человек открыл те же ячейки, что читает разбор.
SHEET_URL = ("https://docs.google.com/spreadsheets/d/"
             "18lWAb4YTTEbdh8Kk0Q0Y62O0G9lkWxtbQ91tL_AZc4Y/edit")
# Подсказка человеку в задаче, а не данные: 7:4 суперфинала взято из рукописного литерала
# `collectors/parse_special_tournaments_data.py`, сетка источника счёт не записала вовсе.
FRAME_HINT = {("3-й Сольный Турнир по пенальти", "Superfinal"):
              "в прежней рамке турнира значилось 7:4"}
BRACKET_JSON = ROOT / "data" / "challonge_penalty4.json"
CARRIER = ROOT / "special_tournaments_data.json"

# Блоки сетки 3-го турнира: начало блока, его заголовок и смещения колонки имён и колонки
# счёта — как подписал источник (гугл-лист «Goal 3 PK.xls»).
GRID_BLOCKS = [
    (0, "Winners 1/8", 1, 5), (7, "Winners 1/4", 1, 5), (14, "Winners 1/2", 1, 5),
    (21, "Winners Final", 1, 5), (28, "Superfinal", 1, 5),
    (36, "Losers Final", 2, 1), (43, "Losers stage 5", 2, 1), (50, "Losers stage 4", 2, 1),
    (57, "Losers stage 3", 2, 1), (64, "Losers stage 2", 2, 1), (71, "Losers stage 1", 2, 1),
]
# Круги challonge → этап. Верхняя сетка читается по числу встреч (5, 8, 4, 2, 1), нижняя — по
# номеру круга; «Grand Final» даёт две строки: идущему снизу нужно выиграть дважды.
WINNERS_ROUNDS = {1: "Winners, круг 1", 2: "Winners 1/8", 3: "Winners 1/4", 4: "Winners 1/2",
                  5: "Winners Final", 6: "Гранд-финал"}
LOSERS_ROUNDS = {-1: "Losers, круг 1", -2: "Losers stage 2", -3: "Losers stage 3",
                 -4: "Losers stage 4", -5: "Losers stage 5", -6: "Losers stage 6",
                 -7: "Losers Final"}

# Написания источниковой темы, которых справочник не знает: русские формы ников и одна
# опечатка. Всё, что `ALIAS_MAP` уже умеет сам («Распутник», «Кирпич», «Kipriot91»), здесь не
# перечислено — таблица должна оставаться короткой и читаться как список открытий источника.
LOCAL_ALIAS = {
    "Мафута": "mafuta", "мафута": "mafuta", "Mafuta": "mafuta", "Рик": "Ric25", "рик": "Ric25",
    "Центзлой": "CentZloy", "Допи": "Dopi", "допи": "Dopi", "Допи4": "Dopi",
    "мейкер": "AJ_Maker", "Енот": "E_not", "Аяз": "BZK", "аяз": "BZK", "бзк": "BZK",
    "Дрон": "Dr1N", "дрон": "Dr1N", "Расти": "Rustin Cohle", "расти": "Rustin Cohle",
    "Эдекси": "edexy", "эдекси": "edexy", "Edexy": "edexy", "Липецк": "Lipetsk",
    "Транзистор": "Transistor", "транзистор": "Transistor", "Тимощук": "Tymoschuk",
    "тимощук": "Tymoschuk", "Кунио": "Kunio", "ТубусТД": "tubustd",
    "huba-buba": "Huba Buba", "Huba-Buba 5": "Huba Buba", "ектоПовер": "ectoPower",
    "Alpharusin": "Alpharushin", "Ромарио": "Romario",
}
# Буквы групп в регламенте 3-го турнира набраны кириллицей, а в отчётах — латиницей.
GROUP_LETTERS = {"А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K", "М": "M",
                 "О": "O", "Р": "P", "Т": "T", "У": "U", "Х": "X"}

URL = re.compile(r"https?://\S+")
# Числа не должны липнуть к словам: в «Kipriot91 - 5:0» счёт только один, а «91 - 5» — не он.
SCORE = re.compile(r"(?<!\w)(\d{1,2})\s*[:\-–]\s*(\d{1,2})(?!\w)")
PARENTHETIC = re.compile(r"[(（]([0-9\s:;,.\-–]+)[)）]")
PARTICIPANT = re.compile(r"\[id(-?\d+)\|([^\]]+)\]")
PRONOUN = re.compile(r"(?<![\w-])я(?![\w-])")
MAX_SCORE = 12  # серия до 7 побед плюс переигровка; «23:59» это время, а не счёт


def topic_url(topic):
    return f"https://vk.com/topic-{GROUP}_{topic}"


def post_url(topic, comment_id):
    return f"{topic_url(topic)}#post{comment_id}"


def canonical(text):
    """Написание источника → каноник справочника: локальная таблица, затем `ALIAS_MAP`."""
    token = re.sub(r"\s+", " ", str(text or "")).strip()
    return clean_alias(LOCAL_ALIAS.get(token, token)) if token else None


def group_letter(text):
    letters = re.sub(r"[^А-ЯA-Z]", "", str(text or ""))[:1]
    return GROUP_LETTERS.get(letters, letters)


def org_post(comments):
    """Первое сообщение темы: `board.getComments` отдаёт его первым комментарием от сообщества.

    Оно же — заявка участников. Регламент внутри него полнеет счётов-примеров («к примеру, -
    5:3, 4:5, 2:5»), поэтому как отчёт результатов этот комментарий не разбирается.
    """
    for comment in sorted(comments, key=lambda item: item["id"]):
        if comment["from_id"] == -GROUP:
            return str(comment.get("text") or ""), comment["id"]
    return "", None


def roster(text):
    """Заявка и группы из первого сообщения темы: строки `[id123|Ник]` под заголовком группы."""
    players, groups, group = {}, {}, None
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("группа"):
            parts = stripped.split()
            group = group_letter(parts[1]) if len(parts) > 1 else None
        found = PARTICIPANT.search(line)
        if not found:
            continue
        nick = canonical(found.group(2)) or found.group(2).strip()
        players[int(found.group(1))] = nick
        if group:
            groups[nick] = group
    return players, groups


def vocabulary(nicks):
    """Написания, которые стоит искать в отчётах: каноник игрока и все его формы из справочника.

    Источник пишет того же человека по-разному («BOP95» и «ВОР95», «Izzotope» и «izzzotope»,
    «Dopi4» и «Допи»), поэтому словарь строится обратным проходом по `ALIAS_MAP`: берутся все
    ключи, которые приводят к нужному нику. Список игроков дают и заявка темы, и сетка: заявка
    4-го турнира с сеткой не сходится (ВОР95 заменён на Memori), и без сетки Memori остался бы
    нераспознанным — такие встречи уходят в отчёт, а не в базу молча.
    """
    known = {nick for nick in nicks if nick}
    words = set(known)
    for source in list(LOCAL_ALIAS) + list(ALIAS_MAP):
        if canonical(source) in known:
            words.add(source)
    return sorted({word for word in words if len(word) > 1}, key=len, reverse=True)


def find_nicks(text, words, author):
    """Игроки, названные в строке, в порядке появления. `я` — это автор комментария."""
    lowered = text.lower()
    found = {}
    for word in words:
        position = lowered.find(word.lower())
        nick = canonical(word)
        if position < 0 or nick in found:
            continue
        found[nick] = position
    pronoun = PRONOUN.search(text)
    if author and pronoun and author not in found:
        found[author] = pronoun.start()
    return [nick for nick, _ in sorted(found.items(), key=lambda item: item[1])]


def legs_of(text):
    """Счёта ног из строки: сначала из скобки серии, иначе — все пары чисел подряд."""
    bracket = PARENTHETIC.search(text)
    source = bracket.group(1) if bracket and SCORE.search(bracket.group(1)) else text
    legs = []
    for match in SCORE.finditer(source):
        score = tuple(map(int, match.groups()))
        if max(score) <= MAX_SCORE:
            legs.append(score)
    return legs


def plain(line):
    """Строка без ссылок: подчёркивание вокруг цифр — разметка источника, а не часть счёта."""
    text = URL.sub(" ", line)
    text = re.sub(r"_(?=\s*\d)", " ", text)
    return re.sub(r"(?<=\d)_", " ", text)


def game_key(a, b, s1, s2):
    """Игра без порядка сторон: кто выиграл и с каким счётом.

    Один и тот же текст в двух комментариях (и перевёрнутые стороны) дают один ключ — второй
    показ не удваивает игру. Ничья в серии пенальти невозможна по регламенту, но ключ её различает.
    """
    if s1 == s2:
        return (*tuple(sorted([a, b])), "draw", s1)
    winner, loser, hi, lo = ((a, b, s1, s2) if s1 > s2 else (b, a, s2, s1))
    return (winner, loser, hi, lo)


def comment_videos(comment):
    """Видео-вложения комментария: ссылка и название.

    Название — тоже источник: игрок крепит запись «Goal3 PK. Kunio vs BZK», а в тексте оставляет
    одно «5-1». Счёта в названиях нет ни разу (проверено по обоим топикам), поэтому они дают
    только пары сторон.
    """
    out = []
    for attachment in comment.get("attachments") or []:
        video = attachment.get("video") or {}
        if video.get("id"):
            out.append({"url": f"https://vk.com/video{video['owner_id']}_{video['id']}",
                        "title": str(video.get("title") or "")})
    return out


def comment_legs(comments, players, words, skip=None):
    """Все ноги, выложенные в комментариях: пара, порядок сторон, счёт, пост и ссылки.

    Строка обязана назвать двух известных игроков и показать счёт. Отдельная строка с парой без
    счёта («ectoPower vs BZK») запоминается, и счёт следующих строк относится к ней: так отчёты
    выкладывают Memori, ectoPower и Kunio. Если же в строке только счёт, а пара не названа,
    стороны берутся из названия прикреплённого видео — но лишь когда видео в комментарии одно
    и его название читается однозначно. Первое сообщение темы (`skip`) не разбирается: там счёт
    есть только в примерах регламента.

    Третьим списком возвращаются `mentions` — места, где пара названа без счёта (строка «BZK vs
    izzzotope» или название закреплённого видео). Они игру не рождают, но позволяют приложить
    запись к встрече сетки, у которой счёт сказал только источник структуры.
    """
    legs, unparsed, mentions = [], [], []
    for comment in sorted(comments, key=lambda item: item["id"]):
        if comment["id"] == skip:
            continue
        author = players.get(comment["from_id"])
        videos = comment_videos(comment)
        titled = [video for video in videos
                  if len(find_nicks(video["title"], words, None)) >= 2]
        for video in titled:
            pair = find_nicks(video["title"], words, None)[:2]
            mentions.append({"pair": tuple(sorted(pair)), "comment_id": comment["id"],
                             "line": f"видео «{video['title']}»", "links": [video["url"]]})
        pending = None
        for line in str(comment.get("text") or "").splitlines():
            raw = line.strip()
            if not raw:
                continue
            text = plain(raw)
            scores = legs_of(text)
            nicks = find_nicks(text, words, author)
            if len(nicks) >= 2:
                nicks = nicks[:2]
                if scores:
                    pending = None
                else:
                    pending = (nicks, raw)
                    mentions.append({"pair": tuple(sorted(nicks)), "comment_id": comment["id"],
                                     "line": raw, "links": [video["url"] for video in videos]})
                    continue
            elif not scores:
                continue
            elif pending:
                nicks, source = pending
                raw = f"{source} — {raw}"
            elif len(titled) == 1:
                nicks = find_nicks(titled[0]["title"], words, None)[:2]
                raw = f"{raw} — стороны по названию видео «{titled[0]['title']}»"
            else:
                unparsed.append({"comment_id": comment["id"], "line": raw,
                                 "why": f"названо игроков: {len(nicks)}"
                                        + (f" — {', '.join(nicks)}" if nicks else "")})
                continue
            links = URL.findall(raw) + [video["url"] for video in videos]
            for score in scores:
                legs.append({"pair": tuple(sorted(nicks)), "a": nicks[0], "b": nicks[1],
                             "s1": score[0], "s2": score[1], "comment_id": comment["id"],
                             "line": raw, "links": list(dict.fromkeys(links))})
    return legs, unparsed, mentions


def sum_proof(legs, game):
    """Доказательство встречи, у которой в теме несколько ног вместо одного счёта.

    Challonge записывает серию одной строкой («4:10»), а источник выкладывает её двумя играми:
    «Буц - Christian - 1:5» и «Буц - Christian - 3:5 (Ответка на слабо)». Сумма ног одной
    публикации, совпавшая с сеткой, и есть доказательство всей встречи.
    """
    by_comment = {}
    for leg in legs:
        by_comment.setdefault(leg["comment_id"], []).append(leg)
    want = game_key(game["a"], game["b"], game["s1"], game["s2"])
    for comment_id, group in sorted(by_comment.items()):
        if len(group) < 2:
            continue
        total = (sum(leg["s1"] for leg in group), sum(leg["s2"] for leg in group))
        if game_key(group[0]["a"], group[0]["b"], *total) == want:
            return group
    return None


def read_grid(path=GRID_CSV):
    """Сетка плей-офф 3-го турнира: 11 блоков, в каждом — пары строк колонки имён.

    На стороне победителей имя стоит сразу за заголовком блока, а счёт — через пять колонок;
    на стороне проигравших блок читается справа налево: номер встречи, счёт, имя. Встреча без
    счёта (суперфинал источник счётом не записал) возвращается с `unverified` — доносить счёт
    до неё нельзя, только пометить.
    """
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    games = []
    for start, stage, name_at, score_at in GRID_BLOCKS:
        names = [(row, rows[row][start + name_at].strip()) for row in range(1, len(rows))
                 if start + name_at < len(rows[row]) and rows[row][start + name_at].strip()]
        for first, second in zip(names[0::2], names[1::2]):
            a, b = canonical(first[1]), canonical(second[1])
            s1 = rows[first[0]][start + score_at].strip()
            s2 = rows[second[0]][start + score_at].strip()
            scored = s1.isdigit() and s2.isdigit()
            if not a or not b or a == b:
                continue
            games.append({"stage": stage, "league": "Плей-офф", "a": a, "b": b,
                          "s1": int(s1) if scored else None, "s2": int(s2) if scored else None,
                          "number": f"{stage}#{len(games) + 1}",
                          "line": f"{stage}: {first[1]} {s1}:{s2} {second[1]}"})
    return games


def read_bracket(path=BRACKET_JSON):
    """Сетка challonge 4-го турнира: круг задаёт этап, номер встречи остаётся в подписи."""
    games = []
    for match in json.loads(Path(path).read_text(encoding="utf-8")):
        stage = WINNERS_ROUNDS.get(match["round"]) or LOSERS_ROUNDS.get(match["round"])
        if stage is None:
            continue
        if match["slot"] == "V":
            stage = "Гранд-финал (переигровка)"
        games.append({
            "stage": stage,
            "league": "Верхняя сетка" if match["round"] > 0 else "Нижняя сетка",
            "a": canonical(match["p1"]), "b": canonical(match["p2"]),
            "s1": match["s1"], "s2": match["s2"], "number": f"challonge #{match['id']}",
            "line": f"{stage}: {match['p1']} {match['s1']}:{match['s2']} {match['p2']}"})
    return games


def carrier_rows(title):
    """Строки, которые рамка документа описывает сама: стороны в своём порядке, этап и счёт.

    Рамка 3-го турнира — те 20 встреч плей-офф, что лежали в базе до живого разбора: они уже
    навешены на документ, и второй ряд той же игры был бы дублем. Порядок сторон в рамке свой,
    поэтому ключ строится от неё, а не от отсортированной пары.
    """
    for doc in json.loads(CARRIER.read_text(encoding="utf-8")):
        if doc.get("title") != title:
            continue
        rows = []
        for row in doc.get("matches") or []:
            parsed = re.match(r"^\s*(\d+)\s*[:\-–]\s*(\d+)\s*$", str(row.get("score") or ""))
            a = canonical(str(row.get("p1") or "").split("&")[0])
            b = canonical(str(row.get("p2") or "").split("&")[0])
            if not parsed or not a or not b:
                continue
            rows.append({"a": a, "b": b, "stage": row.get("stage"),
                         "s1": int(parsed.group(1)), "s2": int(parsed.group(2))})
        return rows
    return []


def row_of(game, title, topic, proof, groups, hint=None):
    """Строка носителя: стороны, счёт, этап, ссылка на доказательство и задача человеку, если его нет."""
    scored = game["s1"] is not None
    line = proof["line"][:200] if proof else game["line"]
    if proof and "s1" not in proof:
        # Доказательство назвало пары, но не счёт: он взят из сетки, и строка обязана это помнить.
        line = f"{line} — счёт только в сетке источника, в отчёте темы его нет"
    row = {
        "tournament": title,
        "season": SEASON,
        "kind": "special",
        "row_set": "special",
        "stage": game["stage"],
        "league": game["league"],
        "tour": game["stage"],
        "team_a": [game["a"]],
        "team_b": [game["b"]],
        "score": [game["s1"], game["s2"]] if scored else [None, None],
        "score_text": (f"{game['s1']}:{game['s2']}" if scored
                       else "счёт не опубликован: в сетке источника только стороны"),
        "phase": "regular",
        "counted": True,
        "source_ref": (f"topic-{topic}#{proof['comment_id']}#{game['number']}" if proof
                       else f"bracket-{topic}#{game['number']}"),
        "source_line": line,
        "source_text": line,
        "source_page": f"topic-{topic}",
        "page_url": post_url(topic, proof["comment_id"]) if proof else topic_url(topic),
        "links": list(dict.fromkeys(proof["links"])) if proof else [],
        "note": (f"{game['s1']}:{game['s2']}" if scored
                 else "счёт не опубликован: в сетке источника только стороны"),
    }
    if not scored:
        # Исход без победителя и без голов: витрина показывает сам факт встречи, а счёт впишет
        # человек. Ровно та же форма, что у выведенных строк группового тура молодёжки.
        row["outcome"] = ["none", "none"]
    if not proof:
        row["review"] = {
            "задача": "встреча есть в сетке источника, но отчёта в теме нет — найти запись и "
                      "приложить ссылку" + (f"; {hint}" if hint else ""),
            "ссылки": [topic_url(topic)],
        }
    if not scored:
        row["review"] = {"задача": "счёт суперфинала источником не записан (в гугл-листе пусты "
                                   "обе ячейки счёта) — проверить по записи и вписать в интерфейсе"
                                   + (f"; {hint}" if hint else ""),
                         "ссылки": [topic_url(topic), SHEET_URL]}
    if game["stage"].startswith("Группа"):
        letter_a, letter_b = groups.get(game["a"]), groups.get(game["b"])
        if letter_a and letter_b and letter_a != letter_b:
            row["review"] = {"задача": f"встреча помечена группой {letter_a}, но соперник играет "
                                       f"в {letter_b} — проверить, где она играла",
                             "ссылки": [row["page_url"]]}
    return row


def penalty_games(dump_dir):
    """Обе темы пенальти → строки носителя и отчёт для проверки.

    Порядок строк: сначала групповой тур, потом сетка плей-офф — так читатель карточки турнира
    показывает группы выше плей-офф, а `order_in_source` идёт за ними.
    """
    rows, report = [], {"турниры": {}, "вне сетки": [], "не распознано": [], "без отчёта": [],
                        "без счёта": [], "повторы показов": [], "рамка против сетки": [],
                        "счёт только из сетки": []}
    for meta in TOURNAMENTS.values():
        topic = meta["topic"]
        path = Path(dump_dir) / "comments" / f"{topic}.json"
        if not path.exists():
            continue
        dump = json.loads(path.read_text(encoding="utf-8"))
        comments = dump["comments"]
        reglament, org_id = org_post(comments)
        players, groups = roster(reglament)
        games = read_grid() if meta["grid"] else read_bracket()
        frame = carrier_rows(meta["title"]) if meta["grid"] else {}
        nicks = set(players.values()) | {game["a"] for game in games} | {game["b"] for game in games}
        legs, unparsed, mentions = comment_legs(comments, players, vocabulary(nicks), skip=org_id)

        # Встреча сетки, счёт которой рамка документа уже описывает, живым строкам не достается:
        # иначе одна игра легла бы двумя рядами. Этап для проверки не берётся — рамка 3-го
        # турнира подписывает лузерские встречи одним «Losers Round», а сетка зовёт их по кругам.
        frame_keys = {game_key(row["a"], row["b"], row["s1"], row["s2"]) for row in frame}
        grid_keys = {game_key(game["a"], game["b"], game["s1"], game["s2"])
                     for game in games if game["s1"] is not None}
        for row in frame:
            if game_key(row["a"], row["b"], row["s1"], row["s2"]) not in grid_keys:
                report["рамка против сетки"].append({
                    "турнир": meta["title"], "этап": row["stage"],
                    "пара": [row["a"], row["b"]], "в рамке": f"{row['s1']}:{row['s2']}",
                    "в сетке": "такой встречи в сетке источника нет"})

        def in_frame(game):
            return game["s1"] is not None and game_key(game["a"], game["b"],
                                                      game["s1"], game["s2"]) in frame_keys

        # Нога, совпавшая со встречей сетки, становится её доказательством и в групповой тур
        # уже не идёт. Если нога назвала пару, но не назвала счёт (строка «BZK vs izzzotope» и
        # название закреплённого видео), доказательством становится сама запись — но только когда
        # пара играет в сетке ровно одну встречу: иначе непонятно, к какой из двух прикладывать.
        by_key, by_pair = {}, {}
        for leg in legs:
            by_key.setdefault(game_key(leg["a"], leg["b"], leg["s1"], leg["s2"]), []).append(leg)
            by_pair.setdefault(leg["pair"], []).append(leg)
        by_mention = {}
        for mention in mentions:
            by_mention.setdefault(mention["pair"], []).append(mention)
        single = Counter(tuple(sorted([game["a"], game["b"]])) for game in games)
        proofs, proven = {}, set()
        for game in games:
            if in_frame(game) or game["s1"] is None:
                continue
            found = by_key.get(game_key(game["a"], game["b"], game["s1"], game["s2"]))
            if not found:
                found = sum_proof(by_pair.get(tuple(sorted([game["a"], game["b"]])), []), game)
            if found:
                proofs[id(game)] = found[0]
                proven.update(id(leg) for leg in found)
                continue
            pair = tuple(sorted([game["a"], game["b"]]))
            if single[pair] == 1 and by_mention.get(pair):
                proofs[id(game)] = by_mention[pair][0]
                report["счёт только из сетки"].append({
                    "турнир": meta["title"], "этап": game["stage"], "пара": list(pair),
                    "счёт": f"{game['s1']}:{game['s2']}",
                    "чем взято": by_mention[pair][0]["line"][:120],
                    "комментарий": post_url(topic, by_mention[pair][0]["comment_id"])})

        group_rows, shown = [], {}
        for leg in legs:
            if id(leg) in proven:
                continue
            key = game_key(leg["a"], leg["b"], leg["s1"], leg["s2"])
            entry = {"турнир": meta["title"], "пара": list(leg["pair"]),
                     "счёт": f"{leg['s1']}:{leg['s2']}",
                     "комментарий": post_url(topic, leg["comment_id"])}
            first = shown.get(key)
            if first is not None:
                # Тот же результат той же пары вторым рядом не идёт — и неважно, выложил его
                # другой человек или тот же в том же комментарии («0:5 0:5» это дома и в гостях,
                # а «2:0 (5:0, 5:0)» — две серии одной встречи; различить их источник не может).
                # Импортёр бы такую строку спрятал как дубль, поэтому решение видно здесь, в отчёте.
                report["повторы показов"].append({**entry, "почему": f"та же пара и тот же счёт, "
                                                                     f"что уже показаны в комментарии {first}"})
                continue
            shown.setdefault(key, leg["comment_id"])
            if not meta["grid"]:
                report["вне сетки"].append({**entry, "почему": "отчёт есть, в сетке такой встречи нет"})
                continue
            if key in frame_keys:
                report["повторы показов"].append({**entry, "почему": "нога уже лежит в рамке документа"})
                continue
            letter = groups.get(leg["a"]) or groups.get(leg["b"])
            game = {"stage": f"Группа {letter}" if letter else "Групповой тур",
                    "league": "Групповой этап",
                    "a": leg["a"], "b": leg["b"], "s1": leg["s1"], "s2": leg["s2"],
                    "number": f"{leg['comment_id']}#{leg['a']}-{leg['b']}#{len(group_rows) + 1}",
                    "line": leg["line"]}
            group_rows.append(row_of(game, meta["title"], topic, leg, groups))

        bracket_rows = []
        for game in games:
            if in_frame(game):
                continue
            proof = proofs.get(id(game))
            hint = FRAME_HINT.get((meta["title"], game["stage"]))
            bracket_rows.append(row_of(game, meta["title"], topic, proof, groups, hint))
            if game["s1"] is None:
                report["без счёта"].append({"турнир": meta["title"], "этап": game["stage"],
                                            "стороны": [game["a"], game["b"]],
                                            "в сетке": "только стороны, ячейки счёта пусты"})
                continue
            if proof is None:
                report["без отчёта"].append({"турнир": meta["title"], "этап": game["stage"],
                                             "стороны": [game["a"], game["b"]],
                                             "счёт": f"{game['s1']}:{game['s2']}"})

        rows += group_rows + bracket_rows
        for item in unparsed:
            report["не распознано"].append({"турнир": meta["title"], "комментарий": item["comment_id"],
                                            "строка": item["line"], "почему": item["why"]})
        report["турниры"][meta["title"]] = {
            "встреч в сетке": len(games),
            "уже в рамке": len(frame),
            "новых по сетке": len(bracket_rows),
            "с доказательством": len(proofs),
            "игр группового тура": len(group_rows),
            "ног в комментариях": len(legs),
            "игроков в заявке": len(players),
        }
    return rows, report
