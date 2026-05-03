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



