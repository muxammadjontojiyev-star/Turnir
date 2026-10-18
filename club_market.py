"""
club_market.py — ligada KLUBNI TOPSHIRISH (2026-10-18).

Egasi so'rovi:
  * Liga ishtirokchisi profilida "Klubimni topshiraman" tugmachasini (switch) yoqadi —
    yoqishdan oldin klub tanlash navbati haqida ogohlantiriladi (club_priority.py).
  * Ligalar asosiy sahifasida topshirilayotgan klublar ro'yxati; klubsiz qolganlar (hech
    qaysi ligada ro'yxatda bo'lmaganlar) klubni o'ziga rasmiylashtiradi — o'rin, klub,
    jadval va natijalar yangi egaga o'tadi (participant_admin.league_reassign_participant).
  * Shu mavsumda klubini topshirganlar (club_reliability 'abandoned') boshqa klub ololmaydi.
Klub olinganda eski egasi "tashlab ketgan" hisoblanadi (keyingi mavsumda navbatning oxirida).
2026-10-18: kanalni TARK ETGAN liga ishtirokchisining klubi ham avtomatik ro'yxatga chiqadi
(source='left'; channel_leave_bot / scan_channel_leavers); kanalga qaytsa — o'zi olib tashlanadi.
Taklif faqat egasi hali shu ligada ro'yxatda bo'lsa amal qiladi (registrations bilan JOIN —
admin almashtirsa yoki o'chirsa taklif o'zi yo'qoladi). Mavsum reset'ida jadval tozalanadi.
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)


SRC_SELF, SRC_LEFT = "self", "left"     # o'zi topshirdi | kanalni tark etdi


def init_club_market_table(cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS club_offers (
            user_id INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cols = {r[1] for r in cursor.execute("PRAGMA table_info(club_offers)").fetchall()}
    if "source" not in cols:
        cursor.execute(f"ALTER TABLE club_offers ADD COLUMN source TEXT NOT NULL DEFAULT '{SRC_SELF}'")


def _my_registration(cur, user_id: int):
    return cur.execute("SELECT r.league_id, r.club_name, l.name AS league_name FROM registrations r "
                       "JOIN leagues l ON l.id = r.league_id WHERE r.user_id = ?", (user_id,)).fetchone()


def _gave_up_this_season(cur, telegram_id: int) -> bool:
    from club_priority import ST_ABANDONED, _current_season
    r = cur.execute("SELECT 1 FROM club_reliability WHERE telegram_id = ? AND season_number = ? AND status = ?",
                    (telegram_id, _current_season(cur), ST_ABANDONED)).fetchone()
    return r is not None


def club_offers_list(user: dict) -> dict:
    """Topshirilayotgan klublar + mening holatim {registered, offering, can_take, reason}."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT o.user_id, o.created_at, o.source, u.nickname, u.username, r.league_id, r.club_name, "
            "l.name AS league_name, "
            "(SELECT COUNT(*) FROM matches m WHERE (m.player1_id = o.user_id OR m.player2_id = o.user_id) "
            " AND m.status = 'confirmed') AS played "
            "FROM club_offers o JOIN registrations r ON r.user_id = o.user_id "
            "JOIN users u ON u.id = o.user_id JOIN leagues l ON l.id = r.league_id "
            "ORDER BY l.id, o.created_at")
        offers = [dict(r) for r in cur.fetchall()]
        reg = _my_registration(cur, user["id"])
        offering = any(o["user_id"] == user["id"] and o["source"] == SRC_SELF for o in offers)
        if reg:
            reason = "already_registered"
        elif _gave_up_this_season(cur, user["telegram_id"]):
            reason = "gave_up_club"
        else:
            reason = None
        return {"offers": offers, "me": {"registered": bool(reg), "offering": offering,
                                          "can_take": reason is None, "reason": reason,
                                          "league_name": reg["league_name"] if reg else None,
                                          "club_name": reg["club_name"] if reg else None}}
    finally:
        conn.close()


