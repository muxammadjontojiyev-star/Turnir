"""
cl_playoff.py — ChL play-off (2026-07-20).

Guruh bosqichidan keyin: har guruhdan top-2 → 16 o'yinchi → 1/8 (r16) →
1/4 (r8) → 1/2 (r4) → final. Har juftlik UY+MEHMON (2 o'yin), final — 1 o'yin.

Konventsiya (models.py cl_playoff_matches izohiga mos):
  - Juftlik tomonlari: sideA (yuqori urug' — guruh g'olibi / toq feeder g'olibi),
    sideB (quyi urug'). Real ChL kabi: 1-o'yinda sideB UYDA, 2-o'yinda sideA UYDA.
  - Demak leg1: player1=sideB, player2=sideA;  leg2: player1=sideA, player2=sideB.
  - Final: leg=1, player1=sideA (yarim final pos0 g'olibi), player2=sideB.
  - 2-o'yin 1-o'yin TASDIQLANGACH yaratiladi (cl_playoff_results.py).
  - Agregat teng bo'lishi mumkin emas (o'yin ichida penalti/qo'shimcha vaqt).

1/8 juftlash (bir guruhdoshlar uchrashmaydi, yarmlar ajratilgan):
  pos0 W(G1)-RU(G2), pos1 W(G3)-RU(G4), pos2 W(G5)-RU(G6), pos3 W(G7)-RU(G8),
  pos4 W(G2)-RU(G1), pos5 W(G4)-RU(G3), pos6 W(G6)-RU(G5), pos7 W(G8)-RU(G7).
G'olib oqimi: (pos 2k, 2k+1) g'oliblari keyingi bosqich pos k'da uchrashadi.
"""

import logging

from models import get_connection
from config import MATCH_STATUS_PENDING, MATCH_STATUS_CONFIRMED

logger = logging.getLogger(__name__)

CL_PO_ROUNDS = ["r16", "r8", "r4", "final"]

# (g'olib guruhi, ikkinchi o'rin guruhi) — pos 0..7 tartibida
CL_PO_R16_PAIRING = [(1, 2), (3, 4), (5, 6), (7, 8), (2, 1), (4, 3), (6, 5), (8, 7)]


def _current_season(cursor) -> int:
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["current_season"] if row else 1


