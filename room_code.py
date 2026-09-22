"""
room_code.py — eFootball xona ID sini raqibga yuborish (2026-08-28).
2026-09-22: barcha rejimlarga kengaytirildi (liga, ChL, ChL play-off,
Divizion, JCh guruh, JCh play-off). Jadval xaritasi chat_report.MODES dan
olinadi — ikkinchi nusxa saqlanmaydi (qoida #26 DRY). Ishtirokchi tekshiruvi
hamma rejimda bir xil: "player1_id / player2_id ichida bormi".

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
from chat_report import MODES

logger = logging.getLogger(__name__)

# eFootball xona ID formati aniq belgilanmagan (raqam yoki harf-raqam bo'lishi
# mumkin), shuning uchun tekshiruv ATAYLAB keng: faqat bo'shliq/belgilar
# tozalanadi va uzunlik chegaralanadi. Juda qattiq validatsiya haqiqiy kodni
# rad etib, funksiyani ishlatib bo'lmas qilib qo'yardi.
ROOM_CODE_MIN_LEN = 4
ROOM_CODE_MAX_LEN = 16
_ROOM_CODE_CLEAN_RE = re.compile(r"[^A-Za-z0-9]")

# Chat xabari shakli — chatda va nizo hisobotida shu ko'rinishda chiqadi
ROOM_CODE_PREFIX = "🎮 Xona ID:"

# Bildirishnomada ko'rinadigan rejim nomi (texts.py kalitlari)
MODE_NAME_KEYS = {
    "league": "mode_name_league",
    "cl": "mode_name_cl",
    "cl_po": "mode_name_cl",
    "div": "mode_name_division",
    "wc": "mode_name_worldcup",
    "wc_po": "mode_name_worldcup",
}


def normalize_room_code(raw: str) -> str | None:
    """Kodni tozalaydi (bo'shliq, tire va h.k. olib tashlanadi). Yaroqsiz bo'lsa None."""
    cleaned = _ROOM_CODE_CLEAN_RE.sub("", raw or "")
    if not (ROOM_CODE_MIN_LEN <= len(cleaned) <= ROOM_CODE_MAX_LEN):
        return None
    return cleaned


def send_room_code(match_id: int, sender_user_id: int, raw_code: str,
                   mode: str = "league"):
    """
    Xona ID sini chat xabari sifatida yozadi va raqibning telegram_id sini qaytaradi.

    sender_user_id — users.id (telegram_id EMAS). Chaqiruvchi endpoint uni
    allaqachon aniqlagan bo'ladi.

    Qaytaradi: (ok, reason, info)
      reason: ok | invalid_code | bad_mode | match_not_found | not_participant |
              send_failed
      info (ok bo'lsa): {"code", "recipient_telegram_id", "mode"}

    Bildirishnoma HAR DOIM qaytariladi (throttle yo'q) — modul izohiga qarang.
    """
    code = normalize_room_code(raw_code)
    if code is None:
        return False, "invalid_code", {}

    cfg = MODES.get(mode)
    if cfg is None:
        logger.warning("Xona ID: noma'lum rejim %r", mode)
        return False, "bad_mode", {}

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Ishtirokchi tekshiruvi — hamma rejimda bir xil (qoida #34).
        # Jadval nomi MODES'dan (KODDAN) keladi, foydalanuvchidan emas —
        # SQL injection xavfi yo'q, qiymatlar parametrlashtirilgan (qoida #29).
        cursor.execute(
            f"SELECT player1_id, player2_id FROM {cfg['match_table']} WHERE id = ?",
            (match_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return False, "match_not_found", {}
        p1, p2 = row["player1_id"], row["player2_id"]
        if not p1 or not p2:
            return False, "match_not_found", {}   # juftlik hali to'lmagan
        if sender_user_id not in (p1, p2):
            return False, "not_participant", {}

        opponent_id = p2 if sender_user_id == p1 else p1
        text = f"{ROOM_CODE_PREFIX} {code}"

        # wc_messages guruh va play-off xabarlarini BIR jadvalda saqlaydi
        if cfg["playoff"] is not None:
            cursor.execute(
                f"INSERT INTO {cfg['msg_table']} (match_id, sender_id, text, is_playoff) "
                f"VALUES (?, ?, ?, ?)",
                (match_id, sender_user_id, text, cfg["playoff"]),
            )
        else:
            cursor.execute(
                f"INSERT INTO {cfg['msg_table']} (match_id, sender_id, text) "
                f"VALUES (?, ?, ?)",
                (match_id, sender_user_id, text),
            )

        cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (opponent_id,))
        opp = cursor.fetchone()
        conn.commit()
    except Exception:
        logger.exception("Xona ID yozishda xato (rejim %s, match %s)", mode, match_id)
        return False, "send_failed", {}
    finally:
        conn.close()

    if opp is None:
        # Xabar yozildi, lekin raqib topilmadi — bildirishnomasiz ham chatda turadi
        logger.warning("Xona ID: raqib topilmadi (rejim %s, match %s)", mode, match_id)
        return True, "ok", {"code": code, "recipient_telegram_id": None, "mode": mode}

    return True, "ok", {
        "code": code,
        "recipient_telegram_id": dict(opp)["telegram_id"],
        "mode": mode,
    }
