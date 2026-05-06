# -*- coding: utf-8 -*-
from __future__ import annotations

from aqt import mw
from .config import CONFIG_KEY_BALANCE, CONFIG_KEY_STATS, REWARD_MAP
from ._safe_config import col_ready, cfg_int, cfg_dict, cfg_set
from .logger import get_logger

logger = get_logger(__name__)


def get_balance() -> int:
    return cfg_int(CONFIG_KEY_BALANCE, 0)


def set_balance(amount: int) -> None:
    """Cập nhật số dư ví."""
    new_bal = int(amount)
    cfg_set(CONFIG_KEY_BALANCE, new_bal)
    _refresh_topbar()
    _check_balance_dropped(new_bal)


def set_balance_and_log(amount: int, txn_type: str, txn_amount: int,
                        description: str = "") -> None:
    """Set balance + ghi transaction history."""
    new_bal = int(amount)
    cfg_set(CONFIG_KEY_BALANCE, new_bal)
    _refresh_topbar()
    # Ghi nhận tiền thưởng cho quest earn_money (chỉ khi là reward và amount > 0)
    if txn_type == "reward" and txn_amount and txn_amount > 0:
        try:
            from .daily_quest import record_earn_money
            record_earn_money(int(txn_amount))
        except Exception as e:
            logger.debug("set_balance_and_log: record_earn_money — %s", e)
    _check_balance_dropped(new_bal)


def _check_balance_dropped(new_bal: int) -> None:
    """Trigger achievement ẩn 'Về 0' khi balance < 1.000đ."""
    if new_bal >= 1000:
        return
    try:
        from .achievements import check_and_unlock
        check_and_unlock("balance_dropped", True)
    except Exception as e:
        logger.debug("_check_balance_dropped: %s", e)


def _consume_energy_and_stamina() -> float:
    """
    Tiêu hao năng lượng khi review, áp dụng shield/reduce/regen từ boosts.
    Tích hợp % tiết kiệm năng lượng từ xe đang active (v1.1.5b).
    Trả về energy_multiplier (1.0 nếu còn NL, 0.5 nếu kiệt sức).
    """
    try:
        import random
        from .energy_system import consume_energy_with_vehicle, restore_energy, get_reward_multiplier_from_energy
        from .food_effects import get_active_boosts

        boosts = get_active_boosts()
        energy_shield = False
        energy_reduce = 1.0  # 1.0 = bình thường, 0.5 = 50% xác suất tốn NL/thẻ

        # Pass 1: kiểm tra shield và reduce
        for b in boosts:
            effect_list = b.get("effect_list", [])
            if not effect_list:
                effect_list = [b]
            for eff in effect_list:
                etype = eff.get("type", b.get("type", ""))
                val   = eff.get("value", b.get("value", 0)) or 0
                if etype == "energy_shield":
                    energy_shield = True
                elif etype == "energy_reduce":
                    energy_reduce = min(energy_reduce, float(val))

        # Lấy % tiết kiệm năng lượng từ xe đang active
        vehicle_save = 0.0
        try:
            from .vehicle_system import get_active_vehicle
            av = get_active_vehicle()
            if av:
                vehicle_save = float(av.get("energy_save_percent", 0.0))
        except Exception:
            pass

        # Tiêu hao năng lượng (có thể bị shield hoặc giảm xác suất)
        if not energy_shield:
            if energy_reduce >= 1.0 or random.random() < energy_reduce:
                # Dùng consume_energy_with_vehicle để áp dụng % tiết kiệm từ xe
                consume_energy_with_vehicle(amount=1, vehicle_energy_save=vehicle_save)

        # Pass 2: hồi năng lượng từ stamina_regen / energy_regen
        for b in boosts:
            effect_list = b.get("effect_list", [])
            if not effect_list:
                effect_list = [b]
            for eff in effect_list:
                etype = eff.get("type", b.get("type", ""))
                if etype in ("stamina_regen", "energy_regen"):
                    val = int(eff.get("value", b.get("value", 0)) or 0)
                    if val > 0:
                        restore_energy(val)

        return get_reward_multiplier_from_energy()
    except Exception as e:
        logger.warning("_consume_energy_and_stamina: %s", e)
        return 1.0


