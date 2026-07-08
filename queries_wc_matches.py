"""
queries_wc_matches.py — WC guruh o'yinlari: ochiq tur, natija kiritish/tasdiqlash, deadline + avtomatik 0:0.

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from datetime import datetime, timedelta
from models import get_connection
from config import (
    MATCHDAY_UNLOCK_HOUR,
    MATCHDAY_UNLOCK_MINUTE,
    MATCHDAYS_PER_UNLOCK,
)
from queries_leagues import _parse_draw_date, _tournament_now
from queries_wc import wc_get_group


# ============================================================
#  WORLD CUP — o'yinlar, matchday-lock, natija kiritish/tasdiqlash
# ============================================================

# WC guruhda 4 jamoa -> 3 tur (matchday). Liga TOTAL_MATCHDAYS (38) emas.
WC_TOTAL_MATCHDAYS = 3


def wc_get_open_matchday(group_letter: str) -> int:
    """
    Shu WC guruh uchun hozir ochiq eng yuqori matchday raqami (liga
    get_open_matchday mantig'i, lekin guruh draw_date va WC_TOTAL_MATCHDAYS bo'yicha).

    draw_date yo'q bo'lsa (guruh to'lmagan/o'yin yo'q) — 0.
    """
    grp = wc_get_group(group_letter)
    if grp is None:
        return 0
    draw_dt = _parse_draw_date(grp["draw_date"] if "draw_date" in grp.keys() else None)
    if draw_dt is None:
        return 0

    now = _tournament_now()

    def unlock_day(d: datetime):
        shifted = d - timedelta(hours=MATCHDAY_UNLOCK_HOUR, minutes=MATCHDAY_UNLOCK_MINUTE)
        return shifted.date()

    days_passed = (unlock_day(now) - unlock_day(draw_dt)).days
    open_count = (1 + days_passed) * MATCHDAYS_PER_UNLOCK

    if open_count < 1:
        return 0
    if open_count > WC_TOTAL_MATCHDAYS:
        return WC_TOTAL_MATCHDAYS
    return open_count


def wc_get_user_matches(user_id: int) -> list[dict]:
    """
    Foydalanuvchining WC o'yinlari (player1 yoki player2). Raqib jamoa nomi,
    username, telegram_id bilan (liga get_user_matches kabi).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.*,
               w1.team_name   AS player1_club,
               w2.team_name   AS player2_club,
               u1.telegram_id AS player1_telegram_id,
               u1.username    AS player1_username,
               u1.nickname    AS player1_nickname,
               u2.telegram_id AS player2_telegram_id,
               u2.username    AS player2_username,
               u2.nickname    AS player2_nickname
        FROM wc_matches m
        LEFT JOIN wc_registrations w1 ON w1.user_id = m.player1_id
        LEFT JOIN wc_registrations w2 ON w2.user_id = m.player2_id
        LEFT JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
        WHERE m.player1_id = ? OR m.player2_id = ?
        ORDER BY m.matchday ASC
        """,
        (user_id, user_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def wc_get_match_by_id(match_id: int) -> dict | None:
    """ID bo'yicha WC matchni qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wc_matches WHERE id = ?", (match_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def wc_submit_match_result(match_id: int, score1: int, score2: int, submitted_by: int) -> tuple[bool, str]:
    """
    WC match natijasini kiritadi (liga submit_match_result kabi, lekin matchday-lock
    tekshiruvi bilan: kelajak (yopiq) turlarning natijasi kiritilmaydi).

    Sabablar: ok, match_not_found, not_participant, already_submitted, matchday_locked
    """
    match = wc_get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"
    if submitted_by not in (match["player1_id"], match["player2_id"]):
        return False, "not_participant"
    if match["status"] != "pending":
        return False, "already_submitted"

    # Matchday-lock: faqat ochilgan turlarning natijasi kiritiladi
    open_md = wc_get_open_matchday(match["group_letter"])
    if match["matchday"] > open_md:
        return False, "matchday_locked"

    from queries_matches import _result_status_for
    new_status = _result_status_for(score1, score2)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE wc_matches
        SET score1 = ?, score2 = ?, submitted_by = ?, status = ?
        WHERE id = ?
        """,
        (score1, score2, submitted_by, new_status, match_id),
    )
    conn.commit()
    conn.close()
    return True, ("ok_admin_pending" if new_status == "admin_pending" else "ok")


def wc_confirm_or_reject_match(match_id: int, action: str, confirmed_by: int) -> tuple[bool, str]:
    """
    WC natijani tasdiqlaydi yoki rad etadi (liga confirm_or_reject_match kabi).
    reject -> pending + score NULL (qayta kiritish mumkin).

    Sabablar: ok, match_not_found, not_opponent, wrong_status, invalid_action
    """
    match = wc_get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"
    if match["status"] != "awaiting_confirmation":
        return False, "wrong_status"
    if confirmed_by == match["submitted_by"]:
        return False, "not_opponent"
    if confirmed_by not in (match["player1_id"], match["player2_id"]):
        return False, "not_opponent"
    if action not in ("confirm", "reject"):
        return False, "invalid_action"

    conn = get_connection()
    cursor = conn.cursor()
    if action == "confirm":
        cursor.execute("UPDATE wc_matches SET status = 'confirmed' WHERE id = ?", (match_id,))
    else:
        cursor.execute(
            """
            UPDATE wc_matches
            SET status = 'pending', score1 = NULL, score2 = NULL, submitted_by = NULL
            WHERE id = ?
            """,
            (match_id,),
        )
    conn.commit()
    conn.close()
    return True, "ok"


def wc_admin_resolve_pending(match_id: int, action: str) -> tuple[bool, str]:
    """
    Bosh admin katta hisobli (admin_pending) WC guruh o'yinini tasdiqlaydi/rad etadi.
    Liga admin_resolve_pending kabi. Sabablar: ok, match_not_found, wrong_status, invalid_action
    """
    if action not in ("confirm", "reject"):
        return False, "invalid_action"
    match = wc_get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"
    if match["status"] != "admin_pending":
        return False, "wrong_status"

    conn = get_connection()
    cursor = conn.cursor()
    if action == "confirm":
        cursor.execute("UPDATE wc_matches SET status = 'confirmed' WHERE id = ?", (match_id,))
    else:
        cursor.execute(
            "UPDATE wc_matches SET status = 'pending', score1 = NULL, score2 = NULL, "
            "submitted_by = NULL WHERE id = ?",
            (match_id,),
        )
    conn.commit()
    conn.close()
    return True, "ok"


def wc_get_admin_pending_matches() -> list[dict]:
    """
    Barcha WC guruhlar bo'ylab admin tasdig'ini kutayotgan (admin_pending) o'yinlar.
    Eng yangisi (id DESC) birinchi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT w.id, w.group_letter, w.matchday, w.player1_id, w.player2_id,
               w.score1, w.score2, w.submitted_by,
               u1.nickname AS p1_nick, u1.username AS p1_user, r1.team_name AS p1_team,
               u2.nickname AS p2_nick, u2.username AS p2_user, r2.team_name AS p2_team
        FROM wc_matches w
        LEFT JOIN users u1 ON u1.id = w.player1_id
        LEFT JOIN users u2 ON u2.id = w.player2_id
        LEFT JOIN wc_registrations r1 ON r1.user_id = w.player1_id
        LEFT JOIN wc_registrations r2 ON r2.user_id = w.player2_id
        WHERE w.status = 'admin_pending'
        ORDER BY w.id DESC
        """
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ---- WC guruh: deadline o'tgan matchday + avtomatik 0:0 yopish ----

def wc_get_deadline_passed_matchday(group_letter: str) -> int:
    """
    WC guruh uchun deadline (23:30) o'tgan eng yuqori matchday raqami.
    Liga get_deadline_passed_matchday mantig'i, lekin guruh draw_date bo'yicha.

    days_passed=0 (start kuni): ochiq turlar deadline'i hali o'tmagan → 0.
    days_passed=N: N*MATCHDAYS_PER_UNLOCK tur deadline o'tdi (WC_TOTAL bilan cheklangan).
    """
    grp = wc_get_group(group_letter)
    if grp is None:
        return 0
    draw_dt = _parse_draw_date(grp["draw_date"] if "draw_date" in grp.keys() else None)
    if draw_dt is None:
        return 0

    now = _tournament_now()

    def unlock_day(d: datetime):
        shifted = d - timedelta(hours=MATCHDAY_UNLOCK_HOUR, minutes=MATCHDAY_UNLOCK_MINUTE)
        return shifted.date()

    days_passed = (unlock_day(now) - unlock_day(draw_dt)).days
    if days_passed < 1:
        return 0
    passed = days_passed * MATCHDAYS_PER_UNLOCK
    if passed > WC_TOTAL_MATCHDAYS:
        passed = WC_TOTAL_MATCHDAYS
    return passed


def wc_auto_resolve_group(group_letter: str, up_to_matchday: int) -> dict:
    """
    WC guruhda deadline o'tgan (up_to_matchday gacha) o'ynalmagan o'yinlarni
    avtomatik yopadi. Liga auto_resolve_matches naqshi, wc_matches uchun.

    - 'pending' (hech kim kiritmagan) → 0:0 durang, 'confirmed'.
    - 'awaiting_confirmation' (bir tomon kiritgan) → kiritilgan natija 'confirmed'.

    Qaytaradi: {pending_resolved, awaiting_resolved}
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE wc_matches
        SET score1 = 0, score2 = 0, status = 'confirmed'
        WHERE group_letter = ? AND matchday <= ? AND status = 'pending'
        """,
        (group_letter, up_to_matchday),
    )
    pending_resolved = cursor.rowcount

    cursor.execute(
        """
        UPDATE wc_matches
        SET status = 'confirmed'
        WHERE group_letter = ? AND matchday <= ? AND status = 'awaiting_confirmation'
        """,
        (group_letter, up_to_matchday),
    )
    awaiting_resolved = cursor.rowcount

    conn.commit()
    conn.close()
    return {"pending_resolved": pending_resolved, "awaiting_resolved": awaiting_resolved}


def wc_auto_resolve_all_groups() -> dict:
    """
    Barcha WC guruhlarda deadline o'tgan o'ynalmagan o'yinlarni 0:0 yopadi.
    Scheduler (har kuni) yoki admin tugmasi chaqiradi.

    Qaytaradi: {groups: {harf: {pending_resolved, awaiting_resolved}}, total_pending, total_awaiting}
    """
    from wc_data import WC_GROUP_LETTERS

    result = {}
    total_p = 0
    total_a = 0
    for letter in WC_GROUP_LETTERS:
        up_to = wc_get_deadline_passed_matchday(letter)
        if up_to < 1:
            continue
        r = wc_auto_resolve_group(letter, up_to)
        if r["pending_resolved"] or r["awaiting_resolved"]:
            result[letter] = r
            total_p += r["pending_resolved"]
            total_a += r["awaiting_resolved"]
    return {"groups": result, "total_pending": total_p, "total_awaiting": total_a}
