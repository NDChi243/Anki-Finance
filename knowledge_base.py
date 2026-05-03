# -*- coding: utf-8 -*-
from __future__ import annotations
"""
knowledge_base.py — Kho kiến thức tài chính cá nhân Anki Tycoon.

Mỗi "note" có:
  id        : uuid ngắn
  title     : tiêu đề
  body      : nội dung (plain text, hỗ trợ xuống dòng)
  category  : nhóm (do user tự đặt hoặc chọn từ gợi ý)
  tags      : list tag tự do
  emoji     : icon đại diện
  pinned    : ghim lên đầu
  created   : ISO timestamp
  updated   : ISO timestamp

Dữ liệu lưu vào Anki config (giống các module khác).
Admin có thể seed sẵn các bài học tài chính mặc định.
"""

import uuid
from datetime import datetime
from ._safe_config import col_ready, cfg_list, cfg_set

_KEY = "anki_tycoon_knowledge"

# ── Seed data — kiến thức tài chính mặc định ─────────────────────
# Admin chỉnh sửa danh sách này trước khi publish
SEED_NOTES = [
    {
        "title": "Lãi kép là gì?",
        "category": "Cơ bản",
        "emoji": "📈",
        "tags": ["lãi kép", "tiết kiệm", "thời gian"],
        "body": (
            "Lãi kép (Compound Interest) là lãi được tính trên cả gốc lẫn lãi đã tích lũy trước đó.\n\n"
            "Ví dụ: Gửi 10.000.000đ, lãi 8%/năm:\n"
            "  • Năm 1: 10.800.000đ\n"
            "  • Năm 5: ~14.693.000đ\n"
            "  • Năm 10: ~21.589.000đ\n"
            "  • Năm 20: ~46.610.000đ\n\n"
            "💡 Bí quyết: Bắt đầu càng sớm, lãi kép càng mạnh.\n"
            "Quy tắc 72: Chia 72 cho lãi suất = số năm để tiền nhân đôi.\n"
            "→ 72 ÷ 8% = 9 năm tiền nhân đôi!"
        ),
        "pinned": True,
    },
    {
        "title": "Quy tắc 50/30/20",
        "category": "Ngân sách",
        "emoji": "💰",
        "tags": ["ngân sách", "chi tiêu", "tiết kiệm"],
        "body": (
            "Quy tắc phân bổ thu nhập phổ biến nhất:\n\n"
            "  🔵 50% — Nhu cầu thiết yếu\n"
            "     Tiền nhà, ăn uống, điện nước, đi lại\n\n"
            "  🟡 30% — Mong muốn cá nhân\n"
            "     Giải trí, ăn ngoài, mua sắm không thiết yếu\n\n"
            "  🟢 20% — Tiết kiệm & đầu tư\n"
            "     Quỹ khẩn cấp, đầu tư dài hạn, trả nợ\n\n"
            "💡 Nếu thu nhập thấp, ưu tiên tăng % tiết kiệm trước.\n"
            "Điều chỉnh tỷ lệ phù hợp với hoàn cảnh của bạn."
        ),
        "pinned": True,
    },
    {
        "title": "Quỹ khẩn cấp",
        "category": "Cơ bản",
        "emoji": "🛡️",
        "tags": ["quỹ khẩn cấp", "an toàn tài chính"],
        "body": (
            "Quỹ khẩn cấp là khoản tiền dự phòng cho các tình huống bất ngờ:\n"
            "mất việc, bệnh tật, sửa xe, sửa nhà...\n\n"
            "📌 Mục tiêu: 3–6 tháng chi phí sinh hoạt\n"
            "📌 Để ở đâu: Tài khoản tiết kiệm không kỳ hạn — rút được ngay\n"
            "📌 KHÔNG đầu tư quỹ này vào cổ phiếu hoặc crypto\n\n"
            "Các bước xây dựng:\n"
            "  1. Tính chi phí 1 tháng của bạn\n"
            "  2. Đặt mục tiêu = chi phí × 3\n"
            "  3. Tiết kiệm đều đặn mỗi tháng cho đến khi đủ\n"
            "  4. Chỉ dùng khi thực sự khẩn cấp"
        ),
        "pinned": False,
    },
    {
        "title": "Lãi suất ngân hàng Việt Nam",
        "category": "Thực tế",
        "emoji": "🏦",
        "tags": ["ngân hàng", "lãi suất", "việt nam"],
        "body": (
            "Lãi suất tiết kiệm ngân hàng VN (tham khảo 2024):\n\n"
            "  Không kỳ hạn:  ~0.1–0.5%/năm\n"
            "  1 tháng:       ~3.5–4.5%/năm\n"
            "  3 tháng:       ~4.0–5.0%/năm\n"
            "  6 tháng:       ~4.5–5.5%/năm\n"
            "  12 tháng:      ~5.0–6.5%/năm\n"
            "  24 tháng:      ~5.5–7.0%/năm\n\n"
            "💡 Lãi suất thay đổi theo chính sách NHNN.\n"
            "So sánh nhiều ngân hàng trước khi gửi.\n"
            "Tiền gửi được bảo hiểm lên đến 125 triệu đồng/người/ngân hàng."
        ),
        "pinned": False,
    },
    {
        "title": "Đầu tư vs Tiết kiệm",
        "category": "Đầu tư",
        "emoji": "⚖️",
        "tags": ["đầu tư", "tiết kiệm", "rủi ro"],
        "body": (
            "Tiết kiệm:\n"
            "  ✅ An toàn, bảo toàn vốn\n"
            "  ✅ Lãi suất cố định, dễ dự đoán\n"
            "  ❌ Lãi suất thấp, có thể thua lạm phát\n"
            "  ✅ Phù hợp: quỹ khẩn cấp, mục tiêu ngắn hạn <3 năm\n\n"
            "Đầu tư:\n"
            "  ✅ Lợi nhuận tiềm năng cao hơn\n"
            "  ❌ Có rủi ro mất vốn\n"
            "  ✅ Phù hợp: mục tiêu dài hạn >5 năm\n"
            "  ❌ Cần kiến thức và thời gian nghiên cứu\n\n"
            "💡 Không nên đầu tư tiền mà bạn cần trong 1–2 năm tới.\n"
            "Đa dạng hóa = không bỏ tất cả trứng vào 1 giỏ."
        ),
        "pinned": False,
    },
    {
        "title": "Lạm phát là gì?",
        "category": "Kinh tế",
        "emoji": "📊",
        "tags": ["lạm phát", "kinh tế", "sức mua"],
        "body": (
            "Lạm phát là sự tăng giá chung của hàng hóa và dịch vụ theo thời gian.\n\n"
            "Ví dụ: Tô phở năm 2015 giá 30.000đ → năm 2024 giá 60.000đ\n"
            "→ Lạm phát đã 'ăn' 50% sức mua trong 9 năm\n\n"
            "Lạm phát VN trung bình ~3–5%/năm\n\n"
            "Tác động:\n"
            "  • 1 triệu đồng hôm nay ≠ 1 triệu đồng sau 10 năm\n"
            "  • Tiền gửi ngân hàng với lãi < lạm phát = thực tế đang lỗ\n"
            "  • Vì vậy cần đầu tư để bảo toàn sức mua\n\n"
            "💡 Mục tiêu tối thiểu: lợi nhuận đầu tư > tỷ lệ lạm phát"
        ),
        "pinned": False,
    },
    {
        "title": "Cổ phiếu là gì?",
        "category": "Đầu tư",
        "emoji": "📉",
        "tags": ["cổ phiếu", "chứng khoán", "đầu tư"],
        "body": (
            "Cổ phiếu là một phần sở hữu của công ty.\n"
            "Khi mua cổ phiếu = bạn trở thành cổ đông của công ty đó.\n\n"
            "Lợi nhuận từ cổ phiếu:\n"
            "  1. Tăng giá: mua 50.000đ → bán 80.000đ → lời 30.000đ\n"
            "  2. Cổ tức: công ty chia lợi nhuận định kỳ cho cổ đông\n\n"
            "Rủi ro:\n"
            "  • Giá có thể giảm xuống dưới giá mua\n"
            "  • Công ty có thể phá sản → mất vốn\n\n"
            "VN-Index: chỉ số đo lường thị trường chứng khoán Việt Nam\n\n"
            "💡 Không đầu tư tiền bạn không thể chấp nhận mất.\n"
            "Bắt đầu bằng quỹ ETF thay vì chọn cổ phiếu riêng lẻ."
        ),
        "pinned": False,
    },
    {
        "title": "Quỹ ETF — Đầu tư thụ động",
        "category": "Đầu tư",
        "emoji": "🗂️",
        "tags": ["etf", "quỹ đầu tư", "chứng khoán"],
        "body": (
            "ETF (Exchange-Traded Fund) = quỹ đầu tư giao dịch trên sàn.\n\n"
            "ETF mua 1 lúc nhiều cổ phiếu → tự động đa dạng hóa rủi ro.\n\n"
            "Ưu điểm:\n"
            "  ✅ Phí quản lý thấp (~0.3–0.65%/năm tại VN)\n"
            "  ✅ Không cần chọn cổ phiếu riêng lẻ\n"
            "  ✅ Giao dịch dễ như mua cổ phiếu thường\n"
            "  ✅ Phù hợp người mới bắt đầu\n\n"
            "ETF phổ biến tại VN: E1VFVN30, FUEVFVND, VFMVN30\n\n"
            "Chiến lược đơn giản: DCA (Dollar-Cost Averaging)\n"
            "→ Mua đều đặn mỗi tháng, không quan tâm giá lên xuống"
        ),
        "pinned": False,
    },
    {
        "title": "Tín dụng & Thẻ tín dụng",
        "category": "Thực tế",
        "emoji": "💳",
        "tags": ["tín dụng", "thẻ tín dụng", "nợ"],
        "body": (
            "Thẻ tín dụng cho phép chi tiêu trước, trả sau.\n\n"
            "⚠️ Lãi suất thẻ tín dụng: 25–35%/năm — rất cao!\n\n"
            "Dùng thẻ tín dụng đúng cách:\n"
            "  ✅ Thanh toán TOÀN BỘ dư nợ trước ngày đến hạn\n"
            "  ✅ Không bao giờ chỉ trả tối thiểu (minimum payment)\n"
            "  ✅ Tận dụng điểm thưởng và cashback\n"
            "  ❌ Không rút tiền mặt từ thẻ tín dụng\n"
            "  ❌ Không dùng thẻ tín dụng để đầu tư\n\n"
            "Ví dụ nguy hiểm: Nợ 10 triệu, chỉ trả tối thiểu 5%/tháng\n"
            "→ Mất 5–7 năm để trả hết và tốn gần gấp đôi tiền gốc!"
        ),
        "pinned": False,
    },
    {
        "title": "Bảo hiểm nhân thọ",
        "category": "Bảo vệ",
        "emoji": "🛡️",
        "tags": ["bảo hiểm", "rủi ro", "bảo vệ"],
        "body": (
            "Bảo hiểm nhân thọ bảo vệ tài chính gia đình khi bạn mất hoặc mắc bệnh hiểm nghèo.\n\n"
            "Khi nào cần bảo hiểm nhân thọ?\n"
            "  ✅ Có người phụ thuộc vào thu nhập của bạn\n"
            "  ✅ Còn nợ vay (nhà, xe)\n"
            "  ✅ Doanh nghiệp gia đình\n\n"
            "Các loại phổ biến:\n"
            "  • Bảo hiểm tử kỳ: rẻ nhất, chỉ bảo vệ trong thời hạn\n"
            "  • Bảo hiểm trọn đời: đắt hơn, bảo vệ suốt đời\n"
            "  • Bảo hiểm sức khỏe: chi trả viện phí\n\n"
            "💡 Ưu tiên bảo hiểm sức khỏe trước.\n"
            "Đọc kỹ điều khoản loại trừ trước khi ký hợp đồng."
        ),
        "pinned": False,
    },
]


