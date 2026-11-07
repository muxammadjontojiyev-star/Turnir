// =============================================================
//  crule_admin.js — bosh admin: tex win «javobsiz qoldirish» qoidasi uchun JAVOB KECHIKISHI CHEGARASI (2026-11-07).
//  Admin → «📸 SKRINSHOT VA TEXNIK G'ALABA» (mshot_admin.js shu kartani qo'shadi). Server: chat_rules.reply_max_h,
//  GET /crule/config, POST /crule/admin/config. Global: apiFetch, escHtml, showToast, crT, crErr.
// =============================================================

const CRA_TEXTS = {
  uz: { t: "⏱ Javob kechikishi chegarasi", h: "Tex win «javobsiz qoldirish» qoidasi faqat raqib xabariga shu vaqt ichida javob bergan o'yinchiga ishlaydi. Kech javob bergan — faqat «3 marta yozish» qoidasi bilan.", u: "soat", s: "Saqlash", ok: "✅ Saqlandi" },
  ru: { t: "⏱ Предел задержки ответа", h: "Правило «оставил без ответа» действует только для игрока, ответившего сопернику в пределах этого времени. Ответившему позже — только правило «3 сообщений».", u: "ч", s: "Сохранить", ok: "✅ Сохранено" },
  en: { t: "⏱ Reply delay limit", h: "The «left unanswered» tech-win rule only applies to a player who replied to the opponent within this time. A late replier needs the «3 messages» rule.", u: "h", s: "Save", ok: "✅ Saved" },
};
function craT(k) { return ((typeof APP !== "undefined" && CRA_TEXTS[APP.lang]) || CRA_TEXTS.uz)[k]; }

async function crAdminHtml() {
  try {
    if (!(await apiFetch("/admin/whoami")).is_super) return "";
    const c = await apiFetch("/crule/config");
    return `<div class="card msa-only cra-card"><div class="msa-line"><b>${escHtml(craT("t"))}</b></div>
      <div class="adm-pp-hint">${escHtml(craT("h"))}</div>
      <div class="cra-row"><input type="number" class="modal-input cra-h" min="${Number(c.min)}" max="${Number(c.max)}"
        value="${Number(c.reply_max_h)}" inputmode="numeric"> <span>${escHtml(craT("u"))}</span>
        <button class="btn btn--primary" data-cra-save="1">${escHtml(craT("s"))}</button></div></div>`;
  } catch (_) { return ""; }
}

document.addEventListener("click", async (e) => {
  const b = e.target.closest ? e.target.closest("[data-cra-save]") : null;
  if (!b) return;
  e.preventDefault();
  const v = Number(b.closest(".cra-card")?.querySelector(".cra-h")?.value || 0);
  b.disabled = true;
  try {
    const r = await apiFetch("/crule/admin/config", { method: "POST", body: JSON.stringify({ reply_max_h: v }) });
    const inp = b.closest(".cra-card").querySelector(".cra-h");
    if (inp) inp.value = r.reply_max_h;
    showToast(craT("ok"));
  } catch (err) { showToast(typeof crErr === "function" ? crErr(err) : String(err.message || err)); }
  b.disabled = false;
});
