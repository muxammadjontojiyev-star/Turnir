"""
tb_public.py — "TEAMLAR JANGI": TEAMI YO'QLAR UCHUN KO'RINADIGAN LIGALAR (2026-11-07, egasi: «Bosh admin o'zi hohlagan
liga teamlarini teamga qo'shilish istagida bo'lib teamlar jangi bo'limiga kirganlar uchun ko'rinadigan qilaolsin,
shu bilan birga teami yo'q bo'lganlar team sardorlarining telegram chatiga yozish imkoni ham bo'lsin»).

  * tb_leagues.public_teams (0/1) — bosh admin liga sozlamasida yoqadi (POST /tb/admin/league/public).
  * public_teams() — yoqilgan ligalarning TASDIQLANGAN teamlari: nomi, logosi, a'zolar soni, sardor (Telegram
    username / ID — «✈️ Sardorga yozish» tugmasi uchun). Faqat teami yo'q foydalanuvchiga beriladi (tb_api_public.py).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)

PUBLIC_TEAMS_MAX = 200          # bir javobdagi teamlar chegarasi


def migrate_public(cur) -> None:
    cols = {r[1] for r in cur.execute("PRAGMA table_info(tb_leagues)").fetchall()}
    if "public_teams" not in cols:
        cur.execute("ALTER TABLE tb_leagues ADD COLUMN public_teams INTEGER NOT NULL DEFAULT 0")


def set_public(league_id: int, on: bool) -> tuple[bool, str | dict]:
    conn = get_connection()
    try:
        migrate_public(conn.cursor())
        cur = conn.execute("UPDATE tb_leagues SET public_teams = ? WHERE id = ?", (1 if on else 0, league_id))
        conn.commit()
        if not cur.rowcount:
            return False, "league_not_found"
    finally:
        conn.close()
    logger.info("TB: liga #%s teamlari teamsizlarga %s", league_id, "KO'RINADI" if on else "yashirildi")
    return True, {"league_id": league_id, "public": bool(on)}


def public_teams() -> list[dict]:
    """[{league: {id, name, emoji, logo_ver}, teams: [{id, name, emoji, logo_ver, members_count, lineup_max,
    captain_username, captain_nickname, captain_tg}]}] — faqat ochiq ligalar, tasdiqlangan teamlar."""
    conn = get_connection()
    try:
        migrate_public(conn.cursor())
        rows = conn.execute(
            "SELECT t.id, t.name, t.emoji, t.logo_ver, l.id AS league_id, l.name AS league_name, l.emoji AS league_emoji, "
            "l.logo_ver AS league_logo_ver, l.lineup_max, u.username AS captain_username, u.nickname AS captain_nickname, "
            "u.telegram_id AS captain_tg, (SELECT COUNT(*) FROM tb_members m WHERE m.team_id = t.id) AS members_count "
            "FROM tb_teams t JOIN tb_leagues l ON l.id = t.league_id JOIN users u ON u.id = t.captain_user_id "
            "WHERE l.public_teams = 1 AND t.status = 'approved' ORDER BY l.name, t.name LIMIT ?",
            (PUBLIC_TEAMS_MAX,)).fetchall()
    finally:
        conn.close()
    out: dict[int, dict] = {}
    for r in rows:
        g = out.setdefault(r["league_id"], {"league": {"id": r["league_id"], "name": r["league_name"],
                                                       "emoji": r["league_emoji"], "logo_ver": r["league_logo_ver"]},
                                            "teams": []})
        g["teams"].append({k: r[k] for k in ("id", "name", "emoji", "logo_ver", "members_count", "lineup_max",
                                             "captain_username", "captain_nickname", "captain_tg")})
    return list(out.values())
