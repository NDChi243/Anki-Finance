# -*- coding: utf-8 -*-
"""
real_estate.py — Bất động sản cho thuê Anki Tycoon (Expanded).

Phase 2:
  - Market value fluctuation (giá trị thị trường biến động theo thời gian)
  - Renovation / Upgrade (nâng cấp BĐS — tăng fair_rent + market_value)
  - Enhanced portfolio (market_value, value_change, upgrade_level, ROI)
  - Bán BĐS theo giá thị trường thay vì 50% cố định

Người chơi mua BĐS từ shop → cấu hình giá thuê → nhận thu nhập thụ động
ngay cả khi không mở Anki (tính theo time elapsed khi mở lại).

Cơ chế:
  - Mỗi BĐS có base_rent (gợi ý), market_value (giá trị thị trường)
  - Người chơi tự đặt rent_price (kéo slider hoặc nhập)
  - satisfaction = f(rent_price / fair_rent) → màu gradient
  - Nếu satisfaction < 20% → tenant bỏ đi (vacant = True)
  - Thu nhập cộng dồn theo giây kể từ lần cuối collect
  - Thuế BĐS = 15% thu nhập cho thuê / tháng
  - Max tích lũy = 30 ngày (tránh overflow khi bỏ lâu)
"""

import time
import math
import random
from datetime import datetime
from ._safe_config import col_ready, cfg_list, cfg_dict, cfg_set, cfg_int

_KEY_PORTFOLIO     = "anki_tycoon_re_portfolio"      # [{slot_id, item_id, ...}]
_KEY_LAST_COLLECT  = "anki_tycoon_re_last_collect"
_KEY_MARKET       = "anki_tycoon_re_market"           # {item_id: {"value": int, "trend": float, "updated": float}}
_KEY_UPGRADES     = "anki_tycoon_re_upgrades"         # {slot_id: {"level": int, "spent": int, "upgraded_at": float}}

MAX_ACCUMULATE_DAYS = 30
RENT_TAX_RATE       = 0.15    # 15% thuế thu nhập cho thuê
SECS_PER_MONTH      = 30 * 24 * 3600
SECS_PER_DAY        = 86400

# ── Market value simulation constants ──
MV_UPDATE_INTERVAL = 6 * 3600     # Cập nhật mỗi 6h
MV_AMPLITUDE       = 0.15         # Biên độ dao động ±15%
MV_DRIFT_PER_DAY   = 0.005        # Drift tối đa 0.5%/ngày

# ── Upgrade constants ──
MAX_UPGRADE_LEVEL  = 5
UPGRADE_COST_RATIO = 0.08         # Mỗi cấp = 8% giá mua
UPGRADE_RENT_BONUS = 0.10         # +10% fair_rent/cấp
UPGRADE_VALUE_BONUS = 0.08        # +8% market_value/cấp


def _now() -> float:
    return time.time()


def _get_portfolio() -> list:
    return cfg_list(_KEY_PORTFOLIO, [])

def _save_portfolio(p: list):
    cfg_set(_KEY_PORTFOLIO, p)


# ════════════════════════════════════════════════════════════════
#  Market Value Fluctuation
# ════════════════════════════════════════════════════════════════

def _get_market_data() -> dict:
    """{item_id: {"value": int, "trend": float, "updated": float}}"""
    return cfg_dict(_KEY_MARKET, {})

def _save_market_data(data: dict):
    cfg_set(_KEY_MARKET, data)

def _seed_re_market():
    """Khởi tạo market data mặc định nếu chưa có."""
    data = _get_market_data()
    if data:
        return data
    # Seed từ shop items
    try:
        from .shop_data import get_item
        # Các item_id BĐS
        re_ids = ["re_chungcu","re_nhamat","re_villa","re_toanha",
                  "re_shophouse","re_condotel","re_datnen"]
        for rid in re_ids:
            item = get_item(rid)
            if item:
                price = item.get("price", 0)
                seed_val = hash(rid) % 1000 / 1000.0  # 0.000–0.999
                trend = (seed_val - 0.5) * 2 * MV_DRIFT_PER_DAY  # -0.005..+0.005
                data[rid] = {
                    "value": price,
                    "trend": trend,
                    "updated": _now(),
                }
    except Exception:
        pass
    _save_market_data(data)
    return data

