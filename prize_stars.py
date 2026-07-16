"""
prize_stars.py — Kubok yulduzchalari (2026-07-16).

Sovrin yutgan ishtirokchilar useri yonida ko'rinadigan yulduzcha (★) soni.
FAQAT kuboklar hisoblanadi: league_cup, wc_cup, cl_cup (kelajak uchun).
Oltin to'p (golden_ball) va oltin butsa (golden_boot, wc_golden_boot)
MUSTASNO — ular yulduzcha bermaydi.

Sovrinlar telegram_id ga bog'langan (mavsum reset'ida users o'chsa ham
qoladi — season_prizes.get_user_prizes bilan bir xil yondashuv), shuning
uchun natija uch xil kalitda qaytariladi:
  by_tg       — telegram_id bo'yicha (asosiy, doimiy)
  by_user     — JORIY users.id bo'yicha (reyting qatorlari user_id beradi)
  by_username — joriy username (lowercase) bo'yicha (zaxira)
"""

from models import get_connection

# Yulduzcha beriladigan sovrin turlari — faqat kuboklar
CUP_PRIZE_TYPES = ("league_cup", "wc_cup", "cl_cup")


def get_cup_star_counts() -> dict:
    """
    Barcha kubok egalari bo'yicha yulduzcha sonlarini qaytaradi.

    Qaytaradi:
      {"by_user": {user_id(str): n}, "by_tg": {telegram_id(str): n},
       "by_username": {username_lower: n}}
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        placeholders = ",".join("?" * len(CUP_PRIZE_TYPES))
        # Bitta so'rov: sovrin + joriy user (telegram_id orqali) — N+1 yo'q (qoida #24)
        cursor.execute(
            f"""
            SELECT sp.telegram_id, sp.user_id AS prize_user_id,
                   u.id AS current_user_id, u.username,
                   COUNT(*) AS cups
            FROM season_prizes sp
            LEFT JOIN users u ON u.telegram_id = sp.telegram_id
            WHERE sp.prize_type IN ({placeholders})
            GROUP BY sp.telegram_id, sp.user_id, u.id, u.username
            """,
            CUP_PRIZE_TYPES,
        )
        by_tg: dict[str, int] = {}
        by_user: dict[str, int] = {}
        by_username: dict[str, int] = {}
        for r in cursor.fetchall():
            cups = r["cups"]
            tg = r["telegram_id"]
            if tg is not None:
                key = str(tg)
                by_tg[key] = by_tg.get(key, 0) + cups
                if r["current_user_id"] is not None:
                    ukey = str(r["current_user_id"])
                    by_user[ukey] = by_user.get(ukey, 0) + cups
                if r["username"]:
                    nkey = str(r["username"]).lower()
                    by_username[nkey] = by_username.get(nkey, 0) + cups
            elif r["prize_user_id"] is not None:
                # Eski yozuvlar (telegram_id NULL) — user_id bo'yicha zaxira
                ukey = str(r["prize_user_id"])
                by_user[ukey] = by_user.get(ukey, 0) + cups
        return {"by_user": by_user, "by_tg": by_tg, "by_username": by_username}
    finally:
        conn.close()
