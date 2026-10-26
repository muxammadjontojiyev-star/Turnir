"""
tb_leagues_bulk.py — "TEAMLAR JANGI": bosh admin sozlamalarni BARCHA ligalarga birdan qo'llaydi (2026-10-26).
tb_leagues.py 300 qatordan oshmasligi uchun alohida (qoida #21). Har liga tb_leagues.tb_league_update orqali
yangilanadi — tekshiruv bir joyda (qoida #26). Endpoint: POST /tb/admin/leagues/bulk-settings (tb_api_league.py).
"""

import logging

from tb_leagues import TB_LINEUP_CEIL, TB_LINEUP_FLOOR, _int_in, tb_league_update, tb_leagues_list

logger = logging.getLogger(__name__)


def tb_leagues_bulk_update(data: dict) -> tuple[bool, str | dict]:
    """
    2026-10-26 (bosh admin): tarkib min/max va divizion hajmini BARCHA ligalarga qo'llaydi.
    Berilmagan maydon o'zgarmaydi. Har liga tb_league_update orqali (bitta tekshiruv, qoida #26).
    Sabablar: nothing_to_update, bad_lineup_limits, bad_division_size (qiymatning o'zi noto'g'ri).
    Qaytaradi: {updated, failed: [{league_id, name, reason}]} — failed: shu ligaga mos kelmadi (masalan min > max).
    """
    keys = ("lineup_min", "lineup_max", "division_size")
    upd = {k: data[k] for k in keys if data.get(k) not in (None, "")}
    if not upd:
        return False, "nothing_to_update"
    from tb_season import TB_DIV_SIZE_MAX, TB_DIV_SIZE_MIN
    for k in ("lineup_min", "lineup_max"):                 # qiymatning o'zi noto'g'ri — bitta xato, hech narsa o'zgarmaydi
        if k in upd and _int_in(upd[k], TB_LINEUP_FLOOR, TB_LINEUP_CEIL) is None:
            return False, "bad_lineup_limits"
    if "lineup_min" in upd and "lineup_max" in upd and int(upd["lineup_min"]) > int(upd["lineup_max"]):
        return False, "bad_lineup_limits"
    if "division_size" in upd and _int_in(upd["division_size"], TB_DIV_SIZE_MIN, TB_DIV_SIZE_MAX) is None:
        return False, "bad_division_size"
    updated, failed = 0, []
    for lg in tb_leagues_list(None):
        ok, res = tb_league_update(lg["id"], upd)
        if ok:
            updated += 1
        else:
            failed.append({"league_id": lg["id"], "name": lg["name"], "reason": res})
    logger.info("TB: barcha ligalarga sozlama %s — %s ta yangilandi, %s ta xato", upd, updated, len(failed))
    return True, {"updated": updated, "failed": failed}
