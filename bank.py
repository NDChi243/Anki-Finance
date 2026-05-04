# -*- coding: utf-8 -*-
from __future__ import annotations
"""
bank.py — Hệ thống ngân hàng Anki Tycoon với lãi kép và kỳ hạn.
"""

import time
import uuid
from datetime import datetime
from ._safe_config import col_ready, cfg_dict, cfg_list, cfg_set
from .logger import get_logger
logger = get_logger(__name__)

_KEY_DEMAND   = "anki_tycoon_demand_savings"
_KEY_DEPOSITS = "anki_tycoon_term_deposits"
_KEY_SEND_MORE_LOG = "anki_tycoon_term_send_more_log"
_KEY_INSTANT_INTEREST = "anki_tycoon_instant_interest"  # {last_claim_ts: float}
_SEND_MORE_WEEKLY_LIMIT = 3

DEMAND_PRODUCT = {
    "code": "demand",
    "label": "Tiền gửi không kỳ hạn",
    "rate": 0.003,
    "note": "Rút tiền linh hoạt bất cứ lúc nào",
    "reference": "Tham khảo nhóm tiết kiệm KKH tại ACB và MB Bank",
}

TERM_PRODUCTS = {
    "accumulative": {
        "label": "Tiền gửi tích lũy",
        "note": "Mô phỏng dòng gửi góp linh hoạt, cho phép nộp thêm trong quá trình gửi.",
        "reference": "Tham khảo ACB Tích Lũy Tương Lai và KBank Tiết Kiệm Tích Lũy",
        "min_amount": 1_000_000,
        "compound": True,
        "allow_topup": True,
        "interest_mode": "maturity",
        "terms": {
            12: 0.048,
            24: 0.050,
            36: 0.052,
            60: 0.054,
        },
    },
    "periodic": {
        "label": "Tiền gửi trả lãi sau định kỳ",
        "note": "Mô phỏng sổ lĩnh lãi định kỳ theo tháng hoặc quý, gốc nhận khi đáo hạn.",
        "reference": "Tham khảo nhóm sản phẩm lĩnh lãi định kỳ tại ACB và Agribank",
        "min_amount": 1_000_000,
        "compound": False,
        "allow_topup": False,
        "interest_mode": "periodic",
        "terms": {
            1: 0.040,
            3: 0.043,
            6: 0.047,
            12: 0.050,
        },
    },
    "upfront": {
        "label": "Tiền gửi trả lãi trước toàn bộ",
        "note": "Nhận lãi ngay tại lúc mở sổ, đến đáo hạn nhận lại phần gốc.",
        "reference": "Tham khảo tiền gửi trả lãi trước tại Agribank Plus và ACB",
        "min_amount": 1_000_000,
        "compound": False,
        "allow_topup": False,
        "interest_mode": "upfront",
        "terms": {
            1: 0.037,
            3: 0.041,
            6: 0.045,
            12: 0.048,
        },
    },
    "tiered": {
        "label": "Tiền gửi tiết kiệm bậc thang",
        "note": "Lãi suất tăng dần theo số tiền gửi cùng một kỳ hạn.",
        "reference": "Tham khảo nhóm tiền gửi bậc thang tại ACB",
        "min_amount": 5_000_000,
        "compound": False,
        "allow_topup": False,
        "interest_mode": "maturity",
        "terms": {
            1: 0.041,
            3: 0.045,
            6: 0.049,
            12: 0.053,
        },
        "tiers": [
            {"min_amount": 100_000_000, "bonus_rate": 0.0035, "label": "Từ 100 triệu"},
            {"min_amount": 20_000_000,  "bonus_rate": 0.0015, "label": "Từ 20 triệu"},
            {"min_amount": 5_000_000,   "bonus_rate": 0.0,    "label": "Từ 5 triệu"},
        ],
    },
}

LEGACY_TERM_PLANS = {
    1:  {"label": "1 tháng",  "months": 1,  "rate": 0.04,  "compound": True},
    3:  {"label": "3 tháng",  "months": 3,  "rate": 0.055, "compound": True},
    6:  {"label": "6 tháng",  "months": 6,  "rate": 0.068, "compound": True},
    12: {"label": "12 tháng", "months": 12, "rate": 0.082, "compound": True},
}
_SECS_PER_YEAR = 365 * 24 * 3600


