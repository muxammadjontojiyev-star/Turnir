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

# 2026-10-03 (admin qarori): guruhlar 4 kishilik va DOIM TO'LIQ — sig'im 4 ga karrali,
# turnir faqat qabul qilinganlar soni 4 ga karrali bo'lganda boshlanadi (sig'imdan kam bo'lsa ham).
PT_GROUP_SIZE = 4               # guruhda kishi soni (pt_draw shu yerdan oladi — qoida #17)
PT_MIN_PLAYERS = 8              # = 2 guruh
PT_MAX_PLAYERS = 128            # = 32 guruh (pley-off 1/32 finaldan)
PT_DEFAULT_PLAYERS = 8          # yaratish formasidagi standart sig'im
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
                    "t.receipt_at, t.reject_reason, t.max_players, t.paid_via")


def is_manager(cursor, tid: int, user_id: int, owner_user_id: int | None = None) -> bool:
    """
    Turnirni boshqara oladimi: tashkilotchi YOKI turnir admini (pt_admins).
    Barcha "boshqaruv" tekshiruvlari shu yerdan (qoida #26). owner_user_id berilsa — qo'shimcha so'rovsiz.
    """
    if owner_user_id is None:
        cursor.execute("SELECT owner_user_id FROM pt_tournaments WHERE id = ?", (tid,))
        r = cursor.fetchone()
        if not r:
            return False
        owner_user_id = r["owner_user_id"]
    if owner_user_id == user_id:
        return True
    cursor.execute("SELECT 1 FROM pt_admins WHERE tournament_id = ? AND user_id = ?", (tid, user_id))
    return cursor.fetchone() is not None


def managers_for_notify(cursor, tid: int) -> list[dict]:
    """Tashkilotchi + adminlar: [{telegram_id, language}] (so'rovlar, hal qilinmagan o'yinlar xabari)."""
    cursor.execute(
        "SELECT u.telegram_id, u.language FROM pt_tournaments t JOIN users u ON u.id = t.owner_user_id "
        "WHERE t.id = ? UNION SELECT u.telegram_id, u.language FROM pt_admins a "
        "JOIN users u ON u.id = a.user_id WHERE a.tournament_id = ?", (tid, tid))
    return [dict(r) for r in cursor.fetchall()]


def _clean_name(name: str) -> str:
    """Bo'sh joylarni siqadi. HTML frontendda escHtml qilinadi (qoida #35)."""
    return " ".join((name or "").split())


def valid_size(n) -> bool:
    """Sig'im: butun son, PT_MIN_PLAYERS..PT_MAX_PLAYERS oralig'ida va PT_GROUP_SIZE ga karrali."""
    return (isinstance(n, int) and not isinstance(n, bool)
            and PT_MIN_PLAYERS <= n <= PT_MAX_PLAYERS and n % PT_GROUP_SIZE == 0)


def can_start_with(n: int) -> str | None:
    """Shu sondagi ishtirokchi bilan boshlash mumkinmi? None — mumkin, aks holda sabab."""
    if n < PT_MIN_PLAYERS:
        return "not_enough_players"
    if n % PT_GROUP_SIZE:
        return "not_multiple"
    return None


