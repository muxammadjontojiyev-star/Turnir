"""
pt_support.py — SHAXSIY turnir: ishtirokchi <-> tashkilotchi chati (2026-10-08).

Admin so'rovi: qatnashuvchilar nizolar, savollar va boshqa masalalar bo'yicha tashkilotchiga
yoza olsin. Har ishtirokchi uchun turnirda BITTA suhbat (pt_support_threads, UNIQUE): unda
ishtirokchi va boshqaruvchilar (tashkilotchi, turnir adminlari, bosh admin — pt_core.is_manager)
yozishadi. O'yin chati bilan bir xil oyna (api.js openWebChat, prefiks /pt/support) — javob
shakllari pt_chat.py bilan bir xil (qoida #26).
  - Ishtirokchi: turnir a'zosi (approved yoki pending — qo'shilish so'rovi haqida ham so'rashi mumkin).
  - Boshqaruvchi o'zi bilan suhbat ochmaydi (u javob beradi).
  - O'qildi: ishtirokchi xabari — istalgan boshqaruvchi ochganda; boshqaruvchi xabari — ishtirokchi ochganda.
Matn bazaga XOM, ko'rsatishda mask_text; frontend escHtml (qoida #35).
"""

import time as _time

from models import get_connection
from profanity import mask_text

MAX_MESSAGE_LEN = 500
_PREVIEW_LEN = 80
_TYPING_SECONDS = 6
_ONLINE_SECONDS = 70
_TYPING: dict[tuple[int, str], float] = {}       # (thread_id, "member"|"staff") -> vaqt


def _preview(text: str) -> str:
    safe, _ = mask_text(text)
    return safe if len(safe) <= _PREVIEW_LEN else safe[:_PREVIEW_LEN - 3] + "…"


def _tournament(cursor, tid: int):
    cursor.execute("SELECT id, name, owner_user_id FROM pt_tournaments WHERE id = ?", (tid,))
    return cursor.fetchone()


def _is_manager(cursor, tid: int, user_id: int, owner_id: int) -> bool:
    from pt_core import is_manager
    return is_manager(cursor, tid, user_id, owner_id)


