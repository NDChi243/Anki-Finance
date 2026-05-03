# -*- coding: utf-8 -*-
"""
test_tax_system.py — Unit tests cho tax_system.py

Coverage:
  A. get_tax_rate()          — tra bảng thuế tài sản theo thu nhập
  B. calculate_tax()         — tính thuế tài sản + ngưỡng miễn
  C. _calc_pit_progressive() — thuế TNCN lũy tiến 5 bậc
  D. calculate_pit()         — TNCN đầy đủ (giảm trừ cá nhân + học tập)
  E. calculate_incremental_pit() — khấu trừ tạm thời (withholding)
  F. get_sct_for_item()      — thuế tiêu thụ đặc biệt theo category
  G. apply_pit_withholding_on_income() — withholding flow
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

import anki_finance.tax_system as ts


# ═══════════════════════════════════════════════════════════════
# A. get_tax_rate
# ═══════════════════════════════════════════════════════════════

class TestGetTaxRate:
    """Tra bảng TAX_BRACKETS theo thu nhập tháng."""

    def test_zero_income(self):
        assert ts.get_tax_rate(0) == pytest.approx(0.001)

    def test_below_1m(self):
        assert ts.get_tax_rate(500_000) == pytest.approx(0.001)

    def test_exactly_1m_not_above(self):
        # Bracket "> 1M" nên đúng 1M vẫn là 0.001
        assert ts.get_tax_rate(1_000_000) == pytest.approx(0.001)

    def test_above_1m(self):
        assert ts.get_tax_rate(1_000_001) == pytest.approx(0.002)

    def test_above_5m(self):
        assert ts.get_tax_rate(5_000_001) == pytest.approx(0.003)

    def test_exactly_5m_not_above(self):
        assert ts.get_tax_rate(5_000_000) == pytest.approx(0.002)

    def test_above_20m(self):
        assert ts.get_tax_rate(20_000_001) == pytest.approx(0.004)

    def test_above_100m(self):
        assert ts.get_tax_rate(100_000_001) == pytest.approx(0.005)

    def test_very_high_income(self):
        assert ts.get_tax_rate(1_000_000_000) == pytest.approx(0.005)


# ═══════════════════════════════════════════════════════════════
# B. calculate_tax
# ═══════════════════════════════════════════════════════════════

class TestCalculateTax:
    """Tính thuế tài sản hàng ngày (cần total_assets > TAX_THRESHOLD)."""

    @pytest.fixture(autouse=True)
    def no_tax_reduction(self, monkeypatch):
        # Loại bỏ passive effect → factor = 1.0
        monkeypatch.setattr(ts, "_get_tax_reduction_factor", lambda: 1.0)

    def test_below_threshold_not_taxable(self):
        result = ts.calculate_tax(5_000_000, 0)
        assert result["taxable"] is False
        assert result["amount"] == 0

    def test_exactly_threshold_not_taxable(self):
        # TAX_THRESHOLD = 10_000_000; điều kiện là >
        result = ts.calculate_tax(10_000_000, 0)
        assert result["taxable"] is False

    def test_above_threshold_taxable(self):
        result = ts.calculate_tax(10_000_001, 0)
        assert result["taxable"] is True

    def test_amount_calculation_low_income(self):
        # income=0 → rate=0.001; assets=50M
        result = ts.calculate_tax(50_000_000, 0)
        assert result["taxable"] is True
        assert result["rate"] == pytest.approx(0.001)
        assert result["amount"] == round(50_000_000 * 0.001)  # 50_000

    def test_amount_calculation_high_income(self):
        # income>100M → rate=0.005; assets=200M
        result = ts.calculate_tax(200_000_000, 150_000_000)
        assert result["rate"] == pytest.approx(0.005)
        assert result["amount"] == round(200_000_000 * 0.005)  # 1_000_000

    def test_rate_pct_field(self):
        result = ts.calculate_tax(50_000_000, 1_000_001)
        assert result["rate_pct"] == pytest.approx(0.2)

    def test_tax_reduction_applied(self, monkeypatch):
        # Override fixture: giảm 50%
        monkeypatch.setattr(ts, "_get_tax_reduction_factor", lambda: 0.5)
        full = ts.calculate_tax(50_000_000, 0)
        # amount phải bằng 50% so với không giảm
        expected = round(round(50_000_000 * 0.001) * 0.5)
        assert full["amount"] == expected


# ═══════════════════════════════════════════════════════════════
# C. _calc_pit_progressive — 5 bậc thuế TNCN 2026
# ═══════════════════════════════════════════════════════════════

class TestCalcPitProgressive:
    """Hàm thuần túy, không cần mock."""

    def test_zero_taxable(self):
        assert ts._calc_pit_progressive(0) == 0

    def test_bac1_partial(self):
        # 5M nằm trong bậc 1 (≤10M, rate 5%)
        assert ts._calc_pit_progressive(5_000_000) == round(5_000_000 * 0.05)  # 250_000

    def test_bac1_full(self):
        # Đúng 10M → chỉ bậc 1
        assert ts._calc_pit_progressive(10_000_000) == round(10_000_000 * 0.05)  # 500_000

    def test_bac2(self):
        # 20M = 10M (bậc 1) + 10M (bậc 2)
        expected = round(10_000_000 * 0.05) + round(10_000_000 * 0.10)
        assert ts._calc_pit_progressive(20_000_000) == expected  # 1_500_000

    def test_bac3(self):
        # 50M = 10M + 20M + 20M (bậc 3)
        expected = (
            round(10_000_000 * 0.05)   # 500_000
            + round(20_000_000 * 0.10) # 2_000_000
            + round(20_000_000 * 0.20) # 4_000_000
        )
        assert ts._calc_pit_progressive(50_000_000) == expected  # 6_500_000

    def test_bac4(self):
        # 100M = bậc 1+2+3 + 40M bậc 4 (đúng ranh giới, chưa vào bậc 5)
        expected = (
            round(10_000_000 * 0.05)   # 500_000
            + round(20_000_000 * 0.10) # 2_000_000
            + round(30_000_000 * 0.20) # 6_000_000
            + round(40_000_000 * 0.30) # 12_000_000
        )
        assert ts._calc_pit_progressive(100_000_000) == expected  # 20_500_000

    def test_bac5(self):
        # 110M = bậc 1+2+3+4 + 10M bậc 5
        expected = (
            round(10_000_000 * 0.05)
            + round(20_000_000 * 0.10)
            + round(30_000_000 * 0.20)
            + round(40_000_000 * 0.30)
            + round(10_000_000 * 0.35)  # 3_500_000
        )
        assert ts._calc_pit_progressive(110_000_000) == expected  # 24_000_000

    def test_is_progressive_not_flat(self):
        # Thuế lũy tiến: thuế 20M > 10M * 2
        tax_10m = ts._calc_pit_progressive(10_000_000)
        tax_20m = ts._calc_pit_progressive(20_000_000)
        assert tax_20m > tax_10m * 2


# ═══════════════════════════════════════════════════════════════
# D. calculate_pit
# ═══════════════════════════════════════════════════════════════

class TestCalculatePit:
    """Tính TNCN đầy đủ: giảm trừ cá nhân 15.5M + giảm trừ học tập."""

    @pytest.fixture(autouse=True)
    def no_tax_reduction(self, monkeypatch):
        monkeypatch.setattr(ts, "_get_tax_reduction_factor", lambda: 1.0)

    def test_income_below_personal_deduction_no_tax(self):
        # 15M < 15.5M → taxable = 0
        result = ts.calculate_pit(15_000_000, 0)
        assert result["tax"] == 0
        assert result["taxable_income"] == 0

    def test_income_exactly_personal_deduction_no_tax(self):
        result = ts.calculate_pit(15_500_000, 0)
        assert result["tax"] == 0

    def test_income_above_personal_deduction(self):
        # 20M - 15.5M = 4.5M taxable @ bậc 1 (5%)
        result = ts.calculate_pit(20_000_000, 0)
        assert result["taxable_income"] == 4_500_000
        assert result["tax"] == round(4_500_000 * 0.05)  # 225_000

    def test_study_deduction_reduces_tax(self):
        # 1000 thẻ × 1000đ = 1M giảm trừ học tập
        result_no_cards = ts.calculate_pit(20_000_000, 0)
        result_with_cards = ts.calculate_pit(20_000_000, 1000)
        assert result_with_cards["tax"] < result_no_cards["tax"]
        assert result_with_cards["study_deduction"] == 1_000_000

    def test_study_deduction_capped_at_5m(self):
        # 10000 thẻ = 10M → capped tại 5M
        result = ts.calculate_pit(50_000_000, 10_000)
        assert result["study_deduction"] == 5_000_000

    def test_study_deduction_5001_cards_still_capped(self):
        result_5000 = ts.calculate_pit(50_000_000, 5000)
        result_5001 = ts.calculate_pit(50_000_000, 5001)
        assert result_5000["study_deduction"] == 5_000_000
        assert result_5001["study_deduction"] == 5_000_000
        assert result_5000["tax"] == result_5001["tax"]

    def test_effective_rate_pct_field(self):
        result = ts.calculate_pit(20_000_000, 0)
        expected_rate = result["tax"] / 20_000_000 * 100
        assert result["rate_eff_pct"] == pytest.approx(expected_rate, abs=0.01)

    def test_returns_all_required_fields(self):
        result = ts.calculate_pit(30_000_000, 500)
        for key in ("monthly_income", "cards_this_month", "personal_deduction",
                    "study_deduction", "total_deduction", "taxable_income",
                    "tax", "rate_eff_pct", "source_ref"):
            assert key in result, f"Thiếu field: {key}"

    def test_tax_reduction_applied(self, monkeypatch):
        monkeypatch.setattr(ts, "_get_tax_reduction_factor", lambda: 0.5)
        result_full = ts.calculate_pit(30_000_000, 0)
        monkeypatch.setattr(ts, "_get_tax_reduction_factor", lambda: 1.0)
        result_no_red = ts.calculate_pit(30_000_000, 0)
        assert result_full["tax"] == round(result_no_red["tax"] * 0.5)


# ═══════════════════════════════════════════════════════════════
# E. calculate_incremental_pit (withholding)
# ═══════════════════════════════════════════════════════════════

class TestCalculateIncrementalPit:
    """Tính thuế tăng thêm ngay khi có thu nhập mới (withholding cơ chế)."""

    @pytest.fixture(autouse=True)
    def no_tax_reduction(self, monkeypatch):
        monkeypatch.setattr(ts, "_get_tax_reduction_factor", lambda: 1.0)

    def test_zero_new_income(self):
        assert ts.calculate_incremental_pit(0, 0, 0) == 0

    def test_negative_new_income(self):
        assert ts.calculate_incremental_pit(-1000, 0, 0) == 0

    def test_first_income_below_deduction_no_tax(self):
        # Thu nhập đầu tiên 10M < 15.5M giảm trừ → không có thuế
        result = ts.calculate_incremental_pit(10_000_000, 0, 0)
        assert result == 0

    def test_first_income_above_deduction(self):
        # Thu nhập đầu 20M, prev=0 → toàn bộ thuế = calculate_pit(20M, 0)["tax"]
        incremental = ts.calculate_incremental_pit(20_000_000, 0, 0)
        full_tax = ts.calculate_pit(20_000_000, 0)["tax"]
        assert incremental == full_tax

    def test_income_pushes_into_higher_bracket(self):
        # prev=20M (taxable=4.5M @ bậc 1), new=20M → total=40M (vào bậc 2)
        # Biên thuế phải > 5% (bậc 2 = 10%)
        incremental = ts.calculate_incremental_pit(20_000_000, 20_000_000, 0)
        assert incremental > 0
        # Tỷ lệ biên trên 20M mới phải > bậc 1 (vì tổng vượt 15.5M + 10M = 25.5M)
        implied_rate = incremental / 20_000_000
        assert implied_rate > 0.05  # cao hơn bậc 1

    def test_additive_property(self):
        # Tổng khấu trừ từng bước phải bằng thuế cả tháng
        income_step = 10_000_000
        total_steps = 3
        total_income = income_step * total_steps

        total_withheld = 0
        prev = 0
        for _ in range(total_steps):
            withheld = ts.calculate_incremental_pit(income_step, prev, 0)
            total_withheld += withheld
            prev += income_step

        full_tax = ts.calculate_pit(total_income, 0)["tax"]
        # Sai lệch tối đa vài ngàn do làm tròn từng bước
        assert abs(total_withheld - full_tax) < 10_000

    def test_with_cards_reduces_incremental_tax(self):
        # 1000 thẻ → giảm trừ học tập 1M → ít thuế hơn
        without_cards = ts.calculate_incremental_pit(25_000_000, 0, 0)
        with_cards = ts.calculate_incremental_pit(25_000_000, 0, 1000)
        assert with_cards <= without_cards


# ═══════════════════════════════════════════════════════════════
# F. get_sct_for_item — Thuế tiêu thụ đặc biệt
# ═══════════════════════════════════════════════════════════════

class TestGetSctForItem:
    """Tính SCT theo category/item_id."""

    @pytest.fixture(autouse=True)
    def no_tax_reduction(self, monkeypatch):
        monkeypatch.setattr(ts, "_get_tax_reduction_factor", lambda: 1.0)

    def _item(self, item_id: str, category: str, price: int) -> dict:
        return {"id": item_id, "category": category, "price": price, "name": item_id}

    def test_normal_car_45_percent(self):
        item = self._item("honda_civic", "🚗 Showroom xe hơi", 500_000_000)
        result = ts.get_sct_for_item(item)
        assert result["has_sct"] is True
        assert result["rate"] == pytest.approx(0.45)
        assert result["amount"] == round(500_000_000 * 0.45)

    def test_luxury_car_over_5b_150_percent(self):
        item = self._item("ferrari_sf90", "🚗 Showroom xe hơi", 6_000_000_000)
        result = ts.get_sct_for_item(item)
        assert result["has_sct"] is True
        assert result["rate"] == pytest.approx(1.50)
        assert result["amount"] == round(6_000_000_000 * 1.50)

    def test_luxury_car_exactly_5b_gets_normal_rate(self):
        # Đúng 5B → không phải ">" 5B → 45%
        item = self._item("luxury_car", "🚗 Showroom xe hơi", 5_000_000_000)
        result = ts.get_sct_for_item(item)
        assert result["rate"] == pytest.approx(0.45)

    def test_rolex_luxury_20_percent(self):
        item = self._item("rolex", "⌚ Đồng hồ", 100_000_000)
        result = ts.get_sct_for_item(item)
        assert result["has_sct"] is True
        assert result["rate"] == pytest.approx(0.20)

    def test_iphone_electronics_10_percent(self):
        item = self._item("iphone15", "📱 Điện tử", 30_000_000)
        result = ts.get_sct_for_item(item)
        assert result["has_sct"] is True
        assert result["rate"] == pytest.approx(0.10)

    def test_macbook_electronics_10_percent(self):
        item = self._item("macbook_pro", "💻 Laptop", 50_000_000)
        result = ts.get_sct_for_item(item)
        assert result["has_sct"] is True
        assert result["rate"] == pytest.approx(0.10)

    def test_no_sct_for_food(self):
        item = self._item("pho_bo", "🍜 Đồ ăn", 50_000)
        result = ts.get_sct_for_item(item)
        assert result["has_sct"] is False
        assert result["amount"] == 0

    def test_no_sct_for_unknown_item(self):
        item = self._item("random_item_xyz", "Khác", 1_000_000)
        result = ts.get_sct_for_item(item)
        assert result["has_sct"] is False

    def test_sct_amount_rounded(self):
        item = self._item("ipad_air", "📱 Điện tử", 17_000_000)
        result = ts.get_sct_for_item(item)
        assert result["amount"] == round(17_000_000 * 0.10)

    def test_rate_pct_field_correct(self):
        item = self._item("honda_civic", "🚗 Showroom xe hơi", 500_000_000)
        result = ts.get_sct_for_item(item)
        assert result["rate_pct"] == pytest.approx(45.0)

    def test_sct_reduction_applied(self, monkeypatch):
        monkeypatch.setattr(ts, "_get_tax_reduction_factor", lambda: 0.5)
        item = self._item("honda_civic", "🚗 Showroom xe hơi", 500_000_000)
        result = ts.get_sct_for_item(item)
        expected = round(round(500_000_000 * 0.45) * 0.5)
        assert result["amount"] == expected


# ═══════════════════════════════════════════════════════════════
# G. apply_pit_withholding_on_income — flow withholding
# ═══════════════════════════════════════════════════════════════

class TestApplyPitWithholdingOnIncome:
    """Test flow khấu trừ thuế TNCN ngay khi nhận thưởng."""

    @pytest.fixture(autouse=True)
    def no_tax_reduction(self, monkeypatch):
        monkeypatch.setattr(ts, "_get_tax_reduction_factor", lambda: 1.0)

    def test_zero_income_returns_zero(self, fake_config):
        store = fake_config(ts)
        result = ts.apply_pit_withholding_on_income(0)
        assert result["withheld"] == 0

    def test_negative_income_returns_zero(self, fake_config):
        fake_config(ts)
        result = ts.apply_pit_withholding_on_income(-1000)
        assert result["withheld"] == 0

    def test_income_below_deduction_no_withholding(self, fake_config, monkeypatch):
        store = fake_config(ts)
        # Mock get_monthly_income → 0 (prev income)
        monkeypatch.setattr(ts, "col_ready", lambda: True)
        with patch("anki_finance.tax_system.get_monthly_income", return_value=0):
            result = ts.apply_pit_withholding_on_income(10_000_000)
        # 10M + 0 = 10M < 15.5M → no tax
        assert result["withheld"] == 0
        assert result["net_income"] == 10_000_000

    def test_income_above_deduction_withholds(self, fake_config, monkeypatch):
        store = fake_config(ts)
        with patch("anki_finance.tax_system.get_monthly_income", return_value=0):
            result = ts.apply_pit_withholding_on_income(20_000_000)
        expected = ts.calculate_incremental_pit(20_000_000, 0, 0)
        assert result["withheld"] == expected
        assert result["net_income"] == 20_000_000 - expected

    def test_withheld_accumulated_in_store(self, fake_config, monkeypatch):
        store = fake_config(ts, {"anki_tycoon_pit_withheld_this_month": 100_000})
        with patch("anki_finance.tax_system.get_monthly_income", return_value=0):
            ts.apply_pit_withholding_on_income(20_000_000)
        new_withheld = store.get("anki_tycoon_pit_withheld_this_month", 0)
        assert new_withheld > 100_000  # tích lũy thêm


# ═══════════════════════════════════════════════════════════════
# H. Hằng số & metadata
# ═══════════════════════════════════════════════════════════════

class TestConstants:
    def test_tax_threshold(self):
        assert ts.TAX_THRESHOLD == 10_000_000

    def test_pit_slabs_count(self):
        assert len(ts._PIT_SLABS) == 5

    def test_pit_slabs_sorted(self):
        lows = [low for low, _, _ in ts._PIT_SLABS]
        assert lows == sorted(lows), "Bậc thuế phải sắp xếp tăng dần"

    def test_personal_deduction_2026(self):
        assert ts._PERSONAL_DEDUCTION == 15_500_000

    def test_max_study_deduction(self):
        assert ts._MAX_STUDY_DEDUCTION == 5_000_000

    def test_transfer_tax_rate(self):
        assert ts.TRANSFER_TAX_RATE == pytest.approx(0.02)
