// E2 · 작도 — 기술 도면처럼 가는 선으로 중심선·원 세 개·치수를 먼저 긋고, 원반을 시계 방향으로 칠하고, 초승달을 끝에서 끝으로 칠한 뒤 도면선이 걷힌다.
// 대기: 마우스를 심볼 위에 올리면 도면선이 옅게 다시 보인다(어떻게 만든 모양인지).
import { G, COL, EASE, el, stage, revealCopy, handoff, reduce, fine, mobile } from './ek.js?v=1501';
const { box, svg } = stage('e2');
const defs = el('defs', {}, svg);
const clip = el('clipPath', { id: 'e2c' }, defs); el('path', { d: G.cres }, clip);
const guides = el('g', { class: 'guides', fill: 'none', stroke: COL.guide, 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke' }, svg);
const L = (d, extra = {}) => el('path', Object.assign({ d, pathLength: 1, 'vector-effect': 'non-scaling-stroke' }, extra), guides);
const lines = [
  L(`M${G.dx - 44} ${G.dy}H${G.dx + 50}`), L(`M${G.dx} ${G.dy + 42}V${G.dy - 50}`),            // 원반 중심선
  L(`M${G.ax - 6} ${G.ay}H${G.ax + 44}`, { opacity: 0.6 }), L(`M${G.ax} ${G.ay + 6}V${G.ay - 42}`, { opacity: 0.6 }), // 고리 중심선(짧게)
  L(circ(G.dx, G.dy, G.dr), { stroke: COL.ink, opacity: 0.55 }),
  L(circ(G.ax, G.ay, G.ar), { stroke: COL.ind }),
  L(circ(G.dx, G.dy, G.br), { 'stroke-dasharray': '0.012 0.008', opacity: 0.8 }),
  L(`M${G.dx} ${G.dy}L${G.ax} ${G.ay}`, { stroke: COL.ind }),                                  // 두 중심을 잇는 선
  L(`M${G.dx} ${G.dy}L${G.dx - G.dr * 0.866} ${G.dy + G.dr * 0.5}`, { stroke: COL.ink, opacity: 0.6 }), // 반지름
];
function circ(cx, cy, r) { return `M${cx} ${cy - r}A${r} ${r} 0 1 1 ${cx} ${cy + r}A${r} ${r} 0 1 1 ${cx} ${cy - r}`; }
const labels = el('g', { class: 'lbl' }, svg);
const lab = (x, y, t, a = 'start') => { const e = el('text', { x, y, 'text-anchor': a }, labels); e.textContent = t; return e; };
const tx = [lab(G.dx - 28, G.dy + 21, 'R 30', 'end'), lab(G.ax + 33, G.ay - 22, 'R 31'), lab(G.dx + 30, G.dy + 33, 'R 36.5'), lab(G.ax + 3, G.ay + 4.5, '7 · 7')];
// 칠하기: 굵은 선(원반 반지름만큼)을 시계 방향으로 그려 원반을 채운다 / 초승달은 고리를 따라가는 굵은 호를 초승달 모양으로 잘라서
const disc = el('circle', { cx: G.dx, cy: G.dy, r: G.dr / 2, fill: 'none', stroke: COL.ink, 'stroke-width': G.dr + 0.3, pathLength: 1, transform: `rotate(-90 ${G.dx} ${G.dy})` }, svg);
const solid = el('circle', { cx: G.dx, cy: G.dy, r: G.dr, fill: COL.ink, opacity: 0 }, svg); // 칠이 끝나면 이음매 없는 원으로 바꿔 끼운다
const cresG = el('g', { 'clip-path': 'url(#e2c)' }, svg);
// 초승달 한쪽 끝(43,17.6)에서 다른 끝(82.4,56.9)까지 원 A 를 따라 도는 호
const A0 = Math.atan2(17.61 - G.ay, 43.13 - G.ax) - 0.1, A1 = Math.atan2(56.87 - G.ay, 82.39 - G.ax) + 0.1, RR = G.ar - 2, pt = (a) => `${G.ax + RR * Math.cos(a)} ${G.ay + RR * Math.sin(a)}`;
const arc = el('path', { d: `M${pt(A0)} A${RR} ${RR} 0 0 1 ${pt(A1)}`, fill: 'none', stroke: COL.ind, 'stroke-width': 12, 'stroke-linecap': 'butt', pathLength: 1 }, cresG);
const draw = (e, v) => { e.style.strokeDasharray = '1 1'; e.style.strokeDashoffset = v; };
lines.forEach((e) => { if (!e.getAttribute('stroke-dasharray')) draw(e, 1); });
draw(disc, 1); draw(arc, 1);
if (reduce) { [disc, arc].forEach((e) => draw(e, 0)); solid.setAttribute('opacity', 1); guides.style.opacity = 0; labels.style.opacity = 0; gsap.from(svg, { opacity: 0, duration: 0.4 }); revealCopy(0.2); }
else {
  const tl = gsap.timeline({ delay: 0.2 });
  lines.forEach((e, i) => { if (e.getAttribute('stroke-dasharray')) tl.from(e, { opacity: 0, duration: 0.5, ease: EASE.out }, 0.35 + i * 0.07); else tl.to(e.style, { strokeDashoffset: 0, duration: 0.7, ease: EASE.inOut }, i * 0.07); });
  tl.from(tx, { opacity: 0, y: 1.5, duration: 0.4, ease: EASE.out, stagger: 0.06 }, 0.55)
    .to(disc.style, { strokeDashoffset: 0, duration: 0.8, ease: EASE.inOut, onComplete: () => { solid.setAttribute('opacity', 1); disc.style.visibility = 'hidden'; }, onReverseComplete: () => {} }, 1.0)
    .to(arc.style, { strokeDashoffset: 0, duration: 0.55, ease: EASE.inOut }, 1.55)
    .to([guides, labels], { opacity: 0, duration: 0.6, ease: EASE.out }, 2.15);
  revealCopy(1.7);
  // 마우스를 심볼 위에 올리면 도면이 옅게 다시
  if (fine) { box.style.pointerEvents = 'auto';
    box.addEventListener('pointerenter', () => { if (tl.progress() === 1) gsap.to([guides, labels], { opacity: 0.45, duration: 0.2, ease: 'none', overwrite: true }); });
    box.addEventListener('pointerleave', () => { if (tl.progress() === 1) gsap.to([guides, labels], { opacity: 0, duration: 0.2, ease: 'none', overwrite: true }); }); }
}
handoff(box);
