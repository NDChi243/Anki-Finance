// ════════════════════════════════════════════

//  ACHIEVEMENT

// ════════════════════════════════════════════



let achAllData = [];        // full list từ Python

let achFilter = 'all';      // category filter hiện tại

let achCategoryIcons = {};



async function loadAchievements() {

  await refreshBalance();

  try {

    const raw = await B.getAllAchievements();

    const data = JSON.parse(raw);

    if (data.error) { achAllData = []; console.warn('Achievement error:', data.error); return; }

    achAllData = Array.isArray(data) ? data : [];

    renderAchievements();

  } catch (e) {

    console.warn('loadAchievements error:', e);

    achAllData = [];

  }

}



function renderAchievements() {

  const grid = document.getElementById('ach-grid');

  if (!grid) return;



  const list = achAllData;

  const unlocked = list.filter(a => a.unlocked);

  const total = list.length;

  const pct = total > 0 ? Math.round(unlocked.length / total * 100) : 0;



  // Stats

  document.getElementById('ach-unlocked').textContent = unlocked.length;

  document.getElementById('ach-progress-pct').textContent = pct + '%';

  document.getElementById('ach-progress-label').textContent = unlocked.length + ' / ' + total;

  document.getElementById('ach-progress-bar').style.width = pct + '%';



  // Build category filter tabs

  const cats = {};

  list.forEach(a => {

    const cat = a.category || 'Khác';

    if (!cats[cat]) cats[cat] = 0;

    cats[cat]++;

  });

  const filterContainer = document.getElementById('ach-filter-tabs');

  let filterHtml = '<button class="btn btn-sm" data-cat="all" onclick="filterAchievements(\'all\')" style="' +

    (achFilter === 'all' ? 'background:var(--gold);color:#000' : 'background:var(--surface2);color:var(--text)') +

    '">📋 Tất cả (' + total + ')</button>';

  Object.keys(cats).sort().forEach(cat => {

    const isActive = achFilter === cat;

    const emoji = achCategoryIcons[cat] || '🏷️';

    filterHtml += '<button class="btn btn-sm" data-cat="' + cat + '" onclick="filterAchievements(\'' + cat + '\')" style="' +

      (isActive ? 'background:var(--gold);color:#000' : 'background:var(--surface2);color:var(--text)') +

      '">' + emoji + ' ' + cat + ' (' + cats[cat] + ')</button>';

  });

  filterContainer.innerHTML = filterHtml;



  // Filter + render grid

  const filtered = achFilter === 'all' ? list : list.filter(a => (a.category || 'Khác') === achFilter);



  grid.innerHTML = filtered.map(a => {

    const isUnlocked = a.unlocked;

    const canClaim = a.unlocked && !a.claimed;

    const claimed = a.claimed;

    const rewardDesc = buildRewardDesc(a);



    // Card style: unlocked vs locked

    const cardBorder = isUnlocked

      ? 'border-color:rgba(250,204,21,.4);background:rgba(250,204,21,.04)'

      : 'border-color:var(--border)';

    const emojiOpacity = isUnlocked ? '1' : '.35';

    const titleColor = isUnlocked ? 'var(--text)' : 'var(--muted2)';



    // Progress

    let progressHtml = '';

    if (a.progress !== undefined && a.target !== undefined && a.target > 0) {

      const p = Math.min(a.progress / a.target * 100, 100);

      progressHtml = `

        <div style="margin-top:8px">

          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted2);margin-bottom:3px">

            <span>${fmtProgress(a.progress, a.target, a.trigger_type||'')}</span>

            <span>${Math.round(p)}%</span>

          </div>

          <div style="height:5px;background:var(--surface2);border-radius:4px;overflow:hidden">

            <div style="height:100%;width:${p}%;background:${isUnlocked ? 'var(--gold)' : 'var(--blue)'};border-radius:4px;transition:width .4s"></div>

          </div>

        </div>`;

    }



    // Action button

    let actionBtn = '';

    if (canClaim) {

      actionBtn = '<button class="btn btn-sm" onclick="claimAchievement(\'' + a.id + '\')" style="margin-top:8px;background:var(--gold);color:#000;font-weight:700">🎁 Nhận thưởng</button>';

    } else if (claimed) {

      actionBtn = '<div style="margin-top:8px;font-size:11px;color:var(--green);font-weight:700">✅ Đã nhận thưởng</div>';

    }



    // Hidden badge

    const hiddenBadge = a.hidden && !isUnlocked

      ? '<span style="font-size:10px;background:var(--surface2);padding:2px 6px;border-radius:4px;color:var(--muted2)">🔒 Ẩn</span>'

      : '';



    return `

      <div class="card" style="padding:14px;${cardBorder}">

        <div style="display:flex;align-items:flex-start;gap:10px">

          <div style="font-size:28px;opacity:${emojiOpacity}">${a.emoji||'🏆'}</div>

          <div style="flex:1;min-width:0">

            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">

              <span style="font-weight:700;font-size:14px;color:${titleColor}">${isUnlocked || !a.hidden ? a.title : '???'}</span>

              ${hiddenBadge}

            </div>

            <div style="font-size:12px;color:var(--muted2);margin-top:3px">${isUnlocked || !a.hidden ? a.desc : 'Hoàn thành để khám phá!'}</div>

            ${rewardDesc}

            ${progressHtml}

            ${actionBtn}

          </div>

        </div>

      </div>`;

  }).join('') || '<div class="empty" style="grid-column:1/-1"><div class="ei">🏆</div>Không có thành tựu nào.</div>';

}



