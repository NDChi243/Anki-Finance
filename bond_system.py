# -*- coding: utf-8 -*-
from __future__ import annotations
from .logger import get_logger
logger = get_logger(__name__)
"""
bond_system.py — Hệ thống Trái phiếu Anki Finance v1.0
======================================================
Mô phỏng thị trường trái phiếu Việt Nam với các loại:
  - Trái phiếu Chính phủ (Government Bonds)
  - Trái phiếu Doanh nghiệp (Corporate Bonds)
  - Trái phiếu Đô thị (Municipal Bonds)
  - Trái phiếu có Tài sản đảm bảo (Secured Bonds)
  - Trái phiếu Chuyển đổi (Convertible Bonds)

Cơ chế:
  - Lãi suất coupon cố định / thả nổi theo kỳ hạn
  - Thanh toán coupon định kỳ (mỗi lần update tương đương ~1 tháng)
  - Đáo hạn (maturity): hoàn trả mệnh giá
  - Giao dịch thứ cấp: mua/bán trái phiếu theo giá thị trường
  - Trái phiếu chuyển đổi: có thể chuyển thành cổ phiếu (tham khảo stock_market)
  - Accrued interest (lãi tích lũy) khi mua/bán giữa kỳ
"""

import time
import math
import random
from datetime import datetime, timedelta
from ._safe_config import col_ready, cfg_int, cfg_dict, cfg_list, cfg_set

# ═══════════════════════════════════════════════════════════════
#  CONFIG KEYS
# ═══════════════════════════════════════════════════════════════

_KEY_BOND_MARKET     = "anki_tycoon_bonds_market"         # dict{bond_id: bond_data}
_KEY_BOND_PORTFOLIO  = "anki_tycoon_bonds_portfolio"      # list[holding]
_KEY_BOND_LAST_UPDATE = "anki_tycoon_bonds_last_update"    # float timestamp
_KEY_BOND_REVIEW_CNT = "anki_tycoon_bonds_review_count"   # int
_KEY_BOND_COUPON_LOG  = "anki_tycoon_bonds_coupon_log"    # list[coupon_event]
_KEY_BOND_TXNS        = "anki_tycoon_bonds_transactions"   # list[txn]

UPDATE_INTERVAL_SECS = 4 * 3600   # 4 giờ (như stock)
REVIEWS_PER_UPDATE   = 50         # số thẻ cần ôn để trả coupon
MAX_LOG_ENTRIES      = 50

# ═══════════════════════════════════════════════════════════════
#  BOND DEFINITIONS — Dữ liệu tham khảo thị trường trái phiếu VN
# ═══════════════════════════════════════════════════════════════
#
# Cấu trúc mỗi bond:
#   id: mã trái phiếu
#   name: tên hiển thị
#   type: loại trái phiếu
#   issuer: tổ chức phát hành
#   face_value: mệnh giá (VND)
#   coupon_rate: lãi suất coupon năm (float, ví dụ 0.05 = 5%)
#   tenure_months: kỳ hạn (tháng)
#   coupon_freq_months: tần suất trả coupon (tháng)
#   risk_level: mức rủi ro (1-5, 1=thấp nhất)
#   sector: ngành
#   floating: bool — lãi suất thả nổi?
#   convertible: bool — có thể chuyển đổi?
#   base_price: giá tham chiếu (% mệnh giá, 100 = ngang mệnh giá)
#   min_holding: số lượng mua tối thiểu
#   description: mô tả

