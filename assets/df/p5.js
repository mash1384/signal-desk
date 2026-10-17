import * as THREE from 'three';
import { renderer, loop, mobile, reduce, fonts, lerp, clamp, ss, EN, Morph, cloud, pin, stageOf, project, captions, T, line, COL, sm } from './pk.js?v=e2db2637';
import { makeBrief, BR_NAMES } from './brief.js?v=e2db2637';

const sec = document.getElementById('nx'), canvas = document.getElementById('nxgl'), lay = sec.querySelector('.px-lay'), capEl = sec.querySelector('.px-cap'), endB = sec.querySelector('.px-end b');
const r = renderer(canvas), scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(32, 1, 0.1, 400);
const mob = mobile(), XN = mob ? 150 : 240, ZN = mob ? 44 : 56, N = XN * ZN, m = new Morph(N); scene.add(m.points); m.U.uSz.value = mob ? 1.05 : 0.95; m.U.uBurst.value = 0.5; m.U.uWob.value = 0.015;
const WX = 16, WZ = 5.2, NOW = Date.now() / 1000, T0 = NOW - 86400, BINS = 96;
cloud(m, 0, { w: 20, h: 8, y: 5 });
const xOf = (u) => (u - 0.5) * WX;
const B = [...Array(BINS)].map(() => ({ n: 0, u: 0, d: 0 }));
const smooth = (arr, u) => { const x = clamp(u * BINS - 0.5, 0, BINS - 1), i = Math.floor(x), f = x - i, a = arr[i], b = arr[Math.min(BINS - 1, i + 1)]; return a + (b - a) * (f * f * (3 - 2 * f)); };
let HN = [], NET = [], MX = 1, HOURS = [], ENT = {}, ready = false;
function build() {
  const raw = B.map((b) => b.n), g = (k) => [-2, -1, 0, 1, 2].reduce((s, o) => s + (raw[clamp(k + o, 0, BINS - 1)] || 0) * [1, 3, 5, 3, 1][o + 2], 0) / 13;
  HN = raw.map((_, k) => g(k)); MX = Math.max(1, ...HN);
  NET = B.map((b, k) => { let u = 0, d = 0; for (let o = -3; o <= 3; o++) { const q = B[clamp(k + o, 0, BINS - 1)]; u += q.u; d += q.d; } return (u - d) / (u + d + 3); });
  m.set(1, (i, o) => { const xi = i % XN, zi = (i / XN) | 0, u = xi / (XN - 1); o[0] = xOf(u); o[1] = -1.6; o[2] = (zi / (ZN - 1) - 0.5) * WZ; const c = COL.navy; o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = 0.22; return o; });
  const up = COL.up, dn = COL.dn, base = new THREE.Color(document.documentElement.dataset.theme === 'dark' ? '#cdd8e8' : '#2a3f73'), tmp = new THREE.Color();
  m.set(2, (i, o) => { const xi = i % XN, zi = (i / XN) | 0, u = xi / (XN - 1), zz = zi / (ZN - 1) - 0.5, hN = smooth(HN, u) / MX, net = smooth(NET, u);
    const env = Math.exp(-zz * zz * 9), h = 4.0 * hN * env + 0.08 * Math.sin(u * 60 + zz * 9) * env;
    o[0] = xOf(u); o[1] = -1.6 + h; o[2] = zz * WZ;
    tmp.copy(base).lerp(COL.ind, clamp(hN * 1.2) * 0.6).lerp(net >= 0 ? up : dn, clamp(Math.abs(net) * 1.8) * clamp(hN * 2.2) * 0.85);
    o[3] = tmp.r; o[4] = tmp.g; o[5] = tmp.b; o[6] = 0.3 + 0.68 * clamp(env * (0.35 + hN)); return o; });
  m.copy(2, 3); m.copy(2, 4);
}
const RS = WZ + 1.3, RIDGES = mob ? 9 : 15, FX0 = mob ? -120 : -170, FX1 = WX / 2, DX = mob ? 0.2 : 0.14, DZ = mob ? 0.2 : 0.15;
const seedR = (k) => { let x = Math.sin(k * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const FA = document.documentElement.dataset.theme === 'dark' ? 1.45 : 1;   // 다크: 작은 점이 어두운 배경에 묻히지 않게 더 진하게
const fpos = [], fh = [], fc = [], frr = [], tmpC = new THREE.Color(), baseC = new THREE.Color(document.documentElement.dataset.theme === 'dark' ? '#cdd8e8' : '#2a3f73');
for (let ri = -(RIDGES >> 1); ri <= RIDGES >> 1; ri++) {
  const zc = ri * RS, sc = ri === 0 ? 1 : 0.55 + 0.6 * seedR(ri + 3), ph = seedR(ri) * 6.28, NXp = Math.ceil((FX1 - FX0) / DX) + 1;
  const prof = new Float32Array(NXp), net = new Float32Array(NXp);
  for (let k = 0; k < NXp; k++) { const x = FX0 + k * DX; prof[k] = 0.16 + 0.12 * Math.sin(x * 6.283 / WX + ph) + 0.05 * Math.sin(x * 1.7 + ph * 3); }
  const bursts = Math.round((FX1 - FX0) / WX * (7 + 6 * seedR(ri + 9)));
  for (let b = 0; b < bursts; b++) { const bx = FX0 + seedR(ri * 31 + b) * (FX1 - FX0), bh = 0.25 + Math.pow(seedR(ri * 17 + b * 3), 2.2) * 1.1, bw = 0.12 + seedR(ri * 7 + b * 5) * 0.9, bn = seedR(ri * 13 + b * 11) * 2 - 1;
    const k0 = Math.max(0, Math.floor((bx - bw * 4 - FX0) / DX)), k1 = Math.min(NXp - 1, Math.ceil((bx + bw * 4 - FX0) / DX));
    for (let k = k0; k <= k1; k++) { const x = FX0 + k * DX, g = Math.exp(-(((x - bx) / bw) ** 2)); prof[k] += bh * g; net[k] += bn * g * bh; } }
  let mx = 0; for (let k = 0; k < NXp; k++) { prof[k] += 0.04 * (seedR(ri * 1000 + k) - 0.5); mx = Math.max(mx, prof[k]); }
  for (let z = -WZ / 2; z <= WZ / 2; z += DZ) { const zz = z / WZ, env = Math.exp(-zz * zz * 9); if (env < 0.04) continue;
    for (let k = 0; k < NXp; k++) { const x = FX0 + k * DX; if (ri === 0 && x > -WX / 2 - 0.2) break;
      const hN = prof[k] / mx, h = 4.0 * sc * hN * env + 0.08 * Math.sin(x * 3.7 + zz * 9) * env, nt = Math.tanh(net[k] * 1.5);
      tmpC.copy(baseC).lerp(COL.ind, clamp(hN * 1.2) * 0.6).lerp(nt >= 0 ? COL.up : COL.dn, clamp(Math.abs(nt) * 1.4) * clamp(hN * 2.2) * 0.5);
      fpos.push(x + (Math.random() - 0.5) * DX * 0.5, 0, zc + z + (Math.random() - 0.5) * DZ * 0.5); fh.push(h); fc.push(tmpC.r, tmpC.g, tmpC.b, Math.min(1, (0.3 + 0.68 * clamp(env * (0.35 + hN))) * FA)); frr.push(Math.random()); } } }
const fg = new THREE.BufferGeometry(); fg.setAttribute('position', new THREE.Float32BufferAttribute(fpos, 3)); fg.setAttribute('aH', new THREE.Float32BufferAttribute(fh, 1));
fg.setAttribute('aC', new THREE.Float32BufferAttribute(fc, 4)); fg.setAttribute('aR', new THREE.Float32BufferAttribute(frr, 1));
const FU = { uT: { value: 0 }, uRev: { value: 0 }, uA: { value: 0 }, uSz: { value: 1 } };
const field = new THREE.Points(fg, new THREE.ShaderMaterial({ uniforms: FU, transparent: true, depthWrite: false, vertexShader: `attribute float aR, aH; attribute vec4 aC; uniform float uT, uRev, uA, uSz; varying vec4 vC;
  void main(){ vec3 p = position; float d = length(p.xz * vec2(1., 1.35)), vis = 1. - smoothstep(uRev - 18., uRev, d), edge = exp(-pow((d - uRev + 6.) / 5., 2.)) * step(.01, uRev);
    float breathe = 1. + .05 * sin(uT * .9 + p.x * .15 + p.z * .3);
    p.y = -1.6 + aH * vis * breathe + edge * .5;   // 드러나는 고리를 따라 살짝 솟는다
    vec4 mv = modelViewMatrix * vec4(p, 1.); float fade = 1. - smoothstep(70., 190., -mv.z);
    vC = vec4(mix(aC.rgb, vec3(.42,.36,1.), edge * .7), aC.a * .82 * uA * vis * fade * (1. + edge * .8));
    gl_Position = projectionMatrix * mv; gl_PointSize = max(1.5, uSz * (1.4 + aR * 1.4) * (10. / -mv.z) * ${Math.min(devicePixelRatio || 1, 2).toFixed(1)}); }`,
  fragmentShader: `varying vec4 vC; void main(){ vec2 q = gl_PointCoord - .5; float d = dot(q, q); if (d > .25 || vC.a < .004) discard; gl_FragColor = vec4(vC.rgb, vC.a * (1. - d * 2.6)); }` }));
field.frustumCulled = false; field.renderOrder = -1; scene.add(field);
const box = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => new THREE.Vector3(a * (WX / 2 + 0.25), -1.58, b * (WZ / 2 + 0.3)))), new THREE.LineBasicMaterial({ color: 0x533afd, transparent: true, opacity: 0 }));
scene.add(box);
const glow = new THREE.Mesh(new THREE.PlaneGeometry(WX + 3, WZ + 3).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, opacity: 0, map: (() => { const c = document.createElement('canvas'); c.width = 256; c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(128, 64, 10, 128, 64, 128); gr.addColorStop(0, 'rgba(83,58,253,.55)'); gr.addColorStop(1, 'rgba(83,58,253,0)'); g.setTransform(1, 0, 0, 0.5, 0, 32); g.fillStyle = gr; g.fillRect(0, 0, 256, 256); return new THREE.CanvasTexture(c); })() }));
glow.position.y = -1.62; glow.renderOrder = -2; scene.add(glow);
const today = document.createElement('div'); today.className = 'px-lbl'; today.style.cssText += ';transform-origin:left'; lay.appendChild(today);
const setToday = () => { today.innerHTML = `<b style="color:var(--primary)">${T('Today · last 24h', '오늘 · 지난 24시간')}</b><span>${T('real data', '실제 데이터')}</span>`; }; setToday(); DFI.onLang(setToday);

