# -*- coding: utf-8 -*-
from __future__ import annotations
"""
auto_update.py — Tự động kiểm tra & cập nhật add-on từ GitHub (branch main).

Cách hoạt động:
  1. Khi Anki khởi động, chạy 1 thread nền fetch version.json từ branch main.
  2. So sánh với version hiện tại.
  3. Nếu mới hơn → tải ZIP của branch main → giải nén đè → thông báo restart.

Để phát hành bản mới: chỉ cần tăng "version" trong version.json rồi push lên main.
Không cần tạo GitHub Release.
"""

import os
import json
import time
import threading
import traceback
import zipfile
import io
import shutil
import subprocess
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError

from .logger import get_logger
logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════
# CẤU HÌNH — chỉ sửa 2 dòng này
# ═══════════════════════════════════════════════════════════════
GITHUB_USER = "NDChi243"
GITHUB_REPO = "Anki-Finance"

# Nội bộ
_ADDON_DIR            = os.path.dirname(os.path.abspath(__file__))
_VERSION_FILE         = os.path.join(_ADDON_DIR, "version.json")
_STATE_FILE           = os.path.join(_ADDON_DIR, "_update_state.json")
_UPDATE_CHECK_INTERVAL_SECONDS = 3    # ⚡ Kiểm tra mỗi 3 giây (trước: 60s) — user muốn cập nhật NGAY LẬP TỨC
_DOWNLOAD_RETRIES              = 3
_VERSION_CHECK_TIMEOUT         = 5
_DOWNLOAD_TIMEOUT              = 60

# ═══════════════════════════════════════════════════════════════
# TỰ ĐỘNG PHÁT HIỆN BRANCH — fallback về "main" nếu không phải git repo
# ═══════════════════════════════════════════════════════════════
_GIT_BRANCH: str | None = None   # cache sau lần gọi đầu

def _detect_git_branch() -> str:
    """
    Đọc branch git hiện tại bằng `git rev-parse --abbrev-ref HEAD`.
    Nếu không phải git repo hoặc lỗi → fallback về "main".
    Kết quả được cache để tránh gọi subprocess nhiều lần.
    """
    global _GIT_BRANCH
    if _GIT_BRANCH is not None:
        return _GIT_BRANCH

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True,
            cwd=_ADDON_DIR, timeout=5
        )
        branch = result.stdout.strip()
        if branch and result.returncode == 0:
            _GIT_BRANCH = branch
            _log(f"🔀 Phát hiện branch: {branch}")
            return branch
    except Exception as e:
        logger.debug("_detect_git_branch: không xác định được branch: %s", e)

    _GIT_BRANCH = "main"
    _log("ℹ️ Không phát hiện git repo, dùng branch 'main' làm mặc định.")
    return "main"

# Trạng thái toàn cục
_UPDATE_AVAILABLE = False
_PENDING_INFO     = None   # {"local": str, "latest": str, "changelog": str}
_DOWNLOADING      = False
_APPLIED          = False
_PENDING_RESTART  = False


# ── Helpers ──────────────────────────────────────────────────────

def _log(msg: str):
    logger.info(msg)


def _parse_version(v: str) -> tuple:
    """
    '1.2.3'   → (1, 2, 3, 0)
    '1.2.3.4' → (1, 2, 3, 4)   ← build number
    '1.2.3a'  → (1, 2, 3, 1)   ← a=1, b=2, c=3 ...
    '1.2.3b'  → (1, 2, 3, 2)
    """
    try:
        s = v.strip().lstrip("v").split("-")[0]
        # Tách phần chữ cái ở cuối: "1.0.7c" → numeric="1.0.7", letter="c"
        i = len(s)
        while i > 0 and s[i - 1].isalpha():
            i -= 1
        letter = s[i:].lower()
        numeric = s[:i]
        parts = numeric.strip(".").split(".")
        nums = []
        for p in parts:
            try:
                nums.append(int(p))
            except ValueError:
                nums.append(0)
        # Chuyển chữ cái thành số build: a→1, b→2, c→3 …
        if letter:
            nums.append(ord(letter[0]) - ord("a") + 1)
        while len(nums) < 4:
            nums.append(0)
        return tuple(nums[:4])
    except Exception as e:
        logger.warning("_parse_version: lỗi parse version '%s': %s", v, e)
        return (0, 0, 0, 0)


# ── File-based state (thread-safe, không cần mw.col) ─────────────
# Dùng file JSON thay vì Anki config để tránh threading issues.

def _read_state() -> dict:
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.debug("_read_state: chưa có file state, trả về dict rỗng")
        return {}


