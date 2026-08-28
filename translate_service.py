"""
translate_service.py — chat xabarlarini tarjima qilish (2026-08-28).

Muammo (qoida #52): botdan chet ellik ishtirokchilar ham foydalanmoqda —
ingliz/rus va boshqa tillarda yozilgan chat xabarini raqib tushunmaydi.

Yechim: xabar matni tashqi tarjima xizmatiga yuboriladi va foydalanuvchining
ilova tiliga (uz/ru/en) o'giriladi.

MUHIM DIZAYN QARORI: bu modul MATN bilan ishlaydi, chat jadvallari bilan EMAS.
Shu sabab bitta endpoint BARCHA 5 chatga (liga, ChL, ChL play-off, Divizion,
WC) yetadi — messages/cl_messages/cl_po_messages/div_messages/wc_messages
jadvallariga tegilmaydi (qoida #26 DRY, qoida #02 boshqa joylarga tegmaslik).

KESH: bir xil matn + bir xil nishon til qayta so'ralmaydi — chat_translations
jadvali (models.py). Bu tashqi xizmatga so'rovni keskin kamaytiradi (bir xil
xabarni ikkala tomon ham bossa — bitta so'rov).

XIZMAT: TRANSLATE_URL (config.py, environment variable) — sukut bo'yicha
Google'ning kalitsiz endpointi. Boshqa xizmatga o'tilsa faqat _call_provider()
o'zgaradi, chat kodi va API shartnomasi o'zgarmaydi.
"""

import hashlib
import logging

import httpx

from config import (
    TRANSLATE_ENABLED,
    TRANSLATE_MAX_CHARS,
    TRANSLATE_TIMEOUT_SECONDS,
    TRANSLATE_URL,
)
from models import get_connection

logger = logging.getLogger(__name__)

# Ilova tillari (app.js setLanguage bilan bir xil) — faqat shularga o'giriladi
SUPPORTED_TARGET_LANGS = ("uz", "ru", "en")


def _cache_key(text: str, target_lang: str) -> str:
    """sha256(nishon_til + matn) — kesh kaliti. Uzun matn ham qisqa kalitga tushadi."""
    raw = f"{target_lang}\n{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _cache_get(key: str) -> dict | None:
    """Keshdan tarjimani o'qiydi. Topilmasa None."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT translated_text, detected_lang FROM chat_translations WHERE cache_key = ?",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {"translated": row["translated_text"], "detected_lang": row["detected_lang"]}
    except Exception:
        # Kesh ishlamasa tarjima baribir davom etadi (jim yutmaymiz — qoida #44)
        logger.exception("Tarjima keshini o'qishda xato")
        return None
    finally:
        conn.close()


def _cache_put(key: str, target_lang: str, translated: str, detected_lang: str | None) -> None:
    """Tarjimani keshga yozadi. Takror yozuv xato bermaydi (INSERT OR REPLACE)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO chat_translations "
            "(cache_key, target_lang, detected_lang, translated_text) VALUES (?, ?, ?, ?)",
            (key, target_lang, detected_lang, translated),
        )
        conn.commit()
    except Exception:
        logger.exception("Tarjima keshiga yozishda xato")
    finally:
        conn.close()


def _call_provider(text: str, target_lang: str) -> tuple[str, str | None]:
    """
    Tashqi tarjima xizmatiga so'rov (qoida #37: xatolikka tayyor).

    Qaytaradi: (tarjima_matni, aniqlangan_til)
    Xato bo'lsa Exception ko'taradi — chaqiruvchi ushlaydi.

    Javob formati (Google gtx): [[["tarjima","asl",...], ...], null, "en", ...]
    Uzun matn bir nechta bo'lakka bo'linadi — hammasi birlashtiriladi.
    """
    params = {
        "client": "gtx",
        "sl": "auto",          # manba til avtomatik aniqlanadi
        "tl": target_lang,
        "dt": "t",
        "q": text,
    }
    resp = httpx.get(TRANSLATE_URL, params=params, timeout=TRANSLATE_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()

    chunks = data[0] or []
    translated = "".join(part[0] for part in chunks if part and part[0])
    detected = data[2] if len(data) > 2 else None
    if not translated:
        raise ValueError("bo'sh tarjima")
    return translated, detected


def translate_text(text: str, target_lang: str) -> tuple[bool, str, dict]:
    """
    Matnni target_lang tiliga o'giradi.

    Qaytaradi: (ok, reason, info)
      reason: ok | disabled | invalid_target | empty_text | text_too_long |
              provider_error
      info (ok bo'lsa): {
        translated:     tarjima matni,
        detected_lang:  aniqlangan manba til (yoki None),
        cached:         keshdan olindimi (True/False),
        same_language:  manba til nishon til bilan bir xilmi
      }

    same_language=True bo'lsa frontend "bu xabar allaqachon sizning tilingizda"
    deb ko'rsatishi mumkin (qoida #40: jim qolmaslik).
    """
    if not TRANSLATE_ENABLED:
        return False, "disabled", {}

    target = (target_lang or "").strip().lower()
    if target not in SUPPORTED_TARGET_LANGS:
        return False, "invalid_target", {}

    src = (text or "").strip()
    if not src:
        return False, "empty_text", {}
    if len(src) > TRANSLATE_MAX_CHARS:
        return False, "text_too_long", {}

    key = _cache_key(src, target)
    cached = _cache_get(key)
    if cached is not None:
        return True, "ok", {
            "translated": cached["translated"],
            "detected_lang": cached["detected_lang"],
            "cached": True,
            "same_language": cached["detected_lang"] == target,
        }

    try:
        translated, detected = _call_provider(src, target)
    except Exception:
        logger.exception("Tarjima xizmati xatosi (target=%s, uzunlik=%s)", target, len(src))
        return False, "provider_error", {}

    _cache_put(key, target, translated, detected)
    return True, "ok", {
        "translated": translated,
        "detected_lang": detected,
        "cached": False,
        "same_language": detected == target,
    }
