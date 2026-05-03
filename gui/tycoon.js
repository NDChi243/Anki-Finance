// ════════════════════════════════════════════

//  STATE

// ════════════════════════════════════════════

let B = null;          // bridge

let allItems = [];     // shop items

let curBal = 0;

let curSavings = 0;

let residenceData = null;

let availableResidences = [];

let selectedResidenceId = '';

let selectedResidencePreview = null;

let loanStatusData = null;

let taxFullData = null;

const RESET_MIN_BALANCE = 50000;



// ── Debounce utility ──────────────────────────

function debounce(fn, ms = 300) {

  let timer;

  return (...args) => {

    clearTimeout(timer);

    timer = setTimeout(() => fn(...args), ms);

  };

}



// ── Throttle utility ──────────────────────────

function throttle(fn, ms = 100) {

  let last = 0;

  return (...args) => {

    const now = Date.now();

    if (now - last >= ms) {

      last = now;

      fn(...args);

    }

  };

}



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



// ════════════════════════════════════════════

//  ROUTER

// ════════════════════════════════════════════

const LOADERS = {

  dashboard: loadDashboard,

  shop:      loadShop,

  inventory: loadInventory,

  bank:      loadBank,

  finance:   loadFinance,

  realestate: loadRealEstate,

  knowledge: loadKnowledge,

  stocks:    goStocks,

  digital:   loadDigitalAssets,

  quests:    loadQuests,

  achievement: loadAchievements,

  learning:  loadLearning,

  garage:    loadGarage,

  settings:  loadSettings,

};



function go(page) {

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));

  document.querySelectorAll('.nb').forEach(b => b.classList.remove('active'));

  document.getElementById('page-' + page).classList.add('active');

  document.getElementById('nb-' + page).classList.add('active');

  LOADERS[page]?.();

}



// ════════════════════════════════════════════

//  BALANCE

// ════════════════════════════════════════════

async function refreshBalance() {

  // REQ1 FIX: luôn fetch trực tiếp từ Python, không cache cũ

  curBal = await B.getBalance();

  updateNavBal(curBal);

}



function updateNavBal(v) {

  document.getElementById('nav-bal').textContent = fmt(v);

  document.getElementById('bal-big').textContent = fmt(v);

  let sub = 'Ôn bài chăm chỉ để kiếm thêm tiền!';

  // Dùng so sánh an toàn với BigInt

  if (_numGte(v, 10000000000)) sub = '🏆 Tỷ phú Anki! Không thể tin được!';

  else if (_numGte(v, 1000000000)) sub = '🚀 Hơn 1 tỷ! Bạn đang giàu lên rồi!';

  else if (_numGte(v, 100000000)) sub = '💎 Hơn 100 triệu — mua xe đi!';

  else if (_numGte(v, 10000000)) sub = '📈 Đang trên đà làm giàu!';

  else if (v == 0 || v === '0')  sub = '🌱 Bắt đầu ôn bài để kiếm tiền đầu tiên!';

  document.getElementById('bal-sub').textContent = sub;

  updateResetButtonState();

}



function getResetDisabledReason() {

  if (curBal < 0) return 'Không thể reset khi tài khoản đang nợ.';

  if (curBal < RESET_MIN_BALANCE) return 'Cần ít nhất 50.000 VND để reset.';

  return '';

}



function updateResetButtonState() {

  const btn = document.getElementById('reset-btn');

  const hint = document.getElementById('reset-btn-hint');

  if (!btn) return;

  const reason = getResetDisabledReason();

  btn.disabled = !!reason;

  btn.title = reason;

  if (hint) {

    hint.textContent = reason || 'Nút reset chỉ mở khi số dư hiện tại từ 50.000 VND trở lên.';

  }

}



// ════════════════════════════════════════════

//  DASHBOARD

// ════════════════════════════════════════════

async function loadDashboard() {

  // Dùng combined API — 1 call thay vì 5+ calls

  const raw = JSON.parse(await B.getDashboardData());

  if (!raw.ok) { toast('err', '❌ Lỗi tải dashboard'); return; }



  const { balance, stats: s, streak, rank, quests, goal, again, bank } = raw;

  curBal = balance;

  updateNavBal(balance);



  document.getElementById('s-cards').textContent  = s.cards_reviewed || 0;

  document.getElementById('s-earned').textContent = fmt(s.total_earned || 0);

  document.getElementById('s-spent').textContent  = fmt(s.total_spent  || 0);

  document.getElementById('s-savings').textContent= fmt(bank.total_savings || 0);

  document.getElementById('c1').textContent = (s.ease_1||0) + ' lần';

  document.getElementById('c2').textContent = (s.ease_2||0) + ' lần';

  document.getElementById('c3').textContent = (s.ease_3||0) + ' lần';

  document.getElementById('c4').textContent = (s.ease_4||0) + ' lần';



  // Again monitor

  updateAgainMonitor(again);

  refreshBoostStrip();



  // Goal

  const gc = document.getElementById('goal-card');

  const ge = document.getElementById('goal-empty-prompt');

  if (goal && goal.has_goal) {

    gc.style.display = 'block'; ge.style.display = 'none';

    document.getElementById('goal-emoji').textContent = goal.item_emoji || '🎯';

    document.getElementById('goal-name').textContent  = goal.item_name || '';

    document.getElementById('goal-pct').textContent   = goal.percent + '%';

    document.getElementById('goal-price-info').textContent = 'Giá: ' + fmt(goal.item_price);

    document.getElementById('goal-set-at').textContent = goal.set_at ? 'Đặt lúc ' + goal.set_at : '';

    const bar  = document.getElementById('goal-bar');

    const wrap = document.getElementById('goal-progress-wrap');

    bar.style.width = goal.percent + '%';

    wrap.classList.toggle('goal-reached', goal.reached);

    const remaining = document.getElementById('goal-remaining');

    const badge     = document.getElementById('goal-reached-badge');

    if (goal.reached) {

      remaining.textContent = '🎉 Đủ tiền mua rồi!';

      remaining.style.color = 'var(--green)';

      badge.style.display   = 'inline-flex';

    } else {

      remaining.textContent = `còn thiếu ${fmt(goal.remaining)}`;

      remaining.style.color = 'var(--muted2)';

      badge.style.display   = 'none';

    }

  } else {

    gc.style.display = 'none'; ge.style.display = 'block';

  }



  // Streak mini

  const fire = streak.streak > 0 ? (streak.streak >= 30 ? '🔥🔥🔥' : streak.streak >= 7 ? '🔥🔥' : '🔥') : '💤';

  document.getElementById('streak-fire').textContent = fire;

  document.getElementById('streak-num').textContent  = streak.streak;

  document.getElementById('streak-mult').textContent = '×' + streak.multiplier.toFixed(1);

  document.getElementById('streak-hint').textContent = streak.streak > 0

    ? `${streak.today_cards}/${streak.min_cards} thẻ hôm nay`

    : (streak.today_cards >= streak.min_cards ? 'Ôn thêm để tính streak mới' : `Cần ${streak.cards_needed} thẻ nữa`);

  const bestEl = document.getElementById('streak-best');

  if (bestEl) bestEl.textContent = streak.best > 0 ? `Kỷ lục: ${streak.best} ngày` : '';



  // Rank mini

  document.getElementById('rank-emoji-sm').textContent  = rank.rank_emoji;

  document.getElementById('rank-label-sm').textContent  = rank.rank_label;

  document.getElementById('rank-xp-sm').textContent     = (rank.xp||0).toLocaleString('vi-VN');

  document.getElementById('rank-prog-sm').style.width   = rank.overall_pct + '%';

  document.getElementById('rank-prog-sm').style.background = `linear-gradient(90deg,${rank.rank_color},${rank.rank_color}aa)`;

  const mini = document.getElementById('rank-mini');

  if (mini) mini.style.borderColor = rank.rank_color + '66';

  document.getElementById('rank-next-sm').textContent = rank.is_max

    ? '🏆 Rank tối đa!' : `Tiếp: ${rank.next_rank?.label} (${rank.overall_pct}%)`;



  // Quest mini

  const questList = quests.quests || [];

  const qel = document.getElementById('quest-mini-list');

  if (!questList.length) {

    qel.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Chưa có quest.</div>';

  } else {

    qel.innerHTML = questList.map(q => {

      const pct = q.type === 'no_again_under' || q.type === 'no_purchase' || q.type === 'no_penalty'

        ? (q.done ? 100 : 0)

        : q.target > 0 ? Math.min(100, Math.round(q.progress / q.target * 100)) : 0;

      const col = q.done ? 'var(--green)' : 'var(--accent)';

      return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border)">

        <span style="font-size:16px">${q.emoji||'🎯'}</span>

        <div style="flex:1;min-width:0">

          <div style="font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${q.title}</div>

          <div style="background:var(--surface2);border-radius:3px;height:4px;margin-top:3px;overflow:hidden">

            <div style="height:100%;width:${pct}%;background:${col};border-radius:3px;transition:width .3s"></div>

          </div>

        </div>

        <span style="font-size:11px;font-weight:700;color:${col};flex-shrink:0">${q.done?'✅':''+pct+'%'}</span>

      </div>`;

    }).join('');

  }



  // Passive effects panel

  const passiveEffects = raw.passive_effects || [];

  const panel = document.getElementById('passive-panel');

  const list  = document.getElementById('passive-effects-list');

  if (passiveEffects.length) {

    panel.style.display = 'block';

    list.innerHTML = passiveEffects.map(p =>

      `<div class="passive-item">

        <span class="pi-icon">${p.emoji||'✨'}</span>

        <span class="pi-name">${p.name}</span>

        <span class="pi-val">${p.description||''}</span>

      </div>`

    ).join('');

  } else {

    panel.style.display = 'none';

  }



  // Auto-collect rent

  try {

    const rc = JSON.parse(await B.collectAllRent());

    if (rc.net > 0) toast('ok', `🏠 Thu tiền thuê tự động: +${fmt(rc.net)}`);

  } catch(e) {}



  // Quiz mini-card on dashboard — chỉ hiển thị stats, không còn thông báo "cứ 20 thẻ"

  try {

    const qs = JSON.parse(await B.getQuizStats());

    document.getElementById('dash-quiz-acc').textContent    = qs.total > 0 ? qs.accuracy + '%' : '—';

    document.getElementById('dash-quiz-streak').textContent = qs.streak;

    document.getElementById('dash-quiz-total').textContent  = qs.total;

  } catch(_) {}



  // Achievement mini

  try {

    await refreshAchievementMini();

    // Check nếu có achievement mới từ dashboard data

    if (raw.achievement?.recent?.length) {

      raw.achievement.recent.forEach(a => {

        if (a.unlocked && !a.claimed) showAchievementToast(a);

      });

    }

  } catch(_) {}

}



function updateAgainMonitor(a) {

  const count   = a.count || 0;

  const penalty = a.penalty_total || 0;

  const status  = a.status || 'normal';

  const maxBar  = 65; // 65 lần = 100% progress bar



  document.getElementById('again-count-big').textContent = count;

  document.getElementById('again-progress').style.width  = Math.min(count/maxBar*100, 100) + '%';

  document.getElementById('again-penalty-today').textContent = `Phạt hôm nay: ${fmt(penalty)}`;



  const badge = document.getElementById('again-status-badge');

  const hint  = document.getElementById('again-hint');

  const mon   = document.getElementById('again-monitor');



  if (status === 'heavy') {

    badge.textContent = '🔴 PHẠT NẶNG'; badge.className = 'badge badge-red';

    hint.textContent  = `Phạt ×2 mỗi lần bấm Again! (${count} lần)`;

    mon.style.borderColor = 'var(--red)';

  } else if (status === 'penalty') {

    badge.textContent = '🚨 Đang bị phạt'; badge.className = 'badge badge-red';

    hint.textContent  = `Mỗi lần Again tiếp theo đều bị phạt tiền!`;

    mon.style.borderColor = 'rgba(239,68,68,.5)';

  } else if (status === 'warn') {

    badge.textContent = '⚠️ Cảnh báo'; badge.className = 'badge badge-yellow';

    hint.textContent  = `Còn ${55 - count} lần nữa sẽ bị phạt!`;

    mon.style.borderColor = 'rgba(245,158,11,.5)';

  } else {

    badge.textContent = '✅ Bình thường'; badge.className = 'badge badge-green';

    hint.textContent  = count === 0 ? 'Hôm nay chưa bấm Again 🎉' : `Còn ${50 - count} lần tới ngưỡng cảnh báo`;

    mon.style.borderColor = 'var(--border)';

  }

}



// ════════════════════════════════════════════

//  SHOP  — Category Cards + Modal

// ════════════════════════════════════════════



const SHOP_CATEGORIES = [

  {key:'food',    label:'🍽️ Ẩm thực',                desc:'Consumable cho phiên học ngắn hạn: ăn uống, hồi tài nguyên, tăng reward, giữ nhịp học', color:'#f97316'},

  {key:'car',     label:'🚗 Showroom xe',              desc:'Tài sản di chuyển và lifestyle asset: buff gián tiếp, thiên về chất sống và hiệu suất', color:'#3b82f6'},

  {key:'tech',    label:'💻 Cửa hàng đồ công nghệ',    desc:'Productivity gear và scheduler build dài hạn: review nhiều hơn, cooldown thấp hơn', color:'#8b5cf6'},

  {key:'luxury',  label:'💎 Cửa hàng hàng hiệu',       desc:'Prestige asset và đồ sở hữu cao cấp: thiên về passive value, danh tiếng và lối chơi sở hữu', color:'#eab308'},

  {key:'re',      label:'🏠 Thị trường bất động sản',  desc:'Tài sản tạo dòng tiền thụ động và tích lũy giá trị theo thời gian', color:'#06b6d4'},

  {key:'finance', label:'🏦 Vật phẩm tài chính',       desc:'Core bank/invest tools: lãi suất, tốc độ tích lũy, thanh khoản và combo ngân hàng', color:'#f59e0b'},

  {key:'study',   label:'🎓 Vật phẩm học tập',         desc:'Tác động trực tiếp lên review, interval, ease và phần thưởng học thẻ', color:'#ec4899'},

  {key:'ins',     label:'🛡️ Bảo hiểm',                 desc:'Lớp phòng thủ tài chính: giảm rủi ro, giữ tài sản và hạn chế thiệt hại khi có biến cố', color:'#14b8a6'},

];



async function loadShop() {

  const raw = await B.getShopItems();

  allItems = JSON.parse(raw);

  renderShopCategories();

}



function renderShopCategories() {

  const el = document.getElementById('shop-categories');

  el.innerHTML = SHOP_CATEGORIES.map(c => {

    let countLabel;

    if (c.key === 'food') {

      const foodCount = allItems.filter(i => i.category === '🍽️ Ẩm thực').length;

      const drinkCount = allItems.filter(i => i.category === '🥤 Đồ uống').length;

      countLabel = `${foodCount} món ăn + ${drinkCount} đồ uống`;

    } else {

      const count = allItems.filter(i => i.category === c.label).length;

      countLabel = `${count} sản phẩm`;

    }

    return `<div class="shop-cat-card ${c.key}-card" onclick="openShopModal('${c.key}')" style="--cat-color:${c.color}">

      <div class="scc-icon">${c.label.slice(0,2)}</div>

      <div class="scc-name">${c.label.slice(2).trim()}</div>

      <div class="scc-desc">${c.desc}</div>

      <div class="scc-count">${countLabel}</div>

    </div>`;

  }).join('');

}



// ── Modal ──────────────────────────────────



let _activeStars    = new Set();

let _activeRarities = new Set();

let _activeFoodSubTab = 'food'; // 'food' hoặc 'drink'



function openShopModal(catKey) {

  const cat = SHOP_CATEGORIES.find(c => c.key === catKey);

  if (!cat) return;

  const modalThemeDesc = {

    food: 'Nhóm học tập ngắn hạn: ăn uống và boost dùng trong phiên học.',

    car: 'Nhóm tài sản dài hạn: phương tiện và lifestyle asset tác động gián tiếp đến hiệu suất hoặc đầu tư.',

    tech: 'Nhóm công nghệ: productivity, scheduler, combo build dài hạn.',

    luxury: 'Nhóm tài sản phong cách: thiên về prestige, đầu tư và lợi ích sở hữu.',

    crypto: 'Nhóm tài chính chủ động: giao dịch, staking và thị trường.',

    re: 'Nhóm tài chính tài sản: thu nhập thụ động và tích lũy dài hạn.',

    finance: 'Nhóm công cụ tài chính cốt lõi: tối ưu lãi suất, thanh khoản, tốc độ tích lũy và set ngân hàng.',

    study: 'Nhóm học tập trực tiếp: can thiệp reward, interval, ease và nhịp học.',

    ins: 'Nhóm phòng thủ tài chính: giảm rủi ro và bớt thiệt hại khi biến cố xảy ra.',

  };



  document.getElementById('shop-modal-title').textContent = cat.label;

  document.getElementById('shop-modal-subtitle').textContent = modalThemeDesc[catKey] || '';

  document.getElementById('shm-search').value = '';

  document.getElementById('shm-sort').value = '';

  _activeStars.clear();

  _activeRarities.clear();



  // Show/hide food/drink sub-tabs

  const foodTabs = document.getElementById('shm-food-tabs');

  if (catKey === 'food') {

    foodTabs.style.display = 'flex';

    _activeFoodSubTab = 'food';

    foodTabs.querySelectorAll('.food-tab').forEach(t => t.classList.toggle('active', t.dataset.sub === 'food'));

  } else {

    foodTabs.style.display = 'none';

  }



  // Extra filters per category

  const extra = document.getElementById('shm-extra-filters');

  let html = '';

  if (catKey === 'food') {

    html = `<div class="shm-stars-filter">${[1,2,3,4,5].map(s =>

      `<button class="btn btn-sm btn-ghost shm-star-btn" data-star="${s}" onclick="toggleStarFilter(${s},this)">${'⭐'.repeat(s)}</button>`

    ).join('')}</div>`;

  } else if (catKey === 'car') {

    const vgroups = [...new Set(allItems.filter(i=>i.category===cat.label).map(i=>i.vehicle_group).filter(Boolean))];

    const origins = [...new Set(allItems.filter(i=>i.origin).map(i=>i.origin))];

    const brands  = [...new Set(allItems.filter(i=>i.brand).map(i=>i.brand))];

    html = `<select id="shm-filter-vgroup" onchange="filterShopModal()" class="filter-select"><option value="">🚗 Loại xe</option>${vgroups.map(v=>`<option value="${v}">${v}</option>`).join('')}</select>

    <select id="shm-filter-origin" onchange="filterShopModal()" class="filter-select"><option value="">🌍 Khu vực</option>${origins.map(o=>`<option value="${o}">${o}</option>`).join('')}</select>

    <select id="shm-filter-brand" onchange="filterShopModal()" class="filter-select"><option value="">🏷️ Hãng</option>${brands.map(b=>`<option value="${b}">${b}</option>`).join('')}</select>`;

  } else if (catKey === 'study') {

    const labels = {uncommon:'🟢 Thường', rare:'🔵 Hiếm', epic:'🟣 Sử thi', legendary:'🟠 Huyền thoại'};

    html = `<div class="shm-rarity-filter">${['uncommon','rare','epic','legendary'].map(r =>

      `<button class="btn btn-sm btn-ghost shm-rarity-btn" data-rarity="${r}" onclick="toggleRarityFilter('${r}',this)">${labels[r]}</button>`

    ).join('')}</div>`;

  }

  extra.innerHTML = html;



  const filtered = _getFilteredItems(catKey);

  _renderShopModalGrid(filtered);

  _updateStats(filtered, catKey);



  document.getElementById('modal-shop-cat').classList.add('open');

  document.body.style.overflow = 'hidden';

}



function closeShopModal() {

  document.getElementById('modal-shop-cat').classList.remove('open');

  document.body.style.overflow = '';

}



// Close modal on overlay backdrop click

document.getElementById('modal-shop-cat').addEventListener('click', function(e) {

  if (e.target === this) closeShopModal();

});



function toggleStarFilter(star, btn) {

  if (_activeStars.has(star)) { _activeStars.delete(star); btn.classList.remove('active'); }

  else { _activeStars.add(star); btn.classList.add('active'); }

  filterShopModal();

}



function toggleRarityFilter(rarity, btn) {

  if (_activeRarities.has(rarity)) { _activeRarities.delete(rarity); btn.classList.remove('active'); }

  else { _activeRarities.add(rarity); btn.classList.add('active'); }

  filterShopModal();

}



function switchFoodTab(subTab, btn) {

  _activeFoodSubTab = subTab;

  document.querySelectorAll('.food-tab').forEach(t => t.classList.remove('active'));

  btn.classList.add('active');

  // Reset star filter when switching tabs

  _activeStars.clear();

  document.querySelectorAll('.shm-star-btn').forEach(b => b.classList.remove('active'));

  const filtered = _getFilteredItems('food');

  _renderShopModalGrid(filtered);

  _updateStats(filtered, 'food');

}



function filterShopModal() {

  const modal = document.getElementById('modal-shop-cat');

  if (!modal.classList.contains('open')) return;

  const title = document.getElementById('shop-modal-title').textContent;

  const cat = SHOP_CATEGORIES.find(c => c.label === title);

  if (!cat) return;

  const filtered = _getFilteredItems(cat.key);

  _renderShopModalGrid(filtered);

  _updateStats(filtered, cat.key);

}



function _getFilteredItems(catKey) {

  const cat = SHOP_CATEGORIES.find(c => c.key === catKey);

  if (!cat) return [];

  let list;

  if (catKey === 'food') {

    // Filter by sub-tab: food items → "🍽️ Ẩm thực", drink items → "🥤 Đồ uống"

    const targetCat = _activeFoodSubTab === 'food' ? '🍽️ Ẩm thực' : '🥤 Đồ uống';

    list = allItems.filter(i => i.category === targetCat);

  } else {

    list = allItems.filter(i => i.category === cat.label);

  }



  const q = document.getElementById('shm-search').value.toLowerCase();

  if (q) list = list.filter(i => i.name.toLowerCase().includes(q) || (i.description||'').toLowerCase().includes(q));



  if (catKey === 'food' && _activeStars.size > 0)

    list = list.filter(i => _activeStars.has(i.stars));

  if (catKey === 'car') {

    const vg = document.getElementById('shm-filter-vgroup');

    const o  = document.getElementById('shm-filter-origin');

    const b  = document.getElementById('shm-filter-brand');

    const vgv = vg ? vg.value : '';

    const ov  = o ? o.value : '';

    const bv  = b ? b.value : '';

    if (vgv) list = list.filter(i => i.vehicle_group === vgv);

    if (ov)  list = list.filter(i => i.origin === ov);

    if (bv)  list = list.filter(i => i.brand === bv);

  }

  if (catKey === 'study' && _activeRarities.size > 0)

    list = list.filter(i => _activeRarities.has(i.rarity));



  const sv = document.getElementById('shm-sort').value;

  if (sv === 'asc')  list.sort((a,b)=>a.price-b.price);

  else if (sv === 'desc') list.sort((a,b)=>b.price-a.price);

  else if (sv === 'name') list.sort((a,b)=>a.name.localeCompare(b.name));



  return list;

}



function _updateStats(items, catKey) {

  const el = document.getElementById('shm-stats');

  if (!items.length) { el.innerHTML = ''; return; }

  const minP = fmt(Math.min(...items.map(i=>i.price)));

  const maxP = fmt(Math.max(...items.map(i=>i.price)));

  if (catKey === 'car') {

    const groups = {}; items.forEach(i=>{const g=i.vehicle_group||'Khác'; groups[g]=(groups[g]||0)+1;});

    const parts = Object.entries(groups).map(([g,c])=>{

      const icon = g==='Ô tô'?'🚗':g==='Xe máy'?'🏍️':g==='Xe máy điện'?'🛵':g==='Xe điện'?'⚡':g==='Xe đạp'?'🚲':'❓';

      return `${icon} ${g}: ${c}`;

    }).join(' · ');

    const origins = [...new Set(items.map(i=>i.origin))].join(', ');

    el.innerHTML = `<span style="font-size:12px;color:var(--muted2)">📊 ${items.length} xe · ${minP}đ – ${maxP}đ · ${parts} · 🌍 ${origins}</span>`;

  } else if (catKey === 'food') {

    const avg = (items.reduce((s,i)=>s+(i.stars||0),0)/items.length).toFixed(1);

    const subLabel = _activeFoodSubTab === 'food' ? 'món ăn' : 'đồ uống';

    el.innerHTML = `<span style="font-size:12px;color:var(--muted2)">📊 ${items.length} ${subLabel} · ⭐ ${avg} sao · ${minP}đ – ${maxP}đ</span>`;

  } else if (catKey === 'study') {

    const rc = {}; items.forEach(i=>{rc[i.rarity]=(rc[i.rarity]||0)+1;});

    const parts = Object.entries(rc).map(([r,c])=>`${r==='uncommon'?'🟢':r==='rare'?'🔵':r==='epic'?'🟣':'🟠'}${c}`).join(' · ');

    el.innerHTML = `<span style="font-size:12px;color:var(--muted2)">📊 ${items.length} vật phẩm · ${parts}</span>`;

  } else {

    el.innerHTML = `<span style="font-size:12px;color:var(--muted2)">📊 ${items.length} sản phẩm · ${minP}đ – ${maxP}đ</span>`;

  }

}



function _renderShopModalGrid(items) {

  const grid = document.getElementById('shop-modal-grid');

  if (!items.length) {

    grid.innerHTML = '<div class="empty" style="grid-column:1/-1"><div class="ei">🔍</div><p>Không tìm thấy sản phẩm nào</p></div>';

    return;

  }

  grid.innerHTML = items.map(item => _renderShopModalCard(item)).join('');

}



function _renderShopModalCard(item) {

  const can   = curBal >= item.price;

  const owned = item.owned_count || 0;

  const isRE  = item.is_real_estate;

  const catKey = SHOP_CATEGORIES.find(c => c.label === item.category)?.key

    || (item.category === '🥤 Đồ uống' ? 'food' : undefined);

  const themeColors = {

    study: 'background:rgba(236,72,153,.16);color:#f472b6;border:1px solid rgba(236,72,153,.28)',

    tech: 'background:rgba(59,130,246,.16);color:#60a5fa;border:1px solid rgba(59,130,246,.28)',

    finance: 'background:rgba(245,158,11,.16);color:#fbbf24;border:1px solid rgba(245,158,11,.28)',

  };

  const roleColors = {

    'Buff phiên học': 'background:rgba(16,185,129,.12);color:#34d399;border:1px solid rgba(16,185,129,.25)',

    'Can thiệp scheduler': 'background:rgba(124,58,237,.12);color:#c084fc;border:1px solid rgba(124,58,237,.24)',

    'Tăng năng suất': 'background:rgba(59,130,246,.12);color:#93c5fd;border:1px solid rgba(59,130,246,.24)',

    'Ngân hàng': 'background:rgba(245,158,11,.12);color:#fbbf24;border:1px solid rgba(245,158,11,.24)',

    'Đầu tư chủ động': 'background:rgba(6,182,212,.12);color:#67e8f9;border:1px solid rgba(6,182,212,.24)',

    'Phòng thủ rủi ro': 'background:rgba(20,184,166,.12);color:#5eead4;border:1px solid rgba(20,184,166,.24)',

    'Dòng tiền thụ động': 'background:rgba(16,185,129,.12);color:#6ee7b7;border:1px solid rgba(16,185,129,.24)',

    'Bổ trợ': 'background:rgba(148,163,184,.12);color:#cbd5e1;border:1px solid rgba(148,163,184,.24)',

  };

  const themeRow = `<div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:center;margin-top:4px">

    <span class="badge" style="${themeColors[item.theme_group] || themeColors.finance};font-size:10px">${item.theme_icon || '✨'} ${item.theme_label || 'Bổ trợ'}</span>

    <span class="badge" style="${roleColors[item.role_label] || roleColors['Bổ trợ']};font-size:10px">${item.role_label || 'Bổ trợ'}</span>

    ${item.set_name ? `<span class="badge badge-purple" style="font-size:10px">🧩 ${item.set_name}</span>` : ''}

  </div>`;



  let extras = '';

  if (catKey === 'food') {

    let parts = [];

    if (item.stars) parts.push(`${'⭐'.repeat(item.stars)}${'☆'.repeat(5-item.stars)}`);

    if (item.expire_h) parts.push(`<span style="font-size:11px;color:var(--muted2)">⏳ HSD: ${item.expire_h}h</span>`);

    if (owned > 0) parts.push(`<span style="font-size:11px;color:var(--green)">✅ Đã mua x${owned}</span>`);

    extras = parts.length ? `<div class="stars-row" style="justify-content:center;gap:6px">${parts.join(' · ')}</div>` : '';

  }

  if (catKey === 'car' && item.brand) {

    const vgIcons = {'Ô tô':'🚗','Xe máy':'🏍️','Xe máy điện':'🛵','Xe điện':'⚡','Xe đạp':'🚲'};

    const vgIcon = vgIcons[item.vehicle_group]||'🚗';

    const oe = item.origin === 'Châu Á' ? '🌏' : item.origin === 'Châu Âu' ? '🌍' : '🌎';

    const typeField = item.car_type || item.bike_type || item.ebike_type || item.ev_type || item.cycle_type || '';

    extras = `<div class="car-info"><span class="vg-badge">${vgIcon} ${item.vehicle_group||''}</span><span class="origin-badge">${oe} ${item.origin}</span><span class="car-brand">${item.brand}</span><span style="font-size:11px;color:var(--muted2)">${typeField}</span></div>`;

  }

  if (catKey === 'study' && item.rarity) {

    const rc = {uncommon:'#10b981', rare:'#3b82f6', epic:'#8b5cf6', legendary:'#f59e0b'};

    const rl = {uncommon:'Thường', rare:'Hiếm', epic:'Sử thi', legendary:'Huyền thoại'};

    const color = rc[item.rarity]||'#888';

    const l = rl[item.rarity]||item.rarity;

    const isLeg = item.rarity === 'legendary';

    extras = `<div class="rarity-badge" style="background:${color}20;color:${color};border:1px solid ${color}40${isLeg ? ';animation:legendaryGlow 2s ease-in-out infinite' : ''}">${isLeg ? '👑' : item.rarity === 'epic' ? '💜' : item.rarity === 'rare' ? '💎' : '🟢'} ${l}</div>`;

  }



  const reInfo = isRE

    ? `<div style="font-size:11px;color:var(--cyan);margin-top:2px">🏠 Thuê ~${fmt(item.fair_rent||0)}/tháng</div>`

    : '';



  // Open detail modal on most item groups so theme/build info is visible everywhere

  const detailTypes = ['car','luxury','tech','crypto','re','finance','study','ins','food'];

  const canDetail = detailTypes.includes(catKey);



  return `<div class="item-card card-hover" style="${isRE?'border-color:rgba(6,182,212,.3)':''}${catKey==='study'?';background:var(--surface2)':''}${canDetail?';cursor:pointer':''}"

    ${canDetail ? `onclick="openItemDetail('${item.id}')"` : ''}>

    ${owned > 0 ? `<span class="badge badge-green owned-badge">✓ x${owned}</span>` : ''}

    <div class="item-img-wrap">${item.image_url

      ? `<img class="item-img" src="${item.image_url}" alt="${item.name}" loading="lazy">`

      : `<div class="item-emoji">${item.emoji||'📦'}</div>`

    }</div>

    <div class="item-name">${item.name}</div>

    ${themeRow}

    <div class="item-desc">${item.description||''}</div>

    ${item.effect_html ? `<div class="effect-row">${item.effect_html}</div>` : ''}

    ${extras}

    ${reInfo}

    <div class="item-price">${fmt(item.price)}</div>

    <button class="btn ${can?'btn-primary':'btn-ghost'} btn-full"

      ${can?'':'disabled'}

      onclick="event.stopPropagation();buyItem('${item.id}',this)">

      ${can ? (isRE ? '🏠 Mua BĐS' : '🛒 Mua ngay') : '💸 Chưa đủ tiền'}

    </button>

  </div>`;

}



// ── Shop Item Detail Modal ─────────────────



let _detailItem = null;



function openItemDetail(itemId) {

  const item = allItems.find(i => i.id === itemId);

  if (!item) return;

  _detailItem = item;

  const catKey = SHOP_CATEGORIES.find(c => c.label === item.category)?.key

    || (item.category === '🥤 Đồ uống' ? 'food' : undefined);



  // Image

  const img = document.getElementById('sd-img');

  const emoji = document.getElementById('sd-emoji');

  if (item.image_url) {

    img.src = item.image_url;

    img.style.display = 'block';

    emoji.style.display = 'none';

  } else {

    img.style.display = 'none';

    emoji.style.display = 'block';

    emoji.textContent = item.emoji || '📦';

  }



  // Name & description

  document.getElementById('sd-name').textContent = item.name;

  document.getElementById('sd-desc').textContent = item.description || '';



  // Badges

  const badges = document.getElementById('sd-badges');

  let badgeHtml = '';

  if (item.vehicle_group) {

    const vgIcons = {'Ô tô':'🚗','Xe máy':'🏍️','Xe máy điện':'🛵','Xe điện':'⚡','Xe đạp':'🚲'};

    badgeHtml += `<span class="badge badge-blue">${vgIcons[item.vehicle_group]||'🚗'} ${item.vehicle_group}</span>`;

  }

  if (item.brand) badgeHtml += `<span class="badge badge-purple">🏷️ ${item.brand}</span>`;

  if (item.origin) {

    const oe = item.origin === 'Châu Á' ? '🌏' : item.origin === 'Châu Âu' ? '🌍' : '🌎';

    badgeHtml += `<span class="badge" style="background:rgba(59,130,246,.15);color:#3b82f6">${oe} ${item.origin}</span>`;

  }

  if (item.stars) badgeHtml += `<span class="badge" style="background:rgba(245,158,11,.15);color:#f59e0b">${'⭐'.repeat(item.stars)}</span>`;

  if (item.rarity) {

    const rl = {uncommon:'🟢 Thường', rare:'💎 Hiếm', epic:'💜 Sử thi', legendary:'👑 Huyền thoại'};

    badgeHtml += `<span class="badge" style="background:rgba(124,58,237,.15);color:#a855f7">${rl[item.rarity]||item.rarity}</span>`;

  }

  badgeHtml += `<span class="badge" style="background:rgba(59,130,246,.15);color:#60a5fa">${item.theme_icon || '✨'} ${item.theme_label || 'Bổ trợ'}</span>`;

  badgeHtml += `<span class="badge" style="background:rgba(16,185,129,.15);color:#34d399">${item.role_label || 'Bổ trợ'}</span>`;

  if (item.set_name) badgeHtml += `<span class="badge badge-purple">🧩 ${item.set_name}</span>`;

  badges.innerHTML = badgeHtml;



  document.getElementById('sd-theme-note').textContent = item.theme_note || '';

  const setNote = document.getElementById('sd-set-note');

  if (item.set_name) {

    setNote.style.display = 'block';

    setNote.textContent = `Thuộc bộ ${item.set_name} — ghép đủ set để nhận bonus build bổ sung.`;

  } else {

    setNote.style.display = 'none';

    setNote.textContent = '';

  }



  // Specs grid

  const specs = document.getElementById('sd-specs');

  const specItems = [];

  if (item.vehicle_group) specItems.push({label:'Loại xe', value:item.vehicle_group});

  const typeField = item.car_type || item.bike_type || item.ebike_type || item.ev_type || item.cycle_type || '';

  if (typeField) specItems.push({label:'Kiểu dáng', value:typeField});

  if (item.brand) specItems.push({label:'Thương hiệu', value:item.brand});

  if (item.origin) specItems.push({label:'Xuất xứ', value:item.origin});

  if (item.stars) specItems.push({label:'Đánh giá', value:'⭐'.repeat(item.stars)});

  if (catKey === 'luxury') specItems.push({label:'Phân khúc', value:'Hàng hiệu cao cấp'});

  if (catKey === 'tech') specItems.push({label:'Phân khúc', value:'Công nghệ số'});

  if (catKey === 'finance') specItems.push({label:'Phân khúc', value:'Công cụ tài chính'});

  specs.innerHTML = specItems.map(s =>

    `<div class="sd-spec"><div class="label">${s.label}</div><div class="value">${s.value}</div></div>`

  ).join('');



  // Effects

  const effects = document.getElementById('sd-effects');

  const detailEffects = (item.effect_list && item.effect_list.length) ? item.effect_list : (item.effect ? [item.effect] : []);

  if (detailEffects.length) {

    const effIcons = {

      study_time_reduction:'⏱️', xp_multiplier:'⚡', stock_cooldown_reduction:'📉',

      crypto_cooldown_reduction:'🪙', equipment_slot:'🎒', disease_resistance:'💪',

      interest_bonus:'🏦', tax_reduction:'💰', health_boost:'❤️', passive_income_bonus:'💵',

      interest_speed_boost:'📈', instant_interest_cooldown:'⏳', new_card_limit_boost:'🆕',

      skill_cooldown_reduction:'🔧', review_count_bonus:'📚', food_freshness:'🍽️',

      interval_boost:'📈', easy_interval_bonus:'🎯', factor_boost:'🧠'

    };

    effects.innerHTML = detailEffects.map(e =>

      `<div class="sd-effect">

        <span class="sd-effect-icon">${effIcons[e.type]||'✨'}</span>

        <div><div class="sd-effect-name">${e.name||''}</div>

        <div class="sd-effect-desc">${e.desc||''}</div></div>

      </div>`

    ).join('');

  } else {

    effects.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Không có hiệu ứng đặc biệt</div>';

  }



  // Price & buy button

  const can = curBal >= item.price;

  document.getElementById('sd-price').textContent = fmt(item.price);

  const btn = document.getElementById('sd-buy-btn');

  btn.textContent = can ? '🛒 Mua ngay' : '💸 Chưa đủ tiền';

  btn.disabled = !can;

  btn.className = `btn ${can?'btn-primary':'btn-ghost'}`;



  // Show modal

  document.getElementById('modal-shop-detail').classList.add('open');

  document.body.style.overflow = 'hidden';

}



function closeItemDetail() {

  document.getElementById('modal-shop-detail').classList.remove('open');

  document.body.style.overflow = '';

  _detailItem = null;

}



// Close on overlay click

document.getElementById('modal-shop-detail').addEventListener('click', function(e) {

  if (e.target === this) closeItemDetail();

});



function buyItemFromDetail() {

  if (!_detailItem) return;

  const btn = document.getElementById('sd-buy-btn');

  buyItem(_detailItem.id, btn);

  // Re-check balance after purchase

  setTimeout(() => {

    if (_detailItem) openItemDetail(_detailItem.id);

  }, 500);

}



async function buyItem(id, btn) {

  btn.disabled = true;

  btn.textContent = '⏳…';

  const res = JSON.parse(await B.buyItem(id));

  if (res.ok) {

    toast('ok', `✅ Đã mua ${res.item_name}! Còn: ${fmt(res.new_balance)}`);

    await loadShop();

  } else {

    toast('err', '❌ ' + res.error);

    btn.disabled = false;

    btn.textContent = '🛒 Mua ngay';

  }

}



// ════════════════════════════════════════════

//  INVENTORY

// ════════════════════════════════════════════

async function reloadImages() {

  await B.refreshImageCache();

  const dir = await B.getImagesDir();

  document.getElementById('img-dir-path').textContent = dir;

  document.getElementById('img-dir-hint').style.display = 'block';

  await loadShop();

  toast('info', '🖼️ Đã làm mới cache ảnh!');

}



async function loadInventory() {

  // Kiểm tra đồ thiu trước

  const spoiledRaw = await B.checkSpoiledFood();

  const spoiled = JSON.parse(spoiledRaw);

  if (spoiled.length > 0) {

    toast('err', `🍂 ${spoiled.length} mặt hàng đồ ăn đã thiu và bị xoá khỏi kho!`);

  }



  const inv = JSON.parse(await B.getInventoryWithFreshness());

  const g   = document.getElementById('inv-grid');

  const total = inv.reduce((a,i)=>a+(i.quantity||1),0);

  document.getElementById('inv-badge').textContent = `${inv.length} loại • ${total} mặt hàng`;



  if (!inv.length) {

    g.innerHTML = `<div class="empty" style="grid-column:1/-1">

      <div class="ei">🎒</div>

      <p>Kho trống — ghé <a href="#" onclick="go('shop');return false" style="color:var(--accent2)">cửa hàng</a> nhé!</p>

    </div>`;

    return;

  }



  // Load active boosts để hiển thị strip

  await refreshBoostStrip();



  g.innerHTML = inv.map(i => {

    const isFood  = i.is_food;
    const isStudy = i.is_study;

    const eff    = i.effect || {};

    // REQ2 FIX: dùng active_slot thực từ Python freshness dict

    const activeSlot = i.active_slot || '';

    const slots      = i.food_slots || [];

    const firstSlot  = slots[0] || null;



    let foodExtra = '';

    if (isFood) {

      // Freshness bar

      let freshBar = '';

      if (firstSlot) {

        const pct   = firstSlot.fresh_pct || 0;

        const remH  = firstSlot.remaining_h || 0;

        const col   = pct > 50 ? 'var(--green)' : pct > 20 ? 'var(--yellow)' : 'var(--red)';

        freshBar = `

          <div style="width:100%;margin-top:4px">

            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">

              <span>Độ tươi</span><span style="color:${col}">${remH.toFixed(1)}h còn lại</span>

            </div>

            <div class="fresh-wrap" style="width:100%">

              <div style="height:100%;width:${pct}%;background:${col};border-radius:2px;transition:width .3s"></div>

            </div>

          </div>`;

      }

      // Effect description

      const effDesc = eff.desc || '';

      const canUse  = !!activeSlot;

      foodExtra = `

        <div style="font-size:11px;color:var(--green);margin-top:2px;text-align:center">${effDesc}</div>

        ${freshBar}

        <button class="btn btn-green" style="font-size:11px;padding:4px 10px;margin-top:6px;width:100%"

          ${canUse ? '' : 'disabled'}

          onclick="useFoodItem('${i.id}','${activeSlot}')">

          ${canUse ? '✨ Dùng ngay' : '⚠️ Không có slot'}

        </button>

        ${slots.length > 1 ? `<div style="font-size:10px;color:var(--muted2);margin-top:2px">${slots.length} phần trong kho</div>` : ''}`;

    } else if (isStudy) {
      let freshBar = '';
      if (firstSlot) {
        const pct   = firstSlot.fresh_pct || 0;
        const remH  = firstSlot.remaining_h || 0;
        const col   = pct > 50 ? 'var(--green)' : pct > 20 ? 'var(--yellow)' : 'var(--red)';
        freshBar = `

          <div style="width:100%;margin-top:4px">

            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">

              <span>Hạn sử dụng</span><span style="color:${col}">${remH.toFixed(1)}h còn lại</span>

            </div>

            <div class="fresh-wrap" style="width:100%">

              <div style="height:100%;width:${pct}%;background:${col};border-radius:2px;transition:width .3s"></div>

            </div>

          </div>`;

      }

      const effDesc = eff.desc || '';

      const canUse  = !!activeSlot;

      foodExtra = `

        <div style="font-size:11px;color:var(--accent2);margin-top:2px;text-align:center">${effDesc}</div>

        ${freshBar}

        <button class="btn btn-primary" style="font-size:11px;padding:4px 10px;margin-top:6px;width:100%"

          ${canUse ? '' : 'disabled'}

          onclick="useStudyItem('${i.id}','${activeSlot}')">

          ${canUse ? '📖 Áp dụng' : '⚠️ Hết hạn'}

        </button>

        ${slots.length > 1 ? `<div style="font-size:10px;color:var(--muted2);margin-top:2px">${slots.length} cái trong kho</div>` : ''}`;

    }



    return `

    <div class="inv-card ${isFood ? 'food-card' : ''}">

      <div class="item-img-wrap" style="width:90px;height:90px">

        ${i.image_url

          ? `<img class="item-img" style="width:90px;height:90px" src="${i.image_url}" alt="${i.name}">`

          : `<div style="font-size:36px">${i.emoji||'📦'}</div>`

        }

      </div>

      <div style="font-size:13px;font-weight:700">${i.name}</div>

      <div style="font-size:11px;color:var(--muted2)">${i.description||''}</div>

      ${!isFood && i.effect_html ? `<div class="effect-row">${i.effect_html}</div>` : ''}

      <span class="badge ${isFood ? 'badge-green' : 'badge-purple'}" style="font-size:10px">

        ${isFood ? '🍽️ ' : ''}${i.category||''}

      </span>

      <span class="badge badge-green">x${i.quantity}</span>

      <div style="font-size:11px;color:var(--yellow);font-weight:700">${fmt(i.price)}</div>

      ${foodExtra}

    </div>`;

  }).join('');

}



async function useFoodItem(itemId, slotId) {

  const res = JSON.parse(await B.activateFoodBoost(itemId, slotId));

  if (res.ok) {

    toast('ok', `⚡ ${res.message || 'Boost đã kích hoạt!'}`);

    await loadInventory();

    await refreshBoostStrip();

  } else {

    toast('err', '❌ ' + (res.error || 'Lỗi kích hoạt boost'));

  }

}



async function useStudyItem(itemId, slotId) {

  const res = JSON.parse(await B.activateFoodBoost(itemId, slotId));

  if (res.ok) {

    toast('ok', `📖 ${res.message || 'Đã áp dụng vật phẩm học tập!'}`);

    await loadInventory();

    await refreshBoostStrip();

  } else {

    toast('err', '❌ ' + (res.error || 'Lỗi kích hoạt vật phẩm học tập'));

  }

}


// ════════════════════════════════════════════════════════════
//  GARAGE
// ════════════════════════════════════════════════════════════

async function loadGarage() {

  const res = JSON.parse(await B.getGarageData());

  const garage = res.garage || [];

  const active = res.active_vehicle;

  const slots  = res.total_slots || 1;



  // ── Slot info ──

  document.getElementById('garage-slot-text').textContent =

    `${garage.length} / ${slots} slot`;



  // ── Active vehicle banner ──

  const banner = document.getElementById('garage-active-banner');

  if (active) {

    banner.style.display = 'block';

    document.getElementById('gab-emoji').textContent = active.emoji || '🚗';

    document.getElementById('gab-name').textContent = active.name || '';

    // Durability bar
    const dupPct = active.durability_pct || 0;
    const dupCol = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';
    document.getElementById('gab-dup').textContent = `${active.durability || 0}/${active.max_durability || 0}`;
    const dupBar = document.getElementById('gab-dup-bar');
    dupBar.style.width = dupPct + '%';
    dupBar.style.background = dupCol;

    // Fuel section
    const fuelSection = document.getElementById('gab-fuel-section');
    const manualLabel = document.getElementById('gab-manual-label');

    if (active.fuel_type && active.fuel_type !== 'manual') {
      fuelSection.style.display = 'block';
      manualLabel.style.display = 'none';

      const unit = active.fuel_type === 'electric' ? 'kWh' : 'L';
      const fuelLabel = active.fuel_type === 'electric' ? '🔋 Pin' : '⛽ Xăng';
      document.getElementById('gab-fuel-label').textContent = fuelLabel;

      const fuelPct = active.fuel_pct || 0;
      const fuelCol = fuelPct > 50 ? 'var(--green)' : fuelPct > 20 ? 'var(--yellow)' : 'var(--red)';
      document.getElementById('gab-fuel').textContent = `${active.fuel_level || 0}/${active.max_fuel || 0} ${unit}`;
      const fuelBar = document.getElementById('gab-fuel-bar');
      fuelBar.style.width = fuelPct + '%';
      fuelBar.style.background = fuelCol;
    } else {
      fuelSection.style.display = 'none';
      manualLabel.style.display = 'block';
    }

  } else {

    banner.style.display = 'none';

  }



  // ── Vehicle cards ──

  const grid = document.getElementById('garage-grid');



  if (!garage.length) {

    grid.innerHTML = '<div class="empty"><div class="ei">🏗️</div><p>Garage trống — ghé <a href="#" onclick="go(\'shop\');return false" style="color:var(--accent2)">cửa hàng</a> mua xe nhé!</p></div>';

    return;

  }



  grid.innerHTML = garage.map(v => {

    const isActive      = v.is_active;
    const inRepair      = v.in_repair;
    const maintDue      = v.maintenance_due;
    const inBreakdown   = v.breakdown_repair;
    const fuelType      = v.fuel_type || 'gasoline';
    const isManual      = fuelType === 'manual';
    const isElectric    = fuelType === 'electric';
    const fuelUnit      = isElectric ? 'kWh' : 'L';
    const vg            = v.vehicle_group || 'Ô tô';

    // Emoji theo nhóm xe
    const vgEmojiMap = {'Ô tô':'🚗','Xe điện':'⚡','Xe máy':'🏍️','Xe máy điện':'🛵','Xe đạp':'🚲'};
    const driveEmoji = vgEmojiMap[vg] || '🚗';

    // Status badges
    let statusBadge = '';
    if (isActive)      statusBadge = '<span class="badge badge-green" style="font-size:10px">✅ Đang lái</span>';
    else if (inRepair) statusBadge = '<span class="badge badge-red"   style="font-size:10px;background:rgba(239,68,68,.15);color:var(--red)">🔧 Đang sửa</span>';
    else if (inBreakdown) statusBadge = '<span class="badge" style="font-size:10px;background:rgba(239,68,68,.15);color:var(--red)">💥 Sự cố</span>';
    else if (maintDue) statusBadge = '<span class="badge badge-yellow" style="font-size:10px">⚠️ Bảo dưỡng</span>';
    else if (!isManual && (v.fuel_level || 0) <= 0) statusBadge = '<span class="badge badge-red" style="font-size:10px">🪫 Hết nhiên liệu</span>';

    // Durability bar
    const dupPct = v.durability_pct || 0;
    const dupCol = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';
    const dupBar = `<div style="margin-top:5px">
      <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">
        <span>🔩 Độ bền</span>
        <span style="color:${dupCol};font-weight:600">${v.durability || 0} / ${v.max_durability || 0}</span>
      </div>
      <div class="fresh-wrap" style="width:100%;margin-top:2px">
        <div style="height:100%;width:${dupPct}%;background:${dupCol};border-radius:2px;transition:width .4s"></div>
      </div>
    </div>`;

    // Fuel bar
    let fuelBar = '';
    if (!isManual) {
      const fuelPct  = v.fuel_pct || 0;
      const fuelCol  = fuelPct > 30 ? 'var(--green)' : fuelPct > 10 ? 'var(--yellow)' : 'var(--red)';
      const flLabel  = isElectric ? '🔋 Pin' : '⛽ Xăng';
      const fuelLvl  = typeof v.fuel_level === 'number' ? v.fuel_level.toFixed(1) : '0';
      let chargingTag = '';
      if (v.is_charging) {
        const cm = Math.max(0, Math.floor((v.charge_remaining || 0) / 60));
        chargingTag = ` <span style="color:var(--accent2);font-size:9px">⚡ Đang sạc (~${cm}p)</span>`;
      }
      fuelBar = `<div style="margin-top:5px">
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">
          <span>${flLabel}${chargingTag}</span>
          <span style="color:${fuelCol};font-weight:600">${fuelLvl} / ${v.max_fuel || 0} ${fuelUnit}</span>
        </div>
        <div class="fresh-wrap" style="width:100%;margin-top:2px">
          <div style="height:100%;width:${fuelPct}%;background:${v.is_charging?'var(--accent2)':fuelCol};border-radius:2px;transition:width .4s"></div>
        </div>
      </div>`;
    } else {
      fuelBar = `<div style="margin-top:5px;font-size:10px;color:var(--muted2)">
        🚲 Không tốn nhiên liệu &nbsp;•&nbsp; <span style="color:var(--green)">Giảm 15% sự kiện khẩn cấp</span>
      </div>`;
    }

    // Sell estimate
    const sellEst = v.sell_estimate || 0;
    const sellLine = sellEst > 0
      ? `<div style="font-size:10px;color:var(--muted2);margin-top:2px">💰 Giá bán ước tính: <span style="color:var(--yellow)">${fmt(sellEst)}</span></div>`
      : '';

    // Action buttons
    let actions = '';

    if (isActive) {
      actions = `<button class="btn btn-ghost" style="font-size:11px;padding:4px 8px;width:100%" onclick="stopCurrentVehicle()">🛑 Dừng xe</button>`;

    } else if (inBreakdown) {
      const bdDone = v.breakdown_reviews_done || 0;
      const bdReq  = v.breakdown_reviews_required || 30;
      const bdPct  = Math.round(bdDone / bdReq * 100);
      actions = `<div style="font-size:10px;color:var(--red);text-align:center;padding:4px">
        💥 Đang sửa sự cố: ${bdDone}/${bdReq} thẻ (${bdPct}%)
        <div class="fresh-wrap" style="width:100%;margin-top:4px">
          <div style="height:100%;width:${bdPct}%;background:var(--red);border-radius:2px"></div>
        </div>
      </div>`;

    } else if (inRepair) {
      const remaining = Math.max(0, Math.floor((v.repair_until || 0) - Date.now()/1000));
      const rh = Math.floor(remaining/3600), rm = Math.floor((remaining%3600)/60);
      const rStr = rh > 0 ? `${rh}h${rm}p` : `${rm} phút`;
      actions = `<div style="font-size:10px;color:var(--muted2);text-align:center;padding:4px">🔧 Đang sửa — còn ${rStr}</div>`;

    } else if (v.durability <= 0) {
      actions = `<button class="btn btn-yellow" style="font-size:11px;padding:4px 8px;width:100%" onclick="repairVehicle('${v.item_id}')">🔧 Sửa chữa</button>`;

    } else if (maintDue) {
      actions = `<div style="display:flex;gap:4px">
        <button class="btn btn-yellow" style="font-size:11px;padding:4px 8px;flex:1" onclick="maintainVehicle('${v.item_id}')">🔧 Bảo dưỡng</button>
        <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;color:var(--red)" onclick="sellVehicleFromGarage('${v.item_id}')">💰 Bán</button>
      </div>`;

    } else {
      // Sẵn sàng lái
      let fuelActions = '';
      if (!isManual && !isElectric && (v.fuel_level||0) < (v.max_fuel||0)) {
        fuelActions += `<button class="btn btn-ghost" style="font-size:10px;padding:3px 6px" onclick="refuelVehicle('${v.item_id}')">⛽ Đổ xăng</button>`;
      }
      if (isElectric && !v.is_charging && (v.fuel_level||0) < (v.max_fuel||0)) {
        fuelActions += `<button class="btn btn-ghost" style="font-size:10px;padding:3px 6px" onclick="rechargeVehicle('${v.item_id}')">🔌 Sạc điện</button>`;
      }
      if (isElectric && v.is_charging) {
        fuelActions += `<span style="font-size:10px;color:var(--accent2);padding:3px 6px">⚡ Đang sạc...</span>`;
      }

      // Kiểm tra có thể lái không (hết nhiên liệu → disable)
      const noFuel = !isManual && (v.fuel_level||0) <= 0;
      const driveBtn = noFuel
        ? `<button class="btn" style="font-size:11px;padding:4px 8px;flex:1;opacity:.4;cursor:not-allowed" disabled title="${isElectric?'Hết điện, cần sạc':'Hết xăng, cần đổ'}">${driveEmoji} Lái xe</button>`
        : `<button class="btn btn-green" style="font-size:11px;padding:4px 8px;flex:1" onclick="useVehicle('${v.item_id}')">${driveEmoji} Lái xe</button>`;

      actions = `<div style="display:flex;gap:4px;flex-wrap:wrap">${driveBtn}${fuelActions}</div>
        <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;margin-top:4px;width:100%;color:var(--red)" onclick="sellVehicleFromGarage('${v.item_id}')">💰 Bán xe</button>`;
    }

    return `
      <div class="card" style="padding:12px;display:flex;flex-direction:column;gap:2px${isActive?' border:1px solid var(--green)':''}">
        <div style="display:flex;align-items:center;gap:8px">
          <div class="item-img-wrap" style="width:48px;height:48px;min-width:48px">
            ${v.image_url
              ? `<img class="item-img" style="width:48px;height:48px" src="${v.image_url}" alt="${v.name}">`
              : `<div style="font-size:24px">${v.emoji||driveEmoji}</div>`
            }
          </div>
          <div style="flex:1;min-width:0">
            <div style="font-size:13px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${v.name}</div>
            <div style="font-size:11px;color:var(--muted2)">${vg} &nbsp;•&nbsp; <span style="color:var(--yellow)">${fmt(v.price)}</span></div>
          </div>
          ${statusBadge}
        </div>
        ${dupBar}
        ${fuelBar}
        ${sellLine}
        <div style="margin-top:6px">${actions}</div>
      </div>`;

  }).join('');

}



