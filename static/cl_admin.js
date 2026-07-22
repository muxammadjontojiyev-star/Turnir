// ============================================================
//  cl_admin.js — Chempionlar ligasi admin paneli (ChL Profil tabi ichida)
//
//  worldcup_admin.js naqshi (qoida 10 — parallel joylar sinxron):
//    - Bosh admin (config ADMIN_TELEGRAM_IDS) → panel ko'rinadi
//    - Boshqa hamma → panel yashirin
//  Rol serverdan aniqlanadi: GET /admin/whoami (is_super). Kodda ID yo'q.
//
//  Amallar: Qur'a o'tkazish → POST /cl/draw (32 kvalifikant → 8 guruh × 4)
//  Global: apiFetch, showToast, escHtml, CL, clLoadThenRender
// ============================================================

const CL_ADMIN = { isSuper: false, loaded: false, fixId: "", fixInfo: null,
                   fixIsPlayoff: false };  // 2026-07-22: play-off checkbox holati (talab 1)

// Nav'da Admin tab ko'rsatish uchun rolni oldindan tekshiradi (bir marta)
async function clCheckAdmin() {
  if (CL_ADMIN.loaded) return CL_ADMIN.isSuper;
  try {
    const who = await apiFetch("/admin/whoami");
    CL_ADMIN.isSuper = !!who.is_super;
  } catch (_) {
    CL_ADMIN.isSuper = false;
  }
  CL_ADMIN.loaded = true;
  return CL_ADMIN.isSuper;
}

// Admin sahifasini chizadi (5-tab). Faqat super admin.
async function clRenderAdminPage() {
  const isSuper = await clCheckAdmin();
  const page = document.getElementById("cl-admin-page");
  if (!page) return;
  if (!isSuper) {
    page.innerHTML = `<div class="card">Bu sahifa faqat administrator uchun.</div>`;
    return;
  }
  clLoadAdminPanel();
}

