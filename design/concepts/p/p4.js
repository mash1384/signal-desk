// P4 · 코인 별자리 — 입자들이 소식이 몰린 곳(비트코인·이더리움·AI·거시경제 …)마다 성운처럼 모인다.
// 성운 크기 = 지난 24시간 그 주제 소식 수, 색 = 호재·악재 쪽으로 기운 정도. 스크롤하면 카메라가 큰 성운부터 하나씩 다가가 가장 큰 소식을 보여 준다.
import * as THREE from 'three';
import { renderer, loop, mobile, reduce, fonts, lerp, clamp, ss, EN, SECT, Morph, cloud, pin, stageOf, project, captions, T, line, COL, rnd, sm } from './pk.js';

const sec = document.getElementById('nx'), canvas = document.getElementById('nxgl'), lay = sec.querySelector('.px-lay'), capEl = sec.querySelector('.px-cap'), endB = sec.querySelector('.px-end b');
const r = renderer(canvas), scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(35, 1, 0.1, 200);
const mob = mobile(), N = mob ? 9000 : 15000, m = new Morph(N); scene.add(m.points); m.U.uSz.value = mob ? 1.05 : 0.95; m.U.uBurst.value = 1.1; m.U.uWob.value = 0.05;
cloud(m, 0, { w: 20, h: 9, y: 5 });
const SLOT = mob ? [[0, 1.6, 0], [-0.9, -1.4, 0.5], [1.0, -0.2, -0.6], [-1.1, 3.9, -0.8], [1.1, 3.2, 0.6], [0.4, -3.4, -0.4]]
  : [[-0.6, 0.2, 0.6], [3.6, -0.6, -0.4], [-4.2, -0.7, -0.8], [1.8, 2.3, -1.4], [-2.4, 2.4, 0.2], [5.4, 1.8, -1.6]];
