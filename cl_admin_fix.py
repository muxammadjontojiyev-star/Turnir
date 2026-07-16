"""
cl_admin_fix.py — ChL admin: tasdiqlangan natijani tuzatish (liga naqshi).

Match ID orqali:
  cl_admin_get_match_info(id) — o'yinchilar, klublar (logo uchun), hisob, tur.
  cl_admin_set_result(id, s1, s2) — istalgan statusdan -> confirmed (tuzatish).

Klub nomi COALESCE(registrations, cl_participants) — ligada keyin logo tanlaganlar ham.
"""

import logging

from models import get_connection
from config import MATCH_STATUS_CONFIRMED

logger = logging.getLogger(__name__)


def cl_admin_get_match_info(match_id: int) -> dict | None:
    """
    {id, matchday, group_number, status, score1, score2,
     player1_id, player1_name, player1_username, player1_club,
     player2_id, player2_name, player2_username, player2_club}
    Topilmasa None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT m.id, m.matchday, m.group_number, m.status, m.score1, m.score2,
                   m.player1_id, m.player2_id,
                   u1.nickname AS player1_name, u2.nickname AS player2_name,
                   u1.username AS player1_username, u2.username AS player2_username,
                   COALESCE(r1.club_name, c1.club_name) AS player1_club,
                   COALESCE(r2.club_name, c2.club_name) AS player2_club
            FROM cl_matches m
            JOIN users u1 ON u1.id = m.player1_id
            JOIN users u2 ON u2.id = m.player2_id
            LEFT JOIN cl_participants c1
                   ON c1.user_id = m.player1_id AND c1.season = m.season
            LEFT JOIN cl_participants c2
                   ON c2.user_id = m.player2_id AND c2.season = m.season
            LEFT JOIN registrations r1 ON r1.user_id = m.player1_id
            LEFT JOIN registrations r2 ON r2.user_id = m.player2_id
            WHERE m.id = ?
            """,
            (match_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def cl_admin_cancel_match(match_id: int) -> tuple[bool, str]:
    """
    2026-07-16: Admin NATIJANI BEKOR QILADI — o'yin natija kiritilmagan
    holatga qaytadi: status='pending', score1/score2/submitted_by NULL
    (liga admin_cancel_match / divizion naqshi). Istalgan statusdan ishlaydi.
    Sabab: ok, match_not_found.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id FROM cl_matches WHERE id = ?", (match_id,))
        if not cursor.fetchone():
            cursor.execute("ROLLBACK")
            return False, "match_not_found"

        cursor.execute(
            "UPDATE cl_matches SET score1=NULL, score2=NULL, "
            "submitted_by=NULL, status='pending' WHERE id=?",
            (match_id,),
        )
        cursor.execute("COMMIT")
        logger.info("ChL admin natijani bekor qildi: match %s -> pending", match_id)
        return True, "ok"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def cl_admin_set_result(match_id: int, score1: int, score2: int
                        ) -> tuple[bool, str]:
    """
    Natijani o'rnatadi/tuzatadi: istalgan statusdan -> confirmed.
    Sabab: match_not_found.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id FROM cl_matches WHERE id = ?", (match_id,))
        if not cursor.fetchone():
            cursor.execute("ROLLBACK")
            return False, "match_not_found"

        cursor.execute(
            "UPDATE cl_matches SET score1 = ?, score2 = ?, status = ? WHERE id = ?",
            (score1, score2, MATCH_STATUS_CONFIRMED, match_id),
        )
        cursor.execute("COMMIT")
        logger.info("ChL admin natija tuzatdi: match %s -> %s:%s", match_id, score1, score2)
        return True, "ok"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
