# -*- coding: utf-8 -*-
from __future__ import annotations
"""
housing_residence.py — Nơi ở của người chơi.

Tách biệt hoàn toàn với real_estate.py (BĐS đầu tư cho thuê).
Người chơi luôn có một nơi ở; chi phí sinh hoạt phụ thuộc loại nhà.

Upgrade path:
  room_basic → room_ktx → apartment_mini → apartment_std
  apartment_std → townhouse (mua đứt) → villa (mua đứt)
"""

from ._safe_config import col_ready, cfg_dict, cfg_set

_KEY_RESIDENCE = "anki_tycoon_residence"
_KEY_INITIALIZED = "anki_tycoon_initialized"

# ── Danh sách nơi ở ────────────────────────────────────────────────
RESIDENCES = {
    "room_basic": {
        "id":            "room_basic",
        "name":          "Nhà trọ cơ bản",
        "emoji":         "🏠",
        "desc":          "Phòng trọ nhỏ, đủ để ở qua ngày",
        "type":          "rent",
        "monthly_rent":  0,           # Miễn phí (nhà ban đầu)
        "purchase_price": 0,
        "utilities_base": 200_000,    # Điện + nước base/tháng
        "food_monthly":   1_500_000,  # Ăn uống cơ bản/tháng
        "internet_monthly": 150_000,  # Internet/tháng
        "unlock_balance": 0,
    },
    "room_ktx": {
        "id":            "room_ktx",
        "name":          "Phòng ký túc xá",
        "emoji":         "🏫",
        "desc":          "Phòng KTX, chia sẻ tiện nghi, giá rẻ",
        "type":          "rent",
        "monthly_rent":  1_500_000,
        "purchase_price": 0,
        "utilities_base": 150_000,
        "food_monthly":   1_500_000,
        "internet_monthly": 100_000,
        "unlock_balance": 5_000_000,
    },
    "apartment_mini": {
        "id":            "apartment_mini",
        "name":          "Chung cư mini",
        "emoji":         "🏢",
        "desc":          "Căn hộ mini, đầy đủ tiện nghi cơ bản",
        "type":          "rent",
        "monthly_rent":  4_000_000,
        "purchase_price": 0,
        "utilities_base": 350_000,
        "food_monthly":   2_500_000,
        "internet_monthly": 200_000,
        "unlock_balance": 20_000_000,
    },
    "apartment_std": {
        "id":            "apartment_std",
        "name":          "Chung cư tiêu chuẩn",
        "emoji":         "🏙️",
        "desc":          "Căn hộ 2PN, khu dân cư tiện ích đầy đủ",
        "type":          "rent",
        "monthly_rent":  8_000_000,
        "purchase_price": 2_000_000_000,  # Có thể mua đứt
        "utilities_base": 500_000,
        "food_monthly":   4_000_000,
        "internet_monthly": 250_000,
        "unlock_balance": 50_000_000,
    },
    "townhouse": {
        "id":            "townhouse",
        "name":          "Nhà phố",
        "emoji":         "🏘️",
        "desc":          "Nhà phố 3 tầng, khu trung tâm",
        "type":          "buy",
        "monthly_rent":  0,
        "purchase_price": 4_000_000_000,
        "utilities_base": 800_000,
        "food_monthly":   6_000_000,
        "internet_monthly": 300_000,
        "land_tax_rate":  0.0003,     # 0.03%/năm
        "unlock_balance": 1_000_000_000,
    },
    "villa": {
        "id":            "villa",
        "name":          "Biệt thự",
        "emoji":         "🏰",
        "desc":          "Biệt thự compound, hồ bơi riêng, sân vườn",
        "type":          "buy",
        "monthly_rent":  0,
        "purchase_price": 12_000_000_000,
        "utilities_base": 1_500_000,
        "food_monthly":   8_000_000,
        "internet_monthly": 500_000,
        "land_tax_rate":  0.0003,
        "unlock_balance": 5_000_000_000,
    },
}

_DEFAULT_RESIDENCE = {
    "id":             "room_basic",
    "type":           "rent",
    "purchase_price": 0,
    "bought_at":      None,
}


def _get_raw() -> dict:
    return cfg_dict(_KEY_RESIDENCE, _DEFAULT_RESIDENCE)


def get_residence() -> dict:
    """Trả về nơi ở hiện tại kèm thông tin từ RESIDENCES."""
    raw = _get_raw()
    rid = raw.get("id", "room_basic")
    info = RESIDENCES.get(rid, RESIDENCES["room_basic"]).copy()
    info["bought_at"]      = raw.get("bought_at")
    info["purchase_price"] = raw.get("purchase_price", info["purchase_price"])
    return info


