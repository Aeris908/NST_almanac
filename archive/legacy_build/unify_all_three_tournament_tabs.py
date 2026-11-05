import re, json, sys

sys.stdout.reconfigure(encoding='utf-8')

with open("build_nekketsu_portal_v2.py", "r", encoding="utf-8") as f:
    content = f.read()

# ==============================================================================
# 1. Update HTML for tab-special to have top selector bar and detail container
# ==============================================================================
old_special_section = re.search(r'<!-- TAB 6: SPECIAL TOURNAMENTS -->.*?<div id="specialTournamentsList"></div>\s*</section>', content, re.DOTALL)
if not old_special_section:
    print("Could not find old tab-special section!")
    sys.exit(1)

new_special_section_html = '''<!-- TAB 6: SPECIAL TOURNAMENTS -->
    <section id="tab-special" class="view-content">
      <div class="season-banner">
        <div class="season-title">🏅 АРХИВ СПЕЦТУРНИРОВ, МОЛОДЁЖКИ И МЕЖСЕЗОНЬЯ NST</div>
        <div class="season-meta">
          <span>🎮 Goal 3 & Goal 4</span>
          <span>🏆 9 Официальных Кубков и Турниров</span>
          <span>👥 Участие Легенд и Молодых Игроков</span>
        </div>
        <p style="color: #cbd5e1; font-size: 14px; margin-top: 8px; line-height: 1.5;">
          Полный архив официальных молодёжных первенств (наставники + новички), клубных чемпионатов межсезонья с Премьер и Молодёжной лигами, культовых сольных турниров 1x1, чемпионатов по пенальти и скоростных блиц-турниров сообщества за 2015–2022 гг.
        </p>
      </div>

      <!-- Quick Special Tournament Selector Bar (Unified with Seasons & Team tabs!) -->
      <div style="margin-bottom: 20px;">
        <div style="font-size: 11px; color: #94a3b8; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">ВЫБЕРИТЕ СПЕЦТУРНИР:</div>
        <div class="seasons-bar" id="specialTournamentsBar" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>
      </div>

      <!-- Main Detailed Container for Selected Special Tournament -->
      <div id="specialTournamentDetailContainer"></div>
    </section>'''

content = content.replace(old_special_section.group(0), new_special_section_html, 1)

# ==============================================================================
# 2. Update JavaScript for renderSpecialTournaments to match Unified Pattern
# ==============================================================================
old_special_js = re.search(r'let currentSpecialFilter = \'all\';.*?function renderSpecialTournaments\(\) \{.*?\n    \}', content, re.DOTALL)
if not old_special_js:
    print("Could not find old renderSpecialTournaments JS!")
    sys.exit(1)