async function clLoadAdminPanel() {
  const panel = document.getElementById("cl-admin-page") || document.getElementById("cl-admin-panel");
  if (!panel) return;

  await clCheckAdmin();
  if (!CL_ADMIN.isSuper) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }

  const drawn = !!(CL.groups && CL.groups.drawn);
  const st = CL.state || {};
  const started = !!st.started;
  panel.classList.remove("hidden");
  panel.innerHTML = `
    <div class="card" style="border-color:rgba(245,197,66,.45)">
      <b>${ICON.get("shield", 16)} ChL admin paneli</b>
      <div style="font-size:12.5px;opacity:.75;margin:4px 0 10px">
        ${drawn
          ? CT("cla_draw_done")
          : CT("cla_draw_hint")}
      </div>
      <button class="btn btn--primary" id="cl-admin-draw" ${drawn ? "disabled" : ""}>
        ${ICON.get("dice", 16)} Qur'a o'tkazish
      </button>
      ${drawn ? `
      <div style="font-size:12.5px;opacity:.75;margin:12px 0 8px">
        Kalendarni qayta qurish: guruh tarkibi saqlanadi, o'yinlar ikki doira
        (uy + mehmon, 6 tur) qilib qaytadan yoziladi. Natija kiritilgan bo'lsa ishlamaydi.
      </div>
      <button class="btn" id="cl-admin-rebuild">${ICON.get("recycle", 16)} Kalendarni qayta qurish (uy+mehmon)</button>

      <div style="font-size:12.5px;opacity:.75;margin:14px 0 6px">
        Ishtirokchini almashtirish: guruhdagi istalgan ishtirokchini (⚠️ = o'chirilgan
        akkount) yangi Telegram ID'ga bog'laydi. So'ng kalendarni qayta quring.
      </div>
      <div id="cl-orphans-box" style="margin-bottom:6px"></div>
      <input class="modal-input" id="cl-new-tg" type="number" inputmode="numeric"
             placeholder="Yangi Telegram ID" style="margin-bottom:8px">
      <button class="btn" id="cl-admin-reassign">👤 Akkountni almashtirish</button>

      <div style="font-size:12.5px;opacity:.75;margin:12px 0 8px">
        ${started
          ? CT("cla_started_hint").replace("{cur}", st.current_matchday).replace("{total}", st.total_matchdays)
          : CT("cla_start_hint")}
      </div>
      <button class="btn btn--primary" id="cl-admin-start" ${started ? "disabled" : ""}>
        ${ICON.get("play", 16)} O'yinlarni boshlash
      </button>` : ""}

      <div class="admin-hint" style="margin-top:14px">
        <b>${CT("cla_playoff")}</b> barcha guruh o'yinlari tugagach, har guruhdan top-2
        (16 o'yinchi) 1/8 setkasiga joylanadi. Har juftlik uy+mehmon, final — 1 o'yin.
      </div>
      <button class="btn btn--primary" id="cl-admin-po-start">${CT("cla_playoff_start")}</button>

      ${drawn ? clAdminFixForm() : ""}
    </div>`;

  if (typeof applyIcons === "function") applyIcons(panel);

  const btn = document.getElementById("cl-admin-draw");
  if (btn && !drawn) btn.addEventListener("click", () => void clAdminDraw(btn));

  const rbtn = document.getElementById("cl-admin-rebuild");
  if (rbtn) rbtn.addEventListener("click", () => void clAdminRebuild(rbtn));

  const rasgn = document.getElementById("cl-admin-reassign");
  if (rasgn) rasgn.addEventListener("click", () => void clAdminReassign(rasgn));

  if (document.getElementById("cl-orphans-box")) void clLoadOrphans();

  const sbtn = document.getElementById("cl-admin-start");
  if (sbtn && !started) sbtn.addEventListener("click", () => void clAdminStart(sbtn));

  // 2026-07-20: play-off boshlash (cl_playoff.js) — xatolar toast bilan tushuntiriladi
  const pobtn = document.getElementById("cl-admin-po-start");
  if (pobtn && typeof clpoAdminStart === "function")
    pobtn.addEventListener("click", () => void clpoAdminStart(pobtn));

  // Match ID orqali tuzatish (liga naqshi)
  const fixId = document.getElementById("cl-fix-match-id");
  if (fixId) fixId.addEventListener("input", (e) => clFixIdChanged(e.target.value));

  // 2026-07-22 (talab 1): "Play-off o'yini" checkbox — o'zgarsa preview qayta so'raladi
  const fixPo = document.getElementById("cl-fix-is-playoff");
  if (fixPo) fixPo.addEventListener("change", (e) => {
    CL_ADMIN.fixIsPlayoff = e.target.checked;
    if (CL_ADMIN.fixId) clFixIdChanged(CL_ADMIN.fixId);  // yangi jadvaldan info olib preview yangilanadi
    else clRerenderPanel();
  });
  const fixSubmit = document.getElementById("cl-fix-submit");
  if (fixSubmit) fixSubmit.addEventListener("click", () => void clAdminFixSubmit(fixSubmit));

  // Natijani bekor qilish (2026-07-16) — o'yin natija kiritilmagan holatga qaytadi
  const fixCancel = document.getElementById("cl-fix-cancel-result");
  if (fixCancel) fixCancel.addEventListener("click", () => void clAdminCancelResult(fixCancel));
}

// 2026-07-16: Admin ChL natijasini BEKOR QILADI (pending, — : —).
// Liga/WC/Divizion'dagi bekor qilish bilan bir xil oqim.
async function clAdminCancelResult(btn) {
  const t = APP.t || {};
  const id = parseInt(CL_ADMIN.fixId, 10);
  if (!id) { showToast("Match ID kiriting"); return; }
  if (!confirm(t.admin_reset_confirm || CT("cla_cancel_ask"))) return;
  btn.disabled = true;
  const po = CL_ADMIN.fixIsPlayoff ? 1 : 0;
  try {
    await apiFetch(`/cl/admin/match/cancel?match_id=${id}&is_playoff=${po}`, { method: "POST" });
    showToast(t.admin_reset_done || CT("cla_cancelled"));
    CL_ADMIN.fixId = "";
    CL_ADMIN.fixInfo = null;
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    const msg = { match_not_found: CT("cla_match_404_low") }[e.message] || e.message;
    showToast(CT("cl_error") + msg);
  }
}

