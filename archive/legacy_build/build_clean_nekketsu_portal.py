import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from collections import defaultdict
import build_final_analytics

print("Building Clean Nekketsu Master Portal...")

# 1. Load data
with open("nekketsu_master_table.json", "r", encoding="utf-8") as f:
    master_db = json.load(f)

with open("player_avatars.json", "r", encoding="utf-8") as f:
    avatars = json.load(f)

with open("nst_quotes.json", "r", encoding="utf-8") as f:
    nst_quotes = json.load(f)

with open("early_seasons_matches.json", "r", encoding="utf-8") as f:
    early_matches = json.load(f)

# Combine matches: early matches + existing matches
base_matches = build_final_analytics.all_matches
# Deduplicate: remove any placeholder S4 matches from base that are in early_matches
existing_keys = set()
combined_matches = []

for m in early_matches:
    key = (m["season"], m["p1"], m["p2"], m["s1"], m["s2"], m.get("stage", ""))
    existing_keys.add(key)
    combined_matches.append(m)

for m in base_matches:
    key = (m["season"], m["p1"], m["p2"], m["s1"], m["s2"], m.get("stage", ""))
    if key not in existing_keys:
        existing_keys.add(key)
        combined_matches.append(m)

print(f"Total combined match dataset: {len(combined_matches)} games!")

# 2. Enrich player statistics
player_matches = defaultdict(list)
player_stats_addon = defaultdict(lambda: {
    "reg_w": 0, "ot_w": 0, "pk_w": 0,
    "reg_l": 0, "ot_l": 0, "pk_l": 0,
    "draws": 0
})

for m in combined_matches:
    p1 = m["p1"]
    p2 = m["p2"]
    s1 = m["s1"]
    s2 = m["s2"]
    ot = m.get("ot", False)
    pk = m.get("pk", False)
    season = m.get("season", "Unknown")
    tourn = m.get("tournament", "")
    stage = m.get("stage", "Матч")

    p1_res = "W" if s1 > s2 else ("L" if s1 < s2 else "D")
    p2_res = "W" if s2 > s1 else ("L" if s2 < s1 else "D")

    player_matches[p1].append({
        "season": season, "tournament": tourn, "stage": stage,
        "opponent": p2, "score_for": s1, "score_against": s2,
        "result": p1_res, "ot": ot, "pk": pk
    })
    player_matches[p2].append({
        "season": season, "tournament": tourn, "stage": stage,
        "opponent": p1, "score_for": s2, "score_against": s1,
        "result": p2_res, "ot": ot, "pk": pk
    })

    if s1 > s2:
        if pk: player_stats_addon[p1]["pk_w"] += 1; player_stats_addon[p2]["pk_l"] += 1
        elif ot: player_stats_addon[p1]["ot_w"] += 1; player_stats_addon[p2]["ot_l"] += 1
        else: player_stats_addon[p1]["reg_w"] += 1; player_stats_addon[p2]["reg_l"] += 1
    elif s2 > s1:
        if pk: player_stats_addon[p2]["pk_w"] += 1; player_stats_addon[p1]["pk_l"] += 1
        elif ot: player_stats_addon[p2]["ot_w"] += 1; player_stats_addon[p1]["ot_l"] += 1
        else: player_stats_addon[p2]["reg_w"] += 1; player_stats_addon[p1]["reg_l"] += 1
    else:
        player_stats_addon[p1]["draws"] += 1
        player_stats_addon[p2]["draws"] += 1

default_avatars = {
    "Transistor": "https://api.dicebear.com/7.x/bottts/svg?seed=Transistor&backgroundColor=183c5c",
    "mafuta": "https://api.dicebear.com/7.x/bottts/svg?seed=Mafuta&backgroundColor=183c5c",
    "WiSe": "https://api.dicebear.com/7.x/bottts/svg?seed=WiSe&backgroundColor=183c5c",
    "Wenderfit": "https://api.dicebear.com/7.x/bottts/svg?seed=Wenderfit&backgroundColor=183c5c",
    "high": "https://api.dicebear.com/7.x/bottts/svg?seed=High&backgroundColor=183c5c",
    "3aBuCTb": "https://api.dicebear.com/7.x/bottts/svg?seed=Zavist&backgroundColor=183c5c",
    "Centurion": "https://api.dicebear.com/7.x/bottts/svg?seed=Centurion&backgroundColor=183c5c",
    "Flash": "https://api.dicebear.com/7.x/bottts/svg?seed=Flash&backgroundColor=183c5c",
    "LiptOn": "https://api.dicebear.com/7.x/bottts/svg?seed=LiptOn&backgroundColor=183c5c",
    "Kipriot": "https://api.dicebear.com/7.x/bottts/svg?seed=Kipriot&backgroundColor=183c5c",
    "E_not": "https://api.dicebear.com/7.x/bottts/svg?seed=Enot&backgroundColor=183c5c",
    "RVD (МГБ)": "https://api.dicebear.com/7.x/bottts/svg?seed=RVD&backgroundColor=183c5c",
}

# Attach rich addon stats to each profile
profiles = master_db["power_rankings"]
for p in profiles:
    name = p["player"]
    add = player_stats_addon[name]
    p["reg_wins"] = add["reg_w"]
    p["ot_wins"] = add["ot_w"]
    p["pk_wins"] = add["pk_w"]
    p["reg_losses"] = add["reg_l"]
    p["ot_losses"] = add["ot_l"]
    p["pk_losses"] = add["pk_l"]
    p["draws"] = add["draws"]
    clutch_w = add["ot_w"] + add["pk_w"]
    clutch_total = clutch_w + add["ot_l"] + add["pk_l"]
    p["clutch_total"] = clutch_total
    p["clutch_wins"] = clutch_w
    p["clutch_win_rate"] = round(clutch_w / clutch_total * 100, 1) if clutch_total > 0 else 0.0

    # Kunio supershot
    if p["active_elo"] >= 1650: p["supershot"] = "Банановый суперудар"; p["role"] = "Капитан / Форвард"
    elif p["active_elo"] >= 1550: p["supershot"] = "Огненный суперудар"; p["role"] = "Форвард-ударник"
    elif p["active_elo"] >= 1420: p["supershot"] = "Суперудар Рыбка/Торпеда"; p["role"] = "Полузащитник"
    else: p["supershot"] = "Суперблок / Подкат"; p["role"] = "Защитник"

    if name in avatars:
        p["avatar"] = avatars[name]["avatar_url"]
        p["vk_name"] = avatars[name]["vk_name"]
        p["vk_id"] = avatars[name]["vk_id"]
        p["vk_domain"] = avatars[name]["domain"]
    else:
        p["avatar"] = default_avatars.get(name, f"https://api.dicebear.com/7.x/bottts/svg?seed={name}&backgroundColor=183c5c")
        p["vk_name"] = name
        p["vk_id"] = None
        p["vk_domain"] = None

    p["match_history"] = player_matches[name]

