"""
wc_playoff_qualify.py — JCh play-off setkasi guruh natijalariga MOSmi (2026-10-14).

Muammo: Australia guruhda 4-o'rinda, lekin setkada turibdi. Sabab: play-off
boshlanganda guruhda hali tasdiqlanmagan o'yin(lar) bo'lgan (wc_get_qualified_teams
faqat 4 jamoa borligini tekshirardi) — setka o'sha paytdagi jadval bo'yicha tuzilgan,
keyin natija tasdiqlanib o'rinlar o'zgargan.

  wc_playoff_qualify_diff() — hozirgi guruh jadvallari bo'yicha play-off'ga chiqishi
      KERAK bo'lgan 32 jamoa bilan setkadagi (1/16) 32 ishtirokchini solishtiradi:
        wrong   — setkada bor, lekin chiqmasligi kerak (guruhdagi o'rni bilan);
        missing — chiqishi kerak, lekin setkada yo'q.
  wc_playoff_qualify_fix() — har "wrong"ni o'z 1/16 o'rnida "missing" bilan
      almashtiradi (faqat natija kiritilmagan 1/16 o'yinlarida; aks holda to'xtaydi).

Faqat bosh admin (api endpointlari). Guruh o'yinlari (wc_matches) TEGILMAYDI.
"""

import logging

from config import MATCH_STATUS_PENDING
from models import get_connection
from wc_data import WC_GROUP_LETTERS
from wc_playoff import wc_get_qualified_teams
from wc_rating import calculate_wc_group_rating

logger = logging.getLogger(__name__)

_SLOT_COL = {1: "player1_id", 2: "player2_id"}


def _group_positions() -> dict[int, dict]:
    """user_id -> {group_letter, position, team_name, username, nickname, points}."""
    out = {}
    for letter in WC_GROUP_LETTERS:
        for pos, t in enumerate(calculate_wc_group_rating(letter), start=1):
            out[t["user_id"]] = {
                "user_id": t["user_id"], "group_letter": letter, "position": pos,
                "team_name": t["team_name"], "username": t["username"],
                "nickname": t["nickname"], "points": t["points"],
            }
    return out


def _r32_slots(cursor) -> list[dict]:
    cursor.execute(
        "SELECT id, position, player1_id, player2_id, score1, score2, status "
        "FROM wc_playoff_matches WHERE round = 'r32' ORDER BY position"
    )
    slots = []
    for m in cursor.fetchall():
        played = m["status"] != MATCH_STATUS_PENDING or m["score1"] is not None or m["score2"] is not None
        for slot, col in _SLOT_COL.items():
            if m[col]:
                other = m[_SLOT_COL[3 - slot]]
                slots.append({"match_id": m["id"], "match_position": m["position"], "slot": slot,
                              "user_id": m[col], "opponent_id": other, "played": played})
    return slots


def wc_playoff_qualify_diff() -> dict:
    """
    Qaytaradi: {started, ok, wrong: [...], missing: [...]}
      wrong:   {user_id, team_name, group_letter, position, match_id, slot, played, ...}
      missing: {user_id, team_name, group_letter, position, kind: winner|runner_up|third}
    """
    q = wc_get_qualified_teams()
    conn = get_connection()
    try:
        slots = _r32_slots(conn.cursor())
    finally:
        conn.close()
    if not slots:
        return {"started": False, "ok": True, "wrong": [], "missing": []}

    if not q["ready"]:
        return {"started": True, "ok": False, "groups_ready": False,
                "reason": q["reason"], "wrong": [], "missing": []}
    groups = _group_positions()
    should = {}
    for kind, key in (("winner", "winners"), ("runner_up", "runners_up"), ("third", "best_thirds")):
        for t in q.get(key, []):
            should[t["user_id"]] = kind
    in_bracket = {s["user_id"]: s for s in slots}

    wrong = [dict(groups.get(uid, {"user_id": uid}), **s)
             for uid, s in in_bracket.items() if uid not in should]
    # Kuchsizroq (guruhda pastroq) birinchi
    wrong.sort(key=lambda w: (-(w.get("position") or 9), w.get("points") or 0))
    kind_order = {"winner": 0, "runner_up": 1, "third": 2}
    missing = [dict(groups.get(uid, {"user_id": uid}), kind=kind)
               for uid, kind in should.items() if uid not in in_bracket]
    missing.sort(key=lambda m: (kind_order[m["kind"]], -(m.get("points") or 0)))
    return {"started": True, "ok": not wrong and not missing,
            "groups_ready": q["ready"], "wrong": wrong, "missing": missing}


def wc_playoff_qualify_fix() -> tuple[bool, str | dict]:
    """
    Har "wrong" o'rniga (o'sha 1/16 o'yin va slot) navbatdagi "missing" qo'yiladi.
    Sabablar: not_started / nothing_to_fix / groups_not_ready / count_mismatch / has_result.
    """
    d = wc_playoff_qualify_diff()
    if not d["started"]:
        return False, "not_started"
    if d["ok"]:
        return False, "nothing_to_fix"
    if not d["groups_ready"]:
        return False, "groups_not_ready"
    if len(d["wrong"]) != len(d["missing"]):
        return False, "count_mismatch"
    if any(w["played"] for w in d["wrong"]):
        return False, "has_result"

    conn = get_connection()
    cur = conn.cursor()
    changes = []
    try:
        for w, m in zip(d["wrong"], d["missing"]):
            col = _SLOT_COL[w["slot"]]
            cur.execute(
                f"UPDATE wc_playoff_matches SET {col} = ? WHERE id = ? AND {col} = ? "  # nosec — ustun nomi kod ichida qat'iy
                "AND status = ? AND score1 IS NULL AND score2 IS NULL",
                (m["user_id"], w["match_id"], w["user_id"], MATCH_STATUS_PENDING),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return False, "has_result"
            changes.append({"match_id": w["match_id"], "slot": w["slot"],
                            "out": w.get("team_name"), "in": m.get("team_name"),
                            "same_group_opponent": w.get("opponent_id") is not None and
                            _same_group(m["user_id"], w["opponent_id"])})
        conn.commit()
    finally:
        conn.close()
    logger.info("JCh play-off setkasi tuzatildi: %s", changes)
    return True, {"changes": changes}


def _same_group(user_a: int, user_b: int) -> bool:
    g = _group_positions()
    return bool(g.get(user_a) and g.get(user_b) and g[user_a]["group_letter"] == g[user_b]["group_letter"])
