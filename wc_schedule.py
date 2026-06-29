"""
wc_schedule.py — World Cup guruh o'yinlari (round-robin) generatsiyasi.

Har guruhda 4 jamoa. Har kim har kim bilan 1 marta o'ynaydi (1 doira):
4 jamoa -> 3 tur (matchday), har turda 2 o'yin -> jami 6 o'yin.

Liga schedule.py dagi circle method qayta ishlatiladi (bir doira),
lekin wc_matches jadvaliga, group_letter bo'yicha yoziladi.
"""

from models import get_connection
from config import MATCH_STATUS_PENDING
from schedule import _generate_round_robin_pairs


def wc_get_group_player_ids(group_letter: str) -> list[int]:
    """Guruhdagi barcha ro'yxatdan o'tgan o'yinchilar ID larini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM wc_registrations WHERE group_letter = ?",
        (group_letter,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["user_id"] for row in rows]


def wc_group_has_matches(group_letter: str) -> bool:
    """Shu guruhda o'yinlar allaqachon yaratilganmi (ikki marta qur'a oldini olish)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM wc_matches WHERE group_letter = ?",
        (group_letter,),
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] > 0


def generate_wc_group_schedule(group_letter: str, player_ids: list[int]) -> int:
    """
    Guruh uchun 1 doiralik round-robin jadval generatsiya qiladi (har kim har
    kim bilan 1 marta) va wc_matches'ga yozadi.

    4 jamoa -> 3 tur (matchday 1..3), har turda 2 o'yin -> 6 o'yin.
    Qaytaradi: yaratilgan matchlar soni.
    """
    rounds = _generate_round_robin_pairs(player_ids)  # 1 doira

    conn = get_connection()
    cursor = conn.cursor()

    created = 0
    for matchday_index, round_pairs in enumerate(rounds, start=1):
        for (player1_id, player2_id) in round_pairs:
            cursor.execute(
                """
                INSERT INTO wc_matches
                    (group_letter, matchday, player1_id, player2_id, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (group_letter, matchday_index, player1_id, player2_id, MATCH_STATUS_PENDING),
            )
            created += 1

    conn.commit()
    conn.close()
    return created


def wc_delete_group_matches(group_letter: str) -> int:
    """Guruh o'yinlarini o'chiradi (qayta qur'a yoki tozalash uchun)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM wc_matches WHERE group_letter = ?", (group_letter,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted
