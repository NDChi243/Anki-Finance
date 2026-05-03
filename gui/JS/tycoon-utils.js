// ════════════════════════════════════════════

//  UTILS — Safe Big Number Formatting

// ════════════════════════════════════════════



// Format số tiền an toàn, không bị overflow với số > 2^53

// Dùng string manipulation thay vì Number.toLocaleString()

function _fmtSafe(n) {

  if (n === null || n === undefined) n = 0;

  let s = typeof n === 'string' ? n : String(n);

  let neg = false;

  if (s.startsWith('-')) { neg = true; s = s.slice(1); }

  s = s.replace(/[^0-9]/g, '');

  if (!s || s === '0') return '0';

  // Loại bỏ leading zeros

  s = s.replace(/^0+/, '') || '0';

  // Thêm dấu . sau mỗi 3 chữ số từ phải

  let result = '';

  for (let i = s.length - 1, c = 0; i >= 0; i--, c++) {

    if (c > 0 && c % 3 === 0) result = '.' + result;

    result = s[i] + result;

  }

  return (neg ? '-' : '') + result;

}



function fmt(n) {

  return _fmtSafe(n) + ' VND';

}



// So sánh số an toàn (hỗ trợ string)

function _numCmp(a, b) {

  const na = typeof a === 'string' ? BigInt(a.replace(/[^0-9-]/g,'') || '0') : BigInt(a||0);

  const nb = typeof b === 'string' ? BigInt(b.replace(/[^0-9-]/g,'') || '0') : BigInt(b||0);

  if (na > nb) return 1;

  if (na < nb) return -1;

  return 0;

}



function _numGte(a, b) { return _numCmp(a, b) >= 0; }

function _numLt(a, b) { return _numCmp(a, b) < 0; }



function toast(type, msg, ms=3500) {

  const c = document.getElementById('toasts');

  const t = document.createElement('div');

  t.className = 'toast ' + type;

  t.textContent = msg;

  c.appendChild(t);

  setTimeout(() => { t.style.transition='opacity .3s'; t.style.opacity='0'; setTimeout(()=>t.remove(),300); }, ms);

}





