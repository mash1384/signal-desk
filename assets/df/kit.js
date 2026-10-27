import * as THREE from 'three';
export const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
export const mobile = () => innerWidth < 900;
export function renderer(canvas, { alpha = false, clear = 0xffffff } = {}) {
  const r = new THREE.WebGLRenderer({ canvas, antialias: true, alpha, powerPreference: 'high-performance' });
  r.setPixelRatio(Math.min(devicePixelRatio || 1, mobile() ? 1.5 : 2));
  if (!alpha) r.setClearColor(clear, 1);
  return r;
}
export function loop(r, scene, camera, tick) {
  const hero = document.getElementById('hero');
  let on = true, last = performance.now();
  new IntersectionObserver((e) => { on = e[0].isIntersecting; }).observe(hero);
  const size = () => { const w = hero.clientWidth, h = hero.clientHeight; r.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); };
  size(); addEventListener('resize', size);
  const f = (now) => { requestAnimationFrame(f); if (!on || document.hidden) { last = now; return; } const dt = Math.min(0.05, (now - last) / 1000); last = now; tick(now / 1000, dt); r.render(scene, camera); };
  requestAnimationFrame(f);
  return size;
}
export const pointer = { x: 0, y: 0, tx: 0, ty: 0, active: false };
addEventListener('pointermove', (e) => { pointer.tx = e.clientX / innerWidth * 2 - 1; pointer.ty = -(e.clientY / innerHeight * 2 - 1); pointer.active = true; }, { passive: true });
export function easePointer(k = 0.06) { pointer.x += (pointer.tx - pointer.x) * k; pointer.y += (pointer.ty - pointer.y) * k; }
export function revealCopy(delay = 0.4) {
  if (reduce) { document.querySelectorAll('.reveal').forEach((e) => { e.style.cssText = 'opacity:1;transform:none;filter:none'; }); return; }
  gsap.to('.reveal', { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.9, ease: 'power3.out', stagger: 0.1, delay });
}
export const data = { flash: DFD.flash(), klines: fetch('https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=15m&limit=96').then((r) => r.json()).then((k) => k.map((x) => +x[4])).catch(() => null) };
export const VCOL = { '호재': new THREE.Color('#12b07c'), '악재': new THREE.Color('#e5533f'), '중립': new THREE.Color('#9aa7b8') };
