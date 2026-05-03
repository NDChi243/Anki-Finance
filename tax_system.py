# -*- coding: utf-8 -*-
"""
tax_system.py
-------------
Hệ thống thuế đầy đủ của Anki Tycoon.

A. Thuế tài sản hàng ngày:
  - Ngưỡng > 10M VND, thu hàng ngày khi mở Anki
  - Lũy tiến theo thu nhập tháng (0.1%–0.5%/ngày)

B. Thuế TNCN (Biểu thuế 2026 — 5 bậc):
  - Khấu trừ tạm thời NGAY KHI có thu nhập (withholding)
  - Giảm trừ bản thân 15,5M + giảm trừ học tập (tối đa 5M)
  - Quyết toán chênh lệch cuối tháng
  - Nguồn: Thư viện pháp luật - Công thức tính thuế TNCN 2026

C. Thuế tiêu thụ đặc biệt / SCT:
  - Tính thêm khi mua đồ tại shop theo danh mục
  - Xe ô tô: 45%, xe sang >5B: 150%, xa xỉ: 20%, điện tử: 10%

D. Thuế đất hàng năm:
  - Nhà ở mua đứt: 0.03%/năm → tính hàng tháng
  - BĐS đầu tư: 0.15%/năm → tính hàng tháng

E. Thuế chuyển nhượng BĐS:
  - 2% giá trị khi bán BĐS đầu tư
"""

import time
from ._safe_config import col_ready, cfg_int, cfg_str, cfg_list, cfg_set

_KEY_LAST_TAX_DATE = "anki_tycoon_last_tax_date"
_KEY_TAX_LOG       = "anki_tycoon_tax_log"

TAX_THRESHOLD = 10_000_000   # Ngưỡng bắt đầu tính thuế

# Bảng thuế: (ngưỡng_thu_nhập_tháng, tỷ_lệ_ngày)
TAX_BRACKETS = [
    (100_000_000, 0.005),   # > 100M  → 0.5%/ngày
    (20_000_000,  0.004),   # > 20M   → 0.4%/ngày
    (5_000_000,   0.003),   # > 5M    → 0.3%/ngày
    (1_000_000,   0.002),   # > 1M    → 0.2%/ngày
    (0,           0.001),   # ≥ 0     → 0.1%/ngày
]
MAX_LOG = 60


def _get_tax_reduction_factor() -> float:
    """
    Đọc tax_reduction từ passive effects.
    Trả về hệ số nhân thuế (1.0 = không giảm, 0.5 = giảm 50%).
    """
    try:
        from .item_effects import get_all_passive_effects
        passive = get_all_passive_effects()
        reduction = float(passive.get("tax_reduction", 0.0))
        reduction = min(max(reduction, 0.0), 0.9)  # cap 0%–90%
        if reduction > 0:
            return 1.0 - reduction
    except Exception:
        pass
    return 1.0