// --- ChL "Match ID orqali tuzatish" (liga divAdminFixForm naqshi, ranglar ChL) ---
function clAdminFixForm() {
  const info = CL_ADMIN.fixInfo;
  let preview = "";
  if (info === "notfound") {
    preview = `<div style="font-size:12px;color:#ff6b6b;margin:6px 0">${CT("cl_match_404")}</div>`;
  } else if (info) {
    const p1 = info.player1_username ? "@" + info.player1_username : (info.player1_name || "—");
    const p2 = info.player2_username ? "@" + info.player2_username : (info.player2_name || "—");
    const cur = (info.score1 != null) ? `${info.score1} : ${info.score2}` : "— : —";
    const badge = (club) => (typeof clClubBadge === "function") ? clClubBadge(club, 30) : "";
    // 2026-07-22 (talab 1): play-off o'yinida bosqich+leg, guruhda tur ko'rsatiladi
    const meta = info.is_playoff
      ? `#${info.id} · ${escHtml(info.round_label || info.round || "Play-off")}${info.round !== "final" ? " · " + info.leg + "-o'yin" : ""}`
      : `#${info.id} · Guruh ${info.group_number} · ${info.matchday}-tur`;
    preview = `
      <div class="card" style="margin:8px 0;padding:10px 12px">
        <div style="opacity:.65;font-size:11.5px">${meta}</div>
        <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-top:6px">
          ${badge(info.player1_club)}
          <span style="font-weight:800;white-space:nowrap;font-size:16px">${cur}</span>
          ${badge(info.player2_club)}
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11.5px;opacity:.75;margin-top:4px">
          <span>${escHtml(p1)}</span><span>${escHtml(p2)}</span>
        </div>
      </div>`;
  }
  const disabled = !info || info === "notfound";
  return `
    <div class="section-label" style="margin-top:16px">MATCH ID ORQALI TUZATISH</div>
    <input id="cl-fix-match-id" class="modal-input" type="number" min="1"
           placeholder="Match ID" value="${CL_ADMIN.fixId || ""}" style="margin-bottom:6px" />
    <label class="admin-fix-playoff-check" style="display:flex;align-items:center;gap:8px;margin:2px 2px 8px;font-size:13.5px">
      <input id="cl-fix-is-playoff" type="checkbox" ${CL_ADMIN.fixIsPlayoff ? "checked" : ""} />
      <span>${escHtml((APP.t && APP.t.admin_fix_is_playoff) || "Play-off o'yini")}</span>
    </label>
    ${preview}
    <div class="score-input-row" style="display:flex;align-items:center;justify-content:center;gap:10px;margin:6px 0">
      <input id="cl-fix-score1" class="score-input" type="number" min="0" max="99"
             value="${info && info !== "notfound" && info.score1 != null ? info.score1 : 0}" />
      <span class="score-separator">:</span>
      <input id="cl-fix-score2" class="score-input" type="number" min="0" max="99"
             value="${info && info !== "notfound" && info.score2 != null ? info.score2 : 0}" />
    </div>
    <button class="btn btn--primary" id="cl-fix-submit" ${disabled ? "disabled" : ""}
            style="opacity:${disabled ? ".45" : "1"}">Tuzatish</button>
    <button class="btn btn--ghost" id="cl-fix-cancel-result" ${disabled ? "disabled" : ""}
            style="margin-top:8px;color:var(--red-neon);border-color:rgba(255,69,96,.3);opacity:${disabled ? ".45" : "1"}">
      ${escHtml((APP.t && APP.t.admin_reset_btn) || CT("cla_cancel_result"))}
    </button>`;
}

