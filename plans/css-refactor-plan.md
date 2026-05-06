# Kế hoạch tái cấu trúc CSS — Anki Finance

> **Mục tiêu:** Chia nhỏ file `gui/tycoon.css` (1200 dòng, monolithic) thành các module riêng biệt để AI dễ dàng mở rộng, maintain, và debug mà không sợ conflict.

---

## 1. Phân tích hiện trạng

### File hiện tại: `gui/tycoon.css` — 1200 dòng, 1 file duy nhất

```
:root variables          (dòng 1-60)     — 60 biến CSS custom properties
Base reset + body        (dòng 61-74)    — box-sizing, html/body
Utility classes           (dòng 76-81)    — .num-mono, .gradient-text
TOPNAV                    (dòng 83-149)   — nav, .brand, .nb, .nav-bal, .nav-chip
PAGES                     (dòng 151-154)  — .page, .page.active
COMMON components         (dòng 156-228)  — .card, .glass-card, .chip, .skeleton, .grid-auto
STAT CARD                 (dòng 230-240)  — .stat
BADGE                     (dòng 242-249)  — .badge-*
QUIZ                      (dòng 251-282)  — .quiz-option, .quiz-progress-dot
EASE BADGES               (dòng 284-288)  — .ease-1..4
BUTTONS                   (dòng 290-325)  — .btn, .btn-*
INPUTS                    (dòng 327-333)  — .inp
PROGRESS BAR              (dòng 335-348)  — .progress-wrap, .progress-bar
DIVIDER / TOAST / EMPTY   (dòng 350-370)  — hr, .toast, .empty
SCROLLBAR                 (dòng 372-377)  — ::-webkit-scrollbar
MODAL                     (dòng 379-398)  — .modal-overlay, .modal
--- PAGE-SPECIFIC ---
DASHBOARD                 (dòng 404-432)  — .hero, .reward-row
SHOP                      (dòng 434-451)  — .item-card, .shop-toolbar
EFFECT TAGS               (dòng 453-471)  — .effect-tag
PASSIVE EFFECTS           (dòng 473-492)  — .passive-panel
INVENTORY                 (dòng 494-495)  — .inv-card
BANK                      (dòng 497-533)  — .bank-tabs, .bank-preset, .term-card
FINANCE                   (dòng 535-575)  — .fin-tabs, .fin-stat-card, .txn-*
BOOST / FOOD / TAX / RES  (dòng 577-616)  — misc
GOAL PROGRESS             (dòng 618-625)  — .goal-card
KNOWLEDGE BASE            (dòng 627-661)  — .kb-card, .kb-editor
REAL ESTATE               (dòng 663-669)  — .re-card
SHOP SPECIFIC             (dòng 671-776)  — .shop-cat-card, rarity, shop-detail-modal
STOCK MARKET              (dòng 777-855)  — .stock-card, .session-timer
DIGITAL ASSETS            (dòng 857-914)  — .crypto-card, .staking-card
CREDIT BANKING            (dòng 916-1001) — .cb-score, .cc-card, .loan-card
BANK VIEW TOGGLE          (dòng 1003-1011) — .bank-view-toggle
CREDIT SECTION HEADER     (dòng 1013-1016) — .credit-section-header
GARAGE                    (dòng 1018-1090) — .garage-card, .garage-stat-bar
DESIGN POLISH LAYER       (dòng 1092-1195) — Overrides & enhancements
```

### Vấn đề hiện tại

| # | Vấn đề | Mức độ |
|---|--------|--------|
| 1 | **Monolithic** — 1200 dòng, 1 file, khó maintain | 🔴 Cao |
| 2 | **Duplicate declarations** — `.badge-blue` ở dòng 247 **và** 281; `.badge-purple` ở 248 **và** 282 | 🔴 Cao |
| 3 | **Design Polish Layer** (dòng 1092+) override các selector cũ — nếu không biết sẽ rất confusion | 🟠 Trung bình |
| 4 | **Selector specificity** không nhất quán — có chỗ dùng `.card`, có chỗ dùng `.glass-card`, khó biết cái nào ưu tiên | 🟠 Trung bình |
| 5 | **No responsive design** — không có @media query cho mobile | 🟡 Thấp (ưu tiên sau) |
| 6 | **Inline styles trong HTML** — rất nhiều style="..." trong tycoon_ui.html (4887 dòng) | 🟡 Thấp (không đụng) |

---

## 2. Kiến trúc đề xuất: CSS Module System

