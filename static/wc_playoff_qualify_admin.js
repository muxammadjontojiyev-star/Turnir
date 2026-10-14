/**
 * wc_playoff_qualify_admin.js — JCh admin: "SETKANI TEKSHIRISH" (2026-10-14, faqat bosh admin).
 *
 * Setkadagi (1/16) jamoalar hozirgi guruh jadvallariga mosmi:
 *   GET  /wc/admin/playoff/qualify-check → noto'g'ri chiqqanlar (wrong) va chiqmay qolganlar (missing)
 *   POST /wc/admin/playoff/qualify-fix   → har noto'g'risi o'z 1/16 o'rnida to'g'risi bilan almashadi
 * Konteyner: #wc-po-qualify-box (worldcup_admin.js wcRenderAdminPanel).
 * Global: apiFetch, escHtml, showToast, renderWcFlagBadge (worldcup_admin.js).
 */

const WCQ_KIND = { winner: "1-o'rin", runner_up: "2-o'rin", third: "eng yaxshi 3-o'rin" };
const WCQ_ERR = {
  has_result: "1/16 o'yinida natija bor — avval natijani bekor qiling",
  count_mismatch: "noto'g'ri va yetishmayotganlar soni teng emas — qo'lda almashtiring",
  groups_not_ready: "guruhlarda hali tasdiqlanmagan o'yin bor",
  nothing_to_fix: "tuzatadigan narsa yo'q",
  not_started: "play-off hali boshlanmagan",
};

function wcqTeamHtml(o, extra) {
  const flag = typeof renderWcFlagBadge === "function" ? renderWcFlagBadge(o.team_name) : "";
  return `<div class="wcq-row">${flag}<b>${escHtml(o.team_name || "?")}</b>
    <span class="wcq-meta">${escHtml(o.group_letter || "?")}-guruh, ${escHtml(String(o.position || "?"))}-o'rin${extra ? " · " + escHtml(extra) : ""}</span></div>`;
}

async function wcqCheck(btn) {
  const box = document.getElementById("wcq-result");
  if (!box) return;
  btn.disabled = true;
  try {
    const d = await apiFetch("/wc/admin/playoff/qualify-check");
    if (!d.started) { box.innerHTML = `<div class="adm-pp-empty">Play-off hali boshlanmagan</div>`; return; }
    if (d.groups_ready === false) { box.innerHTML = `<div class="adm-pp-empty">⏳ Guruhlarda hali tasdiqlanmagan o'yin bor</div>`; return; }
    if (d.ok) { box.innerHTML = `<div class="adm-pp-empty">✅ Setka guruh jadvallariga to'liq mos</div>`; return; }
    box.innerHTML = `
      <div class="adm-pp-hint">❌ Setkada turibdi, lekin chiqmasligi kerak:</div>
      ${d.wrong.map(w => wcqTeamHtml(w, w.played ? "1/16 natijasi bor" : "")).join("")}
      <div class="adm-pp-hint" style="margin-top:8px">✅ Chiqishi kerak, lekin setkada yo'q:</div>
      ${d.missing.map(m => wcqTeamHtml(m, WCQ_KIND[m.kind] || "")).join("")}
      <button class="btn btn--primary" id="wcq-fix" style="width:100%;margin-top:10px">🔧 Setkani tuzatish</button>
      <div class="adm-pp-hint" style="margin-top:6px;text-align:center">Noto'g'ri jamoa o'rniga to'g'risi o'sha 1/16 o'yinga qo'yiladi. Guruh natijalari o'zgarmaydi.</div>`;
  } catch (e) {
    showToast("❌ " + e.message);
  } finally {
    btn.disabled = false;
  }
}

async function wcqFix(btn) {
  if (!window.confirm("Setka tuzatilsinmi? Noto'g'ri chiqqan jamoa o'rniga to'g'risi qo'yiladi.")) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/wc/admin/playoff/qualify-fix", { method: "POST" });
    const lines = (r.changes || []).map(c => `${c.out} → ${c.in}${c.same_group_opponent ? " (⚠️ raqibi bilan bir guruhdan)" : ""}`);
    window.alert("✅ Setka tuzatildi:\n" + lines.join("\n"));
    const check = document.getElementById("wcq-check");
    if (check) void wcqCheck(check);
  } catch (e) {
    showToast("❌ " + (WCQ_ERR[e.message] || e.message));
    btn.disabled = false;
  }
}

function wcqInit() {
  const box = document.getElementById("wc-po-qualify-box");
  if (!box) return;
  box.innerHTML = `
    <button class="btn btn--ghost" id="wcq-check" style="width:100%">🔎 Setkani guruh jadvallari bilan tekshirish</button>
    <div id="wcq-result" class="wcq-result"></div>`;
  if (!window._wcqBound) {
    window._wcqBound = true;
    document.addEventListener("click", (e) => {
      if (!e.target.closest) return;
      const c = e.target.closest("#wcq-check");
      if (c) { void wcqCheck(c); return; }
      const f = e.target.closest("#wcq-fix");
      if (f) void wcqFix(f);
    });
  }
}
