"""
season_rewards.py — MAVSUM MUKOFOTI: eF Token (2026-11-01).

Egasi so'rovi: mavsum yakunlanganda ishtirokchilarga o'rni, sovrinlari va kubok turnirlarida qaysi
bosqichgacha borganiga qarab farqli eF Token beriladi. Summalar — egasi tasdiqlagan jadval (pastda).

Qachon beriladi (har biri O'Z yakunlash tugmasida, reset'dan OLDIN, o'sha tranzaksiyada):
  * liga      — season_prizes._finalize_league_locked: o'rin (1-ligalar to'liq, 2-ligalar yarmi)
                + Oltin to'p / Oltin butsa;
  * ChL / YeL / OChL — finalize_cl_season / el_finalize / ac_finalize: eng uzoq yetgan bosqich;
  * JCh       — _finalize_wc_locked: bosqich + JCh Oltin butsasi.
Shartlar: liga — kamida yarim o'yin (ligadagi eng ko'p o'ynaganning yarmi) va «tashlab ketgan» emas;
kubok turnirlari — kamida 1 ta tasdiqlangan o'yin. Bosqich summalari qo'shilmaydi (eng yuqorisi).
Takror yo'q: season_rewards UNIQUE(kind, season, user_id) + wallet_tx (kind, ref) (qoida #38).
Xato yakunlashni to'xtatmaydi: SAVEPOINT ichida, xato bo'lsa faqat mukofot bekor bo'ladi (log).
Bot xabari — season_rewards_notify.py (scheduler).
"""

import json
import logging

from config import MATCH_STATUS_CONFIRMED, SECOND_TIER_LEAGUES

logger = logging.getLogger(__name__)

# --- summalar (eF Token) ---
LEAGUE_POS_REWARDS = ((1, 300), (2, 200), (3, 150), (5, 100), (10, 70), (15, 50), (20, 30))  # (shu o'ringacha, summa)
SECOND_TIER_DIVISOR = 2            # 2-ligalar — yarmi
GOLDEN_BONUS = 200                 # Oltin to'p, Oltin butsa (liga va JCh)
CUP_STAGES = ("league", "playin", "r16", "r8", "r4", "finalist", "champion")
CUP_REWARDS = {
    "cl": dict(zip(CUP_STAGES, (50, 80, 120, 180, 250, 350, 500))),
    "el": dict(zip(CUP_STAGES, (30, 50, 80, 120, 170, 230, 350))),
    "ac": dict(zip(CUP_STAGES, (30, 50, 80, 120, 170, 230, 350))),   # egasi: Osiyo ChL — YeL summalari
}
WC_STAGES = ("group", "r32", "r16", "r8", "r4", "third", "finalist", "champion")
WC_REWARDS = dict(zip(WC_STAGES, (50, 80, 120, 180, 250, 300, 350, 500)))
_CUP_TABLES = {"cl": ("cl_participants", "cl_matches", "cl_playoff_matches"),
               "el": ("el_participants", "el_matches", "el_playoff_matches"),
               "ac": ("ac_participants", "ac_matches", "ac_playoff_matches")}   # nomlar KODDAN (qoida #29)
TX_PREFIX = "reward_"


