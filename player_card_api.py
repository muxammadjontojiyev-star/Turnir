"""
player_card_api.py — SHAXSIY O'YINCHI KARTASI endpointlari (2026-11-04). Mantiq — player_card.py.
  GET  /pcard/options      — tanlanadigan pozitsiyalar va davlatlar
  GET  /pcard/{user_id}    — karta (OVR, pozitsiya, davlat, ramka); har kim ko'ra oladi (ommaviy profil kabi)
  POST /pcard/me           — {position, country} (null — ko'rsatilmasin). Xato (400): bad_position, bad_country
  GET  /players/{user_id}/cutout — rasmdan qirqilgan odam (WEBP, shaffof; player_cutout.py). Auth yo'q —
       <img src> orqali yuklanadi (/players/{id}/photo kabi). 404 — odam/rasm yo'q, 503 — navbat band.
"""

import asyncio

from fastapi import APIRouter, Body, Depends, HTTPException, Response

from api import get_authenticated_user

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


CUTOUT_CACHE_HDR = "public, max-age=3600"


@router.get("/players/{user_id}/cutout")
async def pcard_cutout(user_id: int):
    from player_cutout import get_cutout
    from queries_users import get_user_by_id
    target = get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    try:
        img = await get_cutout(user_id, target["telegram_id"])
    except (TimeoutError, asyncio.TimeoutError):
        raise HTTPException(status_code=503, detail="busy")
    if not img:
        raise HTTPException(status_code=404, detail="no_cutout")
    return Response(content=img, media_type="image/webp", headers={"Cache-Control": CUTOUT_CACHE_HDR})
