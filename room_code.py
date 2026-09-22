"""
room_code.py — eFootball xona ID sini raqibga yuborish (2026-08-28).

Muammo (qoida #52): kelishuv bot chatida bo'lishi kerak (yozishmalar serverda
saqlanadi — dalil), lekin "ilovani och → o'yinni top → chatni och → yoz" yo'li
Telegramga yozishdan uzun. Natijada ishtirokchilar Telegramda gaplashishda
davom etadi va nizolarda dalil qolmaydi.

Yechim: o'yin kartasida ALOHIDA tugma — xona ID kiritiladi va bitta bosishda
raqibga yetadi. Raqib esa Telegramdan kodni TO'G'RIDAN-TO'G'RI ko'radi,
ilovani ochishi shart emas.

DIZAYN QARORI (qoida #19): kod ALOHIDA jadvalga emas, oddiy chat xabari
sifatida `messages` ga yoziladi. Sabab:
  1. dalil izi bir joyda qoladi (kim, qachon yuborgan) — asosiy maqsad shu;
  2. chat access/ruxsat mantig'i qayta yozilmaydi (qoida #26 DRY);
  3. o'qilganlik (is_read) avtomatik ishlaydi — "raqib kodni ko'rdimi?"
     degan savolga javob beradi.

MUHIM FARQ: oddiy chat xabarida bot bildirishnomasi anti-spam bilan
cheklanadi (CHAT_NOTIFY_THROTTLE_SECONDS) — ya'ni yaqinda yozishgan bo'lsa
bildirishnoma YUBORILMAYDI. Xona ID uchun bu yaramaydi: kod vaqtga bog'liq,
raqib uni DARHOL olishi shart. Shuning uchun bu yerda throttle QO'LLANILMAYDI.
"""

import logging
import re

from models import get_connection
from queries_chat import _chat_match_access

logger = logging.getLogger(__name__)

# eFootball xona ID formati aniq belgilanmagan (raqam yoki harf-raqam bo'lishi
# mumkin), shuning uchun tekshiruv ATAYLAB keng: faqat bo'shliq/belgilar
# tozalanadi va uzunlik chegaralanadi. Juda qattiq validatsiya haqiqiy kodni
# rad etib, funksiyani ishlatib bo'lmas qilib qo'yardi.
ROOM_CODE_MIN_LEN = 4
ROOM_CODE_MAX_LEN = 16
_ROOM_CODE_CLEAN_RE = re.compile(r"[^A-Za-z0-9]")

# Chat xabari shakli — frontend shu prefiks bo'yicha xabarni ajratib
# ko'rsatishi mumkin (hozircha oddiy matn sifatida ko'rinadi).
ROOM_CODE_PREFIX = "🎮 Xona ID:"


def normalize_room_code(raw: str) -> str | None:
    """Kodni tozalaydi (bo'shliq, tire va h.k. olib tashlanadi). Yaroqsiz bo'lsa None."""
    cleaned = _ROOM_CODE_CLEAN_RE.sub("", raw or "")
    if not (ROOM_CODE_MIN_LEN <= len(cleaned) <= ROOM_CODE_MAX_LEN):
        return None
    return cleaned


def send_room_code(match_id: int, sender_telegram_id: int, raw_code: str):
    """
    Xona ID sini chat xabari sifatida yozadi va raqibga bildirishnoma qaytaradi.

    Qaytaradi: (ok, reason, info)
      reason: ok | invalid_code | no_access | send_failed
      info (ok bo'lsa): {
        "code": tozalangan kod,
        "recipient_telegram_id": raqibning telegram_id si
      }

    Bildirishnoma HAR DOIM qaytariladi (throttle yo'q) — modul izohiga qarang.
    """
    code = normalize_room_code(raw_code)
    if code is None:
        return False, "invalid_code", {}

    access = _chat_match_access(match_id, sender_telegram_id)
    if access is None:
        return False, "no_access", {}

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO messages (match_id, sender_id, text) VALUES (?, ?, ?)",
            (match_id, access["my_user_id"], f"{ROOM_CODE_PREFIX} {code}"),
        )
        cursor.execute(
            "SELECT telegram_id FROM users WHERE id = ?", (access["opponent_user_id"],))
        opp = cursor.fetchone()
        conn.commit()
    except Exception:
        logger.exception("Xona ID yozishda xato (match %s)", match_id)
        return False, "send_failed", {}
    finally:
        conn.close()

    if opp is None:
        # Xabar yozildi, lekin raqib topilmadi — bildirishnomasiz ham chat'da turadi
        logger.warning("Xona ID: raqib topilmadi (match %s)", match_id)
        return True, "ok", {"code": code, "recipient_telegram_id": None}

    return True, "ok", {
        "code": code,
        "recipient_telegram_id": dict(opp)["telegram_id"],
    }