def _update_market_values() -> dict:
    """
    Cập nhật giá trị thị trường cho tất cả loại BĐS.
    Chạy mỗi MV_UPDATE_INTERVAL (6h) hoặc khi UI load.
    Trả về dict {item_id: market_value}.
    """
    data = _get_market_data()
    if not data:
        data = _seed_re_market()

    now = _now()
    updated = False
    for item_id, mv in data.items():
        last_up = float(mv.get("updated", now))
        elapsed = now - last_up
        if elapsed < MV_UPDATE_INTERVAL:
            continue
        price = mv.get("value", 0)
        trend = mv.get("trend", 0)

        # Số ngày đã trôi qua
        days = elapsed / SECS_PER_DAY
        # Drift: trend * days
        drift = trend * days
        # Random walk component: seeded deterministic theo item_id + cycle
        cycle = int(now // MV_UPDATE_INTERVAL)
        seed = hash(f"{item_id}_{cycle}") & 0x7FFFFFFF
        rng = random.Random(seed)
        noise = rng.uniform(-MV_AMPLITUDE, MV_AMPLITUDE)

        change_pct = drift + noise
        change_pct = max(-0.25, min(0.25, change_pct))  # cap ±25%/lần

        new_value = int(price * (1.0 + change_pct))
        new_value = max(1, new_value)  # không xuống dưới 1đ

        # Đôi khi trend đổi chiều (20% chance mỗi lần update)
        if rng.random() < 0.20:
            trend = rng.uniform(-MV_DRIFT_PER_DAY, MV_DRIFT_PER_DAY)

        data[item_id] = {
            "value": new_value,
            "trend": trend,
            "updated": now,
        }
        updated = True

    if updated:
        _save_market_data(data)
    return data

def get_market_value(item_id: str, purchase_price: int = 0) -> int:
    """
    Lấy giá trị thị trường hiện tại của 1 BĐS.
    Fallback về purchase_price hoặc 0.
    """
    _update_market_values()
    data = _get_market_data()
    mv = data.get(item_id)
    if mv:
        return mv.get("value", purchase_price)
    return purchase_price

def get_all_market_values() -> dict:
    """Trả về {item_id: market_value} — dùng cho UI."""
    _update_market_values()
    return {k: v.get("value", 0) for k, v in _get_market_data().items()}


# ════════════════════════════════════════════════════════════════
#  Renovation / Upgrade
# ════════════════════════════════════════════════════════════════

def _get_upgrades() -> dict:
    """{slot_id: {"level": int, "spent": int, "upgraded_at": float}}"""
    return cfg_dict(_KEY_UPGRADES, {})

def _save_upgrades(data: dict):
    cfg_set(_KEY_UPGRADES, data)

def get_upgrade_info(slot_id: str) -> dict:
    """Trả về thông tin nâng cấp của 1 BĐS."""
    upgrades = _get_upgrades()
    info = upgrades.get(slot_id, {"level": 0, "spent": 0, "upgraded_at": 0})
    current_level = info.get("level", 0)
    maxed = current_level >= MAX_UPGRADE_LEVEL
    portfolio = _get_portfolio()
    prop = next((p for p in portfolio if p["slot_id"] == slot_id), None)
    if not prop:
        return {"level": 0, "max_level": MAX_UPGRADE_LEVEL, "maxed": True,
                "next_cost": 0, "fair_rent_bonus": 0, "value_bonus": 0}
    price = prop.get("price", 1)
    next_level = current_level + 1
    next_cost = int(price * UPGRADE_COST_RATIO * next_level) if not maxed else 0
    fair_rent_bonus = 1.0 + current_level * UPGRADE_RENT_BONUS
    value_bonus = 1.0 + current_level * UPGRADE_VALUE_BONUS
    return {
        "level": current_level,
        "max_level": MAX_UPGRADE_LEVEL,
        "maxed": maxed,
        "total_spent": info.get("spent", 0),
        "next_cost": next_cost,
        "fair_rent_mult": round(fair_rent_bonus, 2),
        "value_mult": round(value_bonus, 2),
        "fair_rent_bonus_pct": int(current_level * UPGRADE_RENT_BONUS * 100),
        "value_bonus_pct": int(current_level * UPGRADE_VALUE_BONUS * 100),
    }

def upgrade_property(slot_id: str) -> dict:
    """
    Nâng cấp BĐS:
      - Kiểm tra tồn tại
      - Kiểm tra max level
      - Trừ tiền
      - Tăng level → cập nhật fair_rent + market_value
    """
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng"}

    portfolio = _get_portfolio()
    prop = next((p for p in portfolio if p["slot_id"] == slot_id), None)
    if not prop:
        return {"ok": False, "error": "Không tìm thấy BĐS"}

    upgrades = _get_upgrades()
    info = upgrades.get(slot_id, {"level": 0, "spent": 0, "upgraded_at": 0})
    current_level = info.get("level", 0)
    if current_level >= MAX_UPGRADE_LEVEL:
        return {"ok": False, "error": f"Đã đạt cấp tối đa ({MAX_UPGRADE_LEVEL})"}

    price = prop.get("price", 1)
    next_level = current_level + 1
    cost = int(price * UPGRADE_COST_RATIO * next_level)

    # Trừ tiền
    from .balance import get_balance, set_balance
    bal = get_balance()
    if bal < cost:
        return {"ok": False, "error": f"Không đủ tiền! Cần {cost:,}đ".replace(",", ".")}
    set_balance(bal - cost)

    # Flush accrued trước khi đổi fair_rent
    _flush_accrued(prop)

    # Cập nhật fair_rent
    original_fair = prop.get("_original_fair_rent", prop["fair_rent"])
    if "_original_fair_rent" not in prop:
        prop["_original_fair_rent"] = prop["fair_rent"]
    new_fair = int(original_fair * (1.0 + next_level * UPGRADE_RENT_BONUS))
    prop["fair_rent"] = new_fair

    # Nếu rent_price đang < fair_rent mới, giữ nguyên (người dùng tự điều chỉnh)
    # Cập nhật upgrade info
    upgrades[slot_id] = {
        "level": next_level,
        "spent": info.get("spent", 0) + cost,
        "upgraded_at": _now(),
    }
    _save_upgrades(upgrades)
    _save_portfolio(portfolio)

    # Ghi giao dịch
    try:
        from .transactions import add_transaction
        add_transaction("re_upgrade", cost,
                        f"🔨 Nâng cấp BĐS {prop.get('name','')} lên cấp {next_level}",
                        {"slot_id": slot_id, "level": next_level, "cost": cost})
    except Exception:
        pass

    return {
        "ok": True,
        "new_level": next_level,
        "cost": cost,
        "new_fair_rent": new_fair,
        "message": f"✅ Nâng cấp BĐS lên cấp {next_level}!",
    }


# ════════════════════════════════════════════════════════════════
#  Satisfaction model
# ════════════════════════════════════════════════════════════════

def calc_satisfaction(rent_price: int, fair_rent: int) -> dict:
    """
    ratio = rent_price / fair_rent
      ≤ 0.6  → 100%  (rất vui, thuê ngay)
      0.6–1.0 → 60–100% (hài lòng)
      1.0–1.4 → 20–60% (chấp nhận được)
      1.4–1.8 → 5–20%  (không vui)
      > 1.8   → 0%     (bỏ đi)
    """
    if fair_rent <= 0:
        return {"pct": 100, "color": "#10b981", "label": "Rất hài lòng", "will_rent": True}

    ratio = rent_price / fair_rent
    if ratio <= 0.6:
        pct = 100
    elif ratio <= 1.0:
        pct = int(60 + (1.0 - ratio) / 0.4 * 40)
    elif ratio <= 1.4:
        pct = int(20 + (1.4 - ratio) / 0.4 * 40)
    elif ratio <= 1.8:
        pct = int(5 + (1.8 - ratio) / 0.4 * 15)
    else:
        pct = 0

    pct = max(0, min(100, pct))
    if pct >= 80:
        color, label = "#10b981", "Rất hài lòng 😊"
        will_rent = True
    elif pct >= 60:
        color, label = "#34d399", "Hài lòng 🙂"
        will_rent = True
    elif pct >= 40:
        color, label = "#f59e0b", "Chấp nhận 😐"
        will_rent = True
    elif pct >= 20:
        color, label = "#f97316", "Không vui 😒"
        will_rent = True
    else:
        color, label = "#ef4444", "Không thuê! 🚫"
        will_rent = False

    return {"pct": pct, "color": color, "label": label, "will_rent": will_rent}


# ════════════════════════════════════════════════════════════════
#  Portfolio API
# ════════════════════════════════════════════════════════════════

def add_property(item_id: str, item_data: dict) -> dict:
    """Thêm BĐS vào portfolio khi mua từ shop."""
    if not col_ready():
        return {"ok": False}
    import uuid as _uuid
    slot_id   = f"re_{item_id}_{str(_uuid.uuid4())[:6]}"
    fair_rent = item_data.get("fair_rent", item_data.get("price", 0) // 200)
    price     = item_data.get("price", 0)
    entry = {
        "slot_id":    slot_id,
        "item_id":    item_id,
        "name":       item_data.get("name", item_id),
        "emoji":      item_data.get("emoji", "🏠"),
        "price":      price,
        "fair_rent":  fair_rent,
        "rent_price": fair_rent,          # mặc định = fair_rent
        "vacant":     False,
        "accrued":    0,                  # tiền chưa collect
        "last_ts":    _now(),
        "total_earned": 0,
        "total_tax":    0,
        "bought_at":  datetime.now().strftime("%d/%m/%Y"),
    }
    portfolio = _get_portfolio()
    portfolio.append(entry)
    _save_portfolio(portfolio)
    return {"ok": True, "slot_id": slot_id}


def set_rent_price(slot_id: str, rent_price: int) -> dict:
    """Cập nhật giá thuê cho một BĐS."""
    portfolio = _get_portfolio()
    prop = next((p for p in portfolio if p["slot_id"] == slot_id), None)
    if not prop:
        return {"ok": False, "error": "Không tìm thấy bất động sản"}
    # Trước khi đổi giá, flush accrued với giá cũ
    _flush_accrued(prop)
    prop["rent_price"] = max(0, int(rent_price))
    sat = calc_satisfaction(prop["rent_price"], prop["fair_rent"])
    prop["vacant"] = not sat["will_rent"]
    _save_portfolio(portfolio)
    return {"ok": True, "satisfaction": sat, "vacant": prop["vacant"]}


def _flush_accrued(prop: dict):
    """Cộng dồn thu nhập từ lần last_ts đến now vào accrued."""
    now  = _now()
    last = float(prop.get("last_ts", now))
    elapsed = now - last
    # Max tích lũy
    elapsed = min(elapsed, MAX_ACCUMULATE_DAYS * SECS_PER_DAY)

    if not prop.get("vacant", False) and prop.get("rent_price", 0) > 0:
        monthly = float(prop["rent_price"])
        per_sec = monthly / SECS_PER_MONTH
        earned  = per_sec * elapsed
        prop["accrued"] = prop.get("accrued", 0) + earned

    prop["last_ts"] = now


def collect_all_rent() -> dict:
    """
    Thu toàn bộ tiền thuê đã tích lũy. Gọi khi:
      - Người dùng bấm "Thu tiền" trong UI
      - profileLoaded (auto-collect)
    Trả về tổng thu nhập, thuế, net.
    """
    if not col_ready():
        return {"ok": False, "total": 0, "tax": 0, "net": 0}

    portfolio = _get_portfolio()
    if not portfolio:
        return {"ok": True, "total": 0, "tax": 0, "net": 0, "count": 0}

    total_gross = 0.0
    for prop in portfolio:
        _flush_accrued(prop)
        total_gross += prop.get("accrued", 0)

    if total_gross < 1:
        _save_portfolio(portfolio)
        return {"ok": True, "total": 0, "tax": 0, "net": 0, "count": 0}

    tax = int(total_gross * RENT_TAX_RATE)
    net = int(total_gross) - tax

    for prop in portfolio:
        prop_share = prop.get("accrued", 0)
        prop_tax   = int(prop_share * RENT_TAX_RATE)
        prop_net   = int(prop_share) - prop_tax
        prop["total_earned"] = prop.get("total_earned", 0) + int(prop_share)
        prop["total_tax"]    = prop.get("total_tax", 0) + prop_tax
        prop["accrued"]      = 0
    _save_portfolio(portfolio)

    from .balance import get_balance, set_balance_and_log
    from .transactions import add_transaction
    new_bal = get_balance() + net
    set_balance_and_log(new_bal, "rent_income", net, f"Thu nhập cho thuê ({len(portfolio)} BĐS)")
    if net > 0:
        add_transaction("rent_income", net, f"🏠 Tiền thuê ({len(portfolio)} BĐS, thuế {RENT_TAX_RATE*100:.0f}%: -{tax:,}đ)".replace(",","."))

    return {"ok": True, "total": int(total_gross), "tax": tax, "net": net,
            "count": len(portfolio)}


def get_portfolio_status() -> list:
    """
    Trả về danh sách BĐS kèm:
      - pending (accrued hiện tại)
      - satisfaction
      - monthly_net
      - market_value (giá trị thị trường hiện tại)
      - value_change (chênh lệch so với giá mua)
      - value_change_pct
      - upgrade_level
      - roi_pct
    """
    portfolio = _get_portfolio()
    _update_market_values()
    market_data = _get_market_data()
    upgrades = _get_upgrades()
    result = []
    now = _now()

    for prop in portfolio:
        item_id = prop.get("item_id", "")
        price   = prop.get("price", 0)

        # Pending rent
        last = float(prop.get("last_ts", now))
        elapsed = min(now - last, MAX_ACCUMULATE_DAYS * SECS_PER_DAY)
        if not prop.get("vacant") and prop.get("rent_price", 0) > 0:
            per_sec = float(prop["rent_price"]) / SECS_PER_MONTH
            pending = prop.get("accrued", 0) + per_sec * elapsed
        else:
            pending = prop.get("accrued", 0)

        # Market value
        mv_entry = market_data.get(item_id)
        if mv_entry:
            base_market_value = mv_entry.get("value", price)
        else:
            base_market_value = price

        # Upgrade bonus on value
        upg_info = upgrades.get(prop["slot_id"], {"level": 0})
        upg_level = upg_info.get("level", 0)
        value_mult = 1.0 + upg_level * UPGRADE_VALUE_BONUS
        market_value = int(base_market_value * value_mult)

        value_change = market_value - price
        value_change_pct = round((value_change / price) * 100, 1) if price > 0 else 0.0

        # ROI: (total_earned - total_tax + value_change) / price * 100
        total_earned = prop.get("total_earned", 0)
        total_tax = prop.get("total_tax", 0)
        net_earned = total_earned - total_tax
        # Thêm pending (chưa thu)
        net_earned += int(pending) - int(pending * RENT_TAX_RATE)
        roi = ((net_earned + max(0, value_change)) / price * 100) if price > 0 else 0.0

        sat = calc_satisfaction(prop["rent_price"], prop["fair_rent"])
        result.append({
            **prop,
            "pending":         int(pending),
            "satisfaction":    sat,
            "monthly_net":     int(prop.get("rent_price", 0) * (1 - RENT_TAX_RATE)),
            "market_value":    market_value,
            "value_change":    value_change,
            "value_change_pct": value_change_pct,
            "upgrade_level":   upg_level,
            "roi_pct":         round(roi, 1),
        })
    return result


def remove_property(slot_id: str) -> dict:
    """
    Bán BĐS theo giá thị trường hiện tại (thay vì 50% cố định).
    - Phải collect hết tiền thuê trước khi bán.
    """
    if not col_ready():
        return {"ok": False}
    portfolio = _get_portfolio()
    prop = next((p for p in portfolio if p["slot_id"] == slot_id), None)
    if not prop:
        return {"ok": False, "error": "Không tìm thấy"}

    # Flush accrued trước
    _flush_accrued(prop)

    # Kiểm tra còn accrued không (phải collect trước)
    if prop.get("accrued", 0) > 1000:
        return {"ok": False, "error": "Hãy thu tiền thuê trước khi bán!"}

    # Tính giá bán theo thị trường
    item_id = prop.get("item_id", "")
    purchase_price = prop.get("price", 0)
    upgrades = _get_upgrades()
    upg_info = upgrades.get(slot_id, {"level": 0})
    upg_level = upg_info.get("level", 0)
    value_mult = 1.0 + upg_level * UPGRADE_VALUE_BONUS

    base_mv = get_market_value(item_id, purchase_price)
    sell_price = int(base_mv * value_mult)

    # Phí môi giới 5%
    fee = int(sell_price * 0.05)
    net_sell = sell_price - fee

    # Cộng tiền
    from .balance import get_balance, set_balance_and_log
    from .transactions import add_transaction
    new_bal = get_balance() + net_sell
    set_balance_and_log(new_bal, "re_sale", net_sell,
                        f"Bán {prop.get('name','')} giá {sell_price:,}đ (phí {fee:,}đ)".replace(",", "."))
    add_transaction("re_sale", net_sell,
                    f"🏚️ Bán {prop.get('name','')}: {sell_price:,}đ - phí {fee:,}đ".replace(",", "."),
                    {"slot_id": slot_id, "item_id": item_id, "sell_price": sell_price, "fee": fee})

    # Xoá khỏi portfolio
    new_p = [p for p in portfolio if p["slot_id"] != slot_id]
    _save_portfolio(new_p)

    # Xoá upgrade data
    all_upgrades = _get_upgrades()
    if slot_id in all_upgrades:
        del all_upgrades[slot_id]
        _save_upgrades(all_upgrades)

    return {"ok": True, "sell_price": sell_price, "fee": fee, "net": net_sell,
            "message": f"✅ Đã bán {prop.get('name','')} — Thu về {net_sell:,}đ".replace(",", ".")}


def get_total_monthly_income() -> int:
    """Ước tính thu nhập tháng từ toàn bộ BĐS."""
    return sum(
        int(p.get("rent_price", 0) * (1 - RENT_TAX_RATE))
        for p in _get_portfolio()
        if not p.get("vacant")
    )


def get_re_summary() -> dict:
    """
    Tổng quan đầu tư BĐS:
      - total_invested (tổng tiền mua)
      - total_market_value (tổng giá trị thị trường)
      - unrealized_pnl (lời/lỗ chưa bán)
      - total_pending_rent (tiền thuê chờ thu)
      - total_earned (tổng đã thu)
      - count (số BĐS)
      - avg_roi_pct (ROI trung bình)
    """
    result = get_portfolio_status()
    total_invested = sum(p.get("price", 0) for p in result)
    total_mv = sum(p.get("market_value", 0) for p in result)
    total_pending = sum(p.get("pending", 0) for p in result)
    total_earned = sum(p.get("total_earned", 0) - p.get("total_tax", 0) for p in result)
    count = len(result)
    unrealized_pnl = total_mv - total_invested
    avg_roi = round((total_earned + max(0, unrealized_pnl)) / max(total_invested, 1) * 100, 1)

    return {
        "total_invested": total_invested,
        "total_market_value": total_mv,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": round((unrealized_pnl / max(total_invested, 1)) * 100, 1),
        "total_pending_rent": total_pending,
        "total_earned": total_earned,
        "count": count,
        "avg_roi_pct": avg_roi,
        "total_monthly_income": get_total_monthly_income(),
    }
