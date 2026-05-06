// ════════════════════════════════════════════
//  INVENTORY — Unified (Items, Vehicles, Tech)
// ════════════════════════════════════════════

// ── Global state ──
let _invAllData = null;              // raw data from getCategorizedInventory()
let _invAllItems = [];               // regular items (filtered)
let _invAllVehicles = [];            // vehicles
let _invAllTech = [];                // tech items
let _invActiveVehicle = null;        // active vehicle info
let _invActiveTech = null;           // active tech info
let _invSlotsInfo = null;            // { used, total }

// ── Inventory countdown state (v1.1.5) ────
let _invCountdownData = [];
let _invCountdownTimer = null;

function _startInventoryCountdown() {
  _stopInventoryCountdown();
  const tick = () => {
    const now = Date.now();
    _invCountdownData = _invCountdownData.filter(d => {
      const el = document.getElementById(d.elId);
      if (!el) return false;
      const remaining = Math.max(0, (d.expiresAtMs - now) / 1000);
      const remH = remaining / 3600;
      const pct = d.maxH > 0 ? Math.min(100, (remH / d.maxH) * 100) : 0;
      const col = pct > 50 ? 'var(--green)' : pct > 20 ? 'var(--yellow)' : 'var(--red)';
      const wholeRemaining = Math.floor(remaining);
      if (wholeRemaining !== d._lastDisplayed) {
        d._lastDisplayed = wholeRemaining;
        if (remaining <= 0) {
          el.innerHTML = `<span style="color:var(--red)">0.0h còn lại</span>`;
          return false;
        }
        const labelEl = el.querySelector('.inv-fresh-label');
        if (labelEl) labelEl.textContent = `${remH.toFixed(1)}h còn lại`;
        const barEl = el.querySelector('.inv-fresh-bar');
        if (barEl) barEl.style.width = `${pct}%`;
        if (barEl) barEl.style.background = col;
      }
      return remaining > 0;
    });
    if (_invCountdownData.length > 0) {
      _invCountdownTimer = requestAnimationFrame(tick);
    } else {
      _invCountdownTimer = null;
    }
  };
  _invCountdownTimer = requestAnimationFrame(tick);
}

function _stopInventoryCountdown() {
  if (_invCountdownTimer) {
    cancelAnimationFrame(_invCountdownTimer);
    _invCountdownTimer = null;
  }
}

// ── Sub-tab switching ──
function switchInvTab(tab) {
  // Update tab buttons
  document.querySelectorAll('.inv-tab').forEach(btn => btn.classList.remove('active'));
  const tabBtn = document.getElementById('itab-' + tab);
  if (tabBtn) tabBtn.classList.add('active');

  // Show/hide panels
  document.getElementById('inv-tab-items').style.display    = tab === 'items' ? 'block' : 'none';
  document.getElementById('inv-tab-vehicles').style.display = tab === 'vehicles' ? 'block' : 'none';
  document.getElementById('inv-tab-tech').style.display     = tab === 'tech' ? 'block' : 'none';

  // Refresh boost strip (có active boosts ở items tab)
  if (tab === 'items' && typeof refreshBoostStrip === 'function') {
    refreshBoostStrip();
  }
}

// ── Main loader ──
async function loadInventory() {
  // Check spoiled food first
  try {
    const spoiledRaw = await B.checkSpoiledFood();
    const spoiled = JSON.parse(spoiledRaw);
    if (spoiled.length > 0) {
      toast('err', `🍂 ${spoiled.length} mặt hàng đồ ăn đã thiu và bị xoá khỏi kho!`);
    }
  } catch (_) {}

  try {
    const raw = await B.getCategorizedInventory();
    const data = JSON.parse(raw);

    _invAllData = data;
    _invAllItems = data.regular_items || [];
    _invAllVehicles = data.garage || [];
    _invAllTech = data.tech_lab || [];
    _invActiveVehicle = data.active_vehicle || null;
    _invActiveTech = data.active_tech || null;
    _invSlotsInfo = data.slots_info || { used: 0, total: 50 };

    // Update badge
    const totalItems = _invAllItems.reduce((a, i) => a + (i.quantity || 1), 0);
    document.getElementById('inv-badge').textContent =
      `${_invAllItems.length} loại • ${totalItems} mặt hàng`;

    const slotInfo = _invSlotsInfo;
    document.getElementById('inv-slot-badge').textContent =
      `📦 ${slotInfo.used || 0}/${slotInfo.total || 50} slot`;

    // Load active boosts
    if (typeof refreshBoostStrip === 'function') {
      await refreshBoostStrip();
    }

    // Render current tab
    const activeTab = document.querySelector('.inv-tab.active');
    const tab = activeTab ? activeTab.id.replace('itab-', '') : 'items';

    _invCountdownData = [];
    _stopInventoryCountdown();

    if (tab === 'items') {
      renderInvGrid();
    } else if (tab === 'vehicles') {
      renderInvVehicleGrid(_invAllVehicles);
    } else if (tab === 'tech') {
      renderInvTechGrid(_invAllTech);
    }

  } catch (err) {
    console.error('[Inventory] loadInventory error:', err);
    toast('err', '❌ Lỗi tải inventory: ' + (err.message || err));
  }
}