def cl_po_is_started(season: int | None = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_season(cursor)
        cursor.execute(
            "SELECT started FROM cl_playoff_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        return bool(row and row["started"])
    finally:
        conn.close()


def cl_po_qualified(season: int) -> tuple[bool, str, dict]:
    """
    Har guruhdan top-2 ni aniqlaydi. Shartlar:
      - Barcha guruh o'yinlari tasdiqlangan (pending/awaiting qolmagan)
      - Har 8 guruhda kamida 2 o'yinchi reytingda bor
    Qaytaradi: (ready, reason, {"winners": {g: user_id}, "runners": {g: user_id}})
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM cl_matches WHERE season = ?", (season,))
        total = cursor.fetchone()["cnt"]
        if total == 0:
            return False, "not_drawn", {}
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM cl_matches "
            "WHERE season = ? AND status != ?",
            (season, MATCH_STATUS_CONFIRMED),
        )
        if cursor.fetchone()["cnt"] > 0:
            return False, "groups_not_finished", {}
    finally:
        conn.close()

    from cl_core import cl_group_rating
    winners, runners = {}, {}
    for g in range(1, 9):
        rating = cl_group_rating(g, season)
        if len(rating) < 2:
            return False, f"group_{g}_incomplete", {}
        winners[g] = rating[0]["user_id"]
        runners[g] = rating[1]["user_id"]
    return True, "ok", {"winners": winners, "runners": runners}


def cl_po_start(season: int | None = None) -> tuple[bool, str | dict]:
    """
    Bosh admin play-off'ni boshlaydi: 1/8 ning 8 ta 1-o'yinini yaratadi.
    Xato sabablari: already_started, not_drawn, groups_not_finished,
    group_N_incomplete. Idempotent (qoida #38): started tekshiriladi.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_season(cursor)
        cursor.execute(
            "SELECT started FROM cl_playoff_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        if row and row["started"]:
            cursor.execute("ROLLBACK")
            return False, "already_started"

        ready, reason, q = cl_po_qualified(season)
        if not ready:
            cursor.execute("ROLLBACK")
            return False, reason

        created = 0
        for pos, (wg, rg) in enumerate(CL_PO_R16_PAIRING):
            side_a = q["winners"][wg]    # 2-o'yinda uyda
            side_b = q["runners"][rg]    # 1-o'yinda uyda
            cursor.execute(
                "INSERT INTO cl_playoff_matches "
                "(season, round, position, leg, player1_id, player2_id, status) "
                "VALUES (?, 'r16', ?, 1, ?, ?, ?)",
                (season, pos, side_b, side_a, MATCH_STATUS_PENDING),
            )
            created += 1

        cursor.execute(
            "INSERT INTO cl_playoff_state (season, started, started_at) "
            "VALUES (?, 1, datetime('now')) "
            "ON CONFLICT(season) DO UPDATE SET started = 1, "
            "started_at = excluded.started_at",
            (season,),
        )
        cursor.execute("COMMIT")
        logger.info("ChL play-off boshlandi: mavsum %s, %s ta 1/8 o'yin", season, created)
        return True, {"season": season, "created": created}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _po_rows(cursor, season: int) -> list[dict]:
    """Barcha play-off qatorlari o'yinchi nomi/klubi bilan (SELECT * emas — qoida #32)."""
    cursor.execute(
        """
        SELECT m.id, m.round, m.position, m.leg, m.player1_id, m.player2_id,
               m.score1, m.score2, m.status, m.submitted_by,
               u1.nickname AS p1_nick, u1.username AS p1_user, c1.club_name AS p1_club,
               u2.nickname AS p2_nick, u2.username AS p2_user, c2.club_name AS p2_club
        FROM cl_playoff_matches m
        LEFT JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
        LEFT JOIN cl_participants c1 ON c1.user_id = m.player1_id AND c1.season = m.season
        LEFT JOIN cl_participants c2 ON c2.user_id = m.player2_id AND c2.season = m.season
        WHERE m.season = ?
        ORDER BY m.position, m.leg
        """,
        (season,),
    )
    return [dict(r) for r in cursor.fetchall()]


def _side_info(row: dict, prefix: str) -> dict:
    return {
        "user_id": row.get(f"player{1 if prefix == 'p1' else 2}_id"),
        "nickname": row.get(f"{prefix}_nick"),
        "username": row.get(f"{prefix}_user"),
        "club_name": row.get(f"{prefix}_club"),
    }


def _tie_from_rows(round_name: str, position: int, legs: dict) -> dict:
    """
    Bir juftlikni (sideA/sideB, 2 o'yin, agregat, g'olib) yig'adi.
    sideA = leg1.player2, sideB = leg1.player1; final: sideA = player1.
    """
    leg1 = legs.get(1)
    leg2 = legs.get(2)
    is_final = (round_name == "final")
    if is_final:
        side_a = _side_info(leg1, "p1") if leg1 else {}
        side_b = _side_info(leg1, "p2") if leg1 else {}
    else:
        side_a = _side_info(leg1, "p2") if leg1 else {}
        side_b = _side_info(leg1, "p1") if leg1 else {}

    agg_a = agg_b = None
    winner_id = None
    if is_final:
        if leg1 and leg1["status"] == MATCH_STATUS_CONFIRMED:
            agg_a, agg_b = leg1["score1"], leg1["score2"]
            winner_id = side_a["user_id"] if agg_a > agg_b else side_b["user_id"]
    else:
        if (leg1 and leg2 and leg1["status"] == MATCH_STATUS_CONFIRMED
                and leg2["status"] == MATCH_STATUS_CONFIRMED):
            # A: 1-o'yinda mehmon (score2), 2-o'yinda uyda (score1)
            agg_a = leg1["score2"] + leg2["score1"]
            agg_b = leg1["score1"] + leg2["score2"]
            winner_id = side_a["user_id"] if agg_a > agg_b else side_b["user_id"]

    return {
        "round": round_name, "position": position,
        "a": side_a, "b": side_b,
        "leg1": leg1, "leg2": leg2,
        "agg_a": agg_a, "agg_b": agg_b,
        "winner_id": winner_id,
    }


def cl_po_bracket(season: int | None = None) -> dict:
    """To'liq setka: {"started", "rounds": {round: [tie...]}, "champion"}."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_season(cursor)
        cursor.execute(
            "SELECT started FROM cl_playoff_state WHERE season = ?", (season,))
        st = cursor.fetchone()
        if not (st and st["started"]):
            return {"started": False, "rounds": {}, "champion": None}
        rows = _po_rows(cursor, season)
    finally:
        conn.close()

    grouped: dict[tuple, dict] = {}
    for r in rows:
        grouped.setdefault((r["round"], r["position"]), {})[r["leg"]] = r

    rounds: dict[str, list] = {}
    champion = None
    for (rnd, pos), legs in sorted(grouped.items(), key=lambda kv: kv[0][1]):
        tie = _tie_from_rows(rnd, pos, legs)
        rounds.setdefault(rnd, []).append(tie)
        if rnd == "final" and tie["winner_id"]:
            champion = tie["a"] if tie["winner_id"] == tie["a"].get("user_id") else tie["b"]
    return {"started": True, "rounds": rounds, "champion": champion}


def cl_po_my_matches(user_id: int, season: int | None = None) -> dict:
    """
    Foydalanuvchining play-off o'yinlari (Profil sahifasi uchun).
    Har o'yinga juftlik konteksti (leg2 uchun leg1 hisobi — agregat ko'rsatish).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_season(cursor)
        cursor.execute(
            "SELECT started FROM cl_playoff_state WHERE season = ?", (season,))
        st = cursor.fetchone()
        if not (st and st["started"]):
            return {"started": False, "matches": [], "me_id": user_id}
        rows = _po_rows(cursor, season)
    finally:
        conn.close()

    by_tie: dict[tuple, dict] = {}
    for r in rows:
        by_tie.setdefault((r["round"], r["position"]), {})[r["leg"]] = r

    matches = []
    for r in rows:
        if user_id not in (r["player1_id"], r["player2_id"]):
            continue
        m = dict(r)
        other = by_tie[(r["round"], r["position"])].get(2 if r["leg"] == 1 else 1)
        m["other_leg_score1"] = other["score1"] if other else None
        m["other_leg_score2"] = other["score2"] if other else None
        m["other_leg_status"] = other["status"] if other else None
        matches.append(m)
    return {"started": True, "matches": matches, "me_id": user_id}
