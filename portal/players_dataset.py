"""Сборка полного мультиспортивного каталога всех игроков Nekketsu.

Объединяет:
1. Каталог игроков и матчей из базы nst.db по ВСЕМ дисциплинам (футбол, баскетбол, хоккей, доджбол).
2. Профили игроков, рейтинги Elo, статусы Зала славы, аватары и цитаты.
3. Полную турнирную хронологию каждого игрока («в каких туриках был»).
4. Полную матчевую историю каждого игрока («что делал») с ссылками на видео и VK.
"""

import sqlite3
from collections import defaultdict

from db.store import DB_PATH, connect
from portal.build_soccer import compose_payload
from portal.roster_tables import (
    CORE_ACTIVE_COMMUNITY,
    DEFAULT_AVATARS,
    HALL_OF_FAME_LEGENDS,
    HOF_REASONS,
)

HOF_FALLBACK_REASON = "Легендарный ветеран Высшей лиги NST."

DISCIPLINE_ICONS = {
    "soccer": "⚽",
    "basketball": "🏀",
    "hockey": "🏒",
    "dodgeball": "🏐",
}
AVATAR_FALLBACK = "https://api.dicebear.com/7.x/bottts/svg?seed={name}&backgroundColor=183c5c"


def parse_score_value(val):
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def get_match_result(score_for, score_opp, outcome=None, status=None):
    """Исход стороны из базы: `outcome` авторитетнее счёта (буллитная победа при равных голах,
    #88), технический результат даёт точный статус строки, а не подстрока в подписи."""
    is_tech = status == "technical"
    if outcome == "win":
        return ("ТП (ПОБЕДА)" if is_tech else "ПОБЕДА"), "win"
    if outcome == "loss":
        return ("ТП (ПОРАЖЕНИЕ)" if is_tech else "ПОРАЖЕНИЕ"), "loss"
    if outcome == "draw":
        return "НИЧЬЯ", "draw"
    if score_for is not None and score_opp is not None:
        if score_for > score_opp:
            return ("ТП (ПОБЕДА)" if is_tech else "ПОБЕДА"), "win"
        if score_for < score_opp:
            return ("ТП (ПОРАЖЕНИЕ)" if is_tech else "ПОРАЖЕНИЕ"), "loss"
        return "НИЧЬЯ", "draw"
    return "—", "none"


def period_flags(phase):
    """ОТ и буллиты из фазы матча ('overtime'/'penalties'/'overtime_penalties'), не из подписи."""
    phase = phase or ""
    return "overtime" in phase, "penalties" in phase


