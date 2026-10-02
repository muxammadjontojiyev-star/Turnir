"""
Yevropa ligasi — ishtirokchi profili (WebApp "Profil" tabi uchun).
cl_profile.py naqshi, ALOHIDA nusxa.

Bitta vazifa (qoida #25): YeL kartochkasi — nickname, klub, umumiy reytingdagi
o'rni va statistikasi. Avatar: mavjud GET /players/{user_id}/photo (qoida #26).
"""

from el_core import el_group_rating
from models import get_connection

_STAT_KEYS = ("played", "wins", "draws", "losses",
              "goals_for", "goals_against", "goal_difference", "points")


def el_get_profile(user_id: int, season: int) -> dict:
    """
    Qaytaradi: {registered, user_id, nickname, club_name, group_number, position, <statistika>}
    Ishtirokchi bo'lmasa: {"registered": False, "user_id"}.
    Qur'agacha: group_number/position = None, statistika 0.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT p.user_id, p.nickname, p.group_number, "
            "COALESCE(r.club_name, p.club_name) AS club_name "
            "FROM el_participants p "
            "LEFT JOIN registrations r ON r.user_id = p.user_id "
            "WHERE p.season = ? AND p.user_id = ?",
            (season, user_id),
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    if not row:
        return {"registered": False, "user_id": user_id}

    profile = {"registered": True, "user_id": row["user_id"], "nickname": row["nickname"],
               "club_name": row["club_name"], "group_number": row["group_number"],
               "position": None, **{k: 0 for k in _STAT_KEYS}}
    if not row["group_number"]:
        return profile

    for i, r in enumerate(el_group_rating(row["group_number"], season), start=1):
        if r["user_id"] == user_id:
            profile["position"] = i
            profile.update({k: r[k] for k in _STAT_KEYS})
            break
    return profile
