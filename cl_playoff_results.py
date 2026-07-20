"""
cl_playoff_results.py — ChL play-off natija oqimi (2026-07-20).

Oqim (guruh o'yinlari bilan bir xil): bir ishtirokchi natija kiritadi
(pending → awaiting_confirmation), raqib tasdiqlaydi yoki rad etadi.

Tasdiqlangach (bir tranzaksiyada — qoida #38):
  - 1-o'yin (final emas) → 2-o'yin yaratiladi (uy/mehmon almashadi).
  - 2-o'yin → agregat g'olibi keyingi bosqich juftligiga yoziladi.
  - Final → g'olib = chempion (cl_playoff.cl_po_bracket hisoblaydi).

Taqiqlar (server tomonida — qoida #41):
  - Final durang bo'lmaydi (draw_not_allowed).
  - 2-o'yin natijasi agregatni teng qilsa rad etiladi
    (aggregate_draw_not_allowed) — eFootball'da penalti/qo'shimcha vaqt
    o'yin ichida o'ynaladi, yakuniy hisob kiritiladi.
"""

import logging

from models import get_connection
from config import (
    MATCH_STATUS_PENDING,
    MATCH_STATUS_AWAITING_CONFIRMATION,
    MATCH_STATUS_CONFIRMED,
)
from cl_playoff import CL_PO_ROUNDS

logger = logging.getLogger(__name__)


