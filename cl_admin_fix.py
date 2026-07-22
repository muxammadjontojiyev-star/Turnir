"""
cl_admin_fix.py — ChL admin: tasdiqlangan natijani tuzatish (liga naqshi).

GURUH o'yinlari (cl_matches) — Match ID orqali:
  cl_admin_get_match_info(id) — o'yinchilar, klublar (logo uchun), hisob, tur.
  cl_admin_set_result(id, s1, s2) — istalgan statusdan -> confirmed (tuzatish).
  cl_admin_cancel_match(id) — natijani bekor qiladi (pending, — : —).

PLAY-OFF o'yinlari (cl_playoff_matches) — 2026-07-22, talab 1 (WC namunasidek):
  cl_admin_po_get_match_info(id) — juftlik/bosqich/leg + hisob (logo uchun klub).
  cl_admin_po_set_result(id, s1, s2) — confirmed; 2-o'yin/final bo'lsa g'olibni
    keyingi bosqichga ko'chiradi (mavjud _advance_winner qayta ishlatiladi — DRY).
  cl_admin_po_cancel_match(id) — natijani bekor qiladi (pending, — : —).

Klub nomi COALESCE(registrations, cl_participants) — ligada keyin logo tanlaganlar ham.
"""

import logging

from models import get_connection
from config import MATCH_STATUS_CONFIRMED, MATCH_STATUS_PENDING

logger = logging.getLogger(__name__)

# Play-off bosqich nomlari (frontend ko'rsatuvi uchun) — cl_playoff.js bilan mos
_CL_PO_ROUND_UZ = {"r16": "1/8 final", "r8": "1/4 final",
                   "r4": "1/2 final", "final": "Final"}


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


# ============================================================
#  PLAY-OFF (cl_playoff_matches) — admin tuzatish (talab 1, WC namunasidek)
# ============================================================

def cl_admin_po_get_match_info(match_id: int) -> dict | None:
    """
    Play-off o'yin ma'lumoti (admin 'Match ID orqali tuzatish' formasi, checkbox
    yoqilganda). Guruh info naqshi bilan bir xil shakl — frontend bir xil
    preview'ni chizadi. Qo'shimcha: round_label + leg (agregat konteksti uchun).

    {id, matchday(=None), group_number(=None), round, round_label, leg, status,
     score1, score2, player1_id/name/username/club, player2_...}
    Topilmasa None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT m.id, m.round, m.position, m.leg, m.status, m.score1, m.score2,
                   m.player1_id, m.player2_id,
                   u1.nickname AS player1_name, u2.nickname AS player2_name,
                   u1.username AS player1_username, u2.username AS player2_username,
                   COALESCE(r1.club_name, c1.club_name) AS player1_club,
                   COALESCE(r2.club_name, c2.club_name) AS player2_club
            FROM cl_playoff_matches m
            LEFT JOIN users u1 ON u1.id = m.player1_id
            LEFT JOIN users u2 ON u2.id = m.player2_id
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
        if not row:
            return None
        info = dict(row)
        # Frontend guruh preview naqshiga moslash: matchday/group_number o'rniga bosqich
        info["matchday"] = None
        info["group_number"] = None
        info["round_label"] = _CL_PO_ROUND_UZ.get(info["round"], info["round"])
        info["is_playoff"] = 1
        return info
    finally:
        conn.close()


def cl_admin_po_set_result(match_id: int, score1: int, score2: int
                           ) -> tuple[bool, str]:
    """
    Play-off natijasini o'rnatadi/tuzatadi: istalgan statusdan -> confirmed.
    So'ng, IKKALA o'yin (uy+mehmon) confirmed bo'lsa — agregat g'olibini keyingi
    bosqichga ko'chiradi (cl_playoff_results._tie_winner_if_ready/_advance_winner
    qayta ishlatiladi — DRY; g'olib o'zgarsa keyingi slot idempotent qayta yoziladi).

    Ehtiyot (qoida #41): final durang bo'lmaydi; istalgan o'yinni tuzatish juftlik
    agregatini teng qilsa rad etiladi (eFootballda penalti/extra-time o'yin ichida).

    Sabablar: ok / match_not_found / draw_not_allowed / aggregate_draw_not_allowed
    """
    from cl_playoff_results import _aggregate_would_draw, _tie_winner_if_ready, _advance_winner

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT id, season, round, position, leg, player1_id, player2_id "
            "FROM cl_playoff_matches WHERE id = ?",
            (match_id,),
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute("ROLLBACK")
            return False, "match_not_found"
        m = dict(row)

        # Final durang bo'lmaydi
        if m["round"] == "final" and score1 == score2:
            cursor.execute("ROLLBACK")
            return False, "draw_not_allowed"

        # Istalgan o'yinni tuzatish juftlik agregatini teng qilmasin (ikkala leg ochiq)
        if m["round"] != "final" and _aggregate_would_draw(cursor, m, score1, score2):
            cursor.execute("ROLLBACK")
            return False, "aggregate_draw_not_allowed"

        cursor.execute(
            "UPDATE cl_playoff_matches SET score1 = ?, score2 = ?, status = ? "
            "WHERE id = ?",
            (score1, score2, MATCH_STATUS_CONFIRMED, match_id),
        )

        # G'olibni keyingi bosqichga ko'chirish — IKKALA o'yin confirmed bo'lganda
        # (final — chempion bracket'da hisoblanadi). Idempotent: _advance_winner
        # keyingi slotni bir xil g'olib bilan qayta yozadi (g'olib o'zgarsa — tuzatadi).
        if m["round"] != "final":
            winner = _tie_winner_if_ready(cursor, m)
            if winner is not None:
                _advance_winner(cursor, m, winner)

        cursor.execute("COMMIT")
        logger.info("ChL admin PO natija tuzatdi: match %s -> %s:%s (%s leg%s)",
                    match_id, score1, score2, m["round"], m["leg"])
        return True, "ok"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def cl_admin_po_cancel_match(match_id: int) -> tuple[bool, str]:
    """
    Play-off natijasini BEKOR qiladi: pending, hisob NULL (guruh
    cl_admin_cancel_match naqshi). Istalgan statusdan ishlaydi.
    DIQQAT: keyingi bosqichga o'tgan g'olib avtomatik olib tashlanmaydi —
    admin xohlasa keyingi o'yinni ham qo'lda tuzatadi (guruh naqshi bilan bir xil,
    kaskad o'zgartirish qilinmaydi — qoida #4).

    Sabablar: ok / match_not_found
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id FROM cl_playoff_matches WHERE id = ?", (match_id,))
        if not cursor.fetchone():
            cursor.execute("ROLLBACK")
            return False, "match_not_found"
        cursor.execute(
            "UPDATE cl_playoff_matches SET score1=NULL, score2=NULL, "
            "submitted_by=NULL, status=? WHERE id=?",
            (MATCH_STATUS_PENDING, match_id),
        )
        cursor.execute("COMMIT")
        logger.info("ChL admin PO natijani bekor qildi: match %s -> pending", match_id)
        return True, "ok"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
