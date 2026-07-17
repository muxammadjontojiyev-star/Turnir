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
    DIV_POINTS_WIN, DIV_POINTS_DRAW, DIV_POINTS_LOSS, DIV_START_RATING,
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


# 2026-07-16: 17:00 "ro'yxat ochildi" e'loni — kuniga BIR MARTA yuborilishi
# uchun idempotentlik belgilari (div_state.reg_announced_at, qoida #38).

def div_is_reg_announced(day: str | None = None) -> bool:
    """Bugungi "ro'yxat ochildi" e'loni yuborilganmi?"""
    day = day or _today()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT reg_announced_at FROM div_state WHERE day = ?", (day,))
        row = cursor.fetchone()
        return bool(row and row["reg_announced_at"])
    finally:
        conn.close()


def div_mark_reg_announced(day: str | None = None) -> None:
    """Bugungi e'lonni "yuborildi" deb belgilaydi (takror yuborilmasin)."""
    day = day or _today()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO div_state (day, reg_announced_at) VALUES (?, datetime('now')) "
            "ON CONFLICT(day) DO UPDATE SET reg_announced_at = datetime('now')",
            (day,),
        )
        conn.commit()
    finally:
        conn.close()


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
                           "wins": 0, "draws": 0, "losses": 0,
                           # To'p urarlar tabi uchun: urgan/o'tkazgan gollar
                           "goals_for": 0, "goals_against": 0}
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
        # Gol statistikasi (to'p urarlar): har kim o'z hisobidagi gollarni oladi
        a["goals_for"] += s1; a["goals_against"] += s2
        b["goals_for"] += s2; b["goals_against"] += s1
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
    for p in table:
        # Umumiy ball: hamma DIV_START_RATING (1500) dan boshlaydi, o'yin achkolari
        # (+15/+10/-10) shunga qo'shiladi/ayriladi (profilda ko'rsatiladi).
        p["rating"] = DIV_START_RATING + p["points"]
        p["goal_diff"] = p["goals_for"] - p["goals_against"]
    table.sort(key=lambda p: p["points"], reverse=True)
    return table


def div_scorers() -> list[dict]:
    """
    "To'p urarlar" tabi: eng ko'p gol urgan ishtirokchilar.

    Gol = confirmed o'yinlarda ishtirokchining O'Z hisobidagi gollar yig'indisi
    (masalan 3:0 va 1:2 o'ynasa -> 3+1 = 4 gol). Manba div_rating() bilan bir xil
    (DRY, qoida #26) — bir xil o'yinlardan hisoblanadi.

    Saralash: gollar (ko'p) -> gol farqi -> o'yin soni (kam) -> achko.
    """
    rows = [p for p in div_rating() if p["goals_for"] > 0 or p["played"] > 0]
    rows.sort(key=lambda p: (-p["goals_for"], -p["goal_diff"],
                             p["played"], -p["points"]))
    return rows


# ============ ADMIN (bosh admin, Divizion tabidagi panel) ============

def div_admin_list_matches(day: str | None = None) -> list[dict]:
    """
    Kunlik BARCHA o'yinlar (har qanday status) — admin panel ro'yxati.
    day=None -> bugun. day='all' -> barcha kunlar (oxirgi 100 o'yin), shunda
    admin o'tgan kunlardagi (jumladan TASDIQLANGAN) natijalarni ham tuzatadi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    base = """
        SELECT m.*, u1.nickname AS player1_name, u1.username AS player1_username,
               u2.nickname AS player2_name, u2.username AS player2_username
        FROM div_matches m
        JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
    """
    if day == "all":
        cursor.execute(base + " ORDER BY m.day DESC, m.id DESC LIMIT 100")
    else:
        cursor.execute(base + " WHERE m.day = ? ORDER BY m.id", (day or _today(),))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def div_admin_set_result(match_id: int, score1: int, score2: int) -> tuple[bool, str]:
    """
    Admin natijani O'RNATADI/TUZATADI: istalgan statusdan to'g'ridan-to'g'ri
    'confirmed' ga o'tkazadi (noto'g'ri kiritilgan natijani ham qayta yozadi).
    Bye o'yinga (player2 NULL) hisob kiritilmaydi. Sabablar: ok, match_not_found,
    bye_match.
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
    Admin NATIJANI bekor qiladi: hisob tozalanadi, o'yin 'pending' ga qaytadi —
    ishtirokchilar natijani QAYTA kirita oladi (liga admin oqimi bilan bir xil).
    Bye o'yin (player2 NULL) bekor qilinmaydi. Sabablar: ok, match_not_found,
    bye_match.
    Eslatma: 23:30 avto-yopish kuniga bir marta ishlaydi (div_state.resolved_at);
    undan keyin bekor qilingan o'yin natijasini admin o'zi kiritadi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT player2_id FROM div_matches WHERE id = ?", (match_id,))
        m = cursor.fetchone()
        if m is None:
            return False, "match_not_found"
        if m["player2_id"] is None:
            return False, "bye_match"
        cursor.execute(
            "UPDATE div_matches SET status='pending', score1=NULL, score2=NULL, "
            "submitted_by=NULL WHERE id=?",
            (match_id,),
        )
        conn.commit()
        return True, "ok"
    finally:
        conn.close()


