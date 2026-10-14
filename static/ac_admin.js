// ============================================================
//  ac_admin.js — Osiyo Chempionlar ligasi admin paneli (OChL Profil tabi ichida)
//
//  worldcup_admin.js naqshi (qoida 10 — parallel joylar sinxron):
//    - Bosh admin (config ADMIN_TELEGRAM_IDS) → panel ko'rinadi
//    - Boshqa hamma → panel yashirin
//  Rol serverdan aniqlanadi: GET /admin/whoami (is_super). Kodda ID yo'q.
//
//  Amallar: Qur'a o'tkazish → POST /ac/draw (32 ishtirokchi → Swiss, 8 tur)
//  Global: apiFetch, showToast, escHtml, AC, acLoadThenRender
// ============================================================

const AC_ADMIN = { isSuper: false, isCl: false, loaded: false, fixId: "", fixInfo: null,
                   fixIsPlayoff: false };  // 2026-07-22: play-off checkbox + OChL admin roli

// Nav'da Admin tab ko'rsatish uchun rolni oldindan tekshiradi (bir marta).
// 2026-07-22 (talab 2): bosh admin YOKI tayinlangan OChL admin panelni ko'radi;
// admin tayinlash oynasi esa faqat bosh adminda (quyida isSuper bilan).
async function acCheckAdmin() {
  if (AC_ADMIN.loaded) return AC_ADMIN.isSuper || AC_ADMIN.isCl;
  try {
    const who = await apiFetch("/admin/whoami");
    AC_ADMIN.isSuper = !!who.is_super;
    AC_ADMIN.isCl = !!who.is_cl_admin;
  } catch (_) {
    AC_ADMIN.isSuper = false;
    AC_ADMIN.isCl = false;
  }
  AC_ADMIN.loaded = true;
  return AC_ADMIN.isSuper || AC_ADMIN.isCl;
}

// Admin sahifasini chizadi (5-tab). Bosh admin yoki tayinlangan OChL admin.
async function acRenderAdminPage() {
  const canView = await acCheckAdmin();
  const page = document.getElementById("ac-admin-page");
  if (!page) return;
  if (!canView) {
    page.innerHTML = `<div class="card">Bu sahifa faqat administrator uchun.</div>`;
    return;
  }
  acLoadAdminPanel();
}

