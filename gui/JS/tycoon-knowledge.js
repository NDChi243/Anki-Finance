// ════════════════════════════════════════════

//  KNOWLEDGE BASE

// ════════════════════════════════════════════

let _kbNotes = [];

let _kbCurrentId = null;

let _kbCurrentEmoji = '📝';

const KB_EMOJIS = ['📝','💡','📚','📊','💰','🏦','📈','📉','💳','🏠','🚗','✈️',

                   '🎓','⚖️','🛡️','🔑','💎','🌍','🏆','⭐','🔥','💼','🤝','📋'];

const KB_DEFAULT_CATS = ['Cơ bản','Ngân sách','Đầu tư','Tiết kiệm','Kinh tế','Thực tế','Bảo vệ','Ghi chú'];



async function loadKnowledge() {

  const [notesRaw, catsRaw] = await Promise.all([B.getAllNotes(), B.getCategories()]);

  _kbNotes = JSON.parse(notesRaw);

  renderKbList(_kbNotes);

  buildKbCatFilter(JSON.parse(catsRaw));

  const stats = document.getElementById('kb-stats');

  const pinned = _kbNotes.filter(n=>n.pinned).length;

  stats.textContent = `${_kbNotes.length} ghi chú • ${pinned} ghim`;

  // Load KN Perks (v1.1.5)
  await loadKNPerks();

}



function renderKbList(notes) {

  const el = document.getElementById('kb-list-el');

  if (!notes.length) {

    el.innerHTML = `<div class="empty"><div class="ei">💡</div>

      <p>Chưa có ghi chú nào.<br>Nhấn <strong>✏️ Thêm mới</strong> để bắt đầu!</p></div>`;

    return;

  }

  el.innerHTML = notes.map(n => {

    const preview = (n.body||'').replace(/\n/g,' ').slice(0, 80) + ((n.body||'').length > 80 ? '…' : '');

    const tags    = (n.tags||[]).slice(0,3).map(t=>`<span class="kb-tag">#${t}</span>`).join('');

    const updated = n.updated ? n.updated.slice(0,10) : '';

    return `<div class="kb-card ${n.pinned?'pinned':''}" onclick="openKbDetail('${n.id}')">

      <div style="display:flex;align-items:flex-start;gap:10px">

        <span class="kb-emoji">${n.emoji||'📝'}</span>

        <div style="flex:1;min-width:0">

          <div style="display:flex;align-items:center;gap:6px">

            <span class="kb-title">${n.title}</span>

            ${n.pinned ? '<span style="font-size:11px">📌</span>' : ''}

          </div>

          <div class="kb-meta">

            <span class="badge badge-purple" style="font-size:9px;padding:1px 6px">${n.category||'Ghi chú'}</span>

            <span style="margin-left:6px">${updated}</span>

          </div>

          <div class="kb-body-preview">${preview}</div>

          <div style="margin-top:4px">${tags}</div>

        </div>

      </div>

    </div>`;

  }).join('');

}



function buildKbCatFilter(cats) {

  const sel = document.getElementById('kb-cat-filter');

  const cur = sel.value;

  sel.innerHTML = '<option value="">📂 Tất cả</option>';

  cats.forEach(c => sel.insertAdjacentHTML('beforeend',`<option value="${c}">${c}</option>`));

  if (cur) sel.value = cur;

}



async function kbSearch() {

  const q = document.getElementById('kb-search').value.trim();

  if (!q) { kbFilter(); return; }

  const raw = await B.searchNotes(q);

  renderKbList(JSON.parse(raw));

}



function kbFilter() {

  const cat = document.getElementById('kb-cat-filter').value;

  const filtered = cat ? _kbNotes.filter(n=>n.category===cat) : _kbNotes;

  renderKbList(filtered);

}



// ── Detail ──────────────────────────────────

async function openKbDetail(id) {

  const raw = await B.getNoteById(id);

  const n   = JSON.parse(raw);

  if (!n || !n.id) return;

  _kbCurrentId = id;



  document.getElementById('kb-list-view').style.display   = 'none';

  document.getElementById('kb-detail-view').style.display = 'block';



  document.getElementById('kb-detail-emoji').textContent = n.emoji || '📝';

  document.getElementById('kb-detail-title').textContent = n.title || '';

  document.getElementById('kb-detail-body').textContent  = n.body  || '';



  const cat     = n.category || 'Ghi chú';

  const updated = n.updated ? n.updated.replace('T',' ').slice(0,16) : '';

  document.getElementById('kb-detail-meta').textContent = `${cat} • Cập nhật: ${updated}`;



  const tagsEl = document.getElementById('kb-detail-tags');

  tagsEl.innerHTML = (n.tags||[]).map(t=>`<span class="kb-tag">#${t}</span>`).join('');



  const pinBtn = document.getElementById('kb-pin-btn');

  pinBtn.textContent = n.pinned ? '📌 Bỏ ghim' : '📌 Ghim';

}



