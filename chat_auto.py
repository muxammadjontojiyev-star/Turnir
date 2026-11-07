"""
chat_auto.py — TEX WIN 3:0 NI YOZISH (umumiy) va DEADLINE'DA AVTOMATIK TEX WIN (2026-11-07).

Egasi: «chat holatidan kelib chiqib win olishga haqli bo'lgan ishtirokchi deadline'dan oldin tugmani bosishga
ulgurmasa yoki botga kirolmasa — botning o'zi 3:0 qilib tasdiqlashi kerak».

  * apply_techwin — g'olib nomidan 3:0 kiritiladi + mag'lub nomidan tasdiqlanadi (rejimlarning o'z funksiyalari,
    match_modes — barcha tekshiruvlari ishlaydi; ikki marta yozilmaydi: natija bor bo'lsa rejim rad etadi).
    Sabablar (kind): button — tugma, auto — deadline'da bot, concede — «win sizga» (chat_concede.py).
  * sweep — scheduler har daqiqada chaqiradi: deadline'ga SWEEP_BEFORE_MIN daqiqa qolganda, chatida yozishma bor
    ochiq (pending) o'yinlar tekshiriladi: faqat BITTA tomon tex winga haqli bo'lsa (chat_rules.tech_check,
    deadline lahzasi bo'yicha) yoki raqib «win sizga» degan bo'lsa — 3:0. Ikkalasi ham / hech kim — tegilmaydi (0:0).
    Chatda xona ID almashilgan (yuborilgan + nusxalangan) o'yinga bot avtomatik tegmaydi — ular o'ynagan bo'lishi
    mumkin (natijani kiritishni unutgan); tugma bilan so'rash va «win sizga» — avvalgidek.
"""

import logging
from datetime import timedelta

from models import get_connection

logger = logging.getLogger(__name__)

SWEEP_BEFORE_MIN = 3            # deadline'dan shuncha daqiqa oldin tekshiriladi (scheduler — daqiqada bir)
SWEEP_EVAL_BEFORE_S = 1         # qoida deadline'dan 1 soniya oldingi holat bo'yicha baholanadi
NOTIFY_KEYS = {                 # kind → (mag'lubga, g'olibga)
    "button": ("crule_notify_tech_lost", None),
    "auto": ("crule_notify_tech_lost", "crule_notify_tech_auto_won"),
    "concede": ("crule_notify_concede_lost", "crule_notify_concede_won"),
}


async def apply_techwin(mode: str, match_id: int, winner_id: int, kind: str = "button") -> tuple[bool, str | dict]:
    from chat_rules import TECH_SCORE
    from match_modes import confirm_as, get_match, submit_as
    from queries_users import get_user_by_id
    m = get_match(mode, match_id)
    if not m or m.get("status") != "pending":
        return False, "tech_has_result"
    p1, p2 = m.get("player1_id"), m.get("player2_id")
    if winner_id not in (p1, p2):
        return False, "not_participant"
    loser_id = p2 if winner_id == p1 else p1
    s1, s2 = (TECH_SCORE, 0) if winner_id == p1 else (0, TECH_SCORE)
    winner, loser = get_user_by_id(winner_id), get_user_by_id(loser_id)
    if not winner or not loser:
        return False, "opponent_not_found"
    ok, res = await submit_as(mode, match_id, s1, s2, winner)
    if not ok:
        return False, str(res)
    ok2, res2 = await confirm_as(mode, match_id, loser)
    if not ok2:                                        # kiritildi, tasdiq bo'lmadi — rejim deadline'da tasdiqlaydi
        logger.error("TEX WIN: tasdiqlanmadi %s #%s: %s", mode, match_id, res2)
    logger.info("TEX WIN (%s): %s #%s — user %s 3:0 (tasdiq: %s)", kind, mode, match_id, winner_id, ok2)
    await _notify(mode, match_id, kind, winner, loser)
    return True, {"score1": s1, "score2": s2, "status": (get_match(mode, match_id) or {}).get("status")}


