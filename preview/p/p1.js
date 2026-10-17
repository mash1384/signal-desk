// P1 · 점이 다시 소식으로 — 오프닝에서 "모든 소식은 점이 돼요"라고 했으니, 이번엔 점들이 다시 실제 소식 카드로 모인다.
// 입자가 카드 테두리·호재/악재 화살표·세기 막대를 그리고, 그 안에 실제 속보 글이 또렷하게 떠오른다. 스크롤마다 다음 소식으로 흩어졌다 다시 모인다.
import * as THREE from 'three';
import { renderer, loop, mobile, reduce, fonts, lerp, clamp, ss, EN, Morph, cloud, drawPoints, rrEdge, pin, stageOf, project, captions, T, line, COL, rnd } from './pk.js';

const sec = document.getElementById('nx'), canvas = document.getElementById('nxgl'), lay = sec.querySelector('.px-lay'), capEl = sec.querySelector('.px-cap'), endB = sec.querySelector('.px-end b');
const r = renderer(canvas), scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(35, 1, 0.1, 200);
const mob = mobile(), N = mob ? 9000 : 15000, m = new Morph(N); scene.add(m.points); m.U.uSz.value = mob ? 1.1 : 1.0; m.U.uBurst.value = 0.7;
cam.position.set(0, 0, mob ? 14 : 12);
cloud(m, 0, { w: 18, h: 8, y: 4.5 });
const CW = mob ? 3.6 : 6.6, CH = mob ? 3.7 : 3.2, CY = mob ? -1.0 : -0.55;
const ARROW = { up: drawPoints((g, W, H) => { g.lineWidth = 46; g.lineCap = 'round'; g.lineJoin = 'round'; g.beginPath(); g.moveTo(130, 390); g.lineTo(380, 140); g.moveTo(190, 140); g.lineTo(380, 140); g.lineTo(380, 330); g.stroke(); }, { wid: 1, step: 4 }),
  dn: drawPoints((g, W, H) => { g.lineWidth = 46; g.lineCap = 'round'; g.lineJoin = 'round'; g.beginPath(); g.moveTo(130, 140); g.lineTo(380, 390); g.moveTo(190, 390); g.lineTo(380, 390); g.lineTo(380, 200); g.stroke(); }, { wid: 1, step: 4 }),
  link: drawPoints((g) => { g.lineWidth = 34; [[256, 150], [140, 350], [372, 350]].forEach(([x, y]) => { g.beginPath(); g.arc(x, y, 58, 0, 6.283); g.stroke(); }); g.beginPath(); g.moveTo(222, 200); g.lineTo(168, 296); g.moveTo(290, 200); g.lineTo(344, 296); g.moveTo(200, 350); g.lineTo(312, 350); g.stroke(); }, { wid: 1, step: 4 }) };
