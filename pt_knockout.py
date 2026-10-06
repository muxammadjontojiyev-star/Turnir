"""
pt_knockout.py — SHAXSIY turnir pley-offi: yarim final, final, chempion (2026-10-02, 5-bosqich).

Yarim finalga 4 kishi (admin qarori, guruhlar ≤ 4):
  2 guruh: A1–B2, B1–A2
  3 guruh: 3 g'olib + eng yaxshi 2-o'rin; eng kuchli g'olib – 2-o'rin (bir guruhdan
           bo'lsa keyingi g'olib bilan almashtiriladi), qolgan ikki g'olib bir-biri bilan
  4 guruh: g'oliblar reytingi 1–4, 2–3
Guruhlararo solishtirish: o'yin boshiga ochko > o'yin boshiga gol farqi > o'yin boshiga gol
(guruhlar o'lchami 3–5 — oddiy ochko adolatsiz bo'lardi).
Bitta o'yin, durang yo'q. Ikkala yarim final confirmed -> final; final confirmed -> chempion.
"""

import logging

from models import get_connection
from pt_results import pt_group_standings

logger = logging.getLogger(__name__)

STAGE_SEMI = "semi"
STAGE_FINAL = "final"


def _cross_key(row: dict) -> tuple:
    p = row["played"] or 1
    return (row["points"] / p, row["goal_diff"] / p, row["goals_for"] / p)


def pt_semi_pairs(standings: dict[str, list[dict]]) -> list[tuple[int, int]]:
    """Guruh jadvallaridan 2 ta yarim final juftligi [(sideA, sideB), ...] (user_id)."""
    labels = sorted(standings)
    if len(labels) == 2:
        a, b = standings[labels[0]], standings[labels[1]]
        return [(a[0]["user_id"], b[1]["user_id"]), (b[0]["user_id"], a[1]["user_id"])]
    winners = sorted(((g, standings[g][0]) for g in labels), key=lambda x: _cross_key(x[1]), reverse=True)
    if len(labels) == 4:
        w = [r["user_id"] for _, r in winners]
        return [(w[0], w[3]), (w[1], w[2])]
    # 3 guruh: eng yaxshi 2-o'rin
    g_r, runner = max(((g, standings[g][1]) for g in labels), key=lambda x: _cross_key(x[1]))
    order = [g for g, _ in winners]
    vs_runner = 0 if order[0] != g_r else 1          # bir guruhdan bo'lsa — keyingi g'olib
    rest = [winners[i][1]["user_id"] for i in range(3) if i != vs_runner]
    return [(winners[vs_runner][1]["user_id"], runner["user_id"]), (rest[0], rest[1])]


def _winner(m) -> int | None:
    if m["status"] != "confirmed" or m["score1"] is None or m["score1"] == m["score2"]:
        return None
    return m["player1_id"] if m["score1"] > m["score2"] else m["player2_id"]


def pt_start_semis(cursor, tid: int) -> list[tuple[int, int]]:
    """Yarim final o'yinlarini yaratadi (ochiq tranzaksiya ichida). Juftliklarni qaytaradi."""
    pairs = pt_semi_pairs(pt_group_standings(cursor, tid))
    cursor.executemany(
        "INSERT INTO pt_matches (tournament_id, stage, round, player1_id, player2_id) VALUES (?, ?, ?, ?, ?)",
        [(tid, STAGE_SEMI, i, a, b) for i, (a, b) in enumerate(pairs, start=1)])
    cursor.execute("UPDATE pt_tournaments SET round_deadline = NULL, updated_at = CURRENT_TIMESTAMP "
                   "WHERE id = ?", (tid,))
    return pairs


def pt_advance(cursor, tid: int) -> dict:
    """
    Har tasdiqlashdan keyin chaqiriladi (idempotent):
      - ikkala yarim final hal -> final yaratiladi yoki (g'olib o'zgargan bo'lsa) yangilanadi;
      - final hal -> turnir 'finished', champion_user_id.
    Qaytaradi: {"event": None | "final_created" | "final_updated" | "finished", ...}
    """
    cursor.execute("SELECT id, stage, round, player1_id, player2_id, score1, score2, status "
                   "FROM pt_matches WHERE tournament_id = ? AND stage IN (?, ?) ORDER BY round",
                   (tid, STAGE_SEMI, STAGE_FINAL))
    rows = [dict(r) for r in cursor.fetchall()]
    semis = [r for r in rows if r["stage"] == STAGE_SEMI]
    final = next((r for r in rows if r["stage"] == STAGE_FINAL), None)
    if final and final["status"] == "confirmed":
        champ = _winner(final)
        if champ:
            cursor.execute("UPDATE pt_tournaments SET status = 'finished', champion_user_id = ?, "
                           "finished_at = CURRENT_TIMESTAMP, round_deadline = NULL, "
                           "updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'running'", (champ, tid))
            if cursor.rowcount:
                return {"event": "finished", "champion_id": champ}
        return {"event": None}
    if len(semis) != 2:
        return {"event": None}
    w = [_winner(s) for s in semis]
    if None in w:
        return {"event": None}
    if final is None:
        cursor.execute("INSERT INTO pt_matches (tournament_id, stage, round, player1_id, player2_id) "
                       "VALUES (?, ?, 1, ?, ?)", (tid, STAGE_FINAL, w[0], w[1]))
        cursor.execute("UPDATE pt_tournaments SET round_deadline = NULL WHERE id = ?", (tid,))
        return {"event": "final_created", "players": w}
    if [final["player1_id"], final["player2_id"]] != w:   # tashkilotchi yarim finalni tuzatgan
        cursor.execute("UPDATE pt_matches SET player1_id = ?, player2_id = ?, score1 = NULL, score2 = NULL, "
                       "submitted_by = NULL, status = 'pending' WHERE id = ?", (w[0], w[1], final["id"]))
        return {"event": "final_updated", "players": w}
    return {"event": None}


def pt_knockout_phase(cursor, tid: int) -> str | None:
    """None (guruh) | 'semi_ready' (yarim final hali boshlanmagan) | 'semi' | 'final' | 'finished'."""
    cursor.execute("SELECT status, current_round, total_rounds FROM pt_tournaments WHERE id = ?", (tid,))
    t = cursor.fetchone()
    if not t or t["total_rounds"] == 0 or t["current_round"] <= t["total_rounds"]:
        return None
    if t["status"] == "finished":
        return "finished"
    cursor.execute("SELECT stage FROM pt_matches WHERE tournament_id = ? AND stage IN (?, ?)",
                   (tid, STAGE_SEMI, STAGE_FINAL))
    stages = {r["stage"] for r in cursor.fetchall()}
    if STAGE_FINAL in stages:
        return "final"
    return "semi" if STAGE_SEMI in stages else "semi_ready"


def pt_owner_start_semis(tid: int, owner_id: int) -> tuple[bool, str | list]:
    """Tashkilotchi yarim finalni boshlaydi. Sabablar: not_found, not_owner, not_running, not_ready."""
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT owner_user_id, status FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        why = None
        if not t:
            why = "not_found"
        elif t["owner_user_id"] != owner_id:
            why = "not_owner"
        elif t["status"] != "running":
            why = "not_running"
        elif pt_knockout_phase(cursor, tid) != "semi_ready":
            why = "not_ready"                      # guruhlar tugamagan yoki allaqachon boshlangan
        if why:
            cursor.execute("ROLLBACK")
            return False, why
        pairs = pt_start_semis(cursor, tid)
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_owner_start_semis: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
    logger.info("PT #%s: yarim final boshlandi %s", tid, pairs)
    return True, pairs
