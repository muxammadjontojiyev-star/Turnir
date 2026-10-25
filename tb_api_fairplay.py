"""
tb_api_fairplay.py — "TEAMLAR JANGI": «Boshqa odam o'ynadi» shikoyati endpointlari (2026-10-25, 4-bosqich).
Mantiq: tb_fairplay.py. Shikoyat — faqat o'yin ishtirokchisi; ko'rib chiqish — shu liga admini
yoki bosh admin (tb_api.require_manage, qoida #34). Bot xabarlari yiqilsa ham amal saqlanadi (qoida #37).
api.py da include_router qilinadi.
"""

import logging

from fastapi import APIRouter, Body, Depends

from api import get_authenticated_user
from tb_api import _fail, _ok, require_manage

logger = logging.getLogger(__name__)
router = APIRouter()


def _who(username: str | None, nick: str | None) -> str:
    return "@" + username if username else (nick or "—")


async def _send(telegram_id: int, language: str | None, key: str, **fmt) -> None:
    try:
        from notify import notify_user
        await notify_user(telegram_id, key, language, open_button_key="btn_open_app", **fmt)
    except Exception as exc:
        logger.warning("TB shikoyat: xabar yuborilmadi (%s): %s", key, exc)


@router.post("/tb/report")
async def tb_report(game_id: int = Body(..., embed=True), note: str | None = Body(None, embed=True),
                    user: dict = Depends(get_authenticated_user)):
    from tb_fairplay import tb_report_create, tb_report_get
    from tb_leagues import tb_league, tb_league_admin_contact
    res = _ok(tb_report_create(user["id"], game_id, note))
    rep = tb_report_get(res["report_id"])
    adm = tb_league_admin_contact(rep["league_id"]) if rep else None
    if adm:
        lg = tb_league(rep["league_id"]) or {}
        await _send(adm["telegram_id"], adm["language"], "tb_notify_report",
                    league=lg.get("name", ""), round=rep["round"], game=rep["game_id"],
                    reporter=_who(rep["reporter_username"], rep["reporter_nick"]),
                    accused=_who(rep["accused_username"], rep["accused_nick"]))
    return res


@router.get("/tb/admin/reports")
def tb_admin_reports(league_id: int, status: str = "open", admin: dict = Depends(get_authenticated_user)):
    from tb_fairplay import REPORT_OPEN, tb_reports_list
    require_manage(admin, league_id)
    return {"reports": tb_reports_list(league_id, REPORT_OPEN if status == "open" else None)}


@router.post("/tb/admin/report/resolve")
async def tb_admin_report_resolve(report_id: int = Body(..., embed=True), decision: str = Body(..., embed=True),
                                  admin: dict = Depends(get_authenticated_user)):
    from texts import t
    from tb_fairplay import tb_report_get, tb_report_resolve
    rep = tb_report_get(report_id)
    if not rep:
        _fail("report_not_found", 404)
    require_manage(admin, rep["league_id"])
    res = _ok(tb_report_resolve(report_id, decision, admin["id"]))
    try:
        from models import get_connection
        conn = get_connection()
        try:
            r = conn.cursor().execute("SELECT telegram_id, language FROM users WHERE id = ?",
                                      (res["reporter_id"],)).fetchone()
        finally:
            conn.close()
        if r:
            await _send(r["telegram_id"], r["language"], "tb_notify_report_done", game=res["game_id"],
                        decision=t(f"tb_report_dec_{decision}", r["language"]))
    except Exception as exc:
        logger.warning("TB shikoyat: shikoyatchiga xabar yuborilmadi: %s", exc)
    return res
