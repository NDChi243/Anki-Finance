# -*- coding: utf-8 -*-
"""
finance_quiz.py — Câu đố tài chính: bộ câu hỏi trắc nghiệm trong tab Học tập.

Người dùng chủ động vào tab "Học tập" → chọn "Kiểm tra" → làm 1 set 10-15 câu.
Mỗi câu đúng → +QUIZ_BONUS (giới hạn 5 câu/ngày, cả đúng lẫn sai).
Mỗi câu đúng → +KN (Kiến Thức) ngẫu nhiên 15-20 điểm.
"""

import random
import time
import math
from ._safe_config import col_ready, cfg_int, cfg_dict, cfg_list, cfg_set, cfg_str
from .logger import get_logger
logger = get_logger(__name__)

_KEY_QUIZ_STATS     = "anki_tycoon_quiz_stats"
_KEY_QUIZ_SET_INDEX = "anki_tycoon_quiz_set_index"
_KEY_QUIZ_SET_DATA  = "anki_tycoon_quiz_set_data"
_KEY_QUIZ_TOPIC     = "anki_tycoon_quiz_topic"
_KEY_DAILY_DATE     = "anki_tycoon_quiz_daily_date"
_KEY_DAILY_CORRECT  = "anki_tycoon_quiz_daily_correct"
_KEY_DAILY_COUNT    = "anki_tycoon_quiz_daily_count"  # Tổng số câu đã trả lời trong ngày (cả đúng/sai)

QUIZ_BONUS       = 50_000  # Tiền thưởng khi trả lời đúng (VND)
KN_PER_CORRECT_MIN = 15    # KN tối thiểu cho 1 câu đúng
KN_PER_CORRECT_MAX = 20    # KN tối đa cho 1 câu đúng
QUIZ_SET_SIZE    = 12      # Số câu mỗi set
QUIZ_DAILY_LIMIT = 5       # Tối đa 5 câu (cả đúng lẫn sai)/ngày

# ── Topic definitions ─────────────────────────────────────────────
QUIZ_TOPICS = {
    "all":         "📚 Tất cả chủ đề",
    "lai_kep":     "⏳ Lãi kép & Thời gian",
    "chung_khoan": "📈 Chứng khoán",
    "crypto":      "₿ Crypto",
    "bat_dong_san":"🏠 Bất động sản",
    "ngan_hang":   "🏦 Ngân hàng & Tiết kiệm",
    "quan_ly_no":  "📉 Quản lý nợ",
    "fire":        "🔥 Ngân sách & FIRE",
    "bao_hiem":    "🛡️ Bảo hiểm",
    "tong_hop":    "🧠 Tổng hợp & Tư duy",
    "nang_cao":    "🚀 Nâng cao",
}

# ── Question pool ─────────────────────────────────────────────────

