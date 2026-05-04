# -*- coding: utf-8 -*-
"""
vehicle_effects.py — Hiệu ứng xe cộ & tích hợp năng lượng (v1.1.5b)
===============================================================
Cung cấp các hàm truy vấn nhanh cho:
  - % tiết kiệm năng lượng khi học thẻ
  - Số km đã đi
  - Thông tin tốc độ học (hệ số nhân nhiên liệu)
"""

from .logger import get_logger
logger = get_logger(__name__)


def get_active_vehicle_energy_save() -> float:
    """
    Trả về % năng lượng tiết kiệm (0.0 - 0.30) của xe đang active.
    0.0 nếu không có xe active hoặc xe không có tính năng tiết kiệm.
    """
    try:
        from .vehicle_system import get_active_vehicle
        av = get_active_vehicle()
        if not av:
            return 0.0
        return float(av.get("energy_save_percent", 0.0))
    except Exception as e:
        logger.debug("get_active_vehicle_energy_save: %s", e)
        return 0.0


def get_active_vehicle_km() -> float:
    """
    Trả về số km xe đang active đã đi (10 thẻ = 1km).
    """
    try:
        from .vehicle_system import get_active_vehicle
        av = get_active_vehicle()
        if not av:
            return 0.0
        return float(av.get("km_traveled", 0.0))
    except Exception as e:
        logger.debug("get_active_vehicle_km: %s", e)
        return 0.0


def get_active_vehicle_total_cards() -> int:
    """
    Trả về tổng số thẻ đã học khi lái xe đang active.
    """
    try:
        from .vehicle_system import get_active_vehicle
        av = get_active_vehicle()
        if not av:
            return 0
        return int(av.get("total_cards_driven", 0))
    except Exception as e:
        logger.debug("get_active_vehicle_total_cards: %s", e)
        return 0


def get_active_vehicle_speed_multiplier(elapsed_seconds: float = None) -> float:
    """
    Tính hệ số nhân nhiên liệu dựa trên tốc độ học hiện tại.
    elapsed_seconds: thời gian học thẻ (giây). Nếu None, trả về 1.0.
    """
    if elapsed_seconds is None or elapsed_seconds <= 0:
        return 1.0
    try:
        from .vehicle_system import _calc_speed_fuel_multiplier
        return _calc_speed_fuel_multiplier(elapsed_seconds)
    except Exception as e:
        logger.debug("get_active_vehicle_speed_multiplier: %s", e)
        return 1.0


def get_vehicle_save_info(item_id: str) -> dict:
    """
    Trả về thông tin tiết kiệm năng lượng và KM cho 1 xe cụ thể.
    """
    try:
        from .vehicle_system import get_vehicle_info
        info = get_vehicle_info(item_id)
        if not info:
            return {}
        return {
            "km_traveled": float(info.get("km_traveled", 0.0)),
            "energy_save_percent": float(info.get("energy_save_percent", 0.0)),
            "total_cards_driven": int(info.get("total_cards_driven", 0)),
            "is_active": info.get("is_active", False),
        }
    except Exception as e:
        logger.debug("get_vehicle_save_info: %s", e)
        return {}


def calc_effective_energy_cost(base_cost: int = 1) -> dict:
    """
    Tính chi phí năng lượng thực tế sau khi áp dụng tiết kiệm từ xe.
    Trả về: {"base": int, "save_percent": float, "saved": float, "actual": float}
    """
    save_pct = get_active_vehicle_energy_save()
    saved = base_cost * save_pct
    actual = max(0.0, base_cost - saved)
    return {
        "base": base_cost,
        "save_percent": round(save_pct * 100, 1),
        "saved": round(saved, 2),
        "actual": round(actual, 2),
    }
