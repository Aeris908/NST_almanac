import re, json, sys

sys.stdout.reconfigure(encoding='utf-8')

# Read build_nekketsu_portal_v2.py
with open("build_nekketsu_portal_v2.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the HTML section of tab-teams
old_section = re.search(r'<!-- TAB 7: TEAM TOURNAMENTS \(2X2\) -->.*?<div id="teamTournamentsList"></div>\s*</section>', content, re.DOTALL)
if not old_section:
    print("Could not find old tab-teams section!")
    sys.exit(1)

new_section_html = '''<!-- TAB 7: TEAM TOURNAMENTS (2X2) -->
    <section id="tab-teams" class="view-content">
      <div class="season-banner">
        <div class="season-title">👥 ОФИЦИАЛЬНЫЕ КОМАНДНЫЕ ЧЕМПИОНАТЫ GOAL 3 (2х2)</div>
        <div class="season-meta">
          <span>🎮 Goal 3 (NES) & Goal 4</span>
          <span>🏆 Эпоха Командных Битв (2012–2023)</span>
          <span>👥 Парный формат 2 на 2 & Клубы</span>
        </div>
        <p style="color: #cbd5e1; font-size: 14px; margin-top: 8px; line-height: 1.5;">
          Золотая летопись официальных командных чемпионатов сообщества NST: выберите турнир для детального просмотра всех сыгранных матчей, таблиц дивизионов, сетки плей-офф и составов легендарных дуэтов.
        </p>
      </div>

      <!-- Quick Tournament Selector Bar (like in Seasons tab!) -->
      <div style="margin-bottom: 20px;">
        <div style="font-size: 11px; color: #94a3b8; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">ВЫБЕРИТЕ КОМАНДНЫЙ ЧЕМПИОНАТ:</div>
        <div class="seasons-bar" id="teamTournamentsBar" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>
      </div>

      <!-- Main Detailed Container for Selected Tournament -->
      <div id="teamTournamentDetailContainer"></div>
    </section>'''

content = content.replace(old_section.group(0), new_section_html, 1)

# 2. Update JavaScript logic for renderTeamTournaments
old_js = re.search(r'let currentTeamFilter = \'all\';.*?function renderTeamTournaments\(\) \{.*?\n    \}', content, re.DOTALL)
if not old_js:
    print("Could not find old renderTeamTournaments JS!")
    sys.exit(1)

new_js = '''let selectedTeamTournId = 'team_champ_6';
    let teamSubTab = 'matches';
    let teamPairFilter = 'all';

    function selectTeamTournament(id) {
      selectedTeamTournId = id;
      teamPairFilter = 'all';
      renderTeamTournamentsBar();
      renderTeamTournamentDetails();
    }

    function switchTeamSubTab(subTab) {
      teamSubTab = subTab;
      renderTeamTournamentDetails();
    }

    function filterTeamPair(pair) {
      teamPairFilter = pair;
      renderTeamTournamentDetails();
    }

    function renderTeamTournamentsBar() {
      const bar = document.getElementById('teamTournamentsBar');
      if (!bar) return;
      const all = DATA.team_tournaments || [];

      bar.innerHTML = all.map(t => {
        const isAct = t.id === selectedTeamTournId;
        return `
          <button class="season-btn ${isAct ? 'active' : ''}" onclick="selectTeamTournament('${t.id}')">
            ${t.title.replace(' по Goal 3', '').replace(' (Эпоха зарождения 2х2)', '')}
          </button>
        `;
      }).join('');
    }

    function renderTeamTournaments() {
      renderTeamTournamentsBar();
      renderTeamTournamentDetails();
    }

    function renderTeamTournamentDetails() {
      const container = document.getElementById('teamTournamentDetailContainer');
      if (!container) return;

      const all = DATA.team_tournaments || [];
      const t = all.find(x => x.id === selectedTeamTournId) || all[0];
      if (!t) return;

      const matches = t.matches || [];
      const divisions = t.divisions || {};

      // Collect all unique team names for filter
      const teamsSet = new Set();
      matches.forEach(m => {
        if (m.t1) teamsSet.add(m.t1);
        if (m.t2) teamsSet.add(m.t2);
      });
      const allTeamsList = Array.from(teamsSet).sort();

      // Filter matches
      const filteredMatches = matches.filter(m => {
        if (teamPairFilter !== 'all') {
          return m.t1 === teamPairFilter || m.t2 === teamPairFilter;
        }
        return true;
      });

      // Master players chips
      const playersChips = (t.key_players || []).map(p => {
        const prof = (DATA.profiles || []).find(x => x.player.toLowerCase() === p.toLowerCase());
        const av = prof ? prof.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p}`;
        return `
          <span class="player-chip-link" onclick="openPlayerModal('${p}')" title="Открыть анкету ${p}">
            <img src="${av}" style="width: 16px; height: 16px; border-radius: 2px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p}'">
            ${p}
          </span>
        `;
      }).join('');

      // Build Sub-Tab content
      let subContentHtml = '';

      // 1. ALL MATCHES SUB-TAB
      if (teamSubTab === 'matches') {
        const pairOptions = allTeamsList.map(pair => `
          <option value="${pair}" ${teamPairFilter === pair ? 'selected' : ''}>${pair}</option>
        `).join('');

        const matchesListHtml = filteredMatches.length > 0 ? filteredMatches.map(m => {
          const isT1Win = m.score.startsWith('5:') || m.score.startsWith('6:') || m.score.startsWith('7:') || m.score.includes('победа t1') || m.score.includes('Победа leon') || m.score.includes('Победа Kamaz') || m.score.includes('Победа ectopower') || m.score.includes('Победа PacnyTHuK') || m.score.includes('Победа Буц');
          
          return `
            <div class="h2h-match-item" style="padding: 12px 16px; margin-bottom: 8px;">
              <div style="display: flex; align-items: center; gap: 8px; flex: 1.2; min-width: 140px;">
                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--nes-gold); font-weight: 800; min-width: 70px;">
                  ${m.tour || 'Матч'}
                </span>
                <span class="league-badge ${m.league && m.league.includes('Высшая') ? 'badge-premier' : (m.league && m.league.includes('Средняя') ? 'badge-middle' : 'badge-yard')}" style="font-size: 10px; padding: 2px 6px;">
                  ${m.league || 'Лига'}
                </span>
              </div>
              <div style="display: flex; align-items: center; justify-content: center; gap: 14px; flex: 2; flex-wrap: wrap;">
                <span style="font-family: var(--font-title); font-size: 14px; color: #fff; text-align: right; flex: 1;">
                  ${m.t1}
                </span>
                <div class="score-badge" style="font-size: 15px; padding: 5px 14px; letter-spacing: 1px; font-weight: 900; color: var(--nes-cyan); min-width: 80px; text-align: center;">
                  ${m.score}
                </div>
                <span style="font-family: var(--font-title); font-size: 14px; color: #cbd5e1; text-align: left; flex: 1;">
                  ${m.t2}
                </span>
              </div>
            </div>
          `;
        }).join('') : `
          <div style="background: rgba(0,0,0,0.4); border: 2px dashed #94a3b8; padding: 32px; text-align: center; color: #cbd5e1;">
            Матчи по выбранному фильтру не найдены.
          </div>
        `;

        subContentHtml = `
          <div style="margin-top: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px;">
              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-cyan);">
                📋 СЫГРАННЫЕ МАТЧИ И СЕРИИ (${filteredMatches.length} из ${matches.length}):
              </div>
              ${allTeamsList.length > 0 ? `
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span style="font-size: 12px; color: #94a3b8; font-weight: 700;">Фильтр по команде:</span>
                  <select class="clean-search" style="padding: 4px 10px; font-size: 12px;" onchange="filterTeamPair(this.value)">
                    <option value="all">▶ Все команды турнира</option>
                    ${pairOptions}
                  </select>
                </div>
              ` : ''}
            </div>
            <div>
              ${matchesListHtml}
            </div>
          </div>
        `;
      }

      // 2. TABLES SUB-TAB
      else if (teamSubTab === 'tables') {
        let divHtml = '';
        if (Object.keys(divisions).length > 0) {
          for (const [divName, rows] of Object.entries(divisions)) {
            const isTop = divName.includes('Высшая');
            divHtml += `
              <div style="margin-bottom: 24px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.15); padding: 16px;">
                <div style="font-family: var(--font-title); font-size: 15px; color: ${isTop ? 'var(--nes-gold)' : 'var(--nes-cyan)'}; margin-bottom: 12px;">
                  🏆 ${divName.toUpperCase()}
                </div>
                <table class="special-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Команда (Дуэт)</th>
                      ${rows[0]?.games !== undefined ? '<th>Матчи</th>' : ''}
                      ${rows[0]?.w !== undefined ? '<th>В</th>' : ''}
                      ${rows[0]?.l !== undefined ? '<th>П</th>' : ''}
                      ${rows[0]?.pts !== undefined ? '<th>Очки</th>' : ''}
                      ${rows[0]?.result !== undefined ? '<th>Итог</th>' : ''}
                    </tr>
                  </thead>
                  <tbody>
                    ${rows.map((r, i) => `
                      <tr>
                        <td style="color: ${i === 0 ? 'var(--nes-gold)' : (i === 1 ? '#cbd5e1' : (i === 2 ? '#d97706' : '#94a3b8'))}; font-weight: 800;">
                          ${r.rank !== undefined ? r.rank : (i + 1)}
                        </td>
                        <td style="font-weight: 800; color: #fff;">${r.team}</td>
                        ${r.games !== undefined ? `<td style="font-family: var(--font-mono);">${r.games}</td>` : ''}
                        ${r.w !== undefined ? `<td style="font-family: var(--font-mono); color: var(--nes-green); font-weight: 700;">${r.w}</td>` : ''}
                        ${r.l !== undefined ? `<td style="font-family: var(--font-mono); color: var(--nes-red);">${r.l}</td>` : ''}
                        ${r.pts !== undefined ? `<td style="font-family: var(--font-mono); font-weight: 900; color: var(--nes-gold); font-size: 14px;">${r.pts}</td>` : ''}
                        ${r.result !== undefined ? `<td style="font-size: 12px; color: #cbd5e1;">${r.result}</td>` : ''}
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            `;
          }
        } else {
          divHtml = `<div style="padding: 24px; text-align: center; color: #94a3b8;">Таблицы группового этапа не сохранились, смотрите матчи и плей-офф.</div>`;
        }
        subContentHtml = `<div style="margin-top: 16px;">${divHtml}</div>`;
      }

      // 3. PLAYOFF SUB-TAB
      else if (teamSubTab === 'playoff') {
        const playoffList = (t.playoff_matches || []).concat(matches.filter(m => m.tour && (m.tour.includes('финал') || m.tour.includes('место'))));
        // Deduplicate
        const seenPlayoff = new Set();
        const uniquePlayoff = [];
        playoffList.forEach(m => {
          const k = `${m.t1}_${m.t2}_${m.score}`;
          if (!seenPlayoff.has(k)) {
            seenPlayoff.add(k);
            uniquePlayoff.push(m);
          }
        });

        subContentHtml = `
          <div style="margin-top: 16px;">
            <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold); margin-bottom: 12px;">
              ⚡ МАТЧИ РЕШАЮЩЕЙ СТАДИИ ПЛЕЙ-ОФФ:
            </div>
            ${uniquePlayoff.length > 0 ? `
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px;">
                ${uniquePlayoff.map(m => `
                  <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                      <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">
                        ${m.league ? `${m.league} &bull; ` : ''}${m.tour || m.stage || 'Плей-офф'}
                      </div>
                      <div style="font-size: 13px; color: #fff; font-weight: 800; margin-top: 4px;">${m.t1}</div>
                      <div style="font-size: 13px; color: #94a3b8; font-weight: 700;">${m.t2}</div>
                    </div>
                    <div class="score-badge" style="font-size: 15px; padding: 5px 12px; font-weight: 900; color: var(--nes-cyan); margin-left: 12px;">
                      ${m.score}
                    </div>
                  </div>
                `).join('')}
              </div>
            ` : '<div style="color: #94a3b8;">Сетка плей-офф отсутствует.</div>'}
          </div>
        `;
      }

      // 4. ABOUT SUB-TAB
      else if (teamSubTab === 'about') {
        subContentHtml = `
          <div style="margin-top: 16px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">
            <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 10px;">
              📜 ИСТОРИЯ И РЕГЛАМЕНТ ТУРНИРА
            </div>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 16px;">
              ${t.description}
            </p>
            ${t.organizer ? `<div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">Организатор: <strong style="color: #fff;">${t.organizer}</strong></div>` : ''}
            ${t.prize_pool ? `<div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">Призовой фонд: <strong style="color: var(--nes-gold);">${t.prize_pool}</strong></div>` : ''}
            <div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">Формат: <strong style="color: var(--nes-cyan);">${t.format}</strong></div>
            <div style="font-size: 13px; color: #94a3b8;">Платформа / Ром: <strong style="color: #fff;">${t.game}</strong></div>
          </div>
        `;
      }

      container.innerHTML = `
        <div class="special-card" style="border-color: var(--nes-cyan); box-shadow: 4px 4px 0px #000;">
          <!-- Header Row -->
          <div class="special-header-row">
            <div>
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px;">
                <span class="special-tag tag-solo" style="background: #1e3a8a; color: #93c5fd; border-color: #3b82f6;">👥 2x2 КОМАНДНЫЙ ЧЕМПИОНАТ</span>
                <span style="font-size: 12px; color: var(--nes-gold); font-weight: 800; font-family: var(--font-mono);">${t.season_year}</span>
                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>
                <span style="font-size: 11px; color: #cbd5e1; font-weight: 700;">${t.game}</span>
                ${t.organizer ? `<span style="font-size: 11px; color: #94a3b8;">&bull;</span><span style="font-size: 11px; color: var(--nes-cyan);">Орг: ${t.organizer}</span>` : ''}
                ${t.prize_pool ? `<span style="font-size: 11px; color: var(--nes-gold); background: rgba(255,183,3,0.15); padding: 2px 6px; border: 1px solid var(--nes-gold);">💰 Фонд: ${t.prize_pool}</span>` : ''}
              </div>
              <h2 style="font-family: var(--font-title); font-size: 22px; color: #fff; margin: 0; text-shadow: 0 0 10px rgba(0,229,255,0.4);">
                ${t.title}
              </h2>
            </div>
          </div>

          <!-- Podium Box -->
          <div class="podium-box-grid">
            <div class="podium-slot gold">
              <span style="font-size: 24px;">🥇</span>
              <div>
                <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">1 МЕСТО &bull; ЧЕМПИОНЫ</div>
                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.champion}</div>
              </div>
            </div>
            <div class="podium-slot silver">
              <span style="font-size: 24px;">🥈</span>
              <div>
                <div style="font-size: 10px; color: #cbd5e1; font-weight: 800; text-transform: uppercase;">2 МЕСТО &bull; СЕРЕБРО</div>
                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.runner_up}</div>
              </div>
            </div>
            <div class="podium-slot bronze">
              <span style="font-size: 24px;">🥉</span>
              <div>
                <div style="font-size: 10px; color: #d97706; font-weight: 800; text-transform: uppercase;">3 МЕСТО &bull; БРОНЗА</div>
                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.bronze || '—'}</div>
              </div>
            </div>
          </div>

          <!-- Key Master Players -->
          ${playersChips ? `
            <div style="margin: 12px 0 16px 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span style="font-size: 11px; color: #94a3b8; font-weight: 700;">Мастера лиги в турнире:</span>
              ${playersChips}
            </div>
          ` : ''}

          <!-- Tournament Sub-Navigation Buttons (Tabs) -->
          <div style="display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 2px solid rgba(255,255,255,0.2); padding-bottom: 12px; margin-top: 16px;">
            <button class="filter-btn ${teamSubTab === 'matches' ? 'active' : ''}" onclick="switchTeamSubTab('matches')">
              📋 Все матчи турнира (${matches.length})
            </button>
            <button class="filter-btn ${teamSubTab === 'tables' ? 'active' : ''}" onclick="switchTeamSubTab('tables')">
              🏆 Таблицы лиг
            </button>
            <button class="filter-btn ${teamSubTab === 'playoff' ? 'active' : ''}" onclick="switchTeamSubTab('playoff')">
              ⚡ Сетка плей-офф
            </button>
            <button class="filter-btn ${teamSubTab === 'about' ? 'active' : ''}" onclick="switchTeamSubTab('about')">
              📜 Описание и история
            </button>
          </div>

          <!-- Active Sub-Tab Content -->
          ${subContentHtml}
        </div>
      `;
    }'''

content = content.replace(old_js.group(0), new_js, 1)

with open("build_nekketsu_portal_v2.py", "w", encoding="utf-8") as f:
    f.write(content)

print("build_nekketsu_portal_v2.py successfully upgraded with interactive drill-down for Team Tournaments!")
