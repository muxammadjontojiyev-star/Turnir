"""
tb_leagues.py — "TEAMLAR JANGI": ligalar mantig'i (2026-10-16).

  Bosh admin: liga ochadi (nom, belgi, admin), adminni almashtiradi, bo'sh ligani o'chiradi.
  Liga admini: sozlamalar (nom, belgi, tarkib chegaralari, divizion hajmi), taklif havolasi.
  Ruxsat: tb_can_manage(user, league_id) — bosh admin yoki shu liga admini (qoida #34).
  Taklif: /start tbl_<kod> -> WebApp ?tbl_join=<kod> -> sardor shu ligada team ochadi.
Sabab kodlari frontend'da matnga aylanadi (tb.js TB_ERR).
"""

import logging
import re
import secrets

from admin_roles import is_super_admin
from models import get_connection
from tb_core import TB_EMOJIS, _begin, _clean_name, _finish
from tb_models_league import TB_LEAGUE_CODE_BYTES

logger = logging.getLogger(__name__)

TB_LEAGUE_PREFIX = "tbl_"           # /start parametri: tbl_<invite_code>
TB_LINEUP_FLOOR = 3                 # liga sozlamasi: asosiy tarkib kamida shuncha bo'lishi mumkin
TB_LINEUP_CEIL = 30                 # liga sozlamasi: asosiy tarkib ko'pi bilan
_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{4,40}$")
_LEAGUE_COLS = ("l.id, l.name, l.emoji, l.logo_ver, l.admin_user_id, l.lineup_min, l.lineup_max, l.division_size, "
                "l.created_at, u.nickname AS admin_nickname, u.username AS admin_username")


def parse_tb_league_payload(payload: str | None) -> str | None:
    if not payload or not payload.startswith(TB_LEAGUE_PREFIX):
        return None
    code = payload[len(TB_LEAGUE_PREFIX):]
    return code if _CODE_RE.match(code) else None


def _league_cur(cur, league_id: int) -> dict | None:
    cur.execute(f"SELECT {_LEAGUE_COLS} FROM tb_leagues l LEFT JOIN users u ON u.id = l.admin_user_id "
                "WHERE l.id = ?", (league_id,))
    r = cur.fetchone()
    return dict(r) if r else None


def tb_league(league_id: int | None, with_code: bool = False) -> dict | None:
    if not league_id:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        lg = _league_cur(cur, league_id)
        if lg and with_code:
            lg["invite_code"] = cur.execute("SELECT invite_code FROM tb_leagues WHERE id = ?",
                                            (league_id,)).fetchone()["invite_code"]
        return lg
    finally:
        conn.close()


def tb_league_by_code(code: str) -> dict | None:
    if not code or not _CODE_RE.match(code):
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        r = cur.execute("SELECT id FROM tb_leagues WHERE invite_code = ?", (code,)).fetchone()
        return _league_cur(cur, r["id"]) if r else None
    finally:
        conn.close()


def tb_leagues_list(admin_user_id: int | None = None) -> list[dict]:
    """Ligalar (+ teamlar soni, kutilayotgan arizalar). admin_user_id berilsa — faqat uning ligalari."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        sql = (f"SELECT {_LEAGUE_COLS}, "
               "(SELECT COUNT(*) FROM tb_teams t WHERE t.league_id = l.id AND t.status = 'approved') AS teams, "
               "(SELECT COUNT(*) FROM tb_teams t WHERE t.league_id = l.id AND t.status = 'pending') AS pending "
               "FROM tb_leagues l LEFT JOIN users u ON u.id = l.admin_user_id ")
        if admin_user_id is None:
            cur.execute(sql + "ORDER BY l.id")
        else:
            cur.execute(sql + "WHERE l.admin_user_id = ? ORDER BY l.id", (admin_user_id,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def tb_can_manage(user: dict, league_id: int | None) -> bool:
    if not league_id:
        return False
    if is_super_admin(user["telegram_id"]):
        return True
    lg = tb_league(league_id)
    return bool(lg and lg["admin_user_id"] == user["id"])


def tb_managed_leagues(user: dict) -> list[dict]:
    """Foydalanuvchi boshqaradigan ligalar (bosh admin — hammasi)."""
    return tb_leagues_list(None if is_super_admin(user["telegram_id"]) else user["id"])


def find_user(who: str | None) -> int | None:
    """'@username', 'username' yoki Telegram ID -> users.id."""
    w = str(who or "").strip()
    if not w:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        if w.lstrip("-").isdigit():
            r = cur.execute("SELECT id FROM users WHERE telegram_id = ?", (int(w),)).fetchone()
        else:
            r = cur.execute("SELECT id FROM users WHERE username = ? COLLATE NOCASE", (w.lstrip("@"),)).fetchone()
        return r["id"] if r else None
    finally:
        conn.close()


# ------------------------------------------------------------------ bosh admin

def tb_league_create(name: str, emoji: str | None, admin_who: str | None) -> tuple[bool, str | dict]:
    """Sabablar: bad_name_*, bad_emoji, admin_not_found, league_name_taken."""
    clean, why = _clean_name(name)
    if not clean:
        return False, why
    if emoji and emoji not in TB_EMOJIS:
        return False, "bad_emoji"
    admin_id = None
    if admin_who and str(admin_who).strip():
        admin_id = find_user(admin_who)
        if not admin_id:
            return False, "admin_not_found"
    conn = get_connection()
    cur = _begin(conn)
    try:
        if cur.execute("SELECT 1 FROM tb_leagues WHERE name = ? COLLATE NOCASE", (clean,)).fetchone():
            _finish(cur, False)
            return False, "league_name_taken"
        cur.execute("INSERT INTO tb_leagues (name, emoji, admin_user_id, invite_code) VALUES (?, ?, ?, ?)",
                    (clean, emoji or TB_EMOJIS[0], admin_id, secrets.token_urlsafe(TB_LEAGUE_CODE_BYTES)))
        lid = cur.lastrowid
        _finish(cur, True)
        logger.info("TB: liga ochildi id=%s '%s' (admin user=%s)", lid, clean, admin_id)
        return True, {"league_id": lid, "admin_user_id": admin_id}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def tb_league_set_admin(league_id: int, admin_who: str | None) -> tuple[bool, str | dict]:
    """Bo'sh admin_who — adminni olib tashlash. Sabablar: league_not_found, admin_not_found."""
    admin_id = None
    if admin_who and str(admin_who).strip():
        admin_id = find_user(admin_who)
        if not admin_id:
            return False, "admin_not_found"
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE tb_leagues SET admin_user_id = ? WHERE id = ?", (admin_id, league_id))
        conn.commit()
        if cur.rowcount == 0:
            return False, "league_not_found"
        return True, {"league_id": league_id, "admin_user_id": admin_id}
    finally:
        conn.close()


