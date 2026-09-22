"""
wc_eligibility.py — JCh'da ro'yxatdan o'tish huquqi (2026-09-22).

Muammo (qoida #52): JCh'ga istalgan kishi ro'yxatdan o'ta olardi. Endi u
Divizionning mukofoti bo'lishi kerak — faqat kuchlilar tushsin.

Qoida: Divizion mavsumi yakunlanganda reytingdagi TOP-48 ishtirokchi JCh'da
ro'yxatdan o'tish huquqini oladi. 48 raqami tasodifiy emas — JCh sig'imi ham
roppa-rosa 48 (12 guruh x WC_TEAMS_PER_GROUP=4).

HAR MAVSUMDA RO'YXAT ALMASHADI (admin qarori): yangi top-48 yozilishidan
oldin eski ro'yxat butunlay o'chiriladi. Ya'ni o'tgan mavsumda huquq olgan,
lekin bu safar 48 talikka kirmagan ishtirokchi huquqini yo'qotadi.

TEGILMAGAN: allaqachon ro'yxatdan o'tganlar (wc_registrations). JCh mavsumini
yakunlash reset_wc_data() orqali ularni o'zi tozalaydi, shuning uchun bu modul
faqat YANGI ro'yxatdan o'tishlarni boshqaradi (qoida #02).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

# JCh sig'imi bilan bir xil: 12 guruh x 4 o'yinchi.
# Konstanta sifatida — wc_data'dan hisoblanadi, qo'lda yozilmaydi (qoida #17).
def wc_slots_count() -> int:
    """JCh'dagi umumiy joy soni (12 guruh x 4 = 48)."""
    from wc_data import WC_GROUP_LETTERS, WC_TEAMS_PER_GROUP
    return len(WC_GROUP_LETTERS) * WC_TEAMS_PER_GROUP


def rebuild_wc_eligible(cursor, season_number: int, rating: list[dict]) -> int:
    """
    Divizion reytingidan top-N ni wc_eligible ga yozadi (eski ro'yxat o'chadi).

    cursor — OCHIQ tranzaksiya kursori (finalize_division_season ichidan
    chaqiriladi, shuning uchun bu yerda COMMIT qilinmaydi — sovrinlar bilan
    BIR tranzaksiyada saqlanadi, qoida #38).
    rating — div_rating() natijasi (kamayish tartibida).

    Qaytaradi: yozilgan ishtirokchilar soni.
    """
    limit = wc_slots_count()
    # Faqat o'yin o'ynaganlar (sovrinlar mantig'i bilan bir xil filtr)
    played = [p for p in rating if p.get("played", 0) > 0][:limit]

    cursor.execute("DELETE FROM wc_eligible")
    for place, p in enumerate(played, start=1):
        cursor.execute(
            "INSERT INTO wc_eligible (user_id, telegram_id, place, season_number, points) "
            "VALUES (?, (SELECT telegram_id FROM users WHERE id = ?), ?, ?, ?)",
            (p["user_id"], p["user_id"], place, season_number, p.get("points", 0)),
        )
    logger.info("JCh huquqi yangilandi: %s ishtirokchi (Divizion %s-mavsum top-%s)",
                len(played), season_number, limit)
    return len(played)


def is_wc_eligible(user_id: int) -> bool:
    """Shu foydalanuvchi JCh'ga ro'yxatdan o'ta oladimi?"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM wc_eligible WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def wc_eligibility_status(user_id: int) -> dict:
    """
    Frontend uchun holat: huquq bormi, ro'yxat umuman shakllanganmi.

    Qaytaradi: {
      "eligible": bool,        # shu odam o'ta oladimi
      "place": int | None,     # divizion reytingidagi o'rni
      "total": int,            # ro'yxatdagi umumiy odam soni
      "slots": int,            # JCh sig'imi (48)
      "season_number": int | None,  # qaysi divizion mavsumidan
    }

    total = 0 bo'lsa — Divizion mavsumi hali yakunlanmagan, ya'ni hali
    HECH KIM ro'yxatdan o'ta olmaydi. Frontend shunga qarab tushuntiradi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) AS n, MAX(season_number) AS s FROM wc_eligible")
        agg = cursor.fetchone()
        cursor.execute(
            "SELECT place, season_number FROM wc_eligible WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return {
            "eligible": row is not None,
            "place": row["place"] if row else None,
            "total": agg["n"] or 0,
            "slots": wc_slots_count(),
            "season_number": (row["season_number"] if row else agg["s"]),
        }
    finally:
        conn.close()
