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

  if (page !== 'stocks' && typeof stopSessionCountdown === 'function') stopSessionCountdown();
  if (page !== 'garage' && typeof stopGarageBoostTicker === 'function') stopGarageBoostTicker();
  if (page !== 'learning' && typeof stopQuizCountdown === 'function') stopQuizCountdown();

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nb').forEach(b => b.classList.remove('active'));

  document.getElementById('page-' + page).classList.add('active');
  document.getElementById('nb-' + page).classList.add('active');

  LOADERS[page]?.();

}
