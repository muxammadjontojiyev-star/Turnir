// =============================================================
//  dom_morph.js — MILTILLASHSIZ QAYTA CHIZISH (2026-11-05, egasi: «pir-pirashlarni tuzating»)
//  domMorph(el, html) — el.innerHTML = html o'rniga: yangi HTML'ni eskisi bilan solishtiradi va faqat
//  O'ZGARGAN joyni yangilaydi. Natijada rasm qayta yuklanmaydi, animatsiya qayta o'ynamaydi, scroll va
//  yozilayotgan matn (input) joyida qoladi.
//  FAQAT hodisalari DELEGATSIYA bilan (document/root'da) ulangan joylarda ishlatiladi — elementga to'g'ridan
//  ulangan listener'lar qayta ulanib ketishi mumkin. Hozir: Do'kon (shop.js shopRender).
// =============================================================

function domMorph(el, html) {
  if (!el) return;
  const tpl = document.createElement("template");
  tpl.innerHTML = html;
  _dmChildren(el, tpl.content);
}

function _dmSame(a, b) {
  if (a.nodeType !== b.nodeType) return false;
  if (a.nodeType !== 1) return true;
  return a.tagName === b.tagName && (a.id || "") === (b.id || "");
}

function _dmChildren(from, to) {
  let f = from.firstChild;
  let t = to.firstChild;
  while (t) {
    const next = t.nextSibling;
    if (!f) {
      from.appendChild(t);
    } else if (_dmSame(f, t)) {
      _dmNode(f, t);
      f = f.nextSibling;
    } else {
      from.insertBefore(t, f);
    }
    t = next;
  }
  while (f) {
    const n = f.nextSibling;
    from.removeChild(f);
    f = n;
  }
}

function _dmNode(f, t) {
  if (f.nodeType !== 1) {
    if (f.nodeValue !== t.nodeValue) f.nodeValue = t.nodeValue;
    return;
  }
  // atributlar
  for (const a of Array.from(f.attributes)) if (!t.hasAttribute(a.name)) f.removeAttribute(a.name);
  for (const a of Array.from(t.attributes)) {
    if (f.getAttribute(a.name) === a.value) continue;
    f.setAttribute(a.name, a.value);
    // input: atribut o'zgarganda (yangi ma'lumot) qiymat ham yangilanadi; o'zgarmasa — foydalanuvchi yozgani qoladi
    if (a.name === "value" && "value" in f && f !== document.activeElement) f.value = a.value;
  }
  if (f.tagName === "INPUT" && (f.type === "checkbox" || f.type === "radio")) f.checked = t.hasAttribute("checked");
  if (f.tagName === "TEXTAREA") {
    if (f !== document.activeElement && f.value !== t.value) f.value = t.value;
    return;
  }
  _dmChildren(f, t);
}
