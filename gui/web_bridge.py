# -*- coding: utf-8 -*-
"""
QWebChannel bridge — JavaScript ↔ Python.
Tất cả method đều là @pyqtSlot để JS gọi được.

PERF: Cache shop items trong memory để tránh đọc file JSON nhiều lần.
"""

import json
import time
from aqt.qt import QObject, pyqtSlot, pyqtSignal

from ..logger import get_logger
logger = get_logger(__name__)

from ..balance import get_balance, set_balance_and_log, get_stats, record_purchase as record_purchase_balance
from ..inventory import get_inventory, add_to_inventory, count_item, can_add_to_inventory, get_inventory_slots_info
from ..shop_data import load_shop_items, get_items_map
from ..transactions import get_transactions, clear_transactions
from ..finance import (
    get_budget, set_budget, get_monthly_spending,
    get_monthly_income, get_budget_status, reset_monthly_if_needed,
)
from ..bank import (
    get_savings, calculate_interest,
    get_demand_balance, calc_demand_interest,
    deposit_demand, withdraw_demand, claim_demand_interest,
    open_term_deposit, close_term_deposit, add_term_funds,
    get_all_deposits_info, get_bank_products,
    get_total_savings, get_total_current_value, get_send_more_status,
    get_instant_interest_status, claim_instant_term_interest,
)
from .image_manager import get_image_url, clear_cache, get_images_dir, list_available_images
from ..again_tracker import get_today_summary, get_daily_again_count, get_daily_penalty_total
from ..food_effects import (
    get_boosts_summary, activate_boost, get_effect_for_item,
    check_and_spoil_food, register_food_purchase, _get_fresh,
    check_daily_limit, record_purchase, get_daily_limits_info,
    _get_item_category,
    record_study_purchase, get_weekly_study_count, get_weekly_study_total,
)
from ..item_effects import (
    register_passive_effect,
    get_passive_effects_summary, get_all_passive_effects,
    get_item_effect_descriptions, format_item_effects_html,
    get_item_effects, is_passive_item, ACTIVE_TYPES,
)
from ..reset_manager import perform_reset, get_reset_log, get_confirm_phrase
from ..streak_system import get_streak_status
from ..rank_system import get_rank_status
from ..daily_quest import get_quest_summary
from ..goals import get_goal


_SET_FAMILY_BY_ITEM = {
    "tech_macbook_m3": "Focus Ecosystem",
    "tech_ipad_pro": "Focus Ecosystem",
    "tech_kinh_ap_trong_tam": "Focus Ecosystem",
    "tech_bang_dieu_khien_hoc_tap": "AI Study Desk",
    "tech_iphone16": "AI Study Desk",
    "tech_dell_xps": "AI Study Desk",
    "finance_so_tiet_kiem_thong_minh": "Private Banking Suite",
    "finance_the_tin_dung_vip": "Private Banking Suite",
    "finance_chung_chi_cfa": "Private Banking Suite",
    "ins_health": "Safety Net",
    "ins_life": "Safety Net",
    "ins_unemployment": "Safety Net",
}


def _resolve_theme_profile(item: dict) -> dict:
    cat = item.get("category", "")
    etypes = {e.get("type", "") for e in get_item_effects(item)}

    if "Ẩm thực" in cat or "Đồ uống" in cat:
        group = "food"
        icon = "🍽️"
        label = "Ẩm thực & Đồ uống"
        note = "Consumable kích hoạt buff ngắn hạn trong phiên học — tiêu thụ để nhận hiệu ứng tức thì."
    elif "Vật phẩm học tập" in cat:
        group = "study"
        icon = "🎓"
        label = "Học tập"
        note = "Buff ngắn hạn hoặc tác động trực tiếp lên phiên học, review và trí nhớ."
    elif "Cửa hàng đồ công nghệ" in cat:
        group = "tech"
        icon = "💻"
        label = "Công nghệ"
        note = "Thiết bị tăng năng suất và can thiệp scheduler theo hướng build dài hạn."
    else:
        group = "finance"
        icon = "🏦"
        label = "Tài chính"
        note = "Tài sản, bảo hiểm và công cụ đầu tư tối ưu dòng tiền, rủi ro hoặc tăng trưởng."

    role = "Bổ trợ"
    if etypes & {"reward_multiplier", "xp_bonus", "double_easy", "night_owl", "no_again_penalty", "penalty_shield"}:
        role = "Buff phiên học"
    elif etypes & {"interval_boost", "easy_interval_bonus", "factor_boost", "study_time_reduction"}:
        role = "Can thiệp scheduler"
    elif etypes & {"review_count_bonus", "skill_cooldown_reduction", "movement_speed", "stamina_regen"}:
        role = "Tăng năng suất"
    elif etypes & {"interest_bonus", "interest_speed_boost", "instant_interest_cooldown"}:
        role = "Ngân hàng"
    elif etypes & {"stock_cooldown_reduction", "crypto_cooldown_reduction"}:
        role = "Đầu tư chủ động"
    elif etypes & {"tax_reduction", "disease_resistance", "repair_speed", "health_boost"}:
        role = "Phòng thủ rủi ro"
    elif etypes & {"passive_income_bonus"}:
        role = "Dòng tiền thụ động"

    return {
        "theme_group": group,
        "theme_icon": icon,
        "theme_label": label,
        "role_label": role,
        "theme_note": note,
        "set_name": _SET_FAMILY_BY_ITEM.get(item.get("id", ""), ""),
    }


def _enrich_items(items: list) -> list:
    for item in items:
        item["owned_count"] = count_item(item["id"])
        url = get_image_url(item["id"])
        item["image_url"] = url if url else ""
        item.update(_resolve_theme_profile(item))
        # Thêm effect descriptions cho UI
        effects = get_item_effect_descriptions(item)
        if effects:
            item["effect_descriptions"] = effects
            item["effect_html"] = format_item_effects_html(get_item_effects(item))
        else:
            item["effect_descriptions"] = []
            item["effect_html"] = ""
    return items


