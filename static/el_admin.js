// ============================================================
//  el_admin.js — Yevropa ligasi admin paneli (YeL Profil tabi ichida)
//
//  worldcup_admin.js naqshi (qoida 10 — parallel joylar sinxron):
//    - Bosh admin (config ADMIN_TELEGRAM_IDS) → panel ko'rinadi
//    - Boshqa hamma → panel yashirin
//  Rol serverdan aniqlanadi: GET /admin/whoami (is_super). Kodda ID yo'q.
//
//  Amallar: Qur'a o'tkazish → POST /el/draw (36 ishtirokchi → Swiss, 8 tur)
//  Global: apiFetch, showToast, escHtml, EL, elLoadThenRender
// ============================================================

const EL_ADMIN = { isSuper: false, isCl: false, loaded: false, fixId: "", fixInfo: null,
                   fixIsPlayoff: false };  // 2026-07-22: play-off checkbox + YeL admin roli

// Nav'da Admin tab ko'rsatish uchun rolni oldindan tekshiradi (bir marta).
// 2026-07-22 (talab 2): bosh admin YOKI tayinlangan YeL admin panelni ko'radi;
// admin tayinlash oynasi esa faqat bosh adminda (quyida isSuper bilan).
async function elCheckAdmin() {
  if (EL_ADMIN.loaded) return EL_ADMIN.isSuper || EL_ADMIN.isCl;
  try {
    const who = await apiFetch("/admin/whoami");
    EL_ADMIN.isSuper = !!who.is_super;
    EL_ADMIN.isCl = !!who.is_cl_admin;
  } catch (_) {
    EL_ADMIN.isSuper = false;
    EL_ADMIN.isCl = false;
  }
  EL_ADMIN.loaded = true;
  return EL_ADMIN.isSuper || EL_ADMIN.isCl;
}

// Admin sahifasini chizadi (5-tab). Bosh admin yoki tayinlangan YeL admin.
async function elRenderAdminPage() {
  const canView = await elCheckAdmin();
  const page = document.getElementById("el-admin-page");
  if (!page) return;
  if (!canView) {
    page.innerHTML = `<div class="card">Bu sahifa faqat administrator uchun.</div>`;
    return;
  }
  elLoadAdminPanel();
}

