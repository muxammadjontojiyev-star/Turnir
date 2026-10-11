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
            "SELECT place, season_number, via FROM wc_eligible WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return {
            "eligible": row is not None,
            "place": row["place"] if row else None,
            "via": row["via"] if row else None,      # 2026-10-11: division | admin
            "total": agg["n"] or 0,
            "slots": wc_slots_count(),
            "season_number": (row["season_number"] if row else agg["s"]),
        }
    finally:
        conn.close()


# ============================================================
#  2026-10-10: admin ko'rinishi va QAYTA HISOBLASH (sovrinlarga tegmaydi)
# ============================================================
# Sabab: Divizion yakunlangach top-48 ishtirokchi JCh'ga o'ta olmadi (admin xabari).
# Yo'llanmalar faqat finalize_division_season ichida yozilardi — admin ro'yxatni
# KO'RA olmasdi va xato bo'lsa qayta yaratolmasdi. Endi ikkalasi mumkin.

def wc_eligible_list() -> dict:
    """Admin uchun: joriy yo'llanma ro'yxati (o'rin tartibida) + qaysi Divizion mavsumidan."""
    from division_finalize import _season_context
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT e.place, e.user_id, e.points, e.season_number, e.via, u.nickname, u.username, "
            "CASE WHEN r.user_id IS NULL THEN 0 ELSE 1 END AS registered "
            "FROM wc_eligible e LEFT JOIN users u ON u.id = e.user_id "
            "LEFT JOIN wc_registrations r ON r.user_id = e.user_id ORDER BY e.place"
        )
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    _, prev_number = _season_context("prev")
    return {
        "total": len(rows),
        "registered": sum(r["registered"] for r in rows),       # 2026-10-11: davlat tanlaganlar
        "free": _free_slots_for(rows),                          # admin qo'sha oladigan o'rinlar
        "slots": wc_slots_count(),
        "season_number": rows[0]["season_number"] if rows else None,
        "prev_season_number": prev_number,   # "qayta hisoblash" shu mavsumdan oladi
        "list": rows,
    }


def rebuild_wc_eligible_from_division(season: str | None = "prev") -> tuple[bool, str, dict]:
    """
    Bosh admin: yo'llanmalarni Divizion reytingidan QAYTA yozadi (sovrinlar tegilmaydi).
    season='prev' (standart) — tugagan mavsum; 'current' — joriy mavsum.
    Idempotent: rebuild_wc_eligible eski ro'yxatni o'chirib qayta yozadi (qoida #38).
    Qaytaradi: (ok, reason, {season_number, count}); reason: ok | no_participants | rebuild_failed
    """
    from division import div_rating
    from division_finalize import _season_context
    day, season_number = _season_context(season)
    rating = div_rating(day)
    if not any(p.get("played", 0) > 0 for p in rating):
        return False, "no_participants", {"season_number": season_number}

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        count = rebuild_wc_eligible(cursor, season_number, rating)
        cursor.execute("COMMIT")
        return True, "ok", {"season_number": season_number, "count": count}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("rebuild_wc_eligible_from_division: ROLLBACK xatosi")
        logger.exception("rebuild_wc_eligible_from_division xatosi")
        return False, "rebuild_failed", {"season_number": season_number}
    finally:
        conn.close()


# ============================================================
#  2026-10-11: O'RNIGA QO'SHISH — admin Telegram ID'lar ro'yxati bilan yo'llanma beradi
# ============================================================
# Admin so'rovi: top-48 ning bir qismi kanal/botdan chiqib ketgan va davlat tanlamayapti.
# Admin bo'sh qolgan o'rinlarga istalgan odamlarni Telegram ID bilan BIR YO'LA qo'shadi.
# Qoida: Divizion orqali yo'llanma olib, HALI davlat tanlamaganlarning huquqi bekor qilinadi
# (via='division' va wc_registrations'da yo'q). Admin qo'shganlar (via='admin') saqlanadi.
# Bo'sh o'rin = JCh sig'imi - ro'yxatdan o'tganlar - hali tanlamagan admin qo'shganlar.

