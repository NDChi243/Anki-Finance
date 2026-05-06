# -*- coding: utf-8 -*-
from aqt import mw
import uuid

from .logger import get_logger

logger = get_logger(__name__)

CONFIG_KEY_BUDGET           = "anki_tycoon_budget"
CONFIG_KEY_MONTHLY_SPENDING = "anki_tycoon_monthly_spending"
CONFIG_KEY_MONTHLY_INCOME   = "anki_tycoon_monthly_income"
CONFIG_KEY_LAST_MONTH_RESET = "anki_tycoon_last_month_reset"
CONFIG_KEY_MONEY_JARS       = "anki_tycoon_money_jars"

MAX_JARS = 6

JAR_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]


def _col_ready() -> bool:
    try:
        return mw is not None and mw.col is not None
    except Exception as e:
        logger.debug("_col_ready: %s", e)
        return False


def _cfg_int(key: str, default: int = 0) -> int:
    """Luôn trả về int, không bao giờ None."""
    if not _col_ready():
        return default
    try:
        v = mw.col.get_config(key, default)
        if v is None:
            return default
        return int(v)
    except Exception as e:
        logger.warning("_cfg_int(%s): %s", key, e)
        return default


def _cfg_str(key: str, default: str = "") -> str:
    if not _col_ready():
        return default
    try:
        v = mw.col.get_config(key, default)
        return str(v) if v is not None else default
    except Exception as e:
        logger.warning("_cfg_str(%s): %s", key, e)
        return default


def _cfg_set(key: str, val):
    if not _col_ready():
        return
    try:
        mw.col.set_config(key, val)
    except Exception as e:
        logger.warning("_cfg_set(%s): %s", key, e)


def get_budget() -> int:
    return _cfg_int(CONFIG_KEY_BUDGET, 0)

def set_budget(amount: int):
    _cfg_set(CONFIG_KEY_BUDGET, int(amount))

def get_monthly_spending() -> int:
    return _cfg_int(CONFIG_KEY_MONTHLY_SPENDING, 0)

def add_spending(amount: int):
    _cfg_set(CONFIG_KEY_MONTHLY_SPENDING, get_monthly_spending() + int(amount))

def get_monthly_income() -> int:
    return _cfg_int(CONFIG_KEY_MONTHLY_INCOME, 0)

def add_income(amount: int):
    _cfg_set(CONFIG_KEY_MONTHLY_INCOME, get_monthly_income() + int(amount))


def reset_monthly_if_needed() -> bool:
    if not _col_ready():
        return False
    from datetime import datetime
    current_month = datetime.now().strftime("%Y-%m")
    last = _cfg_str(CONFIG_KEY_LAST_MONTH_RESET, "")
    if last != current_month:
        # Thu thuế TNCN và thuế đất trước khi reset
        try:
            from .tax_system import collect_monthly_pit, collect_monthly_land_tax
            collect_monthly_pit()
            collect_monthly_land_tax()
        except Exception as e:
            logger.warning("reset_monthly_if_needed: %s", e)
        _cfg_set(CONFIG_KEY_MONTHLY_SPENDING, 0)
        _cfg_set(CONFIG_KEY_MONTHLY_INCOME, 0)
        _cfg_set(CONFIG_KEY_LAST_MONTH_RESET, current_month)
        return True
    return False


# ── Money Jars ─────────────────────────────────────────────────────

def get_money_jars() -> list:
    if not _col_ready():
        return []
    try:
        v = mw.col.get_config(CONFIG_KEY_MONEY_JARS, [])
        return v if isinstance(v, list) else []
    except Exception as e:
        logger.warning("get_money_jars: %s", e)
        return []


def save_money_jars(jars: list) -> None:
    if not _col_ready():
        return
    try:
        mw.col.set_config(CONFIG_KEY_MONEY_JARS, jars[:MAX_JARS])
    except Exception as e:
        logger.warning("save_money_jars: %s", e)


def save_money_jar(jar_data: dict) -> dict:
    """Tạo mới hoặc cập nhật 1 jar. jar_data phải có ít nhất 'name'."""
    try:
        jars = get_money_jars()
        jar_id = jar_data.get("id", "")
        if jar_id:
            for i, j in enumerate(jars):
                if j.get("id") == jar_id:
                    jars[i] = {**j, **jar_data}
                    save_money_jars(jars)
                    return {"ok": True, "jar": jars[i]}
            return {"ok": False, "error": "Không tìm thấy hộp"}
        else:
            if len(jars) >= MAX_JARS:
                return {"ok": False, "error": f"Tối đa {MAX_JARS} hộp"}
            new_jar = {
                "id":            str(uuid.uuid4())[:8],
                "name":          jar_data.get("name", "Hộp mới"),
                "emoji":         jar_data.get("emoji", "💰"),
                "target_type":   jar_data.get("target_type", "fixed"),
                "target_amount": int(jar_data.get("target_amount", 0)),
                "target_pct":    float(jar_data.get("target_pct", 0)),
                "color":         jar_data.get("color", JAR_COLORS[len(jars) % len(JAR_COLORS)]),
                "note":          jar_data.get("note", ""),
            }
            jars.append(new_jar)
            save_money_jars(jars)
            return {"ok": True, "jar": new_jar}
    except Exception as e:
        logger.error("save_money_jar: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}


def delete_money_jar(jar_id: str) -> dict:
    try:
        jars = get_money_jars()
        new_jars = [j for j in jars if j.get("id") != jar_id]
        if len(new_jars) == len(jars):
            return {"ok": False, "error": "Không tìm thấy hộp"}
        save_money_jars(new_jars)
        return {"ok": True}
    except Exception as e:
        logger.error("delete_money_jar: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}


def get_budget_status() -> dict:
    budget  = get_budget()   # đã là int, không bao giờ None
    spent   = get_monthly_spending()
    income  = get_monthly_income()
    # Lấy thông tin chi phí sinh hoạt từ transactions
    try:
        from .transactions import get_transactions_by_type
        living_txns = get_transactions_by_type("living_cost")
        living_cost_total = sum(int(t.get("amount", 0)) for t in living_txns)
    except Exception as e:
        logger.warning("get_budget_status: living_cost — %s", e)
        living_cost_total = 0
    if budget <= 0:
        return {"percent": 0, "warning": False, "remaining": 0,
                "spent": spent, "income": income, "budget": 0,
                "living_cost": living_cost_total}
    percent = (spent / budget) * 100
    return {"percent": min(percent, 100), "warning": percent >= 80,
            "remaining": budget - spent, "spent": spent,
            "income": income, "budget": budget,
            "living_cost": living_cost_total}