def _apply_food_penalties(boost_info: dict) -> None:
    """
    v1.0.7 — Áp dụng trade-off penalties từ food/drink boosts.
    - stamina_cost: tiêu hao thêm thể lực (năng lượng)
    """
    try:
        from .energy_system import consume_energy
        stamina = int(boost_info.get("stamina_cost", 0) or 0)
        if stamina > 0:
            consume_energy(stamina)
    except Exception as e:
        logger.warning("_apply_food_penalties: %s", e)


def _apply_reward_penalty(reward: int, boost_info: dict) -> int:
    """
    v1.0.7 — Áp dụng reward_penalty từ food/drink trade-offs.
    reward_penalty = 0.1 means -10% tiền thưởng.
    """
    penalty_pct = float(boost_info.get("reward_penalty", 0.0) or 0.0)
    if penalty_pct > 0:
        reduction = int(reward * penalty_pct)
        reward = max(0, reward - reduction)
    return reward


def add_reward(ease: int) -> dict:
    if not col_ready():
        return {"rewarded": False, "penalized": False, "penalty": 0, "message": ""}

    from .transactions import add_transaction
    from .finance import reset_monthly_if_needed

    reset_monthly_if_needed()

    # ── Load passive effects (xp_multiplier từ xe/luxury/tech/BĐS) ──
    try:
        from .item_effects import get_all_passive_effects
        _passive = get_all_passive_effects()
        passive_xp_mult = float(_passive.get("xp_multiplier", 1.0))
    except Exception as e:
        logger.warning("add_reward: passive_xp_mult — %s", e)
        passive_xp_mult = 1.0

    # ── KN Perks: reward_mult (buff tiền thưởng vĩnh viễn) ──
    try:
        from .kn_perks import get_active_bonuses
        _kn_bonus = get_active_bonuses()
        kn_reward_mult = 1.0 + float(_kn_bonus.get("reward_mult", 0.0))
    except Exception as e:
        logger.warning("add_reward: kn_perks reward_mult — %s", e)
        kn_reward_mult = 1.0

    # ── Tiêu hao năng lượng + áp dụng stamina_regen ──
    energy_mult = _consume_energy_and_stamina()

    # ── Load các hàm kiểm soát kinh tế ──
    try:
        from .economy_controls import (
            get_daily_cap_multiplier,
            apply_wealth_tax_on_reward,
            get_again_recovery_fee,
            increment_daily_cards_count,
            increment_total_system_cards,
        )
        econ_available = True
    except Exception as e:
        logger.warning("add_reward: economy_controls — %s", e)
        econ_available = False

    if ease == 1:
        from .again_tracker import record_again

        # Kiểm tra shield (no_again_penalty) từ active boosts TRƯỚC khi phạt
        boost_info = {"multiplier": 1.0, "bonus": 0, "shield": False,
                      "stamina_cost": 0, "reward_penalty": 0.0}
        try:
            from .food_effects import consume_boost_card
            boost_info = consume_boost_card(1)
        except Exception as e:
            logger.warning("add_reward(again): consume_boost_card — %s", e)

        # Áp dụng trade-off penalties từ food/drink
        _apply_food_penalties(boost_info)

        has_shield = bool(boost_info.get("shield", False))

        if has_shield:
            # Có khiên: vẫn thưởng nhẹ, không phạt
            reward = REWARD_MAP.get(1, 500)
            final_reward = int(reward * boost_info["multiplier"] * passive_xp_mult * energy_mult * kn_reward_mult) + int(boost_info["bonus"])
            final_reward = _apply_reward_penalty(final_reward, boost_info)

            # ── Daily cap multiplier ──
            if econ_available:
                cap_mult, _ = get_daily_cap_multiplier()
                final_reward = int(final_reward * cap_mult)
                # Wealth tax
                final_reward, wealth_tax_amount, wealth_tax_rate = apply_wealth_tax_on_reward(final_reward)
            else:
                wealth_tax_amount = 0

            final_reward = _apply_loan_repay(final_reward)
            net_income, pit_withheld = _apply_pit_withholding(final_reward)
            new_bal = get_balance() + net_income
            set_balance_and_log(new_bal, "reward", final_reward, "Học tập — Again (🛡️ khiên)")
            _update_stats(ease, final_reward)
            add_transaction("reward", final_reward, "Học tập — Again (🛡️ khiên)")
            if pit_withheld > 0:
                add_transaction("pit_withholding", pit_withheld, "Khấu trừ tạm thời thuế TNCN")
            net_str = f"{net_income:,}đ".replace(",", ".")
            return {"count": 0, "rewarded": True, "penalized": False,
                    "penalty": 0, "shielded": True, "boost": boost_info,
                    "message": f"🛡️ Khiên chống Again! +{net_str}"}

        # Không có khiên — xử lý phạt Again bình thường
        result = record_again()
        if result.get("rewarded"):
            reward = REWARD_MAP.get(1, 0)
            final_reward = int(reward * boost_info["multiplier"] * passive_xp_mult * energy_mult * kn_reward_mult) + int(boost_info["bonus"])
            final_reward = _apply_reward_penalty(final_reward, boost_info)

            # ── Daily cap multiplier ──
            if econ_available:
                cap_mult, _ = get_daily_cap_multiplier()
                final_reward = int(final_reward * cap_mult)
                # Wealth tax
                final_reward, wealth_tax_amount, wealth_tax_rate = apply_wealth_tax_on_reward(final_reward)
            else:
                wealth_tax_amount = 0

            final_reward = _apply_loan_repay(final_reward)

            # ── Phí phục hồi kiến thức Again ──
            again_fee = 0
            if econ_available and final_reward > 0:
                again_fee = get_again_recovery_fee()
                again_fee = min(again_fee, final_reward)
                final_reward -= again_fee
            else:
                again_fee = 0

            net_income, pit_withheld = _apply_pit_withholding(final_reward)
            new_bal = get_balance() + net_income
            set_balance_and_log(new_bal, "reward", final_reward, "Học tập — Again")
            _update_stats(ease, final_reward)
            add_transaction("reward", final_reward, "Học tập — Again")
            if pit_withheld > 0:
                add_transaction("pit_withholding", pit_withheld, "Khấu trừ tạm thời thuế TNCN")
            if again_fee > 0:
                add_transaction("again_recovery_fee", again_fee,
                                f"Phí phục hồi kiến thức Again: {again_fee:,}đ".replace(",", "."))
        result["boost"] = boost_info
        return result
    else:
        reward = REWARD_MAP.get(ease, 0)
        if reward <= 0:
            return {"rewarded": False, "penalized": False, "penalty": 0, "message": ""}

        boost_info = {"multiplier": 1.0, "bonus": 0, "shield": False,
                      "stamina_cost": 0, "reward_penalty": 0.0}
        try:
            from .food_effects import consume_boost_card
            boost_info = consume_boost_card(ease)
        except Exception as e:
            logger.warning("add_reward(ease=%s): consume_boost_card — %s", ease, e)

        # Áp dụng trade-off penalties từ food/drink (trước khi tính thưởng)
        _apply_food_penalties(boost_info)

        # Áp dụng CẢ active boost + passive xp_multiplier + energy_multiplier
        final_reward = int(reward * boost_info["multiplier"] * passive_xp_mult * energy_mult * kn_reward_mult) + int(boost_info["bonus"])
        # Áp dụng reward_penalty (giảm % tiền thưởng từ food trade-off)
        final_reward = _apply_reward_penalty(final_reward, boost_info)

        # ── Daily cap multiplier (diminishing returns) ──
        daily_cap_info = {}
        if econ_available:
            cap_mult, cap_info = get_daily_cap_multiplier()
            daily_cap_info = cap_info
            final_reward = int(final_reward * cap_mult)
            # ── Wealth tax ──
            final_reward, wealth_tax_amount, wealth_tax_rate = apply_wealth_tax_on_reward(final_reward)
        else:
            wealth_tax_amount = 0

        final_reward = _apply_loan_repay(final_reward)
        net_income, pit_withheld = _apply_pit_withholding(final_reward)
        new_bal = get_balance() + net_income

        parts = []
        if boost_info["multiplier"] != 1.0:
            parts.append(f"×{boost_info['multiplier']:.1f} boost")
        if passive_xp_mult != 1.0:
            parts.append(f"×{passive_xp_mult:.1f} passive")
        if energy_mult < 1.0:
            parts.append(f"×{energy_mult:.1f} kiệt sức")
        if boost_info["bonus"] > 0:
            parts.append(f"+{boost_info['bonus']:,}đ bonus".replace(",", "."))
        penalty_pct = float(boost_info.get("reward_penalty", 0.0) or 0.0)
        if penalty_pct > 0:
            parts.append(f"-{int(penalty_pct*100)}% phạt")
        if econ_available and daily_cap_info.get("multiplier", 1.0) < 1.0:
            parts.append(f"×{daily_cap_info['mult_pct']}% daily cap")
        if wealth_tax_amount > 0:
            parts.append(f"-{wealth_tax_amount:,}đ thuế".replace(",", "."))
        boost_str = f" ({', '.join(parts)})" if parts else ""

        desc = f"Học tập — ease {ease}{boost_str}"
        set_balance_and_log(new_bal, "reward", final_reward, desc)
        _update_stats(ease, final_reward)
        add_transaction("reward", final_reward, desc)
        if pit_withheld > 0:
            add_transaction("pit_withholding", pit_withheld, "Khấu trừ tạm thời thuế TNCN")

        msg = f"+{net_income:,}đ{boost_str}".replace(",", ".")
        if pit_withheld > 0:
            tax_str = f"{pit_withheld:,}đ".replace(",", ".")
            msg += f" (thuế: -{tax_str})"
        return {"rewarded": True, "penalized": False, "penalty": 0,
                "boost": boost_info,
                "passive_xp_mult": passive_xp_mult,
                "energy_mult": energy_mult,
                "pit_withheld": pit_withheld,
                "message": msg}


