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

  // Load dashboard immediately when the webview starts.
  loadDashboard().catch(() => {});

});


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
