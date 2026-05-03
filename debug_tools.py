# -*- coding: utf-8 -*-
from __future__ import annotations
"""
debug_tools.py — Công cụ gỡ lỗi / sửa chữa dữ liệu cho Anki Finance.

Cơ chế:
  - Quét toàn bộ config keys, phát hiện giá trị None, sai kiểu, thiếu key
  - Tự động sửa chữa (repair) dữ liệu hỏng
  - Xoá in-memory cache để load lại từ Anki config
  - Trả về báo cáo chi tiết những gì đã sửa
  - An toàn: KHÔNG xoá dữ liệu người dùng, chỉ sửa lỗi

Cách dùng từ JS:
  const raw = await B.runDebugTools();
  const report = JSON.parse(raw);
  // report.fixed_keys, report.repaired, report.errors, ...

Version: 1.1.0e
"""

import time
import traceback
from aqt import mw


# ── Danh sách keys được bảo vệ (không quét type, không sửa) ──────
# Các keys này có cơ chế quản lý riêng, debug_tools không được động vào
# để tránh clear nhầm dữ liệu người dùng (portfolio, market, staking, ...)
PROTECTED_KEYS: set[str] = {
    # ── Energy System ──────────────────────────────────────────
    # Tự quản lý kiểu dữ liệu nội bộ (float timestamp)
    "anki_tycoon_energy",
    "anki_tycoon_max_energy_base",
    "anki_tycoon_energy_last_regen",
    # ── Emergency Events ───────────────────────────────────────
    # Tự quản lý, tránh bị clear ngày
    "anki_tycoon_emergency_last_date",
    "anki_tycoon_emergency_log",
    # ── Stock Market (Chứng khoán) ─────────────────────────────
    # Tự quản lý market, portfolio, dividends, corporate actions
    "anki_tycoon_stocks_market",
    "anki_tycoon_stocks_portfolio",
    "anki_tycoon_stocks_last_update",
    "anki_tycoon_stocks_price_history",
    "anki_tycoon_stocks_transactions",
    "anki_tycoon_stocks_review_count",
    "anki_tycoon_stocks_simulated_session",
    "anki_tycoon_stocks_dividends",
    "anki_tycoon_stocks_corp_actions",
    "anki_tycoon_stocks_div_events",
    "anki_tycoon_stocks_ca_events",
    # ── Crypto Market ──────────────────────────────────────────
    # Tự quản lý market, portfolio, staking, market cycle
    "anki_tycoon_crypto_market",
    "anki_tycoon_crypto_portfolio",
    "anki_tycoon_crypto_last_update",
    "anki_tycoon_crypto_price_history",
    "anki_tycoon_crypto_transactions",
    "anki_tycoon_crypto_review_count",
    "anki_tycoon_crypto_staking",
    "anki_tycoon_crypto_market_cycle",
    # ── Real Estate ────────────────────────────────────────────
    # Tự quản lý portfolio, market, upgrades
    "anki_tycoon_re_portfolio",
    "anki_tycoon_re_last_collect",
    "anki_tycoon_re_market",
    "anki_tycoon_re_upgrades",
    # ── Credit Banking ─────────────────────────────────────────
    # Hệ thống tín dụng phức tạp, tự quản lý
    "anki_tycoon_credit_score",
    "anki_tycoon_credit_cards",
    "anki_tycoon_credit_bills",
    "anki_tycoon_bank_loans",
    "anki_tycoon_collateral",
    "anki_tycoon_income_verified",
    "anki_tycoon_loan_insurance",
    "anki_tycoon_loyalty",
    "anki_tycoon_credit_history",
    "anki_tycoon_overdue_logs",
    # ── Economy Controls ───────────────────────────────────────
    # Daily cap, CPI, garage fees, consumables — tự quản lý
    "anki_tycoon_daily_cap_data",
    "anki_tycoon_daily_cap_date",
    "anki_tycoon_total_system_cards",
    "anki_tycoon_cpi_index",
    "anki_tycoon_garage_fees_date",
    "anki_tycoon_breakdown_log",
    "anki_tycoon_consumable_cooldowns",
    # ── Housing / Residence ────────────────────────────────────
    "anki_tycoon_residence",
    "anki_tycoon_initialized",
    # ── Achievements ───────────────────────────────────────────
    "anki_tycoon_achievement_data",
    "anki_tycoon_achievement_effects",
    # ── Finance Quiz ───────────────────────────────────────────
    "anki_tycoon_quiz_stats",
    "anki_tycoon_quiz_set_index",
    "anki_tycoon_quiz_set_data",
    "anki_tycoon_quiz_topic",
    "anki_tycoon_quiz_daily_date",
    "anki_tycoon_quiz_daily_correct",
    # ── Vehicle System ─────────────────────────────────────────
    "anki_tycoon_vehicle_data",
    "anki_tycoon_garage_slots_bought",
    # ── Passive Effects ────────────────────────────────────────
    "anki_tycoon_passive_effects",
    # ── Food / Boosts ──────────────────────────────────────────
    "anki_tycoon_active_boosts",
    "anki_tycoon_food_freshness",
    # ── Goals ──────────────────────────────────────────────────
    "anki_tycoon_goal",
    # ── Knowledge Base ─────────────────────────────────────────
    "anki_tycoon_knowledge",
    # ── Tax Log (audit) ────────────────────────────────────────
    "anki_tycoon_tax_log",
    # ── Reset Log ──────────────────────────────────────────────
    "anki_tycoon_reset_log",
    "anki_tycoon_reset_just_done",
    # ── Rental Income Log ──────────────────────────────────────
    "anki_tycoon_rental_income_log",
    # ── Login Tracker ──────────────────────────────────────────
    "anki_tycoon_last_login",
}

