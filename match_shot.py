"""
match_shot.py — NATIJANI MATCH HISTORY SKRINSHOTI BILAN YOZISH (2026-11-06, egasi so'rovi). Barcha rejimlar.

Oqim: ishtirokchi skrinshot yuklaydi (read_shot) → bot o'yin qatorlarini o'qiydi (match_shot_ocr) → ishtirokchi
aynan o'ynalgan qatorni tanlaydi (apply_shot) → bot tekshiradi:
  * ikkala ishtirokchining eFootball niknamei (ef_nick) qatordagi niknamelarga mos (kichik o'qish xatolariga chidamli);
  * sana-vaqt o'yin ochilgandan keyin va SHOT_MAX_AGE_H ichida (Toshkent vaqti; dd/mm va mm/dd ikkalasi sinanadi);
  * bu eFootball o'yini avval boshqa natija uchun ishlatilmagan (match_shots.fp UNIQUE);
→ natija DARHOL tasdiqlanadi (rejimning o'z submit + raqib nomidan confirm, match_modes). Raqibga xabar —
DISPUTE_HOURS ichida «E'tiroz» bosa oladi → o'yin skrinshot bilan adminga (match_claims.py ro'yxati).
Pley-offda durang (penaltilar) — hozircha skrinshot bilan EMAS (egasi namunani yuboradi), oddiy tartibda.
"""

import io
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from models import get_connection

logger = logging.getLogger(__name__)

TZ_LOCAL = timezone(timedelta(hours=5))   # Toshkent (o'yin vaqti skrinshotda telefon vaqtida)
SHOT_MAX_AGE_H = 72               # shundan eski o'yin qabul qilinmaydi
# 2026-11-06 (egasi: «bugungi o'yinni o'tgan kungi deyapti»): eFootball Match History vaqti telefon / o'yin serveri
# mintaqasida bo'lishi mumkin (Toshkentdan bir necha soat oldinda yoki orqada) — shuning uchun keng oyna.
# Bir o'yinni ikki marta ishlatish baribir mumkin emas (_shot_used), shu sabab oyna kengligi xavfsiz.
SHOT_FUTURE_MIN = 12 * 60         # o'yin vaqti Toshkentdan shuncha oldinda ko'rinishi mumkin (vaqt mintaqasi)
OPEN_SLACK_MIN = 12 * 60          # o'yin ochilishidan shuncha oldin ko'ringani ham qabul (vaqt mintaqasi)
DISPUTE_HOURS = 12
NICK_MATCH_MIN = 0.86             # nikname o'xshashligi (OCR xatolari: «_» ↔ « », 0 ↔ O)
READ_DAILY_LIMIT = 30
READ_TTL_S = 15 * 60              # o'qilgan skrinshot tanlash uchun shuncha saqlanadi
SHOT_IMG_MAX = 1600
SHOT_IMG_Q = 80
_READS: dict[str, dict] = {}      # token → {user_id, rows, img, at}
_READ_COUNT: dict[tuple[int, str], int] = {}
_NICK_REMIND: set[int] = set()    # niknameini kiritmagan raqiblar — API eslatma yuboradi (match_shot_api)


def migrate_match_shots(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS match_shots (id INTEGER PRIMARY KEY AUTOINCREMENT, mode TEXT NOT NULL, "
                "match_id INTEGER NOT NULL, uploader_id INTEGER NOT NULL, opponent_id INTEGER NOT NULL, "
                "score1 INTEGER, score2 INTEGER, played_at TEXT, fp TEXT UNIQUE, img BLOB, "
                "status TEXT NOT NULL DEFAULT 'applied', created_at REAL, disputed_at REAL)")


def _key(s: str) -> str:
    return re.sub(r"[\s_.\-]+", "", (s or "").casefold()).replace("0", "o").replace("1", "l")


def nick_sim(a: str, b: str) -> float:
    ka, kb = _key(a), _key(b)
    return SequenceMatcher(None, ka, kb).ratio() if ka and kb else 0.0


def _jpeg(raw: bytes) -> bytes:
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((SHOT_IMG_MAX, SHOT_IMG_MAX))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=SHOT_IMG_Q)
    return out.getvalue()