function closeKbDetail() {

  document.getElementById('kb-detail-view').style.display = 'none';

  document.getElementById('kb-list-view').style.display   = 'block';

  _kbCurrentId = null;

  loadKnowledge();

}



async function kbTogglePin() {

  if (!_kbCurrentId) return;

  const res = JSON.parse(await B.togglePin(_kbCurrentId));

  const pinBtn = document.getElementById('kb-pin-btn');

  pinBtn.textContent = res.pinned ? '📌 Bỏ ghim' : '📌 Ghim';

  toast('ok', res.pinned ? '📌 Đã ghim ghi chú' : '📌 Đã bỏ ghim');

}



async function kbDeleteCurrent() {

  if (!_kbCurrentId) return;

  const title = document.getElementById('kb-detail-title').textContent;

  if (!confirm(`Xoá ghi chú "${title}"?`)) return;

  await B.deleteNote(_kbCurrentId);

  toast('info', '🗑️ Đã xoá ghi chú');

  closeKbDetail();

}



// ── Editor ──────────────────────────────────

let _kbEditingId = null;



function openKbEditor(note = null) {

  _kbEditingId    = note ? note.id : null;

  _kbCurrentEmoji = note ? (note.emoji || '📝') : '📝';



  document.getElementById('kb-list-view').style.display   = 'none';

  document.getElementById('kb-detail-view').style.display = 'none';

  document.getElementById('kb-editor-view').style.display = 'block';



  document.getElementById('kb-editor-title-label').textContent =

    note ? '✏️ Sửa ghi chú' : '✏️ Thêm ghi chú mới';



  document.getElementById('kb-title-inp').value  = note ? note.title  : '';

  document.getElementById('kb-body-inp').value   = note ? note.body   : '';

  document.getElementById('kb-cat-inp').value    = '';

  document.getElementById('kb-tags-inp').value   = note ? (note.tags||[]).join(', ') : '';

  document.getElementById('kb-emoji-custom').value = '';



  // Render emoji picker

  const picker = document.getElementById('kb-emoji-picker');

  picker.innerHTML = KB_EMOJIS.map(e =>

    `<span class="emoji-opt ${e===_kbCurrentEmoji?'sel':''}" onclick="setKbEmoji('${e}')">${e}</span>`

  ).join('');



  // Render category chips

  const chipsEl = document.getElementById('kb-cat-chips');

  const allCats = [...new Set([...KB_DEFAULT_CATS, ...(_kbNotes.map(n=>n.category).filter(Boolean))])];

  const curCat  = note ? note.category : 'Ghi chú';

  chipsEl.innerHTML = allCats.map(c =>

    `<span class="cat-chip ${c===curCat?'sel':''}" onclick="selectKbCat(this,'${c}')">${c}</span>`

  ).join('');

  if (note) document.getElementById('kb-cat-inp').value = '';

}



function openKbEditorForCurrent() {

  if (!_kbCurrentId) return;

  const n = _kbNotes.find(x=>x.id===_kbCurrentId)

         || JSON.parse(document.getElementById('kb-detail-body').textContent || '{}');

  const title = document.getElementById('kb-detail-title').textContent;

  const body  = document.getElementById('kb-detail-body').textContent;

  const meta  = document.getElementById('kb-detail-meta').textContent;

  const cat   = meta.split(' • ')[0] || 'Ghi chú';

  const emoji = document.getElementById('kb-detail-emoji').textContent;

  const tags  = [...document.getElementById('kb-detail-tags').querySelectorAll('.kb-tag')]

                  .map(el=>el.textContent.replace('#',''));

  openKbEditor({ id: _kbCurrentId, title, body, category: cat, emoji, tags });

}



function closeKbEditor() {

  document.getElementById('kb-editor-view').style.display = 'none';

  if (_kbEditingId) {

    // Trở về detail

    document.getElementById('kb-detail-view').style.display = 'block';

  } else {

    document.getElementById('kb-list-view').style.display = 'block';

    loadKnowledge();

  }

}



function setKbEmoji(e) {

  if (!e || !e.trim()) return;

  _kbCurrentEmoji = e.trim();

  document.querySelectorAll('.emoji-opt').forEach(el => {

    el.classList.toggle('sel', el.textContent === _kbCurrentEmoji);

  });

  document.getElementById('kb-emoji-custom').value = '';

}



function selectKbCat(el, cat) {

  document.querySelectorAll('.cat-chip').forEach(c=>c.classList.remove('sel'));

  el.classList.add('sel');

  document.getElementById('kb-cat-inp').value = '';

  el.dataset.val = cat;

}



function _getSelectedCat() {

  const custom = document.getElementById('kb-cat-inp').value.trim();

  if (custom) return custom;

  const sel = document.querySelector('.cat-chip.sel');

  return sel ? (sel.dataset.val || sel.textContent) : 'Ghi chú';

}



