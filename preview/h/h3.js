// H3 · Particle mark — 1만 6천 개 입자가 잡음처럼 흩어졌다가 소용돌이치며 Delfona의 일식 심볼(원반 + 초승달 고리)로 모인다.
// 입자 일부는 지난 24시간 호재·악재 비율만큼 초록·빨강, 나머지는 남색·인디고. 마우스를 가까이 대면 밀려났다가 돌아온다.
import * as THREE from 'three';
import { renderer, loop, pointer, easePointer, revealCopy, reduce, mobile, data } from './kit.js?v=202610151430';
const canvas = document.getElementById('gl'), r = renderer(canvas, { clear: 0xf7f9fc });
const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(35, 1, 0.1, 100); cam.position.set(0, 0, 10);
const N = mobile() ? 9000 : 16000;
// 표시 모양을 캔버스에 그려 점을 뽑는다(두 사선 + 점)
function sampleMark() {
  // 일식 심볼: 꽉 찬 원반 + 오른쪽 위 초승달 고리(고리 입자는 연한 남보라). 좌표는 brand/mark.svg(= marks2 N3)와 같은 100×100 기준
  const S = 512, c = document.createElement('canvas'); c.width = c.height = S; const g = c.getContext('2d');
  g.setTransform(5.6, 0, 0, 5.6, 256 - 50 * 5.6, 256 - 50 * 5.6);
  g.fillStyle = 'rgb(255,0,0)'; g.beginPath(); g.arc(46, 54, 30, 0, Math.PI * 2); g.fill();
  g.fillStyle = 'rgb(0,0,255)'; g.fill(new Path2D('M75.88 70.22 A32.6 32.6 0 1 0 29.78 24.12 A34 34 0 0 1 40.31 20.48 A29.4 29.4 0 0 1 79.52 59.69 A34 34 0 0 1 75.88 70.22 Z'));
  const p = g.getImageData(0, 0, S, S).data, pts = [];
  for (let y = 0; y < S; y += 3) for (let x = 0; x < S; x += 3) { const k = (y * S + x) * 4; if (p[k + 3] > 128) pts.push([(x / S - 0.5) * 4.6, -(y / S - 0.5) * 4.6, p[k + 2] > p[k]]); }
  for (let i = pts.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [pts[i], pts[j]] = [pts[j], pts[i]]; }
  return pts;
}
const mark = sampleMark();
const aStart = new Float32Array(N * 3), aEnd = new Float32Array(N * 3), aRnd = new Float32Array(N), aCol = new Float32Array(N * 3);
for (let i = 0; i < N; i++) {
  const a = Math.random() * Math.PI * 2, rr = 6 + Math.random() * 8; aStart.set([Math.cos(a) * rr, Math.sin(a) * rr * 0.6, (Math.random() - 0.5) * 8], i * 3);
  const m = mark[i % mark.length], sc = mobile() ? 0.52 : 1; aEnd.set([m[0] * sc + (Math.random() - 0.5) * 0.05, m[1] * sc + (Math.random() - 0.5) * 0.05, (Math.random() - 0.5) * 0.3], i * 3);
  aRnd[i] = Math.random();
}
// 스크롤 장면용: 구(모든 소식이 한 덩어리) → 막대 두 개(호재·악재 수)
const aSph = new Float32Array(N * 3), aB = new Float32Array(N * 3);
for (let i = 0; i < N; i++) { const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, rr = (mobile() ? 1.3 : 2.1) * Math.cbrt(0.85 + Math.random() * 0.15), s2 = Math.sqrt(1 - u * u);
  aSph.set([rr * s2 * Math.cos(th), rr * u, rr * s2 * Math.sin(th)], i * 3); aB.set([Math.random(), Math.pow(Math.random(), 0.9), Math.random()], i * 3); }
