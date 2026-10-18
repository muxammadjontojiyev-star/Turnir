// =============================================================
//  admin_participants.js — Liga ishtirokchilari: QIDIRUV + amallar (2026-10-13)
//  Bosh admin so'rovi: ligalar bo'yicha uzun ro'yxat (Chiqarish tugmalari) va
//  ochiladigan ro'yxatlardan qidirish o'rniga — bitta qidiruv maydoni:
//    klub nomi, @username, nik yoki Telegram ID yoziladi → mos ishtirokchilar
//    kartochkada chiqadi → bittasi tanlanadi → amallar:
//      👤 Yangi akkountga o'tkazish  (POST /league/participant/reassign, new_query)
//      🔄 Boshqa ishtirokchi bilan o'zaro almashtirish (POST /league/participants/swap)
//      🚫 Chiqarish (api.js removePlayer — DELETE /admin/players/{id}, avvalgi tugma bilan bir xil)
//  Ma'lumot: GET /league/participants/all (bir marta yuklanadi, qidiruv brauzerda).
//  Faqat bosh admin (backend himoyalangan). Global: apiFetch, escHtml, showToast,
//  findClubLogo, removePlayer.
// =============================================================

const ADM_PP_MAX_RESULTS = 8;
const ADM_PP = { list: [], sel: null, swapB: null };

// Qidiruv uchun normallashtirish: kichik harf, urg'usiz (Cádiz → cadiz), @ siz
function admPpNorm(s) {
  return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/^@/, "").trim();
}

function admPpFind(query, excludeId) {
  const q = admPpNorm(query);
  if (!q) return [];
  const isNum = /^\d+$/.test(q);
  return ADM_PP.list.filter(o => o.user_id !== excludeId && (
    (isNum && String(o.telegram_id || "").startsWith(q)) ||
    admPpNorm(o.club_name).includes(q) ||
    admPpNorm(o.username).includes(q) ||
    admPpNorm(o.nickname).includes(q)
  )).slice(0, ADM_PP_MAX_RESULTS);
}

function admPpCardHtml(o, attr) {
  const logo = o.club_name && typeof findClubLogo === "function" ? findClubLogo(o.club_name) : null;
  const logoHtml = logo
    ? `<img class="admin-player-logo" src="${escHtml(logo)}" alt="">`
    : `<span class="admin-player-logo admin-player-logo--empty"></span>`;
  const name = o.username ? `@${escHtml(o.username)}` : escHtml(o.nickname || "—");
  return `<button class="adm-pp-card" ${attr}="${o.user_id}">
      ${logoHtml}
      <span class="adm-pp-info">
        <b>${o.orphan ? "⚠️ " : ""}${name}</b>
        <span>${escHtml(o.league_name || "?")} · ${escHtml(o.club_name || "—")}${o.telegram_id ? ` · ID ${escHtml(String(o.telegram_id))}` : ""}</span>
      </span>
    </button>`;
}

function admPpRenderResults() {
  const box = document.getElementById("adm-pp-results");
  const q = document.getElementById("adm-pp-q")?.value || "";
  if (!box) return;
  if (!admPpNorm(q)) { box.innerHTML = ""; return; }
  const found = admPpFind(q);
  box.innerHTML = found.length
    ? found.map(o => admPpCardHtml(o, "data-pp-pick")).join("")
    : `<div class="adm-pp-empty">Hech kim topilmadi</div>`;
}

