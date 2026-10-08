// =============================================================
//  pt_support.js — SHAXSIY turnir: ishtirokchi <-> tashkilotchi chati (2026-10-08)
//  Admin so'rovi: qatnashuvchilar nizolar, savollar va boshqa masalalar bo'yicha tashkilotchiga
//  yoza olsin. Chat oynasi — o'yin chati bilan bir xil (api.js openWebChat, prefiks /pt/support).
//  Ishtirokchi: Asosiy sahifada "Tashkilotchiga yozish" kartasi (yangi javoblar soni bilan).
//  Boshqaruvchi (tashkilotchi / turnir admini / bosh admin): Admin sahifasida
//  "Ishtirokchilar xabarlari" — suhbatlar ro'yxati, o'qilmaganlar yuqorida, Admin rozetkasida soni.
//  Global: PT, PTT, escHtml, apiFetch, showToast, openWebChat, ptOpenDetail.
// =============================================================

function ptIsSupportMember(t) {
  return !!t && !(t.is_manager || t.is_owner) && !!t.my_status && t.status !== "cancelled";
}

// Asosiy: ishtirokchi kartasi
function ptSupportCardHtml(t) {
  if (!ptIsSupportMember(t)) return "";
  const n = t.support_unread || 0;
  const owner = t.owner_username ? "@" + t.owner_username : (t.owner_nickname || "");
  return `<div class="card pt-support-card">
      <div class="pt-support-head"><span class="pt-next-kicker">${escHtml(PTT("pt_sup_kicker"))}</span>
        ${n ? `<span class="pt-sup-new">${escHtml(PTT("pt_sup_new", { n }))}</span>` : ""}</div>
      <div class="pt-support-text">${escHtml(PTT("pt_sup_text", { owner }))}</div>
      <button class="btn btn--primary pt-support-btn" id="pt-support-open">✉️ ${escHtml(PTT("pt_sup_btn"))}</button>
    </div>`;
}

// Admin: suhbatlar ro'yxati (ochilganda yuklanadi)
function ptSupportAdminHtml(t) {
  if (!(t.is_manager || t.is_owner)) return "";
  return `<div id="pt-support-threads"><div class="empty-state">…</div></div>`;
}

async function ptLoadSupportThreads(t) {
  const box = document.getElementById("pt-support-threads");
  if (!box) return;
  try {
    const { threads } = await apiFetch(`/pt/${encodeURIComponent(t.id)}/support/threads`);
    if (!threads.length) {
      box.innerHTML = `<div class="pt-hint pt-sup-empty">${escHtml(PTT("pt_sup_none"))}</div>`;
      return;
    }
    box.innerHTML = `<div class="card pt-sup-list">${threads.map(th => {
      const user = th.username ? "@" + th.username : (th.nickname || "");
      const logo = th.team_name && typeof ptTeamBadge === "function" ? ptTeamBadge(th.team_name) : "";
      const mine = th.last_role === "staff" ? `${escHtml(PTT("pt_sup_you"))}: ` : "";
      return `<button class="pt-sup-row${th.unread ? " pt-sup-row--new" : ""}" data-pt-sup-thread="${th.thread_id}"
          data-pt-sup-label="${escHtml(user)}">
          <span class="pt-sup-avatar">${logo || escHtml((user.replace("@", "")[0] || "?").toUpperCase())}</span>
          <span class="pt-sup-main"><span class="pt-sup-name">${escHtml(user)}${th.team_name ? ` <span class="pt-muted">· ${escHtml(th.team_name)}</span>` : ""}</span>
            <span class="pt-sup-last">${mine}${escHtml(th.last_text || "")}</span></span>
          <span class="pt-sup-side"><span class="pt-sup-time">${escHtml(th.last_local || "")}</span>
            ${th.unread ? `<span class="chat-badge pt-sup-badge">${th.unread > 9 ? "9+" : th.unread}</span>` : ""}</span>
        </button>`;
    }).join("")}</div>`;
    box.querySelectorAll("[data-pt-sup-thread]").forEach(b => b.addEventListener("click", () =>
      ptOpenSupportChat(t, Number(b.dataset.ptSupThread), b.dataset.ptSupLabel)));
  } catch (e) {
    box.innerHTML = `<div class="empty-state">${escHtml(PTT("pt_load_err"))}</div>`;
  }
}

