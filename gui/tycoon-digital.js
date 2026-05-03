// ════════════════════════════════════════════════════════════

//  DIGITAL ASSETS — Tài sản số (Crypto)

// ════════════════════════════════════════════════════════════



let _cryptoMarket     = [];   // market array

let _cryptoPortfolio  = [];   // holdings

let _cryptoStaking    = [];   // staking positions

let _cryptoTxns       = [];   // transactions

let _cryptoSort       = 'change_pct';

let _buyCryptoSym     = null;

let _sellCryptoSym    = null;

let _stakeCryptoSym   = null;

let _detailCryptoSym  = null;



async function loadDigitalAssets() {

  try {

    const raw = JSON.parse(await B.getCryptoAllData());

    if (!raw.ok) { toast('err', '❌ ' + (raw.error || 'Lỗi tải crypto')); return; }

    _cryptoMarket    = raw.market    || [];

    _cryptoPortfolio = raw.portfolio || [];

    _cryptoStaking   = raw.staking   || [];

    _cryptoTxns      = raw.transactions || [];

    renderMarketCycleBanner(raw.market_cycle || {});

    renderCryptoHero(raw.portfolio_summary || {});

    renderCryptoGrid();

    renderCryptoPortfolio();

    renderCryptoStaking();

    renderCryptoTransactions();

  } catch (e) {

    toast('err', '❌ Lỗi tải tài sản số: ' + e.message);

  }

}



// ── Banner ──────────────────────────────────────────────────

function renderMarketCycleBanner(cycle) {

  const el = document.getElementById('crypto-cycle-banner');

  if (!el) return;

  el.className = 'market-cycle-banner ' + (cycle.color || 'neutral');

  el.textContent = cycle.label || '⚖️ Thị trường trung lập';

}



// ── Hero summary ─────────────────────────────────────────────

function renderCryptoHero(summary) {

  const fmt = v => fmtVND(v);

  const pnl = summary.total_pnl || 0;

  const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };

  el('cov-invested', fmt(summary.total_invested || 0));

  el('cov-mktval',   fmt(summary.total_market_value || 0));

  const pnlEl = document.getElementById('cov-pnl');

  if (pnlEl) {

    pnlEl.textContent = (pnl >= 0 ? '+' : '') + fmt(pnl);

    pnlEl.style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)';

  }

  el('cov-staking', fmt(summary.total_staking_vnd || 0));

}



// ── Tab switching ────────────────────────────────────────────

function switchCryptoTab(tab) {

  document.querySelectorAll('.crypto-tab').forEach(t => t.classList.remove('active'));

  const tabEl = document.getElementById('ctab-' + tab);

  if (tabEl) tabEl.classList.add('active');

  document.querySelectorAll('.crypto-panel').forEach(p => p.classList.remove('active'));

  const panelEl = document.getElementById('cpanel-' + tab);

  if (panelEl) panelEl.classList.add('active');

}



// ── Market grid ───────────────────────────────────────────────

function sortCryptoBy(field) {

  _cryptoSort = field;

  renderCryptoGrid();

}



