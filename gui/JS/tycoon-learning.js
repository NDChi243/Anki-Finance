// ════════════════════════════════════════════

//  LEARNING PAGE (Quiz + Emergency Log)

// ════════════════════════════════════════════

// ── QUIZ STATE ──

let quizData = null;        // { quiz_set, set_size }

let quizCurrentQ = 0;       // 0-based index

let quizAnswered = {};      // { q_index: selected }

let quizResults = {};       // { q_index: {correct,bonus_awarded,explanation,correct_answer} }

let quizSubmitted = false;  // flag to prevent double submit

let quizLoading = false;

let quizTopics = null;       // { slug: display_name }

let selectedTopic = '';      // current topic filter



// ── Cached quiz stats (tránh gọi bridge lại mỗi lần vào tab) ──

let _cachedQuizStats = null;



// ── Cached DOM refs cho quiz rendering ──

let _quizDom = null;

function _getQuizDom() {

  if (!_quizDom) {

    _quizDom = {

      area:      document.getElementById('quiz-area'),

      empty:     document.getElementById('quiz-empty'),

      progress:  document.getElementById('quiz-progress'),

      qText:     document.getElementById('quiz-q-text'),

      options:   document.getElementById('quiz-options'),

      result:    document.getElementById('quiz-result'),

      qCounter:  document.getElementById('quiz-q-counter'),

      prevBtn:   document.getElementById('quiz-prev-btn'),

      nextBtn:   document.getElementById('quiz-next-btn'),

      finishBtn: document.getElementById('quiz-finish-btn'),

      newBtn:    document.getElementById('quiz-new-btn'),

    };

  }

  return _quizDom;

}



// ── Cache DOM refs cho quiz stats ──

let _quizStatsDom = null;

function _getQuizStatsDom() {

  if (!_quizStatsDom) {

    _quizStatsDom = {

      accuracy: document.getElementById('quiz-accuracy'),

      correct:  document.getElementById('quiz-correct'),

      total:    document.getElementById('quiz-total'),

      streak:   document.getElementById('quiz-streak'),

      best:     document.getElementById('quiz-best'),

    };

  }

  return _quizStatsDom;

}



function _updateQuizStatsUI(s) {

  const d = _getQuizStatsDom();

  d.accuracy.textContent = s.accuracy + '%';

  d.correct.textContent  = s.correct;

  d.total.textContent    = s.total;

  d.streak.textContent   = s.streak;

  d.best.textContent     = s.best_streak;

}



// ════════════════════════════════════════════

async function loadLearning() {

  await refreshBalance();



  // ── Quiz Stats (dùng cache nếu có) ─────────

  if (_cachedQuizStats) {

    _updateQuizStatsUI(_cachedQuizStats);

  } else {

    const statsRaw = await B.getQuizStats();

    _cachedQuizStats = JSON.parse(statsRaw);

    _updateQuizStatsUI(_cachedQuizStats);

  }



  // ── Daily limit ──────────────────────────

  await refreshDailyQuizLimit();



  // ── Load quiz topics ─────────────────────

  await loadQuizTopics();



  // ── Load current quiz set ─────────────────

  await loadQuizSet();



  // ── Emergency Log ─────────────────────────

  await loadEmergencyLog();

}



// ── Cập nhật hiển thị giới hạn câu hỏi mỗi ngày ──

let _quizCountdownInterval = null;

async function refreshDailyQuizLimit() {

  try {

    const raw = await B.getQuizDailyInfo();

    const info = JSON.parse(raw);

    const badge = document.getElementById('quiz-daily-limit-badge');

    if (badge) {

      const rem = info.remaining;

      const limit = info.limit;

      const count = info.count || info.correct_today || 0;

      if (rem <= 0) {

        badge.className = 'badge badge-red';

        // Hiển thị countdown đến 7:00 sáng hôm sau

        const secs = info.next_reset_seconds || 0;

        if (secs > 0) {

          const h = Math.floor(secs / 3600);

          const m = Math.floor((secs % 3600) / 60);

          const s = secs % 60;

          const pad = (n) => String(n).padStart(2, '0');

          badge.textContent = `📅 Hết lượt • Mở lại sau ${pad(h)}:${pad(m)}:${pad(s)}`;

          _startQuizCountdown(secs, badge);

        } else {

          badge.textContent = `📅 Hết lượt hôm nay (${count}/${limit})`;

        }

      } else {

        badge.className = 'badge badge-green';

        badge.textContent = `📅 Hôm nay: ${count}/${limit}  •  Còn ${rem} lượt`;

        // Dừng countdown nếu đang chạy

        if (_quizCountdownInterval) {

          clearInterval(_quizCountdownInterval);

          _quizCountdownInterval = null;

        }

      }

    }

  } catch (e) {

    console.error('refreshDailyQuizLimit error', e);

  }

}

