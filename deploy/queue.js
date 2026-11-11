// queue.js — Логика кабинета лороведа и очереди задач

(() => {
  const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  const API_BASE = isLocal ? "http://127.0.0.1:8090" : "";

  const state = {
    token: sessionStorage.getItem("nstEditorToken") || localStorage.getItem("nstEditorToken") || "",
    tasks: Array.isArray(window.__INITIAL_QUEUE__) ? window.__INITIAL_QUEUE__ : [],
    filter: "all",
    search: "",
    tournament:new URLSearchParams(location.search).get('tournament')||'',
    workFilter:'all',
    revision: null,
    isAuthorized: false,
    busy: false,
    resolvedIds: new Set(),
  };

  const escapeHTML = value => String(value == null ? '' : value).replace(/[&<>"']/g,
    ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

  const DRAFT_KEY = 'nst-review-drafts-v1';
  let drafts = {};
  try { drafts = JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}') || {}; } catch (_) {}
  const draftId = form => form.dataset.taskId || form.closest('article')?.id.replace('task-', '');
  const draftFields = form => [...form.querySelectorAll('input,select,textarea')];
  function writeDraft(form) {
    if (form.dataset.saved === '1') return;
    const id = draftId(form); if (!id) return;
    drafts[id] = {version:1, sourceRef:form.dataset.sourceRef, updated:Date.now(), fields:draftFields(form).map(el=>({value:el.value,checked:el.checked})),
      rows:[...form.querySelectorAll('.review-game')].map(row=>({id:row.dataset.matchId,
        common:row.dataset.useCommon,reversed:row.dataset.reversed,own:!row.querySelector('.row-player-fields').hidden}))};
    form.dataset.dirty='1';
    const status=form.querySelector('.draft-status');
    try {
      localStorage.setItem(DRAFT_KEY,JSON.stringify(drafts));
      if(status) status.textContent='Черновик сохранён в этом браузере · '+new Date().toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'});
    } catch (_) {if(status) status.textContent='Не удалось сохранить черновик в браузере. Не закрывайте страницу.';}
  }
  function clearDraft(form) {
    delete drafts[draftId(form)];form.dataset.dirty='0';form.dataset.saved='1';
    try {localStorage.setItem(DRAFT_KEY,JSON.stringify(drafts));} catch (_) {}
  }
  function restoreDraft(form) {
    const draft=drafts[draftId(form)];if(!draft || draft.version!==1 || draft.sourceRef!==form.dataset.sourceRef || !Array.isArray(draft.fields))return false;
    if(form.matches('.archive-review-form') && Array.isArray(draft.rows)) {
      form.querySelector('.review-games').innerHTML=draft.rows.map(row=>reviewGameRow({id:row.id})).join('');
      form.querySelectorAll('.review-game').forEach((row,i)=>{
        row.dataset.useCommon=draft.rows[i].common;row.dataset.reversed=draft.rows[i].reversed;
        row.querySelector('.row-player-fields').hidden=!draft.rows[i].own;
      });
    }
    draftFields(form).forEach((el,i)=>{if(draft.fields[i]){el.value=draft.fields[i].value;el.checked=!!draft.fields[i].checked;}});
    form.dataset.dirty='1';return true;
  }
  function attachDraft(form) {
    form.dataset.sourceRef=state.tasks.find(task=>String(task.id)===String(draftId(form)))?.source_ref||'';
    const status=document.createElement('p');status.className='draft-status';status.setAttribute('role','status');
    status.textContent=restoreDraft(form)?'Черновик восстановлен. Сверьте его с актуальным источником и выполните предпросмотр.':'Черновик сохраняется в этом браузере при изменении полей.';
    form.prepend(status);
    const discard=document.createElement('button');discard.type='button';discard.className='btn-preview';discard.textContent='Сбросить черновик';
    status.after(discard);
    discard.onclick=()=>{
      if(!confirm('Сбросить введённые правки этой задачи и загрузить данные заново?'))return;
      clearDraft(form);const task=state.tasks.find(t=>String(t.id)===String(draftId(form)));
      if(form.matches('.archive-review-form')&&task){const host=form.parentElement;host.replaceChildren();openReviewEditor(task,host);}else renderList();
    };
    form.addEventListener('input',()=>writeDraft(form));form.addEventListener('change',()=>writeDraft(form));
  }
  let errorSequence=0;
  function fieldError(input,message) {
    if(!input)return;
    let hint=input.parentElement.querySelector('.field-error');
    if(!hint){hint=document.createElement('span');hint.className='field-error';hint.id='field-error-'+(++errorSequence);input.after(hint);input.setAttribute('aria-describedby',hint.id);}
    hint.textContent=message;hint.hidden=!message;input.setAttribute('aria-invalid',String(!!message));input.setCustomValidity(message);
  }
  function revealError(input) {
    const own=input?.closest('.row-player-fields');if(own)own.hidden=false;
    input?.scrollIntoView({block:'center'});input?.focus();
  }
  function validateReview(form, rowNames, all=false) {
    form.querySelectorAll('input,select,textarea').forEach(input=>fieldError(input,''));
    const required=(input,message)=>{if(all&&!input.value.trim())fieldError(input,message);};
    required(form.querySelector('.review-note'),'Укажите, что проверено и какое решение принято.');
    if(form.querySelector('.review-decision').value==='save') {
      required(form.querySelector('.review-doc'),'Выберите турнир.');
      form.querySelectorAll('.review-game').forEach(row=>{
        const names=rowNames(row),seen=new Set();
        names.forEach((name,i)=>{
          const keys=['a1','a2','b1','b2'];
          const original=row.dataset.reversed==='1'?(i+2)%4:i;
          const input=row.dataset.useCommon==='1'?form.querySelector('.review-common-'+keys[original]):row.querySelector('.review-'+keys[original]);
          if(!name){if(all)fieldError(input,'Выберите игрока из подсказок.');}
          else if(seen.has(name.toLowerCase()))fieldError(input,'Этот игрок уже указан в этой игре.');
          seen.add(name.toLowerCase());
        });
        ['s1','s2'].forEach(key=>{const input=row.querySelector('.review-'+key);required(input,'Укажите число голов.');if(input.value && (!Number.isInteger(Number(input.value))||Number(input.value)<0||Number(input.value)>99))fieldError(input,'Укажите целое число от 0 до 99.');});
        const phase=row.querySelector('.review-phase').value;
        if(phase==='penalties' && row.querySelector('.review-s1').value===row.querySelector('.review-s2').value){
          ['pk1','pk2'].forEach(key=>required(row.querySelector('.review-'+key),'Укажите результат буллитов.'));
          const a=row.querySelector('.review-pk1'),b=row.querySelector('.review-pk2');
          for(const input of [a,b])if(input.value!==''&&(!Number.isInteger(Number(input.value))||Number(input.value)<0||Number(input.value)>99))fieldError(input,'Укажите целое число от 0 до 99.');
          if(a.value!==''&&b.value!==''&&Number(a.value)===Number(b.value))fieldError(b,'Счёт буллитов должен определить победителя.');
        }
        if(phase==='overtime' && row.querySelector('.review-s1').value!=='' && row.querySelector('.review-s1').value===row.querySelector('.review-s2').value)fieldError(row.querySelector('.review-s2'),'В овертайме должен быть победитель.');
      });
    }
    const invalid=form.querySelector('[aria-invalid=true]');if(invalid&&all)revealError(invalid);return !invalid;
  }
  window.addEventListener('beforeunload',event=>{
    if(document.querySelector('form[data-dirty="1"]')){event.preventDefault();event.returnValue='';}
  });

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
      const publication=document.getElementById('publicationStatus');
      if(publication)publication.textContent=data.publication_revision && window.__PUBLISHED_REVISION__===data.publication_revision
        ? 'Публикация: открытая версия сайта соответствует текущей базе.'
        : 'Публикация: в базе есть изменения, которых ещё нет в открытой версии сайта. Требуется сборка и публикация.';
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
        if (!document.querySelector(".archive-review-form")) renderList();
        showNotice(`Очередь успешно обновлена с сервера (всего ${state.tasks.length} задач)`, "success");
      }
    } catch (err) {
      showNotice(`Не удалось обновить очередь с сервера: ${escapeHTML(err.message)}`, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function journalValue(entry,value) {
    if(entry.field==='exists')return value?'Запись существует':'Записи нет';
    if(entry.table_name==='incoming' && entry.field==='payload') {
      try {return JSON.parse(value || '{}')['вердикт_редактора']?.note || 'Вердикт ещё не вынесен';} catch (_) {return 'Обновлены сведения задачи';}
    }
    return value ?? '—';
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
      if(data.operations?.length) {
        const fields={score:'Счёт',outcome:'Исход',tour:'Тур',league:'Лига',stage:'Стадия',stage_id:'Этап',phase:'Результат',note:'Примечание',verdict:'Статус задачи',payload:'Решение',manual:'Ручная правка',player_id:'Игрок',exists:'Наличие записи',label:'Состав',is_playoff:'Плей-офф',source_text:'Текст источника'};
        container.innerHTML=data.operations.map(op=>`<details class="journal-operation"><summary>${escapeHTML(op.created_at)} · ${escapeHTML(op.editor)} · ${escapeHTML(op.note||'Изменение данных архива')} ${op.live?'':'· отменено'}</summary>
          <ul>${op.entries.map(e=>`<li>${escapeHTML(fields[e.field]||'Данные записи')} · #${Number(e.row_id)}: ${escapeHTML(journalValue(e,e.old_value))} → ${escapeHTML(journalValue(e,e.new_value))}</li>`).join('')}</ul>
          ${op.live?`<button type="button" class="btn-preview" data-undo-op="${escapeHTML(op.op)}">Отменить это решение</button>`:''}</details>`).join('');
        container.querySelectorAll('[data-undo-op]').forEach(button=>button.onclick=async()=>{
          if(!confirm('Отменить именно это решение и все входящие в него изменения?'))return;
          button.disabled=true;
          try {
            const current=await apiCall('/api/state');
            await apiCall('/api/edit',{operation:'undo',args:{what:'op:'+button.dataset.undoOp},persist:true,expect:current.revision});
            showNotice('Выбранное решение отменено. Обновите открытую форму перед новой правкой.','success');
            state.resolvedIds.clear();await checkAuth();await fetchLiveQueue();
          }catch(error){showNotice(error.message,'error');button.disabled=false;}
        });
        return;
      }
      container.innerHTML = data.entries.map(e => `
        <div class="journal-item">
          <div>
            <span class="time">${escapeHTML(e.created_at || "—")}</span>
            <span class="author">@${escapeHTML(e.editor || "Лоровед")}</span>:
            <strong>${escapeHTML(e.table_name || "матч")}</strong> #${escapeHTML(e.row_id)} [${escapeHTML(e.field)}]:
            <code>${escapeHTML(journalValue(e,e.old_value))}</code> → <strong>${escapeHTML(journalValue(e,e.new_value))}</strong>
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
      if(state.resolvedIds.has(task.id))return false;
      if(state.tournament && taskTournament(task)!==state.tournament)return false;
      if(state.workFilter==='draft' && (!drafts[task.id]||drafts[task.id].sourceRef!==(task.source_ref||'')))return false;
      if(state.workFilter==='no-games' && (task.review_matches?.length || task.match_id))return false;
      if(state.workFilter==='uncertain' && !task.algorithm_doubt)return false;
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
    list.querySelectorAll('.decision-form').forEach(attachDraft);
    attachCardListeners(list);
  }

  function taskTournament(task) {return task.review_doc_key || task.row?.doc_key || task.row?.tournament || '';}
  function nextTask(id) {
    const all=getFilteredTasks(), task=all.find(t=>t.id>id)||all[0];
    renderTabs();renderList();
    if(!task){showNotice('Все задачи по выбранным фильтрам решены.','success');return;}
    const card=document.getElementById('task-'+task.id);
    card?.querySelector('[data-review-open]')?.click();card?.scrollIntoView({block:'start'});
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
        <div class="review-workspace" data-pane="editor"><nav class="workspace-tabs" aria-label="Рабочая область"><button type="button" data-pane="source">Источник</button><button type="button" data-pane="editor" aria-pressed="true">Редактор</button></nav>
        <aside class="review-source"><details><summary>Текст источника</summary><pre>${escapeHTML(task.shown)}</pre></details></aside><div class="review-edit-pane">
        <p style="color:#cbd5e1;font-size:13px;margin-top:16px">${task.match_id ? `Связанный матч: #${Number(task.match_id)}. ` : 'Отдельная запись матча ещё не создана. '}Составы и результаты, которые не удалось доказать, не подставляются автоматически.</p>
        <button type="button" class="btn-preview" data-review-open="${Number(task.id)}" style="margin-top:16px">${task.match_id ? 'Редактировать игры и вынести вердикт' : 'Разобрать отчёт и добавить игры'}</button>
        <div data-review-editor="${Number(task.id)}"></div>
        </div></div>
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
                  <input aria-label="Голы первой стороны" type="number" min="0" max="99" class="input-s1" value="${row.score_a !== null && row.score_a !== undefined ? row.score_a : ""}" placeholder="0">
                  <span style="color:#64748b;font-weight:700;">:</span>
                  <input aria-label="Голы второй стороны" type="number" min="0" max="99" class="input-s2" value="${row.score_b !== null && row.score_b !== undefined ? row.score_b : ""}" placeholder="0">
                </div>
              </div>

              <div class="form-group">
                <label>Решение / Исход матча</label>
                <select class="input-outcome" aria-label="Тип результата">
                  <option value="regular" ${(!['penalties','overtime'].includes(row.phase) && !['technical','void'].includes(row.status)) ? 'selected' : ''}>Основное время (по счёту)</option>
                  <option value="penalties" ${row.phase === 'penalties' ? 'selected' : ''}>Победа по пенальти / буллитам (PK)</option>
                  <option value="overtime" ${row.phase === 'overtime' ? 'selected' : ''}>Победа в овертайме (OT)</option>
                  <option value="technical" ${row.status === 'technical' ? 'selected' : ''}>Технический результат (ТП)</option>
                  <option value="void" ${row.status === 'void' ? 'selected' : ''}>Аннулировать встречу (Void)</option>
                </select>
              </div>

              <div class="legacy-pk form-group" ${row.phase==='penalties'?'':'hidden'}><label>Буллиты первой стороны<input class="input-pk1" type="number" min="0" max="99"></label><label>Буллиты второй стороны<input class="input-pk2" type="number" min="0" max="99"></label></div>

              ${task.batch === 'lore_review_unproven' ? `
                <div class="form-group">
                  <label>Уточнение лиги / стадии</label>
                  <input type="text" class="input-stage" aria-label="Стадия матча" value="${escapeHTML(row.stage || task.tour || '')}" placeholder="Например: 1/4 финала">
                </div>
              ` : `
                <div class="form-group">
                  <label>Тур / Стадия</label>
                  <input type="text" class="input-stage" aria-label="Стадия матча" value="${escapeHTML(row.stage || task.tour || '')}" placeholder="Стадия матча">
                </div>
              `}

              <div class="form-group" style="grid-column: 1 / -1;">
                <label>Пояснение вердикта лороведа (для журнала летописи)</label>
                <input type="text" class="input-note" aria-label="Обоснование решения" required placeholder="Что проверено и какое решение принято">
              </div>
            </div>

            <div class="form-actions">
              <button type="button" class="btn-save" data-action="save" disabled>Сохранить решение</button>
              <button type="button" class="btn-preview" data-action="preview">Предпросмотр дельты</button>
            </div>

            <div class="diff-preview-box" hidden></div>
          </form>
        </div>
      </article>
    `;
  }

  // ── Обработчики карточек и сохранение ─────────────────────────────────

  let nickFieldId = 0;
  function nickField(key, label, value = '') {
    const id = 'nick-options-' + (++nickFieldId);
    return `<label class="nick-label">${label}<span class="nick-combobox"><input class="review-${key} review-player" aria-label="${escapeHTML(label)}" value="${escapeHTML(value)}" placeholder="Начните вводить ник…" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="${id}"><span class="nick-options" id="${id}" role="listbox" hidden></span></span></label>`;
  }
  function attachNickSuggestions(form) {
    const controls = new WeakMap();
    function control(input) {
      if(controls.has(input)) return controls.get(input);
      const box=input.parentElement.querySelector('.nick-options');
      const state={items:[],active:-1,request:0,timer:null};
      function close() {box.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');state.active=-1;state.request++;}
      function choose(index) {
        const player=state.items[index];if(!player)return;
        input.value=player.nick;close();input.dispatchEvent(new Event('change',{bubbles:true}));input.focus();
      }
      function highlight() {
        [...box.querySelectorAll('[role=option]')].forEach((el,i)=>el.setAttribute('aria-selected',String(i===state.active)));
        const active=box.querySelector('[aria-selected=true]');
        if(active){input.setAttribute('aria-activedescendant',active.id);active.scrollIntoView({block:'nearest'});}
      }
      async function search() {
        const request=++state.request;const query=input.value.trim();
        if(!form.isConnected || document.activeElement!==input) return;
        box.hidden=false;input.setAttribute('aria-expanded','true');box.textContent='Ищем игроков…';
        try {
          const answer=await apiCall('/api/players?q='+encodeURIComponent(query));
          if(request!==state.request || document.activeElement!==input)return;
          state.items=(answer.players||[]).slice(0,8);state.active=-1;
          box.replaceChildren();
          if(!state.items.length){box.textContent='Игрок не найден. Проверьте ник.';return;}
          state.items.forEach((player,i)=>{
            const option=document.createElement('span');option.id=box.id+'-'+i;option.setAttribute('role','option');option.setAttribute('aria-selected','false');option.textContent=player.nick;
            option.addEventListener('pointerdown',event=>{event.preventDefault();choose(i);});box.appendChild(option);
          });
        }catch(_){if(request===state.request)box.textContent='Подсказки недоступны. Проверьте вход редактора.';}
      }
      input.addEventListener('keydown',event=>{
        if(event.key==='Escape'){close();return;}
        if((event.key==='ArrowDown'||event.key==='ArrowUp')&&!box.hidden&&state.items.length){
          event.preventDefault();state.active=state.active<0?(event.key==='ArrowDown'?0:state.items.length-1):(state.active+(event.key==='ArrowDown'?1:-1)+state.items.length)%state.items.length;highlight();
        }else if(event.key==='Enter'&&!box.hidden){event.preventDefault();if(state.active>=0)choose(state.active);}
      });
      input.addEventListener('blur',close);
      const value={search,close,state};controls.set(input,value);return value;
    }
    form.addEventListener('focusin',event=>{if(event.target.matches('.review-player'))control(event.target).search();});
    form.addEventListener('input',event=>{
      if(!event.target.matches('.review-player'))return;
      const c=control(event.target);clearTimeout(c.state.timer);c.close();c.state.items=[];c.state.active=-1;
      c.state.timer=setTimeout(c.search,180);
    });
  }

  function reviewGameRow(row = {}, sides = []) {
    const names=(row.sides||[]).map(s=>s.players||'');
    const a=String(names[0]||sides[0]||'').split(' & '),b=String(names[1]||sides[1]||'').split(' & ');
    const pk=String(row.note||'').match(/\((?:ПК|PK)?\s*(\d+)\s*[:-]\s*(\d+)/i);
    return `<fieldset class="review-game" data-match-id="${row.id || ''}" data-use-common="${row.id?'0':'1'}" data-reversed="0">
      <legend>${row.id?'Игра #'+Number(row.id):'Новая игра'}</legend>
      <div class="game-pairs" aria-live="polite"></div>
      <div class="review-scoreline">
        <label>Голы A<input type="number" class="review-s1" min="0" max="99" value="${row.score_a??''}"></label><span class="score-colon">:</span>
        <label>Голы B<input type="number" class="review-s2" min="0" max="99" value="${row.score_b??''}"></label>
        <label>Результат<select class="review-phase">${[['regular','Основное время'],['overtime','Овертайм'],['penalties','Буллиты']].map(([v,t])=>`<option value="${v}"${row.phase===v?' selected':''}>${t}</option>`).join('')}</select></label>
        <label class="game-playoff"><input type="checkbox" class="review-playoff" ${row.is_playoff?'checked':''}>Плей-офф</label>
      </div>
      <div class="review-pk" ${row.phase==='penalties'?'':'hidden'}><label>Буллиты A<input type="number" class="review-pk1" min="0" max="99" value="${pk?pk[1]:''}"></label><label>Буллиты B<input type="number" class="review-pk2" min="0" max="99" value="${pk?pk[2]:''}"></label></div>
      <div class="game-tools"><button type="button" class="btn-preview" data-swap-game>⇄ Поменять пары и счёт</button><button type="button" class="btn-preview" data-own-roster>Изменить игроков этой игры</button><button type="button" class="btn-preview" data-remove-game>Убрать строку</button></div>
      <div class="row-player-fields form-grid" hidden>${nickField('a1','Игрок A1',a[0]||'')}${nickField('a2','Игрок A2',a[1]||'')}${nickField('b1','Игрок B1',b[0]||'')}${nickField('b2','Игрок B2',b[1]||'')}</div>
    </fieldset>`;
  }

  function openReviewEditor(task, host) {
    if (host.querySelector('form')) return;
    const workspace=host.closest('.review-workspace');
    if(workspace){workspace.classList.add('editing');workspace.querySelector('details').open=true;}
    const rows = task.review_matches || (task.row ? [task.row] : []);
    const first = rows[0] || {};
    host.innerHTML = `<form class="archive-review-form" data-task-id="${Number(task.id)}">
      <h3>Решение лороведа</h3><p>Сначала укажите пары, затем внесите счета игр. Ник выбирается из подсказок — сам он не заменяется.</p>
      <div class="form-grid">
      <label>Турнир<select class="review-doc" ${rows.length ? 'disabled' : ''}><option value="">Выберите турнир</option>${(task.review_documents || []).map(d=>`<option value="${escapeHTML(d.doc_key)}" ${d.doc_key === (first.doc_key || task.review_doc_key) ? 'selected' : ''}>${escapeHTML(d.title)}</option>`).join('')}</select></label>
      <label>Лига / группа<input class="review-league" value="${escapeHTML(first.league || '')}"></label>
      <label>Тур<input class="review-tour" value="${escapeHTML(first.tour || task.tour || '')}"></label>
      <label>Стадия<input class="review-stage" value="${escapeHTML(first.stage || '')}" placeholder="Групповой этап / 1/2 финала"></label>
</div>
      <section class="common-roster"><h4>Составы отчёта</h4><div class="form-grid">${nickField('common-a1','Пара A · первый игрок',String(first.players_a||first.sides?.[0]?.players||task.sides?.[0]||'').split(' & ')[0]||'')}${nickField('common-a2','Пара A · второй игрок',String(first.players_a||first.sides?.[0]?.players||task.sides?.[0]||'').split(' & ')[1]||'')}${nickField('common-b1','Пара B · первый игрок',String(first.players_b||first.sides?.[1]?.players||task.sides?.[1]||'').split(' & ')[0]||'')}${nickField('common-b2','Пара B · второй игрок',String(first.players_b||first.sides?.[1]?.players||task.sides?.[1]||'').split(' & ')[1]||'')}</div><button type="button" class="btn-preview" data-apply-roster>Применить состав ко всем играм</button></section>
      <div class="review-games">${(rows.length ? rows : [{}]).map(row=>reviewGameRow(row,task.sides)).join('')}</div>
      <button type="button" class="btn-preview" data-add-game>Добавить игру</button>
      <div class="form-grid review-verdict">      <label>Вердикт<select class="review-decision"><option value="save">Сохранить игры и закрыть задачу</option><option value="confirm">Подтвердить текущие данные без изменений</option><option value="reject">Отклонить отчёт: дубль, цитата или ошибка</option></select></label>
      <label>Обоснование вердикта<textarea class="review-note" required placeholder="Что проверено по источнику и какое решение принято"></textarea></label></div>
      <div class="form-actions"><button type="button" class="btn-preview" data-review-preview>Предпросмотр решения</button><button type="submit" class="btn-save" disabled>Сохранить решение</button></div>
      <pre class="review-result" role="status" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre>
      <p>Запись в базу и публикация сайта — разные этапы. После сохранения игры ждут следующей публикации.</p>
    </form>`;
    const form = host.querySelector('form');
    attachDraft(form);
    attachNickSuggestions(form);
    const commonNames=()=>['a1','a2','b1','b2'].map(k=>form.querySelector('.review-common-'+k).value.trim());
    const rowNames=row=>{
      let names=row.dataset.useCommon==='1'?commonNames():['a1','a2','b1','b2'].map(k=>row.querySelector('.review-'+k).value.trim());
      return row.dataset.reversed==='1'?[names[2],names[3],names[0],names[1]]:names;
    };
    function updateGames() {
      form.querySelectorAll('.review-game').forEach((row,index)=>{
        const n=rowNames(row);row.querySelector('.game-pairs').textContent=(index+1)+'. '+(n[0]||'Игрок A1')+' & '+(n[1]||'Игрок A2')+' — '+(n[2]||'Игрок B1')+' & '+(n[3]||'Игрок B2');
        row.querySelector('.review-pk').hidden=row.querySelector('.review-phase').value!=='penalties';
      });
      const editing=form.querySelector('.review-decision').value==='save';
      form.querySelector('.common-roster').hidden=!editing;form.querySelector('.review-games').hidden=!editing;form.querySelector('[data-add-game]').hidden=!editing;
    }
    updateGames();
    const output = form.querySelector('.review-result');
    const save = form.querySelector('[type=submit]');
    let previewed = null;
    let previewRevision = null;
    const value = selector => form.querySelector(selector).value.trim();
    const payload = () => {
      const decision = value('.review-decision');
      const games = decision !== 'save' ? [] : [...form.querySelectorAll('.review-game')].map(row => {
        const get = sel => row.querySelector(sel).value.trim();
        const integer = sel => get(sel) === '' ? null : Number(get(sel));
        return {match_id:row.dataset.matchId ? Number(row.dataset.matchId) : undefined,
          doc_key:value('.review-doc'), league:value('.review-league'),tour:value('.review-tour'),stage:value('.review-stage'),
          sides:[rowNames(row).slice(0,2).join(' & '),rowNames(row).slice(2).join(' & ')],
          s1:integer('.review-s1'),s2:integer('.review-s2'),pk1:integer('.review-pk1'),pk2:integer('.review-pk2'),
          phase:get('.review-phase'),playoff:row.querySelector('.review-playoff').checked};
      });
      return {task_id:task.id, decision, note:value('.review-note'), games};
    };
    form.addEventListener('input',()=>{previewed=null;save.disabled=true;updateGames();});
    form.addEventListener('change',()=>{previewed=null;save.disabled=true;updateGames();});
    form.addEventListener('focusout',async event=>{
      const input=event.target;if(!input.matches('input,select,textarea'))return;
      validateReview(form,rowNames);
      if(input.matches('.review-player')&&input.value.trim()) {
        const typed=input.value.trim();
        try {const answer=await apiCall('/api/players?q='+encodeURIComponent(typed));
          if(input.value.trim()===typed&&!answer.players.some(p=>p.nick.toLowerCase()===typed.toLowerCase()))fieldError(input,'Выберите точный ник из подсказок.');
        }catch(_){/* Сервер проверит ник при предпросмотре. */}
      }
    });
    form.addEventListener('input',event=>{if(event.target.setCustomValidity)fieldError(event.target,'');});
    form.addEventListener('click',event=>{
      const button=event.target.closest('button');if(!button)return;
      if(button.matches('[data-add-game]')) form.querySelector('.review-games').insertAdjacentHTML('beforeend',reviewGameRow());
      else if(button.matches('[data-remove-game]')) button.closest('fieldset').remove();
      else if(button.matches('[data-apply-roster]')) form.querySelectorAll('.review-game').forEach(row=>{row.dataset.useCommon='1';row.dataset.reversed='0';row.querySelector('.row-player-fields').hidden=true;});
      else if(button.matches('[data-swap-game]')) {
        const row=button.closest('fieldset');row.dataset.reversed=row.dataset.reversed==='1'?'0':'1';
        for(const [a,b] of [['s1','s2'],['pk1','pk2']]){const left=row.querySelector('.review-'+a),right=row.querySelector('.review-'+b);[left.value,right.value]=[right.value,left.value];}
      }else if(button.matches('[data-own-roster]')) {
        const row=button.closest('fieldset'),names=rowNames(row);['a1','a2','b1','b2'].forEach((k,i)=>row.querySelector('.review-'+k).value=names[i]);
        row.dataset.useCommon='0';row.dataset.reversed='0';row.querySelector('.row-player-fields').hidden=!row.querySelector('.row-player-fields').hidden;
      }else return;
      previewed=null;save.disabled=true;updateGames();writeDraft(form);
    });
    form.querySelector('[data-review-preview]').onclick=async event=>{
      if(!state.isAuthorized) {output.textContent='Введите токен редактора вверху страницы.';return;}
      if(!validateReview(form,rowNames,true)||!form.reportValidity()) return;
      const button=event.target;button.disabled=true;save.disabled=true;
      try {
        const args=payload(); const status=await apiCall('/api/state');state.revision=status.revision;
        const result=await apiCall('/api/edit',{operation:'review-task',args,persist:false,expect:status.revision});
        previewed=JSON.stringify(args); previewRevision=result.revision;
        const decisions={save:'Сохранить игры',confirm:'Подтвердить без изменений',reject:'Отклонить отчёт'};
        const lines=[decisions[args.decision], ...args.games.map((g,i)=>(i+1)+'. '+g.sides[0]+' — '+g.sides[1]+': '+g.s1+':'+g.s2+(g.phase==='penalties'&&g.pk1!==null?' (буллиты '+g.pk1+':'+g.pk2+')':''))];
        const headline=result.delta?.headline || {};
        for(const [key,label] of [['matches','Матчей в архиве'],['goals','Голов в архиве']]) if(Array.isArray(headline[key])) lines.push(label+': '+headline[key][0]+' → '+headline[key][1]);
        lines.push('Обоснование: '+args.note,'После сохранения задача будет закрыта.');
        output.textContent=lines.join('\n');
        save.disabled=false;
      } catch(error){previewed=null;output.textContent='Предпросмотр не выполнен: '+error.message;
        const nick=error.message.match(/Игрок «([^»]+)»/);
        if(nick){const input=[...form.querySelectorAll('.review-player')].find(el=>el.value.trim()===nick[1]);fieldError(input,'Игрок не найден. Выберите ник из подсказок.');revealError(input);}
      }
      finally{button.disabled=false;}
    };
    form.onsubmit=async event=>{
      event.preventDefault();const args=payload();
      if(!previewed || previewed!==JSON.stringify(args)) {save.disabled=true;output.textContent='Сначала обновите предпросмотр.';return;}
      save.disabled=true;
      try {
        const result=await apiCall('/api/edit',{operation:'review-task',args,persist:true,expect:previewRevision});
        state.revision=result.revision_after;state.resolvedIds.add(task.id);
        clearDraft(form);
        document.getElementById('publicationStatus').textContent='Сохранено в базе. Публикация: ожидает обновления сайта.';
        output.textContent='Сохранено в базе. Задача закрыта. Публикация: ожидает обновления сайта.';
        form.querySelectorAll('input,select,textarea,button').forEach(el=>el.disabled=true);
        const next=document.createElement('button');next.type='button';next.className='btn-save';next.textContent='Следующая задача';next.onclick=()=>nextTask(task.id);form.append(next);
        document.getElementById('task-'+task.id).classList.add('resolved');
        showNotice('Вердикт сохранён; публикация сайта обновит витрину.','success');loadJournal();
      } catch(error){previewed=null;output.textContent='Решение не сохранено: '+error.message+' Повторите предпросмотр.';}
    };
  }

  function attachCardListeners(root) {
    root.querySelectorAll('.workspace-tabs button').forEach(button=>button.onclick=()=>{
      const workspace=button.closest('.review-workspace');workspace.dataset.pane=button.dataset.pane;
      workspace.querySelectorAll('.workspace-tabs button').forEach(el=>el.setAttribute('aria-pressed',String(el===button)));
    });
    root.querySelectorAll('[data-review-open]').forEach(button=>button.onclick=()=>{
      const task=state.tasks.find(t=>t.id===Number(button.dataset.reviewOpen));
      if(task) openReviewEditor(task,root.querySelector('[data-review-editor="'+task.id+'"]'));
    });
    root.querySelectorAll(".decision-form").forEach(form => {
      const matchId = parseInt(form.dataset.matchId, 10);
      const taskId = parseInt(form.dataset.taskId, 10);
      const previewBox = form.querySelector(".diff-preview-box");
      const saveBtn = form.querySelector('[data-action="save"]');
      const previewBtn = form.querySelector('[data-action="preview"]');
      let approved=null, approvedRevision=null;
      const update=()=>{
        approved=null;saveBtn.disabled=true;
        form.querySelector('.legacy-pk').hidden=form.querySelector('.input-outcome').value!=='penalties';
      };
      update();
      form.addEventListener('input',update);form.addEventListener('change',update);
      form.addEventListener('focusout',event=>{if(event.target.matches('.input-s1,.input-s2')&&event.target.value&&!event.target.checkValidity())fieldError(event.target,'Укажите целое число от 0 до 99.');});
      form.addEventListener('input',event=>{if(event.target.setCustomValidity)fieldError(event.target,'');});

      // Клик по предпросмотру
      previewBtn.onclick = async () => {
        if(!state.isAuthorized){showNotice('Введите токен редактора вверху страницы.','error');return;}
        if(!form.reportValidity())return;
        approved=null;saveBtn.disabled=true;
        try {
          previewBtn.disabled = true;
          previewBtn.textContent = "Считаем дельту…";
          const payload = collectFormData(form, matchId);
          payload.persist = false;
          const current=await apiCall('/api/state');payload.expect = current.revision;

          const res = await apiCall("/api/edit", payload);
          approved=JSON.stringify(payload.args);approvedRevision=res.revision;saveBtn.disabled=false;
          previewBox.hidden = false;
          const args=payload.args;
          previewBox.textContent=`Матч #${matchId}: ${args.outcome==='void'?'аннулировать':args.s1+':'+args.s2+' · '+form.querySelector('.input-outcome').selectedOptions[0].textContent}\nСтадия: ${args.stage||'не указана'}\nОбоснование: ${args.note}\nПосле сохранения задача будет закрыта.`;
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

        try {
          saveBtn.disabled = true;
          saveBtn.textContent = "Записываем в Neon…";
          const payload = collectFormData(form, matchId);
          if(!approved||approved!==JSON.stringify(payload.args))throw Error('Сначала выполните предпросмотр решения.');
          payload.persist = true;
          payload.expect = approvedRevision;

          const res = await apiCall("/api/edit", payload);
          state.revision = res.revision_after || res.revision;
          state.resolvedIds.add(taskId);
          clearDraft(form);

          showNotice(`Вердикт по матчу #${matchId} сохранён в базе. Публикация ожидает обновления сайта.`, "success");
          form.querySelectorAll('input,select,textarea,button').forEach(el=>el.disabled=true);
          const next=document.createElement('button');next.type='button';next.className='btn-save';next.textContent='Следующая задача';next.onclick=()=>nextTask(taskId);form.append(next);

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
          approved=null;
          previewBox.hidden=false;previewBox.textContent='Решение не сохранено: '+err.message+' Повторите предпросмотр.';
          showNotice(`Ошибка записи: ${escapeHTML(err.message)}`, "error");
        } finally {
          saveBtn.disabled = form.dataset.saved==='1'||!approved;
          saveBtn.textContent = "Сохранить решение";
        }
      };
    });
  }

  function collectFormData(form, matchId) {
    const s1 = form.querySelector('.input-s1').value===''?NaN:Number(form.querySelector('.input-s1').value);
    const s2 = form.querySelector('.input-s2').value===''?NaN:Number(form.querySelector('.input-s2').value);
    const outcome = form.querySelector(".input-outcome").value;
    const stage = form.querySelector(".input-stage")?.value?.trim() || "";
    const note = form.querySelector(".input-note")?.value?.trim() || "";

    if (outcome!=='void' && (!Number.isInteger(s1)||!Number.isInteger(s2)||s1<0||s2<0||s1>99||s2>99)) {
      const input=form.querySelector(!Number.isInteger(s1)||s1<0||s1>99?'.input-s1':'.input-s2');fieldError(input,'Укажите целое число голов от 0 до 99.');revealError(input);
      throw new Error("Укажите корректный счёт обеих сторон.");
    }
    if(!note){const input=form.querySelector('.input-note');fieldError(input,'Укажите обоснование решения.');revealError(input);throw Error('Укажите обоснование решения.');}
    const pk1=form.querySelector('.input-pk1').value,pk2=form.querySelector('.input-pk2').value;
    if(outcome==='penalties'&&s1===s2&&(!pk1||!pk2||Number(pk1)===Number(pk2))){fieldError(form.querySelector('.input-pk2'),'Укажите разные результаты буллитов.');revealError(form.querySelector('.input-pk2'));throw Error('Проверьте результаты буллитов.');}
    return {
      operation: "review-existing",
      args: {task_id:Number(form.dataset.taskId),match_id:matchId,s1,s2,outcome,stage,note,pk1:pk1===''?null:Number(pk1),pk2:pk2===''?null:Number(pk2)},
    };
  }

  // ── Инициализация ─────────────────────────────────────────────────────

  function init() {
    const tokenInput = document.getElementById("tokenInput");
    const loginBtn = document.getElementById("loginBtn");
    const searchInput = document.getElementById("queueSearch");
    const refreshBtn = document.getElementById("refreshBtn");
    const undoBtn = document.getElementById("undoLastBtn");

    const tournament=document.getElementById('queueTournament');
    function updateTournamentOptions() {
      if(!tournament)return;
      const docs=new Map();state.tasks.forEach(task=>{
        const key=taskTournament(task);if(!key)return;
        docs.set(key,task.review_documents?.find(d=>d.doc_key===key)?.title||task.row?.tournament||key);
      });
      tournament.innerHTML='<option value="">Все турниры</option>'+[...docs].map(([key,title])=>`<option value="${escapeHTML(key)}">${escapeHTML(title)}</option>`).join('');
      tournament.value=state.tournament||'';
    }
    updateTournamentOptions();
    if(tournament)tournament.onchange=()=>{state.tournament=tournament.value;renderList();};
    const work=document.getElementById('queueWorkFilter');
    if(work)work.onchange=()=>{state.workFilter=work.value;renderList();};
    document.getElementById('queueReset')?.addEventListener('click',()=>{
      state.filter='all';state.search='';state.tournament='';state.workFilter='all';
      searchInput.value='';if(work)work.value='all';updateTournamentOptions();renderTabs();renderList();
    });

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
        checkAuth().then(ok=>{if(ok) fetchLiveQueue();});
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
    checkAuth().then(ok=>{if(ok) fetchLiveQueue();});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
