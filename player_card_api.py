"""
player_card_api.py — SHAXSIY O'YINCHI KARTASI endpointlari (2026-11-04). Mantiq — player_card.py.
  GET  /pcard/options      — tanlanadigan pozitsiyalar va davlatlar
  GET  /pcard/{user_id}    — karta (OVR, pozitsiya, davlat, ramka); har kim ko'ra oladi (ommaviy profil kabi)
  POST /pcard/me           — {position, country} (null — ko'rsatilmasin). Xato (400): bad_position, bad_country
  POST   /pcard/me/photo           — o'zi tanlagan rasm {image: dataURL}; fon olib tashlanadi (player_cutout.py)
  DELETE /pcard/me/photo           — rasmni olib tashlash (kartada yana Telegram rasmi)
  DELETE /pcard/admin/{id}/photo   — bosh admin: nomaqbul rasmni o'chirish
  GET    /players/{id}/cardphoto   — karta rasmi (<img src>, auth yo'q). 404 — yuklanmagan
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Response

from api import get_authenticated_super_admin, get_authenticated_user

router = APIRouter()


@router.get("/pcard/options")
def pcard_options(user: dict = Depends(get_authenticated_user)):
    from player_card import COUNTRIES, POSITIONS
    return {"positions": list(POSITIONS), "countries": list(COUNTRIES)}


@router.get("/pcard/{user_id}")
def pcard_get(user_id: int, user: dict = Depends(get_authenticated_user)):
    from player_card import pcards_for_users
    card = pcards_for_users([user_id]).get(user_id)
    if card is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    return card


@router.post("/pcard/me")
def pcard_set(position: str | None = Body(None), country: str | None = Body(None),
              user: dict = Depends(get_authenticated_user)):
    from player_card import pcards_for_users, set_card_info
    ok, r = set_card_info(user["id"], position, country)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return pcards_for_users([user["id"]]).get(user["id"]) or {}



PHOTO_CACHE_HDR = "public, max-age=604800, immutable"   # URL'da ?v=versiya — rasm almashsa URL ham almashadi
PHOTO_ERRORS = {"too_big", "bad_image", "too_small", "daily_limit"}


@router.post("/pcard/me/photo")
async def pcard_photo_upload(image: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """{image: "data:image/jpeg;base64,..."} — frontend kichraytirib yuboradi. Xato (400): PHOTO_ERRORS."""
    import base64
    import binascii
    from player_cutout import PHOTO_MAX_BYTES, save_upload
    b64 = image.split(",", 1)[-1]
    if len(b64) > PHOTO_MAX_BYTES * 4 // 3 + 16:
        raise HTTPException(status_code=400, detail="too_big")
    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="bad_image")
    ok, r = await save_upload(user["id"], raw)
    if not ok:
        raise HTTPException(status_code=400, detail=r if r in PHOTO_ERRORS else "bad_image")
    from player_card import pcards_for_users
    return pcards_for_users([user["id"]]).get(user["id"]) or {}


@router.delete("/pcard/me/photo")
def pcard_photo_delete(user: dict = Depends(get_authenticated_user)):
    from player_card import pcards_for_users
    from player_cutout import delete_photo
    delete_photo(user["id"])
    return pcards_for_users([user["id"]]).get(user["id"]) or {}


@router.delete("/pcard/admin/{user_id}/photo")
def pcard_photo_admin_delete(user_id: int, admin: dict = Depends(get_authenticated_super_admin)):
    """Bosh admin — nomaqbul karta rasmini o'chirish."""
    import logging
    from player_cutout import delete_photo
    delete_photo(user_id)
    logging.getLogger(__name__).info("KARTA: bosh admin %s user %s karta rasmini o'chirdi", admin.get("id"), user_id)
    return {"ok": True}


@router.get("/players/{user_id}/cardphoto")
def pcard_photo_get(user_id: int):
    """Karta rasmi (<img src> — auth yo'q, /players/{id}/photo kabi). 404 — yuklanmagan."""
    from player_cutout import get_photo
    r = get_photo(user_id)
    if r is None:
        raise HTTPException(status_code=404, detail="no_photo")
    return Response(content=r[0], media_type=r[1], headers={"Cache-Control": PHOTO_CACHE_HDR})
