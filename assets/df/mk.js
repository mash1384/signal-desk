const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const EOUT = 'cubic-bezier(0.23, 1, 0.32, 1)';
function bez(x1, y1, x2, y2) { const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  return (x) => { if (x <= 0) return 0; if (x >= 1) return 1; let lo = 0, hi = 1, t = x; for (let i = 0; i < 40; i++) { if (((ax * t + bx) * t + cx) * t < x) lo = t; else hi = t; t = (lo + hi) / 2; } return ((ay * t + by) * t + cy) * t; }; }
const FLY = bez(0.7, 0, 0.2, 1);
const done = () => dispatchEvent(new Event('df-intro-done'));
export async function intro(name, { flyAt = 4.32, base = '../mo/' } = {}) {
  const hd = document.querySelector('.hd'), logo = hd.querySelector('.logo'), rest = hd.querySelectorAll('.nav, .lang, .btn'), copy = document.querySelectorAll('.reveal');
  const showCopy = (delay = 0) => copy.forEach((e, i) => e.animate([{ opacity: 0, transform: 'translateY(14px)' }, { opacity: 1, transform: 'none' }], { duration: 900, delay: delay + i * 70, easing: EOUT, fill: 'both' }));
  const rp = document.querySelector('.replay'); if (rp) rp.onclick = () => location.reload();
  let inner = false; try { inner = !!document.referrer && new URL(document.referrer).origin === location.origin && !/[?&]intro\b/.test(location.search); } catch (e) {}
  if (reduce) { copy.forEach(e => { e.style.opacity = 1; }); done(); return; }
  if (inner) { showCopy(); done(); return; }
  if (window.DF_NOINTRO) { showCopy(); done(); return; }
  const metaP = fetch(`${base}${name}.json`).then((r) => r.json()).catch(() => null);
  let ov = document.getElementById('intro');
  if (!ov) { ov = document.createElement('div'); ov.className = 'intro'; ov.id = 'intro'; ov.innerHTML = `<div class="ibg"></div><video muted playsinline autoplay preload="auto" src="${base}${name}.mp4"></video><button type="button" class="skip">Skip</button>`; document.body.appendChild(ov); }
  const v = ov.querySelector('video'), bg = ov.querySelector('.ibg');
  logo.style.opacity = '0'; rest.forEach((e) => { e.style.opacity = '0'; e.style.willChange = 'opacity'; });   // 층을 미리 만들어 둔다
  document.documentElement.classList.add('intro-on');
  let flown = false, ended = false;
  const finishNoIntro = () => { if (ended) return; ended = flown = true; ov.remove(); logo.style.opacity = ''; rest.forEach((e) => { e.style.opacity = ''; }); document.documentElement.classList.remove('intro-on'); showCopy(); done(); };
  let meta = null; metaP.then((m) => { meta = m; });
  const fly = async () => {
    if (flown || ended) return; flown = true;
    if (!meta) meta = await Promise.race([metaP, new Promise((r) => setTimeout(() => r(null), 800))]);
    await Promise.race([document.fonts.load('15px Michroma'), new Promise((r) => setTimeout(r, 400))]);   // 헤더 글자가 제 글꼴인지
    if (!meta) { finishNoIntro(); return; }
    const vr = v.getBoundingClientRect(), side = Math.min(vr.width, vr.height), vx = vr.left + (vr.width - side) / 2, vy = vr.top + (vr.height - side) / 2;
    const [bx, by, bs] = meta.box; const t = logo.querySelector('svg').getBoundingClientRect(), lr = logo.getBoundingClientRect();
    const k = (bs * side) / t.width, dx = vx + bx * side - t.left, dy = vy + by * side - t.top;
    logo.style.transformOrigin = `${t.left - lr.left}px ${t.top - lr.top}px`; hd.style.zIndex = '90';
    const N = 48, kf = [];
    for (let i = 0; i <= N; i++) { const p = FLY(i / N), s = Math.exp(Math.log(k) * (1 - p)); kf.push({ transform: `translate(${dx * (1 - p)}px, ${dy * (1 - p)}px) scale(${s})` }); }
    logo.style.opacity = '1'; const a = logo.animate(kf, { duration: 1050, easing: 'linear', fill: 'backwards' }); v.style.visibility = 'hidden';
    bg.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 650, delay: 280, easing: 'ease', fill: 'forwards' });
    showCopy(520);
    a.onfinish = () => {
      ov.remove(); hd.style.zIndex = ''; logo.style.transformOrigin = ''; document.documentElement.classList.remove('intro-on');
      rest.forEach((e, i) => { const f = e.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 420, delay: i * 40, easing: 'ease', fill: 'backwards' }); e.style.opacity = ''; f.onfinish = () => { e.style.willChange = ''; }; });
      done();
    };
  };
  if ('requestVideoFrameCallback' in v) { const cb = (now, md) => { if (md.mediaTime >= flyAt) fly(); else v.requestVideoFrameCallback(cb); }; v.requestVideoFrameCallback(cb); }
  else v.addEventListener('timeupdate', () => { if (v.currentTime >= flyAt) fly(); });
  v.addEventListener('ended', fly);
  const skip = () => { if (flown || ended) return; try { v.currentTime = Math.max(0, (v.duration || 4.5) - 0.05); } catch (e) {} v.pause(); setTimeout(fly, 80); };
  ov.querySelector('.skip').onclick = skip; addEventListener('keydown', skip, { once: true }); addEventListener('wheel', skip, { once: true, passive: true }); addEventListener('touchmove', skip, { once: true, passive: true });
  if (v.paused && !v.ended) v.play().catch(finishNoIntro);
  if (v.ended || v.currentTime >= flyAt) fly();                    // 이 모듈이 늦게 와서 영상이 이미 끝났으면 바로
  else setTimeout(() => { if (!flown && v.currentTime === 0) finishNoIntro(); }, 2500);   // 재생 요청이 걸린 채(paused=false) 멈춰도   // 끝내 재생이 안 되면(저전력 모드 등) — 빈 화면을 오래 두지 않게
}
