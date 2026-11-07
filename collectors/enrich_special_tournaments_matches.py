"""Таблицы игр молодёжного и клубного турниров в special_tournaments_data.json.

Запускать вручную не нужно: носитель уже содержит результат, а скрипт воспроизводит его не
целиком (обогащение хроникой, `year` и `topic_id` дописывает collectors/enrich_all_tournaments.py).
Оставлен как свидетельство того, откуда взялись строки молодёжного плей-офф.
"""

import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("special_tournaments_data.json", "r", encoding="utf-8") as f:
    st_data = json.load(f)

# 1. Молодёжный II: плей-офф рамки становится списком игр документа.
for t in st_data:
    if t["id"] == "youth_championship_2":
        t_matches = []
        for p in t.get("playoff", []):
            t_matches.append(
                {
                    "tour": p.get("stage", "Плей-офф"),
                    "league": "Плей-офф (до 5-6 побед)",
                    "p1": p.get("t1"),
                    "p2": p.get("t2"),
                    "score": p.get("score"),
                }
            )
        t["matches"] = t_matches

    # 2. Клубный Goal 4: игр рамка больше не несёт — их приносит разбор листов источника.
    # Прежний вариант читал special_tournaments/club_matches.csv и брал лигу из row[15],
    # но в том CSV колонка 15 — «МБ» (итог серии), а «Лига» — колонка 16: все строки молча
    # становились молодёжкой. Плюс обрезка club_m[:50] съедала Туры 5–10 и три игры с буллитами.
    # Протокол целиком разбирает portal/club_sources.py, строки идут через db/import_live.py:
    # рамка спецтурнира принимает только девять ключей и не умеет выразить ни ТП обоим, ни буллиты.
    if t["id"] == "club_offseason_goal4":
        t["matches"] = []
        t["row_keys"] = ["tour", "league", "p1", "p2", "score"]

with open("special_tournaments_data.json", "w", encoding="utf-8") as f:
    json.dump(st_data, f, ensure_ascii=False, indent=2)

print("special_tournaments_data.json: таблицы игр молодёжного и клубного турниров обновлены")
for t in st_data:
    print(f"  {t['title']}: игр {len(t.get('matches', []))}")
