// =============================================================
//  leagues_admin.js — Admin → «LIGA MAVSUMI»: LIGALARNI YOQISH / O'CHIRISH (bosh admin, 2026-11-02)
//  Yangi kelganlarga joy yetmasa — liga (masalan 2-liga) yoqiladi; keraksizi o'chiriladi (botda ko'rinmaydi,
//  ma'lumot saqlanadi). Ishtirokchisi bor ligani o'chirib bo'lmaydi (backend: has_players).
//  API: GET /admin/leagues/all, POST /admin/leagues/{id}/active {on} (leagues_admin.py).
//  loadSeasonInfo qayta tayinlash orqali o'raladi — club_priority_admin.js dan KEYIN ulanadi.
//  Global: APP, apiFetch, escHtml, showToast, loadHome (api.js).
// =============================================================

const LGA_TXT = {
  uz: { title: "🏟 LIGALAR — YOQISH / O'CHIRISH", hint: "O'chirilgan liga botda ko'rinmaydi, ma'lumoti saqlanadi. Ishtirokchisi bor ligani o'chirib bo'lmaydi.",
        on: "Yoqilgan", off: "O'chiq", btn_on: "Yoqish", btn_off: "O'chirish", players: "o'yinchi",
        r_eu: "🌍 Yevropa", r_asia: "🌏 Osiyo", r_sa: "🌎 Janubiy Amerika", r_na: "🌎 Shimoliy Amerika",
        c_on: "«{n}» ligasi yoqilsinmi? U botda ko'rinadi va ro'yxatdan o'tish ochiladi.",
        c_off: "«{n}» ligasi o'chirilsinmi? U botda ko'rinmaydi.", has_players: "Bu ligada ishtirokchilar bor — o'chirib bo'lmaydi." },
  ru: { title: "🏟 ЛИГИ — ВКЛ / ВЫКЛ", hint: "Выключенная лига скрыта в боте, данные сохраняются. Лигу с участниками выключить нельзя.",
        on: "Вкл", off: "Выкл", btn_on: "Включить", btn_off: "Выключить", players: "игроков",
        r_eu: "🌍 Европа", r_asia: "🌏 Азия", r_sa: "🌎 Южная Америка", r_na: "🌎 Северная Америка",
        c_on: "Включить лигу «{n}»? Она появится в боте, откроется регистрация.",
        c_off: "Выключить лигу «{n}»? Она будет скрыта.", has_players: "В лиге есть участники — выключить нельзя." },
  en: { title: "🏟 LEAGUES — ON / OFF", hint: "A turned-off league is hidden in the bot, its data is kept. A league with players can't be turned off.",
        on: "On", off: "Off", btn_on: "Turn on", btn_off: "Turn off", players: "players",
        r_eu: "🌍 Europe", r_asia: "🌏 Asia", r_sa: "🌎 South America", r_na: "🌎 North America",
        c_on: "Turn on «{n}»? It will appear in the bot and registration opens.",
        c_off: "Turn off «{n}»? It will be hidden.", has_players: "This league has players — it can't be turned off." },
};
function lgaT(k, n) { return ((LGA_TXT[APP.lang] || LGA_TXT.uz)[k] || LGA_TXT.uz[k]).replace("{n}", n || ""); }

async function lgaRender() {
  const anchor = document.getElementById("btn-finalize-season");
  if (!anchor) return;
  let box = document.getElementById("leagues-admin");
  if (!box) {
    box = document.createElement("div");
    box.id = "leagues-admin";
    box.style.marginTop = "16px";
    anchor.parentNode.appendChild(box);
  }
  let list;
  try { list = (await apiFetch("/admin/leagues/all")).leagues || []; } catch (_) { box.innerHTML = ""; return; }
  let region = null;
  const rows = list.map(l => {
    const head = l.region !== region ? `<div class="admin-player-league" style="margin:10px 2px 4px"><b>${escHtml(lgaT("r_" + (l.region || "eu")))}</b></div>` : "";
    region = l.region;
    const on = !!l.is_active;
    return head + `<div style="display:flex;align-items:center;gap:8px;padding:6px 2px;border-bottom:1px solid rgba(255,255,255,.06)">
        <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;${on ? "" : "opacity:.55"}">${escHtml(l.name)}
          <small style="opacity:.6">· ${Number(l.players)}/${Number(l.max_players)} ${escHtml(lgaT("players"))}</small></span>
        <small style="color:${on ? "#4ade80" : "#94a3b8"}">${escHtml(lgaT(on ? "on" : "off"))}</small>
        <button class="btn ${on ? "" : "btn--primary"}" style="padding:6px 10px;font-size:12px;min-width:86px"
          data-lga-id="${Number(l.id)}" data-lga-on="${on ? 0 : 1}" data-lga-name="${escHtml(l.name)}">${escHtml(lgaT(on ? "btn_off" : "btn_on"))}</button>
      </div>`;
  }).join("");
  box.innerHTML = `<div class="admin-player-league" style="margin:0 2px 4px"><b>${escHtml(lgaT("title"))}</b></div>
    <div class="admin-player-league" style="margin:0 2px 6px;opacity:.75">${escHtml(lgaT("hint"))}</div>${rows}`;
}

document.addEventListener("click", async (e) => {
  const b = e.target.closest ? e.target.closest("[data-lga-id]") : null;
  if (!b || !document.getElementById("leagues-admin")?.contains(b)) return;
  const on = b.dataset.lgaOn === "1";
  if (!window.confirm(lgaT(on ? "c_on" : "c_off", b.dataset.lgaName))) return;
  b.disabled = true;                                      // ikki marta bosish (qoida #38)
  try {
    await apiFetch(`/admin/leagues/${encodeURIComponent(b.dataset.lgaId)}/active`, { method: "POST", body: JSON.stringify({ on }) });
    showToast("✅");
    if (typeof loadHome === "function") { try { await loadHome(); } catch (_) {} }
  } catch (err) {
    showToast("❌ " + (err.message === "has_players" ? lgaT("has_players") : err.message));
  }
  await lgaRender();
});

if (typeof loadSeasonInfo === "function") {
  const _lgaPrevSeasonInfo = loadSeasonInfo;
  loadSeasonInfo = async function () {
    await _lgaPrevSeasonInfo();
    await lgaRender();
  };
}
