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
"""

import logging
import random

from schedule import _generate_round_robin_pairs

logger = logging.getLogger(__name__)

FMT_LEAGUE, FMT_UCL = "league", "ucl"
TB_UCL_QUALIFY = (2, 4, 8, 16)          # pley-offga chiqadiganlar
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
                   "final_legs": "INTEGER", "waiting_admin": "INTEGER NOT NULL DEFAULT 0"}
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


def ko_schedule(qualify: int, ko_legs: int, final_legs: int) -> list[tuple[int, int]]:
    """Pley-off turlari ketma-ketligi: [(bosqich hajmi, oyoq), ...]. Masalan 8,2,1 -> 8/1 8/2 4/1 4/2 2/1."""
    out, size = [], qualify
    while size >= 2:
        legs = final_legs if size == 2 else ko_legs
        out.extend((size, leg) for leg in range(1, legs + 1))
        size //= 2
    return out


def validate_ucl(n_teams: int, rounds, qualify, ko_legs, final_legs) -> tuple[str | None, dict]:
    """Qur'a parametrlari. Qaytaradi: (sabab | None, tozalangan qiymatlar)."""
    try:
        q, kl, fl = int(qualify), int(ko_legs or 1), int(final_legs or 1)
        r = int(rounds or min(TB_UCL_ROUNDS_DEFAULT, max(1, n_teams - 1)))
    except (TypeError, ValueError):
        return "bad_ucl_params", {}
    if q not in TB_UCL_QUALIFY or q > n_teams:
        return "bad_qualify", {}
    if kl not in TB_UCL_LEGS or fl not in TB_UCL_LEGS:
        return "bad_legs", {}
    max_r = n_teams - 1 if n_teams % 2 == 0 else n_teams      # toq sonda bitta "dam olish" turi bor
    if r < 1 or r > max_r:
        return "bad_ucl_rounds", {}
    return None, {"ucl_rounds": r, "ucl_qualify": q, "ko_legs": kl, "final_legs": fl}


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
    sched = ko_schedule(s["ucl_qualify"], s["ko_legs"], s["final_legs"])
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
    if size == s["ucl_qualify"]:
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
    legs = s["final_legs"] if size == 2 else s["ko_legs"]
    for no, (ta, tb) in enumerate(pairs, start=1):
        cur.execute("INSERT INTO tb_ko_ties (season_id, stage_size, tie_no, team_a, team_b, legs) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (sid, size, no, ta, tb, legs))
        tie_id = cur.lastrowid
        for leg in range(legs):
            home, away = (ta, tb) if leg == 0 else (tb, ta)
            cur.execute("INSERT INTO tb_fixtures (season_id, division, round, home_team_id, away_team_id, tie_id) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (sid, KO_DIVISION, rnd + leg, home, away, tie_id))
    logger.info("TB UCL: mavsum %s — 1/%s bosqich (%s juftlik) yaratildi", sid, size // 2, len(pairs))
    return "ok"


def ucl_champion(cur, season_id: int) -> dict | None:
    """Final g'olibi (hal qilingan bo'lsa)."""
    resolve_ties(cur, season_id)
    r = cur.execute("SELECT k.winner_team_id AS team_id, t.name FROM tb_ko_ties k JOIN tb_teams t "
                    "ON t.id = k.winner_team_id WHERE k.season_id = ? AND k.stage_size = 2", (season_id,)).fetchone()
    return dict(r) if r else None
