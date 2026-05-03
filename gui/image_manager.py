# -*- coding: utf-8 -*-
from __future__ import annotations
"""
image_manager.py
----------------
Map id sản phẩm → đường dẫn file ảnh trong assets/images/.
Hỗ trợ .jpg / .jpeg / .png / .webp / .gif
Nếu không tìm thấy ảnh → trả về None, UI sẽ fallback về emoji.
"""

import os

# Thư mục chứa ảnh: <addon_root>/assets/images/
_ADDON_ROOT   = os.path.dirname(os.path.dirname(__file__))   # lên 1 cấp từ gui/
_IMAGES_DIR   = os.path.join(_ADDON_ROOT, "assets", "images")
_EXTENSIONS   = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")

# Cache để không scan disk mỗi lần gọi
_cache: dict[str, str | None] = {}


def get_image_url(item_id: str) -> str | None:
    """
    Trả về URL dạng file:// để QWebEngineView load được.
    Trả về None nếu không tìm thấy ảnh.
    """
    if item_id in _cache:
        return _cache[item_id]

    for ext in _EXTENSIONS:
        path = os.path.join(_IMAGES_DIR, item_id + ext)
        if os.path.isfile(path):
            # Chuẩn hóa path separator cho mọi OS, encode thành file URL
            url = "file:///" + path.replace("\\", "/")
            _cache[item_id] = url
            return url

    _cache[item_id] = None
    return None


def clear_cache():
    """Gọi khi user thêm ảnh mới mà không restart Anki."""
    _cache.clear()


def get_images_dir() -> str:
    """Trả về đường dẫn thư mục ảnh để hiển thị trong UI."""
    return _IMAGES_DIR


def list_available_images() -> dict[str, str]:
    """Trả về dict {item_id: file_path} của tất cả ảnh hiện có."""
    result = {}
    if not os.path.isdir(_IMAGES_DIR):
        return result
    for fname in os.listdir(_IMAGES_DIR):
        name, ext = os.path.splitext(fname)
        if ext.lower() in _EXTENSIONS:
            result[name] = os.path.join(_IMAGES_DIR, fname)
    return result