function _startQuizCountdown(seconds, badgeEl) {

  // Dừng interval cũ nếu có

  if (_quizCountdownInterval) {

    clearInterval(_quizCountdownInterval);

    _quizCountdownInterval = null;

  }

  let remaining = seconds;

  _quizCountdownInterval = setInterval(() => {

    remaining--;

    if (remaining <= 0) {

      clearInterval(_quizCountdownInterval);

      _quizCountdownInterval = null;

      // Tự động refresh lại khi hết giờ

      refreshDailyQuizLimit();

      return;

    }

    const h = Math.floor(remaining / 3600);

    const m = Math.floor((remaining % 3600) / 60);

    const s = remaining % 60;

    const pad = (n) => String(n).padStart(2, '0');

    badgeEl.textContent = `📅 Hết lượt • Mở lại sau ${pad(h)}:${pad(m)}:${pad(s)}`;

  }, 1000);

}



// ── Load quiz topics into dropdown ─────────────────────────────────

async function loadQuizTopics() {

  try {

    const raw = await B.getQuizTopics();

    quizTopics = JSON.parse(raw);

    const sel = document.getElementById('quiz-topic-select');

    if (!sel) return;

    sel.innerHTML = '<option value="">📚 Tất cả chủ đề</option>';

    for (const [slug, display] of Object.entries(quizTopics)) {

      const opt = document.createElement('option');

      opt.value = slug;

      opt.textContent = display;

      sel.appendChild(opt);

    }

    // Khôi phục lựa chọn trước đó (nếu có)

    if (selectedTopic) sel.value = selectedTopic;

  } catch (e) {

    console.error('loadQuizTopics error', e);

  }

}



// ── Quiz Functions ────────────────────────────────────────────────



async function loadQuizSet() {

  try {

    const raw = await B.getQuizSet();

    const data = JSON.parse(raw);

    quizData = data;

    quizCurrentQ = 0;

    quizAnswered = {};

    quizResults = {};

    quizSubmitted = false;

    renderQuiz();

  } catch (e) {

    console.error('loadQuizSet error', e);

    const dom = _getQuizDom();

    dom.area.style.display = 'none';

    dom.empty.style.display = '';

  }

}



async function startNewQuiz() {

  if (quizLoading) return;

  quizLoading = true;

  const dom = _getQuizDom();

  dom.newBtn.textContent = '⏳ Đang tạo...';

  try {

    let raw;

    if (selectedTopic) {

      raw = await B.newQuizSetByTopic(selectedTopic);

    } else {

      raw = await B.newQuizSet();

    }

    const data = JSON.parse(raw);

    quizData = data;

    quizCurrentQ = 0;

    quizAnswered = {};

    quizResults = {};

    quizSubmitted = false;

    renderQuiz();

    // Cập nhật lại thống kê — xoá cache để lấy mới

    const sr = JSON.parse(await B.getQuizStats());

    _cachedQuizStats = sr;

    _updateQuizStatsUI(sr);

    // Cập nhật daily limit

    await refreshDailyQuizLimit();

  } catch (e) {

    console.error('startNewQuiz error', e);

  }

  dom.newBtn.textContent = '🔄 Bộ câu mới';

  quizLoading = false;

}



async function onTopicChange() {

  const sel = document.getElementById('quiz-topic-select');

  selectedTopic = sel ? sel.value : '';

  await startNewQuiz();

}



