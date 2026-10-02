"""
Yevropa ligasi liga bosqichi o'yinlari: natija kiritish/tasdiqlash.
cl_matches_queries.py naqshi, ALOHIDA nusxa (ChL'ga tegilmaydi).

Oqim (ChL/WC bilan bir xil):
  pending -> (submit) -> awaiting_confirmation | admin_pending (katta hisob)
  awaiting_confirmation -> (raqib confirm) -> confirmed
  awaiting_confirmation -> (raqib reject)  -> pending (score NULL, qayta kiritiladi)
Faqat o'yin ishtirokchilari harakat qila oladi (qoida #34).
Status yangilanishi SHARTLI (WHERE status = ...) — ikki marta bosish yoki
parallel so'rov ikki marta yozmaydi (qoida #38).
"""

from models import get_connection
from queries_matches import _result_status_for


def el_get_match_by_id(match_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, season, group_number, matchday, player1_id, player2_id, "
            "score1, score2, status, submitted_by FROM el_matches WHERE id = ?",
            (match_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def el_get_user_matches(user_id: int, season: int) -> list[dict]:
    """Foydalanuvchining YeL o'yinlari (raqib nomi, username, klubi bilan), tur tartibida."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT m.id, m.season, m.group_number, m.matchday, m.player1_id, m.player2_id,
                   m.score1, m.score2, m.status, m.submitted_by,
                   u1.nickname AS player1_name, u2.nickname AS player2_name,
                   u1.username AS player1_username, u2.username AS player2_username,
                   COALESCE(rg1.club_name, e1.club_name) AS player1_club,
                   COALESCE(rg2.club_name, e2.club_name) AS player2_club
            FROM el_matches m
            JOIN users u1 ON u1.id = m.player1_id
            JOIN users u2 ON u2.id = m.player2_id
            LEFT JOIN el_participants e1 ON e1.user_id = m.player1_id AND e1.season = m.season
            LEFT JOIN el_participants e2 ON e2.user_id = m.player2_id AND e2.season = m.season
            LEFT JOIN registrations rg1 ON rg1.user_id = m.player1_id
            LEFT JOIN registrations rg2 ON rg2.user_id = m.player2_id
            WHERE m.season = ? AND (m.player1_id = ? OR m.player2_id = ?)
            ORDER BY m.matchday, m.id
            """,
            (season, user_id, user_id),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def el_submit_match_result(match_id: int, score1: int, score2: int,
                           submitted_by: int) -> tuple[bool, str]:
    """Sabablar: ok, ok_admin_pending, match_not_found, not_participant, already_submitted"""
    match = el_get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"
    if submitted_by not in (match["player1_id"], match["player2_id"]):
        return False, "not_participant"
    if match["status"] != "pending":
        return False, "already_submitted"

    new_status = _result_status_for(score1, score2)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE el_matches SET score1 = ?, score2 = ?, submitted_by = ?, status = ? "
            "WHERE id = ? AND status = 'pending'",
            (score1, score2, submitted_by, new_status, match_id),
        )
        changed = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    if not changed:   # parallel so'rov oldinroq yozib ulgurgan
        return False, "already_submitted"
    return True, ("ok_admin_pending" if new_status == "admin_pending" else "ok")


def el_confirm_or_reject_match(match_id: int, action: str,
                               confirmed_by: int) -> tuple[bool, str]:
    """
    Sabablar: ok, match_not_found, wrong_status, not_opponent, invalid_action
    reject -> pending + score NULL (qayta kiritish mumkin).
    """
    match = el_get_match_by_id(match_id)
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
    try:
        if action == "confirm":
            cursor.execute(
                "UPDATE el_matches SET status = 'confirmed' "
                "WHERE id = ? AND status = 'awaiting_confirmation'", (match_id,))
        else:
            cursor.execute(
                "UPDATE el_matches SET status = 'pending', score1 = NULL, "
                "score2 = NULL, submitted_by = NULL "
                "WHERE id = ? AND status = 'awaiting_confirmation'", (match_id,))
        changed = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    if not changed:
        return False, "wrong_status"
    return True, "ok"