def _write_state(**kwargs):
    try:
        state = _read_state()
        for k, v in kwargs.items():
            if v is None:
                state.pop(k, None)
            else:
                state[k] = v
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        _log(f"⚠️ Không ghi được state: {e}")


def _read_local_version_file() -> str:
    try:
        with open(_VERSION_FILE, "r", encoding="utf-8") as f:
            return str(json.load(f).get("version", "0.0.0"))
    except Exception:
        logger.debug("_read_local_version_file: chưa có file version, trả về 0.0.0")
        return "0.0.0"


def _get_local_version() -> str:
    """
    Trả về version đang chạy.
    Ưu tiên: state file > version.json.
    Nếu version.json mới hơn (cài tay), tự đồng bộ lại state file.
    """
    state = _read_state()
    state_ver = state.get("version", "")
    file_ver  = _read_local_version_file()

    if state_ver and _parse_version(state_ver) >= _parse_version(file_ver):
        return state_ver

    # version.json mới hơn (có thể do cài tay) — đồng bộ
    if file_ver and file_ver != "0.0.0":
        _write_state(version=file_ver)
    return file_ver or state_ver or "0.0.0"


def _should_check_now() -> bool:
    state = _read_state()
    last = state.get("last_check", "")
    if last:
        try:
            last_time = datetime.fromisoformat(last)
            # ⚡ Dùng seconds thay vì minutes
            if datetime.now() - last_time < timedelta(seconds=_UPDATE_CHECK_INTERVAL_SECONDS):
                return False
        except Exception as e:
            logger.warning("_should_check_now: lỗi parse last_check '%s': %s", last, e)
    return True


def _mark_checked():
    _write_state(last_check=datetime.now().isoformat())


def _save_prev_version(version: str):
    _write_state(prev_version=version)


def _clear_prev_version():
    _write_state(prev_version=None)


# ── GitHub URLs (dùng branch hiện tại, không dùng Releases) ─────

def _version_json_url() -> str:
    branch = _detect_git_branch()
    return f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{branch}/version.json"


def _branch_zip_url() -> str:
    branch = _detect_git_branch()
    return f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/refs/heads/{branch}.zip"


# ── Run on Anki main thread ───────────────────────────────────────

def _run_on_main(func):
    """Đưa func sang main thread của Anki (cần cho UI và mw.col)."""
    try:
        from aqt import mw
        mw.taskman.run_on_main(func)
    except Exception as e:
        logger.warning("_run_on_main: không đưa được func lên main thread: %s", e)
        try:
            func()
        except Exception as e2:
            logger.warning("_run_on_main: func fallback cũng lỗi: %s", e2)


# ── Fetch remote version ──────────────────────────────────────────