def pt_support_open(tid: int, user_id: int) -> tuple[bool, str | dict]:
    """Ishtirokchi o'z suhbatini ochadi (yo'q bo'lsa yaratiladi, idempotent — qoida #38).
    Sabablar: not_found, not_member, is_manager. Qaytaradi: {thread_id, owner_username, owner_nickname}."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        t = _tournament(cursor, tid)
        if not t:
            return False, "not_found"
        if _is_manager(cursor, tid, user_id, t["owner_user_id"]):
            return False, "is_manager"
        cursor.execute("SELECT 1 FROM pt_members WHERE tournament_id = ? AND user_id = ?", (tid, user_id))
        if not cursor.fetchone():
            return False, "not_member"
        cursor.execute("INSERT OR IGNORE INTO pt_support_threads (tournament_id, member_user_id) VALUES (?, ?)",
                       (tid, user_id))
        conn.commit()
        cursor.execute("SELECT id FROM pt_support_threads WHERE tournament_id = ? AND member_user_id = ?", (tid, user_id))
        th = cursor.fetchone()["id"]
        cursor.execute("SELECT username, nickname FROM users WHERE id = ?", (t["owner_user_id"],))
        o = cursor.fetchone()
        return True, {"thread_id": th, "owner_username": o["username"] if o else None,
                      "owner_nickname": o["nickname"] if o else None}
    finally:
        conn.close()


def _thread(cursor, thread_id: int):
    cursor.execute("SELECT s.id, s.tournament_id, s.member_user_id, t.owner_user_id, t.name FROM pt_support_threads s "
                   "JOIN pt_tournaments t ON t.id = s.tournament_id WHERE s.id = ?", (thread_id,))
    return cursor.fetchone()


def _role(cursor, th, user_id: int) -> str | None:
    """'member' (suhbat egasi) | 'staff' (boshqaruvchi) | None (ruxsat yo'q, qoida #34)."""
    if th is None:
        return None
    if th["member_user_id"] == user_id:
        return "member"
    return "staff" if _is_manager(cursor, th["tournament_id"], user_id, th["owner_user_id"]) else None


def pt_support_send(thread_id: int, sender_id: int, text: str) -> tuple[bool, str, dict | None]:
    """(ok, sabab, notify). notify: {recipients: [{telegram_id, language}], preview, name, who, role}.
    Sabablar: empty, too_long, chat_no_access."""
    text = (text or "").strip()
    if not text:
        return False, "empty", None
    if len(text) > MAX_MESSAGE_LEN:
        return False, "too_long", None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        th = _thread(cursor, thread_id)
        role = _role(cursor, th, sender_id)
        if role is None:
            return False, "chat_no_access", None
        cursor.execute("INSERT INTO pt_support_messages (thread_id, sender_id, sender_role, text) VALUES (?, ?, ?, ?)",
                       (thread_id, sender_id, role, text))
        cursor.execute("UPDATE pt_support_threads SET last_at = CURRENT_TIMESTAMP WHERE id = ?", (thread_id,))
        conn.commit()
        if role == "member":
            from pt_core import managers_for_notify
            recipients = managers_for_notify(cursor, th["tournament_id"])
        else:
            cursor.execute("SELECT telegram_id, language FROM users WHERE id = ?", (th["member_user_id"],))
            recipients = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT telegram_id, username, nickname FROM users WHERE id = ?", (sender_id,))
        u = cursor.fetchone()
    finally:
        conn.close()
    sender_tg = u["telegram_id"] if u else None
    who = ("@" + u["username"]) if u and u["username"] else (u["nickname"] if u else "")
    return True, "ok", {"recipients": [r for r in recipients if r["telegram_id"] != sender_tg],
                        "preview": _preview(text), "name": th["name"], "who": who, "role": role}


def pt_support_messages(thread_id: int, requester_id: int) -> list[dict] | None:
    """Xabarlar (openWebChat formati). Ruxsatsiz — None. Qarshi tomon xabarlari o'qildi qilinadi."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        th = _thread(cursor, thread_id)
        role = _role(cursor, th, requester_id)
        if role is None:
            return None
        cursor.execute("UPDATE pt_support_messages SET is_read = 1, read_at = datetime('now') "
                       "WHERE thread_id = ? AND sender_role != ? AND is_read = 0", (thread_id, role))
        conn.commit()
        cursor.execute("SELECT m.id, m.sender_id, m.sender_role, m.text, m.created_at, m.is_read, u.username, u.nickname "
                       "FROM pt_support_messages m LEFT JOIN users u ON u.id = m.sender_id "
                       "WHERE m.thread_id = ? ORDER BY m.id", (thread_id,))
        out = []
        for r in cursor.fetchall():
            d = dict(r)
            d["mine"] = d["sender_id"] == requester_id
            d["is_read"] = bool(d["is_read"])
            d["club_name"] = None
            d["text"], _ = mask_text(d["text"])
            # Boshqa boshqaruvchi (masalan turnir admini) javobi — kim yozgani matn boshida
            if role == "staff" and d["sender_role"] == "staff" and not d["mine"]:
                d["text"] = f"[{'@' + d['username'] if d['username'] else d['nickname'] or ''}] {d['text']}"
            for k in ("username", "nickname", "sender_role"):
                d.pop(k, None)
            out.append(d)
        return out
    finally:
        conn.close()


def pt_support_typing(thread_id: int, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        role = _role(cursor, _thread(cursor, thread_id), user_id)
    finally:
        conn.close()
    if role is None:
        return False
    _TYPING[(thread_id, role)] = _time.time()
    return True


def pt_support_state(thread_id: int, requester_id: int) -> dict | None:
    """Ishtirokchiga — tashkilotchi holati; boshqaruvchiga — ishtirokchi holati (openWebChat formati)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        th = _thread(cursor, thread_id)
        role = _role(cursor, th, requester_id)
        if role is None:
            return None
        other = th["owner_user_id"] if role == "member" else th["member_user_id"]
        cursor.execute("SELECT username, (julianday('now') - julianday(last_seen)) * 86400.0 AS secs "
                       "FROM users WHERE id = ?", (other,))
        u = cursor.fetchone()
    finally:
        conn.close()
    secs = int(u["secs"]) if u and u["secs"] is not None else None
    online = secs is not None and secs <= _ONLINE_SECONDS
    other_role = "staff" if role == "member" else "member"
    typing = (_time.time() - _TYPING.get((thread_id, other_role), 0)) <= _TYPING_SECONDS
    return {"online": online, "typing": typing, "last_seen_seconds": 0 if online else secs,
            "opponent_username": u["username"] if u else None, "opponent_user_id": other}


def pt_support_threads(tid: int, user_id: int) -> list[dict] | None:
    """Boshqaruvchiga: turnirdagi suhbatlar (eng yangisi birinchi, xabarsizlari yo'q). Ruxsatsiz — None."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        t = _tournament(cursor, tid)
        if not t or not _is_manager(cursor, tid, user_id, t["owner_user_id"]):
            return None
        cursor.execute(
            "SELECT s.id AS thread_id, s.member_user_id AS user_id, u.username, u.nickname, pm.team_name, "
            "(SELECT text FROM pt_support_messages WHERE thread_id = s.id ORDER BY id DESC LIMIT 1) AS last_text, "
            "(SELECT sender_role FROM pt_support_messages WHERE thread_id = s.id ORDER BY id DESC LIMIT 1) AS last_role, "
            "(SELECT created_at FROM pt_support_messages WHERE thread_id = s.id ORDER BY id DESC LIMIT 1) AS last_at, "
            "(SELECT COUNT(*) FROM pt_support_messages WHERE thread_id = s.id AND sender_role = 'member' "
            " AND is_read = 0) AS unread "
            "FROM pt_support_threads s JOIN users u ON u.id = s.member_user_id "
            "LEFT JOIN pt_members pm ON pm.tournament_id = s.tournament_id AND pm.user_id = s.member_user_id "
            "WHERE s.tournament_id = ? AND EXISTS (SELECT 1 FROM pt_support_messages WHERE thread_id = s.id) "
            "ORDER BY unread > 0 DESC, last_at DESC", (tid,))
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    from pt_rounds import utc_to_local_text
    for r in rows:
        r["last_text"] = _preview(r["last_text"] or "")
        r["last_local"] = utc_to_local_text(r.pop("last_at"))
    return rows


def support_unread(tid: int, user_id: int, manager: bool) -> int:
    """Turnir tafsiloti uchun (pt_core): boshqaruvchiga — o'qilmagan ishtirokchi xabarlari,
    ishtirokchiga — o'qilmagan tashkilotchi javoblari."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        base = ("SELECT COUNT(*) AS c FROM pt_support_messages m JOIN pt_support_threads s ON s.id = m.thread_id "
                "WHERE s.tournament_id = ? AND m.is_read = 0 AND ")
        if manager:
            cursor.execute(base + "m.sender_role = 'member'", (tid,))
        else:
            cursor.execute(base + "m.sender_role = 'staff' AND s.member_user_id = ?", (tid, user_id))
        return cursor.fetchone()["c"]
    finally:
        conn.close()
