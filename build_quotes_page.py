import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("nst_quotes.json", "r", encoding="utf-8") as f:
    quotes = json.load(f)

with open("player_avatars.json", "r", encoding="utf-8") as f:
    avatars_raw = json.load(f)

avatars = {}
for k, v in avatars_raw.items():
    avatars[k.lower()] = v

quotes_json = json.dumps(quotes, ensure_ascii=False)
avatars_json = json.dumps(avatars, ensure_ascii=False)

html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Золотой Цитатник Сообщества NEKKETSU (407 цитат) • Альманах</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Rubik:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400&family=JetBrains+Mono:wght@600;700;800&family=Russo+One&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="audio-player.css">
  <style>
    :root {{
      --nes-bg: #091728;
      --nes-bg-dark: #050d18;
      --nes-card-bg: #0d1e32;
      --nes-panel-border: 1px solid #234568;
      --nes-gold: #ffcb05;
      --nes-cyan: #38bdf8;
      --nes-green: #22c55e;
      --nes-red: #f43f5e;
      --nes-purple: #c084fc;
      --font-title: 'Russo One', sans-serif;
      --font-body: 'Rubik', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      text-shadow: none !important;
    }}

    /* Custom Slim Clean Scrollbars */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: #050d18; }}
    ::-webkit-scrollbar-thumb {{
      background: #234568;
      border-radius: 4px;
      border: 1px solid rgba(255,255,255,0.12);
    }}
    ::-webkit-scrollbar-thumb:hover {{ background: #38bdf8; }}

    body {{
      background-color: var(--nes-bg);
      color: #f8fafc;
      font-family: var(--font-body);
      font-size: 15px;
      line-height: 1.55;
      background-image: 
        radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.12) 0%, transparent 60%),
        linear-gradient(rgba(0,0,0,0.15) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,0.15) 1px, transparent 1px);
      background-size: 100% 100%, 36px 36px, 36px 36px;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }}

    header {{
      background: #06111e;
      border-bottom: 2px solid #1e3a58;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 4px 20px rgba(0,0,0,0.6);
    }}
    .header-inner {{
      max-width: 1820px;
      margin: 0 auto;
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
    }}
    .logo-block {{
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
    }}
    .logo-badge {{
      background: var(--nes-gold);
      color: #000000;
      font-family: var(--font-title);
      font-size: 18px;
      padding: 5px 12px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 1px;
      font-weight: 900;
    }}
    .logo-text h1 {{
      font-family: var(--font-title);
      font-size: 18px;
      color: #ffffff;
      letter-spacing: 0.5px;
    }}
    .logo-text p {{
      font-size: 11px;
      color: var(--nes-gold);
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .nav-link-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #ffffff;
      font-family: var(--font-body);
      font-size: 12px;
      font-weight: 700;
      padding: 6px 14px;
      border-radius: 4px;
      text-decoration: none;
      transition: all 0.15s ease;
      cursor: pointer;
    }}
    .nav-link-btn:hover {{
      background: rgba(255, 203, 5, 0.15);
      border-color: var(--nes-gold);
      color: var(--nes-gold);
    }}
    .nav-link-btn.primary {{
      background: #2787f5;
      border-color: #2787f5;
      color: #ffffff;
    }}
    .nav-link-btn.primary:hover {{
      background: #1971d2;
    }}
    .nav-link-btn.gold {{
      background: rgba(255, 203, 5, 0.15);
      border-color: var(--nes-gold);
      color: var(--nes-gold);
    }}

    .container {{
      max-width: 1820px;
      margin: 0 auto;
      padding: 24px;
      width: 100%;
      flex: 1;
    }}

    /* Random Quote Hero Card */
    .random-hero {{
      background: #0d1e32;
      border: 2px solid var(--nes-gold);
      box-shadow: 0 8px 30px rgba(0,0,0,0.6);
      border-radius: 8px;
      padding: 20px 24px;
      margin-bottom: 24px;
    }}
    .random-hero-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .random-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--nes-gold);
      color: #000;
      font-family: var(--font-title);
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }}
    .random-quote-text {{
      font-size: 16px;
      font-style: italic;
      color: #ffffff;
      line-height: 1.6;
      background: #081729;
      border-left: 5px solid var(--nes-gold);
      padding: 14px 20px;
      border-radius: 4px;
      margin-bottom: 14px;
      white-space: pre-line;
      box-shadow: inset 0 2px 8px rgba(0,0,0,0.5);
    }}
    .random-quote-author {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}

    /* Toolbar */
    .toolbar {{
      background: #0c1e32;
      border: 1px solid #1a334e;
      border-radius: 8px;
      padding: 14px 18px;
      margin-bottom: 18px;
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
    }}
    .search-input-box {{
      display: flex;
      align-items: center;
      background: #06111d;
      border: 1px solid #234568;
      border-radius: 4px;
      padding: 8px 14px;
      flex: 1;
      min-width: 260px;
      gap: 8px;
    }}
    .search-input-box input {{
      background: none;
      border: none;
      color: #fff;
      font-family: var(--font-body);
      font-size: 14px;
      width: 100%;
      outline: none;
    }}
    .search-input-box input::placeholder {{
      color: #64748b;
    }}

    .author-select {{
      background: #06111d;
      border: 1px solid #234568;
      border-radius: 4px;
      color: #fff;
      font-family: var(--font-body);
      font-size: 13px;
      padding: 8px 12px;
      outline: none;
      cursor: pointer;
      min-width: 200px;
    }}

    .authors-chips {{
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 10px;
      margin-bottom: 16px;
    }}
    .author-chip {{
      background: #0c1e32;
      border: 1px solid #1e3a58;
      color: #cbd5e1;
      font-family: var(--font-body);
      font-size: 12px;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 4px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
    }}
    .author-chip:hover, .author-chip.active {{
      background: var(--nes-gold);
      border-color: var(--nes-gold);
      color: #000;
      font-weight: 700;
    }}

    .quotes-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 14px;
    }}
    .quote-card {{
      background: #0d1e32;
      border: 1px solid #1a334e;
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: all 0.15s ease;
      box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    }}
    .quote-card:hover {{
      transform: translateY(-2px);
      border-color: var(--nes-cyan);
    }}
    .quote-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }}
    .quote-card-author {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .author-avatar {{
      width: 32px;
      height: 32px;
      border-radius: 4px;
      border: 1px solid rgba(255,255,255,0.2);
      background: #081729;
    }}
    .author-name {{
      font-size: 14px;
      font-weight: 700;
      color: #ffffff;
    }}
    .quote-id-tag {{
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 800;
      color: var(--nes-gold);
      background: #081729;
      border: 1px solid #1e3a58;
      padding: 2px 8px;
      border-radius: 4px;
    }}
    .quote-bubble {{
      font-size: 13.5px;
      color: #f1f5f9;
      line-height: 1.5;
      background: #081729;
      border-left: 3px solid var(--nes-gold);
      padding: 10px 14px;
      border-radius: 4px;
      margin-bottom: 10px;
      white-space: pre-line;
      flex: 1;
    }}
    .quote-card-actions {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid #142a42;
      padding-top: 8px;
      margin-top: 4px;
    }}
    .copy-btn {{
      background: none;
      border: 1px solid #234568;
      color: #94a3b8;
      font-family: var(--font-body);
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .copy-btn:hover {{
      background: rgba(255,255,255,0.1);
      color: #fff;
      border-color: #fff;
    }}

    footer {{
      background: #050d18;
      border-top: 1px solid #1a334e;
      padding: 16px 24px;
      text-align: center;
      font-size: 12px;
      color: #64748b;
      margin-top: 30px;
    }}
  </style>
</head>
<body data-discipline="quotes">

  <header>
    <div class="header-inner">
      <a href="index.html" class="logo-block">
        <div class="logo-badge">NST</div>
        <div class="logo-text">
          <h1>ЗОЛОТОЙ ЦИТАТНИК NEKKETSU</h1>
          <p>Архив легендарных перлов комьюнити • 407 цитат (2015–2026)</p>
        </div>
      </a>
      <div class="header-actions">
        <a href="index.html" class="nav-link-btn gold">🏛️ В Главный Альманах</a>
        <a href="soccer.html" class="nav-link-btn">⚽ Чемпионат Goal 3</a>
        <a href="https://vk.ru/nekketsu" target="_blank" class="nav-link-btn primary">VK Сообщество ↗</a>
      </div>
    </div>
  </header>

  <main class="container">

    <div class="random-hero">
      <div class="random-hero-top">
        <div class="random-badge">🎲 СЛУЧАЙНЫЙ ПЕРЛ КОМЬЮНИТИ</div>
        <button class="nav-link-btn gold" onclick="rollRandomQuote()">⚡ Крутить следующую</button>
      </div>
      <div class="random-quote-text" id="randomQuoteText">Загрузка цитаты...</div>
      <div class="random-quote-author">
        <div style="display: flex; align-items: center; gap: 10px;">
          <img id="randomQuoteAvatar" src="" class="author-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=nst'">
          <div>
            <div id="randomQuoteAuthor" style="font-weight: 700; color: #fff; font-size: 15px;"></div>
            <div id="randomQuoteId" style="font-size: 11px; color: var(--nes-gold); font-family: var(--font-mono);"></div>
          </div>
        </div>
        <button class="copy-btn" onclick="copyRandomQuote(this)">📋 Скопировать цитату</button>
      </div>
    </div>

    <div class="toolbar">
      <div class="search-input-box">
        <span>🔍</span>
        <input type="text" id="searchInput" placeholder="Поиск по тексту цитаты или автору..." oninput="handleSearch()">
      </div>
      <select id="authorSelect" class="author-select" onchange="handleAuthorChange()">
        <option value="">Все авторы (407 цитат)</option>
      </select>
    </div>

    <div class="authors-chips" id="authorChips"></div>

    <div style="font-size: 13px; color: #94a3b8; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center;">
      <span>Показано цитат: <strong id="quoteCounter" style="color: var(--nes-gold);">407</strong></span>
      <span style="font-size: 11px; color: #64748b;">Официальный архив форумов и бесед NST</span>
    </div>

    <div class="quotes-grid" id="quotesGrid"></div>

  </main>

  <footer>
    <div>Альманах киберспортивного сообщества <strong>NEKKETSU SPORTS TOURNAMENTS</strong> &bull; 2015–2026</div>
    <div style="margin-top: 6px;">
      <a href="index.html" style="color: var(--nes-gold); text-decoration: none;">На главную</a> &bull; 
      <a href="soccer.html" style="color: var(--nes-cyan); text-decoration: none;">Футбольная лига</a> &bull; 
      <a href="https://vk.ru/nekketsu" target="_blank" style="color: #60a5fa; text-decoration: none;">VK Группа</a>
    </div>
  </footer>

  <script>
    const QUOTES = {quotes_json};
    const AVATARS = {avatars_json};

    let currentFilter = {{ search: '', author: '' }};
    let currentRandom = null;

    function getAvatar(author) {{
      const low = (author || '').toLowerCase();
      if (AVATARS[low]) return AVATARS[low];
      return `https://api.dicebear.com/7.x/bottts/svg?seed=${{encodeURIComponent(author)}}`;
    }}

    function rollRandomQuote() {{
      if (!QUOTES || QUOTES.length === 0) return;
      const idx = Math.floor(Math.random() * QUOTES.length);
      currentRandom = QUOTES[idx];
      const tEl = document.getElementById('randomQuoteText');
      const aEl = document.getElementById('randomQuoteAuthor');
      const idEl = document.getElementById('randomQuoteId');
      const avEl = document.getElementById('randomQuoteAvatar');

      if (tEl) tEl.innerText = `«${{currentRandom.text}}»`;
      if (aEl) aEl.innerText = currentRandom.author;
      if (idEl) idEl.innerText = `#${{currentRandom.id}} в архиве`;
      if (avEl) avEl.src = getAvatar(currentRandom.author);
    }}

    function copyRandomQuote(btn) {{
      if (!currentRandom) return;
      const fullText = `«${{currentRandom.text}}» — ${{currentRandom.author}} [Цитата #${{currentRandom.id}}]`;
      navigator.clipboard.writeText(fullText).then(() => {{
        const old = btn.innerText;
        btn.innerText = '✅ Скопировано!';
        btn.style.color = '#22c55e';
        setTimeout(() => {{
          btn.innerText = old;
          btn.style.color = '';
        }}, 2000);
      }});
    }}

    function copyCardQuote(id, btn) {{
      const q = QUOTES.find(x => String(x.id) === String(id));
      if (!q) return;
      const fullText = `«${{q.text}}» — ${{q.author}} [Цитата #${{q.id}}]`;
      navigator.clipboard.writeText(fullText).then(() => {{
        const old = btn.innerText;
        btn.innerText = '✅ Скопировано!';
        btn.style.color = '#22c55e';
        setTimeout(() => {{
          btn.innerText = old;
          btn.style.color = '';
        }}, 2000);
      }});
    }}

    function initFilters() {{
      const authorMap = {{}};
      QUOTES.forEach(q => {{
        const a = q.author || 'Неизвестный';
        authorMap[a] = (authorMap[a] || 0) + 1;
      }});

      const sortedAuthors = Object.keys(authorMap).sort((a, b) => authorMap[b] - authorMap[a]);

      const sel = document.getElementById('authorSelect');
      sortedAuthors.forEach(a => {{
        const opt = document.createElement('option');
        opt.value = a;
        opt.textContent = `${{a}} (${{authorMap[a]}})`;
        sel.appendChild(opt);
      }});

      const chipsEl = document.getElementById('authorChips');
      const allChip = document.createElement('button');
      allChip.className = 'author-chip active';
      allChip.textContent = `Все авторы (${{QUOTES.length}})`;
      allChip.onclick = () => selectAuthorChip('');
      chipsEl.appendChild(allChip);

      sortedAuthors.slice(0, 12).forEach(a => {{
        const chip = document.createElement('button');
        chip.className = 'author-chip';
        chip.textContent = `${{a}} (${{authorMap[a]}})`;
        chip.onclick = () => selectAuthorChip(a);
        chipsEl.appendChild(chip);
      }});
    }}

    function selectAuthorChip(author) {{
      currentFilter.author = author;
      document.getElementById('authorSelect').value = author;
      document.querySelectorAll('.author-chip').forEach(c => {{
        if ((!author && c.textContent.startsWith('Все авторы')) || (author && c.textContent.startsWith(author))) {{
          c.classList.add('active');
        }} else {{
          c.classList.remove('active');
        }}
      }});
      renderQuotesGrid();
    }}

    function handleSearch() {{
      currentFilter.search = document.getElementById('searchInput').value.trim().toLowerCase();
      renderQuotesGrid();
    }}

    function handleAuthorChange() {{
      const a = document.getElementById('authorSelect').value;
      selectAuthorChip(a);
    }}

    function renderQuotesGrid() {{
      const grid = document.getElementById('quotesGrid');
      const counter = document.getElementById('quoteCounter');

      const filtered = QUOTES.filter(q => {{
        if (currentFilter.author && q.author !== currentFilter.author) return false;
        if (currentFilter.search) {{
          const tMatch = (q.text || '').toLowerCase().includes(currentFilter.search);
          const aMatch = (q.author || '').toLowerCase().includes(currentFilter.search);
          const idMatch = String(q.id) === currentFilter.search.replace('#', '');
          if (!tMatch && !aMatch && !idMatch) return false;
        }}
        return true;
      }});

      counter.innerText = filtered.length;

      if (filtered.length === 0) {{
        grid.innerHTML = `
          <div style="grid-column: 1 / -1; background: #0c1e32; border: 2px dashed #234568; border-radius: 8px; padding: 48px; text-align: center; color: #94a3b8;">
            <div style="font-size: 28px; margin-bottom: 8px;">🤔</div>
            <div style="font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 6px;">Ничего не найдено</div>
            <div style="font-size: 13px;">Попробуйте изменить поисковый запрос или выбрать другого автора.</div>
          </div>
        `;
        return;
      }}

      grid.innerHTML = filtered.map(q => {{
        const av = getAvatar(q.author);
        return `
          <div class="quote-card">
            <div>
              <div class="quote-card-header">
                <div class="quote-card-author">
                  <img src="${{av}}" class="author-avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=${{encodeURIComponent(q.author)}}'">
                  <span class="author-name">${{q.author}}</span>
                </div>
                <span class="quote-id-tag">#${{q.id}}</span>
              </div>
              <div class="quote-bubble">
                «${{q.text}}»
              </div>
            </div>
            <div class="quote-card-actions">
              <a href="soccer.html#/player/${{encodeURIComponent(q.author)}}" class="nav-link-btn" style="padding: 3px 8px; font-size: 11px;" title="Искать игрока в футбольном рейтинге">👤 Профиль</a>
              <button class="copy-btn" onclick="copyCardQuote('${{q.id}}', this)">📋 Копировать</button>
            </div>
          </div>
        `;
      }}).join('');
    }}

    window.addEventListener('DOMContentLoaded', () => {{
      initFilters();
      rollRandomQuote();
      renderQuotesGrid();
    }});
  </script>
  <!-- Persistent Audio Deck & PJAX Router -->
  <script src="audio/playlist-manifest.js"></script>
<script src="audio-player.js"></script>
</body>
</html>
"""

out_path = os.path.abspath("quotes.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Updated quotes.html with identical fonts and styling: {out_path}")
