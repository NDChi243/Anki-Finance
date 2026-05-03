# -*- coding: utf-8 -*-
"""
conftest.py — pytest setup cho anki_finance tests.

Chiến lược:
1. Chèn mock module Anki/PyQt vào sys.modules TRƯỚC khi import bất kỳ anki_finance.*
2. Pre-mock gui subpackage để tránh PyQt5 cascade
3. Cung cấp fixture fake_config để patch _safe_config functions per-module

Cách dùng:
    def test_foo(fake_config):
        import anki_finance.my_module as mod
        store = fake_config(mod, {"anki_tycoon_balance": 5_000_000})
        result = mod.my_func()
        assert store["anki_tycoon_balance"] == expected
"""
from __future__ import annotations

import sys
import pathlib
from unittest.mock import MagicMock

# ── 1. Mock tất cả Anki + Qt modules TRƯỚC MỌI IMPORT ─────────────
_ANKI_STUBS = [
    "aqt", "aqt.qt", "aqt.utils", "aqt.gui_hooks",
    "aqt.webview", "aqt.theme", "aqt.editor",
    "anki", "anki.cards", "anki.collection", "anki.notes",
    "anki.hooks", "anki.utils", "anki.consts", "anki.sound",
    "PyQt5", "PyQt5.QtCore", "PyQt5.QtWidgets",
    "PyQt5.QtWebEngineWidgets", "PyQt5.QtGui", "PyQt5.QtNetwork",
]
for _stub in _ANKI_STUBS:
    if _stub not in sys.modules:
        sys.modules[_stub] = MagicMock()

# ── 2. Thêm thư mục addons21 vào sys.path ─────────────────────────
# __file__ = .../addons21/anki_finance/tests/conftest.py
_ADDONS21 = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_ADDONS21) not in sys.path:
    sys.path.insert(0, str(_ADDONS21))

# ── 3. Pre-mock GUI subpackage (tránh PyQt5 import cascade) ────────
for _gui_mod in [
    "anki_finance.gui",
    "anki_finance.gui.topbar",
    "anki_finance.gui.webview_window",
    "anki_finance.gui.web_bridge",
    "anki_finance.gui.image_manager",
]:
    if _gui_mod not in sys.modules:
        sys.modules[_gui_mod] = MagicMock()

import pytest


# ── 4. Fixture factory ─────────────────────────────────────────────

@pytest.fixture
def fake_config(monkeypatch):
    """
    Factory fixture: patch _safe_config functions trên một module
    bằng in-memory dict store.

    Trả về hàm _make(module, initial_store) → store dict.
    Mọi thay đổi trong store đều được lưu và có thể kiểm tra sau test.
    """
    def _make(module, initial: dict | None = None) -> dict:
        store: dict = dict(initial or {})

        def col_ready() -> bool:
            return True

        def cfg_int(key: str, default: int = 0) -> int:
            v = store.get(key)
            return int(v) if v is not None else default

        def cfg_str(key: str, default: str = "") -> str:
            v = store.get(key)
            return str(v) if v is not None else default

        def cfg_list(key: str, default: list | None = None) -> list:
            d = default if default is not None else []
            v = store.get(key)
            return list(v) if isinstance(v, list) else list(d)

        def cfg_dict(key: str, default: dict | None = None) -> dict:
            d = default if default is not None else {}
            v = store.get(key)
            return dict(v) if isinstance(v, dict) else dict(d)

        def cfg_set(key: str, val) -> None:
            store[key] = val

        def cfg_remove(key: str) -> None:
            store.pop(key, None)

        for name, fn in [
            ("col_ready", col_ready),
            ("cfg_int", cfg_int),
            ("cfg_str", cfg_str),
            ("cfg_list", cfg_list),
            ("cfg_dict", cfg_dict),
            ("cfg_set", cfg_set),
            ("cfg_remove", cfg_remove),
        ]:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, fn)

        return store

    return _make