def build_players_dataset(db_path=DB_PATH):
    con = connect(str(db_path))
    con.row_factory = sqlite3.Row

    # 1. Футбольные данные и профили из существующего пайплайна
    soccer_payload = compose_payload(db_path)
    soccer_profiles = {p["player"]: p for p in soccer_payload["profiles"]}

    # 2. Ссылки на видео и посты VK из базы
    links = defaultdict(dict)
    for r in con.execute("select match_id, kind, url from match_links"):
        links[r["match_id"]][r["kind"]] = r["url"]

    # 3. Список дисциплин
    disciplines = {}
    for r in con.execute("select id, slug, name from disciplines order by id"):
        slug = r["slug"]
        disciplines[slug] = {
            "id": r["id"],
            "slug": slug,
            "name": r["name"],
            "icon": DISCIPLINE_ICONS.get(slug, "🎮"),
        }

    # 4. Все валидные матчи базы с привязкой сторон и игроков
    matches_map = {}
    match_query = """
    select m.id, m.tournament_id, m.stage_id, m.row_set, m.status, m.tour, m.league,
           m.played_on, m.source_ref, m.note, m.is_playoff, m.phase,
           t.name as tour_name, t.season, t.discipline_id,
           d.slug as disc_slug, d.name as disc_name,
           st.name as stage_name,
           ms.id as side_id, ms.side_index, ms.label, ms.score, ms.outcome,
           p.id as player_id, p.nick as player_nick
    from matches m
    join tournaments t on t.id = m.tournament_id
    join disciplines d on d.id = t.discipline_id
    left join stages st on st.id = m.stage_id
    join match_sides ms on ms.match_id = m.id
    join side_players sp on sp.side_id = ms.id
    join players p on p.id = sp.player_id
    where m.status <> 'void' and m.hidden_by is null
      and m.duplicate_of is null and m.source <> 'demo'
    order by m.played_on nulls last, m.id
    """

    for r in con.execute(match_query):
        mid = r["id"]
        if mid not in matches_map:
            matches_map[mid] = {
                "info": r,
                "sides": {
                    0: {"score": None, "outcome": None, "players": [], "label": None},
                    1: {"score": None, "outcome": None, "players": [], "label": None},
                },
            }
        s_idx = r["side_index"]
        matches_map[mid]["sides"][s_idx]["score"] = r["score"]
        matches_map[mid]["sides"][s_idx]["outcome"] = r["outcome"]
        matches_map[mid]["sides"][s_idx]["label"] = r["label"]
        nick = r["player_nick"]
        if nick not in matches_map[mid]["sides"][s_idx]["players"]:
            matches_map[mid]["sides"][s_idx]["players"].append(nick)

    # 5. Список всех реальных игроков (kind = 'player')
    player_rows = con.execute(
        "select id, nick, slug, kind from players where kind = 'player' order by nick collate nocase"
    ).fetchall()

    players_list = []
    
    for prow in player_rows:
        nick = prow["nick"]
        sp = soccer_profiles.get(nick, {})
        
        # Личные данные
        avatar = sp.get("avatar") or DEFAULT_AVATARS.get(nick) or AVATAR_FALLBACK.format(name=nick)
        vk_name = sp.get("vk_name") or nick
        vk_id = sp.get("vk_id")
        vk_domain = sp.get("vk_domain")
        is_active = nick in CORE_ACTIVE_COMMUNITY or sp.get("is_active", False)
        is_hof = nick in HALL_OF_FAME_LEGENDS or sp.get("is_hall_of_fame", False)
        hof_reason = sp.get("hof_reason") or HOF_REASONS.get(nick, HOF_FALLBACK_REASON if is_hof else None)
        status_label = sp.get("status_badge") or ("🏛️ ЗАЛ СЛАВЫ" if is_hof else ("⚡ АКТИВНЫЙ" if is_active else "📦 ВЕТЕРАН"))
        
        featured_quote = sp.get("quote")
        all_quotes = sp.get("all_quotes", [])

        # Сбор матчей игрока
        player_matches = []
        tournaments_dict = {}
        disc_stats = defaultdict(lambda: {
            "matches": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "tournaments": set(),
        })
        rivals_counter = defaultdict(lambda: {"matches": 0, "wins": 0, "draws": 0, "losses": 0})

        for mid, mdata in matches_map.items():
            s0 = mdata["sides"][0]
            s1 = mdata["sides"][1]
            
            if nick in s0["players"]:
                my_side, opp_side = s0, s1
            elif nick in s1["players"]:
                my_side, opp_side = s1, s0
            else:
                continue

            score_for = parse_score_value(my_side["score"])
            score_opp = parse_score_value(opp_side["score"])
            outcome = my_side["outcome"]
            info = mdata["info"]
            note = info["note"] or ""

            result_str, res_type = get_match_result(score_for, score_opp, outcome, info["status"])
            
            # Партнеры (для 2х2)
            partners = [p for p in my_side["players"] if p != nick]
            partner_str = ", ".join(partners) if partners else None

            # Соперники
            opponents = opp_side["players"]
            opp_str = ", ".join(opponents) if opponents else (opp_side["label"] or "—")

            # Учет в H2H
            for opp_nick in opponents:
                rivals_counter[opp_nick]["matches"] += 1
                if res_type == "win":
                    rivals_counter[opp_nick]["wins"] += 1
                elif res_type == "draw":
                    rivals_counter[opp_nick]["draws"] += 1
                elif res_type == "loss":
                    rivals_counter[opp_nick]["losses"] += 1

            disc_slug = info["disc_slug"]
            disc_name = info["disc_name"]
            disc_icon = DISCIPLINE_ICONS.get(disc_slug, "🎮")
            
            # Обновление стат по дисциплине
            ds = disc_stats[disc_slug]
            ds["matches"] += 1
            if res_type == "win":
                ds["wins"] += 1
            elif res_type == "draw":
                ds["draws"] += 1
            elif res_type == "loss":
                ds["losses"] += 1
            if score_for is not None:
                ds["goals_for"] += score_for
            if score_opp is not None:
                ds["goals_against"] += score_opp
            tid = info["tournament_id"]
            ds["tournaments"].add(tid)

            # Учет турнира
            if tid not in tournaments_dict:
                tournaments_dict[tid] = {
                    "id": tid,
                    "name": info["tour_name"],
                    "season": info["season"] or "—",
                    "disc_slug": disc_slug,
                    "disc_name": disc_name,
                    "disc_icon": disc_icon,
                    "matches": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "stages": [],
                }
            tentry = tournaments_dict[tid]
            tentry["matches"] += 1
            if res_type == "win":
                tentry["wins"] += 1
            elif res_type == "draw":
                tentry["draws"] += 1
            elif res_type == "loss":
                tentry["losses"] += 1
            if score_for is not None:
                tentry["goals_for"] += score_for
            if score_opp is not None:
                tentry["goals_against"] += score_opp
            stage_val = info["tour"] or info["stage_name"] or ""
            if stage_val and stage_val not in tentry["stages"]:
                tentry["stages"].append(stage_val)

            is_ot, is_pk = period_flags(info["phase"])

            m_record = {
                "id": mid,
                "disc_slug": disc_slug,
                "tournament": info["tour_name"],
                "season": info["season"] or "",
                "stage": stage_val,
                "played_on": info["played_on"] or (info["season"] or "—"),
                "opponent": opp_str,
                "score_for": score_for,
                "score_opp": score_opp,
                "score_display": f"{score_for}:{score_opp}" if score_for is not None and score_opp is not None else (note or "—"),
                "result": result_str,
                "res_type": res_type,
            }
            if partner_str:
                m_record["partner"] = partner_str
            if is_ot:
                m_record["ot"] = True
            if is_pk:
                m_record["pk"] = True
            if note:
                m_record["note"] = note
            if links[mid].get("video"):
                m_record["video_url"] = links[mid]["video"]
            if links[mid].get("vk_post"):
                m_record["vk_url"] = links[mid]["vk_post"]

            player_matches.append(m_record)

        # Итоги карьеры по всем дисциплинам
        total_m = len(player_matches)
        total_w = sum(1 for m in player_matches if m["res_type"] == "win")
        total_d = sum(1 for m in player_matches if m["res_type"] == "draw")
        total_l = sum(1 for m in player_matches if m["res_type"] == "loss")
        total_gf = sum(m["score_for"] for m in player_matches if m["score_for"] is not None)
        total_ga = sum(m["score_opp"] for m in player_matches if m["score_opp"] is not None)
        win_rate = round((total_w / total_m * 100), 1) if total_m > 0 else 0.0

        # Разбивка по дисциплинам в удобном формате
        disciplines_breakdown = []
        for dslug, dinfo in disciplines.items():
            if dslug in disc_stats:
                dstat = disc_stats[dslug]
                d_total = dstat["matches"]
                d_w = dstat["wins"]
                d_wr = round((d_w / d_total * 100), 1) if d_total > 0 else 0.0
                breakdown_item = {
                    "slug": dslug,
                    "name": dinfo["name"],
                    "icon": dinfo["icon"],
                    "matches": d_total,
                    "wins": d_w,
                    "draws": dstat["draws"],
                    "losses": dstat["losses"],
                    "win_rate": d_wr,
                    "goals_for": dstat["goals_for"],
                    "goals_against": dstat["goals_against"],
                    "tournaments_count": len(dstat["tournaments"]),
                }
                if dslug == "soccer":
                    breakdown_item["elo"] = sp.get("active_elo")
                    breakdown_item["peak_elo"] = sp.get("peak_elo")
                    breakdown_item["league"] = sp.get("league")
                    breakdown_item["clean_sheets"] = sp.get("clean_sheets", 0)
                disciplines_breakdown.append(breakdown_item)

        # Турниры отсортированные по убыванию матчей или ID
        tournaments_list = list(tournaments_dict.values())
        tournaments_list.sort(key=lambda t: (t["matches"]), reverse=True)

        # Топ-соперники H2H
        top_rivals = []
        for opp_nick, rstats in sorted(rivals_counter.items(), key=lambda item: item[1]["matches"], reverse=True)[:6]:
            if opp_nick and opp_nick not in ("—", "?"):
                top_rivals.append({
                    "nick": opp_nick,
                    "matches": rstats["matches"],
                    "wins": rstats["wins"],
                    "draws": rstats["draws"],
                    "losses": rstats["losses"],
                })

        # Матчи сортируем от новых к старым
        player_matches.reverse()

        players_list.append({
            "nick": nick,
            "slug": prow["slug"],
            "vk_name": vk_name,
            "avatar": avatar,
            "vk_id": vk_id,
            "vk_domain": vk_domain,
            "is_active": is_active,
            "is_hall_of_famer": is_hof,
            "hof_reason": hof_reason,
            "status_badge": status_label,
            "featured_quote": featured_quote,
            "all_quotes": all_quotes,
            "soccer_elo": sp.get("active_elo"),
            "soccer_peak_elo": sp.get("peak_elo"),
            "soccer_league": sp.get("league"),
            "career": {
                "matches": total_m,
                "wins": total_w,
                "draws": total_d,
                "losses": total_l,
                "win_rate": win_rate,
                "goals_for": total_gf,
                "goals_against": total_ga,
                "goal_diff": total_gf - total_ga,
                "disciplines_count": len(disciplines_breakdown),
            },
            "disciplines": disciplines_breakdown,
            "tournaments": tournaments_list,
            "matches": player_matches,
            "top_rivals": top_rivals,
        })

    con.close()

    # Сортировка общего списка игроков:
    # 1. Сначала активные (is_active), затем Зал славы, затем ветераны.
    # 2. Внутри группы — по количеству побед во всех видах спорта.
    players_list.sort(
        key=lambda p: (
            p["is_active"],
            p["is_hall_of_famer"],
            p["career"]["wins"],
            p["career"]["matches"],
        ),
        reverse=True,
    )

    stats = {
        "total_players": len(players_list),
        "active_players": sum(1 for p in players_list if p["is_active"]),
        "hof_players": sum(1 for p in players_list if p["is_hall_of_famer"]),
        "multisport_players": sum(1 for p in players_list if p["career"]["disciplines_count"] > 1),
        "total_matches": len(matches_map),
        "disciplines_count": len(disciplines),
    }

    return {
        "stats": stats,
        "disciplines": list(disciplines.values()),
        "players": players_list,
    }