def _played_at(row: dict, opened: datetime | None) -> datetime | None:
    """Skrinshot sanasi (Toshkent) — oyna ichida bo'lsa; dd/mm va mm/dd sinanadi. Vaqt o'qilmagan bo'lsa —
    o'sha kunning istalgan vaqti oynaga tushsa qabul (vaqt o'rniga oynadagi eng yaqin payt olinadi)."""
    now = datetime.now(TZ_LOCAL)
    lo = now - timedelta(hours=SHOT_MAX_AGE_H)
    if opened:
        lo = max(lo, opened - timedelta(minutes=OPEN_SLACK_MIN))
    hi = now + timedelta(minutes=SHOT_FUTURE_MIN)
    try:
        a, b, y = re.split(r"[/.\-]", row["date"])
    except ValueError:
        return None
    tm = row.get("time")
    for d, m in ((a, b), (b, a)):
        try:
            if tm:
                hh, mm = tm.split(":")
                dt = datetime(int(y), int(m), int(d), int(hh), int(mm), tzinfo=TZ_LOCAL)
                if lo <= dt <= hi:
                    return dt
            else:
                day0 = datetime(int(y), int(m), int(d), tzinfo=TZ_LOCAL)
                day1 = day0 + timedelta(days=1) - timedelta(minutes=1)
                if day1 >= lo and day0 <= hi:
                    return min(max(day0, lo), hi)
        except ValueError:
            continue
    logger.info("MATCH SHOT: sana oynadan tashqari — o'qildi %s %s; oyna %s … %s (ochilgan %s)",
                row.get("date"), tm, lo.strftime("%d.%m %H:%M"), hi.strftime("%d.%m %H:%M"),
                opened.strftime("%d.%m %H:%M") if opened else "-")
    return None


def _opened(match: dict) -> datetime | None:
    """O'yin ochilgan payt (Toshkent): created_at — SQLite UTC «YYYY-MM-DD HH:MM:SS»; open_date — mahalliy sana."""
    try:
        if match.get("created_at"):
            dt = datetime.fromisoformat(str(match["created_at"])[:19])
            return dt.replace(tzinfo=timezone.utc).astimezone(TZ_LOCAL)
        if match.get("open_date"):
            return datetime.fromisoformat(str(match["open_date"])[:10]).replace(tzinfo=TZ_LOCAL)
    except ValueError:
        return None
    return None


async def read_shot(user_id: int, raw: bytes) -> tuple[bool, str | dict]:
    import asyncio
    import secrets
    from match_shot_ocr import read_rows
    today = datetime.now(TZ_LOCAL).date().isoformat()
    k = (user_id, today)
    if _READ_COUNT.get(k, 0) >= READ_DAILY_LIMIT:
        return False, "daily_limit"
    try:
        img = await asyncio.to_thread(_jpeg, raw)
        rows = await asyncio.to_thread(read_rows, raw)
    except RuntimeError:
        return False, "ocr_unavailable"
    except Exception:
        logger.exception("MATCH SHOT: o'qib bo'lmadi (user %s)", user_id)
        return False, "bad_image"
    _READ_COUNT[k] = _READ_COUNT.get(k, 0) + 1
    if not rows:
        return False, "no_rows"
    now = time.time()
    for t in [t for t, v in _READS.items() if now - v["at"] > READ_TTL_S]:
        _READS.pop(t, None)
    token = secrets.token_urlsafe(12)
    _READS[token] = {"user_id": user_id, "rows": rows, "img": img, "at": now}
    return True, {"token": token, "rows": rows}


FP_TIME_TOL_MIN = 10             # belgi chizig'i ostidagi vaqt biroz noto'g'ri o'qilsa ham — o'sha o'yin