def _get_term_product(product_code: str | None) -> dict | None:
    return TERM_PRODUCTS.get((product_code or "").strip())


def _get_product_rate(product_code: str, term_months: int, amount: int) -> float:
    product = _get_term_product(product_code)
    if not product:
        plan = LEGACY_TERM_PLANS.get(term_months, LEGACY_TERM_PLANS[1])
        return float(plan["rate"])

    base_rate = float(product["terms"].get(term_months, 0.0))
    if base_rate <= 0:
        return 0.0

    bonus_rate = 0.0
    for tier in product.get("tiers", []) or []:
        if amount >= int(tier.get("min_amount", 0) or 0):
            bonus_rate = float(tier.get("bonus_rate", 0.0) or 0.0)
            break
    rate = base_rate + bonus_rate

    # interest_bonus là phần trăm cộng thêm lên lãi suất gốc.
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        interest_bonus = float(passive.get("interest_bonus", 0.0))
        # Cộng dồn interest_bonus từ KN Perks
        try:
            from .kn_perks import get_active_bonuses
            kn_bonuses = get_active_bonuses()
            interest_bonus += float(kn_bonuses.get("interest_bonus", 0.0))
        except Exception as e:
            logger.debug("_get_product_rate: kn_perks interest_bonus — %s", e)
        if interest_bonus > 0:
            rate = rate * (1.0 + interest_bonus)
    except Exception as e:
        logger.debug("_get_product_rate: passive effects interest_bonus — %s", e)

    return rate


def _calc_simple_interest(principal: int, rate: float, years: float) -> float:
    return principal * rate * years


def _calc_growth_value(principal: int, rate: float, years: float, compound: bool) -> float:
    if principal <= 0 or years <= 0 or rate <= 0:
        return float(principal)
    if compound:
        return principal * ((1 + rate / 12) ** (12 * years))
    return principal + _calc_simple_interest(principal, rate, years)


def _format_payout_cycle(interval_months: int) -> str:
    return "hàng tháng" if interval_months <= 1 else f"mỗi {interval_months} tháng"


def _get_periodic_interval_months(term_months: int) -> int:
    return 1 if term_months <= 3 else 3