def _today() -> str:
    """Trả về 'YYYY-MM-DD' dùng Unix timestamp, chống time travel."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time()))


def get_tax_rate(monthly_income: int) -> float:
    """Trả về tỷ lệ thuế ngày dựa theo thu nhập tháng."""
    for threshold, rate in TAX_BRACKETS:
        if monthly_income > threshold:
            return rate
    return 0.001


def calculate_tax(total_assets: int, monthly_income: int) -> dict:
    """
    Tính thuế phải nộp.
    Trả về: {taxable, rate, amount, rate_pct}
    """
    if total_assets <= TAX_THRESHOLD:
        return {"taxable": False, "rate": 0, "amount": 0, "rate_pct": 0}

    rate   = get_tax_rate(monthly_income)
    amount = round(total_assets * rate)
    # Áp dụng giảm thuế từ passive effects
    tax_factor = _get_tax_reduction_factor()
    if tax_factor < 1.0:
        amount = round(amount * tax_factor)
    return {
        "taxable":   True,
        "rate":      rate,
        "rate_pct":  rate * 100,
        "amount":    amount,
        "assets":    total_assets,
        "income":    monthly_income,
    }


def check_and_collect_tax() -> dict:
    """
    Kiểm tra và thu thuế nếu hôm nay chưa thu.
    Gọi khi mở Anki (profileLoaded).
    Trả về dict kết quả — UI dùng để hiển thị thông báo nếu cần.
    """
    if not col_ready():
        return {"collected": False, "reason": "not_ready"}

    # Đã thu hôm nay rồi?
    if cfg_str(_KEY_LAST_TAX_DATE, "") == _today():
        return {"collected": False, "reason": "already_collected"}

    # Tính tổng tài sản
    from .balance import get_balance
    from .bank import get_total_savings
    from .finance import get_monthly_income

    try:
        wallet  = get_balance()
        savings = get_total_savings()
        try:
            from .digital_assets import get_crypto_portfolio_value
            crypto_value = get_crypto_portfolio_value()
        except Exception:
            crypto_value = 0
        total   = wallet + savings + crypto_value
        income  = get_monthly_income()
    except Exception:
        return {"collected": False, "reason": "error"}

    tax_info = calculate_tax(total, income)

    if not tax_info["taxable"]:
        # Vẫn đánh dấu đã kiểm tra hôm nay
        cfg_set(_KEY_LAST_TAX_DATE, _today())
        _append_log({
            "date":       _today(),
            "collected":  False,
            "reason":     "below_threshold",
            "total":      total,
            "threshold":  TAX_THRESHOLD,
            "tax":        0,
            "rate_pct":   0,
        })
        return {"collected": False, "reason": "below_threshold", "total": total}

    # Thu thuế
    amount = tax_info["amount"]
    new_balance = wallet - amount
    from .balance import set_balance
    set_balance(new_balance)

    cfg_set(_KEY_LAST_TAX_DATE, _today())

    from .transactions import add_transaction
    add_transaction(
        "tax", amount,
        f"Thuế tài sản {tax_info['rate_pct']:.1f}%/ngày "
        f"(TTS: {_fmt(total)}, Thu nhập tháng: {_fmt(income)})"
    )

    log_entry = {
        "date":      _today(),
        "collected": True,
        "total":     total,
        "savings":   savings,
        "wallet":    wallet,
        "income":    income,
        "rate_pct":  tax_info["rate_pct"],
        "tax":       amount,
    }
    _append_log(log_entry)

    return {
        "collected":  True,
        "amount":     amount,
        "rate_pct":   tax_info["rate_pct"],
        "total":      total,
        "new_balance": new_balance,
    }


def _append_log(entry: dict) -> None:
    log = cfg_list(_KEY_TAX_LOG, [])
    log.insert(0, entry)
    if len(log) > MAX_LOG:
        log = log[:MAX_LOG]
    cfg_set(_KEY_TAX_LOG, log)


def get_tax_log() -> list:
    return cfg_list(_KEY_TAX_LOG, [])


def get_tax_status_today() -> dict:
    """Trạng thái thuế hôm nay để hiển thị trên UI."""
    if not col_ready():
        return {"collected_today": False, "next_tax": 0, "rate_pct": 0}

    from .balance import get_balance
    from .bank import get_total_savings
    from .finance import get_monthly_income

    wallet  = get_balance()
    savings = get_total_savings()
    try:
        from .digital_assets import get_crypto_portfolio_value
        crypto_value = get_crypto_portfolio_value()
    except Exception:
        crypto_value = 0
    total   = wallet + savings + crypto_value
    income  = get_monthly_income()

    tax_info         = calculate_tax(total, income)
    collected_today  = cfg_str(_KEY_LAST_TAX_DATE, "") == _today()

    # Lấy số tiền đã thu hôm nay từ log
    tax_today = 0
    log = get_tax_log()
    if log and log[0].get("date") == _today():
        tax_today = log[0].get("tax", 0)

    return {
        "collected_today": collected_today,
        "taxable":         tax_info["taxable"],
        "total_assets":    total,
        "threshold":       TAX_THRESHOLD,
        "rate_pct":        tax_info.get("rate_pct", 0),
        "next_tax":        tax_info.get("amount", 0),
        "tax_today":       tax_today,
        "monthly_income":  income,
    }


def _fmt(n: int) -> str:
    return f"{n:,}đ".replace(",", ".")


# ═══════════════════════════════════════════════════════════════
# B. THUẾ THU NHẬP CÁ NHÂN (PIT) — Biểu thuế 2026
# ═══════════════════════════════════════════════════════════════

_KEY_PIT_LOG       = "anki_tycoon_pit_log"
_KEY_MONTHLY_CARDS = "anki_tycoon_monthly_cards_count"
_KEY_PIT_WITHHELD  = "anki_tycoon_pit_withheld_this_month"

# ── Biểu thuế lũy tiến TNCN 2026 (tháng, triệu đồng) ────────
# Nguồn: Thư viện pháp luật — Công thức tính thuế TNCN 2026
# theo biểu thuế và mức giảm trừ gia cảnh 2026 chính thức.
_PIT_SLABS = [
    (0,           10_000_000, 0.05),   # Bậc 1: ≤10M → 5%
    (10_000_000,  30_000_000, 0.10),   # Bậc 2: >10M–30M → 10%
    (30_000_000,  60_000_000, 0.20),   # Bậc 3: >30M–60M → 20%
    (60_000_000, 100_000_000, 0.30),   # Bậc 4: >60M–100M → 30%
    (100_000_000, None,       0.35),   # Bậc 5: >100M → 35%
]

_PERSONAL_DEDUCTION       = 15_500_000  # Giảm trừ bản thân 15,5 triệu/tháng (2026)
_STUDY_DEDUCTION_PER_CARD = 1_000       # Giảm trừ học tập: 1.000đ/thẻ ôn
_MAX_STUDY_DEDUCTION      = 5_000_000   # Tối đa 5 triệu/tháng

_PIT_SOURCE_REF = (
    "Nguồn: Thư viện pháp luật — Công thức tính thuế TNCN 2026 "
    "theo biểu thuế và mức giảm trừ gia cảnh 2026 chính thức."
)


def _calc_pit_progressive(taxable: int) -> int:
    """Tính thuế lũy tiến theo biểu thuế TNCN 2026 (5 bậc)."""
    tax = 0
    for low, high, rate in _PIT_SLABS:
        if taxable <= low:
            break
        slab = (taxable - low) if high is None else (min(taxable, high) - low)
        tax += round(slab * rate)
    return tax


def calculate_pit(monthly_income: int, cards_this_month: int) -> dict:
    """
    Tính thuế TNCN theo công thức 2026.
    Công thức: Thu nhập tính thuế = Thu nhập - Giảm trừ bản thân - Giảm trừ học tập
    """
    study_deduction = min(cards_this_month * _STUDY_DEDUCTION_PER_CARD, _MAX_STUDY_DEDUCTION)
    total_deduction = _PERSONAL_DEDUCTION + study_deduction
    taxable         = max(0, monthly_income - total_deduction)

    tax = _calc_pit_progressive(taxable)

    tax_factor = _get_tax_reduction_factor()
    if tax_factor < 1.0:
        tax = round(tax * tax_factor)

    rate_eff = (tax / monthly_income * 100) if monthly_income > 0 else 0

    return {
        "monthly_income":     monthly_income,
        "cards_this_month":   cards_this_month,
        "personal_deduction": _PERSONAL_DEDUCTION,
        "study_deduction":    study_deduction,
        "total_deduction":    total_deduction,
        "taxable_income":     taxable,
        "tax":                tax,
        "rate_eff_pct":       round(rate_eff, 2),
        "source_ref":         _PIT_SOURCE_REF,
    }


def calculate_incremental_pit(new_income: int, prev_monthly_income: int,
                               cards_so_far: int = 0) -> int:
    """
    Tính thuế TNCN tăng thêm trên khoản thu nhập mới new_income,
    biết rằng đã tích lũy prev_monthly_income trong tháng.
    Dùng cho cơ chế khấu trừ tạm thời (withholding) ngay khi có thu nhập.
    """
    if new_income <= 0:
        return 0

    study_ded    = min(cards_so_far * _STUDY_DEDUCTION_PER_CARD, _MAX_STUDY_DEDUCTION)
    prev_taxable = max(0, prev_monthly_income - _PERSONAL_DEDUCTION - study_ded)

    new_total   = prev_monthly_income + new_income
    new_taxable = max(0, new_total - _PERSONAL_DEDUCTION - study_ded)

    incremental  = max(0, _calc_pit_progressive(new_taxable) - _calc_pit_progressive(prev_taxable))

    tax_factor = _get_tax_reduction_factor()
    if tax_factor < 1.0:
        incremental = round(incremental * tax_factor)

    return incremental


def apply_pit_withholding_on_income(income_amount: int) -> dict:
    """
    Khấu trừ thuế TNCN tạm thời ngay khi có thu nhập mới.
    Cập nhật tổng khấu trừ tháng này vào config.
    Trả về {"withheld": int, "net_income": int}.
    """
    if not col_ready() or income_amount <= 0:
        return {"withheld": 0, "net_income": income_amount}

    from .finance import get_monthly_income
    prev_income = get_monthly_income()
    cards       = cfg_int(_KEY_MONTHLY_CARDS, 0)
    withheld    = calculate_incremental_pit(income_amount, prev_income, cards)

    if withheld <= 0:
        return {"withheld": 0, "net_income": income_amount}

    total_withheld = cfg_int(_KEY_PIT_WITHHELD, 0)
    cfg_set(_KEY_PIT_WITHHELD, total_withheld + withheld)

    return {"withheld": withheld, "net_income": income_amount - withheld}


def collect_monthly_pit() -> dict:
    """
    Quyết toán thuế TNCN cuối tháng.
    So sánh tổng đã khấu trừ tạm thời với thuế thực tế,
    thu thêm hoặc hoàn lại phần chênh lệch.
    Gọi từ finance.reset_monthly_if_needed khi phát hiện tháng mới.
    """
    if not col_ready():
        return {"collected": False}

    from .finance import get_monthly_income
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    income           = get_monthly_income()
    cards            = cfg_int(_KEY_MONTHLY_CARDS, 0)
    pit_info         = calculate_pit(income, cards)
    actual_tax       = pit_info["tax"]
    already_withheld = cfg_int(_KEY_PIT_WITHHELD, 0)

    # Luôn reset bộ đếm tháng dù có thuế hay không
    cfg_set(_KEY_MONTHLY_CARDS, 0)
    cfg_set(_KEY_PIT_WITHHELD, 0)

    difference = actual_tax - already_withheld

    log_entry = {
        "date":      _today(),
        "withheld":  already_withheld,
        "adjustment": difference,
        **pit_info,
    }

    if abs(difference) < 1_000:
        # Chênh lệch không đáng kể → bỏ qua quyết toán
        log_entry["collected"] = already_withheld > 0
        _append_pit_log(log_entry)
        return {"collected": already_withheld > 0, "reason": "settled_in_withholding",
                "withheld": already_withheld, **pit_info}

    bal     = get_balance()
    new_bal = bal - difference  # difference âm = hoàn thuế → tăng balance
    set_balance(new_bal)

    if difference > 0:
        add_transaction("pit_tax", difference,
            f"Quyết toán thuế TNCN — nộp thêm {_fmt(difference)} "
            f"(đã khấu trừ {_fmt(already_withheld)}, thực tế {_fmt(actual_tax)})")
    else:
        add_transaction("pit_refund", abs(difference),
            f"Quyết toán thuế TNCN — hoàn thuế {_fmt(abs(difference))} "
            f"(đã khấu trừ {_fmt(already_withheld)}, thực tế {_fmt(actual_tax)})")

    log_entry["collected"] = True
    _append_pit_log(log_entry)
    return {"collected": True, "adjustment": difference,
            "withheld": already_withheld, **pit_info}


def record_monthly_card() -> None:
    """Ghi nhận 1 thẻ ôn vào bộ đếm tháng (cho giảm trừ học tập PIT)."""
    if not col_ready():
        return
    count = cfg_int(_KEY_MONTHLY_CARDS, 0)
    cfg_set(_KEY_MONTHLY_CARDS, count + 1)


def get_pit_preview() -> dict:
    """Xem trước thuế TNCN tháng này (tính cả đã khấu trừ tạm thời)."""
    if not col_ready():
        return {}
    from .finance import get_monthly_income
    income  = get_monthly_income()
    cards   = cfg_int(_KEY_MONTHLY_CARDS, 0)
    preview = calculate_pit(income, cards)
    preview["already_withheld"]      = cfg_int(_KEY_PIT_WITHHELD, 0)
    preview["remaining_to_settle"]   = max(0, preview["tax"] - preview["already_withheld"])
    return preview


def _append_pit_log(entry: dict) -> None:
    log = cfg_list(_KEY_PIT_LOG, [])
    log.insert(0, entry)
    if len(log) > 24:  # 24 tháng
        log = log[:24]
    cfg_set(_KEY_PIT_LOG, log)


def get_pit_log() -> list:
    return cfg_list(_KEY_PIT_LOG, [])


# ═══════════════════════════════════════════════════════════════
# C. THUẾ TIÊU THỤ ĐẶC BIỆT (SCT) — Tính khi mua đồ ở shop
# ═══════════════════════════════════════════════════════════════

# Bảng SCT theo danh mục / từ khóa item_id hoặc category
_SCT_RULES = [
    # (matcher_fn, rate, label)
    # Xe sang (>5B)
    (lambda item: "🚗 Showroom xe hơi" in item.get("category","") and item.get("price",0) > 5_000_000_000,
     1.50, "Xe sang (>5B)"),
    # Xe thường
    (lambda item: "🚗 Showroom xe hơi" in item.get("category",""),
     0.45, "Xe ô tô"),
    # Xa xỉ phẩm (Rolex, đồng hồ, túi hiệu...)
    (lambda item: item.get("id","") in ("rolex","hermes_bag","gucci_bag","lv_bag","patek_watch"),
     0.20, "Hàng xa xỉ"),
    # Điện tử tiêu dùng
    (lambda item: any(k in item.get("id","") for k in ("iphone","macbook","airpods","ipad","ps5","xbox")),
     0.10, "Điện tử"),
]


def get_sct_for_item(item: dict) -> dict:
    """
    Tính thuế SCT cho 1 item khi mua.
    Trả về {"rate": float, "amount": int, "label": str, "has_sct": bool}
    """
    price = item.get("price", 0)
    for matcher, rate, label in _SCT_RULES:
        try:
            if matcher(item):
                amount = round(price * rate)
                # Áp dụng giảm thuế SCT từ passive effects
                tax_factor = _get_tax_reduction_factor()
                if tax_factor < 1.0:
                    amount = round(amount * tax_factor)
                return {
                    "has_sct": True,
                    "rate":    rate,
                    "amount":  amount,
                    "label":   label,
                    "rate_pct": rate * 100,
                }
        except Exception:
            pass
    return {"has_sct": False, "rate": 0, "amount": 0, "label": "", "rate_pct": 0}


def collect_sct(item: dict) -> int:
    """
    Thu SCT khi mua item. Trả về số tiền thuế đã trừ.
    Gọi từ web_bridge.buyItem sau khi đã deduct giá gốc.
    """
    if not col_ready():
        return 0
    sct = get_sct_for_item(item)
    if not sct["has_sct"]:
        return 0

    amount = sct["amount"]
    from .balance import get_balance, set_balance
    from .transactions import add_transaction
    bal = get_balance()
    set_balance(bal - amount)
    add_transaction(
        "sct_tax", amount,
        f"Thuế tiêu thụ đặc biệt {sct['rate_pct']:.0f}% — {item.get('name','')}"
    )
    return amount


# ═══════════════════════════════════════════════════════════════
# D. THUẾ ĐẤT HÀNG NĂM — Thu hàng tháng cùng monthly_reset
# ═══════════════════════════════════════════════════════════════

_KEY_LAND_TAX_LOG = "anki_tycoon_land_tax_log"

# Thuế suất BĐS đầu tư theo số lượng BĐS
_LAND_TAX_INVESTMENT_BASE = 0.0015   # 0.15%/năm → /12/tháng
_LAND_TAX_INVESTMENT_EXTRA = 0.0020  # 0.20%/năm từ BĐS thứ 2 trở lên


def collect_monthly_land_tax() -> dict:
    """
    Thu thuế đất hàng tháng:
      1. Nhà ở mua đứt (housing_residence) → 0.03%/năm /12
      2. BĐS đầu tư (real_estate) → 0.15%/năm cho BĐS đầu; 0.20% từ BĐS thứ 2
    Gọi cùng lúc với monthly_reset.
    """
    if not col_ready():
        return {"collected": False}

    total_tax = 0
    breakdown = []

    # Nhà ở
    try:
        from .housing_residence import get_residence, get_monthly_land_tax
        res = get_residence()
        land = get_monthly_land_tax(res)
        if land > 0:
            total_tax += land
            breakdown.append({"type": "residence", "name": res["name"], "tax": land})
    except Exception:
        pass

    # BĐS đầu tư
    try:
        from .real_estate import get_portfolio_status
        portfolio = get_portfolio_status()
        props = portfolio.get("properties", [])
        for i, prop in enumerate(props):
            price = prop.get("purchase_price", prop.get("price", 0))
            rate  = _LAND_TAX_INVESTMENT_BASE if i == 0 else _LAND_TAX_INVESTMENT_EXTRA
            tax   = round(price * rate / 12)
            if tax > 0:
                total_tax += tax
                breakdown.append({
                    "type":     "investment",
                    "name":     prop.get("name", f"BĐS #{i+1}"),
                    "price":    price,
                    "rate_pct": rate * 100,
                    "tax":      tax,
                })
    except Exception:
        pass

    # Áp dụng giảm thuế đất từ passive effects
    if total_tax > 0:
        tax_factor = _get_tax_reduction_factor()
        if tax_factor < 1.0:
            total_tax = round(total_tax * tax_factor)
            for item in breakdown:
                item["tax"] = round(item["tax"] * tax_factor)

    if total_tax <= 0:
        return {"collected": False, "reason": "no_land_tax"}

    from .balance import get_balance, set_balance
    from .transactions import add_transaction
    bal = get_balance()
    set_balance(bal - total_tax)
    add_transaction(
        "land_tax", total_tax,
        f"Thuế đất hàng tháng ({len(breakdown)} tài sản): {_fmt(total_tax)}"
    )

    log_entry = {"date": _today(), "total": total_tax, "breakdown": breakdown}
    land_log = cfg_list(_KEY_LAND_TAX_LOG, [])
    land_log.insert(0, log_entry)
    if len(land_log) > 24:
        land_log = land_log[:24]
    cfg_set(_KEY_LAND_TAX_LOG, land_log)

    return {"collected": True, "total": total_tax, "breakdown": breakdown}


def get_land_tax_log() -> list:
    return cfg_list(_KEY_LAND_TAX_LOG, [])


# ═══════════════════════════════════════════════════════════════
# E. THUẾ CHUYỂN NHƯỢNG BĐS — Tính khi bán BĐS đầu tư
# ═══════════════════════════════════════════════════════════════

TRANSFER_TAX_RATE = 0.02  # 2%


def collect_transfer_tax(selling_price: int, property_name: str = "") -> int:
    """
    Thu thuế 2% khi bán BĐS đầu tư. Trả về số tiền thuế.
    Gọi từ real_estate.remove_property khi bán.
    """
    if not col_ready() or selling_price <= 0:
        return 0
    tax = round(selling_price * TRANSFER_TAX_RATE)
    # Áp dụng giảm thuế chuyển nhượng từ passive effects
    tax_factor = _get_tax_reduction_factor()
    if tax_factor < 1.0:
        tax = round(tax * tax_factor)
    from .balance import get_balance, set_balance
    from .transactions import add_transaction
    set_balance(get_balance() - tax)
    add_transaction(
        "transfer_tax", tax,
        f"Thuế chuyển nhượng BĐS 2% — {property_name}: {_fmt(tax)}"
    )
    return tax


# ═══════════════════════════════════════════════════════════════
# F. TỔNG HỢP: get_full_tax_status — dùng cho UI
# ═══════════════════════════════════════════════════════════════

def get_full_tax_status() -> dict:
    """Trả về toàn bộ trạng thái thuế cho UI Finance > Thuế."""
    if not col_ready():
        return {}
    wealth  = get_tax_status_today()
    pit     = get_pit_preview()
    try:
        from .housing_residence import get_monthly_land_tax, get_residence
        land_res = get_monthly_land_tax(get_residence())
    except Exception:
        land_res = 0
    try:
        from .loan_system import get_loan_info
        loan = get_loan_info()
    except Exception:
        loan = {"has_loan": False}

    tax_guide = {
        "source_ref":           _PIT_SOURCE_REF,
        "personal_deduction":   _PERSONAL_DEDUCTION,
        "study_bonus_per_card": _STUDY_DEDUCTION_PER_CARD,
        "max_study_deduction":  _MAX_STUDY_DEDUCTION,
        "slabs": [
            {
                "from_m":   low // 1_000_000,
                "to_m":     (high // 1_000_000) if high else None,
                "rate_pct": rate * 100,
            }
            for low, high, rate in _PIT_SLABS
        ],
        "how_withholding_works": (
            "Thuế TNCN được khấu trừ tạm thời ngay khi bạn nhận thưởng học tập. "
            "Cuối tháng, hệ thống quyết toán chênh lệch (nộp thêm hoặc hoàn thuế)."
        ),
    }

    return {
        "wealth_tax":         wealth,
        "pit_preview":        pit,
        "land_tax_residence": land_res,
        "loan":               loan,
        "pit_log":            get_pit_log()[:6],
        "land_log":           get_land_tax_log()[:6],
        "tax_guide":          tax_guide,
    }