async function useVehicle(vehicleId) {
  const res = JSON.parse(await B.selectVehicle(vehicleId));
  if (res.ok) {
    const ftLabel = res.fuel_type === 'manual' ? '🚲' : res.fuel_type === 'electric' ? '⚡' : '🚗';
    toast('ok', `${ftLabel} Đang lái xe!`);
    await loadGarage();
  } else {
    toast('err', '❌ ' + (res.error || 'Không thể lái xe'));
  }
}



async function stopCurrentVehicle() {

  const res = JSON.parse(await B.stopVehicle());

  if (res.ok) {

    toast('ok', '🛑 Đã dừng xe.');

    await loadGarage();

  } else {

    toast('err', '❌ ' + (res.error || 'Không thể dừng xe'));

  }

}



async function repairVehicle(vehicleId) {

  const res = JSON.parse(await B.startRepair(vehicleId));

  if (res.ok) {

    toast('ok', '🔧 Đã gửi sửa: ' + (res.item_name || '') + ' (' + (res.duration_str || '') + ')');

    await loadGarage();

  } else {

    toast('err', '❌ ' + (res.error || 'Không thể sửa'));

  }

}



async function maintainVehicle(vehicleId) {

  const res = JSON.parse(await B.doMaintenance(vehicleId));

  if (res.ok) {

    toast('ok', '🔧 Đã bảo dưỡng! Độ bền: ' + res.new_durability + '/' + res.max_durability);

    await loadGarage();

  } else {

    toast('err', '❌ ' + (res.error || 'Không thể bảo dưỡng'));

  }

}



async function refuelVehicle(vehicleId) {

  const res = JSON.parse(await B.refuelVehicle(vehicleId));

  if (res.ok) {

    toast('ok', '⛽ Đã đổ xăng! (' + fmt(res.cost) + ')');

    await loadGarage();

  } else {

    toast('err', '❌ ' + (res.error || 'Không thể đổ xăng'));

  }

}



async function rechargeVehicle(vehicleId) {

  const res = JSON.parse(await B.rechargeVehicle(vehicleId));

  if (res.ok) {

    toast('ok', '🔌 Đã sạc! (' + (res.charge_duration_str || '') + ')');

    await loadGarage();

  } else {

    toast('err', '❌ ' + (res.error || 'Không thể sạc'));

  }

}



async function sellVehicleFromGarage(vehicleId) {
  // Dùng sell_estimate đã tính sẵn từ backend (bao gồm time-based depreciation)
  const garageData = JSON.parse(await B.getGarageData());
  const vehicle = (garageData.garage || []).find(v => v.item_id === vehicleId);
  if (!vehicle) return;

  const price     = vehicle.price || 0;
  const sellEst   = vehicle.sell_estimate || 0;
  const lossAmt   = price - sellEst;
  const deprPct   = price > 0 ? Math.round((lossAmt / price) * 100) : 0;
  const dupPct    = vehicle.durability_pct || 0;

  if (!confirm(
    `💰 Bán xe: ${vehicle.name || ''}\n\n` +
    `• Giá mua gốc:      ${fmt(price)}\n` +
    `• Độ bền còn lại:   ${dupPct}%\n` +
    `• Khấu hao:         ${deprPct}%\n` +
    `• Giá bán ước tính: ${fmt(sellEst)}\n` +
    `• Bạn mất:          ${fmt(lossAmt)}\n\n` +
    `Xác nhận bán xe này?`
  )) return;

  const res = JSON.parse(await B.sellVehicle(vehicleId));

  if (res.ok) {
    toast('ok', `💰 Đã bán ${res.item_name || ''} — thu về ${fmt(res.sell_price)} (khấu hao ${res.depreciation_pct}%)`);
    await loadGarage();
  } else {
    toast('err', '❌ ' + (res.error || 'Không thể bán'));
  }
}



async function buyGarageSlot() {

  const res = JSON.parse(await B.buyGarageSlot());

  if (res.ok) {

    toast('ok', '✅ Đã mua thêm slot garage! (' + fmt(res.price) + ')');

    await loadGarage();

  } else {

    toast('err', '❌ ' + (res.error || 'Không thể mua slot'));

  }

}





let boostTickerInterval = null;



async function refreshBoostStrip() {

  const boosts = JSON.parse(await B.getActiveBoosts());

  const strip  = document.getElementById('boost-strip');

  const list   = document.getElementById('boost-strip-list');



  if (!boosts.length) {

    strip.style.display = 'none';

    if (boostTickerInterval) { clearInterval(boostTickerInterval); boostTickerInterval = null; }

    return;

  }



  strip.style.display = 'block';

  const render = () => {

    list.innerHTML = boosts.map(b => {

      let timer = '';

      if (b.remaining_s !== null && b.remaining_s !== undefined) {

        const s = Math.max(0, Math.floor(b.remaining_s));

        const m = Math.floor(s/60), sec = s%60;

        timer = m > 0 ? `${m}p${sec}s` : `${sec}s`;

        b.remaining_s = Math.max(0, (b.remaining_s||0) - 1);

      } else if (b.cards_left !== null && b.cards_left !== undefined) {

        timer = `còn ${b.cards_left} thẻ`;

      }

      const desc = b.desc ? ` — ${b.desc}` : '';

      return `<span style="margin-left:8px;color:var(--green)">${b.name}</span><span style="color:var(--muted2);font-size:11px">${desc}</span> <span style="color:var(--muted2)">(${timer})</span>`;

    }).join(' |');

  };

  render();

  if (boostTickerInterval) clearInterval(boostTickerInterval);

  boostTickerInterval = setInterval(render, 1000);

}



// ════════════════════════════════════════════

//  BANK

// ════════════════════════════════════════════

let selProduct = null;

let selPlan = null;

let bankProducts = [];

let bankTicker = null;

let bankData  = {};

let termDeps  = [];

let demandInterestLive = 0;

let termMode = 'open';



async function loadBank() {

  const [bdRaw, depsRaw, productsRaw] = await Promise.all([

    B.getBankData(), B.getTermDeposits(), B.getBankProducts()

  ]);

  bankData = JSON.parse(bdRaw);

  termDeps = JSON.parse(depsRaw);

  bankProducts = JSON.parse(productsRaw);

  demandInterestLive = bankData.demand_interest || 0;



  syncSelectedProduct();

  updateDemandRateLabel();

  updateBankOverview();

  renderProductGrid();

  renderPlanGrid();

  renderSendMoreOptions();

  updateProductUI();

  updateTermModeUI();

  updateTermPreview();

  renderDeposits();

  startBankTicker();

  loadCreditBanking();

}



// ── Bank View Toggle ──

function showBankDepositView() {

  const dv = document.getElementById('bank-deposit-view');

  const cv = document.getElementById('bank-credit-view');

  if (dv) dv.classList.add('active');

  if (cv) cv.classList.remove('active');

  document.querySelectorAll('.bvt-btn').forEach(b => b.classList.remove('active'));

  const firstBtn = document.querySelector('.bank-view-toggle .bvt-btn:first-child');

  if (firstBtn) firstBtn.classList.add('active');

}



function showBankCreditView() {

  const cv = document.getElementById('bank-credit-view');

  const dv = document.getElementById('bank-deposit-view');

  if (cv) cv.classList.add('active');

  if (dv) dv.classList.remove('active');

  document.querySelectorAll('.bvt-btn').forEach(b => b.classList.remove('active'));

  const creditBtn = document.querySelector('.bvt-btn.bvt-credit');

  if (creditBtn) creditBtn.classList.add('active');

  // Tải dữ liệu tín dụng nếu chưa có

  if (typeof loadCreditBanking === 'function') {

    loadCreditBanking();

  }

}



function goToBankCreditView() {

  go('bank');

  setTimeout(() => { showBankCreditView(); }, 80);

}



function syncSelectedProduct() {

  if (!bankProducts.length) {

    selProduct = null;

    selPlan = null;

    return;

  }

  const currentCode = selProduct?.code;

  selProduct = bankProducts.find(p => p.code === currentCode) || bankProducts[0];

  if (selProduct?.kind === 'term') {

    const currentMonths = selPlan?.months;

    selPlan = selProduct.terms.find(t => t.months === currentMonths) || selProduct.terms[0] || null;

  } else {

    selPlan = null;

  }

}



function updateDemandRateLabel() {

  const rate = (bankData.demand_rate || 0) * 100;

  const el = document.getElementById('demand-rate-label');

  if (el) el.textContent = `${rate.toFixed(rate >= 1 ? 1 : 2)}% / năm`;

}



function updateBankOverview() {

  document.getElementById('bov-wallet').textContent = fmt(bankData.wallet || 0);

  const demandVal = (bankData.demand_balance || 0) + demandInterestLive;

  document.getElementById('bov-demand').textContent = fmt(Math.floor(demandVal));

  document.getElementById('demand-int-live').textContent = fmt(Math.floor(demandInterestLive));



  const termVal = termDeps.reduce((s, d) => s + (d.total || d.principal || d.amount || 0), 0);

  document.getElementById('bov-term').textContent = fmt(Math.floor(termVal));

  document.getElementById('bov-total').textContent = fmt(Math.floor(demandVal + termVal));

}



function startBankTicker() {

  if (bankTicker) clearInterval(bankTicker);

  const rate = bankData.demand_rate || 0;

  const secsPerYear = 365 * 24 * 3600;

  const principal = bankData.demand_balance || 0;

  const ratePerSec = principal * rate / secsPerYear;



  termDeps.forEach(d => {

    if (!d.matured && (d.interest_mode || 'maturity') === 'maturity') {

      const r = d.rate || 0.04;

      const principal = d.principal || d.amount || 0;

      d._ratePerSec = principal * r / secsPerYear;

    } else {

      d._ratePerSec = 0;

    }

  });



  bankTicker = setInterval(() => {

    demandInterestLive += ratePerSec;

    document.getElementById('demand-int-live').textContent = fmt(Math.floor(demandInterestLive));



    termDeps.forEach(d => {

      if (!d.matured && d._ratePerSec > 0) {

        const principal = d.principal || d.amount || 0;

        d.total = (d.total || principal) + d._ratePerSec;

        d.interest = d.total - principal;

      }

      if (!d.matured) {

        d.seconds_left = Math.max(0, (d.seconds_left || 0) - 1);

        if (d.seconds_left <= 0) d.matured = true;

      }

    });



    updateBankOverview();



    termDeps.forEach(d => {

      const el = document.getElementById('dep-' + d.id);

      if (!el) return;

      el.querySelector('.dep-total').textContent = fmt(Math.floor(d.total || d.principal || d.amount || 0));

      const interestDisplay = (d.interest_mode || 'maturity') === 'upfront'

        ? Math.round(d.interest_paid_total || 0)

        : Math.floor(d.interest || 0);

      el.querySelector('.dep-interest').textContent = fmt(interestDisplay);

      el.querySelector('.term-progress-bar').style.width = `${d.matured ? 100 : (d.progress_pct || 0)}%`;

      const cdEl = el.querySelector('.dep-countdown');

      if (cdEl) cdEl.textContent = d.matured ? '✅ Đáo hạn!' : fmtCountdown(d.seconds_left || 0);

      const closeBtn = el.querySelector('.btn-close-dep');

      if (closeBtn && d.matured) {

        closeBtn.classList.remove('btn-ghost');

        closeBtn.classList.add('btn-green');

        closeBtn.textContent = '🏆 Tất toán nhận tiền';

      }

    });

  }, 1000);

}



function switchBankTab(tab) {

  document.querySelectorAll('.bank-tab').forEach((b, i) => {

    b.classList.toggle('active', ['open', 'deposits'][i] === tab);

  });

  document.querySelectorAll('.bank-panel').forEach(p => p.classList.remove('active'));

  document.getElementById('bp-' + tab).classList.add('active');

  if (tab === 'deposits') renderDeposits();

}



function renderProductGrid() {

  const grid = document.getElementById('bank-product-grid');

  if (!grid) return;

  grid.innerHTML = bankProducts.map(p => {

    const selected = selProduct?.code === p.code;

    const headline = p.kind === 'demand'

      ? `${p.rate_pct}%/năm`

      : `${p.terms[0]?.months || 0}T - ${p.terms[p.terms.length - 1]?.months || 0}T`;

    return `

      <div class="bank-product-card ${selected ? 'selected' : ''}" onclick="selectBankProduct('${p.code}')">

        <div class="bp-name">${p.label}</div>

        <div class="bp-rate">${headline}</div>

        <div class="bp-note">${p.note}</div>

      </div>`;

  }).join('');

}



function selectBankProduct(code) {

  selProduct = bankProducts.find(p => p.code === code) || null;

  if (!selProduct) return;

  if (selProduct.kind === 'term') {

    selPlan = selProduct.terms[0] || null;

  } else {

    selPlan = null;

  }

  if (selProduct.code !== 'accumulative' && termMode === 'add') termMode = 'open';

  renderProductGrid();

  renderPlanGrid();

  renderSendMoreOptions();

  updateProductUI();

  updateTermModeUI();

  updateTermPreview();

}



function updateProductUI() {

  const demandPanel = document.getElementById('demand-product-panel');

  const termPanel = document.getElementById('term-product-panel');

  const helpEl = document.getElementById('product-help');

  if (!selProduct) return;



  const help = `${selProduct.note}${selProduct.reference ? ` Tham khảo: ${selProduct.reference}.` : ''}`;

  if (helpEl) helpEl.textContent = help;



  const isDemand = selProduct.kind === 'demand';

  demandPanel.style.display = isDemand ? 'block' : 'none';

  termPanel.style.display = isDemand ? 'none' : 'block';

}



function renderPlanGrid() {

  const g = document.getElementById('plan-grid');

  if (!g) return;

  if (!selProduct || selProduct.kind !== 'term') {

    g.innerHTML = '';

    return;

  }

  g.innerHTML = selProduct.terms.map(p => `

    <div class="plan-card ${selPlan?.months === p.months ? 'selected' : ''}" id="pc-${p.months}" onclick="selectPlan(${p.months})">

      <div class="pc-label">${p.label}</div>

      <div class="pc-rate">${p.rate_pct}%/năm</div>

      <div class="pc-note">${productPlanNote(selProduct)}</div>

    </div>`).join('');

}



function productPlanNote(product) {

  if (!product) return '';

  if (product.code === 'accumulative') return 'Gửi góp linh hoạt';

  if (product.code === 'periodic') return 'Lĩnh lãi định kỳ';

  if (product.code === 'upfront') return 'Nhận lãi ngay';

  if (product.code === 'tiered') return 'Lãi tăng theo số tiền';

  return 'Tiền gửi có kỳ hạn';

}



function selectPlan(months) {

  if (!selProduct || selProduct.kind !== 'term') return;

  selPlan = selProduct.terms.find(t => t.months === months) || null;

  renderPlanGrid();

  updateTermPreview();

}



function setTermMode(mode) {

  if (mode === 'add' && selProduct?.code !== 'accumulative') return;

  termMode = mode;

  renderSendMoreOptions();

  updateTermModeUI();

  updateTermPreview();

}



function updateTermModeUI() {

  const isAdd = termMode === 'add' && selProduct?.code === 'accumulative';

  const amountInput = document.getElementById('term-amt');

  const addBtn = document.getElementById('term-mode-add');

  const openBtn = document.getElementById('term-mode-open');

  const submitBtn = document.getElementById('term-submit-btn');

  const sendMore = bankData.send_more || {};

  const eligibleDeps = termDeps.filter(d => d.allow_topup);



  openBtn?.classList.toggle('active', !isAdd);

  addBtn?.classList.toggle('active', isAdd);

  if (addBtn) addBtn.disabled = selProduct?.code !== 'accumulative';



  document.getElementById('term-open-fields').style.display = isAdd ? 'none' : 'block';

  document.getElementById('send-more-fields').style.display = isAdd ? 'block' : 'none';

  document.getElementById('term-mode-help').textContent = isAdd

    ? 'Chọn sổ tích lũy hiện có và gửi thêm tối đa 3 lần mỗi tuần.'

    : `Mở sổ mới cho sản phẩm "${selProduct?.label || 'tiền gửi'}".`;

  document.getElementById('term-amount-label').textContent = isAdd

    ? '💵 SỐ TIỀN GỬI THÊM'

    : `💵 SỐ TIỀN GỬI (tối thiểu ${fmt(selProduct?.min_amount || 0)})`;

  submitBtn.textContent = isAdd ? '➕ Gửi thêm vào sổ' : '📋 Mở sổ tiết kiệm';



  if (amountInput) {

    amountInput.min = String(isAdd ? 1000 : (selProduct?.min_amount || 100000));

    amountInput.step = isAdd ? '10000' : '100000';

  }



  submitBtn.disabled = isAdd && (!eligibleDeps.length || (sendMore.remaining || 0) <= 0);

}



function renderSendMoreOptions(selectedId = null) {

  const select = document.getElementById('send-more-passbook');

  const statusEl = document.getElementById('send-more-status');

  if (!select || !statusEl) return;



  const prevValue = selectedId || select.value;

  const sendMore = bankData.send_more || {};

  const eligibleDeps = termDeps.filter(d => d.allow_topup);



  if (!eligibleDeps.length) {

    select.innerHTML = '<option value="">Chưa có sổ tích lũy nào</option>';

    statusEl.textContent = 'Cần có ít nhất 1 sổ tích lũy để dùng tính năng gửi thêm.';

    return;

  }



  select.innerHTML = eligibleDeps.map(d => {

    const principal = d.principal || d.amount || 0;

    return `<option value="${d.id}">${d.product_label || d.label} #${d.id} • Gốc ${fmt(principal)}</option>`;

  }).join('');



  if (eligibleDeps.some(d => d.id === prevValue)) {

    select.value = prevValue;

  }



  statusEl.textContent = `Bạn đã gửi thêm ${sendMore.used || 0}/${sendMore.limit || 3} lần trong tuần này. Còn ${sendMore.remaining || 0} lượt.`;

}



function getSelectedSendMoreDeposit() {

  const id = document.getElementById('send-more-passbook')?.value;

  return termDeps.find(d => d.id === id) || null;

}



function openSendMore(id) {

  selectBankProduct('accumulative');

  switchBankTab('open');

  termMode = 'add';

  renderSendMoreOptions(id);

  updateTermModeUI();

  updateTermPreview();

}



function setAmt(id, v) {

  document.getElementById(id).value = v;

  updateTermPreview();

}



function setAmtAll() {

  document.getElementById('wd-amt').value = bankData.demand_balance || 0;

}



async function doDeposit() {

  const amt = parseInt(document.getElementById('dep-amt').value) || 0;

  if (amt <= 0) { toast('err','❌ Nhập số tiền hợp lệ!'); return; }

  const res = JSON.parse(await B.bankDeposit(amt));

  if (res.ok) {

    toast('ok', `📥 Đã gửi ${fmt(amt)}!`);

    await loadBank();

  } else { toast('err', '❌ ' + res.error); }

}



async function doWithdraw() {

  const amt = parseInt(document.getElementById('wd-amt').value) || 0;

  if (amt <= 0) { toast('err','❌ Nhập số tiền hợp lệ!'); return; }

  const res = JSON.parse(await B.bankWithdraw(amt));

  if (res.ok) {

    toast('ok', `📤 Đã rút ${fmt(amt)} về ví!`);

    await loadBank();

  } else { toast('err', '❌ ' + res.error); }

}



async function claimDemandInterest() {

  const res = JSON.parse(await B.bankClaimInterest());

  if (res.ok) {

    toast('ok', `💰 Nhận được ${fmt(res.interest)} tiền lãi!`);

    demandInterestLive = 0;

    await loadBank();

  } else { toast('info', 'ℹ️ Chưa có lãi để nhận.'); }

}



