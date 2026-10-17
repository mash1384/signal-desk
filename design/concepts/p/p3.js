// P3 · 숫자로 말하기 — 오프닝의 입자들이 내려와 실제 숫자를 입자로 쓴다.
// 382(24시간 판정 수) → 41(두 곳 이상 보도) → 10(세기 3) → 비트코인 24시간 변동률. 숫자가 바뀔 때 입자가 흩어졌다 다시 모인다.
import * as THREE from 'three';
import { renderer, loop, mobile, reduce, fonts, lerp, clamp, ss, Morph, cloud, textPoints, pin, stageOf, captions, T, COL, rnd } from './pk.js';

const sec = document.getElementById('nx'), canvas = document.getElementById('nxgl'), capEl = sec.querySelector('.px-cap'), endB = sec.querySelector('.px-end b');
const r = renderer(canvas), scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(35, 1, 0.1, 200);
const N = mobile() ? 9000 : 15000, m = new Morph(N); scene.add(m.points); m.U.uSz.value = mobile() ? 1.15 : 1.0;
cloud(m, 0, { w: 18, h: 8, y: 4.5 });
const CAP = [null,
  [['stories judged in the last 24 hours', 'Every one read, translated, and called positive or negative.'], ['지난 24시간 판정한 소식', '하나하나 읽고, 번역하고, 호재·악재를 판정했어요.']],
  [['reported by two or more outlets', 'The same story from several places becomes one.'], ['두 곳 이상에서 보도된 소식', '여러 곳에서 나온 같은 소식은 하나로 묶어요.']],
  [['rated the strongest — 3 of 3', 'The few that can move the whole market.'], ['가장 센 소식 — 세기 3', '시장 전체를 움직일 수 있는 몇 건이에요.']],
  [['Bitcoin, last 24 hours', 'Live price change from Binance.'], ['비트코인, 지난 24시간', '바이낸스 실시간 시세 변동이에요.']]];
const cap = captions(capEl, CAP);
let ready = false;
function numStage(k, text, colorOf) {
  const vh = 2 * cam.position.z * Math.tan(cam.fov * Math.PI / 360), vw = vh * cam.aspect;
  const pts = textPoints(text, { font: '400 230px Inter', hgt: 1, step: mobile() ? 4 : 3 }), ratio = pts.W / pts.H, hgt = Math.min(mobile() ? 2.4 : 3.9, vw * (mobile() ? 0.82 : 0.6) / ratio);
  const sc = hgt, M = pts.length;
  m.set(k, (i, o) => { const p = pts[i % M], c = colorOf(i, p); o[0] = p.x * sc + rnd(0.012); o[1] = p.y * sc - (mobile() ? 0.2 : 0.55) + rnd(0.012); o[2] = rnd(0.22) + (i >= M * 2 ? rnd(0.5) : 0);
    o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = i < M * 2 ? 0.92 : 0.18; return o; });
}
const ink = (i) => (i % 7 === 0 ? COL.ind : COL.ink);
Promise.all([DFD.flash(), DFD.prices(['BTC']).catch(() => null), fonts('0123456789%+−.')]).then(([d, pr]) => {
  const s0 = Date.now() / 1000 - 86400, xs = d.items.filter((x) => x.t >= s0);
  const all = xs.length, multi = xs.filter((x) => (x.n || 1) >= 2).length, strong = xs.filter((x) => (x.s || 1) >= 3).length;
  const ch = pr && pr.BTC ? pr.BTC.c : null, chT = ch == null ? '–' : (ch > 0 ? '+' : ch < 0 ? '−' : '') + Math.abs(ch).toFixed(2) + '%';
  numStage(1, String(all), ink); numStage(2, String(multi), ink);
  numStage(3, String(strong), (i) => (i % 5 === 0 ? COL.ind : COL.ink));
  numStage(4, chT, (i) => (i % 6 === 0 ? COL.ink : ch == null ? COL.ink : ch >= 0 ? COL.up : COL.dn));
  const setEnd = () => { endB.innerHTML = T(`Every number here is <em>live</em>.`, `여기 숫자는 모두 <em>실시간</em>이에요.`); }; setEnd(); DFI.onLang(setEnd);
  ready = true;
});
cam.position.set(0, 0, 14);
const st = pin(sec, mobile() ? 380 : 420);
const KEYS = [0.0, 0.14, 0.37, 0.6, 0.83];
loop(sec, r, scene, cam, (t, dt) => {
  const P = reduce ? st.T : st.step(dt); m.U.uT.value = t;
  const s = ready ? stageOf(P, KEYS, 0.4) : 0; m.U.uS.value = Math.min(4, s);
  cap(Math.round(s) >= 1 && P < 0.92 ? Math.round(s) : -1); capEl.style.opacity = s < 0.6 ? 0 : 1 - Math.abs(s - Math.round(s)) * 2.2;
  // 카메라: 숫자를 비스듬히 돌아보며 깊이감(입자 z가 흩어져 있어 3D로 보인다)
  const a = Math.sin(P * Math.PI * 2.2) * 0.32; cam.position.set(Math.sin(a) * 14, Math.sin(P * Math.PI) * 0.8, Math.cos(a) * 14); cam.lookAt(0, -0.3, 0);
  m.points.rotation.y = Math.sin(t * 0.35) * 0.06;
  m.U.uA.value = 1 - ss(0.89, 0.97, P) * 0.88;
  sec.style.setProperty('--ep', ss(0.9, 0.98, P).toFixed(3));
});
