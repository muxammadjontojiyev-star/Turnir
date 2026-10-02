"""
el_playoff.py — Yevropa ligasi play-off: boshlash (cl_playoff naqshi, ALOHIDA nusxa).

  1-BOSQICH el_po_start()         — pley-in (9-24 o'rin, 8 juftlik, uy+mehmon).
  2-BOSQICH el_po_start_bracket() — pley-in tugagach asosiy setka (r16) ochiladi:
                                    top-8 seed + 8 pley-in g'olibi.
  Keyin r16 -> r8 -> r4 -> final (el_playoff_results._advance_winner).

Konventsiya: sideA = yuqori urug', sideB = quyi urug'.
  leg1: player1 = sideB (uyda), player2 = sideA; leg2 teskari. Final: 1 o'yin, player1 = sideA.
Setkani ko'rish — el_playoff_view.py.
"""

import logging

from config import MATCH_STATUS_CONFIRMED, MATCH_STATUS_PENDING
from models import get_connection

logger = logging.getLogger(__name__)

EL_PO_ROUNDS = ["r16", "r8", "r4", "final"]   # asosiy setka zanjiri
EL_PO_PLAYIN = "playin"                       # kirish raundi (zanjirga kirmaydi)
EL_PO_FINAL = "final"


def _current_season(cursor) -> int:
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["current_season"] if row else 1


def _rollback(cursor, where: str) -> None:
    try:
        cursor.execute("ROLLBACK")
    except Exception:
        logger.exception("%s: ROLLBACK xatosi", where)


def _insert_tie(cursor, season: int, rnd: str, pos: int, side_a, side_b) -> None:
    """Juftlikning ikkala o'yinini yaratadi: leg1 uyda sideB, leg2 uyda sideA."""
    sql = ("INSERT INTO el_playoff_matches "
           "(season, round, position, leg, player1_id, player2_id, status) "
           "VALUES (?, ?, ?, ?, ?, ?, ?)")
    cursor.execute(sql, (season, rnd, pos, 1, side_b, side_a, MATCH_STATUS_PENDING))
    cursor.execute(sql, (season, rnd, pos, 2, side_a, side_b, MATCH_STATUS_PENDING))


