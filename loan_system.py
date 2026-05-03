# -*- coding: utf-8 -*-
"""
loan_system.py — Vay nóng tự động khi hết tiền.

Khi balance < 0 sau khi trừ chi phí sinh hoạt:
  - Tự động vay 5.000.000đ
  - Lãi suất 25%/tháng ≈ 0.833%/ngày
  - Lãi cộng dồn mỗi ngày mở Anki
  - Thu nhập từ thẻ dùng để trả nợ trước (xử lý trong add_reward)
"""

import time
from ._safe_config import col_ready, cfg_dict, cfg_list, cfg_set

_KEY_LOAN      = "anki_tycoon_loan_balance"   # {"principal": int, "interest_accrued": int, "since": str}
_KEY_LOAN_LOG  = "anki_tycoon_loan_log"

AUTO_LOAN_AMOUNT = 5_000_000    # 5 triệu mỗi lần vay
DAILY_RATE       = 0.00833      # 25%/tháng ÷ 30 ≈ 0.833%/ngày


def _today() -> str:
    """Trả về 'YYYY-MM-DD' dùng Unix timestamp, chống time travel."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time()))


def get_loan_info() -> dict:
    """Trả về thông tin khoản nợ hiện tại."""
    raw = cfg_dict(_KEY_LOAN, {})
    return {
        "has_loan":          bool(raw.get("total", 0)),
        "total":             int(raw.get("total", 0)),
        "principal":         int(raw.get("principal", 0)),
        "interest_accrued":  int(raw.get("interest_accrued", 0)),
        "since":             raw.get("since", ""),
        "last_interest_date": raw.get("last_interest_date", ""),
        "daily_rate_pct":    DAILY_RATE * 100,
        "monthly_rate_pct":  25.0,
    }


def _save_loan(info: dict):
    cfg_set(_KEY_LOAN, info)


def ensure_loan_if_needed() -> dict:
    """
    Nếu balance < 0 → vay tự động.
    Gọi sau khi trừ chi phí sinh hoạt.
    """
    if not col_ready():
        return {"borrowed": 0}

    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    bal = get_balance()
    if bal >= 0:
        return {"borrowed": 0}

    # Balance âm → cần vay đủ để dương
    needed  = -bal
    times   = (needed // AUTO_LOAN_AMOUNT) + 1
    amount  = times * AUTO_LOAN_AMOUNT

    loan = get_loan_info()
    new_principal = loan["principal"] + amount
    new_total     = loan["total"]     + amount

    _save_loan({
        "principal":          new_principal,
        "interest_accrued":   loan["interest_accrued"],
        "total":              new_total,
        "since":              loan.get("since") or _today(),
        "last_interest_date": loan.get("last_interest_date") or _today(),
    })

    set_balance(bal + amount)
    add_transaction("loan", amount, f"Vay nóng tự động — lãi 25%/tháng")
    _append_log({"date": _today(), "event": "borrow", "amount": amount})

    return {"borrowed": amount, "new_total": new_total}


def accrue_daily_interest() -> dict:
    """
    Cộng lãi hàng ngày vào khoản nợ.
    Gọi từ __init__.py khi mở Anki.
    """
    if not col_ready():
        return {"accrued": 0}

    loan = get_loan_info()
    if not loan["has_loan"]:
        return {"accrued": 0}

    # Chỉ tính lãi 1 lần/ngày
    last = loan.get("last_interest_date", "")
    if last == _today():
        return {"accrued": 0}

    interest = round(loan["total"] * DAILY_RATE)
    new_total = loan["total"] + interest

    _save_loan({
        "principal":          loan["principal"],
        "interest_accrued":   loan["interest_accrued"] + interest,
        "total":              new_total,
        "since":              loan["since"],
        "last_interest_date": _today(),
    })

    from .transactions import add_transaction
    add_transaction("loan_interest", interest,
                    f"Lãi vay nóng 0.833%/ngày (tổng nợ: {new_total:,}đ)".replace(",","."))
    _append_log({"date": _today(), "event": "interest", "amount": interest, "total": new_total})

    return {"accrued": interest, "new_total": new_total}


def repay_from_reward(reward_amount: int) -> dict:
    """
    Dùng tiền thưởng thẻ để trả nợ trước.
    Trả về {"used_for_repay": int, "remaining": int, "loan_cleared": bool}
    """
    if not col_ready():
        return {"used_for_repay": 0, "remaining": reward_amount, "loan_cleared": False}

    loan = get_loan_info()
    if not loan["has_loan"]:
        return {"used_for_repay": 0, "remaining": reward_amount, "loan_cleared": False}

    repay = min(reward_amount, loan["total"])
    new_total = loan["total"] - repay
    cleared = new_total <= 0

    if cleared:
        _save_loan({})  # Xóa khoản nợ
    else:
        _save_loan({
            "principal":          max(0, loan["principal"] - repay),
            "interest_accrued":   loan["interest_accrued"],
            "total":              new_total,
            "since":              loan["since"],
            "last_interest_date": loan["last_interest_date"],
        })

    if repay > 0:
        from .transactions import add_transaction
        add_transaction("loan_repay", repay,
                        f"Trả nợ vay nóng (còn: {new_total:,}đ)".replace(",","."))
        _append_log({"date": _today(), "event": "repay", "amount": repay, "remaining": new_total})

    return {
        "used_for_repay": repay,
        "remaining":      reward_amount - repay,
        "loan_cleared":   cleared,
        "loan_remaining": new_total,
    }


def get_loan_log() -> list:
    return cfg_list(_KEY_LOAN_LOG, [])


def _append_log(entry: dict):
    log = cfg_list(_KEY_LOAN_LOG, [])
    log.insert(0, entry)
    if len(log) > 60:
        log = log[:60]
    cfg_set(_KEY_LOAN_LOG, log)
