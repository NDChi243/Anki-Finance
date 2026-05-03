# -*- coding: utf-8 -*-
import time
from ._safe_config import col_ready, cfg_int, cfg_str, cfg_set

_KEY_COUNT         = "anki_tycoon_daily_again_count"
_KEY_DATE          = "anki_tycoon_daily_again_date"
_KEY_TOTAL_PENALTY = "anki_tycoon_daily_again_penalty"

WARN_THRESHOLD = 50
PENALTY_START  = 55
PENALTY_HEAVY  = 60
BASE_PENALTY   = 3000


def _today() -> str:
    """Trả về 'YYYY-MM-DD' dùng Unix timestamp, chống time travel."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time()))


def _reset_if_new_day():
    if not col_ready():
        return
    if cfg_str(_KEY_DATE, "") != _today():
        cfg_set(_KEY_COUNT, 0)
        cfg_set(_KEY_TOTAL_PENALTY, 0)
        cfg_set(_KEY_DATE, _today())


def get_daily_again_count() -> int:
    if not col_ready():
        return 0
    _reset_if_new_day()
    return cfg_int(_KEY_COUNT, 0)


def get_daily_penalty_total() -> int:
    return cfg_int(_KEY_TOTAL_PENALTY, 0)


def record_again() -> dict:
    if not col_ready():
        return {"count": 0, "rewarded": True, "penalized": False,
                "penalty": 0, "warn": False, "message": "+500 VND"}

    _reset_if_new_day()
    count = cfg_int(_KEY_COUNT, 0) + 1
    cfg_set(_KEY_COUNT, count)

    result = {"count": count, "rewarded": False, "penalized": False,
              "penalty": 0, "warn": False, "message": ""}

    if count < WARN_THRESHOLD:
        result["rewarded"] = True
        result["message"]  = "+500 VND"

    elif count < PENALTY_START:
        result["rewarded"] = True
        result["warn"]     = True
        result["message"]  = f"⚠️ Again lần {count} — còn {PENALTY_START - count} lần nữa bị phạt!"

    else:
        from .balance import get_balance, set_balance
        from .transactions import add_transaction

        balance    = get_balance()
        multiplier = 2 if count >= PENALTY_HEAVY else 1
        penalty    = round((BASE_PENALTY + balance * 0.10 / 5) * multiplier) \
                     if balance >= 1_000_000 else BASE_PENALTY * multiplier

        set_balance(balance - penalty)
        cfg_set(_KEY_TOTAL_PENALTY, cfg_int(_KEY_TOTAL_PENALTY, 0) + penalty)
        add_transaction("penalty", penalty, f"Phạt Again lần {count}/ngày")

        new_bal = balance - penalty
        debt  = f" [NỢ {abs(new_bal):,}đ]".replace(",", ".") if new_bal < 0 else ""
        heavy = " 🔴×2" if count >= PENALTY_HEAVY else ""
        result.update(penalized=True, penalty=penalty,
                      message=f"🚨 Phạt {penalty:,}đ{heavy}{debt}".replace(",", "."))

    return result


def get_today_summary() -> dict:
    if not col_ready():
        return {"count": 0, "penalty_total": 0, "status": "normal",
                "warn_at": WARN_THRESHOLD, "penalty_at": PENALTY_START, "heavy_at": PENALTY_HEAVY}
    _reset_if_new_day()
    count   = cfg_int(_KEY_COUNT, 0)
    penalty = cfg_int(_KEY_TOTAL_PENALTY, 0)
    status  = ("heavy" if count >= PENALTY_HEAVY else
               "penalty" if count >= PENALTY_START else
               "warn" if count >= WARN_THRESHOLD else "normal")
    return {"count": count, "penalty_total": penalty, "status": status,
            "warn_at": WARN_THRESHOLD, "penalty_at": PENALTY_START, "heavy_at": PENALTY_HEAVY}
