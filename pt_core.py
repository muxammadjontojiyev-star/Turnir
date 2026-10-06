"""
pt_core.py — SHAXSIY turnirlar yadrosi (2026-10-02, 1-bosqich: yaratish va ko'rish).

Muammo (qoida #52): do'stlar guruhi rasmiy turnirlarga aralashmaydigan o'z yopiq
turnirini o'tkaza olishi kerak; tashkilotchi buning uchun to'laydi.

Bu bosqichda: turnir yaratish (awaiting_payment), mening turnirlarim ro'yxati,
bitta turnir tafsiloti (faqat a'zo / tashkilotchi / bosh admin — qoida #34).
Tashkilotchi avtomatik ishtirokchi (approved) sifatida qo'shiladi.
"""

import logging
import secrets

from models import get_connection

logger = logging.getLogger(__name__)

PT_MIN_PLAYERS = 6
PT_MAX_PLAYERS = 20
PT_NAME_MIN = 3
PT_NAME_MAX = 40
PT_MAX_UNPAID_PER_USER = 3      # to'lanmagan turnirlar cheklovi (suiiste'mol — qoida #39)
_INVITE_CODE_BYTES = 6          # ~8 belgili URL-xavfsiz kod

STATUS_AWAITING_PAYMENT = "awaiting_payment"
STATUS_PAYMENT_REVIEW = "payment_review"
STATUS_RECRUITING = "recruiting"
STATUS_RUNNING = "running"
STATUS_FINISHED = "finished"
STATUS_REJECTED = "rejected"
STATUS_CANCELLED = "cancelled"
_UNPAID = (STATUS_AWAITING_PAYMENT, STATUS_PAYMENT_REVIEW)

_TOURNAMENT_COLS = ("t.id, t.name, t.status, t.invite_code, t.price_uzs, t.created_at, "
                    "t.owner_user_id, u.nickname AS owner_nickname, u.username AS owner_username, "
                    "t.receipt_at, t.reject_reason")


def _clean_name(name: str) -> str:
    """Bo'sh joylarni siqadi. HTML frontendda escHtml qilinadi (qoida #35)."""
    return " ".join((name or "").split())


def pt_create_tournament(user: dict, name: str, price_uzs: int) -> tuple[bool, str | dict]:
    """
    Sabablar: price_not_set, name_too_short, name_too_long, too_many_unpaid.
    Qaytaradi (ok): {"id", "status", "invite_code", "price_uzs"}
    """
    if price_uzs <= 0:
        return False, "price_not_set"
    name = _clean_name(name)
    if len(name) < PT_NAME_MIN:
        return False, "name_too_short"
    if len(name) > PT_NAME_MAX:
        return False, "name_too_long"

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        ph = ",".join("?" * len(_UNPAID))
        cursor.execute(
            f"SELECT COUNT(*) AS c FROM pt_tournaments WHERE owner_user_id = ? AND status IN ({ph})",
            (user["id"], *_UNPAID),
        )
        if cursor.fetchone()["c"] >= PT_MAX_UNPAID_PER_USER:
            cursor.execute("ROLLBACK")
            return False, "too_many_unpaid"

        code = secrets.token_urlsafe(_INVITE_CODE_BYTES)
        cursor.execute(
            "INSERT INTO pt_tournaments (owner_user_id, owner_telegram_id, name, status, "
            "invite_code, price_uzs) VALUES (?, ?, ?, ?, ?, ?)",
            (user["id"], user["telegram_id"], name, STATUS_AWAITING_PAYMENT, code, price_uzs),
        )
        tid = cursor.lastrowid
        cursor.execute(
            "INSERT INTO pt_members (tournament_id, user_id, telegram_id, status) "
            "VALUES (?, ?, ?, 'approved')",
            (tid, user["id"], user["telegram_id"]),
        )
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_create_tournament: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
    logger.info("Shaxsiy turnir yaratildi: #%s '%s' (user %s)", tid, name, user["id"])
    return True, {"id": tid, "status": STATUS_AWAITING_PAYMENT,
                  "invite_code": code, "price_uzs": price_uzs}


def pt_list_my_tournaments(user_id: int) -> list[dict]:
    """Men tashkilotchi YOKI a'zo bo'lgan turnirlar (yangisi birinchi)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            SELECT {_TOURNAMENT_COLS},
                   (SELECT COUNT(*) FROM pt_members m2
                     WHERE m2.tournament_id = t.id AND m2.status = 'approved') AS members_count,
                   m.status AS my_status
            FROM pt_tournaments t
            JOIN users u ON u.id = t.owner_user_id
            LEFT JOIN pt_members m ON m.tournament_id = t.id AND m.user_id = ?
            WHERE t.owner_user_id = ? OR m.user_id IS NOT NULL
            ORDER BY t.id DESC
            """,
            (user_id, user_id),
        )
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    for r in rows:
        r["is_owner"] = r["owner_user_id"] == user_id
        if not r["is_owner"]:
            r.pop("invite_code", None)   # havolani faqat tashkilotchi tarqatadi
    return rows


def pt_get_tournament(tournament_id: int, user_id: int, is_super: bool = False) -> dict | None:
    """
    Turnir tafsiloti + a'zolar. Ruxsat: tashkilotchi, a'zo (pending ham) yoki bosh admin.
    Ruxsat bo'lmasa yoki topilmasa None (mavjudligini ham oshkor qilmaymiz).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"SELECT {_TOURNAMENT_COLS} FROM pt_tournaments t "
            "JOIN users u ON u.id = t.owner_user_id WHERE t.id = ?",
            (tournament_id,),
        )
        t = cursor.fetchone()
        if not t:
            return None
        t = dict(t)
        cursor.execute(
            "SELECT m.user_id, m.status, m.group_label, u.nickname, u.username "
            "FROM pt_members m JOIN users u ON u.id = m.user_id "
            "WHERE m.tournament_id = ? ORDER BY m.status = 'pending', m.id",
            (tournament_id,),
        )
        members = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    is_owner = t["owner_user_id"] == user_id
    is_member = any(m["user_id"] == user_id for m in members)
    if not (is_owner or is_member or is_super):
        return None
    if not (is_owner or is_super):
        t.pop("invite_code", None)
        members = [m for m in members if m["status"] == "approved"]
    t.update({"is_owner": is_owner, "members": members,
              "approved_count": sum(1 for m in members if m["status"] == "approved"),
              "min_players": PT_MIN_PLAYERS, "max_players": PT_MAX_PLAYERS})
    return t
