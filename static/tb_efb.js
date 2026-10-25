// =============================================================
//  tb_efb.js — "TEAMLAR JANGI": eFootball akkaunti (2026-10-25)
//  O'rniga boshqa odam o'ynashiga qarshi: har ishtirokchi eFootball User ID va nikini bog'laydi.
//  1) Teamga qo'shilish / team ochish oldidan forma (majburiy — server ham tekshiradi: efb_required).
//  2) Teamim: bog'lanmagan eski a'zolarga ogohlantirish + forma; bog'langanlarga o'z akkaunti.
//  3) A'zolar ro'yxatida eFootball niki (ID — faqat sardor/adminga, backend yashiradi).
//  4) Liga admini / bosh admin: a'zo qatorida «✏️ eFB» — almashtirish, o'chirish, tarix.
//  Backend: POST /tb/efb, /tb/admin/efb, /tb/admin/efb/clear, GET /tb/admin/efb/history (tb_api_efb.py).
//  tb_i18n.js va tb.js dan KEYIN ulanadi. Global: TB, apiFetch, escHtml, tbToast, tbConfirm, tbErr, tbWho.
// =============================================================

function tbEfbLim() {
  return (TB.me && TB.me.efb_limits) || { id_min: 6, id_max: 24, name_min: 2, name_max: 24 };
}

function tbEfbInputsHtml(prefix, cur) {
  const L = tbEfbLim();
  const v = (x) => escHtml((cur && cur[x]) || "");
  return `
    <input id="${prefix}-id" class="modal-input tb-efb-input" maxlength="${L.id_max}" autocomplete="off"
      autocapitalize="characters" spellcheck="false" placeholder="eFootball User ID" value="${v("efb_id")}">
    <input id="${prefix}-name" class="modal-input" maxlength="${L.name_max}" autocomplete="off"
      spellcheck="false" placeholder="eFootball'dagi nikingiz" value="${v("efb_name")}">`;
}

// Qo'shilish / team ochish oldidan (bog'langan bo'lsa — hech narsa)
function tbEfbJoinFormHtml() {
  if (!TB.me || TB.me.efb) return "";
  return `
    <div class="section-label">EFOOTBALL AKKAUNTI</div>
    <div class="card tb-form">
      ${tbEfbInputsHtml("tb-efb")}
      <div class="tb-hint">User ID va nik eFootball'dagi profilingizda ko'rinadi.</div>
      <div class="tb-hint">O'yin oldidan raqibingiz nikingizni ko'radi. ID ni keyin faqat liga admini o'zgartira oladi.</div>
    </div>`;
}

// Teamim sahifasi: eski a'zo (bog'lanmagan) — ogohlantirish + forma; bog'langan — ixcham karta
function tbEfbMineHtml() {
  if (!TB.me) return "";
  const e = TB.me.efb;
  if (e) {
    return `<div class="card tb-efb-mine">🎮 <span>eFootball:</span> <b>${escHtml(e.efb_name)}</b>
        <span class="tb-efb-id">${escHtml(e.efb_id)}</span>
        <div class="tb-hint">O'zgartirish uchun liga adminiga yozing.</div></div>`;
  }
  return `
    <div class="tb-warn">⚠️ eFootball akkauntingizni kiriting — usiz raqibingiz o'yinda sizni taniy olmaydi.</div>
    <div class="card tb-form">
      ${tbEfbInputsHtml("tb-efb")}
      <div class="tb-hint">User ID va nik eFootball'dagi profilingizda ko'rinadi.</div>
      <button class="btn btn--primary" data-tb="efb-save">💾 Saqlash</button>
    </div>`;
}

// Formadagi qiymatni saqlaydi (bog'langan bo'lsa — darhol true). Qaytaradi: true | false
async function tbEfbEnsure(btn) {
  if (!TB.me || TB.me.efb) return true;
  const id = (document.getElementById("tb-efb-id")?.value || "").trim();
  const name = (document.getElementById("tb-efb-name")?.value || "").trim();
  if (!id || !name) { tbToast("Avval eFootball User ID va nikingizni kiriting"); return false; }
  if (btn) btn.disabled = true;
  try {
    const r = await apiFetch("/tb/efb", { method: "POST", body: JSON.stringify({ efb_id: id, efb_name: name }) });
    TB.me.efb = { efb_id: r.efb_id, efb_name: r.efb_name };
    return true;
  } catch (e) {
    tbToast("❌ " + tbErr(e));
    if (btn) btn.disabled = false;
    return false;
  }
}

// ---------------- A'zolar ro'yxati: nik (+ ID sardor/adminga) + admin tahriri ----------------
function tbEfbCanEdit(t) {
  return !!(TB.me && t && (TB.me.is_super || (TB.me.managed_leagues || []).some(x => x.id === t.league_id)));
}