QUIZ_POOL = [
    # ── Lãi kép & Thời gian ─────────────────────────────────────────
    {
        "q": "Theo Quy tắc 72, với lãi suất 8%/năm, tiền sẽ tăng gấp đôi sau bao nhiêu năm?",
        "options": ["6 năm", "9 năm", "12 năm", "18 năm"],
        "correct": 1,
        "explanation": "Quy tắc 72: chia 72 cho lãi suất → 72 ÷ 8 = 9 năm. Đây là cách ước tính nhanh sức mạnh của lãi kép.",
        "topic": "lai_kep",
    },
    {
        "q": "Lãi kép (compound interest) khác lãi đơn ở điểm nào?",
        "options": [
            "Lãi kép tính theo tuần, lãi đơn tính theo tháng",
            "Lãi kép tính lãi trên cả gốc lẫn lãi đã tích lũy",
            "Lãi kép chỉ áp dụng cho tiền gửi ngân hàng",
            "Lãi kép luôn thấp hơn lãi đơn",
        ],
        "correct": 1,
        "explanation": "Lãi kép tính lãi trên cả vốn gốc lẫn lãi đã cộng dồn từ các kỳ trước — đây là bí mật làm giàu dài hạn của mọi nhà đầu tư.",
        "topic": "lai_kep",
    },
    {
        "q": "Nếu lạm phát 3%/năm, sức mua của 100 triệu đồng sẽ giảm còn khoảng một nửa sau bao nhiêu năm?",
        "options": ["12 năm", "18 năm", "24 năm", "36 năm"],
        "correct": 2,
        "explanation": "Quy tắc 72: 72 ÷ 3 = 24 năm để sức mua giảm một nửa. Đây là lý do tiền mặt dài hạn luôn thua lạm phát.",
        "topic": "lai_kep",
    },
    {
        "q": "Đầu tư 10 triệu, lãi kép 10%/năm trong 30 năm, kết quả xấp xỉ bao nhiêu?",
        "options": ["40 triệu", "130 triệu", "174 triệu", "300 triệu"],
        "correct": 2,
        "explanation": "10M × (1.10)^30 ≈ 174 triệu. Lãi kép nhân tài sản lên 17 lần sau 30 năm — đây là sức mạnh của thời gian!",
        "topic": "lai_kep",
    },
    {
        "q": "Tại sao bắt đầu đầu tư từ năm 25 tuổi lại có lợi hơn nhiều so với năm 35 tuổi?",
        "options": [
            "Vì lãi suất cao hơn khi còn trẻ",
            "Vì có nhiều thời gian cho lãi kép phát huy tác dụng",
            "Vì thuế đầu tư thấp hơn khi trẻ",
            "Vì rủi ro thị trường thấp hơn khi trẻ",
        ],
        "correct": 1,
        "explanation": "Thời gian là tài sản lớn nhất của nhà đầu tư. 10 năm chênh lệch có thể tạo ra hàng tỷ đồng nhờ lãi kép — tiền đẻ ra tiền theo cấp số nhân.",
        "topic": "lai_kep",
    },

    # ── Chứng khoán ─────────────────────────────────────────────────
    {
        "q": "T+2 trong giao dịch chứng khoán tại Việt Nam có nghĩa là gì?",
        "options": [
            "Tất toán trong vòng 2 giờ sau giao dịch",
            "Mua hôm nay, 2 ngày làm việc sau mới hoàn tất thanh toán và có thể bán",
            "Lãi suất ký quỹ 2% mỗi tháng",
            "Tối thiểu phải mua 2 mã cổ phiếu trong một lệnh",
        ],
        "correct": 1,
        "explanation": "T+2 = Settlement 2 ngày làm việc. Bạn mua hôm nay (T), nhưng cổ phiếu chỉ về tài khoản và có thể bán sau T+2. Đây là quy định thanh toán chứng khoán cơ bản.",
        "topic": "chung_khoan",
    },
    {
        "q": "Chỉ số P/E (Price-to-Earnings ratio) của một cổ phiếu đo lường điều gì?",
        "options": [
            "Tỷ lệ lợi nhuận hàng năm so với vốn đầu tư",
            "Giá cổ phiếu chia cho lợi nhuận mỗi cổ phiếu (EPS)",
            "Tỷ lệ cổ tức so với giá cổ phiếu hiện tại",
            "Tổng vốn hóa thị trường của công ty",
        ],
        "correct": 1,
        "explanation": "P/E = Giá / EPS. P/E = 20 nghĩa là nhà đầu tư sẵn sàng trả 20đ cho mỗi 1đ lợi nhuận. P/E cao = kỳ vọng tăng trưởng cao, P/E thấp = có thể đang rẻ hoặc công ty khó khăn.",
        "topic": "chung_khoan",
    },
    {
        "q": "Đa dạng hóa danh mục đầu tư (diversification) có lợi ích chính là gì?",
        "options": [
            "Đảm bảo lợi nhuận tối đa trong mọi thị trường",
            "Giảm rủi ro phi hệ thống (rủi ro riêng của từng cổ phiếu)",
            "Tránh hoàn toàn thuế thu nhập từ đầu tư",
            "Tăng tốc độ thực hiện giao dịch",
        ],
        "correct": 1,
        "explanation": "Đa dạng hóa giảm rủi ro phi hệ thống — rủi ro riêng của từng công ty. Khi 1 cổ phiếu giảm mạnh, các cổ phiếu khác trong danh mục có thể bù đắp tổn thất.",
        "topic": "chung_khoan",
    },
    {
        "q": "Cổ tức (dividend) là gì?",
        "options": [
            "Phí môi giới khi mua bán cổ phiếu",
            "Lãi suất ngân hàng áp dụng riêng cho cổ đông",
            "Phần lợi nhuận công ty chia cho cổ đông",
            "Phần trăm thuế trên mỗi giao dịch chứng khoán",
        ],
        "correct": 2,
        "explanation": "Cổ tức là một phần lợi nhuận mà công ty chia cho cổ đông, thường theo quý hoặc năm. Không phải công ty nào cũng trả cổ tức — nhiều công ty giữ lại để tái đầu tư.",
        "topic": "chung_khoan",
    },
    {
        "q": "Chỉ số VN-Index phản ánh điều gì?",
        "options": [
            "Giá trung bình của 30 cổ phiếu lớn nhất",
            "Tổng giá trị giao dịch mỗi phiên",
            "Biến động giá của toàn bộ cổ phiếu niêm yết trên HOSE",
            "Tỷ giá VND so với rổ ngoại tệ",
        ],
        "correct": 2,
        "explanation": "VN-Index là chỉ số tổng hợp phản ánh biến động giá của toàn bộ cổ phiếu niêm yết trên HOSE (Sở GDCK TP.HCM), tính theo phương pháp vốn hóa thị trường.",
        "topic": "chung_khoan",
    },

    # ── Crypto ───────────────────────────────────────────────────────
    {
        "q": "Staking crypto (cắm cọc tiền ảo) là gì?",
        "options": [
            "Mua crypto và giữ yên trong ví lạnh không giao dịch",
            "Khóa crypto trong mạng blockchain để tham gia xác thực và nhận phần thưởng",
            "Chuyển đổi crypto này sang crypto khác để hưởng chênh lệch",
            "Vay thêm tiền fiat để mua thêm crypto",
        ],
        "correct": 1,
        "explanation": "Staking là khóa crypto để tham gia xác thực giao dịch trên mạng Proof-of-Stake, nhận phần thưởng APY. Rủi ro: giá crypto có thể giảm mạnh trong thời gian bạn đang khóa.",
        "topic": "crypto",
    },
    {
        "q": "Rug pull trong thị trường crypto là gì?",
        "options": [
            "Giá tăng đột ngột rồi giảm nhanh do tin tức xấu",
            "Lỗi kỹ thuật của smart contract làm mất tiền",
            "Nhóm phát triển đột ngột rút hết thanh khoản và biến mất",
            "Cộng đồng cùng nhau bán tháo đồng loạt (panic sell)",
        ],
        "correct": 2,
        "explanation": "Rug pull: nhóm phát triển xây dự án, thu hút nhà đầu tư bơm tiền vào, rồi đột ngột rút hết thanh khoản và bỏ trốn. Phổ biến với meme coin và DeFi dự án nhỏ chưa được audit.",
        "topic": "crypto",
    },
    {
        "q": "USDT (Tether) thuộc loại tài sản crypto nào?",
        "options": [
            "Altcoin có biến động mạnh như Bitcoin",
            "Stablecoin được neo giá với USD (1 USDT ≈ 1 USD)",
            "Governance token dùng để bỏ phiếu trong DAO",
            "Proof-of-Work mining coin",
        ],
        "correct": 1,
        "explanation": "USDT là stablecoin được neo với USD. Dùng để tránh biến động khi muốn giữ giá trị tương đương USD trong thế giới crypto mà không cần chuyển ra tiền fiat.",
        "topic": "crypto",
    },
    {
        "q": "So với cổ phiếu, biến động giá (volatility) của crypto thường như thế nào?",
        "options": [
            "Tương đương nhau vì đều bị điều tiết bởi thị trường",
            "Thấp hơn vì crypto được quản lý bởi thuật toán",
            "Cao hơn nhiều — Bitcoin từng giảm 80% trong bear market",
            "Cao hơn nhưng không đáng kể so với cổ phiếu nhỏ",
        ],
        "correct": 2,
        "explanation": "Crypto nổi tiếng với biến động cực mạnh. Bitcoin từng giảm 80% trong bear market và tăng 10x trong bull market. Đây vừa là rủi ro lớn, vừa là cơ hội tiềm năng.",
        "topic": "crypto",
    },

    # ── Bất động sản ─────────────────────────────────────────────────
    {
        "q": "Cap rate (tỷ suất vốn hóa) trong đầu tư BĐS được tính như thế nào?",
        "options": [
            "Giá mua ban đầu / Tiền thuê hàng năm",
            "Thu nhập cho thuê ròng hàng năm / Giá trị tài sản",
            "Lợi nhuận khi bán / Chi phí mua ban đầu",
            "Tổng diện tích (m²) / Giá mua (tỷ đồng)",
        ],
        "correct": 1,
        "explanation": "Cap Rate = NOI (Thu nhập hoạt động ròng) / Giá trị tài sản. Ví dụ: thuê 120M/năm, nhà trị giá 2 tỷ → Cap rate = 6%. Dùng để so sánh các khoản đầu tư BĐS khác nhau.",
        "topic": "bat_dong_san",
    },
    {
        "q": "Thanh khoản của BĐS so với cổ phiếu như thế nào?",
        "options": [
            "BĐS có thanh khoản cao hơn vì giá trị lớn hơn",
            "Hai loại tài sản có thanh khoản tương đương nhau",
            "BĐS có thanh khoản thấp hơn nhiều — không bán ngay được",
            "Phụ thuộc hoàn toàn vào vị trí và loại BĐS",
        ],
        "correct": 2,
        "explanation": "BĐS có thanh khoản rất thấp — mua bán có thể mất vài tuần đến vài tháng. Cổ phiếu có thể bán trong vài giây. Đây là đánh đổi cần cân nhắc khi phân bổ tài sản.",
        "topic": "bat_dong_san",
    },
    {
        "q": "Thuế thu nhập từ chuyển nhượng BĐS tại Việt Nam thường được tính là bao nhiêu trên giá chuyển nhượng?",
        "options": ["0.5%", "1%", "2%", "5%"],
        "correct": 2,
        "explanation": "Thuế chuyển nhượng BĐS tại VN = 2% trên giá ghi trong hợp đồng. Đây là chi phí quan trọng cần tính vào khi mua bán BĐS để tính lợi nhuận thực sự.",
        "topic": "bat_dong_san",
    },
    {
        "q": "Mua nhà 2 tỷ, vốn tự có 1 tỷ (vay 1 tỷ). Nhà tăng giá 20%. Lợi nhuận thực tế trên vốn tự có là bao nhiêu?",
        "options": ["10%", "20%", "40%", "60%"],
        "correct": 2,
        "explanation": "Nhà tăng 20% = +400 triệu. Vốn tự có = 1 tỷ. Lợi nhuận thực = 400M / 1 tỷ = 40%. Đòn bẩy khuếch đại lợi nhuận gấp đôi — và cũng khuếch đại rủi ro tương tự!",
        "topic": "bat_dong_san",
    },

    # ── Ngân hàng & Tiết kiệm ───────────────────────────────────────
    {
        "q": "Lãi suất thực (real interest rate) được tính như thế nào?",
        "options": [
            "Lãi suất danh nghĩa × Số năm gửi",
            "Lãi suất danh nghĩa − Tỷ lệ lạm phát",
            "Lãi suất cho vay − Lãi suất huy động",
            "Lãi suất ngân hàng + Phí dịch vụ hàng năm",
        ],
        "correct": 1,
        "explanation": "Lãi suất thực = Lãi suất danh nghĩa − Lạm phát. Gửi tiết kiệm 6%, lạm phát 4% → Lãi thực chỉ 2%. Đây mới là lợi nhuận thực sự của bạn sau khi trừ lạm phát.",
        "topic": "ngan_hang",
    },
    {
        "q": "Nếu lãi suất tiết kiệm 7%/năm và lạm phát 5%/năm, lãi suất thực là bao nhiêu?",
        "options": ["12%/năm", "7%/năm", "5%/năm", "2%/năm"],
        "correct": 3,
        "explanation": "Lãi suất thực = 7% − 5% = 2%/năm. Tiền của bạn thực sự chỉ tăng sức mua 2% mỗi năm, không phải 7%. Lạm phát 'ăn' phần lớn lãi suất danh nghĩa của bạn.",
        "topic": "ngan_hang",
    },
    {
        "q": "Tiền gửi có kỳ hạn dài (12-60 tháng) thường có lợi gì so với không kỳ hạn?",
        "options": [
            "Có thể rút bất cứ lúc nào mà không bị phạt",
            "Lãi suất cao hơn đổi lại phải cam kết không rút sớm",
            "Không bị ảnh hưởng bởi lạm phát",
            "Được bảo hiểm toàn phần không giới hạn bởi nhà nước",
        ],
        "correct": 1,
        "explanation": "Kỳ hạn dài → lãi suất cao hơn. Đây là bù đắp cho việc bạn cam kết không dùng tiền trong thời gian đó. Rút trước hạn thường bị tính lãi suất không kỳ hạn (thấp hơn nhiều).",
        "topic": "ngan_hang",
    },
    {
        "q": "Bảo hiểm tiền gửi tại Việt Nam bảo vệ tối đa bao nhiêu cho mỗi người ở một ngân hàng?",
        "options": ["50 triệu VND", "100 triệu VND", "125 triệu VND", "500 triệu VND"],
        "correct": 2,
        "explanation": "Bảo hiểm tiền gửi VN (BHTGVN) bảo vệ tối đa 125 triệu VND/người/tổ chức tham gia. Nếu gửi nhiều hơn ở một ngân hàng, phần vượt quá không được bảo hiểm nếu ngân hàng phá sản.",
        "topic": "ngan_hang",
    },

    # ── Quản lý nợ ──────────────────────────────────────────────────
    {
        "q": "Phương pháp Debt Snowball (Quả cầu tuyết) trả nợ hoạt động như thế nào?",
        "options": [
            "Trả khoản nợ có lãi suất cao nhất trước để tiết kiệm tiền lãi",
            "Trả khoản nợ có số dư nhỏ nhất trước để tạo động lực",
            "Chia đều tiền trả cho tất cả các khoản nợ mỗi tháng",
            "Gộp tất cả khoản nợ thành một khoản lớn duy nhất",
        ],
        "correct": 1,
        "explanation": "Snowball: trả khoản nhỏ nhất trước, tạo cảm giác chiến thắng và duy trì động lực. Về toán học không tối ưu bằng Avalanche nhưng hiệu quả tâm lý cao hơn — giúp nhiều người kiên trì hơn.",
        "topic": "quan_ly_no",
    },
    {
        "q": "Phương pháp Debt Avalanche khác Snowball ở điểm then chốt nào?",
        "options": [
            "Trả khoản nợ cũ nhất (thời gian vay dài nhất) trước",
            "Trả khoản có lãi suất cao nhất trước để tiết kiệm tổng tiền lãi nhiều nhất",
            "Trả đều mỗi khoản không phân biệt lãi suất",
            "Không trả nợ, dùng tiền đó đầu tư sinh lời cao hơn lãi vay",
        ],
        "correct": 1,
        "explanation": "Avalanche: ưu tiên khoản lãi suất cao nhất. Về toán học, cách này tiết kiệm tổng tiền lãi phải trả nhiều nhất. Tuy nhiên có thể mất nhiều thời gian hơn để thấy khoản đầu tiên tất toán.",
        "topic": "quan_ly_no",
    },
    {
        "q": "Tỷ lệ Nợ/Thu nhập (DTI - Debt-to-Income ratio) an toàn thường được khuyến nghị là dưới bao nhiêu?",
        "options": ["20%", "36%", "50%", "60%"],
        "correct": 1,
        "explanation": "DTI dưới 36% được xem là lành mạnh theo tiêu chuẩn tài chính. Ngân hàng thường từ chối cho vay thêm nếu DTI vượt 43-50%. DTI thấp = tài chính khỏe mạnh, ít rủi ro vỡ nợ.",
        "topic": "quan_ly_no",
    },
    {
        "q": "Khoản vay nào được coi là 'nợ tốt' (good debt)?",
        "options": [
            "Vay mua điện thoại mới nhất",
            "Vay mua xe hơi để đi làm hàng ngày",
            "Thẻ tín dụng mua sắm tiêu dùng",
            "Vay mua BĐS cho thuê hoặc vay học phí tăng thu nhập tương lai",
        ],
        "correct": 3,
        "explanation": "'Nợ tốt' = vay để mua tài sản sinh lời hoặc tăng thu nhập tương lai (BĐS cho thuê, học phí MBA). 'Nợ xấu' = vay mua tài sản giảm giá (xe, điện thoại) hoặc vay tiêu dùng.",
        "topic": "quan_ly_no",
    },

    # ── Ngân sách & FIRE ─────────────────────────────────────────────
    {
        "q": "Theo quy tắc ngân sách 50/30/20, 50% thu nhập dành cho điều gì?",
        "options": [
            "Tiết kiệm và đầu tư dài hạn",
            "Mong muốn và giải trí (Wants)",
            "Nhu cầu thiết yếu: ăn, ở, đi lại, hóa đơn (Needs)",
            "Trả nợ và hóa đơn tín dụng",
        ],
        "correct": 2,
        "explanation": "Quy tắc 50/30/20: 50% Needs (nhu cầu thiết yếu) / 30% Wants (mong muốn, giải trí) / 20% Savings & Debt (tiết kiệm, đầu tư, trả nợ). Đây là khung ngân sách đơn giản và phổ biến nhất.",
        "topic": "fire",
    },
    {
        "q": "Quỹ khẩn cấp (emergency fund) nên tương đương bao nhiêu tháng chi phí sinh hoạt?",
        "options": ["1 tháng", "3–6 tháng", "12 tháng", "24 tháng"],
        "correct": 1,
        "explanation": "Quỹ khẩn cấp 3-6 tháng chi phí giúp bạn vượt qua mất việc, bệnh tật, hoặc sự cố bất ngờ mà không phải vay nóng lãi suất cao hoặc bán tháo đầu tư đúng lúc thị trường xấu.",
        "topic": "fire",
    },
    {
        "q": "Quy tắc 4% trong phong trào FIRE (Financial Independence, Retire Early) có nghĩa là gì?",
        "options": [
            "Tiết kiệm 4% lương mỗi tháng là đủ để nghỉ hưu",
            "Đầu tư đạt 4% lợi nhuận/năm là đủ sống",
            "Tích lũy tài sản = 25× chi tiêu/năm, rút 4%/năm để sống không cạn kiệt",
            "Đóng thuế 4% trên toàn bộ thu nhập đầu tư hàng năm",
        ],
        "correct": 2,
        "explanation": "Quy tắc 4%: nếu tài sản đầu tư = 25× chi tiêu hàng năm, bạn có thể rút 4%/năm và tài sản kéo dài 30+ năm. Ví dụ: chi 300M/năm → cần 7.5 tỷ để FIRE.",
        "topic": "fire",
    },
    {
        "q": "Dollar-Cost Averaging (DCA) là chiến lược đầu tư như thế nào?",
        "options": [
            "Dồn toàn bộ tiền mua vào khi giá chạm đáy thấp nhất",
            "Đầu tư một số tiền cố định theo định kỳ bất kể giá thị trường",
            "Chỉ mua USD và chờ tỷ giá VND tăng để hưởng lợi",
            "Chia đều tiền vào 10 loại tài sản khác nhau một lần",
        ],
        "correct": 1,
        "explanation": "DCA: đầu tư cùng số tiền mỗi kỳ (ví dụ 2 triệu/tháng vào ETF) bất kể thị trường tăng hay giảm. Khi giá thấp mua được nhiều cổ phần hơn, khi giá cao mua ít — bình quân giá hiệu quả theo thời gian.",
        "topic": "fire",
    },

    # ── Bảo hiểm ────────────────────────────────────────────────────
    {
        "q": "Lý do chính để mua bảo hiểm y tế ngay cả khi còn trẻ khỏe là gì?",
        "options": [
            "Vì bắt buộc theo quy định pháp luật hiện hành",
            "Để bảo vệ tài chính khỏi chi phí y tế thảm họa bất ngờ",
            "Vì phí bảo hiểm (premium) thấp hơn nhiều khi còn trẻ",
            "Để được hoàn thuế thu nhập cá nhân cuối năm",
        ],
        "correct": 1,
        "explanation": "Bảo hiểm y tế bảo vệ bạn khỏi chi phí y tế đột xuất có thể phá hủy tài chính (ung thư, tai nạn, phẫu thuật lớn). Mục đích chính là quản lý rủi ro thảm họa, không phải tiết kiệm phí khám thông thường.",
        "topic": "bao_hiem",
    },
    {
        "q": "Premium trong hợp đồng bảo hiểm là gì?",
        "options": [
            "Số tiền bảo hiểm sẽ bồi thường khi có sự cố xảy ra",
            "Mức khấu trừ tự trả (deductible) trước khi bảo hiểm chi trả",
            "Phí bảo hiểm định kỳ phải đóng để duy trì hợp đồng",
            "Tên gọi của gói bảo hiểm cao cấp nhất",
        ],
        "correct": 2,
        "explanation": "Premium = phí bảo hiểm bạn đóng định kỳ (hàng tháng hoặc hàng năm) để duy trì hợp đồng có hiệu lực. Không đóng premium → hợp đồng mất hiệu lực, không được bảo vệ khi cần.",
        "topic": "bao_hiem",
    },

    # ── Tổng hợp & Tư duy tài chính ─────────────────────────────────
    {
        "q": "Mối quan hệ giữa rủi ro và lợi nhuận kỳ vọng trong đầu tư là gì?",
        "options": [
            "Rủi ro cao hơn luôn đảm bảo lợi nhuận cao hơn chắc chắn",
            "Rủi ro cao hơn đi kèm tiềm năng lợi nhuận cao hơn, nhưng không đảm bảo",
            "Không có mối quan hệ thực sự nào giữa rủi ro và lợi nhuận",
            "Rủi ro thấp thường cho lợi nhuận cao hơn trong dài hạn",
        ],
        "correct": 1,
        "explanation": "Rủi ro cao → tiềm năng lợi nhuận cao HƠN, không phải đảm bảo. Crypto rủi ro cao có thể tăng 10x hoặc giảm 90%. Trái phiếu chính phủ rủi ro thấp, lợi nhuận ổn định thấp hơn.",
        "topic": "tong_hop",
    },
    {
        "q": "Lạm phát ảnh hưởng thế nào đến tiền mặt giữ dưới gối theo thời gian?",
        "options": [
            "Không ảnh hưởng — số tiền vật lý vẫn giữ nguyên",
            "Làm tăng giá trị tiền vì khan hiếm hơn",
            "Làm giảm sức mua — cùng số tiền mua được ít hàng hóa hơn",
            "Chỉ ảnh hưởng đến ngoại tệ, không ảnh hưởng VND",
        ],
        "correct": 2,
        "explanation": "Lạm phát là kẻ thù vô hình của tiền mặt. 100 triệu hôm nay chỉ mua được lượng hàng tương đương ~74 triệu sau 10 năm nếu lạm phát trung bình 3%/năm.",
        "topic": "tong_hop",
    },
    {
        "q": "Net Worth (Tài sản ròng) của một người được tính như thế nào?",
        "options": [
            "Tổng thu nhập hàng năm − Tổng chi tiêu hàng năm",
            "Tổng tài sản sở hữu − Tổng nợ phải trả",
            "Giá trị BĐS + Tiền gửi ngân hàng + Cổ phiếu",
            "Mức lương hàng tháng × 12 tháng",
        ],
        "correct": 1,
        "explanation": "Net Worth = Tổng tài sản (tiền mặt, đầu tư, BĐS, xe...) − Tổng nợ (vay ngân hàng, thẻ tín dụng...). Đây là thước đo sức khỏe tài chính thực sự, quan trọng hơn mức thu nhập đơn thuần.",
        "topic": "tong_hop",
    },
    {
        "q": "Loại tài sản nào lịch sử được coi là hàng rào chống lạm phát hiệu quả nhất?",
        "options": [
            "Tiền gửi không kỳ hạn tại ngân hàng nhà nước",
            "Trái phiếu chính phủ ngắn hạn kỳ hạn 3 tháng",
            "Bất động sản và vàng",
            "Tiền mặt giữ trong két an toàn",
        ],
        "correct": 2,
        "explanation": "BĐS và vàng lịch sử có xu hướng giữ hoặc tăng giá trị thực theo thời gian, trong khi tiền mặt bị lạm phát bào mòn. Đây là lý do dài hạn nên đầu tư thay vì giữ tiền mặt.",
        "topic": "tong_hop",
    },
    {
        "q": "Opportunity cost (Chi phí cơ hội) trong tài chính là gì?",
        "options": [
            "Phí giao dịch và hoa hồng khi mua bán đầu tư",
            "Lợi nhuận từ phương án tốt nhất bị bỏ qua khi chọn một phương án khác",
            "Chi phí bỏ lỡ một đợt giảm giá mua hàng hóa",
            "Thuế phải nộp trên lợi nhuận từ đầu tư",
        ],
        "correct": 1,
        "explanation": "Opportunity cost = lợi nhuận bỏ lỡ từ lựa chọn tốt nhất không được chọn. Ví dụ: giữ 1 tỷ tiền mặt thay vì đầu tư 8%/năm → chi phí cơ hội = 80 triệu/năm đã bỏ lỡ.",
        "topic": "tong_hop",
    },
    {
        "q": "Tỷ suất tiết kiệm (savings rate) được tính như thế nào?",
        "options": [
            "Tổng tiết kiệm / Tổng tài sản hiện có",
            "Tiền tiết kiệm hàng tháng / Thu nhập hàng tháng",
            "Lãi suất tiết kiệm ngân hàng / Lạm phát",
            "Chi tiêu hàng tháng / Thu nhập hàng tháng",
        ],
        "correct": 1,
        "explanation": "Savings Rate = Tiền tiết kiệm / Thu nhập. Savings rate cao là động cơ chính xây dựng tài sản. Người lương 50M tiết kiệm 50% sẽ giàu hơn người lương 100M tiết kiệm 5%.",
        "topic": "tong_hop",
    },

    # ── Nâng cao ────────────────────────────────────────────────────
    {
        "q": "ETF (Exchange-Traded Fund) khác Quỹ tương hỗ thông thường ở điểm gì chính?",
        "options": [
            "ETF chỉ đầu tư vào cổ phiếu, quỹ tương hỗ đầu tư vào trái phiếu",
            "ETF giao dịch trên sàn như cổ phiếu, phí quản lý thường thấp hơn nhiều",
            "ETF được bảo đảm bởi chính phủ, quỹ tương hỗ thì không",
            "ETF chỉ dành cho nhà đầu tư tổ chức, không dành cho cá nhân",
        ],
        "correct": 1,
        "explanation": "ETF giao dịch theo thời gian thực trên sàn như cổ phiếu, phí quản lý thường 0.03–0.5%/năm. Quỹ tương hỗ hoạt động tính giá cuối ngày (NAV), phí 1–2%/năm. ETF phổ biến vì phí thấp và minh bạch.",
        "topic": "nang_cao",
    },
    {
        "q": "Trái phiếu (bond) là gì?",
        "options": [
            "Cổ phần sở hữu trong một công ty",
            "Hợp đồng cho vay — người mua cho vay tiền, được trả lãi định kỳ và hoàn vốn khi đáo hạn",
            "Hợp đồng mua bán ngoại tệ kỳ hạn",
            "Chứng chỉ tiền gửi ngân hàng không kỳ hạn",
        ],
        "correct": 1,
        "explanation": "Trái phiếu = người mua cho tổ chức phát hành vay tiền. Người mua nhận lãi suất cố định (coupon) định kỳ và nhận lại vốn gốc khi đáo hạn. Rủi ro thấp hơn cổ phiếu nhưng lợi nhuận kỳ vọng cũng thấp hơn.",
        "topic": "nang_cao",
    },
    {
        "q": "Tái cân bằng danh mục (rebalancing) có nghĩa là gì?",
        "options": [
            "Bán hết danh mục và mua lại từ đầu",
            "Điều chỉnh tỷ trọng tài sản về mức mục tiêu ban đầu sau khi thị trường thay đổi",
            "Chuyển toàn bộ sang tài sản an toàn hơn khi thị trường xấu",
            "Tăng gấp đôi đầu tư khi giá giảm để bắt đáy",
        ],
        "correct": 1,
        "explanation": "Rebalancing: nếu cổ phiếu tăng mạnh làm tỷ trọng lệch (70% thay vì 60% mục tiêu), bán bớt cổ phiếu và mua thêm trái phiếu để quay về 60/40. Giúp duy trì mức rủi ro mong muốn và tự động 'bán cao, mua thấp'.",
        "topic": "nang_cao",
    },
    {
        "q": "NAV (Net Asset Value) trong quỹ đầu tư được tính như thế nào?",
        "options": [
            "Tổng doanh thu của quỹ trong năm",
            "(Tổng tài sản của quỹ − Tổng nợ) / Số chứng chỉ quỹ đang lưu hành",
            "Giá mua ban đầu của tất cả tài sản trong quỹ",
            "Lợi nhuận chia cổ tức của quỹ trong quý",
        ],
        "correct": 1,
        "explanation": "NAV = (Tổng tài sản − Nợ) / Số chứng chỉ. Đây là giá trị thực của mỗi chứng chỉ quỹ. Quỹ tương hỗ tính NAV cuối ngày; ETF có giá thị trường giao dịch theo thời gian thực (thường sát NAV).",
        "topic": "nang_cao",
    },
    {
        "q": "Margin trading (giao dịch ký quỹ) trong chứng khoán là gì và rủi ro chính?",
        "options": [
            "Giao dịch không cần phí môi giới — rủi ro bị cấm tài khoản",
            "Vay tiền từ môi giới để mua thêm cổ phiếu — khuếch đại cả lãi lẫn lỗ",
            "Mua cổ phiếu thanh toán sau 30 ngày — rủi ro không thanh toán được",
            "Đặt lệnh mua với giá thấp hơn thị trường — rủi ro lệnh không khớp",
        ],
        "correct": 1,
        "explanation": "Margin: vay tiền môi giới để đầu tư thêm. Nếu cổ phiếu tăng 20% và dùng đòn bẩy 2x, lãi thực 40% — nhưng giảm 20% thì lỗ 40% vốn thực. Nếu tài sản giảm quá mức ký quỹ, bị 'margin call' — môi giới bán cổ phiếu của bạn bất kể giá.",
        "topic": "nang_cao",
    },
    {
        "q": "Short selling (bán khống) hoạt động như thế nào?",
        "options": [
            "Bán cổ phiếu trong vòng 24 giờ sau khi mua",
            "Vay cổ phiếu, bán ra ngay, sau đó mua lại với giá thấp hơn để trả — lãi khi giá giảm",
            "Bán cổ phiếu mà chưa có (naked short) — bị pháp luật cấm hoàn toàn",
            "Đặt lệnh bán ngay khi cổ phiếu vừa đạt đỉnh mới",
        ],
        "correct": 1,
        "explanation": "Short selling: vay cổ phiếu từ môi giới, bán ở giá cao, sau đó mua lại ở giá thấp hơn để trả lại, lãi khi giá giảm. Rủi ro lý thuyết vô hạn — giá có thể tăng không giới hạn. Tại VN chưa có bán khống đối với nhà đầu tư cá nhân.",
        "topic": "nang_cao",
    },
    {
        "q": "Sự khác nhau giữa Gross yield và Net yield trong đầu tư BĐS là gì?",
        "options": [
            "Gross yield tính trước thuế, Net yield tính sau thuế và chi phí vận hành",
            "Gross yield là lợi nhuận bán ra, Net yield là lợi nhuận cho thuê",
            "Gross yield dành cho thương mại, Net yield dành cho nhà ở",
            "Không có sự khác biệt — đây chỉ là hai cách gọi khác nhau của cùng một chỉ số",
        ],
        "correct": 0,
        "explanation": "Gross yield = Tiền thuê năm / Giá mua. Net yield = (Tiền thuê − Chi phí vận hành − Thuế) / Giá mua. Ví dụ: BĐS 3 tỷ, thuê 12M/tháng → Gross yield 4.8%, nhưng sau chi phí bảo trì + thuế + vacancy, Net yield chỉ còn 3–3.5%.",
        "topic": "nang_cao",
    },
    {
        "q": "Quỹ khẩn cấp (emergency fund) và Sinking fund (quỹ chìm) khác nhau như thế nào?",
        "options": [
            "Chúng giống nhau, chỉ là hai tên gọi khác nhau",
            "Emergency fund cho rủi ro bất ngờ, Sinking fund cho chi phí đã biết trong tương lai",
            "Emergency fund dùng tiền mặt, Sinking fund đầu tư vào cổ phiếu",
            "Emergency fund của cá nhân, Sinking fund chỉ dành cho doanh nghiệp",
        ],
        "correct": 1,
        "explanation": "Emergency fund: cho rủi ro bất ngờ (ốm đau, mất việc) — phải giữ tiền mặt, dễ rút. Sinking fund: dành cho chi phí lớn đã biết (mua xe, cưới hỏi, sửa nhà) — tích lũy dần theo kế hoạch. Nên có cả hai loại quỹ riêng biệt.",
        "topic": "nang_cao",
    },
    {
        "q": "Chỉ số Sharpe Ratio đo lường điều gì trong đầu tư?",
        "options": [
            "Tổng lợi nhuận tuyệt đối của danh mục",
            "Lợi nhuận vượt trội so với tài sản phi rủi ro, tính trên mỗi đơn vị rủi ro chịu đựng",
            "Tỷ lệ cổ tức so với giá cổ phiếu",
            "Mức độ tương quan giữa hai tài sản trong danh mục",
        ],
        "correct": 1,
        "explanation": "Sharpe Ratio = (Lợi nhuận danh mục − Lãi suất phi rủi ro) / Độ lệch chuẩn. Sharpe > 1 là tốt, > 2 là rất tốt. Dùng để so sánh hiệu quả đầu tư 'xứng đáng với rủi ro chịu đựng' — danh mục lãi 20% với rủi ro cao có thể kém hơn danh mục lãi 12% với rủi ro thấp.",
        "topic": "nang_cao",
    },
    {
        "q": "VN30 Index và VN-Index khác nhau như thế nào?",
        "options": [
            "VN30 chỉ tính 30 cổ phiếu vốn hóa lớn nhất và thanh khoản cao nhất trên HOSE",
            "VN30 bao gồm cả cổ phiếu trên HNX, VN-Index chỉ tính HOSE",
            "VN30 là chỉ số trái phiếu, VN-Index là chỉ số cổ phiếu",
            "Hoàn toàn giống nhau, chỉ khác tên gọi ở từng thời điểm",
        ],
        "correct": 0,
        "explanation": "VN-Index = toàn bộ cổ phiếu trên HOSE (500+ mã). VN30 = 30 mã vốn hóa lớn nhất + thanh khoản cao nhất HOSE, chiếm ~65–70% tổng vốn hóa toàn thị trường. VN30 đại diện tốt hơn cho cổ phiếu blue-chip VN và thường ít biến động hơn VN-Index.",
        "topic": "nang_cao",
    },

    # ── Câu hỏi mới: Tài chính cá nhân & Đầu tư thực tế ──────────────
    {
        "q": "Khi lạm phát tăng cao, loại tài sản nào thường giữ giá trị tốt nhất?",
        "options": [
            "Tiền mặt trong tài khoản ngân hàng",
            "Vàng, bất động sản, và cổ phiếu công ty có sức mạnh định giá",
            "Trái phiếu chính phủ ngắn hạn",
            "Hợp đồng bảo hiểm nhân thọ",
        ],
        "correct": 1,
        "explanation": "Khi lạm phát tăng, tiền mặt mất giá nhanh chóng. Vàng, BĐS và cổ phiếu của các công ty có thể tăng giá theo lạm phát, giúp bảo toàn sức mua. Đây gọi là 'hàng rào chống lạm phát' (inflation hedge).",
        "topic": "tong_hop",
    },
    {
        "q": "Yếu tố nào quan trọng NHẤT khi quyết định đầu tư vào một cổ phiếu?",
        "options": [
            "Giá cổ phiếu đang giảm mạnh nên có thể 'bắt đáy'",
            "Bạn bè hoặc người nổi tiếng khuyên mua",
            "Hiểu rõ mô hình kinh doanh, lợi thế cạnh tranh và định giá hợp lý",
            "Mã cổ phiếu dễ nhớ và có tên đẹp",
        ],
        "correct": 2,
        "explanation": "Đầu tư thông minh dựa trên hiểu biết về doanh nghiệp, không phải tin đồn hay cảm xúc. Warren Buffett gọi đây là 'Circle of Competence' — chỉ đầu tư vào thứ bạn thực sự hiểu.",
        "topic": "chung_khoan",
    },
    {
        "q": "Một nhà đầu tư mới nên phân bổ danh mục như thế nào?",
        "options": [
            "100% vào một cổ phiếu duy nhất đang 'hot'",
            "Đa dạng hóa: quỹ chỉ số ETF + trái phiếu + một phần tiền mặt",
            "Tất cả vào crypto vì lợi nhuận cao nhất",
            "Giữ toàn bộ tiền mặt chờ thị trường sụp đổ",
        ],
        "correct": 1,
        "explanation": "Đa dạng hóa (diversification) giúp giảm rủi ro mà không hy sinh quá nhiều lợi nhuận kỳ vọng. Nhà đầu tư mới nên bắt đầu với quỹ chỉ số ETF vì phí thấp, minh bạch và không cần kiến thức chuyên sâu.",
        "topic": "nang_cao",
    },
    {
        "q": "Tại sao đa số nhà đầu tư cá nhân thường thua lỗ trên thị trường chứng khoán?",
        "options": [
            "Vì thị trường chứng khoán là trò lừa đảo",
            "Vì mua đỉnh bán đáy do tâm lý FOMO và hoảng loạn",
            "Vì phải có bằng cấp tài chính mới đầu tư được",
            "Vì công ty môi giới luôn lừa khách hàng",
        ],
        "correct": 1,
        "explanation": "Nghiên cứu cho thấy nhà đầu tư cá nhân thường mua nhiều nhất khi thị trường đang ở đỉnh (FOMO) và bán tháo khi đáy (hoảng loạn). Đây là lý do 'mua và nắm giữ' (buy & hold) qua quỹ chỉ số thường hiệu quả hơn tự mua bán liên tục.",
        "topic": "chung_khoan",
    },
    {
        "q": "Lợi nhuận kép (compounding) thực sự phát huy sức mạnh nhờ yếu tố nào nhất?",
        "options": [
            "Số tiền đầu tư ban đầu phải thật lớn",
            "Phải chọn đúng cổ phiếu tăng gấp 10 lần",
            "Thời gian đầu tư càng dài càng tốt",
            "Phải giao dịch thường xuyên để bắt sóng",
        ],
        "correct": 2,
        "explanation": "Thời gian là yếu tố quan trọng nhất của lãi kép. Đầu tư 10 triệu với lãi 10%/năm sau 40 năm thành 452 triệu — nhưng sau 20 năm chỉ là 67 triệu. 20 năm cuối tạo ra phần lớn giá trị!",
        "topic": "lai_kep",
    },
    {
        "q": "Khi một công ty có tỷ lệ nợ/vốn chủ sở hữu (D/E ratio) rất cao, rủi ro lớn nhất là gì?",
        "options": [
            "Công ty sẽ bị đánh thuế cao hơn",
            "Công ty khó trả được nợ khi kinh doanh khó khăn, dễ phá sản",
            "Cổ phiếu không được phép giao dịch",
            "Lợi nhuận sẽ bị chia cho nhiều cổ đông hơn",
        ],
        "correct": 1,
        "explanation": "D/E cao = công ty vay nhiều. Trong thời kỳ suy thoái, doanh thu giảm nhưng vẫn phải trả lãi vay — có thể dẫn đến mất khả năng thanh toán và phá sản. Đây là lý do nên tránh cổ phiếu có D/E quá cao trong thị trường xấu.",
        "topic": "nang_cao",
    },
    {
        "q": "Dòng tiền tự do (Free Cash Flow - FCF) của một công ty cho biết điều gì?",
        "options": [
            "Tổng doanh thu của công ty trong năm",
            "Số tiền thực tế công ty tạo ra sau khi trừ chi phí đầu tư duy trì",
            "Số tiền công ty chi cho quảng cáo",
            "Mức lương trung bình của nhân viên",
        ],
        "correct": 1,
        "explanation": "FCF là tiền thực tế còn lại sau khi công ty đã chi tiêu để duy trì hoạt động. Warren Buffett gọi FCF là 'lợi nhuận của chủ sở hữu'. Công ty có FCF dương và tăng trưởng thường là khoản đầu tư tốt.",
        "topic": "chung_khoan",
    },
    {
        "q": "Nên làm gì khi thị trường chứng khoán giảm mạnh 20-30%?",
        "options": [
            "Bán hết để cắt lỗ ngay lập tức",
            "Tiếp tục đầu tư định kỳ theo kế hoạch DCA, thậm chí mua thêm nếu còn tiền nhàn rỗi",
            "Vay tiền để mua thêm vì giá rẻ",
            "Rút hết tiền gửi tiết kiệm và đổ vào chứng khoán",
        ],
        "correct": 1,
        "explanation": "Thị trường giảm là cơ hội mua vào với giá chiết khấu nếu bạn có tầm nhìn dài hạn. Duy trì DCA và không hoảng loạn là chìa khóa. Tuyệt đối không vay tiền đầu tư — rủi ro quá lớn.",
        "topic": "chung_khoan",
    },
    {
        "q": "Quỹ đầu tư chỉ số (Index Fund) có ưu điểm gì so với tự mua từng cổ phiếu?",
        "options": [
            "Phí quản lý thấp, đa dạng hóa ngay lập tức, không cần kiến thức chuyên sâu",
            "Đảm bảo không bao giờ lỗ vốn",
            "Lợi nhuận luôn cao hơn mọi quỹ chủ động",
            "Được miễn thuế hoàn toàn",
        ],
        "correct": 0,
        "explanation": "Index Fund như VN30 ETF hay S&P 500 ETF có phí quản lý cực thấp (~0.1-0.5%/năm), cho bạn sở hữu hàng trăm công ty chỉ với một giao dịch. Warren Buffett khuyên nhà đầu tư phổ thông nên mua Index Fund và nắm giữ dài hạn.",
        "topic": "nang_cao",
    },
    {
        "q": "Rủi ro lớn nhất khi đầu tư vào một công ty 'một sản phẩm' (single product company) là gì?",
        "options": [
            "Sản phẩm có thể bị lỗi thời hoặc bị cạnh tranh thay thế bất cứ lúc nào",
            "Công ty không thể niêm yết trên sàn chứng khoán",
            "Thuế của công ty sẽ cao hơn",
            "Cổ phiếu không được trả cổ tức",
        ],
        "correct": 0,
        "explanation": "Công ty phụ thuộc vào một sản phẩm duy nhất rất dễ bị tổn thương. Ví dụ: Kodak (phim ảnh) bị máy ảnh số thay thế, Nokia bị smartphone thay thế. Đa dạng hóa sản phẩm giúp công ty sống sót qua các thay đổi công nghệ.",
        "topic": "tong_hop",
    },
    {
        "q": "Khi lãi suất ngân hàng trung ương tăng, điều gì thường xảy ra với giá trái phiếu đang lưu hành?",
        "options": [
            "Giá trái phiếu tăng lên",
            "Giá trái phiếu giảm xuống",
            "Giá trái phiếu không thay đổi",
            "Trái phiếu bị thu hồi tự động",
        ],
        "correct": 1,
        "explanation": "Lãi suất và giá trái phiếu có mối quan hệ nghịch. Khi lãi suất mới cao hơn, trái phiếu cũ với lãi suất thấp trở nên kém hấp dẫn, giá giảm. Đây gọi là 'rủi ro lãi suất' (interest rate risk) của trái phiếu.",
        "topic": "nang_cao",
    },
    {
        "q": "Tại sao đa dạng hóa danh mục đầu tư quốc tế lại quan trọng?",
        "options": [
            "Vì ngoại tệ luôn tăng giá so với VND",
            "Để giảm rủi ro tập trung vào một nền kinh tế duy nhất",
            "Vì đầu tư nước ngoài được miễn thuế",
            "Vì chứng khoán nước ngoài luôn tăng giá",
        ],
        "correct": 1,
        "explanation": "Mỗi quốc gia có chu kỳ kinh tế riêng. Khi VN giảm, Mỹ hoặc Nhật có thể tăng. Đầu tư quốc tế giúp giảm rủi ro quốc gia (country risk). Quỹ ETF toàn cầu như VWRA là cách đơn giản để đa dạng hóa quốc tế.",
        "topic": "tong_hop",
    },
    {
        "q": "Yếu tố tâm lý 'neo đậu' (anchoring bias) ảnh hưởng đến quyết định đầu tư như thế nào?",
        "options": [
            "Nhà đầu tư chỉ mua cổ phiếu của các công ty có tên đẹp",
            "Nhà đầu tư bị ám ảnh bởi một mức giá cụ thể (ví dụ giá mua ban đầu) và khó bán lỗ",
            "Nhà đầu tư luôn mua khi thị trường giảm",
            "Nhà đầu tư chỉ theo dõi một cổ phiếu duy nhất",
        ],
        "correct": 1,
        "explanation": "Anchoring bias: nhà đầu tư 'neo' vào giá mua ban đầu. Mua ở giá 50, giờ còn 30, không chịu bán lỗ vì chờ về 50 — trong khi có thể giảm tiếp về 10. Đây là lý do nhiều nhà đầu tư ôm cổ phiếu giảm đến khi mất gần hết.",
        "topic": "tong_hop",
    },
    {
        "q": "Tỷ lệ chi trả cổ tức (Dividend Payout Ratio) cao có thể là dấu hiệu gì?",
        "options": [
            "Công ty rất mạnh, có nhiều tiền để chia cho cổ đông",
            "Công ty có ít cơ hội tái đầu tư sinh lời — có thể đang bão hòa",
            "Cổ phiếu sắp tăng giá mạnh",
            "Công ty sắp được mua lại",
        ],
        "correct": 1,
        "explanation": "Payout ratio > 80% có thể là dấu hiệu công ty không còn cơ hội tăng trưởng để tái đầu tư. Ngược lại, công ty tăng trưởng cao như Amazon thường không trả cổ tức mà tái đầu tư toàn bộ lợi nhuận.",
        "topic": "chung_khoan",
    },
    {
        "q": "Một người có 100 triệu VND nên bắt đầu đầu tư như thế nào cho an toàn và hiệu quả?",
        "options": [
            "Mua vàng và giữ trong két sắt",
            "Gửi tiết kiệm ngân hàng lãi suất 5-7%/năm",
            "Xây dựng quỹ khẩn cấp 3-6 tháng chi phí, sau đó đầu tư vào quỹ chỉ số ETF định kỳ",
            "Cho bạn bè vay lấy lãi cao",
        ],
        "correct": 2,
        "explanation": "Trước khi đầu tư, phải có quỹ khẩn cấp an toàn và thanh khoản. Sau đó, đầu tư định kỳ (DCA) vào quỹ chỉ số ETF là cách tiếp cận an toàn và hiệu quả cho người mới bắt đầu. Không nên bỏ tất cả trứng vào một giỏ.",
        "topic": "fire",
    },
    {
        "q": "Rủi ro thanh khoản (liquidity risk) là gì trong đầu tư?",
        "options": [
            "Rủi ro tài sản đầu tư khó bán nhanh được bằng giá trị thị trường",
            "Rủi ro mất tiền do lạm phát",
            "Rủi ro công ty môi giới phá sản",
            "Rủi ro bị đánh thuế khi bán tài sản",
        ],
        "correct": 0,
        "explanation": "Thanh khoản là khả năng bán tài sản nhanh chóng với giá sát thị trường. BĐS có thanh khoản thấp (mất nhiều tháng để bán), cổ phiếu blue-chip có thanh khoản cao (bán trong vài giây). Cần cân nhắc thanh khoản khi phân bổ tài sản.",
        "topic": "tong_hop",
    },
    {
        "q": "Tại sao không nên 'all-in' vào một kênh đầu tư duy nhất?",
        "options": [
            "Vì pháp luật không cho phép",
            "Vì rủi ro tập trung (concentration risk) — mất trắng nếu kênh đó sụp đổ",
            "Vì thuế sẽ cao hơn khi đầu tư một kênh",
            "Vì ngân hàng sẽ không cho vay nếu chỉ có một tài sản",
        ],
        "correct": 1,
        "explanation": "Rủi ro tập trung là rủi ro lớn nhất của nhà đầu tư thiếu kinh nghiệm. Dù kênh đầu tư có tốt đến đâu, luôn có rủi ro bất đối xứng. Phân bổ tài sản (asset allocation) là yếu tố quyết định 90% thành công đầu tư dài hạn.",
        "topic": "tong_hop",
    },
    {
        "q": "Nếu giá cổ phiếu giảm 50%, cần tăng bao nhiêu phần trăm để hòa vốn?",
        "options": [
            "50%",
            "75%",
            "100%",
            "150%",
        ],
        "correct": 2,
        "explanation": "Mất 50% — cần tăng 100% để quay lại giá ban đầu. Ví dụ: 100 → 50 (giảm 50%) → 100 (tăng 100%). Đây là lý do tại sao bảo toàn vốn quan trọng hơn kiếm lợi nhuận: 'Quy tắc số 1: Đừng để mất tiền. Quy tắc số 2: Đừng quên quy tắc số 1.'",
        "topic": "nang_cao",
    },
]


