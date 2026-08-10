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

DIV_PRIZE_CUP = "div_cup"     # mavsum 1-o'rni (yulduzcha ham beradi)
DIV_PRIZE_BOOT = "div_boot"   # to'purarlar 1-o'rni
# 2026-08: mavsum reytingi 1/2/3-o'rin medalyonlari (profilda ko'rinadi,
# yulduzcha BERMAYDI — faqat kubok beradi).
DIV_MEDALS = {1: "div_medal_1", 2: "div_medal_2", 3: "div_medal_3"}
DIV_SEASON_KIND = "division"


def get_division_season_number() -> int:
    """Joriy divizion mavsum raqami (sana-asosli, division_season)."""
    from division_season import div_current_season
    return div_current_season()["number"]


def _season_context(season: str | None) -> tuple[str | None, int]:
    """
    'season' tanlovini so'rov sanasi + mavsum raqamiga aylantiradi (qoida #26 DRY).
      season='prev' -> O'TGAN mavsum (query_day, number)
      aks holda     -> JORIY mavsum (None, number)
    O'tgan mavsum yo'q bo'lsa (1-mavsum) — joriy qaytadi.
    """
    from division_season import div_prev_season, div_current_season
    if season == "prev":
        prev = div_prev_season()
        if prev is not None:
            return prev["query_day"], prev["number"]
    return None, div_current_season()["number"]


def preview_division_prizes(season: str | None = None) -> dict:
    """
    Yakunlashda kim qaysi sovrinni olishini KO'RSATADI (saqlamaydi).
    Admin tasdiqlashdan oldin ko'radi.

    season='prev' -> O'TGAN mavsum sovrindorlari (masalan 2-mavsum boshlangach
    1-mavsumni yakunlash uchun). Aks holda joriy mavsum.

    Qaytaradi: {
      "season_number": int,
      "cup":  {user_id, nickname, username, points} | None,   # 1-o'rin (kubok + ★)
      "boot": {user_id, nickname, username, goals_for} | None, # to'purar 1-o'rin
      "medals": [{place, user_id, nickname, username, points}, ...]  # 1..3 o'rin
      "already_finalized": bool   # shu mavsum allaqachon yakunlanganmi
    }
    """
    from division import div_rating, div_scorers
    day, season_number = _season_context(season)
    rating = div_rating(day)
    scorers = div_scorers(day)

    played = [p for p in rating if p.get("played", 0) > 0]

    cup = None
    if played:
        w = played[0]
        cup = {"user_id": w["user_id"], "nickname": w.get("nickname"),
               "username": w.get("username"), "points": w.get("points", 0)}

    boot = None
    if scorers and scorers[0].get("goals_for", 0) > 0:
        s = scorers[0]
        boot = {"user_id": s["user_id"], "nickname": s.get("nickname"),
                "username": s.get("username"), "goals_for": s.get("goals_for", 0)}

    # 1/2/3-o'rin medalyonlari (reytingda o'yin o'ynaganlardan)
    medals = []
    for place in (1, 2, 3):
        if len(played) >= place:
            p = played[place - 1]
            medals.append({"place": place, "user_id": p["user_id"],
                           "nickname": p.get("nickname"),
                           "username": p.get("username"),
                           "points": p.get("points", 0)})

    return {
        "season_number": season_number,
        "cup": cup,
        "boot": boot,
        "medals": medals,
        "already_finalized": _is_finalized(season_number),
    }


def _is_finalized(season_number: int) -> bool:
    """Shu divizion mavsumi allaqachon yakunlanganmi (sovrin yozilganmi)."""
    all_types = (DIV_PRIZE_CUP, DIV_PRIZE_BOOT, *DIV_MEDALS.values())
    ph = ",".join("?" * len(all_types))
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"SELECT COUNT(*) AS n FROM season_prizes "
            f"WHERE season_kind = ? AND season_number = ? AND prize_type IN ({ph})",
            (DIV_SEASON_KIND, season_number, *all_types),
        )
        return cursor.fetchone()["n"] > 0
    finally:
        conn.close()


def finalize_division_season(season: str | None = None) -> tuple[bool, str, dict]:
    """
    Divizion mavsumini yakunlaydi: 1-o'rin (kubok + ★), to'purar 1-o'rin (butsa)
    va 1/2/3-o'rin medalyonlarini season_prizes'ga saqlaydi. Idempotent.

    season='prev' -> O'TGAN mavsum yakunlanadi (masalan 2-mavsum boshlangach
    1-mavsum sovrinlarini berish uchun). Aks holda joriy mavsum.

    Qaytaradi: (ok, reason, info)
      reason: ok | no_participants | already_finalized
      info: {season_number, cup, boot, medals} (saqlanganlar)
    """
    prizes = preview_division_prizes(season)
    season_number = prizes["season_number"]
    cup, boot, medals = prizes["cup"], prizes["boot"], prizes["medals"]

    if cup is None and boot is None and not medals:
        return False, "no_participants", {}

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        # Idempotent: shu mavsum allaqachon yakunlanganmi?
        all_types = (DIV_PRIZE_CUP, DIV_PRIZE_BOOT, *DIV_MEDALS.values())
        ph = ",".join("?" * len(all_types))
        cursor.execute(
            f"SELECT COUNT(*) AS n FROM season_prizes "
            f"WHERE season_kind = ? AND season_number = ? AND prize_type IN ({ph})",
            (DIV_SEASON_KIND, season_number, *all_types),
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
        for m in medals:
            _save_prize(cursor, DIV_MEDALS[m["place"]], m["user_id"], season_number)
        if medals:
            saved["medals"] = medals

        cursor.execute("COMMIT")
        logger.info("Divizion %s-mavsum yakunlandi: kubok=%s butsa=%s medal=%s",
                    season_number,
                    cup["user_id"] if cup else None,
                    boot["user_id"] if boot else None,
                    [m["user_id"] for m in medals])
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
