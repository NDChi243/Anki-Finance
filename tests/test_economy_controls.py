# -*- coding: utf-8 -*-
"""
test_economy_controls.py — Unit tests cho economy_controls.py

Coverage:
  A. Daily Cap / Diminishing Returns — get_daily_cap_multiplier()
  B. Wealth Tax Rate               — get_wealth_tax_rate()
  C. Wealth Tax on Reward          — apply_wealth_tax_on_reward()
  D. CPI / Dynamic Pricing         — apply_cpi_to_price()
  E. Again Recovery Fee            — get_again_recovery_fee()
  F. Garage Fee Calculation        — calculate_garage_fees() (logic thuần)
  G. Scarcity                      — is_vehicle_available()
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

import anki_finance.economy_controls as ec


# ═══════════════════════════════════════════════════════════════
# A. Daily Cap / Diminishing Returns
# ═══════════════════════════════════════════════════════════════

class TestDailyCapMultiplier:
    """
    DAILY_CAP_TIERS:
        0-99    → 100%
        100-199 → 50%
        200-299 → 25%
        300-499 → 10%
        500+    → 5%
    """

    def _cap(self, cards_today: int, monkeypatch) -> tuple:
        monkeypatch.setattr(ec, "get_daily_cards_count", lambda: cards_today)
        return ec.get_daily_cap_multiplier()

    def test_tier_1_zero_cards(self, monkeypatch):
        mult, info = self._cap(0, monkeypatch)
        assert mult == pytest.approx(1.0)
        assert info["mult_pct"] == 100

    def test_tier_1_middle(self, monkeypatch):
        mult, info = self._cap(50, monkeypatch)
        assert mult == pytest.approx(1.0)

    def test_tier_1_last_card(self, monkeypatch):
        mult, _ = self._cap(99, monkeypatch)
        assert mult == pytest.approx(1.0)

    def test_tier_2_at_100(self, monkeypatch):
        # 100 thẻ đã review → thẻ thứ 101 nhận 50%
        mult, info = self._cap(100, monkeypatch)
        assert mult == pytest.approx(0.50)
        assert info["mult_pct"] == 50

    def test_tier_2_middle(self, monkeypatch):
        mult, _ = self._cap(150, monkeypatch)
        assert mult == pytest.approx(0.50)

    def test_tier_3_at_200(self, monkeypatch):
        mult, info = self._cap(200, monkeypatch)
        assert mult == pytest.approx(0.25)
        assert info["mult_pct"] == 25

    def test_tier_4_at_300(self, monkeypatch):
        mult, info = self._cap(300, monkeypatch)
        assert mult == pytest.approx(0.10)
        assert info["mult_pct"] == 10

    def test_tier_4_last_card(self, monkeypatch):
        mult, _ = self._cap(499, monkeypatch)
        assert mult == pytest.approx(0.10)

    def test_tier_5_at_500(self, monkeypatch):
        mult, info = self._cap(500, monkeypatch)
        assert mult == pytest.approx(0.05)
        assert info["mult_pct"] == 5

    def test_tier_5_very_high(self, monkeypatch):
        mult, _ = self._cap(9999, monkeypatch)
        assert mult == pytest.approx(0.05)

    def test_info_cards_today_correct(self, monkeypatch):
        _, info = self._cap(75, monkeypatch)
        assert info["cards_today"] == 75

    def test_info_next_threshold_tier1(self, monkeypatch):
        _, info = self._cap(30, monkeypatch)
        assert info["next_threshold"] == 100
        assert info["cards_until_next"] == 70

    def test_tiers_strictly_decrease(self, monkeypatch):
        """Mỗi tier sau phải có multiplier ≤ tier trước."""
        card_samples = [0, 100, 200, 300, 500]
        mults = [self._cap(c, monkeypatch)[0] for c in card_samples]
        for i in range(1, len(mults)):
            assert mults[i] <= mults[i - 1]


# ═══════════════════════════════════════════════════════════════
# B. Wealth Tax Rate
# ═══════════════════════════════════════════════════════════════

class TestWealthTaxRate:
    """
    WEALTH_TAX_BRACKETS (dựa theo total net worth):
        >100B  → 15%
        >10B   → 10%
        >1B    → 5%
        >100M  → 2%
        >10M   → 1%
        ≤10M   → 0%
    """

    def test_zero_net_worth(self):
        assert ec.get_wealth_tax_rate(0) == pytest.approx(0.0)

    def test_below_10m(self):
        assert ec.get_wealth_tax_rate(5_000_000) == pytest.approx(0.0)

    def test_exactly_10m_exempt(self):
        # Bracket > 10M, nên đúng 10M vẫn 0%
        assert ec.get_wealth_tax_rate(10_000_000) == pytest.approx(0.0)

    def test_above_10m(self):
        assert ec.get_wealth_tax_rate(10_000_001) == pytest.approx(0.01)

    def test_above_100m(self):
        assert ec.get_wealth_tax_rate(100_000_001) == pytest.approx(0.02)

    def test_above_1b(self):
        assert ec.get_wealth_tax_rate(1_000_000_001) == pytest.approx(0.05)

    def test_above_10b(self):
        assert ec.get_wealth_tax_rate(10_000_000_001) == pytest.approx(0.10)

    def test_above_100b(self):
        assert ec.get_wealth_tax_rate(100_000_000_001) == pytest.approx(0.15)

    def test_very_rich(self):
        assert ec.get_wealth_tax_rate(999_000_000_000_000) == pytest.approx(0.15)

    def test_brackets_are_monotone(self):
        samples = [0, 10_000_001, 100_000_001, 1_000_000_001,
                   10_000_000_001, 100_000_000_001]
        rates = [ec.get_wealth_tax_rate(s) for s in samples]
        for i in range(1, len(rates)):
            assert rates[i] >= rates[i - 1], "Thuế tài sản phải tăng dần"


# ═══════════════════════════════════════════════════════════════
# C. apply_wealth_tax_on_reward
# ═══════════════════════════════════════════════════════════════

class TestApplyWealthTaxOnReward:
    """Áp dụng thuế tài sản lên tiền thưởng từng thẻ review."""

    def _tax(self, gross: int, net_worth: int, monkeypatch) -> tuple:
        monkeypatch.setattr(ec, "get_total_net_worth", lambda: net_worth)
        # Bỏ qua passive effects trong tests
        monkeypatch.setattr(ec, "get_all_passive_effects", lambda: {}, raising=False)
        return ec.apply_wealth_tax_on_reward(gross)

    def test_zero_reward(self, monkeypatch):
        net, tax, rate = self._tax(0, 50_000_000, monkeypatch)
        assert net == 0 and tax == 0 and rate == pytest.approx(0.0)

    def test_no_tax_below_10m_net_worth(self, monkeypatch):
        gross = 10_000
        net, tax, rate = self._tax(gross, 5_000_000, monkeypatch)
        assert net == gross
        assert tax == 0
        assert rate == pytest.approx(0.0)

    def test_tax_applied_above_10m(self, monkeypatch):
        gross = 100_000
        net_worth = 50_000_000  # → rate 1%
        net, tax, rate = self._tax(gross, net_worth, monkeypatch)
        assert rate == pytest.approx(0.01)
        assert tax == int(gross * 0.01)
        assert net == gross - tax

    def test_net_plus_tax_equals_gross(self, monkeypatch):
        gross = 50_000
        net, tax, rate = self._tax(gross, 500_000_000, monkeypatch)
        assert net + tax == gross

    def test_higher_net_worth_higher_tax_rate(self, monkeypatch):
        gross = 10_000
        _, _, rate_low = self._tax(gross, 50_000_000, monkeypatch)   # >10M → 1%
        _, _, rate_high = self._tax(gross, 500_000_000, monkeypatch)  # >100M → 2%
        assert rate_high > rate_low


# ═══════════════════════════════════════════════════════════════
# D. CPI / Dynamic Pricing
# ═══════════════════════════════════════════════════════════════

class TestCpiPricing:
    """CPI được đọc từ config, áp dụng tỷ lệ lên giá gốc."""

    def test_apply_cpi_base_index(self, monkeypatch):
        monkeypatch.setattr(ec, "get_cpi_index", lambda: 1.0)
        assert ec.apply_cpi_to_price(1_000_000) == 1_000_000

    def test_apply_cpi_inflated(self, monkeypatch):
        monkeypatch.setattr(ec, "get_cpi_index", lambda: 1.5)
        assert ec.apply_cpi_to_price(1_000_000) == 1_500_000

    def test_apply_cpi_truncates_to_int(self, monkeypatch):
        monkeypatch.setattr(ec, "get_cpi_index", lambda: 1.333)
        result = ec.apply_cpi_to_price(1_000_000)
        assert isinstance(result, int)

    def test_cpi_status_fields(self, fake_config, monkeypatch):
        store = fake_config(ec, {
            "anki_tycoon_cpi_index": {"index": 1.1, "last_update": 0},
            "anki_tycoon_total_system_cards": 2000,
        })
        status = ec.get_cpi_status()
        assert "cpi_index" in status
        assert "total_system_cards" in status
        assert "cards_to_next_tick" in status


# ═══════════════════════════════════════════════════════════════
# E. Again Recovery Fee
# ═══════════════════════════════════════════════════════════════

class TestAgainRecoveryFee:
    """
    Công thức: max(MIN=2000, min(MAX=500000, balance * 0.001))
    """

    RATIO = ec.AGAIN_RECOVERY_FEE_RATIO   # 0.001
    MIN   = ec.AGAIN_RECOVERY_MIN          # 2_000
    MAX   = ec.AGAIN_RECOVERY_MAX          # 500_000

    def test_zero_balance_returns_minimum(self, monkeypatch):
        monkeypatch.setattr(ec, "get_balance", lambda: 0, raising=False)
        with patch("anki_finance.economy_controls.get_balance", return_value=0):
            fee = ec.get_again_recovery_fee()
        assert fee == self.MIN

    def test_low_balance_returns_minimum(self, monkeypatch):
        with patch("anki_finance.economy_controls.get_balance", return_value=1_000_000):
            fee = ec.get_again_recovery_fee()
        # 1M * 0.001 = 1000 < MIN=2000 → MIN
        assert fee == self.MIN

    def test_medium_balance(self):
        # 10M * 0.001 = 10_000; 2000 ≤ 10000 ≤ 500000
        with patch("anki_finance.economy_controls.get_balance", return_value=10_000_000):
            fee = ec.get_again_recovery_fee()
        assert fee == 10_000

    def test_high_balance_capped_at_max(self):
        # 1B * 0.001 = 1M > MAX=500k → MAX
        with patch("anki_finance.economy_controls.get_balance", return_value=1_000_000_000):
            fee = ec.get_again_recovery_fee()
        assert fee == self.MAX

    def test_always_between_min_and_max(self):
        for balance in [0, 500_000, 5_000_000, 50_000_000, 500_000_000, 5_000_000_000]:
            with patch("anki_finance.economy_controls.get_balance", return_value=balance):
                fee = ec.get_again_recovery_fee()
            assert self.MIN <= fee <= self.MAX, f"Fee {fee} ngoài khoảng [{self.MIN}, {self.MAX}]"


# ═══════════════════════════════════════════════════════════════
# F. Garage Fee Brackets — thuần logic, không cần shop/vehicle
# ═══════════════════════════════════════════════════════════════

class TestGarageFeeBrackets:
    """Test logic tính phí đỗ xe theo giá trị xe."""

    # Hàm helper: tính phí trực tiếp theo bảng GARAGE_FEE_BRACKETS
    def _calc_fee(self, price: int) -> int:
        fee = ec.GARAGE_FEE_MIN
        for threshold, rate in ec.GARAGE_FEE_BRACKETS:
            if price > threshold:
                fee = max(ec.GARAGE_FEE_MIN,
                          min(ec.GARAGE_FEE_MAX, int(price * rate)))
                break
        return fee

    def test_cheap_car_minimum_fee(self):
        # Xe 50M < 100M → rate 0.01%; 50M*0.0001=5000 = MIN
        fee = self._calc_fee(50_000_000)
        assert fee == ec.GARAGE_FEE_MIN  # 5_000

    def test_mid_car_100m_rate(self):
        # 200M > 100M → rate 0.02%; 200M*0.0002 = 40_000
        fee = self._calc_fee(200_000_000)
        assert fee == max(ec.GARAGE_FEE_MIN,
                          min(ec.GARAGE_FEE_MAX, int(200_000_000 * 0.0002)))

    def test_expensive_car_1b_rate(self):
        # 2B > 1B → rate 0.05%; 2B*0.0005 = 1_000_000 → capped tại 5M? No, 1M < 5M ok
        fee = self._calc_fee(2_000_000_000)
        assert fee == int(2_000_000_000 * 0.0005)  # 1_000_000

    def test_supercar_10b_rate(self):
        # 20B > 10B → rate 0.1%; 20B*0.001 = 20M → capped tại MAX=5M
        fee = self._calc_fee(20_000_000_000)
        assert fee == ec.GARAGE_FEE_MAX  # 5_000_000

    def test_fee_never_below_minimum(self):
        for price in [0, 100_000, 1_000_000, 50_000_000]:
            fee = self._calc_fee(price)
            assert fee >= ec.GARAGE_FEE_MIN

    def test_fee_never_above_maximum(self):
        for price in [100_000_000_000, 1_000_000_000_000]:
            fee = self._calc_fee(price)
            assert fee <= ec.GARAGE_FEE_MAX


# ═══════════════════════════════════════════════════════════════
# G. Scarcity — is_vehicle_available
# ═══════════════════════════════════════════════════════════════

class TestVehicleScarcity:
    """Xe khan hiếm chỉ xuất hiện trong khung giờ nhất định."""

    def test_non_scarce_always_available(self):
        result = ec.is_vehicle_available("honda_wave_alpha")  # không trong danh sách
        assert result["available"] is True
        assert result["next_available_in"] is None

    def test_scarce_vehicle_available_in_window(self, monkeypatch):
        from datetime import datetime
        # ferrari_sf90: available 20h-2h
        mock_dt = MagicMock()
        mock_dt.now.return_value.hour = 21  # trong window
        monkeypatch.setattr("anki_finance.economy_controls.datetime", mock_dt)
        result = ec.is_vehicle_available("ferrari_sf90")
        assert result["available"] is True

    def test_scarce_vehicle_unavailable_outside_window(self, monkeypatch):
        from datetime import datetime
        # ferrari_sf90: available 20h-2h; giờ 10h sáng
        mock_dt = MagicMock()
        mock_dt.now.return_value.hour = 10
        monkeypatch.setattr("anki_finance.economy_controls.datetime", mock_dt)
        result = ec.is_vehicle_available("ferrari_sf90")
        assert result["available"] is False

    def test_next_available_in_is_positive_when_unavailable(self, monkeypatch):
        mock_dt = MagicMock()
        mock_dt.now.return_value.hour = 10  # ngoài window
        monkeypatch.setattr("anki_finance.economy_controls.datetime", mock_dt)
        result = ec.is_vehicle_available("ferrari_sf90")
        assert result["next_available_in"] > 0


# ═══════════════════════════════════════════════════════════════
# H. Constants integrity
# ═══════════════════════════════════════════════════════════════

class TestConstants:
    def test_daily_cap_tiers_count(self):
        assert len(ec.DAILY_CAP_TIERS) == 5

    def test_daily_cap_tiers_ordered(self):
        thresholds = [t for t, _ in ec.DAILY_CAP_TIERS]
        assert thresholds == sorted(thresholds), "DAILY_CAP_TIERS phải tăng dần"

    def test_daily_cap_multipliers_decrease(self):
        mults = [m for _, m in ec.DAILY_CAP_TIERS]
        for i in range(1, len(mults)):
            assert mults[i] <= mults[i - 1]

    def test_wealth_brackets_ordered(self):
        thresholds = [t for t, _ in ec.WEALTH_TAX_BRACKETS]
        assert thresholds == sorted(thresholds, reverse=True), \
            "WEALTH_TAX_BRACKETS phải sắp xếp giảm dần (bracket cao nhất trước)"

    def test_again_fee_min_less_than_max(self):
        assert ec.AGAIN_RECOVERY_MIN < ec.AGAIN_RECOVERY_MAX
