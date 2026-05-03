// ════════════════════════════════════════════

//  GOALS (Req 3)

// ════════════════════════════════════════════

let _goalItems = [];  // cache shop items cho modal



async function refreshGoal() {

  const raw = await B.getGoal();

  const g   = JSON.parse(raw);

  const card    = document.getElementById('goal-card');

  const empty   = document.getElementById('goal-empty-prompt');



  if (!g.has_goal) {

    card.style.display  = 'none';

    empty.style.display = 'block';

    return;

  }

  card.style.display  = 'block';

  empty.style.display = 'none';



  document.getElementById('goal-emoji').textContent    = g.item_emoji || '🎯';

  document.getElementById('goal-name').textContent     = g.item_name || '';

  document.getElementById('goal-pct').textContent      = g.percent + '%';

  document.getElementById('goal-price-info').textContent = 'Giá: ' + fmt(g.item_price);

  document.getElementById('goal-set-at').textContent   = g.set_at ? 'Đặt lúc ' + g.set_at : '';



  const bar  = document.getElementById('goal-bar');

  const wrap = document.getElementById('goal-progress-wrap');

  bar.style.width = g.percent + '%';

  wrap.classList.toggle('goal-reached', g.reached);



  const remaining = document.getElementById('goal-remaining');

  const badge     = document.getElementById('goal-reached-badge');

  if (g.reached) {

    remaining.textContent = '🎉 Đủ tiền mua rồi!';

    remaining.style.color = 'var(--green)';

    badge.style.display   = 'inline-flex';

  } else {

    remaining.textContent = `còn thiếu ${fmt(g.remaining)}`;

    remaining.style.color = 'var(--muted2)';

    badge.style.display   = 'none';

  }

}



async function openGoalModal() {

  const modal = document.getElementById('modal-goal');

  modal.classList.add('open');

  // Load shop items nếu chưa có

  if (!_goalItems.length) {

    const raw = await B.getShopItems();

    _goalItems = JSON.parse(raw);

  }

  filterGoalItems();

}



function closeGoalModal() {

  document.getElementById('modal-goal').classList.remove('open');

  document.getElementById('goal-search-inp').value = '';

}



function filterGoalItems() {

  const q     = (document.getElementById('goal-search-inp').value || '').toLowerCase();

  const items = q

    ? _goalItems.filter(i => i.name.toLowerCase().includes(q) || (i.category||'').toLowerCase().includes(q))

    : _goalItems;

  const el = document.getElementById('goal-items-list');

  if (!items.length) {

    el.innerHTML = '<div style="text-align:center;color:var(--muted2);padding:20px">Không tìm thấy sản phẩm</div>';

    return;

  }

  el.innerHTML = items.map(i => `

    <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;background:var(--surface2);border-radius:8px;cursor:pointer;transition:background .15s"

      onmouseenter="this.style.background='var(--surface3)'" onmouseleave="this.style.background='var(--surface2)'"

      onclick="selectGoalItem('${i.id}','${i.name.replace(/'/g,"\'")}',${i.price},'${i.emoji||'🎯'}')">

      <span style="font-size:24px">${i.image_url ? '' : (i.emoji||'📦')}</span>

      ${i.image_url ? `<img src="${i.image_url}" style="width:32px;height:32px;border-radius:6px;object-fit:cover" onerror="this.style.display='none'">` : ''}

      <div style="flex:1">

        <div style="font-size:13px;font-weight:700">${i.name}</div>

        <div style="font-size:11px;color:var(--muted2)">${i.category||''}</div>

      </div>

      <div style="font-size:13px;font-weight:800;color:var(--yellow)">${fmt(i.price)}</div>

    </div>`).join('');

}



async function selectGoalItem(id, name, price, emoji) {

  const res = JSON.parse(await B.setGoal(id, name, price, emoji));

  if (res.ok) {

    closeGoalModal();

    toast('ok', `🎯 Đã đặt mục tiêu: ${name}`);

    await refreshGoal();

  } else {

    toast('err', '❌ ' + (res.error || 'Lỗi đặt mục tiêu'));

  }

}



async function doDeleteGoal() {

  if (!confirm('Xoá mục tiêu hiện tại?')) return;

  await B.clearGoal();

  toast('info', '🗑️ Đã xoá mục tiêu');

  await refreshGoal();

}



document.getElementById('modal-goal')?.addEventListener('click', e => {

  if (e.target === e.currentTarget) closeGoalModal();

});



