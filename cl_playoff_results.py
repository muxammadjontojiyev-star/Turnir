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
    """
    Kiritilayotgan hisob juftlik agregatini teng qiladimi? 2026-07-22: ikkala o'yin
    bir vaqtda ochiq bo'lgani uchun leg1 YOKI leg2 kiritilishi mumkin — qaysi
    kiritilayotgan bo'lsa, IKKINCHISI (agar confirmed bo'lsa) bilan solishtiriladi.

    Agregat konventsiyasi: aggA (sideA) = leg1.score2 + leg2.score1;
                           aggB (sideB) = leg1.score1 + leg2.score2.
    Boshqa leg hali confirmed bo'lmasa — teng qilib bo'lmaydi (False; juftlik
    hal bo'lganda _tie_winner_if_ready qat'iy tekshiradi).
    """
    leg1, leg2 = _both_legs(cursor, m)
    if m["leg"] == 2:
        other = leg1
        if not other or other["status"] != MATCH_STATUS_CONFIRMED:
            return False
        agg_a = other["score2"] + score1   # leg1.score2 + leg2.score1
        agg_b = other["score1"] + score2   # leg1.score1 + leg2.score2
    else:  # leg == 1
        other = leg2
        if not other or other["status"] != MATCH_STATUS_CONFIRMED:
            return False
        agg_a = score2 + other["score1"]   # leg1.score2 + leg2.score1
        agg_b = score1 + other["score2"]   # leg1.score1 + leg2.score2
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
        # Ikkala o'yin bir vaqtda ochiq — istalgan leg boshqasini teng qilmasin
        if m["round"] != "final" and _aggregate_would_draw(cursor, m, score1, score2):
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
    """
    Keyingi bosqich juftligining IKKALA o'yin qatorini (bo'sh) yaratadi (idempotent).
    2026-07-22: uy+mehmon bir vaqtda ko'rinishi uchun leg1 va leg2 birga ochiladi.
    Final — bitta o'yin (leg1). O'yinchilar hali NULL; g'oliblar kelib to'ldiriladi.
    """
    cursor.execute(
        "INSERT OR IGNORE INTO cl_playoff_matches "
        "(season, round, position, leg, status) VALUES (?, ?, ?, 1, ?)",
        (season, next_round, position, MATCH_STATUS_PENDING),
    )
    if next_round != "final":
        cursor.execute(
            "INSERT OR IGNORE INTO cl_playoff_matches "
            "(season, round, position, leg, status) VALUES (?, ?, ?, 2, ?)",
            (season, next_round, position, MATCH_STATUS_PENDING),
        )


def _advance_winner(cursor, m: dict, winner_id: int) -> None:
    """
    Juftlik hal bo'lgach g'olibni keyingi bosqichga yozadi.
    pos 2k → sideA, pos 2k+1 → sideB. Keyingi bosqich pos = m.position // 2.

    2026-07-22: keyingi bosqichda IKKALA leg mavjud (uy+mehmon bir vaqtda), shuning
    uchun g'olib har ikkovida to'g'ri slotga yoziladi:
      - final (bitta o'yin): sideA=player1, sideB=player2.
      - oddiy bosqich: leg1 → player1=sideB, player2=sideA ; leg2 teskari.
    """
    idx = CL_PO_ROUNDS.index(m["round"])
    next_round = CL_PO_ROUNDS[idx + 1]
    next_pos = m["position"] // 2
    _ensure_next_tie(cursor, m["season"], next_round, next_pos)

    goes_side_a = (m["position"] % 2 == 0)
    if next_round == "final":
        # Final — bitta o'yin: sideA→player1, sideB→player2
        col = "player1_id" if goes_side_a else "player2_id"
        cursor.execute(
            f"UPDATE cl_playoff_matches SET {col} = ? "
            "WHERE season = ? AND round = ? AND position = ? AND leg = 1",
            (winner_id, m["season"], next_round, next_pos),
        )
    else:
        # leg1: player1=sideB, player2=sideA ; leg2 teskari (uy/mehmon almashadi)
        leg1_col = "player2_id" if goes_side_a else "player1_id"
        leg2_col = "player1_id" if goes_side_a else "player2_id"
        cursor.execute(
            f"UPDATE cl_playoff_matches SET {leg1_col} = ? "
            "WHERE season = ? AND round = ? AND position = ? AND leg = 1",
            (winner_id, m["season"], next_round, next_pos),
        )
        cursor.execute(
            f"UPDATE cl_playoff_matches SET {leg2_col} = ? "
            "WHERE season = ? AND round = ? AND position = ? AND leg = 2",
            (winner_id, m["season"], next_round, next_pos),
        )
    logger.info("ChL PO: %s pos%s g'olibi (user %s) → %s pos%s",
                m["round"], m["position"], winner_id, next_round, next_pos)


def _both_legs(cursor, m: dict) -> tuple[dict | None, dict | None]:
    """Juftlikning leg1 va leg2 qatorlarini (to'liq) qaytaradi."""
    cursor.execute(
        "SELECT leg, score1, score2, status, player1_id, player2_id "
        "FROM cl_playoff_matches "
        "WHERE season = ? AND round = ? AND position = ?",
        (m["season"], m["round"], m["position"]),
    )
    leg1 = leg2 = None
    for r in cursor.fetchall():
        d = dict(r)
        if d["leg"] == 1:
            leg1 = d
        elif d["leg"] == 2:
            leg2 = d
    return leg1, leg2