### 2.1. Sơ đồ kiến trúc

```
gui/
├── tycoon.css                  ← IMPORT HUB (chỉ @import, không code)
├── css/
│   ├── _variables.css          ← :root variables + fonts
│   ├── _reset.css              ← *, html, body base
│   ├── _utilities.css          ← .num-mono, .gradient-text, .row, .row-sb, .grid-auto
│   ├── _components.css         ← .card, .glass-card, .chip, .badge, .btn, .inp, .modal, .toast
│   ├── _nav.css                ← nav, .brand, .nb, .nav-bal, .nav-chip
│   ├── _pages.css              ← .page, .page.active
│   ├── _dashboard.css          ← .hero, .reward-row, .stat, .passive-panel
│   ├── _shop.css               ← .item-card, .shop-cat-card, .shop-detail-modal, rarity
│   ├── _bank.css               ← .bank-tabs, .term-card, .fin-*, .cb-*, .loan-card
│   ├── _stocks.css             ← .stock-card, .session-timer, .crypto-card
│   ├── _garage.css             ← .garage-card, .garage-stat-bar
│   ├── _knowledge.css          ← .kb-card, .kb-editor, .quiz-option
│   ├── _realestate.css          ← .re-card, .sat-bar
│   ├── _misc.css               ← effect-tag, goal-card, boost-bar, food-card, tax-tier
│   └── _polish.css             ← DESIGN POLISH LAYER (overrides & enhancements)
```

### 2.2. Quy tắc đặt tên file

- **`_filename.css`** — convention CSS partial (báo hiệu đây là file nhập, không load riêng lẻ)
- **Theme/global** files: `_variables`, `_reset`, `_utilities`, `_components`, `_nav`
- **Page-specific** files: `_dashboard`, `_shop`, `_bank`, `_stocks`, `_garage`, `_knowledge`, `_realestate`
- **Overrides**: `_polish`

### 2.3. Import Hub (`gui/tycoon.css`)

```css
/* ===== ANKI FINANCE — CSS MODULES ===== */
/* Không thêm code mới vào đây! Thêm vào file module tương ứng. */

@import url('css/_variables.css');
@import url('css/_reset.css');
@import url('css/_utilities.css');
@import url('css/_nav.css');
@import url('css/_pages.css');
@import url('css/_components.css');
@import url('css/_dashboard.css');
@import url('css/_shop.css');
@import url('css/_bank.css');
@import url('css/_stocks.css');
@import url('css/_garage.css');
@import url('css/_knowledge.css');
@import url('css/_realestate.css');
@import url('css/_misc.css');
@import url('css/_polish.css');
```

---

## 3. Chi tiết từng module

### 3.1. `_variables.css` — Biến toàn cục

**Nguồn:** dòng 1-60 từ tycoon.css gốc

```css
/* ═══════════════════════════════════════
   CSS Custom Properties (Design Tokens)
   ═══════════════════════════════════════ */
:root {
  /* Surfaces (legacy) */
  --bg: #0a0a10; --surface: #14141d; --surface2: #1c1c2a;
  --surface3: #262638; --border: #2a2a40;

  /* Brand accent */
  --accent: #7c3aed; --accent2: #a855f7; --glow: rgba(124,58,237,.28);

  /* Semantic palette */
  --green: #10b981; --red: #ef4444; --yellow: #f59e0b;
  --blue: #3b82f6; --cyan: #06b6d4; --pink: #ec4899;
  --text: #f1f5f9; --muted: #64748b; --muted2: #94a3b8;

  /* Finance / rank tier palette */
  --profit: #10b981; --loss: #ef4444; --neutral: #94a3b8;
  --gold: #fbbf24; --platinum: #e2e8f0; --emerald: #34d399;
  --sapphire: #60a5fa; --ruby: #f43f5e;

  /* Glass surfaces */
  --glass-bg: rgba(28,28,42,.55); --glass-bg-hi: rgba(40,40,60,.65);
  --glass-border: rgba(255,255,255,.06); --glass-blur: 14px;

  /* Depth shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,.35);
  --shadow: 0 4px 14px rgba(0,0,0,.35);
  --shadow-lg: 0 12px 36px rgba(0,0,0,.45);
  --shadow-glow: 0 8px 28px var(--glow);

  /* Easing curves */
  --ease-out: cubic-bezier(.25,.46,.45,.94);
  --ease-bounce: cubic-bezier(.34,1.56,.64,1);
  --ease-in-out: cubic-bezier(.65,0,.35,1);

  /* Layout constants */
  --nav-h: 56px; --r: 14px; --r-sm: 10px;

  /* Typography */
  --font-ui: "Inter","SF Pro Display",-apple-system,'Segoe UI',sans-serif;
  --font-mono: "JetBrains Mono","SF Mono","Cascadia Mono",ui-monospace,monospace;
}
```