BOND_DEFINITIONS = [
    # ── Trái phiếu Chính phủ (Government Bonds) ──
    {
        "id": "bond_gov_tp105",
        "name": "TP105 - Trái phiếu Chính phủ 5 năm",
        "type": "Chính phủ",
        "issuer": "Kho bạc Nhà nước",
        "face_value": 1_000_000,
        "coupon_rate": 0.038,       # 3.8%/năm
        "tenure_months": 60,
        "coupon_freq_months": 6,     # 6 tháng/lần
        "risk_level": 1,
        "sector": "Chính phủ",
        "floating": False,
        "convertible": False,
        "base_price": 100.0,
        "min_holding": 5,
        "description": "Trái phiếu Kho bạc Nhà nước kỳ hạn 5 năm, lãi suất cố định 3.8%/năm, thanh toán coupon 6 tháng/lần. An toàn nhất thị trường.",
        "emoji": "🏛️",
    },
    {
        "id": "bond_gov_tp110",
        "name": "TP110 - Trái phiếu Chính phủ 10 năm",
        "type": "Chính phủ",
        "issuer": "Kho bạc Nhà nước",
        "face_value": 1_000_000,
        "coupon_rate": 0.045,       # 4.5%/năm
        "tenure_months": 120,
        "coupon_freq_months": 6,
        "risk_level": 1,
        "sector": "Chính phủ",
        "floating": False,
        "convertible": False,
        "base_price": 100.0,
        "min_holding": 5,
        "description": "Trái phiếu Chính phủ kỳ hạn 10 năm, lãi suất cố định 4.5%/năm. Phù hợp với chiến lược đầu tư dài hạn.",
        "emoji": "🏛️",
    },
    {
        "id": "bond_gov_tbt3",
        "name": "TBT3 - Tín phiếu Kho bạc 3 tháng",
        "type": "Chính phủ",
        "issuer": "Kho bạc Nhà nước",
        "face_value": 500_000,
        "coupon_rate": 0.025,       # 2.5%/năm
        "tenure_months": 3,
        "coupon_freq_months": 3,     # Trả lãi khi đáo hạn
        "risk_level": 1,
        "sector": "Chính phủ",
        "floating": False,
        "convertible": False,
        "base_price": 98.5,
        "min_holding": 10,
        "description": "Tín phiếu Kho bạc kỳ hạn ngắn, thanh khoản cao, lãi suất thấp. Công cụ đầu tư ngắn hạn an toàn.",
        "emoji": "📜",
    },
    # ── Trái phiếu Đô thị (Municipal Bonds) ──
    {
        "id": "bond_muni_hcmc",
        "name": "TPHCM 2030 - Trái phiếu Đô thị TP.HCM",
        "type": "Đô thị",
        "issuer": "UBND TP.HCM",
        "face_value": 1_000_000,
        "coupon_rate": 0.052,       # 5.2%/năm
        "tenure_months": 72,
        "coupon_freq_months": 6,
        "risk_level": 2,
        "sector": "Đô thị",
        "floating": False,
        "convertible": False,
        "base_price": 100.0,
        "min_holding": 5,
        "description": "Trái phiếu chính quyền địa phương TP.HCM, kỳ hạn 6 năm, lãi suất 5.2%/năm. Đầu tư vào hạ tầng đô thị.",
        "emoji": "🏙️",
    },
    {
        "id": "bond_muni_hanoi",
        "name": "HN 2028 - Trái phiếu Đô thị Hà Nội",
        "type": "Đô thị",
        "issuer": "UBND TP.Hà Nội",
        "face_value": 1_000_000,
        "coupon_rate": 0.050,       # 5.0%/năm
        "tenure_months": 60,
        "coupon_freq_months": 6,
        "risk_level": 2,
        "sector": "Đô thị",
        "floating": False,
        "convertible": False,
        "base_price": 100.0,
        "min_holding": 5,
        "description": "Trái phiếu chính quyền địa phương Hà Nội, kỳ hạn 5 năm, lãi suất 5.0%/năm.",
        "emoji": "🏙️",
    },
    # ── Trái phiếu Doanh nghiệp (Corporate Bonds) ──
    {
        "id": "bond_corp_vcb",
        "name": "VCB-CB2028 - Trái phiếu Ngân hàng Vietcombank",
        "type": "Doanh nghiệp",
        "issuer": "Ngân hàng TMCP Ngoại thương Việt Nam (Vietcombank)",
        "face_value": 1_000_000,
        "coupon_rate": 0.058,       # 5.8%/năm
        "tenure_months": 48,
        "coupon_freq_months": 3,     # 3 tháng/lần
        "risk_level": 2,
        "sector": "Ngân hàng",
        "floating": False,
        "convertible": False,
        "base_price": 100.5,
        "min_holding": 5,
        "description": "Trái phiếu do Vietcombank phát hành, kỳ hạn 4 năm, lãi suất 5.8%/năm. Ngân hàng thương mại nhà nước lớn nhất VN.",
        "emoji": "🏦",
    },
    {
        "id": "bond_corp_vnm",
        "name": "VNM-CB2027 - Trái phiếu Vinamilk",
        "type": "Doanh nghiệp",
        "issuer": "Công ty CP Sữa Việt Nam (Vinamilk)",
        "face_value": 1_000_000,
        "coupon_rate": 0.062,       # 6.2%/năm
        "tenure_months": 36,
        "coupon_freq_months": 6,
        "risk_level": 2,
        "sector": "Thực phẩm",
        "floating": False,
        "convertible": False,
        "base_price": 101.0,
        "min_holding": 5,
        "description": "Trái phiếu Vinamilk kỳ hạn 3 năm, lãi suất 6.2%/năm. Doanh nghiệp hàng đầu ngành sữa Việt Nam.",
        "emoji": "🥛",
    },
    {
        "id": "bond_corp_hpg",
        "name": "HPG-CB2029 - Trái phiếu Hòa Phát",
        "type": "Doanh nghiệp",
        "issuer": "Tập đoàn Hòa Phát",
        "face_value": 1_000_000,
        "coupon_rate": 0.072,       # 7.2%/năm
        "tenure_months": 60,
        "coupon_freq_months": 6,
        "risk_level": 3,
        "sector": "Thép",
        "floating": False,
        "convertible": False,
        "base_price": 99.0,
        "min_holding": 5,
        "description": "Trái phiếu Tập đoàn Hòa Phát kỳ hạn 5 năm, lãi suất 7.2%/năm. Rủi ro trung bình, lợi suất hấp dẫn.",
        "emoji": "🏭",
    },
    {
        "id": "bond_corp_vinhomes",
        "name": "VHM-CB2030 - Trái phiếu Vinhomes",
        "type": "Doanh nghiệp",
        "issuer": "Công ty CP Vinhomes",
        "face_value": 1_000_000,
        "coupon_rate": 0.095,       # 9.5%/năm
        "tenure_months": 72,
        "coupon_freq_months": 6,
        "risk_level": 4,
        "sector": "Bất động sản",
        "floating": False,
        "convertible": False,
        "base_price": 96.0,
        "min_holding": 5,
        "description": "Trái phiếu Vinhomes kỳ hạn 6 năm, lãi suất cao 9.5%/năm. Rủi ro cao hơn do ngành BĐS biến động.",
        "emoji": "🏗️",
    },
    {
        "id": "bond_corp_masan",
        "name": "MSN-CB2028 - Trái phiếu Masan Group",
        "type": "Doanh nghiệp",
        "issuer": "Tập đoàn Masan",
        "face_value": 1_000_000,
        "coupon_rate": 0.085,       # 8.5%/năm
        "tenure_months": 48,
        "coupon_freq_months": 6,
        "risk_level": 3,
        "sector": "Hàng tiêu dùng",
        "floating": False,
        "convertible": False,
        "base_price": 98.5,
        "min_holding": 5,
        "description": "Trái phiếu Masan Group kỳ hạn 4 năm, lãi suất 8.5%/năm. Mức rủi ro trung bình.",
        "emoji": "🛒",
    },
    # ── Trái phiếu có Tài sản đảm bảo (Secured Bonds) ──
    {
        "id": "bond_sec_techcombank",
        "name": "TCB-SEC2027 - Trái phiếu Techcombank (Có TSĐB)",
        "type": "Có tài sản đảm bảo",
        "issuer": "Ngân hàng TMCP Kỹ thương Việt Nam (Techcombank)",
        "face_value": 1_000_000,
        "coupon_rate": 0.065,       # 6.5%/năm
        "tenure_months": 36,
        "coupon_freq_months": 3,
        "risk_level": 2,
        "sector": "Ngân hàng",
        "floating": False,
        "convertible": False,
        "base_price": 101.5,
        "min_holding": 5,
        "description": "Trái phiếu Techcombank có tài sản đảm bảo, kỳ hạn 3 năm, lãi suất 6.5%/năm. An toàn cao nhờ TSĐB.",
        "emoji": "🔒",
    },
    {
        "id": "bond_sec_mbbank",
        "name": "MBB-SEC2028 - Trái phiếu MB Bank (Có TSĐB)",
        "type": "Có tài sản đảm bảo",
        "issuer": "Ngân hàng TMCP Quân đội (MB Bank)",
        "face_value": 1_000_000,
        "coupon_rate": 0.068,       # 6.8%/năm
        "tenure_months": 48,
        "coupon_freq_months": 6,
        "risk_level": 2,
        "sector": "Ngân hàng",
        "floating": False,
        "convertible": False,
        "base_price": 101.0,
        "min_holding": 5,
        "description": "Trái phiếu MB Bank có tài sản đảm bảo, kỳ hạn 4 năm, lãi suất 6.8%/năm.",
        "emoji": "🔒",
    },
    # ── Trái phiếu Chuyển đổi (Convertible Bonds) ──
    {
        "id": "bond_conv_fpt",
        "name": "FPT-CB2029 - Trái phiếu Chuyển đổi FPT",
        "type": "Chuyển đổi",
        "issuer": "Công ty CP FPT",
        "face_value": 1_000_000,
        "coupon_rate": 0.045,       # 4.5%/năm (thấp hơn do có quyền chuyển đổi)
        "tenure_months": 60,
        "coupon_freq_months": 6,
        "risk_level": 3,
        "sector": "Công nghệ",
        "floating": False,
        "convertible": True,
        "conversion_ratio": 0.5,     # 1 TP -> 0.5 CP (tham khảo giá FPT)
        "base_price": 105.0,
        "min_holding": 5,
        "description": "Trái phiếu chuyển đổi FPT kỳ hạn 5 năm, lãi suất 4.5%/năm + quyền chuyển thành cổ phiếu FPT. Phù hợp nhà đầu tư muốn linh hoạt.",
        "emoji": "🔄",
    },
    {
        "id": "bond_conv_vic",
        "name": "VIC-CB2030 - Trái phiếu Chuyển đổi Vingroup",
        "type": "Chuyển đổi",
        "issuer": "Tập đoàn Vingroup",
        "face_value": 1_000_000,
        "coupon_rate": 0.050,       # 5.0%/năm
        "tenure_months": 72,
        "coupon_freq_months": 6,
        "risk_level": 4,
        "sector": "Đa ngành",
        "floating": False,
        "convertible": True,
        "conversion_ratio": 0.3,
        "base_price": 103.0,
        "min_holding": 5,
        "description": "Trái phiếu chuyển đổi Vingroup kỳ hạn 6 năm, lãi suất 5.0%/năm. Có thể chuyển thành cổ phiếu VIC theo tỷ lệ định trước.",
        "emoji": "🔄",
    },
    # ── Trái phiếu lãi suất thả nổi (Floating Rate Notes) ──
    {
        "id": "bond_float_acb",
        "name": "ACB-FRN2028 - Trái phiếu ACB lãi suất thả nổi",
        "type": "Doanh nghiệp",
        "issuer": "Ngân hàng TMCP Á Châu (ACB)",
        "face_value": 1_000_000,
        "coupon_rate": 0.055,       # 5.5%/năm (tham chiếu)
        "tenure_months": 48,
        "coupon_freq_months": 3,
        "risk_level": 2,
        "sector": "Ngân hàng",
        "floating": True,
        "floating_spread": 0.015,   # +1.5%/năm so với lãi suất tham chiếu
        "convertible": False,
        "base_price": 100.0,
        "min_holding": 5,
        "description": "Trái phiếu ACB lãi suất thả nổi (tham chiếu lãi suất liên ngân hàng + biên độ 1.5%/năm), kỳ hạn 4 năm.",
        "emoji": "🌊",
    },
]

