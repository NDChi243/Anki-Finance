// ════════════════════════════════════════════

//  INVENTORY

// ════════════════════════════════════════════

async function reloadImages() {

  await B.refreshImageCache();

  const dir = await B.getImagesDir();

  document.getElementById('img-dir-path').textContent = dir;

  document.getElementById('img-dir-hint').style.display = 'block';

  await loadShop();

  toast('info', '🖼️ Đã làm mới cache ảnh!');

}



async function loadInventory() {

  // Kiểm tra đồ thiu trước

  const spoiledRaw = await B.checkSpoiledFood();

  const spoiled = JSON.parse(spoiledRaw);

  if (spoiled.length > 0) {

    toast('err', `🍂 ${spoiled.length} mặt hàng đồ ăn đã thiu và bị xoá khỏi kho!`);

  }



  const inv = JSON.parse(await B.getInventoryWithFreshness());

  const g   = document.getElementById('inv-grid');

  const total = inv.reduce((a,i)=>a+(i.quantity||1),0);

  document.getElementById('inv-badge').textContent = `${inv.length} loại • ${total} mặt hàng`;



  if (!inv.length) {

    g.innerHTML = `<div class="empty" style="grid-column:1/-1">

      <div class="ei">🎒</div>

      <p>Kho trống — ghé <a href="#" onclick="go('shop');return false" style="color:var(--accent2)">cửa hàng</a> nhé!</p>

    </div>`;

    return;

  }



  // Load active boosts để hiển thị strip

  await refreshBoostStrip();



  g.innerHTML = inv.map(i => {

    const isFood  = i.is_food;
    const isStudy = i.is_study;

    const eff    = i.effect || {};

    // REQ2 FIX: dùng active_slot thực từ Python freshness dict

    const activeSlot = i.active_slot || '';

    const slots      = i.food_slots || [];

    const firstSlot  = slots[0] || null;



    let foodExtra = '';

    if (isFood) {

      // Freshness bar

      let freshBar = '';

      if (firstSlot) {

        const pct   = firstSlot.fresh_pct || 0;

        const remH  = firstSlot.remaining_h || 0;

        const col   = pct > 50 ? 'var(--green)' : pct > 20 ? 'var(--yellow)' : 'var(--red)';

        freshBar = `

          <div style="width:100%;margin-top:4px">

            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">

              <span>Độ tươi</span><span style="color:${col}">${remH.toFixed(1)}h còn lại</span>

            </div>

            <div class="fresh-wrap" style="width:100%">

              <div style="height:100%;width:${pct}%;background:${col};border-radius:2px;transition:width .3s"></div>

            </div>

          </div>`;

      }

      // Effect description

      const effDesc = eff.desc || '';

      const canUse  = !!activeSlot;

      foodExtra = `

        <div style="font-size:11px;color:var(--green);margin-top:2px;text-align:center">${effDesc}</div>

        ${freshBar}

        <button class="btn btn-green" style="font-size:11px;padding:4px 10px;margin-top:6px;width:100%"

          ${canUse ? '' : 'disabled'}

          onclick="useFoodItem('${i.id}','${activeSlot}')">

          ${canUse ? '✨ Dùng ngay' : '⚠️ Không có slot'}

        </button>

        ${slots.length > 1 ? `<div style="font-size:10px;color:var(--muted2);margin-top:2px">${slots.length} phần trong kho</div>` : ''}`;

    } else if (isStudy) {
      let freshBar = '';
      if (firstSlot) {
        const pct   = firstSlot.fresh_pct || 0;
        const remH  = firstSlot.remaining_h || 0;
        const col   = pct > 50 ? 'var(--green)' : pct > 20 ? 'var(--yellow)' : 'var(--red)';
        freshBar = `

          <div style="width:100%;margin-top:4px">

            <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted2)">

              <span>Hạn sử dụng</span><span style="color:${col}">${remH.toFixed(1)}h còn lại</span>

            </div>

            <div class="fresh-wrap" style="width:100%">

              <div style="height:100%;width:${pct}%;background:${col};border-radius:2px;transition:width .3s"></div>

            </div>

          </div>`;

      }

      const effDesc = eff.desc || '';

      const canUse  = !!activeSlot;

      foodExtra = `

        <div style="font-size:11px;color:var(--accent2);margin-top:2px;text-align:center">${effDesc}</div>

        ${freshBar}

        <button class="btn btn-primary" style="font-size:11px;padding:4px 10px;margin-top:6px;width:100%"

          ${canUse ? '' : 'disabled'}

          onclick="useStudyItem('${i.id}','${activeSlot}')">

          ${canUse ? '📖 Áp dụng' : '⚠️ Hết hạn'}

        </button>

        ${slots.length > 1 ? `<div style="font-size:10px;color:var(--muted2);margin-top:2px">${slots.length} cái trong kho</div>` : ''}`;

    }



    return `

    <div class="inv-card ${isFood ? 'food-card' : ''}">

      <div class="item-img-wrap" style="width:90px;height:90px">

        ${i.image_url

          ? `<img class="item-img" style="width:90px;height:90px" src="${i.image_url}" alt="${i.name}">`

          : `<div style="font-size:36px">${i.emoji||'📦'}</div>`

        }

      </div>

      <div style="font-size:13px;font-weight:700">${i.name}</div>

      <div style="font-size:11px;color:var(--muted2)">${i.description||''}</div>

      ${!isFood && i.effect_html ? `<div class="effect-row">${i.effect_html}</div>` : ''}

      <span class="badge ${isFood ? 'badge-green' : 'badge-purple'}" style="font-size:10px">

        ${isFood ? '🍽️ ' : ''}${i.category||''}

      </span>

      <span class="badge badge-green">x${i.quantity}</span>

      <div style="font-size:11px;color:var(--yellow);font-weight:700">${fmt(i.price)}</div>

      ${foodExtra}

    </div>`;

  }).join('');

}



async function useFoodItem(itemId, slotId) {

  const res = JSON.parse(await B.activateFoodBoost(itemId, slotId));

  if (res.ok) {

    toast('ok', `⚡ ${res.message || 'Boost đã kích hoạt!'}`);

    await loadInventory();

    await refreshBoostStrip();

  } else {

    toast('err', '❌ ' + (res.error || 'Lỗi kích hoạt boost'));

  }

}



async function useStudyItem(itemId, slotId) {

  const res = JSON.parse(await B.activateFoodBoost(itemId, slotId));

  if (res.ok) {

    toast('ok', `📖 ${res.message || 'Đã áp dụng vật phẩm học tập!'}`);

    await loadInventory();

    await refreshBoostStrip();

  } else {

    toast('err', '❌ ' + (res.error || 'Lỗi kích hoạt vật phẩm học tập'));

  }

}


