"""Провенанс строк носителя: какой комментарий стоит за игрой, у которой источника не нашлось.

Сборка ищет комментарии в `vk_match_sources_lookup.json` — индексе, собранном разборщиком
2023 года по своему списку алиасов. Написания, которого в том списке нет («Валера» вместо
«Буца»), или строки, разобранной иначе, индекс не знает — и в базу игра ложится без ссылки и
без текста. Такую строку человек в карточке проверить не может: сверять не с чем.

Сам комментарий лежит в локальной выгрузке `data/vk_dump_*/`, а разбирается он тем же кодом,
что живая сверка (`collectors/vk_reconcile`): те же алиасы, та же складка гомоглифов. Найденное
записываем в носитель, а не в сборку: сборка обязана оставаться офлайн, а датированная
выгрузка не может быть её входом.

Список «без источника» читается из базы, поэтому сборщик запускают после сборки. Повторный
`collectors/save_vk_matches.py` эти три ключа сотрёт: он пересобирает носитель с нуля, и после
него сборщик нужно запустить заново.

    python collectors/vk_row_sources.py            # посмотреть, что нашлось
    python collectors/vk_row_sources.py --write    # записать в носитель
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collectors.vk_reconcile import (
    MATCH_REGEXES,
    SCORE_TOKEN,
    load_live,
    parse_comment,
    post_url,
    resolve_sides,
)
from portal.names import clean_alias, homoglyph_fold
from portal.vk_sources import enrich_vk_source, topic_id

CARRIER = ROOT / "all_vk_seasons_matches.json"
DATABASE = ROOT / "data" / "nst.db"
LOOKUP = ROOT / "vk_match_sources_lookup.json"


def row_key(season, p1, p2, s1, s2):
    """Пара и счёт так, как их видит сборка: канонические ники, порядок сторон как в строке."""
    return season, clean_alias(p1), clean_alias(p2), int(s1), int(s2)


def open_base():
    con = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def without_source(con):
    """Игры среза «комментарии ВК», у которых в базе пустой текст источника."""
    query = """
        select t.season, sa.label as p1, sb.label as p2, sa.score as s1, sb.score as s2
        from matches m
        join tournaments t on t.id = m.tournament_id
        join match_sides sa on sa.match_id = m.id and sa.side_index = 0
        join match_sides sb on sb.match_id = m.id and sb.side_index = 1
        where m.source = 'vk_comments_playoff' and (m.source_text is null or m.source_text = '')
        order by t.season, m.id
    """
    return [row_key(r["season"], r["p1"], r["p2"], r["s1"], r["s2"]) for r in con.execute(query)]


class Comments:
    """Комментарии тем из выгрузки, разобранные так же, как их разбирает сверка."""

    def __init__(self, nicknames):
        self.live, _ = load_live()
        self.nicknames = nicknames
        self.lowered = {homoglyph_fold(nick): nick for nick in nicknames}
        self.indexes = {}

    def topic_indexes(self, tid):
        topic = self.live.get(tid)
        if tid not in self.indexes:
            self.indexes[tid] = self._index(topic) if topic else ({}, {})
        return self.indexes[tid]

    def _index(self, topic):
        """Два взгляда на тему: разобранные ноги и просто строки «пара — счёт»."""
        legs, lines = {}, {}
        for cid, comment in topic["comments"].items():
            text = comment.get("text", "")
            for leg in parse_comment(text):
                pair = self._single(leg["raw"])
                if not pair:
                    continue
                s1, s2 = leg["scores"]
                for orientation in ((s1, s2), (s2, s1)):
                    legs.setdefault((pair, orientation), (cid, comment.get("pos"), leg, text))
            for pair, scores, tail in self._line_pairs(text):
                for s1, s2 in scores:
                    for orientation in ((s1, s2), (s2, s1)):
                        trace = (cid, comment.get("pos"), tail, text)
                        lines.setdefault((pair, orientation), []).append(trace)
        return legs, lines

    def _line_pairs(self, text):
        """Пара и все счёта строки, где она названа.

        Разбор ног отдаёт из «Palka Palych vs AJ_Maker 5:4 (3:3 — основное время, 2:1 — буллиты)»
        только 3:3: итог встречи он считает не ногой. Для поиска комментария это не потеря —
        строка носителя помнит 5:4, и стоит оно в том же тексте.
        """
        found = []
        for line in str(text).splitlines():
            for rx in MATCH_REGEXES:
                for hit in rx.finditer(line):
                    pair = self._single((hit.group(1), hit.group(2)))
                    tail = line[hit.end(2):]
                    scores = [(int(a), int(b)) for a, b in SCORE_TOKEN.findall(tail)]
                    if pair and scores:
                        found.append((pair, scores, tail))
        return found

    def _single(self, raw_pair):
        """Пара одиночников строки комментария; командная нога 2×2 не подходит."""
        sides, _ = resolve_sides(raw_pair, self.nicknames, self.lowered)
        if len(sides) != 2 or any(len(side) != 1 for side in sides):
            return None
        return frozenset(side[0] for side in sides)

    @staticmethod
    def topic_of(season):
        """Тема сезона в выгрузке: по ней строке собирается ссылка на комментарий."""
        return str(topic_id(season))

    def find(self, tid, p1, p2, s1, s2):
        """Комментарий темы, называющий эту пару и этот счёт; None — если в теме его нет.

        Разобранные ноги решают. Строки без разбора принимаем только когда комментарий в теме
        один: два разных комментария с той же парой и счётом — это уже не доказательство.
        """
        legs, lines = self.topic_indexes(tid)
        pair = frozenset({p1, p2})
        for scores in ((s1, s2), (s2, s1)):
            if (pair, scores) in legs:
                cid, pos, leg, text = legs[(pair, scores)]
                ref = f"{leg['scores'][0]}-{leg['scores'][1]}#{leg['leg']}"
                return {"cid": cid, "pos": pos, "text": text, "ref": ref, "loose": False}
        for scores in ((s1, s2), (s2, s1)):
            hits = lines.get((pair, scores), [])
            if len({cid for cid, _pos, _tail, _text in hits}) == 1:
                cid, pos, _tail, text = hits[0]
                return {"cid": cid, "pos": pos, "text": text, "ref": f"{s1}-{s2}", "loose": True}
        return None


def main():
    parser = argparse.ArgumentParser(description="Дополнить строки носителя следом комментария")
    parser.add_argument("--write", action="store_true", help="записать найденное в носитель")
    args = parser.parse_args()

    carrier = json.loads(CARRIER.read_text(encoding="utf-8"))
    lookup = json.loads(LOOKUP.read_text(encoding="utf-8"))
    by_key = {}
    for m in carrier:
        by_key.setdefault(row_key(m["season"], m["p1"], m["p2"], m["s1"], m["s2"]), []).append(m)

    con = open_base()
    wanted = without_source(con)
    nicknames = {row["nick"] for row in con.execute("select nick from players")}
    con.close()
    print(f"строк базы без источника: {len(wanted)}")

    comments = Comments(nicknames)
    filled = skipped = already = 0
    for key in wanted:
        season, p1, p2, s1, s2 = key
        rows = by_key.get(key, [])
        if len(rows) != 1:
            print(f"  ПРОПУСК {season} {p1} {s1}:{s2} {p2}: в носителе таких строк {len(rows)}")
            skipped += 1
            continue
        row = rows[0]
        probe = {**row, "p1": p1, "p2": p2}
        enrich_vk_source(probe, lookup)
        if probe.get("vk_text"):
            already += 1  # архив её уже нашёл: дублировать в носитель не нужно
            continue
        tid = comments.topic_of(season)
        hit = comments.find(tid, p1, p2, s1, s2)
        if not hit:
            print(f"  НЕТ      {season} {p1} {s1}:{s2} {p2}")
            skipped += 1
            continue
        cid, pos, text, ref = hit["cid"], hit["pos"], hit["text"], hit["ref"]
        row["source_ref"] = f"topic-{tid}#{cid}#{ref}"
        row["vk_url"] = post_url(tid, cid, pos)
        row["vk_text"] = text.strip()
        filled += 1
        note = " (по строке, разбор ног счёт не видит)" if hit["loose"] else ""
        print(f"  НАЙДЕНО  {season} {p1} {s1}:{s2} {p2} -> {row['source_ref']}{note}")

    print(f"провенанс добавлен: {filled}, уже был в архиве: {already}, без источника: {skipped}")
    if args.write:
        CARRIER.write_text(json.dumps(carrier, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\r\n")
        print(f"носитель перезаписан: {CARRIER.name}")
    else:
        print("просмотр: с --write изменения попадут в носитель")


if __name__ == "__main__":
    main()