# Build lookup dict
_BONDS_MAP: dict = {b["id"]: b for b in BOND_DEFINITIONS}


# ═══════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_bonds_review_count() -> int:
    return cfg_int(_KEY_BOND_REVIEW_CNT, 0)

def _set_bonds_review_count(n: int):
    cfg_set(_KEY_BOND_REVIEW_CNT, int(n))

def record_review(count: int = 1):
    """Ghi nhận số thẻ đã review cho bond system."""
    cur = _get_bonds_review_count()
    _set_bonds_review_count(cur + count)


# ═══════════════════════════════════════════════════════════════
#  MARKET DATA
# ═══════════════════════════════════════════════════════════════

def _get_market() -> dict:
    return cfg_dict(_KEY_BOND_MARKET, {})

def _set_market(data: dict):
    cfg_set(_KEY_BOND_MARKET, data)

def _get_last_update() -> float:
    return float(cfg_int(_KEY_BOND_LAST_UPDATE, 0))

def _set_last_update(ts: float):
    cfg_set(_KEY_BOND_LAST_UPDATE, int(ts))

def _get_portfolio() -> list:
    return cfg_list(_KEY_BOND_PORTFOLIO, [])

def _set_portfolio(data: list):
    cfg_set(_KEY_BOND_PORTFOLIO, data)