function renderQuiz() {

  const dom = _getQuizDom();



  if (!quizData || !quizData.quiz_set || quizData.quiz_set.length === 0) {

    dom.area.style.display = 'none';

    dom.empty.style.display = '';

    return;

  }



  dom.area.style.display = '';

  dom.empty.style.display = 'none';

  dom.result.style.display = 'none';



  const set = quizData.quiz_set;

  const total = set.length;

  const idx = quizCurrentQ;



  // Progress dots

  dom.progress.innerHTML = set.map((_, i) => {

    let cls = 'quiz-progress-dot';

    if (i === idx) cls += ' current';

    if (quizResults[i] !== undefined) cls += quizResults[i].correct ? ' answered' : ' wrong-answered';

    return `<div class="${cls}" title="Câu ${i+1}"></div>`;

  }).join('');



  // Counter

  dom.qCounter.textContent = `Câu ${idx+1}/${total}`;



  // Question

  const q = set[idx];

  dom.qText.textContent = q.q;



  // Options

  const letter = ['A','B','C','D','E','F'];

  const answered = quizAnswered[idx];

  const resultData = quizResults[idx];



  dom.options.innerHTML = q.options.map((opt, oi) => {

    let cls = 'quiz-option';

    if (resultData !== undefined) {

      cls += ' disabled';

      if (oi === q.correct) cls += ' correct';

      if (answered === oi && oi !== q.correct) cls += ' wrong';

      if (answered === oi) cls += ' selected';

    } else if (answered === oi) {

      cls += ' selected';

    }

    return `<div class="${cls}" data-oi="${oi}" onclick="${resultData !== undefined ? '' : `selectQuizOption(${oi})`}">

      <div class="q-radio">${resultData !== undefined ? (oi === q.correct ? '✓' : (answered === oi ? '✗' : letter[oi] || oi+1)) : (letter[oi] || oi+1)}</div>

      <div class="q-opt-label">${opt}</div>

    </div>`;

  }).join('');



  // Result panel

  if (resultData !== undefined) {

    const isCorrect = resultData.correct;

    dom.result.style.display = '';

    dom.result.style.background = isCorrect ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)';

    dom.result.style.border = isCorrect ? '1px solid rgba(16,185,129,.3)' : '1px solid rgba(239,68,68,.3)';

    dom.result.style.color = isCorrect ? 'var(--green)' : 'var(--red)';

    const icon = isCorrect ? '✅' : '❌';

    const knAwarded = resultData.kn_awarded || 0;

    let bonusText = '';
    if (resultData.bonus_awarded) {
      bonusText = `<br><span style="color:var(--yellow)">🎉 +50.000đ đã được thêm vào ví!</span>`;
    }
    if (knAwarded > 0) {
      bonusText += `<br><span style="color:var(--green)">🧠 +${knAwarded} KN!</span>`;
    }

    const correctAnswer = resultData.correct_answer || 'Không xác định';

    dom.result.innerHTML = `<strong>${icon} ${isCorrect ? 'Chính xác!' : 'Sai rồi!'}</strong><br>

      <span style="color:var(--muted2)">Đáp án đúng: <strong style="color:var(--text)">${correctAnswer}</strong></span><br>

      <span style="color:var(--muted);font-size:12px">💡 ${resultData.explanation || ''}</span>${bonusText}`;

  } else {

    dom.result.style.display = 'none';

  }



  // Navigation

  dom.prevBtn.style.display = idx > 0 ? '' : 'none';

  dom.nextBtn.style.display = (idx < total - 1) ? '' : 'none';

  dom.finishBtn.style.display = (idx === total - 1 && resultData !== undefined) ? '' : 'none';



  // Update stats hint

  const allDone = set.every((_, i) => quizResults[i] !== undefined);

  if (allDone) {

    const correctCount = set.filter((_, i) => quizResults[i] && quizResults[i].correct).length;

    dom.finishBtn.textContent = `✅ Hoàn thành (${correctCount}/${total} đúng)`;

    dom.finishBtn.style.display = '';

    dom.nextBtn.style.display = 'none';

  }

}



