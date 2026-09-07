"""
cl_diagnostics.py — ChL guruh bosqichi diagnostikasi (2026-08-28).

Muammo (qoida #52): admin "Qayta tasnifni boshlash" ni bosganda
"Guruh o'yinlari hali tugamagan" chiqadi, lekin admin panelida barcha turlar
o'tgan ko'rinadi (masalan "Joriy tur: 9 / 8"). Xabar QAYSI o'yin bloklayotganini
aytmaydi — admin muammoni topa olmaydi.

Sabab: cl_playoff.cl_po_qualified() cl_matches ichida status != 'confirmed'
bo'lgan BITTA qator qolsa ham to'xtatadi. cl_rounds._resolve_matchdays_upto() esa
faqat O'SHA PAYTDAGI joriy turni yopadi — biror sabab bilan (masalan matchday
qiymati diapazondan tashqarida bo'lsa) chetda qolgan o'yin abadiy pending
qolishi mumkin.

Bu modul FAQAT O'QIYDI — hech narsa o'zgartirmaydi (qoida #07).
cl_playoff.py 498 qator bo'lgani uchun alohida fayl (qoida #21).
"""

import logging

from models import get_connection
from config import MATCH_STATUS_CONFIRMED

logger = logging.getLogger(__name__)


def _current_season(cursor) -> int:
    """cl_rounds/cl_playoff bilan BIR XIL manba (season_state.current_season)."""
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["current_season"] if row else 1


def cl_group_blocking(season: int | None = None) -> dict:
    """
    Guruh bosqichida tasdiqlanmagan (confirmed bo'lmagan) o'yinlarni qaytaradi.

    Qaytaradi:
      {
        "season": int,
        "current_matchday": int,     # cl_state
        "total_matchdays": int,      # MAX(cl_matches.matchday)
        "total_matches": int,        # shu mavsumdagi barcha guruh o'yinlari
        "blocking_count": int,
        "matchdays": [int, ...],     # bloklayotgan turlar ro'yxati
        "matches": [ {id, matchday, status, score1, score2, p1, p2}, ... ]
      }

    matches ro'yxati 50 ta bilan cheklanadi — admin xabarini bo'g'ib
    qo'ymaslik uchun (blocking_count to'liq sonni beradi).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_season(cursor)

        cursor.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(MAX(matchday), 0) AS mx "
            "FROM cl_matches WHERE season = ?",
            (season,),
        )
        agg = cursor.fetchone()

        cursor.execute(
            "SELECT current_matchday FROM cl_state WHERE season = ?", (season,))
        st = cursor.fetchone()

        cursor.execute(
            """
            SELECT m.id AS id, m.matchday AS matchday, m.status AS status,
                   m.score1 AS score1, m.score2 AS score2,
                   u1.username AS p1_username, u1.nickname AS p1_nickname,
                   u2.username AS p2_username, u2.nickname AS p2_nickname
            FROM cl_matches m
            LEFT JOIN users u1 ON u1.id = m.player1_id
            LEFT JOIN users u2 ON u2.id = m.player2_id
            WHERE m.season = ? AND m.status != ?
            ORDER BY m.matchday, m.id
            LIMIT 50
            """,
            (season, MATCH_STATUS_CONFIRMED),
        )
        rows = [dict(r) for r in cursor.fetchall()]

        # To'liq son (LIMIT'dan qat'i nazar)
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM cl_matches WHERE season = ? AND status != ?",
            (season, MATCH_STATUS_CONFIRMED),
        )
        blocking_count = cursor.fetchone()["cnt"]

        matches = [{
            "id": r["id"],
            "matchday": r["matchday"],
            "status": r["status"],
            "score1": r["score1"],
            "score2": r["score2"],
            "p1": r["p1_username"] or r["p1_nickname"],
            "p2": r["p2_username"] or r["p2_nickname"],
        } for r in rows]

        return {
            "season": season,
            "current_matchday": st["current_matchday"] if st else 0,
            "total_matchdays": agg["mx"],
            "total_matches": agg["cnt"],
            "blocking_count": blocking_count,
            "matchdays": sorted({m["matchday"] for m in matches}),
            "matches": matches,
        }
    finally:
        conn.close()