def _get_coupon_log() -> list:
    return cfg_list(_KEY_BOND_COUPON_LOG, [])

def _set_coupon_log(data: list):
    cfg_set(_KEY_BOND_COUPON_LOG, data)

def _get_txns() -> list:
    return cfg_list(_KEY_BOND_TXNS, [])

def _set_txns(data: list):
    cfg_set(_KEY_BOND_TXNS, data)

def _add_txn(txn_type: str, bond_id: str, amount: int, detail: str = ""):
    """Thêm 1 giao dịch bond vào lịch sử."""
    txns = _get_txns()
    bond = _BONDS_MAP.get(bond_id, {})
    txns.append({
        "ts": time.time(),
        "type": txn_type,
        "bond_id": bond_id,
        "bond_name": bond.get("name", bond_id),
        "amount": amount,
        "detail": detail,
    })
    if len(txns) > MAX_LOG_ENTRIES:
        txns = txns[-MAX_LOG_ENTRIES:]
    _set_txns(txns)


def _seed_market_if_empty():
    """Tạo market data nếu chưa có."""
    market = _get_market()
    if market:
        return
    now = time.time()
    market = {}
    for b in BOND_DEFINITIONS:
        bid = b["id"]
        # Giá khởi tạo: base_price ± nhiễu nhẹ
        base = b["base_price"]
        noise = random.uniform(-2.0, 2.0)
        price = round(base + noise, 2)
        market[bid] = {
            "current_price": price,
            "prev_price": price,
            "base_price": base,
            "last_update": now,
            "price_history": [[now, price]],
            "maturity_date": now + b["tenure_months"] * 30 * 86400,  # 30 ngày/tháng
            "total_coupon_paid": 0,
            "holders": 0,
        }
    _set_market(market)
    _set_last_update(now)


def _update_bond_prices_if_needed(force: bool = False):
    """Cập nhật giá trái phiếu dựa trên biến động thị trường."""
    now = time.time()
    last = _get_last_update()
    
    if not force and (now - last) < UPDATE_INTERVAL_SECS:
        return False

    market = _get_market()
    if not market:
        return False

    # Random walk cho giá mỗi bond
    for bid, data in market.items():
        bond_def = _BONDS_MAP.get(bid)
        if not bond_def:
            continue
        
        base = data.get("base_price", 100.0)
        prev = data.get("current_price", base)
        
        # Biến động giá: ±3% cho mỗi lần update
        volatility = 0.03
        change_pct = random.uniform(-volatility, volatility)
        new_price = prev * (1.0 + change_pct)
        
        # Mean reversion về base_price
        reversion_strength = 0.1
        new_price = new_price + (base - new_price) * reversion_strength
        
        # Giới hạn ±20% so với base
        min_price = base * 0.80
        max_price = base * 1.20
        new_price = max(min_price, min(max_price, new_price))
        new_price = round(new_price, 2)
        
        data["prev_price"] = prev
        data["current_price"] = new_price
        data["last_update"] = now
        
        # Price history
        history = data.get("price_history", [])
        history.append([now, new_price])
        if len(history) > 50:
            history = history[-50:]
        data["price_history"] = history
    
    _set_market(market)
    _set_last_update(now)
    return True


# ═══════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════

def get_all_bonds() -> list:
    """Trả về danh sách tất cả trái phiếu + giá thị trường."""
    _seed_market_if_empty()
    market = _get_market()
    result = []
    for b in BOND_DEFINITIONS:
        bid = b["id"]
        m = market.get(bid, {})
        entry = dict(b)
        entry["current_price"] = m.get("current_price", b["base_price"])
        entry["prev_price"] = m.get("prev_price", b["base_price"])
        entry["price_change_pct"] = round(
            (entry["current_price"] - entry["prev_price"]) / entry["prev_price"] * 100, 2
        ) if entry["prev_price"] > 0 else 0
        entry["maturity_date"] = m.get("maturity_date", 0)
        entry["total_coupon_paid"] = m.get("total_coupon_paid", 0)
        
        # Tính lãi suất thả nổi nếu có
        if b.get("floating"):
            ref_rate = _get_floating_ref_rate()
            spread = b.get("floating_spread", 0.01)
            entry["effective_rate"] = round(ref_rate + spread, 4)
            entry["display_rate"] = f"{ref_rate*100:.1f}% + {spread*100:.1f}%"
        else:
            entry["effective_rate"] = b["coupon_rate"]
            entry["display_rate"] = f"{b['coupon_rate']*100:.1f}%/năm"
        
        result.append(entry)
    return result


def _get_floating_ref_rate() -> float:
    """Lãi suất tham chiếu thả nổi (giả lập lãi suất liên ngân hàng VN)."""
    # Dao động từ 3.5% - 5.5%
    base = 0.045
    noise = random.uniform(-0.01, 0.01)
    return round(base + noise, 4)


def get_all_bonds_map() -> dict:
    """Trả về dict{bond_id: bond_data}."""
    result = {}
    for b in get_all_bonds():
        result[b["id"]] = b
    return result


def get_portfolio() -> list:
    """Trả về danh mục trái phiếu đang nắm giữ."""
    return _get_portfolio()


