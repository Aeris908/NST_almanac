import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from collections import defaultdict
import build_final_analytics

print("Building Pixel-Perfect Goal 3 (Version T358) Portal...")

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

    # Authentic Goal 3 parameters
    if p["active_elo"] >= 1650:
        p["stat_hp"] = 60; p["stat_sp"] = 18; p["rank_letter"] = "S"; p["t358_icon"] = "★"
        p["t358_shot"] = "Банан"
    elif p["active_elo"] >= 1550:
        p["stat_hp"] = 55; p["stat_sp"] = 16; p["rank_letter"] = "A"; p["t358_icon"] = "★"
        p["t358_shot"] = "Огонь"
    elif p["active_elo"] >= 1420:
        p["stat_hp"] = 50; p["stat_sp"] = 14; p["rank_letter"] = "B"; p["t358_icon"] = "💚"
        p["t358_shot"] = "Рыбка"
    elif p["status"] == "ИНАКТИВЕН":
        p["stat_hp"] = 40; p["stat_sp"] = 10; p["rank_letter"] = "D"; p["t358_icon"] = "💤"
        p["t358_shot"] = "Спячка"
    else:
        p["stat_hp"] = 45; p["stat_sp"] = 12; p["rank_letter"] = "C"; p["t358_icon"] = "💢"
        p["t358_shot"] = "Подкат"

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
  <title>NEKKETSU SOCCER LEAGUE &bull; ВЕРСИЯ T358</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
  <style>
    :root {
      --nes-bg: #183c5c;
      --nes-white: #fcfcfc;
      --nes-black: #000000;
      --nes-cyan: #2090d0;
      --nes-teal: #008088;
      --nes-field-green: #4cdc48;
      --nes-field-dark: #00a800;
      --nes-red: #d82800;
      --nes-yellow: #fce440;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--nes-bg);
      color: var(--nes-white);
      font-family: 'Press Start 2P', monospace;
      font-size: 11px;
      line-height: 1.8;
      letter-spacing: 0.5px;
      min-height: 100vh;
      image-rendering: pixelated;
      -webkit-font-smoothing: none;
      -moz-osx-font-smoothing: grayscale;
      padding-bottom: 60px;
    }

    .container { max-width: 1280px; margin: 0 auto; padding: 0 16px; }

    /* Top T358 Title Bar */
    .title-banner {
      border: 3px solid var(--nes-white);
      background: var(--nes-bg);
      padding: 12px 16px;
      margin: 20px 0 14px;
      text-align: center;
    }
    .title-banner h1 {
      font-size: 15px;
      color: var(--nes-white);
      margin-bottom: 4px;
    }
    .version-tag {
      color: var(--nes-cyan);
      font-size: 11px;
    }

    /* Navigation Bar */
    nav {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 22px;
      justify-content: center;
    }
    .menu-item-btn {
      background: var(--nes-bg);
      color: var(--nes-white);
      border: 3px solid var(--nes-white);
      font-family: 'Press Start 2P', monospace;
      font-size: 10px;
      padding: 10px 14px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      text-transform: uppercase;
    }
    .menu-item-btn:hover {
      color: var(--nes-cyan);
      border-color: var(--nes-cyan);
    }
    .menu-item-btn.active {
      background: var(--nes-cyan);
      color: var(--nes-black);
      border-color: var(--nes-white);
      font-weight: 900;
    }

    /* HUD Summary */
    .section-title {
      font-size: 13px;
      color: var(--nes-white);
      margin: 20px 0 10px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .hud-box {
      border: 3px solid var(--nes-white);
      background: var(--nes-bg);
      padding: 14px 18px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-around;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 11px;
    }
    .hud-item span { color: var(--nes-cyan); }

    /* Division Selector */
    .division-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 14px;
    }
    .div-tab-btn {
      background: var(--nes-bg);
      color: var(--nes-white);
      border: 2px solid var(--nes-white);
      font-family: 'Press Start 2P', monospace;
      font-size: 10px;
      padding: 6px 12px;
      cursor: pointer;
    }
    .div-tab-btn.active {
      color: var(--nes-cyan);
      border-color: var(--nes-cyan);
    }
    .search-field {
      background: var(--nes-bg);
      border: 2px solid var(--nes-white);
      color: var(--nes-white);
      font-family: 'Press Start 2P', monospace;
      font-size: 10px;
      padding: 6px 10px;
      outline: none;
      flex: 1;
      max-width: 320px;
    }

    /* Main Table */
    .table-container {
      border: 3px solid var(--nes-white);
      background: var(--nes-bg);
      overflow-x: auto;
      margin-bottom: 30px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 10px;
    }
    th {
      background: var(--nes-bg);
      color: var(--nes-cyan);
      padding: 12px 10px;
      border-bottom: 2px solid var(--nes-white);
      white-space: nowrap;
      cursor: pointer;
    }
    th:hover { color: var(--nes-white); text-decoration: underline; }
    td {
      padding: 10px 10px;
      border-bottom: 1px solid rgba(252, 252, 252, 0.2);
      white-space: nowrap;
    }
    tr:hover td {
      background: rgba(32, 144, 208, 0.2);
    }

    /* Player cell */
    .p-cell {
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
    }
    .p-cell:hover .p-name-txt { color: var(--nes-cyan); }
    .nes-avatar {
      width: 32px;
      height: 32px;
      border: 2px solid var(--nes-white);
      box-shadow: 2px 2px 0 var(--nes-black);
      object-fit: cover;
      background: var(--nes-black);
    }

    /* Screen Views */
    .screen-view { display: none; }
    .screen-view.active { display: block; }

    /* Character Selection Screen (Roster) */
    .roster-field-box {
      border: 3px solid var(--nes-white);
      background: var(--nes-bg);
      padding: 20px;
      margin-bottom: 30px;
    }
    .roster-columns {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }
    .player-line-card {
      border: 2px solid var(--nes-white);
      padding: 10px 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: all 0.1s;
    }
    .player-line-card:hover {
      border-color: var(--nes-cyan);
      background: rgba(32, 144, 208, 0.15);
    }
    .p-left { display: flex; align-items: center; gap: 10px; }
    .p-stats-mono { color: var(--nes-cyan); }

    /* Tactical Dressing Room Modal (Раздевалка) */
    .modal-backdrop {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.85);
      z-index: 1000;
      overflow-y: auto;
      padding: 24px 12px;
    }
    .modal-backdrop.active { display: flex; justify-content: center; align-items: flex-start; }
    .dressing-room-box {
      background: var(--nes-bg);
      border: 4px solid var(--nes-white);
      width: 100%;
      max-width: 900px;
      padding: 20px;
      position: relative;
    }
    .close-btn {
      position: absolute;
      top: 12px; right: 12px;
      background: var(--nes-black);
      color: var(--nes-white);
      border: 2px solid var(--nes-white);
      font-family: 'Press Start 2P', monospace;
      font-size: 10px;
      padding: 4px 8px;
      cursor: pointer;
    }
    .close-btn:hover { background: var(--nes-red); }

    .tactical-top {
      display: flex;
      gap: 20px;
      align-items: center;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }
    .pitch-board {
      width: 140px;
      height: 90px;
      background: var(--nes-field-green);
      border: 3px solid var(--nes-white);
      position: relative;
      flex-shrink: 0;
    }
    .pitch-center-line {
      position: absolute;
      top: 0; bottom: 0; left: 50%;
      width: 2px;
      background: var(--nes-white);
    }
    .pitch-center-circle {
      position: absolute;
      top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      width: 30px; height: 30px;
      border: 2px solid var(--nes-white);
      border-radius: 50%;
    }

    .stat-list-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
      border: 2px solid var(--nes-white);
      padding: 14px;
    }
    .stat-entry { display: flex; justify-content: space-between; }
    .stat-entry .val { color: var(--nes-cyan); }

    /* Match History NES Rows */
    .history-row {
      display: flex;
      justify-content: space-between;
      border-bottom: 1px solid rgba(252, 252, 252, 0.2);
      padding: 6px 0;
      font-size: 9px;
    }
    .history-row.win { color: var(--nes-field-green); }
    .history-row.loss { color: var(--nes-red); }

    /* Seasons Stage Navigation */
    .stage-row {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 10px;
      margin-bottom: 20px;
    }
    .stage-pill {
      background: var(--nes-bg);
      color: var(--nes-white);
      border: 2px solid var(--nes-white);
      font-family: 'Press Start 2P', monospace;
      font-size: 9px;
      padding: 8px 12px;
      cursor: pointer;
      white-space: nowrap;
    }
    .stage-pill.active {
      background: var(--nes-cyan);
      color: var(--nes-black);
      font-weight: 900;
    }

    /* Ship animation banner */
    .ship-banner {
      text-align: center;
      margin-bottom: 16px;
      font-size: 12px;
      color: var(--nes-cyan);
    }

    /* Duel VS Screen (Screenshot 2 Style) */
    .vs-arena {
      border: 3px solid var(--nes-white);
      background: var(--nes-bg);
      padding: 30px 20px;
      text-align: center;
      margin-bottom: 30px;
    }
    .vs-fighters {
      display: flex;
      justify-content: space-around;
      align-items: center;
      margin: 20px 0;
    }
    .fighter-card {
      background: var(--nes-white);
      color: var(--nes-black);
      padding: 16px;
      box-shadow: 6px 6px 0 var(--nes-black);
      border: 2px solid var(--nes-black);
      min-width: 160px;
      cursor: pointer;
    }
    .fighter-card img {
      width: 70px;
      height: 70px;
      border: 2px solid var(--nes-black);
      margin-bottom: 8px;
    }
    .vs-text {
      font-size: 32px;
      color: var(--nes-white);
      text-shadow: 4px 4px 0 var(--nes-black);
    }
  </style>
