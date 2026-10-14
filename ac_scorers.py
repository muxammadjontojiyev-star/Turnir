"""
ac_scorers.py — Osiyo Chempionlar ligasi "To'purarlar" ro'yxati (cl_scorers naqshi, ALOHIDA).

Tasdiqlangan (confirmed) OChL o'yinlaridagi URILGAN GOLLAR yig'indisi.
Saralash: gollar (kamayish) -> o'yinlar soni (kam o'yinda ko'p gol yuqorida) -> nickname.

Gol manbalari AC_SCORE_TABLES: liga bosqichi + play-off (ikkala leg alohida o'yin
sifatida sanaladi) — ustun nomlari bir xil (player1/2_id, score1/2).
Jadval nomlari KODDAN keladi, foydalanuvchidan emas (qoida #29).
"""

from config import MATCH_STATUS_CONFIRMED
from ac_qualification import AC_TOTAL
from models import get_connection

AC_SCORE_TABLES = ("ac_matches", "ac_playoff_matches")


def ac_top_scorers(season: int | None = None, limit: int | None = None) -> list[dict]:
    """[{user_id, nickname, username, club_name, group_number, goals, played}, ...]"""
    if limit is None:
        limit = AC_TOTAL
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
            "FROM ac_participants p JOIN users u ON u.id = p.user_id "
            "LEFT JOIN registrations r ON r.user_id = p.user_id "
            "WHERE p.season = ? AND p.group_number IS NOT NULL",
            (season,),
        )
        players = {
            r["user_id"]: {"user_id": r["user_id"], "nickname": r["nickname"],
                           "username": r["username"], "club_name": r["club_name"],
                           "group_number": r["group_number"], "goals": 0, "played": 0}
            for r in cursor.fetchall()
        }
        if not players:
            return []

        for table in AC_SCORE_TABLES:
            cursor.execute(
                f"SELECT player1_id, player2_id, score1, score2 FROM {table} "
                "WHERE season = ? AND status = ? AND score1 IS NOT NULL",
                (season, MATCH_STATUS_CONFIRMED),
            )
            for m in cursor.fetchall():   # dict orqali O(1) (qoida #24)
                for pid, goals in ((m["player1_id"], m["score1"]), (m["player2_id"], m["score2"])):
                    p = players.get(pid)
                    if p:
                        p["goals"] += goals
                        p["played"] += 1
    finally:
        conn.close()

    rows = sorted(players.values(),
                  key=lambda p: (-p["goals"], p["played"], (p["nickname"] or "").lower()))
    return rows[:limit]
