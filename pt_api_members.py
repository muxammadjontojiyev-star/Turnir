"""
pt_api_members.py — SHAXSIY turnirga qo'shilish endpointlari (3-bosqich, APIRouter).
pt_api.py 300 qatordan oshmasligi uchun alohida (qoida #21); api.py OXIRIDA include.
Biznes-mantiq pt_members.py'da — endpoint faqat chaqiradi va xabar yuboradi (qoida #27).
Bildirishnoma xatosi so'rovni buzmaydi (log bilan — qoida #37/#44).
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_user
from config import BOT_USERNAME

logger = logging.getLogger("pt_api_members")
router = APIRouter()


def _who(user: dict) -> str:
    return "@" + user["username"] if user.get("username") else (user.get("nickname") or "")


async def _notify(telegram_id: int, language: str | None, key: str, **fmt) -> None:
    from notify import notify_user
    try:
        await notify_user(telegram_id, key, language, open_button_key="btn_open_app", **fmt)
    except Exception as exc:
        logger.warning("PT a'zolik xabari yuborilmadi (%s, %s): %s", key, telegram_id, exc)


@router.get("/pt/invite/{code}")
def pt_invite(code: str, user: dict = Depends(get_authenticated_user)):
    """Taklif havolasi ko'rinishi (turnir nomi, tashkilotchi, joylar, mening holatim)."""
    from pt_members import pt_invite_preview
    p = pt_invite_preview(code, user["id"])
    if p is None:
        raise HTTPException(status_code=404, detail="not_found")
    return p


@router.post("/pt/join")
async def pt_join(code: str = Body(..., embed=True), team: str | None = Body(None, embed=True),
                  user: dict = Depends(get_authenticated_user)):
    """So'rov yuborish (pending). Xato: not_found, not_recruiting, already_member, full,
    bad_team, team_taken, league_locked -> 400 (2026-10-07: team — ixtiyoriy klub/terma jamoa)"""
    import sqlite3
    from pt_members import pt_request_join
    try:
        ok, r = pt_request_join(code, user, team)
    except sqlite3.IntegrityError:                       # bir vaqtda shu jamoa band qilindi
        ok, r = False, "team_taken"
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    for mgr in r["managers"]:                            # tashkilotchi + adminlar
        await _notify(mgr["telegram_id"], mgr.get("language"), "pt_notify_join_request",
                      who=_who(user), name=r["name"])
    return {"status": "pending", "tournament_id": r["tournament_id"]}


@router.get("/pt/{tournament_id}/invite-link")
def pt_invite_link(tournament_id: int, user: dict = Depends(get_authenticated_user)):
    """Tashkilotchiga taklif havolasi (faqat recruiting holatida)."""
    from pt_core import STATUS_RECRUITING, pt_get_tournament
    t = pt_get_tournament(tournament_id, user["id"])
    if t is None or not t["is_manager"]:                 # tashkilotchi yoki admin
        raise HTTPException(status_code=404, detail="not_found")
    if t["status"] != STATUS_RECRUITING:
        raise HTTPException(status_code=400, detail="not_recruiting")
    if not BOT_USERNAME:
        raise HTTPException(status_code=503, detail="bot_username_missing")
    return {"link": f"https://t.me/{BOT_USERNAME}?start=pt_{t['invite_code']}"}


@router.post("/pt/{tournament_id}/members/{member_user_id}/approve")
async def pt_member_approve(tournament_id: int, member_user_id: int,
                            user: dict = Depends(get_authenticated_user)):
    """Xato: not_found, not_owner, not_recruiting, member_not_found, already_approved, full -> 400"""
    from pt_members import pt_approve_member
    ok, r = pt_approve_member(tournament_id, user["id"], member_user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    await _notify(r["telegram_id"], r["language"], "pt_notify_join_approved", name=r["name"])
    return {"status": "ok"}


@router.post("/pt/{tournament_id}/members/{member_user_id}/remove")
async def pt_member_remove(tournament_id: int, member_user_id: int,
                           user: dict = Depends(get_authenticated_user)):
    """So'rovni rad etish yoki a'zoni chiqarish. Xato: cannot_remove_owner, not_owner, ... -> 400"""
    from pt_members import pt_remove_member
    ok, r = pt_remove_member(tournament_id, user["id"], member_user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    await _notify(r["telegram_id"], r["language"], "pt_notify_removed", name=r["name"])
    return {"status": "ok"}


@router.post("/pt/{tournament_id}/members/add")
async def pt_member_add(tournament_id: int, query: str = Body(..., embed=True),
                        user: dict = Depends(get_authenticated_user)):
    """ID yoki @username bilan qo'shish. Xato: user_not_found, already_member, full, ... -> 400"""
    from pt_members import pt_add_member
    ok, r = pt_add_member(tournament_id, user["id"], query)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    await _notify(r["telegram_id"], r["language"], "pt_notify_added", name=r["name"])
    return {"status": "ok", "user_id": r["user_id"]}


@router.post("/pt/{tournament_id}/members/{member_user_id}/replace")
async def pt_member_replace(tournament_id: int, member_user_id: int, query: str = Body(..., embed=True),
                            user: dict = Depends(get_authenticated_user)):
    """
    2026-10-10: a'zoni yangi odamga almashtirish (Telegram ID yoki @username) — o'rin, klub,
    o'yinlar va natijalar saqlanadi. Xato: user_not_found, already_member, same_user,
    cannot_replace_owner, member_not_found, finished, not_owner -> 400
    """
    from pt_replace import pt_replace_member
    ok, r = pt_replace_member(tournament_id, user["id"], member_user_id, query)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    await _notify(r["old"]["telegram_id"], r["old"]["language"], "pt_notify_removed", name=r["name"])
    await _notify(r["new"]["telegram_id"], r["new"]["language"], "pt_notify_added", name=r["name"])
    return {"status": "ok", "user_id": r["new"]["user_id"]}


# ============ Turnir adminlari (faqat tashkilotchi boshqaradi) ============

@router.post("/pt/{tournament_id}/admins/add")
async def pt_admin_add(tournament_id: int, query: str = Body(..., embed=True),
                       user: dict = Depends(get_authenticated_user)):
    """Xato: not_owner, finished, user_not_found, is_owner, already_admin -> 400"""
    from pt_admins import pt_add_admin
    ok, r = pt_add_admin(tournament_id, user["id"], query)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    await _notify(r["telegram_id"], r["language"], "pt_notify_admin_added", name=r["name"])
    return {"status": "ok", "user_id": r["user_id"]}


@router.post("/pt/{tournament_id}/admins/{admin_user_id}/remove")
def pt_admin_remove(tournament_id: int, admin_user_id: int, user: dict = Depends(get_authenticated_user)):
    """Xato: not_owner, finished, admin_not_found -> 400"""
    from pt_admins import pt_remove_admin
    ok, r = pt_remove_admin(tournament_id, user["id"], admin_user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return {"status": "ok"}



@router.post("/pt/{tournament_id}/team")
def pt_team(tournament_id: int, team: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """2026-10-07: a'zo klub/terma jamoa tanlaydi (qur'agacha).
    Xato: not_member, not_recruiting, no_teams, bad_team, team_taken, league_locked -> 400; not_found -> 404"""
    from pt_teams import pt_set_team
    ok, r = pt_set_team(tournament_id, user["id"], team)
    if not ok:
        raise HTTPException(status_code=404 if r == "not_found" else 400, detail=r)
    return {"status": "ok", "team": team}
