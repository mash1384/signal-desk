// B1~B3 공통: Blender 로 렌더한 오프닝 영상(정사각, 배경 = 페이지 색)을 첫 화면 오른쪽(폰은 위)에 놓고 재생.
// 영상 가장자리는 둥글게 흐려 배경과 이어 붙인다. 영상이 끝나면 마지막 프레임(= 로고)에서 멈춘다.
// 자동 재생이 막히면(저전력 모드 등) 마지막 프레임 이미지를 바로 보여 주고 글을 띄운다. 움직임 줄이기 설정이면 재생하지 않는다.
export const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const out = (x) => 1 - Math.pow(1 - x, 3);
export function hero({ name, copyAt = 3.6, bg = null }) {
  const h = document.getElementById('hero'), box = document.createElement('div'); box.className = 'stage'; box.setAttribute('aria-hidden', 'true');
  const v = document.createElement('video'); Object.assign(v, { muted: true, playsInline: true, preload: 'auto', poster: `../b/${name}-first.jpg` }); v.setAttribute('muted', ''); v.setAttribute('playsinline', '');
  v.innerHTML = `<source src="../b/${name}.mp4" type="video/mp4">`; box.appendChild(v); h.appendChild(box);
  let shown = false; const reveal = (d = 0) => { if (shown) return; shown = true; const els = document.querySelectorAll('.reveal');
    if (reduce) els.forEach((e) => { e.style.cssText = 'opacity:1;transform:none;filter:none'; });
    else gsap.to(els, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.9, ease: 'expo.out', stagger: 0.07, delay: d }); };
  const last = () => { v.poster = `../b/${name}-last.jpg`; v.removeAttribute('src'); v.querySelectorAll('source').forEach((s) => s.remove()); v.load(); if (bg) paint(1e9); reveal(); };
  // 배경색이 영상과 함께 바뀌는 후보(B2): 첫 화면 배경·헤더 글자색을 영상 시간에 맞춘다
  const paint = (t) => { if (!bg) return; const c = bg(t); h.style.backgroundColor = c.css; document.body.classList.toggle('dk', c.dark); };
  if (bg) paint(0);
  if (reduce) { last(); return { v, box }; }
  const tick = () => { paint(v.currentTime); if (v.currentTime >= copyAt) reveal(); if (!v.ended) requestAnimationFrame(tick); else paint(v.duration); };
  v.addEventListener('playing', () => requestAnimationFrame(tick), { once: true });
  v.play().catch(() => last());
  setTimeout(() => { if (v.currentTime === 0 && v.paused) last(); }, 2500);
  // 다시 보기
  document.querySelector('.replay').onclick = () => { v.currentTime = 0; v.play(); };
  return { v, box };
}
// sRGB ↔ 선형(Blender 와 같은 섞기)
export const lin = (c) => (c / 255 <= 0.04045 ? c / 255 / 12.92 : ((c / 255 + 0.055) / 1.055) ** 2.4);
export const srgb = (l) => Math.round(255 * (l <= 0.0031308 ? l * 12.92 : 1.055 * l ** (1 / 2.4) - 0.055));
export function inout(x) { // cubic-bezier(0.77, 0, 0.175, 1)
  const x1 = 0.77, y1 = 0, x2 = 0.175, y2 = 1, cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  if (x <= 0) return 0; if (x >= 1) return 1; let lo = 0, hi = 1, t = x; for (let i = 0; i < 40; i++) { const X = ((ax * t + bx) * t + cx) * t; if (X < x) lo = t; else hi = t; t = (lo + hi) / 2; } return ((ay * t + by) * t + cy) * t;
}