def _get(cursor, match_id: int) -> dict | None:
    cursor.execute(
        "SELECT id, season, round, position, leg, player1_id, player2_id, "
        "score1, score2, submitted_by, status "
        "FROM cl_playoff_matches WHERE id = ?",
        (match_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _leg1_of(cursor, m: dict) -> dict | None:
    cursor.execute(
        "SELECT score1, score2, status FROM cl_playoff_matches "
        "WHERE season = ? AND round = ? AND position = ? AND leg = 1",
        (m["season"], m["round"], m["position"]),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _aggregate_would_draw(cursor, m: dict, score1: int, score2: int) -> bool:
    """2-o'yin uchun: kiritilayotgan hisob agregatni teng qiladimi?
    leg2: player1=sideA(uyda), player2=sideB. leg1: player1=sideB, player2=sideA.
    aggA = leg1.score2 + score1;  aggB = leg1.score1 + score2."""
    leg1 = _leg1_of(cursor, m)
    if not leg1 or leg1["status"] != MATCH_STATUS_CONFIRMED:
        return False  # bo'lmasligi kerak (leg2 faqat leg1'dan keyin yaratiladi)
    agg_a = leg1["score2"] + score1
    agg_b = leg1["score1"] + score2
    return agg_a == agg_b


def cl_po_submit_result(match_id: int, score1: int, score2: int,
                        user_id: int) -> tuple[bool, str]:
    """
    Natija kiritish. Xato sabablari: not_found, not_participant, wrong_status,
    draw_not_allowed (final), aggregate_draw_not_allowed (2-o'yin).
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        m = _get(cursor, match_id)
        if not m:
            cursor.execute("ROLLBACK"); return False, "not_found"
        if user_id not in (m["player1_id"], m["player2_id"]) or not m["player1_id"] or not m["player2_id"]:
            cursor.execute("ROLLBACK"); return False, "not_participant"
        if m["status"] != MATCH_STATUS_PENDING:
            cursor.execute("ROLLBACK"); return False, "wrong_status"
        if m["round"] == "final" and score1 == score2:
            cursor.execute("ROLLBACK"); return False, "draw_not_allowed"
        if m["leg"] == 2 and _aggregate_would_draw(cursor, m, score1, score2):
            cursor.execute("ROLLBACK"); return False, "aggregate_draw_not_allowed"

        cursor.execute(
            "UPDATE cl_playoff_matches SET score1 = ?, score2 = ?, "
            "submitted_by = ?, status = ? WHERE id = ?",
            (score1, score2, user_id, MATCH_STATUS_AWAITING_CONFIRMATION, match_id),
        )
        cursor.execute("COMMIT")
        return True, "awaiting_confirmation"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _ensure_next_tie(cursor, season: int, next_round: str, position: int) -> None:
    """Keyingi bosqich juftligining 1-o'yin qatorini (bo'sh) yaratadi (idempotent)."""
    cursor.execute(
        "INSERT OR IGNORE INTO cl_playoff_matches "
        "(season, round, position, leg, status) VALUES (?, ?, ?, 1, ?)",
        (season, next_round, position, MATCH_STATUS_PENDING),
    )


def _advance_winner(cursor, m: dict, winner_id: int) -> None:
    """
    2-o'yin tasdiqlangach g'olibni keyingi bosqichga yozadi.
    pos 2k → sideA (leg1.player2; final: player1), pos 2k+1 → sideB (player1;
    final: player2). Keyingi bosqich pos = m.position // 2.
    """
    idx = CL_PO_ROUNDS.index(m["round"])
    next_round = CL_PO_ROUNDS[idx + 1]
    next_pos = m["position"] // 2
    _ensure_next_tie(cursor, m["season"], next_round, next_pos)

    goes_side_a = (m["position"] % 2 == 0)
    if next_round == "final":
        col = "player1_id" if goes_side_a else "player2_id"
    else:
        col = "player2_id" if goes_side_a else "player1_id"
    cursor.execute(
        f"UPDATE cl_playoff_matches SET {col} = ? "
        "WHERE season = ? AND round = ? AND position = ? AND leg = 1",
        (winner_id, m["season"], next_round, next_pos),
    )
    logger.info("ChL PO: %s pos%s g'olibi (user %s) → %s pos%s",
                m["round"], m["position"], winner_id, next_round, next_pos)


def cl_po_confirm_result(match_id: int, user_id: int,
                         accept: bool) -> tuple[bool, str]:
    """
    Tasdiqlash (accept=True) yoki rad etish (False).
    Xato sabablari: not_found, not_participant, wrong_status, cannot_confirm_own.
    Tasdiqda: leg1 → leg2 yaratiladi; leg2 → g'olib keyingi bosqichga.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        m = _get(cursor, match_id)
        if not m:
            cursor.execute("ROLLBACK"); return False, "not_found"
        if user_id not in (m["player1_id"], m["player2_id"]):
            cursor.execute("ROLLBACK"); return False, "not_participant"
        if m["status"] != MATCH_STATUS_AWAITING_CONFIRMATION:
            cursor.execute("ROLLBACK"); return False, "wrong_status"
        if m["submitted_by"] == user_id:
            cursor.execute("ROLLBACK"); return False, "cannot_confirm_own"

        if not accept:
            cursor.execute(
                "UPDATE cl_playoff_matches SET score1 = NULL, score2 = NULL, "
                "submitted_by = NULL, status = ? WHERE id = ?",
                (MATCH_STATUS_PENDING, match_id),
            )
            cursor.execute("COMMIT")
            return True, "rejected"

        # Himoya: tasdiqlash paytida ham agregat tekshiruvi (qoida #41)
        if m["leg"] == 2 and _aggregate_would_draw(cursor, m, m["score1"], m["score2"]):
            cursor.execute("ROLLBACK")
            return False, "aggregate_draw_not_allowed"

        cursor.execute(
            "UPDATE cl_playoff_matches SET status = ? WHERE id = ?",
            (MATCH_STATUS_CONFIRMED, match_id),
        )

        if m["round"] != "final" and m["leg"] == 1:
            # 2-o'yin: uy/mehmon almashadi (sideA endi uyda) — idempotent
            cursor.execute(
                "INSERT OR IGNORE INTO cl_playoff_matches "
                "(season, round, position, leg, player1_id, player2_id, status) "
                "VALUES (?, ?, ?, 2, ?, ?, ?)",
                (m["season"], m["round"], m["position"],
                 m["player2_id"], m["player1_id"], MATCH_STATUS_PENDING),
            )
        elif m["round"] != "final" and m["leg"] == 2:
            leg1 = _leg1_of(cursor, m)
            agg_a = leg1["score2"] + m["score1"]   # sideA = leg2.player1
            agg_b = leg1["score1"] + m["score2"]   # sideB = leg2.player2
            winner = m["player1_id"] if agg_a > agg_b else m["player2_id"]
            _advance_winner(cursor, m, winner)
        # final: qo'shimcha ish yo'q — chempion bracket'da hisoblanadi

        cursor.execute("COMMIT")
        return True, "confirmed"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
