"""
pt_draw.py — SHAXSIY turnir qur'asi (2026-10-02, 4-bosqich).

Admin qarori (2026-10-03, 128 kishigacha): guruhlar 4 KISHILIK va DOIM TO'LIQ.
Boshlash faqat ishtirokchilar soni 4 ga karrali bo'lganda (pt_core.can_start_with):
8 -> 2 guruh, 12 -> 3, ... 128 -> 32. Har guruh 3 tur, har kim 3 o'yin.
Ishtirokchilar tasodifiy aralashtiriladi va guruhlarga navbat bilan taqsimlanadi
(guruhlar farqi ≤ 1 kishi). Har guruh 1 doira (har kim har kim bilan 1 marta).
Guruh nomlari: A..Z, keyin AA, AB, ... (32 guruhgacha).
Tur raqami barcha guruhlar uchun UMUMIY — tashkilotchi bitta muddat belgilaydi.
Toq sonli guruhda har turda 1 kishi dam oladi (schedule._generate_round_robin_pairs).
"""

import logging
import random

from models import get_connection
from pt_core import PT_GROUP_SIZE, PT_MAX_PLAYERS, STATUS_RECRUITING, STATUS_RUNNING, is_manager, start_block
from pt_formats import FMT_LEAGUE, TABLE_LABEL, club_league, is_single_table, split_leagues, swiss_rounds, teams_for, uses_teams
from schedule import _generate_round_robin_pairs

