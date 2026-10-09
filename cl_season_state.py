"""
cl_season_state.py — ChL'ning LIGADAN MUSTAQIL faol mavsum ko'rsatkichi (2026-10-09).

Muammo: ChL jadvallari (cl_participants/cl_matches/cl_playoff_matches/cl_state...)
`season` ustuni bilan saqlanadi va ilgari season_state.current_season (LIGA
mavsumi) bo'yicha o'qilardi. Liga yangi mavsumga o'tsa, ChL o'zi ham "yangi"
(bo'sh) mavsumga sakrab ketardi — tugamagan ChL ko'rinmay qolardi.

Yechim — season_state'da ikki ustun:
  cl_active_season — ChL jadvallaridagi faol `season` kaliti (o'yinlar shu raqamda);
  cl_from_season   — faol ChL qaysi cl_qualifiers.from_season kvalifikantlaridan tuzilgan.
Ikkalasi FAQAT cl_start_new_season() (bosh admin tugmasi) bilan o'zgaradi.
Liga yakunlanishi ularga TEGMAYDI.

Barcha ChL modullari mavsumni cl_data_season() / cl_qualifier_season() dan oladi
(qoida #26 — bitta manba).
"""

import logging
import sqlite3

from models import get_connection

logger = logging.getLogger(__name__)

# ChL ma'lumoti saqlanadigan jadvallar — "oldingi ChL tugaganmi?" tekshiruvi uchun
_CL_DATA_TABLES = ("cl_participants", "cl_matches", "cl_playoff_matches")


def cl_data_season(cursor) -> int:
    """Faol ChL'ning `season` kaliti. Ko'rsatkich hali yo'q bo'lsa — liga mavsumi (eski xulq)."""
    cursor.execute("SELECT current_season, cl_active_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    if row is None:
        return 1
    return row["cl_active_season"] if row["cl_active_season"] is not None else row["current_season"]


def get_cl_data_season() -> int:
    """cl_data_season — o'z ulanishi bilan (API endpointlari uchun)."""
    conn = get_connection()
    try:
        return cl_data_season(conn.cursor())
    finally:
        conn.close()


def cl_qualifier_season(cursor) -> int | None:
    """Faol ChL kvalifikantlarining from_season'i (None — faol ChL uchun kvalifikant yo'q)."""
    cursor.execute("SELECT cl_from_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["cl_from_season"] if row else None


def _latest_qualifier_season(cursor) -> int | None:
    cursor.execute("SELECT MAX(from_season) AS s FROM cl_qualifiers")
    row = cursor.fetchone()
    return row["s"] if row and row["s"] else None


def _cl_has_data(cursor) -> bool:
    """Oldingi ChL ma'lumoti hali tozalanmaganmi (ya'ni ChL yakunlanmagan)."""
    for tbl in _CL_DATA_TABLES:
        cursor.execute(f"SELECT 1 FROM {tbl} LIMIT 1")  # nom — modul konstantasi, user kiritmasi emas
        if cursor.fetchone() is not None:
            return True
    return False


def cl_season_info() -> dict:
    """Admin paneli uchun holat: faol ChL, liga mavsumi, keyingi kvalifikantlar, boshlash mumkinmi."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        active = cl_data_season(cursor)
        from_s = cl_qualifier_season(cursor)
        latest = _latest_qualifier_season(cursor)
        cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
        row = cursor.fetchone()
        league = row["current_season"] if row else 1
        busy = _cl_has_data(cursor)
        reason = _start_block_reason(busy, latest, from_s)
        return {"active_season": active, "from_season": from_s, "league_season": league,
                "next_from_season": latest, "cl_running": busy,
                "can_start": reason is None, "reason": reason}
    finally:
        conn.close()


def _start_block_reason(busy: bool, latest: int | None, from_s: int | None) -> str | None:
    if busy:
        return "cl_not_finished"        # avval "ChL mavsumini yakunlash"
    if latest is None:
        return "no_qualifiers"          # liga mavsumi hali yakunlanmagan
    if from_s is not None and latest <= from_s:
        return "already_started"        # bu kvalifikantlar bilan ChL allaqachon boshlangan
    return None


def cl_start_new_season() -> tuple[bool, str | dict]:
    """
    Bosh admin: yangi ChL mavsumini boshlaydi — ko'rsatkichni joriy liga mavsumiga
    va eng oxirgi kvalifikantlarga o'tkazadi. Qur'a keyin alohida o'tkaziladi.
    Idempotent: BEGIN IMMEDIATE + already_started tekshiruvi (qoida #38).
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        latest = _latest_qualifier_season(cursor)
        reason = _start_block_reason(_cl_has_data(cursor), latest, cl_qualifier_season(cursor))
        if reason:
            cursor.execute("ROLLBACK")
            return False, reason
        cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
        league = cursor.fetchone()["current_season"]
        cursor.execute(
            "UPDATE season_state SET cl_active_season = ?, cl_from_season = ? WHERE id = 1",
            (league, latest),
        )
        cursor.execute("COMMIT")
        logger.info("ChL yangi mavsumi boshlandi: active_season=%s, from_season=%s", league, latest)
        return True, {"active_season": league, "from_season": latest}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except sqlite3.Error:
            logger.exception("cl_start_new_season: ROLLBACK xatosi")
        logger.exception("cl_start_new_season xatosi")
        raise
    finally:
        conn.close()


def migrate_cl_season_pointer(conn) -> None:
    """
    Bir martalik (idempotent) migratsiya: ustunlarni qo'shadi va ko'rsatkichni
    HOZIRGI holatga bog'laydi — cl_active_season = current_season (ChL hozir shu
    kalitda), cl_from_season = MAX(from_season) (hozirgi ChL kvalifikantlari).
    MUHIM: liga mavsumi yakunlanishidan OLDIN deploy qilinishi shart.
    Guard: cl_active_season IS NULL bo'lsagina ishlaydi.
    """
    cursor = conn.cursor()
    for col in ("cl_active_season", "cl_from_season"):
        try:
            cursor.execute(f"ALTER TABLE season_state ADD COLUMN {col} INTEGER")
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                logger.error("ChL ko'rsatkich ustuni xatosi (%s): %s", col, exc)
                raise
    cursor.execute("BEGIN IMMEDIATE")
    cursor.execute("SELECT current_season, cl_active_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    if row is None or row["cl_active_season"] is not None:
        cursor.execute("ROLLBACK")
        return
    latest = _latest_qualifier_season(cursor)
    cursor.execute(
        "UPDATE season_state SET cl_active_season = ?, cl_from_season = ? WHERE id = 1",
        (row["current_season"], latest),
    )
    cursor.execute("COMMIT")
    logger.info("ChL ko'rsatkichi o'rnatildi: active_season=%s, from_season=%s",
                row["current_season"], latest)
