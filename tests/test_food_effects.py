# -*- coding: utf-8 -*-
"""Unit tests cho food_effects.py — active boosts, consume, activate, limits."""

from __future__ import annotations

import time
import pytest


class TestGetCurrentTimeSlot:
    """_get_current_time_slot trả về slot theo giờ hiện tại."""

    def test_returns_tuple(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        slot = mod._get_current_time_slot()
        assert len(slot) == 3  # (name, bonus, desc)
        assert slot[0] in ("morning", "noon", "afternoon", "evening", "late_night", "unknown")
        assert isinstance(slot[1], float)

    def test_bonus_is_positive(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        _, bonus, _ = mod._get_current_time_slot()
        assert bonus > 0


class TestGetItemCategory:
    """_get_item_category phân loại item đúng."""

    def test_drink_by_id(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        assert mod._get_item_category("food_tra_dao_cam_sa") == "drink"

    def test_drink_by_category(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        assert mod._get_item_category("any_id", {"category": "Đồ uống"}) == "drink"

    def test_food_by_category(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        assert mod._get_item_category("any_id", {"category": "Ẩm thực"}) == "food"

    def test_study_by_category(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        assert mod._get_item_category("any_id", {"category": "Vật phẩm học tập"}) == "study"

    def test_finance_by_category(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        assert mod._get_item_category("any_id", {"category": "Vật phẩm tài chính"}) == "finance"

    def test_unknown_returns_other(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        assert mod._get_item_category("unknown_id") == "other"


class TestGetDailyPurchaseCount:
    """get_daily_purchase_count đọc từ purchase log."""

    def test_zero_when_no_purchases(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        assert mod.get_daily_purchase_count("food_banhmi") == 0

    def test_returns_count_after_record(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        mod.record_purchase("food_banhmi")
        assert mod.get_daily_purchase_count("food_banhmi") == 1

    def test_accumulates_multiple(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        mod.record_purchase("food_banhmi")
        mod.record_purchase("food_banhmi")
        mod.record_purchase("food_banhmi")
        assert mod.get_daily_purchase_count("food_banhmi") == 3


class TestCheckDailyLimit:
    """check_daily_limit kiểm tra food/drink/study limits."""

    def test_food_under_limit_returns_ok(self, fake_config, monkeypatch):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        # Mock category cache to avoid loading shop_data
        mod._ITEM_CATEGORY_CACHE = {"food_banhmi": "food"}
        result = mod.check_daily_limit("food_banhmi", {"category": "Ẩm thực"})
        assert result["ok"] is True
        assert result["limit"] == 10

    def test_food_over_limit_returns_error(self, fake_config, monkeypatch):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        mod._ITEM_CATEGORY_CACHE = {"food_banhmi": "food"}
        # Fill purchase log to exceed limit
        mod._get_purchase_log()["_mock"] = {}
        # Directly set the store to simulate 10 purchases
        today = mod._get_today_key()
        log = mod._get_purchase_log()
        log[today] = log.get(today, {})
        log[today]["food_banhmi"] = 10
        mod._save_purchase_log(log)
        result = mod.check_daily_limit("food_banhmi", {"category": "Ẩm thực"})
        assert result["ok"] is False
        assert "đã mua đủ" in result["error"]

    def test_drink_under_limit_returns_ok(self, fake_config, monkeypatch):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        mod._ITEM_CATEGORY_CACHE = {"food_tra_dao_cam_sa": "drink"}
        result = mod.check_daily_limit("food_tra_dao_cam_sa", {"category": "Đồ uống"})
        assert result["ok"] is True

    def test_unknown_category_always_ok(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        result = mod.check_daily_limit("unknown_item")
        assert result["ok"] is True

    def test_study_under_limit_returns_ok(self, fake_config, monkeypatch):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        result = mod.check_daily_limit("study_item", {"category": "Vật phẩm học tập", "price": 100_000})
        assert result["ok"] is True

    def test_study_over_weekly_limit_returns_error(self, fake_config, monkeypatch):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        # Giả lập đã mua 7 items
        week = mod._get_week_key()
        log = mod._get_study_log()
        log[week] = {"study_item": 7}
        mod._save_study_log(log)
        result = mod.check_daily_limit("study_item", {"category": "Vật phẩm học tập", "price": 100_000})
        assert result["ok"] is False
        assert "mua đủ" in result["error"].lower()


class TestGetActiveBoosts:
    """get_active_boosts lọc boost hết hạn."""

    def test_no_boosts_returns_empty(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        assert mod.get_active_boosts() == []

    def test_valid_boost_returned(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        boost = {
            "id": "slot1",
            "expire_ts": now + 3600,
            "cards_left": None,
            "type": "reward_multiplier",
            "value": 1.5,
        }
        mod._save_active([boost])
        active = mod.get_active_boosts()
        assert len(active) == 1
        assert active[0]["id"] == "slot1"

    def test_expired_boost_filtered(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        boost = {
            "id": "slot1",
            "expire_ts": now - 1,  # hết hạn
            "cards_left": None,
        }
        mod._save_active([boost])
        assert mod.get_active_boosts() == []

    def test_no_cards_left_filtered(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        boost = {
            "id": "slot1",
            "expire_ts": now + 3600,
            "cards_left": 0,
        }
        mod._save_active([boost])
        assert mod.get_active_boosts() == []

    def test_expired_boost_cleaned_from_store(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        mod._save_active([
            {"id": "valid", "expire_ts": now + 3600, "cards_left": None},
            {"id": "expired", "expire_ts": now - 1, "cards_left": None},
        ])
        mod.get_active_boosts()
        remaining = mod._get_active()
        assert len(remaining) == 1
        assert remaining[0]["id"] == "valid"


class TestConsumeBoostCard:
    """consume_boost_card xử lý effects khi review card."""

    def test_no_boosts_returns_defaults(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        result = mod.consume_boost_card(3)
        assert result["multiplier"] == 1.0
        assert result["bonus"] == 0
        assert result["shield"] is False

    def test_reward_multiplier_applied(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        mod._save_active([{
            "id": "slot1",
            "expire_ts": now + 3600,
            "cards_left": None,
            "type": "reward_multiplier",
            "value": 1.5,
            "effect_list": [],
        }])
        result = mod.consume_boost_card(3)
        assert result["multiplier"] == 1.5

    def test_xp_bonus_applied(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        mod._save_active([{
            "id": "slot1",
            "expire_ts": now + 3600,
            "cards_left": None,
            "type": "xp_bonus",
            "value": 2000,
            "effect_list": [],
        }])
        result = mod.consume_boost_card(3)
        assert result["bonus"] == 2000

    def test_shield_detected(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        mod._save_active([{
            "id": "slot1",
            "expire_ts": now + 3600,
            "cards_left": None,
            "type": "no_again_penalty",
            "value": 1,
            "effect_list": [],
        }])
        result = mod.consume_boost_card(1)
        assert result["shield"] is True

    def test_effect_list_processed(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        mod._save_active([{
            "id": "slot1",
            "expire_ts": now + 3600,
            "cards_left": None,
            "effect_list": [
                {"type": "reward_multiplier", "value": 1.3},
                {"type": "xp_bonus", "value": 1000},
            ],
        }])
        result = mod.consume_boost_card(3)
        assert result["multiplier"] == 1.3
        assert result["bonus"] == 1000

    def test_decrements_cards_left(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        mod._save_active([{
            "id": "slot1",
            "expire_ts": now + 3600,
            "cards_left": 5,
            "type": "xp_bonus",
            "value": 1000,
            "effect_list": [],
        }])
        mod.consume_boost_card(3)
        remaining = mod._get_active()
        assert remaining[0]["cards_left"] == 4

    def test_trade_off_penalties(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        mod._save_active([{
            "id": "slot1",
            "expire_ts": now + 3600,
            "cards_left": None,
            "effect_list": [
                {"type": "reward_multiplier", "value": 2.0},
                {"type": "stamina_cost", "value": 3},
                {"type": "reward_penalty", "value": 0.1},
            ],
        }])
        result = mod.consume_boost_card(3)
        assert result["multiplier"] == 2.0
        assert result["stamina_cost"] == 3
        assert result["reward_penalty"] == 0.1


class TestDeactivateBoost:
    """deactivate_boost hủy kích hoạt boost."""

    def test_deactivate_valid_boost(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        now = time.time()
        mod._save_active([{
            "id": "slot1",
            "expire_ts": now + 3600,
            "cards_left": None,
            "type": "reward_multiplier",
            "value": 1.5,
            "name": "Test Boost",
        }])
        result = mod.deactivate_boost("slot1")
        assert result["ok"] is True
        assert mod._get_active() == []

    def test_deactivate_nonexistent(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        result = mod.deactivate_boost("no_such_slot")
        assert result["ok"] is False


class TestRecordCancel:
    """record_cancel ghi nhận lượt hủy boost."""

    def test_first_cancel_ok(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        result = mod.record_cancel()
        assert result["ok"] is True
        assert result["remaining"] >= 0

    def test_get_daily_cancel_limit_has_fields(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        info = mod.get_daily_cancel_limit()
        for k in ("base_limit", "max_limit", "limit", "used", "remaining", "total_valid_cards"):
            assert k in info


class TestRecordCardReviewTime:
    """record_card_review_time ghi nhận thẻ hợp lệ."""

    def test_below_min_time_not_recorded(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        mod.record_card_review_time(5)  # < 10s
        assert mod.get_today_valid_card_count() == 0

    def test_above_min_time_recorded(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        mod.record_card_review_time(15)  # >= 10s
        assert mod.get_today_valid_card_count() == 1


class TestGetEffectForItem:
    """get_effect_for_item trả về effect dict."""

    def test_effect_list_returns_primary(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        item_data = {
            "name": "Test Item",
            "effect_list": [
                {"type": "reward_multiplier", "value": 1.5, "duration": 1800},
                {"type": "xp_bonus", "value": 500},
            ],
        }
        result = mod.get_effect_for_item("test_item", item_data)
        assert result["type"] == "reward_multiplier"
        assert result["value"] == 1.5
        assert "_all_effects" in result
        assert len(result["_all_effects"]) == 2

    def test_single_effect_returned(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        item_data = {
            "name": "Coffee",
            "effect": {"type": "reward_multiplier", "value": 1.5, "duration": 1800},
        }
        result = mod.get_effect_for_item("food_ca_phe_trung", item_data)
        assert result["type"] == "reward_multiplier"

    def test_default_effect_fallback(self, fake_config):
        import anki_finance.food_effects as mod
        fake_config(mod, {})
        result = mod.get_effect_for_item("unknown_item")
        assert "type" in result
        assert "value" in result


class TestRegisterFoodPurchase:
    """register_food_purchase ghi freshness."""

    def test_register_creates_freshness_entry(self, fake_config):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        mod.register_food_purchase("food_banhmi", "slot_abc", 24)
        fresh = mod._get_fresh()
        assert "slot_abc" in fresh
        assert fresh["slot_abc"]["item_id"] == "food_banhmi"
        assert fresh["slot_abc"]["expire_h"] == 24.0


class TestGetSpoiledSlots:
    """get_spoiled_slots phát hiện đồ hết hạn."""

    def test_fresh_food_not_spoiled(self, fake_config, monkeypatch):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        # Giả lập thời gian hiện tại
        fake_now = 1_000_000.0
        monkeypatch.setattr(time, "time", lambda: fake_now)
        fresh = {
            "slot1": {"item_id": "food_banhmi", "buy_ts": fake_now, "expire_h": 24},
        }
        mod._save_fresh(fresh)
        assert mod.get_spoiled_slots() == []

    def test_expired_food_detected(self, fake_config, monkeypatch):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        fake_now = 100_000_000.0
        monkeypatch.setattr(time, "time", lambda: fake_now)
        # Mua 25h trước với expire_h=24 → hết hạn
        buy_ts = fake_now - 25 * 3600
        fresh = {
            "slot1": {"item_id": "food_banhmi", "buy_ts": buy_ts, "expire_h": 24},
        }
        mod._save_fresh(fresh)
        spoiled = mod.get_spoiled_slots()
        assert "slot1" in spoiled


class TestCheckAndSpoilFood:
    """check_and_spoil_food xóa đồ hết hạn khỏi inventory."""

    def test_no_spoiled_returns_empty(self, fake_config, monkeypatch):
        import anki_finance.food_effects as mod
        store = fake_config(mod, {})
        fake_now = 1_000_000.0
        monkeypatch.setattr(time, "time", lambda: fake_now)
        fresh = {"slot1": {"item_id": "food_banhmi", "buy_ts": fake_now, "expire_h": 24}}
        mod._save_fresh(fresh)
        assert mod.check_and_spoil_food() == []
