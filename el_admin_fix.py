"""
el_admin_fix.py — YeL admin: liga bosqichi natijasini tuzatish / bekor qilish.
cl_admin_fix.py naqshi, ALOHIDA nusxa.

  el_admin_get_match_info(id) — o'yinchilar, klublar (logo uchun), hisob, tur.
  el_admin_set_result(id, s1, s2) — istalgan statusdan -> confirmed. Katta hisob
      (admin_pending) ham SHU bilan hal qilinadi (ChL bilan bir xil).
  el_admin_cancel_match(id) — natijani bekor qiladi (pending, hisob NULL).
PLAY-OFF (el_playoff_matches):
  el_admin_po_get_match_info(id) — guruh info shakli + round/round_label/leg, is_playoff=1.
  el_admin_po_set_result(id, s1, s2) — confirmed; ikkala leg tayyor bo'lsa g'olib
      keyingi bosqichga yoziladi (el_playoff_results qayta ishlatiladi — DRY). G'olib
      o'zgarsa keyingi slot qayta yoziladi. Final durang / agregat teng — rad.
  el_admin_po_cancel_match(id) — pending; keyingi bosqichga o'tgan g'olib
      avtomatik olinmaydi (ChL bilan bir xil — kaskad yo'q, admin qo'lda tuzatadi).
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


def _admin_update(match_id: int, sql: str, params: tuple, log_msg: str,
                  table: str = "el_matches") -> tuple[bool, str]:
    """Umumiy: o'yin borligini tekshirib, bitta UPDATE (BEGIN IMMEDIATE). DRY (qoida #26).
    table faqat KODDAN keladi (qoida #29)."""
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(f"SELECT id FROM {table} WHERE id = ?", (match_id,))
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


# ============================================================
#  PLAY-OFF (el_playoff_matches)
# ============================================================

_PO_ROUND_UZ = {"playin": "Pley-in", "r16": "1/8 final", "r8": "1/4 final",
                "r4": "1/2 final", "final": "Final"}


def el_admin_po_get_match_info(match_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT m.id, m.round, m.position, m.leg, m.status, m.score1, m.score2,
                   m.player1_id, m.player2_id,
                   u1.nickname AS player1_name, u2.nickname AS player2_name,
                   u1.username AS player1_username, u2.username AS player2_username,
                   COALESCE(r1.club_name, e1.club_name) AS player1_club,
                   COALESCE(r2.club_name, e2.club_name) AS player2_club
            FROM el_playoff_matches m
            LEFT JOIN users u1 ON u1.id = m.player1_id
            LEFT JOIN users u2 ON u2.id = m.player2_id
            LEFT JOIN el_participants e1 ON e1.user_id = m.player1_id AND e1.season = m.season
            LEFT JOIN el_participants e2 ON e2.user_id = m.player2_id AND e2.season = m.season
            LEFT JOIN registrations r1 ON r1.user_id = m.player1_id
            LEFT JOIN registrations r2 ON r2.user_id = m.player2_id
            WHERE m.id = ?
            """,
            (match_id,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    info = dict(row)
    info.update({"matchday": None, "group_number": None, "is_playoff": 1,
                 "round_label": _PO_ROUND_UZ.get(info["round"], info["round"])})
    return info


def el_admin_po_set_result(match_id: int, score1: int, score2: int) -> tuple[bool, str]:
    """Sabablar: ok / match_not_found / draw_not_allowed / aggregate_draw_not_allowed"""
    from el_playoff import EL_PO_FINAL
    from el_playoff_results import _advance_winner, _aggregate_would_draw, _tie_winner_if_ready

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT id, season, round, position, leg, player1_id, player2_id "
            "FROM el_playoff_matches WHERE id = ?", (match_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("ROLLBACK")
            return False, "match_not_found"
        m = dict(row)
        if m["round"] == EL_PO_FINAL and score1 == score2:
            cursor.execute("ROLLBACK")
            return False, "draw_not_allowed"
        if m["round"] != EL_PO_FINAL and _aggregate_would_draw(cursor, m, score1, score2):
            cursor.execute("ROLLBACK")
            return False, "aggregate_draw_not_allowed"

        cursor.execute(
            "UPDATE el_playoff_matches SET score1 = ?, score2 = ?, status = ? WHERE id = ?",
            (score1, score2, MATCH_STATUS_CONFIRMED, match_id),
        )
        if m["round"] != EL_PO_FINAL:
            winner = _tie_winner_if_ready(cursor, m)
            if winner is not None:
                _advance_winner(cursor, m, winner)
        cursor.execute("COMMIT")
        logger.info("YeL admin PO natija tuzatdi: match %s -> %s:%s (%s leg%s)",
                    match_id, score1, score2, m["round"], m["leg"])
        return True, "ok"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("el_admin_po_set_result: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def el_admin_po_cancel_match(match_id: int) -> tuple[bool, str]:
    """Play-off natijasini bekor qiladi -> pending. Sabab: ok, match_not_found."""
    return _admin_update(
        match_id,
        "UPDATE el_playoff_matches SET score1 = NULL, score2 = NULL, submitted_by = NULL, "
        "status = ? WHERE id = ?",
        (MATCH_STATUS_PENDING,),
        f"YeL admin PO natijani bekor qildi: match {match_id} -> pending",
        table="el_playoff_matches",
    )
