"""
pt_daily.py — SHAXSIY turnir: kuniga N tur (2026-10-10).

Admin so'rovi: rasmiy ligalarda kuniga 2 tur ochiladi; shaxsiy turnir tashkilotchisi
kuniga nechta tur ochilishini o'zi tanlasin.

pt_tournaments.rounds_per_day:
  0  — QO'LDA (avvalgi xulq, o'zgarmaydi): bitta tur ochiq, muddatni tashkilotchi qo'yadi.
  N  — KUNLIK: current_round .. current_round+N-1 turlar BIRGA ochiq; muddat avtomatik —
       har kuni rasmiy ligalar vaqtida (MATCHDAY_UNLOCK_HOUR:MINUTE, Toshkent). Muddat o'tganda
       (pt_rounds.pt_tick) ochiq turlar yopiladi (pending -> 0:0, awaiting -> confirmed) va
       keyingi N ta tur ochiladi, yangi muddat yana ertangi shu vaqt.
Faqat guruh/liga bosqichiga tegishli (pley-off muddatlarini tashkilotchi qo'yadi).
"""

from datetime import datetime, timedelta, timezone

from config import MATCHDAY_UNLOCK_HOUR, MATCHDAY_UNLOCK_MINUTE, TOURNAMENT_TIMEZONE_OFFSET

PT_RPD_CHOICES = (0, 1, 2, 3, 4)       # 0 = qo'lda; rasmiy ligalarda 2 (MATCHDAYS_PER_UNLOCK)
PT_DAILY_MIN_GAP_HOURS = 6             # birinchi muddat kamida shuncha soatdan keyin (o'ynashga vaqt)
_LOCAL_TZ = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
_UTC_FMT = "%Y-%m-%d %H:%M:%S"


def daily_time_text() -> str:
    """Kunlik muddat vaqti matni ('23:30') — UI uchun (config'dan, qoida #17)."""
    return f"{MATCHDAY_UNLOCK_HOUR:02d}:{MATCHDAY_UNLOCK_MINUTE:02d}"


def open_upto(current_round: int, total_rounds: int, rounds_per_day: int | None) -> int:
    """Ochiq turlarning oxirgisi: qo'lda — faqat joriy; kunlik — joriy + N-1 (jami turdan oshmaydi)."""
    n = max(int(rounds_per_day or 0), 1)
    return min(current_round + n - 1, max(total_rounds, current_round))


def round_is_open(rnd: int, current_round: int, total_rounds: int, rounds_per_day: int | None) -> bool:
    """Guruh o'yini natija kiritishga ochiqmi (qoida #26 — barcha tekshiruvlar shu yerdan)."""
    return current_round <= rnd <= open_upto(current_round, total_rounds, rounds_per_day)


def round_label(current_round: int, upto: int) -> str:
    """'3' yoki '3–4' — xabarlar va sarlavha uchun."""
    return str(current_round) if upto <= current_round else f"{current_round}–{upto}"


def next_daily_deadline_utc(now_utc: datetime | None = None) -> str:
    """Keyingi kunlik muddat (Toshkent MATCHDAY_UNLOCK_HOUR:MINUTE) — UTC satr, kamida 6 soat keyin."""
    now_utc = now_utc or datetime.now(timezone.utc)
    local = now_utc.astimezone(_LOCAL_TZ)
    cut = local.replace(hour=MATCHDAY_UNLOCK_HOUR, minute=MATCHDAY_UNLOCK_MINUTE, second=0, microsecond=0)
    while cut - local < timedelta(hours=PT_DAILY_MIN_GAP_HOURS):
        cut += timedelta(days=1)
    return cut.astimezone(timezone.utc).strftime(_UTC_FMT)


def pt_set_rounds_per_day(tid: int, user_id: int, n: int) -> tuple[bool, str | dict]:
    """
    Tashkilotchi/admin kuniga turlar sonini tanlaydi.
    Guruh bosqichi ketayotgan bo'lsa va N>0: muddat yo'q bo'lsa — keyingi kunlik muddat qo'yiladi
    (mavjud muddat saqlanadi). Sabablar: bad_value, not_found, not_owner, finished, groups_finished.
    """
    if n not in PT_RPD_CHOICES:
        return False, "bad_value"
    from pt_core import STATUS_RUNNING, is_manager
    from pt_rounds import _tx, members_for_notify, utc_to_local_text

    def run(cursor):
        cursor.execute("SELECT id, name, owner_user_id, status, current_round, total_rounds, round_deadline "
                       "FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        if not t:
            return False, "not_found"
        if not is_manager(cursor, tid, user_id, t["owner_user_id"]):
            return False, "not_owner"
        if t["status"] == "finished":
            return False, "finished"
        running_groups = t["status"] == STATUS_RUNNING and 0 < t["current_round"] <= t["total_rounds"]
        if t["status"] == STATUS_RUNNING and not running_groups:
            return False, "groups_finished"
        deadline = t["round_deadline"]
        new_deadline = running_groups and n > 0 and not deadline
        if new_deadline:
            deadline = next_daily_deadline_utc()
        cursor.execute("UPDATE pt_tournaments SET rounds_per_day = ?, round_deadline = ?, "
                       "updated_at = CURRENT_TIMESTAMP WHERE id = ?", (n, deadline, tid))
        upto = open_upto(t["current_round"], t["total_rounds"], n) if running_groups else None
        return True, {"name": t["name"], "rounds_per_day": n, "new_deadline": bool(new_deadline),
                      "round": round_label(t["current_round"], upto) if upto else None,
                      "deadline_local": utc_to_local_text(deadline),
                      "members": members_for_notify(cursor, tid) if new_deadline or (running_groups and n > 1) else []}
    return _tx(run)