function selectQuizOption(oi) {

  const idx = quizCurrentQ;

  if (!quizData || !quizData.quiz_set) return;

  if (quizResults[idx] !== undefined) return; // already answered

  if (quizSubmitted) return;



  quizAnswered[idx] = oi;

  quizSubmitted = true;



  // Gửi lên Python backend

  B.submitQuizAnswer(idx, oi).then(raw => {

    let res;

    try {

      res = JSON.parse(raw);

    } catch(e) {

      console.error('submitQuizAnswer parse error', e);

      res = {};

    }



    // Kiểm tra lỗi từ backend

    if (res.error) {

      console.error('submitQuizAnswer backend error', res.error);

      toast('error', `❌ Lỗi: ${res.error}`, 3000);

      quizSubmitted = false;

      return;

    }



    quizResults[idx] = res;

    renderQuiz();



    // Update stats display & cache

    const sr = res.stats || { accuracy: 0, correct: 0, total: 0, streak: 0, best_streak: 0 };

    _cachedQuizStats = sr;

    _updateQuizStatsUI(sr);



    // 🔥 Refresh balance + toast nếu được thưởng

    const knAwarded = res.kn_awarded || 0;
    if (res.bonus_awarded) {
      let toastMsg = '🎓 Trả lời đúng! +50.000đ đã được cộng vào ví!';
      if (knAwarded > 0) {
        toastMsg += ` 🧠 +${knAwarded} KN`;
      }
      toast('ok', toastMsg, 3500);
    } else if (knAwarded > 0) {
      toast('ok', `🧠 +${knAwarded} KN đã được cộng!`, 3000);
    }

    refreshBalance();

    refreshDailyQuizLimit();



    quizSubmitted = false;

  }).catch(e => {

    console.error('submitQuizAnswer error', e);

    toast('error', '❌ Không thể ghi nhận câu trả lời. Vui lòng thử lại.', 3000);

    quizSubmitted = false;

  });

}



function nextQuizQuestion() {

  if (!quizData || !quizData.quiz_set) return;

  if (quizCurrentQ < quizData.quiz_set.length - 1) {

    quizCurrentQ++;

    renderQuiz();

  }

}



function prevQuizQuestion() {

  if (quizCurrentQ > 0) {

    quizCurrentQ--;

    renderQuiz();

  }

}



function finishQuiz() {

  renderQuizReview();

}



// ── Review Mode ─────────────────────────────────────────────────────

