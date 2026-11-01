"""
promotion_admin.py — KO'TARILGANLARNI ADMIN QO'SHADI (2026-11-01).

Egasi so'rovi: ko'tarilganlar qachon kirib ro'yxatdan o'tishini kutib bo'lmaydi — liga to'lmagani uchun
qur'a tashlab bo'lmayapti. Bosh admin bitta tugma bilan hali ro'yxatdan o'tmagan HAMMA ko'tarilganni
o'z 1-ligasiga, shu ligadagi BO'SH klublardan TASODIFIY biri bilan yozadi; har biriga bot xabari.

O'tkazib yuboriladi (sabab bilan): akkaunt yo'q, liga qur'asi allaqachon o'tgan, bo'sh klub / joy yo'q.
Hammasi bitta BEGIN IMMEDIATE ichida (qoida #38) — ikki marta bosilsa ham bir kishi ikki marta yozilmaydi
(registrations.user_id UNIQUE, faqat faol band joylar olinadi).
"""

import logging
import secrets

from config import LEAGUE_STATUS_OPEN
from promotion import _ACTIVE

logger = logging.getLogger(__name__)


def promotion_register_all() -> dict:
    """{"added": [{telegram_id, language, league, club}], "skipped": [{telegram_id, league, reason}]}."""
    from pt_formats import LEAGUE_CLUBS
    from shop_core import _tx

    def run(cur):
        rows = cur.execute(f"SELECT p.id, p.telegram_id, p.to_league_id, lg.name AS league, lg.max_players, lg.status "
                           f"FROM league_promotions p JOIN leagues lg ON lg.id = p.to_league_id "
                           f"WHERE {_ACTIVE} ORDER BY p.to_league_id, p.position").fetchall()
        added, skipped = [], []
        for p in rows:
            user = cur.execute("SELECT id, language FROM users WHERE telegram_id = ? ORDER BY id DESC LIMIT 1",
                               (p["telegram_id"],)).fetchone()
            reason = None
            if not user:
                reason = "no_account"
            elif p["status"] != LEAGUE_STATUS_OPEN:
                reason = "league_started"
            else:
                taken = {r["club_name"] for r in cur.execute(
                    "SELECT club_name FROM registrations WHERE league_id = ?", (p["to_league_id"],))}
                free = [c for c in LEAGUE_CLUBS.get(p["league"], ()) if c not in taken]
                cnt = cur.execute("SELECT COUNT(*) AS n FROM registrations WHERE league_id = ?",
                                  (p["to_league_id"],)).fetchone()["n"]
                if not free or cnt >= p["max_players"]:
                    reason = "league_full"
                else:
                    club = secrets.choice(free)
                    cur.execute("INSERT INTO registrations (user_id, league_id, club_name) VALUES (?, ?, ?)",
                                (user["id"], p["to_league_id"], club))
                    added.append({"telegram_id": p["telegram_id"], "language": user["language"],
                                  "league": p["league"], "club": club})
            if reason:
                skipped.append({"telegram_id": p["telegram_id"], "league": p["league"], "reason": reason})
        return True, {"added": added, "skipped": skipped}

    res = _tx(run)[1]
    logger.info("KO'TARILISH (admin): %s kishi qo'shildi, %s o'tkazib yuborildi %s",
                len(res["added"]), len(res["skipped"]), res["skipped"])
    return res