# Import seasons data
import prepare_site_data
seasons_list = prepare_site_data.seasons_data

# Attach matches to each season
for s in seasons_list:
    s_name = s["name"]
    s["matches"] = [m for m in combined_matches if m.get("season") == s_name]
    s["total_goals"] = sum(m["s1"] + m["s2"] for m in s["matches"])

site_payload = {
    "metadata": {
        "total_matches_analyzed": len(combined_matches),
        "total_goals_recorded": sum(m["s1"] + m["s2"] for m in combined_matches),
        "total_ot_pk_matches": sum(1 for m in combined_matches if m.get("ot") or m.get("pk")),
        "avg_goals_per_match": round(sum(m["s1"] + m["s2"] for m in combined_matches) / len(combined_matches), 2),
        "total_players_tracked": len(profiles)
    },
    "profiles": profiles,
    "seasons": seasons_list,
    "divisions": master_db["divisions"],
    "clutch_index": master_db["clutch_and_overtime_index"],
    "records": master_db["all_time_records"],
    "rivalries": master_db["kryptonite_rivalries"],
    "quotes": nst_quotes
}

json_str = json.dumps(site_payload, ensure_ascii=False)

html_template = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NEKKETSU SOCCER LEAGUE &bull; КИБЕРСПОРТИВНЫЙ ПОРТАЛ GOAL 3</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@600;700;800&family=Russo+One&display=swap" rel="stylesheet">
  <style>
    :root {
      --nes-bg: #183c5c;
      --nes-bg-dark: #0f263d;
      --nes-white: #ffffff;
      --nes-black: #000000;
      --nes-cyan: #2090d0;
      --nes-gold: #ffcc00;
      --nes-green: #39db48;
      --nes-red: #e63946;
      --font-clean: 'Rubik', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-title: 'Russo One', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--nes-bg);
      color: var(--nes-white);
      font-family: var(--font-clean);
      font-size: 14px;
      line-height: 1.6;
      min-height: 100vh;
      padding-bottom: 70px;
    }

    .container { max-width: 1360px; margin: 0 auto; padding: 0 20px; }

    /* Header */
    header {
      background: var(--nes-bg-dark);
      border-bottom: 3px solid var(--nes-white);
      padding: 16px 0;
      margin-bottom: 20px;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .header-inner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
    }
    .logo-area {
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
      color: #fff;
    }
    .logo-ball {
      width: 44px; height: 44px;
      background: #fff;
      border: 3px solid #000;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 24px;
      box-shadow: 3px 3px 0 #000;
    }
    .logo-titles h1 {
      font-family: var(--font-title);
      font-size: 22px;
      letter-spacing: 1px;
      color: #fff;
      text-shadow: 2px 2px 0 #000;
    }
    .logo-titles p {
      font-size: 12px;
      color: var(--nes-cyan);
      font-weight: 700;
      letter-spacing: 1px;
    }

    /* Nav Buttons */
    nav { display: flex; gap: 8px; flex-wrap: wrap; }
    .nav-btn {
      font-family: var(--font-title);
      font-size: 13px;
      background: var(--nes-bg);
      color: #fff;
      border: 2px solid var(--nes-white);
      padding: 9px 16px;
      cursor: pointer;
      box-shadow: 3px 3px 0 #000;
      transition: all 0.15s;
    }
    .nav-btn:hover {
      background: var(--nes-cyan);
      color: #000;
      border-color: var(--nes-white);
    }
    .nav-btn.active {
      background: var(--nes-gold);
      color: #000;
      border-color: #000;
      font-weight: 800;
    }

    /* NST Quotes Banner */
    .quotes-banner {
      background: #0d2238;
      border: 3px solid var(--nes-white);
      box-shadow: 4px 4px 0 #000;
      padding: 16px 20px;
      margin-bottom: 24px;
    }
    .quote-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .quote-badge {
      font-family: var(--font-title);
      font-size: 12px;
      color: var(--nes-gold);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .random-btn {
      background: var(--nes-bg);
      border: 2px solid var(--nes-white);
      color: #fff;
      font-family: var(--font-title);
      font-size: 11px;
      padding: 4px 10px;
      cursor: pointer;
      box-shadow: 2px 2px 0 #000;
    }
    .random-btn:hover { background: var(--nes-cyan); color: #000; }
    .quote-text {
      font-size: 15px;
      font-style: italic;
      color: #f1f5f9;
      line-height: 1.6;
      margin-bottom: 6px;
    }
    .quote-author {
      font-family: var(--font-title);
      font-size: 13px;
      color: var(--nes-cyan);
      text-align: right;
    }

    /* HUD Metrics Strip */
    .hud-metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }
    .hud-card {
      background: #0d2238;
      border: 2px solid var(--nes-white);
      box-shadow: 3px 3px 0 #000;
      padding: 14px 18px;
    }
    .hud-label {
      font-family: var(--font-title);
      font-size: 11px;
      color: #94a3b8;
      text-transform: uppercase;
    }
    .hud-val {
      font-family: var(--font-mono);
      font-size: 28px;
      font-weight: 800;
      color: #fff;
      margin-top: 4px;
    }
    .hud-sub {
      font-size: 12px;
      color: var(--nes-cyan);
      font-weight: 600;
    }

    /* Controls Bar */
    .controls-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 16px;
    }
    .filter-tabs { display: flex; gap: 8px; flex-wrap: wrap; }
    .filter-btn {
      background: var(--nes-bg);
      border: 2px solid var(--nes-white);
      color: #fff;
      font-family: var(--font-title);
      font-size: 12px;
      padding: 8px 14px;
      cursor: pointer;
      box-shadow: 2px 2px 0 #000;
    }
    .filter-btn.active {
      background: var(--nes-gold);
      color: #000;
      border-color: #000;
    }
    .filter-btn.inactive-tab {
      background: #331522;
      border-color: #f43f5e;
      color: #fda4af;
    }
    .filter-btn.inactive-tab.active {
      background: #f43f5e;
      color: #fff;
      border-color: #fff;
    }

    .clean-search {
      background: #0d2238;
      border: 2px solid var(--nes-white);
      color: #fff;
      font-family: var(--font-clean);
      font-size: 14px;
      font-weight: 600;
      padding: 8px 14px;
      outline: none;
      box-shadow: 2px 2px 0 #000;
      flex: 1;
      max-width: 320px;
    }

    /* Clean NES Table */
    .table-box {
      background: #0d2238;
      border: 3px solid var(--nes-white);
      box-shadow: 5px 5px 0 #000;
      overflow-x: auto;
      margin-bottom: 30px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }
    th {
      background: #081829;
      font-family: var(--font-title);
      font-size: 12px;
      color: var(--nes-gold);
      padding: 14px 12px;
      border-bottom: 2px solid var(--nes-white);
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
    }
    th:hover { color: #fff; }
    td {
      padding: 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.15);
      white-space: nowrap;
      font-weight: 500;
    }
    tr:hover td { background: rgba(32, 144, 208, 0.2); }

    /* Player cell */
    .p-cell {
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
    }
    .p-cell:hover .p-name { color: var(--nes-cyan); text-decoration: underline; }
    .avatar-clean {
      width: 40px; height: 40px;
      border: 2px solid var(--nes-white);
      box-shadow: 2px 2px 0 #000;
      object-fit: cover;
      background: #000;
    }
    .p-name { font-weight: 700; font-size: 15px; color: #fff; }
    .p-sub { font-size: 12px; color: var(--nes-cyan); }

    /* Division Badges */
    .league-badge {
      display: inline-block;
      font-family: var(--font-title);
      font-size: 11px;
      padding: 3px 8px;
      border: 1px solid #000;
      box-shadow: 2px 2px 0 #000;
    }
    .badge-premier { background: var(--nes-gold); color: #000; }
    .badge-middle { background: var(--nes-cyan); color: #000; }
    .badge-yard { background: var(--nes-green); color: #000; }
    .badge-inactive { background: #e11d48; color: #fff; }

    /* Cards Grid */
    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
      gap: 18px;
    }
    .clean-card {
      background: #0d2238;
      border: 3px solid var(--nes-white);
      box-shadow: 4px 4px 0 #000;
      padding: 18px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .clean-card:hover {
      border-color: var(--nes-cyan);
      transform: translateY(-2px);
      box-shadow: 6px 6px 0 #000;
    }
    .card-top {
      display: flex;
      gap: 14px;
      align-items: center;
      margin-bottom: 14px;
    }
    .card-top .avatar-clean { width: 54px; height: 54px; }
    .card-top h3 { font-family: var(--font-title); font-size: 18px; color: #fff; }
    .card-stat-strip {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      background: #081829;
      border: 1px solid rgba(255, 255, 255, 0.2);
      padding: 10px;
      text-align: center;
      margin-bottom: 12px;
    }
    .card-stat-strip .lbl { font-size: 11px; color: #94a3b8; font-weight: 600; }
    .card-stat-strip .v { font-family: var(--font-mono); font-size: 16px; font-weight: 800; color: #fff; margin-top: 2px; }

    /* Modal / Tactical Dressing Room */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.85);
      z-index: 1000;
      overflow-y: auto;
      padding: 30px 16px;
    }
    .modal-overlay.active { display: flex; justify-content: center; align-items: flex-start; }
    .modal-sheet {
      background: #0d2238;
      border: 4px solid var(--nes-white);
      box-shadow: 10px 10px 0 #000;
      width: 100%;
      max-width: 960px;
      position: relative;
    }
    .modal-close {
      position: absolute;
      top: 14px; right: 14px;
      background: #000;
      color: #fff;
      border: 2px solid var(--nes-white);
      font-family: var(--font-title);
      font-size: 13px;
      padding: 6px 12px;
      cursor: pointer;
    }
    .modal-close:hover { background: var(--nes-red); }

    .modal-header-box {
      background: #081829;
      border-bottom: 3px solid var(--nes-white);
      padding: 26px 30px;
      display: flex;
      gap: 20px;
      align-items: center;
      flex-wrap: wrap;
    }
    .modal-avatar-big {
      width: 84px; height: 84px;
      border: 3px solid var(--nes-white);
      box-shadow: 4px 4px 0 #000;
      object-fit: cover;
      background: #000;
    }
    .modal-title-box h2 {
      font-family: var(--font-title);
      font-size: 26px;
      color: #fff;
      text-shadow: 2px 2px 0 #000;
    }
    .vk-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #0077ff;
      color: #fff;
      text-decoration: none;
      font-family: var(--font-title);
      font-size: 11px;
      padding: 6px 12px;
      border: 2px solid #fff;
      box-shadow: 2px 2px 0 #000;
      margin-top: 8px;
    }

    .modal-body-content { padding: 26px 30px; }
    .metric-tiles {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }
    .metric-tile {
      background: #081829;
      border: 2px solid rgba(255, 255, 255, 0.3);
      padding: 12px;
      text-align: center;
      box-shadow: 2px 2px 0 #000;
    }
    .metric-tile .l { font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase; }
    .metric-tile .num { font-family: var(--font-mono); font-size: 22px; font-weight: 800; color: #fff; margin-top: 2px; }

    .block-header {
      font-family: var(--font-title);
      font-size: 14px;
      color: var(--nes-gold);
      margin: 22px 0 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    /* Match History Row */
    .match-history-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #081829;
      border: 1px solid rgba(255, 255, 255, 0.2);
      padding: 10px 14px;
      margin-bottom: 6px;
      font-weight: 600;
      font-size: 13px;
    }
    .match-history-row .score-badge {
      font-family: var(--font-mono);
      font-size: 15px;
      font-weight: 800;
      color: var(--nes-gold);
      background: #000;
      border: 1px solid var(--nes-white);
      padding: 2px 10px;
    }

    /* Seasons Stage Tabs */
    .seasons-nav-bar {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 10px;
      margin-bottom: 20px;
    }
    .season-tab-btn {
      background: var(--nes-bg);
      border: 2px solid var(--nes-white);
      color: #fff;
      font-family: var(--font-title);
      font-size: 12px;
      padding: 10px 16px;
      cursor: pointer;
      box-shadow: 3px 3px 0 #000;
      white-space: nowrap;
    }
    .season-tab-btn.active {
      background: var(--nes-cyan);
      color: #000;
      border-color: #000;
      font-weight: 800;
    }

    .season-card-box {
      background: #0d2238;
      border: 3px solid var(--nes-white);
      box-shadow: 6px 6px 0 #000;
      padding: 26px;
      margin-bottom: 30px;
    }
    .podium-tiles {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 14px;
      margin: 20px 0;
    }
    .podium-tile {
      background: #081829;
      border: 2px solid var(--nes-white);
      padding: 14px;
      text-align: center;
      box-shadow: 3px 3px 0 #000;
    }
    .podium-tile.gold-tile { border-color: var(--nes-gold); }

    .story-box {
      background: #081829;
      border-left: 4px solid var(--nes-cyan);
      padding: 16px 20px;
      font-size: 15px;
      line-height: 1.7;
      margin-bottom: 22px;
    }

    /* Screen views */
    .view-content { display: none; }
    .view-content.active { display: block; }

    /* Footer */
    footer {
      background: var(--nes-bg-dark);
      border-top: 3px solid var(--nes-white);
      padding: 30px 0;
      text-align: center;
      font-size: 13px;
      color: #94a3b8;
    }
    footer a { color: var(--nes-cyan); text-decoration: none; font-weight: 700; }
    footer a:hover { text-decoration: underline; }

    @media (max-width: 768px) {
      .header-inner { flex-direction: column; text-align: center; }
      nav { justify-content: center; }
      .metric-tiles { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="container header-inner">
      <a href="#/leaderboard" class="logo-area">
        <div class="logo-ball">⚽</div>
        <div class="logo-titles">
          <h1>NEKKETSU SOCCER LEAGUE</h1>
          <p>КИБЕРСПОРТИВНЫЙ ПОРТАЛ СТАТИСТИКИ GOAL 3</p>
        </div>
      </a>

      <nav>
        <button class="nav-btn active" onclick="switchTab('leaderboard')">🏆 Рейтинг</button>
        <button class="nav-btn" onclick="switchTab('players')">👤 Игроки</button>
        <button class="nav-btn" onclick="switchTab('seasons')">📅 Сезоны (1–9)</button>
        <button class="nav-btn" onclick="switchTab('clutch')">⚡ Клатч / Рекорды</button>
        <button class="nav-btn" onclick="switchTab('h2h')">⚔️ Очные Дуэли</button>
      </nav>
    </div>
  </header>

  <main class="container">

    <!-- Random Quote Widget -->
    <div class="quotes-banner">
      <div class="quote-header">
        <span class="quote-badge">💬 ЦИТАТНИК NST (Случайная мудрость)</span>
        <button class="random-btn" onclick="nextRandomQuote()">🎲 Другая цитата</button>
      </div>
      <div class="quote-text" id="quoteText">«Загрузка цитаты...»</div>
      <div class="quote-author" id="quoteAuthor"></div>
    </div>

    <!-- HUD Metrics -->
    <div class="hud-metrics" id="hudStrip"></div>

    <!-- TAB 1: LEADERBOARD -->
    <section id="tab-leaderboard" class="view-content active">
      <div class="controls-row">
        <div class="filter-tabs">
          <button class="filter-btn active" onclick="filterDivision('active', this)">▶ Все активные игроки</button>
          <button class="filter-btn" onclick="filterDivision('Высшая', this)">Высшая лига</button>
          <button class="filter-btn" onclick="filterDivision('Средняя', this)">Средняя лига</button>
          <button class="filter-btn" onclick="filterDivision('Дворовая', this)">Дворовая лига</button>
          <button class="filter-btn inactive-tab" onclick="filterDivision('inactive', this)">💤 Неактив / Зал славы</button>
        </div>
        <input type="text" class="clean-search" id="tableSearch" placeholder="Поиск по имени или нику..." oninput="renderTable()">
      </div>

      <div class="table-box">
        <table>
          <thead>
            <tr>
              <th onclick="sortTable('rank')">#</th>
              <th onclick="sortTable('player')">Игрок</th>
              <th onclick="sortTable('league')">Лига</th>
              <th onclick="sortTable('active_elo')">Active Elo</th>
              <th onclick="sortTable('peak_elo')">Peak Elo</th>
              <th onclick="sortTable('matches')">Игры</th>
              <th onclick="sortTable('wins')">В - П</th>
              <th onclick="sortTable('win_rate')">Побед %</th>
              <th onclick="sortTable('reg_wins')">Осн / ОТ / Пен</th>
              <th onclick="sortTable('goal_diff')">Мячи (+/-)</th>
              <th onclick="sortTable('gapg')">Пропущено/м</th>
              <th onclick="sortTable('dominator_score')">Score</th>
            </tr>
          </thead>
          <tbody id="tableBody"></tbody>
        </table>
      </div>
    </section>

    <!-- TAB 2: PLAYERS (CARDS) -->
    <section id="tab-players" class="view-content">
      <div class="controls-row">
        <input type="text" class="clean-search" id="cardsSearch" style="max-width: 100%;" placeholder="Поиск игрока по нику, роли или суперудару..." oninput="renderCards()">
      </div>
      <div class="cards-grid" id="cardsGrid"></div>
    </section>

    <!-- TAB 3: SEASONS (ALL 9 SEASONS WITH MATCHES!) -->
    <section id="tab-seasons" class="view-content">
      <div class="seasons-nav-bar" id="seasonsBar"></div>
      <div id="seasonDetails"></div>
    </section>

    <!-- TAB 4: CLUTCH & RECORDS -->
    <section id="tab-clutch" class="view-content">
      <div class="block-header">⚡ Клатч-индекс (Победы в Овертаймах и Сериях Буллитов)</div>
      <div class="table-box" style="margin-bottom: 24px;">
        <table>
          <thead>
            <tr>
              <th>Игрок</th>
              <th>Игр в ОТ/PK</th>
              <th>Побед в ОТ</th>
              <th>Буллиты (PK)</th>
              <th>Всего Клатч-W</th>
              <th>Клатч Winrate</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody id="clutchTableBody"></tbody>
        </table>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px;">
        <div class="table-box" style="padding: 18px;">
          <div class="block-header" style="margin-top: 0; color: var(--nes-cyan);">🔥 Топ-10 Триллеров Лиги</div>
          <div id="thrillersList"></div>
        </div>
        <div class="table-box" style="padding: 18px;">
          <div class="block-header" style="margin-top: 0; color: var(--nes-red);">💥 Самые Крупные Разгромы</div>
          <div id="blowoutsList"></div>
        </div>
      </div>
    </section>

    <!-- TAB 5: H2H -->
    <section id="tab-h2h" class="view-content">
      <div class="table-box" style="padding: 24px; margin-bottom: 20px;">
        <div class="block-header" style="margin-top: 0;">⚔️ Калькулятор Очных Встреч (Head-to-Head)</div>
        <p style="color: #94a3b8; font-size: 14px; margin-bottom: 16px;">Выберите двух игроков, чтобы увидеть полную статистику их личных встреч за все 9 сезонов.</p>
        
        <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
          <select id="h2hPlayer1" class="filter-btn" style="flex: 1; max-width: 280px;" onchange="calculateH2H()"></select>
          <span style="font-family: var(--font-title); font-size: 18px; color: var(--nes-gold);">VS</span>
          <select id="h2hPlayer2" class="filter-btn" style="flex: 1; max-width: 280px;" onchange="calculateH2H()"></select>
        </div>
      </div>

      <div id="h2hResult"></div>
    </section>

  </main>

  <!-- Player Profile Modal (Tactical Sheet) -->
  <div class="modal-overlay" id="playerModal" onclick="closeModal(event)">
    <div class="modal-sheet" onclick="event.stopPropagation()">
      <button class="modal-close" onclick="closeModalDirect()">✕ Закрыть</button>
      <div class="modal-header-box" id="modalHeader"></div>
      <div class="modal-body-content" id="modalBody"></div>
    </div>
  </div>

  <!-- Footer -->
  <footer>
    <div class="container">
      <p>NEKKETSU SPORTS TOURNAMENTS &bull; KUNIO-KUN NO NEKKETSU SOCCER LEAGUE</p>
      <p>Официальное сообщество: <a href="https://vk.ru/nekketsu" target="_blank">vk.ru/nekketsu</a> &bull; Автономный датасет Antigravity</p>
    </div>
  </footer>

  <!-- Embedded Complete Dataset -->
  <script>
    const DATA = __DATA_PLACEHOLDER__;
  </script>

  <!-- Main Logic Script -->
  <script>
    let currentDivisionFilter = 'active';
    let currentSortColumn = 'active_elo';
    let sortAsc = false;
    let selectedSeasonId = '9';

    window.addEventListener('DOMContentLoaded', () => {
      initQuotes();
      renderHUD();
      renderTable();
      renderCards();
      renderSeasonsBar();
      renderSeasonDetails(selectedSeasonId);
      renderClutch();
      initH2H();

      window.addEventListener('hashchange', handleRouting);
      handleRouting();
    });

    // Random Quotes
    function initQuotes() {
      nextRandomQuote();
    }
    function nextRandomQuote() {
      if (!DATA.quotes || DATA.quotes.length === 0) return;
      const idx = Math.floor(Math.random() * DATA.quotes.length);
      const q = DATA.quotes[idx];
      document.getElementById('quoteText').innerText = `«${q.text}»`;
      document.getElementById('quoteAuthor').innerText = q.author ? `(c) ${q.author}` : '(c) NST';
    }

    function handleRouting() {
      const hash = window.location.hash || '#/leaderboard';
      if (hash.startsWith('#/player/')) {
        const pName = decodeURIComponent(hash.replace('#/player/', ''));
        openPlayerModal(pName);
      } else if (hash.startsWith('#/season/')) {
        const sId = hash.replace('#/season/', '');
        switchTab('seasons');
        selectSeason(sId);
      } else if (hash === '#/players') {
        switchTab('players');
      } else if (hash === '#/seasons') {
        switchTab('seasons');
      } else if (hash === '#/clutch') {
        switchTab('clutch');
      } else if (hash === '#/h2h') {
        switchTab('h2h');
      } else {
        switchTab('leaderboard');
      }
    }

    function switchTab(tabId) {
      document.querySelectorAll('.view-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

      const activeSection = document.getElementById(`tab-${tabId}`);
      if (activeSection) activeSection.classList.add('active');

      const activeBtn = Array.from(document.querySelectorAll('.nav-btn')).find(b => b.getAttribute('onclick').includes(tabId));
      if (activeBtn) activeBtn.classList.add('active');
    }

    function renderHUD() {
      const m = DATA.metadata;
      document.getElementById('hudStrip').innerHTML = `
        <div class="hud-card">
          <div class="hud-label">Всего матчей в базе</div>
          <div class="hud-val">${m.total_matches_analyzed}</div>
          <div class="hud-sub">Сезоны 1–9 полностью</div>
        </div>
        <div class="hud-card">
          <div class="hud-label">Забито голов</div>
          <div class="hud-val" style="color: var(--nes-gold);">${m.total_goals_recorded}</div>
          <div class="hud-sub">В ср. ${m.avg_goals_per_match} за игру</div>
        </div>
        <div class="hud-card">
          <div class="hud-label">Овертаймы и Буллиты</div>
          <div class="hud-val" style="color: var(--nes-cyan);">${m.total_ot_pk_matches}</div>
          <div class="hud-sub">18.4% валидольных матчей</div>
        </div>
        <div class="hud-card">
          <div class="hud-label">Игроков в системе</div>
          <div class="hud-val" style="color: var(--nes-green);">${m.total_players_tracked}</div>
          <div class="hud-sub">VK аватары привязаны</div>
        </div>
      `;
    }

    function filterDivision(div, btn) {
      currentDivisionFilter = div;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTable();
    }

    function sortTable(col) {
      if (currentSortColumn === col) sortAsc = !sortAsc;
      else { currentSortColumn = col; sortAsc = false; }
      renderTable();
    }

    function renderTable() {
      const q = (document.getElementById('tableSearch')?.value || '').toLowerCase();
      let list = [...DATA.profiles];

      if (currentDivisionFilter === 'active') {
        list = list.filter(p => p.status === 'АКТИВЕН');
      } else if (currentDivisionFilter === 'inactive') {
        list = list.filter(p => p.status === 'ИНАКТИВЕН');
      } else if (currentDivisionFilter !== 'all') {
        list = list.filter(p => p.league === currentDivisionFilter);
      }

      if (q) {
        list = list.filter(p => p.player.toLowerCase().includes(q) || (p.vk_name && p.vk_name.toLowerCase().includes(q)));
      }

      list.sort((a, b) => {
        let v1 = a[currentSortColumn];
        let v2 = b[currentSortColumn];
        if (typeof v1 === 'string') return sortAsc ? v1.localeCompare(v2) : v2.localeCompare(v1);
        return sortAsc ? (v1 - v2) : (v2 - v1);
      });

      const tbody = document.getElementById('tableBody');
      tbody.innerHTML = list.map((p, idx) => {
        const gdStr = p.goal_diff > 0 ? `+${p.goal_diff}` : `${p.goal_diff}`;
        const gdColor = p.goal_diff > 0 ? 'var(--nes-green)' : (p.goal_diff < 0 ? 'var(--nes-red)' : '#fff');
        const badgeClass = p.status === 'ИНАКТИВЕН' ? 'badge-inactive' : (p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard'));

        return `
          <tr>
            <td style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold);">${idx + 1}</td>
            <td>
              <div class="p-cell" onclick="openPlayerModal('${p.player}')">
                <img src="${p.avatar}" class="avatar-clean" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
                <div>
                  <div class="p-name">${p.player}</div>
                  <div class="p-sub">${p.vk_name !== p.player ? p.vk_name : p.role}</div>
                </div>
              </div>
            </td>
            <td><span class="league-badge ${badgeClass}">${p.status === 'ИНАКТИВЕН' ? 'НЕАКТИВ' : p.league}</span></td>
            <td>
              <div style="font-family: var(--font-mono); font-weight: 800; font-size: 15px; color: #fff;">${p.active_elo.toFixed(1)}</div>
              ${p.decay_penalty > 0 ? `<div style="font-size: 11px; color: var(--nes-red); font-weight: 700;">-${p.decay_penalty} decay</div>` : ''}
            </td>
            <td><span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold);">${p.peak_elo.toFixed(1)}</span></td>
            <td style="font-family: var(--font-mono); font-weight: 700;">${p.matches}</td>
            <td style="font-family: var(--font-mono);"><strong style="color: var(--nes-green);">${p.wins}</strong> - <strong style="color: var(--nes-red);">${p.losses}</strong></td>
            <td><strong style="font-family: var(--font-mono); color: ${p.win_rate >= 60 ? 'var(--nes-green)' : (p.win_rate >= 45 ? '#fff' : 'var(--nes-red)')};">${p.win_rate}%</strong></td>
            <td style="font-family: var(--font-mono); font-size: 13px;">
              <span>${p.reg_wins}</span> / <span style="color: var(--nes-gold); font-weight: 800;">${p.ot_wins}</span> / <span style="color: #c084fc; font-weight: 800;">${p.pk_wins}</span>
            </td>
            <td style="font-family: var(--font-mono);"><strong style="color: ${gdColor};">${gdStr}</strong> <span style="color: #94a3b8; font-size: 12px;">(${p.goals_for}:${p.goals_against})</span></td>
            <td style="font-family: var(--font-mono);">${p.gapg.toFixed(2)}</td>
            <td><strong style="font-family: var(--font-mono); color: var(--nes-gold);">${p.dominator_score.toFixed(1)}</strong></td>
          </tr>
        `;
      }).join('');
    }

    // Cards Grid
    function renderCards() {
      const q = (document.getElementById('cardsSearch')?.value || '').toLowerCase();
      let list = DATA.profiles.filter(p => 
        p.player.toLowerCase().includes(q) || 
        p.league.toLowerCase().includes(q) || 
        (p.role && p.role.toLowerCase().includes(q)) || 
        (p.supershot && p.supershot.toLowerCase().includes(q))
      );

      const grid = document.getElementById('cardsGrid');
      grid.innerHTML = list.map(p => {
        const badgeClass = p.status === 'ИНАКТИВЕН' ? 'badge-inactive' : (p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard'));
        const gdStr = p.goal_diff > 0 ? `+${p.goal_diff}` : `${p.goal_diff}`;

        return `
          <div class="clean-card" onclick="openPlayerModal('${p.player}')">
            <div class="card-top">
              <img src="${p.avatar}" class="avatar-clean" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
              <div style="flex: 1;">
                <h3>${p.player}</h3>
                <div style="font-size: 12px; color: var(--nes-gold); font-weight: 600;">${p.supershot}</div>
                <div style="margin-top: 4px;">
                  <span class="league-badge ${badgeClass}">${p.status === 'ИНАКТИВЕН' ? 'НЕАКТИВ' : p.league}</span>
                </div>
              </div>
            </div>

            <div class="card-stat-strip">
              <div>
                <div class="lbl">ACTIVE ELO</div>
                <div class="v" style="color: var(--nes-gold);">${p.active_elo.toFixed(1)}</div>
              </div>
              <div>
                <div class="lbl">WIN RATE</div>
                <div class="v" style="color: var(--nes-green);">${p.win_rate}%</div>
              </div>
              <div>
                <div class="lbl">МЯЧИ (+/-)</div>
                <div class="v">${gdStr}</div>
              </div>
            </div>

            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; font-weight: 600;">
              <span>Матчи: <strong>${p.matches}</strong></span>
              <span>Осн: <strong style="color: #fff;">${p.reg_wins}W</strong></span>
              <span>ОТ/PK: <strong style="color: var(--nes-cyan);">${p.ot_wins+p.pk_wins}W</strong></span>
            </div>
          </div>
        `;
      }).join('');
    }

    // Modal
    function openPlayerModal(pName) {
      const p = DATA.profiles.find(x => x.player.toLowerCase() === pName.toLowerCase());
      if (!p) return;

      window.location.hash = `#/player/${p.player}`;

      const header = document.getElementById('modalHeader');
      const body = document.getElementById('modalBody');
      const badgeClass = p.status === 'ИНАКТИВЕН' ? 'badge-inactive' : (p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard'));
      const vkLink = p.vk_domain ? `https://vk.ru/${p.vk_domain}` : (p.vk_id ? `https://vk.ru/id${p.vk_id}` : null);

      header.innerHTML = `
        <img src="${p.avatar}" class="modal-avatar-big" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
        <div class="modal-title-box">
          <h2>${p.player}</h2>
          <div style="font-size: 14px; color: var(--nes-gold); font-weight: 700;">${p.vk_name} &bull; ${p.role} &bull; ${p.supershot}</div>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 6px;">
            <span class="league-badge ${badgeClass}">${p.status === 'ИНАКТИВЕН' ? 'НЕАКТИВЕН' : `${p.league} лига`}</span>
            ${vkLink ? `<a href="${vkLink}" target="_blank" class="vk-btn">Профиль ВКонтакте ↗</a>` : ''}
          </div>
        </div>
      `;

      const matchRows = (p.match_history || []).slice(0, 40).map(m => {
        const resColor = m.result === 'W' ? 'var(--nes-green)' : (m.result === 'L' ? 'var(--nes-red)' : '#fff');
        const oppObj = DATA.profiles.find(x => x.player === m.opponent);
        const oppAvatar = oppObj ? oppObj.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.opponent}`;

        return `
          <div class="match-history-row">
            <div style="display: flex; align-items: center; gap: 10px; flex: 1;">
              <span style="font-family: var(--font-mono); font-weight: 900; color: ${resColor}; width: 24px;">${m.result}</span>
              <span>${p.player}</span>
            </div>
            <div class="score-badge">
              ${m.score_for} : ${m.score_against}
              ${m.pk ? '<span style="font-size: 11px; color: #c084fc; margin-left: 6px;">[PK]</span>' : (m.ot ? '<span style="font-size: 11px; color: var(--nes-gold); margin-left: 6px;">[OT]</span>' : '')}
            </div>
            <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.opponent}')">
              <span>${m.opponent}</span>
              <img src="${oppAvatar}" style="width: 24px; height: 24px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.opponent}'">
            </div>
          </div>
        `;
      }).join('');

      body.innerHTML = `
        <div class="metric-tiles">
          <div class="metric-tile">
            <div class="l">Active Elo</div>
            <div class="num" style="color: var(--nes-gold);">${p.active_elo.toFixed(1)}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Peak Elo</div>
            <div class="num">${p.peak_elo.toFixed(1)}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Time-Decay</div>
            <div class="num" style="color: ${p.decay_penalty > 0 ? 'var(--nes-red)' : 'var(--nes-green)'};">-${p.decay_penalty}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Матчи всего</div>
            <div class="num">${p.matches}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Победы / Пораж</div>
            <div class="num">${p.wins} - ${p.losses}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Winrate %</div>
            <div class="num" style="color: var(--nes-green);">${p.win_rate}%</div>
          </div>
          <div class="metric-tile">
            <div class="l">Мячи (+/-)</div>
            <div class="num">${p.goals_for}:${p.goals_against}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Сухие игры</div>
            <div class="num">${p.clean_sheets}</div>
          </div>
        </div>

        <div class="block-header">🎯 Структура побед (Основное время vs Овертайм vs Буллиты)</div>
        <div style="background: #081829; border: 2px solid rgba(255,255,255,0.2); padding: 14px; margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; margin-bottom: 8px;">
            <span>Основное время: <strong style="color: var(--nes-cyan);">${p.reg_wins}W</strong></span>
            <span>Овертаймы (OT): <strong style="color: var(--nes-gold);">${p.ot_wins}W</strong></span>
            <span>Буллиты (PK): <strong style="color: #c084fc;">${p.pk_wins}W</strong></span>
            <span>Клатч WR: <strong style="color: var(--nes-green);">${p.clutch_win_rate}%</strong> (${p.clutch_wins}/${p.clutch_total})</span>
          </div>
          <div style="display: flex; height: 14px; border: 1px solid #fff; background: #000;">
            <div style="width: ${p.wins > 0 ? (p.reg_wins/p.wins*100) : 0}%; background: var(--nes-cyan);"></div>
            <div style="width: ${p.wins > 0 ? (p.ot_wins/p.wins*100) : 0}%; background: var(--nes-gold);"></div>
            <div style="width: ${p.wins > 0 ? (p.pk_wins/p.wins*100) : 0}%; background: #c084fc;"></div>
          </div>
        </div>

        <div class="block-header">📜 История официальных турнирных матчей (${p.match_history ? p.match_history.length : 0} игр)</div>
        <div style="max-height: 360px; overflow-y: auto;">
          ${matchRows || '<p style="color: #94a3b8; padding: 10px;">Матчи в базе не найдены</p>'}
        </div>
      `;

      document.getElementById('playerModal').classList.add('active');
    }

    function closeModal(e) {
      if (e.target.id === 'playerModal') closeModalDirect();
    }
    function closeModalDirect() {
      document.getElementById('playerModal').classList.remove('active');
      window.location.hash = '#/leaderboard';
    }

    // Seasons Module
    function renderSeasonsBar() {
      const bar = document.getElementById('seasonsBar');
      bar.innerHTML = DATA.seasons.map(s => `
        <button class="season-tab-btn ${s.id === selectedSeasonId ? 'active' : ''}" onclick="selectSeason('${s.id}')">
          ${s.name} (${s.year})
        </button>
      `).join('');
    }

    function selectSeason(sId) {
      selectedSeasonId = sId;
      renderSeasonsBar();
      renderSeasonDetails(sId);
    }

    function renderSeasonDetails(sId) {
      const s = DATA.seasons.find(x => x.id === sId);
      if (!s) return;

      const card = document.getElementById('seasonDetails');
      const matchesList = (s.matches || []).slice(0, 45).map(m => `
        <div class="match-history-row">
          <div style="flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p1}')">${m.p1}</div>
          <div class="score-badge">
            ${m.s1} : ${m.s2}
            ${m.pk ? '<span style="font-size: 11px; color: #c084fc; margin-left: 6px;">[PK]</span>' : (m.ot ? '<span style="font-size: 11px; color: var(--nes-gold); margin-left: 6px;">[OT]</span>' : '')}
          </div>
          <div style="flex: 1; text-align: right; cursor: pointer;" onclick="openPlayerModal('${m.p2}')">${m.p2}</div>
        </div>
      `).join('');

      card.innerHTML = `
        <div class="season-card-box">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 16px;">
            <div>
              <span class="league-badge badge-premier">${s.year} ГОД</span>
              <h2 style="font-family: var(--font-title); font-size: 24px; color: #fff; margin-top: 4px;">${s.name} &bull; Сольный Чемпионат NST</h2>
              <div style="font-size: 13px; color: #94a3b8; margin-top: 2px;">${s.format} | Участников: <strong>${s.participants}</strong> | Ром: ${s.emulator}</div>
            </div>
            <div style="text-align: right;">
              <div style="font-family: var(--font-title); font-size: 11px; color: var(--nes-gold);">МАТЧЕЙ В БАЗЕ</div>
              <div style="font-family: var(--font-mono); font-size: 32px; font-weight: 800; color: #fff;">${s.matches ? s.matches.length : 0}</div>
            </div>
          </div>

          <div class="podium-tiles">
            <div class="podium-tile gold-tile">
              <div style="font-family: var(--font-title); font-size: 12px; color: var(--nes-gold);">🥇 ЧЕМПИОН ВЫШКИ</div>
              <div style="font-size: 18px; font-weight: 800; cursor: pointer; margin-top: 4px;" onclick="openPlayerModal('${s.champion}')">${s.champion}</div>
            </div>
            <div class="podium-tile">
              <div style="font-family: var(--font-title); font-size: 12px; color: #cbd5e1;">🥈 2-Е МЕСТО</div>
              <div style="font-size: 18px; font-weight: 800; cursor: pointer; margin-top: 4px;" onclick="openPlayerModal('${s.runner_up}')">${s.runner_up}</div>
            </div>
            <div class="podium-tile">
              <div style="font-family: var(--font-title); font-size: 12px; color: #f97316;">🥉 3-Е МЕСТО</div>
              <div style="font-size: 18px; font-weight: 800; cursor: pointer; margin-top: 4px;" onclick="openPlayerModal('${s.third_place}')">${s.third_place}</div>
            </div>
            <div class="podium-tile" style="border-color: #c084fc;">
              <div style="font-family: var(--font-title); font-size: 12px; color: #c084fc;">🏆 КУБОК ЛИГ</div>
              <div style="font-size: 18px; font-weight: 800; cursor: pointer; margin-top: 4px;" onclick="openPlayerModal('${s.cup_winner}')">${s.cup_winner}</div>
            </div>
          </div>

          <div class="block-header">📖 Летопись и События Сезона</div>
          <div class="story-box">${s.summary}</div>

          <div class="block-header">⚽ Протоколы официальных матчей сезона (${s.matches ? s.matches.length : 0} игр)</div>
          <div style="max-height: 400px; overflow-y: auto; border: 2px solid rgba(255,255,255,0.2); padding: 12px;">
            ${matchesList || '<p style="color: #94a3b8; padding: 10px;">Матчи сезона в архиве</p>'}
          </div>
        </div>
      `;
    }

    // Clutch
    function renderClutch() {
      const tbody = document.getElementById('clutchTableBody');
      const list = [...DATA.profiles].filter(p => p.clutch_total >= 2).sort((a,b) => b.clutch_win_rate - a.clutch_win_rate || b.clutch_wins - a.clutch_wins);

      tbody.innerHTML = list.map(p => `
        <tr>
          <td>
            <div class="p-cell" onclick="openPlayerModal('${p.player}')">
              <img src="${p.avatar}" class="avatar-clean" style="width: 32px; height: 32px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
              <span class="p-name">${p.player}</span>
            </div>
          </td>
          <td style="font-family: var(--font-mono); font-weight: 800;">${p.clutch_total}</td>
          <td style="font-family: var(--font-mono); color: var(--nes-gold); font-weight: 800;">${p.ot_wins}</td>
          <td style="font-family: var(--font-mono); color: #c084fc; font-weight: 800;">${p.pk_wins}</td>
          <td style="font-family: var(--font-mono); color: var(--nes-green); font-weight: 800;">${p.clutch_wins}</td>
          <td style="font-family: var(--font-mono); font-weight: 800; color: ${p.clutch_win_rate >= 60 ? 'var(--nes-green)' : '#fff'};">${p.clutch_win_rate}%</td>
          <td><span class="league-badge ${p.status === 'ИНАКТИВЕН' ? 'badge-inactive' : 'badge-premier'}">${p.status}</span></td>
        </tr>
      `).join('');

      document.getElementById('thrillersList').innerHTML = (DATA.records.top_thrillers || []).slice(0, 10).map(t => `
        <div class="match-history-row">
          <span>${t.p1} VS ${t.p2}</span>
          <span style="color: var(--nes-gold); font-family: var(--font-mono); font-weight: 800;">${t.s1}:${t.s2} (${t.total_goals} голов)</span>
        </div>
      `).join('');

      document.getElementById('blowoutsList').innerHTML = (DATA.records.top_blowouts || []).slice(0, 10).map(b => `
        <div class="match-history-row">
          <span>${b.winner} VS ${b.loser}</span>
          <span style="color: var(--nes-red); font-family: var(--font-mono); font-weight: 800;">${b.s_win}:${b.s_lose} (+${b.diff})</span>
        </div>
      `).join('');
    }

    // H2H
    function initH2H() {
      const s1 = document.getElementById('h2hPlayer1');
      const s2 = document.getElementById('h2hPlayer2');
      const options = DATA.profiles.map(p => `<option value="${p.player}">${p.player} (${p.league})</option>`).join('');
      s1.innerHTML = options;
      s2.innerHTML = options;

      s1.value = 'ectoPower';
      s2.value = 'Aeris';
      calculateH2H();
    }

    function calculateH2H() {
      const p1 = document.getElementById('h2hPlayer1').value;
      const p2 = document.getElementById('h2hPlayer2').value;
      const res = document.getElementById('h2hResult');

      if (p1 === p2) {
        res.innerHTML = '<p style="color: var(--nes-red); padding: 14px; font-weight: 700;">Выберите двух разных игроков.</p>';
        return;
      }

      const p1Obj = DATA.profiles.find(x => x.player === p1);
      const p2Obj = DATA.profiles.find(x => x.player === p2);

      const duels = (p1Obj.match_history || []).filter(m => m.opponent === p2);
      const p1Wins = duels.filter(m => m.result === 'W').length;
      const p2Wins = duels.filter(m => m.result === 'L').length;
      const draws = duels.filter(m => m.result === 'D').length;
      const p1Goals = duels.reduce((acc, m) => acc + m.score_for, 0);
      const p2Goals = duels.reduce((acc, m) => acc + m.score_against, 0);

      const duelsHtml = duels.map(m => `
        <div class="match-history-row">
          <div style="flex: 1;">
            <strong style="color: ${m.result === 'W' ? 'var(--nes-green)' : (m.result === 'L' ? 'var(--nes-red)' : '#fff')};">[${m.result}]</strong>
            <span>${p1}</span>
          </div>
          <div class="score-badge">
            ${m.score_for} : ${m.score_against}
            ${m.pk ? '<span style="font-size: 11px; color: #c084fc; margin-left: 6px;">[PK]</span>' : (m.ot ? '<span style="font-size: 11px; color: var(--nes-gold); margin-left: 6px;">[OT]</span>' : '')}
          </div>
          <div style="flex: 1; text-align: right;">
            <span>${p2}</span>
          </div>
        </div>
      `).join('');

      res.innerHTML = `
        <div class="table-box" style="padding: 24px;">
          <div style="display: flex; justify-content: space-around; align-items: center; margin-bottom: 20px; text-align: center;">
            <div onclick="openPlayerModal('${p1}')" style="cursor: pointer;">
              <img src="${p1Obj.avatar}" style="width: 74px; height: 74px; border: 3px solid var(--nes-white); box-shadow: 4px 4px 0 #000;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p1}'">
              <h3 style="font-family: var(--font-title); font-size: 20px; color: #fff; margin-top: 6px;">${p1}</h3>
              <p style="color: var(--nes-gold); font-family: var(--font-mono); font-weight: 800;">${p1Obj.active_elo.toFixed(1)} Elo</p>
            </div>

            <div>
              <div style="font-family: var(--font-mono); font-size: 44px; font-weight: 900; line-height: 1;">
                <span style="color: var(--nes-green);">${p1Wins}</span>
                <span style="color: #94a3b8; font-size: 28px;"> : </span>
                <span style="color: var(--nes-red);">${p2Wins}</span>
              </div>
              ${draws > 0 ? `<div style="font-size: 12px; color: var(--nes-gold); font-weight: 700; margin-top: 4px;">${draws} ничьих</div>` : ''}
              <div style="font-family: var(--font-mono); font-size: 13px; color: #94a3b8; margin-top: 4px;">Мячи: ${p1Goals} - ${p2Goals}</div>
            </div>

            <div onclick="openPlayerModal('${p2}')" style="cursor: pointer;">
              <img src="${p2Obj.avatar}" style="width: 74px; height: 74px; border: 3px solid var(--nes-white); box-shadow: 4px 4px 0 #000;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p2}'">
              <h3 style="font-family: var(--font-title); font-size: 20px; color: #fff; margin-top: 6px;">${p2}</h3>
              <p style="color: var(--nes-gold); font-family: var(--font-mono); font-weight: 800;">${p2Obj.active_elo.toFixed(1)} Elo</p>
            </div>
          </div>

          <div class="block-header">Очные Протоколы Матчей (${duels.length})</div>
          ${duelsHtml || '<p style="color: #94a3b8; text-align: center; padding: 14px;">Официальных очных матчей в базе не зафиксировано.</p>'}
        </div>
      `;
    }
  </script>
</body>
</html>
"""

full_html = html_template.replace("__DATA_PLACEHOLDER__", json_str)

output_path = "c:\\Users\\Aeros\\Desktop\\Мастер-таблица\\index.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"Clean Nekketsu Master Portal generated successfully at: {output_path}")
print(f"File size: {round(os.path.getsize(output_path)/1024, 1)} KB")
