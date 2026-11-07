"""
tb_plan.py — "TEAMLAR JANGI": KEYINGI MAVSUM REJASI (2026-11-07, egasi: «Liga admini UCL formatini tanlab saqlash
tugmasini bosadigan bo'lsin … UCL formatida mavjud teamlar sonidan kelib chiqib bo'lajak o'yinlar formati tashkil
etilishi kerak»).

  * Liga admini format (Liga / UCL) va «har bahsda nechta o'yinchi»ni tanlab «💾 Saqlash» bosadi → tb_leagues.draw_format,
    draw_size, draw_ucl (JSON — qo'lda sozlangan UCL parametrlari; NULL — avtomatik).
  * auto_ucl(n) — qatnasha oladigan teamlar soniga qarab UCL rejasi (static/tb_admin_draw.js da aynan shu qoida):
      liga bosqichi: har team min(6, n−1 / toq bo'lsa n) bahs;
      pley-off: n ≥ 24 — rasmiy ChL kabi (1–8 → 1/8 final, 9–24 pley-off raundi); 12–23 — 1–4 → chorak final,
      5–12 pley-off raundi; 8–11 — top-4 (yarim final); 2–7 — top-2 (final);
      pley-off bahsi n ≥ 8 bo'lsa 2 o'yin (uy-mehmon), aks holda 1; final — 1 o'yin.
  * Qur'a o'tkazilganda saqlangan reja ishlatiladi (frontend parametrlarni yuboradi, server tb_ucl.validate_ucl bilan
    tekshiradi).
"""

import json

from models import get_connection

UCL_ROUNDS_MAX = 6
PLAYIN_BIG, PLAYIN_MID = 24, 12            # shuncha va undan ko'p team — pley-off raundi bilan (16 / 8 setka)
TOP4_FROM = 8                              # 8..11 team — top-4
TWO_LEGS_FROM = 8                          # pley-off bahslari 2 o'yin bo'ladigan teamlar soni
FORMATS = ("league", "ucl")


def migrate_plan(cur) -> None:
    cols = {r[1] for r in cur.execute("PRAGMA table_info(tb_leagues)").fetchall()}
    for name, ddl in (("draw_format", "TEXT"), ("draw_size", "INTEGER"), ("draw_ucl", "TEXT")):
        if name not in cols:
            cur.execute(f"ALTER TABLE tb_leagues ADD COLUMN {name} {ddl}")


def auto_ucl(n: int) -> dict | None:
    """n — qatnasha oladigan teamlar. Kamida 2 ta kerak."""
    if n < 2:
        return None
    max_r = n - 1 if n % 2 == 0 else n
    rounds = max(1, min(UCL_ROUNDS_MAX, max_r))
    if n >= PLAYIN_BIG:
        q, playin = 16, True
    elif n >= PLAYIN_MID:
        q, playin = 8, True
    elif n >= TOP4_FROM:
        q, playin = 4, False
    else:
        q, playin = 2, False
    legs = 2 if n >= TWO_LEGS_FROM else 1
    return {"ucl_rounds": rounds, "ucl_qualify": q, "ucl_playin": playin, "ko_legs": legs, "final_legs": 1}


def get_plan(league_id: int) -> dict:
    conn = get_connection()
    try:
        migrate_plan(conn.cursor())
        r = conn.execute("SELECT draw_format, draw_size, draw_ucl FROM tb_leagues WHERE id = ?", (league_id,)).fetchone()
    finally:
        conn.close()
    if not r or not r["draw_format"]:
        return {"saved": False}
    try:
        manual = json.loads(r["draw_ucl"]) if r["draw_ucl"] else None
    except (TypeError, ValueError):
        manual = None
    return {"saved": True, "format": r["draw_format"], "match_size": r["draw_size"], "manual": manual}


def save_plan(league_id: int, fmt: str, match_size: int | None, manual: dict | None) -> tuple[bool, str | dict]:
    from tb_ucl import TB_MATCH_SIZE_MAX, TB_MATCH_SIZE_MIN
    if fmt not in FORMATS:
        return False, "bad_format"
    if match_size is not None and not (TB_MATCH_SIZE_MIN <= int(match_size) <= TB_MATCH_SIZE_MAX):
        return False, "bad_match_size"
    keep = ("ucl_rounds", "ucl_qualify", "ucl_playin", "ko_legs", "final_legs", "division_size")
    man = {k: manual[k] for k in keep if manual and manual.get(k) is not None} or None
    conn = get_connection()
    try:
        migrate_plan(conn.cursor())
        cur = conn.execute("UPDATE tb_leagues SET draw_format = ?, draw_size = ?, draw_ucl = ? WHERE id = ?",
                           (fmt, match_size, json.dumps(man) if man else None, league_id))
        conn.commit()
        if not cur.rowcount:
            return False, "league_not_found"
    finally:
        conn.close()
    return True, get_plan(league_id)