# ── Statistics ────────────────────────────────────────────────────

def get_quiz_stats() -> dict:
    """Trả về thống kê quiz hiện tại: {correct, total, streak, best_streak, accuracy}."""
    stats = cfg_dict(_KEY_QUIZ_STATS, {"correct": 0, "total": 0, "streak": 0, "best_streak": 0})
    total   = stats.get("total", 0)
    correct = stats.get("correct", 0)
    return {**stats, "accuracy": round(correct / total * 100) if total > 0 else 0}


def _save_stats(stats: dict):
    """Ghi thống kê quiz vào config."""
    cfg_set(_KEY_QUIZ_STATS, stats)


# ── Countdown timer (7:00 AM next day) ────────────────────────────

def get_next_reset_seconds() -> int:
    """
    Trả về số giây còn lại đến 7:00 sáng hôm sau (theo Unix timestamp).
    Dùng để hiển thị countdown timer khi đã đạt giới hạn 5 câu/ngày.
    """
    now = time.time()
    now_local = time.localtime(now)
    # Tạo timestamp cho 7:00 sáng hôm nay
    today_7am = time.mktime(time.struct_time((
        now_local.tm_year, now_local.tm_mon, now_local.tm_mday,
        7, 0, 0, now_local.tm_wday, now_local.tm_yday, now_local.tm_isdst
    )))
    if now < today_7am:
        # Trước 7:00 sáng nay → reset vào 7:00 sáng nay
        return int(today_7am - now)
    else:
        # Sau 7:00 sáng → reset vào 7:00 sáng mai
        tomorrow_7am = today_7am + 86400
        return int(tomorrow_7am - now)


