# -*- coding: utf-8 -*-
from __future__ import annotations
from functools import lru_cache
"""
rank_system.py — Hệ thống cấp bậc Anki Finance Tycoon.

Điều kiện lên rank: ĐẠT ĐỦ CẢ BA:
   1. XP tích lũy >= xp_required
   2. Balance hiện tại >= balance_required
   3. Điểm Kiến Thức (KN) >= kn_required (từ Nhà Đầu tư trở lên)

Cấu trúc rank: 8 nhóm × 1-4 cấp = 23 ranks.
   Học giả → Chuyên viên → Nhà Đầu tư → Doanh nhân →
   Triệu phú → Tỷ phú → Bậc thầy Tài chính → Huyền thoại.

Lưu ý: Người chơi được cấp 10M VND + nhà trọ ban đầu,
      nên yêu cầu balance được thiết kế cao dần từ đó.

⚠️  ID giữ nguyên (sv*, nlc*, tt*, dn*, tp*, typh*, mstc*, hl*) để
    backward-compat với credit_banking, achievements, và config đã lưu.
"""

from ._safe_config import col_ready, cfg_dict, cfg_set, cfg_int

_KEY_XP   = "anki_tycoon_xp"
_KEY_KN   = "anki_tycoon_kn_points"
_KEY_RANK = "anki_tycoon_rank"

# Tracking lượng XP người chơi đã kiếm được khi ở từng mode (lũy kế).
# Dùng để tính tỷ lệ % Simple/Full đóng góp vào mỗi rank đã đạt.
_KEY_XP_EARNED_SIMPLE = "anki_tycoon_xp_earned_simple"
_KEY_XP_EARNED_FULL   = "anki_tycoon_xp_earned_full"
# Snapshot tại mỗi lần lên rank: {rank_id: {simple_xp, full_xp, achieved_at}}
_KEY_RANK_HISTORY     = "anki_tycoon_rank_history"
# Mốc XP earned (per mode) tại lần snapshot rank gần nhất → để tính delta
_KEY_RANK_HIST_CURSOR = "anki_tycoon_rank_history_cursor"

