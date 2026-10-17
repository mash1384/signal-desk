// P2 · 하루의 나선 — 입자들이 24시간을 감은 나선(DNA처럼)으로 모인다. 위가 24시간 전, 아래가 지금.
// 나선 위 밝은 점 하나하나가 실제 소식(초록=호재 바깥쪽, 빨강=악재 안쪽, 회색=중립). 스크롤하면 카메라가 나선을 따라 돌며 내려가고, 지나는 시간의 큰 소식이 떠오른다.
import * as THREE from 'three';
import { renderer, loop, mobile, reduce, fonts, lerp, clamp, ss, EN, Morph, cloud, pin, project, captions, T, line, COL, rnd, sm } from './pk.js';

const sec = document.getElementById('nx'), canvas = document.getElementById('nxgl'), lay = sec.querySelector('.px-lay'), capEl = sec.querySelector('.px-cap'), endB = sec.querySelector('.px-end b');
const r = renderer(canvas), scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(36, 1, 0.1, 200);
const mob = mobile(), N = mob ? 9000 : 15000, m = new Morph(N); scene.add(m.points); m.U.uSz.value = mob ? 1.05 : 0.95; m.U.uBurst.value = 1.0; m.U.uWob.value = 0.02;
cloud(m, 0, { w: 20, h: 9, y: 6 });
const HT = mob ? 13 : 11, RAD = mob ? 1.7 : 2.5, TURNS = 2.25, NOW = Date.now() / 1000, T0 = NOW - 86400;
const at = (u, rad = RAD) => { const a = u * TURNS * Math.PI * 2; return new THREE.Vector3(Math.cos(a) * rad, HT / 2 - u * HT, Math.sin(a) * rad); };
let ITEMS = [], ENT = {}, WIN = [], ready = false;
function build() {
  const per = 9, NS = Math.min(ITEMS.length * per, Math.floor(N * 0.45));
  const vc = { '호재': COL.up, '악재': COL.dn, '중립': COL.gray };
  m.set(1, (i, o) => {
    if (i < NS) { const it = ITEMS[Math.floor(i / per)], u = clamp((it.t - T0) / 86400), off = it.v === '호재' ? 0.32 : it.v === '악재' ? -0.32 : 0, p = at(u, RAD + off), c = vc[it.v] || COL.gray, k = (it.s || 1) * 0.03;
      o[0] = p.x + rnd(0.03 + k); o[1] = p.y + rnd(0.03 + k); o[2] = p.z + rnd(0.03 + k); o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = it.v === '중립' ? 0.45 : 0.95; return o; }
    // 나선 띠(두 가닥 + 사이를 잇는 가로대)
    const u = Math.random(), q = Math.random(), strand = q < 0.7, p = at(u, strand ? RAD + (Math.random() < 0.5 ? 0.42 : -0.42) + rnd(0.04) : RAD + rnd(0.42));
    if (!strand) { const rung = Math.round(u * 96) / 96; const pr = at(rung, RAD + rnd(0.42)); p.copy(pr); }
    const c = Math.random() < 0.2 ? COL.ind : COL.navy; o[0] = p.x; o[1] = p.y + rnd(0.02); o[2] = p.z; o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = strand ? 0.3 : 0.16; return o; });
  m.copy(1, 2); m.copy(1, 3); m.copy(1, 4);
  // 3시간마다 가장 큰 소식
  WIN = [...Array(8)].map((_, w) => { const a = T0 + w * 10800, ys = ITEMS.filter((x) => x.t >= a && x.t < a + 10800 && x.v !== '중립');
    const top = ys.sort((p, q) => ((q.s || 1) * 3 + (q.n || 1)) - ((p.s || 1) * 3 + (p.n || 1)))[0]; return top ? { it: top, u: clamp((top.t - T0) / 86400) } : null; }).filter(Boolean);
  WIN.forEach((w) => { const e = document.createElement('div'); e.className = 'px-card'; e.style.width = mob ? '240px' : '300px'; lay.appendChild(e); w.el = e; }); fillCards();
}
const fillCards = () => WIN.forEach((w) => { w.el.innerHTML = `<p class="m"><b class="${DFD.vcls(w.it.v)}">${DFI.v(w.it.v)}</b><span>${DFD.hm(w.it.t)} · ${DFI.outlets(w.it.n || 1)}</span></p><p class="t">${DFD.esc(line(w.it, ENT))}</p>`; });
const hour = document.createElement('div'); hour.className = 'px-lbl'; hour.style.cssText += ';font-family:var(--mono)'; lay.appendChild(hour);
const CAP = [null, [['The last 24 hours, wound into one strand.', 'Top is a day ago, bottom is now. Every bright point is a real story.'], ['지난 24시간을 한 가닥으로 감았어요.', '위가 하루 전, 아래가 지금. 밝은 점 하나하나가 실제 소식이에요.']],
  [['Follow the day down.', 'Green sits outside, red inside — the biggest story of every three hours.'], ['하루를 따라 내려가요.', '초록은 바깥, 빨강은 안쪽 — 3시간마다 가장 큰 소식.']]];