const g = new THREE.BufferGeometry();
g.setAttribute('position', new THREE.BufferAttribute(aEnd.slice(), 3)); g.setAttribute('aStart', new THREE.BufferAttribute(aStart, 3)); g.setAttribute('aEnd', new THREE.BufferAttribute(aEnd, 3));
g.setAttribute('aSph', new THREE.BufferAttribute(aSph, 3)); g.setAttribute('aB', new THREE.BufferAttribute(aB, 3));
g.setAttribute('aRnd', new THREE.BufferAttribute(aRnd, 1)); g.setAttribute('aCol', new THREE.BufferAttribute(aCol, 3));
const U = { uP: { value: reduce ? 1 : 0 }, uT: { value: 0 }, uM: { value: new THREE.Vector3(99, 99, 0) }, uOff: { value: new THREE.Vector2() }, uS1: { value: 0 }, uS2: { value: 0 }, uS3: { value: 0 }, uFu: { value: 0.5 }, uHU: { value: 2.6 }, uHD: { value: 2.6 }, uBW: { value: mobile() ? 0.62 : 1.1 }, uBX: { value: mobile() ? 0.72 : 1.3 }, uBY: { value: mobile() ? -2.55 : -2.55 } };
const mat = new THREE.ShaderMaterial({ uniforms: U, transparent: true, depthWrite: false, vertexShader: `
  attribute vec3 aStart, aEnd, aCol, aSph, aB; attribute float aRnd; uniform float uP, uT, uS1, uS2, uS3, uFu, uHU, uHD, uBW, uBX, uBY; uniform vec3 uM; uniform vec2 uOff; varying vec3 vC; varying float vA;
  void main(){ float p = smoothstep(0., 1., clamp(uP*1.35 - aRnd*.35, 0., 1.));
    float ang = (1.-p)*6.283*(.6+aRnd); vec3 s = aStart; s.xy = mat2(cos(ang),-sin(ang),sin(ang),cos(ang))*s.xy;
    vec3 q = mix(s, aEnd, p);
    // 스크롤 1: 로고가 풀려 한 덩어리 구가 된다(돌면서)
    float k1 = smoothstep(0., 1., clamp(uS1*1.3 - aRnd*.3, 0., 1.));
    float ra = uT*.15 + uS1*2.5; vec3 sp = aSph; sp.xz = mat2(cos(ra),-sin(ra),sin(ra),cos(ra))*sp.xz;
    q = mix(q, sp + vec3(0., -.35, 0.), k1);
    // 스크롤 2: 구가 둘로 갈라져 호재(왼쪽)·악재(오른쪽) 막대가 된다. 막대 높이 = 지난 24시간 개수
    float side = step(aB.x, uFu); float k2 = smoothstep(0., 1., clamp(uS2*1.3 - aRnd*.3, 0., 1.));
    float h = mix(uHD, uHU, side); vec3 bar = vec3(mix(uBX, -uBX, side) + (fract(aB.x*7.31) - .5)*uBW, uBY + aB.y*h, (aB.z - .5)*uBW*.7);
    q = mix(q, bar, k2);
    // 스크롤 3: 위로 흩어지며 사라진다
    q.y += uS3*uS3*(2. + aRnd*6.); q.x += uS3*(aRnd - .5)*4.;
    q.xy += uOff * (1. - k1);
    q += vec3(sin(uT*.6+aRnd*40.), cos(uT*.5+aRnd*31.), sin(uT*.4+aRnd*17.)) * .035 * p;
    vec2 d = q.xy - uM.xy; float f = exp(-dot(d,d)*1.4); q.xy += normalize(d+1e-4)*f*.9; q.z += f*1.2;
    vec3 bc = mix(vec3(.9,.29,.22), vec3(.07,.69,.49), side);
    vC = mix(aCol, mix(aCol, vec3(.42,.42,.97), .55), k1*(1.-k2)); vC = mix(vC, bc, k2*(.55 + .45*step(.25, aRnd))); vA = mix(.25, .8, p) * (1. - .7*uS3);
    vec4 mv = modelViewMatrix*vec4(q,1.); gl_Position = projectionMatrix*mv; gl_PointSize = (1.5 + aRnd*1.3) * (10. / -mv.z) * ${(Math.min(devicePixelRatio || 1, 2)).toFixed(1)}; }`,
  fragmentShader: `varying vec3 vC; varying float vA; void main(){ vec2 c = gl_PointCoord-.5; float d = dot(c,c); if(d>.25) discard; gl_FragColor = vec4(vC, vA*(1.-d*2.)); }` });