def pt_create_tournament(user: dict, name: str, price_uzs: int,
                         max_players: int = PT_DEFAULT_PLAYERS,
                         via_subscription: bool = False) -> tuple[bool, str | dict]:
    """
    via_subscription=True — faol obuna bilan: to'lovsiz, darhol 'recruiting', paid_via='subscription'
    (obuna va limit tekshiruvi chaqiruvchida — pt_subscriptions.pt_create_with_mode).
    Sabablar: price_not_set, bad_size, name_too_short, name_too_long, too_many_unpaid.
    Qaytaradi (ok): {"id", "status", "invite_code", "price_uzs"}
    """
    if price_uzs <= 0 and not via_subscription:
        return False, "price_not_set"
    if not valid_size(max_players):
        return False, "bad_size"
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
        if cursor.fetchone()["c"] >= PT_MAX_UNPAID_PER_USER and not via_subscription:
            cursor.execute("ROLLBACK")
            return False, "too_many_unpaid"

        code = secrets.token_urlsafe(_INVITE_CODE_BYTES)
        status = STATUS_RECRUITING if via_subscription else STATUS_AWAITING_PAYMENT
        cursor.execute(
            "INSERT INTO pt_tournaments (owner_user_id, owner_telegram_id, name, status, "
            "invite_code, price_uzs, max_players, paid_via) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], user["telegram_id"], name, status, code,
             0 if via_subscription else price_uzs, max_players,
             "subscription" if via_subscription else "one_time"),
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
    return True, {"id": tid, "status": status, "invite_code": code,
                  "price_uzs": 0 if via_subscription else price_uzs, "max_players": max_players,
                  "paid_via": "subscription" if via_subscription else "one_time"}


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
            LEFT JOIN pt_admins a ON a.tournament_id = t.id AND a.user_id = ?
            WHERE t.owner_user_id = ? OR m.user_id IS NOT NULL OR a.user_id IS NOT NULL
            ORDER BY t.id DESC
            """,
            (user_id, user_id, user_id),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT tournament_id FROM pt_admins WHERE user_id = ?", (user_id,))
        admin_of = {r["tournament_id"] for r in cursor.fetchall()}
    finally:
        conn.close()
    for r in rows:
        r["is_owner"] = r["owner_user_id"] == user_id
        r["is_admin"] = r["id"] in admin_of
        if not (r["is_owner"] or r["is_admin"]):
            r.pop("invite_code", None)   # havolani faqat tashkilotchi/admin tarqatadi
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
        cursor.execute("SELECT a.user_id, u.nickname, u.username FROM pt_admins a JOIN users u "
                       "ON u.id = a.user_id WHERE a.tournament_id = ? ORDER BY a.id", (tournament_id,))
        admins = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    is_owner = t["owner_user_id"] == user_id
    is_admin = any(a["user_id"] == user_id for a in admins)
    is_member = any(m["user_id"] == user_id for m in members)
    if not (is_owner or is_admin or is_member or is_super):
        return None
    if not (is_owner or is_admin or is_super):
        t.pop("invite_code", None)
        members = [m for m in members if m["status"] == "approved"]
    t.update({"is_owner": is_owner, "is_admin": is_admin, "is_manager": is_owner or is_admin,
              "admins": admins, "members": members,
              "approved_count": sum(1 for m in members if m["status"] == "approved"),
              "min_players": PT_MIN_PLAYERS, "size_limit": PT_MAX_PLAYERS, "group_size": PT_GROUP_SIZE,
              "start_block": can_start_with(sum(1 for m in members if m["status"] == "approved"))})
    return t


def pt_set_capacity(tid: int, owner_id: int, max_players: int) -> tuple[bool, str]:
    """
    Tashkilotchi sig'imni o'zgartiradi (qur'agacha). Qabul qilinganlardan kam bo'lolmaydi.
    Bir martalik to'lov (2026-10-03):
      - to'lovdan OLDIN (awaiting_payment/rejected) — narx yangi pog'onaga qayta hisoblanadi;
      - to'langan/tekshiruvda — faqat O'SHA narx pog'onasi ichida (tier_locked), aks holda
        8 kishilik narxni to'lab 128 kishilik turnir qilish mumkin bo'lardi.
    Obuna orqali yaratilgan turnirda — istalgan sig'im.
    Sabablar: bad_size, not_found, not_owner, already_started, below_members, tier_locked, price_not_set.
    """
    from pt_pricing import price_for_size, tier_for_size
    if not valid_size(max_players):
        return False, "bad_size"
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT owner_user_id, status, max_players, paid_via FROM pt_tournaments WHERE id = ?",
                       (tid,))
        t = cursor.fetchone()
        why = None
        new_price = None
        if not t:
            why = "not_found"
        elif t["owner_user_id"] != owner_id:
            why = "not_owner"
        elif t["status"] not in (*_UNPAID, STATUS_RECRUITING, STATUS_REJECTED):
            why = "already_started"
        else:
            cursor.execute("SELECT COUNT(*) AS c FROM pt_members WHERE tournament_id = ? "
                           "AND status = 'approved'", (tid,))
            if cursor.fetchone()["c"] > max_players:
                why = "below_members"
            elif t["paid_via"] == "one_time":
                if t["status"] in (STATUS_AWAITING_PAYMENT, STATUS_REJECTED):
                    new_price = price_for_size(max_players)
                    if new_price <= 0:
                        why = "price_not_set"
                elif tier_for_size(max_players) != tier_for_size(t["max_players"]):
                    why = "tier_locked"
        if why:
            cursor.execute("ROLLBACK")
            return False, why
        cursor.execute("UPDATE pt_tournaments SET max_players = ?, price_uzs = COALESCE(?, price_uzs), "
                       "updated_at = CURRENT_TIMESTAMP WHERE id = ?", (max_players, new_price, tid))
        cursor.execute("COMMIT")
        return True, "ok"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_set_capacity: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
