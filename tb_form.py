"""
tb_form.py — "TEAMLAR JANGI": O'YINCHI BAHOSI (10 BALL), FORMA VA BAHS MVP (2026-11-07, egasi: «har bir teamda kim qanday
formada ekanligini ko'rsatuvchi bo'lim … 3 tadan ko'p gol urgan va umuman gol o'tkazmagan — 10 ball … haqiqiy futboldagi
10 balli tizimdagidek … o'sha o'yindagi MVP ni ham shu orqali aniqlaymiz»).

BAHO (har bir tasdiqlangan 1v1 o'yin, urgan gol = gf, o'tkazgan = ga):
  * gf ≥ PERFECT_GOALS (4) va ga = 0 → 10.0 (mukammal o'yin);
  * aks holda: BASE 6.0 + 0.5×gf − 0.5×ga + g'alaba +1.0 / mag'lubiyat −1.0 + quruq o'yin (ga = 0) +0.5,
    1.0..9.9 oralig'ida, 0.1 aniqlikda. Misollar: 3:0 → 9.0 · 1:0 → 8.0 · 2:1 → 7.5 · 0:0 → 6.5 · 2:2 → 6.0 ·
    0:1 → 4.5 · 1:3 → 4.0 · 0:4 → 3.0 · 0:8 → 1.0.
  * Texnik natija (admin «texnik mag'lubiyat» qarori, tb_reports.decision='tech') baholanmaydi.
FORMA: oxirgi FORM_LAST (5) baho o'rtachasi; bahs MVP — tugagan bahsdagi eng yuqori baho (teng bo'lsa — gol farqi,
so'ng urgan gol). Hisob har safar o'yinlardan olinadi (alohida jadval yo'q — natija tuzatilsa, baho ham o'zgaradi).
"""

from models import get_connection

BASE, PER_GOAL, PER_CONCEDED = 6.0, 0.5, 0.5
WIN_BONUS, LOSS_PENALTY, CLEAN_SHEET = 1.0, -1.0, 0.5
PERFECT_GOALS, RATING_MAX, RATING_CAP, RATING_MIN = 4, 10.0, 9.9, 1.0
FORM_LAST = 5
_NOT_TECH = "NOT EXISTS (SELECT 1 FROM tb_reports r WHERE r.game_id = g.id AND r.decision = 'tech')"


def game_rating(gf: int, ga: int) -> float:
    gf, ga = int(gf or 0), int(ga or 0)
    if gf >= PERFECT_GOALS and ga == 0:
        return RATING_MAX
    r = BASE + PER_GOAL * gf - PER_CONCEDED * ga
    r += WIN_BONUS if gf > ga else LOSS_PENALTY if gf < ga else 0
    if ga == 0:
        r += CLEAN_SHEET
    return round(max(RATING_MIN, min(RATING_CAP, r)), 1)


def _pick_mvp(cands: list[tuple]) -> tuple | None:
    """cands: [(rating, gf-ga, gf, -slot, user_id, name)] → eng yaxshisi."""
    return max(cands) if cands else None


