"""Сверка живой выгрузки VK с базой матчей: файл расхождений на решение редактору.

Ничего не пишет в базу. Читает `data/vk_dump_<date>/` (сырьё `collectors/vk_recheck.py`) и
`data/nst.db`, разбирает комментарии обсуждений теми же регулярками, что архивный
`collectors/extract_all_vk_season_matches.py`, и сравнивает с тем, что лежит в базе.

Как найти, о каком турнире речь. Живой топик и база называют одну игру по-разному
(«X Юбилейный Блиц-турнир по гол3 (сольный)» против «X Юбилейный Блиц-турнир по Goal 3»,
«Третий сольный турнир по пенальти» против «3-й Сольный Турнир по пенальти»), поэтому
сверка идёт по подписи: (формат, номер, дисциплина). Сезоны берутся прямо из
`TOPIC_MAP_BY_NAME`, где id обсуждения уже связан с номером сезона.

Дальше сравнение постраничное, и только внутри одного турнира:
  * пара и счёт совпали                     → расхождения нет;
  * пара есть, счёт другой                  → `score_diff`;
  * ни пары, ни счёта                       → `missing_in_db` (игру не занесли);
  * строка базы не всплывает ни в одном комментарии → `missing_in_source`;
  * написания нет в `players`               → `unknown_name` (алиас, а не новый игрок).

Наружу — `data/vk_recheck_<date>.md` (читать человеку) и `.json` с теми же элементами и
полем `kind`, чтобы после решения «применяй п. N» правки шли по машинному списку.
"""

import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.vk_recheck import FOREIGN, SOCCER, dump_dir, select_topics  # noqa: E402
from portal.name_tables import TOPIC_MAP_BY_NAME  # noqa: E402
from portal.names import clean_alias  # noqa: E402

GROUP_ID = 66162180
# Отчёт привязан к дате выгрузки, а не к сегодняшнему числу: обход живёт дольше суток.
DUMP = dump_dir()
TODAY = DUMP.name.removeprefix("vk_dump_")
MD_OUT = ROOT / "data" / f"vk_recheck_{TODAY}.md"
JSON_OUT = ROOT / "data" / f"vk_recheck_{TODAY}.json"

# Те же два шаблона, что у архивного разборщика: «A vs B - 3:1» и «A - B 3:1» с хвостом (OT/ПК).
# Сторона умеет быть парой: командник 2×2 и молодёжный чемпионат пишут «lenin1st & ectoPower»,
# иначе эти турниры вообще не разбирались бы и тоннули в «нет в базе».
SIDE = r"[A-Za-zА-Яа-я0-9_]{3,18}(?:\s*[&/]\s*[A-Za-zА-Яа-я0-9_]{3,18})?"
MATCH_REGEXES = [
    re.compile(
        rf"({SIDE})\s+(?:vs|против|-)\s+({SIDE})\s*[:\-–]\s*(\d+)\s*[:\-–]\s*(\d+)"
        r"(?:\s*\(([^)]{0,40})\))?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"({SIDE})\s+(?:vs|против|-)\s+({SIDE})\s+(\d+)\s*[:\-–]\s*(\d+)"
        r"(?:\s*\(([^)]{0,40})\))?",
        re.IGNORECASE,
    ),
]
BANNED = {"тур", "матч", "лига", "тайм", "счет", "счёт", "игра", "итог", "видео", "ютуб", "старт",
          "первый", "второй", "третий", "группа", "состав", "регистр", "турнир", "рейтинг",
          "таблица", "полуфинал", "финал", "ссылка", "результат", "номер", "года", "году"}
VIDEO_IN_TEXT = re.compile(r"(?:https?://)?(?:vk\.ru|vk\.com|www\.youtube\.com|youtube\.com)/(?:video|clip)\S+")

ROMAN = {v: str(i) for i, v in enumerate(
    ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv",
     "xv", "xvi", "xvii", "xviii", "xix", "xx", "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi"], 1)}
WORDS = {"перв": "1", "втор": "2", "вотор": "2", "трет": "3", "четвёр": "4", "четвер": "4",
         "пят": "5", "шест": "6", "седьм": "7", "восьм": "8", "девят": "9", "десят": "10",
         "одиннадцат": "11", "двенадцат": "12", "тринадцат": "13", "четырнадцат": "14"}
FORMATS = [("молодёж", "молодёжный"), ("молодеж", "молодёжный"), ("командн", "командный"),
           ("блиц", "блиц"), ("пенальт", "пенальти"), ("межсезон", "клубный"), ("клубн", "клубный"),
           ("минибатл", "минибатлы"), ("рейтинг", "рейтинг"), ("кубок", "кубок"),
           ("сольн", "сольный"), ("регуляр", "сезон"), ("сезон", "сезон"), ("season", "сезон"),
           ("чемпионат", "сезон")]

GAMES = [("goal 4", "goal4"), ("goal4", "goal4"), ("гол4", "goal4"), ("гол 4", "goal4"),
         ("goal 3", "goal3"), ("goal3", "goal3"), ("гол3", "goal3"), ("гол 3", "goal3"),
         ("nekketsu soccer", "goal3"), ("soccer league", "goal3"), ("soccer hen", "goal3"),
         ("soccer", "goal3")]
