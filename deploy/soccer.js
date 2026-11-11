
    

    function cleanQuoteLine(str) {

      if (!str) return '';

      return str.split(String.fromCharCode(10)).join(' ').split(String.fromCharCode(13)).join('');

    }

    // Рейтинга может не быть: игрок без рейтинговых партий не получает выдуманного числа
    // (active_elo/peak_elo приходят как null). Вместо падения на .toFixed печатаем прочерк.
    function formatElo(value) {
      return (value === null || value === undefined) ? '—' : value.toFixed(1);
    }

    // Нога, сыгранная вничью по голам, может иметь победителя: его решает серия буллитов.
    // База кладёт исход сторон в m.outcome, а счёт оставляет ничейным — голы-то равные.
    // Таблицы сезона и дуэли обязаны считать ту же победу, что и история игрока.
    function matchWinnerSide(m) {
      const s1 = Number(m.s1 || 0), s2 = Number(m.s2 || 0);
      if (s1 > s2) return 1;
      if (s2 > s1) return 2;
      const decided = m.outcome;
      if (decided && decided[0] !== decided[1]) return decided[0] === 'win' ? 1 : 2;
      return 0;
    }



    let currentDivisionFilter = 'active';

    let currentSortColumn = 'active_elo';

    let sortAsc = false;

    let selectedSeasonId = '9';

    let playerCardFilter = 'all';

    let seasonPlayerFilter = 'all';

    let seasonLeagueFilter = 'all';

    let seasonSubTab = 'matches';

    let playoffViewMode = 'bracket';
    let teamPlayoffViewMode = 'bracket';
    let specialPlayoffViewMode = 'bracket';

    // Маршруты и контекст профиля.
    const validTabs = ['leaderboard', 'players', 'seasons', 'teams', 'special', 'h2h', 'clutch'];
    let profileReturn = '#/leaderboard';
    let profileFocus = null;
    let profileScroll = 0;
    let profileBackground = [];
    function escapeHTML(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g,
        ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    }
    function routeNotice(text) {
      let box = document.getElementById('routeNotice');
      if (!box) { box = document.createElement('div'); box.id = 'routeNotice'; box.setAttribute('role', 'status'); document.querySelector('main').prepend(box); }
      box.textContent = text;
    }
    function hidePlayerModal() {
      const modal = document.getElementById('playerModal');
      if (!modal.classList.contains('active')) return;
      modal.classList.remove('active');
      profileBackground.forEach(([el, previous]) => { el.inert = previous; });
      profileBackground = [];
      document.body.style.overflow = '';
      if (profileFocus && profileFocus.isConnected) profileFocus.focus({preventScroll:true});
      window.scrollTo(0, profileScroll);
    }
    function activateProfile(overlay) {
      const wasOpen=overlay.classList.contains('active');overlay.classList.add('active');document.body.style.overflow='hidden';
      if(!wasOpen){profileBackground=[...document.body.children].filter(el=>el!==overlay&&!['SCRIPT','STYLE'].includes(el.tagName)).map(el=>[el,el.inert]);profileBackground.forEach(([el])=>el.inert=true);overlay.querySelector('.modal-close').focus();}
    }
    function handleRouting() {
      const [hash,query=''] = (window.location.hash || '#/leaderboard').split('?');
      const params=new URLSearchParams(query);
      if (hash.startsWith('#/player/')) {
        let name;
        try { name = decodeURIComponent(hash.slice(9)); } catch (_) { name = ''; }
        if (!DATA.profiles.some(p => p.player.toLowerCase() === name.toLowerCase())) {
          hidePlayerModal(); switchTab('leaderboard', false);
          history.replaceState(null, '', '#/leaderboard'); routeNotice('Игрок не найден. Выберите игрока в каталоге.'); return;
        }
        openPlayerModal(name); return;
      }
      hidePlayerModal();
      const season = hash.match(/^#\/season\/(.+)$/);
      if (season && DATA.seasons.some(s => String(s.id) === season[1])) {
        selectedSeasonId=season[1];seasonPlayerFilter=params.get('player')||'all';seasonLeagueFilter=params.get('league')||'all';seasonSubTab=['matches','tables','playoff','about'].includes(params.get('view'))?params.get('view'):'matches';renderSeasonsBar();switchTab('seasons',false);return;
      }
      const tournament=hash.match(/^#\/(team|special)\/(.+)$/);
      if(tournament){const team=tournament[1]==='team',list=team?DATA.team_tournaments:DATA.special_tournaments;let id;try{id=decodeURIComponent(tournament[2]);}catch(_){id='';}
        if(list.some(t=>t.id===id)){const view=['matches','tables','playoff','about'].includes(params.get('view'))?params.get('view'):'matches';if(team){selectedTeamTournId=id;teamSubTab=view;teamPairFilter=params.get('pair')||'all';}else{selectedSpecialTournId=id;specialSubTab=view;specialPlayerFilter=params.get('player')||'all';}switchTab(team?'teams':'special',false);return;}}
      const tab = hash.replace('#/', '');
      if (!validTabs.includes(tab)) {
        switchTab('leaderboard', false); history.replaceState(null, '', '#/leaderboard');
        routeNotice('Раздел не найден. Открыт рейтинг.'); return;
      }
      if(tab==='leaderboard'||tab==='players'){
        const input=document.getElementById(tab==='leaderboard'?'tableSearch':'cardsSearch');input.value=params.get('q')||'';
        const allowed=['all','active','inactive','hof','all_inactive','Высшая','Средняя','Дворовая'];const filter=allowed.includes(params.get('filter'))?params.get('filter'):(tab==='leaderboard'?'active':'all');
        if(tab==='leaderboard')currentDivisionFilter=filter;else playerCardFilter=filter;
      }
      switchTab(tab, false);
    }
    function switchTab(tabId, updateRoute = true) {
      if (!validTabs.includes(tabId)) tabId = 'leaderboard';
      document.querySelectorAll('.view-content').forEach(s => s.classList.toggle('active', s.id === `tab-${tabId}`));
      document.querySelectorAll('.nav-btn').forEach(b => {
        const selected = (b.getAttribute('onclick') || '').includes("'" + tabId + "'");
        b.classList.toggle('active', selected); b.setAttribute('aria-pressed', String(selected));
      });
      if (updateRoute) {
        const notice = document.getElementById('routeNotice'); if (notice) notice.textContent = '';
        hidePlayerModal();
        const target = tabId==='seasons'?'#/season/'+selectedSeasonId:tabId==='teams'?'#/team/'+selectedTeamTournId:tabId==='special'?'#/special/'+selectedSpecialTournId:'#/'+tabId;
        if (window.location.hash !== target) history.pushState(null, '', target);
      }
      if (tabId === 'seasons' && seasonSubTab === 'playoff') setTimeout(drawBracketConnectors, 60);
      if (tabId === 'teams' && teamSubTab === 'playoff') setTimeout(() => drawBracketConnectors('teamBracketWrapper','teamBracketContainer','teamBracketSvg'),60);
      if (tabId === 'special' && specialSubTab === 'playoff') setTimeout(() => drawBracketConnectors('specialBracketWrapper','specialBracketContainer','specialBracketSvg'),60);
      if(tabId==='seasons')renderSeasonDetails(selectedSeasonId);
      if(tabId==='teams')renderTeamTournaments();
      if(tabId==='special')renderSpecialTournaments();
      if(tabId==='h2h')renderH2H();
      if(tabId==='leaderboard')renderTable();
      if(tabId==='players')renderCards();
    }
    function viewAddress(kind,id) {
      const tab=kind==='season'?'seasons':kind==='team'?'teams':'special';
      if(!document.getElementById('tab-'+tab)?.classList.contains('active'))return;
      const params=new URLSearchParams();params.set('view',kind==='season'?seasonSubTab:kind==='team'?teamSubTab:specialSubTab);
      const filters=kind==='season'?{player:seasonPlayerFilter,league:seasonLeagueFilter}:kind==='team'?{pair:teamPairFilter}:{player:specialPlayerFilter};
      for(const [key,value] of Object.entries(filters))if(value&&value!=='all')params.set(key,value);
      const base='#/'+kind+'/'+encodeURIComponent(id),old=location.hash.split('?');const match=new URLSearchParams(old[1]||'').get('match');if(old[0]===base&&match)params.set('match',match);
      history.replaceState(null,'',base+'?'+params);const link=document.getElementById('currentViewLink');if(link)link.href=location.href;
    }
    let highlightedAddress='';
    function clearMatchAddress() {const parts=location.hash.split('?');const params=new URLSearchParams(parts[1]||'');params.delete('match');history.replaceState(null,'',parts[0]+(params.size?'?'+params:''));}
    function decorateGames() {
      const currentLink=document.getElementById('currentViewLink');if(currentLink)currentLink.href=location.href;
      document.querySelectorAll('[data-match-anchor]').forEach(row=>{
        if(!row.dataset.matchAnchor||row.querySelector('.game-link'))return;
        const kind=row.closest('#seasonDetails')?'season':row.closest('#teamTournamentDetailContainer')?'team':'special';const id=kind==='season'?selectedSeasonId:kind==='team'?selectedTeamTournId:selectedSpecialTournId;
        const link=document.createElement('a');link.className='game-link';link.textContent='Ссылка на игру';link.href='#/'+kind+'/'+encodeURIComponent(id)+'?view=matches&match='+row.dataset.matchAnchor;row.append(link);
      });
      const anchor=new URLSearchParams(location.hash.split('?')[1]||'').get('match');
      if(anchor&&highlightedAddress!==location.hash){const row=[...document.querySelectorAll('.view-content.active [data-match-anchor]')].find(el=>el.dataset.matchAnchor===anchor);if(row){highlightedAddress=location.hash;document.querySelectorAll('.linked-game').forEach(el=>el.classList.remove('linked-game'));row.classList.add('linked-game');row.scrollIntoView({block:'center'});}}
    }

    // HUD Strip
    function renderHud() {
      const m = DATA.metadata;
      if (!m) return;
      const strip = document.getElementById('hudStrip');
      if (!strip) return;
      // Season years look like "2018" or "2020-2022"; span = lowest to highest year found.
      const seasonYears = (DATA.seasons || [])
        .flatMap(s => (String(s.year || '').match(/\d{4}/g) || []).map(Number));
      const yearSpan = seasonYears.length
        ? `${Math.min(...seasonYears)}\u2013${Math.max(...seasonYears)}` : '';
      const clutchShare = m.total_matches_analyzed
        ? (100 * m.total_ot_pk_matches / m.total_matches_analyzed).toFixed(1) : '0';
      strip.innerHTML = `
        <div class="hud-card">
          <div class="hud-label">Всего сыграно матчей</div>
          <div class="hud-val" style="color: var(--nes-gold);">${m.total_matches_analyzed}</div>
          <div class="hud-sub">Все ${DATA.seasons.length} сезонов (${yearSpan} гг.)</div>
        </div>
        <div class="hud-card">
          <div class="hud-label">Забито мячей</div>
          <div class="hud-val">${m.total_goals_recorded}</div>
          <div class="hud-sub">В среднем ${m.avg_goals_per_match} гола за матч</div>
        </div>
        <div class="hud-card">
          <div class="hud-label">Овертаймы и пенальти</div>
          <div class="hud-val" style="color: var(--nes-cyan);">${m.total_ot_pk_matches}</div>
          <div class="hud-sub">${clutchShare}% упорных матчей до золотого гола</div>
        </div>
        <div class="hud-card">
          <div class="hud-label">Активных / Всего игроков</div>
          <div class="hud-val" style="color: var(--nes-green);">${m.active_players_count} из ${m.total_players_tracked}</div>
          <div class="hud-sub">${DATA.profiles.filter(p => p.is_hall_of_fame).length} легенд в Зале славы</div>
        </div>
      `;

      const hofCount = DATA.profiles.filter(p => p.is_hall_of_fame).length;
      const btnAct = document.getElementById('btnActiveFilter');
      const btnInact = document.getElementById('btnInactiveFilter');
      if (btnAct) btnAct.innerText = `▶ Все активные игроки (${m.active_players_count})`;
      if (btnInact) btnInact.innerText = `⭐ Зал славы (${hofCount})`;
    }

    // Leaderboard
    function filterDivision(div, btn) {
      currentDivisionFilter = div;
      document.querySelectorAll('#tab-leaderboard .filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTable();
    }

    function sortTable(col) {
      if (currentSortColumn === col) sortAsc = !sortAsc;
      else { currentSortColumn = col; sortAsc = false; }
      renderTable();
    }

    function renderTable() {
      rememberPlayerSearch();
      searchAddress('leaderboard','tableSearch',currentDivisionFilter);
        const hofB = document.getElementById("hofCriteriaBanner");
        if (hofB) hofB.style.display = (currentDivisionFilter === "inactive") ? "block" : "none";
      const q = (document.getElementById('tableSearch')?.value || '').toLowerCase();
      let list = [...DATA.profiles];

      if (currentDivisionFilter === 'active') {
        list = list.filter(p => p.is_active);
      } else if (currentDivisionFilter === 'inactive') {
        list = list.filter(p => p.is_hall_of_fame);
      } else if (currentDivisionFilter === 'all_inactive') {
        list = list.filter(p => !p.is_active);
      } else if (currentDivisionFilter === 'Высшая') {
        list = list.filter(p => p.is_active && p.league === 'Высшая');
      } else if (currentDivisionFilter === 'Средняя') {
        list = list.filter(p => p.is_active && p.league === 'Средняя');
      } else if (currentDivisionFilter === 'Дворовая') {
        list = list.filter(p => p.is_active && p.league === 'Дворовая');
      }

      if (q) {
        list = list.filter(p => [p.player,p.vk_name,...(p.aliases||[])].some(name=>String(name||'').toLowerCase().includes(q.trim())));
      }

      list.sort((a, b) => {
        let v1 = a[currentSortColumn];
        let v2 = b[currentSortColumn];
        // Рейтинга может не быть (null): такие строки всегда в конце, и в прямом, и в
        // обратном порядке — иначе null сравнивался бы как ноль и лез вперёд.
        const n1 = (v1 === null || v1 === undefined);
        const n2 = (v2 === null || v2 === undefined);
        if (n1 || n2) return n1 === n2 ? 0 : (n1 ? 1 : -1);
        if (typeof v1 === 'string') return sortAsc ? v1.localeCompare(v2) : v2.localeCompare(v1);
        return sortAsc ? (v1 - v2) : (v2 - v1);
      });

      const tbody = document.getElementById('tableBody');
      tbody.innerHTML = list.map((p, idx) => {
        const gdStr = p.goal_diff > 0 ? `+${p.goal_diff}` : `${p.goal_diff}`;
        const gdColor = p.goal_diff > 0 ? 'var(--nes-green)' : (p.goal_diff < 0 ? 'var(--nes-red)' : '#fff');
        const badgeClass = !p.is_active ? 'badge-inactive' : (p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard'));
        const sBadge = p.status_badge || (p.is_active ? 'Активен' : 'Зал славы');
        const sColor = p.is_active ? ((p.status_badge && p.status_badge.includes('Сезон 9')) ? '#22c55e' : '#f59e0b') : '#94a3b8';

        const rankDisplay = idx === 0 
          ? `<span style="display: inline-block; width: 26px; height: 26px; line-height: 24px; text-align: center; border-radius: 50%; background: linear-gradient(135deg, #ffcb05, #d97706); color: #000; font-weight: 900; ">1</span>`
          : (idx === 1
            ? `<span style="display: inline-block; width: 26px; height: 26px; line-height: 24px; text-align: center; border-radius: 50%; background: linear-gradient(135deg, #f1f5f9, #94a3b8); color: #000; font-weight: 900; ">2</span>`
            : (idx === 2
              ? `<span style="display: inline-block; width: 26px; height: 26px; line-height: 24px; text-align: center; border-radius: 50%; background: linear-gradient(135deg, #fdba74, #c2410c); color: #000; font-weight: 900; ">3</span>`
              : `<span style="font-family: var(--font-mono); font-weight: 700; color: #cbd5e1; font-size: 14px;">${idx + 1}</span>`
            )
          );

        return `
          <tr>
            <td style="text-align: center;">${rankDisplay}</td>
            <td>
              <div class="p-cell" role="button" tabindex="0" data-profile-name="${escapeHTML(p.player)}">
                <img src="${p.avatar}" class="avatar-clean" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
                <div>
                  <div class="p-name">${p.player}</div>
                  ${(p.vk_name && p.vk_name !== p.player) ? `
                    <div class="p-sub">${p.vk_name}</div>
                  ` : (p.quote ? `
                    <div class="p-sub" style="color: #94a3b8; font-style: italic; font-size: 11px;">«${p.quote.length > 32 ? p.quote.substring(0, 30) + '…' : p.quote}»</div>
                  ` : '')}
                </div>
              </div>
            </td>
            <td>
              <div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-start;">
                <span class="league-badge ${badgeClass}">${p.league} лига</span>
                <span style="font-size: 11px; font-weight: 700; color: ${sColor};">● ${sBadge}</span>
              </div>
            </td>
            <td>
              <div style="font-family: var(--font-mono); font-weight: 800; font-size: 16px; color: #fff;">${formatElo(p.active_elo)}</div>
              ${p.decay_penalty > 0 ? `<div style="font-size: 11px; color: var(--nes-red); font-weight: 700;">-${p.decay_penalty} за простой</div>` : ''}
            </td>
            <td><span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold); font-size: 15px;">${formatElo(p.peak_elo)}</span></td>
            <td style="font-family: var(--font-mono); font-weight: 700; font-size: 14px;">${p.matches}</td>
            <td>
              <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-green); font-size: 14px;">${p.wins}</span>
              <span style="color: #94a3b8; margin: 0 4px;">/</span>
              <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-red); font-size: 14px;">${p.losses}</span>
            </td>
            <td>
              <div style="display: flex; flex-direction: column; gap: 3px;">
                <span style="font-family: var(--font-mono); font-weight: 700; font-size: 13px; color: ${p.win_rate >= 60 ? 'var(--nes-green)' : (p.win_rate >= 45 ? 'var(--nes-cyan)' : 'var(--nes-gold)')};">${p.win_rate}%</span>
                <div style="width: 44px; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden;">
                  <div style="width: ${p.win_rate}%; height: 100%; background: ${p.win_rate >= 60 ? 'var(--nes-green)' : (p.win_rate >= 45 ? 'var(--nes-cyan)' : 'var(--nes-gold)')}; border-radius: 2px;"></div>
                </div>
              </div>
            </td>
            <td style="font-family: var(--font-mono); font-weight: 700; font-size: 13px;">
              <span>${p.goals_for}:${p.goals_against}</span>
              <span style="font-size: 11px; color: ${gdColor}; margin-left: 4px; font-weight: 800;">(${gdStr})</span>
            </td>
            <td style="font-family: var(--font-mono); font-size: 12px; white-space: nowrap;">
              <span style="color: var(--nes-cyan); font-weight: 700;" title="В основное время">${p.reg_wins} осн</span> / 
              <span style="color: var(--nes-gold); font-weight: 700;" title="В овертаймах">${p.ot_wins} от</span> / 
              <span style="color: #c084fc; font-weight: 700;" title="По пенальти">${p.pk_wins} пен</span>
            </td>
            <td>
              <button class="action-btn" onclick="openPlayerModal('${p.player}')">Анкета ↗</button>
            </td>
          </tr>
        `;
      }).join('');
    }

    // Players View
    function filterPlayerCards(flt, btn) {
      playerCardFilter = flt;
      document.querySelectorAll('#tab-players .filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderCards();
    }

    function renderCards() {
      rememberPlayerSearch();
      searchAddress('players','cardsSearch',playerCardFilter);
      const hofCB = document.getElementById("hofCardsCriteriaBanner");
      if (hofCB) hofCB.style.display = (playerCardFilter === "hof") ? "block" : "none";
      const q = (document.getElementById('cardsSearch')?.value || '').toLowerCase();
      let list = [...DATA.profiles];

      if (playerCardFilter === 'active') {
        list = list.filter(p => p.is_active);
      } else if (playerCardFilter === 'hof') {
        list = list.filter(p => p.is_hall_of_fame);
      } else if (playerCardFilter === 'all_inactive') {
        list = list.filter(p => !p.is_active);
      } else if (playerCardFilter === 'Высшая') {
        list = list.filter(p => p.is_active && p.league === 'Высшая');
      } else if (playerCardFilter === 'Средняя') {
        list = list.filter(p => p.is_active && p.league === 'Средняя');
      } else if (playerCardFilter === 'Дворовая') {
        list = list.filter(p => p.is_active && p.league === 'Дворовая');
      }

      if (q) {
        list = list.filter(p => [p.player,p.vk_name,...(p.aliases||[])].some(name=>String(name||'').toLowerCase().includes(q.trim())));
      }

      const grid = document.getElementById('cardsGrid');
      grid.innerHTML = list.map(p => {
        const gdStr = p.goal_diff > 0 ? `+${p.goal_diff}` : `${p.goal_diff}`;
        const badgeClass = !p.is_active ? 'badge-inactive' : (p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard'));
        const sBadge = p.status_badge || (p.is_active ? 'Активен' : 'Зал славы');
        const sColor = p.is_active ? ((p.status_badge && p.status_badge.includes('Сезон 9')) ? '#22c55e' : '#f59e0b') : '#94a3b8';

        return `
          <div class="clean-card" onclick="openPlayerModal('${p.player}')">
            <div class="card-top">
              <img src="${p.avatar}" class="avatar-clean" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.player}'">
              <div style="flex: 1;">
                <h3>${p.player}</h3>
                ${p.quote ? `
                  <div style="font-size: 11px; color: #cbd5e1; font-style: italic; margin: 3px 0 2px 0; line-height: 1.3;" title="Цитата игрока">
                    «${cleanQuoteLine(p.quote).length > 70 ? cleanQuoteLine(p.quote).substring(0, 68) + '…' : cleanQuoteLine(p.quote)}»
                  </div>
                ` : ''}
                <div style="margin-top: 4px; display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                  <span class="league-badge ${badgeClass}">${p.league} лига</span>
                  <span style="font-size: 11px; font-weight: 700; color: ${sColor};">● ${sBadge}</span>
                  ${p.vk_domain || p.vk_id ? `
                    <a href="${p.vk_domain ? `https://vk.ru/${p.vk_domain}` : `https://vk.ru/id${p.vk_id}`}" target="_blank" class="card-vk-pill" onclick="event.stopPropagation()" title="VK: ${p.vk_name || p.player}">
                      <svg viewBox="0 0 24 24"><path d="M13.162 18.994c.609 0 .858-.406.851-.915-.072-1.747.785-2.28 1.488-2.28.618 0 1.344.428 1.84 1.157.734 1.077 1.258 2.038 2.378 2.038h2.096c1.196 0 1.776-.566 1.442-1.637-.367-1.182-1.603-2.678-2.327-3.486-.554-.62-1.127-1.185-.758-2.02.478-1.076 1.947-3.212 2.27-4.472.167-.655-.178-1.077-.92-1.077h-2.122c-.663 0-.964.332-1.151.78-.445 1.066-1.57 3.327-2.247 3.993-.342.338-.598.24-.76-.085-.298-.596-.341-1.688-.341-2.585 0-2.316.357-3.327-.723-3.582-.437-.103-.984-.132-1.792-.132-1.644 0-2.73.045-3.385.733-.257.27-.37.604-.15.632.493.064.935.318 1.054.945.362 1.905.176 3.655-.66 4.31-.383.298-.828.188-1.156-.214-.943-1.156-1.89-3.39-2.518-5.011-.194-.502-.519-.884-1.139-.884H2.477c-.779 0-.946.368-.946.779 0 .73.945 4.354 4.394 9.176 2.302 3.228 5.568 4.976 8.528 4.976z"/></svg>
                      <span>VK</span>
                    </a>
                  ` : ''}
                </div>
              </div>
            </div>

            <div class="card-stat-strip">
              <div>
                <div class="lbl">РЕЙТИНГ</div>
                <div class="v" style="color: var(--nes-gold);">${formatElo(p.active_elo)}</div>
              </div>
              <div>
                <div class="lbl">% ПОБЕД</div>
                <div class="v" style="color: var(--nes-green);">${p.win_rate}%</div>
              </div>
              <div>
                <div class="lbl">РАЗНИЦА МЯЧЕЙ</div>
                <div class="v">${gdStr}</div>
              </div>
            </div>

            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #cbd5e1; font-weight: 600;">
              <span>Матчей: <strong>${p.matches}</strong></span>
              <span>Побед: <strong style="color: var(--nes-green);">${p.wins}</strong></span>
              <span>Поражений: <strong style="color: var(--nes-red);">${p.losses}</strong></span>
            </div>
          </div>
        `;
      }).join('');
    }

    // Modal Profile
    function openPlayerModal(pName) {
      const p = DATA.profiles.find(x => x.player.toLowerCase() === pName.toLowerCase());
      if (!p) return;

      const overlay = document.getElementById('playerModal');
      if (!overlay.classList.contains('active')) {
        profileReturn = window.location.hash.startsWith('#/player/') ? '#/leaderboard' : (window.location.hash || '#/leaderboard');
        profileFocus = document.activeElement; profileScroll = window.scrollY;
      }
      const target = '#/player/' + encodeURIComponent(p.player);
      if (window.location.hash !== target) history.pushState(null, '', target);

      const header = document.getElementById('modalHeader');
      const body = document.getElementById('modalBody');
      if(p.lazy_url){header.textContent=p.player;activateProfile(overlay);NSTData.ready(p,body,()=>{if(location.hash===target)openPlayerModal(pName);});return;}
      delete body.dataset.loadKey;
      const badgeClass = !p.is_active ? 'badge-inactive' : (p.league === 'Высшая' ? 'badge-premier' : (p.league === 'Средняя' ? 'badge-middle' : 'badge-yard'));
      const sBadge = p.status_badge || (p.is_active ? 'Активен' : 'Зал славы');
      const vkLink = p.vk_domain ? `https://vk.ru/${p.vk_domain}` : (p.vk_id ? `https://vk.ru/id${p.vk_id}` : null);

      header.innerHTML = `
        <img src="${escapeHTML(p.avatar)}" class="modal-avatar-big" onerror="this.onerror=null;this.style.visibility='hidden'">
        <div class="modal-title-box">
          <h2>${escapeHTML(p.player)}</h2>
          ${p.vk_name && p.vk_name !== p.player ? `
            <div style="font-size: 13px; color: #94a3b8; font-weight: 600; margin-top: 2px;">
              ВКонтакте: ${escapeHTML(p.vk_name)}
            </div>
          ` : ''}
          ${p.quote ? `
            <div style="font-size: 12px; color: #f8fafc; font-style: italic; margin-top: 6px; background: rgba(0,0,0,0.4); border-left: 3px solid var(--nes-gold); padding: 6px 10px; border-radius: 2px; line-height: 1.4; max-width: 650px; white-space: pre-line;">
              «${escapeHTML(p.quote)}»
            </div>
          ` : ''}
          
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 8px;">
            <span class="league-badge ${badgeClass}">${escapeHTML(p.league)} лига</span>
            <span style="font-size: 12px; font-weight: 800; color: ${p.is_active ? '#22c55e' : '#cbd5e1'};">● ${escapeHTML(sBadge)}</span>
            ${p.medals && (p.medals.gold + p.medals.silver + p.medals.bronze) > 0 ? `
              <span style="font-size: 11px; font-weight: 800; background: rgba(255, 183, 3, 0.15); border: 1px solid var(--nes-gold); color: #fff; padding: 2px 8px; border-radius: 3px;">
                🏆 ${p.medals.gold}🥇 ${p.medals.silver}🥈 ${p.medals.bronze}🥉
              </span>
            ` : ''}
            ${vkLink ? `
              <a href="${escapeHTML(vkLink)}" target="_blank" class="vk-btn" title="Перейти на страницу ${escapeHTML(p.vk_name || p.player)} ВКонтакте">
                <svg viewBox="0 0 24 24"><path d="M13.162 18.994c.609 0 .858-.406.851-.915-.072-1.747.785-2.28 1.488-2.28.618 0 1.344.428 1.84 1.157.734 1.077 1.258 2.038 2.378 2.038h2.096c1.196 0 1.776-.566 1.442-1.637-.367-1.182-1.603-2.678-2.327-3.486-.554-.62-1.127-1.185-.758-2.02.478-1.076 1.947-3.212 2.27-4.472.167-.655-.178-1.077-.92-1.077h-2.122c-.663 0-.964.332-1.151.78-.445 1.066-1.57 3.327-2.247 3.993-.342.338-.598.24-.76-.085-.298-.596-.341-1.688-.341-2.585 0-2.316.357-3.327-.723-3.582-.437-.103-.984-.132-1.792-.132-1.644 0-2.73.045-3.385.733-.257.27-.37.604-.15.632.493.064.935.318 1.054.945.362 1.905.176 3.655-.66 4.31-.383.298-.828.188-1.156-.214-.943-1.156-1.89-3.39-2.518-5.011-.194-.502-.519-.884-1.139-.884H2.477c-.779 0-.946.368-.946.779 0 .73.945 4.354 4.394 9.176 2.302 3.228 5.568 4.976 8.528 4.976z"/></svg>
                <span>${escapeHTML(p.vk_name && p.vk_name !== p.player ? p.vk_name : 'Профиль ВКонтакте')} ↗</span>
              </a>
            ` : ''}
          </div>

          <!-- Dossier Cards Row -->
          <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px;">
            ${p.kryptonite ? `
              <div style="background: rgba(220, 38, 38, 0.15); border: 1px solid #ef4444; padding: 4px 8px; border-radius: 2px; font-size: 11px; cursor: pointer;" onclick="openPlayerModal('${p.kryptonite.name}')" title="Худший процент побед при 3+ матчах">
                <span style="color: #fca5a5; font-weight: 700;">☠️ Криптонит:</span> <strong>${p.kryptonite.name}</strong> <span style="color: #fca5a5;">(${p.kryptonite.wr}%)</span>
              </div>
            ` : ''}
            ${p.favorite_client ? `
              <div style="background: rgba(34, 197, 94, 0.15); border: 1px solid #22c55e; padding: 4px 8px; border-radius: 2px; font-size: 11px; cursor: pointer;" onclick="openPlayerModal('${p.favorite_client.name}')" title="Лучший процент побед при 3+ матчах">
                <span style="color: #86efac; font-weight: 700;">🎯 Клиент:</span> <strong>${p.favorite_client.name}</strong> <span style="color: #86efac;">(${p.favorite_client.wr}%)</span>
              </div>
            ` : ''}
            ${p.spectacle > 0 ? `
              <div style="background: rgba(0, 229, 255, 0.1); border: 1px solid var(--nes-cyan); padding: 4px 8px; border-radius: 2px; font-size: 11px;">
                <span style="color: var(--nes-cyan); font-weight: 700;">🌪️ Зрелищность:</span> <strong>${p.spectacle}</strong> гол/матч
              </div>
            ` : ''}
          </div>
        </div>
      `;

      // Match categories breakdown
      const mHistory = p.match_history || [];
      const catCounts = {
        all: mHistory.length,
        season: mHistory.filter(m => m.category === 'season').length,
        team: mHistory.filter(m => m.category === 'team').length,
        club: mHistory.filter(m => m.category === 'club').length,
        penalty: mHistory.filter(m => m.category === 'penalty').length,
        special: mHistory.filter(m => m.category === 'special' || m.category === 'blitz' || m.category === 'youth').length,
      };

      const filterButtonsHtml = `
        <div class="modal-match-filters" style="display: flex; gap: 6px; flex-wrap: wrap; margin: 12px 0 14px 0;">
          <button class="filter-btn active" onclick="filterPlayerModalMatches('all', this)">⚽ Все турниры (${catCounts.all})</button>
          ${catCounts.season > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('season', this)">🏆 Регулярные сезоны 1–9 (${catCounts.season})</button>` : ''}
          ${catCounts.team > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('team', this)">👥 Командные 2х2 (${catCounts.team})</button>` : ''}
          ${catCounts.club > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('club', this)">🏖️ Клубные & Межсезонье (${catCounts.club})</button>` : ''}
          ${catCounts.penalty > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('penalty', this)">🥅 Пенальти (${catCounts.penalty})</button>` : ''}
          ${catCounts.special > 0 ? `<button class="filter-btn" onclick="filterPlayerModalMatches('special', this)">⚡ Блицы & Соло (${catCounts.special})</button>` : ''}
        </div>
      `;

      const matchesRows = mHistory.map(m => {
        const resClass = m.result === 'ПОБЕДА' ? 'res-win' : (m.result === 'ПОРАЖЕНИЕ' ? 'res-loss' : 'res-draw');
        const oppObj = DATA.profiles.find(x => x.player.toLowerCase() === m.opponent.toLowerCase());
        const oppAvatar = oppObj ? oppObj.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${escapeHTML(m.opponent)}`;

        let catClass = 'badge-premier';
        if (m.category === 'team') catClass = 'badge-middle';
        else if (m.category === 'club') catClass = 'tag-offseason';
        else if (m.category === 'penalty') catClass = 'tag-penalty';
        else if (m.category === 'special' || m.category === 'blitz') catClass = 'tag-blitz';

        const isWin = m.score_for > m.score_against;
        const isLoss = m.score_for < m.score_against;

        return `
          <div class="match-history-row" data-cat="${escapeHTML(m.category || 'season')}">
            <!-- Tournament Info & Stage -->
            <div class="mhr-meta">
              <span class="mhr-badge ${catClass}" title="${escapeHTML(m.tournament || m.season)}">
                ${escapeHTML(m.cat_label || m.season)}
              </span>
              <span class="mhr-stage">
                ${escapeHTML(m.stage || m.tour || '')}
              </span>
            </div>

            <!-- Result Badge -->
            <div class="mhr-result">
              <span class="res-badge ${resClass}" style="${m.is_technical ? 'background: rgba(239, 68, 68, 0.25); border: 1px solid #ef4444; color: #fca5a5;' : ''}">${m.result}</span>
            </div>

            <!-- Face-to-Face Scoreboard -->
            <div class="mhr-duel">
              <!-- Home Player -->
              <div class="mhr-player mhr-home">
                <span class="mhr-name ${isWin ? 'mhr-winner' : ''}">${escapeHTML(p.player)}${m.partner ? ` <small style="color: #94a3b8;">& ${escapeHTML(m.partner)}</small>` : ''}</span>
                <img src="${escapeHTML(p.avatar)}" class="mhr-avatar" onerror="this.onerror=null;this.style.visibility='hidden'">
              </div>

              <!-- Score Box -->
              <div class="mhr-score-box">
                <span class="mhr-score-num ${isWin ? 'mhr-score-win' : (isLoss ? 'mhr-score-loss' : '')}">${m.score_for}</span>
                <span class="mhr-score-divider">:</span>
                <span class="mhr-score-num ${isLoss ? 'mhr-score-win' : (isWin ? 'mhr-score-loss' : '')}">${m.score_against}</span>
                ${m.pk ? '<span class="ot-tag ot-purple" title="Пенальти">ПЕН</span>' : (m.ot ? '<span class="ot-tag ot-gold" title="Овертайм">ОТ</span>' : '')}
              </div>

              <!-- Away Opponent -->
              <div class="mhr-player mhr-away" data-profile-name="${escapeHTML(m.opponent)}" role="button" tabindex="0" title="Открыть профиль ${escapeHTML(m.opponent)}">
                <img src="${escapeHTML(oppAvatar)}" class="mhr-avatar" onerror="this.onerror=null;this.style.visibility='hidden'">
                <span class="mhr-name ${isLoss ? 'mhr-winner' : ''}">${escapeHTML(m.opponent)}</span>
              </div>
            </div>
          </div>
        `;
      }).join('');

      // Calculate top opponents for this player
      const oppMap = {};
      mHistory.forEach(m => {
        if (m.is_technical) return;
        const oppName = m.opponent;
        if (!oppName) return;
        if (!oppMap[oppName]) {
          oppMap[oppName] = { name: oppName, matches: 0, wins: 0, losses: 0, draws: 0, gf: 0, ga: 0 };
        }
        oppMap[oppName].matches += 1;
        oppMap[oppName].gf += m.score_for;
        oppMap[oppName].ga += m.score_against;
        if (m.result === 'ПОБЕДА') oppMap[oppName].wins += 1;
        else if (m.result === 'ПОРАЖЕНИЕ') oppMap[oppName].losses += 1;
        else oppMap[oppName].draws += 1;
      });

      const topOpponents = Object.values(oppMap).sort((a, b) => b.matches - a.matches).slice(0, 6);
      const topOppHtml = topOpponents.map(opp => {
        const oppProf = DATA.profiles.find(x => x.player.toLowerCase() === opp.name.toLowerCase());
        const oppAv = oppProf ? oppProf.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${escapeHTML(opp.name)}`;
        return `
          <div style="background: rgba(10, 27, 45, 0.8); border: 1px solid rgba(255,255,255,0.25); padding: 8px 12px; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="openPlayerModal('${escapeHTML(opp.name)}')" title="Открыть анкету ${escapeHTML(opp.name)}">
              <img src="${oppAv}" style="width: 28px; height: 28px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${escapeHTML(opp.name)}'">
              <span style="font-weight: 700; font-size: 13px; color: #fff;">${escapeHTML(opp.name)}</span>
            </div>
            <div style="font-size: 12px; text-align: right;">
              <span style="color: var(--nes-green); font-weight: 800;">${opp.wins}В</span>
              <span style="color: #94a3b8;"> - </span>
              <span style="color: var(--nes-red); font-weight: 800;">${opp.losses}П</span>
              <span style="color: #94a3b8; font-size: 11px; margin-left: 4px;">(${opp.matches} игр)</span>
            </div>
          </div>
        `;
      }).join('');

      body.innerHTML = `
        ${!p.is_active && p.hof_reason ? `
          <div style="background: rgba(255, 183, 3, 0.12); border: 2px solid var(--nes-gold); padding: 14px 18px; margin-bottom: 20px; box-shadow: 3px 3px 0px #000;">
            <div style="display: flex; align-items: center; gap: 8px; font-family: var(--font-title); font-size: 13px; color: var(--nes-gold); margin-bottom: 6px;">
              <span>🏛️</span> В ЗАЛЕ СЛАВЫ NEKKETSU LEAGUE &bull; ОБОСНОВАНИЕ И ЗАСЛУГИ:
            </div>
            <div style="font-size: 14px; color: #fff; line-height: 1.5;">
              ${escapeHTML(p.hof_reason)}
            </div>
          </div>
        ` : ''}
        <div class="metric-tiles">
          <div class="metric-tile">
            <div class="l">Текущий рейтинг</div>
            <div class="num" style="color: var(--nes-gold);">${formatElo(p.active_elo)}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Рекорд рейтинга</div>
            <div class="num">${formatElo(p.peak_elo)}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Штраф за простой</div>
            <div class="num" style="color: ${p.decay_penalty > 0 ? 'var(--nes-red)' : 'var(--nes-green)'};">${p.decay_penalty > 0 ? `-${p.decay_penalty} очков` : '—'}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Всего матчей</div>
            <div class="num">${p.matches}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Победы / Поражения</div>
            <div class="num">${p.wins} из ${p.matches}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Процент побед</div>
            <div class="num" style="color: var(--nes-green);">${p.win_rate}%</div>
          </div>
          <div class="metric-tile">
            <div class="l">Забито / Пропущено</div>
            <div class="num">${p.goals_for} : ${p.goals_against}</div>
          </div>
          <div class="metric-tile">
            <div class="l">Игры всухую (на ноль)</div>
            <div class="num">${p.clean_sheets}</div>
          </div>
        </div>

        <div class="block-header">🎯 Как побеждает игрок (распределение по времени матча)</div>
        <div style="background: #0a1b2d; border: 2px solid rgba(255,255,255,0.25); padding: 14px; margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
            <span>В основное время: <strong style="color: var(--nes-cyan);">${p.reg_wins} побед</strong></span>
            <span>В овертаймах: <strong style="color: var(--nes-gold);">${p.ot_wins} побед</strong></span>
            <span>По пенальти: <strong style="color: #c084fc;">${p.pk_wins} побед</strong></span>
            <span>Побед в овертаймах/пенальти: <strong style="color: var(--nes-green);">${p.clutch_win_rate}%</strong> (${p.clutch_wins} из ${p.clutch_total})</span>
          </div>
          <div style="display: flex; height: 16px; border: 1px solid #fff; background: #000;">
            <div style="width: ${p.wins > 0 ? (p.reg_wins/p.wins*100) : 0}%; background: var(--nes-cyan);" title="Основное время"></div>
            <div style="width: ${p.wins > 0 ? (p.ot_wins/p.wins*100) : 0}%; background: var(--nes-gold);" title="Овертаймы"></div>
            <div style="width: ${p.wins > 0 ? (p.pk_wins/p.wins*100) : 0}%; background: #c084fc;" title="Пенальти"></div>
          </div>
        </div>

        ${topOppHtml ? `
          <div class="block-header">⚔️ Главные соперники игрока (Личные встречи)</div>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 8px; margin-bottom: 20px;">
            ${topOppHtml}
          </div>
        ` : ''}

        <div class="block-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
          <span>📜 Официальные протоколы матчей игрока (${mHistory.length} игр в базе)</span>
        </div>
        ${filterButtonsHtml}
        <div id="modalMatchesContainer">
          ${matchesRows || '<p style="color: #94a3b8; padding: 12px;">Протоколы матчей отсутствуют</p>'}
        </div>
      `;

      activateProfile(overlay);
    }

    function filterPlayerModalMatches(cat, btn) {
      document.querySelectorAll('.modal-match-filters .filter-btn').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');

      const rows = document.querySelectorAll('#modalMatchesContainer .match-history-row[data-cat]');
      rows.forEach(r => {
        const rCat = r.getAttribute('data-cat');
        if (cat === 'all') {
          r.style.display = 'flex';
        } else if (cat === 'special') {
          r.style.display = (rCat === 'special' || rCat === 'blitz' || rCat === 'youth') ? 'flex' : 'none';
        } else {
          r.style.display = (rCat === cat) ? 'flex' : 'none';
        }
      });
    }

    
    // ==============================================================================
    // MODAL HELPERS & PROTOCOL VIEWER (ВК ОТЧЁТЫ И ВИДЕО)
    // ==============================================================================
    const PROTOCOLS_STORE = {};
    let protocolNextId = 1;

    function registerProtocol(title, text, date, page, url) {
      const id = 'proto_' + (protocolNextId++);
      PROTOCOLS_STORE[id] = { title, text, date, page, url };
      return id;
    }

    function openProtocolModalById(id) {
      const p = PROTOCOLS_STORE[id];
      if (!p) return;
      const modal = document.getElementById('protocolModal');
      if (!modal) return;
      const t = document.getElementById('protocolModalTitle');
      const d = document.getElementById('protocolModalDate');
      const pg = document.getElementById('protocolModalPage');
      const txt = document.getElementById('protocolModalText');
      const vk = document.getElementById('protocolModalVkLink');

      if (t) t.textContent = p.title || 'Протокол матча из ВК';
      if (d) d.textContent = p.date ? `📅 ${p.date}` : '';
      if (pg) pg.textContent = p.page ? `📄 Лист: ${p.page}` : '';
      if (txt) txt.textContent = p.text || 'Текст отчёта отсутствует.';
      if (vk) {
        if (p.url) {
          vk.href = p.url;
          vk.style.display = 'inline-flex';
        } else {
          vk.style.display = 'none';
        }
      }
      modal.style.display = 'flex';
    }

    function closeProtocolModal(e) {
      if (e && e.target && e.target !== e.currentTarget && !e.target.classList.contains('modal-close')) return;
      const modal = document.getElementById('protocolModal');
      if (modal) modal.style.display = 'none';
    }

    function openVideoModal(url, title = 'Запись матча') {
      const modal = document.getElementById('videoModal');
      const iframe = document.getElementById('videoPlayerIframe');
      const titleEl = document.getElementById('videoModalTitle');
      const extLink = document.getElementById('videoModalExternalLink');
      if (!modal || !iframe) return;

      if (titleEl) titleEl.textContent = title;
      if (extLink) extLink.href = url;

      let embedUrl = url;
      if (url.includes('youtube.com/watch?v=' || url.includes('youtube.com/watch?'))) {
        const m = url.match(/v=([a-zA-Z0-9_-]+)/);
        if (m) embedUrl = `https://www.youtube.com/embed/${m[1]}?autoplay=1`;
      } else if (url.includes('youtu.be/')) {
        const m = url.match(/youtu\.be\/([a-zA-Z0-9_-]+)/);
        if (m) embedUrl = `https://www.youtube.com/embed/${m[1]}?autoplay=1`;
      } else if (url.includes('vk.com/video') || url.includes('vk.ru/video')) {
        const m = url.match(/video(-?\d+)_(\d+)/);
        if (m) embedUrl = `https://vk.ru/video_ext.php?oid=${m[1]}&id=${m[2]}&hash=`;
      }

      iframe.src = embedUrl;
      modal.style.display = 'flex';
    }

    function closeVideoModal(e) {
      if (e && e.target && e.target !== e.currentTarget && !e.target.classList.contains('modal-close')) return;
      const modal = document.getElementById('videoModal');
      const iframe = document.getElementById('videoPlayerIframe');
      if (iframe) iframe.src = '';
      if (modal) modal.style.display = 'none';
    }

    function closePlayerModal(event) {
      if (event && event.target !== event.currentTarget) return;
      hidePlayerModal();
      history.replaceState(null, '', profileReturn);
      handleRouting();
    }
    document.addEventListener('click', event => {
      const target = event.target.closest('[data-profile-name]');
      if (target) openPlayerModal(target.dataset.profileName);
    });
    document.addEventListener('keydown', event => {
      if ((event.key === 'Enter' || event.key === ' ') && event.target.matches('[data-profile-name]')) {
        event.preventDefault(); openPlayerModal(event.target.dataset.profileName); return;
      }
      const overlay = document.getElementById('playerModal');
      if (!overlay || !overlay.classList.contains('active')) return;
      if (event.key === 'Escape') { event.preventDefault(); closePlayerModal(); }
      if (event.key === 'Tab') {
        const items = [...overlay.querySelectorAll('button, a[href], input, select, [tabindex="0"]')].filter(el => !el.disabled && el.getClientRects().length);
        if (!items.length) return;
        const first = items[0], last = items[items.length-1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });

    // Seasons Module

    function renderSeasonsBar() {

      const bar = document.getElementById('seasonsBar');

      if (!bar) return;

      bar.innerHTML = DATA.seasons.map(s => `

        <button class="filter-btn season-tab-btn ${s.id === selectedSeasonId ? 'active' : ''}" onclick="selectSeason('${s.id}')">

          ${s.name} (${s.year} г.)

        </button>

      `).join('');

    }



    function selectSeason(sId, updateRoute = true) {
      if (!DATA.seasons.some(s => String(s.id) === String(sId))) return;
      if (updateRoute && window.location.hash !== "#/season/" + sId) history.pushState(null, "", "#/season/" + sId);

      selectedSeasonId = sId;

      seasonPlayerFilter = 'all';

      seasonLeagueFilter = 'all';

      renderSeasonsBar();

      renderSeasonDetails(sId);

    }



    function switchSeasonSubTab(st) {
      clearMatchAddress();

      seasonSubTab = st;

      renderSeasonDetails(selectedSeasonId);

    }



    function setPlayoffViewMode(mode) {

      playoffViewMode = mode;

      renderSeasonDetails(selectedSeasonId);

    }

    function setTeamPlayoffViewMode(mode) {
      teamPlayoffViewMode = mode;
      renderTeamTournamentDetails();
    }

    function setSpecialPlayoffViewMode(mode) {
      specialPlayoffViewMode = mode;
      renderSpecialTournamentDetails();
    }



    function filterSeasonPlayer(pName) {
      clearMatchAddress();

      seasonPlayerFilter = pName;

      renderSeasonDetails(selectedSeasonId);

    }



    function filterSeasonLeague(leg) {
      clearMatchAddress();

      seasonLeagueFilter = leg;

      renderSeasonDetails(selectedSeasonId);

    }



    function getPlayerSeasonLeague(sId, playerName) {

      const pLow = playerName.toLowerCase().trim();

      const roster = (DATA.season_rosters && (DATA.season_rosters[sId] || DATA.season_rosters[String(sId)])) || {};

      for (const [leagueName, players] of Object.entries(roster)) {

        if (players.some(x => x.toLowerCase().trim() === pLow)) {

          return leagueName;

        }

      }

      const s = DATA.seasons && DATA.seasons.find(x => String(x.id) === String(sId));

      if (s && s.matches) {

        const mWithLeague = s.matches.find(m => (m.p1.toLowerCase() === pLow || m.p2.toLowerCase() === pLow) && m.league && !m.league.toLowerCase().includes('кубок'));

        if (mWithLeague && mWithLeague.league) return mWithLeague.league;

      }

      const prof = DATA.profiles.find(x => x.player.toLowerCase() === pLow);

      if (prof) {

        if (prof.league === 'Высшая') return 'Высшая лига';

        if (prof.league === 'Средняя') return 'Средняя лига';

        if (prof.league === 'Дворовая') return 'Дворовая лига';

      }

      return 'Высшая лига';

    }



    function renderSeasonDetails(sId) {

      const s = DATA.seasons.find(x => String(x.id) === String(sId));

      if (!s) return;



      const card = document.getElementById('seasonDetails');

      if (!card) return;
      if(!NSTData.ready(s,card,()=>renderSeasonDetails(selectedSeasonId)))return;
      viewAddress('season',sId);



      // Calculate participant stats for this season

      const partMap = {};

      (s.matches || []).forEach(m => {

        [m.p1, m.p2].forEach(pName => {

          if (!pName) return;

          if (!partMap[pName]) {

            const prof = DATA.profiles.find(x => x.player.toLowerCase() === pName.toLowerCase());

            partMap[pName] = {

              name: pName,

              avatar: prof ? prof.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pName}`,

              matches: 0,

              wins: 0,

              losses: 0,

              goals_for: 0,

              goals_against: 0

            };

          }

        });



        if (partMap[m.p1] && partMap[m.p2]) {

          partMap[m.p1].matches += 1;

          partMap[m.p2].matches += 1;

          partMap[m.p1].goals_for += m.s1;

          partMap[m.p1].goals_against += m.s2;

          partMap[m.p2].goals_for += m.s2;

          partMap[m.p2].goals_against += m.s1;



          if (m.s1 > m.s2) {

            partMap[m.p1].wins += 1;

            partMap[m.p2].losses += 1;

          } else if (m.s2 > m.s1) {

            partMap[m.p2].wins += 1;

            partMap[m.p1].losses += 1;

          }

        }

      });



      const participantsList = Object.values(partMap).sort((a, b) => {

        if (b.wins !== a.wins) return b.wins - a.wins;

        const gdB = b.goals_for - b.goals_against;

        const gdA = a.goals_for - a.goals_against;

        if (gdB !== gdA) return gdB - gdA;

        return b.matches - a.matches;

      });



      // Group participants by league

      const leagueGroups = {};

      participantsList.forEach(p => {

        const leg = getPlayerSeasonLeague(sId, p.name);

        if (!leagueGroups[leg]) leagueGroups[leg] = [];

        leagueGroups[leg].push(p);

      });



      const leagueOrder = ["Высшая лига", "Высшая (Единая) лига", "Средняя лига", "Младшая лига", "Дворовая лига"];

      const sortedLeagues = Object.keys(leagueGroups).sort((a, b) => {

        const idxA = leagueOrder.indexOf(a) !== -1 ? leagueOrder.indexOf(a) : 99;

        const idxB = leagueOrder.indexOf(b) !== -1 ? leagueOrder.indexOf(b) : 99;

        return idxA - idxB;

      });



      // Master players chips

      const masterSeasonPlayers = participantsList.filter(p => DATA.profiles.some(x => x.player.toLowerCase() === p.name.toLowerCase()));

      const playersChips = masterSeasonPlayers.map(p => `

        <span class="player-chip-link" onclick="openPlayerModal('${p.name}')" title="Открыть анкету ${p.name}">

          <img src="${p.avatar}" style="width: 16px; height: 16px; border-radius: 2px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.name}'">

          ${p.name}

        </span>

      `).join('');



      // Build Sub-Tab content

      let subContentHtml = '';



      // 1. ALL MATCHES SUB-TAB

      if (seasonSubTab === 'matches') {

        let filteredMatches = s.matches || [];

        if (seasonPlayerFilter && seasonPlayerFilter !== 'all') {

          filteredMatches = filteredMatches.filter(m =>

            m.p1.toLowerCase() === seasonPlayerFilter.toLowerCase() ||

            m.p2.toLowerCase() === seasonPlayerFilter.toLowerCase()

          );

        }

        if (seasonLeagueFilter && seasonLeagueFilter !== 'all') {

          filteredMatches = filteredMatches.filter(m => m.league === seasonLeagueFilter);

        }



        const playerOptions = participantsList.map(p => `

          <option value="${p.name}" ${seasonPlayerFilter === p.name ? 'selected' : ''}>${p.name}</option>

        `).join('');



        const leagueOrder = ["Высшая лига", "Высшая (Единая) лига", "Средняя лига", "Младшая лига", "Дворовая лига", "Кубок лиг"];

        const matchLeagues = Array.from(new Set((s.matches || []).map(m => m.league).filter(Boolean)));

        matchLeagues.sort((a, b) => {

          const idxA = leagueOrder.indexOf(a) !== -1 ? leagueOrder.indexOf(a) : 99;

          const idxB = leagueOrder.indexOf(b) !== -1 ? leagueOrder.indexOf(b) : 99;

          return idxA - idxB;

        });



        const leagueOptions = matchLeagues.map(l => `

          <option value="${l}" ${seasonLeagueFilter === l ? 'selected' : ''}>${l}</option>

        `).join('');



        const matchesListHtml = filteredMatches.length > 0 ? filteredMatches.map(m => {

          const p1Low = (m.p1 || '').toLowerCase();

          const p2Low = (m.p2 || '').toLowerCase();

          const prof1 = DATA.profiles.find(x => x.player.toLowerCase() === p1Low);

          const prof2 = DATA.profiles.find(x => x.player.toLowerCase() === p2Low);

          const av1 = prof1 ? prof1.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.p1}`;

          const av2 = prof2 ? prof2.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${m.p2}`;

          const isP1Win = m.s1 > m.s2;

          const isP2Win = m.s2 > m.s1;

          const sMatchTitle = `${m.p1} vs ${m.p2} (${m.s1}:${m.s2}) • ${s.name}`;

          const protoId = m.vk_url ? registerProtocol(sMatchTitle, m.vk_text, m.vk_date, m.vk_page, m.vk_url) : '';



          return `

            <div class="h2h-match-item" data-match-anchor="${m._anchor||''}" style="padding: 12px 16px; margin-bottom: 8px;">

              <div style="display: flex; align-items: center; gap: 8px; flex: 1.2; min-width: 140px;">

                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--nes-gold); font-weight: 800; min-width: 60px;">

                  ${m.tour || 'Матч'}

                </span>

                <span class="league-badge ${m.league && m.league.includes('Высшая') ? 'badge-premier' : (m.league && m.league.includes('Средняя') ? 'badge-middle' : (m.league && m.league.includes('Кубок') ? 'badge-cup' : 'badge-yard'))}" style="font-size: 10px; padding: 2px 6px;">

                  ${m.league || 'Регулярка'}

                </span>

              </div>

              <div style="display: flex; align-items: center; justify-content: center; gap: 14px; flex: 2; flex-wrap: wrap;">

                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p1}')">

                  <span style="font-family: var(--font-title); font-size: 14px; ${isP1Win ? 'color: var(--nes-gold); font-weight: 800;' : 'color: #fff;'}; text-align: right;">${m.p1}</span>

                  <img src="${av1}" style="width: 24px; height: 24px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.p1}'">

                </div>

                <div class="score-badge" style="font-size: 15px; padding: 5px 14px; letter-spacing: 1px; font-weight: 900; color: var(--nes-cyan); min-width: 80px; text-align: center;">

                  ${m.s1} : ${m.s2}

                  ${m.is_technical ? '<span class="ot-tag" style="background: rgba(239, 68, 68, 0.25); border: 1px solid #ef4444; color: #fca5a5; font-size: 10px; padding: 2px 6px; font-weight: 800;" title="Техническое поражение (снят с турнира)">⚡ ТП (СНЯТ)</span>' : (m.pk ? '<span class="ot-tag ot-purple">Пенальти</span>' : (m.ot ? '<span class="ot-tag ot-gold">ОТ</span>' : ''))}

                </div>

                <div style="display: flex; align-items: center; justify-content: flex-start; gap: 8px; flex: 1; cursor: pointer;" onclick="openPlayerModal('${m.p2}')">

                  <img src="${av2}" style="width: 24px; height: 24px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.p2}'">

                  <span style="font-family: var(--font-title); font-size: 14px; ${isP2Win ? 'color: var(--nes-gold); font-weight: 800;' : 'color: #cbd5e1;'}; text-align: left;">${m.p2}</span>

                </div>

              </div>

              ${(m.vk_url || m.video_url) ? `

                <div style="display: flex; gap: 6px; align-items: center; justify-content: flex-end; min-width: 140px; margin-left: auto;">

                  ${m.vk_url ? `

                    <button type="button" class="source-btn-vk" onclick="event.stopPropagation(); openProtocolModalById('${protoId}')" title="Посмотреть текст отчёта матча из ВК">

                      💬 ВК

                    </button>

                  ` : ''}

                  ${m.video_url ? (

                    (m.video_url.includes('youtube.com') || m.video_url.includes('youtu.be')) ? `

                      <a href="${m.video_url}" target="_blank" rel="noopener" class="source-btn-video" title="Смотреть на YouTube в новой вкладке">

                        🎬 YouTube ↗

                      </a>

                    ` : `

                      <button type="button" class="source-btn-video" onclick="event.stopPropagation(); openVideoModal('${m.video_url}', '${sMatchTitle.replace(/'/g, "\'")}')" title="Смотреть в плеере на сайте">

                        🎬 Видео

                      </button>

                    `

                  ) : ''}

                </div>

              ` : '<div style="min-width: 140px; margin-left: auto;"></div>'}

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

                📋 СЫГРАННЫЕ МАТЧИ (${filteredMatches.length} из ${(s.matches || []).length}):

              </div>

              <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">

                ${matchLeagues.length > 1 ? `

                  <div style="display: flex; align-items: center; gap: 6px;">

                    <span style="font-size: 12px; color: #94a3b8; font-weight: 700;">Лига:</span>

                    <select class="clean-search" style="padding: 4px 10px; font-size: 12px;" onchange="filterSeasonLeague(this.value)">

                      <option value="all" ${seasonLeagueFilter === 'all' ? 'selected' : ''}>▶ Все лиги (${matchLeagues.length})</option>

                      ${leagueOptions}

                    </select>

                  </div>

                ` : ''}

                <div style="display: flex; align-items: center; gap: 6px;">

                  <span style="font-size: 12px; color: #94a3b8; font-weight: 700;">Игрок:</span>

                  <select class="clean-search" style="padding: 4px 10px; font-size: 12px;" onchange="filterSeasonPlayer(this.value)">

                    <option value="all" ${seasonPlayerFilter === 'all' ? 'selected' : ''}>▶ Все участники (${participantsList.length})</option>

                    ${playerOptions}

                  </select>

                </div>

              </div>

            </div>

            <div>

              ${matchesListHtml}

            </div>

          </div>

        `;

      }



      // 2. TABLES SUB-TAB

      else if (seasonSubTab === 'tables') {

        let tablesHtml = '<div style="display: flex; flex-direction: column; gap: 20px;">';

        // Exclude Cup / Playoff from regular round-robin standings tables
        const regularLeagues = sortedLeagues.filter(l => !l.toLowerCase().includes('кубок'));

        regularLeagues.forEach(leg => {

          const legMatches = (s.matches || []).filter(m => (m.league || '').toLowerCase() === leg.toLowerCase());

          const rosterPlayers = (DATA.season_rosters && (DATA.season_rosters[sId] || DATA.season_rosters[String(sId)]) && (DATA.season_rosters[sId] || DATA.season_rosters[String(sId)])[leg]) || [];

          const playerSet = new Set(rosterPlayers);

          legMatches.forEach(m => {

            if (m.p1) playerSet.add(m.p1);

            if (m.p2) playerSet.add(m.p2);

          });



          const pStats = Array.from(playerSet).map(pName => {

            const prof = DATA.profiles.find(x => x.player.toLowerCase() === pName.toLowerCase());

            const stat = {

              name: pName,

              avatar: prof ? prof.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pName}`,

              matches: 0, wins: 0, losses: 0, goals_for: 0, goals_against: 0

            };

            const pLow = pName.toLowerCase();

            legMatches.forEach(m => {

              const p1Low = (m.p1 || '').toLowerCase();

              const p2Low = (m.p2 || '').toLowerCase();

              const won = matchWinnerSide(m);

              if (p1Low === pLow) {

                stat.matches += 1;

                stat.goals_for += m.s1;

                stat.goals_against += m.s2;

                if (won === 1) stat.wins += 1;

                else if (won === 2) stat.losses += 1;

              } else if (p2Low === pLow) {

                stat.matches += 1;

                stat.goals_for += m.s2;

                stat.goals_against += m.s1;

                if (won === 2) stat.wins += 1;

                else if (won === 1) stat.losses += 1;

              }

            });

            return stat;

          });



          // Sort table by wins, goal diff, goals for, matches
          pStats.sort((a, b) => {

            if (b.wins !== a.wins) return b.wins - a.wins;

            const gdB = b.goals_for - b.goals_against;

            const gdA = a.goals_for - a.goals_against;

            if (gdB !== gdA) return gdB - gdA;

            if (b.goals_for !== a.goals_for) return b.goals_for - a.goals_for;

            return b.matches - a.matches;

          });



          const badgeClass = leg.includes('Высшая') ? 'badge-premier' : (leg.includes('Средняя') ? 'badge-middle' : 'badge-yard');

          const icon = leg.includes('Высшая') ? '🥇 ' : (leg.includes('Средняя') ? '🥈 ' : (leg.includes('Младшая') ? '⚡ ' : '🥉 '));



          tablesHtml += `

            <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.15); padding: 16px;">

              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff;">

                  <span class="league-badge ${badgeClass}" style="margin-right: 8px;">${icon}${leg}</span>

                  (${pStats.length} участников)

                </div>

              </div>

              <table class="special-table">

                <thead>

                  <tr>

                    <th>#</th>

                    <th>Игрок</th>

                    <th>Матчей</th>

                    <th>Побед</th>

                    <th>Пораж.</th>

                    <th>Голы</th>

                    <th>+/-</th>

                    <th>Профиль</th>

                  </tr>

                </thead>

                <tbody>

                  ${pStats.map((p, idx) => {

                    const gd = p.goals_for - p.goals_against;

                    const gdStr = gd > 0 ? `+${gd}` : `${gd}`;

                    const gdColor = gd > 0 ? 'var(--nes-cyan)' : (gd < 0 ? '#f87171' : '#94a3b8');

                    const rankColor = idx === 0 ? 'var(--nes-gold)' : (idx === 1 ? '#cbd5e1' : (idx === 2 ? '#d97706' : '#94a3b8'));



                    return `

                      <tr>

                        <td style="font-weight: 800; color: ${rankColor}; font-family: var(--font-mono);">${idx + 1}</td>

                        <td>

                          <div style="display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="openPlayerModal('${p.name}')">

                            <img src="${p.avatar}" style="width: 20px; height: 20px; border-radius: 2px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p.name}'">

                            <span style="font-weight: 700; color: #fff;">${p.name}</span>

                          </div>

                        </td>

                        <td style="font-family: var(--font-mono);">${p.matches}</td>

                        <td style="font-family: var(--font-mono); color: var(--nes-green); font-weight: 800;">${p.wins}</td>

                        <td style="font-family: var(--font-mono); color: var(--nes-red); font-weight: 800;">${p.losses}</td>

                        <td style="font-family: var(--font-mono);">${p.goals_for}:${p.goals_against}</td>

                        <td style="font-family: var(--font-mono); color: ${gdColor};">${gdStr}</td>

                        <td>

                          <button class="part-prof-btn" onclick="openPlayerModal('${p.name}')" title="Открыть анкету игрока">↗</button>

                        </td>

                      </tr>

                    `;

                  }).join('')}

                </tbody>

              </table>

            </div>

          `;

        });

        tablesHtml += '</div>';



        subContentHtml = `

          <div style="margin-top: 16px;">

            <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold); margin-bottom: 12px;">

              🏆 ТУРНИРНЫЕ ТАБЛИЦЫ ДИВИЗИОНОВ:

            </div>

            ${tablesHtml}

          </div>

        `;

      }



      // 3. PLAYOFF SUB-TAB (INTERACTIVE TOURNAMENT BRACKET)

      else if (seasonSubTab === 'playoff') {

        const playoffMatches = (s.matches || []).filter(m => {

          const t = (m.tour || '').toLowerCase();

          const l = (m.league || '').toLowerCase();

          return t.includes('финал') || t.includes('1/') || t.includes('плей') || t.includes('playoff') || t.includes('кубок') || l.includes('кубок');

        });



        // Standard bracket round weighting

        const roundOrderDef = [

          { key: '1/16', label: '1/16 Финала', weight: 1 },

          { key: '1/8', label: '1/8 Финала', weight: 2 },

          { key: '1/4', label: '1/4 Финала', weight: 3 },

          { key: '1/2', label: 'Полуфинал', weight: 4 },

          { key: '3', label: 'За 3-е место', weight: 5 },

          { key: 'финал', label: 'Гранд-Финал', weight: 6 }

        ];



        function getRoundDef(rName) {

          const rLow = (rName || '').toLowerCase();

          for (const ro of roundOrderDef) {

            if (ro.key === 'финал') {

              if (rLow.includes('финал') && !rLow.includes('1/16') && !rLow.includes('1/8') && !rLow.includes('1/4') && !rLow.includes('1/2') && !rLow.includes('3')) {

                return ro;

              }

            } else if (rLow.includes(ro.key)) {

              return ro;

            }

          }

          return { key: rName, label: rName || 'Плей-офф', weight: 99 };

        }



        // Group matches into rounds

        const roundMap = {};

        playoffMatches.forEach(m => {

          const rDef = getRoundDef(m.tour || m.stage);

          if (!roundMap[rDef.label]) {

            roundMap[rDef.label] = { def: rDef, matches: [] };

          }

          roundMap[rDef.label].matches.push(m);

        });



        const sortedRounds = Object.values(roundMap).sort((a, b) => a.def.weight - b.def.weight);



        // Determine Champion

        let championName = (s.podium && s.podium.champion) ? s.podium.champion : null;

        const finalRound = sortedRounds.find(r => r.def.key === 'финал');

        if (!championName && finalRound && finalRound.matches.length > 0) {

          const fMatches = finalRound.matches;

          const p1 = fMatches[0].p1;

          const p2 = fMatches[0].p2;

          let p1w = 0, p2w = 0;

          fMatches.forEach(g => {

            if ((g.p1 === p1 && g.s1 > g.s2) || (g.p2 === p1 && g.s2 > g.s1)) p1w++;

            else if ((g.p1 === p2 && g.s1 > g.s2) || (g.p2 === p2 && g.s2 > g.s1)) p2w++;

          });

          championName = p1w > p2w ? p1 : (p2w > p1w ? p2 : p1);

        }

        const champProf = championName ? DATA.profiles.find(x => x.player.toLowerCase() === championName.toLowerCase()) : null;

        const champAvatar = champProf ? champProf.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${championName || 'champ'}`;



        // 1. VISUAL BRACKET HTML

        let visualBracketHtml = '';

        if (sortedRounds.length > 0) {

          let roundsHtml = '';

          sortedRounds.forEach(r => {

            // Group matches in this round into matchups (pairs)

            const matchups = {};

            r.matches.forEach(m => {

              const pairKey = [m.p1, m.p2].sort().join('__VS__');

              if (!matchups[pairKey]) matchups[pairKey] = [];

              matchups[pairKey].push(m);

            });



            let matchupCardsHtml = '';

            Object.entries(matchups).forEach(([pKey, games]) => {

              const [pA, pB] = pKey.split('__VS__');

              let pAw = 0, pBw = 0;

              let pAg = 0, pBg = 0;

              games.forEach(g => {

                const sA = g.p1 === pA ? g.s1 : g.s2;

                const sB = g.p1 === pA ? g.s2 : g.s1;

                pAg += sA;

                pBg += sB;

                if (sA > sB) pAw++;

                else if (sB > sA) pBw++;

              });



              let isAWinner = false, isBWinner = false;

              if (games.length === 1) {

                isAWinner = pAg > pBg;

                isBWinner = pBg > pAg;

              } else {

                isAWinner = pAw > pBw;

                isBWinner = pBw > pAw;

              }



              const profA = DATA.profiles.find(x => x.player.toLowerCase() === pA.toLowerCase());

              const profB = DATA.profiles.find(x => x.player.toLowerCase() === pB.toLowerCase());

              const avA = profA ? profA.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pA}`;

              const avB = profB ? profB.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pB}`;



              const scoreA = games.length === 1 ? pAg : pAw;

              const scoreB = games.length === 1 ? pBg : pBw;

              const isFinal = r.def.key === 'финал';



              // Detailed chips for series matches

              let chipsHtml = '';

              if (games.length > 1) {

                chipsHtml = `<div class="bracket-series-games">` + games.map((g, gIdx) => {

                  const sMatchTitle = `${g.p1} vs ${g.p2} (${g.s1}:${g.s2}) • ${s.name}`;

                  const protoId = g.vk_url ? registerProtocol(sMatchTitle, g.vk_text, g.vk_date, g.vk_page, g.vk_url) : '';

                  const otTag = g.pk ? ' (Пен)' : (g.ot ? ' (ОТ)' : '');

                  const clickAttr = protoId ? `onclick="event.stopPropagation(); openProtocolModalById('${protoId}')" title="Открыть отчёт матча ВК"` : '';

                  return `<span class="bracket-chip" ${clickAttr}>И${gIdx+1}: ${g.s1}:${g.s2}${otTag}</span>`;

                }).join('') + `</div>`;

              } else if (games[0].vk_url || games[0].video_url) {

                const g = games[0];

                const sMatchTitle = `${g.p1} vs ${g.p2} (${g.s1}:${g.s2}) • ${s.name}`;

                const protoId = g.vk_url ? registerProtocol(sMatchTitle, g.vk_text, g.vk_date, g.vk_page, g.vk_url) : '';

                chipsHtml = `<div class="bracket-series-games" style="justify-content: flex-end;">`;

                if (protoId) {

                  chipsHtml += `<button type="button" class="source-btn-vk" style="font-size: 10px; padding: 2px 6px;" onclick="event.stopPropagation(); openProtocolModalById('${protoId}')">💬 ВК</button>`;

                }

                if (g.video_url) {

                  chipsHtml += `<button type="button" class="source-btn-video" style="font-size: 10px; padding: 2px 6px;" onclick="event.stopPropagation(); openVideoModal('${g.video_url}', '${sMatchTitle.replace(/'/g, "'")}')">🎬 Видео</button>`;

                }

                chipsHtml += `</div>`;

              }



              const seriesLabel = games.length > 1 ? `СЕРИЯ ДО ${Math.max(pAw, pBw)} ПОБЕД (${games.length} игр)` : 'МАТЧ НА ВЫЛЕТ';



              matchupCardsHtml += `

                <div class="bracket-match-card ${isFinal ? 'is-final' : ''}" data-players="${pA.toLowerCase()},${pB.toLowerCase()}">

                  <div class="bracket-card-top">

                    <span>${seriesLabel}</span>

                    ${isFinal ? '<span style="color: var(--nes-gold);">🏆 ФИНАЛ</span>' : ''}

                  </div>

                  <div class="bracket-player-row ${isAWinner ? 'winner' : (isBWinner ? 'loser' : '')}" data-player="${pA}" onmouseenter="highlightPlayerBracketPath('${pA}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pA}')" title="Наведите или кликните, чтобы подсветить путь ${pA}">

                    <div class="bracket-p-info">

                      <img src="${avA}" class="bracket-p-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${pA}'">

                      <span class="bracket-p-name">${pA}</span>

                      ${isAWinner ? '<span style="font-size: 11px;">👑</span>' : ''}

                    </div>

                    <div class="bracket-score">${scoreA}</div>

                  </div>

                  <div class="bracket-player-row ${isBWinner ? 'winner' : (isAWinner ? 'loser' : '')}" data-player="${pB}" onmouseenter="highlightPlayerBracketPath('${pB}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pB}')" title="Наведите или кликните, чтобы подсветить путь ${pB}">

                    <div class="bracket-p-info">

                      <img src="${avB}" class="bracket-p-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${pB}'">

                      <span class="bracket-p-name">${pB}</span>

                      ${isBWinner ? '<span style="font-size: 11px;">👑</span>' : ''}

                    </div>

                    <div class="bracket-score">${scoreB}</div>

                  </div>

                  ${chipsHtml}

                </div>

              `;

            });



            roundsHtml += `

              <div class="bracket-round">

                <div class="bracket-round-header">${r.def.label} (${Object.keys(matchups).length})</div>

                <div class="bracket-matchups">

                  ${matchupCardsHtml}

                </div>

              </div>

            `;

          });



          // Champion Podium Card

          if (championName) {

            roundsHtml += `

              <div class="bracket-champion-round">

                <div class="bracket-round-header" style="border-color: var(--nes-gold); color: var(--nes-gold); box-shadow: 0 0 10px rgba(255,183,3,0.3);">🏆 ЧЕМПИОН</div>

                <div class="bracket-champion-box" data-player="${championName}">

                  <div style="font-size: 28px;">👑</div>

                  <img src="${champAvatar}" class="bracket-champ-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${championName}'">

                  <div class="bracket-champ-name" onclick="openPlayerModal('${championName}')">${championName}</div>

                  <div class="bracket-champ-sub">🥇 ОБЛАДАТЕЛЬ КУБКА</div>

                  <div style="font-size: 10px; color: var(--nes-cyan); margin-top: 4px; font-weight: 800;">${s.name}</div>

                </div>

              </div>

            `;

          }



          // Collect all unique participants in playoff
          const playoffParticipantSet = new Set();
          playoffMatches.forEach(m => {
            if (m.p1) playoffParticipantSet.add(m.p1);
            if (m.p2) playoffParticipantSet.add(m.p2);
          });
          const playoffParticipantsList = Array.from(playoffParticipantSet).sort();

          const playerPillsHtml = `
            <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 14px;">
              <span style="font-size: 11px; color: #94a3b8; font-weight: 700;">🔍 Сетка игрока:</span>
              <button type="button" class="bracket-player-pill" onclick="resetPlayerBracketPath()">Все пути</button>
              ${playoffParticipantsList.map(p => `
                <button type="button" class="bracket-player-pill" data-player="${p}" onmouseenter="highlightPlayerBracketPath('${p}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${p}')">
                  ${p}
                </button>
              `).join('')}
            </div>
          `;

          visualBracketHtml = `
            <div style="margin-top: 10px;">
              ${playerPillsHtml}
              <div id="bracketPathBanner" class="bracket-path-banner"><span style="color: #94a3b8;">💡 Наведите на любого игрока или нажмите, чтобы проследить его путь по сетке</span></div>
              <div class="bracket-wrapper" id="bracketWrapper">
                <svg id="bracketSvg" class="bracket-svg"></svg>
                <div class="bracket-container" id="bracketContainer">
                  ${roundsHtml}
                </div>
              </div>
            </div>
          `;

        }



        // 2. FLAT LIST HTML

        const flatListHtml = `

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; margin-top: 12px;">

            ${playoffMatches.map(m => {

              const sMatchTitle = `${m.p1} vs ${m.p2} (${m.s1}:${m.s2}) • ${s.name}`;

              const protoId = m.vk_url ? registerProtocol(sMatchTitle, m.vk_text, m.vk_date, m.vk_page, m.vk_url) : '';

              const isP1Win = m.s1 > m.s2;

              const isP2Win = m.s2 > m.s1;

              return `

                <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); padding: 12px 14px; display: flex; justify-content: space-between; align-items: center;">

                  <div style="flex: 1;">

                    <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">${m.tour || 'Плей-офф'}</div>

                    <div style="font-size: 13px; color: ${isP1Win ? 'var(--nes-gold)' : '#fff'}; font-weight: 800; margin-top: 3px; cursor: pointer;" onclick="openPlayerModal('${m.p1}')">${m.p1}</div>

                    <div style="font-size: 13px; color: ${isP2Win ? 'var(--nes-gold)' : '#94a3b8'}; font-weight: 700; cursor: pointer;" onclick="openPlayerModal('${m.p2}')">${m.p2}</div>

                  </div>

                  <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">

                    <div class="score-badge" style="font-size: 15px; padding: 4px 10px; font-weight: 900; color: var(--nes-cyan);">

                      ${m.s1} : ${m.s2}

                    </div>

                    ${protoId ? `

                      <button type="button" class="source-btn-vk" style="font-size: 9px; padding: 2px 6px;" onclick="event.stopPropagation(); openProtocolModalById('${protoId}')">💬 Отчёт</button>

                    ` : ''}

                  </div>

                </div>

              `;

            }).join('')}

          </div>

        `;



        subContentHtml = `

          <div style="margin-top: 16px;">

            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">

              <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold);">

                ⚡ СЕТКА ПЛЕЙ-ОФФ И ИТОГИ КУБКА:

              </div>

              ${playoffMatches.length > 0 ? `

                <div style="display: flex; gap: 6px;">

                  <button type="button" class="filter-btn ${playoffViewMode === 'bracket' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setPlayoffViewMode('bracket')">

                    ⚡ Турнирная сетка

                  </button>

                  <button type="button" class="filter-btn ${playoffViewMode === 'list' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setPlayoffViewMode('list')">

                    📋 Список всех игр (${playoffMatches.length})

                  </button>

                </div>

              ` : ''}

            </div>



            <!-- Key Season Highlights -->

            ${(s.highlights && s.highlights.length > 0) ? `

              <div style="background: rgba(255, 183, 3, 0.08); border: 1px solid var(--nes-gold); padding: 14px; margin-bottom: 16px;">

                <div style="font-family: var(--font-title); font-size: 12px; color: var(--nes-gold); margin-bottom: 8px;">🌟 ГЛАВНЫЕ СОБЫТИЯ СЕЗОНА:</div>

                <ul style="margin: 0; padding-left: 20px; color: #cbd5e1; font-size: 13px; line-height: 1.6;">

                  ${s.highlights.map(h => `<li>${h}</li>`).join('')}

                </ul>

              </div>

            ` : ''}



            ${playoffMatches.length > 0 ? (playoffViewMode === 'bracket' ? visualBracketHtml : flatListHtml) : `
              <div style="background: rgba(17, 24, 39, 0.85); border: 2px solid var(--nes-gold); padding: 28px 20px; text-align: center; box-shadow: 4px 4px 0 #000; margin-top: 14px;">
                <div style="font-size: 32px; margin-bottom: 8px;">🏛️ 👑</div>
                <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-gold); margin-bottom: 8px;">
                  ПЕРВЫЙ ИСТОРИЧЕСКИЙ СЕЗОН NST (2015 ГОД)
                </div>
                <div style="font-size: 13px; color: #cbd5e1; max-width: 650px; margin: 0 auto 16px auto; line-height: 1.6;">
                  Дебютный чемпионат лиги проводился по классической круговой системе в едином дивизионе. 
                  Титул безоговорочного первого Чемпиона завоевал <strong>mafuta</strong>. 
                  Кубковая стадия на выбывание (<strong>Кубок Лиг</strong>) была учреждена начиная со 2-го сезона.
                </div>
                <button type="button" class="filter-btn active" style="font-size: 12px; padding: 6px 16px;" onclick="switchSeasonSubTab('tables')">
                  🏆 Открыть итоговую таблицу 1-го сезона
                </button>
              </div>
            `}

          </div>

        `;

      }



      // 4. ABOUT SUB-TAB (DEEP CHRONICLES & VK LORE)

      else if (seasonSubTab === 'about') {

        const fullChronicleParas = (s.full_chronicle || s.summary || '').split(String.fromCharCode(10) + String.fromCharCode(10)).filter(Boolean);

        const keyEvents = s.key_events || s.highlights || [];

        const divSummary = s.divisions_summary || {};

        const wallQuotes = s.wall_quotes || [];

        const vkTopicUrl = s.topic_id ? `https://vk.ru/topic-66162180_${s.topic_id}` : null;

        const vkWallUrl = s.wall_post_id ? `https://vk.ru/wall-66162180_${s.wall_post_id}` : null;



        subContentHtml = `

          <div style="margin-top: 16px; display: flex; flex-direction: column; gap: 20px;">

            

            <!-- Era Banner & Primary Links -->

            <div style="background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(0,0,0,0.6)); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000;">

              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">

                <div>

                  <div style="font-size: 11px; font-family: var(--font-mono); color: var(--nes-gold); font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px;">

                    📜 ЭПОХАЛЬНАЯ ЛЕТОПИСЬ СЕЗОНА

                  </div>

                  <div style="font-family: var(--font-title); font-size: 20px; color: #fff; margin-bottom: 8px;">

                    ${s.era_title || s.name} (${s.year} год)

                  </div>

                  <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: #cbd5e1;">

                    <span>👑 <strong>Организаторы:</strong> ${s.organizers || 'Оргкомитет NST'}</span>

                    <span>🎮 <strong>Платформа:</strong> ${s.emulator || 'Mednafen Netplay'}</span>

                    <span>👥 <strong>Участников:</strong> ${participantsList.length} игроков</span>

                    <span>🏆 <strong>Формат:</strong> ${s.format}</span>

                  </div>

                </div>

                <div style="display: flex; gap: 8px; flex-wrap: wrap;">

                  ${vkTopicUrl ? `

                    <a href="${vkTopicUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #2563eb; color: #fff; border: 1px solid #60a5fa; display: inline-flex; align-items: center; gap: 6px;">

                      💬 Тема обсуждения в VK

                    </a>

                  ` : ''}

                  ${vkWallUrl ? `

                    <a href="${vkWallUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #059669; color: #fff; border: 1px solid #34d399; display: inline-flex; align-items: center; gap: 6px;">

                      📰 Итоги на стене VK

                    </a>

                  ` : ''}

                </div>

              </div>

            </div>



            <!-- Historical Chronicle Text -->

            <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 22px;">

              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-cyan); margin-bottom: 14px; display: flex; align-items: center; gap: 8px;">

                <span>📖 ХРОНИКА И ХОД ТУРНИРА</span>

              </div>

              <div style="color: #e2e8f0; font-size: 14px; line-height: 1.7; display: flex; flex-direction: column; gap: 14px;">

                ${fullChronicleParas.map(p => `<p style="margin: 0; text-align: justify;">${p}</p>`).join('')}

              </div>

            </div>



            <!-- Key Milestones & Records Grid -->

            ${keyEvents.length > 0 ? `

              <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  ⚡ КЛЮЧЕВЫЕ МОМЕНТЫ И РЕКОРДЫ СЕЗОНА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 10px;">

                  ${keyEvents.map(evt => `

                    <div style="background: rgba(255,255,255,0.04); border-left: 3px solid var(--nes-gold); padding: 10px 14px; font-size: 13px; color: #cbd5e1; line-height: 1.5;">

                      ${evt}

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}



            <!-- Divisions Summary -->

            ${Object.keys(divSummary).length > 0 ? `

              <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-green); margin-bottom: 12px;">

                  🏆 ИТОГИ ПО ДИВИЗИОНАМ И ЛИГАМ

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">

                  ${Object.entries(divSummary).map(([dName, dText]) => `

                    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); padding: 12px 16px;">

                      <div style="font-family: var(--font-title); font-size: 13px; color: var(--nes-gold); margin-bottom: 6px;">${dName}</div>

                      <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">${dText}</div>

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}



            <!-- Quotes of the Epoch -->

            ${wallQuotes.length > 0 ? `

              <div style="background: rgba(255, 183, 3, 0.04); border: 1px dashed var(--nes-gold); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  💬 АТМОСФЕРА И ЦИТАТЫ СЕЗОНА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px;">

                  ${wallQuotes.map(q => `

                    <div style="background: rgba(0,0,0,0.4); border-left: 3px solid var(--nes-cyan); padding: 12px 14px;">

                      <div style="font-size: 13px; color: #f1f5f9; font-style: italic; line-height: 1.5; margin-bottom: 6px;">

                        «${q.text}»

                      </div>

                      <div style="font-size: 11px; color: var(--nes-cyan); font-weight: 800; text-align: right;">

                        &mdash; ${q.author}

                      </div>

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}



            <!-- Technical Specs -->

            ${s.tech_specs ? `

              <div style="font-size: 12px; color: #94a3b8; background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.08); padding: 12px 16px;">

                ⚙️ <strong>Матчасть и регламент:</strong> ${s.tech_specs}

              </div>

            ` : ''}



          </div>

        `;

      }



      card.innerHTML = `

        <div class="special-card" style="border-color: var(--nes-cyan); box-shadow: 4px 4px 0px #000;">

          <!-- Header Row -->

          <div class="special-header-row">

            <div>

              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px;">

                <span class="special-tag tag-solo" style="background: #1e3a8a; color: #93c5fd; border-color: #3b82f6;">🏆 ОФИЦИАЛЬНЫЙ СЕЗОН NST</span>

                <span style="font-size: 12px; color: var(--nes-gold); font-weight: 800; font-family: var(--font-mono);">${s.year} ГОД</span>

                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>

                <span style="font-size: 11px; color: #cbd5e1; font-weight: 700;">Goal 3 (NES)</span>

                <span style="font-size: 11px; color: #94a3b8;">&bull;</span>

                <span style="font-size: 11px; color: var(--nes-cyan);">${s.format}</span>

              </div>

              <h2 style="font-family: var(--font-title); font-size: 22px; color: #fff; margin: 0; ">

                ${s.name} &bull; Официальный чемпионат NST (${s.year} г.)

              </h2>

            </div>

          </div>



          <!-- Podium Box -->

          <div class="podium-box-grid">

            <div class="podium-slot gold">

              <span style="font-size: 24px;">🥇</span>

              <div>

                <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">1 МЕСТО &bull; ЧЕМПИОН</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px; ${s.champion ? 'cursor: pointer;' : ''}" ${s.champion ? `onclick="openPlayerModal('${s.champion}')"` : 'title="Источник не называет победителя"'}>${s.champion || '— не назван'}</div>

              </div>

            </div>

            <div class="podium-slot silver">

              <span style="font-size: 24px;">🥈</span>

              <div>

                <div style="font-size: 10px; color: #cbd5e1; font-weight: 800; text-transform: uppercase;">2 МЕСТО &bull; СЕРЕБРО</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px; ${s.runner_up ? 'cursor: pointer;' : ''}" ${s.runner_up ? `onclick="openPlayerModal('${s.runner_up}')"` : ''}>${s.runner_up || '— не назван'}</div>

              </div>

            </div>

            <div class="podium-slot bronze">

              <span style="font-size: 24px;">🥉</span>

              <div>

                <div style="font-size: 10px; color: #d97706; font-weight: 800; text-transform: uppercase;">3 МЕСТО &bull; БРОНЗА</div>

                <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px; ${s.third_place ? 'cursor: pointer;' : ''}" ${s.third_place ? `onclick="openPlayerModal('${s.third_place}')"` : ''}>${s.third_place || '— не назван'}</div>

              </div>

            </div>

            ${s.cup_winner ? `

              <div class="podium-slot" style="border-color: #c084fc; background: rgba(192, 132, 252, 0.08);">

                <span style="font-size: 24px;">🏆</span>

                <div>

                  <div style="font-size: 10px; color: #c084fc; font-weight: 800; text-transform: uppercase;">КУБОК ЛИГИ</div>

                  <div style="font-family: var(--font-title); font-size: 14px; color: #fff; margin-top: 2px; cursor: pointer;" onclick="openPlayerModal('${s.cup_winner}')">${s.cup_winner}</div>

                </div>

              </div>

            ` : ''}

          </div>



          <!-- Key Master Players -->

          ${playersChips ? `

            <div style="margin: 12px 0 16px 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">

              <span style="font-size: 11px; color: #94a3b8; font-weight: 700;">Мастера лиги в сезоне:</span>

              ${playersChips}

            </div>

          ` : ''}



          <!-- Tournament Sub-Navigation Buttons (Tabs) -->

          <div style="display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 2px solid rgba(255,255,255,0.2); padding-bottom: 12px; margin-top: 16px;">

            <button class="filter-btn ${seasonSubTab === 'matches' ? 'active' : ''}" onclick="switchSeasonSubTab('matches')">

              📋 Все матчи сезона (${(s.matches || []).length})

            </button>

            <button class="filter-btn ${seasonSubTab === 'tables' ? 'active' : ''}" onclick="switchSeasonSubTab('tables')">

              🏆 Таблицы лиг

            </button>

            <button class="filter-btn ${seasonSubTab === 'playoff' ? 'active' : ''}" onclick="switchSeasonSubTab('playoff')">

              ⚡ Сетка плей-офф / Призёры

            </button>

            <button class="filter-btn ${seasonSubTab === 'about' ? 'active' : ''}" onclick="switchSeasonSubTab('about')">

              📜 Летопись и история

            </button>

          </div>



          <!-- Active Sub-Tab Content -->

          ${subContentHtml}

        </div>

      `;

      if (seasonSubTab === 'playoff' && playoffViewMode === 'bracket') {
        setTimeout(drawBracketConnectors, 60);
      }

    }



    // Clutch & Records

    function renderClutch() {

      const container = document.getElementById('tab-clutch');

      if (!container) return;



      const medals = DATA.medal_leaders || [];

      const cleanSheets = DATA.clean_sheet_leaders || [];

      const clutch = DATA.clutch_leaders || [];

      const attacking = DATA.spec_attacking || [];

      const defensive = DATA.spec_defensive || [];

      const topScorers = DATA.top_scorers_leaders || [];

      const veterans = DATA.veterans_longevity || [];



      container.innerHTML = `

        <div class="season-banner" style="margin-bottom: 24px;">

          <div class="season-title">📊 ЗАЛ СЛАВЫ РЕКОРДОВ, МЕДАЛИ & АНАЛИТИКА NST (2015–2026)</div>

          <div class="season-meta">Сводная статистика за всю историю киберспортивной лиги Goal 3: медальный зачёт, книга исторических рекордов, стили игры, долгожители и рейтинг цитируемости</div>

        </div>



        <!-- 1. MEDAL TABLE & TROPHY CABINET -->

        <div style="background: rgba(0,0,0,0.65); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000; margin-bottom: 24px;">

          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">

            <div>

              <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-gold); margin: 0;">🏅 ОФИЦИАЛЬНЫЙ МЕДАЛЬНЫЙ ЗАЧЁТ ЛИГИ (TROPHY CABINET)</h2>

              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Титулы и призовые места в официальных чемпионатах и Кубках Лиг (Сезоны 1–9). Спецтурниры и пенальти исключены из Зала славы.</div>

            </div>

            <div style="background: rgba(255, 183, 3, 0.15); border: 1px solid var(--nes-gold); padding: 6px 12px; font-size: 12px; font-weight: 700; color: #fff;">

              👑 Первый GOAT: <strong style="color: var(--nes-gold); cursor: pointer;" onclick="openPlayerModal('mafuta')">mafuta</strong> (7 золотых трофеев)

            </div>

          </div>



          <div class="table-box" style="margin-bottom: 0;">

            <table>

              <thead>

                <tr>

                  <th style="width: 40px; text-align: center;">#</th>

                  <th>Игрок</th>

                  <th style="text-align: center; color: var(--nes-gold);">🥇 Золото</th>

                  <th style="text-align: center; color: #cbd5e1;">🥈 Серебро</th>

                  <th style="text-align: center; color: #d97706;">🥉 Бронза</th>

                  <th style="text-align: center;">Всего</th>

                  <th style="text-align: center;">Финалов</th>

                  <th>Главные титулы</th>

                </tr>

              </thead>

              <tbody>

                ${medals.slice(0, 10).map((m, idx) => `

                  <tr onclick="openPlayerModal('${m.player}')" style="cursor: pointer;">

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: ${idx === 0 ? 'var(--nes-gold)' : (idx === 1 ? '#cbd5e1' : (idx === 2 ? '#d97706' : '#94a3b8'))};">${idx + 1}</td>

                    <td>

                      <div style="display: flex; align-items: center; gap: 8px;">

                        <img src="${m.avatar}" style="width: 26px; height: 26px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${m.player}'">

                        <strong style="color: #fff;">${m.player}</strong>

                      </div>

                    </td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold);">${m.medals.gold}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: #cbd5e1;">${m.medals.silver}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: #d97706;">${m.medals.bronze}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 900; color: #fff;">${m.medals.gold + m.medals.silver + m.medals.bronze}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 700; color: var(--nes-cyan);">${m.medals.finals}</td>

                    <td style="font-size: 11px; color: #94a3b8;">${(m.medals.titles || []).slice(0, 2).join(' &bull; ')}</td>

                  </tr>

                `).join('')}

              </tbody>

            </table>

          </div>

        </div>



        <!-- 2. HISTORIC EXTREMES & RECORDS -->

        <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-cyan); margin: 24px 0 14px 0;">⚡ КНИГА ИСТОРИЧЕСКИХ РЕКОРДОВ NST</h2>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px;">

          <!-- Record 1: Blowout -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid #ffffff; padding: 16px; box-shadow: 3px 3px 0 #000;">

            <div style="font-size: 11px; color: var(--nes-gold); font-family: var(--font-title); letter-spacing: 1px;">💥 САМЫЙ КРУПНЫЙ РАЗГРОМ В ИСТОРИИ</div>

            <div style="font-size: 22px; font-weight: 900; margin: 8px 0; color: #fff;">

              Kunio <span style="color: var(--nes-green);">14 : 0</span> yoxter

            </div>

            <div style="font-size: 12px; color: #94a3b8;">

              Разница: <strong style="color: var(--nes-gold);">+14 мячей</strong> &bull; Официальный Чемпионат (Сезон 2)

            </div>

          </div>



          <!-- Record 2: Thriller -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid #ffffff; padding: 16px; box-shadow: 3px 3px 0 #000;">

            <div style="font-size: 11px; color: var(--nes-cyan); font-family: var(--font-title); letter-spacing: 1px;">🌪️ САМЫЙ БЕЗУМНЫЙ ТРИЛЛЕР (23 ГОЛА)</div>

            <div style="font-size: 22px; font-weight: 900; margin: 8px 0; color: #fff;">

              Kipriot <span style="color: var(--nes-cyan);">12 : 11</span> Transistor

            </div>

            <div style="font-size: 12px; color: #94a3b8;">

              Всего забито: <strong style="color: var(--nes-cyan);">23 гола в одном матче!</strong> &bull; Сезон 4

            </div>

          </div>



          <!-- Record 3: Runner-up Thriller -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid #ffffff; padding: 16px; box-shadow: 3px 3px 0 #000;">

            <div style="font-size: 11px; color: #f59e0b; font-family: var(--font-title); letter-spacing: 1px;">🔥 СВЕРХРЕЗУЛЬТАТИВНОЕ ДЕРБИ (21 ГОЛ)</div>

            <div style="font-size: 22px; font-weight: 900; margin: 8px 0; color: #fff;">

              ectoPower <span style="color: #f59e0b;">11 : 10</span> Huba Buba

            </div>

            <div style="font-size: 12px; color: #94a3b8;">

              Всего забито: <strong style="color: #f59e0b;">21 гол</strong> &bull; Сезон 2 (Золотая эпоха)

            </div>

          </div>

        </div>



        <!-- 2.5. ALL-TIME TOP SCORERS (SEASONS 1–9 ONLY) -->

        <div style="background: rgba(0,0,0,0.65); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000; margin-bottom: 24px;">

          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">

            <div>

              <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-gold); margin: 0;">⚽ ЛУЧШИЕ БОМБАРДИРЫ В ИСТОРИИ (СЕЗОНЫ 1–9)</h2>

              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Суммарное количество голов только в официальных матчах чемпионатов NST (без товарищеских пенальти и спецтурниров)</div>

            </div>

            <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; padding: 6px 12px; font-size: 12px; font-weight: 700; color: #fff;">

              🎯 Лучший бомбардир всех времён: <strong style="color: #fca5a5; cursor: pointer;" onclick="openPlayerModal('ectoPower')">ectoPower</strong> (795 голов)

            </div>

          </div>



          <div class="table-box" style="margin-bottom: 0;">

            <table>

              <thead>

                <tr>

                  <th style="width: 40px; text-align: center;">#</th>

                  <th>Бомбардир</th>

                  <th style="text-align: center; color: var(--nes-gold);">⚽ Всего голов</th>

                  <th style="text-align: center;">Матчей в Сезонах</th>

                  <th style="text-align: center; color: var(--nes-cyan);">Ср. голов за матч</th>

                  <th>Статус</th>

                </tr>

              </thead>

              <tbody>

                ${topScorers.slice(0, 8).map((sc, idx) => `

                  <tr onclick="openPlayerModal('${sc.player}')" style="cursor: pointer;">

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: ${idx === 0 ? 'var(--nes-gold)' : (idx === 1 ? '#cbd5e1' : (idx === 2 ? '#d97706' : '#94a3b8'))};">${idx + 1}</td>

                    <td>

                      <div style="display: flex; align-items: center; gap: 8px;">

                        <img src="${sc.avatar}" style="width: 26px; height: 26px; border: 1px solid #fff;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${sc.player}'">

                        <strong style="color: #fff;">${sc.player}</strong>

                      </div>

                    </td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold); font-size: 16px;">${sc.goals_for}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 700; color: #fff;">${sc.matches}</td>

                    <td style="text-align: center; font-family: var(--font-mono); font-weight: 800; color: var(--nes-cyan);">${sc.gpg}</td>

                    <td style="font-size: 11px; color: #94a3b8;">${idx === 0 ? '🥇 Абсолютный рекордсмен' : (idx === 1 ? '🥈 Легенда золотой эпохи' : '🔥 Элитный снайпер')}</td>

                  </tr>

                `).join('')}

              </tbody>

            </table>

          </div>

        </div>



        <!-- 3. CLEAN SHEETS & CLUTCH KINGS -->

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; margin-bottom: 24px;">

          <!-- Clean Sheets Wall -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid rgba(255,255,255,0.4); padding: 18px; box-shadow: 3px 3px 0 #000;">

            <h3 style="font-family: var(--font-title); font-size: 16px; color: var(--nes-green); margin-bottom: 8px;">🧱 «СУХАЯ СТЕНА» (РЕКОРДСМЕНЫ ПО МАТЧАМ НА НОЛЬ)</h3>

            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">Количество победных матчей, в которых соперник не забил ни одного гола</div>

            <div style="display: flex; flex-direction: column; gap: 8px;">

              ${cleanSheets.map((p, idx) => `

                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(0,0,0,0.3); border-left: 3px solid var(--nes-green); cursor: pointer;" onclick="openPlayerModal('${p.player}')">

                  <div style="display: flex; align-items: center; gap: 8px;">

                    <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold); width: 20px;">${idx + 1}.</span>

                    <strong>${p.player}</strong>

                  </div>

                  <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-green); font-size: 14px;">${p.clean_sheets} сухарей</span>

                </div>

              `).join('')}

            </div>

          </div>



          <!-- Clutch Overtime Kings -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid rgba(255,255,255,0.4); padding: 18px; box-shadow: 3px 3px 0 #000;">

            <h3 style="font-family: var(--font-title); font-size: 16px; color: var(--nes-gold); margin-bottom: 8px;">🎯 КОРОЛИ ОВЕРТАЙМОВ И СТАЛЬНЫХ НЕРВОВ</h3>

            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">Лидеры по проценту побед в матчах до золотого гола (от 3+ овертаймов)</div>

            <div style="display: flex; flex-direction: column; gap: 8px;">

              ${clutch.map((p, idx) => `

                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(0,0,0,0.3); border-left: 3px solid var(--nes-gold); cursor: pointer;" onclick="openPlayerModal('${p.player}')">

                  <div style="display: flex; align-items: center; gap: 8px;">

                    <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-cyan); width: 20px;">${idx + 1}.</span>

                    <strong>${p.player}</strong>

                  </div>

                  <div>

                    <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-gold); font-size: 14px;">${p.ot_win_rate}%</span>

                    <span style="font-size: 11px; color: #94a3b8; margin-left: 4px;">(${p.ot_wins}В-${p.ot_losses}П)</span>

                  </div>

                </div>

              `).join('')}

            </div>

          </div>

        </div>



        <!-- 4. PLAYSTYLES: HURRICANE ATTACK VS IRON BUS -->

        <h2 style="font-family: var(--font-title); font-size: 18px; color: var(--nes-gold); margin: 24px 0 14px 0;">🌪️ СТИЛИ ИГРЫ: УРАГАННАЯ АТАКА VS «АВТОБУСЫ»</h2>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; margin-bottom: 24px;">

          <!-- Attackers -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid rgba(255,255,255,0.4); padding: 18px; box-shadow: 3px 3px 0 #000;">

            <h3 style="font-family: var(--font-title); font-size: 15px; color: #f87171; margin-bottom: 8px;">🔥 САМЫЕ ЗРЕЛИЩНЫЕ / УРАГАННЫЕ ИГРОКИ</h3>

            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">Наибольший средний тотал забитых и пропущенных голов в матчах (от 15+ игр)</div>

            <div style="display: flex; flex-direction: column; gap: 8px;">

              ${attacking.map((p, idx) => `

                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(0,0,0,0.3); border-left: 3px solid #f87171; cursor: pointer;" onclick="openPlayerModal('${p.player}')">

                  <div style="display: flex; align-items: center; gap: 8px;">

                    <span style="font-family: var(--font-mono); font-weight: 800; color: #f87171; width: 20px;">${idx + 1}.</span>

                    <strong>${p.player}</strong>

                  </div>

                  <span style="font-family: var(--font-mono); font-weight: 800; color: #f87171; font-size: 14px;">${p.spectacle} гол/матч</span>

                </div>

              `).join('')}

            </div>

          </div>



          <!-- Defensive -->

          <div style="background: rgba(10, 27, 45, 0.9); border: 2px solid rgba(255,255,255,0.4); padding: 18px; box-shadow: 3px 3px 0 #000;">

            <h3 style="font-family: var(--font-title); font-size: 15px; color: var(--nes-cyan); margin-bottom: 8px;">🛡️ САМЫЕ ЗАКРЫТЫЕ / «АВТОБУСНЫЕ» ИГРОКИ</h3>

            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px;">Наименьший средний тотал голов (строгая позиционная оборона и сушка темпа)</div>

            <div style="display: flex; flex-direction: column; gap: 8px;">

              ${defensive.map((p, idx) => `

                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(0,0,0,0.3); border-left: 3px solid var(--nes-cyan); cursor: pointer;" onclick="openPlayerModal('${p.player}')">

                  <div style="display: flex; align-items: center; gap: 8px;">

                    <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-cyan); width: 20px;">${idx + 1}.</span>

                    <strong>${p.player}</strong>

                  </div>

                  <span style="font-family: var(--font-mono); font-weight: 800; color: var(--nes-cyan); font-size: 14px;">${p.spectacle} гол/матч</span>

                </div>

              `).join('')}

            </div>

          </div>

        </div>



        <!-- 5. VETERANS & LONGEVITY -->

        <h2 style="font-family: var(--font-title); font-size: 18px; color: #fff; margin: 24px 0 14px 0;">⏳ «СТАРАЯ ГВАРДИЯ» NST (ДОЛГОЛЕТИЕ 2015 → 2026)</h2>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-bottom: 24px;">

          ${veterans.map(v => `

            <div style="background: rgba(10, 27, 45, 0.85); border: 2px solid rgba(255,255,255,0.3); padding: 14px; box-shadow: 3px 3px 0 #000; cursor: pointer;" onclick="openPlayerModal('${v.player}')">

              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">

                <strong style="font-size: 15px; color: #fff;">${v.player}</strong>

                <span style="font-family: var(--font-mono); font-size: 11px; font-weight: 800; color: var(--nes-green); background: rgba(34,197,94,0.15); padding: 2px 6px; border: 1px solid #22c55e;">${v.span}</span>

              </div>

              <div style="font-size: 12px; color: #cbd5e1; line-height: 1.4;">${v.desc}</div>

              <div style="font-size: 11px; color: #94a3b8; margin-top: 8px; font-weight: 700;">Всего матчей в архиве: <strong style="color: #fff;">${v.matches}</strong></div>

            </div>

          `).join('')}

        </div>



        

      `;

    }



    // Head-to-Head & Rivalries Engine

    function getAllMatches() {

      const all = [];

      (DATA.seasons || []).forEach(s => {

        const sTitle = s.title || `Сезон ${s.id}`;

        (s.matches || []).forEach(m => {

          const mc = Object.assign({}, m);

          if (!mc.season) mc.season = sTitle;

          if (!mc.league) mc.league = s.league || 'Регулярный чемпионат';

          if (!mc.stage) mc.stage = mc.tour || 'Матч';

          all.push(mc);

        });

      });

      (DATA.special_matches || []).forEach(m => {

        const mc = Object.assign({}, m);

        if (!mc.season) mc.season = 'Спецтурнир';

        if (!mc.league) mc.league = 'Турнир';

        if (!mc.stage) mc.stage = mc.tour || 'Матч';

        all.push(mc);

      });

      return all;

    }



    function initH2HControls() {

      const canonicalMap = new Map();



      // First add Master Profiles (38)

      (DATA.profiles || []).forEach(p => {

        canonicalMap.set(p.player.toLowerCase(), p.player);

      });



      // Then add season participants, normalizing

      (DATA.seasons || []).forEach(s => {

        (s.matches || []).forEach(m => {

          [m.p1, m.p2].forEach(p => {

            if (!p) return;

            const pNorm = p.trim();

            const pLow = pNorm.toLowerCase();

            if (!canonicalMap.has(pLow)) {

              canonicalMap.set(pLow, pNorm);

            }

          });

        });

      });



      const masterNames = (DATA.profiles || []).map(p => p.player);

      const otherNames = [];



      canonicalMap.forEach((origName, low) => {

        if (!masterNames.some(m => m.toLowerCase() === low)) {

          otherNames.push(origName);

        }

      });



      masterNames.sort((a, b) => a.localeCompare(b));

      otherNames.sort((a, b) => a.localeCompare(b));



      const sel1 = document.getElementById('h2hSelectP1');

      const sel2 = document.getElementById('h2hSelectP2');

      if (!sel1 || !sel2) return;



      const optsHtml = `

        <optgroup label="⭐ МАСТЕРА ЛИГИ (АКТИВНЫЕ И ЛЕГЕНДЫ)">

          ${masterNames.map(p => `<option value="${p}">${p}</option>`).join('')}

        </optgroup>

        <optgroup label="🎮 УЧАСТНИКИ ТУРНИРОВ И КУБКОВ">

          ${otherNames.map(p => `<option value="${p}">${p}</option>`).join('')}

        </optgroup>

      `;



      sel1.innerHTML = optsHtml;

      sel2.innerHTML = optsHtml;



      sel1.value = 'Kunio';

      sel2.value = 'Ric25';



      updateH2HComparison();

    }



    function selectH2HPair(p1, p2) {

      const sel1 = document.getElementById('h2hSelectP1');

      const sel2 = document.getElementById('h2hSelectP2');

      if (sel1 && sel2) {

        sel1.value = p1;

        sel2.value = p2;

        updateH2HComparison();

        const res = document.getElementById('h2hComparisonResult');

        if (res) {

          res.scrollIntoView({ behavior: 'smooth', block: 'start' });

        }

      }

    }



    function updateH2HComparison() {

      const sel1 = document.getElementById('h2hSelectP1');

      const sel2 = document.getElementById('h2hSelectP2');

      const container = document.getElementById('h2hComparisonResult');

      if (!sel1 || !sel2 || !container) return;



      const p1 = sel1.value;

      const p2 = sel2.value;



      if (!p1 || !p2 || p1 === p2) {

        container.innerHTML = `

          <div style="background: #081729; border: 1px dashed #2a4e75; border-radius: 8px; padding: 24px; text-align: center; color: #cbd5e1;">

            <div style="font-family: var(--font-body); font-size: 16px; font-weight: 700; color: #f43f5e; margin-bottom: 6px;">ВЫБРАН ОДИН И ТОТ ЖЕ ИГРОК</div>

            <div style="font-size: 14px;">Пожалуйста, выберите двух разных соперников для расчета баланса личных встреч.</div>

          </div>

        `;

        return;

      }



      const p1Low = p1.toLowerCase();

      const p2Low = p2.toLowerCase();

      const allMatches = getAllMatches();



      const pairMatches = allMatches.filter(m => {

        const m1 = (m.p1 || '').toLowerCase();

        const m2 = (m.p2 || '').toLowerCase();

        return (m1 === p1Low && m2 === p2Low) || (m1 === p2Low && m2 === p1Low);

      });



      const p1Wins = pairMatches.filter(m => matchWinnerSide(m) === ((m.p1 || '').toLowerCase() === p1Low ? 1 : 2)).length;



      const p2Wins = pairMatches.filter(m => matchWinnerSide(m) === ((m.p1 || '').toLowerCase() === p2Low ? 1 : 2)).length;



      const draws = pairMatches.filter(m => matchWinnerSide(m) === 0).length;



      const p1Goals = pairMatches.reduce((acc, m) => acc + ((m.p1 || '').toLowerCase() === p1Low ? Number(m.s1 || 0) : Number(m.s2 || 0)), 0);

      const p2Goals = pairMatches.reduce((acc, m) => acc + ((m.p1 || '').toLowerCase() === p2Low ? Number(m.s1 || 0) : Number(m.s2 || 0)), 0);



      const prof1 = DATA.profiles.find(x => x.player.toLowerCase() === p1Low);

      const prof2 = DATA.profiles.find(x => x.player.toLowerCase() === p2Low);

      const av1 = prof1 ? prof1.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p1}`;

      const av2 = prof2 ? prof2.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p2}`;



      const total = pairMatches.length;



      if (total === 0) {

        container.innerHTML = `

          <div style="background: #081729; border: 1px solid #1e3a58; border-radius: 8px; padding: 28px; text-align: center;">

            <div style="display: flex; justify-content: center; align-items: center; gap: 24px; margin-bottom: 16px;">

              <div style="text-align: center; cursor: pointer;" onclick="openPlayerModal('${p1}')">

                <img src="${av1}" class="fighter-avatar" style="border: 2px solid #f43f5e;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p1}'">

                <div style="font-family: var(--font-body); font-size: 16px; font-weight: 700; color: #ffffff; margin-top: 6px;">${p1}</div>

              </div>

              <div style="font-family: var(--font-title); font-size: 24px; color: #64748b;">VS</div>

              <div style="text-align: center; cursor: pointer;" onclick="openPlayerModal('${p2}')">

                <img src="${av2}" class="fighter-avatar" style="border: 2px solid #c084fc;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p2}'">

                <div style="font-family: var(--font-body); font-size: 16px; font-weight: 700; color: #ffffff; margin-top: 6px;">${p2}</div>

              </div>

            </div>

            <div style="font-family: var(--font-body); font-size: 16px; font-weight: 700; color: #f43f5e; margin-bottom: 6px;">МАТЧИ НЕ НАЙДЕНЫ</div>

            <div style="color: #cbd5e1; font-size: 14px;">Официальных встреч между <strong>${p1}</strong> и <strong>${p2}</strong> в базе лиги не зафиксировано.</div>

            <div style="font-size: 12px; color: #94a3b8; margin-top: 6px;">Возможно, игроки выступали в разные периоды времени или в параллельных лигах.</div>

          </div>

        `;

        return;

      }



      const p1Pct = Math.round(p1Wins / total * 100);

      const p2Pct = Math.round(p2Wins / total * 100);

      const drawPct = 100 - p1Pct - p2Pct;

      const avgGoals = ((p1Goals + p2Goals) / total).toFixed(1);



      const matchesListHtml = pairMatches.map((m, idx) => {

        const isP1Home = (m.p1 || '').toLowerCase() === p1Low;

        const s1Val = (m.s1 !== undefined && m.s1 !== null) ? Number(m.s1) : 0;

        const s2Val = (m.s2 !== undefined && m.s2 !== null) ? Number(m.s2) : 0;



        const p1Score = isP1Home ? s1Val : s2Val;

        const p2Score = isP1Home ? s2Val : s1Val;



        const isP1Win = p1Score > p2Score;

        const isP2Win = p2Score > p1Score;

        const h2hMatchTitle = `${p1} vs ${p2} (${p1Score}:${p2Score})${m.season ? ' • ' + m.season : ''}`;

        const protoId = m.vk_url ? registerProtocol(h2hMatchTitle, m.vk_text, m.vk_date, m.vk_page, m.vk_url) : '';

        const isDraw = p1Score === p2Score;



        const seasonTitle = m.season || 'Сезон NST';

        const stageTitle = m.stage || m.tour || 'Матч';

        const leagueTitle = m.league || '';



        const gamesExtra = m.games ? `<div style="font-size: 11px; color: #cbd5e1; margin-top: 3px; font-style: italic;">Игры: ${m.games}</div>` : '';

        const otBadge = m.pk ? '<span class="ot-tag ot-purple" style="font-size: 10px; margin-left: 4px;">ПЕН</span>' : (m.ot ? '<span class="ot-tag ot-gold" style="font-size: 10px; margin-left: 4px;">ОТ</span>' : '');



        const resultBadge = isP1Win 

          ? `<span style="background: #be123c; color: #ffffff; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 4px; white-space: nowrap;">Победа ${p1}</span>`

          : (isP2Win

            ? `<span style="background: #7e22ce; color: #ffffff; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 4px; white-space: nowrap;">Победа ${p2}</span>`

            : `<span style="background: #334155; color: #cbd5e1; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 4px; white-space: nowrap;">Ничья</span>`

          );



        return `

          <div class="h2h-match-row">

            <div class="h2h-match-meta">

              <div class="h2h-match-season" title="${seasonTitle}">${seasonTitle}</div>

              <div class="h2h-match-sub">

                ${leagueTitle ? `<span class="league-badge ${leagueTitle.includes('Высшая') ? 'badge-premier' : (leagueTitle.includes('Средняя') ? 'badge-middle' : 'badge-yard')}" style="font-size: 10px; padding: 2px 6px;">${leagueTitle}</span>` : ''}

                <span style="color: #cbd5e1; font-weight: 600;">${stageTitle}</span>

              </div>

            </div>



            <div class="h2h-duel-center">

              <div class="h2h-player-cell h2h-p1-cell ${isP1Win ? 'h2h-p1-winner' : ''}" onclick="openPlayerModal('${p1}')" style="cursor: pointer;" title="Открыть профиль ${p1}">

                ${isP1Win ? '👑 ' : ''}${p1}

              </div>

              <div class="h2h-score-box">

                <span class="${isP1Win ? 'p1-color' : ''}" style="font-weight: 800;">${p1Score}</span>

                <span style="color: #64748b; margin: 0 4px;">:</span>

                <span class="${isP2Win ? 'p2-color' : ''}" style="font-weight: 800;">${p2Score}</span>

                ${otBadge}

              </div>

              <div class="h2h-player-cell h2h-p2-cell ${isP2Win ? 'h2h-p2-winner' : ''}" onclick="openPlayerModal('${p2}')" style="cursor: pointer;" title="Открыть профиль ${p2}">

                ${p2}${isP2Win ? ' 👑' : ''}

              </div>

            </div>



            <div class="h2h-result-badge">

              ${resultBadge}

              ${gamesExtra}

              ${(m.vk_url || m.video_url) ? `

                <div style="display: flex; gap: 6px; align-items: center; margin-top: 6px; flex-wrap: wrap; justify-content: flex-end;">

                  ${m.vk_url ? `

                    <button type="button" class="source-btn-vk" onclick="event.stopPropagation(); openProtocolModalById('${protoId}')" title="Посмотреть текст отчёта матча из ВК">

                      💬 ВК

                    </button>

                  ` : ''}

                  ${m.video_url ? (

                    (m.video_url.includes('youtube.com') || m.video_url.includes('youtu.be')) ? `

                      <a href="${m.video_url}" target="_blank" rel="noopener" class="source-btn-video" title="Смотреть на YouTube в новой вкладке">

                        🎬 YouTube ↗

                      </a>

                    ` : `

                      <button type="button" class="source-btn-video" onclick="event.stopPropagation(); openVideoModal('${m.video_url}', '${p1} vs ${p2} (${p1Score}:${p2Score})')" title="Смотреть в плеере на сайте">

                        🎬 Видео

                      </button>

                    `

                  ) : ''}

                </div>

              ` : ''}

            </div>

          </div>

        `;

      }).join('');



      container.innerHTML = `

        <div class="h2h-billboard">

          <div class="h2h-fighters-row">

            <!-- Fighter 1 Card (Red Corner) -->

            <div class="fighter-card p1-side" onclick="openPlayerModal('${p1}')" title="Кликните, чтобы открыть профиль ${p1}">

              <img src="${av1}" class="fighter-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p1}'">

              <div class="fighter-info">

                <div class="fighter-name">${p1}</div>

                <div class="fighter-meta">

                  ${prof1 ? `Рейтинг: <strong style="color: #ffffff;">${formatElo(prof1.active_elo)}</strong>` : 'Участник турниров'}

                </div>

                <div class="fighter-wins-badge">

                  ${p1Wins} ПОБЕД (${p1Pct}%)

                </div>

              </div>

            </div>



            <!-- Center Duel Stats (Series Nexus) -->

            <div class="duel-center-stats">

              <div style="font-family: var(--font-body); font-size: 12px; font-weight: 700; color: #cbd5e1; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">

                СЧЁТ В СЕРИИ

              </div>

              <div class="duel-score-large">

                <span class="p1-color">${p1Wins}</span>

                <span class="duel-colon">:</span>

                <span class="p2-color">${p2Wins}</span>

              </div>

              <div class="duel-ratio-bar">

                <div class="duel-bar-p1" style="width: ${p1Pct}%;" title="${p1}: ${p1Pct}%"></div>

                ${draws > 0 ? `<div class="duel-bar-draw" style="width: ${drawPct}%;" title="Ничьи: ${drawPct}%"></div>` : ''}

                <div class="duel-bar-p2" style="width: ${p2Pct}%;" title="${p2}: ${p2Pct}%"></div>

              </div>

              <div class="duel-submetrics">

                <span>Всего матчей: <strong>${total}</strong></span>

                ${draws > 0 ? `<span>Ничьих: <strong>${draws}</strong></span>` : ''}

                <span>Мячи: <strong>${p1Goals} : ${p2Goals}</strong></span>

                <span>Ср. голов: <strong>${avgGoals}</strong></span>

              </div>

            </div>



            <!-- Fighter 2 Card (Purple Corner) -->

            <div class="fighter-card p2-side" onclick="openPlayerModal('${p2}')" title="Кликните, чтобы открыть профиль ${p2}">

              <div class="fighter-info" style="text-align: right;">

                <div class="fighter-name">${p2}</div>

                <div class="fighter-meta">

                  ${prof2 ? `Рейтинг: <strong style="color: #ffffff;">${formatElo(prof2.active_elo)}</strong>` : 'Участник турниров'}

                </div>

                <div class="fighter-wins-badge">

                  ${p2Wins} ПОБЕД (${p2Pct}%)

                </div>

              </div>

              <img src="${av2}" class="fighter-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p2}'">

            </div>

          </div>

        </div>



        <div class="h2h-history-box">

          <div class="h2h-history-header">

            <div style="display: flex; align-items: center; gap: 8px;">

              <span>📋 ИСТОРИЯ ОЧНЫХ МАТЧЕЙ</span>

              <span style="background: #14324f; color: #cbd5e1; font-family: var(--font-mono); font-size: 12px; padding: 2px 8px; border-radius: 4px;">${pairMatches.length}</span>

            </div>

            <div style="font-size: 12px; color: #cbd5e1; font-weight: 500;">Кликните по игроку, чтобы открыть его карточку</div>

          </div>

          <div class="h2h-history-list">

            ${matchesListHtml}

          </div>

        </div>

      `;

    }



    function renderH2H() {
      const pending=(DATA.seasons||[]).filter(s=>s.lazy_url);
      if(pending.length){
        const host=document.getElementById('h2hList');host.textContent='Загружаем протоколы для сравнения…';
        Promise.all(pending.map(s=>NSTData.load(s))).then(renderH2H).catch(error=>{host.textContent=error.message;const button=document.createElement('button');button.textContent='Повторить загрузку';button.className='filter-btn';button.onclick=renderH2H;host.append(button);});return;
      }

      initH2HControls();



      // Default pair selection

      const sel1 = document.getElementById('h2hSelectP1');

      const sel2 = document.getElementById('h2hSelectP2');

      if (sel1 && sel2) {

        if (!sel1.value) sel1.value = 'ectoPower';

        if (!sel2.value) sel2.value = 'Rock';

      }

      updateH2HComparison();



      const hBox = document.getElementById('h2hList');

      if (!hBox) return;



      const allMatches = getAllMatches();



      hBox.innerHTML = (DATA.rivalries || []).map(r => {

        const p1 = r.p1 || r.favorite || '';

        const p2 = r.p2 || r.kryptonite || '';

        const title = r.rivalry || r.rivalry_type || `${p1} vs ${p2}`;

        const notes = r.notes || '';



        const p1Low = p1.toLowerCase();

        const p2Low = p2.toLowerCase();



        const pairMatches = allMatches.filter(m => {

          const m1 = (m.p1 || '').toLowerCase();

          const m2 = (m.p2 || '').toLowerCase();

          return (m1 === p1Low && m2 === p2Low) || (m1 === p2Low && m2 === p1Low);

        });



        const p1Wins = pairMatches.filter(m => matchWinnerSide(m) === ((m.p1 || '').toLowerCase() === p1Low ? 1 : 2)).length;



        const p2Wins = pairMatches.filter(m => matchWinnerSide(m) === ((m.p1 || '').toLowerCase() === p2Low ? 1 : 2)).length;



        const draws = pairMatches.filter(m => matchWinnerSide(m) === 0).length;

        const p1Goals = pairMatches.reduce((acc, m) => acc + ((m.p1 || '').toLowerCase() === p1Low ? Number(m.s1 || 0) : Number(m.s2 || 0)), 0);

        const p2Goals = pairMatches.reduce((acc, m) => acc + ((m.p1 || '').toLowerCase() === p2Low ? Number(m.s1 || 0) : Number(m.s2 || 0)), 0);



        const prof1 = DATA.profiles.find(x => x.player.toLowerCase() === p1Low);

        const prof2 = DATA.profiles.find(x => x.player.toLowerCase() === p2Low);

        const av1 = prof1 ? prof1.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p1}`;

        const av2 = prof2 ? prof2.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p2}`;



        return `

          <div style="background: #0c1e32; border: 1px solid #1e3a58; border-radius: 8px; padding: 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.4); display: flex; flex-direction: column; justify-content: space-between;">

            <div>

              <div style="font-size: 13px; color: #ffffff; font-weight: 700; font-family: var(--font-body); margin-bottom: 10px;">${title}</div>

              <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0; background: #081729; border: 1px solid #1a334e; border-radius: 6px; padding: 10px 14px;">

                <div style="display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="openPlayerModal('${p1}')">

                  <img src="${av1}" style="width: 32px; height: 32px; border-radius: 4px; border: 1px solid #f43f5e;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p1}'">

                  <span style="font-size: 14px; font-weight: 700; color: #f43f5e;">${p1}</span>

                </div>

                <div style="text-align: center;">

                  <div style="font-family: var(--font-mono); font-weight: 800; font-size: 20px; color: #ffffff;">

                    <span style="color: #f43f5e;">${p1Wins}</span> : <span style="color: #c084fc;">${p2Wins}</span>

                  </div>

                  <div style="font-size: 11px; color: #94a3b8;">${pairMatches.length} игр</div>

                </div>

                <div style="display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="openPlayerModal('${p2}')">

                  <span style="font-size: 14px; font-weight: 700; color: #c084fc;">${p2}</span>

                  <img src="${av2}" style="width: 32px; height: 32px; border-radius: 4px; border: 1px solid #c084fc;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${p2}'">

                </div>

              </div>

              <div style="font-size: 12px; color: #cbd5e1; margin-bottom: 6px;">

                Мячи: <strong>${p1Goals} : ${p2Goals}</strong> ${draws > 0 ? `| Ничьих: <strong>${draws}</strong>` : ''}

              </div>

              ${notes ? `<div style="font-size: 12px; color: #cbd5e1; line-height: 1.45; border-left: 3px solid #f43f5e; padding-left: 8px; margin-top: 8px; background: rgba(0,0,0,0.2); padding-top: 4px; padding-bottom: 4px;">${notes}</div>` : ''}

            </div>

            <button class="action-btn" style="width: 100%; margin-top: 14px; padding: 7px 12px; font-size: 13px;" onclick="selectH2HPair('${p1}', '${p2}')">Смотреть очные матчи в калькуляторе ↗</button>

          </div>

        `;

      }).join('');

    }



    let selectedTeamTournId = 'team_champ_6';

    let teamSubTab = 'matches';

    let teamPairFilter = 'all';



    function selectTeamTournament(id) {
      if(!(DATA.team_tournaments||[]).some(t=>t.id===id))return;
      if(location.hash.split('?')[0]!=='#/team/'+encodeURIComponent(id))history.pushState(null,'','#/team/'+encodeURIComponent(id));

      selectedTeamTournId = id;

      teamPairFilter = 'all';

      renderTeamTournamentsBar();

      renderTeamTournamentDetails();

    }



    function switchTeamSubTab(subTab) {
      clearMatchAddress();

      teamSubTab = subTab;

      renderTeamTournamentDetails();

    }



    function filterTeamPair(pair) {
      clearMatchAddress();

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



    // Носитель командных турниров хранит все известные игры в playoff_matches,
    // включая групповой этап. Отдельного массива matches у него может не быть.
    function teamTournamentMatches(t) {
      return (Array.isArray(t.matches) && t.matches.length) ? t.matches : (t.playoff_matches || []);
    }
    function isTeamPlayoffMatch(m) {
      const stage = String(m.stage || m.tour || '').toLowerCase();
      return /финал|1\/[248]|за\s+[35](?:-?е)?\s+место/.test(stage);
    }

    function renderTeamTournamentDetails() {

      const container = document.getElementById('teamTournamentDetailContainer');

      if (!container) return;



      const all = DATA.team_tournaments || [];

      const t = all.find(x => x.id === selectedTeamTournId) || all[0];

      if (!t) return;
      if(!NSTData.ready(t,container,renderTeamTournamentDetails))return;
      viewAddress('team',t.id);



      const matches = teamTournamentMatches(t);

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

          <option value="${escapeHTML(pair)}" ${teamPairFilter === pair ? 'selected' : ''}>${escapeHTML(pair)}</option>

        `).join('');



        const matchesListHtml = filteredMatches.length > 0 ? filteredMatches.map(m => {


          

          return `

            <div class="h2h-match-item" data-match-anchor="${m._anchor||''}" style="padding: 12px 16px; margin-bottom: 8px;">

              <div style="display: flex; align-items: center; gap: 8px; flex: 1.2; min-width: 140px;">

                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--nes-gold); font-weight: 800; min-width: 70px;">

                  ${escapeHTML(m.stage || m.tour || 'Матч')}

                </span>

                <span class="league-badge ${m.league && m.league.includes('Высшая') ? 'badge-premier' : (m.league && m.league.includes('Средняя') ? 'badge-middle' : (m.league && m.league.includes('Кубок') ? 'badge-cup' : 'badge-yard'))}" style="font-size: 10px; padding: 2px 6px;">

                  ${m.league || 'Лига'}

                </span>

              </div>

              <div style="display: flex; align-items: center; justify-content: center; gap: 14px; flex: 2; flex-wrap: wrap;">

                <span style="font-family: var(--font-title); font-size: 14px; color: #fff; text-align: right; flex: 1;">

                  ${escapeHTML(m.t1)}

                </span>

                <div class="score-badge" style="font-size: 15px; padding: 5px 14px; letter-spacing: 1px; font-weight: 900; color: var(--nes-cyan); min-width: 80px; text-align: center;">

                  ${escapeHTML(m.score)}${m.vk_url && /^https?:\/\//.test(m.vk_url) ? `<a href="${escapeHTML(m.vk_url)}" target="_blank" rel="noopener" style="display:block;font:12px var(--font-body);color:var(--nes-cyan);margin-top:4px">Источник ↗</a>` : ''}

                </div>

                <span style="font-family: var(--font-title); font-size: 14px; color: #cbd5e1; text-align: left; flex: 1;">

                  ${escapeHTML(m.t2)}

                </span>

              </div>

            </div>

          `;

        }).join('') : `

          <div style="background: rgba(0,0,0,0.4); border: 2px dashed #94a3b8; padding: 32px; text-align: center; color: #cbd5e1;">

            ${matches.length ? 'Матчи по выбранному фильтру не найдены.' : 'В архиве пока нет отдельных протоколов этого турнира. Итоги и описание доступны в соседних вкладках.'}
            ${!matches.length ? `<div style="margin-top:16px"><button class="filter-btn" onclick="switchTeamSubTab('tables')">Посмотреть итоги</button> <button class="filter-btn" onclick="switchTeamSubTab('about')">О турнире</button></div>` : ''}

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
        // Одинаковый счёт одной пары может относиться к разным играм: не склеиваем их.
        const uniquePlayoff = matches.filter(isTeamPlayoffMatch);

        if (uniquePlayoff.length === 0) {
          subContentHtml = `
            <div style="background: rgba(17, 24, 39, 0.85); border: 2px solid var(--nes-gold); padding: 28px 20px; text-align: center; box-shadow: 4px 4px 0 #000; margin-top: 14px;">
              <div style="font-size: 32px; margin-bottom: 8px;">👥 ⚽</div>
              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-gold); margin-bottom: 8px;">
                ПРОТОКОЛЫ ПЛЕЙ-ОФФ НЕ ДОБАВЛЕНЫ
              </div>
              <div style="font-size: 13px; color: #cbd5e1; max-width: 600px; margin: 0 auto 16px auto; line-height: 1.6;">
                В текущем архиве нет отдельных матчей с подтверждённой стадией плей-офф. Это не означает, что плей-офф не проводился. Доступные результаты смотрите в итогах и описании турнира.
              </div>
              <button type="button" class="filter-btn active" style="font-size: 12px; padding: 6px 16px;" onclick="switchTeamSubTab('matches')">
                📋 Посмотреть все матчи турнира
              </button>
            </div>
          `;
        } else if (t.archive_note) {
          // Восстановлены ноги серий, а не итоговые счета серий: не строим из них вымышленную сетку.
          subContentHtml = `<p style="color:#cbd5e1;margin:16px 0">Протоколы отдельных игр плей-офф. Счёт каждой строки относится к игре, а не ко всей серии.</p>` + uniquePlayoff.map(m => `
            <div class="h2h-match-item" style="padding:12px;margin-bottom:8px;flex-wrap:wrap">
              <span>${escapeHTML(m.stage || '')}</span><strong>${escapeHTML(m.t1)} — ${escapeHTML(m.t2)}</strong>
              <span class="score-badge">${escapeHTML(m.score)}</span>
              ${m.vk_url ? `<a href="${escapeHTML(m.vk_url)}" target="_blank" rel="noopener" style="color:var(--nes-cyan)">Источник ↗</a>` : ''}
            </div>`).join('');
        } else {
          // Normalize matches
          const playoffMatches = uniquePlayoff.map(m => {
            const p1 = m.t1 || 'Команда 1';
            const p2 = m.t2 || 'Команда 2';
            let s1 = 0, s2 = 0;
            if (m.score && String(m.score).includes(':')) {
              const parts = String(m.score).split(':');
              s1 = parseInt(parts[0], 10) || 0;
              s2 = parseInt(parts[1], 10) || 0;
            } else if (m.score && String(m.score).toLowerCase().includes('победа')) {
              if (String(m.score).toLowerCase().includes(p1.toLowerCase())) { s1 = 1; s2 = 0; }
              else { s1 = 0; s2 = 1; }
            }
            return {
              p1: p1,
              p2: p2,
              s1: s1,
              s2: s2,
              tour: m.tour || m.stage || 'Плей-офф',
              score: m.score || `${s1}:${s2}`,
              league: m.league || ''
            };
          });

          // Round weighting
          const roundOrderDef = [
            { key: '1/4', label: '1/4 Финала', weight: 1 },
            { key: '1/2', label: 'Полуфинал', weight: 2 },
            { key: '3', label: 'За 3-е место', weight: 3 },
            { key: 'финал', label: 'Гранд-Финал', weight: 4 }
          ];

          function getTeamRoundDef(rName) {
            const rLow = (rName || '').toLowerCase();
            for (const ro of roundOrderDef) {
              if (ro.key === 'финал') {
                if ((rLow.includes('финал') || rLow.includes('final')) && !rLow.includes('1/2') && !rLow.includes('1/4') && !rLow.includes('3')) {
                  return ro;
                }
              } else if (rLow.includes(ro.key) || (ro.key === '1/2' && rLow.includes('полуфинал'))) {
                return ro;
              }
            }
            return { key: rName, label: rName || 'Плей-офф', weight: 99 };
          }

          // Group into rounds
          const roundMap = {};
          playoffMatches.forEach(m => {
            const rDef = getTeamRoundDef(m.tour);
            if (!roundMap[rDef.label]) {
              roundMap[rDef.label] = { def: rDef, matches: [] };
            }
            roundMap[rDef.label].matches.push(m);
          });

          const sortedRounds = Object.values(roundMap).sort((a, b) => a.def.weight - b.def.weight);

          // Champion Info
          let championName = t.champion || null;
          if (championName && championName.includes('/')) {
            championName = championName.split('/')[0].trim();
          }

          // Helper for pair avatars
          function getTeamAvatars(teamName) {
            const parts = teamName.split(/&|\/|\+/).map(x => x.trim()).filter(Boolean);
            return parts.slice(0, 2).map(p => {
              const prof = DATA.profiles.find(x => x.player.toLowerCase() === p.toLowerCase());
              return prof ? prof.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${p}`;
            });
          }

          // Visual Bracket HTML
          let roundsHtml = '';
          sortedRounds.forEach(r => {
            const matchups = {};
            r.matches.forEach(m => {
              const pairKey = [m.p1, m.p2].sort().join('__VS__');
              if (!matchups[pairKey]) matchups[pairKey] = [];
              matchups[pairKey].push(m);
            });

            let matchupCardsHtml = '';
            Object.entries(matchups).forEach(([pKey, games]) => {
              const [pA, pB] = pKey.split('__VS__');
              let pAwins = 0, pBwins = 0;
              games.forEach(g => {
                if ((g.p1 === pA && g.s1 > g.s2) || (g.p2 === pA && g.s2 > g.s1)) pAwins++;
                else if ((g.p1 === pB && g.s1 > g.s2) || (g.p2 === pB && g.s2 > g.s1)) pBwins++;
              });

              const isAWinner = pAwins > pBwins;
              const isBWinner = pBwins > pAwins;
              const avsA = getTeamAvatars(pA);
              const avsB = getTeamAvatars(pB);
              const isFinal = r.def.key === 'финал';

              matchupCardsHtml += `
                <div class="bracket-match-card ${isFinal ? 'is-final' : ''}" data-players="${pA.toLowerCase()},${pB.toLowerCase()}">
                  <div class="bracket-card-top">
                    <span style="color: var(--nes-gold);">${r.def.label}</span>
                    <span>${games[0].score || `${pAwins}:${pBwins}`}</span>
                  </div>
                  <div class="bracket-player-row ${(isAWinner ? 'winner' : '')} ${(isBWinner ? 'loser' : '')}" data-player="${pA}" onmouseenter="highlightPlayerBracketPath('${pA}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pA}')">
                    <div class="bracket-p-info">
                      <div style="display: flex; gap: 2px;">
                        ${avsA.map(av => `<img src="${av}" class="bracket-p-avatar" style="width: 18px; height: 18px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=p'">`).join('')}
                      </div>
                      <span class="bracket-p-name" style="font-size: 11px;">${pA}</span>
                      ${isAWinner ? '<span class="bracket-winner-crown">👑</span>' : ''}
                    </div>
                    <span class="bracket-series-score">${pAwins}</span>
                  </div>
                  <div class="bracket-player-row ${(isBWinner ? 'winner' : '')} ${(isAWinner ? 'loser' : '')}" data-player="${pB}" onmouseenter="highlightPlayerBracketPath('${pB}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pB}')">
                    <div class="bracket-p-info">
                      <div style="display: flex; gap: 2px;">
                        ${avsB.map(av => `<img src="${av}" class="bracket-p-avatar" style="width: 18px; height: 18px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=p'">`).join('')}
                      </div>
                      <span class="bracket-p-name" style="font-size: 11px;">${pB}</span>
                      ${isBWinner ? '<span class="bracket-winner-crown">👑</span>' : ''}
                    </div>
                    <span class="bracket-series-score">${pBwins}</span>
                  </div>
                </div>
              `;
            });

            roundsHtml += `
              <div class="bracket-round">
                <div class="bracket-round-header">
                  ${r.def.label} (${Object.keys(matchups).length})
                </div>
                <div class="bracket-round-matches">
                  ${matchupCardsHtml}
                </div>
              </div>
            `;
          });

          // Champion Round
          if (championName) {
            const champAvatars = getTeamAvatars(championName);
            roundsHtml += `
              <div class="bracket-champion-round">
                <div class="bracket-round-header" style="color: var(--nes-gold); border-bottom-color: var(--nes-gold);">
                  🏆 ЧЕМПИОНЫ
                </div>
                <div class="bracket-champion-box" data-player="${championName}" onmouseenter="highlightPlayerBracketPath('${championName}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${championName}')">
                  <div style="font-size: 32px; filter: drop-shadow(0 0 8px #ffcb05); margin-bottom: 6px;">👑</div>
                  <div style="display: flex; justify-content: center; gap: 4px; margin-bottom: 6px;">
                    ${champAvatars.map(av => `<img src="${av}" class="bracket-champ-avatar" style="width: 38px; height: 38px;" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=champ'">`).join('')}
                  </div>
                  <div class="bracket-champ-name" style="font-size: 13px;">${championName}</div>
                  <div class="bracket-champ-sub">🥇 ПОБЕДИТЕЛИ ЧЕМПИОНАТА 2х2</div>
                  <div style="font-size: 10px; color: var(--nes-cyan); margin-top: 6px; font-weight: 800; text-transform: uppercase;">${t.title}</div>
                </div>
              </div>
            `;
          }

          // Team Pills
          const allTeamsPills = Array.from(new Set(playoffMatches.flatMap(m => [m.p1, m.p2]))).sort();
          const teamPillsHtml = `
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); padding: 8px 12px;">
              <span style="font-size: 11px; font-family: var(--font-title); color: #94a3b8; margin-right: 4px;">👥 Быстрый выбор пути команды:</span>
              ${allTeamsPills.map(tm => `
                <button type="button" class="bracket-player-pill" data-player="${tm}" onmouseenter="highlightPlayerBracketPath('${tm}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${tm}')">
                  ${tm}
                </button>
              `).join('')}
            </div>
          `;

          const visualBracketHtml = `
            <div style="margin-top: 10px;">
              ${teamPillsHtml}
              <div id="teamBracketPathBanner" class="bracket-path-banner">
                <span style="color: #94a3b8;">💡 Наведите на любую команду или нажмите, чтобы проследить её турнирный путь</span>
              </div>
              <div class="bracket-wrapper" id="teamBracketWrapper">
                <svg id="teamBracketSvg" class="bracket-svg"></svg>
                <div class="bracket-container" id="teamBracketContainer">
                  ${roundsHtml}
                </div>
              </div>
            </div>
          `;

          // Flat list
          const flatListHtml = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; margin-top: 12px;">
              ${playoffMatches.map(m => `
                <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); padding: 12px 14px; display: flex; justify-content: space-between; align-items: center;">
                  <div style="flex: 1;">
                    <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">${m.tour || 'Плей-офф'}</div>
                    <div style="font-size: 13px; color: ${m.s1 > m.s2 ? 'var(--nes-gold)' : '#fff'}; font-weight: 800; margin-top: 3px;">${m.p1}</div>
                    <div style="font-size: 13px; color: ${m.s2 > m.s1 ? 'var(--nes-gold)' : '#94a3b8'}; font-weight: 700;">${m.p2}</div>
                  </div>
                  <div class="score-badge" style="font-size: 15px; padding: 5px 12px; font-weight: 900; color: var(--nes-cyan); margin-left: 10px;">
                    ${m.score}
                  </div>
                </div>
              `).join('')}
            </div>
          `;

          subContentHtml = `
            <div style="margin-top: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
                <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold);">
                  ⚡ СЕТКА ПЛЕЙ-ОФФ И ИТОГИ 2х2:
                </div>
                <div style="display: flex; gap: 6px;">
                  <button type="button" class="filter-btn ${teamPlayoffViewMode === 'bracket' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setTeamPlayoffViewMode('bracket')">
                    ⚡ Турнирная сетка
                  </button>
                  <button type="button" class="filter-btn ${teamPlayoffViewMode === 'list' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setTeamPlayoffViewMode('list')">
                    📋 Список всех игр (${playoffMatches.length})
                  </button>
                </div>
              </div>
              ${teamPlayoffViewMode === 'bracket' ? visualBracketHtml : flatListHtml}
            </div>
          `;
        }
      }

      else if (teamSubTab === 'about') {

        const fullChronicleParas = (t.full_chronicle || t.summary || t.description || '').split(String.fromCharCode(10) + String.fromCharCode(10)).filter(Boolean);

        const keyEvents = t.key_events || [];

        const wallQuotes = t.wall_quotes || [];

        const vkTopicUrl = t.topic_id ? `https://vk.ru/topic-66162180_${t.topic_id}` : null;

        const vkWallUrl = t.wall_post_id ? `https://vk.ru/wall-66162180_${t.wall_post_id}` : null;



        subContentHtml = `

          <div style="margin-top: 16px; display: flex; flex-direction: column; gap: 20px;">

            <!-- Era Banner & Primary Links -->

            <div style="background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(0,0,0,0.6)); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000;">

              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">

                <div>

                  <div style="font-size: 11px; font-family: var(--font-mono); color: var(--nes-gold); font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px;">

                    📜 ЛЕТОПИСЬ КОМАНДНОГО ЧЕМПИОНАТА 2х2

                  </div>

                  <div style="font-family: var(--font-title); font-size: 20px; color: #fff; margin-bottom: 8px;">

                    ${t.era_title || t.title} (${t.season_year || t.year || ''})

                  </div>

                  <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: #cbd5e1;">

                    ${(t.organizers || t.organizer) ? `<span>👑 <strong>Организатор:</strong> ${t.organizers || t.organizer}</span>` : ''}

                    ${t.prize_pool ? `<span>💰 <strong>Призовой фонд:</strong> <strong style="color: var(--nes-gold);">${t.prize_pool}</strong></span>` : ''}

                    <span>🎮 <strong>Платформа:</strong> ${t.emulator || t.game || 'Nestopia / Mednafen'}</span>

                    <span>🏆 <strong>Формат:</strong> ${t.format || 'Командный 2х2'}</span>

                  </div>

                </div>

                <div style="display: flex; gap: 8px; flex-wrap: wrap;">

                  ${vkTopicUrl ? `

                    <a href="${vkTopicUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #2563eb; color: #fff; border: 1px solid #60a5fa; display: inline-flex; align-items: center; gap: 6px;">

                      💬 Тема обсуждения в VK

                    </a>

                  ` : ''}

                  ${vkWallUrl ? `

                    <a href="${vkWallUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #059669; color: #fff; border: 1px solid #34d399; display: inline-flex; align-items: center; gap: 6px;">

                      📰 Итоги на стене VK

                    </a>

                  ` : ''}

                </div>

              </div>

            </div>



            <!-- Historical Chronicle Text -->

            <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 22px;">

              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-cyan); margin-bottom: 14px;">

                📖 ХРОНИКА И ПАРНЫЕ СРАЖЕНИЯ

              </div>

              <div style="color: #e2e8f0; font-size: 14px; line-height: 1.7; display: flex; flex-direction: column; gap: 14px;">

                ${fullChronicleParas.map(p => `<p style="margin: 0; text-align: justify;">${p}</p>`).join('')}

              </div>

            </div>



            <!-- Key Milestones -->

            ${keyEvents.length > 0 ? `

              <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  ⚡ КЛЮЧЕВЫЕ МОМЕНТЫ ТУРНИРА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 10px;">

                  ${keyEvents.map(evt => `

                    <div style="background: rgba(255,255,255,0.04); border-left: 3px solid var(--nes-gold); padding: 10px 14px; font-size: 13px; color: #cbd5e1; line-height: 1.5;">

                      ${evt}

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}



            <!-- Quotes of the Epoch -->

            ${wallQuotes.length > 0 ? `

              <div style="background: rgba(255, 183, 3, 0.04); border: 1px dashed var(--nes-gold); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  💬 АТМОСФЕРА И ЦИТАТЫ ТУРНИРА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px;">

                  ${wallQuotes.map(q => `

                    <div style="background: rgba(0,0,0,0.4); border-left: 3px solid var(--nes-cyan); padding: 12px 14px;">

                      <div style="font-size: 13px; color: #f1f5f9; font-style: italic; line-height: 1.5; margin-bottom: 6px;">

                        «${q.text}»

                      </div>

                      <div style="font-size: 11px; color: var(--nes-cyan); font-weight: 800; text-align: right;">

                        &mdash; ${q.author}

                      </div>

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}

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

              <h2 style="font-family: var(--font-title); font-size: 22px; color: #fff; margin: 0; ">

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



          <div class="archive-coverage" role="note">
            <strong>${matches.length?'Архив протоколов: полнота не подтверждена':'Отдельные протоколы пока не восстановлены'}</strong>
            <span>Доступно записей игр и серий: ${matches.length}. ${t.archive_pending?`Связанных задач на проверку: ${Number(t.archive_pending)}.`:'Открытых связанных задач в очереди нет; это не гарантирует полноту архива.'}</span>
            <span>Итоги турнира и протоколы восстанавливаются по отдельным источникам.</span>
            ${t.archive_pending?`<a href="queue.html?tournament=${encodeURIComponent(t.id)}">Задачи по этому турниру</a>`:''}
          </div>
          ${t.archive_note ? `<p style="margin:16px 0;padding:12px 16px;background:var(--nes-card-bg);border:var(--nes-panel-border);border-radius:6px;color:#cbd5e1;font-size:13px">${escapeHTML(t.archive_note)}</p>` : ''}

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

      if (teamSubTab === 'playoff' && teamPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('teamBracketWrapper', 'teamBracketContainer', 'teamBracketSvg'), 60);
      }

    }



    let selectedSpecialTournId = 'youth_championship_2';

    let specialSubTab = 'matches';

    let specialPlayerFilter = 'all';



    function selectSpecialTournament(id) {
      if(!(DATA.special_tournaments||[]).some(t=>t.id===id))return;
      if(location.hash.split('?')[0]!=='#/special/'+encodeURIComponent(id))history.pushState(null,'','#/special/'+encodeURIComponent(id));

      selectedSpecialTournId = id;

      specialPlayerFilter = 'all';

      renderSpecialTournamentsBar();

      renderSpecialTournamentDetails();

    }



    function switchSpecialSubTab(subTab) {
      clearMatchAddress();

      specialSubTab = subTab;

      renderSpecialTournamentDetails();

    }



    function filterSpecialPlayer(p) {
      clearMatchAddress();

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

        else if (t.id === 'penalty_tournament_4') shortName = '🥅 Пенальти 4';

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
      if(t&&!NSTData.ready(t,container,renderSpecialTournamentDetails))return;
      if(t)viewAddress('special',t.id);

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

            <div class="h2h-match-item" data-match-anchor="${m._anchor||''}" style="padding: 12px 16px; margin-bottom: 8px;">

              <div style="display: flex; align-items: center; gap: 8px; flex: 1.2; min-width: 140px;">

                <span style="font-family: var(--font-mono); font-size: 12px; color: var(--nes-gold); font-weight: 800; min-width: 70px;">

                  ${m.tour || m.stage || 'Матч'}

                </span>

                <span class="league-badge ${m.league && m.league.includes('Высшая') ? 'badge-premier' : (m.league && m.league.includes('Средняя') ? 'badge-middle' : (m.league && m.league.includes('Кубок') ? 'badge-cup' : 'badge-yard'))}" style="font-size: 10px; padding: 2px 6px;">

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
        const rawPlayoff = (t.playoff && t.playoff.length > 0) ? t.playoff : (t.matches || []).filter(m => {
          const st = (m.stage || m.tour || '').toLowerCase();
          return st.includes('финал') || st.includes('1/') || st.includes('winners') || st.includes('losers') || st.includes('раунд');
        });

        if (rawPlayoff.length === 0) {
          subContentHtml = `
            <div style="background: rgba(17, 24, 39, 0.85); border: 2px solid var(--nes-gold); padding: 28px 20px; text-align: center; box-shadow: 4px 4px 0 #000; margin-top: 14px;">
              <div style="font-size: 32px; margin-bottom: 8px;">🧗 🏖️</div>
              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-gold); margin-bottom: 8px;">
                КЛУБНЫЙ ФОРМАТ / ЛАДДЕР (БЕЗ ОЛИМПИЙСКОЙ СЕТКИ)
              </div>
              <div style="font-size: 13px; color: #cbd5e1; max-width: 600px; margin: 0 auto 16px auto; line-height: 1.6;">
                Данный турнир проводился по групповой системе или рейтинговой лестнице (Ladder). 
                Все встречи и результаты зафиксированы во вкладке «Все матчи».
              </div>
              <button type="button" class="filter-btn active" style="font-size: 12px; padding: 6px 16px;" onclick="switchSpecialSubTab('matches')">
                📋 Посмотреть все матчи турнира
              </button>
            </div>
          `;
        } else {
          // Normalize special playoff matches
          const playoffMatches = rawPlayoff.map(m => {
            const p1 = m.p1 || m.t1 || 'Игрок 1';
            const p2 = m.p2 || m.t2 || 'Игрок 2';
            let s1 = 0, s2 = 0;
            if (typeof m.s1 === 'number' && typeof m.s2 === 'number') {
              s1 = m.s1; s2 = m.s2;
            } else if (m.score && String(m.score).includes(':')) {
              const parts = String(m.score).split(':');
              s1 = parseInt(parts[0], 10) || 0;
              s2 = parseInt(parts[1], 10) || 0;
            } else if (m.score && String(m.score).toLowerCase().includes('победа')) {
              if (String(m.score).toLowerCase().includes(p1.toLowerCase())) { s1 = 1; s2 = 0; }
              else { s1 = 0; s2 = 1; }
            }
            return {
              p1: p1,
              p2: p2,
              s1: s1,
              s2: s2,
              tour: m.stage || m.tour || 'Плей-офф',
              games: m.games || '',
              score: m.score || `${s1}:${s2}`
            };
          });

          // Standard round weighting
          const roundOrderDef = [
            { key: '1/16', label: '1/16 Финала', weight: 1 },
            { key: '1/8', label: '1/8 Финала', weight: 2 },
            { key: '1/4', label: '1/4 Финала', weight: 3 },
            { key: '1/2', label: 'Полуфинал', weight: 4 },
            { key: '3', label: 'За 3-е место', weight: 5 },
            { key: 'финал', label: 'Гранд-Финал', weight: 6 }
          ];

          function getSpecialRoundDef(rName) {
            const rLow = (rName || '').toLowerCase();
            for (const ro of roundOrderDef) {
              if (ro.key === 'финал') {
                if ((rLow.includes('финал') || rLow.includes('final')) && !rLow.includes('1/16') && !rLow.includes('1/8') && !rLow.includes('1/4') && !rLow.includes('1/2') && !rLow.includes('3')) {
                  return ro;
                }
              } else if (rLow.includes(ro.key) || (ro.key === '1/2' && rLow.includes('полуфинал'))) {
                return ro;
              }
            }
            return { key: rName, label: rName || 'Плей-офф', weight: 99 };
          }

          // Group matches into rounds
          const roundMap = {};
          playoffMatches.forEach(m => {
            const rDef = getSpecialRoundDef(m.tour);
            if (!roundMap[rDef.label]) {
              roundMap[rDef.label] = { def: rDef, matches: [] };
            }
            roundMap[rDef.label].matches.push(m);
          });

          const sortedRounds = Object.values(roundMap).sort((a, b) => a.def.weight - b.def.weight);

          // Determine Champion
          let championName = t.champion || null;
          if (championName && championName.includes('/')) {
            championName = championName.split('/')[0].trim();
          }
          const champProf = championName ? DATA.profiles.find(x => x.player.toLowerCase() === championName.toLowerCase()) : null;
          const champAvatar = champProf ? champProf.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${championName || 'champ'}`;

          // Visual Bracket HTML
          let roundsHtml = '';
          sortedRounds.forEach(r => {
            const matchups = {};
            r.matches.forEach(m => {
              const pairKey = [m.p1, m.p2].sort().join('__VS__');
              if (!matchups[pairKey]) matchups[pairKey] = [];
              matchups[pairKey].push(m);
            });

            let matchupCardsHtml = '';
            Object.entries(matchups).forEach(([pKey, games]) => {
              const [pA, pB] = pKey.split('__VS__');
              let pAwins = 0, pBwins = 0;
              games.forEach(g => {
                if ((g.p1 === pA && g.s1 > g.s2) || (g.p2 === pA && g.s2 > g.s1)) pAwins++;
                else if ((g.p1 === pB && g.s1 > g.s2) || (g.p2 === pB && g.s2 > g.s1)) pBwins++;
              });

              const isAWinner = pAwins > pBwins;
              const isBWinner = pBwins > pAwins;
              const profA = DATA.profiles.find(x => x.player.toLowerCase() === pA.toLowerCase());
              const profB = DATA.profiles.find(x => x.player.toLowerCase() === pB.toLowerCase());
              const avA = profA ? profA.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pA}`;
              const avB = profB ? profB.avatar : `https://api.dicebear.com/7.x/bottts/svg?seed=${pB}`;
              const isFinal = r.def.key === 'финал';

              matchupCardsHtml += `
                <div class="bracket-match-card ${isFinal ? 'is-final' : ''}" data-players="${pA.toLowerCase()},${pB.toLowerCase()}">
                  <div class="bracket-card-top">
                    <span style="color: var(--nes-gold);">${r.def.label}</span>
                    <span>${games[0].score || `${pAwins}:${pBwins}`}</span>
                  </div>
                  <div class="bracket-player-row ${(isAWinner ? 'winner' : '')} ${(isBWinner ? 'loser' : '')}" data-player="${pA}" onmouseenter="highlightPlayerBracketPath('${pA}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pA}')">
                    <div class="bracket-p-info">
                      <img src="${avA}" class="bracket-p-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${pA}'">
                      <span class="bracket-p-name">${pA}</span>
                      ${isAWinner ? '<span class="bracket-winner-crown">👑</span>' : ''}
                    </div>
                    <span class="bracket-series-score">${pAwins}</span>
                  </div>
                  <div class="bracket-player-row ${(isBWinner ? 'winner' : '')} ${(isAWinner ? 'loser' : '')}" data-player="${pB}" onmouseenter="highlightPlayerBracketPath('${pB}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${pB}')">
                    <div class="bracket-p-info">
                      <img src="${avB}" class="bracket-p-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${pB}'">
                      <span class="bracket-p-name">${pB}</span>
                      ${isBWinner ? '<span class="bracket-winner-crown">👑</span>' : ''}
                    </div>
                    <span class="bracket-series-score">${pBwins}</span>
                  </div>
                  ${games[0].games ? `
                    <div style="font-size: 10px; color: var(--nes-cyan); padding: 4px 10px; background: rgba(0,0,0,0.3); border-top: 1px solid rgba(255,255,255,0.06); font-family: var(--font-mono);">
                      ${games[0].games}
                    </div>
                  ` : ''}
                </div>
              `;
            });

            roundsHtml += `
              <div class="bracket-round">
                <div class="bracket-round-header">
                  ${r.def.label} (${Object.keys(matchups).length})
                </div>
                <div class="bracket-round-matches">
                  ${matchupCardsHtml}
                </div>
              </div>
            `;
          });

          // Champion Round
          if (championName) {
            roundsHtml += `
              <div class="bracket-champion-round">
                <div class="bracket-round-header" style="color: var(--nes-gold); border-bottom-color: var(--nes-gold);">
                  🏆 ЧЕМПИОН
                </div>
                <div class="bracket-champion-box" data-player="${championName}" onmouseenter="highlightPlayerBracketPath('${championName}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${championName}')">
                  <div style="font-size: 32px; filter: drop-shadow(0 0 8px #ffcb05); margin-bottom: 6px;">👑</div>
                  <img src="${champAvatar}" class="bracket-champ-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${championName}'">
                  <div class="bracket-champ-name" onclick="openPlayerModal('${championName}')">${championName}</div>
                  <div class="bracket-champ-sub">🥇 ПОБЕДИТЕЛЬ ТУРНИРА</div>
                  <div style="font-size: 10px; color: var(--nes-cyan); margin-top: 6px; font-weight: 800; text-transform: uppercase;">${t.title}</div>
                </div>
              </div>
            `;
          }

          // Participant Pills
          const allSpecialParticipants = Array.from(new Set(playoffMatches.flatMap(m => [m.p1, m.p2]))).sort();
          const playerPillsHtml = `
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); padding: 8px 12px;">
              <span style="font-size: 11px; font-family: var(--font-title); color: #94a3b8; margin-right: 4px;">🎯 Быстрый выбор турнирного пути:</span>
              ${allSpecialParticipants.map(p => `
                <button type="button" class="bracket-player-pill" data-player="${p}" onmouseenter="highlightPlayerBracketPath('${p}')" onmouseleave="clearPlayerBracketHighlight()" onclick="selectPlayerBracketPath('${p}')">
                  ${p}
                </button>
              `).join('')}
            </div>
          `;

          const visualBracketHtml = `
            <div style="margin-top: 10px;">
              ${playerPillsHtml}
              <div id="specialBracketPathBanner" class="bracket-path-banner">
                <span style="color: #94a3b8;">💡 Наведите на любого участника или нажмите, чтобы проследить его путь по сетке</span>
              </div>
              <div class="bracket-wrapper" id="specialBracketWrapper">
                <svg id="specialBracketSvg" class="bracket-svg"></svg>
                <div class="bracket-container" id="specialBracketContainer">
                  ${roundsHtml}
                </div>
              </div>
            </div>
          `;

          // Flat list
          const flatListHtml = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; margin-top: 12px;">
              ${playoffMatches.map(m => `
                <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); padding: 12px 14px; display: flex; justify-content: space-between; align-items: center;">
                  <div style="flex: 1;">
                    <div style="font-size: 10px; color: var(--nes-gold); font-weight: 800; text-transform: uppercase;">${m.tour || 'Плей-офф'}</div>
                    <div style="font-size: 13px; color: ${m.s1 > m.s2 ? 'var(--nes-gold)' : '#fff'}; font-weight: 800; margin-top: 3px;">${m.p1}</div>
                    <div style="font-size: 13px; color: ${m.s2 > m.s1 ? 'var(--nes-gold)' : '#94a3b8'}; font-weight: 700;">${m.p2}</div>
                    ${m.games ? `<div style="font-size: 10px; color: var(--nes-cyan); margin-top: 2px;">Сеты: ${m.games}</div>` : ''}
                  </div>
                  <div class="score-badge" style="font-size: 15px; padding: 5px 12px; font-weight: 900; color: var(--nes-cyan); margin-left: 10px;">
                    ${m.score}
                  </div>
                </div>
              `).join('')}
            </div>
          `;

          subContentHtml = `
            <div style="margin-top: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
                <div style="font-family: var(--font-title); font-size: 14px; color: var(--nes-gold);">
                  ⚡ СЕТКА ПЛЕЙ-ОФФ И ИТОГИ КУБКА:
                </div>
                <div style="display: flex; gap: 6px;">
                  <button type="button" class="filter-btn ${specialPlayoffViewMode === 'bracket' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setSpecialPlayoffViewMode('bracket')">
                    ⚡ Турнирная сетка
                  </button>
                  <button type="button" class="filter-btn ${specialPlayoffViewMode === 'list' ? 'active' : ''}" style="padding: 4px 10px; font-size: 12px;" onclick="setSpecialPlayoffViewMode('list')">
                    📋 Список всех игр (${playoffMatches.length})
                  </button>
                </div>
              </div>
              ${specialPlayoffViewMode === 'bracket' ? visualBracketHtml : flatListHtml}
            </div>
          `;
        }
      }

      else if (specialSubTab === 'about') {
        subContentHtml = `

          <div style="margin-top: 16px; display: flex; flex-direction: column; gap: 20px;">

            <!-- Era Banner & Primary Links -->

            <div style="background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(0,0,0,0.6)); border: 2px solid var(--nes-gold); padding: 20px; box-shadow: 4px 4px 0 #000;">

              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">

                <div>

                  <div style="font-size: 11px; font-family: var(--font-mono); color: var(--nes-gold); font-weight: 800; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px;">

                    📜 ЛЕТОПИСЬ СПЕЦТУРНИРА

                  </div>

                  <div style="font-family: var(--font-title); font-size: 20px; color: #fff; margin-bottom: 8px;">

                    ${t.title} (${t.season_year || t.year || ''})

                  </div>

                  <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: #cbd5e1;">

                    <span>Категория: <strong style="color: var(--nes-gold);">${t.category}</strong></span>

                    <span>Формат: <strong style="color: var(--nes-cyan);">${t.format}</strong></span>

                    <span>Дисциплина: <strong style="color: #fff;">${t.game}</strong></span>

                  </div>

                </div>

                <div style="display: flex; gap: 8px; flex-wrap: wrap;">

                  ${vkTopicUrl ? `

                    <a href="${vkTopicUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #2563eb; color: #fff; border: 1px solid #60a5fa; display: inline-flex; align-items: center; gap: 6px;">

                      💬 Тема в VK

                    </a>

                  ` : ''}

                  ${vkWallUrl ? `

                    <a href="${vkWallUrl}" target="_blank" rel="noopener noreferrer" class="nes-btn" style="text-decoration: none; font-size: 11px; padding: 6px 12px; background: #059669; color: #fff; border: 1px solid #34d399; display: inline-flex; align-items: center; gap: 6px;">

                      📰 Пост в VK

                    </a>

                  ` : ''}

                </div>

              </div>

            </div>



            <!-- Historical Chronicle Text -->

            <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 22px;">

              <div style="font-family: var(--font-title); font-size: 16px; color: var(--nes-cyan); margin-bottom: 14px;">

                📖 ХРОНИКА И РЕГЛАМЕНТ

              </div>

              <div style="color: #e2e8f0; font-size: 14px; line-height: 1.7; display: flex; flex-direction: column; gap: 14px;">

                ${fullChronicleParas.map(p => `<p style="margin: 0; text-align: justify;">${p}</p>`).join('')}

              </div>

            </div>



            <!-- Key Milestones -->

            ${keyEvents.length > 0 ? `

              <div style="background: rgba(0,0,0,0.35); border: 1px solid rgba(255,255,255,0.15); padding: 20px;">

                <div style="font-family: var(--font-title); font-size: 15px; color: var(--nes-gold); margin-bottom: 12px;">

                  ⚡ КЛЮЧЕВЫЕ МОМЕНТЫ ТУРНИРА

                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 10px;">

                  ${keyEvents.map(evt => `

                    <div style="background: rgba(255,255,255,0.04); border-left: 3px solid var(--nes-gold); padding: 10px 14px; font-size: 13px; color: #cbd5e1; line-height: 1.5;">

                      ${evt}

                    </div>

                  `).join('')}

                </div>

              </div>

            ` : ''}

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

              <h2 style="font-family: var(--font-title); font-size: 22px; color: #fff; margin: 0; ">

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

      if (specialSubTab === 'playoff' && specialPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('specialBracketWrapper', 'specialBracketContainer', 'specialBracketSvg'), 60);
      }

    }



    // Init

    

    



    function rememberPlayerSearch() {
      try {sessionStorage.setItem('nst-soccer-search',JSON.stringify({table:document.getElementById('tableSearch').value,cards:document.getElementById('cardsSearch').value,division:currentDivisionFilter,cardFilter:playerCardFilter}));}catch(_){}
    }
    function searchAddress(tab,inputId,filter) {
      const route=location.hash.split('?')[0]||'#/leaderboard';if(route!=='#/'+tab)return;
      const params=new URLSearchParams();const query=document.getElementById(inputId).value;if(query)params.set('q',query);params.set('filter',filter);
      history.replaceState(null,'','#/'+tab+'?'+params);
      document.querySelectorAll('#tab-'+tab+' .filter-tabs .filter-btn').forEach(el=>el.classList.toggle('active',!!el.getAttribute('onclick')?.includes("('"+filter+"',")));
    }
    function resetPlayerSearch(kind) {
      const input=document.getElementById(kind==='table'?'tableSearch':'cardsSearch');input.value='';
      const scope=document.getElementById(kind==='table'?'tab-leaderboard':'tab-players');
      const button=[...scope.querySelectorAll('.filter-btn')].find(el=>el.getAttribute('onclick')?.includes("('all',"));
      if(kind==='table')filterDivision('all',button);else filterPlayerCards('all',button);input.focus();
    }
function initPortal() {
      new MutationObserver(decorateGames).observe(document.querySelector('main'),{childList:true,subtree:true});
      document.getElementById('copyViewLink')?.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(location.href);routeNotice('Ссылка скопирована.');}catch(_){routeNotice('Скопируйте адрес из строки браузера: '+location.href);}});
      try {
        const saved=JSON.parse(sessionStorage.getItem('nst-soccer-search')||'{}');
        document.getElementById('tableSearch').value=typeof saved.table==='string'?saved.table:'';
        document.getElementById('cardsSearch').value=typeof saved.cards==='string'?saved.cards:'';
        if(['all','active','inactive','all_inactive','Высшая','Средняя','Дворовая'].includes(saved.division))currentDivisionFilter=saved.division;
        if(['all','active','hof','all_inactive','Высшая','Средняя','Дворовая'].includes(saved.cardFilter))playerCardFilter=saved.cardFilter;
        for(const [id,filter] of [['tab-leaderboard',currentDivisionFilter],['tab-players',playerCardFilter]])document.querySelectorAll('#'+id+' .filter-tabs .filter-btn').forEach(el=>el.classList.toggle('active',!!el.getAttribute('onclick')?.includes("('"+filter+"',")));
      }catch(_){}
      try { renderHud(); } catch(e) { console.error('renderHud:', e); }
      try { renderTable(); } catch(e) { console.error('renderTable:', e); }
      try { renderCards(); } catch(e) { console.error('renderCards:', e); }
      try { renderSeasonsBar(); } catch(e) { console.error('renderSeasonsBar:', e); }
      try { renderClutch(); } catch(e) { console.error('renderClutch:', e); }
      try { handleRouting(); } catch(e) { console.error('handleRouting:', e); }
    }

    if (document.readyState === 'loading') {
      window.addEventListener('DOMContentLoaded', initPortal);
    } else {
      initPortal();
    }



    
    function drawBracketConnectors(wId = 'bracketWrapper', cId = 'bracketContainer', sId = 'bracketSvg') {
      const wrapper = document.getElementById(wId);
      const container = document.getElementById(cId);
      const svg = document.getElementById(sId);
      if (!wrapper || !container || !svg) return;

      const scrollW = container.scrollWidth;
      const scrollH = container.scrollHeight;
      svg.style.width = scrollW + 'px';
      svg.style.height = scrollH + 'px';
      svg.setAttribute('width', scrollW);
      svg.setAttribute('height', scrollH);
      svg.setAttribute('viewBox', '0 0 ' + scrollW + ' ' + scrollH);

      const wrapRect = wrapper.getBoundingClientRect();
      const sLeft = wrapper.scrollLeft;
      const sTop = wrapper.scrollTop;

      const rounds = Array.from(container.querySelectorAll('.bracket-round, .bracket-champion-round'));
      if (rounds.length < 2) {
        svg.innerHTML = '';
        return;
      }

      let pathsHtml = `
        <defs>
          <filter id="bracketGlowCyan" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="2.5" flood-color="#00f0ff" flood-opacity="0.9"/>
          </filter>
          <filter id="bracketGlowGold" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="#fbbf24" flood-opacity="0.95"/>
          </filter>
          <marker id="arrowCyan" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#00f0ff" />
          </marker>
          <marker id="arrowGold" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#fbbf24" />
          </marker>
        </defs>
      `;

      for (let r = 0; r < rounds.length - 1; r++) {
        const curRound = rounds[r];
        const nextRound = rounds[r + 1];
        if (!curRound || !nextRound) continue;

        const curCards = Array.from(curRound.querySelectorAll('.bracket-match-card'));
        const nextCards = Array.from(nextRound.querySelectorAll('.bracket-match-card, .bracket-champion-box'));

        curCards.forEach(cCard => {
          const winnerRow = cCard.querySelector('.bracket-player-row.winner');
          const winnerName = winnerRow ? (winnerRow.getAttribute('data-player') || '').trim().toLowerCase() : null;
          if (!winnerName) return;

          let destEl = null;
          for (const nCard of nextCards) {
            if (nCard.classList.contains('bracket-champion-box')) {
              const cName = (nCard.getAttribute('data-player') || '').trim().toLowerCase();
              if (cName === winnerName) {
                destEl = nCard;
                break;
              }
            } else {
              const matchRow = nCard.querySelector('.bracket-player-row[data-player="' + winnerRow.getAttribute('data-player') + '"]');
              if (matchRow) {
                destEl = matchRow;
                break;
              }
            }
          }

          if (!destEl) return;

          const cRect = winnerRow.getBoundingClientRect();
          const dRect = destEl.getBoundingClientRect();

          const x1 = Math.round(cRect.right - wrapRect.left + sLeft);
          const y1 = Math.round(cRect.top + cRect.height / 2 - wrapRect.top + sTop);
          const x2 = Math.round(dRect.left - wrapRect.left + sLeft);
          const y2 = Math.round(dRect.top + dRect.height / 2 - wrapRect.top + sTop);

          const midX = Math.round(x1 + (x2 - x1) * 0.5);

          const isChamp = destEl.classList.contains('bracket-champion-box');
          const strokeColor = isChamp ? '#fbbf24' : '#00f0ff';
          const strokeWidth = isChamp ? '3' : '2.5';
          const filterId = isChamp ? 'url(#bracketGlowGold)' : 'url(#bracketGlowCyan)';
          const markerId = isChamp ? 'url(#arrowGold)' : 'url(#arrowCyan)';

          pathsHtml += `
            <path d="M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}"
                  data-player="${winnerName}"
                  class="bracket-connector-path path-player-${winnerName}"
                  fill="none"
                  stroke="${strokeColor}"
                  stroke-width="${strokeWidth}"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  marker-end="${markerId}" />
          `;
        });
      }

      svg.innerHTML = pathsHtml;
    }

    window.addEventListener('resize', () => {
      if (seasonSubTab === 'playoff' && playoffViewMode === 'bracket') {
        setTimeout(drawBracketConnectors, 40);
      }
      if (teamSubTab === 'playoff' && teamPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('teamBracketWrapper', 'teamBracketContainer', 'teamBracketSvg'), 40);
      }
      if (specialSubTab === 'playoff' && specialPlayoffViewMode === 'bracket') {
        setTimeout(() => drawBracketConnectors('specialBracketWrapper', 'specialBracketContainer', 'specialBracketSvg'), 40);
      }
    });

    let lockedBracketPlayer = null;

    function highlightPlayerBracketPath(playerName, force = false, wId = null, bId = null) {
      if (lockedBracketPlayer && !force) return;
      const pLow = (playerName || '').trim().toLowerCase();
      let wrapper = wId ? document.getElementById(wId) : null;
      let banner = bId ? document.getElementById(bId) : null;
      if (!wrapper) {
        const teamTab = document.getElementById('tab-teams');
        const specialTab = document.getElementById('tab-special');
        if (teamTab && teamTab.classList.contains('active')) {
          wrapper = document.getElementById('teamBracketWrapper');
          banner = document.getElementById('teamBracketPathBanner');
        } else if (specialTab && specialTab.classList.contains('active')) {
          wrapper = document.getElementById('specialBracketWrapper');
          banner = document.getElementById('specialBracketPathBanner');
        } else {
          wrapper = document.getElementById('bracketWrapper');
          banner = document.getElementById('bracketPathBanner');
        }
      }
      if (!wrapper || !pLow) return;

      wrapper.classList.add('has-focus');

      // Highlight / dim cards
      const cards = wrapper.querySelectorAll('.bracket-match-card');
      let playerMatchesCount = 0;
      let playerWinsCount = 0;
      let highestRound = '';
      let isChampion = false;

      cards.forEach(card => {
        const playersAttr = (card.getAttribute('data-players') || '').toLowerCase();
        if (playersAttr.includes(pLow)) {
          card.classList.add('card-focused');
          playerMatchesCount++;
          const winnerRow = card.querySelector('.bracket-player-row.winner');
          if (winnerRow && (winnerRow.getAttribute('data-player') || '').toLowerCase() === pLow) {
            playerWinsCount++;
          }
          const roundTitle = card.closest('.bracket-round') ? card.closest('.bracket-round').querySelector('.bracket-round-header') : null;
          if (roundTitle) highestRound = roundTitle.textContent.trim();
        } else {
          card.classList.remove('card-focused');
        }
      });

      // Champion box
      const champBox = wrapper.querySelector('.bracket-champion-box');
      if (champBox) {
        const champName = (champBox.getAttribute('data-player') || '').toLowerCase();
        if (champName === pLow) {
          champBox.classList.add('champ-focused');
          isChampion = true;
        } else {
          champBox.classList.remove('champ-focused');
        }
      }

      // Highlight paths
      const paths = wrapper.querySelectorAll('.bracket-connector-path');
      paths.forEach(p => {
        const pathPlayer = (p.getAttribute('data-player') || '').toLowerCase();
        if (pathPlayer === pLow) {
          p.classList.add('path-focused');
        } else {
          p.classList.remove('path-focused');
        }
      });

      // Quick chips active state
      document.querySelectorAll('.bracket-player-pill').forEach(btn => {
        if ((btn.getAttribute('data-player') || '').toLowerCase() === pLow) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });

      // Update banner text without layout shift
      if (banner) {
        let summaryText = `<div>⚡ ПУТЬ ИГРОКА В СЕТКЕ: <strong style="color: var(--nes-gold); text-transform: uppercase;">${playerName}</strong>`;
        if (isChampion) {
          summaryText += ` &bull; 👑 <span style="color: var(--nes-gold); font-weight: 800;">ОБЛАДАТЕЛЬ КУБКА</span>`;
        } else if (highestRound) {
          summaryText += ` &bull; Дошёл до: <span style="color: var(--nes-cyan); font-weight: 700;">${highestRound}</span>`;
        }
        if (lockedBracketPlayer) {
          summaryText += ` <span style="color: #4ade80; font-size: 11px; margin-left: 8px; font-weight: normal;">(зафиксировано)</span>`;
        }
        summaryText += `</div>`;
        if (lockedBracketPlayer) {
          summaryText += `<button type="button" class="banner-reset-btn" onclick="resetPlayerBracketPath()">&times; Сбросить выбор</button>`;
        }
        banner.innerHTML = summaryText;
        banner.classList.add('active');
      }
    }

    function clearPlayerBracketHighlight(wId = null, bId = null) {
      if (lockedBracketPlayer) return;
      let wrapper = wId ? document.getElementById(wId) : null;
      let banner = bId ? document.getElementById(bId) : null;
      if (!wrapper) {
        const teamTab = document.getElementById('tab-teams');
        const specialTab = document.getElementById('tab-special');
        if (teamTab && teamTab.classList.contains('active')) {
          wrapper = document.getElementById('teamBracketWrapper');
          banner = document.getElementById('teamBracketPathBanner');
        } else if (specialTab && specialTab.classList.contains('active')) {
          wrapper = document.getElementById('specialBracketWrapper');
          banner = document.getElementById('specialBracketPathBanner');
        } else {
          wrapper = document.getElementById('bracketWrapper');
          banner = document.getElementById('bracketPathBanner');
        }
      }
      if (!wrapper) return;

      wrapper.classList.remove('has-focus');
      wrapper.querySelectorAll('.card-focused').forEach(el => el.classList.remove('card-focused'));
      wrapper.querySelectorAll('.champ-focused').forEach(el => el.classList.remove('champ-focused'));
      wrapper.querySelectorAll('.path-focused').forEach(el => el.classList.remove('path-focused'));
      document.querySelectorAll('.bracket-player-pill').forEach(btn => btn.classList.remove('active'));

      if (banner) {
        banner.classList.remove('active');
        banner.innerHTML = '<span style="color: #94a3b8;">💡 Наведите на любого игрока или нажмите, чтобы проследить его путь по сетке</span>';
      }
    }

    function selectPlayerBracketPath(playerName) {
      if (lockedBracketPlayer === playerName) {
        resetPlayerBracketPath();
      } else {
        lockedBracketPlayer = playerName;
        highlightPlayerBracketPath(playerName, true);
      }
    }

    function resetPlayerBracketPath() {
      lockedBracketPlayer = null;
      clearPlayerBracketHighlight();
    }

    window.addEventListener('hashchange', handleRouting);