const ticks = [0, 0.25, 0.5, 0.75, 1].map((u) => { const e = document.createElement('div'); e.className = 'px-lbl'; lay.appendChild(e); return { e, u }; });
const card = document.createElement('div'); card.className = 'px-card'; card.style.width = mob ? '260px' : '320px'; lay.appendChild(card);
const stem = document.createElement('div'); stem.style.cssText = 'position:absolute;left:0;top:0;width:1px;background:linear-gradient(#0d253d55,#0d253d00);opacity:0;transform-origin:top'; lay.appendChild(stem);
const CAP = [null, [['Every story lands on a timeline.', 'The last 24 hours, left to right.'], ['모든 소식은 시간 위에 내려앉아요.', '왼쪽부터 지난 24시간.']],
  [['The day has a shape.', 'Height is how much broke. Colour is which way it leaned.'], ['하루에도 모양이 있어요.', '높이는 소식의 양, 색은 호재·악재 쪽으로 기운 정도.']],
  [['Scrub through the day.', 'The biggest story of each hour, as it happened.'], ['하루를 훑어봐요.', '시간마다 가장 큰 소식이 그대로 떠올라요.']],
  [['That was one day.', 'One small part of a much larger signal.'], ['이게 하루였어요.', '훨씬 큰 흐름 속의 작은 한 조각.']],
  [['Delfona never stops reading.', 'Crypto, macro, policy and AI news — from around the world, every hour, every day.'], ['Delfona는 멈추지 않고 읽어요.', '전 세계 크립토·경제·정책·AI 소식을 매시간, 매일.']],
  [['Then AI sums it all up.', 'Every morning at 09:00 KST, the whole day in one brief.'], ['그리고 AI가 전부 정리해요.', '매일 아침 9시, 하루 전체를 한 장으로.']]];
