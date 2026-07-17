"""
division_bans.py — Divizion kunlik ban tizimi (2026-07-17).

Admin (faqat bosh admin — api.py'da himoyalangan) qoidabuzar ishtirokchiga
istalgancha KUNLIK ban beradi:
  - ban start_day (bugun) dan until_day (bugun + kun - 1) gacha amal qiladi
    (ikkala kun ham kiradi);
  - ban davrida ishtirokchi Divizion ro'yxatidan O'TA OLMAYDI
    (division.div_register tekshiradi);
  - ban kunlari ro'yxat kalendarida qizil ko'rinadi (div_registration_days
    "banned" ro'yxatini qo'shadi — o'z profilida ham, boshqalar ko'rganda ham);
  - ban berilganda ishtirokchi telegramiga xabar boradi (api.py endpoint).

Jadval: div_bans (models.py). Sana taqqoslash ISO ("YYYY-MM-DD") satrlarida —
leksikografik tartib sana tartibiga teng.
"""

import logging
from datetime import timedelta

from models import get_connection
from queries_leagues import _tournament_now

logger = logging.getLogger(__name__)

# Bitta ban uchun maksimal kunlar (himoya — xato kiritilgan ulkan son o'tmasin)
MAX_BAN_DAYS = 365


def div_ban_user(user_id: int, days: int) -> tuple[bool, str | dict]:
    """
    Ishtirokchiga bugundan boshlab `days` kunlik ban beradi.

    Qaytaradi: (True, {start_day, until_day, days, telegram_id, language,
    nickname, username}) yoki (False, sabab).
    Sabablar: invalid_days, user_not_found.
    """
    if not isinstance(days, int) or days < 1 or days > MAX_BAN_DAYS:
        return False, "invalid_days"

    now = _tournament_now()
    start_day = now.strftime("%Y-%m-%d")
    until_day = (now + timedelta(days=days - 1)).strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, telegram_id, language, nickname, username "
            "FROM users WHERE id = ?",
            (user_id,),
        )
        u = cursor.fetchone()
        if not u:
            return False, "user_not_found"

        cursor.execute(
            "INSERT INTO div_bans (user_id, telegram_id, start_day, until_day, days) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, u["telegram_id"], start_day, until_day, days),
        )
        conn.commit()
        logger.info("Divizion ban: user %s (tg %s) -> %s kungacha (%d kun)",
                    user_id, u["telegram_id"], until_day, days)
        return True, {
            "start_day": start_day, "until_day": until_day, "days": days,
            "telegram_id": u["telegram_id"], "language": u["language"],
            "nickname": u["nickname"], "username": u["username"],
        }
    finally:
        conn.close()


def div_is_banned(telegram_id: int, day: str | None = None) -> bool:
    """Berilgan kunda (None -> bugun) ishtirokchi ban ostidami?"""
    day = day or _tournament_now().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT 1 FROM div_bans "
            "WHERE telegram_id = ? AND start_day <= ? AND until_day >= ? LIMIT 1",
            (telegram_id, day, day),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def div_banned_days_month(user_id: int, month: str) -> list[str]:
    """
    Shu OYGA to'g'ri kelgan ban kunlari ro'yxati (kalendar uchun).
    month: "YYYY-MM". Oraliqlar oy chegarasi bilan kesishtiriladi.
    """
    month_start = f"{month}-01"
    month_end = f"{month}-31"   # ISO satr taqqoslashda oy oxiri uchun yetarli
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT start_day, until_day FROM div_bans "
            "WHERE user_id = ? AND start_day <= ? AND until_day >= ?",
            (user_id, month_end, month_start),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    banned: set[str] = set()
    for r in rows:
        # Oraliqni kunma-kun ochamiz (oy bilan kesishgan qismi)
        from datetime import date
        s = date.fromisoformat(max(r["start_day"], month_start))
        # month_end "YYYY-MM-31" haqiqiy sana bo'lmasligi mumkin — until bilan cheklaymiz
        e = date.fromisoformat(r["until_day"])
        d = s
        while d <= e:
            iso = d.isoformat()
            if iso.startswith(month):
                banned.add(iso)
            elif iso > month_end:
                break
            d += timedelta(days=1)
    return sorted(banned)
