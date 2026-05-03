# -*- coding: utf-8 -*-
"""
reset_manager.py — Quản lý reset toàn bộ tài sản về 0 (xóa sạch mọi dấu vết).

Cơ chế:
  - Xoá toàn bộ config keys (game data)
  - Xoá luôn thị trường CK & crypto (sẽ được re-seed tự nhiên khi UI gọi)
  - Cấp lại 10 triệu VND vốn khởi đầu + nhà trọ cơ bản
  - Ghi log reset (một bản ghi duy nhất)
  - Flush toàn bộ in-memory cache để đảm bảo không còn dữ liệu cũ
"""

import time
from aqt import mw
from datetime import datetime

CONFIRM_PHRASE  = "XAC NHAN CHOI LAI"
_KEY_RESET_LOG  = "anki_tycoon_reset_log"
_KEY_RESET_FLAG = "anki_tycoon_reset_just_done"
_MIN_RESET_BALANCE = 50_000


def get_confirm_phrase() -> str:
    return CONFIRM_PHRASE


def _invalidate_cache(key: str):
    """Xoá key khỏi in-memory cache của _safe_config."""
    try:
        from ._safe_config import _cache_invalidate
        _cache_invalidate(key)
    except Exception:
        pass


def _flush_all_cache():
    """Xoá toàn bộ in-memory cache — gọi sau reset để tránh dữ liệu cũ."""
    try:
        from ._safe_config import _cache_invalidate
        _cache_invalidate()  # None = clear all
    except Exception:
        pass


def _safe_remove(key: str):
    """Xoá key — ưu tiên remove_config, fallback set giá trị rỗng."""
    _invalidate_cache(key)
    try:
        if hasattr(mw.col, "remove_config"):
            mw.col.remove_config(key)
        else:
            _set_empty_by_key(key)
    except Exception:
        pass


def _set_empty_by_key(key: str):
    """Set giá trị rỗng phù hợp theo loại key (fallback khi không có remove_config)."""
    # Dict-type keys
    if any(s in key for s in ("stats", "market", "history", "demand_savings",
                              "freshness", "boosts", "goal", "cycle",
                              "residence", "quest_seed", "budget",
                              "monthly_spending", "monthly_income",
                              "monthly_cards", "loan_balance",
                              "reset_just_done")):
        mw.col.set_config(key, {})
    # List-type keys
    elif any(s in key for s in ("inventory", "transactions", "deposits",
                                "portfolio", "staking", "log",
                                "streak_today_cards", "streak_today_date",
                                "send_more_log", "quests", "pit_log",
                                "land_tax_log", "living_cost_log", "loan_log",
                                "reset_log")):
        mw.col.set_config(key, [])
    # String-type keys (dates, etc.)
    elif any(s in key for s in ("date", "timestamp", "last_update",
                                "last_collect", "last_tax", "last_month",
                                "last_living", "initialized", "streak_date",
                                "last_tax_date")):
        mw.col.set_config(key, "")
    # Numeric-type keys
    else:
        mw.col.set_config(key, 0)


def _re_init_player():
    """Cấp lại 10 triệu VND + nhà trọ cơ bản + đánh dấu reset."""
    from ._safe_config import cfg_set
    from .housing_residence import _DEFAULT_RESIDENCE
    from .balance import set_balance
    # Dùng set_balance() thay vì cfg_set trực tiếp để đảm bảo topbar refresh
    set_balance(10_000_000)
    cfg_set("anki_tycoon_residence", dict(_DEFAULT_RESIDENCE))
    cfg_set("anki_tycoon_initialized", {"done": True})
    # Đánh dấu reset vừa xong để _on_profile_loaded không ghi đè
    cfg_set(_KEY_RESET_FLAG, {"ts": time.time()})


def clear_reset_flag():
    """Xoá flag reset — gọi sau khi _on_profile_loaded đã chạy xong."""
    _safe_remove(_KEY_RESET_FLAG)


def is_reset_just_done() -> bool:
    """Kiểm tra xem reset vừa được thực hiện trong phiên này chưa."""
    try:
        from ._safe_config import cfg_dict
        raw = cfg_dict(_KEY_RESET_FLAG, {})
        return bool(raw)
    except Exception:
        return False


