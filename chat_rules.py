"""
chat_rules.py — NATIJA BOT CHATIDAGI YOZISHMALARGA QARAB (2026-11-07, egasi: «hisob kiritish chatdagi
yozishmalardan kelib chiqqan holda bo'ladi»). Faqat BOT ichidagi chat hisoblanadi (Telegram shaxsiy yozishmasi — yo'q).

TEXNIK G'ALABA (3:0) — bot o'zi beradi, tugma bosilganda (chat_rules_api.py), faqat shu holda:
  1. O'yin natijasi hali kiritilmagan (pending) va o'yinga kelishilgan vaqt qulfi yo'q (chat_agree.py).
  2. Hozir deadline'gacha TECH_CUTOFF_MIN (30) daqiqadan kam qoldi, deadline hali o'tmagan.
  3. Siz raqibning OXIRGI xabaridan keyin kamida TECH_MIN_ATTEMPTS (3) xil vaqtda yozgansiz, oralig'i
     TECH_GAP_MIN (40) daqiqadan kam emas; deadline'ga 30 daqiqa qolgandan keyin yozilganlari sanalmaydi.
     Raqib shundan keyin biror narsa yozgan bo'lsa — tex win yo'q (u javob bergan).
  4. «E'tiborsiz qoldirgan» emassiz: raqib sizga 3 xil vaqtda (oralig'i ≥40 daq) yozgan va siz orada javob
     bermagan bo'lsangiz — tex win SIZGA berilmaydi. Ikkalasi ham shunday bo'lsa — hech kimga yo'q, deadline'da 0:0.
QO'LDA NATIJA (chat_gate.py): ikkala ishtirokchi shu o'yin chatida kamida 1 marta yozgan bo'lishi kerak
  (raqib umuman yozmagan bo'lsa — faqat tex win 3:0; 5:0 kabi hiyla yopiladi). Raqib tasdiqlashiga ta'sir yo'q.
Deadline: liga/JCh/ChL/YeL/OChL/KL (+ pley-off) — har kuni 23:30; Divizion — o'yin kunidan keyingi kun 16:00;
shaxsiy turnir — tashkilotchi belgilagan tur muddati (bo'lmasa — tex win yo'q).
"""

from datetime import datetime, timedelta, timezone

from config import (DIV_DEADLINE_HOUR, DIV_DEADLINE_MINUTE, MATCHDAY_UNLOCK_HOUR, MATCHDAY_UNLOCK_MINUTE,
                    TOURNAMENT_TIMEZONE_OFFSET)
from models import get_connection

TECH_MIN_ATTEMPTS = 3          # nechta xil vaqtda yozish kerak
TECH_GAP_MIN = 40              # urinishlar orasidagi minimal oraliq (daqiqa)
TECH_CUTOFF_MIN = 30           # deadline'ga shuncha daqiqa qolgandan keyingi xabarlar sanalmaydi; tugma shundan ochiladi
TECH_SCORE = 3                 # texnik g'alaba hisobi — 3:0 (undan ko'p emas)
MANUAL_MIN_MSGS = 1            # qo'lda natija: har bir ishtirokchi chatda kamida shuncha xabar yozgan bo'lsin
TZ = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
DAILY_DEADLINE_MODES = {"league", "wc", "wc_po", "cl", "cl_po", "el", "el_po", "ac", "ac_po", "co", "co_po"}


def now_local() -> datetime:
    return datetime.now(TZ)


def parse_utc(raw) -> datetime | None:
    """SQLite CURRENT_TIMESTAMP (UTC, «YYYY-MM-DD HH:MM:SS») → Toshkent vaqti."""
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw)[:19].replace("T", " "))
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(TZ)


def fmt_local(dt: datetime | None) -> str:
    return dt.astimezone(TZ).strftime("%d.%m %H:%M") if dt else ""


# ---------------- chat va deadline ----------------

def chat_log(mode: str, match_id: int) -> list[tuple[int, datetime]]:
    """[(sender_user_id, vaqt)] vaqt bo'yicha. Jadval nomlari KODDAN (chat_report.MODES) — foydalanuvchidan emas."""
    from chat_report import MODES as CHAT_MODES
    cfg = CHAT_MODES.get(mode)
    if not cfg:
        return []
    sql = f"SELECT sender_id, created_at FROM {cfg['msg_table']} WHERE match_id = ?"
    args: list = [int(match_id)]
    if cfg.get("playoff") is not None:                  # JCh: guruh va pley-off bitta jadvalda (is_playoff)
        sql += " AND is_playoff = ?"
        args.append(int(cfg["playoff"]))
    conn = get_connection()
    try:
        rows = conn.execute(sql + " ORDER BY id", args).fetchall()
    finally:
        conn.close()
    out = [(int(r["sender_id"]), parse_utc(r["created_at"])) for r in rows]
    return sorted([x for x in out if x[1] is not None], key=lambda x: x[1])


def _next_daily(now: datetime, hour: int, minute: int) -> datetime:
    d = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return d if d > now else d + timedelta(days=1)


