# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Anki Finance — Biến việc ôn thẻ thành trò chơi làm giàu!
"""

from aqt import mw, gui_hooks
from aqt.qt import QAction
from aqt.utils import qconnect
from anki.hooks import addHook

from .balance import add_reward, get_balance
from .config import REWARD_MAP
from .gui import TycoonTopBar, TycoonWindow

# ── Module-level imports cho hot path (tránh lazy import mỗi lần review) ──
from .stock_market import record_review as stock_record_review
from .digital_assets import record_review as crypto_record_review
from .streak_system import record_card_reviewed
from .rank_system import add_xp, get_xp_for_ease, get_rank_status
from .daily_quest import update_quest_progress
from .again_tracker import get_daily_again_count
from ._safe_config import begin_batch, commit_batch

import traceback

# ── Cache rank để tránh get_rank_status + get_balance mỗi thẻ ──
_last_rank_cache: str | None = None
_rank_check_counter: int = 0

def _log_error(context: str):
    """Ghi log lỗi ra console Anki để dễ debug."""
    print(f"[AnkiFinance] ⛔ ERROR in {context}: {traceback.format_exc()}")

# ── Hook: thưởng/phạt tiền sau mỗi lần ôn thẻ ───────────────────
def on_review_done(reviewer, card, ease):
    # Batch tất cả cfg_set() → 1 lần ghi Anki config duy nhất
    begin_batch()
    try:
        result = add_reward(ease)
        _show_review_fx(reviewer, ease, result)
        _update_gamification(ease, result)
        stock_record_review(1)
        crypto_record_review(1)
        # Bond system: ghi nhận thẻ review để tính coupon
        try:
            from .bond_system import record_review as bond_record_review
            bond_record_review(1)
        except Exception:
            pass
        # Hồi năng lượng từ food boost (energy_regen)
        _apply_energy_regen(result)
        # Áp dụng hiệu ứng học tập thực tế lên interval của thẻ
        _apply_study_effects(card, ease, result)
        # Achievement trigger
        try:
            from .achievements import check_and_unlock
            check_and_unlock("card_reviewed", ease)
        except Exception:
            pass

        # ── Economy Controls Integration ──
        try:
            from .economy_controls import (
                increment_daily_cards_count,
                increment_total_system_cards,
                check_breakdown_on_review,
            )
            from .vehicle_system import get_active_vehicle, consume_durability as veh_consume_durability

            increment_daily_cards_count()
            increment_total_system_cards()

            # Tiêu hao độ bền + nhiên liệu cho xe đang active
            active_veh = get_active_vehicle()
            if active_veh:
                veh_id = active_veh.get("item_id") or active_veh.get("vehicle_id")
                if veh_id:
                    # Gọi consume_durability thực sự (giảm độ bền + xăng/điện)
                    veh_consume_durability(1)

                    # Kiểm tra sự cố ngẫu nhiên
                    breakdown = check_breakdown_on_review(veh_id)
                    if breakdown.get("broken"):
                        from .economy_controls import start_breakdown_repair
                        start_breakdown_repair(veh_id)
                        try:
                            from aqt.utils import showInfo
                            name = breakdown.get("name", "Xe của bạn")
                            emoji = breakdown.get("emoji", "🚗")
                            cost = breakdown.get("repair_cost", 0)
                            reviews_req = breakdown.get("reviews_required", 30)
                            showInfo(
                                f"{emoji} <b>{name} gặp sự cố!</b><br>"
                                f"Chi phí sửa chữa: <b>{cost:,}đ</b><br>"
                                f"<small>Hoàn thành {reviews_req} thẻ review để sửa xong.</small>"
                            )
                        except Exception:
                            pass

            # Tiêu hao độ bền cho tech item đang active
            try:
                from .tech_system import consume_durability as tech_consume_durability
                tech_consume_durability(1)
            except Exception:
                pass
        except Exception:
            pass
    except Exception:
        _log_error("on_review_done")
    finally:
        commit_batch()


def _apply_study_effects(card, ease: int, review_result: dict | None = None):
    """
    Áp dụng các hiệu ứng can thiệp scheduler từ passive effects
    lên interval thực tế của thẻ Anki, KHÔNG phá vỡ FSRS.

    Cơ chế:
      - density_reduction (MỚI - thay thế study_time_reduction trên xe):
        Giảm MẬT ĐỘ ôn tập = tăng interval trực tiếp (an toàn với FSRS)
        Không chạm vào card.factor → không phá thuật toán
        VD: thẻ 10 ngày + giảm 10% mật độ → interval 11 ngày

      - interval_boost: Tăng trực tiếp khoảng cách ôn tập thêm %
        (tăng ivl → thẻ xuất hiện muộn hơn)

      - study_time_reduction (CŨ - giữ tương thích ngược):
        Giảm ease → interval ngắn hơn → thẻ ra sớm hơn
        KHÔNG khuyến khích dùng cho item mới (phá FSRS)
    """
    # Chỉ áp dụng cho thẻ đã trả lời đúng (ease 2-4)
    if ease < 2:
        return
    if not card or not hasattr(card, 'ivl'):
        return
    try:
        from .item_effects import get_all_passive_effects
        effects = get_all_passive_effects() or {}

        # --- Đọc các effect từ passive ---
        interval_reduction = float(effects.get("study_time_reduction", 0.0))  # LEGACY: giảm ease
        density_reduction_val = float(effects.get("density_reduction", 0.0))  # MỚI: giảm mật độ = tăng ivl
        interval_boost_val = float(effects.get("interval_boost", 0.0))        # Tăng interval
        easy_interval_bonus = float(effects.get("easy_interval_bonus", 0.0))  # Bonus Easy
        factor_boost_val = float(effects.get("factor_boost", 0.0))            # Tăng ease factor

        # --- Gộp boost từ item dùng 1 lần (food, consumable) ---
        boost_info = (review_result or {}).get("boost", {}) if isinstance(review_result, dict) else {}
        if not effects and not boost_info:
            return
        interval_boost_val += float(boost_info.get("interval_boost", 0.0) or 0.0)
        factor_boost_val += float(boost_info.get("factor_boost", 0.0) or 0.0)
        if ease == 4:
            interval_boost_val += easy_interval_bonus
            interval_boost_val += float(boost_info.get("easy_interval_bonus", 0.0) or 0.0)

        # --- Giới hạn tối đa (tránh mất cân bằng game) ---
        interval_reduction = min(0.5, interval_reduction)
        density_reduction_val = min(0.5, density_reduction_val)  # cap 50% như study_time_reduction cũ
        interval_boost_val = min(0.8, interval_boost_val)
        factor_boost_val = min(0.25, factor_boost_val)

        if (interval_reduction <= 0.0 and density_reduction_val <= 0.0 and
                interval_boost_val <= 0.0 and factor_boost_val <= 0.0):
            return

        # --- 1. study_time_reduction (LEGACY): GIẢM ease → interval ngắn hơn ---
        # Giữ tương thích ngược cho item cũ, nhưng KHÔNG khuyến khích dùng
        old_factor = getattr(card, 'factor', None)
        if old_factor is not None and old_factor > 0:
            new_factor = old_factor
            if interval_reduction > 0.0:
                new_factor = int(new_factor * (1.0 - interval_reduction))
            if factor_boost_val > 0.0:
                new_factor = int(new_factor * (1.0 + factor_boost_val))
            card.factor = min(4000, max(new_factor, 1300))

        # --- 2. density_reduction + interval_boost: TĂNG interval → giãn cách an toàn ---
        # KHÔNG chạm vào card.factor → KHÔNG phá FSRS
        # density_reduction là cơ chế MỚI thay thế study_time_reduction trên xe
        total_ivl_boost = interval_boost_val + density_reduction_val
        if total_ivl_boost > 0.0 and card.ivl > 0:
            old_ivl = int(card.ivl)
            new_ivl = int(old_ivl * (1.0 + total_ivl_boost))
            card.ivl = max(old_ivl, new_ivl)  # chỉ tăng, không giảm
            # Cập nhật due date (ngày đến hạn) — đẩy thẻ ra xa hơn
            if hasattr(card, 'due') and card.ivl > 0:
                card.due = card.due + max(0, card.ivl - old_ivl)

        card.flush()
    except Exception:
        _log_error("_apply_study_effects")


def _apply_energy_regen(result: dict):
    """Hồi năng lượng thực tế từ food boost energy_regen."""
    try:
        regen = int((result or {}).get("boost", {}).get("energy_regen", 0) or 0)
        if regen <= 0:
            return
        from .energy_system import restore_energy
        restore_energy(regen)
    except Exception:
        pass


def _update_gamification(ease: int, result: dict):
    """Cập nhật streak + XP + quest progress (gom 1 try/except)."""
    global _last_rank_cache, _rank_check_counter
    try:
        # ── Streak ──
        streak_result = record_card_reviewed()
        if streak_result.get("milestone_hit"):
            _show_streak_milestone(streak_result["milestone_val"],
                                   streak_result["multiplier"])
        # ── XP + Rank (chỉ check rank mỗi 20 thẻ) ──
        xp = get_xp_for_ease(ease)
        if xp > 0:
            # Áp dụng xp_multiplier từ passive effects (xe, hàng hiệu, tech, crypto, BĐS, ...)
            try:
                from .item_effects import get_all_passive_effects
                passive = get_all_passive_effects()
                xp_mult = float(passive.get("xp_multiplier", 1.0))
                if xp_mult > 0:
                    xp = max(1, int(xp * xp_mult))
            except Exception:
                pass
            add_xp(xp)
            _rank_check_counter += 1
            if _rank_check_counter >= 20 or _last_rank_cache is None:
                _rank_check_counter = 0
                new_status = get_rank_status(get_balance())
                new_rank = new_status["rank_id"]
                if _last_rank_cache is not None and _last_rank_cache != new_rank:
                    _show_rank_up(new_status)
                _last_rank_cache = new_rank
        # ── Quest progress ──
        update_quest_progress("cards_total", 1)
        if ease == 4:
            update_quest_progress("cards_easy", 1)
        elif ease == 3:
            update_quest_progress("cards_good", 1)
        elif ease == 2:
            update_quest_progress("cards_hard", 1)
        update_quest_progress("earn_xp", xp)
        again_count = get_daily_again_count()
        update_quest_progress("no_again_under", again_count, set_absolute=True)
        update_quest_progress("again_ratio", again_count, set_absolute=True)
        if not result.get("penalized"):
            update_quest_progress("no_penalty", 0, set_absolute=True)
    except Exception:
        _log_error("_update_gamification")

def _show_streak_milestone(days: int, mult: float):
    """Hiệu ứng milestone streak trên reviewer."""
    try:
        from aqt import mw
        if not hasattr(mw, "reviewer") or not mw.reviewer:
            return
        text = f"🔥 STREAK {days} NGÀY! ×{mult:.1f}"
        color = "#f97316"
        js = f"""(function(){{
            var el=document.createElement('div');
            el.textContent='{text}';
            el.style.cssText='position:fixed;top:30%;left:50%;transform:translateX(-50%) scale(1);'+
            'background:#1a0a0066;border:2px solid {color};color:{color};'+
            'font-size:22px;font-weight:900;padding:12px 28px;border-radius:32px;'+
            'z-index:99999;pointer-events:none;font-family:-apple-system,Segoe UI,sans-serif;'+
            'box-shadow:0 4px 28px {color}66;transition:all .5s ease;';
            document.body.appendChild(el);
            setTimeout(()=>{{el.style.opacity='0';el.style.transform='translateX(-50%) scale(1.1)';el.style.top='25%';}},1200);
            setTimeout(()=>el.remove(),1700);
        }})();"""
        mw.reviewer.web.eval(js)
    except Exception:
        _log_error("_show_streak_milestone")

def _show_rank_up(status: dict):
    """Hiệu ứng lên rank."""
    try:
        from aqt import mw
        if not hasattr(mw, "reviewer") or not mw.reviewer:
            return
        emoji = status.get("rank_emoji","⭐")
        label = status.get("rank_label","")
        color = status.get("rank_color","#a855f7")
        text  = f"{emoji} Lên rank: {label}!"
        js = f"""(function(){{
            var el=document.createElement('div');
            el.textContent='{text}';
            el.style.cssText='position:fixed;top:20%;left:50%;transform:translateX(-50%);'+
            'background:rgba(0,0,0,.85);border:2px solid {color};color:{color};'+
            'font-size:18px;font-weight:900;padding:14px 32px;border-radius:32px;'+
            'z-index:99999;pointer-events:none;font-family:-apple-system,Segoe UI,sans-serif;'+
            'box-shadow:0 0 40px {color}88;transition:all .6s ease;';
            document.body.appendChild(el);
            setTimeout(()=>{{el.style.opacity='0';el.style.transform='translateX(-50%) scale(1.05)';}},2200);
            setTimeout(()=>el.remove(),2800);
        }})();"""
        mw.reviewer.web.eval(js)
    except Exception:
        _log_error("_show_rank_up")

gui_hooks.reviewer_did_answer_card.append(on_review_done)


def _show_review_fx(reviewer, ease: int, result: dict):
    """Hiệu ứng nổi lên góc phải thẻ — màu và nội dung theo kết quả."""
    if result.get("penalized"):
        color   = "#ef4444"
        text    = f"-{result['penalty']:,}đ 🚨".replace(",", ".")
        if result.get("count", 0) >= 60:
            text = f"🔴 PHẠT NẶNG -{result['penalty']:,}đ".replace(",", ".")
    elif result.get("warn"):
        color = "#f59e0b"
        text  = result.get("message", "⚠️")
    elif result.get("rewarded"):
        colors = {1: "#94a3b8", 2: "#f59e0b", 3: "#10b981", 4: "#3b82f6"}
        color  = colors.get(ease, "#10b981")
        # FIX Req3: dùng message từ result (đã tính boost) thay vì REWARD_MAP cứng
        text   = result.get("message", f"+{REWARD_MAP.get(ease,0):,}đ".replace(",","."))
    else:
        return

    js = f"""
