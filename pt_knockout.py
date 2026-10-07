"""
pt_knockout.py — SHAXSIY turnir pley-offi (5-bosqich; 2026-10-03: 128 kishigacha).
2026-10-07: ChL/YeL formati — yagona jadvaldan: top-Q to'g'ridan setkaga, Q+1..3Q pley-off raundi
("po", 1 o'yin), so'ng 2Q setka (cl_po_pairs, cl_bracket_slots). Liga formatida pley-off yo'q.

Admin qarori:
  - Pley-offga BARCHA guruh g'oliblari + eng yaxshi 2-o'rinlar (qolgan joylarga).
  - Setka hajmi P = 2 ning darajasi, 2·G dan oshmaydigan eng kattasi (4..64), G — guruhlar.
      2–3 guruh -> 4 (yarim final), 4–7 -> 8 (1/4), 8–15 -> 16 (1/8), 16–31 -> 32 (1/16), 32 -> 64 (1/32).
      Guruhlar 4 kishilik (pt_draw): 8 kishi -> yarim final ... 128 kishi (32 guruh) -> 1/32 final.
  - Urug'lash: g'oliblar (kuch tartibida), keyin 2-o'rinlar; guruhlararo solishtirish —
    o'yin boshiga ochko > GF/o'yin > gol/o'yin (guruhlar 3–5 kishi — oddiy ochko adolatsiz).
  - Standart setka: 1-urug' va 2-urug' faqat finalda uchrashadi; 1-turda bir guruhdan
    ikki kishi tushsa, quyi urug'lar o'rni almashtiriladi.
  - Har o'yin bitta, durang yo'q. Bosqichning HAMMA o'yinlari hal bo'lgach keyingi bosqich
    yaratiladi (k-o'yin = (2k-1) va (2k) g'oliblari). Final hal -> chempion.
"""

import logging

from models import get_connection
from pt_core import is_manager
from pt_legs import insert_ties, ko_legs, ko_ties, update_tie_players
from pt_results import pt_group_standings

logger = logging.getLogger(__name__)

# 2026-10-07: "po" — ChL/YeL pley-off raundi (rasmiy 9–24 pley-in kabi), setkadan oldin
STAGES = ["po", "r64", "r32", "r16", "qf", "semi", "final"]
STAGE_PO = "po"
STAGE_FOR_SIZE = {64: "r64", 32: "r32", 16: "r16", 8: "qf", 4: "semi", 2: "final"}
STAGE_SEMI = "semi"
STAGE_FINAL = "final"
BRACKET_MIN, BRACKET_MAX = 4, 64


def bracket_size(n_groups: int) -> int:
    p = BRACKET_MIN
    while p * 2 <= min(2 * n_groups, BRACKET_MAX):
        p *= 2
    return p


def _fmt(cursor, tid: int) -> str:
    cursor.execute("SELECT format FROM pt_tournaments WHERE id = ?", (tid,))
    r = cursor.fetchone()
    return (r["format"] if r else None) or "classic"


def pt_bracket_size(fmt: str, standings: dict[str, list[dict]]) -> int:
    """Setka hajmi: ChL/YeL — 2Q (pt_formats.cl_direct_count); guruhli formatlar — bracket_size."""
    from pt_formats import FMT_CL, FMT_EL, cl_direct_count
    if fmt in (FMT_CL, FMT_EL):
        return 2 * cl_direct_count(sum(len(r) for r in standings.values()))
    return bracket_size(len(standings))


def _ranking(standings: dict[str, list[dict]]) -> list[int]:
    return [r["user_id"] for r in next(iter(standings.values()), [])]


def cl_po_pairs(ranking: list[int]) -> list[tuple[int, int]]:
    """ChL/YeL pley-off raundi: k-juftlik = (Q+1+k)-o'rin vs (3Q-k)-o'rin (kuchli — eng past bilan)."""
    from pt_formats import cl_direct_count
    q = cl_direct_count(len(ranking))
    return [(ranking[q + k], ranking[3 * q - 1 - k]) for k in range(q)]


def cl_bracket_slots(ranking: list[int]) -> list[tuple[tuple, tuple]]:
    """
    Setka 1-bosqichi (2Q): urug'lar 1..Q — jadvaldagi top-Q ('u', user_id); Q+1..2Q — pley-off
    raundi g'oliblari ('w', juftlik indeksi; k-juftlik g'olibi Q+1+k-urug'). Standart setka
    (seed_order): 1-urug' eng zaif pley-off juftligi g'olibi bilan — rasmiy ChL kabi.
    """
    from pt_formats import cl_direct_count
    q = cl_direct_count(len(ranking))
    seeds = [("u", ranking[i]) for i in range(q)] + [("w", k) for k in range(q)]
    order = seed_order(2 * q)
    return [(seeds[order[i] - 1], seeds[order[i + 1] - 1]) for i in range(0, 2 * q, 2)]


