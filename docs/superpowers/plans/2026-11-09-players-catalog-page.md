# Страница каталога игроков — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Самодостаточная страница `players.html` — плейсхолдер «школьный выпускной альбом» с реальными игроками из `build_players_dataset`, ссылка только с лендинг-хаба.

**Architecture:** Новый шаблон `templates/players_page.html` + собственные `players.css`/`players.js` (не связаны с soccer.css). Сборка `build_players_page.py` рендерит шаблон через `portal/templates.render`, встраивая JSON каталога как `const PLAYERS`. Интеграция в `build_all.py` (BUILDERS/PAGES/ASSETS) и одна ссылка в `templates/landing_page.html`.

**Tech Stack:** Python 3.15 (stdlib), SQLite, pytest, ruff; статичные HTML/CSS/JS; Google Fonts (кириллица); аудио-дека сайта.

**Spec:** `docs/superpowers/specs/2026-11-09-players-catalog-page-design.md`

## Global Constraints

- Русский язык в коде, комментариях, коммитах, сообщениях.
- `ruff format` НЕ запускать; счётчики `ruff check` не наращивать.
- Не нарушать существующие страницы: soccer/quotes не трогаем; ссылка только с хаба.
- Секреты/временные файлы не коммитить; спека и план вне git (дерево отдаётся сайтом).
- База читается через шлюз `db/store.py`; структурные правки воспроизводимы сборкой.
- TDD: сначала красный тест, затем минимальная реализация.
- Push — только по явной просьбе владельца.
- Данные — чистый архив (`build_players_dataset` уже исключает демо и дубли).

## Структура файлов

| Файл | Ответственность |
|---|---|
| `build_players_page.py` (create) | сборка страницы: dataset → render → players.html |
| `templates/players_page.html` (create) | шаблон: голова, обложка, сетка, подвал, хвост скриптов |
| `players.css` (create) | стиль альбома (самодостаточный) |
| `players.js` (create) | рендер сетки карточек из PLAYERS |
| `tests/test_players_page.py` (create) | тест сборки страницы |
| `build_all.py` (modify:19–35) | шаг сборки + PAGES + ASSETS |
| `templates/landing_page.html` (modify:424–428) | ссылка на каталог в .header-actions |

---

### Task 1: Сборка страницы и шаблон

**Files:**
- Create: `build_players_page.py`
- Create: `templates/players_page.html`
- Test: `tests/test_players_page.py`

**Interfaces:**
- Consumes: `portal.players_dataset.build_players_dataset(db_path) -> {stats, disciplines, players}`; `portal.templates.render(name, values) -> str`; `db.store.DB_PATH`.
- Produces: `build_players_page.build_html(dataset) -> str`; `build_players_page.main(db_path=store.DB_PATH)` пишет `players.html`. Токен шаблона `@@PLAYERS_JSON@@`. later-задачи требуют id `playersGrid`, `playersCount` и ссылки на `players.css`/`players.js`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_players_page.py
"""Сборка страницы каталога: шаблон рендерится без маркеров, данные встроены, ассеты на месте."""
import json
import re
import shutil

import pytest

from portal.players_dataset import build_players_dataset


@pytest.fixture(scope="module")
def page_db(tmp_path_factory, source_db):
    target = tmp_path_factory.mktemp("players_page") / "nst.db"
    shutil.copy(source_db, target)
    return target


@pytest.fixture(scope="module")
def html(page_db):
    from build_players_page import build_html
    return build_html(build_players_dataset(page_db))


def test_маркеры_не_остаются(html):
    assert not re.findall(r"@@[A-Z0-9_]+@@", html)


def test_players_встроен_и_парсится(html):
    m = re.search(r"const PLAYERS = (.+);", html)
    assert m, "const PLAYERS не встроен"
    data = json.loads(m.group(1))
    assert {"stats", "disciplines", "players"} <= set(data)
    assert data["players"], "каталог пуст"


