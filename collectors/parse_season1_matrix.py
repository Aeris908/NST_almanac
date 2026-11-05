"""Дивизионы Сезона 1: строки носителя из снимка google-таблиц турнира.

Сезон 1 пришёл в архив из турнирной матрицы КОМЕТОВ (см. `early_seasons_matches.json`), и
второй дивизион того же чемпионата — МЕТЕОРЫ — в архиве не присутствовал вовсе. Снимки обоих
листов лежат в `data/gsheet_season1/` (адреса названы шапкой темы 32593813), поэтому строки
воспроизводимы без сети.

Конвенция матрицы доказана на уже внесённых Кометах: ячейка «строка A → колонка B» есть счёт
ноги `A s1 : s2 B`, и 90 из 90 строк носителя ей равны. Поэтому здесь берётся только первое
значение ячейки, как его взял архив для Кометов, а вторая нога встречи, записанная в скобках
(«1:5 (2:3)»), сознательно не трогается: это тот же вопрос, что и расхождение календаря с
матрицей, и решает его человек.

Запуск:

    python collectors/parse_season1_matrix.py --check   # сверить носитель со снимком
    python collectors/parse_season1_matrix.py           # перезаписать строки дивизиона

Файл носителя остаётся носителем: скрипт трогает только строки с своим `league`, поэтому
повторный прогон идемпотентен и не задевает перенос Кометов, Кубок лиг и остальные сезоны.
"""

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.names import clean_alias  # noqa: E402

SNAPSHOT = ROOT / "data" / "gsheet_season1"
CARRIER = ROOT / "early_seasons_matches.json"
SCORE = re.compile(r"^\s*(\d{1,2})\s*[:\-]\s*(\d{1,2})\s*$")
# Колонки-заголовки матрицы, игроками не являющиеся.
HEADERS = {"м", "команда", "о", "оп", "и", "в", "н", "п", "мз", "мп", "мр", "мср", "№".lower()}

DIVISIONS = {
    "Метеоры": SNAPSHOT / "1579784569.csv",
    "Кометы": SNAPSHOT / "31265171.csv",
}
TOURNAMENT = "Season 1 Регулярный чемпионат"
STAGE = "Круговой этап"


def matrix_rows(path):
    """Пары «строка → колонка» с первым счётом ячейки: (никA, никB, голыA, голыB)."""
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        table = list(csv.reader(handle))
    columns = {}
    for index, name in enumerate(table[0]):
        nick = clean_alias(name.strip())
        if nick and nick.lower() not in HEADERS and not nick.isdigit():
            columns.setdefault(nick.lower(), (nick, index))
    found = []
    for row in table[1:]:
        if len(row) < 3 or not row[1].strip():
            continue
        mine = clean_alias(row[1].strip())
        for other, (nickname, index) in columns.items():
            if other == mine.lower() or index >= len(row):
                continue
            hit = SCORE.match(str(row[index]))
            if not hit:
                continue
            found.append((mine, nickname, int(hit.group(1)), int(hit.group(2))))
    return found


def carrier_rows(division):
    """Строки дивизиона в форме носителя: обе ориентации пары, как их записала матрица."""
    rows = []
    for a, b, s1, s2 in matrix_rows(DIVISIONS[division]):
        rows.append({"season": "Season 1", "tournament": TOURNAMENT, "league": division,
                     "stage": STAGE, "p1": a, "p2": b, "s1": s1, "s2": s2,
                     "ot": False, "pk": False, "is_playoff": False})
    return rows


def main():
    parser = argparse.ArgumentParser(description="Дивизионы Сезона 1 из снимка матрицы")
    parser.add_argument("--check", action="store_true", help="только сверить, ничего не писать")
    parser.add_argument("--division", default="Метеоры", help="дивизион (по умолчанию МЕТЕОРЫ)")
    args = parser.parse_args()

    fresh = carrier_rows(args.division)
    carrier = json.loads(CARRIER.read_text(encoding="utf-8"))
    kept = [row for row in carrier if row.get("league") != args.division]
    if args.check:
        current = [row for row in carrier if row.get("league") == args.division]
        same = current == fresh
        print(f"{args.division}: снимок даёт {len(fresh)} строк, в носителе {len(current)} — "
              f"{'совпадает' if same else 'РАЗЛИЧАЕТСЯ'}")
        return 0 if same else 1

    merged = kept + fresh
    CARRIER.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.division}: записано {len(fresh)} строк "
          f"(всего в носителе было {len(carrier)}, стало {len(merged)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
