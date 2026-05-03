// ════════════════════════════════════════════

//  STOCK MARKET (Phase 1)

// ════════════════════════════════════════════



let _stockData = [];

let _stockPortfolio = [];

let _stockSort = 'symbol';

let _buySymbol = null;

let _sellSymbol = null;



let _stockCountdownInterval = null;



function goStocks() {

  // Dùng combined API để fix bất đồng bộ dữ liệu

  loadAllStockData();

  // Start countdown timer (cập nhật mỗi giây)

  startSessionCountdown();

}



function startSessionCountdown() {

  if (_stockCountdownInterval) clearInterval(_stockCountdownInterval);

  updateSessionTimer(); // cập nhật ngay

  _stockCountdownInterval = setInterval(updateSessionTimer, 1000);

}



function stopSessionCountdown() {

  if (_stockCountdownInterval) {

    clearInterval(_stockCountdownInterval);

    _stockCountdownInterval = null;

  }

}



let _cachedSessionInfo = null;

let _lastSessionFetch = 0;

function updateSessionTimer() {

  const el = document.getElementById('st-countdown');

  const lbl = document.getElementById('st-label');

  if (!el || !lbl) return;

  // Fetch từ bridge mỗi 10 giây, giữa các lần tự countdown local

  const now = Date.now();

  if (now - _lastSessionFetch >= 10000) {

    _lastSessionFetch = now;

    B.getTradingSessionInfo().then(raw => {

      try {

        _cachedSessionInfo = JSON.parse(raw);

        updateTimerDisplay(_cachedSessionInfo, el, lbl);

      } catch(e) {}

    });

  } else if (_cachedSessionInfo) {

    // Countdown local mượt mà mỗi giây

    const info = _cachedSessionInfo;

    if (info.in_session && info.seconds_until_end > 0) {

      info.seconds_until_end--;

    } else if (!info.in_session && info.seconds_until_next > 0) {

      info.seconds_until_next--;

    }

    updateTimerDisplay(info, el, lbl);

  }

}



function updateTimerDisplay(info, el, lbl) {

  if (!info || info.error) {

    el.textContent = '--:--:--';

    el.className = 'st-countdown wait';

    lbl.textContent = '🔄 Phiên giao dịch';

    return;

  }

  if (info.in_session) {

    const sec = info.seconds_until_end || 0;

    const h = Math.floor(sec / 3600);

    const m = Math.floor((sec % 3600) / 60);

    const s = sec % 60;

    el.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;

    el.className = 'st-countdown live';

    lbl.textContent = `🟢 ${info.session_name} - kết thúc sau`;

  } else {

    const sec = info.seconds_until_next || 0;

    const h = Math.floor(sec / 3600);

    const m = Math.floor((sec % 3600) / 60);

    const s = sec % 60;

    el.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;

    el.className = 'st-countdown wait';

    lbl.textContent = `⏳ ${info.session_name} - bắt đầu sau`;

  }

}



// ── Combined All Data (Phase 2 - Fix bất đồng bộ) ──

async function loadAllStockData() {

  try {

    const raw = JSON.parse(await B.getStockAllData());

    if (!raw.ok) { toast('err', '❌ ' + (raw.error || 'Lỗi tải dữ liệu')); return; }



    // Cache market data

    _stockData = raw.market || [];



    // Build sector filter options

    const sectors = [...new Set(_stockData.map(s => s.sector).filter(Boolean))];

    const sel = document.getElementById('stock-sector-filter');

    const curVal = sel.value;

    sel.innerHTML = '<option value="all">🏭 Tất cả</option>' +

      sectors.map(s => `<option value="${s}">${s}</option>`).join('');

    sel.value = curVal;



    renderStockGrid();

    updateStockOverview();



    // VN-Index summary

    const s = raw.summary || {};

    document.getElementById('stock-vnindex').textContent = s.vnindex?.toLocaleString() || '—';

    document.getElementById('stock-vnindex').className = 'vnindex ' + ((s.vnindex_change || 0) >= 0 ? 'up' : 'dn');

    document.getElementById('stock-vnchange').textContent =

      ((s.vnindex_change || 0) >= 0 ? '+' : '') + (s.vnindex_change || 0)?.toFixed(2) +

      ' (' + ((s.vnindex_change_pct || 0) >= 0 ? '+' : '') + (s.vnindex_change_pct || 0)?.toFixed(2) + '%)';

    document.getElementById('stock-vnchange').className = 'vnindex-change ' + ((s.vnindex_change || 0) >= 0 ? 'up' : 'dn');

    document.getElementById('stock-vntime').textContent = '🕒 ' + (s.last_updated || '');



    // Portfolio (cached)

    _stockPortfolio = raw.portfolio || [];

    renderPortfolio();



    // Portfolio summary

    const ps = raw.portfolio_summary || {};

    document.getElementById('ps-invested').textContent = (ps.total_invested||0).toLocaleString();

    document.getElementById('ps-marketval').textContent = (ps.total_market_value||0).toLocaleString();

    const pnlEl = document.getElementById('ps-pnl');

    pnlEl.textContent = ((ps.total_pnl||0) >= 0 ? '+' : '') + (ps.total_pnl||0).toLocaleString();

    pnlEl.className = 'ps-val ' + ((ps.total_pnl||0) >= 0 ? 'pos' : 'neg');



    // Transactions

    renderStockTransactions(raw.transactions || []);



    // Trading session

    if (raw.trading_session) {

      const el = document.getElementById('st-countdown');

      const lbl = document.getElementById('st-label');

      if (el && lbl) updateTimerDisplay(raw.trading_session, el, lbl);

    }

  } catch (e) {

    toast('err', '❌ Lỗi tải dữ liệu thị trường');

  }

}



