"""
pt_rules.py — SHAXSIY turnir qoidalari (2026-10-07).

Muammo (qoida #52): ishtirokchilar turnir qanday o'tishini (ochko, muddat, natija
kiritish, pley-off) bilmay qoladi; har bir guruhning o'z kelishuvlari ham bor.
Yechim: Asosiy sahifada qoidalar bloki. Matnni FAQAT tashkilotchi (turnir egasi)
o'zgartiradi — adminlar ham emas (admin so'rovi). Bo'sh matn — standart qoidalar
(frontendda tarjima qilinadi, bazada NULL).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

PT_RULES_MAX = 2000             # belgilar (qoida #17)
PT_RULES_MAX_LINES = 40         # qator — sahifa cheksiz cho'zilmasin


def clean_rules(text) -> str:
    """Bo'shliqlarni tozalaydi, qatorlar sonini cheklaydi. Uzunlik tekshiruvi — chaqiruvchida."""
    lines = [ln.rstrip() for ln in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    out, blank = [], 0
    for ln in lines:                         # ketma-ket bo'sh qatorlar bittaga
        blank = blank + 1 if not ln.strip() else 0
        if blank <= 1:
            out.append(ln)
    return "\n".join(out[:PT_RULES_MAX_LINES]).strip()


def pt_set_rules(tid: int, owner_id: int, text) -> tuple[bool, str]:
    """
    Qoidalarni saqlash (faqat tashkilotchi — server tekshiradi, qoida #41).
    Bo'sh matn — standart qoidalarga qaytish (NULL).
    Sabablar: too_long, not_found, not_owner, wrong_status.
    """
    rules = clean_rules(text)
    if len(rules) > PT_RULES_MAX:
        return False, "too_long"
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT owner_user_id, status FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        if not t:
            return False, "not_found"
        if t["owner_user_id"] != owner_id:
            return False, "not_owner"
        if t["status"] == "cancelled":
            return False, "wrong_status"
        cursor.execute("UPDATE pt_tournaments SET rules = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                       (rules or None, tid))
        conn.commit()
        return True, "ok"
    finally:
        conn.close()
