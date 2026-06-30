"""
wc_rating.py — World Cup guruh reyting jadvalini hisoblash.

Liga rating.py bilan bir xil mantiq (g'alaba=3, durang=1, mag'lubiyat=0;
saralash: ball > gol farqi > urilgan gollar), faqat wc_matches /
wc_registrations jadvallaridan o'qiydi, group_letter bo'yicha.
Faqat 'confirmed' o'yinlar hisobga olinadi.
"""

from models import get_connection
from config import MATCH_STATUS_CONFIRMED


def calculate_wc_group_rating(group_letter: str) -> list[dict]:
    """
    Guruh uchun to'liq reyting jadvalini hisoblaydi.

    Qaytaradi: ball bo'yicha kamayuvchi tartibda dict ro'yxati:
        {user_id, nickname, username, team_name, played, wins, draws, losses,
         goals_for, goals_against, goal_difference, points}
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Guruhdagi barcha ro'yxatdan o'tgan o'yinchilar (team_name = WC jamoasi)
    cursor.execute(
        """
        SELECT u.id as user_id, u.nickname, u.username, w.team_name
        FROM wc_registrations w
        JOIN users u ON u.id = w.user_id
        WHERE w.group_letter = ?
        """,
        (group_letter,),
    )
    players = {row["user_id"]: {
        "user_id": row["user_id"],
        "nickname": row["nickname"],
        "username": row["username"],
        "team_name": row["team_name"],
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "points": 0,
    } for row in cursor.fetchall()}

    # Faqat tasdiqlangan o'yinlar
    cursor.execute(
        """
        SELECT player1_id, player2_id, score1, score2
        FROM wc_matches
        WHERE group_letter = ? AND status = ?
        """,
        (group_letter, MATCH_STATUS_CONFIRMED),
    )
    matches = cursor.fetchall()
    conn.close()

    for m in matches:
        p1, p2 = m["player1_id"], m["player2_id"]
        s1, s2 = m["score1"], m["score2"]
        if p1 not in players or p2 not in players:
            continue

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

    rating_list.sort(
        key=lambda p: (p["points"], p["goal_difference"], p["goals_for"]),
        reverse=True,
    )
    return rating_list


def get_wc_player_position(group_letter: str, user_id: int) -> dict | None:
    """
    Foydalanuvchining WC guruh reytingidagi joylashuvini qaytaradi.

    Qaytaradi: {position, ...reyting ma'lumotlari} yoki None (topilmasa).
    """
    rating_list = calculate_wc_group_rating(group_letter)
    for index, player in enumerate(rating_list, start=1):
        if player["user_id"] == user_id:
            return {"position": index, **player}
    return None


def calculate_wc_top_scorers() -> list[dict]:
    """
    Barcha WC guruhlardagi o'yinchilarni eng ko'p gol (goals_for) bo'yicha
    tartiblaydi. Liga top-scorers naqshining WC versiyasi.

    Faqat gol urgan (goals_for > 0) o'yinchilar. Har biriga group_letter qo'shiladi.
    Format: [{user_id, nickname, username, team_name, group_letter, goals_for, ...}, ...]
    """
    from wc_data import WC_GROUP_LETTERS

    all_players = []
    for letter in WC_GROUP_LETTERS:
        rating = calculate_wc_group_rating(letter)
        for player in rating:
            player["group_letter"] = letter
            all_players.append(player)

    # Faqat gol urganlar, gol bo'yicha kamayish tartibida
    scorers = [p for p in all_players if p.get("goals_for", 0) > 0]
    scorers.sort(key=lambda p: p["goals_for"], reverse=True)
    return scorers
