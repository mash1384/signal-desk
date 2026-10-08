// 첫 화면: Blender로 미리 렌더링한 지형 비행 프레임을 스크롤에 맞춰 넘긴다.
// 프레임은 렌더 시점의 데이터로 고정되어 있고, 기사 카드는 anchors.json의 프레임별 핀 화면 좌표에 붙인다.
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const seg = (p, a, b) => clamp((p - a) / (b - a));

function main() {
  const sec = document.getElementById('h3d');
  if (!sec) return;
  const pin = sec.querySelector('.pin');
  const canvas = sec.querySelector('canvas');
  const ctx = canvas.getContext('2d');
  const base = sec.dataset.frames;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!base || !ctx) return;
  sec.classList.add('has-webgl');
  if (!reduced) sec.classList.add('is-pinned');

  let variant = null, meta = null, imgs = [], W = 0, H = 0, dpr = 1, lastKey = '';
  const caps = [...sec.querySelectorAll('[data-beat]')];
  const labels = [...sec.querySelectorAll('.tpin')];

  const pickVariant = () => (pin.clientWidth / Math.max(1, pin.clientHeight) < 0.9 ? 'mobile' : 'desktop');
  const progress = () => {
    if (!sec.classList.contains('is-pinned')) return 0;
    const r = sec.getBoundingClientRect(), range = sec.offsetHeight - pin.offsetHeight;
    return clamp(-r.top / (range || 1));
  };
  const cur = () => (meta ? progress() * (meta.frames - 1) : 0);

  const load = async (v) => {
    variant = v;
    const m = await fetch(`${base}${v}/anchors.json`).then((r) => r.json());
    if (variant !== v) return;
    meta = m;
    imgs = new Array(meta.frames);
    const one = (i) => new Promise((res) => {
      const im = new Image();
      im.decoding = 'async';
      im.onload = () => { if (variant === v) { imgs[i] = im; if (i === 0 || Math.abs(i - cur()) < 2) draw(true); } res(); };
      im.onerror = res;
      im.src = `${base}${v}/f${String(i).padStart(3, '0')}.webp`;
    });
    // 첫 프레임 → 4칸 간격 → 2칸 → 나머지 순으로 받아, 일찍부터 대충이라도 스크롤이 된다
    await one(0);
    sec.classList.add('is-ready');
    const order = [], seen = new Set([0]);
    for (const s of [4, 2, 1]) for (let i = 0; i < meta.frames; i += s) if (!seen.has(i)) { seen.add(i); order.push(i); }
    for (let i = 0; i < order.length; i += 6) await Promise.all(order.slice(i, i + 6).map(one));
  };

  const nearest = (i, dir) => {
    for (let k = 0; k < meta.frames; k++) {
      const j = i + k * dir;
      if (j >= 0 && j < meta.frames && imgs[j]) return j;
    }
    return -1;
  };
  // 화면을 덮도록 맞춘 그림 영역
  const fit = () => {
    const [iw, ih] = meta.size, s = Math.max(W / iw, H / ih);
    return { s, ox: (W - iw * s) / 2, oy: (H - ih * s) / 2, iw, ih };
  };
  const show = (el, v) => {
    el.style.opacity = v.toFixed(3);
    el.style.visibility = v < 0.01 ? 'hidden' : 'visible';
  };

  const draw = (force) => {
    if (!meta) return;
    const p = progress(), f = p * (meta.frames - 1);
    const key = f.toFixed(3) + W + 'x' + H;
    if (!force && key === lastKey) return;
    lastKey = key;
    // 가장 가까운 프레임을 그린다(겹쳐 그리면 움직이는 핀이 두 겹으로 보인다). 아직 안 받은 프레임이면 받아 둔 가장 가까운 것
    const r = Math.round(f), lo = nearest(r, -1), hi = nearest(r, 1);
    const a = lo < 0 ? hi : hi < 0 ? lo : (r - lo <= hi - r ? lo : hi);
    const { s, ox, oy, iw, ih } = fit();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (a >= 0) ctx.drawImage(imgs[a], ox, oy, iw * s, ih * s);
    caps.forEach((el) => {
      const [c0, c1, c2, c3] = el.dataset.beat.split(',').map(Number);
      const v = Math.min(seg(p, c0, c1), 1 - seg(p, c2, c3));
      show(el, v);
      el.style.transform = v < 1 ? `translateY(${((1 - v) * 16).toFixed(1)}px)` : 'none';
    });
    const fi = Math.round(f);
    labels.forEach((el, i) => {
      const hw = meta.slots[i];
      if (!hw) { show(el, 0); return; }
      const v = Math.min(seg(p, hw[0] - 0.03, hw[0] + 0.02), 1 - seg(p, hw[1] - 0.02, hw[1] + 0.03));
      show(el, v);
      if (v > 0 && variant === 'desktop') {
        const xy = meta.xy[fi][i];
        const sx = ox + xy[0] * iw * s, sy = oy + xy[1] * ih * s;
        const lw = el.offsetWidth, lh = el.offsetHeight;
        el.style.left = clamp(sx + 24, 16, W - lw - 16) + 'px';
        el.style.top = clamp(sy - lh - 16, 16, H - lh - 16) + 'px';
      }
      el.style.transform = v < 1 ? `translateY(${((1 - v) * 10).toFixed(1)}px)` : 'none';
    });
  };

  const resize = () => {
    W = pin.clientWidth; H = pin.clientHeight; dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    const v = pickVariant();
    if (v !== variant) load(v);
    draw(true);
  };
  new ResizeObserver(resize).observe(pin);
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { ticking = false; draw(false); });
  }, { passive: true });
  resize();
}

main();