async function kbSave() {

  const title = document.getElementById('kb-title-inp').value.trim();

  const body  = document.getElementById('kb-body-inp').value;

  if (!title) { toast('err','❌ Vui lòng nhập tiêu đề!'); return; }

  if (!body.trim()) { toast('err','❌ Vui lòng nhập nội dung!'); return; }



  const cat   = _getSelectedCat();

  const emoji = _kbCurrentEmoji || '📝';

  const rawTags = document.getElementById('kb-tags-inp').value;

  const tags  = rawTags.split(',').map(t=>t.trim()).filter(Boolean);

  const tagsJson = JSON.stringify(tags);



  let res;

  if (_kbEditingId) {

    res = JSON.parse(await B.updateNote(_kbEditingId, title, body, cat, emoji, tagsJson));

  } else {

    res = JSON.parse(await B.createNote(title, body, cat, emoji, tagsJson));

  }



  if (res.ok !== false) {

    toast('ok', _kbEditingId ? '✅ Đã cập nhật ghi chú!' : '✅ Đã tạo ghi chú mới!');

    document.getElementById('kb-editor-view').style.display = 'none';

    _kbEditingId = null;

    await loadKnowledge();

    document.getElementById('kb-list-view').style.display = 'block';

  } else {

    toast('err', '❌ ' + (res.error || 'Lỗi lưu ghi chú'));

  }

}


// ════════════════════════════════════════════

//  KN PERKS (v1.1.5)

// ════════════════════════════════════════════

async function loadKNPerks() {

  try {
    const raw = await B.getKNPerks();
    const data = JSON.parse(raw);
    if (data.error) { console.error('loadKNPerks error', data.error); return; }

    document.getElementById('knp-balance').textContent = (data.kn || 0).toLocaleString('vi-VN');

    const bonusEl = document.getElementById('knp-active-bonuses');
    const bonusList = document.getElementById('knp-bonus-list');
    const bonuses = data.active_bonuses || {};

    const bonusEntries = [];
    if (bonuses.xp_mult > 0) bonusEntries.push(`📚 +${(bonuses.xp_mult * 100).toFixed(0)}% EXP`);
    if (bonuses.reward_mult > 0) bonusEntries.push(`💰 +${(bonuses.reward_mult * 100).toFixed(0)}% tiền thưởng`);
    if (bonuses.tax_reduction > 0) bonusEntries.push(`🏛️ -${(bonuses.tax_reduction * 100).toFixed(0)}% thuế`);
    if (bonuses.interest_bonus > 0) bonusEntries.push(`🏦 +${(bonuses.interest_bonus * 100).toFixed(0)}% lãi suất`);

    if (bonusEntries.length > 0) {
      bonusEl.style.display = 'block';
      bonusList.innerHTML = bonusEntries.map(b => `<span style="margin-right:12px">${b}</span>`).join('');
    } else {
      bonusEl.style.display = 'none';
    }

    const perks = data.perks || [];
    const list = document.getElementById('knp-list');
    list.innerHTML = perks.map(p => {
      const status = p.unlocked
        ? '<span style="color:var(--green);font-weight:700">✅ Đã mở</span>'
        : (p.can_afford
            ? `<button class="btn btn-primary" style="font-size:11px;padding:4px 12px" onclick="unlockKNPerk('${p.id}')">🔓 Mở khóa (${p.kn_cost.toLocaleString('vi-VN')} KN)</button>`
            : `<span style="color:var(--muted2);font-size:11px">🔒 Cần ${p.kn_cost.toLocaleString('vi-VN')} KN</span>`);

      return `<div class="card" style="padding:12px;${p.unlocked ? 'border-color:rgba(16,185,129,.3)' : ''}">
        <div style="display:flex;align-items:center;gap:10px">
          <span style="font-size:24px">${p.emoji || '📜'}</span>
          <div style="flex:1;min-width:0">
            <div style="font-weight:700;font-size:13px">${p.name}</div>
            <div style="font-size:11px;color:var(--muted2);margin-top:2px">${p.description}</div>
          </div>
          <div style="flex-shrink:0">
            ${status}
          </div>
        </div>
      </div>`;
    }).join('');

  } catch (e) {
    console.error('loadKNPerks error', e);
  }

}


async function unlockKNPerk(perkId) {

  const res = JSON.parse(await B.unlockKNPerk(perkId));

  if (res.ok) {
    toast('ok', `🔓 Đã mở khóa <strong>${res.perk_name}</strong>! (-${res.kn_spent.toLocaleString('vi-VN')} KN)`);
    await loadKNPerks();
    // Cập nhật lại KN trong rank card
    try {
      const dashRaw = await B.getDashboardData();
      const dashData = JSON.parse(dashRaw);
      if (dashData.rank) {
        const knSmEl = document.getElementById('rank-kn-sm');
        if (knSmEl) {
          setAnimatedNumberText(knSmEl, dashData.rank.kn || 0, {
            format: 'locale',
            prefix: '🧠 ',
            suffix: ' KN',
            duration: 400,
          });
        }
      }
    } catch (_) {}
  } else {
    toast('err', '❌ ' + (res.error || 'Không thể mở khóa perk'));
  }

}