# ── Danh sách tất cả keys + kiểu dữ liệu mong đợi ────────────────
# key → expected_type (str: "int", "str", "list", "dict", "float")
EXPECTED_TYPES: dict[str, str] = {
    # ── Core finance ──
    "anki_tycoon_balance":          "int",
    "anki_tycoon_stats":            "dict",
    "anki_tycoon_inventory":        "list",
    "anki_tycoon_transactions":     "list",
    "anki_tycoon_budget":           "int",
    "anki_tycoon_monthly_spending": "int",
    "anki_tycoon_monthly_income":   "int",
    "anki_tycoon_last_month_reset": "str",
    # ── Bank ──
    "anki_tycoon_demand_savings":            "dict",
    "anki_tycoon_term_deposits":             "list",
    "anki_tycoon_term_send_more_log":        "list",
    "anki_tycoon_savings":                   "int",
    "anki_tycoon_savings_timestamp":         "str",
    "anki_tycoon_instant_interest":          "dict",
    # ── Again tracker ──
    "anki_tycoon_daily_again_count":   "int",
    "anki_tycoon_daily_again_date":   "str",
    "anki_tycoon_daily_again_penalty": "int",
    # ── Food / boosts ──
    "anki_tycoon_active_boosts":     "dict",
    "anki_tycoon_food_freshness":    "dict",
    # ── Goals ──
    "anki_tycoon_goal":              "dict",
    # ── Streak / Rank / Quest ──
    "anki_tycoon_xp":               "int",
    "anki_tycoon_rank":             "str",
    "anki_tycoon_streak":           "int",
    "anki_tycoon_streak_date":      "str",
    "anki_tycoon_best_streak":      "int",
    "anki_tycoon_streak_today_cards":  "list",
    "anki_tycoon_streak_today_date":   "str",
    "anki_tycoon_daily_quests":     "list",
    "anki_tycoon_quest_seed":       "dict",
    # ── Real estate ──
    "anki_tycoon_re_portfolio":     "list",
    "anki_tycoon_re_last_collect":  "str",
    "anki_tycoon_re_market":        "dict",
    "anki_tycoon_re_upgrades":      "dict",
    # ── Stock market ──
    "anki_tycoon_stocks_market":            "dict",
    "anki_tycoon_stocks_portfolio":         "dict",
    "anki_tycoon_stocks_last_update":       "str",
    "anki_tycoon_stocks_price_history":     "dict",
    "anki_tycoon_stocks_transactions":      "list",
    "anki_tycoon_stocks_review_count":      "int",
    "anki_tycoon_stocks_simulated_session": "dict",
    "anki_tycoon_stocks_dividends":         "dict",
    "anki_tycoon_stocks_corp_actions":      "dict",
    "anki_tycoon_stocks_div_events":        "list",
    "anki_tycoon_stocks_ca_events":         "list",
    # ── Crypto market ──
    "anki_tycoon_crypto_market":            "dict",
    "anki_tycoon_crypto_portfolio":         "dict",
    "anki_tycoon_crypto_last_update":       "str",
    "anki_tycoon_crypto_price_history":     "dict",
    "anki_tycoon_crypto_transactions":      "list",
    "anki_tycoon_crypto_review_count":      "int",
    "anki_tycoon_crypto_staking":           "dict",
    "anki_tycoon_crypto_market_cycle":      "dict",
    # ── Tax system ──
    "anki_tycoon_last_tax_date":               "str",
    "anki_tycoon_pit_log":                     "list",
    "anki_tycoon_monthly_cards_count":         "int",
    "anki_tycoon_pit_withheld_this_month":     "int",
    "anki_tycoon_land_tax_log":                "list",
    # ── Housing / Residence ──
    "anki_tycoon_residence":    "dict",
    "anki_tycoon_initialized":  "dict",
    # ── Living costs ──
    "anki_tycoon_last_living_cost_date": "str",
    "anki_tycoon_living_cost_log":       "list",
    # ── Loan system ──
    "anki_tycoon_loan_balance": "int",
    "anki_tycoon_loan_log":     "list",
    # ── Food purchase log ──
    "anki_tycoon_food_purchase_log":  "list",
    # ── Study purchase log ──
    "anki_tycoon_study_purchase_log": "list",
    # ── Vehicle system ──
    "anki_tycoon_vehicle_data":       "dict",
    "anki_tycoon_garage_slots_bought": "int",
    # ── Passive effects ──
    "anki_tycoon_passive_effects": "dict",
    # ── Achievements ──
    "anki_tycoon_achievement_data":   "dict",
    "anki_tycoon_achievement_effects": "dict",
    # ── Credit Banking ──
    "anki_tycoon_credit_score":      "dict",
    "anki_tycoon_credit_cards":      "dict",
    "anki_tycoon_credit_bills":      "list",
    "anki_tycoon_bank_loans":        "list",
    "anki_tycoon_collateral":        "dict",
    "anki_tycoon_income_verified":   "dict",
    "anki_tycoon_loan_insurance":    "dict",
    "anki_tycoon_loyalty":           "dict",
    "anki_tycoon_credit_history":    "list",
    "anki_tycoon_overdue_logs":      "list",
    # ── Economy Controls ──
    "anki_tycoon_daily_cap_data":        "dict",
    "anki_tycoon_daily_cap_date":        "str",
    "anki_tycoon_total_system_cards":    "int",
    "anki_tycoon_cpi_index":             "float",
    "anki_tycoon_garage_fees_date":      "str",
    "anki_tycoon_breakdown_log":         "list",
    "anki_tycoon_consumable_cooldowns":  "dict",
    # ── Finance Quiz ──
    "anki_tycoon_quiz_stats":        "dict",
    "anki_tycoon_quiz_set_index":    "int",
    "anki_tycoon_quiz_set_data":     "list",
    "anki_tycoon_quiz_topic":        "str",
    "anki_tycoon_quiz_daily_date":   "str",
    "anki_tycoon_quiz_daily_correct": "int",
    # ── Login tracker ──
    "anki_tycoon_last_login": "str",
    # ── Reset log ──
    "anki_tycoon_reset_log":          "list",
    "anki_tycoon_reset_just_done":    "dict",
    # ── Knowledge ──
    "anki_tycoon_knowledge":  "list",
    # ── Tax log (audit) ──
    "anki_tycoon_tax_log":    "list",
    # ── Housing_residence ──
    "anki_tycoon_rental_income_log": "list",
}


