# -*- coding: utf-8 -*-
"""
emergency_events.py — Sự kiện khủng hoảng tài chính ngẫu nhiên.

Kích hoạt mỗi khi mở Anki (xác suất 25%/ngày, tối đa 1 sự kiện/ngày).
Chi phí tỷ lệ với giá trị tài sản liên quan — xe sang sửa đắt, BĐS lớn bảo trì nhiều hơn.
Bảo hiểm trong inventory giảm đáng kể số tiền phải trả.

Items có thể ảnh hưởng đến emergency events:
  - emergency_resistance: giảm xác suất (0.0-0.9)
  - emergency_magnetism:  tăng xác suất (0.0-0.9) — item "xui xẻo" hoặc "rủi ro"
  - emergency_cost_reduction: giảm chi phí khi event xảy ra (0.0-0.9)
  - emergency_cost_increase:  tăng chi phí khi event xảy ra (0.0-0.9)
"""

import random
import time
from ._safe_config import col_ready, cfg_dict, cfg_list, cfg_str, cfg_set

_KEY_LAST_DATE = "anki_tycoon_emergency_last_date"
_KEY_LOG       = "anki_tycoon_emergency_log"

# Keys được bảo vệ khỏi debug_tools
PROTECTED_KEYS = {_KEY_LAST_DATE, _KEY_LOG}

BASE_TRIGGER_PROB = 0.25   # 25% xác suất/ngày (tăng từ 15%)

# Các loại bảo hiểm và mức giảm thiệt hại
_INSURANCE = {
    "health":       {"item_id": "ins_health",       "reduction": 0.70},  # trả 30%
    "car":          {"item_id": "ins_car",           "reduction": 0.65},  # trả 35%
    "property":     {"item_id": "ins_property",      "reduction": 0.60},  # trả 40%
    "motorbike":    {"item_id": "ins_motorbike",     "reduction": 0.55},  # trả 45%
    "accident":     {"item_id": "ins_accident",      "reduction": 0.60},  # tai nạn cá nhân, trả 40%
    "travel":       {"item_id": "ins_travel",        "reduction": 0.65},  # du lịch, trả 35%
    "unemployment": {"item_id": "ins_unemployment",  "reduction": 0.40},  # mất việc, trả 60%
    # ins_life: toàn diện, bao phủ mọi loại, reduction 45%
}
_LIFE_INSURANCE_ID  = "ins_life"
_LIFE_INSURANCE_RED = 0.45

# Các loại sự kiện bổ sung được bảo hiểm chéo
# Ví dụ: ins_accident cũng giảm chi phí y tế (vì tai nạn → viện phí)
_CROSS_COVERAGE: dict[str, list[str]] = {
    "health":   ["ins_accident"],   # tai nạn bao gồm y tế
    "motorbike": ["ins_car"],       # ins_car cũng bảo vệ xe máy (và ngược lại)
    "car":      ["ins_motorbike"],  # ins_motorbike cũng cho phép giảm nhẹ xe hơi
}

# ── Pool sự kiện ─────────────────────────────────────────────────