# ── Quiz set management ──────────────────────────────────────────

def get_quiz_set(topic: str | None = None) -> list:
    """
    Tạo một bộ câu hỏi mới gồm QUIZ_SET_SIZE câu ngẫu nhiên từ pool.
    Nếu topic được chỉ định, chỉ lấy câu hỏi thuộc topic đó.
    Lưu vào config để duy trì trạng thái qua các lần load lại.
    Trả về list dict có key: q, options (đã trộn), explanation, topic, index (vị trí gốc).
    """
    pool = [q for q in QUIZ_POOL if topic is None or q.get("topic") == topic]
    if not pool:
        # Fallback: nếu không có câu nào cho topic, lấy toàn bộ pool
        pool = list(QUIZ_POOL)

    random.shuffle(pool)
    selected = pool[:QUIZ_SET_SIZE]

    quiz_set = []
    for item in selected:
        opts = list(item["options"])
        correct_label = opts[item["correct"]]
        random.shuffle(opts)
        new_correct = opts.index(correct_label)
        quiz_set.append({
            "q": item["q"],
            "options": opts,
            "correct": new_correct,
            "explanation": item["explanation"],
            "topic": item.get("topic", ""),
        })

    cfg_set(_KEY_QUIZ_SET_DATA, quiz_set)
    cfg_set(_KEY_QUIZ_SET_INDEX, 0)
    if topic is not None:
        cfg_set(_KEY_QUIZ_TOPIC, topic)

    return quiz_set