### 3.2. `_reset.css` — Reset & Body

**Nguồn:** dòng 61-74

```css
/* ═══════════════════════════════════════
   Base Reset & Body
   ═══════════════════════════════════════ */
*{box-sizing:border-box;margin:0;padding:0}
html,body{
  height:100%;
  font-family:var(--font-ui);
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(124,58,237,.10), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(59,130,246,.07), transparent 55%),
    var(--bg);
  background-attachment:fixed;
  color:var(--text);
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;
}
body{display:flex;flex-direction:column}
```

### 3.3. `_utilities.css` — Utility Classes

**Nguồn:** dòng 76-81, 219-228

```css
/* ═══════════════════════════════════════
   Utility Classes
   ═══════════════════════════════════════ */
/* Số tiền / chỉ số dùng tabular-nums (không nhảy width) */
.num-mono{font-variant-numeric:tabular-nums;font-feature-settings:"tnum","cv11";letter-spacing:-.2px}
.num-tab{font-variant-numeric:tabular-nums}
.gradient-text{background:linear-gradient(135deg,#7c3aed,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.gradient-text-profit{background:linear-gradient(135deg,#10b981,#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.gradient-text-gold{background:linear-gradient(135deg,#f59e0b,#fbbf24,#fde68a);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}

/* Layout helpers */
.grid-auto{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--min,200px),1fr));gap:14px}
.row{display:flex;align-items:center;gap:10px}
.row-sb{display:flex;align-items:center;justify-content:space-between;gap:10px}
label{font-size:12px;color:var(--muted2);font-weight:600;text-transform:uppercase;letter-spacing:.4px}

/* Scroll-reveal animation */
.reveal{opacity:0;transform:translateY(8px);animation:revealIn .45s var(--ease-out) forwards}
.reveal.delay-1{animation-delay:.06s}
.reveal.delay-2{animation-delay:.12s}
.reveal.delay-3{animation-delay:.18s}
@keyframes revealIn{to{opacity:1;transform:none}}
```

### 3.4. `_nav.css` — Top Navigation

**Nguồn:** dòng 83-149, 1170

```css
/* ═══════════════════════════════════════
   Top Navigation
   ═══════════════════════════════════════ */
/* ... nav, .brand, .nav-links, .nb, .nav-bal, .nav-chip ... */
```

### 3.5. `_components.css` — Shared Components

**Nguồn:** dòng 156-398 (trừ utility đã tách)

Bao gồm:
- `.section-title`, `.section-sub`
- `.card`, `.card-hover`, `.glass-card`
- `.live-dot`, `.chip`, `.skeleton`
- `.stat`, `.badge-*`, `.ease-*`
- `.btn`, `.btn-*`, `.inp`
- `.progress-wrap`, `.progress-bar`
- `hr`, `.toast`, `.empty`
- `::-webkit-scrollbar`
- `.modal-overlay`, `.modal`, `.modal-footer`

### 3.6 - 3.16. Page-specific modules

Mỗi module chứa code từ section tương ứng, giữ nguyên comment headers gốc.

**Quy tắc cho AI khi thêm component mới:**
- Nếu là **shared component** (dùng ở nhiều page) → thêm vào `_components.css`
- Nếu là **page-specific** (chỉ dùng ở 1 page) → thêm vào file page đó
- Nếu là **override/polish** (cải thiện selector cũ) → thêm vào `_polish.css`
- Luôn kiểm tra `_polish.css` trước khi sửa selector cũ để tránh duplicate

### 3.17. `_polish.css` — Design Polish Layer

**Nguồn:** dòng 1092-1195

Đây là layer cuối cùng, chứa các override để cải thiện UI. Không thêm code mới vào đây trừ khi thực sự cần override.

---

## 4. Roadmap thực thi (6 bước)

### Bước 1: Tạo thư mục `gui/css/`
- `mkdir gui/css`
- Tạo lần lượt từng file module

### Bước 2: Extract `_variables.css` + `_reset.css` + `_utilities.css`
- Copy-paste nguyên vẹn từ tycoon.css gốc
- Xoá khỏi tycoon.css gốc, thay bằng `@import`