EVENT_POOL = [

    # ════════════════════════════════════════════════════════════
    # XE HƠI — chỉ áp dụng nếu có xe trong inventory
    # cost_type = "car_pct"  → low/high % × giá xe, có cost_cap
    # cost_type = "car_tier" → cố định theo tier giá xe
    # ════════════════════════════════════════════════════════════
    {
        "id":  "car_maintenance",
        "category": "car",
        "title": "Bảo dưỡng định kỳ",
        "emoji": "🔧",
        "desc": "Xe đến kỳ bảo dưỡng — thay dầu động cơ, lọc gió, kiểm tra phanh và hệ thống điện.",
        "cost_type": "car_pct",
        "cost_low_pct": 0.003,
        "cost_high_pct": 0.007,
        "cost_cap": 40_000_000,
        "insurance_type": "car",
        "weight": 4,
        "lesson": (
            "Chi phí bảo dưỡng thường 0.3–0.7% giá xe/năm. "
            "Toyota Altis: 2–5M/lần. Mercedes C300: 8–20M/lần. Ferrari: 30–60M/lần tại đại lý. "
            "Đây là 'chi phí ẩn' ít người tính khi mua xe đắt tiền."
        ),
    },
    {
        "id":  "car_tire",
        "category": "car",
        "title": "Thay lốp xe",
        "emoji": "🛞",
        "desc": "Lốp xe bị đinh xuyên hoặc mòn quá mức — cần thay mới để đảm bảo an toàn.",
        "cost_type": "car_pct",
        "cost_low_pct": 0.001,
        "cost_high_pct": 0.003,
        "cost_cap": 20_000_000,
        "insurance_type": "car",
        "weight": 4,
        "lesson": (
            "Lốp cần thay sau 40,000–60,000km hoặc 4–5 năm. "
            "Xe phổ thông: 1–3M/bộ 4 lốp. Siêu xe Ferrari/Lambo dùng lốp Pirelli P-Zero đặc chủng "
            "10–50M/chiếc — gấp 20 lần lốp phổ thông. Đây là chi phí vận hành thực của xe sang."
        ),
    },
    {
        "id":  "car_scratch",
        "category": "car",
        "title": "Va chạm nhỏ, xước sơn",
        "emoji": "💥",
        "desc": "Xe bị xước sơn hoặc móp nhẹ khi đỗ ở bãi — cần ra xưởng sơn phủ lại đúng màu.",
        "cost_type": "car_pct",
        "cost_low_pct": 0.005,
        "cost_high_pct": 0.018,
        "cost_cap": 100_000_000,
        "insurance_type": "car",
        "weight": 3,
        "lesson": (
            "Sơn lại xe sang phải đúng mã màu và quy trình kiểm soát chất lượng đặc biệt. "
            "Mercedes C300: 10–40M. Porsche Cayenne: 30–80M. Rolls-Royce: 100–300M. "
            "Bảo hiểm thân vỏ toàn diện là cần thiết khi sở hữu xe giá cao."
        ),
    },
    {
        "id":  "car_accident",
        "category": "car",
        "title": "Tai nạn giao thông",
        "emoji": "🚨",
        "desc": "Va chạm mạnh trên đường — hư hỏng nặng đầu xe, phải gửi xưởng sửa lớn.",
        "cost_type": "car_pct",
        "cost_low_pct": 0.012,
        "cost_high_pct": 0.045,
        "cost_cap": 300_000_000,
        "insurance_type": "car",
        "weight": 1,
        "lesson": (
            "Bảo hiểm thân vỏ toàn diện (bao gồm lỗi của mình) khác với bảo hiểm TNDS bắt buộc "
            "(chỉ bồi thường người khác, không bao gồm xe của bạn). "
            "Xe 2 tỷ không mua thân vỏ = rủi ro mất 60–90M nếu tai nạn — không thể bỏ qua."
        ),
    },
    {
        "id":  "car_inspection",
        "category": "car",
        "title": "Đăng kiểm + Phí đường bộ",
        "emoji": "📋",
        "desc": "Đến kỳ đăng kiểm định kỳ và gia hạn phí sử dụng đường bộ năm nay.",
        "cost_type": "car_tier",
        "cost_tiers": [
            (800_000_000,   2_000_000),
            (2_000_000_000, 4_000_000),
            (6_000_000_000, 7_000_000),
            (float("inf"),  12_000_000),
        ],
        "insurance_type": None,
        "weight": 3,
        "lesson": (
            "Phí đường bộ tại VN tính theo dung tích xi-lanh và loại xe. "
            "Phí đăng kiểm 2 lần/năm. Xe sang (>2 tỷ) đóng tổng 5–15M/năm chỉ riêng phí hành chính, "
            "chưa kể xăng dầu, bảo hiểm và bảo dưỡng — TCO (Total Cost of Ownership) rất cao."
        ),
    },
    {
        "id":  "car_traffic_fine",
        "category": "car",
        "title": "Phạt nguội giao thông",
        "emoji": "🚔",
        "desc": "Camera phát hiện vượt đèn đỏ hoặc quá tốc độ — nhận thông báo phạt về địa chỉ.",
        "cost_type": "car_tier",
        "cost_tiers": [
            (800_000_000,   2_000_000),
            (3_000_000_000, 4_000_000),
            (float("inf"),  8_000_000),
        ],
        "insurance_type": None,
        "weight": 3,
        "lesson": (
            "Nghị định 168/2024 (hiệu lực 1/2025) tăng phạt mạnh: "
            "vượt đèn đỏ ô tô 3–5M, quá tốc độ trên 35km/h: 10–18M + tước GPLX. "
            "Camera phạt nguội đang phủ dày tại các thành phố lớn. Biết luật, chấp hành để tránh mất tiền oan."
        ),
    },
    {
        "id":  "car_theft_parts",
        "category": "car",
        "title": "Bị trộm phụ tùng xe",
        "emoji": "🔩",
        "desc": "Kẻ gian tháo trộm gương chiếu hậu, logo hoặc phụ kiện xe qua đêm.",
        "cost_type": "car_pct",
        "cost_low_pct": 0.002,
        "cost_high_pct": 0.008,
        "cost_cap": 30_000_000,
        "insurance_type": "car",
        "weight": 2,
        "lesson": (
            "Gương chiếu hậu xe sang 2–8M, logo xe BMW/Mercedes 1–3M, "
            "vô lăng cao cấp 10–30M. Bảo hiểm thân vỏ bao gồm mất trộm phụ tùng — "
            "đây là lý do bảo hiểm không chỉ cho tai nạn mà còn cho trộm cắp."
        ),
    },

    # ════════════════════════════════════════════════════════════
    # XE MÁY — chỉ áp dụng nếu có xe máy trong inventory
    # (category "🚲 Bicycle" hoặc "🏍️ Xe máy")
    # cost_type = "bike_pct" → % × giá xe, có cost_cap
    # ════════════════════════════════════════════════════════════
    {
        "id":  "motorbike_puncture",
        "category": "motorbike",
        "title": "Xe máy thủng lốp, thay xăm",
        "emoji": "🛵",
        "desc": "Đi làm giữa đường bị đinh đâm thủng lốp — phải dắt bộ vào tiệm vá hoặc thay lốp mới.",
        "cost_type": "bike_pct",
        "cost_low_pct": 0.002,
        "cost_high_pct": 0.008,
        "cost_cap": 3_000_000,
        "insurance_type": "motorbike",
        "weight": 5,
        "lesson": (
            "Xe máy tại VN là phương tiện chính của đa số. Thay lốp xe số: 150\u2013300K, "
            "xe tay ga: 300\u2013800K/l\u1ed1p. V\u00e1 l\u1ed1p: 30\u201350K. "
            "B\u1ea3o hi\u1ec3m xe m\u00e1y t\u1ef1 nguy\u1ec7n (VNI, PVI) b\u1ed3i th\u01b0\u1eddng thi\u1ec7t h\u1ea1i v\u1eadt ch\u1ea5t "
            "khi va qu\u1eb9t, \u0111\u00e2m \u0111\u1ed5 \u2014 kh\u00e1c v\u1edbi b\u1ea3o hi\u1ec3m TNDS b\u1eaft bu\u1ed9c (66K/n\u0103m)."
        ),
    },
    {
        "id":  "motorbike_maintenance",
        "category": "motorbike",
        "title": "B\u1ea3o d\u01b0\u1ee1ng \u0111\u1ecbnh k\u1ef3 xe m\u00e1y",
        "emoji": "\U0001f527",
        "desc": "Xe t\u1edbi s\u1ed1 km c\u1ea7n thay nh\u1edbt, v\u1ec7 sinh b\u1ed9 ch\u1ebf h\u00f2a kh\u00ed, thay l\u1ecdc gi\u00f3 v\u00e0 bugi.",
        "cost_type": "bike_pct",
        "cost_low_pct": 0.001,
        "cost_high_pct": 0.005,
        "cost_cap": 2_000_000,
        "insurance_type": "motorbike",
        "weight": 5,
        "lesson": (
            "B\u1ea3o d\u01b0\u1ee1ng xe m\u00e1y \u0111\u1ecbnh k\u1ef3: thay nh\u1edbt 1.000km/l\u1ea7n (50\u2013250K), "
            "v\u1ec7 sinh kim phun 10.000km (300\u2013500K), thay l\u1ed1p 20.000km. "
            "Xe tay ga nh\u01b0 Honda SH, Vespa chi ph\u00ed b\u1ea3o d\u01b0\u1ee1ng cao g\u1ea5p 2\u20133 l\u1ea7n xe s\u1ed1. "
            "Chi ph\u00ed v\u1eadn h\u00e0nh l\u00e0 y\u1ebfu t\u1ed1 c\u1ea7n t\u00ednh khi mua xe \u2014 SH 150i ph\u00ed b\u1ea3o d\u01b0\u1ee1ng 2\u20134M/n\u0103m."
        ),
    },
    {
        "id":  "motorbike_scratch",
        "category": "motorbike",
        "title": "Xe m\u00e1y b\u1ecb x\u01b0\u1edbc, m\u00f3p d\u1ef1ng xe",
        "emoji": "\U0001f4a5",
        "desc": "\u0110\u1ed7 xe \u1edf v\u1ec9a h\u00e8, xe kh\u00e1c va qu\u1eb9t l\u00e0m x\u01b0\u1edbc y\u1ebfm ho\u1eb7c g\u00e3y g\u01b0\u01a1ng \u2014 ph\u1ea3i s\u01a1n l\u1ea1i.",
        "cost_type": "bike_pct",
        "cost_low_pct": 0.003,
        "cost_high_pct": 0.012,
        "cost_cap": 5_000_000,
        "insurance_type": "motorbike",
        "weight": 4,
        "lesson": (
            "Xe m\u00e1y tay ga cao c\u1ea5p (SH, Vespa, NVX): s\u01a1n l\u1ea1i y\u1ebfm 500K\u20132M, "
            "g\u01b0\u01a1ng 200\u2013500K/c\u00e1i. Ph\u00e2n kh\u1ed1i l\u1edbn (400cc+): \u0111\u1ed3 nh\u1eadp kh\u1ea9u, chi ph\u00ed g\u1ea5p 3\u20135 l\u1ea7n. "
            "B\u1ea3o hi\u1ec3m v\u1eadt ch\u1ea5t xe m\u00e1y: 0.5\u20131.5% gi\u00e1 tr\u1ecb xe/n\u0103m \u2014 "
            "r\u1ebb h\u01a1n nhi\u1ec1u so v\u1edbi c\u00e1c kho\u1ea3n s\u1eeda ch\u1eefa ri\u00eang l\u1ebb."
        ),
    },
    {
        "id":  "motorbike_accident",
        "category": "motorbike",
        "title": "Tai n\u1ea1n xe m\u00e1y",
        "emoji": "\U0001f6a8",
        "desc": "Tr\u01b0\u1ee3t ng\u00e3 tr\u00ean \u0111\u01b0\u1eddng \u01b0\u1edbt \u2014 xe h\u01b0 h\u1ecfng n\u1eb7ng, ph\u1ea3i thay nhi\u1ec1u ph\u1ee5 t\u00f9ng v\u00e0 s\u01a1n l\u1ea1i.",
        "cost_type": "bike_pct",
        "cost_low_pct": 0.008,
        "cost_high_pct": 0.030,
        "cost_cap": 15_000_000,
        "insurance_type": "motorbike",
        "weight": 2,
        "lesson": (
            "Tai n\u1ea1n xe m\u00e1y chi\u1ebfm 70% s\u1ed1 v\u1ee5 TNGT t\u1ea1i VN. "
            "B\u1ea3o hi\u1ec3m xe m\u00e1y t\u1ef1 nguy\u1ec7n b\u1ed3i th\u01b0\u1eddng thi\u1ec7t h\u1ea1i v\u1eadt ch\u1ea5t (s\u1eeda xe, thay ph\u1ee5 t\u00f9ng) "
            "r\u1ea5t c\u1ea7n thi\u1ebft cho xe tay ga cao c\u1ea5p v\u00e0 ph\u00e2n kh\u1ed1i l\u1edbn. "
            "Ph\u00ed b\u1ea3o hi\u1ec3m: 1\u20133% gi\u00e1 tr\u1ecb xe/n\u0103m \u2014 r\u1ebb h\u01a1n nhi\u1ec1u so v\u1edbi 1 l\u1ea7n s\u1eeda xe sau tai n\u1ea1n."
        ),
    },
    {
        "id":  "motorbike_theft_parts",
        "category": "motorbike",
        "title": "M\u1ea5t ph\u1ee5 t\u00f9ng xe m\u00e1y",
        "emoji": "\U0001f529",
        "desc": "K\u1ebb gian th\u00e1o tr\u1ed9m g\u01b0\u01a1ng, y\u1ebfm, ho\u1eb7c baga xe m\u00e1y khi \u0111\u1ed7 qua \u0111\u00eam.",
        "cost_type": "bike_pct",
        "cost_low_pct": 0.002,
        "cost_high_pct": 0.010,
        "cost_cap": 4_000_000,
        "insurance_type": "motorbike",
        "weight": 3,
        "lesson": (
            "M\u1ea5t ph\u1ee5 t\u00f9ng xe m\u00e1y r\u1ea5t ph\u1ed5 bi\u1ebfn: g\u01b0\u01a1ng 100\u2013500K/c\u00e1i, baga 200\u2013800K, "
            "y\u1ebfm SH 1\u20133M. Xe ph\u00e2n kh\u1ed1i l\u1edbn: b\u1ed9 m\u00e2m \u0111\u00fac 5\u201320M/b\u1ed9. "
            "B\u1ea3o hi\u1ec3m v\u1eadt ch\u1ea5t xe m\u00e1y bao g\u1ed3m m\u1ea5t ph\u1ee5 t\u00f9ng \u2014 "
            "\u0111\u1eb7c bi\u1ec7t h\u1eefu \u00edch cho d\u00f2ng xe nh\u1eadp kh\u1ea9u, ph\u1ee5 t\u00f9ng kh\u00f3 thay th\u1ebf."
        ),
    },

    # ════════════════════════════════════════════════════════════
    # Y TẾ — luôn áp dụng
    # cost_type = "fixed"  → random trong [cost_low, cost_high]
    # ════════════════════════════════════════════════════════════
    {
        "id":  "health_checkup",
        "category": "health",
        "title": "Khám sức khỏe định kỳ",
        "emoji": "🏥",
        "desc": "Tới lịch khám tổng quát — xét nghiệm máu, siêu âm bụng, điện tim, đo huyết áp.",
        "cost_type": "fixed",
        "cost_low": 800_000,
        "cost_high": 3_500_000,
        "insurance_type": "health",
        "weight": 4,
        "lesson": (
            "Khám tổng quát 1–3.5M/lần là khoản đầu tư bảo vệ tài sản quan trọng nhất — bản thân bạn. "
            "Phát hiện ung thư giai đoạn đầu tiết kiệm 200–800M chi phí điều trị sau này. "
            "Người có bảo hiểm sức khỏe thường đi khám sớm hơn, kết quả điều trị tốt hơn."
        ),
    },
    {
        "id":  "health_flu",
        "category": "health",
        "title": "Bị cúm, sốt siêu vi",
        "emoji": "🤒",
        "desc": "Sốt cao, đau đầu, ho nhiều ngày — phải vào phòng khám, mua thuốc và nghỉ làm.",
        "cost_type": "fixed",
        "cost_low": 300_000,
        "cost_high": 2_500_000,
        "insurance_type": "health",
        "weight": 5,
        "lesson": (
            "Cúm mùa tại VN tốn 300K–2.5M/lần (khám + thuốc + test). "
            "Vaccine cúm hàng năm 250–500K có thể ngăn ngừa hoàn toàn và bảo vệ cả gia đình. "
            "Chi phí nhỏ để phòng bệnh hơn rất nhiều so với chi phí chữa bệnh — nguyên tắc tài chính y tế cơ bản."
        ),
    },
    {
        "id":  "health_dental",
        "category": "health",
        "title": "Chi phí nha khoa",
        "emoji": "🦷",
        "desc": "Phát hiện sâu răng hoặc cần làm cầu sứ — nha khoa KHÔNG nằm trong BHYT cơ bản.",
        "cost_type": "fixed",
        "cost_low": 2_000_000,
        "cost_high": 30_000_000,
        "insurance_type": "health",
        "weight": 3,
        "lesson": (
            "Nha khoa tại VN KHÔNG được BHYT nhà nước chi trả. "
            "Bọc răng sứ: 3–10M/cái. Implant: 20–50M/cái. Niềng răng: 30–120M. "
            "Bảo hiểm sức khỏe tư nhân cao cấp (3–10M/năm) mới bao gồm nha khoa — "
            "một trong những lý do quan trọng nhất để mua bảo hiểm sức khỏe."
        ),
    },
    {
        "id":  "health_hospitalization",
        "category": "health",
        "title": "Nhập viện điều trị",
        "emoji": "🚑",
        "desc": "Bệnh tiến triển nặng hơn dự kiến — bác sĩ yêu cầu nhập viện theo dõi 3–7 ngày.",
        "cost_type": "fixed",
        "cost_low": 8_000_000,
        "cost_high": 70_000_000,
        "insurance_type": "health",
        "weight": 2,
        "lesson": (
            "Nhập viện bệnh viện tư (Vinmec, FV, Hạnh Phúc): 3–5 ngày tốn 30–150M. "
            "Bệnh viện công có BHYT: 2–10M nhưng phải chờ lâu và chia sẻ phòng. "
            "Bảo hiểm sức khỏe thanh toán 80–100% chi phí nội trú — "
            "giúp được điều trị tại bệnh viện tốt nhất mà không lo chi phí."
        ),
    },
    {
        "id":  "health_emergency",
        "category": "health",
        "title": "Cấp cứu khẩn cấp",
        "emoji": "🚨",
        "desc": "Tai nạn bất ngờ hoặc cơn đau cấp tính — xe cứu thương, phẫu thuật, ICU.",
        "cost_type": "fixed",
        "cost_low": 20_000_000,
        "cost_high": 150_000_000,
        "insurance_type": "health",
        "weight": 1,
        "lesson": (
            "Cấp cứu không báo trước là nguyên nhân chính làm kiệt sức tài chính nhiều gia đình VN. "
            "ICU tại bệnh viện tư: 5–15M/ngày. Phẫu thuật tim: 100–500M. "
            "Quỹ khẩn cấp 3–6 tháng chi phí + bảo hiểm sức khỏe là hai lá chắn không thể thiếu."
        ),
    },
    {
        "id":  "health_chronic",
        "category": "health",
        "title": "Phát hiện bệnh mãn tính",
        "emoji": "💊",
        "desc": "Kết quả xét nghiệm cho thấy có bệnh tiểu đường hoặc huyết áp cao — cần điều trị dài hạn.",
        "cost_type": "fixed",
        "cost_low": 1_500_000,
        "cost_high": 6_000_000,
        "insurance_type": "health",
        "weight": 2,
        "lesson": (
            "Bệnh mãn tính như tiểu đường tốn 2–8M/tháng cho thuốc + tái khám + xét nghiệm định kỳ — "
            "dài hạn là gánh nặng rất lớn. "
            "Bảo hiểm sức khỏe nên mua sớm khi còn khỏe mạnh: sau khi có bệnh nền, "
            "nhiều công ty bảo hiểm từ chối nhận hoặc loại trừ bệnh sẵn có."
        ),
    },
    {
        "id":  "health_mental",
        "category": "health",
        "title": "Burnout, cần nghỉ ngơi tâm lý",
        "emoji": "🧠",
        "desc": "Căng thẳng kéo dài gây burnout — bác sĩ khuyên nghỉ ngơi, trị liệu tâm lý.",
        "cost_type": "fixed",
        "cost_low": 500_000,
        "cost_high": 5_000_000,
        "insurance_type": "health",
        "weight": 2,
        "lesson": (
            "Trị liệu tâm lý tại VN: 300K–1.5M/buổi (1h), thường cần 8–20 buổi. "
            "BHYT không chi trả hầu hết trị liệu tâm lý. "
            "Sức khỏe tinh thần là một phần quan trọng của 'đầu tư vào bản thân' — "
            "người làm việc hiệu quả và ổn định tâm lý thường có thu nhập cao hơn dài hạn."
        ),
    },

    # ════════════════════════════════════════════════════════════
    # TAI NẠN CÁ NHÂN — luôn áp dụng
    # cost_type = "fixed"  → random trong [cost_low, cost_high]
    # ════════════════════════════════════════════════════════════
    {
        "id":  "accident_slip_fall",
        "category": "accident",
        "title": "Trượt ngã, chấn thương",
        "emoji": "🩼",
        "desc": "Trượt chân ngã cầu thang hoặc té xe — bong gân hoặc nứt xương, cần bó bột và nghỉ ngơi.",
        "cost_type": "fixed",
        "cost_low": 1_500_000,
        "cost_high": 12_000_000,
        "insurance_type": "accident",
        "weight": 4,
        "lesson": (
            "Tai nạn sinh hoạt là loại tai nạn phổ biến nhất: trượt ngã, té xe, bỏng bếp. "
            "Bảo hiểm tai nạn cá nhân chi trả viện phí, phẫu thuật và bồi thường thương tật. "
            "Phí bảo hiểm tai nạn: 200\u2013500K/n\u0103m cho mức b\u1ed3i th\u01b0\u1eddng 20\u201350M \u2014 "
            "r\u1ebb nh\u1ea5t trong c\u00e1c lo\u1ea1i b\u1ea3o hi\u1ec3m nh\u01b0ng r\u1ea5t c\u1ea7n thi\u1ebft."
        ),
    },
    {
        "id":  "accident_sports",
        "category": "accident",
        "title": "Ch\u1ea5n th\u01b0\u01a1ng th\u1ec3 thao",
        "emoji": "\u26bd",
        "desc": "\u0110\u00e1 b\u00f3ng ho\u1eb7c ch\u01a1i th\u1ec3 thao b\u1ecb r\u00e3 c\u01a1, tr\u1eadt kh\u1edbp c\u1ed5 ch\u00e2n \u2014 c\u1ea7n v\u1eadt l\u00fd tr\u1ecb li\u1ec7u.",
        "cost_type": "fixed",
        "cost_low": 800_000,
        "cost_high": 8_000_000,
        "insurance_type": "accident",
        "weight": 3,
        "lesson": (
            "Ch\u1ea5n th\u01b0\u01a1ng th\u1ec3 thao ph\u1ed5 bi\u1ebfn: bong g\u00e2n c\u1ed5 ch\u00e2n (500K\u20132M \u0111i\u1ec1u tr\u1ecb), "
            "r\u00e3 c\u01a1 \u0111\u00f9i, tr\u1eadt kh\u1edbp vai. V\u1eadt l\u00fd tr\u1ecb li\u1ec7u: 200\u2013500K/bu\u1ed5i, 6\u201312 bu\u1ed5i. "
            "B\u1ea3o hi\u1ec3m tai n\u1ea1n c\u00e1 nh\u00e2n bao g\u1ed3m chi ph\u00ed \u0111i\u1ec1u tr\u1ecb ch\u1ea5n th\u01b0\u01a1ng th\u1ec3 thao \u2014 "
            "\u0111\u1eb7c bi\u1ec7t h\u1eefu \u00edch cho ng\u01b0\u1eddi th\u01b0\u1eddng xuy\u00ean t\u1eadp th\u1ec3 thao."
        ),
    },
    {
        "id":  "accident_burn",
        "category": "accident",
        "title": "B\u1ecfng b\u1ebfp ho\u1eb7c h\u00f3a ch\u1ea5t",
        "emoji": "\U0001f525",
        "desc": "N\u1ea5u \u0103n b\u1ecb d\u1ea7u s\u00f4i b\u1eafn v\u00e0o tay ho\u1eb7c h\u00f3a ch\u1ea5t sinh ho\u1ea1t g\u00e2y b\u1ecfng nh\u1eb9 \u2014 c\u1ea7n \u0111i kh\u00e1m v\u00e0 mua thu\u1ed1c.",
        "cost_type": "fixed",
        "cost_low": 500_000,
        "cost_high": 5_000_000,
        "insurance_type": "accident",
        "weight": 4,
        "lesson": (
            "B\u1ecfng l\u00e0 tai n\u1ea1n sinh ho\u1ea1t ph\u1ed5 bi\u1ebfn: b\u1ecfng \u0111\u1ed9 1 (3\u20137 ng\u00e0y kh\u1ecfi, 300K\u20131M). "
            "B\u1ecfng \u0111\u1ed9 2\u20133 c\u1ea7n nh\u1eadp vi\u1ec7n: 5\u201330M \u0111i\u1ec1u tr\u1ecb + gh\u00e9p da n\u1ebfu n\u1eb7ng. "
            "S\u01a1 c\u1ee9u: x\u1ea3 n\u01b0\u1edbc l\u1ea1nh 15 ph\u00fat tr\u01b0\u1edbc khi \u0111i b\u1ec7nh vi\u1ec7n. "
            "B\u1ea3o hi\u1ec3m tai n\u1ea1n c\u00e1 nh\u00e2n chi tr\u1ea3 chi ph\u00ed \u0111i\u1ec1u tr\u1ecb b\u1ecfng \u2014 k\u1ec3 c\u1ea3 ph\u1eabu thu\u1eadt gh\u00e9p da."
        ),
    },

    # ════════════════════════════════════════════════════════════
    # BẤT ĐỘNG SẢN ĐẦU TƯ — chỉ áp dụng nếu có RE portfolio
    # cost_type = "re_pct"       → % × giá BĐS (ngẫu nhiên 1 BĐS)
    # cost_type = "re_rent_loss" → mất N tháng tiền thuê
    # ════════════════════════════════════════════════════════════
    {
        "id":  "re_repair",
        "category": "real_estate",
        "title": "Sửa chữa định kỳ BĐS",
        "emoji": "🔨",
        "desc": "Tường bong tróc, ống nước rỉ — phải sửa trước khi khách thuê phản nàn hoặc bỏ đi.",
        "cost_type": "re_pct",
        "cost_low_pct": 0.004,
        "cost_high_pct": 0.012,
        "cost_cap": 60_000_000,
        "insurance_type": "property",
        "weight": 4,
        "lesson": (
            "Chi phí sửa chữa BĐS thường 0.5–1.5% giá trị/năm. "
            "Căn hộ 3 tỷ → dự phòng 15–45M/năm bảo trì. "
            "Lỗi phổ biến: tính ROI BĐS mà không trừ chi phí bảo trì, "
            "dẫn đến yield thực thấp hơn kỳ vọng 1–2%/năm — con số tưởng nhỏ nhưng quan trọng."
        ),
    },
    {
        "id":  "re_equipment",
        "category": "real_estate",
        "title": "Hỏng thiết bị BĐS",
        "emoji": "❄️",
        "desc": "Điều hòa hoặc máy nước nóng trong căn hộ đang cho thuê hỏng — khách phàn nàn.",
        "cost_type": "re_pct",
        "cost_low_pct": 0.002,
        "cost_high_pct": 0.008,
        "cost_cap": 30_000_000,
        "insurance_type": "property",
        "weight": 4,
        "lesson": (
            "Thiết bị điện lạnh (điều hòa, tủ lạnh) tuổi thọ 7–12 năm. "
            "Nhà đầu tư chuyên nghiệp dự phòng thêm quỹ CapEx riêng ~0.5–1% giá trị/năm, "
            "ngoài quỹ vận hành thông thường — để thay thiết bị khi hỏng mà không ảnh hưởng dòng tiền."
        ),
    },
    {
        "id":  "re_vacant",
        "category": "real_estate",
        "title": "Khách thuê bỏ đi đột ngột",
        "emoji": "🏚️",
        "desc": "Khách thuê dọn đi không báo trước — BĐS trống, phải dọn dẹp và tìm khách mới.",
        "cost_type": "re_rent_loss",
        "months_loss": 1,
        "cost_cap": 80_000_000,
        "insurance_type": "property",
        "weight": 3,
        "lesson": (
            "Vacancy rate (tỷ lệ trống) trung bình BĐS VN: 5–15%/năm. "
            "Nhà đầu tư nên trừ vacancy khi tính yield: BĐS yield brut 8% → yield thực ~6.8–7.6%. "
            "Location tốt = vacancy thấp. Tìm khách mới thường mất 2–8 tuần."
        ),
    },
    {
        "id":  "re_dispute",
        "category": "real_estate",
        "title": "Tranh chấp với khách thuê",
        "emoji": "⚖️",
        "desc": "Khách thuê không chịu dọn ra sau khi hợp đồng hết hạn — phải nhờ luật sư can thiệp.",
        "cost_type": "fixed",
        "cost_low": 5_000_000,
        "cost_high": 30_000_000,
        "insurance_type": "property",
        "weight": 1,
        "lesson": (
            "Tranh chấp thuê nhà rất phổ biến tại VN. "
            "Phòng ngừa: hợp đồng thuê có công chứng, đặt cọc 2 tháng tiền thuê, "
            "điều khoản phạt vi phạm rõ ràng. "
            "Chi phí luật sư 5–30M + mất thêm 1–3 tháng tiền thuê trong thời gian tranh chấp."
        ),
    },
    {
        "id":  "re_tax_audit",
        "category": "real_estate",
        "title": "Kiểm tra thuế thu nhập cho thuê",
        "emoji": "🏛️",
        "desc": "Cơ quan thuế yêu cầu kê khai và nộp bổ sung thuế thu nhập từ hoạt động cho thuê.",
        "cost_type": "fixed",
        "cost_low": 3_000_000,
        "cost_high": 25_000_000,
        "insurance_type": None,
        "weight": 1,
        "lesson": (
            "Thuế thu nhập cho thuê BĐS tại VN: 10% trên doanh thu (gồm 5% TNCN + 5% VAT) "
            "nếu doanh thu > 100M/năm. "
            "Nhiều chủ nhà không kê khai đầy đủ — rủi ro bị truy thu + phạt 1–3 lần số thuế. "
            "Cần tư vấn kế toán nếu có nhiều BĐS cho thuê."
        ),
    },
    {
        "id":  "re_fire_damage",
        "category": "real_estate",
        "title": "Hỏa hoạn nhỏ, thiệt hại nội thất",
        "emoji": "🔥",
        "desc": "Chập điện gây cháy phòng bếp — thiệt hại nội thất và cần sửa lại tường, trần.",
        "cost_type": "re_pct",
        "cost_low_pct": 0.005,
        "cost_high_pct": 0.020,
        "cost_cap": 80_000_000,
        "insurance_type": "property",
        "weight": 1,
        "lesson": (
            "Bảo hiểm cháy nổ bắt buộc đối với nhà chung cư tại VN (Nghị định 23/2018) "
            "nhưng mức bảo hiểm thường rất thấp. "
            "Bảo hiểm BĐS toàn diện bao gồm hỏa hoạn, lũ lụt và thiệt hại tài sản — "
            "không thể thiếu cho nhà đầu tư có nhiều BĐS."
        ),
    },

    # ════════════════════════════════════════════════════════════
    # NƠI Ở MUA ĐỨT (townhouse / villa) — chỉ áp dụng nếu residence type=buy
    # cost_type = "res_pct"  → % × purchase_price, có cost_cap
    # ════════════════════════════════════════════════════════════
    {
        "id":  "res_plumbing",
        "category": "residence",
        "title": "Sự cố ống nước, hệ thống điện",
        "emoji": "💧",
        "desc": "Ống nước trong tường rò rỉ hoặc hệ thống điện chập chờn — thợ phải đục tường để sửa.",
        "cost_type": "res_pct",
        "cost_low_pct": 0.001,
        "cost_high_pct": 0.004,
        "cost_cap": 20_000_000,
        "insurance_type": "property",
        "weight": 4,
        "lesson": (
            "Hệ thống ống nước và điện cần kiểm tra định kỳ 5–10 năm. "
            "Sự cố ống nước trong tường đặc biệt tốn vì phải đục phá. "
            "Nhà ở cần ngân sách bảo trì 1–2% giá trị/năm — nhà phố 4 tỷ → dự phòng 40–80M/năm."
        ),
    },
    {
        "id":  "res_appliance",
        "category": "residence",
        "title": "Thiết bị gia dụng cao cấp hỏng",
        "emoji": "❄️",
        "desc": "Điều hòa trung tâm, máy bơm nước hoặc hệ thống lọc nước toàn nhà hỏng.",
        "cost_type": "res_pct",
        "cost_low_pct": 0.002,
        "cost_high_pct": 0.006,
        "cost_cap": 35_000_000,
        "insurance_type": "property",
        "weight": 3,
        "lesson": (
            "Biệt thự và nhà phố thường dùng điều hòa VRF (Variable Refrigerant Flow): 50–300M/cụm. "
            "Bảo trì 2 lần/năm 5–15M — rẻ hơn nhiều so với sửa chữa khi hỏng hoàn toàn. "
            "Thiết bị gia dụng cao cấp: chi phí sửa thường 30–50% giá mua."
        ),
    },
    {
        "id":  "res_waterproof",
        "category": "residence",
        "title": "Thấm nước mái, sàn",
        "emoji": "🏗️",
        "desc": "Mùa mưa phát hiện thấm nước qua mái hoặc sàn — nếu không xử lý sẽ hư kết cấu.",
        "cost_type": "res_pct",
        "cost_low_pct": 0.003,
        "cost_high_pct": 0.009,
        "cost_cap": 60_000_000,
        "insurance_type": "property",
        "weight": 2,
        "lesson": (
            "Chống thấm nhà phố/biệt thự: 20–80M. "
            "Không xử lý kịp thời dẫn đến nấm mốc, hư kết cấu sàn và tường — "
            "chi phí sửa lớn gấp 3–5 lần. "
            "Kiểm tra và bảo trì chống thấm định kỳ 5–7 năm là khoản đầu tư bắt buộc cho nhà sở hữu."
        ),
    },
    {
        "id":  "res_security",
        "category": "residence",
        "title": "Nâng cấp hệ thống an ninh",
        "emoji": "🔐",
        "desc": "Hàng xóm bị trộm — quyết định nâng cấp camera, cửa khóa thông minh, báo động.",
        "cost_type": "res_pct",
        "cost_low_pct": 0.001,
        "cost_high_pct": 0.003,
        "cost_cap": 15_000_000,
        "insurance_type": None,
        "weight": 2,
        "lesson": (
            "Hệ thống camera an ninh nhà ở: 3–15M cho setup cơ bản (4–8 camera). "
            "Khóa thông minh (smart lock): 2–8M/cái. "
            "Đây là khoản đầu tư giảm rủi ro với ROI cực tốt — "
            "bảo hiểm nhà ở cũng giảm phí premium nếu có hệ thống an ninh tốt."
        ),
    },

    # ════════════════════════════════════════════════════════════
    # CUỘC SỐNG — luôn áp dụng
    # ════════════════════════════════════════════════════════════
    {
        "id":  "life_scam",
        "category": "life",
        "title": "Bị lừa đảo trực tuyến",
        "emoji": "🎣",
        "desc": "Nhận cuộc gọi giả mạo ngân hàng, click link phishing — mất tiền trước khi kịp phát hiện.",
        "cost_type": "fixed",
        "cost_low": 2_000_000,
        "cost_high": 10_000_000,
        "insurance_type": None,
        "weight": 3,
        "lesson": (
            "Lừa đảo trực tuyến thiệt hại hơn 16,000 tỷ VND tại VN năm 2023. "
            "Nguyên tắc vàng: ngân hàng KHÔNG BAO GIỜ gọi hỏi OTP hay mật khẩu qua điện thoại. "
            "Bật xác thực 2 lớp (2FA) cho tất cả tài khoản ngân hàng và ví điện tử."
        ),
    },
    {
        "id":  "life_pickpocket",
        "category": "life",
        "title": "Mất ví, bị móc túi",
        "emoji": "👝",
        "desc": "Ví bị móc trên xe buýt hoặc chợ đông — mất tiền mặt và thẻ ngân hàng.",
        "cost_type": "fixed",
        "cost_low": 500_000,
        "cost_high": 5_000_000,
        "insurance_type": None,
        "weight": 4,
        "lesson": (
            "Không nên giữ quá 500K tiền mặt trong ví. "
            "Apple Pay / Google Pay an toàn hơn thẻ vật lý vì dùng token hóa — "
            "không thể sử dụng nếu bị mất điện thoại (cần sinh trắc học). "
            "Kích hoạt tính năng khóa thẻ ngay trong app ngân hàng khi phát hiện mất ví."
        ),
    },
    {
        "id":  "life_social",
        "category": "life",
        "title": "Chi phí xã hội: đám cưới, sinh nhật sếp",
        "emoji": "🎊",
        "desc": "Nhận 3 thiệp mời đám cưới và sinh nhật sếp cùng tháng — phong bì và quà không thể thiếu.",
        "cost_type": "fixed",
        "cost_low": 500_000,
        "cost_high": 6_000_000,
        "insurance_type": None,
        "weight": 5,
        "lesson": (
            "Chi phí xã hội (phong bì, quà, nhậu tiệc) chiếm trung bình 5–10% thu nhập người Việt. "
            "Trong quy tắc 50/30/20, đây thuộc phần 30% Wants. "
            "Mẹo: đặt ngân sách cố định cho 'chi phí xã hội' mỗi tháng và không vượt ngưỡng đó."
        ),
    },
    {
        "id":  "life_electricity",
        "category": "life",
        "title": "Hóa đơn điện tăng vọt",
        "emoji": "⚡",
        "desc": "Hóa đơn điện tháng này tăng gấp đôi vì mùa hè nóng, chạy điều hòa liên tục.",
        "cost_type": "fixed",
        "cost_low": 500_000,
        "cost_high": 4_000_000,
        "insurance_type": None,
        "weight": 4,
        "lesson": (
            "Điện tính theo bậc thang — càng dùng nhiều càng đắt/kWh. "
            "Mùa hè (T6-T8) hóa đơn có thể tăng 200–400% vì điều hòa ngốn điện. "
            "Điều hòa chiếm 40–60% hóa đơn điện gia đình. "
            "Điều hòa inverter tiết kiệm 30–50% điện so với điều hòa thường — tiết kiệm chi phí dài hạn."
        ),
    },
    {
        "id":  "life_theft",
        "category": "life",
        "title": "Trộm đột nhập",
        "emoji": "🔓",
        "desc": "Về nhà phát hiện kẻ trộm đã vào qua cửa sổ — lấy đi đồ điện tử và tiền mặt.",
        "cost_type": "fixed",
        "cost_low": 3_000_000,
        "cost_high": 25_000_000,
        "insurance_type": "property",
        "weight": 1,
        "lesson": (
            "Bảo hiểm tài sản gia đình bồi thường tài sản bị trộm trong nhà — "
            "đang phổ biến dần tại VN. "
            "Camera an ninh 4–8 camera: 3–15M là khoản đầu tư cực hiệu quả để phòng ngừa. "
            "Hầu hết vụ trộm là cơ hội (không có camera/khóa tốt) — phòng thủ đơn giản rất hiệu quả."
        ),
    },
    {
        "id":  "life_tech_broken",
        "category": "life",
        "title": "Thiết bị công nghệ hỏng",
        "emoji": "📱",
        "desc": "Điện thoại rơi vỡ màn hình kính, laptop tràn nước — phải sửa hoặc thay thế mới.",
        "cost_type": "fixed",
        "cost_low": 1_500_000,
        "cost_high": 20_000_000,
        "insurance_type": None,
        "weight": 3,
        "lesson": (
            "Thay màn hình iPhone 16 Pro Max: 5–9M. Sửa MacBook tràn nước: 8–25M. "
            "AppleCare+ (bảo hiểm thiết bị Apple): 2–4M/năm, cover 2 lần tai nạn. "
            "Quyết định mua AppleCare+ hợp lý nếu bạn hay làm rơi vỡ đồ — "
            "kỳ vọng toán học có lợi nếu xác suất tai nạn > 15–20%/năm."
        ),
    },
    {
        "id":  "life_pet",
        "category": "life",
        "title": "Thú cưng bệnh khẩn cấp",
        "emoji": "🐾",
        "desc": "Chó/mèo nuốt vật lạ hoặc bị tai nạn — cấp cứu thú y, phẫu thuật và thuốc.",
        "cost_type": "fixed",
        "cost_low": 1_000_000,
        "cost_high": 12_000_000,
        "insurance_type": None,
        "weight": 2,
        "lesson": (
            "Chi phí thú y cao cấp tại VN đang tăng mạnh: phẫu thuật 3–30M, ICU thú y 500K/ngày. "
            "Bảo hiểm thú cưng đang bắt đầu xuất hiện tại VN (~500K–2M/năm). "
            "Quỹ thú cưng dự phòng 5–15M là khôn ngoan nếu bạn nuôi thú cưng có giá trị tình cảm cao."
        ),
    },
    {
        "id":  "life_travel_cancel",
        "category": "life",
        "title": "Hủy chuyến đi, phí không hoàn",
        "emoji": "✈️",
        "desc": "Kế hoạch du lịch bị hủy do ốm hoặc công việc đột xuất — phí phạt hủy không được hoàn.",
        "cost_type": "fixed",
        "cost_low": 1_000_000,
        "cost_high": 10_000_000,
        "insurance_type": "travel",
        "weight": 3,
        "lesson": (
            "Bảo hiểm du lịch 100–500K/chuyến bao gồm: phí hủy chuyến bay, "
            "y tế khẩn cấp ở nước ngoài (lên đến $100,000), mất hành lý. "
            "Một trong những loại bảo hiểm có ROI cao nhất — chi ít, được bảo vệ nhiều."
        ),
    },
    {
        "id":  "life_income_drop",
        "category": "life",
        "title": "Thu nhập tháng này sụt giảm",
        "emoji": "📉",
        "desc": "Công ty cắt thưởng KPI hoặc dự án freelance bị hủy — thu nhập tháng này hụt đáng kể.",
        "cost_type": "fixed",
        "cost_low": 3_000_000,
        "cost_high": 20_000_000,
        "insurance_type": "unemployment",
        "weight": 2,
        "lesson": (
            "Thu nhập không ổn định là rủi ro tài chính lớn — đặc biệt với freelancer và người kinh doanh. "
            "Đa dạng hóa nguồn thu nhập (lương + đầu tư thụ động + freelance) giúp "
            "không quá phụ thuộc vào một nguồn. "
            "Quỹ khẩn cấp 3–6 tháng chi phí là 'lương thứ 2' giúp bạn tồn tại khi thu nhập gián đoạn."
        ),
    },
    {
        "id":  "life_family",
        "category": "life",
        "title": "Gia đình cần hỗ trợ tài chính",
        "emoji": "👨‍👩‍👧",
        "desc": "Bố/mẹ có việc cần gấp hoặc em cần tiền học phí — phải gửi tiền về hỗ trợ.",
        "cost_type": "fixed",
        "cost_low": 2_000_000,
        "cost_high": 15_000_000,
        "insurance_type": None,
        "weight": 3,
        "lesson": (
            "Hỗ trợ gia đình là thực tế tài chính của đa số người Việt — "
            "đặc biệt là con cái đầu tiên trong gia đình thoát nghèo. "
            "Mẹo: đặt ngân sách rõ ràng cho khoản này mỗi tháng và không để nó ăn vào "
            "quỹ khẩn cấp hay tiết kiệm cốt lõi của bạn."
        ),
    },
    {
        "id":  "life_unpaid_bill",
        "category": "life",
        "title": "Phí phạt hóa đơn quá hạn",
        "emoji": "📄",
        "desc": "Quên đóng thẻ tín dụng đúng hạn — bị tính lãi phạt và phí chậm thanh toán.",
        "cost_type": "fixed",
        "cost_low": 200_000,
        "cost_high": 2_000_000,
        "insurance_type": None,
        "weight": 4,
        "lesson": (
            "Thẻ tín dụng quá hạn: lãi phạt 3–4%/tháng = 36–48%/năm. "
            "Chỉ cần quên 1 tháng là mất tiền oan. "
            "Giải pháp: thiết lập auto-debit thanh toán tối thiểu mỗi tháng, "
            "đặt nhắc nhở lịch, hoặc thanh toán toàn bộ mỗi tháng để không bao giờ chịu lãi."
        ),
    },
]


