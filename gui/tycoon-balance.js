// ════════════════════════════════════════════

//  BALANCE

// ════════════════════════════════════════════

async function refreshBalance() {

  // REQ1 FIX: luôn fetch trực tiếp từ Python, không cache cũ

  curBal = await B.getBalance();

  updateNavBal(curBal);

}



function updateNavBal(v) {

  document.getElementById('nav-bal').textContent = fmt(v);

  document.getElementById('bal-big').textContent = fmt(v);

  let sub = 'Ôn bài chăm chỉ để kiếm thêm tiền!';

  // Dùng so sánh an toàn với BigInt

  if (_numGte(v, 10000000000)) sub = '🏆 Tỷ phú Anki! Không thể tin được!';

  else if (_numGte(v, 1000000000)) sub = '🚀 Hơn 1 tỷ! Bạn đang giàu lên rồi!';

  else if (_numGte(v, 100000000)) sub = '💎 Hơn 100 triệu — mua xe đi!';

  else if (_numGte(v, 10000000)) sub = '📈 Đang trên đà làm giàu!';

  else if (v == 0 || v === '0')  sub = '🌱 Bắt đầu ôn bài để kiếm tiền đầu tiên!';

  document.getElementById('bal-sub').textContent = sub;

  updateResetButtonState();

}



function getResetDisabledReason() {

  if (curBal < 0) return 'Không thể reset khi tài khoản đang nợ.';

  if (curBal < RESET_MIN_BALANCE) return 'Cần ít nhất 50.000 VND để reset.';

  return '';

}



function updateResetButtonState() {

  const btn = document.getElementById('reset-btn');

  const hint = document.getElementById('reset-btn-hint');

  if (!btn) return;

  const reason = getResetDisabledReason();

  btn.disabled = !!reason;

  btn.title = reason;

  if (hint) {

    hint.textContent = reason || 'Nút reset chỉ mở khi số dư hiện tại từ 50.000 VND trở lên.';

  }

}



