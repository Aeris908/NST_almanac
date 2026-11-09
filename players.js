// Каталог игроков — выпускной альбом: рендер сетки карточек из встроенного PLAYERS.
(function () {
  const data = typeof PLAYERS !== 'undefined' ? PLAYERS : { players: [] };
  const players = data.players || [];
  const grid = document.getElementById('playersGrid');
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function disciplinesLine(p) {
    return (p.disciplines || []).map((d) => `${d.icon || ''} ${d.name || d.slug}`.trim()).join(' • ');
  }

  function badge(p) {
    if (p.is_hall_of_famer) return '<span class="album-badge hall">Зал славы</span>';
    if (p.is_active) return '<span class="album-badge active">Активен</span>';
    return '<span class="album-badge">Ветеран</span>';
  }

  function card(p) {
    const career = p.career || { wins: 0, matches: 0 };
    const quote = p.featured_quote ? `<p class="album-quote">«${esc(p.featured_quote)}»</p>` : '';
    return `<article class="album-card">
      <div class="album-photo"><img src="${esc(p.avatar)}" alt="${esc(p.nick)}" loading="lazy"></div>
      <h3 class="album-name">${esc(p.nick)}</h3>
      ${badge(p)}
      <p class="album-disc">${esc(disciplinesLine(p))}</p>
      ${quote}
      <p class="album-stats">${career.wins} побед • ${career.matches} матчей</p>
    </article>`;
  }

  if (grid) grid.innerHTML = players.map(card).join('');
  const count = document.getElementById('playersCount');
  if (count) count.textContent = players.length;
})();