def _find_holding(bond_id: str) -> dict | None:
    """Tìm holding trong portfolio theo bond_id."""
    port = _get_portfolio()
    for h in port:
        if h["bond_id"] == bond_id and h.get("status") == "active":
            return h
    return None


def buy_bond(bond_id: str, quantity: int) -> dict:
    """Mua trái phiếu.
    
    Args:
        bond_id: mã trái phiếu
        quantity: số lượng (mỗi đơn vị = 1 mệnh giá)
    
    Returns:
        dict với kết quả giao dịch
    """
    _seed_market_if_empty()
    
    bond_def = _BONDS_MAP.get(bond_id)
    if not bond_def:
        return {"ok": False, "error": "Mã trái phiếu không tồn tại."}
    
    if quantity < bond_def.get("min_holding", 5):
        return {
            "ok": False,
            "error": f"Số lượng mua tối thiểu: {bond_def['min_holding']} đơn vị ({bond_def['min_holding']*bond_def['face_value']:,}đ mệnh giá).".replace(",", ".")
        }
    
    from .balance import get_balance, set_balance_and_log
    
    market = _get_market()
    m = market.get(bond_id, {})
    current_price = m.get("current_price", bond_def["base_price"])
    
    # Giá mua = mệnh giá * giá thị trường (%) / 100
    unit_price = int(bond_def["face_value"] * current_price / 100)
    total_cost = unit_price * quantity
    
    balance = get_balance()
    if balance < total_cost:
        shortage = total_cost - balance
        return {
            "ok": False,
            "error": f"Không đủ tiền! Cần thêm {shortage:,} VND.".replace(",", ".")
        }
    
    # Trừ tiền
    new_bal = balance - total_cost
    set_balance_and_log(new_bal, "purchase", -total_cost, f"Mua trái phiếu: {bond_def['name']} x{quantity}")
    
    # Thêm vào portfolio
    port = _get_portfolio()
    now = time.time()
    
    # Kiểm tra đã có holding active chưa
    existing = _find_holding(bond_id)
    if existing:
        # Gộp vào holding cũ (average price)
        old_qty = existing["quantity"]
        old_cost = existing["total_cost"]
        new_qty = old_qty + quantity
        new_cost = old_cost + total_cost
        existing["quantity"] = new_qty
        existing["total_cost"] = new_cost
        existing["avg_price"] = round(new_cost / new_qty)
        existing["last_trade"] = now
    else:
        # Tạo holding mới
        maturity_ts = m.get("maturity_date", now + bond_def["tenure_months"] * 30 * 86400)
        port.append({
            "bond_id": bond_id,
            "bond_name": bond_def["name"],
            "quantity": quantity,
            "avg_price": unit_price,
            "total_cost": total_cost,
            "face_value": bond_def["face_value"],
            "coupon_rate": bond_def["coupon_rate"],
            "tenure_months": bond_def["tenure_months"],
            "maturity_date": maturity_ts,
            "purchase_date": now,
            "last_coupon_time": now,
            "total_coupon_received": 0,
            "status": "active",
            "last_trade": now,
        })
    
    _set_portfolio(port)
    
    # Cập nhật market holders count
    m["holders"] = m.get("holders", 0) + 1
    _set_market(market)
    
    # Log giao dịch
    _add_txn("buy", bond_id, total_cost, f"Mua {quantity} đơn vị")
    
    from .transactions import add_transaction
    add_transaction("invest", total_cost, f"📜 Mua trái phiếu: {bond_def['name']} x{quantity}")
    
    return {
        "ok": True,
        "new_balance": new_bal,
        "quantity": quantity,
        "total_cost": total_cost,
        "unit_price": unit_price,
        "bond_name": bond_def["name"],
    }