def _col_ready() -> bool:
    try:
        return mw is not None and mw.col is not None
    except Exception:
        return False


def _get_default_for_type(expected: str):
    """Trả về giá trị mặc định hợp lý theo kiểu mong đợi."""
    if expected == "int":
        return 0
    elif expected == "float":
        return 0.0
    elif expected == "str":
        return ""
    elif expected == "list":
        return []
    elif expected == "dict":
        return {}
    return None


def _safe_get_type_name(val) -> str:
    """Trả về tên kiểu an toàn."""
    if val is None:
        return "None"
    return type(val).__name__


# ── Public API ────────────────────────────────────────────────────

def run_debug_tools() -> dict:
    """
    Chạy toàn bộ công cụ gỡ lỗi:
      1. Xoá in-memory cache
      2. Quét tất cả config keys để tìm None/NoneType
      3. Sửa type mismatches
      4. Trả về báo cáo chi tiết

    Returns:
        dict với các keys:
          - ok: bool
          - cache_cleared: bool
          - fixed_none_keys: [str, ...]  — keys đã sửa từ None
          - fixed_type_keys: [{key, expected, found, default}, ...]
          - keys_ok: int                 — keys không có vấn đề
          - total_scanned: int           — tổng số keys đã quét
          - errors: [str, ...]           — lỗi nếu có
    """
    report: dict = {
        "ok": True,
        "cache_cleared": False,
        "fixed_none_keys": [],
        "fixed_type_keys": [],
        "keys_ok": 0,
        "total_scanned": 0,
        "errors": [],
    }

    if not _col_ready():
        report["ok"] = False
        report["errors"].append("Anki chưa sẵn sàng (mw.col là None).")
        return report

    try:
        # ── Bước 1: Xoá in-memory cache ──────────────────────
        try:
            from ._safe_config import _cache_invalidate
            _cache_invalidate()  # clear all
            report["cache_cleared"] = True
        except Exception as e:
            report["errors"].append(f"Không thể xoá cache: {e}")

        # ── Bước 2: Dọn None keys (dùng purge_none_keys hiện có) ──
        try:
            from ._safe_config import purge_none_keys
            # Lọc bỏ protected keys — không động vào
            all_keys = [k for k in EXPECTED_TYPES.keys() if k not in PROTECTED_KEYS]
            # Đếm số None trước khi sửa
            none_before = []
            for key in all_keys:
                try:
                    v = mw.col.get_config(key, None)
                    if v is None:
                        none_before.append(key)
                except Exception:
                    pass
            # Thực hiện sửa
            purge_none_keys(all_keys)
            # Ghi lại keys đã sửa (dựa trên những key từng là None)
            report["fixed_none_keys"] = none_before
        except Exception as e:
            report["errors"].append(f"Lỗi khi dọn None keys: {e}")

        # ── Bước 3: Kiểm tra type mismatches ──────────────────
        for key, expected in EXPECTED_TYPES.items():
            # Bỏ qua protected keys
            if key in PROTECTED_KEYS:
                report["keys_ok"] += 1
                report["total_scanned"] += 1
                continue
            report["total_scanned"] += 1
            try:
                v = mw.col.get_config(key, None)
                if v is None:
                    # Đã được xử lý ở bước 2, set giá trị mặc định
                    default = _get_default_for_type(expected)
                    if default is not None:
                        mw.col.set_config(key, default)
                    continue

                actual_type = _safe_get_type_name(v)

                # Map Python type names → expected type names
                type_map = {
                    "int": ("int", "float"),
                    "float": ("float", "int"),
                    "str": ("str",),
                    "list": ("list",),
                    "dict": ("dict",),
                }

                if actual_type not in type_map.get(expected, (expected,)):
                    # Type mismatch — sửa
                    default = _get_default_for_type(expected)
                    mw.col.set_config(key, default)
                    report["fixed_type_keys"].append({
                        "key": key,
                        "expected": expected,
                        "found": actual_type,
                        "default": default,
                    })
                else:
                    report["keys_ok"] += 1

            except Exception as e:
                report["errors"].append(f"Lỗi khi kiểm tra key '{key}': {e}")

        # ── Bước 4: Xoá lại cache 1 lần nữa để đảm bảo ────────
        try:
            from ._safe_config import _cache_invalidate
            _cache_invalidate()
        except Exception:
            pass

    except Exception as e:
        report["ok"] = False
        report["errors"].append(f"Lỗi không xác định: {traceback.format_exc()}")

    return report


