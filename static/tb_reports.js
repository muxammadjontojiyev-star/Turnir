// =============================================================
//  tb_reports.js — "TEAMLAR JANGI": «Boshqa odam o'ynadi» shikoyati (2026-10-25, 4-bosqich)
//  O'yinchi: Jang kartasida «🚩 Boshqa odam o'ynadi» -> izoh (ixtiyoriy) -> POST /tb/report.
//            Yuborilgan bo'lsa — holat yozuvi (g.my_report, /tb/my-games).
//  Admin (liga admini / bosh admin): Admin tabida «SHIKOYATLAR» — ikkala tomonning eFootball niki,
//            natija, skrinshot; qaror: asossiz | qayta o'ynash | texnik mag'lubiyat
//            (POST /tb/admin/report/resolve). Admin matnlari o'zbekcha (tb_i18n.js qoidasi).
//  Backend: tb_api_fairplay.py. tb_season.js (tbReportBtnHtml) va tb_admin.js (tbReportsLoad,
//  tbReportsAdminHtml) chaqiradi. Global: TB, apiFetch, escHtml, tbToast, tbConfirm, tbErr, tbWho,
//  tbBattleLoad, tbAdminRender, chatLoadImages.
// =============================================================

const TB_REPORT_NOTE_MAX = 300;

// ---------------- O'yinchi: Jang kartasi ----------------
function tbReportBtnHtml(g) {
  const r = g.my_report;
  if (r) {
    return `<div class="tb-report-state">${r.status === "open"
      ? "🚩 Shikoyat yuborilgan — admin ko'rib chiqmoqda" : "🚩 Shikoyat ko'rib chiqildi"}</div>`;
  }
  return `<button class="tb-mini tb-mini--danger tb-report-btn" data-tbr-open="${g.id}">🚩 Boshqa odam o'ynadi</button>`;
}

function tbReportFormHtml(gid) {
  return `<div class="tb-report-form" data-tbr-box="${gid}">
      <div class="tb-hint">Raqibingiz o'rniga boshqa odam o'ynagan bo'lsa, liga adminiga xabar boradi. Xonadagi nikni va nima bo'lganini yozing.</div>
      <textarea id="tbr-note-${gid}" class="modal-input tb-report-note" maxlength="${TB_REPORT_NOTE_MAX}" rows="3"
        placeholder="Masalan: xonaga boshqa nik kirdi"></textarea>
      <button class="btn btn--danger" data-tbr-send="${gid}">🚩 Shikoyat yuborish</button>
    </div>`;
}

async function tbReportSend(gid, btn) {
  if (!tbConfirm("Shikoyat liga adminiga yuborilsinmi? Bir o'yinga faqat bir marta yuboriladi.")) return;
  const note = (document.getElementById(`tbr-note-${gid}`)?.value || "").trim();
  btn.disabled = true;
  try {
    await apiFetch("/tb/report", { method: "POST", body: JSON.stringify({ game_id: gid, note }) });
    tbToast("✅ Shikoyat yuborildi");
    await tbBattleLoad();
  } catch (e) {
    tbToast("❌ " + tbErr(e));
    btn.disabled = false;
  }
}

// ---------------- Admin: shikoyatlar ro'yxati ----------------
async function tbReportsLoad(leagueId) {
  try { TB.adminReports = (await apiFetch(`/tb/admin/reports?league_id=${leagueId}`)).reports || []; }
  catch (_) { TB.adminReports = []; }                       // ro'yxat yuklanmasa — Admin tabi baribir ochiladi
}

function tbReportSideHtml(label, username, nick) {
  return `<div class="tb-rep-side"><small>${label}</small><b>${escHtml(tbWho({ username, nickname: nick }))}</b></div>`;
}

function tbReportCardHtml(r) {
  const res = r.game_status === "confirmed" ? `${r.score1}:${r.score2} ✅`
    : r.game_status === "awaiting_confirmation" ? `${r.score1}:${r.score2} ⏳` : "natija yo'q";
  const proof = r.proof_token
    ? `<div class="tb-proof-view"><span class="webchat-img webchat-img--loading" data-chat-img="${escHtml(r.proof_token)}">📷</span></div>`
    : `<div class="tb-hint">Skrinshot yo'q</div>`;
  return `<div class="card tb-rep">
      <div class="tb-rep-head"><b>O'yin #${r.game_id}</b><span>${r.round}-tur · ${r.slot}-juftlik · ${escHtml(r.created_at || "")}</span></div>
      <div class="tb-hint">${escHtml(r.home_team)} — ${escHtml(r.away_team)} · ${escHtml(res)}</div>
      <div class="tb-rep-sides">
        ${tbReportSideHtml("Shikoyatchi", r.reporter_username, r.reporter_nick)}
        ${tbReportSideHtml("Gumon qilingan", r.accused_username, r.accused_nick)}
      </div>
      ${r.note ? `<div class="tb-note">${escHtml(r.note)}</div>` : ""}
      ${proof}
      <div class="tb-hint">Yozishmalar hisoboti — bosh admin panelida, o'yin #${r.game_id} (Teamlar jangi).</div>
      <div class="tb-adm-acts">
        <button class="tb-mini" data-tbr-dec="dismiss" data-id="${r.id}">Asossiz</button>
        <button class="tb-mini" data-tbr-dec="replay" data-id="${r.id}">🔁 Qayta o'ynash</button>
        <button class="tb-mini tb-mini--danger" data-tbr-dec="tech" data-id="${r.id}">⛔ Texnik mag'lubiyat</button>
      </div>
    </div>`;
}