def sell_bond(bond_id: str, quantity: int = None) -> dict:
    """Bán trái phiếu trên thị trường thứ cấp.
    
    Args:
        bond_id: mã trái phiếu
        quantity: số lượng muốn bán (None = bán tất cả)
    
    Returns:
        dict với kết quả giao dịch
    """
    bond_def = _BONDS_MAP.get(bond_id)
    if not bond_def:
        return {"ok": False, "error": "Mã trái phiếu không tồn tại."}
    
    port = _get_portfolio()
    holding = None
    for h in port:
        if h["bond_id"] == bond_id and h.get("status") == "active":
            holding = h
            break
    
    if not holding:
        return {"ok": False, "error": "Bạn không sở hữu trái phiếu này."}
    
    max_qty = holding["quantity"]
    sell_qty = quantity if quantity is not None else max_qty
    
    if sell_qty <= 0:
        return {"ok": False, "error": "Số lượng không hợp lệ."}
    if sell_qty > max_qty:
        return {"ok": False, "error": f"Bạn chỉ có {max_qty} đơn vị trái phiếu này."}
    
    from .balance import get_balance, set_balance_and_log
    
    market = _get_market()
    m = market.get(bond_id, {})
    current_price = m.get("current_price", bond_def["base_price"])
    
    # Tính accrued interest (lãi tích lũy) — người bán được hưởng lãi đến ngày bán
    now = time.time()
    last_coupon = holding.get("last_coupon_time", holding["purchase_date"])
    elapsed_months = (now - last_coupon) / (30 * 86400)
    coupon_rate = holding.get("coupon_rate", bond_def["coupon_rate"])
    face_value = holding.get("face_value", bond_def["face_value"])
    
    # Lãi tích lũy cho kỳ hiện tại
    coupon_freq_months = bond_def.get("coupon_freq_months", 6)
    if coupon_freq_months > 0 and elapsed_months > 0:
        # Lãi suất cho cả kỳ
        period_rate = coupon_rate * coupon_freq_months / 12
        # Lãi tích lũy = mệnh giá * lãi suất kỳ * (tháng đã qua / tháng của kỳ)
        accrued_per_unit = int(face_value * period_rate * (elapsed_months / coupon_freq_months))
    else:
        accrued_per_unit = 0
    
    # Giá bán = giá thị trường + lãi tích lũy
    sell_price_per_unit = int(face_value * current_price / 100) + accrued_per_unit
    total_proceeds = sell_price_per_unit * sell_qty
    
    # Cộng tiền
    balance = get_balance()
    new_bal = balance + total_proceeds
    set_balance_and_log(new_bal, "sell", total_proceeds, f"Bán trái phiếu: {bond_def['name']} x{sell_qty}")
    
    # Cập nhật holding
    remaining = max_qty - sell_qty
    if remaining <= 0:
        # Xóa holding
        port = [h for h in port if h.get("bond_id") != bond_id or h.get("status") != "active"]
    else:
        holding["quantity"] = remaining
        holding["total_cost"] = int(holding["total_cost"] * remaining / max_qty)
        holding["last_trade"] = now
        port = [h if h.get("bond_id") != bond_id or h.get("status") != "active" else holding for h in port]
    
    _set_portfolio(port)
    
    # Log
    _add_txn("sell", bond_id, total_proceeds, f"Bán {sell_qty} đơn vị, giá {current_price}%")
    
    from .transactions import add_transaction
    add_transaction("invest_income", total_proceeds, f"📜 Bán trái phiếu: {bond_def['name']} x{sell_qty}")
    
    pnl = total_proceeds - int(holding.get("avg_price", 0) * sell_qty) if remaining == 0 else 0
    
    return {
        "ok": True,
        "new_balance": new_bal,
        "quantity": sell_qty,
        "total_proceeds": total_proceeds,
        "unit_price": sell_price_per_unit,
        "accrued_interest": accrued_per_unit * sell_qty,
        "bond_name": bond_def["name"],
        "pnl": pnl,
    }


def process_coupon_payments() -> dict:
    """Xử lý thanh toán coupon cho tất cả trái phiếu đang nắm giữ.
    
    Mỗi lần gọi (khi đủ số thẻ review), tính coupon dồn tích
    từ lần trả coupon cuối cùng.
    
    Returns:
        dict với kết quả: {ok, total_coupon, payments: [{bond_id, amount, name}, ...]}
    """
    _seed_market_if_empty()
    
    # Kiểm tra số thẻ review
    review_count = _get_bonds_review_count()
    if review_count < REVIEWS_PER_UPDATE:
        return {
            "ok": False,
            "reason": "not_enough_reviews",
            "reviews_current": review_count,
            "reviews_needed": REVIEWS_PER_UPDATE,
        }
    
    # Reset review count
    _set_bonds_review_count(0)
    
    port = _get_portfolio()
    if not port:
        return {"ok": False, "reason": "no_bonds"}
    
    from .balance import get_balance, set_balance_and_log
    
    now = time.time()
    total_coupon = 0
    payments = []
    market = _get_market()
    coupon_log = _get_coupon_log()
    
    for holding in port:
        if holding.get("status") != "active":
            continue
        
        bid = holding["bond_id"]
        bond_def = _BONDS_MAP.get(bid)
        if not bond_def:
            continue
        
        face_value = holding.get("face_value", bond_def["face_value"])
        quantity = holding["quantity"]
        coupon_rate = holding.get("coupon_rate", bond_def["coupon_rate"])
        last_coupon = holding.get("last_coupon_time", holding["purchase_date"])
        coupon_freq = bond_def.get("coupon_freq_months", 6)
        
        # Tính số kỳ coupon đã trôi qua
        elapsed_days = (now - last_coupon) / 86400
        freq_days = coupon_freq * 30  # 30 ngày/tháng
        periods_elapsed = int(elapsed_days / freq_days)
        
        if periods_elapsed <= 0:
            continue
        
        # Tính coupon cho các kỳ đã qua
        # Lãi suất cho 1 kỳ: coupon_rate * (coupon_freq_months / 12)
        period_rate = coupon_rate * coupon_freq / 12
        
        # Trái phiếu lãi suất thả nổi — tính lại rate theo thị trường
        if bond_def.get("floating"):
            ref_rate = _get_floating_ref_rate()
            spread = bond_def.get("floating_spread", 0.01)
            period_rate = (ref_rate + spread) * coupon_freq / 12
        
        coupon_per_unit = int(face_value * period_rate)
        total_payment = coupon_per_unit * quantity * periods_elapsed
        
        if total_payment <= 0:
            continue
        
        # Cộng tiền
        balance = get_balance()
        set_balance_and_log(balance + total_payment, "coupon", total_payment,
                            f"📜 Coupon: {bond_def['name']} x{quantity} ({periods_elapsed} kỳ)")
        
        # Cập nhật holding
        holding["last_coupon_time"] = now
        holding["total_coupon_received"] = holding.get("total_coupon_received", 0) + total_payment
        
        # Cập nhật market
        m = market.get(bid, {})
        m["total_coupon_paid"] = m.get("total_coupon_paid", 0) + total_payment
        
        total_coupon += total_payment
        payments.append({
            "bond_id": bid,
            "bond_name": bond_def["name"],
            "emoji": bond_def.get("emoji", "📜"),
            "amount": total_payment,
            "periods": periods_elapsed,
            "quantity": quantity,
        })
        
        # Log coupon
        coupon_log.append({
            "ts": now,
            "bond_id": bid,
            "bond_name": bond_def["name"],
            "amount": total_payment,
            "periods": periods_elapsed,
            "quantity": quantity,
        })
    
    if total_coupon > 0:
        _set_portfolio(port)
        _set_market(market)
        _set_coupon_log(coupon_log)
        
        # Transaction log
        from .transactions import add_transaction
        add_transaction("coupon", total_coupon, f"📜 Coupon trái phiếu: +{total_coupon:,}đ".replace(",", "."))
    
    return {
        "ok": True,
        "total_coupon": total_coupon,
        "payments": payments,
        "num_bonds": len(payments),
    }


