"""Живая выгрузка VK-сообщества NEKKETSU SPORTS TOURNAMENTS для сверки с базой матчей.

Что делает: `topics` (список обсуждений), `comments` (комментарии выбранных обсуждений),
`wall` (записи стены), `wiki` (тексты вики-страниц) и `docs` (список документов сообщества).
Каждый этап раскладывает сырые ответы
в `data/vk_dump_<год-месяц-день>/` и при повторном запуске пропускает уже скачанное, поэтому
обход можно обрывать и продолжать, не сжигая лимиты.

Про доступность методов, измеренную этим ключом: `board.*`, `groups.*`, `users.get`,
`wall.search`, `docs.get` работают; `pages.get` и `pages.getTitles` отвечают кодом 3
(«Unknown method») — через API вики этим ключом не читается; `wall.get` при паузе меньше
~2.5 секунд уходит в код 9 «Flood control» и отлеживает его несколько минут.

Токен берётся из `.env` (см. `.env.example`) и уходит только в заголовок `Authorization: Bearer`
— в URL его нет, значит он не попадёт ни в логи, ни в сообщения об ошибках. Ошибку метода печатаем
как `error_code` + `error_msg`, сырой ответ не выбрасываем целиком.

    python collectors/vk_recheck.py topics
    python collectors/vk_recheck.py comments --scope soccer
    python collectors/vk_recheck.py wall
    python collectors/vk_recheck.py wiki
    python collectors/vk_recheck.py comments --ids 52002075,49868493
"""

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.env_file import secret  # noqa: E402

GROUP_ID = 66162180
API = "https://api.vk.com/method/"
API_VERSION = "5.199"
PAGE = 100
PAUSE = 0.5  # пользовательский ключ живёт под лимитом ~3 запроса в секунду, wall.get требует запаса
BACKOFF = {6: 1.0, 9: 5.0, 29: 30.0, 30: 2.0}
MAX_TRIES = 5

# Дисциплины, которые в этом клубе живут бок о бок с футболом: их брать в расхождение нельзя.
FOREIGN = re.compile(
    r"tecmo|world cup|nhl ?9[48]|blades of steel|side pocket|street fighter|mortal|kontra|contra"
    r"|colin|mckinley|pocket fighter|ike ike|super spike|urban champion|exerion|iso\s?\d|basket"
    r"|шахмат|indie heat|indy heat|rush'n|general chaos|tiny toon|balloon fight|chip 'n dale"
    r"|danny sullivan|guerrilla war|tetris|ice climber|ultimate mortal|hard skill|dodgeball bu\b(?!.*soccer)"
    r"|вышибал|kakutou|\bnkd\b|хокке|баскет|файтинг|тенис|боул|sensible|bombermen|бомбермэн"
    r"|killer instinct|excitebike|exitebike|eternal champions|prisoners of war|mario\b|guerrilla"
    r"|6x6|cups?\b.*rle|нхл|cs ?1\.6|counter|chip ['’]n dale|muscle|m\.u\.s\.c\.l\.e",
    re.I,
)
# Наш футбол: Goal 3 он же Kunio-kun no Nekketsu Soccer League он же Dodgeball Bu — Soccer Hen.
# Goal 4 берём намеренно: он уже живёт в базе («Клубный Чемпионат по Goal 4. МЕЖСЕЗОНЬЕ» на 50 игр
# и «Сольный рейтинг (Ladder) по Goal 4»), поэтому отрезать его от сверки значило бы соврать.
SOCCER = re.compile(
    r"goal ?[34]|гол ?[34]|nekketsu soccer|soccer league|неккетсу soccer"
    r"|kunio-kun no nekketsu|soccer hen|soccer \(сезон|сольный чемпионат|сольный турнир"
    r"|сольный рейтинг|рейтинговый сольный|молодёжн\w* чемпионат|командный чемпионат"
    r"|командник|командный турнир|командн\w* .*(2х2|2x2)|турнир по ?пенальти|пенальти"
    r"|блиц|минибатл|межсезон",
    re.I,
)


def dump_dir():
    """Каталог выгрузки: самый свежий из существующих `vk_dump_*`, иначе — на сегодня.

    Обход живёт дольше суток (стена, вики), аresume работает только в тот же каталог: иначе
    вчерашние комментарии считаются уже скачанными, а сегодня начнётся заново.
    """
    root = ROOT / "data"
    existing = sorted(root.glob("vk_dump_*"), key=lambda p: p.name, reverse=True)
    return existing[0] if existing else root / f"vk_dump_{date.today().isoformat()}"