async def _notify(mode: str, match_id: int, kind: str, winner: dict, loser: dict) -> None:
    from chat_rules_api import _tell
    from match_shot_api import _tell_admins
    to_loser, to_winner = NOTIFY_KEYS.get(kind, NOTIFY_KEYS["button"])
    await _tell(loser["id"], to_loser, mode)
    if to_winner:
        await _tell(winner["id"], to_winner, mode)
    await _tell_admins(mode, match_id, "crule_admin_tech",
                       winner=winner.get("nickname") or winner.get("username") or str(winner["id"]))


def _pending_with_chat(mode: str) -> list[dict]:
    """Chatida kamida bitta xabar bor ochiq o'yinlar (faqat ular tex winga haqli bo'lishi mumkin)."""
    from chat_report import MODES as CHAT_MODES
    from match_modes import get_match
    cfg = CHAT_MODES.get(mode)
    if not cfg:
        return []
    po = f" AND is_playoff = {int(cfg['playoff'])}" if cfg.get("playoff") is not None else ""
    conn = get_connection()
    try:
        ids = [r[0] for r in conn.execute(
            f"SELECT DISTINCT m.id FROM {cfg['match_table']} m WHERE m.status = 'pending' AND m.id IN "
            f"(SELECT match_id FROM {cfg['msg_table']} WHERE 1=1{po})").fetchall()]
    finally:
        conn.close()
    return [m for m in (get_match(mode, i) for i in ids) if m]


def _mode_window(mode: str, now) -> bool:
    """Rejimning umumiy deadline'i yaqinmi (kunlik 23:30 / Divizion 16:00); xususiy turnir — har doim tekshiriladi."""
    from chat_rules import DAILY_DEADLINE_MODES, _next_daily
    from config import DIV_DEADLINE_HOUR, DIV_DEADLINE_MINUTE, MATCHDAY_UNLOCK_HOUR, MATCHDAY_UNLOCK_MINUTE
    if mode in DAILY_DEADLINE_MODES:
        h, mi = MATCHDAY_UNLOCK_HOUR, MATCHDAY_UNLOCK_MINUTE
    elif mode == "div":
        h, mi = DIV_DEADLINE_HOUR, DIV_DEADLINE_MINUTE
    else:
        return True
    return _next_daily(now, h, mi) - now <= timedelta(minutes=SWEEP_BEFORE_MIN)


async def sweep(now=None) -> int:
    """Deadline arafasida avtomatik tex win. Qaytaradi: yozilgan o'yinlar soni."""
    from chat_concede import open_concession
    from chat_room import room_check
    from chat_rules import deadline_for, now_local, tech_check
    from match_modes import MODES
    now = now or now_local()
    done = 0
    for mode in MODES:
        if not _mode_window(mode, now):                # har daqiqa barcha o'yinlarni so'ramaslik uchun
            continue
        try:
            matches = _pending_with_chat(mode)
        except Exception:
            logger.exception("TEX WIN sweep: %s ro'yxati", mode)
            continue
        for m in matches:
            try:
                dl = deadline_for(mode, m, now)
                if not dl or not (dl - timedelta(minutes=SWEEP_BEFORE_MIN) <= now < dl):
                    continue
                at = dl - timedelta(seconds=SWEEP_EVAL_BEFORE_S)
                p1, p2 = m["player1_id"], m["player2_id"]
                c = open_concession(mode, m)
                if not c and room_check(mode, int(m["id"]), p1, p2)[0]:
                    continue                            # xona ID almashilgan — o'yin bo'lgan bo'lishi mumkin: bot tegmaydi
                won = [p for p in (p1, p2) if p and tech_check(mode, m, p, now=at)[0]]
                if c:                                   # «win sizga» (rad etilmagan) — har doim raqibiga
                    won = [p2 if c["user_id"] == p1 else p1]
                if len(won) == 1:
                    ok, _ = await apply_techwin(mode, int(m["id"]), won[0], "concede" if c else "auto")
                    done += int(ok)
            except Exception:
                logger.exception("TEX WIN sweep: %s #%s", mode, m.get("id"))
    if done:
        logger.info("TEX WIN sweep: %s ta o'yinga bot 3:0 yozdi", done)
    return done
