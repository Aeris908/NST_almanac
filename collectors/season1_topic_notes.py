"""Сезон 1: что именно говорит живая тема 32593813 про каждую ногу чемпионата.

Матрица и календарь (`data/gsheet_season1/`) согласуются нога в ногу и лежат в git, поэтому они
и есть основа архива. Комментарий темы — второй голос: он подтверждает не все игры, зато называет
тур своими словами. Чтобы это можно было сверять без сети и без выгрузки, здесь собирается
маленький носитель `data/season1_topic_notes.json`: для каждой ноги матрицы — id комментариев,
которые её называют, и номер тура из их шапки.

Файл описательный, ничего не решает: генератор архива берёт из него только то, стоит ли в
`note_leg` оставить спор «календарь против темы».

Запуск (нужна локальная выгрузка `data/vk_dump_2026-11-03/`, в git она не лежит):

    python collectors/season1_topic_notes.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.vk_reconcile import parse_comment  # noqa: E402
from portal.names import clean_alias  # noqa: E402

DUMP = ROOT / "data" / "vk_dump_2026-11-03" / "comments" / "32593813.json"
OUT = ROOT / "data" / "season1_topic_notes.json"
TOUR_RX = re.compile(r"(\d{1,2})\s*тур", re.IGNORECASE)

# Пост-шапка (2292) и его перепечатка (2489) показывают формат отчёта, а не результат; в
# комментарии 3025 организатор цитирует чужой отчёт. Ни одно из них игрой не было.
SAMPLES = {2292, 2489, 3025}


def token(text):
    return clean_alias(text or "").strip().strip("*.,_()[]").lower()


def main():
    if not DUMP.exists():
        sys.exit(f"нет выгрузки темы: {DUMP} — без неё носитель не собрать, "
                 "а архив Сезона 1 она не касается: он строится по листам")
    comments = json.loads(DUMP.read_text(encoding="utf-8"))["comments"]
    found = defaultdict(lambda: {"comments": [], "tours": []})
    for comment in comments:
        cid = int(comment["id"])
        if cid in SAMPLES:
            continue
        text = comment.get("text") or ""
        hit = TOUR_RX.search(text)
        for leg in parse_comment(text):
            names = [token(x) for x in leg["raw"]]
            if len(names) != 2 or not all(names) or names[0] == names[1]:
                continue
            key = (tuple(sorted(names)), tuple(sorted(leg["scores"])))
            entry = found[key]
            if cid not in entry["comments"]:
                entry["comments"].append(cid)
            if hit and int(hit.group(1)) not in entry["tours"]:
                entry["tours"].append(int(hit.group(1)))

    rows = [{"pair": list(pair), "scores": list(scores),
             "comments": value["comments"], "tours": value["tours"]}
            for (pair, scores), value in sorted(found.items())]
    # По строке на ногу: носитель читают глазами, а json.dumps с отступом разложил бы каждую
    # четвёрку чисел на шесть строк.
    body = ",\n".join(" " + json.dumps(row, ensure_ascii=False) for row in rows)
    OUT.write_text("[\n" + body + "\n]\n", encoding="utf-8")
    with_tour = sum(1 for r in rows if r["tours"])
    print(f"ног с отчётом темы: {len(rows)}, из них с номером тура {with_tour} → {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