def club_offer_set(user_id: int, on: bool) -> tuple[bool, str | dict]:
    """Klubni topshirishga qo'yish / qaytarib olish. Sabab: not_registered."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if on:
            if not _my_registration(cur, user_id):
                return False, "not_registered"
            cur.execute("INSERT OR IGNORE INTO club_offers (user_id) VALUES (?)", (user_id,))
        else:
            cur.execute("DELETE FROM club_offers WHERE user_id = ?", (user_id,))
        conn.commit()
        logger.info("Klub bozori: user %s — taklif %s", user_id, "qo'yildi" if on else "olindi")
        return True, {"offering": bool(on)}
    finally:
        conn.close()


def club_offer_left(telegram_ids: list[int], left: bool = True) -> int:
    """
    Kanalni tark etgan liga ishtirokchilari klubini ro'yxatga qo'yadi (left=True) yoki kanalga
    qaytganda faqat 'left' manbali taklifni olib tashlaydi (left=False). Qaytaradi: o'zgargan qatorlar.
    """
    ids = [int(x) for x in telegram_ids or []]
    if not ids:
        return 0
    marks = ",".join("?" * len(ids))
    conn = get_connection()
    try:
        cur = conn.cursor()
        if left:
            cur.execute(f"INSERT OR IGNORE INTO club_offers (user_id, source) SELECT r.user_id, ? FROM registrations r "
                        f"JOIN users u ON u.id = r.user_id WHERE u.telegram_id IN ({marks})", (SRC_LEFT, *ids))
        else:
            cur.execute(f"DELETE FROM club_offers WHERE source = ? AND user_id IN "
                        f"(SELECT id FROM users WHERE telegram_id IN ({marks}))", (SRC_LEFT, *ids))
        n = cur.rowcount
        conn.commit()
        if n:
            logger.info("Klub bozori: kanal (%s) — %s ta klub %s", "chiqdi" if left else "qaytdi", n,
                        "ro'yxatga qo'yildi" if left else "ro'yxatdan olindi")
        return n
    finally:
        conn.close()


def club_offer_take(taker: dict, owner_user_id: int) -> tuple[bool, str | dict]:
    """
    Klubni o'ziga rasmiylashtirish. Sabablar: offer_not_found, already_registered, gave_up_club,
    priority_wait, own_offer, nothing_to_reassign (kimdir oldinroq oldi), new_already_participant.
    Qaytaradi: {league_name, club_name, owner_telegram_id, owner_language}.
    """
    if owner_user_id == taker["id"]:
        return False, "own_offer"
    from club_priority import club_priority_for
    conn = get_connection()
    try:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT r.club_name, l.name AS league_name, u.telegram_id, u.language FROM club_offers o "
            "JOIN registrations r ON r.user_id = o.user_id JOIN leagues l ON l.id = r.league_id "
            "JOIN users u ON u.id = o.user_id WHERE o.user_id = ?", (owner_user_id,)).fetchone()
        if not row:
            return False, "offer_not_found"
        if _my_registration(cur, taker["id"]):
            return False, "already_registered"
        if _gave_up_this_season(cur, taker["telegram_id"]):
            return False, "gave_up_club"
        info = dict(row)
    finally:
        conn.close()
    if not club_priority_for(taker["telegram_id"])["open"]:
        return False, "priority_wait"
    from participant_admin import league_reassign_participant
    ok, res = league_reassign_participant(owner_user_id, taker["telegram_id"], abandoned=True)
    if not ok:
        return False, res
    club_offer_set(owner_user_id, False)
    logger.info("Klub bozori: %s (%s) — user %s -> tg %s", info["club_name"], info["league_name"],
                owner_user_id, taker["telegram_id"])
    return True, {"league_name": info["league_name"], "club_name": info["club_name"],
                  "owner_telegram_id": info["telegram_id"], "owner_language": info["language"]}
