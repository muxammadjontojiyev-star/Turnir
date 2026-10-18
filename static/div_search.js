// =============================================================
//  div_search.js — Divizion reytingida QIDIRUV (2026-10-18)
//  Raqibning @username yoki ismini yozsangiz — o'rni, balli chiqadi; bosilsa jadval o'sha
//  qatorga suriladi va yonadi (div-row-flash, "Sizning o'rningiz" bilan bir xil effekt).
//  Qidiruv brauzerda — DIV.rating allaqachon yuklangan (serverga qo'shimcha so'rov yo'q).
//  division.js divRenderRating() -> divSearchBoxHtml(). Global: DIV, APP, escHtml.
// =============================================================

const DIV_SEARCH_MAX = 8;          // ko'rsatiladigan natijalar soni
const DIV_SEARCH_TXT = {
  uz: { ph: "🔍 Raqib: @username yoki ism", none: "Topilmadi", pts: "ball", more: "yana {n} ta — aniqroq yozing" },
  ru: { ph: "🔍 Соперник: @username или имя", none: "Не найдено", pts: "очк.", more: "ещё {n} — уточните запрос" },
  en: { ph: "🔍 Opponent: @username or name", none: "Not found", pts: "pts", more: "{n} more — refine your search" },
};

function divSearchT(k) { return (DIV_SEARCH_TXT[APP.lang] || DIV_SEARCH_TXT.uz)[k]; }

function divSearchBoxHtml() {
  return `<div class="div-search">
      <input id="div-search-q" class="modal-input" type="search" autocomplete="off" placeholder="${escHtml(divSearchT("ph"))}">
      <div id="div-search-res" class="div-search-res"></div>
    </div>`;
}

function divSearchNorm(s) { return String(s || "").toLowerCase().replace(/^@/, "").trim(); }

function divSearchRun(q) {
  const box = document.getElementById("div-search-res");
  if (!box) return;
  const nq = divSearchNorm(q);
  if (!nq) { box.innerHTML = ""; return; }
  const found = [];
  (DIV.rating || []).forEach((p, i) => {
    if (divSearchNorm(p.username).includes(nq) || divSearchNorm(p.nickname).includes(nq)) found.push([p, i]);
  });
  if (!found.length) { box.innerHTML = `<div class="div-search-none">${escHtml(divSearchT("none"))}</div>`; return; }
  const items = found.slice(0, DIV_SEARCH_MAX).map(([p, i]) => {
    const label = p.username ? "@" + p.username : (p.nickname || "—");
    const sub = p.username && p.nickname ? p.nickname : "";
    return `<button class="div-search-item" data-div-find="${p.user_id}">
        <b class="div-search-rank">${i + 1}</b>
        <span class="div-search-name">${escHtml(label)}${sub ? `<small>${escHtml(sub)}</small>` : ""}</span>
        <span class="div-search-pts">${p.rating ?? 1500} ${escHtml(divSearchT("pts"))}</span>
      </button>`;
  }).join("");
  const more = found.length > DIV_SEARCH_MAX
    ? `<div class="div-search-none">${escHtml(divSearchT("more").replace("{n}", found.length - DIV_SEARCH_MAX))}</div>` : "";
  box.innerHTML = items + more;
}

function divSearchGoto(uid) {
  const row = document.querySelector(`.div-rating-row[data-uid="${uid}"]`);
  if (!row) return;
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  row.classList.add("div-row-flash");
  setTimeout(() => row.classList.remove("div-row-flash"), 1600);
}

document.addEventListener("input", (e) => {
  if (e.target && e.target.id === "div-search-q") divSearchRun(e.target.value);
});
document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-div-find]") : null;
  if (b) divSearchGoto(b.dataset.divFind);
});
