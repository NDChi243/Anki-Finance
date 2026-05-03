// ════════════════════════════════════════════

//  DEBUG TOOLS (1.1.0e)

// ════════════════════════════════════════════

async function runDebugScan() {

  const btn  = document.getElementById('debug-scan-btn');

  const out  = document.getElementById('debug-result');

  const min  = document.getElementById('debug-mini-status');

  if (!btn) return;

  btn.disabled = true;

  btn.textContent = '⏳ Đang quét...';

  out.style.display = 'block';

  out.innerHTML = '⏳ Đang kiểm tra dữ liệu...';

  min.textContent = '';

  try {

    const raw = await B.runDebugTools();

    const r = JSON.parse(raw);

    if (!r.ok) {

      out.innerHTML = '❌ ' + (r.error || 'Lỗi không xác định.');

      toast('err', '🔧 Gỡ lỗi thất bại!');

      return;

    }

    // Tạo báo cáo đẹp

    let html = '<div style="margin-bottom:8px;font-weight:700">✅ Kết quả gỡ lỗi</div>';

    if (r.cache_cleared) {

      html += '<div style="color:var(--green)">✔️ Bộ nhớ đệm (cache) đã được xoá</div>';

    }

    const noneFixed = r.fixed_none_keys || [];

    if (noneFixed.length > 0) {

      html += '<div style="color:var(--yellow);margin-top:4px">🔧 Đã sửa ' + noneFixed.length + ' key bị null/None:</div>';

      html += '<div style="font-size:10px;color:var(--muted2);max-height:120px;overflow-y:auto">';

      html += noneFixed.map(k => '&nbsp;&nbsp;• ' + k).join('<br>');

      html += '</div>';

    }

    const typeFixed = r.fixed_type_keys || [];

    if (typeFixed.length > 0) {

      html += '<div style="color:var(--yellow);margin-top:4px">🔧 Đã sửa ' + typeFixed.length + ' key sai kiểu dữ liệu:</div>';

      html += '<div style="font-size:10px;color:var(--muted2);max-height:120px;overflow-y:auto">';

      typeFixed.forEach(f => {

        html += '&nbsp;&nbsp;• <code>' + f.key + '</code>: expected <strong>' + f.expected + '</strong>, found <strong>' + f.found + '</strong><br>';

      });

      html += '</div>';

    }

    if (r.keys_ok > 0) {

      html += '<div style="color:var(--green);margin-top:4px">✔️ ' + r.keys_ok + '/' + r.total_scanned + ' keys hoạt động bình thường.</div>';

    }

    const errors = r.errors || [];

    if (errors.length > 0) {

      html += '<div style="color:var(--red);margin-top:4px">⚠️ ' + errors.length + ' lỗi phát sinh:</div>';

      html += '<div style="font-size:10px;color:var(--red);max-height:80px;overflow-y:auto">';

      errors.forEach(e => { html += '&nbsp;&nbsp;• ' + e + '<br>'; });

      html += '</div>';

    }

    if (noneFixed.length === 0 && typeFixed.length === 0 && errors.length === 0) {

      html += '<div style="color:var(--green);margin-top:4px">✨ Không phát hiện lỗi nào. Hệ thống sạch sẽ!</div>';

    }

    out.innerHTML = html;

    min.textContent = '🕒 Lần cuối: ' + new Date().toLocaleTimeString('vi-VN');

    toast('ok', '🔧 Gỡ lỗi hoàn tất!');

  } catch (e) {

    out.innerHTML = '❌ Lỗi: ' + e.message;

    toast('err', '🔧 Lỗi khi gỡ lỗi: ' + e.message);

  } finally {

    btn.disabled = false;

    btn.textContent = '🔍 Quét & Sửa lỗi';

  }

}

async function runDebugReport() {

  const out  = document.getElementById('debug-result');

  const min  = document.getElementById('debug-mini-status');

  const btn  = document.getElementById('debug-report-btn');

  if (!btn) return;

  btn.disabled = true;

  out.style.display = 'block';

  out.innerHTML = '⏝ Đang lấy báo cáo...';

  min.textContent = '';

  try {

    const raw = await B.getDebugReport();

    const r = JSON.parse(raw);

    if (!r.ok) {

      out.innerHTML = '❌ ' + (r.error || 'Lỗi không xác định.');

      return;

    }

    let html = '<div style="margin-bottom:8px;font-weight:700">📋 Báo cáo hệ thống</div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Phiên bản</span><span style="font-weight:700">v' + (r.version || '?') + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Anki version</span><span style="font-weight:700">' + (r.anki_version || '?') + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Profile</span><span style="font-weight:700">' + (r.profile || '?') + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Số dư hiện tại</span><span style="font-weight:700;color:var(--green)">' + fmt(r.balance || 0) + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Config keys đang hoạt động</span><span style="font-weight:700">' + r.active_keys + '/' + r.total_expected_keys + '</span></div>';

    html += '<div class="row-sb" style="padding:3px 0"><span>Cache entries</span><span style="font-weight:700">' + (r.cache_size || 0) + '</span></div>';

    const errors = r.errors || [];

    if (errors.length > 0) {

      html += '<div style="color:var(--red);margin-top:6px">⚠️ Lỗi: ' + errors.join('; ') + '</div>';

    }

    out.innerHTML = html;

    min.textContent = '🕒 Lần cuối: ' + new Date().toLocaleTimeString('vi-VN');

  } catch (e) {

    out.innerHTML = '❌ Lỗi: ' + e.message;

  } finally {

    btn.disabled = false;

  }

}