// ════════════════════════════════════════════
//  TAB 1: VẬT PHẨM (Regular Items)
// ════════════════════════════════════════════

function applyInvFilter() {
  const typeVal   = document.getElementById('inv-filter-type').value;
  const statusVal = document.getElementById('inv-filter-status').value;
  const priceMin  = parseFloat(document.getElementById('inv-filter-price-min').value) || 0;
  const priceMax  = parseFloat(document.getElementById('inv-filter-price-max').value) || 0;
  const sortVal   = document.getElementById('inv-filter-sort').value;

  let filtered = _invAllItems;

  // Filter by type
  if (typeVal) {
    filtered = filtered.filter(i => (i.item_type || '') === typeVal);
  }

  // Filter by status (freshness / active)
  if (statusVal) {
    const now = Date.now();
    filtered = filtered.filter(i => {
      const slots = i.food_slots || [];
      const firstSlot = slots[0] || null;
      const remH = firstSlot ? firstSlot.remaining_h || 0 : 0;
      const isFood = i.is_food || i.is_study;
      const isFinance = (i.category || '').includes('Vật phẩm tài chính');

      switch (statusVal) {
        case 'fresh':
          return isFood && remH > 12;
        case 'expiring':
          return isFood && remH > 0 && remH <= 12;
        case 'expired':
          return isFood && remH <= 0;
        case 'active':
          return isFinance || (i.is_boost_active);
        default:
          return true;
      }
    });
  }

  // Filter by price range
  if (priceMin > 0) filtered = filtered.filter(i => (i.price || 0) >= priceMin);
  if (priceMax > 0) filtered = filtered.filter(i => (i.price || 0) <= priceMax);

  // Sort
  if (sortVal) {
    switch (sortVal) {
      case 'price_asc':  filtered.sort((a,b) => (a.price||0) - (b.price||0)); break;
      case 'price_desc': filtered.sort((a,b) => (b.price||0) - (a.price||0)); break;
      case 'name_asc':   filtered.sort((a,b) => (a.name||'').localeCompare(b.name||'')); break;
      case 'name_desc':  filtered.sort((a,b) => (b.name||'').localeCompare(a.name||'')); break;
      case 'qty_asc':    filtered.sort((a,b) => (a.quantity||1) - (b.quantity||1)); break;
      case 'qty_desc':   filtered.sort((a,b) => (b.quantity||1) - (a.quantity||1)); break;
    }
  }

  // Update count
  document.getElementById('inv-filter-count').textContent =
    `Hiển thị ${filtered.length} / ${_invAllItems.length} vật phẩm`;

  renderInvGrid(filtered);
}

function resetInvFilter() {
  document.getElementById('inv-filter-type').value = '';
  document.getElementById('inv-filter-status').value = '';
  document.getElementById('inv-filter-price-min').value = '';
  document.getElementById('inv-filter-price-max').value = '';
  document.getElementById('inv-filter-sort').value = '';
  applyInvFilter();
}