# ── Bảng rank ─────────────────────────────────────────────────────
# (id, label, xp_required, balance_required, kn_required, emoji, color_hex, group)
# Rebalance v1.2: thresholds rank cao (typh/mstc/hl) giảm ~10-15%
# để late-game khả thi hơn. Rank thấp giữ nguyên (không phá nhịp người chơi cũ).
RANKS = [
    # ── Học giả (sv1-3) — onboarding tier ──
    {"id":"sv1","label":"Tân Học giả",       "xp":0,        "bal":0,          "kn":0,   "emoji":"📖","color":"#94a3b8","group":"Học giả"},
    {"id":"sv2","label":"Học giả",           "xp":200,      "bal":10_000_000, "kn":0,   "emoji":"🎓","color":"#94a3b8","group":"Học giả"},
    {"id":"sv3","label":"Học giả Tinh nhuệ", "xp":500,      "bal":20_000_000, "kn":0,   "emoji":"🧠","color":"#cbd5e1","group":"Học giả"},

    # ── Chuyên viên (nlc1-3) — corporate tier ──
    {"id":"nlc1","label":"Chuyên viên Tập sự",   "xp":1_000,  "bal":50_000_000,  "kn":0,    "emoji":"👔","color":"#f59e0b","group":"Chuyên viên"},
    {"id":"nlc2","label":"Chuyên viên Tài chính","xp":2_500,  "bal":100_000_000, "kn":0,    "emoji":"💼","color":"#f59e0b","group":"Chuyên viên"},
    {"id":"nlc3","label":"Chuyên viên Cao cấp",  "xp":5_000,  "bal":250_000_000, "kn":0,    "emoji":"🏛️","color":"#fbbf24","group":"Chuyên viên"},

    # ── Nhà Đầu tư (tt1-3) — investor tier ──
    {"id":"tt1","label":"Nhà Đầu tư Cá nhân",  "xp":10_000, "bal":500_000_000,   "kn":1_000,  "emoji":"📊","color":"#10b981","group":"Nhà Đầu tư"},
    {"id":"tt2","label":"Trader Chuyên nghiệp","xp":20_000, "bal":1_000_000_000, "kn":2_500,  "emoji":"📈","color":"#10b981","group":"Nhà Đầu tư"},
    {"id":"tt3","label":"Portfolio Manager",   "xp":35_000, "bal":2_000_000_000, "kn":5_000,  "emoji":"💹","color":"#34d399","group":"Nhà Đầu tư"},

    # ── Doanh nhân (dn1-4) — entrepreneur tier ──
    {"id":"dn1","label":"Founder",            "xp":50_000,  "bal":5_000_000_000,    "kn":10_000, "emoji":"🚀","color":"#3b82f6","group":"Doanh nhân"},
    {"id":"dn2","label":"CEO",                "xp":80_000,  "bal":10_000_000_000,   "kn":20_000, "emoji":"🏢","color":"#3b82f6","group":"Doanh nhân"},
    {"id":"dn3","label":"Quản lý Quỹ Đầu tư", "xp":115_000, "bal":18_000_000_000,   "kn":38_000, "emoji":"🏛️","color":"#60a5fa","group":"Doanh nhân"},
    {"id":"dn4","label":"Cá Mập Phố Wall",    "xp":160_000, "bal":45_000_000_000,   "kn":65_000, "emoji":"🦈","color":"#60a5fa","group":"Doanh nhân"},

    # ── Triệu phú (tp1-3) — millionaire tier ──
    {"id":"tp1","label":"Triệu phú",         "xp":230_000, "bal":90_000_000_000,   "kn":110_000, "emoji":"💎","color":"#a855f7","group":"Triệu phú"},
    {"id":"tp2","label":"Triệu phú Tinh hoa","xp":360_000, "bal":180_000_000_000,  "kn":180_000, "emoji":"👑","color":"#a855f7","group":"Triệu phú"},
    {"id":"tp3","label":"Mogul Tài chính",   "xp":540_000, "bal":450_000_000_000,  "kn":320_000, "emoji":"🏆","color":"#c084fc","group":"Triệu phú"},

    # ── Tỷ phú (typh1-3) — billionaire tier ──
    {"id":"typh1","label":"Tỷ phú",          "xp":800_000,   "bal":900_000_000_000,    "kn":540_000,   "emoji":"🌟","color":"#ec4899","group":"Tỷ phú"},
    {"id":"typh2","label":"Tycoon",          "xp":1_300_000, "bal":1_800_000_000_000,  "kn":880_000,   "emoji":"🌙","color":"#f472b6","group":"Tỷ phú"},
    {"id":"typh3","label":"Oracle Tài chính","xp":2_200_000, "bal":4_400_000_000_000,  "kn":1_550_000, "emoji":"⭐","color":"#fbbf24","group":"Tỷ phú"},

    # ── Bậc thầy Tài chính (mstc1-3) — financial master tier ──
    {"id":"mstc1","label":"Bậc thầy Vốn hóa",   "xp":3_500_000, "bal":9_000_000_000_000,  "kn":2_600_000, "emoji":"🎯","color":"#f43f5e","group":"Bậc thầy Tài chính"},
    {"id":"mstc2","label":"Bậc thầy Phái sinh", "xp":5_400_000, "bal":17_000_000_000_000, "kn":4_400_000, "emoji":"💠","color":"#f43f5e","group":"Bậc thầy Tài chính"},
    {"id":"mstc3","label":"Hiền triết Phố Wall","xp":9_000_000, "bal":42_000_000_000_000, "kn":7_000_000, "emoji":"🔮","color":"#fb7185","group":"Bậc thầy Tài chính"},

    # ── Huyền thoại (hl1) — endgame max rank ──
    {"id":"hl1","label":"Huyền thoại Anki — Compounding Sage","xp":17_000_000, "bal":85_000_000_000_000, "kn":12_500_000, "emoji":"👑","color":"#fbbf24","group":"Huyền thoại"},
]

# XP per ease (base, trước boost)
_RANK_IDS = [r["id"] for r in RANKS]
_RANK_INDEX = {rank_id: idx for idx, rank_id in enumerate(_RANK_IDS)}

XP_PER_EASE = {1: 2, 2: 8, 3: 15, 4: 25}


# ── XP API ────────────────────────────────────────────────────────

def get_xp() -> int:
    return cfg_int(_KEY_XP, 0)

def _get_current_mode() -> str:
    try:
        from ._safe_config import cfg_str
        from .config import CONFIG_KEY_GAME_MODE, DEFAULT_GAME_MODE
        return cfg_str(CONFIG_KEY_GAME_MODE, DEFAULT_GAME_MODE)
    except Exception:
        return "full"

