"""
tb_manage.py — "TEAMLAR JANGI": a'zolar boshqaruvi (sardor) va bosh admin amallari
(2026-10-15, 1-bosqich). tb_core.py dan ajratildi (qoida #21).
Har amal BEGIN IMMEDIATE ichida (qoida #38); ruxsat — sardor / bosh admin (qoida #34).
"""

import logging
import secrets

from models import get_connection
from tb_core import (
    ROLE_CAPTAIN, ROLE_MEMBER, STATUS_APPROVED, STATUS_REJECTED,
    _INVITE_CODE_BYTES, _begin, _finish, _league_limits, _my_membership,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ a'zolar boshqaruvi

def _captain_team(cur, user_id: int):
    m = _my_membership(cur, user_id)
    return m["team_id"] if m and m["role"] == ROLE_CAPTAIN else None


def tb_leave(user_id: int) -> tuple[bool, str | dict]:
    """
    A'zo teamdan chiqadi. Sardor chiqa olmaydi — avval sardorlikni topshiradi yoki teamni tarqatadi.
    Sabablar: not_in_team, captain_cannot_leave.
    """
    conn = get_connection()
    cur = _begin(conn)
    try:
        m = _my_membership(cur, user_id)
        if not m:
            _finish(cur, False)
            return False, "not_in_team"
        if m["role"] == ROLE_CAPTAIN:
            _finish(cur, False)
            return False, "captain_cannot_leave"
        cur.execute("DELETE FROM tb_members WHERE user_id = ?", (user_id,))
        _finish(cur, True)
        return True, {"team_id": m["team_id"]}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def tb_remove_member(captain_id: int, member_user_id: int) -> tuple[bool, str | dict]:
    """Sabablar: not_captain, member_not_found, cannot_remove_self."""
    conn = get_connection()
    cur = _begin(conn)
    try:
        team_id = _captain_team(cur, captain_id)
        if not team_id:
            _finish(cur, False)
            return False, "not_captain"
        if member_user_id == captain_id:
            _finish(cur, False)
            return False, "cannot_remove_self"
        cur.execute("DELETE FROM tb_members WHERE team_id = ? AND user_id = ? AND role = ?",
                    (team_id, member_user_id, ROLE_MEMBER))
        ok = cur.rowcount > 0
        _finish(cur, ok)
        return (True, {"team_id": team_id}) if ok else (False, "member_not_found")
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def tb_transfer_captain(captain_id: int, new_user_id: int) -> tuple[bool, str | dict]:
    """Sardorlikni o'z teamidagi a'zoga topshirish. Sabablar: not_captain, member_not_found."""
    conn = get_connection()
    cur = _begin(conn)
    try:
        team_id = _captain_team(cur, captain_id)
        if not team_id:
            _finish(cur, False)
            return False, "not_captain"
        cur.execute("SELECT 1 FROM tb_members WHERE team_id = ? AND user_id = ? AND role = ?",
                    (team_id, new_user_id, ROLE_MEMBER))
        if not cur.fetchone():
            _finish(cur, False)
            return False, "member_not_found"
        cur.execute("UPDATE tb_members SET role = ? WHERE team_id = ? AND user_id = ?",
                    (ROLE_MEMBER, team_id, captain_id))
        cur.execute("UPDATE tb_members SET role = ? WHERE team_id = ? AND user_id = ?",
                    (ROLE_CAPTAIN, team_id, new_user_id))
        cur.execute("UPDATE tb_teams SET captain_user_id = ? WHERE id = ?", (new_user_id, team_id))
        _finish(cur, True)
        return True, {"team_id": team_id}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def tb_set_lineup(captain_id: int, user_ids: list[int]) -> tuple[bool, str | dict]:
    """
    Asosiy tarkib (tartib bilan). Sabablar: not_captain, lineup_size, lineup_duplicate, lineup_not_member.
    """
    ids = [int(x) for x in (user_ids or [])]
    if len(set(ids)) != len(ids):
        return False, "lineup_duplicate"
    conn = get_connection()
    cur = _begin(conn)
    try:
        team_id = _captain_team(cur, captain_id)
        if not team_id:
            _finish(cur, False)
            return False, "not_captain"
        lmin, lmax = _league_limits(cur, team_id)          # 2026-10-16: liga sozlamasi
        if len(ids) < lmin or len(ids) > lmax:
            _finish(cur, False)
            return False, "lineup_size"
        cur.execute("SELECT user_id FROM tb_members WHERE team_id = ?", (team_id,))
        members = {r["user_id"] for r in cur.fetchall()}
        if not set(ids) <= members:
            _finish(cur, False)
            return False, "lineup_not_member"
        cur.execute("UPDATE tb_members SET in_lineup = 0, lineup_pos = NULL WHERE team_id = ?", (team_id,))
        for pos, uid in enumerate(ids, start=1):
            cur.execute("UPDATE tb_members SET in_lineup = 1, lineup_pos = ? WHERE team_id = ? AND user_id = ?",
                        (pos, team_id, uid))
        _finish(cur, True)
        return True, {"team_id": team_id, "lineup": len(ids)}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def tb_regen_invite(captain_id: int) -> tuple[bool, str | dict]:
    """Taklif havolasini yangilash (eski havola ishlamay qoladi). Sabab: not_captain."""
    conn = get_connection()
    cur = _begin(conn)
    try:
        team_id = _captain_team(cur, captain_id)
        if not team_id:
            _finish(cur, False)
            return False, "not_captain"
        code = secrets.token_urlsafe(_INVITE_CODE_BYTES)
        cur.execute("UPDATE tb_teams SET invite_code = ? WHERE id = ?", (code, team_id))
        _finish(cur, True)
        return True, {"invite_code": code}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def _in_active_season(cur, team_id: int) -> bool:
    """
    2026-10-16: team biror mavsum qur'asida qatnashganmi. Qatnashgan team o'chirilmaydi —
    bahslar va jadval tarixi unga bog'langan (FK).
    """
    cur.execute("SELECT 1 FROM tb_season_teams WHERE team_id = ? LIMIT 1", (team_id,))
    return cur.fetchone() is not None


def _delete_team(cur, team_id: int) -> None:
    from tb_logos import delete_logo_cur
    delete_logo_cur(cur, "team", team_id)             # 2026-10-16: logosi ham
    cur.execute("DELETE FROM tb_members WHERE team_id = ?", (team_id,))
    cur.execute("DELETE FROM tb_teams WHERE id = ?", (team_id,))


def tb_dissolve(captain_id: int) -> tuple[bool, str | dict]:
    """Sardor teamni tarqatadi (barcha a'zolar chiqadi). Sabab: not_captain."""
    conn = get_connection()
    cur = _begin(conn)
    try:
        team_id = _captain_team(cur, captain_id)
        if not team_id:
            _finish(cur, False)
            return False, "not_captain"
        if _in_active_season(cur, team_id):          # 2026-10-16: mavsum davomida tarqatib bo'lmaydi
            _finish(cur, False)
            return False, "in_active_season"
        _delete_team(cur, team_id)
        _finish(cur, True)
        logger.info("TB: team tarqatildi id=%s (sardor user=%s)", team_id, captain_id)
        return True, {"team_id": team_id}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


# ------------------------------------------------------------------ liga admini / bosh admin

def tb_admin_review(team_id: int, admin_tg: int, approve: bool, reason: str | None = None
                    ) -> tuple[bool, str | dict]:
    """Tasdiqlash/rad etish. Sabablar: not_found. Qaytaradi: {captain_telegram_id, language, name}."""
    conn = get_connection()
    cur = _begin(conn)
    try:
        cur.execute("SELECT t.id, t.name, u.telegram_id, u.language FROM tb_teams t "
                    "JOIN users u ON u.id = t.captain_user_id WHERE t.id = ?", (team_id,))
        t = cur.fetchone()
        if not t:
            _finish(cur, False)
            return False, "not_found"
        cur.execute(
            "UPDATE tb_teams SET status = ?, reject_reason = ?, reviewed_by = ?, "
            "reviewed_at = datetime('now') WHERE id = ?",
            (STATUS_APPROVED if approve else STATUS_REJECTED,
             None if approve else (reason or "").strip()[:200] or None, admin_tg, team_id),
        )
        _finish(cur, True)
        return True, {"captain_telegram_id": t["telegram_id"], "language": t["language"], "name": t["name"]}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


def tb_team_league(team_id: int) -> int | None:
    """Admin amallarida ruxsat tekshiruvi uchun: team ligasi."""
    from tb_core import tb_team_league_id
    return tb_team_league_id(team_id)


def tb_admin_delete(team_id: int) -> tuple[bool, str | dict]:
    conn = get_connection()
    cur = _begin(conn)
    try:
        cur.execute("SELECT 1 FROM tb_teams WHERE id = ?", (team_id,))
        if not cur.fetchone():
            _finish(cur, False)
            return False, "not_found"
        if _in_active_season(cur, team_id):
            _finish(cur, False)
            return False, "in_active_season"
        _delete_team(cur, team_id)
        _finish(cur, True)
        return True, {"team_id": team_id}
    except Exception:
        _finish(cur, False)
        raise
    finally:
        conn.close()


TB_BULK_DELETE_MAX = 200        # bir so'rovda o'chiriladigan teamlar soni chegarasi


def tb_admin_delete_many(team_ids: list[int], league_id: int) -> tuple[bool, str | dict]:
    """
    2026-10-16: tanlangan teamlarni bir yo'la o'chirish (shaxsiy turnirdagi kabi).
    Faqat shu LIGA teamlari o'chadi (boshqa liga teami — failed, qoida #34);
    mavsumda qatnashgan team ham o'chirilmaydi (tb_admin_delete -> in_active_season).
    Sabablar: empty, too_many. Qaytaradi: {deleted: [id], failed: [id]}.
    """
    from tb_core import tb_team_league_id
    uniq = list(dict.fromkeys(int(i) for i in (team_ids or []) if int(i) > 0))
    if not uniq:
        return False, "empty"
    if len(uniq) > TB_BULK_DELETE_MAX:
        return False, "too_many"
    deleted, failed = [], []
    for tid in uniq:
        try:
            ok = tb_team_league_id(tid) == league_id and tb_admin_delete(tid)[0]
        except Exception:
            logger.exception("tb_admin_delete_many: team #%s o'chirilmadi", tid)
            ok = False
        (deleted if ok else failed).append(tid)
    logger.info("TB bulk delete (liga %s): %d o'chirildi, %d o'chirilmadi", league_id, len(deleted), len(failed))
    return True, {"deleted": deleted, "failed": failed}
