"""
robi_usage.py — «ROBI» OVOZI: BEPUL LIMIT HISOBI (2026-11-03).

Azure F0 (bepul) tarifidan chiqmaslik uchun sarf bazada yuritiladi (qoida #38 — bir tranzaksiyada):
  * oylik umumiy: TTS belgilar soni, STT soniyalar (config.ROBI_TTS_MONTHLY_CHARS / ROBI_STT_MONTHLY_SEC —
    bepul limitdan zaxira bilan kam);
  * kunlik har foydalanuvchi: yangi ovozlashtirishlar va ovozli savollar soni (suiiste'moldan himoya).
Keshdagi (avval yaratilgan) ovoz hisobga KIRMAYDI. Xizmat xato qaytarsa — band qilingan sarf qaytariladi.
Davr — UTC kalendar oyi / kuni.
"""

import logging
from datetime import datetime, timezone

from models import get_connection

logger = logging.getLogger(__name__)

KIND_TTS, KIND_STT = "tts", "stt"
_ALL = 0          # who = 0 — oylik umumiy yozuv


def init_robi_tables(cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS robi_usage (
            period TEXT NOT NULL,
            kind TEXT NOT NULL,
            who INTEGER NOT NULL DEFAULT 0,
            amount INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (period, kind, who)
        )
    """)


def _periods() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m"), now.strftime("%Y-%m-%d")


def _get(cur, period: str, kind: str, who: int) -> int:
    r = cur.execute("SELECT amount FROM robi_usage WHERE period = ? AND kind = ? AND who = ?",
                    (period, kind, who)).fetchone()
    return r["amount"] if r else 0


def _add(cur, period: str, kind: str, who: int, amount: int) -> None:
    cur.execute("INSERT INTO robi_usage (period, kind, who, amount) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(period, kind, who) DO UPDATE SET amount = MAX(0, amount + excluded.amount)",
                (period, kind, who, amount))


def reserve(kind: str, telegram_id: int, amount: int, month_cap: int, user_daily_cap: int) -> tuple[bool, str]:
    """Sarfni oldindan band qiladi. Qaytaradi: (True, 'ok') | (False, 'quota_month' | 'quota_user')."""
    month, day = _periods()
    conn = get_connection()
    conn.isolation_level = None
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        if month_cap and _get(cur, month, kind, _ALL) + amount > month_cap:
            cur.execute("ROLLBACK")
            return False, "quota_month"
        if user_daily_cap and _get(cur, day, kind, telegram_id) + 1 > user_daily_cap:
            cur.execute("ROLLBACK")
            return False, "quota_user"
        _add(cur, month, kind, _ALL, amount)
        _add(cur, day, kind, telegram_id, 1)
        cur.execute("COMMIT")
        return True, "ok"
    except Exception:
        try:
            cur.execute("ROLLBACK")
        except Exception:
            pass
        logger.exception("Robi: limit hisobida xato (%s)", kind)
        return False, "quota_month"          # xato bo'lsa — xavfsiz tomonga: xizmat chaqirilmaydi
    finally:
        conn.close()


def release(kind: str, telegram_id: int, amount: int) -> None:
    """Xizmat xato qaytarganda band qilingan sarfni qaytaradi."""
    month, day = _periods()
    conn = get_connection()
    try:
        cur = conn.cursor()
        _add(cur, month, kind, _ALL, -amount)
        _add(cur, day, kind, telegram_id, -1)
        conn.commit()
    except Exception:
        logger.exception("Robi: sarfni qaytarishda xato (%s)", kind)
    finally:
        conn.close()


def month_usage() -> dict:
    """Bosh admin / log uchun: joriy oy sarfi {tts: belgi, stt: soniya}."""
    month, _ = _periods()
    conn = get_connection()
    try:
        cur = conn.cursor()
        return {"month": month, KIND_TTS: _get(cur, month, KIND_TTS, _ALL), KIND_STT: _get(cur, month, KIND_STT, _ALL)}
    finally:
        conn.close()