class TycoonBridge(QObject):
    balanceChanged = pyqtSignal(int)

    # ── Dashboard ──────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getDashboardData(self):
        """Trả về tất cả dữ liệu cần cho Dashboard trong 1 lần gọi."""
        try:
            streak = get_streak_status()
            rank   = get_rank_status()
            quest  = get_quest_summary()
            goal   = get_goal()
            again  = get_today_summary()
            stats  = get_stats()

            # Achievement summary
            try:
                from ..achievements import get_unlocked_count, get_total_count, get_recent_unlocked
                ach_summary = {
                    "unlocked": get_unlocked_count(),
                    "total":    get_total_count(),
                    "recent":   get_recent_unlocked(3),
                }
            except Exception as e:
                logger.debug("getDashboard (achievements): %s", e)
                ach_summary = {"unlocked": 0, "total": 0, "recent": []}

            # Real Estate summary
            try:
                from ..real_estate import get_re_summary
                re_summary = get_re_summary()
            except Exception as e:
                logger.debug("getDashboard (real_estate): %s", e)
                re_summary = {}

            # Stock dividend summary
            try:
                from ..stock_market import get_dividend_summary
                stock_dividends = get_dividend_summary()
            except Exception as e:
                logger.debug("getDashboard (stock_dividends): %s", e)
                stock_dividends = {}

            return json.dumps({
                "ok": True,
                "balance": get_balance(),
                "stats": stats,
                "streak": streak,
                "rank": rank,
                "quests": {"quests": quest, "summary": quest},
                "goal": goal,
                "again": {
                    "count":    get_daily_again_count(),
                    "penalty":  get_daily_penalty_total(),
                    "summary":  again,
                },
                "bank": {
                    "total_savings": get_total_savings(),
                },
                "passive_effects": get_passive_effects_summary(),
                "passive_aggregated": get_all_passive_effects(),
                # ── Achievement ──
                "achievement": ach_summary,
                # ── BĐS ──
                "re_summary": re_summary,
                # ── Stock ──
                "stock_dividends": stock_dividends,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getShopItems(self):
        items = _enrich_items(load_shop_items())
        return json.dumps(items, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def buyItem(self, item_id: str):
        # Dùng get_items_map() để tra cứu nhanh, tránh load lại JSON
        items_map = get_items_map()
        item = items_map.get(item_id)
        if not item:
            logger.warning("buyItem(%s): item không tồn tại trong items_map (items_map size=%d)", item_id, len(items_map))
            return json.dumps({"ok": False, "error": "Sản phẩm không tồn tại."})
        logger.debug("buyItem(%s): vehicle_group='%s', category='%s', price=%d",
                     item_id, item.get("vehicle_group"), item.get("category", ""), item.get("price", 0))

        # ── Kiểm tra daily purchase limit ──
        limit_check = check_daily_limit(item_id, item)
        if not limit_check["ok"]:
            return json.dumps(limit_check, ensure_ascii=False)

        balance = get_balance()
        price = item["price"]
        if balance < price:
            shortage = price - balance
            return json.dumps({
                "ok": False,
                "error": f"Không đủ tiền! Cần thêm {shortage:,} VND.".replace(",", "."),
            })

        is_vehicle = bool(item.get("vehicle_group"))
        cat = _get_item_category(item_id, item)
        is_food_or_drink = cat in ("food", "drink")

        # ⚠️ Diagnostic: nếu item thuộc "Showroom xe" nhưng thiếu vehicle_group → cảnh báo
        if "showroom xe" in item.get("category", "").lower() and not is_vehicle:
            logger.warning("buyItem(%s): item category='%s' nhưng thiếu vehicle_group! Dữ liệu shop không hợp lệ.", item_id, item.get("category", ""))

        if is_vehicle:
            # Xe cộ chỉ vào garage, không vào inventory
            try:
                from ..vehicle_system import get_total_garage_slots, get_garage_summary
                used = len(get_garage_summary())
                total = get_total_garage_slots()
                if used >= total:
                    return json.dumps({
                        "ok": False,
                        "error": f"🚗 Garage đầy! ({used}/{total} slot). Mua thêm slot hoặc bán xe cũ trước khi mua xe mới.",
                    }, ensure_ascii=False)
            except Exception as e:
                logger.debug("purchaseItem (garage check): %s", e)
        else:
            if not is_food_or_drink:
                if not can_add_to_inventory():
                    slots = get_inventory_slots_info()
                    return json.dumps({
                        "ok": False,
                        "error": f"🎒 Kho đầy! ({slots['used']}/{slots['max']} slot). Mua nhà lớn hơn hoặc trang bị item tăng sức chứa để mở thêm slot!",
                    }, ensure_ascii=False)

        new_bal = balance - price
        set_balance_and_log(new_bal, "purchase", -price, f"Mua: {item['name']}")
        # ⚠️ LUÔN thêm vào inventory (trừ xe - xe vào garage riêng).
        # Food/drink cũng cần vào inventory để activate_boost có thể
        # tìm thấy và remove khỏi kho khi kích hoạt boost.
        if not is_vehicle:
            add_to_inventory(item_id)

        # ── Ghi nhận giao dịch vào tài chính (monthly spending) ──
        record_purchase_balance(price, item["name"])

        # ── Ghi nhận daily/weekly purchase limit ──
        if cat in ("food", "drink"):
            record_purchase(item_id)

        # ── Vật phẩm học tập: ghi nhận weekly limit ──
        is_study = (cat == "study")
        if is_study:
            record_study_purchase(item_id, item.get("price", 0))

        # Nếu là đồ ăn/uống → đăng ký freshness với slot_id chuẩn
        item_cat = _get_item_category(item_id, item)
        is_food = item_cat in ("food", "drink")
        if is_food or is_study:
            import uuid as _uuid
            slot_id  = f"{item_id}_{str(_uuid.uuid4())[:8]}"
            effect   = get_effect_for_item(item_id, item)
            expire_h = item.get("expire_h", effect.get("expire_h", 24))
            register_food_purchase(item_id, slot_id, expire_h)

        # Nếu là item passive effect → đăng ký ngay (trừ đồ công nghệ - chỉ active khi dùng)
        is_tech = "Cửa hàng đồ công nghệ" in item.get("category", "")
        if is_passive_item(item) and not is_tech:
            register_passive_effect(item_id, item)

        # Nếu là xe (có vehicle_group) → đăng ký vào garage
        if item.get("vehicle_group"):
            try:
                from ..vehicle_system import register_vehicle
                register_vehicle(item_id, item)
                logger.info("buyItem(%s): đã đăng ký xe vào garage", item_id)
            except Exception as e:
                logger.debug("purchaseItem (register_vehicle): %s", e)
        elif "showroom xe" in item.get("category", "").lower():
            # ⚠️ Item có category Showroom xe nhưng không có vehicle_group → lỗi dữ liệu
            logger.error("buyItem(%s): category='%s' nhưng vehicle_group bị thiếu! Xe sẽ KHÔNG được đăng ký vào garage.", item_id, item.get("category", ""))

        # Nếu là đồ công nghệ → đăng ký vào tech lab (passive effects chỉ active khi dùng)
        if is_tech:
            try:
                from ..tech_system import register_tech
                register_tech(item_id, item)
            except Exception as e:
                logger.debug("purchaseItem (register_tech): %s", e)

        # Nếu là BĐS → tạo entry trong portfolio
        if item.get("is_real_estate"):
            try:
                from ..real_estate import add_property
                add_property(item_id, item)
            except Exception as e:
                logger.debug("purchaseItem (add_property): %s", e)

        # Nếu là tài sản số → tạo holding crypto + đăng ký effects
        if item.get("is_digital_asset"):
            try:
                from ..digital_assets import add_digital_asset
                add_digital_asset(item_id, item)
            except Exception as e:
                logger.debug("purchaseItem (add_digital_asset): %s", e)
            # Passive effects (passive_income_bonus, crypto_cooldown_reduction, ...) → đăng ký ngay
            register_passive_effect(item_id, item)
            # Boost chủ động có giới hạn thẻ/giờ (meme coins: xp_bonus) → kích hoạt ngay
            import uuid as _uuid2
            _active_effs = [
                e for e in get_item_effects(item)
                if e.get("type") in ACTIVE_TYPES
                and (e.get("cards", 0) > 0 or e.get("duration", 0) > 0 or e.get("expire_h", 0) > 0)
            ]
            if _active_effs:
                _slot_id = f"{item_id}_{str(_uuid2.uuid4())[:8]}"
                _expire_h = item.get("expire_h", _active_effs[0].get("expire_h", 72))
                register_food_purchase(item_id, _slot_id, _expire_h)
                _eff = _active_effs[0].copy()
                if len(_active_effs) > 1:
                    _eff["_all_effects"] = _active_effs
                activate_boost(item_id, _eff, _slot_id)

        # Thuế tiêu thụ đặc biệt (SCT)
        sct_amount = 0
        try:
            from ..tax_system import collect_sct, get_sct_for_item
            sct_info = get_sct_for_item(item)
            if sct_info["has_sct"]:
                sct_amount = collect_sct(item)
        except Exception as e:
            logger.debug("purchaseItem (SCT): %s", e)

        new_balance = get_balance()
        self.balanceChanged.emit(new_balance)

        logger.debug("buyItem(%s): hoàn tất — new_balance=%d", item_id, new_balance)
        return json.dumps({
            "ok":             True,
            "new_balance":    new_balance,
            "item_name":      item["name"],
            "is_food":        is_food,
            "is_study":       is_study,
            "is_real_estate": bool(item.get("is_real_estate")),
            "sct_amount":     sct_amount,
        }, ensure_ascii=False)

    @pyqtSlot(str, str, result=str)
    def processShopPayment(self, item_id: str, payment_json: str):
        logger.debug("processShopPayment(%s): payment_json=%s", item_id, payment_json)
        """
        Mua item với lựa chọn phương thức thanh toán.
        payment_json (JSON string): {
            "method": "cash" | "credit" | "split",
            "card_id": "..." (nếu method=credit/split),
            "cash_amount": 0 (nếu split),
            "card_amount": 0 (nếu split)
        }
        """
        try:
            payment = json.loads(payment_json)
        except Exception as e:
            logger.debug("processPayment (parse): %s", e)
            return json.dumps({"ok": False, "error": "Dữ liệu thanh toán không hợp lệ."})

        method = payment.get("method", "cash")

        # ── Load item ────────────────────────────────────────────
        items_map = get_items_map()
        item = items_map.get(item_id)
        if not item:
            return json.dumps({"ok": False, "error": "Sản phẩm không tồn tại."})

        # ── Kiểm tra daily purchase limit ──
        limit_check = check_daily_limit(item_id, item)
        if not limit_check["ok"]:
            return json.dumps(limit_check, ensure_ascii=False)

        price = item["price"]
        balance = get_balance()

        # ── Xác định số tiền cash vs card ────────────────────────
        if method == "cash":
            cash_amount = price
            card_id = None
            card_amount = 0
        elif method == "credit":
            cash_amount = 0
            card_id = payment.get("card_id")
            card_amount = price
        elif method == "split":
            cash_amount = payment.get("cash_amount", 0)
            card_amount = payment.get("card_amount", 0)
            card_id = payment.get("card_id")
            if cash_amount + card_amount != price:
                return json.dumps({
                    "ok": False,
                    "error": f"Tổng tiền thanh toán ({cash_amount+card_amount:,}₫) không khớp giá ({price:,}₫).".replace(",", ".")
                })
        else:
            return json.dumps({"ok": False, "error": "Phương thức thanh toán không hợp lệ."})

        # ── Kiểm tra inventory / garage ──────────────────────────
        is_vehicle = bool(item.get("vehicle_group"))
        cat = _get_item_category(item_id, item)
        is_food_or_drink = cat in ("food", "drink")

        # ⚠️ Diagnostic: nếu item thuộc "Showroom xe" nhưng thiếu vehicle_group → cảnh báo
        if "showroom xe" in item.get("category", "").lower() and not is_vehicle:
            logger.warning("processShopPayment(%s): item category='%s' nhưng thiếu vehicle_group! Dữ liệu shop không hợp lệ.", item_id, item.get("category", ""))

        if is_vehicle:
            try:
                from ..vehicle_system import get_total_garage_slots, get_garage_summary
                used = len(get_garage_summary())
                total = get_total_garage_slots()
                if used >= total:
                    return json.dumps({
                        "ok": False,
                        "error": f"🚗 Garage đầy! ({used}/{total} slot). Mua thêm slot hoặc bán xe cũ trước khi mua xe mới.",
                    }, ensure_ascii=False)
            except Exception as e:
                logger.debug("processPayment (garage check): %s", e)
        else:
            if not is_food_or_drink:
                if not can_add_to_inventory():
                    slots = get_inventory_slots_info()
                    return json.dumps({
                        "ok": False,
                        "error": f"🎒 Kho đầy! ({slots['used']}/{slots['max']} slot). Mua nhà lớn hơn hoặc trang bị item tăng sức chứa để mở thêm slot!",
                    }, ensure_ascii=False)

        # ── Xử lý thanh toán ─────────────────────────────────────
        from ..credit_banking import process_shop_payment

        # process_shop_payment sẽ:
        #   1. Kiểm tra tổng tiền khớp giá
        #   2. Kiểm tra số dư tiền mặt (nếu cash_amount > 0)
        #   3. Xử lý thẻ tín dụng (nếu card_amount > 0) qua use_credit_card
        pay_result = process_shop_payment(
            price=price,
            cash_amount=cash_amount,
            card_id=card_id,
            card_amount=card_amount
        )
        if not pay_result.get("ok"):
            return json.dumps(pay_result, ensure_ascii=False)

        # ── Trừ tiền mặt & ghi log ──────────────────────────────
        if cash_amount > 0:
            # set_balance_and_log sẽ set balance mới + log transaction
            set_balance_and_log(balance - cash_amount, "purchase", -cash_amount,
                                f"Mua: {item['name']} (tiền mặt)")

        # ── Ghi log cho giao dịch thẻ tín dụng ──────────────────
        if card_amount > 0:
            from ..transactions import add_transaction as add_finance_txn
            try:
                add_finance_txn("credit_card_purchase", card_amount,
                                f"Mua: {item['name']} (thẻ tín dụng)")
            except Exception as e:
                logger.debug("processPayment (credit card txn): %s", e)

        # ── Inventory / Garage ───────────────────────────────────
        # ⚠️ LUÔN thêm vào inventory (trừ xe - xe vào garage riêng).
        # Food/drink cũng cần vào inventory để activate_boost có thể
        # tìm thấy và remove khỏi kho khi kích hoạt boost.
        if not is_vehicle:
            add_to_inventory(item_id)

        # Ghi nhận giao dịch tài chính (monthly spending)
        record_purchase_balance(price, item["name"])

        # Ghi nhận daily/weekly purchase limit
        cat = _get_item_category(item_id, item)
        if cat in ("food", "drink"):
            record_purchase(item_id)

        # Vật phẩm học tập
        is_study = (cat == "study")
        if is_study:
            record_study_purchase(item_id, item.get("price", 0))

        # Food / study → freshness
        is_food = cat in ("food", "drink")
        if is_food or is_study:
            import uuid as _uuid
            slot_id  = f"{item_id}_{str(_uuid.uuid4())[:8]}"
            effect   = get_effect_for_item(item_id, item)
            expire_h = item.get("expire_h", effect.get("expire_h", 24))
            register_food_purchase(item_id, slot_id, expire_h)

        # Passive effects
        is_tech = "Cửa hàng đồ công nghệ" in item.get("category", "")
        _is_passive = is_passive_item(item)
        if _is_passive and not is_tech:
            register_passive_effect(item_id, item)

        # Vehicle
        if item.get("vehicle_group"):
            try:
                from ..vehicle_system import register_vehicle
                register_vehicle(item_id, item)
                logger.info("processShopPayment(%s): đã đăng ký xe vào garage", item_id)
            except Exception as e:
                logger.debug("processPayment (register_vehicle): %s", e)
        elif "showroom xe" in item.get("category", "").lower():
            # ⚠️ Item có category Showroom xe nhưng không có vehicle_group → lỗi dữ liệu
            logger.error("processShopPayment(%s): category='%s' nhưng vehicle_group bị thiếu! Xe sẽ KHÔNG được đăng ký vào garage.", item_id, item.get("category", ""))

        # Tech
        if is_tech:
            try:
                from ..tech_system import register_tech
                register_tech(item_id, item)
            except Exception as e:
                logger.debug("processPayment (register_tech): %s", e)

        # Real Estate
        if item.get("is_real_estate"):
            try:
                from ..real_estate import add_property
                add_property(item_id, item)
            except Exception as e:
                logger.debug("processPayment (add_property): %s", e)

        # Digital assets
        if item.get("is_digital_asset"):
            try:
                from ..digital_assets import add_digital_asset
                add_digital_asset(item_id, item)
            except Exception as e:
                logger.debug("processPayment (add_digital_asset): %s", e)
            register_passive_effect(item_id, item)
            import uuid as _uuid2
            _active_effs = [
                e for e in get_item_effects(item)
                if e.get("type") in ACTIVE_TYPES
                and (e.get("cards", 0) > 0 or e.get("duration", 0) > 0 or e.get("expire_h", 0) > 0)
            ]
            if _active_effs:
                _slot_id = f"{item_id}_{str(_uuid2.uuid4())[:8]}"
                _expire_h = item.get("expire_h", _active_effs[0].get("expire_h", 72))
                register_food_purchase(item_id, _slot_id, _expire_h)
                _eff = _active_effs[0].copy()
                if len(_active_effs) > 1:
                    _eff["_all_effects"] = _active_effs
                activate_boost(item_id, _eff, _slot_id)

        # SCT tax
        sct_amount = 0
        try:
            from ..tax_system import collect_sct, get_sct_for_item
            sct_info = get_sct_for_item(item)
            if sct_info["has_sct"]:
                sct_amount = collect_sct(item)
        except Exception as e:
            logger.debug("processPayment (SCT): %s", e)

        new_balance = get_balance()
        self.balanceChanged.emit(new_balance)

        logger.debug("processShopPayment(%s): hoàn tất — new_balance=%d", item_id, new_balance)
        return json.dumps({
            "ok":             True,
            "new_balance":    new_balance,
            "item_name":      item["name"],
            "is_food":        is_food,
            "is_study":       is_study,
            "is_real_estate": bool(item.get("is_real_estate")),
            "sct_amount":     sct_amount,
            "payment_method": method,
            "cash_used":      cash_amount,
            "card_used":      card_amount,
            "card_id":        card_id,
        }, ensure_ascii=False)

    # ── Inventory ──────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getInventory(self):
        inv = get_inventory()
        items_map = get_items_map()
        counts: dict = {}
        for iid in inv:
            counts[iid] = counts.get(iid, 0) + 1

        owned = []
        for iid, qty in counts.items():
            item = items_map.get(iid)
            if item:
                entry = {**item, "quantity": qty}
                url = get_image_url(iid)
                entry["image_url"] = url if url else ""
                owned.append(entry)

        return json.dumps(owned, ensure_ascii=False)

    # ── Transactions ───────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getTransactions(self):
        return json.dumps(get_transactions(), ensure_ascii=False)

    @pyqtSlot()
    def clearTransactions(self):
        clear_transactions()

    # ── Finance / Budget ───────────────────────────────────────────
    @pyqtSlot(result=str)
    def getFinanceData(self):
        reset_monthly_if_needed()
        status = get_budget_status()
        # Lấy thông tin chi phí sinh hoạt để hiển thị trong finance
        try:
            from ..living_costs import get_living_cost_status
            lc_status = get_living_cost_status()
        except Exception as e:
            logger.debug("getFinanceStatus (living_costs): %s", e)
            lc_status = {}
        # Tính tổng tài sản ròng (ví + ngân hàng + CK + crypto + BĐS + xe)
        try:
            from ..economy_controls import get_total_net_worth
            total_net_worth = get_total_net_worth()
        except Exception as e:
            logger.debug("getFinanceStatus (net_worth): %s", e)
            total_net_worth = 0
        return json.dumps({
            "budget":           get_budget(),
            "spending":         get_monthly_spending(),
            "income":           get_monthly_income(),
            "status":           status,
            "living_cost":      lc_status,
            "total_net_worth":  total_net_worth,
        })

    @pyqtSlot(int, result=bool)
    def setBudget(self, amount: int):
        set_budget(amount)
        return True

    # ── Bank: Không kỳ hạn ────────────────────────────────────────
    @pyqtSlot(result=str)
    def getBankData(self):
        return json.dumps({
            "demand_balance":  get_demand_balance(),
            "demand_interest": calc_demand_interest(),
            "demand_rate":     0.003,
            "total_savings":   get_total_savings(),
            "total_value":     get_total_current_value(),
            "wallet":          get_balance(),
            "savings":         get_savings(),
            "interest":        calculate_interest(),
            "send_more":       get_send_more_status(),
        })

    @pyqtSlot(int, result=str)
    def bankDeposit(self, amount: int):
        res = deposit_demand(amount)
        new_balance = get_balance()
        self.balanceChanged.emit(new_balance)
        return json.dumps({**res, "balance": new_balance,
                           "demand_balance": get_demand_balance()})

    @pyqtSlot(int, result=str)
    def bankWithdraw(self, amount: int):
        res = withdraw_demand(amount)
        new_balance = get_balance()
        self.balanceChanged.emit(new_balance)
        return json.dumps({**res, "balance": new_balance,
                           "demand_balance": get_demand_balance()})

    @pyqtSlot(result=str)
    def bankClaimInterest(self):
        interest = claim_demand_interest()
        new_balance = get_balance()
        self.balanceChanged.emit(new_balance)
        return json.dumps({"ok": interest > 0, "interest": interest,
                           "balance": new_balance})

    # ── Bank: Kỳ hạn ──────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getBankProducts(self):
        return json.dumps(get_bank_products(), ensure_ascii=False)

    @pyqtSlot(result=str)
    def getTermDeposits(self):
        return json.dumps(get_all_deposits_info(), ensure_ascii=False)

    @pyqtSlot(int, int, str, result=str)
    def openTermDeposit(self, amount: int, term_months: int, product_code: str):
        res = open_term_deposit(amount, term_months, product_code)
        if res["ok"]:
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def closeTermDeposit(self, deposit_id: str):
        res = close_term_deposit(deposit_id, force=False)
        if res["ok"]:
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def forceCloseTermDeposit(self, deposit_id: str):
        res = close_term_deposit(deposit_id, force=True)
        if res["ok"]:
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, int, result=str)
    def addTermDepositFunds(self, deposit_id: str, amount: int):
        res = add_term_funds(deposit_id, amount)
        if res["ok"]:
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    # ── Bank: Lãi tức thì ─────────────────────────────────────────
    @pyqtSlot(result=str)
    def getInstantInterestStatus(self):
        """Trả về trạng thái kỹ năng thu lãi tức thì."""
        return json.dumps(get_instant_interest_status(), ensure_ascii=False)

    @pyqtSlot(result=str)
    def claimInstantInterest(self):
        """Thu lãi tức thì từ tất cả sổ tiết kiệm có kỳ hạn."""
        res = claim_instant_term_interest()
        if res.get("ok"):
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    # ── Image helpers ──────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getImagesDir(self):
        return get_images_dir()

    @pyqtSlot()
    def refreshImageCache(self):
        clear_cache()

    @pyqtSlot(result=str)
    def getAvailableImages(self):
        return json.dumps(list_available_images())

    # ── Again Tracker ─────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getAgainSummary(self):
        return json.dumps({
            "today": get_today_summary(),
            "count": get_daily_again_count(),
            "penalty": get_daily_penalty_total(),
        })

    # ── Reset ──────────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getConfirmPhrase(self):
        """Trả về cụm xác nhận reset."""
        return get_confirm_phrase()

    @pyqtSlot(str, result=str)
    def performReset(self, confirm_input: str):
        return json.dumps(perform_reset(confirm_input), ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def performHardReset(self, confirm_input: str):
        from ..reset_manager import perform_hard_reset
        return json.dumps(perform_hard_reset(confirm_input), ensure_ascii=False)

    @pyqtSlot(result=str)
    def getResetLog(self):
        return json.dumps(get_reset_log(), ensure_ascii=False)

    # ── Food Boosts ────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getActiveBoosts(self):
        return json.dumps(get_boosts_summary(), ensure_ascii=False)

    @pyqtSlot(result=str)
    def getDailyLimits(self):
        """Trả về thông tin daily limit cho food/drink."""
        return json.dumps(get_daily_limits_info(), ensure_ascii=False)

    @pyqtSlot(str, str, result=str)
    def activateFoodBoost(self, item_id: str, slot_id: str):
        items_map = get_items_map()
        item  = items_map.get(item_id)
        if not item:
            return json.dumps({"ok": False, "error": "Không tìm thấy sản phẩm."})
        effect = get_effect_for_item(item_id, item)
        res    = activate_boost(item_id, effect, slot_id)
        if res["ok"]:
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def deactivateBoost(self, slot_id: str):
        """
        Hủy kích hoạt 1 boost (thức ăn/đồ học tập) đang active.
        - Kiểm tra daily cancel limit (mặc định 10, mở rộng đến 20)
        - Mỗi 10 thẻ học hợp lệ (≥10s) thêm 1 lần hủy
        - Không hoàn tiền
        """
        from ..food_effects import deactivate_boost
        res = deactivate_boost(slot_id)
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getDailyCancelInfo(self):
        """
        Trả về thông tin giới hạn hủy boost hôm nay cho UI.
        """
        from ..food_effects import get_daily_cancel_limit
        return json.dumps(get_daily_cancel_limit(), ensure_ascii=False)

    # ── Vehicle & Garage ──────────────────────────────────────────
    @pyqtSlot(result=str)
    def getGarageData(self):
        from ..vehicle_system import get_garage_summary, get_total_garage_slots, get_active_vehicle
        vehicles = get_garage_summary()
        logger.info("getGarageData: có %d xe trong garage", len(vehicles))
        data = {
            "garage": vehicles,
            "total_slots": get_total_garage_slots(),
            "active_vehicle": get_active_vehicle(),
        }
        return json.dumps(data, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getVehicleDiagnostic(self):
        """Trả về diagnostic data cho hệ thống xe — gọi từ JS console: JSON.parse(await B.getVehicleDiagnostic())"""
        from ..vehicle_system import (_get_data, get_garage_summary, get_total_garage_slots,
                                       _KEY_VEHICLE, get_active_vehicle)
        from .._safe_config import _config_cache, cfg_dict
        from aqt import mw
        import time
        result = {"ok": True}
        try:
            # 1. Anki config raw
            raw = mw.col.get_config(_KEY_VEHICLE, None)
            result["anki_config_raw"] = raw
            if isinstance(raw, dict):
                result["anki_garage_size"] = len(raw.get("garage", {}))
                result["anki_garage_keys"] = list(raw.get("garage", {}).keys())
            else:
                result["anki_config_type"] = type(raw).__name__ if raw is not None else "None"
        except Exception as e:
            result["anki_config_error"] = str(e)

        # 2. Cache info
        try:
            entry = _config_cache.get(_KEY_VEHICLE)
            if entry is not None:
                val, ts = entry
                age = time.time() - ts
                result["cache_age"] = round(age, 1)
                result["cache_hit"] = True
                if isinstance(val, dict):
                    result["cache_garage_size"] = len(val.get("garage", {}))
                    result["cache_garage_keys"] = list(val.get("garage", {}).keys())
                else:
                    result["cache_val_type"] = type(val).__name__
            else:
                result["cache_hit"] = False
        except Exception as e:
            result["cache_error"] = str(e)

        # 3. get_garage_summary()
        try:
            summary = get_garage_summary()
            result["summary_count"] = len(summary)
            result["summary_ids"] = [v.get("item_id") for v in summary]
            result["summary_names"] = [v.get("name") for v in summary]
        except Exception as e:
            result["summary_error"] = str(e)
            import traceback
            result["summary_traceback"] = traceback.format_exc()

        # 4. get_total_garage_slots()
        try:
            result["total_slots"] = get_total_garage_slots()
        except Exception as e:
            result["slots_error"] = str(e)

        # 5. col_ready()
        try:
            from .._safe_config import col_ready
            result["col_ready"] = col_ready()
        except Exception as e:
            result["col_ready_error"] = str(e)

        return json.dumps(result, ensure_ascii=False, default=str)

    @pyqtSlot(str, result=str)
    def selectVehicle(self, vehicle_id: str):
        from ..vehicle_system import select_vehicle
        res = select_vehicle(vehicle_id)
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(result=str)
    def stopVehicle(self):
        from ..vehicle_system import stop_vehicle
        res = stop_vehicle()
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def startRepair(self, vehicle_id: str):
        from ..vehicle_system import start_repair
        res = start_repair(vehicle_id)
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def doMaintenance(self, vehicle_id: str):
        from ..vehicle_system import do_maintenance
        res = do_maintenance(vehicle_id)
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def refuelVehicle(self, vehicle_id: str):
        from ..vehicle_system import refuel_vehicle
        res = refuel_vehicle(vehicle_id)
        if res.get("ok"):
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def rechargeVehicle(self, vehicle_id: str):
        from ..vehicle_system import recharge_vehicle
        res = recharge_vehicle(vehicle_id)
        if res.get("ok"):
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def sellVehicle(self, vehicle_id: str):
        from ..vehicle_system import sell_vehicle
        res = sell_vehicle(vehicle_id)
        if res.get("ok"):
            # Dọn legacy: xe cũ có thể còn trong inventory (mua trước khi fix)
            try:
                from ..inventory import remove_from_inventory
                remove_from_inventory(vehicle_id)
            except Exception as e:
                logger.debug("sellVehicle (remove legacy): %s", e)
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def getRepairCost(self, vehicle_id: str):
        from ..vehicle_system import get_repair_cost_preview
        return json.dumps(get_repair_cost_preview(vehicle_id), ensure_ascii=False)

    @pyqtSlot(result=str)
    def getGarageSlotInfo(self):
        from ..vehicle_system import get_total_garage_slots, get_slot_buy_price, MAX_GARAGE_SLOTS, get_garage_slots_bought
        return json.dumps({
            "total_slots": get_total_garage_slots(),
            "bought": get_garage_slots_bought(),
            "max_slots": MAX_GARAGE_SLOTS,
            "buy_price": get_slot_buy_price(),
        }, ensure_ascii=False)

    @pyqtSlot(result=str)
    def buyGarageSlot(self):
        from ..vehicle_system import buy_garage_slot
        res = buy_garage_slot()
        if res.get("ok"):
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def quickMaintenance(self, vehicle_id: str):
        from ..vehicle_system import quick_maintenance
        res = quick_maintenance(vehicle_id)
        if res.get("ok"):
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getVehicleEffects(self):
        """
        Trả về hiệu ứng và trạng thái của xe đang active (v1.1.5b).
        Bao gồm: energy_save_percent, km_traveled, total_cards_driven, v.v.
        """
        try:
            from ..vehicle_system import get_active_vehicle, get_active_vehicle_effects
            av = get_active_vehicle()
            if not av:
                return json.dumps({"active": False}, ensure_ascii=False)
            effects = get_active_vehicle_effects()
            return json.dumps({
                "active": True,
                "vehicle_id": av.get("item_id") or av.get("vehicle_id"),
                "name": av.get("name", ""),
                "emoji": av.get("emoji", "🚗"),
                "vehicle_group": av.get("vehicle_group", ""),
                "fuel_type": av.get("fuel_type", "gasoline"),
                "durability_pct": round(av.get("durability", 0) / max(av.get("max_durability", 1), 1) * 100, 1),
                "fuel_pct": round(av.get("fuel_level", 0) / max(av.get("max_fuel", 1), 1) * 100, 1),
                "km_traveled": float(av.get("km_traveled", 0.0)),
                "total_cards_driven": int(av.get("total_cards_driven", 0)),
                "energy_save_percent": round(float(av.get("energy_save_percent", 0.0)) * 100, 1),
                "effects": effects,
            }, ensure_ascii=False)
        except Exception as e:
            logger.warning("getVehicleEffects: %s", e)
            return json.dumps({"active": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getVehicleEnergySaveInfo(self):
        """
        Trả về thông tin tiết kiệm năng lượng của xe đang active cho UI.
        """
        try:
            from ..vehicle_effects import calc_effective_energy_cost, get_active_vehicle_energy_save, get_active_vehicle_km
            save_pct = get_active_vehicle_energy_save()
            km = get_active_vehicle_km()
            cost_info = calc_effective_energy_cost(1)
            return json.dumps({
                "energy_save_percent": round(save_pct * 100, 1),
                "km_traveled": km,
                "actual_cost": cost_info.get("actual", 1),
                "saved": cost_info.get("saved", 0),
                "has_vehicle": save_pct > 0,
            }, ensure_ascii=False)
        except Exception as e:
            logger.warning("getVehicleEnergySaveInfo: %s", e)
            return json.dumps({"energy_save_percent": 0, "km_traveled": 0, "has_vehicle": False}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getMaintenanceTabData(self):
        from ..vehicle_system import get_maintenance_tab_data
        return json.dumps(get_maintenance_tab_data(), ensure_ascii=False)

    @pyqtSlot(result=str)
    def checkSpoiledFood(self):
        spoiled = check_and_spoil_food()
        return json.dumps(spoiled, ensure_ascii=False)

    # ── Tech Lab ────────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getTechLabData(self):
        """Trả về danh sách tech items trong tech lab."""
        from ..tech_system import get_tech_summary, get_active_tech
        tech_list = get_tech_summary()
        active = get_active_tech()
        return json.dumps({
            "tech_lab": tech_list,
            "active_tech": active,
        }, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def activateTech(self, item_id: str):
        """Kích hoạt tech item."""
        from ..tech_system import activate_tech
        res = activate_tech(item_id)
        if res.get("ok"):
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(result=str)
    def deactivateTech(self):
        """Tắt tech item đang active."""
        from ..tech_system import deactivate_tech
        res = deactivate_tech()
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def repairTech(self, item_id: str):
        """Sửa chữa tech item."""
        from ..tech_system import start_repair
        res = start_repair(item_id)
        if res.get("ok"):
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def maintainTech(self, item_id: str):
        """Bảo dưỡng tech item."""
        from ..tech_system import do_maintenance
        res = do_maintenance(item_id)
        if res.get("ok"):
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def sellTech(self, item_id: str):
        """Bán tech item."""
        from ..tech_system import sell_tech
        res = sell_tech(item_id)
        if res.get("ok"):
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def getTechRepairCost(self, item_id: str):
        """Xem trước chi phí sửa chữa tech item."""
        from ..tech_system import get_repair_cost_preview
        return json.dumps(get_repair_cost_preview(item_id), ensure_ascii=False)

    # ── Passive Effects & Item Effects ──────────────────────────────
    @pyqtSlot(result=str)
    def getPassiveEffects(self):
        """Trả về danh sách passive effects đang active."""
        return json.dumps(get_passive_effects_summary(), ensure_ascii=False)

    @pyqtSlot(result=str)
    def getPassiveEffectsAggregated(self):
        """Trả về dict gộp tất cả passive effects (dùng cho game logic)."""
        return json.dumps(get_all_passive_effects(), ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def getItemEffects(self, item_id: str):
        """Trả về mô tả effect của 1 item."""
        items_map = get_items_map()
        item = items_map.get(item_id)
        if not item:
            return json.dumps([])
        descs = get_item_effect_descriptions(item)
        return json.dumps(descs, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getInventoryWithFreshness(self):
        """
        Inventory kèm freshness info cho đồ ăn.
        FIX: truyền đúng slot_id thực từ freshness dict thay vì hardcode _0.
        """
        inv   = get_inventory()
        items_map = get_items_map()
        fresh = _get_fresh()   # {slot_id: {item_id, buy_ts, expire_h}}

        counts: dict = {}
        for iid in inv:
            counts[iid] = counts.get(iid, 0) + 1

        # Nhóm slot theo item_id: {item_id: [slot_id, ...]}
        slots_by_item: dict = {}
        for sid, info in fresh.items():
            iid = info.get("item_id", "")
            if iid:
                slots_by_item.setdefault(iid, []).append(sid)

        owned = []
        for iid, qty in counts.items():
            item = items_map.get(iid)
            if not item:
                continue
            entry = {**item, "quantity": qty}
            url = get_image_url(iid)
            entry["image_url"] = url if url else ""

            item_cat = _get_item_category(iid, item)
            if item_cat in ("food", "drink") or item_cat == "study":
                effect = get_effect_for_item(iid, item)
                entry["effect"]    = effect
                entry["is_food"]   = (item_cat in ("food", "drink"))
                entry["is_study"]  = (item_cat == "study")
                entry["expire_h"]  = item.get("expire_h", effect.get("expire_h", 24))

                # Lấy tất cả slot thực còn trong freshness dict
                real_slots = slots_by_item.get(iid, [])
                entry["food_slots"] = []
                now = time.time()
                for sid in real_slots:
                    info = fresh[sid]
                    buy_ts   = float(info.get("buy_ts", now))
                    expire_h = float(info.get("expire_h", 24))
                    elapsed_h = (now - buy_ts) / 3600
                    remaining_h = max(0.0, expire_h - elapsed_h)
                    fresh_pct = round(remaining_h / expire_h * 100, 1) if expire_h > 0 else 0
                    entry["food_slots"].append({
                        "slot_id":     sid,
                        "remaining_h": round(remaining_h, 2),
                        "fresh_pct":   fresh_pct,
                    })
                # Slot đầu tiên là slot dùng được (nếu còn)
                entry["active_slot"] = real_slots[0] if real_slots else ""
            else:
                entry["is_food"]    = False
                entry["is_study"]   = False
                entry["food_slots"] = []
                entry["active_slot"] = ""
                # Passive effect descriptions cho non-food items
                from ..item_effects import get_item_effect_descriptions, format_item_effects_html, get_item_effects
                eff_list = get_item_effects(item)
                if eff_list:
                    entry["effect_descriptions"] = get_item_effect_descriptions(item)
                    entry["effect_html"] = format_item_effects_html(eff_list)
            owned.append(entry)

        return json.dumps(owned, ensure_ascii=False)

    # ── Tax ───────────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getTaxStatus(self):
        from ..tax_system import get_tax_status_today
        return json.dumps(get_tax_status_today())

    @pyqtSlot(result=str)
    def getTaxLog(self):
        from ..tax_system import get_tax_log
        return json.dumps(get_tax_log(), ensure_ascii=False)

    # ── Goal (Mục tiêu) ───────────────────────────────────────────
    @pyqtSlot(result=str)
    def getGoal(self):
        from ..goals import get_goal
        return json.dumps(get_goal(), ensure_ascii=False)

    @pyqtSlot(str, str, int, str, result=str)
    def setGoal(self, item_id: str, item_name: str, item_price: int, item_emoji: str):
        from ..goals import set_goal
        return json.dumps(set_goal(item_id, item_name, item_price, item_emoji), ensure_ascii=False)

    @pyqtSlot(result=str)
    def clearGoal(self):
        from ..goals import clear_goal
        res = clear_goal()
        return json.dumps(res, ensure_ascii=False)

    # ── Streak (Tier 1) ───────────────────────────────────────────
    @pyqtSlot(result=str)
    def getStreakStatus(self):
        from ..streak_system import get_streak_status
        return json.dumps(get_streak_status(), ensure_ascii=False)

    # ── Rank (Tier 1) ─────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getRankStatus(self):
        from ..rank_system import get_rank_status
        return json.dumps(get_rank_status(), ensure_ascii=False)

    @pyqtSlot(result=str)
    def getAllRanks(self):
        from ..rank_system import get_all_ranks
        return json.dumps(get_all_ranks(), ensure_ascii=False)

    # ── Daily Quest (Tier 1) ──────────────────────────────────────
    @pyqtSlot(result=str)
    def getQuestSummary(self):
        from ..daily_quest import get_quest_summary
        return json.dumps(get_quest_summary(), ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def claimQuestReward(self, quest_id: str):
        from ..daily_quest import claim_quest_reward
        res = claim_quest_reward(quest_id)
        if res.get("ok") and res.get("money", 0) > 0:
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    # ── Debug ──────────────────────────────────────────────────────
    @pyqtSlot(int)
    def addBalance(self, amount: int):
        new_bal = get_balance() + amount
        set_balance_and_log(new_bal, "debug", amount, "Debug add balance")
        self.balanceChanged.emit(new_bal)

    @pyqtSlot(result=str)
    def runDebugTools(self):
        """Chạy công cụ gỡ lỗi: quét + sửa lỗi dữ liệu, xoá cache."""
        try:
            from ..debug_tools import run_debug_tools
            result = run_debug_tools()
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getDebugReport(self):
        """Trả về báo cáo tổng quan hệ thống (chỉ đọc, không sửa)."""
        try:
            from ..debug_tools import get_debug_report
            result = get_debug_report()
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    # ── Real Estate ───────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getPortfolio(self):
        from ..real_estate import get_portfolio_status
        return json.dumps(get_portfolio_status(), ensure_ascii=False)

    @pyqtSlot(str, int, result=str)
    def setRentPrice(self, slot_id: str, rent_price: int):
        from ..real_estate import set_rent_price
        return json.dumps(set_rent_price(slot_id, rent_price), ensure_ascii=False)

    @pyqtSlot(result=str)
    def collectAllRent(self):
        from ..real_estate import collect_all_rent
        res = collect_all_rent()
        if res.get("net", 0) > 0:
            self.balanceChanged.emit(get_balance())
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def removeProperty(self, slot_id: str):
        from ..real_estate import remove_property
        return json.dumps(remove_property(slot_id), ensure_ascii=False)

    @pyqtSlot(int, int, result=str)
    def calcSatisfaction(self, rent_price: int, fair_rent: int):
        from ..real_estate import calc_satisfaction
        return json.dumps(calc_satisfaction(rent_price, fair_rent), ensure_ascii=False)

    @pyqtSlot(result=str)
    def getREMarketValues(self):
        """Trả về market value hiện tại của tất cả BĐS."""
        try:
            from ..real_estate import get_all_market_values
            return json.dumps(get_all_market_values(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def getPropertyUpgradeInfo(self, slot_id: str):
        """Thông tin nâng cấp của 1 BĐS."""
        try:
            from ..real_estate import get_upgrade_info
            return json.dumps(get_upgrade_info(slot_id), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def upgradeProperty(self, slot_id: str):
        """Nâng cấp BĐS."""
        try:
            from ..real_estate import upgrade_property
            res = upgrade_property(slot_id)
            if res.get("ok"):
                self.balanceChanged.emit(get_balance())
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getRESummary(self):
        """Tổng quan danh mục BĐS."""
        try:
            from ..real_estate import get_re_summary
            return json.dumps(get_re_summary(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    # ── Knowledge Base ────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getAllNotes(self):
        from ..knowledge_base import get_all_notes
        return json.dumps(get_all_notes(), ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def getNoteById(self, note_id: str):
        from ..knowledge_base import get_note
        n = get_note(note_id)
        return json.dumps(n or {}, ensure_ascii=False)

    @pyqtSlot(str, str, str, str, str, result=str)
    def createNote(self, title: str, body: str, category: str,
                   emoji: str, tags_json: str):
        from ..knowledge_base import create_note
        import json as _j
        tags = _j.loads(tags_json) if tags_json else []
        note = create_note(title, body, category, tags, emoji)
        return json.dumps({"ok": bool(note), "note": note}, ensure_ascii=False)

    @pyqtSlot(str, str, str, str, str, str, result=str)
    def updateNote(self, note_id: str, title: str, body: str,
                   category: str, emoji: str, tags_json: str):
        from ..knowledge_base import update_note
        import json as _j
        tags = _j.loads(tags_json) if tags_json else []
        res  = update_note(note_id, title=title, body=body,
                           category=category, emoji=emoji, tags=tags)
        return json.dumps(res, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def deleteNote(self, note_id: str):
        from ..knowledge_base import delete_note
        return json.dumps(delete_note(note_id), ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def togglePin(self, note_id: str):
        from ..knowledge_base import toggle_pin
        return json.dumps(toggle_pin(note_id), ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def searchNotes(self, query: str):
        from ..knowledge_base import search_notes
        return json.dumps(search_notes(query), ensure_ascii=False)

    @pyqtSlot(result=str)
    def getCategories(self):
        from ..knowledge_base import get_categories
        return json.dumps(get_categories(), ensure_ascii=False)

    # ── Balance ─────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getBalance(self):
        """Trả về số dư hiện tại dạng số nguyên."""
        return str(get_balance())

    # ── Stock Market ────────────────────────────────────────────
    @pyqtSlot(str, int, result=str)
    def buyStock(self, symbol: str, shares: int):
        from ..stock_market import buy_stock
        try:
            res = buy_stock(symbol, shares)
            if res.get("ok"):
                self.balanceChanged.emit(res.get("new_balance", 0))
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, result=str)
    def sellStock(self, symbol: str, shares: int):
        from ..stock_market import sell_stock
        try:
            res = sell_stock(symbol, shares)
            if res.get("ok"):
                self.balanceChanged.emit(res.get("new_balance", 0))
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, result=str)
    def getStockHistory(self, symbol: str, limit: int = 50):
        from ..stock_market import get_stock_history
        try:
            data = get_stock_history(symbol, limit)
            return json.dumps({"ok": True, "data": data}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    # ── Stock Market Phase 2: Combined Data + Session Info ──

    @pyqtSlot(result=str)
    def getStockAllData(self):
        """
        Trả về tất cả dữ liệu CK trong 1 lần gọi.
        Fix triệt để lỗi bất đồng bộ giữa market list và portfolio.
        """
        try:
            from ..stock_market import get_all_stock_data
            data = get_all_stock_data()
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, result=str)
    def getDividendHistory(self, symbol: str = "", limit: int = 20):
        """Lịch sử cổ tức đã nhận."""
        try:
            from ..stock_market import get_dividend_history
            data = get_dividend_history(symbol or None, limit)
            return json.dumps({"ok": True, "data": data}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getDividendSummary(self):
        """Tổng quan cổ tức."""
        try:
            from ..stock_market import get_dividend_summary
            return json.dumps(get_dividend_summary(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @pyqtSlot(int, result=str)
    def getCorporateActionHistory(self, limit: int = 20):
        """Lịch sử sự kiện doanh nghiệp."""
        try:
            from ..stock_market import get_corporate_action_history
            data = get_corporate_action_history(limit)
            return json.dumps({"ok": True, "data": data}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    # ── Digital Assets (Tài sản số) ──────────────────────────
    @pyqtSlot(result=str)
    def getCryptoAllData(self):
        try:
            from ..item_effects import repair_crypto_passive_effects
            repair_crypto_passive_effects()
            from ..digital_assets import get_all_crypto_data
            data = get_all_crypto_data()
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, result=str)
    def buyCrypto(self, symbol: str, amount_vnd: int):
        try:
            from ..digital_assets import buy_crypto
            res = buy_crypto(symbol, amount_vnd)
            if res.get("ok"):
                self.balanceChanged.emit(res.get("new_balance", 0))
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, float, result=str)
    def sellCrypto(self, symbol: str, sell_pct: float):
        try:
            from ..digital_assets import sell_crypto
            res = sell_crypto(symbol, sell_pct)
            if res.get("ok"):
                self.balanceChanged.emit(res.get("new_balance", 0))
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, float, result=str)
    def stakeCrypto(self, symbol: str, stake_pct: float):
        try:
            from ..digital_assets import stake_crypto
            return json.dumps(stake_crypto(symbol, stake_pct), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def unstakeCrypto(self, stake_id: str):
        try:
            from ..digital_assets import unstake_crypto
            res = unstake_crypto(stake_id)
            if res.get("ok"):
                self.balanceChanged.emit(get_balance())
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, result=str)
    def getCryptoHistory(self, symbol: str, limit: int = 50):
        try:
            from ..digital_assets import get_crypto_history
            data = get_crypto_history(symbol, limit)
            return json.dumps({"ok": True, "data": data}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def collectStakingYield(self):
        try:
            from ..digital_assets import collect_staking_yield
            res = collect_staking_yield()
            if res.get("ok") and res.get("yield_vnd", 0) > 0:
                self.balanceChanged.emit(get_balance())
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getCryptoMarketCycle(self):
        try:
            from ..digital_assets import get_market_cycle_info
            return json.dumps(get_market_cycle_info(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getTradingSessionInfo(self):
        """Trả về thông tin phiên giao dịch + đếm ngược."""
        try:
            from ..stock_market import get_trading_session_info
            info = get_trading_session_info()
            return json.dumps(info, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"in_session": False, "error": str(e)}, ensure_ascii=False)

    # ── Limit / Stop-Loss Orders ──────────────────────────────────
    @pyqtSlot(str, str, int, int, str, result=str)
    def placeLimitOrder(self, symbol: str, order_type: str, trigger_price: int,
                        quantity: int, direction: str):
        """Đặt lệnh Limit / Stop-Loss."""
        try:
            from ..stock_market import place_limit_order
            res = place_limit_order(symbol, order_type, trigger_price, quantity, direction)
            if res.get("ok"):
                from ..balance import get_balance
                self.balanceChanged.emit(get_balance())
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def cancelLimitOrder(self, order_id: str):
        """Huỷ lệnh limit/stop-loss."""
        try:
            from ..stock_market import cancel_limit_order
            res = cancel_limit_order(order_id)
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def getLimitOrders(self, status: str = ""):
        """Lấy danh sách limit/stop-loss orders."""
        try:
            from ..stock_market import get_limit_orders
            s = status if status else None
            orders = get_limit_orders(s)
            return json.dumps(orders, ensure_ascii=False)
        except Exception as e:
            return json.dumps([], ensure_ascii=False)

    # ── Market News ───────────────────────────────────────────────
    @pyqtSlot(int, result=str)
    def getMarketNews(self, limit: int = 10):
        """Lấy lịch sử tin tức thị trường."""
        try:
            from ..stock_market import get_market_news
            news = get_market_news(limit)
            return json.dumps(news, ensure_ascii=False)
        except Exception as e:
            return json.dumps([], ensure_ascii=False)

    @pyqtSlot(result=str)
    def getCurrentNews(self):
        """Lấy tin tức của cycle hiện tại."""
        try:
            from ..stock_market import get_current_news
            news = get_current_news()
            return json.dumps(news, ensure_ascii=False)
        except Exception as e:
            return json.dumps([], ensure_ascii=False)

    # ── Housing / Living Costs ────────────────────────────────────
    @pyqtSlot(result=str)
    def syncLivingCosts(self):
        """Đồng bộ chi phí sinh hoạt 1 lần an toàn trước khi UI tải."""
        try:
            from ..living_costs import collect_daily_living_costs
            result = collect_daily_living_costs()
            if result.get("collected") or result.get("loan", {}).get("borrowed", 0) > 0:
                self.balanceChanged.emit(get_balance())
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getResidenceInfo(self):
        """Nơi ở hiện tại + chi phí sinh hoạt."""
        try:
            from ..living_costs import get_living_cost_status
            return json.dumps(get_living_cost_status(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getAvailableResidences(self):
        """Danh sách nơi ở có thể chọn."""
        try:
            from ..housing_residence import get_all_residences_for_ui
            return json.dumps(get_all_residences_for_ui(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def previewChangeResidence(self, new_id: str):
        """Xem trước chi phí khi chuyển nơi ở (chưa thực hiện)."""
        try:
            from ..housing_residence import RESIDENCES, get_monthly_land_tax
            if new_id not in RESIDENCES:
                return json.dumps({"ok": False, "error": "Không tìm thấy."})
            info = RESIDENCES[new_id]
            current_bal = get_balance()
            can_afford = True
            if info["type"] == "buy":
                can_afford = current_bal >= info["purchase_price"]
            return json.dumps({
                "ok":         True,
                "info":       info,
                "can_afford": can_afford,
                "balance":    current_bal,
                "monthly_land_tax": get_monthly_land_tax(info) if info["type"] == "buy" else 0,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def changeResidence(self, new_id: str):
        """Thực sự chuyển nơi ở (nếu mua thì trừ tiền)."""
        try:
            from ..housing_residence import RESIDENCES, change_residence
            if new_id not in RESIDENCES:
                return json.dumps({"ok": False, "error": "Không tìm thấy."})
            info = RESIDENCES[new_id]
            force_buy = info["type"] == "buy"
            res = change_residence(new_id, force_buy=force_buy)
            if res["ok"]:
                self.balanceChanged.emit(get_balance())
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def sellResidence(self):
        """Bán nhà đang ở (chỉ nhà mua đứt)."""
        try:
            from ..housing_residence import sell_residence
            res = sell_residence()
            if res.get("ok"):
                self.balanceChanged.emit(get_balance())
            return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getLoanStatus(self):
        """Thông tin khoản vay nóng hiện tại."""
        try:
            from ..loan_system import get_loan_info, get_loan_log
            info = get_loan_info()
            info["log"] = get_loan_log()[:10]
            return json.dumps(info, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    # ── Credit Banking Nâng cao ──────────────────────────────────────

    @pyqtSlot(result=str)
    def getCreditScore(self):
        """Điểm tín dụng hiện tại."""
        try:
            from ..credit_banking import get_credit_score_info
            return json.dumps(get_credit_score_info(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getCreditCardProducts(self):
        """Danh sách sản phẩm thẻ tín dụng."""
        try:
            from ..credit_banking import get_credit_card_products
            return json.dumps({"ok": True, "products": get_credit_card_products()}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def applyCreditCard(self, product_code: str):
        """Đăng ký mở thẻ tín dụng."""
        try:
            from ..credit_banking import apply_credit_card
            result = apply_credit_card(product_code)
            if result.get("ok"):
                self.balanceChanged.emit(result.get("new_balance", 0))
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getMyCreditCards(self):
        """Danh sách thẻ tín dụng đang sở hữu."""
        try:
            from ..credit_banking import get_my_credit_cards
            return json.dumps(get_my_credit_cards(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, str, str, result=str)
    def useCreditCard(self, card_id: str, amount: int, merchant: str, category: str):
        """Thanh toán bằng thẻ tín dụng."""
        try:
            from ..credit_banking import use_credit_card
            return json.dumps(use_credit_card(card_id, amount, merchant, category), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, result=str)
    def payCreditCard(self, card_id: str, amount: int):
        """Thanh toán dư nợ thẻ tín dụng."""
        try:
            from ..credit_banking import pay_credit_card
            result = pay_credit_card(card_id, amount)
            if result.get("ok"):
                self.balanceChanged.emit(result.get("balance", 0))
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def getCreditCardStatement(self, card_id: str):
        """Sao kê chi tiết thẻ tín dụng."""
        try:
            from ..credit_banking import get_credit_card_statement
            return json.dumps(get_credit_card_statement(card_id), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getLoanProducts(self):
        """Danh sách sản phẩm vay ngân hàng."""
        try:
            from ..credit_banking import get_loan_products
            return json.dumps({"ok": True, "products": get_loan_products()}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getRepaymentMethods(self):
        """Danh sách phương thức trả nợ."""
        try:
            from ..credit_banking import get_repayment_methods
            return json.dumps({"ok": True, "methods": get_repayment_methods()}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(int, float, int, str, bool, result=str)
    def calcLoanInstallment(self, principal: int, annual_rate: float, tenure_months: int,
                             method: str, is_floating: bool):
        """Tính toán khoản trả hàng tháng."""
        try:
            from ..credit_banking import calculate_loan_installment
            result = calculate_loan_installment(principal, annual_rate, tenure_months, method, is_floating)
            if "error" not in result:
                result["ok"] = True
                result["monthly_payment"] = result.get("first_installment", 0)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, int, str, bool, result=str)
    def applyForLoan(self, product_code: str, amount: int, tenure_months: int,
                      repayment_method: str, use_floating_rate: bool):
        """Đăng ký vay ngân hàng."""
        try:
            from ..credit_banking import apply_for_loan
            result = apply_for_loan(product_code, amount, tenure_months, repayment_method, use_floating_rate)
            if result.get("ok"):
                self.balanceChanged.emit(result.get("new_balance", 0))
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getMyLoans(self):
        """Danh sách khoản vay đang có."""
        try:
            from ..credit_banking import get_my_loans
            return json.dumps({"ok": True, "loans": get_my_loans()}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, bool, result=str)
    def repayLoan(self, loan_id: str, amount: int, extra_principal: bool):
        """Trả nợ khoản vay."""
        try:
            from ..credit_banking import repay_loan_installment
            result = repay_loan_installment(loan_id, amount, extra_principal)
            if result.get("ok"):
                self.balanceChanged.emit(result.get("new_balance", 0))
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, int, result=str)
    def restructureLoan(self, loan_id: str, new_tenure_months: int):
        """Gia hạn / cơ cấu lại nợ."""
        try:
            from ..credit_banking import restructure_loan
            return json.dumps(restructure_loan(loan_id, new_tenure_months), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getCollateralSummary(self):
        """Tổng quan tài sản thế chấp."""
        try:
            from ..credit_banking import get_collateral_summary
            return json.dumps(get_collateral_summary(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getMyCollaterals(self):
        """Danh sách tài sản thế chấp."""
        try:
            from ..credit_banking import get_my_collaterals
            return json.dumps(get_my_collaterals(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, str, int, str, result=str)
    def registerCollateral(self, collateral_type: str, asset_id: str,
                            estimated_value: int, description: str):
        """Đăng ký tài sản thế chấp."""
        try:
            from ..credit_banking import register_collateral
            return json.dumps(register_collateral(collateral_type, asset_id, estimated_value, description), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def removeCollateral(self, collateral_id: str):
        """Xóa tài sản thế chấp."""
        try:
            from ..credit_banking import remove_collateral
            return json.dumps(remove_collateral(collateral_id), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def verifyIncome(self):
        """Chứng minh thu nhập qua học Anki và tài sản."""
        try:
            from ..credit_banking import verify_income
            result = verify_income()
            result["ok"] = True
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getIncomeStatus(self):
        """Trạng thái chứng minh thu nhập."""
        try:
            from ..credit_banking import get_income_verification_status
            return json.dumps(get_income_verification_status(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getAnkiBackedBenefits(self):
        """Ưu đãi dựa trên thành tích học Anki."""
        try:
            from ..credit_banking import get_ankibacked_benefits
            return json.dumps(get_ankibacked_benefits(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getLoyaltyStatus(self):
        """Trạng thái khách hàng thân thiết."""
        try:
            from ..credit_banking import get_loyalty_status
            return json.dumps(get_loyalty_status(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getFullBankingSummary(self):
        """Tổng quan toàn bộ hệ thống ngân hàng nâng cao."""
        try:
            from ..credit_banking import get_full_banking_summary
            return json.dumps(get_full_banking_summary(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getLoanInsurancePlans(self):
        """Danh sách gói bảo hiểm khoản vay."""
        try:
            from ..credit_banking import get_loan_insurance_plans
            return json.dumps({"ok": True, "plans": get_loan_insurance_plans()}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, str, result=str)
    def buyLoanInsurance(self, loan_id: str, plan_id: str):
        """Mua bảo hiểm khoản vay."""
        try:
            from ..credit_banking import buy_loan_insurance
            result = buy_loan_insurance(loan_id, plan_id)
            if result.get("ok"):
                self.balanceChanged.emit(result.get("new_balance", 0))
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getBankingAllData(self):
        """Tất cả dữ liệu ngân hàng nâng cao trong 1 lần gọi."""
        try:
            from ..credit_banking import (
                get_credit_score_info, get_my_credit_cards, get_my_loans,
                get_collateral_summary, get_income_verification_status,
                get_loyalty_status, get_ankibacked_benefits
            )
            return json.dumps({
                "ok": True,
                "credit_score": get_credit_score_info(),
                "credit_cards": get_my_credit_cards(),
                "loans": get_my_loans(),
                "collateral": get_collateral_summary(),
                "income": get_income_verification_status(),
                "loyalty": get_loyalty_status(),
                "ankibacked": get_ankibacked_benefits(),
                "loan_products": [],
                "card_products": [],
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getFullTaxStatus(self):
        """Toàn bộ trạng thái thuế cho tab Thuế."""
        try:
            from ..tax_system import get_full_tax_status
            return json.dumps(get_full_tax_status(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def getSctForItem(self, item_id: str):
        """Xem thuế SCT của 1 item trước khi mua."""
        try:
            from ..tax_system import get_sct_for_item
            items_map = get_items_map()
            item  = items_map.get(item_id)
            if not item:
                return json.dumps({"has_sct": False})
            return json.dumps(get_sct_for_item(item), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
    # ── KN Perks (v1.1.5) ──────────────────────────────────────────

    @pyqtSlot(result=str)
    def getKNPerks(self):
        """Trả về toàn bộ thông tin KN Perks."""
        try:
            from ..kn_perks import get_kn_perks_summary
            return json.dumps(get_kn_perks_summary(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def unlockKNPerk(self, perk_id: str):
        """Mở khóa 1 perk bằng KN."""
        try:
            from ..kn_perks import unlock_perk
            result = unlock_perk(perk_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    # ── Rank / KN / EXP ──────────────────────────────────────────────


    @pyqtSlot(result=str)
    def getKN(self):
        """Trả về điểm Kiến Thức hiện tại."""
        try:
            from ..rank_system import get_kn
            return json.dumps({"kn": get_kn()}, ensure_ascii=False)
        except Exception as e:
            logger.debug("getKn: %s", e)
            return json.dumps({"kn": 0}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getExp(self):
        """Trả về EXP hiện tại."""
        try:
            from ..rank_system import get_xp
            return json.dumps({"xp": get_xp()}, ensure_ascii=False)
        except Exception as e:
            logger.debug("getExp: %s", e)
            return json.dumps({"xp": 0}, ensure_ascii=False)

    # ── Finance Quiz ──────────────────────────────────────────────────

    @pyqtSlot(result=str)
    def getQuizStats(self):
        """Trả về thống kê quiz: {correct, total, streak, best_streak, accuracy}."""
        try:
            from ..finance_quiz import get_quiz_stats
            return json.dumps(get_quiz_stats(), ensure_ascii=False)
        except Exception as e:
            logger.debug("getQuizStats: %s", e)
            return json.dumps({"correct": 0, "total": 0, "streak": 0, "best_streak": 0, "accuracy": 0}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getQuizSet(self):
        """Trả về bộ câu hỏi hiện tại (hoặc tạo mới)."""
        try:
            from ..finance_quiz import get_current_quiz_set, QUIZ_SET_SIZE
            data = get_current_quiz_set()
            return json.dumps({
                "quiz_set": data,
                "set_size": QUIZ_SET_SIZE,
            }, ensure_ascii=False)
        except Exception as e:
            logger.debug("getQuizSet: %s", e)
            return json.dumps({"quiz_set": [], "set_size": 12}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def newQuizSet(self):
        """Tạo bộ câu hỏi mới (không filter topic)."""
        try:
            from ..finance_quiz import get_quiz_set, QUIZ_SET_SIZE
            data = get_quiz_set()
            return json.dumps({
                "quiz_set": data,
                "set_size": QUIZ_SET_SIZE,
            }, ensure_ascii=False)
        except Exception as e:
            logger.debug("newQuizSet: %s", e)
            return json.dumps({"quiz_set": [], "set_size": 12}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getQuizTopics(self):
        """Trả về danh sách chủ đề quiz."""
        try:
            from ..finance_quiz import QUIZ_TOPICS
            return json.dumps(QUIZ_TOPICS, ensure_ascii=False)
        except Exception as e:
            logger.debug("getQuizTopics: %s", e)
            return json.dumps({}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def newQuizSetByTopic(self, topic: str):
        """Tạo bộ câu hỏi mới theo chủ đề."""
        try:
            from ..finance_quiz import get_quiz_set, QUIZ_SET_SIZE
            data = get_quiz_set(topic=topic)
            return json.dumps({
                "quiz_set": data,
                "set_size": QUIZ_SET_SIZE,
                "topic": topic,
            }, ensure_ascii=False)
        except Exception as e:
            logger.debug("newQuizSetByTopic: %s", e)
            return json.dumps({"quiz_set": [], "set_size": 12, "topic": ""}, ensure_ascii=False)

    @pyqtSlot(int, int, result=str)
    def submitQuizAnswer(self, q_index: int, selected: int):
        """Ghi nhận câu trả lời quiz."""
        try:
            from ..finance_quiz import record_quiz_answer
            result = record_quiz_answer(q_index, selected)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.debug("submitQuizAnswer: %s", e)
            return json.dumps({"error": "Lỗi xử lý câu trả lời"}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getQuizDailyInfo(self):
        """Trả về {correct_today, count, limit, remaining, next_reset_seconds, date}
        — hạn mức quiz + countdown timer."""
        try:
            from ..finance_quiz import get_daily_quiz_info
            return json.dumps(get_daily_quiz_info(), ensure_ascii=False)
        except Exception as e:
            logger.debug("getQuizDailyInfo: %s", e)
            return json.dumps({
                "correct_today": 0, "count": 0, "limit": 5, "remaining": 5,
                "next_reset_seconds": 0, "date": "",
            }, ensure_ascii=False)

    # ── Emergency Events ──────────────────────────────────────────────

    @pyqtSlot(result=str)
    def getEmergencyLog(self):
        """Trả về lịch sử sự kiện khẩn cấp (tối đa 30 sự kiện gần nhất)."""
        try:
            from ..emergency_events import get_emergency_log
            return json.dumps(get_emergency_log(), ensure_ascii=False)
        except Exception as e:
            logger.debug("getEmergencyLog: %s", e)
            return json.dumps([], ensure_ascii=False)

    # ── Auto Update ───────────────────────────────────────────────────

    @pyqtSlot(result=str)
    def getUpdateInfo(self):
        """Trả về thông tin version hiện tại + bản cập nhật (nếu có)."""
        try:
            from ..auto_update import get_current_version, get_latest_release_info
            info = {
                "current_version": get_current_version(),
                "latest": get_latest_release_info(),
            }
            return json.dumps(info, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def checkForUpdates(self):
        """Người dùng bấm nút 'Kiểm tra cập nhật' — force check đồng bộ."""
        try:
            from ..auto_update import force_check_update_sync
            result = force_check_update_sync()
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def downloadUpdate(self):
        """Người dùng bấm 'Cập nhật ngay' — tải và cài đặt bản mới từ branch main."""
        try:
            from ..auto_update import download_and_apply_update
            result = download_and_apply_update()
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    # ── Achievement ───────────────────────────────────────────────────

    @pyqtSlot(result=str)
    def getAllAchievements(self):
        """Trả về full danh sách achievement + progress/status cho UI."""
        try:
            from ..achievements import get_all_achievements
            return json.dumps(get_all_achievements(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def claimAchievementReward(self, achievement_id: str):
        """Claim reward của 1 achievement."""
        try:
            from ..achievements import claim_reward
            result = claim_reward(achievement_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getAchievementStats(self):
        """Trả về unlocked_count, total_count, recent_unlocked."""
        try:
            from ..achievements import get_unlocked_count, get_total_count, get_recent_unlocked
            return json.dumps({
                "unlocked": get_unlocked_count(),
                "total":    get_total_count(),
                "recent":   get_recent_unlocked(3),
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    # ══════════════════════════════════════════════════════════
    # ECONOMY CONTROLS BRIDGE
    # ══════════════════════════════════════════════════════════

    @pyqtSlot(result=str)
    def getEconomyStatus(self):
        """Trả về toàn bộ trạng thái kiểm soát kinh tế."""
        try:
            from ..economy_controls import get_full_economy_status
            return json.dumps(get_full_economy_status(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getConsumableCooldowns(self):
        """Trả về cooldown của consumables."""
        try:
            from ..economy_controls import get_consumable_cooldowns
            return json.dumps(get_consumable_cooldowns(), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def useConsumable(self, consumable_id: str):
        """Sử dụng consumable (mua từ shop)."""
        try:
            from ..economy_controls import (
                CONSUMABLE_MAP, can_use_consumable, record_consumable_use
            )
            from ..balance import get_balance, set_balance, record_purchase

            consumable = CONSUMABLE_MAP.get(consumable_id)
            if not consumable:
                return json.dumps({"ok": False, "error": "Vật phẩm không tồn tại."}, ensure_ascii=False)

            # Kiểm tra daily limit
            check = can_use_consumable(consumable_id)
            if not check.get("ok"):
                return json.dumps(check, ensure_ascii=False)

            # Kiểm tra tiền
            price = consumable.get("price", 0)
            bal = get_balance()
            if bal < price:
                return json.dumps({"ok": False, "error": "Không đủ tiền mua."}, ensure_ascii=False)

            # Trừ tiền + ghi nhận
            set_balance(bal - price)
            record_purchase(price, consumable.get("name", consumable_id))
            record_consumable_use(consumable_id)

            from ..transactions import add_transaction
            add_transaction("consumable", price,
                            f"Mua {consumable['emoji']} {consumable['name']}: {price:,}đ".replace(",", "."))

            # Nếu consumable có effect, active boost
            from ..food_effects import register_food_purchase
            register_food_purchase(consumable_id, consumable)

            return json.dumps({"ok": True, "name": consumable.get("name"), "price": price}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    # ══════════════════════════════════════════════════════════
    # BOND BRIDGE
    # ══════════════════════════════════════════════════════════

    @pyqtSlot(result=str)
    def getBondAllData(self):
        """Trả về toàn bộ dữ liệu trái phiếu cho UI."""
        try:
            from ..bond_system import get_all_bond_data
            return json.dumps(get_all_bond_data(), ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def buyBond(self, bond_id: str):
        """Mua 1 đơn vị trái phiếu (mệnh giá tối thiểu)."""
        try:
            from ..bond_system import buy_bond
            result = buy_bond(bond_id)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def sellBond(self, bond_id: str):
        """Bán 1 đơn vị trái phiếu (thị trường thứ cấp)."""
        try:
            from ..bond_system import sell_bond
            result = sell_bond(bond_id)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(str, result=str)
    def convertBond(self, bond_id: str):
        """Chuyển đổi trái phiếu chuyển đổi thành cổ phiếu."""
        try:
            from ..bond_system import convert_convertible_bond
            result = convert_convertible_bond(bond_id)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getBondCouponLog(self):
        """Lấy lịch sử coupon trái phiếu."""
        try:
            from ..bond_system import get_coupon_log
            return json.dumps(get_coupon_log(20), ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def getBondMarketSummary(self):
        """Tổng quan thị trường trái phiếu."""
        try:
            from ..bond_system import get_market_summary
            return json.dumps(get_market_summary(), ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

    @pyqtSlot(result=str)
    def processBondCoupons(self):
        """Xử lý thanh toán coupon nếu đủ review."""
        try:
            from ..bond_system import process_coupon_payments
            result = process_coupon_payments()
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