function renderInvGrid(items) {
  const g = document.getElementById('inv-grid');
  const list = items !== undefined ? items : _invAllItems;

  if (!list.length) {
    const isFiltered = items !== undefined;
    g.innerHTML = `<div class="empty" style="grid-column:1/-1">
      <div class="ei">🔍</div>
      <p>${isFiltered ? 'Không tìm thấy vật phẩm phù hợp với bộ lọc.' : 'Kho trống — ghé <a href="#" onclick="go(\'shop\');return false" style="color:var(--accent2)">cửa hàng</a> nhé!'}</p>
    </div>`;
    _stopInventoryCountdown();
    return;
  }

  _invCountdownData = [];
  _stopInventoryCountdown();

  g.innerHTML = list.map(i => {
    const isFood    = i.is_food;
    const isStudy   = i.is_study;
    const isFinance = (i.category || '').includes('Vật phẩm tài chính');
    const eff       = i.effect || {};
    const activeSlot = i.active_slot || '';
    const slots      = i.food_slots || [];
    const firstSlot  = slots[0] || null;

    let foodExtra = '';

    if (isFood) {
      let freshBar = '';
      const freshId = i.id + '_' + (firstSlot?.slot_id || '0');
      if (firstSlot) {
        const pct   = firstSlot.fresh_pct || 0;
        const remH  = firstSlot.remaining_h || 0;
        const col   = pct > 50 ? 'var(--green)' : pct > 20 ? 'var(--yellow)' : 'var(--red)';
        const expiresAtMs = Date.now() + (remH * 3600 * 1000);
        const maxH = i.expire_h || remH || 24;
        _invCountdownData.push({
          id: i.id, slotId: firstSlot?.slot_id || '',
          elId: 'inv-fresh-' + freshId,
          expiresAtMs, maxH, _lastDisplayed: -1,
        });
        freshBar = `
          <div style="width:100%;margin-top:4px" id="inv-fresh-${freshId}">
            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">
              <span>Độ tươi</span><span class="inv-fresh-label" style="color:${col}">${remH.toFixed(1)}h còn lại</span>
            </div>
            <div class="fresh-wrap" style="width:100%">
              <div class="inv-fresh-bar" style="height:100%;width:${pct}%;background:${col};border-radius:2px;transition:width .3s"></div>
            </div>
          </div>`;
      }
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
      const freshId = i.id + '_' + (firstSlot?.slot_id || '0');
      if (firstSlot) {
        const pct   = firstSlot.fresh_pct || 0;
        const remH  = firstSlot.remaining_h || 0;
        const col   = pct > 50 ? 'var(--green)' : pct > 20 ? 'var(--yellow)' : 'var(--red)';
        const expiresAtMs = Date.now() + (remH * 3600 * 1000);
        const maxH = i.expire_h || remH || 24;
        _invCountdownData.push({
          id: i.id, slotId: firstSlot?.slot_id || '',
          elId: 'inv-fresh-' + freshId,
          expiresAtMs, maxH, _lastDisplayed: -1,
        });
        freshBar = `
          <div style="width:100%;margin-top:4px" id="inv-fresh-${freshId}">
            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">
              <span>Hạn sử dụng</span><span class="inv-fresh-label" style="color:${col}">${remH.toFixed(1)}h còn lại</span>
            </div>
            <div class="fresh-wrap" style="width:100%">
              <div class="inv-fresh-bar" style="height:100%;width:${pct}%;background:${col};border-radius:2px;transition:width .3s"></div>
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

    let financeExtra = '';
    if (isFinance) {
      const knCost = i.kn_cost || 0;
      const knRefund = Math.round(knCost * 0.5);
      financeExtra = `
        <div style="margin-top:4px;font-size:11px;color:var(--accent2);display:flex;align-items:center;gap:4px">
          <span style="background:rgba(16,185,129,.15);color:var(--green);border:1px solid rgba(16,185,129,.3);border-radius:4px;padding:1px 6px;font-size:10px">⚡ Đang hoạt động</span>
          <span style="color:var(--muted2)">· Thụ động</span>
        </div>
        <div style="font-size:10px;color:var(--accent2);margin-top:3px;text-align:center">🧠 Đã mua bằng ${knCost.toLocaleString('vi-VN')} KN</div>
        <button class="btn btn-ghost" style="font-size:10px;padding:3px 10px;margin-top:6px;width:100%;color:var(--red)"
          onclick="sellFinanceItemFromInv('${i.id}','${(i.name||'').replace(/'/g,"\\'")}',${knRefund})">
          🗑️ Bán bỏ (hoàn ${knRefund.toLocaleString('vi-VN')} KN)
        </button>`;
    }

    return `
    <div class="inv-card ${isFood ? 'food-card' : ''}${isFinance ? ' finance-card' : ''}">
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
      ${financeExtra}
    </div>`;
  }).join('');

  _startInventoryCountdown();
}

// ════════════════════════════════════════════
//  TAB 2: XE CỘ (Vehicles)
// ════════════════════════════════════════════

function applyInvVehicleFilter() {
  const groupVal  = (document.getElementById('inv-vehicle-filter-group').value || '').toLowerCase().trim();
  const statusVal = document.getElementById('inv-vehicle-filter-status').value;
  const durVal    = document.getElementById('inv-vehicle-filter-durability').value;
  const fuelVal   = document.getElementById('inv-vehicle-filter-fuel').value;
  const priceMin  = parseFloat(document.getElementById('inv-vehicle-filter-price-min').value) || 0;
  const priceMax  = parseFloat(document.getElementById('inv-vehicle-filter-price-max').value) || 0;
  const starsVal  = document.getElementById('inv-vehicle-filter-stars').value;
  const sortVal   = document.getElementById('inv-vehicle-filter-sort').value;

  let filtered = _invAllVehicles;

  // Filter by vehicle group
  if (groupVal) {
    filtered = filtered.filter(v => (v.vehicle_group || '').toLowerCase().trim() === groupVal);
  }

  // Filter by status
  if (statusVal) {
    filtered = filtered.filter(v => {
      switch (statusVal) {
        case 'active':     return v.is_active;
        case 'idle':       return !v.is_active && !v.in_repair && !v.breakdown_repair && !v.maintenance_due && (v.durability || 0) > 0 && ((v.fuel_type === 'manual') || (v.fuel_level || 0) > 0);
        case 'repair':     return v.in_repair;
        case 'breakdown':  return v.breakdown_repair;
        case 'maint_due':  return v.maintenance_due;
        case 'no_fuel':    return v.fuel_type !== 'manual' && (v.fuel_level || 0) <= 0 && !v.is_charging;
        case 'broken':     return (v.durability || 0) <= 0;
        default:           return true;
      }
    });
  }

  // Filter by durability
  if (durVal) {
    filtered = filtered.filter(v => {
      const pct = v.durability_pct || 0;
      switch (durVal) {
        case 'critical': return pct <= 20;
        case 'low':      return pct > 20 && pct <= 50;
        case 'medium':   return pct > 50 && pct <= 80;
        case 'high':     return pct > 80;
        default:         return true;
      }
    });
  }

  // Filter by fuel type
  if (fuelVal) {
    filtered = filtered.filter(v => (v.fuel_type || 'gasoline') === fuelVal);
  }

  // Price range
  if (priceMin > 0) filtered = filtered.filter(v => (v.price || 0) >= priceMin);
  if (priceMax > 0) filtered = filtered.filter(v => (v.price || 0) <= priceMax);

  // Stars
  if (starsVal) {
    const minStars = parseInt(starsVal);
    filtered = filtered.filter(v => (v.stars || 0) >= minStars);
  }

  // Sort
  if (sortVal) {
    switch (sortVal) {
      case 'price_asc':  filtered.sort((a,b) => (a.price||0) - (b.price||0)); break;
      case 'price_desc': filtered.sort((a,b) => (b.price||0) - (a.price||0)); break;
      case 'dup_asc':    filtered.sort((a,b) => (a.durability_pct||0) - (b.durability_pct||0)); break;
      case 'dup_desc':   filtered.sort((a,b) => (b.durability_pct||0) - (a.durability_pct||0)); break;
      case 'fuel_asc':   filtered.sort((a,b) => (a.fuel_pct||0) - (b.fuel_pct||0)); break;
      case 'fuel_desc':  filtered.sort((a,b) => (b.fuel_pct||0) - (a.fuel_pct||0)); break;
      case 'km_asc':     filtered.sort((a,b) => (a.km_traveled||0) - (b.km_traveled||0)); break;
      case 'km_desc':    filtered.sort((a,b) => (b.km_traveled||0) - (a.km_traveled||0)); break;
      case 'name_asc':   filtered.sort((a,b) => (a.name||'').localeCompare(b.name||'')); break;
      case 'name_desc':  filtered.sort((a,b) => (b.name||'').localeCompare(a.name||'')); break;
    }
  }

  // Update count
  document.getElementById('inv-vehicle-filter-count').textContent =
    `Hiển thị ${filtered.length} / ${_invAllVehicles.length} xe`;

  renderInvVehicleGrid(filtered);
}

function resetInvVehicleFilter() {
  document.getElementById('inv-vehicle-filter-group').value = '';
  document.getElementById('inv-vehicle-filter-status').value = '';
  document.getElementById('inv-vehicle-filter-durability').value = '';
  document.getElementById('inv-vehicle-filter-fuel').value = '';
  document.getElementById('inv-vehicle-filter-price-min').value = '';
  document.getElementById('inv-vehicle-filter-price-max').value = '';
  document.getElementById('inv-vehicle-filter-stars').value = '';
  document.getElementById('inv-vehicle-filter-sort').value = '';
  applyInvVehicleFilter();
}

function toggleInvVehicleAdvFilter() {
  const adv = document.getElementById('inv-vehicle-adv-filters');
  const btn = document.getElementById('inv-vehicle-adv-toggle');
  if (!adv) return;
  const isHidden = adv.style.display === 'none' || adv.style.display === '';
  adv.style.display = isHidden ? 'flex' : 'none';
  if (btn) btn.textContent = isHidden ? '✕ Ẩn nâng cao' : '⚙️ Nâng cao';
}

function loadInvVehicleActiveBanner() {
  const active = _invActiveVehicle;
  const banner = document.getElementById('inv-garage-active-banner');
  if (!banner) return;

  // Garage slots info
  const slotText = document.getElementById('inv-garage-slot-text');
  if (slotText) {
    const total = _invSlotsInfo?.garage_slots || _invSlotsInfo?.total || 1;
    slotText.textContent = `${_invAllVehicles.length} / ${total} slot`;
  }

  if (active) {
    banner.style.display = 'block';

    const emojiEl = document.getElementById('inv-gab-emoji');
    if (emojiEl) emojiEl.textContent = active.emoji || '🚗';
    const nameEl = document.getElementById('inv-gab-name');
    if (nameEl) nameEl.textContent = active.name || '';

    // Durability bar
    const dupPct = active.durability_pct || 0;
    const dupCol = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';
    const gabDup = document.getElementById('inv-gab-dup');
    if (gabDup) gabDup.textContent = `${active.durability || 0}/${active.max_durability || 0}`;
    const dupBar = document.getElementById('inv-gab-dup-bar');
    if (dupBar) { dupBar.style.width = dupPct + '%'; dupBar.style.background = dupCol; }

    // Fuel section
    const fuelSection = document.getElementById('inv-gab-fuel-section');
    const manualLabel = document.getElementById('inv-gab-manual-label');
    const fuelWarning = document.getElementById('inv-gab-fuel-warning');
    const fuelActions = document.getElementById('inv-gab-fuel-actions');

    if (active.fuel_type && active.fuel_type !== 'manual') {
      if (fuelSection) fuelSection.style.display = 'block';
      if (manualLabel) manualLabel.style.display = 'none';

      const unit = active.fuel_type === 'electric' ? 'kWh' : 'L';
      const fuelLabel = active.fuel_type === 'electric' ? '🔋 Pin' : '⛽ Xăng';
      const gabFuelLabel = document.getElementById('inv-gab-fuel-label');
      if (gabFuelLabel) gabFuelLabel.textContent = fuelLabel;

      const fuelPct = active.fuel_pct || 0;
      const fuelCol = fuelPct > 50 ? 'var(--green)' : fuelPct > 20 ? 'var(--yellow)' : 'var(--red)';
      const gabFuel = document.getElementById('inv-gab-fuel');
      if (gabFuel) gabFuel.textContent = `${active.fuel_level || 0}/${active.max_fuel || 0} ${unit}`;
      const fuelBar = document.getElementById('inv-gab-fuel-bar');
      if (fuelBar) { fuelBar.style.width = fuelPct + '%'; fuelBar.style.background = fuelCol; }

      const vehicleId = active.item_id;
      const isElectric = active.fuel_type === 'electric';

      if (fuelPct <= 10) {
        if (fuelWarning) { fuelWarning.style.display = 'block'; fuelWarning.textContent = '🪫 ' + (isElectric ? 'Pin sắp hết! Hãy sạc ngay.' : 'Xăng sắp hết! Hãy đổ xăng ngay.'); fuelWarning.style.color = 'var(--red)'; }
      } else if (fuelPct <= 30) {
        if (fuelWarning) { fuelWarning.style.display = 'block'; fuelWarning.textContent = '⚠️ Nhiên liệu sắp hết (' + fuelPct + '%)'; fuelWarning.style.color = 'var(--yellow)'; }
      } else {
        if (fuelWarning) fuelWarning.style.display = 'none';
      }

      let actionsHtml = '';
      if (fuelPct < 100) {
        if (isElectric) {
          if (active.is_charging) {
            const cm = Math.max(0, Math.floor((active.charge_remaining || 0) / 60));
            actionsHtml = `<span style="font-size:10px;color:var(--accent2);padding:3px 6px">⚡ Đang sạc (~${cm}p)</span>`;
          } else {
            actionsHtml = `<button class="btn btn-ghost" style="font-size:10px;padding:3px 8px" onclick="rechargeVehicle('${vehicleId}')">🔌 Sạc điện ngay</button>`;
          }
        } else {
          actionsHtml = `<button class="btn btn-ghost" style="font-size:10px;padding:3px 8px" onclick="refuelVehicle('${vehicleId}')">⛽ Đổ xăng ngay</button>`;
        }
      } else {
        actionsHtml = '<span style="font-size:10px;color:var(--green)">✅ Đầy nhiên liệu</span>';
      }
      if (fuelActions) { fuelActions.innerHTML = actionsHtml; fuelActions.style.display = 'flex'; }
    } else {
      if (fuelSection) fuelSection.style.display = 'none';
      if (manualLabel) manualLabel.style.display = 'block';
    }

    // KM section
    const kmSection = document.getElementById('inv-gab-km-section');
    const km = active.km_traveled || 0;
    const totalCards = active.total_cards_driven || 0;
    const gabKm = document.getElementById('inv-gab-km');
    if (gabKm) gabKm.textContent = km.toFixed(1) + ' km';
    const gabCards = document.getElementById('inv-gab-cards-driven');
    if (gabCards) gabCards.textContent = totalCards.toLocaleString();
    if (kmSection) kmSection.style.display = 'block';

    // Energy save section
    const esSection = document.getElementById('inv-gab-energy-save-section');
    const esPct = active.energy_save_percent || 0;
    if (esPct > 0) {
      const gabEs = document.getElementById('inv-gab-energy-save');
      if (gabEs) gabEs.textContent = (esPct * 100).toFixed(1) + '%';
      if (esSection) esSection.style.display = 'block';
    } else {
      if (esSection) esSection.style.display = 'none';
    }

  } else {
    banner.style.display = 'none';
  }
}

function renderInvVehicleGrid(vehicles) {
  const grid = document.getElementById('inv-vehicle-grid');
  const list = vehicles !== undefined ? vehicles : _invAllVehicles;

  // Update active banner & slot info
  loadInvVehicleActiveBanner();

  if (!list.length) {
    grid.innerHTML = '<div class="empty"><div class="ei">🔍</div><p>Không tìm thấy xe nào phù hợp với bộ lọc.</p></div>';
    return;
  }

  grid.innerHTML = list.map(v => {
    const isActive      = v.is_active;
    const inRepair      = v.in_repair;
    const maintDue      = v.maintenance_due;
    const inBreakdown   = v.breakdown_repair;
    const fuelType      = v.fuel_type || 'gasoline';
    const isManual      = fuelType === 'manual';
    const isElectric    = fuelType === 'electric';
    const fuelUnit      = isElectric ? 'kWh' : 'L';
    const vg            = v.vehicle_group || 'Ô tô';

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

    // KM
    const kmVal = v.km_traveled || 0;
    const cardsVal = v.total_cards_driven || 0;
    const esVal = v.energy_save_percent || 0;
    let kmLine = '';
    if (kmVal > 0 || cardsVal > 0) {
      kmLine = `<div style="font-size:10px;color:var(--muted2);margin-top:2px">
        📍 ${kmVal.toFixed(1)} km &nbsp;•&nbsp; 📊 ${cardsVal.toLocaleString()} thẻ
      </div>`;
    }

    // Energy save
    let esLine = '';
    if (esVal > 0) {
      esLine = `<div style="font-size:10px;color:var(--green);margin-top:1px">
        ⚡ Tiết kiệm ${(esVal * 100).toFixed(1)}% năng lượng
      </div>`;
    }

    // Sell estimate
    const sellEst = v.sell_estimate || 0;
    const sellLine = sellEst > 0
      ? `<div style="font-size:10px;color:var(--muted2);margin-top:2px">💰 Giá bán ước tính: <span style="color:var(--yellow)">${fmt(sellEst)}</span></div>`
      : '';

    // Actions
    let actions = '';
    if (isActive) {
      actions = `<button class="btn btn-ghost" style="font-size:11px;padding:4px 8px;width:100%" onclick="stopCurrentVehicle();setTimeout(loadInventory,300)">🛑 Dừng xe</button>`;
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
      actions = `<button class="btn btn-yellow" style="font-size:11px;padding:4px 8px;width:100%" onclick="repairVehicle('${v.item_id}');setTimeout(loadInventory,300)">🔧 Sửa chữa</button>`;
    } else if (maintDue) {
      actions = `<div style="display:flex;gap:4px">
        <button class="btn btn-yellow" style="font-size:11px;padding:4px 8px;flex:1" onclick="maintainVehicle('${v.item_id}');setTimeout(loadInventory,300)">🔧 Bảo dưỡng</button>
        <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;color:var(--red)" onclick="sellVehicleFromGarage('${v.item_id}')">💰 Bán</button>
      </div>`;
    } else {
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

      const noFuel = !isManual && (v.fuel_level||0) <= 0;
      const driveBtn = noFuel
        ? `<button class="btn" style="font-size:11px;padding:4px 8px;flex:1;opacity:.4;cursor:not-allowed" disabled title="${isElectric?'Hết điện, cần sạc':'Hết xăng, cần đổ'}">${driveEmoji} Lái xe</button>`
        : `<button class="btn btn-green" style="font-size:11px;padding:4px 8px;flex:1" onclick="useVehicle('${v.item_id}');setTimeout(loadInventory,300)">${driveEmoji} Lái xe</button>`;

      const maxDup = v.max_durability || 100;
      const curDup = v.durability || 0;
      let maintBtn = '';
      if (curDup < maxDup) {
        maintBtn = `<button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;color:var(--yellow)" onclick="quickMaintenanceVehicle('${v.item_id}');setTimeout(loadInventory,300)">🔧 Bảo dưỡng</button>`;
      }

      actions = `<div style="display:flex;gap:4px;flex-wrap:wrap">${driveBtn}${fuelActions}${maintBtn}</div>
        <div style="display:flex;gap:4px;margin-top:4px">
          <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;flex:1" onclick="openGarageDetail('${v.item_id}')">📋 Chi tiết</button>
          <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;color:var(--red);flex:1" onclick="sellVehicleFromGarage('${v.item_id}')">💰 Bán xe</button>
        </div>`;
    }

    // Compare toggle
    const isCompareSelected = typeof _garageCompareList !== 'undefined' && _garageCompareList.indexOf(v.item_id) >= 0;
    const compareToggle = `<button class="btn btn-ghost" style="font-size:9px;padding:2px 6px;${isCompareSelected?'color:var(--accent2);border-color:var(--accent2)':''}" onclick="event.stopPropagation();toggleGarageCompare('${v.item_id}')" title="${isCompareSelected?'Bỏ chọn so sánh':'Thêm vào so sánh'}">${isCompareSelected?'✅':'☐'}</button>`;

    return `
      <div class="card" style="padding:12px;display:flex;flex-direction:column;gap:2px${isActive?';border:1px solid var(--green)':''}">
        <div style="display:flex;align-items:center;gap:6px">
          <div class="item-img-wrap" style="width:48px;height:48px;min-width:48px">
            ${v.image_url
              ? `<img class="item-img" style="width:48px;height:48px" src="${v.image_url}" alt="${v.name}">`
              : `<div style="font-size:24px">${v.emoji||driveEmoji}</div>`
            }
          </div>
          <div style="flex:1;min-width:0">
            <div style="font-size:13px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${v.name}</div>
            <div style="font-size:11px;color:var(--muted2)">${vg} &nbsp;•&nbsp; <span style="color:var(--yellow)">${fmt(v.price)}</span></div>
            <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:2px">${statusBadge}${compareToggle}</div>
          </div>
        </div>
        ${dupBar}
        ${fuelBar}
        ${kmLine}
        ${esLine}
        ${sellLine}
        <div style="margin-top:6px">${actions}</div>
      </div>`;
  }).join('');
}

