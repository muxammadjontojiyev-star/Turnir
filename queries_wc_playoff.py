"""
queries_wc_playoff.py — WC play-off: bracket qurish, round ochilishi, g'olibni keyingi bosqichga o'tkazish.

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from datetime import timedelta
from models import get_connection
from config import (
    MATCHDAY_UNLOCK_HOUR,
    MATCHDAY_UNLOCK_MINUTE,
)
from queries_leagues import _parse_draw_date, _tournament_now


# ============================================================
#   WC PLAY-OFF (chiqib ketish bosqichi) DB amallari
# ============================================================

def wc_playoff_is_started() -> bool:
    """Play-off boshlanganmi (wc_playoff_state.started=1)?"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT started FROM wc_playoff_state WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return bool(row and row["started"] == 1)


def wc_playoff_has_matches() -> bool:
    """Play-off matchlari yaratilganmi?"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM wc_playoff_matches")
    cnt = cursor.fetchone()["cnt"]
    conn.close()
    return cnt > 0


def wc_playoff_build_bracket(r32_pairings: list[dict]) -> dict:
    """
    Play-off bracketini DB'ga yozadi: barcha bosqich matchlarini yaratadi va
    g'olib oqimi uchun next_match_id/next_slot bog'lanishlarini o'rnatadi.

    r32_pairings: wc_build_r32_pairings() natijasi (16 ta juftlik).

    Struktura (g'olib oqimi):
      r32 (16) -> r16 (8) -> r8 (4) -> r4 (2) -> final (1)
      r4 mag'lublari -> bronze (1)

    Avval keyingi bosqichlar (bo'sh) yaratiladi (ID olish uchun), keyin
    oldingilari ularga bog'lanadi. Final va bronze alohida.

    Qaytaradi: {created: jami match soni}
    """
    conn = get_connection()
    cursor = conn.cursor()

    def make_match(round_name, position, p1=None, p2=None, next_id=None, next_slot=None, open_date=None):
        cursor.execute(
            """
            INSERT INTO wc_playoff_matches
                (round, position, player1_id, player2_id, next_match_id, next_slot, open_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (round_name, position, p1, p2, next_id, next_slot, open_date),
        )
        return cursor.lastrowid

    # 1) Final (1 ta) — eng oxirgi, next yo'q
    final_id = make_match("final", 0)
    # 2) Bronze (1 ta) — r4 mag'lublari, next yo'q
    bronze_id = make_match("bronze", 0)

    # 3) r4 (2 ta) — g'olib final'ga (slot 1,2), mag'lub bronze'ga (slot 1,2)
    # next_match_id = final, lekin mag'lub bronze'ga ham borishi kerak.
    # next_slot final uchun (1 yoki 2). Bronze bog'lanishi alohida ustun kerak emas —
    # r4 ID'larini bronze'ga qo'lda bog'lash uchun loser oqimi kodda hal qilinadi.
    r4_ids = []
    for i in range(2):
        mid = make_match("r4", i, next_id=final_id, next_slot=(i + 1))
        r4_ids.append(mid)

    # 4) r8 (4 ta) — g'olib r4'ga
    r8_ids = []
    for i in range(4):
        parent = r4_ids[i // 2]
        slot = (i % 2) + 1
        mid = make_match("r8", i, next_id=parent, next_slot=slot)
        r8_ids.append(mid)

    # 5) r16 (8 ta) — g'olib r8'ga
    r16_ids = []
    for i in range(8):
        parent = r8_ids[i // 2]
        slot = (i % 2) + 1
        mid = make_match("r16", i, next_id=parent, next_slot=slot)
        r16_ids.append(mid)

    # 6) r32 (16 ta) — g'olib r16'ga, jamoalar bilan to'ldiriladi
    for pair in r32_pairings:
        pos = pair["position"]
        parent = r16_ids[pos // 2]
        slot = (pos % 2) + 1
        p1 = pair["team1"]["user_id"]
        p2 = pair["team2"]["user_id"]
        make_match("r32", pos, p1=p1, p2=p2, next_id=parent, next_slot=slot)

    # wc_playoff_state: boshlangan deb belgilaymiz
    now = _tournament_now()
    cursor.execute(
        """
        INSERT INTO wc_playoff_state (id, started, start_date) VALUES (1, 1, ?)
        ON CONFLICT(id) DO UPDATE SET started = 1, start_date = excluded.start_date
        """,
        (now.isoformat(),),
    )

    conn.commit()
    cursor.execute("SELECT COUNT(*) as cnt FROM wc_playoff_matches")
    total = cursor.fetchone()["cnt"]
    conn.close()
    return {"created": total, "bronze_id": bronze_id, "final_id": final_id, "r4_ids": r4_ids}


# ---- WC PLAY-OFF: kunlik bosqich oqimi ----

# Bosqichlar tartibi (kun bo'yicha ochiladi). Har kun bitta bosqich.
# final va bronze bir kunda (oxirgi kun) ochiladi.
WC_PLAYOFF_ROUND_ORDER = ["r32", "r16", "r8", "r4", "final"]


def wc_playoff_get_open_round_index() -> int:
    """
    Play-off start_date'dan boshlab hozir ochiq eng yuqori bosqich indeksi.
    0 = r32 (1-kun), 1 = r16 (2-kun), ..., 4 = final+bronze (5-kun).
    Boshlanmagan bo'lsa -1.

    Liga matchday-lock mantig'i, lekin har kun 1 bosqich (deadline 23:30).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT started, start_date FROM wc_playoff_state WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if not row or row["started"] != 1:
        return -1
    start_dt = _parse_draw_date(row["start_date"])
    if start_dt is None:
        return -1

    now = _tournament_now()

    def unlock_day(d):
        shifted = d - timedelta(hours=MATCHDAY_UNLOCK_HOUR, minutes=MATCHDAY_UNLOCK_MINUTE)
        return shifted.date()

    days_passed = (unlock_day(now) - unlock_day(start_dt)).days
    idx = days_passed  # 1-kun (days_passed=0) -> r32 ochiq
    if idx < 0:
        idx = 0
    last = len(WC_PLAYOFF_ROUND_ORDER) - 1
    if idx > last:
        idx = last
    return idx


def wc_playoff_round_is_open(round_name: str) -> bool:
    """Berilgan play-off bosqichi hozir ochiqmi (kun bo'yicha)?"""
    open_idx = wc_playoff_get_open_round_index()
    if open_idx < 0:
        return False
    # final va bronze bir xil kun (oxirgi)
    rname = "final" if round_name == "bronze" else round_name
    try:
        round_idx = WC_PLAYOFF_ROUND_ORDER.index(rname)
    except ValueError:
        return False
    return round_idx <= open_idx


def wc_playoff_get_match_by_id(match_id: int) -> dict | None:
    """ID bo'yicha play-off matchni qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wc_playoff_matches WHERE id = ?", (match_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def wc_playoff_advance_winner(match_id: int) -> None:
    """
    Play-off match natijasi confirmed bo'lgach, g'olibni keyingi bosqich
    matchining tegishli slotiga joylaydi. r4 bo'lsa, mag'lubni ham bronze'ga.

    G'olib: kattaroq skor egasi (eFootballda durang yo'q).
    """
    match = wc_playoff_get_match_by_id(match_id)
    if match is None or match["status"] != "confirmed":
        return
    if match["score1"] is None or match["score2"] is None:
        return

    # G'olib va mag'lub
    if match["score1"] > match["score2"]:
        winner, loser = match["player1_id"], match["player2_id"]
    elif match["score2"] > match["score1"]:
        winner, loser = match["player2_id"], match["player1_id"]
    else:
        return  # durang — bo'lmasligi kerak

    conn = get_connection()
    cursor = conn.cursor()

    # G'olibni keyingi matchga joylaymiz
    if match["next_match_id"] and match["next_slot"]:
        col = "player1_id" if match["next_slot"] == 1 else "player2_id"
        cursor.execute(
            f"UPDATE wc_playoff_matches SET {col} = ? WHERE id = ?",
            (winner, match["next_match_id"]),
        )

    # r4 mag'lublari bronze'ga (round='bronze')
    if match["round"] == "r4":
        cursor.execute("SELECT id, player1_id, player2_id FROM wc_playoff_matches WHERE round = 'bronze' LIMIT 1")
        bronze = cursor.fetchone()
        if bronze and loser not in (bronze["player1_id"], bronze["player2_id"]):
            # Bo'sh slotga qo'yamiz (loser allaqachon bo'lsa — takror yozmaymiz)
            if bronze["player1_id"] is None:
                cursor.execute("UPDATE wc_playoff_matches SET player1_id = ? WHERE id = ?", (loser, bronze["id"]))
            elif bronze["player2_id"] is None:
                cursor.execute("UPDATE wc_playoff_matches SET player2_id = ? WHERE id = ?", (loser, bronze["id"]))

    conn.commit()
    conn.close()


def wc_playoff_backfill_advancements() -> int:
    """
    Bir martalik ta'mirlash: ilgari confirmed bo'lgan, lekin g'olibi keyingi
    bosqichga o'tkazilmay qolgan play-off matchlarni to'g'rilaydi.
    Server startida chaqiriladi; idempotent — takror ishlashi xavfsiz
    (advance slotni bir xil g'olib bilan yozadi, bronze takrorlanmaydi).

    Bosqich tartibida yuriladi (r32→r16→r8→r4), shunda avval pastki
    bosqich slotlari to'ladi. Qaytaradi: qayta ishlangan matchlar soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM wc_playoff_matches
        WHERE status = 'confirmed' AND score1 IS NOT NULL AND score2 IS NOT NULL
        ORDER BY
            CASE round
                WHEN 'r32' THEN 0 WHEN 'r16' THEN 1 WHEN 'r8' THEN 2
                WHEN 'r4' THEN 3 ELSE 4
            END, id
        """
    )
    ids = [r["id"] for r in cursor.fetchall()]
    conn.close()

    for mid in ids:
        wc_playoff_advance_winner(mid)
    return len(ids)