def post_url(topic, cid, pos):
    """Ссылка, по которой VK открывает нужную страницу обсуждения и прокручивает к комментарию.

    Формат проверен в браузере: страница обсуждения отдаёт 20 комментариев, поэтому offset —
    это индекс комментария, округлённый вниз до двадцатки, а якорь `#post<id>` доскачивает до
    строки. Без offset ссылка прыгает на первую страницу, и человек не видит, о чём речь.
    """
    return f"https://vk.com/topic-{GROUP_ID}_{topic}?offset={(int(pos or 0) // 20) * 20}#post{cid}"
# Кириллические близнецы латинских букв: именно они рождают в архиве «BOР95» и «СentZloy».
HOMO = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ѕ": "s",
    "в": "b", "к": "k", "н": "h", "т": "t", "м": "m", "ј": "j", "ԁ": "d",
})


def signature(title):
    """(формат, номер, дисциплина) из названия — то, по чему живой топик и строка базы сходятся.

    Номер ищем по названию, уже очищенному от упоминаний игры и года: в «Клубный Чемпионат
    по Goal 4. МЕЖСЕЗОНЬЕ» четвёрка — это часть названия игры, а не номер розыгрыша.
    """
    raw = re.sub(r"[^\wа-яё\s]", " ", str(title).lower())
    game = next((name for key, name in GAMES if key in raw), "")
    low = re.sub(r"(goal ?\d+|гол ?\d+|nekketsu soccer league|soccer league|soccer hen"
                 r"|\b(19|20)\d{2}\b|\([^)]*\))", " ", raw)
    number = ""
    for token in low.split():
        if token.isdigit():
            number = str(int(token))
            break
        if token in ROMAN:
            number = ROMAN[token]
            break
    if not number:
        for word, digit in WORDS.items():
            match = re.search(rf"\b{word}\w*", low)
            if match:
                number = digit
                break
    fmt = next((name for key, name in FORMATS if key in low), "")
    return fmt, number, game


def describe(sig):
    fmt, number, game = sig
    return " ".join(x for x in (fmt, f"№{number}" if number else "", game or "")).strip() or "—"


def player_of(name, nicknames, lowered):
    """Написание → ник из базы: справочник алиасов, затем поиск по «сложенному» написанию.

    Складка нужна из-за гомоглифов: в базе живут ники с кириллической «Р» («BOР95») и «С»
    («СentZloy»), а в комментариях те же люди пишутся латиницей. Без складки один и тот же
    игрок давал бы две разные пары, и настоящие игры попадали бы в «нет в базе».
    """
    canonical = clean_alias(name) or name
    canonical = canonical.strip().strip("*.,_()[]")
    if canonical in nicknames:
        return canonical
    folded = fold(canonical)
    hit = lowered.get(folded)
    if hit:
        return hit
    # «RVD» в комментариях — это «RVD (МГБ)» из базы: префикс с уточнением в скобках
    prefixed = [nick for nick in nicknames if fold(nick).startswith(folded + " (")]
    return prefixed[0] if len(prefixed) == 1 else None


def fold(text):
    """Нижний регистр плюс замена кириллических гомоглифов латинскими."""
    return str(text).lower().translate(HOMO)


SCORE_TOKEN = re.compile(r"(\d{1,2})\s*[:\-–]\s*(\d{1,2})")
EXAMPLE_MARK = re.compile(r"ПРИМЕР\s+(ВЫКЛАДЫВАНИЯ|ОФОРМЛЕНИЯ)", re.IGNORECASE)
SERIES_MARK = re.compile(r"(пк|рк|пен|буллит|pk|rk|shootout|серия)", re.IGNORECASE)


def without_examples(text):
    """Вырезать блок «ПРИМЕР ВЫКЛАДЫВАНИЯ РЕЗУЛЬТАТОВ», который печатается в шапке каждой темы.

    Это образец оформления, а не протокол: в темах Сезонов 2–7 он повторяется слово в слово
    («ВЛ 1-й тур. Memori vs Centurion - 3:0, 8:5пен.»), и однажды из него выросла выдуманная игра
    в каждом сезоне. Блок заканчивается первой строкой без счёта и без короткого заголовка тура.
    """
    kept, skipping = [], False
    for line in text.split("\n"):
        if EXAMPLE_MARK.search(line):
            skipping = True
            continue
        if skipping:
            stripped = line.strip()
            looks_like_fixture = SCORE_TOKEN.search(stripped) or len(stripped) <= 20
            if looks_like_fixture and stripped:
                continue
            skipping = False
        kept.append(line)
    return "\n".join(kept)


