"""
match_modes.py — BARCHA REJIMLAR uchun yagona o'yin adapteri (2026-11-06, match_shot.py / match_claims.py).

Har rejim uchun:
  * table, scope — o'yin jadvali va admin scope'i (admin_roles);
  * submit / confirm — rejimning O'ZINING endpoint funksiyasi chaqiriladi (barcha tekshiruvlar, deadline,
    pley-off o'tishi, xabarlar — odatdagidek ishlaydi): skrinshotli natija = yuklagan kiritadi + raqib
    nomidan tasdiqlanadi;
  * force — admin natijasi (texnik g'alaba / e'tirozni hal qilish) — rejimning admin funksiyasi.
Tezkor o'yin (qm) va Jamoaviy bahs (tb) kiritilmagan: ularda o'z isbot tizimi bor.
"""

import inspect
import logging

from fastapi import HTTPException

from models import get_connection

logger = logging.getLogger(__name__)


def _league_force(mid, s1, s2):
    from queries_matches import admin_fix_confirmed_match, get_match_by_id
    m = get_match_by_id(mid)
    if m is None:
        return False, "match_not_found"
    if m["status"] == "confirmed":
        return admin_fix_confirmed_match(mid, s1, s2)
    conn = get_connection()
    try:
        conn.execute("UPDATE matches SET score1 = ?, score2 = ?, status = 'confirmed' WHERE id = ?", (s1, s2, mid))
        conn.commit()
    finally:
        conn.close()
    return True, "ok"


def _pt_force(mid, s1, s2):
    from pt_owner_fix import pt_owner_set_result
    conn = get_connection()
    try:
        r = conn.execute("SELECT t.owner_user_id FROM pt_matches m JOIN pt_tournaments t ON t.id = m.tournament_id "
                         "WHERE m.id = ?", (mid,)).fetchone()
    finally:
        conn.close()
    if not r:
        return False, "match_not_found"
    ok, res = pt_owner_set_result(mid, r["owner_user_id"], s1, s2)
    return ok, (res if isinstance(res, str) else "ok")


def _fn(module: str, name: str):
    def get():
        return getattr(__import__(module, fromlist=[name]), name)
    return get


# kind: confirm funksiyasi argumenti — "action" (action="confirm") yoki "accept" (accept=True)
MODES: dict[str, dict] = {
    "league": {"table": "matches", "scope": "league", "playoff": False,
               "submit": _fn("api", "submit_result"), "confirm": _fn("api", "confirm_result"), "kind": "action",
               "force": lambda: _league_force},
    "wc": {"table": "wc_matches", "scope": "wc", "playoff": False,
           "submit": _fn("api", "wc_submit_result"), "confirm": _fn("api", "wc_confirm"), "kind": "action",
           "force": lambda: (lambda m, a, b: __import__("queries_wc_admin").wc_admin_set_score(m, a, b, 0))},
    "wc_po": {"table": "wc_playoff_matches", "scope": "wc", "playoff": True,
              "submit": _fn("api", "wc_playoff_submit"), "confirm": _fn("api", "wc_playoff_confirm"), "kind": "accept",
              "force": lambda: (lambda m, a, b: __import__("queries_wc_admin").wc_admin_set_score(m, a, b, 1))},
    "cl": {"table": "cl_matches", "scope": "cl", "playoff": False,
           "submit": _fn("api", "cl_submit"), "confirm": _fn("api", "cl_confirm"), "kind": "accept",
           "force": _fn("cl_admin_fix", "cl_admin_set_result")},
    "cl_po": {"table": "cl_playoff_matches", "scope": "cl", "playoff": True,
              "submit": _fn("api", "cl_playoff_submit"), "confirm": _fn("api", "cl_playoff_confirm"), "kind": "accept",
              "force": _fn("cl_admin_fix", "cl_admin_po_set_result")},
    "div": {"table": "div_matches", "scope": "division", "playoff": False,
            "submit": _fn("api", "div_submit_endpoint"), "confirm": _fn("api", "div_confirm_endpoint"), "kind": "accept",
            "force": _fn("division", "div_admin_set_result")},
    "pt": {"table": "pt_matches", "scope": None, "playoff": False,
           "submit": _fn("pt_api_play", "pt_match_result"), "confirm": _fn("pt_api_play", "pt_match_confirm"),
           "kind": "accept", "force": lambda: _pt_force},
}
for _p in ("el", "ac", "co"):
    MODES[_p] = {"table": f"{_p}_matches", "scope": _p, "playoff": False,
                 "submit": _fn(f"{_p}_api", f"{_p}_submit"), "confirm": _fn(f"{_p}_api", f"{_p}_confirm"), "kind": "accept",
                 "force": _fn(f"{_p}_admin_fix", f"{_p}_admin_set_result")}
    MODES[f"{_p}_po"] = {"table": f"{_p}_playoff_matches", "scope": _p, "playoff": True,
                         "submit": _fn(f"{_p}_api_playoff", f"{_p}_playoff_submit"),
                         "confirm": _fn(f"{_p}_api_playoff", f"{_p}_playoff_confirm"), "kind": "accept",
                         "force": _fn(f"{_p}_admin_fix", f"{_p}_admin_po_set_result")}


def get_match(mode: str, match_id: int) -> dict | None:
    """{id, player1_id, player2_id, score1, score2, status, submitted_by, created_at?, league_id?, stage?}"""
    cfg = MODES.get(mode)
    if not cfg:
        return None
    conn = get_connection()
    try:
        r = conn.execute(f"SELECT * FROM {cfg['table']} WHERE id = ?", (int(match_id),)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


async def _call(fn, **kw):
    try:
        res = fn(**kw)
        if inspect.isawaitable(res):
            res = await res
        return True, res
    except HTTPException as exc:
        return False, str(exc.detail)


async def submit_as(mode: str, match_id: int, s1: int, s2: int, user: dict):
    return await _call(MODES[mode]["submit"](), match_id=match_id, score1=s1, score2=s2, user=user)


async def confirm_as(mode: str, match_id: int, user: dict):
    cfg = MODES[mode]
    extra = {"action": "confirm"} if cfg["kind"] == "action" else {"accept": True}
    return await _call(cfg["confirm"](), match_id=match_id, user=user, **extra)


def force_set(mode: str, match_id: int, s1: int, s2: int) -> tuple[bool, str]:
    try:
        ok, why = MODES[mode]["force"]()(match_id, s1, s2)
    except Exception:
        logger.exception("MATCH MODES: force %s #%s", mode, match_id)
        return False, "force_failed"
    return bool(ok), str(why)


def reviewer_tgs(mode: str, match: dict) -> list[int]:
    """Xabar yuboriladigan adminlar: bosh adminlar + rejim (liga — o'sha liga) admini."""
    from config import ADMIN_TELEGRAM_IDS
    out = set(ADMIN_TELEGRAM_IDS)
    scope = MODES[mode]["scope"]
    if scope:
        from admin_roles import can_manage_league, list_admins
        for a in list_admins(scope):
            tg = a["telegram_id"]
            if scope != "league" or can_manage_league(tg, match.get("league_id")):
                out.add(tg)
    return sorted(out)


def can_review(telegram_id: int, mode: str, match: dict) -> bool:
    from admin_roles import can_manage_league, is_scope_admin, is_super_admin
    if is_super_admin(telegram_id):
        return True
    scope = MODES.get(mode, {}).get("scope")
    if not scope or not is_scope_admin(telegram_id, scope):
        return False
    return scope != "league" or can_manage_league(telegram_id, match.get("league_id"))