# ── Helpers ───────────────────────────────────────────────────────

def _get_passive_effects_safe() -> dict:
    """
    Lấy passive effects tổng hợp + effect từ xe đang active.
    Xe đạp active: +0.15 emergency_resistance, +0.5 health_boost.
    """
    effects = {}
    try:
        from .item_effects import get_all_passive_effects
        effects = dict(get_all_passive_effects())
    except Exception:
        pass
    try:
        from .vehicle_system import get_active_vehicle_effects
        veh_effects = get_active_vehicle_effects()
        for k, v in veh_effects.items():
            effects[k] = effects.get(k, 0.0) + v
    except Exception:
        pass
    return effects


def _build_context() -> dict:
    """Trả về thông tin tài sản hiện tại của người chơi."""
    # inventory là list of item ID strings (không phải dicts)
    inventory     = cfg_list("anki_tycoon_inventory", [])
    re_portfolio  = cfg_list("anki_tycoon_re_portfolio", [])
    residence_raw = cfg_dict("anki_tycoon_residence", {})

    # Xe cộ lấy từ garage (vehicle_group lưu lowercase trong garage)
    _CAR_GROUPS    = {"ô tô", "xe điện"}
    _BIKE_GROUPS   = {"xe máy", "xe máy điện"}
    _CYCLE_GROUPS  = {"xe đạp"}

    garage_vehicles = []
    try:
        from .vehicle_system import get_garage_summary
        garage_vehicles = get_garage_summary()
    except Exception:
        pass

    cars      = [v for v in garage_vehicles if v.get("vehicle_group", "").lower() in _CAR_GROUPS]
    motorbikes = [v for v in garage_vehicles if v.get("vehicle_group", "").lower() in _BIKE_GROUPS]
    bicycles   = [v for v in garage_vehicles if v.get("vehicle_group", "").lower() in _CYCLE_GROUPS]

    res_type  = residence_raw.get("type", "rent")
    res_price = int(residence_raw.get("purchase_price", 0))

    return {
        "inventory":            inventory,  # list of item ID strings
        "cars":                 cars,       # list of garage vehicle dicts (có "price", "name")
        "has_car":              len(cars) > 0,
        "motorbikes":           motorbikes,
        "has_motorbike":        len(motorbikes) > 0,
        "bicycles":             bicycles,
        "has_bicycle":          len(bicycles) > 0,
        "re_portfolio":         re_portfolio,
        "has_re":               len(re_portfolio) > 0,
        "has_owned_residence":  res_type == "buy" and res_price > 0,
        "residence":            residence_raw,
        "residence_price":      res_price,
    }