def _fp_prefix(row: dict, played: datetime) -> str:
    nicks = "|".join(sorted([_key(row["left"]), _key(row["right"])]))
    return f"{nicks}|{played:%Y-%m-%d}|{row['s_left']}-{row['s_right']}|"


def _fp(row: dict, played: datetime) -> str:
    return _fp_prefix(row, played) + f"{played:%H:%M}"


def _shot_used(conn, row: dict, played: datetime) -> bool:
    """Shu eFootball o'yini (niknamelar, sana, hisob, vaqt ±FP_TIME_TOL_MIN) avval ishlatilganmi."""
    pre = _fp_prefix(row, played)
    for r in conn.execute("SELECT fp FROM match_shots WHERE substr(fp, 1, ?) = ?", (len(pre), pre)):
        try:
            hh, mm = r["fp"][len(pre):].split(":")
        except ValueError:
            return True
        if abs((int(hh) * 60 + int(mm)) - (played.hour * 60 + played.minute)) <= FP_TIME_TOL_MIN:
            return True
    return False


def _check_row(mode: str, match: dict, user_id: int, row: dict) -> tuple[str | None, dict]:
    """(xato | None, {s1, s2, opponent_id, played})"""
    from ef_nick import nicks_for_users
    p1, p2 = match["player1_id"], match["player2_id"]
    if user_id not in (p1, p2) or not p2:
        return "not_participant", {}
    nicks = nicks_for_users([p1, p2])
    opp = p2 if user_id == p1 else p1
    if user_id not in nicks:
        return "no_my_nick", {}
    if opp not in nicks:
        return "no_opp_nick", {"opponent_id": opp, "my_nick": nicks[user_id]}
    if _key(nicks[p1]) == _key(nicks[p2]):
        return "same_person", {}                        # bitta eFootball akkaunt ikkala tomonda (ef_nick_link)
    straight = min(nick_sim(row["left"], nicks[p1]), nick_sim(row["right"], nicks[p2]))
    swapped = min(nick_sim(row["left"], nicks[p2]), nick_sim(row["right"], nicks[p1]))
    if max(straight, swapped) < NICK_MATCH_MIN:
        return "nick_mismatch", {"detail": f"{nicks[p1]} / {nicks[p2]}"}   # ro'yxatdagi niknamelar — foydalanuvchiga
    s1, s2 = (row["s_left"], row["s_right"]) if straight >= swapped else (row["s_right"], row["s_left"])
    played = _played_at(row, _opened(match))
    if played is None:
        return "bad_date", {}
    from match_modes import MODES
    if MODES[mode]["playoff"] and s1 == s2:
        return "playoff_draw", {}
    return None, {"s1": s1, "s2": s2, "opponent_id": opp, "played": played}


GARBLED_NICK_MIN = 3                                   # bundan qisqa nikname — belgi chizig'i yozuvni yopgan


def _garbled(row: dict) -> bool:
    """Qator nikname(lar)i o'qilmay qolganmi (belgi chizig'i ustidan o'tgan)."""
    return min(len(_key(row.get("left") or "")), len(_key(row.get("right") or ""))) < GARBLED_NICK_MIN