def legs_of(tail):
    """Ноги встречи в хвосте строки.

    Скобка значит разное в зависимости от наполнения: одна счёт-пара в скобках — это то, чем
    доиграли уже названную ногу (золотой гол, как требует регламент: «5-5 (1-0)», или серия
    пенальти: «1-1 (4-3 пен)»), а несколько — сам перечень ног, перед которым стоит итог встречи
    («ectoPower vs PacnyTHuK - 3:5 (3:1, 4:2, 1:3, 0:2)»). Итог отдельной игрой не бывает.

    Вне скобок нога от ноги отделяется запятой: «3:0, 8:5пен» — это вторая нога, выигранная по
    пенальти (так объясняет сам регламент темы). Если же между счёт-парами стоит слово серии и
    нет запятой — «6-6 PK 5:4» — второй счёт это серия первой ноги, а не игра.
    """
    groups = [SCORE_TOKEN.findall(inner) for inner in re.findall(r"\(([^()]*)\)", tail)]
    listed = [(int(a), int(b)) for group in groups if len(group) > 1 for a, b in group]
    if listed:
        return listed
    outside = re.sub(r"\([^)]*\)", " ", tail)
    legs, previous_end = [], None
    for hit in SCORE_TOKEN.finditer(outside):
        gap = outside[previous_end:hit.start()] if previous_end is not None else ""
        previous_end = hit.end()
        if SERIES_MARK.search(gap) and not re.search(r"[,;]", gap):
            continue
        legs.append((int(hit.group(1)), int(hit.group(2))))
    return legs


def parse_comment(text):
    """Строки «пара — счёт» из комментария.

    Встреча 2×2 и молодёжного турнира пишется серией в одну строку:
    `2 тур: SaikoDelph & Jgunishka VS Aoshi & Aeris 5-2; 3-4; 0-5; 2-2 (PK 3-2)` — это четыре
    ноги одной встречи, а не один матч. Берём счёт-пары после стороны, но не всякие: что именно
    считать ногой, объясняет `legs_of`, а шаблон из шапки темы отрезает `without_examples`.
    """
    found = []
    for chunk in re.split(r"[\n;]", without_examples(text)):
        chunk = chunk.strip()
        if not chunk:
            continue
        for rx in MATCH_REGEXES:
            for hit in rx.finditer(chunk):
                left, right = hit.group(1), hit.group(2)
                tokens = [t.strip().lower() for side in (left, right) for t in re.split(r"[&/]", side)]
                if any(t in BANNED for t in tokens) or not all(tokens):
                    continue
                legs = legs_of(chunk[hit.end(2):])
                legs = [(a, b) for a, b in legs if a <= 30 and b <= 30 and (a, b) != (0, 0)]
                if not legs:
                    continue
                note = (chunk + " " + (hit.group(5) or "")).lower()
                for index, (s1, s2) in enumerate(legs[:6], 1):
                    found.append({
                        "line": chunk[:140],
                        "raw": (left, right),
                        "scores": (s1, s2),
                        "leg": f"{index}/{len(legs)}",
                        "note": note,
                        "ot": "ot" in note or "овертайм" in note,
                        "pk": any(k in note for k in ("pk", "рк", "пк", "пен", "буллит")),
                    })
    return found


def load_live():
    """Комментарии футбольных обсуждений. Прочие дисциплины клуба (Tecmo, NHL94, Contra, шахматы)
    в сверку матчей не берём: они не имели отношения к Goal 3 никогда.
    """
    folder = DUMP / "comments"
    topics_file = DUMP / "topics.json"
    allowed = None
    if topics_file.exists():
        allowed = {str(t["id"]) for t in select_topics(json.loads(topics_file.read_text(encoding="utf-8")),
                                                       "soccer", None)}
    picked = {}
    total = 0
    for path in sorted(folder.glob("*.json")):
        blob = json.loads(path.read_text(encoding="utf-8"))
        topic = blob["topic"]
        total += 1
        tid = str(topic["id"])
        if allowed is not None and tid not in allowed:
            continue
        ordered = sorted(blob["comments"], key=lambda c: c.get("date", 0))
        for position, comment in enumerate(ordered):
            comment["pos"] = position
        picked[tid] = {"title": topic.get("title", ""),
                       "comments": {str(c["id"]): c for c in ordered}}
    return picked, total


def load_base(con):
    """Единицы сравнения: лиги и кубки — это `tournaments`, спец- и командные турниры — `tournament_docs`.

    Строки спецтурниров лежат и в том, и в другом (у матча есть и `tournament_id`, и `doc_id`),
    поэтому строку относим к документу, если он указан: иначе одна и та же игра учитывалась бы
    дважды и выдавала бы фантомные совпадения.
    """
    units = {}
    for row in con.execute("select id, name, season, kind from tournaments"):
        units[("t", row["id"])] = {"key": ("t", row["id"]), "origin": "t", "name": row["name"],
                                   "season": row["season"], "kind": row["kind"],
                                   "sig": tournament_signature(dict(row)), "rows": []}
    for row in con.execute("select id, kind, json_extract(payload, '$.title') as title from tournament_docs"):
        units[("d", row["id"])] = {"key": ("d", row["id"]), "origin": "d", "name": row["title"],
                                   "season": "", "kind": row["kind"],
                                   "sig": signature(row["title"]), "rows": []}
    # Состав и подпись стороны читаются раздельно: «Кубик & Snipe» — то, что показал источник,
    # a `Kubik` — как тот же игрок лежит в базе. См. `pair_keys`.
    sql = """
    select m.id, m.tournament_id as tid, m.doc_id, m.row_set, m.tour, m.league, m.played_on,
           m.status, m.manual, m.hidden_by, m.duplicate_of, m.source, m.note,
           sa.score as s1, sb.score as s2,
           sa.label as la, sb.label as lb,
           (select group_concat(p.nick, ' & ') from side_players sp
              join players p on p.id = sp.player_id where sp.side_id = sa.id) as na,
           (select group_concat(p.nick, ' & ') from side_players sp
              join players p on p.id = sp.player_id where sp.side_id = sb.id) as nb,
           (select group_concat(l.url, ' ') from match_links l where l.match_id = m.id) as urls
    from matches m
    join match_sides sa on sa.match_id = m.id and sa.side_index = 0
    join match_sides sb on sb.match_id = m.id and sb.side_index = 1
    where m.tournament_id is not null or m.doc_id is not null
    """
    for r in con.execute(sql):
        key = ("d", r["doc_id"]) if r["doc_id"] else ("t", r["tid"])
        unit = units.get(key)
        if unit is None:
            continue
        shown = {"a": r["la"] or r["na"], "b": r["lb"] or r["nb"]}
        unit["rows"].append({
            "id": r["id"], "row_set": r["row_set"], "tour": r["tour"], "league": r["league"],
            "played_on": r["played_on"], "status": r["status"], "manual": r["manual"],
            "hidden_by": r["hidden_by"], "duplicate_of": r["duplicate_of"], "source": r["source"],
            "note": r["note"], "scores": (r["s1"], r["s2"]),
            "sides": (sides_of(r["na"] or shown["a"]), sides_of(r["nb"] or shown["b"])),
            "labeled": (sides_of(r["la"]), sides_of(r["lb"])),
            "a": shown["a"], "b": shown["b"], "urls": r["urls"] or "",
        })
    return units


