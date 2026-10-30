"""
pt_ko_wc.py — SHAXSIY "Jahon chempionati" (wc) formati pley-offi, rasmiy JCh qoidasi (2026-10-30).

Muammo: wc formati klassik qoidadan foydalanardi (setka — 2·G dan oshmaydigan 2 ning darajasi,
faqat g'oliblar + eng yaxshi 2-o'rinlar). 48 kishi (12 guruh) -> 16 kishilik setka: 12 g'olib + 4 ta
2-o'rin, qolgan 2-o'rinlar va 3-o'rinlar chiqmay qolardi.

Yangi qoida (wc_bracket_size):
  - Setka P = 2·G dan kichik bo'lmagan eng kichik 2 ning darajasi (kamida 4).
  - P <= 3·G (3-o'rinlar bilan to'ldirish mumkin) va P <= 64 bo'lsa: HAMMA g'oliblar + HAMMA
    2-o'rinlar + eng yaxshi (P − 2·G) ta 3-o'rin. Aks holda — klassik qoida (pt_knockout.bracket_size).
      G=12 (48 kishi) -> 32: 12 + 12 + 8 ta eng yaxshi 3-o'rin (1/16 final) — rasmiy JCh-2026 kabi.
      G=6 -> 16 (4 ta 3-o'rin), G=3 -> 8 (2 ta 3-o'rin), G=2/4/8 -> 4/8/16 (3-o'rinsiz),
      G=5 -> 8 (klassik: 16 uchun 3-o'rinlar yetmaydi).
  - Urug'lash: g'oliblar, keyin 2-o'rinlar, keyin 3-o'rinlar — har biri o'z ichida _cross_key bo'yicha.
    Bir guruhdan ikki kishi 1-turda uchrashmasligi — pt_knockout.pt_first_round_pairs (o'zgarmagan).

Qayta tuzish (pt_wc_rebuild_knockout): eski qoida bilan ochilgan JCh setkasi — pley-offda hali
birorta natija kiritilmagan bo'lsa — o'chiriladi va yangi qoida bilan qayta yaratiladi.
"""

import logging

from models import get_connection
from pt_core import is_manager

logger = logging.getLogger(__name__)

WC_THIRD_PLACE_INDEX = 2          # guruh jadvalida 3-o'rin (0-asosli)


def wc_bracket_size(n_groups: int) -> int:
    from pt_knockout import BRACKET_MAX, BRACKET_MIN, bracket_size
    p = BRACKET_MIN
    while p < 2 * n_groups:
        p *= 2
    if p <= 3 * n_groups and p <= BRACKET_MAX:
        return p
    return bracket_size(n_groups)


def wc_thirds_count(n_groups: int) -> int:
    """Setkaga chiqadigan 3-o'rinlar soni (0 — 3-o'rinsiz)."""
    return max(0, wc_bracket_size(n_groups) - 2 * n_groups)


def wc_playoff_seeds(standings: dict[str, list[dict]]) -> list[tuple[int, str]]:
    """[(user_id, guruh), ...] urug' tartibida: g'oliblar, 2-o'rinlar, eng yaxshi 3-o'rinlar."""
    from pt_knockout import _cross_key
    size = wc_bracket_size(len(standings))
    seeds = []
    for place in range(WC_THIRD_PLACE_INDEX + 1):
        tier = sorted(((g, rows[place]) for g, rows in standings.items() if len(rows) > place),
                      key=lambda x: _cross_key(x[1]), reverse=True)
        seeds += [(r["user_id"], g) for g, r in tier]
    return seeds[:size]


def _first_stage_pairs(cursor, tid: int) -> tuple[str | None, set]:
    """Hozirgi pley-off 1-bosqichi va uning juftliklari (1-o'yin bo'yicha)."""
    from pt_knockout import STAGES
    cursor.execute("SELECT stage, player1_id, player2_id, leg FROM pt_matches "
                   "WHERE tournament_id = ? AND stage != 'group'", (tid,))
    rows = cursor.fetchall()
    present = [s for s in STAGES if any(r["stage"] == s for r in rows)]
    if not present:
        return None, set()
    first = present[0]
    return first, {frozenset((r["player1_id"], r["player2_id"])) for r in rows
                   if r["stage"] == first and (r["leg"] or 1) == 1}


def wc_rebuild_block(cursor, tid: int) -> str | None:
    """
    Qayta tuzish mumkinmi (ochiq tranzaksiya yoki oddiy o'qish ichida). None — mumkin; aks holda sabab:
    not_found, not_running, bad_format, not_started, ko_has_results, nothing_to_change.
    """
    from pt_formats import FMT_WC
    from pt_knockout import pt_first_round_pairs, pt_knockout_phase
    from pt_results import pt_group_standings
    cursor.execute("SELECT status, format FROM pt_tournaments WHERE id = ?", (tid,))
    t = cursor.fetchone()
    if not t:
        return "not_found"
    if t["status"] != "running":
        return "not_running"
    if (t["format"] or "classic") != FMT_WC:
        return "bad_format"
    if pt_knockout_phase(cursor, tid) in (None, "ko_ready"):
        return "not_started"
    cursor.execute("SELECT 1 FROM pt_matches WHERE tournament_id = ? AND stage != 'group' AND "
                   "(status != 'pending' OR score1 IS NOT NULL OR submitted_by IS NOT NULL) LIMIT 1", (tid,))
    if cursor.fetchone():
        return "ko_has_results"
    stage, pairs = pt_first_round_pairs(pt_group_standings(cursor, tid), FMT_WC)
    cur_stage, cur_pairs = _first_stage_pairs(cursor, tid)
    if cur_stage == stage and cur_pairs == {frozenset(p) for p in pairs}:
        return "nothing_to_change"
    return None


def pt_wc_rebuild_knockout(tid: int, user_id: int) -> tuple[bool, str | dict]:
    """Tashkilotchi/admin: JCh setkasini yangi qoida bilan qayta tuzadi. Sabablar — wc_rebuild_block + not_owner."""
    from pt_knockout import pt_start_knockout
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT owner_user_id FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        why = "not_found" if not t else (
            None if is_manager(cursor, tid, user_id, t["owner_user_id"]) else "not_owner")
        why = why or wc_rebuild_block(cursor, tid)
        if why:
            cursor.execute("ROLLBACK")
            return False, why
        cursor.execute("DELETE FROM pt_messages WHERE match_id IN (SELECT id FROM pt_matches "
                       "WHERE tournament_id = ? AND stage != 'group')", (tid,))
        cursor.execute("DELETE FROM pt_matches WHERE tournament_id = ? AND stage != 'group'", (tid,))
        stage, pairs = pt_start_knockout(cursor, tid)
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_wc_rebuild_knockout: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
    logger.info("PT #%s: JCh setkasi qayta tuzildi (%s, %s juftlik)", tid, stage, len(pairs))
    return True, {"stage": stage, "pairs": pairs}
