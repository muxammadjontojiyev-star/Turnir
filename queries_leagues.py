"""
queries_leagues.py — Ligalar CRUD, qur'a sanasi, natijalarni saqlash/tiklash, matchday reset/reopen.

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from datetime import datetime, timezone, timedelta
from models import get_connection
from config import (
    TOURNAMENT_TIMEZONE_OFFSET,
)


# ============ LEAGUES ============

def get_all_leagues() -> list[dict]:
    """Barcha ligalarni qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leagues")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_league_by_id(league_id: int) -> dict | None:
    """ID bo'yicha ligani qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leagues WHERE id = ?", (league_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def count_league_players(league_id: int) -> int:
    """Ligadagi ro'yxatdan o'tgan ishtirokchilar sonini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM registrations WHERE league_id = ?", (league_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"]


def get_taken_clubs(league_id: int) -> list[str]:
    """Shu ligada allaqachon band qilingan klub nomlari ro'yxatini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT club_name FROM registrations WHERE league_id = ? AND club_name IS NOT NULL",
        (league_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["club_name"] for row in rows]


def update_league_status(league_id: int, status: str) -> None:
    """Liga statusini yangilaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leagues SET status = ? WHERE id = ?", (status, league_id))
    conn.commit()
    conn.close()


def league_has_matches(league_id: int) -> bool:
    """Liga uchun allaqachon match (jadval) yaratilganmi — qur'a takror o'tkazilishini oldini olish uchun."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM matches WHERE league_id = ? LIMIT 1", (league_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def delete_league_matches(league_id: int) -> int:
    """
    Liga uchun barcha matchlarni o'chiradi (qayta qur'a uchun).

    ⚠️ DIQQAT: bu kiritilgan natijalarni ham o'chiradi. Faqat to'liq qayta qur'a
    (redraw) uchun ishlatiladi. last_notified_matchday ham 0 ga qaytariladi,
    chunki yangi jadvalda turlar yangidan ochiladi.

    Qaytaradi: o'chirilgan matchlar soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM matches WHERE league_id = ?", (league_id,))
    count = cursor.fetchone()["cnt"]
    cursor.execute("DELETE FROM matches WHERE league_id = ?", (league_id,))
    cursor.execute(
        "UPDATE leagues SET last_notified_matchday = 0 WHERE id = ?", (league_id,)
    )
    conn.commit()
    conn.close()
    return count