def sides_of(label):
    """Сторона как набор имён: «lenin1st & ectoPower» → два игрока.

    Чем склеена строка — не важно: так `group_concat` ников, так и подпись источника.
    """
    parts = [p.strip() for p in re.split(r"\s*&\s*|/", str(label or "")) if p.strip()]
    return tuple(sorted(parts))


def pair_keys(row):
    """Ключи, под которыми строка базы находится.

    Источник называет сторону своими словами, база хранит её двумя способами: состав из
    канонических ников и подпись, как её показал источник («Кубик & Snipe» против `Kubik`).
    Гомоглиф в подписи не сворачивается в ник, поэтому поиск только по одному из них терял
    целые лиги: средняя лига VI Командного считалась отсутствующей, хотя все её встречи в базе.
    """
    keys = []
    for sides in (row["sides"], row.get("labeled") or ()):
        if not all(sides):
            continue
        key = tuple(sorted([tuple(sorted(fold(name) for name in side)) for side in sides]))
        if key not in keys:
            keys.append(key)
    return keys


def score_key(scores):
    """Счёт как ключ: у строк с надписью словами («Победа X/Y») чисел нет, и None сортировке не поддаётся."""
    return tuple(sorted(value if value is not None else -1 for value in scores))


ARCHIVE_NAMES = {"season": "сезон", "team": "командный", "youth": "молодёжный",
                 "penalty": "пенальти", "club": "клубный"}


def season_by_topic():
    """id обсуждения → подпись из справочника топиков (`TOPIC_MAP_BY_NAME`).

    Одно и то же обсуждение записано там несколькими именами («youth 2», «молодёжный»,
    «молодежный»), поэтому оставляем самую подробную вариант — тот, где есть номер.
    """
    map_ = {}
    for name, tid in TOPIC_MAP_BY_NAME.items():
        words = " ".join(ARCHIVE_NAMES.get(word, word) for word in name.lower().split())
        sig = signature(words)
        if not sig[0]:
            continue
        current = map_.get(str(tid))
        if current is None or (not current[1] and sig[1]):
            map_[str(tid)] = sig
    return map_


def tournament_signature(t):
    """Подпись турнира базы: `kind` и `season` надёжнее названия — «Season 4 Высшая лига»
    по тексту названия вообще не читается по-русски, а это девять сезонов лиги."""
    match = re.search(r"(\d+)", str(t["season"] or ""))
    if t["kind"] == "league" and match:
        return "сезон", str(int(match.group(1))), "goal3"
    if t["kind"] == "cup" and match:
        return "кубок", str(int(match.group(1))), "goal3"
    return signature(t["name"])


def unit_targets(sig, units):
    """Единицы базы, которые соответствуют подписи обсуждения.

    Сезон — это не один турнир: у «Soccer League. 4-й сезон» в базе три лиги и кубок, поэтому
    для «сезон N» берём все единицы этого номера. Остальные форматы ищем по подписи целиком,
    а затем по паре «формат + номер» — и только если вариант ровно один.
    """
    fmt, number, _game = sig
    if not fmt:
        return []
    if fmt == "сезон" and number:
        return [u["key"] for u in units.values() if u["sig"][0] in ("сезон", "кубок") and u["sig"][1] == number]
    exact = [u["key"] for u in units.values() if u["sig"] == sig]
    if exact:
        return exact
    # Подпись из справочника топиков («team 4») не знает дисциплины, поэтому ищем по паре
    # «формат + номер». Турнир и его документ дают двух кандидатов: выбираем документ, потому
    # что строки лежат у него, а запись `tournaments` пуста по построению.
    loose = [u for u in units.values() if u["sig"][:2] == (fmt, number) and number]
    docs = [u for u in loose if u["origin"] == "d"]
    if docs:
        return [u["key"] for u in docs]
    return [u["key"] for u in loose] if len(loose) == 1 else []