// ════════════════════════════════════════════
//  TAB 3: CÔNG NGHỆ (Tech)
// ════════════════════════════════════════════

function applyInvTechFilter() {
  const statusVal = document.getElementById('inv-tech-filter-status').value;
  const durVal    = document.getElementById('inv-tech-filter-durability').value;
  const priceMin  = parseFloat(document.getElementById('inv-tech-filter-price-min').value) || 0;
  const priceMax  = parseFloat(document.getElementById('inv-tech-filter-price-max').value) || 0;
  const sortVal   = document.getElementById('inv-tech-filter-sort').value;

  let filtered = _invAllTech;

  // Filter by status
  if (statusVal) {
    filtered = filtered.filter(v => {
      switch (statusVal) {
        case 'active':    return v.is_active;
        case 'idle':      return !v.is_active && !v.in_repair && !v.maintenance_due && (v.durability || 0) > 0;
        case 'repair':    return v.in_repair;
        case 'maint_due': return v.maintenance_due;
        case 'broken':    return (v.durability || 0) <= 0;
        default:          return true;
      }
    });
  }

  // Filter by durability
  if (durVal) {
    filtered = filtered.filter(v => {
      const pct = v.durability_pct || 0;
      switch (durVal) {
        case 'critical': return pct <= 20;
        case 'low':      return pct > 20 && pct <= 50;
        case 'medium':   return pct > 50 && pct <= 80;
        case 'high':     return pct > 80;
        default:         return true;
      }
    });
  }

  // Price range
  if (priceMin > 0) filtered = filtered.filter(v => (v.price || 0) >= priceMin);
  if (priceMax > 0) filtered = filtered.filter(v => (v.price || 0) <= priceMax);

  // Sort
  if (sortVal) {
    switch (sortVal) {
      case 'price_asc':  filtered.sort((a,b) => (a.price||0) - (b.price||0)); break;
      case 'price_desc': filtered.sort((a,b) => (b.price||0) - (a.price||0)); break;
      case 'dup_asc':    filtered.sort((a,b) => (a.durability_pct||0) - (b.durability_pct||0)); break;
      case 'dup_desc':   filtered.sort((a,b) => (b.durability_pct||0) - (a.durability_pct||0)); break;
      case 'name_asc':   filtered.sort((a,b) => (a.name||'').localeCompare(b.name||'')); break;
      case 'name_desc':  filtered.sort((a,b) => (b.name||'').localeCompare(a.name||'')); break;
    }
  }

  // Update count
  document.getElementById('inv-tech-filter-count').textContent =
    `Hiển thị ${filtered.length} / ${_invAllTech.length} thiết bị`;

  renderInvTechGrid(filtered);
}

