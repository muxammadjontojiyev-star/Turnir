"""
pt_teams.py — SHAXSIY turnirda klub / terma jamoa tanlash (2026-10-07).

Admin qarori: liga formatida — tanlangan ligadagi klublardan, ChL/YeL — 5 ligadagi barcha
klublardan, JCh — rasmiy JCh'dagi 48 terma jamoadan; bitta jamoa — bitta ishtirokchi.
Tanlash/almashtirish faqat qur'agacha (recruiting); a'zo (approved yoki pending) o'zi tanlaydi.
Band qilish poyga holatidan UNIQUE indeks bilan himoyalangan (idx_pt_members_team).
"""

import logging
import sqlite3

from models import get_connection
from pt_formats import teams_for, uses_teams

logger = logging.getLogger(__name__)


def check_team(fmt: str, league: str | None, team) -> str | None:
    """Jamoa shu formatga tegishlimi. None — to'g'ri, aks holda sabab (bad_team / no_teams)."""
    if not uses_teams(fmt):
        return "no_teams"
    return None if isinstance(team, str) and team in teams_for(fmt, league) else "bad_team"


def team_taken(cursor, tid: int, team: str, user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM pt_members WHERE tournament_id = ? AND team_name = ? AND user_id != ?",
                   (tid, team, user_id))
    return cursor.fetchone() is not None


def pt_set_team(tid: int, user_id: int, team) -> tuple[bool, str]:
    """
    A'zo o'z jamoasini tanlaydi/almashtiradi (faqat recruiting).
    Sabablar: not_found, not_member, not_recruiting, no_teams, bad_team, team_taken.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT status, format, league_name FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        why = None
        if not t:
            why = "not_found"
        else:
            cursor.execute("SELECT 1 FROM pt_members WHERE tournament_id = ? AND user_id = ?", (tid, user_id))
            if not cursor.fetchone():
                why = "not_member"
            elif t["status"] != "recruiting":
                why = "not_recruiting"
            else:
                why = check_team(t["format"] or "classic", t["league_name"], team)
                if not why and team_taken(cursor, tid, team, user_id):
                    why = "team_taken"
        if why:
            cursor.execute("ROLLBACK")
            return False, why
        cursor.execute("UPDATE pt_members SET team_name = ? WHERE tournament_id = ? AND user_id = ?",
                       (team, tid, user_id))
        cursor.execute("COMMIT")
        return True, "ok"
    except sqlite3.IntegrityError:                       # bir vaqtda ikki kishi bir jamoani tanladi
        cursor.execute("ROLLBACK")
        return False, "team_taken"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_set_team: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
