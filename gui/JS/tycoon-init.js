// ============================================
//  INIT + GLOBAL AUTO-REFRESH
// ============================================

let _autoRefreshTimer = null;
let _autoRefreshCountdown = 0;
let _autoRefreshLastTickMs = 0;

const AUTO_REFRESH_SEC = 30;


function _runActivePageRefresh() {

  const activePage = document.querySelector('.page.active')?.id;
  if (!activePage) return;

  const loader = LOADERS[activePage.replace('page-', '')];
  if (loader) loader().catch(() => {});

}


function _stopAutoRefreshTicker() {

  if (_autoRefreshTimer) {
    cancelAnimationFrame(_autoRefreshTimer);
    _autoRefreshTimer = null;
  }

  _autoRefreshLastTickMs = 0;

}


function _startAutoRefreshTicker() {

  _stopAutoRefreshTicker();

  const tick = (now) => {

    if (!_autoRefreshLastTickMs) _autoRefreshLastTickMs = now;

    const elapsed = now - _autoRefreshLastTickMs;
    if (elapsed >= 1000) {
      const wholeSeconds = Math.floor(elapsed / 1000);
      _autoRefreshLastTickMs += wholeSeconds * 1000;
      _autoRefreshCountdown -= wholeSeconds;

      if (_autoRefreshCountdown <= 0) {
        _autoRefreshCountdown = AUTO_REFRESH_SEC;
        _runActivePageRefresh();
      }
    }

    _autoRefreshTimer = requestAnimationFrame(tick);

  };

  _autoRefreshTimer = requestAnimationFrame(tick);

}


new QWebChannel(qt.webChannelTransport, ch => {

  B = ch.objects.bridge;

  B.balanceChanged.connect(v => {

    curBal = v;
    updateNavBal(v);

    const activePage = document.querySelector('.page.active')?.id;
    if (activePage) {
      const loader = LOADERS[activePage.replace('page-', '')];
      if (loader && activePage !== 'page-dashboard') {
        _autoRefreshCountdown = AUTO_REFRESH_SEC;
      }
    }

  });

  _autoRefreshCountdown = AUTO_REFRESH_SEC;
  _startAutoRefreshTicker();

  // ── Game Mode: load + apply tab visibility ─────
  _initGameMode().catch(() => {});

  // Load dashboard immediately when the webview starts.
  loadDashboard().catch(() => {});

});


/**
 * Các advanced tabs bị ẩn trong Simple Mode.
 * Định nghĩa hằng để tránh phụ thuộc config.py bên Python.
 */
const ADVANCED_TAB_IDS = [
  'nb-realestate',
  'nb-garage',
  'nb-techlab',
  'nb-stocks',
  'nb-digital',
  'nb-learning',
];


/**
 * Khởi tạo game mode: đọc từ bridge và ẩn/hiện tab tương ứng.
 */
async function _initGameMode() {
  try {
    const raw = await B.getGameMode();
    const res = JSON.parse(raw);
    const mode = res.ok ? res.mode : 'full';

    // Lưu vào TycoonState
    TycoonState.gameMode = mode;
    window.gameMode = mode;

    _applyTabVisibility(mode);
  } catch (e) {
    console.warn('_initGameMode:', e);
  }
}


/**
 * Ẩn/Hiện navigation tabs dựa trên game mode.
 * @param {'full'|'simple'} mode
 */
function _applyTabVisibility(mode) {
  const isSimple = (mode === 'simple');

  for (const navId of ADVANCED_TAB_IDS) {
    const btn = document.getElementById(navId);
    if (btn) {
      btn.style.display = isSimple ? 'none' : '';
    }
  }

  // Ẩn page divs tương ứng
  const advancedPageIds = [
    'page-realestate',
    'page-garage',
    'page-techlab',
    'page-stocks',
    'page-digital',
    'page-learning',
  ];

  for (const pageId of advancedPageIds) {
    const page = document.getElementById(pageId);
    if (page) {
      page.style.display = isSimple ? 'none' : '';
    }
  }

  // Nếu đang ở advanced page và chuyển sang simple, redirect về dashboard
  if (isSimple) {
    const activePage = document.querySelector('.page.active');
    if (activePage) {
      const activeId = activePage.id; // e.g. "page-realestate"
      if (advancedPageIds.includes(activeId)) {
        go('dashboard');
      }
    }
  }
}


/**
 * Hàm public để áp dụng lại tab visibility (gọi sau khi chuyển mode trong Settings).
 * @param {'full'|'simple'} mode
 */
function applyTabVisibility(mode) {
  _applyTabVisibility(mode);
}


async function loadAll() {

  const page = document.querySelector('.page.active').id.replace('page-', '');

  if (page === 'dashboard') await loadDashboard();
  else {
    await refreshBalance();
    if (page === 'shop') await loadShop();
    if (page === 'inventory') await loadInventory();
    if (page === 'bank') await loadBank();
    if (page === 'finance') await loadFinance();
  }

}
