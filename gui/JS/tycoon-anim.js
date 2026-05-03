// ============================================
//  NUMBER ANIMATION
// ============================================

const _tycoonAnimRafs = new WeakMap();

function _readAnimatedNumber(el, fallback = 0) {
  if (!el) return fallback;
  const raw = Number(el.dataset.animValue);
  return Number.isFinite(raw) ? raw : fallback;
}

function _setAnimatedNumberMeta(el, options = {}) {
  if (!el) return;
  if (options.format !== undefined) el.dataset.animFormat = options.format;
  if (options.prefix !== undefined) el.dataset.animPrefix = options.prefix;
  if (options.suffix !== undefined) el.dataset.animSuffix = options.suffix;
  if (options.decimals !== undefined) el.dataset.animDecimals = String(options.decimals);
}

function _formatAnimatedNumber(el, value) {
  const format = el?.dataset.animFormat || 'plain';
  const prefix = el?.dataset.animPrefix || '';
  const suffix = el?.dataset.animSuffix || '';
  const decimals = Number(el?.dataset.animDecimals || 0);
  const rounded = decimals > 0 ? Number(value.toFixed(decimals)) : Math.round(value);

  let body = String(rounded);
  if (format === 'money') {
    body = typeof fmt === 'function' ? fmt(rounded) : rounded.toLocaleString('vi-VN');
  } else if (format === 'locale') {
    body = rounded.toLocaleString('vi-VN');
  } else if (format === 'fixed') {
    body = rounded.toFixed(decimals);
  }

  return `${prefix}${body}${suffix}`;
}

function _paintAnimatedNumber(el, value) {
  if (!el) return;
  el.dataset.animValue = String(value);
  el.textContent = _formatAnimatedNumber(el, value);
}

function animateNumber(el, from, to, duration = 400) {
  if (!el) return;

  const startValue = Number(from);
  const endValue = Number(to);
  if (!Number.isFinite(startValue) || !Number.isFinite(endValue)) {
    _paintAnimatedNumber(el, Number.isFinite(endValue) ? endValue : 0);
    return;
  }

  const activeRaf = _tycoonAnimRafs.get(el);
  if (activeRaf) cancelAnimationFrame(activeRaf);

  const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (duration <= 0 || reduceMotion || startValue === endValue) {
    _paintAnimatedNumber(el, endValue);
    return;
  }

  const startAt = performance.now();
  const delta = endValue - startValue;

  const step = (now) => {
    const progress = Math.min(1, (now - startAt) / duration);
    const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
    _paintAnimatedNumber(el, startValue + delta * eased);

    if (progress < 1) {
      _tycoonAnimRafs.set(el, requestAnimationFrame(step));
    } else {
      _tycoonAnimRafs.delete(el);
    }
  };

  _tycoonAnimRafs.set(el, requestAnimationFrame(step));
}

function setAnimatedNumberText(el, value, options = {}) {
  if (!el) return;
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    if (options.fallbackText !== undefined) el.textContent = options.fallbackText;
    return;
  }

  _setAnimatedNumberMeta(el, options);
  const from = _readAnimatedNumber(el, numericValue);
  animateNumber(el, from, numericValue, options.duration ?? 400);
}
