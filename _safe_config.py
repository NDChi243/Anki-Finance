# -*- coding: utf-8 -*-
from __future__ import annotations
"""
_safe_config.py — helpers chống lỗi None khi đọc config.
Dùng chung cho tất cả module khác.

Tối ưu hiệu suất:
  - cache_read: cache trong memory các giá trị đã đọc, tránh gọi mw.col.get_config()
    liên tục. Cache tự động invalidate sau cfg_set().
  - batch_cfg_set: Gom nhiều cfg_set vào 1 lần save duy nhất.
"""

from aqt import mw
import time
import copy

from .logger import get_logger

logger = get_logger(__name__)

# ── In-memory cache ──────────────────────────────────────────────
_config_cache = {}       # {key: (value, timestamp)}
_cache_ttl = 10.0        # Thời gian sống của cache (giây) — tăng từ 2s lên 10s để giảm I/O
_cache_enabled = True    # Có thể tắt cache nếu debug

# Keys đặc biệt cần cache dài hơn (ít thay đổi)
_LONG_CACHE_KEYS = {
    "anki_tycoon_balance",
    "anki_tycoon_stats",
    "anki_tycoon_budget",
    "anki_tycoon_daily_again_count",
    "anki_tycoon_daily_again_date",
    "anki_tycoon_passive_effects",
    "anki_tycoon_vehicle_data",
    "anki_tycoon_re_portfolio",
    "anki_tycoon_stocks_market",
    "anki_tycoon_crypto_market",
}


def _cache_get(key: str):
    """Lấy giá trị từ cache nếu còn hạn."""
    if not _cache_enabled:
        return None
    entry = _config_cache.get(key)
    if entry is None:
        return None
    val, ts = entry
    ttl = _cache_ttl * 5 if key in _LONG_CACHE_KEYS else _cache_ttl
    if time.time() - ts < ttl:
        return val
    # Hết hạn — xoá khỏi cache
    del _config_cache[key]
    return None


def _cache_set(key: str, val):
    """Lưu giá trị vào cache."""
    if _cache_enabled:
        _config_cache[key] = (val, time.time())


def _cache_invalidate(key: str = None):
    """Invalidate 1 key hoặc toàn bộ cache."""
    if key:
        _config_cache.pop(key, None)
    else:
        _config_cache.clear()


def set_cache_enabled(enabled: bool):
    """Bật/tắt cache (dùng cho debug)."""
    global _cache_enabled
    _cache_enabled = enabled
    if not enabled:
        _cache_invalidate()


# ── Helpers ──────────────────────────────────────────────────────

def col_ready() -> bool:
    try:
        return mw is not None and mw.col is not None
    except Exception as e:
        logger.debug("col_ready: %s", e)
        return False


def cfg_int(key: str, default: int = 0) -> int:
    # Kiểm tra cache trước
    cached = _cache_get(key)
    if cached is not None:
        # ⚠️ Chống TypeError: nếu cached là list/dict (vd: anki_tycoon_knowledge),
        # không thể int() — invalidate cache và fallthrough xuống mw.col
        if isinstance(cached, (int, float)):
            return int(cached)
        if isinstance(cached, str):
            try:
                return int(cached)
            except (ValueError, TypeError):
                logger.debug("cfg_int: cached string '%s' not int for key '%s'", cached, key)
        # Cache bị lỗi kiểu — xoá cache và đọc lại từ config
        _cache_invalidate(key)

    if not col_ready():
        return default
    try:
        v = mw.col.get_config(key, default)
        if v is None:
            return default
        # ⚠️ Kiểm tra kiểu dữ liệu từ Anki config trước khi int()
        if isinstance(v, (int, float)):
            result = int(v)
        elif isinstance(v, str):
            try:
                result = int(v)
            except (ValueError, TypeError):
                logger.debug("cfg_int: config value '%s' not int for key '%s'", v, key)
                return default
        else:
            return default
        _cache_set(key, result)
        return result
    except Exception as e:
        logger.warning("cfg_int(%s): %s", key, e)
        return default


def cfg_str(key: str, default: str = "") -> str:
    cached = _cache_get(key)
    if cached is not None:
        return str(cached)

    if not col_ready():
        return default
    try:
        v = mw.col.get_config(key, default)
        result = str(v) if v is not None else default
        _cache_set(key, result)
        return result
    except Exception as e:
        logger.warning("cfg_str(%s): %s", key, e)
        return default


def cfg_list(key: str, default: list | None = None) -> list:
    if default is None:
        default = []
    cached = _cache_get(key)
    if cached is not None:
        if isinstance(cached, (list, tuple)):
            return list(cached)
        # Cache bị lỗi kiểu dữ liệu (corrupted) — bỏ qua
        _cache_invalidate(key)

    if not col_ready():
        return list(default)
    try:
        v = mw.col.get_config(key, default)
        result = v if isinstance(v, list) else list(default)
        _cache_set(key, result)
        return result
    except Exception as e:
        logger.warning("cfg_list(%s): %s", key, e)
        return list(default)


