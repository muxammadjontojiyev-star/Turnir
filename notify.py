"""
notify.py — Foydalanuvchilarga bot orqali inline (push) xabar yuborish.

API thread'idan ishlatiladi: botning polling jarayoniga tegmasdan, to'g'ridan-to'g'ri
Telegram Bot API `sendMessage`ni httpx orqali chaqiradi. Har bir foydalanuvchiga
o'zining DB'dagi tilida (users.language) yuboriladi.

Xato bo'lsa (foydalanuvchi botni bloklagan, chat topilmadi va h.k.) — jim o'tadi,
chunki bitta foydalanuvchiga yuborilmasligi qolganlarini to'xtatmasligi kerak.
"""

import logging

import httpx

from config import BOT_TOKEN, DEFAULT_LANGUAGE, WEBAPP_URL
from texts import t

logger = logging.getLogger(__name__)

_API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def _send_message(chat_id: int, text: str,
                        open_button: str | None = None) -> bool:
    """
    Bitta foydalanuvchiga matnli xabar yuboradi.

    open_button: berilsa, xabar ostida shu matnli WebApp tugmasi chiqadi
      (bosilsa ilova darhol ochiladi — chat xabarlariga tez javob berish uchun).

    Qaytaradi: True (muvaffaqiyat) yoki False (xato — jim yutiladi).
    """
    if not BOT_TOKEN:
        return False
    payload = {"chat_id": chat_id, "text": text}
    if open_button:
        # WebApp tugmasi faqat HTTPS URL bilan ishlaydi (Telegram talabi)
        if WEBAPP_URL.startswith("https://"):
            payload["reply_markup"] = {
                "inline_keyboard": [[
                    {"text": open_button, "web_app": {"url": WEBAPP_URL}}
                ]]
            }
        else:
            payload["reply_markup"] = {
                "inline_keyboard": [[{"text": open_button, "url": WEBAPP_URL}]]
            }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(f"{_API_BASE}/sendMessage", json=payload)
            return r.status_code == 200
    except Exception as exc:
        logger.warning("Bildirishnoma yuborilmadi (chat_id=%s): %s", chat_id, exc)
        return False


async def notify_user(telegram_id: int, text_key: str, language: str,
                      open_button_key: str | None = None, **fmt) -> bool:
    """
    Bitta foydalanuvchiga uning tilida (texts.py'dagi text_key bo'yicha) xabar yuboradi.

    fmt: matndagi {placeholder}'lar uchun qiymatlar (masalan league="LaLiga").
    open_button_key: texts.py'dagi kalit — berilsa xabar ostida ilovani ochish
      tugmasi chiqadi (masalan "btn_open_app" — chat xabarlariga tez javob uchun).
    """
    lang = language or DEFAULT_LANGUAGE
    message = t(text_key, lang)
    if fmt:
        try:
            message = message.format(**fmt)
        except (KeyError, IndexError, ValueError) as exc:
            # Placeholder mos kelmasa — xom matn yuboriladi, lekin log qoldiramiz (qoida #44)
            logger.warning("Bildirishnoma format xatosi (%s): %s", text_key, exc)
    button = t(open_button_key, lang) if open_button_key else None
    return await _send_message(telegram_id, message, open_button=button)


async def notify_members(members: list[dict], text_key: str, **fmt) -> int:
    """
    Bir nechta foydalanuvchiga (har biriga o'z tilida) bir xil text_key bo'yicha
    xabar yuboradi. members: [{telegram_id, language}, ...].

    Qaytaradi: muvaffaqiyatli yuborilgan xabarlar soni.
    """
    sent = 0
    for m in members:
        ok = await notify_user(m["telegram_id"], text_key, m.get("language"), **fmt)
        if ok:
            sent += 1
    return sent
