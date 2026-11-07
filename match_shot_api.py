"""
match_shot_api.py — eF nikname, SKRINSHOTLI NATIJA, TEXNIK G'ALABA so'rovi va ADMIN KO'RIB CHIQISHI (2026-11-06).
Mantiq: ef_nick.py, match_shot.py, match_claims.py, match_modes.py.

  GET  /ef-nick                      — {nick, free_left, price, free_per_season}
  POST /ef-nick {nick, pay}          — xato: bad_nick, same_nick, nick_taken, nick_link_full, need_pay, insufficient;
                                       band nikname (shu mavsum) — egasiga ulash so'rovi, javobda link_requested
  GET  /ef-nick/links                — mening niknamemga ulash so'rovlari; POST /ef-nick/links/{id} {accept}
  POST /mshot/read {image}           — {token, rows[]}; xato: ocr_unavailable, no_rows, bad_image, daily_limit
  POST /mshot/apply {mode, match_id, token, row} — natija yoziladi; xato: expired, no_my_nick, no_opp_nick,
       nick_mismatch, bad_date, shot_used, playoff_draw, opp_other_score, my_other_score, already_confirmed, ...
  GET  /mshot/incoming               — men haqimda skrinshot bilan yozilgan natijalar (e'tiroz muddati ichida)
  POST /mshot/{id}/dispute           — e'tiroz → adminga
  POST /mshot/{id}/accept {nick}     — raqib niknamesi yo'q edi: tasdiqlash (+ niknamesi saqlanadi); /reject — rad
  POST /mshot/tech {mode, match_id, images[], note} — texnik g'alaba so'rovi
  GET  /mshot/admin/list             — ochiq ishlar (bosh admin + rejim/liga admini)
  GET  /mshot/admin/img/{kind}/{id}/{idx} — rasm (base64)
  POST /mshot/admin/decide {kind, id, action, s1, s2}
  GET  /mshot/config                 — {shot_only}: natija faqat skrinshot bilanmi (match_guard)
  POST /mshot/admin/only {on}        — bosh admin: kalitni yoqish/o'chirish
Rasmlar JSON'da dataURL (base64) — frontend kichraytirib yuboradi.
"""

import base64
import binascii
import logging

from fastapi import APIRouter, Body, Depends, Header, HTTPException

from api import get_authenticated_super_admin, get_authenticated_user

logger = logging.getLogger(__name__)
router = APIRouter()

IMG_MAX_BYTES = 8 * 1024 * 1024
MODE_LABEL_KEY = "mshot_mode_{}"
_NICK_REMINDED: set[int] = set()   # jarayon davomida bir martadan


def _b64(data_url: str) -> bytes:
    b = (data_url or "").split(",", 1)[-1]
    if len(b) > IMG_MAX_BYTES * 4 // 3 + 16:
        raise HTTPException(status_code=400, detail="too_big")
    try:
        return base64.b64decode(b, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="bad_image")


def _fail(ok_r):
    ok, r = ok_r
    if not ok:
        raise HTTPException(status_code=400, detail=r)
    return r


async def _tell(user_id: int, key: str, **fmt) -> None:
    from notify import notify_user
    from queries_users import get_user_by_id
    u = get_user_by_id(user_id)
    if u:
        try:
            await notify_user(u["telegram_id"], key, u.get("language"), open_button_key="btn_open_app", **fmt)
        except Exception as exc:
            logger.warning("MATCH SHOT: xabar yuborilmadi (%s): %s", user_id, exc)


async def _tell_admins(mode: str, match_id: int, key: str, **fmt) -> None:
    """Bosh adminlar + o'sha liga (ligada) / rejim adminlari (match_modes.reviewer_tgs), har biri o'z tilida."""
    from match_modes import get_match, reviewer_tgs
    from notify import notify_user
    from queries_users import get_user_by_telegram_id
    from texts import t
    m = get_match(mode, match_id)
    tgs = reviewer_tgs(mode, m or {})
    sent = 0
    for tg in tgs:
        u = get_user_by_telegram_id(tg) or {}
        lang = u.get("language")
        where = t("mshot_where_league" if mode == "league" else "mshot_where_mode", lang or "uz")
        try:
            sent += bool(await notify_user(tg, key, lang, open_button_key="btn_open_app",
                                           mode=t(MODE_LABEL_KEY.format(mode), lang or "uz"), where=where, match=match_id, **fmt))
        except Exception as exc:
            logger.warning("MATCH SHOT: adminga xabar yuborilmadi (%s): %s", tg, exc)
    logger.info("MATCH SHOT: %s #%s — %s: %s/%s adminga yuborildi (%s)", mode, match_id, key, sent, len(tgs), tgs)


# ---------------- eF nikname ----------------

@router.get("/ef-nick")
def ef_nick_get(user: dict = Depends(get_authenticated_user)):
    from ef_nick import get_nick_info
    return get_nick_info(user["id"])


