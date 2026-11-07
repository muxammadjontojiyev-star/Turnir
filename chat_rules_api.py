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

from api import get_authenticated_user

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
    from chat_rules import TECH_SCORE, tech_check
    from match_modes import confirm_as, get_match, submit_as
    from match_shot_api import _tell_admins
    from queries_users import get_user_by_id
    lock = _LOCKS.setdefault((mode, int(match_id)), asyncio.Lock())
    async with lock:                                    # ikki marta bosilsa — ikkinchisi «natija bor» deydi
        m = _match_or_404(mode, match_id)
        ok, why, _ = tech_check(mode, m, user["id"])
        if not ok:
            raise HTTPException(status_code=400, detail=why)
        me_p1 = user["id"] == m["player1_id"]
        opp_id = m["player2_id"] if me_p1 else m["player1_id"]
        s1, s2 = (TECH_SCORE, 0) if me_p1 else (0, TECH_SCORE)
        ok, res = await submit_as(mode, match_id, s1, s2, user)
        if not ok:
            raise HTTPException(status_code=400, detail=res)
        opp = get_user_by_id(opp_id)
        ok2, res2 = await confirm_as(mode, match_id, opp) if opp else (False, "opponent_not_found")
        if not ok2:                                     # kiritildi, tasdiq bo'lmadi — deadline'da avtomatik tasdiqlanadi
            logger.error("CHAT QOIDA: tex win tasdiqlanmadi %s #%s: %s", mode, match_id, res2)
        logger.info("CHAT QOIDA: TEX WIN %s #%s — user %s 3:0 (tasdiq: %s)", mode, match_id, user["id"], ok2)
    await _tell(opp_id, "crule_notify_tech_lost", mode)
    await _tell_admins(mode, match_id, "crule_admin_tech",
                       winner=user.get("nickname") or user.get("username") or str(user["id"]))
    final = get_match(mode, match_id) or {}
    return {"status": final.get("status"), "score1": s1, "score2": s2}


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