# ── Helpers ───────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _make_id() -> str:
    return str(uuid.uuid4())[:8]

def _get_all() -> list:
    return cfg_list(_KEY, [])

def _save_all(notes: list):
    cfg_set(_KEY, notes)


# ── Public API ────────────────────────────────────────────────────

def get_all_notes() -> list:
    """Trả về tất cả notes, pinned lên trước, sort by updated desc."""
    notes = _get_all()
    notes.sort(key=lambda n: (not n.get("pinned", False), n.get("updated", "")), reverse=False)
    # stable sort: pinned first, then by updated desc
    pinned   = [n for n in notes if n.get("pinned")]
    unpinned = sorted([n for n in notes if not n.get("pinned")],
                      key=lambda n: n.get("updated",""), reverse=True)
    return pinned + unpinned


def get_note(note_id: str) -> dict | None:
    return next((n for n in _get_all() if n.get("id") == note_id), None)


def create_note(title: str, body: str, category: str = "Ghi chú",
                tags: list | None = None, emoji: str = "📝",
                pinned: bool = False) -> dict:
    if not col_ready():
        return {}
    now = _now()
    note = {
        "id":       _make_id(),
        "title":    title.strip(),
        "body":     body,
        "category": category.strip() or "Ghi chú",
        "tags":     tags or [],
        "emoji":    emoji or "📝",
        "pinned":   bool(pinned),
        "created":  now,
        "updated":  now,
    }
    notes = _get_all()
    notes.insert(0, note)
    _save_all(notes)
    return note


