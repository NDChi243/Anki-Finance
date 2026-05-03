// ════════════════════════════════════════════

//  STATE

// ════════════════════════════════════════════

let B = null;          // bridge

let allItems = [];     // shop items

let curBal = 0;

let curSavings = 0;

let residenceData = null;

let availableResidences = [];

let selectedResidenceId = '';

let selectedResidencePreview = null;

let loanStatusData = null;

let taxFullData = null;

const RESET_MIN_BALANCE = 50000;



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



