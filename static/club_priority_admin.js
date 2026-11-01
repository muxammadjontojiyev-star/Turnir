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
        c_off: "Navbat o'chirilsinmi? Hamma darhol klub tanlay oladi.", c_on: "Navbat yoqilsinmi? Yangilar va tashlab ketganlar kutadi." },
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
}

if (typeof loadSeasonInfo === "function") {
  const _cpaPrevSeasonInfo = loadSeasonInfo;
  loadSeasonInfo = async function () {
    await _cpaPrevSeasonInfo();
    await cpaRender();
  };
}
