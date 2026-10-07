"""
pt_results.py — SHAXSIY turnir guruh o'yinlari: ko'rinish, natija, jadval (4-bosqich).

Natija oqimi (rasmiy turnirlar kabi): pending -> (o'yinchi kiritadi) awaiting_confirmation
-> (raqib tasdiqlaydi) confirmed | (raqib rad etadi) pending.
Faqat JORIY turning o'yinlari kiritiladi (server tekshiruvi — qoida #41).
2026-10-07: katta hisob (MAX_NORMAL_SCORE dan ko'p) -> admin_pending — tashkilotchi/turnir admini
(o'yinda o'ynamayotgan) yoki bosh admin tasdiqlaydi (pt_bigscore.py).
Jadval: ochko (3/1/0) > gol farqi > urilgan gol; ppg — o'yin boshiga ochko
(turli o'lchamdagi guruhlarni solishtirish uchun, 5-bosqich).
"""

import logging

from models import get_connection
from pt_rounds import utc_to_local_text

logger = logging.getLogger(__name__)

_MATCH_COLS = ("m.id, m.stage, m.group_label, m.round, m.leg, m.player1_id, m.player2_id, m.score1, m.score2, "
               "m.status, m.submitted_by, u1.nickname AS p1_name, u1.username AS p1_username, "
               "u2.nickname AS p2_name, u2.username AS p2_username, "
               "pm1.team_name AS p1_team, pm2.team_name AS p2_team")
# 2026-10-07: o'yinchilar klubi/terma jamoasi (jamoali formatlar) — pt_members'dan
_MATCH_FROM = ("FROM pt_matches m LEFT JOIN users u1 ON u1.id = m.player1_id "
               "LEFT JOIN users u2 ON u2.id = m.player2_id "
               "LEFT JOIN pt_members pm1 ON pm1.tournament_id = m.tournament_id AND pm1.user_id = m.player1_id "
               "LEFT JOIN pt_members pm2 ON pm2.tournament_id = m.tournament_id AND pm2.user_id = m.player2_id ")


