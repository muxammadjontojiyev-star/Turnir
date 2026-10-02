"""
el_playin.py — YeL play-off kirish qur'asi (cl_playin naqshi, ALOHIDA nusxa).

Yagona reyting (36 klub) 8 tur tugagach:
  - TOP-8 -> to'g'ridan asosiy setkaga (seed 1..8).
  - 9-24 o'rin -> PLEY-IN juftlari (9,24), (10,23), ..., (16,17) — uy+mehmon.
  - Setka: r16 pos p da sideA = seed[p], sideB = pley-in g'olibi[7-p]
    (seed-1 eng zaif pley-in juftligi g'olibi bilan tushadi).
Faqat SOF hisoblash — DB yozmaydi (qoida #25/#27).
"""

EL_SEED_COUNT = 8          # to'g'ridan setkaga o'tadiganlar
EL_QUALIFY_TOTAL = 24      # play-offga jalb qilinadigan o'rinlar (1..24)
# (yuqori_orin, quyi_orin), kuch tartibida — konstantalardan hisoblanadi (qoida #17)
EL_PLAYIN_PAIRS = [(EL_SEED_COUNT + 1 + i, EL_QUALIFY_TOTAL - i)
                   for i in range((EL_QUALIFY_TOTAL - EL_SEED_COUNT) // 2)]


def build_playin_draw(ranking_user_ids: list[int]) -> dict:
    """
    ranking_user_ids: reyting tartibidagi user_id lar (0-index = 1-o'rin).
    Qaytaradi: {"seeds": [top-8], "playin": [(hi_id, lo_id), ...] kuch tartibida}
    """
    seeds = ranking_user_ids[:EL_SEED_COUNT]
    playin = [(ranking_user_ids[hi - 1], ranking_user_ids[lo - 1])
              for hi, lo in EL_PLAYIN_PAIRS
              if lo - 1 < len(ranking_user_ids)]
    return {"seeds": seeds, "playin": playin}


def r16_slot_for_playin_position(playin_pos: int) -> int:
    """Pley-in juftligi (0..7) g'olibi qaysi r16 pozitsiyasiga boradi: 7 - pos."""
    return EL_SEED_COUNT - 1 - playin_pos
