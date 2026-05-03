// ============================================
//  DASHBOARD
// ============================================

async function loadDashboard() {

  // Combined API: 1 call instead of many smaller calls.
  const raw = JSON.parse(await B.getDashboardData());
  if (!raw.ok) { toast('err', '❌ Lỗi tải dashboard'); return; }

  const { balance, stats: s, streak, rank, quests, goal, again, bank } = raw;

  curBal = balance;
  updateNavBal(balance);

  setAnimatedNumberText(document.getElementById('s-cards'), s.cards_reviewed || 0, { duration: 400 });
  setAnimatedNumberText(document.getElementById('s-earned'), s.total_earned || 0, { format: 'money', duration: 400 });
  setAnimatedNumberText(document.getElementById('s-spent'), s.total_spent || 0, { format: 'money', duration: 400 });
  setAnimatedNumberText(document.getElementById('s-savings'), bank.total_savings || 0, { format: 'money', duration: 400 });
  setAnimatedNumberText(document.getElementById('c1'), s.ease_1 || 0, { suffix: ' lần', duration: 400 });
  setAnimatedNumberText(document.getElementById('c2'), s.ease_2 || 0, { suffix: ' lần', duration: 400 });
  setAnimatedNumberText(document.getElementById('c3'), s.ease_3 || 0, { suffix: ' lần', duration: 400 });
  setAnimatedNumberText(document.getElementById('c4'), s.ease_4 || 0, { suffix: ' lần', duration: 400 });

  updateAgainMonitor(again);
  refreshBoostStrip();

  const gc = document.getElementById('goal-card');
  const ge = document.getElementById('goal-empty-prompt');

  if (goal && goal.has_goal) {

    gc.style.display = 'block';
    ge.style.display = 'none';

    document.getElementById('goal-emoji').textContent = goal.item_emoji || '🎯';
    document.getElementById('goal-name').textContent = goal.item_name || '';
    document.getElementById('goal-pct').textContent = goal.percent + '%';
    document.getElementById('goal-price-info').textContent = 'Giá: ' + fmt(goal.item_price);
    document.getElementById('goal-set-at').textContent = goal.set_at ? 'Đặt lúc ' + goal.set_at : '';

    const bar = document.getElementById('goal-bar');
    const wrap = document.getElementById('goal-progress-wrap');
    bar.style.width = goal.percent + '%';
    wrap.classList.toggle('goal-reached', goal.reached);

    const remaining = document.getElementById('goal-remaining');
    const badge = document.getElementById('goal-reached-badge');

    if (goal.reached) {
      remaining.textContent = '🎉 Đủ tiền mua rồi!';
      remaining.style.color = 'var(--green)';
      badge.style.display = 'inline-flex';
    } else {
      remaining.textContent = `còn thiếu ${fmt(goal.remaining)}`;
      remaining.style.color = 'var(--muted2)';
      badge.style.display = 'none';
    }

  } else {

    gc.style.display = 'none';
    ge.style.display = 'block';

  }

  const fire = streak.streak > 0
    ? (streak.streak >= 30 ? '🔥🔥🔥' : streak.streak >= 7 ? '🔥🔥' : '🔥')
    : '💤';

  document.getElementById('streak-fire').textContent = fire;
  setAnimatedNumberText(document.getElementById('streak-num'), streak.streak || 0, { duration: 400 });
  document.getElementById('streak-mult').textContent = '×' + streak.multiplier.toFixed(1);
  document.getElementById('streak-hint').textContent = streak.streak > 0
    ? `${streak.today_cards}/${streak.min_cards} thẻ hôm nay`
    : (streak.today_cards >= streak.min_cards ? 'Ôn thêm để tính streak mới' : `Cần ${streak.cards_needed} thẻ nữa`);

  const bestEl = document.getElementById('streak-best');
  if (bestEl) bestEl.textContent = streak.best > 0 ? `Kỷ lục: ${streak.best} ngày` : '';

  document.getElementById('rank-emoji-sm').textContent = rank.rank_emoji;
  document.getElementById('rank-label-sm').textContent = rank.rank_label;
  setAnimatedNumberText(document.getElementById('rank-xp-sm'), rank.xp || 0, { format: 'locale', duration: 400 });
  document.getElementById('rank-prog-sm').style.width = rank.overall_pct + '%';
  document.getElementById('rank-prog-sm').style.background = `linear-gradient(90deg,${rank.rank_color},${rank.rank_color}aa)`;

  const mini = document.getElementById('rank-mini');
  if (mini) mini.style.borderColor = rank.rank_color + '66';

  document.getElementById('rank-next-sm').textContent = rank.is_max
    ? '🏆 Rank tối đa!'
    : `Tiếp: ${rank.next_rank?.label} (${rank.overall_pct}%)`;

  const knSmEl = document.getElementById('rank-kn-sm');
  if (knSmEl) {
    const kn = rank.kn || 0;
    setAnimatedNumberText(knSmEl, kn, {
      format: 'locale',
      prefix: '🧠 ',
      suffix: ' KN',
      duration: 400,
    });
  }

  const questList = quests.quests || [];
  const qel = document.getElementById('quest-mini-list');

  if (!questList.length) {
    qel.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Chưa có quest.</div>';
  } else {
    qel.innerHTML = questList.map(q => {
      const pct = q.type === 'no_again_under' || q.type === 'no_purchase' || q.type === 'no_penalty'
        ? (q.done ? 100 : 0)
        : q.target > 0 ? Math.min(100, Math.round(q.progress / q.target * 100)) : 0;
      const col = q.done ? 'var(--green)' : 'var(--accent)';

      return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:16px">${q.emoji || '🎯'}</span>
        <div style="flex:1;min-width:0">
          <div style="font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${q.title}</div>
          <div style="background:var(--surface2);border-radius:3px;height:4px;margin-top:3px;overflow:hidden">
            <div style="height:100%;width:${pct}%;background:${col};border-radius:3px;transition:width .3s"></div>
          </div>
        </div>
        <span style="font-size:11px;font-weight:700;color:${col};flex-shrink:0">${q.done ? '✅' : '' + pct + '%'}</span>
      </div>`;
    }).join('');
  }

  const passiveEffects = raw.passive_effects || [];
  const panel = document.getElementById('passive-panel');
  const list = document.getElementById('passive-effects-list');

  if (passiveEffects.length) {
    panel.style.display = 'block';
    list.innerHTML = passiveEffects.map(p =>
      `<div class="passive-item">
        <span class="pi-icon">${p.emoji || '✨'}</span>
        <span class="pi-name">${p.name}</span>
        <span class="pi-val">${p.description || ''}</span>
      </div>`
    ).join('');
  } else {
    panel.style.display = 'none';
  }

  try {
    const rc = JSON.parse(await B.collectAllRent());
    if (rc.net > 0) toast('ok', `🏠 Thu tiền thuê tự động: +${fmt(rc.net)}`);
  } catch (e) {}

  try {
    const qs = JSON.parse(await B.getQuizStats());
    document.getElementById('dash-quiz-acc').textContent = qs.total > 0 ? qs.accuracy + '%' : '—';
    setAnimatedNumberText(document.getElementById('dash-quiz-streak'), qs.streak || 0, { duration: 400 });
    setAnimatedNumberText(document.getElementById('dash-quiz-total'), qs.total || 0, { duration: 400 });
  } catch (_) {}

  try {
    await refreshAchievementMini();
    if (raw.achievement?.recent?.length) {
      raw.achievement.recent.forEach(a => {
        if (a.unlocked && !a.claimed) showAchievementToast(a);
      });
    }
  } catch (_) {}

}


function updateAgainMonitor(a) {

  const count = a.count || 0;
  const penalty = a.penalty_total || 0;
  const status = a.status || 'normal';
  const maxBar = 65;

  setAnimatedNumberText(document.getElementById('again-count-big'), count, { duration: 400 });
  document.getElementById('again-progress').style.width = Math.min(count / maxBar * 100, 100) + '%';
  document.getElementById('again-penalty-today').textContent = `Phạt hôm nay: ${fmt(penalty)}`;

  const badge = document.getElementById('again-status-badge');
  const hint = document.getElementById('again-hint');
  const mon = document.getElementById('again-monitor');

  if (status === 'heavy') {
    badge.textContent = '🔴 PHẠT NẶNG';
    badge.className = 'badge badge-red';
    hint.textContent = `Phạt ×2 mỗi lần bấm Again! (${count} lần)`;
    mon.style.borderColor = 'var(--red)';
  } else if (status === 'penalty') {
    badge.textContent = '🚨 Đang bị phạt';
    badge.className = 'badge badge-red';
    hint.textContent = 'Mỗi lần Again tiếp theo đều bị phạt tiền!';
    mon.style.borderColor = 'rgba(239,68,68,.5)';
  } else if (status === 'warn') {
    badge.textContent = '⚠️ Cảnh báo';
    badge.className = 'badge badge-yellow';
    hint.textContent = `Còn ${55 - count} lần nữa sẽ bị phạt!`;
    mon.style.borderColor = 'rgba(245,158,11,.5)';
  } else {
    badge.textContent = '✅ Bình thường';
    badge.className = 'badge badge-green';
    hint.textContent = count === 0 ? 'Hôm nay chưa bấm Again 🎉' : `Còn ${50 - count} lần tới ngưỡng cảnh báo`;
    mon.style.borderColor = 'var(--border)';
  }

}
