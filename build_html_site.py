import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from collections import defaultdict
import build_final_analytics

print("Generating Authentic Nekketsu Soccer League (Goal 3) Portal...")

# 1. Load data
with open("nekketsu_master_table.json", "r", encoding="utf-8") as f:
    master_db = json.load(f)

with open("player_avatars.json", "r", encoding="utf-8") as f:
    avatars = json.load(f)

all_matches = build_final_analytics.all_matches

# 2. Enrich player statistics
player_matches = defaultdict(list)
player_stats_addon = defaultdict(lambda: {
    "reg_w": 0, "ot_w": 0, "pk_w": 0,
    "reg_l": 0, "ot_l": 0, "pk_l": 0,
    "draws": 0
})

for m in all_matches:
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
    "Transistor": "https://api.dicebear.com/7.x/bottts/svg?seed=Transistor&backgroundColor=1e293b",
    "mafuta": "https://api.dicebear.com/7.x/bottts/svg?seed=Mafuta&backgroundColor=b45309",
    "WiSe": "https://api.dicebear.com/7.x/bottts/svg?seed=WiSe&backgroundColor=047857",
    "Wenderfit": "https://api.dicebear.com/7.x/bottts/svg?seed=Wenderfit&backgroundColor=4338ca",
    "high": "https://api.dicebear.com/7.x/bottts/svg?seed=High&backgroundColor=6d28d9",
    "3aBuCTb": "https://api.dicebear.com/7.x/bottts/svg?seed=Zavist&backgroundColor=be123c",
    "Centurion": "https://api.dicebear.com/7.x/bottts/svg?seed=Centurion&backgroundColor=1d4ed8",
    "Flash": "https://api.dicebear.com/7.x/bottts/svg?seed=Flash&backgroundColor=eab308",
    "LiptOn": "https://api.dicebear.com/7.x/bottts/svg?seed=LiptOn&backgroundColor=0284c7",
    "Kipriot": "https://api.dicebear.com/7.x/bottts/svg?seed=Kipriot&backgroundColor=0d9488",
    "E_not": "https://api.dicebear.com/7.x/bottts/svg?seed=Enot&backgroundColor=475569",
    "RVD (МГБ)": "https://api.dicebear.com/7.x/bottts/svg?seed=RVD&backgroundColor=991b1b",
}

# Attach rich stats
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

    # Authentic Goal 3 attributes:
    # 1. Supershot
    if p["active_elo"] >= 1650:
        p["shot_name"] = "Банановый суперудар (Banana Shot)"
        p["shot_icon"] = "🍌⚡"
        p["position"] = "FW (Нападающий)"
    elif p["active_elo"] >= 1550:
        p["shot_name"] = "Огненный суперудар (Fire Shot)"
        p["shot_icon"] = "🔥⚽"
        p["position"] = "FW (Форвард-ударник)"
    elif p["active_elo"] >= 1420:
        p["shot_name"] = "Суперудар Торпеда (Fish/Torpedo)"
        p["shot_icon"] = "🐟💨"
        p["position"] = "MF (Полузащитник)"
    elif p["gapg"] <= 2.2:
        p["shot_name"] = "Суперблок вратаря (Mega Save)"
        p["shot_icon"] = "🧤🛡️"
        p["position"] = "GK / DF (Бетонный защитник)"
    else:
        p["shot_name"] = "Удар в падении головой (Dive Header)"
        p["shot_icon"] = "💥👟"
        p["position"] = "MF / DF (Универсал)"

    # 2. In-game Mood from Nekketsu Soccer League
    if p["status"] == "ИНАКТИВЕН":
        p["mood"] = "💤 В спячке"
        p["mood_icon"] = "💤"
    elif p["win_rate"] >= 70:
        p["mood"] = "🔥 В ударе!"
        p["mood_icon"] = "🔥"
    elif p["win_rate"] >= 50:
        p["mood"] = "😊 Отличный"
        p["mood_icon"] = "😊"
    else:
        p["mood"] = "😡 Боевой"
        p["mood_icon"] = "😡"

    # Avatar & VK info
    if name in avatars:
        p["avatar"] = avatars[name]["avatar_url"]
        p["vk_name"] = avatars[name]["vk_name"]
        p["vk_id"] = avatars[name]["vk_id"]
        p["vk_domain"] = avatars[name]["domain"]
    else:
        p["avatar"] = default_avatars.get(name, f"https://api.dicebear.com/7.x/bottts/svg?seed={name}&backgroundColor=0f291e")
        p["vk_name"] = name
        p["vk_id"] = None
        p["vk_domain"] = None

    p["match_history"] = player_matches[name]

import prepare_site_data
seasons_list = prepare_site_data.seasons_data

for s in seasons_list:
    s_name = s["name"]
    s["matches"] = [m for m in all_matches if m.get("season") == s_name]
    s["total_goals"] = sum(m["s1"] + m["s2"] for m in s["matches"])

site_payload = {
    "metadata": master_db["metadata"],
    "profiles": profiles,
    "seasons": seasons_list,
    "divisions": master_db["divisions"],
    "clutch_index": master_db["clutch_and_overtime_index"],
    "records": master_db["all_time_records"],
    "rivalries": master_db["kryptonite_rivalries"],
    "all_matches": all_matches
}

json_str = json.dumps(site_payload, ensure_ascii=False)

