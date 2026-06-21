"""
schedule.py — Round-robin (circle method) jadval generatsiyasi.

Liga 20 kishiga to'lganda, har bir o'yinchi qolgan 19 tasi bilan
2 marta (uy/mehmon) o'ynaydi -> jami 380 ta match, 38 kun (matchday)ga
taqsimlangan holda.
"""

from models import get_connection
from config import MATCH_STATUS_PENDING


def _generate_round_robin_pairs(player_ids: list[int]) -> list[list[tuple[int, int]]]:
    """
    Circle method algoritmi.

    N ta o'yinchi uchun (N-1) ta tur generatsiya qiladi, har turda N/2 ta juftlik.
    Qaytaradi: [[(player1, player2), ...], ...]  -- har bir ichki ro'yxat bitta tur.
    """
    players = player_ids[:]
    n = len(players)

    if n % 2 != 0:
        players.append(None)  # toq son bo'lsa, "bye" uchun placeholder
        n += 1

    rounds = []
    for _ in range(n - 1):
        round_pairs = []
        for i in range(n // 2):
            home = players[i]
            away = players[n - 1 - i]
            if home is not None and away is not None:
                round_pairs.append((home, away))
        rounds.append(round_pairs)

        # Aylantirish: birinchi o'yinchi joyida qoladi, qolganlari aylanadi
        players = [players[0]] + [players[-1]] + players[1:-1]

    return rounds


def generate_league_schedule(league_id: int, player_ids: list[int]) -> int:
    """
    Liga uchun to'liq 38 kunlik (2 doiralik) jadval generatsiya qiladi va DB'ga yozadi.

    1-doira: birinchi (N-1) tur, uy egasi/mehmon asl tartibda.
    2-doira: keyingi (N-1) tur, uy egasi/mehmon teskari tartibda.

    Qaytaradi: yaratilgan matchlar soni.
    """
    first_leg = _generate_round_robin_pairs(player_ids)
    second_leg = [
        [(away, home) for (home, away) in round_pairs] for round_pairs in first_leg
    ]
    full_schedule = first_leg + second_leg  # jami 2*(N-1) tur = 38 ta (N=20 bo'lsa)

    conn = get_connection()
    cursor = conn.cursor()

    matches_created = 0
    for matchday_index, round_pairs in enumerate(full_schedule, start=1):
        for (player1_id, player2_id) in round_pairs:
            cursor.execute(
                """
                INSERT INTO matches
                    (league_id, matchday, player1_id, player2_id, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (league_id, matchday_index, player1_id, player2_id, MATCH_STATUS_PENDING),
            )
            matches_created += 1

    conn.commit()
    conn.close()
    return matches_created


def get_league_player_ids(league_id: int) -> list[int]:
    """Liganing barcha ro'yxatdan o'tgan o'yinchilari ID larini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM registrations WHERE league_id = ?", (league_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["user_id"] for row in rows]


def get_matches_by_matchday(league_id: int, matchday: int) -> list[dict]:
    """Berilgan liga va kun (tur) uchun barcha matchlarni qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM matches WHERE league_id = ? AND matchday = ?",
        (league_id, matchday),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