function tbReportsAdminHtml() {
  const list = TB.adminReports || [];
  return `<div class="section-label">🚩 SHIKOYATLAR (${list.length})</div>
    ${list.length ? list.map(tbReportCardHtml).join("") : `<div class="card tb-hint tb-hint--center">Ochiq shikoyat yo'q</div>`}`;
}

const TB_REPORT_DEC_ASK = {
  dismiss: "Shikoyat asossiz deb yopilsinmi? Natija o'zgarmaydi.",
  replay: "Natija bekor qilinib, o'yin qayta o'ynalsinmi?",
  tech: "Gumon qilingan o'yinchiga texnik mag'lubiyat berilsinmi? Bahs hisobi qayta hisoblanadi.",
};

async function tbReportDecide(id, dec, btn) {
  if (!confirm(TB_REPORT_DEC_ASK[dec])) return;
  btn.disabled = true;
  try {
    await apiFetch("/tb/admin/report/resolve", { method: "POST", body: JSON.stringify({ report_id: id, decision: dec }) });
    showToast("✅ Qaror saqlandi — shikoyatchiga xabar yuborildi");
    await tbReportsLoad(TB.adminLeagueId);
    tbAdminRender();
  } catch (e) {
    showToast("❌ " + (e.message === "round_closed"
      ? "Bahs yakunlangan — qayta o'ynab bo'lmaydi. «Texnik mag'lubiyat» yoki «Asossiz»ni tanlang." : tbErr(e)));
    btn.disabled = false;
  }
}

document.addEventListener("click", (e) => {
  if (!e.target.closest) return;
  const op = e.target.closest("#tb-root [data-tbr-open]");
  if (op) {
    const gid = +op.dataset.tbrOpen, box = document.querySelector(`[data-tbr-box="${gid}"]`);
    if (box) { box.remove(); return; }
    op.insertAdjacentHTML("afterend", tbReportFormHtml(gid));
    if (typeof tbI18nApply === "function") tbI18nApply(op.parentElement);
    return;
  }
  const sd = e.target.closest("#tb-root [data-tbr-send]");
  if (sd) { void tbReportSend(+sd.dataset.tbrSend, sd); return; }
  const dc = e.target.closest("#tb-root [data-tbr-dec]");
  if (dc) void tbReportDecide(+dc.dataset.id, dc.dataset.tbrDec, dc);
});

// ---------------- Xato kodlari va tarjima (o'yinchi matnlari) ----------------
Object.assign(TB_ERR, {
  already_reported: "Bu o'yin bo'yicha shikoyat allaqachon yuborilgan",
  note_too_long: "Izoh 300 belgidan oshmasin",
  report_not_found: "Shikoyat topilmadi", already_resolved: "Shikoyat allaqachon ko'rib chiqilgan",
  bad_decision: "Noto'g'ri qaror",
});
Object.assign(TB_I18N.ru, {
  "🚩 Shikoyat yuborilgan — admin ko'rib chiqmoqda": "🚩 Жалоба отправлена — админ рассматривает",
  "🚩 Shikoyat ko'rib chiqildi": "🚩 Жалоба рассмотрена", "🚩 Boshqa odam o'ynadi": "🚩 Играл другой человек",
  "Raqibingiz o'rniga boshqa odam o'ynagan bo'lsa, liga adminiga xabar boradi. Xonadagi nikni va nima bo'lganini yozing.": "Если вместо соперника играл другой человек, админ лиги получит сообщение. Укажите ник в комнате и что произошло.",
  "Masalan: xonaga boshqa nik kirdi": "Например: в комнату зашёл другой ник",
  "🚩 Shikoyat yuborish": "🚩 Отправить жалобу", "✅ Shikoyat yuborildi": "✅ Жалоба отправлена",
  "Shikoyat liga adminiga yuborilsinmi? Bir o'yinga faqat bir marta yuboriladi.": "Отправить жалобу админу лиги? На одну игру — только одна жалоба.",
  "Bu o'yin bo'yicha shikoyat allaqachon yuborilgan": "Жалоба по этой игре уже отправлена",
  "Izoh 300 belgidan oshmasin": "Комментарий — не более 300 символов",
});
Object.assign(TB_I18N.en, {
  "🚩 Shikoyat yuborilgan — admin ko'rib chiqmoqda": "🚩 Report sent — the admin is reviewing it",
  "🚩 Shikoyat ko'rib chiqildi": "🚩 Report reviewed", "🚩 Boshqa odam o'ynadi": "🚩 Someone else played",
  "Raqibingiz o'rniga boshqa odam o'ynagan bo'lsa, liga adminiga xabar boradi. Xonadagi nikni va nima bo'lganini yozing.": "If someone else played instead of your opponent, the league admin will be notified. Write the nickname in the room and what happened.",
  "Masalan: xonaga boshqa nik kirdi": "E.g. a different nickname joined the room",
  "🚩 Shikoyat yuborish": "🚩 Send report", "✅ Shikoyat yuborildi": "✅ Report sent",
  "Shikoyat liga adminiga yuborilsinmi? Bir o'yinga faqat bir marta yuboriladi.": "Send the report to the league admin? Only one report per match.",
  "Bu o'yin bo'yicha shikoyat allaqachon yuborilgan": "A report for this match was already sent",
  "Izoh 300 belgidan oshmasin": "Comment must be at most 300 characters",
});
