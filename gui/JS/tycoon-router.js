// ============================================
//  ROUTER
// ============================================

const LOADERS = {

  dashboard: () => loadDashboard(),
  shop: () => loadShop(),
  inventory: () => loadInventory(),
  bank: () => loadBank(),
  finance: () => loadFinance(),
  realestate: () => loadRealEstate(),
  knowledge: () => loadKnowledge(),
  stocks: () => goStocks(),
  digital: () => loadDigitalAssets(),
  quests: () => loadQuests(),
  achievement: () => loadAchievements(),
  learning: () => loadLearning(),
  garage: () => loadGarage(),
  techlab: () => loadTechLab(),
  settings: () => loadSettings(),

};


function go(page) {

  // ── Cleanup tickers via TickerManager ──────
  // Thay vì gọi từng hàm stop riêng lẻ, dùng TickerManager
  if (window.TycoonTicker) {
    if (page !== 'stocks')   TycoonTicker.stop('stock-session');
    if (page !== 'learning') TycoonTicker.stop('quiz-countdown');
    // Boost strip ticker tự check condition nên không cần stop ở đây
  } else {
    // Fallback cho code cũ (nếu chưa load tycoon-ticker.js)
    if (page !== 'stocks' && typeof stopSessionCountdown === 'function') stopSessionCountdown();
    if (page !== 'learning' && typeof stopQuizCountdown === 'function') stopQuizCountdown();
  }

  // ── Page visibility ────────────────────────
  const pages = document.querySelectorAll('.page');
  for (let i = 0; i < pages.length; i++) pages[i].classList.remove('active');

  const navBtns = document.querySelectorAll('.nb');
  for (let i = 0; i < navBtns.length; i++) navBtns[i].classList.remove('active');

  const targetPage = document.getElementById('page-' + page);
  const targetNav  = document.getElementById('nb-' + page);
  if (targetPage) targetPage.classList.add('active');
  if (targetNav)  targetNav.classList.add('active');

  // ── Load page ──────────────────────────────
  LOADERS[page]?.();

}
