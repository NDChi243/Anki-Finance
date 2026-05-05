// ════════════════════════════════════════════════════════════
//  GARAGE
// ════════════════════════════════════════════════════════════

let _garageAllVehicles = [];

async function loadGarage() {

  try {

    const raw = await B.getGarageData();
    const res = JSON.parse(raw);

    const garage = res.garage || [];

    const active = res.active_vehicle;

    const slots  = res.total_slots || 1;

    // Store full list for filtering
    _garageAllVehicles = garage;

    console.log('[Garage] loadGarage: vehicles=', garage.length, 'raw length=', raw.length);

    // ── Slot info ──

    const slotEl = document.getElementById('garage-slot-text');
    if (slotEl) {
      slotEl.textContent = `${garage.length} / ${slots} slot`;
    }

    // ── Active vehicle banner ──

    const banner = document.getElementById('garage-active-banner');

    if (active) {

      if (banner) banner.style.display = 'block';

      const emojiEl = document.getElementById('gab-emoji');
      if (emojiEl) emojiEl.textContent = active.emoji || '🚗';

      const nameEl = document.getElementById('gab-name');
      if (nameEl) nameEl.textContent = active.name || '';

      // Durability bar
      const dupPct = active.durability_pct || 0;
      const dupCol = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';
      const gabDup = document.getElementById('gab-dup');
      if (gabDup) gabDup.textContent = `${active.durability || 0}/${active.max_durability || 0}`;
      const dupBar = document.getElementById('gab-dup-bar');
      if (dupBar) { dupBar.style.width = dupPct + '%'; dupBar.style.background = dupCol; }

      // Fuel section
      const fuelSection = document.getElementById('gab-fuel-section');
      const manualLabel = document.getElementById('gab-manual-label');
      const fuelWarning = document.getElementById('gab-fuel-warning');
      const fuelActions = document.getElementById('gab-fuel-actions');

      if (active.fuel_type && active.fuel_type !== 'manual') {
        if (fuelSection) fuelSection.style.display = 'block';
        if (manualLabel) manualLabel.style.display = 'none';

        const unit = active.fuel_type === 'electric' ? 'kWh' : 'L';
        const fuelLabel = active.fuel_type === 'electric' ? '🔋 Pin' : '⛽ Xăng';
        const gabFuelLabel = document.getElementById('gab-fuel-label');
        if (gabFuelLabel) gabFuelLabel.textContent = fuelLabel;

        const fuelPct = active.fuel_pct || 0;
        const fuelCol = fuelPct > 50 ? 'var(--green)' : fuelPct > 20 ? 'var(--yellow)' : 'var(--red)';
        const gabFuel = document.getElementById('gab-fuel');
        if (gabFuel) gabFuel.textContent = `${active.fuel_level || 0}/${active.max_fuel || 0} ${unit}`;
        const fuelBar = document.getElementById('gab-fuel-bar');
        if (fuelBar) { fuelBar.style.width = fuelPct + '%'; fuelBar.style.background = fuelCol; }

        // Fuel warning & quick-refuel buttons
        const vehicleId = active.item_id;
        const isElectric = active.fuel_type === 'electric';

        if (fuelPct <= 10) {
          if (fuelWarning) { fuelWarning.style.display = 'block'; fuelWarning.textContent = '🪫 ' + (isElectric ? 'Pin sắp hết! Hãy sạc ngay.' : 'Xăng sắp hết! Hãy đổ xăng ngay.'); }
        } else if (fuelPct <= 30) {
          if (fuelWarning) { fuelWarning.style.display = 'block'; fuelWarning.textContent = '⚠️ Nhiên liệu sắp hết (' + fuelPct + '%)'; fuelWarning.style.color = 'var(--yellow)'; }
        } else {
          if (fuelWarning) fuelWarning.style.display = 'none';
        }

        // Quick refuel/recharge buttons on active banner
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

      // ── KM traveled (v1.1.5b) ──
      const kmSection = document.getElementById('gab-km-section');
      const km = active.km_traveled || 0;
      const totalCards = active.total_cards_driven || 0;
      const gabKm = document.getElementById('gab-km');
      if (gabKm) gabKm.textContent = km.toFixed(1) + ' km';
      const gabCards = document.getElementById('gab-cards-driven');
      if (gabCards) gabCards.textContent = totalCards.toLocaleString();
      if (kmSection) kmSection.style.display = 'flex';

      // ── Energy save (v1.1.5b) ──
      const esSection = document.getElementById('gab-energy-save-section');
      const esPct = active.energy_save_percent || 0;
      if (esPct > 0) {
        const gabEs = document.getElementById('gab-energy-save');
        if (gabEs) gabEs.textContent = (esPct * 100).toFixed(1) + '%';
        if (esSection) esSection.style.display = 'block';
      } else {
        if (esSection) esSection.style.display = 'none';
      }

    } else {

      if (banner) banner.style.display = 'none';

    }

    // ── Apply filters & render ──
    applyGarageFilter();

  } catch (err) {
    console.error('[Garage] loadGarage error:', err);
    if (typeof toast === 'function') {
      toast('err', 'Garage error: ' + (err.message || err));
    }
  }

}

function switchGarageTab(tab) {
  // Update tab buttons
  document.querySelectorAll('.garage-tab').forEach(btn => btn.classList.remove('active'));
  const tabBtn = tab === 'garage' ? document.getElementById('gtab-garage') : document.getElementById('gtab-maintenance');
  if (tabBtn) tabBtn.classList.add('active');

  // Show/hide panels
  document.getElementById('garage-tab-garage').style.display = tab === 'garage' ? 'block' : 'none';
  document.getElementById('garage-tab-maintenance').style.display = tab === 'maintenance' ? 'block' : 'none';

  // Load maintenance data when switching to that tab
  if (tab === 'maintenance') {
    loadMaintenanceTab();
  }
}

function applyGarageFilter() {
  const groupVal = (document.getElementById('garage-filter-group').value || '').toLowerCase().trim();
  const statusVal = document.getElementById('garage-filter-status').value;
  const durVal = document.getElementById('garage-filter-durability').value;
  const fuelVal = document.getElementById('garage-filter-fuel').value;
  const priceMin = parseFloat(document.getElementById('garage-filter-price-min').value);
  const priceMax = parseFloat(document.getElementById('garage-filter-price-max').value);
  const starsVal = document.getElementById('garage-filter-stars').value;
  const sortVal = document.getElementById('garage-filter-sort').value;

  let filtered = _garageAllVehicles;

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

  // Filter by durability range
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

  // ─── Advanced: Filter by price range ──────────────────────
  if (priceMin) {
    filtered = filtered.filter(v => (v.price || 0) >= priceMin);
  }
  if (priceMax) {
    filtered = filtered.filter(v => (v.price || 0) <= priceMax);
  }

  // ─── Advanced: Filter by minimum stars ────────────────────
  if (starsVal) {
    const minStars = parseInt(starsVal);
    filtered = filtered.filter(v => (v.stars || 0) >= minStars);
  }

  // ─── Advanced: Sort ──────────────────────────────────────
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
  document.getElementById('garage-filter-count').textContent =
    `Hiển thị ${filtered.length} / ${_garageAllVehicles.length} xe`;

  // Render filtered vehicles
  renderGarageGrid(filtered);
}

function resetGarageFilter() {
  document.getElementById('garage-filter-group').value = '';
  document.getElementById('garage-filter-status').value = '';
  document.getElementById('garage-filter-durability').value = '';
  document.getElementById('garage-filter-fuel').value = '';
  document.getElementById('garage-filter-price-min').value = '';
  document.getElementById('garage-filter-price-max').value = '';
  document.getElementById('garage-filter-stars').value = '';
  document.getElementById('garage-filter-sort').value = '';
  applyGarageFilter();
}

function renderGarageGrid(vehicles) {
  const grid = document.getElementById('garage-grid');

  if (!vehicles.length) {
    grid.innerHTML = '<div class="empty"><div class="ei">🔍</div><p>Không tìm thấy xe nào phù hợp với bộ lọc.</p></div>';
    return;
  }

  grid.innerHTML = vehicles.map(v => {

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

    // KM traveled (v1.1.5b)
    const kmVal = v.km_traveled || 0;
    const cardsVal = v.total_cards_driven || 0;
    const esVal = v.energy_save_percent || 0;
    let kmLine = '';
    if (kmVal > 0 || cardsVal > 0) {
      kmLine = `<div style="font-size:10px;color:var(--muted2);margin-top:2px">
        📍 ${kmVal.toFixed(1)} km &nbsp;•&nbsp; 📊 ${cardsVal.toLocaleString()} thẻ
      </div>`;
    }

    // Energy save line (v1.1.5b)
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

    // ── Action buttons ──
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

      // Nút bảo dưỡng chủ động khi độ bền < max_durability
      const maxDup = v.max_durability || 100;
      const curDup = v.durability || 0;
      let maintBtn = '';
      if (curDup < maxDup) {
        maintBtn = `<button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;color:var(--yellow)" onclick="quickMaintenanceVehicle('${v.item_id}')">🔧 Bảo dưỡng</button>`;
      }

      actions = `<div style="display:flex;gap:4px;flex-wrap:wrap">${driveBtn}${fuelActions}${maintBtn}</div>
        <div style="display:flex;gap:4px;margin-top:4px">
          <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;flex:1" onclick="openGarageDetail('${v.item_id}')">📋 Chi tiết</button>
          <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;color:var(--red);flex:1" onclick="sellVehicleFromGarage('${v.item_id}')">💰 Bán xe</button>
        </div>`;
    }

    const isCompareSelected = _garageCompareList && _garageCompareList.indexOf(v.item_id) >= 0;
    const compareToggle = `<button class="btn btn-ghost" style="font-size:9px;padding:2px 6px;${isCompareSelected?'color:var(--accent2);border-color:var(--accent2)':''}" onclick="event.stopPropagation();toggleGarageCompare('${v.item_id}')" title="${isCompareSelected?'Bỏ chọn so sánh':'Thêm vào so sánh'}">${isCompareSelected?'✅':'☐'}</button>`;

    return `
      <div class="card" style="padding:12px;display:flex;flex-direction:column;gap:2px${isActive?' border:1px solid var(--green)':''}">
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


// ─── Garage Vehicle Detail Modal ─────────────────────────────

function openGarageDetail(vehicleId) {
const vehicle = _garageAllVehicles.find(v => v.item_id === vehicleId);
if (!vehicle) return toast('err', '❌ Không tìm thấy xe');

// Image
const img = document.getElementById('gd-img');
const emoji = document.getElementById('gd-emoji');
if (vehicle.image_url) {
  img.src = vehicle.image_url;
  img.style.display = 'block';
  emoji.style.display = 'none';
} else {
  img.style.display = 'none';
  emoji.style.display = 'block';
  emoji.textContent = vehicle.emoji || '🚗';
}

// Name & description
document.getElementById('gd-name').textContent = vehicle.name || '';
document.getElementById('gd-desc').textContent = vehicle.description || '';

// Badges
const badges = document.getElementById('gd-badges');
const vgIcons = {'Ô tô':'🚗','Xe máy':'🏍️','Xe máy điện':'🛵','Xe điện':'⚡','Xe đạp':'🚲'};
const vg = vehicle.vehicle_group || '';
let badgeHtml = '';
if (vg) badgeHtml += `<span class="badge badge-blue">${vgIcons[vg]||'🚗'} ${vg}</span>`;
if (vehicle.brand) badgeHtml += `<span class="badge badge-purple">🏷️ ${vehicle.brand}</span>`;
if (vehicle.origin) {
  const oe = vehicle.origin === 'Châu Á' ? '🌏' : vehicle.origin === 'Châu Âu' ? '🌍' : '🌎';
  badgeHtml += `<span class="badge" style="background:rgba(59,130,246,.15);color:#3b82f6">${oe} ${vehicle.origin}</span>`;
}
if (vehicle.stars) badgeHtml += `<span class="badge" style="background:rgba(245,158,11,.15);color:#f59e0b">${'⭐'.repeat(vehicle.stars)}</span>`;
badges.innerHTML = badgeHtml;

// Durability
const dupPct = vehicle.durability_pct || 0;
const dupCol = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';
document.getElementById('gd-dup').textContent = `${vehicle.durability || 0} / ${vehicle.max_durability || 0}`;
document.getElementById('gd-dup').style.color = dupCol;
const dupBar = document.getElementById('gd-dup-bar');
dupBar.style.width = dupPct + '%';
dupBar.style.background = dupCol;

// Fuel
const fuelSection = document.getElementById('gd-fuel-section');
const manualLabel = document.getElementById('gd-manual-label');
const fuelType = vehicle.fuel_type || 'gasoline';
const isManual = fuelType === 'manual';
const isElectric = fuelType === 'electric';

if (!isManual) {
  fuelSection.style.display = 'block';
  manualLabel.style.display = 'none';
  const unit = isElectric ? 'kWh' : 'L';
  const flLabel = isElectric ? '🔋 Pin' : '⛽ Xăng';
  document.getElementById('gd-fuel-label').textContent = flLabel;
  const fuelPct = vehicle.fuel_pct || 0;
  const fuelCol = fuelPct > 50 ? 'var(--green)' : fuelPct > 20 ? 'var(--yellow)' : 'var(--red)';
  const fuelLvl = typeof vehicle.fuel_level === 'number' ? vehicle.fuel_level.toFixed(1) : '0';
  document.getElementById('gd-fuel').textContent = `${fuelLvl} / ${vehicle.max_fuel || 0} ${unit}`;
  document.getElementById('gd-fuel').style.color = fuelCol;
  const fuelBar = document.getElementById('gd-fuel-bar');
  fuelBar.style.width = fuelPct + '%';
  fuelBar.style.background = vehicle.is_charging ? 'var(--accent2)' : fuelCol;
} else {
  fuelSection.style.display = 'none';
  manualLabel.style.display = 'block';
}

// ── KM traveled (v1.1.5b) ──
const kmSection = document.getElementById('gd-km-section');
const kmVal = vehicle.km_traveled || 0;
const cardsVal = vehicle.total_cards_driven || 0;
if (kmVal > 0 || cardsVal > 0) {
  document.getElementById('gd-km').textContent = kmVal.toFixed(1) + ' km';
  document.getElementById('gd-cards-driven').textContent = cardsVal.toLocaleString();
  kmSection.style.display = 'block';
} else {
  kmSection.style.display = 'none';
}

// ── Energy save (v1.1.5b) ──
const esSection = document.getElementById('gd-energy-save-section');
const esVal = vehicle.energy_save_percent || 0;
if (esVal > 0) {
  document.getElementById('gd-energy-save').textContent = (esVal * 100).toFixed(1) + '%';
  esSection.style.display = 'block';
} else {
  esSection.style.display = 'none';
}

// Specs
const specs = document.getElementById('gd-specs');
const specItems = [];
if (vg) specItems.push({label:'Loại xe', value: vg});
const typeField = vehicle.car_type || vehicle.bike_type || vehicle.ebike_type || vehicle.ev_type || vehicle.cycle_type || '';
if (typeField) specItems.push({label:'Kiểu dáng', value: typeField});
if (vehicle.brand) specItems.push({label:'Thương hiệu', value: vehicle.brand});
if (vehicle.origin) specItems.push({label:'Xuất xứ', value: vehicle.origin});
if (vehicle.stars) specItems.push({label:'Đánh giá', value: '⭐'.repeat(vehicle.stars)});
// Fuel specs
if (!isManual) {
  const unit = isElectric ? 'kWh' : 'L';
  specItems.push({label: isElectric ? '🔋 Dung lượng pin' : '⛽ Bình xăng', value: `${vehicle.max_fuel || 0} ${unit}`});
  if (isElectric && vehicle.charge_time_hours) {
    specItems.push({label: '⏱️ Thời gian sạc', value: `${vehicle.charge_time_hours}h`});
  }
}
// Status
if (vehicle.is_active) specItems.push({label:'Trạng thái', value:'✅ Đang lái'});
else if (vehicle.in_repair) specItems.push({label:'Trạng thái', value:'🔧 Đang sửa'});
else if (vehicle.breakdown_repair) specItems.push({label:'Trạng thái', value:'💥 Sự cố'});
else if (vehicle.maintenance_due) specItems.push({label:'Trạng thái', value:'⚠️ Bảo dưỡng'});
else if (!isManual && (vehicle.fuel_level||0) <= 0) specItems.push({label:'Trạng thái', value:'🪫 Hết nhiên liệu'});
else specItems.push({label:'Trạng thái', value:'🟢 Sẵn sàng'});

specs.innerHTML = specItems.map(s =>
  `<div class="sd-spec"><div class="label">${s.label}</div><div class="value">${s.value}</div></div>`
).join('');

// Effects
const effects = document.getElementById('gd-effects');
const effectList = (vehicle.effect_list && vehicle.effect_list.length) ? vehicle.effect_list : (vehicle.effect ? [vehicle.effect] : []);
if (effectList.length) {
  const effIcons = {
    study_time_reduction:'⏱️', xp_multiplier:'⚡', stock_cooldown_reduction:'📉',
    crypto_cooldown_reduction:'🪙', equipment_slot:'🎒', disease_resistance:'💪',
    interest_bonus:'🏦', tax_reduction:'💰', health_boost:'❤️', passive_income_bonus:'💵',
    interest_speed_boost:'📈', instant_interest_cooldown:'⏳', new_card_limit_boost:'🆕',
    skill_cooldown_reduction:'🔧', review_count_bonus:'📚', food_freshness:'🍽️',
    interval_boost:'📈', easy_interval_bonus:'🎯', factor_boost:'🧠',
    density_reduction:'📉'  // added for garage vehicles
  };
  effects.innerHTML = effectList.map(e =>
    `<div class="sd-effect">
      <span class="sd-effect-icon">${effIcons[e.type]||'✨'}</span>
      <div><div class="sd-effect-name">${e.name||''}</div>
      <div class="sd-effect-desc">${e.desc||''}</div></div>
    </div>`
  ).join('');
} else {
  effects.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Không có hiệu ứng đặc biệt</div>';
}

// Sell estimate
const sellEst = vehicle.sell_estimate || 0;
const sellLine = document.getElementById('gd-sell-line');
if (sellEst > 0) {
  sellLine.style.display = 'block';
  sellLine.textContent = `💰 Giá bán ước tính: ${fmt(sellEst)}`;
} else {
  sellLine.style.display = 'none';
}

// Actions
const actions = document.getElementById('gd-actions');
let actionHtml = '';

if (vehicle.is_active) {
  actionHtml = `<button class="btn btn-ghost" style="font-size:12px;padding:6px 14px" onclick="stopCurrentVehicle();closeGarageDetailModal()">🛑 Dừng xe</button>`;
} else if (vehicle.durability <= 0) {
  actionHtml = `<button class="btn btn-yellow" style="font-size:12px;padding:6px 14px" onclick="repairVehicle('${vehicle.item_id}');closeGarageDetailModal()">🔧 Sửa chữa</button>`;
} else {
  // Drive button
  const noFuel = !isManual && (vehicle.fuel_level||0) <= 0;
  if (!noFuel && !vehicle.in_repair && !vehicle.breakdown_repair) {
    actionHtml += `<button class="btn btn-green" style="font-size:12px;padding:6px 14px" onclick="useVehicle('${vehicle.item_id}');closeGarageDetailModal()">${vgIcons[vg]||'🚗'} Lái xe</button>`;
  }
  // Fuel buttons
  if (!isManual && (vehicle.fuel_level||0) < (vehicle.max_fuel||0)) {
    if (isElectric && !vehicle.is_charging) {
      actionHtml += `<button class="btn btn-ghost" style="font-size:12px;padding:6px 14px" onclick="rechargeVehicle('${vehicle.item_id}');closeGarageDetailModal()">🔌 Sạc điện</button>`;
    } else if (!isElectric) {
      actionHtml += `<button class="btn btn-ghost" style="font-size:12px;padding:6px 14px" onclick="refuelVehicle('${vehicle.item_id}');closeGarageDetailModal()">⛽ Đổ xăng</button>`;
    }
  }
  if (isElectric && vehicle.is_charging) {
    actionHtml += `<span style="font-size:12px;color:var(--accent2);padding:6px">⚡ Đang sạc...</span>`;
  }
  // Maintenance
  if ((vehicle.durability||0) < (vehicle.max_durability||100)) {
    actionHtml += `<button class="btn btn-ghost" style="font-size:12px;padding:6px 14px;color:var(--yellow)" onclick="quickMaintenanceVehicle('${vehicle.item_id}');closeGarageDetailModal()">🔧 Bảo dưỡng</button>`;
  }
  // Sell
  actionHtml += `<button class="btn btn-ghost" style="font-size:12px;padding:6px 14px;color:var(--red)" onclick="sellVehicleFromGarage('${vehicle.item_id}')">💰 Bán xe</button>`;
}

actions.innerHTML = actionHtml;

// Show modal
document.getElementById('modal-garage-detail').classList.add('open');
document.body.style.overflow = 'hidden';
}

function closeGarageDetailModal() {
document.getElementById('modal-garage-detail').classList.remove('open');
document.body.style.overflow = '';
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


// ─── Tab Bảo dưỡng / Sửa ngay ─────────────────────────────────


async function loadMaintenanceTab() {
  const container = document.getElementById('maint-vehicle-list');
  container.innerHTML = '<div class="empty"><div class="ei">⏳</div><p>Đang tải dữ liệu bảo dưỡng…</p></div>';

  try {
    const data = JSON.parse(await B.getMaintenanceTabData());
    const vehicles = data.vehicles || [];
    const totalCost = data.total_cost || 0;
    const count = data.count || 0;

    // Update stats cards
    document.getElementById('maint-count').textContent = count;
    document.getElementById('maint-total-cost').textContent = fmt(totalCost);

    // Tip
    const tipEl = document.getElementById('maint-tip');
    if (count === 0) {
      tipEl.textContent = '✅ Tất cả xe đã ở độ bền tối đa!';
    } else if (count === 1) {
      tipEl.textContent = '💡 Bảo dưỡng định kỳ giúp xe bền hơn, tránh sự cố tốn kém!';
    } else {
      tipEl.textContent = `💡 Có ${count} xe cần bảo dưỡng. Bảo dưỡng sớm giúp tiết kiệm chi phí sửa chữa về sau.`;
    }

    if (!vehicles.length) {
      container.innerHTML = '<div class="empty"><div class="ei">✅</div><p>Tất cả xe đã ở trạng thái tốt nhất! 🎉</p></div>';
      return;
    }

    container.innerHTML = vehicles.map(v => {
      const dupPct = v.durability_pct || 0;
      const dupCol = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';
      const vgEmojiMap = {'Ô tô':'🚗','Xe điện':'⚡','Xe máy':'🏍️','Xe máy điện':'🛵','Xe đạp':'🚲'};
      const emoji = vgEmojiMap[v.vehicle_group] || '🚗';

      const maintDueTag = v.maintenance_due
        ? '<span style="font-size:10px;color:var(--yellow);margin-left:6px">⚠️ Đến hạn</span>'
        : '';

      return `<div class="card" style="padding:12px;border-color:rgba(245,158,11,.2)">
        <div style="display:flex;align-items:center;gap:10px">
          <span style="font-size:24px">${v.emoji || emoji}</span>
          <div style="flex:1;min-width:0">
            <div style="font-size:13px;font-weight:700">${v.name}${maintDueTag}</div>
            <div style="font-size:11px;color:var(--muted2)">${v.vehicle_group || ''}</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:12px;font-weight:700;color:var(--yellow)">${fmt(v.cost)}</div>
            <div style="font-size:10px;color:var(--muted2)">⏱ ${v.duration_str}</div>
          </div>
        </div>
        <div style="margin-top:8px">
          <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">
            <span>🔩 Độ bền</span>
            <span style="color:${dupCol};font-weight:600">${v.durability} / ${v.max_durability}</span>
          </div>
          <div class="fresh-wrap" style="width:100%;margin-top:2px">
            <div style="height:100%;width:${dupPct}%;background:${dupCol};border-radius:2px;transition:width .4s"></div>
          </div>
        </div>
        <button class="btn btn-yellow" style="font-size:11px;padding:4px 10px;margin-top:8px;width:100%" onclick="quickMaintenanceVehicle('${v.item_id}')">
          🔧 Bảo dưỡng ngay — ${fmt(v.cost)}
        </button>
      </div>`;
    }).join('');

  } catch (e) {
    container.innerHTML = '<div class="empty"><div class="ei">❌</div><p>Lỗi tải dữ liệu bảo dưỡng.</p></div>';
    console.error('loadMaintenanceTab error:', e);
  }
}


async function quickMaintenanceVehicle(vehicleId) {
  const res = JSON.parse(await B.quickMaintenance(vehicleId));

  if (res.ok) {
    toast('ok', `🔧 Đã gửi bảo dưỡng: ${res.item_name || ''} (${res.duration_str || ''}) — phí ${fmt(res.cost)}`);
    await loadGarage();
    // Reload maintenance tab if visible
    const maintTab = document.getElementById('garage-tab-maintenance');
    if (maintTab && maintTab.style.display !== 'none') {
      loadMaintenanceTab();
    }
  } else {
    toast('err', '❌ ' + (res.error || 'Không thể bảo dưỡng'));
  }
}


let boostTickerInterval = null;


// ─── Advanced Filter Toggle ─────────────────────────────

function toggleGarageAdvFilter() {
  const adv = document.getElementById('garage-adv-filters');
  const btn = document.getElementById('garage-adv-toggle');
  const isHidden = adv.style.display === 'none' || adv.style.display === '';
  adv.style.display = isHidden ? 'flex' : 'none';
  btn.textContent = isHidden ? '✕ Ẩn nâng cao' : '⚙️ Nâng cao';
}


// ─── Comparison System ─────────────────────────────

let _garageCompareList = [];

function toggleGarageCompare(vehicleId) {
  const idx = _garageCompareList.indexOf(vehicleId);
  if (idx >= 0) {
    _garageCompareList.splice(idx, 1);
  } else {
    if (_garageCompareList.length >= 4) {
      toast('err', '❌ Chỉ có thể so sánh tối đa 4 xe cùng lúc');
      return;
    }
    _garageCompareList.push(vehicleId);
  }
  updateGarageCompareBtn();
  applyGarageFilter();
}

function updateGarageCompareBtn() {
  const btn = document.getElementById('garage-compare-btn');
  if (!btn) return;
  const count = _garageCompareList.length;
  const cntEl = document.getElementById('garage-compare-count');
  if (cntEl) cntEl.textContent = count;
  btn.style.display = count > 0 ? 'inline-block' : 'none';
}

function openGarageCompare() {
  const modal = document.getElementById('modal-garage-compare');
  const content = document.getElementById('gc-content');

  const vehicles = _garageCompareList
    .map(id => _garageAllVehicles.find(v => v.item_id === id))
    .filter(Boolean);

  if (vehicles.length < 2) {
    content.innerHTML = '<div class="empty"><div class="ei">⚠️</div><p>Cần ít nhất 2 xe để so sánh.</p></div>';
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
    return;
  }

  const vgIcons = {'Ô tô':'🚗','Xe máy':'🏍️','Xe máy điện':'🛵','Xe điện':'⚡','Xe đạp':'🚲'};

  const fields = [
    { label: '🔖 Nhóm',        get: (v) => vgIcons[v.vehicle_group] || '🚗' },
    { label: '🏷️ Hãng',        get: (v) => v.brand || '—' },
    { label: '🌍 Xuất xứ',     get: (v) => v.origin || '—' },
    { label: '⭐ Sao',         get: (v) => v.stars ? '⭐'.repeat(v.stars) : '—' },
    { label: '💰 Giá mua',     get: (v) => fmt(v.price || 0) },
    { label: '⛽ Nhiên liệu',  get: (v) => {
        const ft = v.fuel_type || 'gasoline';
        return ft === 'electric' ? '🔋 Điện' : ft === 'manual' ? '🚲 Tay' : '⛽ Xăng';
      }},
    { label: '🔩 Độ bền',      get: (v) => `${v.durability || 0} / ${v.max_durability || 0} (${v.durability_pct || 0}%)` },
    { label: '🛢️ Nhiên liệu',  get: (v) => {
        if (v.fuel_type === 'manual') return '♾️ Không tốn';
        const unit = v.fuel_type === 'electric' ? 'kWh' : 'L';
        return `${(v.fuel_level||0).toFixed(1)} / ${v.max_fuel||0} ${unit} (${v.fuel_pct||0}%)`;
      }},
    { label: '⚡ Sạc',         get: (v) => v.is_charging ? '✅ Đang sạc' : v.charge_time_hours ? `${v.charge_time_hours}h` : '—' },
    { label: '📊 Trạng thái',  get: (v) => {
        if (v.is_active) return '✅ Đang lái';
        if (v.in_repair) return '🔧 Đang sửa';
        if (v.breakdown_repair) return '💥 Sự cố';
        if (v.maintenance_due) return '⚠️ Cần bảo dưỡng';
        if (!v.is_active && (v.durability||0) > 0) return '🟢 Sẵn sàng';
        return '🔴 Không dùng được';
      }},
    { label: '💰 Giá bán (ước)', get: (v) => fmt(v.sell_estimate || 0) },
  ];

  let html = `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr>`;
  html += `<th style="text-align:left;padding:8px 10px;background:var(--surface2);border:1px solid var(--border);font-weight:700;min-width:80px">Thông số</th>`;
  vehicles.forEach(v => {
    const imgTag = v.image_url
      ? `<img src="${v.image_url}" style="width:40px;height:40px;border-radius:6px;object-fit:cover;display:block;margin:0 auto 4px">`
      : `<div style="font-size:24px;text-align:center">${v.emoji||vgIcons[v.vehicle_group]||'🚗'}</div>`;
    const bgColor = v.is_active ? 'rgba(16,185,129,.08)' : 'var(--surface2)';
    html += `<th style="text-align:center;padding:8px 10px;background:${bgColor};border:1px solid var(--border);font-weight:700;min-width:130px">
      ${imgTag}
      <div style="font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px" title="${v.name}">${v.name}</div>
    </th>`;
  });
  html += `</tr></thead><tbody>`;

  fields.forEach(f => {
    html += `<tr><td style="padding:6px 10px;border:1px solid var(--border);font-weight:600;color:var(--muted2);background:var(--surface2)">${f.label}</td>`;
    vehicles.forEach(v => {
      html += `<td style="padding:6px 10px;border:1px solid var(--border);text-align:center">${f.get(v)}</td>`;
    });
    html += `</tr>`;
  });

  html += `<tr><td style="padding:6px 10px;border:1px solid var(--border);font-weight:600;color:var(--muted2);background:var(--surface2)">✨ Hiệu ứng</td>`;
  vehicles.forEach(v => {
    const effects = v.effect_list || [];
    let effectsHtml = effects.length
      ? effects.map(e => `<div style="font-size:11px;margin:2px 0">${e.icon||'•'} ${e.name||''} ${e.value ? `<span style="color:var(--accent2)">${e.value}</span>` : ''}</div>`).join('')
      : '<span style="color:var(--muted2)">Không có</span>';
    html += `<td style="padding:6px 10px;border:1px solid var(--border);text-align:left;font-size:11px">${effectsHtml}</td>`;
  });
  html += `</tr>`;

  html += `<tr><td style="padding:6px 10px;border:1px solid var(--border);font-weight:600;color:var(--muted2);background:var(--surface2)">🔧 Thao tác</td>`;
  vehicles.forEach(v => {
    html += `<td style="padding:6px 10px;border:1px solid var(--border);text-align:center">
      <button class="btn btn-ghost" style="font-size:10px;padding:3px 8px" onclick="closeGarageCompare();openGarageDetail('${v.item_id}')">📋 Chi tiết</button>
    </td>`;
  });
  html += `</tr></tbody></table></div>`;

  html += `<div style="display:flex;gap:8px;justify-content:center;margin-top:16px">
    <button class="btn btn-ghost" style="font-size:12px;padding:6px 16px" onclick="closeGarageCompare()">✕ Đóng</button>
    <button class="btn btn-ghost" style="font-size:12px;padding:6px 16px;color:var(--red)" onclick="clearGarageCompare()">🗑️ Xoá tất cả</button>
  </div>`;

  content.innerHTML = html;
  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeGarageCompare() {
  document.getElementById('modal-garage-compare').classList.remove('open');
  document.body.style.overflow = '';
}

function clearGarageCompare() {
  _garageCompareList = [];
  updateGarageCompareBtn();
  applyGarageFilter();
  closeGarageCompare();
}


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

  let _lastCardsRefresh = 0;  // timestamp (ms) lần cuối refresh cards_left từ backend

  const render = () => {

    const now = Math.floor(Date.now() / 1000);

    // ── Định kỳ refresh cards_left từ backend (mỗi 3 giây) ──
    const hasCardsBoosts = boosts.some(b => b.cards_left !== null && b.cards_left !== undefined);
    if (hasCardsBoosts && Date.now() - _lastCardsRefresh > 3000) {
      _lastCardsRefresh = Date.now();
      B.getActiveBoosts().then(raw => {
        try {
          const fresh = JSON.parse(raw);
          fresh.forEach(fb => {
            const existing = boosts.find(b => b.id === fb.id);
            if (existing) existing.cards_left = fb.cards_left;
          });
        } catch (_) {}
      }).catch(() => {});
    }

    // Lọc bỏ boost đã hết hạn (remaining_s <= 0 hoặc cards_left <= 0)
    const activeBoosts = boosts.filter(b => {
      if (b.remaining_s !== null && b.remaining_s !== undefined) {
        return b.remaining_s > 0;
      }
      if (b.cards_left !== null && b.cards_left !== undefined) {
        return b.cards_left > 0;
      }
      return true;
    });

    if (!activeBoosts.length) {
      strip.style.display = 'none';
      list.innerHTML = '';
      if (boostTickerInterval) { clearInterval(boostTickerInterval); boostTickerInterval = null; }
      // Trigger refresh để clean backend
      if (typeof refreshBoostStrip === 'function') refreshBoostStrip();
      return;
    }

    list.innerHTML = activeBoosts.map(b => {

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
      const slotId = (b.id || '').replace(/'/g, "\\'");

      return `<span style="margin-left:8px;color:var(--green)">${b.name}</span><span style="color:var(--muted2);font-size:11px">${desc}</span> <span style="color:var(--muted2)">(${timer})</span>` +
        `<button class="btn btn-ghost" style="font-size:10px;padding:2px 6px;margin-left:4px;color:var(--red)" onclick="deactivateBoostConfirm('${slotId}')">❌ Hủy</button>`;

    }).join(' |');

  };

  render();

  if (boostTickerInterval) clearInterval(boostTickerInterval);

  boostTickerInterval = setInterval(render, 1000);

}
