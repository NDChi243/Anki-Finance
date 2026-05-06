// ============================================
//  PERFORMANCE — RAF-based Ticker Plugin
//  Sử dụng TickerManager thay vì raw RAF/setInterval
// ============================================

// ── Internal State ───────────────────────────
let _stockCountdownLastPaintMs = 0;
let _stockCountdownFetchInFlight = false;
let _stockSessionTargetMs = 0;

let _quizCountdownTargetMs = 0;
let _quizCountdownLastSecond = null;

let _boostStripState = [];
let _boostStripLastSecond = null;
let _perfLastCardsRefresh = 0;


// ════════════════════════════════════════════
//  1. STOCK SESSION TICKER
// ════════════════════════════════════════════

function _syncSessionTimerInfo(info, nowMs = Date.now()) {
  if (!info) return;
  _cachedSessionInfo = { ...info };
  if (info.in_session) {
    _stockSessionTargetMs = nowMs + Math.max(0, Number(info.seconds_until_end || 0)) * 1000;
  } else {
    _stockSessionTargetMs = nowMs + Math.max(0, Number(info.seconds_until_next || 0)) * 1000;
  }
}

function _getLiveSessionInfo(nowMs = Date.now()) {
  if (!_cachedSessionInfo) return null;
  const info = { ..._cachedSessionInfo };
  const remaining = Math.max(0, Math.ceil((_stockSessionTargetMs - nowMs) / 1000));
  if (info.in_session) info.seconds_until_end = remaining;
  else info.seconds_until_next = remaining;
  return info;
}

updateSessionTimer = function() {
  const el = document.getElementById('st-countdown');
  const lbl = document.getElementById('st-label');
  if (!el || !lbl) return;

  const now = Date.now();
  if (!_stockCountdownFetchInFlight && (now - _lastSessionFetch >= 10000 || !_cachedSessionInfo)) {
    _lastSessionFetch = now;
    _stockCountdownFetchInFlight = true;
    B.getTradingSessionInfo().then(raw => {
      try {
        _syncSessionTimerInfo(JSON.parse(raw), Date.now());
        updateTimerDisplay(_getLiveSessionInfo(Date.now()), el, lbl);
      } catch (e) {}
    }).finally(() => {
      _stockCountdownFetchInFlight = false;
    });
  } else if (_cachedSessionInfo) {
    updateTimerDisplay(_getLiveSessionInfo(now), el, lbl);
  }
};

// Legacy wrappers (external code gọi startSessionCountdown / stopSessionCountdown)
startSessionCountdown = function() {
  if (window.TycoonTicker) {
    TycoonTicker.start('stock-session');
  }
};

stopSessionCountdown = function() {
  if (window.TycoonTicker) {
    TycoonTicker.stop('stock-session');
  }
  _stockCountdownLastPaintMs = 0;
};

// Register với TickerManager
if (window.TycoonTicker) {
  TycoonTicker.register('stock-session', {
    callback: (now) => {
      if (!_stockCountdownLastPaintMs || now - _stockCountdownLastPaintMs >= 250) {
        _stockCountdownLastPaintMs = now;
        updateSessionTimer();
      }
    },
    condition: () => TycoonCore.isPageActive('stocks'),
    useRAF: true
  });
}


// ════════════════════════════════════════════
//  2. QUIZ COUNTDOWN TICKER
// ════════════════════════════════════════════