def get_debug_report() -> dict:
    """
    Trả về báo cáo tổng quan hệ thống để debug:
      - Version hiện tại
      - Số dư
      - Số lượng config keys đang hoạt động
      - Tình trạng cache
      - Thông tin Anki profile

    KHÔNG sửa bất cứ gì — chỉ đọc.
    """
    report: dict = {
        "ok": True,
        "version": "",
        "balance": 0,
        "active_keys": 0,
        "total_expected_keys": len(EXPECTED_TYPES),
        "cache_size": 0,
        "profile": "",
        "anki_version": "",
        "errors": [],
    }

    if not _col_ready():
        report["ok"] = False
        report["errors"].append("Anki chưa sẵn sàng.")
        return report

    try:
        # Version
        try:
            from .auto_update import get_current_version
            report["version"] = get_current_version()
        except Exception:
            report["version"] = "?"

        # Balance
        try:
            from .balance import get_balance
            report["balance"] = get_balance()
        except Exception:
            pass

        # Đếm keys đang hoạt động
        active = 0
        for key in EXPECTED_TYPES:
            try:
                v = mw.col.get_config(key, None)
                if v is not None:
                    active += 1
            except Exception:
                pass
        report["active_keys"] = active

        # Cache size
        try:
            from ._safe_config import _config_cache
            report["cache_size"] = len(_config_cache)
        except Exception:
            pass

        # Profile
        try:
            report["profile"] = str(mw.pm.name)
        except Exception:
            report["profile"] = "?"

        # Anki version
        try:
            from anki import version as anki_ver
            report["anki_version"] = str(anki_ver)
        except Exception:
            report["anki_version"] = "?"

    except Exception as e:
        report["errors"].append(str(e))

    return report


def quick_repair() -> dict:
    """
    Sửa nhanh — chỉ chạy các bước cần thiết nhất để thông thoáng.
    Gọi từ __init__._on_profile_loaded() nếu cần.
    KHÔNG động vào PROTECTED_KEYS (energy, emergency events).

    Returns:
        {"repaired": bool, "details": str}
    """
    result = {"repaired": False, "details": ""}
    try:
        # Xoá cache
        from ._safe_config import _cache_invalidate
        _cache_invalidate()

        # Dọn None keys cơ bản — bỏ qua protected keys
        from ._safe_config import purge_none_keys
        safe_keys = [k for k in EXPECTED_TYPES.keys() if k not in PROTECTED_KEYS]
        purge_none_keys(safe_keys)

        result["repaired"] = True
        result["details"] = "Cache cleared, None keys purged (protected keys skipped)."
    except Exception as e:
        result["details"] = str(e)
    return result
