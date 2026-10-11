"""
chat_images_api.py — bot chatida rasm (APIRouter, 2026-10-11). Mantiq: chat_images.py.

  POST /chat/image          {mode, match_id, image_base64} → chatga "📷 [img:token]"
  GET  /chat/image/{token}  rasm baytlari (faqat ishtirokchi yoki rejim admini)

Barcha rejimlar bitta endpointdan (room-code naqshi): league | cl | cl_po | div |
wc | wc_po | el | el_po | pt.
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response

from api import get_authenticated_user

logger = logging.getLogger("chat_images_api")
router = APIRouter()

_BAD_REQUEST = ("bad_mode", "empty_image", "image_too_large", "bad_image", "too_many_images")


@router.post("/chat/image")
async def chat_image_send(
    match_id: int = Body(..., embed=True),
    image_base64: str = Body(..., embed=True),
    mode: str = Body("league", embed=True),
    user: dict = Depends(get_authenticated_user),
):
    from chat_images import send_chat_image
    from room_code import MODE_NAME_KEYS
    ok, reason, info = send_chat_image(match_id, user["id"], image_base64, mode)
    if not ok:
        if reason in _BAD_REQUEST:
            raise HTTPException(status_code=400, detail=reason)
        if reason == "not_participant":
            raise HTTPException(status_code=403, detail="chat_no_access")
        if reason == "match_not_found":
            raise HTTPException(status_code=404, detail="match_not_found")
        raise HTTPException(status_code=500, detail="send_failed")

    if info["recipient_telegram_id"] is not None:
        try:
            from notify import notify_user_photo
            from queries_users import get_user_by_telegram_id
            from texts import t
            recipient = get_user_by_telegram_id(info["recipient_telegram_id"])
            lang = recipient.get("language") if recipient else None
            await notify_user_photo(
                info["recipient_telegram_id"], info["data"], info["mime"],
                "notify_chat_image", lang, open_button_key="btn_open_app",
                mode=t(MODE_NAME_KEYS.get(info["mode"], "mode_name_league"), lang),
            )
        except Exception as exc:
            # Rasm chatda saqlandi — bildirishnoma yiqilsa javob buzilmaydi (qoida #44)
            logger.warning("Chat rasmi bildirishnomasi yuborilmadi: %s", exc)

    return {"ok": True, "token": info["token"]}


@router.get("/chat/image/{token}")
def chat_image_get(token: str, user: dict = Depends(get_authenticated_user)):
    from chat_images import get_chat_image
    r = get_chat_image(token, user["id"], user["telegram_id"])
    if r is None:
        raise HTTPException(status_code=404, detail="not_found")
    data, mime = r
    # token o'zgarmas — brauzer keshlasin (lekin faqat shu foydalanuvchida)
    return Response(content=data, media_type=mime, headers={"Cache-Control": "private, max-age=86400"})
