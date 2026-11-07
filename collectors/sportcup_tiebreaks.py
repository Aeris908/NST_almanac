"""Чем на самом деле была доигровка: снапшот Sportcup против отчёта темы.

`overtimeWin` у источника значит «была доигровка», а не «был овертайм». Игру, решённую серией,
Sportcup хранит счётом самой серии — «1:1 (ПК 5:3)» живёт как 5:3, «1:1, 3:6 пен.» как 3:6, — а
ключа `afterGameWin` в снапшоте Сезонов 8-9 не встречается ни разу. Витрина поэтому печатает тег
«ОТ» там, где были пенальти, а индексы овертаймов считают серию как овертайм.

Скрипт берёт каждую помеченную игру и ищет её строку в теме сезона, чтобы решить по источнику, а
не по догадке. Три кучи:

* `penalties` — строка найдена, счёт игры в ней стоит, и тема прямо называет серию (пен, ПК, PK,
  буллиты);
* `overtime` — тема прямо называет овертайм или золотой гол;
* `unknown` — строки нет, или маркеров нет, или они противоречат друг другу. Угадывать нельзя:
  такая игра остаётся помеченной как есть и ждёт человека.

    python collectors/sportcup_tiebreaks.py            # отчёт
    python collectors/sportcup_tiebreaks.py --write    # дописать доказанное в decisions
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portal.names import clean_alias, homoglyph_fold

SNAPSHOT = ROOT / "data" / "sportcup_games.json"
DECISIONS = ROOT / "data" / "sportcup_decisions.json"
TOPIC_BY_SEASON = {"Season 8": 52002075, "Season 9": 54769667}
SERIES = re.compile(r"пен|пк|\bpk\b|буллит", re.IGNORECASE)
OVERTIME = re.compile(r"овертайм|экстра|\bот\b|\bot\b|золот", re.IGNORECASE)


def dump_dir():
    folders = sorted((ROOT / "data").glob("vk_dump_*"))
    return folders[-1] if folders else None


def topic_lines(season):
    """Строки комментариев темы сезона: (текст строки, id комментария)."""
    tid = TOPIC_BY_SEASON[season]
    path = dump_dir() / "comments" / f"{tid}.json"
    if not path.exists():
        return []
    blob = json.loads(path.read_text(encoding="utf-8"))
    lines = []
    for comment in blob["comments"]:
        for line in (comment.get("text") or "").splitlines():
            if line.strip():
                lines.append((line.strip(), comment["id"]))
    return lines


def score_forms(s1, s2):
    """Как счёт мог быть напечатан: обе ориентации и через дефис."""
    return (f"{s1}:{s2}", f"{s1}-{s2}", f"{s2}:{s1}", f"{s2}-{s1}")


def classify(game, lines):
    """Куча и доказательство: строка темы, где обе стороны и счёт игры."""
    pair = {homoglyph_fold(clean_alias(game["member1"]["title"])),
            homoglyph_fold(clean_alias(game["member2"]["title"]))}
    s1, s2 = game["scoreMember1"], game["scoreMember2"]
    hits = []
    for text, cid in lines:
        folded = homoglyph_fold(text)
        if not all(nick in folded for nick in pair):
            continue
        if not any(form in text for form in score_forms(s1, s2)):
            continue
        hits.append((text, cid))
    if not hits:
        return "unknown", None
    series = [hit for hit in hits if SERIES.search(hit[0])]
    extra = [hit for hit in hits if OVERTIME.search(hit[0])]
    if series and not extra:
        return "penalties", series[0]
    if extra and not series:
        return "overtime", extra[0]
    return "unknown", hits[0]


def tiebreak_games():
    """Игры Сезонов 8-9 с флагом доигровки и числовым счётом: (сезон, лига, игра)."""
    out = []
    blob = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    for stage in blob["stages"]:
        for game in stage["response"].get("list", []):
            if game.get("resultStatus") != "FINAL" or not game.get("overtimeWin"):
                continue
            if game.get("scoreMember1") is None or game.get("scoreMember2") is None:
                continue
            out.append((stage["season"], stage["league"], game))
    return out


def collect():
    lines = {season: topic_lines(season) for season in TOPIC_BY_SEASON}
    verdict = {}
    for season, league, game in tiebreak_games():
        kind, evidence = classify(game, lines.get(season, []))
        verdict[game["uuid"]] = {
            "season": season,
            "league": league,
            "match": f"{game['member1']['title']} {game['scoreMember1']}:"
                     f"{game['scoreMember2']} {game['member2']['title']}",
            "verdict": kind,
            "comment": evidence[1] if evidence else None,
            "line": evidence[0] if evidence else None,
        }
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="дописать доказанные серии в data/sportcup_decisions.json")
    args = parser.parse_args()

    verdict = collect()
    counts = Counter(row["verdict"] for row in verdict.values())
    print(f"игр с флагом доигровки: {len(verdict)}")
    for key in ("penalties", "overtime", "unknown"):
        print(f"   {key}: {counts.get(key, 0)}")

    shown = 0
    for uuid, row in sorted(verdict.items(), key=lambda kv: (kv[1]["season"], kv[1]["match"])):
        if row["verdict"] != "penalties" or shown >= 12:
            continue
        shown += 1
        print(f"\n{uuid} [{row['season']}] {row['match']}\n   коммент {row['comment']}: "
              f"{(row['line'] or '')[:110]}")

    if args.write:
        decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
        proven = sorted(uuid for uuid, row in verdict.items() if row["verdict"] == "penalties")
        decisions["tiebreak_penalties"] = [
            {"uuid": uuid, "match": verdict[uuid]["match"],
             "reason": f"тема {TOPIC_BY_SEASON[verdict[uuid]['season']]}, "
                       f"комментарий {verdict[uuid]['comment']}"}
            for uuid in proven
        ]
        DECISIONS.write_text(json.dumps(decisions, ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8")
        print(f"\nзаписано серий: {len(proven)} → {DECISIONS.name}")


if __name__ == "__main__":
    main()