def add_xp(amount: int) -> None:
    if not col_ready(): return
    amt = int(amount)
    cfg_set(_KEY_XP, get_xp() + amt)
    if amt > 0:
        # Track XP đóng góp theo mode hiện tại
        if _get_current_mode() == "simple":
            cfg_set(_KEY_XP_EARNED_SIMPLE, cfg_int(_KEY_XP_EARNED_SIMPLE, 0) + amt)
        else:
            cfg_set(_KEY_XP_EARNED_FULL, cfg_int(_KEY_XP_EARNED_FULL, 0) + amt)

def get_xp_for_ease(ease: int) -> int:
    return XP_PER_EASE.get(ease, 0)


# ── KN (Kiến Thức) API ───────────────────────────────────────────

def get_kn() -> int:
    """Lấy điểm Kiến Thức hiện tại."""
    kn = cfg_int(_KEY_KN, 0)
    if kn == 0:
        # Backward compatibility: đọc từ key cũ nếu chưa migrate
        # ⚠️ LƯU Ý: key "anki_tycoon_knowledge" hiện được knowledge_base.py dùng
        # để lưu LIST các note, KHÔNG phải số nguyên như trước đây.
        # Nếu đọc ra list thì bỏ qua, không migrate.
        _OLD_KEY = "anki_tycoon_knowledge"
        try:
            old_kn = cfg_int(_OLD_KEY, 0)
            if isinstance(old_kn, int) and old_kn > 0:
                # Migrate sang key mới (chỉ đọc, không xoá key cũ vì knowledge_base đang dùng)
                cfg_set(_KEY_KN, old_kn)
                kn = old_kn
        except Exception:
            pass
    return kn

def add_kn(amount: int) -> None:
    """Cộng điểm Kiến Thức."""
    if not col_ready(): return
    cfg_set(_KEY_KN, get_kn() + int(amount))


# ── Rank logic ────────────────────────────────────────────────────

def _calc_rank(xp: int, balance: int, kn: int = 0) -> dict:
    """Tính rank hiện tại dựa trên xp + balance + kn."""
    current = RANKS[0]
    for r in RANKS:
        kn_req = r.get("kn", 0)
        if xp >= r["xp"] and balance >= r["bal"] and kn >= kn_req:
            current = r
        else:
            break
    return current

_calc_rank = lru_cache(maxsize=512)(_calc_rank)

def _next_rank(current_id: str) -> dict | None:
    idx = _RANK_INDEX.get(current_id)
    if idx is None: return None
    return RANKS[idx + 1] if idx + 1 < len(RANKS) else None


def get_rank_status(balance: int | None = None) -> dict:
    """
    Trả về toàn bộ thông tin rank hiện tại + progress lên rank tiếp theo.
    Bao gồm cả điểm Kiến Thức (KN) và tỷ lệ % Simple/Full đóng góp.
    """
    if not col_ready():
        return _empty_status()

    from .balance import get_balance as _get_bal
    if balance is None:
        balance = _get_bal()

    xp      = get_xp()
    kn      = get_kn()
    current = _calc_rank(xp, balance, kn)
    nxt     = _next_rank(current["id"])

    # Progress tới rank tiếp theo
    xp_pct  = 0.0
    bal_pct = 0.0
    kn_pct  = 0.0
    if nxt:
        xp_pct  = min(100.0, xp  / nxt["xp"]  * 100) if nxt["xp"]  > 0 else 100.0
        bal_pct = min(100.0, balance / nxt["bal"] * 100) if nxt["bal"] > 0 else 100.0
        kn_req  = nxt.get("kn", 0)
        kn_pct  = min(100.0, kn / kn_req * 100) if kn_req > 0 else 100.0
        if kn_req > 0:
            overall_pct = min(xp_pct, bal_pct, kn_pct)   # phải đủ CẢ BA
        else:
            overall_pct = min(xp_pct, bal_pct)            # phải đủ CẢ HAI
    else:
        kn_pct = 100.0
        overall_pct = 100.0

    # Overall Simple/Full contribution (tổng XP kiếm được từ mỗi mode)
    total_simple = cfg_int(_KEY_XP_EARNED_SIMPLE, 0)
    total_full   = cfg_int(_KEY_XP_EARNED_FULL, 0)
    total_both   = total_simple + total_full
    simple_pct   = round(total_simple / total_both * 100, 1) if total_both > 0 else 0.0
    full_pct     = round(total_full / total_both * 100, 1) if total_both > 0 else 0.0

    return {
        "xp":           xp,
        "kn":           kn,
        "rank_id":      current["id"],
        "rank_label":   current["label"],
        "rank_emoji":   current["emoji"],
        "rank_color":   current["color"],
        "rank_group":   current["group"],
        "next_rank":    nxt,
        "xp_pct":       round(xp_pct, 1),
        "bal_pct":      round(bal_pct, 1),
        "kn_pct":       round(kn_pct, 1),
        "overall_pct":  round(overall_pct, 1),
        "xp_needed":    max(0, nxt["xp"] - xp) if nxt else 0,
        "bal_needed":   max(0, nxt["bal"] - balance) if nxt else 0,
        "kn_needed":    max(0, nxt.get("kn", 0) - kn) if nxt else 0,
        "is_max":       nxt is None,
        "simple_pct":   simple_pct,
        "full_pct":     full_pct,
    }