logger = logging.getLogger(__name__)

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def group_label(i: int) -> str:
    """0 -> 'A', 25 -> 'Z', 26 -> 'AA', 27 -> 'AB', ..."""
    return _LETTERS[i] if i < 26 else _LETTERS[i // 26 - 1] + _LETTERS[i % 26]


def pt_group_count(n_players: int) -> int:
    """Guruhlar soni: n / PT_GROUP_SIZE (boshlashda n 4 ga karrali — guruhlar to'liq), kamida 2."""
    return max(2, -(-n_players // PT_GROUP_SIZE))


def pt_split_groups(player_ids: list[int], rng: random.Random | None = None) -> dict[str, list[int]]:
    """Aralashtirib, guruhlarga navbat bilan taqsimlaydi: {'A': [...], 'B': [...]}."""
    ids = player_ids[:]
    (rng or random).shuffle(ids)
    g = pt_group_count(len(ids))
    groups = {group_label(i): [] for i in range(g)}
    for i, uid in enumerate(ids):
        groups[group_label(i % g)].append(uid)
    return groups


def pt_build_group_schedule(groups: dict[str, list[int]], legs: int = 1) -> list[tuple[str, int, int, int]]:
    """[(guruh, tur, player1, player2), ...] — har guruh 1 doira (legs=2: 2-doira uy/mehmon almashgan),
    tur raqamlari umumiy."""
    out = []
    for label, ids in groups.items():
        rounds = _generate_round_robin_pairs(ids)
        if legs == 2:
            rounds = rounds + [[(b, a) for a, b in r] for r in rounds]
        for rnd, pairs in enumerate(rounds, start=1):
            for p1, p2 in pairs:
                out.append((label, rnd, p1, p2))
    return out


def pt_build_table_schedule(fmt: str, ids: list[int], legs: int = 1,
                            rng: random.Random | None = None, label: str = TABLE_LABEL) -> list[tuple[str, int, int, int]]:
    """
    2026-10-07: yagona jadval (guruhsiz) — [(TABLE_LABEL, tur, player1, player2), ...].
      league: har kim har kim bilan 1 yoki 2 doira (2-doirada uy/mehmon almashadi, turlar davomi).
      cl/el : Swiss — doira usulining birinchi min(8, n-1) turi (aralashtirilgan tartibda):
              har turda hamma o'ynaydi, hech kim bir raqib bilan ikki marta uchrashmaydi.
    """
    ids = ids[:]
    (rng or random).shuffle(ids)
    rounds = _generate_round_robin_pairs(ids)
    if fmt == FMT_LEAGUE:
        if legs == 2:
            rounds = rounds + [[(b, a) for a, b in r] for r in rounds]
    else:
        rounds = rounds[:swiss_rounds(len(ids))]
    return [(label, rnd, p1, p2) for rnd, pairs in enumerate(rounds, start=1) for p1, p2 in pairs]


def assign_missing_teams(cursor, tid: int, fmt: str, league: str | None, members: list[dict],
                         rng: random.Random | None = None) -> list[tuple[int, str]] | None:
    """
    2026-10-08: qur'ada klub/jamoa tanlamagan ishtirokchilarga bo'sh klub TASODIFIY beriladi
    (admin so'rovi: tashkilotchi o'zi klub tanlamagan, joylar to'lgan — qur'a to'xtab qolmasin).
    Liga formatida sig'im = klublar soni, shuning uchun bo'sh klublar aynan yetadi.
    members (o'zgaradi: team_name to'ldiriladi). Qaytaradi [(user_id, team)] yoki None (klub yetmasa).
    """
    missing = [m for m in members if not m.get("team_name")]
    if not missing:
        return []
    taken = {m["team_name"] for m in members if m.get("team_name")}
    free = [x for x in teams_for(fmt, league) if x not in taken]
    if len(free) < len(missing):
        return None
    (rng or random).shuffle(free)
    out = []
    for m, team in zip(missing, free):
        m["team_name"] = team
        cursor.execute("UPDATE pt_members SET team_name = ? WHERE tournament_id = ? AND user_id = ?",
                       (team, tid, m["user_id"]))
        out.append((m["user_id"], team))
    logger.info("PT #%s: %s kishiga klub qur'ada berildi: %s", tid, len(out), out)
    return out


def pt_start_tournament(tid: int, owner_id: int) -> tuple[bool, str | dict]:
    """
    Tashkilotchi turnirni boshlaydi: pending so'rovlar o'chiriladi, qur'a, o'yinlar.
    Sabablar: not_found, not_owner, not_recruiting, not_enough_players, not_multiple, too_many_players,
    2026-10-07: not_even (ChL/YeL), league_not_full (liga). 2026-10-08: klub tanlamaganlarga bo'sh klub beriladi.
    1-tur ochiladi (muddatsiz — tashkilotchi belgilaydi).
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT owner_user_id, status, name, max_players, format, league_name, legs "
                       "FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        reason = None
        if not t:
            reason = "not_found"
        elif not is_manager(cursor, tid, owner_id, t["owner_user_id"]):   # tashkilotchi yoki admin
            reason = "not_owner"
        elif t["status"] != STATUS_RECRUITING:
            reason = "not_recruiting"
        players = []
        if not reason:
            cursor.execute("SELECT user_id, status, team_name FROM pt_members WHERE tournament_id = ? "
                           "AND status = 'approved'", (tid,))
            members = [dict(r) for r in cursor.fetchall()]
            players = [m["user_id"] for m in members]
            if len(players) > min(t["max_players"], PT_MAX_PLAYERS):
                reason = "too_many_players"
            else:   # formatga qarab: not_enough_players | not_multiple | not_even | league_not_full | teams_missing
                reason = start_block(dict(t), members)
        if reason:
            cursor.execute("ROLLBACK")
            return False, reason

        fmt = t["format"] or "classic"
        cursor.execute("DELETE FROM pt_members WHERE tournament_id = ? AND status = 'pending'", (tid,))   # ularning klubi bo'shaydi
        auto = assign_missing_teams(cursor, tid, fmt, t["league_name"], members) if uses_teams(fmt) else []
        if auto is None:                               # bo'sh klub yetmadi (bo'lmasligi kerak — sig'im = klublar soni)
            cursor.execute("ROLLBACK")
            return False, "teams_missing"
        if fmt == FMT_LEAGUE:                          # liga: har tanlangan liga — alohida jadval (guruh = liga nomi)
            groups = {lg: [] for lg in split_leagues(t["league_name"])}
            for mbr in members:
                groups.setdefault(club_league(mbr["team_name"], t["league_name"]) or TABLE_LABEL, []).append(mbr["user_id"])
            schedule = [row for lg, ids in groups.items()
                        for row in pt_build_table_schedule(fmt, ids, t["legs"] or 1, label=lg)]
        elif is_single_table(fmt):                     # ChL / YeL — yagona jadval
            groups = {TABLE_LABEL: players}
            schedule = pt_build_table_schedule(fmt, players, t["legs"] or 1)
        else:                                          # erkin / JCh — 4 kishilik guruhlar (erkin: 1 yoki 2 doira)
            groups = pt_split_groups(players)
            schedule = pt_build_group_schedule(groups, t["legs"] or 1)
        total_rounds = max(r for _, r, _, _ in schedule)

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
                  "matches": len(schedule), "total_rounds": total_rounds, "name": t["name"], "format": fmt,
                  "auto_teams": len(auto)}