// 카드 한 장의 입자 배치: 테두리 46% · 기호 22% · 세기 막대 8% · 옅은 바탕 24%
function cardStage(k, it, glyph, tint, cx = 0, cy = CY, w = CW, h = CH, scale = 1) {
  const gs = (mob ? 0.95 : 1.7) * scale, gx = cx + (mob ? w / 2 - gs * 0.62 : w / 2 - gs * 0.75), gy = mob ? cy - h / 2 + gs * 0.62 : cy, G = ARROW[glyph];
  m.set(k, (i, o) => { const q = i / N; let x, y, z = rnd(0.05), c = COL.ink, a = 0.9;
    if (q < 0.46) { const [ex, ey] = rrEdge(Math.random(), w, h, 0.28 * scale); x = cx + ex + rnd(0.012); y = cy + ey + rnd(0.012); c = i % 9 ? COL.ink : COL.ind; }
    else if (q < 0.68) { const p = G[i % G.length]; x = gx + p.x * gs; y = gy + p.y * gs; c = tint; a = 0.95; z = rnd(0.12); }
    else if (q < 0.76) { const b = i % 3, on = b < (it.s || 1); x = cx - w / 2 + 0.36 * scale + b * 0.34 * scale + Math.random() * 0.26 * scale; y = cy - h / 2 + 0.34 * scale + rnd(0.035 * scale); c = on ? tint : COL.gray; a = on ? 0.95 : 0.35; }
    else { x = cx + rnd(w / 2 - 0.1); y = cy + rnd(h / 2 - 0.1); c = COL.lt; a = 0.16; z = rnd(0.2) - 0.1; }
    o[0] = x; o[1] = y; o[2] = z; o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = a; return o; });
}
// 마지막: 작은 카드 세 장(실시간 목록)
function feedStage(k, xs) {
  const w = mob ? 3.5 : 3.4, h = mob ? 1.5 : 2.1, gap = mob ? 0.24 : 0.3, cx = (j) => mob ? 0 : (j - 1) * (w + gap), cy = (j) => mob ? CY + 0.4 + (1 - j) * (h + gap) : CY;
  m.set(k, (i, o) => { const j = i % 3, q = (i / N); let x, y, z = rnd(0.05), c = COL.ink, a = 0.85, it = xs[j] || {};
    const tint = it.v === '호재' ? COL.up : COL.dn;
    if (q < 0.62) { const [ex, ey] = rrEdge(Math.random(), w, h, 0.22); x = cx(j) + ex; y = cy(j) + ey; c = i % 9 ? COL.ink : COL.ind; }
    else if (q < 0.74) { x = cx(j) - w / 2 + 0.09 + rnd(0.02); y = cy(j) + rnd(h / 2 - 0.26); c = tint; a = 0.95; }   // 왼쪽 색 띠(호재 초록·악재 빨강)
    else { x = cx(j) + rnd(w / 2 - 0.1); y = cy(j) + rnd(h / 2 - 0.1); c = COL.lt; a = 0.14; }
    o[0] = x; o[1] = y; o[2] = z; o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = a; return o; });
  return { w, h, cx, cy };
}
// 글(HTML): 큰 카드 안 글, 마지막 목록 글
const big = document.createElement('div'); big.className = 'px-card px-in'; lay.appendChild(big);
const minis = [0, 1, 2].map(() => { const e = document.createElement('div'); e.className = 'px-card px-mini'; lay.appendChild(e); return e; });
const st2 = document.createElement('style'); st2.textContent = `.px-in{background:none;box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none;padding:0}.px-in .t{font-size:clamp(20px,2.1vw,30px);font-weight:400;letter-spacing:-.025em;line-height:1.22}:lang(ko) .px-in .t{font-weight:500}
  .px-in .m{font-size:12.5px}.px-in .v{display:inline-block;padding:3px 10px;border-radius:99px;font:700 12px/1.4 var(--sans);letter-spacing:.04em;text-transform:uppercase}.px-in .v.up{background:#e7f7f0;color:#0e9f6e}.px-in .v.down{background:#fdeeec;color:#df4a3a}
  .px-in .f{margin-top:14px;font-family:var(--mono);font-size:12px;color:var(--mute)}.px-mini{background:none;box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none}
  @media(max-width:899px){.px-in .t{font-size:19px}}.px-mini .t{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}@media(max-width:899px){.px-mini{padding:0}.px-mini .t{font-size:14px}}`; document.head.appendChild(st2);
let STORIES = [], FEED = [], ENT = {}, FD = null;
const CAP = [null,
  [['Every point is a real story.', 'The strongest positive call of the last 24 hours.'], ['점 하나하나가 실제 소식이에요.', '지난 24시간 가장 센 호재 판정.']],
  [['Negative news, called just as fast.', 'The strongest negative call.'], ['악재도 똑같이 빠르게.', '지난 24시간 가장 센 악재 판정.']],
  [['Confirmed by several outlets.', 'Reports of the same story, grouped into one card.'], ['여러 곳에서 확인된 소식.', '같은 소식의 보도를 카드 하나로 묶었어요.']],
  [['And it never stops.', 'The latest signals, as they land.'], ['그리고 멈추지 않아요.', '방금 들어온 신호들.']]];
const cap = captions(capEl, CAP);
const fillBig = (it, kind) => { if (!it) return; const up = it.v === '호재';
  big.innerHTML = `<p class="m"><span class="v ${up ? 'up' : 'down'}">${DFI.v(it.v)}</span><span>${DFD.hm(it.t)}</span></p><p class="t">${DFD.esc(line(it, ENT))}</p>
    <p class="f">${[...(it.coins || []).slice(0, 3)].join(' · ')}${it.coins && it.coins.length ? '   ·   ' : ''}${DFI.outlets(it.n || 1)}   ·   ${T('strength', '세기')} ${it.s || 1}/3</p>`; };