def _empty_status() -> dict:
    r = RANKS[0]
    return {"xp":0,"kn":0,"rank_id":r["id"],"rank_label":r["label"],
            "rank_emoji":r["emoji"],"rank_color":r["color"],
            "rank_group":r["group"],"next_rank":RANKS[1],
            "xp_pct":0,"bal_pct":0,"kn_pct":0,"overall_pct":0,
            "xp_needed":RANKS[1]["xp"],"bal_needed":RANKS[1]["bal"],"kn_needed":RANKS[1].get("kn",0),"is_max":False,
            "simple_pct":0.0,"full_pct":0.0}

def get_all_ranks() -> list:
    return RANKS


# ── Rank contribution tracking (% Simple / Full) ──────────────────

def get_rank_history() -> dict:
    """Trả về dict: {rank_id: {simple_xp, full_xp, achieved_at, simple_pct, full_pct}}."""
    if not col_ready(): return {}
    raw = cfg_dict(_KEY_RANK_HISTORY, {})
    out = {}
    for rid, snap in raw.items():
        if not isinstance(snap, dict):
            continue
        s = int(snap.get("simple_xp", 0) or 0)
        f = int(snap.get("full_xp", 0) or 0)
        total = s + f
        out[rid] = {
            "simple_xp":   s,
            "full_xp":     f,
            "achieved_at": snap.get("achieved_at", ""),
            "simple_pct":  round(s / total * 100, 1) if total > 0 else 0.0,
            "full_pct":    round(f / total * 100, 1) if total > 0 else 0.0,
        }
    return out


def snapshot_rank_if_changed(new_rank_id: str) -> dict | None:
    """
    Gọi mỗi khi phát hiện rank up. Snapshot delta XP (simple/full) từ rank trước
    đến rank mới. Idempotent: nếu rank này đã snapshot rồi thì bỏ qua.
    Trả về snapshot vừa tạo, hoặc None nếu không tạo gì.
    """
    if not col_ready(): return None
    history = cfg_dict(_KEY_RANK_HISTORY, {})
    if new_rank_id in history:
        return None

    earned_simple = cfg_int(_KEY_XP_EARNED_SIMPLE, 0)
    earned_full   = cfg_int(_KEY_XP_EARNED_FULL, 0)
    cursor        = cfg_dict(_KEY_RANK_HIST_CURSOR, {"simple": 0, "full": 0})

    delta_simple = max(0, earned_simple - int(cursor.get("simple", 0) or 0))
    delta_full   = max(0, earned_full   - int(cursor.get("full",   0) or 0))

    import time
    snap = {
        "simple_xp":   delta_simple,
        "full_xp":     delta_full,
        "achieved_at": time.strftime("%Y-%m-%d", time.localtime(time.time())),
    }
    history[new_rank_id] = snap
    cfg_set(_KEY_RANK_HISTORY, history)
    cfg_set(_KEY_RANK_HIST_CURSOR, {"simple": earned_simple, "full": earned_full})
    return snap


def reset_rank_contribution_for_mode(mode: str) -> None:
    """Reset XP contribution counter của 1 mode (dùng khi reset mode đó)."""
    if not col_ready(): return
    if mode == "simple":
        cfg_set(_KEY_XP_EARNED_SIMPLE, 0)
    elif mode == "full":
        cfg_set(_KEY_XP_EARNED_FULL, 0)
    # Cập nhật lại cursor để đoạn delta tiếp theo không âm
    cursor = cfg_dict(_KEY_RANK_HIST_CURSOR, {"simple": 0, "full": 0})
    if mode == "simple":
        cursor["simple"] = 0
    elif mode == "full":
        cursor["full"] = 0
    cfg_set(_KEY_RANK_HIST_CURSOR, cursor)