def _fetch_remote_version() -> dict | None:
    url = _version_json_url()
    headers = {
        "User-Agent": f"AnkiFinance-AutoUpdate/{_get_local_version()}",
        "Cache-Control": "no-cache",
    }
    req = Request(url, headers=headers)

    # ⚡ Chỉ retry 1 lần vì vòng lặp ngoài sẽ retry sau 60s
    for attempt in range(2):
        try:
            with urlopen(req, timeout=_VERSION_CHECK_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                version = str(data.get("version", "")).strip()
                if not version:
                    _log("⚠️ version.json thiếu trường 'version'.")
                    return None
                return {
                    "version":   version,
                    "changelog": str(data.get("changelog", data.get("description", ""))),
                    "name":      str(data.get("name", "Anki Finance")),
                }
        except URLError as e:
            _log(f"⚠️ Lỗi mạng (lần {attempt+1}/2): {e.reason}")
            if attempt < 1:
                time.sleep(1)  # ⚡ Chỉ đợi 1s giữa các lần retry
        except (json.JSONDecodeError, Exception) as e:
            _log(f"⚠️ Lỗi parse version.json từ GitHub: {e}")
            break

    return None


# ── Download & apply ──────────────────────────────────────────────

def _fetch_branch_zip() -> bytes | None:
    url = _branch_zip_url()
    headers = {"User-Agent": f"AnkiFinance-AutoUpdate/{_get_local_version()}"}
    req = Request(url, headers=headers)

    for attempt in range(_DOWNLOAD_RETRIES):
        try:
            _log(f"📥 Đang tải branch main ZIP (lần {attempt+1}) ...")
            with urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp:
                data = resp.read()
            _log(f"✅ Tải thành công ({len(data):,} bytes)")
            return data
        except URLError as e:
            _log(f"⚠️ Lỗi tải ZIP (lần {attempt+1}): {e.reason}")
            if attempt < _DOWNLOAD_RETRIES - 1:
                time.sleep(3)
        except Exception as e:
            _log(f"⚠️ Lỗi không xác định khi tải ZIP: {e}")
            break
    return None


def _apply_zip_update(zip_bytes: bytes, new_version: str) -> bool:
    """
    Giải nén ZIP branch main và đè lên thư mục add-on.
    Cấu trúc ZIP GitHub: {repo}-main/... → bỏ qua thư mục root.
    auto_update.py ĐƯỢC phép cập nhật (không nằm trong SKIP_FILES nữa).
    """
    SKIP_FILES = {"_user_backup"}

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            all_names = zf.namelist()
            if not all_names:
                _log("❌ ZIP rỗng")
                return False

            # Tìm thư mục root (vd: Anki-Finance-1-main/)
            root_dir = next((n for n in all_names if n.endswith("/")), "")

            extracted = 0
            for name in all_names:
                if name == root_dir:
                    continue

                rel_path = name[len(root_dir):] if root_dir else name
                if not rel_path:
                    continue

                base_name = os.path.basename(rel_path) or os.path.dirname(rel_path).split("/")[0]
                if base_name in SKIP_FILES:
                    continue

                target = os.path.join(_ADDON_DIR, rel_path)

                if name.endswith("/"):
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    extracted += 1

            _log(f"✅ Đã ghi {extracted} file")
            # Ghi version vào state file (thread-safe, không cần mw.col)
            _write_state(version=new_version)
            return True

    except zipfile.BadZipFile:
        _log("❌ File ZIP hỏng")
    except Exception as e:
        _log(f"❌ Lỗi giải nén: {e}\n{traceback.format_exc()}")
    return False


def _backup_user_config():
    try:
        src = os.path.join(_ADDON_DIR, "shop_items.json")
        if os.path.exists(src):
            bak_dir = os.path.join(_ADDON_DIR, "_user_backup")
            os.makedirs(bak_dir, exist_ok=True)
            shutil.copy2(src, os.path.join(bak_dir, "shop_items.json"))
    except Exception as e:
        _log(f"⚠️ Backup thất bại: {e}")


# ── Notifications ─────────────────────────────────────────────────

def _notify(msg: str, period: int = 7000):
    """Phải gọi từ main thread."""
    try:
        from aqt.utils import tooltip
        tooltip(msg, period=period)
    except Exception as e:
        logger.warning("_notify: không hiện được tooltip: %s", e)


def _show_update_popup_if_needed():
    """
    Gọi khi Anki khởi động (main thread).
    Nếu state file ghi nhận vừa update → hiện popup chào mừng.
    """
    try:
        state   = _read_state()
        prev_ver = state.get("prev_version")

        if not prev_ver:
            return

        current_ver = _get_local_version()
        _log(f"🔍 Kiểm tra popup: cũ={prev_ver}, mới={current_ver}")

        if current_ver and _parse_version(current_ver) > _parse_version(prev_ver):
            from aqt.utils import showInfo
            showInfo(
                f"🎉 Anki Finance đã được cập nhật thành công!\n\n"
                f"📦 v{prev_ver}  →  v{current_ver}\n\n"
                f"✅ Bạn đang dùng phiên bản mới nhất.\n"
                f"Cảm ơn bạn đã sử dụng Anki Finance 💜"
            )

        # Xoá flag để không hiện lại lần sau
        _clear_prev_version()

    except Exception as e:
        _log(f"⚠️ Lỗi popup update: {e}")


# ── Core update flow (vòng lặp liên tục) ──────────────────────────

def _do_check():
    """
    ⚡ Vòng lặp vĩnh viễn trong thread nền.
    Kiểm tra version.json trên GitHub mỗi {_UPDATE_CHECK_INTERVAL_SECONDS} giây.
    Khi phát hiện bản mới → tự động tải ZIP → áp dụng → thông báo restart.

    So với phiên bản cũ:
      - Trước: chạy 1 lần rồi thoát, interval 30 phút.
      - Nay:   vòng lặp liên tục, interval {_UPDATE_CHECK_INTERVAL_SECONDS}s, check NGAY LẬP TỨC.
    """
    global _UPDATE_AVAILABLE, _PENDING_INFO, _DOWNLOADING, _APPLIED, _PENDING_RESTART

    while True:
        try:
            # ⏳ Nếu chưa đủ interval → ngủ ngắn rồi thử lại
            if not _should_check_now():
                time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)
                continue

            local_ver = _get_local_version()
            _log(f"📋 Version hiện tại: v{local_ver}")

            remote = _fetch_remote_version()
            if not remote:
                _log(f"⚠️ Không lấy được version.json từ GitHub — sẽ thử lại sau {_UPDATE_CHECK_INTERVAL_S}.")
                _mark_checked()
                time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)
                continue

            remote_ver = remote["version"]
            _log(f"🌐 Version trên GitHub main: v{remote_ver}")

            if _parse_version(remote_ver) <= _parse_version(local_ver):
                _log("✅ Đang dùng phiên bản mới nhất.")
                _UPDATE_AVAILABLE = False
                _PENDING_INFO = None
                _mark_checked()
                time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)
                continue

            # 🎉 Có bản mới!
            _log(f"🎉 Có bản cập nhật: v{local_ver} → v{remote_ver}")
            _UPDATE_AVAILABLE = True
            _PENDING_INFO = {
                "local":     local_ver,
                "latest":    remote_ver,
                "changelog": remote.get("changelog", ""),
            }

            # Lưu prev_version vào file trước khi download (thread-safe)
            _save_prev_version(local_ver)
            _backup_user_config()

            # Tự động tải + áp dụng NGAY LẬP TỨC
            _DOWNLOADING = True
            zip_data = _fetch_branch_zip()

            if not zip_data:
                _DOWNLOADING = False
                _log("❌ Tải ZIP thất bại — hiện thông báo thủ công.")
                _run_on_main(lambda: _notify(
                    f"🔄 Anki Finance có bản mới v{remote_ver}!\n"
                    f"Mở cửa sổ Tycoon → tab Cài đặt để cập nhật.",
                    period=9000
                ))
                _mark_checked()
                time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)
                continue

            success = _apply_zip_update(zip_data, remote_ver)
            _DOWNLOADING = False

            if success:
                _log(f"✅ Cập nhật thành công v{local_ver} → v{remote_ver}!")
                _APPLIED = True
                _UPDATE_AVAILABLE = False
                _PENDING_INFO = None
                _PENDING_RESTART = True
                _mark_checked()
                _run_on_main(lambda: _notify(
                    f"✅ Anki Finance v{remote_ver} đã sẵn sàng!\n"
                    f"🔄 Vui lòng khởi động lại Anki để áp dụng.",
                    period=10000
                ))
                # ⚡ Tiếp tục vòng lặp để phát hiện bản mới hơn
                time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)
                continue
            else:
                _log("❌ Áp dụng ZIP thất bại.")
                _run_on_main(lambda: _notify(
                    f"❌ Cập nhật lên v{remote_ver} thất bại.\n"
                    f"Kiểm tra kết nối mạng hoặc thử lại sau.",
                    period=7000
                ))
                _mark_checked()
                time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)
                continue

        except Exception:
            _log(f"❌ Lỗi không xác định:\n{traceback.format_exc()}")
            _UPDATE_AVAILABLE = False
            _PENDING_INFO = None
            _DOWNLOADING = False
            time.sleep(_UPDATE_CHECK_INTERVAL_SECONDS)
            continue