const fillMinis = () => FEED.forEach((it, j) => { minis[j].innerHTML = `<p class="m"><b class="${DFD.vcls(it.v)}">${DFI.v(it.v)}</b><span>${DFI.ago(it.t)}</span></p><p class="t">${DFD.esc(line(it, ENT))}</p>`; });
let shown = -1;
Promise.all([DFD.flash(), EN, fonts()]).then(([d, en]) => {
  ENT = en; const s0 = Date.now() / 1000 - 86400, xs = d.items.filter((x) => x.t >= s0 && x.v !== '중립');
  const score = (x) => (x.s || 1) * 3 + Math.min(x.n || 1, 4) + (x.coins.length ? 1 : 0);
  const pos = xs.filter((x) => x.v === '호재').sort((a, b) => score(b) - score(a))[0], neg = xs.filter((x) => x.v === '악재').sort((a, b) => score(b) - score(a))[0];
  const multi = xs.filter((x) => x !== pos && x !== neg).sort((a, b) => (b.n || 1) - (a.n || 1) || score(b) - score(a))[0];
  STORIES = [pos, neg, multi].filter(Boolean); FEED = xs.filter((x) => !STORIES.includes(x)).slice(0, 3);
  cardStage(1, STORIES[0], 'up', COL.up); cardStage(2, STORIES[1], 'dn', COL.dn); cardStage(3, STORIES[2], 'link', COL.ind);
  FD = feedStage(4, FEED); fillMinis(); DFI.onLang(() => { fillMinis(); if (shown >= 0) fillBig(STORIES[shown]); });
  const setEnd = () => { endB.innerHTML = T(`<em>${xs.length}</em> signals in the last 24 hours. All live.`, `지난 24시간 신호 <em>${xs.length}</em>건. 모두 실시간이에요.`); }; setEnd(); DFI.onLang(setEnd);
});
const st = pin(sec, mob ? 400 : 440), KEYS = [0, 0.13, 0.36, 0.59, 0.82];
const tl = new THREE.Vector3(), br = new THREE.Vector3();
loop(sec, r, scene, cam, (t, dt) => {
  const P = reduce ? st.T : st.step(dt); m.U.uT.value = t;
  const s = STORIES.length ? stageOf(P, KEYS, 0.42) : 0, k = Math.round(s), near = clamp(1 - Math.abs(s - k) * 3.2);
  m.U.uS.value = s;
  cap(k >= 1 && P < 0.92 ? k : -1); capEl.style.opacity = s < 0.6 ? 0 : clamp(1 - Math.abs(s - k) * 2.4);
  m.points.rotation.y = Math.sin(t * 0.3) * 0.035; m.points.rotation.x = Math.sin(t * 0.23) * 0.02;
  m.U.uA.value = 1 - ss(0.89, 0.97, P) * 0.85;
  // 큰 카드 글: 카드가 다 모였을 때만 또렷하게
  if (k >= 1 && k <= 3 && STORIES[k - 1]) { if (shown !== k - 1) { shown = k - 1; fillBig(STORIES[shown]); }
    tl.set(-CW / 2 + (mob ? 0.3 : 0.42), CY + CH / 2 - (mob ? 0.3 : 0.38), 0); br.set(mob ? CW / 2 - 0.3 : CW / 2 - 2.0, CY - CH / 2 + 0.55, 0);
    const [x0, y0] = project(cam, sec, tl), [x1] = project(cam, sec, br);
    big.style.transform = `translate(${x0}px,${y0 + (1 - near) * 14}px)`; big.style.width = (x1 - x0) + 'px'; big.style.opacity = near * (1 - ss(0.86, 0.9, P)); }
  else big.style.opacity = 0;
  // 마지막 목록 글
  if (FD) minis.forEach((e, j) => { const c = new THREE.Vector3(FD.cx(j) - FD.w / 2 + 0.22, FD.cy(j) + FD.h / 2 - 0.2, 0), c2 = new THREE.Vector3(FD.cx(j) + FD.w / 2 - 0.2, 0, 0);
    const [x0, y0] = project(cam, sec, c), [x1] = project(cam, sec, c2); e.style.transform = `translate(${x0}px,${y0 + (mob ? 4 : 8)}px)`; e.style.width = (x1 - x0) + 'px';
    e.style.opacity = (k === 4 ? near : 0) * (1 - ss(0.88, 0.93, P)); });
  sec.style.setProperty('--ep', ss(0.9, 0.98, P).toFixed(3));
});
