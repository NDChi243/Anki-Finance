// ════════════════════════════════════════════

//  STREAK + RANK + QUEST

// ════════════════════════════════════════════



function fmtVND(n) {

  return _fmtSafe(n) + ' VND';

}



// ── Streak mini (dashboard) ──────────────────

async function refreshStreakRankMini() {

  const [sRaw, rRaw] = await Promise.all([B.getStreakStatus(), B.getRankStatus()]);

  const s = JSON.parse(sRaw);

  const r = JSON.parse(rRaw);



  // Streak

  const fire = s.streak > 0 ? (s.streak >= 30 ? '🔥🔥🔥' : s.streak >= 7 ? '🔥🔥' : '🔥') : '💤';

  document.getElementById('streak-fire').textContent = fire;

  document.getElementById('streak-num').textContent  = s.streak;

  document.getElementById('streak-mult').textContent = '×' + s.multiplier.toFixed(1);

  const hint = s.streak > 0

    ? `${s.today_cards}/${s.min_cards} thẻ hôm nay`

    : (s.today_cards >= s.min_cards ? 'Ôn thêm để tính streak mới' : `Cần ${s.cards_needed} thẻ nữa`);

  document.getElementById('streak-hint').textContent = hint;

  const bestEl = document.getElementById('streak-best');

  if (bestEl) bestEl.textContent = s.best > 0 ? `Kỷ lục: ${s.best} ngày` : '';



  // Rank mini

  document.getElementById('rank-emoji-sm').textContent  = r.rank_emoji;

  document.getElementById('rank-label-sm').textContent  = r.rank_label;

  document.getElementById('rank-xp-sm').textContent     = (r.xp||0).toLocaleString('vi-VN');

  document.getElementById('rank-prog-sm').style.width   = r.overall_pct + '%';

  document.getElementById('rank-prog-sm').style.background = `linear-gradient(90deg,${r.rank_color},${r.rank_color}aa)`;

  const mini = document.getElementById('rank-mini');

  if (mini) mini.style.borderColor = r.rank_color + '66';

  const nextLbl = r.is_max ? '🏆 Rank tối đa!' :

    `Tiếp: ${r.next_rank?.label} (${r.overall_pct}%)`;

  document.getElementById('rank-next-sm').textContent = nextLbl;

}



// ── Quest mini (dashboard) ────────────────────

