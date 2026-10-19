// =============================================================
//  qm.js — TEZKOR O'YIN (2026-10-19)
//  Suzuvchi tugma (bo'lim tanlash va ligalar bosh sahifasida) -> alohida oyna:
//    "Raqib qidirish" -> boshqa qidirayotgan bilan juftlanadi -> VS (rasmlar, reyting),
//    3 daqiqada xona ID (aks holda bekor), natija + raqib tasdig'i, chat (openWebChat "/qm/matches").
//    "Reyting" tabi — tezkor o'yin reytingi.
//  Backend: qm_api.py (/qm/state, /qm/search, /qm/cancel, /qm/room, /qm/submit, /qm/confirm, /qm/rating).
//  Global: APP, API_BASE, apiFetch, escHtml, showToast, ICON, openWebChat.
// =============================================================

const QM_POLL_MS = 2500;
const QM_FAB_CHECK_MS = 700;
const QM = { open: false, tab: "play", st: null, sig: "", poll: null, tick: null, rating: null, searchStart: 0 };

const QM_TXT = {
  uz: {
    title: "TEZKOR O'YIN", tab_play: "O'yin", tab_rating: "Reyting", search: "🔍 Raqib qidirish",
    searching: "Raqib qidirilmoqda…", cancel: "Bekor qilish", online: "onlaynda", waiting: "qidiryapti",
    my_rating: "Reytingim", rules: [
      "Qidirayotgan boshqa o'yinchi bilan avtomatik juftlanasiz.",
      "Raqib topilgach 3 daqiqa ichida eFootball'da xona ochib, xona ID ni yuboring — aks holda o'yin bekor bo'ladi.",
      "Natijani bittangiz kiritadi, ikkinchisi tasdiqlaydi. 10 daqiqada javob bo'lmasa — avtomatik tasdiqlanadi.",
      "Ball gol farqiga bog'liq: g'alaba +10 va har gol farqi uchun +2 (1:0 → +12, 5:0 → +20), mag'lubiyat −5 va har gol uchun −2 (ko'pi bilan −15), durang +3. Gol farqi 5 tagacha hisoblanadi. Bir raqib bilan kuniga 3 ta o'yin reytingga kiradi."],
    found: "Raqib topildi!", room_title: "Xona ID ni yuboring", room_hint: "eFootball'da do'stona xona oching va ID ni shu yerga yozing. Raqibingiz ham yuborishi mumkin.",
    room_ph: "Xona ID", send: "Yuborish", room_left: "Qolgan vaqt", room_code: "Xona ID", copy: "Nusxalash", copied: "✅ Nusxalandi",
    result_title: "Natijani kiriting", you: "Siz", opp: "Raqib", submit: "Natijani yuborish", play_left: "Natija uchun",
    wait_confirm: "⏳ Raqib tasdig'i kutilmoqda", auto_in: "avtomatik tasdiq", opp_submitted: "Raqib natija kiritdi:",
    your_first: "(sizning hisobingiz birinchi)", confirm: "✅ Tasdiqlash", reject: "❌ Rad etish", chat: "💬 Chat",
    win: "G'alaba!", draw: "Durang", loss: "Mag'lubiyat", not_rated: "reytingga kirmadi (kunlik chegara)",
    cancelled: "O'yin bekor qilindi", c_no_room: "3 daqiqa ichida xona ID yuborilmadi.", c_no_result: "Natija vaqtida kiritilmadi.",
    c_cancelled: "O'yinchilardan biri bekor qildi.", again: "🔍 Yana qidirish", pts: "ball",
    ask_submit: "Natija: Siz {m} : {o} Raqib. Yuborilsinmi?", ask_reject: "Natija rad etilsinmi? Chatda kelishib oling.",
    ask_cancel: "O'yin bekor qilinsinmi?", sent: "✅ Yuborildi", top: "TOP-50", pos: "O'rnim", no_games: "Hali o'yin yo'q",
    played: "o'yin", recent: "SO'NGGI O'YINLARIM",
    errors: { bad_score: "Hisob 0–30 oralig'ida bo'lsin", no_match: "Faol o'yin yo'q", no_room_yet: "Avval xona ID yuborilishi kerak",
      already_submitted: "Natija allaqachon kiritilgan", nothing_to_confirm: "Tasdiqlanadigan natija yo'q",
      own_submission: "O'zingiz kiritgan natijani raqib tasdiqlaydi", match_closed: "O'yin yopilgan",
      invalid_code: "Xona ID noto'g'ri (4–16 ta harf/raqam)", match_not_found: "O'yin topilmadi" },
  },
  ru: {
    title: "БЫСТРАЯ ИГРА", tab_play: "Игра", tab_rating: "Рейтинг", search: "🔍 Найти соперника",
    searching: "Ищем соперника…", cancel: "Отмена", online: "онлайн", waiting: "в поиске",
    my_rating: "Мой рейтинг", rules: [
      "Вас автоматически соединят с другим игроком в поиске.",
      "После нахождения соперника за 3 минуты создайте комнату в eFootball и отправьте ID — иначе игра отменится.",
      "Результат вводит один, второй подтверждает. Без ответа 10 минут — подтверждается автоматически.",
      "Очки зависят от разницы мячей: победа +10 и +2 за каждый мяч разницы (1:0 → +12, 5:0 → +20), поражение −5 и −2 за мяч (не более −15), ничья +3. Разница учитывается до 5 мячей. С одним соперником в рейтинг идут 3 игры в день."],
    found: "Соперник найден!", room_title: "Отправьте ID комнаты", room_hint: "Создайте дружескую комнату в eFootball и впишите ID сюда. Соперник тоже может отправить.",
    room_ph: "ID комнаты", send: "Отправить", room_left: "Осталось", room_code: "ID комнаты", copy: "Копировать", copied: "✅ Скопировано",
    result_title: "Введите результат", you: "Вы", opp: "Соперник", submit: "Отправить результат", play_left: "На результат",
    wait_confirm: "⏳ Ждём подтверждения соперника", auto_in: "автоподтверждение", opp_submitted: "Соперник ввёл результат:",
    your_first: "(ваш счёт первым)", confirm: "✅ Подтвердить", reject: "❌ Отклонить", chat: "💬 Чат",
    win: "Победа!", draw: "Ничья", loss: "Поражение", not_rated: "не в рейтинг (дневной лимит)",
    cancelled: "Игра отменена", c_no_room: "ID комнаты не отправлен за 3 минуты.", c_no_result: "Результат не введён вовремя.",
    c_cancelled: "Один из игроков отменил.", again: "🔍 Искать снова", pts: "очк.",
    ask_submit: "Результат: Вы {m} : {o} Соперник. Отправить?", ask_reject: "Отклонить результат? Договоритесь в чате.",
    ask_cancel: "Отменить игру?", sent: "✅ Отправлено", top: "ТОП-50", pos: "Моё место", no_games: "Пока нет игр",
    played: "игр", recent: "МОИ ПОСЛЕДНИЕ ИГРЫ",
    errors: { bad_score: "Счёт от 0 до 30", no_match: "Нет активной игры", no_room_yet: "Сначала отправьте ID комнаты",
      already_submitted: "Результат уже введён", nothing_to_confirm: "Нечего подтверждать",
      own_submission: "Ваш результат подтверждает соперник", match_closed: "Игра закрыта",
      invalid_code: "Неверный ID комнаты (4–16 букв/цифр)", match_not_found: "Игра не найдена" },
  },
  en: {
    title: "QUICK MATCH", tab_play: "Play", tab_rating: "Rating", search: "🔍 Find opponent",
    searching: "Searching for an opponent…", cancel: "Cancel", online: "online", waiting: "searching",
    my_rating: "My rating", rules: [
      "You're automatically paired with another searching player.",
      "Once matched, create a room in eFootball and send its ID within 3 minutes — or the match is cancelled.",
      "One player submits the result, the other confirms. No reply in 10 minutes — confirmed automatically.",
      "Points depend on goal difference: win +10 plus +2 per goal of margin (1:0 → +12, 5:0 → +20), loss −5 and −2 per goal (at most −15), draw +3. Margin counts up to 5 goals. Up to 3 games a day vs the same opponent count for rating."],
    found: "Opponent found!", room_title: "Send the room ID", room_hint: "Create a friendly room in eFootball and type its ID here. Your opponent can send it too.",
    room_ph: "Room ID", send: "Send", room_left: "Time left", room_code: "Room ID", copy: "Copy", copied: "✅ Copied",
    result_title: "Enter the result", you: "You", opp: "Opponent", submit: "Submit result", play_left: "For result",
    wait_confirm: "⏳ Waiting for opponent's confirmation", auto_in: "auto-confirm", opp_submitted: "Opponent submitted:",
    your_first: "(your score first)", confirm: "✅ Confirm", reject: "❌ Reject", chat: "💬 Chat",
    win: "Victory!", draw: "Draw", loss: "Defeat", not_rated: "not rated (daily limit)",
    cancelled: "Match cancelled", c_no_room: "No room ID was sent within 3 minutes.", c_no_result: "The result wasn't submitted in time.",
    c_cancelled: "One of the players cancelled.", again: "🔍 Search again", pts: "pts",
    ask_submit: "Result: You {m} : {o} Opponent. Send?", ask_reject: "Reject the result? Agree in the chat.",
    ask_cancel: "Cancel the match?", sent: "✅ Sent", top: "TOP-50", pos: "My place", no_games: "No games yet",
    played: "games", recent: "MY RECENT GAMES",
    errors: { bad_score: "Score must be 0–30", no_match: "No active match", no_room_yet: "Send the room ID first",
      already_submitted: "Result already submitted", nothing_to_confirm: "Nothing to confirm",
      own_submission: "Your opponent confirms your result", match_closed: "Match closed",
      invalid_code: "Invalid room ID (4–16 letters/digits)", match_not_found: "Match not found" },
  },
};

