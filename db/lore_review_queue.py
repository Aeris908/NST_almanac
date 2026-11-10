"""Очередь задач на проверку лороведом (lore review queue).

Содержит спорные ситуации, требующие осознанного решения лороведа/редактора:
1. Сезон 8, 1/2 финала Кубка лиг: ectoPower vs Romix 4:4.
   В рейтинговом пуле ничья (draw/draw), Elo не сдвинут победой.
   В комментарии ВК зафиксирована победа ectoPower по буллитам (4:4, пк: 9-7).
   Алгоритм подсвечивает конфликт исхода в матче на выбывание и ожидает вердикта лороведа.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db import store

DB_PATH = store.DB_PATH
BATCH = "lore_review_s8"
UNPROVEN_BATCH = "lore_review_unproven"
LORE_BATCHES = (BATCH, UNPROVEN_BATCH)


def populate_lore_review(con):
    """Регистрирует задачи лороведу, если они ещё не решены ручной правкой."""
    # Очищаем батчи лороведа перед заполнением
    for b in LORE_BATCHES:
        con.execute("delete from incoming where batch = ?", (b,))

    # 1. ectoPower vs Romix в Сезоне 8 Кубок лиг (пул #342)
    # Находим строку пула
    row = con.execute("""
        select m.id, m.manual, s0.score, s1.score, s0.outcome, s1.outcome
        from matches m
        join tournaments t on t.id = m.tournament_id
        join match_sides s0 on s0.match_id = m.id and s0.side_index = 0
        join match_sides s1 on s1.match_id = m.id and s1.side_index = 1
        join side_players sp0 on sp0.side_id = s0.id
        join players p0 on p0.id = sp0.player_id
        join side_players sp1 on sp1.side_id = s1.id
        join players p1 on p1.id = sp1.player_id
        where t.name = 'Season 8 Кубок лиг' and m.row_set = 'pool'
          and p0.nick = 'ectoPower' and p1.nick = 'Romix'
          and s0.score = 4 and s1.score = 4
    """).fetchone()

    if row:
        match_id, manual, _s0, _s1, out0, out1 = row
        # Если матч уже правился вручную или исход больше не ничья — задача считается решённой
        verdict = "same" if (manual or (out0 != "draw" and out1 != "draw")) else "conflict"
        payload = {
            "задача": "Сезон 8, 1/2 финала Кубка лиг: в Sportcup и рейтинговом пуле зафиксирована ничья 4:4 (draw/draw). В протоколе ВК зафиксирована победа ectoPower по буллитам (4:4, пк: 9-7). Требуется решение лороведа: пересчитывать ли исход пула на победу ectoPower с пересчётом Elo, либо оставить историческую ничью.",
            "алгоритм_сомнение": "Ничья в кубковом матче на выбывание с серией буллитов (по протоколу 9:7 в пользу ectoPower) противоречит регламенту плей-офф. Исход влияет на рейтинг Elo.",
            "ссылки": [
                "https://vk.ru/topic-66162180_52002075?offset=120#post31593",
                "https://vk.ru/video-66162180_456249558",
            ],
            "тур": "1/2 финала",
            "лига": "Кубок лиг",
            "стороны": ["ectoPower", "Romix"],
            "как_выглядит": "Пул: 4:4 (draw/draw, Elo не сдвинут победой). Протокол ВК: 4:4 (пк: 9-7, победа ectoPower).",
        }
        con.execute(
            "insert into incoming(batch, source, source_ref, payload, verdict, matched_match_id)"
            " values (?, 'review_pool', 's8_cup_semifinal_ectopower_romix', ?, ?, ?)",
            (BATCH, json.dumps(payload, ensure_ascii=False), verdict, match_id),
        )

    # 2. Строки комментарного носителя без точного доказательства лиги и тура
    unproven_rows = con.execute("""
        select m.id, m.manual, t.name, m.tour, m.source_ref,
               (select group_concat(p.nick, ' vs ')
                from match_sides ms
                join side_players sp on sp.side_id = ms.id
                join players p on p.id = sp.player_id
                where ms.match_id = m.id) as sides,
               (select group_concat(ms.score, ':')
                from match_sides ms
                where ms.match_id = m.id) as score,
               (select url
                from match_links ml
                where ml.match_id = m.id and ml.kind = 'vk_post'
                limit 1) as vk_url
        from matches m
        join tournaments t on t.id = m.tournament_id
        where m.source = 'vk_comments_playoff' and m.tour = 'Плей-офф / Кубок'
        order by t.name, m.id
    """).fetchall()

    for r in unproven_rows:
        mid, manual, t_name, tour, s_ref, sides, score, vk_url = r
        # Если матч уже правился вручную или тур перестал быть заглушкой — решено
        verdict = "same" if (manual or tour != "Плей-офф / Кубок") else "conflict"
        payload = {
            "задача": (
                f"Не доказан дивизион (Высшая/Средняя/Дворовая) или тур по тексту комментария в ВК. "
                f"Сейчас в витрине стоит временный плейсхолдер '{tour}' в турнире '{t_name}'. "
                f"Требуется проверить контекст обсуждения в ВК и выставить верный дивизион и тур."
            ),
            "алгоритм_сомнение": (
                "В тексте комментария дивизион не указан; строка временно помещена в Высшую лигу "
                "с этапом 'Плей-офф / Кубок'."
            ),
            "ссылки": [vk_url] if vk_url else [],
            "тур": tour,
            "лига": t_name,
            "стороны": sides.split(" vs ") if sides else [],
            "как_выглядит": f"{t_name} · {tour} · {sides} ({score})",
        }
        ref_key = s_ref or f"unproven_playoff_{mid}"
        con.execute(
            "insert into incoming(batch, source, source_ref, payload, verdict, matched_match_id)"
            " values (?, 'review_unproven', ?, ?, ?, ?)",
            (UNPROVEN_BATCH, ref_key, json.dumps(payload, ensure_ascii=False), verdict, mid),
        )

    con.commit()


def main(db_path=DB_PATH):
    sys.stdout.reconfigure(encoding="utf-8")
    con = store.connect(db_path)
    populate_lore_review(con)
    for b in LORE_BATCHES:
        count = con.execute("select count(*) from incoming where batch = ? and verdict = 'conflict'", (b,)).fetchone()[0]
        print(f"задач лороведу в батче {b}: {count}")
    return 0


if __name__ == "__main__":
    main()
