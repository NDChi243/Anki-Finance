# -*- coding: utf-8 -*-
"""
energy_system.py — Hệ thống năng lượng học tập.

Cơ chế:
  - Mỗi thẻ review tiêu hao 1 năng lượng
  - Nếu hết năng lượng: tiền thưởng giảm 50%
  - Food/study items có thể hồi năng lượng (stamina_regen)
  - Equipment tăng giới hạn năng lượng tối đa (energy_limit)
  - Năng lượng hồi phục tự nhiên 1 điểm mỗi 1 phút
"""

import time
from ._safe_config import col_ready, cfg_int, cfg_set
from .logger import get_logger
logger = get_logger(__name__)

_KEY_ENERGY       = "anki_tycoon_energy"
_KEY_MAX_ENERGY   = "anki_tycoon_max_energy_base"
_KEY_LAST_REGEN   = "anki_tycoon_energy_last_regen"

BASE_MAX_ENERGY = 100
REGEN_INTERVAL  = 60  # 1 phút hồi 1 điểm

# Keys được bảo vệ khỏi debug_tools scan — tránh bị clear type
_PROTECTED_KEYS = {_KEY_ENERGY, _KEY_MAX_ENERGY, _KEY_LAST_REGEN}


def _get_passive_effects():
    """Lazy load passive effects để tránh circular import."""
    try:
        from .item_effects import get_all_passive_effects
        return get_all_passive_effects()
    except Exception as e:
        logger.debug("_get_passive_effects: %s", e)
        return {}


def get_current_energy() -> int:
    """Lấy năng lượng hiện tại, tự động hồi nếu đã đến hạn."""
    if not col_ready():
        return BASE_MAX_ENERGY
    _auto_regen()
    return cfg_int(_KEY_ENERGY, BASE_MAX_ENERGY)


def get_max_energy() -> int:
    """
    Tính max energy = base (100) + bonus từ passive effects.
    energy_limit từ passive items cộng dồn.
    review_count_bonus được quy đổi thành sức học thêm trong ngày.
    """
    base = cfg_int(_KEY_MAX_ENERGY, BASE_MAX_ENERGY)
    passive = _get_passive_effects()
    bonus = int(passive.get("energy_limit", 0)) + int(passive.get("review_count_bonus", 0))
    return base + bonus


def set_max_energy(val: int):
    """Set base max energy (dùng khi reset)."""
    cfg_set(_KEY_MAX_ENERGY, max(BASE_MAX_ENERGY, int(val)))


def consume_energy(amount: int = 1) -> int:
    """
    Tiêu hao năng lượng khi review thẻ.
    Trả về năng lượng còn lại.
    """
    if not col_ready():
        return BASE_MAX_ENERGY
    _auto_regen()
    current = cfg_int(_KEY_ENERGY, BASE_MAX_ENERGY)
    current = max(0, current - amount)
    cfg_set(_KEY_ENERGY, current)
    return current


def consume_energy_with_vehicle(amount: int = 1, vehicle_energy_save: float = 0.0) -> dict:
    """
    Tiêu hao năng lượng khi review thẻ, có tính % tiết kiệm từ xe.
    
    Args:
        amount: Lượng năng lượng cơ bản tiêu hao (mặc định 1)
        vehicle_energy_save: % tiết kiệm từ xe (0.0 = 0%, 0.30 = 30%)
    
    Returns:
        {"energy_left": int, "actual_consumed": float, "saved": float, "save_percent": float}
    """
    if not col_ready():
        return {"energy_left": BASE_MAX_ENERGY, "actual_consumed": amount, "saved": 0.0, "save_percent": 0.0}
    
    # Tính lượng năng lượng thực tế tiêu hao sau khi trừ % tiết kiệm
    save_pct = max(0.0, min(1.0, vehicle_energy_save))
    saved = amount * save_pct
    actual_consumed = max(0.0, amount - saved)
    
    _auto_regen()
    current = cfg_int(_KEY_ENERGY, BASE_MAX_ENERGY)
    current = max(0, int(current - actual_consumed))
    cfg_set(_KEY_ENERGY, current)
    
    return {
        "energy_left": current,
        "actual_consumed": round(actual_consumed, 2),
        "saved": round(saved, 2),
        "save_percent": round(save_pct * 100, 1),
    }


def restore_energy(amount: int) -> int:
    """
    Hồi năng lượng từ food/stamina_regen.
    Trả về năng lượng sau khi hồi.
    """
    if not col_ready():
        return BASE_MAX_ENERGY
    current = get_current_energy()
    max_eng = get_max_energy()
    current = min(max_eng, current + amount)
    cfg_set(_KEY_ENERGY, current)
    return current


def is_exhausted() -> bool:
    """Kiểm tra có kiệt sức không (năng lượng = 0)."""
    return get_current_energy() <= 0


def get_energy_percent() -> float:
    """Trả về % năng lượng còn lại (0.0 - 1.0)."""
    max_eng = get_max_energy()
    if max_eng <= 0:
        return 0.0
    return min(1.0, get_current_energy() / max_eng)


def get_reward_multiplier_from_energy() -> float:
    """
    Trả về hệ số nhân thưởng dựa trên năng lượng:
    - Năng lượng > 0: ×1.0 (bình thường)
    - Năng lượng = 0: ×0.5 (kiệt sức, học kém hiệu quả)
    """
    if is_exhausted():
        return 0.5
    return 1.0


def reset_energy():
    """Reset năng lượng về đầy (dùng cho reset game)."""
    if not col_ready():
        return
    max_eng = get_max_energy()
    cfg_set(_KEY_ENERGY, max_eng)
    cfg_set(_KEY_LAST_REGEN, time.time())


def _auto_regen():
    """Tự động hồi năng lượng theo thời gian (1 điểm/30 phút)."""
    try:
        raw = cfg_int(_KEY_LAST_REGEN, 0)
        # Nếu raw là 0 hoặc None (do lỗi debug_tools cũ clear mất),
        # coi như lần đầu — set mốc thời gian và hồi đầy năng lượng
        if not raw or raw <= 0:
            now = time.time()
            cfg_set(_KEY_LAST_REGEN, now)
            # Phục hồi năng lượng về đầy nếu đang bị 0 (fix cho user đã bị lỗi)
            current = cfg_int(_KEY_ENERGY, BASE_MAX_ENERGY)
            if current <= 0:
                max_eng = get_max_energy()
                cfg_set(_KEY_ENERGY, max_eng)
            return

        last = float(raw)
        now = time.time()
        elapsed = now - last
        if elapsed < REGEN_INTERVAL:
            return

        points_to_regen = int(elapsed // REGEN_INTERVAL)
        current = cfg_int(_KEY_ENERGY, BASE_MAX_ENERGY)
        max_eng = get_max_energy()
        current = min(max_eng, current + points_to_regen)
        cfg_set(_KEY_ENERGY, current)

        # Cập nhật mốc thời gian — chỉ lưu khi đã hồi xong
        new_last = last + (points_to_regen * REGEN_INTERVAL)
        cfg_set(_KEY_LAST_REGEN, new_last)
    except Exception as e:
        logger.warning("_auto_regen: %s", e)


def get_energy_status() -> dict:
    """Trả về trạng thái năng lượng đầy đủ cho UI."""
    current = get_current_energy()
    max_eng = get_max_energy()
    pct = (current / max_eng * 100) if max_eng > 0 else 0
    return {
        "current": current,
        "max": max_eng,
        "percent": round(pct, 1),
        "exhausted": current <= 0,
        "multiplier": get_reward_multiplier_from_energy(),
    }
