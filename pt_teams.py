"""
pt_teams.py — SHAXSIY turnirda klub / terma jamoa tanlash (2026-10-07).

Admin qarori: liga formatida — tanlangan ligadagi klublardan, ChL/YeL — 5 ligadagi barcha
klublardan, JCh — rasmiy JCh'dagi 48 terma jamoadan; bitta jamoa — bitta ishtirokchi.
Tanlash/almashtirish faqat qur'agacha (recruiting); a'zo (approved yoki pending) o'zi tanlaydi.
Band qilish poyga holatidan UNIQUE indeks bilan himoyalangan (idx_pt_members_team).

2026-10-08: ko'p ligali turnirda ligalar KETMA-KET ochiladi (rasmiy ligalar kabi —
api._is_league_locked): keyingi liga klubini faqat undan oldingi barcha ligalar to'lgach
tanlash mumkin (league_locked). Ligalar tartibi — tashkilotchi tanlagan tartib.
"To'lgan" = ligadagi barcha klublar band (approved yoki pending a'zo). O'z jamoasi hisobga
olinmaydi — to'lgan 1-ligadan 2-ligaga o'tib, 1-ligani bo'shatib qo'yib bo'lmaydi.
"""

import logging
import sqlite3

from models import get_connection
from pt_formats import FMT_LEAGUE, LEAGUE_CLUBS, club_league, split_leagues, teams_for, uses_teams

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


def league_locked(cursor, tid: int, league: str | None, team: str, user_id: int) -> bool:
    """Klub ligasidan oldingi ligalardan biri to'lmagan bo'lsa — True (tanlab bo'lmaydi)."""
    leagues = split_leagues(league)
    lg = club_league(team, league)
    if len(leagues) < 2 or lg is None:
        return False
    for prev in leagues[:leagues.index(lg)]:
        clubs = LEAGUE_CLUBS.get(prev, ())
        marks = ",".join("?" * len(clubs))
        cursor.execute(f"SELECT COUNT(*) AS c FROM pt_members WHERE tournament_id = ? AND user_id != ? "
                       f"AND team_name IN ({marks})", (tid, user_id, *clubs))
        if cursor.fetchone()["c"] < len(clubs):
            return True
    return False


def team_block(cursor, tid: int, fmt: str, league: str | None, team, user_id: int) -> str | None:
    """Jamoani tanlash to'sig'i (DRY: so'rov va almashtirish): bad_team / no_teams / team_taken /
    league_locked; None — mumkin."""
    why = check_team(fmt, league, team)
    if why:
        return why
    if team_taken(cursor, tid, team, user_id):
        return "team_taken"
    if fmt == FMT_LEAGUE and league_locked(cursor, tid, league, team, user_id):
        return "league_locked"
    return None


def pt_set_team(tid: int, user_id: int, team) -> tuple[bool, str]:
    """
    A'zo o'z jamoasini tanlaydi/almashtiradi (faqat recruiting).
    Sabablar: not_found, not_member, not_recruiting, no_teams, bad_team, team_taken, league_locked.
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
                why = team_block(cursor, tid, t["format"] or "classic", t["league_name"], team, user_id)
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
