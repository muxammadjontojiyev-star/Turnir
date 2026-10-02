"""
el_diagnostics.py — YeL liga bosqichi diagnostikasi (cl_diagnostics naqshi, ALOHIDA).

"Liga bosqichi hali tugamagan" (groups_not_finished) chiqqanda QAYSI o'yinlar
bloklayotganini ko'rsatadi. FAQAT O'QIYDI (qoida #07).
"""

from config import MATCH_STATUS_CONFIRMED
from models import get_connection

BLOCKING_LIST_LIMIT = 50   # admin xabarini bo'g'masligi uchun (to'liq son alohida)


def el_group_blocking(season: int | None = None) -> dict:
    """
    {season, current_matchday, total_matchdays, total_matches, blocking_count,
     matchdays: [int], matches: [{id, matchday, status, score1, score2, p1, p2}]}
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
            row = cursor.fetchone()
            season = row["current_season"] if row else 1

        cursor.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(MAX(matchday), 0) AS mx "
            "FROM el_matches WHERE season = ?", (season,))
        agg = cursor.fetchone()
        cursor.execute("SELECT current_matchday FROM el_state WHERE season = ?", (season,))
        st = cursor.fetchone()
        cursor.execute(
            """
            SELECT m.id, m.matchday, m.status, m.score1, m.score2,
                   COALESCE(u1.username, u1.nickname) AS p1,
                   COALESCE(u2.username, u2.nickname) AS p2
            FROM el_matches m
            LEFT JOIN users u1 ON u1.id = m.player1_id
            LEFT JOIN users u2 ON u2.id = m.player2_id
            WHERE m.season = ? AND m.status != ?
            ORDER BY m.matchday, m.id
            LIMIT ?
            """,
            (season, MATCH_STATUS_CONFIRMED, BLOCKING_LIST_LIMIT),
        )
        matches = [dict(r) for r in cursor.fetchall()]
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM el_matches WHERE season = ? AND status != ?",
            (season, MATCH_STATUS_CONFIRMED))
        blocking_count = cursor.fetchone()["cnt"]
    finally:
        conn.close()
    return {"season": season,
            "current_matchday": st["current_matchday"] if st else 0,
            "total_matchdays": agg["mx"], "total_matches": agg["cnt"],
            "blocking_count": blocking_count,
            "matchdays": sorted({m["matchday"] for m in matches}),
            "matches": matches}