def div_admin_resolve_pending(match_id: int, accept: bool) -> tuple[bool, str]:
    """
    Katta hisob (admin_pending) bo'yicha admin qarori — liga admin oqimi kabi:
      accept=True  -> kiritilgan hisob tasdiqlanadi (confirmed)
      accept=False -> rad: hisob tozalanadi, pending (ishtirokchilar qayta kiritadi)
    Sabablar: ok, match_not_found, wrong_status.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT status FROM div_matches WHERE id = ?", (match_id,))
        m = cursor.fetchone()
        if m is None:
            return False, "match_not_found"
        if m["status"] != "admin_pending":
            return False, "wrong_status"
        if accept:
            cursor.execute(
                "UPDATE div_matches SET status='confirmed' WHERE id=?", (match_id,))
        else:
            cursor.execute(
                "UPDATE div_matches SET status='pending', score1=NULL, score2=NULL, "
                "submitted_by=NULL WHERE id=?", (match_id,))
        conn.commit()
        return True, "ok"
    finally:
        conn.close()


def div_my_stats(user_id: int) -> dict:
    """
    Foydalanuvchining Divizion shaxsiy statistikasi (profil sahifasi uchun):
      {wins, draws, losses, played, win_rate, points}
    win_rate = g'alaba / (g'alaba+durang+mag'lubiyat) * 100, butun foiz.
    Manba — confirmed div_matches (bye = g'alaba). div_rating bilan izchil (DRY).
    """
    for row in div_rating():
        if row["user_id"] == user_id:
            w, d, l = row["wins"], row["draws"], row["losses"]
            total = w + d + l
            win_rate = round(w / total * 100) if total else 0
            return {"wins": w, "draws": d, "losses": l, "played": row["played"],
                    "win_rate": win_rate, "points": row["points"],
                    # Umumiy ball = 1500 + achkolar (profilda ism yonida)
                    "rating": row["rating"],
                    "goals_for": row["goals_for"],
                    "goals_against": row["goals_against"]}
    # Hali o'ynamagan: boshlang'ich ball
    return {"wins": 0, "draws": 0, "losses": 0, "played": 0,
            "win_rate": 0, "points": 0, "rating": DIV_START_RATING,
            "goals_for": 0, "goals_against": 0}


def div_my_matches(user_id: int, limit: int = 50) -> list[dict]:
    """
    Foydalanuvchining barcha Divizion o'yinlari tarixi (profil "O'yinlarim").
    Har o'yin: {id, day, is_bye, my_score, opp_score, opp_name, status}.
    Yangi kun birinchi (day DESC, id DESC).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.id, m.day, m.player1_id, m.player2_id, m.score1, m.score2, m.status,
               u1.nickname AS p1_name, u1.username AS p1_username,
               u2.nickname AS p2_name, u2.username AS p2_username
        FROM div_matches m
        JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
        WHERE m.player1_id = ? OR m.player2_id = ?
        ORDER BY m.day DESC, m.id DESC
        LIMIT ?
        """,
        (user_id, user_id, limit),
    )
    out = []
    for r in cursor.fetchall():
        d = dict(r)
        is_bye = d["player2_id"] is None
        if d["player1_id"] == user_id:
            my, opp = d["score1"], d["score2"]
            opp_name, opp_username, opp_uid = d["p2_name"], d["p2_username"], d["player2_id"]
        else:
            my, opp = d["score2"], d["score1"]
            opp_name, opp_username, opp_uid = d["p1_name"], d["p1_username"], d["player1_id"]
        out.append({
            "id": d["id"], "day": d["day"], "is_bye": is_bye,
            "my_score": my, "opp_score": opp,
            "opp_name": opp_name if not is_bye else None,
            "opp_username": opp_username if not is_bye else None,
            "opp_user_id": opp_uid if not is_bye else None,
            "status": d["status"],
        })
    conn.close()
    return out


def div_admin_match_info(match_id: int) -> dict | None:
    """
    O'yin haqida qisqa ma'lumot (admin "Match ID orqali tuzatish" formasi uchun):
    ikkala o'yinchi, joriy hisob, status, kun. Topilmasa None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.id, m.day, m.score1, m.score2, m.status,
               m.player1_id, m.player2_id,
               u1.nickname AS player1_name, u1.username AS player1_username,
               u2.nickname AS player2_name, u2.username AS player2_username
        FROM div_matches m
        JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
        WHERE m.id = ?
        """,
        (match_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["is_bye"] = d["player2_id"] is None
    return d


def div_registration_days(user_id: int, month: str | None = None) -> dict:
    """
    Foydalanuvchi qaysi kunlari Divizionga ro'yxatdan o'tgan (profil kalendari).

    month: "YYYY-MM" (None -> joriy oy, Toshkent vaqti bo'yicha).
    Qaytaradi:
      {
        "month": "2026-07",           # ko'rsatilayotgan oy
        "today": "2026-07-13",        # bugungi kun (turnir vaqti bo'yicha)
        "days": ["2026-07-11", ...],  # SHU OYDA ro'yxatdan o'tgan kunlar
      }
    Kalendarda: days ichidagi kunlar yashil, qolganlari rangsiz.
    """
    now = _tournament_now()
    if not month:
        month = now.strftime("%Y-%m")

    conn = get_connection()
    cursor = conn.cursor()
    # day formati "YYYY-MM-DD" -> oy bo'yicha prefiks qidiruvi (parametrlashtirilgan)
    cursor.execute(
        "SELECT day FROM div_registrations "
        "WHERE user_id = ? AND day LIKE ? ORDER BY day",
        (user_id, f"{month}-%"),
    )
    days = [r["day"] for r in cursor.fetchall()]
    conn.close()

    return {"month": month, "today": now.strftime("%Y-%m-%d"), "days": days}
