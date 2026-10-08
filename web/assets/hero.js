// 첫 화면: 거대한 SIGNAL 글자가 창이 되어 그 너머로 Blender로 렌더한 파문 영상이 보인다.
// 스크롤하면 I 획 속으로 빨려 들어가 화면 가득 파문이 펼쳐진다. 글자 위치·크기는 CSS가 정한 .hx__word를 그대로 따른다.
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const seg = (p, a, b) => clamp((p - a) / (b - a));
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const TRACK = -0.045; // .hx__word 의 letter-spacing과 같게

function main() {
  const sec = document.getElementById('hx');
  if (!sec) return;
  const pin = sec.querySelector('.pin');
  const canvas = sec.querySelector('canvas');
  const ctx = canvas.getContext('2d');
  const word = sec.querySelector('.hx__word');
  const base = sec.dataset.video;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!base || !ctx || !word) return;
  if (!reduced) sec.classList.add('is-pinned');

  const caps = [...sec.querySelectorAll('[data-beat]')];
  // 글자 모양 마스크는 따로 그려 두었다가 영상 위에 찍어 낸다
  const mask = document.createElement('canvas');
  const mctx = mask.getContext('2d');
  let W = 0, H = 0, dpr = 1, variant = null, video = null, poster = null, lay = null, visible = true, raf = 0, font = '';
  const bg = getComputedStyle(sec).backgroundColor || '#0b0c0f';

  const progress = () => {
    if (!sec.classList.contains('is-pinned')) return 0;
    const r = sec.getBoundingClientRect(), range = sec.offsetHeight - pin.offsetHeight;
    return clamp(-r.top / (range || 1));
  };

  // CSS로 배치된 글자(줄마다 span)를 캔버스 좌표의 글리프 목록으로 옮긴다
  const layout = () => {
    const cs = getComputedStyle(word);
    const size = parseFloat(cs.fontSize);
    font = `${cs.fontWeight} ${size}px ${cs.fontFamily}`;
    ctx.font = font;
    const pr = pin.getBoundingClientRect();
    const fm = ctx.measureText('SIGNAL');
    const A = fm.fontBoundingBoxAscent ?? size * 0.9, D = fm.fontBoundingBoxDescent ?? size * 0.22;
    const glyphs = [];
    let anchor = null;
    for (const sp of word.querySelectorAll('span')) {
      const r = sp.getBoundingClientRect();
      let x = r.left - pr.left;
      const y = r.top - pr.top + (r.height - (A + D)) / 2 + A;
      for (const ch of sp.textContent) {
        const m = ctx.measureText(ch);
        const g = { ch, x, y, l: x - m.actualBoundingBoxLeft, r: x + m.actualBoundingBoxRight, t: y - m.actualBoundingBoxAscent, b: y + m.actualBoundingBoxDescent };
        glyphs.push(g);
        if (ch === 'I' && !anchor) anchor = g;
        x += m.width + TRACK * size;
      }
    }
    if (!anchor) return;
    const sw = anchor.r - anchor.l, sh = anchor.b - anchor.t;
    lay = { glyphs, anchor, ax: (anchor.l + anchor.r) / 2, ay: (anchor.t + anchor.b) / 2, smax: Math.max(W / sw, H / sh) * 1.15 };
  };

  const media = () => (video && video.readyState >= 2 ? video : poster && poster.complete && poster.naturalWidth ? poster : null);
  const drawMedia = (m, a, sc) => {
    if (!m || a <= 0.002) return;
    const iw = m.videoWidth || m.naturalWidth, ih = m.videoHeight || m.naturalHeight;
    const k = Math.max(W / iw, H / ih) * sc;
    ctx.globalAlpha = a;
    ctx.drawImage(m, (W - iw * k) / 2, (H - ih * k) / 2, iw * k, ih * k);
    ctx.globalAlpha = 1;
  };

  const draw = () => {
    if (!lay) return;
    const p = progress();
    const z = ease(seg(p, 0.06, 0.64));
    const s = Math.exp(Math.log(lay.smax) * z);
    // 들어갈수록 I 획의 가운데가 화면 가운데로 온다
    const cx = lay.ax + (W / 2 - lay.ax) * z, cy = lay.ay + (H / 2 - lay.ay) * z;
    const m = media(), sc = 1.08 - 0.08 * z, full = z >= 0.999;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, W, H);
    drawMedia(m, 1, sc);
    if (!full) {
      mctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      mctx.clearRect(0, 0, W, H);
      mctx.fillStyle = '#fff';
      mctx.font = font;
      mctx.translate(cx, cy); mctx.scale(s, s); mctx.translate(-lay.ax, -lay.ay);
      for (const g of lay.glyphs) {
        const L = cx + (g.l - lay.ax) * s, R = cx + (g.r - lay.ax) * s, T = cy + (g.t - lay.ay) * s, B = cy + (g.b - lay.ay) * s;
        if (R < 0 || L > W || B < 0 || T > H) continue;
        // 아주 크게 키우면 글자 렌더가 불안정한 브라우저가 있어, I 획은 같은 크기의 사각형으로 그린다
        if (g === lay.anchor && s > 6) mctx.fillRect(g.l, g.t, g.r - g.l, g.b - g.t);
        else mctx.fillText(g.ch, g.x, g.y);
      }
      // 검은 물 위에서도 글자 모양이 읽히도록 글자 안을 살짝 밝힌다(들어갈수록 사라진다)
      ctx.globalCompositeOperation = 'lighter';
      ctx.fillStyle = `rgba(30, 33, 40, ${(1 - z).toFixed(3)})`;
      ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'destination-in';
      ctx.drawImage(mask, 0, 0, W, H);
      ctx.globalCompositeOperation = 'destination-over';
      drawMedia(m, 0.07 * (1 - z), sc); // 글자 밖으로도 아주 옅게 비친다
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'source-over';
    }
    caps.forEach((el) => {
      const [c0, c1, c2, c3] = el.dataset.beat.split(',').map(Number);
      const v = Math.min(seg(p, c0, c1), 1 - seg(p, c2, c3));
      el.style.opacity = v.toFixed(3);
      el.style.visibility = v < 0.01 ? 'hidden' : 'visible';
      el.style.transform = v < 1 ? `translateY(${((1 - v) * 14).toFixed(1)}px)` : 'none';
    });
  };

  const tick = () => {
    raf = 0;
    draw();
    if (visible && video && !video.paused) raf = requestAnimationFrame(tick);
  };
  const kick = () => { if (!raf) raf = requestAnimationFrame(tick); };

  const setVariant = (v) => {
    if (v === variant) return;
    variant = v;
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => { if (variant === v) { poster = img; sec.classList.add('is-live'); kick(); } };
    img.src = `${base}ripple-${v}.webp`;
    if (reduced) return;
    if (video) { video.pause(); video.remove(); }
    const el = document.createElement('video');
    el.muted = true; el.loop = true; el.playsInline = true; el.preload = 'auto';
    el.setAttribute('muted', ''); el.setAttribute('playsinline', ''); el.setAttribute('aria-hidden', 'true');
    el.className = 'hx__video';
    el.src = `${base}ripple-${v}.mp4`;
    el.addEventListener('playing', kick);
    el.addEventListener('loadeddata', kick);
    pin.appendChild(el);
    video = el;
    if (visible) el.play().catch(() => {});
  };

  const resize = () => {
    W = pin.clientWidth; H = pin.clientHeight; dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = mask.width = Math.round(W * dpr); canvas.height = mask.height = Math.round(H * dpr);
    setVariant(W / Math.max(1, H) < 0.8 ? 'mobile' : 'desktop');
    layout();
    kick();
  };

  new IntersectionObserver(([e]) => {
    visible = e.isIntersecting;
    if (!video) return;
    if (visible) video.play().catch(() => {});
    else video.pause();
  }).observe(sec);
  window.addEventListener('scroll', kick, { passive: true });
  const start = () => { new ResizeObserver(resize).observe(pin); resize(); };
  // 글자 모양을 캔버스에 옮기기 전에 웹폰트를 기다린다(늦어도 1.5초 뒤엔 시작)
  Promise.race([document.fonts.load(`900 100px Geist`), new Promise((r) => setTimeout(r, 1500))]).then(start, start);
}

main();
