"""
pt_legs.py — SHAXSIY turnir pley-offida ikki o'yinli juftliklar (javob o'yini, 2026-10-07).

Admin qarori: ERKIN formatda tashkilotchi "2 doira" tanlasa — guruh uy+mehmon (pt_draw) va
pley-off har bosqichi IKKI O'YIN YIG'INDISI (final — 1 o'yin). Boshqa formatlarda doim 1 o'yin.
  - 1-o'yin: A uyda (player1=A), 2-o'yin: B uyda (player1=B); pt_matches.leg = 1 | 2, round = juftlik raqami.
  - 1-o'yinda durang mumkin; 2-o'yin faqat 1-o'yin tasdiqlangach kiritiladi (first_leg_pending) va
    yig'indi teng bo'lmasligi kerak (aggregate_draw — penalti 2-o'yin ichida, yakuniy hisob kiritiladi).
  - Juftlik g'olibi — yig'indi bo'yicha; pt_knockout juftliklar ("tie") bilan ishlaydi (ko_ties).
"""

STAGE_FINAL = "final"


def ko_legs(cursor, tid: int) -> int:
    """Pley-off juftligidagi o'yinlar soni: erkin format + 2 doira -> 2, aks holda 1."""
    cursor.execute("SELECT format, legs FROM pt_tournaments WHERE id = ?", (tid,))
    r = cursor.fetchone()
    return 2 if r and (r["format"] or "classic") == "classic" and (r["legs"] or 1) == 2 else 1


def insert_ties(cursor, tid: int, stage: str, pairs: list[tuple[int, int]], legs: int) -> None:
    rows = []
    for i, (a, b) in enumerate(pairs, start=1):
        rows.append((tid, stage, i, a, b, 1))
        if legs == 2 and stage != STAGE_FINAL:
            rows.append((tid, stage, i, b, a, 2))          # javob o'yini — uy/mehmon almashadi
    cursor.executemany("INSERT INTO pt_matches (tournament_id, stage, round, player1_id, player2_id, leg) "
                       "VALUES (?, ?, ?, ?, ?, ?)", rows)


def _score_for(row: dict, uid: int):
    return row["score1"] if row["player1_id"] == uid else row["score2"]


def ko_ties(cursor, tid: int) -> dict[str, list[dict]]:
    """
    {bosqich: [juftlik, ...]} round tartibida. Juftlik: player1/2 (1-o'yin bo'yicha), status
    (confirmed — barcha o'yinlari tasdiqlangan), score1/2 — yig'indi, rows — o'yinlar, any_confirmed.
    """
    cursor.execute("SELECT id, stage, round, leg, player1_id, player2_id, score1, score2, status FROM pt_matches "
                   "WHERE tournament_id = ? AND stage != 'group' ORDER BY round, leg", (tid,))
    ties: dict[tuple, dict] = {}
    for r in cursor.fetchall():
        r = dict(r)
        key = (r["stage"], r["round"])
        if key not in ties:
            ties[key] = {"stage": r["stage"], "round": r["round"], "id": r["id"], "player1_id": r["player1_id"],
                         "player2_id": r["player2_id"], "rows": []}
        ties[key]["rows"].append(r)
    out: dict[str, list[dict]] = {}
    for (stage, _), t in sorted(ties.items(), key=lambda kv: kv[0][1]):
        rows = t["rows"]
        done = all(x["status"] == "confirmed" and x["score1"] is not None for x in rows)
        t["status"] = "confirmed" if done else rows[0]["status"]
        t["any_confirmed"] = any(x["status"] == "confirmed" for x in rows)
        t["score1"] = sum(_score_for(x, t["player1_id"]) for x in rows) if done else None
        t["score2"] = sum(_score_for(x, t["player2_id"]) for x in rows) if done else None
        out.setdefault(stage, []).append(t)
    return out


def update_tie_players(cursor, tie: dict, p1: int, p2: int) -> None:
    """Tuzatishdan keyin keyingi bosqich juftligining o'yinchilarini yangilaydi (barcha o'yinlari)."""
    for x in tie["rows"]:
        a, b = (p1, p2) if (x.get("leg") or 1) == 1 else (p2, p1)
        cursor.execute("UPDATE pt_matches SET player1_id = ?, player2_id = ?, score1 = NULL, score2 = NULL, "
                       "submitted_by = NULL, status = 'pending' WHERE id = ?", (a, b, x["id"]))


def ko_draw_check(cursor, m: dict, score1: int, score2: int) -> str | None:
    """
    Pley-off natijasi tekshiruvi (o'yinchi kiritishi va tashkilotchi tuzatishi uchun umumiy, qoida #26).
    m: {id, tournament_id|tid, stage, round, player1_id, player2_id}. None — ruxsat.
    """
    if m["stage"] == "group":
        return None
    tid = m.get("tournament_id") or m.get("tid")
    cursor.execute("SELECT id, leg, player1_id, player2_id, score1, score2, status FROM pt_matches "
                   "WHERE tournament_id = ? AND stage = ? AND round = ? AND id != ?",
                   (tid, m["stage"], m["round"], m["id"]))
    other = cursor.fetchone()
    if not other:                                         # bitta o'yinli juftlik
        return "draw_not_allowed" if score1 == score2 else None
    other = dict(other)
    mine_leg = 2 if (other["leg"] or 1) == 1 else 1
    if mine_leg == 2 and other["status"] != "confirmed":
        return "first_leg_pending"
    if other["status"] != "confirmed" or other["score1"] is None:
        return None                                       # 1-o'yin: durang mumkin
    agg1 = score1 + _score_for(other, m["player1_id"])
    agg2 = score2 + _score_for(other, m["player2_id"])
    return "aggregate_draw" if agg1 == agg2 else None