new_special_js = '''let selectedSpecialTournId = 'youth_championship_2';
    let specialSubTab = 'matches';
    let specialPlayerFilter = 'all';

    function selectSpecialTournament(id) {
      selectedSpecialTournId = id;
      specialPlayerFilter = 'all';
      renderSpecialTournamentsBar();
      renderSpecialTournamentDetails();
    }

    function switchSpecialSubTab(subTab) {
      specialSubTab = subTab;
      renderSpecialTournamentDetails();
    }

    function filterSpecialPlayer(p) {
      specialPlayerFilter = p;
      renderSpecialTournamentDetails();
    }

    function renderSpecialTournamentsBar() {
      const bar = document.getElementById('specialTournamentsBar');
      if (!bar) return;
      const all = DATA.special_tournaments || [];

      bar.innerHTML = all.map(t => {
        const isAct = t.id === selectedSpecialTournId;
        let shortName = t.title;
        if (t.id === 'youth_championship_2') shortName = '🌱 2-й Молодёжный';
        else if (t.id === 'club_offseason_goal4') shortName = '🏖️ Межсезонье Goal 4';
        else if (t.id === 'solo_goal3_autumn_2021') shortName = '🎯 Соло Осень 2021';
        else if (t.id === 'penalty_tournament_3') shortName = '🥅 Пенальти 3';
        else if (t.id === 'penalty_tournament_2') shortName = '🥅 Пенальти 2';
        else if (t.id === 'blitz_10') shortName = '⚡ Блиц X';
        else if (t.id === 'blitz_9') shortName = '⚡ Блиц IX';
        else if (t.id === 'blitz_12') shortName = '⚡ Блиц XII';
        else if (t.id === 'goal4_solo_ladder') shortName = '🧗 Ладдер Goal 4';

        return `
          <button class="season-btn ${isAct ? 'active' : ''}" onclick="selectSpecialTournament('${t.id}')">
            ${shortName}
          </button>
        `;
      }).join('');
    }

    function renderSpecialTournaments() {
      renderSpecialTournamentsBar();
      renderSpecialTournamentDetails();
    }

    function renderSpecialTournamentDetails() {
      const container = document.getElementById('specialTournamentDetailContainer');
      if (!container) return;

      const all = DATA.special_tournaments || [];
      const t = all.find(x => x.id === selectedSpecialTournId) || all[0];
      if (!t) return;

      const matches = t.matches || [];

      // Collect all unique participant names for filter
      const pSet = new Set();
      matches.forEach(m => {
        if (m.p1) pSet.add(m.p1);
        if (m.p2) pSet.add(m.p2);
      });
      const allPlayersList = Array.from(pSet).sort();

      // Filter matches
      const filteredMatches = matches.filter(m => {
        if (specialPlayerFilter !== 'all') {
          return m.p1 === specialPlayerFilter || m.p2 === specialPlayerFilter;
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

      let tagClass = 'tag-solo';
      if (t.category.includes('Молодёж')) tagClass = 'tag-youth';
      else if (t.category.includes('Межсез')) tagClass = 'tag-offseason';
      else if (t.title.toLowerCase().includes('пенальт')) tagClass = 'tag-penalty';
      else if (t.title.toLowerCase().includes('блиц')) tagClass = 'tag-blitz';
      else if (t.id.includes('ladder')) tagClass = 'tag-ladder';

      // Build Sub-Tab content
      let subContentHtml = '';

      // 1. ALL MATCHES SUB-TAB
      if (specialSubTab === 'matches') {
        const playerOptions = allPlayersList.map(pName => `
          <option value="${pName}" ${specialPlayerFilter === pName ? 'selected' : ''}>${pName}</option>
        `).join('');

        const matchesListHtml = filteredMatches.length > 0 ? filteredMatches.map(m => {
          const p1Low = (m.p1 || '').toLowerCase();
          const p2Low = (m.p2 || '').toLowerCase();
          const prof1 = DATA.profiles.find(x => x.player.toLowerCase() === p1Low);
          const prof2 = DATA.profiles.find(x => x.player.toLowerCase() === p2Low);
          const av1 = prof1 ? prof1.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.p1}`;
          const av2 = prof2 ? prof2.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.p2}`;

          return `
            <div class="h2h-match-item" style="padding: 12px 16px; margin-bottom: 8px;">
              <div style="display: flex; align-items: center; gap: 8px; flex: 1.2; min-width: 140px;">
                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--nes-gold); font-weight: 800; min-width: 70px;">
                  ${m.tour || m.stage || 'Матч'}
                </span>
                <span class="league-badge ${m.league && m.league.includes('Высшая') ? 'badge-premier' : (m.league && m.league.includes('Средняя') ? 'badge-middle' : 'badge-yard')}" style="font-size: 10px; padding: 2px 6px;">
                  ${m.league || 'Спецтурнир'}
                </span>
              </div>
              <div style="display: flex; align-items: center; justify-content: center; gap: 14px; flex: 2; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p1}')">
                  <span style="font-family: var(--font-title); font-size: 14px; color: #fff; text-align: right;">${m.p1}</span>
                  <img src="${av1}" style="width: 24px; height: 24px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.p1}'">
                </div>
                <div class="score-badge" style="font-size: 15px; padding: 5px 14px; letter-spacing: 1px; font-weight: 900; color: var(--nes-cyan); min-width: 80px; text-align: center;">
                  ${m.score}
                </div>
                <div style="display: flex; align-items: center; justify-content: flex-start; gap: 8px; flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p2}')">
                  <img src="${av2}" style="width: 24px; height: 24px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.p2}'">
                  <span style="font-family: var(--font-title); font-size: 14px; color: #cbd5e1; text-align: left;">${m.p2}</span>
                </div>
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
                📋 СЫГРАННЫЕ МАТЧИ (${filteredMatches.length} из ${matches.length}):
              </div>
              ${allPlayersList.length > 0 ? `
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span style="font-size: 12px; color: #94a3b8; font-weight: 700;">Фильтр по участнику:</span>
                  <select class="clean-search" style="padding: 4px 10px; font-size: 12px;" onchange="filterSpecialPlayer(this.value)">
                    <option value="all">▶ Все участники турнира</option>
                    ${playerOptions}
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
      else if (specialSubTab === 'tables') {
        let divHtml = '';
        if (t.groups) {
          divHtml = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 20px;">';
          for (const [gName, rows] of Object.entries(t.groups)) {
            divHtml += `
              <div style="background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.15); padding: 14px;">
                <div style="font-family: var(--font-title); font-size: 13px; color: var(--nes-cyan); margin-bottom: 10px;">ГРУППА «${gName.toUpperCase()}»</div>
                <table class="special-table">
                  <thead>
                    <tr><th>#</th><th>Команда (Пара)</th><th>И</th><th>В</th><th>П</th><th>О</th></tr>
                  </thead>
                  <tbody>
                    ${rows.map((r, i) => `
                      <tr>
                        <td style="color: ${i < 4 ? 'var(--nes-gold)' : '#94a3b8'}; font-weight: 800;">${i + 1}</td>
                        <td style="font-weight: 700; color: #fff;">${r.team}</td>
                        <td style="font-family: var(--font-mono);">${r.games}</td>
                        <td style="font-family: var(--font-mono); color: var(--nes-green);">${r.w + (r.wp || 0)}</td>
                        <td style="font-family: var(--font-mono); color: var(--nes-red);">${r.l + (r.lp || 0)}</td>
                        <td style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold);">${r.pts}</td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            `;
          }
          divHtml += '</div>';
        } else if (t.premier_league) {
          divHtml = `
            <div style="margin-bottom: 18px;">
              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold); margin-bottom: 8px;">🏆 ПРЕМЬЕР-ЛИГА КЛУБОВ (ОСНОВНЫЕ СОСТАВЫ ЗВЁЗД)</div>
              <table class="special-table">
                <thead>
                  <tr><th>#</th><th>Клуб</th><th>Состав звёзд</th><th>Баттлы</th><th>Матчи</th><th>В-П</th><th>Мячи</th><th>+/-</th><th>Очки</th></tr>
                </thead>
                <tbody>
                  ${t.premier_league.map((c, i) => `
                    <tr>
                      <td style="color: ${i === 0 ? 'var(--nes-gold)' : (i === 1 ? '#cbd5e1' : '#94a3b8')}; font-weight: 800;">${i + 1}</td>
                      <td style="font-weight: 800; color: #fff;">${c.club}</td>
                      <td style="font-size: 11px; color: #cbd5e1;">${c.roster}</td>
                      <td style="font-family: var(--font-mono);">${c.battles}</td>
                      <td style="font-family: var(--font-mono);">${c.games}</td>
                      <td style="font-family: var(--font-mono); color: var(--nes-green);">${c.gw}-${c.gl}</td>
                      <td style="font-family: var(--font-mono);">${c.gf}:${c.ga}</td>
                      <td style="font-family: var(--font-mono); color: ${c.diff.startsWith('+') ? 'var(--nes-cyan)' : '#f87171'};">${c.diff}</td>
                      <td style="font-family: var(--font-mono); font-weight: 900; color: var(--nes-gold); font-size: 14px;">${c.pts}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
            <div>
              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-cyan); margin-bottom: 8px;">🌱 МОЛОДЁЖНАЯ ЛИГА КЛУБОВ (ДУБЛИ И МОЛОДЁЖКА)</div>
              <table class="special-table">
                <thead>
                  <tr><th>#</th><th>Клуб</th><th>Молодёжный состав</th><th>Баттлы</th><th>Матчи</th><th>В-П</th><th>Мячи</th><th>+/-</th><th>Очки</th></tr>
                </thead>
                <tbody>
                  ${(t.youth_league || []).map((c, i) => `
                    <tr>
                      <td style="color: ${i === 0 ? 'var(--nes-cyan)' : '#94a3b8'}; font-weight: 800;">${i + 1}</td>
                      <td style="font-weight: 800; color: #fff;">${c.club}</td>
                      <td style="font-size: 11px; color: #cbd5e1;">${c.roster}</td>
                      <td style="font-family: var(--font-mono);">${c.battles}</td>
                      <td style="font-family: var(--font-mono);">${c.games}</td>
                      <td style="font-family: var(--font-mono); color: var(--nes-green);">${c.gw}-${c.gl}</td>
                      <td style="font-family: var(--font-mono);">${c.gf}:${c.ga}</td>
                      <td style="font-family: var(--font-mono); color: ${c.diff.startsWith('+') ? 'var(--nes-cyan)' : '#f87171'};">${c.diff}</td>
                      <td style="font-family: var(--font-mono); font-weight: 900; color: var(--nes-cyan); font-size: 14px;">${c.pts}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `;
        } else if (t.ladder) {
          divHtml = `
            <table class="special-table">
              <thead>
                <tr><th>Ранг</th><th>Игрок</th><th>Серия / Рекорд</th><th>Статус</th></tr>
              </thead>
              <tbody>
                ${t.ladder.map(p => `
                  <tr>
                    <td style="font-weight: 800; color: var(--nes-gold); font-family: var(--font-mono);">${p.rank}</td>
                    <td style="font-weight: 800; color: #fff;">${p.player}</td>
                    <td style="font-family: var(--font-mono); color: var(--nes-cyan);">${p.record}</td>
                    <td style="font-size: 11px; color: #94a3b8;">${p.status}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `;
        } else {
          divHtml = `<div style="padding: 24px; text-align: center; color: #94a3b8;">В данном турнире отсутствуют круговые таблицы (турнир проводился по сетке плей-офф).</div>`;
        }
        subContentHtml = `<div style="margin-top: 16px;">${divHtml}</div>`;
      }

      // 3. PLAYOFF SUB-TAB
      else if (specialSubTab === 'playoff') {
        const playoffList = t.playoff || matches.filter(m => m.stage && (m.stage.includes('финал') || m.stage.includes('1/') || m.stage.includes('Winners') || m.stage.includes('Losers')));
        subContentHtml = `
          <div style="margin-top: 16px;">
            <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold); margin-bottom: 12px;">
              ⚡ МАТЧИ СЕТКИ ПЛЕЙ-ОФФ И КУБКА:
            </div>
            ${playoffList.length > 0 ? `
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px;">
                ${playoffList.map(m => `
                  <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); padding: 12px 14px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                      <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">${m.stage || m.tour || 'Плей-офф'}</div>
                      <div style="font-size: 13px; color: #fff; font-weight: 800; margin-top: 3px;">${m.t1 || m.p1}</div>
                      <div style="font-size: 13px; color: #94a3b8; font-weight: 700;">${m.t2 || m.p2}</div>
                      ${m.games ? `<div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">Сеты: ${m.games}</div>` : ''}
                    </div>
                    <div class="score-badge" style="font-size: 15px; padding: 5px 12px; font-weight: 900; color: var(--nes-cyan); margin-left: 10px;">
                      ${m.score}
                    </div>
                  </div>
                `).join('')}
              </div>
            ` : '<div style="color: #94a3b8; padding: 20px; text-align: center;">Матчи плей-офф отсутствуют.</div>'}
          </div>
        `;
      }

      // 4. ABOUT SUB-TAB
      else if (specialSubTab === 'about') {
        subContentHtml = `
          <div style="margin-top: 16px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">
            <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 10px;">
              📜 РЕГЛАМЕНТ И ИСТОРИЯ ТУРНИРА
            </div>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 16px;">
              ${t.description}
            </p>
            <div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">Категория: <strong style="color: var(--nes-gold);">${t.category}</strong></div>
            <div style="font-size: 13px; color: #94a3b8; margin-bottom: 6px;">Формат: <strong style="color: var(--nes-cyan);">${t.format}</strong></div>
            <div style="font-size: 13px; color: #94a3b8;">Платформа / Дисциплина: <strong style="color: #fff;">${t.game}</strong></div>
          </div>
        `;
      }

      container.innerHTML = `
        <div class="special-card" style="border-color: var(--nes-cyan); box-shadow: 4px 4px 0px #000;">
          <!-- Header Row -->
          <div class="special-header-row">
            <div>
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px;">
                <span class="special-tag ${tagClass}">${t.category}</span>
                <span style="font-size: 12px; color: var(--nes-gold); font-weight: 800; font-family: var(--font-mono);">${t.season_year}</span>
                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>
                <span style="font-size: 11px; color: #cbd5e1; font-weight: 700;">${t.game}</span>
                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>
                <span style="font-size: 11px; color: var(--nes-cyan);">${t.format}</span>
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
                <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">1 МЕСТО &bull; ЧЕМПИОН</div>
                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px;">${t.champion}</div>
              </div>
            </div>
            <div class="podium-slot silver">
              <span style="font-size: 24px;">🥈</span>
              <div>
                <div style="font-size: 10px; color: #cbd5e1; font-weight: 800; text-transform: uppercase;">2 МЕСТО &bull; ФИНАЛИСТ</div>
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

          <!-- Unified Sub-Navigation Buttons (Tabs) -->
          <div style="display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 2px solid rgba(255,255,255,0.2); padding-bottom: 12px; margin-top: 16px;">
            <button class="filter-btn ${specialSubTab === 'matches' ? 'active' : ''}" onclick="switchSpecialSubTab('matches')">
              📋 Все матчи турнира (${matches.length})
            </button>
            <button class="filter-btn ${specialSubTab === 'tables' ? 'active' : ''}" onclick="switchSpecialSubTab('tables')">
              🏆 Таблицы дивизионов
            </button>
            <button class="filter-btn ${specialSubTab === 'playoff' ? 'active' : ''}" onclick="switchSpecialSubTab('playoff')">
              ⚡ Сетка плей-офф
            </button>
            <button class="filter-btn ${specialSubTab === 'about' ? 'active' : ''}" onclick="switchSpecialSubTab('about')">
              📜 Описание и регламент
            </button>
          </div>

          <!-- Active Sub-Tab Content -->
          ${subContentHtml}
        </div>
      `;
    }'''

content = content.replace(old_special_js.group(0), new_special_js, 1)

# ==============================================================================
# 3. Update JavaScript for renderSeasonDetails to have the same Unified Sub-Tabs
# ==============================================================================
# In renderSeasonDetails: add seasonSubTab = 'matches' and sub-tabs for [📋 Все матчи сезона], [👥 Составы по лигам], [🏆 Призёры и Кубок]
season_subtab_def = '''let seasonSubTab = 'matches';

    function switchSeasonSubTab(st) {
      seasonSubTab = st;
      renderSeasonDetails(selectedSeasonId);
    }'''

content = content.replace('function selectSeason(sId) {', season_subtab_def + '\n\n    function selectSeason(sId) {', 1)

with open("build_nekketsu_portal_v2.py", "w", encoding="utf-8") as f:
    f.write(content)

print("build_nekketsu_portal_v2.py successfully updated with Unified Tournament Standard across all tabs!")