# ── Danh sách keys cần xoá ──────────────────────────────────

KEYS_TO_CLEAR = [
    # ── Core finance ──────────────────────────────────────────
    "anki_tycoon_balance",
    "anki_tycoon_stats",
    "anki_tycoon_inventory",
    "anki_tycoon_transactions",
    "anki_tycoon_budget",
    "anki_tycoon_monthly_spending",
    "anki_tycoon_monthly_income",
    "anki_tycoon_last_month_reset",
    # ── Bank ─────────────────────────────────────────────────
    "anki_tycoon_demand_savings",
    "anki_tycoon_term_deposits",
    "anki_tycoon_term_send_more_log",
    "anki_tycoon_savings",
    "anki_tycoon_savings_timestamp",
    "anki_tycoon_instant_interest",
    # ── Again tracker ────────────────────────────────────────
    "anki_tycoon_daily_again_count",
    "anki_tycoon_daily_again_date",
    "anki_tycoon_daily_again_penalty",
    # ── Food / boosts ────────────────────────────────────────
    "anki_tycoon_active_boosts",
    "anki_tycoon_food_freshness",
    # ── Goals ────────────────────────────────────────────────
    "anki_tycoon_goal",
    # ── Streak / Rank / Quest ────────────────────────────────
    "anki_tycoon_xp",
    "anki_tycoon_rank",
    "anki_tycoon_streak",
    "anki_tycoon_streak_date",
    "anki_tycoon_best_streak",
    "anki_tycoon_streak_today_cards",
    "anki_tycoon_streak_today_date",
    "anki_tycoon_daily_quests",
    "anki_tycoon_quest_seed",
    # ── Real estate ──────────────────────────────────────────
    "anki_tycoon_re_portfolio",
    "anki_tycoon_re_last_collect",
    "anki_tycoon_re_market",
    "anki_tycoon_re_upgrades",
    # ── Stock market ─────────────────────────────────────────
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
    # ── Crypto market ────────────────────────────────────────
    "anki_tycoon_crypto_market",
    "anki_tycoon_crypto_portfolio",
    "anki_tycoon_crypto_last_update",
    "anki_tycoon_crypto_price_history",
    "anki_tycoon_crypto_transactions",
    "anki_tycoon_crypto_review_count",
    "anki_tycoon_crypto_staking",
    "anki_tycoon_crypto_market_cycle",
    # ── Tax system ───────────────────────────────────────────
    "anki_tycoon_last_tax_date",
    "anki_tycoon_pit_log",
    "anki_tycoon_monthly_cards_count",
    "anki_tycoon_pit_withheld_this_month",
    "anki_tycoon_land_tax_log",
    # ── Housing / Residence ──────────────────────────────────
    "anki_tycoon_residence",
    "anki_tycoon_initialized",
    # ── Living costs ─────────────────────────────────────────
    "anki_tycoon_last_living_cost_date",
    "anki_tycoon_living_cost_log",
    # ── Loan system ──────────────────────────────────────────
    "anki_tycoon_loan_balance",
    "anki_tycoon_loan_log",
    # ── Food purchase log (daily limit tracker) ──────────────
    "anki_tycoon_food_purchase_log",
    # ── Study purchase log (weekly limit tracker) ────────────
    "anki_tycoon_study_purchase_log",
    # ── Vehicle system ───────────────────────────────────────
    "anki_tycoon_vehicle_data",
    "anki_tycoon_garage_slots_bought",
    # ── Passive effects ──────────────────────────────────────
    "anki_tycoon_passive_effects",
    # ── Achievements ───────────────────────────────────────────
    "anki_tycoon_achievement_data",
    "anki_tycoon_achievement_effects",
    # ── Credit Banking (tín dụng & vay ngân hàng) ─────────────
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
    # ── Economy Controls (daily cap, CPI, garage, consumables) ─
    "anki_tycoon_daily_cap_data",
    "anki_tycoon_daily_cap_date",
    "anki_tycoon_total_system_cards",
    "anki_tycoon_cpi_index",
    "anki_tycoon_garage_fees_date",
    "anki_tycoon_breakdown_log",
    "anki_tycoon_consumable_cooldowns",
    # ── Energy System ─────────────────────────────────────────
    "anki_tycoon_energy",
    "anki_tycoon_max_energy_base",
    "anki_tycoon_energy_last_regen",
    # ── Finance Quiz ──────────────────────────────────────────
    "anki_tycoon_quiz_stats",
    "anki_tycoon_quiz_set_index",
    "anki_tycoon_quiz_set_data",
    "anki_tycoon_quiz_topic",
    "anki_tycoon_quiz_daily_date",
    "anki_tycoon_quiz_daily_correct",
    # ── Emergency Events ──────────────────────────────────────
    "anki_tycoon_emergency_last_date",
    "anki_tycoon_emergency_log",
    # ── Login tracker ─────────────────────────────────────────
    "anki_tycoon_last_login",
    # ── Reset log ────────────────────────────────────────────
    "anki_tycoon_reset_log",
]