function renderQuizReview() {

  const dom = _getQuizDom();

  const set = quizData?.quiz_set;

  if (!set || set.length === 0) return;



  const total = set.length;

  let correctCount = 0;

  for (let i = 0; i < total; i++) {

    if (quizResults[i] && quizResults[i].correct) correctCount++;

  }

  const wrongCount = total - correctCount;

  const accuracyPct = total > 0 ? Math.round(correctCount / total * 100) : 0;



  // Ẩn các element quiz thường

  dom.qText.style.display = 'none';

  dom.options.style.display = 'none';

  dom.result.style.display = 'none';

  dom.prevBtn.style.display = 'none';

  dom.nextBtn.style.display = 'none';

  dom.finishBtn.style.display = 'none';



  const letter = ['A','B','C','D','E','F'];



  // Summary header

  // Tính tổng KN kiếm được từ các câu đúng
  let totalKn = 0;
  for (let i = 0; i < total; i++) {
    const res = quizResults[i];
    if (res && res.correct && res.kn_awarded) {
      totalKn += res.kn_awarded;
    }
  }

  let html = `

    <div style="text-align:center;padding:16px 0;margin-bottom:16px">

      <div style="font-size:32px;margin-bottom:6px">${accuracyPct >= 80 ? '🎉' : accuracyPct >= 50 ? '💪' : '📚'}</div>

      <div style="font-size:18px;font-weight:800">Kết quả: ${correctCount}/${total} đúng</div>

      <div style="font-size:13px;color:var(--muted2);margin-top:4px">Độ chính xác: ${accuracyPct}%</div>

      <div style="display:flex;gap:16px;justify-content:center;margin-top:10px;font-size:13px">

        <span style="color:var(--green)">✅ Đúng: ${correctCount}</span>

        <span style="color:var(--red)">❌ Sai: ${wrongCount}</span>

        ${totalKn > 0 ? `<span style="color:var(--green)">🧠 +${totalKn} KN</span>` : ''}

      </div>

    </div>

    <div style="max-height:420px;overflow-y:auto;display:flex;flex-direction:column;gap:8px;margin-bottom:16px;padding-right:4px">`;



  for (let i = 0; i < total; i++) {

    const q = set[i];

    const res = quizResults[i];

    const isCorrect = res && res.correct;

    const correctLetter = letter[q.correct] || (q.correct + 1);

    const answeredIdx = quizAnswered[i];

    const answeredLetter = answeredIdx !== undefined ? (letter[answeredIdx] || (answeredIdx + 1)) : '—';



    html += `

      <div style="background:${isCorrect ? 'rgba(16,185,129,.07)' : 'rgba(239,68,68,.07)'};border-radius:8px;padding:10px 12px;border-left:3px solid ${isCorrect ? 'var(--green)' : 'var(--red)'}">

        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">

          <div style="font-size:13px;font-weight:600;flex:1;line-height:1.5">Câu ${i+1}: ${q.q}</div>

          <span style="font-size:16px;white-space:nowrap">${isCorrect ? '✅' : '❌'}</span>

        </div>

        <div style="display:flex;gap:12px;margin-top:6px;font-size:12px;flex-wrap:wrap">

          <span style="color:var(--muted2)">Bạn chọn: <strong style="color:${isCorrect ? 'var(--green)' : 'var(--red)'}">${answeredLetter}</strong></span>

          ${!isCorrect ? `<span style="color:var(--muted2)">Đáp án: <strong style="color:var(--green)">${correctLetter}</strong></span>` : ''}

          <span style="color:var(--muted);font-size:11px;flex-basis:100%;margin-top:2px">💡 ${(q.explanation || '').substring(0, 100)}${(q.explanation || '').length > 100 ? '...' : ''}</span>

        </div>

      </div>`;

  }



  html += `</div>

    <div style="display:flex;gap:8px;justify-content:center">

      <button class="btn btn-secondary" onclick="exitReviewMode();startNewQuiz()" style="font-size:12px;padding:6px 16px">🔄 Làm lại</button>

      <button class="btn" onclick="exitReviewMode()" style="font-size:12px;padding:6px 16px">📚 Về danh sách</button>

    </div>`;



  // Inject hoặc tạo review container

  let reviewDiv = document.getElementById('quiz-review-area');

  if (!reviewDiv) {

    reviewDiv = document.createElement('div');

    reviewDiv.id = 'quiz-review-area';

    dom.area.appendChild(reviewDiv);

  }

  reviewDiv.innerHTML = html;

  reviewDiv.style.display = '';

}



function exitReviewMode() {

  const dom = _getQuizDom();

  const reviewDiv = document.getElementById('quiz-review-area');

  if (reviewDiv) reviewDiv.style.display = 'none';

  // Khôi phục trạng thái quiz ban đầu

  dom.qText.style.display = '';

  dom.options.style.display = '';

  quizCurrentQ = 0;

  renderQuiz();

  document.getElementById('page-learning').scrollIntoView({ behavior: 'smooth', block: 'start' });

}



// ── Emergency Log ──────────────────────────────────────────────────



