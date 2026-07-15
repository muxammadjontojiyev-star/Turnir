"""
cl_scorers.py — ChL "To'purarlar" ro'yxati.

Bitta vazifa (qoida #25): tasdiqlangan (confirmed) ChL o'yinlari bo'yicha har bir
ishtirokchining URILGAN GOLLARI yig'indisi. Barcha 8 guruh bo'yicha umumiy.

Saralash: gollar (kamayish) → o'yinlar soni (kamayish teskari: kam o'yinda ko'p gol
yuqorida) → nickname. Guruh bosqichida hammaning o'yin soni teng bo'lgani uchun bu
faqat yarim o'ynalgan holatlar uchun ahamiyatli.
"""

from models import get_connection
from config import MATCH_STATUS_CONFIRMED


def cl_top_scorers(season: int | None = None, limit: int = 32) -> list[dict]:
    """
    [{user_id, nickname, username, club_name, group_number, goals, played}, ...]
    Faqat kerakli ustunlar olinadi (qoida #32 — SELECT * yo'q).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
            row = cursor.fetchone()
            season = row["current_season"] if row else 1

        cursor.execute(
            "SELECT p.user_id, p.nickname, p.group_number, u.username, "
            "COALESCE(r.club_name, p.club_name) AS club_name "
            "FROM cl_participants p JOIN users u ON u.id = p.user_id "
            "LEFT JOIN registrations r ON r.user_id = p.user_id "
            "WHERE p.season = ? AND p.group_number IS NOT NULL",
            (season,),
        )
        players = {
            r["user_id"]: {
                "user_id": r["user_id"], "nickname": r["nickname"],
                "username": r["username"], "club_name": r["club_name"],
                "group_number": r["group_number"], "goals": 0, "played": 0,
            }
            for r in cursor.fetchall()
        }
        if not players:
            return []

        cursor.execute(
            "SELECT player1_id, player2_id, score1, score2 FROM cl_matches "
            "WHERE season = ? AND status = ? AND score1 IS NOT NULL",
            (season, MATCH_STATUS_CONFIRMED),
        )
        for m in cursor.fetchall():   # dict orqali O(1) — nested loop yo'q (qoida #24)
            p1 = players.get(m["player1_id"])
            p2 = players.get(m["player2_id"])
            if p1:
                p1["goals"] += m["score1"]
                p1["played"] += 1
            if p2:
                p2["goals"] += m["score2"]
                p2["played"] += 1

        rows = sorted(
            players.values(),
            key=lambda p: (-p["goals"], p["played"], (p["nickname"] or "").lower()),
        )
        return rows[:limit]
    finally:
        conn.close()