def _update_stats(ease: int, reward: int) -> None:
    stats = get_stats()
    stats["total_earned"]   = int(stats.get("total_earned", 0) or 0) + reward
    stats["cards_reviewed"] = int(stats.get("cards_reviewed", 0) or 0) + 1
    stats[f"ease_{ease}"]   = int(stats.get(f"ease_{ease}", 0) or 0) + 1
    set_stats(stats)
    # Ghi nhận thẻ cho giảm trừ thuế TNCN
    try:
        from .tax_system import record_monthly_card
        record_monthly_card()
    except Exception as e:
        logger.warning("_update_stats: record_monthly_card — %s", e)


def record_purchase(amount: int, item_name: str = "") -> None:
    if not col_ready():
        return
    from .transactions import add_transaction
    stats = get_stats()
    stats["total_spent"] = int(stats.get("total_spent", 0) or 0) + int(amount)
    set_stats(stats)
    if item_name:
        add_transaction("purchase", int(amount), f"Mua: {item_name}")


def get_stats() -> dict:
    default = {"total_earned": 0, "total_spent": 0, "cards_reviewed": 0,
               "ease_1": 0, "ease_2": 0, "ease_3": 0, "ease_4": 0}
    s = cfg_dict(CONFIG_KEY_STATS, default)
    for k, v in default.items():
        if k not in s or s[k] is None:
            s[k] = v
    return s


