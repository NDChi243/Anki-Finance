# -*- coding: utf-8 -*-
"""
logger.py — Logging framework chuẩn cho Anki Finance.

Cung cấp:
  - logging.getLogger(__name__) pattern cho mỗi module
  - Cấu hình log level qua Anki config (anki_tycoon_log_level)
  - Ghi log ra file để debug
  - Helper log_error() để log exception với traceback
  - Helper log_return() để log fallback/graceful degradation

Usage:
    from .logger import get_logger
    logger = get_logger(__name__)

    try:
        result = do_something()
    except SpecificError as e:
        logger.error("Lỗi khi do_something: %s", e, exc_info=True)
        result = default_value
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# ── Module-level root logger ──────────────────────────────────────
_LOG_ROOT = "anki_finance"
_logger = logging.getLogger(_LOG_ROOT)

# ── Handlers ─────────────────────────────────────────────────────
_file_handler: RotatingFileHandler = None
_console_handler: logging.StreamHandler = None
_initialized = False


def _get_log_dir() -> str:
    """Lấy thư mục chứa log file (cùng thư mục với addon)."""
    return os.path.dirname(os.path.abspath(__file__))


def _get_log_file() -> str:
    """Đường dẫn đến file log."""
    return os.path.join(_get_log_dir(), "anki_finance.log")


def _level_from_config(level_name: str | None, default: int = logging.WARNING) -> int:
    """Chuyển tên level từ config thành logging constant."""
    if not level_name:
        return default
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    return level_map.get(level_name, default)


def setup_logging(log_level: int | str | None = None,
                  log_file: str | None = None) -> logging.Logger:
    """
    Khởi tạo logging framework.

    Args:
        log_level: Mức log (int logging constant, str level name, hoặc None để đọc từ config).
                   Nếu None, đọc từ config Anki (anki_tycoon_log_level).
        log_file: Đường dẫn file log. Nếu None, dùng mặc định (anki_finance.log trong thư mục addon).

    Returns:
        logging.Logger instance.
    """
    global _file_handler, _console_handler, _initialized

    if _initialized:
        # Nếu đã init, chỉ update level nếu cần
        if log_level is not None:
            level = _level_from_config(log_level) if isinstance(log_level, str) else log_level
            _logger.setLevel(level)
            if _file_handler:
                _file_handler.setLevel(level)
        return _logger

    # ── Xác định log level ──
    if log_level is None:
        # Đọc từ Anki config (nếu có thể)
        try:
            from aqt import mw
            if mw is not None and mw.col is not None:
                cfg_level = mw.col.get_config("anki_tycoon_log_level", None)
                if cfg_level is not None:
                    log_level = _level_from_config(cfg_level)
        except Exception:
            pass

    if log_level is None:
        log_level = logging.WARNING  # Mặc định: WARNING
    elif isinstance(log_level, str):
        log_level = _level_from_config(log_level)

    if log_file is None:
        log_file = _get_log_file()

    _logger.setLevel(log_level)

    # ── File handler (Rotating, 10MB, 3 backups) ──
    try:
        _file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=3,
            encoding="utf-8",
        )
        _file_handler.setLevel(log_level)
        _file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        _logger.addHandler(_file_handler)
    except Exception as e:
        # Không thể tạo file handler -> fallback chỉ console
        print(f"[AnkiFinance][Logger] ⚠ Không thể tạo file log '{log_file}': {e}", file=sys.stderr)

    # ── Console handler (Anki terminal) ──
    _console_handler = logging.StreamHandler(sys.stdout)
    _console_handler.setLevel(logging.WARNING)  # Console chỉ hiển thị WARNING+
    _console_handler.setFormatter(logging.Formatter(
        "[AnkiFinance] %(levelname)s | %(message)s",
    ))
    _logger.addHandler(_console_handler)

    _initialized = True

    _logger.info("Logging initialized — level=%s, file=%s",
                 logging.getLevelName(log_level), log_file)

    return _logger


def get_logger(module_name: str) -> logging.Logger:
    """
    Lấy logger cho một module cụ thể.
    Tự động rút gọn __name__ (vd: 'balance' thay vì 'anki_finance.balance').

    Usage:
        from .logger import get_logger
        logger = get_logger(__name__)
    """
    # Rút gọn module name
    if module_name.startswith(_LOG_ROOT + "."):
        module_name = module_name[len(_LOG_ROOT) + 1:]
    elif module_name == _LOG_ROOT:
        module_name = "root"
    elif module_name == "__main__":
        module_name = "main"

    return logging.getLogger(f"{_LOG_ROOT}.{module_name}")


def log_error(logger: logging.Logger, context: str,
              exc: BaseException | None = None,
              extra: str | None = None) -> None:
    """
    Helper: ghi log error kèm traceback.
    Tương đương logger.error("...", exc_info=True) nhưng ngắn gọn hơn.

    Args:
        logger: Logger instance.
        context: Mô tả ngữ cảnh (vd: "load_shop_items").
        exc: Exception object (nếu None, lấy từ sys.exc_info()).
        extra: Thông tin bổ sung.
    """
    msg = f"[{context}]"
    if extra:
        msg = f"{msg} {extra}"
    logger.error(msg, exc_info=exc if exc else True)


def log_warning(logger: logging.Logger, context: str,
                detail: str = "",
                exc: BaseException | None = None) -> None:
    """
    Helper: ghi log warning (không traceback, chỉ thông báo).
    Dùng cho các fallback/graceful degradation.

    Args:
        logger: Logger instance.
        context: Mô tả ngữ cảnh.
        detail: Chi tiết lỗi.
        exc: Exception object (optional, nếu có sẽ log thêm message).
    """
    if detail:
        logger.warning("[%s] %s", context, detail)
    else:
        logger.warning("[%s]", context)
    if exc:
        logger.debug("[%s] Exception: %s: %s", context, type(exc).__name__, exc)
