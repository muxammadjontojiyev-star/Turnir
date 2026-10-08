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
                    "t.receipt_at, t.reject_reason, t.max_players, t.paid_via, t.rules, "
                    "t.format, t.league_name, t.legs")


def is_super_user(cursor, user_id: int) -> bool:
    """2026-10-07: bosh admin (config.ADMIN_TELEGRAM_IDS) — tashkilotchilarga yordam berish uchun
    istalgan shaxsiy turnirni ko'radi va tashkilotchi huquqlari bilan sozlaydi."""
    from admin_roles import is_super_admin
    cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (user_id,))
    r = cursor.fetchone()
    return bool(r) and is_super_admin(r["telegram_id"])


def can_own(cursor, owner_user_id: int, user_id: int) -> bool:
    """Tashkilotchi huquqi (admin qo'shish, sig'im, qoidalar, o'chirish): turnir egasi yoki bosh admin."""
    return owner_user_id == user_id or is_super_user(cursor, user_id)


def is_manager(cursor, tid: int, user_id: int, owner_user_id: int | None = None) -> bool:
    """
    Turnirni boshqara oladimi: tashkilotchi YOKI turnir admini (pt_admins) YOKI bosh admin (2026-10-07).
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
    return cursor.fetchone() is not None or is_super_user(cursor, user_id)


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


def check_format(fmt: str, league: str | None, legs: int, max_players: int) -> str | None:
    """2026-10-07: format, liga, doira va sig'im tekshiruvi. None — to'g'ri, aks holda sabab."""
    from pt_formats import FMT_LEAGUE, LEGS_ALLOWED, LEGS_FORMATS, valid_format, valid_leagues, valid_size_for
    if not valid_format(fmt):
        return "bad_format"
    if fmt == FMT_LEAGUE and not valid_leagues(league):
        return "bad_league"
    if legs not in LEGS_ALLOWED or (legs == 2 and fmt not in LEGS_FORMATS):
        return "bad_legs"
    return None if valid_size_for(fmt, max_players, league) else "bad_size"


def pt_create_tournament(user: dict, name: str, price_uzs: int,
                         max_players: int = PT_DEFAULT_PLAYERS,
                         via_subscription: bool = False, fmt: str = "classic",
                         league: str | None = None, legs: int = 1) -> tuple[bool, str | dict]:
    """
    2026-10-07: fmt (classic|league|cl|el|wc), league (faqat league; ro'yxat yoki "A|B" — ko'p liga),
    legs (1|2 — league va classic).
    via_subscription=True — faol obuna bilan: to'lovsiz, darhol 'recruiting', paid_via='subscription'
    (obuna va limit tekshiruvi chaqiruvchida — pt_subscriptions.pt_create_with_mode).
    Sabablar: price_not_set, bad_size, name_too_short, name_too_long, too_many_unpaid.
    Qaytaradi (ok): {"id", "status", "invite_code", "price_uzs"}
    """
    if price_uzs <= 0 and not via_subscription:
        return False, "price_not_set"
    why = check_format(fmt, league, legs, max_players)
    if why:
        return False, why
    from pt_formats import join_leagues
    league = join_leagues(league) if fmt == "league" else None       # ko'p liga: "A|B"
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
            "invite_code, price_uzs, max_players, paid_via, format, league_name, legs) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], user["telegram_id"], name, status, code,
             0 if via_subscription else price_uzs, max_players,
             "subscription" if via_subscription else "one_time", fmt, league, legs),
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
                  "paid_via": "subscription" if via_subscription else "one_time",
                  "format": fmt, "league_name": league, "legs": legs}


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


def start_block(t: dict, members: list[dict]) -> str | None:
    """Boshlash to'sig'i formatga qarab; jamoali formatlarda hamma klub/jamoa tanlagan bo'lishi shart."""
    from pt_formats import can_start_fmt, uses_teams
    approved = [m for m in members if m["status"] == "approved"]
    fmt = t.get("format") or "classic"
    why = can_start_fmt(fmt, len(approved), t["max_players"])
    if not why and uses_teams(fmt) and any(not m.get("team_name") for m in approved):
        why = "teams_missing"
    return why


def _support_unread(tid: int, user_id: int, manager: bool) -> int:
    from pt_support import support_unread
    return support_unread(tid, user_id, manager)


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
            "SELECT m.user_id, m.status, m.group_label, m.team_name, u.nickname, u.username "
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
    taken = sorted(m["team_name"] for m in members if m.get("team_name"))   # pending'lar ham band qilgan
    my = next((m for m in members if m["user_id"] == user_id), None)
    if not (is_owner or is_admin or is_super):
        t.pop("invite_code", None)
        members = [m for m in members if m["status"] == "approved"]
    t.update({"is_owner": is_owner, "is_admin": is_admin, "is_manager": is_owner or is_admin or is_super,
              "is_super": is_super, "can_own": is_owner or is_super,          # 2026-10-07: bosh admin yordami
              "admins": admins, "members": members,
              "approved_count": sum(1 for m in members if m["status"] == "approved"),
              "min_players": PT_MIN_PLAYERS, "size_limit": PT_MAX_PLAYERS, "group_size": PT_GROUP_SIZE,
              "start_block": start_block(t, members),
              # 2026-10-08: ishtirokchi <-> tashkilotchi chati (pt_support.py) — o'qilmaganlar
              "support_unread": _support_unread(tournament_id, user_id, is_owner or is_admin or is_super),
              "taken_teams": taken, "my_team": my.get("team_name") if my else None,
              "my_status": my["status"] if my else None})
    return t


# 2026-10-07: pt_set_capacity -> pt_capacity.py (formatga qarab sig'im; qoida #21)