function admPpRenderPanel() {
  const panel = document.getElementById("adm-pp-panel");
  if (!panel) return;
  const o = ADM_PP.sel;
  if (!o) { panel.innerHTML = ""; return; }
  const b = ADM_PP.swapB;
  panel.innerHTML = `
    <div class="adm-pp-selected">
      ${admPpCardHtml(o, "data-pp-none")}
      <button class="adm-pp-x" id="adm-pp-clear" title="Bekor">✕</button>
    </div>

    <div class="adm-pp-act">
      <div class="adm-pp-act-title">👤 Yangi akkountga o'tkazish</div>
      <div class="adm-pp-hint">Klub, jadval va natijalar joyida qoladi — o'yinchi almashadi.</div>
      <input id="adm-pp-new" class="modal-input" type="text" autocomplete="off" placeholder="Yangi Telegram ID yoki @username">
      <label class="adm-pp-check"><input type="checkbox" id="adm-pp-abandoned" checked>
        Tashlab ketdi (kanalni tark etdi) — keyingi mavsumda klub tanlash navbatida oxirgi bo'ladi</label>
      <button class="btn" id="adm-pp-reassign">👤 O'tkazish</button>
    </div>

    <div class="adm-pp-act">
      <div class="adm-pp-act-title">🔄 Boshqa ishtirokchi bilan o'zaro almashtirish</div>
      <div class="adm-pp-hint">Ikkalasining o'rni (liga, klub, natijalar) joyida qoladi — odamlar almashadi.</div>
      ${b
        ? `<div class="adm-pp-selected">${admPpCardHtml(b, "data-pp-none")}<button class="adm-pp-x" id="adm-pp-b-clear" title="Bekor">✕</button></div>
           <button class="btn" id="adm-pp-swap">🔄 O'zaro almashtirish</button>`
        : `<input id="adm-pp-bq" class="modal-input" type="text" autocomplete="off" placeholder="Ikkinchi ishtirokchi: klub, @username yoki ID">
           <div id="adm-pp-bresults" class="adm-pp-results"></div>`}
    </div>

    <button class="btn btn--danger adm-pp-remove" id="adm-pp-remove">🚫 Chiqarish</button>`;

  document.getElementById("adm-pp-clear")?.addEventListener("click", () => { ADM_PP.sel = null; ADM_PP.swapB = null; admPpRenderPanel(); });
  document.getElementById("adm-pp-b-clear")?.addEventListener("click", () => { ADM_PP.swapB = null; admPpRenderPanel(); });
  document.getElementById("adm-pp-reassign")?.addEventListener("click", e => void admPpReassign(e.currentTarget));
  document.getElementById("adm-pp-swap")?.addEventListener("click", e => void admPpSwap(e.currentTarget));
  document.getElementById("adm-pp-remove")?.addEventListener("click", () => { if (typeof removePlayer === "function") void removePlayer(o.user_id); });
  const bq = document.getElementById("adm-pp-bq");
  bq?.addEventListener("input", () => {
    const res = document.getElementById("adm-pp-bresults");
    if (!res) return;
    const found = admPpFind(bq.value, o.user_id);
    res.innerHTML = !admPpNorm(bq.value) ? ""
      : found.length ? found.map(x => admPpCardHtml(x, "data-pp-b")).join("") : `<div class="adm-pp-empty">Hech kim topilmadi</div>`;
  });
}

function admPpLabel(o) {
  return `${o.username ? "@" + o.username : (o.nickname || "—")} (${o.league_name || "?"} · ${o.club_name || "—"})`;
}

async function admPpReassign(btn) {
  const o = ADM_PP.sel;
  const q = (document.getElementById("adm-pp-new")?.value || "").trim();
  if (!o) return;
  if (!q) { showToast("Yangi Telegram ID yoki @username kiriting"); return; }
  if (!confirm(`${admPpLabel(o)} o'rni ${q} akkountiga o'tkazilsinmi?\n\nQur'a natijasi o'zgarmaydi.`)) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/league/participant/reassign", {
      method: "POST", body: JSON.stringify({ old_user_id: o.user_id, new_query: q,
        abandoned: !!document.getElementById("adm-pp-abandoned")?.checked }),   // 2026-10-18: klub navbati
    });
    showToast(`✅ O'tkazildi: ${r.matches_updated || 0} o'yin yangilandi`);
    await admPpReload();
  } catch (e) {
    const msg = {
      new_user_not_found: "yangi akkount botda topilmadi (avval /start bossin)",
      nothing_to_reassign: "bu ishtirokchi topilmadi",
      new_already_participant: "yangi akkount allaqachon ishtirokchi",
    }[e.message] || e.message;
    showToast("Xato: " + msg);
    btn.disabled = false;
  }
}

async function admPpSwap(btn) {
  const a = ADM_PP.sel, b = ADM_PP.swapB;
  if (!a || !b) return;
  if (!confirm(`Quyidagilar O'ZARO almashtirilsinmi?\n\n${admPpLabel(a)}\n⇅\n${admPpLabel(b)}\n\nQur'a natijasi o'zgarmaydi — faqat o'yinchilar almashadi.`)) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/league/participants/swap", {
      method: "POST", body: JSON.stringify({ user_id_a: a.user_id, user_id_b: b.user_id }),
    });
    showToast(`✅ Almashtirildi: ${r.matches_updated || 0} o'yin ustuni yangilandi`);
    await admPpReload();
  } catch (e) {
    const msg = {
      same_user: "bir xil ishtirokchi tanlandi",
      participant_not_found: "ishtirokchi(lar) topilmadi",
    }[e.message] || e.message;
    showToast("Xato: " + msg);
    btn.disabled = false;
  }
}

async function admPpReload() {
  try {
    const d = await apiFetch("/league/participants/all");
    ADM_PP.list = d.participants || [];
  } catch (_) {
    ADM_PP.list = [];
  }
  ADM_PP.sel = null;
  ADM_PP.swapB = null;
  const inp = document.getElementById("adm-pp-q");
  if (inp) inp.value = "";
  admPpRenderResults();
  admPpRenderPanel();
  const cnt = document.getElementById("adm-pp-count");
  if (cnt) cnt.textContent = ADM_PP.list.length ? `${ADM_PP.list.length} ishtirokchi` : "";
}

// api.js loadAdminPanel (bosh admin) chaqiradi
async function admPpInit() {
  const root = document.getElementById("adm-pp");
  if (!root) return;
  if (!root._bound) {
    root._bound = true;
    document.getElementById("adm-pp-q")?.addEventListener("input", admPpRenderResults);
    root.addEventListener("click", (e) => {
      const pick = e.target.closest("[data-pp-pick]");
      if (pick) {
        ADM_PP.sel = ADM_PP.list.find(o => String(o.user_id) === pick.dataset.ppPick) || null;
        ADM_PP.swapB = null;
        document.getElementById("adm-pp-q").value = "";
        admPpRenderResults();
        admPpRenderPanel();
        return;
      }
      const pb = e.target.closest("[data-pp-b]");
      if (pb) {
        ADM_PP.swapB = ADM_PP.list.find(o => String(o.user_id) === pb.dataset.ppB) || null;
        admPpRenderPanel();
      }
    });
  }
  await admPpReload();
}