(function() {{
    var el = document.createElement('div');
    el.textContent = '{text}';
    el.style.cssText =
        'position:fixed;bottom:72px;right:22px;' +
        'background:{color}1a;border:2px solid {color};color:{color};' +
        'font-size:17px;font-weight:900;padding:7px 16px;border-radius:28px;' +
        'z-index:99999;pointer-events:none;' +
        'font-family:-apple-system,Segoe UI,sans-serif;' +
        'box-shadow:0 4px 18px {color}44;' +
        'opacity:1;transform:translateY(0);' +
        'transition:opacity .5s ease,transform .5s ease;';
    document.body.appendChild(el);
    setTimeout(function(){{
        el.style.opacity='0';
        el.style.transform='translateY(-48px)';
    }}, 900);
    setTimeout(function(){{ el.remove(); }}, 1450);
}})();
"""
    try:
        reviewer.web.eval(js)
    except Exception:
        _log_error("_show_review_fx reviewer.web.eval")

# ── Inject TopBar ──────────────────────────────────────────────────
def _inject_topbar():
    if hasattr(mw, "tycoon_topbar"):
        return

    topbar = TycoonTopBar(mw)
    mw.tycoon_topbar = topbar

    central = mw.centralWidget()
    if central and central.layout():
        central.layout().insertWidget(0, topbar)
    else:
        from aqt.qt import QWidget, QVBoxLayout
        old = mw.takeCentralWidget()
        wrapper = QWidget()
        vbox = QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(topbar)
        if old:
            vbox.addWidget(old)
        mw.setCentralWidget(wrapper)


def _migrate_none_keys():
    """Dọn các key bị set = None từ các phiên bản cũ.
    
    Chỉ dọn các keys core finance đơn giản.
    KHÔNG dọn keys của stock market, crypto, real estate, credit banking, ...
    vì chúng có cơ chế tự quản lý và tự seed riêng.
    """
    try:
        from ._safe_config import purge_none_keys
        purge_none_keys([
            "anki_tycoon_balance",
            "anki_tycoon_stats",
            "anki_tycoon_inventory",
            "anki_tycoon_transactions",
            "anki_tycoon_budget",
            "anki_tycoon_monthly_spending",
            "anki_tycoon_monthly_income",
            "anki_tycoon_last_month_reset",
            "anki_tycoon_demand_savings",
            "anki_tycoon_term_deposits",
            "anki_tycoon_daily_again_count",
            "anki_tycoon_daily_again_date",
            "anki_tycoon_daily_again_penalty",
            "anki_tycoon_savings",
            "anki_tycoon_savings_timestamp",
            "anki_tycoon_active_boosts",
            "anki_tycoon_food_freshness",
            "anki_tycoon_reset_log",
            "anki_tycoon_last_tax_date",
            "anki_tycoon_tax_log",
        ])
    except Exception:
        _log_error("_migrate_none_keys")

def _on_profile_loaded():
    # Xoá flag reset nếu còn sót từ phiên trước (reset đã hoàn tất)
    try:
        from .reset_manager import clear_reset_flag
        clear_reset_flag()
    except Exception:
        pass

    _migrate_none_keys()

    # ── Quick Repair: tự động sửa lỗi dữ liệu nhẹ khi khởi động ──
    try:
        from .debug_tools import quick_repair
        qr = quick_repair()
        if qr.get("repaired"):
            print(f"[AnkiFinance][Debug] 🔧 Quick repair: {qr.get('details', 'ok')}")
    except Exception:
        pass

    # Tự động kiểm tra cập nhật từ GitHub (chạy thread nền)
    try:
        from .auto_update import auto_update_on_startup
        auto_update_on_startup()
    except Exception:
        pass

    _ensure_new_player()
    _inject_topbar()
    _collect_daily_tax()
    _collect_daily_living_costs()
    _accrue_loan_interest()
    _seed_knowledge()
    _auto_collect_rent()
    _update_stock_prices()
    _update_crypto_prices()
    _auto_collect_staking_yield()
    _check_inactivity_penalty()
    _check_emergency_event()
    _process_daily_credit_banking()
    _auto_collect_bond_coupon()

    # ── v1.1.3: Sửa passive effects cho crypto items đã mua trước khi có fix ──
    try:
        from .item_effects import repair_crypto_passive_effects
        repair_crypto_passive_effects()
    except Exception:
        pass

    # ── Economy Controls: thu phí đỗ xe garage hàng ngày ──
    _collect_garage_fees()


def _update_stock_prices():
    """Cập nhật giá chứng khoán khi mở app (nếu đã đến hạn)."""
    try:
        from .stock_market import update_prices_if_needed
        update_prices_if_needed()
    except Exception:
        _log_error("stock_market.update_prices_if_needed")


def _update_crypto_prices():
    """Cập nhật giá crypto khi mở app (nếu đã đến hạn)."""
    try:
        from .digital_assets import update_prices_if_needed
        update_prices_if_needed()
    except Exception:
        _log_error("digital_assets.update_prices_if_needed")


def _auto_collect_staking_yield():
    """Thu yield staking crypto tích lũy kể từ lần mở Anki trước."""
    try:
        from .digital_assets import collect_staking_yield
        result = collect_staking_yield()
        if result.get("ok") and result.get("yield_vnd", 0) > 0:
            from aqt.utils import tooltip
            tooltip(
                f"🏦 Crypto Staking — Yield: +{result['yield_vnd']:,}đ".replace(",", "."),
                period=3000
            )
    except Exception:
        _log_error("digital_assets.collect_staking_yield")


def _auto_collect_rent():
    """Thu tiền thuê BĐS tích lũy kể từ lần mở Anki trước."""
    try:
        from .real_estate import collect_all_rent
        result = collect_all_rent()
        if result.get("net", 0) > 0:
            from aqt.utils import tooltip
            tooltip(
                f"🏠 Anki Finance — Tiền thuê: +{result['net']:,}đ "
                f"(thuế: {result['tax']:,}đ)".replace(",","."),
                period=3000
            )
    except Exception:
        _log_error("real_estate.collect_all_rent")


def _seed_knowledge():
    """Seed bài học tài chính mặc định nếu chưa có note nào."""
    try:
        from .knowledge_base import seed_default_notes
        seed_default_notes()
    except Exception:
        _log_error("knowledge_base.seed_default_notes")


def _ensure_new_player():
    """Khởi tạo người chơi mới: 10 triệu VND + nhà trọ."""
    try:
        from .housing_residence import ensure_initialized
        ensure_initialized()
    except Exception:
        _log_error("housing_residence.ensure_initialized")


def _collect_daily_living_costs():
    """Thu chi phí sinh hoạt hàng ngày."""
    try:
        from .living_costs import collect_daily_living_costs
        result = collect_daily_living_costs()
        if result.get("collected"):
            from aqt.utils import tooltip
            total = result["total"]
            bd    = result["breakdown"]
            tooltip(
                f"🏠 Chi phí sinh hoạt hôm nay: -{total:,}đ "
                f"({bd['residence_name']}, {bd['cards_yesterday']} thẻ hôm qua)".replace(",", "."),
                period=4000
            )
            loan = result.get("loan", {})
            if loan.get("borrowed", 0) > 0:
                from aqt.utils import tooltip as tt
                tt(
                    f"⚠️ Hết tiền — vay nóng tự động: +{loan['borrowed']:,}đ "
                    f"(lãi 25%/tháng)".replace(",", "."),
                    period=5000
                )
    except Exception:
        _log_error("living_costs.collect_daily_living_costs")


def _accrue_loan_interest():
    """Cộng lãi khoản vay nóng hàng ngày."""
    try:
        from .loan_system import accrue_daily_interest
        result = accrue_daily_interest()
        if result.get("accrued", 0) > 0:
            from aqt.utils import tooltip
            tooltip(
                f"💸 Lãi vay nóng hôm nay: -{result['accrued']:,}đ "
                f"(tổng nợ: {result['new_total']:,}đ)".replace(",", "."),
                period=4000
            )
    except Exception:
        _log_error("loan_system.accrue_daily_interest")


def _check_inactivity_penalty():
    """Phí duy trì hệ thống: 10.000đ + 1% số dư/ngày vắng mặt (tối đa 5 ngày, tối đa 15% số dư)."""
    try:
        import time
        from ._safe_config import cfg_str, cfg_set
        today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
        _KEY = "anki_tycoon_last_login"
        last = cfg_str(_KEY, "")
        cfg_set(_KEY, today)
        if not last or last == today:
            return
        from datetime import datetime
        last_dt = datetime.fromisoformat(last)
        now_dt = datetime.fromtimestamp(time.time())
        gap = (now_dt.date() - last_dt.date()).days
        missed = max(0, gap - 1)
        if missed == 0:
            return
        from .balance import get_balance, set_balance
        from .transactions import add_transaction
        balance = get_balance()
        missed = min(missed, 7)  # tính phạt tối đa 7 ngày
        per_day = 10_000 + int(balance * 0.01)
        total = min(per_day * missed, int(balance * 0.15), 500_000)
        if total <= 0:
            return
        set_balance(max(0, balance - total))
        add_transaction("penalty", total,
                        f"🔧 Phí duy trì hệ thống — vắng {missed} ngày ({total:,}đ)".replace(",", "."))
        from aqt.utils import tooltip
        tooltip(f"🔧 Phí hệ thống {missed} ngày vắng mặt: -{total:,}đ".replace(",", "."), period=4000)
    except Exception:
        _log_error("inactivity_penalty")


def _check_emergency_event():
    """Kích hoạt sự kiện tài chính bất ngờ ngẫu nhiên (15%/ngày, tối đa 1 sự kiện/ngày)."""
    try:
        from .emergency_events import check_and_trigger_emergency
        check_and_trigger_emergency(mw)
    except Exception:
        _log_error("emergency_events.check_and_trigger_emergency")


def _process_daily_credit_banking():
    """Xử lý tự động hàng ngày cho credit banking (phí thẻ, quá hạn, điểm tín dụng)."""
    try:
        from .credit_banking import process_daily_banking
        result = process_daily_banking()
        # annual_fees: list of {card_id, fee, paid}
        annual_fees = result.get("annual_fees", [])
        if annual_fees:
            total_fee = sum(f.get("fee", 0) for f in annual_fees)
            from aqt.utils import tooltip
            tooltip(
                f"💳 Phí thường niên thẻ tín dụng đã được thu: "
                f"{total_fee:,}đ".replace(",", "."),
                period=4000
            )
        # late_penalties: dict {total_penalty, cards_penalized, count}
        late_pen = result.get("late_penalties", {})
        if late_pen and late_pen.get("total_penalty", 0) > 0:
            from aqt.utils import tooltip
            tooltip(
                f"⚠️ Phí phạt trễ hạn thẻ tín dụng: "
                f"{late_pen['total_penalty']:,}đ".replace(",", "."),
                period=4000
            )
        # overdue: dict {processed, details}
        overdue = result.get("overdue", {})
        if overdue and overdue.get("processed", 0) > 0:
            from aqt.utils import tooltip
            tooltip(
                f"🚨 Khoản vay bị quá hạn! Lãi phạt đã cộng. "
                f"Kiểm tra tab Ngân hàng nâng cao.",
                period=4000
            )
        # income_verify: dict {overall_level, verified_income, ...}
        income = result.get("income_verify", {})
        if income and income.get("overall_level", 0) > 0:
            from aqt.utils import tooltip
            tooltip(
                f"✅ Thu nhập đã được xác thực tự động. "
                f"Mức thu nhập: {income.get('verified_income', 0):,}₫/tháng • "
                f"Level {income.get('overall_level', 0)}".replace(",", "."),
                period=4000
            )
    except Exception:
        _log_error("credit_banking.process_daily_banking")


def _collect_daily_tax():
    """Thu thuế hàng ngày — gọi sau khi profile đã load xong."""
    try:
        from .tax_system import check_and_collect_tax
        result = check_and_collect_tax()
        if result.get("collected"):
            from aqt.utils import tooltip
            amt   = result['amount']
            rate  = result['rate_pct']
            tooltip(
                f"🏛️ Anki Finance — Thuế tài sản hôm nay: "
                f"{amt:,}đ ({rate:.1f}%/ngày)".replace(",", "."),
                period=4000
            )
    except Exception:
        _log_error("tax_system.check_and_collect_tax")


def _collect_garage_fees():
    """Thu phí đỗ xe garage hàng ngày."""
    try:
        from .economy_controls import collect_garage_fees
        result = collect_garage_fees()
        if result.get("collected") and result.get("total_fees", 0) > 0:
            seized = result.get("seized_vehicles", [])
            total = result["total_fees"]
            paid = result.get("paid", total)
            if seized:
                from aqt.utils import tooltip
                tooltip(
                    f"🚗 Phí đỗ xe garage: đã đóng {paid:,}đ • "
                    f"{len(seized)} xe bị niêm phong do thiếu tiền!".replace(",", "."),
                    period=5000
                )
            else:
                from aqt.utils import tooltip
                tooltip(
                    f"🚗 Phí đỗ xe garage: {paid:,}đ".replace(",", "."),
                    period=3000
                )
    except Exception:
        pass


def _auto_collect_bond_coupon():
    """Tự động thu coupon trái phiếu khi mở app (nếu đủ thẻ review)."""
    try:
        from .bond_system import process_coupon_payments
        result = process_coupon_payments()
        if result.get("ok") and result.get("total_coupon", 0) > 0:
            from aqt.utils import tooltip
            payments = result.get("payments", [])
            detail = " + ".join([f"{p['emoji']} {p['bond_name']}: {p['amount']:,}đ".replace(",", ".") for p in payments[:3]])
            if len(payments) > 3:
                detail += f" ... và {len(payments)-3} trái phiếu khác"
            tooltip(
                f"📜 Coupon trái phiếu: +{result['total_coupon']:,}đ\n{detail}".replace(",", "."),
                period=5000
            )
        # Kiểm tra đáo hạn
        from .bond_system import check_maturity
        maturity = check_maturity()
        if maturity.get("processed", 0) > 0:
            from aqt.utils import tooltip
            tooltip(
                f"📜 {maturity['processed']} trái phiếu đã đáo hạn! Nhận {maturity['total_proceeds']:,}đ".replace(",", "."),
                period=5000
            )
    except Exception:
        _log_error("bond_system._auto_collect_bond_coupon")


addHook("profileLoaded", _on_profile_loaded)

if mw.col:
    _on_profile_loaded()


# ── Menu ──────────────────────────────────────────────────────────
def _show_tycoon():
    win = TycoonWindow(mw)
    win.show()

action = QAction("🎓 Anki Finance", mw)
qconnect(action.triggered, _show_tycoon)
mw.form.menuTools.addAction(action)
