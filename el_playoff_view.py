"""
el_playoff_view.py — YeL play-off setkasini va o'yinlarini KO'RSATISH (faqat o'qish).
cl_playoff.py dagi ko'rsatish qismi naqshi (cl_po_bracket / cl_po_my_matches).
Javob shakllari ChL bilan bir xil — frontend (5-bosqich) cl_playoff.js naqshini
qayta ishlatadi.
"""

from config import MATCH_STATUS_CONFIRMED
from el_playoff import EL_PO_FINAL, EL_PO_PLAYIN, EL_PO_ROUNDS, _current_season
from models import get_connection

# Profil tartibi: pley-in -> r16 -> r8 -> r4 -> final
_ROUND_ORDER = {EL_PO_PLAYIN: -1, **{r: i for i, r in enumerate(EL_PO_ROUNDS)}}


def _started(cursor, season: int) -> bool:
    cursor.execute("SELECT started FROM el_playoff_state WHERE season = ?", (season,))
    row = cursor.fetchone()
    return bool(row and row["started"])


def _po_rows(cursor, season: int) -> list[dict]:
    """Barcha play-off qatorlari o'yinchi nomi/klubi bilan (SELECT * emas — qoida #32)."""
    cursor.execute(
        """
        SELECT m.id, m.round, m.position, m.leg, m.player1_id, m.player2_id,
               m.score1, m.score2, m.status, m.submitted_by,
               u1.nickname AS p1_nick, u1.username AS p1_user,
               COALESCE(r1.club_name, e1.club_name) AS p1_club,
               u2.nickname AS p2_nick, u2.username AS p2_user,
               COALESCE(r2.club_name, e2.club_name) AS p2_club
        FROM el_playoff_matches m
        LEFT JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
        LEFT JOIN el_participants e1 ON e1.user_id = m.player1_id AND e1.season = m.season
        LEFT JOIN el_participants e2 ON e2.user_id = m.player2_id AND e2.season = m.season
        LEFT JOIN registrations r1 ON r1.user_id = m.player1_id
        LEFT JOIN registrations r2 ON r2.user_id = m.player2_id
        WHERE m.season = ?
        ORDER BY m.position, m.leg
        """,
        (season,),
    )
    return [dict(r) for r in cursor.fetchall()]


def _side_info(row: dict | None, prefix: str) -> dict:
    if not row:
        return {}
    return {"user_id": row.get(f"player{1 if prefix == 'p1' else 2}_id"),
            "nickname": row.get(f"{prefix}_nick"),
            "username": row.get(f"{prefix}_user"),
            "club_name": row.get(f"{prefix}_club")}


def _tie_from_rows(round_name: str, position: int, legs: dict) -> dict:
    """Bir juftlik: sideA/sideB, 2 o'yin, agregat, g'olib."""
    leg1, leg2 = legs.get(1), legs.get(2)
    is_final = round_name == EL_PO_FINAL
    side_a = _side_info(leg1, "p1" if is_final else "p2")
    side_b = _side_info(leg1, "p2" if is_final else "p1")

    agg_a = agg_b = winner_id = None
    if is_final:
        if leg1 and leg1["status"] == MATCH_STATUS_CONFIRMED:
            agg_a, agg_b = leg1["score1"], leg1["score2"]
    elif (leg1 and leg2 and leg1["status"] == MATCH_STATUS_CONFIRMED
          and leg2["status"] == MATCH_STATUS_CONFIRMED):
        agg_a = leg1["score2"] + leg2["score1"]
        agg_b = leg1["score1"] + leg2["score2"]
    if agg_a is not None and agg_a != agg_b:
        winner_id = side_a["user_id"] if agg_a > agg_b else side_b["user_id"]

    return {"round": round_name, "position": position, "a": side_a, "b": side_b,
            "leg1": leg1, "leg2": leg2, "agg_a": agg_a, "agg_b": agg_b,
            "winner_id": winner_id}


def _load(season: int | None) -> tuple[bool, list[dict]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_season(cursor)
        if not _started(cursor, season):
            return False, []
        return True, _po_rows(cursor, season)
    finally:
        conn.close()


def el_po_bracket(season: int | None = None) -> dict:
    """To'liq setka: {"started", "rounds": {round: [tie...]}, "champion"}."""
    started, rows = _load(season)
    if not started:
        return {"started": False, "rounds": {}, "champion": None}

    grouped: dict[tuple, dict] = {}
    for r in rows:
        grouped.setdefault((r["round"], r["position"]), {})[r["leg"]] = r

    rounds: dict[str, list] = {}
    champion = None
    for (rnd, pos), legs in sorted(grouped.items(), key=lambda kv: kv[0][1]):
        tie = _tie_from_rows(rnd, pos, legs)
        rounds.setdefault(rnd, []).append(tie)
        if rnd == EL_PO_FINAL and tie["winner_id"]:
            champion = tie["a"] if tie["winner_id"] == tie["a"].get("user_id") else tie["b"]
    return {"started": True, "rounds": rounds, "champion": champion}


def _user_matches(user_id: int, season: int | None) -> tuple[bool, list[dict]]:
    """Bitta ishtirokchining play-off o'yinlari (boshqa leg hisobi bilan), bosqich tartibida."""
    started, rows = _load(season)
    if not started:
        return False, []
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
    matches.sort(key=lambda m: (_ROUND_ORDER.get(m["round"], 99), m["leg"]))
    return True, matches


def el_po_my_matches(user_id: int, season: int | None = None) -> dict:
    """O'z play-off o'yinlarim (natija tugmalari uchun me_id bilan)."""
    started, matches = _user_matches(user_id, season)
    return {"started": started, "matches": matches, "me_id": user_id}


def el_po_user_matches(target_id: int, season: int | None = None) -> dict:
    """Boshqa ishtirokchining play-off o'yinlari — faqat o'qish (me_id yo'q)."""
    started, matches = _user_matches(target_id, season)
    return {"started": started, "matches": matches}
