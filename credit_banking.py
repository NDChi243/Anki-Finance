# -*- coding: utf-8 -*-
"""
credit_banking.py — Hệ thống Ngân hàng Nâng cao Anki Tycoon

Bao gồm:
  - Credit Score (điểm tín dụng) dựa trên học Anki
  - Thẻ tín dụng (hạn mức, lãi suất, phí thường niên, chu kỳ)
  - Vay ngân hàng (kỳ hạn, lãi cố định/thả nổi, phương thức trả nợ)
  - Phân loại nợ tốt/xấu
  - Tài sản thế chấp & định giá
  - Chứng minh thu nhập qua học Anki
  - Rank yêu cầu tối thiểu
  - Bảo hiểm khoản vay, gia hạn, ưu đãi
  - Lịch sử tín dụng & chi tiêu
"""

import time
import uuid
import math
from datetime import datetime, timedelta
from typing import Any

from ._safe_config import col_ready, cfg_dict, cfg_list, cfg_set, cfg_int
from .logger import get_logger
logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════
# CONFIG KEYS
# ═══════════════════════════════════════════════════════════════

_KEY_CREDIT_SCORE    = "anki_tycoon_credit_score"       # {score, history, last_updated}
_KEY_CREDIT_CARDS    = "anki_tycoon_credit_cards"        # [{id, product, ...}]
_KEY_CREDIT_BILLS    = "anki_tycoon_credit_bills"        # [{card_id, statement_date, ...}]
_KEY_LOANS           = "anki_tycoon_bank_loans"          # [{id, product, ...}] — vay có kỳ hạn
_KEY_COLLATERAL      = "anki_tycoon_collateral"          # [{id, type, asset_id, valuation, ltv, ...}]
_KEY_INCOME_VERIFIED = "anki_tycoon_income_verified"     # {level, verified_at, method, income}
_KEY_LOAN_INSURANCE  = "anki_tycoon_loan_insurance"      # [{loan_id, type, premium, ...}]
_KEY_LOYALTY         = "anki_tycoon_loyalty"             # {points, tier, perks}
_KEY_CREDIT_HISTORY  = "anki_tycoon_credit_history"      # [{date, event, details, score_change}]
_KEY_OVERDUE_LOGS    = "anki_tycoon_overdue_logs"        # [{loan_id, date, days_overdue, penalty, ...}]

# ═══════════════════════════════════════════════════════════════
# RANK REQUIREMENTS (tham chiếu rank_system.py)
# ═══════════════════════════════════════════════════════════════

# Yêu cầu rank tối thiểu cho từng sản phẩm
# Lưu ý: id rank giữ nguyên (sv*, nlc*, tt*, dn*, tp*) vì tham chiếu
# trong config & DB. Tên hiển thị tham khảo theo bảng mới ở rank_system.py.
PRODUCT_RANK_REQUIREMENTS = {
    # Thẻ tín dụng
    "cc_standard":      "sv1",      # Tân Học giả
    "cc_gold":          "nlc1",     # Chuyên viên Tập sự
    "cc_platinum":      "tt1",      # Nhà Đầu tư Cá nhân
    "cc_vip":           "dn2",      # CEO
    "cc_black":         "tp1",      # Triệu phú

    # Vay tiêu dùng
    "loan_personal":    "sv2",      # Học giả
    "loan_education":   "sv1",      # Tân Học giả
    "loan_medical":     "nlc1",     # Chuyên viên Tập sự

    # Vay thế chấp
    "loan_mortgage":    "tt1",      # Nhà Đầu tư Cá nhân
    "loan_business":    "dn1",      # Founder
    "loan_car":         "nlc2",     # Chuyên viên Tài chính
    "loan_home_renovation": "tt1",  # Nhà Đầu tư Cá nhân

    # Vay đặc biệt
    "loan_ankibacked":  "sv2",      # Vay dựa trên thành tích học Anki
}

# ═══════════════════════════════════════════════════════════════
# THẺ TÍN DỤNG (Credit Card Products)
# ═══════════════════════════════════════════════════════════════

CREDIT_CARD_PRODUCTS = {
    "cc_standard": {
        "label": "Thẻ Tín Dụng Chuẩn",
        "emoji": "💳",
        "max_credit": 20_000_000,         # Hạn mức tối đa 20 triệu
        "min_credit": 1_000_000,
        "interest_rate": 0.025,           # 2.5%/tháng (30%/năm)
        "late_fee_rate": 0.05,            # 5% phí trả chậm
        "annual_fee": 200_000,            # Phí thường niên 200k
        "annual_fee_waived_first": True,  # Miễn phí năm đầu
        "grace_days": 45,                 # 45 ngày miễn lãi
        "cash_advance_fee": 0.04,         # 4% phí ứng tiền mặt
        "cash_advance_rate": 0.035,       # 3.5%/tháng lãi ứng tiền
        "min_payment_pct": 0.05,          # 5% dư nợ tối thiểu
        "foreign_transaction_fee": 0.03,  # 3% phí giao dịch ngoại tệ
        "overlimit_fee": 100_000,         # Phí vượt hạn mức
        "late_fee_min": 50_000,           # Phí trả chậm tối thiểu
        "cycle_days": 30,                 # Chu kỳ thanh toán 30 ngày
        "perks": ["Bảo hiểm du lịch cơ bản", "Hoàn tiền 0.5%"],
        "late_payment_grace_days": 3,     # Grace period trả chậm
    },
    "cc_gold": {
        "label": "Thẻ Tín Dụng Vàng",
        "emoji": "💛",
        "max_credit": 50_000_000,         # 50 triệu
        "min_credit": 5_000_000,
        "interest_rate": 0.022,           # 2.2%/tháng (26.4%/năm)
        "late_fee_rate": 0.04,            # 4%
        "annual_fee": 500_000,
        "annual_fee_waived_first": True,
        "grace_days": 45,
        "cash_advance_fee": 0.035,
        "cash_advance_rate": 0.03,
        "min_payment_pct": 0.05,
        "foreign_transaction_fee": 0.025,
        "overlimit_fee": 150_000,
        "late_fee_min": 80_000,
        "cycle_days": 30,
        "perks": ["Bảo hiểm du lịch cao cấp", "Hoàn tiền 1%", "Sân bay VIP lounge 2 lần/năm"],
        "late_payment_grace_days": 5,
    },
    "cc_platinum": {
        "label": "Thẻ Tín Dụng Bạch Kim",
        "emoji": "💠",
        "max_credit": 150_000_000,        # 150 triệu
        "min_credit": 20_000_000,
        "interest_rate": 0.020,           # 2%/tháng (24%/năm)
        "late_fee_rate": 0.035,           # 3.5%
        "annual_fee": 1_500_000,
        "annual_fee_waived_first": True,
        "grace_days": 50,
        "cash_advance_fee": 0.03,
        "cash_advance_rate": 0.028,
        "min_payment_pct": 0.05,
        "foreign_transaction_fee": 0.02,
        "overlimit_fee": 200_000,
        "late_fee_min": 120_000,
        "cycle_days": 30,
        "perks": ["Bảo hiểm du lịch toàn diện", "Hoàn tiền 1.5%", "Sân bay VIP lounge 6 lần/năm",
                   "Bảo hiểm mua hàng", "Ưu đãi 5 sao"],
        "late_payment_grace_days": 7,
    },
    "cc_vip": {
        "label": "Thẻ Tín Dụng VIP",
        "emoji": "💎",
        "max_credit": 500_000_000,        # 500 triệu
        "min_credit": 50_000_000,
        "interest_rate": 0.017,           # 1.7%/tháng (20.4%/năm)
        "late_fee_rate": 0.03,            # 3%
        "annual_fee": 5_000_000,
        "annual_fee_waived_first": False,
        "grace_days": 55,
        "cash_advance_fee": 0.025,
        "cash_advance_rate": 0.025,
        "min_payment_pct": 0.03,
        "foreign_transaction_fee": 0.015,
        "overlimit_fee": 300_000,
        "late_fee_min": 200_000,
        "cycle_days": 30,
        "perks": ["Bảo hiểm du lịch toàn diện (hạng sang)", "Hoàn tiền 2%",
                   "Sân bay VIP lounge không giới hạn", "Concierge 24/7",
                   "Miễn phí giao dịch ngoại tệ", "Quà tặng sinh nhật"],
        "late_payment_grace_days": 10,
    },
    "cc_black": {
        "label": "Thẻ Tín Dụng Black",
        "emoji": "🖤",
        "max_credit": 2_000_000_000,      # 2 tỷ
        "min_credit": 200_000_000,
        "interest_rate": 0.012,           # 1.2%/tháng (14.4%/năm)
        "late_fee_rate": 0.025,           # 2.5%
        "annual_fee": 20_000_000,
        "annual_fee_waived_first": False,
        "grace_days": 60,
        "cash_advance_fee": 0.02,
        "cash_advance_rate": 0.02,
        "min_payment_pct": 0.02,
        "foreign_transaction_fee": 0.0,
        "overlimit_fee": 500_000,
        "late_fee_min": 500_000,
        "cycle_days": 30,
        "perks": ["Bảo hiểm toàn diện toàn cầu", "Hoàn tiền 3%",
                   "Sân bay VIP lounge toàn cầu", "Concierge 24/7 cao cấp",
                   "Miễn phí tất cả giao dịch", "Quà tặng sinh nhật+VIP events",
                   "Tài xế riêng 12 lần/năm", "Ưu đãi golf 5 sao"],
        "late_payment_grace_days": 15,
    },
}

# ═══════════════════════════════════════════════════════════════
# SẢN PHẨM VAY (Loan Products)
# ═══════════════════════════════════════════════════════════════