function tbEfbMemberHtml(m, t) {
  const tag = m.efb_name
    ? `<span class="tb-efb-tag">🎮 ${escHtml(m.efb_name)}${m.efb_id ? ` <i>${escHtml(m.efb_id)}</i>` : ""}</span>`
    : `<span class="tb-efb-tag tb-efb-tag--none">🎮 —</span>`;
  const edit = tbEfbCanEdit(t)
    ? `<button class="tb-mini" data-tb-efb-edit="${m.user_id}" data-efb-id="${escHtml(m.efb_id || "")}"
         data-efb-name="${escHtml(m.efb_name || "")}">✏️ eFB</button>` : "";
  return tag + edit;
}

function tbEfbEditorHtml(uid, cur) {
  return `<div class="tb-efb-editor" data-tb-efb-box="${uid}">
      ${tbEfbInputsHtml("tb-efb-adm-" + uid, cur)}
      <div class="tb-g-acts">
        <button class="btn btn--primary" data-tb-efb-act="save" data-uid="${uid}">💾 Saqlash</button>
        <button class="btn btn--ghost" data-tb-efb-act="clear" data-uid="${uid}">🗑 O'chirish</button>
      </div>
      <button class="tb-mini" data-tb-efb-act="hist" data-uid="${uid}">🕘 Tarix</button>
      <div class="tb-efb-hist" id="tb-efb-hist-${uid}"></div>
    </div>`;
}

function tbEfbHistHtml(list) {
  if (!list.length) return `<div class="tb-hint">Tarix bo'sh</div>`;
  return list.map(h => `<div class="tb-efb-hrow"><span>${escHtml(h.created_at || "")}</span>
      <b>${escHtml(h.old_id || "—")} → ${escHtml(h.new_id || "—")}</b>
      <span>${escHtml(h.new_name || h.old_name || "")} · ${escHtml(tbWho({ username: h.by_username, nickname: h.by_nickname }))}</span></div>`).join("");
}

async function tbEfbAdminAct(act, uid, btn) {
  if (act === "hist") {
    const box = document.getElementById("tb-efb-hist-" + uid);
    try { box.innerHTML = tbEfbHistHtml((await apiFetch(`/tb/admin/efb/history?user_id=${uid}`)).history || []); }
    catch (e) { tbToast("❌ " + tbErr(e)); }
    return;
  }
  if (act === "clear" && !tbConfirm("eFootball bog'lashi o'chirilsinmi? O'yinchi qayta o'zi kiritadi.")) return;
  const body = act === "clear" ? { user_id: uid } : {
    user_id: uid,
    efb_id: (document.getElementById(`tb-efb-adm-${uid}-id`)?.value || "").trim(),
    efb_name: (document.getElementById(`tb-efb-adm-${uid}-name`)?.value || "").trim(),
  };
  btn.disabled = true;
  try {
    await apiFetch(act === "clear" ? "/tb/admin/efb/clear" : "/tb/admin/efb", { method: "POST", body: JSON.stringify(body) });
    tbToast(act === "clear" ? "✅ O'chirildi" : "✅ eFootball akkaunti saqlandi");
    TB.me = await apiFetch("/tb/me");
    if (TB.view === "team" && TB._openTeamId) void tbOpenTeam(TB._openTeamId); else tbRenderTab();
  } catch (e) {
    tbToast("❌ " + tbErr(e));
    btn.disabled = false;
  }
}

document.addEventListener("click", (e) => {
  if (!e.target.closest) return;
  const ed = e.target.closest("#tb-root [data-tb-efb-edit]");
  if (ed) {
    const uid = +ed.dataset.tbEfbEdit;
    const open = document.querySelector(`[data-tb-efb-box="${uid}"]`);
    if (open) { open.remove(); return; }
    ed.closest(".tb-member")?.insertAdjacentHTML("afterend",
      tbEfbEditorHtml(uid, { efb_id: ed.dataset.efbId, efb_name: ed.dataset.efbName }));
    return;
  }
  const a = e.target.closest("#tb-root [data-tb-efb-act]");
  if (a) void tbEfbAdminAct(a.dataset.tbEfbAct, +a.dataset.uid, a);
});

