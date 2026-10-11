// =============================================================
//  admin_contacts.js — "MAS'UL ADMINLAR" bloki (2026-10-11)
//  Har rejimning Profil sahifasida, profil kartasi ostida: bosh admin tayinlagan
//  adminlar va ularning Telegram profiliga bitta bosishda o'tish.
//  Liga — faqat o'z ligasining adminlari; ChL/YeL/Divizion/JCh — shu rejim adminlari.
//  Backend: GET /admins/contacts?mode=... (admin_contacts.py). Admin yo'q bo'lsa blok chiqmaydi.
//  Joylash: renderer'lar adminContactsBoxHtml(mode) qo'yadi; to'ldirish avtomatik
//  (MutationObserver — rejimlar sahifani tez-tez qayta chizadi, qoida #26).
//  Global: APP, apiFetch, escHtml.
// =============================================================

const ADMIN_CONTACTS_TTL_MS = 5 * 60 * 1000;     // 5 daqiqa kesh
const ADMIN_CONTACTS = { cache: {}, loading: {} };

function adminContactsListHtml(list) {
  const t = APP.t || {};
  if (!list || !list.length) return "";
  const rows = list.map(a => {
    const name = a.nickname || (a.username ? "@" + a.username : "Admin");
    const sub = a.username ? `@${escHtml(a.username)}` : "";
    const href = a.username ? `https://t.me/${encodeURIComponent(a.username)}` : `tg://user?id=${encodeURIComponent(a.telegram_id)}`;
    return `<button class="admin-contact-row" data-admin-contact="${escHtml(href)}">
        <span class="admin-contact-icon">🛡</span>
        <span class="admin-contact-info"><b>${escHtml(name)}</b>${sub ? `<span>${sub}</span>` : ""}</span>
        <span class="admin-contact-go">${escHtml(t.admin_contact_write || "Yozish")} ›</span>
      </button>`;
  }).join("");
  return `<div class="section-label">${escHtml(t.admin_contacts_title || "MAS'UL ADMINLAR")}</div>
    <div class="admin-contacts-list">${rows}</div>`;
}

// Renderer'lar shu joy-egallovchini qo'yadi (kesh bo'lsa darhol to'la chiziladi)
function adminContactsBoxHtml(mode) {
  const c = ADMIN_CONTACTS.cache[mode];
  const fresh = c && Date.now() - c.at < ADMIN_CONTACTS_TTL_MS;
  return `<div class="admin-contacts" data-admin-contacts="${escHtml(mode)}"${fresh ? ' data-ac-done="1"' : ""}>${fresh ? adminContactsListHtml(c.list) : ""}</div>`;
}

async function adminContactsFetch(mode) {
  const c = ADMIN_CONTACTS.cache[mode];
  if (c && Date.now() - c.at < ADMIN_CONTACTS_TTL_MS) return c.list;
  if (ADMIN_CONTACTS.loading[mode]) return ADMIN_CONTACTS.loading[mode];
  ADMIN_CONTACTS.loading[mode] = apiFetch(`/admins/contacts?mode=${encodeURIComponent(mode)}`)
    .then(d => { ADMIN_CONTACTS.cache[mode] = { list: d.admins || [], at: Date.now() }; return d.admins || []; })
    .catch(() => [])                                   // blok shunchaki chiqmaydi (ixtiyoriy ma'lumot)
    .finally(() => { delete ADMIN_CONTACTS.loading[mode]; });
  return ADMIN_CONTACTS.loading[mode];
}

function adminContactsFill() {
  document.querySelectorAll("[data-admin-contacts]:not([data-ac-done])").forEach(box => {
    box.dataset.acDone = "1";
    const mode = box.dataset.adminContacts;
    void adminContactsFetch(mode).then(list => {
      document.querySelectorAll(`[data-admin-contacts="${mode}"]`).forEach(b => {
        b.innerHTML = adminContactsListHtml(list);
        b.dataset.acDone = "1";
      });
    });
  });
}

function adminContactOpen(href) {
  const tg = window.Telegram?.WebApp;
  try {
    if (href.startsWith("https://t.me/") && tg?.openTelegramLink) tg.openTelegramLink(href);
    else if (tg?.openLink) tg.openLink(href);
    else window.open(href, "_blank");
  } catch (_) {
    window.open(href, "_blank");
  }
}

if (!window._adminContactsBound) {
  window._adminContactsBound = true;
  document.addEventListener("click", (e) => {
    const row = e.target.closest ? e.target.closest("[data-admin-contact]") : null;
    if (row) adminContactOpen(row.dataset.adminContact);
  });
  let scheduled = false;
  const obs = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled = false; adminContactsFill(); });
  });
  const start = () => { obs.observe(document.body, { childList: true, subtree: true }); adminContactsFill(); };
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);
}
