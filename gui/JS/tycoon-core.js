// ════════════════════════════════════════════
//  CORE — Constants & Base Helpers
//  Phiên bản dùng chung cho tất cả JS modules
// ════════════════════════════════════════════
//  Load đầu tiên, sau qwebchannel.js
// ════════════════════════════════════════════

window.TycoonCore = (() => {
  // ── Version ─────────────────────────────
  const VERSION = '1.1.8b';

  // ── DOM Helpers ─────────────────────────
  function $(id) {
    return document.getElementById(id);
  }

  function $$(sel) {
    return document.querySelector(sel);
  }

  function $$$(sel) {
    return document.querySelectorAll(sel);
  }

  // ── Page Detection ──────────────────────
  function getActivePage() {
    const active = $$('.page.active');
    if (!active) return null;
    // page-dashboard → 'dashboard'
    return active.id.replace('page-', '');
  }

  function isPageActive(page) {
    const active = $$('.page.active');
    if (!active) return false;
    // page-garage → match page='garage'
    return active.id === 'page-' + page;
  }

  // ── Bridge Caller (safe) ────────────────
  async function bridgeCall(method, ...args) {
    try {
      if (!window.B) {
        console.warn('[Core] Bridge not ready for:', method);
        return { ok: false, error: 'Bridge not ready' };
      }
      const raw = await window.B[method](...args);
      // Python bridge trả về JSON string hoặc object
      if (typeof raw === 'string') {
        return JSON.parse(raw);
      }
      return raw;
    } catch (e) {
      console.error('[Core] Bridge call failed:', method, e);
      return { ok: false, error: e.message };
    }
  }

  // ── Public API ──────────────────────────
  return {
    VERSION,
    $,
    $$,
    $$$,
    getActivePage,
    isPageActive,
    bridge: {
      call: bridgeCall
    }
  };
})();
