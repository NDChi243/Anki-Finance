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