def get_current_quiz_set() -> list:
    """Trả về bộ câu hỏi hiện tại, hoặc tạo mới nếu chưa có."""
    data = cfg_list(_KEY_QUIZ_SET_DATA, [])
    if not data:
        return get_quiz_set()
    return data


def get_quiz_set_index() -> int:
    return cfg_int(_KEY_QUIZ_SET_INDEX, 0)


def _check_daily_limit() -> dict:
    """
    Kiểm tra và cập nhật daily limit.
    Trả về: {"allowed": bool, "count": int, "limit": int, "next_reset_seconds": int}
    """
    today = _today_key()
    if cfg_str(_KEY_DAILY_DATE, "") != today:
        # Ngày mới — reset counter
        cfg_set(_KEY_DAILY_DATE, today)
        cfg_set(_KEY_DAILY_COUNT, 0)
        daily_count = 0
    else:
        daily_count = cfg_int(_KEY_DAILY_COUNT, 0)

    allowed = daily_count < QUIZ_DAILY_LIMIT
    return {
        "allowed": allowed,
        "count": daily_count,
        "limit": QUIZ_DAILY_LIMIT,
        "next_reset_seconds": get_next_reset_seconds() if not allowed else 0,
    }


def record_quiz_answer(q_index: int, selected: int) -> dict:
    """
    Ghi nhận câu trả lời của người dùng.
    
    Args:
        q_index: chỉ số câu trong set (0-based)
        selected: đáp án người dùng chọn (0-based)
        
    Returns:
        dict: {correct: bool, explanation: str, bonus_awarded: bool,
               kn_awarded: int, daily_limit: dict, stats: dict}
    """
    # Kiểm tra daily limit trước
    limit_info = _check_daily_limit()
    if not limit_info["allowed"]:
        return {
            "error": "daily_limit_reached",
            "daily_limit": limit_info,
            "message": f"Bạn đã đạt giới hạn {QUIZ_DAILY_LIMIT} câu hỏi hôm nay. Hãy quay lại vào 7:00 sáng mai!",
        }

    quiz_set = get_current_quiz_set()
    stats = cfg_dict(_KEY_QUIZ_STATS, {"correct": 0, "total": 0, "streak": 0, "best_streak": 0})

    if q_index < 0 or q_index >= len(quiz_set):
        return {"error": "Invalid question index"}

    question = quiz_set[q_index]
    is_correct = (selected == question["correct"])

    # Cập nhật thống kê
    stats["total"] = stats.get("total", 0) + 1
    if is_correct:
        stats["correct"]      = stats.get("correct", 0) + 1
        stats["streak"]       = stats.get("streak", 0) + 1
        stats["best_streak"]  = max(stats.get("best_streak", 0), stats["streak"])
    else:
        stats["streak"] = 0

    _save_stats(stats)

    # Tăng daily count (cả đúng lẫn sai)
    daily_count = limit_info["count"] + 1
    cfg_set(_KEY_DAILY_COUNT, daily_count)

    # Cộng bonus + KN nếu đúng
    bonus_awarded = False
    kn_awarded = 0
    if is_correct:
        bonus_awarded = _give_bonus()
        # Thưởng KN ngẫu nhiên 15-20
        kn_awarded = random.randint(KN_PER_CORRECT_MIN, KN_PER_CORRECT_MAX)
        try:
            from .rank_system import add_kn
            add_kn(kn_awarded)
        except Exception as e:
            logger.debug("answer_question: add_kn — %s", e)
            kn_awarded = 0

    return {
        "correct": is_correct,
        "explanation": question["explanation"],
        "correct_answer": question["options"][question["correct"]],
        "bonus_awarded": bonus_awarded,
        "kn_awarded": kn_awarded,
        "stats": get_quiz_stats(),
        "daily_limit": {
            "count": daily_count,
            "limit": QUIZ_DAILY_LIMIT,
            "remaining": max(0, QUIZ_DAILY_LIMIT - daily_count),
            "next_reset_seconds": get_next_reset_seconds() if daily_count >= QUIZ_DAILY_LIMIT else 0,
        },
    }