def _free_slots_for(rows: list[dict]) -> int:
    """wc_eligible_list qatorlaridan: admin yana nechta odam qo'sha oladi."""
    registered = sum(r["registered"] for r in rows)
    waiting_admin = sum(1 for r in rows if r.get("via") == "admin" and not r["registered"])
    return max(0, wc_slots_count() - registered - waiting_admin)


def parse_telegram_ids(text: str) -> list[int]:
    """'123, 456\n789' -> [123, 456, 789] (takrorsiz, tartib saqlanadi; raqam bo'lmaganlar tashlanadi)."""
    import re
    out = []
    for tok in re.split(r"[\s,;]+", text or ""):
        if tok.isdigit() and int(tok) not in out:
            out.append(int(tok))
    return out


def wc_eligible_add_bulk(telegram_ids: list[int]) -> tuple[bool, str, dict]:
    """
    Bo'sh o'rinlarga yo'llanma beradi (BIR tranzaksiyada, qoida #38).
    Qaytaradi: (ok, reason, info) — reason: ok | empty | too_many | none_added
      info: {added: [{telegram_id, user_id, nickname, language}], not_found: [tg], already: [tg],
             revoked: int, free: int}
    Hech bo'lmaganda bitta qo'shilmasa — o'zgarish saqlanmaydi (none_added).
    """
    if not telegram_ids:
        return False, "empty", {}
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        # 1) Divizion orqali olib, davlat tanlamaganlarning huquqi bekor
        cursor.execute("DELETE FROM wc_eligible WHERE via = 'division' AND user_id NOT IN "
                       "(SELECT user_id FROM wc_registrations)")
        revoked = cursor.rowcount or 0
        # 2) Bo'sh o'rinlar
        cursor.execute("SELECT COUNT(*) AS n FROM wc_registrations")
        registered = cursor.fetchone()["n"]
        cursor.execute("SELECT COUNT(*) AS n FROM wc_eligible WHERE via = 'admin' AND user_id NOT IN "
                       "(SELECT user_id FROM wc_registrations)")
        waiting = cursor.fetchone()["n"]
        free = max(0, wc_slots_count() - registered - waiting)

        added, not_found, already = [], [], []
        candidates = []
        for tg in telegram_ids:
            cursor.execute("SELECT id, nickname, language FROM users WHERE telegram_id = ?", (tg,))
            u = cursor.fetchone()
            if not u:
                not_found.append(tg)
                continue
            cursor.execute("SELECT 1 FROM wc_eligible WHERE user_id = ? UNION "
                           "SELECT 1 FROM wc_registrations WHERE user_id = ?", (u["id"], u["id"]))
            if cursor.fetchone():
                already.append(tg)
                continue
            candidates.append((tg, u))
        if len(candidates) > free:
            cursor.execute("ROLLBACK")
            return False, "too_many", {"free": free, "valid": len(candidates),
                                       "not_found": not_found, "already": already, "revoked": revoked}
        if not candidates:
            cursor.execute("ROLLBACK")
            return False, "none_added", {"free": free, "not_found": not_found, "already": already}

        cursor.execute("SELECT COALESCE(MAX(place), 0) AS p, MAX(season_number) AS s FROM wc_eligible")
        row = cursor.fetchone()
        place, season = row["p"], row["s"]
        if season is None:
            from division_finalize import _season_context
            season = _season_context("prev")[1]
        for tg, u in candidates:
            place += 1
            cursor.execute(
                "INSERT INTO wc_eligible (user_id, telegram_id, place, season_number, points, via) "
                "VALUES (?, ?, ?, ?, NULL, 'admin')", (u["id"], tg, place, season))
            added.append({"telegram_id": tg, "user_id": u["id"], "nickname": u["nickname"],
                          "language": u["language"]})
        cursor.execute("COMMIT")
        logger.info("JCh yo'llanma (admin): +%s, bekor qilindi %s, topilmadi %s, avvaldan %s",
                    len(added), revoked, len(not_found), len(already))
        return True, "ok", {"added": added, "not_found": not_found, "already": already,
                            "revoked": revoked, "free": free - len(added)}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("wc_eligible_add_bulk: ROLLBACK xatosi")
        logger.exception("wc_eligible_add_bulk xatosi")
        raise
    finally:
        conn.close()
