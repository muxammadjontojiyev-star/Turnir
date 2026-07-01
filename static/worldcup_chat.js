// ============================================================
//  worldcup_chat.js — World Cup chati (frontend)
//
//  Liga api.js'dagi chat (openWebChat / openOpponentModal) naqshida, lekin
//  WC endpointlariga (/wc/matches/...) ulangan. Liga chat kodiga tegmaydi.
//
//  Global konstantalar (CHAT_POLL_INTERVAL_MS, TYPING_SEND_THROTTLE_MS) va
//  yordamchilar (escHtml, apiFetch, ICON, API_BASE, showToast, formatChatTime,
//  formatLastSeen, wcTeamFlag) bir sahifada — qayta ishlatamiz.
// ============================================================

// Joriy WC chat holati
const WC_CHAT = {
  matchId: null,
  oppLabel: null,
  lastTypingSent: 0,
  poll: null,
  isPlayoff: 0,
};

// Raqib modali (VS — "Chatni ochish" / "Raqib chatiga yozish")
function wcOpenOpponentModal(matchId) {
  const t = APP.t;
  const m = (WC.myMatches || []).find(x => x.id === matchId);
  if (!m) return;

  const myTgId = (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) || null;
  const iAmP1 = m.player1_telegram_id === myTgId;
  const opp = iAmP1
    ? { tg: m.player2_telegram_id, username: m.player2_username, nickname: m.player2_nickname, club: m.player2_club }
    : { tg: m.player1_telegram_id, username: m.player1_username, nickname: m.player1_nickname, club: m.player1_club };

  // Telegram chatiga yozish tugmasi
  const chatBtn = (opp.username || opp.tg)
    ? `<button class="opp-chat-btn" id="wc-opp-chat-btn">${ICON.get("chat", 18)} ${escHtml(t.opp_write_button || "Raqib chatiga yozish")}</button>`
    : `<div class="opp-no-contact">${escHtml(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi")}</div>`;

  // WebApp ichki chat — faqat aktiv match (pending / awaiting_confirmation)
  const chatActive = (m.status === "pending" || m.status === "awaiting_confirmation");
  const webChatBtn = chatActive
    ? `<button class="opp-chat-btn opp-webchat-btn" id="wc-opp-webchat-btn">${ICON.get("chat", 18)} ${escHtml(t.webchat_open || "Chatni ochish")}</button>`
    : "";

  let modal = document.getElementById("wc-modal-opponent");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "wc-modal-opponent";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box opp-modal-box">
      <button class="modal-close" id="wc-opp-modal-close">${ICON.get("close", 18)}</button>
      <div class="opp-vs">
        ${wcRenderOpponentSide(m.player1_club, m.player1_username, m.player1_nickname)}
        <div class="opp-vs-sep">VS</div>
        ${wcRenderOpponentSide(m.player2_club, m.player2_username, m.player2_nickname)}
      </div>
      ${webChatBtn}
      ${chatBtn}
    </div>
  `;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  document.getElementById("wc-opp-modal-close").addEventListener("click", wcCloseOpponentModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) wcCloseOpponentModal(); });

  // "Raqib chatiga yozish" → Telegram
  const btn = document.getElementById("wc-opp-chat-btn");
  if (btn && (opp.username || opp.tg)) {
    btn.addEventListener("click", () => wcOpenTelegramChat(opp));
  }

  // "Chatni ochish" → WebApp ichki chat
  const webBtn = document.getElementById("wc-opp-webchat-btn");
  if (webBtn) {
    const oppLabel = opp.nickname || (opp.username ? "@" + String(opp.username).replace(/^@/, "") : (t.webchat_opponent || "Raqib"));
    webBtn.addEventListener("click", () => {
      wcCloseOpponentModal();
      wcOpenWebChat(matchId, oppLabel);
    });
  }
}

function wcRenderOpponentSide(club, username, nickname) {
  const flag = wcTeamFlag(club);
  const name = nickname || club || "?";
  const uname = username ? `<span class="opp-username">@${escHtml(String(username).replace(/^@/, ""))}</span>` : "";
  return `
    <div class="opp-side">
      <div class="opp-flag">${flag}</div>
      <div class="opp-name">${escHtml(name)}</div>
      ${uname}
    </div>`;
}

function wcCloseOpponentModal() {
  const modal = document.getElementById("wc-modal-opponent");
  if (modal) modal.classList.add("hidden");
}

// "Raqib chatiga yozish" tugmasi bosilganda chatga o'tadi (chatOpened belgilaydi)
function wcOpenMatchChat(matchId) {
  const m = (WC.myMatches || []).find(x => x.id === matchId);
  if (!m) return;
  const myTgId = (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) || null;
  const iAmP1 = m.player1_telegram_id === myTgId;
  const opp = iAmP1
    ? { tg: m.player2_telegram_id, username: m.player2_username }
    : { tg: m.player1_telegram_id, username: m.player1_username };

  // Chat ochilgan deb belgilaymiz — Natija tugmasi ochiladi
  if (!WC.chatOpened) WC.chatOpened = new Set();
  WC.chatOpened.add(matchId);

  wcOpenTelegramChat(opp);
  void wcLoadMatches();  // Ro'yxatni yangilab, "Natija" tugmasini ochish
}

// Telegram chatiga o'tish (username yoki tg id orqali)
function wcOpenTelegramChat(opp) {
  const t = APP.t;
  const tg = window.Telegram?.WebApp;
  if (opp.username) {
    const link = `https://t.me/${String(opp.username).replace(/^@/, "")}`;
    if (tg && typeof tg.openTelegramLink === "function") {
      try { tg.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); }
    } else {
      window.open(link, "_blank");
    }
  } else if (opp.tg) {
    const tgLink = `tg://user?id=${opp.tg}`;
    if (tg && typeof tg.openLink === "function") {
      try { tg.openLink(tgLink); } catch (_) { window.open(tgLink, "_blank"); }
    } else {
      window.open(tgLink, "_blank");
    }
  } else {
    showToast(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi");
  }
}