function updateTermPreview() {

  const previewEl = document.getElementById('term-preview');

  const amt = parseInt(document.getElementById('term-amt').value) || 0;

  if (amt <= 0 || !selProduct || selProduct.kind !== 'term') {

    previewEl.style.display = 'none';

    return;

  }



  let previewMonths = 0;

  let previewRate = 0;

  let interestMode = selProduct.interest_mode || 'maturity';



  if (termMode === 'add') {

    const dep = getSelectedSendMoreDeposit();

    if (!dep) {

      previewEl.style.display = 'none';

      return;

    }

    previewMonths = dep.term_months || 0;

    previewRate = dep.rate || 0;

    interestMode = dep.interest_mode || 'maturity';

  } else {

    if (!selPlan) {

      previewEl.style.display = 'none';

      return;

    }

    if (amt < (selProduct.min_amount || 0)) {

      previewEl.style.display = 'none';

      return;

    }

    previewMonths = selPlan.months;

    previewRate = selPlan.rate;

    if (selProduct.code === 'tiered') {

      const tiers = [...(selProduct.tiers || [])].sort((a, b) => (b.min_amount || 0) - (a.min_amount || 0));

      const tier = tiers.find(t => amt >= (t.min_amount || 0));

      if (tier) previewRate += tier.bonus_rate || 0;

    }

  }



  const years = previewMonths / 12;

  const isCompound = selProduct.code === 'accumulative';

  const total = isCompound

    ? amt * Math.pow(1 + previewRate / 12, 12 * years)

    : amt + (amt * previewRate * years);

  const interest = total - amt;



  document.getElementById('prev-principal').textContent = fmt(amt);

  document.getElementById('prev-interest').textContent = fmt(Math.round(interest));



  if (interestMode === 'upfront') {

    document.getElementById('prev-interest-label').textContent = 'Lãi nhận ngay';

    document.getElementById('prev-total-label').textContent = 'Gốc khi đáo hạn';

    document.getElementById('prev-total').textContent = fmt(amt);

  } else if (interestMode === 'periodic') {

    document.getElementById('prev-interest-label').textContent = 'Tổng lãi toàn kỳ';

    document.getElementById('prev-total-label').textContent = 'Gốc khi đáo hạn';

    document.getElementById('prev-total').textContent = fmt(amt);

  } else {

    document.getElementById('prev-interest-label').textContent = 'Lãi dự kiến';

    document.getElementById('prev-total-label').textContent = 'Tổng nhận';

    document.getElementById('prev-total').textContent = fmt(Math.round(total));

  }



  previewEl.style.display = 'block';

}

document.addEventListener('input', e => { if (e.target.id === 'term-amt') updateTermPreview(); });



function submitTermAction() {

  if (termMode === 'add') return sendMoreToTermDeposit();

  return openTermDeposit();

}



async function openTermDeposit() {

  if (!selProduct || selProduct.kind !== 'term') { toast('err','❌ Chọn loại tiền gửi trước!'); return; }

  if (!selPlan) { toast('err','❌ Chọn kỳ hạn trước!'); return; }



  const amt = parseInt(document.getElementById('term-amt').value) || 0;

  if (amt < (selProduct.min_amount || 0)) {

    toast('err', `❌ Tối thiểu ${fmt(selProduct.min_amount || 0)}!`);

    return;

  }



  const res = JSON.parse(await B.openTermDeposit(amt, selPlan.months, selProduct.code));

  if (res.ok) {

    let msg = `📋 Đã mở sổ ${res.product_label || selProduct.label}!`;

    if (res.interest_mode === 'upfront') {

      msg += ` Nhận ngay ${fmt(res.interest_paid_now || 0)} tiền lãi.`;

    } else {

      msg += ` Lãi dự kiến: ${fmt(res.interest_at_maturity || 0)}.`;

    }

    toast('ok', msg);

    switchBankTab('deposits');

    await loadBank();

  } else {

    toast('err', '❌ ' + res.error);

  }

}



async function sendMoreToTermDeposit() {

  const dep = getSelectedSendMoreDeposit();

  if (!dep) { toast('err', '❌ Chọn sổ tích lũy trước!'); return; }



  const sendMore = bankData.send_more || {};

  if ((sendMore.remaining || 0) <= 0) {

    toast('err', '❌ Bạn đã dùng hết 3 lượt gửi thêm trong tuần này.');

    updateTermModeUI();

    return;

  }



  const amt = parseInt(document.getElementById('term-amt').value) || 0;

  if (amt <= 0) { toast('err', '❌ Nhập số tiền hợp lệ!'); return; }



  const confirmed = confirm(

    `Xác nhận gửi thêm ${fmt(amt)} vào sổ "${dep.product_label || dep.label}" #${dep.id}?\n\n` +

    `Bạn còn ${sendMore.remaining || 0} lượt gửi thêm trong tuần này.`

  );

  if (!confirmed) return;



  const res = JSON.parse(await B.addTermDepositFunds(dep.id, amt));

  if (res.ok) {

    toast('ok', `➕ Đã gửi thêm ${fmt(amt)} vào sổ #${dep.id}!`);

    await loadBank();

    switchBankTab('deposits');

  } else {

    toast('err', '❌ ' + res.error);

    await loadBank();

  }

}



function depositSummaryLine(d, principal, interestMat) {

  const totalAtMaturity = Math.round(d.total_at_maturity || principal);

  if ((d.interest_mode || 'maturity') === 'upfront') {

    return `Đã nhận ngay: <span style="color:var(--yellow);font-weight:700">${fmt(Math.round(d.interest_paid_total || 0))}</span>

      &nbsp;|&nbsp; Đáo hạn nhận gốc: <span style="color:var(--green);font-weight:700">${fmt(principal)}</span>`;

  }

  if ((d.interest_mode || 'maturity') === 'periodic') {

    return `Tổng lãi toàn kỳ: <span style="color:var(--yellow);font-weight:700">${fmt(interestMat)}</span>

      &nbsp;|&nbsp; Đáo hạn nhận gốc: <span style="color:var(--green);font-weight:700">${fmt(principal)}</span>`;

  }

  return `Lãi khi đáo hạn: <span style="color:var(--yellow);font-weight:700">${fmt(interestMat)}</span>

    &nbsp;|&nbsp; Tổng nhận: <span style="color:var(--green);font-weight:700">${fmt(totalAtMaturity)}</span>`;

}



function depositInterestLabel(d) {

  const mode = d.interest_mode || 'maturity';

  if (mode === 'upfront') return 'Đã nhận';

  if (mode === 'periodic') return 'Lãi kỳ hiện tại';

  return 'Lãi hiện tại';

}



function depositTotalLabel(d) {

  const mode = d.interest_mode || 'maturity';

  if (mode === 'upfront') return 'Gốc còn khóa';

  if (mode === 'periodic') return 'Giá trị trong sổ';

  return 'Tổng hiện tại';

}



function renderDeposits() {

  const el = document.getElementById('deposits-list');

  if (!termDeps.length) {

    el.innerHTML = '<div class="empty"><div class="ei">📂</div><p>Chưa có sổ nào.</p></div>';

    return;

  }



  el.innerHTML = termDeps.map(d => {

    const matured = d.matured;

    const pct = d.matured ? 100 : (d.progress_pct || 0);

    const interestMat = Math.round(d.interest_at_maturity || 0);

    const principal = d.principal || d.amount || 0;

    const topupCount = d.topup_count || 0;

    const interestDisplay = (d.interest_mode || 'maturity') === 'upfront'

      ? Math.round(d.interest_paid_total || 0)

      : Math.floor(d.interest || 0);

    return `

    <div class="term-card ${matured ? 'matured' : ''}" id="dep-${d.id}">

      <div class="row-sb">

        <div>

          <span style="font-weight:700;font-size:14px">${d.product_label || d.label}</span>

          <span class="badge badge-purple" style="font-size:10px;margin-left:6px">${d.display_term || ''}</span>

          <span class="badge badge-blue" style="font-size:10px;margin-left:4px">${d.interest_mode_label || 'Lãi cuối kỳ'}</span>

          ${matured ? '<span class="badge badge-green" style="margin-left:4px">✅ Đáo hạn</span>' : ''}

          ${topupCount ? `<span class="badge badge-blue" style="margin-left:4px">+${topupCount} lần gửi thêm</span>` : ''}

        </div>

        <span style="font-size:11px;color:var(--muted2)">#${d.id}</span>

      </div>

      <div style="font-size:11px;color:var(--muted2);margin-top:5px">

        ${d.label} • ${(d.rate_pct || 0).toFixed(2)}%/năm

      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:10px 0;font-size:12px">

        <div><div style="color:var(--muted2)">Gốc</div><div style="font-weight:700">${fmt(principal)}</div></div>

        <div><div style="color:var(--muted2)">${depositInterestLabel(d)}</div><div class="dep-interest realtime-ticker" style="font-weight:700;color:var(--yellow)">${fmt(interestDisplay)}</div></div>

        <div><div style="color:var(--muted2)">${depositTotalLabel(d)}</div><div class="dep-total realtime-ticker" style="font-weight:800;color:var(--green)">${fmt(Math.floor(d.total || principal))}</div></div>

      </div>

      <div style="font-size:11px;color:var(--muted2);margin-bottom:4px">

        ${depositSummaryLine(d, principal, interestMat)}

      </div>

      <div class="term-progress"><div class="term-progress-bar ${matured ? 'done' : ''}" style="width:${pct}%"></div></div>

      <div class="row-sb" style="font-size:12px">

        <span class="dep-countdown" style="color:${matured ? 'var(--green)' : 'var(--muted2)'}">

          ${matured ? '✅ Đáo hạn!' : fmtCountdown(d.seconds_left || 0)}

        </span>

        <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">

          ${!matured && d.allow_topup ? `<button class="btn btn-blue" style="font-size:11px" onclick="openSendMore('${d.id}')">➕ Gửi thêm</button>` : ''}

          ${matured

            ? `<button class="btn btn-green btn-close-dep" onclick="closeDep('${d.id}',false)">🏆 Tất toán nhận tiền</button>`

            : `<button class="btn btn-ghost btn-close-dep" style="font-size:11px" onclick="confirmEarlyClose('${d.id}')">⚠️ Rút sớm</button>`

          }

        </div>

      </div>

    </div>`;

  }).join('');

}



async function closeDep(id, force) {

  const fn = force ? B.forceCloseTermDeposit : B.closeTermDeposit;

  const res = JSON.parse(await fn(id));

  if (res.ok) {

    const msg = res.matured

      ? `🏆 Tất toán! Nhận ${fmt(res.payout)}${res.interest_earned ? `, tổng lãi ${fmt(res.interest_earned)}` : ''}`

      : `📤 Rút sớm: nhận ${fmt(res.payout)}`;

    toast('ok', msg);

    await loadBank();

  } else if (res.early_withdraw) {

    toast('err', '⚠️ Sổ chưa đáo hạn. Dùng nút "Rút sớm".');

  } else {

    toast('err', '❌ ' + (res.error || 'Lỗi không xác định'));

  }

}



async function confirmEarlyClose(id) {

  const dep = termDeps.find(d => d.id === id);

  if (!dep) return;

  const countdown = fmtCountdown(dep.seconds_left || 0);

  const principal = dep.principal || dep.amount || 0;

  const upfrontPenalty = (dep.interest_mode || 'maturity') === 'upfront'

    ? `\nSố tiền nhận lại sẽ bị trừ phần lãi đã ứng trước.`

    : `\nBạn sẽ mất phần lãi chưa đến hạn.`;

  if (confirm(`⚠️ Rút sớm sổ "${dep.label}"?\n\nGốc hiện tại: ${fmt(principal)}.${upfrontPenalty}\nCòn ${countdown} nữa là đáo hạn.\n\nXác nhận rút sớm?`)) {

    await closeDep(id, true);

  }

}



function fmtCountdown(secs) {

  secs = Math.floor(secs);

  if (secs <= 0) return '✅ Đáo hạn!';

  const d = Math.floor(secs / 86400);

  const h = Math.floor((secs % 86400) / 3600);

  const m = Math.floor((secs % 3600) / 60);

  const s = secs % 60;

  if (d > 0) return `${d}n ${h}g ${m}p`;

  if (h > 0) return `${h}g ${m}p ${s}s`;

  return `${m}p ${s}s`;

}



// ════════════════════════════════════════════

//  FINANCE — redesigned

// ════════════════════════════════════════════



let _finTxns    = [];   // full txn list cached

let _finData    = null;

let _finBankData= null;



// ── Tab switcher ────────────────────────────

function switchFinTab(tab, btn) {

  const resolvedBtn = btn || [...document.querySelectorAll('.fin-tab')]

    .find(b => (b.getAttribute('onclick') || '').includes(`'${tab}'`));

  document.querySelectorAll('.fin-tab').forEach(b => b.classList.remove('active'));

  document.querySelectorAll('.fin-panel').forEach(p => p.classList.remove('active'));

  if (resolvedBtn) resolvedBtn.classList.add('active');

  document.getElementById('fin-panel-' + tab).classList.add('active');

  if (tab === 'charts' && _finTxns.length) {

    setTimeout(() => drawAllCharts(_finTxns, _finData), 50);

  }

}



// ── Main load ────────────────────────────────

async function loadFinance() {

  await B.syncLivingCosts();

  await refreshBalance();

  const [finRaw, bankRaw, txnRaw, residenceRaw, loanRaw, taxFullRaw, economyRaw] = await Promise.all([
    B.getFinanceData(),
    B.getBankData(),
    B.getTransactions(),
    B.getResidenceInfo(),
    B.getLoanStatus(),
    B.getFullTaxStatus(),
    B.getEconomyStatus(),
  ]);
  const fin  = JSON.parse(finRaw);

  const bk   = JSON.parse(bankRaw);

  const txns = JSON.parse(txnRaw);

  residenceData = JSON.parse(residenceRaw);

  loanStatusData = JSON.parse(loanRaw);

  taxFullData = JSON.parse(taxFullRaw);

  _finTxns    = txns;

  _finData    = fin;

  _finBankData= bk;



  // Tháng

  const now = new Date();

  document.getElementById('fin-month').textContent =

    `Tháng ${now.getMonth()+1}/${now.getFullYear()} — ${now.toLocaleDateString('vi-VN',{weekday:'long'})}`;



  // ── Stat cards ──

  const interest = Math.max(0, Math.floor((bk.total_value || 0) - (bk.total_savings || bk.savings || 0)) || (bk.interest || 0));

  const savings  = bk.total_savings || bk.savings || 0;

  // Sử dụng total_net_worth từ backend (bao gồm ví + NH + CK + Crypto + BĐS + xe)
  const total    = fin.total_net_worth || (curBal + (bk.total_value || savings + interest));

  document.getElementById('fin-wallet').textContent   = fmt(curBal);

  document.getElementById('fin-savings').textContent  = fmt(savings);

  document.getElementById('fin-interest').textContent = fmt(interest);

  document.getElementById('fin-total').textContent    = fmt(total);

  document.getElementById('fin-interest-sub').textContent = `Lãi chờ: ${fmt(interest)}`;



  // ── Cash flow (bao gồm cả chi phí sinh hoạt) ──

  const livingCost = fin.living_cost?.living_cost_mtd || 0;

  const totalSpending = fin.spending + livingCost;

  document.getElementById('fin-inc').textContent = fmt(fin.income);

  document.getElementById('fin-exp').textContent = fmt(totalSpending);

  const net = fin.income - totalSpending;

  const netEl = document.getElementById('fin-net');

  netEl.textContent  = (net >= 0 ? '+' : '-') + fmt(Math.abs(net));

  netEl.style.color  = net >= 0 ? 'var(--green)' : 'var(--red)';



  // ── Insights ──

  const daysInMonth = new Date(now.getFullYear(), now.getMonth()+1, 0).getDate();

  const daysPassed  = now.getDate();

  const dailyAvg    = daysPassed > 0 ? Math.round(fin.spending / daysPassed) : 0;

  const saveRate    = fin.income > 0 ? Math.round((fin.income - fin.spending) / fin.income * 100) : 0;

  const txnThisMonth = txns.filter(t => {

    try { return new Date(t.timestamp).getMonth() === now.getMonth(); } catch { return true; }

  }).length;

  document.getElementById('fin-daily-avg').textContent  = fmt(dailyAvg);

  document.getElementById('fin-save-rate').textContent  = saveRate + '%';

  document.getElementById('fin-txn-count').textContent  = txnThisMonth;

  const saveRateEl = document.getElementById('fin-save-rate');

  saveRateEl.style.color = saveRate >= 20 ? 'var(--green)' : saveRate >= 0 ? 'var(--yellow)' : 'var(--red)';



  // ── Budget donut + alerts ──

  const st  = fin.status;

  const prog = document.getElementById('fin-prog');

  const bdg  = document.getElementById('fin-budget-badge');

  const pctEl= document.getElementById('fin-budget-pct');

  const infoEl= document.getElementById('fin-budget-info');

  const alertEl= document.getElementById('fin-budget-alert');

  const alertDot= document.getElementById('fin-alert-dot');



  if (st.budget > 0) {

    const pct = Math.min(st.percent, 100);

    prog.style.width = pct + '%';

    pctEl.textContent = Math.round(pct) + '%';

    document.getElementById('fin-prog-spent').textContent   = `Đã chi: ${fmt(st.spent)}`;

    document.getElementById('fin-prog-remain').textContent  = `Còn lại: ${fmt(Math.max(0, st.remaining))}`;

    infoEl.textContent = `${fmt(st.spent)} / ${fmt(st.budget)} VND`;



    drawDonut('budget-donut-canvas', pct, pct >= 100 ? '#ef4444' : pct >= 80 ? '#f59e0b' : '#10b981');



    if (pct >= 100) {

      pctEl.style.color     = 'var(--red)';

      bdg.textContent        = '🚨 Vượt ngân sách!';

      bdg.className          = 'badge badge-red';

      alertEl.innerHTML      = '<div class="budget-alert danger">🚨 Bạn đã vượt ngân sách tháng này! Hãy kiểm soát chi tiêu.</div>';

      alertDot.style.display = 'block';

    } else if (pct >= 80) {

      pctEl.style.color     = 'var(--yellow)';

      bdg.textContent        = '⚠️ Sắp hết';

      bdg.className          = 'badge badge-yellow';

      alertEl.innerHTML      = `<div class="budget-alert warn">⚠️ Đã dùng ${Math.round(pct)}% ngân sách — còn ${fmt(st.remaining)} VND.</div>`;

      alertDot.style.display = 'block';

    } else if (pct >= 50) {

      pctEl.style.color     = 'var(--yellow)';

      bdg.textContent        = '📊 Đang theo dõi';

      bdg.className          = 'badge badge-yellow';

      alertEl.innerHTML      = `<div class="budget-alert safe">✅ Dùng ${Math.round(pct)}% — đang trong tầm kiểm soát.</div>`;

      alertDot.style.display = 'none';

    } else {

      pctEl.style.color     = 'var(--green)';

      bdg.textContent        = '✅ Bình thường';

      bdg.className          = 'badge badge-green';

      alertEl.innerHTML      = `<div class="budget-alert safe">✅ Còn ${fmt(st.remaining)} VND trong tháng này.</div>`;

      alertDot.style.display = 'none';

    }



    // Spending notifications (once per session per threshold)

    checkBudgetNotification(pct, fin.spending, st.budget);

  } else {

    prog.style.width           = '0%';

    pctEl.textContent          = '—';

    pctEl.style.color          = 'var(--muted2)';

    bdg.textContent            = '';

    infoEl.textContent         = 'Chưa đặt ngân sách';

    alertEl.innerHTML          = '<div class="budget-alert warn" style="cursor:pointer" onclick="openBudgetModal()">💡 Nhấn ⚙️ Ngân sách để đặt giới hạn chi tiêu.</div>';

    alertDot.style.display     = 'none';

    drawDonut('budget-donut-canvas', 0, '#64748b');

    document.getElementById('fin-prog-spent').textContent  = '';

    document.getElementById('fin-prog-remain').textContent = '';

  }

  document.getElementById('budget-inp').value = fin.budget || '';



  // ── Render economy controls ──
  renderEconomyControls(economyRaw);

  // ── Render transactions & tax ──
  renderTxns(txns);

  renderResidenceStatus(residenceData);

  renderLoanStatus(loanStatusData);

  renderFullTaxStatus(taxFullData);

  renderTaxStatus((taxFullData && taxFullData.wealth_tax) || {});



  // ── Draw charts if that tab is active ──

  const activePanel = document.querySelector('.fin-panel.active');

  if (activePanel && activePanel.id === 'fin-panel-charts') {

    setTimeout(() => drawAllCharts(txns, fin), 80);

  }

}

// ── Render economy controls ──────────────────

function renderEconomyControls(raw) {
  if (!raw) return;
  let data;
  try { data = JSON.parse(raw); } catch { return; }

  // ── Daily Cap ──
  const dc = data.daily_cap;
  if (dc) {
    const el = document.getElementById('econ-daily-cap');
    const detail = document.getElementById('econ-daily-cap-detail');
    if (el) el.textContent = `×${dc.mult_pct}%`;
    if (detail) {
      const nextInfo = dc.cards_until_next > 0
        ? ` (còn ${dc.cards_until_next} thẻ)`
        : ' (đã đạt giới hạn)';
      detail.textContent = `${dc.cards_today} thẻ hôm nay${nextInfo}`;
    }
  }

  // ── CPI / Lạm phát ──
  const cpi = data.cpi;
  if (cpi) {
    const el = document.getElementById('econ-cpi');
    const detail = document.getElementById('econ-cpi-detail');
    if (el) {
      const sign = cpi.cpi_pct >= 0 ? '+' : '';
      el.textContent = `${sign}${cpi.cpi_pct.toFixed(1)}%`;
      el.style.color = cpi.cpi_pct > 5 ? 'var(--red)' : cpi.cpi_pct > 2 ? 'var(--yellow)' : 'var(--text)';
    }
    if (detail) {
      const nextPct = cpi.cpi_pct + cpi.inflation_rate_per_tick;
      const toNext = cpi.cards_to_next_tick > 0
        ? `còn ${cpi.cards_to_next_tick} thẻ → +${nextPct.toFixed(1)}%`
        : `chờ tăng...`;
      detail.textContent = `${cpi.total_system_cards.toLocaleString('vi-VN')} thẻ hệ thống · ${toNext}`;
    }
  }

  // ── Wealth Tax ──
  const wt = data.wealth_tax;
  if (wt) {
    const el = document.getElementById('econ-wealth-tax');
    const detail = document.getElementById('econ-wealth-tax-detail');
    if (el) el.textContent = wt.tax_rate_pct > 0 ? `${wt.tax_rate_pct}%` : '0%';
    if (detail) {
      detail.textContent = wt.tax_rate_pct > 0
        ? `${wt.bracket_name} · ${fmtVND(wt.net_worth)}`
        : 'Miễn thuế';
    }
  }

  // ── Again Recovery Fee ──
  const fee = data.again_recovery_fee;
  if (fee !== undefined && fee !== null) {
    const el = document.getElementById('econ-again-fee');
    if (el) {
      el.textContent = fee > 0 ? fmtVND(fee) : '0đ';
      el.title = fee > 0
        ? `Phí phục hồi khi trả lời Again: ${fmtVND(fee)}`
        : 'Chưa có phí phục hồi';
    }
  }
}



// ── Spending notification (per session) ──────

const _notifiedThresholds = new Set();

function checkBudgetNotification(pct, spent, budget) {

  const thresholds = [

    {at:50,  msg:`📊 Đã dùng 50% ngân sách tháng — còn ${fmt(budget - spent)} VND.`, type:'info'},

    {at:80,  msg:`⚠️ Cảnh báo: Đã chi ${fmt(spent)} / ${fmt(budget)} (80%)!`, type:'err'},

    {at:100, msg:`🚨 Vượt ngân sách! Đã chi ${fmt(spent)} so với hạn mức ${fmt(budget)}.`, type:'err'},

  ];

  for (const t of thresholds) {

    if (pct >= t.at && !_notifiedThresholds.has(t.at)) {

      _notifiedThresholds.add(t.at);

      toast(t.type, t.msg);

    }

  }

}



// ── Transactions rendering ───────────────────

const TXN_ICONS  = {

  reward:'🎯', purchase:'🛒', deposit:'🏦', withdraw:'💸', interest:'💰', tax:'🏛️',

  penalty:'🚨', debug:'🔧', living_cost:'🏠', loan:'🏦', loan_interest:'📈',

  loan_repay:'💳', pit_tax:'🧾', land_tax:'🏡', transfer_tax:'🏘️', sct_tax:'🛍️', rent_income:'🏠'

};

const TXN_COLORS = {

  reward:'var(--green)', purchase:'var(--red)', deposit:'var(--blue)', withdraw:'var(--yellow)', interest:'var(--blue)',

  tax:'var(--yellow)', penalty:'var(--red)', debug:'var(--muted2)', living_cost:'var(--red)', loan:'var(--yellow)',

  loan_interest:'var(--yellow)', loan_repay:'var(--red)', pit_tax:'var(--yellow)', land_tax:'var(--yellow)',

  transfer_tax:'var(--yellow)', sct_tax:'var(--yellow)', rent_income:'var(--green)'

};

const TXN_LABELS = {

  reward:'Thu nhập', purchase:'Chi tiêu', deposit:'Tiết kiệm', withdraw:'Rút tiết kiệm', interest:'Lãi',

  tax:'Thuế tài sản', penalty:'Phạt', debug:'Debug', living_cost:'Sinh hoạt', loan:'Vay nóng',

  loan_interest:'Lãi vay', loan_repay:'Trả nợ', pit_tax:'Thuế TNCN', land_tax:'Thuế đất',

  transfer_tax:'Thuế chuyển nhượng', sct_tax:'Thuế SCT', rent_income:'Thu nhập cho thuê'

};

const TXN_MINUS  = new Set([

  'purchase','tax','penalty','deposit','living_cost','loan_interest','loan_repay','pit_tax','land_tax','transfer_tax','sct_tax'

]);



function renderTxns(txns, filter='all', search='') {

  const el = document.getElementById('txn-list');

  const lbl= document.getElementById('txn-count-label');

  let list = [...txns];

  if (filter && filter !== 'all') {

    if (filter === 'reward') list = list.filter(t => t.type === 'reward' || t.type === 'interest');

    else if (filter === 'tax') list = list.filter(t => (t.type || '').includes('tax') || t.type === 'land_tax');

    else if (filter === 'loan') list = list.filter(t => ['loan', 'loan_interest', 'loan_repay'].includes(t.type));

    else if (filter === 'living_cost') list = list.filter(t => t.type === 'living_cost');

    else list = list.filter(t => t.type === filter);

  }

  if (search) {

    const q = search.toLowerCase();

    list = list.filter(t => (t.description||'').toLowerCase().includes(q) || (t.type||'').includes(q));

  }

  lbl.textContent = list.length ? `${list.length} giao dịch` : '';

  if (!list.length) {

    el.innerHTML = '<div class="empty"><div class="ei">📭</div><p>Không có giao dịch nào</p></div>';

    return;

  }

  el.innerHTML = list.slice(0,80).map((t,i) => {

    const isMinus = TXN_MINUS.has(t.type);

    const color   = TXN_COLORS[t.type] || 'var(--text)';

    const pillBg  = isMinus ? 'rgba(239,68,68,.15)' : 'rgba(16,185,129,.15)';

    const pillColor=isMinus ? 'var(--red)' : 'var(--green)';

    const pillText= TXN_LABELS[t.type] || t.type;

    return `

    <div class="txn-item" onclick="openTxnDetail(${i})">

      <span class="txn-icon">${TXN_ICONS[t.type]||'📌'}</span>

      <div class="txn-body">

        <div class="txn-desc">${t.description || '—'}</div>

        <div class="txn-date">${t.date || ''}</div>

      </div>

      <span class="txn-type-pill" style="background:${pillBg};color:${pillColor}">${pillText}</span>

      <span class="txn-amount" style="color:${color}">${isMinus?'-':'+'}${fmt(t.amount)}</span>

    </div>`;

  }).join('');

}



function filterTxns() {

  const filter = document.getElementById('txn-filter').value;

  const search = document.getElementById('txn-search').value;

  renderTxns(_finTxns, filter, search);

}



function exportTxnsCSV() {

  if (!_finTxns || !_finTxns.length) {

    toast('warn', '⚠️ Không có giao dịch nào để xuất');

    return;

  }

  // Header

  const headers = ['Ngày', 'Loại', 'Số tiền', 'Mô tả'];

  const rows = _finTxns.map(t => [

    t.date || t.time || '',

    TXN_LABELS[t.type] || t.type,

    (TXN_MINUS.has(t.type) ? '-' : '+') + (t.amount || 0),

    (t.description || '').replace(/"/g, '""'),

  ]);

  const csv = [headers.join(','), ...rows.map(r => r.map(v => `"${v}"`).join(','))].join('\n');

  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });

  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');

  a.href = url;

  a.download = 'anki-finance-giao-dich.csv';

  document.body.appendChild(a);

  a.click();

  document.body.removeChild(a);

  URL.revokeObjectURL(url);

  toast('ok', '✅ Đã tải file CSV');

}



// ── Transaction detail modal ─────────────────

function openTxnDetail(idx) {

  const filter = document.getElementById('txn-filter').value;

  const search = document.getElementById('txn-search').value;

  let list = [..._finTxns];

  if (filter && filter !== 'all') {

    if (filter === 'reward') list = list.filter(t => t.type === 'reward' || t.type === 'interest');

    else if (filter === 'tax') list = list.filter(t => (t.type || '').includes('tax') || t.type === 'land_tax');

    else if (filter === 'loan') list = list.filter(t => ['loan', 'loan_interest', 'loan_repay'].includes(t.type));

    else if (filter === 'living_cost') list = list.filter(t => t.type === 'living_cost');

    else list = list.filter(t => t.type === filter);

  }

  if (search) {

    const q = search.toLowerCase();

    list = list.filter(t => (t.description||'').toLowerCase().includes(q));

  }

  const t = list[idx];

  if (!t) return;

  const isMinus = TXN_MINUS.has(t.type);

  const color   = TXN_COLORS[t.type] || 'var(--text)';

  document.getElementById('txn-detail-title').textContent = TXN_ICONS[t.type] + ' ' + (TXN_LABELS[t.type] || 'Giao dịch');

  document.getElementById('txn-detail-body').innerHTML = `

    <div style="text-align:center;padding:16px 0">

      <div style="font-size:48px;margin-bottom:8px">${TXN_ICONS[t.type]||'📌'}</div>

      <div style="font-size:32px;font-weight:900;color:${color}">${isMinus?'-':'+'}${fmt(t.amount)}</div>

      <div style="font-size:13px;color:var(--muted2);margin-top:4px">${t.description||'—'}</div>

    </div>

    <hr/>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:12px">

      <div style="background:var(--surface2);border-radius:8px;padding:10px">

        <div style="color:var(--muted2);margin-bottom:3px">Loại</div>

        <div style="font-weight:700">${TXN_LABELS[t.type]||t.type}</div>

      </div>

      <div style="background:var(--surface2);border-radius:8px;padding:10px">

        <div style="color:var(--muted2);margin-bottom:3px">Thời gian</div>

        <div style="font-weight:700">${t.date||'—'}</div>

      </div>

    </div>

    ${t.timestamp ? `<div style="font-size:11px;color:var(--muted);text-align:center">${new Date(t.timestamp).toLocaleString('vi-VN')}</div>` : ''}

  `;

  document.getElementById('modal-txn-detail').classList.add('open');

}

function closeTxnDetail() {

  document.getElementById('modal-txn-detail').classList.remove('open');

}



async function confirmClearTxns() {

  if (!confirm('Xoá toàn bộ lịch sử giao dịch?')) return;

  await B.clearTransactions();

  _finTxns = [];

  toast('ok','🗑️ Đã xoá lịch sử giao dịch!');

  renderTxns([]);

  document.getElementById('txn-count-label').textContent = '';

}



// ── Budget modal ─────────────────────────────

function openBudgetModal() {

  document.getElementById('modal-budget').classList.add('open');

}

function closeBudgetModal() {

  document.getElementById('modal-budget').classList.remove('open');

}

function setBudgetPreset(v) {

  document.getElementById('budget-inp').value = v || '';

}

async function saveBudget() {

  const v = parseInt(document.getElementById('budget-inp').value) || 0;

  await B.setBudget(v);

  closeBudgetModal();

  _notifiedThresholds.clear();

  toast('ok', v > 0 ? `🎯 Ngân sách: ${fmt(v)} VND/tháng` : '🗑️ Đã xoá ngân sách');

  loadFinance();

}



// ── Canvas: Donut chart ───────────────────────

function drawDonut(canvasId, pct, color, label) {

  const canvas = document.getElementById(canvasId);

  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  const W = canvas.width, H = canvas.height;

  const cx = W/2, cy = H/2, r = Math.min(W,H)/2 - 8, thick = 14;

  ctx.clearRect(0, 0, W, H);

  // Background ring

  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2);

  ctx.strokeStyle = 'rgba(255,255,255,0.07)'; ctx.lineWidth = thick; ctx.stroke();

  // Value arc

  const angle = (pct / 100) * Math.PI * 2 - Math.PI/2;

  ctx.beginPath(); ctx.arc(cx, cy, r, -Math.PI/2, angle);

  ctx.strokeStyle = color; ctx.lineWidth = thick;

  ctx.lineCap = 'round'; ctx.stroke();

  // Center text

  ctx.fillStyle = color;

  ctx.font = `900 ${Math.round(W*0.18)}px -apple-system,sans-serif`;

  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';

  ctx.fillText(Math.round(pct) + '%', cx, cy - 6);

  if (label) {

    ctx.font = `600 ${Math.round(W*0.1)}px -apple-system,sans-serif`;

    ctx.fillStyle = 'rgba(255,255,255,0.5)';

    ctx.fillText(label, cx, cy + Math.round(W*0.12));

  }

}



// ── Canvas: Bar chart ────────────────────────

function drawBarChart(canvasId, labels, incomes, expenses) {

  const canvas = document.getElementById(canvasId);

  if (!canvas) return;

  const ctx   = canvas.getContext('2d');

  const W     = canvas.offsetWidth || canvas.width || 400;

  canvas.width = W;

  const H     = canvas.height;

  ctx.clearRect(0, 0, W, H);

  const pad   = {top:20, right:10, bottom:30, left:40};

  const chartW = W - pad.left - pad.right;

  const chartH = H - pad.top - pad.bottom;

  const n      = labels.length;

  if (!n) return;

  const maxVal = Math.max(...incomes, ...expenses, 1);

  const bw     = (chartW / n) * 0.35;

  const gap    = (chartW / n) * 0.3;



  // Grid lines

  ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 1;

  for (let i=0;i<=4;i++) {

    const y = pad.top + chartH - (chartH * i / 4);

    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();

    ctx.fillStyle = 'rgba(255,255,255,0.35)'; ctx.font = '10px sans-serif';

    ctx.textAlign = 'right'; ctx.fillText(fmtK(maxVal * i/4), pad.left - 3, y + 3);

  }



  for (let i=0;i<n;i++) {

    const x0 = pad.left + i * (chartW/n) + gap;

    const x1 = x0 + bw;

    const hI  = (incomes[i] / maxVal) * chartH;

    const hE  = (expenses[i]/ maxVal) * chartH;



    // Income bar (green)

    const gradI = ctx.createLinearGradient(0, pad.top + chartH - hI, 0, pad.top + chartH);

    gradI.addColorStop(0,'#10b981'); gradI.addColorStop(1,'rgba(16,185,129,0.3)');

    ctx.fillStyle = gradI;

    ctx.fillRect(x0, pad.top + chartH - hI, bw, hI);



    // Expense bar (red)

    const gradE = ctx.createLinearGradient(0, pad.top + chartH - hE, 0, pad.top + chartH);

    gradE.addColorStop(0,'#ef4444'); gradE.addColorStop(1,'rgba(239,68,68,0.3)');

    ctx.fillStyle = gradE;

    ctx.fillRect(x1 + 2, pad.top + chartH - hE, bw, hE);



    // Label

    ctx.fillStyle = 'rgba(255,255,255,0.5)'; ctx.font = '10px sans-serif';

    ctx.textAlign = 'center';

    ctx.fillText(labels[i], x0 + bw + 1, H - pad.bottom + 14);

  }

  // Legend

  ctx.fillStyle='#10b981'; ctx.fillRect(pad.left, 4, 10, 8);

  ctx.fillStyle='rgba(255,255,255,0.6)'; ctx.font='10px sans-serif'; ctx.textAlign='left';

  ctx.fillText('Thu nhập', pad.left+13, 12);

  ctx.fillStyle='#ef4444'; ctx.fillRect(pad.left+80, 4, 10, 8);

  ctx.fillStyle='rgba(255,255,255,0.6)';

  ctx.fillText('Chi tiêu', pad.left+93, 12);

}



// ── Canvas: Donut pie (category) ─────────────

function drawPieChart(canvasId, segments) {

  const canvas = document.getElementById(canvasId);

  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  const W = canvas.width, H = canvas.height;

  const cx = W/2, cy = H/2, r = Math.min(W,H)/2 - 6;

  ctx.clearRect(0,0,W,H);

  const total = segments.reduce((a,s)=>a+s.value,0);

  if (!total) return;

  let angle = -Math.PI/2;

  for (const seg of segments) {

    const arc = (seg.value/total)*Math.PI*2;

    ctx.beginPath(); ctx.moveTo(cx,cy);

    ctx.arc(cx,cy,r,angle,angle+arc);

    ctx.fillStyle = seg.color; ctx.fill();

    ctx.strokeStyle = '#16161f'; ctx.lineWidth = 2; ctx.stroke();

    angle += arc;

  }

  // Inner hole

  ctx.beginPath(); ctx.arc(cx,cy,r*0.52,0,Math.PI*2);

  ctx.fillStyle = '#16161f'; ctx.fill();

  ctx.fillStyle = 'rgba(255,255,255,0.7)';

  ctx.font = `700 ${Math.round(W*0.13)}px sans-serif`;

  ctx.textAlign='center'; ctx.textBaseline='middle';

  ctx.fillText(segments.length + ' loại', cx, cy);

}



// ── Canvas: Line trend chart ─────────────────

function drawTrendChart(canvasId, txns) {

  const canvas = document.getElementById(canvasId);

  if (!canvas) return;

  const ctx  = canvas.getContext('2d');

  const W    = canvas.offsetWidth || canvas.width || 400;

  canvas.width = W;

  const H    = canvas.height;

  ctx.clearRect(0,0,W,H);

  const recent = txns.slice(0,20).reverse();

  if (recent.length < 2) {

    ctx.fillStyle='rgba(255,255,255,0.3)'; ctx.font='12px sans-serif';

    ctx.textAlign='center'; ctx.fillText('Cần ít nhất 2 giao dịch',W/2,H/2); return;

  }

  const pad = {top:12,right:12,bottom:20,left:10};

  const chartW = W - pad.left - pad.right;

  const chartH = H - pad.top - pad.bottom;



  // Simulate cumulative balance delta

  let vals = [];

  let cum = 0;

  for (const t of recent) {

    const delta = TXN_MINUS.has(t.type) ? -t.amount : t.amount;

    cum += delta;

    vals.push(cum);

  }

  const minV = Math.min(...vals);

  const maxV = Math.max(...vals, minV+1);

  const range = maxV - minV || 1;



  const points = vals.map((v,i) => ({

    x: pad.left + (i/(recent.length-1))*chartW,

    y: pad.top + chartH - ((v-minV)/range)*chartH,

  }));



  // Gradient fill

  const grad = ctx.createLinearGradient(0, pad.top, 0, H);

  grad.addColorStop(0,'rgba(124,58,237,0.35)');

  grad.addColorStop(1,'rgba(124,58,237,0.02)');

  ctx.beginPath(); ctx.moveTo(points[0].x, points[0].y);

  points.slice(1).forEach(p => ctx.lineTo(p.x, p.y));

  ctx.lineTo(points[points.length-1].x, H); ctx.lineTo(points[0].x, H);

  ctx.closePath(); ctx.fillStyle = grad; ctx.fill();



  // Line

  ctx.beginPath(); ctx.moveTo(points[0].x, points[0].y);

  points.slice(1).forEach(p => ctx.lineTo(p.x, p.y));

  ctx.strokeStyle='#a855f7'; ctx.lineWidth=2; ctx.lineJoin='round'; ctx.stroke();



  // Dots

  for (const p of points) {

    ctx.beginPath(); ctx.arc(p.x, p.y, 3, 0, Math.PI*2);

    ctx.fillStyle='#a855f7'; ctx.fill();

  }

}