function resetInvTechFilter() {
  document.getElementById('inv-tech-filter-status').value = '';
  document.getElementById('inv-tech-filter-durability').value = '';
  document.getElementById('inv-tech-filter-price-min').value = '';
  document.getElementById('inv-tech-filter-price-max').value = '';
  document.getElementById('inv-tech-filter-sort').value = '';
  applyInvTechFilter();
}

function loadInvTechActiveBanner() {
  const active = _invActiveTech;
  const banner = document.getElementById('inv-tech-active-banner');
  if (!banner) return;

  if (active) {
    banner.style.display = 'block';
    const emojiEl = document.getElementById('inv-tlab-emoji');
    if (emojiEl) emojiEl.textContent = active.emoji || '💻';
    const nameEl = document.getElementById('inv-tlab-name');
    if (nameEl) nameEl.textContent = active.name || '';

    // Durability
    const dupPct = active.durability_pct || 0;
    const dupCol = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';
    const tlabDup = document.getElementById('inv-tlab-dup');
    if (tlabDup) tlabDup.textContent = `${active.durability || 0}/${active.max_durability || 0}`;
    const dupBar = document.getElementById('inv-tlab-dup-bar');
    if (dupBar) { dupBar.style.width = dupPct + '%'; dupBar.style.background = dupCol; }

    // Status text
    let statusText = '✅ Đang hoạt động';
    if (active.in_repair) {
      statusText = '🔧 Đang sửa chữa';
    } else if (active.maintenance_due) {
      statusText = '⚠️ Cần bảo dưỡng';
    } else if (active.durability <= 0) {
      statusText = '💔 Hết độ bền';
    }
    const statusEl = document.getElementById('inv-tlab-status');
    if (statusEl) statusEl.textContent = statusText;

  } else {
    banner.style.display = 'none';
  }
}