def test_ассеты_и_сетка(html):
    assert 'href="players.css"' in html
    assert 'src="players.js"' in html
    assert 'id="playersGrid"' in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_players_page.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_html' from 'build_players_page'` (модуль ещё не создан).

- [ ] **Step 3: Create the build script**

```python
# build_players_page.py
"""Build the NST player catalog page (players.html) — школьный выпускной альбом."""
import json
import sys
from pathlib import Path

from db import store
from portal.players_dataset import build_players_dataset
from portal.templates import render

sys.stdout.reconfigure(encoding="utf-8")
OUTPUT_PATH = Path("players.html")


def build_html(dataset):
    """Шаблон альбома с встроенным каталогом; render бросит KeyError на лишний маркер."""
    return render("players_page.html", {
        "PLAYERS_JSON": json.dumps(dataset, ensure_ascii=False),
    })


def main(db_path=store.DB_PATH):
    dataset = build_players_dataset(db_path)
    html = build_html(dataset)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    stats = dataset["stats"]
    print(f"Players page written to {OUTPUT_PATH.resolve()} ({len(html) / 1024:.1f} KB) | "
          f"игроков {stats['total_players']}, дисциплин {stats['disciplines_count']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create the template**

```html
<!-- templates/players_page.html -->
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Каталог игроков • Выпускной альбом NST • Альманах</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800&family=Marck+Script&family=Rubik:wght@400;500;600;700&family=JetBrains+Mono:wght@600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="audio-player.css">
  <link rel="stylesheet" href="players.css">
</head>
<body data-discipline="players">
  <header class="album-cover">
    <p class="album-kicker">NEKKETSU SPORTS TOURNAMENTS • 2015–2026</p>
    <h1>Выпускной альбом</h1>
    <p class="album-sub">Каталог игроков сообщества • <span id="playersCount">0</span> чел.</p>
    <a class="album-home" href="index.html">← На главную</a>
  </header>
  <main>
    <div class="album-grid" id="playersGrid"></div>
  </main>
  <footer class="album-footer">
    <div>Альманах киберспортивного сообщества <strong>NEKKETSU</strong> • 2015–2026</div>
    <div class="album-footer-links">
      <a href="index.html">На главную</a> •
      <a href="soccer.html">Футбольная лига</a> •
      <a href="https://vk.ru/nekketsu" target="_blank" rel="noopener">VK Группа</a>
    </div>
  </footer>
  <script>const PLAYERS = @@PLAYERS_JSON@@;</script>
  <script src="players.js"></script>
  <script src="audio/playlist-manifest.js"></script>
  <script src="audio-player.js"></script>
</body>
</html>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_players_page.py -q`
Expected: PASS (3 теста).

- [ ] **Step 6: Commit**

```bash
git add build_players_page.py templates/players_page.html tests/test_players_page.py
git commit -m "сборка страницы каталога игроков: шаблон альбома и встроенный каталог"
```

---

### Task 2: Стиль альбома и рендер сетки

**Files:**
- Create: `players.css`
- Create: `players.js`

**Interfaces:**
- Consumes: глобальный `PLAYERS` (inline-скрипт шаблона; classic-скрипты делят глобальную лексическую область, `window.PLAYERS` не используется); поля карточки `nick, avatar, status_badge, is_active, is_hall_of_famer, disciplines[{slug,name,icon}], featured_quote, career{wins,matches}`; id `playersGrid`, `playersCount`.
- Produces: карточки `.album-card` в `#playersGrid`; счётчик в `#playersCount`.

- [ ] **Step 1: Create players.css**