def _cross_key(row: dict) -> tuple:
    p = row["played"] or 1
    return (row["points"] / p, row["goal_diff"] / p, row["goals_for"] / p)


def seed_order(size: int) -> list[int]:
    """Standart setka tartibi (1-asosli urug'lar): 4 -> [1,4,2,3], 8 -> [1,8,4,5,2,7,3,6]."""
    order = [1, 2]
    while len(order) < size:
        n = len(order) * 2
        order = [x for s in order for x in (s, n + 1 - s)]
    return order


def pt_playoff_seeds(standings: dict[str, list[dict]]) -> list[tuple[int, str]]:
    """[(user_id, guruh), ...] urug' tartibida: g'oliblar, keyin eng yaxshi 2-o'rinlar."""
    size = bracket_size(len(standings))
    winners = sorted(((g, rows[0]) for g, rows in standings.items() if rows),
                     key=lambda x: _cross_key(x[1]), reverse=True)
    runners = sorted(((g, rows[1]) for g, rows in standings.items() if len(rows) > 1),
                     key=lambda x: _cross_key(x[1]), reverse=True)
    seeds = [(r["user_id"], g) for g, r in winners] + [(r["user_id"], g) for g, r in runners]
    return seeds[:size]


def pt_first_round_pairs(standings: dict[str, list[dict]]) -> tuple[str, list[tuple[int, int]]]:
    """(bosqich, [(yuqori_urug', quyi_urug'), ...]) — bir guruhdan ikki kishi 1-turda uchrashmaydi."""
    seeds = pt_playoff_seeds(standings)
    size = len(seeds)
    order = seed_order(size)
    pairs = [[seeds[order[i] - 1], seeds[order[i + 1] - 1]] for i in range(0, size, 2)]
    for i, (hi, lo) in enumerate(pairs):
        if hi[1] != lo[1]:
            continue
        # yaqin juftlik bilan quyi urug'larni almashtiramiz (ikkala tomon ham to'qnashmasin)
        for j in sorted(range(len(pairs)), key=lambda k: abs(k - i)):
            if j == i:
                continue
            hj, lj = pairs[j]
            if lj[1] != hi[1] and lo[1] != hj[1]:
                pairs[i][1], pairs[j][1] = lj, lo
                break
    return STAGE_FOR_SIZE[size], [(a[0], b[0]) for a, b in pairs]


# Eski nom (5-bosqich testlari va chaqiruvlar uchun moslik)
def pt_semi_pairs(standings):
    return pt_first_round_pairs(standings)[1]


def _winner(m) -> int | None:
    if m["status"] != "confirmed" or m["score1"] is None or m["score1"] == m["score2"]:
        return None
    return m["player1_id"] if m["score1"] > m["score2"] else m["player2_id"]


def pt_start_knockout(cursor, tid: int) -> tuple[str, list[tuple[int, int]]]:
    """1-bosqich o'yinlarini yaratadi (ochiq tranzaksiya ichida). ChL/YeL — pley-off raundi."""
    standings = pt_group_standings(cursor, tid)
    if _fmt(cursor, tid) in ("cl", "el"):
        stage, pairs = STAGE_PO, cl_po_pairs(_ranking(standings))
    else:
        stage, pairs = pt_first_round_pairs(standings)
    insert_ties(cursor, tid, stage, pairs, ko_legs(cursor, tid))    # erkin 2 doira — javob o'yini bilan
    cursor.execute("UPDATE pt_tournaments SET round_deadline = NULL, updated_at = CURRENT_TIMESTAMP "
                   "WHERE id = ?", (tid,))
    return stage, pairs


def _ko_by_stage(cursor, tid: int) -> dict[str, list[dict]]:
    """2026-10-07: juftliklar (ikki o'yinli bo'lsa — yig'indi bilan), pt_legs.ko_ties."""
    return ko_ties(cursor, tid)