function renderInvTechGrid(items) {
  const grid = document.getElementById('inv-tech-grid');
  const list = items !== undefined ? items : _invAllTech;

  // Update active tech banner
  loadInvTechActiveBanner();

  if (!list.length) {
    grid.innerHTML = '<div class="empty"><div class="ei">💻</div><p>Bạn chưa có thiết bị công nghệ nào. Hãy mua ở cửa hàng!</p></div>';
    return;
  }

  grid.innerHTML = list.map(v => {
    const isActive      = v.is_active;
    const inRepair      = v.in_repair;
    const maintDue      = v.maintenance_due;
    const dupPct        = v.durability_pct || 0;
    const dupCol        = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';

    const sellEst = v.sell_estimate || 0;
    const sellLine = sellEst > 0
      ? `<div style="font-size:10px;color:var(--muted2);margin-top:2px">💰 Giá bán ước tính: <span style="color:var(--yellow)">${fmt(sellEst)}</span></div>`
      : '';

    // Status badge
    let statusBadge = '';
    if (isActive) {
      statusBadge = '<span style="font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(16,185,129,.15);color:var(--green);font-weight:600">✅ Đang dùng</span>';
    } else if (inRepair) {
      statusBadge = '<span style="font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(245,158,11,.15);color:var(--yellow);font-weight:600">🔧 Đang sửa</span>';
    } else if (maintDue) {
      statusBadge = '<span style="font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(239,68,68,.15);color:var(--red);font-weight:600">⚠️ Cần bảo dưỡng</span>';
    } else if (v.durability <= 0) {
      statusBadge = '<span style="font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(239,68,68,.15);color:var(--red);font-weight:600">💔 Hết độ bền</span>';
    } else {
      statusBadge = '<span style="font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(107,114,128,.15);color:var(--muted2);font-weight:600">💤 Không dùng</span>';
    }

    // Actions
    let actions = '';
    if (isActive) {
      actions = `<button class="btn btn-ghost" style="font-size:10px;padding:3px 8px;width:100%;color:var(--red)" onclick="deactivateCurrentTech();setTimeout(loadInventory,300)">🛑 Tắt</button>`;
    } else if (inRepair) {
      const remaining = Math.max(0, Math.floor((v.repair_until || 0) - Date.now()/1000));
      const rh = Math.floor(remaining/3600), rm = Math.floor((remaining%3600)/60);
      actions = `<span style="font-size:10px;color:var(--yellow)">🔧 Còn ${rh}h${rm}p</span>`;
    } else if (v.durability <= 0) {
      actions = `<button class="btn btn-yellow" style="font-size:11px;padding:4px 8px;width:100%" onclick="repairTechItem('${v.item_id}');setTimeout(loadInventory,300)">🔧 Sửa chữa</button>`;
    } else if (maintDue) {
      actions = `<div style="display:flex;gap:4px;flex-wrap:wrap">
        <button class="btn btn-yellow" style="font-size:10px;padding:3px 8px;flex:1" onclick="maintainTechItem('${v.item_id}');setTimeout(loadInventory,300)">🔧 Bảo dưỡng</button>
        <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;color:var(--red)" onclick="sellTechItem('${v.item_id}')">💰 Bán</button>
      </div>`;
    } else {
      actions = `<div style="display:flex;gap:4px;flex-wrap:wrap">
        <button class="btn btn-green" style="font-size:10px;padding:3px 8px;flex:1" onclick="activateTechItem('${v.item_id}');setTimeout(loadInventory,300)">▶️ Dùng</button>
        <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;color:var(--red)" onclick="sellTechItem('${v.item_id}')">💰 Bán</button>
      </div>`;
    }

    return `<div class="card" style="padding:12px;border-color:${isActive ? 'rgba(16,185,129,.4)' : 'var(--border)'}">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:22px">${v.emoji || '💻'}</span>
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${v.name || v.item_id}</div>
          <div style="font-size:10px;color:var(--muted2)">${fmt(v.price || 0)}</div>
        </div>
        ${statusBadge}
      </div>
      <div style="margin-bottom:6px">
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">
          <span>🔩 Độ bền</span>
          <span style="color:${dupCol};font-weight:600">${v.durability || 0} / ${v.max_durability || 0}</span>
        </div>
        <div class="fresh-wrap" style="width:100%;margin-top:2px">
          <div style="height:100%;width:${dupPct}%;background:${dupCol};border-radius:2px;transition:width .4s ease"></div>
        </div>
      </div>
      ${sellLine}
      <div style="margin-top:6px">${actions}</div>
    </div>`;
  }).join('');
}

