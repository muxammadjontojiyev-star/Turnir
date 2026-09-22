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

# 2026-09-22: barcha rejimlar. Har rejimda o'z jadvallari va "tur" ustuni bor,
# qolgan mantiq (vaqt, kutish tahlili) BIR XIL — shuning uchun so'rov
# shakllantiriladi, funksiya takrorlanmaydi (qoida #26 DRY).
#   msg_table   — xabarlar jadvali
#   match_table — o'yinlar jadvali
#   round_col   — "tur" ma'nosidagi ustun (yo'q bo'lsa None)
#   round_label — admin ko'radigan nom
#   playoff     — wc_messages'da is_playoff filtri kerakmi (None = kerak emas)
#   has_club    — klub nomi registrations'dan olinadimi (faqat liga)
MODES = {
    "league": {"msg_table": "messages",        "match_table": "matches",
               "round_col": "matchday", "round_label": "tur",
               "playoff": None, "has_club": True,  "title": "Liga"},
    "cl":     {"msg_table": "cl_messages",     "match_table": "cl_matches",
               "round_col": "matchday", "round_label": "tur",
               "playoff": None, "has_club": False, "title": "ChL guruh"},
    "cl_po":  {"msg_table": "cl_po_messages",  "match_table": "cl_playoff_matches",
               "round_col": "round",    "round_label": "bosqich",
               "playoff": None, "has_club": False, "title": "ChL play-off"},
    "div":    {"msg_table": "div_messages",    "match_table": "div_matches",
               "round_col": "day",      "round_label": "kun",
               "playoff": None, "has_club": False, "title": "Divizion"},
    "wc":     {"msg_table": "wc_messages",     "match_table": "wc_matches",
               "round_col": "matchday", "round_label": "tur",
               "playoff": 0,    "has_club": False, "title": "JCh guruh"},
    "wc_po":  {"msg_table": "wc_messages",     "match_table": "wc_playoff_matches",
               "round_col": "round",    "round_label": "bosqich",
               "playoff": 1,    "has_club": False, "title": "JCh play-off"},
}
DEFAULT_MODE = "league"


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


def match_chat_report(match_id: int, mode: str = DEFAULT_MODE) -> dict | None:
    """
    O'yin yozishmalari hisoboti. Match topilmasa (yoki rejim noto'g'ri) None.

    mode: MODES kalitlaridan biri (league / cl / cl_po / div / wc / wc_po).

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
    cfg = MODES.get(mode)
    if cfg is None:
        logger.warning("Noma'lum rejim: %r", mode)
        return None

    # Ustun nomlari MODES'dan keladi (foydalanuvchi kiritmaydi) — SQL injection
    # xavfi yo'q (qoida #29: faqat qiymatlar parametrlashtiriladi).
    round_sel = f"m.{cfg['round_col']} AS round_value" if cfg["round_col"] else "NULL AS round_value"
    club_sel = ("r1.club_name AS p1_club, r2.club_name AS p2_club"
                if cfg["has_club"] else "NULL AS p1_club, NULL AS p2_club")
    club_join = ("LEFT JOIN registrations r1 ON r1.user_id = m.player1_id "
                 "LEFT JOIN registrations r2 ON r2.user_id = m.player2_id"
                 if cfg["has_club"] else "")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            SELECT m.id, {round_sel}, m.status, m.score1, m.score2,
                   m.player1_id, m.player2_id,
                   u1.username AS p1_username, u1.nickname AS p1_nickname,
                   u2.username AS p2_username, u2.nickname AS p2_nickname,
                   {club_sel}
            FROM {cfg['match_table']} m
            LEFT JOIN users u1 ON u1.id = m.player1_id
            LEFT JOIN users u2 ON u2.id = m.player2_id
            {club_join}
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
        # 2026-09-22: klub nomi ham — admin qaysi klubga ochko berishni tez tushunsin.
        # Logo frontendda nom bo'yicha topiladi (api.js findClubLogo), shuning uchun
        # bu yerda faqat NOM qaytariladi (qoida #26 — logo jadvali takrorlanmaydi).
        clubs = {
            m["player1_id"]: m["p1_club"],
            m["player2_id"]: m["p2_club"],
        }

        # wc_messages guruh va play-off xabarlarini BIR jadvalda saqlaydi —
        # is_playoff bilan ajratiladi (qoida #11)
        playoff_where = " AND is_playoff = ?" if cfg["playoff"] is not None else ""
        params = [match_id]
        if cfg["playoff"] is not None:
            params.append(cfg["playoff"])
        params.append(MAX_MESSAGES + 1)
        cursor.execute(
            f"SELECT id, sender_id, text, is_read, created_at, read_at "
            f"FROM {cfg['msg_table']} WHERE match_id = ?{playoff_where} "
            f"ORDER BY id LIMIT ?",
            tuple(params),
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
        "sender_club": clubs.get(r["sender_id"]),
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
                "waiting_club": clubs.get(block_start["sender_id"]),
                "replier_label": labels.get(r["sender_id"], "?"),
                "replier_club": clubs.get(r["sender_id"]),
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
            "waiting_club": clubs.get(block_start["sender_id"]),
            "replier_label": labels.get(opponent_id, "?"),
            "replier_club": clubs.get(opponent_id),
            "asked_at": _to_tashkent(block_start["created_at"]),
            "replied_at": None,          # javob kelmagan
            "wait_min": None,
            "seen_min": _minutes_between(block_start["created_at"], block_start.get("read_at")),
        })

    waits = [d["wait_min"] for d in delays if d["wait_min"] is not None]

    return {
        "mode": mode,
        "mode_title": cfg["title"],
        "round_label": cfg["round_label"],
        "match": {
            "id": m["id"], "matchday": m["round_value"], "status": m["status"],
            "score1": m["score1"], "score2": m["score2"],
            "p1": {"user_id": m["player1_id"], "label": labels.get(m["player1_id"]),
                   "club": m["p1_club"]},
            "p2": {"user_id": m["player2_id"], "label": labels.get(m["player2_id"]),
                   "club": m["p2_club"]},
        },
        "messages": messages,
        "delays": delays,
        "max_wait_min": max(waits) if waits else None,
        "message_count": len(messages),
        "truncated": truncated,
    }