// ── Draw all charts ───────────────────────────

function drawAllCharts(txns, fin) {

  // 1. Bar chart: group by type

  const typeGroups = {};

  for (const t of txns) {

    const k = TXN_LABELS[t.type] || t.type;

    if (!typeGroups[k]) typeGroups[k] = {inc:0, exp:0};

    if (TXN_MINUS.has(t.type)) typeGroups[k].exp += t.amount;

    else typeGroups[k].inc += t.amount;

  }

  const sortedGroups = Object.entries(typeGroups)

    .sort((a,b) => (b[1].inc+b[1].exp)-(a[1].inc+a[1].exp))

    .slice(0,6);

  drawBarChart('chart-incexp',

    sortedGroups.map(([k])=>k.substring(0,5)),

    sortedGroups.map(([,v])=>v.inc),

    sortedGroups.map(([,v])=>v.exp));



  // 2. Donut: category segments

  const catColors = {'Thu nhập':'#10b981','Chi tiêu':'#ef4444','Tiết kiệm':'#3b82f6','Rút tiết kiệm':'#f59e0b','Lãi':'#60a5fa','Thuế':'#f97316','Phạt':'#dc2626','Debug':'#64748b'};

  const catTotals = {};

  for (const t of txns) {

    const k = TXN_LABELS[t.type] || t.type;

    catTotals[k] = (catTotals[k]||0) + t.amount;

  }

  const pieSegs = Object.entries(catTotals)

    .filter(([,v])=>v>0)

    .sort((a,b)=>b[1]-a[1])

    .slice(0,6)

    .map(([k,v])=>({label:k, value:v, color: catColors[k]||'#7c3aed'}));

  drawPieChart('chart-category', pieSegs);



  // Legend

  const totalPie = pieSegs.reduce((a,s)=>a+s.value,0);

  document.getElementById('chart-category-legend').innerHTML =

    pieSegs.map(s=>`

      <div style="display:flex;align-items:center;gap:6px">

        <span style="width:10px;height:10px;border-radius:50%;background:${s.color};flex-shrink:0;display:inline-block"></span>

        <span style="flex:1;color:var(--muted2)">${s.label}</span>

        <span style="font-weight:700;color:var(--text)">${totalPie?Math.round(s.value/totalPie*100):0}%</span>

      </div>`).join('');



  // 3. Trend

  drawTrendChart('chart-trend', txns);

}



// ── Chart modal ───────────────────────────────

let _chartModalType = '';

function openChartModal(type) {

  _chartModalType = type;

  const titles = {incexp:'📊 Thu nhập vs Chi tiêu — Chi tiết', category:'🍩 Phân loại giao dịch', trend:'📈 Xu hướng số dư'};

  document.getElementById('modal-chart-title').textContent = titles[type] || 'Biểu đồ';

  document.getElementById('modal-chart-legend').innerHTML  = '';

  document.getElementById('modal-chart-stats').innerHTML   = '';

  document.getElementById('modal-chart').classList.add('open');

  setTimeout(() => drawModalChart(type), 80);

}

function closeChartModal() {

  document.getElementById('modal-chart').classList.remove('open');

}

function drawModalChart(type) {

  const canvas = document.getElementById('modal-chart-canvas');

  if (!canvas || !_finTxns) return;

  canvas.height = 260;

  if (type === 'incexp') {

    const typeGroups = {};

    for (const t of _finTxns) {

      const k = TXN_LABELS[t.type]||t.type;

      if (!typeGroups[k]) typeGroups[k]={inc:0,exp:0};

      if (TXN_MINUS.has(t.type)) typeGroups[k].exp+=t.amount;

      else typeGroups[k].inc+=t.amount;

    }

    const groups = Object.entries(typeGroups).sort((a,b)=>(b[1].inc+b[1].exp)-(a[1].inc+a[1].exp)).slice(0,8);

    drawBarChart('modal-chart-canvas', groups.map(([k])=>k.substring(0,6)), groups.map(([,v])=>v.inc), groups.map(([,v])=>v.exp));

    const totInc = _finTxns.filter(t=>!TXN_MINUS.has(t.type)).reduce((a,t)=>a+t.amount,0);

    const totExp = _finTxns.filter(t=>TXN_MINUS.has(t.type)).reduce((a,t)=>a+t.amount,0);

    document.getElementById('modal-chart-stats').innerHTML = `

      <div style="background:rgba(16,185,129,.1);border-radius:8px;padding:10px;text-align:center">

        <div style="font-size:11px;color:var(--muted2)">Tổng thu</div>

        <div style="font-weight:800;color:var(--green)">${fmt(totInc)}</div>

      </div>

      <div style="background:rgba(239,68,68,.1);border-radius:8px;padding:10px;text-align:center">

        <div style="font-size:11px;color:var(--muted2)">Tổng chi</div>

        <div style="font-weight:800;color:var(--red)">${fmt(totExp)}</div>

      </div>

      <div style="background:rgba(124,58,237,.1);border-radius:8px;padding:10px;text-align:center">

        <div style="font-size:11px;color:var(--muted2)">Chênh lệch</div>

        <div style="font-weight:800;color:${totInc-totExp>=0?'var(--green)':'var(--red)'}">${fmt(Math.abs(totInc-totExp))}</div>

      </div>`;

  } else if (type === 'category') {

    canvas.width=280; canvas.height=280;

    const catColors={'Thu nhập':'#10b981','Chi tiêu':'#ef4444','Tiết kiệm':'#3b82f6','Rút tiết kiệm':'#f59e0b','Lãi':'#60a5fa','Thuế':'#f97316','Phạt':'#dc2626','Debug':'#64748b'};

    const catTotals={};

    for (const t of _finTxns) { const k=TXN_LABELS[t.type]||t.type; catTotals[k]=(catTotals[k]||0)+t.amount; }

    const segs = Object.entries(catTotals).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([k,v])=>({label:k,value:v,color:catColors[k]||'#7c3aed'}));

    drawPieChart('modal-chart-canvas',segs);

    const tot=segs.reduce((a,s)=>a+s.value,0);

    document.getElementById('modal-chart-legend').innerHTML=`<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">`+

      segs.map(s=>`<div style="display:flex;align-items:center;gap:6px">

        <span style="width:10px;height:10px;border-radius:50%;background:${s.color};display:inline-block"></span>

        <span style="color:var(--muted2);font-size:11px">${s.label}: <strong style="color:var(--text)">${tot?Math.round(s.value/tot*100):0}% (${fmt(s.value)})</strong></span>

      </div>`).join('')+'</div>';

  } else if (type === 'trend') {

    drawTrendChart('modal-chart-canvas', _finTxns);

  }

}



// ── Helper: format K/M (safe) ──────────────────

function fmtK(v) {

  // Chuyển về string để xử lý số lớn

  const s = typeof v === 'string' ? v : String(v||0);

  const num = s.replace(/[^0-9-]/g, '');

  const len = num.length;

  if (len > 9) return num.slice(0, len-6) + '.' + num.slice(len-6, len-5) + 'B';

  if (len > 6) return num.slice(0, len-3) + '.' + num.slice(len-3, len-2) + 'M';

  if (len > 3) return num.slice(0, len-3) + 'K';

  return num;

}





// Reset modal

async function openResetModal() {

  const reason = getResetDisabledReason();

  if (reason) {

    updateResetButtonState();

    toast('err', '❌ ' + reason);

    return;

  }

  const phrase = await B.getConfirmPhrase();

  document.getElementById('reset-phrase-display').textContent = phrase;

  document.getElementById('reset-confirm-inp').value = '';

  document.getElementById('reset-error').textContent = '';

  document.getElementById('modal-reset').classList.add('open');

}

function closeResetModal() {

  document.getElementById('modal-reset').classList.remove('open');

}

async function doReset() {

  const inp = document.getElementById('reset-confirm-inp').value;

  const res = JSON.parse(await B.performReset(inp));

  if (res.ok) {

    closeResetModal();

    toast('ok', '✅ Đã reset toàn bộ tài sản. Chơi lại từ đầu!\n💰 Bạn nhận được 10.000.000 VND vốn khởi đầu.');

    await refreshBalance();

    updateResetButtonState();

    await loadSettings();

    await loadDashboard();

  } else {

    document.getElementById('reset-error').textContent = res.error;

  }

}



async function doHardReset() {

  if (!confirm('🔥 Reset cục bộ: Xoá SẠCH mọi dữ liệu kể cả lịch sử reset, lịch sử thuế, kiến thức tài chính. Chắc chắn?')) return;

  const inp = document.getElementById('reset-confirm-inp').value;

  if (!inp.trim()) {

    document.getElementById('reset-error').textContent = 'Vui lòng nhập cụm xác nhận.';

    return;

  }

  const res = JSON.parse(await B.performHardReset(inp));

  if (res.ok) {

    closeResetModal();

    toast('ok', '🔥 Đã reset CỤC BỘ toàn bộ dữ liệu!\n💰 Vẫn giữ 10.000.000 VND vốn khởi đầu.');

    await refreshBalance();

    updateResetButtonState();

    await loadSettings();

    await loadDashboard();

  } else {

    document.getElementById('reset-error').textContent = res.error;

  }

}

document.getElementById('modal-reset')?.addEventListener('click', e => {

  if (e.target === e.currentTarget) closeResetModal();

});



// ════════════════════════════════════════════

//  DEBUG TOOLS (1.1.0e)

// ════════════════════════════════════════════

async function runDebugScan() {

  const btn  = document.getElementById('debug-scan-btn');

  const out  = document.getElementById('debug-result');

  const min  = document.getElementById('debug-mini-status');

  if (!btn) return;

  btn.disabled = true;

  btn.textContent = '⏳ Đang quét...';

  out.style.display = 'block';

  out.innerHTML = '⏳ Đang kiểm tra dữ liệu...';

  min.textContent = '';

  try {

    const raw = await B.runDebugTools();

    const r = JSON.parse(raw);

    if (!r.ok) {

      out.innerHTML = '❌ ' + (r.error || 'Lỗi không xác định.');

      toast('err', '🔧 Gỡ lỗi thất bại!');

      return;

    }

    // Tạo báo cáo đẹp

    let html = '<div style="margin-bottom:8px;font-weight:700">✅ Kết quả gỡ lỗi</div>';

    if (r.cache_cleared) {

      html += '<div style="color:var(--green)">✔️ Bộ nhớ đệm (cache) đã được xoá</div>';

    }

    const noneFixed = r.fixed_none_keys || [];

    if (noneFixed.length > 0) {

      html += '<div style="color:var(--yellow);margin-top:4px">🔧 Đã sửa ' + noneFixed.length + ' key bị null/None:</div>';

      html += '<div style="font-size:10px;color:var(--muted2);max-height:120px;overflow-y:auto">';

      html += noneFixed.map(k => '&nbsp;&nbsp;• ' + k).join('<br>');

      html += '</div>';

    }

    const typeFixed = r.fixed_type_keys || [];

    if (typeFixed.length > 0) {

      html += '<div style="color:var(--yellow);margin-top:4px">🔧 Đã sửa ' + typeFixed.length + ' key sai kiểu dữ liệu:</div>';

      html += '<div style="font-size:10px;color:var(--muted2);max-height:120px;overflow-y:auto">';

      typeFixed.forEach(f => {

        html += '&nbsp;&nbsp;• <code>' + f.key + '</code>: expected <strong>' + f.expected + '</strong>, found <strong>' + f.found + '</strong><br>';

      });

      html += '</div>';

    }

    if (r.keys_ok > 0) {

      html += '<div style="color:var(--green);margin-top:4px">✔️ ' + r.keys_ok + '/' + r.total_scanned + ' keys hoạt động bình thường.</div>';

    }

    const errors = r.errors || [];

    if (errors.length > 0) {

      html += '<div style="color:var(--red);margin-top:4px">⚠️ ' + errors.length + ' lỗi phát sinh:</div>';

      html += '<div style="font-size:10px;color:var(--red);max-height:80px;overflow-y:auto">';

      errors.forEach(e => { html += '&nbsp;&nbsp;• ' + e + '<br>'; });

      html += '</div>';

    }

    if (noneFixed.length === 0 && typeFixed.length === 0 && errors.length === 0) {

      html += '<div style="color:var(--green);margin-top:4px">✨ Không phát hiện lỗi nào. Hệ thống sạch sẽ!</div>';

    }

    out.innerHTML = html;

    min.textContent = '🕒 Lần cuối: ' + new Date().toLocaleTimeString('vi-VN');

    toast('ok', '🔧 Gỡ lỗi hoàn tất!');

  } catch (e) {

    out.innerHTML = '❌ Lỗi: ' + e.message;

    toast('err', '🔧 Lỗi khi gỡ lỗi: ' + e.message);

  } finally {

    btn.disabled = false;

    btn.textContent = '🔍 Quét & Sửa lỗi';

  }

}

async function runDebugReport() {

  const out  = document.getElementById('debug-result');

  const min  = document.getElementById('debug-mini-status');

  const btn  = document.getElementById('debug-report-btn');

  if (!btn) return;

  btn.disabled = true;

  out.style.display = 'block';

  out.innerHTML = '⏝ Đang lấy báo cáo...';

  min.textContent = '';

  try {

    const raw = await B.getDebugReport();

    const r = JSON.parse(raw);

    if (!r.ok) {

      out.innerHTML = '❌ ' + (r.error || 'Lỗi không xác định.');

      return;

    }

    let html = '<div style="margin-bottom:8px;font-weight:700">📋 Báo cáo hệ thống</div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Phiên bản</span><span style="font-weight:700">v' + (r.version || '?') + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Anki version</span><span style="font-weight:700">' + (r.anki_version || '?') + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Profile</span><span style="font-weight:700">' + (r.profile || '?') + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Số dư hiện tại</span><span style="font-weight:700;color:var(--green)">' + fmt(r.balance || 0) + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Config keys đang hoạt động</span><span style="font-weight:700">' + r.active_keys + '/' + r.total_expected_keys + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Cache entries</span><span style="font-weight:700">' + (r.cache_size || 0) + '</span></div>';

    const errors = r.errors || [];

    if (errors.length > 0) {

      html += '<div style="color:var(--red);margin-top:6px">⚠️ Lỗi: ' + errors.join('; ') + '</div>';

    }

    out.innerHTML = html;

    min.textContent = '🕒 Lần cuối: ' + new Date().toLocaleTimeString('vi-VN');

  } catch (e) {

    out.innerHTML = '❌ Lỗi: ' + e.message;

  } finally {

    btn.disabled = false;

  }

}



// ════════════════════════════════════════════

//  TAX

// ════════════════════════════════════════════

function renderResidenceStatus(data) {

  if (!data || !data.residence) return;

  residenceData = data;

  const res = data.residence || {};

  document.getElementById('res-emoji').textContent = res.emoji || '🏠';

  document.getElementById('res-name').textContent = res.name || 'Chưa có nơi ở';

  document.getElementById('res-desc').textContent = res.desc || '—';

  document.getElementById('res-rent').textContent = fmt(data.monthly_rent || 0);

  document.getElementById('res-food').textContent = fmt(data.monthly_food || 0);

  document.getElementById('res-internet').textContent = fmt(data.monthly_internet || 0);

  document.getElementById('res-utils').textContent = fmt(data.monthly_utilities_est || 0);

  document.getElementById('res-total-est').textContent = fmt(data.monthly_total_est || 0);

  document.getElementById('res-land-tax').textContent = fmt(data.monthly_land_tax || 0);



  const statusEl = document.getElementById('res-collection-status');

  const lastEl = document.getElementById('res-last-collected');

  const collected = !!data.collected_today;

  statusEl.textContent = collected ? 'Đã thu' : 'Chưa thu';

  statusEl.style.color = collected ? 'var(--green)' : 'var(--yellow)';

  lastEl.textContent = data.last_collected ? `Gần nhất: ${data.last_collected}` : 'Chưa có lần thu nào';



  const sellBtn = document.getElementById('res-sell-btn');

  sellBtn.style.display = res.type === 'buy' ? 'inline-flex' : 'none';



  renderResidenceLog(data.log || []);

}



function renderResidenceLog(log) {

  const el = document.getElementById('res-log-list');

  if (!log.length) {

    el.innerHTML = '<div class="empty"><div class="ei">📋</div><p>Chưa có dữ liệu</p></div>';

    return;

  }

  el.innerHTML = log.map(entry => {

    const bd = entry.breakdown || {};

    const borrowed = entry.loan || 0;

    return `

      <div class="mini-log-item">

        <span style="font-size:18px">${borrowed > 0 ? '⚠️' : '📅'}</span>

        <div style="flex:1;min-width:0">

          <div style="font-weight:700">${entry.date || '--'} · ${bd.residence_name || 'Sinh hoạt'}</div>

          <div style="color:var(--muted2);line-height:1.6">

            Điện nước ${fmt(bd.daily_utilities || 0)} · ăn ${fmt(bd.daily_food || 0)} · internet ${fmt(bd.daily_internet || 0)}

            ${bd.daily_rent ? ` · thuê ${fmt(bd.daily_rent)}` : ''}

          </div>

          <div style="color:var(--muted2);line-height:1.6">

            ${bd.cards_yesterday || 0} thẻ hôm qua · ${bd.util_mult_label || '—'}

            ${borrowed > 0 ? ` · vay bù ${fmt(borrowed)}` : ''}

          </div>

        </div>

        <span style="font-weight:800;color:var(--red)">-${fmt(entry.total || 0)}</span>

      </div>`;

  }).join('');

}



function renderLoanStatus(loan) {

  loanStatusData = loan || {};

  const hasLoan = !!loanStatusData.has_loan;

  const banner = document.getElementById('loan-banner');

  banner.style.display = hasLoan ? 'flex' : 'none';

  document.getElementById('loan-amount-banner').textContent = fmt(loanStatusData.total || 0);



  const badge = document.getElementById('loan-status-badge');

  badge.textContent = hasLoan ? 'Đang có nợ' : 'Không có nợ';

  badge.className = hasLoan ? 'badge badge-red' : 'badge badge-green';



  document.getElementById('loan-total').textContent = fmt(loanStatusData.total || 0);

  document.getElementById('loan-interest').textContent = fmt(loanStatusData.interest_accrued || 0);

  document.getElementById('loan-principal').textContent = fmt(loanStatusData.principal || 0);

  document.getElementById('loan-rate').textContent = `${(loanStatusData.monthly_rate_pct || 25).toFixed(0)}%/tháng`;

  document.getElementById('loan-meta').textContent = hasLoan

    ? `Vay từ ${loanStatusData.since || '--'} · cộng lãi gần nhất ${loanStatusData.last_interest_date || '--'}`

    : 'Thu nhập từ ôn thẻ sẽ ưu tiên trả nợ trước.';



  renderLoanLog(loanStatusData.log || []);

}



function renderLoanLog(log) {

  const el = document.getElementById('loan-log-list');

  if (!log.length) {

    el.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Chưa có biến động nợ.</div>';

    return;

  }

  const labelMap = {

    borrow: { icon: '🏦', text: 'Vay thêm', color: 'var(--red)' },

    interest: { icon: '📈', text: 'Cộng lãi', color: 'var(--yellow)' },

    repay: { icon: '💸', text: 'Trả nợ', color: 'var(--green)' },

  };

  el.innerHTML = log.slice(0, 6).map(entry => {

    const meta = labelMap[entry.event] || { icon: '📌', text: entry.event || 'Cập nhật', color: 'var(--text)' };

    return `

      <div class="mini-log-item">

        <span style="font-size:18px">${meta.icon}</span>

        <div style="flex:1;min-width:0">

          <div style="font-weight:700">${meta.text}</div>

          <div style="color:var(--muted2)">${entry.date || '--'}${entry.total ? ` · tổng nợ ${fmt(entry.total)}` : entry.remaining !== undefined ? ` · còn ${fmt(entry.remaining)}` : ''}</div>

        </div>

        <span style="font-weight:800;color:${meta.color}">${entry.event === 'repay' ? '-' : '+'}${fmt(entry.amount || 0)}</span>

      </div>`;

  }).join('');

}



async function openResidenceModal() {

  const modal = document.getElementById('modal-residence');

  selectedResidenceId = '';

  selectedResidencePreview = null;

  modal.classList.add('open');

  document.body.style.overflow = 'hidden';

  const raw = await B.getAvailableResidences();

  availableResidences = JSON.parse(raw) || [];

  renderResidenceOptions();

  const current = availableResidences.find(r => r.is_current) || availableResidences[0];

  if (current) await selectResidenceOption(current.id);

}



function closeResidenceModal() {

  document.getElementById('modal-residence').classList.remove('open');

  document.body.style.overflow = '';

  selectedResidenceId = '';

  selectedResidencePreview = null;

}



function renderResidenceOptions() {

  const el = document.getElementById('residence-options-list');

  if (!availableResidences.length) {

    el.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Không có nơi ở khả dụng.</div>';

    return;

  }

  const currentId = residenceData?.residence?.id;

  el.innerHTML = availableResidences.map(opt => {

    const unlocked = curBal >= (opt.unlock_balance || 0) || opt.id === currentId;

    const active = opt.id === selectedResidenceId;

    const monthly = opt.monthly_total || 0;

    return `

      <div class="res-option ${active ? 'active' : ''} ${!unlocked ? 'locked' : ''}" onclick="selectResidenceOption('${opt.id}')">

        <div class="res-option-title">

          <span style="font-size:22px">${opt.emoji || '🏠'}</span>

          <span>${opt.name || opt.id}</span>

          ${opt.id === currentId ? '<span class="badge badge-purple" style="font-size:10px">Hiện tại</span>' : ''}

          ${opt.type === 'buy' ? '<span class="badge badge-yellow" style="font-size:10px">Mua đứt</span>' : '<span class="badge badge-blue" style="font-size:10px">Thuê</span>'}

        </div>

        <div class="res-option-meta">

          ${opt.desc || '—'}<br/>

          Chi phí/tháng: <strong style="color:var(--text)">${fmt(monthly)}</strong>

          ${opt.type === 'buy' ? `<br/>Giá mua: <strong style="color:var(--yellow)">${fmt(opt.purchase_price || 0)}</strong>` : ''}

          <br/>Mở khi số dư đạt <strong style="color:${unlocked ? 'var(--green)' : 'var(--red)'}">${fmt(opt.unlock_balance || 0)}</strong>

        </div>

      </div>`;

  }).join('');

}



async function selectResidenceOption(id) {

  selectedResidenceId = id;

  renderResidenceOptions();

  const raw = await B.previewChangeResidence(id);

  selectedResidencePreview = JSON.parse(raw);

  if (selectedResidencePreview && selectedResidencePreview.ok === false) {

    document.getElementById('res-modal-name').textContent = 'Không xem trước được';

    document.getElementById('res-modal-desc').textContent = selectedResidencePreview.error || 'Dữ liệu không hợp lệ.';

    document.getElementById('res-modal-status').textContent = selectedResidencePreview.error || 'Dữ liệu không hợp lệ.';

    document.getElementById('res-modal-status').style.color = 'var(--red)';

    document.getElementById('res-modal-confirm-btn').disabled = true;

    return;

  }

  const info = selectedResidencePreview.info || availableResidences.find(r => r.id === id) || {};

  const currentId = residenceData?.residence?.id;

  const unlocked = curBal >= (info.unlock_balance || 0) || id === currentId;

  const canAfford = info.type !== 'buy' || !!selectedResidencePreview.can_afford;

  const isCurrent = id === currentId;

  const monthly = (info.monthly_rent || 0) + (info.food_monthly || 0) + (info.internet_monthly || 0) + (info.utilities_base || 0) + (selectedResidencePreview.monthly_land_tax || 0);



  document.getElementById('res-modal-emoji').textContent = info.emoji || '🏠';

  document.getElementById('res-modal-name').textContent = info.name || id;

  document.getElementById('res-modal-type').textContent = info.type === 'buy' ? 'Nhà mua đứt' : 'Nhà thuê';

  document.getElementById('res-modal-desc').textContent = info.desc || '—';

  document.getElementById('res-modal-upfront').textContent = fmt(info.type === 'buy' ? (info.purchase_price || 0) : 0);

  document.getElementById('res-modal-monthly').textContent = fmt(monthly);

  document.getElementById('res-modal-utils').textContent = fmt(info.utilities_base || 0);

  document.getElementById('res-modal-land-tax').textContent = fmt(selectedResidencePreview.monthly_land_tax || 0);



  const statusEl = document.getElementById('res-modal-status');

  const confirmBtn = document.getElementById('res-modal-confirm-btn');

  if (isCurrent) {

    statusEl.textContent = 'Đây là nơi ở hiện tại của bạn.';

    statusEl.style.color = 'var(--muted2)';

  } else if (!unlocked) {

    statusEl.textContent = `Chưa mở khoá. Cần tối thiểu ${fmt(info.unlock_balance || 0)} số dư hiện tại.`;

    statusEl.style.color = 'var(--red)';

  } else if (!canAfford) {

    statusEl.textContent = `Không đủ tiền mua. Số dư hiện tại: ${fmt(curBal)}.`;

    statusEl.style.color = 'var(--red)';

  } else {

    statusEl.textContent = info.type === 'buy'

      ? `Bạn sẽ trả ngay ${fmt(info.purchase_price || 0)} để chuyển sang nhà mua đứt.`

      : `Có thể chuyển ngay. Chi phí hàng tháng dự kiến là ${fmt(monthly)}.`;

    statusEl.style.color = 'var(--green)';

  }

  confirmBtn.disabled = isCurrent || !unlocked || !canAfford;

  confirmBtn.textContent = info.type === 'buy' ? 'Xác nhận mua' : 'Xác nhận chuyển';

}



async function confirmResidenceChange() {

  if (!selectedResidenceId) return;

  const res = JSON.parse(await B.changeResidence(selectedResidenceId));

  if (!res.ok) {

    toast('err', '❌ ' + (res.error || 'Không thể đổi nơi ở'));

    return;

  }

  closeResidenceModal();

  availableResidences = [];

  selectedResidencePreview = null;

  toast('ok', res.cost > 0 ? `🏠 Đã mua nơi ở mới với giá ${fmt(res.cost)}.` : '🏠 Đã chuyển nơi ở.');

  await loadFinance();

  loadDashboard().catch(() => {});

}



async function sellCurrentResidence() {

  if (!residenceData?.residence || residenceData.residence.type !== 'buy') return;

  if (!confirm(`Bán "${residenceData.residence.name}" và quay về nhà cơ bản?`)) return;

  const res = JSON.parse(await B.sellResidence());

  if (!res.ok) {

    toast('err', '❌ ' + (res.error || 'Không thể bán nhà'));

    return;

  }

  toast('ok', `💰 Đã bán nhà và nhận ${fmt(res.received || 0)}.`);

  await loadFinance();

  loadDashboard().catch(() => {});

}



function renderFullTaxStatus(full) {

  if (!full) return;

  taxFullData = full;

  const pit = full.pit_preview || {};



  document.getElementById('tax-pit-income').textContent     = fmt(pit.monthly_income || 0);

  document.getElementById('tax-pit-deduction').textContent  = fmt(pit.total_deduction || 0);

  document.getElementById('tax-pit-taxable').textContent    = fmt(pit.taxable_income || 0);

  document.getElementById('tax-pit-amount').textContent     = fmt(pit.tax || 0);

  document.getElementById('tax-pit-withheld').textContent   = fmt(pit.already_withheld || 0);

  document.getElementById('tax-pit-remaining').textContent  = fmt(pit.remaining_to_settle || 0);



  const insAmt = Math.round((pit.monthly_income || 0) * 0.105);

  document.getElementById('tax-pit-effective').textContent =

    `Hiệu suất: ${(pit.rate_eff_pct || 0).toFixed(2)}% · BH: ${fmt(insAmt)} · Thẻ: ${pit.cards_this_month || 0}`;



  const pitBadge = document.getElementById('tax-pit-badge');

  if ((pit.tax || 0) > 0) {

    pitBadge.textContent = `~${(pit.rate_eff_pct || 0).toFixed(2)}%`;

    pitBadge.className = 'badge badge-yellow';

  } else {

    pitBadge.textContent = 'Miễn thuế';

    pitBadge.className = 'badge badge-green';

  }



  // Cập nhật nguồn tham khảo từ backend nếu có

  const guide = full.tax_guide || {};

  if (guide.source_ref) {

    const refEl = document.getElementById('pit-source-ref');

    if (refEl) refEl.textContent = guide.source_ref;

  }



  const land = full.land_tax_residence || 0;

  document.getElementById('tax-land-current').textContent = fmt(land);

  document.getElementById('tax-land-note').textContent = land > 0

    ? 'Thuế đất nhà ở mua đứt sẽ bị trừ theo kỳ monthly reset.'

    : 'Không có nhà mua đứt.';



  const loan = full.loan || loanStatusData || {};

  document.getElementById('tax-loan-total').textContent = fmt(loan.total || 0);

  document.getElementById('tax-loan-note').textContent = loan.has_loan

    ? `Gốc ${fmt(loan.principal || 0)} · lãi cộng dồn ${fmt(loan.interest_accrued || 0)}.`

    : 'Không có khoản vay nóng.';



  renderPitLog(full.pit_log || []);

  renderLandTaxLog(full.land_log || []);

}



function renderPitLog(log) {

  const el = document.getElementById('tax-pit-log-list');

  if (!log.length) {

    el.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Chưa có lịch sử PIT.</div>';

    return;

  }

  el.innerHTML = log.map(entry => {

    const withheld  = entry.withheld || 0;

    const adj       = entry.adjustment || 0;

    const totalTax  = entry.tax || 0;

    const isExempt  = totalTax <= 0 && withheld <= 0;

    let detail = `Thu nhập ${fmt(entry.monthly_income || 0)} · giảm trừ ${fmt(entry.total_deduction || 0)}`;

    if (withheld > 0) detail += ` · đã khấu trừ ${fmt(withheld)}`;

    if (adj > 0)  detail += ` · nộp thêm ${fmt(adj)}`;

    if (adj < 0)  detail += ` · hoàn ${fmt(Math.abs(adj))}`;

    return `

    <div class="mini-log-item">

      <span style="font-size:18px">${isExempt ? '✅' : (adj < 0 ? '💚' : '🧾')}</span>

      <div style="flex:1;min-width:0">

        <div style="font-weight:700">${entry.date || '--'}</div>

        <div style="color:var(--muted2);font-size:11px">${detail}</div>

      </div>

      <span style="font-weight:800;color:${isExempt ? 'var(--green)' : (adj < 0 ? 'var(--green)' : 'var(--red)')}">${isExempt ? 'Miễn' : (adj < 0 ? '+' + fmt(Math.abs(adj)) : '-' + fmt(totalTax))}</span>

    </div>`;

  }).join('');

}



function renderLandTaxLog(log) {

  const el = document.getElementById('tax-land-log-list');

  if (!log.length) {

    el.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Chưa có lịch sử thuế đất.</div>';

    return;

  }

  el.innerHTML = log.map(entry => `

    <div class="mini-log-item">

      <span style="font-size:18px">🏡</span>

      <div style="flex:1;min-width:0">

        <div style="font-weight:700">${entry.date || '--'}</div>

        <div style="color:var(--muted2)">${(entry.breakdown || []).length} tài sản · ${(entry.breakdown || []).map(x => x.name).join(', ') || '—'}</div>

      </div>

      <span style="font-weight:800;color:var(--red)">-${fmt(entry.total || 0)}</span>

    </div>

  `).join('');

}



document.getElementById('modal-residence')?.addEventListener('click', e => {

  if (e.target === e.currentTarget) closeResidenceModal();

});



function renderTaxStatus(t) {

  t = t || {};

  const badge    = document.getElementById('tax-status-badge');

  const totalEl  = document.getElementById('tax-total-assets');

  const todayEl  = document.getElementById('tax-today-amount');

  const rateEl   = document.getElementById('tax-rate');

  const nextEl   = document.getElementById('tax-next');



  if (!t.taxable) {

    badge.textContent  = '✅ Miễn thuế';

    badge.className    = 'badge badge-green';

    totalEl.textContent = fmt(t.total_assets || 0);

    todayEl.textContent = '0 VND';

    rateEl.textContent  = 'Miễn (TTS < 10M)';

    nextEl.textContent  = '0 VND';

  } else {

    const collected = t.collected_today;

    badge.textContent   = collected ? '✅ Đã thu hôm nay' : '⏳ Sẽ thu ngày mai';

    badge.className     = collected ? 'badge badge-green' : 'badge badge-yellow';

    totalEl.textContent = fmt(t.total_assets || 0);

    todayEl.textContent = fmt(t.tax_today || 0);

    rateEl.textContent  = (t.rate_pct || 0).toFixed(1) + '%/ngày';

    nextEl.textContent  = fmt(t.next_tax || 0);

  }



  // Highlight bracket đang áp dụng

  const inc = t.monthly_income || 0;

  const brackets = [

    {id:'tb-0', min:0,          max:1_000_000},

    {id:'tb-1', min:1_000_000,  max:5_000_000},

    {id:'tb-2', min:5_000_000,  max:20_000_000},

    {id:'tb-3', min:20_000_000, max:100_000_000},

    {id:'tb-4', min:100_000_000, max:Infinity},

  ];

  brackets.forEach(b => {

    const el = document.getElementById(b.id);

    if (!el) return;

    const active = t.taxable && inc > b.min && (b.max === Infinity || inc <= b.max);

    el.classList.toggle('tax-active-row', active);

    el.style.color = active ? 'var(--yellow)' : '';

  });

}



// ════════════════════════════════════════════

//  LEARNING PAGE (Quiz + Emergency Log)

// ════════════════════════════════════════════

// ── QUIZ STATE ──

let quizData = null;        // { quiz_set, set_size }

let quizCurrentQ = 0;       // 0-based index

let quizAnswered = {};      // { q_index: selected }

let quizResults = {};       // { q_index: {correct,bonus_awarded,explanation,correct_answer} }

let quizSubmitted = false;  // flag to prevent double submit

let quizLoading = false;

let quizTopics = null;       // { slug: display_name }

let selectedTopic = '';      // current topic filter



// ── Cached quiz stats (tránh gọi bridge lại mỗi lần vào tab) ──

let _cachedQuizStats = null;



// ── Cached DOM refs cho quiz rendering ──

let _quizDom = null;

function _getQuizDom() {

  if (!_quizDom) {

    _quizDom = {

      area:      document.getElementById('quiz-area'),

      empty:     document.getElementById('quiz-empty'),

      progress:  document.getElementById('quiz-progress'),

      qText:     document.getElementById('quiz-q-text'),

      options:   document.getElementById('quiz-options'),

      result:    document.getElementById('quiz-result'),

      qCounter:  document.getElementById('quiz-q-counter'),

      prevBtn:   document.getElementById('quiz-prev-btn'),

      nextBtn:   document.getElementById('quiz-next-btn'),

      finishBtn: document.getElementById('quiz-finish-btn'),

      newBtn:    document.getElementById('quiz-new-btn'),

    };

  }

  return _quizDom;

}



// ── Cache DOM refs cho quiz stats ──

let _quizStatsDom = null;

function _getQuizStatsDom() {

  if (!_quizStatsDom) {

    _quizStatsDom = {

      accuracy: document.getElementById('quiz-accuracy'),

      correct:  document.getElementById('quiz-correct'),

      total:    document.getElementById('quiz-total'),

      streak:   document.getElementById('quiz-streak'),

      best:     document.getElementById('quiz-best'),

    };

  }

  return _quizStatsDom;

}



function _updateQuizStatsUI(s) {

  const d = _getQuizStatsDom();

  d.accuracy.textContent = s.accuracy + '%';

  d.correct.textContent  = s.correct;

  d.total.textContent    = s.total;

  d.streak.textContent   = s.streak;

  d.best.textContent     = s.best_streak;

}



// ════════════════════════════════════════════

async function loadLearning() {

  await refreshBalance();



  // ── Quiz Stats (dùng cache nếu có) ─────────

  if (_cachedQuizStats) {

    _updateQuizStatsUI(_cachedQuizStats);

  } else {

    const statsRaw = await B.getQuizStats();

    _cachedQuizStats = JSON.parse(statsRaw);

    _updateQuizStatsUI(_cachedQuizStats);

  }



  // ── Daily limit ──────────────────────────

  await refreshDailyQuizLimit();



  // ── Load quiz topics ─────────────────────

  await loadQuizTopics();



  // ── Load current quiz set ─────────────────

  await loadQuizSet();



  // ── Emergency Log ─────────────────────────

  await loadEmergencyLog();

}



// ── Cập nhật hiển thị giới hạn câu hỏi mỗi ngày ──

async function refreshDailyQuizLimit() {

  try {

    const raw = await B.getQuizDailyInfo();

    const info = JSON.parse(raw);

    const badge = document.getElementById('quiz-daily-limit-badge');

    if (badge) {

      const rem = info.remaining;

      const limit = info.limit;

      if (rem <= 0) {

        badge.className = 'badge badge-red';

        badge.textContent = `📅 Hết lượt hôm nay (${info.correct_today}/${limit})`;

      } else {

        badge.className = 'badge badge-green';

        badge.textContent = `📅 Hôm nay: ${info.correct_today}/${limit}  •  Còn ${rem} lượt`;

      }

    }

  } catch (e) {

    console.error('refreshDailyQuizLimit error', e);

  }

}



// ── Load quiz topics into dropdown ─────────────────────────────────