// ════════════════════════════════════════════
//  ITEM ACTIONS (kept from original)
// ════════════════════════════════════════════

async function reloadImages() {
  await B.refreshImageCache();
  const dir = await B.getImagesDir();
  document.getElementById('img-dir-path').textContent = dir;
  document.getElementById('img-dir-hint').style.display = 'block';
  await loadShop();
  toast('info', '🖼️ Đã làm mới cache ảnh!');
}

async function sellFinanceItemFromInv(itemId, itemName, knRefund) {
  if (!confirm(`Bán "${itemName}"?\n\nBạn sẽ nhận lại ${knRefund.toLocaleString('vi-VN')} KN (50% KN đã bỏ ra).\nVật phẩm sẽ bị xoá khỏi kho.`)) return;
  const res = JSON.parse(await B.sellFinanceItem(itemId));
  if (res.ok) {
    toast('ok', `🧠 Đã bán "${res.item_name}" · Hoàn ${(res.kn_refund||0).toLocaleString('vi-VN')} KN`);
    await loadInventory();
  } else {
    toast('err', '❌ ' + (res.error || 'Không thể bán'));
  }
}

async function useFoodItem(itemId, slotId) {
  const res = JSON.parse(await B.activateFoodBoost(itemId, slotId));
  if (res.ok) {
    toast('ok', `⚡ ${res.message || 'Boost đã kích hoạt!'}`);
    await loadInventory();
    if (typeof refreshBoostStrip === 'function') await refreshBoostStrip();
  } else {
    toast('err', '❌ ' + (res.error || 'Lỗi kích hoạt boost'));
  }
}

async function useStudyItem(itemId, slotId) {
  const res = JSON.parse(await B.activateFoodBoost(itemId, slotId));
  if (res.ok) {
    toast('ok', `📖 ${res.message || 'Đã áp dụng vật phẩm học tập!'}`);
    await loadInventory();
    if (typeof refreshBoostStrip === 'function') await refreshBoostStrip();
  } else {
    toast('err', '❌ ' + (res.error || 'Lỗi kích hoạt vật phẩm học tập'));
  }
}