async function loadEmergencyLog() {

  const logRaw = await B.getEmergencyLog();

  const log = JSON.parse(logRaw);



  document.getElementById('emg-count-badge').textContent = log.length + ' sự kiện';



  // Insurance status from inventory

  const invRaw = JSON.parse(await B.getInventory());

  const invIds = new Set((invRaw || []).map(i => i.id || ''));

  const insMap = [

    { id: 'ins_health',   label: 'Bảo hiểm SK',   emoji: '🏥' },

    { id: 'ins_car',      label: 'Bảo hiểm xe',   emoji: '🚗' },

    { id: 'ins_property', label: 'Bảo hiểm BĐS',  emoji: '🏠' },

    { id: 'ins_life',     label: 'Bảo hiểm NT',    emoji: '💙' },

  ];

  const insRow = document.getElementById('emg-insurance-row');

  insRow.innerHTML = insMap.map(ins => {

    const owned = invIds.has(ins.id);

    return `<span class="badge ${owned ? 'badge-green' : 'badge-red'}" title="${owned ? 'Đã mua' : 'Chưa mua'}">

      ${ins.emoji} ${ins.label} ${owned ? '✅' : '✕'}

    </span>`;

  }).join('');



  const listEl = document.getElementById('emg-log-list');

  const emptyEl = document.getElementById('emg-empty');



  if (log.length === 0) {

    listEl.innerHTML = '';

    emptyEl.style.display = '';

    return;

  }

  emptyEl.style.display = 'none';



  const EMOJI = {

    car: '🚗', health: '🏥', property: '🏠', residence: '🏡', income: '💼',

  };



  listEl.innerHTML = log.map(e => {

    const paid = Number(e.paid || e.base_cost || 0);

    const base = Number(e.base_cost || paid);

    const insured = e.insured;

    const saving = base - paid;

    const cat = (e.event_id || '').split('_')[0];

    const emoji = EMOJI[cat] || '⚠️';

    return `

      <div style="display:flex;align-items:flex-start;gap:10px;padding:10px 12px;

                  background:var(--surface2);border-radius:9px;border:1px solid ${insured ? 'rgba(16,185,129,.2)' : 'rgba(239,68,68,.15)'}">

        <div style="font-size:22px;flex-shrink:0">${emoji}</div>

        <div style="flex:1;min-width:0">

          <div style="font-size:13px;font-weight:700">${e.title || 'Sự kiện'}</div>

          <div style="font-size:11px;color:var(--muted2);margin-top:1px">${e.date || ''}</div>

          ${insured && saving > 0 ? `<div style="font-size:11px;color:var(--green);margin-top:2px">🛡️ Bảo hiểm tiết kiệm ${fmt(saving)}</div>` : ''}

        </div>

        <div style="text-align:right;flex-shrink:0">

          <div style="font-size:14px;font-weight:900;color:var(--red)">-${fmt(paid)}</div>

          ${insured ? `<div style="font-size:10px;color:var(--muted2)">gốc ${fmt(base)}</div>` : ''}

        </div>

      </div>`;

  }).join('');

}



async function loadSettings() {

  await refreshBalance();

  updateResetButtonState();

  // Reset log

  const logRaw = await B.getResetLog();

  const log = JSON.parse(logRaw);

  const el = document.getElementById('reset-log-list');

  if (!log.length) {

    el.innerHTML = '<div style="font-size:13px;color:var(--muted2)">Chưa có lần reset nào.</div>';

  } else {

    el.innerHTML = log.map(r => `

      <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);font-size:12px">

        <span style="color:var(--muted2)">${r.date}</span>

        <span style="flex:1;color:var(--muted2)">Số dư trước: <strong style="color:var(--text)">${fmt(r.snapshot?.balance||0)}</strong></span>

        <span style="color:var(--blue)">TTS: ${fmt(r.snapshot?.net_worth||0)}</span>

      </div>`).join('');

  }

  // Tax log

  await loadTaxLog();

}



async function loadTaxLog() {

  const raw  = await B.getTaxLog();

  const log  = JSON.parse(raw);

  const el   = document.getElementById('tax-log-list');

  if (!log || !log.length) {

    el.innerHTML = '<div style="font-size:13px;color:var(--muted2)">Chưa có lịch sử thuế.</div>';

    return;

  }

  el.innerHTML = log.map(r => {

    const collected = r.collected;

    const color = collected ? 'var(--red)' : 'var(--green)';

    const icon  = collected ? '🏛️' : '✅';

    return `

    <div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--border);font-size:12px">

      <span>${icon}</span>

      <span style="color:var(--muted2);width:80px;flex-shrink:0">${r.date}</span>

      <span style="flex:1;color:var(--muted2)">

        TTS: <strong style="color:var(--text)">${fmt(r.total||0)}</strong>

        ${collected ? `| ${r.rate_pct?.toFixed(1)||'?'}%/ngày` : '| Miễn thuế'}

      </span>

      <span style="font-weight:800;color:${color}">${collected ? '-'+fmt(r.tax||0) : 'Miễn'}</span>

    </div>`;

  }).join('');

}