def _sync_periodic_interest_for_deposit(dep: dict, at_time: float) -> int:
    if dep.get("interest_mode") != "periodic":
        return 0

    principal = int(dep.get("amount", 0) or 0)
    rate = float(dep.get("rate", 0.0) or 0.0)
    term_months = int(dep.get("term_months", 0) or 0)
    if principal <= 0 or rate <= 0 or term_months <= 0:
        return 0

    interval_months = int(dep.get("payout_interval_months", 1) or 1)
    interval_secs = interval_months * 30.44 * 24 * 3600
    if interval_secs <= 0:
        return 0

    total_periods = max(1, term_months // interval_months)
    paid_periods = int(dep.get("paid_periods", 0) or 0)
    elapsed_periods = min(total_periods, int(max(0.0, at_time - float(dep.get("start_ts", at_time) or at_time)) // interval_secs))
    periods_due = max(0, elapsed_periods - paid_periods)
    if periods_due <= 0:
        return 0

    interest_per_period = _calc_simple_interest(principal, rate, interval_months / 12)
    payout = int(round(interest_per_period * periods_due))
    dep["paid_periods"] = paid_periods + periods_due
    dep["interest_paid_total"] = int(dep.get("interest_paid_total", 0) or 0) + payout
    dep["last_payout_ts"] = float(dep.get("start_ts", at_time) or at_time) + dep["paid_periods"] * interval_secs
    return payout


def _sync_periodic_payouts() -> int:
    deps = _get_deposits()
    now = time.time()
    payouts = []

    for dep in deps:
        payout = _sync_periodic_interest_for_deposit(dep, now)
        if payout > 0:
            payouts.append((dep, payout))

    if not payouts:
        return 0

    _save_deposits(deps)

    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    total_payout = sum(payout for _, payout in payouts)
    set_balance(get_balance() + total_payout)
    for dep, payout in payouts:
        add_transaction("interest", payout, f"Lãi định kỳ sổ {dep.get('label', '?')} #{dep.get('id', '?')}")
    return total_payout


# ── Demand ──────────────────────────────────────────────────────

def _get_demand() -> dict:
    default = {"amount": 0, "ts": time.time()}
    d = cfg_dict(_KEY_DEMAND, default)
    # Đảm bảo keys tồn tại
    if "amount" not in d or d["amount"] is None:
        d["amount"] = 0
    if "ts" not in d or d["ts"] is None:
        d["ts"] = time.time()
    return d


def _save_demand(d: dict):
    cfg_set(_KEY_DEMAND, d)


def get_demand_balance() -> int:
    return int(_get_demand().get("amount", 0) or 0)


def calc_demand_interest() -> float:
    d = _get_demand()
    amount = int(d.get("amount", 0) or 0)
    if amount <= 0:
        return 0.0
    ts = float(d.get("ts", time.time()) or time.time())
    elapsed_years = (time.time() - ts) / _SECS_PER_YEAR
    # interest_bonus là phần trăm cộng thêm lên lãi suất không kỳ hạn.
    rate = DEMAND_PRODUCT["rate"]
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        interest_bonus = float(passive.get("interest_bonus", 0.0))
        # Cộng dồn interest_bonus từ KN Perks
        try:
            from .kn_perks import get_active_bonuses
            kn_bonuses = get_active_bonuses()
            interest_bonus += float(kn_bonuses.get("interest_bonus", 0.0))
        except Exception as e:
            logger.debug("calc_demand_interest: kn_perks interest_bonus — %s", e)
        if interest_bonus > 0:
            rate = rate * (1.0 + interest_bonus)
    except Exception as e:
        logger.debug("calc_demand_interest: passive effects interest_bonus — %s", e)
    return amount * rate * elapsed_years


def deposit_demand(amount: int) -> dict:
    from .balance import get_balance, set_balance
    from .transactions import add_transaction
    if amount <= 0:
        return {"ok": False, "error": "Số tiền không hợp lệ."}
    bal = get_balance()
    if bal < amount:
        return {"ok": False, "error": "Số dư ví không đủ."}

    _flush_demand_interest()
    set_balance(bal - amount)
    d = _get_demand()
    d["amount"] = int(d.get("amount", 0) or 0) + amount
    _save_demand(d)
    add_transaction("bank_deposit", amount, "Gửi không kỳ hạn")
    return {"ok": True}


def withdraw_demand(amount: int) -> dict:
    from .balance import get_balance, set_balance
    from .transactions import add_transaction
    if amount <= 0:
        return {"ok": False, "error": "Số tiền không hợp lệ."}

    _flush_demand_interest()
    d = _get_demand()
    cur = int(d.get("amount", 0) or 0)
    if cur < amount:
        return {"ok": False, "error": "Số dư không kỳ hạn không đủ."}

    d["amount"] = cur - amount
    d["ts"] = time.time()
    _save_demand(d)
    set_balance(get_balance() + amount)
    add_transaction("bank_withdraw", amount, "Rút không kỳ hạn")
    return {"ok": True}


def claim_demand_interest() -> int:
    from .balance import get_balance, set_balance
    from .transactions import add_transaction
    interest = int(calc_demand_interest())
    if interest <= 0:
        return 0
    d = _get_demand()
    d["ts"] = time.time()
    _save_demand(d)
    set_balance(get_balance() + interest)
    add_transaction("interest", interest, f"Lãi không kỳ hạn {DEMAND_PRODUCT['rate'] * 100:.1f}%/năm")
    return interest


def _flush_demand_interest():
    interest = int(calc_demand_interest())
    if interest > 0:
        from .balance import get_balance, set_balance
        from .transactions import add_transaction
        d = _get_demand()
        d["ts"] = time.time()
        _save_demand(d)
        set_balance(get_balance() + interest)
        add_transaction("interest", interest, "Lãi không kỳ hạn (tự động)")


# ── Term Deposits ──────────────────────────────────────────────

def _get_deposits() -> list:
    return cfg_list(_KEY_DEPOSITS, [])


def _save_deposits(lst: list):
    cfg_set(_KEY_DEPOSITS, lst)


def _get_send_more_log() -> list:
    return cfg_list(_KEY_SEND_MORE_LOG, [])


def _save_send_more_log(entries: list):
    cfg_set(_KEY_SEND_MORE_LOG, entries)


def _get_week_bucket(ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(ts if ts is not None else time.time())
    iso = dt.isocalendar()
    return f"{iso.year:04d}-W{iso.week:02d}"


def _get_deposit_segments(dep: dict) -> list:
    segments = []

    base_amount = int(dep.get("amount", 0) or 0)
    if base_amount > 0:
        segments.append({
            "amount": base_amount,
            "start_ts": float(dep.get("start_ts", time.time()) or time.time()),
        })

    for topup in dep.get("topups", []) or []:
        amount = int(topup.get("amount", 0) or 0)
        if amount <= 0:
            continue
        segments.append({
            "amount": amount,
            "start_ts": float(topup.get("start_ts", time.time()) or time.time()),
        })

    return segments


def _get_current_week_send_more_entries() -> list:
    week = _get_week_bucket()
    return [
        entry for entry in _get_send_more_log()
        if isinstance(entry, dict) and entry.get("week") == week
    ]


def get_send_more_status() -> dict:
    used = len(_get_current_week_send_more_entries())
    return {
        "limit": _SEND_MORE_WEEKLY_LIMIT,
        "used": used,
        "remaining": max(0, _SEND_MORE_WEEKLY_LIMIT - used),
    }


def _record_send_more(deposit_id: str, amount: int):
    now = time.time()
    entries = _get_current_week_send_more_entries()
    entries.append({
        "deposit_id": deposit_id,
        "amount": int(amount),
        "ts": now,
        "week": _get_week_bucket(now),
    })
    _save_send_more_log(entries[-20:])


def _calc_term_value(dep: dict, at_time: float = None) -> dict:
    if at_time is None:
        at_time = time.time()

    term_months = int(dep.get("term_months", 1) or 1)
    product = _get_term_product(dep.get("product_code"))
    plan = LEGACY_TERM_PLANS.get(term_months, LEGACY_TERM_PLANS[1])
    default_rate = float(plan["rate"])
    if product:
        default_rate = _get_product_rate(dep.get("product_code", ""), term_months, int(dep.get("amount", 0) or 0)) or default_rate
    rate = float(dep.get("rate", default_rate) or default_rate)
    compound = bool(dep.get("compound", (product or plan).get("compound", True)))
    interest_mode = dep.get("interest_mode") or (product or {}).get("interest_mode") or "maturity"
    term_secs = term_months * 30.44 * 24 * 3600
    segments = _get_deposit_segments(dep)

    # interest_speed_boost: làm lãi tích lũy nhanh hơn
    # Ví dụ: boost = 0.5 → elapsed × 1.5 → lãi nhanh hơn 50%
    try:
        speed_boost = get_interest_speed_boost()
    except Exception as e:
        logger.debug("_calc_term_value: get_interest_speed_boost — %s", e)
        speed_boost = 0.0
    speed_factor = 1.0 + speed_boost  # 1.0 = bình thường, 1.5 = nhanh hơn 50%

    if not segments:
        return {
            "principal": 0,
            "interest": 0,
            "total": 0,
            "progress_pct": 0,
            "matured": False,
            "seconds_left": 0,
            "interest_at_maturity": 0,
            "total_at_maturity": 0,
            "interest_paid_total": 0,
            "payout_at_close": 0,
        }

    principal = 0
    interest = 0.0
    total = 0.0
    progress_values = []
    seconds_left_values = []
    matured = True
    gross_interest_at_maturity = 0.0
    total_at_maturity = 0.0
    interest_paid_total = float(dep.get("interest_paid_total", 0) or 0)
    interval_months = int(dep.get("payout_interval_months", 1) or 1)
    interval_secs = interval_months * 30.44 * 24 * 3600

    for seg in segments:
        seg_amount = int(seg.get("amount", 0) or 0)
        start_ts = float(seg.get("start_ts", time.time()) or time.time())
        elapsed = max(0.0, at_time - start_ts)

        # Áp dụng speed boost: elapsed ảo tăng lên, giúp lãi tích lũy nhanh hơn
        boosted_elapsed = elapsed * speed_factor

        seg_matured = boosted_elapsed >= term_secs
        seg_progress = min(boosted_elapsed / term_secs * 100, 100) if term_secs > 0 else 100
        seg_seconds_left = max(0.0, term_secs - boosted_elapsed)

        years_elapsed = boosted_elapsed / _SECS_PER_YEAR

        if interest_mode == "upfront":
            seg_total = float(seg_amount)
            seg_interest = 0.0
        elif interest_mode == "periodic":
            paid_periods = int(dep.get("paid_periods", 0) or 0)
            cycle_elapsed = max(0.0, elapsed - (paid_periods * interval_secs))
            cycle_elapsed = min(cycle_elapsed, interval_secs)
            seg_interest = _calc_simple_interest(seg_amount, rate, cycle_elapsed / _SECS_PER_YEAR)
            seg_total = seg_amount + seg_interest
        else:
            seg_total = _calc_growth_value(seg_amount, rate, years_elapsed, compound)
            seg_interest = seg_total - seg_amount

        principal += seg_amount
        total += seg_total
        interest += seg_interest
        progress_values.append(seg_progress)
        seconds_left_values.append(seg_seconds_left)
        matured = matured and seg_matured
        maturity_total = _calc_growth_value(seg_amount, rate, term_months / 12, compound)
        total_at_maturity += maturity_total
        gross_interest_at_maturity += maturity_total - seg_amount

    if interest_mode == "periodic":
        total_at_maturity = principal + gross_interest_at_maturity
    elif interest_mode == "upfront":
        total_at_maturity = principal + interest_paid_total

    if interest_mode == "upfront":
        payout_at_close = principal
    elif interest_mode == "periodic":
        payout_at_close = principal
    else:
        payout_at_close = total

    return {
        "principal":            principal,
        "interest":             interest,
        "total":                total,
        "progress_pct":         min(progress_values) if progress_values else 0,
        "matured":              matured,
        "seconds_left":         max(seconds_left_values) if seconds_left_values else 0,
        "interest_at_maturity": gross_interest_at_maturity,
        "total_at_maturity":    total_at_maturity,
        "interest_paid_total":  interest_paid_total,
        "payout_at_close":      payout_at_close,
    }


def open_term_deposit(amount: int, term_months: int, product_code: str) -> dict:
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    product = _get_term_product(product_code)
    if not product:
        return {"ok": False, "error": "Sản phẩm gửi tiền không hợp lệ."}
    if term_months not in product["terms"]:
        return {"ok": False, "error": "Kỳ hạn không hợp lệ cho sản phẩm đã chọn."}

    min_amount = int(product.get("min_amount", 100_000) or 100_000)
    if amount < min_amount:
        return {"ok": False, "error": f"Số tiền tối thiểu là {min_amount:,} VND.".replace(",", ".")}

    bal = get_balance()
    if bal < amount:
        return {"ok": False, "error": "Số dư ví không đủ."}

    rate = _get_product_rate(product_code, term_months, amount)
    if rate <= 0:
        return {"ok": False, "error": "Không tìm thấy lãi suất phù hợp."}

    interest_mode = product.get("interest_mode", "maturity")
    upfront_interest = 0
    new_balance = bal - amount
    if interest_mode == "upfront":
        upfront_interest = int(round(_calc_simple_interest(amount, rate, term_months / 12)))
        new_balance += upfront_interest
    set_balance(new_balance)

    dep = {
        "id":                    str(uuid.uuid4())[:8],
        "amount":                int(amount),
        "term_months":           int(term_months),
        "start_ts":              time.time(),
        "rate":                  rate,
        "label":                 f"{product['label']} • {term_months} tháng",
        "product_code":          product_code,
        "product_label":         product["label"],
        "interest_mode":         interest_mode,
        "compound":              bool(product.get("compound", False)),
        "allow_topup":           bool(product.get("allow_topup", False)),
        "topups":                [],
        "interest_paid_total":   upfront_interest,
        "payout_cycle_label":    "",
    }
    if interest_mode == "periodic":
        interval_months = _get_periodic_interval_months(term_months)
        dep["payout_interval_months"] = interval_months
        dep["payout_cycle_label"] = _format_payout_cycle(interval_months)

    deps = _get_deposits()
    deps.append(dep)
    _save_deposits(deps)

    projected_total = _calc_growth_value(amount, rate, term_months / 12, bool(product.get("compound", False)))
    projected_interest = int(round(projected_total - amount))
    add_transaction("deposit", amount, f"Mở sổ {dep['label']} — {rate*100:.2f}%/năm")
    if upfront_interest > 0:
        add_transaction("interest", upfront_interest, f"Nhận lãi trước sổ {dep['label']} #{dep['id']}")

    return {
        "ok": True,
        "deposit_id": dep["id"],
        "interest_at_maturity": projected_interest,
        "interest_paid_now": upfront_interest,
        "interest_mode": interest_mode,
        "product_label": product["label"],
    }


def close_term_deposit(deposit_id: str, force: bool = False) -> dict:
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    _sync_periodic_payouts()
    deps = _get_deposits()
    dep  = next((d for d in deps if d.get("id") == deposit_id), None)
    if not dep:
        return {"ok": False, "error": "Không tìm thấy sổ."}

    info    = _calc_term_value(dep)
    matured = info["matured"]
    interest_mode = dep.get("interest_mode") or "maturity"

    if not matured and not force:
        return {
            "ok": False,
            "error": "Sổ chưa đáo hạn.",
            "early_withdraw": True,
            "seconds_left": info["seconds_left"],
        }

    principal       = int(info["principal"] or 0)
    payout = principal
    interest_earned = 0

    if matured:
        if interest_mode == "upfront":
            payout = principal
            interest_earned = int(dep.get("interest_paid_total", 0) or 0)
        elif interest_mode == "periodic":
            payout = principal
            interest_earned = int(dep.get("interest_paid_total", 0) or 0)
        else:
            payout = int(info["total"])
            interest_earned = payout - principal
    else:
        if interest_mode == "upfront":
            paid_now = int(dep.get("interest_paid_total", 0) or 0)
            payout = max(0, principal - paid_now)
        else:
            payout = principal

    deps = [d for d in deps if d.get("id") != deposit_id]
    _save_deposits(deps)
    set_balance(get_balance() + payout)

    if matured:
        if interest_mode == "maturity" and interest_earned > 0:
            add_transaction("interest", interest_earned, f"Lãi sổ {dep.get('label','?')} #{dep.get('id','?')}")
        add_transaction("withdraw", principal, f"Tất toán sổ {dep.get('label','?')} #{dep.get('id','?')}")
    else:
        if interest_mode == "upfront":
            paid_now = int(dep.get("interest_paid_total", 0) or 0)
            add_transaction("withdraw", payout, f"Rút sớm sổ {dep.get('label','?')} #{dep.get('id','?')} (thu hồi lãi trả trước {paid_now:,} VND)".replace(",", "."))
        else:
            add_transaction("withdraw", payout, f"Rút sớm sổ {dep.get('label','?')} #{dep.get('id','?')} (mất lãi)")

    return {"ok": True, "payout": payout,
            "interest_earned": interest_earned, "matured": matured}


def add_term_funds(deposit_id: str, amount: int) -> dict:
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    if amount <= 0:
        return {"ok": False, "error": "Số tiền không hợp lệ."}

    status = get_send_more_status()
    if status["remaining"] <= 0:
        return {"ok": False, "error": "Bạn chỉ có thể gửi thêm tối đa 3 lần mỗi tuần."}

    deps = _get_deposits()
    dep = next((d for d in deps if d.get("id") == deposit_id), None)
    if not dep:
        return {"ok": False, "error": "Không tìm thấy sổ."}
    if not dep.get("allow_topup", False):
        return {"ok": False, "error": "Sổ này không hỗ trợ gửi thêm."}

    bal = get_balance()
    if bal < amount:
        return {"ok": False, "error": "Số dư ví không đủ."}

    set_balance(bal - amount)
    topups = dep.get("topups", []) or []
    topups.append({
        "amount": int(amount),
        "start_ts": time.time(),
    })
    dep["topups"] = topups
    _save_deposits(deps)
    _record_send_more(deposit_id, amount)

    add_transaction("deposit", amount, f"Gửi thêm vào sổ {dep.get('label', '?')} #{dep.get('id', '?')}")

    return {
        "ok": True,
        "deposit_id": deposit_id,
        "remaining_this_week": get_send_more_status()["remaining"],
    }


# ── Interest Speed Boost (từ passive effects) ──────────────────

def get_interest_speed_boost() -> float:
    """
    Đọc passive effects để lấy interest_speed_boost.
    Trả về hệ số (0.0 = không boost, 0.5 = lãi nhanh hơn 50%).
    """
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        return float(passive.get("interest_speed_boost", 0.0))
    except Exception as e:
        logger.debug("get_interest_speed_boost: %s", e)
        return 0.0


def get_instant_interest_cooldown() -> float:
    """
    Đọc passive effects để lấy instant_interest_cooldown (giây).
    Trả về thời gian hồi giữa 2 lần thu lãi tức thì.
    0 = không có kỹ năng này.
    """
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        cooldown = float(passive.get("instant_interest_cooldown", 0.0))
        reduction = float(passive.get("skill_cooldown_reduction", 0.0))
        if cooldown > 0 and reduction > 0:
            cooldown = cooldown * max(0.1, 1.0 - reduction)
        return cooldown
    except Exception as e:
        logger.debug("get_instant_interest_cooldown: %s", e)
        return 0.0


def _get_instant_interest_state() -> dict:
    return cfg_dict(_KEY_INSTANT_INTEREST, {"last_claim_ts": 0.0})


def _save_instant_interest_state(state: dict):
    cfg_set(_KEY_INSTANT_INTEREST, state)


def get_instant_interest_status() -> dict:
    """
    Trả về trạng thái kỹ năng thu lãi tức thì.
    {
        "enabled": bool,          # Có item nào cho kỹ năng này không
        "cooldown": float,        # Tổng cooldown (giây)
        "remaining": float,       # Thời gian còn lại (giây)
        "ready": bool,            # Có thể dùng ngay không
    }
    """
    cooldown = get_instant_interest_cooldown()
    if cooldown <= 0:
        return {"enabled": False, "cooldown": 0, "remaining": 0, "ready": False}

    state = _get_instant_interest_state()
    last = float(state.get("last_claim_ts", 0.0) or 0.0)
    now = time.time()
    elapsed = now - last
    remaining = max(0.0, cooldown - elapsed)

    return {
        "enabled": True,
        "cooldown": cooldown,
        "remaining": remaining,
        "ready": remaining <= 0,
    }


def claim_instant_term_interest() -> dict:
    """
    Thu lãi tức thì từ tất cả sổ tiết kiệm có kỳ hạn (không đóng sổ).
    Chỉ hoạt động nếu có passive effect instant_interest_cooldown > 0
    và đã hết thời gian hồi.

    Cơ chế:
      - Tính lãi hiện tại của mỗi sổ (dùng _calc_term_value)
      - Ghi nhận lãi vào balance
      - Reset start_ts để lãi bắt đầu tích lũy lại từ đầu
      - Lưu thời điểm thu lãi để tính cooldown
    """
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    # Kiểm tra cooldown
    status = get_instant_interest_status()
    if not status["enabled"]:
        return {"ok": False, "error": "Bạn chưa có kỹ năng thu lãi tức thì. Mua vật phẩm tài chính để kích hoạt!"}
    if not status["ready"]:
        remaining_h = int(status["remaining"] // 3600)
        remaining_m = int((status["remaining"] % 3600) // 60)
        return {
            "ok": False,
            "error": f"Kỹ năng đang hồi. Còn {remaining_h}h{remaining_m:02d}m nữa.",
            "remaining": status["remaining"],
        }

    # Đồng bộ periodic payouts trước
    _sync_periodic_payouts()

    deps = _get_deposits()
    if not deps:
        return {"ok": False, "error": "Bạn chưa có sổ tiết kiệm nào."}

    total_interest = 0
    total_principal = 0
    claimed_deps = []

    for dep in deps:
        interest_mode = dep.get("interest_mode") or "maturity"
        if interest_mode == "upfront":
            # Lãi trả trước rồi, không thu thêm
            continue

        info = _calc_term_value(dep)
        principal = int(info["principal"] or 0)
        current_total = int(info["total"] or 0)
        interest = current_total - principal

        if interest <= 0:
            continue

        total_interest += interest
        total_principal += principal
        claimed_deps.append(dep.get("label", "?"))

        # Reset start_ts để bắt đầu tích lũy lại — dời toàn bộ segments
        now_ts = time.time()
        segments = _get_deposit_segments(dep)
        for seg in segments:
            seg["start_ts"] = now_ts
        # Cập nhật amount gốc (giữ nguyên, chỉ reset thời gian)
        dep["start_ts"] = now_ts
        # Reset periodic tracking
        dep["paid_periods"] = 0
        dep["interest_paid_total"] = 0

    if total_interest <= 0:
        return {"ok": False, "error": "Hiện chưa có lãi phát sinh trên các sổ."}

    # Ghi nhận lãi
    _save_deposits(deps)
    set_balance(get_balance() + total_interest)

    # Ghi cooldown
    state = _get_instant_interest_state()
    state["last_claim_ts"] = time.time()
    _save_instant_interest_state(state)

    desc = " + ".join(claimed_deps[:3])
    if len(claimed_deps) > 3:
        desc += f" và {len(claimed_deps)-3} sổ khác"
    add_transaction("interest", total_interest, f"📌 Thu lãi tức thì: {desc}")

    # Cập nhật lại trạng thái sau khi claim
    new_status = get_instant_interest_status()

    return {
        "ok": True,
        "interest_claimed": total_interest,
        "deps_count": len(claimed_deps),
        "cooldown_remaining": new_status["remaining"],
    }


def get_all_deposits_info() -> list:
    _sync_periodic_payouts()
    deps = _get_deposits()
    result = []
    for dep in deps:
        info = _calc_term_value(dep)
        rate = float(dep.get("rate", 0.04) or 0.04)
        interest_mode = dep.get("interest_mode") or "maturity"
        result.append({
            **dep,
            **info,
            "rate_pct": rate * 100,
            "topup_count": len(dep.get("topups", []) or []),
            "display_term": f"{int(dep.get('term_months', 0) or 0)} tháng",
            "allow_topup": bool(dep.get("allow_topup", False)),
            "interest_mode_label": {
                "maturity": "Lãi cuối kỳ",
                "periodic": f"Lĩnh lãi {dep.get('payout_cycle_label') or 'định kỳ'}",
                "upfront": "Lãi nhận ngay",
            }.get(interest_mode, "Lãi cuối kỳ"),
        })
    return result


def get_bank_products() -> list:
    products = [{
        "code": DEMAND_PRODUCT["code"],
        "kind": "demand",
        "label": DEMAND_PRODUCT["label"],
        "rate": DEMAND_PRODUCT["rate"],
        "rate_pct": round(DEMAND_PRODUCT["rate"] * 100, 2),
        "min_amount": 1_000,
        "note": DEMAND_PRODUCT["note"],
        "reference": DEMAND_PRODUCT["reference"],
        "terms": [],
    }]

    for code, product in TERM_PRODUCTS.items():
        products.append({
            "code": code,
            "kind": "term",
            "label": product["label"],
            "note": product["note"],
            "reference": product["reference"],
            "min_amount": int(product.get("min_amount", 100_000) or 100_000),
            "allow_topup": bool(product.get("allow_topup", False)),
            "interest_mode": product.get("interest_mode", "maturity"),
            "terms": [
                {
                    "months": months,
                    "label": f"{months} tháng",
                    "rate": _get_product_rate(code, months, int(product.get("min_amount", 100_000) or 100_000)),
                    "rate_pct": round(_get_product_rate(code, months, int(product.get("min_amount", 100_000) or 100_000)) * 100, 2),
                }
                for months in sorted(product["terms"])
            ],
            "tiers": product.get("tiers", []),
        })
    return products


def get_term_plans() -> list:
    return get_bank_products()


# ── Tổng hợp ───────────────────────────────────────────────────

def get_total_savings() -> int:
    total = get_demand_balance()
    for dep in _get_deposits():
        total += sum(int(seg.get("amount", 0) or 0) for seg in _get_deposit_segments(dep))
    return total


def get_total_current_value() -> float:
    _sync_periodic_payouts()
    total = get_demand_balance() + calc_demand_interest()
    for dep in _get_deposits():
        info = _calc_term_value(dep)
        total += info["total"]
    return total


# ── Legacy aliases ─────────────────────────────────────────────

def get_savings() -> int:
    return get_total_savings()

def calculate_interest() -> int:
    return int(calc_demand_interest())

def claim_interest() -> int:
    return claim_demand_interest()

def deposit(amount: int) -> bool:
    return deposit_demand(amount)["ok"]

def withdraw(amount: int) -> bool:
    return withdraw_demand(amount)["ok"]
