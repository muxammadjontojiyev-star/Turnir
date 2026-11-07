"""
chat_agree.py — O'YINNI BOSHQA VAQTGA KELISHISH (2026-11-07, egasi: «o'yin boshqa kun o'ynashga kelishilgan
bo'lsa hech kim natija kirita olmasligi kerak»). Bot chatidagi «📅 Boshqa vaqtga kelishish» tugmasi.

  * Bir ishtirokchi sana-vaqt taklif qiladi → ikkinchisi «Qabul» / «Rad» bosadi (faqat raqib qabul qila oladi).
  * Qabul qilingach — kelishilgan vaqtgacha HECH KIM natija kirita olmaydi (qo'lda, skrinshot, tex win — barchasi).
  * Kelishilgan vaqt deadline'dan keyin bo'lsa — deadline'da tur odatdagidek 0:0 yopiladi (natija kiritilmagan),
    ular o'ynagach admin hisobni o'zgartiradi (egasi). Pley-offda kiritilmagan o'yin — avvalgidek admin hal qiladi.
  * Yangi taklif eskisini almashtiradi; yangi qabul — eski kelishuvni. Taklif/qabul chatga ham yoziladi
    (raqib ko'radi, va bu «yozishma» sifatida tex win qoidasida hisoblanadi).
"""

import logging
import time
from datetime import datetime, timedelta, timezone

from chat_rules import TZ, fmt_local, now_local, parse_utc
from models import get_connection

logger = logging.getLogger(__name__)

AGREE_MAX_DAYS = 7             # eng uzog'i shuncha kun oldinga
AGREE_PAST_SLACK_MIN = 1       # «hozir» tanlanganda soniyalar farqi uchun
AGREE_MSG_PROPOSE = "📅 {at} ?"
AGREE_MSG_ACCEPT = "✅ 📅 {at}"
AGREE_MSG_DECLINE = "❌ 📅 {at}"


