// E1 · 일식 — 남보라 원(빛)이 먼저 떠오르고, 남색 원반이 왼쪽 아래에서 미끄러져 들어와 가린다.
// 다 가리는 순간 남는 테두리가 Delfona 의 초승달 고리가 되고, 빛 테두리(코로나)가 한 번 퍼진다. 이후 마우스를 따라 원반이 조금 움직여 고리 두께가 바뀐다.
import { G, COL, EASE, el, stage, revealCopy, handoff, reduce, fine, mobile } from './ek.js?v=1501';
const { box, svg } = stage('e1');
const defs = el('defs', {}, svg);
const glow = el('radialGradient', { id: 'e1g', cx: '50%', cy: '50%', r: '50%' }, defs);
el('stop', { offset: '0', 'stop-color': '#8f86ff' }, glow); el('stop', { offset: '1', 'stop-color': COL.ind }, glow);
const mask = el('mask', { id: 'e1m', maskUnits: 'userSpaceOnUse', x: -60, y: -60, width: 220, height: 220 }, defs);
el('rect', { x: -60, y: -60, width: 220, height: 220, fill: '#fff' }, mask);
const hole = el('circle', { cx: G.dx, cy: G.dy, r: G.br, fill: '#000' }, mask);
const coronas = [0, 1].map(() => el('circle', { cx: G.ax, cy: G.ay, r: G.ar, fill: 'none', stroke: COL.ind, 'stroke-width': 0.5, opacity: 0, 'vector-effect': 'non-scaling-stroke' }, svg));
const sun = el('circle', { cx: G.ax, cy: G.ay, r: G.ar, fill: 'url(#e1g)', mask: 'url(#e1m)' }, svg);
const moon = el('circle', { cx: G.dx, cy: G.dy, r: G.dr, fill: COL.ink }, svg);
// 원반 위치(최종 자리 기준 오프셋) — 원반과 가림 구멍이 같이 움직인다
const P = { x: -52, y: 52, px: 0, py: 0 };
const put = () => { const x = G.dx + P.x + P.px, y = G.dy + P.y + P.py; moon.setAttribute('cx', x); moon.setAttribute('cy', y); hole.setAttribute('cx', x); hole.setAttribute('cy', y); };
put();
[sun, moon].forEach((e) => { e.style.transformOrigin = '50% 50%'; e.style.transformBox = 'fill-box'; });
if (reduce) { P.x = P.y = 0; put(); gsap.from(svg, { opacity: 0, duration: 0.4 }); revealCopy(0.2); }
else {
  const tl = gsap.timeline({ delay: 0.25 });
  tl.from(sun, { opacity: 0, scale: 0.94, duration: 0.7, ease: EASE.out }, 0)
    .from(moon, { opacity: 0, duration: 0.3, ease: 'none' }, 0.35)
    .to(P, { x: 0, y: 0, duration: 1.6, ease: EASE.inOut, onUpdate: put }, 0.35)
    // 다 가린 순간: 빛 테두리 두 겹이 퍼지며 사라진다
    .fromTo(coronas[0], { attr: { r: G.ar }, opacity: 0.55 }, { attr: { r: G.ar * 1.42 }, opacity: 0, duration: 1.3, ease: EASE.out }, 1.9)
    .fromTo(coronas[1], { attr: { r: G.ar }, opacity: 0.35 }, { attr: { r: G.ar * 1.7 }, opacity: 0, duration: 1.6, ease: EASE.out }, 2.02)
    .fromTo(sun, { scale: 1.02 }, { scale: 1, duration: 0.6, ease: EASE.out }, 1.9);
  revealCopy(1.55);
  // 대기: 마우스 쪽으로 원반이 최대 2.4 만큼 — 고리가 두꺼워졌다 얇아진다(마우스가 있는 기기만)
  if (fine) {
    let tx = 0, ty = 0; addEventListener('pointermove', (e) => { const r = box.getBoundingClientRect(); tx = ((e.clientX - (r.left + r.width / 2)) / innerWidth) * 4.8; ty = ((e.clientY - (r.top + r.height / 2)) / innerHeight) * 4.8; }, { passive: true });
    gsap.ticker.add(() => { if (tl.progress() < 0.6) return; P.px += (Math.max(-2.4, Math.min(2.4, tx)) - P.px) * 0.06; P.py += (Math.max(-2.4, Math.min(2.4, ty)) - P.py) * 0.06; put(); });
  }
}
handoff(box);