def match_tournaments(live, units, con):
    """Живой топик → набор единиц базы плюс счётчик ссылок базы на это обсуждение."""
    linked = {}
    for row in con.execute("select url from match_links where url like '%topic-66162180_%'"):
        for tid in re.findall(rf"topic-{GROUP_ID}_(\d+)", row["url"]):
            linked.setdefault(tid, set()).add(row["url"])
    nick_season = season_by_topic()
    pairs = {}
    for tid, topic in live.items():
        sig = nick_season.get(tid) or signature(topic["title"])
        pairs[tid] = {"title": topic["title"], "sig": sig, "units": unit_targets(sig, units),
                      "links_in_db": len(linked.get(tid, ()))}
    return pairs


def load_wiki():
    """Вычитанные браузером вики-страницы: `data/vk_dump_<дата>/wiki_browser/<id>.json`."""
    folder = DUMP / "wiki_browser"
    if not folder.exists():
        return {}
    pages = {}
    for path in sorted(folder.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        pages[str(page["id"])] = page
    return pages


ROW_PAIR = re.compile(r"^(.{3,60}?)\s*(?:--|—|–|\bvs\.?\b|\bпротив\b)\s*(.{3,60}?)\s*$", re.IGNORECASE)
ROW_SCORE = re.compile(r"(\d{1,2})\s*[-:]\s*(\d{1,2})")
TOUR_HEAD = re.compile(r"(\d{1,2})\s*тур|тур\s*(\d{1,2})", re.IGNORECASE)


def _cell(value):
    """Ячейка вики-таблицы. Выгрузка знает два формата: строка и тройка `[текст, ссылки, текст]`.

    Без нормализации разбор падал на двадцати страницах из сорока четырёх: `" ".join(cells)`
    не переваривает вложенный список, а `cells[0]` в тройке — это уже не текст строки.
    """
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else ""
    return str(value)


def wiki_rows(page):
    """Встречи с вики-таблицы сезона.

    Структура страницы честная: строка-заголовок тура («1 Тур - 28.03. Гвинея, трава»), потом
    строки вида `['ArmFly -- Transistor', '0-5', '4-9', 'видео']` — то есть **две ноги** одной
    встречи, а не один матч. Именно эта вторая нога и терялась при ручном переносе в носитель.
    """
    rows = []
    tour = ""
    for table in page.get("tables") or []:
        for raw_cells in table:
            cells = [_cell(value) for value in raw_cells]
            if not cells:
                continue
            head = " ".join(cells).strip()
            pair = ROW_PAIR.match(cells[0]) if cells else None
            if not pair:
                if TOUR_HEAD.search(head):
                    tour = (TOUR_HEAD.search(head).group(1) or TOUR_HEAD.search(head).group(2)).strip()
                continue
            legs = []
            for cell in cells[1:]:
                # Скобки — это послематчевые пенальти («4:4 (6:5 PK)»), отдельной ногой они не являются
                for a, b in ROW_SCORE.findall(re.sub(r"\([^)]*\)", " ", cell)):
                    legs.append(((int(a), int(b)), cell.strip()))
            for (s1, s2), leg_note in legs[:6]:
                if s1 > 30 or s2 > 30:
                    continue
                rows.append({"line": head[:150], "tour": tour, "raw": (pair.group(1), pair.group(2)),
                             "scores": (s1, s2), "note": leg_note, "leg": f"{len(legs)} ног"})
    return rows


def resolve_sides(raw_pair, nicknames, lowered):
    """«A & B» / «A» → канонические ники базы; то, что не сверилось, возвращается отдельно."""
    sides, unresolved = [], []
    for raw in raw_pair:
        members = []
        for token in re.split(r"[&/]", raw or ""):
            token = token.strip()
            if not token:
                continue
            nick = player_of(token, nicknames, lowered)
            (members.append(nick) if nick else unresolved.append(token))
        sides.append(tuple(sorted(members)))
    return sides, unresolved


def main():
    if not DUMP.exists() or not (DUMP / "comments").exists():
        sys.exit(f"нет выгрузки комментариев в {DUMP} — сначала collectors/vk_recheck.py comments")
    con = sqlite3.connect(ROOT / "data" / "nst.db")
    con.row_factory = sqlite3.Row
    nicknames = {r[0] for r in con.execute("select nick from players")}
    lowered = {fold(r[0]): r[0] for r in con.execute("select nick from players")}
    live, all_topics = load_live()
    units = load_base(con)
    pairs = match_tournaments(live, units, con)

    # Глобальные индексы по всей базе. Без них любая строчка из прогноза или цитаты чужого
    # тура выглядела бы как «игры нет в базе»: игра может лежать в другом документе того же
    # сезона (вики-таблица, сводка плей-офф), и это другой разговор, а не потеря.
    global_scores = defaultdict(list)
    global_pairs = defaultdict(list)
    for unit in units.values():
        for row in unit["rows"]:
            for pair in pair_keys(row):
                global_scores[(pair, score_key(row["scores"]))].append({"id": row["id"], "unit": unit["name"]})
                global_pairs[pair].append({"id": row["id"], "unit": unit["name"],
                                           "scores": row["scores"], "tour": row["tour"]})

    issues = defaultdict(list)
    matched_lines = 0
    for tid, info in sorted(pairs.items(), key=lambda kv: kv[1]["title"]):
        topic = live[tid]
        rows = [r for key in info["units"] for r in units[key]["rows"]]
        if info["units"] and not rows:
            issues["empty_tournament"].append({
                "topic": tid, "title": topic["title"], "comments": len(topic["comments"]),
                "tournament": ", ".join(units[key]["name"] for key in info["units"]),
                "hint": "турнир в базе заведён, но в нём ноль строк — обсуждение есть, данных нет",
            })
            continue
        if not rows:
            issues["unmatched_topic"].append({
                "topic": tid, "title": topic["title"], "comments": len(topic["comments"]),
                "signature": describe(info["sig"]),
                "hint": "ни один турнир базы не совпал с обсуждением по формату и номеру",
            })
            continue
        by_pair = defaultdict(list)
        for row in rows:
            for pair in pair_keys(row):
                by_pair[pair].append(row)
        seen_rows = set()
        asserted = Counter()
        unnamed = set()
        for cid, comment in sorted(topic["comments"].items(), key=lambda kv: int(kv[1].get("date", 0))):
            text = comment.get("text") or ""
            day = date.fromtimestamp(comment["date"]).isoformat() if comment.get("date") else None
            for item in parse_comment(text):
                sides, unresolved = resolve_sides(item["raw"], nicknames, lowered)
                if unresolved:
                    # Один и тот же нераспознанный ник в строке с четырьмя ногами — это одна
                    # находка, а не четыре: счёт идёт по парам, иначе раздел раздувается.
                    key = (cid, tuple(item["raw"]))
                    if key not in unnamed:
                        unnamed.add(key)
                        issues["unknown_name"].append({
                            "topic": tid, "title": topic["title"], "comment_id": cid,
                            "line": item["line"], "unresolved": unresolved,
                            "url": post_url(tid, cid, comment.get("pos")),
                            "hint": "написания нет в players — это алиас, а не новый игрок",
                        })
                    continue
                pair = tuple(sorted([tuple(sorted(fold(name) for name in side)) for side in sides]))
                candidates = by_pair.get(pair, [])
                scored = [c for c in candidates
                          if score_key(c["scores"]) == score_key(item["scores"])]
                signature_key = (pair, score_key(item["scores"]))
                if signature_key in asserted:
                    asserted[signature_key] += 1
                    continue
                asserted[signature_key] = 1
                if scored:
                    matched_lines += 1
                    seen_rows.update(c["id"] for c in scored)
                    continue
                base_entry = {
                    "topic": tid, "title": topic["title"], "comment_id": cid,
                    "comment_day": day, "line": item["line"], "leg": item["leg"],
                    "source_pair": [list(s) for s in sides], "scores": list(item["scores"]),
                    "url": post_url(tid, cid, comment.get("pos")),
                }
                if candidates:
                    c = candidates[0]
                    seen_rows.add(c["id"])
                    issues["score_diff"].append({
                        **base_entry,
                        "base": {"id": c["id"], "tour": c["tour"], "scores": list(c["scores"]),
                                 "status": c["status"], "manual": c["manual"], "a": c["a"], "b": c["b"]},
                        "hint": "та же пара в этом турнире, но счёт другой",
                    })
                elif global_scores.get(signature_key):
                    hits = global_scores[signature_key]
                    issues["matched_elsewhere"].append({
                        **base_entry,
                        "base": {"id": hits[0]["id"], "unit": hits[0]["unit"]},
                        "hint": "игра в базе есть, но в другом документе — сверьте, что это не дубль",
                    })
                elif global_pairs.get(pair):
                    other = global_pairs[pair][0]
                    issues["score_diff"].append({
                        **base_entry,
                        "base": {"id": other["id"], "tour": other["tour"], "scores": list(other["scores"]),
                                 "unit": other["unit"]},
                        "hint": "такая пара в базе есть, но в другом турнире и с другим счётом",
                    })
                else:
                    issues["missing_in_db"].append({
                        **base_entry,
                        "shape": f"{len(sides[0])}×{len(sides[1])}",
                        "tournament": {"units": [units[k]["name"] for k in info["units"]], "rows": len(rows)},
                        "hint": ("ни в этом турнире, ни где-либо в базе такой пары нет"
                                 + (" — форма 2×2: похоже на командный турнир, а не на сезон"
                                    if max(len(sides[0]), len(sides[1])) > 1 else "")),
                    })
                videos = VIDEO_IN_TEXT.findall(text)
                for c in candidates[:1]:
                    if not videos:
                        break
                    have = {h.split("//")[-1].rstrip(".,") for h in c["urls"].split()}
                    fresh = [v.split("//")[-1].rstrip(".,") for v in videos
                             if v.split("//")[-1].rstrip(".,") not in have]
                    if fresh:
                        issues["video_link"].append({
                            "topic": tid, "title": topic["title"], "comment_id": cid,
                            "base": {"id": c["id"], "a": c["a"], "b": c["b"]},
                            "missing": fresh[:3], "hint": "в комментарии есть видео, в базе его нет",
                        })
        if not seen_rows:
            issues["no_lines_recognised"].append({
                "topic": tid, "title": topic["title"],
                "tournament": ", ".join(units[k]["name"] for k in info["units"]),
                "rows": len(rows), "comments": len(topic["comments"]),
                "hint": "ни одна строка турнира не узнана в комментариях — вероятно, источник другой (вики-таблица)",
            })

    # Вики-календари: те же встречи, но разложенные по ногам. База собрана из этих страниц
    # руками, поэтому сравнение живьём показывает и потерянные ноги, и ошибки переноса.
    wiki_inventory = []
    skipped_pages = 0
    for pid, page in sorted(load_wiki().items()):
        title = str(page.get("title") or "")
        if not SOCCER.search(title) or FOREIGN.search(title):
            skipped_pages += 1
            continue
        found = wiki_rows(page)
        if not found:
            continue
        counts = Counter()
        for row in found:
            sides, unresolved = resolve_sides(row["raw"], nicknames, lowered)
            if unresolved:
                counts["unknown"] += 1
                continue
            pair = tuple(sorted([tuple(sorted(fold(name) for name in side)) for side in sides]))
            key = (pair, score_key(row["scores"]))
            if key in global_scores:
                counts["matched"] += 1
                continue
            item = {
                "page": pid, "title": page.get("title", "")[:70], "tour": row["tour"],
                "line": row["line"], "source_pair": [list(s) for s in sides],
                "scores": list(row["scores"]), "note": row["note"],
                "url": f"https://vk.com/page-{GROUP_ID}_{pid}",
            }
            if pair in global_pairs:
                other = global_pairs[pair][0]
                counts["differs"] += 1
                issues["wiki_score_diff"].append({**item, "base": {"id": other["id"], "tour": other["tour"],
                                                                "scores": list(other["scores"]),
                                                                "unit": other["unit"]},
                                                "hint": "нога встречи есть в базе другим счётом"})
            else:
                counts["missing"] += 1
                issues["wiki_missing_in_db"].append({**item,
                                                    "hint": "такой пары нет в базе ни с каким счётом"})
        wiki_inventory.append({"pid": pid, "title": page.get("title", "")[:60], "rows": len(found),
                              **counts})

    # Пустые единицы базы целиком: только документы и лиги/кубки. Турниры формата special/team
    # существует в паре с документом, и их строки уходят документу, поэтому сами по себе они
    # пустые по построению — пугать этим читателя не нужно.
    for unit in units.values():
        if unit["rows"]:
            continue
        if unit["origin"] == "t" and unit["kind"] in ("special", "team"):
            continue
        issues["empty_unit"].append({"title": unit["name"], "kind": unit["kind"],
                                     "hint": "турнир в базе заведён, строк ноль"})

    # Два написания одного игрока внутри самой базы: гомоглифы, регистр, «ss»/«ssss».
    variants_by_fold = defaultdict(list)
    for nick in sorted(nicknames):
        variants_by_fold[fold(nick)].append(nick)
    for folded, variants in sorted(variants_by_fold.items()):
        if len(variants) > 1:
            issues["nick_twins"].append({"folded": folded, "variants": variants,
                                         "hint": "в `players` несколько ников на один slug — это чинят алиасом"})

    order = ("missing_in_db", "score_diff", "wiki_missing_in_db", "wiki_score_diff",
             "matched_elsewhere", "unmatched_topic", "empty_tournament", "empty_unit",
             "unknown_name", "nick_twins", "video_link", "no_lines_recognised")
    counts = {k: len(issues[k]) for k in order}
    stats = {"обсуждений в выгрузке всего (все дисциплины клуба)": all_topics,
             "футбольных обсуждений в сверке": len(live),
             "комментариев": sum(len(t["comments"]) for t in live.values()),
             "единиц базы (турниры и документы)": len(units),
             "вики-страниц вычитано": len(wiki_inventory) + skipped_pages,
             "вики-страниц не про футбол": skipped_pages,
             "строк базы в сопоставленных единицах": len({r["id"] for v in pairs.values()
                                                          for k in v["units"] for r in units[k]["rows"]}),
             "строк источника, совпавших с базой": matched_lines}
    JSON_OUT.write_text(json.dumps({
        "generated": TODAY,
        "stats": stats,
        "counts": counts,
        "topics": {tid: {"title": v["title"], "signature": describe(v["sig"]),
                         "units": [units[k]["name"] for k in v["units"]]} for tid, v in pairs.items()},
        "wiki": wiki_inventory,
        "items": {k: issues[k] for k in order},
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # Опись по обсуждениям: что за турнир, сколько строк в базе, сколько ног нашли в
    # комментариях и сколько из них не сошлось. Читается раньше деталей — по ней видно,
    # куда вообще смотреть.
    per_topic = defaultdict(Counter)
    for key in ("missing_in_db", "score_diff", "matched_elsewhere"):
        for item in issues[key]:
            per_topic[item["topic"]][key] += 1
    inventory = []
    for tid, info in pairs.items():
        rows = [r for key in info["units"] for r in units[key]["rows"]]
        inventory.append({
            "tid": tid, "title": info["title"], "comments": len(live[tid]["comments"]),
            "units": ", ".join(units[k]["name"] for k in info["units"]) or "—",
            "rows": len(rows), "matched": 0,
            "missing": per_topic[tid]["missing_in_db"], "diff": per_topic[tid]["score_diff"],
            "elsewhere": per_topic[tid]["matched_elsewhere"],
        })
    inventory.sort(key=lambda row: -(row["missing"] + row["diff"]))

    lines = [f"# Расхождения живого VK против базы — {TODAY}", ""]
    lines.append("## Опись обсуждений")
    lines.append("")
    lines.append("| обсуждение | в базе | строк | расхождений | ссылка |")
    lines.append("|---|---|---|---|---|")
    for row in inventory:
        link = f"https://vk.com/topic-{GROUP_ID}_{row['tid']}"
        verdict = f"нет {row['missing']} · счёт {row['diff']}" if (row["missing"] or row["diff"]) else "чисто"
        lines.append(f"| {row['title'][:58]} | {row['units'][:44]} | {row['rows']} | {verdict} | [открыть]({link}) |")
    lines.append("")
    if wiki_inventory:
        lines.append("## Вики-календари (вычитаны браузером, `pages.get` ключу недоступен)")
        lines.append("")
        lines.append("| страница | строк-встреч | совпало | нет в базе | другой счёт | вне справочника |")
        lines.append("|---|---|---|---|---|---|")
        for row in sorted(wiki_inventory, key=lambda r: -(r.get("missing", 0) + r.get("differs", 0))):
            lines.append(f"| [{row['title'][:48]}](https://vk.com/page-{GROUP_ID}_{row['pid']}) "
                         f"| {row['rows']} | {row.get('matched', 0)} | {row.get('missing', 0)} "
                         f"| {row.get('differs', 0)} | {row.get('unknown', 0)} |")
        lines.append("")
    titles = {
        "missing_in_db": "Игра есть в обсуждении, её нет в базе",
        "score_diff": "Пара та, счёт расходится",
        "wiki_missing_in_db": "Вики-календарь: ноги встречи нет в базе",
        "wiki_score_diff": "Вики-календарь: нога есть другим счётом",
        "matched_elsewhere": "Игра в базе есть, но в другом документе",
        "unmatched_topic": "Обсуждение не нашло своего турнира в базе",
        "empty_tournament": "Турнир в базе есть, строк в нём нет",
        "empty_unit": "Пустые турниры базы (все, включая те, что без обсуждения)",
        "unknown_name": "Написание игрока вне справочника",
        "nick_twins": "Два ника в players — один игрок",
        "video_link": "Видео из комментария не попало в базу",
        "no_lines_recognised": "Турнир не читается из комментариев (проверить источник)",
    }
    lines.append("| что найдено | сколько |")
    lines.append("|---|---|")
    for key in order:
        lines.append(f"| {titles[key]} | {counts[key]} |")
    lines += ["", *[f"- {k}: {v}" for k, v in stats.items()], ""]
    for key in order:
        items = issues[key]
        if not items:
            continue
        lines.append(f"## {titles[key]} ({len(items)})")
        if key in ("unknown_name", "nick_twins"):
            by_name = defaultdict(list)
            for item in items:
                for name in (item.get("unresolved") or item.get("variants")):
                    by_name[name].append(item)
            if key == "unknown_name":
                for name, examples in sorted(by_name.items(), key=lambda kv: -len(kv[1])):
                    line = examples[0]["line"]
                    lines.append(f"- **{name}** — {len(examples)} строк, пример: `{line}` "
                                 f"([комментарий]({examples[0]['url']}))")
            else:
                for item in items:
                    lines.append(f"- **{item['folded']}** → {', '.join(repr(v) for v in item['variants'])}")
            lines.append("")
            continue
        for n, item in enumerate(items, 1):
            head = f"{n}. **{item.get('title', '')}** · топик {item.get('topic')}"
            if item.get("url"):
                head += f" · [комментарий]({item['url']})"
            lines.append(head)
            if item.get("line"):
                lines.append(f"   - источник: `{item['line']}`")
            if item.get("source_pair"):
                shape = f" · форма {item['shape']}" if item.get("shape") else ""
                leg = f" · нога {item['leg']}" if item.get("leg") else ""
                lines.append(f"   - пара: {item['source_pair']}, счёт "
                             f"{item.get('scores') or item.get('source_scores')}{shape}{leg}")
            if item.get("kind") == "team" or item.get("kind") == "special":
                lines.append(f"   - это {item['kind']} в базе")
            if item.get("base"):
                b = item["base"]
                lines.append(f"   - база: {' | '.join(f'{k}={v}' for k, v in b.items() if v not in (None, '', 0))}")
            if item.get("signature"):
                lines.append(f"   - подпись обсуждения: {item['signature']}")
            tour = item.get("tournament")
            if isinstance(tour, dict):
                lines.append(f"   - турнир базы: {', '.join(tour.get('units', []))} · строк {tour.get('rows')}")
            elif tour:
                extra = f" · строк {item['rows']}" if item.get("rows") is not None else ""
                lines.append(f"   - турнир базы: {tour}{extra}")
            lines.append(f"   - {item.get('hint', '')}")
        lines.append("")
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"расхождений: {sum(counts.values())}")
    for key in order:
        print(f"   {key:22s} {counts[key]}")
    print("\n".join(["", f"{MD_OUT.name}", f"{JSON_OUT.name}"]))


if __name__ == "__main__":
    main()