async function loadQuizTopics() {

  try {

    const raw = await B.getQuizTopics();

    quizTopics = JSON.parse(raw);

    const sel = document.getElementById('quiz-topic-select');

    if (!sel) return;

    sel.innerHTML = '<option value="">📚 Tất cả chủ đề</option>';

    for (const [slug, display] of Object.entries(quizTopics)) {

      const opt = document.createElement('option');

      opt.value = slug;

      opt.textContent = display;

      sel.appendChild(opt);

    }

    // Khôi phục lựa chọn trước đó (nếu có)

    if (selectedTopic) sel.value = selectedTopic;

  } catch (e) {

    console.error('loadQuizTopics error', e);

  }

}



// ── Quiz Functions ────────────────────────────────────────────────



async function loadQuizSet() {

  try {

    const raw = await B.getQuizSet();

    const data = JSON.parse(raw);

    quizData = data;

    quizCurrentQ = 0;

    quizAnswered = {};

    quizResults = {};

    quizSubmitted = false;

    renderQuiz();

  } catch (e) {

    console.error('loadQuizSet error', e);

    const dom = _getQuizDom();

    dom.area.style.display = 'none';

    dom.empty.style.display = '';

  }

}



async function startNewQuiz() {

  if (quizLoading) return;

  quizLoading = true;

  const dom = _getQuizDom();

  dom.newBtn.textContent = '⏳ Đang tạo...';

  try {

    let raw;

    if (selectedTopic) {

      raw = await B.newQuizSetByTopic(selectedTopic);

    } else {

      raw = await B.newQuizSet();

    }

    const data = JSON.parse(raw);

    quizData = data;

    quizCurrentQ = 0;

    quizAnswered = {};

    quizResults = {};

    quizSubmitted = false;

    renderQuiz();

    // Cập nhật lại thống kê — xoá cache để lấy mới

    const sr = JSON.parse(await B.getQuizStats());

    _cachedQuizStats = sr;

    _updateQuizStatsUI(sr);

    // Cập nhật daily limit

    await refreshDailyQuizLimit();

  } catch (e) {

    console.error('startNewQuiz error', e);

  }

  dom.newBtn.textContent = '🔄 Bộ câu mới';

  quizLoading = false;

}



async function onTopicChange() {

  const sel = document.getElementById('quiz-topic-select');

  selectedTopic = sel ? sel.value : '';

  await startNewQuiz();

}



function renderQuiz() {

  const dom = _getQuizDom();



  if (!quizData || !quizData.quiz_set || quizData.quiz_set.length === 0) {

    dom.area.style.display = 'none';

    dom.empty.style.display = '';

    return;

  }



  dom.area.style.display = '';

  dom.empty.style.display = 'none';

  dom.result.style.display = 'none';



  const set = quizData.quiz_set;

  const total = set.length;

  const idx = quizCurrentQ;



  // Progress dots

  dom.progress.innerHTML = set.map((_, i) => {

    let cls = 'quiz-progress-dot';

    if (i === idx) cls += ' current';

    if (quizResults[i] !== undefined) cls += quizResults[i].correct ? ' answered' : ' wrong-answered';

    return `<div class="${cls}" title="Câu ${i+1}"></div>`;

  }).join('');



  // Counter

  dom.qCounter.textContent = `Câu ${idx+1}/${total}`;



  // Question

  const q = set[idx];

  dom.qText.textContent = q.q;



  // Options

  const letter = ['A','B','C','D','E','F'];

  const answered = quizAnswered[idx];

  const resultData = quizResults[idx];



  dom.options.innerHTML = q.options.map((opt, oi) => {

    let cls = 'quiz-option';

    if (resultData !== undefined) {

      cls += ' disabled';

      if (oi === q.correct) cls += ' correct';

      if (answered === oi && oi !== q.correct) cls += ' wrong';

      if (answered === oi) cls += ' selected';

    } else if (answered === oi) {

      cls += ' selected';

    }

    return `<div class="${cls}" data-oi="${oi}" onclick="${resultData !== undefined ? '' : `selectQuizOption(${oi})`}">

      <div class="q-radio">${resultData !== undefined ? (oi === q.correct ? '✓' : (answered === oi ? '✗' : letter[oi] || oi+1)) : (letter[oi] || oi+1)}</div>

      <div class="q-opt-label">${opt}</div>

    </div>`;

  }).join('');



  // Result panel

  if (resultData !== undefined) {

    const isCorrect = resultData.correct;

    dom.result.style.display = '';

    dom.result.style.background = isCorrect ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)';

    dom.result.style.border = isCorrect ? '1px solid rgba(16,185,129,.3)' : '1px solid rgba(239,68,68,.3)';

    dom.result.style.color = isCorrect ? 'var(--green)' : 'var(--red)';

    const icon = isCorrect ? '✅' : '❌';

    const bonusText = resultData.bonus_awarded ? `<br><span style="color:var(--yellow)">🎉 +25.000đ đã được thêm vào ví!</span>` : '';

    const correctAnswer = resultData.correct_answer || 'Không xác định';

    dom.result.innerHTML = `<strong>${icon} ${isCorrect ? 'Chính xác!' : 'Sai rồi!'}</strong><br>

      <span style="color:var(--muted2)">Đáp án đúng: <strong style="color:var(--text)">${correctAnswer}</strong></span><br>

      <span style="color:var(--muted);font-size:12px">💡 ${resultData.explanation || ''}</span>${bonusText}`;

  } else {

    dom.result.style.display = 'none';

  }



  // Navigation

  dom.prevBtn.style.display = idx > 0 ? '' : 'none';

  dom.nextBtn.style.display = (idx < total - 1) ? '' : 'none';

  dom.finishBtn.style.display = (idx === total - 1 && resultData !== undefined) ? '' : 'none';



  // Update stats hint

  const allDone = set.every((_, i) => quizResults[i] !== undefined);

  if (allDone) {

    const correctCount = set.filter((_, i) => quizResults[i] && quizResults[i].correct).length;

    dom.finishBtn.textContent = `✅ Hoàn thành (${correctCount}/${total} đúng)`;

    dom.finishBtn.style.display = '';

    dom.nextBtn.style.display = 'none';

  }

}



function selectQuizOption(oi) {

  const idx = quizCurrentQ;

  if (!quizData || !quizData.quiz_set) return;

  if (quizResults[idx] !== undefined) return; // already answered

  if (quizSubmitted) return;



  quizAnswered[idx] = oi;

  quizSubmitted = true;



  // Gửi lên Python backend

  B.submitQuizAnswer(idx, oi).then(raw => {

    let res;

    try {

      res = JSON.parse(raw);

    } catch(e) {

      console.error('submitQuizAnswer parse error', e);

      res = {};

    }



    // Kiểm tra lỗi từ backend

    if (res.error) {

      console.error('submitQuizAnswer backend error', res.error);

      toast('error', `❌ Lỗi: ${res.error}`, 3000);

      quizSubmitted = false;

      return;

    }



    quizResults[idx] = res;

    renderQuiz();



    // Update stats display & cache

    const sr = res.stats || { accuracy: 0, correct: 0, total: 0, streak: 0, best_streak: 0 };

    _cachedQuizStats = sr;

    _updateQuizStatsUI(sr);



    // 🔥 Refresh balance + toast nếu được thưởng

    if (res.bonus_awarded) {

      toast('ok', '🎓 Trả lời đúng! +25.000đ đã được cộng vào ví.', 3000);

    }

    refreshBalance();

    refreshDailyQuizLimit();



    quizSubmitted = false;

  }).catch(e => {

    console.error('submitQuizAnswer error', e);

    toast('error', '❌ Không thể ghi nhận câu trả lời. Vui lòng thử lại.', 3000);

    quizSubmitted = false;

  });

}



function nextQuizQuestion() {

  if (!quizData || !quizData.quiz_set) return;

  if (quizCurrentQ < quizData.quiz_set.length - 1) {

    quizCurrentQ++;

    renderQuiz();

  }

}



function prevQuizQuestion() {

  if (quizCurrentQ > 0) {

    quizCurrentQ--;

    renderQuiz();

  }

}



function finishQuiz() {

  renderQuizReview();

}



// ── Review Mode ─────────────────────────────────────────────────────

function renderQuizReview() {

  const dom = _getQuizDom();

  const set = quizData?.quiz_set;

  if (!set || set.length === 0) return;



  const total = set.length;

  let correctCount = 0;

  for (let i = 0; i < total; i++) {

    if (quizResults[i] && quizResults[i].correct) correctCount++;

  }

  const wrongCount = total - correctCount;

  const accuracyPct = total > 0 ? Math.round(correctCount / total * 100) : 0;



  // Ẩn các element quiz thường

  dom.qText.style.display = 'none';

  dom.options.style.display = 'none';

  dom.result.style.display = 'none';

  dom.prevBtn.style.display = 'none';

  dom.nextBtn.style.display = 'none';

  dom.finishBtn.style.display = 'none';



  const letter = ['A','B','C','D','E','F'];



  // Summary header

  let html = `

    <div style="text-align:center;padding:16px 0;margin-bottom:16px">

      <div style="font-size:32px;margin-bottom:6px">${accuracyPct >= 80 ? '🎉' : accuracyPct >= 50 ? '💪' : '📚'}</div>

      <div style="font-size:18px;font-weight:800">Kết quả: ${correctCount}/${total} đúng</div>

      <div style="font-size:13px;color:var(--muted2);margin-top:4px">Độ chính xác: ${accuracyPct}%</div>

      <div style="display:flex;gap:16px;justify-content:center;margin-top:10px;font-size:13px">

        <span style="color:var(--green)">✅ Đúng: ${correctCount}</span>

        <span style="color:var(--red)">❌ Sai: ${wrongCount}</span>

      </div>

    </div>

    <div style="max-height:420px;overflow-y:auto;display:flex;flex-direction:column;gap:8px;margin-bottom:16px;padding-right:4px">`;



  for (let i = 0; i < total; i++) {

    const q = set[i];

    const res = quizResults[i];

    const isCorrect = res && res.correct;

    const correctLetter = letter[q.correct] || (q.correct + 1);

    const answeredIdx = quizAnswered[i];

    const answeredLetter = answeredIdx !== undefined ? (letter[answeredIdx] || (answeredIdx + 1)) : '—';



    html += `

      <div style="background:${isCorrect ? 'rgba(16,185,129,.07)' : 'rgba(239,68,68,.07)'};border-radius:8px;padding:10px 12px;border-left:3px solid ${isCorrect ? 'var(--green)' : 'var(--red)'}">

        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">

          <div style="font-size:13px;font-weight:600;flex:1;line-height:1.5">Câu ${i+1}: ${q.q}</div>

          <span style="font-size:16px;white-space:nowrap">${isCorrect ? '✅' : '❌'}</span>

        </div>

        <div style="display:flex;gap:12px;margin-top:6px;font-size:12px;flex-wrap:wrap">

          <span style="color:var(--muted2)">Bạn chọn: <strong style="color:${isCorrect ? 'var(--green)' : 'var(--red)'}">${answeredLetter}</strong></span>

          ${!isCorrect ? `<span style="color:var(--muted2)">Đáp án: <strong style="color:var(--green)">${correctLetter}</strong></span>` : ''}

          <span style="color:var(--muted);font-size:11px;flex-basis:100%;margin-top:2px">💡 ${(q.explanation || '').substring(0, 100)}${(q.explanation || '').length > 100 ? '...' : ''}</span>

        </div>

      </div>`;

  }



  html += `</div>

    <div style="display:flex;gap:8px;justify-content:center">

      <button class="btn btn-secondary" onclick="exitReviewMode();startNewQuiz()" style="font-size:12px;padding:6px 16px">🔄 Làm lại</button>

      <button class="btn" onclick="exitReviewMode()" style="font-size:12px;padding:6px 16px">📚 Về danh sách</button>

    </div>`;



  // Inject hoặc tạo review container

  let reviewDiv = document.getElementById('quiz-review-area');

  if (!reviewDiv) {

    reviewDiv = document.createElement('div');

    reviewDiv.id = 'quiz-review-area';

    dom.area.appendChild(reviewDiv);

  }

  reviewDiv.innerHTML = html;

  reviewDiv.style.display = '';

}



function exitReviewMode() {

  const dom = _getQuizDom();

  const reviewDiv = document.getElementById('quiz-review-area');

  if (reviewDiv) reviewDiv.style.display = 'none';

  // Khôi phục trạng thái quiz ban đầu

  dom.qText.style.display = '';

  dom.options.style.display = '';

  quizCurrentQ = 0;

  renderQuiz();

  document.getElementById('page-learning').scrollIntoView({ behavior: 'smooth', block: 'start' });

}



// ── Emergency Log ──────────────────────────────────────────────────



async function loadEmergencyLog() {

  const logRaw = await B.getEmergencyLog();

  const log = JSON.parse(logRaw);



  document.getElementById('emg-count-badge').textContent = log.length + ' sự kiện';



  // Insurance status from inventory

  const invRaw = JSON.parse(await B.getInventory());

  const invIds = new Set((invRaw || []).map(i => i.id || ''));

  const insMap = [

    { id: 'ins_health',   label: 'Bảo hiểm SK',   emoji: '🏥' },

    { id: 'ins_car',      label: 'Bảo hiểm xe',   emoji: '🚗' },

    { id: 'ins_property', label: 'Bảo hiểm BĐS',  emoji: '🏠' },

    { id: 'ins_life',     label: 'Bảo hiểm NT',    emoji: '💙' },

  ];

  const insRow = document.getElementById('emg-insurance-row');

  insRow.innerHTML = insMap.map(ins => {

    const owned = invIds.has(ins.id);

    return `<span class="badge ${owned ? 'badge-green' : 'badge-red'}" title="${owned ? 'Đã mua' : 'Chưa mua'}">

      ${ins.emoji} ${ins.label} ${owned ? '✅' : '✕'}

    </span>`;

  }).join('');



  const listEl = document.getElementById('emg-log-list');

  const emptyEl = document.getElementById('emg-empty');



  if (log.length === 0) {

    listEl.innerHTML = '';

    emptyEl.style.display = '';

    return;

  }

  emptyEl.style.display = 'none';



  const EMOJI = {

    car: '🚗', health: '🏥', property: '🏠', residence: '🏡', income: '💼',

  };



  listEl.innerHTML = log.map(e => {

    const paid = Number(e.paid || e.base_cost || 0);

    const base = Number(e.base_cost || paid);

    const insured = e.insured;

    const saving = base - paid;

    const cat = (e.event_id || '').split('_')[0];

    const emoji = EMOJI[cat] || '⚠️';

    return `

      <div style="display:flex;align-items:flex-start;gap:10px;padding:10px 12px;

                  background:var(--surface2);border-radius:9px;border:1px solid ${insured ? 'rgba(16,185,129,.2)' : 'rgba(239,68,68,.15)'}">

        <div style="font-size:22px;flex-shrink:0">${emoji}</div>

        <div style="flex:1;min-width:0">

          <div style="font-size:13px;font-weight:700">${e.title || 'Sự kiện'}</div>

          <div style="font-size:11px;color:var(--muted2);margin-top:1px">${e.date || ''}</div>

          ${insured && saving > 0 ? `<div style="font-size:11px;color:var(--green);margin-top:2px">🛡️ Bảo hiểm tiết kiệm ${fmt(saving)}</div>` : ''}

        </div>

        <div style="text-align:right;flex-shrink:0">

          <div style="font-size:14px;font-weight:900;color:var(--red)">-${fmt(paid)}</div>

          ${insured ? `<div style="font-size:10px;color:var(--muted2)">gốc ${fmt(base)}</div>` : ''}

        </div>

      </div>`;

  }).join('');

}



async function loadSettings() {

  await refreshBalance();

  updateResetButtonState();

  // Reset log

  const logRaw = await B.getResetLog();

  const log = JSON.parse(logRaw);

  const el = document.getElementById('reset-log-list');

  if (!log.length) {

    el.innerHTML = '<div style="font-size:13px;color:var(--muted2)">Chưa có lần reset nào.</div>';

  } else {

    el.innerHTML = log.map(r => `

      <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);font-size:12px">

        <span style="color:var(--muted2)">${r.date}</span>

        <span style="flex:1;color:var(--muted2)">Số dư trước: <strong style="color:var(--text)">${fmt(r.snapshot?.balance||0)}</strong></span>

        <span style="color:var(--blue)">TTS: ${fmt(r.snapshot?.net_worth||0)}</span>

      </div>`).join('');

  }

  // Tax log

  await loadTaxLog();

}



async function loadTaxLog() {

  const raw  = await B.getTaxLog();

  const log  = JSON.parse(raw);

  const el   = document.getElementById('tax-log-list');

  if (!log || !log.length) {

    el.innerHTML = '<div style="font-size:13px;color:var(--muted2)">Chưa có lịch sử thuế.</div>';

    return;

  }

  el.innerHTML = log.map(r => {

    const collected = r.collected;

    const color = collected ? 'var(--red)' : 'var(--green)';

    const icon  = collected ? '🏛️' : '✅';

    return `

    <div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--border);font-size:12px">

      <span>${icon}</span>

      <span style="color:var(--muted2);width:80px;flex-shrink:0">${r.date}</span>

      <span style="flex:1;color:var(--muted2)">

        TTS: <strong style="color:var(--text)">${fmt(r.total||0)}</strong>

        ${collected ? `| ${r.rate_pct?.toFixed(1)||'?'}%/ngày` : '| Miễn thuế'}

      </span>

      <span style="font-weight:800;color:${color}">${collected ? '-'+fmt(r.tax||0) : 'Miễn'}</span>

    </div>`;

  }).join('');

}



// ════════════════════════════════════════════

//  ACHIEVEMENT

// ════════════════════════════════════════════



let achAllData = [];        // full list từ Python

let achFilter = 'all';      // category filter hiện tại

let achCategoryIcons = {};



async function loadAchievements() {

  await refreshBalance();

  try {

    const raw = await B.getAllAchievements();

    const data = JSON.parse(raw);

    if (data.error) { achAllData = []; console.warn('Achievement error:', data.error); return; }

    achAllData = Array.isArray(data) ? data : [];

    renderAchievements();

  } catch (e) {

    console.warn('loadAchievements error:', e);

    achAllData = [];

  }

}



function renderAchievements() {

  const grid = document.getElementById('ach-grid');

  if (!grid) return;



  const list = achAllData;

  const unlocked = list.filter(a => a.unlocked);

  const total = list.length;

  const pct = total > 0 ? Math.round(unlocked.length / total * 100) : 0;



  // Stats

  document.getElementById('ach-unlocked').textContent = unlocked.length;

  document.getElementById('ach-progress-pct').textContent = pct + '%';

  document.getElementById('ach-progress-label').textContent = unlocked.length + ' / ' + total;

  document.getElementById('ach-progress-bar').style.width = pct + '%';



  // Build category filter tabs

  const cats = {};

  list.forEach(a => {

    const cat = a.category || 'Khác';

    if (!cats[cat]) cats[cat] = 0;

    cats[cat]++;

  });

  const filterContainer = document.getElementById('ach-filter-tabs');

  let filterHtml = '<button class="btn btn-sm" data-cat="all" onclick="filterAchievements(\'all\')" style="' +

    (achFilter === 'all' ? 'background:var(--gold);color:#000' : 'background:var(--surface2);color:var(--text)') +

    '">📋 Tất cả (' + total + ')</button>';

  Object.keys(cats).sort().forEach(cat => {

    const isActive = achFilter === cat;

    const emoji = achCategoryIcons[cat] || '🏷️';

    filterHtml += '<button class="btn btn-sm" data-cat="' + cat + '" onclick="filterAchievements(\'' + cat + '\')" style="' +

      (isActive ? 'background:var(--gold);color:#000' : 'background:var(--surface2);color:var(--text)') +

      '">' + emoji + ' ' + cat + ' (' + cats[cat] + ')</button>';

  });

  filterContainer.innerHTML = filterHtml;



  // Filter + render grid

  const filtered = achFilter === 'all' ? list : list.filter(a => (a.category || 'Khác') === achFilter);



  grid.innerHTML = filtered.map(a => {

    const isUnlocked = a.unlocked;

    const canClaim = a.unlocked && !a.claimed;

    const claimed = a.claimed;

    const rewardDesc = buildRewardDesc(a);



    // Card style: unlocked vs locked

    const cardBorder = isUnlocked

      ? 'border-color:rgba(250,204,21,.4);background:rgba(250,204,21,.04)'

      : 'border-color:var(--border)';

    const emojiOpacity = isUnlocked ? '1' : '.35';

    const titleColor = isUnlocked ? 'var(--text)' : 'var(--muted2)';



    // Progress

    let progressHtml = '';

    if (a.progress !== undefined && a.target !== undefined && a.target > 0) {

      const p = Math.min(a.progress / a.target * 100, 100);

      progressHtml = `

        <div style="margin-top:8px">

          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted2);margin-bottom:3px">

            <span>${fmtProgress(a.progress, a.target, a.trigger_type||'')}</span>

            <span>${Math.round(p)}%</span>

          </div>

          <div style="height:5px;background:var(--surface2);border-radius:4px;overflow:hidden">

            <div style="height:100%;width:${p}%;background:${isUnlocked ? 'var(--gold)' : 'var(--blue)'};border-radius:4px;transition:width .4s"></div>

          </div>

        </div>`;

    }



    // Action button

    let actionBtn = '';

    if (canClaim) {

      actionBtn = '<button class="btn btn-sm" onclick="claimAchievement(\'' + a.id + '\')" style="margin-top:8px;background:var(--gold);color:#000;font-weight:700">🎁 Nhận thưởng</button>';

    } else if (claimed) {

      actionBtn = '<div style="margin-top:8px;font-size:11px;color:var(--green);font-weight:700">✅ Đã nhận thưởng</div>';

    }



    // Hidden badge

    const hiddenBadge = a.hidden && !isUnlocked

      ? '<span style="font-size:10px;background:var(--surface2);padding:2px 6px;border-radius:4px;color:var(--muted2)">🔒 Ẩn</span>'

      : '';



    return `

      <div class="card" style="padding:14px;${cardBorder}">

        <div style="display:flex;align-items:flex-start;gap:10px">

          <div style="font-size:28px;opacity:${emojiOpacity}">${a.emoji||'🏆'}</div>

          <div style="flex:1;min-width:0">

            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">

              <span style="font-weight:700;font-size:14px;color:${titleColor}">${isUnlocked || !a.hidden ? a.title : '???'}</span>

              ${hiddenBadge}

            </div>

            <div style="font-size:12px;color:var(--muted2);margin-top:3px">${isUnlocked || !a.hidden ? a.desc : 'Hoàn thành để khám phá!'}</div>

            ${rewardDesc}

            ${progressHtml}

            ${actionBtn}

          </div>

        </div>

      </div>`;

  }).join('') || '<div class="empty" style="grid-column:1/-1"><div class="ei">🏆</div>Không có thành tựu nào.</div>';

}



function filterAchievements(cat) {

  achFilter = cat;

  renderAchievements();

}



function buildRewardDesc(a) {

  const parts = [];

  if (a.reward?.money) parts.push('💰 ' + fmt(a.reward.money));

  if (a.reward?.xp) parts.push('⭐ ' + a.reward.xp + ' XP');

  if (a.effect) {

    const e = a.effect;

    if (e.interest_bonus) parts.push('🏦 Lãi +' + (e.interest_bonus * 100).toFixed(1) + '%');

    if (e.max_energy) parts.push('⚡ NL tối đa +' + e.max_energy);

    if (e.income_bonus) parts.push('📈 Thu nhập +' + (e.income_bonus * 100).toFixed(1) + '%');

    if (e.discount) parts.push('🔖 Giảm ' + (e.discount * 100).toFixed(1) + '%');

  }

  if (!parts.length) return '';

  return '<div style="font-size:11px;color:var(--muted2);margin-top:4px">' + parts.join(' · ') + '</div>';

}



function fmtProgress(progress, target, triggerType) {

  if (triggerType === 'card_reviewed') return '📝 ' + progress + ' / ' + target + ' thẻ';

  if (triggerType === 'streak_updated') return '🔥 ' + progress + ' / ' + target + ' ngày';

  if (triggerType === 'net_worth_updated') return '💰 ' + fmt(progress) + ' / ' + fmt(target);

  if (triggerType === 'total_savings') return '🏦 ' + fmt(progress) + ' / ' + fmt(target);

  if (triggerType === 'stock_traded') return '📈 ' + progress + ' / ' + target + ' GD';

  if (triggerType === 'items_owned') return '🎒 ' + progress + ' / ' + target + ' món';

  if (triggerType === 'quest_claimed') return '📋 ' + progress + ' / ' + target + ' quest';

  if (triggerType === 'emergency_handled') return '🚨 ' + progress + ' / ' + target + ' lần';

  if (triggerType === 'quiz_answered') return '🧠 ' + progress + ' / ' + target + ' câu';

  if (triggerType === 'rank_reached') return '🏅 ' + progress + ' / ' + target;

  return progress + ' / ' + target;

}



async function claimAchievement(id) {

  try {

    const raw = await B.claimAchievementReward(id);

    const res = JSON.parse(raw);

    if (res.ok) {

      toast('success', '🎉 ' + (res.title || 'Thành tựu') + ' — Nhận ' + fmt(res.money || 0) + ' + ' + (res.xp || 0) + ' XP');

      await loadAchievements();

      await refreshBalance();

    } else {

      toast('error', res.error || 'Lỗi nhận thưởng');

    }

  } catch (e) {

    toast('error', 'Lỗi: ' + e.message);

  }

}



// ── Achievement toast notification (gọi từ dashboard khi có thành tựu mới) ──

function showAchievementToast(ach) {

  const area = document.getElementById('ach-toast-area') || document.getElementById('toasts');

  if (!area) return;

  const t = document.createElement('div');

  t.style.cssText = 'background:linear-gradient(135deg,rgba(250,204,21,.15),rgba(245,158,11,.1));border:1px solid rgba(250,204,21,.4);border-radius:12px;padding:12px 16px;backdrop-filter:blur(8px);max-width:320px;animation:slideUp .3s ease';

  t.innerHTML = '<div style="display:flex;align-items:center;gap:10px"><span style="font-size:28px">' + (ach.emoji||'🏆') + '</span><div><div style="font-weight:700;font-size:14px;color:var(--gold)">🏆 Thành tựu mới!</div><div style="font-size:13px;color:var(--text);margin-top:2px">' + (ach.title||'') + '</div></div></div>';

  area.appendChild(t);

  setTimeout(() => { t.style.transition = 'opacity .4s, transform .4s'; t.style.opacity = '0'; t.style.transform = 'translateX(40px)'; setTimeout(() => t.remove(), 400); }, 4000);

}



// ── Refresh dashboard achievement mini-section ──

async function refreshAchievementMini() {

  try {

    const raw = await B.getAchievementStats();

    const s = JSON.parse(raw);

    const el = document.getElementById('ach-mini');

    if (!el) return;

    if (s.unlocked > 0) {

      el.style.display = 'block';

      el.innerHTML = '<div style="display:flex;align-items:center;gap:8px;font-size:13px"><span>🏆</span><span style="flex:1">Thành tựu</span><span style="font-weight:700;color:var(--gold)">' + s.unlocked + ' / ' + s.total + '</span></div>';

      if (s.recent?.length) {

        el.innerHTML += '<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">' +

          s.recent.map(r => '<span style="font-size:11px;background:var(--surface2);padding:2px 8px;border-radius:4px;color:var(--muted2)">' + (r.emoji||'🏆') + ' ' + r.title + '</span>').join('') +

          '</div>';

      }

    } else {

      el.style.display = 'none';

    }

  } catch (e) {}

}



// ════════════════════════════════════════════

//  UTILS — Safe Big Number Formatting

// ════════════════════════════════════════════



// Format số tiền an toàn, không bị overflow với số > 2^53

// Dùng string manipulation thay vì Number.toLocaleString()

function _fmtSafe(n) {

  if (n === null || n === undefined) n = 0;

  let s = typeof n === 'string' ? n : String(n);

  let neg = false;

  if (s.startsWith('-')) { neg = true; s = s.slice(1); }

  s = s.replace(/[^0-9]/g, '');

  if (!s || s === '0') return '0';

  // Loại bỏ leading zeros

  s = s.replace(/^0+/, '') || '0';

  // Thêm dấu . sau mỗi 3 chữ số từ phải

  let result = '';

  for (let i = s.length - 1, c = 0; i >= 0; i--, c++) {

    if (c > 0 && c % 3 === 0) result = '.' + result;

    result = s[i] + result;

  }

  return (neg ? '-' : '') + result;

}



function fmt(n) {

  return _fmtSafe(n) + ' VND';

}



// So sánh số an toàn (hỗ trợ string)

function _numCmp(a, b) {

  const na = typeof a === 'string' ? BigInt(a.replace(/[^0-9-]/g,'') || '0') : BigInt(a||0);

  const nb = typeof b === 'string' ? BigInt(b.replace(/[^0-9-]/g,'') || '0') : BigInt(b||0);

  if (na > nb) return 1;

  if (na < nb) return -1;

  return 0;

}



function _numGte(a, b) { return _numCmp(a, b) >= 0; }

function _numLt(a, b) { return _numCmp(a, b) < 0; }



function toast(type, msg, ms=3500) {

  const c = document.getElementById('toasts');

  const t = document.createElement('div');

  t.className = 'toast ' + type;

  t.textContent = msg;

  c.appendChild(t);

  setTimeout(() => { t.style.transition='opacity .3s'; t.style.opacity='0'; setTimeout(()=>t.remove(),300); }, ms);

}





// ════════════════════════════════════════════

//  STREAK + RANK + QUEST

// ════════════════════════════════════════════



function fmtVND(n) {

  return _fmtSafe(n) + ' VND';

}



// ── Streak mini (dashboard) ──────────────────

async function refreshStreakRankMini() {

  const [sRaw, rRaw] = await Promise.all([B.getStreakStatus(), B.getRankStatus()]);

  const s = JSON.parse(sRaw);

  const r = JSON.parse(rRaw);



  // Streak

  const fire = s.streak > 0 ? (s.streak >= 30 ? '🔥🔥🔥' : s.streak >= 7 ? '🔥🔥' : '🔥') : '💤';

  document.getElementById('streak-fire').textContent = fire;

  document.getElementById('streak-num').textContent  = s.streak;

  document.getElementById('streak-mult').textContent = '×' + s.multiplier.toFixed(1);

  const hint = s.streak > 0

    ? `${s.today_cards}/${s.min_cards} thẻ hôm nay`

    : (s.today_cards >= s.min_cards ? 'Ôn thêm để tính streak mới' : `Cần ${s.cards_needed} thẻ nữa`);

  document.getElementById('streak-hint').textContent = hint;

  const bestEl = document.getElementById('streak-best');

  if (bestEl) bestEl.textContent = s.best > 0 ? `Kỷ lục: ${s.best} ngày` : '';



  // Rank mini

  document.getElementById('rank-emoji-sm').textContent  = r.rank_emoji;

  document.getElementById('rank-label-sm').textContent  = r.rank_label;

  document.getElementById('rank-xp-sm').textContent     = (r.xp||0).toLocaleString('vi-VN');

  document.getElementById('rank-prog-sm').style.width   = r.overall_pct + '%';

  document.getElementById('rank-prog-sm').style.background = `linear-gradient(90deg,${r.rank_color},${r.rank_color}aa)`;

  const mini = document.getElementById('rank-mini');

  if (mini) mini.style.borderColor = r.rank_color + '66';

  const nextLbl = r.is_max ? '🏆 Rank tối đa!' :

    `Tiếp: ${r.next_rank?.label} (${r.overall_pct}%)`;

  document.getElementById('rank-next-sm').textContent = nextLbl;

}



// ── Quest mini (dashboard) ────────────────────

async function refreshQuestMini() {

  const raw = await B.getQuestSummary();

  const data = JSON.parse(raw);

  const quests = data.quests || [];

  const el = document.getElementById('quest-mini-list');

  if (!quests.length) { el.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Chưa có quest.</div>'; return; }



  el.innerHTML = quests.map(q => {

    const pct = q.type === 'no_again_under' || q.type === 'no_purchase' || q.type === 'no_penalty'

      ? (q.done ? 100 : 0)

      : q.target > 0 ? Math.min(100, Math.round(q.progress / q.target * 100)) : 0;

    const col = q.done ? 'var(--green)' : 'var(--accent)';

    return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border)">

      <span style="font-size:16px">${q.emoji||'🎯'}</span>

      <div style="flex:1;min-width:0">

        <div style="font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${q.title}</div>

        <div style="background:var(--surface2);border-radius:3px;height:4px;margin-top:3px;overflow:hidden">

          <div style="height:100%;width:${pct}%;background:${col};border-radius:3px;transition:width .3s"></div>

        </div>

      </div>

      <span style="font-size:11px;font-weight:700;color:${col};flex-shrink:0">${q.done?'✅':''+pct+'%'}</span>

    </div>`;

  }).join('');

}



// ── Full Quests page ──────────────────────────

async function loadQuests() {

  const [sRaw, rRaw, qRaw] = await Promise.all([

    B.getStreakStatus(), B.getRankStatus(), B.getQuestSummary(),

  ]);

  const s = JSON.parse(sRaw);

  const r = JSON.parse(rRaw);

  const q = JSON.parse(qRaw);



  renderStreakFull(s);

  renderRankFull(r);

  renderQuestsFull(q);

  renderRanksTable();

}



function renderStreakFull(s) {

  document.getElementById('streak-count-full').textContent = s.streak;

  document.getElementById('streak-mult-full').textContent  = '×' + s.multiplier.toFixed(1);

  document.getElementById('streak-best-full').textContent  = s.best;

  const info = s.streak === 0

    ? `Hôm nay ôn ${s.today_cards}/${s.min_cards} thẻ — ${s.cards_needed > 0 ? 'cần thêm ' + s.cards_needed + ' thẻ để tính streak' : 'đủ streak!'}`

    : `🔥 Streak ${s.streak} ngày! Hôm nay ${s.today_cards}/${s.min_cards} thẻ.`;

  document.getElementById('streak-today-info').textContent = info;



  // Quest date

  const now = new Date();

  document.getElementById('quest-date-label').textContent =

    `${now.toLocaleDateString('vi-VN', {weekday:'long', day:'numeric', month:'long'})}`;

}



function renderRankFull(r) {

  document.getElementById('rank-emoji-big').textContent  = r.rank_emoji;

  document.getElementById('rank-label-full').textContent = r.rank_label;

  document.getElementById('rank-xp-full').textContent    = (r.xp||0).toLocaleString('vi-VN');

  document.getElementById('rank-group-full').textContent = 'Nhóm: ' + r.rank_group;



  const bar = document.getElementById('rank-prog-full');

  bar.style.width      = r.overall_pct + '%';

  bar.style.background = `linear-gradient(90deg,${r.rank_color},${r.rank_color}bb)`;



  const card = document.getElementById('rank-full-card');

  if (card) {

    card.style.borderColor = r.rank_color + '66';

    const glow = card.querySelector('.rank-glow');

    if (glow) glow.style.background = r.rank_color;

  }



  const progText = r.is_max

    ? '🏆 Đã đạt rank tối đa — Tỷ phú Anki!'

    : `Tiến tới ${r.next_rank?.label}: ${r.overall_pct}% (XP: ${r.xp_pct}%, Tiền: ${r.bal_pct}%)`;

  document.getElementById('rank-prog-text').textContent = progText;



  const reqEl = document.getElementById('rank-requirements');

  if (reqEl && r.next_rank) {

    const nx = r.next_rank;

    reqEl.innerHTML = `

      <div style="background:var(--surface2);border-radius:8px;padding:8px;text-align:center">

        <div style="font-size:10px;color:var(--muted2);margin-bottom:2px">XP cần thêm</div>

        <div style="font-weight:800;color:var(--accent2)">⭐ ${(r.xp_needed||0).toLocaleString('vi-VN')}</div>

      </div>

      <div style="background:var(--surface2);border-radius:8px;padding:8px;text-align:center">

        <div style="font-size:10px;color:var(--muted2);margin-bottom:2px">Tiền cần thêm</div>

        <div style="font-weight:800;color:var(--yellow)">💰 ${fmtVND(r.bal_needed)}</div>

      </div>`;

  } else if (reqEl) {

    reqEl.innerHTML = '<div style="text-align:center;color:var(--green);font-weight:700;padding:8px;grid-column:1/-1">🏆 Rank tối đa — bạn là huyền thoại!</div>';

  }

}



function renderQuestsFull(data) {

  const quests  = data.quests || [];

  const done    = data.done || 0;

  document.getElementById('quest-done-badge').textContent = `${done}/${quests.length} hoàn thành`;

  document.getElementById('quest-done-badge').className =

    done === quests.length ? 'badge badge-green' : 'badge badge-purple';



  const el = document.getElementById('quest-full-list');

  if (!quests.length) { el.innerHTML = '<div class="empty"><div class="ei">📋</div><p>Chưa có quest.</p></div>'; return; }



  el.innerHTML = quests.map(q => {

    const isDone    = q.done;

    const isClaimed = q.reward_claimed;

    let pct = 0;

    if (q.type === 'no_again_under' || q.type === 'no_purchase' || q.type === 'no_penalty') {

      pct = isDone ? 100 : 0;

    } else {

      pct = q.target > 0 ? Math.min(100, Math.round(q.progress / q.target * 100)) : 0;

    }

    const progText = q.type === 'no_again_under'

      ? `${q.progress} lần Again (cần ≤ ${q.target})`

      : `${q.progress} / ${q.target}`;



    return `<div class="quest-card ${isDone?'done':''} ${isClaimed?'claimed':''}">

      <div style="display:flex;align-items:flex-start;gap:10px">

        <span class="quest-emoji">${q.emoji||'🎯'}</span>

        <div style="flex:1">

          <div class="quest-title">${q.title}</div>

          <div class="quest-desc">${q.desc}</div>

          <div style="display:flex;align-items:center;gap:8px;margin-top:6px">

            <div class="quest-prog-wrap">

              <div class="quest-prog-bar ${isDone?'done':''}" style="width:${pct}%"></div>

            </div>

            <span style="font-size:11px;color:var(--muted2);flex-shrink:0">${progText}</span>

          </div>

          <div style="display:flex;align-items:center;justify-content:space-between;margin-top:4px">

            <span class="quest-reward">

              ${q.money > 0 ? '💵 +' + fmtVND(q.money) : ''}

              ${q.xp > 0 ? ' ⭐ +' + q.xp + ' XP' : ''}

            </span>

            ${isDone && !isClaimed

              ? `<button class="btn btn-green" style="font-size:11px;padding:3px 10px" onclick="claimQuest('${q.id}')">🎁 Nhận thưởng</button>`

              : isClaimed ? '<span style="font-size:11px;color:var(--muted2)">✅ Đã nhận</span>'

              : `<span style="font-size:11px;color:var(--muted2)">${pct}%</span>`

            }

          </div>

        </div>

      </div>

    </div>`;

  }).join('');

}



async function claimQuest(questId) {

  const res = JSON.parse(await B.claimQuestReward(questId));

  if (res.ok) {

    toast('ok', `🎁 ${res.quest_title}: +${fmtVND(res.money)} ${res.xp>0?'⭐ +'+res.xp+' XP':''}`.trim());

    await loadQuests();

    await refreshStreakRankMini();

  } else {

    toast('err', '❌ ' + res.error);

  }

}



let _allRanks = null;

async function renderRanksTable() {

  if (!_allRanks) {

    _allRanks = JSON.parse(await B.getAllRanks());

  }

  const el = document.getElementById('ranks-table');

  const curRankId = JSON.parse(await B.getRankStatus()).rank_id;

  el.innerHTML = _allRanks.map(r => {

    const isCur = r.id === curRankId;

    return `<div style="display:flex;align-items:center;gap:10px;padding:7px 10px;border-radius:8px;font-size:12px;

        ${isCur ? 'background:rgba(124,58,237,.12);border:1px solid rgba(124,58,237,.3)' : 'background:var(--surface2)'}">

      <span style="font-size:20px">${r.emoji}</span>

      <span style="flex:1;font-weight:${isCur?700:500};color:${isCur?r.color:'var(--text)'}">${r.label}</span>

      <span style="color:var(--accent2);font-size:11px">⭐ ${r.xp.toLocaleString('vi-VN')} XP</span>

      <span style="color:var(--yellow);font-size:11px">💰 ${fmtVND(r.bal)}</span>

      ${isCur ? '<span class="badge badge-purple" style="font-size:9px">← Bạn</span>' : ''}

    </div>`;

  }).join('');

}





// ════════════════════════════════════════════

//  KNOWLEDGE BASE

// ════════════════════════════════════════════

let _kbNotes = [];

let _kbCurrentId = null;

let _kbCurrentEmoji = '📝';

const KB_EMOJIS = ['📝','💡','📚','📊','💰','🏦','📈','📉','💳','🏠','🚗','✈️',

                   '🎓','⚖️','🛡️','🔑','💎','🌍','🏆','⭐','🔥','💼','🤝','📋'];

const KB_DEFAULT_CATS = ['Cơ bản','Ngân sách','Đầu tư','Tiết kiệm','Kinh tế','Thực tế','Bảo vệ','Ghi chú'];



async function loadKnowledge() {

  const [notesRaw, catsRaw] = await Promise.all([B.getAllNotes(), B.getCategories()]);

  _kbNotes = JSON.parse(notesRaw);

  renderKbList(_kbNotes);

  buildKbCatFilter(JSON.parse(catsRaw));

  const stats = document.getElementById('kb-stats');

  const pinned = _kbNotes.filter(n=>n.pinned).length;

  stats.textContent = `${_kbNotes.length} ghi chú • ${pinned} ghim`;

}



function renderKbList(notes) {

  const el = document.getElementById('kb-list-el');

  if (!notes.length) {

    el.innerHTML = `<div class="empty"><div class="ei">💡</div>

      <p>Chưa có ghi chú nào.<br>Nhấn <strong>✏️ Thêm mới</strong> để bắt đầu!</p></div>`;

    return;

  }

  el.innerHTML = notes.map(n => {

    const preview = (n.body||'').replace(/\n/g,' ').slice(0, 80) + ((n.body||'').length > 80 ? '…' : '');

    const tags    = (n.tags||[]).slice(0,3).map(t=>`<span class="kb-tag">#${t}</span>`).join('');

    const updated = n.updated ? n.updated.slice(0,10) : '';

    return `<div class="kb-card ${n.pinned?'pinned':''}" onclick="openKbDetail('${n.id}')">

      <div style="display:flex;align-items:flex-start;gap:10px">

        <span class="kb-emoji">${n.emoji||'📝'}</span>

        <div style="flex:1;min-width:0">

          <div style="display:flex;align-items:center;gap:6px">

            <span class="kb-title">${n.title}</span>

            ${n.pinned ? '<span style="font-size:11px">📌</span>' : ''}

          </div>

          <div class="kb-meta">

            <span class="badge badge-purple" style="font-size:9px;padding:1px 6px">${n.category||'Ghi chú'}</span>

            <span style="margin-left:6px">${updated}</span>

          </div>

          <div class="kb-body-preview">${preview}</div>

          <div style="margin-top:4px">${tags}</div>

        </div>

      </div>

    </div>`;

  }).join('');

}