def _tie_winner_if_ready(cursor, m: dict) -> int | None:
    """
    2026-07-22: juftlik hal bo'ldimi? IKKALA o'yin (uy+mehmon) tasdiqlangan bo'lsa —
    agregat g'olibini qaytaradi; aks holda None (hali erta). Tartibdan mustaqil —
    leg1 yoki leg2 oxirgi tasdiqlanishidan qat'i nazar ishlaydi.

    Agregat: sideA = leg2.player1 (leg1.player2). aggA = leg1.score2 + leg2.score1;
             aggB = leg1.score1 + leg2.score2. Teng bo'lsa None (bo'lmasligi kerak —
             kiritishda taqiqlangan).
    """
    leg1, leg2 = _both_legs(cursor, m)
    if not (leg1 and leg2):
        return None
    if leg1["status"] != MATCH_STATUS_CONFIRMED or leg2["status"] != MATCH_STATUS_CONFIRMED:
        return None
    agg_a = leg1["score2"] + leg2["score1"]   # sideA
    agg_b = leg1["score1"] + leg2["score2"]   # sideB
    if agg_a == agg_b:
        return None
    # sideA = leg2.player1, sideB = leg2.player2
    return leg2["player1_id"] if agg_a > agg_b else leg2["player2_id"]


def cl_po_confirm_result(match_id: int, user_id: int,
                         accept: bool) -> tuple[bool, str]:
    """
    Tasdiqlash (accept=True) yoki rad etish (False).
    Xato sabablari: not_found, not_participant, wrong_status, cannot_confirm_own.
    2026-07-22: uy+mehmon o'yinlari bir vaqtda ochiq (start'da yaratiladi). Har
    o'yin alohida tasdiqlanadi; IKKALA o'yin tasdiqlangach agregat g'olibi
    avtomatik keyingi bosqichga o'tadi (tartibdan mustaqil).
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

        # Himoya: tasdiqlash paytida ham agregat tekshiruvi (qoida #41).
        # Ikkala o'yin ochiq — qaysi leg tasdiqlanayotgan bo'lsa, boshqasi bilan.
        if m["round"] != "final" and _aggregate_would_draw(cursor, m, m["score1"], m["score2"]):
            cursor.execute("ROLLBACK")
            return False, "aggregate_draw_not_allowed"

        cursor.execute(
            "UPDATE cl_playoff_matches SET status = ? WHERE id = ?",
            (MATCH_STATUS_CONFIRMED, match_id),
        )

        if m["round"] == "final":
            # Final — bitta o'yin; chempion bracket'da hisoblanadi
            pass
        else:
            # Ikkala o'yin ham tasdiqlangan bo'lsa — g'olib keyingi bosqichga
            winner = _tie_winner_if_ready(cursor, m)
            if winner is not None:
                _advance_winner(cursor, m, winner)

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


def cl_po_auto_confirm_awaiting(season: int | None = None) -> dict:
    """
    2026-07-22 (talab 2): deadline (23:30) da ChL play-off o'yinlarini avtomatik
    yopish. FAQAT awaiting_confirmation (hisob kiritilgan, tasdiq kutayotgan) →
    confirmed. PENDING (hisob kiritilmagan) TEGILMAYDI — play-off'da durang
    yo'q, shuning uchun 0:0 qilib bo'lmaydi; ularni admin qo'lda tasdiqlaydi.

    Har yopilgan o'yindan keyin, agar juftlikning IKKALA legi ham confirmed
    bo'lsa — agregat g'olibi keyingi bosqichga o'tadi (_tie_winner_if_ready +
    _advance_winner qayta ishlatiladi — DRY). Agregat teng bo'lsa g'olib chiqmaydi
    (bu holat kiritishda taqiqlangani uchun deyarli bo'lmaydi).

    Idempotent — kuniga necha marta chaqirilsa ham awaiting qolmagach 0 qaytaradi.
    Scheduler chaqiradi (cl_tick yonida).
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
            r = cursor.fetchone()
            season = r["current_season"] if r else 1

        # Play-off boshlangan bo'lishi kerak
        cursor.execute(
            "SELECT started FROM cl_playoff_state WHERE season = ?", (season,))
        st = cursor.fetchone()
        if not (st and st["started"]):
            cursor.execute("ROLLBACK")
            return {"confirmed": 0, "advanced": 0}

        # Awaiting o'yinlarni yig'amiz (advance uchun round/position/leg kerak)
        cursor.execute(
            "SELECT id, season, round, position, leg, player1_id, player2_id "
            "FROM cl_playoff_matches WHERE season = ? AND status = ?",
            (season, MATCH_STATUS_AWAITING_CONFIRMATION),
        )
        awaiting = [dict(r) for r in cursor.fetchall()]
        if not awaiting:
            cursor.execute("ROLLBACK")
            return {"confirmed": 0, "advanced": 0}

        # 1) Hammasini confirmed qilamiz
        cursor.execute(
            "UPDATE cl_playoff_matches SET status = ? "
            "WHERE season = ? AND status = ?",
            (MATCH_STATUS_CONFIRMED, season, MATCH_STATUS_AWAITING_CONFIRMATION),
        )
        confirmed = cursor.rowcount or 0

        # 2) Har juftlik uchun (takrorsiz) g'olibni tekshiramiz
        advanced = 0
        seen = set()
        for m in awaiting:
            if m["round"] == "final":
                continue
            key = (m["round"], m["position"])
            if key in seen:
                continue
            seen.add(key)
            winner = _tie_winner_if_ready(cursor, m)
            if winner is not None:
                _advance_winner(cursor, m, winner)
                advanced += 1

        cursor.execute("COMMIT")
        if confirmed:
            logger.info("ChL play-off deadline: %s awaiting → confirmed, %s juftlik advance.",
                        confirmed, advanced)
        return {"confirmed": confirmed, "advanced": advanced}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