LOAN_PRODUCTS = {
    "loan_personal": {
        "label": "Vay Tiêu Dùng",
        "emoji": "🛍️",
        "min_amount": 1_000_000,
        "max_amount": 100_000_000,
        "min_tenure_months": 6,       # Kỳ hạn tối thiểu
        "max_tenure_months": 60,      # Kỳ hạn tối đa (5 năm)
        "interest_rate_fixed": 0.015,  # 1.5%/tháng lãi cố định
        "interest_rate_floating": 0.012,  # 1.2%/tháng lãi thả nổi (tham chiếu)
        "is_collateral_required": False,
        "disbursement_fee": 0.01,     # 1% phí giải ngân
        "early_repayment_fee": 0.03,  # 3% phí trả nợ trước hạn
        "description": "Vay tiêu dùng không cần tài sản đảm bảo",
    },
    "loan_education": {
        "label": "Vay Giáo Dục / Học Tập",
        "emoji": "📚",
        "min_amount": 500_000,
        "max_amount": 50_000_000,
        "min_tenure_months": 12,
        "max_tenure_months": 84,      # 7 năm
        "interest_rate_fixed": 0.008,  # 0.8%/tháng (lãi suất ưu đãi)
        "interest_rate_floating": 0.006,
        "is_collateral_required": False,
        "disbursement_fee": 0.005,
        "early_repayment_fee": 0.01,
        "description": "Vay hỗ trợ học tập với lãi suất ưu đãi",
    },
    "loan_medical": {
        "label": "Vay Y Tế",
        "emoji": "🏥",
        "min_amount": 2_000_000,
        "max_amount": 100_000_000,
        "min_tenure_months": 6,
        "max_tenure_months": 48,
        "interest_rate_fixed": 0.012,
        "interest_rate_floating": 0.010,
        "is_collateral_required": False,
        "disbursement_fee": 0.01,
        "early_repayment_fee": 0.02,
        "description": "Vay chi trả viện phí và điều trị y tế",
    },
    "loan_mortgage": {
        "label": "Vay Thế Chấp Mua Nhà",
        "emoji": "🏠",
        "min_amount": 100_000_000,
        "max_amount": 10_000_000_000,
        "min_tenure_months": 12,
        "max_tenure_months": 360,     # 30 năm
        "interest_rate_fixed": 0.01,   # 1%/tháng (cố định 12-24T đầu)
        "interest_rate_floating": 0.008,
        "is_collateral_required": True,
        "max_ltv_pct": 0.70,          # Cho vay tối đa 70% giá trị TSĐB
        "disbursement_fee": 0.02,
        "early_repayment_fee": 0.02,
        "description": "Vay mua nhà với tài sản thế chấp là BĐS",
        "min_income_requirement": True,
    },
    "loan_business": {
        "label": "Vay Kinh Doanh",
        "emoji": "🏢",
        "min_amount": 20_000_000,
        "max_amount": 5_000_000_000,
        "min_tenure_months": 6,
        "max_tenure_months": 120,     # 10 năm
        "interest_rate_fixed": 0.013,
        "interest_rate_floating": 0.010,
        "is_collateral_required": True,
        "max_ltv_pct": 0.60,          # 60% LTV
        "disbursement_fee": 0.015,
        "early_repayment_fee": 0.03,
        "description": "Vay vốn kinh doanh, mở rộng sản xuất",
        "min_income_requirement": True,
    },
    "loan_car": {
        "label": "Vay Mua Xe",
        "emoji": "🚗",
        "min_amount": 20_000_000,
        "max_amount": 2_000_000_000,
        "min_tenure_months": 12,
        "max_tenure_months": 96,      # 8 năm
        "interest_rate_fixed": 0.012,
        "interest_rate_floating": 0.009,
        "is_collateral_required": True,
        "max_ltv_pct": 0.80,          # 80% giá trị xe
        "disbursement_fee": 0.015,
        "early_repayment_fee": 0.03,
        "description": "Vay mua ô tô mới hoặc cũ với xe làm tài sản thế chấp",
    },
    "loan_home_renovation": {
        "label": "Vay Sửa Nhà",
        "emoji": "🔨",
        "min_amount": 10_000_000,
        "max_amount": 500_000_000,
        "min_tenure_months": 6,
        "max_tenure_months": 120,
        "interest_rate_fixed": 0.012,
        "interest_rate_floating": 0.010,
        "is_collateral_required": True,
        "max_ltv_pct": 0.65,
        "disbursement_fee": 0.015,
        "early_repayment_fee": 0.02,
        "description": "Vay cải tạo, sửa chữa nhà ở",
    },
    "loan_ankibacked": {
        "label": "Vay AnkiBacked™",
        "emoji": "🃏",
        "min_amount": 100_000,
        "max_amount": 200_000_000,
        "min_tenure_months": 1,
        "max_tenure_months": 24,
        "interest_rate_fixed": 0.005,  # 0.5%/tháng — siêu ưu đãi!
        "interest_rate_floating": 0.004,
        "is_collateral_required": False,
        "disbursement_fee": 0.005,
        "early_repayment_fee": 0.005,
        "description": "🎯 Vay dựa trên thành tích học Anki! Học càng chăm, lãi càng thấp",
        "ankibacked": True,
        "study_tracking": True,
    },
}

# ═══════════════════════════════════════════════════════════════
# PHƯƠNG THỨC TRẢ NỢ
# ═══════════════════════════════════════════════════════════════

REPAYMENT_METHODS = {
    "equal_installment": {
        "label": "Trả góp cố định hàng tháng",
        "desc": "Mỗi tháng trả số tiền bằng nhau (gốc + lãi)",
    },
    "equal_principal": {
        "label": "Gốc cố định, lãi giảm dần",
        "desc": "Gốc chia đều các kỳ, lãi tính trên dư nợ giảm dần",
    },
    "bullet": {
        "label": "Trả lãi hàng tháng, gốc cuối kỳ",
        "desc": "Chỉ trả lãi hàng tháng, toàn bộ gốc trả vào kỳ cuối",
    },
}

# ═══════════════════════════════════════════════════════════════
# PHÂN LOẠI NỢ (Theo thông tư 02/2013/TT-NHNN và Basel II)
# ═══════════════════════════════════════════════════════════════

# Nhóm nợ theo tiêu chuẩn Việt Nam
DEBT_CLASSIFICATION = [
    {"group": 1, "label": "Nợ đủ tiêu chuẩn",    "days_overdue": 0,    "provision_rate": 0.0},
    {"group": 2, "label": "Nợ cần chú ý",        "days_overdue": 10,   "provision_rate": 0.05},
    {"group": 3, "label": "Nợ dưới tiêu chuẩn",  "days_overdue": 30,   "provision_rate": 0.20},
    {"group": 4, "label": "Nợ nghi ngờ",         "days_overdue": 90,   "provision_rate": 0.50},
    {"group": 5, "label": "Nợ có khả năng mất vốn", "days_overdue": 180, "provision_rate": 1.0},
]

def classify_debt(days_overdue: int) -> dict:
    """Phân loại nợ dựa trên số ngày quá hạn."""
    for i in range(len(DEBT_CLASSIFICATION) - 1, -1, -1):
        if days_overdue >= DEBT_CLASSIFICATION[i]["days_overdue"]:
            return dict(DEBT_CLASSIFICATION[i])
    return dict(DEBT_CLASSIFICATION[0])

# ═══════════════════════════════════════════════════════════════
# HÌNH THỨC CHỨNG MINH THU NHẬP
# ═══════════════════════════════════════════════════════════════

INCOME_VERIFICATION_METHODS = [
    {
        "id": "study_based",
        "label": "Chứng minh qua học Anki",
        "emoji": "📱",
        "levels": [
            {"level": 1, "label": "Cơ bản", "cards_required": 100,  "weight": 0.3, "income_multiplier": 0.5},
            {"level": 2, "label": "Trung bình", "cards_required": 500, "weight": 0.5, "income_multiplier": 1.0},
            {"level": 3, "label": "Khá", "cards_required": 2000, "weight": 0.7, "income_multiplier": 2.0},
            {"level": 4, "label": "Tốt", "cards_required": 5000, "weight": 0.9, "income_multiplier": 3.5},
            {"level": 5, "label": "Xuất sắc", "cards_required": 10000, "weight": 1.0, "income_multiplier": 5.0},
        ],
    },
    {
        "id": "asset_based",
        "label": "Chứng minh qua tài sản",
        "emoji": "🏦",
        "levels": [
            {"level": 1, "label": "Có tài sản", "asset_value_required": 10_000_000, "weight": 0.4, "income_multiplier": 1.0},
            {"level": 2, "label": "Khá giả", "asset_value_required": 100_000_000, "weight": 0.6, "income_multiplier": 2.5},
            {"level": 3, "label": "Giàu có", "asset_value_required": 1_000_000_000, "weight": 0.8, "income_multiplier": 5.0},
            {"level": 4, "label": "Siêu giàu", "asset_value_required": 10_000_000_000, "weight": 1.0, "income_multiplier": 10.0},
        ],
    },
    {
        "id": "balance_based",
        "label": "Chứng minh qua số dư",
        "emoji": "💰",
        "levels": [
            {"level": 1, "label": "Ổn định", "balance_required": 1_000_000, "weight": 0.2, "income_multiplier": 0.3},
            {"level": 2, "label": "Khá", "balance_required": 50_000_000, "weight": 0.4, "income_multiplier": 1.0},
            {"level": 3, "label": "Tốt", "balance_required": 500_000_000, "weight": 0.6, "income_multiplier": 3.0},
            {"level": 4, "label": "Vững vàng", "balance_required": 5_000_000_000, "weight": 0.8, "income_multiplier": 8.0},
        ],
    },
    {
        "id": "streak_based",
        "label": "Chứng minh qua Streak học tập",
        "emoji": "🔥",
        "levels": [
            {"level": 1, "label": "Chăm chỉ", "streak_required": 7, "weight": 0.3, "income_multiplier": 0.5},
            {"level": 2, "label": "Kiên trì", "streak_required": 30, "weight": 0.5, "income_multiplier": 1.5},
            {"level": 3, "label": "Kỷ luật", "streak_required": 90, "weight": 0.7, "income_multiplier": 3.0},
            {"level": 4, "label": "Huyền thoại", "streak_required": 365, "weight": 1.0, "income_multiplier": 6.0},
        ],
    },
]

# ═══════════════════════════════════════════════════════════════
# LÃI SUẤT THAM CHIẾU (tham khảo NHNN & Basel II)
# ═══════════════════════════════════════════════════════════════

# Lãi suất cơ bản tham chiếu (như lãi suất điều hành NHNN)
REFERENCE_INTEREST_RATE = 0.045  # 4.5%/năm

# Tỷ lệ an toàn vốn tối thiểu (CAR theo Basel II)
MIN_CAPITAL_ADEQUACY_RATIO = 0.08  # 8%

# Tỷ lệ dư nợ tối đa so với vốn tự có
MAX_DEBT_TO_EQUITY = 0.40  # 40%

# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _now() -> float:
    return time.time()

