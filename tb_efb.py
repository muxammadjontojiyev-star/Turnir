"""
tb_efb.py — "TEAMLAR JANGI": eFootball akkauntini Telegram akkauntiga bog'lash (2026-10-25).

Maqsad: o'yinchi o'rniga boshqa odam o'ynashini kamaytirish. Har ishtirokchi eFootball
User ID va o'yindagi nikini kiritadi; VS-oynada raqib nikini ko'radi (xonaga boshqa nik
kirsa — darhol bilinadi).

Qoidalar (egasi qarori):
  - bitta eFootball ID — faqat bitta Telegram akkauntga (UNIQUE);
  - foydalanuvchi ID ni FAQAT BIR MARTA o'zi kiritadi; keyin almashtirish — faqat liga admini
    yoki bosh admin (tb_efb_admin_set / tb_efb_admin_clear);
  - har o'zgarish tb_efb_history ga yoziladi (kim, qachon, eski -> yangi);
  - bog'lash team a'zoligiga emas, FOYDALANUVCHIGA tegishli: teamdan chiqib boshqasiga
    o'tsa ham saqlanadi;
  - yangi qo'shilish / team ochish uchun majburiy (tb_core.tb_join, tb_create_team);
    eski a'zolarga faqat ogohlantirish (o'yinlar bloklanmaydi).
Sabab kodlari frontend'da matnga aylanadi (tb_efb.js -> TB_ERR).
"""

import logging
import re

from models import get_connection

logger = logging.getLogger(__name__)

TB_EFB_ID_MIN = 6
TB_EFB_ID_MAX = 24
TB_EFB_NAME_MIN = 2
TB_EFB_NAME_MAX = 24

_ID_RE = re.compile(r"^[A-Z0-9-]+$")
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f<>]")


def init_tb_efb_tables(cursor) -> None:
    """tb_models.init_tb_tables ichidan chaqiriladi (CREATE IF NOT EXISTS — idempotent, qoida #31)."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tb_efb_accounts (
            user_id INTEGER PRIMARY KEY,
            efb_id TEXT NOT NULL COLLATE NOCASE UNIQUE,
            efb_name TEXT NOT NULL,
            updated_by INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tb_efb_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            old_id TEXT, old_name TEXT,
            new_id TEXT, new_name TEXT,
            changed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_efb_hist_user ON tb_efb_history(user_id)")


def tb_efb_clean(efb_id, efb_name) -> tuple[tuple[str, str] | None, str]:
    """ID: probel/tire atrofi tozalanadi, katta harf; nik: ortiqcha probellar, boshqaruv belgilarisiz."""
    i = re.sub(r"\s+", "", str(efb_id or "")).upper()
    if not (TB_EFB_ID_MIN <= len(i) <= TB_EFB_ID_MAX) or not _ID_RE.match(i):
        return None, "efb_bad_id"
    n = " ".join(str(efb_name or "").split())
    if not (TB_EFB_NAME_MIN <= len(n) <= TB_EFB_NAME_MAX) or _CTRL_RE.search(n):
        return None, "efb_bad_name"
    return (i, n), "ok"


def tb_efb_of(cursor, user_id: int) -> dict | None:
    r = cursor.execute("SELECT efb_id, efb_name, updated_at FROM tb_efb_accounts WHERE user_id = ?",
                       (user_id,)).fetchone()
    return dict(r) if r else None


def tb_efb_has(cursor, user_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM tb_efb_accounts WHERE user_id = ?", (user_id,)).fetchone() is not None


def tb_efb_get(user_id: int) -> dict | None:
    conn = get_connection()
    try:
        return tb_efb_of(conn.cursor(), user_id)
    finally:
        conn.close()


def _write(user_id: int, efb_id, efb_name, by_user_id: int, allow_replace: bool) -> tuple[bool, str | dict]:
    clean, why = tb_efb_clean(efb_id, efb_name)
    if not clean:
        return False, why
    new_id, new_name = clean
    conn = get_connection()
    conn.isolation_level = None
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")                     # qoida #38: ikki marta bosish — bitta yozuv
    try:
        old = tb_efb_of(cur, user_id)
        if old and not allow_replace:
            cur.execute("ROLLBACK")
            return False, "efb_locked"
        owner = cur.execute("SELECT user_id FROM tb_efb_accounts WHERE efb_id = ? COLLATE NOCASE",
                            (new_id,)).fetchone()
        if owner and owner["user_id"] != user_id:
            cur.execute("ROLLBACK")
            return False, "efb_id_taken"
        if old and old["efb_id"] == new_id and old["efb_name"] == new_name:
            cur.execute("ROLLBACK")
            return True, {"efb_id": new_id, "efb_name": new_name, "changed": False}
        cur.execute(
            "INSERT INTO tb_efb_accounts (user_id, efb_id, efb_name, updated_by) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET efb_id = excluded.efb_id, efb_name = excluded.efb_name, "
            "updated_by = excluded.updated_by, updated_at = CURRENT_TIMESTAMP",
            (user_id, new_id, new_name, by_user_id))
        cur.execute("INSERT INTO tb_efb_history (user_id, old_id, old_name, new_id, new_name, changed_by) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, old and old["efb_id"], old and old["efb_name"], new_id, new_name, by_user_id))
        cur.execute("COMMIT")
        logger.info("TB eFB: user=%s %s -> %s (by=%s)", user_id, old and old["efb_id"], new_id, by_user_id)
        return True, {"efb_id": new_id, "efb_name": new_name, "changed": True}
    except Exception:
        cur.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def tb_efb_set_self(user_id: int, efb_id, efb_name) -> tuple[bool, str | dict]:
    """Foydalanuvchi o'zi — faqat birinchi marta. Sabablar: efb_bad_id, efb_bad_name, efb_locked, efb_id_taken."""
    return _write(user_id, efb_id, efb_name, user_id, allow_replace=False)


def tb_efb_admin_set(target_user_id: int, efb_id, efb_name, admin_user_id: int) -> tuple[bool, str | dict]:
    """Liga admini / bosh admin — almashtirish (ruxsat tb_api_efb.py da tekshiriladi)."""
    return _write(target_user_id, efb_id, efb_name, admin_user_id, allow_replace=True)


def tb_efb_admin_clear(target_user_id: int, admin_user_id: int) -> tuple[bool, str | dict]:
    """Bog'lashni o'chirish (foydalanuvchi qayta o'zi kiritadi). Sabab: efb_not_set."""
    conn = get_connection()
    conn.isolation_level = None
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    try:
        old = tb_efb_of(cur, target_user_id)
        if not old:
            cur.execute("ROLLBACK")
            return False, "efb_not_set"
        cur.execute("DELETE FROM tb_efb_accounts WHERE user_id = ?", (target_user_id,))
        cur.execute("INSERT INTO tb_efb_history (user_id, old_id, old_name, changed_by) VALUES (?, ?, ?, ?)",
                    (target_user_id, old["efb_id"], old["efb_name"], admin_user_id))
        cur.execute("COMMIT")
        logger.info("TB eFB: user=%s bog'lash o'chirildi (by=%s)", target_user_id, admin_user_id)
        return True, {}
    except Exception:
        cur.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def tb_efb_history(user_id: int, limit: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT h.old_id, h.old_name, h.new_id, h.new_name, h.created_at, "
                    "u.username AS by_username, u.nickname AS by_nickname "
                    "FROM tb_efb_history h LEFT JOIN users u ON u.id = h.changed_by "
                    "WHERE h.user_id = ? ORDER BY h.id DESC LIMIT ?", (user_id, limit))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