def pt_advance(cursor, tid: int) -> dict:
    """
    Har tasdiqlashdan keyin (idempotent):
      - tuzatish natijasida g'olib o'zgargan bo'lsa — keyingi bosqich o'yini yangilanadi
        (u hali tasdiqlanmagan bo'lsa): event 'stage_updated';
      - oxirgi bosqichning hamma o'yini hal -> keyingi bosqich: event 'stage_created';
      - final hal -> turnir 'finished': event 'finished'.
    """
    by = _ko_by_stage(cursor, tid)
    present = [s for s in STAGES if s in by]
    if not present:
        return {"event": None}
    slots = None
    if STAGE_PO in by:                                   # ChL/YeL: setka urug'lari jadvaldan (o'zgarmas)
        slots = cl_bracket_slots(_ranking(pt_group_standings(cursor, tid)))
    po_win = [_winner(m) for m in by.get(STAGE_PO, [])]

    def _slot(sl):
        return sl[1] if sl[0] == "u" else po_win[sl[1]]

    updated = None
    for s, nxt in zip(present, present[1:]):
        for j, m in enumerate(by[nxt]):
            if s == STAGE_PO:
                w = [_slot(a) for a in slots[j]] if j < len(slots) else [None]
            else:
                w = [_winner(x) for x in by[s][2 * j:2 * j + 2]]
            if None in w or [m["player1_id"], m["player2_id"]] == w or m["any_confirmed"]:
                continue
            update_tie_players(cursor, m, w[0], w[1])
            m.update(player1_id=w[0], player2_id=w[1], status="pending", score1=None, score2=None)
            updated = {"event": "stage_updated", "stage": nxt, "players": w}
    last = present[-1]
    winners = [_winner(m) for m in by[last]]
    if None in winners:
        return updated or {"event": None}
    if last == STAGE_FINAL:
        cursor.execute("UPDATE pt_tournaments SET status = 'finished', champion_user_id = ?, "
                       "finished_at = CURRENT_TIMESTAMP, round_deadline = NULL, "
                       "updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'running'", (winners[0], tid))
        return {"event": "finished", "champion_id": winners[0]} if cursor.rowcount else (updated or {"event": None})
    if last == STAGE_PO:
        nxt = STAGE_FOR_SIZE[2 * len(slots)]
        pairs = [(_slot(a), _slot(b)) for a, b in slots]
    else:
        nxt = STAGES[STAGES.index(last) + 1]
        pairs = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
    insert_ties(cursor, tid, nxt, pairs, ko_legs(cursor, tid))
    cursor.execute("UPDATE pt_tournaments SET round_deadline = NULL WHERE id = ?", (tid,))
    return {"event": "stage_created", "stage": nxt, "pairs": pairs,
            "players": list(pairs[0]) if nxt == STAGE_FINAL else None}


def pt_next_match_locked(cursor, tid: int, stage: str, rnd: int) -> bool:
    """Shu o'yin g'olibi o'tgan keyingi bosqich o'yini allaqachon tasdiqlanganmi? (tuzatish taqiqi)"""
    if stage == STAGE_FINAL:
        return False
    if stage == STAGE_PO:                                # ChL/YeL: g'olib qaysi setka o'yiniga o'tgan
        slots = cl_bracket_slots(_ranking(pt_group_standings(cursor, tid)))
        j = next((i for i, pair in enumerate(slots) if ("w", rnd - 1) in pair), None)
        if j is None:
            return False
        nxt, nrnd = STAGE_FOR_SIZE[2 * len(slots)], j + 1
    else:
        nxt, nrnd = STAGES[STAGES.index(stage) + 1], (rnd + 1) // 2
    cursor.execute("SELECT 1 FROM pt_matches WHERE tournament_id = ? AND stage = ? AND round = ? "
                   "AND status = 'confirmed'", (tid, nxt, nrnd))          # ikki o'yinli: birortasi tasdiqlangan
    return cursor.fetchone() is not None


def pt_knockout_phase(cursor, tid: int) -> str | None:
    """None (guruh) | 'ko_ready' (pley-off boshlanmagan) | joriy bosqich ('r64'..'final') | 'finished'."""
    cursor.execute("SELECT status, current_round, total_rounds FROM pt_tournaments WHERE id = ?", (tid,))
    t = cursor.fetchone()
    if not t or t["total_rounds"] == 0 or t["current_round"] <= t["total_rounds"]:
        return None
    if t["status"] == "finished":
        return "finished"
    cursor.execute("SELECT DISTINCT stage FROM pt_matches WHERE tournament_id = ? AND stage != 'group'", (tid,))
    stages = {r["stage"] for r in cursor.fetchall()}
    present = [s for s in STAGES if s in stages]
    return present[-1] if present else "ko_ready"


def pt_owner_start_knockout(tid: int, owner_id: int) -> tuple[bool, str | dict]:
    """Tashkilotchi pley-offni boshlaydi. Sabablar: not_found, not_owner, not_running, not_ready."""
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
        elif not is_manager(cursor, tid, owner_id, t["owner_user_id"]):   # tashkilotchi yoki admin
            why = "not_owner"
        elif t["status"] != "running":
            why = "not_running"
        elif pt_knockout_phase(cursor, tid) != "ko_ready" or _fmt(cursor, tid) == "league":
            why = "not_ready"                            # liga formatida pley-off yo'q
        if why:
            cursor.execute("ROLLBACK")
            return False, why
        stage, pairs = pt_start_knockout(cursor, tid)
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_owner_start_knockout: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
    logger.info("PT #%s: pley-off boshlandi (%s, %s juftlik)", tid, stage, len(pairs))
    return True, {"stage": stage, "pairs": pairs}
