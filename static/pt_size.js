// =============================================================
//  pt_size.js — SHAXSIY turnir sig'imi (2026-10-03; pt.js'dan ajratildi — qoida #21)
//  Sig'im 8..128, qadam 4 (guruhlar to'liq). Bir martalik to'langan turnirda faqat
//  o'sha narx pog'onasi (server: tier_locked). Global: PT, PTT, apiFetch, escHtml,
//  showToast, ptOpenDetail, ptTierOf/ptTierPrice (pt_sub.js).
// =============================================================

// <select>: min..max, qadam = guruh o'lchami (4) — guruhlar doim to'liq bo'lsin.
// minAllowed — qabul qilinganlardan kam tanlab bo'lmaydi (yuqoriga 4 ga yaxlitlanadi).
// allow(n) — ixtiyoriy filtr (narx pog'onasi yopiq sig'imlar ko'rinmasin)
// 2026-10-07: rule — format qoidasi {min, max, step} (pt_formats.js ptFmtRule); bo'lmasa erkin format
function ptSizeSelectHtml(id, selected, minAllowed, allow, rule) {
  const c = PT.config || {};
  const r = rule || { min: c.min_players || 8, max: c.max_players || 128, step: c.group_size || 4 };
  const step = r.step;
  const lo = Math.max(r.min, r.min + Math.ceil(Math.max(0, (minAllowed || 0) - r.min) / step) * step), hi = r.max;
  if ((Number(selected) - r.min) % step) selected = r.min + Math.ceil((Number(selected) - r.min) / step) * step;   // eski sig'im
  let opts = "";
  for (let n = lo; n <= hi; n += step) {
    if (allow && !allow(n)) continue;
    opts += `<option value="${n}" ${n === Number(selected) ? "selected" : ""}>${escHtml(PTT("pt_size_n", { n }))}</option>`;
  }
  return `<select class="modal-input pt-select" id="${id}">${opts}</select>`;
}

// Bir martalik: to'lovgacha — narxi bor pog'onalar; to'langach — faqat o'sha pog'ona (server: tier_locked)
function ptEditSizeFilter(t) {
  // obuna-turnir yoki narx pog'onalari serverdan kelmagan (eski backend) — cheklovsiz
  if (t.paid_via === "subscription" || typeof ptTierOf !== "function" || !ptHasTiers()) return null;
  if (["awaiting_payment", "rejected"].includes(t.status)) return n => ptTierPrice(n) > 0;
  const cur = ptTierOf(t.max_players);
  return n => ptTierOf(n) === cur;
}

function ptCanEditSize(t) {
  return t.is_owner && (t.format || "classic") !== "league" &&     // liga: sig'im = klublar soni (qat'iy)
    ["awaiting_payment", "payment_review", "rejected", "recruiting"].includes(t.status);
}

async function ptSaveSize(tid) {
  if (PT.busy) return;
  const max_players = Number(document.getElementById("pt-size-edit")?.value || 0);
  PT.busy = true;
  try {
    await apiFetch(`/pt/${encodeURIComponent(tid)}/capacity`, { method: "POST", body: JSON.stringify({ max_players }) });
    showToast(PTT("pt_size_saved"));
  } catch (e) {
    const map = { bad_size: "pt_err_bad_size", below_members: "pt_err_below_members", already_started: "pt_err_started",
                  tier_locked: "pt_err_tier_locked", price_not_set: "pt_price_not_set" };
    showToast(PTT(map[e && e.message] || "pt_err_generic"));
  } finally {
    PT.busy = false;
  }
  await ptOpenDetail(tid);
}


// Sig'im tahriri bloki (faqat tashkilotchi, qur'agacha) — Admin sahifasida
function ptSizeEditHtml(t) {
  if (!ptCanEditSize(t)) return "";
  return `<div class="card pt-pay">
      <label class="pt-field-label" for="pt-size-edit">${escHtml(PTT("pt_size_label"))}</label>
      <div class="pt-fix-row">${ptSizeSelectHtml("pt-size-edit", t.max_players, t.approved_count, ptEditSizeFilter(t),
        typeof ptFmtRule === "function" ? ptFmtRule(t.format || "classic", t.league_name) : null)}
        <button class="btn btn--ghost" id="pt-size-save">${escHtml(PTT("pt_size_save"))}</button></div>
    </div>`;
}