```css
/* Каталог игроков — «выпускной альбом». Самодостаточный стиль, не связан с soccer.css. */
:root {
  --album-paper: #f4ecd8;
  --album-paper-dark: #e7d9bd;
  --album-ink: #2b2418;
  --album-muted: #6b5d45;
  --album-accent: #8a3324;
  --album-gold: #b8860b;
  --album-frame: #fffdf7;
  --font-cover: 'Playfair Display', serif;
  --font-hand: 'Marck Script', cursive;
  --font-body: 'Rubik', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font-body);
  color: var(--album-ink);
  background: var(--album-paper);
  background-image:
    radial-gradient(circle at 20% 10%, rgba(184,134,11,0.06), transparent 40%),
    repeating-linear-gradient(0deg, rgba(0,0,0,0.015) 0 1px, transparent 1px 28px);
  line-height: 1.5;
  padding-bottom: 52px; /* фиксированная аудио-дека */
}
/* Обложка */
.album-cover { text-align: center; padding: 44px 20px 20px; }
.album-kicker { font-family: var(--font-mono); font-size: 12px; letter-spacing: 1px; color: var(--album-muted); }
.album-cover h1 { font-family: var(--font-cover); font-size: 44px; font-weight: 800; color: var(--album-accent); margin: 6px 0; }
.album-sub { font-size: 15px; color: var(--album-muted); }
.album-home { display: inline-block; margin-top: 12px; font-size: 13px; color: var(--album-gold); text-decoration: none; }
.album-home:hover { text-decoration: underline; }
/* Сетка альбома */
.album-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 26px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 28px 24px 48px;
}
.album-card {
  background: var(--album-frame);
  border: 1px solid var(--album-paper-dark);
  border-radius: 4px;
  padding: 16px 16px 18px;
  box-shadow: 3px 3px 0 rgba(0,0,0,0.12);
  text-align: center;
}
.album-card:nth-child(odd) { transform: rotate(-0.6deg); }
.album-card:nth-child(even) { transform: rotate(0.6deg); }
.album-photo img {
  width: 100%; aspect-ratio: 1 / 1; object-fit: cover;
  border: 6px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.25);
  background: var(--album-paper-dark);
}
.album-name { font-family: var(--font-hand); font-size: 30px; color: var(--album-accent); margin: 10px 0 4px; }
.album-badge { display: inline-block; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; padding: 2px 8px; border-radius: 3px; border: 1px solid var(--album-muted); color: var(--album-muted); }
.album-badge.active { border-color: #2e7d32; color: #2e7d32; }
.album-badge.hall { border-color: var(--album-gold); color: var(--album-gold); }
.album-disc { font-size: 12px; color: var(--album-muted); margin-top: 8px; }
.album-quote { font-style: italic; font-size: 13px; color: var(--album-muted); margin: 8px 0; }
.album-stats { font-family: var(--font-mono); font-size: 12px; margin-top: 8px; }
/* Подвал */
.album-footer { text-align: center; padding: 20px; font-size: 12px; color: var(--album-muted); border-top: 1px solid var(--album-paper-dark); }
.album-footer-links { margin-top: 6px; }
.album-footer a { color: var(--album-accent); text-decoration: none; }
.album-footer a:hover { text-decoration: underline; }
```

- [ ] **Step 2: Create players.js**

```js
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
```

- [ ] **Step 3: Build the page**

Run: `python build_players_page.py`
Expected: `Players page written to ...players.html` с ненулевым числом игроков.

- [ ] **Step 4: Verify in browser (принятый в проекте способ проверки JS)**

Run (background): `python -m http.server 8099 --bind 127.0.0.1`
Затем `mcp__browser-use__navigate_page` → `http://127.0.0.1:8099/players.html`
и `mcp__browser-use__evaluate_script`:

```js
() => ({
  cards: document.querySelectorAll('.album-card').length,
  firstName: document.querySelector('.album-name')?.textContent || null,
  count: document.getElementById('playersCount')?.textContent,
  paper: getComputedStyle(document.body).backgroundColor
})
```

Expected: `cards > 0`, `firstName` непустой, `count` совпадает с cards, фон кремовый (`rgb(244, 236, 216)`). Кириллица в именах отрисована (шрифт Marck Script). Остановить сервер (TaskStop фоновой задачи).

- [ ] **Step 5: Commit**

```bash
git add players.css players.js
git commit -m "стиль выпускного альбома и рендер сетки карточек игроков"
```

