// =============================================================
//  club_priority_admin.js — Admin → «LIGA MAVSUMI»: klub tanlash NAVBATI kaliti (2026-11-01)
//  Yoqilgan: o'tgan mavsumni oxirigacha o'ynaganlar darhol, yangilar keyinroq, tashlab ketganlar oxirida
//  (club_priority.py). O'chiq: hamma darhol klub tanlaydi. API: GET/POST /admin/club-priority {on}.
//  loadSeasonInfo (api.js / season_break.js) qayta tayinlash orqali o'raladi — index.html da season_break.js
//  dan KEYIN ulanadi. Global: APP, apiFetch, showToast.
// =============================================================

const CPA_TXT = {
  uz: { on: "🟢 Klub tanlash navbati: YOQILGAN", off: "⚪ Klub tanlash navbati: O'CHIQ",
        btn_off: "O'chirish", btn_on: "Yoqish",
        hint: "Yoqilganda: oxirigacha o'ynaganlar darhol, yangilar 24 soatdan, tashlab ketganlar 48 soatdan keyin klub tanlaydi (yangi mavsum ochilgan paytdan). O'chiq — hamma darhol.",
        c_off: "Navbat o'chirilsinmi? Hamma darhol klub tanlay oladi.", c_on: "Navbat yoqilsinmi? Yangilar va tashlab ketganlar kutadi.",
        ab_title: "«Tashlab ketgan» deb belgilanganlar ({s}-mavsum): {n}",
        ab_hint: "Yozuvi yo'q odam «yangi» hisoblanadi. Bu ro'yxatdagilarga «navbatingiz oxirida» chiqadi — kerak bo'lsa belgini olib tashlang.",
        ab_clear: "Belgini olib tashlash", ab_c: "Belgi olib tashlansinmi? Odam «yangi» navbatiga o'tadi.",
        r_club_taken: "klubi boshqaga o'tgan (topshirgan yoki kanaldan chiqqan)", r_admin: "admin akkauntni ko'chirgan", r_removed: "o'yinlari bor holda chiqarilgan",
        r_null: "sababi yozilmagan (eski)", find_ph: "@username yoki Telegram ID", find_btn: "Tekshirish",
        f_none: "Topilmadi", t_finished: "oxirigacha o'ynagan — darhol", t_new: "yangi — {t} dan", t_abandoned: "tashlab ketgan — {t} dan",
        t_off: "navbat o'chiq — darhol", t_open: "hozir tanlay oladi" },
  ru: { on: "🟢 Очередь выбора клуба: ВКЛЮЧЕНА", off: "⚪ Очередь выбора клуба: ВЫКЛЮЧЕНА",
        btn_off: "Выключить", btn_on: "Включить",
        hint: "Включена: доигравшие — сразу, новые — через 24 ч, бросившие — через 48 ч (от старта сезона). Выключена — все сразу.",
        c_off: "Выключить очередь? Все смогут выбрать клуб сразу.", c_on: "Включить очередь? Новые и бросившие будут ждать." },
  en: { on: "🟢 Club pick queue: ON", off: "⚪ Club pick queue: OFF",
        btn_off: "Turn off", btn_on: "Turn on",
        hint: "On: players who finished pick at once, new ones after 24 h, those who left after 48 h (from season start). Off — everyone at once.",
        c_off: "Turn the queue off? Everyone can pick a club right away.", c_on: "Turn the queue on? New players and leavers will wait." },
};

function cpaT(k) { return (CPA_TXT[APP.lang] || CPA_TXT.uz)[k] || CPA_TXT.uz[k]; }

function cpaTime(iso) {
  return typeof clubPrioTime === "function" ? clubPrioTime(iso) : String(iso || "").slice(0, 16).replace("T", " ");
}

