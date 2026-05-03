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



