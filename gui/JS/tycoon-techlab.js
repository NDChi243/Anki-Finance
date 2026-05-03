// ════════════════════════════════════════════════════════════
//  TECH LAB
// ════════════════════════════════════════════════════════════

let _techLabAllItems = [];

async function loadTechLab() {

  const res = JSON.parse(await B.getTechLabData());

  const techList = res.tech_lab || [];
  const active   = res.active_tech;

  _techLabAllItems = techList;

  // ── Active tech banner ──
  const banner = document.getElementById('techlab-active-banner');

  if (active) {
    banner.style.display = 'block';

    document.getElementById('tlab-emoji').textContent = active.emoji || '💻';
    document.getElementById('tlab-name').textContent  = active.name || '';

    // Durability bar
    const dupPct = active.durability_pct || 0;
    const dupCol = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';
    document.getElementById('tlab-dup').textContent = `${active.durability || 0}/${active.max_durability || 0}`;
    const dupBar = document.getElementById('tlab-dup-bar');
    dupBar.style.width = dupPct + '%';
    dupBar.style.background = dupCol;

    // Status text
    let statusText = '✅ Đang hoạt động';
    if (active.in_repair) {
      statusText = '🔧 Đang sửa chữa';
    } else if (active.maintenance_due) {
      statusText = '⚠️ Cần bảo dưỡng';
    } else if (active.durability <= 0) {
      statusText = '💔 Hết độ bền';
    }
    document.getElementById('tlab-status').textContent = statusText;

  } else {
    banner.style.display = 'none';
  }

  // ── Render tech grid ──
  renderTechLabGrid(techList);
}

function renderTechLabGrid(items) {
  const grid = document.getElementById('techlab-grid');

  if (!items.length) {
    grid.innerHTML = `<div class="empty"><div class="ei">💻</div><p>Bạn chưa có thiết bị công nghệ nào. Hãy mua ở cửa hàng!</p></div>`;
    return;
  }

  grid.innerHTML = items.map(v => {
    const isActive      = v.is_active;
    const inRepair      = v.in_repair;
    const maintDue      = v.maintenance_due;
    const dupPct        = v.durability_pct || 0;
    const dupCol        = dupPct > 50 ? 'var(--green)' : dupPct > 20 ? 'var(--yellow)' : 'var(--red)';

    // Sell estimate
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
      actions = `<button class="btn btn-ghost" style="font-size:10px;padding:3px 8px;width:100%;color:var(--red)" onclick="deactivateCurrentTech()">🛑 Tắt</button>`;
    } else if (inRepair) {
      const remaining = Math.max(0, Math.floor((v.repair_until || 0) - Date.now()/1000));
      const rh = Math.floor(remaining/3600), rm = Math.floor((remaining%3600)/60);
      actions = `<span style="font-size:10px;color:var(--yellow)">🔧 Còn ${rh}h${rm}p</span>`;
    } else if (v.durability <= 0) {
      actions = `<button class="btn btn-yellow" style="font-size:11px;padding:4px 8px;width:100%" onclick="repairTechItem('${v.item_id}')">🔧 Sửa chữa</button>`;
    } else if (maintDue) {
      actions = `<div style="display:flex;gap:4px;flex-wrap:wrap">
        <button class="btn btn-yellow" style="font-size:10px;padding:3px 8px;flex:1" onclick="maintainTechItem('${v.item_id}')">🔧 Bảo dưỡng</button>
        <button class="btn btn-ghost" style="font-size:10px;padding:3px 6px;color:var(--red)" onclick="sellTechItem('${v.item_id}')">💰 Bán</button>
      </div>`;
    } else {
      actions = `<div style="display:flex;gap:4px;flex-wrap:wrap">
        <button class="btn btn-green" style="font-size:10px;padding:3px 8px;flex:1" onclick="activateTechItem('${v.item_id}')">▶️ Dùng</button>
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

      <!-- Durability bar -->
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

// ── Actions ──────────────────────────────────────────────

async function activateTechItem(itemId) {
  const res = JSON.parse(await B.activateTech(itemId));
  if (res.ok) {
    toast('ok', `✅ Đã kích hoạt!`);
    await loadTechLab();
  } else {
    toast('err', '❌ ' + res.error);
  }
}

async function deactivateCurrentTech() {
  const res = JSON.parse(await B.deactivateTech());
  if (res.ok) {
    toast('ok', `🛑 Đã tắt thiết bị`);
    await loadTechLab();
  } else {
    toast('err', '❌ ' + res.error);
  }
}

async function repairTechItem(itemId) {
  // Xem trước chi phí
  const preview = JSON.parse(await B.getTechRepairCost(itemId));
  if (!preview.ok) {
    toast('err', '❌ ' + preview.error);
    return;
  }

  const confirmed = confirm(
    `🔧 Sửa chữa: ${preview.item_name}\n` +
    `• Chi phí: ${fmt(preview.cost)}\n` +
    `• Thời gian: ${preview.duration_str}\n\n` +
    `Xác nhận sửa chữa?`
  );
  if (!confirmed) return;

  const res = JSON.parse(await B.repairTech(itemId));
  if (res.ok) {
    toast('ok', `🔧 Đã gửi sửa chữa! Chi phí: ${fmt(res.cost)}. Thời gian: ${res.duration_str}`);
    await loadTechLab();
  } else {
    toast('err', '❌ ' + res.error);
  }
}

async function maintainTechItem(itemId) {
  const res = JSON.parse(await B.maintainTech(itemId));
  if (res.ok) {
    toast('ok', `🔧 Đã bảo dưỡng! Độ bền: ${res.new_durability}/${res.max_durability}`);
    await loadTechLab();
  } else {
    toast('err', '❌ ' + res.error);
  }
}

async function sellTechItem(itemId) {
  // Tìm item trong danh sách
  const item = _techLabAllItems.find(v => v.item_id === itemId);
  if (!item) return;

  const price     = item.price || 0;
  const sellEst   = item.sell_estimate || 0;
  const lossAmt   = price - sellEst;
  const deprPct   = price > 0 ? Math.round((lossAmt / price) * 100) : 0;

  const confirmed = confirm(
    `💰 Bán: ${item.name}\n` +
    `• Giá gốc:        ${fmt(price)}\n` +
    `• Khấu hao:       ${deprPct}%\n` +
    `• Giá bán ước tính: ${fmt(sellEst)}\n` +
    `• Bạn mất:        ${fmt(lossAmt)}\n\n` +
    `Xác nhận bán?`
  );
  if (!confirmed) return;

  const res = JSON.parse(await B.sellTech(itemId));
  if (res.ok) {
    toast('ok', `💰 Đã bán ${res.item_name} — thu về ${fmt(res.sell_price)} (khấu hao ${res.depreciation_pct}%)`);
    await loadTechLab();
  } else {
    toast('err', '❌ ' + res.error);
  }
}
