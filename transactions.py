# -*- coding: utf-8 -*-
from __future__ import annotations
from .logger import get_logger
logger = get_logger(__name__)
"""
transactions.py — Hệ thống ghi nhận lịch sử giao dịch tập trung.

Tất cả loại giao dịch được hỗ trợ:
- purchase:     Mua hàng từ shop
- reward:       Thưởng học tập
- interest:     Lãi ngân hàng
- penalty:      Phạt Again
- stock_buy:    Mua cổ phiếu
- stock_sell:   Bán cổ phiếu
- crypto_buy:   Mua crypto
- crypto_sell:  Bán crypto
- crypto_stake: Stake crypto
- crypto_unstake: Unstake crypto
- staking_yield: Lợi nhuận staking
- tax:          Thuế tài sản
- pit_tax:      Thuế TNCN (PIT)
- sct_tax:      Thuế tiêu thụ đặc biệt (SCT)
- land_tax:     Thuế đất
- transfer_tax:    Thuế chuyển nhượng
- pit_withholding: Khấu trừ tạm thời thuế TNCN (ngay khi nhận thưởng)
- pit_refund:      Hoàn thuế TNCN cuối tháng (quyết toán)
- rent_income:     Thu nhập từ cho thuê BĐS
- living_cost:  Chi phí sinh hoạt
- bank_deposit: Gửi tiền ngân hàng
- bank_withdraw: Rút tiền ngân hàng
- deposit:      Gửi tiết kiệm có kỳ hạn
- withdraw:     Rút tiết kiệm có kỳ hạn
- loan:         Vay nóng
- loan_borrow:  Vay nóng (alias)
- loan_repay:   Trả nợ vay
- loan_interest: Lãi vay nóng
- debug:        Gỡ lỗi
"""

from datetime import datetime
from ._safe_config import col_ready, cfg_list, cfg_set

CONFIG_KEY_TRANSACTIONS = "anki_tycoon_transactions"
MAX_TRANSACTIONS = 300  # Tăng từ 100 lên 300 để lưu nhiều giao dịch hơn

# Danh sách type là spending (tiêu tiền)
SPENDING_TYPES = {
    "purchase", "stock_buy", "crypto_buy",
    "tax", "pit_tax", "sct_tax", "land_tax", "transfer_tax",
    "pit_withholding",
    "living_cost", "bank_deposit", "deposit",
    "loan_repay", "loan_interest", "penalty",
    "emergency",
}

# Danh sách type là income (kiếm tiền)
INCOME_TYPES = {
    "reward", "interest",
    "stock_sell", "crypto_sell", "crypto_unstake", "staking_yield",
    "rent_income", "bank_withdraw", "withdraw",
    "loan", "loan_borrow",
    "pit_refund",
}


def get_transactions() -> list:
    """Lấy toàn bộ lịch sử giao dịch."""
    return cfg_list(CONFIG_KEY_TRANSACTIONS, [])


def add_transaction(txn_type: str, amount: int, description: str, metadata: dict | None = None) -> None:
    """
    Ghi một giao dịch mới vào lịch sử.

    Args:
        txn_type: Loại giao dịch (purchase, reward, stock_buy, ...)
        amount: Số tiền (số dương)
        description: Mô tả giao dịch
        metadata: Dict chứa thông tin bổ sung (symbol, shares, ...)
    """
    if not col_ready():
        return
    try:
        transactions = get_transactions()
        now = datetime.now()
        transactions.insert(0, {
            "type":        txn_type,
            "amount":      int(amount),
            "description": description,
            "timestamp":   now.isoformat(),
            "date":        now.strftime("%d/%m %H:%M"),
            "metadata":    metadata or {},
        })
        if len(transactions) > MAX_TRANSACTIONS:
            transactions = transactions[:MAX_TRANSACTIONS]
        cfg_set(CONFIG_KEY_TRANSACTIONS, transactions)

        # Cập nhật thống kê thu/chi cho finance.py
        from .finance import add_spending, add_income
        if txn_type in SPENDING_TYPES:
            add_spending(int(amount))
        elif txn_type in INCOME_TYPES:
            add_income(int(amount))
    except Exception as e:
        logger.debug("add_transaction: finance stats — %s", e)


def clear_transactions() -> None:
    """Xoá toàn bộ lịch sử giao dịch."""
    cfg_set(CONFIG_KEY_TRANSACTIONS, [])


def get_transactions_by_type(txn_type: str) -> list:
    """Lọc giao dịch theo loại."""
    transactions = get_transactions()
    return [t for t in transactions if t.get("type") == txn_type]


def get_transactions_by_date(date_str: str) -> list:
    """Lọc giao dịch theo ngày (định dạng DD/MM)."""
    transactions = get_transactions()
    return [t for t in transactions if t.get("date", "").startswith(date_str)]


def get_transaction_summary() -> dict:
    """
    Tổng hợp thu/chi theo từng loại giao dịch.
    Trả về: {total_spending, total_income, by_type: {type: {spending, income, count}}}
    """
    transactions = get_transactions()
    by_type = {}
    total_spending = 0
    total_income = 0

    for t in transactions:
        txn_type = t.get("type", "unknown")
        amount = int(t.get("amount", 0))

        if txn_type not in by_type:
            by_type[txn_type] = {"spending": 0, "income": 0, "count": 0}

        by_type[txn_type]["count"] += 1

        if txn_type in SPENDING_TYPES:
            by_type[txn_type]["spending"] += amount
            total_spending += amount
        elif txn_type in INCOME_TYPES:
            by_type[txn_type]["income"] += amount
            total_income += amount

    return {
        "total_spending": total_spending,
        "total_income": total_income,
        "net": total_income - total_spending,
        "by_type": by_type,
    }