def _today_str() -> str:
    """Trả về 'YYYY-MM-DD' dùng Unix timestamp, chống time travel."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time()))

def _get_rank_id() -> str:
    """Lấy rank_id hiện tại của người chơi."""
    try:
        from .rank_system import get_rank_status
        return get_rank_status().get("rank_id", "sv1")
    except Exception as e:
        logger.debug("_get_rank_id: %s", e)
        return "sv1"

def _get_rank_group() -> str:
    """Lấy nhóm rank hiện tại."""
    try:
        from .rank_system import get_rank_status
        return get_rank_status().get("rank_group", "Học giả")
    except Exception as e:
        logger.debug("_get_rank_group: %s", e)
        return "Học giả"

def _get_rank_index(rank_id: str = None) -> int:
    """Lấy index của rank trong hệ thống."""
    try:
        from .rank_system import get_all_ranks
        ranks = get_all_ranks()
        for i, r in enumerate(ranks):
            if r["id"] == (rank_id or _get_rank_id()):
                return i
        return 0
    except Exception as e:
        logger.debug("_get_rank_index: %s", e)
        return 0

def _check_rank_requirement(product_id: str) -> dict:
    """Kiểm tra rank yêu cầu cho 1 sản phẩm."""
    req_rank = PRODUCT_RANK_REQUIREMENTS.get(product_id, "sv1")
    current_rank = _get_rank_id()
    try:
        from .rank_system import get_all_ranks
        ranks = get_all_ranks()
        req_idx = -1
        cur_idx = -1
        for i, r in enumerate(ranks):
            if r["id"] == req_rank:
                req_idx = i
            if r["id"] == current_rank:
                cur_idx = i
        if cur_idx >= req_idx:
            return {"ok": True, "required": req_rank, "current": current_rank}
        req_label = ranks[req_idx]["label"] if req_idx >= 0 else req_rank
        return {"ok": False, "required": req_rank, "required_label": req_label,
                "current": current_rank, "error": f"Yêu cầu {req_label} trở lên"}
    except Exception as e:
        logger.debug("_check_rank_requirement: %s", e)
        return {"ok": True}

def _get_study_stats() -> dict:
    """Lấy thống kê học tập để dùng trong chứng minh thu nhập & credit score."""
    try:
        from .balance import get_stats
        stats = get_stats()
        cards_reviewed = int(stats.get("cards_reviewed", 0) or 0)
        return {
            "cards_reviewed": cards_reviewed,
            "total_earned": int(stats.get("total_earned", 0) or 0),
            "ease_distribution": {
                "again": int(stats.get("ease_1", 0) or 0),
                "hard": int(stats.get("ease_2", 0) or 0),
                "good": int(stats.get("ease_3", 0) or 0),
                "easy": int(stats.get("ease_4", 0) or 0),
            }
        }
    except Exception as e:
        logger.debug("_get_study_stats: %s", e)
        return {"cards_reviewed": 0, "total_earned": 0, "ease_distribution": {}}

def _get_streak_info() -> dict:
    """Lấy thông tin streak."""
    try:
        from .streak_system import get_streak_status
        s = get_streak_status()
        return {
            "current": int(s.get("current", 0)) if isinstance(s, dict) else 0,
            "longest": int(s.get("longest", 0)) if isinstance(s, dict) else 0,
        }
    except Exception as e:
        logger.debug("_get_streak_info: %s", e)
        return {"current": 0, "longest": 0}

def _get_total_asset_value() -> int:
    """Ước tính tổng giá trị tài sản từ balance + inventory."""
    total = 0
    try:
        from .balance import get_balance
        total += get_balance()
    except Exception as e:
        logger.debug("_get_total_asset_value (balance): %s", e)
    try:
        from .bank import get_total_savings
        total += get_total_savings()
    except Exception as e:
        logger.debug("_get_total_asset_value (bank): %s", e)
    try:
        from .real_estate import get_re_summary
        re = get_re_summary()
        total += int(re.get("total_value", 0) or 0)
    except Exception as e:
        logger.debug("_get_total_asset_value (real_estate): %s", e)
    try:
        from .stock_market import get_portfolio_value
        total += int(get_portfolio_value())
    except Exception as e:
        logger.debug("_get_total_asset_value (stock): %s", e)
    return total

def _generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:10]}"

# ═══════════════════════════════════════════════════════════════
# 1. CREDIT SCORE SYSTEM — ĐIỂM TÍN DỤNG
# ═══════════════════════════════════════════════════════════════

def _get_credit_score_data() -> dict:
    """Lấy dữ liệu điểm tín dụng, khởi tạo nếu chưa có."""
    default = {
        "score": 450,           # FICO scale: 300-850
        "history": [],
        "last_updated": _now(),
        "total_cards_reviewed_at_init": 0,
    }
    return cfg_dict(_KEY_CREDIT_SCORE, default)

def _save_credit_score_data(data: dict):
    cfg_set(_KEY_CREDIT_SCORE, data)

def calculate_credit_score() -> int:
    """
    Tính điểm tín dụng dựa trên:
    - Lịch sử học Anki (số thẻ, streak, ease ratio)
    - Lịch sử thanh toán thẻ tín dụng
    - Tỷ lệ dư nợ/hạn mức (utilization)
    - Tài sản nắm giữ
    - Thu nhập ước tính
    """
    score = 450  # Baseline

    # ── Factor 1: Học Anki (max +200) ──
    study = _get_study_stats()
    cards = study.get("cards_reviewed", 0)
    score += min(80, cards // 50)  # +1 điểm mỗi 50 thẻ, tối đa 80

    dist = study.get("ease_distribution", {})
    again = dist.get("again", 0)
    total = sum(dist.values()) or 1
    again_ratio = again / total
    if again_ratio < 0.1:
        score += 40
    elif again_ratio < 0.2:
        score += 25
    elif again_ratio < 0.3:
        score += 10

    # Streak
    streak = _get_streak_info()
    score += min(80, streak.get("current", 0) * 2)  # +2 điểm mỗi ngày streak, tối đa 80

    # ── Factor 2: Lịch sử thanh toán (max +150) ──
    credit_data = _get_credit_score_data()
    for entry in credit_data.get("history", []):
        if entry.get("type") == "payment_on_time":
            score += 5
        elif entry.get("type") == "late_payment":
            score -= min(50, max(10, entry.get("days_late", 1) * 5))
        elif entry.get("type") == "default":
            score -= 100

    # ── Factor 3: Tài sản (max +50) ──
    asset_value = _get_total_asset_value()
    if asset_value >= 10_000_000_000:
        score += 50
    elif asset_value >= 1_000_000_000:
        score += 35
    elif asset_value >= 100_000_000:
        score += 20
    elif asset_value >= 10_000_000:
        score += 10

    # ── Factor 4: Tỷ lệ sử dụng thẻ tín dụng (max +50) ──
    cards_data = _get_cards_data()
    total_used = sum(c.get("used_credit", 0) for c in cards_data)
    total_limit = sum(c.get("approved_limit", 0) for c in cards_data) or 1
    utilization = total_used / total_limit
    if utilization < 0.10:
        score += 50  # Dùng ít -> tốt
    elif utilization < 0.30:
        score += 30
    elif utilization < 0.50:
        score += 10
    elif utilization > 0.90:
        score -= 30  # Dùng gần hết hạn mức -> xấu

    # ── Clamp ──
    return max(300, min(850, score))

def get_credit_score_info() -> dict:
    """Trả về thông tin điểm tín dụng đầy đủ."""
    data = _get_credit_score_data()
    score = calculate_credit_score()
    data["score"] = score
    data["last_updated"] = _now()
    _save_credit_score_data(data)

    # Xếp hạng tín dụng
    if score >= 750:
        rating = "Xuất sắc"
        emoji = "🌟"
    elif score >= 700:
        rating = "Tốt"
        emoji = "✅"
    elif score >= 650:
        rating = "Khá"
        emoji = "👍"
    elif score >= 550:
        rating = "Trung bình"
        emoji = "⚠️"
    else:
        rating = "Kém"
        emoji = "🔴"

    return {
        "score": score,
        "rating": rating,
        "emoji": emoji,
        "last_updated": data.get("last_updated", 0),
        "history_count": len(data.get("history", [])),
    }

def update_credit_history(event_type: str, details: str, score_change: int = 0):
    """Ghi lại sự kiện vào lịch sử tín dụng."""
    data = _get_credit_score_data()
    history = data.get("history", [])
    history.append({
        "date": _today_str(),
        "timestamp": _now(),
        "type": event_type,
        "details": details,
        "score_change": score_change,
    })
    # Chỉ giữ 100 sự kiện gần nhất
    data["history"] = history[-100:]
    _save_credit_score_data(data)

# ═══════════════════════════════════════════════════════════════
# 2. CREDIT CARD SYSTEM — THẺ TÍN DỤNG
# ═══════════════════════════════════════════════════════════════

def _get_cards_data() -> list:
    return cfg_list(_KEY_CREDIT_CARDS, [])

def _save_cards_data(cards: list):
    cfg_set(_KEY_CREDIT_CARDS, cards)

def get_credit_card_products() -> list:
    """Trả về danh sách sản phẩm thẻ tín dụng + kiểm tra rank requirement."""
    result = []
    for code, product in CREDIT_CARD_PRODUCTS.items():
        rank_check = _check_rank_requirement(code)
        entry = {**product, "code": code}
        entry["rank_requirement"] = {
            "required_id": PRODUCT_RANK_REQUIREMENTS.get(code, "sv1"),
            "met": rank_check["ok"],
        }
        if not rank_check["ok"]:
            entry["blocked_reason"] = rank_check.get("error", "")
        result.append(entry)
    return result

def apply_credit_card(product_code: str, requested_limit: int = None) -> dict:
    """Đăng ký mở thẻ tín dụng."""
    if product_code not in CREDIT_CARD_PRODUCTS:
        return {"ok": False, "error": "Sản phẩm thẻ không hợp lệ."}

    product = CREDIT_CARD_PRODUCTS[product_code]

    # Kiểm tra rank
    rank_check = _check_rank_requirement(product_code)
    if not rank_check["ok"]:
        return {"ok": False, "error": rank_check.get("error", "Không đủ rank.")}

    # Kiểm tra đã có thẻ loại này chưa
    existing = _get_cards_data()
    if any(c.get("product_code") == product_code for c in existing):
        return {"ok": False, "error": "Bạn đã có thẻ này rồi."}

    # Tính hạn mức dựa trên credit score + thu nhập
    credit_info = get_credit_score_info()
    score = credit_info["score"]

    # Hạn mức = base_limit * score_factor
    score_factor = score / 500.0  # score 300 → 0.6x, score 850 → 1.7x
    base_limit = requested_limit or product["max_credit"]
    approved_limit = min(int(base_limit * score_factor), product["max_credit"])
    approved_limit = max(approved_limit, product["min_credit"])

    # Nếu request cụ thể, kiểm tra
    if requested_limit and requested_limit > approved_limit:
        approved_limit = min(requested_limit, approved_limit)

    new_card = {
        "id": _generate_id("cc_"),
        "product_code": product_code,
        "product_label": product["label"],
        "approved_limit": approved_limit,
        "used_credit": 0,
        "available_credit": approved_limit,
        "interest_rate": product["interest_rate"],
        "annual_fee": product["annual_fee"],
        "annual_fee_paid": product.get("annual_fee_waived_first", False),
        "grace_days": product["grace_days"],
        "min_payment_pct": product["min_payment_pct"],
        "opened_at": _now(),
        "opened_date": _today_str(),
        "last_statement_date": _today_str(),
        "next_payment_date": (_now() + product["cycle_days"] * 86400),
        "cycle_days": product["cycle_days"],
        "late_fee_rate": product["late_fee_rate"],
        "status": "active",  # active, locked, closed
        "transactions": [],   # [{date, amount, merchant, category}]
        "payment_history": [], # [{date, amount, on_time}]
        "rewards_points": 0,
        "last_annual_fee_date": _today_str(),
    }

    cards = _get_cards_data()
    cards.append(new_card)
    _save_cards_data(cards)

    update_credit_history("card_opened", f"Mở thẻ {product['label']} - hạn mức {approved_limit:,}₫", 5)

    return {
        "ok": True,
        "card_id": new_card["id"],
        "approved_limit": approved_limit,
        "product_label": product["label"],
        "interest_rate": product["interest_rate"],
        "grace_days": product["grace_days"],
    }

def get_my_credit_cards() -> list:
    """Trả về danh sách thẻ tín dụng đang sở hữu kèm thông tin chi tiết."""
    cards = _get_cards_data()
    result = []
    now = _now()
    for card in cards:
        product = CREDIT_CARD_PRODUCTS.get(card["product_code"], {})
        # Kiểm tra phí thường niên
        annual_fee_due = False
        if not card.get("annual_fee_paid", False):
            last_fee = card.get("last_annual_fee_date", card.get("opened_date", ""))
            try:
                fee_date = datetime.fromisoformat(last_fee) if last_fee else datetime.now()
                if (now - fee_date.timestamp()) >= 365 * 86400:
                    annual_fee_due = True
            except Exception as e:
                logger.debug("_process_credit_cards (annual fee date): %s", e)

        # Tính sao kê
        payment_info = _calc_card_payment_info(card)

        result.append({
            "id": card["id"],
            "product_code": card["product_code"],
            "product_label": card["product_label"],
            "emoji": product.get("emoji", "💳"),
            "approved_limit": card["approved_limit"],
            "used_credit": card.get("used_credit", 0),
            "available_credit": card["approved_limit"] - card.get("used_credit", 0),
            "utilization_pct": round(card.get("used_credit", 0) / max(1, card["approved_limit"]) * 100, 1),
            "interest_rate_pct": card.get("interest_rate", 0.025) * 100,
            "interest_rate_monthly_pct": card.get("interest_rate", 0.025) * 100,
            "grace_days": card.get("grace_days", 45),
            "status": card.get("status", "active"),
            "rewards_points": card.get("rewards_points", 0),
            "annual_fee_due": annual_fee_due,
            "annual_fee_amount": card.get("annual_fee", product.get("annual_fee", 0)),
            "transaction_count": len(card.get("transactions", [])),
            "perks": product.get("perks", []),
            **payment_info,
        })
    return result

def _calc_card_payment_info(card: dict) -> dict:
    """Tính toán thông tin thanh toán cho 1 thẻ."""
    now = _now()
    used = card.get("used_credit", 0)
    min_payment = int(used * card.get("min_payment_pct", 0.05))
    min_payment = max(min_payment, 100_000)  # Tối thiểu 100k

    next_payment = card.get("next_payment_date", now)
    days_until_payment = max(0, (next_payment - now) / 86400)

    # Kiểm tra quá hạn
    days_overdue = 0
    if now > next_payment and used > 0:
        days_overdue = int((now - next_payment) / 86400)

    # Dư nợ sao kê tối thiểu (giả định bằng dư nợ hiện tại)
    statement_balance = used

    return {
        "statement_balance": statement_balance,
        "min_payment": min_payment,
        "next_payment_date": next_payment,
        "days_until_payment": int(days_until_payment),
        "days_overdue": days_overdue,
        "is_overdue": days_overdue > 0,
        "overdue_classification": classify_debt(days_overdue) if days_overdue > 0 else None,
        "grace_period_end": next_payment + card.get("grace_days", 45) * 86400 if used > 0 else 0,
    }

def use_credit_card(card_id: str, amount: int, merchant: str = "", category: str = "") -> dict:
    """Sử dụng thẻ tín dụng để thanh toán."""
    cards = _get_cards_data()
    card = next((c for c in cards if c["id"] == card_id), None)
    if not card:
        return {"ok": False, "error": "Không tìm thấy thẻ."}
    if card.get("status") != "active":
        return {"ok": False, "error": "Thẻ đang bị khóa."}

    available = card["approved_limit"] - card.get("used_credit", 0)
    if amount > available:
        return {"ok": False, "error": f"Vượt hạn mức khả dụng. Còn {available:,}₫".replace(",", ".")}

    # Cập nhật dư nợ
    card["used_credit"] = card.get("used_credit", 0) + amount

    # Ghi lịch sử giao dịch
    txns = card.get("transactions", [])
    txns.append({
        "date": _today_str(),
        "timestamp": _now(),
        "amount": amount,
        "merchant": merchant or "Thanh toán trực tuyến",
        "category": category or "Khác",
    })
    card["transactions"] = txns[-200:]  # Giữ 200 giao dịch gần nhất

    # Rewards points
    card["rewards_points"] = card.get("rewards_points", 0) + amount // 10000

    _save_cards_data(cards)
    update_credit_history("card_used", f"Thanh toán {amount:,}₫ {merchant}".replace(",", "."))

    return {
        "ok": True,
        "amount": amount,
        "used_credit": card["used_credit"],
        "available_credit": card["approved_limit"] - card["used_credit"],
        "product_label": card.get("product_label", "Thẻ tín dụng"),
        "rewards_earned": amount // 10000,
        "total_rewards": card["rewards_points"],
    }

def pay_credit_card(card_id: str, amount: int) -> dict:
    """Thanh toán dư nợ thẻ tín dụng."""
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    cards = _get_cards_data()
    card = next((c for c in cards if c["id"] == card_id), None)
    if not card:
        return {"ok": False, "error": "Không tìm thấy thẻ."}

    if amount <= 0:
        return {"ok": False, "error": "Số tiền không hợp lệ."}

    used = card.get("used_credit", 0)
    if amount > used:
        amount = used  # Trả toàn bộ dư nợ

    bal = get_balance()
    if bal < amount:
        return {"ok": False, "error": "Số dư ví không đủ."}

    # Trừ tiền
    set_balance(bal - amount)
    card["used_credit"] = used - amount

    # Ghi lịch sử thanh toán
    pay_history = card.get("payment_history", [])
    now = _now()
    next_payment = card.get("next_payment_date", now)
    on_time = now <= next_payment

    pay_history.append({
        "date": _today_str(),
        "timestamp": now,
        "amount": amount,
        "on_time": on_time,
        "remaining": card["used_credit"],
    })
    card["payment_history"] = pay_history[-50:]

    # Điều chỉnh next_payment_date
    if card["used_credit"] <= 0:
        # Đã trả hết, reset chu kỳ
        card["next_payment_date"] = now + card.get("cycle_days", 30) * 86400
        card["last_statement_date"] = _today_str()

    _save_cards_data(cards)
    add_transaction("credit_card_payment", amount, f"Thanh toán thẻ {card['product_label']}")

    # Cập nhật credit score
    if on_time:
        update_credit_history("payment_on_time", f"Thanh toán {amount:,}₫ đúng hạn".replace(",", "."), 5)
    else:
        update_credit_history("late_payment", f"Thanh toán {amount:,}₫ trễ".replace(",", "."), -10)

    return {
        "ok": True,
        "paid": amount,
        "remaining_debt": card["used_credit"],
        "on_time": on_time,
        "card_cleared": card["used_credit"] <= 0,
    }

def process_credit_card_annual_fees() -> list:
    """Xử lý thu phí thường niên cho tất cả thẻ (gọi định kỳ)."""
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    cards = _get_cards_data()
    now = _now()
    fees_collected = []

    for card in cards:
        if card.get("annual_fee_paid", False):
            continue
        last_fee_str = card.get("last_annual_fee_date", card.get("opened_date", ""))
        try:
            last_fee = datetime.fromisoformat(last_fee_str).timestamp() if last_fee_str else 0
        except Exception as e:
            logger.debug("_charge_annual_fees (date parse): %s", e)
            last_fee = 0

        # Miễn phí năm đầu nếu có
        if not last_fee and card.get("opened_at", 0) > 0:
            first_year_end = card["opened_at"] + 365 * 86400
            if now < first_year_end:
                continue  # Miễn phí năm đầu

        if last_fee > 0 and (now - last_fee) < 365 * 86400:
            continue  # Chưa đến hạn

        # Thu phí thường niên
        fee = card.get("annual_fee", CREDIT_CARD_PRODUCTS.get(card["product_code"], {}).get("annual_fee", 0))
        bal = get_balance()
        if bal >= fee:
            set_balance(bal - fee)
            card["annual_fee_paid"] = True
            card["last_annual_fee_date"] = _today_str()
            add_transaction("credit_card_fee", fee, f"Phí thường niên {card['product_label']}")
            fees_collected.append({"card_id": card["id"], "fee": fee, "paid": True})
        else:
            # Không đủ tiền -> ghi nợ phí vào dư nợ thẻ
            card["used_credit"] = card.get("used_credit", 0) + fee
            card["annual_fee_paid"] = True
            card["last_annual_fee_date"] = _today_str()
            fees_collected.append({"card_id": card["id"], "fee": fee, "paid": False, "added_to_debt": True})

    _save_cards_data(cards)
    return fees_collected

def get_credit_card_statement(card_id: str) -> dict:
    """Lấy sao kê chi tiết cho 1 thẻ."""
    cards = _get_cards_data()
    card = next((c for c in cards if c["id"] == card_id), None)
    if not card:
        return {"ok": False, "error": "Không tìm thấy thẻ."}

    txns = card.get("transactions", [])
    payment_info = _calc_card_payment_info(card)

    return {
        "ok": True,
        "card": {
            "id": card["id"],
            "product_label": card["product_label"],
            "approved_limit": card["approved_limit"],
            "used_credit": card.get("used_credit", 0),
        },
        "transactions": txns[-50:],  # 50 giao dịch gần nhất
        "payment_info": payment_info,
        "rewards_points": card.get("rewards_points", 0),
        "payment_history": card.get("payment_history", [])[-12:],
    }

def process_late_payment_penalties() -> dict:
    """Xử lý phạt trả chậm cho tất cả thẻ quá hạn."""
    from .transactions import add_transaction

    cards = _get_cards_data()
    now = _now()
    total_penalty = 0
    cards_penalized = []

    for card in cards:
        if card.get("status") != "active":
            continue
        if card.get("used_credit", 0) <= 0:
            continue

        next_payment = card.get("next_payment_date", now)
        if now <= next_payment:
            continue  # Chưa đến hạn

        days_overdue = int((now - next_payment) / 86400)
        if days_overdue <= card.get("grace_days", 0):
            continue  # Còn trong grace period

        # Tính lãi phạt
        used = card.get("used_credit", 0)
        interest = int(used * card.get("interest_rate", 0.025))

        # Phí trả chậm
        late_fee_rate = card.get("late_fee_rate", 0.05)
        late_fee = max(
            int(used * late_fee_rate),
            card.get("late_fee_min", 50_000)
        )

        penalty = interest + late_fee
        card["used_credit"] = used + penalty
        total_penalty += penalty
        cards_penalized.append({
            "card_id": card["id"],
            "product_label": card["product_label"],
            "days_overdue": days_overdue,
            "interest": interest,
            "late_fee": late_fee,
            "total_penalty": penalty,
        })

        update_credit_history("late_payment",
            f"Phạt trả chậm thẻ {card['product_label']}: {days_overdue} ngày", -15)

        # Nếu quá 180 ngày -> chuyển nợ xấu
        if days_overdue >= 180:
            card["status"] = "locked"
            update_credit_history("default",
                f"Thẻ {card['product_label']} bị khóa do nợ xấu >180 ngày", -100)

        add_transaction("credit_card_penalty", penalty,
            f"Phí phạt thẻ {card['product_label']} ({days_overdue} ngày quá hạn)")

    if cards_penalized:
        _save_cards_data(cards)

    return {
        "total_penalty": total_penalty,
        "cards_penalized": cards_penalized,
        "count": len(cards_penalized),
    }

# ═══════════════════════════════════════════════════════════════
# 3. ADVANCED LOAN SYSTEM — VAY NGÂN HÀNG NÂNG CAO
# ═══════════════════════════════════════════════════════════════

def _get_bank_loans() -> list:
    return cfg_list(_KEY_LOANS, [])

def _save_bank_loans(loans: list):
    cfg_set(_KEY_LOANS, loans)

def get_loan_products() -> list:
    """Trả về danh sách sản phẩm vay + kiểm tra rank."""
    result = []
    for code, product in LOAN_PRODUCTS.items():
        rank_check = _check_rank_requirement(code)
        entry = {**product, "code": code}
        entry["rank_requirement"] = {
            "required_id": PRODUCT_RANK_REQUIREMENTS.get(code, "sv1"),
            "met": rank_check["ok"],
        }
        if not rank_check["ok"]:
            entry["blocked_reason"] = rank_check.get("error", "")
        result.append(entry)
    return result

def get_repayment_methods() -> list:
    """Trả về danh sách phương thức trả nợ."""
    return [{"id": k, **v} for k, v in REPAYMENT_METHODS.items()]

def calculate_loan_installment(
    principal: int,
    annual_rate: float,
    tenure_months: int,
    method: str = "equal_installment",
    is_floating: bool = False,
    floating_ref_rate: float = None,
) -> dict:
    """
    Tính toán khoản trả hàng tháng theo từng phương thức.
    Phù hợp với Thông tư 39/2016/TT-NHNN.
    """
    monthly_rate = annual_rate / 12
    if monthly_rate <= 0:
        return {"error": "Lãi suất không hợp lệ"}

    monthly_rate = min(monthly_rate, 0.05)  # Trần lãi suất an toàn

    repayment_schedule = []
    total_interest = 0

    if method == "equal_installment":
        # Công thức trả góp đều: PMT = P * r * (1+r)^n / ((1+r)^n - 1)
        if monthly_rate > 0:
            factor = (1 + monthly_rate) ** tenure_months
            installment = int(principal * monthly_rate * factor / (factor - 1))
        else:
            installment = principal // tenure_months

        remaining = principal
        for period in range(1, tenure_months + 1):
            interest = int(remaining * monthly_rate)
            principal_paid = installment - interest
            if principal_paid > remaining:
                principal_paid = remaining
                installment = principal_paid + interest
            remaining -= principal_paid
            total_interest += interest
            repayment_schedule.append({
                "period": period,
                "installment": installment,
                "principal": principal_paid,
                "interest": interest,
                "remaining": max(0, remaining),
            })

    elif method == "equal_principal":
        # Gốc cố định, lãi giảm dần
        base_principal = principal // tenure_months
        remaining = principal
        for period in range(1, tenure_months + 1):
            principal_paid = min(base_principal, remaining)
            interest = int(remaining * monthly_rate)
            installment = principal_paid + interest
            remaining -= principal_paid
            total_interest += interest
            repayment_schedule.append({
                "period": period,
                "installment": installment,
                "principal": principal_paid,
                "interest": interest,
                "remaining": max(0, remaining),
            })

    elif method == "bullet":
        # Trả lãi hàng tháng, gốc cuối kỳ
        monthly_interest = int(principal * monthly_rate)
        for period in range(1, tenure_months + 1):
            is_last = period == tenure_months
            interest = monthly_interest
            principal_paid = principal if is_last else 0
            installment = interest + principal_paid
            remaining = principal - principal_paid if not is_last else 0
            total_interest += interest
            repayment_schedule.append({
                "period": period,
                "installment": installment,
                "principal": principal_paid,
                "interest": interest,
                "remaining": max(0, remaining),
            })

    else:
        return {"error": "Phương thức trả nợ không hợp lệ"}

    return {
        "principal": principal,
        "annual_rate_pct": round(annual_rate * 100, 2),
        "monthly_rate_pct": round(monthly_rate * 100, 2),
        "tenure_months": tenure_months,
        "method": method,
        "method_label": REPAYMENT_METHODS.get(method, {}).get("label", method),
        "total_interest": total_interest,
        "total_payment": principal + total_interest,
        "first_installment": repayment_schedule[0]["installment"] if repayment_schedule else 0,
        "last_installment": repayment_schedule[-1]["installment"] if repayment_schedule else 0,
        "schedule": repayment_schedule[:60],  # Tối đa 60 kỳ
        "full_schedule_count": len(repayment_schedule),
    }

def apply_for_loan(
    product_code: str,
    amount: int,
    tenure_months: int,
    repayment_method: str = "equal_installment",
    use_floating_rate: bool = False,
) -> dict:
    """Đăng ký vay ngân hàng."""
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    if product_code not in LOAN_PRODUCTS:
        return {"ok": False, "error": "Sản phẩm vay không hợp lệ."}

    product = LOAN_PRODUCTS[product_code]

    # Kiểm tra rank
    rank_check = _check_rank_requirement(product_code)
    if not rank_check["ok"]:
        return {"ok": False, "error": rank_check.get("error", "Không đủ rank.")}

    # Kiểm tra số tiền
    if amount < product["min_amount"]:
        return {"ok": False, "error": f"Số tiền tối thiểu là {product['min_amount']:,}₫".replace(",", ".")}
    if amount > product["max_amount"]:
        return {"ok": False, "error": f"Số tiền tối đa là {product['max_amount']:,}₫".replace(",", ".")}

    # Kiểm tra kỳ hạn
    if tenure_months < product["min_tenure_months"]:
        return {"ok": False, "error": f"Kỳ hạn tối thiểu là {product['min_tenure_months']} tháng"}
    if tenure_months > product["max_tenure_months"]:
        return {"ok": False, "error": f"Kỳ hạn tối đa là {product['max_tenure_months']} tháng"}

    # Kiểm tra phương thức trả nợ
    if repayment_method not in REPAYMENT_METHODS:
        return {"ok": False, "error": "Phương thức trả nợ không hợp lệ."}

    # Kiểm tra tài sản thế chấp nếu yêu cầu
    if product.get("is_collateral_required", False):
        collaterals = _get_collaterals_data()
        total_collateral_value = sum(c.get("valuation", 0) for c in collaterals if c.get("verified", False))
        max_ltv = product.get("max_ltv_pct", 0.70)
        if total_collateral_value <= 0:
            return {"ok": False, "error": "Sản phẩm này yêu cầu tài sản thế chấp.", "needs_collateral": True}
        max_loan_via_collateral = int(total_collateral_value * max_ltv)
        if amount > max_loan_via_collateral:
            return {"ok": False, "error": f"Giá trị TSĐB không đủ. Tối đa {max_loan_via_collateral:,}₫ (LTV {max_ltv*100:.0f}%)".replace(",", ".")}

    # Kiểm tra income requirement
    if product.get("min_income_requirement", False):
        income_info = get_income_verification_status()
        if income_info.get("verified_income", 0) <= 0:
            return {"ok": False, "error": "Sản phẩm này yêu cầu chứng minh thu nhập.", "needs_income": True}
        income = income_info["verified_income"]
        debt_ratio = amount / max(1, income)
        if debt_ratio > MAX_DEBT_TO_EQUITY:
            return {"ok": False, "error": f"Dư nợ vượt quá {MAX_DEBT_TO_EQUITY*100:.0f}% thu nhập xác thực.".replace(",", ".")}

    # Credit score check
    credit_info = get_credit_score_info()
    if credit_info["score"] < 400:
        return {"ok": False, "error": f"Điểm tín dụng quá thấp ({credit_info['score']}). Cần tối thiểu 400."}

    # Xác định lãi suất
    if use_floating_rate:
        # Lãi thả nổi = lãi suất tham chiếu + biên độ dựa trên credit score
        margin = max(0.02, 0.06 - (credit_info["score"] - 300) / 5500)
        annual_rate = REFERENCE_INTEREST_RATE + margin
    else:
        annual_rate = product["interest_rate_fixed"]

    # Điều chỉnh lãi suất theo credit score
    score_bonus = min(0.03, (credit_info["score"] - 300) * 0.00006)
    final_rate = max(0.005, annual_rate - score_bonus)

    # Phí giải ngân
    disbursement_fee = int(amount * product.get("disbursement_fee", 0.01))

    # Tính toán lịch trả nợ
    calc_result = calculate_loan_installment(amount, final_rate * 12, tenure_months, repayment_method)
    if "error" in calc_result:
        return {"ok": False, "error": calc_result["error"]}

    # Tạo khoản vay
    now = _now()
    loan = {
        "id": _generate_id("ln_"),
        "product_code": product_code,
        "product_label": product["label"],
        "principal": amount,
        "original_principal": amount,
        "disbursed_amount": amount - disbursement_fee,
        "disbursement_fee": disbursement_fee,
        "annual_rate": final_rate * 12,
        "monthly_rate": final_rate,
        "is_floating_rate": use_floating_rate,
        "floating_ref_rate": REFERENCE_INTEREST_RATE if use_floating_rate else None,
        "tenure_months": tenure_months,
        "repayment_method": repayment_method,
        "schedule": calc_result.get("schedule", []),
        "total_interest": calc_result["total_interest"],
        "total_payment": calc_result["total_payment"],
        "paid_installments": 0,
        "total_paid": 0,
        "remaining_principal": amount,
        "remaining_interest": calc_result["total_interest"],
        "status": "active",  # active, closed, defaulted, restructured
        "opened_at": now,
        "opened_date": _today_str(),
        "closed_at": None,
        "next_payment_date": now + 30 * 86400,
        "days_overdue": 0,
        "overdue_amount": 0,
        "late_payment_history": [],
        "ankibacked": product.get("ankibacked", False),
        "study_benefit_active": product.get("ankibacked", False),
    }

    # Giải ngân
    net_amount = amount - disbursement_fee
    set_balance(get_balance() + net_amount)
    add_transaction("loan_borrow", net_amount, f"Giải ngân {product['label']} (trừ phí {disbursement_fee:,}₫)".replace(",", "."))

    loans = _get_bank_loans()
    loans.append(loan)
    _save_bank_loans(loans)

    update_credit_history("loan_opened", f"Vay {product['label']} {amount:,}₫".replace(",", "."), 10)

    return {
        "ok": True,
        "loan_id": loan["id"],
        "product_label": product["label"],
        "principal": amount,
        "disbursed": net_amount,
        "disbursement_fee": disbursement_fee,
        "interest_rate_monthly": round(final_rate * 100, 2),
        "interest_rate_annual": round(final_rate * 12 * 100, 2),
        "is_floating": use_floating_rate,
        "tenure_months": tenure_months,
        "repayment_method": repayment_method,
        "first_installment": calc_result["first_installment"],
        "total_interest": calc_result["total_interest"],
        "total_payment": calc_result["total_payment"],
    }

def get_my_loans() -> list:
    """Trả về danh sách các khoản vay đang có."""
    loans = _get_bank_loans()
    now = _now()
    result = []

    for loan in loans:
        remaining = loan.get("remaining_principal", 0)
        # Tính toán số ngày quá hạn
        next_payment = loan.get("next_payment_date", now)
        days_overdue = max(0, int((now - next_payment) / 86400)) if remaining > 0 else 0
        debt_class = classify_debt(days_overdue)

        # Tính lãi phạt nếu quá hạn
        penalty_interest = 0
        if days_overdue > 0:
            # Lãi phạt = 150% lãi suất gốc (theo Thông tư 39/2016)
            penalty_rate = loan.get("monthly_rate", 0.01) * 1.5
            penalty_interest = int(remaining * penalty_rate * min(days_overdue, 90) / 30)

        progress_pct = 0
        if loan.get("original_principal", 0) > 0:
            progress_pct = round(
                (loan["original_principal"] - remaining) / loan["original_principal"] * 100, 1
            )

        result.append({
            "id": loan["id"],
            "product_code": loan["product_code"],
            "product_label": loan["product_label"],
            "original_principal": loan.get("original_principal", loan["principal"]),
            "principal": loan["principal"],
            "remaining_principal": remaining,
            "disbursed_amount": loan.get("disbursed_amount", loan["principal"]),
            "disbursement_fee": loan.get("disbursement_fee", 0),
            "annual_rate_pct": round(loan.get("annual_rate", 0.12) * 100, 2),
            "monthly_rate_pct": round(loan.get("monthly_rate", 0.01) * 100, 2),
            "is_floating_rate": loan.get("is_floating_rate", False),
            "tenure_months": loan.get("tenure_months", 12),
            "repayment_method": loan.get("repayment_method", "equal_installment"),
            "paid_installments": loan.get("paid_installments", 0),
            "total_paid": loan.get("total_paid", 0),
            "total_interest_expected": loan.get("total_interest", 0),
            "next_payment_date": loan.get("next_payment_date", now),
            "days_overdue": days_overdue,
            "is_overdue": days_overdue > 0,
            "penalty_interest": penalty_interest,
            "debt_classification": debt_class,
            "debt_classification_label": debt_class.get("label", "N1 - Đủ tiêu chuẩn"),
            "status": loan.get("status", "active"),
            "progress_pct": progress_pct,
            "opened_date": loan.get("opened_date", ""),
            "ankibacked": loan.get("ankibacked", False),
            "schedule_preview": loan.get("schedule", [])[:6],  # 6 kỳ đầu
        })
    return result

def repay_loan_installment(loan_id: str, amount: int = None, extra_principal: bool = False) -> dict:
    """
    Trả nợ định kỳ hoặc trả trước hạn.
    - amount = None: trả kỳ hiện tại theo schedule
    - amount = int: trả số tiền cụ thể
    - extra_principal = True: trả thêm gốc (giảm kỳ hạn)
    """
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    loans = _get_bank_loans()
    loan = next((l for l in loans if l["id"] == loan_id), None)
    if not loan:
        return {"ok": False, "error": "Không tìm thấy khoản vay."}
    if loan.get("status") != "active":
        return {"ok": False, "error": "Khoản vay đã đóng."}

    remaining = loan.get("remaining_principal", 0)
    if remaining <= 0:
        return {"ok": False, "error": "Khoản vay đã được tất toán."}

    now = _now()
    schedule = loan.get("schedule", [])
    paid_count = loan.get("paid_installments", 0)

    # Nếu không chỉ định amount, lấy số tiền kỳ hiện tại
    if amount is None:
        if paid_count < len(schedule):
            due = schedule[paid_count]
            amount = due.get("installment", 0)
        else:
            # Đã hết schedule, trả phần còn lại
            amount = remaining
    else:
        if amount <= 0:
            return {"ok": False, "error": "Số tiền không hợp lệ."}

    bal = get_balance()
    if bal < amount:
        return {"ok": False, "error": "Số dư ví không đủ."}

    # Xác định phần gốc và lãi
    if extra_principal and amount > 0:
        # Trả thêm gốc
        interest_part = int(remaining * loan.get("monthly_rate", 0.01))
        principal_part = amount - interest_part
        if principal_part > remaining:
            principal_part = remaining
    elif paid_count < len(schedule):
        due = schedule[paid_count]
        principal_part = due.get("principal", 0)
        interest_part = due.get("interest", 0)
        if amount != due.get("installment", 0):
            # Trả khác với schedule (trả nhiều hơn)
            base_interest = int(remaining * loan.get("monthly_rate", 0.01))
            interest_part = min(base_interest, amount)
            principal_part = amount - interest_part
    else:
        base_interest = int(remaining * loan.get("monthly_rate", 0.01))
        interest_part = min(base_interest, amount)
        principal_part = amount - interest_part

    # Đảm bảo không trả quá
    if principal_part > remaining:
        principal_part = remaining
        interest_part = max(0, amount - principal_part)

    # Kiểm tra phí trả trước hạn nếu trả thêm gốc
    early_fee = 0
    if extra_principal or principal_part > (remaining * 0.1):
        # Chỉ tính phí nếu trả > 10% dư nợ còn lại
        early_fee_rate = LOAN_PRODUCTS.get(loan["product_code"], {}).get("early_repayment_fee", 0.03)
        early_fee = int(principal_part * early_fee_rate)

    total_deduct = amount
    set_balance(bal - total_deduct)

    # Cập nhật khoản vay
    loan["remaining_principal"] = max(0, remaining - principal_part)
    loan["total_paid"] = loan.get("total_paid", 0) + total_deduct
    if not extra_principal and paid_count < len(schedule):
        loan["paid_installments"] = paid_count + 1

    # Cập nhật next_payment_date
    loan["next_payment_date"] = now + 30 * 86400

    # Kiểm tra đã trả hết chưa
    is_fully_paid = loan["remaining_principal"] <= 0
    if is_fully_paid:
        loan["status"] = "closed"
        loan["closed_at"] = now
        update_credit_history("loan_cleared",
            f"Tất toán khoản vay {loan['product_label']}", 30)

    _save_bank_loans(loans)
    add_transaction("loan_repay", total_deduct,
        f"Trả nợ {loan['product_label']} (gốc: {principal_part:,}₫, lãi: {interest_part:,}₫)".replace(",", "."))

    if early_fee > 0:
        add_transaction("loan_repay", early_fee,
            f"Phí trả trước hạn {loan['product_label']}")

    update_credit_history("payment_on_time",
        f"Trả {total_deduct:,}₫ khoản vay {loan['product_label']}".replace(",", "."), 10)

    return {
        "ok": True,
        "loan_id": loan_id,
        "paid": total_deduct,
        "principal_paid": principal_part,
        "interest_paid": interest_part,
        "early_repayment_fee": early_fee,
        "remaining_principal": loan["remaining_principal"],
        "fully_paid": is_fully_paid,
        "next_payment_date": loan["next_payment_date"],
    }

def process_loan_overdue() -> dict:
    """Xử lý quá hạn cho tất cả khoản vay."""
    from .transactions import add_transaction

    loans = _get_bank_loans()
    now = _now()
    results = []

    for loan in loans:
        if loan.get("status") != "active":
            continue
        remaining = loan.get("remaining_principal", 0)
        if remaining <= 0:
            continue

        next_payment = loan.get("next_payment_date", now)
        days_overdue = max(0, int((now - next_payment) / 86400))

        if days_overdue <= 0:
            continue

        # Grace period (mặc định 15 ngày)
        grace_days = 15
        if days_overdue > grace_days:
            # Tính lãi phạt (150% lãi suất gốc)
            monthly_rate = loan.get("monthly_rate", 0.01)
            penalty_rate = monthly_rate * 1.5
            penalty = int(remaining * penalty_rate * min(days_overdue - grace_days, 30) / 30)

            loan["remaining_principal"] = remaining + penalty
            loan["overdue_amount"] = loan.get("overdue_amount", 0) + penalty

            overdue_log = loan.get("late_payment_history", [])
            overdue_log.append({
                "date": _today_str(),
                "timestamp": now,
                "days_overdue": days_overdue,
                "penalty": penalty,
            })
            loan["late_payment_history"] = overdue_log[-30:]

            add_transaction("loan_penalty", penalty,
                f"Phạt quá hạn {loan['product_label']} ({days_overdue} ngày)")

        loan["days_overdue"] = days_overdue

        # Phân loại nợ xấu
        debt_class = classify_debt(days_overdue)
        if debt_class["group"] >= 3:
            update_credit_history("bad_debt",
                f"Khoản vay {loan['product_label']} chuyển {debt_class['label']} ({days_overdue} ngày)",
                -20 * debt_class["group"])
        if days_overdue >= 180:
            loan["status"] = "defaulted"
            update_credit_history("default",
                f"Khoản vay {loan['product_label']} bị mất khả năng thanh toán", -150)

        results.append({
            "loan_id": loan["id"],
            "product_label": loan["product_label"],
            "days_overdue": days_overdue,
            "debt_group": debt_class["group"],
            "debt_label": debt_class["label"],
        })

    if results:
        _save_bank_loans(loans)

    return {"processed": len(results), "details": results}

def restructure_loan(loan_id: str, new_tenure_months: int = None) -> dict:
    """
    Gia hạn / cơ cấu lại nợ.
    Cho phép giãn kỳ hạn khi khách hàng gặp khó khăn.
    """
    loans = _get_bank_loans()
    loan = next((l for l in loans if l["id"] == loan_id), None)
    if not loan:
        return {"ok": False, "error": "Không tìm thấy khoản vay."}
    if loan.get("status") not in ("active",):
        return {"ok": False, "error": "Khoản vay không thể cơ cấu lại."}

    # Chỉ cho gia hạn nếu có credit score >= 500 hoặc ankibacked
    credit_info = get_credit_score_info()
    if credit_info["score"] < 500 and not loan.get("ankibacked", False):
        return {"ok": False, "error": "Điểm tín dụng quá thấp để gia hạn."}

    remaining = loan.get("remaining_principal", 0)
    if remaining <= 0:
        return {"ok": False, "error": "Khoản vay đã tất toán."}

    old_tenure = loan.get("tenure_months", 12)
    old_paid = loan.get("paid_installments", 0)
    new_tenure = new_tenure_months or (old_tenure * 2)

    # Giới hạn gia hạn tối đa gấp đôi kỳ hạn gốc
    max_tenure = old_tenure * 2
    if new_tenure > max_tenure:
        new_tenure = max_tenure

    # Tính lại lịch trả nợ với kỳ hạn mới
    monthly_rate = loan.get("monthly_rate", 0.01)
    remaining_terms = new_tenure - old_paid
    if remaining_terms <= 0:
        remaining_terms = 6

    calc_result = calculate_loan_installment(
        remaining, monthly_rate * 12, remaining_terms, loan.get("repayment_method", "equal_installment")
    )

    if "error" in calc_result:
        return {"ok": False, "error": calc_result["error"]}

    old_status = dict(loan)

    loan["tenure_months"] = new_tenure
    loan["schedule"] = calc_result.get("schedule", [])
    loan["total_interest"] = old_status.get("total_paid", 0) + calc_result.get("total_interest", 0)
    loan["total_payment"] = remaining + calc_result.get("total_interest", 0)
    loan["restructured"] = True
    loan["restructured_at"] = _now()
    loan["restructure_count"] = loan.get("restructure_count", 0) + 1
    loan["next_payment_date"] = _now() + 30 * 86400
    loan["days_overdue"] = 0

    _save_bank_loans(loans)
    update_credit_history("loan_restructured",
        f"Cơ cấu lại khoản vay {loan['product_label']}: kỳ hạn mới {new_tenure} tháng", 15)

    return {
        "ok": True,
        "loan_id": loan_id,
        "old_tenure": old_tenure if not old_status.get("restructured") else old_status.get("tenure_months"),
        "new_tenure": new_tenure,
        "remaining_principal": remaining,
        "new_monthly_payment": calc_result.get("first_installment", 0),
        "new_total_interest": calc_result.get("total_interest", 0),
    }

# ═══════════════════════════════════════════════════════════════
# 4. COLLATERAL SYSTEM — TÀI SẢN THẾ CHẤP
# ═══════════════════════════════════════════════════════════════

def _get_collaterals_data() -> list:
    return cfg_list(_KEY_COLLATERAL, [])

def _save_collaterals_data(collaterals: list):
    cfg_set(_KEY_COLLATERAL, collaterals)

COLLATERAL_TYPES = {
    "real_estate": {
        "label": "Bất động sản",
        "emoji": "🏠",
        "base_ltv": 0.70,     # Cho vay tối đa 70%
        "valuation_method": "market_price",
    },
    "vehicle": {
        "label": "Phương tiện (xe hơi, xe máy)",
        "emoji": "🚗",
        "base_ltv": 0.60,     # Cho vay tối đa 60% (khấu hao)
        "valuation_method": "purchase_price_depreciated",
    },
    "savings": {
        "label": "Sổ tiết kiệm",
        "emoji": "🏦",
        "base_ltv": 0.90,     # Cho vay tối đa 90%
        "valuation_method": "face_value",
    },
    "stock": {
        "label": "Cổ phiếu niêm yết",
        "emoji": "📈",
        "base_ltv": 0.50,     # Cho vay tối đa 50%
        "valuation_method": "market_value",
    },
    "digital_asset": {
        "label": "Tài sản số (Crypto)",
        "emoji": "🪙",
        "base_ltv": 0.30,     # Cho vay tối đa 30% (rủi ro cao)
        "valuation_method": "market_value",
    },
}

def get_my_collaterals() -> list:
    """Danh sách tài sản thế chấp đã đăng ký."""
    collaterals = _get_collaterals_data()
    return [
        {
            **c,
            "type_info": COLLATERAL_TYPES.get(c.get("collateral_type", "real_estate"), {}),
        }
        for c in collaterals
    ]

def register_collateral(
    collateral_type: str,
    asset_id: str = None,
    estimated_value: int = None,
    description: str = ""
) -> dict:
    """
    Đăng ký tài sản thế chấp.
    Tự động định giá dựa trên loại tài sản và số liệu trong game.
    """
    if collateral_type not in COLLATERAL_TYPES:
        return {"ok": False, "error": "Loại tài sản thế chấp không hợp lệ."}

    type_info = COLLATERAL_TYPES[collateral_type]

    # Định giá tài sản
    valuation_result = _valuate_asset(collateral_type, asset_id, estimated_value)
    if "error" in valuation_result:
        return {"ok": False, "error": valuation_result["error"]}

    base_ltv = type_info["base_ltv"]

    # Điều chỉnh LTV dựa trên credit score
    credit_info = get_credit_score_info()
    if credit_info["score"] >= 700:
        base_ltv = min(1.0, base_ltv + 0.10)
    elif credit_info["score"] >= 600:
        base_ltv = min(1.0, base_ltv + 0.05)

    collateral = {
        "id": _generate_id("col_"),
        "collateral_type": collateral_type,
        "asset_id": asset_id or "",
        "label": type_info["label"],
        "emoji": type_info["emoji"],
        "description": description or type_info["label"],
        "valuation": valuation_result["valuation"],
        "valuation_method": valuation_result.get("method", "estimated"),
        "ltv_pct": base_ltv,
        "max_loan_amount": int(valuation_result["valuation"] * base_ltv),
        "registered_at": _now(),
        "verified": True,  # Game auto-verify
        "status": "active",
    }

    collaterals = _get_collaterals_data()
    collaterals.append(collateral)
    _save_collaterals_data(collaterals)

    return {
        "ok": True,
        "collateral_id": collateral["id"],
        "label": type_info["label"],
        "valuation": valuation_result["valuation"],
        "ltv_pct": base_ltv * 100,
        "max_loan": collateral["max_loan_amount"],
    }

def _valuate_asset(collateral_type: str, asset_id: str = None, estimated_value: int = None) -> dict:
    """Định giá tài sản dựa trên dữ liệu game."""
    if estimated_value and estimated_value > 0:
        return {"valuation": estimated_value, "method": "user_estimated"}

    if collateral_type == "savings":
        try:
            from .bank import get_total_savings
            savings = get_total_savings()
            if savings > 0:
                return {"valuation": savings, "method": "face_value"}
            return {"error": "Không có sổ tiết kiệm nào."}
        except Exception as e:
            logger.debug("_collateral_valuation (savings): %s", e)
            return {"error": "Không thể định giá sổ tiết kiệm."}

    elif collateral_type == "real_estate":
        try:
            from .real_estate import get_re_summary
            re = get_re_summary()
            total_value = int(re.get("total_value", 0) or 0)
            if total_value > 0:
                return {"valuation": total_value, "method": "market_price"}
            return {"error": "Không có bất động sản nào."}
        except Exception as e:
            logger.debug("_collateral_valuation (real_estate): %s", e)
            return {"error": "Không thể định giá BĐS."}

    elif collateral_type == "vehicle":
        # Định giá xe từ inventory
        try:
            from .inventory import get_inventory
            from .shop_data import load_shop_items
            inv = get_inventory()
            items = {i["id"]: i for i in load_shop_items()}
            vehicle_cats = {"Showroom xe hơi", "Showroom xe máy", "Showroom xe điện"}
            total_value = 0
            for iid in inv:
                item = items.get(iid)
                if item and any(c in item.get("category", "") for c in vehicle_cats):
                    price = item.get("price", 0)
                    total_value += int(price * 0.6)  # Khấu hao 40%
            if total_value > 0:
                return {"valuation": total_value, "method": "purchase_price_depreciated"}
            return {"error": "Không có xe nào trong kho.", "needs_manual": True}
        except Exception as e:
            logger.debug("_collateral_valuation (vehicle): %s", e)
            return {"error": "Không thể định giá xe."}

    elif collateral_type == "stock":
        try:
            from .stock_market import get_portfolio_value
            value = int(get_portfolio_value())
            if value > 0:
                return {"valuation": value, "method": "market_value"}
            return {"error": "Không có cổ phiếu nào."}
        except Exception as e:
            logger.debug("_collateral_valuation (stock): %s", e)
            return {"error": "Không thể định giá cổ phiếu."}

    elif collateral_type == "digital_asset":
        try:
            from .digital_assets import get_portfolio_value
            value = int(get_portfolio_value())
            if value > 0:
                return {"valuation": value, "method": "market_value"}
            return {"error": "Không có tài sản số nào."}
        except Exception as e:
            logger.debug("_collateral_valuation (digital_asset): %s", e)
            return {"error": "Không thể định giá tài sản số."}

    return {"error": "Không thể định giá tài sản này."}

def remove_collateral(collateral_id: str) -> dict:
    """Xoá tài sản thế chấp (khi trả hết nợ)."""
    collaterals = _get_collaterals_data()
    before = len(collaterals)
    collaterals = [c for c in collaterals if c["id"] != collateral_id]
    if len(collaterals) == before:
        return {"ok": False, "error": "Không tìm thấy tài sản thế chấp."}
    _save_collaterals_data(collaterals)
    return {"ok": True}

def get_collateral_summary() -> dict:
    """Tổng quan về tài sản thế chấp."""
    collaterals = _get_collaterals_data()
    total_valuation = sum(c.get("valuation", 0) for c in collaterals)
    total_max_loan = sum(c.get("max_loan_amount", 0) for c in collaterals)

    return {
        "count": len(collaterals),
        "total_valuation": total_valuation,
        "total_max_loan": total_max_loan,
        "collaterals": [
            {
                "id": c["id"],
                "label": c.get("label", ""),
                "emoji": c.get("emoji", "📦"),
                "valuation": c.get("valuation", 0),
                "max_loan": c.get("max_loan_amount", 0),
                "ltv_pct": round(c.get("ltv_pct", 0.7) * 100, 1),
            }
            for c in collaterals
        ],
    }

# ═══════════════════════════════════════════════════════════════
# 5. INCOME VERIFICATION — CHỨNG MINH THU NHẬP
# ═══════════════════════════════════════════════════════════════

def _get_income_verified() -> dict:
    return cfg_dict(_KEY_INCOME_VERIFIED, {
        "level": 0,
        "verified_at": None,
        "methods": {},
        "verified_income": 0,
    })

def _save_income_verified(data: dict):
    cfg_set(_KEY_INCOME_VERIFIED, data)

def calculate_verified_income() -> dict:
    """
    Tính thu nhập xác thực dựa trên các phương thức chứng minh.
    Kết quả dùng để xác định hạn mức tín dụng và vay vốn.
    """
    study = _get_study_stats()
    streak = _get_streak_info()
    balance = 0
    try:
        from .balance import get_balance
        balance = get_balance()
    except Exception as e:
        logger.debug("get_credit_score (balance): %s", e)

    asset_value = _get_total_asset_value()
    cards_reviewed = study.get("cards_reviewed", 0)
    current_streak = streak.get("current", 0)

    active_methods = {}
    total_weight = 0.0
    total_income = 0

    # Method 1: Study-based
    for level_info in INCOME_VERIFICATION_METHODS[0]["levels"]:
        if cards_reviewed >= level_info["cards_required"]:
            est_income = int(10_000_000 * level_info["income_multiplier"])  # Thu nhập cơ bản 10tr * multiplier
            active_methods["study_based"] = {
                "level": level_info["level"],
                "label": level_info["label"],
                "weight": level_info["weight"],
                "estimated_income": est_income,
            }
            total_income += int(est_income * level_info["weight"])
            total_weight += level_info["weight"]
            break

    # Method 2: Asset-based
    for level_info in INCOME_VERIFICATION_METHODS[1]["levels"]:
        if asset_value >= level_info["asset_value_required"]:
            est_income = int(asset_value * 0.12 / 12)  # 12%/năm sinh lời từ tài sản
            active_methods["asset_based"] = {
                "level": level_info["level"],
                "label": level_info["label"],
                "weight": level_info["weight"],
                "estimated_income": est_income,
            }
            total_income += int(est_income * level_info["weight"])
            total_weight += level_info["weight"]
            break

    # Method 3: Balance-based
    for level_info in INCOME_VERIFICATION_METHODS[2]["levels"]:
        if balance >= level_info["balance_required"]:
            est_income = int(balance * 0.06 / 12)  # 6%/năm lợi nhuận từ số dư
            active_methods["balance_based"] = {
                "level": level_info["level"],
                "label": level_info["label"],
                "weight": level_info["weight"],
                "estimated_income": est_income,
            }
            total_income += int(est_income * level_info["weight"])
            total_weight += level_info["weight"]
            break

    # Method 4: Streak-based
    for level_info in INCOME_VERIFICATION_METHODS[3]["levels"]:
        if current_streak >= level_info["streak_required"]:
            est_income = int(15_000_000 * level_info["income_multiplier"])  # Bonus từ kỷ luật
            active_methods["streak_based"] = {
                "level": level_info["level"],
                "label": level_info["label"],
                "weight": level_info["weight"],
                "estimated_income": est_income,
            }
            total_income += int(est_income * level_info["weight"])
            total_weight += level_info["weight"]
            break

    # Thu nhập xác thực cuối cùng
    if total_weight > 0:
        verified_income = int(total_income / total_weight) if total_weight > 0 else 0
    else:
        verified_income = 0

    # Tổng số phương thức
    methods_count = len(active_methods)
    overall_level = min(methods_count, 4)  # Level 0-4

    return {
        "overall_level": overall_level,
        "verified_income": verified_income,
        "active_methods": active_methods,
        "methods_count": methods_count,
        "total_weight": total_weight,
        "stats": {
            "cards_reviewed": cards_reviewed,
            "current_streak": current_streak,
            "balance": balance,
            "asset_value": asset_value,
        }
    }

def verify_income() -> dict:
    """Thực hiện xác thực thu nhập và lưu kết quả."""
    result = calculate_verified_income()
    income_data = _get_income_verified()
    income_data["level"] = result["overall_level"]
    income_data["verified_at"] = _now()
    income_data["methods"] = result["active_methods"]
    income_data["verified_income"] = result["verified_income"]
    _save_income_verified(income_data)

    update_credit_history("income_verified",
        f"Xác thực thu nhập: level {result['overall_level']}, {result['verified_income']:,}₫/tháng".replace(",", "."),
        result["overall_level"] * 10)

    return result

def get_income_verification_status() -> dict:
    """Trả về trạng thái chứng minh thu nhập hiện tại."""
    data = _get_income_verified()
    if not data.get("verified_at"):
        return {
            "verified": False,
            "level": 0,
            "verified_income": 0,
            "methods": {},
            "message": "Chưa chứng minh thu nhập",
        }

    return {
        "verified": True,
        "level": data.get("level", 0),
        "verified_income": data.get("verified_income", 0),
        "methods": data.get("methods", {}),
        "verified_at": data.get("verified_at"),
        "message": f"Thu nhập xác thực: {data.get('verified_income', 0):,}₫/tháng".replace(",", "."),
    }

# ═══════════════════════════════════════════════════════════════
# 6. LOAN INSURANCE — BẢO HIỂM KHOẢN VAY
# ═══════════════════════════════════════════════════════════════

LOAN_INSURANCE_PLANS = {
    "basic": {
        "label": "Bảo hiểm khoản vay Cơ bản",
        "emoji": "🛡️",
        "premium_rate": 0.01,       # 1% số tiền vay
        "coverage": 0.50,           # Bảo hiểm 50% dư nợ
        "covers": ["death", "disability"],
        "description": "Bảo hiểm rủi ro tử vong và tàn tật",
    },
    "standard": {
        "label": "Bảo hiểm khoản vay Tiêu chuẩn",
        "emoji": "🛡️",
        "premium_rate": 0.02,
        "coverage": 0.75,
        "covers": ["death", "disability", "unemployment"],
        "description": "Bảo hiểm rủi ro tử vong, tàn tật và thất nghiệp",
    },
    "premium": {
        "label": "Bảo hiểm khoản vay Cao cấp",
        "emoji": "💎",
        "premium_rate": 0.035,
        "coverage": 1.0,
        "covers": ["death", "disability", "unemployment", "critical_illness"],
        "description": "Bảo hiểm toàn diện mọi rủi ro",
    },
}

def get_loan_insurance_plans() -> list:
    return [{"id": k, **v} for k, v in LOAN_INSURANCE_PLANS.items()]

def _get_loan_insurance_data() -> list:
    return cfg_list(_KEY_LOAN_INSURANCE, [])

def _save_loan_insurance_data(data: list):
    cfg_set(_KEY_LOAN_INSURANCE, data)

def buy_loan_insurance(loan_id: str, plan_id: str) -> dict:
    """Mua bảo hiểm cho khoản vay."""
    from .balance import get_balance, set_balance
    from .transactions import add_transaction

    if plan_id not in LOAN_INSURANCE_PLANS:
        return {"ok": False, "error": "Gói bảo hiểm không hợp lệ."}

    loans = _get_bank_loans()
    loan = next((l for l in loans if l["id"] == loan_id), None)
    if not loan:
        return {"ok": False, "error": "Không tìm thấy khoản vay."}

    plan = LOAN_INSURANCE_PLANS[plan_id]
    premium = int(loan["principal"] * plan["premium_rate"])

    bal = get_balance()
    if bal < premium:
        return {"ok": False, "error": "Số dư không đủ."}

    set_balance(bal - premium)

    insurances = _get_loan_insurance_data()
    insurance_entry = {
        "id": _generate_id("ins_"),
        "loan_id": loan_id,
        "plan_id": plan_id,
        "plan_label": plan["label"],
        "premium": premium,
        "coverage": plan["coverage"],
        "covers": plan["covers"],
        "purchased_at": _now(),
        "status": "active",
    }
    insurances.append(insurance_entry)
    _save_loan_insurance_data(insurances)

    add_transaction("loan_insurance", premium, f"Mua {plan['label']} cho {loan['product_label']}")

    return {
        "ok": True,
        "insurance_id": insurance_entry["id"],
        "plan_label": plan["label"],
        "premium": premium,
        "coverage_pct": plan["coverage"] * 100,
    }

# ═══════════════════════════════════════════════════════════════
# 7. LOYALTY / SPECIAL OFFERS — KHÁCH HÀNG THÂN THIẾT
# ═══════════════════════════════════════════════════════════════

LOYALTY_TIERS = [
    {"tier": 0, "label": "Mới",           "min_points": 0,     "benefits": []},
    {"tier": 1, "label": "Đồng",           "min_points": 100,   "benefits": ["Giảm 5% phí thường niên"]},
    {"tier": 2, "label": "Bạc",            "min_points": 500,   "benefits": ["Giảm 10% phí thường niên", "+1% lãi suất tiết kiệm"]},
    {"tier": 3, "label": "Vàng",           "min_points": 2000,  "benefits": ["Giảm 15% phí thường niên", "+2% lãi suất tiết kiệm", "Miễn phí giải ngân"]},
    {"tier": 4, "label": "Bạch kim",       "min_points": 5000,  "benefits": ["Miễn phí thường niên", "+3% lãi suất tiết kiệm", "Miễn phí giải ngân", "Tăng 10% hạn mức"]},
    {"tier": 5, "label": "Kim cương",      "min_points": 15000, "benefits": ["Miễn phí thường niên", "+5% lãi suất tiết kiệm", "Miễn phí tất cả", "Tăng 20% hạn mức", "Ngân hàng riêng"]},
]

def _get_loyalty_data() -> dict:
    return cfg_dict(_KEY_LOYALTY, {
        "points": 0,
        "tier": 0,
        "total_products": 0,
        "total_loans": 0,
        "total_interest_paid": 0,
    })

def _save_loyalty_data(data: dict):
    cfg_set(_KEY_LOYALTY, data)

def get_loyalty_status() -> dict:
    """Trả về trạng thái khách hàng thân thiết."""
    data = _get_loyalty_data()
    current_tier = 0
    for tier_info in reversed(LOYALTY_TIERS):
        if data.get("points", 0) >= tier_info["min_points"]:
            current_tier = tier_info["tier"]
            break

    data["tier"] = current_tier
    _save_loyalty_data(data)

    next_tier = None
    for tier_info in LOYALTY_TIERS:
        if tier_info["tier"] > current_tier:
            next_tier = tier_info
            break

    current_benefits = LOYALTY_TIERS[current_tier]["benefits"] if current_tier < len(LOYALTY_TIERS) else []

    return {
        "points": data.get("points", 0),
        "tier": current_tier,
        "tier_label": LOYALTY_TIERS[current_tier]["label"] if current_tier < len(LOYALTY_TIERS) else "Mới",
        "benefits": current_benefits,
        "next_tier": next_tier,
        "products_count": data.get("total_products", 0),
        "loans_count": data.get("total_loans", 0),
    }

def _add_loyalty_points(points: int):
    """Thêm điểm thân thiết."""
    data = _get_loyalty_data()
    data["points"] = data.get("points", 0) + points
    _save_loyalty_data(data)

# ═══════════════════════════════════════════════════════════════
# 8. BANKING STUDY INTEGRATION — TÍCH HỢP HỌC ANKI
# ═══════════════════════════════════════════════════════════════

def get_ankibacked_benefits() -> dict:
    """
    Tính toán các ưu đãi dựa trên thành tích học Anki.
    Học càng nhiều → càng được hưởng nhiều ưu đãi.
    """
    study = _get_study_stats()
    streak = _get_streak_info()
    credit = get_credit_score_info()

    cards = study.get("cards_reviewed", 0)
    current_streak = streak.get("current", 0)
    score = credit["score"]

    benefits = {
        "cards_reviewed": cards,
        "current_streak": current_streak,
        "credit_score": score,
        "interest_rate_discount": 0,
        "limit_boost_pct": 0,
        "fee_waivers": [],
    }

    # Giảm lãi suất dựa trên số thẻ đã học
    if cards >= 10000:
        benefits["interest_rate_discount"] = 0.008  # Giảm 0.8%/tháng
        benefits["limit_boost_pct"] = 0.30
        benefits["fee_waivers"].append("Miễn phí thường niên tất cả thẻ")
    elif cards >= 5000:
        benefits["interest_rate_discount"] = 0.005
        benefits["limit_boost_pct"] = 0.20
        benefits["fee_waivers"].append("Miễn phí thường niên thẻ Chuẩn & Vàng")
    elif cards >= 2000:
        benefits["interest_rate_discount"] = 0.003
        benefits["limit_boost_pct"] = 0.10
        benefits["fee_waivers"].append("Miễn phí thường niên thẻ Chuẩn")
    elif cards >= 500:
        benefits["interest_rate_discount"] = 0.001
        benefits["limit_boost_pct"] = 0.05

    # Bonus từ streak
    if current_streak >= 365:
        benefits["interest_rate_discount"] = min(0.015, benefits["interest_rate_discount"] + 0.005)
        benefits["fee_waivers"].append("Miễn phí giải ngân tất cả khoản vay")
    elif current_streak >= 90:
        benefits["interest_rate_discount"] = min(0.010, benefits["interest_rate_discount"] + 0.003)
    elif current_streak >= 30:
        benefits["interest_rate_discount"] = min(0.008, benefits["interest_rate_discount"] + 0.001)

    # Bonus từ credit score
    if score >= 750:
        benefits["interest_rate_discount"] = min(0.020, benefits["interest_rate_discount"] + 0.005)
        benefits["limit_boost_pct"] = max(benefits["limit_boost_pct"], 0.25)
    elif score >= 650:
        benefits["interest_rate_discount"] = min(0.015, benefits["interest_rate_discount"] + 0.003)

    return benefits

def sync_study_to_credit():
    """
    Đồng bộ dữ liệu học Anki vào hệ thống tín dụng.
    Gọi định kỳ từ __init__.py để cập nhật credit score.
    """
    old_data = _get_credit_score_data()
    old_score = old_data.get("score", 450)
    new_score = calculate_credit_score()

    diff = new_score - old_score
    old_data["score"] = new_score
    old_data["last_updated"] = _now()
    _save_credit_score_data(old_data)

    # Tự động verify income nếu chưa
    income_data = _get_income_verified()
    if not income_data.get("verified_at"):
        verify_income()

    # Thêm loyalty points cho việc học
    study = _get_study_stats()
    cards = study.get("cards_reviewed", 0)
    streak = _get_streak_info()
    # Mỗi 100 thẻ = 1 loyalty point
    loyalty_points = cards // 100
    _add_loyalty_points(max(0, loyalty_points - _get_loyalty_data().get("points", 0)))

    return {
        "old_score": old_score,
        "new_score": new_score,
        "change": diff,
        "score_rating": get_credit_score_info()["rating"],
    }

# ═══════════════════════════════════════════════════════════════
# 9. MASTER SUMMARY — TỔNG HỢP NGÂN HÀNG
# ═══════════════════════════════════════════════════════════════

def get_full_banking_summary() -> dict:
    """Trả về tổng quan toàn bộ hệ thống ngân hàng."""
    credit_info = get_credit_score_info()
    cards = get_my_credit_cards()
    loans = get_my_loans()
    income = get_income_verification_status()
    collateral_summary = get_collateral_summary()
    loyalty = get_loyalty_status()
    benefits = get_ankibacked_benefits()

    total_debt = sum(c.get("used_credit", 0) for c in cards)
    total_limit = sum(c.get("approved_limit", 0) for c in cards)
    total_loan_remaining = sum(l.get("remaining_principal", 0) for l in loans if l.get("status") == "active")

    # Nợ tốt (nhóm 1-2) / nợ xấu (nhóm 3-5)
    bad_loans = [l for l in loans if l.get("debt_classification", {}).get("group", 1) >= 3]
    good_loans = [l for l in loans if l.get("debt_classification", {}).get("group", 1) < 3]

    return {
        "credit_score": credit_info,
        "credit_cards": {
            "total": len(cards),
            "total_limit": total_limit,
            "total_used": total_debt,
            "utilization_pct": round(total_debt / max(1, total_limit) * 100, 1) if cards else 0,
            "cards": cards,
        },
        "loans": {
            "total_active": len([l for l in loans if l.get("status") == "active"]),
            "total_remaining": total_loan_remaining,
            "bad_debt_count": len(bad_loans),
            "good_debt_count": len(good_loans),
            "loans": loans,
        },
        "income": income,
        "collateral": collateral_summary,
        "loyalty": loyalty,
        "ankibacked_benefits": benefits,
    }

# ═══════════════════════════════════════════════════════════════
# 9b. SHOP PAYMENT — THANH TOÁN MUA HÀNG HỖN HỢP
# ═══════════════════════════════════════════════════════════════

def process_shop_payment(price: int, cash_amount: int = 0,
                         card_id: str = None, card_amount: int = 0) -> dict:
    """
    Xử lý phần THẺ TÍN DỤNG của thanh toán mua hàng (không xử lý tiền mặt).
      - cash_amount > 0, card_id = None   → thanh toán 100% tiền mặt
      - cash_amount = 0, card_id != None  → thanh toán 100% thẻ tín dụng
      - cash_amount > 0, card_id != None  → thanh toán hỗn hợp (split)

    LƯU Ý: Hàm này CHỈ xử lý thẻ tín dụng (gọi use_credit_card).
           Tiền mặt do caller xử lý qua set_balance_and_log.

    Args:
        price: Tổng tiền hàng
        cash_amount: Số tiền trả bằng tiền mặt (VND, chỉ để kiểm tra)
        card_id: ID thẻ tín dụng (None nếu không dùng thẻ)
        card_amount: Số tiền trả bằng thẻ tín dụng (VND)

    Returns:
        dict with ok / error + thông tin chi tiết
    """
    from .balance import get_balance

    # ── Validation ──────────────────────────────────────────────
    if cash_amount < 0 or card_amount < 0:
        return {"ok": False, "error": "Số tiền không hợp lệ."}

    total_paid = cash_amount + card_amount
    if total_paid != price:
        return {"ok": False, "error": f"Tổng tiền thanh toán ({total_paid:,}₫) không khớp với giá ({price:,}₫).".replace(",", ".")}

    # ── Kiểm tra tiền mặt (do caller xử lý sau) ────────────────
    if cash_amount > 0:
        bal = get_balance()
        if bal < cash_amount:
            shortage = cash_amount - bal
            return {"ok": False, "error": f"Không đủ tiền mặt! Cần thêm {shortage:,}₫ trong ví.".replace(",", ".")}

    # ── Xử lý thẻ tín dụng ─────────────────────────────────────
    used_card_label = None
    rewards_earned = 0
    if card_amount > 0:
        if not card_id:
            return {"ok": False, "error": "Chưa chọn thẻ tín dụng."}

        card_result = use_credit_card(
            card_id=card_id,
            amount=card_amount,
            merchant="Mua sắm trong game",
            category="shopping"
        )
        if not card_result.get("ok"):
            return card_result

        used_card_label = card_result.get("product_label", card_id)
        rewards_earned = card_result.get("rewards_earned", 0)

    return {
        "ok": True,
        "price": price,
        "cash_used": cash_amount,
        "card_used": card_amount,
        "card_id": card_id,
        "used_card_label": used_card_label,
        "rewards_earned": rewards_earned,
        "remaining_balance": get_balance(),
    }


# ═══════════════════════════════════════════════════════════════
# 10. DAILY/PERIODIC PROCESSING — XỬ LÝ ĐỊNH KỲ
# ═══════════════════════════════════════════════════════════════

def process_daily_banking() -> dict:
    """
    Xử lý ngân hàng hàng ngày:
    - Đồng bộ credit score
    - Phạt trả chậm thẻ tín dụng
    - Xử lý quá hạn khoản vay
    - Thu phí thường niên
    - Tính điểm loyalty
    """
    results = {}

    # 1. Đồng bộ học -> credit
    results["sync"] = sync_study_to_credit()

    # 2. Phạt trả chậm thẻ tín dụng
    results["late_penalties"] = process_late_payment_penalties()

    # 3. Xử lý quá hạn khoản vay
    results["overdue"] = process_loan_overdue()

    # 4. Thu phí thường niên
    results["annual_fees"] = process_credit_card_annual_fees()

    # 5. Tự động chứng minh thu nhập
    results["income_verify"] = verify_income()

    return results