async def apply_shot(user: dict, mode: str, match_id: int, token: str, row_idx: int,
                     expect: tuple[int, int] | None = None) -> tuple[bool, str | dict]:
    """expect — qo'lda kiritilgan YIRIK hisob (player1, player2): skrinshotdagi bilan bir xil bo'lsa — darhol tasdiq."""
    from match_modes import MODES, confirm_as, get_match, submit_as
    from queries_users import get_user_by_id
    rd = _READS.get(token)
    if not rd or rd["user_id"] != user["id"] or not (0 <= row_idx < len(rd["rows"])):
        return False, "expired"
    if mode not in MODES:
        return False, "bad_mode"
    match = get_match(mode, match_id)
    if not match:
        return False, "match_not_found"
    if match.get("status") == "confirmed":
        return False, "already_confirmed"
    row = rd["rows"][row_idx]
    why, r = _check_row(mode, match, user["id"], row)
    awaiting = why == "no_opp_nick"
    if awaiting:                                        # raqib niknamesi yo'q — u tasdiqlaydi (match_shot_await)
        from match_shot_await import check_await
        why, r = check_await(mode, match, user["id"], row, r["my_nick"])
    if why == "nick_mismatch" and row.get("marked") and _garbled(row):
        return False, "mark_over_text"                 # belgi chizig'i nikname ustidan o'tib, o'qib bo'lmadi
    if why == "nick_mismatch":                          # 2026-11-06: haqiqiy sabab yashirilmaydi — ro'yxatdagi niknamelar
        return False, f"nick_mismatch|{(r or {}).get('detail', '')}".rstrip("|")
    if why == "bad_date":
        return False, f"bad_date|{row.get('date', '')} {row.get('time') or ''}".strip()
    if why:
        return False, why
    fp = _fp(row, r["played"])
    conn = get_connection()
    try:
        if _shot_used(conn, row, r["played"]):
            return False, "shot_used"
    finally:
        conn.close()
    s1, s2, opp = r["s1"], r["s2"], get_user_by_id(r["opponent_id"])
    if expect is not None and (s1, s2) != tuple(expect):  # 2026-11-07: yirik hisob — skrinshot bilan bir xil bo'lsin
        me1 = user["id"] == match["player1_id"]
        return False, f"shot_score_mismatch|{s1 if me1 else s2}:{s2 if me1 else s1}"
    if awaiting:
        from match_shot_await import apply_await
        ok, res = await apply_await(user, mode, match, r, fp, rd["img"])
        if not ok:
            return False, res
        _READS.pop(token, None)
        my = s1 if user["id"] == match["player1_id"] else s2
        their = s2 if user["id"] == match["player1_id"] else s1
        return True, {"score1": s1, "score2": s2, "admin_pending": res["admin_pending"], "await_opp": res["await_opp"],
                      "opponent": opp, "my": my, "their": their, "opp_nick": r["opp_nick"]}
    sub = match.get("submitted_by")
    if sub and sub == opp["id"]:
        if (match.get("score1"), match.get("score2")) != (s1, s2):
            return False, "opp_other_score"           # raqib boshqa hisob kiritgan — rad eting, admin hal qiladi
        ok, res = await confirm_as(mode, match_id, user)
    elif sub and sub == user["id"]:
        if (match.get("score1"), match.get("score2")) != (s1, s2):
            return False, "my_other_score"
        ok, res = await confirm_as(mode, match_id, opp)
    else:
        ok, res = await submit_as(mode, match_id, s1, s2, user)
        if ok and "admin_pending" not in str(res):
            ok, res = await confirm_as(mode, match_id, opp)
        elif ok and expect is not None:                 # yirik hisob, skrinshot = kiritilgan → admin kutilmaydi
            from match_modes import force_set
            ok, res = force_set(mode, match_id, s1, s2)
    if not ok:
        return False, str(res)
    pending = "admin_pending" in str(res)
    conn = get_connection()
    try:
        conn.execute("INSERT INTO match_shots (mode, match_id, uploader_id, opponent_id, score1, score2, played_at, fp, "
                     "img, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (mode, match_id, user["id"], opp["id"], s1, s2, r["played"].isoformat(), fp, rd["img"],
                      "admin_pending" if pending else "applied", time.time()))
        conn.commit()
    finally:
        conn.close()
    _READS.pop(token, None)
    logger.info("MATCH SHOT: %s #%s — %s:%s (user %s, skrinshot)", mode, match_id, s1, s2, user["id"])
    my = s1 if user["id"] == match["player1_id"] else s2
    their = s2 if user["id"] == match["player1_id"] else s1
    return True, {"score1": s1, "score2": s2, "admin_pending": pending, "await_opp": False, "opponent": opp, "my": my, "their": their}

