"""
Mavsum yakuni tabrigi — bir martalik oyna mantig'i.

Mavsum yakunlangach (season_state.current_season oshgach) har bir ishtirokchi
web app'ga birinchi kirganida:
  - sovrin YUTGAN bo'lsa — salyut/animatsiya bilan tabrik (o'z sovrinlari ro'yxati),
  - yutmagan bo'lsa — sovrindorlar ro'yxati (sovrin rasmi bilan).
Ko'rsatilgani season_celebration_seen jadvalida belgilanadi (bir marta, qoida #38).

Hozircha faqat LIGA mavsumi (season_kind='league') uchun ishlatiladi.
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

_KIND_LEAGUE = "league"


def _last_finished_league_season(cursor) -> int:
    """Oxirgi YAKUNLANGAN liga mavsumi raqami (joriy - 1). 0 => hali yakunlanmagan."""
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    current = row["current_season"] if row else 1
    return current - 1


def _season_winners(cursor, season: int) -> list[dict]:
    """
    Berilgan liga mavsumi sovrindorlari.
    Qaytaradi: [{prize_type, league_id, league_name, telegram_id, nickname}, ...]
    users reset'da o'chirilmaydi, shuning uchun nickname JOIN orqali olinadi;
    topilmasa 'Ishtirokchi' fallback (frontendda ko'rsatish uchun).
    """
    cursor.execute(
        """
        SELECT sp.prize_type, sp.league_id, sp.telegram_id,
               l.name AS league_name,
               u.nickname AS nickname
        FROM season_prizes sp
        LEFT JOIN leagues l ON l.id = sp.league_id
        LEFT JOIN users u ON u.telegram_id = sp.telegram_id
        WHERE sp.season_number = ? AND sp.season_kind = ?
        ORDER BY sp.id ASC
        """,
        (season, _KIND_LEAGUE),
    )
    winners = []
    for r in cursor.fetchall():
        d = dict(r)
        if not d.get("nickname"):
            d["nickname"] = "Ishtirokchi"
        winners.append(d)
    return winners


def get_celebration(telegram_id: int) -> dict:
    """
    Foydalanuvchi uchun tabrik oynasi ma'lumoti.

    Qaytaradi:
      {"show": False}  — ko'rsatilmaydi (mavsum yakunlanmagan / allaqachon ko'rilgan /
                          sovrindorlar yo'q), yoki
      {"show": True, "season": N, "is_winner": bool,
       "my_prizes": [...], "winners": [...]}
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        season = _last_finished_league_season(cursor)
        if season < 1:
            return {"show": False}

        cursor.execute(
            "SELECT 1 FROM season_celebration_seen "
            "WHERE telegram_id = ? AND season_number = ? AND season_kind = ?",
            (telegram_id, season, _KIND_LEAGUE),
        )
        if cursor.fetchone():
            return {"show": False}

        winners = _season_winners(cursor, season)
        if not winners:
            # Sovrindorlar yozilmagan mavsum — ko'rsatadigan narsa yo'q
            return {"show": False}

        my_prizes = [w for w in winners if w["telegram_id"] == telegram_id]
        return {
            "show": True,
            "season": season,
            "is_winner": bool(my_prizes),
            "my_prizes": my_prizes,
            "winners": winners,
        }
    finally:
        conn.close()


def mark_celebration_seen(telegram_id: int) -> dict:
    """
    Oxirgi yakunlangan mavsum tabrigi "ko'rildi" deb belgilaydi.
    INSERT OR IGNORE — takroriy bosishda ikki marta yozilmaydi (qoida #38).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        season = _last_finished_league_season(cursor)
        if season < 1:
            return {"status": "ok", "season": None}
        cursor.execute(
            "INSERT OR IGNORE INTO season_celebration_seen "
            "(telegram_id, season_number, season_kind) VALUES (?, ?, ?)",
            (telegram_id, season, _KIND_LEAGUE),
        )
        conn.commit()
        return {"status": "ok", "season": season}
    finally:
        conn.close()
