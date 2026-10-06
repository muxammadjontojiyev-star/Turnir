"""
pt_members.py — SHAXSIY turnirga qo'shilish (2026-10-02, 3-bosqich).

Admin qarori: ikkala usul ham.
  1) Taklif havolasi: t.me/<bot>?start=pt_<kod> -> do'st so'rov yuboradi (pending)
     -> tashkilotchi tasdiqlaydi (approved) yoki rad etadi (o'chiriladi).
  2) Tashkilotchi Telegram ID yoki @username bilan to'g'ridan-to'g'ri qo'shadi (approved).
A'zolik faqat 'recruiting' holatida o'zgaradi (qur'adan keyin tarkib qotadi).
Sig'im: approved <= turnirning o'z max_players qiymati (tashkilotchi 6..20 tanlaydi).
Har amal BEGIN IMMEDIATE ichida (qoida #38).
Ruxsat: boshqaruv amallari FAQAT tashkilotchi (qoida #34).
"""

import logging
import re

from models import get_connection
from pt_core import STATUS_RECRUITING, is_manager, managers_for_notify

logger = logging.getLogger(__name__)

INVITE_PREFIX = "pt_"                         # /start parametri: pt_<invite_code>
_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{4,40}$")
_USERNAME_RE = re.compile(r"^@?([A-Za-z0-9_]{4,32})$")


def parse_invite_payload(payload: str | None) -> str | None:
    """'/start pt_<kod>' parametridan kodni ajratadi; noto'g'ri bo'lsa None."""
    if not payload or not payload.startswith(INVITE_PREFIX):
        return None
    code = payload[len(INVITE_PREFIX):]
    return code if _CODE_RE.match(code) else None


def _approved_count(cursor, tid: int) -> int:
    cursor.execute("SELECT COUNT(*) AS c FROM pt_members WHERE tournament_id = ? AND status = 'approved'",
                   (tid,))
    return cursor.fetchone()["c"]


def pt_invite_preview(code: str, user_id: int | None = None) -> dict | None:
    """Havola egasi ko'radigan qisqa ma'lumot (invite_code oshkor qilinmaydi)."""
    if not code or not _CODE_RE.match(code):
        return None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT t.id, t.name, t.status, t.max_players, u.nickname AS owner_nickname, "
            "u.username AS owner_username "
            "FROM pt_tournaments t JOIN users u ON u.id = t.owner_user_id WHERE t.invite_code = ?",
            (code,),
        )
        t = cursor.fetchone()
        if not t:
            return None
        out = dict(t)
        out["approved_count"] = _approved_count(cursor, t["id"])
        out["my_status"] = None
        if user_id is not None:
            cursor.execute("SELECT status FROM pt_members WHERE tournament_id = ? AND user_id = ?",
                           (t["id"], user_id))
            m = cursor.fetchone()
            out["my_status"] = m["status"] if m else None
        return out
    finally:
        conn.close()


def _tx(fn):
    """BEGIN IMMEDIATE tranzaksiyasi o'rami (DRY): fn(cursor) -> (ok, natija)."""
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        ok, result = fn(cursor)
        cursor.execute("COMMIT" if ok else "ROLLBACK")
        return ok, result
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_members: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def _owner_info(cursor, tid: int) -> dict | None:
    cursor.execute(
        "SELECT t.id, t.name, t.status, t.owner_user_id, t.owner_telegram_id, t.max_players, "
        "u.language AS owner_language "
        "FROM pt_tournaments t JOIN users u ON u.id = t.owner_user_id WHERE t.id = ?", (tid,))
    r = cursor.fetchone()
    return dict(r) if r else None


def pt_request_join(code: str, user: dict) -> tuple[bool, str | dict]:
    """
    Havola orqali so'rov (pending). Sabablar: not_found, not_recruiting, already_member, full.
    Qaytaradi (ok): {tournament_id, name, owner_telegram_id, owner_language} — tashkilotchiga xabar uchun.
    """
    def run(cursor):
        if not code or not _CODE_RE.match(code):
            return False, "not_found"
        cursor.execute("SELECT id FROM pt_tournaments WHERE invite_code = ?", (code,))
        row = cursor.fetchone()
        if not row:
            return False, "not_found"
        t = _owner_info(cursor, row["id"])
        if t["status"] != STATUS_RECRUITING:
            return False, "not_recruiting"
        cursor.execute("SELECT 1 FROM pt_members WHERE tournament_id = ? AND user_id = ?",
                       (t["id"], user["id"]))
        if cursor.fetchone():
            return False, "already_member"
        if _approved_count(cursor, t["id"]) >= t["max_players"]:
            return False, "full"
        cursor.execute(
            "INSERT INTO pt_members (tournament_id, user_id, telegram_id, status) VALUES (?, ?, ?, 'pending')",
            (t["id"], user["id"], user["telegram_id"]))
        return True, {"tournament_id": t["id"], "name": t["name"],
                      "owner_telegram_id": t["owner_telegram_id"], "owner_language": t["owner_language"],
                      "managers": managers_for_notify(cursor, t["id"])}
    return _tx(run)