let G = [], ENT = {}, ready = false;
const labels = [], card = document.createElement('div'); card.className = 'px-card'; card.style.width = mob ? '270px' : '340px'; lay.appendChild(card);
function build(items) {
  const s0 = Date.now() / 1000 - 86400, xs = items.filter((x) => x.t >= s0), grp = {};
  const add = (key, name, x) => { (grp[key] = grp[key] || { key, name, xs: [] }).xs.push(x); };
  xs.forEach((x) => { const coins = (x.coins || []).filter((c) => !/^USD/.test(c)); if (coins.length) coins.slice(0, 2).forEach((c) => add('c:' + c, [c, c], x));
    (x.sectors || []).slice(0, 1).forEach((s) => add('s:' + s, SECT[s] || [s, s], x)); if (!coins.length && !(x.sectors || []).length && x.mw) add('macro', ['Macro', '거시경제'], x); });
  G = Object.values(grp).sort((a, b) => b.xs.length - a.xs.length).slice(0, 6).map((g, i) => { const u = g.xs.filter((x) => x.v === '호재').length, d = g.xs.filter((x) => x.v === '악재').length;
    const top = g.xs.filter((x) => x.v !== '중립').sort((p, q) => ((q.s || 1) * 3 + (q.n || 1)) - ((p.s || 1) * 3 + (p.n || 1)))[0];
    return { ...g, n: g.xs.length, u, d, net: (u - d) / (u + d + 2), top, c: new THREE.Vector3(...SLOT[i]) }; });
  const tot = G.reduce((a, g) => a + g.n, 0), mx = G[0].n;
  G.forEach((g) => { g.R = (mob ? 0.42 : 0.55) + (mob ? 0.75 : 1.05) * Math.sqrt(g.n / mx); g.share = g.n / tot; });
  // 입자 배분: 85%를 성운에(소식 수 비례), 15%는 사이를 떠도는 먼지
  const cut = []; let acc = 0; G.forEach((g) => { acc += g.share * 0.85; cut.push(acc); });
  const tmp = new THREE.Color();
  m.set(1, (i, o) => { const q = (i + 0.5) / N; let j = cut.findIndex((c) => q < c);
    if (j < 0) { o[0] = rnd(mob ? 2.4 : 7.5); o[1] = rnd(mob ? 5 : 3.6); o[2] = rnd(3); o[3] = COL.lt.r; o[4] = COL.lt.g; o[5] = COL.lt.b; o[6] = 0.18; return o; }
    const g = G[j], u = Math.random(), rr = g.R * Math.pow(u, 1.6), th = Math.random() * 6.283, ph = Math.acos(Math.random() * 2 - 1);
    // 납작한 원반 + 둥근 핵(은하처럼)
    const disk = Math.random() < 0.45, x = disk ? Math.cos(th) * g.R * 1.35 * Math.sqrt(Math.random()) : rr * Math.sin(ph) * Math.cos(th), z = disk ? Math.sin(th) * g.R * 1.35 * Math.sqrt(Math.random()) : rr * Math.cos(ph), y = disk ? rnd(0.06) : rr * Math.sin(ph) * Math.sin(th) * 0.8;
    const tilt = 0.5 + j * 0.3; o[0] = g.c.x + x; o[1] = g.c.y + y * Math.cos(tilt) - z * Math.sin(tilt) * 0.35; o[2] = g.c.z + z * Math.cos(tilt) * 0.6;
    tmp.copy(COL.ink).lerp(COL.ind, 0.35 + 0.3 * Math.random()).lerp(g.net >= 0 ? COL.up : COL.dn, clamp(Math.abs(g.net) * 1.7) * (0.35 + 0.65 * Math.random()));
    o[3] = tmp.r; o[4] = tmp.g; o[5] = tmp.b; o[6] = 0.35 + 0.6 * (1 - u); return o; });
  m.copy(1, 2); m.copy(1, 3); m.copy(1, 4);
  G.forEach((g, i) => { const e = labels[i] || document.createElement('div'); e.className = 'px-lbl'; lay.appendChild(e); labels[i] = e; });
  setLabels();
}
const setLabels = () => G.forEach((g, i) => { labels[i].innerHTML = `<b>${g.name[DFI.lang() === 'ko' ? 1 : 0]}</b><span>${g.n} · <i class="up" style="font-style:normal">${g.u}↑</i> <i class="down" style="font-style:normal">${g.d}↓</i></span>`; });
let shownG = -1;
const fillCard = (g) => { card.innerHTML = `<p class="m"><b>${g.name[DFI.lang() === 'ko' ? 1 : 0]}</b><span>${g.n} ${T('stories in 24h', '건 · 24시간')}</span></p>` + (g.top ? `<p class="t"><b class="${DFD.vcls(g.top.v)}" style="font-size:11px;margin-right:6px;text-transform:uppercase">${DFI.v(g.top.v)}</b>${DFD.esc(line(g.top, ENT))}</p><p class="m" style="margin-top:8px"><span>${DFD.hm(g.top.t)}</span><span>· ${DFI.outlets(g.top.n || 1)}</span></p>` : ''); };
const CAP = [null, [['Where the news is gathering.', 'Each cloud is a coin or a theme. Size is how much news it drew in 24 hours.'], ['소식이 몰리는 곳.', '성운 하나가 코인 또는 주제예요. 크기는 지난 24시간 소식의 양.']],
  [['Up close, the biggest story.', 'Colour shows which way the news leaned.'], ['가까이서 보면, 가장 큰 소식.', '색은 소식이 호재·악재 어느 쪽으로 기울었는지예요.']]];
const cap = captions(capEl, CAP);
Promise.all([DFD.flash(), EN, fonts()]).then(([d, en]) => { ENT = en; build(d.items); ready = true;
  DFI.onLang(() => { setLabels(); if (shownG >= 0) fillCard(G[shownG]); });
  const setEnd = () => { endB.innerHTML = T(`See what every coin is <em>hearing</em>, live.`, `코인마다 어떤 소식이 <em>쏟아지는지</em> 실시간으로.`); }; setEnd(); DFI.onLang(setEnd); });
