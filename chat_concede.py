"""
chat_concede.py — «WIN SIZGA» — RAQIBGA G'ALABANI BERISH (2026-11-07, egasi: «ba'zi ishtirokchilar raqibiga win sizga deb
yoki shunga o'xshash xabar yuboradi. Shunaqa holatda faqatgina 3:0 kiritishga ruxsat berish kerak»).

Bot erkin matnni 100% tushunolmaydi («win sizga emas», hazil), shuning uchun:
  * Bot chatida X yozgan xabarda taslim iborasi (CONCEDE_PATTERNS) bo'lsa — X ning o'ziga chatda so'rov chiqadi:
    «Raqibga 3:0 berasizmi?» → «Ha» — darhol 3:0 (raqib foydasiga, tasdiqlangan; chat_auto.apply_techwin);
    «Yo'q» — bu xabar taslim emas (keyin hisobga olinmaydi).
  * X javob bermasa: raqib (Y) xona ID siz ham FAQAT 3:0 (o'z foydasiga) kirita oladi — odatiy tasdiq tartibida
    (chat_gate.py); deadline'da bot o'zi 3:0 qiladi (chat_auto.sweep).
Jadval — concessions (X ning shu xabarga qarori; migratsiya).
"""

import logging
import re
import time

from models import get_connection

logger = logging.getLogger(__name__)

_APOS = re.compile(r"[ʻʼ’‘'`´]")
CONCEDE_PATTERNS = [re.compile(p, re.I) for p in (
    # o'zbekcha (lotin)
    r"\b(win|vin|g ?alaba|yutuq)\s+(sizga|senga|sizniki|seniki|sizda|senda|sizgaa|sizzga)\b",
    r"\b(sizga|senga)\s+(win|vin|g ?alaba)\b",
    r"\btex(ni|nik|nikni|win|vin)?\s+(oling|ol|olavering|olaver|olib qoying|olib qoy)\b",
    r"\btex(ga)?\s+(beraman|berdim|chiqaraman|bervoraman|berib qoyaman)\b",
    r"\b3\s*[:\-–]?\s*0\s*(kiriting|kirit|kiritavering|qoying|qoy|yozing|yoz|qilavering)\b",
    r"\b(oynay|oyney|oyin)\s*olmayman\b", r"\boynolmayman\b", r"\boynamayman\b", r"\boynay olmadim\b",
    # o'zbekcha (kirill)
    r"(вин|галаба|ғалаба)\s+(сизга|сенга)", r"техни\s+(олинг|ол)", r"ўйнай?\s*олмайман",
    # ruscha
    r"победа\s+(твоя|ваша|за тобой|за вами)", r"забира(й|йте)\s+(победу|тех)", r"став(ь|ьте)\s+3\s*[:\-]?\s*0",
    r"(тех|техничку|техпобеду)\s+(бери|берите|забирай|забирайте)", r"не\s+(смогу|могу)\s+(сыграть|играть)",
    # inglizcha
    r"\byou\s+(win|can have the win|take the win)\b", r"\btake\s+the\s+(win|tech)\b", r"\bi\s+can\s*n?o?t\s+play\b",
    r"\bcant\s+play\b", r"\bgive\s+you\s+the\s+win\b",
)]
NEGATION_RE = re.compile(r"\b(emas|emasku|yoq|hazil|joke|kidding|нет|шучу)\b", re.I)


def is_concession(text: str) -> bool:
    t = _APOS.sub("", str(text or "")).lower()
    if not t or t.startswith("🎮") or t.startswith("📷") or NEGATION_RE.search(t):
        return False
    return any(p.search(t) for p in CONCEDE_PATTERNS)


def migrate_concessions(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS concessions (id INTEGER PRIMARY KEY AUTOINCREMENT, mode TEXT NOT NULL, "
                "match_id INTEGER NOT NULL, user_id INTEGER NOT NULL, msg_id INTEGER NOT NULL, status TEXT NOT NULL, "
                "created_at REAL NOT NULL, UNIQUE(mode, match_id, msg_id))")


def _messages(mode: str, match_id: int) -> list[dict]:
    from chat_report import MODES as CHAT_MODES
    cfg = CHAT_MODES.get(mode)
    if not cfg:
        return []
    sql = f"SELECT id, sender_id, text FROM {cfg['msg_table']} WHERE match_id = ?"
    args: list = [int(match_id)]
    if cfg.get("playoff") is not None:
        sql += " AND is_playoff = ?"
        args.append(int(cfg["playoff"]))
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(sql + " ORDER BY id", args).fetchall()]
    finally:
        conn.close()


def _decided(mode: str, match_id: int) -> dict[int, str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT msg_id, status FROM concessions WHERE mode = ? AND match_id = ?",
                            (mode, int(match_id))).fetchall()
    except Exception:
        return {}                                       # jadval hali yo'q
    finally:
        conn.close()
    return {int(r["msg_id"]): r["status"] for r in rows}


def open_concession(mode: str, match: dict) -> dict | None:
    """Rad etilmagan eng so'nggi taslim xabari: {user_id (taslim bo'lgan), msg_id, text} yoki None."""
    p1, p2 = match.get("player1_id"), match.get("player2_id")
    decided = _decided(mode, int(match["id"]))
    for m in reversed(_messages(mode, int(match["id"]))):
        if int(m["sender_id"]) in (p1, p2) and decided.get(int(m["id"])) != "declined" and is_concession(m["text"]):
            return {"user_id": int(m["sender_id"]), "msg_id": int(m["id"]), "text": str(m["text"])[:200]}
    return None


def waiver_for(mode: str, match: dict, me: int) -> bool:
    """Raqibim menga «win sizga» degan (rad etmagan) — men xona ID siz FAQAT 3:0 kirita olaman."""
    c = open_concession(mode, match)
    return bool(c and c["user_id"] != me)


def decide(mode: str, match: dict, me: int, msg_id: int, accept: bool) -> tuple[bool, str | dict]:
    c = open_concession(mode, match)
    if not c or c["msg_id"] != int(msg_id) or c["user_id"] != me:
        return False, "concede_not_found"
    conn = get_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO concessions (mode, match_id, user_id, msg_id, status, created_at) "
                     "VALUES (?,?,?,?,?,?)", (mode, int(match["id"]), me, int(msg_id),
                                              "confirmed" if accept else "declined", time.time()))
        conn.commit()
    finally:
        conn.close()
    logger.info("TASLIM: %s #%s — user %s: %s", mode, match["id"], me, "tasdiqladi" if accept else "rad etdi")
    p1, p2 = match.get("player1_id"), match.get("player2_id")
    return True, {"winner_id": p2 if me == p1 else p1}
