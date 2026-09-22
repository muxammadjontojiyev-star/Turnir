"""
chat_report.py — admin uchun o'yin yozishmalari hisoboti (2026-08-28).

Muammo (qoida #52): ishtirokchi Telegram chatidan raqibning xabarini o'chirib,
skrinshot olib adminga "javob bermadi" deb ko'rsatmoqda. Admin ishonib hisobni
uning foydasiga kiritmoqda.

Yechim: bot chatidagi yozishmalar SERVERDA saqlanadi (`messages` jadvali) va
ularni hech kim o'chira olmaydi — kodda `DELETE FROM messages` umuman yo'q.
Admin skrinshot so'ramasdan haqiqiy yozishmani ko'rsin.

NIMANI KO'RSATADI:
  1. To'liq yozishma — kim, nima, qachon (Toshkent vaqtida);
  2. Har bir xabar o'qilganmi va QACHON o'qilgani (read_at, 2026-08-28 dan);
  3. HISOB-KITOB: har bir tomon raqibni necha daqiqa kutdirgan —
     "javob bermadi" bilan "ataylab cho'zdi" ni ajratish uchun.

Bu modul FAQAT O'QIYDI — hech narsa o'zgartirmaydi (qoida #07).
"""

import logging
from datetime import datetime, timedelta, timezone

from models import get_connection

logger = logging.getLogger(__name__)

# Toshkent vaqti (UTC+5). SQLite created_at/read_at ni UTC da saqlaydi —
# admin 23:20 bilan solishtirganda konvertatsiya SHART, aks holda xulosa
# 5 soatga xato bo'ladi.
TASHKENT_TZ = timezone(timedelta(hours=5))

# Hisobotda ko'rsatiladigan maksimal xabar soni
MAX_MESSAGES = 200


def _to_tashkent(raw: str | None) -> str | None:
    """SQLite UTC vaqtini ('YYYY-MM-DD HH:MM:SS') Toshkent vaqtiga o'giradi."""
    if not raw:
        return None
    try:
        dt = datetime.strptime(str(raw)[:19], "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc).astimezone(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        logger.warning("Vaqt formatini o'qib bo'lmadi: %r", raw)
        return None


def _minutes_between(a: str | None, b: str | None) -> int | None:
    """a dan b gacha necha daqiqa (ikkalasi ham UTC matn)."""
    if not a or not b:
        return None
    try:
        da = datetime.strptime(str(a)[:19], "%Y-%m-%d %H:%M:%S")
        db = datetime.strptime(str(b)[:19], "%Y-%m-%d %H:%M:%S")
        return int((db - da).total_seconds() // 60)
    except (ValueError, TypeError):
        return None


def match_chat_report(match_id: int) -> dict | None:
    """
    O'yin yozishmalari hisoboti. Match topilmasa None.

    Qaytaradi:
      {
        "match": {id, matchday, status, score1, score2,
                  p1: {user_id, label}, p2: {...}},
        "messages": [{id, sender_user_id, sender_label, text,
                      sent_at, read_at, read_after_min}, ...],
        "delays": [{waiting_user_id, waiting_label, replier_label,
                    asked_at, replied_at, wait_min, seen_min}, ...],
        "max_wait_min": int | None,     # eng uzun kutish
        "message_count": int,
        "truncated": bool
      }

    delays: raqib xabar yozgandan keyin, JAVOB kelguncha o'tgan vaqt.
      wait_min  — javob kutilgan daqiqa (javob kelmagan bo'lsa None)
      seen_min  — xabar yozilgandan o'qilgunicha (ko'rdimi va qachon)
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT m.id, m.matchday, m.status, m.score1, m.score2,
                   m.player1_id, m.player2_id,
                   u1.username AS p1_username, u1.nickname AS p1_nickname,
                   u2.username AS p2_username, u2.nickname AS p2_nickname
            FROM matches m
            LEFT JOIN users u1 ON u1.id = m.player1_id
            LEFT JOIN users u2 ON u2.id = m.player2_id
            WHERE m.id = ?
            """,
            (match_id,),
        )
        mrow = cursor.fetchone()
        if mrow is None:
            return None
        m = dict(mrow)

        labels = {
            m["player1_id"]: m["p1_username"] or m["p1_nickname"] or f"#{m['player1_id']}",
            m["player2_id"]: m["p2_username"] or m["p2_nickname"] or f"#{m['player2_id']}",
        }

        cursor.execute(
            "SELECT id, sender_id, text, is_read, created_at, read_at "
            "FROM messages WHERE match_id = ? ORDER BY id LIMIT ?",
            (match_id, MAX_MESSAGES + 1),
        )
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    truncated = len(rows) > MAX_MESSAGES
    rows = rows[:MAX_MESSAGES]

    messages = [{
        "id": r["id"],
        "sender_user_id": r["sender_id"],
        "sender_label": labels.get(r["sender_id"], f"#{r['sender_id']}"),
        "text": r["text"],
        "sent_at": _to_tashkent(r["created_at"]),
        "read_at": _to_tashkent(r.get("read_at")),
        "read_after_min": _minutes_between(r["created_at"], r.get("read_at")),
    } for r in rows]

    # Kutish tahlili: tomon almashgan har bir joyda, oldingi tomonning
    # BIRINCHI javobsiz xabaridan javob kelgunicha o'tgan vaqt.
    delays = []
    block_start = None      # javob kutayotgan tomonning birinchi xabari
    for r in rows:
        if block_start is None:
            block_start = r
            continue
        if r["sender_id"] != block_start["sender_id"]:
            # Javob keldi — kutish tugadi
            delays.append({
                "waiting_user_id": block_start["sender_id"],
                "waiting_label": labels.get(block_start["sender_id"], "?"),
                "replier_label": labels.get(r["sender_id"], "?"),
                "asked_at": _to_tashkent(block_start["created_at"]),
                "replied_at": _to_tashkent(r["created_at"]),
                "wait_min": _minutes_between(block_start["created_at"], r["created_at"]),
                "seen_min": _minutes_between(block_start["created_at"], block_start.get("read_at")),
            })
            block_start = r
    # Sikl tugagach block_start har doim OXIRGI blokning birinchi xabari bo'ladi,
    # va o'sha blokka javob kelmagan (aks holda block_start siljigan bo'lardi).
    # Ya'ni bu — hali javobsiz, ochiq kutish.
    if block_start is not None:
        opponent_id = (m["player2_id"] if block_start["sender_id"] == m["player1_id"]
                       else m["player1_id"])
        delays.append({
            "waiting_user_id": block_start["sender_id"],
            "waiting_label": labels.get(block_start["sender_id"], "?"),
            "replier_label": labels.get(opponent_id, "?"),
            "asked_at": _to_tashkent(block_start["created_at"]),
            "replied_at": None,          # javob kelmagan
            "wait_min": None,
            "seen_min": _minutes_between(block_start["created_at"], block_start.get("read_at")),
        })

    waits = [d["wait_min"] for d in delays if d["wait_min"] is not None]

    return {
        "match": {
            "id": m["id"], "matchday": m["matchday"], "status": m["status"],
            "score1": m["score1"], "score2": m["score2"],
            "p1": {"user_id": m["player1_id"], "label": labels.get(m["player1_id"])},
            "p2": {"user_id": m["player2_id"], "label": labels.get(m["player2_id"])},
        },
        "messages": messages,
        "delays": delays,
        "max_wait_min": max(waits) if waits else None,
        "message_count": len(messages),
        "truncated": truncated,
    }
