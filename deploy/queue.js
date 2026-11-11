// queue.js — Логика кабинета лороведа и очереди задач

(() => {
  const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  const API_BASE = isLocal ? "http://127.0.0.1:8090" : "";

  const state = {
    token: sessionStorage.getItem("nstEditorToken") || localStorage.getItem("nstEditorToken") || "",
    tasks: Array.isArray(window.__INITIAL_QUEUE__) ? window.__INITIAL_QUEUE__ : [],
    filter: "all",
    search: "",
    revision: null,
    isAuthorized: false,
    busy: false,
    resolvedIds: new Set(),
  };

  const escapeHTML = value => String(value == null ? '' : value).replace(/[&<>"']/g,
    ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

  // ── Сеть и API ────────────────────────────────────────────────────────

  async function apiCall(path, body) {
    const response = await fetch(API_BASE + path, {
      method: body === undefined ? "GET" : "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + state.token,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const answer = await response.json().catch(() => ({ ok: false, error: "Сервер ответил не в формате JSON" }));
    if (!response.ok || answer.ok === false) {
      throw new Error(answer.error || ("HTTP " + response.status));
    }
    return answer;
  }

  async function checkAuth() {
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("statusText");
    const undoBtn = document.getElementById("undoLastBtn");

    if (!state.token) {
      dot.className = "status-dot offline";
      text.textContent = "🔒 Введите токен для редактирования";
      state.isAuthorized = false;
      return false;
    }

    try {
      const data = await apiCall("/api/state");
      state.isAuthorized = true;
      state.revision = data.revision;
      dot.className = "status-dot online";
      text.innerHTML = `🟢 Авторизован: <strong>Лоровед</strong> · Подключение: <strong>сервер редактора</strong> · Ревизия: <code>${escapeHTML(data.revision || "актуальна")}</code>`;
      if (undoBtn) undoBtn.disabled = !data.corrections_live;
      loadJournal();
      return true;
    } catch (err) {
      state.isAuthorized = false;
      dot.className = "status-dot offline";
      text.textContent = `❌ Ошибка доступа: ${escapeHTML(err.message)}. Проверьте токен`;
      return false;
    }
  }

  async function fetchLiveQueue() {
    const btn = document.getElementById("refreshBtn");
    if (btn) btn.disabled = true;
    try {
      showNotice("Загрузка актуальной очереди с сервера…", "info");
      const answer = await apiCall("/api/queue");
      if (Array.isArray(answer.tasks)) {
        state.tasks = answer.tasks;
        renderTabs();
        renderList();
        showNotice(`Очередь успешно обновлена с сервера (всего ${state.tasks.length} задач)`, "success");
      }
    } catch (err) {
      showNotice(`Не удалось обновить очередь с сервера: ${escapeHTML(err.message)}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function loadJournal() {
    const container = document.getElementById("journalEntries");
    const undoBtn = document.getElementById("undoLastBtn");
    if (!container) return;

    try {
      const data = await apiCall("/api/log?limit=8");
      if (!data.entries || !data.entries.length) {
        container.innerHTML = '<p class="journal-empty">В журнале пока нет записей.</p>';
        if (undoBtn) undoBtn.disabled = true;
        return;
      }

      if (undoBtn) undoBtn.disabled = false;
      container.innerHTML = data.entries.map(e => `
        <div class="journal-item">
          <div>
            <span class="time">${escapeHTML(e.created_at || "—")}</span>
            <span class="author">@${escapeHTML(e.editor || "Лоровед")}</span>:
            <strong>${escapeHTML(e.table_name || "матч")}</strong> #${escapeHTML(e.row_id)} [${escapeHTML(e.field)}]:
            <code>${escapeHTML(e.old_value !== null ? e.old_value : "—")}</code> → <strong>${escapeHTML(e.new_value !== null ? e.new_value : "—")}</strong>
          </div>
          ${e.reverted_at ? '<span style="color:var(--nes-red);font-size:11px;">отменено</span>' : ''}
        </div>
      `).join("");
    } catch (e) {
      container.innerHTML = `<p class="journal-empty" style="color:var(--nes-red)">Не удалось загрузить историю: ${escapeHTML(e.message)}</p>`;
    }
  }

  // ── Уведомления ───────────────────────────────────────────────────────

  function showNotice(msg, kind = "info") {
    const box = document.getElementById("noticeBox");
    if (!box) return;
    box.hidden = false;
    box.className = `notice-box ${kind}`;
    box.textContent = msg;
    if (kind === "success" || kind === "info") {
      setTimeout(() => { box.hidden = true; }, 6000);
    }
  }

  // ── Табы и фильтрация ─────────────────────────────────────────────────

  const BATCH_CATEGORIES = [
    { id: "all", label: "Все задачи" },
    { id: "team_archive_review", label: "👥 Командный архив" },
    { id: "lore_review_s8", label: "⭐ Рейтинг и Кубок лиг" },
    { id: "lore_review_unproven", label: "❓ Недоказанные стадии" },
    { id: "vk_live", label: "📋 Не вошедшие в сводку" },
  ];

  function getBatchCategory(batch) {
    if (batch === "team_archive_review") return "team_archive_review";
    if (!batch) return "vk_live";
    if (batch === "lore_review_s8" || batch.startsWith("lore_review_s")) return "lore_review_s8";
    if (batch === "lore_review_unproven") return "lore_review_unproven";
    return "vk_live";
  }

  function getCategoryCounts() {
    const counts = { all: state.tasks.length, lore_review_s8: 0, lore_review_unproven: 0, vk_live: 0 };
    for (const t of state.tasks) {
      const cat = getBatchCategory(t.batch);
      counts[cat] = (counts[cat] || 0) + 1;
    }
    return counts;
  }

  function renderTabs() {
    const tabsContainer = document.getElementById("queueTabs");
    const statsContainer = document.getElementById("queueStats");
    if (!tabsContainer) return;

    const counts = getCategoryCounts();
    if (statsContainer) {
      statsContainer.innerHTML = `
        <span>Задач в очереди: <strong>${counts.all}</strong></span>
        <span>•</span>
        <span>Решено в сессии: <strong>${state.resolvedIds.size}</strong></span>
        <span>•</span>
        <span>Подключение: <strong>сервер редактора</strong></span>
      `;
    }

    tabsContainer.innerHTML = BATCH_CATEGORIES.map(cat => `
      <button type="button" class="tab-btn ${state.filter === cat.id ? "active" : ""}" data-cat="${cat.id}">
        ${cat.label}
        <span class="badge">${counts[cat.id] || 0}</span>
      </button>
    `).join("");

    tabsContainer.querySelectorAll(".tab-btn").forEach(btn => {
      btn.onclick = () => {
        state.filter = btn.dataset.cat;
        renderTabs();
        renderList();
      };
    });
  }

  function getFilteredTasks() {
    return state.tasks.filter(task => {
      // Категория
      if (state.filter !== "all" && getBatchCategory(task.batch) !== state.filter) {
        return false;
      }
      // Поиск
      if (state.search) {
        const q = state.search.toLowerCase();
        const sides = (task.sides || []).join(" ").toLowerCase();
        const taskText = (task.task || "").toLowerCase();
        const doubt = (task.algorithm_doubt || "").toLowerCase();
        const tour = (task.tour || "").toLowerCase();
        const matchId = String(task.match_id || "");
        return sides.includes(q) || taskText.includes(q) || doubt.includes(q) || tour.includes(q) || matchId.includes(q);
      }
      return true;
    });
  }

  // ── Рендер карточек задач ─────────────────────────────────────────────

  function renderList() {
    const list = document.getElementById("queueList");
    const countEl = document.getElementById("queueCount");
    if (!list) return;

    const filtered = getFilteredTasks();
    if (countEl) {
      countEl.textContent = `Показано: ${filtered.length} из ${state.tasks.length}`;
    }

    if (!filtered.length) {
      list.innerHTML = `
        <div class="task-card" style="text-align:center;padding:40px 20px;">
          <h3 style="font-family:var(--font-title);color:#94a3b8;margin-bottom:8px;">Задачи не найдены</h3>
          <p style="color:#64748b;">В выбранной категории нет задач или строка поиска отфильтровала все записи.</p>
        </div>
      `;
      return;
    }

    list.innerHTML = filtered.map(task => renderTaskCard(task)).join("");
    attachCardListeners(list);
  }

  function renderTaskCard(task) {
    if (task.batch === "team_archive_review") {
      const links = (task.links || []).filter(url => /^https?:\/\//.test(url)).map(url =>
        `<a class="link-btn" href="${escapeHTML(url)}" target="_blank" rel="noopener">Источник ↗</a>`).join(' ');
      return `<article class="task-card lore-unproven" id="task-${Number(task.id)}">
        <div class="card-header"><span class="badge-tag badge-unproven">👥 Проверка командного архива</span></div>
        <div class="card-task">${escapeHTML(task.task)}</div>
        <div class="card-doubt"><strong>Что не доказано:</strong> ${escapeHTML(task.algorithm_doubt)}</div>
        <div class="card-links">${links}</div>
        <details style="margin-top:16px"><summary>Текст источника</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 var(--font-body);margin-top:12px">${escapeHTML(task.shown)}</pre></details>
        <p style="color:#cbd5e1;font-size:13px;margin-top:16px">${task.match_id ? `Связанный матч: #${Number(task.match_id)}. ` : 'Отдельная запись матча ещё не создана. '}Составы и результаты, которые не удалось доказать, не подставляются автоматически.</p>
        ${task.match_id ? `<a class="link-btn" href="soccer.html?edit=1#/teams" style="margin-top:12px">Открыть редактор командного раздела</a>` : ''}
      </article>`;
    }
    const row = task.row || {};
    const sides = task.sides || (row.players_a && row.players_b ? [row.players_a, row.players_b] : ["Сторона 1", "Сторона 2"]);
    const isResolved = state.resolvedIds.has(task.id);

    let batchClass = "lore-live";
    let badgeLabel = "📋 Не вошедший в сводку матч";
    if (task.batch === "lore_review_s8" || (task.batch && task.batch.includes("s8"))) {
      batchClass = "lore-s8";
      badgeLabel = "⭐ Рейтинг Elo · Кубок лиг";
    } else if (task.batch === "lore_review_unproven") {
      batchClass = "lore-unproven";
      badgeLabel = "❓ Лига / Тур не доказаны";
    }

    const currentScore = (row.score_a !== undefined && row.score_a !== null)
      ? `${row.score_a} : ${row.score_b}`
      : "счёт не зафиксирован";

    const linksHtml = (task.links || []).map((url, i) => {
      let label = `Первоисточник #${i + 1}`;
      if (url.includes("topic-") || url.includes("vk.com") || url.includes("vk.ru")) label = "Пост/тема ВКонтакте";
      if (url.includes("video")) label = "Видеозапись матча";
      if (url.includes("docs.google") || url.includes("spreadsheets")) label = "Google Таблица";
      return `<a href="${url}" target="_blank" rel="noopener" class="link-btn">🔗 ${label}</a>`;
    }).join(" ");

    return `
      <article class="task-card ${batchClass} ${isResolved ? "resolved" : ""}" id="task-${task.id}" data-id="${task.id}" data-match-id="${task.match_id}">
        <div class="card-header">
          <div class="card-title-group">
            <span class="badge-tag ${task.batch === 'lore_review_s8' ? 'badge-s8' : (task.batch === 'lore_review_unproven' ? 'badge-unproven' : 'badge-live')}">
              ${badgeLabel}
            </span>
            <h2 class="card-match-title">
              <span>${sides[0]}</span>
              <span class="vs">vs</span>
              <span>${sides[1]}</span>
              ${isResolved ? '<span style="color:var(--nes-green);font-size:16px;">✅ РЕШЕНО</span>' : ''}
            </h2>
          </div>
          <div class="card-meta">
            ${row.season ? `<span class="meta-pill">📅 ${row.season}</span>` : ""}
            ${row.tournament ? `<span class="meta-pill">🏆 ${row.tournament}</span>` : ""}
            ${row.stage ? `<span class="meta-pill">🎯 ${row.stage}</span>` : ""}
            <span class="meta-pill">#${task.match_id}</span>
          </div>
        </div>

        ${task.algorithm_doubt ? `
          <div class="card-doubt">
            <strong>⚠️ Сомнение алгоритма:</strong> ${task.algorithm_doubt}
          </div>
        ` : ""}

        <div class="card-task">
          <strong>💡 Что проверить лороведу:</strong> ${task.task}
        </div>

        <div class="card-current-state">
          <div class="state-item"><strong>В базе сейчас:</strong> ${currentScore}</div>
          <div class="state-item"><strong>Статус:</strong> ${row.status || "played"}</div>
          ${row.phase ? `<div class="state-item"><strong>Фаза:</strong> ${row.phase}</div>` : ""}
          ${row.source ? `<div class="state-item"><strong>Источник:</strong> ${row.source}</div>` : ""}
        </div>

        ${linksHtml ? `
          <div class="card-links">
            <strong>Ссылки на доказательства:</strong>
            ${linksHtml}
          </div>
        ` : ""}

        <!-- Блок решения лороведа -->
        <div class="decision-box">
          <div class="decision-header">
            <span>✏️ Внести вердикт лороведа в летопись</span>
            <span style="font-size:11px;color:#64748b;">Матч #${task.match_id}</span>
          </div>

          <form class="decision-form" data-match-id="${task.match_id}" data-task-id="${task.id}">
            <div class="form-grid">
              <div class="form-group">
                <label>Счёт встречи (${sides[0]} : ${sides[1]})</label>
                <div class="score-inputs">
                  <input type="number" min="0" max="99" class="input-s1" value="${row.score_a !== null && row.score_a !== undefined ? row.score_a : ""}" placeholder="0" required>
                  <span style="color:#64748b;font-weight:700;">:</span>
                  <input type="number" min="0" max="99" class="input-s2" value="${row.score_b !== null && row.score_b !== undefined ? row.score_b : ""}" placeholder="0" required>
                </div>
              </div>

              <div class="form-group">
                <label>Решение / Исход матча</label>
                <select class="input-outcome">
                  <option value="regular" ${(row.phase !== 'penalties' && row.status !== 'technical') ? 'selected' : ''}>Обычное время (по счёту)</option>
                  <option value="penalties" ${row.phase === 'penalties' ? 'selected' : ''}>Победа по пенальти / буллитам (PK)</option>
                  <option value="overtime" ${row.phase === 'overtime' ? 'selected' : ''}>Победа в овертайме (OT)</option>
                  <option value="technical" ${row.status === 'technical' ? 'selected' : ''}>Технический результат (ТП)</option>
                  <option value="void" ${row.status === 'void' ? 'selected' : ''}>Аннулировать встречу (Void)</option>
                </select>
              </div>

              ${task.batch === 'lore_review_unproven' ? `
                <div class="form-group">
                  <label>Уточнение лиги / стадии</label>
                  <input type="text" class="input-stage" value="${row.stage || task.tour || ''}" placeholder="Например: 1/4 финала">
                </div>
              ` : `
                <div class="form-group">
                  <label>Тур / Стадия</label>
                  <input type="text" class="input-stage" value="${row.stage || task.tour || ''}" placeholder="Тур или стадия">
                </div>
              `}

              <div class="form-group" style="grid-column: 1 / -1;">
                <label>Пояснение вердикта лороведа (для журнала летописи)</label>
                <input type="text" class="input-note" placeholder="Обоснование: например, 'Подтверждено видеозаписью ВК, серия буллитов 9:7'">
              </div>
            </div>

            <div class="form-actions">
              <button type="button" class="btn-save" data-action="save">💾 Записать в летопись (Neon Postgres)</button>
              <button type="button" class="btn-preview" data-action="preview">Предпросмотр дельты</button>
            </div>

            <div class="diff-preview-box" hidden></div>
          </form>
        </div>
      </article>
    `;
  }

  // ── Обработчики карточек и сохранение ─────────────────────────────────

  function attachCardListeners(root) {
    root.querySelectorAll(".decision-form").forEach(form => {
      const matchId = parseInt(form.dataset.matchId, 10);
      const taskId = parseInt(form.dataset.taskId, 10);
      const previewBox = form.querySelector(".diff-preview-box");
      const saveBtn = form.querySelector('[data-action="save"]');
      const previewBtn = form.querySelector('[data-action="preview"]');

      // Клик по предпросмотру
      previewBtn.onclick = async () => {
        try {
          previewBtn.disabled = true;
          previewBtn.textContent = "Считаем дельту…";
          const payload = collectFormData(form, matchId);
          payload.persist = false;
          payload.expect = state.revision;

          const res = await apiCall("/api/edit", payload);
          previewBox.hidden = false;
          const deltaStr = JSON.stringify(res.delta || {}, null, 2);
          previewBox.innerHTML = `
            <strong>Дельта изменений (предпросмотр):</strong>
            <pre>${deltaStr === "{}" ? "Правка не меняет видимых итоговых чисел таблицы." : escapeHTML(deltaStr)}</pre>
          `;
        } catch (err) {
          previewBox.hidden = false;
          previewBox.innerHTML = `<span style="color:var(--nes-red);">Ошибка предпросмотра: ${escapeHTML(err.message)}</span>`;
        } finally {
          previewBtn.disabled = false;
          previewBtn.textContent = "Предпросмотр дельты";
        }
      };

      // Клик по сохранению
      saveBtn.onclick = async () => {
        if (!state.isAuthorized) {
          alert("Сначала введите токен редактора в верхней панели!");
          document.getElementById("tokenInput")?.focus();
          return;
        }

        const confirmMsg = `Записать вердикт лороведа по матчу #${matchId} в облачную базу Neon Postgres?`;
        if (!confirm(confirmMsg)) return;

        try {
          saveBtn.disabled = true;
          saveBtn.textContent = "Записываем в Neon…";
          const payload = collectFormData(form, matchId);
          payload.persist = true;
          payload.expect = state.revision;

          const res = await apiCall("/api/edit", payload);
          state.revision = res.revision;
          state.resolvedIds.add(taskId);

          showNotice(`✅ Вердикт по матчу #${matchId} успешно сохранён в Neon Postgres! Новая ревизия: ${res.revision}`, "success");

          // Отмечаем карточку как решённую
          const card = document.getElementById(`task-${taskId}`);
          if (card) {
            card.classList.add("resolved");
            const titleEl = card.querySelector(".card-match-title");
            if (titleEl && !titleEl.innerHTML.includes("РЕШЕНО")) {
              titleEl.insertAdjacentHTML("beforeend", '<span style="color:var(--nes-green);font-size:16px;margin-left:10px;">✅ РЕШЕНО</span>');
            }
          }

          loadJournal();
          checkAuth();
        } catch (err) {
          alert(`Не удалось сохранить вердикт: ${escapeHTML(err.message)}`);
          showNotice(`Ошибка записи: ${escapeHTML(err.message)}`, "error");
        } finally {
          saveBtn.disabled = false;
          saveBtn.textContent = "💾 Записать в летопись (Neon Postgres)";
        }
      };
    });
  }

  function collectFormData(form, matchId) {
    const s1 = parseInt(form.querySelector(".input-s1").value, 10);
    const s2 = parseInt(form.querySelector(".input-s2").value, 10);
    const outcome = form.querySelector(".input-outcome").value;
    const stage = form.querySelector(".input-stage")?.value?.trim() || "";
    const note = form.querySelector(".input-note")?.value?.trim() || "";

    if (isNaN(s1) || isNaN(s2) || s1 < 0 || s2 < 0) {
      throw new Error("Укажите корректный неотрицательный счёт обеих сторон!");
    }

    if (outcome === "void") {
      return { operation: "void", args: { match_id: matchId, reason: note || "Аннулировано лороведом" } };
    }

    return {
      operation: "set-score",
      args: { match_id: matchId, s1, s2 },
    };
  }

  // ── Инициализация ─────────────────────────────────────────────────────

  function init() {
    const tokenInput = document.getElementById("tokenInput");
    const loginBtn = document.getElementById("loginBtn");
    const searchInput = document.getElementById("queueSearch");
    const refreshBtn = document.getElementById("refreshBtn");
    const undoBtn = document.getElementById("undoLastBtn");

    if (tokenInput) {
      tokenInput.value = state.token;
      tokenInput.onkeydown = (e) => {
        if (e.key === "Enter") loginBtn.click();
      };
    }

    if (loginBtn) {
      loginBtn.onclick = () => {
        const val = tokenInput.value.trim();
        state.token = val;
        sessionStorage.setItem("nstEditorToken", val);
        localStorage.setItem("nstEditorToken", val);
        checkAuth();
      };
    }

    if (searchInput) {
      searchInput.oninput = (e) => {
        state.search = e.target.value.trim();
        renderList();
      };
    }

    if (refreshBtn) {
      refreshBtn.onclick = fetchLiveQueue;
    }

    if (undoBtn) {
      undoBtn.onclick = async () => {
        if (!confirm("Откатить последнее совершённое изменение в базе данных?")) return;
        try {
          undoBtn.disabled = true;
          undoBtn.textContent = "Откатываем…";
          const res = await apiCall("/api/edit", {
            operation: "undo",
            args: { what: "last" },
            persist: true,
            expect: state.revision,
          });
          state.revision = res.revision;
          showNotice(`↩️ Последняя операция успешно отменена в базе! Новая ревизия: ${res.revision}`, "success");
          loadJournal();
          checkAuth();
          fetchLiveQueue();
        } catch (err) {
          alert(`Не удалось отменить: ${escapeHTML(err.message)}`);
        } finally {
          undoBtn.disabled = false;
          undoBtn.textContent = "↩️ Откатить последнее решение";
        }
      };
    }

    renderTabs();
    renderList();
    checkAuth();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
