// ============================================
//  BALANCE
// ============================================

async function refreshBalance() {

  // Always fetch fresh data from Python.
  curBal = await B.getBalance();

  updateNavBal(curBal);

  // Update EXP, KN, rank on navbar at the same time.
  refreshNavExpKnRank();

}


function _setAnimatedMoney(el, value) {

  if (!el) return;

  if (typeof setAnimatedNumberText === 'function') {
    setAnimatedNumberText(el, value, { format: 'money', duration: 400 });
  } else {
    el.textContent = fmt(value);
  }

}


function _setAnimatedLocale(el, value, prefix = '', suffix = '') {

  if (!el) return;

  if (typeof setAnimatedNumberText === 'function') {
    setAnimatedNumberText(el, value, {
      format: 'locale',
      prefix,
      suffix,
      duration: 400,
    });
  } else {
    el.textContent = `${prefix}${Number(value || 0).toLocaleString('vi-VN')}${suffix}`;
  }

}


function updateNavBal(v) {

  _setAnimatedMoney(document.getElementById('nav-bal'), v);
  _setAnimatedMoney(document.getElementById('bal-big'), v);

  let sub = 'Ôn bài chăm chỉ để kiếm thêm tiền!';

  if (_numGte(v, 1000000000000)) sub = '👑 Huyền thoại Phố Wall! Compounding Sage!';
  else if (_numGte(v, 100000000000)) sub = '🌟 Tycoon đỉnh cao - bậc thầy thị trường!';
  else if (_numGte(v, 10000000000)) sub = '🦈 Cá Mập Phố Wall - không gì cản nổi!';
  else if (_numGte(v, 1000000000)) sub = '🚀 Hơn 1 tỷ - Founder thực thụ!';
  else if (_numGte(v, 100000000)) sub = '💎 Hơn 100 triệu - mua xe đi!';
  else if (_numGte(v, 10000000)) sub = '📈 Đang trên đà làm giàu!';
  else if (v == 0 || v === '0') sub = '🌱 Bắt đầu ôn bài để kiếm tiền đầu tiên!';

  document.getElementById('bal-sub').textContent = sub;

  updateResetButtonState();

}


async function refreshNavExpKnRank() {

  try {

    const [expRaw, knRaw, dashRaw] = await Promise.all([
      B.getExp(),
      B.getKN(),
      B.getDashboardData(),
    ]);

    const expData = JSON.parse(expRaw);
    const knData = JSON.parse(knRaw);
    const dashData = JSON.parse(dashRaw);

    const xpEl = document.getElementById('nav-xp');
    const knEl = document.getElementById('nav-kn');
    const rnEl = document.getElementById('nav-rank');

    if (xpEl) {
      const xp = expData.xp || 0;
      _setAnimatedLocale(xpEl, xp, '⭐ ', ' EXP');
    }

    if (knEl) {
      const kn = knData.kn || 0;
      _setAnimatedLocale(knEl, kn, '🧠 ', ' KN');
    }

    if (rnEl && dashData.rank) {
      const r = dashData.rank;
      const emoji = r.rank_emoji || '📚';
      const label = r.rank_label || '—';
      rnEl.textContent = `${emoji} ${label.substring(0, 14)}`;
    }

  } catch (e) {

    console.error('refreshNavExpKnRank error', e);

  }

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