def check_maturity() -> dict:
    """Kiểm tra và xử lý trái phiếu đến hạn.
    
    Returns:
        dict với kết quả: {processed: int, details: [{bond_id, name, proceeds}], total_proceeds: int}
    """
    port = _get_portfolio()
    if not port:
        return {"processed": 0, "details": [], "total_proceeds": 0}
    
    from .balance import get_balance, set_balance_and_log
    
    now = time.time()
    matured = []
    remaining = []
    total_proceeds = 0
    
    for holding in port:
        if holding.get("status") != "active":
            continue
        
        maturity_date = holding.get("maturity_date", 0)
        if maturity_date <= 0 or now < maturity_date:
            remaining.append(holding)
            continue
        
        # Trái phiếu đáo hạn
        bid = holding["bond_id"]
        bond_def = _BONDS_MAP.get(bid, {})
        face_value = holding.get("face_value", bond_def.get("face_value", 1_000_000))
        quantity = holding["quantity"]
        
        # Hoàn trả mệnh giá
        proceeds = face_value * quantity
        
        # Cộng tiền
        balance = get_balance()
        set_balance_and_log(balance + proceeds, "maturity", proceeds,
                            f"📜 Đáo hạn trái phiếu: {holding.get('bond_name', bid)} x{quantity}")
        
        total_proceeds += proceeds
        matured.append({
            "bond_id": bid,
            "bond_name": holding.get("bond_name", bid),
            "quantity": quantity,
            "proceeds": proceeds,
            "total_coupon_received": holding.get("total_coupon_received", 0),
        })
        
        _add_txn("maturity", bid, proceeds, f"Đáo hạn {quantity} đơn vị, nhận {proceeds:,}đ".replace(",", "."))
    
    if matured:
        _set_portfolio(remaining)
        
        from .transactions import add_transaction
        add_transaction("maturity", total_proceeds,
                        f"📜 Đáo hạn {len(matured)} trái phiếu: +{total_proceeds:,}đ".replace(",", "."))
    
    return {
        "processed": len(matured),
        "details": matured,
        "total_proceeds": total_proceeds,
    }


def convert_convertible_bond(bond_id: str, quantity: int = None) -> dict:
    """Chuyển đổi trái phiếu chuyển đổi thành cổ phiếu.
    
    Args:
        bond_id: mã trái phiếu chuyển đổi
        quantity: số lượng muốn chuyển (None = tất cả)
    
    Returns:
        dict với kết quả
    """
    bond_def = _BONDS_MAP.get(bond_id)
    if not bond_def:
        return {"ok": False, "error": "Mã trái phiếu không tồn tại."}
    if not bond_def.get("convertible"):
        return {"ok": False, "error": "Trái phiếu này không có tính năng chuyển đổi."}
    
    port = _get_portfolio()
    holding = _find_holding(bond_id)
    if not holding:
        return {"ok": False, "error": "Bạn không sở hữu trái phiếu này."}
    
    max_qty = holding["quantity"]
    conv_qty = quantity if quantity is not None else max_qty
    
    if conv_qty <= 0 or conv_qty > max_qty:
        return {"ok": False, "error": "Số lượng không hợp lệ."}
    
    conversion_ratio = bond_def.get("conversion_ratio", 0.5)
    shares_received = int(conv_qty * conversion_ratio)
    
    if shares_received <= 0:
        return {"ok": False, "error": "Số cổ phiếu nhận được quá nhỏ."}
    
    # Chuyển đổi: bán trái phiếu ở mệnh giá và mua cổ phiếu tương ứng
    # Mô phỏng: thêm shares_received cổ phiếu vào portfolio chứng khoán
    # (trong thực tế, cần có cơ chế thêm cổ phiếu từ stock_market)
    
    from .balance import get_balance, set_balance_and_log
    face_value = holding.get("face_value", bond_def["face_value"])
    proceeds = face_value * conv_qty  # Hoàn trả mệnh giá
    
    balance = get_balance()
    new_bal = balance + proceeds
    set_balance_and_log(new_bal, "convert", proceeds,
                        f"🔄 Chuyển đổi trái phiếu: {bond_def['name']} -> {shares_received} CP")
    
    # Ghi log giao dịch
    _add_txn("convert", bond_id, proceeds,
             f"Chuyển đổi {conv_qty} đơn vị -> {shares_received} CP")
    from .transactions import add_transaction
    add_transaction("invest_income", proceeds,
                    f"🔄 Chuyển đổi trái phiếu: {bond_def['name']} -> {shares_received} CP")
    
    # Xóa holding hoặc giảm quantity
    remaining = max_qty - conv_qty
    if remaining <= 0:
        port = [h for h in port if h.get("bond_id") != bond_id or h.get("status") != "active"]
    else:
        holding["quantity"] = remaining
        holding["total_cost"] = int(holding["total_cost"] * remaining / max_qty)
        port = [h if h.get("bond_id") != bond_id or h.get("status") != "active" else holding for h in port]
    
    _set_portfolio(port)
    
    # Ghi nhận cổ phiếu vào stock portfolio
    try:
        from .stock_market import _add_shares_directly
        # Map bond id to a stock symbol
        stock_symbols = {
            "bond_conv_fpt": "FPT",
            "bond_conv_vic": "VIC",
        }
        symbol = stock_symbols.get(bond_id)
        if symbol:
            _add_shares_directly(symbol, shares_received, proceeds)
    except Exception as e:
        logger.warning("convert_bond: _add_shares_directly — %s", e)
    
    _add_txn("convert", bond_id, proceeds, f"Chuyển đổi {conv_qty} đơn vị -> {shares_received} CP")
    
    return {
        "ok": True,
        "bond_name": bond_def["name"],
        "quantity_converted": conv_qty,
        "shares_received": shares_received,
        "proceeds": proceeds,
        "new_balance": new_bal,
    }