def team_form(team_id: int) -> list[dict]:
    """Team a'zolari formasi: [{user_id, name, games, avg, form, last[], mvp, w, d, l, gf, ga}] — forma bo'yicha."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        members = cur.execute(
            "SELECT m.user_id, u.username, u.nickname FROM tb_members m JOIN users u ON u.id = m.user_id WHERE m.team_id = ?",
            (team_id,)).fetchall()
        rows = cur.execute(
            "SELECT g.id, g.fixture_id, g.slot, g.home_user_id, g.away_user_id, g.score1, g.score2, f.status AS fx_status, "
            "f.home_team_id, f.away_team_id FROM tb_games g JOIN tb_fixtures f ON f.id = g.fixture_id "
            f"WHERE g.status = 'confirmed' AND (f.home_team_id = ? OR f.away_team_id = ?) AND {_NOT_TECH} ORDER BY g.id",
            (team_id, team_id)).fetchall()
        fx_ids = sorted({r["fixture_id"] for r in rows if r["fx_status"] == "finished"})
        mvps = _fixture_mvp_users(cur, fx_ids)
    finally:
        conn.close()
    stats = {m["user_id"]: {"user_id": m["user_id"], "name": "@" + m["username"] if m["username"] else (m["nickname"] or "—"),
                            "ratings": [], "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0} for m in members}
    for r in rows:
        home = r["home_team_id"] == team_id
        uid = r["home_user_id"] if home else r["away_user_id"]
        if uid not in stats:
            continue                                    # endi teamda yo'q o'yinchi
        gf, ga = (r["score1"], r["score2"]) if home else (r["score2"], r["score1"])
        s = stats[uid]
        s["ratings"].append(game_rating(gf, ga))
        s["gf"] += int(gf or 0)
        s["ga"] += int(ga or 0)
        s["w" if gf > ga else "l" if gf < ga else "d"] += 1
    out = []
    for s in stats.values():
        rt = s.pop("ratings")
        last = rt[-FORM_LAST:]
        s.update({"games": len(rt), "avg": round(sum(rt) / len(rt), 1) if rt else None,
                  "form": round(sum(last) / len(last), 1) if last else None, "last": list(reversed(last)),
                  "mvp": sum(1 for v in mvps.values() if v == s["user_id"])})
        out.append(s)
    out.sort(key=lambda x: (x["form"] is None, -(x["form"] or 0), -x["games"]))
    return out


def _fixture_mvp_users(cur, fx_ids: list[int]) -> dict[int, int]:
    if not fx_ids:
        return {}
    marks = ",".join("?" * len(fx_ids))
    rows = cur.execute(f"SELECT g.id, g.fixture_id, g.slot, g.home_user_id, g.away_user_id, g.score1, g.score2 FROM tb_games g "
                       f"WHERE g.fixture_id IN ({marks}) AND g.status = 'confirmed' AND {_NOT_TECH}", tuple(fx_ids)).fetchall()
    by: dict[int, list] = {}
    for g in rows:
        a, b = int(g["score1"] or 0), int(g["score2"] or 0)
        by.setdefault(g["fixture_id"], []).extend([(game_rating(a, b), a - b, a, -g["slot"], g["home_user_id"], ""),
                                                   (game_rating(b, a), b - a, b, -g["slot"], g["away_user_id"], "")])
    return {fx: _pick_mvp(c)[4] for fx, c in by.items() if c}


def decorate_fixtures(fixtures: list[dict]) -> list[dict]:
    """tb_games.tb_round_fixtures natijasiga: har o'yinga r1/r2 (baho), tugagan bahsga mvp {name, rating, side}."""
    ids = [g["id"] for f in fixtures for g in f.get("games", [])]
    tech = set()
    if ids:
        conn = get_connection()
        try:
            marks = ",".join("?" * len(ids))
            tech = {r[0] for r in conn.execute(f"SELECT game_id FROM tb_reports WHERE decision = 'tech' AND game_id IN ({marks})",
                                               tuple(ids)).fetchall()}
        finally:
            conn.close()
    for f in fixtures:
        cands = []
        for g in f.get("games", []):
            if g.get("status") != "confirmed" or g["id"] in tech:
                continue
            a, b = int(g["score1"] or 0), int(g["score2"] or 0)
            g["r1"], g["r2"] = game_rating(a, b), game_rating(b, a)
            cands += [(g["r1"], a - b, a, -g["slot"], "home", g["home"]), (g["r2"], b - a, b, -g["slot"], "away", g["away"])]
        best = _pick_mvp(cands) if f.get("status") == "finished" else None
        f["mvp"] = {"name": best[5], "rating": best[0], "side": best[4]} if best else None
    return fixtures
