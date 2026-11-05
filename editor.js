/* Карандаши в интерфейсе летописи.
   Страница публична, поэтому этот код ничего не разрешает: он только спрашивает токен и просит
   сервер. Право писать решает `db/serve.py` (или Vercel-функция), сверяя токен редактора.
   Активируется только по `?edit=1` — без него ни одной кнопки, ни одного запроса. */

(() => {
  const params = new URLSearchParams(location.search);
  if (!params.has("edit")) return;

  const API_BASE = params.get("api")
    || document.querySelector('meta[name="nst-editor-api"]')?.content
    || "http://127.0.0.1:8090";

  const state = { token: sessionStorage.getItem("nstEditorToken") || "", revision: null, row: null,
    publish: [] };

  const el = (tag, cls, html) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html !== undefined) node.innerHTML = html;
    return node;
  };

  // Единый вход всех запросов: занятость ставится и снимается в одной точке, на любом ответе.
  async function call(path, body) {
    return pending(requestLabel(path), () => rawCall(path, body));
  }

  async function rawCall(path, body) {
    const response = await fetch(API_BASE + path, {
      method: body === undefined ? "GET" : "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + state.token },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const answer = await response.json().catch(() => ({ ok: false, error: "сервер ответил не JSON" }));
    if (!response.ok || answer.ok === false) throw new Error(answer.error || ("HTTP " + response.status));
    return answer;
  }

  /* ── панель ─────────────────────────────────────────────────────────── */

  const bar = el("div", "nst-edit-bar");
  const panel = el("div", "nst-edit-panel");
  panel.hidden = true;

  function say(message, kind = "info") {
    lastStatus = {message, kind};
    paintStatus();
  }

  function paintStatus() {
    const box = bar.querySelector(".nst-edit-status");
    if (!box) return;
    box.textContent = isBusy()
      ? `выполняется: ${busy.label} · ${Math.floor((Date.now() - busy.since) / 1000)} с`
      : lastStatus.message;
    box.dataset.kind = isBusy() ? "busy" : lastStatus.kind;
  }

  /* ── занято: правка ждёт сервера 9–12 секунд ─────────────────────────── */

  // Без подписи происходящего ответ сервера выглядит зависшей панелью, и лоровед жмёт второй раз.
  const REQUEST_WORDS = {
    "/api/state": "обновление состояния базы",
    "/api/locate": "поиск строки матча",
    "/api/queue": "чтение очереди редактуры",
    "/api/log": "чтение журнала правок",
    "/api/publish": "чтение очереди публикаций",
    "/api/containers": "список контейнеров",
    "/api/players": "поиск карточек игроков",
    "/api/search": "поиск строк по сезону и турниру",
    "/api/doc": "чтение рамки турнира",
    "/api/edit": "правка базы",
  };

  const busy = {depth: 0, label: "", since: 0, ticker: null, frozen: []};
  let lastStatus = {message: "подключение…", kind: "info"};

  function isBusy() {
    return busy.depth > 0;
  }

  const requestLabel = (path) => (REQUEST_WORDS[path.split("?")[0]] || "запрос к серверу");

  function freezeButtons() {
    // Вооружение снимаем, а не только блокируем клик: иначе первый же клик после разблокировки
    // оказался бы вторым шаговым подтверждением и удалил бы строку.
    const nodes = [...bar.querySelectorAll("button"), ...panel.querySelectorAll("button")];
    for (const node of nodes) if (node.nstDisarm) node.nstDisarm();
    for (const node of nodes) {
      if (node.disabled) continue;  // выключена панелью навсегда, а не на время запроса
      node.disabled = true;
      busy.frozen.push(node);
    }
  }

  function unfreezeButtons() {
    // Список ведётся отдельно от счётчика глубины: кнопки вырастают внутри панели уже после
    // заморозки (журнал перерисовывается посреди отката), и их надо разморозить все.
    while (busy.frozen.length) busy.frozen.pop().disabled = false;
  }

  async function pending(label, task) {
    // Счётчик, а не флаг: занятость держится и на правке, и на пересчёте состояния после неё.
    const outermost = busy.depth === 0;
    busy.depth += 1;
    try {
      if (outermost) {
        busy.label = label;
        busy.since = Date.now();
        busy.ticker = setInterval(paintStatus, 1000);
        bar.dataset.busy = "1";
        panel.dataset.busy = "1";
        document.body.classList.add("nst-edit-busy");
        freezeButtons();
        paintStatus();
      }
      return await task();
    } finally {
      busy.depth -= 1;
      if (busy.depth === 0) {
        clearInterval(busy.ticker);
        busy.ticker = null;
        delete bar.dataset.busy;
        delete panel.dataset.busy;
        document.body.classList.remove("nst-edit-busy");
        unfreezeButtons();
        paintStatus();
      }
    }
  }

  // Захват на контейнерах добирает кнопки, выросшие уже внутри занятого запроса.
  for (const root of [bar, panel]) {
    root.addEventListener("click", (event) => {
      if (!isBusy() || !event.target.closest("button")) return;
      event.preventDefault();
      event.stopPropagation();
      paintStatus();
    }, true);
  }

  function buildBar() {
    bar.appendChild(el("span", "nst-edit-title", "✎ РЕДАКТОР БАЗЫ"));
    const field = el("input", "nst-edit-token");
    field.type = "password";
    field.placeholder = "токен";
    const login = el("button", null, "войти");
    login.type = "button";
    login.onclick = () => {
      const given = field.value.trim();
      if (!given) return say("сначала токен: он не в адресе и не в ссылках", "error");
      state.token = given;
      sessionStorage.setItem("nstEditorToken", given);
      field.value = "";
      return refreshState();
    };
    bar.appendChild(field);
    bar.appendChild(login);
    bar.appendChild(el("span", "nst-edit-status", "подключение…"));
    const buttons = el("div", "nst-edit-actions");
    for (const [label, action] of [["очередь", "queue"], ["найти", "search"],
                                   ["новая игра", "match"],
                                   ["новый турнир", "tournament"], ["игроки", "players"],
                                   ["журнал", "log"], ["опубликовать", "publish"],
                                   ["обновить", "state"], ["скрыть", "hide"]]) {
      const button = el("button", null, label);
      button.type = "button";
      button.onclick = () => {
        if (action === "hide") return document.body.classList.remove("nst-edit-on");
        if (action === "queue") return showQueue();
        if (action === "search") return showSearch();
        if (action === "match") return showNewMatch();
        if (action === "tournament") return showNewTournament();
        if (action === "players") return showPlayers("");
        if (action === "log") return showLog();
        if (action === "publish") return showPublish();
        return refreshState();
      };
      buttons.appendChild(button);
    }
    bar.appendChild(buttons);
  }

  async function refreshState() {
    try {
      const answer = await call("/api/state");
      state.revision = answer.revision;
      // Очередь публикаций зовётся рядом: без неё панель осталась бы со статусом базы, а с ней —
      // ещё и с числом запросов, которые ждут сборки.
      try {
        state.publish = (await call("/api/publish")).requests || [];
      } catch (error) {
        state.publish = [];  // сервер старее страницы: ручки нет — счётчика нет
      }
      paintPublishQueue();
      say(`ревизия ${answer.revision} · матчей ${answer.matches} · правок живых ${answer.corrections_live}`
        + ` · ручных строк ${answer.manual} · в очереди ${answer.queue}` + publishWord(state.publish));
    } catch (error) {
      say("сервер правки недоступен: " + error.message, "error");
    }
  }

  // Подпись занятости берёт сама операция: её слово встаёт после «предпросмотр» и «запись».
  const EDIT_WORDS = {
    "set-score": {what: "счёта"},
    "set-players": {what: "состава"},
    "set-source": {what: "источников"},
    "set-rating": {what: "рейтингового флага"},
    "set-place": {what: "места строки"},
    "set-date": {what: "даты"},
    "set-phase": {what: "фазы"},
    "set-provenance": {what: "происхождения"},
    "set-doc": {what: "рамки турнира"},
    "add-match": {preview: "предпросмотр новой игры", write: "занесение новой игры"},
    "add-tournament": {preview: "предпросмотр турнира", write: "заведение турнира"},
    "rename-player": {preview: "предпросмотр ника", write: "переименование карточки"},
    "merge-player": {preview: "предпросмотр слияния", write: "слияние карточек"},
    "void": {write: "снятие игры с зачёта"},
    "unvoid": {write: "возврат игры на зачёт"},
    "unhide": {write: "возврат строки на витрину"},
    "drop-match": {write: "удаление игры из базы"},
    "drop-tournament": {write: "удаление турнира"},
    // Запрос на выкат — не правка строки: перерисовывать ничего не нужно, только поставить в очередь.
    "publish-request": {preview: "предпросмотр очереди", write: "запрос публикации"},
  };

  function editLabel(edit) {
    if (edit.operation === "undo") {
      const what = String(edit.args?.what || "");
      if (what.startsWith("op:")) return "откат операции целиком";
      if (what === "last") return "откат последней операции";
      return "откат записи журнала";
    }
    const words = EDIT_WORDS[edit.operation] || {};
    if (!edit.persist) return words.preview || `предпросмотр ${words.what || edit.operation}`;
    return words.write || `запись ${words.what || edit.operation}`;
  }

  /* ── как понять, на какую строку матча нажал редактор ─────────────────── */

  const scoreOf = (row) => {
    const badge = row.querySelector(".score-badge");
    const found = (badge?.textContent || "").match(/(\d+)\s*:\s*(\d+)/);
    return found ? `${found[1]}:${found[2]}` : (badge?.textContent || "").trim();
  };

  const sidesOf = (row) => {
    const badge = row.querySelector(".score-badge");
    if (!badge) return [];
    // Соседи бейджа по строке и есть пары. Внутри бейджа сидят метки («ОТ», «Пенальти»,
    // «⚡ ТП (СНЯТ)») — их брать нельзя, иначе правая сторона прочитается как «ОТ».
    const kids = [...badge.parentElement.children];
    const at = kids.indexOf(badge);
    const text = (node) => (node ? node.textContent.trim().replace(/\s+/g, " ") : "");
    return [text(kids[at - 1]), text(kids[at + 1])].filter(Boolean);
  };

  const tourOf = (row) => [...row.querySelectorAll("span")].map(n => n.textContent.trim())[0] || "";

  /* Строка истории игрока: sides здесь не соседи бейджа, а два именованных блока, и счёт
     смотрит на мир глазами этого игрока («забито: пропущено»), а не сторон матча. */
  const historyOf = (row) => {
    const name = (sel) => (row.querySelector(sel)?.textContent || "").replace(/\s+/g, " ").trim();
    const goals = [...row.querySelectorAll(".mhr-score-num")].map(n => n.textContent.trim());
    return {
      a: name(".mhr-home .mhr-name"),
      b: name(".mhr-away .mhr-name"),
      score: goals.length === 2 ? `${goals[0]}:${goals[1]}` : "",
      tour: name(".mhr-stage"),
    };
  };

  /* Строка «личных встреч»: те же матчи, но показанные парой «игрок — игрок» с короной у
     победителя, поэтому имя чистится от значка, а сезон берётся из подписи строки — без него
     одна и та же пара с одним счётом находится в нескольких сезонах. */
  const h2hOf = (row) => {
    const cell = (sel) => (row.querySelector(sel)?.textContent || "").replace(/👑/g, "")
      .replace(/\s+/g, " ").trim();
    const nums = [...row.querySelectorAll(".h2h-score-box span")].map(n => n.textContent.trim())
      .filter((text) => /^\d+$/.test(text));
    return {
      a: cell(".h2h-p1-cell"),
      b: cell(".h2h-p2-cell"),
      score: nums.length === 2 ? `${nums[0]}:${nums[1]}` : "",
      season: cell(".h2h-match-season"),
    };
  };

  async function openRow(row) {
    const [a, b] = sidesOf(row);
    if (!a || !b) return say("не удалось разобрать пару в этой строке", "error");
    return locateAndShow(a, b, tourOf(row), scoreOf(row));
  }

  async function openHistory(row) {
    const { a, b, score, tour } = historyOf(row);
    if (!a || !b) return say("не удалось разобрать пару в этой строке истории", "error");
    return locateAndShow(a, b, tour, score);
  }

  async function openDuel(row) {
    const { a, b, score, season } = h2hOf(row);
    if (!a || !b) return say("не удалось разобрать пару в этой строке", "error");
    return locateAndShow(a, b, "", score, season);
  }

  async function locateAndShow(a, b, tour, score, season = "") {
    // Занятость держим на всём клике: поиск иногда делает второй запрос подряд, без сезона.
    return pending("поиск строки матча", async () => {
      say(`ищу «${a} ${score} ${b}»…`);
      try {
        let answer = await call("/api/locate", { a, b, tour, score, season, include_hidden: true });
        if (!answer.candidates.length && season) {
          // Подпись сезона на странице не всегда совпадает с тем, как его зовёт база (спецтурниры),
          // — тогда ищем без него и даём выбрать человеку.
          answer = await call("/api/locate", { a, b, tour, score, include_hidden: true });
        }
        if (!answer.candidates.length) return say("в базе нет строки под этой картинкой", "error");
        if (answer.candidates.length > 1) return showCandidates(answer.candidates);
        return showMatch(answer.candidates[0]);
      } catch (error) {
        return say(error.message, "error");
      }
    });
  }

  /* ── что показать редактору ──────────────────────────────────────────── */

  function openPanel(title, bodyNode) {
    panel.innerHTML = "";
    const head = el("div", "nst-edit-head");
    head.appendChild(el("strong", null, title));
    const close = el("button", "nst-edit-close", "×");
    close.type = "button";
    // Закрытие панели во время запроса выбросило бы дельту, которую сервер уже считает.
    close.onclick = () => { panel.hidden = true; state.row = null; };
    head.appendChild(close);
    panel.appendChild(head);
    panel.appendChild(bodyNode);
    panel.hidden = false;
    if (isBusy()) freezeButtons();  // панель перерисована посреди занятого запроса (откат из журнала)
  }

  const line = (label, value) => el("div", "nst-edit-line", `<b>${label}</b> ${value ?? "—"}`);

  function candidateButton(row) {
    // Надпись строки и статус приходят из источника (ник, подпись тура) — в панель они попадают
    // текстом, иначе написание с углом или скобкой стало бы разметкой.
    const button = el("button", "nst-edit-candidate",
      `#${row.id} · ${safe(row.display)} · <i>${row.row_set}${row.manual ? " · ручная" : ""}`
      + `${row.hidden_by ? " · скрыта как дубль" : ""}`
      + `${row.status !== "played" ? " · " + safe(STATUS_WORDS[row.status] || row.status) : ""}</i>`);
    button.type = "button";
    button.onclick = () => showMatch(row);
    return button;
  }

  function showCandidates(candidates) {
    const box = el("div", "nst-edit-candidates");
    box.appendChild(el("p", "nst-edit-note",
      `под это описание подходит ${candidates.length} строк — выбери, какую править, а не ту, что первая`));
    candidates.forEach((row) => box.appendChild(candidateButton(row)));
    openPanel("несколько строк", box);
  }

  function showMatch(row) {
    state.row = row;
    const box = el("div", "nst-edit-match");
    box.appendChild(line("строка", `#${row.id} · ${row.tournament} · ${row.stage || ""}`));
    if (row.review) {
      box.appendChild(el("p", "nst-edit-note", `<b>задача из очереди:</b> ${row.review["задача"]}`));
    }
    const hrefs = (row.links || []).map((link) =>
      `<a href="${link.url}" target="_blank" rel="noopener">${LINK_WORDS[link.kind] || link.kind}</a>`).join(" · ");
    if (hrefs) box.appendChild(line("источник", hrefs));
    if (row.linked && row.linked.length) {
      box.appendChild(el("p", "nst-edit-note",
        `правка пойдёт по всей связке: #${row.id} + #${row.linked.join(", #")}`
        + " — это одна игра, просто в базе она из двух строк (страница + рейтинг)"));
    }
    box.appendChild(line("счёт источника", `"${row.note || "—"}"`));
    (row.sides || []).forEach((side) => box.appendChild(line(
      `[${side.side_index}] ${side.players || side.label}`,
      `${side.score ?? "—"} · ${OUTCOME_WORDS[side.outcome] || side.outcome}`)));
    if (row.in_rating_pool) {
      box.appendChild(el("p", "nst-edit-warn",
        "матч входит в рейтинговый пул: счёт и игроки двигают Elo и мастер-таблицу — "
        + "предпросмотр покажет, насколько"));
    }

    const rosterForm = el("div", "nst-edit-form");
    rosterForm.appendChild(el("span", "nst-edit-h", "кто играл"));
    const rosterInputs = (row.sides || []).map((side) => {
      const input = document.createElement("input");
      input.type = "text";
      input.className = "nst-edit-players";
      input.value = side.label || side.players || "";
      rosterForm.appendChild(input);
      return input;
    });
    for (const [label, persist] of [["предпросмотр состава", false], ["записать состав", true]]) {
      const button = el("button", "nst-edit-secondary", label);
      button.type = "button";
      button.onclick = () => run({
        operation: "set-players",
        args: { match_id: row.id, sides: rosterInputs.map((input) => input.value) },
        persist,
      });
      rosterForm.appendChild(button);
    }
    box.appendChild(rosterForm);
    const look = el("button", "nst-edit-secondary", "карточки этих игроков");
    look.type = "button";
    look.onclick = () => showPlayers((rosterInputs[0]?.value.split("&")[0] || "").trim());
    rosterForm.appendChild(look);
    box.appendChild(el("p", "nst-edit-note",
      "пара 2×2 — через « & ». Ник сворачивается в карточку по справочнику имён, неизвестный ник "
      + "заведёт новую карточку; если под таким ником уже живёт другой игрок — правка не запишется"));

    const sourceForm = el("div", "nst-edit-form");
    sourceForm.appendChild(el("span", "nst-edit-h", "источники"));
    const noteInput = document.createElement("input");
    noteInput.type = "text";
    noteInput.className = "nst-edit-players nst-edit-wide";
    noteInput.placeholder = "что таблица турнира показывает в колонке счёта";
    noteInput.value = row.note || "";
    sourceForm.appendChild(noteInput);
    const linksBox = document.createElement("textarea");
    linksBox.className = "nst-edit-links nst-edit-wide";
    linksBox.rows = 3;
    linksBox.placeholder = "vk_post https://vk.com/topic-66162180_33437511#post4868\n"
      + "video https://vk.com/video-66162180-1";
    linksBox.value = (row.links || []).map((link) => `${link.kind} ${link.url}`).join("\n");
    sourceForm.appendChild(linksBox);
    for (const [label, persist] of [["предпросмотр источников", false], ["записать источники", true]]) {
      const button = el("button", "nst-edit-secondary", label);
      button.type = "button";
      button.onclick = () => run({
        operation: "set-source",
        args: { match_id: row.id, note: noteInput.value, links: parseLinks(linksBox.value) },
        persist,
      });
      sourceForm.appendChild(button);
    }
    box.appendChild(sourceForm);
    box.appendChild(el("p", "nst-edit-note",
      "ссылки заменяются списком целиком: что написано в поле — то и есть доказательства игры. "
      + "Одна ссылка на строку в минуту, без повторов"));
    if (row.doc_key) {
      const docButton = el("button", "nst-edit-secondary", `рамка турнира ${row.doc_key}`);
      docButton.type = "button";
      docButton.onclick = () => showDoc(row.doc_key);
      box.appendChild(docButton);
    }

    const ratingForm = el("div", "nst-edit-form");
    const rated = document.createElement("input");
    rated.type = "checkbox";
    rated.id = `nst-rated-${row.id}`;
    rated.checked = !!row.in_rating_pool;
    ratingForm.appendChild(rated);
    ratingForm.appendChild(el("label", null, "рейтинговая партия — считается в Elo"));
    for (const [label, persist] of [["предпросмотр рейтинга", false], ["записать флаг", true]]) {
      const button = el("button", "nst-edit-secondary", label);
      button.type = "button";
      button.onclick = () => run({
        operation: "set-rating", args: { match_id: row.id, rated: rated.checked }, persist });
      ratingForm.appendChild(button);
    }
    box.appendChild(ratingForm);
    box.appendChild(el("p", "nst-edit-note",
      "в рейтинг берутся только матчи 1×1 с числовым счётом и понятным годом; остальное редактор "
      + "откажет и скажет почему. Целым сезонам или турнирам флаг ставит rate-scope — "
      + "«python db/edit.py rate-scope --season 'Season 6'»"));
    box.appendChild(detailsBlock(row));

    const form = el("div", "nst-edit-form");
    const first = document.createElement("input");
    const second = document.createElement("input");
    [first, second].forEach((input) => { input.type = "number"; input.min = "0"; input.className = "nst-edit-score"; });
    first.value = row.sides?.[0]?.score ?? 0;
    second.value = row.sides?.[1]?.score ?? 0;
    form.appendChild(first);
    form.appendChild(el("span", "nst-edit-vs", ":"));
    form.appendChild(second);
    for (const [label, operation, persist] of [["предпросмотр", "set-score", false], ["записать", "set-score", true]]) {
      const button = el("button", null, label);
      button.type = "button";
      button.onclick = () => run({ operation, args: { match_id: row.id, s1: +first.value, s2: +second.value }, persist });
      form.appendChild(button);
    }
    for (const [label, operation] of [["снять с зачёта", "void"], ["вернуть на зачёт", "unvoid"]]) {
      const button = el("button", "nst-edit-secondary", label);
      button.type = "button";
      button.onclick = () => run({ operation, args: { match_id: row.id }, persist: true });
      form.appendChild(button);
    }
    if (row.hidden_by) {
      const button = el("button", "nst-edit-secondary", "вернуть строку на витрину");
      button.type = "button";
      button.onclick = () => run({ operation: "unhide", args: { match_id: row.id }, persist: true });
      form.appendChild(button);
    }
    form.appendChild(dangerButton("удалить игру из базы", () => ({
      operation: "drop-match", args: { match_id: row.id }, persist: true,
    })));
    box.appendChild(form);
    box.appendChild(el("p", "nst-edit-note",
      "«снять с зачёта» прячет игру на витрине и не трогает архив; «удалить» стирает строку вместе "
      + "со сторонами, составом и ссылками — и только пока на неё не ссылается другая (дубли)"));
    box.appendChild(el("div", "nst-edit-delta"));
    openPanel(`правка строки #${row.id}`, box);
  }

  /* ── детали строки: где лежит, когда играли, чем закончилось и откуда взялось */

  const PHASES = ["regular", "overtime", "penalties", "overtime_penalties"];
  const PHASE_WORDS = {regular: "основное время", overtime: "овертайм", penalties: "буллиты",
                       overtime_penalties: "овертайм + буллиты", "": "не трогать"};
  // У этих полей «не трогать» — собственное значение (пустая опция списка), а не пустая строка.
  const TRISTATE = new Set(["phase", "playoff"]);

  // В правку едет только то, что человек переписал: незадетое поле списка ничего не меняет,
  // а очищенное текстовое — очищает, потому что пустое оно не равно тому, что лежит в базе.
  function editRequest(inputs, persist, operation, matchId) {
    const args = {match_id: matchId};
    for (const [input, current, name] of inputs) {
      const value = input.value.trim();
      const held = String(current ?? "");
      if (TRISTATE.has(name)) {
        if (value === "" || value === held) continue;
        args[name] = name === "playoff" ? value === "1" : value;
        continue;
      }
      if (value === held) continue;
      args[name] = value;
    }
    return {operation, args, persist};
  }

  function detailsBlock(row) {
    const wrap = el("div", "nst-edit-details");
    wrap.appendChild(el("span", "nst-edit-h", "детали строки"));

    const place = el("div", "nst-edit-form");
    const tour = field("input", "nst-edit-players",
                       {type: "text", placeholder: "тур: 12 Тур", value: row.tour || ""});
    const league = field("input", "nst-edit-players",
                         {type: "text", placeholder: "дивизион: Высшая", value: row.league || ""});
    const stage = field("input", "nst-edit-players",
                        {type: "text", placeholder: "этап: Финал", value: row.stage || ""});
    place.append(tour, league, stage);
    for (const [label, persist] of [["предпросмотр места", false], ["записать место", true]]) {
      writeButton(place, label,
                  () => editRequest([
                    [tour, row.tour, "tour"],
                    [league, row.league, "league"],
                    [stage, row.stage, "stage"],
                  ], persist, "set-place", row.id), persist);
    }
    wrap.appendChild(place);
    wrap.appendChild(el("p", "nst-edit-note",
      "перенос в другой тур или этап меняет, где игра лежит на странице. Импортер узнаёт строку "
      + "по старому месту и заносит её в память (`source_place`) — иначе следующая выгрузка ВК "
      + "принесла бы ту же партию вторым рядом"));

    const date = el("div", "nst-edit-form");
    const played = field("input", "nst-edit-players",
                         {type: "text", placeholder: "дата: 2024-05-01 / 2024-05 / 2024",
                          value: row.played_on || ""});
    const rawDate = field("input", "nst-edit-players nst-edit-wide",
                          {type: "text", placeholder: "дата дословно из источника",
                           value: row.source_date_raw || ""});
    date.append(played, rawDate);
    for (const [label, persist] of [["предпросмотр даты", false], ["записать дату", true]]) {
      writeButton(date, label,
                  () => editRequest([[played, row.played_on, "played_on"],
                              [rawDate, row.source_date_raw, "source_date_raw"]],
                             persist, "set-date", row.id), persist);
    }
    wrap.appendChild(date);
    wrap.appendChild(el("p", "nst-edit-note",
      "без года партия не попадает в Elo: рейтинг проигрывает матчами по порядку времени, а год "
      + "берётся из сезона, даты или рамки. Точность («ГГГГ», «ГГГГ-ММ», «ГГГГ-ММ-ДД») база считает "
      + "по форме сама"));

    const phase = el("div", "nst-edit-form");
    const phasePick = field("select", "nst-edit-pick");
    for (const value of ["", ...PHASES]) {
      phasePick.appendChild(field("option", null, {value, textContent: PHASE_WORDS[value]}));
    }
    phasePick.value = row.phase || "regular";
    const playoffPick = field("select", "nst-edit-pick");
    [["", "плей-офф: не трогать"], ["1", "плей-офф"], ["0", "регулярка"]].forEach(([value, text]) =>
      playoffPick.appendChild(field("option", null, {value, textContent: text})));
    playoffPick.value = row.is_playoff === null || row.is_playoff === undefined ? "" : String(row.is_playoff);
    phase.append(phasePick, playoffPick);
    for (const [label, persist] of [["предпросмотр фазы", false], ["записать фазу", true]]) {
      writeButton(phase, label,
                  () => editRequest([[phasePick, row.phase, "phase"],
                              [playoffPick, row.is_playoff, "playoff"]],
                             persist, "set-phase", row.id), persist);
    }
    wrap.appendChild(phase);
    wrap.appendChild(el("p", "nst-edit-note",
      "победа в овертайме или по буллитам стоит 0.75 вместо 1, плей-офф играет при K=32 — поэтому "
      + "фаза сверяется с исходами до записи и редактор откажет, если счёт с ними не сходится"));

    const origin = el("div", "nst-edit-form");
    origin.appendChild(el("span", "nst-edit-h", "происхождение строки"));
    const originFields = [
      ["source", "носитель: wiki_table, cup_reference, vk_post…"],
      ["source_ref", "ключ строки у носителя"],
      ["source_locator", "где искать: адрес топика, страница"],
      ["source_page", "страница источника"],
      ["source_text", "как источник это описал (дословно)"],
    ].map(([name, placeholder]) => {
      const input = field("input", "nst-edit-players nst-edit-wide",
                          {type: "text", placeholder, value: row[name] || ""});
      origin.appendChild(input);
      return [input, row[name], name];
    });
    for (const [label, persist] of [["предпросмотр происхождения", false], ["записать происхождение", true]]) {
      writeButton(origin, label,
                  () => editRequest(originFields, persist, "set-provenance", row.id), persist);
    }
    wrap.appendChild(origin);
    wrap.appendChild(el("p", "nst-edit-warn",
      "source_ref — ключ, по которому импортёр узнаёт игру при следующей сборке. Поставишь новый — "
      + "старый ключ освободится, и источник принесёт ту же партию вторым рядом: база спрячет дубль "
      + "за ручной строкой, а спор ляжет в очередь редактуры. Происхождение правится у одной строки: "
      + "у связки «витрина + рейтинг» два носителя и два ключа, общий база не примет"));
    return wrap;
  }

  /* Удаление — единственная правка, которую нельзя передумать молча: первый клик только
     вооружает кнопку, второй пишет. */
  function dangerButton(label, build) {
    const button = el("button", "nst-edit-danger", label);
    button.type = "button";
    let armed = false;
    // Сброс висит на самой кнопке: боевым бывает первый клик после разблокировки.
    const disarm = () => {
      if (!armed) return;
      armed = false;
      button.textContent = label;
    };
    button.nstDisarm = disarm;
    button.onclick = () => {
      if (isBusy()) return undefined;  // занятой сервер: клик не трогает ни вооружение, ни надпись
      if (!armed) {
        armed = true;
        button.textContent = `${label} — нажми ещё раз`;
        return undefined;
      }
      disarm();
      return run(build());
    };
    return button;
  }

  const FIELD_LABELS = {
    goals: "голов", matches: "матчей", videos: "видео", league_matches: "матчей лиги",
    special_matches: "спецматчей", team_matches: "командных", players: "игроков",
    total_goals_recorded: "голов записано", total_matches_analyzed: "матчей посчитано",
    avg_goals_per_match: "голов на матч",
  };

  // Что значит изменённое поле базы — редактор видит правку словами, а не именем колонки.
  const COLUMN_LABELS = {
    score: "счёт", outcome: "исход", note: "подпись строки", status: "зачёт",
    roster: "состав стороны", label: "подпись стороны", payload: "рамка", title: "заголовок",
    manual: "ручная правка", exists: "строка", in_rating_pool: "рейтинговая партия",
    hidden_by: "скрыта как дубль", duplicate_of: "дубль",
    tour: "тур", league: "дивизион", stage_id: "этап", played_on: "дата",
    date_precision: "точность даты", phase: "фаза", is_playoff: "плей-офф",
    source: "носитель", source_ref: "ключ источника", source_locator: "где искать",
    source_page: "страница источника", source_text: "текст источника",
    source_place: "место у источника", nick: "ник", slug: "адрес карточки", player_id: "игрок",
  };

  const TABLE_WORDS = {matches: "матч", match_sides: "сторона", match_links: "ссылка",
                       tournament_docs: "турнир", players: "игрок", stages: "этап",
                       side_players: "состав стороны", player_aliases: "алиас"};

  // Служебные слова базы — наружу по-русски: карточку читает человек, а не отладчик.
  const OUTCOME_WORDS = {win: "победа", loss: "поражение", draw: "ничья", none: "без итога"};
  const STATUS_WORDS = {played: "в зачёте", void: "снят с зачёта", technical: "технический"};
  const LINK_WORDS = {vk_post: "пост ВК", video: "видео", wiki: "вики-страница", api: "запись API"};
  const KIND_WORDS = {special: "спецтурнир", team: "командный", league: "сезон", cup: "кубок"};

  // Значения-коды некоторых полей человек читает глазами, поэтому и «1 → 0» показывается словом.
  const FIELD_WORDS = {phase: PHASE_WORDS, outcome: OUTCOME_WORDS, status: STATUS_WORDS,
                       is_playoff: {0: "регулярка", 1: "плей-офф"},
                       in_rating_pool: {0: "не считается", 1: "считается"},
                       manual: {0: "носитель", 1: "человек"},
                       date_precision: {exact: "до дня", month: "до месяца", season: "до сезона"}};

  // Строка ссылки = «вид адрес»; без вида считаем постом ВК — именно так их приносит источник.
  const parseLinks = (text) => text.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => {
    const at = line.search(/\s/);
    return at < 0 ? ["vk_post", line] : [line.slice(0, at), line.slice(at).trim()];
  });

  // Пустая строка базы значит «подписи нет» — наряду с ∅ (поля до правки не было) это надо различать.
  // Кодексы полей (фаза, плей-офф, зачёт) читаются словами, а не нулями.
  const shownValue = (value, field) => {
    if (value === null || value === undefined) return "∅";
    if (value === "") return "пусто";
    const words = FIELD_WORDS[field];
    if (words && words[value] !== undefined) return words[value];
    return value;
  };

  function renderDelta(answer) {
    const box = panel.querySelector(".nst-edit-delta");
    box.innerHTML = "";
    if (answer.operation === "publish-request") return renderPublish(answer, box);
    if (!answer.persisted) box.appendChild(el("p", "nst-edit-note", "предпросмотр: база не изменена"));
    const fields = answer.changes || [];
    box.appendChild(el("p", "nst-edit-h",
      fields.length ? `в базе: ${fields.length} поле(й)` : "в базе"));
    for (const item of fields) {
      if (item.field === "exists") {
        // Создание и удаление строки — не значение колонки: снимок целиком человеку не читается.
        box.appendChild(el("div", "nst-edit-diff", item.new
          ? `заведена строка ${TABLE_WORDS[item.table] || item.table} #${item.row_id}`
          : `убрана строка ${TABLE_WORDS[item.table] || item.table} #${item.row_id}`));
        continue;
      }
      box.appendChild(el("div", "nst-edit-diff",
        `${TABLE_WORDS[item.table] || item.table} #${item.row_id} · `
        + `${COLUMN_LABELS[item.field] || item.field}: `
        + `<i>${shownValue(item.old, item.field)} → ${shownValue(item.new, item.field)}</i>`));
    }
    if (!fields.length) box.appendChild(el("div", "nst-edit-note", "ни одного поля — правка ничего не трогает"));
    if ((answer.created || []).length) {
      box.appendChild(el("p", "nst-edit-warn",
        `заведутся новые карточки игроков: ${answer.created.join(", ")}. Проверь написание: `
        + "опечатка родит двойника, а не переименование"));
    }
    const changes = answer.delta || {};
    if (!Object.keys(changes).length) {
      return box.appendChild(el("p", "nst-edit-warn",
        "правка ничего не изменит на странице. Так, например, работает «снять с зачёта»: Elo матч "
        + "перестаёт считать, а таблица его продолжает показывать."));
    }
    if (changes.headline) {
      box.appendChild(el("p", "nst-edit-h", "витрина"));
      for (const [key, pairValue] of Object.entries(changes.headline)) {
        if (!Array.isArray(pairValue)) continue;  // вложенный объект — не «было → стало» числами
        const [old, next] = pairValue;
        box.appendChild(el("div", "nst-edit-diff", `${FIELD_LABELS[key] || key}: ${old} → ${next}`));
      }
    }
    const players = changes.profiles || {};
    if (Array.isArray(players)) {
      box.appendChild(el("div", "nst-edit-note",
        "список профилей изменился целиком — нужен пересбор страницы, полей не показать"));
    }
    const names = Array.isArray(players) ? [] : Object.keys(players).filter((name) => name !== "__order__");
    if (names.length) {
      box.appendChild(el("p", "nst-edit-h", `изменённых игроков: ${names.length}`));
      for (const name of names.slice(0, 12)) {
        const value = players[name];
        if (Array.isArray(value)) {
          // Карточка появилась или исчезла целиком (переименование, слияние, новый ник): сверку по
          // полям здесь невозможна — показываем профиль до и после одним взглядом.
          const brief = (p) => (p ? `${p.active_elo ?? "—"} Elo · ${p.matches ?? "—"} матчей`
                                  : "карточки нет");
          box.appendChild(el("div", "nst-edit-diff",
            `<b>${name}</b>: ${brief(value[0])} → ${brief(value[1])}`));
          continue;
        }
        const fields = Object.entries(value)
          .filter(([key]) => key !== "match_history")
          .map(([key, [old, next]]) => `${key} ${old} → ${next}`);
        box.appendChild(el("div", "nst-edit-diff", `<b>${name}</b> ${fields.join(", ") || "без изменения чисел"}`));
      }
      if (names.length > 12) box.appendChild(el("div", "nst-edit-note", `…и ещё ${names.length - 12}`));
    }
    for (const [section, value] of Object.entries(changes)) {
      if (section === "headline" || section === "profiles" || typeof value !== "object") continue;
      if (Array.isArray(value)) {
        box.appendChild(el("div", "nst-edit-note", `${section}: раздел изменился целиком`));
        continue;
      }
      const order = value && value.__order__;
      box.appendChild(el("div", "nst-edit-note",
        `${section}: ${order ? "порядок сместился" : "изменилось содержание"}`
        + (value && value.__length__ ? ` (строк ${value.__length__[0]} → ${value.__length__[1]})` : "")));
    }
    if (answer.persisted) {
      box.appendChild(el("p", "nst-edit-warn",
        `записано (журнал ${answer.journal.join(", ")}). Цифры на странице обновит сборка: `
        + "python build_all.py"));
    }
  }

  async function run(request) {
    if (!state.token) return say("введите токен редактора в панели слева", "error");
    return pending(editLabel(request), async () => {
      try {
        const answer = await call("/api/edit", { ...request, expect: request.persist ? state.revision : undefined });
        if (!panel.querySelector(".nst-edit-delta")) {
          // Откат пришёл из журнала: дельту показывать некуда, зато список записей устарел.
          say(answer.persisted ? `откатлено записей: ${(answer.reverted || []).length}`
                               : "откатывать нечего");
          return showLog();
        }
        renderDelta(answer);
        return refreshState();
      } catch (error) {
        say(error.message, "error");
        // Ревизия устарела: панель должна показать новую, а не слать правку по старой картинке.
        if (/изменилась с момента/.test(error.message)) return refreshState();
      }
    });
  }

  /* ── новые сущности: игра, турнир, рамка ─────────────────────────────── */

  function field(tag, cls, attrs) {
    const node = document.createElement(tag);
    node.className = cls;
    Object.entries(attrs || {}).forEach(([name, value]) => { node[name] = value; });
    return node;
  }

  function writeButton(box, label, build, persist) {
    const button = el("button", persist ? null : "nst-edit-secondary", label);
    button.type = "button";
    button.onclick = () => {
      try {
        return run(build());
      } catch (error) {
        return say(error.message, "error");
      }
    };
    box.appendChild(button);
    return button;
  }

  async function showNewMatch() {
    let answer;
    try {
      answer = await call("/api/containers");
    } catch (error) {
      return say(error.message, "error");
    }
    const box = el("div", "nst-edit-match");
    box.appendChild(el("p", "nst-edit-note",
      "так вносят игру, которую источник описал словами, а таблица её потеряла. Строка получает "
      + "пометку «ручная»: импортёр её не тронет и не задвоит"));
    const pick = field("select", "nst-edit-pick nst-edit-wide");
    for (const doc of answer.docs) {
      const option = field("option", null, {value: `doc:${doc.doc_key}`,
        textContent: `${doc.title} — ${KIND_WORDS[doc.kind] || doc.kind}`});
      pick.appendChild(option);
    }
    for (const season of answer.seasons) {
      pick.appendChild(field("option", null, {value: `season:${season}`, textContent: season}));
    }
    box.appendChild(pick);

    const form = el("div", "nst-edit-form");
    const stage = field("input", "nst-edit-players", {type: "text", placeholder: "этап: Финал"});
    const tour = field("input", "nst-edit-players", {type: "text", placeholder: "тур: 12 Тур"});
    const sideA = field("input", "nst-edit-players", {type: "text", placeholder: "первая сторона"});
    const sideB = field("input", "nst-edit-players", {type: "text", placeholder: "вторая сторона"});
    const scoreA = field("input", "nst-edit-score", {type: "number", min: "0"});
    const scoreB = field("input", "nst-edit-score", {type: "number", min: "0"});
    const note = field("input", "nst-edit-players nst-edit-wide",
                       {type: "text", placeholder: "подпись в колонке счёта — пусто значит «как счёт»"});
    const links = field("textarea", "nst-edit-links nst-edit-wide", {rows: "2"});
    form.append(stage, tour, sideA, sideB, scoreA, el("span", "nst-edit-vs", ":"), scoreB, note, links);
    box.appendChild(form);

    const build = (persist) => () => {
      const [what, value] = pick.value.split(":");
      const args = {sides: [sideA.value, sideB.value], stage: stage.value.trim(),
                    tour: tour.value.trim(), note: note.value.trim(),
                    links: parseLinks(links.value)};
      if (what === "doc") args.doc_key = value;
      else args.season = value;
      if (scoreA.value !== "") args.s1 = +scoreA.value;
      if (scoreB.value !== "") args.s2 = +scoreB.value;
      return {operation: "add-match", args, persist};
    };
    writeButton(form, "предпросмотр игры", build(false), false);
    writeButton(form, "занести игру", build(true), true);
    box.appendChild(el("div", "nst-edit-delta"));
    openPanel("новая игра", box);
  }

  function showNewTournament() {
    const box = el("div", "nst-edit-match");
    box.appendChild(el("p", "nst-edit-note",
      "новый турнир — это рамка без игр: список игр к ней приносит редактор кнопкой «новая игра» "
      + "или живой импорт, если у турнира есть тема ВК"));
    const form = el("div", "nst-edit-form");
    const key = field("input", "nst-edit-players", {type: "text", placeholder: "ключ: blitz_13"});
    const title = field("input", "nst-edit-players", {type: "text", placeholder: "заголовок"});
    const kind = field("select", "nst-edit-pick");
    kind.append(field("option", null, {value: "special", textContent: "спецтурнир"}),
                field("option", null, {value: "team", textContent: "командный"}));
    const category = field("input", "nst-edit-players", {type: "text", placeholder: "раздел: Спецтурниры"});
    form.append(key, title, kind, category);
    box.appendChild(form);
    const build = (persist) => () => ({
      operation: "add-tournament",
      args: {doc_key: key.value.trim(), title: title.value.trim(), kind: kind.value,
             frame: {category: category.value.trim()}},
      persist,
    });
    writeButton(form, "предпросмотр турнира", build(false), false);
    writeButton(form, "завести турнир", build(true), true);
    box.appendChild(el("div", "nst-edit-delta"));
    openPanel("новый турнир", box);
  }

  async function showDoc(docKey) {
    let doc;
    try {
      doc = (await call(`/api/doc?doc_key=${encodeURIComponent(docKey)}`)).doc;
    } catch (error) {
      return say(error.message, "error");
    }
    const box = el("div", "nst-edit-match");
    box.appendChild(line("документ", `${doc.doc_key} · ${KIND_WORDS[doc.kind] || doc.kind}`));
    box.appendChild(line("ключ игр", `${doc.match_field} · `
      + (doc.manual ? "рамку уже правил человек" : "рамку ведёт носитель")));
    const form = el("div", "nst-edit-form");
    const title = field("input", "nst-edit-players nst-edit-wide", {type: "text", value: doc.title});
    const frame = field("textarea", "nst-edit-links nst-edit-wide", {rows: "14"});
    frame.value = JSON.stringify(doc.frame, null, 1);
    form.append(title, frame);
    box.appendChild(form);
    const build = (persist) => () => {
      let parsed;
      try {
        parsed = JSON.parse(frame.value);
      } catch (error) {
        throw new Error(`рамка не читается как JSON: ${error.message}`);
      }
      return {operation: "set-doc", args: {doc_key: doc.doc_key, title: title.value, frame: parsed},
              persist};
    };
    writeButton(form, "предпросмотр рамки", build(false), false);
    writeButton(form, "записать рамку", build(true), true);
    form.appendChild(dangerButton("удалить турнир", () => ({
      operation: "drop-tournament", args: {doc_key: doc.doc_key}, persist: true,
    })));
    box.appendChild(el("p", "nst-edit-note",
      `ключ «${doc.match_field}» обязан остаться в рамке (пустым): игры живут в базе, а читатель `
      + "навешивает их сюда"));
    box.appendChild(el("p", "nst-edit-warn",
      "турнир удаляется только пустой: пока в нём есть игры, база откажет и назовёт их число — "
      + "сначала удали игры или заведи их в другой контейнер"));
    box.appendChild(el("div", "nst-edit-delta"));
    openPanel(`рамка турнира ${doc.title}`, box);
  }

  /* ── карточки игроков: переименование и слияние двойников ──────────────── */

  // Слияние — это направление: человек сначала говорит, какую карточку оставить, потом жмёт
  // «слить эту в …» на той, что уходит. Кнопка одна на строку — перепутать стороны нельзя.
  const mergePick = {id: null, nick: ""};

  function playerRow(player, rerender) {
    const box = el("div", "nst-edit-player");
    const picked = mergePick.id === player.id;
    box.appendChild(el("div", "nst-edit-line",
      `<b>#${player.id} · ${player.nick}</b> <i>сторон в базе: ${player.sides}</i>`
      + (picked ? " · <b>эту оставляем</b>" : "")));
    const nick = field("input", "nst-edit-players", {type: "text", value: player.nick});
    box.appendChild(nick);
    const request = (persist) => () => {
      const value = nick.value.trim();
      if (!value) throw new Error("ник не может быть пустым");
      if (value === player.nick) throw new Error("написание не изменилось");
      return {operation: "rename-player", args: {player_id: player.id, nick: value}, persist};
    };
    writeButton(box, "предпросмотр", request(false), false);
    writeButton(box, "переименовать", request(true), true);
    const pick = el("button", "nst-edit-secondary", picked ? "снять выбор" : "оставить эту");
    pick.type = "button";
    pick.onclick = () => {
      mergePick.id = picked ? null : player.id;
      mergePick.nick = picked ? "" : player.nick;
      return rerender();
    };
    box.appendChild(pick);
    if (mergePick.id && mergePick.id !== player.id) {
      box.appendChild(dangerButton(`слить эту в #${mergePick.id} ${mergePick.nick}`, () => {
        const args = {keep_id: mergePick.id, drop_id: player.id};
        mergePick.id = null;
        mergePick.nick = "";
        return {operation: "merge-player", args, persist: true};
      }));
    }
    return box;
  }

  async function showPlayers(query) {
    const box = el("div", "nst-edit-match");
    box.appendChild(el("p", "nst-edit-note",
      "Ник карточки читает вся витрина: переименование оставляет партии и ссылки на месте, а "
      + "слияние собирает двойников, которых наплодил разбор (один игрок писался по-разному). "
      + "Поиск по подстроке, «_» и «%» внутри ника — обычные символы"));
    const search = field("input", "nst-edit-players nst-edit-wide",
                         {type: "text", placeholder: "ник или его часть", value: query || ""});
    const results = el("div", "nst-edit-players-list");
    let found = [];
    const render = () => {
      results.innerHTML = "";
      if (!found.length) {
        results.appendChild(el("p", "nst-edit-note", mergePick.id
          ? `карточку #${mergePick.id} ${mergePick.nick} оставь выбранной и ищи вторую`
          : "по этому написанию карточек нет"));
      }
      found.forEach((player) => results.appendChild(playerRow(player, render)));
    };
    const load = async () => {
      try {
        found = (await call("/api/players?q=" + encodeURIComponent(search.value.trim()))).players;
        render();
      } catch (error) {
        say(error.message, "error");
      }
    };
    search.onkeydown = (event) => {
      // Нажатие в поле идёт мимо кнопок, поэтому занятость проверяем и здесь.
      if (event.key === "Enter" && !isBusy()) load();
    };
    const go = el("button", null, "найти");
    go.type = "button";
    go.onclick = load;
    box.append(search, go, results);
    box.appendChild(el("p", "nst-edit-note",
      "слияние откажется, если эти двое когда-нибудь играли друг против друга, — иначе игрок "
      + "оказался бы по обе стороны одной партии. Откат возвращается журналом как одна операция"));
    box.appendChild(el("div", "nst-edit-delta"));
    openPanel("карточки игроков", box);
    if (query) await load();
  }

  async function showSearch() {
    // Лоровед приходит «Сезон 7, Кубок лиг, 1/2 финала» или «где играл Bubnov», а не кликом по
    // картинке: здесь строки ищутся по разрядникам архива, а карточка открывается та же, что и
    // из таблицы турнира.
    const box = el("div", "nst-edit-match");
    box.appendChild(el("p", "nst-edit-note",
      "четыре независимых фильтра: пустое поле не сужает поиск, «%» и «_» внутри написания — "
      + "обычные символы, а не маска"));
    const form = el("div", "nst-edit-form nst-edit-search");
    const season = field("select", "nst-edit-pick");
    const tournament = field("select", "nst-edit-pick");
    const tour = field("input", "nst-edit-players", {type: "text", placeholder: "тур или этап"});
    const player = field("input", "nst-edit-players",
                         {type: "text", placeholder: "ник игрока или подпись стороны"});
    const hidden = field("input", "nst-edit-flag", {type: "checkbox"});
    const list = el("div", "nst-edit-search-list");

    const choose = (node, values, blank) => {
      const wanted = node.value;
      node.innerHTML = "";
      node.appendChild(field("option", null, {value: "", textContent: blank}));
      for (const value of values) {
        node.appendChild(field("option", null, {value, textContent: value}));
      }
      // Выбранное остаётся выбранным, только если оно всё ещё подходит под другие фильтры:
      // турнир чужого сезона в списке исчезает, и молча держать его было бы правкой вслепую.
      node.value = wanted && values.includes(wanted) ? wanted : "";
    };

    const load = async () => {
      const query = new URLSearchParams();
      if (season.value) query.set("season", season.value);
      if (tournament.value) query.set("tournament", tournament.value);
      if (tour.value.trim()) query.set("tour", tour.value.trim());
      if (player.value.trim()) query.set("player", player.value.trim());
      if (hidden.checked) query.set("include_hidden", "1");
      let answer;
      try {
        answer = await call("/api/search?" + query.toString());
      } catch (error) {
        return say(error.message, "error");
      }
      choose(season, answer.seasons, "все сезоны");
      choose(tournament, answer.tournaments, "все турниры");
      list.innerHTML = "";
      if (!answer.rows.length) {
        list.appendChild(el("p", "nst-edit-note",
          "под эти условия строк нет — снимите один фильтр или включите скрытые дубли"));
      }
      for (const row of answer.rows) list.appendChild(candidateButton(row));
      list.appendChild(el("p", "nst-edit-note",
        `подошло строк ${answer.total}, карточек ${answer.rows.length}`
        // Обрезку объявляем только по строкам, которые реально успели прийти до свёртки связок:
        // карточек всегда меньше строк, и по ним «показаны не все» выглядело бы правдой наугад.
        + (answer.fetched >= answer.shown
          ? ` — из-за лимита в ${answer.shown} строк список неполный, уточните сезон, турнир или тур`
          : "")));
      return undefined;
    };

    // Смена фильтра — тоже запрос: без проверки занятости быстрый двойной выбор сезона присылает
    // два ответа, и панель успевает перерисоваться stale-списком.
    for (const node of [season, tournament, hidden]) node.onchange = () => !isBusy() && load();
    for (const node of [tour, player]) {
      node.onkeydown = (event) => {
        if (event.key === "Enter" && !isBusy()) load();
      };
    }
    const go = el("button", null, "найти");
    go.type = "button";
    go.onclick = () => (isBusy() ? undefined : load());
    form.append(season, tournament, tour, player);
    const check = el("label", "nst-edit-check");
    check.append(hidden, el("span", null, "показать и скрытые дубли"));
    form.append(check, go);
    box.append(form, list);
    openPanel("поиск строки", box);
    return load();
  }

  async function showQueue() {
    try {
      const answer = await call("/api/queue");
      const box = el("div", "nst-edit-queue");
      if (!answer.tasks.length) box.appendChild(el("p", "nst-edit-note", "очередь пуста — всё разобрано"));
      for (const task of answer.tasks) {
        const item = el("div", "nst-edit-task");
        const where = [task.tour, (task.sides || []).join(" — "), task.shown].filter(Boolean).join(" · ");
        item.appendChild(el("div", "nst-edit-line", `<b>${where}</b>`));
        item.appendChild(el("div", "nst-edit-note", task.task));
        const hrefs = (task.links || []).map((url, index) =>
          `<a href="${url}" target="_blank" rel="noopener">ссылка ${index + 1}</a>`).join(" · ");
        if (hrefs) item.appendChild(el("div", "nst-edit-line", hrefs));
        const open = el("button", null, task.row ? "к строке" : "строки в базе нет");
        open.type = "button";
        if (task.row) open.onclick = () => showMatch(task.row);
        else open.disabled = true;
        item.appendChild(open);
        box.appendChild(item);
      }
      return openPanel(`очередь редактуры: ${answer.tasks.length}`, box);
    } catch (error) {
      return say(error.message, "error");
    }
  }

  // Одна правка заводит несколько записей журнала: число полей подписываем по-русски.
  const fieldsWord = (n) => (n % 10 === 1 && n % 100 !== 11 ? "поле"
    : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? "поля" : "полей");

  async function showLog() {
    try {
      const answer = await call("/api/log?limit=30");
      const box = el("div", "nst-edit-log");
      if (!answer.entries.length) box.appendChild(el("p", "nst-edit-note", "журнал пуст — правок не было"));
      const lastOperation = el("button", "nst-edit-secondary", "откатить последнюю операцию целиком");
      lastOperation.type = "button";
      lastOperation.onclick = () => run({ operation: "undo", args: { what: "last" }, persist: true });
      box.appendChild(lastOperation);
      // Записи одной правки идут подряд под общей меткой: откатывать надо кусок, а не поле за полем.
      const groups = [];
      for (const entry of answer.entries) {
        const held = groups[groups.length - 1];
        if (held && held.op && entry.op && held.op === entry.op) held.items.push(entry);
        else groups.push({op: entry.op || "", items: [entry]});
      }
      for (const group of groups) {
        const live = group.items.filter((item) => item.live).length;
        const whole = Number.isFinite(group.items[0].op_live) ? group.items[0].op_live : live;
        if (group.op && whole > 0) {
          const head = el("div", "nst-edit-log-op");
          head.appendChild(el("span", "nst-edit-note", `операция ${group.op}`));
          const undoAll = el("button", "nst-edit-secondary",
            `откатить операцию целиком (${whole} ${fieldsWord(whole)})`);
          undoAll.type = "button";
          undoAll.onclick = () => run({ operation: "undo", args: { what: "op:" + group.op }, persist: true });
          head.appendChild(undoAll);
          box.appendChild(head);
        }
        for (const entry of group.items) {
          const values = entry.field === "exists"
            ? (entry.new_value ? "строка создана правкой" : "строка удалена правкой")
            : `${shownValue(entry.old_value, entry.field)} → ${shownValue(entry.new_value, entry.field)}`;
          const row = el("div", "nst-edit-log-row",
            `#${entry.id} · ${entry.created_at} · <b>${entry.editor}</b> · `
            + `${TABLE_WORDS[entry.table_name] || entry.table_name} #${entry.row_id} `
            + `${COLUMN_LABELS[entry.field] || entry.field}: <i>${values}</i>`
            + (entry.match ? ` · ${entry.match}` : "")
            + (entry.reverted_at ? ` · отменено ${entry.reverted_at}` : ""));
          if (entry.live) {
            const button = el("button", "nst-edit-secondary", "откатить");
            button.type = "button";
            button.onclick = () => run({ operation: "undo", args: { what: String(entry.id) }, persist: true });
            row.appendChild(button);
          }
          box.appendChild(row);
        }
      }
      return openPanel("журнал правок", box);
    } catch (error) {
      return say(error.message, "error");
    }
  }

  /* ── очередь публикаций: правки накоплены, выкат делает сборка ───────────── */

  // Статус запроса читается словами: «applied» человеку ничего не говорит, а «ушло в выкат» — говорит.
  const PUBLISH_WORDS = {queued: "ждёт сборки", applied: "ушло в выкат", failed: "сборка не прошла"};

  const openPublishCount = (rows) => (rows || []).filter((row) => row.status === "queued").length;

  function publishWord(rows) {
    const open = openPublishCount(rows);
    return open ? ` · на выкат поставлено: ${open}` : " · публикаций не ждёт";
  }

  // Подпись редактора и хвост вывода сборки приходят из базы и из лога: в innerHTML их вставлять
  // надо текстом, иначе одна строка note сломает всю панель.
  const safe = (text) => String(text ?? "").replace(/[&<>]/g,
    (char) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[char]));

  // Список очереди в панели: его перерисовывает обновление состояния, чтобы после второго клика
  // человек видел новый запрос, а не тот список, с которым открывал панель.
  let publishBox = null;

  function publishSummary() {
    const rows = state.publish;
    if (!rows.length) return "очередь пуста: запрос не поставился";
    const last = rows[rows.length - 1];
    return `запрос #${last.id} · правок в выкат <b>${last.corrections_live}</b> · `
      + `отпечаток ${safe(last.revision)} · ${PUBLISH_WORDS[last.status] || safe(last.status)}`
      + (last.note ? ` · «${safe(last.note)}»` : "");
  }

  function paintPublishQueue() {
    if (!publishBox || !publishBox.isConnected) return undefined;
    publishBox.innerHTML = "";
    const rows = state.publish;
    if (!rows.length) {
      publishBox.appendChild(el("p", "nst-edit-note", "очередь пуста — правок на выкат не ставили"));
    }
    // Последние сверху: человек открыл панель смотреть свой запрос, а не историю за сезон.
    for (const row of [...rows].reverse()) {
      publishBox.appendChild(el("div", "nst-edit-publish-row",
        `#${row.id} · ${safe(row.created_at)} · <b>${safe(row.editor)}</b> · `
        + `${PUBLISH_WORDS[row.status] || safe(row.status)} · правок ${row.corrections_live} · `
        + `отпечаток ${safe(row.revision)}`
        + (row.note ? ` · «${safe(row.note)}»` : "")
        + (row.applied_at ? ` · взято ${safe(row.applied_at)}` : "")
        + (row.detail ? ` · <i>${safe(row.detail.split("\n")[0])}</i>` : "")));
    }
    const result = panel.querySelector(".nst-edit-publish-result");
    if (result) result.innerHTML = publishSummary();
    const head = panel.querySelector(".nst-edit-head strong");
    if (head && panel.querySelector(".nst-edit-publish")) {
      head.textContent = `очередь публикаций: ждёт ${openPublishCount(state.publish)}`;
    }
    return undefined;
  }

  // Ответ на второй клик: те же числа, что уходят в запрос, и напоминание, что витрину обновляет
  // сборка, а не эта кнопка.
  function renderPublish(answer, box) {
    box.appendChild(el("p", "nst-edit-h", answer.persisted ? "запрос публикации"
                                                           : "предпросмотр: очередь не изменена"));
    box.appendChild(el("div", "nst-edit-diff", `отпечаток базы: <b>${safe(answer.revision)}</b>`));
    box.appendChild(el("div", "nst-edit-publish-result", "считаем, сколько правок уходит в выкат…"));
    box.appendChild(el("p", "nst-edit-warn",
      "на сайт ничего ещё не выложено: цифры обновит сборка — python db/publish.py apply или "
      + "обычный python build_all.py. Запрос виден в очереди выше"));
    return box;
  }

  async function showPublish() {
    let answer;
    try {
      answer = await call("/api/publish");
    } catch (error) {
      return say(error.message, "error");
    }
    state.publish = answer.requests || [];
    const box = el("div", "nst-edit-publish");
    box.appendChild(el("p", "nst-edit-note",
      `живых правок в базе: ${answer.corrections_live}. Пока они в журнале, выкатывать есть что; `
      + "ноль правок — панель откажет ставить запрос"));
    const form = el("div", "nst-edit-form");
    form.appendChild(el("span", "nst-edit-h", "что публикуем"));
    const note = field("input", "nst-edit-players nst-edit-wide",
      {type: "text", placeholder: "одна строка: например, сезон 9 разобран до конца"});
    form.appendChild(note);
    // Два шага, как у удаления: первый клик вооружает кнопку, второй ставит запрос. Поведение общее,
    // а цвет другой: выкат ничего не разрушает.
    const ask = dangerButton("опубликовать", () => ({
      operation: "publish-request", args: {note: note.value.trim()}, persist: true,
    }));
    ask.classList.add("nst-edit-publish-ask");
    form.appendChild(ask);
    box.appendChild(form);
    box.appendChild(el("p", "nst-edit-note",
      "запрос ничего на сайт не выкладывает: он говорит сборке, какой срез базы вы считаете "
      + "готовым. Второй запрос на тот же срез панель откажет — сборка закроет первый"));
    publishBox = el("div", "nst-edit-publish-queue");
    box.appendChild(publishBox);
    box.appendChild(el("div", "nst-edit-delta"));
    openPanel(`очередь публикаций: ждёт ${openPublishCount(state.publish)}`, box);
    return paintPublishQueue();
  }

  buildBar();
  document.body.appendChild(bar);
  document.body.appendChild(panel);
  document.body.classList.add("nst-edit-on");
  /* Ловим на фазе захвата: в режиме правки клик по строке матча значит «правь эту строку»,
     а не «открой карточку соперника», как обещает inline-обработчик страницы. */
  document.addEventListener("click", (event) => {
    if (event.target.closest("button, a, input, .nst-edit-bar, .nst-edit-panel")) return;
    if (!event.target.closest(".h2h-match-item, .h2h-match-row, .match-history-row")) return;
    // Занятый сервер: клик по строке не порождает второй запрос и не открывает профиль игрока.
    if (isBusy()) {
      event.preventDefault();
      event.stopPropagation();
      return paintStatus();
    }
    const row = event.target.closest(".h2h-match-item");
    if (row) {
      event.stopPropagation();
      return openRow(row);
    }
    const history = event.target.closest(".match-history-row");
    if (history) {
      event.stopPropagation();
      return openHistory(history);
    }
    const duel = event.target.closest(".h2h-match-row");
    if (duel) {
      event.stopPropagation();
      return openDuel(duel);
    }
  }, true);
  refreshState();
})();