async function refreshQuestMini() {

  const raw = await B.getQuestSummary();

  const data = JSON.parse(raw);

  const quests = data.quests || [];

  const el = document.getElementById('quest-mini-list');

  if (!quests.length) { el.innerHTML = '<div style="font-size:12px;color:var(--muted2)">Chưa có quest.</div>'; return; }



  el.innerHTML = quests.map(q => {

    const pct = q.type === 'no_again_under' || q.type === 'no_purchase' || q.type === 'no_penalty'

      ? (q.done ? 100 : 0)

      : q.target > 0 ? Math.min(100, Math.round(q.progress / q.target * 100)) : 0;

    const col = q.done ? 'var(--green)' : 'var(--accent)';

    return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border)">

      <span style="font-size:16px">${q.emoji||'🎯'}</span>

      <div style="flex:1;min-width:0">

        <div style="font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${q.title}</div>

        <div style="background:var(--surface2);border-radius:3px;height:4px;margin-top:3px;overflow:hidden">

          <div style="height:100%;width:${pct}%;background:${col};border-radius:3px;transition:width .3s"></div>

        </div>

      </div>

      <span style="font-size:11px;font-weight:700;color:${col};flex-shrink:0">${q.done?'✅':''+pct+'%'}</span>

    </div>`;

  }).join('');

}



// ── Full Quests page ──────────────────────────

async function loadQuests() {

  const [sRaw, rRaw, qRaw] = await Promise.all([

    B.getStreakStatus(), B.getRankStatus(), B.getQuestSummary(),

  ]);

  const s = JSON.parse(sRaw);

  const r = JSON.parse(rRaw);

  const q = JSON.parse(qRaw);



  renderStreakFull(s);

  renderRankFull(r);

  renderQuestsFull(q);

  renderRanksTable();

}



function renderStreakFull(s) {

  document.getElementById('streak-count-full').textContent = s.streak;

  document.getElementById('streak-mult-full').textContent  = '×' + s.multiplier.toFixed(1);

  document.getElementById('streak-best-full').textContent  = s.best;

  const info = s.streak === 0

    ? `Hôm nay ôn ${s.today_cards}/${s.min_cards} thẻ — ${s.cards_needed > 0 ? 'cần thêm ' + s.cards_needed + ' thẻ để tính streak' : 'đủ streak!'}`

    : `🔥 Streak ${s.streak} ngày! Hôm nay ${s.today_cards}/${s.min_cards} thẻ.`;

  document.getElementById('streak-today-info').textContent = info;



  // Quest date

  const now = new Date();

  document.getElementById('quest-date-label').textContent =

    `${now.toLocaleDateString('vi-VN', {weekday:'long', day:'numeric', month:'long'})}`;

}



function renderRankFull(r) {

  document.getElementById('rank-emoji-big').textContent  = r.rank_emoji;

  document.getElementById('rank-label-full').textContent = r.rank_label;

  document.getElementById('rank-xp-full').textContent    = (r.xp||0).toLocaleString('vi-VN');

  document.getElementById('rank-group-full').textContent = 'Nhóm: ' + r.rank_group;



  const bar = document.getElementById('rank-prog-full');

  bar.style.width      = r.overall_pct + '%';

  bar.style.background = `linear-gradient(90deg,${r.rank_color},${r.rank_color}bb)`;



  const card = document.getElementById('rank-full-card');

  if (card) {

    card.style.borderColor = r.rank_color + '66';

    const glow = card.querySelector('.rank-glow');

    if (glow) glow.style.background = r.rank_color;

  }



  const progText = r.is_max

    ? '🏆 Đã đạt rank tối đa — Tỷ phú Anki!'

    : `Tiến tới ${r.next_rank?.label}: ${r.overall_pct}% (XP: ${r.xp_pct}%, Tiền: ${r.bal_pct}%)`;

  document.getElementById('rank-prog-text').textContent = progText;



  const reqEl = document.getElementById('rank-requirements');

  if (reqEl && r.next_rank) {

    const nx = r.next_rank;

    reqEl.innerHTML = `

      <div style="background:var(--surface2);border-radius:8px;padding:8px;text-align:center">

        <div style="font-size:10px;color:var(--muted2);margin-bottom:2px">XP cần thêm</div>

        <div style="font-weight:800;color:var(--accent2)">⭐ ${(r.xp_needed||0).toLocaleString('vi-VN')}</div>

      </div>

      <div style="background:var(--surface2);border-radius:8px;padding:8px;text-align:center">

        <div style="font-size:10px;color:var(--muted2);margin-bottom:2px">Tiền cần thêm</div>

        <div style="font-weight:800;color:var(--yellow)">💰 ${fmtVND(r.bal_needed)}</div>

      </div>`;

  } else if (reqEl) {

    reqEl.innerHTML = '<div style="text-align:center;color:var(--green);font-weight:700;padding:8px;grid-column:1/-1">🏆 Rank tối đa — bạn là huyền thoại!</div>';

  }

}



function renderQuestsFull(data) {

  const quests  = data.quests || [];

  const done    = data.done || 0;

  document.getElementById('quest-done-badge').textContent = `${done}/${quests.length} hoàn thành`;

  document.getElementById('quest-done-badge').className =

    done === quests.length ? 'badge badge-green' : 'badge badge-purple';



  const el = document.getElementById('quest-full-list');

  if (!quests.length) { el.innerHTML = '<div class="empty"><div class="ei">📋</div><p>Chưa có quest.</p></div>'; return; }



  el.innerHTML = quests.map(q => {

    const isDone    = q.done;

    const isClaimed = q.reward_claimed;

    let pct = 0;

    if (q.type === 'no_again_under' || q.type === 'no_purchase' || q.type === 'no_penalty') {

      pct = isDone ? 100 : 0;

    } else {

      pct = q.target > 0 ? Math.min(100, Math.round(q.progress / q.target * 100)) : 0;

    }

    const progText = q.type === 'no_again_under'

      ? `${q.progress} lần Again (cần ≤ ${q.target})`

      : `${q.progress} / ${q.target}`;



    return `<div class="quest-card ${isDone?'done':''} ${isClaimed?'claimed':''}">

      <div style="display:flex;align-items:flex-start;gap:10px">

        <span class="quest-emoji">${q.emoji||'🎯'}</span>

        <div style="flex:1">

          <div class="quest-title">${q.title}</div>

          <div class="quest-desc">${q.desc}</div>

          <div style="display:flex;align-items:center;gap:8px;margin-top:6px">

            <div class="quest-prog-wrap">

              <div class="quest-prog-bar ${isDone?'done':''}" style="width:${pct}%"></div>

            </div>

            <span style="font-size:11px;color:var(--muted2);flex-shrink:0">${progText}</span>

          </div>

          <div style="display:flex;align-items:center;justify-content:space-between;margin-top:4px">

            <span class="quest-reward">

              ${q.money > 0 ? '💵 +' + fmtVND(q.money) : ''}

              ${q.xp > 0 ? ' ⭐ +' + q.xp + ' XP' : ''}

            </span>

            ${isDone && !isClaimed

              ? `<button class="btn btn-green" style="font-size:11px;padding:3px 10px" onclick="claimQuest('${q.id}')">🎁 Nhận thưởng</button>`

              : isClaimed ? '<span style="font-size:11px;color:var(--muted2)">✅ Đã nhận</span>'

              : `<span style="font-size:11px;color:var(--muted2)">${pct}%</span>`

            }

          </div>

        </div>

      </div>

    </div>`;

  }).join('');

}



async function claimQuest(questId) {

  const res = JSON.parse(await B.claimQuestReward(questId));

  if (res.ok) {

    toast('ok', `🎁 ${res.quest_title}: +${fmtVND(res.money)} ${res.xp>0?'⭐ +'+res.xp+' XP':''}`.trim());

    await loadQuests();

    await refreshStreakRankMini();

  } else {

    toast('err', '❌ ' + res.error);

  }

}



let _allRanks = null;

async function renderRanksTable() {

  if (!_allRanks) {

    _allRanks = JSON.parse(await B.getAllRanks());

  }

  const el = document.getElementById('ranks-table');

  const curRankId = JSON.parse(await B.getRankStatus()).rank_id;

  el.innerHTML = _allRanks.map(r => {

    const isCur = r.id === curRankId;

    return `<div style="display:flex;align-items:center;gap:10px;padding:7px 10px;border-radius:8px;font-size:12px;

        ${isCur ? 'background:rgba(124,58,237,.12);border:1px solid rgba(124,58,237,.3)' : 'background:var(--surface2)'}">

      <span style="font-size:20px">${r.emoji}</span>

      <span style="flex:1;font-weight:${isCur?700:500};color:${isCur?r.color:'var(--text)'}">${r.label}</span>

      <span style="color:var(--accent2);font-size:11px">⭐ ${r.xp.toLocaleString('vi-VN')} XP</span>

      <span style="color:var(--yellow);font-size:11px">💰 ${fmtVND(r.bal)}</span>

      ${isCur ? '<span class="badge badge-purple" style="font-size:9px">← Bạn</span>' : ''}

    </div>`;

  }).join('');

}