// ---------------- Tarjima (ru/en) va xato kodlari ----------------
Object.assign(TB_ERR, {
  efb_required: "Avval eFootball User ID va nikingizni kiriting",
  efb_bad_id: "eFootball ID 6–24 ta lotin harfi yoki raqamdan iborat bo'lsin",
  efb_bad_name: "Nik 2–24 belgidan iborat bo'lsin",
  efb_locked: "eFootball akkaunti allaqachon bog'langan — o'zgartirish faqat liga admini orqali",
  efb_id_taken: "Bu eFootball ID boshqa akkauntga bog'langan",
  efb_not_set: "eFootball akkaunti bog'lanmagan",
});
Object.assign(TB_I18N.ru, {
  "EFOOTBALL AKKAUNTI": "АККАУНТ EFOOTBALL", "eFootball'dagi nikingiz": "Ваш ник в eFootball",
  "User ID va nik eFootball'dagi profilingizda ko'rinadi.": "User ID и ник видны в вашем профиле eFootball.",
  "O'yin oldidan raqibingiz nikingizni ko'radi. ID ni keyin faqat liga admini o'zgartira oladi.": "Перед игрой соперник увидит ваш ник. Изменить ID потом сможет только админ лиги.",
  "eFootball:": "eFootball:", "O'zgartirish uchun liga adminiga yozing.": "Чтобы изменить, напишите админу лиги.",
  "⚠️ eFootball akkauntingizni kiriting — usiz raqibingiz o'yinda sizni taniy olmaydi.": "⚠️ Укажите аккаунт eFootball — без него соперник не узнает вас в игре.",
  "💾 Saqlash": "💾 Сохранить", "✅ eFootball akkaunti saqlandi": "✅ Аккаунт eFootball сохранён",
  "Avval eFootball User ID va nikingizni kiriting": "Сначала укажите User ID и ник в eFootball",
  "eFootball ID 6–24 ta lotin harfi yoki raqamdan iborat bo'lsin": "eFootball ID — 6–24 латинских букв или цифр",
  "Nik 2–24 belgidan iborat bo'lsin": "Ник — 2–24 символа",
  "eFootball akkaunti allaqachon bog'langan — o'zgartirish faqat liga admini orqali": "Аккаунт eFootball уже привязан — изменить может только админ лиги",
  "Bu eFootball ID boshqa akkauntga bog'langan": "Этот eFootball ID привязан к другому аккаунту",
  "eFootball akkaunti bog'lanmagan": "Аккаунт eFootball не привязан",
});
Object.assign(TB_I18N.en, {
  "EFOOTBALL AKKAUNTI": "EFOOTBALL ACCOUNT", "eFootball'dagi nikingiz": "Your eFootball nickname",
  "User ID va nik eFootball'dagi profilingizda ko'rinadi.": "Your User ID and nickname are shown in your eFootball profile.",
  "O'yin oldidan raqibingiz nikingizni ko'radi. ID ni keyin faqat liga admini o'zgartira oladi.": "Your opponent will see your nickname before the match. Only the league admin can change the ID later.",
  "eFootball:": "eFootball:", "O'zgartirish uchun liga adminiga yozing.": "To change it, message the league admin.",
  "⚠️ eFootball akkauntingizni kiriting — usiz raqibingiz o'yinda sizni taniy olmaydi.": "⚠️ Add your eFootball account — otherwise your opponent can't recognise you in the match.",
  "💾 Saqlash": "💾 Save", "✅ eFootball akkaunti saqlandi": "✅ eFootball account saved",
  "Avval eFootball User ID va nikingizni kiriting": "Enter your eFootball User ID and nickname first",
  "eFootball ID 6–24 ta lotin harfi yoki raqamdan iborat bo'lsin": "eFootball ID must be 6–24 Latin letters or digits",
  "Nik 2–24 belgidan iborat bo'lsin": "Nickname must be 2–24 characters",
  "eFootball akkaunti allaqachon bog'langan — o'zgartirish faqat liga admini orqali": "eFootball account is already linked — only the league admin can change it",
  "Bu eFootball ID boshqa akkauntga bog'langan": "This eFootball ID is linked to another account",
  "eFootball akkaunti bog'lanmagan": "eFootball account is not linked",
});

// ---------------- 2-bosqich: VS-oynada ikkala tomonning eFootball niki (tb_season.js tbsGameCardHtml) ----------------
function tbEfbVsHtml(g, iAmHome) {
  const side = (name, id) => name
    ? `<div class="tb-efb-vs-side"><b>🎮 ${escHtml(name)}</b><span>${escHtml(id || "")}</span></div>`
    : `<div class="tb-efb-vs-side is-none"><b>🎮 —</b><span>Kiritilmagan</span></div>`;
  const me = iAmHome ? [g.home_efb, g.home_efb_id] : [g.away_efb, g.away_efb_id];
  const op = iAmHome ? [g.away_efb, g.away_efb_id] : [g.home_efb, g.home_efb_id];
  const warn = op[0] ? `Xonaga faqat shu nik kirishi kerak. Boshqa nik kirsa — o'ynamang va adminga xabar bering.`
    : `Raqib eFootball akkauntini kiritmagan — xonadagi nikini chatda so'rang.`;
  return `<div class="tb-efb-vs">${side(me[0], me[1])}<i>eFootball</i>${side(op[0], op[1])}</div>
    <div class="tb-hint tb-hint--center">${escHtml(warn)}</div>`;
}
Object.assign(TB_I18N.ru, {
  "Kiritilmagan": "Не указан",
  "Xonaga faqat shu nik kirishi kerak. Boshqa nik kirsa — o'ynamang va adminga xabar bering.": "В комнату должен зайти именно этот ник. Если зашёл другой — не играйте и сообщите админу.",
  "Raqib eFootball akkauntini kiritmagan — xonadagi nikini chatda so'rang.": "Соперник не указал аккаунт eFootball — спросите его ник в чате.",
});
Object.assign(TB_I18N.en, {
  "Kiritilmagan": "Not set",
  "Xonaga faqat shu nik kirishi kerak. Boshqa nik kirsa — o'ynamang va adminga xabar bering.": "Only this nickname should join the room. If someone else joins — don't play and tell the admin.",
  "Raqib eFootball akkauntini kiritmagan — xonadagi nikini chatda so'rang.": "Your opponent hasn't added an eFootball account — ask for their nickname in chat.",
});
