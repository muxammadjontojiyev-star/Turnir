"""
el_api.py — Yevropa ligasi (YeL) API endpointlari (FastAPI APIRouter).

Nega alohida fayl (qoida #19/#21): api.py 3000+ qator; YeL endpointlari
bir joyda jamlanadi. api.py OXIRIDA app.include_router(router) qilinadi.

Import tartibi: bu modul api.py ning eng oxiridan import qilinadi — o'sha
paytda get_authenticated_user / get_authenticated_super_admin allaqachon
e'lon qilingan bo'ladi (api modul sys.modules'da), shuning uchun aylanma
import xavfsiz. api.py'dagi auth/rate-limit dependency'lari qayta ishlatiladi
(DRY, qoida #26) — ChL endpointlari bilan bir xil himoya.
"""

from fastapi import APIRouter, Depends, HTTPException

from api import get_authenticated_super_admin, get_authenticated_user

router = APIRouter()


# ============ Kvalifikatsiya / ishtirokchilar ============

@router.get("/el/qualifiers")
def el_qualifiers(user: dict = Depends(get_authenticated_user)):
    """YeL kvalifikantlari (oxirgi yakunlangan mavsum). me_qualified — so'rovchi kvalifikantmi."""
    from el_qualification import get_el_qualifiers, is_el_qualifier
    data = get_el_qualifiers()
    data["me_qualified"] = is_el_qualifier(user["telegram_id"], data["from_season"])
    return data


@router.get("/el/groups")
def el_groups(user: dict = Depends(get_authenticated_user)):
    """
    YeL ishtirokchilari. Avval sinxron: kvalifikant yangi mavsumda istalgan klub
    bilan ro'yxatdan o'tgan bo'lsa — telegram_id orqali avtomatik qo'shiladi.
    me_participant — so'rovchi YeL ishtirokchisimi.
    """
    from el_core import el_get_groups, el_sync_participants
    el_sync_participants()
    data = el_get_groups()
    data["me_participant"] = any(
        p["telegram_id"] == user["telegram_id"] for p in data["participants"]
    )
    return data


@router.get("/el/rating-all")
def el_rating_all(user: dict = Depends(get_authenticated_user)):
    """YeL yagona umumiy reyting (javob shakli /cl/rating-all bilan bir xil)."""
    from el_core import EL_LEAGUE_GROUP, el_group_rating
    rows = el_group_rating(EL_LEAGUE_GROUP)
    groups = [{"group_number": EL_LEAGUE_GROUP, "rating": rows}] if rows else []
    return {"groups": groups}


# ============ Turlar ============

@router.get("/el/state")
def el_state(user: dict = Depends(get_authenticated_user)):
    """YeL tur holati: started, current_matchday, total_matchdays, finished, stale."""
    from el_rounds import el_get_state
    return el_get_state()


@router.post("/el/draw")
def el_draw_endpoint(admin: dict = Depends(get_authenticated_super_admin)):
    """YeL Swiss qur'asi (bosh admin). Xato: already_drawn, no_participants -> 400"""
    from el_core import el_draw, el_sync_participants
    el_sync_participants()
    success, result = el_draw()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/el/rounds/start")
def el_rounds_start(admin: dict = Depends(get_authenticated_super_admin)):
    """YeL turlarini boshlash (bosh admin): 1-tur ochiladi. Xato: not_drawn, already_started -> 400"""
    from el_rounds import el_start_rounds
    success, result = el_start_rounds()
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


@router.post("/el/admin/group/force-close")
def el_admin_group_force_close(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Bosh admin liga bosqichini DARHOL yopadi (faqat bosqich tugagan bo'lsa).
    Xato: not_started, not_drawn, group_not_over, force_close_failed -> 400
    """
    from el_rounds import el_force_close_group
    ok, reason, info = el_force_close_group()
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", **info}
