// ============================================================
//  cl_chat.js — ChL raqib VS-oynasi (liga openOpponentModal / division.js naqshi)
//
//  O'yin kartasidagi LOGOLAR JUFTLIGIGA bosilganda ochiladi:
//    • "Chatni ochish"        → WebApp chati (api.js openWebChat, prefiks /cl/matches)
//    • "Raqib chatiga yozish" → Telegram (t.me/username)
//  Global: CL, clIsMe, clClubBadge (cl.js), escHtml, ICON, openWebChat, APP.
// ============================================================

function clOpenOpponentModal(matchId) {
  const m = (CL.myMatches || []).find(x => x.id === matchId);
  if (!m) return;
  const t = APP.t || {};

  // 2026-07-16: Yopiq (hali ochilmagan) turda VS/chat oynasi ochilmaydi —
  // boshqa kirish nuqtalari uchun ham himoya (karta markazi allaqachon yopiq).
  const st = CL.state || {};
  if (m.status === "pending" && !(st.started && m.matchday === st.current_matchday)) {
    showToast(t.matchday_locked_short || "Bu tur hali ochilmagan");
    return;
  }

  // Qaysi tomon men, qaysi biri raqib (me_id backend'dan — taxmin yo'q)
  const iAmP1 = clIsMe(m.player1_id);
  const me  = { name: iAmP1 ? m.player1_name : m.player2_name,
                club: iAmP1 ? m.player1_club : m.player2_club,
                username: iAmP1 ? m.player1_username : m.player2_username };
  const opp = { name: iAmP1 ? m.player2_name : m.player1_name,
                club: iAmP1 ? m.player2_club : m.player1_club,
                username: iAmP1 ? m.player2_username : m.player1_username };

  let modal = document.getElementById("modal-cl-opponent");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-cl-opponent";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }

  const side = (p) => `
    <div class="opp-side">
      <div class="cl-vs-logo">${clClubBadge(p.club, 72)}</div>
      <div class="opp-club">${escHtml(p.club || p.name || "—")}</div>
      <div class="opp-user">${p.username ? "@" + escHtml(p.username) : "—"}</div>
    </div>`;

  const tgBtn = opp.username
    ? `<button class="opp-chat-btn" id="cl-opp-tg">${ICON.get("chat", 18)} ${escHtml(t.opp_write_button || "Raqib chatiga yozish")}</button>`
    : `<div class="opp-no-contact">${escHtml(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi")}</div>`;

  modal.innerHTML = `
    <div class="modal-box opp-modal-box">
      <button class="modal-close" id="cl-opp-close">${ICON.get("close", 18)}</button>
      <div class="opp-vs">
        ${side(me)}
        <div class="opp-vs-sep">VS</div>
        ${side(opp)}
      </div>
      <button class="opp-chat-btn opp-webchat-btn" id="cl-opp-webchat">
        ${ICON.get("chat", 18)} ${escHtml(t.webchat_open || "Chatni ochish")}
      </button>
      ${tgBtn}
    </div>`;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  const close = () => modal.classList.add("hidden");
  document.getElementById("cl-opp-close").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });

  document.getElementById("cl-opp-webchat").addEventListener("click", () => {
    close();
    openWebChat(m.id, opp.name || "Raqib", "/cl/matches");   // api.js webchat (DRY)
  });
  document.getElementById("cl-opp-tg")?.addEventListener("click", () => {
    const tg = window.Telegram?.WebApp;
    const link = `https://t.me/${String(opp.username).replace(/^@/, "")}`;
    if (tg?.openTelegramLink) {
      try { tg.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); }
    } else {
      window.open(link, "_blank");
    }
    close();
  });
}
