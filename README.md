# 🎓 Anki Finance

Biến việc ôn thẻ Anki thành trò chơi làm giàu!

## 📦 Cài đặt

1. Tải add-on từ GitHub Releases
2. Giải nén vào thư mục `addons21/anki_finance/`
3. Khởi động lại Anki

## 🔄 Cập nhật tự động từ GitHub

Add-on này được tích hợp sẵn cơ chế **Auto-Update** — tự động kiểm tra và tải bản cập nhật mới nhất từ **GitHub Releases** mà **không cần qua AnkiWeb**.

### Cách hoạt động

1. Mỗi khi khởi động Anki, add-on chạy 1 thread nền kiểm tra GitHub API
2. So sánh version hiện tại với release mới nhất
3. Nếu có bản mới → tự động tải ZIP release → giải nén đè lên thư mục hiện tại
4. Hiển thị thông báo yêu cầu khởi động lại Anki

### Cấu hình lần đầu (dành cho developer)

Mở file [`auto_update.py`](auto_update.py) và sửa 3 hằng số ở đầu file:

```python
GITHUB_USER = "your-username"    # GitHub username của bạn
GITHUB_REPO = "anki-finance"     # Tên repository
CURRENT_VERSION = "1.0.0"        # Version hiện tại
```

---

## 🚀 Hướng dẫn push lên GitHub & thiết lập Auto-Update

### Bước 1: Tạo repository trên GitHub

1. Vào [github.com/new](https://github.com/new)
2. Nhập tên repository (VD: `anki-finance`)
3. Chọn **Public** (cần public để người dùng khác tải được)
4. **Không** tick "Initialize with README" (vì đã có sẵn)
5. Click **Create repository**

### Bước 2: Push code lên GitHub

Mở terminal (CMD/PowerShell) tại thư mục add-on và chạy:

```bash
# Khởi tạo Git repo
cd /d "C:\Users\nguye\AppData\Roaming\Anki2\addons21\anki_finance"
git init
git add .
git commit -m "Initial commit: Anki Finance v1.0.0"

# Liên kết với GitHub repository
git remote add origin https://github.com/YOUR_USERNAME/anki-finance.git

# Push lên GitHub
git branch -M main
git push -u origin main
```

> ⚠️ Thay `YOUR_USERNAME` bằng GitHub username thật của bạn.

### Bước 3: Sửa cấu hình trong file auto_update.py

Mở file [`auto_update.py`](auto_update.py), sửa 3 dòng đầu:

```python
GITHUB_USER = "your-username"    # → Thay bằng username GitHub của bạn
GITHUB_REPO = "anki-finance"     # → Thay bằng tên repository (nếu khác)
CURRENT_VERSION = "1.0.0"        # Giữ nguyên
```

Commit và push lại:

```bash
git add auto_update.py
git commit -m "Configure GitHub username"
git push
```

### Bước 4: Tạo Release đầu tiên

Có **2 cách**:

#### Cách A: Tạo Release thủ công (qua GitHub UI)

1. Vào repository của bạn trên GitHub → **Releases** → **Create a new release**
2. **Tag version**: `v1.0.0`
3. **Release title**: `v1.0.0 - Initial Release`
4. **Description**: Ghi chú thay đổi
5. **Attach binaries**: Có thể đính kèm file ZIP (không bắt buộc)
6. Click **Publish release**

#### Cách B: Dùng Git tag + GitHub CLI

```bash
git tag -a v1.0.0 -m "Initial Release v1.0.0"
git push origin v1.0.0
```

> **Lưu ý quan trọng**: GitHub chỉ cho phép 60 requests/giờ với API unauthenticated. Nếu deploy cho nhiều người dùng, nên tạo **Personal Access Token (PAT)** và cấu hình trong `auto_update.py`.

### Bước 5: Kiểm tra auto-update

1. Tăng `CURRENT_VERSION` trong `auto_update.py` lên `1.0.1`
2. Tạo release mới trên GitHub với tag `v1.0.1`
3. Khởi động lại Anki → kiểm tra console log:
   ```
   [AnkiFinance][AutoUpdate] 🚀 Khởi động auto-updater (v1.0.0)
   [AnkiFinance][AutoUpdate] 🌐 Phiên bản mới nhất trên GitHub: v1.0.1
   [AnkiFinance][AutoUpdate] 🎉 Có bản cập nhật: v1.0.0 → v1.0.1
   ```

### Bước 6: Deploy đến người dùng khác

Người dùng chỉ cần:
1. Clone repo hoặc download release ZIP đầu tiên về máy
2. Giải nén vào `addons21/anki_finance/`
3. Mỗi lần bạn release bản mới, add-on tự động cập nhật

---

## 🔧 Cấu hình nâng cao

### Giới hạn tốc độ GitHub API

Để tránh vượt quá rate limit của GitHub, có thể tạo **Personal Access Token**:

1. Vào [GitHub Settings → Tokens](https://github.com/settings/tokens) → Generate new token
2. Chọn scope `public_repo` (đủ để đọc releases)
3. Copy token và sửa trong [`auto_update.py`](auto_update.py):

```python
# Thêm dòng này sau phần import
_GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"

# Và sửa hàm _github_api_url:
def _github_api_url() -> str:
    return f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
```

### Tần suất kiểm tra

Mặc định: **1 lần/ngày**. Sửa hằng số trong [`auto_update.py`](auto_update.py):

```python
_UPDATE_INTERVAL_DAYS = 1   # 0 = kiểm tra mỗi lần khởi động
```

---

## 📁 Cấu trúc thư mục

```
anki_finance/
├── auto_update.py        # 🆕 Cơ chế tự động cập nhật từ GitHub
├── __init__.py            # Entry point (đã tích hợp auto_update)
├── version.json           # 🆕 File version metadata
├── .gitignore             # 🆕 Git ignore rules
├── README.md              # 🆕 Hướng dẫn
├── balance.py
├── config.py
├── gui/
│   ├── web_bridge.py      # Đã thêm bridge methods cho auto_update
│   └── ...
├── assets/
└── ...
```

---

## 📝 License

MIT License
