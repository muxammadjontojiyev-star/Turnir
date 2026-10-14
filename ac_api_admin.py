"""
ac_api_admin.py — Osiyo Chempionlar ligasi ADMIN endpointlari (APIRouter).
ac_api.py 300 qatordan oshmasligi uchun alohida (qoida #21); api.py OXIRIDA include.

Ruxsat:
  - natija tuzatish/bekor qilish — bosh admin YOKI 'ac' scope admini
    (ac_api.get_authenticated_ac_admin);
  - ishtirokchini ko'chirish, diagnostika — faqat bosh admin.
is_playoff: ChL /cl/admin/match/* bilan bir xil — noto'g'ri belgi berilsa ham
ikkinchi jadval tekshiriladi (fallback), javobda HAQIQIY is_playoff qaytadi.
"""

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin, validate_scores
from ac_api import get_authenticated_ac_admin

router = APIRouter()


# ============ Natija tuzatish (liga bosqichi + play-off) ============

@router.get("/ac/admin/match/{match_id}/info")
def ac_admin_match_info(match_id: int, is_playoff: int = 0,
                        admin: dict = Depends(get_authenticated_ac_admin)):
    from ac_admin_fix import ac_admin_get_match_info, ac_admin_po_get_match_info
    first, second = ((ac_admin_po_get_match_info, ac_admin_get_match_info) if is_playoff
                     else (ac_admin_get_match_info, ac_admin_po_get_match_info))
    info = first(match_id) or second(match_id)
    if info is None:
        raise HTTPException(status_code=404, detail="match_not_found")
    info.setdefault("is_playoff", 0)
    return info


@router.post("/ac/admin/match/set-result")
def ac_admin_set_result(match_id: int, score1: int, score2: int, is_playoff: int = 0,
                        admin: dict = Depends(get_authenticated_ac_admin)):
    """
    Istalgan statusdan -> confirmed (katta hisob qarori ham shu). Play-off'da g'olib
    keyingi bosqichga o'tadi. Xato: match_not_found / draw_not_allowed /
    aggregate_draw_not_allowed -> 400
    """
    validate_scores(score1, score2)
    from ac_admin_fix import ac_admin_po_set_result, ac_admin_set_result as _set
    ok, reason = (ac_admin_po_set_result if is_playoff else _set)(match_id, score1, score2)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


@router.post("/ac/admin/match/cancel")
def ac_admin_match_cancel(match_id: int, is_playoff: int = 0,
                          admin: dict = Depends(get_authenticated_ac_admin)):
    """Natijani bekor qiladi -> pending (ishtirokchilar qayta kiritadi)."""
    from ac_admin_fix import ac_admin_cancel_match, ac_admin_po_cancel_match
    ok, reason = (ac_admin_po_cancel_match if is_playoff else ac_admin_cancel_match)(match_id)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return {"status": "ok", "match_id": match_id}


# ============ Diagnostika (faqat bosh admin) ============

@router.get("/ac/admin/group-blocking")
def ac_admin_group_blocking(admin: dict = Depends(get_authenticated_super_admin)):
    """groups_not_finished chiqqanda QAYSI o'yinlar bloklayotganini ko'rsatadi (faqat o'qish)."""
    from ac_diagnostics import ac_group_blocking
    return ac_group_blocking()


# ============ Ishtirokchini yangi akkountga ko'chirish (faqat bosh admin) ============

@router.get("/ac/participants/all")
def ac_participants_all(admin: dict = Depends(get_authenticated_super_admin)):
    from ac_participant_admin import ac_list_all_participants
    return {"participants": ac_list_all_participants()}


@router.post("/ac/participant/reassign")
def ac_participant_reassign(
    old_user_id: int = Body(..., embed=True),
    new_telegram_id: int = Body(..., embed=True),
    admin: dict = Depends(get_authenticated_super_admin),
):
    """Xato: new_user_not_found, nothing_to_reassign, new_already_participant -> 400"""
    from ac_participant_admin import ac_reassign_participant
    ok, result = ac_reassign_participant(old_user_id, new_telegram_id)
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


# ============ Mavsumni yakunlash (faqat bosh admin) ============

@router.post("/season/ac/finalize")
def season_ac_finalize(admin: dict = Depends(get_authenticated_super_admin)):
    """
    Final g'olibi OChL kubogini oladi (season_prizes, doimiy — profil va ★), so'ng
    OChL ma'lumoti tozalanadi. Qaytarib bo'lmaydi.
    Xato: already_finalized / no_champion -> 400
    """
    from ac_finalize import AC_PRIZE_CUP, finalize_ac_season
    result = finalize_ac_season()
    if result.get("already"):
        raise HTTPException(status_code=400, detail="already_finalized")
    if result.get("reason") == "no_champion":
        raise HTTPException(status_code=400, detail="no_champion")
    return {"status": "ok", "season": result["season"], "counts": result["counts"],
            "champion": (result.get("prizes") or {}).get(AC_PRIZE_CUP)}