const cap = captions(capEl, CAP);
const hm = (ts) => { const d = new Date(ts * 1000); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
const setTicks = () => ticks.forEach((k) => { k.e.innerHTML = `<span>${k.u === 1 ? T('NOW', '지금') : hm(T0 + k.u * 86400)}</span>`; });
Promise.all([DFD.flash(), EN, fonts()]).then(([d, en]) => {
  ENT = en; const xs = d.items.filter((x) => x.t >= T0);
  xs.forEach((x) => { const b = B[Math.min(BINS - 1, Math.floor((x.t - T0) / 900))]; b.n++; if (x.v === '호재') b.u++; if (x.v === '악재') b.d++; });
  HOURS = [...Array(24)].map((_, h) => { const a = T0 + h * 3600, ys = xs.filter((x) => x.t >= a && x.t < a + 3600);
    const top = ys.filter((x) => x.v !== '중립').sort((p, q) => ((q.s || 1) * 3 + (q.n || 1)) - ((p.s || 1) * 3 + (p.n || 1)))[0];
    return { a, n: ys.length, u: ys.filter((x) => x.v === '호재').length, d: ys.filter((x) => x.v === '악재').length, top }; });
  build(); setTicks(); DFI.onLang(() => { setTicks(); lastH = -1; });
  const setEnd = () => { endB.innerHTML = BR === 4 ? T(`Every issue on Earth — read, judged and summed up. Live.`, `전 세계의 이슈를 읽고, 판정하고, 요약해요. 실시간으로.`) : BR ? T(`A new brief <em>every morning</em> at 09:00 KST.`, `매일 아침 9시, <em>새 하루 정리</em>가 도착해요.`) : T(`Every hour, every day. <em>Watch it live.</em>`, `매시간, 매일. <em>실시간으로 보세요.</em>`); }; setEnd(); DFI.onLang(setEnd);
  ready = true;
});
const BR = clamp(Math.round(+(new URLSearchParams(location.search).get('br')) || window.DF_BR || 0), 0, 5);
if (BR === 4) { sec.classList.add('fin4'); const c4 = document.createElement('style'); c4.textContent = `.fin4 .px-end{place-content:end center;padding-bottom:max(13vh,90px)}.fin4 .px-end .box{background:none;box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none;padding:0}
  .fin4 .px-end b{max-width:none;word-break:keep-all;font-size:clamp(17px,1.6vw,22px);font-weight:400;letter-spacing:-.01em;color:var(--ink2)}:lang(ko) .fin4 .px-end b{font-weight:500}.fin4 .px-end .btn{margin-top:18px}
  @media(max-width:899px){.fin4 .px-end{padding-bottom:22vh}.fin4 .px-end b{font-size:16px;padding:0 24px}}`; document.head.appendChild(c4); }
const BRF = BR ? makeBrief(BR, { scene, sec, lay, mob, sample: (n) => {   // 지금 화면의 파형 입자에서 n개를 뽑는다(오늘 구간 15%)
  const p = new Float32Array(n * 3), c = new Float32Array(n * 4), NF = fh.length;
  for (let i = 0; i < n; i++) { if (i < n * 0.15) { const j = (Math.random() * N) | 0; for (let q = 0; q < 3; q++) p[i * 3 + q] = m.P[2][j * 3 + q]; for (let q = 0; q < 4; q++) c[i * 4 + q] = m.C[2][j * 4 + q]; }
    else { const j = (Math.random() * NF) | 0; p[i * 3] = fpos[j * 3]; p[i * 3 + 1] = -1.6 + fh[j]; p[i * 3 + 2] = fpos[j * 3 + 2]; for (let q = 0; q < 4; q++) c[i * 4 + q] = fc[j * 4 + q]; c[i * 4 + 3] *= 0.82; } }
  return { p, c }; } }) : null;
const SKIP = 0.13, st = pin(sec, Math.round((1 - SKIP) * (BR === 4 ? (mob ? 1150 : 1250) : BR ? (mob ? 900 : 1000) : (mob ? 600 : 660)))), KEYS = [0, 0.12, 0.3, 0.86, 0.95];
const fP = new THREE.Vector3(), fL = new THREE.Vector3();
let lastH = -1; const v = new THREE.Vector3(), cp = new THREE.Vector3(), lk = new THREE.Vector3();
loop(sec, r, scene, cam, (t, dt) => {
  const RAW = SKIP + (1 - SKIP) * (reduce ? st.T : st.step(dt)), RP = BRF ? Math.min(0.94, RAW / 0.66) : RAW, P = Math.min(0.84, RP * 0.84 / 0.64); m.U.uT.value = t;   // P: 기존 장면 진행(0.84에서 멈춤)
  const Z = sm(ss(0.64, 0.86, RP)), ZC = ss(0.62, 0.68, RP);   // Z: 줌 아웃 진행
  const PRE = 2 * sm(ss(0.1, 1.0, st.pre)), s = ready ? Math.max(stageOf(P, KEYS, 0.3), PRE) : 0; m.U.uS.value = Math.min(2, s);   // 들어오면서 이미 파형이 된다(스크롤을 오래 안 해도)
  const scanU = clamp((P - 0.33) / 0.5), scanOn = ss(0.3, 0.36, P) * (1 - ss(0.85, 0.9, P)), sx = xOf(scanU);
  m.U.uHiX.value = sx; m.U.uHiW.value = 0.32; m.U.uHiOn.value = scanOn;
  const k = RP > 0.95 ? -1 : RP > 0.82 ? 5 : RP > 0.7 ? 4 : ZC > 0.5 ? -1 : (P < 0.12 && PRE < 0.6) ? -1 : P < 0.29 ? 1 : P < 0.34 ? 2 : P < (mob ? 0.355 : 0.85) ? 3 : -1; cap(k);
  capEl.style.opacity = k < 0 ? 0 : k >= 4 ? clamp(Math.min((RP - 0.7) / 0.03, RP > 0.82 ? (RP - 0.82) / 0.03 : (0.82 - RP) / 0.02, (0.95 - RP) / 0.02)) : 1 - ZC;
  const f = ss(0.3, 0.42, P) * (1 - ss(0.84, 0.93, P)), follow = mob ? 0.92 : 0.45;
  const fitZ = mob ? Math.max(24, (WX / 2 + 0.9) / (Math.tan((cam.fov * Math.PI) / 360) * cam.aspect)) : 20, fitK = fitZ / (mob ? 24 : 20);
  cp.set(lerp(0, sx * follow - 1.5, f), lerp((mob ? 8 : 7) * fitK, mob ? 5.2 : 4.4, f), lerp(fitZ, mob ? 15 : 13.5, f)); lk.set(lerp(0, sx * follow + (mob ? 0 : 0.8), f), lerp(-0.4, 0.4, f), 0);
  const Z2 = ss(0.8, 1, RP);   // 다 물러난 뒤에도 천천히 옆으로 흐르며 더 높이(웅장하게)
  fP.set((mob ? 10 : 18) - Z2 * (mob ? 4 : 9), (mob ? 44 : 27) + Z2 * (mob ? 10 : 9), (mob ? 52 : 40) + Z2 * 8); fL.set((mob ? -6 : -22) - Z2 * (mob ? 5 : 11), -3, mob ? -12 : -10);
  const fov = lerp(32, mob ? 44 : 40, Z); if (Math.abs(cam.fov - fov) > 0.01) { cam.fov = fov; cam.updateProjectionMatrix(); }
  cp.lerp(fP, Z); lk.lerp(fL, Z);
  cam.position.copy(cp); cam.lookAt(lk);
  FU.uT.value = t; FU.uRev.value = lerp(0, mob ? 170 : 240, ss(0.66, 0.93, RP)); FU.uSz.value = m.U.uSz.value; FU.uA.value = ss(0.64, 0.7, RP) * (1 - ss(0.95, 0.99, RP) * 0.5);
  box.material.opacity = ss(0.72, 0.78, RP) * (1 - ss(0.93, 0.97, RP)) * 0.9;
  glow.material.opacity = ss(0.7, 0.8, RP) * (1 - ss(0.95, 0.99, RP) * 0.6) * 0.9;
  { v.set(-WX / 2 - 0.25, -1.4, WZ / 2 + 0.3); const [x, y, z] = project(cam, sec, v); today.style.transform = `translate(${x}px,${y + 8}px)`; today.style.opacity = z < 1 ? ss(0.74, 0.8, RP) * (1 - ss(0.93, 0.97, RP)) * clamp((x - 10) / 24) * clamp((sec.clientWidth - 10 - x - today.offsetWidth) / 24 + 1) : 0; }
  m.U.uA.value = 1 - ss(0.95, 0.99, RP) * 0.6; m.U.uHiOn.value *= 1 - ZC; m.U.uSz.value = (mob ? 1.05 : 0.95) * (1 + Z * 1.6) * lerp(Math.pow(fitK, 0.75), 1, Math.max(f, Z));
  const SW = sec.clientWidth, SH = lay.clientHeight || innerHeight, edge = (x, y) => clamp((x - 18) / 24) * clamp((SW - 18 - x) / 24) * clamp((SH - 18 - y) / 24) * clamp((y - 18) / 24);
  ticks.forEach((q) => { v.set(xOf(q.u), -1.6, WZ / 2 + 0.5); const [x, y, z] = project(cam, sec, v); q.e.style.transform = `translate(${x}px,${y}px) translate(-50%,-50%)`; q.e.style.opacity = z < 1 ? Math.max(ss(0.12, 0.2, P), ss(0.6, 1.2, PRE)) * (1 - f * 0.6) * (1 - ZC) * edge(x, y) : 0; });
  if (ready) { const hh = Math.min(23, Math.floor(scanU * 24)), H = HOURS[hh];
    if (hh !== lastH) { lastH = hh; card.innerHTML = `<p class="m"><span>${hm(H.a)}–${hm(H.a + 3600)}</span><span>· ${H.n} ${T('stories', '건')}</span><span class="up">${H.u}↑</span><span class="down">${H.d}↓</span></p>` + (H.top ? `<p class="t"><b class="${DFD.vcls(H.top.v)}" style="font-size:11px;margin-right:6px;text-transform:uppercase">${DFI.v(H.top.v)}</b>${DFD.esc(line(H.top, ENT))}</p>` : `<p class="t" style="color:var(--mute)">${T('A quiet hour.', '조용한 시간이었어요.')}</p>`); }
    const hN = smooth(HN, scanU) / MX; v.set(sx, -1.6 + 4.0 * hN + 0.25, 0); const [x, y, z] = project(cam, sec, v);
    const lift = mob ? 120 : 110, cx = clamp(x, (mob ? 130 : 160) + 10, sec.clientWidth - (mob ? 130 : 160) - 10);
    card.style.transform = `translate(${cx}px,${y - lift}px) translate(-50%,-100%)`; card.style.opacity = z < 1 ? ss(0.36, 0.4, P) * (1 - ZC) : 0;
    stem.style.transform = `translate(${x}px,${y - lift}px)`; stem.style.height = lift + 'px'; stem.style.opacity = card.style.opacity; }
  sec.style.setProperty('--ep', ss(0.955, 0.99, RP).toFixed(3));
  if (BRF) { const BP = clamp((RAW - 0.64) / 0.36);
    BRF.update(BP, t, cam, lk, (f) => { if (!f) return; const k = clamp(1 - f * 2.2); FU.uA.value *= k; m.U.uA.value *= k * 0.6; box.material.opacity *= k; glow.material.opacity *= k; today.style.opacity = 0; card.style.opacity = 0; stem.style.opacity = 0; });
    if (BP > 0) { const kk = BP < 0.3 ? 6 : -1; cap(kk); capEl.style.opacity = kk === 6 ? clamp(Math.min(BP / 0.04, (0.3 - BP) / 0.04)) : 0; sec.style.setProperty('--ep', (BR === 4 ? ss(0.93, 0.985, BP) : ss(0.955, 0.99, BP)).toFixed(3)); } }
});

if (BR && !window.DF_BASE) { const bar0 = BR === 4; const bar = document.createElement('div'); bar.className = 'fxbar';
  const draw = () => { bar.innerHTML = `<span>${T('Brief scene', '정리 장면')}</span>` + [1, 2, 3, 4, 5].map((k) => `<a href="?br=${k}&go=br&v=${Date.now() % 1e6}" class="${k === BR ? 'on' : ''}">${k}<i> · ${BR_NAMES[k][DFI.lang() === 'ko' ? 1 : 0]}</i></a>`).join(''); };
  if (!bar0) { draw(); DFI.onLang(draw); document.body.appendChild(bar); }
  const css = document.createElement('style'); css.textContent = `.fxbar{position:fixed;left:16px;bottom:16px;z-index:95;display:flex;gap:4px;align-items:center;padding:5px;border-radius:16px;background:rgb(255 255 255/.88);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);box-shadow:0 0 0 1px rgb(13 37 61/.08),0 10px 30px -14px rgb(13 37 61/.35);font:600 12px/1 "Pretendard Variable",'Pretendard Variable',system-ui,sans-serif}
  .fxbar span{padding:0 8px;color:#5b6b82;font-family:'JetBrains Mono',monospace;font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.06em}.fxbar a{padding:8px 10px;border-radius:11px;color:#273951}.fxbar a.on{background:#0d253d;color:#fff}.fxbar i{font-style:normal}
  @media(max-width:899px){.fxbar{left:8px;bottom:12px;gap:2px;padding:4px}.fxbar span{display:none}.fxbar a{padding:7px 9px;font-size:11.5px}.fxbar a:not(.on) i{display:none}}`; document.head.appendChild(css);
  if (/go=br/.test(location.search)) addEventListener('load', () => setTimeout(() => { ScrollTrigger.refresh(); const tr = ScrollTrigger.getAll().find((x) => x.trigger === sec); if (tr) scrollTo(0, tr.start + 0.6 * (tr.end - tr.start)); }, 900)); }
