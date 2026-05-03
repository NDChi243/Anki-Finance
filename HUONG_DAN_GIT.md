# 📘 Hướng dẫn Git — Anki Finance

## 📌 Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Môi trường cần có](#2-môi-trường-cần-có)
3. [Lần đầu kéo code từ GitHub về máy mới](#3-đầu-tiên-kéo-code-từ-github-về-máy-mới)
4. [Quy trình làm việc hàng ngày](#4-quy-trình-làm-việc-hàng-ngày)
5. [Cách tạo bản cập nhật (Release)](#5-cách-tạo-bản-cập-nhật-release)
6. [Các lệnh Git thường dùng](#6-các-lệnh-git-thường-dùng)
7. [Xử lý lỗi thường gặp](#7-xử-lý-lỗi-thường-gặp)

---

## 1. Tổng quan

Repo hiện tại: **`https://github.com/NDChi243/Anki-Finance-1.git`**
Branch chính: **`main`**

Thư mục code:  
[`C:\Users\nguye\AppData\Roaming\Anki2\addons21\anki_finance`](file:///C:/Users/nguye/AppData/Roaming/Anki2/addons21/anki_finance)

> ⚠️ Đây là thư mục add-on của Anki, nằm trong `AppData`. Khi code được push lên GitHub, người dùng khác có thể clone về và dùng.

---

## 2. Môi trường cần có

| Công cụ | Mục đích |
|---------|----------|
| **Git** | Quản lý phiên bản code |
| **GitHub Account** | Lưu code từ xa |
| **VSCode** | Soạn thảo code |

### Kiểm tra Git đã cài chưa

Mở **CMD** hoặc **PowerShell**, gõ:

```bash
git --version
```

Nếu chưa có → tải tại [git-scm.com](https://git-scm.com/downloads/win)

### Cấu hình Git lần đầu (chỉ làm 1 lần)

```bash
git config --global user.name "NDChi243"
git config --global user.email "email_của_bạn@example.com"
```

---

## 3. Lần đầu kéo code từ GitHub về máy mới

> Nếu bạn đang làm việc trên máy hiện tại, code đã có sẵn, bỏ qua bước này.

```bash
# Di chuyển đến thư mục addons21
cd /d "C:\Users\nguye\AppData\Roaming\Anki2\addons21"

# Clone repo (chỉ làm 1 lần)
git clone https://github.com/NDChi243/Anki-Finance-1.git anki_finance

# Vào thư mục
cd anki_finance
```

Sau đó mở Anki và bắt đầu dùng.

---

## 4. Quy trình làm việc hàng ngày

### 4.1. Khi code ở trên GitHub mới hơn (kéo về)

```bash
# Bước 1: Mở terminal tại thư mục anki_finance
cd /d "C:\Users\nguye\AppData\Roaming\Anki2\addons21\anki_finance"

# Bước 2: Kéo code mới nhất từ GitHub về
git pull
```

### 4.2. Khi bạn sửa code xong (đẩy lên)

```bash
# Bước 1: Xem những file đã sửa
git status

# Bước 2: Thêm tất cả file đã sửa vào stage
git add -A

# Bước 3: Chụp ảnh code (commit) với ghi chú
git commit -m "Mô tả ngắn gọn bạn đã sửa gì"

# Bước 4: Đẩy lên GitHub
git push
```

> **📝 Quy tắc đặt message commit:**
> - Tiếng Việt có dấu, ngắn gọn, rõ ràng
> - Ví dụ:
>   - `"Thêm chức năng mua bán cổ phiếu"`
>   - `"Sửa lỗi không hiển thị số dư"`
>   - `"Cập nhật giao diện topbar"`

### 4.3. Luồng làm việc nhanh (chỉ 1 dòng)

```bash
cd /d "C:\Users\nguye\AppData\Roaming\Anki2\addons21\anki_finance" && git add -A && git commit -m "Mô tả thay đổi" && git push
```

Copy-paste dòng trên, chỉ sửa phần `"Mô tả thay đổi"` là xong.

---

## 5. Cách tạo bản cập nhật (Release)

Auto-update của Anki Finance dùng **branch `main`** + file [`version.json`](version.json).

### Khi nào cần tạo bản mới?

Khi bạn sửa code và muốn người dùng khác tự động nhận được bản cập nhật.

### Các bước:

```bash
# Bước 1: Sửa số version trong file version.json
#   Mở version.json → tăng số "version" lên (VD: 1.0.2 → 1.0.3)

# Bước 2: Commit và push
cd /d "C:\Users\nguye\AppData\Roaming\Anki2\addons21\anki_finance"
git add version.json
git commit -m "Bump version 1.0.2 → 1.0.3"
git push

# Bước 3: (Không bắt buộc) Tạo GitHub Release cho đẹp
#   Lên github.com → Repo → Releases → Create a new release
#   Tag: v1.0.3
#   Title: v1.0.3 - Thêm chức năng mới
```

Sau khi push lên `main`, người dùng sẽ tự động nhận được cập nhật trong vòng **24h** (hoặc khi khởi động lại Anki).

---

## 6. Các lệnh Git thường dùng

| Lệnh | Chức năng |
|------|-----------|
| `git status` | Xem trạng thái: file nào đã sửa, thêm, xoá |
| `git add -A` | Thêm tất cả thay đổi vào stage |
| `git add ten_file.py` | Chỉ thêm 1 file cụ thể |
| `git commit -m "nội dung"` | Commit với ghi chú |
| `git push` | Đẩy code lên GitHub |
| `git pull` | Kéo code mới nhất từ GitHub về |
| `git log --oneline` | Xem lịch sử commit (dạng rút gọn) |
| `git diff` | Xem chi tiết nội dung đã sửa |
| `git restore ten_file.py` | Huỷ thay đổi trên 1 file (chưa stage) |
| `git restore --staged ten_file.py` | Bỏ stage 1 file (unstage) |
| `git reset --soft HEAD~1` | Huỷ commit gần nhất (giữ lại code) |

---

## 7. Xử lý lỗi thường gặp

### ❌ `"failed to push some refs"` / `"diverged"`

**Nguyên nhân:** Code trên GitHub mới hơn code của bạn.

**Cách xử lý:**

```bash
# Kéo code mới nhất về, tự động merge
git pull --no-rebase

# Nếu có conflict → sửa rồi commit lại
git add -A
git commit -m "Merge remote changes"
git push
```

### ❌ `"Please tell me who you are"`

**Nguyên nhân:** Chưa cấu hình Git.

**Cách xử lý:**

```bash
git config --global user.name "NDChi243"
git config --global user.email "email_của_bạn@example.com"
```

### ❌ `"Authentication failed"`

**Nguyên nhân:** Sai token hoặc mật khẩu.

**Cách xử lý (dùng Personal Access Token - PAT):**

1. Vào [GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)
2. Generate new token → chọn scope `repo` → copy token
3. Dùng token làm mật khẩu khi push:

```bash
git remote set-url origin https://NDChi243:TOKEN_CUA_BAN@github.com/NDChi243/Anki-Finance-1.git
```

> Thay `TOKEN_CUA_BAN` bằng token thật.

### ❌ Muốn huỷ commit vừa tạo, chưa push

```bash
git reset --soft HEAD~1
```

Code vẫn giữ nguyên, chỉ huỷ commit.

### ❌ Muốn huỷ commit vừa tạo, đã push rồi

```bash
git reset --soft HEAD~1
git push --force
```

> ⚠️ Chỉ dùng `--force` khi bạn chắc chắn không ai dùng code này.

---

## 🎯 Tóm tắt nhanh

| Tình huống | Làm gì? |
|-----------|---------|
| **Sửa code xong, muốn đẩy lên** | `git add -A && git commit -m "..." && git push` |
| **Máy mới, cần code** | `git clone https://github.com/NDChi243/Anki-Finance-1.git` |
| **Đồng bộ code mới nhất** | `git pull` |
| **Tạo bản cập nhật cho người dùng** | Sửa `version.json` → push → (tuỳ chọn) tạo Release |

---

*Happy coding! 🚀*