const cap = captions(capEl, CAP);
Promise.all([DFD.flash(), EN, fonts()]).then(([d, en]) => { ENT = en; ITEMS = d.items.filter((x) => x.t >= T0); build(); ready = true; DFI.onLang(fillCards);
  const setEnd = () => { endB.innerHTML = T(`That was today — <em>${ITEMS.length}</em> stories. The next one is live.`, `여기까지가 오늘 — <em>${ITEMS.length}</em>건. 다음 소식은 실시간으로.`); }; setEnd(); DFI.onLang(setEnd); });
const st = pin(sec, mob ? 460 : 520), v = new THREE.Vector3(), cp = new THREE.Vector3(), lk = new THREE.Vector3(), oP = new THREE.Vector3(), oL = new THREE.Vector3();
loop(sec, r, scene, cam, (t, dt) => {
  const P = reduce ? st.T : st.step(dt); m.U.uT.value = t;
  m.U.uS.value = ready ? clamp((P - 0.03) / 0.13) : 0;
  const dive = ss(0.24, 0.34, P) * (1 - ss(0.84, 0.93, P)), u = clamp((P - 0.3) / 0.52);
  // 전체 보기: 나선을 옆에서(살짝 위에서) 천천히 돈다
  const sp = t * 0.08 + P * 1.5; oP.set(Math.sin(sp) * (mob ? 30 : 23), mob ? 1 : 0.6, Math.cos(sp) * (mob ? 30 : 23)); oL.set(mob ? 0 : 1.6, mob ? -0.6 : 0, 0);
  // 따라 내려가기: 지금 시각의 나선 점보다 약간 앞 각도·위에서, 그 점을 본다
  const a = u * TURNS * Math.PI * 2, D = mob ? 7.2 : 7.8; cp.set(Math.cos(a + 0.55) * D, HT / 2 - u * HT + 1.6, Math.sin(a + 0.55) * D); const pt = at(u); lk.set(pt.x * 0.55, pt.y - 0.5, pt.z * 0.55);
  cam.position.copy(oP).lerp(cp, sm(dive)); cam.lookAt(oL.lerp(lk, sm(dive)));
  cap(P < 0.14 || P > 0.9 ? -1 : dive < 0.5 ? 1 : 2); capEl.style.opacity = P < 0.14 ? 0 : 1;
  if (ready) {
    // 시간 표시: 따라갈 때 지금 지나는 시각
    const hh = new Date((T0 + u * 86400) * 1000); hour.innerHTML = `<b>${String(hh.getHours()).padStart(2, '0')}:${String(hh.getMinutes()).padStart(2, '0')}</b><span>${T(Math.round((1 - u) * 24) + 'h ago', Math.round((1 - u) * 24) + '시간 전')}</span>`;
    v.copy(at(u, RAD + 0.9)); const [hx, hy, hz] = project(cam, sec, v); hour.style.transform = `translate(${clamp(hx, 50, sec.clientWidth - 50)}px,${clamp(hy, 120, sec.clientHeight - 80)}px) translate(-50%,-50%)`; hour.style.opacity = hz < 1 ? dive * (1 - ss(0.82, 0.86, P)) : 0;
    let best = null, bn = 1e9; WIN.forEach((w) => { const dd = Math.abs(w.u - u); if (dd < bn) { bn = dd; best = w; } });
    WIN.forEach((w) => { const near = w === best ? clamp(1 - bn * 14) * dive * (1 - ss(0.82, 0.86, P)) : 0; v.copy(at(w.u, RAD)); const [x, y, z] = project(cam, sec, v);
      const cw = mob ? 240 : 300, cx = clamp(x + (mob ? -cw / 2 : 40), 12, sec.clientWidth - cw - 12), cy = mob ? Math.max(sec.clientHeight * 0.58, y + 30) : y - 60;
      w.el.style.transform = `translate(${cx}px,${cy}px) translateY(${(1 - near) * 16}px)`; w.el.style.opacity = z < 1 ? near : 0; });
  }
  m.U.uA.value = 1 - ss(0.9, 0.98, P) * 0.8;
  sec.style.setProperty('--ep', ss(0.91, 0.98, P).toFixed(3));
});
