"""
queries_wc_admin.py — WC admin amallari: fix/set-score/reset, o'yinchini olib tashlash, jadval tuzatish.

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from models import get_connection
from queries_leagues import _tournament_now
from queries_wc import wc_count_group_players, wc_get_user_registration, wc_set_group_draw_date
from queries_wc_matches import wc_get_match_by_id
from queries_wc_playoff import wc_playoff_advance_winner


def wc_admin_fix_confirmed_match(match_id: int, score1: int, score2: int) -> tuple[bool, str]:
    """
    WC admin allaqachon 'confirmed' bo'lgan WC matchning noto'g'ri natijasini
    qo'lda tuzatadi. Liga admin_fix_confirmed_match naqshiga mos, wc_matches uchun.

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "match_not_found", "wrong_status"
    """
    match = wc_get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"

    if match["status"] != "confirmed":
        return False, "wrong_status"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE wc_matches SET score1 = ?, score2 = ? WHERE id = ?",
        (score1, score2, match_id),
    )
    conn.commit()
    conn.close()
    return True, "ok"


def wc_admin_set_score(match_id: int, score1: int, score2: int, is_playoff: int = 0) -> tuple[bool, str]:
    """
    WC admin har qanday holatdagi (pending/awaiting/confirmed) WC matchning
    natijasini to'g'ri songa o'zgartiradi va statusni 'confirmed' qiladi.
    is_playoff=0 → wc_matches (guruh), is_playoff=1 → wc_playoff_matches (play-off).
    O'yinchilar o'ynamasdan noto'g'ri kiritgan natijani admin tuzatishi uchun.

    Reyting dinamik (wc_matches'dan hisoblanadi), shuning uchun avtomat yangilanadi.

    Qaytaradi: (success, reason). Sabablar: ok / match_not_found
    """
    table = "wc_playoff_matches" if is_playoff else "wc_matches"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id FROM {table} WHERE id = ?", (match_id,))
    if cursor.fetchone() is None:
        conn.close()
        return False, "match_not_found"

    cursor.execute(
        f"UPDATE {table} SET score1 = ?, score2 = ?, status = 'confirmed' WHERE id = ?",
        (score1, score2, match_id),
    )
    conn.commit()
    conn.close()

    # Play-off bo'lsa — g'olibni keyingi bosqichga o'tkazamiz
    # (wc_playoff_confirm_result bilan bir xil oqim; admin tasdig'ida ham ishlashi shart)
    if is_playoff:
        wc_playoff_advance_winner(match_id)

    return True, "ok"


def wc_admin_reset_match(match_id: int, is_playoff: int = 0) -> tuple[bool, str]:
    """
    WC admin noto'g'ri kiritilgan natijani BEKOR qiladi: skorni tozalaydi va
    o'yinni qayta 'pending' (— : —) holatiga qaytaradi. O'yinchilar qaytadan
    to'g'ri natija kiritishi mumkin bo'ladi.
    is_playoff=0 → wc_matches (guruh), is_playoff=1 → wc_playoff_matches (play-off).

    Qaytaradi: (success, reason). Sabablar: ok / match_not_found / already_pending
    """
    table = "wc_playoff_matches" if is_playoff else "wc_matches"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT status, score1 FROM {table} WHERE id = ?", (match_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False, "match_not_found"

    r = dict(row)
    if r["status"] == "pending" and r["score1"] is None:
        conn.close()
        return False, "already_pending"

    cursor.execute(
        f"UPDATE {table} SET score1 = NULL, score2 = NULL, submitted_by = NULL, status = 'pending' WHERE id = ?",
        (match_id,),
    )
    conn.commit()
    conn.close()
    return True, "ok"


def wc_admin_remove_player(user_id: int) -> tuple[bool, str]:
    """
    WC admin o'yinchini World Cup ro'yxatidan chiqaradi — FAQAT guruh hali
    to'lmagan (o'yinlar yaratilmagan) bo'lsa. O'yinlar boshlangan bo'lsa
    chiqarish guruh jadvalini buzadi, shuning uchun rad etiladi.

    Qaytaradi: (success, reason)
    Sabablar: ok / not_registered / group_started (o'yinlar boshlangan)
    """
    reg = wc_get_user_registration(user_id)
    if reg is None:
        return False, "not_registered"

    from wc_schedule import wc_group_has_matches
    if wc_group_has_matches(reg["group_letter"]):
        return False, "group_started"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM wc_registrations WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True, "ok"


def wc_get_all_players() -> list[dict]:
    """
    Barcha WC ishtirokchilari (admin paneli uchun). Har biriga nickname,
    username, guruh, jamoa qo'shiladi.
    Format: [{user_id, telegram_id, nickname, username, group_letter, team_name}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT w.user_id, u.telegram_id, u.nickname, u.username,
               w.group_letter, w.team_name
        FROM wc_registrations w
        JOIN users u ON u.id = w.user_id
        ORDER BY w.group_letter, w.team_name
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def wc_fix_missing_schedules() -> dict:
    """
    Admin uchun: barcha to'lgan (4 jamoa) lekin o'yinlari yaratilmagan YOKI
    o'yinlari to'liq bo'lmagan WC guruhlarini topib, jadval (round-robin)
    generatsiya qiladi. Bug tuzatish uchun.

    4 jamoali guruhda aniq 6 o'yin bo'lishi kerak (round-robin). Agar guruh
    to'lgan-u, o'yinlar yo'q yoki 6 tadan kam bo'lsa — eski (chala) o'yinlar
    o'chiriladi va qayta to'liq yaratiladi.

    Qaytaradi: {fixed: [...], skipped_not_full: [...], already_ok: [...]}
    """
    from wc_data import WC_GROUP_LETTERS, WC_TEAMS_PER_GROUP
    from wc_schedule import (
        wc_group_has_matches, wc_get_group_player_ids,
        generate_wc_group_schedule, wc_delete_group_matches,
    )

    # 4 jamoali round-robin: C(4,2) = 6 o'yin
    expected_matches = WC_TEAMS_PER_GROUP * (WC_TEAMS_PER_GROUP - 1) // 2

    fixed = []
    skipped_not_full = []
    already_ok = []

    for letter in WC_GROUP_LETTERS:
        players = wc_count_group_players(letter)
        if players < WC_TEAMS_PER_GROUP:
            skipped_not_full.append(letter)
            continue

        # Guruhda nechta o'yin bor?
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM wc_matches WHERE group_letter = ?",
            (letter,),
        )
        match_count = cursor.fetchone()["cnt"]
        conn.close()

        if match_count == expected_matches:
            already_ok.append(letter)
            continue

        # O'yin yo'q yoki chala (6 tadan kam/ko'p) — eskisini tozalab qayta yaratamiz
        if match_count > 0:
            wc_delete_group_matches(letter)
        player_ids = wc_get_group_player_ids(letter)
        generate_wc_group_schedule(letter, player_ids)
        wc_set_group_draw_date(letter)
        fixed.append(letter)

    return {
        "fixed": fixed,
        "skipped_not_full": skipped_not_full,
        "already_ok": already_ok,
    }


def wc_start_all_today() -> dict:
    """
    Admin uchun: o'yinlari yaratilgan barcha WC guruhlarning draw_date'ini
    HOZIRGI vaqtga qo'yadi — ya'ni bugundan start beradi. Shunda matchday-lock
    bugundan boshlanadi: bugun matchday 1..MATCHDAYS_PER_UNLOCK ochiq, keyingi
    turlar har kun 23:30 (Toshkent) da ochiladi (liga kabi).

    Faqat o'yinlari bor (to'lgan) guruhlarga ta'sir qiladi.
    Qaytaradi: {started: [guruh harflari]}
    """
    from wc_data import WC_GROUP_LETTERS
    from wc_schedule import wc_group_has_matches

    started = []
    now = _tournament_now()
    for letter in WC_GROUP_LETTERS:
        if wc_group_has_matches(letter):
            wc_set_group_draw_date(letter, now)
            started.append(letter)
    return {"started": started}