function buildKbCatFilter(cats) {

  const sel = document.getElementById('kb-cat-filter');

  const cur = sel.value;

  sel.innerHTML = '<option value="">📂 Tất cả</option>';

  cats.forEach(c => sel.insertAdjacentHTML('beforeend',`<option value="${c}">${c}</option>`));

  if (cur) sel.value = cur;

}



async function kbSearch() {

  const q = document.getElementById('kb-search').value.trim();

  if (!q) { kbFilter(); return; }

  const raw = await B.searchNotes(q);

  renderKbList(JSON.parse(raw));

}



function kbFilter() {

  const cat = document.getElementById('kb-cat-filter').value;

  const filtered = cat ? _kbNotes.filter(n=>n.category===cat) : _kbNotes;

  renderKbList(filtered);

}



// ── Detail ──────────────────────────────────

async function openKbDetail(id) {

  const raw = await B.getNoteById(id);

  const n   = JSON.parse(raw);

  if (!n || !n.id) return;

  _kbCurrentId = id;



  document.getElementById('kb-list-view').style.display   = 'none';

  document.getElementById('kb-detail-view').style.display = 'block';



  document.getElementById('kb-detail-emoji').textContent = n.emoji || '📝';

  document.getElementById('kb-detail-title').textContent = n.title || '';

  document.getElementById('kb-detail-body').textContent  = n.body  || '';



  const cat     = n.category || 'Ghi chú';

  const updated = n.updated ? n.updated.replace('T',' ').slice(0,16) : '';

  document.getElementById('kb-detail-meta').textContent = `${cat} • Cập nhật: ${updated}`;



  const tagsEl = document.getElementById('kb-detail-tags');

  tagsEl.innerHTML = (n.tags||[]).map(t=>`<span class="kb-tag">#${t}</span>`).join('');



  const pinBtn = document.getElementById('kb-pin-btn');

  pinBtn.textContent = n.pinned ? '📌 Bỏ ghim' : '📌 Ghim';

}



function closeKbDetail() {

  document.getElementById('kb-detail-view').style.display = 'none';

  document.getElementById('kb-list-view').style.display   = 'block';

  _kbCurrentId = null;

  loadKnowledge();

}



async function kbTogglePin() {

  if (!_kbCurrentId) return;

  const res = JSON.parse(await B.togglePin(_kbCurrentId));

  const pinBtn = document.getElementById('kb-pin-btn');

  pinBtn.textContent = res.pinned ? '📌 Bỏ ghim' : '📌 Ghim';

  toast('ok', res.pinned ? '📌 Đã ghim ghi chú' : '📌 Đã bỏ ghim');

}



async function kbDeleteCurrent() {

  if (!_kbCurrentId) return;

  const title = document.getElementById('kb-detail-title').textContent;

  if (!confirm(`Xoá ghi chú "${title}"?`)) return;

  await B.deleteNote(_kbCurrentId);

  toast('info', '🗑️ Đã xoá ghi chú');

  closeKbDetail();

}



// ── Editor ──────────────────────────────────

let _kbEditingId = null;



function openKbEditor(note = null) {

  _kbEditingId    = note ? note.id : null;

  _kbCurrentEmoji = note ? (note.emoji || '📝') : '📝';



  document.getElementById('kb-list-view').style.display   = 'none';

  document.getElementById('kb-detail-view').style.display = 'none';

  document.getElementById('kb-editor-view').style.display = 'block';



  document.getElementById('kb-editor-title-label').textContent =

    note ? '✏️ Sửa ghi chú' : '✏️ Thêm ghi chú mới';



  document.getElementById('kb-title-inp').value  = note ? note.title  : '';

  document.getElementById('kb-body-inp').value   = note ? note.body   : '';

  document.getElementById('kb-cat-inp').value    = '';

  document.getElementById('kb-tags-inp').value   = note ? (note.tags||[]).join(', ') : '';

  document.getElementById('kb-emoji-custom').value = '';



  // Render emoji picker

  const picker = document.getElementById('kb-emoji-picker');

  picker.innerHTML = KB_EMOJIS.map(e =>

    `<span class="emoji-opt ${e===_kbCurrentEmoji?'sel':''}" onclick="setKbEmoji('${e}')">${e}</span>`

  ).join('');



  // Render category chips

  const chipsEl = document.getElementById('kb-cat-chips');

  const allCats = [...new Set([...KB_DEFAULT_CATS, ...(_kbNotes.map(n=>n.category).filter(Boolean))])];

  const curCat  = note ? note.category : 'Ghi chú';

  chipsEl.innerHTML = allCats.map(c =>

    `<span class="cat-chip ${c===curCat?'sel':''}" onclick="selectKbCat(this,'${c}')">${c}</span>`

  ).join('');

  if (note) document.getElementById('kb-cat-inp').value = '';

}



function openKbEditorForCurrent() {

  if (!_kbCurrentId) return;

  const n = _kbNotes.find(x=>x.id===_kbCurrentId)

         || JSON.parse(document.getElementById('kb-detail-body').textContent || '{}');

  const title = document.getElementById('kb-detail-title').textContent;

  const body  = document.getElementById('kb-detail-body').textContent;

  const meta  = document.getElementById('kb-detail-meta').textContent;

  const cat   = meta.split(' • ')[0] || 'Ghi chú';

  const emoji = document.getElementById('kb-detail-emoji').textContent;

  const tags  = [...document.getElementById('kb-detail-tags').querySelectorAll('.kb-tag')]

                  .map(el=>el.textContent.replace('#',''));

  openKbEditor({ id: _kbCurrentId, title, body, category: cat, emoji, tags });

}



function closeKbEditor() {

  document.getElementById('kb-editor-view').style.display = 'none';

  if (_kbEditingId) {

    // Trở về detail

    document.getElementById('kb-detail-view').style.display = 'block';

  } else {

    document.getElementById('kb-list-view').style.display = 'block';

    loadKnowledge();

  }

}



function setKbEmoji(e) {

  if (!e || !e.trim()) return;

  _kbCurrentEmoji = e.trim();

  document.querySelectorAll('.emoji-opt').forEach(el => {

    el.classList.toggle('sel', el.textContent === _kbCurrentEmoji);

  });

  document.getElementById('kb-emoji-custom').value = '';

}



function selectKbCat(el, cat) {

  document.querySelectorAll('.cat-chip').forEach(c=>c.classList.remove('sel'));

  el.classList.add('sel');

  document.getElementById('kb-cat-inp').value = '';

  el.dataset.val = cat;

}



function _getSelectedCat() {

  const custom = document.getElementById('kb-cat-inp').value.trim();

  if (custom) return custom;

  const sel = document.querySelector('.cat-chip.sel');

  return sel ? (sel.dataset.val || sel.textContent) : 'Ghi chú';

}



async function kbSave() {

  const title = document.getElementById('kb-title-inp').value.trim();

  const body  = document.getElementById('kb-body-inp').value;

  if (!title) { toast('err','❌ Vui lòng nhập tiêu đề!'); return; }

  if (!body.trim()) { toast('err','❌ Vui lòng nhập nội dung!'); return; }



  const cat   = _getSelectedCat();

  const emoji = _kbCurrentEmoji || '📝';

  const rawTags = document.getElementById('kb-tags-inp').value;

  const tags  = rawTags.split(',').map(t=>t.trim()).filter(Boolean);

  const tagsJson = JSON.stringify(tags);



  let res;

  if (_kbEditingId) {

    res = JSON.parse(await B.updateNote(_kbEditingId, title, body, cat, emoji, tagsJson));

  } else {

    res = JSON.parse(await B.createNote(title, body, cat, emoji, tagsJson));

  }



  if (res.ok !== false) {

    toast('ok', _kbEditingId ? '✅ Đã cập nhật ghi chú!' : '✅ Đã tạo ghi chú mới!');

    document.getElementById('kb-editor-view').style.display = 'none';

    _kbEditingId = null;

    await loadKnowledge();

    document.getElementById('kb-list-view').style.display = 'block';

  } else {

    toast('err', '❌ ' + (res.error || 'Lỗi lưu ghi chú'));

  }

}





// ════════════════════════════════════════════

//  REAL ESTATE

// ════════════════════════════════════════════

async function loadRealEstate() {

  const raw  = await B.getPortfolio();

  const props = JSON.parse(raw);



  // Load market values summary

  let reSummary = {};

  try { reSummary = JSON.parse(await B.getRESummary()); } catch(e) {}



  // Overview

  document.getElementById('re-count').textContent   = props.length;

  const monthly = props.reduce((s,p)=>s+(p.monthly_net||0),0);

  const pending  = props.reduce((s,p)=>s+(p.pending||0),0);

  document.getElementById('re-monthly').textContent = fmt(monthly);

  document.getElementById('re-pending').textContent = fmt(pending);

  document.getElementById('re-mktval').textContent  = fmt(reSummary.total_market_value||0);

  document.getElementById('re-roi').textContent     = (reSummary.avg_roi_pct||0).toFixed(1) + '%';

  const unrealized = (reSummary.total_market_value||0) - (reSummary.total_invested||0);

  document.getElementById('re-unrealized').textContent = fmt(unrealized);

  document.getElementById('re-unrealized').style.color = unrealized >= 0 ? 'var(--green)' : 'var(--red)';



  const el = document.getElementById('re-list');

  if (!props.length) {

    el.innerHTML = `<div class="empty"><div class="ei">🏠</div>

      <p>Chưa có bất động sản nào.<br>

      Mua BĐS trong <a href="#" onclick="go('shop');return false" style="color:var(--accent2)">Cửa hàng</a>!</p>

    </div>`;

    return;

  }



  el.innerHTML = props.map(p => {

    const sat = p.satisfaction || {pct:0, color:'#ef4444', label:'?', will_rent:false};

    const taxPerMonth = Math.round((p.rent_price||0) * 0.15);

    const netPerMonth = (p.rent_price||0) - taxPerMonth;

    const mktVal = p.market_value || 0;

    const valChg = p.value_change || 0;

    const valChgPct = p.value_change_pct || 0;

    const valCls = valChg >= 0 ? 'up' : 'dn';

    const valIcon = valChg >= 0 ? '📈' : '📉';

    const upgradeLvl = p.upgrade_level || 0;

    const roi = p.price > 0 ? ((mktVal - p.price) / p.price * 100).toFixed(1) : '0.0';

    return `<div class="re-card ${p.vacant?'vacant':''}" id="re-${p.slot_id}">

      <div style="display:flex;align-items:flex-start;gap:12px">

        <span style="font-size:36px">${p.emoji||'🏠'}</span>

        <div style="flex:1">

          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">

            <span style="font-size:15px;font-weight:800">${p.name}</span>

            <span class="stock-change ${valCls}" style="font-size:11px;padding:2px 6px;border-radius:4px;white-space:nowrap">

              ${valIcon} ${fmt(mktVal)} (${valChgPct >= 0 ? '+' : ''}${valChgPct.toFixed(1)}%)

            </span>

            ${upgradeLvl > 0 ? `<span class="badge badge-purple" style="font-size:10px">🔨 Cấp ${upgradeLvl}</span>` : ''}

          </div>

          <div style="font-size:11px;color:var(--muted2);margin-top:2px">

            Mua ${p.bought_at||''} · Giá mua: ${fmt(p.price||0)} · ROI: ${roi}%

          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin:10px 0;font-size:12px">

            <div style="background:var(--surface2);border-radius:6px;padding:7px;text-align:center">

              <div style="color:var(--muted2)">Giá thuê/tháng</div>

              <div style="font-weight:800;color:var(--yellow)">${fmt(p.rent_price||0)}</div>

            </div>

            <div style="background:var(--surface2);border-radius:6px;padding:7px;text-align:center">

              <div style="color:var(--muted2)">Net sau thuế</div>

              <div style="font-weight:800;color:var(--green)">${fmt(netPerMonth)}</div>

            </div>

            <div style="background:var(--surface2);border-radius:6px;padding:7px;text-align:center">

              <div style="color:var(--muted2)">Chờ thu</div>

              <div style="font-weight:800;color:var(--accent2)">${fmt(p.pending||0)}</div>

            </div>

          </div>

        </div>

      </div>



      <!-- Satisfaction bar -->

      <div style="margin-bottom:8px">

        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">

          <span style="color:var(--muted2)">Mức độ hài lòng khách thuê</span>

          <span class="sat-label" style="color:${sat.color}">${sat.label} (${sat.pct}%)</span>

        </div>

        <div class="sat-bar-wrap">

          <div class="sat-bar" style="width:${sat.pct}%;background:${sat.color}"></div>

        </div>

        ${p.vacant ? '<div style="font-size:11px;color:var(--red);font-weight:700">🚫 Khách không thuê — hạ giá xuống!</div>' : ''}

      </div>



      <!-- Rent slider -->

      <div style="margin-bottom:10px">

        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">

          <span style="color:var(--muted2)">Điều chỉnh giá thuê</span>

          <span style="color:var(--muted2)">Giá thị trường: <strong style="color:var(--text)">${fmt(p.fair_rent||0)}</strong></span>

        </div>

        <input type="range" class="rent-slider" id="slider-${p.slot_id}"

          min="${Math.round((p.fair_rent||1)*0.3)}"

          max="${Math.round((p.fair_rent||1)*2.5)}"

          step="${Math.round((p.fair_rent||1)*0.05)}"

          value="${p.rent_price||p.fair_rent||0}"

          oninput="onRentSlider('${p.slot_id}',this.value,${p.fair_rent||0})"

          onchange="saveRentPrice('${p.slot_id}',this.value)"/>

        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-top:2px">

          <span>×0.3 (rất rẻ)</span><span>×1.0 (thị trường)</span><span>×2.5 (rất đắt)</span>

        </div>

        <div style="margin-top:6px;display:flex;gap:6px">

          <input class="inp" id="rent-inp-${p.slot_id}" type="number"

            value="${p.rent_price||p.fair_rent||0}" min="0" step="1000000"

            style="flex:1;font-size:13px"

            onchange="syncSliderFromInp('${p.slot_id}',this.value,${p.fair_rent||0})"/>

          <button class="btn btn-ghost" style="font-size:11px" onclick="saveRentPrice('${p.slot_id}',document.getElementById('rent-inp-${p.slot_id}').value)">✓ Lưu</button>

        </div>

      </div>

      <div style="display:flex;justify-content:flex-end;gap:6px;flex-wrap:wrap">

        <button class="btn" style="font-size:11px;padding:4px 10px" onclick="openUpgradeModal('${p.slot_id}')">🔨 Nâng cấp</button>

        <button class="btn btn-red" style="font-size:11px;padding:4px 10px" onclick="sellProperty('${p.slot_id}','${p.name}')">🏚️ Bán lại</button>

      </div>

    </div>`;

  }).join('');

}



function onRentSlider(slotId, val, fairRent) {

  const v = parseInt(val)||0;

  const inp = document.getElementById('rent-inp-'+slotId);

  if (inp) inp.value = v;

  // Live update satisfaction bar

  const card = document.getElementById('re-'+slotId);

  if (!card) return;

  const sat = calcSatLocal(v, fairRent);

  const bar  = card.querySelector('.sat-bar');

  const lbl  = card.querySelector('.sat-label');

  if (bar) { bar.style.width = sat.pct+'%'; bar.style.background = sat.color; }

  if (lbl) { lbl.textContent = sat.label+' ('+sat.pct+'%)'; lbl.style.color = sat.color; }

}



function calcSatLocal(rent, fair) {

  if (!fair) return {pct:100,color:'#10b981',label:'Rất hài lòng 😊'};

  const r = rent / fair;

  let pct;

  if (r<=0.6) pct=100;

  else if (r<=1.0) pct=Math.round(60+(1.0-r)/0.4*40);

  else if (r<=1.4) pct=Math.round(20+(1.4-r)/0.4*40);

  else if (r<=1.8) pct=Math.round(5+(1.8-r)/0.4*15);

  else pct=0;

  pct=Math.max(0,Math.min(100,pct));

  if (pct>=80) return {pct,color:'#10b981',label:'Rất hài lòng 😊'};

  if (pct>=60) return {pct,color:'#34d399',label:'Hài lòng 🙂'};

  if (pct>=40) return {pct,color:'#f59e0b',label:'Chấp nhận 😐'};

  if (pct>=20) return {pct,color:'#f97316',label:'Không vui 😒'};

  return {pct,color:'#ef4444',label:'Không thuê! 🚫'};

}



function syncSliderFromInp(slotId, val, fairRent) {

  const v = parseInt(val)||0;

  const sl = document.getElementById('slider-'+slotId);

  if (sl) sl.value = v;

  onRentSlider(slotId, v, fairRent);

}



async function saveRentPrice(slotId, val) {

  const v = parseInt(val)||0;

  const res = JSON.parse(await B.setRentPrice(slotId, v));

  if (res.ok) {

    toast('ok', res.vacant ? '⚠️ Giá quá cao — khách không thuê!' : '✅ Đã lưu giá thuê');

    await loadRealEstate();

  } else { toast('err','❌ '+(res.error||'Lỗi')); }

}



async function collectRent() {

  const res = JSON.parse(await B.collectAllRent());

  if (res.net > 0) {

    toast('ok', `💰 Thu được ${fmt(res.net)} (thuế: ${fmt(res.tax)})`);

    await loadRealEstate();

  } else {

    toast('info', 'ℹ️ Chưa có tiền thuê để thu');

  }

}



async function sellProperty(slotId, name) {

  // Fetch market value for confirm message

  let mktValStr = 'giá trị thị trường';

  try {

    const raw = await B.getPortfolio();

    const props = JSON.parse(raw);

    const prop = props.find(p => p.slot_id === slotId);

    if (prop && prop.market_value) mktValStr = fmt(prop.market_value);

  } catch(e) {}

  if (!confirm(`Bán "${name}"?\nGiá bán (thị trường): ${mktValStr} (trừ 5% phí môi giới)\nThu tiền thuê trước khi bán!`)) return;

  const res = JSON.parse(await B.removeProperty(slotId));

  if (res.ok) { toast('info','🏚️ Đã bán bất động sản'); await loadRealEstate(); }

  else toast('err','❌ '+(res.error||'Lỗi'));

}



// ── Upgrade Modal ──────────────────────────────────

let _upgradeSlotId = '';



async function openUpgradeModal(slotId) {

  _upgradeSlotId = slotId;

  const modal = document.getElementById('modal-upgrade-re');

  try {

    const raw = await B.getPropertyUpgradeInfo(slotId);

    const info = JSON.parse(raw);

    if (!info.ok) {

      toast('err', '❌ ' + (info.error || 'Không thể lấy thông tin nâng cấp'));

      return;

    }



    // Hiển thị thông tin

    const infoEl = document.getElementById('upgrade-re-info');

    const detailEl = document.getElementById('upgrade-re-detail');



    const curLvl = info.level || 0;

    const maxLvl = info.max_level || 5;



    if (curLvl >= maxLvl) {

      infoEl.innerHTML = `

        <div style="text-align:center;padding:10px">

          <div style="font-size:40px;margin-bottom:8px">🏆</div>

          <div style="font-weight:800;color:var(--green)">BĐS đã đạt cấp tối đa!</div>

          <div style="font-size:12px;color:var(--muted2);margin-top:4px">Cấp ${maxLvl}/${maxLvl}</div>

        </div>`;

      detailEl.innerHTML = '';

      document.getElementById('upgrade-re-confirm-btn').style.display = 'none';

      modal.classList.add('open');

      document.body.style.overflow = 'hidden';

      return;

    }



    document.getElementById('upgrade-re-confirm-btn').style.display = 'inline-flex';



    infoEl.innerHTML = `

      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">

        <span style="font-size:32px">🔨</span>

        <div>

          <div style="font-weight:800">Nâng cấp BĐS</div>

          <div style="font-size:12px;color:var(--muted2)">Cấp hiện tại: ${curLvl} → Cấp ${curLvl + 1}</div>

        </div>

      </div>

      <div style="background:var(--surface2);border-radius:8px;padding:10px;font-size:13px;line-height:1.8">

        <div>💰 Chi phí nâng cấp: <strong style="color:var(--red)">${fmt(info.next_cost || 0)}</strong></div>

        <div>📈 Giá thuê tăng: <strong style="color:var(--green)">+${info.fair_rent_bonus_pct || 10}%</strong> (thêm ${fmt(info.fair_rent_bonus || 0)}/tháng)</div>

        <div>🏠 Giá trị BĐS tăng: <strong style="color:var(--green)">+${info.value_bonus_pct || 8}%</strong></div>

      </div>`;



    // Chi tiết các cấp

    const rows = [];

    for (let i = 1; i <= maxLvl; i++) {

      const isCurrent = i === curLvl + 1;

      const isPast = i <= curLvl;

      const lvlCost = Math.round(info.base_cost ? info.base_cost * i : 0);

      rows.push(`<div style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;background:${isCurrent ? 'rgba(59,130,246,.12)' : isPast ? 'rgba(16,185,129,.08)' : 'transparent'};font-size:12px">

        <span>${isPast ? '✅' : isCurrent ? '🔜' : '🔒'}</span>

        <span style="flex:1">Cấp ${i}</span>

        <span style="color:var(--muted2)">${isPast ? 'Đã nâng cấp' : fmt(lvlCost)}</span>

      </div>`);

    }

    detailEl.innerHTML = rows.join('');



  } catch(e) {

    toast('err', '❌ Lỗi khi tải thông tin nâng cấp');

    return;

  }

  modal.classList.add('open');

  document.body.style.overflow = 'hidden';

}



function closeUpgradeModal() {

  document.getElementById('modal-upgrade-re').classList.remove('open');

  document.body.style.overflow = '';

  _upgradeSlotId = '';

}



async function confirmUpgrade() {

  if (!_upgradeSlotId) return;

  const btn = document.getElementById('upgrade-re-confirm-btn');

  btn.disabled = true;

  btn.textContent = '⏳ Đang nâng cấp...';

  try {

    const raw = await B.upgradeProperty(_upgradeSlotId);

    const res = JSON.parse(raw);

    if (res.ok) {

      toast('ok', '🔨 Nâng cấp BĐS thành công!');

      closeUpgradeModal();

      await loadRealEstate();

    } else {

      toast('err', '❌ ' + (res.error || 'Không đủ tiền?'));

    }

  } catch(e) {

    toast('err', '❌ Lỗi khi nâng cấp');

  }

  btn.disabled = false;

  btn.textContent = '🔨 Nâng cấp';

}



// Close modal on overlay click

document.getElementById('modal-budget').addEventListener('click', e => {

  if (e.target === e.currentTarget) closeBudgetModal();

});

document.getElementById('modal-chart')?.addEventListener('click', e => {

  if (e.target === e.currentTarget) closeChartModal();

});

document.getElementById('modal-txn-detail')?.addEventListener('click', e => {

  if (e.target === e.currentTarget) closeTxnDetail();

});

document.getElementById('modal-upgrade-re')?.addEventListener('click', e => {

  if (e.target === e.currentTarget) closeUpgradeModal();

});



// ════════════════════════════════════════════

//  GOALS (Req 3)

// ════════════════════════════════════════════

let _goalItems = [];  // cache shop items cho modal



async function refreshGoal() {

  const raw = await B.getGoal();

  const g   = JSON.parse(raw);

  const card    = document.getElementById('goal-card');

  const empty   = document.getElementById('goal-empty-prompt');



  if (!g.has_goal) {

    card.style.display  = 'none';

    empty.style.display = 'block';

    return;

  }

  card.style.display  = 'block';

  empty.style.display = 'none';



  document.getElementById('goal-emoji').textContent    = g.item_emoji || '🎯';

  document.getElementById('goal-name').textContent     = g.item_name || '';

  document.getElementById('goal-pct').textContent      = g.percent + '%';

  document.getElementById('goal-price-info').textContent = 'Giá: ' + fmt(g.item_price);

  document.getElementById('goal-set-at').textContent   = g.set_at ? 'Đặt lúc ' + g.set_at : '';



  const bar  = document.getElementById('goal-bar');

  const wrap = document.getElementById('goal-progress-wrap');

  bar.style.width = g.percent + '%';

  wrap.classList.toggle('goal-reached', g.reached);



  const remaining = document.getElementById('goal-remaining');

  const badge     = document.getElementById('goal-reached-badge');

  if (g.reached) {

    remaining.textContent = '🎉 Đủ tiền mua rồi!';

    remaining.style.color = 'var(--green)';

    badge.style.display   = 'inline-flex';

  } else {

    remaining.textContent = `còn thiếu ${fmt(g.remaining)}`;

    remaining.style.color = 'var(--muted2)';

    badge.style.display   = 'none';

  }

}



async function openGoalModal() {

  const modal = document.getElementById('modal-goal');

  modal.classList.add('open');

  // Load shop items nếu chưa có

  if (!_goalItems.length) {

    const raw = await B.getShopItems();

    _goalItems = JSON.parse(raw);

  }

  filterGoalItems();

}



function closeGoalModal() {

  document.getElementById('modal-goal').classList.remove('open');

  document.getElementById('goal-search-inp').value = '';

}



function filterGoalItems() {

  const q     = (document.getElementById('goal-search-inp').value || '').toLowerCase();

  const items = q

    ? _goalItems.filter(i => i.name.toLowerCase().includes(q) || (i.category||'').toLowerCase().includes(q))

    : _goalItems;

  const el = document.getElementById('goal-items-list');

  if (!items.length) {

    el.innerHTML = '<div style="text-align:center;color:var(--muted2);padding:20px">Không tìm thấy sản phẩm</div>';

    return;

  }

  el.innerHTML = items.map(i => `

    <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;background:var(--surface2);border-radius:8px;cursor:pointer;transition:background .15s"

      onmouseenter="this.style.background='var(--surface3)'" onmouseleave="this.style.background='var(--surface2)'"

      onclick="selectGoalItem('${i.id}','${i.name.replace(/'/g,"\'")}',${i.price},'${i.emoji||'🎯'}')">

      <span style="font-size:24px">${i.image_url ? '' : (i.emoji||'📦')}</span>

      ${i.image_url ? `<img src="${i.image_url}" style="width:32px;height:32px;border-radius:6px;object-fit:cover" onerror="this.style.display='none'">` : ''}

      <div style="flex:1">

        <div style="font-size:13px;font-weight:700">${i.name}</div>

        <div style="font-size:11px;color:var(--muted2)">${i.category||''}</div>

      </div>

      <div style="font-size:13px;font-weight:800;color:var(--yellow)">${fmt(i.price)}</div>

    </div>`).join('');

}



async function selectGoalItem(id, name, price, emoji) {

  const res = JSON.parse(await B.setGoal(id, name, price, emoji));

  if (res.ok) {

    closeGoalModal();

    toast('ok', `🎯 Đã đặt mục tiêu: ${name}`);

    await refreshGoal();

  } else {

    toast('err', '❌ ' + (res.error || 'Lỗi đặt mục tiêu'));

  }

}



async function doDeleteGoal() {

  if (!confirm('Xoá mục tiêu hiện tại?')) return;

  await B.clearGoal();

  toast('info', '🗑️ Đã xoá mục tiêu');

  await refreshGoal();

}



document.getElementById('modal-goal')?.addEventListener('click', e => {

  if (e.target === e.currentTarget) closeGoalModal();

});



// ════════════════════════════════════════════

//  STOCK MARKET (Phase 1)

// ════════════════════════════════════════════



let _stockData = [];

let _stockPortfolio = [];

let _stockSort = 'symbol';

let _buySymbol = null;

let _sellSymbol = null;



let _stockCountdownInterval = null;



function goStocks() {

  // Dùng combined API để fix bất đồng bộ dữ liệu

  loadAllStockData();

  // Start countdown timer (cập nhật mỗi giây)

  startSessionCountdown();

}



function startSessionCountdown() {

  if (_stockCountdownInterval) clearInterval(_stockCountdownInterval);

  updateSessionTimer(); // cập nhật ngay

  _stockCountdownInterval = setInterval(updateSessionTimer, 1000);

}



function stopSessionCountdown() {

  if (_stockCountdownInterval) {

    clearInterval(_stockCountdownInterval);

    _stockCountdownInterval = null;

  }

}



let _cachedSessionInfo = null;

let _lastSessionFetch = 0;

function updateSessionTimer() {

  const el = document.getElementById('st-countdown');

  const lbl = document.getElementById('st-label');

  if (!el || !lbl) return;

  // Fetch từ bridge mỗi 10 giây, giữa các lần tự countdown local

  const now = Date.now();

  if (now - _lastSessionFetch >= 10000) {

    _lastSessionFetch = now;

    B.getTradingSessionInfo().then(raw => {

      try {

        _cachedSessionInfo = JSON.parse(raw);

        updateTimerDisplay(_cachedSessionInfo, el, lbl);

      } catch(e) {}

    });

  } else if (_cachedSessionInfo) {

    // Countdown local mượt mà mỗi giây

    const info = _cachedSessionInfo;

    if (info.in_session && info.seconds_until_end > 0) {

      info.seconds_until_end--;

    } else if (!info.in_session && info.seconds_until_next > 0) {

      info.seconds_until_next--;

    }

    updateTimerDisplay(info, el, lbl);

  }

}



function updateTimerDisplay(info, el, lbl) {

  if (!info || info.error) {

    el.textContent = '--:--:--';

    el.className = 'st-countdown wait';

    lbl.textContent = '🔄 Phiên giao dịch';

    return;

  }

  if (info.in_session) {

    const sec = info.seconds_until_end || 0;

    const h = Math.floor(sec / 3600);

    const m = Math.floor((sec % 3600) / 60);

    const s = sec % 60;

    el.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;

    el.className = 'st-countdown live';

    lbl.textContent = `🟢 ${info.session_name} - kết thúc sau`;

  } else {

    const sec = info.seconds_until_next || 0;

    const h = Math.floor(sec / 3600);

    const m = Math.floor((sec % 3600) / 60);

    const s = sec % 60;

    el.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;

    el.className = 'st-countdown wait';

    lbl.textContent = `⏳ ${info.session_name} - bắt đầu sau`;

  }

}



// ── Combined All Data (Phase 2 - Fix bất đồng bộ) ──

async function loadAllStockData() {

  try {

    const raw = JSON.parse(await B.getStockAllData());

    if (!raw.ok) { toast('err', '❌ ' + (raw.error || 'Lỗi tải dữ liệu')); return; }



    // Cache market data

    _stockData = raw.market || [];



    // Build sector filter options

    const sectors = [...new Set(_stockData.map(s => s.sector).filter(Boolean))];

    const sel = document.getElementById('stock-sector-filter');

    const curVal = sel.value;

    sel.innerHTML = '<option value="all">🏭 Tất cả</option>' +

      sectors.map(s => `<option value="${s}">${s}</option>`).join('');

    sel.value = curVal;



    renderStockGrid();

    updateStockOverview();



    // VN-Index summary

    const s = raw.summary || {};

    document.getElementById('stock-vnindex').textContent = s.vnindex?.toLocaleString() || '—';

    document.getElementById('stock-vnindex').className = 'vnindex ' + ((s.vnindex_change || 0) >= 0 ? 'up' : 'dn');

    document.getElementById('stock-vnchange').textContent =

      ((s.vnindex_change || 0) >= 0 ? '+' : '') + (s.vnindex_change || 0)?.toFixed(2) +

      ' (' + ((s.vnindex_change_pct || 0) >= 0 ? '+' : '') + (s.vnindex_change_pct || 0)?.toFixed(2) + '%)';

    document.getElementById('stock-vnchange').className = 'vnindex-change ' + ((s.vnindex_change || 0) >= 0 ? 'up' : 'dn');

    document.getElementById('stock-vntime').textContent = '🕒 ' + (s.last_updated || '');



    // Portfolio (cached)

    _stockPortfolio = raw.portfolio || [];

    renderPortfolio();



    // Portfolio summary

    const ps = raw.portfolio_summary || {};

    document.getElementById('ps-invested').textContent = (ps.total_invested||0).toLocaleString();

    document.getElementById('ps-marketval').textContent = (ps.total_market_value||0).toLocaleString();

    const pnlEl = document.getElementById('ps-pnl');

    pnlEl.textContent = ((ps.total_pnl||0) >= 0 ? '+' : '') + (ps.total_pnl||0).toLocaleString();

    pnlEl.className = 'ps-val ' + ((ps.total_pnl||0) >= 0 ? 'pos' : 'neg');



    // Transactions

    renderStockTransactions(raw.transactions || []);



    // Trading session

    if (raw.trading_session) {

      const el = document.getElementById('st-countdown');

      const lbl = document.getElementById('st-label');

      if (el && lbl) updateTimerDisplay(raw.trading_session, el, lbl);

    }

  } catch (e) {

    toast('err', '❌ Lỗi tải dữ liệu thị trường');

  }

}



