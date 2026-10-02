"""
el_admin_fix.py — YeL admin: liga bosqichi natijasini tuzatish / bekor qilish.
cl_admin_fix.py (guruh qismi) naqshi, ALOHIDA nusxa. Play-off qismi 4-bosqichda.

  el_admin_get_match_info(id) — o'yinchilar, klublar (logo uchun), hisob, tur.
  el_admin_set_result(id, s1, s2) — istalgan statusdan -> confirmed. Katta hisob
      (admin_pending) ham SHU bilan hal qilinadi (ChL bilan bir xil).
  el_admin_cancel_match(id) — natijani bekor qiladi (pending, hisob NULL).
Ruxsat endpoint darajasida: bosh admin yoki 'el' scope admini.
"""

import logging

from config import MATCH_STATUS_CONFIRMED, MATCH_STATUS_PENDING
from models import get_connection

logger = logging.getLogger(__name__)


def el_admin_get_match_info(match_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT m.id, m.matchday, m.group_number, m.status, m.score1, m.score2,
                   m.player1_id, m.player2_id,
                   u1.nickname AS player1_name, u2.nickname AS player2_name,
                   u1.username AS player1_username, u2.username AS player2_username,
                   COALESCE(r1.club_name, e1.club_name) AS player1_club,
                   COALESCE(r2.club_name, e2.club_name) AS player2_club
            FROM el_matches m
            JOIN users u1 ON u1.id = m.player1_id
            JOIN users u2 ON u2.id = m.player2_id
            LEFT JOIN el_participants e1 ON e1.user_id = m.player1_id AND e1.season = m.season
            LEFT JOIN el_participants e2 ON e2.user_id = m.player2_id AND e2.season = m.season
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


def _admin_update(match_id: int, sql: str, params: tuple, log_msg: str) -> tuple[bool, str]:
    """Umumiy: o'yin borligini tekshirib, bitta UPDATE (BEGIN IMMEDIATE). DRY (qoida #26)."""
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id FROM el_matches WHERE id = ?", (match_id,))
        if not cursor.fetchone():
            cursor.execute("ROLLBACK")
            return False, "match_not_found"
        cursor.execute(sql, (*params, match_id))
        cursor.execute("COMMIT")
        logger.info(log_msg)
        return True, "ok"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("el_admin: ROLLBACK xatosi (match %s)", match_id)
        raise
    finally:
        conn.close()


def el_admin_set_result(match_id: int, score1: int, score2: int) -> tuple[bool, str]:
    """Natijani o'rnatadi/tuzatadi -> confirmed. Sabab: ok, match_not_found."""
    return _admin_update(
        match_id,
        "UPDATE el_matches SET score1 = ?, score2 = ?, status = ? WHERE id = ?",
        (score1, score2, MATCH_STATUS_CONFIRMED),
        f"YeL admin natija tuzatdi: match {match_id} -> {score1}:{score2}",
    )


def el_admin_cancel_match(match_id: int) -> tuple[bool, str]:
    """Natijani bekor qiladi -> pending, hisob/submitted_by NULL. Sabab: ok, match_not_found."""
    return _admin_update(
        match_id,
        "UPDATE el_matches SET score1 = NULL, score2 = NULL, submitted_by = NULL, "
        "status = ? WHERE id = ?",
        (MATCH_STATUS_PENDING,),
        f"YeL admin natijani bekor qildi: match {match_id} -> pending",
    )
