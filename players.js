// Каталог игроков — общая витрина по всем дисциплинам.
// Рендерит боевые карточки из встроенного PLAYERS, поиск/сортировку/фильтр
// и досье-модалку с переходом «насквозь» в страницу дисциплины.
(function () {
  'use strict';

  const data = typeof PLAYERS !== 'undefined' ? PLAYERS : { stats: {}, disciplines: [], players: [] };
  const players = data.players || [];

  // Страницы дисциплин, куда ведёт deep-link из досье. Остальные появятся,
  // когда у дисциплины будет своя страница и реальные матчи.
  const DISCIPLINE_PAGES = {
    soccer: { page: 'soccer.html', label: 'футбол' },
  };

  const state = { disc: 'all', query: '', sort: 'matches' };
  try {Object.assign(state,JSON.parse(sessionStorage.getItem('nst-catalog-view')||'{}'));}catch(_){}
  if(typeof state.query!=='string')state.query='';
  const queryParams=new URLSearchParams(location.search);
  if(queryParams.has('q'))state.query=queryParams.get('q');
  if(queryParams.has('disc'))state.disc=queryParams.get('disc');
  if(queryParams.has('sort'))state.sort=queryParams.get('sort');
  if(!(data.disciplines||[]).some(d=>d.slug===state.disc))state.disc='all';
  let lastFocused = null;
  let firstPaint = true;

  /* ---------- Утилиты ---------- */

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (ch) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
    ));
  }

  // Цвет кромки карточки по статусу: Зал славы — gold, актив — cyan,
  // ветеран — dim, прочий инактив — slate.
  function edgeColor(p) {
    if (p.is_hall_of_famer) return 'var(--gold)';
    if (p.is_active) return 'var(--cyan)';
    if (/ВЕТЕРАН/.test(p.status_badge || '')) return 'var(--dim)';
    return 'var(--slate)';
  }

  function initials(nick) {
    const clean = String(nick || '').replace(/[^\p{L}\p{N}]/gu, '');
    return clean.slice(0, 2).toUpperCase() || '?';
  }

  function formatDiff(diff) { return (diff > 0 ? '+' : '') + diff; }
  function diffClass(diff) { return diff > 0 ? 'pos' : diff < 0 ? 'neg' : 'zero'; }

  // Матчи в dataset отсортированы от новых к старым — берём первые пять.
  function recentForm(p) {
    return (p.matches || []).slice(0, 5).map((m) => m.res_type);
  }

  function disciplineCount(slug) {
    return players.filter((p) => (p.disciplines || []).some((d) => d.slug === slug)).length;
  }

  /* ---------- Сводка и фильтр дисциплин ---------- */

  function renderStats() {
    const s = data.stats || {};
    const num = (n) => Number(n || 0).toLocaleString('ru');
    document.getElementById('catalogStats').innerHTML = [
      `<div class="stat"><b class="c">${num(s.total_players)}</b> игроков</div>`,
      `<div class="stat"><b class="c">${num(s.active_players)}</b> активных</div>`,
      `<div class="stat"><b class="g">${num(s.hof_players)}</b> зал славы</div>`,
      `<div class="stat"><b class="p">${num(s.total_matches)}</b> матчей в архиве</div>`,
      `<div class="stat"><b>${num(s.disciplines_count)}</b> дисциплины</div>`,
    ].join('');
  }

  function renderDisciplineFilters() {
    const box = document.getElementById('disciplineFilters');
    const chips = [
      `<button class="disc-chip ${state.disc==='all'?'on':''}" aria-pressed="${state.disc==='all'}" data-disc="all"><span class="ic">🎮</span>Все<span class="n">${players.length}</span></button>`,
    ];
    (data.disciplines || []).forEach((d) => {
      const count = disciplineCount(d.slug);
      const soon = count === 0;
      const title = soon ? ' title="Нет реальных матчей — дисциплина появится, когда придут данные"' : '';
      chips.push(
        `<button class="disc-chip${soon ? ' soon' : ''}${state.disc===d.slug?' on':''}" aria-pressed="${state.disc===d.slug}" data-disc="${esc(d.slug)}"${soon ? ' disabled' : ''}${title}>` +
        `<span class="ic">${esc(d.icon)}</span>${esc(d.name)}<span class="n">${count}</span></button>`
      );
    });
    box.innerHTML = chips.join('');

    box.querySelectorAll('.disc-chip:not(.soon)').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.disc = btn.dataset.disc;
        box.querySelectorAll('.disc-chip').forEach((b) => { b.classList.remove('on'); b.setAttribute('aria-pressed','false'); });
        btn.classList.add('on'); btn.setAttribute('aria-pressed','true');
        renderGrid();
      });
    });
  }

  /* ---------- Выборка: фильтр + поиск + сортировка ---------- */

  const SORTERS = {
    wr: (a, b) => b.career.win_rate - a.career.win_rate || b.career.matches - a.career.matches,
    matches: (a, b) => b.career.matches - a.career.matches,
    wins: (a, b) => b.career.wins - a.career.wins,
    name: (a, b) => a.nick.localeCompare(b.nick, 'ru'),
  };

  function visiblePlayers() {
    let list = players.slice();
    if (state.disc !== 'all') {
      list = list.filter((p) => (p.disciplines || []).some((d) => d.slug === state.disc));
    }
    if (state.query) {
      const q = state.query.trim().toLowerCase();
      list = list.filter((p) => [p.nick,p.vk_name,...(p.aliases||[])].some(name=>String(name||'').toLowerCase().includes(q)));
    }
    list.sort(SORTERS[state.sort] || SORTERS.wr);
    return list;
  }

  /* ---------- Карточка ---------- */

  // Точки формы: старые слева, свежий справа; недостающие слоты пустые.
  function formDots(form) {
    const labels = { win: 'победа', draw: 'ничья', loss: 'поражение' };
    const slots = form.slice().reverse().map((r) => `<span class="dot ${esc(r)}" title="${labels[r] || ''}"></span>`);
    while (slots.length < 5) slots.unshift('<span class="dot"></span>');
    return slots.join('');
  }

  function cardHTML(p, index, animate) {
    const c = p.career || { matches: 0, wins: 0, draws: 0, losses: 0, win_rate: 0, goals_for: 0, goals_against: 0, goal_diff: 0 };
    const edge = edgeColor(p);
    const total = c.matches || 1;
    const winPct = (c.wins / total) * 100;
    const drawPct = (c.draws / total) * 100;
    const lossPct = (c.losses / total) * 100;
    const icon = (p.disciplines && p.disciplines[0] && p.disciplines[0].icon) || '🎮';

    const discChips = (p.disciplines || []).map((d) =>
      `<span class="dchip" title="${esc(d.name)}"><span class="ic">${esc(d.icon)}</span><b>${d.matches}</b></span>`
    ).join('');

    const foot = p.soccer_elo
      ? `<span class="elo">ELO ${Math.round(p.soccer_elo)}</span>` + (p.soccer_league ? `<span class="league">${esc(p.soccer_league)}</span>` : '')
      : `<span class="league">${esc(p.soccer_league || 'без рейтинга')}</span>`;

    const vkLine = p.vk_name && p.vk_name !== p.nick ? esc(p.vk_name) : '';
    const tournaments = (p.tournaments || []).length;
    const enterClass = animate ? ' enter' : '';
    const delay = animate ? ` style="--edge:${edge};animation-delay:${Math.min(index, 11) * 45}ms"` : ` style="--edge:${edge}"`;

    return `<article class="pcard${enterClass}"${delay} data-nick="${esc(p.nick)}" tabindex="0" role="button" aria-label="Досье ${esc(p.nick)}">
      <div class="pc-head">
        <div class="portrait"><span class="ini">${esc(initials(p.nick))}</span><img src="${esc(p.avatar)}" alt="" loading="lazy" onerror="this.style.display='none'"></div>
        <div class="pc-name"><h3>${esc(p.nick)}</h3><div class="vk">${vkLine}</div></div>
        <span class="badge">${esc(p.status_badge)}</span>
      </div>
      <div class="rating"><div class="wr">${c.win_rate.toFixed(0)}<small>%</small></div><div class="wr-lab">побед за карьеру</div></div>
      <div class="recbar"><i class="w" style="width:${winPct}%"></i><i class="d" style="width:${drawPct}%"></i><i class="l" style="width:${lossPct}%"></i></div>
      <div class="recnums"><span class="w"><i>В</i><b>${c.wins}</b></span><span class="d"><i>Н</i><b>${c.draws}</b></span><span class="l"><i>П</i><b>${c.losses}</b></span></div>
      <div class="metarow"><span class="goals">${esc(icon)} <b>${c.goals_for}</b>:<b>${c.goals_against}</b> <span class="diff ${diffClass(c.goal_diff)}">(${formatDiff(c.goal_diff)})</span></span><span class="tour">🏆 <b>${tournaments}</b></span></div>
      <div class="discrow">${discChips}</div>
      <div class="formrow"><span class="lab">Форма</span><span class="dots">${formDots(recentForm(p))}</span></div>
      <div class="pc-foot">${foot}</div>
      ${p.featured_quote ? `<div class="quote">«${esc(p.featured_quote)}»</div>` : ''}
      <span class="hint">Открыть досье ↗</span>
    </article>`;
  }

  function renderGrid() {
    const address=new URL(location.href);for(const [key,value,fallback] of [['q',state.query,''],['disc',state.disc,'all'],['sort',state.sort,'matches']]){if(value===fallback)address.searchParams.delete(key);else address.searchParams.set(key,value);}history.replaceState(null,'',address);
    try{sessionStorage.setItem('nst-catalog-view',JSON.stringify(state));}catch(_){}
    const list = visiblePlayers();
    const animate = firstPaint;
    firstPaint = false;
    const grid = document.getElementById('playersGrid');
    grid.innerHTML = list.length
      ? list.map((p, i) => cardHTML(p, i, animate)).join('')
      : '<div class="empty">Игроки не найдены. Проверьте ник или алиас и выбранную дисциплину. <button type="button" id="emptyReset">Сбросить поиск и фильтр</button></div>';
    document.getElementById('emptyReset')?.addEventListener('click',resetSearch);
    document.getElementById('catalogCount').innerHTML = `показано <b>${list.length}</b> из ${players.length}`;

    grid.querySelectorAll('.pcard').forEach((el) => {
      const open = () => openDossier(el.dataset.nick);
      el.addEventListener('click', open);
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); }
      });
    });
  }

  /* ---------- Досье-модалка ---------- */

  function disciplineRow(d) {
    const extra = d.elo ? ` · ELO ${Math.round(d.elo)}${d.league ? ' · ' + esc(d.league) : ''}` : '';
    return `<div class="dossier-disc">
      <span class="ic">${esc(d.icon)}</span>
      <div class="nm"><b>${esc(d.name)}</b><span>${d.matches} матчей · винрейт ${d.win_rate}%${extra}</span></div>
      <div class="st"><b>${d.win_rate}%</b><br>${d.matches} игр</div>
    </div>`;
  }

  function rivalBlock(r) {
    if (!r) return '';
    return `<div class="dossier-sec">Главный соперник</div>
      <div class="rival"><span class="vs">VS</span><div class="rn"><b>${esc(r.nick)}</b><span>${r.matches} личных встреч</span></div><div class="h2h"><b>${r.wins}</b>–${r.draws}–<b>${r.losses}</b></div></div>`;
  }

  // Кнопки «насквозь в дисциплину»: только для дисциплин с готовой страницей.
  function disciplineLinks(p) {
    return (p.disciplines || [])
      .filter((d) => DISCIPLINE_PAGES[d.slug])
      .map((d) => {
        const target = DISCIPLINE_PAGES[d.slug];
        const href = `${target.page}#/player/${encodeURIComponent(p.nick)}`;
        return `<a class="btn primary" href="${href}">Перейти в ${esc(target.label)} ↗</a>`;
      }).join('');
  }

  function openDossier(nick) {
    const p = players.find((x) => x.nick === nick);
    if (!p) return;
    const c = p.career || {};
    const edge = edgeColor(p);
    const rival = (p.top_rivals || [])[0];
    const eloLine = p.soccer_elo ? ` · ELO ${Math.round(p.soccer_elo)} (пик ${Math.round(p.soccer_peak_elo || p.soccer_elo)})` : '';
    const links = disciplineLinks(p);

    const modal = document.getElementById('dossierModal');
    modal.innerHTML = `<div class="dossier-in" style="--edge:${edge}">
      <button class="dossier-close" id="dossierClose" aria-label="Закрыть">✕</button>
      <div class="dossier-head">
        <div class="dossier-portrait"><span class="ini">${esc(initials(p.nick))}</span><img src="${esc(p.avatar)}" alt="" onerror="this.style.display='none'"></div>
        <div><h2 id="dossierTitle">${esc(p.nick)}</h2><div class="vk">${esc(p.vk_name)}${eloLine}</div><span class="badge">${esc(p.status_badge)}</span></div>
      </div>
      <div class="dossier-sec">Карьера · все дисциплины</div>
      <div class="dossier-career">
        <div class="dossier-cell hero"><div class="v">${(c.win_rate || 0).toFixed(0)}%</div><div class="k">винрейт</div></div>
        <div class="dossier-cell"><div class="v">${c.matches || 0}</div><div class="k">матчей</div></div>
        <div class="dossier-cell"><div class="v" style="color:var(--green)">${c.wins || 0}</div><div class="k">побед</div></div>
        <div class="dossier-cell"><div class="v" style="color:var(--red)">${c.losses || 0}</div><div class="k">поражений</div></div>
      </div>
      <div class="dossier-sec">Где играет</div>
      ${(p.disciplines || []).map(disciplineRow).join('')}
      ${rivalBlock(rival)}
      ${p.featured_quote ? `<div class="dossier-sec">Цитата</div><div class="dossier-quote">«${esc(p.featured_quote)}»</div>` : ''}
      <div class="dossier-actions">${links}<button class="btn" id="dossierClose2">Закрыть</button></div>
      ${links ? '' : '<div class="dossier-note">У этой дисциплины пока нет отдельной страницы — переход появится, когда она будет готова.</div>'}
    </div>`;

    lastFocused = document.activeElement;
    const scrim = document.getElementById('dossierScrim');
    scrim.classList.add('open');
    modal.scrollTop = 0;
    document.body.style.overflow = 'hidden';
    document.querySelector('.catalog-wrap').inert = true;
    document.getElementById('dossierClose').addEventListener('click', closeDossier);
    document.getElementById('dossierClose2').addEventListener('click', closeDossier);
    modal.addEventListener('keydown', trapFocus);
    document.getElementById('dossierClose').focus();
  }

  // Tab циклически ходит только по фокусируемым элементам досье.
  function trapFocus(e) {
    if (e.key !== 'Tab') return;
    const items = Array.from(document.getElementById('dossierModal')
      .querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'));
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  function closeDossier() {
    document.getElementById('dossierScrim').classList.remove('open');
    document.getElementById('dossierModal').removeEventListener('keydown', trapFocus);
    document.querySelector('.catalog-wrap').inert = false;
    document.body.style.overflow = '';
    if (lastFocused && lastFocused.isConnected) lastFocused.focus();
  }

  /* ---------- Инициализация ---------- */

  function resetSearch() {state.query='';state.disc='all';document.getElementById('playerSearch').value='';renderDisciplineFilters();renderGrid();document.getElementById('playerSearch').focus();}
  document.getElementById('playerSearch').value=state.query;
  document.getElementById('playerSort').value=SORTERS[state.sort]?state.sort:'matches';
  document.getElementById('playerSearchReset')?.addEventListener('click',resetSearch);

  document.getElementById('playerSearch').addEventListener('input', (e) => {
    state.query = e.target.value;
    renderGrid();
  });
  document.getElementById('playerSort').addEventListener('change', (e) => {
    state.sort = e.target.value;
    renderGrid();
  });
  document.getElementById('dossierScrim').addEventListener('click', (e) => {
    if (e.target.id === 'dossierScrim') closeDossier();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && document.getElementById('dossierScrim').classList.contains('open')) closeDossier();
  });

  renderStats();
  renderDisciplineFilters();
  renderGrid();
})();