def _target_member(cursor, tid: int, owner_id: int, member_user_id: int):
    """Umumiy tekshiruv: tashkilotchi, recruiting, a'zo mavjud. (ok, t|sabab, member)"""
    t = _owner_info(cursor, tid)
    if not t:
        return False, "not_found", None
    if not is_manager(cursor, tid, owner_id, t["owner_user_id"]):       # tashkilotchi yoki admin
        return False, "not_owner", None
    if t["status"] != STATUS_RECRUITING:
        return False, "not_recruiting", None
    cursor.execute(
        "SELECT m.status, m.telegram_id, u.language FROM pt_members m JOIN users u ON u.id = m.user_id "
        "WHERE m.tournament_id = ? AND m.user_id = ?", (tid, member_user_id))
    m = cursor.fetchone()
    if not m:
        return False, "member_not_found", None
    return True, t, dict(m)


def pt_approve_member(tid: int, owner_id: int, member_user_id: int) -> tuple[bool, str | dict]:
    """pending -> approved. Sabablar: not_found, not_owner, not_recruiting, member_not_found, already_approved, full."""
    def run(cursor):
        ok, t, m = _target_member(cursor, tid, owner_id, member_user_id)
        if not ok:
            return False, t
        if m["status"] == "approved":
            return False, "already_approved"
        if _approved_count(cursor, tid) >= t["max_players"]:
            return False, "full"
        cursor.execute("UPDATE pt_members SET status = 'approved' WHERE tournament_id = ? AND user_id = ? "
                       "AND status = 'pending'", (tid, member_user_id))
        return True, {"name": t["name"], "telegram_id": m["telegram_id"], "language": m["language"]}
    return _tx(run)


def pt_remove_member(tid: int, owner_id: int, member_user_id: int) -> tuple[bool, str | dict]:
    """
    So'rovni rad etish YOKI a'zoni chiqarish (tashkilotchi yoki admin).
    TASHKILOTCHINI hech kim chiqara olmaydi (cannot_remove_owner) — tekshiruv chiqarilayotgan
    odam bo'yicha (amal bajaruvchi bo'yicha emas: admin tashkilotchini chiqarib yubormasin).
    """
    def run(cursor):
        ok, t, m = _target_member(cursor, tid, owner_id, member_user_id)
        if not ok:
            return False, t
        if member_user_id == t["owner_user_id"]:
            return False, "cannot_remove_owner"
        cursor.execute("DELETE FROM pt_members WHERE tournament_id = ? AND user_id = ?",
                       (tid, member_user_id))
        return True, {"name": t["name"], "telegram_id": m["telegram_id"], "language": m["language"],
                      "was": m["status"]}
    return _tx(run)


def _find_user(cursor, query: str) -> dict | None:
    """Telegram ID (raqam) yoki @username bo'yicha bazadagi foydalanuvchi."""
    q = (query or "").strip()
    if q.isdigit():
        cursor.execute("SELECT id, telegram_id, nickname, username, language FROM users WHERE telegram_id = ?",
                       (int(q),))
    else:
        m = _USERNAME_RE.match(q)
        if not m:
            return None
        cursor.execute("SELECT id, telegram_id, nickname, username, language FROM users "
                       "WHERE LOWER(username) = LOWER(?)", (m.group(1),))
    r = cursor.fetchone()
    return dict(r) if r else None


def pt_add_member(tid: int, owner_id: int, query: str) -> tuple[bool, str | dict]:
    """
    Tashkilotchi ID/@username bilan qo'shadi (darhol approved; pending bo'lsa tasdiqlanadi).
    Sabablar: not_found, not_owner, not_recruiting, user_not_found, already_member, full.
    """
    def run(cursor):
        t = _owner_info(cursor, tid)
        if not t:
            return False, "not_found"
        if not is_manager(cursor, tid, owner_id, t["owner_user_id"]):   # tashkilotchi yoki admin
            return False, "not_owner"
        if t["status"] != STATUS_RECRUITING:
            return False, "not_recruiting"
        u = _find_user(cursor, query)
        if not u:
            return False, "user_not_found"
        cursor.execute("SELECT status FROM pt_members WHERE tournament_id = ? AND user_id = ?", (tid, u["id"]))
        existing = cursor.fetchone()
        if existing and existing["status"] == "approved":
            return False, "already_member"
        if _approved_count(cursor, tid) >= t["max_players"]:
            return False, "full"
        if existing:
            cursor.execute("UPDATE pt_members SET status = 'approved' WHERE tournament_id = ? AND user_id = ?",
                           (tid, u["id"]))
        else:
            cursor.execute("INSERT INTO pt_members (tournament_id, user_id, telegram_id, status) "
                           "VALUES (?, ?, ?, 'approved')", (tid, u["id"], u["telegram_id"]))
        return True, {"name": t["name"], "user_id": u["id"], "telegram_id": u["telegram_id"],
                      "language": u["language"], "nickname": u["nickname"], "username": u["username"]}
    return _tx(run)
