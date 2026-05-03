# -*- coding: utf-8 -*-

import json
import os
import time

# ── In-memory cache cho shop items ──────────────────────────────
# Tránh đọc file JSON từ disk mỗi lần gọi (có thể 5-10 lần/tab)
_shop_cache = None
_shop_cache_ts = 0.0
_SHOP_CACHE_TTL = 60.0  # Cache 60 giây, đủ cho 1 phiên làm việc


def load_shop_items(force_reload: bool = False) -> list:
    """Load shop items từ JSON, có cache trong memory.
    
    Args:
        force_reload: Bỏ qua cache, load lại từ disk.
    """
    global _shop_cache, _shop_cache_ts
    now = time.time()
    if not force_reload and _shop_cache is not None and (now - _shop_cache_ts) < _SHOP_CACHE_TTL:
        return _shop_cache

    addon_dir = os.path.dirname(__file__)  # root addon
    json_path = os.path.join(addon_dir, "shop_items.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            _shop_cache = json.load(f)
            _shop_cache_ts = now
            return _shop_cache
    except Exception:
        result = _default_items()
        _shop_cache = result
        _shop_cache_ts = now
        return result


def get_item(item_id: str) -> dict | None:
    """Lấy 1 item từ shop theo id, không cần load lại toàn bộ."""
    items = load_shop_items()
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def get_items_map() -> dict:
    """Trả về dict {item_id: item} để tra cứu nhanh."""
    items = load_shop_items()
    return {i["id"]: i for i in items}


def _default_items() -> list:
    return [
        {"id": "coffee",        "name": "Cà phê Starbucks",    "description": "Uống để tỉnh học bài",            "category": "Đồ ăn uống",  "price": 85000,         "emoji": "☕"},
        {"id": "boba",          "name": "Trà sữa Gong Cha",    "description": "Topping đầy đủ, size L",           "category": "Đồ ăn uống",  "price": 65000,         "emoji": "🧋"},
        {"id": "airpods",       "name": "AirPods Pro 2",       "description": "Chống ồn chủ động thế hệ 2",      "category": "Điện tử",     "price": 6000000,       "emoji": "🎧"},
        {"id": "ps5",           "name": "PlayStation 5",       "description": "Console thế hệ mới của Sony",     "category": "Điện tử",     "price": 15000000,      "emoji": "🎮"},
        {"id": "iphone16",      "name": "iPhone 16 Pro Max",   "description": "8GB RAM / 256GB — Titanium Black", "category": "Điện tử",     "price": 40000000,      "emoji": "📱"},
        {"id": "macbook_m3",    "name": "MacBook Pro M3",      "description": "16GB RAM / 512GB SSD",            "category": "Điện tử",     "price": 45000000,      "emoji": "💻"},
        {"id": "vacation_dalat","name": "Du lịch Đà Lạt",      "description": "Gói 3N2Đ, khách sạn 4 sao",      "category": "Du lịch",     "price": 3000000,       "emoji": "🌸"},
        {"id": "vacation_bali", "name": "Du lịch Bali",        "description": "Gói 5N4Đ, villa riêng",           "category": "Du lịch",     "price": 25000000,      "emoji": "🏝️"},
        {"id": "honda_civic",   "name": "Honda Civic 2024",    "description": "Sedan hạng C, 1.5L Turbo",        "category": "Xe cộ",       "price": 800000000,     "emoji": "🚗"},
        {"id": "tesla_model3",  "name": "Tesla Model 3",       "description": "Xe điện, phạm vi 570km",          "category": "Xe cộ",       "price": 1500000000,    "emoji": "⚡"},
        {"id": "rolex",         "name": "Rolex Submariner",    "description": "Đồng hồ luxury huyền thoại",      "category": "Xa xỉ phẩm", "price": 400000000,     "emoji": "⌚"},
        {"id": "lamborghini",   "name": "Lamborghini Huracán", "description": "Siêu xe V10, 630 mã lực",         "category": "Xe cộ",       "price": 15000000000,   "emoji": "🏎️"},
    ]