def get_monthly_fixed_costs(residence: dict | None = None) -> dict:
    """
    Trả về chi phí cố định hàng tháng (không tính điện/nước biến đổi).
    """
    if residence is None:
        residence = get_residence()
    return {
        "rent":     residence.get("monthly_rent", 0),
        "food":     residence.get("food_monthly", 0),
        "internet": residence.get("internet_monthly", 0),
    }


def get_utilities_daily(cards_yesterday: int, residence: dict | None = None) -> int:
    """
    Điện + nước hàng ngày = base/30 * multiplier(thẻ hôm qua).
    """
    if residence is None:
        residence = get_residence()
    base_monthly = residence.get("utilities_base", 200_000)
    base_daily   = base_monthly / 30.0

    if cards_yesterday == 0:
        mult = 2.0
    elif cards_yesterday <= 20:
        mult = 1.5
    elif cards_yesterday <= 50:
        mult = 1.2
    elif cards_yesterday <= 100:
        mult = 1.0
    else:
        mult = 0.7

    return round(base_daily * mult)


def get_monthly_land_tax(residence: dict | None = None) -> int:
    """Thuế đất hàng tháng cho nhà mua đứt (0 nếu đang thuê)."""
    if residence is None:
        residence = get_residence()
    if residence.get("type") != "buy":
        return 0
    rate = residence.get("land_tax_rate", 0.0003)
    value = residence.get("purchase_price", 0)
    return round(value * rate / 12)


def get_all_residences_for_ui() -> list:
    """Danh sách nơi ở cho UI chọn."""
    current = get_residence()
    out = []
    for rid, info in RESIDENCES.items():
        entry = info.copy()
        entry["is_current"] = (rid == current["id"])
        entry["monthly_total"] = (
            info["monthly_rent"]
            + info["food_monthly"]
            + info["internet_monthly"]
            + info["utilities_base"]
        )
        out.append(entry)
    return out


def change_residence(new_id: str, force_buy: bool = False) -> dict:
    """
    Chuyển nơi ở. Nếu type='buy' phải có đủ balance.
    force_buy=True để thực sự trừ tiền mua nhà.
    Trả về {"ok", "error"?, "cost"?}
    """
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}
    if new_id not in RESIDENCES:
        return {"ok": False, "error": "Nơi ở không hợp lệ."}

    info = RESIDENCES[new_id]
    cost = 0

    if info["type"] == "buy":
        cost = info["purchase_price"]
        if force_buy:
            from .balance import get_balance, set_balance
            from .transactions import add_transaction
            bal = get_balance()
            if bal < cost:
                return {"ok": False, "error": f"Không đủ tiền. Cần {cost:,}đ.".replace(",",".")}
            set_balance(bal - cost)
            add_transaction("purchase", cost, f"Mua nhà: {info['name']}")
        # Nếu không force_buy (chỉ xem), return thông tin để confirm

    import time
    cfg_set(_KEY_RESIDENCE, {
        "id":             new_id,
        "type":           info["type"],
        "purchase_price": cost if info["type"] == "buy" else 0,
        "bought_at":      time.strftime("%Y-%m-%d", time.localtime(time.time())) if info["type"] == "buy" and force_buy else None,
    })
    return {"ok": True, "new_id": new_id, "cost": cost}


def sell_residence() -> dict:
    """Bán nhà đang ở (chỉ nhà mua đứt) → chuyển về room_basic."""
    res = get_residence()
    if res.get("type") != "buy":
        return {"ok": False, "error": "Chỉ bán được nhà mua đứt."}

    sell_price = res.get("purchase_price", 0)
    if sell_price <= 0:
        return {"ok": False, "error": "Không có giá trị để bán."}

    from .balance import get_balance, set_balance
    from .transactions import add_transaction
    set_balance(get_balance() + sell_price)
    add_transaction("rent_income", sell_price, f"Bán nhà ở: {res['name']}")

    cfg_set(_KEY_RESIDENCE, {**_DEFAULT_RESIDENCE})
    return {"ok": True, "received": sell_price}


def ensure_initialized() -> bool:
    """Khởi tạo người chơi mới: 10 triệu VND + nhà trọ cơ bản."""
    if not col_ready():
        return False
    from ._safe_config import cfg_dict
    raw = cfg_dict(_KEY_INITIALIZED, {})
    if raw.get("done"):
        return False  # Đã init rồi

    from .balance import get_balance, set_balance
    if get_balance() == 0:
        set_balance(10_000_000)

    cfg_set(_KEY_RESIDENCE, {**_DEFAULT_RESIDENCE})
    cfg_set(_KEY_INITIALIZED, {"done": True})
    return True
