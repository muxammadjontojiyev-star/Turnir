"""
ChL guruh o'yinlari: natija kiritish/tasdiqlash.

Oqim WC (queries_wc_matches) bilan bir xil (qoida #10 — parallel joylar sinxron):
  pending -> (submit) -> awaiting_confirmation | admin_pending (katta hisob)
  awaiting_confirmation -> (raqib confirm) -> confirmed
  awaiting_confirmation -> (raqib reject)  -> pending (score NULL, qayta kiritiladi)
Faqat o'yin ishtirokchilari harakat qila oladi (qoida #34).
"""

from models import get_connection
from queries_matches import _result_status_for


def cl_get_match_by_id(match_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cl_matches WHERE id = ?", (match_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def cl_get_user_matches(user_id: int, season: int) -> list[dict]:
    """Foydalanuvchining ChL o'yinlari (raqib nomi bilan), matchday tartibida."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.*, u1.nickname AS player1_name, u2.nickname AS player2_name,
               c1.club_name AS player1_club, c2.club_name AS player2_club
        FROM cl_matches m
        JOIN users u1 ON u1.id = m.player1_id
        JOIN users u2 ON u2.id = m.player2_id
        LEFT JOIN cl_participants c1
               ON c1.user_id = m.player1_id AND c1.season = m.season
        LEFT JOIN cl_participants c2
               ON c2.user_id = m.player2_id AND c2.season = m.season
        WHERE m.season = ? AND (m.player1_id = ? OR m.player2_id = ?)
        ORDER BY m.matchday, m.id
        """,
        (season, user_id, user_id),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def cl_submit_match_result(match_id: int, score1: int, score2: int,
                           submitted_by: int) -> tuple[bool, str]:
    """
    Sabablar: ok, ok_admin_pending, match_not_found, not_participant,
    already_submitted
    """
    match = cl_get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"
    if submitted_by not in (match["player1_id"], match["player2_id"]):
        return False, "not_participant"
    if match["status"] != "pending":
        return False, "already_submitted"

    new_status = _result_status_for(score1, score2)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE cl_matches SET score1 = ?, score2 = ?, submitted_by = ?, status = ? "
        "WHERE id = ?",
        (score1, score2, submitted_by, new_status, match_id),
    )
    conn.commit()
    conn.close()
    return True, ("ok_admin_pending" if new_status == "admin_pending" else "ok")


def cl_confirm_or_reject_match(match_id: int, action: str,
                               confirmed_by: int) -> tuple[bool, str]:
    """
    Sabablar: ok, match_not_found, wrong_status, not_opponent, invalid_action
    reject -> pending + score NULL (qayta kiritish mumkin).
    """
    match = cl_get_match_by_id(match_id)
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
        cursor.execute("UPDATE cl_matches SET status = 'confirmed' WHERE id = ?",
                       (match_id,))
    else:
        cursor.execute(
            "UPDATE cl_matches SET status = 'pending', score1 = NULL, "
            "score2 = NULL, submitted_by = NULL WHERE id = ?",
            (match_id,),
        )
    conn.commit()
    conn.close()
    return True, "ok"