function filterAchievements(cat) {

  achFilter = cat;

  renderAchievements();

}



function buildRewardDesc(a) {

  const parts = [];

  if (a.reward?.money) parts.push('💰 ' + fmt(a.reward.money));

  if (a.reward?.xp) parts.push('⭐ ' + a.reward.xp + ' XP');

  if (a.effect) {

    const e = a.effect;

    if (e.interest_bonus) parts.push('🏦 Lãi +' + (e.interest_bonus * 100).toFixed(1) + '%');

    if (e.max_energy) parts.push('⚡ NL tối đa +' + e.max_energy);

    if (e.income_bonus) parts.push('📈 Thu nhập +' + (e.income_bonus * 100).toFixed(1) + '%');

    if (e.discount) parts.push('🔖 Giảm ' + (e.discount * 100).toFixed(1) + '%');

  }

  if (!parts.length) return '';

  return '<div style="font-size:11px;color:var(--muted2);margin-top:4px">' + parts.join(' · ') + '</div>';

}



function fmtProgress(progress, target, triggerType) {

  if (triggerType === 'card_reviewed') return '📝 ' + progress + ' / ' + target + ' thẻ';

  if (triggerType === 'streak_updated') return '🔥 ' + progress + ' / ' + target + ' ngày';

  if (triggerType === 'net_worth_updated') return '💰 ' + fmt(progress) + ' / ' + fmt(target);

  if (triggerType === 'total_savings') return '🏦 ' + fmt(progress) + ' / ' + fmt(target);

  if (triggerType === 'stock_traded') return '📈 ' + progress + ' / ' + target + ' GD';

  if (triggerType === 'items_owned') return '🎒 ' + progress + ' / ' + target + ' món';

  if (triggerType === 'quest_claimed') return '📋 ' + progress + ' / ' + target + ' quest';

  if (triggerType === 'emergency_handled') return '🚨 ' + progress + ' / ' + target + ' lần';

  if (triggerType === 'quiz_answered') return '🧠 ' + progress + ' / ' + target + ' câu';

  if (triggerType === 'rank_reached') return '🏅 ' + progress + ' / ' + target;

  return progress + ' / ' + target;

}



async function claimAchievement(id) {

  try {

    const raw = await B.claimAchievementReward(id);

    const res = JSON.parse(raw);

    if (res.ok) {

      toast('success', '🎉 ' + (res.title || 'Thành tựu') + ' — Nhận ' + fmt(res.money || 0) + ' + ' + (res.xp || 0) + ' XP');

      await loadAchievements();

      await refreshBalance();

    } else {

      toast('error', res.error || 'Lỗi nhận thưởng');

    }

  } catch (e) {

    toast('error', 'Lỗi: ' + e.message);

  }

}



// ── Achievement toast notification (gọi từ dashboard khi có thành tựu mới) ──

function showAchievementToast(ach) {

  const area = document.getElementById('ach-toast-area') || document.getElementById('toasts');

  if (!area) return;

  const t = document.createElement('div');

  t.style.cssText = 'background:linear-gradient(135deg,rgba(250,204,21,.15),rgba(245,158,11,.1));border:1px solid rgba(250,204,21,.4);border-radius:12px;padding:12px 16px;backdrop-filter:blur(8px);max-width:320px;animation:slideUp .3s ease';

  t.innerHTML = '<div style="display:flex;align-items:center;gap:10px"><span style="font-size:28px">' + (ach.emoji||'🏆') + '</span><div><div style="font-weight:700;font-size:14px;color:var(--gold)">🏆 Thành tựu mới!</div><div style="font-size:13px;color:var(--text);margin-top:2px">' + (ach.title||'') + '</div></div></div>';

  area.appendChild(t);

  setTimeout(() => { t.style.transition = 'opacity .4s, transform .4s'; t.style.opacity = '0'; t.style.transform = 'translateX(40px)'; setTimeout(() => t.remove(), 400); }, 4000);

}



// ── Refresh dashboard achievement mini-section ──

async function refreshAchievementMini() {

  try {

    const raw = await B.getAchievementStats();

    const s = JSON.parse(raw);

    const el = document.getElementById('ach-mini');

    if (!el) return;

    if (s.unlocked > 0) {

      el.style.display = 'block';

      el.innerHTML = '<div style="display:flex;align-items:center;gap:8px;font-size:13px"><span>🏆</span><span style="flex:1">Thành tựu</span><span style="font-weight:700;color:var(--gold)">' + s.unlocked + ' / ' + s.total + '</span></div>';

      if (s.recent?.length) {

        el.innerHTML += '<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">' +

          s.recent.map(r => '<span style="font-size:11px;background:var(--surface2);padding:2px 8px;border-radius:4px;color:var(--muted2)">' + (r.emoji||'🏆') + ' ' + r.title + '</span>').join('') +

          '</div>';

      }

    } else {

      el.style.display = 'none';

    }

  } catch (e) {}

}