@router.post("/ef-nick")
async def ef_nick_set(nick: str = Body(..., embed=True), pay: bool = Body(False, embed=True),
                user: dict = Depends(get_authenticated_user)):
    from ef_nick import get_nick_info, set_nick
    r = _fail(set_nick(user["id"], nick, pay))
    if isinstance(r, dict) and r.get("pending"):         # band nikname — egasiga tasdiq so'rovi (ef_nick_link)
        if not r.get("repeat"):
            await _tell(r["owner_id"], "efnick_link_request", who=_who_name(user))
        return {**get_nick_info(user["id"]), "link_requested": True}
    return r


def _who_name(user: dict) -> str:
    return ("@" + user["username"]) if user.get("username") else (user.get("nickname") or str(user.get("id")))


@router.get("/ef-nick/links")
def ef_nick_links(user: dict = Depends(get_authenticated_user)):
    """Mening niknamemga ulanmoqchi bo'lgan (ikkinchi) akkauntlar — tasdiq kutilmoqda."""
    from ef_nick_link import requests_for_owner
    return {"items": requests_for_owner(user["id"])}


@router.post("/ef-nick/links/{link_id}")
async def ef_nick_link_decide(link_id: int, accept: bool = Body(..., embed=True),
                              user: dict = Depends(get_authenticated_user)):
    from ef_nick_link import decide_link
    r = _fail(decide_link(user["id"], link_id, accept))
    await _tell(r["user_id"], "efnick_link_ok" if accept else "efnick_link_no")
    return {"status": "ok"}


# ---------------- skrinshotli natija ----------------

