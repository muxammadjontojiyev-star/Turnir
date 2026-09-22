"""
division_bye.py — Divizion "baraban" (toq qolgan ishtirokchi achkosi), 2026-09-22.

Muammo (qoida #52): Divizionda ro'yxatdan o'tganlar soni toq bo'lsa, raqib
yetmagan ishtirokchiga avtomatik g'alaba (+15) berilardi — u hech narsa
qilmasdan eng yuqori achkoni olardi.

Yechim: raqibsiz qolgan ishtirokchi BARABAN aylantiradi. 6 ta qism:
bitta 15, ikkita 10, uchta 5 (config.DIV_BYE_WHEEL). Ehtimollik teng, ya'ni
15 ga tushish 1/6, 10 ga 2/6, 5 ga 3/6.

MUHIM QARORLAR (admin):
  1. Aylantirmasa — DIV_BYE_MIN (5) beriladi. Shuning uchun aylantirilmagan
     baraban reytingda ham 5 bo'lib turadi: bu KAFOLATLANGAN MINIMUM,
     aylantirgach faqat oshishi mumkin.
  2. ESKI yozuvlar (bye_wheel = 0) tegilmaydi — ular +15 bo'lib qoladi.
  3. Faqat o'sha kun aylantiriladi: o'yin kuni X, deadline X+1 kuni 16:00
     (div_pair_day 20:00 da qur'a qiladi, o'ynash ertasi 16:00 gacha).

NATIJA SERVERDA ANIQLANADI (qoida #41): klient faqat animatsiyani ko'rsatadi.
Aks holda ishtirokchi natijani o'zi tanlab olardi.
"""

import logging
import random
from datetime import datetime, timedelta

from config import DIV_BYE_WHEEL, DIV_BYE_MIN, DIV_DEADLINE_HOUR, DIV_DEADLINE_MINUTE
from models import get_connection
from queries_leagues import _tournament_now

logger = logging.getLogger(__name__)


def bye_deadline_passed(day: str) -> bool:
    """
    Shu kun uchun baraban muddati o'tdimi?

    O'yin kuni X uchun deadline — X+1 kuni DIV_DEADLINE_HOUR:MINUTE
    (scheduler div_auto_resolve_day bilan bir xil mantiq — qoida #26).
    """
    try:
        d = datetime.strptime(day, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        logger.warning("bye_deadline_passed: noto'g'ri kun %r", day)
        return True
    now = _tournament_now()
    deadline = datetime.combine(
        d + timedelta(days=1),
        datetime.min.time().replace(hour=DIV_DEADLINE_HOUR, minute=DIV_DEADLINE_MINUTE),
    ).replace(tzinfo=now.tzinfo)
    return now >= deadline


def _find_bye(cursor, user_id: int):
    """Foydalanuvchining baraban tizimidagi ENG SO'NGGI bye o'yini."""
    cursor.execute(
        "SELECT id, day, bye_points FROM div_matches "
        "WHERE player1_id = ? AND player2_id IS NULL AND bye_wheel = 1 "
        "ORDER BY day DESC, id DESC LIMIT 1",
        (user_id,),
    )
    return cursor.fetchone()


def get_bye_state(user_id: int) -> dict:
    """
    Frontend uchun holat.

    Qaytaradi: {
      "has_bye":   bool,        # baraban tizimidagi bye bormi
      "day":       str | None,
      "spun":      bool,        # aylantirilganmi
      "points":    int | None,  # natija (aylantirilgan bo'lsa)
      "expired":   bool,        # muddat o'tganmi
      "can_spin":  bool,        # hozir aylantira oladimi
      "segments":  list[int],   # baraban qismlari (ko'rsatish uchun)
      "min_points": int,
    }
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        row = _find_bye(cursor, user_id)
    finally:
        conn.close()

    base = {"segments": list(DIV_BYE_WHEEL), "min_points": DIV_BYE_MIN}
    if row is None:
        return {"has_bye": False, "day": None, "spun": False, "points": None,
                "expired": False, "can_spin": False, **base}

    day = row["day"]
    spun = row["bye_points"] is not None
    expired = bye_deadline_passed(day)
    return {
        "has_bye": True,
        "day": day,
        "spun": spun,
        "points": row["bye_points"],
        "expired": expired,
        "can_spin": (not spun) and (not expired),
        **base,
    }


def spin_bye_wheel(user_id: int) -> tuple[bool, str, dict]:
    """
    Barabanni aylantiradi va natijani saqlaydi.

    Qaytaradi: (ok, reason, info)
      reason: ok | no_bye | already_spun | expired | spin_failed
      info (ok bo'lsa): {"points", "index", "day", "segments"}
        index — qaysi qism (animatsiya shu qismda to'xtashi uchun)

    IDEMPOTENT (qoida #38): UPDATE sharti "bye_points IS NULL" — tugma ikki
    marta bosilsa ikkinchisi 0 qator o'zgartiradi va already_spun qaytadi.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        row = _find_bye(cursor, user_id)
        if row is None:
            cursor.execute("ROLLBACK")
            return False, "no_bye", {}
        if row["bye_points"] is not None:
            cursor.execute("ROLLBACK")
            return False, "already_spun", {"points": row["bye_points"], "day": row["day"]}
        if bye_deadline_passed(row["day"]):
            cursor.execute("ROLLBACK")
            return False, "expired", {"day": row["day"], "points": DIV_BYE_MIN}

        # Natija SERVERDA — klient tanlay olmaydi (qoida #41)
        index = random.randrange(len(DIV_BYE_WHEEL))
        points = DIV_BYE_WHEEL[index]

        cursor.execute(
            "UPDATE div_matches SET bye_points = ? WHERE id = ? AND bye_points IS NULL",
            (points, row["id"]),
        )
        if cursor.rowcount == 0:      # parallel so'rov bizdan oldin ulgurdi
            cursor.execute("ROLLBACK")
            return False, "already_spun", {}
        cursor.execute("COMMIT")

        logger.info("Divizion baraban: user_id=%s kun=%s natija=%s achko",
                    user_id, row["day"], points)
        return True, "ok", {
            "points": points,
            "index": index,
            "day": row["day"],
            "segments": list(DIV_BYE_WHEEL),
        }
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("spin_bye_wheel: ROLLBACK xatosi")
        logger.exception("spin_bye_wheel xatosi (user_id=%s)", user_id)
        return False, "spin_failed", {}
    finally:
        conn.close()
