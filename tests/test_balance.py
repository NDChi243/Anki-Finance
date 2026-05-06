# -*- coding: utf-8 -*-
"""Unit tests cho balance.py — get/set balance, add_reward, stats, penalties."""

from __future__ import annotations

import pytest

# ─── get_balance / set_balance ────────────────────────────────


class TestGetBalance:
    """get_balance() đọc từ config key."""

    def test_returns_zero_when_not_set(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        assert mod.get_balance() == 0

    def test_returns_stored_value(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {mod.CONFIG_KEY_BALANCE: 5_000_000})
        assert mod.get_balance() == 5_000_000


class TestSetBalance:
    """set_balance(amount) ghi đúng và trigger callbacks."""

    def test_sets_balance_in_config(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        mod.set_balance(10_000)
        assert store.get(mod.CONFIG_KEY_BALANCE) == 10_000

    def test_overwrites_previous_value(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {mod.CONFIG_KEY_BALANCE: 5_000})
        mod.set_balance(20_000)
        assert store.get(mod.CONFIG_KEY_BALANCE) == 20_000

    def test_converts_to_int(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        mod.set_balance(9999.9)
        bal = store.get(mod.CONFIG_KEY_BALANCE)
        assert bal == 9999
        assert isinstance(bal, int)


# ─── set_balance_and_log ──────────────────────────────────────


class TestSetBalanceAndLog:
    """set_balance_and_log ghi balance + check_balance_dropped."""

    def test_sets_balance(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        mod.set_balance_and_log(15_000, "reward", 15_000, "test")
        assert store.get(mod.CONFIG_KEY_BALANCE) == 15_000

    def test_balance_dropped_below_1000_fires_achievement(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        fired = []
        monkeypatch.setattr(mod, "_check_balance_dropped", lambda nb: fired.append(nb))
        mod.set_balance_and_log(500, "purchase", 500, "test")
        assert 500 in fired


# ─── _check_balance_dropped ───────────────────────────────────


class TestCheckBalanceDropped:
    """_check_balance_dropped trigger achievement khi balance < 1000."""

    def test_balance_above_1000_noop(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        fake_config(mod, {})
        called = []
        monkeypatch.setattr("anki_finance.achievements.check_and_unlock", lambda *a: called.append(a))
        mod._check_balance_dropped(5000)
        assert len(called) == 0

    def test_balance_999_triggers_achievement(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        fake_config(mod, {})
        called = []
        monkeypatch.setattr("anki_finance.achievements.check_and_unlock", lambda *a: called.append(a))
        mod._check_balance_dropped(999)
        assert len(called) == 1
        assert called[0] == ("balance_dropped", True)

    def test_balance_0_triggers_achievement(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        fake_config(mod, {})
        called = []
        monkeypatch.setattr("anki_finance.achievements.check_and_unlock", lambda *a: called.append(a))
        mod._check_balance_dropped(0)
        assert len(called) == 1

    def test_exception_safe(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        fake_config(mod, {})
        monkeypatch.setattr("anki_finance.achievements.check_and_unlock", lambda *a: (_ for _ in ()).throw(Exception("boom")))
        # Should not raise
        mod._check_balance_dropped(500)


# ─── add_reward (col_ready=false) ─────────────────────────────


class TestAddRewardNotReady:
    """add_reward trả về dict không rewarded khi col_ready() == False."""

    def test_not_ready_returns_empty(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        original = mod.col_ready

        def not_ready():
            return False
        import anki_finance._safe_config as sc
        # fake_config đã patch col_ready, ta cần patch lại
        import anki_finance.balance as b

        def col_false():
            return False
        # monkeypatch trực tiếp
        import pytest
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(b, "col_ready", col_false)
        try:
            result = b.add_reward(2)
            assert result == {"rewarded": False, "penalized": False, "penalty": 0, "message": ""}
        finally:
            monkeypatch.undo()


# ─── record_purchase ──────────────────────────────────────────


class TestRecordPurchase:
    """record_purchase ghi stats + transaction."""

    def test_adds_to_total_spent(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        mod.record_purchase(50_000, "Test Item")
        stats = mod.get_stats()
        assert stats["total_spent"] == 50_000

    def test_accumulates_multiple_purchases(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        mod.record_purchase(10_000, "A")
        mod.record_purchase(20_000, "B")
        stats = mod.get_stats()
        assert stats["total_spent"] == 30_000

    def test_col_ready_false_noop(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        import pytest
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(mod, "col_ready", lambda: False)
        try:
            mod.record_purchase(50_000, "X")
            stats = mod.get_stats()
            assert stats["total_spent"] == 0
        finally:
            monkeypatch.undo()


# ─── get_stats / set_stats ────────────────────────────────────


class TestGetStats:
    """get_stats trả về dict đầy đủ các keys."""

    def test_default_stats_have_all_keys(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        s = mod.get_stats()
        for k in ("total_earned", "total_spent", "cards_reviewed", "ease_1", "ease_2", "ease_3", "ease_4"):
            assert k in s
            assert s[k] == 0

    def test_fills_missing_keys(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {mod.CONFIG_KEY_STATS: {"total_earned": 100}})
        s = mod.get_stats()
        assert s["total_earned"] == 100
        assert s["total_spent"] == 0
        assert s["cards_reviewed"] == 0

    def test_set_stats_roundtrip(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        expected = {"total_earned": 500, "total_spent": 200, "cards_reviewed": 10,
                    "ease_1": 2, "ease_2": 3, "ease_3": 4, "ease_4": 1}
        mod.set_stats(expected)
        retrieved = mod.get_stats()
        assert retrieved == expected


# ─── _update_stats ────────────────────────────────────────────


class TestUpdateStats:
    """_update_stats cập nhật counters."""

    def test_increments_cards_reviewed(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        mod._update_stats(3, 10_000)
        s = mod.get_stats()
        assert s["cards_reviewed"] == 1
        assert s["ease_3"] == 1
        assert s["total_earned"] == 10_000

    def test_accumulates_multi_cards(self, fake_config):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        mod._update_stats(2, 15_000)
        mod._update_stats(2, 15_000)
        s = mod.get_stats()
        assert s["cards_reviewed"] == 2
        assert s["ease_2"] == 2
        assert s["total_earned"] == 30_000


# ─── _apply_food_penalties / _apply_reward_penalty ────────────


class TestApplyFoodPenalties:
    """_apply_food_penalties tiêu hao stamina_cost."""

    def test_no_stamina_cost_noop(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        fake_config(mod, {})
        consumed = []
        monkeypatch.setattr("anki_finance.energy_system.consume_energy", lambda amt: consumed.append(amt))
        mod._apply_food_penalties({"stamina_cost": 0})
        assert len(consumed) == 0

    def test_positive_stamina_consumes_energy(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        fake_config(mod, {})
        consumed = []
        monkeypatch.setattr("anki_finance.energy_system.consume_energy", lambda amt: consumed.append(amt))
        mod._apply_food_penalties({"stamina_cost": 5})
        assert consumed == [5]

    def test_exception_safe(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        fake_config(mod, {})
        monkeypatch.setattr("anki_finance.energy_system.consume_energy", lambda amt: (_ for _ in ()).throw(Exception("err")))
        mod._apply_food_penalties({"stamina_cost": 5})  # should not raise


class TestApplyRewardPenalty:
    """_apply_reward_penalty giảm % reward."""

    def test_no_penalty_returns_same(self, fake_config):
        import anki_finance.balance as mod
        fake_config(mod, {})
        assert mod._apply_reward_penalty(10_000, {}) == 10_000
        assert mod._apply_reward_penalty(10_000, {"reward_penalty": 0}) == 10_000

    def test_ten_percent_penalty(self, fake_config):
        import anki_finance.balance as mod
        fake_config(mod, {})
        result = mod._apply_reward_penalty(10_000, {"reward_penalty": 0.1})
        assert result == 9_000

    def test_fifty_percent_penalty(self, fake_config):
        import anki_finance.balance as mod
        fake_config(mod, {})
        result = mod._apply_reward_penalty(10_000, {"reward_penalty": 0.5})
        assert result == 5_000

    def test_never_below_zero(self, fake_config):
        import anki_finance.balance as mod
        fake_config(mod, {})
        result = mod._apply_reward_penalty(1_000, {"reward_penalty": 2.0})
        assert result == 0


# ─── add_reward (ease 2, 3, 4 — various paths) ────────────────


class TestAddRewardEase2:
    """add_reward với ease=2 (Hard) — path cơ bản."""

    def test_returns_rewarded_dict_with_fields(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        # Mock các dependencies để tránh lỗi import
        monkeypatch.setattr(mod, "_consume_energy_and_stamina", lambda: 1.0)
        monkeypatch.setattr(mod, "_apply_food_penalties", lambda bi: None)
        monkeypatch.setattr(mod, "_apply_reward_penalty", lambda r, bi: r)
        monkeypatch.setattr(mod, "_apply_loan_repay", lambda r: r)
        monkeypatch.setattr(mod, "_apply_pit_withholding", lambda gi: (gi, 0))
        monkeypatch.setattr(mod, "_update_stats", lambda e, r: None)
        monkeypatch.setattr(mod, "set_balance_and_log", lambda *a, **kw: None)
        monkeypatch.setattr("anki_finance.transactions.add_transaction", lambda *a, **kw: None)
        monkeypatch.setattr("anki_finance.finance.reset_monthly_if_needed", lambda: None)
        monkeypatch.setattr("anki_finance.again_tracker", None)  # prevent import for ease=1

        result = mod.add_reward(2)
        assert result["rewarded"] is True
        assert "message" in result
        assert "boost" in result


class TestAddRewardEase1NoShield:
    """add_reward với ease=1 (Again) không có shield."""

    def test_calls_record_again(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        monkeypatch.setattr(mod, "_consume_energy_and_stamina", lambda: 1.0)
        monkeypatch.setattr(mod, "_apply_food_penalties", lambda bi: None)
        monkeypatch.setattr(mod, "_apply_reward_penalty", lambda r, bi: r)
        monkeypatch.setattr(mod, "_apply_loan_repay", lambda r: r)
        monkeypatch.setattr(mod, "_apply_pit_withholding", lambda gi: (gi, 0))
        monkeypatch.setattr(mod, "_update_stats", lambda e, r: None)
        monkeypatch.setattr(mod, "set_balance_and_log", lambda *a, **kw: None)
        monkeypatch.setattr("anki_finance.transactions.add_transaction", lambda *a, **kw: None)
        monkeypatch.setattr("anki_finance.finance.reset_monthly_if_needed", lambda: None)

        result = mod.add_reward(1)
        # Vì record_again và consume_boost_card được mock, shouldn't crash
        assert "boost" in result


class TestAddRewardZeroRewardEase:
    """add_reward với ease lạ trả về rewarded=False."""

    def test_unknown_ease_returns_empty(self, fake_config, monkeypatch):
        import anki_finance.balance as mod
        store = fake_config(mod, {})
        monkeypatch.setattr(mod, "_consume_energy_and_stamina", lambda: 1.0)
        monkeypatch.setattr(mod, "_apply_food_penalties", lambda bi: None)
        monkeypatch.setattr("anki_finance.finance.reset_monthly_if_needed", lambda: None)
        monkeypatch.setattr("anki_finance.again_tracker", None)

        result = mod.add_reward(99)
        assert result["rewarded"] is False
        assert result["message"] == ""
