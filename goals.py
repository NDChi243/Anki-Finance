# -*- coding: utf-8 -*-
"""
goals.py — Hệ thống mục tiêu cá nhân Anki Tycoon.

Cho phép đặt mục tiêu mua 1 món đồ cụ thể và theo dõi
progress bar tiến tới mục tiêu đó.
"""

from ._safe_config import col_ready, cfg_dict, cfg_set

_KEY_GOAL = "anki_tycoon_goal"


def _default() -> dict:
    return {
        "item_id":    "",
        "item_name":  "",
        "item_price": 0,
        "item_emoji": "",
        "set_at":     "",
    }


def get_goal() -> dict:
    """Trả về mục tiêu hiện tại (hoặc dict rỗng nếu chưa đặt)."""
    g = cfg_dict(_KEY_GOAL, _default())
    for k, v in _default().items():
        if k not in g or g[k] is None:
            g[k] = v
    return g


def set_goal(item_id: str, item_name: str, item_price: int,
             item_emoji: str = "") -> dict:
    """Đặt mục tiêu mới. Ghi đè mục tiêu cũ."""
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}
    from datetime import datetime
    goal = {
        "item_id":    item_id,
        "item_name":  item_name,
        "item_price": int(item_price),
        "item_emoji": item_emoji,
        "set_at":     datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    cfg_set(_KEY_GOAL, goal)
    return {"ok": True, "goal": goal}


def clear_goal() -> dict:
    """Xoá mục tiêu hiện tại."""
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}
    cfg_set(_KEY_GOAL, _default())
    return {"ok": True}


def get_goal_progress(current_balance: int) -> dict:
    """
    Tính % tiến độ tiến tới mục tiêu.
    Trả về dict đầy đủ để UI render progress bar.
    """
    goal = get_goal()
    if not goal.get("item_id") or goal.get("item_price", 0) <= 0:
        return {
            "has_goal": False,
            "percent":  0,
            "remaining": 0,
            "reached":  False,
        }

    price     = int(goal["item_price"])
    balance   = max(0, int(current_balance))
    percent   = min(100, round(balance / price * 100, 1)) if price > 0 else 0
    remaining = max(0, price - balance)

    return {
        "has_goal":   True,
        "item_id":    goal["item_id"],
        "item_name":  goal["item_name"],
        "item_price": price,
        "item_emoji": goal.get("item_emoji", "🎯"),
        "set_at":     goal.get("set_at", ""),
        "balance":    balance,
        "percent":    percent,
        "remaining":  remaining,
        "reached":    balance >= price,
    }