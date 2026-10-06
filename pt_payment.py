"""
pt_payment.py — SHAXSIY turnir to'lovi (2026-10-02, 2-bosqich).

Oqim (admin qarori: QO'LDA to'lov):
  awaiting_payment | rejected --(tashkilotchi chek yuklaydi)--> payment_review
  payment_review --(bosh admin tasdiqlaydi)--> recruiting
  payment_review --(bosh admin rad etadi, sabab bilan)--> rejected (chekni qayta yuborish mumkin)

Chek rasmi pt_receipts'da (alohida jadval). Uni faqat bosh admin ko'radi (qoida #34).
Status o'tishlari SHARTLI UPDATE bilan — ikki marta bosish ikki marta yozmaydi (qoida #38).
Rasm serverda ham tekshiriladi: hajm va fayl imzosi (qoida #41).
"""

import base64
import binascii
import logging

from models import get_connection
from pt_core import (
    STATUS_AWAITING_PAYMENT,
    STATUS_PAYMENT_REVIEW,
    STATUS_RECRUITING,
    STATUS_REJECTED,
)

logger = logging.getLogger(__name__)

RECEIPT_MAX_BYTES = 2_500_000      # ~2.5 MB (frontend 1600px JPEG ga siqadi)
REJECT_REASON_MAX = 200
_SUBMITTABLE = (STATUS_AWAITING_PAYMENT, STATUS_REJECTED)


def detect_image_mime(data: bytes) -> str | None:
    """Fayl imzosi bo'yicha (kengaytmaga ishonmaymiz): JPEG / PNG / WEBP, aks holda None."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def decode_receipt(image_base64: str) -> tuple[bytes | None, str]:
    """base64 (data: prefiksi bo'lishi mumkin) -> (baytlar, mime) yoki (None, sabab)."""
    raw = (image_base64 or "").strip()
    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    if not raw:
        return None, "empty_image"
    # base64 4/3 marta katta — dekodlashdan oldin taxminiy chegara (xotira himoyasi)
    if len(raw) > RECEIPT_MAX_BYTES * 4 // 3 + 16:
        return None, "image_too_large"
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        return None, "bad_image"
    if len(data) > RECEIPT_MAX_BYTES:
        return None, "image_too_large"
    mime = detect_image_mime(data)
    if mime is None:
        return None, "bad_image"
    return data, mime


def pt_submit_receipt(tournament_id: int, user_id: int, data: bytes,
                      mime: str) -> tuple[bool, str | dict]:
    """
    Faqat tashkilotchi, status awaiting_payment yoki rejected bo'lsa.
    Sabablar: not_found, not_owner, wrong_status.
    Qaytaradi (ok): {"id", "name", "price_uzs", "owner_nickname", "owner_username"} — admin xabari uchun.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT t.id, t.name, t.status, t.price_uzs, t.owner_user_id, "
            "u.nickname AS owner_nickname, u.username AS owner_username "
            "FROM pt_tournaments t JOIN users u ON u.id = t.owner_user_id WHERE t.id = ?",
            (tournament_id,),
        )
        t = cursor.fetchone()
        reason = None
        if not t:
            reason = "not_found"
        elif t["owner_user_id"] != user_id:
            reason = "not_owner"
        elif t["status"] not in _SUBMITTABLE:
            reason = "wrong_status"
        if reason:
            cursor.execute("ROLLBACK")
            return False, reason

        cursor.execute(
            "INSERT INTO pt_receipts (tournament_id, mime, data) VALUES (?, ?, ?) "
            "ON CONFLICT(tournament_id) DO UPDATE SET mime = excluded.mime, "
            "data = excluded.data, created_at = CURRENT_TIMESTAMP",
            (tournament_id, mime, data),
        )
        cursor.execute(
            "UPDATE pt_tournaments SET status = ?, receipt_at = CURRENT_TIMESTAMP, "
            "reject_reason = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (STATUS_PAYMENT_REVIEW, tournament_id),
        )
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_submit_receipt: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
    logger.info("PT #%s: chek yuborildi (%s bayt)", tournament_id, len(data))
    out = dict(t)
    out.pop("status", None)
    out.pop("owner_user_id", None)
    return True, out


def pt_list_payments() -> list[dict]:
    """Bosh admin: tekshiruvdagi to'lovlar (eng eskisi birinchi — navbat tartibi)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT t.id, t.name, t.price_uzs, t.receipt_at, t.created_at, "
            "u.nickname AS owner_nickname, u.username AS owner_username, "
            "t.owner_telegram_id "
            "FROM pt_tournaments t JOIN users u ON u.id = t.owner_user_id "
            "WHERE t.status = ? ORDER BY t.receipt_at, t.id",
            (STATUS_PAYMENT_REVIEW,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def pt_get_receipt(tournament_id: int) -> tuple[bytes, str] | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT mime, data FROM pt_receipts WHERE tournament_id = ?",
                       (tournament_id,))
        row = cursor.fetchone()
        return (bytes(row["data"]), row["mime"]) if row else None
    finally:
        conn.close()


def _review(tournament_id: int, admin_tg: int, new_status: str,
            reason: str | None) -> tuple[bool, str | dict]:
    """Umumiy: payment_review -> new_status (shartli UPDATE). Sabab: not_found, wrong_status."""
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        paid = ", paid_at = CURRENT_TIMESTAMP" if new_status == STATUS_RECRUITING else ""
        cursor.execute(
            f"UPDATE pt_tournaments SET status = ?, reviewed_by = ?, reject_reason = ?, "
            f"updated_at = CURRENT_TIMESTAMP{paid} WHERE id = ? AND status = ?",
            (new_status, admin_tg, reason, tournament_id, STATUS_PAYMENT_REVIEW),
        )
        if cursor.rowcount != 1:
            cursor.execute("SELECT 1 FROM pt_tournaments WHERE id = ?", (tournament_id,))
            exists = cursor.fetchone() is not None
            cursor.execute("ROLLBACK")
            return False, "wrong_status" if exists else "not_found"
        cursor.execute(
            "SELECT t.name, t.owner_telegram_id, u.language FROM pt_tournaments t "
            "JOIN users u ON u.id = t.owner_user_id WHERE t.id = ?", (tournament_id,))
        info = dict(cursor.fetchone())
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt payment _review: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
    logger.info("PT #%s: to'lov %s (admin %s)", tournament_id, new_status, admin_tg)
    return True, info


def pt_approve_payment(tournament_id: int, admin_tg: int) -> tuple[bool, str | dict]:
    return _review(tournament_id, admin_tg, STATUS_RECRUITING, None)


def clean_reject_reason(reason: str | None) -> str | None:
    """Bo'sh joylarni siqadi, 200 belgigacha qisqartiradi; bo'sh bo'lsa None."""
    return " ".join((reason or "").split())[:REJECT_REASON_MAX] or None


def pt_reject_payment(tournament_id: int, admin_tg: int,
                      reason: str | None) -> tuple[bool, str | dict]:
    return _review(tournament_id, admin_tg, STATUS_REJECTED, clean_reject_reason(reason))