def _applicable(ctx: dict) -> list:
    """Lọc sự kiện phù hợp với tài sản người chơi."""
    result = []
    for ev in EVENT_POOL:
        cat = ev["category"]
        if cat == "car"          and not ctx["has_car"]:          continue
        if cat == "motorbike"    and not ctx["has_motorbike"]:    continue
        if cat == "real_estate"  and not ctx["has_re"]:           continue
        if cat == "residence"    and not ctx["has_owned_residence"]: continue
        result.append(ev)
    return result


def _weighted_pick(events: list) -> dict:
    weights = [e.get("weight", 1) for e in events]
    total   = sum(weights)
    r       = random.random() * total
    cum     = 0
    for ev, w in zip(events, weights):
        cum += w
        if r <= cum:
            return ev
    return events[-1]


def _calc_cost(event: dict, ctx: dict) -> tuple[int, str]:
    """
    Tính chi phí và chuỗi mô tả ngữ cảnh.
    Áp dụng health_boost từ passive effects: giảm chi phí sự kiện y tế.
    Trả về (chi_phí_gốc, chuỗi_ngữ_cảnh).
    """
    ctype = event["cost_type"]
    cap   = event.get("cost_cap", 10_000_000_000)

    if ctype == "fixed":
        cost = random.randint(event["cost_low"], event["cost_high"])
        # Áp dụng health_boost cho sự kiện y tế
        if event.get("category") == "health":
            health_boost_val = float(ctx.get("passive_effects", {}).get("health_boost", 0.0))
            if health_boost_val > 0.0:
                reduction = min(0.9, health_boost_val * 0.1)  # mỗi điểm health = giảm 10%
                cost = max(int(cost * (1.0 - reduction)), 1000)
        return cost, ""

    elif ctype in ("car_pct", "car_tier"):
        car       = random.choice(ctx["cars"])
        car_price = int(car.get("price", 500_000_000))
        car_name  = car.get("name", "Xe hơi")
        if ctype == "car_pct":
            low  = max(int(car_price * event["cost_low_pct"]), 500_000)
            high = max(int(car_price * event["cost_high_pct"]), low)
            cost = min(random.randint(low, high), cap)
        else:
            cost = event["cost_tiers"][-1][1]
            for thresh, tcost in event["cost_tiers"]:
                if car_price < thresh:
                    cost = tcost
                    break
        return cost, f"(xe {car_name})"

    elif ctype == "bike_pct":
        bike       = random.choice(ctx["motorbikes"])
        bike_price = int(bike.get("price", 35_000_000))
        bike_name  = bike.get("name", "Xe máy")
        low  = max(int(bike_price * event["cost_low_pct"]), 50_000)
        high = max(int(bike_price * event["cost_high_pct"]), low)
        cost = min(random.randint(low, high), cap)
        return cost, f"(xe máy: {bike_name})"

    elif ctype == "re_pct":
        prop       = random.choice(ctx["re_portfolio"])
        prop_price = int(prop.get("price", 3_000_000_000))
        prop_name  = prop.get("name", "BĐS")
        low  = max(int(prop_price * event["cost_low_pct"]), 1_000_000)
        high = max(int(prop_price * event["cost_high_pct"]), low)
        cost = min(random.randint(low, high), cap)
        return cost, f"(BĐS: {prop_name})"

    elif ctype == "re_rent_loss":
        prop      = random.choice(ctx["re_portfolio"])
        rent      = int(prop.get("rent_price", 10_000_000))
        months    = event.get("months_loss", 1)
        cost      = min(rent * months, cap)
        prop_name = prop.get("name", "BĐS")
        return max(cost, 1_000_000), f"(mất {months} tháng thuê — {prop_name})"

    elif ctype == "res_pct":
        res_price = ctx["residence_price"]
        low  = max(int(res_price * event["cost_low_pct"]), 500_000)
        high = max(int(res_price * event["cost_high_pct"]), low)
        cost = min(random.randint(low, high), cap)
        res_id = ctx["residence"].get("id", "nhà")
        return cost, f"({res_id})"

    return 1_000_000, ""