def tb_league_delete(league_id: int) -> tuple[bool, str | dict]:
    """Faqat bo'sh liga (teamsiz, mavsumsiz). Sabablar: league_not_found, league_not_empty."""
    conn = get_connection()
    cur = _begin(conn)
    try:
        if not cur.execute("SELECT 1 FROM tb_leagues WHERE id = ?", (league_id,)).fetchone():
            _finish(cur, False)
            return False, "league_not_found"
        busy = cur.execute("SELECT (SELECT COUNT(*) FROM tb_teams WHERE league_id = ?) + "
                           "(SELECT COUNT(*) FROM tb_seasons WHERE league_id = ?) AS n",
                           (league_id, league_id)).fetchone()["n"]
        if busy:
            _finish(cur, False)
            return False, "league_not_empty"
        from tb_logos import delete_logo_cur
        delete_logo_cur(cur, "league", league_id)
        cur.execute("DELETE FROM tb_leagues WHERE id = ?", (league_id,))
        _finish(cur, True)
        return True, {"league_id": league_id}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


# ------------------------------------------------------------------ liga admini

def _int_in(v, lo: int, hi: int) -> int | None:
    try:
        x = int(v)
    except (TypeError, ValueError):
        return None
    return x if lo <= x <= hi else None


def tb_league_update(league_id: int, data: dict) -> tuple[bool, str | dict]:
    """
    Sozlamalar: name, emoji, lineup_min, lineup_max, division_size (berilganlari o'zgaradi).
    Sabablar: league_not_found, bad_name_*, bad_emoji, league_name_taken, bad_lineup_limits, bad_division_size.
    """
    from tb_season import TB_DIV_SIZE_MAX, TB_DIV_SIZE_MIN
    lg = tb_league(league_id)
    if not lg:
        return False, "league_not_found"
    upd = {}
    if data.get("name") is not None:
        clean, why = _clean_name(data["name"])
        if not clean:
            return False, why
        upd["name"] = clean
    if data.get("emoji") is not None:
        if data["emoji"] not in TB_EMOJIS:
            return False, "bad_emoji"
        upd["emoji"] = data["emoji"]
    lmin = lg["lineup_min"] if data.get("lineup_min") is None else _int_in(data["lineup_min"], TB_LINEUP_FLOOR, TB_LINEUP_CEIL)
    lmax = lg["lineup_max"] if data.get("lineup_max") is None else _int_in(data["lineup_max"], TB_LINEUP_FLOOR, TB_LINEUP_CEIL)
    if lmin is None or lmax is None or lmin > lmax:
        return False, "bad_lineup_limits"
    upd["lineup_min"], upd["lineup_max"] = lmin, lmax
    if data.get("division_size") is not None:
        ds = _int_in(data["division_size"], TB_DIV_SIZE_MIN, TB_DIV_SIZE_MAX)
        if ds is None:
            return False, "bad_division_size"
        upd["division_size"] = ds
    conn = get_connection()
    cur = _begin(conn)
    try:
        if "name" in upd and cur.execute("SELECT 1 FROM tb_leagues WHERE name = ? COLLATE NOCASE AND id != ?",
                                         (upd["name"], league_id)).fetchone():
            _finish(cur, False)
            return False, "league_name_taken"
        sets = ", ".join(f"{k} = ?" for k in upd)          # kalitlar yuqorida qat'iy belgilangan
        cur.execute(f"UPDATE tb_leagues SET {sets} WHERE id = ?", (*upd.values(), league_id))
        _finish(cur, True)
        return True, {"league_id": league_id}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def tb_league_regen_code(league_id: int) -> tuple[bool, str | dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        code = secrets.token_urlsafe(TB_LEAGUE_CODE_BYTES)
        cur.execute("UPDATE tb_leagues SET invite_code = ? WHERE id = ?", (code, league_id))
        conn.commit()
        return (True, {"invite_code": code}) if cur.rowcount else (False, "league_not_found")
    finally:
        conn.close()


def tb_league_admin_contact(league_id: int) -> dict | None:
    """Liga admini (yangi team arizasi haqida xabar uchun): {telegram_id, language} yoki None."""
    conn = get_connection()
    try:
        r = conn.cursor().execute(
            "SELECT u.telegram_id, u.language FROM tb_leagues l JOIN users u ON u.id = l.admin_user_id "
            "WHERE l.id = ?", (league_id,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()
