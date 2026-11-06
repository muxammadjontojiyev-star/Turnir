"""
ef_nick.py — ishtirokchining eFOOTBALL NIKNAMEI (2026-11-06, egasi so'rovi).

Match History skrinshotidagi o'yinni aynan shu ikki ishtirokchiniki ekanini tekshirish uchun
(match_shot.py). Qoidalar (egasi):
  * Bir nikname — bitta ishtirokchiga (katta-kichik harf va bo'sh joysiz solishtiriladi).
  * Birinchi kiritish — bepul. Keyin har MAVSUMDA (liga mavsumi, season_state) NICK_FREE_CHANGES marta
    bepul almashtirish; qo'shimchasi — NICK_PAID_PRICE eF Token (wallet_change, kind "ef_nick").
Jadval — ef_nicknames (migratsiya, qoida #31).
"""

import logging
import re
import unicodedata

from models import get_connection

logger = logging.getLogger(__name__)

NICK_MIN, NICK_MAX = 2, 24
NICK_FREE_CHANGES = 2            # mavsumiga bepul almashtirish
NICK_PAID_PRICE = 5              # qo'shimcha almashtirish narxi (eF Token)
WALLET_KIND = "ef_nick"
_BAD_CHARS = re.compile(r"[\x00-\x1f\x7f<>]")


def migrate_ef_nick(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS ef_nicknames (user_id INTEGER PRIMARY KEY, nick TEXT NOT NULL, "
                "nick_norm TEXT NOT NULL UNIQUE, season INTEGER, changes INTEGER NOT NULL DEFAULT 0, "
                "updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")


def norm_nick(s: str) -> str:
    """Solishtirish uchun: NFKC, kichik harf, bo'sh joysiz."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s or "")).casefold()


def _season(cur) -> int:
    try:
        r = cur.execute("SELECT current_season FROM season_state WHERE id = 1").fetchone()
        return r["current_season"] if r else 1
    except Exception:
        return 1


def get_nick_info(user_id: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        r = cur.execute("SELECT nick, season, changes FROM ef_nicknames WHERE user_id = ?", (user_id,)).fetchone()
        season = _season(cur)
    finally:
        conn.close()
    used = (r["changes"] if r and r["season"] == season else 0)
    return {"nick": r["nick"] if r else None, "free_left": max(0, NICK_FREE_CHANGES - used),
            "price": NICK_PAID_PRICE, "free_per_season": NICK_FREE_CHANGES}


def nicks_for_users(user_ids) -> dict[int, str]:
    ids = [int(u) for u in user_ids if u]
    if not ids:
        return {}
    conn = get_connection()
    try:
        q = ",".join("?" * len(ids))
        return {r["user_id"]: r["nick"] for r in conn.execute(
            f"SELECT user_id, nick FROM ef_nicknames WHERE user_id IN ({q})", ids)}
    finally:
        conn.close()


def set_nick(user_id: int, nick: str, pay: bool = False) -> tuple[bool, str | dict]:
    """Xato: bad_nick, same_nick, nick_taken, need_pay (bepul tugagan — pay=True bilan qayta), insufficient."""
    nick = unicodedata.normalize("NFKC", (nick or "").strip())
    if not (NICK_MIN <= len(nick) <= NICK_MAX) or _BAD_CHARS.search(nick):
        return False, "bad_nick"
    nn = norm_nick(nick)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        season = _season(cur)
        r = cur.execute("SELECT nick, nick_norm, season, changes FROM ef_nicknames WHERE user_id = ?", (user_id,)).fetchone()
        if r and r["nick_norm"] == nn and r["nick"] == nick:
            conn.rollback()
            return False, "same_nick"
        other = cur.execute("SELECT user_id FROM ef_nicknames WHERE nick_norm = ? AND user_id != ?", (nn, user_id)).fetchone()
        if other:
            conn.rollback()
            return False, "nick_taken"
        paid = False
        if r is None:
            cur.execute("INSERT INTO ef_nicknames (user_id, nick, nick_norm, season, changes) VALUES (?, ?, ?, ?, 0)",
                        (user_id, nick, nn, season))
        else:
            used = r["changes"] if r["season"] == season else 0
            if used >= NICK_FREE_CHANGES:
                if not pay:
                    conn.rollback()
                    return False, "need_pay"
                from wallet import wallet_change
                try:
                    wallet_change(cur, user_id, -NICK_PAID_PRICE, WALLET_KIND)
                except ValueError:
                    conn.rollback()
                    return False, "insufficient"
                paid = True
            cur.execute("UPDATE ef_nicknames SET nick = ?, nick_norm = ?, season = ?, changes = ?, "
                        "updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (nick, nn, season, used + 1, user_id))
        conn.commit()
    finally:
        conn.close()
    logger.info("eF NIKNAME: user %s → %r%s", user_id, nick, " (pullik)" if paid else "")
    return True, get_nick_info(user_id)
