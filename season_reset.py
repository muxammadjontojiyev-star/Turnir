"""
Mavsum reset — yangi mavsum boshlanganda eski ma'lumotlarni tozalash.

Talab: yangi mavsumda hamma YANGIDAN ro'yxatdan o'tsin. Shuning uchun mavsum
yakunlangach (sovrinlar SAQLANIB) tegishli ro'yxat/o'yin/holat tozalanadi.

MUHIM qarorlar (loyiha egasi):
- `users` jadvaliga TEGILMAYDI (liga+WC umumiy; odam qayta kirsa telegram_id
  bo'yicha baribir tanaladi). Sovrinlar telegram_id ga bog'langan — reset'dan
  keyin ham egasiga bog'liq qoladi.
- Liga va WC ALOHIDA: `reset_league_data()` faqat liga jadvallarini,
  `reset_wc_data()` faqat WC jadvallarini tozalaydi.

FK/self-ref muammosini oldini olish uchun reset o'z ulanishida
`PRAGMA foreign_keys = OFF` bilan, bitta tranzaksiyada bajariladi. (users
o'chirilmagani uchun users'ga ishora qiluvchi FK'lar baribir buzilmaydi;
OFF faqat wc_playoff_matches.next_match_id o'z-o'ziga ishorasi va
messages->matches tartibi uchun xavfsizlik.)
"""

import logging
import sqlite3

from config import DB_PATH

logger = logging.getLogger(__name__)


def _reset_connection():
    """Reset uchun alohida ulanish — FK tekshiruvi OFF (o'chirish tartibi erkin)."""
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


# Liga kontenti (users TEGILMAYDI). Tartib muhim emas (FK OFF).
_LEAGUE_TABLES = ["messages", "chat_notify", "chat_typing", "matches", "registrations", "prizes"]

# WC kontenti (users TEGILMAYDI).
_WC_TABLES = [
    "wc_messages", "wc_chat_notify", "wc_chat_typing",
    "wc_playoff_matches", "wc_matches", "wc_registrations", "wc_groups",
]


def reset_league_data() -> dict:
    """
    Liga ma'lumotlarini tozalaydi (yangi liga mavsumi uchun):
      - registrations, matches, liga chat (messages/notify/typing), prizes
      - leagues: status='open', draw_date=NULL, notified/deadline hisoblagichlar 0/NULL

    users, leagues qatorlarining O'ZI (nomi/max_players), season_prizes — TEGILMAYDI.
    Qaytaradi: {"tables": {jadval: o'chirilgan_qatorlar}}
    """
    conn = _reset_connection()
    cursor = conn.cursor()
    counts = {}
    try:
        cursor.execute("BEGIN")
        for tbl in _LEAGUE_TABLES:
            cursor.execute(f"DELETE FROM {tbl}")
            counts[tbl] = cursor.rowcount
        # Ligalarni "ochiq" holatga qaytaramiz (qur'a/tur hisoblagichlari nol)
        cursor.execute(
            "UPDATE leagues SET status = 'open', draw_date = NULL, "
            "last_notified_matchday = 0, last_deadline_notice_date = NULL"
        )
        counts["leagues_reset"] = cursor.rowcount
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        conn.close()
        logger.exception("reset_league_data xatosi")
        raise
    conn.close()
    return {"tables": counts}


def reset_wc_data() -> dict:
    """
    WC ma'lumotlarini tozalaydi (yangi WC mavsumi uchun):
      - wc_registrations, wc_matches, wc_playoff_matches, wc chat, wc_groups
      - wc_playoff_state: started=0, start_date=NULL

    users, season_prizes — TEGILMAYDI.
    Qaytaradi: {"tables": {jadval: o'chirilgan_qatorlar}}
    """
    conn = _reset_connection()
    cursor = conn.cursor()
    counts = {}
    try:
        cursor.execute("BEGIN")
        for tbl in _WC_TABLES:
            cursor.execute(f"DELETE FROM {tbl}")
            counts[tbl] = cursor.rowcount
        # Play-off holatini boshlang'ich (boshlanmagan) holatga qaytaramiz
        cursor.execute("UPDATE wc_playoff_state SET started = 0, start_date = NULL WHERE id = 1")
        counts["wc_playoff_state_reset"] = cursor.rowcount
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        conn.close()
        logger.exception("reset_wc_data xatosi")
        raise
    conn.close()
    return {"tables": counts}
