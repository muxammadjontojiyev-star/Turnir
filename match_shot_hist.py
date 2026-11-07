"""
match_shot_hist.py — Match History qatorini tekshirish (match_shot.py 300 qatordan oshmasligi uchun ajratildi, 2026-11-07).
history_check → (xato | None, natija, raqib niknamesi kutiladimi, fp). Qoidalar — match_shot.py boshidagi izohda.
"""

from match_shot import _check_row, _fp, _key, _shot_used
from models import get_connection

GARBLED_NICK_MIN = 3                                   # bundan qisqa nikname — belgi chizig'i yozuvni yopgan


def _garbled(row: dict) -> bool:
    """Qator nikname(lar)i o'qilmay qolganmi (belgi chizig'i ustidan o'tgan)."""
    return min(len(_key(row.get("left") or "")), len(_key(row.get("right") or ""))) < GARBLED_NICK_MIN


def history_check(mode: str, match: dict, uid: int, row: dict) -> tuple[str | None, dict, bool, str]:
    """Match History qatori: (xato | None, natija, raqib niknamesi kutiladimi, fp)."""
    why, r = _check_row(mode, match, uid, row)
    awaiting = why == "no_opp_nick"
    if awaiting:                                        # raqib niknamesi yo'q — u tasdiqlaydi (match_shot_await)
        from match_shot_await import check_await
        why, r = check_await(mode, match, uid, row, r["my_nick"])
    if why == "nick_mismatch" and row.get("marked") and _garbled(row):
        return "mark_over_text", r, awaiting, ""      # belgi chizig'i nikname ustidan o'tib, o'qib bo'lmadi
    if why == "nick_mismatch":                          # 2026-11-06: haqiqiy sabab yashirilmaydi — ro'yxatdagi niknamelar
        return f"nick_mismatch|{(r or {}).get('detail', '')}".rstrip("|"), r, awaiting, ""
    if why == "bad_date":
        return f"bad_date|{row.get('date', '')} {row.get('time') or ''}".strip(), r, awaiting, ""
    if why:
        return why, r, awaiting, ""
    fp = _fp(row, r["played"])
    conn = get_connection()
    try:
        if _shot_used(conn, row, r["played"]):
            return "shot_used", r, awaiting, ""
    finally:
        conn.close()
    return None, r, awaiting, fp