// 2026-11-02: «tashlab ketgan»lar ro'yxati, qidiruv va belgini olib tashlash (GET/POST /admin/club-priority/...)
async function cpaRenderAbandoned(box, q) {
  let d;
  try { d = await apiFetch("/admin/club-priority/abandoned" + (q ? "?q=" + encodeURIComponent(q) : "")); }
  catch (_) { return; }
  const list = d.list || [];
  let found = "";
  if (q) {
    const f = d.found;
    if (!f) found = `<div class="admin-player-league" style="margin:6px 2px">${escHtml(cpaT("f_none"))}</div>`;
    else {
      const p = f.priority || {};
      const st = !p.active ? cpaT(p.tier ? "t_open" : "t_off")
        : p.tier === "finished" ? cpaT("t_finished") : cpaT(p.tier === "abandoned" ? "t_abandoned" : "t_new").replace("{t}", cpaTime(p.opens_at));
      found = `<div class="admin-player-league" style="margin:6px 2px">${escHtml(f.username ? "@" + f.username : (f.nickname || ""))} · ID ${escHtml(f.telegram_id)} — <b>${escHtml(st)}</b></div>`;
    }
  }
  const rows = list.map(r => `<div style="display:flex;align-items:center;gap:8px;padding:6px 2px;border-bottom:1px solid rgba(255,255,255,.06)">
      <span style="flex:1;min-width:0">${escHtml(r.username ? "@" + r.username : (r.nickname || "—"))} <small style="opacity:.6">· ID ${escHtml(r.telegram_id)}</small><br>
        <small style="opacity:.7">${escHtml(cpaT("r_" + (r.reason || "null")))} · ${escHtml(String(r.created_at || "").slice(0, 16))}</small></span>
      <button class="btn" style="padding:6px 10px;font-size:12px" data-cpa-clear="${Number(r.telegram_id)}">${escHtml(cpaT("ab_clear"))}</button>
    </div>`).join("");
  box.innerHTML = `<div class="admin-player-league" style="margin:12px 2px 4px"><b>${escHtml(cpaT("ab_title").replace("{s}", d.season).replace("{n}", list.length))}</b></div>
    <div class="admin-player-league" style="margin:0 2px 6px;opacity:.75">${escHtml(cpaT("ab_hint"))}</div>
    <div style="display:flex;gap:6px"><input class="modal-input" id="cpa-find" placeholder="${escHtml(cpaT("find_ph"))}" value="${escHtml(q || "")}" style="flex:1">
      <button class="btn" id="cpa-find-btn">${escHtml(cpaT("find_btn"))}</button></div>${found}${rows}`;
  document.getElementById("cpa-find-btn").addEventListener("click", () => cpaRenderAbandoned(box, document.getElementById("cpa-find").value));
  box.querySelectorAll("[data-cpa-clear]").forEach(b => b.addEventListener("click", async () => {
    if (!window.confirm(cpaT("ab_c"))) return;
    b.disabled = true;
    try { await apiFetch("/admin/club-priority/clear", { method: "POST", body: JSON.stringify({ telegram_id: Number(b.dataset.cpaClear) }) }); showToast("✅"); }
    catch (err) { showToast("❌ " + err.message); }
    await cpaRenderAbandoned(box, q);
  }));
}

async function cpaRender() {
  const anchor = document.getElementById("btn-finalize-season");
  if (!anchor) return;
  let box = document.getElementById("club-priority-admin");
  if (!box) {
    box = document.createElement("div");
    box.id = "club-priority-admin";
    box.style.marginTop = "14px";
    anchor.parentNode.appendChild(box);
  }
  let on;
  try { on = !!(await apiFetch("/admin/club-priority")).on; } catch (_) { box.innerHTML = ""; return; }
  box.innerHTML = `<div class="admin-player-league" style="margin:0 2px 6px"><b>${cpaT(on ? "on" : "off")}</b></div>
    <button class="btn ${on ? "" : "btn--primary"}" id="btn-club-priority" style="width:100%">${cpaT(on ? "btn_off" : "btn_on")}</button>
    <div class="admin-player-league" style="margin:6px 2px 0">${cpaT("hint")}</div>`;
  document.getElementById("btn-club-priority").addEventListener("click", async (e) => {
    if (!window.confirm(cpaT(on ? "c_off" : "c_on"))) return;
    e.target.disabled = true;                              // ikki marta bosish (qoida #38)
    try {
      await apiFetch("/admin/club-priority", { method: "POST", body: JSON.stringify({ on: !on }) });
      showToast("✅");
    } catch (err) {
      showToast("❌ " + err.message);
    }
    await cpaRender();
  });
  const ab = document.createElement("div");
  ab.id = "club-priority-abandoned";
  box.appendChild(ab);
  await cpaRenderAbandoned(ab, "");
}

if (typeof loadSeasonInfo === "function") {
  const _cpaPrevSeasonInfo = loadSeasonInfo;
  loadSeasonInfo = async function () {
    await _cpaPrevSeasonInfo();
    await cpaRender();
  };
}