def call(method, token, **params):
    """Один вызов метода с тротлингом и разбором ошибок лимитов."""
    body = urllib.parse.urlencode({**params, "v": API_VERSION}).encode()
    request = urllib.request.Request(
        API + method,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "NST Almanac sync",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    for attempt in range(MAX_TRIES):
        time.sleep(PAUSE)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return {"_error": {"error_code": error.code, "error_msg": "HTTP error"}}
        except Exception as error:  # сеть могла отвалить на середине обхода — это не конец света
            return {"_error": {"error_code": -1, "error_msg": f"{type(error).__name__}: {error}"}}
        error = payload.get("error") or {}
        code = error.get("error_code")
        if code in BACKOFF:
            print(f"   {method}: код {code}, пауза {BACKOFF[code]}с (попытка {attempt + 1})")
            time.sleep(BACKOFF[code])
            continue
        if code:
            return {"_error": {"error_code": code, "error_msg": error.get("error_msg", "")}}
        return payload
    return {"_error": {"error_code": -2, "error_msg": "слишком много повторов"}}


def load_json(path, fallback=None):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return fallback


def stage_topics(token, out):
    target = out / "topics.json"
    topics, offset = [], 0
    while True:
        reply = call("board.getTopics", token, group_id=GROUP_ID, order=0, count=PAGE, offset=offset, extended=0)
        if "_error" in reply:
            print(f"topics: {reply['_error']}")
            break
        response = reply["response"]
        items = response.get("items") or []
        topics += items
        offset += PAGE
        if not items or offset >= response.get("count", 0):
            break
    target.write_text(json.dumps(topics, ensure_ascii=False), encoding="utf-8")
    print(f"топиков: {len(topics)} → {target.name}")
    return topics


def select_topics(topics, scope, ids):
    if ids:
        wanted = {str(i) for i in ids.split(",")}
        return [t for t in topics if str(t["id"]) in wanted]
    if scope == "all":
        return topics
    picked = []
    for t in topics:
        title = str(t.get("title", ""))
        if SOCCER.search(title) and not FOREIGN.search(title):
            picked.append(t)
    return picked


def stage_comments(token, out, topics):
    folder = out / "comments"
    folder.mkdir(exist_ok=True)
    total_pages = skipped = 0
    for topic in topics:
        tid = topic["id"]
        target = folder / f"{tid}.json"
        if target.exists():
            skipped += 1
            continue
        comments, offset = [], 0
        while True:
            reply = call(
                "board.getComments", token, group_id=GROUP_ID, topic_id=tid,
                need_likes=0, count=PAGE, offset=offset, sort="asc", extended=1,
            )
            if "_error" in reply:
                print(f"   топик {tid}: {reply['_error']} — остаётся недокачанным")
                break
            response = reply["response"]
            items = response.get("items") or []
            comments += items
            offset += PAGE
            total_pages += 1
            if not items or offset >= response.get("count", 0):
                break
        if comments:
            target.write_text(json.dumps({"topic": topic, "comments": comments}, ensure_ascii=False),
                              encoding="utf-8")
            print(f"   [{tid}] {len(comments)} комм. «{str(topic.get('title'))[:60]}»")
    print(f"страниц закачано: {total_pages} | топиков уже было на диске: {skipped}")


def stage_wall(token, out):
    target = out / "wall.json"
    posts = load_json(target, []) or []
    offset = len(posts)
    while True:
        reply = call("wall.get", token, owner_id=-GROUP_ID, count=PAGE, offset=offset, extended=1, filters="post")
        if "_error" in reply:
            print(f"wall: {reply['_error']}")
            break
        response = reply["response"]
        items = response.get("items") or []
        posts += items
        offset += PAGE
        if not items or offset >= response.get("count", 0):
            break
    target.write_text(json.dumps(posts, ensure_ascii=False), encoding="utf-8")
    print(f"записей стены: {len(posts)} → {target.name}")


def page_ids(out):
    """Номера вики-страниц, которые стоит скачивать.

    `pages.getTitles` новые ключи VK не отдают (код 3, «Unknown method»), поэтому список
    собирается из того, на что ссылки уже есть: живые обсуждения и стена + архивные носители
    + колонки базы. Ничего не выдумываем: качаем ровно те страницы, которые кто-то назвал.
    """
    sources = [
        out / "wall.json", out / "topics.json",
        ROOT / "wiki_pages_meta.json", ROOT / "wiki_seasons_matches.json",
        ROOT / "wall_tournaments_posts.json", ROOT / "vk_soccer_comments_cache.json",
        ROOT / "special_tournaments_data.json", ROOT / "team_tournaments_data.json",
        ROOT / "all_group_topics.json", ROOT / "vk_match_sources_lookup.json",
        ROOT / "all_vk_seasons_matches.json", ROOT / "early_seasons_matches.json",
    ]
    blob = "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in sources if f.exists())
    found = set(re.findall(rf"page-{GROUP_ID}_(\d+)", blob))
    db = ROOT / "data" / "nst.db"
    if db.exists():
        con = sqlite3.connect(db)
        values = []
        for column in ("source_page", "source_locator", "source_ref", "note"):
            try:
                values += [str(v) for (v,) in con.execute(f"select distinct {column} from matches")]
            except sqlite3.Error:
                continue
        text = " ".join(values)
        found.update(re.findall(rf"page-{GROUP_ID}_(\d+)", text))
        found.update(re.findall(r"wiki_page_(\d+)", text))
        con.close()
    return sorted(found, key=int)


def stage_wiki(token, out):
    ids = page_ids(out)
    folder = out / "wiki"
    folder.mkdir(exist_ok=True)
    fetched = skipped = failed = 0
    for pid in ids:
        target = folder / f"{pid}.json"
        if target.exists():
            skipped += 1
            continue
        reply = call("pages.get", token, group_id=GROUP_ID, page_id=pid, info_keys="parent_id")
        if "_error" in reply:
            failed += 1
            print(f"   страница {pid}: код {reply['_error']['error_code']} — {reply['_error']['error_msg'][:70]}")
            continue
        page = reply.get("response") or {}
        target.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")
        fetched += 1
        if page.get("view_count") is not None:
            print(f"   [{pid}] {str(page.get('title'))[:60]} — {len(str(page.get('html') or ''))} симв.")
    print(f"вики: скачано {fetched} | уже было {skipped} | с ошибкой {failed} (из {len(ids)})")


def stage_docs(token, out):
    """Список документов сообщества: регламенты часто лежат файлами, а не вики-страницей."""
    target = out / "docs.json"
    docs, offset = [], 0
    while True:
        reply = call("docs.get", token, group_id=GROUP_ID, count=PAGE, offset=offset)
        if "_error" in reply:
            print(f"docs: {reply['_error']}")
            break
        response = reply["response"]
        items = response.get("items") or []
        docs += items
        offset += PAGE
        if not items or offset >= response.get("count", 0):
            break
    target.write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    print(f"документов: {len(docs)} → {target.name}")


def main():
    global PAUSE
    parser = argparse.ArgumentParser(description="Выгрузка живого VK-сообщества для сверки")
    parser.add_argument("stage", choices=("topics", "comments", "wall", "wiki", "docs"))
    parser.add_argument("--scope", choices=("soccer", "all"), default="soccer")
    parser.add_argument("--ids", help="через запятую — выбрать конкретные топики")
    parser.add_argument("--pause", type=float, default=PAUSE,
                        help="пауза между запросами; wall.get при 0.5с упирается в код 9, ему нужно 2-3")
    args = parser.parse_args()

    PAUSE = args.pause

    token = secret("VK_API_TOKEN")
    if not token:
        sys.exit("VK_API_TOKEN не задан (окружение или .env) — см. .env.example")
    out = dump_dir()
    out.mkdir(parents=True, exist_ok=True)

    if args.stage == "topics":
        stage_topics(token, out)
        return
    if args.stage == "wall":
        stage_wall(token, out)
        return
    if args.stage == "docs":
        stage_docs(token, out)
        return
    topics = load_json(out / "topics.json")
    if not topics:
        topics = stage_topics(token, out)
    if args.stage == "comments":
        picked = select_topics(topics, args.scope, args.ids)
        print(f"топиков в работе: {len(picked)} из {len(topics)}")
        stage_comments(token, out, picked)
    else:
        stage_wiki(token, out)


if __name__ == "__main__":
    main()
