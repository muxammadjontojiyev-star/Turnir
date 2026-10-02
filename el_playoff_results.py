"""
el_playoff_results.py — YeL play-off natija oqimi (cl_playoff_results naqshi, ALOHIDA).

Oqim: kiritish (pending -> awaiting_confirmation), raqib tasdiqlaydi yoki rad etadi.
Juftlikning IKKALA o'yini tasdiqlangach agregat g'olibi keyingi bosqichga o'tadi
(bir tranzaksiyada — qoida #38). Final — 1 o'yin, g'olib = chempion.

Taqiqlar (server tomonida — qoida #41):
  - Final durang bo'lmaydi (draw_not_allowed).
  - Agregatni teng qiladigan hisob rad etiladi (aggregate_draw_not_allowed) —
    penalti/qo'shimcha vaqt o'yin ichida o'ynaladi, yakuniy hisob kiritiladi.
"""

import logging

from config import (
    MATCH_STATUS_AWAITING_CONFIRMATION,
    MATCH_STATUS_CONFIRMED,
    MATCH_STATUS_PENDING,
)
from el_playoff import EL_PO_FINAL, EL_PO_PLAYIN, EL_PO_ROUNDS, _current_season, _rollback
from models import get_connection

logger = logging.getLogger(__name__)


def _get(cursor, match_id: int) -> dict | None:
    cursor.execute(
        "SELECT id, season, round, position, leg, player1_id, player2_id, "
        "score1, score2, submitted_by, status FROM el_playoff_matches WHERE id = ?",
        (match_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _both_legs(cursor, m: dict) -> tuple[dict | None, dict | None]:
    cursor.execute(
        "SELECT leg, score1, score2, status, player1_id, player2_id "
        "FROM el_playoff_matches WHERE season = ? AND round = ? AND position = ?",
        (m["season"], m["round"], m["position"]),
    )
    legs = {r["leg"]: dict(r) for r in cursor.fetchall()}
    return legs.get(1), legs.get(2)


def _aggregate_would_draw(cursor, m: dict, score1: int, score2: int) -> bool:
    """
    Kiritilayotgan hisob agregatni teng qiladimi? Boshqa leg confirmed bo'lsagina
    tekshiriladi. aggA = leg1.score2 + leg2.score1; aggB = leg1.score1 + leg2.score2.
    """
    leg1, leg2 = _both_legs(cursor, m)
    other = leg1 if m["leg"] == 2 else leg2
    if not other or other["status"] != MATCH_STATUS_CONFIRMED:
        return False
    if m["leg"] == 2:
        agg_a, agg_b = other["score2"] + score1, other["score1"] + score2
    else:
        agg_a, agg_b = score2 + other["score1"], score1 + other["score2"]
    return agg_a == agg_b


def _tie_winner_if_ready(cursor, m: dict) -> int | None:
    """Ikkala o'yin confirmed bo'lsa agregat g'olibi (sideA = leg2.player1), aks holda None."""
    leg1, leg2 = _both_legs(cursor, m)
    if not (leg1 and leg2):
        return None
    if leg1["status"] != MATCH_STATUS_CONFIRMED or leg2["status"] != MATCH_STATUS_CONFIRMED:
        return None
    agg_a = leg1["score2"] + leg2["score1"]
    agg_b = leg1["score1"] + leg2["score2"]
    if agg_a == agg_b:
        return None
    return leg2["player1_id"] if agg_a > agg_b else leg2["player2_id"]


def _ensure_next_tie(cursor, season: int, next_round: str, position: int) -> None:
    """Keyingi juftlikning bo'sh o'yin qatorlarini yaratadi (idempotent). Final — 1 o'yin."""
    sql = ("INSERT OR IGNORE INTO el_playoff_matches "
           "(season, round, position, leg, status) VALUES (?, ?, ?, ?, ?)")
    cursor.execute(sql, (season, next_round, position, 1, MATCH_STATUS_PENDING))
    if next_round != EL_PO_FINAL:
        cursor.execute(sql, (season, next_round, position, 2, MATCH_STATUS_PENDING))


def _set_player(cursor, season: int, rnd: str, pos: int, leg: int, col: str, uid: int) -> None:
    # col faqat KODDAN keladi ('player1_id'/'player2_id') — qoida #29
    cursor.execute(
        f"UPDATE el_playoff_matches SET {col} = ? "
        "WHERE season = ? AND round = ? AND position = ? AND leg = ?",
        (uid, season, rnd, pos, leg),
    )


def _advance_winner(cursor, m: dict, winner_id: int) -> None:
    """
    G'olibni keyingi bosqichga yozadi.
      PLEY-IN: r16 ochilgan bo'lsa, MOS pozitsiyaga sideB (leg1.player1, leg2.player2).
               Ochilmagan bo'lsa hech narsa (setka admin bilan alohida ochiladi).
      Boshqa: pos 2k -> sideA, 2k+1 -> sideB; keyingi pos = pos // 2.
               Final: sideA=player1, sideB=player2.
    """
    season = m["season"]
    if m["round"] == EL_PO_PLAYIN:
        from el_playin import r16_slot_for_playin_position
        first = EL_PO_ROUNDS[0]
        cursor.execute(
            "SELECT COUNT(*) AS n FROM el_playoff_matches WHERE season = ? AND round = ?",
            (season, first))
        if cursor.fetchone()["n"] == 0:
            return
        pos = r16_slot_for_playin_position(m["position"])
        _ensure_next_tie(cursor, season, first, pos)
        _set_player(cursor, season, first, pos, 1, "player1_id", winner_id)
        _set_player(cursor, season, first, pos, 2, "player2_id", winner_id)
        logger.info("YeL PO: pley-in pos%s g'olibi (user %s) -> r16 pos%s",
                    m["position"], winner_id, pos)
        return

    next_round = EL_PO_ROUNDS[EL_PO_ROUNDS.index(m["round"]) + 1]
    next_pos = m["position"] // 2
    _ensure_next_tie(cursor, season, next_round, next_pos)
    goes_side_a = m["position"] % 2 == 0
    if next_round == EL_PO_FINAL:
        _set_player(cursor, season, next_round, next_pos, 1,
                    "player1_id" if goes_side_a else "player2_id", winner_id)
    else:
        _set_player(cursor, season, next_round, next_pos, 1,
                    "player2_id" if goes_side_a else "player1_id", winner_id)
        _set_player(cursor, season, next_round, next_pos, 2,
                    "player1_id" if goes_side_a else "player2_id", winner_id)
    logger.info("YeL PO: %s pos%s g'olibi (user %s) -> %s pos%s",
                m["round"], m["position"], winner_id, next_round, next_pos)


def el_po_submit_result(match_id: int, score1: int, score2: int,
                        user_id: int) -> tuple[bool, str]:
    """Sabablar: not_found, not_participant, wrong_status, draw_not_allowed, aggregate_draw_not_allowed."""
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        m = _get(cursor, match_id)
        reason = None
        if not m:
            reason = "not_found"
        elif (not m["player1_id"] or not m["player2_id"]
              or user_id not in (m["player1_id"], m["player2_id"])):
            reason = "not_participant"
        elif m["status"] != MATCH_STATUS_PENDING:
            reason = "wrong_status"
        elif m["round"] == EL_PO_FINAL and score1 == score2:
            reason = "draw_not_allowed"
        elif m["round"] != EL_PO_FINAL and _aggregate_would_draw(cursor, m, score1, score2):
            reason = "aggregate_draw_not_allowed"
        if reason:
            cursor.execute("ROLLBACK")
            return False, reason

        cursor.execute(
            "UPDATE el_playoff_matches SET score1 = ?, score2 = ?, submitted_by = ?, "
            "status = ? WHERE id = ?",
            (score1, score2, user_id, MATCH_STATUS_AWAITING_CONFIRMATION, match_id),
        )
        cursor.execute("COMMIT")
        return True, "awaiting_confirmation"
    except Exception:
        _rollback(cursor, "el_po_submit_result")
        raise
    finally:
        conn.close()


def el_po_confirm_result(match_id: int, user_id: int, accept: bool) -> tuple[bool, str]:
    """
    Tasdiqlash yoki rad etish. Sabablar: not_found, not_participant, wrong_status,
    cannot_confirm_own, aggregate_draw_not_allowed. Javob: confirmed | rejected.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        m = _get(cursor, match_id)
        reason = None
        if not m:
            reason = "not_found"
        elif user_id not in (m["player1_id"], m["player2_id"]):
            reason = "not_participant"
        elif m["status"] != MATCH_STATUS_AWAITING_CONFIRMATION:
            reason = "wrong_status"
        elif m["submitted_by"] == user_id:
            reason = "cannot_confirm_own"
        if reason:
            cursor.execute("ROLLBACK")
            return False, reason

        if not accept:
            cursor.execute(
                "UPDATE el_playoff_matches SET score1 = NULL, score2 = NULL, "
                "submitted_by = NULL, status = ? WHERE id = ?",
                (MATCH_STATUS_PENDING, match_id),
            )
            cursor.execute("COMMIT")
            return True, "rejected"

        if m["round"] != EL_PO_FINAL and _aggregate_would_draw(cursor, m, m["score1"], m["score2"]):
            cursor.execute("ROLLBACK")
            return False, "aggregate_draw_not_allowed"

        cursor.execute("UPDATE el_playoff_matches SET status = ? WHERE id = ?",
                       (MATCH_STATUS_CONFIRMED, match_id))
        if m["round"] != EL_PO_FINAL:
            winner = _tie_winner_if_ready(cursor, m)
            if winner is not None:
                _advance_winner(cursor, m, winner)
        cursor.execute("COMMIT")
        return True, "confirmed"
    except Exception:
        _rollback(cursor, "el_po_confirm_result")
        raise
    finally:
        conn.close()


def el_po_auto_confirm_awaiting(season: int | None = None) -> dict:
    """
    Deadline (23:30): FAQAT awaiting -> confirmed (pending TEGILMAYDI — play-off'da
    0:0 durang yo'q, admin hal qiladi). Har juftlik hal bo'lsa g'olib o'tadi.
    Idempotent. Qaytaradi: {"confirmed", "advanced"}.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_season(cursor)
        cursor.execute("SELECT started FROM el_playoff_state WHERE season = ?", (season,))
        st = cursor.fetchone()
        cursor.execute(
            "SELECT id, season, round, position, leg FROM el_playoff_matches "
            "WHERE season = ? AND status = ?",
            (season, MATCH_STATUS_AWAITING_CONFIRMATION),
        )
        awaiting = [dict(r) for r in cursor.fetchall()]
        if not (st and st["started"]) or not awaiting:
            cursor.execute("ROLLBACK")
            return {"confirmed": 0, "advanced": 0}

        cursor.execute(
            "UPDATE el_playoff_matches SET status = ? WHERE season = ? AND status = ?",
            (MATCH_STATUS_CONFIRMED, season, MATCH_STATUS_AWAITING_CONFIRMATION),
        )
        confirmed = cursor.rowcount or 0

        advanced = 0
        seen: set[tuple] = set()
        for m in awaiting:
            key = (m["round"], m["position"])
            if m["round"] == EL_PO_FINAL or key in seen:
                continue
            seen.add(key)
            winner = _tie_winner_if_ready(cursor, m)
            if winner is not None:
                _advance_winner(cursor, m, winner)
                advanced += 1
        cursor.execute("COMMIT")
        logger.info("YeL play-off deadline: %s awaiting -> confirmed, %s juftlik o'tdi.",
                    confirmed, advanced)
        return {"confirmed": confirmed, "advanced": advanced}
    except Exception:
        _rollback(cursor, "el_po_auto_confirm_awaiting")
        raise
    finally:
        conn.close()
