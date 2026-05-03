# -*- coding: utf-8 -*-
from __future__ import annotations
"""
living_costs.py — Chi phí sinh hoạt hàng ngày.

Thu một lần/ngày khi mở Anki (giống cơ chế thuế trong tax_system.py).
Chi phí gồm:
  - Điện + nước: base cố định + biến đổi theo số thẻ ôn ngày hôm trước
  - Ăn uống cơ bản: theo nơi ở (tính theo ngày)
  - Internet: theo nơi ở (tính theo ngày)
  - Tiền thuê (nếu đang thuê): tính hàng tháng, chia nhỏ theo ngày
"""

import time
from ._safe_config import col_ready, cfg_str, cfg_list, cfg_set, begin_batch, commit_batch

_KEY_LAST_DATE = "anki_tycoon_last_living_cost_date"
_KEY_LOG       = "anki_tycoon_living_cost_log"
MAX_LOG        = 30


def _today() -> str:
    """Trả về 'YYYY-MM-DD' dùng Unix timestamp, chống time travel."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time()))


def _get_cards_reviewed_yesterday() -> int:
    """Lấy số thẻ ôn ngày hôm qua từ streak_system / stats."""
    try:
        from aqt import mw
        if not mw or not mw.col:
            return 0
        from datetime import datetime, timedelta, time as dtime
        yesterday = (datetime.now() - timedelta(days=1)).date()
        # Dùng Anki collection stats nếu có
        try:
            start_ts = int(datetime.combine(yesterday, dtime.min).timestamp() * 1000)
            end_ts = int(datetime.combine(yesterday + timedelta(days=1), dtime.min).timestamp() * 1000)
            stats = mw.col.db.scalar(
                "SELECT count() FROM revlog WHERE id >= ? AND id < ?",
                start_ts,
                end_ts,
            )
            return int(stats) if stats else 0
        except Exception:
            pass
        # Fallback: streak_system có stats ngày hiện tại
        from .streak_system import get_streak_status
        s = get_streak_status()
        return int(s.get("cards_today", 0))
    except Exception:
        return 0


def calculate_daily_costs(cards_yesterday: int | None = None) -> dict:
    """
    Tính chi phí sinh hoạt hôm nay.
    Trả về breakdown chi tiết.
    """
    from .housing_residence import get_residence, get_monthly_fixed_costs, get_utilities_daily
    res    = get_residence()
    fixed  = get_monthly_fixed_costs(res)

    if cards_yesterday is None:
        cards_yesterday = _get_cards_reviewed_yesterday()

    # Chia nhỏ chi phí tháng → ngày
    daily_rent     = round(fixed["rent"] / 30)
    daily_food     = round(fixed["food"] / 30)
    daily_internet = round(fixed["internet"] / 30)
    daily_utils    = get_utilities_daily(cards_yesterday, res)

    total = daily_rent + daily_food + daily_internet + daily_utils

    # Điện nhân bao nhiêu?
    base_daily_utils = round(res.get("utilities_base", 200_000) / 30.0)
    if cards_yesterday == 0:
        util_mult_label = "×2.0 (không học)"
    elif cards_yesterday <= 20:
        util_mult_label = "×1.5 (học ít)"
    elif cards_yesterday <= 50:
        util_mult_label = "×1.2 (học trung bình)"
    elif cards_yesterday <= 100:
        util_mult_label = "×1.0 (bình thường)"
    else:
        util_mult_label = "×0.7 (học chăm, tiết kiệm)"

    return {
        "residence_name":    res["name"],
        "residence_emoji":   res["emoji"],
        "cards_yesterday":   cards_yesterday,
        "daily_rent":        daily_rent,
        "daily_food":        daily_food,
        "daily_internet":    daily_internet,
        "daily_utilities":   daily_utils,
        "util_base_daily":   base_daily_utils,
        "util_mult_label":   util_mult_label,
        "total":             total,
    }


def collect_daily_living_costs() -> dict:
    """
    Thu chi phí sinh hoạt nếu hôm nay chưa thu.
    Gọi từ __init__.py khi mở Anki.
    Atomic batch: đảm bảo balance, transaction, last_date được ghi đồng bộ.
    """
    if not col_ready():
        return {"collected": False, "reason": "not_ready"}

    if cfg_str(_KEY_LAST_DATE, "") == _today():
        return {"collected": False, "reason": "already_collected"}

    cards_yesterday = _get_cards_reviewed_yesterday()
    breakdown = calculate_daily_costs(cards_yesterday)
    total = breakdown["total"]

    if total <= 0:
        cfg_set(_KEY_LAST_DATE, _today())
        return {"collected": False, "reason": "no_cost"}

    from .balance import get_balance, set_balance
    from .transactions import add_transaction
    from .loan_system import ensure_loan_if_needed

    try:
        # Atomic batch: balance + transaction + last_date
        begin_batch()

        bal = get_balance()
        new_bal = bal - total

        set_balance(new_bal)
        add_transaction(
            "living_cost", total,
            f"Chi phí sinh hoạt ({breakdown['residence_name']}) — "
            f"điện/nước {breakdown['util_mult_label']}, {cards_yesterday} thẻ hôm qua"
        )

        cfg_set(_KEY_LAST_DATE, _today())

        commit_batch()

        # Kiểm tra nếu âm → tự động vay
        loan_result = ensure_loan_if_needed()

        log_entry = {
            "date":            _today(),
            "cards_yesterday": cards_yesterday,
            "breakdown":       breakdown,
            "total":           total,
            "balance_after":   get_balance(),
            "loan":            loan_result.get("borrowed", 0),
        }
        _append_log(log_entry)

        # Force refresh topbar để UI hiển thị balance mới
        try:
            from ._safe_config import _cache_invalidate
            _cache_invalidate("anki_tycoon_balance")
            from aqt import mw
            if hasattr(mw, "tycoon_topbar") and mw.tycoon_topbar:
                mw.tycoon_topbar.refresh()
        except Exception:
            pass

        return {
            "collected": True,
            "total":     total,
            "breakdown": breakdown,
            "loan":      loan_result,
        }
    except Exception:
        # Nếu có lỗi, huỷ batch để tránh ghi dở dang
        try:
            from ._safe_config import discard_batch
            discard_batch()
        except Exception:
            pass
        return {"collected": False, "reason": "error"}


def get_living_cost_log() -> list:
    return cfg_list(_KEY_LOG, [])


def get_living_cost_status() -> dict:
    """Trạng thái chi phí sinh hoạt cho UI — kết nối với tài chính & ngân sách."""
    if not col_ready():
        return {}
    from .housing_residence import get_residence, get_monthly_fixed_costs, get_monthly_land_tax, get_utilities_daily
    res         = get_residence()
    fixed       = get_monthly_fixed_costs(res)
    land_tax    = get_monthly_land_tax(res)
    cards_today = _get_cards_reviewed_yesterday()  # hôm nay (dùng làm ước tính)

    util_today  = get_utilities_daily(cards_today, res) * 30  # estimate tháng

    # Lấy thông tin chi phí sinh hoạt thực tế từ finance (month-to-date)
    try:
        from .transactions import get_transactions_by_type
        living_txns = get_transactions_by_type("living_cost")
        living_cost_mtd = sum(int(t.get("amount", 0)) for t in living_txns)
        living_cost_count = len(living_txns)
    except Exception:
        living_cost_mtd = 0
        living_cost_count = 0

    # Lấy thông tin ngân sách
    try:
        from .finance import get_monthly_spending, get_budget, get_budget_status
        budget_status = get_budget_status()
    except Exception:
        budget_status = {}

    return {
        "residence":          res,
        "monthly_rent":       fixed["rent"],
        "monthly_food":       fixed["food"],
        "monthly_internet":   fixed["internet"],
        "monthly_utilities_est": util_today,
        "monthly_land_tax":   land_tax,
        "monthly_total_est":  (
            fixed["rent"] + fixed["food"] + fixed["internet"]
            + util_today + land_tax
        ),
        "last_collected":     cfg_str(_KEY_LAST_DATE, ""),
        "collected_today":    cfg_str(_KEY_LAST_DATE, "") == _today(),
        "log":                get_living_cost_log()[-7:],  # 7 ngày gần nhất
        "living_cost_mtd":    living_cost_mtd,          # Chi phí thực tế đã thu trong tháng
        "living_cost_count":  living_cost_count,        # Số lần đã thu trong tháng
        "budget_status":      budget_status,            # Trạng thái ngân sách
    }


def _append_log(entry: dict):
    log = cfg_list(_KEY_LOG, [])
    log.insert(0, entry)
    if len(log) > MAX_LOG:
        log = log[:MAX_LOG]
    cfg_set(_KEY_LOG, log)
