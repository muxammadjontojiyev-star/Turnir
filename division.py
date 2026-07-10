"""
division.py — Divizion (3-tab) asosiy mantig'i.

Kunlik tsikl (Toshkent vaqti, _tournament_now):
  17:00–19:00  ro'yxatdan o'tish oynasi (div_register)
  19:00+       qur'a: ro'yxatdan o'tganlar tasodifiy juftlanadi (div_pair_day);
               toq qolgan ishtirokchiga AVTOMATIK G'ALABA (player2=NULL, confirmed).
               Har bir ishtirokchiga qur'a natijasi telegram orqali yuboriladi
               (scheduler chaqiradi, notify.py).
  23:30        deadline: o'ynalmagan juftlik 0:0 durang, bir tomon kiritgani
               tasdiqlanadi (div_auto_resolve_day).

Achko (config): g'alaba +15, durang +10, mag'lubiyat -10. Toq (bye) = g'alaba (+15).
Reyting achkosi manba-haqiqatdan (confirmed div_matches) har safar hisoblanadi —
ikki marta yozilish xavfi yo'q (qoida #38).
"""

import logging
import random

from models import get_connection
from config import (
    DIV_REG_START_HOUR, DIV_REG_END_HOUR,
    DIV_DEADLINE_HOUR, DIV_DEADLINE_MINUTE,
    DIV_POINTS_WIN, DIV_POINTS_DRAW, DIV_POINTS_LOSS,
)
from queries_leagues import _tournament_now
from queries_matches import _result_status_for

logger = logging.getLogger(__name__)


def _today() -> str:
    return _tournament_now().date().isoformat()


def div_registration_window() -> dict:
    """Ro'yxat oynasi holati: {open: bool, day, now_hhmm}."""
    now = _tournament_now()
    is_open = DIV_REG_START_HOUR <= now.hour < DIV_REG_END_HOUR
    return {"open": is_open, "day": now.date().isoformat(),
            "now": now.strftime("%H:%M")}


def div_register(user_id: int, telegram_id: int, nickname: str) -> tuple[bool, str]:
    """
    Bugungi ro'yxatga yozadi. Sabablar: ok, window_closed, already_registered.
    INSERT OR IGNORE + UNIQUE(day, telegram_id) — race-himoyali (qoida #38).
    """
    win = div_registration_window()
    if not win["open"]:
        return False, "window_closed"
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO div_registrations (day, telegram_id, user_id, nickname) "
            "VALUES (?, ?, ?, ?)",
            (win["day"], telegram_id, user_id, nickname),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return False, "already_registered"
        return True, "ok"
    finally:
        conn.close()


