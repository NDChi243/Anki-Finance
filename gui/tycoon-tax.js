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



