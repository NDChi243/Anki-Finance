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