def deadline_for(mode: str, match: dict, now: datetime | None = None) -> datetime | None:
    now = now or now_local()
    if mode in DAILY_DEADLINE_MODES:
        return _next_daily(now, MATCHDAY_UNLOCK_HOUR, MATCHDAY_UNLOCK_MINUTE)
    if mode == "div":
        try:
            day = datetime.fromisoformat(str(match.get("day"))[:10])
        except (TypeError, ValueError):
            return None
        nxt = day + timedelta(days=1)
        return datetime(nxt.year, nxt.month, nxt.day, DIV_DEADLINE_HOUR, DIV_DEADLINE_MINUTE, tzinfo=TZ)
    if mode == "pt":
        conn = get_connection()
        try:
            r = conn.execute("SELECT round_deadline FROM pt_tournaments WHERE id = ?",
                             (match.get("tournament_id"),)).fetchone()
        finally:
            conn.close()
        return parse_utc(r["round_deadline"]) if r else None
    return None


# ---------------- qoida hisoblari ----------------

def count_attempts(times: list[datetime], gap_min: int = TECH_GAP_MIN) -> int:
    """Xil vaqtdagi urinishlar soni: keyingisi oldingi hisoblangandan ≥ gap_min keyin (ochko'z — eng ko'p son)."""
    n, last = 0, None
    for t in sorted(times):
        if last is None or t - last >= timedelta(minutes=gap_min):
            n, last = n + 1, t
    return n


def ignored_opponent(log: list[tuple[int, datetime]], me: int, cutoff: datetime) -> bool:
    """Raqib menga ketma-ket (men orada yozmay) ≥3 xil vaqtda yozganmi — men uni e'tiborsiz qoldirganmanmi."""
    run: list[datetime] = []
    for sender, t in log:
        if t >= cutoff:
            break
        if sender == me:
            run = []
        else:
            run.append(t)
            if count_attempts(run) >= TECH_MIN_ATTEMPTS:
                return True
    return False


def tech_check(mode: str, match: dict, me: int, now: datetime | None = None,
               log: list | None = None) -> tuple[bool, str, dict]:
    """(mumkinmi, sabab kodi, tafsilot {deadline, opens_at, attempts}). Natija YOZILMAYDI — faqat tekshiruv."""
    now = now or now_local()
    p1, p2 = match.get("player1_id"), match.get("player2_id")
    if me not in (p1, p2) or not p1 or not p2:
        return False, "not_participant", {}
    opp = p2 if me == p1 else p1
    if match.get("status") != "pending":
        return False, "tech_has_result", {}
    from chat_agree import active_lock
    lock = active_lock(mode, int(match["id"]), now)
    if lock:
        return False, "agree_locked", {"until": fmt_local(lock)}
    dl = deadline_for(mode, match, now)
    if dl is None:
        return False, "tech_no_deadline", {}
    cutoff = dl - timedelta(minutes=TECH_CUTOFF_MIN)
    log = chat_log(mode, int(match["id"])) if log is None else log
    info = {"deadline": fmt_local(dl), "opens_at": fmt_local(cutoff)}
    opp_times = [t for s, t in log if s == opp and t <= now]
    last_opp = max(opp_times) if opp_times else None
    mine = [t for s, t in log if s == me and t < cutoff and (last_opp is None or t > last_opp)]
    info["attempts"] = min(count_attempts(mine), TECH_MIN_ATTEMPTS)
    if now >= dl:
        return False, "tech_too_late", info
    if ignored_opponent(log, me, cutoff):
        return False, "tech_you_ignored", info
    if info["attempts"] < TECH_MIN_ATTEMPTS:
        replied = last_opp is not None and any(s == me and t < last_opp for s, t in log)
        return False, ("tech_opp_replied" if replied else "tech_need_attempts"), info
    if now < cutoff:
        return False, "tech_too_early", info
    return True, "ok", info


def manual_check(mode: str, match: dict, me: int, now: datetime | None = None) -> tuple[bool, str, dict]:
    """Qo'lda natija kiritish mumkinmi: kelishuv qulfi yo'q va ikkalasi ham chatda yozgan."""
    from chat_agree import active_lock
    lock = active_lock(mode, int(match["id"]), now or now_local())
    if lock:
        return False, "agree_locked", {"until": fmt_local(lock)}
    p1, p2 = match.get("player1_id"), match.get("player2_id")
    if me not in (p1, p2):
        return True, "ok", {}                            # ishtirokchi emas — rejimning o'zi rad etadi
    opp = p2 if me == p1 else p1
    log = chat_log(mode, int(match["id"]))
    mine = sum(1 for s, _ in log if s == me)
    theirs = sum(1 for s, _ in log if s == opp)
    if mine < MANUAL_MIN_MSGS or theirs < MANUAL_MIN_MSGS:
        return False, ("chat_opp_silent" if mine >= MANUAL_MIN_MSGS else "chat_need_both"), {}
    return True, "ok", {}