def _empty_row(uid: int, nick: str, username: str | None, team: str | None = None) -> dict:
    return {"user_id": uid, "nickname": nick, "username": username, "team_name": team, "played": 0, "wins": 0,
            "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0}


def _apply(row: dict, gf: int, ga: int) -> None:
    row["played"] += 1
    row["goals_for"] += gf
    row["goals_against"] += ga
    if gf > ga:
        row["wins"] += 1
        row["points"] += 3
    elif gf == ga:
        row["draws"] += 1
        row["points"] += 1
    else:
        row["losses"] += 1


def pt_group_standings(cursor, tid: int) -> dict[str, list[dict]]:
    """{'A': [qatorlar tartiblangan], ...} — faqat confirmed guruh o'yinlari."""
    cursor.execute(
        "SELECT m.user_id, m.group_label, m.team_name, u.nickname, u.username FROM pt_members m "
        "JOIN users u ON u.id = m.user_id WHERE m.tournament_id = ? AND m.status = 'approved' "
        "AND m.group_label IS NOT NULL", (tid,))
    rows: dict[int, dict] = {}
    groups: dict[str, list[dict]] = {}
    for r in cursor.fetchall():
        row = _empty_row(r["user_id"], r["nickname"], r["username"], r["team_name"])
        rows[r["user_id"]] = row
        groups.setdefault(r["group_label"], []).append(row)
    cursor.execute(
        "SELECT player1_id, player2_id, score1, score2 FROM pt_matches WHERE tournament_id = ? "
        "AND stage = 'group' AND status = 'confirmed'", (tid,))
    for m in cursor.fetchall():
        if m["player1_id"] in rows:
            _apply(rows[m["player1_id"]], m["score1"], m["score2"])
        if m["player2_id"] in rows:
            _apply(rows[m["player2_id"]], m["score2"], m["score1"])
    for g in groups.values():
        for row in g:
            row["goal_diff"] = row["goals_for"] - row["goals_against"]
            row["ppg"] = round(row["points"] / row["played"], 3) if row["played"] else 0.0
        g.sort(key=lambda x: (x["points"], x["goal_diff"], x["goals_for"]), reverse=True)
    return dict(sorted(groups.items()))


def _ordered(standings: dict, order: list[str]) -> list:
    """Liga jadvallari tanlash tartibida (qolganlari oxirida)."""
    return sorted(standings.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else len(order))


def pt_get_play(tid: int, user_id: int, is_super: bool = False) -> dict | None:
    """O'yin ko'rinishi: tur, muddat, guruh jadvallari, mening o'yinlarim, joriy tur o'yinlari."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, owner_user_id, status, current_round, total_rounds, round_deadline, "
                       "format, league_name, legs FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        if not t:
            return None
        cursor.execute("SELECT 1 FROM pt_members WHERE tournament_id = ? AND user_id = ? "
                       "AND status = 'approved'", (tid, user_id))
        is_member = cursor.fetchone() is not None
        from pt_core import is_manager
        manager = is_manager(cursor, tid, user_id, t["owner_user_id"])
        if not (is_member or manager or is_super):
            return None
        cursor.execute(
            f"SELECT {_MATCH_COLS} {_MATCH_FROM}WHERE m.tournament_id = ? "
            "ORDER BY m.round, m.group_label, m.id", (tid,))
        matches = [dict(r) for r in cursor.fetchall()]
        standings = pt_group_standings(cursor, tid)
        from pt_knockout import pt_knockout_phase
        phase = pt_knockout_phase(cursor, tid)
        cursor.execute("SELECT u.id, u.nickname, u.username, pm.team_name FROM pt_tournaments t JOIN users u "
                       "ON u.id = t.champion_user_id LEFT JOIN pt_members pm ON pm.tournament_id = t.id "
                       "AND pm.user_id = u.id WHERE t.id = ?", (tid,))
        ch = cursor.fetchone()
    finally:
        conn.close()
    cur = t["current_round"]
    fmt = t["format"] or "classic"
    from config import MAX_NORMAL_SCORE
    for x in matches:                                    # 2026-10-07: katta hisob — kim qaror qila oladi
        if x["status"] == "admin_pending":
            x["can_decide"] = bool(is_super or (manager and user_id not in (x["player1_id"], x["player2_id"])))
    n_players = sum(len(r) for r in standings.values())
    from pt_formats import cl_direct_count, is_single_table, split_leagues
    from pt_knockout import STAGES, pt_bracket_size
    _order = {"group": 0, **{s: i + 1 for i, s in enumerate(STAGES)}}
    matches.sort(key=lambda m: (_order.get(m["stage"], 9), m["round"] or 0, m["group_label"] or "", m["leg"] or 1, m["id"]))
    return {
        "status": t["status"], "current_round": cur, "total_rounds": t["total_rounds"],
        "groups_finished": cur > t["total_rounds"] > 0,
        "deadline_local": utc_to_local_text(t["round_deadline"]),
        "is_owner": t["owner_user_id"] == user_id, "is_manager": manager, "me_id": user_id,
        "standings": standings,
        "my_matches": [m for m in matches if user_id in (m["player1_id"], m["player2_id"])],
        "round_matches": [m for m in matches if m["stage"] == "group" and m["round"] == cur],
        # 5-bosqich: pley-off
        "phase": phase,                     # None | ko_ready | r64..final (joriy bosqich) | finished
        "bracket_size": pt_bracket_size(fmt, standings),
        # 2026-10-07: format (yagona jadval — liga/ChL/YeL), ChL/YeL zonalari: top-Q setka, Q+1..3Q pley-off raundi
        "max_normal_score": MAX_NORMAL_SCORE,
        "big_pending": [x for x in matches if x["status"] == "admin_pending" and x.get("can_decide")],
        "format": fmt, "league_name": t["league_name"], "legs": t["legs"], "single_table": is_single_table(fmt),
        "direct_count": cl_direct_count(n_players) if fmt in ("cl", "el") else None,
        # 2026-10-07: ko'p ligali turnir — har liga chempioni (jadval birinchisi), tanlash tartibida
        "leagues": split_leagues(t["league_name"]) if fmt == "league" else [],
        "champions": [{"league": g, "user_id": rows[0]["user_id"], "nickname": rows[0]["nickname"],
                       "username": rows[0]["username"], "team_name": rows[0]["team_name"]}
                      for g, rows in _ordered(standings, split_leagues(t["league_name"])) if rows]
                     if fmt == "league" and t["status"] == "finished" else [],
        "knockout": [m for m in matches if m["stage"] != "group"],
        "champion": dict(ch) if ch else None,
    }


def _match_for_update(cursor, match_id: int):
    cursor.execute(
        "SELECT m.id, m.tournament_id, m.stage, m.round, m.player1_id, m.player2_id, m.status, "
        "m.submitted_by, t.status AS t_status, t.current_round FROM pt_matches m "
        "JOIN pt_tournaments t ON t.id = m.tournament_id WHERE m.id = ?", (match_id,))
    r = cursor.fetchone()
    return dict(r) if r else None


def _tx(fn):
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        ok, result = fn(cursor)
        cursor.execute("COMMIT" if ok else "ROLLBACK")
        return ok, result
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_results: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def pt_submit_result(match_id: int, user_id: int, score1: int, score2: int) -> tuple[bool, str | dict]:
    """Sabablar: match_not_found, not_participant, not_running, round_closed, already_submitted."""
    def run(cursor):
        m = _match_for_update(cursor, match_id)
        if not m:
            return False, "match_not_found"
        if user_id not in (m["player1_id"], m["player2_id"]):
            return False, "not_participant"
        if m["t_status"] != "running":
            return False, "not_running"
        if m["stage"] == "group" and m["round"] != m["current_round"]:
            return False, "round_closed"
        if m["stage"] != "group":                            # pley-off: durang yo'q; javob o'yinida — yig'indi
            from pt_legs import ko_draw_check
            why = ko_draw_check(cursor, m, score1, score2)
            if why:
                return False, why
        # 2026-10-07: katta hisob (rasmiy turnirlar kabi, MAX_NORMAL_SCORE) — admin tasdig'iga (pt_bigscore)
        from pt_bigscore import STATUS_ADMIN_PENDING, deciders, is_big_score
        big = is_big_score(score1, score2)
        cursor.execute(
            "UPDATE pt_matches SET score1 = ?, score2 = ?, submitted_by = ?, status = ? "
            "WHERE id = ? AND status = 'pending'",
            (score1, score2, user_id, STATUS_ADMIN_PENDING if big else "awaiting_confirmation", match_id))
        if cursor.rowcount != 1:
            return False, "already_submitted"
        opp = m["player2_id"] if m["player1_id"] == user_id else m["player1_id"]
        cursor.execute("SELECT telegram_id, language FROM users WHERE id = ?", (opp,))
        o = cursor.fetchone()
        cursor.execute("SELECT name FROM pt_tournaments WHERE id = ?", (m["tournament_id"],))
        name = cursor.fetchone()["name"]
        return True, {"opponent": dict(o) if o else None, "admin_pending": big, "name": name,
                      "deciders": deciders(cursor, m["tournament_id"], m["player1_id"], m["player2_id"]) if big else [],
                      "score": f"{score1}:{score2}"}
    return _tx(run)


def pt_confirm_result(match_id: int, user_id: int, accept: bool) -> tuple[bool, str | dict]:
    """
    Raqib tasdiqlaydi/rad etadi. Sabablar: match_not_found, not_opponent, wrong_status.
    Qaytaradi (ok): {"status": confirmed|rejected, "advance": pt_advance natijasi, "tournament_id"}.
    """
    def run(cursor):
        m = _match_for_update(cursor, match_id)
        if not m:
            return False, "match_not_found"
        if user_id not in (m["player1_id"], m["player2_id"]) or user_id == m["submitted_by"]:
            return False, "not_opponent"
        if accept:
            cursor.execute("UPDATE pt_matches SET status = 'confirmed' WHERE id = ? "
                           "AND status = 'awaiting_confirmation'", (match_id,))
        else:
            cursor.execute("UPDATE pt_matches SET status = 'pending', score1 = NULL, score2 = NULL, "
                           "submitted_by = NULL WHERE id = ? AND status = 'awaiting_confirmation'", (match_id,))
        if cursor.rowcount != 1:
            return False, "wrong_status"
        advance = {"event": None}
        if accept and m["stage"] != "group":
            from pt_knockout import pt_advance          # sikl importdan qochish (pt_knockout -> pt_results)
            advance = pt_advance(cursor, m["tournament_id"])
        return True, {"status": "confirmed" if accept else "rejected", "advance": advance,
                      "tournament_id": m["tournament_id"]}
    return _tx(run)


def pt_get_player(tid: int, viewer_id: int, target_id: int, is_super: bool = False) -> tuple[bool, str | dict]:
    """
    2026-10-04: ishtirokchining turnir profili (Reytingdan bosilganda).
    Ruxsat: ko'ruvchi — a'zo / tashkilotchi / admin / bosh admin (qoida #34).
    Qaytaradi: {user, group, position, row, matches (barcha bosqichlar), status, current_round}.
    Sabablar: not_found (turnir yo'q yoki ruxsat yo'q), player_not_found.
    """
    from pt_core import is_manager
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT owner_user_id, status, current_round FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        if not t:
            return False, "not_found"
        cursor.execute("SELECT 1 FROM pt_members WHERE tournament_id = ? AND user_id = ? AND status = 'approved'",
                       (tid, viewer_id))
        if not (cursor.fetchone() or is_manager(cursor, tid, viewer_id, t["owner_user_id"]) or is_super):
            return False, "not_found"
        cursor.execute("SELECT u.id, u.nickname, u.username, m.group_label, m.team_name FROM pt_members m "
                       "JOIN users u ON u.id = m.user_id WHERE m.tournament_id = ? AND m.user_id = ? "
                       "AND m.status = 'approved'", (tid, target_id))
        u = cursor.fetchone()
        if not u:
            return False, "player_not_found"
        cursor.execute(
            f"SELECT {_MATCH_COLS} {_MATCH_FROM}WHERE m.tournament_id = ? "
            "AND (m.player1_id = ? OR m.player2_id = ?)", (tid, target_id, target_id))
        matches = [dict(r) for r in cursor.fetchall()]
        standings = pt_group_standings(cursor, tid)
    finally:
        conn.close()
    from pt_knockout import STAGES
    order = {"group": 0, **{s: i + 1 for i, s in enumerate(STAGES)}}
    matches.sort(key=lambda m: (order.get(m["stage"], 9), m["round"] or 0, m["leg"] or 1, m["id"]))
    group, pos, row = u["group_label"], None, None
    for i, r in enumerate(standings.get(group, []), start=1):
        if r["user_id"] == target_id:
            pos, row = i, r
            break
    return True, {"user": {"id": u["id"], "nickname": u["nickname"], "username": u["username"],
                           "team_name": u["team_name"]},
                  "group": group, "position": pos, "row": row, "matches": matches,
                  "status": t["status"], "current_round": t["current_round"]}
