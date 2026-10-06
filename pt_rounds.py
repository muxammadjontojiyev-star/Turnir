"""
pt_rounds.py — SHAXSIY turnir turlari va muddatlari (2026-10-02, 4-bosqich).

Admin qarori: har tur muddatini TASHKILOTCHI belgilaydi.
  - Faqat joriy tur ochiq (natija kiritiladi). Muddat bo'lmasa — tur ochiq turaveradi.
  - Muddat o'tganda (scheduler, daqiqada 1 marta) YOKI tashkilotchi "Turni yopish"
    bosganda: awaiting -> confirmed, pending -> 0:0 confirmed (rasmiy turnirlar kabi),
    keyingi tur ochiladi (muddatsiz — tashkilotchi yangisini belgilaydi).
  - Oxirgi tur yopilgach current_round = total_rounds + 1 -> guruh bosqichi tugadi.
Muddat UTC 'YYYY-MM-DD HH:MM:SS' da saqlanadi; tashkilotchi Toshkent vaqtida kiritadi.
"""

import logging
from datetime import datetime, timedelta, timezone

from config import TOURNAMENT_TIMEZONE_OFFSET
from models import get_connection
from pt_core import STATUS_RUNNING

logger = logging.getLogger(__name__)

DEADLINE_MIN_AHEAD_MIN = 5          # kamida 5 daqiqa keyin
DEADLINE_MAX_AHEAD_DAYS = 30
_LOCAL_TZ = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
_UTC_FMT = "%Y-%m-%d %H:%M:%S"


