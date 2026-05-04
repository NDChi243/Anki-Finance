# -*- coding: utf-8 -*-
"""
kn_perks.py — Hệ thống KN Perks (v1.1.5)
Cho phép người dùng dùng điểm Kiến Thức (KN) để mở khóa
các buff vĩnh viễn, giúp KN có giá trị sử dụng thực tế.
"""

from ._safe_config import cfg_get, cfg_set, col_ready
from .rank_system import get_kn, add_kn
from .logger import get_logger

logger = get_logger(__name__)

_KEY_UNLOCKED = "anki_tycoon_kn_perks_unlocked"  # list of perk ids

# ─── Định nghĩa các Perk ──────────────────────────────────────────

PERKS = [
    {
        "id": "xp_boost_1",
        "name": "Gia Tăng Kiến Thức",
        "emoji": "📚",
        "description": "Tăng vĩnh viễn +15% EXP nhận được khi review thẻ.",
        "kn_cost": 300,
        "effect": {"type": "xp_mult", "value": 0.15},
    },
    {
        "id": "income_boost_1",
        "name": "Đầu Tư Thông Minh",
        "emoji": "💡",
        "description": "Tăng vĩnh viễn +10% tiền thưởng nhận được khi review thẻ.",
        "kn_cost": 500,
        "effect": {"type": "reward_mult", "value": 0.10},
    },
    {
        "id": "tax_reduction_1",
        "name": "Ưu Đãi Thuế",
        "emoji": "🏛️",
        "description": "Giảm vĩnh viễn -5% thuế thu nhập hàng ngày.",
        "kn_cost": 800,
        "effect": {"type": "tax_reduction", "value": 0.05},
    },
    {
        "id": "interest_boost_1",
        "name": "Lãi Suất Cao",
        "emoji": "🏦",
        "description": "Tăng vĩnh viễn +5% lãi suất tiết kiệm không kỳ hạn.",
        "kn_cost": 1200,
        "effect": {"type": "interest_bonus", "value": 0.05},
    },
    {
        "id": "xp_boost_2",
        "name": "Học Tập Toàn Diện",
        "emoji": "🎓",
        "description": "Tăng vĩnh viễn +30% EXP nhận được khi review thẻ (cộng dồn với Gia Tăng Kiến Thức).",
        "kn_cost": 2000,
        "effect": {"type": "xp_mult", "value": 0.30},
    },
    {
        "id": "master_perk",
        "name": "Bậc Thầy Tri Thức",
        "emoji": "👑",
        "description": "Tăng vĩnh viễn +20% tiền thưởng và +20% EXP khi review thẻ.",
        "kn_cost": 5000,
        "effect": {"type": "master_bonus", "value": 0.20},
    },
]


# ─── API ───────────────────────────────────────────────────────────


def _get_unlocked() -> list:
    """Lấy danh sách perk id đã mở khóa."""
    return cfg_get(_KEY_UNLOCKED, [])


def _save_unlocked(ids: list):
    """Lưu danh sách perk id đã mở khóa."""
    cfg_set(_KEY_UNLOCKED, ids)


def get_all_perks() -> list:
    """Trả về danh sách tất cả perk kèm trạng thái đã mở khóa."""
    unlocked = set(_get_unlocked())
    kn = get_kn()
    result = []
    for p in PERKS:
        entry = dict(p)
        entry["unlocked"] = p["id"] in unlocked
        entry["can_afford"] = kn >= p["kn_cost"] if not entry["unlocked"] else False
        result.append(entry)
    return result


def unlock_perk(perk_id: str) -> dict:
    """Mở khóa 1 perk bằng KN. Trả về dict kết quả."""
    if not col_ready():
        return {"ok": False, "error": "Chưa sẵn sàng."}

    # Kiểm tra perk có tồn tại
    perk = None
    for p in PERKS:
        if p["id"] == perk_id:
            perk = p
            break
    if not perk:
        return {"ok": False, "error": "Perk không tồn tại."}

    unlocked = _get_unlocked()
    if perk_id in unlocked:
        return {"ok": False, "error": "Perk này đã được mở khóa rồi."}

    kn = get_kn()
    if kn < perk["kn_cost"]:
        return {
            "ok": False,
            "error": f"Không đủ KN. Cần {perk['kn_cost']} KN, bạn có {kn} KN.",
        }

    # Trừ KN
    add_kn(-perk["kn_cost"])
    # Lưu trạng thái
    unlocked.append(perk_id)
    _save_unlocked(unlocked)

    logger.info("🔓 Mở khóa perk '%s' (giá: %d KN)", perk["name"], perk["kn_cost"])

    return {
        "ok": True,
        "perk_id": perk_id,
        "perk_name": perk["name"],
        "kn_spent": perk["kn_cost"],
        "kn_remaining": get_kn(),
    }


def get_active_bonuses() -> dict:
    """Trả về tổng hợp tất cả bonus đang active từ các perk đã mở khóa."""
    unlocked = _get_unlocked()
    bonuses = {
        "xp_mult": 0.0,
        "reward_mult": 0.0,
        "tax_reduction": 0.0,
        "interest_bonus": 0.0,
    }

    for pid in unlocked:
        for p in PERKS:
            if p["id"] == pid:
                eff = p["effect"]
                etype = eff["type"]
                val = eff["value"]
                if etype == "master_bonus":
                    bonuses["xp_mult"] += val
                    bonuses["reward_mult"] += val
                elif etype in bonuses:
                    bonuses[etype] += val

    return bonuses


def get_kn_perks_summary() -> dict:
    """Trả về toàn bộ thông tin perks + KN hiện tại + bonus active."""
    return {
        "kn": get_kn(),
        "perks": get_all_perks(),
        "active_bonuses": get_active_bonuses(),
    }
