// ════════════════════════════════════════════════════════════
//  GARAGE
// ════════════════════════════════════════════════════════════

let _garageAllVehicles = [];

async function loadGarage() {

  const res = JSON.parse(await B.getGarageData());

  const garage = res.garage || [];

  const active = res.active_vehicle;

  const slots  = res.total_slots || 1;

  // Store full list for filtering
  _garageAllVehicles = garage;

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

  // ── Apply filters & render ──
  applyGarageFilter();

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