def _insurance_factor(event: dict, inventory: list) -> float:
    """
    Trả về tỷ lệ tiền phải trả sau bảo hiểm.
    1.0 = không có bảo hiểm, 0.3 = bảo hiểm y tế giảm 70%.
    Hỗ trợ bảo hiểm chéo: ins_accident cũng bao phủ sự kiện y tế, v.v.
    inventory: list of item ID strings
    """
    # inventory là list of strings (item IDs), không phải dicts
    inv_ids = {i if isinstance(i, str) else i.get("id", "") for i in inventory}
    ins_type = event.get("insurance_type")

    # Bảo hiểm nhân thọ toàn diện — bao phủ mọi loại
    has_life = _LIFE_INSURANCE_ID in inv_ids
    life_red = _LIFE_INSURANCE_RED if has_life else 0.0

    # Bảo hiểm chuyên biệt
    best_specific = 0.0
    if ins_type and ins_type in _INSURANCE:
        info = _INSURANCE[ins_type]
        if info["item_id"] in inv_ids:
            best_specific = info["reduction"]
        # Kiểm tra bảo hiểm chéo
        for cross_id in _CROSS_COVERAGE.get(ins_type, []):
            if cross_id in inv_ids:
                # Bảo hiểm chéo cho 60% mức bảo vệ của bảo hiểm gốc
                cross_red = info["reduction"] * 0.6
                best_specific = max(best_specific, cross_red)

    best_red = max(life_red, best_specific)
    return max(0.05, 1.0 - best_red)  # luôn phải trả ít nhất 5%