const st = pin(sec, mob ? 440 : 480);
const camP = new THREE.Vector3(), camL = new THREE.Vector3(), tA = new THREE.Vector3(), tB = new THREE.Vector3(), lA = new THREE.Vector3(), lB = new THREE.Vector3(), v = new THREE.Vector3();
// 카메라 위치: -1=전체, 0..2=성운 i에 다가감
const view = (k, P, outP, outL) => { if (k < 0 || !G[k]) { outP.set(0, mob ? 0.4 : 0.3, mob ? 21 : 15.5); outL.set(0, mob ? 0.2 : 0.2, 0); return; }
  const g = G[k], a = Math.sin(P * 9 + k) * 0.25; outP.set(g.c.x + g.R * (mob ? 0.2 : 1.4) + Math.sin(a) * 1.2, g.c.y + 0.5, g.c.z + g.R * 2.4 + (mob ? 5.2 : 4.4)); outL.set(g.c.x + (mob ? 0 : g.R * 0.9), g.c.y - (mob ? 0.9 : 0), g.c.z); };
const KF = [[0.0, -1], [0.3, -1], [0.38, 0], [0.5, 0], [0.58, 1], [0.68, 1], [0.76, 2], [0.85, 2], [0.92, -1], [1, -1]];
loop(sec, r, scene, cam, (t, dt) => {
  const P = reduce ? st.T : st.step(dt); m.U.uT.value = t;
  m.U.uS.value = ready ? clamp((P - 0.03) / 0.13) : 0;
  let i = 0; while (i < KF.length - 2 && P > KF[i + 1][0]) i++;
  const [pa, ka] = KF[i], [pb, kb] = KF[i + 1], f = sm((P - pa) / (pb - pa));
  view(ka, P, tA, lA); view(kb, P, tB, lB); camP.copy(tA).lerp(tB, f); camL.copy(lA).lerp(lB, f);
  cam.position.copy(camP); cam.lookAt(camL);
  m.points.rotation.y = Math.sin(t * 0.12) * 0.05;
  const focus = ka === kb ? ka : f < 0.5 ? ka : kb, fo = ka === kb ? 1 : Math.abs(f - 0.5) * 2;
  cap(P < 0.14 || P > 0.9 ? -1 : focus < 0 ? 1 : 2); capEl.style.opacity = P < 0.14 ? 0 : 1;
  if (ready) {
    G.forEach((g, j) => { v.copy(g.c).applyMatrix4(m.points.matrixWorld); v.y -= g.R * 0.5 + 0.3; const [x, y, z] = project(cam, sec, v);
      labels[j].style.transform = `translate(${x}px,${y}px) translate(-50%,0)`; labels[j].style.opacity = z < 1 ? ss(0.14, 0.2, P) * (focus < 0 ? 1 : j === focus ? 0 : 0.35) * fo * (1 - ss(0.9, 0.95, P)) : 0; });
    if (focus >= 0 && G[focus]) { if (shownG !== focus) { shownG = focus; fillCard(G[focus]); }
      const g = G[focus]; v.copy(g.c).applyMatrix4(m.points.matrixWorld); v.x += mob ? 0 : g.R * 1.25; v.y += mob ? -g.R * 1.5 : 0; const [x, y] = project(cam, sec, v);
      card.style.transform = mob ? `translate(${sec.clientWidth / 2}px,${y}px) translate(-50%,0)` : `translate(${x}px,${y}px) translate(0,-50%)`; card.style.opacity = fo * (1 - ss(0.9, 0.93, P)); }
    else card.style.opacity = 0;
  }
  m.U.uA.value = 1 - ss(0.9, 0.98, P) * 0.8;
  sec.style.setProperty('--ep', ss(0.92, 0.98, P).toFixed(3));
});