def get_played_results(league_id: int) -> list[dict]:
    """
    Liga uchun NATIJA kiritilgan matchlarni qaytaradi (qayta qur'ada saqlash uchun).

    Faqat score'i bor (confirmed/awaiting_confirmation/rejected) matchlar.
    Qaytaradi: [{player1_id, player2_id, score1, score2, submitted_by, status}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT player1_id, player2_id, score1, score2, submitted_by, status
        FROM matches
        WHERE league_id = ? AND score1 IS NOT NULL
        """,
        (league_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def restore_results_to_schedule(league_id: int, played: list[dict]) -> int:
    """
    Saqlangan natijalarni (get_played_results) yangi jadvalga ko'chiradi.

    Har bir saqlangan natija uchun yangi jadvaldan O'SHA ikki o'yinchi o'rtasidagi
    matchni topadi (uy/mehmon tartibi muhim — player1 vs player2 aniq mos kelishi
    kerak) va score/status'ni yozadi.

    Qaytaradi: muvaffaqiyatli ko'chirilgan natijalar soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    restored = 0
    for r in played:
        # Yangi jadvalda aynan shu yo'nalishdagi (p1 uy, p2 mehmon) matchni topamiz
        cursor.execute(
            """
            UPDATE matches
            SET score1 = ?, score2 = ?, submitted_by = ?, status = ?
            WHERE league_id = ? AND player1_id = ? AND player2_id = ?
              AND score1 IS NULL
            """,
            (r["score1"], r["score2"], r["submitted_by"], r["status"],
             league_id, r["player1_id"], r["player2_id"]),
        )
        if cursor.rowcount > 0:
            restored += 1
    conn.commit()
    conn.close()
    return restored

def _tournament_now() -> datetime:
    """Hozirgi vaqtni turnir mintaqasida (Toshkent UTC+5) qaytaradi."""
    tz = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
    return datetime.now(tz)


def _parse_draw_date(raw) -> datetime | None:
    """
    draw_date'ni (ISO string yoki datetime) turnir mintaqasidagi datetime'ga aylantiradi.
    None yoki noto'g'ri qiymatda None qaytaradi.
    """
    if raw is None:
        return None
    tz = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
    if isinstance(raw, datetime):
        dt = raw
    else:
        try:
            dt = datetime.fromisoformat(str(raw))
        except ValueError:
            return None
    # Naive bo'lsa — turnir mintaqasida deb hisoblaymiz (biz shunday yozamiz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def set_league_draw_date(league_id: int, dt: datetime | None = None) -> None:
    """
    Liga qur'a sanasini yozadi (turnir mintaqasi, ISO format). dt berilmasa — hozir.
    Bu sana asosida har kuni bitta yangi tur ochiladi (get_open_matchday).
    """
    if dt is None:
        dt = _tournament_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leagues SET draw_date = ? WHERE id = ?",
        (dt.isoformat(), league_id),
    )
    conn.commit()
    conn.close()


def reset_awaiting_in_range(league_id: int, from_md: int, to_md: int) -> int:
    """
    Berilgan ORALIQDAGI (from_md < matchday <= to_md) TASDIQLANMAGAN
    (awaiting_confirmation) natijalarni qayta 'pending' qiladi (score tozalanadi).

    Bu turlar hali o'ynalmagan bo'lsa-yu, kimdir yolg'on natija kiritib qo'ygan,
    raqib esa tasdiqlamagan ham rad qilmagan bo'lsa — ularni dastlabki (toza) holatga
    qaytaradi. CONFIRMED (tasdiqlangan) natijalarga TEGMAYDI — faqat awaiting.

    Qaytaradi: tozalangan turlar soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE matches
        SET score1 = NULL, score2 = NULL, submitted_by = NULL, status = 'pending'
        WHERE league_id = ? AND matchday > ? AND matchday <= ?
          AND status = 'awaiting_confirmation'
        """,
        (league_id, from_md, to_md),
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


def reopen_matchday_range(league_id: int, from_md: int, to_md: int) -> int:
    """
    Berilgan ORALIQDAGI (from_md < matchday <= to_md) avtomatik 0:0 tasdiqlangan
    turlarni qayta 'pending' qiladi. reopen_matchdays'dan farqi — pastki chegara ham
    bor, shuning uchun deadline o'tib tasdiqlangan turlarga (1-2) TEGMAYDI.

    Masalan from_md=2, to_md=4 → faqat 3-4 turdagi 0:0'lar qaytariladi.
    Faqat score 0:0 confirmed (qo'lda natijalarga tegmaydi).

    Qaytaradi: qayta ochilgan turlar soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE matches
        SET score1 = NULL, score2 = NULL, submitted_by = NULL, status = 'pending'
        WHERE league_id = ? AND matchday > ? AND matchday <= ?
          AND status = 'confirmed' AND score1 = 0 AND score2 = 0
        """,
        (league_id, from_md, to_md),
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


def reopen_matchdays(league_id: int, up_to_matchday: int) -> int:
    """
    Berilgan turgacha (up_to_matchday) bo'lgan AVTOMATIK 0:0 tasdiqlangan turlarni
    qayta 'pending' holatiga qaytaradi (xato avtomatik tasdiqni bekor qilish uchun).

    Faqat score 0:0 va confirmed bo'lganlarni qaytaradi (qo'lda kiritilган haqiqiy
    natijalarga TEGMAYDI — ular 0:0 emas yoki boshqa status).

    Qaytaradi: qayta ochilgan turlar (match) soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE matches
        SET score1 = NULL, score2 = NULL, submitted_by = NULL, status = 'pending'
        WHERE league_id = ? AND matchday <= ?
          AND status = 'confirmed' AND score1 = 0 AND score2 = 0
        """,
        (league_id, up_to_matchday),
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count
