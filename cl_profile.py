"""
Chempionlar ligasi — ishtirokchi profili (WebApp "Profil" tabi uchun).

Bitta vazifa (qoida #25): ishtirokchining ChL kartochkasini yig'ish —
nickname, klub, guruh, guruhdagi o'rni va statistikasi.
Avatar rasmi alohida mavjud endpoint orqali keladi: GET /players/{user_id}/photo
(qoida #26 — takrorlanmasin).
"""

from models import get_connection
from cl_core import cl_group_rating


def cl_get_profile(user_id: int, season: int) -> dict:
    """
    Qaytaradi:
      {registered: bool, user_id, nickname, club_name, group_number,
       position, played, wins, draws, losses, goals_for, goals_against,
       goal_difference, points}
    Ishtirokchi bo'lmasa: {"registered": False}.
    Qur'a bo'lmagan bo'lsa: group_number/position = None, statistika 0.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT user_id, nickname, club_name, group_number "
            "FROM cl_participants WHERE season = ? AND user_id = ?",
            (season, user_id),
        )
        row = cursor.fetchone()
        if not row:
            return {"registered": False, "user_id": user_id}
        p = dict(row)
    finally:
        conn.close()

    profile = {
        "registered": True,
        "user_id": p["user_id"],
        "nickname": p["nickname"],
        "club_name": p["club_name"],
        "group_number": p["group_number"],
        "position": None,
        "played": 0, "wins": 0, "draws": 0, "losses": 0,
        "goals_for": 0, "goals_against": 0, "goal_difference": 0, "points": 0,
    }
    if not p["group_number"]:
        return profile

    table = cl_group_rating(p["group_number"], season)
    for i, r in enumerate(table, start=1):
        if r["user_id"] == user_id:
            profile.update({
                "position": i,
                "played": r["played"], "wins": r["wins"],
                "draws": r["draws"], "losses": r["losses"],
                "goals_for": r["goals_for"], "goals_against": r["goals_against"],
                "goal_difference": r["goal_difference"], "points": r["points"],
            })
            break
    return profile