function renderPortfolio() {

  const el = document.getElementById('portfolio-holdings');

  const holdings = _stockPortfolio;

  if (!holdings.length) {

    el.innerHTML = '<div class="empty"><div class="ei">💼</div><div>Chưa có cổ phiếu nào</div><div style="font-size:12px;color:var(--muted2)">Mua ngay từ tab Danh sách!</div></div>';

    return;

  }

  el.innerHTML = holdings.map(h => {

    const pnl = h.pnl||0;

    const pnlPct = h.pnl_pct||0;

    const pnlCls = pnl >= 0 ? 'pos' : 'neg';

    const canSell = h.can_sell !== false;

    const cd = h.cooldown_remaining || 0;

    let cdHtml = '';

    if (!canSell && cd > 0) {

      const cdH = Math.floor(cd / 3600);

      const cdM = Math.floor((cd % 3600) / 60);

      cdHtml = `<span class="cooldown-badge"><span class="cd-icon">🔒</span>T+${h.cooldown_days||2} ${cdH}h${cdM}p</span>`;

    } else if (canSell) {

      cdHtml = `<span class="cooldown-badge ready"><span class="cd-icon">✅</span>Sẵn sàng bán</span>`;

    }

    return `<div class="holding-card">

      <div class="hc-top">

        <div>

          <div class="hc-symbol">${h.symbol} ${cdHtml}</div>

          <div class="hc-company">${h.company||'—'}</div>

        </div>

        <div class="hc-pnl ${pnlCls}">${pnl >= 0 ? '+' : ''}${pnl.toLocaleString()} (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)</div>

      </div>

      <div class="hc-detail">

        <div class="hcd-item"><div class="hcd-val">${(h.shares||0).toLocaleString()}</div><div class="hcd-lbl">Số lượng</div></div>

        <div class="hcd-item"><div class="hcd-val">${(h.avg_cost||0).toLocaleString()}</div><div class="hcd-lbl">Giá vốn TB</div></div>

        <div class="hcd-item"><div class="hcd-val">${(h.current_price||0).toLocaleString()}</div><div class="hcd-lbl">Giá hiện tại</div></div>

        <div class="hcd-item"><div class="hcd-val">${(h.market_value||0).toLocaleString()}</div><div class="hcd-lbl">Giá trị</div></div>

      </div>

      <div style="display:flex;gap:6px;margin-top:4px">

        <button class="btn" style="flex:1;font-size:11px;padding:5px" onclick="openBuyModal('${h.symbol}')">🟢 Mua thêm</button>

        <button class="btn ${canSell ? 'btn-ghost' : ''}" style="flex:1;font-size:11px;padding:5px" onclick="openSellModal('${h.symbol}')"

          ${canSell ? '' : 'disabled title="Đang trong thời gian T+2"'} >

          ${canSell ? '🔴 Bán' : '🔒 T+2'}

        </button>

      </div>

    </div>`;

  }).join('');

}



function renderStockTransactions(txns) {

  const el = document.getElementById('stock-txn-list');

  if (!txns || !txns.length) {

    el.innerHTML = '<div class="empty"><div class="ei">📜</div><div>Chưa có giao dịch nào</div></div>';

    return;

  }

  el.innerHTML = txns.map(t => {

    const tType = t.type === 'buy' ? 'Mua' : 'Bán';

    const tCls = t.type === 'buy' ? 'buy' : 'sell';

    const icon = t.type === 'buy' ? '🟢' : '🔴';

    return `<div class="txn-stock-item">

      <div class="tsi-icon">${icon}</div>

      <div class="tsi-body">

        <span class="tsi-sym">${t.symbol}</span>

        <span style="color:var(--muted2)"> — ${t.shares} cp × ${(t.price||0).toLocaleString()}</span>

        <div style="font-size:10px;color:var(--muted)">${t.date || t.time || ''}</div>

      </div>

      <div class="tsi-type ${tCls}">${tType}</div>

      <div class="tsi-amt">${(t.total||0).toLocaleString()}</div>

    </div>`;

  }).join('');

}