async function elLoadAdminPanel() {
  const panel = document.getElementById("el-admin-page") || document.getElementById("el-admin-panel");
  if (!panel) return;

  await elCheckAdmin();
  if (!(EL_ADMIN.isSuper || EL_ADMIN.isCl)) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }

  const drawn = !!(EL.groups && EL.groups.drawn);
  const st = EL.state || {};
  const started = !!st.started;
  // 2026-09-22: eskirgan holat (o'tgan mavsumdan qolgan) — backend stale deydi.
  // Bunday holatda tugma OCHIQ bo'ladi, bosilsa 1-turdan qayta boshlanadi.
  const stale = !!st.stale;
  panel.classList.remove("hidden");
  // 2026-07-22: qur'a / kalendar / akkount almashtirish / o'yin+play-off boshlash —
  // FAQAT bosh admin. Tayinlangan YeL admin faqat natija tuzatishni ko'radi.
  panel.innerHTML = `
    <div class="card" style="border-color:rgba(245,197,66,.45)">
      <b>${ICON.get("shield", 16)} YeL admin paneli</b>
      ${EL_ADMIN.isSuper ? `
      <div style="font-size:12.5px;opacity:.75;margin:4px 0 10px">
        ${drawn
          ? ET("ela_draw_done")
          : ET("ela_draw_hint")}
      </div>
      <button class="btn btn--primary" id="el-admin-draw" ${drawn ? "disabled" : ""}>
        ${ICON.get("dice", 16)} Qur'a o'tkazish
      </button>
      ${drawn ? `
      <div style="font-size:12.5px;opacity:.75;margin:14px 0 6px">
        Ishtirokchini almashtirish: istalgan ishtirokchini (⚠️ = o'chirilgan
        akkount) yangi Telegram ID'ga bog'laydi. Qur'a va natijalar saqlanadi.
      </div>
      <div id="el-orphans-box" style="margin-bottom:6px"></div>
      <input class="modal-input" id="el-new-tg" type="number" inputmode="numeric"
             placeholder="Yangi Telegram ID" style="margin-bottom:8px">
      <button class="btn" id="el-admin-reassign">👤 Akkountni almashtirish</button>

      <div style="font-size:12.5px;opacity:.75;margin:12px 0 8px">
        ${stale
          ? `<b style="color:#ff6b6b">⚠️ Tur holati eskirgan (o'tgan mavsumdan qolgan): ${st.current_matchday}-tur ko'rsatilmoqda, lekin hech bir o'yin o'ynalmagan. Shu sababli barcha turlar YOPIQ. "O'yinlarni boshlash" ni bosing — 1-tur ochiladi.</b>`
          : (started
            ? ET("ela_started_hint").replace("{cur}", st.current_matchday).replace("{total}", st.total_matchdays)
            : ET("ela_start_hint"))}
      </div>
      <button class="btn btn--primary" id="el-admin-start" ${started && !stale ? "disabled" : ""}>
        ${ICON.get("play", 16)} O'yinlarni boshlash
      </button>` : ""}

      <div class="admin-hint" style="margin-top:14px">
        <b>1-bosqich — Qayta tasnif:</b> liga bosqichi (8 tur) tugagach 9-24 o'rin
        egalari 8 juftlikda uy+mehmon o'ynaydi. Setka hali ochilmaydi.
      </div>
      <button class="btn btn--primary" id="el-admin-po-start">${ET("ela_playoff_start")}</button>

      <div class="admin-hint" style="margin-top:14px">
        <b>2-bosqich — Setka:</b> qayta tasnif tugagach bosiladi. 8 g'olib top-8
        bilan juftlanadi (1/8 final). Har juftlik uy+mehmon, final — 1 o'yin.
      </div>
      <button class="btn" id="el-admin-po-bracket">🏟️ Setkani ochish (1/8 final)</button>

      <div class="admin-hint" style="margin-top:14px">
        <b>Mavsumni yakunlash:</b> final g'olibi YeL kubogini oladi — kubok
        profil sahifasida va useri oldida yulduzcha (★) bo'lib doimiy qoladi.
        So'ng YeL ma'lumoti tozalanadi (keyingi mavsum ishtirokchilari
        ligalardagi 8–15-o'rinlar orqali tanlanadi). Qaytarib bo'lmaydi!
      </div>
      <button class="btn" id="el-admin-finalize"
              style="border-color:rgba(245,197,66,.55);color:#f5c542">
        🏆 YeL mavsumini yakunlash
      </button>
      ` : ""}

      ${drawn ? elAdminFixForm() : ""}

      ${EL_ADMIN.isSuper ? `
      <div class="section-label" style="margin-top:16px">ADMIN TAYINLASH</div>
      <div class="admin-fix-form">
        <input id="el-admin-new-id" class="modal-input" type="number" min="1"
               placeholder="Telegram ID" style="margin-bottom:8px" />
        <button class="btn btn--primary" id="el-btn-admin-add">Admin qo'shish</button>
        <div id="el-admin-roles-list" class="admin-players-list" style="margin-top:8px"></div>
      </div>` : ""}
    </div>`;

  if (typeof applyIcons === "function") applyIcons(panel);

  const btn = document.getElementById("el-admin-draw");
  if (btn && !drawn) btn.addEventListener("click", () => void elAdminDraw(btn));

  const rasgn = document.getElementById("el-admin-reassign");
  if (rasgn) rasgn.addEventListener("click", () => void elAdminReassign(rasgn));

  if (document.getElementById("el-orphans-box")) void elLoadOrphans();

  const sbtn = document.getElementById("el-admin-start");
  if (sbtn && !started) sbtn.addEventListener("click", () => void elAdminStart(sbtn));

  // 2026-07-20: play-off boshlash (el_playoff.js) — xatolar toast bilan tushuntiriladi
  const pobtn = document.getElementById("el-admin-po-start");
  if (pobtn && typeof elpoAdminStart === "function")
    pobtn.addEventListener("click", () => void elpoAdminStart(pobtn));

  // 2026-08: 2-bosqich — asosiy setkani ochish (qayta tasnif tugagach)
  const brbtn = document.getElementById("el-admin-po-bracket");
  if (brbtn && typeof elpoAdminStartBracket === "function")
    brbtn.addEventListener("click", () => void elpoAdminStartBracket(brbtn));

  // Match ID orqali tuzatish (liga naqshi)
  const fixId = document.getElementById("el-fix-match-id");
  if (fixId) fixId.addEventListener("input", (e) => elFixIdChanged(e.target.value));

  // 2026-07-22 (talab 1): "Play-off o'yini" checkbox — o'zgarsa preview qayta so'raladi
  const fixPo = document.getElementById("el-fix-is-playoff");
  if (fixPo) fixPo.addEventListener("change", (e) => {
    EL_ADMIN.fixIsPlayoff = e.target.checked;
    if (EL_ADMIN.fixId) elFixIdChanged(EL_ADMIN.fixId);  // yangi jadvaldan info olib preview yangilanadi
    else elRerenderPanel();
  });
  const fixSubmit = document.getElementById("el-fix-submit");
  if (fixSubmit) fixSubmit.addEventListener("click", () => void elAdminFixSubmit(fixSubmit));

  // Natijani bekor qilish (2026-07-16) — o'yin natija kiritilmagan holatga qaytadi
  const fixCancel = document.getElementById("el-fix-cancel-result");
  if (fixCancel) fixCancel.addEventListener("click", () => void elAdminCancelResult(fixCancel));

  // 2026-07-22 (talab 2): admin tayinlash — faqat bosh admin (api.js DRY yordamchisi)
  if (EL_ADMIN.isSuper) {
    const addBtn = document.getElementById("el-btn-admin-add");
    if (addBtn) addBtn.addEventListener("click",
      () => void scopeAdminRoleAdd("el", "el-admin-new-id", "el-admin-roles-list"));
    if (document.getElementById("el-admin-roles-list"))
      void scopeAdminRolesLoad("el", "el-admin-roles-list");

    // 2026-07-23: YeL mavsumini yakunlash (kubok saqlanadi + ma'lumot tozalanadi)
    const finBtn = document.getElementById("el-admin-finalize");
    if (finBtn) finBtn.addEventListener("click", () => void elAdminFinalizeSeason(finBtn));
  }
}

// 2026-07-23: YeL mavsumini yakunlash — final g'olibi kubokni oladi.
async function elAdminFinalizeSeason(btn) {
  if (!confirm("YeL mavsumi yakunlansinmi?\n\nFinal g'olibi YeL kubogini oladi "
             + "(profil va yulduzchada doimiy qoladi), so'ng YeL ma'lumoti tozalanadi.\n\n"
             + "Bu amalni qaytarib bo'lmaydi!")) return;
  btn.disabled = true;
  const prev = btn.textContent;
  btn.textContent = "Yakunlanmoqda…";
  try {
    const r = await apiFetch("/season/el/finalize", { method: "POST" });
    const champ = r.champion || {};
    const who = champ.username ? "@" + champ.username : (champ.nickname || "chempion");
    showToast(`🏆 Mavsum yakunlandi — kubok: ${who}`);
    await elLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.textContent = prev;
    const msg = {
      already_finalized: "mavsum allaqachon yakunlangan",
      no_champion: "chempion aniqlanmagan — final o'ynalmagan",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

// 2026-07-16: Admin YeL natijasini BEKOR QILADI (pending, — : —).
// Liga/WC/Divizion'dagi bekor qilish bilan bir xil oqim.
async function elAdminCancelResult(btn) {
  const t = APP.t || {};
  const id = parseInt(EL_ADMIN.fixId, 10);
  if (!id) { showToast("Match ID kiriting"); return; }
  if (!confirm(t.admin_reset_confirm || ET("ela_cancel_ask"))) return;
  btn.disabled = true;
  const po = EL_ADMIN.fixIsPlayoff ? 1 : 0;
  try {
    await apiFetch(`/el/admin/match/cancel?match_id=${id}&is_playoff=${po}`, { method: "POST" });
    showToast(t.admin_reset_done || ET("ela_cancelled"));
    EL_ADMIN.fixId = "";
    EL_ADMIN.fixInfo = null;
    await elLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    const msg = { match_not_found: ET("ela_match_404_low") }[e.message] || e.message;
    showToast(ET("el_error") + msg);
  }
}

// --- YeL "Match ID orqali tuzatish" (liga divAdminFixForm naqshi, ranglar YeL) ---
function elAdminFixForm() {
  const info = EL_ADMIN.fixInfo;
  let preview = "";
  if (info === "notfound") {
    preview = `<div style="font-size:12px;color:#ff6b6b;margin:6px 0">${ET("el_match_404")}</div>`;
  } else if (info) {
    const p1 = info.player1_username ? "@" + info.player1_username : (info.player1_name || "—");
    const p2 = info.player2_username ? "@" + info.player2_username : (info.player2_name || "—");
    const cur = (info.score1 != null) ? `${info.score1} : ${info.score2}` : "— : —";
    const badge = (club) => (typeof elClubBadge === "function") ? elClubBadge(club, 30) : "";
    // 2026-07-22 (talab 1): play-off o'yinida bosqich+leg, guruhda tur ko'rsatiladi
    const meta = info.is_playoff
      ? `#${info.id} · ${escHtml(info.round_label || info.round || "Play-off")}${info.round !== "final" ? " · " + info.leg + "-o'yin" : ""}`
      : `#${info.id} · ${info.matchday}-tur`;
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
    <input id="el-fix-match-id" class="modal-input" type="number" min="1"
           placeholder="Match ID" value="${EL_ADMIN.fixId || ""}" style="margin-bottom:6px" />
    <label class="admin-fix-playoff-check" style="display:flex;align-items:center;gap:8px;margin:2px 2px 8px;font-size:13.5px">
      <input id="el-fix-is-playoff" type="checkbox" ${EL_ADMIN.fixIsPlayoff ? "checked" : ""} />
      <span>${escHtml((APP.t && APP.t.admin_fix_is_playoff) || "Play-off o'yini")}</span>
    </label>
    ${preview}
    <div class="score-input-row" style="display:flex;align-items:center;justify-content:center;gap:10px;margin:6px 0">
      <input id="el-fix-score1" class="score-input" type="number" min="0" max="99"
             value="${info && info !== "notfound" && info.score1 != null ? info.score1 : 0}" />
      <span class="score-separator">:</span>
      <input id="el-fix-score2" class="score-input" type="number" min="0" max="99"
             value="${info && info !== "notfound" && info.score2 != null ? info.score2 : 0}" />
    </div>
    <button class="btn btn--primary" id="el-fix-submit" ${disabled ? "disabled" : ""}
            style="opacity:${disabled ? ".45" : "1"}">Tuzatish</button>
    <button class="btn btn--ghost" id="el-fix-cancel-result" ${disabled ? "disabled" : ""}
            style="margin-top:8px;color:var(--red-neon);border-color:rgba(255,69,96,.3);opacity:${disabled ? ".45" : "1"}">
      ${escHtml((APP.t && APP.t.admin_reset_btn) || ET("ela_cancel_result"))}
    </button>
    ${typeof chatReportBoxHtml === "function"
        ? chatReportBoxHtml("el", { playoffMode: "el_po" })
        : ""}`;
}

let _elFixTimer = null;
function elFixIdChanged(raw) {
  clearTimeout(_elFixTimer);
  EL_ADMIN.fixId = raw;
  const id = parseInt(raw, 10);
  if (!id || id <= 0) { EL_ADMIN.fixInfo = null; elRerenderPanel(); return; }
  _elFixTimer = setTimeout(async () => {
    const po = EL_ADMIN.fixIsPlayoff ? 1 : 0;
    try {
      EL_ADMIN.fixInfo = await apiFetch(`/el/admin/match/${id}/info?is_playoff=${po}`);
      // Serverdan HAQIQIY is_playoff kelsa (fallback ishlagan bo'lsa) — checkbox'ni to'g'rilaymiz
      if (EL_ADMIN.fixInfo && typeof EL_ADMIN.fixInfo.is_playoff !== "undefined") {
        EL_ADMIN.fixIsPlayoff = !!EL_ADMIN.fixInfo.is_playoff;
      }
    } catch (_) {
      EL_ADMIN.fixInfo = "notfound";
    }
    elRerenderPanel();
  }, 350);
}

// Panelni qayta chizadi va ID inputga fokusni tiklaydi (qoida #40)
function elRerenderPanel() {
  void elLoadAdminPanel().then(() => {
    const el = document.getElementById("el-fix-match-id");
    if (el) { el.focus(); const v = el.value; el.value = ""; el.value = v; }
  });
}

async function elAdminFixSubmit(btn) {
  const id = parseInt(EL_ADMIN.fixId, 10);
  const s1 = Number(document.getElementById("el-fix-score1").value || 0);
  const s2 = Number(document.getElementById("el-fix-score2").value || 0);
  const po = EL_ADMIN.fixIsPlayoff ? 1 : 0;
  if (!id) { showToast("Match ID kiriting"); return; }
  if (!confirm(`#${id} natijasi ${s1}:${s2} qilib tuzatilsinmi?`)) return;
  btn.disabled = true;
  btn.textContent = "Tuzatilmoqda…";
  try {
    await apiFetch(`/el/admin/match/set-result?match_id=${id}&score1=${s1}&score2=${s2}&is_playoff=${po}`,
                   { method: "POST" });
    showToast(ET("ela_result_fixed"));
    EL_ADMIN.fixId = "";
    EL_ADMIN.fixInfo = null;
    await elLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "Tuzatish";
    // Play-off maxsus xatolari (talab 1) — server sabablari
    const msg = {
      match_not_found: ET("ela_match_404_low"),
      draw_not_allowed: "final durang bo'lmaydi",
      aggregate_draw_not_allowed: "ikki o'yin agregati teng bo'lib qoladi (g'olib aniq bo'lsin)",
    }[e.message] || e.message;
    showToast(ET("el_error") + msg);
  }
}

// Kalendarni qayta qurish (ikki doira, to'g'ri tur raqamlari)
// Barcha ishtirokchilar ro'yxatini yuklaydi (admin almashtirish uchun)
async function elLoadOrphans() {
  const box = document.getElementById("el-orphans-box");
  if (!box) return;
  try {
    const d = await apiFetch("/el/participants/all");
    const list = d.participants || [];
    if (!list.length) {
      box.innerHTML = `<div style="font-size:12px;opacity:.6">${ET("ela_players_404")}</div>`;
      return;
    }
    const opts = list.map(o => {
      const mark = o.orphan ? "⚠️ " : "";
      const label = `${mark}G${o.group_number || "?"} · ${(o.nickname || "—").replace(/"/g, "")}`;
      return `<option value="${o.user_id}">${label}</option>`;
    }).join("");
    box.innerHTML = `<select class="modal-input el-orphan-select" id="el-orphan-select">
      <option value="">— almashtiriladigan ishtirokchini tanlang —</option>${opts}
    </select>`;
  } catch (_) {
    box.innerHTML = `<div style="font-size:12px;opacity:.6">${ET("ela_list_failed")}</div>`;
  }
}

// Akkount almashtirish (tanlangan participant → yangi Telegram ID)
async function elAdminReassign(btn) {
  const sel = document.getElementById("el-orphan-select");
  const oldUid = sel ? Number(sel.value || 0) : 0;
  const newTg = Number(document.getElementById("el-new-tg").value || 0);
  if (!oldUid) { showToast("Almashtiriladigan ishtirokchini tanlang"); return; }
  if (!newTg) { showToast("Yangi Telegram ID kiriting"); return; }
  if (!confirm(`Tanlangan ishtirokchi yangi akkountga (${newTg}) bog'lansinmi?`)) return;
  btn.disabled = true;
  const prev = btn.innerHTML;
  btn.textContent = ET("ela_connecting");
  try {
    const r = await apiFetch("/el/participant/reassign", {
      method: "POST",
      body: JSON.stringify({ old_user_id: oldUid, new_telegram_id: newTg }),
    });
    showToast(`Bog'landi: ${r.matches_updated} o'yin yangilandi. Endi kalendarni qayta quring.`);
    await elLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = prev;
    const msg = {
      new_user_not_found: "yangi akkount botda topilmadi (avval /start bossin)",
      nothing_to_reassign: "bu id topilmadi",
      new_already_participant: "yangi akkount allaqachon ishtirokchi",
    }[e.message] || e.message;
    showToast(ET("el_error") + msg);
  }
}

async function elAdminDraw(btn) {
  if (!confirm(ET("ela_draw_ask"))) return;
  btn.disabled = true;                       // ikki marta bosishdan himoya (qoida 38)
  btn.textContent = ET("ela_drawing");  // vizual javob (qoida 40)
  try {
    const r = await apiFetch("/el/draw", { method: "POST" });
    showToast(`Qur'a o'tkazildi: ${r.participants} ishtirokchi, ${r.matches} o'yin`);
    EL.section = "home";
    await elLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("dice", 16)} Qur'a o'tkazish`;
    showToast(ET("el_error") + elDrawErrorText(e.message));
  }
}

// Turlarni boshlash (1-tur ochiladi)
async function elAdminStart(btn) {
  if (!confirm(ET("ela_start_ask"))) return;
  btn.disabled = true;
  btn.textContent = ET("ela_starting");
  try {
    const r = await apiFetch("/el/rounds/start", { method: "POST" });
    showToast(`Boshlandi: ${r.current_matchday}-tur ochildi`);
    EL.section = "profile";
    await elLoadProfile();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("play", 16)} O'yinlarni boshlash`;
    showToast(ET("el_error") + elDrawErrorText(e.message));
  }
}

function elDrawErrorText(reason) {
  return ({
    already_drawn: ET("ela_err_drawn"),
    no_participants: ET("ela_err_no_qual"),
    not_drawn: ET("ela_err_draw_first"),
    results_exist: ET("ela_err_has_results"),
    already_started: ET("ela_err_started"),
    matchday_locked: ET("el_round_locked").toLowerCase(),
  })[reason] || reason;
}
