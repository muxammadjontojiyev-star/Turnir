"""
chat_rules_api.py — chat qoidalari API (2026-11-07). Qoidalar: chat_rules.py, kelishuv: chat_agree.py.

  GET  /crule/{mode}/{match_id}          — holat: tex win (mumkinmi, sababi, deadline, urinishlar), kelishuv, qo'lda natija
  POST /crule/techwin {mode, match_id}   — bot chatni tekshiradi; shart bajarilsa DARHOL 3:0 (rejimning o'z funksiyalari:
                                           da'vogar kiritadi + raqib nomidan tasdiqlanadi — barcha tekshiruvlar ishlaydi)
  POST /crule/agree {mode, match_id, at} — boshqa vaqtga taklif («YYYY-MM-DDTHH:MM», Toshkent)
  POST /crule/agree/{id}/decide {accept} — raqib: qabul / rad; taklif qilgan o'zi: bekor qilish (accept=false)
  POST /crule/room-copy {mode, match_id, code} — chatdagi xona ID nusxalandi (chat_room.py)
"""

import asyncio
import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from api import get_authenticated_super_admin, get_authenticated_user

logger = logging.getLogger(__name__)
router = APIRouter()
_LOCKS: dict[tuple[str, int], asyncio.Lock] = {}


def _match_or_404(mode: str, match_id: int) -> dict:
    from match_modes import MODES, get_match
    if mode not in MODES:
        raise HTTPException(status_code=400, detail="bad_mode")
    m = get_match(mode, match_id)
    if not m:
        raise HTTPException(status_code=404, detail="match_not_found")
    return m


async def _tell(user_id: int, key: str, mode: str, **fmt) -> None:
    from match_shot_api import MODE_LABEL_KEY
    from notify import notify_user
    from queries_users import get_user_by_id
    from texts import t
    u = get_user_by_id(user_id)
    if not u:
        return
    lang = u.get("language") or "uz"
    try:
        await notify_user(u["telegram_id"], key, lang, open_button_key="btn_open_app",
                          mode=t(MODE_LABEL_KEY.format(mode), lang), **fmt)
    except Exception as exc:
        logger.warning("CHAT QOIDA: xabar yuborilmadi (%s, %s): %s", user_id, key, exc)


def _concede_state(mode: str, m: dict, me: int) -> dict | None:
    """«Win sizga»: mine — men yozganman (so'rov chiqadi), theirs — raqib yozgan (men faqat 3:0 kirita olaman)."""
    from chat_concede import open_concession
    if m.get("status") != "pending":
        return None
    c = open_concession(mode, m)
    if not c:
        return None
    return {"msg_id": c["msg_id"], "mine": c["user_id"] == me, "text": c["text"]}


@router.get("/crule/{mode}/{match_id}")
def crule_state(mode: str, match_id: int, user: dict = Depends(get_authenticated_user)):
    from chat_agree import state
    from chat_rules import manual_check, tech_check
    m = _match_or_404(mode, match_id)
    if user["id"] not in (m.get("player1_id"), m.get("player2_id")):
        raise HTTPException(status_code=403, detail="not_participant")
    t_ok, t_why, t_info = tech_check(mode, m, user["id"])
    m_ok, m_why, _ = manual_check(mode, m, user["id"])
    return {"tech": {"ok": t_ok, "reason": t_why, **t_info}, "manual": {"ok": m_ok, "reason": m_why},
            "agree": state(mode, match_id, user["id"]), "status": m.get("status"),
            "concede": _concede_state(mode, m, user["id"]),
            "me_p1": user["id"] == m.get("player1_id")}


