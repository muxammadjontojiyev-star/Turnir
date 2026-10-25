"""
tb_core.py — "TEAMLAR JANGI": teamlar va a'zolar mantig'i (2026-10-15, 1-bosqich).

Egasi qarorlari:
  - 2026-10-16: team LIGA ichida ochiladi (liga taklif havolasi, tb_leagues.py);
  - teamni istalgan foydalanuvchi ochadi (sardor), a'zolarni taklif havolasi bilan
    yig'adi (t.me/<bot>?start=tb_<kod>); bosh admin teamni tasdiqlaydi yoki rad etadi;
  - team hajmi cheklanmagan; ASOSIY TARKIBni sardor tuzadi (TB_LINEUP_MIN..TB_LINEUP_MAX);
  - bir kishi faqat bitta teamda.
Har o'zgartiruvchi amal BEGIN IMMEDIATE ichida (qoida #38); ruxsat — sardor/bosh admin (qoida #34).
Sabab kodlari frontend'da matnga aylanadi (tb.js TB_ERR).
"""

import logging
import re
import secrets

from models import get_connection
from tb_efb import tb_efb_has

logger = logging.getLogger(__name__)

TB_NAME_MIN = 3
TB_NAME_MAX = 24
TB_LINEUP_MIN = 6               # asosiy tarkib: kamida
TB_LINEUP_MAX = 20              # asosiy tarkib: ko'pi bilan
TB_INVITE_PREFIX = "tb_"        # /start parametri: tb_<invite_code>
TB_EMOJIS = ("⚔️", "🛡", "🔥", "⚡", "🦁", "🐺", "🦅", "🐉", "👑", "💎", "🚀", "🌪", "☠️", "🎯", "🏹", "🌙")
STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED = "pending", "approved", "rejected"
ROLE_CAPTAIN, ROLE_MEMBER = "captain", "member"

_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{4,40}$")
_NAME_RE = re.compile(r"^[\w .'’`\-]+$", re.UNICODE)
_INVITE_CODE_BYTES = 6


def parse_tb_invite_payload(payload: str | None) -> str | None:
    """'/start tb_<kod>' -> kod (noto'g'ri bo'lsa None)."""
    if not payload or not payload.startswith(TB_INVITE_PREFIX):
        return None
    code = payload[len(TB_INVITE_PREFIX):]
    return code if _CODE_RE.match(code) else None


def _clean_name(name: str) -> tuple[str | None, str]:
    n = " ".join(str(name or "").split())
    if len(n) < TB_NAME_MIN or len(n) > TB_NAME_MAX:
        return None, "bad_name_len"
    if not _NAME_RE.match(n):
        return None, "bad_name_chars"
    from profanity import contains_profanity
    if contains_profanity(n):
        return None, "bad_name_profanity"
    return n, "ok"


def _my_membership(cursor, user_id: int):
    cursor.execute("SELECT team_id, role FROM tb_members WHERE user_id = ?", (user_id,))
    return cursor.fetchone()


def _league_limits(cursor, team_id: int) -> tuple[int, int]:
    """2026-10-16: team ligasining asosiy tarkib chegaralari (liga yo'q bo'lsa — standart)."""
    cursor.execute("SELECT l.lineup_min, l.lineup_max FROM tb_teams t JOIN tb_leagues l ON l.id = t.league_id "
                   "WHERE t.id = ?", (team_id,))
    r = cursor.fetchone()
    return (r["lineup_min"], r["lineup_max"]) if r else (TB_LINEUP_MIN, TB_LINEUP_MAX)


def _begin(conn):
    conn.isolation_level = None
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    return cur


def _finish(cur, ok: bool):
    cur.execute("COMMIT" if ok else "ROLLBACK")


# ------------------------------------------------------------------ o'qish