def _today_key() -> str:
    """Trả về 'YYYY-MM-DD' dùng Unix timestamp, chống time travel."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time()))


def get_daily_quiz_info() -> dict:
    """Trả về {correct_today, count, limit, remaining, next_reset_seconds, date}
    cho UI hiển thị hạn mức ngày và countdown timer."""
    today = _today_key()
    if cfg_str(_KEY_DAILY_DATE, "") != today:
        return {
            "correct_today": 0,
            "count": 0,
            "limit": QUIZ_DAILY_LIMIT,
            "remaining": QUIZ_DAILY_LIMIT,
            "next_reset_seconds": 0,
            "date": today,
        }
    correct = cfg_int(_KEY_DAILY_CORRECT, 0)
    count = cfg_int(_KEY_DAILY_COUNT, 0)
    remaining = max(0, QUIZ_DAILY_LIMIT - count)
    return {
        "correct_today": correct,
        "count": count,
        "limit": QUIZ_DAILY_LIMIT,
        "remaining": remaining,
        "next_reset_seconds": get_next_reset_seconds() if remaining <= 0 else 0,
        "date": today,
    }


def _give_bonus() -> bool:
    """Cộng QUIZ_BONUS vào số dư ví nếu chưa đạt giới hạn ngày. Trả về True nếu thưởng."""
    if not col_ready():
        return False
    try:
        today = _today_key()
        if cfg_str(_KEY_DAILY_DATE, "") != today:
            cfg_set(_KEY_DAILY_DATE, today)
            cfg_set(_KEY_DAILY_CORRECT, 0)
        daily = cfg_int(_KEY_DAILY_CORRECT, 0)
        if daily >= QUIZ_DAILY_LIMIT:
            return False  # đã đạt giới hạn 5 câu đúng có thưởng/ngày
        cfg_set(_KEY_DAILY_CORRECT, daily + 1)

        from .balance import get_balance, set_balance
        from .transactions import add_transaction
        set_balance(get_balance() + QUIZ_BONUS)
        add_transaction("reward", QUIZ_BONUS,
                        f"🎓 Quiz tài chính — trả lời đúng +{QUIZ_BONUS:,}đ".replace(",", "."))
        return True
    except Exception as e:
        logger.warning("_give_bonus: %s", e)
        return False