function renderCryptoGrid() {

  const container = document.getElementById('crypto-market-grid');

  if (!container) return;

  const catFilter = (document.getElementById('crypto-cat-filter') || {}).value || 'all';

  const searchQ   = ((document.getElementById('crypto-search') || {}).value || '').toLowerCase().trim();



  let list = _cryptoMarket.slice();

  if (catFilter !== 'all') list = list.filter(a => a.category === catFilter);

  if (searchQ) list = list.filter(a =>

    a.symbol.toLowerCase().includes(searchQ) ||

    (a.name || '').toLowerCase().includes(searchQ) ||

    (a.name_vi || '').toLowerCase().includes(searchQ)

  );

  if (_cryptoSort === 'change_pct') {

    list.sort((a, b) => (b.change_pct || 0) - (a.change_pct || 0));

  } else {

    list.sort((a, b) => (b.price || 0) - (a.price || 0));

  }



  if (!list.length) {

    container.innerHTML = '<div class="empty" style="grid-column:1/-1;margin-top:30px"><div class="ei">🔍</div><div>Không tìm thấy coin nào</div></div>';

    return;

  }



  container.innerHTML = list.map(a => {

    const chg       = a.change_pct || 0;

    const isStable  = a.is_stablecoin;

    const isRugged  = a.rug_pulled;

    const cardClass = isRugged ? 'rugged' : isStable ? 'stable' : chg >= 0 ? 'up' : 'dn';

    const priceClass = isStable ? 'stable' : chg >= 0 ? 'up' : 'dn';

    const chgStr    = (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%';

    const apyBadge  = a.staking_apy > 0 ? `<span class="crypto-apy-badge">🏦 ${(a.staking_apy*100).toFixed(1)}% APY</span>` : '';

    const rugBadge  = isRugged ? `<span class="rug-badge">🚨 Rug Pull</span>` : '';

    return `

<div class="crypto-card ${cardClass}" onclick="showCryptoDetail('${a.symbol}')">

  <div class="cc-row">

    <div>

      <div class="cc-sym">${a.emoji || '🪙'} ${a.symbol}${rugBadge}</div>

      <div class="cc-name">${a.name_vi || a.name}</div>

    </div>

    <span class="crypto-cat-badge">${a.category}</span>

  </div>

  <div class="cc-row">

    <div class="cc-price ${priceClass}">${fmtVND(a.price)}</div>

    <div class="cc-chg ${chg >= 0 ? 'up' : 'dn'}">${chgStr}</div>

  </div>

  <div class="cc-row" style="flex-wrap:wrap;gap:4px">

    ${apyBadge}

    <span class="crypto-exch">📍 ${a.exchange}</span>

  </div>

  <button class="btn" style="width:100%;margin-top:4px;font-size:12px" onclick="event.stopPropagation();openBuyCryptoModal('${a.symbol}')">🟢 Mua</button>

</div>`;

  }).join('');

}



// ── Portfolio ─────────────────────────────────────────────────

function renderCryptoPortfolio() {

  const container = document.getElementById('crypto-holdings-list');

  if (!container) return;

  if (!_cryptoPortfolio.length) {

    container.innerHTML = `<div class="empty" style="margin-top:30px"><div class="ei">💼</div><div>Chưa có tài sản nào</div><div style="font-size:12px;color:var(--muted2);margin-top:6px">Mua crypto trên tab Thị trường hoặc Cửa hàng</div></div>`;

    return;

  }

  container.innerHTML = _cryptoPortfolio.map(h => {

    const pnl      = h.pnl || 0;

    const pnlPct   = h.pnl_pct || 0;

    const pnlClass = pnl >= 0 ? 'pos' : 'neg';

    const pnlStr   = (pnl >= 0 ? '+' : '') + fmtVND(pnl) + ` (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)`;

    const qty      = h.quantity || 0;

    const avail    = h.avail_qty || 0;

    const staked   = h.staked_amount || 0;

    const hasStaking = (h.staking_apy || 0) > 0;

    const stakeBtnHtml = hasStaking

      ? `<button class="btn btn-ghost" style="font-size:11px" onclick="openStakeModal('${h.symbol}')">🏦 Stake</button>`

      : '';

    return `

<div class="crypto-holding-card">

  <div class="ch-head">

    <div>

      <div class="ch-sym">${h.emoji || '🪙'} ${h.symbol}</div>

      <div class="ch-meta">Số lượng: ${qty.toFixed(6)} • Khả dụng: ${avail.toFixed(6)}${staked > 0 ? ` • Đang stake: ${staked.toFixed(6)}` : ''}</div>

      <div class="ch-meta">Giá vốn TB: ${fmtVND(h.avg_cost_per_unit || 0)} • Sàn: ${h.exchange || ''}</div>

    </div>

    <div class="ch-value">

      <div class="ch-val">${fmtVND(h.market_value || 0)}</div>

      <div class="ch-pnl ${pnlClass}">${pnlStr}</div>

    </div>

  </div>

  <div style="display:flex;gap:6px;flex-wrap:wrap">

    <button class="btn btn-ghost" style="font-size:11px" onclick="openBuyCryptoModal('${h.symbol}')">➕ Mua thêm</button>

    <button class="btn btn-ghost" style="font-size:11px;color:var(--red);border-color:var(--red)" onclick="openSellCryptoModal('${h.symbol}')">🔴 Bán</button>

    ${stakeBtnHtml}

  </div>

</div>`;

  }).join('');

}



// ── Staking positions ────────────────────────────────────────

function renderCryptoStaking() {

  const container = document.getElementById('crypto-staking-list');

  if (!container) return;

  if (!_cryptoStaking.length) {

    container.innerHTML = '<div style="font-size:13px;color:var(--muted2);padding:8px 0">Chưa có vị thế staking nào.</div>';

    return;

  }

  container.innerHTML = _cryptoStaking.map(s => {

    const locked   = s.locked;

    const daysLeft = s.days_left || 0;

    const lockStr  = locked ? `🔒 Còn ${daysLeft} ngày` : '✅ Sẵn sàng rút';

    const unBtn    = locked ? '' : `<button class="btn" style="font-size:11px;background:var(--accent2)" onclick="doUnstake('${s.stake_id}')">📤 Rút stake</button>`;

    return `

<div class="staking-card">

  <div class="sk-head">

    <span class="sk-sym">${s.emoji || '🪙'} ${s.symbol}</span>

    <span class="sk-apy">APY ${((s.staking_apy||0)*100).toFixed(1)}%</span>

  </div>

  <div class="sk-detail">

    Đang stake: <strong>${(s.staked_amount||0).toFixed(6)}</strong> ${s.symbol} (~${fmtVND(s.staked_vnd||0)})<br>

    Trạng thái: ${lockStr}<br>

    Bắt đầu: ${s.staked_at ? new Date(s.staked_at*1000).toLocaleDateString('vi-VN') : '—'}

  </div>

  ${unBtn ? `<div style="margin-top:8px">${unBtn}</div>` : ''}

</div>`;

  }).join('');

}



// ── Transactions ─────────────────────────────────────────────

function renderCryptoTransactions() {

  const container = document.getElementById('crypto-txn-list');

  if (!container) return;

  if (!_cryptoTxns.length) {

    container.innerHTML = '<div class="empty" style="margin-top:30px"><div class="ei">📜</div><div>Chưa có giao dịch nào</div></div>';

    return;

  }

  const list = [..._cryptoTxns].reverse();

  container.innerHTML = list.map(t => {

    const typeLabel = { buy:'Mua', sell:'Bán', stake:'Stake', unstake:'Unstake' }[t.type] || t.type;

    const amtStr = t.total_vnd > 0 ? fmtVND(t.total_vnd) : (t.note || '');

    return `

<div class="crypto-txn-item">

  <span class="crypto-txn-badge ${t.type}">${typeLabel}</span>

  <span style="font-size:18px">${t.emoji || '🪙'}</span>

  <div style="flex:1">

    <div style="font-size:13px;font-weight:700">${t.symbol} — ${(t.quantity||0).toFixed(6)}</div>

    <div style="font-size:11px;color:var(--muted2)">${t.date || ''} · ${t.exchange || ''}</div>

  </div>

  <div style="text-align:right;font-size:13px;font-weight:700">${amtStr}</div>

</div>`;

  }).join('');

}



// ── Buy Modal ─────────────────────────────────────────────────

function openBuyCryptoModal(symbol) {

  const asset = _cryptoMarket.find(a => a.symbol === symbol);

  if (!asset) return;

  _buyCryptoSym = symbol;

  document.getElementById('bc-emoji').textContent   = asset.emoji || '🪙';

  document.getElementById('bc-symbol').textContent  = asset.symbol;

  document.getElementById('bc-name-vi').textContent = asset.name_vi || asset.name;

  document.getElementById('bc-price').textContent   = fmtVND(asset.price);

  document.getElementById('bc-exchange').textContent = '📍 ' + (asset.exchange || '');

  document.getElementById('bc-amount').value = '';

  document.getElementById('bc-preview').textContent = '';

  document.getElementById('modal-buy-crypto').classList.add('open');

  document.getElementById('bc-amount').focus();

}



function openBuyCryptoFromDetail() {

  document.getElementById('modal-crypto-detail').classList.remove('open');

  if (_detailCryptoSym) openBuyCryptoModal(_detailCryptoSym);

}



function setCryptoAmt(amount) {

  document.getElementById('bc-amount').value = amount;

  previewBuyCrypto();

}



function previewBuyCrypto() {

  const asset = _cryptoMarket.find(a => a.symbol === _buyCryptoSym);

  if (!asset) return;

  const amt = parseInt(document.getElementById('bc-amount').value) || 0;

  const fee = Math.round(amt * 0.001);

  const net = amt - fee;

  const qty = net / (asset.price || 1);

  document.getElementById('bc-preview').innerHTML =

    `Nhận: <strong>${qty.toFixed(6)} ${asset.symbol}</strong> · Phí: ${fmtVND(fee)}`;

}



async function confirmBuyCrypto() {

  const amt = parseInt(document.getElementById('bc-amount').value) || 0;

  if (!_buyCryptoSym || amt <= 0) { toast('warn', '⚠️ Nhập số tiền hợp lệ.'); return; }

  const btn = document.getElementById('bc-confirm-btn');

  btn.disabled = true;

  try {

    const res = JSON.parse(await B.buyCrypto(_buyCryptoSym, amt));

    if (!res.ok) { toast('err', '❌ ' + res.error); return; }

    document.getElementById('modal-buy-crypto').classList.remove('open');

    toast('ok', `✅ Mua ${res.quantity.toFixed(6)} ${_buyCryptoSym} thành công!`);

    loadDigitalAssets();

  } catch(e) { toast('err', '❌ ' + e.message); }

  finally { btn.disabled = false; }

}



// ── Sell Modal ─────────────────────────────────────────────────

function openSellCryptoModal(symbol) {

  const h = _cryptoPortfolio.find(h => h.symbol === symbol);

  const a = _cryptoMarket.find(a => a.symbol === symbol);

  if (!h || !a) return;

  _sellCryptoSym = symbol;

  document.getElementById('sc-emoji').textContent    = h.emoji || '🪙';

  document.getElementById('sc-symbol').textContent   = symbol;

  document.getElementById('sc-holding').textContent  = `Số lượng: ${(h.quantity||0).toFixed(6)} · Khả dụng: ${(h.avail_qty||0).toFixed(6)}`;

  document.getElementById('sc-price').textContent    = fmtVND(a.price);

  document.getElementById('sc-pnl-now').textContent  = `PnL: ${h.pnl >= 0 ? '+' : ''}${fmtVND(h.pnl||0)}`;

  document.getElementById('sc-pnl-now').style.color  = (h.pnl||0) >= 0 ? 'var(--green)' : 'var(--red)';

  document.getElementById('sc-pct-slider').value = 50;

  document.getElementById('sc-pct-label').textContent = '50%';

  document.getElementById('sc-preview').textContent   = '';

  previewSellCrypto();

  document.getElementById('modal-sell-crypto').classList.add('open');

}



function previewSellCrypto() {

  const pct    = parseInt(document.getElementById('sc-pct-slider').value) || 50;

  const h      = _cryptoPortfolio.find(h => h.symbol === _sellCryptoSym);

  const a      = _cryptoMarket.find(a => a.symbol === _sellCryptoSym);

  document.getElementById('sc-pct-label').textContent = pct + '%';

  if (!h || !a) return;

  const sellQty  = (h.avail_qty || 0) * pct / 100;

  const gross    = sellQty * (a.price || 0);

  const fee      = gross * 0.001;

  const net      = gross - fee;

  const costBasis = sellQty * (h.avg_cost_per_unit || a.price);

  const pnl      = net - costBasis;

  document.getElementById('sc-preview').innerHTML =

    `Thu về: <strong>${fmtVND(Math.round(net))}</strong> · PnL: <span style="color:${pnl>=0?'var(--green)':'var(--red)'}">${pnl>=0?'+':''}${fmtVND(Math.round(pnl))}</span>`;

}



async function confirmSellCrypto() {

  const pct = parseInt(document.getElementById('sc-pct-slider').value) || 50;

  if (!_sellCryptoSym) return;

  try {

    const res = JSON.parse(await B.sellCrypto(_sellCryptoSym, pct / 100));

    if (!res.ok) { toast('err', '❌ ' + res.error); return; }

    document.getElementById('modal-sell-crypto').classList.remove('open');

    const pnlStr = (res.pnl >= 0 ? '+' : '') + fmtVND(res.pnl || 0);

    toast('ok', `✅ Bán ${_sellCryptoSym} — Thu về ${fmtVND(res.net_vnd)} · PnL: ${pnlStr}`);

    loadDigitalAssets();

  } catch(e) { toast('err', '❌ ' + e.message); }

}



// ── Stake Modal ────────────────────────────────────────────────

function openStakeModal(symbol) {

  const h = _cryptoPortfolio.find(h => h.symbol === symbol);

  const a = _cryptoMarket.find(a => a.symbol === symbol);

  if (!h || !a || (a.staking_apy || 0) <= 0) {

    toast('warn', `⚠️ ${symbol} không hỗ trợ staking.`); return;

  }

  _stakeCryptoSym = symbol;

  document.getElementById('stk-emoji').textContent  = h.emoji || '🪙';

  document.getElementById('stk-symbol').textContent = symbol;

  document.getElementById('stk-apy').textContent    = `APY: ${((a.staking_apy||0)*100).toFixed(1)}% / năm`;

  document.getElementById('stk-pct-slider').value   = 50;

  document.getElementById('stk-pct-label').textContent = '50%';

  previewStake();

  document.getElementById('modal-stake-crypto').classList.add('open');

}



function previewStake() {

  const pct = parseInt(document.getElementById('stk-pct-slider').value) || 50;

  document.getElementById('stk-pct-label').textContent = pct + '%';

  const h = _cryptoPortfolio.find(h => h.symbol === _stakeCryptoSym);

  const a = _cryptoMarket.find(a => a.symbol === _stakeCryptoSym);

  if (!h || !a) return;

  const stakeQty  = (h.avail_qty || 0) * pct / 100;

  const annualYield = stakeQty * (a.staking_apy || 0);

  document.getElementById('stk-preview').innerHTML =

    `Stake: <strong>${stakeQty.toFixed(6)} ${_stakeCryptoSym}</strong> · Yield ~${annualYield.toFixed(6)} ${_stakeCryptoSym}/năm`;

}



async function confirmStakeCrypto() {

  const pct = parseInt(document.getElementById('stk-pct-slider').value) || 50;

  if (!_stakeCryptoSym) return;

  try {

    const res = JSON.parse(await B.stakeCrypto(_stakeCryptoSym, pct / 100));

    if (!res.ok) { toast('err', '❌ ' + res.error); return; }

    document.getElementById('modal-stake-crypto').classList.remove('open');

    toast('ok', `🏦 Đã stake ${res.amount.toFixed(6)} ${_stakeCryptoSym} · APY ${((res.apy||0)*100).toFixed(1)}%`);

    loadDigitalAssets();

  } catch(e) { toast('err', '❌ ' + e.message); }

}



// ── Unstake ────────────────────────────────────────────────────

async function doUnstake(stakeId) {

  try {

    const res = JSON.parse(await B.unstakeCrypto(stakeId));

    if (!res.ok) { toast('err', '❌ ' + res.error); return; }

    toast('ok', `📤 Rút stake thành công! Yield: +${res.yield_units.toFixed(6)} ${res.symbol}`);

    loadDigitalAssets();

  } catch(e) { toast('err', '❌ ' + e.message); }

}



// ── Crypto Detail ──────────────────────────────────────────────

async function showCryptoDetail(symbol) {

  const asset = _cryptoMarket.find(a => a.symbol === symbol);

  if (!asset) return;

  _detailCryptoSym = symbol;

  document.getElementById('cd-emoji').textContent    = asset.emoji || '🪙';

  document.getElementById('cd-symbol').textContent   = symbol;

  document.getElementById('cd-name').textContent     = asset.name_vi || asset.name;

  document.getElementById('cd-price').textContent    = fmtVND(asset.price);

  const chg = asset.change_pct || 0;

  const chgEl = document.getElementById('cd-change');

  chgEl.textContent = (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%';

  chgEl.style.color = chg >= 0 ? 'var(--green)' : 'var(--red)';

  document.getElementById('cd-category').textContent    = asset.category;

  document.getElementById('cd-exchange-label').textContent = '📍 ' + (asset.exchange || '') + (asset.staking_apy > 0 ? ` · 🏦 Staking APY ${((asset.staking_apy||0)*100).toFixed(1)}%` : '');

  document.getElementById('modal-crypto-detail').classList.add('open');



  // Load price history

  try {

    const histRaw = JSON.parse(await B.getCryptoHistory(symbol, 50));

    if (histRaw.ok && histRaw.data && histRaw.data.length > 1) {

      renderCryptoChart('cd-chart', histRaw.data);

    }

  } catch(e) {}

}



function renderCryptoChart(containerId, data) {

  const container = document.getElementById(containerId);

  if (!container || !data.length) return;

  const prices = data.map(d => d[1]);

  const minP   = Math.min(...prices);

  const maxP   = Math.max(...prices);

  const range  = maxP - minP || 1;

  container.innerHTML = prices.map((p, i) => {

    const h   = Math.max(4, Math.round(((p - minP) / range) * 100));

    const chg = i > 0 ? p - prices[i-1] : 0;

    const col = chg >= 0 ? 'var(--green)' : 'var(--red)';

    return `<div style="flex:1;height:${h}%;background:${col};border-radius:2px 2px 0 0;min-height:4px;transition:height .3s" title="${fmtVND(p)}"></div>`;

  }).join('');

}



// ── Tab switching ──

function switchStockTab(tab) {

  document.querySelectorAll('.stock-tab').forEach(t => t.classList.remove('active'));

  document.getElementById('stab-' + tab).classList.add('active');

  document.querySelectorAll('.stock-panel').forEach(p => p.classList.remove('active'));

  document.getElementById('spanel-' + tab).classList.add('active');

  // Dùng dữ liệu đã cache từ loadAllStockData() — fix bất đồng bộ

  if (tab === 'portfolio') {

    if (_stockPortfolio && _stockPortfolio.length) renderPortfolio();

    else loadAllStockData();

  }

  if (tab === 'txns') {

    // Transactions đã được render sẵn trong loadAllStockData, chỉ refresh nếu chưa có

    const txnEl = document.getElementById('stock-txn-list');

    if (!txnEl || !txnEl.children.length || txnEl.innerHTML.includes('Chưa có')) {

      loadAllStockData();

    }

  }

  if (tab === 'events') {

    loadDividendData();

  }

}



// ── Dividend & Corporate Actions ──────────────────

let _divTab = 'history';



function switchDivTab(tab) {

  _divTab = tab;

  document.getElementById('div-tab-history').classList.toggle('active', tab === 'history');

  document.getElementById('div-tab-corp').classList.toggle('active', tab === 'corp');

  document.getElementById('div-history-list').style.display = tab === 'history' ? 'block' : 'none';

  document.getElementById('div-corp-list').style.display = tab === 'corp' ? 'block' : 'none';

}



async function loadDividendData() {

  // Load dividend summary

  try {

    const raw = JSON.parse(await B.getDividendSummary());

    if (raw.ok) {

      document.getElementById('div-total-received').textContent = fmt(raw.total_received || 0);

      document.getElementById('div-avg-yield').textContent = (raw.avg_yield_pct || 0).toFixed(2) + '%';

      document.getElementById('div-symbol-count').textContent = raw.symbol_count || 0;

    }

  } catch(e) {}



  // Load dividend history

  try {

    const raw = JSON.parse(await B.getDividendHistory());

    if (raw.ok) {

      renderDividendHistory(raw.data || []);

    }

  } catch(e) {}



  // Load corporate action history

  try {

    const raw = JSON.parse(await B.getCorporateActionHistory());

    if (raw.ok) {

      renderCorporateActions(raw.data || []);

    }

  } catch(e) {}

}



function renderDividendHistory(data) {

  const el = document.getElementById('div-history-list');

  if (!data.length) {

    el.innerHTML = '<div class="empty"><div class="ei">💰</div><div>Chưa có cổ tức nào</div><div style="font-size:12px;color:var(--muted2)">Cổ tức được trả tự động mỗi phiên giao dịch</div></div>';

    return;

  }

  el.innerHTML = data.slice(0, 50).map(d => {

    const date = d.date || d.time || '';

    return `<div class="stock-txn-item" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-bottom:1px solid var(--border);font-size:13px">

      <span style="font-size:20px">💰</span>

      <div style="flex:1;min-width:0">

        <div style="font-weight:700">${d.symbol || '—'}</div>

        <div style="font-size:11px;color:var(--muted2)">${date}</div>

      </div>

      <div style="text-align:right">

        <div style="font-weight:800;color:var(--green)">+${fmt(d.amount || 0)}</div>

        <div style="font-size:11px;color:var(--muted2)">${(d.yield_pct || 0).toFixed(2)}%</div>

      </div>

    </div>`;

  }).join('');

  if (data.length > 50) {

    el.innerHTML += `<div style="text-align:center;padding:8px;font-size:11px;color:var(--muted2)">... và ${data.length - 50} khoản cổ tức khác</div>`;

  }

}



function renderCorporateActions(data) {

  const el = document.getElementById('div-corp-list');

  if (!data.length) {

    el.innerHTML = '<div class="empty"><div class="ei">🏢</div><div>Chưa có sự kiện doanh nghiệp nào</div></div>';

    return;

  }

  el.innerHTML = data.slice(0, 30).map(d => {

    const type = d.type || '';

    let icon = '🏢', label = '', detail = '';

    if (type === 'split') {

      icon = '🔀'; label = 'Chia tách cổ phiếu';

      detail = `${d.old_shares||0} → ${d.new_shares||0} cp · Điều chỉnh giá vốn`;

    } else if (type === 'bonus') {

      icon = '🎁'; label = 'Cổ phiếu thưởng';

      detail = `Nhận ${fmt(d.bonus_shares||0)} cp · Giá vốn điều chỉnh: ${fmt(d.avg_cost||0)}`;

    } else if (type === 'rights') {

      icon = '📋'; label = 'Phát hành quyền mua';

      detail = `Mua ${fmt(d.rights_shares||0)} cp giá ${fmt(d.rights_price||0)} · Tổng: ${fmt(d.cost||0)}`;

    }

    const date = d.date || d.time || '';

    return `<div class="stock-txn-item" style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-bottom:1px solid var(--border);font-size:13px">

      <span style="font-size:20px">${icon}</span>

      <div style="flex:1;min-width:0">

        <div style="font-weight:700">${d.symbol || '—'} · ${label}</div>

        <div style="font-size:11px;color:var(--muted2)">${detail}</div>

        <div style="font-size:10px;color:var(--muted)">${date}</div>

      </div>

    </div>`;

  }).join('');

  if (data.length > 30) {

    el.innerHTML += `<div style="text-align:center;padding:8px;font-size:11px;color:var(--muted2)">... và ${data.length - 30} sự kiện khác</div>`;

  }

}



function renderStockGrid() {

  const q = (document.getElementById('stock-search').value || '').toLowerCase();

  const sector = document.getElementById('stock-sector-filter').value;

  let list = _stockData.filter(s => {

    if (sector !== 'all' && s.sector !== sector) return false;

    if (q && !s.symbol.toLowerCase().includes(q) && !(s.company||'').toLowerCase().includes(q)) return false;

    return true;

  });



  // Sort

  if (_stockSort === 'symbol') list.sort((a, b) => a.symbol.localeCompare(b.symbol));

  else if (_stockSort === 'change') list.sort((a, b) => (b.change_pct||0) - (a.change_pct||0));

  else if (_stockSort === 'price') list.sort((a, b) => (b.price||0) - (a.price||0));



  const el = document.getElementById('stock-grid');

  if (!list.length) {

    el.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--muted2);padding:30px">🔍 Không tìm thấy mã nào</div>';

    return;

  }

  el.innerHTML = list.map(s => {

    const cls = s.change > 0 ? 'up' : s.change < 0 ? 'dn' : 'flat';

    const pCls = s.change > 0 ? 'up' : s.change < 0 ? 'dn' : '';

    const chgStr = (s.change >= 0 ? '+' : '') + (s.change||0).toFixed(2) + ' (' + (s.change_pct >= 0 ? '+' : '') + (s.change_pct||0).toFixed(2) + '%)';

    return `<div class="stock-card ${cls}">

      <div class="sc-top">

        <div>

          <div class="sc-symbol">${s.symbol}</div>

          <div class="sc-company">${s.company||'—'}</div>

        </div>

        <div style="text-align:right">

          <div class="sc-price ${pCls}">${(s.price||0).toLocaleString()}</div>

          <div class="sc-change ${pCls}">${chgStr}</div>

        </div>

      </div>

      <div class="sc-meta">

        <span>📊 ${(s.volume||0).toLocaleString()}</span>

      </div>

      <div class="sc-sector">🏭 ${s.sector||'—'}</div>

      <div class="sc-actions">

        <button class="btn" style="flex:1" onclick="openBuyModal('${s.symbol}')">🟢 Mua</button>

        <button class="btn btn-ghost" style="flex:1" onclick="openSellModal('${s.symbol}')">🔴 Bán</button>

        <button class="btn btn-ghost" style="flex:0;padding:5px 10px" onclick="showStockDetail('${s.symbol}')">📊</button>

      </div>

    </div>`;

  }).join('');

}



function filterStocks() { renderStockGrid(); }



function sortStocks(by) {

  _stockSort = by;

  document.querySelectorAll('.stock-sort-btn').forEach(b => b.classList.toggle('active', b.dataset.sort === by));

  renderStockGrid();

}



function updateStockOverview() {

  const total = _stockData.length;

  const adv = _stockData.filter(s => (s.change||0) > 0).length;

  const dec = _stockData.filter(s => (s.change||0) < 0).length;

  const flat = total - adv - dec;

  const vol = _stockData.reduce((sum, s) => sum + (s.volume||0), 0);

  document.getElementById('sov-count').textContent = total;

  document.getElementById('sov-advancers').textContent = adv;

  document.getElementById('sov-decliners').textContent = dec;

  document.getElementById('sov-unchanged').textContent = flat;

  document.getElementById('sov-volume').textContent = vol >= 1000000 ? (vol/1000000).toFixed(1)+'M' : vol >= 1000 ? (vol/1000).toFixed(1)+'K' : vol;

}



// ── Buy Modal ──

function openBuyModal(symbol) {

  _buySymbol = symbol;

  const s = _stockData.find(x => x.symbol === symbol);

  if (!s) { toast('err', '❌ Không tìm thấy mã ' + symbol); return; }

  document.getElementById('bs-symbol').textContent = s.symbol;

  document.getElementById('bs-company').textContent = s.company || '';

  document.getElementById('bs-price').textContent = (s.price||0).toLocaleString();

  document.getElementById('bs-shares').value = 1;

  previewBuy();

  document.getElementById('modal-buy-stock').classList.add('open');

}



function closeBuyModal() {

  document.getElementById('modal-buy-stock').classList.remove('open');

  _buySymbol = null;

}



function previewBuy() {

  const s = _stockData.find(x => x.symbol === _buySymbol);

  if (!s) return;

  const shares = parseInt(document.getElementById('bs-shares').value) || 0;

  const total = shares * (s.price||0);

  document.getElementById('bs-total').textContent = total.toLocaleString();

  document.getElementById('bs-balance').textContent = (curBal || 0).toLocaleString();

  document.getElementById('bs-confirm-btn').disabled = (shares < 1 || total > (curBal || 0));

}



async function confirmBuy() {

  const shares = parseInt(document.getElementById('bs-shares').value) || 0;

  if (shares < 1) { toast('err', '❌ Số lượng không hợp lệ'); return; }

  try {

    const raw = JSON.parse(await B.buyStock(_buySymbol, shares));

    if (raw.ok) {

      toast('ok', `🟢 Mua thành công ${shares} cp ${_buySymbol}`);

      closeBuyModal();

      await refreshBalance();

      loadAllStockData();

    } else {

      toast('err', '❌ ' + (raw.error || 'Giao dịch thất bại'));

    }

  } catch (e) {

    toast('err', '❌ Lỗi: ' + e.message);

  }

}



// ── Sell Modal ──

function openSellModal(symbol) {

  _sellSymbol = symbol;

  // Ưu tiên tìm trong _stockData (market), fallback sang portfolio

  let s = _stockData.find(x => x.symbol === symbol);

  const h = _stockPortfolio.find(x => x.symbol === symbol);

  if (!s && h) {

    // Tạo object tạm từ portfolio data nếu market chưa load

    s = {

      symbol:  h.symbol,

      company: h.company || h.company_name || '',

      price:   h.current_price || 0,

      change:  h.change || 0,

    };

  }

  if (!s) { toast('err', '❌ Không tìm thấy mã ' + symbol); return; }

  document.getElementById('ss-symbol').textContent = s.symbol;

  document.getElementById('ss-company').textContent = s.company || '';

  document.getElementById('ss-price').textContent = (s.price||0).toLocaleString();



  const maxShares = h ? (h.shares||0) : 0;

  document.getElementById('ss-max-shares').textContent = maxShares;

  document.getElementById('ss-avgcost').textContent = h ? (h.avg_cost||0).toLocaleString() : '—';



  document.getElementById('ss-shares').value = Math.min(1, maxShares);

  previewSell();

  document.getElementById('modal-sell-stock').classList.add('open');

}



function closeSellModal() {

  document.getElementById('modal-sell-stock').classList.remove('open');

  _sellSymbol = null;

}



function previewSell() {

  let s = _stockData.find(x => x.symbol === _sellSymbol);

  const h = _stockPortfolio.find(x => x.symbol === _sellSymbol);

  // Fallback từ portfolio nếu market chưa load

  if (!s && h) {

    s = {

      symbol:  h.symbol,

      price:   h.current_price || 0,

    };

  }

  if (!s) return;

  const shares = parseInt(document.getElementById('ss-shares').value) || 0;

  const total = shares * (s.price||0);

  document.getElementById('ss-total').textContent = total.toLocaleString();

  const maxShares = h ? (h.shares||0) : 0;

  document.getElementById('ss-confirm-btn').disabled = (shares < 1 || shares > maxShares);

}



async function confirmSell() {

  const shares = parseInt(document.getElementById('ss-shares').value) || 0;

  if (shares < 1) { toast('err', '❌ Số lượng không hợp lệ'); return; }

  try {

    const raw = JSON.parse(await B.sellStock(_sellSymbol, shares));

    if (raw.ok) {

      toast('ok', `🔴 Bán thành công ${shares} cp ${_sellSymbol}`);

      closeSellModal();

      await refreshBalance();

      // Dùng combined API — đồng bộ hoàn toàn

      loadAllStockData();

    } else {

      toast('err', '❌ ' + (raw.error || 'Giao dịch thất bại'));

    }

  } catch (e) {

    toast('err', '❌ Lỗi: ' + e.message);

  }

}



// ── Stock Detail Modal ──

async function showStockDetail(symbol) {

  try {

    const raw = JSON.parse(await B.getStockHistory(symbol, 50));

    if (!raw.ok) { toast('err', '❌ ' + raw.error); return; }

    const history = raw.data || [];

    const s = _stockData.find(x => x.symbol === symbol);

    if (!s) return;



    document.getElementById('sd-symbol').textContent = symbol;

    document.getElementById('sd-company').textContent = s.company || '';

    document.getElementById('sd-price').textContent = (s.price||0).toLocaleString();

    const chgStr = (s.change >= 0 ? '+' : '') + (s.change||0).toFixed(2);

    document.getElementById('sd-change').textContent = chgStr;

    document.getElementById('sd-change').style.color = s.change >= 0 ? 'var(--green)' : 'var(--red)';

    document.getElementById('sd-sector').textContent = s.sector || '—';



    // Mini sparkline

    const chartEl = document.getElementById('sd-chart');

    if (history.length > 1) {

      const prices = history.map(h => h.price || 0);

      const maxP = Math.max(...prices);

      const minP = Math.min(...prices);

      const range = maxP - minP || 1;

      chartEl.innerHTML = prices.map((p, idx) => {

        const hgt = ((p - minP) / range * 100);

        const isUp = idx === 0 || p >= prices[idx - 1];

        const barColor = isUp ? 'var(--green)' : 'var(--red)';

        return `<div style="flex:1;height:100%;display:flex;align-items:flex-end;justify-content:center">

          <div style="width:60%;background:${barColor};border-radius:2px 2px 0 0;height:${hgt}%;min-height:2px"></div>

        </div>`;

      }).join('');

    } else {

      chartEl.innerHTML = '<div style="text-align:center;width:100%;color:var(--muted2);padding:30px">Chưa có dữ liệu lịch sử</div>';

    }



    document.getElementById('modal-stock-detail').classList.add('open');

  } catch (e) {

    toast('err', '❌ Lỗi tải chi tiết');

  }

}



function closeStockDetail() {

  document.getElementById('modal-stock-detail').classList.remove('open');

}



