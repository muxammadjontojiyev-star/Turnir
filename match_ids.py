"""
match_ids.py — O'YIN RAQAMLARI KATTALASHIB KETMASIN (2026-11-01).

Egasi so'rovi: 1-mavsumda o'yin raqami (#1234) 4 xonali edi, endi 5 xonali (#18538) bo'lib ketdi —
oshib ketmasin. Sabab: SQLite AUTOINCREMENT hisoblagichi mavsum tozalanganda ham davom etardi.

  * restart_ids(cur, tables) — mavsum tozalanganda (season_reset.py) jadval BO'SH bo'lsa hisoblagich
    nolga qaytadi: keyingi mavsum o'yinlari #1 dan boshlanadi (liga ≤ 4 xona, JCh ≤ 3, ChL/YeL/OChL ≤ 3).
  * renumber_league_matches() — JORIY liga mavsumi uchun bir martalik (har ishga tushishda xavfsiz):
    o'yin raqami 9999 dan katta bo'lsa, hamma liga o'yinlari tartibi saqlangan holda 1 dan qayta
    raqamlanadi va bog'liq jadvallar (liga chati, bildirishnoma, yozmoqda, chat rasmlari) ham yangilanadi.
    Bitta tranzaksiya, FK tekshiruvi o'chiq (_reset_connection) — yarim yangilanib qolmaydi.
"""

import logging

logger = logging.getLogger(__name__)

LEAGUE_ID_LIMIT = 9999           # liga o'yin raqami — ko'pi bilan 4 xona
_LEAGUE_REFS = ("messages", "chat_notify", "chat_typing")   # match_id -> matches.id (nomlar KODDAN, qoida #29)


def restart_ids(cur, tables) -> None:
    """Bo'sh jadvallarning AUTOINCREMENT hisoblagichini nolga qaytaradi (to'la jadvalga tegmaydi)."""
    for t in tables:
        if cur.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone() is None:
            cur.execute("DELETE FROM sqlite_sequence WHERE name = ?", (t,))


def renumber_league_matches() -> int:
    """Qaytaradi: qayta raqamlangan o'yinlar soni (kerak bo'lmasa 0)."""
    from season_reset import _reset_connection
    conn = _reset_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        r = cur.execute("SELECT MIN(id) AS lo, MAX(id) AS hi, COUNT(*) AS n FROM matches").fetchone()
        if not r["n"] or r["hi"] <= LEAGUE_ID_LIMIT:
            cur.execute("ROLLBACK")
            return 0
        offset = r["lo"] - 1
        if r["hi"] - offset > LEAGUE_ID_LIMIT or r["hi"] - offset >= r["lo"]:
            cur.execute("ROLLBACK")          # sig'maydi yoki raqamlar to'qnashadi — tegilmaydi
            logger.warning("O'yin raqamlari: qayta raqamlab bo'lmadi (%s..%s)", r["lo"], r["hi"])
            return 0
        cur.execute("UPDATE matches SET id = id - ?", (offset,))
        for t in _LEAGUE_REFS:
            cur.execute(f"UPDATE {t} SET match_id = match_id - ? WHERE match_id >= ?", (offset, r["lo"]))
        cur.execute("UPDATE chat_images SET match_id = match_id - ? WHERE mode = 'league' AND match_id >= ?",
                    (offset, r["lo"]))
        cur.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM matches) WHERE name = 'matches'")
        cur.execute("COMMIT")
        logger.info("O'yin raqamlari: %s ta liga o'yini qayta raqamlandi (#%s.. -> #1..)", r["n"], r["lo"])
        return r["n"]
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        logger.exception("O'yin raqamlarini qayta raqamlashda xato (o'zgarish bekor)")
        return 0
    finally:
        conn.close()
