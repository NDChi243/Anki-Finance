// ════════════════════════════════════════════
//  TICKER — Centralized RAF/Interval Ticker Manager
//  Quản lý tất cả tickers trong app
//  - register(name, config): đăng ký ticker
//  - start(name)/stop(name): bật/tắt
//  - unregister(name): xóa hoàn toàn
// ════════════════════════════════════════════
//  Load sau tycoon-anim.js, trước các tab files
// ════════════════════════════════════════════

window.TycoonTicker = (() => {
  // ── Internal Registry ──────────────────
  // Map<name, { rafId, intervalId, callback, condition, useRAF, lastSecond, lastPaintMs }>
  const _registry = new Map();

  // ── Countdown Utilities ────────────────
  function formatCountdown(totalSeconds) {
    if (totalSeconds == null || totalSeconds < 0) return '--:--:--';
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  }

  // ── Internal: RAF loop ─────────────────
  function _startRafLoop(name) {
    const entry = _registry.get(name);
    if (!entry || entry.rafId) return; // already running

    const tick = (now) => {
      // Kiểm tra nếu đã bị unregister giữa chừng
      const current = _registry.get(name);
      if (!current) return;

      // Kiểm tra condition (nếu có)
      if (typeof current.condition === 'function' && !current.condition()) {
        // Condition fail → dừng loop nhưng giữ registry
        current.rafId = null;
        return;
      }

      // Gọi callback
      try {
        current.callback(now);
      } catch (e) {
        console.error('[Ticker] Error in', name, e);
      }

      // Request next frame
      current.rafId = requestAnimationFrame(tick);
    };

    entry.rafId = requestAnimationFrame(tick);
  }

  // ── Public API ─────────────────────────
  return {
    /**
     * Đăng ký một ticker mới.
     * @param {string} name        - Tên duy nhất (ví dụ 'boost-strip', 'stock-session')
     * @param {object} config
     * @param {function} config.callback    - Hàm được gọi mỗi frame/interval
     * @param {function} [config.condition] - Hàm trả về true nếu ticker nên chạy
     * @param {boolean} [config.useRAF=true] - true = requestAnimationFrame, false = setInterval(1000)
     */
    register(name, config) {
      if (_registry.has(name)) {
        console.warn('[Ticker] Overwriting existing ticker:', name);
        this.unregister(name);
      }

      _registry.set(name, {
        rafId: null,
        intervalId: null,
        callback: config.callback,
        condition: config.condition || null,
        useRAF: config.useRAF !== false, // default true
        lastSecond: null,
        lastPaintMs: 0
      });

      return this;
    },

    /**
     * Bắt đầu một ticker.
     */
    start(name) {
      const entry = _registry.get(name);
      if (!entry) {
        console.warn('[Ticker] Unknown ticker:', name);
        return this;
      }

      // Nếu đang chạy rồi thì skip
      if (entry.useRAF && entry.rafId) return this;
      if (!entry.useRAF && entry.intervalId) return this;

      if (entry.useRAF) {
        _startRafLoop(name);
      } else {
        // setInterval fallback: 1 giây
        entry.intervalId = setInterval(() => {
          const current = _registry.get(name);
          if (!current) return;
          if (typeof current.condition === 'function' && !current.condition()) return;
          try {
            current.callback(Date.now());
          } catch (e) {
            console.error('[Ticker] Error in', name, e);
          }
        }, 1000);
      }

      return this;
    },

    /**
     * Dừng một ticker (giữ registry).
     */
    stop(name) {
      const entry = _registry.get(name);
      if (!entry) return this;

      if (entry.rafId) {
        cancelAnimationFrame(entry.rafId);
        entry.rafId = null;
      }
      if (entry.intervalId) {
        clearInterval(entry.intervalId);
        entry.intervalId = null;
      }

      return this;
    },

    /**
     * Dừng tất cả tickers.
     */
    stopAll() {
      for (const name of _registry.keys()) {
        this.stop(name);
      }
      return this;
    },

    /**
     * Bắt đầu tất cả tickers đã đăng ký.
     */
    startAll() {
      for (const name of _registry.keys()) {
        this.start(name);
      }
      return this;
    },

    /**
     * Xóa hoàn toàn ticker khỏi registry.
     */
    unregister(name) {
      this.stop(name);
      _registry.delete(name);
      return this;
    },

    /**
     * Kiểm tra ticker có đang chạy không.
     */
    isRunning(name) {
      const entry = _registry.get(name);
      if (!entry) return false;
      return !!(entry.rafId || entry.intervalId);
    },

    /**
     * Lấy danh sách tất cả tickers đã đăng ký.
     */
    listRegistered() {
      return Array.from(_registry.keys());
    },

    /**
     * Lấy entry ticker (để debug).
     */
    getEntry(name) {
      return _registry.get(name) || null;
    }
  };
})();
