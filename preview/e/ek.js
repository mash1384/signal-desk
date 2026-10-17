// E1~E3 공통: 입자 대신 벡터(SVG)로 그리는 일식 심볼 오프닝. 곡선·스프링, 무대 만들기, 글 들어오기, 스크롤 넘김.
// 심볼 기하(100×100): 원반 c(46,54) r30, 고리 = 원 A c(53,47) r31 에서 원 B c(46,54) r36.5 를 뺀 초승달 — brand/mark-L.svg 와 같다.
export const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
export const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
export const mobile = () => innerWidth < 900;
export const NS = 'http://www.w3.org/2000/svg';
export const G = { dx: 46, dy: 54, dr: 30, ax: 53, ay: 47, ar: 31, br: 36.5, cres: 'M82.39 56.87 A31 31 0 0 0 43.13 17.61 A36.5 36.5 0 0 1 82.39 56.87 Z' };
export const COL = { ink: '#0d253d', ind: '#533afd', lt: '#a9b3ff', up: '#12b07c', down: '#e5533f', grey: '#9aa7b8', guide: '#8a97ab' };
// cubic-bezier(x1,y1,x2,y2) — CSS 와 같은 곡선을 GSAP ease 로
export function bez(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const X = (t) => ((ax * t + bx) * t + cx) * t, Y = (t) => ((ay * t + by) * t + cy) * t, dX = (t) => (3 * ax * t + 2 * bx) * t + cx;
  return (x) => { if (x <= 0) return 0; if (x >= 1) return 1; let t = x; for (let i = 0; i < 8; i++) { const e = X(t) - x, d = dX(t); if (Math.abs(e) < 1e-6 || !d) break; t -= e / d; }
    let lo = 0, hi = 1; for (let i = 0; i < 20 && Math.abs(X(t) - x) > 1e-6; i++) { if (X(t) < x) lo = t; else hi = t; t = (lo + hi) / 2; } return Y(t); };
}
export const EASE = { out: bez(0.23, 1, 0.32, 1), inOut: bez(0.77, 0, 0.175, 1) };
// Apple 식 스프링(bounce) — GSAP 의 duration D 안에서 멈추도록: 체감 길이 = D/1.6, 남는 0.6 은 잔떨림이 가라앉는 시간
export function spring(D = 1.4, bounce = 0.2) {
  const z = 1 - bounce, w = (2 * Math.PI * 1.6) / D, wd = w * Math.sqrt(Math.max(1e-4, 1 - z * z));
  return (p) => { if (p >= 1) return 1; const t = p * D; return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t)); };
}
export function el(tag, attrs = {}, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
// 무대: 데스크톱은 글 오른쪽, 폰은 위쪽
export function stage(name) {
  const hero = document.getElementById('hero'), box = document.createElement('div'); box.className = 'stage ' + name; box.setAttribute('aria-hidden', 'true');
  const svg = el('svg', { viewBox: '0 0 100 100', overflow: 'visible' }); box.appendChild(svg); hero.appendChild(box); return { hero, box, svg };
}
export function revealCopy(delay = 0.4) {
  const els = document.querySelectorAll('.reveal');
  if (reduce) { gsap.to(els, { opacity: 1, duration: 0.4, delay: 0.1, onStart: () => els.forEach((e) => { e.style.transform = 'none'; e.style.filter = 'none'; }) }); return; }
  gsap.to(els, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.9, ease: EASE.out, stagger: 0.07, delay });
}
// 스크롤하면 글은 위로 사라지고 심볼은 작아지며 물러난다(다음 장면으로 넘김)
export function handoff(box) {
  gsap.registerPlugin(ScrollTrigger);
  const hero = document.getElementById('hero');
  const tl = gsap.timeline({ scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: 0.6 } });
  tl.to('.copy', { y: -70, opacity: 0, ease: 'none', duration: 0.6 }, 0).to(box, { scale: 0.86, opacity: 0, yPercent: -12, ease: 'none', duration: 1 }, 0)
    .to('#hud', { opacity: 0, ease: 'none', duration: 0.3 }, 0);
}
export const T = (en, ko) => (DFI.lang() === 'ko' ? ko : en);
