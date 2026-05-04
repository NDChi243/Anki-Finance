# -*- coding: utf-8 -*-
from __future__ import annotations
from .logger import get_logger
logger = get_logger(__name__)
"""
streak_system.py — Streak học tập hàng ngày.

- Streak tăng mỗi ngày có ít nhất MIN_CARDS_FOR_STREAK thẻ ôn
- Streak mất nếu bỏ ngày
- Multiplier: streak 3→×1.2, 7→×1.5, 14→×1.8, 30→×2.0, 60→×2.5, 100→×3.0
- Bonus XP khi đạt milestone streak
"""

import time
from datetime import timedelta
from ._safe_config import col_ready, cfg_int, cfg_str, cfg_set

_KEY_STREAK       = "anki_tycoon_streak"
_KEY_STREAK_DATE  = "anki_tycoon_streak_date"   # ngày ôn gần nhất
_KEY_BEST_STREAK  = "anki_tycoon_best_streak"
_KEY_TODAY_CARDS  = "anki_tycoon_streak_today_cards"
_KEY_TODAY_DATE   = "anki_tycoon_streak_today_date"

MIN_CARDS_FOR_STREAK = 5   # tối thiểu 5 thẻ/ngày mới tính streak

STREAK_MULTIPLIERS = [
    (100, 3.0),
    (60,  2.5),
    (30,  2.0),
    (14,  1.8),
    (7,   1.5),
    (3,   1.2),
    (1,   1.1),
    (0,   1.0),
]

STREAK_MILESTONES = {3, 7, 14, 30, 60, 100, 200, 365}


def _today() -> str:
    """Trả về 'YYYY-MM-DD' dùng Unix timestamp, chống time travel."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time()))

def _yesterday() -> str:
    """Trả về 'YYYY-MM-DD' của hôm qua dùng Unix timestamp."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))


def get_streak() -> int:
    if not col_ready(): return 0
    return cfg_int(_KEY_STREAK, 0)

def get_best_streak() -> int:
    return cfg_int(_KEY_BEST_STREAK, 0)

def get_multiplier(streak: int | None = None) -> float:
    if streak is None:
        streak = get_streak()
    for threshold, mult in STREAK_MULTIPLIERS:
        if streak >= threshold:
            return mult
    return 1.0


def record_card_reviewed() -> dict:
    """
    Gọi sau mỗi thẻ ôn. Tự động cập nhật streak khi đủ MIN_CARDS.
    Trả về dict với streak_updated, milestone_hit, multiplier.
    """
    if not col_ready():
        return {"streak": 0, "streak_updated": False, "milestone_hit": False, "multiplier": 1.0}

    today = _today()

    # Reset today_cards nếu sang ngày mới
    if cfg_str(_KEY_TODAY_DATE, "") != today:
        cfg_set(_KEY_TODAY_CARDS, 0)
        cfg_set(_KEY_TODAY_DATE, today)

    today_cards = cfg_int(_KEY_TODAY_CARDS, 0) + 1
    cfg_set(_KEY_TODAY_CARDS, today_cards)

    result = {
        "streak":          get_streak(),
        "streak_updated":  False,
        "milestone_hit":   False,
        "milestone_val":   0,
        "multiplier":      get_multiplier(),
        "today_cards":     today_cards,
        "cards_needed":    max(0, MIN_CARDS_FOR_STREAK - today_cards),
    }

    # Chưa đủ MIN_CARDS → chưa tính streak hôm nay
    if today_cards < MIN_CARDS_FOR_STREAK:
        return result

    # Đã đủ cards — kiểm tra có cần cập nhật streak không
    last_date = cfg_str(_KEY_STREAK_DATE, "")

    if last_date == today:
        # Đã cập nhật hôm nay rồi
        result["streak"] = get_streak()
        result["multiplier"] = get_multiplier()
        return result

    streak = cfg_int(_KEY_STREAK, 0)

    if last_date == _yesterday():
        # Ngày liên tiếp → tăng streak
        streak += 1
    else:
        # Bỏ ngày → reset
        streak = 1

    cfg_set(_KEY_STREAK, streak)
    cfg_set(_KEY_STREAK_DATE, today)

    # Cập nhật best streak
    best = cfg_int(_KEY_BEST_STREAK, 0)
    if streak > best:
        cfg_set(_KEY_BEST_STREAK, streak)

    milestone_hit = streak in STREAK_MILESTONES
    result.update(
        streak=streak,
        streak_updated=True,
        milestone_hit=milestone_hit,
        milestone_val=streak if milestone_hit else 0,
        multiplier=get_multiplier(streak),
    )

    # Achievement trigger
    try:
        from .achievements import check_and_unlock
        check_and_unlock("streak_updated", streak)
    except Exception as e:
        logger.debug("update_streak: achievements trigger — %s", e)

    return result


def check_streak_broken() -> bool:
    """
    Kiểm tra streak có bị mất hôm nay không.
    (Gọi khi mở Anki — nếu last_date < hôm qua thì streak đã mất)
    """
    if not col_ready(): return False
    last = cfg_str(_KEY_STREAK_DATE, "")
    if not last: return False
    streak = cfg_int(_KEY_STREAK, 0)
    if streak > 0 and last < _yesterday():
        cfg_set(_KEY_STREAK, 0)
        return True
    return False


def get_streak_status() -> dict:
    if not col_ready():
        return {"streak":0,"best":0,"multiplier":1.0,"today_cards":0,
                "cards_needed":MIN_CARDS_FOR_STREAK,"min_cards":MIN_CARDS_FOR_STREAK}
    check_streak_broken()
    streak = get_streak()
    today  = _today()
    today_cards = cfg_int(_KEY_TODAY_CARDS, 0) if cfg_str(_KEY_TODAY_DATE,"") == today else 0
    return {
        "streak":       streak,
        "best":         get_best_streak(),
        "multiplier":   get_multiplier(streak),
        "today_cards":  today_cards,
        "cards_needed": max(0, MIN_CARDS_FOR_STREAK - today_cards),
        "min_cards":    MIN_CARDS_FOR_STREAK,
        "streak_active": cfg_str(_KEY_STREAK_DATE, "") >= _yesterday(),
    }