# ── Public API ────────────────────────────────────────────────────

def check_for_updates(background: bool = True):
    """Gọi khi Anki khởi động."""
    if background:
        t = threading.Thread(target=_do_check, daemon=True, name="AnkiFinance-Updater")
        t.start()
    else:
        _do_check()


def get_current_version() -> str:
    return _get_local_version()


def get_latest_release_info() -> dict | None:
    remote = _fetch_remote_version()
    if not remote:
        return None
    local = _get_local_version()
    return {
        "version":    remote["version"],
        "changelog":  remote.get("changelog", ""),
        "has_update": _parse_version(remote["version"]) > _parse_version(local),
        "url":        f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}",
    }


def force_check_update_sync() -> dict:
    """Người dùng bấm nút 'Kiểm tra cập nhật'."""
    local_ver = _get_local_version()
    remote = _fetch_remote_version()

    if not remote:
        return {"ok": False, "error": "Không thể kết nối GitHub", "current_version": local_ver}

    remote_ver = remote["version"]
    if _parse_version(remote_ver) > _parse_version(local_ver):
        return {
            "ok": True,
            "has_update": True,
            "current_version": local_ver,
            "latest_version":  remote_ver,
            "changelog":       remote.get("changelog", ""),
            "url":             f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}",
        }
    return {
        "ok": True,
        "has_update": False,
        "current_version": local_ver,
        "latest_version":  remote_ver,
        "message": "Bạn đang dùng phiên bản mới nhất.",
    }


