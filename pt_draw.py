"""
pt_draw.py — SHAXSIY turnir qur'asi (2026-10-02, 4-bosqich).

Admin qarori (guruhlar ≤ 4 ta, 4 kishilikka yaqin):
  6–8 ishtirokchi  -> 2 guruh      9–12 -> 3 guruh      13–20 -> 4 guruh
Ishtirokchilar tasodifiy aralashtiriladi va guruhlarga navbat bilan taqsimlanadi
(guruhlar farqi ≤ 1 kishi). Har guruh 1 doira (har kim har kim bilan 1 marta).
Tur raqami barcha guruhlar uchun UMUMIY — tashkilotchi bitta muddat belgilaydi.
Toq sonli guruhda har turda 1 kishi dam oladi (schedule._generate_round_robin_pairs).
"""

import logging
import random

from models import get_connection
from pt_core import PT_MAX_PLAYERS, PT_MIN_PLAYERS, STATUS_RECRUITING, STATUS_RUNNING
from schedule import _generate_round_robin_pairs

logger = logging.getLogger(__name__)

GROUP_LABELS = "ABCD"


def pt_group_count(n_players: int) -> int:
    """Ishtirokchilar soniga qarab guruhlar soni (≤ 4)."""
    if n_players <= 8:
        return 2
    if n_players <= 12:
        return 3
    return 4


def pt_split_groups(player_ids: list[int], rng: random.Random | None = None) -> dict[str, list[int]]:
    """Aralashtirib, guruhlarga navbat bilan taqsimlaydi: {'A': [...], 'B': [...]}."""
    ids = player_ids[:]
    (rng or random).shuffle(ids)
    g = pt_group_count(len(ids))
    groups = {GROUP_LABELS[i]: [] for i in range(g)}
    for i, uid in enumerate(ids):
        groups[GROUP_LABELS[i % g]].append(uid)
    return groups


def pt_build_group_schedule(groups: dict[str, list[int]]) -> list[tuple[str, int, int, int]]:
    """[(guruh, tur, player1, player2), ...] — har guruh 1 doira, tur raqamlari umumiy."""
    out = []
    for label, ids in groups.items():
        for rnd, pairs in enumerate(_generate_round_robin_pairs(ids), start=1):
            for p1, p2 in pairs:
                out.append((label, rnd, p1, p2))
    return out


def pt_start_tournament(tid: int, owner_id: int) -> tuple[bool, str | dict]:
    """
    Tashkilotchi turnirni boshlaydi: pending so'rovlar o'chiriladi, qur'a, o'yinlar.
    Sabablar: not_found, not_owner, not_recruiting, not_enough_players, too_many_players.
    1-tur ochiladi (muddatsiz — tashkilotchi belgilaydi).
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT owner_user_id, status, name FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        reason = None
        if not t:
            reason = "not_found"
        elif t["owner_user_id"] != owner_id:
            reason = "not_owner"
        elif t["status"] != STATUS_RECRUITING:
            reason = "not_recruiting"
        players = []
        if not reason:
            cursor.execute("SELECT user_id FROM pt_members WHERE tournament_id = ? AND status = 'approved'",
                           (tid,))
            players = [r["user_id"] for r in cursor.fetchall()]
            if len(players) < PT_MIN_PLAYERS:
                reason = "not_enough_players"
            elif len(players) > PT_MAX_PLAYERS:
                reason = "too_many_players"
        if reason:
            cursor.execute("ROLLBACK")
            return False, reason

        groups = pt_split_groups(players)
        schedule = pt_build_group_schedule(groups)
        total_rounds = max(r for _, r, _, _ in schedule)

        cursor.execute("DELETE FROM pt_members WHERE tournament_id = ? AND status = 'pending'", (tid,))
        for label, ids in groups.items():
            cursor.executemany(
                "UPDATE pt_members SET group_label = ? WHERE tournament_id = ? AND user_id = ?",
                [(label, tid, uid) for uid in ids])
        cursor.executemany(
            "INSERT INTO pt_matches (tournament_id, stage, group_label, round, player1_id, player2_id) "
            "VALUES (?, 'group', ?, ?, ?, ?)",
            [(tid, label, rnd, p1, p2) for label, rnd, p1, p2 in schedule])
        cursor.execute(
            "UPDATE pt_tournaments SET status = ?, current_round = 1, total_rounds = ?, "
            "round_deadline = NULL, started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?", (STATUS_RUNNING, total_rounds, tid))
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_start_tournament: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
    logger.info("PT #%s boshlandi: %s ishtirokchi, %s guruh, %s o'yin, %s tur",
                tid, len(players), len(groups), len(schedule), total_rounds)
    return True, {"groups": {k: len(v) for k, v in groups.items()},
                  "matches": len(schedule), "total_rounds": total_rounds, "name": t["name"]}
