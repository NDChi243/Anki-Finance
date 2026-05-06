// ════════════════════════════════════════════
//  STATE — Centralized State Manager
//  Tất cả global state gom vào TycoonState
// ════════════════════════════════════════════

window.TycoonState = {
  // Bridge (set by tycoon-init.js after QWebChannel setup)
  B: null,

  // Shop
  allItems: [],

  // Balance
  curBal: 0,
  curSavings: 0,

  // Residence
  residenceData: null,
  availableResidences: [],
  selectedResidenceId: '',
  selectedResidencePreview: null,

  // Loans
  loanStatusData: null,

  // Tax
  taxFullData: null,

  // Constants
  RESET_MIN_BALANCE: 50000,

  // ── Balance helpers ─────────────────────
  setBal(v) { this.curBal = v; },
  setSavings(v) { this.curSavings = v; },

  // ── Bridge check ────────────────────────
  isBridgeReady() { return this.B !== null; }
};

// ── Backward compatibility aliases ──────────
// Các tab files cũ vẫn dùng biến global.
// Sau khi refactor từng file, xóa alias tương ứng.
window.B          = TycoonState.B;
window.allItems   = TycoonState.allItems;
window.curBal     = TycoonState.curBal;
window.curSavings = TycoonState.curSavings;
window.residenceData        = TycoonState.residenceData;
window.availableResidences  = TycoonState.availableResidences;
window.selectedResidenceId  = TycoonState.selectedResidenceId;
window.selectedResidencePreview = TycoonState.selectedResidencePreview;
window.loanStatusData       = TycoonState.loanStatusData;
window.taxFullData          = TycoonState.taxFullData;
window.RESET_MIN_BALANCE    = TycoonState.RESET_MIN_BALANCE;

// ── Debounce utility ──────────────────────────

function debounce(fn, ms = 300) {

  let timer;

  return (...args) => {

    clearTimeout(timer);

    timer = setTimeout(() => fn(...args), ms);

  };

}

// ── Throttle utility ──────────────────────────

function throttle(fn, ms = 100) {

  let last = 0;

  return (...args) => {

    const now = Date.now();

    if (now - last >= ms) {

      last = now;

      fn(...args);

    }

  };

}