@router.post("/crule/room-copy")
def crule_room_copy(mode: str = Body(..., embed=True), match_id: int = Body(..., embed=True),
                    code: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """Chatdagi xona ID bosildi (nusxalandi) — raqib yuborgan ID bo'lsa yoziladi (qo'lda natija sharti)."""
    from chat_room import record_copy
    ok, why = record_copy(mode, _match_or_404(mode, match_id), user["id"], code)
    return {"ok": ok, "reason": why}


@router.post("/crule/techwin")
async def crule_techwin(mode: str = Body(..., embed=True), match_id: int = Body(..., embed=True),
                        user: dict = Depends(get_authenticated_user)):
    from chat_auto import apply_techwin
    from chat_rules import tech_check
    lock = _LOCKS.setdefault((mode, int(match_id)), asyncio.Lock())
    async with lock:                                    # ikki marta bosilsa — ikkinchisi «natija bor» deydi
        ok, why, _ = tech_check(mode, _match_or_404(mode, match_id), user["id"])
        if not ok:
            raise HTTPException(status_code=400, detail=why)
        ok, res = await apply_techwin(mode, match_id, user["id"], "button")
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/crule/concede")
async def crule_concede(mode: str = Body(..., embed=True), match_id: int = Body(..., embed=True),
                        msg_id: int = Body(..., embed=True), accept: bool = Body(..., embed=True),
                        user: dict = Depends(get_authenticated_user)):
    """«Win sizga» deb yozgan o'yinchi: «Ha» — raqibga darhol 3:0; «Yo'q» — taslim emas (chat_concede.py)."""
    from chat_auto import apply_techwin
    from chat_concede import decide
    m = _match_or_404(mode, match_id)
    if m.get("status") != "pending":
        raise HTTPException(status_code=400, detail="tech_has_result")
    ok, r = decide(mode, m, user["id"], msg_id, accept)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    if not accept:
        return {"status": "declined"}
    ok, res = await apply_techwin(mode, match_id, r["winner_id"], "concede")
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.get("/crule/config")
def crule_config(user: dict = Depends(get_authenticated_user)):
    from chat_rules import REPLY_MAX_H_MAX, REPLY_MAX_H_MIN, reply_max_h
    return {"reply_max_h": reply_max_h(), "min": REPLY_MAX_H_MIN, "max": REPLY_MAX_H_MAX}


@router.post("/crule/admin/config")
def crule_admin_config(reply_max_h: int = Body(..., embed=True), admin: dict = Depends(get_authenticated_super_admin)):
    from chat_rules import set_reply_max_h
    h = set_reply_max_h(reply_max_h)
    logger.info("CHAT QOIDA: javob kechikishi chegarasi — %s soat (admin %s)", h, admin.get("id"))
    return {"reply_max_h": h}


@router.post("/crule/agree")
async def crule_agree(mode: str = Body(..., embed=True), match_id: int = Body(..., embed=True),
                      at: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from chat_agree import parse_at, propose
    m = _match_or_404(mode, match_id)
    dt = parse_at(at)
    if dt is None:
        raise HTTPException(status_code=400, detail="agree_bad_time")
    ok, r = propose(mode, m, user["id"], dt)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    await _tell(r["opponent_id"], "crule_notify_agree_proposed", mode, at=r["at"])
    return r


@router.post("/crule/agree/{agree_id}/decide")
async def crule_agree_decide(agree_id: int, accept: bool = Body(..., embed=True),
                             user: dict = Depends(get_authenticated_user)):
    from chat_agree import decide
    from chat_rules import deadline_for, now_local
    from match_modes import get_match
    ok, r = decide(agree_id, user["id"], accept)
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    if r["status"] == "accepted":
        await _tell(r["proposer_id"], "crule_notify_agree_accepted", r["mode"], at=r["at"])
        m = get_match(r["mode"], r["match_id"]) or {}
        from chat_agree import active_lock
        lk, dl = active_lock(r["mode"], r["match_id"]), deadline_for(r["mode"], m, now_local())
        if lk and dl and lk >= dl:                      # kelishilgan vaqt deadline'dan keyin — ikkalasiga ogohlantirish
            r["after_deadline"] = True
            for uid in (r["proposer_id"], r["opponent_id"]):
                await _tell(uid, "crule_notify_agree_late", r["mode"])
    elif r["status"] == "declined":
        await _tell(r["proposer_id"], "crule_notify_agree_declined", r["mode"], at=r["at"])
    return r