function _formatCountdownClock(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function stopQuizCountdown() {
  if (window.TycoonTicker) {
    TycoonTicker.stop('quiz-countdown');
  }
  _quizCountdownLastSecond = null;
}

function _renderQuizCountdownBadge(badgeEl, remainingSeconds) {
  badgeEl.textContent = `📅 Hết lượt • Mở lại sau ${_formatCountdownClock(remainingSeconds)}`;
}

_startQuizCountdown = function(seconds, badgeEl) {
  stopQuizCountdown();
  _quizCountdownTargetMs = Date.now() + Math.max(0, Number(seconds || 0)) * 1000;

  // Render ngay
  _quizCountdownLastSecond = null;
  _renderQuizCountdownBadge(badgeEl, Math.max(0, Math.ceil((_quizCountdownTargetMs - Date.now()) / 1000)));

  // Register với TickerManager
  if (window.TycoonTicker) {
    TycoonTicker.unregister('quiz-countdown');
    TycoonTicker.register('quiz-countdown', {
      callback: () => {
        if (!badgeEl || !document.body.contains(badgeEl)) {
          stopQuizCountdown();
          return;
        }
        const remaining = Math.max(0, Math.ceil((_quizCountdownTargetMs - Date.now()) / 1000));
        if (remaining <= 0) {
          stopQuizCountdown();
          refreshDailyQuizLimit();
          return;
        }
        if (_quizCountdownLastSecond !== remaining) {
          _quizCountdownLastSecond = remaining;
          _renderQuizCountdownBadge(badgeEl, remaining);
        }
      },
      condition: null, // tự quản lý condition trong callback
      useRAF: true
    });
    TycoonTicker.start('quiz-countdown');
  }
};

refreshDailyQuizLimit = async function() {
  try {
    const raw = await B.getQuizDailyInfo();
    const info = JSON.parse(raw);
    const badge = document.getElementById('quiz-daily-limit-badge');
    if (!badge) return;
    const rem = info.remaining;
    const limit = info.limit;
    const count = info.count || info.correct_today || 0;

    if (rem <= 0) {
      badge.className = 'badge badge-red';
      const secs = info.next_reset_seconds || 0;
      if (secs > 0) {
        _startQuizCountdown(secs, badge);
      } else {
        stopQuizCountdown();
        badge.textContent = `📅 Hết lượt hôm nay (${count}/${limit})`;
      }
    } else {
      stopQuizCountdown();
      badge.className = 'badge badge-green';
      badge.textContent = `📅 Hôm nay: ${count}/${limit}  •  Còn ${rem} lượt`;
    }
  } catch (e) {
    console.error('refreshDailyQuizLimit error', e);
  }
};


// ════════════════════════════════════════════
//  3. BOOST STRIP TICKER
// ════════════════════════════════════════════

function _renderBoostStrip(listEl) {
  const now = Date.now();
  const activeBoosts = _boostStripState.filter(b => {
    if (b.expiresAtMs !== null && b.expiresAtMs !== undefined) {
      return b.expiresAtMs > now;
    }
    if (b.cards_left !== null && b.cards_left !== undefined) {
      return b.cards_left > 0;
    }
    return true;
  });

  if (!activeBoosts.length) {
    const strip = document.getElementById('boost-strip');
    if (strip) strip.style.display = 'none';
    listEl.innerHTML = '';
    _boostStripState = [];
    stopGarageBoostTicker();
    return;
  }

  listEl.innerHTML = activeBoosts.map(b => {
    let timer = '';
    if (b.expiresAtMs !== null && b.expiresAtMs !== undefined) {
      const remaining = Math.max(0, Math.ceil((b.expiresAtMs - Date.now()) / 1000));
      const m = Math.floor(remaining / 60);
      const s = remaining % 60;
      timer = m > 0 ? `${m}p${s}s` : `${s}s`;
    } else if (b.cards_left !== null && b.cards_left !== undefined) {
      timer = `còn ${b.cards_left} thẻ`;
    }
    const desc = b.desc ? ` — ${b.desc}` : '';
    const slotId = (b.id || '').replace(/'/g, "\\'");
    return `<span style="margin-left:8px;color:var(--green)">${b.name}</span><span style="color:var(--muted2);font-size:11px">${desc}</span> <span style="color:var(--muted2)">(${timer})</span>` +
      `<button class="btn btn-ghost" style="font-size:10px;padding:2px 6px;margin-left:4px;color:var(--red)" onclick="deactivateBoostConfirm('${slotId}')">❌ Hủy</button>`;
  }).join(' |');
}

// ── Deactivate Boost ──
async function deactivateBoostConfirm(slotId) {
  const boost = _boostStripState.find(b => b.id === slotId);
  if (!boost) return;
  const name = boost.name || 'vật phẩm';

  let cancelInfo = { remaining: '...', limit: '...', cards_needed_for_next: 0, total_valid_cards: 0 };
  try {
    const raw = await B.getDailyCancelInfo();
    cancelInfo = JSON.parse(raw);
  } catch (e) {}

  const remaining = cancelInfo.remaining;
  const limit = cancelInfo.limit;
  const cardsNeeded = cancelInfo.cards_needed_for_next || 0;
  const validCards = cancelInfo.total_valid_cards || 0;

  let progressText = '';
  if (limit > 10) {
    const extraFromCards = limit - 10;
    progressText = `<span style="font-size:11px;color:var(--muted2)">📊 Học thêm <strong>${cardsNeeded}</strong> thẻ hợp lệ (≥10s) để mở thêm 1 lượt hủy</span>`;
  } else if (cardsNeeded > 0) {
    progressText = `<span style="font-size:11px;color:var(--muted2)">📊 Học <strong>${cardsNeeded}</strong> thẻ hợp lệ (≥10s) nữa để mở rộng limit (hiện tại ${validCards} thẻ)</span>`;
  } else {
    progressText = `<span style="font-size:11px;color:var(--green)">✅ Đã đạt giới hạn hủy tối đa ${limit}/ngày!</span>`;
  }

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay open';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:600;display:flex;align-items:center;justify-content:center';
  overlay.innerHTML = `<div class="modal" style="max-width:420px">
    <div class="row-sb" style="margin-bottom:14px">
      <h3>⚠️ Hủy kích hoạt</h3>
      <button class="btn btn-ghost" style="font-size:12px;padding:4px 10px" onclick="this.closest('.modal-overlay').remove()">✕</button>
    </div>
    <p style="font-size:13px;color:var(--muted2);margin-bottom:10px;line-height:1.6">
      Bạn có chắc muốn hủy <strong>${name}</strong>?
    </p>
    <div style="background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.3);border-radius:8px;padding:10px 12px;margin-bottom:10px;font-size:12px;color:var(--muted2);line-height:1.5">
      📋 Lượt hủy hôm nay: <strong style="color:${remaining > 0 ? 'var(--green)' : 'var(--red)'}">${remaining}/${limit}</strong>
    </div>
    <div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);border-radius:8px;padding:10px 12px;margin-bottom:14px;font-size:12px;color:var(--muted2);line-height:1.5">
      ⛔ Toàn bộ hiệu ứng của vật phẩm sẽ bị hủy.<br>
      💸 Sẽ <strong>không được hoàn lại tiền</strong>.
    </div>
    <div style="margin-bottom:14px;font-size:11px;color:var(--muted2);line-height:1.5">
      ${progressText}
    </div>
    <div class="modal-footer" style="gap:8px">
      <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()" style="flex:1">Đóng</button>
      <button class="btn" style="flex:1;background:var(--red);color:#fff" onclick="confirmDeactivateBoost('${slotId.replace(/'/g, "\\'")}')">Xác nhận hủy</button>
    </div>
  </div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
}

async function confirmDeactivateBoost(slotId) {
  document.querySelectorAll('.modal-overlay').forEach(el => el.remove());
  const res = JSON.parse(await B.deactivateBoost(slotId));
  if (res.ok) {
    toast('ok', `✅ ${res.message || 'Đã hủy kích hoạt!'} (còn ${res.remaining}/${res.limit} lượt hôm nay)`);
    await refreshBoostStrip();
    if (typeof loadInventory === 'function') {
      await loadInventory();
    }
  } else {
    toast('err', '❌ ' + (res.error || 'Không thể hủy kích hoạt'));
  }
}


// ════════════════════════════════════════════
//  4. CANCEL BADGE TICKER
// ════════════════════════════════════════════

let _cancelBadgeLastSecond = null;

async function refreshDailyCancelBadge() {
  try {
    const raw = await B.getDailyCancelInfo();
    const info = JSON.parse(raw);
    const remaining = info.remaining;
    const limit = info.limit;
    const validCards = info.total_valid_cards || 0;
    const extraFromCards = info.extra_from_cards || 0;

    let badge = document.getElementById('daily-cancel-badge');
    if (!badge) {
      const strip = document.getElementById('boost-strip');
      if (!strip || strip.style.display === 'none') return;
      badge = document.createElement('span');
      badge.id = 'daily-cancel-badge';
      badge.style.cssText = 'display:inline-block;font-size:10px;padding:1px 6px;border-radius:20px;margin-left:6px;vertical-align:middle';
      const list = document.getElementById('boost-strip-list');
      if (list && list.parentNode) {
        list.parentNode.insertBefore(badge, list.nextSibling);
      }
    }

    if (remaining <= 0) {
      badge.textContent = `🚫 Hết lượt hủy (${limit}/${limit})`;
      badge.style.background = 'rgba(239,68,68,.15)';
      badge.style.color = '#ef4444';
      badge.style.border = '1px solid rgba(239,68,68,.3)';
    } else if (extraFromCards > 0) {
      badge.textContent = `📋 Còn ${remaining}/${limit} lượt hủy (➕${extraFromCards} từ học thẻ)`;
      badge.style.background = 'rgba(59,130,246,.12)';
      badge.style.color = '#60a5fa';
      badge.style.border = '1px solid rgba(59,130,246,.25)';
    } else {
      badge.textContent = `📋 Còn ${remaining}/${limit} lượt hủy`;
      badge.style.background = 'rgba(59,130,246,.12)';
      badge.style.color = '#60a5fa';
      badge.style.border = '1px solid rgba(59,130,246,.25)';
    }
  } catch (e) {
    console.error('refreshDailyCancelBadge error', e);
  }
}

// Register cancel badge ticker
if (window.TycoonTicker) {
  TycoonTicker.register('cancel-badge', {
    callback: () => {
      const secondStamp = Math.floor(Date.now() / 1000);
      if (_cancelBadgeLastSecond !== secondStamp) {
        _cancelBadgeLastSecond = secondStamp;
        refreshDailyCancelBadge();
      }
    },
    condition: null, // tự check visibility trong callback
    useRAF: true
  });
}

function startCancelBadgeTicker() {
  _cancelBadgeLastSecond = null;
  if (window.TycoonTicker) {
    TycoonTicker.start('cancel-badge');
  }
}

function stopCancelBadgeTicker() {
  if (window.TycoonTicker) {
    TycoonTicker.stop('cancel-badge');
  }
  _cancelBadgeLastSecond = null;
}


// ════════════════════════════════════════════
//  5. BOOST STRIP — Core Functions
// ════════════════════════════════════════════

function stopGarageBoostTicker() {
  // Legacy cleanup: clear cả interval và RAF (đề phòng conflict cũ)
  if (window.boostTickerInterval) {
    clearInterval(window.boostTickerInterval);
    cancelAnimationFrame(window.boostTickerInterval);
    window.boostTickerInterval = null;
  }
  if (window.TycoonTicker) {
    TycoonTicker.stop('boost-strip');
  }
  _boostStripLastSecond = null;
}

// Register boost strip ticker với TickerManager
if (window.TycoonTicker) {
  TycoonTicker.register('boost-strip', {
    callback: () => {
      const secondStamp = Math.floor(Date.now() / 1000);
      if (_boostStripLastSecond !== secondStamp) {
        _boostStripLastSecond = secondStamp;

        const listEl = document.getElementById('boost-strip-list');
        if (!listEl) return;

        // Refresh cards_left từ backend (mỗi 3 giây)
        const hasCardsBoosts = _boostStripState.some(b => b.cards_left !== null && b.cards_left !== undefined);
        if (hasCardsBoosts && Date.now() - _perfLastCardsRefresh > 3000) {
          _perfLastCardsRefresh = Date.now();
          B.getActiveBoosts().then(raw => {
            try {
              const fresh = JSON.parse(raw);
              fresh.forEach(fb => {
                const existing = _boostStripState.find(b => b.id === fb.id);
                if (existing) existing.cards_left = fb.cards_left;
              });
            } catch (_) {}
          }).catch(() => {});
        }

        _renderBoostStrip(listEl);
      }
    },
    condition: null, // Luôn chạy (kể cả khi không ở garage) — timer cần đếm ngược liên tục
    useRAF: true
  });
}

refreshBoostStrip = async function() {
  const boosts = JSON.parse(await B.getActiveBoosts());
  const strip = document.getElementById('boost-strip');
  const list = document.getElementById('boost-strip-list');

  if (!boosts.length) {
    strip.style.display = 'none';
    _boostStripState = [];
    stopGarageBoostTicker();
    stopCancelBadgeTicker();
    return;
  }

  _boostStripState = boosts.map(b => ({
    ...b,
    expiresAtMs: b.remaining_s !== null && b.remaining_s !== undefined
      ? Date.now() + Math.max(0, Number(b.remaining_s || 0)) * 1000
      : null,
  }));

  strip.style.display = 'block';
  _renderBoostStrip(list);
  startCancelBadgeTicker();

  // Boost ticker luôn chạy trên mọi page — timer đếm ngược liên tục
  if (window.TycoonTicker) {
    TycoonTicker.start('boost-strip');
  }
};


// ════════════════════════════════════════════
//  6. HOOK: Load Garage → Refresh Boost Strip
// ════════════════════════════════════════════

if (typeof loadGarage === 'function') {
  const _loadGarageOriginal = loadGarage;
  loadGarage = async function(...args) {
    const result = await _loadGarageOriginal.apply(this, args);
    try {
      await refreshBoostStrip();
    } catch (e) {}
    return result;
  };
}