def download_and_apply_update() -> dict:
    """Người dùng bấm 'Cập nhật ngay' trong UI (gọi từ main thread)."""
    local_ver = _get_local_version()

    remote = _fetch_remote_version()
    if not remote:
        return {"ok": False, "error": "Không thể lấy thông tin phiên bản mới"}

    remote_ver = remote["version"]

    _save_prev_version(local_ver)
    _backup_user_config()

    zip_data = _fetch_branch_zip()
    if not zip_data:
        return {"ok": False, "error": "Không thể tải file cập nhật"}

    success = _apply_zip_update(zip_data, remote_ver)
    if success:
        _schedule_anki_restart(delay_seconds=3)
        return {
            "ok": True,
            "message": f"✅ Cập nhật thành công lên v{remote_ver}! Anki sẽ khởi động lại sau 3 giây.",
            "old_version": local_ver,
            "new_version": remote_ver,
        }
    return {"ok": False, "error": "Giải nén hoặc ghi file thất bại"}


def is_update_available() -> bool:
    return bool(_UPDATE_AVAILABLE)


def get_pending_update_info() -> dict | None:
    return _PENDING_INFO


def confirm_and_apply_update() -> dict:
    """Topbar bấm nút cập nhật → tải + cài + restart (gọi từ main thread)."""
    global _UPDATE_AVAILABLE, _PENDING_INFO, _DOWNLOADING, _APPLIED, _PENDING_RESTART

    if not _PENDING_INFO:
        return {"ok": False, "error": "Không có bản cập nhật đang chờ."}
    if _DOWNLOADING:
        return {"ok": False, "error": "Đang tải, vui lòng đợi..."}

    _DOWNLOADING = True
    info = _PENDING_INFO
    local_ver  = info["local"]
    remote_ver = info["latest"]

    try:
        _log(f"📥 Người dùng xác nhận cập nhật v{local_ver} → v{remote_ver}")
        _save_prev_version(local_ver)
        _backup_user_config()

        zip_data = _fetch_branch_zip()
        if not zip_data:
            _DOWNLOADING = False
            return {"ok": False, "error": "Không thể tải file cập nhật."}

        success = _apply_zip_update(zip_data, remote_ver)
        if not success:
            _DOWNLOADING = False
            return {"ok": False, "error": "Giải nén hoặc ghi file thất bại."}

        _APPLIED = True
        _UPDATE_AVAILABLE = False
        _DOWNLOADING = False
        _PENDING_INFO = None
        _PENDING_RESTART = True

        _notify(
            f"✅ Anki Finance v{remote_ver} đã cài xong!\n"
            f"🔄 Anki sẽ khởi động lại sau 3 giây...",
            period=5000
        )
        _schedule_anki_restart(delay_seconds=3)

        return {
            "ok": True,
            "message": f"✅ Cập nhật thành công! Anki sẽ tự khởi động lại trong 3 giây.",
            "old_version": local_ver,
            "new_version": remote_ver,
        }
    except Exception as e:
        _DOWNLOADING = False
        _log(f"❌ Lỗi: {e}\n{traceback.format_exc()}")
        return {"ok": False, "error": str(e)}


def _schedule_anki_restart(delay_seconds: int = 3):
    try:
        from aqt import mw
        from aqt.qt import QTimer

        try:
            profile_name = mw.pm.name
            if profile_name:
                mw.pm.set_next_profile(profile_name)
        except Exception as e:
            logger.warning("_schedule_anki_restart: lỗi set_next_profile: %s", e)

        def _do_restart():
            _log("🔄 Khởi động lại Anki...")
            try:
                mw.restart()
            except AttributeError:
                logger.warning("_do_restart: mw.restart không có, thử close")
                try:
                    mw.close()
                except Exception as e:
                    logger.warning("_do_restart: không restart được: %s", e)

        QTimer.singleShot(delay_seconds * 1000, _do_restart)
    except Exception as e:
        _log(f"⚠️ Không thể lên lịch restart: {e}")


def _reset_pending_restart():
    global _PENDING_RESTART
    _PENDING_RESTART = False


def auto_update_on_startup():
    """Gọi từ __init__.py khi profile loaded (main thread)."""
    _log(f"🚀 AutoUpdater khởi động (v{_get_local_version()})")
    _show_update_popup_if_needed()
    check_for_updates(background=True)


# ── Test nhanh khi chạy trực tiếp ────────────────────────────────
if __name__ == "__main__":
    print(f"Anki Finance Auto-Updater")
    print(f"  Add-on dir:    {_ADDON_DIR}")
    print(f"  Local version: {_get_local_version()}")
    print(f"  Remote URL:    {_version_json_url()}")
    check_for_updates(background=False)