function qmT(k) { const d = QM_TXT[APP.lang] || QM_TXT.uz; return d[k] != null ? d[k] : QM_TXT.uz[k]; }
function qmErr(e) { return qmT("errors")[e && e.message] || (e && e.message) || ""; }
function qmWho(u) { return u ? (u.username ? "@" + u.username : (u.nickname || "—")) : "—"; }
function qmClock(s) { s = Math.max(0, s | 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; }

function qmAvatar(uid, name, cls) {
  const letter = escHtml(((name || "?").replace(/^@/, "").trim()[0] || "?").toUpperCase());
  return `<span class="qm-ava ${cls || ""}"><i>${letter}</i>${uid ? `<img src="${API_BASE}/players/${+uid}/photo" alt=""
    loading="lazy" onerror="this.remove()">` : ""}</span>`;
}

// ---------------------------------------------------------------- suzuvchi tugma
function qmFabEnsure() {
  let fab = document.getElementById("qm-fab");
  if (!fab) {
    fab = document.createElement("button");
    fab.id = "qm-fab";
    fab.className = "qm-fab hidden";
    fab.setAttribute("aria-label", "Tezkor o'yin");
    fab.innerHTML = `<span class="qm-fab-core">⚡</span><span class="qm-fab-ring"></span><i class="qm-fab-dot hidden"></i>`;
    fab.addEventListener("click", qmOpen);
    document.body.appendChild(fab);
  }
  return fab;
}

function qmFabShouldShow() {
  if (QM.open) return false;
  const hub = document.getElementById("hub-select");
  if (hub && !hub.classList.contains("hidden") && hub.offsetParent !== null) return true;
  const home = document.getElementById("section-home");
  return !!(home && home.classList.contains("active") && home.offsetParent !== null
    && !document.querySelector(".modal:not(.hidden)"));
}

function qmFabUpdate() {
  const fab = qmFabEnsure();
  fab.classList.toggle("hidden", !qmFabShouldShow());
  const busy = QM.st && (QM.st.match || QM.st.searching);
  fab.querySelector(".qm-fab-dot").classList.toggle("hidden", !busy);
}

// ---------------------------------------------------------------- oyna
function qmOpen() {
  let root = document.getElementById("qm-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "qm-root";
    root.className = "qm-root";
    document.body.appendChild(root);
    root.addEventListener("click", qmClick);
  }
  root.classList.remove("hidden");
  QM.open = true;
  QM.sig = "";
  qmFabUpdate();
  qmRender();
  void qmPoll();
  clearInterval(QM.poll);
  QM.poll = setInterval(() => { if (QM.tab === "play") void qmPoll(); }, QM_POLL_MS);
  clearInterval(QM.tick);
  QM.tick = setInterval(qmTickTimers, 1000);
}

function qmClose() {
  QM.open = false;
  clearInterval(QM.poll);
  clearInterval(QM.tick);
  document.getElementById("qm-root")?.classList.add("hidden");
  qmFabUpdate();
}

async function qmPoll() {
  try {
    QM.st = await apiFetch("/qm/state");
    QM.stAt = Date.now();
  } catch (_) { return; }
  const s = QM.st;
  // taymerlar sig'ga kirmaydi — kiritilayotgan matn (xona ID, hisob) qayta chizilmasin
  const sig = JSON.stringify([QM.tab, s.searching, s.match && { ...s.match, room_left: 0, play_left: 0, confirm_left: 0 },
    s.last && s.last.id, s.last && s.last.status, s.me.rating, s.unread]);
  if (sig !== QM.sig) { QM.sig = sig; qmRender(); }
  else qmUpdateCounters();
  qmFabUpdate();
}

function qmLeft(key) {
  const m = QM.st && QM.st.match;
  if (!m || m[key] == null) return null;
  return m[key] - Math.floor((Date.now() - (QM.stAt || Date.now())) / 1000);
}

function qmTickTimers() {
  for (const key of ["room_left", "play_left", "confirm_left"]) {
    const el = document.getElementById("qm-t-" + key);
    if (el) {
      const v = qmLeft(key);
      el.textContent = qmClock(v);
      el.classList.toggle("is-low", v != null && v <= 30);
    }
  }
  const se = document.getElementById("qm-search-time");
  if (se && QM.searchStart) se.textContent = qmClock((Date.now() - QM.searchStart) / 1000);
}

function qmUpdateCounters() {
  const s = QM.st;
  const el = document.getElementById("qm-counters");
  if (el && s) el.innerHTML = qmCountersHtml(s);
}

function qmCountersHtml(s) {
  return `<span><i class="qm-dot-on"></i>${s.online} ${escHtml(qmT("online"))}</span>
    <span>🔍 ${s.waiting} ${escHtml(qmT("waiting"))}</span>`;
}

function qmRender() {
  const root = document.getElementById("qm-root");
  if (!root) return;
  const body = QM.tab === "rating" ? qmRatingHtml() : qmPlayHtml();
  root.innerHTML = `
    <div class="qm-head">
      <button class="qm-x" data-qm="close" aria-label="close">${ICON.get("close", 18)}</button>
      <div class="qm-title">⚡ ${escHtml(qmT("title"))}</div>
      <span></span>
    </div>
    <div class="qm-tabs">
      <button class="qm-tab${QM.tab === "play" ? " active" : ""}" data-qm-tab="play">${escHtml(qmT("tab_play"))}</button>
      <button class="qm-tab${QM.tab === "rating" ? " active" : ""}" data-qm-tab="rating">${escHtml(qmT("tab_rating"))}</button>
    </div>
    <div class="qm-body">${body}</div>`;
  qmTickTimers();
}

// ---------------------------------------------------------------- o'yin tabi
function qmPlayHtml() {
  const s = QM.st;
  if (!s) return `<div class="empty-state">…</div>`;
  if (s.match) return qmMatchHtml(s.match, s);
  const me = s.me;
  const last = s.last ? qmLastHtml(s.last) : "";
  if (s.searching) {
    if (!QM.searchStart) QM.searchStart = Date.now();
    return `<div class="qm-radar"><span></span><span></span><span></span>${qmAvatar(me.user_id, qmWho(me), "qm-ava--xl")}</div>
      <div class="qm-search-title">${escHtml(qmT("searching"))} <b id="qm-search-time">0:00</b></div>
      <div class="qm-counters" id="qm-counters">${qmCountersHtml(s)}</div>
      <button class="btn btn--ghost qm-wide" data-qm="cancel">${escHtml(qmT("cancel"))}</button>`;
  }
  QM.searchStart = 0;
  return `${last}
    <div class="card qm-me">
      ${qmAvatar(me.user_id, qmWho(me), "qm-ava--lg")}
      <div><small>${escHtml(qmT("my_rating"))}</small><b>${me.rating}</b>
        <span>${me.wins}–${me.draws}–${me.losses}</span></div>
    </div>
    <button class="qm-search-btn" data-qm="search">${escHtml(qmT("search"))}</button>
    <div class="qm-counters" id="qm-counters">${qmCountersHtml(s)}</div>
    <ul class="qm-rules">${qmT("rules").map(r => `<li>${escHtml(r)}</li>`).join("")}</ul>`;
}

function qmVsHtml(m, s) {
  const opp = m.opponent;
  return `<div class="qm-vs">
      <div class="qm-side">${qmAvatar(s.me.user_id, qmWho(s.me), "qm-ava--lg")}<b>${escHtml(qmT("you"))}</b><span>${s.me.rating}</span></div>
      <div class="qm-vs-x">VS</div>
      <div class="qm-side">${qmAvatar(opp.id, qmWho(opp), "qm-ava--lg")}<b>${escHtml(qmWho(opp))}</b><span>${opp.rating}</span></div>
    </div>`;
}

function qmMatchHtml(m, s) {
  const opp = m.opponent;
  const chat = `<div class="qm-actions">
      <button class="btn btn--ghost" data-qm="chat">${escHtml(qmT("chat"))}${s.unread ? ` <i class="qm-badge">${s.unread}</i>` : ""}</button>
      ${opp.username ? `<button class="btn btn--ghost" data-qm-tg="${escHtml(opp.username)}">✈️ Telegram</button>` : ""}
    </div>`;
  let body = "";
  if (m.status === "room") {
    body = `<div class="card qm-step">
        <div class="qm-step-head"><b>${escHtml(qmT("room_title"))}</b>
          <span class="qm-timer" id="qm-t-room_left">${qmClock(m.room_left)}</span></div>
        <div class="qm-hint">${escHtml(qmT("room_hint"))}</div>
        <div class="qm-row"><input id="qm-room" class="modal-input" inputmode="numeric" autocomplete="off" maxlength="20"
          placeholder="${escHtml(qmT("room_ph"))}"><button class="btn btn--primary" data-qm="room">${escHtml(qmT("send"))}</button></div>
        <button class="tb-mini qm-cancel" data-qm="cancel-match">${escHtml(qmT("cancel"))}</button>
      </div>`;
  } else {
    const code = m.room_code ? `<div class="qm-code"><span>${escHtml(qmT("room_code"))}: <b>${escHtml(m.room_code)}</b></span>
        <button class="tb-mini" data-qm="copy">${escHtml(qmT("copy"))}</button></div>` : "";
    if (m.status === "playing") {
      body = `<div class="card qm-step">${code}
          <div class="qm-step-head"><b>${escHtml(qmT("result_title"))}</b>
            <span class="qm-timer" id="qm-t-play_left">${qmClock(m.play_left)}</span></div>
          <div class="qm-score">
            <div><span>${escHtml(qmT("you"))}</span><input class="score-input" id="qm-m" type="number" inputmode="numeric" min="0" max="30" value="0"></div>
            <b>:</b>
            <div><span>${escHtml(qmT("opp"))}</span><input class="score-input" id="qm-o" type="number" inputmode="numeric" min="0" max="30" value="0"></div>
          </div>
          <button class="btn btn--primary qm-wide" data-qm="submit">${escHtml(qmT("submit"))}</button>
        </div>`;
    } else if (m.submitted_by_me) {
      body = `<div class="card qm-step">${code}
          <div class="qm-final">${m.my_score} : ${m.opp_score}</div>
          <div class="qm-hint qm-center">${escHtml(qmT("wait_confirm"))} · ${escHtml(qmT("auto_in"))}
            <b class="qm-timer" id="qm-t-confirm_left">${qmClock(m.confirm_left)}</b></div>
        </div>`;
    } else {
      body = `<div class="card qm-step">${code}
          <div class="qm-hint qm-center">${escHtml(qmT("opp_submitted"))} ${escHtml(qmT("your_first"))}</div>
          <div class="qm-final">${m.my_score} : ${m.opp_score}</div>
          <div class="qm-actions">
            <button class="btn btn--primary" data-qm-confirm="1">${escHtml(qmT("confirm"))}</button>
            <button class="btn btn--ghost" data-qm-confirm="0">${escHtml(qmT("reject"))}</button>
          </div>
          <div class="qm-hint qm-center">${escHtml(qmT("auto_in"))} <b class="qm-timer" id="qm-t-confirm_left">${qmClock(m.confirm_left)}</b></div>
        </div>`;
    }
  }
  return `<div class="qm-found">${escHtml(qmT("found"))}</div>${qmVsHtml(m, s)}${body}${chat}`;
}

function qmLastHtml(m) {
  if (m.status === "cancelled") {
    const why = { no_room: "c_no_room", no_result: "c_no_result", cancelled: "c_cancelled" }[m.cancel_reason] || "c_cancelled";
    return `<div class="card qm-last is-cancel"><b>⛔ ${escHtml(qmT("cancelled"))}</b><span>${escHtml(qmT(why))}</span></div>`;
  }
  const res = m.my_score > m.opp_score ? "win" : m.my_score < m.opp_score ? "loss" : "draw";
  const d = m.my_delta || 0;
  return `<div class="card qm-last is-${res}">
      <b>${res === "win" ? "🏆" : res === "draw" ? "🤝" : "💔"} ${escHtml(qmT(res))} ${m.my_score} : ${m.opp_score}</b>
      <span>${escHtml(qmWho(m.opponent))} · ${m.rated ? `${d > 0 ? "+" : ""}${d} ${escHtml(qmT("pts"))}` : escHtml(qmT("not_rated"))}</span>
    </div>`;
}

// ---------------------------------------------------------------- reyting tabi
async function qmLoadRating() {
  try { QM.rating = await apiFetch("/qm/rating"); } catch (_) { QM.rating = { top: [], me: null, recent: [] }; }
  if (QM.tab === "rating") qmRender();
}

function qmRatingHtml() {
  const r = QM.rating;
  if (!r) return `<div class="empty-state">…</div>`;
  const me = r.me || {};
  const rows = (r.top || []).map((p, i) => `
      <div class="qm-rrow${me && p.user_id === (QM.st && QM.st.me.user_id) ? " is-me" : ""}">
        <b class="qm-rpos">${i + 1}</b>${qmAvatar(p.user_id, qmWho(p), "qm-ava--sm")}
        <span class="qm-rname">${escHtml(qmWho(p))}<small>${p.wins}–${p.draws}–${p.losses} · ${p.played} ${escHtml(qmT("played"))}</small></span>
        <b class="qm-rpts">${p.rating}</b>
      </div>`).join("");
  const recent = (r.recent || []).map(qmLastHtml).join("");
  return `<div class="card qm-me">
      ${qmAvatar(QM.st && QM.st.me.user_id, QM.st ? qmWho(QM.st.me) : "", "qm-ava--lg")}
      <div><small>${escHtml(qmT("pos"))}: ${me.position || "—"}</small><b>${me.rating ?? "—"}</b>
        <span>${me.wins || 0}–${me.draws || 0}–${me.losses || 0}</span></div>
    </div>
    ${recent ? `<div class="section-label">${escHtml(qmT("recent"))}</div>${recent}` : ""}
    <div class="section-label">${escHtml(qmT("top"))}</div>
    <div class="card qm-rlist">${rows || `<div class="qm-hint qm-center">${escHtml(qmT("no_games"))}</div>`}</div>`;
}

// ---------------------------------------------------------------- amallar
async function qmPost(path, body, btn) {
  if (btn) btn.disabled = true;
  try {
    const r = await apiFetch(path, { method: "POST", body: JSON.stringify(body || {}) });
    await qmPoll();
    return r;
  } catch (e) {
    showToast("❌ " + qmErr(e));
    if (btn) btn.disabled = false;
    return null;
  }
}

function qmClick(e) {
  const t = e.target;
  if (!t.closest) return;
  const tab = t.closest("[data-qm-tab]");
  if (tab) {
    QM.tab = tab.dataset.qmTab;
    QM.sig = "";
    qmRender();
    if (QM.tab === "rating") void qmLoadRating(); else void qmPoll();
    return;
  }
  const cf = t.closest("[data-qm-confirm]");
  if (cf) {
    const accept = cf.dataset.qmConfirm === "1";
    if (!accept && !window.confirm(qmT("ask_reject"))) return;
    void qmPost("/qm/confirm", { accept }, cf);
    return;
  }
  const tg = t.closest("[data-qm-tg]");
  if (tg) {
    const url = `https://t.me/${encodeURIComponent(tg.dataset.qmTg)}`;
    const w = window.Telegram?.WebApp;
    if (w?.openTelegramLink) w.openTelegramLink(url); else window.open(url, "_blank");
    return;
  }
  const b = t.closest("[data-qm]");
  if (!b) return;
  const a = b.dataset.qm, m = QM.st && QM.st.match;
  if (a === "close") qmClose();
  else if (a === "search") { QM.searchStart = Date.now(); void qmPost("/qm/search", {}, b); }
  else if (a === "cancel") { QM.searchStart = 0; void qmPost("/qm/cancel", {}, b); }
  else if (a === "cancel-match" && window.confirm(qmT("ask_cancel"))) void qmPost("/qm/cancel", {}, b);
  else if (a === "room" && m) {
    const code = (document.getElementById("qm-room")?.value || "").trim();
    if (!code) return;
    void qmPost("/qm/room", { match_id: m.id, code }, b).then(r => { if (r) showToast(qmT("sent")); });
  } else if (a === "submit" && m) {
    const mine = document.getElementById("qm-m")?.value, opp = document.getElementById("qm-o")?.value;
    if (mine === "" || opp === "") return;
    if (!window.confirm(qmT("ask_submit").replace("{m}", mine).replace("{o}", opp))) return;
    void qmPost("/qm/submit", { my_score: +mine, opp_score: +opp }, b).then(r => { if (r) showToast(qmT("sent")); });
  } else if (a === "copy" && m && m.room_code) {
    navigator.clipboard?.writeText(m.room_code).then(() => showToast(qmT("copied")), () => showToast(m.room_code));
  } else if (a === "chat" && m && typeof openWebChat === "function") {
    openWebChat(m.id, qmWho(m.opponent), "/qm/matches");
  }
}

setInterval(qmFabUpdate, QM_FAB_CHECK_MS);
