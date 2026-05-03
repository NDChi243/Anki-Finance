// ════════════════════════════════════════════

//  INIT + GLOBAL AUTO‑REFRESH (real‑time sync)

// ════════════════════════════════════════════

let _autoRefreshTimer = null;

let _autoRefreshCountdown = 0;

const AUTO_REFRESH_SEC = 30;



new QWebChannel(qt.webChannelTransport, ch => {

  B = ch.objects.bridge;



  // Khi balance thay đổi → refresh page đang active

  B.balanceChanged.connect(v => {

    curBal = v;

    updateNavBal(v);

    const activePage = document.querySelector('.page.active')?.id;

    if (activePage) {

      const loader = LOADERS[activePage.replace('page-','')];

      if (loader && activePage !== 'page-dashboard') {

        // Reset countdown để tránh refresh quá dày

        _autoRefreshCountdown = AUTO_REFRESH_SEC;

      }

    }

  });



  // Auto‑refresh toàn cục — luôn bật, không cần nút bấm

  _autoRefreshCountdown = AUTO_REFRESH_SEC;

  _autoRefreshTimer = setInterval(() => {

    _autoRefreshCountdown--;

    if (_autoRefreshCountdown <= 0) {

      _autoRefreshCountdown = AUTO_REFRESH_SEC;

      const activePage = document.querySelector('.page.active')?.id;

      if (activePage) {

        const loader = LOADERS[activePage.replace('page-','')];

        if (loader) loader().catch(() => {});

      }

    }

  }, 1000);



  // 🔥 FIX: Load dashboard ngay khi webview khởi tạo

  // Đảm bảo balance và dữ liệu dashboard được hiển thị ngay lập tức

  // không cần đợi auto-refresh 30 giây hay phải chuyển tab

  loadDashboard().catch(() => {});

});



async function loadAll() {

  const page = document.querySelector('.page.active').id.replace('page-','');

  if (page === 'dashboard') await loadDashboard();

  else {

    await refreshBalance();

    if (page === 'shop')      await loadShop();

    if (page === 'inventory') await loadInventory();

    if (page === 'bank')      await loadBank();

    if (page === 'finance')   await loadFinance();

  }

}



