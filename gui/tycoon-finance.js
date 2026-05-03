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