@router.post("/mshot/read")
async def mshot_read(image: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    from match_shot import read_shot
    return _fail(await read_shot(user["id"], _b64(image)))


@router.post("/mshot/apply")
async def mshot_apply(mode: str = Body(..., embed=True), match_id: int = Body(..., embed=True),
                      token: str = Body(..., embed=True), row: int = Body(..., embed=True),
                      expect_s1: int | None = Body(None, embed=True), expect_s2: int | None = Body(None, embed=True),
                      user: dict = Depends(get_authenticated_user)):
    """expect_s1/expect_s2 — qo'lda kiritilgan yirik hisob (chat_gate.py): skrinshot shu bilan bir xil bo'lsin."""
    from chat_agree import active_lock
    from chat_rules import fmt_local
    from match_shot import _NICK_REMIND, DISPUTE_HOURS, apply_shot
    lk = active_lock(mode, match_id)                   # 2026-11-07: kelishilgan vaqtgacha natija yo'q
    if lk:
        raise HTTPException(status_code=400, detail=f"agree_locked|{fmt_local(lk)}")
    expect = (int(expect_s1), int(expect_s2)) if expect_s1 is not None and expect_s2 is not None else None
    ok, r = await apply_shot(user, mode, match_id, token, row, expect)
    for uid in list(_NICK_REMIND):                     # raqib niknameini kiritmagan — unga eslatma (bir marta)
        _NICK_REMIND.discard(uid)
        if uid not in _NICK_REMINDED:
            _NICK_REMINDED.add(uid)
            await _tell(uid, "mshot_notify_set_nick")
    r = _fail((ok, r))
    if r["admin_pending"]:
        await _tell_admins(mode, match_id, "mshot_admin_pending", score=f"{r['score1']}:{r['score2']}")
    elif r.get("await_opp"):
        await _tell(r["opponent"]["id"], "mshot_notify_await", score=f"{r['their']}:{r['my']}", nick=r["opp_nick"])
        return {"status": "await_opp", "score1": r["score1"], "score2": r["score2"]}
    else:
        await _tell(r["opponent"]["id"], "mshot_notify_applied", score=f"{r['their']}:{r['my']}", hours=DISPUTE_HOURS)
    return {"status": "admin_pending" if r["admin_pending"] else "ok", "score1": r["score1"], "score2": r["score2"]}


@router.get("/mshot/incoming")
def mshot_incoming(user: dict = Depends(get_authenticated_user)):
    from match_shot_user import incoming
    return {"items": incoming(user["id"])}


@router.post("/mshot/{shot_id}/dispute")
async def mshot_dispute(shot_id: int, user: dict = Depends(get_authenticated_user)):
    from match_shot_user import dispute
    r = _fail(dispute(user["id"], shot_id))
    await _tell_admins(r["mode"], r["match_id"], "mshot_admin_dispute", score=f"{r['score1']}:{r['score2']}")
    return {"status": "ok"}


@router.post("/mshot/{shot_id}/accept")
async def mshot_accept(shot_id: int, nick: str = Body(..., embed=True), user: dict = Depends(get_authenticated_user)):
    """Raqib niknamesi yo'q edi: «bu mening niknamem» → niknamesi saqlanadi, natija tasdiqlanadi."""
    from match_shot_await import accept_await
    r = _fail(await accept_await(user, shot_id, nick))
    await _tell(r["uploader_id"], "mshot_notify_await_ok", score=f"{r['score1']}:{r['score2']}")
    return {"status": "ok"}


@router.post("/mshot/{shot_id}/reject")
async def mshot_reject(shot_id: int, user: dict = Depends(get_authenticated_user)):
    from match_shot_await import reject_await
    r = _fail(await reject_await(user, shot_id))
    await _tell_admins(r["mode"], r["match_id"], "mshot_admin_dispute", score=f"{r['score1']}:{r['score2']}")
    return {"status": "ok"}


@router.post("/mshot/tech")
async def mshot_tech(mode: str = Body(..., embed=True), match_id: int = Body(..., embed=True),
                     images: list[str] = Body(..., embed=True), note: str = Body("", embed=True),
                     user: dict = Depends(get_authenticated_user)):
    from match_claims import CLAIM_MAX_IMAGES, create_claim
    raws = [_b64(i) for i in (images or [])[:CLAIM_MAX_IMAGES]]
    r = _fail(create_claim(user["id"], mode, match_id, raws, note))
    await _tell_admins(mode, match_id, "mshot_admin_tech")
    await _tell(r["opponent_id"], "mshot_notify_tech_claim")
    return {"status": "ok", "id": r["id"]}


# ---------------- admin ----------------
# 2026-11-06: bosh admin + tayinlangan liga / rejim adminlari (har kim faqat o'zinikini ko'radi — can_review)

def get_any_admin(x_telegram_init_data: str = Header(...)) -> dict:
    from admin_roles import VALID_SCOPES, is_scope_admin, is_super_admin
    from api import get_or_create_user, verify_telegram_init_data
    tg = verify_telegram_init_data(x_telegram_init_data)
    tid = tg["id"]
    if not (is_super_admin(tid) or any(is_scope_admin(tid, sc) for sc in VALID_SCOPES)):
        raise HTTPException(status_code=403, detail="not_admin")
    u = get_or_create_user(tid, tg.get("first_name", f"user_{tid}"), tg.get("username"))
    return {**u, "telegram_id": tid}


@router.get("/mshot/admin/list")
def mshot_admin_list(modes: str = "", admin: dict = Depends(get_any_admin)):
    """modes — vergul bilan (masalan «cl,cl_po»): rejimning o'z Admin bo'limi uchun; bo'sh — hammasi."""
    from match_claims import admin_list
    want = {m for m in modes.split(",") if m}
    items = admin_list(admin["telegram_id"])
    return {"items": [i for i in items if not want or i["mode"] in want]}


@router.get("/mshot/admin/img/{kind}/{item_id}/{idx}")
def mshot_admin_img(kind: str, item_id: int, idx: int, admin: dict = Depends(get_any_admin)):
    from match_claims import admin_list, claim_image
    from match_shot_user import shot_image
    if not any(i["kind"] == kind and i["id"] == item_id for i in admin_list(admin["telegram_id"])):
        raise HTTPException(status_code=404, detail="not_found")
    img = shot_image(item_id) if kind == "shot" else claim_image(item_id, idx)
    if not img:
        raise HTTPException(status_code=404, detail="not_found")
    return {"data": "data:image/jpeg;base64," + base64.b64encode(img).decode()}


@router.post("/mshot/admin/decide")
async def mshot_admin_decide(kind: str = Body(..., embed=True), id: int = Body(..., embed=True),
                             action: str = Body(..., embed=True), s1: int | None = Body(None, embed=True),
                             s2: int | None = Body(None, embed=True), admin: dict = Depends(get_any_admin)):
    from match_claims import decide
    r = _fail(decide(admin, kind, id, action, s1, s2))
    it = r["item"]
    if kind == "tech":
        key = "mshot_notify_tech_ok" if r["result"] == "tech_win" else "mshot_notify_tech_no"
        await _tell(it["claimant_id"], key)
        if r["result"] == "tech_win":
            await _tell(it["opponent_id"], "mshot_notify_tech_lost")
    elif r["result"] == "fixed":
        for uid in (it["uploader_id"], it["opponent_id"]):
            await _tell(uid, "mshot_notify_fixed", score=f"{r['score'][0]}:{r['score'][1]}")
    return {"status": "ok", "result": r["result"]}


# ---------------- «natija faqat skrinshot bilan» kaliti (match_guard.py) ----------------

@router.get("/mshot/config")
def mshot_config(user: dict = Depends(get_authenticated_user)):
    from match_guard import shot_only
    return {"shot_only": shot_only()}


@router.post("/mshot/admin/only")
def mshot_admin_only(on: bool = Body(..., embed=True), admin: dict = Depends(get_authenticated_super_admin)):
    from match_guard import set_shot_only
    return {"shot_only": set_shot_only(on)}
