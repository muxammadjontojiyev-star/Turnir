"""
ef_nick_link.py — BITTA eFOOTBALL AKKAUNT → 2 TA TELEGRAM AKKAUNT (2026-11-06, egasi: A varianti).

Ba'zi ishtirokchilar 2 ta Telegram akkaunt bilan 2 ta klubda o'ynaydi, eFootball akkaunti esa bitta.
  * Ikkinchi akkaunt band niknameni kiritsa — nikname EGASIGA (birinchi akkaunt) so'rov boradi
    («Bu sizning ikkinchi akkauntingizmi?»). Faqat egasi tasdiqlasa ulanadi — begona egallay olmaydi.
  * Bitta niknamega ko'pi bilan LINK_MAX ta qo'shimcha akkaunt.
  * FAQAT SHU MAVSUM (egasi: «yangi mavsumda 1 ta akkauntda o'ynashadi»): ulash ruxsat etilgan mavsum —
    app_flags.ef_link_season (birinchi migratsiyadagi joriy mavsum). Mavsum almashgach ulanishlar o'z-o'zidan
    amal qilmaydi va yangisi yaratilmaydi.
  * Ulangan ikki akkaunt bir-biriga raqib bo'lsa — skrinshot qabul qilinmaydi (match_shot: same_person).
Jadval — ef_nick_links (migratsiya, qoida #31).
"""

import logging
import time

from models import get_connection

logger = logging.getLogger(__name__)

LINK_MAX = 1                     # egasidan tashqari nechta akkaunt ulanishi mumkin
FLAG_LINK_SEASON = "ef_link_season"
ST_PENDING, ST_OK, ST_NO = "pending", "ok", "rejected"


def _season(cur) -> int:
    try:
        r = cur.execute("SELECT current_season FROM season_state WHERE id = 1").fetchone()
        return r["current_season"] if r else 1
    except Exception:
        return 1


def migrate_ef_nick_link(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS ef_nick_links (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "user_id INTEGER NOT NULL, owner_id INTEGER NOT NULL, season INTEGER NOT NULL, "
                "status TEXT NOT NULL DEFAULT 'pending', created_at REAL, decided_at REAL)")
    cur.execute("CREATE TABLE IF NOT EXISTS app_flags (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("INSERT OR IGNORE INTO app_flags (key, value) VALUES (?, ?)", (FLAG_LINK_SEASON, str(_season(cur))))


def link_allowed(cur) -> bool:
    try:
        r = cur.execute("SELECT value FROM app_flags WHERE key = ?", (FLAG_LINK_SEASON,)).fetchone()
    except Exception:
        return False
    return bool(r) and str(_season(cur)) == r["value"]


def active_links(cur, user_ids) -> dict[int, int]:
    """{ulangan user_id: egasi user_id} — faqat tasdiqlangan va joriy mavsumdagilar."""
    ids = [int(u) for u in user_ids if u]
    if not ids or not link_allowed(cur):
        return {}
    q = ",".join("?" * len(ids))
    season = _season(cur)
    try:
        return {r["user_id"]: r["owner_id"] for r in cur.execute(
            f"SELECT user_id, owner_id FROM ef_nick_links WHERE status = 'ok' AND season = ? AND user_id IN ({q})",
            [season, *ids])}
    except Exception:
        return {}


def my_link(cur, user_id: int) -> dict | None:
    """Mening (ikkinchi akkaunt sifatida) joriy so'rovim / ulanishim."""
    if not link_allowed(cur):
        return None
    r = cur.execute("SELECT l.id, l.status, n.nick FROM ef_nick_links l JOIN ef_nicknames n ON n.user_id = l.owner_id "
                    "WHERE l.user_id = ? AND l.season = ? AND l.status IN ('pending', 'ok') ORDER BY l.id DESC LIMIT 1",
                    (user_id, _season(cur))).fetchone()
    return dict(r) if r else None


def request_link(cur, user_id: int, owner_id: int) -> tuple[bool, str | dict]:
    """set_nick ichidan (BEGIN IMMEDIATE tranzaksiyada) — band nikname uchun egasiga so'rov."""
    if not link_allowed(cur):
        return False, "nick_taken"
    season = _season(cur)
    if cur.execute("SELECT 1 FROM ef_nick_links WHERE owner_id = ? AND user_id = ? AND season = ? AND status = 'pending'",
                   (owner_id, user_id, season)).fetchone():
        return True, {"pending": True, "owner_id": owner_id, "repeat": True}
    n = cur.execute("SELECT COUNT(*) AS n FROM ef_nick_links WHERE owner_id = ? AND season = ? AND status = 'ok'",
                    (owner_id, season)).fetchone()["n"]
    if n >= LINK_MAX:
        return False, "nick_link_full"
    if cur.execute("SELECT 1 FROM ef_nick_links WHERE owner_id = ? AND season = ? AND status = 'ok'",
                   (user_id, season)).fetchone():
        return False, "nick_taken"                 # o'zi boshqaga «ega» — avval o'shani hal qilsin
    cur.execute("UPDATE ef_nick_links SET status = 'rejected', decided_at = ? WHERE user_id = ? AND status IN ('pending', 'ok')",
                (time.time(), user_id))
    cur.execute("INSERT INTO ef_nick_links (user_id, owner_id, season, created_at) VALUES (?, ?, ?, ?)",
                (user_id, owner_id, season, time.time()))
    logger.info("eF NIKNAME ULASH so'rovi: user %s → egasi %s", user_id, owner_id)
    return True, {"pending": True, "owner_id": owner_id}


def drop_my_link(cur, user_id: int) -> None:
    """O'z niknameini kiritsa — eski ulanish/so'rov bekor."""
    cur.execute("UPDATE ef_nick_links SET status = 'rejected', decided_at = ? WHERE user_id = ? AND status IN ('pending', 'ok')",
                (time.time(), user_id))


def requests_for_owner(owner_id: int) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if not link_allowed(cur):
            return []
        rows = cur.execute("SELECT l.id, u.nickname, u.username FROM ef_nick_links l JOIN users u ON u.id = l.user_id "
                           "WHERE l.owner_id = ? AND l.season = ? AND l.status = 'pending' ORDER BY l.id",
                           (owner_id, _season(cur))).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def decide_link(owner_id: int, link_id: int, accept: bool) -> tuple[bool, str | dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        r = cur.execute("SELECT * FROM ef_nick_links WHERE id = ?", (link_id,)).fetchone()
        if not r or r["owner_id"] != owner_id:
            conn.rollback()
            return False, "not_found"
        if r["status"] != ST_PENDING:
            conn.rollback()
            return False, "already_decided"
        if accept:
            n = cur.execute("SELECT COUNT(*) AS n FROM ef_nick_links WHERE owner_id = ? AND season = ? AND status = 'ok'",
                            (owner_id, r["season"])).fetchone()["n"]
            if n >= LINK_MAX:
                conn.rollback()
                return False, "nick_link_full"
        cur.execute("UPDATE ef_nick_links SET status = ?, decided_at = ? WHERE id = ?",
                    (ST_OK if accept else ST_NO, time.time(), link_id))
        conn.commit()
        logger.info("eF NIKNAME ULASH #%s: egasi %s — %s", link_id, owner_id, "TASDIQLADI" if accept else "RAD ETDI")
        return True, {"user_id": r["user_id"], "accepted": bool(accept)}
    finally:
        conn.close()
