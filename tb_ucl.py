"""
tb_ucl.py — "TEAMLAR JANGI": UCL formati (2026-10-18).

Egasi qarorlari:
  * Format har mavsum qur'asida tanlanadi: 'league' (divizionlar, aylanma) yoki 'ucl'.
  * UCL — bizning ChL kabi: barcha teamlar BITTA umumiy jadvalda (division=1), har team
    ucl_rounds ta TASODIFIY raqib bilan o'ynaydi (takrorsiz), so'ng top ucl_qualify (2/4/8/16)
    pley-offga chiqadi: 1-o'rin — oxirgi o'tgan bilan, 2 — oxirgidan oldingi bilan va h.k.
  * Pley-off bahsi ko_legs (1/2) o'yindan, final final_legs (1/2) — admin qur'ada tanlaydi.
  * Bahsda necha kishi o'ynashi (match_size: 11 vs 11, 10 vs 10 ...) — qur'ada (ikkala formatda).
  * Pley-off juftligi g'olibi: 1v1 g'alabalar yig'indisi -> gol farqi -> teng bo'lsa LIGA ADMINI
    belgilaydi (needs_admin). Qaror kutilayotganda keyingi bosqich ochilmaydi (tb_seasons.waiting_admin).
Pley-off bahslari tb_fixtures'da division=0 va tie_id bilan (jadval hisobiga kirmaydi);
juftliklar — tb_ko_ties. Har oyoq (leg) — bitta tur (kun). Ko'rinish/qaror — tb_ucl_view.py.

2026-10-26 — PLEY-OFF RAUNDI (egasi: "rasmiy ChL kabi", ucl_playin=1). ucl_qualify = setka hajmi B
(16 / 8 / 4): jadvalning 1..B/2-o'rinlari to'g'ridan setkaga, B/2+1..B/2+B-o'rinlari pley-off raundida
(B/2+1 — oxirgisi bilan: 9–24, 10–23 … 16–17). Raund g'oliblari setkada: 1-o'rin — 16–17 juftligi
g'olibi bilan, 2 — 15–18 bilan … 8 — 9–24 bilan. Kerakli teamlar: 1.5×B (24 / 12 / 6).
Pley-off raundi tb_ko_ties.stage_size = TB_PLAYIN_STAGE (1) bilan saqlanadi (setka bosqichlari >= 2),
bahsi ko_legs o'yindan. ucl_playin=0 — eski qoida (top-N to'g'ridan setkaga).
"""

import logging
import random

from schedule import _generate_round_robin_pairs

logger = logging.getLogger(__name__)

FMT_LEAGUE, FMT_UCL = "league", "ucl"
TB_UCL_QUALIFY = (2, 4, 8, 16)          # pley-offga chiqadiganlar (eski qoida) / setka hajmi
TB_UCL_PLAYIN_BRACKETS = (4, 8, 16)     # 2026-10-26: pley-off raundi bilan setka hajmlari
TB_PLAYIN_STAGE = 1                     # tb_ko_ties.stage_size — pley-off raundi (setka bosqichlari >= 2)
TB_UCL_LEGS = (1, 2)
TB_UCL_ROUNDS_DEFAULT = 6               # liga bosqichida har team nechta bahs o'ynaydi
TB_MATCH_SIZE_MIN, TB_MATCH_SIZE_MAX = 1, 30
KO_DIVISION = 0                         # pley-off bahslari jadvalga kirmasin


