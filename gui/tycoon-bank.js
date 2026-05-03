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