def cfg_dict(key: str, default: dict | None = None) -> dict:
    if default is None:
        default = {}
    cached = _cache_get(key)
    if cached is not None:
        if isinstance(cached, dict):
            if key == "anki_tycoon_vehicle_data":
                garage_size = len(cached.get("garage", {}))
                logger.debug("cfg_dict(%s): HIT cache — garage có %d xe", key, garage_size)
            # ⚠️ Dùng deepcopy để tránh shared mutable state giữa cache và caller.
            # Nếu dùng dict(cached) (shallow copy), các dict con (garage, maintenance_due, ...)
            # vẫn là cùng object với cache → mọi thay đổi từ caller sẽ làm corrupt cache.
            return copy.deepcopy(cached)
        # Cache bị lỗi kiểu dữ liệu (corrupted) — bỏ qua
        logger.warning("cfg_dict(%s): cache corrupted (type=%s), bỏ qua", key, type(cached).__name__)
        _cache_invalidate(key)

    if not col_ready():
        logger.warning("cfg_dict(%s): col_ready() == False, trả về default", key)
        return dict(default)
    try:
        v = mw.col.get_config(key, default)
        result = v if isinstance(v, dict) else dict(default)
        if key == "anki_tycoon_vehicle_data":
            garage_size = len(result.get("garage", {}))
            logger.debug("cfg_dict(%s): MISS cache — đọc từ Anki config, garage có %d xe, v=%s", key, garage_size, type(v).__name__)
        _cache_set(key, result)
        # ⚠️ Deepcopy để caller không làm corrupt cache khi modify result
        return copy.deepcopy(result)
    except Exception as e:
        logger.warning("cfg_dict(%s): %s", key, e)
        return dict(default)


# ── Batch write support ─────────────────────────────────────────
# Cho phép gom nhiều cfg_set() thành 1 lần ghi duy nhất
_batch_writes = {}       # {key: value} — gom khi đang trong batch mode
_batch_active = False


def begin_batch():
    """Bắt đầu batch mode — các cfg_set sẽ được gom lại."""
    global _batch_active, _batch_writes
    _batch_active = True
    _batch_writes = {}


def commit_batch():
    """Kết thúc batch mode và ghi tất cả config một lần."""
    global _batch_active, _batch_writes
    _batch_active = False
    if not col_ready() or not _batch_writes:
        _batch_writes = {}
        return
    try:
        for key, val in _batch_writes.items():
            _raw_set(key, val)
    except Exception as e:
        logger.warning("commit_batch: %s", e)
    _batch_writes = {}


def discard_batch():
    """Huỷ batch — không ghi gì cả."""
    global _batch_active, _batch_writes
    _batch_active = False
    _batch_writes = {}


def _raw_set(key: str, val):
    """Ghi trực tiếp xuống Anki config, bỏ qua cache."""
    try:
        mw.col.set_config(key, val)
        _cache_set(key, val)
    except Exception as e:
        logger.warning("_raw_set(%s): %s", key, e)


def cfg_set(key: str, val):
    """Ghi config — nếu đang trong batch mode thì gom lại."""
    # Invalidate cache trước
    _cache_invalidate(key)

    if _batch_active:
        if key == "anki_tycoon_vehicle_data":
            garage_size = len(val.get("garage", {})) if isinstance(val, dict) else "N/A"
            logger.debug("cfg_set(%s): batch mode — gom lại, garage có %s xe", key, garage_size)
        _batch_writes[key] = val
        return

    if not col_ready():
        logger.warning("cfg_set(%s): col_ready() == False, bỏ qua ghi!", key)
        return
    try:
        if key == "anki_tycoon_vehicle_data":
            garage_size = len(val.get("garage", {})) if isinstance(val, dict) else "N/A"
            logger.debug("cfg_set(%s): ghi config với garage có %s xe (type val=%s)", key, garage_size, type(val).__name__)
        mw.col.set_config(key, val)
        _cache_set(key, val)
        if key == "anki_tycoon_vehicle_data":
            logger.debug("cfg_set(%s): đã ghi và cache thành công", key)
    except Exception as e:
        logger.warning("cfg_set(%s): %s", key, e)


def cfg_remove(key: str):
    """Xoá key — fallback set giá trị default hợp lý nếu không có remove_config."""
    _cache_invalidate(key)
    if not col_ready():
        return
    try:
        if hasattr(mw.col, "remove_config"):
            mw.col.remove_config(key)
        else:
            mw.col.set_config(key, 0)
    except Exception as e:
        logger.warning("cfg_remove(%s): %s", key, e)


def purge_none_keys(keys: list):
    """Sửa các key có value = None về giá trị mặc định hợp lý theo kiểu."""
    if not col_ready():
        return
    for key in keys:
        try:
            v = mw.col.get_config(key, None)
            if v is None:
                # Đoán kiểu default theo tên key
                if any(s in key for s in ("inventory", "transactions", "deposits", "reset_log", "stocks_portfolio", "stocks_transactions")):
                    mw.col.set_config(key, [])
                    _cache_set(key, [])
                elif any(s in key for s in ("stats", "demand_savings", "freshness", "boosts", "stocks_market", "stocks_price_history")):
                    mw.col.set_config(key, {})
                    _cache_set(key, {})
                elif "date" in key or "month_reset" in key:
                    mw.col.set_config(key, "")
                    _cache_set(key, "")
                else:
                    mw.col.set_config(key, 0)
                    _cache_set(key, 0)
        except Exception as e:
            logger.warning("purge_none_keys(%s): %s", key, e)