def _team_row(cursor, team_id: int):
    cursor.execute(
        "SELECT t.id, t.name, t.emoji, t.logo_ver, t.status, t.reject_reason, t.captain_user_id, t.created_at, "
        "u.nickname AS captain_nickname, u.username AS captain_username, "
        "t.league_id, l.name AS league_name, l.emoji AS league_emoji, l.logo_ver AS league_logo_ver, "
        "(SELECT COUNT(*) FROM tb_members m WHERE m.team_id = t.id) AS members_count "
        "FROM tb_teams t JOIN users u ON u.id = t.captain_user_id "
        "LEFT JOIN tb_leagues l ON l.id = t.league_id WHERE t.id = ?",
        (team_id,),
    )
    r = cursor.fetchone()
    return dict(r) if r else None


def _members(cursor, team_id: int) -> list[dict]:
    cursor.execute(
        "SELECT m.user_id, m.role, m.in_lineup, m.lineup_pos, m.joined_at, "
        "u.telegram_id, u.nickname, u.username, e.efb_id, e.efb_name "
        "FROM tb_members m JOIN users u ON u.id = m.user_id "
        "LEFT JOIN tb_efb_accounts e ON e.user_id = m.user_id WHERE m.team_id = ? "
        "ORDER BY m.role = 'captain' DESC, m.in_lineup DESC, m.lineup_pos, u.nickname",
        (team_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def tb_team_detail(team_id: int, viewer_id: int, viewer_is_admin: bool = False) -> dict | None:
    """Team + a'zolar. Taklif kodi faqat sardor/bosh adminga; telegram_id faqat sardor/adminga."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        team = _team_row(cur, team_id)
        if not team:
            return None
        is_captain = team["captain_user_id"] == viewer_id
        members = _members(cur, team_id)
        if not (is_captain or viewer_is_admin):
            for m in members:
                m.pop("telegram_id", None)
                m.pop("efb_id", None)           # 2026-10-25: nik hammaga, ID — sardor/adminga
        team["members"] = members
        team["is_captain"] = is_captain
        team["is_member"] = any(m["user_id"] == viewer_id for m in members)
        team["lineup_count"] = sum(1 for m in members if m["in_lineup"])
        cur.execute("SELECT season_number, division FROM tb_titles WHERE team_id = ? ORDER BY season_id DESC",
                    (team_id,))
        team["titles"] = [dict(r) for r in cur.fetchall()]      # 2026-10-16 (3-bosqich)
        if is_captain or viewer_is_admin:
            cur.execute("SELECT invite_code FROM tb_teams WHERE id = ?", (team_id,))
            team["invite_code"] = cur.fetchone()["invite_code"]
        return team
    finally:
        conn.close()


def tb_my_team_id(user_id: int) -> int | None:
    conn = get_connection()
    try:
        r = _my_membership(conn.cursor(), user_id)
        return r["team_id"] if r else None
    finally:
        conn.close()


def tb_team_league_id(team_id: int | None) -> int | None:
    """2026-10-16: team qaysi ligada."""
    if not team_id:
        return None
    conn = get_connection()
    try:
        r = conn.cursor().execute("SELECT league_id FROM tb_teams WHERE id = ?", (team_id,)).fetchone()
        return r["league_id"] if r else None
    finally:
        conn.close()


def tb_list_teams(status: str | None = STATUS_APPROVED, league_id: int | None = None) -> list[dict]:
    """Liga teamlari (status=None — hammasi, admin uchun). 2026-10-16: league_id bo'yicha."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        sql = ("SELECT t.id, t.name, t.emoji, t.logo_ver, t.status, t.reject_reason, t.created_at, "
               "u.nickname AS captain_nickname, u.username AS captain_username, "
               "(SELECT COUNT(*) FROM tb_members m WHERE m.team_id = t.id) AS members_count, "
               "(SELECT COUNT(*) FROM tb_members m WHERE m.team_id = t.id AND m.in_lineup = 1) AS lineup_count, "
               "(SELECT COUNT(*) FROM tb_titles x WHERE x.team_id = t.id) AS titles_count "
               "FROM tb_teams t JOIN users u ON u.id = t.captain_user_id WHERE t.league_id = ? ")
        if status:
            cur.execute(sql + "AND t.status = ? ORDER BY members_count DESC, t.name", (league_id, status))
        else:
            cur.execute(sql + "ORDER BY t.status = 'pending' DESC, t.created_at DESC", (league_id,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def tb_invite_preview(code: str, user_id: int | None = None) -> dict | None:
    if not code or not _CODE_RE.match(code):
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM tb_teams WHERE invite_code = ?", (code,))
        r = cur.fetchone()
        if not r:
            return None
        team = _team_row(cur, r["id"])
        team.pop("captain_user_id", None)
        if user_id is not None:
            m = _my_membership(cur, user_id)
            team["my_team_id"] = m["team_id"] if m else None
        return team
    finally:
        conn.close()


# ------------------------------------------------------------------ yaratish / qo'shilish

def tb_create_team(user_id: int, name: str, emoji: str | None, league_code: str | None = None
                   ) -> tuple[bool, str | dict]:
    """
    Team faqat liga taklif havolasi orqali ochiladi (2026-10-16): league_code -> liga.
    Sabablar: league_not_found, bad_name_*, bad_emoji, already_in_team, efb_required, name_taken.
    """
    from tb_leagues import tb_league_by_code
    league = tb_league_by_code(league_code) if league_code else None
    if not league:
        return False, "league_not_found"
    clean, why = _clean_name(name)
    if not clean:
        return False, why
    if emoji and emoji not in TB_EMOJIS:
        return False, "bad_emoji"
    conn = get_connection()
    cur = _begin(conn)
    try:
        if _my_membership(cur, user_id):
            _finish(cur, False)
            return False, "already_in_team"
        if not tb_efb_has(cur, user_id):                # 2026-10-25: eFootball akkaunti majburiy
            _finish(cur, False)
            return False, "efb_required"
        cur.execute("SELECT 1 FROM tb_teams WHERE name = ? COLLATE NOCASE", (clean,))
        if cur.fetchone():
            _finish(cur, False)
            return False, "name_taken"
        code = secrets.token_urlsafe(_INVITE_CODE_BYTES)
        cur.execute(
            "INSERT INTO tb_teams (name, emoji, captain_user_id, invite_code, status, league_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (clean, emoji or TB_EMOJIS[0], user_id, code, STATUS_PENDING, league["id"]),
        )
        team_id = cur.lastrowid
        cur.execute("INSERT INTO tb_members (team_id, user_id, role) VALUES (?, ?, ?)",
                    (team_id, user_id, ROLE_CAPTAIN))
        _finish(cur, True)
        logger.info("TB: team yaratildi id=%s '%s' (sardor user=%s, liga=%s)", team_id, clean, user_id, league["id"])
        return True, {"team_id": team_id, "league_id": league["id"], "name": clean}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def tb_join(user_id: int, code: str) -> tuple[bool, str | dict]:
    """Taklif kodi bilan qo'shilish. Sabablar: not_found, rejected, already_in_team, efb_required."""
    if not code or not _CODE_RE.match(code):
        return False, "not_found"
    conn = get_connection()
    cur = _begin(conn)
    try:
        cur.execute("SELECT id, status FROM tb_teams WHERE invite_code = ?", (code,))
        t = cur.fetchone()
        if not t:
            _finish(cur, False)
            return False, "not_found"
        if t["status"] == STATUS_REJECTED:
            _finish(cur, False)
            return False, "rejected"
        m = _my_membership(cur, user_id)
        if m:
            _finish(cur, False)
            return False, "already_member" if m["team_id"] == t["id"] else "already_in_team"
        if not tb_efb_has(cur, user_id):                # 2026-10-25: eFootball akkaunti majburiy
            _finish(cur, False)
            return False, "efb_required"
        cur.execute("INSERT INTO tb_members (team_id, user_id, role) VALUES (?, ?, ?)",
                    (t["id"], user_id, ROLE_MEMBER))
        _finish(cur, True)
        return True, {"team_id": t["id"]}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()