// ---- WebApp ichki chat oynasi ----
function wcOpenWebChat(matchId, opponentLabel, isPlayoff = 0) {
  const t = APP.t;
  WC_CHAT.matchId = matchId;
  WC_CHAT.oppLabel = opponentLabel || (t.webchat_opponent || "Raqib");
  WC_CHAT.lastTypingSent = 0;
  WC_CHAT.isPlayoff = isPlayoff ? 1 : 0;

  // Chat ochildi — Natija tugmasi ochiladi
  if (!WC.chatOpened) WC.chatOpened = new Set();
  WC.chatOpened.add(matchId);

  let modal = document.getElementById("wc-modal-webchat");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "wc-modal-webchat";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box webchat-box">
      <div class="webchat-header">
        <img class="webchat-avatar hidden" id="wc-webchat-avatar" alt="">
        <div class="webchat-headinfo">
          <span class="webchat-title">${escHtml(WC_CHAT.oppLabel)}</span>
          <span class="webchat-username" id="wc-webchat-username"></span>
          <span class="webchat-status" id="wc-webchat-status"></span>
        </div>
        <button class="modal-close" id="wc-webchat-close">${ICON.get("close", 18)}</button>
      </div>
      <div class="webchat-messages" id="wc-webchat-messages">
        <div class="webchat-loading">${escHtml(t.webchat_loading || "Yuklanmoqda...")}</div>
      </div>
      <div class="webchat-input-row">
        <input type="text" id="wc-webchat-input" class="webchat-input"
               placeholder="${escHtml(t.webchat_placeholder || "Xabar yozing...")}"
               maxlength="2000" autocomplete="off" />
        <button class="webchat-send" id="wc-webchat-send">${ICON.get("chat", 18)}</button>
      </div>
    </div>
  `;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  document.getElementById("wc-webchat-close").addEventListener("click", wcCloseWebChat);
  modal.addEventListener("click", (e) => { if (e.target === modal) wcCloseWebChat(); });

  const input = document.getElementById("wc-webchat-input");
  const sendBtn = document.getElementById("wc-webchat-send");
  sendBtn.addEventListener("click", wcSendWebChatMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); wcSendWebChatMessage(); }
  });
  input.addEventListener("input", () => {
    const now = Date.now();
    if (now - WC_CHAT.lastTypingSent > TYPING_SEND_THROTTLE_MS) {
      WC_CHAT.lastTypingSent = now;
      apiFetch(`/wc/matches/${matchId}/typing?is_playoff=${WC_CHAT.isPlayoff}`, { method: "POST" }).catch(() => {});
    }
  });

  wcLoadWebChatMessages();
  wcLoadWebChatState();
  if (WC_CHAT.poll) clearInterval(WC_CHAT.poll);
  WC_CHAT.poll = setInterval(() => {
    wcLoadWebChatMessages();
    wcLoadWebChatState();
  }, CHAT_POLL_INTERVAL_MS);
}

function wcCloseWebChat() {
  if (WC_CHAT.poll) { clearInterval(WC_CHAT.poll); WC_CHAT.poll = null; }
  WC_CHAT.matchId = null;
  const modal = document.getElementById("wc-modal-webchat");
  if (modal) modal.classList.add("hidden");
  void wcLoadMatches();  // Natija tugmasi yangilanishi uchun
}

async function wcLoadWebChatMessages() {
  const matchId = WC_CHAT.matchId;
  if (!matchId) return;
  try {
    const data = await apiFetch(`/wc/matches/${matchId}/messages?is_playoff=${WC_CHAT.isPlayoff}`);
    wcRenderWebChatMessages(data.messages || []);
  } catch (e) {
    const box = document.getElementById("wc-webchat-messages");
    if (box) box.innerHTML = `<div class="webchat-loading">${escHtml(APP.t.webchat_closed || "Chat yopilgan")}</div>`;
    if (WC_CHAT.poll) { clearInterval(WC_CHAT.poll); WC_CHAT.poll = null; }
  }
}

async function wcLoadWebChatState() {
  const matchId = WC_CHAT.matchId;
  if (!matchId) return;
  try {
    const state = await apiFetch(`/wc/matches/${matchId}/state?is_playoff=${WC_CHAT.isPlayoff}`);
    wcRenderWebChatStatus(state);
  } catch (_) { /* jim */ }
}

function wcRenderWebChatStatus(state) {
  const el = document.getElementById("wc-webchat-status");
  if (!el || !state) return;
  const t = APP.t;

  const avatar = document.getElementById("wc-webchat-avatar");
  if (avatar && state.opponent_user_id && !avatar.dataset.loaded) {
    avatar.dataset.loaded = "1";
    avatar.src = `${API_BASE}/players/${state.opponent_user_id}/photo`;
    avatar.onload = () => avatar.classList.remove("hidden");
    avatar.onerror = () => avatar.classList.add("hidden");
  }
  const userEl = document.getElementById("wc-webchat-username");
  if (userEl && !userEl.dataset.loaded) {
    userEl.dataset.loaded = "1";
    if (state.opponent_username) {
      userEl.textContent = "@" + String(state.opponent_username).replace(/^@/, "");
    } else {
      userEl.style.display = "none";
    }
  }

  if (state.typing) {
    el.innerHTML = `${escHtml(t.webchat_typing || "yozmoqda")}<span class="typing-dots"><i></i><i></i><i></i></span>`;
    el.className = "webchat-status typing";
    return;
  }
  if (state.online) {
    el.textContent = t.webchat_online || "online";
    el.className = "webchat-status online";
    return;
  }
  const secs = state.last_seen_seconds;
  if (secs === null || secs === undefined) {
    el.textContent = t.webchat_offline || "oflayn";
    el.className = "webchat-status";
    return;
  }
  el.textContent = (typeof formatLastSeen === "function") ? formatLastSeen(secs) : "";
  el.className = "webchat-status";
}

function wcRenderWebChatMessages(messages) {
  const box = document.getElementById("wc-webchat-messages");
  if (!box) return;
  const t = APP.t;

  if (!messages.length) {
    box.innerHTML = `<div class="webchat-empty">${escHtml(t.webchat_empty || "Hali xabar yo'q. Birinchi bo'lib yozing!")}</div>`;
    return;
  }

  const atBottom = (box.scrollHeight - box.scrollTop - box.clientHeight) < 60;

  box.innerHTML = messages.map(msg => {
    const mine = msg.mine;
    const ticks = mine ? (msg.is_read ? "✓✓" : "✓") : "";
    const tickCls = (mine && msg.is_read) ? "webchat-ticks read" : "webchat-ticks";
    const time = (typeof formatChatTime === "function") ? formatChatTime(msg.created_at) : "";
    const flag = msg.club_name ? wcTeamFlag(msg.club_name) : "";
    const flagSpan = flag ? `<span class="webchat-club-logo" title="${escHtml(msg.club_name || "")}">${flag}</span>` : "";
    return `
      <div class="webchat-msg ${mine ? "mine" : "theirs"}">
        ${flagSpan}
        <div class="webchat-bubble">
          <span class="webchat-text">${escHtml(msg.text)}</span>
          <span class="webchat-meta">
            ${time ? `<span class="webchat-time">${time}</span>` : ""}
            ${mine ? `<span class="${tickCls}">${ticks}</span>` : ""}
          </span>
        </div>
      </div>`;
  }).join("");

  if (atBottom) box.scrollTop = box.scrollHeight;
}

async function wcSendWebChatMessage() {
  const matchId = WC_CHAT.matchId;
  const input = document.getElementById("wc-webchat-input");
  if (!matchId || !input) return;
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  try {
    await apiFetch(`/wc/matches/${matchId}/messages?is_playoff=${WC_CHAT.isPlayoff}`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    await wcLoadWebChatMessages();
  } catch (e) {
    showToast("❌ " + (e.message || "Xato"));
    input.value = text;  // Qaytaramiz
  }
}
