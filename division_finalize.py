"""
division_finalize.py — Divizion mavsumini yakunlash (2026-08).

Bosh admin divizion mavsumini qo'lda yakunlaydi (liga/WC kabi). Yakunlaganda:
  - div_cup  : joriy mavsum reytingi (div_rating) 1-o'rin egasiga
  - div_boot : to'purarlar (div_scorers) 1-o'rin egasiga
Sovrinlar season_prizes'ga season_kind='division' bilan saqlanadi va barcha
rejim profillarida ko'rinadi (o'ziga ham, boshqalarga ham).

Idempotent (qoida #38): bir divizion mavsumini ikki marta yakunlash dublikat
bermaydi — season_prizes'da UNIQUE(prize_type, season_number, season_kind).

Bu modul faqat SOF mantiq — API handler (api.py) uni chaqiradi (qoida #27).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

DIV_PRIZE_CUP = "div_cup"     # mavsum 1-o'rni
DIV_PRIZE_BOOT = "div_boot"   # to'purarlar 1-o'rni
DIV_SEASON_KIND = "division"


def get_division_season_number() -> int:
    """Joriy divizion mavsum raqami (sana-asosli, division_season)."""
    from division_season import div_current_season
    return div_current_season()["number"]


def preview_division_prizes() -> dict:
    """
    Yakunlashda kim qaysi sovrinni olishini KO'RSATADI (saqlamaydi).
    Admin tasdiqlashdan oldin ko'radi.

    Qaytaradi: {
      "season_number": int,
      "cup":  {user_id, nickname, username, points} | None,
      "boot": {user_id, nickname, username, goals_for} | None,
    }
    """
    from division import div_rating, div_scorers
    rating = div_rating()
    scorers = div_scorers()

    cup = None
    if rating and rating[0].get("played", 0) > 0:
        w = rating[0]
        cup = {"user_id": w["user_id"], "nickname": w.get("nickname"),
               "username": w.get("username"), "points": w.get("points", 0)}

    boot = None
    if scorers and scorers[0].get("goals_for", 0) > 0:
        s = scorers[0]
        boot = {"user_id": s["user_id"], "nickname": s.get("nickname"),
                "username": s.get("username"), "goals_for": s.get("goals_for", 0)}

    return {
        "season_number": get_division_season_number(),
        "cup": cup,
        "boot": boot,
    }


def finalize_division_season() -> tuple[bool, str, dict]:
    """
    Joriy divizion mavsumini yakunlaydi: 1-o'rin (kubok) va to'purar 1-o'rin
    (butsa) sovrinlarini season_prizes'ga saqlaydi. Idempotent.

    Qaytaradi: (ok, reason, info)
      reason: ok | no_participants | already_finalized
      info: {season_number, cup, boot} (saqlanganlar)
    """
    prizes = preview_division_prizes()
    season_number = prizes["season_number"]
    cup, boot = prizes["cup"], prizes["boot"]

    if cup is None and boot is None:
        return False, "no_participants", {}

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        # Idempotent: shu mavsum allaqachon yakunlanganmi?
        cursor.execute(
            "SELECT COUNT(*) AS n FROM season_prizes "
            "WHERE season_kind = ? AND season_number = ? "
            "AND prize_type IN (?, ?)",
            (DIV_SEASON_KIND, season_number, DIV_PRIZE_CUP, DIV_PRIZE_BOOT),
        )
        if cursor.fetchone()["n"] > 0:
            cursor.execute("ROLLBACK")
            return False, "already_finalized", {}

        saved = {}
        if cup is not None:
            _save_prize(cursor, DIV_PRIZE_CUP, cup["user_id"], season_number)
            saved["cup"] = cup
        if boot is not None:
            _save_prize(cursor, DIV_PRIZE_BOOT, boot["user_id"], season_number)
            saved["boot"] = boot

        cursor.execute("COMMIT")
        logger.info("Divizion %s-mavsum yakunlandi: kubok=%s butsa=%s",
                    season_number,
                    cup["user_id"] if cup else None,
                    boot["user_id"] if boot else None)
        return True, "ok", {"season_number": season_number, **saved}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        logger.exception("finalize_division_season xatosi")
        return False, "finalize_failed", {}
    finally:
        conn.close()


def _save_prize(cursor, prize_type: str, user_id: int, season_number: int) -> None:
    """season_prizes'ga bitta divizion sovrinini yozadi (user_id + telegram_id)."""
    cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    telegram_id = row["telegram_id"] if row else None
    cursor.execute(
        "INSERT INTO season_prizes "
        "(user_id, telegram_id, prize_type, season_number, season_kind) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, telegram_id, prize_type, season_number, DIV_SEASON_KIND),
    )