---

### Task 3: Интеграция в сборку и ссылка с хаба

**Files:**
- Modify: `build_all.py:19–35`
- Modify: `templates/landing_page.html:424–428`

**Interfaces:**
- Consumes: `build_players_page.py` (Task 1), `players.html`/`players.css`/`players.js`.
- Produces: `players.html` и ассеты в `deploy/`; ссылка `👤 Каталог игроков` в шапке хаба.

- [ ] **Step 1: Add the build step and assets to build_all.py**

В `BUILDERS` после строки landing (line 28) добавить:

```python
    ("Building player catalog (players.html)", "build_players_page.py"),
```

Заменить `PAGES` и `ASSETS` (lines 34–35):

```python
PAGES = ("index.html", "soccer.html", "quotes.html", "players.html")
ASSETS = ("audio-player.js", "audio-player.css", "soccer.css", "soccer.js", "editor.js", "editor.css",
          "players.js", "players.css")
```

- [ ] **Step 2: Add the hub link**

В `templates/landing_page.html` в `.header-actions` после ссылки на quotes (line 426) добавить:

```html
        <a href="players.html" class="nav-btn-link">👤 Каталог игроков</a>
```

- [ ] **Step 3: Verify the full build and deploy**

Run: `python build_all.py --from-store`
Expected: шаг `Building player catalog (players.html)` выполнен; в конце список содержит `deploy/players.html`, `deploy/players.js`, `deploy/players.css`.

Run: `python - <<'EOF'`
```python
from pathlib import Path
assert Path("deploy/players.html").exists()
assert Path("deploy/players.js").exists()
assert Path("deploy/players.css").exists()
assert 'href="players.html"' in Path("index.html").read_text(encoding="utf-8")
print("deploy и ссылка с хаба на месте")
EOF
```
Expected: `deploy и ссылка с хаба на месте`.

- [ ] **Step 4: Commit**

```bash
git add build_all.py templates/landing_page.html players.html deploy/players.html deploy/players.js deploy/players.css deploy/index.html index.html
git commit -m "каталог игроков в сборке и deploy, ссылка с лендинг-хаба"
```

---

### Task 4: Финальная проверка

**Files:** нет новых (проверка).

- [ ] **Step 1: Full test suite**

Run: `python -m pytest -q >/dev/null 2>&1; echo EXIT=$?`
Expected: `EXIT=0`.

- [ ] **Step 2: Ruff on new files**

Run: `ruff check build_players_page.py tests/test_players_page.py`
Expected: `All checks passed!` (JS/CSS ruff не проверяет).

- [ ] **Step 3: Invariants**

Run: `python db/validate.py`
Expected: `OK: все 23 инвариантов выполнены`.

- [ ] **Step 4: End-to-end browser check from the hub**

Поднять сервер, открыть `http://127.0.0.1:8099/index.html`, кликнуть `👤 Каталог игроков` → переход на `players.html`, сетка отрисована. Проверить, что soccer.html и quotes.html не изменились (`git diff --stat HEAD~3 -- soccer.html quotes.html` пусто). Остановить сервер.

- [ ] **Step 5: Report**

Сообщить владельцу: страница готова, проверки зелёные, существующие страницы не тронуты. Push не делать.

---

## Self-Review (выполнено автором плана)

- **Покрытие спеки:** форма-сетка (Task 2), данные из каталога (Task 1), уникальный стиль альбома (Task 2 CSS), ссылка только с хаба (Task 3), интеграция сборки (Task 3), тесты/проверка (Task 1, 4), аудио-fallback (проверка в Task 2/4). Фильтры/модалка — вне объёма, задач нет (соответствует спеке).
- **Плейсхолдеры:** отсутствуют; весь код приведён.
- **Согласованность имён:** `build_html`/`main`, токен `PLAYERS_JSON`, id `playersGrid`/`playersCount`, классы `.album-*` совпадают в шаблоне, CSS и JS.