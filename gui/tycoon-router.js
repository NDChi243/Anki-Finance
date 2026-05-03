// ════════════════════════════════════════════

//  ROUTER

// ════════════════════════════════════════════

const LOADERS = {

  dashboard:   () => loadDashboard(),

  shop:        () => loadShop(),

  inventory:   () => loadInventory(),

  bank:        () => loadBank(),

  finance:     () => loadFinance(),

  realestate:  () => loadRealEstate(),

  knowledge:   () => loadKnowledge(),

  stocks:      () => goStocks(),

  digital:     () => loadDigitalAssets(),

  quests:      () => loadQuests(),

  achievement: () => loadAchievements(),

  learning:    () => loadLearning(),

  garage:      () => loadGarage(),

  settings:    () => loadSettings(),

};



function go(page) {

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));

  document.querySelectorAll('.nb').forEach(b => b.classList.remove('active'));

  document.getElementById('page-' + page).classList.add('active');

  document.getElementById('nb-' + page).classList.add('active');

  LOADERS[page]?.();

}