def el_po_is_started(season: int | None = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_season(cursor)
        cursor.execute("SELECT started FROM el_playoff_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        return bool(row and row["started"])
    finally:
        conn.close()


def el_po_qualified(season: int) -> tuple[bool, str, dict]:
    """
    Shartlar: barcha liga bosqichi o'yinlari confirmed; reytingda >= 24 o'yinchi.
    Qaytaradi: (ready, reason, {"seeds", "playin"}).
    reason: ok | not_drawn | groups_not_finished | not_enough_players
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) AS cnt FROM el_matches WHERE season = ?", (season,))
        if cursor.fetchone()["cnt"] == 0:
            return False, "not_drawn", {}
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM el_matches WHERE season = ? AND status != ?",
            (season, MATCH_STATUS_CONFIRMED),
        )
        if cursor.fetchone()["cnt"] > 0:
            return False, "groups_not_finished", {}
    finally:
        conn.close()

    from el_core import EL_LEAGUE_GROUP, el_group_rating
    from el_playin import EL_QUALIFY_TOTAL, build_playin_draw
    rating = el_group_rating(EL_LEAGUE_GROUP, season)
    if len(rating) < EL_QUALIFY_TOTAL:
        return False, "not_enough_players", {}
    return True, "ok", build_playin_draw([r["user_id"] for r in rating])


def el_po_start(season: int | None = None) -> tuple[bool, str | dict]:
    """
    Pley-in'ni boshlaydi (8 juftlik, uy+mehmon). Setka hali YARATILMAYDI.
    Sabablar: already_started, not_drawn, groups_not_finished, not_enough_players.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_season(cursor)
        cursor.execute("SELECT started FROM el_playoff_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        if row and row["started"]:
            cursor.execute("ROLLBACK")
            return False, "already_started"

        ready, reason, q = el_po_qualified(season)
        if not ready:
            cursor.execute("ROLLBACK")
            return False, reason

        for pos, (hi_id, lo_id) in enumerate(q["playin"]):
            _insert_tie(cursor, season, EL_PO_PLAYIN, pos, side_a=hi_id, side_b=lo_id)

        cursor.execute(
            "INSERT INTO el_playoff_state (season, started, started_at) "
            "VALUES (?, 1, datetime('now')) "
            "ON CONFLICT(season) DO UPDATE SET started = 1, started_at = excluded.started_at",
            (season,),
        )
        cursor.execute("COMMIT")
        logger.info("YeL pley-in boshlandi: mavsum %s, %s juftlik", season, len(q["playin"]))
        return True, {"season": season, "playin_pairs": len(q["playin"])}
    except Exception:
        _rollback(cursor, "el_po_start")
        raise
    finally:
        conn.close()


def _playin_winners(cursor, season: int) -> dict[int, int] | None:
    """Har pley-in pozitsiyasi g'olibi (agregat). Biror juftlik chala bo'lsa None."""
    cursor.execute(
        "SELECT position, leg, player1_id, player2_id, score1, score2 "
        "FROM el_playoff_matches WHERE season = ? AND round = ? ORDER BY position, leg",
        (season, EL_PO_PLAYIN),
    )
    legs_by_pos: dict[int, dict] = {}
    for r in cursor.fetchall():
        legs_by_pos.setdefault(r["position"], {})[r["leg"]] = dict(r)

    winners: dict[int, int] = {}
    for pos, legs in legs_by_pos.items():
        l1, l2 = legs.get(1), legs.get(2)
        if not l1 or not l2:
            return None
        agg_a = (l1["score2"] or 0) + (l2["score1"] or 0)   # sideA = leg1.player2
        agg_b = (l1["score1"] or 0) + (l2["score2"] or 0)   # sideB = leg1.player1
        winners[pos] = l1["player2_id"] if agg_a > agg_b else l1["player1_id"]
    return winners


def el_po_start_bracket(season: int | None = None) -> tuple[bool, str | dict]:
    """
    Asosiy setkani (r16) ochadi: sideA = seed[p], sideB = pley-in g'olibi[7-p].
    Sabablar: playin_not_started, bracket_already_started, playin_not_finished,
    not_enough_players / groups_not_finished, bracket_failed.
    """
    from el_playin import r16_slot_for_playin_position

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_season(cursor)

        cursor.execute(
            "SELECT COUNT(*) AS n FROM el_playoff_matches WHERE season = ? AND round = ?",
            (season, EL_PO_PLAYIN))
        if cursor.fetchone()["n"] == 0:
            cursor.execute("ROLLBACK")
            return False, "playin_not_started"

        cursor.execute(
            "SELECT COUNT(*) AS n FROM el_playoff_matches WHERE season = ? AND round = ?",
            (season, EL_PO_ROUNDS[0]))
        if cursor.fetchone()["n"] > 0:
            cursor.execute("ROLLBACK")
            return False, "bracket_already_started"

        cursor.execute(
            "SELECT COUNT(*) AS n FROM el_playoff_matches "
            "WHERE season = ? AND round = ? AND status != ?",
            (season, EL_PO_PLAYIN, MATCH_STATUS_CONFIRMED))
        if cursor.fetchone()["n"] > 0:
            cursor.execute("ROLLBACK")
            return False, "playin_not_finished"

        winners = _playin_winners(cursor, season)
        if winners is None:
            cursor.execute("ROLLBACK")
            return False, "playin_not_finished"

        ready, reason, q = el_po_qualified(season)
        if not ready:
            cursor.execute("ROLLBACK")
            return False, reason

        # r16 pos -> pley-in pozitsiyasi (teskari moslik), bitta lug'at (qoida #24)
        playin_for_r16 = {r16_slot_for_playin_position(pp): pp for pp in winners}
        for pos, seed_id in enumerate(q["seeds"]):
            pp = playin_for_r16.get(pos)
            opp_id = winners.get(pp) if pp is not None else None
            _insert_tie(cursor, season, EL_PO_ROUNDS[0], pos, side_a=seed_id, side_b=opp_id)

        cursor.execute("COMMIT")
        logger.info("YeL setka ochildi: mavsum %s, %s r16 juftligi", season, len(q["seeds"]))
        return True, {"season": season, "r16_pairs": len(q["seeds"])}
    except Exception:
        _rollback(cursor, "el_po_start_bracket")
        logger.exception("el_po_start_bracket xatosi")
        return False, "bracket_failed"
    finally:
        conn.close()