# Keys KHÔNG xoá (dữ liệu người dùng):
#   anki_tycoon_knowledge    — Kiến thức tài chính
#   anki_tycoon_tax_log      — Lịch sử thuế (audit)


def perform_reset(confirm_input: str, hard: bool = False) -> dict:
    """
    Thực hiện reset toàn bộ game.

    Parameters:
        confirm_input: Chuỗi xác nhận (phải đúng CONFIRM_PHRASE)
        hard: Nếu True → xoá cả tax_log, knowledge_base để xoá sạch hoàn toàn

    Returns:
        {"ok": True, "snapshot": {...}} hoặc {"ok": False, "error": "..."}
    """
    if confirm_input.strip().upper() != CONFIRM_PHRASE:
        return {"ok": False, "error": f'Sai cụm xác nhận. Phải nhập đúng: "{CONFIRM_PHRASE}"'}

    if mw is None or mw.col is None:
        return {"ok": False, "error": "Hệ thống chưa sẵn sàng, thử lại sau."}

    from .balance import get_balance
    balance = get_balance()
    if balance < 0:
        return {"ok": False, "error": "Không thể reset khi tài khoản đang nợ."}
    if balance < _MIN_RESET_BALANCE:
        return {"ok": False, "error": "Chỉ có thể reset khi số dư hiện tại từ 50.000 VND trở lên."}

    from .bank import get_total_savings, get_total_current_value
    snapshot = {
        "balance":   balance,
        "savings":   get_total_savings(),
        "net_worth": int(get_total_current_value()) + balance,
    }

    # ── Bước 1: Xoá toàn bộ keys ──────────────────────────────
    keys = list(KEYS_TO_CLEAR)

    # Hard reset: xoá thêm tax_log + knowledge
    if hard:
        keys.extend([
            "anki_tycoon_tax_log",
            "anki_tycoon_knowledge",
        ])

    for key in keys:
        _safe_remove(key)

    # ── Bước 2: Flush toàn bộ cache để tránh dữ liệu cũ ───────
    _flush_all_cache()

    # ── Bước 3: Cấp lại vốn khởi đầu 10 triệu + nhà trọ ──────
    _re_init_player()

    # ── Bước 4: Ghi log reset (chỉ 1 bản ghi) ────────────────
    try:
        mw.col.set_config(_KEY_RESET_LOG, [{
            "date":     datetime.now().strftime("%d/%m/%Y %H:%M"),
            "snapshot": snapshot,
            "hard":     hard,
        }])
    except Exception:
        pass

    # ── Bước 5: Refresh topbar ────────────────────────────────
    try:
        if hasattr(mw, "tycoon_topbar") and mw.tycoon_topbar:
            mw.tycoon_topbar.refresh()
    except Exception:
        pass

    return {"ok": True, "snapshot": snapshot}


def perform_hard_reset(confirm_input: str) -> dict:
    """
    Reset cục bộ — xoá sạch mọi dữ liệu kể cả lịch sử reset, lịch sử thuế, kiến thức tài chính.
    Là wrapper gọi perform_reset() với hard=True.
    """
    return perform_reset(confirm_input, hard=True)


def get_reset_log() -> list:
    if mw is None or mw.col is None:
        return []
    try:
        val = mw.col.get_config(_KEY_RESET_LOG, [])
        return val if isinstance(val, list) else []
    except Exception:
        return []
