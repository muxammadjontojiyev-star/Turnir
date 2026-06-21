"""
rating.py — Liga reyting jadvalini hisoblash.

Faqat 'confirmed' statusdagi matchlar hisobga olinadi.
Hisoblash mantig'i: g'alaba=3 ball, durang=1 ball, mag'lubiyat=0 ball
(real futbol reytingi standartiga mos).
"""

from models import get_connection
from config import MATCH_STATUS_CONFIRMED


def calculate_league_rating(league_id: int) -> list[dict]:
    """
    Liga uchun to'liq reyting jadvalini hisoblaydi.

    Qaytaradi: har bir o'yinchi uchun dict ro'yxati, ball bo'yicha kamayish tartibida:
        {user_id, nickname, played, wins, draws, losses,
         goals_for, goals_against, goal_difference, points}
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Ligadagi barcha ro'yxatdan o'tgan o'yinchilar
    cursor.execute(
        """
        SELECT u.id as user_id, u.nickname
        FROM registrations r
        JOIN users u ON u.id = r.user_id
        WHERE r.league_id = ?
        """,
        (league_id,),
    )
    players = {row["user_id"]: {
        "user_id": row["user_id"],
        "nickname": row["nickname"],
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "points": 0,
    } for row in cursor.fetchall()}

    # Faqat tasdiqlangan matchlar
    cursor.execute(
        """
        SELECT player1_id, player2_id, score1, score2
        FROM matches
        WHERE league_id = ? AND status = ?
        """,
        (league_id, MATCH_STATUS_CONFIRMED),
    )
    matches = cursor.fetchall()
    conn.close()

    for m in matches:
        p1, p2 = m["player1_id"], m["player2_id"]
        s1, s2 = m["score1"], m["score2"]

        if p1 not in players or p2 not in players:
            continue  # ehtiyot chorasi: ro'yxatdan o'chirilgan o'yinchi bo'lsa

        players[p1]["played"] += 1
        players[p2]["played"] += 1
        players[p1]["goals_for"] += s1
        players[p1]["goals_against"] += s2
        players[p2]["goals_for"] += s2
        players[p2]["goals_against"] += s1

        if s1 > s2:
            players[p1]["wins"] += 1
            players[p1]["points"] += 3
            players[p2]["losses"] += 1
        elif s2 > s1:
            players[p2]["wins"] += 1
            players[p2]["points"] += 3
            players[p1]["losses"] += 1
        else:
            players[p1]["draws"] += 1
            players[p2]["draws"] += 1
            players[p1]["points"] += 1
            players[p2]["points"] += 1

    rating_list = list(players.values())
    for p in rating_list:
        p["goal_difference"] = p["goals_for"] - p["goals_against"]

    # Saralash: ball > gol farqi > urilgan gollar (standart futbol reytingi tartibi)
    rating_list.sort(
        key=lambda p: (p["points"], p["goal_difference"], p["goals_for"]),
        reverse=True,
    )

    return rating_list


def get_player_position(league_id: int, user_id: int) -> dict | None:
    """
    Berilgan o'yinchining liga reytingidagi joylashuvini qaytaradi.

    Qaytaradi: {position, ...reyting ma'lumotlari} yoki None (agar liga/user topilmasa).
    """
    rating_list = calculate_league_rating(league_id)
    for index, player in enumerate(rating_list, start=1):
        if player["user_id"] == user_id:
            return {"position": index, **player}
    return None
