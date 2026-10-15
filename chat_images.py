"""
chat_images.py — bot chatida (WebApp ichki chati) rasm yuborish (2026-10-11).

Admin so'rovi: barcha rejimlarda (liga, ChL, YeL, Divizion, JCh, shaxsiy
turnir) bot chati orqali rasm ham yuborilsin — masalan, natija skrinshoti.

DIZAYN (qoida #19, room_code.py naqshi):
  * Rasm baytlari ALOHIDA `chat_images` jadvalida (xabarlar so'rovi og'ir
    bo'lmasin, qoida #32). Chatga oddiy xabar yoziladi:
        "📷 [img:<token>]"
    Shu tufayli o'qilganlik (✓✓), o'qilmaganlar rozetkasi, nizo hisoboti va
    har rejimning chat ruxsat mantig'i QAYTA YOZILMAYDI (qoida #26).
  * Jadval xaritasi chat_report.MODES dan olinadi (ikkinchi nusxa yo'q).
  * Rasm ochiq havola emas: GET faqat o'yin ishtirokchisiga yoki shu rejim
    adminiga (qoida #34). token — 128-bit tasodifiy (taxmin qilib bo'lmaydi).
  * Hajm/format tekshiruvi pt_payment.decode_receipt bilan bir xil
    (JPEG/PNG/WEBP imzosi, ≤ 2.5 MB) — qoida #26, #41.
  * Spamdan himoya: bitta o'yinda bitta ishtirokchi ko'pi bilan
    CHAT_IMAGE_MAX_PER_MATCH ta rasm (qoida #39).
"""

import logging
import re
import secrets

from admin_roles import (SCOPE_AC, SCOPE_CL, SCOPE_DIVISION, SCOPE_EL, SCOPE_LEAGUE,
                         SCOPE_WC, is_scope_admin, is_super_admin)
from chat_report import MODES
from models import get_connection
from pt_payment import decode_receipt

logger = logging.getLogger(__name__)

CHAT_IMAGE_MAX_PER_MATCH = 30          # bitta o'yinda bitta ishtirokchidan (qoida #39)
CHAT_IMAGE_TOKEN_BYTES = 16            # 16 bayt → 32 hex belgi
CHAT_IMAGE_PREFIX = "📷"
CHAT_IMAGE_TEXT_FMT = CHAT_IMAGE_PREFIX + " [img:{token}]"
_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")

# Rasmni kim ko'ra oladi (ishtirokchidan tashqari): shu rejim admini.
# Shaxsiy turnir uchun scope yo'q — faqat bosh admin (None).
_MODE_SCOPES = {
    "league": SCOPE_LEAGUE,
    "cl": SCOPE_CL, "cl_po": SCOPE_CL,
    "div": SCOPE_DIVISION,
    "wc": SCOPE_WC, "wc_po": SCOPE_WC,
    "el": SCOPE_EL, "el_po": SCOPE_EL,
    "ac": SCOPE_AC, "ac_po": SCOPE_AC,   # 2026-10-15
    "pt": None,
    "tb": None,    # 2026-10-16: Teamlar jangi — ishtirokchilar + bosh admin
}


def _players(cursor, cfg: dict, match_id: int) -> tuple | None:
    # Jadval nomi KODDAN (MODES) keladi — foydalanuvchidan emas (qoida #29)
    cursor.execute(
        f"SELECT player1_id, player2_id FROM {cfg['match_table']} WHERE id = ?",
        (match_id,),
    )
    row = cursor.fetchone()
    if row is None or not row["player1_id"] or not row["player2_id"]:
        return None
    return row["player1_id"], row["player2_id"]


def send_chat_image(match_id: int, sender_user_id: int, image_base64: str,
                    mode: str = "league"):
    """
    Rasmni saqlaydi va chatga "📷 [img:token]" xabarini yozadi.

    Qaytaradi: (ok, reason, info)
      reason: ok | bad_mode | empty_image | image_too_large | bad_image |
              match_not_found | not_participant | too_many_images | send_failed
      info (ok): {"token", "recipient_telegram_id", "mode", "data", "mime"}
    """
    cfg = MODES.get(mode)
    if cfg is None:
        return False, "bad_mode", {}
    data, mime_or_reason = decode_receipt(image_base64)
    if data is None:
        return False, mime_or_reason, {}

    conn = get_connection()
    cursor = conn.cursor()
    try:
        players = _players(cursor, cfg, match_id)
        if players is None:
            return False, "match_not_found", {}
        if sender_user_id not in players:
            return False, "not_participant", {}

        cursor.execute(
            "SELECT COUNT(*) AS n FROM chat_images WHERE mode = ? AND match_id = ? AND sender_id = ?",
            (mode, match_id, sender_user_id),
        )
        if cursor.fetchone()["n"] >= CHAT_IMAGE_MAX_PER_MATCH:
            return False, "too_many_images", {}

        token = secrets.token_hex(CHAT_IMAGE_TOKEN_BYTES)
        cursor.execute(
            "INSERT INTO chat_images (token, mode, match_id, sender_id, mime, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (token, mode, match_id, sender_user_id, mime_or_reason, data),
        )
        text = CHAT_IMAGE_TEXT_FMT.format(token=token)
        # wc_messages guruh va play-off xabarlarini BIR jadvalda saqlaydi
        if cfg["playoff"] is not None:
            cursor.execute(
                f"INSERT INTO {cfg['msg_table']} (match_id, sender_id, text, is_playoff) "
                f"VALUES (?, ?, ?, ?)",
                (match_id, sender_user_id, text, cfg["playoff"]),
            )
        else:
            cursor.execute(
                f"INSERT INTO {cfg['msg_table']} (match_id, sender_id, text) VALUES (?, ?, ?)",
                (match_id, sender_user_id, text),
            )
        opponent_id = players[1] if sender_user_id == players[0] else players[0]
        cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (opponent_id,))
        opp = cursor.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Chat rasmi yozilmadi (rejim %s, match %s)", mode, match_id)
        return False, "send_failed", {}
    finally:
        conn.close()

    return True, "ok", {
        "token": token,
        "recipient_telegram_id": opp["telegram_id"] if opp else None,
        "mode": mode,
        "data": data,                 # bildirishnomada rasmning o'zi yuboriladi
        "mime": mime_or_reason,
    }


def get_chat_image(token: str, user_id: int, telegram_id: int):
    """
    Rasm baytlari: (data, mime) yoki None (topilmadi / ruxsat yo'q — farqi
    oshkor qilinmaydi). Ruxsat: o'yin ishtirokchisi yoki shu rejim admini.
    """
    if not _TOKEN_RE.match(token or ""):
        return None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT mode, match_id, mime, data FROM chat_images WHERE token = ?", (token,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        cfg = MODES.get(row["mode"])
        players = _players(cursor, cfg, row["match_id"]) if cfg else None
        allowed = bool(players) and user_id in players
        if not allowed:
            scope = _MODE_SCOPES.get(row["mode"])
            allowed = is_scope_admin(telegram_id, scope) if scope else is_super_admin(telegram_id)
        if not allowed:
            return None
        return bytes(row["data"]), row["mime"]
    finally:
        conn.close()