html_template = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>熱血サッカーリーグ &bull; KUNIO-KUN NO NEKKETSU SOCCER LEAGUE &bull; GOAL 3 MASTER PORTAL</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Russo+One&family=Rubik:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      /* Authentic Nekketsu Goal 3 NES Palette */
      --pitch-grass: #125426;
      --pitch-dark: #0a3317;
      --pitch-lines: #ffffff;
      
      --nes-hud-blue: #0044aa;
      --nes-hud-navy: #001f5c;
      --nes-gold: #ffcc00;
      --nes-red: #d91438;
      --nes-orange: #ff6600;
      --nes-cream: #fff8e7;
      --nes-black: #0c0c0c;
      
      --font-title: 'Russo One', sans-serif;
      --font-body: 'Rubik', sans-serif;
      --font-num: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--pitch-dark);
      background-image: 
        repeating-linear-gradient(0deg, #0e3b1c, #0e3b1c 60px, #124722 60px, #124722 120px);
      color: #ffffff;
      font-family: var(--font-body);
      line-height: 1.5;
      min-height: 100vh;
      overflow-x: hidden;
      border-left: 12px solid #000;
      border-right: 12px solid #000;
    }

    .container { max-width: 1400px; margin: 0 auto; padding: 0 20px; }

    /* Top Goal 3 Championship Marquee */
    .top-marquee {
      background: var(--nes-gold);
      color: #000;
      font-family: var(--font-title);
      font-size: 14px;
      padding: 6px 0;
      border-bottom: 4px solid #000;
      text-transform: uppercase;
      letter-spacing: 1px;
      overflow: hidden;
      white-space: nowrap;
    }
    .marquee-track {
      display: inline-block;
      animation: marqueeRun 32s linear infinite;
    }
    @keyframes marqueeRun {
      0% { transform: translateX(100vw); }
      100% { transform: translateX(-100%); }
    }

    /* NES Technos Title Header */
    header {
      background: linear-gradient(180deg, var(--nes-hud-blue), var(--nes-hud-navy));
      border-bottom: 5px solid #000;
      box-shadow: 0 8px 0 rgba(0,0,0,0.5);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .header-inner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 90px;
    }

    .nekketsu-logo {
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
    }
    .logo-ball {
      width: 52px;
      height: 52px;
      background: #ffffff;
      border: 4px solid #000;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 26px;
      box-shadow: 4px 4px 0 #000;
      transform: rotate(-10deg);
    }
    .logo-titles h1 {
      font-family: var(--font-title);
      font-size: 26px;
      color: #ffffff;
      text-shadow: 3px 3px 0 #000, -2px -2px 0 var(--nes-red);
      letter-spacing: 1px;
      line-height: 1.1;
    }
    .logo-titles p {
      font-family: var(--font-title);
      font-size: 13px;
      color: var(--nes-gold);
      letter-spacing: 2px;
      text-shadow: 2px 2px 0 #000;
    }

    /* NES Navigation Menu */
    nav { display: flex; gap: 10px; }
    .nav-tab-btn {
      font-family: var(--font-title);
      font-size: 14px;
      background: #000000;
      color: #ffffff;
      border: 3px solid #ffffff;
      padding: 10px 18px;
      cursor: pointer;
      box-shadow: 4px 4px 0 #000;
      transition: all 0.1s;
      text-transform: uppercase;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .nav-tab-btn:hover {
      background: var(--nes-red);
      color: #ffffff;
      transform: translate(-2px, -2px);
      box-shadow: 6px 6px 0 #000;
    }
    .nav-tab-btn.active {
      background: var(--nes-gold);
      color: #000000;
      border-color: #000000;
      box-shadow: 4px 4px 0 #000;
      transform: translate(2px, 2px);
    }

    /* NES Stadium Scoreboard */
    .stadium-hud {
      background: #000000;
      border: 4px solid #ffffff;
      box-shadow: 6px 6px 0 #000;
      padding: 16px 24px;
      margin: 28px 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      border-radius: 4px;
    }
    .hud-box {
      border-left: 4px solid var(--nes-gold);
      padding-left: 14px;
    }
    .hud-title {
      font-family: var(--font-title);
      font-size: 12px;
      color: var(--nes-gold);
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .hud-val {
      font-family: var(--font-num);
      font-size: 34px;
      font-weight: 900;
      color: #ffffff;
      line-height: 1.1;
      margin: 4px 0;
    }
    .hud-desc {
      font-size: 13px;
      color: #94a3b8;
      font-weight: 600;
    }

    /* Tab content */
    .tab-view { display: none; margin-bottom: 80px; }
    .tab-view.active { display: block; animation: nesAppear 0.15s ease-out; }
    @keyframes nesAppear {
      from { opacity: 0; transform: scale(0.99); }
      to { opacity: 1; transform: scale(1); }
    }

    /* Controls Bar */
    .menu-bar {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      margin-bottom: 20px;
    }
    .division-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
    .div-btn {
      font-family: var(--font-title);
      font-size: 12px;
      background: #000000;
      color: #ffffff;
      border: 3px solid #ffffff;
      padding: 8px 14px;
      cursor: pointer;
      box-shadow: 3px 3px 0 #000;
      text-transform: uppercase;
    }
    .div-btn:hover { background: #1e3a8a; }
    .div-btn.active {
      background: var(--nes-gold);
      color: #000000;
      border-color: #000000;
    }

    .nes-search-box {
      background: #000000;
      border: 3px solid #ffffff;
      box-shadow: 4px 4px 0 #000;
      display: flex;
      align-items: center;
      padding: 2px 10px;
      flex: 1;
      max-width: 380px;
    }
    .nes-search-box input {
      background: transparent;
      border: none;
      color: #ffffff;
      font-family: var(--font-body);
      font-size: 15px;
      font-weight: 600;
      padding: 8px 6px;
      width: 100%;
      outline: none;
    }
    .nes-search-box input::placeholder { color: #64748b; }

    /* The Goal 3 Tournament Master Table */
    .nes-table-panel {
      background: #000000;
      border: 4px solid #ffffff;
      box-shadow: 8px 8px 0 #000;
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 14px;
    }
    thead th {
      background: var(--nes-hud-blue);
      color: var(--nes-gold);
      font-family: var(--font-title);
      font-size: 12px;
      letter-spacing: 0.5px;
      padding: 16px 12px;
      border-bottom: 3px solid #ffffff;
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
    }
    thead th:hover { background: #1d4ed8; color: #ffffff; }
    tbody td {
      padding: 12px 14px;
      border-bottom: 1px solid #1e293b;
      white-space: nowrap;
      font-weight: 600;
    }
    tbody tr:nth-child(even) td { background: #080d1a; }
    tbody tr:hover td { background: #132448; }

    /* Player cell */
    .player-row-cell {
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
    }
    .player-row-cell:hover .p-title { color: var(--nes-gold); text-decoration: underline; }
    .nes-portrait-box {
      width: 44px;
      height: 44px;
      background: #000;
      border: 2px solid #ffffff;
      box-shadow: 2px 2px 0 #000;
      flex-shrink: 0;
      position: relative;
      overflow: hidden;
    }
    .nes-portrait-box img { width: 100%; height: 100%; object-fit: cover; }
    .p-title { font-size: 16px; font-weight: 800; color: #ffffff; }
    .p-subinfo { font-size: 12px; color: var(--nes-gold); font-weight: 600; }

    /* Badges */
    .nes-badge {
      display: inline-block;
      font-family: var(--font-title);
      font-size: 10px;
      padding: 4px 8px;
      border: 2px solid #000;
      box-shadow: 2px 2px 0 #000;
      text-transform: uppercase;
    }
    .badge-premier { background: var(--nes-gold); color: #000; }
    .badge-middle { background: #38bdf8; color: #000; }
    .badge-yard { background: #4ade80; color: #000; }

    /* Character Roster Grid (Goal 3 Style) */
    .roster-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
      gap: 20px;
    }
    .roster-card {
      background: #000000;
      border: 4px solid #ffffff;
      box-shadow: 6px 6px 0 #000;
      padding: 18px;
      cursor: pointer;
      position: relative;
      transition: all 0.15s;
    }
    .roster-card:hover {
      border-color: var(--nes-gold);
      transform: translate(-3px, -3px);
      box-shadow: 10px 10px 0 #000;
    }
    .roster-card-header {
      display: flex;
      align-items: center;
      gap: 14px;
      border-bottom: 3px solid #1e293b;
      padding-bottom: 12px;
      margin-bottom: 12px;
    }
    .roster-card-header .nes-portrait-box {
      width: 58px;
      height: 58px;
      border: 3px solid var(--nes-gold);
    }
    .roster-hero-name {
      font-family: var(--font-title);
      font-size: 20px;
      color: #ffffff;
      line-height: 1.1;
    }
    .roster-position {
      font-size: 12px;
      font-weight: 700;
      color: var(--nes-gold);
      margin-top: 2px;
    }

    .roster-meters {
      background: #0a1122;
      border: 2px solid #1e293b;
      padding: 12px;
      margin-bottom: 12px;
    }
    .meter-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 6px;
    }
    .meter-item:last-child { margin-bottom: 0; }
    .meter-bar {
      width: 130px;
      height: 12px;
      background: #000;
      border: 2px solid #334155;
    }
    .meter-fill {
      height: 100%;
      background: var(--nes-gold);
    }

    .roster-supershot-line {
      font-size: 13px;
      font-weight: 800;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 6px;
      background: var(--nes-hud-navy);
      padding: 6px 10px;
      border: 2px solid #1e40af;
      margin-bottom: 12px;
    }
    .roster-card-footer {
      display: flex;
      justify-content: space-between;
      font-family: var(--font-num);
      font-size: 13px;
      font-weight: 800;
      color: #94a3b8;
    }

    /* Modal Tactical Team Sheet */
    .tactical-modal-overlay {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.88);
      z-index: 1000;
      overflow-y: auto;
      padding: 30px 16px;
    }
    .tactical-modal-overlay.active { display: flex; justify-content: center; align-items: flex-start; }
    .tactical-sheet {
      background: #000000;
      border: 5px solid #ffffff;
      box-shadow: 12px 12px 0 #000;
      width: 100%;
      max-width: 960px;
      position: relative;
    }
    .sheet-close-btn {
      position: absolute;
      top: 14px; right: 14px;
      font-family: var(--font-title);
      font-size: 14px;
      background: var(--nes-red);
      color: #ffffff;
      border: 3px solid #ffffff;
      padding: 6px 14px;
      cursor: pointer;
      box-shadow: 3px 3px 0 #000;
    }
    .sheet-close-btn:hover { background: #000; color: var(--nes-red); }

    .sheet-hero {
      background: linear-gradient(135deg, var(--nes-hud-blue), var(--nes-hud-navy));
      border-bottom: 4px solid #ffffff;
      padding: 28px 32px;
      display: flex;
      gap: 22px;
      align-items: center;
    }
    .sheet-portrait {
      width: 96px;
      height: 96px;
      border: 4px solid var(--nes-gold);
      box-shadow: 4px 4px 0 #000;
      object-fit: cover;
      background: #000;
    }
    .sheet-title h2 {
      font-family: var(--font-title);
      font-size: 28px;
      color: #ffffff;
      text-shadow: 3px 3px 0 #000;
    }
    .sheet-sub {
      font-size: 15px;
      font-weight: 700;
      color: var(--nes-gold);
      margin: 4px 0 10px;
    }
    .vk-tactical-link {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-family: var(--font-title);
      font-size: 11px;
      background: #0077ff;
      color: #ffffff;
      text-decoration: none;
      padding: 6px 14px;
      border: 2px solid #ffffff;
      box-shadow: 3px 3px 0 #000;
    }
    .vk-tactical-link:hover { background: #0052b3; }

    .sheet-body { padding: 30px 32px; }

    .sheet-stat-boxes {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 12px;
      margin-bottom: 26px;
    }
    .stat-tile {
      background: #0b1426;
      border: 2px solid #1e3a8a;
      box-shadow: 3px 3px 0 #000;
      padding: 12px;
      text-align: center;
    }
    .stat-tile-label { font-family: var(--font-title); font-size: 10px; color: #94a3b8; text-transform: uppercase; }
    .stat-tile-val { font-family: var(--font-num); font-size: 26px; font-weight: 900; color: #ffffff; margin-top: 4px; }

    .section-banner-title {
      font-family: var(--font-title);
      font-size: 15px;
      color: var(--nes-gold);
      background: #000;
      padding: 6px 14px;
      border: 2px solid #ffffff;
      display: inline-block;
      box-shadow: 3px 3px 0 #000;
      margin: 24px 0 14px;
      text-transform: uppercase;
    }

    /* Match rows */
    .goal3-match-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #091222;
      border: 2px solid #1e293b;
      padding: 12px 18px;
      margin-bottom: 8px;
      font-weight: 700;
      font-size: 14px;
      box-shadow: 2px 2px 0 #000;
    }
    .goal3-score-display {
      font-family: var(--font-num);
      font-size: 20px;
      font-weight: 900;
      color: var(--nes-gold);
      background: #000000;
      border: 2px solid #ffffff;
      padding: 3px 14px;
      box-shadow: 2px 2px 0 #000;
      letter-spacing: 2px;
    }

    /* Season Stages */
    .seasons-stages-bar {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 12px;
      margin-bottom: 22px;
    }
    .stage-button {
      font-family: var(--font-title);
      font-size: 12px;
      background: #000;
      color: #ffffff;
      border: 3px solid #ffffff;
      padding: 12px 18px;
      cursor: pointer;
      box-shadow: 4px 4px 0 #000;
      white-space: nowrap;
      text-transform: uppercase;
    }
    .stage-button:hover { background: #1e3a8a; }
    .stage-button.active {
      background: var(--nes-gold);
      color: #000;
      border-color: #000;
    }

    .season-panel-box {
      background: #000000;
      border: 4px solid #ffffff;
      box-shadow: 8px 8px 0 #000;
      padding: 28px;
      margin-bottom: 30px;
    }
    .season-podium-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin: 22px 0;
    }
    .podium-box-nes {
      background: #081020;
      border: 3px solid #1e3a8a;
      box-shadow: 4px 4px 0 #000;
      padding: 16px;
      text-align: center;
    }
    .podium-box-nes.gold { border-color: var(--nes-gold); }
    .podium-rank { font-family: var(--font-title); font-size: 12px; color: var(--nes-gold); margin-bottom: 6px; }
    .podium-name { font-size: 18px; font-weight: 900; color: #ffffff; cursor: pointer; }
    .podium-name:hover { color: var(--nes-gold); text-decoration: underline; }

    .story-chalkboard {
      background: #07120a;
      border: 3px solid #15803d;
      padding: 18px 22px;
      color: #f0fdf4;
      font-size: 15px;
      line-height: 1.7;
      margin-bottom: 22px;
      box-shadow: 4px 4px 0 #000;
    }

    /* Footer */
    footer {
      background: #000000;
      border-top: 5px solid #ffffff;
      padding: 40px 0;
      text-align: center;
      font-family: var(--font-title);
      font-size: 12px;
      color: #94a3b8;
      line-height: 1.8;
    }
    footer a { color: var(--nes-gold); text-decoration: none; }
    footer a:hover { text-decoration: underline; }

    @media (max-width: 768px) {
      .header-inner { flex-direction: column; height: auto; padding: 14px 0; gap: 12px; }
      nav { justify-content: center; }
      .sheet-hero { flex-direction: column; text-align: center; }
      .sheet-stat-boxes { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>

  <!-- Top Marquee -->
  <div class="top-marquee">
    <div class="marquee-track">
      ⚽ NEKKETSU SOCCER LEAGUE &bull; ЧЕМПИОНАТ СНГ ПО GOAL 3 &bull; 414 ОФИЦИАЛЬНЫХ МАТЧЕЙ &bull; ТОП-ДОМИНАТОР: ECTOPOWER (4 ТИТУЛА) &bull; ЖЕЛЕЗНАЯ СТЕНА: KUNIO (1.76 GAPG) &bull; МАТЧ ВЕКА: RIC25 8:9 MEMORI (17 ГОЛОВ) &bull; ВЕТЕРАН: AERIS (32 ИГРЫ, 1405.9 ELO) &bull; КЛАТЧ-КОРОЛЬ: PACNYTHUK ⚽
    </div>
  </div>

  <!-- Header -->
  <header>
    <div class="container header-inner">
      <a href="#/leaderboard" class="nekketsu-logo">
        <div class="logo-ball">⚽</div>
        <div class="logo-titles">
          <h1>NEKKETSU SOCCER LEAGUE</h1>
          <p>熱血サッカーリーグ &bull; ТУРНИРНЫЙ ПОРТАЛ GOAL 3</p>
        </div>
      </a>

      <nav>
        <button class="nav-tab-btn active" onclick="switchTab('leaderboard')">🏆 Рейтинг</button>
        <button class="nav-tab-btn" onclick="switchTab('roster')">👤 Составы (Игроки)</button>
        <button class="nav-tab-btn" onclick="switchTab('seasons')">📅 Сезоны 1–9</button>
        <button class="nav-tab-btn" onclick="switchTab('clutch')">⚡ Клатч и Рекорды</button>
        <button class="nav-tab-btn" onclick="switchTab('h2h')">⚔️ Очные Дуэли</button>
      </nav>
    </div>
  </header>

  <main class="container">

    <!-- Stadium Scoreboard HUD -->
    <div class="stadium-hud" id="hudContainer"></div>

    <!-- TAB 1: LEADERBOARD -->
    <section id="tab-leaderboard" class="tab-view active">
      <div class="menu-bar">
        <div class="division-buttons">
          <button class="div-btn active" onclick="filterDivision('all', this)">[Все Дивизионы]</button>
          <button class="div-btn" onclick="filterDivision('Высшая', this)">[Высшая Лига]</button>
          <button class="div-btn" onclick="filterDivision('Средняя', this)">[Средняя Лига]</button>
          <button class="div-btn" onclick="filterDivision('Дворовая', this)">[Дворовая Лига]</button>
        </div>
        <div class="nes-search-box">
          <span style="font-size: 16px; margin-right: 6px;">🔍</span>
          <input type="text" id="tableSearch" placeholder="Поиск по никнейму..." oninput="renderTable()">
        </div>
      </div>

      <div class="nes-table-panel">
        <table>
          <thead>
            <tr>
              <th onclick="sortTable('rank')">#</th>
              <th onclick="sortTable('player')">Игрок (Профиль)</th>
              <th onclick="sortTable('league')">Дивизион</th>
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

    <!-- TAB 2: ROSTER (CARDS) -->
    <section id="tab-roster" class="tab-view">
      <div class="menu-bar">
        <div class="nes-search-box" style="max-width: 100%;">
          <span style="font-size: 16px; margin-right: 6px;">🔍</span>
          <input type="text" id="rosterSearch" placeholder="Поиск игрока по нику, позиции или суперудару..." oninput="renderRosterCards()">
        </div>
      </div>
      <div class="roster-grid" id="rosterGrid"></div>
    </section>

    <!-- TAB 3: SEASONS -->
    <section id="tab-seasons" class="tab-view">
      <div class="seasons-stages-bar" id="seasonsBar"></div>
      <div id="seasonContentArea"></div>
    </section>

    <!-- TAB 4: CLUTCH & RECORDS -->
    <section id="tab-clutch" class="tab-view">
      <div class="section-banner-title">⚡ Рейтинг Клатч-Мастеров (Овертаймы и Серии Буллитов)</div>
      <div class="nes-table-panel" style="margin-bottom: 28px;">
        <table>
          <thead>
            <tr>
              <th>Игрок</th>
              <th>Игр в ОТ/Пен</th>
              <th>Побед в ОТ</th>
              <th>Побед по Пен</th>
              <th>Всего Клатч-W</th>
              <th>Клатч Winrate</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody id="clutchTableBody"></tbody>
        </table>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 24px;">
        <div class="nes-table-panel" style="padding: 22px;">
          <div class="section-banner-title" style="margin-top: 0; color: #38bdf8;">🔥 Топ-10 Триллеров Лиги</div>
          <div id="thrillersList"></div>
        </div>
        <div class="nes-table-panel" style="padding: 22px;">
          <div class="section-banner-title" style="margin-top: 0; color: var(--nes-red);">💥 Самые Крупные Разгромы</div>
          <div id="blowoutsList"></div>
        </div>
      </div>
    </section>

    <!-- TAB 5: H2H -->
    <section id="tab-h2h" class="tab-view">
      <div class="nes-table-panel" style="padding: 26px; margin-bottom: 24px;">
        <div class="section-banner-title" style="margin-top: 0;">⚔️ Калькулятор Личных Встреч (Очные Дуэли)</div>
        <p style="color: #94a3b8; font-size: 14px; margin-bottom: 18px; font-weight: 600;">Выберите двух участников, чтобы поднять протоколы всех их официальных матчей.</p>
        
        <div style="display: flex; gap: 14px; flex-wrap: wrap; align-items: center;">
          <select id="h2hPlayer1" class="div-btn" style="flex: 1; max-width: 280px; font-size: 14px; padding: 10px;" onchange="calculateH2H()"></select>
          <span style="font-family: var(--font-title); font-size: 20px; color: var(--nes-gold);">VS</span>
          <select id="h2hPlayer2" class="div-btn" style="flex: 1; max-width: 280px; font-size: 14px; padding: 10px;" onchange="calculateH2H()"></select>
        </div>
      </div>

      <div id="h2hResultContainer"></div>
    </section>

  </main>

  <!-- Player Profile Modal (Tactical Sheet) -->
  <div class="tactical-modal-overlay" id="tacticalModal" onclick="closeModal(event)">
    <div class="tactical-sheet" onclick="event.stopPropagation()">
      <button class="sheet-close-btn" onclick="closeModalDirect()">ЗАКРЫТЬ [X]</button>
      <div class="sheet-hero" id="sheetHero"></div>
      <div class="sheet-body" id="sheetBody"></div>
    </div>
  </div>

  <!-- Footer -->
  <footer>
    <div class="container">
      <p>⚽ NEKKETSU SOCCER LEAGUE &bull; 熱血サッカーリーグ &bull; EST. 2015</p>
      <p>ОФИЦИАЛЬНОЕ СООБЩЕСТВО: <a href="https://vk.ru/nekketsu" target="_blank">VK.RU/NEKKETSU</a> &bull; АНАЛИТИКА И СТАТИСТИКА ANTIGRAVITY</p>
      <p style="color: var(--nes-gold); margin-top: 4px;">ПЛАТФОРМА: FAMICOM / NES &bull; MEDNAFEN NETPLAY TOURNAMENTS</p>
    </div>
  </footer>

  <!-- Embedded JSON Dataset -->
  <script>
    const DATA = __DATA_PLACEHOLDER__;
  </script>

  <!-- Application Logic -->
  <script>
    let currentDivisionFilter = 'all';
    let currentSortColumn = 'active_elo';
    let sortAsc = false;
    let selectedSeasonId = '9';

    window.addEventListener('DOMContentLoaded', () => {
      renderHUD();
      renderTable();
      renderRosterCards();
      renderSeasonsBar();
      renderSeasonContent(selectedSeasonId);
      renderClutchSection();
      initH2HSelects();

      window.addEventListener('hashchange', handleRouting);
      handleRouting();
    });

    function handleRouting() {
      const hash = window.location.hash || '#/leaderboard';
      if (hash.startsWith('#/player/')) {
        const pName = decodeURIComponent(hash.replace('#/player/', ''));
        openPlayerModal(pName);
      } else if (hash.startsWith('#/season/')) {
        const sId = hash.replace('#/season/', '');
        switchTab('seasons');
        selectSeason(sId);
      } else if (hash === '#/roster') {
        switchTab('roster');
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
      document.querySelectorAll('.tab-view').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-tab-btn').forEach(el => el.classList.remove('active'));

      const activeSection = document.getElementById(`tab-${tabId}`);
      if (activeSection) activeSection.classList.add('active');

      const activeBtn = Array.from(document.querySelectorAll('.nav-tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
      if (activeBtn) activeBtn.classList.add('active');
    }

    function renderHUD() {
      const m = DATA.metadata;
      const hud = document.getElementById('hudContainer');
      hud.innerHTML = `
        <div class="hud-box">
          <div class="hud-title">Всего матчей в базе</div>
          <div class="hud-val">${m.total_matches_analyzed}</div>
          <div class="hud-desc">Сезоны 1–9 (2015–2025 гг.)</div>
        </div>
        <div class="hud-box">
          <div class="hud-title">Забито мячей</div>
          <div class="hud-val" style="color: var(--nes-gold);">${m.total_goals_recorded}</div>
          <div class="hud-desc">В среднем ${m.avg_goals_per_match} за игру</div>
        </div>
        <div class="hud-box">
          <div class="hud-title">Овертаймы и Буллиты</div>
          <div class="hud-val" style="color: #38bdf8;">${m.total_ot_pk_matches}</div>
          <div class="hud-desc">18.4% драматичных концовок</div>
        </div>
        <div class="hud-box">
          <div class="hud-title">Участников турниров</div>
          <div class="hud-val" style="color: #4ade80;">${m.total_players_tracked}</div>
          <div class="hud-desc">Аватары из ВК привязаны</div>
        </div>
      `;
    }

    function filterDivision(div, btn) {
      currentDivisionFilter = div;
      document.querySelectorAll('.div-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTable();
    }

    function sortTable(col) {
      if (currentSortColumn === col) {
        sortAsc = !sortAsc;
      } else {
        currentSortColumn = col;
        sortAsc = false;
      }
      renderTable();
    }

    function renderTable() {
      const query = (document.getElementById('tableSearch')?.value || '').toLowerCase();
      let list = [...DATA.profiles];

      if (currentDivisionFilter !== 'all') {
        list = list.filter(p => p.league === currentDivisionFilter);
      }
      if (query) {
        list = list.filter(p => p.player.toLowerCase().includes(query) || (p.vk_name && p.vk_name.toLowerCase().includes(query)));
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
        const gdColor = p.goal_diff > 0 ? '#4ade80' : (p.goal_diff < 0 ? '#f87171' : '#ffffff');
        const badgeClass = p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard');

        return `
          <tr>
            <td style="font-family: var(--font-num); font-weight: 800; color: var(--nes-gold);">${idx + 1}</td>
            <td>
              <div class="player-row-cell" onclick="openPlayerModal('${p.player}')">
                <div class="nes-portrait-box">
                  <img src="${p.avatar}" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
                </div>
                <div>
                  <div class="p-title">${p.player} <span style="font-size: 13px;">${p.mood_icon}</span></div>
                  <div class="p-subinfo">${p.vk_name !== p.player ? p.vk_name : p.position}</div>
                </div>
              </div>
            </td>
            <td><span class="nes-badge ${badgeClass}">${p.league}</span></td>
            <td>
              <div style="font-family: var(--font-num); font-weight: 900; font-size: 16px; color: #ffffff;">${p.active_elo.toFixed(1)}</div>
              ${p.decay_penalty > 0 ? `<div style="font-size: 11px; color: #f87171; font-weight: 800;">-${p.decay_penalty} decay</div>` : ''}
            </td>
            <td><span style="font-family: var(--font-num); font-weight: 800; color: var(--nes-gold);">${p.peak_elo.toFixed(1)}</span></td>
            <td style="font-family: var(--font-num); font-weight: 800;">${p.matches}</td>
            <td style="font-family: var(--font-num);"><strong style="color: #4ade80;">${p.wins}</strong> - <strong style="color: #f87171;">${p.losses}</strong></td>
            <td><strong style="font-family: var(--font-num); color: ${p.win_rate >= 60 ? '#4ade80' : (p.win_rate >= 45 ? '#ffffff' : '#f87171')};">${p.win_rate}%</strong></td>
            <td style="font-family: var(--font-num); font-size: 13px;">
              <span>${p.reg_wins}</span> / <span style="color: var(--nes-gold); font-weight: 800;">${p.ot_wins}</span> / <span style="color: #c084fc; font-weight: 800;">${p.pk_wins}</span>
            </td>
            <td style="font-family: var(--font-num);"><strong style="color: ${gdColor};">${gdStr}</strong> <span style="color: #64748b; font-size: 12px;">(${p.goals_for}:${p.goals_against})</span></td>
            <td style="font-family: var(--font-num);">${p.gapg.toFixed(2)}</td>
            <td><strong style="font-family: var(--font-num); color: var(--nes-gold);">${p.dominator_score.toFixed(1)}</strong></td>
          </tr>
        `;
      }).join('');
    }

    // Roster Cards Grid
    function renderRosterCards() {
      const q = (document.getElementById('rosterSearch')?.value || '').toLowerCase();
      let list = DATA.profiles.filter(p => 
        p.player.toLowerCase().includes(q) || 
        p.league.toLowerCase().includes(q) || 
        p.position.toLowerCase().includes(q) || 
        (p.shot_name && p.shot_name.toLowerCase().includes(q))
      );

      const grid = document.getElementById('rosterGrid');
      grid.innerHTML = list.map(p => {
        const badgeClass = p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard');
        const gdStr = p.goal_diff > 0 ? `+${p.goal_diff}` : `${p.goal_diff}`;
        const eloWidth = Math.min(100, Math.max(15, ((p.active_elo - 1000) / 750) * 100));

        return `
          <div class="roster-card" onclick="openPlayerModal('${p.player}')">
            <div class="roster-card-header">
              <div class="nes-portrait-box">
                <img src="${p.avatar}" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
              </div>
              <div style="flex: 1;">
                <div class="roster-hero-name">${p.player} ${p.mood_icon}</div>
                <div class="roster-position">${p.position}</div>
                <div style="margin-top: 4px;">
                  <span class="nes-badge ${badgeClass}">${p.league}</span>
                  <span class="nes-badge" style="background: #1e293b; color: #fff;">${p.status}</span>
                </div>
              </div>
            </div>

            <div class="roster-supershot-line">
              <span>${p.shot_icon}</span>
              <span>${p.shot_name}</span>
            </div>

            <div class="roster-meters">
              <div class="meter-item">
                <span>Active Elo:</span>
                <div class="meter-bar"><div class="meter-fill" style="width: ${eloWidth}%;"></div></div>
                <span style="font-family: var(--font-num); color: var(--nes-gold);">${p.active_elo.toFixed(1)}</span>
              </div>
              <div class="meter-item">
                <span>Винрейт:</span>
                <div class="meter-bar"><div class="meter-fill" style="width: ${p.win_rate}%; background: #4ade80;"></div></div>
                <span style="font-family: var(--font-num); color: #4ade80;">${p.win_rate}%</span>
              </div>
            </div>

            <div class="roster-card-footer">
              <span>Матчи: <strong style="color: #fff;">${p.matches}</strong></span>
              <span>Баланс: <strong style="color: #4ade80;">${p.wins}W</strong> - <strong style="color: #f87171;">${p.losses}L</strong></span>
              <span>Разница: <strong style="color: #fff;">${gdStr}</strong></span>
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

      const hero = document.getElementById('sheetHero');
      const body = document.getElementById('sheetBody');
      const badgeClass = p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard');
      const vkLink = p.vk_domain ? `https://vk.ru/${p.vk_domain}` : (p.vk_id ? `https://vk.ru/id${p.vk_id}` : null);

      hero.innerHTML = `
        <img src="${p.avatar}" class="sheet-portrait" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
        <div class="sheet-title">
          <h2>${p.player} ${p.mood_icon}</h2>
          <div class="sheet-sub">${p.vk_name} &bull; ${p.position} &bull; Настрой: ${p.mood}</div>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <span class="nes-badge ${badgeClass}">${p.league} ЛИГА</span>
            <span class="nes-badge" style="background: #1e293b; color: #fff;">${p.status}</span>
            ${vkLink ? `<a href="${vkLink}" target="_blank" class="vk-tactical-link">Профиль ВКонтакте ↗</a>` : ''}
          </div>
        </div>
      `;

      const matchRows = (p.match_history || []).slice(0, 35).map(m => {
        const resColor = m.result === 'W' ? '#4ade80' : (m.result === 'L' ? '#f87171' : '#ffffff');
        const oppObj = DATA.profiles.find(x => x.player === m.opponent);
        const oppAvatar = oppObj ? oppObj.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.opponent}`;

        return `
          <div class="goal3-match-row">
            <div style="flex: 1; display: flex; align-items: center; gap: 10px;">
              <span style="font-family: var(--font-num); font-size: 15px; font-weight: 900; color: ${resColor}; width: 24px;">${m.result}</span>
              <span style="color: #fff;">${p.player}</span>
            </div>
            <div class="goal3-score-display">
              ${m.score_for} : ${m.score_against}
              ${m.pk ? '<span style="font-size: 11px; color: #c084fc; margin-left: 6px;">[PK]</span>' : (m.ot ? '<span style="font-size: 11px; color: var(--nes-gold); margin-left: 6px;">[OT]</span>' : '')}
            </div>
            <div style="flex: 1; display: flex; align-items: center; justify-content: flex-end; gap: 10px; cursor: pointer;" onclick="openPlayerModal('${m.opponent}')">
              <span style="color: #fff;">${m.opponent}</span>
              <img src="${oppAvatar}" style="width: 26px; height: 26px; border: 2px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.opponent}'">
            </div>
          </div>
        `;
      }).join('');

      body.innerHTML = `
        <div class="sheet-stat-boxes">
          <div class="stat-tile">
            <div class="stat-tile-label">Active Elo</div>
            <div class="stat-tile-val" style="color: var(--nes-gold);">${p.active_elo.toFixed(1)}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-label">Peak Elo</div>
            <div class="stat-tile-val">${p.peak_elo.toFixed(1)}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-label">Time-Decay</div>
            <div class="stat-tile-val" style="color: ${p.decay_penalty > 0 ? '#f87171' : '#4ade80'};">-${p.decay_penalty}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-label">Всего игр</div>
            <div class="stat-tile-val">${p.matches}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-label">Побед %</div>
            <div class="stat-tile-val" style="color: #4ade80;">${p.win_rate}%</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-label">Мячи (+/-)</div>
            <div class="stat-tile-val">${p.goals_for}:${p.goals_against}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-label">Забито/м (GPG)</div>
            <div class="stat-tile-val">${p.gpg.toFixed(2)}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-tile-label">Пропущено/м (GAPG)</div>
            <div class="stat-tile-val">${p.gapg.toFixed(2)}</div>
          </div>
        </div>

        <div class="section-banner-title">⚡ Суперудар и Тактическая Роль</div>
        <div style="background: #000; border: 3px solid #1e3a8a; padding: 16px; margin-bottom: 24px;">
          <div style="font-size: 18px; font-weight: 900; color: var(--nes-gold); margin-bottom: 6px;">
            ${p.shot_icon} ${p.shot_name}
          </div>
          <div style="color: #94a3b8; font-size: 14px;">
            Позиция на поле: <strong>${p.position}</strong> | Фирменный стиль: <strong>${p.playstyle}</strong>
          </div>
        </div>

        <div class="section-banner-title">🎯 Победы: Основное время vs Овертайм vs Буллиты</div>
        <div style="background: #000; border: 3px solid #1e3a8a; padding: 16px; margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 13px; margin-bottom: 8px;">
            <span>Основное время: <strong style="color: #38bdf8;">${p.reg_wins}W</strong></span>
            <span>Овертаймы (OT): <strong style="color: var(--nes-gold);">${p.ot_wins}W</strong></span>
            <span>Буллиты (PK): <strong style="color: #c084fc;">${p.pk_wins}W</strong></span>
            <span>Клатч WR: <strong style="color: #4ade80;">${p.clutch_win_rate}%</strong> (${p.clutch_wins}/${p.clutch_total})</span>
          </div>
          <div style="display: flex; height: 16px; border: 2px solid #334155; background: #000;">
            <div style="width: ${p.wins > 0 ? (p.reg_wins/p.wins*100) : 0}%; background: #38bdf8;"></div>
            <div style="width: ${p.wins > 0 ? (p.ot_wins/p.wins*100) : 0}%; background: var(--nes-gold);"></div>
            <div style="width: ${p.wins > 0 ? (p.pk_wins/p.wins*100) : 0}%; background: #c084fc;"></div>
          </div>
        </div>

        <div class="section-banner-title">📜 Список официальных турнирных матчей (${p.match_history ? p.match_history.length : 0})</div>
        <div style="max-height: 380px; overflow-y: auto; padding-right: 6px;">
          ${matchRows || '<p style="color: #64748b; padding: 14px;">Матчи в базе не найдены</p>'}
        </div>
      `;

      document.getElementById('tacticalModal').classList.add('active');
    }

    function closeModal(e) {
      if (e.target.id === 'tacticalModal') closeModalDirect();
    }
    function closeModalDirect() {
      document.getElementById('tacticalModal').classList.remove('active');
      window.location.hash = '#/leaderboard';
    }

    // Seasons Module
    function renderSeasonsBar() {
      const bar = document.getElementById('seasonsBar');
      bar.innerHTML = DATA.seasons.map(s => `
        <button class="stage-button ${s.id === selectedSeasonId ? 'active' : ''}" onclick="selectSeason('${s.id}')">
          STAGE ${s.id}: ${s.name} (${s.year})
        </button>
      `).join('');
    }

    function selectSeason(sId) {
      selectedSeasonId = sId;
      renderSeasonsBar();
      renderSeasonContent(sId);
    }

    function renderSeasonContent(sId) {
      const s = DATA.seasons.find(x => x.id === sId);
      if (!s) return;

      const container = document.getElementById('seasonContentArea');
      const highlightsHtml = (s.highlights || []).map(h => `<li style="margin-bottom: 8px;">${h}</li>`).join('');

      const matchesList = (s.matches || []).slice(0, 40).map(m => `
        <div class="goal3-match-row">
          <div style="flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p1}')">${m.p1}</div>
          <div class="goal3-score-display">
            ${m.s1} : ${m.s2}
            ${m.pk ? '<span style="font-size: 11px; color: #c084fc; margin-left: 6px;">[PK]</span>' : (m.ot ? '<span style="font-size: 11px; color: var(--nes-gold); margin-left: 6px;">[OT]</span>' : '')}
          </div>
          <div style="flex: 1; text-align: right; cursor: pointer;" onclick="openPlayerModal('${m.p2}')">${m.p2}</div>
        </div>
      `).join('');

      container.innerHTML = `
        <div class="season-panel-box">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
            <div>
              <span class="nes-badge" style="background: var(--nes-red); color: #fff; margin-bottom: 8px;">STAGE ${s.id} &bull; ${s.year} ГОД</span>
              <h2 style="font-family: var(--font-title); font-size: 26px; color: #ffffff; text-shadow: 2px 2px 0 #000;">${s.name} &bull; Сольный Чемпионат NST</h2>
              <p style="color: #94a3b8; font-size: 14px; font-weight: 600; margin-top: 4px;">${s.format} | Участников: <strong>${s.participants}</strong> | Ром / Эмулятор: ${s.emulator}</p>
            </div>
            <div style="text-align: right;">
              <div style="font-family: var(--font-title); font-size: 11px; color: var(--nes-gold);">МАТЧЕЙ В СЕЗОНЕ</div>
              <div style="font-family: var(--font-num); font-size: 40px; font-weight: 900; color: #ffffff; line-height: 1;">${s.matches ? s.matches.length : 0}</div>
            </div>
          </div>

          <div class="season-podium-grid">
            <div class="podium-box-nes gold">
              <div class="podium-rank">🥇 Чемпион Высшей лиги</div>
              <div class="podium-name" onclick="openPlayerModal('${s.champion}')">${s.champion}</div>
            </div>
            <div class="podium-box-nes">
              <div class="podium-rank" style="color: #cbd5e1;">🥈 Вице-чемпион</div>
              <div class="podium-name" onclick="openPlayerModal('${s.runner_up}')">${s.runner_up}</div>
            </div>
            <div class="podium-box-nes">
              <div class="podium-rank" style="color: #fb923c;">🥉 3-е место</div>
              <div class="podium-name" onclick="openPlayerModal('${s.third_place}')">${s.third_place}</div>
            </div>
            <div class="podium-box-nes" style="border-color: var(--nes-red);">
              <div class="podium-rank" style="color: var(--nes-red);">🏆 Обладатель Кубка</div>
              <div class="podium-name" onclick="openPlayerModal('${s.cup_winner}')">${s.cup_winner}</div>
            </div>
          </div>

          <div class="section-banner-title">📖 Летопись и События Сезона</div>
          <div class="story-chalkboard">${s.summary}</div>

          <div class="section-banner-title">⚡ Хайлайты и Ключевые Факты</div>
          <ul style="color: #cbd5e1; font-size: 15px; font-weight: 600; padding-left: 20px; margin-bottom: 24px; line-height: 1.8;">
            ${highlightsHtml}
          </ul>

          <div class="section-banner-title">⚽ Протоколы матчей сезона (${s.matches ? s.matches.length : 0})</div>
          <div style="max-height: 400px; overflow-y: auto; padding-right: 6px;">
            ${matchesList || '<p style="color: #64748b; padding: 14px;">Матчи сезона архивированы в Google Sheets / Oball</p>'}
          </div>
        </div>
      `;
    }

    // Clutch & Records
    function renderClutchSection() {
      const tbody = document.getElementById('clutchTableBody');
      const clutchList = [...DATA.profiles].filter(p => p.clutch_total >= 2).sort((a,b) => b.clutch_win_rate - a.clutch_win_rate || b.clutch_wins - a.clutch_wins);

      tbody.innerHTML = clutchList.map(p => `
        <tr>
          <td>
            <div class="player-row-cell" onclick="openPlayerModal('${p.player}')">
              <img src="${p.avatar}" style="width: 32px; height: 32px; border: 2px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
              <span class="p-title">${p.player}</span>
            </div>
          </td>
          <td style="font-family: var(--font-num); font-weight: 800;">${p.clutch_total}</td>
          <td style="font-family: var(--font-num); color: var(--nes-gold); font-weight: 800;">${p.ot_wins}</td>
          <td style="font-family: var(--font-num); color: #c084fc; font-weight: 800;">${p.pk_wins}</td>
          <td style="font-family: var(--font-num); color: #4ade80; font-weight: 900;">${p.clutch_wins}</td>
          <td><strong style="color: ${p.clutch_win_rate >= 60 ? '#4ade80' : '#ffffff'}; font-family: var(--font-num); font-size: 15px;">${p.clutch_win_rate}%</strong></td>
          <td><span class="nes-badge" style="background: #1e293b; color: #fff;">${p.status}</span></td>
        </tr>
      `).join('');

      // Thrillers
      const tDiv = document.getElementById('thrillersList');
      tDiv.innerHTML = (DATA.records.top_thrillers || []).slice(0, 10).map(t => `
        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #1e293b; font-size: 14px; font-weight: 700;">
          <span><strong>${t.p1}</strong> ${t.s1} : ${t.s2} <strong>${t.p2}</strong></span>
          <span style="color: #38bdf8; font-family: var(--font-num); font-weight: 800;">${t.total_goals} голов (${t.season})</span>
        </div>
      `).join('');

      // Blowouts
      const bDiv = document.getElementById('blowoutsList');
      bDiv.innerHTML = (DATA.records.top_blowouts || []).slice(0, 10).map(b => `
        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #1e293b; font-size: 14px; font-weight: 700;">
          <span><strong>${b.winner}</strong> ${b.s_win} : ${b.s_lose} <strong>${b.loser}</strong></span>
          <span style="color: var(--nes-red); font-family: var(--font-num); font-weight: 800;">+${b.diff} голов (${b.season})</span>
        </div>
      `).join('');
    }

    // H2H
    function initH2HSelects() {
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
      const res = document.getElementById('h2hResultContainer');

      if (p1 === p2) {
        res.innerHTML = '<p style="color: var(--nes-red); font-family: var(--font-title); font-size: 14px; padding: 20px;">ВЫБЕРИТЕ ДВУХ РАЗНЫХ ИГРОКОВ.</p>';
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
        <div class="goal3-match-row">
          <div style="flex: 1; display: flex; align-items: center; gap: 8px;">
            <span style="font-family: var(--font-num); font-size: 14px; font-weight: 900; color: ${m.result === 'W' ? '#4ade80' : (m.result === 'L' ? '#f87171' : '#ffffff')};">${m.result}</span>
            <span>${p1}</span>
          </div>
          <div class="goal3-score-display">
            ${m.score_for} : ${m.score_against}
            ${m.pk ? '<span style="font-size: 11px; color: #c084fc; margin-left: 6px;">[PK]</span>' : (m.ot ? '<span style="font-size: 11px; color: var(--nes-gold); margin-left: 6px;">[OT]</span>' : '')}
          </div>
          <div style="flex: 1; text-align: right;">
            <span>${p2}</span>
          </div>
        </div>
      `).join('');

      res.innerHTML = `
        <div class="nes-table-panel" style="padding: 28px;">
          <div style="display: flex; justify-content: space-around; align-items: center; margin-bottom: 24px; text-align: center;">
            <div onclick="openPlayerModal('${p1}')" style="cursor: pointer;">
              <img src="${p1Obj.avatar}" style="width: 80px; height: 80px; border: 4px solid var(--nes-gold); box-shadow: 4px 4px 0 #000;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p1}'">
              <h3 style="font-family: var(--font-title); font-size: 22px; color: #ffffff; margin-top: 6px;">${p1}</h3>
              <p style="color: var(--nes-gold); font-family: var(--font-num); font-weight: 800;">${p1Obj.active_elo.toFixed(1)} Elo</p>
            </div>

            <div style="text-align: center;">
              <div style="font-family: var(--font-num); font-size: 48px; font-weight: 900; line-height: 1;">
                <span style="color: #4ade80;">${p1Wins}</span>
                <span style="color: #64748b; font-size: 32px;"> : </span>
                <span style="color: #f87171;">${p2Wins}</span>
              </div>
              ${draws > 0 ? `<div style="font-family: var(--font-title); font-size: 12px; color: var(--nes-gold); margin-top: 4px;">${draws} НИЧЬИХ</div>` : ''}
              <div style="font-family: var(--font-num); font-size: 14px; color: #94a3b8; margin-top: 6px; font-weight: 700;">Мячи: ${p1Goals} - ${p2Goals}</div>
            </div>

            <div onclick="openPlayerModal('${p2}')" style="cursor: pointer;">
              <img src="${p2Obj.avatar}" style="width: 80px; height: 80px; border: 4px solid var(--nes-red); box-shadow: 4px 4px 0 #000;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p2}'">
              <h3 style="font-family: var(--font-title); font-size: 22px; color: #ffffff; margin-top: 6px;">${p2}</h3>
              <p style="color: var(--nes-red); font-family: var(--font-num); font-weight: 800;">${p2Obj.active_elo.toFixed(1)} Elo</p>
            </div>
          </div>

          <div class="section-banner-title">Очные Матчи в Истории (${duels.length})</div>
          ${duelsHtml || '<p style="color: #64748b; text-align: center; padding: 20px; font-weight: 700;">Официальных очных матчей в базе не зафиксировано.</p>'}
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

print(f"Goal 3 Nekketsu Master Portal generated successfully at: {output_path}")