def div_day_registrations(day: str | None = None) -> list[dict]:
    """Kunlik ro'yxat (asosiy sahifa uchun)."""
    day = day or _today()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT r.telegram_id, r.user_id, r.nickname, u.username "
        "FROM div_registrations r LEFT JOIN users u ON u.id = r.user_id "
        "WHERE r.day = ? ORDER BY r.id",
        (day,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def div_pair_day(day: str | None = None) -> dict | None:
    """
    Kunlik qur'a: ro'yxatdagilarni tasodifiy juftlaydi, toq qolganga bye (avto
    g'alaba). Idempotent: div_state.paired_at belgisi + BEGIN IMMEDIATE.

    Qaytaradi: {"day", "pairs": [(tg1, tg2|None), ...], "matches": n} yoki
    None (allaqachon qur'a qilingan / ro'yxat bo'sh).
    """
    day = day or _today()
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT paired_at FROM div_state WHERE day = ?", (day,))
        st = cursor.fetchone()
        if st and st["paired_at"]:
            cursor.execute("ROLLBACK")
            return None

        cursor.execute(
            "SELECT telegram_id, user_id FROM div_registrations WHERE day = ?", (day,)
        )
        regs = [dict(r) for r in cursor.fetchall()]
        if not regs:
            cursor.execute("ROLLBACK")
            return None

        random.shuffle(regs)
        pairs = []
        created = 0
        i = 0
        while i + 1 < len(regs):
            a, b = regs[i], regs[i + 1]
            cursor.execute(
                "INSERT INTO div_matches (day, player1_id, player2_id, status) "
                "VALUES (?, ?, ?, 'pending')",
                (day, a["user_id"], b["user_id"]),
            )
            pairs.append((a["telegram_id"], b["telegram_id"]))
            created += 1
            i += 2
        if i < len(regs):  # toq qolgan — avtomatik g'alaba
            bye = regs[i]
            cursor.execute(
                "INSERT INTO div_matches (day, player1_id, player2_id, status) "
                "VALUES (?, ?, NULL, 'confirmed')",
                (day, bye["user_id"],),
            )
            pairs.append((bye["telegram_id"], None))
            created += 1

        cursor.execute(
            "INSERT INTO div_state (day, paired_at) VALUES (?, datetime('now')) "
            "ON CONFLICT(day) DO UPDATE SET paired_at = datetime('now')",
            (day,),
        )
        cursor.execute("COMMIT")
        logger.info("Divizion qur'a: %s kuni %d o'yin (%d ishtirokchi).",
                    day, created, len(regs))
        return {"day": day, "pairs": pairs, "matches": created}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def div_get_my_match(user_id: int, day: str | None = None) -> dict | None:
    """
    Foydalanuvchining bugungi o'yini (raqib useri/username bilan — profil sahifasi).
    bye bo'lsa opponent maydonlari None, status 'confirmed' (avto g'alaba).
    """
    day = day or _today()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.*, u1.nickname AS player1_name, u1.username AS player1_username,
               u2.nickname AS player2_name, u2.username AS player2_username,
               u1.telegram_id AS player1_tg, u2.telegram_id AS player2_tg
        FROM div_matches m
        JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
        WHERE m.day = ? AND (m.player1_id = ? OR m.player2_id = ?)
        """,
        (day, user_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    m = dict(row)
    if m["player1_id"] == user_id:
        m["opponent"] = {"user_id": m["player2_id"], "nickname": m["player2_name"],
                         "username": m["player2_username"], "telegram_id": m["player2_tg"]}
        m["is_bye"] = m["player2_id"] is None
    else:
        m["opponent"] = {"user_id": m["player1_id"], "nickname": m["player1_name"],
                         "username": m["player1_username"], "telegram_id": m["player1_tg"]}
        m["is_bye"] = False
    return m


def div_submit_result(match_id: int, score1: int, score2: int,
                      submitted_by: int) -> tuple[bool, str]:
    """Liga/WC/ChL bilan bir xil oqim (qoida #10). Bye o'yiniga kiritilmaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM div_matches WHERE id = ?", (match_id,))
    m = cursor.fetchone()
    conn.close()
    if m is None:
        return False, "match_not_found"
    m = dict(m)
    if m["player2_id"] is None:
        return False, "bye_match"
    if submitted_by not in (m["player1_id"], m["player2_id"]):
        return False, "not_participant"
    if m["status"] != "pending":
        return False, "already_submitted"

    new_status = _result_status_for(score1, score2)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE div_matches SET score1=?, score2=?, submitted_by=?, status=? WHERE id=?",
        (score1, score2, submitted_by, new_status, match_id),
    )
    conn.commit()
    conn.close()
    return True, ("ok_admin_pending" if new_status == "admin_pending" else "ok")


def div_confirm_or_reject(match_id: int, action: str,
                          confirmed_by: int) -> tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM div_matches WHERE id = ?", (match_id,))
    m = cursor.fetchone()
    if m is None:
        conn.close()
        return False, "match_not_found"
    m = dict(m)
    if m["status"] != "awaiting_confirmation":
        conn.close()
        return False, "wrong_status"
    if confirmed_by == m["submitted_by"] or \
       confirmed_by not in (m["player1_id"], m["player2_id"]):
        conn.close()
        return False, "not_opponent"
    if action not in ("confirm", "reject"):
        conn.close()
        return False, "invalid_action"
    if action == "confirm":
        cursor.execute("UPDATE div_matches SET status='confirmed' WHERE id=?", (match_id,))
    else:
        cursor.execute(
            "UPDATE div_matches SET status='pending', score1=NULL, score2=NULL, "
            "submitted_by=NULL WHERE id=?", (match_id,))
    conn.commit()
    conn.close()
    return True, "ok"


def div_auto_resolve_day(day: str | None = None) -> dict:
    """
    Deadline (23:30) o'tgach: pending -> 0:0 durang, awaiting -> tasdiq.
    Idempotent (div_state.resolved_at). Qaytaradi: {"pending": n, "awaiting": n}.
    """
    day = day or _today()
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT resolved_at FROM div_state WHERE day = ?", (day,))
        st = cursor.fetchone()
        if st and st["resolved_at"]:
            cursor.execute("ROLLBACK")
            return {"pending": 0, "awaiting": 0, "already": True}

        cursor.execute(
            "UPDATE div_matches SET score1=0, score2=0, status='confirmed' "
            "WHERE day=? AND status='pending' AND player2_id IS NOT NULL", (day,))
        pending = cursor.rowcount
        cursor.execute(
            "UPDATE div_matches SET status='confirmed' "
            "WHERE day=? AND status='awaiting_confirmation'", (day,))
        awaiting = cursor.rowcount
        cursor.execute(
            "INSERT INTO div_state (day, resolved_at) VALUES (?, datetime('now')) "
            "ON CONFLICT(day) DO UPDATE SET resolved_at = datetime('now')", (day,))
        cursor.execute("COMMIT")
        return {"pending": pending, "awaiting": awaiting, "already": False}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def div_rating() -> list[dict]:
    """
    Umumiy Divizion reytingi: barcha kunlar bo'yicha confirmed o'yinlardan
    achko yig'indisi (+15/+10/-10; bye=+15). Kamayish tartibida.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT m.player1_id, m.player2_id, m.score1, m.score2 "
        "FROM div_matches m WHERE m.status = 'confirmed'"
    )
    matches = cursor.fetchall()

    points: dict[int, dict] = {}

    def ensure(uid):
        if uid not in points:
            points[uid] = {"user_id": uid, "points": 0, "played": 0,
                           "wins": 0, "draws": 0, "losses": 0}
        return points[uid]

    for m in matches:
        p1, p2 = m["player1_id"], m["player2_id"]
        a = ensure(p1)
        if p2 is None:  # bye — avtomatik g'alaba
            a["points"] += DIV_POINTS_WIN
            a["played"] += 1
            a["wins"] += 1
            continue
        b = ensure(p2)
        s1, s2 = m["score1"] or 0, m["score2"] or 0
        a["played"] += 1; b["played"] += 1
        if s1 > s2:
            a["points"] += DIV_POINTS_WIN; a["wins"] += 1
            b["points"] += DIV_POINTS_LOSS; b["losses"] += 1
        elif s2 > s1:
            b["points"] += DIV_POINTS_WIN; b["wins"] += 1
            a["points"] += DIV_POINTS_LOSS; a["losses"] += 1
        else:
            a["points"] += DIV_POINTS_DRAW; a["draws"] += 1
            b["points"] += DIV_POINTS_DRAW; b["draws"] += 1

    if not points:
        conn.close()
        return []

    # Nicknamelar bitta so'rovda (qoida #24/#32)
    ids = list(points.keys())
    q = ",".join("?" * len(ids))
    cursor.execute(
        f"SELECT id, nickname, username, telegram_id FROM users WHERE id IN ({q})", ids)
    for r in cursor.fetchall():
        if r["id"] in points:
            points[r["id"]].update(nickname=r["nickname"], username=r["username"],
                                   telegram_id=r["telegram_id"])
    conn.close()

    table = list(points.values())
    table.sort(key=lambda p: p["points"], reverse=True)
    return table


# ============ ADMIN (bosh admin, Divizion tabidagi panel) ============

def div_admin_list_matches(day: str | None = None) -> list[dict]:
    """Kunlik BARCHA o'yinlar (har qanday status) — admin panel ro'yxati."""
    day = day or _today()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.*, u1.nickname AS player1_name, u2.nickname AS player2_name
        FROM div_matches m
        JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
        WHERE m.day = ? ORDER BY m.id
        """,
        (day,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def div_admin_set_result(match_id: int, score1: int, score2: int) -> tuple[bool, str]:
    """
    Admin natijani O'RNATADI/TUZATADI: istalgan statusdan to'g'ridan-to'g'ri
    'confirmed' ga o'tkazadi (noto'g'ri kiritilgan natijani ham qayta yozadi).
    Bye o'yinga (player2 NULL) hisob kiritilmaydi. Sabablar: ok, match_not_found,
    bye_match, cancelled.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT player2_id, status FROM div_matches WHERE id = ?", (match_id,))
        m = cursor.fetchone()
        if m is None:
            return False, "match_not_found"
        if m["player2_id"] is None:
            return False, "bye_match"
        if m["status"] == "cancelled":
            return False, "cancelled"
        cursor.execute(
            "UPDATE div_matches SET score1=?, score2=?, status='confirmed', "
            "submitted_by=NULL WHERE id=?",
            (score1, score2, match_id),
        )
        conn.commit()
        return True, "ok"
    finally:
        conn.close()


def div_admin_cancel_match(match_id: int) -> tuple[bool, str]:
    """
    Admin o'yinni BEKOR qiladi: status='cancelled', hisob tozalanadi.
    Bekor qilingan o'yin reytingga kirmaydi (div_rating faqat 'confirmed').
    Sabablar: ok, match_not_found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM div_matches WHERE id = ?", (match_id,))
        if cursor.fetchone() is None:
            return False, "match_not_found"
        cursor.execute(
            "UPDATE div_matches SET status='cancelled', score1=NULL, score2=NULL, "
            "submitted_by=NULL WHERE id=?",
            (match_id,),
        )
        conn.commit()
        return True, "ok"
    finally:
        conn.close()