def update_note(note_id: str, title: str = None, body: str = None,
                category: str = None, tags: list = None,
                emoji: str = None, pinned: bool = None) -> dict:
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng"}
    notes = _get_all()
    note  = next((n for n in notes if n.get("id") == note_id), None)
    if not note:
        return {"ok": False, "error": "Không tìm thấy note"}
    if title    is not None: note["title"]    = title.strip()
    if body     is not None: note["body"]     = body
    if category is not None: note["category"] = category.strip()
    if tags     is not None: note["tags"]     = tags
    if emoji    is not None: note["emoji"]    = emoji
    if pinned   is not None: note["pinned"]   = bool(pinned)
    note["updated"] = _now()
    _save_all(notes)
    return {"ok": True, "note": note}


def delete_note(note_id: str) -> dict:
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng"}
    notes = _get_all()
    new   = [n for n in notes if n.get("id") != note_id]
    if len(new) == len(notes):
        return {"ok": False, "error": "Không tìm thấy note"}
    _save_all(new)
    return {"ok": True}


def toggle_pin(note_id: str) -> dict:
    notes = _get_all()
    note  = next((n for n in notes if n.get("id") == note_id), None)
    if not note:
        return {"ok": False}
    note["pinned"] = not note.get("pinned", False)
    note["updated"] = _now()
    _save_all(notes)
    return {"ok": True, "pinned": note["pinned"]}


def get_categories() -> list:
    """Danh sách category duy nhất đang có."""
    cats = list({n.get("category", "Ghi chú") for n in _get_all()})
    return sorted(cats)


def search_notes(query: str) -> list:
    """Tìm kiếm trong title + body + tags."""
    q = query.lower()
    return [
        n for n in get_all_notes()
        if q in n.get("title","").lower()
        or q in n.get("body","").lower()
        or any(q in t.lower() for t in n.get("tags",[]))
    ]


def seed_default_notes():
    """
    Seed các bài học tài chính mặc định nếu chưa có note nào.
    Gọi 1 lần khi profile load.
    """
    if not col_ready():
        return
    if _get_all():   # đã có dữ liệu → không seed lại
        return
    now = _now()
    notes = []
    for s in SEED_NOTES:
        note = {
            "id":       _make_id(),
            "title":    s["title"],
            "body":     s["body"],
            "category": s["category"],
            "tags":     s.get("tags", []),
            "emoji":    s.get("emoji", "📝"),
            "pinned":   s.get("pinned", False),
            "created":  now,
            "updated":  now,
        }
        notes.append(note)
    _save_all(notes)