async function acLoadAdminPanel() {
  const panel = document.getElementById("ac-admin-page") || document.getElementById("ac-admin-panel");
  if (!panel) return;

  await acCheckAdmin();
  if (!(AC_ADMIN.isSuper || AC_ADMIN.isCl)) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }

  const drawn = !!(AC.groups && AC.groups.drawn);
  const st = AC.state || {};
  const started = !!st.started;
  // 2026-09-22: eskirgan holat (o'tgan mavsumdan qolgan) — backend stale deydi.
  // Bunday holatda tugma OCHIQ bo'ladi, bosilsa 1-turdan qayta boshlanadi.
  const stale = !!st.stale;
  panel.classList.remove("hidden");
  // 2026-07-22: qur'a / kalendar / akkount almashtirish / o'yin+play-off boshlash —
  // FAQAT bosh admin. Tayinlangan OChL admin faqat natija tuzatishni ko'radi.
  panel.innerHTML = `
    <div class="card" style="border-color:rgba(245,197,66,.45)">
      <b>${ICON.get("shield", 16)} OChL admin paneli</b>
      ${AC_ADMIN.isSuper ? `
      <div style="font-size:12.5px;opacity:.75;margin:4px 0 10px">
        ${drawn
          ? ACT("aca_draw_done")
          : ACT("aca_draw_hint")}
      </div>
      <button class="btn btn--primary" id="ac-admin-draw" ${drawn ? "disabled" : ""}>
        ${ICON.get("dice", 16)} Qur'a o'tkazish
      </button>
      ${drawn ? `
      <div style="font-size:12.5px;opacity:.75;margin:14px 0 6px">
        Ishtirokchini almashtirish: istalgan ishtirokchini (⚠️ = o'chirilgan
        akkount) yangi Telegram ID'ga bog'laydi. Qur'a va natijalar saqlanadi.
      </div>
      <div id="ac-orphans-box" style="margin-bottom:6px"></div>
      <input class="modal-input" id="ac-new-tg" type="number" inputmode="numeric"
             placeholder="Yangi Telegram ID" style="margin-bottom:8px">
      <button class="btn" id="ac-admin-reassign">👤 Akkountni almashtirish</button>

      <div style="font-size:12.5px;opacity:.75;margin:12px 0 8px">
        ${stale
          ? `<b style="color:#ff6b6b">⚠️ Tur holati eskirgan (o'tgan mavsumdan qolgan): ${st.current_matchday}-tur ko'rsatilmoqda, lekin hech bir o'yin o'ynalmagan. Shu sababli barcha turlar YOPIQ. "O'yinlarni boshlash" ni bosing — 1-tur ochiladi.</b>`
          : (started
            ? ACT("aca_started_hint").replace("{cur}", st.current_matchday).replace("{total}", st.total_matchdays)
            : ACT("aca_start_hint"))}
      </div>
      <button class="btn btn--primary" id="ac-admin-start" ${started && !stale ? "disabled" : ""}>
        ${ICON.get("play", 16)} O'yinlarni boshlash
      </button>` : ""}

      <div class="admin-hint" style="margin-top:14px">
        <b>1-bosqich — Qayta tasnif:</b> liga bosqichi (8 tur) tugagach 9-24 o'rin
        egalari 8 juftlikda uy+mehmon o'ynaydi. Setka hali ochilmaydi.
      </div>
      <button class="btn btn--primary" id="ac-admin-po-start">${ACT("aca_playoff_start")}</button>

      <div class="admin-hint" style="margin-top:14px">
        <b>2-bosqich — Setka:</b> qayta tasnif tugagach bosiladi. 8 g'olib top-8
        bilan juftlanadi (1/8 final). Har juftlik uy+mehmon, final — 1 o'yin.
      </div>
      <button class="btn" id="ac-admin-po-bracket">🏟️ Setkani ochish (1/8 final)</button>

      <div class="admin-hint" style="margin-top:14px">
        <b>Mavsumni yakunlash:</b> final g'olibi OChL kubogini oladi — kubok
        profil sahifasida va useri oldida yulduzcha (★) bo'lib doimiy qoladi.
        So'ng OChL ma'lumoti tozalanadi (keyingi mavsum ishtirokchilari
        4 ta Osiyo ligasining top-8 o'rinlari orqali tanlanadi). Qaytarib bo'lmaydi!
      </div>
      <button class="btn" id="ac-admin-finalize"
              style="border-color:rgba(245,197,66,.55);color:#f5c542">
        🏆 OChL mavsumini yakunlash
      </button>
      ` : ""}

      ${drawn ? acAdminFixForm() : ""}

      ${AC_ADMIN.isSuper ? `
      <div class="section-label" style="margin-top:16px">ADMIN TAYINLASH</div>
      <div class="admin-fix-form">
        <input id="ac-admin-new-id" class="modal-input" type="number" min="1"
               placeholder="Telegram ID" style="margin-bottom:8px" />
        <button class="btn btn--primary" id="ac-btn-admin-add">Admin qo'shish</button>
        <div id="ac-admin-roles-list" class="admin-players-list" style="margin-top:8px"></div>
      </div>` : ""}
    </div>`;

  if (typeof applyIcons === "function") applyIcons(panel);

  const btn = document.getElementById("ac-admin-draw");
  if (btn && !drawn) btn.addEventListener("click", () => void acAdminDraw(btn));

  const rasgn = document.getElementById("ac-admin-reassign");
  if (rasgn) rasgn.addEventListener("click", () => void acAdminReassign(rasgn));

  if (document.getElementById("ac-orphans-box")) void acLoadOrphans();

  const sbtn = document.getElementById("ac-admin-start");
  if (sbtn && !started) sbtn.addEventListener("click", () => void acAdminStart(sbtn));

  // 2026-07-20: play-off boshlash (ac_playoff.js) — xatolar toast bilan tushuntiriladi
  const pobtn = document.getElementById("ac-admin-po-start");
  if (pobtn && typeof acpoAdminStart === "function")
    pobtn.addEventListener("click", () => void acpoAdminStart(pobtn));

  // 2026-08: 2-bosqich — asosiy setkani ochish (qayta tasnif tugagach)
  const brbtn = document.getElementById("ac-admin-po-bracket");
  if (brbtn && typeof acpoAdminStartBracket === "function")
    brbtn.addEventListener("click", () => void acpoAdminStartBracket(brbtn));

  // Match ID orqali tuzatish (liga naqshi)
  const fixId = document.getElementById("ac-fix-match-id");
  if (fixId) fixId.addEventListener("input", (e) => acFixIdChanged(e.target.value));

  // 2026-07-22 (talab 1): "Play-off o'yini" checkbox — o'zgarsa preview qayta so'raladi
  const fixPo = document.getElementById("ac-fix-is-playoff");
  if (fixPo) fixPo.addEventListener("change", (e) => {
    AC_ADMIN.fixIsPlayoff = e.target.checked;
    if (AC_ADMIN.fixId) acFixIdChanged(AC_ADMIN.fixId);  // yangi jadvaldan info olib preview yangilanadi
    else acRerenderPanel();
  });
  const fixSubmit = document.getElementById("ac-fix-submit");
  if (fixSubmit) fixSubmit.addEventListener("click", () => void acAdminFixSubmit(fixSubmit));

  // Natijani bekor qilish (2026-07-16) — o'yin natija kiritilmagan holatga qaytadi
  const fixCancel = document.getElementById("ac-fix-cancel-result");
  if (fixCancel) fixCancel.addEventListener("click", () => void acAdminCancelResult(fixCancel));

  // 2026-07-22 (talab 2): admin tayinlash — faqat bosh admin (api.js DRY yordamchisi)
  if (AC_ADMIN.isSuper) {
    const addBtn = document.getElementById("ac-btn-admin-add");
    if (addBtn) addBtn.addEventListener("click",
      () => void scopeAdminRoleAdd("ac", "ac-admin-new-id", "ac-admin-roles-list"));
    if (document.getElementById("ac-admin-roles-list"))
      void scopeAdminRolesLoad("ac", "ac-admin-roles-list");

    // 2026-07-23: OChL mavsumini yakunlash (kubok saqlanadi + ma'lumot tozalanadi)
    const finBtn = document.getElementById("ac-admin-finalize");
    if (finBtn) finBtn.addEventListener("click", () => void acAdminFinalizeSeason(finBtn));
  }
}

// 2026-07-23: OChL mavsumini yakunlash — final g'olibi kubokni oladi.
async function acAdminFinalizeSeason(btn) {
  if (!confirm("OChL mavsumi yakunlansinmi?\n\nFinal g'olibi OChL kubogini oladi "
             + "(profil va yulduzchada doimiy qoladi), so'ng OChL ma'lumoti tozalanadi.\n\n"
             + "Bu amalni qaytarib bo'lmaydi!")) return;
  btn.disabled = true;
  const prev = btn.textContent;
  btn.textContent = "Yakunlanmoqda…";
  try {
    const r = await apiFetch("/season/ac/finalize", { method: "POST" });
    const champ = r.champion || {};
    const who = champ.username ? "@" + champ.username : (champ.nickname || "chempion");
    showToast(`🏆 Mavsum yakunlandi — kubok: ${who}`);
    await acLoadThenRender();
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

// 2026-07-16: Admin OChL natijasini BEKOR QILADI (pending, — : —).
// Liga/WC/Divizion'dagi bekor qilish bilan bir xil oqim.
async function acAdminCancelResult(btn) {
  const t = APP.t || {};
  const id = parseInt(AC_ADMIN.fixId, 10);
  if (!id) { showToast("Match ID kiriting"); return; }
  if (!confirm(t.admin_reset_confirm || ACT("aca_cancel_ask"))) return;
  btn.disabled = true;
  const po = AC_ADMIN.fixIsPlayoff ? 1 : 0;
  try {
    await apiFetch(`/ac/admin/match/cancel?match_id=${id}&is_playoff=${po}`, { method: "POST" });
    showToast(t.admin_reset_done || ACT("aca_cancelled"));
    AC_ADMIN.fixId = "";
    AC_ADMIN.fixInfo = null;
    await acLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    const msg = { match_not_found: ACT("aca_match_404_low") }[e.message] || e.message;
    showToast(ACT("ac_error") + msg);
  }
}

// --- OChL "Match ID orqali tuzatish" (liga divAdminFixForm naqshi, ranglar OChL) ---
function acAdminFixForm() {
  const info = AC_ADMIN.fixInfo;
  let preview = "";
  if (info === "notfound") {
    preview = `<div style="font-size:12px;color:#ff6b6b;margin:6px 0">${ACT("ac_match_404")}</div>`;
  } else if (info) {
    const p1 = info.player1_username ? "@" + info.player1_username : (info.player1_name || "—");
    const p2 = info.player2_username ? "@" + info.player2_username : (info.player2_name || "—");
    const cur = (info.score1 != null) ? `${info.score1} : ${info.score2}` : "— : —";
    const badge = (club) => (typeof acClubBadge === "function") ? acClubBadge(club, 30) : "";
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
    <input id="ac-fix-match-id" class="modal-input" type="number" min="1"
           placeholder="Match ID" value="${AC_ADMIN.fixId || ""}" style="margin-bottom:6px" />
    <label class="admin-fix-playoff-check" style="display:flex;align-items:center;gap:8px;margin:2px 2px 8px;font-size:13.5px">
      <input id="ac-fix-is-playoff" type="checkbox" ${AC_ADMIN.fixIsPlayoff ? "checked" : ""} />
      <span>${escHtml((APP.t && APP.t.admin_fix_is_playoff) || "Play-off o'yini")}</span>
    </label>
    ${preview}
    <div class="score-input-row" style="display:flex;align-items:center;justify-content:center;gap:10px;margin:6px 0">
      <input id="ac-fix-score1" class="score-input" type="number" min="0" max="99"
             value="${info && info !== "notfound" && info.score1 != null ? info.score1 : 0}" />
      <span class="score-separator">:</span>
      <input id="ac-fix-score2" class="score-input" type="number" min="0" max="99"
             value="${info && info !== "notfound" && info.score2 != null ? info.score2 : 0}" />
    </div>
    <button class="btn btn--primary" id="ac-fix-submit" ${disabled ? "disabled" : ""}
            style="opacity:${disabled ? ".45" : "1"}">Tuzatish</button>
    <button class="btn btn--ghost" id="ac-fix-cancel-result" ${disabled ? "disabled" : ""}
            style="margin-top:8px;color:var(--red-neon);border-color:rgba(255,69,96,.3);opacity:${disabled ? ".45" : "1"}">
      ${escHtml((APP.t && APP.t.admin_reset_btn) || ACT("aca_cancel_result"))}
    </button>
    ${typeof chatReportBoxHtml === "function"
        ? chatReportBoxHtml("ac", { playoffMode: "ac_po" })
        : ""}`;
}

let _acFixTimer = null;
function acFixIdChanged(raw) {
  clearTimeout(_acFixTimer);
  AC_ADMIN.fixId = raw;
  const id = parseInt(raw, 10);
  if (!id || id <= 0) { AC_ADMIN.fixInfo = null; acRerenderPanel(); return; }
  _acFixTimer = setTimeout(async () => {
    const po = AC_ADMIN.fixIsPlayoff ? 1 : 0;
    try {
      AC_ADMIN.fixInfo = await apiFetch(`/ac/admin/match/${id}/info?is_playoff=${po}`);
      // Serverdan HAQIQIY is_playoff kelsa (fallback ishlagan bo'lsa) — checkbox'ni to'g'rilaymiz
      if (AC_ADMIN.fixInfo && typeof AC_ADMIN.fixInfo.is_playoff !== "undefined") {
        AC_ADMIN.fixIsPlayoff = !!AC_ADMIN.fixInfo.is_playoff;
      }
    } catch (_) {
      AC_ADMIN.fixInfo = "notfound";
    }
    acRerenderPanel();
  }, 350);
}

// Panelni qayta chizadi va ID inputga fokusni tiklaydi (qoida #40)
function acRerenderPanel() {
  void acLoadAdminPanel().then(() => {
    const ac = document.getElementById("ac-fix-match-id");
    if (ac) { ac.focus(); const v = ac.value; ac.value = ""; ac.value = v; }
  });
}

async function acAdminFixSubmit(btn) {
  const id = parseInt(AC_ADMIN.fixId, 10);
  const s1 = Number(document.getElementById("ac-fix-score1").value || 0);
  const s2 = Number(document.getElementById("ac-fix-score2").value || 0);
  const po = AC_ADMIN.fixIsPlayoff ? 1 : 0;
  if (!id) { showToast("Match ID kiriting"); return; }
  if (!confirm(`#${id} natijasi ${s1}:${s2} qilib tuzatilsinmi?`)) return;
  btn.disabled = true;
  btn.textContent = "Tuzatilmoqda…";
  try {
    await apiFetch(`/ac/admin/match/set-result?match_id=${id}&score1=${s1}&score2=${s2}&is_playoff=${po}`,
                   { method: "POST" });
    showToast(ACT("aca_result_fixed"));
    AC_ADMIN.fixId = "";
    AC_ADMIN.fixInfo = null;
    await acLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "Tuzatish";
    // Play-off maxsus xatolari (talab 1) — server sabablari
    const msg = {
      match_not_found: ACT("aca_match_404_low"),
      draw_not_allowed: "final durang bo'lmaydi",
      aggregate_draw_not_allowed: "ikki o'yin agregati teng bo'lib qoladi (g'olib aniq bo'lsin)",
    }[e.message] || e.message;
    showToast(ACT("ac_error") + msg);
  }
}

// Kalendarni qayta qurish (ikki doira, to'g'ri tur raqamlari)
// Barcha ishtirokchilar ro'yxatini yuklaydi (admin almashtirish uchun)
async function acLoadOrphans() {
  const box = document.getElementById("ac-orphans-box");
  if (!box) return;
  try {
    const d = await apiFetch("/ac/participants/all");
    const list = d.participants || [];
    if (!list.length) {
      box.innerHTML = `<div style="font-size:12px;opacity:.6">${ACT("aca_players_404")}</div>`;
      return;
    }
    const opts = list.map(o => {
      const mark = o.orphan ? "⚠️ " : "";
      const label = `${mark}G${o.group_number || "?"} · ${(o.nickname || "—").replace(/"/g, "")}`;
      return `<option value="${o.user_id}">${label}</option>`;
    }).join("");
    box.innerHTML = `<select class="modal-input ac-orphan-select" id="ac-orphan-select">
      <option value="">— almashtiriladigan ishtirokchini tanlang —</option>${opts}
    </select>`;
  } catch (_) {
    box.innerHTML = `<div style="font-size:12px;opacity:.6">${ACT("aca_list_failed")}</div>`;
  }
}

// Akkount almashtirish (tanlangan participant → yangi Telegram ID)
async function acAdminReassign(btn) {
  const sel = document.getElementById("ac-orphan-select");
  const oldUid = sel ? Number(sel.value || 0) : 0;
  const newTg = Number(document.getElementById("ac-new-tg").value || 0);
  if (!oldUid) { showToast("Almashtiriladigan ishtirokchini tanlang"); return; }
  if (!newTg) { showToast("Yangi Telegram ID kiriting"); return; }
  if (!confirm(`Tanlangan ishtirokchi yangi akkountga (${newTg}) bog'lansinmi?`)) return;
  btn.disabled = true;
  const prev = btn.innerHTML;
  btn.textContent = ACT("aca_connecting");
  try {
    const r = await apiFetch("/ac/participant/reassign", {
      method: "POST",
      body: JSON.stringify({ old_user_id: oldUid, new_telegram_id: newTg }),
    });
    showToast(`Bog'landi: ${r.matches_updated} o'yin yangilandi. Endi kalendarni qayta quring.`);
    await acLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = prev;
    const msg = {
      new_user_not_found: "yangi akkount botda topilmadi (avval /start bossin)",
      nothing_to_reassign: "bu id topilmadi",
      new_already_participant: "yangi akkount allaqachon ishtirokchi",
    }[e.message] || e.message;
    showToast(ACT("ac_error") + msg);
  }
}

async function acAdminDraw(btn) {
  if (!confirm(ACT("aca_draw_ask"))) return;
  btn.disabled = true;                       // ikki marta bosishdan himoya (qoida 38)
  btn.textContent = ACT("aca_drawing");  // vizual javob (qoida 40)
  try {
    const r = await apiFetch("/ac/draw", { method: "POST" });
    showToast(`Qur'a o'tkazildi: ${r.participants} ishtirokchi, ${r.matches} o'yin`);
    AC.section = "home";
    await acLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("dice", 16)} Qur'a o'tkazish`;
    showToast(ACT("ac_error") + acDrawErrorText(e.message));
  }
}

// Turlarni boshlash (1-tur ochiladi)
async function acAdminStart(btn) {
  if (!confirm(ACT("aca_start_ask"))) return;
  btn.disabled = true;
  btn.textContent = ACT("aca_starting");
  try {
    const r = await apiFetch("/ac/rounds/start", { method: "POST" });
    showToast(`Boshlandi: ${r.current_matchday}-tur ochildi`);
    AC.section = "profile";
    await acLoadProfile();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("play", 16)} O'yinlarni boshlash`;
    showToast(ACT("ac_error") + acDrawErrorText(e.message));
  }
}

function acDrawErrorText(reason) {
  return ({
    already_drawn: ACT("aca_err_drawn"),
    no_participants: ACT("aca_err_no_qual"),
    not_drawn: ACT("aca_err_draw_first"),
    results_exist: ACT("aca_err_has_results"),
    already_started: ACT("aca_err_started"),
    matchday_locked: ACT("ac_round_locked").toLowerCase(),
  })[reason] || reason;
}