### Bước 3: Extract `_nav.css` + `_pages.css` + `_components.css`
- Các module nền tảng, load sớm
- **Xử lý duplicate:** Hợp nhất `.badge-blue` (dòng 247 và 281) — giữ phiên bản ở dòng 247, xoá dòng 281
- **Xử lý duplicate:** Hợp nhất `.badge-purple` (dòng 248 và 282) — giữ phiên bản ở dòng 248, xoá dòng 282

### Bước 4: Extract page-specific modules
- `_dashboard.css`, `_shop.css`, `_bank.css`, `_stocks.css`
- `_garage.css`, `_knowledge.css`, `_realestate.css`, `_misc.css`

### Bước 5: Extract `_polish.css`
- Design Polish Layer (dòng 1092-1195)
- **Quan trọng:** Giữ nguyên selector chain, không thay đổi gì

### Bước 6: Tạo Import Hub + Test
- `gui/tycoon.css` chỉ còn `@import` statements
- Load thử trong Anki, kiểm tra từng tab

---

## 5. Quy tắc cho AI Auto-Expansion

Khi AI được yêu cầu thêm tính năng mới, AI phải:

```
1. Xác định LOẠI component:
   - Là biến mới?            → _variables.css
   - Là utility class mới?   → _utilities.css
   - Là shared component?    → _components.css
   - Là page-specific?       → _{page_name}.css
   - Là override?            → _polish.css

2. MỞ đúng file:
   - Mở file module tương ứng
   - Kiểm tra section header đã có chưa
   - Nếu chưa → thêm section header mới
   - Nếu rồi → thêm vào cuối section

3. THÊM code:
   - Luôn dùng CSS custom properties từ _variables.css
   - Tuân thủ naming convention (xem mục 6)
   - Giữ selector specificity tối thiểu
   - KHÔNG sửa file khác

4. VERIFY:
   - Kiểm tra không có duplicate selector
   - Nếu override selector cũ → phải vào _polish.css
```

---

## 6. Naming Convention

### Class naming rules

| Pattern | Example | Khi nào dùng |
|---------|---------|-------------|
| `.{page}-{component}` | `.shop-cat-card`, `.fin-stat-card` | Page-specific components |
| `.{component}-{variant}` | `.badge-green`, `.btn-primary` | Component variants |
| `.{component}__{sub}` | (tránh BEM phức tạp) | Chỉ khi component phức tạp |
| `.{abbr}-{prop}` | `.fsc-val`, `.scc-icon` | Viết tắt page + thuộc tính |

### !important rules
- **KHÔNG** dùng `!important` trừ phi thực sự không còn cách nào
- Nếu cần override, ưu tiên specificity cao hơn (thêm class cha)

---

## 7. Xử lý rủi ro

| Rủi ro | Mitigation |
|--------|-----------|
| CSS @import không load được trong WebView | Kiểm tra Anki web engine hỗ trợ @import. Nếu không → dùng <link> trong HTML |
| Selector order bị thay đổi sau tách | Import order phải đúng: variables → reset → utilities → nav → pages → components → pages → polish |
| Duplicate declarations làm hỏng UI | So sánh kỹ từng selector. Dùng diff tool để verify |
| Quên xoá code gốc | Sau mỗi lần extract, verify file gốc giảm đúng số dòng |
| Anki cache CSS cũ | Hard refresh (Ctrl+Shift+R) hoặc clear Anki cache |

---

## 8. "Done" Checklist

- [ ] `gui/css/` directory created with all module files
- [ ] `gui/tycoon.css` converted to import hub only
- [ ] All duplicate selectors resolved (badge-blue, badge-purple)
- [ ] All pages render correctly in Anki
- [ ] No console errors related to missing styles
- [ ] `.claude/skills/add-css-component.md` created for AI
- [ ] `.claude/rules/04-css-rules.md` created for AI

---

## 9. Kết luận

Sau refactor:
- **Trước:** 1 file × 1200 dòng = khó maintain, AI dễ conflict
- **Sau:** 15 file module × ~80 dòng mỗi file = AI biết chính xác file nào cần sửa
- **AI auto-expansion:** Chỉ cần nói "Thêm component X vào trang Y" → AI mở `_Y.css`, thêm vào cuối section, không động đến file khác
- **Zero risk of regression:** Import hub giữ nguyên load order, polish layer là safety net