def migrate_agreements(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS match_agreements (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "mode TEXT NOT NULL, match_id INTEGER NOT NULL, proposer_id INTEGER NOT NULL, "
                "opponent_id INTEGER NOT NULL, at_utc TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'proposed', "
                "created_at REAL NOT NULL, decided_at REAL)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_match_agreements ON match_agreements(mode, match_id, status)")


def _utc_text(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def active_lock(mode: str, match_id: int, now: datetime | None = None) -> datetime | None:
    """Qabul qilingan kelishuv vaqti hali kelmagan bo'lsa — o'sha vaqt (qulf), aks holda None."""
    now = now or now_local()
    conn = get_connection()
    try:
        r = conn.execute("SELECT at_utc FROM match_agreements WHERE mode = ? AND match_id = ? AND status = 'accepted' "
                         "ORDER BY id DESC LIMIT 1", (mode, int(match_id))).fetchone()
    except Exception:
        return None                                      # jadval hali yo'q (migratsiyadan oldin)
    finally:
        conn.close()
    at = parse_utc(r["at_utc"]) if r else None
    return at if at and at > now else None


def state(mode: str, match_id: int, me: int) -> dict:
    """{proposal: {id, at, mine} | None, agreed: {at, active} | None}"""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM match_agreements WHERE mode = ? AND match_id = ? "
                            "AND status IN ('proposed', 'accepted') ORDER BY id DESC", (mode, int(match_id))).fetchall()
    finally:
        conn.close()
    now = now_local()
    prop = next((r for r in rows if r["status"] == "proposed"), None)
    acc = next((r for r in rows if r["status"] == "accepted"), None)
    out = {"proposal": None, "agreed": None}
    if prop:
        at = parse_utc(prop["at_utc"])
        out["proposal"] = {"id": prop["id"], "at": fmt_local(at), "mine": prop["proposer_id"] == me,
                           "expired": bool(at and at <= now)}
    if acc:
        at = parse_utc(acc["at_utc"])
        out["agreed"] = {"at": fmt_local(at), "active": bool(at and at > now)}
    return out


def _chat_note(cur, mode: str, match_id: int, sender: int, text: str) -> None:
    from chat_report import MODES as CHAT_MODES
    cfg = CHAT_MODES.get(mode)
    if not cfg:
        return
    if cfg.get("playoff") is not None:
        cur.execute(f"INSERT INTO {cfg['msg_table']} (match_id, sender_id, text, is_playoff) VALUES (?, ?, ?, ?)",
                    (match_id, sender, text, int(cfg["playoff"])))
    else:
        cur.execute(f"INSERT INTO {cfg['msg_table']} (match_id, sender_id, text) VALUES (?, ?, ?)",
                    (match_id, sender, text))


def parse_at(value: str) -> datetime | None:
    """«YYYY-MM-DDTHH:MM» — Toshkent vaqti."""
    try:
        return datetime.fromisoformat(str(value).strip()[:16]).replace(tzinfo=TZ)
    except ValueError:
        return None


def propose(mode: str, match: dict, me: int, at: datetime) -> tuple[bool, str | dict]:
    from chat_rules import deadline_for
    p1, p2 = match.get("player1_id"), match.get("player2_id")
    if me not in (p1, p2) or not p1 or not p2:
        return False, "not_participant"
    if match.get("status") != "pending":
        return False, "agree_has_result"
    now = now_local()
    if at < now - timedelta(minutes=AGREE_PAST_SLACK_MIN):
        return False, "agree_in_past"
    if at > now + timedelta(days=AGREE_MAX_DAYS):
        return False, "agree_too_far"
    opp = p2 if me == p1 else p1
    mid = int(match["id"])
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE match_agreements SET status = 'replaced', decided_at = ? WHERE mode = ? AND match_id = ? "
                    "AND status = 'proposed'", (time.time(), mode, mid))
        cur.execute("INSERT INTO match_agreements (mode, match_id, proposer_id, opponent_id, at_utc, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (mode, mid, me, opp, _utc_text(at), time.time()))
        aid = cur.lastrowid
        _chat_note(cur, mode, mid, me, AGREE_MSG_PROPOSE.format(at=fmt_local(at)))
        conn.commit()
    finally:
        conn.close()
    dl = deadline_for(mode, match, now)
    logger.info("KELISHUV: %s #%s — %s taklif qildi: %s", mode, mid, me, fmt_local(at))
    return True, {"id": aid, "opponent_id": opp, "at": fmt_local(at), "after_deadline": bool(dl and at >= dl)}


def decide(agree_id: int, me: int, accept: bool) -> tuple[bool, str | dict]:
    """Raqib qabul qiladi / rad etadi; taklif qilgan o'zi — faqat bekor qiladi (accept=False)."""
    from match_modes import get_match
    conn = get_connection()
    try:
        cur = conn.cursor()
        r = cur.execute("SELECT * FROM match_agreements WHERE id = ?", (int(agree_id),)).fetchone()
        if not r or r["status"] != "proposed":
            return False, "agree_not_found"
        mine = r["proposer_id"] == me
        if me not in (r["proposer_id"], r["opponent_id"]) or (mine and accept):
            return False, "not_participant"
        at = parse_utc(r["at_utc"])
        m = get_match(r["mode"], r["match_id"]) or {}
        if accept and (m.get("status") != "pending"):
            return False, "agree_has_result"
        # o'tgan vaqtni qabul qilish — qulf qo'ymaydi (masalan «hozir o'ynaymiz»: eski kelishuv bekor bo'ladi)
        status = "accepted" if accept else ("cancelled" if mine else "declined")
        if accept:
            cur.execute("UPDATE match_agreements SET status = 'replaced', decided_at = ? WHERE mode = ? AND match_id = ? "
                        "AND status = 'accepted'", (time.time(), r["mode"], r["match_id"]))
        cur.execute("UPDATE match_agreements SET status = ?, decided_at = ? WHERE id = ? AND status = 'proposed'",
                    (status, time.time(), r["id"]))
        if not mine:
            _chat_note(cur, r["mode"], r["match_id"], me,
                       (AGREE_MSG_ACCEPT if accept else AGREE_MSG_DECLINE).format(at=fmt_local(at)))
        conn.commit()
    finally:
        conn.close()
    logger.info("KELISHUV: %s #%s — %s: %s (%s)", r["mode"], r["match_id"], me, status, fmt_local(at))
    return True, {"status": status, "mode": r["mode"], "match_id": r["match_id"], "at": fmt_local(at),
                  "proposer_id": r["proposer_id"], "opponent_id": r["opponent_id"]}
