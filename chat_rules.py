"""
chat_rules.py — NATIJA BOT CHATIDAGI YOZISHMALARGA QARAB (2026-11-07, egasi: «hisob kiritish chatdagi
yozishmalardan kelib chiqqan holda bo'ladi»). Faqat BOT ichidagi chat hisoblanadi (Telegram shaxsiy yozishmasi — yo'q).

TEXNIK G'ALABA (3:0) — bot o'zi beradi, tugma bosilganda (chat_rules_api.py), faqat shu holda:
  1. O'yin natijasi hali kiritilmagan (pending) va o'yinga kelishilgan vaqt qulfi yo'q (chat_agree.py).
  2. Hozir deadline'gacha TECH_CUTOFF_MIN (30) daqiqadan kam qoldi, deadline hali o'tmagan.
  3. Siz raqibning OXIRGI xabaridan keyin kamida TECH_MIN_ATTEMPTS (3) xil vaqtda yozgansiz, oralig'i
     TECH_GAP_MIN (40) daqiqadan kam emas; deadline'ga 30 daqiqa qolgandan keyin yozilganlari sanalmaydi.
     Raqib shundan keyin biror narsa yozgan bo'lsa — tex win yo'q (u javob bergan).
  3b. YOKI (2026-11-07, egasi: «men unga deadlinegacha umuman javob bermaganman — Diyorbek haqli edi»): chatdagi
     OXIRGI xabar sizniki, u raqibning xabariga javob (raqib avval yozgan), deadline'ga 30 daqiqa qolishidan oldin
     yozilgan va raqib kamida TECH_REPLY_WAIT_MIN (30) daqiqa javob bermagan — javobsiz qoldirgan raqib yutqazadi.
     Faqat O'ZI o'z vaqtida javob bergan bo'lsa: raqib xabaridan keyin birinchi javobingiz reply_max_h() (standart 3)
     soat ichida yozilgan (bosh admin Admin → «📸 SKRINSHOT VA TEXNIK G'ALABA» da o'zgartiradi). Kech javob
     bergan — faqat 3 urinish qoidasi bilan.
  4. «E'tiborsiz qoldirgan» emassiz: raqib sizga 3 xil vaqtda (oralig'i ≥40 daq) yozgan va siz orada javob
     bermagan bo'lsangiz — tex win SIZGA berilmaydi. Ikkalasi ham shunday bo'lsa — hech kimga yo'q, deadline'da 0:0.
QO'LDA NATIJA (chat_gate.py; 2026-11-07 egasi: «har qanday qo'lda natija»): bot chatida bir tomon xona ID yuborgan,
  ikkinchi tomon uni chatda bosib nusxalagan bo'lishi kerak (chat_room.py). Aks holda — faqat tex win 3:0.
  Raqib tasdiqlashi, skrinshotli natija, admin tuzatishlari — ta'sir yo'q.
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
TECH_REPLY_WAIT_MIN = 30       # 3b: oxirgi (javob) xabaringizdan keyin raqib shuncha daqiqa jim bo'lsa — tex win
FLAG_REPLY_MAX_H = "tech_reply_max_h"   # 3b: javobingiz raqib xabaridan keyin shuncha soat ichida bo'lsin (app_flags)
REPLY_MAX_H_DEFAULT, REPLY_MAX_H_MIN, REPLY_MAX_H_MAX = 3, 1, 24
TZ = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
DAILY_DEADLINE_MODES = {"league", "wc", "wc_po", "cl", "cl_po", "el", "el_po", "ac", "ac_po", "co", "co_po"}


def reply_max_h() -> int:
    conn = get_connection()
    try:
        r = conn.execute("SELECT value FROM app_flags WHERE key = ?", (FLAG_REPLY_MAX_H,)).fetchone()
    except Exception:
        r = None
    finally:
        conn.close()
    try:
        return max(REPLY_MAX_H_MIN, min(REPLY_MAX_H_MAX, int(r["value"]))) if r else REPLY_MAX_H_DEFAULT
    except (TypeError, ValueError):
        return REPLY_MAX_H_DEFAULT


def set_reply_max_h(hours: int) -> int:
    h = max(REPLY_MAX_H_MIN, min(REPLY_MAX_H_MAX, int(hours)))
    conn = get_connection()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS app_flags (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO app_flags (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                     (FLAG_REPLY_MAX_H, str(h)))
        conn.commit()
    finally:
        conn.close()
    return h


def _reply_in_time(seen: list, me: int, last_t: datetime) -> bool:
    """3b: raqibning (oxirgi xabarim oldidagi) so'nggi xabaridan keyin birinchi javobim reply_max_h soat ichidami."""
    prev_opp = max((t for s, t in seen if s != me and t < last_t), default=None)
    if prev_opp is None:
        return False
    first = min(t for s, t in seen if s == me and t > prev_opp)
    return first - prev_opp <= timedelta(hours=reply_max_h())


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
    seen = [(s, t) for s, t in log if t <= now]
    last = seen[-1] if seen else None                  # 3b: oxirgi xabar meniki — raqibga javob, u esa jim
    unanswered = bool(last and last[0] == me and last[1] < cutoff and any(s == opp and t < last[1] for s, t in seen))
    late = unanswered and not _reply_in_time(seen, me, last[1])
    unanswered = unanswered and not late
    info["unanswered"], info["late_reply"] = unanswered, late
    if now >= dl:
        return False, "tech_too_late", info
    if ignored_opponent(log, me, cutoff):
        return False, "tech_you_ignored", info
    if info["attempts"] < TECH_MIN_ATTEMPTS and not unanswered:
        replied = last_opp is not None and any(s == me and t < last_opp for s, t in log)
        if late:
            return False, "tech_late_reply", {**info, "max_h": reply_max_h()}
        return False, ("tech_opp_replied" if replied else "tech_need_attempts"), info
    if now < cutoff:
        return False, "tech_too_early", info
    if info["attempts"] < TECH_MIN_ATTEMPTS:          # faqat 3b bo'yicha — raqibga javob berish uchun vaqt qolsin
        wait_until = last[1] + timedelta(minutes=TECH_REPLY_WAIT_MIN)
        if now < wait_until:
            info["wait_until"] = fmt_local(wait_until)
            return False, "tech_wait_reply", info
    return True, "ok", info


def manual_check(mode: str, match: dict, me: int, now: datetime | None = None) -> tuple[bool, str, dict]:
    """Qo'lda natija kiritish mumkinmi: kelishuv qulfi yo'q va xona ID almashilgan (yuborildi + raqib nusxaladi)."""
    from chat_agree import active_lock
    lock = active_lock(mode, int(match["id"]), now or now_local())
    if lock:
        return False, "agree_locked", {"until": fmt_local(lock)}
    p1, p2 = match.get("player1_id"), match.get("player2_id")
    if me not in (p1, p2):
        return True, "ok", {}                            # ishtirokchi emas — rejimning o'zi rad etadi
    from chat_room import room_check
    ok, why = room_check(mode, int(match["id"]), me, p2 if me == p1 else p1)
    return ok, why, {}