def set_stats(stats: dict) -> None:
    cfg_set(CONFIG_KEY_STATS, stats)


def _apply_pit_withholding(gross_income: int) -> tuple[int, int]:
    """
    Khấu trừ thuế TNCN tạm thời trên gross_income.
    Trả về (net_income, pit_withheld).
    """
    try:
        from .tax_system import apply_pit_withholding_on_income
        result = apply_pit_withholding_on_income(gross_income)
        pit = result.get("withheld", 0)
        return gross_income - pit, pit
    except Exception as e:
        logger.warning("_apply_pit_withholding: %s", e)
        return gross_income, 0


def _apply_loan_repay(reward: int) -> int:
    """Nếu đang nợ, dùng tiền thưởng trả nợ trước. Trả về phần còn lại."""
    try:
        from .loan_system import get_loan_info, repay_from_reward
        if get_loan_info()["has_loan"]:
            res = repay_from_reward(reward)
            return res["remaining"]
    except Exception as e:
        logger.warning("_apply_loan_repay: %s", e)
    return reward


def _refresh_topbar() -> None:
    try:
        if hasattr(mw, "tycoon_topbar") and mw.tycoon_topbar:
            mw.tycoon_topbar.refresh()
            # Đồng bộ webview nếu cửa sổ đang mở
            win = getattr(mw.tycoon_topbar, "_window", None)
            if win and hasattr(win, "bridge"):
                win.bridge.balanceChanged.emit(get_balance())
    except Exception as e:
        logger.warning("_refresh_topbar: %s", e)
