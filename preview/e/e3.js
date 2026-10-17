// E3 · 신호 — 원반이 먼저 놓이고, 초승달이 원반 둘레를 한 바퀴 넘게 돌다 스프링으로 오른쪽 위에 멈춘다(잔상 두 겹이 뒤따라와 합쳐진다).
// 그다음부터 원반에서 동심원이 퍼진다: 동심원 하나 = 방금 판정한 소식 하나(초록 호재 · 빨강 악재 · 회색 중립). 처음엔 최근 8건을 차례로, 이후 새 소식이 오면 바로.
import { G, COL, EASE, spring, el, stage, revealCopy, handoff, reduce, mobile, T } from './ek.js?v=1501';
const { hero, box, svg } = stage('e3');
const rings = el('g', { fill: 'none' }, svg);
const disc = el('circle', { cx: G.dx, cy: G.dy, r: G.dr, fill: COL.ink }, svg);
const mk = (o) => el('path', { d: G.cres, fill: COL.ind, opacity: o, transform: `rotate(0 ${G.dx} ${G.dy})` }, svg);
const ghosts = [mk(0), mk(0)], cres = mk(1);
const rot = (e, a) => e.setAttribute('transform', `rotate(${a} ${G.dx} ${G.dy})`);
disc.style.transformBox = 'fill-box'; disc.style.transformOrigin = '50% 50%';
const hud = document.createElement('p'); hud.className = 'hud e3hud'; hud.id = 'hud'; hud.setAttribute('aria-live', 'off'); hero.appendChild(hud);
const VC = { '호재': COL.up, '악재': COL.down }, seen = new Set();
function ping(it, quiet) {
  const c = VC[it.v] || COL.grey;
  if (!reduce) { const r = el('circle', { cx: G.dx, cy: G.dy, r: G.dr, stroke: c, 'stroke-width': 2, 'vector-effect': 'non-scaling-stroke', opacity: 1 }, rings);
    gsap.to(r, { attr: { r: G.dr * 1.8 }, duration: 2.6, ease: EASE.out }); gsap.to(r, { opacity: 0, duration: 2.6, ease: 'power1.in', onComplete: () => r.remove() }); }
  if (quiet) return;
  const line = DFI.line(it) || it.ko || "";
  hud.innerHTML = `<b style="color:${c}">${DFI.v ? DFI.v(it.v) : it.v}</b> ${DFD.esc(line.length > 90 ? line.slice(0, 88) + '…' : line)} <span>${DFI.ago(it.t)}</span>`;
  gsap.fromTo(hud, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: 0.4, ease: EASE.out, overwrite: true });
}
async function feed(first) {
  try { const d = await DFD.flash(), xs = (d.items || []).filter((x) => x.v && DFI.has(x)).sort((a, b) => a.t - b.t);
    if (first) { const last = xs.slice(-8); xs.forEach((x) => seen.add(x.id)); last.forEach((x, i) => gsap.delayedCall(i * 0.55, () => ping(x, false))); }
    else xs.filter((x) => !seen.has(x.id)).forEach((x, i) => { seen.add(x.id); gsap.delayedCall(i * 0.55, () => ping(x, false)); });
  } catch (e) { /* 소식을 못 받아도 심볼은 그대로 */ }
}
if (reduce) { gsap.from(svg, { opacity: 0, duration: 0.4 }); revealCopy(0.2); feed(true); }
else {
  const S = { a: -470 }, D = 1.9, tl = gsap.timeline({ delay: 0.2 });
  const lag = [0, 0];
  tl.from(disc, { opacity: 0, scale: 0.94, duration: 0.6, ease: EASE.out }, 0)
    .fromTo(cres, { opacity: 0 }, { opacity: 1, duration: 0.3, ease: 'none' }, 0.3)
    .fromTo(ghosts, { opacity: 0 }, { opacity: (i) => [0.22, 0.1][i], duration: 0.3, ease: 'none' }, 0.3)
    .to(S, { a: 0, duration: D, ease: spring(D, 0.18), onUpdate() { rot(cres, S.a); lag[0] += (S.a - lag[0]) * 0.32; lag[1] += (lag[0] - lag[1]) * 0.32; rot(ghosts[0], lag[0] - 14); rot(ghosts[1], lag[1] - 30); } }, 0.3)
    .to(ghosts, { opacity: 0, duration: 0.5, ease: EASE.out }, 1.5)
    .add(() => feed(true), 1.9);
  lag[0] = lag[1] = S.a;
  revealCopy(1.3);
}
setInterval(() => { if (!document.hidden) feed(false); }, 30000);
handoff(box);