def get_portfolio_summary() -> dict:
    """Tổng quan danh mục trái phiếu."""
    port = _get_portfolio()
    active = [h for h in port if h.get("status") == "active"]
    
    if not active:
        return {"total_value": 0, "total_cost": 0, "total_coupon_received": 0, "count": 0, "holdings": []}
    
    market = _get_market()
    total_value = 0
    total_cost = 0
    total_coupon = 0
    details = []
    
    for h in active:
        bid = h["bond_id"]
        bond_def = _BONDS_MAP.get(bid, {})
        m = market.get(bid, {})
        current_price = m.get("current_price", bond_def.get("base_price", 100))
        face_value = h.get("face_value", bond_def.get("face_value", 1_000_000))
        qty = h["quantity"]
        
        unit_val = int(face_value * current_price / 100)
        value = unit_val * qty
        cost = h.get("total_cost", 0)
        coupon_rcvd = h.get("total_coupon_received", 0)
        
        total_value += value
        total_cost += cost
        total_coupon += coupon_rcvd
        
        # P&L
        pl = value + coupon_rcvd - cost
        pl_pct = round(pl / cost * 100, 2) if cost > 0 else 0
        
        # Thời gian đến hạn
        maturity = h.get("maturity_date", 0)
        now = time.time()
        days_to_maturity = max(0, int((maturity - now) / 86400)) if maturity > 0 else 0
        
        details.append({
            "bond_id": bid,
            "bond_name": h.get("bond_name", bid),
            "type": bond_def.get("type", ""),
            "emoji": bond_def.get("emoji", "📜"),
            "quantity": qty,
            "face_value": face_value,
            "current_price": current_price,
            "unit_value": unit_val,
            "total_value": value,
            "total_cost": cost,
            "coupon_received": coupon_rcvd,
            "pnl": pl,
            "pnl_pct": pl_pct,
            "coupon_rate": h.get("coupon_rate", bond_def.get("coupon_rate", 0)),
            "days_to_maturity": days_to_maturity,
            "convertible": bond_def.get("convertible", False),
        })
    
    return {
        "total_value": total_value,
        "total_cost": total_cost,
        "total_coupon_received": total_coupon,
        "total_pnl": total_value + total_coupon - total_cost,
        "count": len(active),
        "holdings": details,
    }


def get_coupon_log(limit: int = 20) -> list:
    """Lấy lịch sử coupon gần nhất."""
    log = _get_coupon_log()
    return log[-limit:]


def get_transaction_history(limit: int = 30) -> list:
    """Lấy lịch sử giao dịch trái phiếu."""
    txns = _get_txns()
    return txns[-limit:]


def get_market_summary() -> dict:
    """Tổng quan thị trường trái phiếu."""
    _seed_market_if_empty()
    bonds = get_all_bonds()
    market = _get_market()
    
    # Phân loại theo type
    by_type: dict = {}
    for b in bonds:
        btype = b.get("type", "Khác")
        if btype not in by_type:
            by_type[btype] = []
        by_type[btype].append(b)
    
    # Coupon pending
    review_count = _get_bonds_review_count()
    reviews_needed = max(0, REVIEWS_PER_UPDATE - review_count)
    
    return {
        "total_bonds": len(bonds),
        "bonds_by_type": {k: len(v) for k, v in by_type.items()},
        "total_holders": sum(m.get("holders", 0) for m in market.values()),
        "reviews_current": review_count,
        "reviews_needed": reviews_needed,
        "reviews_ready": review_count >= REVIEWS_PER_UPDATE,
    }


def update_prices_if_needed():
    """Gọi từ __init__.py khi mở app."""
    _seed_market_if_empty()
    _update_bond_prices_if_needed()
    check_maturity()


def get_all_bond_data() -> dict:
    """Trả về tất cả dữ liệu trái phiếu cho UI (1 lần gọi)."""
    _seed_market_if_empty()
    _update_bond_prices_if_needed()
    
    bonds = get_all_bonds()
    portfolio = get_portfolio_summary()
    coupon_log = get_coupon_log(10)
    txns = get_transaction_history(10)
    summary = get_market_summary()
    
    return {
        "ok": True,
        "bonds": bonds,
        "portfolio": portfolio,
        "coupon_log": coupon_log,
        "transactions": txns,
        "summary": summary,
    }


# ═══════════════════════════════════════════════════════════════
#  ADD SHARES DIRECTLY (stock_market bridge)
# ═══════════════════════════════════════════════════════════════

def _add_shares_directly(symbol: str, shares: int, cost_basis: int):
    """Add shares to stock portfolio (called from convert_convertible_bond).
    
    This function tries to access stock_market internals.
    If stock_market doesn't have _add_shares_directly, we just add cash.
    """
    # This is a fallback — if stock_market has the function, it will be used
    # Otherwise, the convertible bond conversion just returns cash
    pass