function renderPortfolio() {

  const el = document.getElementById('portfolio-holdings');

  const holdings = _stockPortfolio;

  if (!holdings.length) {

    el.innerHTML = '<div class="empty"><div class="ei">💼</div><div>Chưa có cổ phiếu nào</div><div style="font-size:12px;color:var(--muted2)">Mua ngay từ tab Danh sách!</div></div>';

    return;

  }

  el.innerHTML = holdings.map(h => {

    const pnl = h.pnl||0;

    const pnlPct = h.pnl_pct||0;

    const pnlCls = pnl >= 0 ? 'pos' : 'neg';

    const canSell = h.can_sell !== false;

    const cd = h.cooldown_remaining || 0;

    let cdHtml = '';

    if (!canSell && cd > 0) {

      const cdH = Math.floor(cd / 3600);

      const cdM = Math.floor((cd % 3600) / 60);

      cdHtml = `<span class="cooldown-badge"><span class="cd-icon">🔒</span>T+${h.cooldown_days||2} ${cdH}h${cdM}p</span>`;

    } else if (canSell) {

      cdHtml = `<span class="cooldown-badge ready"><span class="cd-icon">✅</span>Sẵn sàng bán</span>`;

    }

    return `<div class="holding-card">

      <div class="hc-top">

        <div>

          <div class="hc-symbol">${h.symbol} ${cdHtml}</div>

          <div class="hc-company">${h.company||'—'}</div>

        </div>

        <div class="hc-pnl ${pnlCls}">${pnl >= 0 ? '+' : ''}${pnl.toLocaleString()} (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)</div>

      </div>

      <div class="hc-detail">

        <div class="hcd-item"><div class="hcd-val">${(h.shares||0).toLocaleString()}</div><div class="hcd-lbl">Số lượng</div></div>

        <div class="hcd-item"><div class="hcd-val">${(h.avg_cost||0).toLocaleString()}</div><div class="hcd-lbl">Giá vốn TB</div></div>

        <div class="hcd-item"><div class="hcd-val">${(h.current_price||0).toLocaleString()}</div><div class="hcd-lbl">Giá hiện tại</div></div>

        <div class="hcd-item"><div class="hcd-val">${(h.market_value||0).toLocaleString()}</div><div class="hcd-lbl">Giá trị</div></div>

      </div>

      <div style="display:flex;gap:6px;margin-top:4px">

        <button class="btn" style="flex:1;font-size:11px;padding:5px" onclick="openBuyModal('${h.symbol}')">🟢 Mua thêm</button>

        <button class="btn ${canSell ? 'btn-ghost' : ''}" style="flex:1;font-size:11px;padding:5px" onclick="openSellModal('${h.symbol}')"

          ${canSell ? '' : 'disabled title="Đang trong thời gian T+2"'} >

          ${canSell ? '🔴 Bán' : '🔒 T+2'}

        </button>

      </div>

    </div>`;

  }).join('');

}



function renderStockTransactions(txns) {

  const el = document.getElementById('stock-txn-list');

  if (!txns || !txns.length) {

    el.innerHTML = '<div class="empty"><div class="ei">📜</div><div>Chưa có giao dịch nào</div></div>';

    return;

  }

  el.innerHTML = txns.map(t => {

    const tType = t.type === 'buy' ? 'Mua' : 'Bán';

    const tCls = t.type === 'buy' ? 'buy' : 'sell';

    const icon = t.type === 'buy' ? '🟢' : '🔴';

    return `<div class="txn-stock-item">

      <div class="tsi-icon">${icon}</div>

      <div class="tsi-body">

        <span class="tsi-sym">${t.symbol}</span>

        <span style="color:var(--muted2)"> — ${t.shares} cp × ${(t.price||0).toLocaleString()}</span>

        <div style="font-size:10px;color:var(--muted)">${t.date || t.time || ''}</div>

      </div>

      <div class="tsi-type ${tCls}">${tType}</div>

      <div class="tsi-amt">${(t.total||0).toLocaleString()}</div>

    </div>`;

  }).join('');

}



// ════════════════════════════════════════════════════════════

//  DIGITAL ASSETS — Tài sản số (Crypto)

// ════════════════════════════════════════════════════════════



let _cryptoMarket     = [];   // market array

let _cryptoPortfolio  = [];   // holdings

let _cryptoStaking    = [];   // staking positions

let _cryptoTxns       = [];   // transactions

let _cryptoSort       = 'change_pct';

let _buyCryptoSym     = null;

let _sellCryptoSym    = null;

let _stakeCryptoSym   = null;

let _detailCryptoSym  = null;



async function loadDigitalAssets() {

  try {

    const raw = JSON.parse(await B.getCryptoAllData());

    if (!raw.ok) { toast('err', '❌ ' + (raw.error || 'Lỗi tải crypto')); return; }

    _cryptoMarket    = raw.market    || [];

    _cryptoPortfolio = raw.portfolio || [];

    _cryptoStaking   = raw.staking   || [];

    _cryptoTxns      = raw.transactions || [];

    renderMarketCycleBanner(raw.market_cycle || {});

    renderCryptoHero(raw.portfolio_summary || {});

    renderCryptoGrid();

    renderCryptoPortfolio();

    renderCryptoStaking();

    renderCryptoTransactions();

  } catch (e) {

    toast('err', '❌ Lỗi tải tài sản số: ' + e.message);

  }

}



// ── Banner ──────────────────────────────────────────────────

function renderMarketCycleBanner(cycle) {

  const el = document.getElementById('crypto-cycle-banner');

  if (!el) return;

  el.className = 'market-cycle-banner ' + (cycle.color || 'neutral');

  el.textContent = cycle.label || '⚖️ Thị trường trung lập';

}



// ── Hero summary ─────────────────────────────────────────────

function renderCryptoHero(summary) {

  const fmt = v => fmtVND(v);

  const pnl = summary.total_pnl || 0;

  const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };

  el('cov-invested', fmt(summary.total_invested || 0));

  el('cov-mktval',   fmt(summary.total_market_value || 0));

  const pnlEl = document.getElementById('cov-pnl');

  if (pnlEl) {

    pnlEl.textContent = (pnl >= 0 ? '+' : '') + fmt(pnl);

    pnlEl.style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)';

  }

  el('cov-staking', fmt(summary.total_staking_vnd || 0));

}



// ── Tab switching ────────────────────────────────────────────

function switchCryptoTab(tab) {

  document.querySelectorAll('.crypto-tab').forEach(t => t.classList.remove('active'));

  const tabEl = document.getElementById('ctab-' + tab);

  if (tabEl) tabEl.classList.add('active');

  document.querySelectorAll('.crypto-panel').forEach(p => p.classList.remove('active'));

  const panelEl = document.getElementById('cpanel-' + tab);

  if (panelEl) panelEl.classList.add('active');

}



// ── Market grid ───────────────────────────────────────────────

function sortCryptoBy(field) {

  _cryptoSort = field;

  renderCryptoGrid();

}