def init_rewards_table(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS season_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            season INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            telegram_id INTEGER,
            amount INTEGER NOT NULL,
            detail TEXT NOT NULL,
            notified INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (kind, season, user_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_season_rewards_notified ON season_rewards(notified)")


def _grant(cur, kind: str, season: int, user_id: int, parts: list[dict]) -> int:
    """Bitta ishtirokchiga yozadi va balansga qo'shadi. Qaytaradi: berilgan summa (takror bo'lsa 0)."""
    total = sum(p["a"] for p in parts)
    row = cur.execute("SELECT telegram_id FROM users WHERE id = ?", (user_id,)).fetchone()
    if total <= 0 or not row:
        return 0
    cur.execute("INSERT OR IGNORE INTO season_rewards (kind, season, user_id, telegram_id, amount, detail) "
                "VALUES (?, ?, ?, ?, ?, ?)", (kind, season, user_id, row["telegram_id"], total,
                                              json.dumps(parts, ensure_ascii=False)))
    if not cur.rowcount:
        return 0
    from wallet import wallet_change
    wallet_change(cur, user_id, total, TX_PREFIX + kind, cur.lastrowid)
    return total


def _safe_run(cur, kind: str, season: int, build) -> dict:
    """build() -> {user_id: [parts]}; SAVEPOINT — xato bo'lsa faqat mukofot bekor, yakunlash davom etadi."""
    cur.execute("SAVEPOINT season_rewards")
    try:
        people, total = 0, 0
        for uid, parts in build().items():
            got = _grant(cur, kind, season, uid, parts)
            people, total = people + (got > 0), total + got
        cur.execute("RELEASE SAVEPOINT season_rewards")
        logger.info("MUKOFOT %s #%s: %s kishiga jami %s eF", kind, season, people, total)
        return {"people": people, "total": total}
    except Exception:
        cur.execute("ROLLBACK TO SAVEPOINT season_rewards")
        cur.execute("RELEASE SAVEPOINT season_rewards")
        logger.exception("MUKOFOT %s #%s: xato — mukofot berilmadi (yakunlash davom etadi)", kind, season)
        return {"people": 0, "total": 0, "error": True}


def _pos_reward(pos: int) -> int:
    return next((a for last, a in LEAGUE_POS_REWARDS if pos <= last), 0)


def grant_league_rewards(cur, season: int, prizes: dict | None) -> dict:
    def build():
        from rating import calculate_league_rating
        out: dict[int, list] = {}
        leagues = cur.execute("SELECT id, name FROM leagues WHERE id IN "
                              "(SELECT DISTINCT league_id FROM registrations)").fetchall()
        abandoned = {r["telegram_id"] for r in cur.execute(
            "SELECT telegram_id FROM club_reliability WHERE season_number = ? AND status = 'abandoned'", (season,))}
        for lg in leagues:
            table = calculate_league_rating(lg["id"])
            most = max((p["played"] for p in table), default=0)
            for pos, p in enumerate(table, start=1):
                tg = cur.execute("SELECT telegram_id FROM users WHERE id = ?", (p["user_id"],)).fetchone()
                if not p["played"] or p["played"] * 2 < most or (tg and tg["telegram_id"] in abandoned):
                    continue
                amount = _pos_reward(pos)
                if lg["name"] in SECOND_TIER_LEAGUES:
                    amount //= SECOND_TIER_DIVISOR
                if amount:
                    out.setdefault(p["user_id"], []).append({"k": "pos", "lg": lg["name"], "n": pos, "a": amount})
        for key in ("golden_ball", "golden_boot"):
            winner = (prizes or {}).get(key)
            if winner and winner.get("user_id"):
                out.setdefault(winner["user_id"], []).append({"k": key, "a": GOLDEN_BONUS})
        return out
    return _safe_run(cur, "league", season, build)


def _played(cur, tables: tuple[str, ...]) -> set[int]:
    ids: set[int] = set()
    for t in tables:
        for r in cur.execute(f"SELECT player1_id, player2_id FROM {t} WHERE status = ?", (MATCH_STATUS_CONFIRMED,)):
            ids.update(x for x in (r["player1_id"], r["player2_id"]) if x)
    return ids


def _reached(cur, po_table: str, order: tuple[str, ...]) -> dict[int, int]:
    """{user_id: eng yuqori bosqich indeksi (order bo'yicha)} — play-off jadvalidagi ishtirokidan."""
    best: dict[int, int] = {}
    for r in cur.execute(f"SELECT round, player1_id, player2_id FROM {po_table}"):
        if r["round"] not in order:
            continue
        for uid in (r["player1_id"], r["player2_id"]):
            if uid:
                best[uid] = max(best.get(uid, 0), order.index(r["round"]))
    return best


def grant_cup_rewards(cur, kind: str, season: int, champion_uid: int | None) -> dict:
    """ChL / YeL / OChL: bosqich — liga bosqichi < pley-in < 1/8 < 1/4 < 1/2 < finalchi < chempion."""
    part_t, match_t, po_t = _CUP_TABLES[kind]
    order = CUP_STAGES[:5] + ("final",)

    def build():
        played = _played(cur, (match_t, po_t))
        best = _reached(cur, po_t, order)
        out = {}
        for r in cur.execute(f"SELECT DISTINCT user_id FROM {part_t}").fetchall():
            uid = r["user_id"]
            if uid not in played:
                continue
            stage = "champion" if uid == champion_uid else (
                "finalist" if best.get(uid) == order.index("final") else CUP_STAGES[best.get(uid, 0)])
            out[uid] = [{"k": "stage", "s": stage, "a": CUP_REWARDS[kind][stage]}]
        return out
    return _safe_run(cur, kind, season, build)


def grant_wc_rewards(cur, season: int, prizes: dict | None) -> dict:
    """JCh: guruh < 1/16 < 1/8 < 1/4 < 1/2 < 3-o'rin (bronza g'olibi) < finalchi < chempion; + Oltin butsa."""
    order = ("group", "r32", "r16", "r8", "r4", "final")

    def build():
        played = _played(cur, ("wc_matches", "wc_playoff_matches"))
        best = _reached(cur, "wc_playoff_matches", order)
        champ = ((prizes or {}).get("wc_cup") or {}).get("user_id")
        third = None
        b = cur.execute("SELECT player1_id, player2_id, score1, score2 FROM wc_playoff_matches "
                        "WHERE round = 'bronze' AND status = ?", (MATCH_STATUS_CONFIRMED,)).fetchone()
        if b and b["score1"] is not None and b["score2"] is not None and b["score1"] != b["score2"]:
            third = b["player1_id"] if b["score1"] > b["score2"] else b["player2_id"]
        out = {}
        for r in cur.execute("SELECT user_id FROM wc_registrations").fetchall():
            uid = r["user_id"]
            if uid not in played:
                continue
            idx = best.get(uid, 0)
            stage = ("champion" if uid == champ else "finalist" if idx == order.index("final")
                     else "third" if uid == third else order[idx])
            out[uid] = [{"k": "stage", "s": stage, "a": WC_REWARDS[stage]}]
        boot = (prizes or {}).get("wc_golden_boot")
        if boot and boot.get("user_id") and boot["user_id"] in played:
            out.setdefault(boot["user_id"], []).append({"k": "golden_boot", "a": GOLDEN_BONUS})
        return out
    return _safe_run(cur, "wc", season, build)