# ── Dialog ────────────────────────────────────────────────────────

def _show_dialog(event: dict, base_cost: int, insured_cost: int,
                 cost_ctx: str, pay_factor: float, parent=None):
    from aqt import mw
    from aqt.qt import (
        QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, Qt,
    )
    if parent is None:
        parent = mw

    insured      = pay_factor < 0.999
    discount_pct = round((1.0 - pay_factor) * 100)

    dlg = QDialog(parent)
    dlg.setWindowTitle("⚠️ Sự kiện tài chính bất ngờ")
    dlg.setMinimumWidth(500)
    dlg.setModal(True)
    dlg.setStyleSheet("""
        QDialog {
            background: #0f172a;
            color: #e2e8f0;
            font-family: -apple-system, 'Segoe UI', sans-serif;
        }
        QLabel { color: #e2e8f0; }
        QPushButton {
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 28px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover { background: #2563eb; }
    """)

    layout = QVBoxLayout(dlg)
    layout.setSpacing(10)
    layout.setContentsMargins(24, 20, 24, 20)

    # Tiêu đề sự kiện
    title_lbl = QLabel(f"{event['emoji']}  {event['title']}")
    title_lbl.setStyleSheet(
        "font-size:18px; font-weight:900; color:#f97316; margin-bottom:4px;"
    )
    layout.addWidget(title_lbl)

    # Mô tả sự kiện
    desc_lbl = QLabel(event["desc"])
    desc_lbl.setWordWrap(True)
    desc_lbl.setStyleSheet("font-size:13px; color:#cbd5e1; margin-bottom:4px;")
    layout.addWidget(desc_lbl)

    # Ngữ cảnh (xe/BĐS cụ thể)
    if cost_ctx:
        ctx_lbl = QLabel(cost_ctx)
        ctx_lbl.setStyleSheet("font-size:12px; color:#475569; font-style:italic;")
        layout.addWidget(ctx_lbl)

    # ── Hộp chi phí ──────────────────────────────────────────────
    cost_frame = QFrame()
    cost_frame.setStyleSheet(
        "background:#1e293b; border-radius:10px; padding:4px; margin-top:4px;"
    )
    cost_inner = QVBoxLayout(cost_frame)
    cost_inner.setSpacing(5)
    cost_inner.setContentsMargins(14, 12, 14, 12)

    chead = QLabel("💸 Chi phí phát sinh")
    chead.setStyleSheet("font-size:12px; font-weight:bold; color:#64748b;")
    cost_inner.addWidget(chead)

    base_lbl = QLabel(f"Thiệt hại ước tính:  {base_cost:,}đ".replace(",", "."))
    base_lbl.setStyleSheet("font-size:13px; color:#e2e8f0;")
    cost_inner.addWidget(base_lbl)

    if insured:
        saved = base_cost - insured_cost
        ins_lbl = QLabel(
            f"🛡️ Bảo hiểm bù đắp (−{discount_pct}%):  −{saved:,}đ".replace(",", ".")
        )
        ins_lbl.setStyleSheet("font-size:13px; color:#4ade80;")
        cost_inner.addWidget(ins_lbl)

        final_lbl = QLabel(
            f"✅ Thực tế bạn phải trả:  {insured_cost:,}đ".replace(",", ".")
        )
        final_lbl.setStyleSheet("font-size:15px; font-weight:bold; color:#fbbf24;")
        cost_inner.addWidget(final_lbl)
    else:
        final_lbl = QLabel(
            f"❌ Số tiền bị trừ:  {insured_cost:,}đ".replace(",", ".")
        )
        final_lbl.setStyleSheet("font-size:15px; font-weight:bold; color:#ef4444;")
        cost_inner.addWidget(final_lbl)

        if event.get("insurance_type"):
            tip_map = {
                "health":   "Bảo hiểm y tế",
                "car":      "Bảo hiểm xe ô tô",
                "property": "Bảo hiểm bất động sản",
            }
            tip_name = tip_map.get(event["insurance_type"], "Bảo hiểm")
            tip_lbl = QLabel(
                f"💡 Mua {tip_name} trong shop để giảm thiệt hại lần sau!"
            )
            tip_lbl.setWordWrap(True)
            tip_lbl.setStyleSheet("font-size:12px; color:#60a5fa; font-style:italic;")
            cost_inner.addWidget(tip_lbl)

    layout.addWidget(cost_frame)

    # ── Hộp kiến thức ────────────────────────────────────────────
    lesson_frame = QFrame()
    lesson_frame.setStyleSheet(
        "background:#090f1e; border-radius:10px; border:1px solid #1e3a5f; "
        "padding:4px; margin-top:2px;"
    )
    lesson_inner = QVBoxLayout(lesson_frame)
    lesson_inner.setSpacing(4)
    lesson_inner.setContentsMargins(14, 10, 14, 10)

    lhead = QLabel("📚 Kiến thức tài chính")
    lhead.setStyleSheet("font-size:12px; font-weight:bold; color:#3b82f6;")
    lesson_inner.addWidget(lhead)

    lesson_lbl = QLabel(event["lesson"])
    lesson_lbl.setWordWrap(True)
    lesson_lbl.setStyleSheet("font-size:12px; color:#94a3b8; line-height:1.5;")
    lesson_inner.addWidget(lesson_lbl)
    layout.addWidget(lesson_frame)

    # OK button
    ok_btn = QPushButton("✓ Đã hiểu, tiếp tục")
    ok_btn.clicked.connect(dlg.accept)
    layout.addWidget(ok_btn, 0, Qt.AlignmentFlag.AlignRight)

    dlg.exec()


