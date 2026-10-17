// 첫 화면: 거대한 SIGNAL 글자가 창이 되어 그 너머로 Blender로 렌더한 파문 영상이 보인다.
// 스크롤하면 I 획 속으로 빨려 들어가 화면 가득 파문이 펼쳐진다. 글자 위치·크기는 CSS가 정한 .hx__word를 그대로 따른다.
// 영상은 브라우저가 직접 재생하고(<video>), 캔버스는 그 위를 배경색으로 덮은 뒤 글자 모양만 뚫는다.
// 영상 프레임을 캔버스로 옮기지 않아 휴대폰에서도 가볍고, 스크롤 값은 짧은 관성으로 따라가 휠 한 칸에도 끊기지 않는다.
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const seg = (p, a, b) => clamp((p - a) / (b - a));
const easeSine = (t) => 0.5 - Math.cos(Math.PI * t) / 2;
const TRACK = -0.045; // .hx__word 의 letter-spacing과 같게
const LAG = 0.09;     // 스크롤을 따라가는 시간 상수(초)

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

  // 무대: 영상 → 글자 안을 살짝 밝히는 막 → 글자 모양으로 뚫린 캔버스. 한 덩어리로 나타난다
  const stage = document.createElement('div');
  stage.className = 'hx__stage';
  stage.setAttribute('aria-hidden', 'true');
  const video = document.createElement('video');
  video.className = 'hx__video';
  video.muted = true; video.loop = true; video.playsInline = true; video.preload = 'auto';
  video.setAttribute('muted', ''); video.setAttribute('playsinline', '');
  const lift = document.createElement('div');
  lift.className = 'hx__lift';
  pin.insertBefore(stage, canvas);
  stage.append(video, lift, canvas);

  const caps = [...sec.querySelectorAll('[data-beat]')];
  const bg = getComputedStyle(sec).backgroundColor || '#0b0c0f';
  let W = 0, H = 0, dpr = 1, variant = null, lay = null, font = '', visible = true, raf = 0;
  let top = 0, range = 1, target = 0, cur = 0, last = 0, drawn = -1, ready = false;

  const measure = () => {
    top = sec.getBoundingClientRect().top + scrollY;
    range = Math.max(1, sec.offsetHeight - pin.offsetHeight);
  };
  const readTarget = () => (sec.classList.contains('is-pinned') ? clamp((scrollY - top) / range) : 0);

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

  const draw = (p) => {
    if (!lay) return;
    // 지수 확대(크기 비율이 일정하게 변함) + 시작·끝만 부드럽게
    const z = easeSine(seg(p, 0.05, 0.68));
    const s = Math.exp(Math.log(lay.smax) * z);
    const cx = lay.ax + (W / 2 - lay.ax) * z, cy = lay.ay + (H / 2 - lay.ay) * z;
    video.style.transform = `scale(${(1.08 - 0.08 * z).toFixed(4)})`;
    lift.style.opacity = (1 - z).toFixed(3);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, W, H);
    if (z < 0.999) {
      // 배경색으로 덮되 글자 밖으로도 영상이 아주 옅게 비치게 한다
      ctx.globalAlpha = 1 - 0.07 * (1 - z);
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'destination-out';
      ctx.font = font;
      ctx.fillStyle = '#000';
      ctx.translate(cx, cy); ctx.scale(s, s); ctx.translate(-lay.ax, -lay.ay);
      for (const g of lay.glyphs) {
        const L = cx + (g.l - lay.ax) * s, R = cx + (g.r - lay.ax) * s, T = cy + (g.t - lay.ay) * s, B = cy + (g.b - lay.ay) * s;
        if (R < 0 || L > W || B < 0 || T > H) continue;
        // 아주 크게 키우면 글자 렌더가 불안정한 브라우저가 있어, I 획은 같은 크기의 사각형으로 뚫는다
        if (g === lay.anchor && s > 6) ctx.fillRect(g.l, g.t, g.r - g.l, g.b - g.t);
        else ctx.fillText(g.ch, g.x, g.y);
      }
    }
    caps.forEach((el) => {
      const [c0, c1, c2, c3] = el.dataset.beat.split(',').map(Number);
      const v = Math.min(seg(p, c0, c1), 1 - seg(p, c2, c3));
      const key = v.toFixed(3);
      if (el._v === key) return;
      el._v = key;
      el.style.opacity = key;
      el.style.visibility = v < 0.01 ? 'hidden' : 'visible';
      el.style.transform = v < 1 ? `translateY(${((1 - v) * 14).toFixed(1)}px)` : 'none';
    });
    drawn = p;
  };

  const frame = (now) => {
    raf = 0;
    const dt = last ? Math.min(0.1, (now - last) / 1000) : 1 / 60;
    last = now;
    target = readTarget();
    cur += (target - cur) * (1 - Math.exp(-dt / LAG));
    if (Math.abs(target - cur) < 0.0004) cur = target;
    if (cur !== drawn) draw(cur);
    if (cur !== target) raf = requestAnimationFrame(frame);
    else last = 0;
  };
  const kick = () => { if (!raf && ready) raf = requestAnimationFrame(frame); };

  const setVariant = (v) => {
    if (v === variant) return;
    variant = v;
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => { if (variant === v) { ready = true; drawn = -1; kick(); requestAnimationFrame(() => sec.classList.add('is-live')); } };
    img.src = `${base}ripple-${v}.webp`;
    video.poster = img.src;
    if (reduced) return;
    video.src = `${base}ripple-${v}.mp4`;
    if (visible) video.play().catch(() => {});
  };

  const resize = () => {
    W = pin.clientWidth; H = pin.clientHeight; dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    measure();
    setVariant(W / Math.max(1, H) < 0.8 ? 'mobile' : 'desktop');
    layout();
    // 크기가 바뀌면 관성 없이 바로 맞춘다
    cur = target = readTarget(); drawn = -1;
    if (ready) draw(cur);
  };

  new IntersectionObserver(([e]) => {
    visible = e.isIntersecting;
    if (reduced) return;
    if (visible) video.play().catch(() => {});
    else video.pause();
  }).observe(sec);
  window.addEventListener('scroll', kick, { passive: true });
  const start = () => { new ResizeObserver(resize).observe(pin); resize(); };
  // 글자 모양을 캔버스에 옮기기 전에 웹폰트를 기다린다(늦어도 1.5초 뒤엔 시작)
  Promise.race([document.fonts.load(`900 100px Geist`), new Promise((r) => setTimeout(r, 1500))]).then(start, start);
}

main();