def parse_local_deadline(value: str, now_utc: datetime | None = None) -> tuple[str | None, str]:
    """'YYYY-MM-DDTHH:MM' (Toshkent) -> (UTC satr, 'ok') yoki (None, sabab)."""
    try:
        local = datetime.strptime((value or "").strip()[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=_LOCAL_TZ)
    except ValueError:
        return None, "bad_deadline"
    now_utc = now_utc or datetime.now(timezone.utc)
    utc = local.astimezone(timezone.utc)
    if utc < now_utc + timedelta(minutes=DEADLINE_MIN_AHEAD_MIN):
        return None, "deadline_in_past"
    if utc > now_utc + timedelta(days=DEADLINE_MAX_AHEAD_DAYS):
        return None, "deadline_too_far"
    return utc.strftime(_UTC_FMT), "ok"


def utc_to_local_text(utc_str: str | None) -> str | None:
    """UTC satr -> 'DD.MM HH:MM' (Toshkent) — xabarlar va UI uchun."""
    if not utc_str:
        return None
    try:
        dt = datetime.strptime(utc_str, _UTC_FMT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return dt.astimezone(_LOCAL_TZ).strftime("%d.%m %H:%M")


def members_for_notify(cursor, tid: int) -> list[dict]:
    """Bildirishnoma uchun: [{telegram_id, language}] (approved a'zolar)."""
    cursor.execute(
        "SELECT m.telegram_id, u.language FROM pt_members m JOIN users u ON u.id = m.user_id "
        "WHERE m.tournament_id = ? AND m.status = 'approved'", (tid,))
    return [dict(r) for r in cursor.fetchall()]


def _tx(fn):
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
            logger.exception("pt_rounds: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def _owned_running(cursor, tid: int, owner_id: int):
    cursor.execute("SELECT id, name, owner_user_id, status, current_round, total_rounds "
                   "FROM pt_tournaments WHERE id = ?", (tid,))
    t = cursor.fetchone()
    if not t:
        return None, "not_found"
    if t["owner_user_id"] != owner_id:
        return None, "not_owner"
    if t["status"] != STATUS_RUNNING:
        return None, "not_running"
    if t["current_round"] > t["total_rounds"]:
        return None, "groups_finished"
    return dict(t), "ok"


def _close_round(cursor, t: dict) -> dict:
    """Joriy turni yopadi (va undan oldingi chala qolganlarni), keyingisini ochadi."""
    tid, cur = t["id"], t["current_round"]
    cursor.execute(
        "UPDATE pt_matches SET status = 'confirmed' WHERE tournament_id = ? AND stage = 'group' "
        "AND round <= ? AND status = 'awaiting_confirmation'", (tid, cur))
    awaiting = cursor.rowcount or 0
    cursor.execute(
        "UPDATE pt_matches SET score1 = 0, score2 = 0, status = 'confirmed' WHERE tournament_id = ? "
        "AND stage = 'group' AND round <= ? AND status = 'pending'", (tid, cur))
    zero = cursor.rowcount or 0
    cursor.execute(
        "UPDATE pt_tournaments SET current_round = current_round + 1, round_deadline = NULL, "
        "updated_at = CURRENT_TIMESTAMP WHERE id = ?", (tid,))
    return {"id": tid, "name": t["name"], "closed_round": cur, "next_round": cur + 1,
            "groups_finished": cur + 1 > t["total_rounds"], "awaiting": awaiting, "zero": zero,
            "members": members_for_notify(cursor, tid)}


def pt_set_deadline(tid: int, owner_id: int, local_value: str) -> tuple[bool, str | dict]:
    """
    Joriy tur (yoki pley-off bosqichi) muddati.
    Sabablar: not_found, not_owner, not_running, groups_finished (yarim final boshlanmagan), bad_deadline, ...
    """
    utc, reason = parse_local_deadline(local_value)
    if utc is None:
        return False, reason

    def run(cursor):
        t, why = _owned_running(cursor, tid, owner_id)
        phase = None
        if t is None and why == "groups_finished":
            from pt_knockout import STAGES, pt_knockout_phase
            phase = pt_knockout_phase(cursor, tid)
            if phase in STAGES:                                 # pley-off bosqichiga muddat
                cursor.execute("SELECT id, name, current_round FROM pt_tournaments WHERE id = ?", (tid,))
                t = dict(cursor.fetchone())
        if t is None:
            return False, why
        cursor.execute("UPDATE pt_tournaments SET round_deadline = ?, updated_at = CURRENT_TIMESTAMP "
                       "WHERE id = ?", (utc, tid))
        return True, {"name": t["name"], "round": t["current_round"], "phase": phase, "deadline_utc": utc,
                      "deadline_local": utc_to_local_text(utc), "members": members_for_notify(cursor, tid)}
    return _tx(run)


def pt_close_round_now(tid: int, owner_id: int) -> tuple[bool, str | dict]:
    """Tashkilotchi joriy turni muddatidan oldin yopadi."""
    def run(cursor):
        t, why = _owned_running(cursor, tid, owner_id)
        if t is None:
            return False, why
        return True, _close_round(cursor, t)
    return _tx(run)


def _close_knockout(cursor, t: dict) -> dict:
    """
    Pley-off muddati o'tdi: FAQAT awaiting -> confirmed (durang yo'q, 0:0 qo'yilmaydi);
    o'ynalmaganini tashkilotchi hal qiladi (unga xabar). Keyin pt_advance.
    """
    from pt_knockout import pt_advance
    tid = t["id"]
    cursor.execute("UPDATE pt_matches SET status = 'confirmed' WHERE tournament_id = ? AND stage != 'group' "
                   "AND status = 'awaiting_confirmation'", (tid,))
    awaiting = cursor.rowcount or 0
    cursor.execute("UPDATE pt_tournaments SET round_deadline = NULL WHERE id = ?", (tid,))
    # Hal qilinmaganlar pt_advance'dan OLDIN sanaladi — aks holda shu daqiqada yaratilgan
    # final ham "o'ynalmagan" deb tashkilotchiga noto'g'ri xabar ketardi.
    cursor.execute("SELECT COUNT(*) AS c FROM pt_matches WHERE tournament_id = ? AND stage != 'group' "
                   "AND status = 'pending'", (tid,))
    pending = cursor.fetchone()["c"]
    adv = pt_advance(cursor, tid)
    cursor.execute("SELECT t.owner_telegram_id, u.language FROM pt_tournaments t JOIN users u "
                   "ON u.id = t.owner_user_id WHERE t.id = ?", (tid,))
    o = dict(cursor.fetchone())
    return {"id": tid, "name": t["name"], "knockout": True, "awaiting": awaiting, "pending": pending,
            "advance": adv, "owner": o, "members": members_for_notify(cursor, tid)}


def pt_tick(now_utc: datetime | None = None) -> list[dict]:
    """
    Scheduler: muddati o'tgan turlarni yopadi (idempotent — muddat NULL bo'ladi).
    Guruh: _close_round (0:0 bilan). Pley-off: _close_knockout (faqat awaiting tasdiqlanadi).
    """
    now_s = (now_utc or datetime.now(timezone.utc)).strftime(_UTC_FMT)

    def run(cursor):
        cursor.execute(
            "SELECT id, name, current_round, total_rounds FROM pt_tournaments "
            "WHERE status = ? AND round_deadline IS NOT NULL AND round_deadline <= ?", (STATUS_RUNNING, now_s))
        out = []
        for r in cursor.fetchall():
            t = dict(r)
            out.append(_close_round(cursor, t) if t["current_round"] <= t["total_rounds"]
                       else _close_knockout(cursor, t))
        return True, out
    _, closed = _tx(run)
    for c in closed:
        if c.get("knockout"):
            logger.info("PT #%s: pley-off muddati o'tdi (awaiting %s, hal qilinmagan %s)",
                        c["id"], c["awaiting"], c["pending"])
        else:
            logger.info("PT #%s: %s-tur muddati o'tdi (awaiting %s, 0:0 %s)",
                        c["id"], c["closed_round"], c["awaiting"], c["zero"])
    return closed