scene.add(new THREE.Points(g, mat));
function colors(u, d) {
  const tot = Math.max(1, u + d), fu = u / tot, a = g.getAttribute('aCol');
  const C = { navy: new THREE.Color('#1d3557'), ind: new THREE.Color('#6d6cf7'), lt: new THREE.Color('#a9b7ff'), up: new THREE.Color('#2cc68f'), dn: new THREE.Color('#f06a55'), dot: new THREE.Color('#7f8cff') };
  for (let i = 0; i < N; i++) { const m = mark[i % mark.length], r0 = aRnd[i]; let c = m[2] ? C.dot : r0 < 0.12 ? (r0 / 0.12 < fu ? C.up : C.dn) : r0 < 0.4 ? C.ind : r0 < 0.62 ? C.lt : C.navy; a.setXYZ(i, c.r, c.g, c.b); }
  a.needsUpdate = true;
}
colors(1, 1);
const off = () => mobile() ? new THREE.Vector2(0, 1.75) : new THREE.Vector2(2.6, 0);
const ndc = new THREE.Vector3();
loop(r, scene, cam, (t) => {
  U.uT.value = t; easePointer(0.12); U.uOff.value.copy(off());
  if (pointer.active) { ndc.set(pointer.x, pointer.y, 0.5).unproject(cam); const dir = ndc.sub(cam.position).normalize(), k = -cam.position.z / dir.z; U.uM.value.copy(cam.position).add(dir.multiplyScalar(k)); }
  scene.rotation.y = Math.sin(t * 0.25) * 0.12 + pointer.x * 0.12; scene.rotation.x = pointer.y * 0.08;
});
if (!reduce) gsap.to(U.uP, { value: 1, duration: 3.0, ease: 'power3.inOut', delay: 0.3 });
revealCopy(1.4);
let C24 = { u: 0, d: 0 };
data.flash.then((d) => { const c = DFD.day24(d.items); colors(c.u, c.d); C24 = c;
  const tot = Math.max(1, c.u + c.d), mx = Math.max(c.u, c.d); U.uFu.value = c.u / tot; const H = mobile() ? 2.55 : 3.1; U.uHU.value = H * c.u / mx; U.uHD.value = H * c.d / mx;
  const hud = document.getElementById('hud'), put = () => { hud.innerHTML = `${DFI.lang() === 'ko' ? '입자 ' + N.toLocaleString() + '개 · 초록·빨강 비율 = 24시간 호재·악재' : N.toLocaleString() + ' particles · green/red share = 24h bullish/bearish'} · <span class="up">${c.u}</span>/<span class="down">${c.d}</span>`; };
  put(); DFI.onLang(put); gsap.to(hud, { opacity: 1, duration: 0.8, delay: 2.8 }); });

// ---------- 스크롤: 첫 화면을 고정한 채 로고 → 구 → 호재·악재 막대 → 흩어짐 ----------
gsap.registerPlugin(ScrollTrigger);
const hero = document.getElementById('hero'), sc = document.getElementById('sc'), nL = document.getElementById('nL'), nR = document.getElementById('nR');
const CAP = { en: [['Every story becomes a point.', 'The last 24 hours, gathered into one field.'], ['Then each one is judged.', 'Bullish to the left, bearish to the right — real 24h counts.']],
  ko: [['모든 소식은 하나의 점이 돼요.', '지난 24시간이 한 덩어리로 모였어요.'], ['그리고 하나하나 판정해요.', '호재는 왼쪽, 악재는 오른쪽 — 실제 24시간 개수예요.']] };
let ci = -1; const cap = (k) => { if (k === ci) return; ci = k; const c = (CAP[DFI.lang()] || CAP.en)[k]; sc.querySelector('b').textContent = c[0]; sc.querySelector('span').textContent = c[1]; };
DFI.onLang(() => { const k = ci; ci = -1; cap(Math.max(0, k)); });
const tl = gsap.timeline({ scrollTrigger: { trigger: hero, start: 'top top', end: '+=240%', pin: true, scrub: 0.8, anticipatePin: 1 } });
tl.to('.copy', { y: -80, opacity: 0, filter: 'blur(8px)', duration: 0.25, ease: 'power2.in' }, 0)
  .to('#hud', { opacity: 0, duration: 0.1 }, 0)
  .fromTo(hero, { '--wm': 1 }, { '--wm': 0, duration: 0.2 }, 0.02)
  .to(U.uS1, { value: 1, duration: 0.35, ease: 'none' }, 0.05)
  .fromTo(sc, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.12, onStart: () => cap(0), onReverseComplete: () => {} }, 0.15)
  .to(sc, { opacity: 0, y: -10, duration: 0.06, onComplete: () => cap(1), onReverseComplete: () => cap(0) }, 0.42)
  .to(sc, { opacity: 1, y: 0, duration: 0.08 }, 0.49)
  .to(U.uS2, { value: 1, duration: 0.3, ease: 'none' }, 0.45)
  .fromTo(['#nL', '#nR'], { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0.68)
  .to({ v: 0 }, { v: 1, duration: 0.12, onUpdate() { const f = this.targets()[0].v; nL.querySelector('b').textContent = Math.round(C24.u * f); nR.querySelector('b').textContent = Math.round(C24.d * f); } }, 0.68)
  .to(['#sc', '#nL', '#nR'], { opacity: 0, duration: 0.08 }, 0.9)
  .to(U.uS3, { value: 1, duration: 0.12, ease: 'power1.in' }, 0.88);
// 막대 위 숫자 자리: 3D 좌표를 화면으로
const v3 = new THREE.Vector3();
gsap.ticker.add(() => { if (U.uS2.value <= 0) return; const put = (el, x, h) => { v3.set(x, U.uBY.value + h + 0.3, 0).applyMatrix4(scene.matrixWorld).project(cam);
  el.style.left = ((v3.x + 1) / 2 * hero.clientWidth) + 'px'; el.style.top = ((1 - v3.y) / 2 * hero.clientHeight) + 'px'; };
  put(nL, -U.uBX.value, U.uHU.value); put(nR, U.uBX.value, U.uHD.value); });