function renderCryptoGrid() {

  const container = document.getElementById('crypto-market-grid');

  if (!container) return;

  const catFilter = (document.getElementById('crypto-cat-filter') || {}).value || 'all';

  const searchQ   = ((document.getElementById('crypto-search') || {}).value || '').toLowerCase().trim();



  let list = _cryptoMarket.slice();

  if (catFilter !== 'all') list = list.filter(a => a.category === catFilter);

  if (searchQ) list = list.filter(a =>

    a.symbol.toLowerCase().includes(searchQ) ||

    (a.name || '').toLowerCase().includes(searchQ) ||

    (a.name_vi || '').toLowerCase().includes(searchQ)

  );

  if (_cryptoSort === 'change_pct') {

    list.sort((a, b) => (b.change_pct || 0) - (a.change_pct || 0));

  } else {

    list.sort((a, b) => (b.price || 0) - (a.price || 0));

  }



  if (!list.length) {

    container.innerHTML = '<div class="empty" style="grid-column:1/-1;margin-top:30px"><div class="ei">🔍</div><div>Không tìm thấy coin nào</div></div>';

    return;

  }



  container.innerHTML = list.map(a => {

    const chg       = a.change_pct || 0;

    const isStable  = a.is_stablecoin;

    const isRugged  = a.rug_pulled;

    const cardClass = isRugged ? 'rugged' : isStable ? 'stable' : chg >= 0 ? 'up' : 'dn';

    const priceClass = isStable ? 'stable' : chg >= 0 ? 'up' : 'dn';

    const chgStr    = (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%';

    const apyBadge  = a.staking_apy > 0 ? `<span class="crypto-apy-badge">🏦 ${(a.staking_apy*100).toFixed(1)}% APY</span>` : '';

    const rugBadge  = isRugged ? `<span class="rug-badge">🚨 Rug Pull</span>` : '';

    return `

<div class="crypto-card ${cardClass}" onclick="showCryptoDetail('${a.symbol}')">

  <div class="cc-row">

    <div>

      <div class="cc-sym">${a.emoji || '🪙'} ${a.symbol}${rugBadge}</div>

      <div class="cc-name">${a.name_vi || a.name}</div>

    </div>

    <span class="crypto-cat-badge">${a.category}</span>

  </div>

  <div class="cc-row">

    <div class="cc-price ${priceClass}">${fmtVND(a.price)}</div>

    <div class="cc-chg ${chg >= 0 ? 'up' : 'dn'}">${chgStr}</div>

  </div>

  <div class="cc-row" style="flex-wrap:wrap;gap:4px">

    ${apyBadge}

    <span class="crypto-exch">📍 ${a.exchange}</span>

  </div>

  <button class="btn" style="width:100%;margin-top:4px;font-size:12px" onclick="event.stopPropagation();openBuyCryptoModal('${a.symbol}')">🟢 Mua</button>

</div>`;

  }).join('');

}



// ── Portfolio ─────────────────────────────────────────────────

function renderCryptoPortfolio() {

  const container = document.getElementById('crypto-holdings-list');

  if (!container) return;

  if (!_cryptoPortfolio.length) {

    container.innerHTML = `<div class="empty" style="margin-top:30px"><div class="ei">💼</div><div>Chưa có tài sản nào</div><div style="font-size:12px;color:var(--muted2);margin-top:6px">Mua crypto trên tab Thị trường hoặc Cửa hàng</div></div>`;

    return;

  }

  container.innerHTML = _cryptoPortfolio.map(h => {

    const pnl      = h.pnl || 0;

    const pnlPct   = h.pnl_pct || 0;

    const pnlClass = pnl >= 0 ? 'pos' : 'neg';

    const pnlStr   = (pnl >= 0 ? '+' : '') + fmtVND(pnl) + ` (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)`;

    const qty      = h.quantity || 0;

    const avail    = h.avail_qty || 0;

    const staked   = h.staked_amount || 0;

    const hasStaking = (h.staking_apy || 0) > 0;

    const stakeBtnHtml = hasStaking

      ? `<button class="btn btn-ghost" style="font-size:11px" onclick="openStakeModal('${h.symbol}')">🏦 Stake</button>`

      : '';

    return `

<div class="crypto-holding-card">

  <div class="ch-head">

    <div>

      <div class="ch-sym">${h.emoji || '🪙'} ${h.symbol}</div>

      <div class="ch-meta">Số lượng: ${qty.toFixed(6)} • Khả dụng: ${avail.toFixed(6)}${staked > 0 ? ` • Đang stake: ${staked.toFixed(6)}` : ''}</div>

      <div class="ch-meta">Giá vốn TB: ${fmtVND(h.avg_cost_per_unit || 0)} • Sàn: ${h.exchange || ''}</div>

    </div>

    <div class="ch-value">

      <div class="ch-val">${fmtVND(h.market_value || 0)}</div>

      <div class="ch-pnl ${pnlClass}">${pnlStr}</div>

    </div>

  </div>

  <div style="display:flex;gap:6px;flex-wrap:wrap">

    <button class="btn btn-ghost" style="font-size:11px" onclick="openBuyCryptoModal('${h.symbol}')">➕ Mua thêm</button>

    <button class="btn btn-ghost" style="font-size:11px;color:var(--red);border-color:var(--red)" onclick="openSellCryptoModal('${h.symbol}')">🔴 Bán</button>

    ${stakeBtnHtml}

  </div>

</div>`;

  }).join('');

}



// ── Staking positions ────────────────────────────────────────

function renderCryptoStaking() {

  const container = document.getElementById('crypto-staking-list');

  if (!container) return;

  if (!_cryptoStaking.length) {

    container.innerHTML = '<div style="font-size:13px;color:var(--muted2);padding:8px 0">Chưa có vị thế staking nào.</div>';

    return;

  }

  container.innerHTML = _cryptoStaking.map(s => {

    const locked   = s.locked;

    const daysLeft = s.days_left || 0;

    const lockStr  = locked ? `🔒 Còn ${daysLeft} ngày` : '✅ Sẵn sàng rút';

    const unBtn    = locked ? '' : `<button class="btn" style="font-size:11px;background:var(--accent2)" onclick="doUnstake('${s.stake_id}')">📤 Rút stake</button>`;

    return `

<div class="staking-card">

  <div class="sk-head">

    <span class="sk-sym">${s.emoji || '🪙'} ${s.symbol}</span>

    <span class="sk-apy">APY ${((s.staking_apy||0)*100).toFixed(1)}%</span>

  </div>

  <div class="sk-detail">

    Đang stake: <strong>${(s.staked_amount||0).toFixed(6)}</strong> ${s.symbol} (~${fmtVND(s.staked_vnd||0)})<br>

    Trạng thái: ${lockStr}<br>

    Bắt đầu: ${s.staked_at ? new Date(s.staked_at*1000).toLocaleDateString('vi-VN') : '—'}

  </div>

  ${unBtn ? `<div style="margin-top:8px">${unBtn}</div>` : ''}

</div>`;

  }).join('');

}



// ── Transactions ─────────────────────────────────────────────

function renderCryptoTransactions() {

  const container = document.getElementById('crypto-txn-list');

  if (!container) return;

  if (!_cryptoTxns.length) {

    container.innerHTML = '<div class="empty" style="margin-top:30px"><div class="ei">📜</div><div>Chưa có giao dịch nào</div></div>';

    return;

  }

  const list = [..._cryptoTxns].reverse();

  container.innerHTML = list.map(t => {

    const typeLabel = { buy:'Mua', sell:'Bán', stake:'Stake', unstake:'Unstake' }[t.type] || t.type;

    const amtStr = t.total_vnd > 0 ? fmtVND(t.total_vnd) : (t.note || '');

    return `

<div class="crypto-txn-item">

  <span class="crypto-txn-badge ${t.type}">${typeLabel}</span>

  <span style="font-size:18px">${t.emoji || '🪙'}</span>

  <div style="flex:1">

    <div style="font-size:13px;font-weight:700">${t.symbol} — ${(t.quantity||0).toFixed(6)}</div>

    <div style="font-size:11px;color:var(--muted2)">${t.date || ''} · ${t.exchange || ''}</div>

  </div>

  <div style="text-align:right;font-size:13px;font-weight:700">${amtStr}</div>

</div>`;

  }).join('');

}



// ── Buy Modal ─────────────────────────────────────────────────

function openBuyCryptoModal(symbol) {

  const asset = _cryptoMarket.find(a => a.symbol === symbol);

  if (!asset) return;

  _buyCryptoSym = symbol;

  document.getElementById('bc-emoji').textContent   = asset.emoji || '🪙';

  document.getElementById('bc-symbol').textContent  = asset.symbol;

  document.getElementById('bc-name-vi').textContent = asset.name_vi || asset.name;

  document.getElementById('bc-price').textContent   = fmtVND(asset.price);

  document.getElementById('bc-exchange').textContent = '📍 ' + (asset.exchange || '');

  document.getElementById('bc-amount').value = '';

  document.getElementById('bc-preview').textContent = '';

  document.getElementById('modal-buy-crypto').classList.add('open');

  document.getElementById('bc-amount').focus();

}



function openBuyCryptoFromDetail() {

  document.getElementById('modal-crypto-detail').classList.remove('open');

  if (_detailCryptoSym) openBuyCryptoModal(_detailCryptoSym);

}



function setCryptoAmt(amount) {

  document.getElementById('bc-amount').value = amount;

  previewBuyCrypto();

}



function previewBuyCrypto() {

  const asset = _cryptoMarket.find(a => a.symbol === _buyCryptoSym);

  if (!asset) return;

  const amt = parseInt(document.getElementById('bc-amount').value) || 0;

  const fee = Math.round(amt * 0.001);

  const net = amt - fee;

  const qty = net / (asset.price || 1);

  document.getElementById('bc-preview').innerHTML =

    `Nhận: <strong>${qty.toFixed(6)} ${asset.symbol}</strong> · Phí: ${fmtVND(fee)}`;

}



async function confirmBuyCrypto() {

  const amt = parseInt(document.getElementById('bc-amount').value) || 0;

  if (!_buyCryptoSym || amt <= 0) { toast('warn', '⚠️ Nhập số tiền hợp lệ.'); return; }

  const btn = document.getElementById('bc-confirm-btn');

  btn.disabled = true;

  try {

    const res = JSON.parse(await B.buyCrypto(_buyCryptoSym, amt));

    if (!res.ok) { toast('err', '❌ ' + res.error); return; }

    document.getElementById('modal-buy-crypto').classList.remove('open');

    toast('ok', `✅ Mua ${res.quantity.toFixed(6)} ${_buyCryptoSym} thành công!`);

    loadDigitalAssets();

  } catch(e) { toast('err', '❌ ' + e.message); }

  finally { btn.disabled = false; }

}



// ── Sell Modal ─────────────────────────────────────────────────

function openSellCryptoModal(symbol) {

  const h = _cryptoPortfolio.find(h => h.symbol === symbol);

  const a = _cryptoMarket.find(a => a.symbol === symbol);

  if (!h || !a) return;

  _sellCryptoSym = symbol;

  document.getElementById('sc-emoji').textContent    = h.emoji || '🪙';

  document.getElementById('sc-symbol').textContent   = symbol;

  document.getElementById('sc-holding').textContent  = `Số lượng: ${(h.quantity||0).toFixed(6)} · Khả dụng: ${(h.avail_qty||0).toFixed(6)}`;

  document.getElementById('sc-price').textContent    = fmtVND(a.price);

  document.getElementById('sc-pnl-now').textContent  = `PnL: ${h.pnl >= 0 ? '+' : ''}${fmtVND(h.pnl||0)}`;

  document.getElementById('sc-pnl-now').style.color  = (h.pnl||0) >= 0 ? 'var(--green)' : 'var(--red)';

  document.getElementById('sc-pct-slider').value = 50;

  document.getElementById('sc-pct-label').textContent = '50%';

  document.getElementById('sc-preview').textContent   = '';

  previewSellCrypto();

  document.getElementById('modal-sell-crypto').classList.add('open');

}



function previewSellCrypto() {

  const pct    = parseInt(document.getElementById('sc-pct-slider').value) || 50;

  const h      = _cryptoPortfolio.find(h => h.symbol === _sellCryptoSym);

  const a      = _cryptoMarket.find(a => a.symbol === _sellCryptoSym);

  document.getElementById('sc-pct-label').textContent = pct + '%';

  if (!h || !a) return;

  const sellQty  = (h.avail_qty || 0) * pct / 100;

  const gross    = sellQty * (a.price || 0);

  const fee      = gross * 0.001;

  const net      = gross - fee;

  const costBasis = sellQty * (h.avg_cost_per_unit || a.price);

  const pnl      = net - costBasis;

  document.getElementById('sc-preview').innerHTML =

    `Thu về: <strong>${fmtVND(Math.round(net))}</strong> · PnL: <span style="color:${pnl>=0?'var(--green)':'var(--red)'}">${pnl>=0?'+':''}${fmtVND(Math.round(pnl))}</span>`;

}



async function confirmSellCrypto() {

  const pct = parseInt(document.getElementById('sc-pct-slider').value) || 50;

  if (!_sellCryptoSym) return;

  try {

    const res = JSON.parse(await B.sellCrypto(_sellCryptoSym, pct / 100));

    if (!res.ok) { toast('err', '❌ ' + res.error); return; }

    document.getElementById('modal-sell-crypto').classList.remove('open');

    const pnlStr = (res.pnl >= 0 ? '+' : '') + fmtVND(res.pnl || 0);

    toast('ok', `✅ Bán ${_sellCryptoSym} — Thu về ${fmtVND(res.net_vnd)} · PnL: ${pnlStr}`);

    loadDigitalAssets();

  } catch(e) { toast('err', '❌ ' + e.message); }

}



// ── Stake Modal ────────────────────────────────────────────────

function openStakeModal(symbol) {

  const h = _cryptoPortfolio.find(h => h.symbol === symbol);

  const a = _cryptoMarket.find(a => a.symbol === symbol);

  if (!h || !a || (a.staking_apy || 0) <= 0) {

    toast('warn', `⚠️ ${symbol} không hỗ trợ staking.`); return;

  }

  _stakeCryptoSym = symbol;

  document.getElementById('stk-emoji').textContent  = h.emoji || '🪙';

  document.getElementById('stk-symbol').textContent = symbol;

  document.getElementById('stk-apy').textContent    = `APY: ${((a.staking_apy||0)*100).toFixed(1)}% / năm`;

  document.getElementById('stk-pct-slider').value   = 50;

  document.getElementById('stk-pct-label').textContent = '50%';

  previewStake();

  document.getElementById('modal-stake-crypto').classList.add('open');

}



function previewStake() {

  const pct = parseInt(document.getElementById('stk-pct-slider').value) || 50;

  document.getElementById('stk-pct-label').textContent = pct + '%';

  const h = _cryptoPortfolio.find(h => h.symbol === _stakeCryptoSym);

  const a = _cryptoMarket.find(a => a.symbol === _stakeCryptoSym);

  if (!h || !a) return;

  const stakeQty  = (h.avail_qty || 0) * pct / 100;

  const annualYield = stakeQty * (a.staking_apy || 0);

  document.getElementById('stk-preview').innerHTML =

    `Stake: <strong>${stakeQty.toFixed(6)} ${_stakeCryptoSym}</strong> · Yield ~${annualYield.toFixed(6)} ${_stakeCryptoSym}/năm`;

}



async function confirmStakeCrypto() {

  const pct = parseInt(document.getElementById('stk-pct-slider').value) || 50;

  if (!_stakeCryptoSym) return;

  try {

    const res = JSON.parse(await B.stakeCrypto(_stakeCryptoSym, pct / 100));

    if (!res.ok) { toast('err', '❌ ' + res.error); return; }

    document.getElementById('modal-stake-crypto').classList.remove('open');

    toast('ok', `🏦 Đã stake ${res.amount.toFixed(6)} ${_stakeCryptoSym} · APY ${((res.apy||0)*100).toFixed(1)}%`);

    loadDigitalAssets();

  } catch(e) { toast('err', '❌ ' + e.message); }

}



// ── Unstake ────────────────────────────────────────────────────

async function doUnstake(stakeId) {

  try {

    const res = JSON.parse(await B.unstakeCrypto(stakeId));

    if (!res.ok) { toast('err', '❌ ' + res.error); return; }

    toast('ok', `📤 Rút stake thành công! Yield: +${res.yield_units.toFixed(6)} ${res.symbol}`);

    loadDigitalAssets();

  } catch(e) { toast('err', '❌ ' + e.message); }

}



// ── Crypto Detail ──────────────────────────────────────────────

async function showCryptoDetail(symbol) {

  const asset = _cryptoMarket.find(a => a.symbol === symbol);

  if (!asset) return;

  _detailCryptoSym = symbol;

  document.getElementById('cd-emoji').textContent    = asset.emoji || '🪙';

  document.getElementById('cd-symbol').textContent   = symbol;

  document.getElementById('cd-name').textContent     = asset.name_vi || asset.name;

  document.getElementById('cd-price').textContent    = fmtVND(asset.price);

  const chg = asset.change_pct || 0;

  const chgEl = document.getElementById('cd-change');

  chgEl.textContent = (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%';

  chgEl.style.color = chg >= 0 ? 'var(--green)' : 'var(--red)';

  document.getElementById('cd-category').textContent    = asset.category;

  document.getElementById('cd-exchange-label').textContent = '📍 ' + (asset.exchange || '') + (asset.staking_apy > 0 ? ` · 🏦 Staking APY ${((asset.staking_apy||0)*100).toFixed(1)}%` : '');

  document.getElementById('modal-crypto-detail').classList.add('open');



  // Load price history

  try {

    const histRaw = JSON.parse(await B.getCryptoHistory(symbol, 50));

    if (histRaw.ok && histRaw.data && histRaw.data.length > 1) {

      renderCryptoChart('cd-chart', histRaw.data);

    }

  } catch(e) {}

}



function renderCryptoChart(containerId, data) {

  const container = document.getElementById(containerId);

  if (!container || !data.length) return;

  const prices = data.map(d => d[1]);

  const minP   = Math.min(...prices);

  const maxP   = Math.max(...prices);

  const range  = maxP - minP || 1;

  container.innerHTML = prices.map((p, i) => {

    const h   = Math.max(4, Math.round(((p - minP) / range) * 100));

    const chg = i > 0 ? p - prices[i-1] : 0;

    const col = chg >= 0 ? 'var(--green)' : 'var(--red)';

    return `<div style="flex:1;height:${h}%;background:${col};border-radius:2px 2px 0 0;min-height:4px;transition:height .3s" title="${fmtVND(p)}"></div>`;

  }).join('');

}



// ── Tab switching ──

function switchStockTab(tab) {

  document.querySelectorAll('.stock-tab').forEach(t => t.classList.remove('active'));

  document.getElementById('stab-' + tab).classList.add('active');

  document.querySelectorAll('.stock-panel').forEach(p => p.classList.remove('active'));

  document.getElementById('spanel-' + tab).classList.add('active');

  // Dùng dữ liệu đã cache từ loadAllStockData() — fix bất đồng bộ

  if (tab === 'portfolio') {

    if (_stockPortfolio && _stockPortfolio.length) renderPortfolio();

    else loadAllStockData();

  }

  if (tab === 'txns') {

    // Transactions đã được render sẵn trong loadAllStockData, chỉ refresh nếu chưa có

    const txnEl = document.getElementById('stock-txn-list');

    if (!txnEl || !txnEl.children.length || txnEl.innerHTML.includes('Chưa có')) {

      loadAllStockData();

    }

  }

  if (tab === 'events') {

    loadDividendData();

  }

}



// ── Dividend & Corporate Actions ──────────────────

let _divTab = 'history';



function switchDivTab(tab) {

  _divTab = tab;

  document.getElementById('div-tab-history').classList.toggle('active', tab === 'history');

  document.getElementById('div-tab-corp').classList.toggle('active', tab === 'corp');

  document.getElementById('div-history-list').style.display = tab === 'history' ? 'block' : 'none';

  document.getElementById('div-corp-list').style.display = tab === 'corp' ? 'block' : 'none';

}



async function loadDividendData() {

  // Load dividend summary

  try {

    const raw = JSON.parse(await B.getDividendSummary());

    if (raw.ok) {

      document.getElementById('div-total-received').textContent = fmt(raw.total_received || 0);

      document.getElementById('div-avg-yield').textContent = (raw.avg_yield_pct || 0).toFixed(2) + '%';

      document.getElementById('div-symbol-count').textContent = raw.symbol_count || 0;

    }

  } catch(e) {}



  // Load dividend history

  try {

    const raw = JSON.parse(await B.getDividendHistory());

    if (raw.ok) {

      renderDividendHistory(raw.data || []);

    }

  } catch(e) {}



  // Load corporate action history

  try {

    const raw = JSON.parse(await B.getCorporateActionHistory());

    if (raw.ok) {

      renderCorporateActions(raw.data || []);

    }

  } catch(e) {}

}



function renderDividendHistory(data) {

  const el = document.getElementById('div-history-list');

  if (!data.length) {

    el.innerHTML = '<div class="empty"><div class="ei">💰</div><div>Chưa có cổ tức nào</div><div style="font-size:12px;color:var(--muted2)">Cổ tức được trả tự động mỗi phiên giao dịch</div></div>';

    return;

  }

  el.innerHTML = data.slice(0, 50).map(d => {

    const date = d.date || d.time || '';

    return `<div class="stock-txn-item" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-bottom:1px solid var(--border);font-size:13px">

      <span style="font-size:20px">💰</span>

      <div style="flex:1;min-width:0">

        <div style="font-weight:700">${d.symbol || '—'}</div>

        <div style="font-size:11px;color:var(--muted2)">${date}</div>

      </div>

      <div style="text-align:right">

        <div style="font-weight:800;color:var(--green)">+${fmt(d.amount || 0)}</div>

        <div style="font-size:11px;color:var(--muted2)">${(d.yield_pct || 0).toFixed(2)}%</div>

      </div>

    </div>`;

  }).join('');

  if (data.length > 50) {

    el.innerHTML += `<div style="text-align:center;padding:8px;font-size:11px;color:var(--muted2)">... và ${data.length - 50} khoản cổ tức khác</div>`;

  }

}



function renderCorporateActions(data) {

  const el = document.getElementById('div-corp-list');

  if (!data.length) {

    el.innerHTML = '<div class="empty"><div class="ei">🏢</div><div>Chưa có sự kiện doanh nghiệp nào</div></div>';

    return;

  }

  el.innerHTML = data.slice(0, 30).map(d => {

    const type = d.type || '';

    let icon = '🏢', label = '', detail = '';

    if (type === 'split') {

      icon = '🔀'; label = 'Chia tách cổ phiếu';

      detail = `${d.old_shares||0} → ${d.new_shares||0} cp · Điều chỉnh giá vốn`;

    } else if (type === 'bonus') {

      icon = '🎁'; label = 'Cổ phiếu thưởng';

      detail = `Nhận ${fmt(d.bonus_shares||0)} cp · Giá vốn điều chỉnh: ${fmt(d.avg_cost||0)}`;

    } else if (type === 'rights') {

      icon = '📋'; label = 'Phát hành quyền mua';

      detail = `Mua ${fmt(d.rights_shares||0)} cp giá ${fmt(d.rights_price||0)} · Tổng: ${fmt(d.cost||0)}`;

    }

    const date = d.date || d.time || '';

    return `<div class="stock-txn-item" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-bottom:1px solid var(--border);font-size:13px">

      <span style="font-size:20px">${icon}</span>

      <div style="flex:1;min-width:0">

        <div style="font-weight:700">${d.symbol || '—'} · ${label}</div>

        <div style="font-size:11px;color:var(--muted2)">${detail}</div>

        <div style="font-size:10px;color:var(--muted)">${date}</div>

      </div>

    </div>`;

  }).join('');

  if (data.length > 30) {

    el.innerHTML += `<div style="text-align:center;padding:8px;font-size:11px;color:var(--muted2)">... và ${data.length - 30} sự kiện khác</div>`;

  }

}



function renderStockGrid() {

  const q = (document.getElementById('stock-search').value || '').toLowerCase();

  const sector = document.getElementById('stock-sector-filter').value;

  let list = _stockData.filter(s => {

    if (sector !== 'all' && s.sector !== sector) return false;

    if (q && !s.symbol.toLowerCase().includes(q) && !(s.company||'').toLowerCase().includes(q)) return false;

    return true;

  });



  // Sort

  if (_stockSort === 'symbol') list.sort((a, b) => a.symbol.localeCompare(b.symbol));

  else if (_stockSort === 'change') list.sort((a, b) => (b.change_pct||0) - (a.change_pct||0));

  else if (_stockSort === 'price') list.sort((a, b) => (b.price||0) - (a.price||0));



  const el = document.getElementById('stock-grid');

  if (!list.length) {

    el.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--muted2);padding:30px">🔍 Không tìm thấy mã nào</div>';

    return;

  }

  el.innerHTML = list.map(s => {

    const cls = s.change > 0 ? 'up' : s.change < 0 ? 'dn' : 'flat';

    const pCls = s.change > 0 ? 'up' : s.change < 0 ? 'dn' : '';

    const chgStr = (s.change >= 0 ? '+' : '') + (s.change||0).toFixed(2) + ' (' + (s.change_pct >= 0 ? '+' : '') + (s.change_pct||0).toFixed(2) + '%)';

    return `<div class="stock-card ${cls}">

      <div class="sc-top">

        <div>

          <div class="sc-symbol">${s.symbol}</div>

          <div class="sc-company">${s.company||'—'}</div>

        </div>

        <div style="text-align:right">

          <div class="sc-price ${pCls}">${(s.price||0).toLocaleString()}</div>

          <div class="sc-change ${pCls}">${chgStr}</div>

        </div>

      </div>

      <div class="sc-meta">

        <span>📊 ${(s.volume||0).toLocaleString()}</span>

      </div>

      <div class="sc-sector">🏭 ${s.sector||'—'}</div>

      <div class="sc-actions">

        <button class="btn" style="flex:1" onclick="openBuyModal('${s.symbol}')">🟢 Mua</button>

        <button class="btn btn-ghost" style="flex:1" onclick="openSellModal('${s.symbol}')">🔴 Bán</button>

        <button class="btn btn-ghost" style="flex:0;padding:5px 10px" onclick="showStockDetail('${s.symbol}')">📊</button>

      </div>

    </div>`;

  }).join('');

}



function filterStocks() { renderStockGrid(); }



function sortStocks(by) {

  _stockSort = by;

  document.querySelectorAll('.stock-sort-btn').forEach(b => b.classList.toggle('active', b.dataset.sort === by));

  renderStockGrid();

}



function updateStockOverview() {

  const total = _stockData.length;

  const adv = _stockData.filter(s => (s.change||0) > 0).length;

  const dec = _stockData.filter(s => (s.change||0) < 0).length;

  const flat = total - adv - dec;

  const vol = _stockData.reduce((sum, s) => sum + (s.volume||0), 0);

  document.getElementById('sov-count').textContent = total;

  document.getElementById('sov-advancers').textContent = adv;

  document.getElementById('sov-decliners').textContent = dec;

  document.getElementById('sov-unchanged').textContent = flat;

  document.getElementById('sov-volume').textContent = vol >= 1000000 ? (vol/1000000).toFixed(1)+'M' : vol >= 1000 ? (vol/1000).toFixed(1)+'K' : vol;

}



// ── Buy Modal ──

function openBuyModal(symbol) {

  _buySymbol = symbol;

  const s = _stockData.find(x => x.symbol === symbol);

  if (!s) { toast('err', '❌ Không tìm thấy mã ' + symbol); return; }

  document.getElementById('bs-symbol').textContent = s.symbol;

  document.getElementById('bs-company').textContent = s.company || '';

  document.getElementById('bs-price').textContent = (s.price||0).toLocaleString();

  document.getElementById('bs-shares').value = 1;

  previewBuy();

  document.getElementById('modal-buy-stock').classList.add('open');

}



function closeBuyModal() {

  document.getElementById('modal-buy-stock').classList.remove('open');

  _buySymbol = null;

}



function previewBuy() {

  const s = _stockData.find(x => x.symbol === _buySymbol);

  if (!s) return;

  const shares = parseInt(document.getElementById('bs-shares').value) || 0;

  const total = shares * (s.price||0);

  document.getElementById('bs-total').textContent = total.toLocaleString();

  document.getElementById('bs-balance').textContent = (curBal || 0).toLocaleString();

  document.getElementById('bs-confirm-btn').disabled = (shares < 1 || total > (curBal || 0));

}



async function confirmBuy() {

  const shares = parseInt(document.getElementById('bs-shares').value) || 0;

  if (shares < 1) { toast('err', '❌ Số lượng không hợp lệ'); return; }

  try {

    const raw = JSON.parse(await B.buyStock(_buySymbol, shares));

    if (raw.ok) {

      toast('ok', `🟢 Mua thành công ${shares} cp ${_buySymbol}`);

      closeBuyModal();

      await refreshBalance();

      loadAllStockData();

    } else {

      toast('err', '❌ ' + (raw.error || 'Giao dịch thất bại'));

    }

  } catch (e) {

    toast('err', '❌ Lỗi: ' + e.message);

  }

}



// ── Sell Modal ──

function openSellModal(symbol) {

  _sellSymbol = symbol;

  // Ưu tiên tìm trong _stockData (market), fallback sang portfolio

  let s = _stockData.find(x => x.symbol === symbol);

  const h = _stockPortfolio.find(x => x.symbol === symbol);

  if (!s && h) {

    // Tạo object tạm từ portfolio data nếu market chưa load

    s = {

      symbol:  h.symbol,

      company: h.company || h.company_name || '',

      price:   h.current_price || 0,

      change:  h.change || 0,

    };

  }

  if (!s) { toast('err', '❌ Không tìm thấy mã ' + symbol); return; }

  document.getElementById('ss-symbol').textContent = s.symbol;

  document.getElementById('ss-company').textContent = s.company || '';

  document.getElementById('ss-price').textContent = (s.price||0).toLocaleString();



  const maxShares = h ? (h.shares||0) : 0;

  document.getElementById('ss-max-shares').textContent = maxShares;

  document.getElementById('ss-avgcost').textContent = h ? (h.avg_cost||0).toLocaleString() : '—';



  document.getElementById('ss-shares').value = Math.min(1, maxShares);

  previewSell();

  document.getElementById('modal-sell-stock').classList.add('open');

}



function closeSellModal() {

  document.getElementById('modal-sell-stock').classList.remove('open');

  _sellSymbol = null;

}



function previewSell() {

  let s = _stockData.find(x => x.symbol === _sellSymbol);

  const h = _stockPortfolio.find(x => x.symbol === _sellSymbol);

  // Fallback từ portfolio nếu market chưa load

  if (!s && h) {

    s = {

      symbol:  h.symbol,

      price:   h.current_price || 0,

    };

  }

  if (!s) return;

  const shares = parseInt(document.getElementById('ss-shares').value) || 0;

  const total = shares * (s.price||0);

  document.getElementById('ss-total').textContent = total.toLocaleString();

  const maxShares = h ? (h.shares||0) : 0;

  document.getElementById('ss-confirm-btn').disabled = (shares < 1 || shares > maxShares);

}



async function confirmSell() {

  const shares = parseInt(document.getElementById('ss-shares').value) || 0;

  if (shares < 1) { toast('err', '❌ Số lượng không hợp lệ'); return; }

  try {

    const raw = JSON.parse(await B.sellStock(_sellSymbol, shares));

    if (raw.ok) {

      toast('ok', `🔴 Bán thành công ${shares} cp ${_sellSymbol}`);

      closeSellModal();

      await refreshBalance();

      // Dùng combined API — đồng bộ hoàn toàn

      loadAllStockData();

    } else {

      toast('err', '❌ ' + (raw.error || 'Giao dịch thất bại'));

    }

  } catch (e) {

    toast('err', '❌ Lỗi: ' + e.message);

  }

}



// ── Stock Detail Modal ──

async function showStockDetail(symbol) {

  try {

    const raw = JSON.parse(await B.getStockHistory(symbol, 50));

    if (!raw.ok) { toast('err', '❌ ' + raw.error); return; }

    const history = raw.data || [];

    const s = _stockData.find(x => x.symbol === symbol);

    if (!s) return;



    document.getElementById('sd-symbol').textContent = symbol;

    document.getElementById('sd-company').textContent = s.company || '';

    document.getElementById('sd-price').textContent = (s.price||0).toLocaleString();

    const chgStr = (s.change >= 0 ? '+' : '') + (s.change||0).toFixed(2);

    document.getElementById('sd-change').textContent = chgStr;

    document.getElementById('sd-change').style.color = s.change >= 0 ? 'var(--green)' : 'var(--red)';

    document.getElementById('sd-sector').textContent = s.sector || '—';



    // Mini sparkline

    const chartEl = document.getElementById('sd-chart');

    if (history.length > 1) {

      const prices = history.map(h => h.price || 0);

      const maxP = Math.max(...prices);

      const minP = Math.min(...prices);

      const range = maxP - minP || 1;

      chartEl.innerHTML = prices.map((p, idx) => {

        const hgt = ((p - minP) / range * 100);

        const isUp = idx === 0 || p >= prices[idx - 1];

        const barColor = isUp ? 'var(--green)' : 'var(--red)';

        return `<div style="flex:1;height:100%;display:flex;align-items:flex-end;justify-content:center">

          <div style="width:60%;background:${barColor};border-radius:2px 2px 0 0;height:${hgt}%;min-height:2px"></div>

        </div>`;

      }).join('');

    } else {

      chartEl.innerHTML = '<div style="text-align:center;width:100%;color:var(--muted2);padding:30px">Chưa có dữ liệu lịch sử</div>';

    }



    document.getElementById('modal-stock-detail').classList.add('open');

  } catch (e) {

    toast('err', '❌ Lỗi tải chi tiết');

  }

}



function closeStockDetail() {

  document.getElementById('modal-stock-detail').classList.remove('open');

}



// ════════════════════════════════════════════

//  CREDIT BANKING FUNCTIONS

// ════════════════════════════════════════════



// ── State ──

let _cbSelectedCardProduct = null;

let _cbSelectedLoanProduct = null;

let _cbSelectedRepayMethod = null;

let _cbSelectedInsurance = null;

let _cbPayCardId = null;

let _cbUseCardId = null;



// ── Init ──

async function loadCreditBanking() {

  try {

    const raw = JSON.parse(await B.getBankingAllData());

    if (raw.ok === false) return;

    const d = raw.data || raw;



    renderCreditScore(d.credit_score);

    renderMyCards(d.credit_cards || []);

    renderMyLoans(d.loans || []);

    renderCollateralSummary(d.collateral || {});

    renderMyCollaterals((d.collateral && d.collateral.collaterals) || []);

    renderIncomeStatus(d.income || {});

    renderLoyalty(d.loyalty || {});

    renderAnkiBacked(d.ankibacked || {});

  } catch(e) {

    // Silent fail - banking not ready

  }

}



// ── Tab Switching ──

function switchCbTab(tab) {

  document.querySelectorAll('.cb-tab').forEach(t => t.classList.remove('active'));

  document.querySelectorAll('.cb-panel').forEach(p => p.classList.remove('active'));

  const tabs = ['cards', 'loans', 'collateral', 'income', 'loyalty'];

  const idx = tabs.indexOf(tab);

  if (idx >= 0) {

    document.querySelectorAll('.cb-tab')[idx]?.classList.add('active');

  }

  document.getElementById('cbp-' + tab)?.classList.add('active');

}



// ── Credit Score ──

function renderCreditScore(cs) {

  if (!cs) return;

  const score = cs.score || 0;

  const rating = cs.rating || 'N/A';

  const colorClass = score >= 740 ? 'cb-score-excellent' : score >= 670 ? 'cb-score-good' : score >= 580 ? 'cb-score-fair' : 'cb-score-poor';

  const el = document.getElementById('cb-score-display');

  if (el) {

    el.textContent = score;

    el.className = 'cb-score-big ' + colorClass;

  }

  const lbl = document.getElementById('cb-score-label');

  if (lbl) lbl.textContent = `Xếp hạng: ${rating} · Tối đa 850`;

  const bar = document.getElementById('cb-score-bar');

  if (bar) bar.style.width = Math.min(100, (score / 850) * 100) + '%';

}



// ── My Credit Cards ──

function renderMyCards(cards) {

  const el = document.getElementById('cb-my-cards');

  if (!el) return;

  if (!cards || !cards.length) {

    el.innerHTML = '<div class="empty"><div class="ei">💳</div><p>Chưa có thẻ tín dụng nào. Nhấn "Mở thẻ mới" để đăng ký!</p></div>';

    return;

  }

  el.innerHTML = cards.map(c => {

    const tier = (c.product_code || 'cc_standard').replace('cc_', '');

    const limit = c.approved_limit || c.credit_limit || 0;

    const used = c.used_credit || c.outstanding || 0;

    const avail = c.available_credit != null ? c.available_credit : (limit - used);

    const utilPct = c.utilization_pct != null ? c.utilization_pct.toFixed(1) : (limit > 0 ? ((used / limit) * 100).toFixed(1) : 0);

    const annualFee = c.annual_fee_amount || c.annual_fee || 0;

    const ratePct = c.interest_rate_pct || c.interest_rate_monthly_pct || ((c.interest_rate || 0) * 100);

    const daysOverdue = c.days_overdue || 0;

    const daysUntil = c.days_until_payment || 0;

    const dueStr = daysOverdue > 0 ? `🔴 Quá hạn ${daysOverdue} ngày` : (daysUntil > 0 ? `${daysUntil} ngày nữa` : '—');

    const overdueStyle = daysOverdue > 0 ? 'border-color:var(--red);' : '';

    return `<div class="cc-card ${tier}" style="${overdueStyle}">

      <div class="cc-top">

        <div>

          <div class="cc-name">${c.emoji || '💳'} ${c.product_label || tier.toUpperCase()}</div>

          <div class="cc-limit">Hạn mức: ${fmt(limit)}</div>

        </div>

        <div style="text-align:right">

          <div class="cc-limit-used">${fmt(used)}</div>

          <div style="font-size:11px;color:var(--muted2)">đã dùng (${utilPct}%)</div>

        </div>

      </div>

      <div class="progress-wrap" style="margin:6px 0 8px"><div class="progress-bar" style="width:${Math.min(100, utilPct)}%;background:${utilPct > 80 ? 'var(--red)' : utilPct > 60 ? 'var(--yellow)' : 'var(--green)'}"></div></div>

      <div class="cc-detail">

        <div class="cc-detail-item"><span style="color:var(--muted2)">Còn lại</span><br/><strong style="color:var(--green)">${fmt(avail)}</strong></div>

        <div class="cc-detail-item"><span style="color:var(--muted2)">LS/tháng</span><br/><strong>${ratePct.toFixed(1)}%</strong></div>

        <div class="cc-detail-item"><span style="color:var(--muted2)">Phí năm</span><br/><strong>${fmt(annualFee)}</strong></div>

        <div class="cc-detail-item"><span style="color:var(--muted2)">Hạn TT</span><br/><strong style="color:${daysOverdue > 0 ? 'var(--red)' : 'var(--text)'}">${dueStr}</strong></div>

      </div>

      ${c.rewards_points ? `<div style="margin-top:6px;font-size:11px;color:var(--accent2)">⭐ ${c.rewards_points} điểm thưởng</div>` : ''}

      <div class="cc-actions">

        <button class="btn btn-primary" style="font-size:11px;padding:5px 12px" onclick="showUseCardModal('${c.id}')">💳 Thanh toán</button>

        <button class="btn btn-green" style="font-size:11px;padding:5px 12px" onclick="showPayCardModal('${c.id}')">💵 Trả nợ</button>

        <button class="btn btn-ghost" style="font-size:11px;padding:5px 12px" onclick="showCardStatement('${c.id}')">📋 Sao kê</button>

      </div>

    </div>`;

  }).join('');

}



// ── Apply Card Modal ──

async function showApplyCardModal() {

  _cbSelectedCardProduct = null;

  document.getElementById('btn-confirm-apply-card').disabled = true;

  document.getElementById('cb-card-preview').style.display = 'none';



  try {

    const raw = JSON.parse(await B.getCreditCardProducts());

    if (!raw.ok) { toast('err', '❌ ' + (raw.error || 'Lỗi tải sản phẩm')); return; }

    const products = raw.products || raw.data || [];

    const grid = document.getElementById('cb-card-products');

    grid.innerHTML = products.map(p => {

      const sel = _cbSelectedCardProduct?.code === p.code;

      return `<div class="loan-product-card ${sel ? 'selected' : ''}" onclick="selectCardProduct('${p.code}')">

        <div class="lp-name">${p.label || p.name || p.code}</div>

        <div class="lp-rate">${(p.interest_rate*100).toFixed(1)}%/th</div>

        <div style="font-size:10px;color:var(--muted2)">Hạn mức: ${fmt(p.max_credit || p.credit_limit || 0)}</div>

        <div style="font-size:10px;color:var(--muted2)">Phí năm: ${fmt(p.annual_fee)}</div>

      </div>`;

    }).join('');

  } catch(e) { toast('err', '❌ Lỗi tải sản phẩm thẻ'); }



  document.getElementById('modal-apply-card').classList.add('open');

}



function selectCardProduct(code) {

  const raw = document.getElementById('cb-card-products');

  const cards = raw.querySelectorAll('.loan-product-card');

  cards.forEach(c => c.classList.remove('selected'));

  const target = Array.from(cards).find(c => c.onclick && c.onclick.toString().includes(code));

  const allBtns = raw.querySelectorAll('.loan-product-card');

  allBtns.forEach(b => {

    if (b.textContent.includes(code) || b.outerHTML.includes(code)) b.classList.add('selected');

  });



  // Get product data from API call result

  document.getElementById('btn-confirm-apply-card').disabled = false;

  _cbSelectedCardProduct = { code: code };

  document.getElementById('cb-card-preview').style.display = 'block';

  document.getElementById('cb-card-preview').innerHTML = `✅ Đã chọn thẻ <strong>${code.toUpperCase()}</strong>. Nhấn "Đăng ký" để mở thẻ.`;

}



function closeApplyCardModal() {

  document.getElementById('modal-apply-card').classList.remove('open');

  _cbSelectedCardProduct = null;

}



async function confirmApplyCard() {

  if (!_cbSelectedCardProduct) { toast('err', '❌ Chọn sản phẩm thẻ trước!'); return; }

  try {

    const raw = JSON.parse(await B.applyCreditCard(_cbSelectedCardProduct.code));

    if (raw.ok) {

      toast('ok', `💳 Mở thẻ ${_cbSelectedCardProduct.code.toUpperCase()} thành công!`);

      closeApplyCardModal();

      await loadCreditBanking();

      await refreshBalance();

    } else {

      toast('err', '❌ ' + (raw.error || 'Không thể mở thẻ'));

    }

  } catch(e) { toast('err', '❌ Lỗi: ' + e.message); }

}



// ── Pay Card Modal ──

function showPayCardModal(cardId) {

  _cbPayCardId = cardId;

  document.getElementById('cb-pay-card-info').innerHTML = `💳 Thanh toán dư nợ thẻ <strong>#${cardId}</strong>`;

  document.getElementById('cb-pay-amount').value = '';

  document.getElementById('modal-pay-card').classList.add('open');

}



function closePayCardModal() {

  document.getElementById('modal-pay-card').classList.remove('open');

  _cbPayCardId = null;

}



async function confirmPayCard() {

  const amount = parseInt(document.getElementById('cb-pay-amount').value) || 0;

  if (amount <= 0) { toast('err', '❌ Nhập số tiền hợp lệ!'); return; }

  try {

    const raw = JSON.parse(await B.payCreditCard(_cbPayCardId, amount));

    if (raw.ok) {

      toast('ok', `💵 Đã thanh toán ${fmt(amount)} cho thẻ!`);

      closePayCardModal();

      await loadCreditBanking();

      await refreshBalance();

    } else {

      toast('err', '❌ ' + (raw.error || 'Thanh toán thất bại'));

    }

  } catch(e) { toast('err', '❌ Lỗi: ' + e.message); }

}



// ── Use Card Modal ──

function showUseCardModal(cardId) {

  _cbUseCardId = cardId;

  document.getElementById('cb-use-card-info').innerHTML = `💳 Thanh toán bằng thẻ <strong>#${cardId}</strong>`;

  document.getElementById('cb-use-amount').value = '';

  document.getElementById('cb-use-merchant').value = '';

  document.getElementById('modal-use-card').classList.add('open');

}



function closeUseCardModal() {

  document.getElementById('modal-use-card').classList.remove('open');

  _cbUseCardId = null;

}



async function confirmUseCard() {

  const amount = parseInt(document.getElementById('cb-use-amount').value) || 0;

  const merchant = document.getElementById('cb-use-merchant').value || 'Unknown';

  const category = document.getElementById('cb-use-category').value || 'other';

  if (amount <= 0) { toast('err', '❌ Nhập số tiền hợp lệ!'); return; }

  try {

    const raw = JSON.parse(await B.useCreditCard(_cbUseCardId, amount, merchant, category));

    if (raw.ok) {

      toast('ok', `💳 Đã thanh toán ${fmt(amount)} bằng thẻ!`);

      closeUseCardModal();

      await loadCreditBanking();

      await refreshBalance();

    } else {

      toast('err', '❌ ' + (raw.error || 'Giao dịch thất bại'));

    }

  } catch(e) { toast('err', '❌ Lỗi: ' + e.message); }

}



// ── Card Statement ──

async function showCardStatement(cardId) {

  try {

    const raw = JSON.parse(await B.getCreditCardStatement(cardId));

    if (!raw.ok) { toast('err', '❌ ' + raw.error); return; }

    const txns = raw.transactions || [];

    const cardInfo = raw.card || {};

    const outstanding = cardInfo.used_credit || raw.outstanding || 0;

    const creditLimit = cardInfo.approved_limit || raw.credit_limit || 0;

    let html = `<div style="background:var(--surface2);border-radius:10px;padding:14px;margin-bottom:10px">

      <div class="row-sb"><span style="font-weight:700">Dư nợ</span><span style="color:var(--yellow);font-weight:800">${fmt(outstanding)}</span></div>

      <div class="row-sb" style="margin-top:4px"><span style="color:var(--muted2)">Hạn mức</span><span>${fmt(creditLimit)}</span></div>

      <div class="row-sb" style="margin-top:4px"><span style="color:var(--muted2)">Còn lại</span><span style="color:var(--green)">${fmt(creditLimit - outstanding)}</span></div>

      ${raw.rewards_points ? `<div class="row-sb" style="margin-top:4px"><span style="color:var(--muted2)">Điểm thưởng</span><span style="color:var(--accent2)">${raw.rewards_points} pts</span></div>` : ''}

    </div>`;

    if (txns.length) {

      html += '<div style="font-size:12px;font-weight:700;margin-bottom:6px">📜 Lịch sử giao dịch</div>';

      html += txns.map(t => {

        const isPayment = t.type === 'payment';

        return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border);font-size:12px">

          <span>${isPayment ? '💵' : '💳'}</span>

          <div style="flex:1;min-width:0">

            <div style="font-weight:600">${t.merchant || t.description || '—'}</div>

            <div style="font-size:10px;color:var(--muted)">${t.date || ''} · ${t.category || ''}</div>

          </div>

          <span style="font-weight:800;color:${isPayment ? 'var(--green)' : 'var(--red)'}">${isPayment ? '-' : '+'}${fmt(t.amount||0)}</span>

        </div>`;

      }).join('');

    } else {

      html += '<div style="text-align:center;padding:12px;color:var(--muted2);font-size:12px">Chưa có giao dịch nào</div>';

    }

    showModal('📋 Sao kê thẻ tín dụng', html);

  } catch(e) { toast('err', '❌ Lỗi tải sao kê'); }

}



// ── Loans ──

function renderMyLoans(loans) {

  const el = document.getElementById('cb-my-loans');

  if (!el) return;

  if (!loans || !loans.length) {

    el.innerHTML = '<div class="empty"><div class="ei">🏦</div><p>Chưa có khoản vay nào. Nhấn "Vay mới" để đăng ký!</p></div>';

    return;

  }

  const methodLabels = { equal_installment: 'Trả đều', principal_first: 'Giảm dần', bullet: 'Trả cuối kỳ', interest_only: 'Lãi hàng tháng' };

  el.innerHTML = loans.map(l => {

    const remaining = l.remaining_principal || l.balance || 0;

    const principal = l.original_principal || l.principal || 0;

    const overdue = l.is_overdue || l.days_overdue > 0;

    const paidPct = l.progress_pct != null ? l.progress_pct : (principal > 0 ? ((1 - remaining/principal)*100) : 0);

    const ratePct = l.monthly_rate_pct || ((l.interest_rate || 0) * 100);

    return `<div class="loan-card ${overdue ? 'overdue' : ''}">

      <div class="lc-head">

        <div>

          <div class="lc-product">${l.product_label || l.product_name || 'Khoản vay'} ${l.ankibacked ? '📚' : ''}</div>

          <div style="font-size:11px;color:var(--muted2)">${methodLabels[l.repayment_method] || l.repayment_method || '—'} · ${l.tenure_months||0} tháng</div>

        </div>

        <div style="text-align:right">

          <div class="lc-balance" style="color:${overdue ? 'var(--red)' : 'var(--yellow)'}">${fmt(remaining)}</div>

          <div style="font-size:10px;color:var(--muted2)">còn nợ</div>

        </div>

      </div>

      <div class="lc-terms">

        <span>Gốc: ${fmt(principal)}</span>

        <span>LS: ${ratePct.toFixed(2)}%/th</span>

        <span>Đã trả: ${l.paid_installments||0}/${l.tenure_months||0} kỳ</span>

        <span>${overdue ? `🔴 Quá hạn ${l.days_overdue||0} ngày` : '🟢 Trong hạn'}</span>

      </div>

      <div class="lc-progress"><div class="lc-progress-bar" style="width:${Math.min(100, paidPct)}%"></div></div>

      <div style="display:flex;gap:6px;margin-top:8px">

        <button class="btn btn-green" style="font-size:11px;padding:4px 10px" onclick="repayLoan('${l.id}')">💰 Trả nợ</button>

        <button class="btn btn-ghost" style="font-size:11px;padding:4px 10px" onclick="showLoanDetail('${l.id}')">📋 Chi tiết</button>

      </div>

    </div>`;

  }).join('');

}



async function repayLoan(loanId) {

  const amtStr = prompt('Nhập số tiền muốn trả (VND):');

  if (!amtStr) return;

  const amount = parseInt(amtStr) || 0;

  if (amount <= 0) { toast('err', '❌ Số tiền không hợp lệ!'); return; }

  const extra = confirm('Trả thêm vào gốc (prepay)? OK = trả gốc thêm, Cancel = trả kỳ hạn bình thường');

  try {

    const raw = JSON.parse(await B.repayLoan(loanId, amount, extra));

    if (raw.ok) {

      toast('ok', `💰 Đã trả ${fmt(amount)} cho khoản vay!`);

      await loadCreditBanking();

      await refreshBalance();

    } else {

      toast('err', '❌ ' + (raw.error || 'Trả nợ thất bại'));

    }

  } catch(e) { toast('err', '❌ Lỗi: ' + e.message); }

}



async function showLoanDetail(loanId) {

  try {

    const raw = JSON.parse(await B.getMyLoans());

    if (!raw.ok) return;

    const loans = raw.loans || raw.data || [];

    const l = loans.find(x => x.id === loanId);

    if (!l) { toast('err', '❌ Không tìm thấy khoản vay'); return; }

    const remaining = l.remaining_principal || l.balance || 0;

    const principal = l.original_principal || l.principal || 0;

    const ratePct = l.monthly_rate_pct || ((l.interest_rate || 0) * 100);

    let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px">

      <div style="background:var(--surface2);padding:8px;border-radius:6px"><span style="color:var(--muted2)">Sản phẩm</span><br/><strong>${l.product_label||l.product_name||'—'}</strong></div>

      <div style="background:var(--surface2);padding:8px;border-radius:6px"><span style="color:var(--muted2)">Gốc vay</span><br/><strong>${fmt(principal)}</strong></div>

      <div style="background:var(--surface2);padding:8px;border-radius:6px"><span style="color:var(--muted2)">Còn nợ</span><br/><strong style="color:var(--yellow)">${fmt(remaining)}</strong></div>

      <div style="background:var(--surface2);padding:8px;border-radius:6px"><span style="color:var(--muted2)">LS/tháng</span><br/><strong>${ratePct.toFixed(2)}%</strong></div>

      <div style="background:var(--surface2);padding:8px;border-radius:6px"><span style="color:var(--muted2)">Kỳ hạn</span><br/><strong>${l.tenure_months||0} tháng</strong></div>

      <div style="background:var(--surface2);padding:8px;border-radius:6px"><span style="color:var(--muted2)">Đã trả</span><br/><strong>${l.paid_installments||0}/${l.tenure_months||0} kỳ</strong></div>

      <div style="background:var(--surface2);padding:8px;border-radius:6px"><span style="color:var(--muted2)">Đã trả (VND)</span><br/><strong style="color:var(--green)">${fmt(l.total_paid||0)}</strong></div>

      <div style="background:var(--surface2);padding:8px;border-radius:6px"><span style="color:var(--muted2)">Phân loại nợ</span><br/><strong>${(l.debt_classification?.label)||l.debt_classification_label||'N1 - Đủ tiêu chuẩn'}</strong></div>

    </div>`;

    if (l.is_overdue) {

      html += `<div style="margin-top:8px;background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);border-radius:8px;padding:8px;font-size:12px;color:var(--red)">⚠️ Quá hạn ${l.days_overdue||0} ngày · Lãi phạt: ${fmt(l.penalty_interest||0)}</div>`;

    }

    if (l.ankibacked) {

      html += `<div style="margin-top:8px;font-size:12px;color:var(--accent2)">📚 Khoản vay AnkiBacked™ — ưu đãi lãi suất từ thành tích học Anki</div>`;

    }

    showModal('📋 Chi tiết khoản vay', html);

  } catch(e) { toast('err', '❌ Lỗi tải chi tiết'); }

}



// ── Apply Loan Modal ──

async function showApplyLoanModal() {

  _cbSelectedLoanProduct = null;

  _cbSelectedRepayMethod = null;

  _cbSelectedInsurance = null;

  document.getElementById('cb-loan-form').style.display = 'none';



  try {

    const raw = JSON.parse(await B.getLoanProducts());

    if (!raw.ok) { toast('err', '❌ ' + (raw.error || 'Lỗi tải sản phẩm vay')); return; }

    const products = raw.products || raw.data || [];

    const grid = document.getElementById('cb-loan-products');

    grid.innerHTML = products.map(p => {

      const fixedRate = p.interest_rate_fixed ?? p.fixed_rate;

      const floatRate = p.interest_rate_floating ?? p.floating_rate;

      const rateStr = fixedRate != null ? `${(fixedRate*100).toFixed(1)}%` : floatRate != null ? `${(floatRate*100).toFixed(1)}% (thả nổi)` : '—';

      const rankLabel = p.rank_requirement?.required_id || p.min_rank || '';

      return `<div class="loan-product-card" onclick="selectLoanProduct('${p.code}')">

        <div class="lp-name">${p.label || p.name || p.code}</div>

        <div class="lp-rate">${rateStr}</div>

        <div class="lp-rank">${rankLabel ? `Rank: ${rankLabel}` : ''}</div>

      </div>`;

    }).join('');

  } catch(e) { toast('err', '❌ Lỗi tải sản phẩm vay'); }



  document.getElementById('modal-apply-loan').classList.add('open');

}



async function selectLoanProduct(code) {

  _cbSelectedLoanProduct = code;

  document.querySelectorAll('#cb-loan-products .loan-product-card').forEach(c => c.classList.remove('selected'));

  document.querySelectorAll('#cb-loan-products .loan-product-card').forEach(c => {

    if (c.outerHTML.includes(code) || c.textContent.includes(code.replace('_', ' '))) c.classList.add('selected');

  });

  document.getElementById('cb-loan-form').style.display = 'block';

  document.getElementById('cb-loan-amount').value = '';



  // Load repayment methods

  try {

    const raw = JSON.parse(await B.getRepaymentMethods());

    if (raw.ok) {

      const methods = raw.methods || raw.data || [];

      const container = document.getElementById('cb-repay-methods');

      _cbSelectedRepayMethod = null;

      container.innerHTML = methods.map(m => `<div class="repay-method-card" onclick="selectRepayMethod('${m.id}')">

        <div class="rm-name">${m.label || m.name || m.id}</div>

        <div class="rm-desc">${m.desc || m.description || ''}</div>

      </div>`).join('');

    }

  } catch(e) {}



  // Load insurance plans

  try {

    const raw = JSON.parse(await B.getLoanInsurancePlans());

    if (raw.ok) {

      const plans = raw.plans || raw.data || [];

      const container = document.getElementById('cb-insurance-plans');

      _cbSelectedInsurance = null;

      container.innerHTML = plans.map(p => `<div class="insurance-plan-card" onclick="selectInsurancePlan('${p.id}')">

        <div class="ip-name">${p.label || p.name || p.id}</div>

        <div class="ip-fee">${((p.premium_rate ?? p.fee_rate ?? 0)*100).toFixed(1)}%</div>

        <div class="ip-detail">${p.description || ''}</div>

      </div>`).join('');

    }

  } catch(e) {}



  updateLoanPreview();

}



function selectRepayMethod(id) {

  _cbSelectedRepayMethod = id;

  document.querySelectorAll('#cb-repay-methods .repay-method-card').forEach(c => c.classList.remove('selected'));

  document.querySelectorAll('#cb-repay-methods .repay-method-card').forEach(c => {

    if (c.outerHTML.includes(id) || c.textContent.includes(id)) c.classList.add('selected');

  });

  updateLoanPreview();

}



function selectInsurancePlan(id) {

  _cbSelectedInsurance = id;

  document.querySelectorAll('#cb-insurance-plans .insurance-plan-card').forEach(c => c.classList.remove('selected'));

  document.querySelectorAll('#cb-insurance-plans .insurance-plan-card').forEach(c => {

    if (c.outerHTML.includes(id) || c.textContent.includes(id)) c.classList.add('selected');

  });

}



function updateLoanPreview() {

  const principal = parseInt(document.getElementById('cb-loan-amount').value) || 0;

  const tenure = parseInt(document.getElementById('cb-loan-tenure').value) || 12;

  const el = document.getElementById('cb-loan-preview');

  if (principal <= 0 || !_cbSelectedLoanProduct) {

    el.style.display = 'none';

    return;

  }

  // Quick preview using calc API

  const annualRate = 0.12; // default fallback

  B.calcLoanInstallment(principal, annualRate, tenure, _cbSelectedRepayMethod || 'equal_installment', false)

    .then(raw => {

      const res = JSON.parse(raw);

      if (res.ok) {

        el.style.display = 'block';

        const d = res.data || res;

        el.innerHTML = `<div class="row-sb"><span style="color:var(--muted2)">Trả hàng tháng</span><span style="font-weight:800;color:var(--yellow)">${fmt(d.monthly_payment||0)}</span></div>

          <div class="row-sb" style="margin-top:4px"><span style="color:var(--muted2)">Tổng lãi</span><span style="font-weight:700">${fmt(d.total_interest||0)}</span></div>

          <div class="row-sb" style="margin-top:4px"><span style="color:var(--muted2)">Tổng trả</span><span style="font-weight:800;color:var(--green);font-size:15px">${fmt(d.total_payment||0)}</span></div>`;

      } else {

        el.innerHTML = '<div style="color:var(--muted2)">Không thể tính toán</div>';

      }

    })

    .catch(() => { el.style.display = 'none'; });

}



function closeApplyLoanModal() {

  document.getElementById('modal-apply-loan').classList.remove('open');

  _cbSelectedLoanProduct = null;

}



async function confirmApplyLoan() {

  if (!_cbSelectedLoanProduct) { toast('err', '❌ Chọn sản phẩm vay trước!'); return; }

  const amount = parseInt(document.getElementById('cb-loan-amount').value) || 0;

  const tenure = parseInt(document.getElementById('cb-loan-tenure').value) || 12;

  if (amount <= 0) { toast('err', '❌ Nhập số tiền vay hợp lệ!'); return; }

  try {

    const raw = JSON.parse(await B.applyForLoan(_cbSelectedLoanProduct, amount, tenure, _cbSelectedRepayMethod || 'equal_installment', _cbSelectedInsurance ? true : false));

    if (raw.ok) {

      toast('ok', `🏦 Vay ${fmt(amount)} thành công!${raw.disbursed ? ` Giải ngân: ${fmt(raw.disbursed)}` : ''}`);

      closeApplyLoanModal();

      await loadCreditBanking();

      await refreshBalance();

    } else {

      toast('err', '❌ ' + (raw.error || 'Vay thất bại'));

    }

  } catch(e) { toast('err', '❌ Lỗi: ' + e.message); }

}



// ── Collateral ──

function renderCollateralSummary(summary) {

  const el1 = document.getElementById('cb-col-total');

  const el2 = document.getElementById('cb-col-ltv-total');

  const el3 = document.getElementById('cb-col-count');

  if (el1) el1.textContent = fmt(summary.total_valuation || summary.total_value || 0);

  if (el2) el2.textContent = fmt(summary.total_max_loan || summary.max_loan_value || 0);

  if (el3) el3.textContent = summary.count || 0;

}



function renderMyCollaterals(collaterals) {

  const el = document.getElementById('cb-my-collaterals');

  if (!el) return;

  if (!collaterals || !collaterals.length) {

    el.innerHTML = '<div class="empty"><div class="ei">🔒</div><p>Chưa có tài sản thế chấp nào.</p></div>';

    return;

  }

  el.innerHTML = collaterals.map(c => {

    const icon = c.emoji || '🔒';

    const name = c.label || c.name || c.type || 'Tài sản';

    const val = c.valuation || c.value || 0;

    const maxLoan = c.max_loan || Math.round(val * (c.ltv_ratio || 0));

    const ltvPct = c.ltv_pct != null ? c.ltv_pct : ((c.ltv_ratio || 0) * 100);

    return `<div class="collateral-card">

      <div class="col-type">${icon} ${name}</div>

      <div class="col-value">Giá trị: ${fmt(val)} · LTV: ${ltvPct.toFixed(0)}%</div>

      <div class="col-ltv">Giá trị vay tối đa: <strong style="color:var(--yellow)">${fmt(maxLoan)}</strong></div>

      <div style="margin-top:6px;display:flex;gap:6px">

        <button class="btn btn-ghost" style="font-size:10px;padding:3px 8px" onclick="removeCollateral('${c.id}')">🗑️ Xoá</button>

      </div>

    </div>`;

  }).join('');

}



async function removeCollateral(collateralId) {

  if (!confirm('Xoá tài sản thế chấp này?')) return;

  try {

    const raw = JSON.parse(await B.removeCollateral(collateralId));

    if (raw.ok) {

      toast('ok', '🔒 Đã xoá tài sản thế chấp!');

      await loadCreditBanking();

    } else {

      toast('err', '❌ ' + (raw.error || 'Xoá thất bại'));

    }

  } catch(e) { toast('err', '❌ Lỗi: ' + e.message); }

}



// ── Register Collateral Modal ──

function showRegisterCollateralModal() {

  document.getElementById('cb-col-asset-id').value = '';

  document.getElementById('cb-col-value').value = '';

  document.getElementById('cb-col-preview').style.display = 'none';

  document.getElementById('modal-register-collateral').classList.add('open');

}



function closeRegisterCollateralModal() {

  document.getElementById('modal-register-collateral').classList.remove('open');

}



function updateCollateralPreview() {

  const type = document.getElementById('cb-col-type').value;

  const value = parseInt(document.getElementById('cb-col-value').value) || 0;

  const ltvRates = { real_estate: 0.7, vehicle: 0.6, savings: 0.9, stock: 0.5, digital_asset: 0.3 };

  const ltv = ltvRates[type] || 0.5;

  const el = document.getElementById('cb-col-preview');

  if (value <= 0) { el.style.display = 'none'; return; }

  el.style.display = 'block';

  el.innerHTML = `Giá trị: <strong>${fmt(value)}</strong> · Tỷ lệ LTV: <strong>${(ltv*100).toFixed(0)}%</strong> · Giá trị vay tối đa: <strong style="color:var(--yellow)">${fmt(Math.round(value*ltv))}</strong>`;

}



async function confirmRegisterCollateral() {

  const type = document.getElementById('cb-col-type').value;

  const assetId = document.getElementById('cb-col-asset-id').value.trim();

  const value = parseInt(document.getElementById('cb-col-value').value) || 0;

  if (!assetId) { toast('err', '❌ Nhập ID/mô tả tài sản!'); return; }

  if (value <= 0) { toast('err', '❌ Nhập giá trị tài sản!'); return; }

  try {

    const raw = JSON.parse(await B.registerCollateral(type, assetId, value, 'VND'));

    if (raw.ok) {

      toast('ok', '🔒 Đăng ký thế chấp thành công!');

      closeRegisterCollateralModal();

      await loadCreditBanking();

    } else {

      toast('err', '❌ ' + (raw.error || 'Đăng ký thất bại'));

    }

  } catch(e) { toast('err', '❌ Lỗi: ' + e.message); }

}



// ── Income ──

function renderIncomeStatus(status) {

  if (!status) return;

  const amount = status.verified_income || status.monthly_income || 0;

  const verified = status.verified || false;

  const methods = status.methods || status.breakdown || {};

  const methodCount = Object.keys(methods).length;

  const el = document.getElementById('cb-income-amount');

  if (el) el.textContent = fmt(amount) + ' VND/tháng';

  const statusEl = document.getElementById('cb-income-status');

  if (statusEl) {

    statusEl.textContent = verified

      ? `✅ Đã xác thực qua ${methodCount} phương thức · Cấp độ ${status.level || 0}`

      : '❌ Chưa xác thực — Nhấn nút bên dưới để xác thực ngay';

    statusEl.style.color = verified ? 'var(--green)' : 'var(--muted2)';

  }

  const breakdown = document.getElementById('cb-income-breakdown');

  if (breakdown && methodCount > 0) {

    const methodNames = { study_based: '📚 Dựa trên học tập', asset_based: '🏦 Dựa trên tài sản', streak_based: '🔥 Dựa trên streak', rank_based: '🏆 Dựa trên rank' };

    breakdown.innerHTML = Object.entries(methods).map(([key, info]) => {

      const name = methodNames[key] || key;

      const est = typeof info === 'object' ? (info.estimated_income || 0) : info;

      return `<div class="income-method">

        <div class="row-sb"><span>${name}</span><span style="font-weight:700;color:var(--green)">${fmt(est)}/tháng</span></div>

        ${typeof info === 'object' && info.label ? `<div style="font-size:10px;color:var(--muted2);margin-top:2px">${info.label}</div>` : ''}

      </div>`;

    }).join('');

  } else if (breakdown) {

    breakdown.innerHTML = '<div style="color:var(--muted2);font-size:12px">Chưa có dữ liệu phân tích thu nhập. Nhấn "Xác thực thu nhập" để cập nhật.</div>';

  }

}



async function doVerifyIncome() {

  try {

    const raw = JSON.parse(await B.verifyIncome());

    if (raw.ok) {

      const income = raw.verified_income || 0;

      toast('ok', `✅ Xác thực thu nhập thành công: ${fmt(income)} VND/tháng!`);

      await loadCreditBanking();

    } else {

      toast('err', '❌ ' + (raw.error || 'Xác thực thất bại'));

    }

  } catch(e) { toast('err', '❌ Lỗi: ' + e.message); }

}



// ── Loyalty ──

function renderLoyalty(loyalty) {

  const el = document.getElementById('cb-loyalty-status');

  if (!el) return;

  if (!loyalty || !loyalty.tier) {

    el.innerHTML = '<div class="empty"><div class="ei">⭐</div><p>Chưa có thông tin khách hàng thân thiết</p></div>';

    return;

  }

  const tier = (loyalty.tier || 'new').toLowerCase();

  const tierLabels = { new: 'Mới', bronze: 'Đồng', silver: 'Bạc', gold: 'Vàng', platinum: 'Bạch Kim', diamond: 'Kim Cương' };

  const tierClass = `loyalty-${tier}`;

  el.innerHTML = `<div class="card" style="text-align:center;padding:18px">

    <div style="font-size:40px;margin-bottom:6px">${getTierEmoji(tier)}</div>

    <div class="loyalty-badge ${tierClass}" style="font-size:16px;padding:6px 18px">${tierLabels[tier] || tier}</div>

    <div style="margin-top:10px;font-size:13px;color:var(--muted2)">${loyalty.benefits || loyalty.description || ''}</div>

    <div style="margin-top:8px;display:grid;grid-template-columns:repeat(3,1fr);gap:8px">

      <div class="bank-ov-card"><div class="bov-val" style="color:var(--accent2)">${loyalty.points||0}</div><div class="bov-lbl">Điểm</div></div>

      <div class="bank-ov-card"><div class="bov-val" style="color:var(--yellow)">${loyalty.discount||0}%</div><div class="bov-lbl">Giảm giá</div></div>

      <div class="bank-ov-card"><div class="bov-val" style="color:var(--green)">${loyalty.cashback||0}%</div><div class="bov-lbl">Cashback</div></div>

    </div>

  </div>`;



  // Next tier info

  if (loyalty.next_tier) {

    el.innerHTML += `<div style="text-align:center;margin-top:8px;font-size:12px;color:var(--muted2)">

      🎯 Tier tiếp theo: <strong>${tierLabels[loyalty.next_tier] || loyalty.next_tier}</strong>

      (cần ${loyalty.points_needed||0} điểm nữa)

    </div>`;

  }

}



function getTierEmoji(tier) {

  const map = { new: '🌱', bronze: '🥉', silver: '🥈', gold: '🥇', platinum: '💎', diamond: '👑' };

  return map[tier] || '⭐';

}



function renderAnkiBacked(ab) {

  const el = document.getElementById('cb-ankibacked');

  if (!el) return;

  if (!ab || !ab.active) {

    el.innerHTML = '';

    return;

  }

  el.innerHTML = `<div class="ankibacked-banner">

    <div class="ab-title">📚 AnkiBacked™</div>

    <div class="ab-sub">Vay ưu đãi dựa trên thành tích học tập Anki của bạn</div>

    <div class="ab-stat">

      <div class="ab-stat-item"><div class="ab-stat-val">${ab.study_streak||0} ngày</div><div class="ab-stat-lbl">Streak học</div></div>

      <div class="ab-stat-item"><div class="ab-stat-val">${(ab.rate_discount||0)*100}%</div><div class="ab-stat-lbl">Giảm lãi</div></div>

      <div class="ab-stat-item"><div class="ab-stat-val">${fmt(ab.max_loan||0)}</div><div class="ab-stat-lbl">Hạn mức</div></div>

    </div>

  </div>`;

}



// ── Utility ──

function showModal(title, bodyHtml) {

  // Use a simple modal approach

  const overlay = document.createElement('div');

  overlay.className = 'modal-overlay open';

  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:600;display:flex;align-items:center;justify-content:center';

  overlay.innerHTML = `<div class="modal" style="max-width:500px;max-height:80vh;overflow-y:auto">

    <div class="row-sb" style="margin-bottom:14px">

      <h3>${title}</h3>

      <button class="btn btn-ghost" style="font-size:12px;padding:4px 10px" onclick="this.closest('.modal-overlay').remove()">✕</button>

    </div>

    ${bodyHtml}

  </div>`;

  document.body.appendChild(overlay);

  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });

}



// ════════════════════════════════════════════

//  LEDGER ANTI-CHEAT (Req 4)