let _clFixTimer = null;
function clFixIdChanged(raw) {
  clearTimeout(_clFixTimer);
  CL_ADMIN.fixId = raw;
  const id = parseInt(raw, 10);
  if (!id || id <= 0) { CL_ADMIN.fixInfo = null; clRerenderPanel(); return; }
  _clFixTimer = setTimeout(async () => {
    const po = CL_ADMIN.fixIsPlayoff ? 1 : 0;
    try {
      CL_ADMIN.fixInfo = await apiFetch(`/cl/admin/match/${id}/info?is_playoff=${po}`);
      // Serverdan HAQIQIY is_playoff kelsa (fallback ishlagan bo'lsa) — checkbox'ni to'g'rilaymiz
      if (CL_ADMIN.fixInfo && typeof CL_ADMIN.fixInfo.is_playoff !== "undefined") {
        CL_ADMIN.fixIsPlayoff = !!CL_ADMIN.fixInfo.is_playoff;
      }
    } catch (_) {
      CL_ADMIN.fixInfo = "notfound";
    }
    clRerenderPanel();
  }, 350);
}

// Panelni qayta chizadi va ID inputga fokusni tiklaydi (qoida #40)
function clRerenderPanel() {
  void clLoadAdminPanel().then(() => {
    const el = document.getElementById("cl-fix-match-id");
    if (el) { el.focus(); const v = el.value; el.value = ""; el.value = v; }
  });
}

async function clAdminFixSubmit(btn) {
  const id = parseInt(CL_ADMIN.fixId, 10);
  const s1 = Number(document.getElementById("cl-fix-score1").value || 0);
  const s2 = Number(document.getElementById("cl-fix-score2").value || 0);
  const po = CL_ADMIN.fixIsPlayoff ? 1 : 0;
  if (!id) { showToast("Match ID kiriting"); return; }
  if (!confirm(`#${id} natijasi ${s1}:${s2} qilib tuzatilsinmi?`)) return;
  btn.disabled = true;
  btn.textContent = "Tuzatilmoqda…";
  try {
    await apiFetch(`/cl/admin/match/set-result?match_id=${id}&score1=${s1}&score2=${s2}&is_playoff=${po}`,
                   { method: "POST" });
    showToast(CT("cla_result_fixed"));
    CL_ADMIN.fixId = "";
    CL_ADMIN.fixInfo = null;
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "Tuzatish";
    // Play-off maxsus xatolari (talab 1) — server sabablari
    const msg = {
      match_not_found: CT("cla_match_404_low"),
      draw_not_allowed: "final durang bo'lmaydi",
      aggregate_draw_not_allowed: "ikki o'yin agregati teng bo'lib qoladi (g'olib aniq bo'lsin)",
    }[e.message] || e.message;
    showToast(CT("cl_error") + msg);
  }
}

// Kalendarni qayta qurish (ikki doira, to'g'ri tur raqamlari)
// Barcha ishtirokchilar ro'yxatini yuklaydi (admin almashtirish uchun)
async function clLoadOrphans() {
  const box = document.getElementById("cl-orphans-box");
  if (!box) return;
  try {
    const d = await apiFetch("/cl/participants/all");
    const list = d.participants || [];
    if (!list.length) {
      box.innerHTML = `<div style="font-size:12px;opacity:.6">${CT("cla_players_404")}</div>`;
      return;
    }
    const opts = list.map(o => {
      const mark = o.orphan ? "⚠️ " : "";
      const label = `${mark}G${o.group_number || "?"} · ${(o.nickname || "—").replace(/"/g, "")}`;
      return `<option value="${o.user_id}">${label}</option>`;
    }).join("");
    box.innerHTML = `<select class="modal-input cl-orphan-select" id="cl-orphan-select">
      <option value="">— almashtiriladigan ishtirokchini tanlang —</option>${opts}
    </select>`;
  } catch (_) {
    box.innerHTML = `<div style="font-size:12px;opacity:.6">${CT("cla_list_failed")}</div>`;
  }
}