def init_ucl_columns(cur) -> None:
    """Migratsiya (idempotent): tb_seasons/tb_fixtures yangi ustunlari + tb_ko_ties."""
    def cols(t):
        return {r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()}
    season_cols = {"format": "TEXT NOT NULL DEFAULT 'league'", "match_size": "INTEGER",
                   "ucl_rounds": "INTEGER", "ucl_qualify": "INTEGER", "ko_legs": "INTEGER",
                   "final_legs": "INTEGER", "waiting_admin": "INTEGER NOT NULL DEFAULT 0",
                   "ucl_playin": "INTEGER NOT NULL DEFAULT 0"}             # 2026-10-26
    have = cols("tb_seasons")
    for name, ddl in season_cols.items():
        if name not in have:
            cur.execute(f"ALTER TABLE tb_seasons ADD COLUMN {name} {ddl}")
    if "tie_id" not in cols("tb_fixtures"):
        cur.execute("ALTER TABLE tb_fixtures ADD COLUMN tie_id INTEGER")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tb_ko_ties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_id INTEGER NOT NULL,
            stage_size INTEGER NOT NULL,
            tie_no INTEGER NOT NULL,
            team_a INTEGER NOT NULL,
            team_b INTEGER NOT NULL,
            legs INTEGER NOT NULL,
            winner_team_id INTEGER,
            needs_admin INTEGER NOT NULL DEFAULT 0,
            UNIQUE (season_id, stage_size, tie_no),
            FOREIGN KEY (season_id) REFERENCES tb_seasons(id),
            FOREIGN KEY (team_a) REFERENCES tb_teams(id),
            FOREIGN KEY (team_b) REFERENCES tb_teams(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tb_ko_season ON tb_ko_ties(season_id, stage_size)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tb_fx_tie ON tb_fixtures(tie_id)")


def playin_need(bracket: int) -> int:
    """Pley-off raundi bilan kerakli teamlar: B/2 to'g'ridan + B raundda (16 -> 24)."""
    return bracket // 2 + bracket


def ko_schedule(qualify: int, ko_legs: int, final_legs: int, playin: bool = False) -> list[tuple[int, int]]:
    """Pley-off turlari ketma-ketligi: [(bosqich hajmi, oyoq), ...]. Masalan 8,2,1 -> 8/1 8/2 4/1 4/2 2/1.
    playin=True — boshida pley-off raundi: (TB_PLAYIN_STAGE, 1), (TB_PLAYIN_STAGE, 2) ..."""
    out = [(TB_PLAYIN_STAGE, leg) for leg in range(1, ko_legs + 1)] if playin else []
    size = qualify
    while size >= 2:
        legs = final_legs if size == 2 else ko_legs
        out.extend((size, leg) for leg in range(1, legs + 1))
        size //= 2
    return out


def validate_ucl(n_teams: int, rounds, qualify, ko_legs, final_legs, playin=False) -> tuple[str | None, dict]:
    """Qur'a parametrlari. Qaytaradi: (sabab | None, tozalangan qiymatlar). Sabab: bad_playin (2026-10-26)."""
    try:
        q, kl, fl = int(qualify), int(ko_legs or 1), int(final_legs or 1)
        r = int(rounds or min(TB_UCL_ROUNDS_DEFAULT, max(1, n_teams - 1)))
    except (TypeError, ValueError):
        return "bad_ucl_params", {}
    playin = bool(playin)
    if playin and (q not in TB_UCL_PLAYIN_BRACKETS or playin_need(q) > n_teams):
        return "bad_playin", {}
    if q not in TB_UCL_QUALIFY or q > n_teams:
        return "bad_qualify", {}
    if kl not in TB_UCL_LEGS or fl not in TB_UCL_LEGS:
        return "bad_legs", {}
    max_r = n_teams - 1 if n_teams % 2 == 0 else n_teams      # toq sonda bitta "dam olish" turi bor
    if r < 1 or r > max_r:
        return "bad_ucl_rounds", {}
    return None, {"ucl_rounds": r, "ucl_qualify": q, "ko_legs": kl, "final_legs": fl, "ucl_playin": int(playin)}


def create_ucl_fixtures(cur, season_id: int, team_ids: list[int], rounds: int) -> int:
    """Liga bosqichi: aylanma jadvalning birinchi `rounds` turi (takrorsiz tasodifiy raqiblar)."""
    ids = team_ids[:]
    random.shuffle(ids)
    for tid in ids:
        cur.execute("INSERT INTO tb_season_teams (season_id, team_id, division) VALUES (?, ?, 1)",
                    (season_id, tid))
    n = 0
    for rnd, pairs in enumerate(_generate_round_robin_pairs(ids)[:rounds], start=1):
        for home, away in pairs:
            if random.random() < 0.5:
                home, away = away, home
            cur.execute("INSERT INTO tb_fixtures (season_id, division, round, home_team_id, away_team_id) "
                        "VALUES (?, 1, ?, ?, ?)", (season_id, rnd, home, away))
            n += 1
    return n


def _tie_score(cur, tie) -> dict:
    """Juftlikning yakunlangan oyoqlari bo'yicha: a/b g'alabalari, gollari, tugaganmi."""
    cur.execute("SELECT home_team_id, home_wins, away_wins, home_goals, away_goals, status "
                "FROM tb_fixtures WHERE tie_id = ? ORDER BY round", (tie["id"],))
    a = {"wins": 0, "goals": 0}
    b = {"wins": 0, "goals": 0}
    legs_done = 0
    for f in cur.fetchall():
        if f["status"] != "finished":
            continue
        legs_done += 1
        ha = f["home_team_id"] == tie["team_a"]
        a["wins"] += f["home_wins"] if ha else f["away_wins"]
        b["wins"] += f["away_wins"] if ha else f["home_wins"]
        a["goals"] += f["home_goals"] if ha else f["away_goals"]
        b["goals"] += f["away_goals"] if ha else f["home_goals"]
    return {"a": a, "b": b, "done": legs_done >= tie["legs"]}


def resolve_ties(cur, season_id: int) -> None:
    """Barcha oyoqlari tugagan, g'olibi yo'q juftliklarni hal qiladi (teng bo'lsa — needs_admin)."""
    cur.execute("SELECT * FROM tb_ko_ties WHERE season_id = ? AND winner_team_id IS NULL", (season_id,))
    for tie in cur.fetchall():
        sc = _tie_score(cur, tie)
        if not sc["done"]:
            continue
        a, b = sc["a"], sc["b"]
        key_a, key_b = (a["wins"], a["goals"] - b["goals"]), (b["wins"], b["goals"] - a["goals"])
        if key_a == key_b:
            cur.execute("UPDATE tb_ko_ties SET needs_admin = 1 WHERE id = ?", (tie["id"],))
        else:
            win = tie["team_a"] if key_a > key_b else tie["team_b"]
            cur.execute("UPDATE tb_ko_ties SET winner_team_id = ?, needs_admin = 0 WHERE id = ?", (win, tie["id"]))


def _stage_at(s: dict, rnd: int) -> tuple[int, int] | None:
    """Tur raqami -> (bosqich hajmi, oyoq) yoki None (liga bosqichi)."""
    if rnd <= (s["ucl_rounds"] or 0):
        return None
    sched = ko_schedule(s["ucl_qualify"], s["ko_legs"], s["final_legs"], bool(s.get("ucl_playin")))
    i = rnd - s["ucl_rounds"] - 1
    return sched[i] if 0 <= i < len(sched) else None


def prepare_round(cur, s: dict, rnd: int) -> str:
    """
    UCL: `rnd` pley-off bosqichining 1-oyog'i bo'lsa — juftliklar va bahslarni yaratadi.
    Qaytaradi: 'ok' yoki 'waiting' (oldingi bosqichda admin qarori kutilmoqda).
    """
    if s.get("format") != FMT_UCL:
        return "ok"
    st = _stage_at(s, rnd)
    if not st or st[1] != 1:
        return "ok"
    size = st[0]
    sid = s["id"]
    if cur.execute("SELECT 1 FROM tb_ko_ties WHERE season_id = ? AND stage_size = ?", (sid, size)).fetchone():
        return "ok"                                         # allaqachon yaratilgan (idempotent)
    playin = bool(s.get("ucl_playin"))
    if size == TB_PLAYIN_STAGE or (size == s["ucl_qualify"] and playin):
        pairs = _playin_pairs(cur, s, size)
        if pairs is None:
            return "waiting"
    elif size == s["ucl_qualify"]:
        from tb_season import _standings_cur
        seeds = [r["team_id"] for r in _standings_cur(cur, sid, 1)][:size]
        pairs = [(seeds[i], seeds[size - 1 - i]) for i in range(size // 2)]
    else:
        resolve_ties(cur, sid)
        cur.execute("SELECT winner_team_id FROM tb_ko_ties WHERE season_id = ? AND stage_size = ? ORDER BY tie_no",
                    (sid, size * 2))
        winners = [r["winner_team_id"] for r in cur.fetchall()]
        if not winners or any(w is None for w in winners):
            return "waiting"
        pairs = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
    legs = s["final_legs"] if size == 2 else s["ko_legs"]               # pley-off raundi ham ko_legs
    for no, (ta, tb) in enumerate(pairs, start=1):
        cur.execute("INSERT INTO tb_ko_ties (season_id, stage_size, tie_no, team_a, team_b, legs) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (sid, size, no, ta, tb, legs))
        tie_id = cur.lastrowid
        for leg in range(legs):
            home, away = (ta, tb) if leg == 0 else (tb, ta)
            cur.execute("INSERT INTO tb_fixtures (season_id, division, round, home_team_id, away_team_id, tie_id) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (sid, KO_DIVISION, rnd + leg, home, away, tie_id))
    logger.info("TB UCL: mavsum %s — %s bosqich (%s juftlik) yaratildi", sid,
                "pley-off raundi" if size == TB_PLAYIN_STAGE else f"1/{size // 2}", len(pairs))
    return "ok"


def _playin_pairs(cur, s: dict, size: int) -> list[tuple[int, int]] | None:
    """
    2026-10-26 (ucl_playin): pley-off raundi yoki undan keyingi birinchi setka bosqichi juftliklari.
      raund: o'rinlar D+1..D+B (D = B/2): (D+1, D+B), (D+2, D+B-1) ... — tie_no 1..D
      setka: i-o'rin (1..D) — (D+1-i)-juftlik g'olibi bilan (1 — 16–17 g'olibi, 8 — 9–24 g'olibi)
    None — raund g'oliblari hali aniq emas (admin qarori kutilmoqda).
    """
    from tb_season import _standings_cur
    sid, b = s["id"], s["ucl_qualify"]
    d = b // 2
    seeds = [r["team_id"] for r in _standings_cur(cur, sid, 1)]
    if size == TB_PLAYIN_STAGE:
        pool = seeds[d:d + b]
        return [(pool[k], pool[b - 1 - k]) for k in range(d)]
    resolve_ties(cur, sid)
    cur.execute("SELECT winner_team_id FROM tb_ko_ties WHERE season_id = ? AND stage_size = ? ORDER BY tie_no",
                (sid, TB_PLAYIN_STAGE))
    winners = [r["winner_team_id"] for r in cur.fetchall()]
    if len(winners) != d or any(w is None for w in winners):
        return None
    return [(seeds[i], winners[d - 1 - i]) for i in range(d)]


def ucl_champion(cur, season_id: int) -> dict | None:
    """Final g'olibi (hal qilingan bo'lsa)."""
    resolve_ties(cur, season_id)
    r = cur.execute("SELECT k.winner_team_id AS team_id, t.name FROM tb_ko_ties k JOIN tb_teams t "
                    "ON t.id = k.winner_team_id WHERE k.season_id = ? AND k.stage_size = 2", (season_id,)).fetchone()
    return dict(r) if r else None