</head>
<body>

  <div class="container">

    <!-- Top T358 Title Box -->
    <div class="title-banner">
      <h1>⚽ НЕККЕТСУ СОККЕР ЛИГА ⚽</h1>
      <div class="version-tag">★★★ ВЕРСИЯ Т358 &bull; NES FAMICOM NETPLAY ★★★</div>
    </div>

    <!-- Main Navigation Bar -->
    <nav>
      <button class="menu-item-btn active" onclick="switchTab('leaderboard')">1🏆 ТАБЛИЦА РЕЙТИНГА</button>
      <button class="menu-item-btn" onclick="switchTab('roster')">2⚽ СОСТАВЫ И СТАТЫ</button>
      <button class="menu-item-btn" onclick="switchTab('seasons')">3📅 СЕЗОНЫ 1-9</button>
      <button class="menu-item-btn" onclick="switchTab('clutch')">4⚡ КЛАТЧ И РЕКОРДЫ</button>
      <button class="menu-item-btn" onclick="switchTab('h2h')">5⚔️ ДУЭЛИ VS</button>
    </nav>

    <!-- HUD Bar -->
    <div class="hud-box" id="hudBox"></div>

    <!-- TAB 1: LEADERBOARD -->
    <section id="tab-leaderboard" class="screen-view active">
      <div class="division-row">
        <button class="div-tab-btn active" onclick="filterDivision('all', this)">▶ Все лиги</button>
        <button class="div-tab-btn" onclick="filterDivision('Высшая', this)">Высшая</button>
        <button class="div-tab-btn" onclick="filterDivision('Средняя', this)">Средняя</button>
        <button class="div-tab-btn" onclick="filterDivision('Дворовая', this)">Дворовая</button>
        <input type="text" class="search-field" id="tableSearch" placeholder="ПОИСК ИГРОКА..." oninput="renderTable()">
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th onclick="sortTable('rank')">#</th>
              <th onclick="sortTable('player')">ИГРОК</th>
              <th onclick="sortTable('league')">ЛИГА</th>
              <th onclick="sortTable('active_elo')">ELO</th>
              <th onclick="sortTable('peak_elo')">PEAK</th>
              <th onclick="sortTable('matches')">ИГРЫ</th>
              <th onclick="sortTable('wins')">В-П</th>
              <th onclick="sortTable('win_rate')">WIN%</th>
              <th onclick="sortTable('reg_wins')">ОСН/ОТ/PK</th>
              <th onclick="sortTable('goal_diff')">МЯЧИ</th>
              <th onclick="sortTable('gapg')">GAPG</th>
              <th onclick="sortTable('dominator_score')">SCORE</th>
            </tr>
          </thead>
          <tbody id="tableBody"></tbody>
        </table>
      </div>
    </section>

    <!-- TAB 2: ROSTER (STYLE OF SCREENSHOT 4) -->
    <section id="tab-roster" class="screen-view">
      <div class="roster-field-box">
        <div class="section-title">⚽ Сделать замены? Выбор состава и характеристики</div>
        <div class="roster-columns" id="rosterList"></div>
      </div>
    </section>

    <!-- TAB 3: SEASONS (STYLE OF SCREENSHOT 2) -->
    <section id="tab-seasons" class="screen-view">
      <div class="ship-banner">🚢 ПЛЫВЁМ В СЕЗОНЫ NST 🚢</div>
      <div class="stage-row" id="seasonsStages"></div>
      <div id="seasonStageCard"></div>
    </section>

    <!-- TAB 4: CLUTCH & RECORDS -->
    <section id="tab-clutch" class="screen-view">
      <div class="section-title">⚽ Режим игры: +пенальти +овертаймы (Клатч-индекс)</div>
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>ИГРОК</th>
              <th>ОТ/PK ИГРЫ</th>
              <th>ОТ ПОБЕДЫ</th>
              <th>БУЛЛИТЫ (PK)</th>
              <th>ВСЕГО W</th>
              <th>КЛАТЧ WIN%</th>
              <th>СТАТУС</th>
            </tr>
          </thead>
          <tbody id="clutchTableBody"></tbody>
        </table>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; margin-top: 20px;">
        <div class="table-container" style="padding: 14px;">
          <div style="color: var(--nes-cyan); margin-bottom: 12px;">🔥 ТОП-10 ТРИЛЛЕРОВ</div>
          <div id="thrillersList"></div>
        </div>
        <div class="table-container" style="padding: 14px;">
          <div style="color: var(--nes-red); margin-bottom: 12px;">💥 ТОП РАЗГРОМОВ</div>
          <div id="blowoutsList"></div>
        </div>
      </div>
    </section>

    <!-- TAB 5: H2H DUELS (STYLE OF SCREENSHOT 2) -->
    <section id="tab-h2h" class="screen-view">
      <div class="vs-arena">
        <div class="section-title" style="justify-content: center;">⚽ Выбор соперников (Очные Дуэли)</div>
        <div style="margin: 16px 0; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
          <select id="h2hPlayer1" class="div-tab-btn" onchange="calculateH2H()"></select>
          <span style="color: var(--nes-cyan); font-size: 14px;">VS</span>
          <select id="h2hPlayer2" class="div-tab-btn" onchange="calculateH2H()"></select>
        </div>
        <div id="h2hResultBox"></div>
      </div>
    </section>

  </div>

  <!-- Tactical Dressing Room Modal (Раздевалка - Screenshot 3) -->
  <div class="modal-backdrop" id="playerModal" onclick="closeModal(event)">
    <div class="dressing-room-box" onclick="event.stopPropagation()">
      <button class="close-btn" onclick="closeModalDirect()">[X]</button>
      <div class="section-title">⚽ Раздевалка: Характеристики игрока</div>
      
      <div class="tactical-top">
        <div class="pitch-board">
          <div class="pitch-center-line"></div>
          <div class="pitch-center-circle"></div>
        </div>
        <img id="modalAvatar" class="nes-avatar" style="width: 56px; height: 56px;" src="">
        <div>
          <div id="modalPlayerName" style="font-size: 16px; color: var(--nes-white); margin-bottom: 4px;"></div>
          <div id="modalPlayerSub" style="color: var(--nes-cyan); font-size: 10px;"></div>
          <div id="modalVkLink" style="margin-top: 6px;"></div>
        </div>
      </div>

      <div class="stat-list-grid" id="modalStatsGrid"></div>

      <div class="section-title">⚽ Список официальных матчей</div>
      <div style="max-height: 320px; overflow-y: auto; border: 2px solid var(--nes-white); padding: 10px;" id="modalMatchHistory"></div>
    </div>
  </div>

  <!-- Embedded JSON Dataset -->
  <script>
    const DATA = __DATA_PLACEHOLDER__;
  </script>

  <!-- Script Logic -->
  <script>
    let currentDivisionFilter = 'all';
    let currentSortColumn = 'active_elo';
    let sortAsc = false;
    let selectedSeasonId = '9';

    window.addEventListener('DOMContentLoaded', () => {
      renderHUD();
      renderTable();
      renderRoster();
      renderSeasonsStages();
      renderSeasonStage(selectedSeasonId);
      renderClutchTable();
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
      document.querySelectorAll('.screen-view').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.menu-item-btn').forEach(el => el.classList.remove('active'));

      const activeSection = document.getElementById(`tab-${tabId}`);
      if (activeSection) activeSection.classList.add('active');

      const activeBtn = Array.from(document.querySelectorAll('.menu-item-btn')).find(b => b.getAttribute('onclick').includes(tabId));
      if (activeBtn) activeBtn.classList.add('active');
    }

    function renderHUD() {
      const m = DATA.metadata;
      document.getElementById('hudBox').innerHTML = `
        <div class="hud-item">МАТЧЕЙ: <span>${m.total_matches_analyzed}</span></div>
        <div class="hud-item">ГОЛОВ: <span>${m.total_goals_recorded}</span></div>
        <div class="hud-item">В СРЕДНЕМ: <span>${m.avg_goals_per_match}</span></div>
        <div class="hud-item">ОТ/БУЛЛИТЫ: <span>${m.total_ot_pk_matches}</span></div>
        <div class="hud-item">ИГРОКОВ: <span>${m.total_players_tracked}</span></div>
      `;
    }

    function filterDivision(div, btn) {
      currentDivisionFilter = div;
      document.querySelectorAll('.div-tab-btn').forEach(b => b.classList.remove('active'));
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

      if (currentDivisionFilter !== 'all') list = list.filter(p => p.league === currentDivisionFilter);
      if (q) list = list.filter(p => p.player.toLowerCase().includes(q) || (p.vk_name && p.vk_name.toLowerCase().includes(q)));

      list.sort((a, b) => {
        let v1 = a[currentSortColumn];
        let v2 = b[currentSortColumn];
        if (typeof v1 === 'string') return sortAsc ? v1.localeCompare(v2) : v2.localeCompare(v1);
        return sortAsc ? (v1 - v2) : (v2 - v1);
      });

      const tbody = document.getElementById('tableBody');
      tbody.innerHTML = list.map((p, idx) => {
        const gdStr = p.goal_diff > 0 ? `+${p.goal_diff}` : `${p.goal_diff}`;

        return `
          <tr>
            <td style="color: var(--nes-cyan);">${idx + 1}</td>
            <td>
              <div class="p-cell" onclick="openPlayerModal('${p.player}')">
                <img src="${p.avatar}" class="nes-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
                <div>
                  <span class="p-name-txt">${p.player}</span>
                  <span style="color: var(--nes-yellow);">${p.t358_icon}</span>
                </div>
              </div>
            </td>
            <td><span style="color: ${p.league === 'Высшая' ? 'var(--nes-yellow)' : (p.league === 'Средняя' ? 'var(--nes-cyan)' : 'var(--nes-field-green)')};">${p.league}</span></td>
            <td style="color: var(--nes-cyan); font-weight: 800;">${p.active_elo.toFixed(1)}</td>
            <td style="color: var(--nes-yellow);">${p.peak_elo.toFixed(1)}</td>
            <td>${p.matches}</td>
            <td>${p.wins}-${p.losses}</td>
            <td style="color: ${p.win_rate >= 60 ? 'var(--nes-field-green)' : (p.win_rate >= 45 ? '#ffffff' : 'var(--nes-red)')};">${p.win_rate}%</td>
            <td>${p.reg_wins}/${p.ot_wins}/${p.pk_wins}</td>
            <td style="color: ${p.goal_diff > 0 ? 'var(--nes-field-green)' : (p.goal_diff < 0 ? 'var(--nes-red)' : '#fff')};">${gdStr}</td>
            <td>${p.gapg.toFixed(2)}</td>
            <td style="color: var(--nes-yellow);">${p.dominator_score.toFixed(1)}</td>
          </tr>
        `;
      }).join('');
    }

    // Roster (Screenshot 4 style)
    function renderRoster() {
      const list = DATA.profiles;
      const container = document.getElementById('rosterList');
      container.innerHTML = list.map((p, idx) => `
        <div class="player-line-card" onclick="openPlayerModal('${p.player}')">
          <div class="p-left">
            <span style="color: var(--nes-white);">${idx + 1}</span>
            <img src="${p.avatar}" class="nes-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
            <div>
              <div style="color: #ffffff;">${p.player}</div>
              <div style="color: var(--nes-cyan); font-size: 8px;">${p.t358_shot} &bull; ${p.league}</div>
            </div>
          </div>
          <div class="p-stats-mono">
            <span>${p.stat_hp}</span>
            <span>${p.stat_sp}</span>
            <span style="color: #fff;">${p.rank_letter}</span>
            <span style="color: var(--nes-yellow);">${p.t358_icon}</span>
          </div>
        </div>
      `).join('');
    }

    // Modal (Dressing Room)
    function openPlayerModal(pName) {
      const p = DATA.profiles.find(x => x.player.toLowerCase() === pName.toLowerCase());
      if (!p) return;

      window.location.hash = `#/player/${p.player}`;

      document.getElementById('modalAvatar').src = p.avatar;
      document.getElementById('modalPlayerName').innerText = `${p.player} ${p.t358_icon}`;
      document.getElementById('modalPlayerSub').innerText = `${p.vk_name} | ${p.league} лига | ${p.status}`;

      const vkLink = p.vk_domain ? `https://vk.ru/${p.vk_domain}` : (p.vk_id ? `https://vk.ru/id${p.vk_id}` : null);
      document.getElementById('modalVkLink').innerHTML = vkLink ? `<a href="${vkLink}" target="_blank" style="color: var(--nes-cyan); font-size: 9px;">[СТРАНИЦА ВКОНТАКТЕ ↗]</a>` : '';

      document.getElementById('modalStatsGrid').innerHTML = `
        <div class="stat-entry"><span>Active Elo:</span><span class="val">${p.active_elo.toFixed(1)}</span></div>
        <div class="stat-entry"><span>Peak Elo:</span><span class="val">${p.peak_elo.toFixed(1)}</span></div>
        <div class="stat-entry"><span>Time-Decay:</span><span class="val" style="color: ${p.decay_penalty > 0 ? 'var(--nes-red)' : 'var(--nes-field-green)'};">-${p.decay_penalty}</span></div>
        <div class="stat-entry"><span>Игр сыграно:</span><span class="val">${p.matches}</span></div>
        <div class="stat-entry"><span>Победы/Пораж:</span><span class="val">${p.wins} - ${p.losses}</span></div>
        <div class="stat-entry"><span>Винрейт:</span><span class="val">${p.win_rate}%</span></div>
        <div class="stat-entry"><span>Осн. время:</span><span class="val">${p.reg_wins}W</span></div>
        <div class="stat-entry"><span>Овертаймы:</span><span class="val">${p.ot_wins}W</span></div>
        <div class="stat-entry"><span>Буллиты (PK):</span><span class="val">${p.pk_wins}W</span></div>
        <div class="stat-entry"><span>Клатч Win%:</span><span class="val">${p.clutch_win_rate}%</span></div>
        <div class="stat-entry"><span>Забито/Пропущ:</span><span class="val">${p.goals_for}:${p.goals_against}</span></div>
        <div class="stat-entry"><span>Сухие игры:</span><span class="val">${p.clean_sheets}</span></div>
      `;

      const matchRows = (p.match_history || []).slice(0, 30).map(m => `
        <div class="history-row ${m.result === 'W' ? 'win' : (m.result === 'L' ? 'loss' : '')}">
          <span>[${m.result}] VS ${m.opponent}</span>
          <span>${m.score_for}:${m.score_against} ${m.pk ? '[PK]' : (m.ot ? '[OT]' : '')}</span>
          <span style="color: #64748b;">${m.season}</span>
        </div>
      `).join('');

      document.getElementById('modalMatchHistory').innerHTML = matchRows || '<p>Матчи не найдены</p>';
      document.getElementById('playerModal').classList.add('active');
    }

    function closeModal(e) {
      if (e.target.id === 'playerModal') closeModalDirect();
    }
    function closeModalDirect() {
      document.getElementById('playerModal').classList.remove('active');
      window.location.hash = '#/leaderboard';
    }

    // Seasons
    function renderSeasonsStages() {
      const row = document.getElementById('seasonsStages');
      row.innerHTML = DATA.seasons.map(s => `
        <button class="stage-pill ${s.id === selectedSeasonId ? 'active' : ''}" onclick="selectSeason('${s.id}')">
          STAGE ${s.id}: ${s.name}
        </button>
      `).join('');
    }

    function selectSeason(sId) {
      selectedSeasonId = sId;
      renderSeasonsStages();
      renderSeasonStage(sId);
    }

    function renderSeasonStage(sId) {
      const s = DATA.seasons.find(x => x.id === sId);
      if (!s) return;

      const card = document.getElementById('seasonStageCard');
      const matchesList = (s.matches || []).slice(0, 35).map(m => `
        <div class="history-row">
          <span>${m.p1} VS ${m.p2}</span>
          <span style="color: var(--nes-cyan);">${m.s1}:${m.s2} ${m.pk ? '[PK]' : (m.ot ? '[OT]' : '')}</span>
        </div>
      `).join('');

      card.innerHTML = `
        <div class="table-container" style="padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 16px;">
            <div>
              <span style="color: var(--nes-cyan); font-size: 12px;">★★★ STAGE ${s.id} &bull; ${s.year} ГОД ★★★</span>
              <h2 style="font-size: 16px; color: #fff; margin-top: 4px;">${s.name}</h2>
              <div style="font-size: 9px; color: #94a3b8; margin-top: 2px;">${s.format} | Ром: ${s.emulator}</div>
            </div>
            <div style="color: var(--nes-yellow);">МАТЧЕЙ: ${s.matches ? s.matches.length : 0}</div>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px;">
            <div style="border: 2px solid var(--nes-yellow); padding: 10px;">
              <div style="color: var(--nes-yellow); font-size: 9px;">🥇 ЧЕМПИОН:</div>
              <div style="cursor: pointer; color: #fff; margin-top: 4px;" onclick="openPlayerModal('${s.champion}')">${s.champion}</div>
            </div>
            <div style="border: 2px solid var(--nes-white); padding: 10px;">
              <div style="font-size: 9px;">🥈 2-Е МЕСТО:</div>
              <div style="cursor: pointer; color: #fff; margin-top: 4px;" onclick="openPlayerModal('${s.runner_up}')">${s.runner_up}</div>
            </div>
            <div style="border: 2px solid var(--nes-white); padding: 10px;">
              <div style="font-size: 9px;">🥉 3-Е МЕСТО:</div>
              <div style="cursor: pointer; color: #fff; margin-top: 4px;" onclick="openPlayerModal('${s.third_place}')">${s.third_place}</div>
            </div>
            <div style="border: 2px solid var(--nes-cyan); padding: 10px;">
              <div style="color: var(--nes-cyan); font-size: 9px;">🏆 КУБОК:</div>
              <div style="cursor: pointer; color: #fff; margin-top: 4px;" onclick="openPlayerModal('${s.cup_winner}')">${s.cup_winner}</div>
            </div>
          </div>

          <div class="section-title">⚽ Летопись сезона:</div>
          <div style="background: rgba(0,0,0,0.3); border: 2px solid var(--nes-white); padding: 12px; margin-bottom: 16px; font-size: 10px; line-height: 1.8;">
            ${s.summary}
          </div>

          <div class="section-title">⚽ Протоколы матчей (${s.matches ? s.matches.length : 0}):</div>
          <div style="max-height: 300px; overflow-y: auto; border: 2px solid var(--nes-white); padding: 10px;">
            ${matchesList || '<p>Матчи в архиве</p>'}
          </div>
        </div>
      `;
    }

    // Clutch
    function renderClutchTable() {
      const tbody = document.getElementById('clutchTableBody');
      const list = [...DATA.profiles].filter(p => p.clutch_total >= 2).sort((a,b) => b.clutch_win_rate - a.clutch_win_rate || b.clutch_wins - a.clutch_wins);

      tbody.innerHTML = list.map(p => `
        <tr>
          <td>
            <div class="p-cell" onclick="openPlayerModal('${p.player}')">
              <img src="${p.avatar}" class="nes-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
              <span class="p-name-txt">${p.player}</span>
            </div>
          </td>
          <td>${p.clutch_total}</td>
          <td style="color: var(--nes-cyan);">${p.ot_wins}</td>
          <td style="color: var(--nes-yellow);">${p.pk_wins}</td>
          <td style="color: var(--nes-field-green);">${p.clutch_wins}</td>
          <td style="color: ${p.clutch_win_rate >= 60 ? 'var(--nes-field-green)' : '#fff'}; font-weight: 800;">${p.clutch_win_rate}%</td>
          <td>${p.status}</td>
        </tr>
      `).join('');

      document.getElementById('thrillersList').innerHTML = (DATA.records.top_thrillers || []).slice(0, 10).map(t => `
        <div class="history-row">
          <span>${t.p1} VS ${t.p2}</span>
          <span style="color: var(--nes-cyan);">${t.s1}:${t.s2} (${t.total_goals} голов)</span>
        </div>
      `).join('');

      document.getElementById('blowoutsList').innerHTML = (DATA.records.top_blowouts || []).slice(0, 10).map(b => `
        <div class="history-row loss">
          <span>${b.winner} VS ${b.loser}</span>
          <span>${b.s_win}:${b.s_lose} (+${b.diff})</span>
        </div>
      `).join('');
    }

    // H2H
    function initH2HSelects() {
      const s1 = document.getElementById('h2hPlayer1');
      const s2 = document.getElementById('h2hPlayer2');
      const options = DATA.profiles.map(p => `<option value="${p.player}">${p.player}</option>`).join('');
      s1.innerHTML = options;
      s2.innerHTML = options;

      s1.value = 'ectoPower';
      s2.value = 'Aeris';
      calculateH2H();
    }

    function calculateH2H() {
      const p1 = document.getElementById('h2hPlayer1').value;
      const p2 = document.getElementById('h2hPlayer2').value;
      const res = document.getElementById('h2hResultBox');

      if (p1 === p2) {
        res.innerHTML = '<p style="color: var(--nes-red); padding: 14px;">ВЫБЕРИТЕ ДВУХ РАЗНЫХ ИГРОКОВ</p>';
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
        <div class="history-row" style="color: #fff; padding: 6px 10px; border-bottom: 1px solid var(--nes-white);">
          <span>[${m.result}] ${p1} VS ${p2}</span>
          <span style="color: var(--nes-cyan);">${m.score_for} : ${m.score_against} ${m.pk ? '[PK]' : (m.ot ? '[OT]' : '')}</span>
          <span style="color: #64748b;">${m.season}</span>
        </div>
      `).join('');

      res.innerHTML = `
        <div class="vs-fighters">
          <div class="fighter-card" onclick="openPlayerModal('${p1}')">
            <img src="${p1Obj.avatar}" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p1}'">
            <div style="font-size: 12px; font-weight: 900;">${p1}</div>
            <div style="font-size: 9px; color: var(--nes-teal); margin-top: 4px;">${p1Obj.active_elo.toFixed(1)} ELO</div>
          </div>

          <div>
            <div class="vs-text">VS</div>
            <div style="font-size: 20px; color: var(--nes-yellow); margin-top: 8px;">${p1Wins} : ${p2Wins}</div>
            ${draws > 0 ? `<div style="font-size: 9px; color: #fff; margin-top: 2px;">${draws} НИЧЬИХ</div>` : ''}
            <div style="font-size: 9px; color: #fff; margin-top: 4px;">МЯЧИ: ${p1Goals}-${p2Goals}</div>
          </div>

          <div class="fighter-card" onclick="openPlayerModal('${p2}')">
            <img src="${p2Obj.avatar}" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p2}'">
            <div style="font-size: 12px; font-weight: 900;">${p2}</div>
            <div style="font-size: 9px; color: var(--nes-teal); margin-top: 4px;">${p2Obj.active_elo.toFixed(1)} ELO</div>
          </div>
        </div>

        <div class="section-title">⚽ Протоколы очных дуэлей (${duels.length}):</div>
        <div style="max-height: 260px; overflow-y: auto; text-align: left; border: 2px solid var(--nes-white); padding: 8px;">
          ${duelsHtml || '<p style="text-align: center; color: #94a3b8; padding: 10px;">МАТЧЕЙ В БАЗЕ НЕ НАЙДЕНО</p>'}
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

print(f"Goal 3 T358 Portal generated successfully at: {output_path}")