// Akkount almashtirish (tanlangan participant → yangi Telegram ID)
async function clAdminReassign(btn) {
  const sel = document.getElementById("cl-orphan-select");
  const oldUid = sel ? Number(sel.value || 0) : 0;
  const newTg = Number(document.getElementById("cl-new-tg").value || 0);
  if (!oldUid) { showToast("Almashtiriladigan ishtirokchini tanlang"); return; }
  if (!newTg) { showToast("Yangi Telegram ID kiriting"); return; }
  if (!confirm(`Tanlangan ishtirokchi yangi akkountga (${newTg}) bog'lansinmi?`)) return;
  btn.disabled = true;
  const prev = btn.innerHTML;
  btn.textContent = CT("cla_connecting");
  try {
    const r = await apiFetch("/cl/participant/reassign", {
      method: "POST",
      body: JSON.stringify({ old_user_id: oldUid, new_telegram_id: newTg }),
    });
    showToast(`Bog'landi: ${r.matches_updated} o'yin yangilandi. Endi kalendarni qayta quring.`);
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = prev;
    const msg = {
      new_user_not_found: "yangi akkount botda topilmadi (avval /start bossin)",
      nothing_to_reassign: "bu id topilmadi",
      new_already_participant: "yangi akkount allaqachon ishtirokchi",
    }[e.message] || e.message;
    showToast(CT("cl_error") + msg);
  }
}

async function clAdminRebuild(btn, force = false) {
  const msg = force
    ? CT("cla_rebuild_force")
    : CT("cla_rebuild_ask");
  if (!confirm(msg)) return;
  btn.disabled = true;
  btn.textContent = "Qayta qurilmoqda…";
  try {
    const r = await apiFetch("/cl/schedule/rebuild", {
      method: "POST",
      body: JSON.stringify({ force }),
    });
    showToast(`Kalendar tayyor: ${r.matches} o'yin (${r.groups} guruh)`);
    CL.section = "home";
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("recycle", 16)} Kalendarni qayta qurish (uy+mehmon)`;
    if (e.message === "results_exist") {
      // Natija bor — majburiy (natijalarni saqlab) qurishni taklif qilamiz
      if (confirm(CT("cla_rebuild_keep"))) {
        return clAdminRebuild(btn, true);
      }
    } else {
      showToast(CT("cl_error") + clDrawErrorText(e.message));
    }
  }
}

async function clAdminDraw(btn) {
  if (!confirm(CT("cla_draw_ask"))) return;
  btn.disabled = true;                       // ikki marta bosishdan himoya (qoida 38)
  btn.textContent = CT("cla_drawing");  // vizual javob (qoida 40)
  try {
    const r = await apiFetch("/cl/draw", { method: "POST" });
    showToast(`Qur'a o'tkazildi: ${r.groups} guruh, ${r.matches} o'yin`);
    CL.section = "home";
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("dice", 16)} Qur'a o'tkazish`;
    showToast(CT("cl_error") + clDrawErrorText(e.message));
  }
}

// Turlarni boshlash (1-tur ochiladi)
async function clAdminStart(btn) {
  if (!confirm(CT("cla_start_ask"))) return;
  btn.disabled = true;
  btn.textContent = CT("cla_starting");
  try {
    const r = await apiFetch("/cl/rounds/start", { method: "POST" });
    showToast(`Boshlandi: ${r.current_matchday}-tur ochildi`);
    CL.section = "profile";
    await clLoadProfile();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("play", 16)} O'yinlarni boshlash`;
    showToast(CT("cl_error") + clDrawErrorText(e.message));
  }
}

function clDrawErrorText(reason) {
  return ({
    already_drawn: CT("cla_err_drawn"),
    no_participants: CT("cla_err_no_qual"),
    not_drawn: CT("cla_err_draw_first"),
    results_exist: CT("cla_err_has_results"),
    already_started: CT("cla_err_started"),
    matchday_locked: CT("cl_round_locked").toLowerCase(),
  })[reason] || reason;
}