// Chat oynasi (umumiy openWebChat); yopilganda turnir qayta yuklanadi — rozetkalar yangilanadi
function ptOpenSupportChat(t, threadId, label) {
  if (typeof openWebChat !== "function") return;
  openWebChat(threadId, label, "/pt/support");
  const modal = document.getElementById("modal-webchat");
  const refresh = () => { if (PT.detail && String(PT.detail.id) === String(t.id)) void ptOpenDetail(t.id); };
  document.getElementById("webchat-close")?.addEventListener("click", refresh, { once: true });
  modal?.addEventListener("click", e => { if (e.target === modal) refresh(); }, { once: true });
}

async function ptOpenMySupport(t) {
  if (PT.busy) return;                                    // ikki marta bosish (qoida #38)
  PT.busy = true;
  try {
    const r = await apiFetch(`/pt/${encodeURIComponent(t.id)}/support/open`, { method: "POST" });
    const owner = r.owner_username ? "@" + r.owner_username : (r.owner_nickname || "");
    ptOpenSupportChat(t, r.thread_id, `${PTT("pt_sup_title")} · ${owner}`);
  } catch (e) {
    showToast(PTT("pt_err_generic"));
  } finally {
    PT.busy = false;
  }
}

function ptBindSupport(t) {
  document.getElementById("pt-support-open")?.addEventListener("click", () => void ptOpenMySupport(t));
  if (PT.tab === "admin") void ptLoadSupportThreads(t);
}

// Matnlar (texts_pt_ui.js 300 qator chegarasiga yaqin — qoida #21; xuddi shu usulda qo'shiladi)
const PT_SUP_TEXTS = {
  uz: { pt_sup_kicker: "💬 SAVOL YOKI NIZO?", pt_sup_btn: "Tashkilotchiga yozish", pt_sup_title: "Tashkilotchi",
        pt_sup_text: "Raqib bilan kelisha olmadingizmi, natija bo'yicha nizo bormi yoki savolingiz bormi — tashkilotchiga ({owner}) yozing. Tashkilotchi va turnir adminlari javob beradi.",
        pt_sup_new: "{n} ta yangi javob", pt_sup_none: "Hozircha ishtirokchilardan xabar yo'q. Ular Asosiy sahifadagi «Tashkilotchiga yozish» tugmasi orqali yozadi.",
        pt_sup_you: "Siz", pt_adm_sec_support: "💬 ISHTIROKCHILAR XABARLARI" },
  ru: { pt_sup_kicker: "💬 ВОПРОС ИЛИ СПОР?", pt_sup_btn: "Написать организатору", pt_sup_title: "Организатор",
        pt_sup_text: "Не договорились с соперником, спор по результату или есть вопрос — напишите организатору ({owner}). Ответят организатор и админы турнира.",
        pt_sup_new: "Новых ответов: {n}", pt_sup_none: "Пока сообщений от участников нет. Они пишут через кнопку «Написать организатору» на Главной.",
        pt_sup_you: "Вы", pt_adm_sec_support: "💬 СООБЩЕНИЯ УЧАСТНИКОВ" },
  en: { pt_sup_kicker: "💬 QUESTION OR DISPUTE?", pt_sup_btn: "Message the organizer", pt_sup_title: "Organizer",
        pt_sup_text: "Can't agree with your opponent, a result dispute or a question — write to the organizer ({owner}). The organizer and tournament admins will reply.",
        pt_sup_new: "{n} new replies", pt_sup_none: "No messages from players yet. They write via the “Message the organizer” button on Home.",
        pt_sup_you: "You", pt_adm_sec_support: "💬 PLAYER MESSAGES" },
};
for (const lang of ["uz", "ru", "en"]) {
  if (typeof PT_TEXTS !== "undefined" && PT_TEXTS[lang]) Object.assign(PT_TEXTS[lang], PT_SUP_TEXTS[lang]);
  if (typeof TEXTS !== "undefined" && TEXTS[lang]) Object.assign(TEXTS[lang], PT_SUP_TEXTS[lang]);
}
