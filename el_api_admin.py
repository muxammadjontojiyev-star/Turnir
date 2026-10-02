"""
el_api_admin.py — Yevropa ligasi ADMIN endpointlari (APIRouter).
el_api.py 300 qatordan oshmasligi uchun alohida (qoida #21); api.py OXIRIDA include.

Ruxsat:
  - natija tuzatish/bekor qilish — bosh admin YOKI 'el' scope admini
    (el_api.get_authenticated_el_admin);
  - ishtirokchini ko'chirish, diagnostika — faqat bosh admin.
is_playoff: ChL /cl/admin/match/* bilan bir xil — noto'g'ri belgi berilsa ham
ikkinchi jadval tekshiriladi (fallback), javobda HAQIQIY is_playoff qaytadi.
"""

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin, validate_scores
from el_api import get_authenticated_el_admin

router = APIRouter()


# ============ Natija tuzatish (liga bosqichi + play-off) ============

@router.get("/el/admin/match/{match_id}/info")
def el_admin_match_info(match_id: int, is_playoff: int = 0,
                        admin: dict = Depends(get_authenticated_el_admin)):
    from el_admin_fix import el_admin_get_match_info, el_admin_po_get_match_info
    first, second = ((el_admin_po_get_match_info, el_admin_get_match_info) if is_playoff
                     else (el_admin_get_match_info, el_admin_po_get_match_info))
    info = first(match_id) or second(match_id)
    if info is None:
        raise HTTPException(status_code=404, detail="match_not_found")
    info.setdefault("is_playoff", 0)
    return info


@router.post("/el/admin/match/set-result")
def el_admin_set_result(match_id: int, score1: int, score2: int, is_playoff: int = 0,
                        admin: dict = Depends(get_authenticated_el_admin)):
    """
    Istalgan statusdan -> confirmed (katta hisob qarori ham shu). Play-off'da g'olib
    keyingi bosqichga o'tadi. Xato: match_not_found / draw_not_allowed /
    aggregate_draw_not_allowed -> 400
    """
    validate_scores(score1, score2)
    from el_admin_fix import el_admin_po_set_result, el_admin_set_result as _set
    ok, reason = (el_admin_po_set_result if is_playoff else _set)(match_id, score1, score2)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@router.post("/el/admin/match/cancel")
def el_admin_match_cancel(match_id: int, is_playoff: int = 0,
                          admin: dict = Depends(get_authenticated_el_admin)):
    """Natijani bekor qiladi -> pending (ishtirokchilar qayta kiritadi)."""
    from el_admin_fix import el_admin_cancel_match, el_admin_po_cancel_match
    ok, reason = (el_admin_po_cancel_match if is_playoff else el_admin_cancel_match)(match_id)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ Diagnostika (faqat bosh admin) ============

@router.get("/el/admin/group-blocking")
def el_admin_group_blocking(admin: dict = Depends(get_authenticated_super_admin)):
    """groups_not_finished chiqqanda QAYSI o'yinlar bloklayotganini ko'rsatadi (faqat o'qish)."""
    from el_diagnostics import el_group_blocking
    return el_group_blocking()


# ============ Ishtirokchini yangi akkountga ko'chirish (faqat bosh admin) ============

@router.get("/el/participants/all")
def el_participants_all(admin: dict = Depends(get_authenticated_super_admin)):
    from el_participant_admin import el_list_all_participants
    return {"participants": el_list_all_participants()}


@router.post("/el/participant/reassign")
def el_participant_reassign(
    old_user_id: int = Body(..., embed=True),
    new_telegram_id: int = Body(..., embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """Xato: new_user_not_found, nothing_to_reassign, new_already_participant -> 400"""
    from el_participant_admin import el_reassign_participant
    ok, result = el_reassign_participant(old_user_id, new_telegram_id)
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}