# ── Public API ────────────────────────────────────────────────────

def check_and_trigger_emergency(parent=None) -> bool:
    """
    Kiểm tra và kích hoạt sự kiện khẩn cấp ngẫu nhiên.
    Gọi từ _on_profile_loaded(). Tối đa 1 sự kiện/ngày.
    
    Items ảnh hưởng:
      - disease_resistance: giảm xác suất (cũ)
      - emergency_resistance: giảm xác suất (mới)
      - emergency_magnetism:  tăng xác suất (mới) — item "rủi ro"
      - emergency_cost_reduction: giảm chi phí (mới)
      - emergency_cost_increase:  tăng chi phí (mới)
      - health_boost: giảm chi phí y tế (cũ)
    
    Trả về True nếu sự kiện được kích hoạt.
    """
    if not col_ready():
        return False

    today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
    # Đã check hôm nay rồi → bỏ qua
    if cfg_str(_KEY_LAST_DATE, "") == today:
        return False
    # Đánh dấu đã check (dù có sự kiện hay không)
    cfg_set(_KEY_LAST_DATE, today)

    # ── Lấy passive effects ──
    passive = _get_passive_effects_safe()

    # ── Tính xác suất trigger ──
    # Các effect giảm xác suất
    disease_resist = float(passive.get("disease_resistance", 0.0))
    emergency_resist = float(passive.get("emergency_resistance", 0.0))
    total_resist = min(0.9, max(0.0, disease_resist) + max(0.0, emergency_resist))
    
    # Các effect tăng xác suất
    emergency_magnet = float(passive.get("emergency_magnetism", 0.0))
    emergency_magnet = min(0.9, max(0.0, emergency_magnet))
    
    # Công thức: base_prob * (1 - total_resist) * (1 + emergency_magnet)
    trigger_prob = BASE_TRIGGER_PROB * (1.0 - total_resist) * (1.0 + emergency_magnet)
    trigger_prob = max(0.01, min(0.95, trigger_prob))  # tối thiểu 1%, tối đa 95%

    if random.random() > trigger_prob:
        return False  # Ngày bình thường, không có sự kiện

    ctx        = _build_context()
    # Gắn passive effects vào context để _calc_cost dùng health_boost
    ctx["passive_effects"] = passive
    candidates = _applicable(ctx)
    if not candidates:
        return False

    event      = _weighted_pick(candidates)
    base_cost, cost_ctx = _calc_cost(event, ctx)
    factor     = _insurance_factor(event, ctx["inventory"])
    insured_cost = max(int(base_cost * factor), 0)

    # ── Áp dụng emergency_cost_reduction / emergency_cost_increase từ items ──
    cost_reduction = float(passive.get("emergency_cost_reduction", 0.0))
    cost_reduction = min(0.9, max(0.0, cost_reduction))
    cost_increase = float(passive.get("emergency_cost_increase", 0.0))
    cost_increase = min(0.9, max(0.0, cost_increase))
    
    if cost_reduction > 0.0:
        insured_cost = max(int(insured_cost * (1.0 - cost_reduction)), 1000)
    if cost_increase > 0.0:
        insured_cost = int(insured_cost * (1.0 + cost_increase))

    # Trừ tiền ngay
    try:
        from .balance import get_balance, set_balance
        from .transactions import add_transaction
        set_balance(max(get_balance() - insured_cost, -insured_cost))
        add_transaction(
            "emergency", insured_cost,
            f"🚨 Sự kiện khẩn cấp: {event['title']}"
        )
    except Exception:
        pass

    # Lưu log
    try:
        log = cfg_list(_KEY_LOG, [])
        log.insert(0, {
            "date":       today,
            "event_id":   event["id"],
            "title":      event["title"],
            "base_cost":  base_cost,
            "paid":       insured_cost,
            "insured":    factor < 0.999,
        })
        cfg_set(_KEY_LOG, log[:30])
    except Exception:
        pass

    # Hiện dialog sau 1.5 giây (tránh chồng chất với các tooltip khác)
    from aqt.qt import QTimer
    from aqt import mw
    _parent = parent or mw
    QTimer.singleShot(
        1500,
        lambda: _show_dialog(event, base_cost, insured_cost, cost_ctx, factor, _parent)
    )

    # Achievement trigger
    try:
        from .achievements import check_and_unlock
        check_and_unlock("emergency_handled", 1)
    except Exception:
        pass

    return True


def get_emergency_log() -> list:
    """Trả về lịch sử sự kiện khẩn cấp."""
    return cfg_list(_KEY_LOG, [])
