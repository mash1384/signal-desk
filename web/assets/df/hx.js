// 첫 화면 스크롤 장면: 글(LIVE·제목·설명·버튼)이 그 자리에서 입자로 부서져 흩어지고 → 한 덩어리 구가 됐다가 → 호재(왼쪽)·악재(오른쪽) 막대로 갈라진다.
// 막대 높이 = 지난 24시간 실제 개수. 입자는 쉬는 동안 안 보이고(글이 그대로 보임), 스크롤을 시작하면 글 화소 자리에 나타나 글을 대신한다.
// 글 자리는 화면의 글자 하나하나 위치(Range)를 같은 글꼴로 캔버스에 다시 그려 뽑는다 → 3D 평면(z=0) 좌표로 옮긴다.
import * as THREE from 'three';
import { renderer, loop, pointer, easePointer, reduce, mobile, data } from './kit.js';
const hero = document.getElementById('hero'), copyEl = hero.querySelector('.copy');
const canvas = document.createElement('canvas'); canvas.className = 'hx'; canvas.setAttribute('aria-hidden', 'true'); hero.prepend(canvas);
const r = renderer(canvas, { alpha: true }); r.setClearColor(0x000000, 0);
const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(35, 1, 0.1, 100); cam.position.set(0, 0, 10);
const N = mobile() ? 9000 : 16000;
// 화면 글 → 점(css px, hero 기준)
function sampleCopy() {
  const W = hero.clientWidth, H = hero.clientHeight, c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d');
  const hr = hero.getBoundingClientRect();
  const walk = (el) => { const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n; while ((n = tw.nextNode())) {
    const cs = getComputedStyle(n.parentElement); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    g.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`; g.fillStyle = cs.color; g.textBaseline = 'alphabetic';
    if ('letterSpacing' in g) g.letterSpacing = cs.letterSpacing === 'normal' ? '0px' : cs.letterSpacing;
    const asc = g.measureText('가Hg').fontBoundingBoxAscent;
    for (let i = 0; i < n.textContent.length; i++) { const ch = n.textContent[i]; if (!ch.trim()) continue;
      const rg = document.createRange(); rg.setStart(n, i); rg.setEnd(n, i + 1); const q = rg.getClientRects()[0]; if (!q || !q.width) continue;
      g.fillText(ch, q.left - hr.left, q.top - hr.top + asc); } } };
  // 바탕이 칠해진 것(LIVE 배지·버튼 알약)을 먼저, 그 위에 글자
  copyEl.querySelectorAll('.kick b, .btn.p').forEach((b) => { const q = b.getBoundingClientRect(), x = q.left - hr.left, y = q.top - hr.top; g.fillStyle = getComputedStyle(b).backgroundColor; g.beginPath(); g.roundRect(x, y, q.width, q.height, q.height / 2); g.fill(); });
  copyEl.querySelectorAll('.kick, h1, .sub, .btns').forEach(walk);
  const d = g.getImageData(0, 0, W, H).data, pts = [], st = 2;
  for (let y = 0; y < H; y += st) for (let x = 0; x < W; x += st) { const k = (y * W + x) * 4; if (d[k + 3] > 110) pts.push([x, y, d[k] / 255, d[k + 1] / 255, d[k + 2] / 255]); }
  for (let i = pts.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [pts[i], pts[j]] = [pts[j], pts[i]]; }
  return { pts, W, H };
}
const aInk = new Float32Array(N * 3), aEnd = new Float32Array(N * 3), aRnd = new Float32Array(N), aCol = new Float32Array(N * 3), aDir = new Float32Array(N * 3);
const aSph = new Float32Array(N * 3), aB = new Float32Array(N * 3);
for (let i = 0; i < N; i++) {
  aRnd[i] = Math.random(); const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, rr = (mobile() ? 1.3 : 2.1) * Math.cbrt(0.85 + Math.random() * 0.15), s2 = Math.sqrt(1 - u * u);
  aSph.set([rr * s2 * Math.cos(th), rr * u, rr * s2 * Math.sin(th)], i * 3); aB.set([Math.random(), Math.pow(Math.random(), 0.9), Math.random()], i * 3);
  const a = Math.random() * Math.PI * 2, z = Math.random() * 2 - 1; aDir.set([Math.cos(a) * Math.sqrt(1 - z * z), Math.sin(a) * Math.sqrt(1 - z * z), z], i * 3);
}
const g = new THREE.BufferGeometry();
for (const [k, v, n] of [['position', aEnd, 3], ['aEnd', aEnd, 3], ['aSph', aSph, 3], ['aB', aB, 3], ['aRnd', aRnd, 1], ['aCol', aCol, 3], ['aDir', aDir, 3], ['aInk', aInk, 3]]) g.setAttribute(k, new THREE.BufferAttribute(v, n));
g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 50);
const U = { uT: { value: 0 }, uM: { value: new THREE.Vector3(99, 99, 0) }, uV: { value: 0 }, uX: { value: 0 }, uS1: { value: 0 }, uS2: { value: 0 }, uS3: { value: 0 }, uFu: { value: 0.5 },
  uHU: { value: 2.6 }, uHD: { value: 2.6 }, uBW: { value: mobile() ? 0.62 : 1.1 }, uBX: { value: mobile() ? 0.72 : 1.3 }, uBY: { value: -2.55 }, uPx: { value: 1 } };
const mat = new THREE.ShaderMaterial({ uniforms: U, transparent: true, depthWrite: false, vertexShader: `
  attribute vec3 aEnd, aCol, aSph, aB, aDir, aInk; attribute float aRnd; uniform float uT, uV, uX, uS1, uS2, uS3, uFu, uHU, uHD, uBW, uBX, uBY, uPx; uniform vec3 uM; varying vec3 vC; varying float vA;
  void main(){
    // 0: 글 자리 → 사방으로 살짝 터지며 흩어진다
    float kx = smoothstep(0., 1., clamp(uX*1.4 - aRnd*.4, 0., 1.));
    vec3 q = aEnd + aDir * kx * (.35 + aRnd * 1.1) + vec3(0., 0., kx * (aRnd - .5));
    // 1: 한 덩어리 구(돌면서)
    float k1 = smoothstep(0., 1., clamp(uS1*1.3 - aRnd*.3, 0., 1.));
    float ra = uT*.15 + uS1*2.5; vec3 sp = aSph; sp.xz = mat2(cos(ra),-sin(ra),sin(ra),cos(ra))*sp.xz;
    q = mix(q, sp + vec3(0., -.35, 0.), k1);
    // 2: 둘로 갈라져 호재(왼쪽)·악재(오른쪽) 막대. 높이 = 24시간 개수
    float side = step(aB.x, uFu); float k2 = smoothstep(0., 1., clamp(uS2*1.3 - aRnd*.3, 0., 1.));
    float h = mix(uHD, uHU, side); vec3 bar = vec3(mix(uBX, -uBX, side) + (fract(aB.x*7.31) - .5)*uBW, uBY + aB.y*h, (aB.z - .5)*uBW*.7);
    q = mix(q, bar, k2);
    // 3: 위로 흩어지며 사라진다
    q.y += uS3*uS3*(2. + aRnd*6.); q.x += uS3*(aRnd - .5)*4.;
    q += vec3(sin(uT*.6+aRnd*40.), cos(uT*.5+aRnd*31.), sin(uT*.4+aRnd*17.)) * .035 * kx;
    vec2 d = q.xy - uM.xy; float f = exp(-dot(d,d)*1.4) * k1; q.xy += normalize(d+1e-4)*f*.9; q.z += f*1.2;
    vec3 bc = mix(vec3(.9,.29,.22), vec3(.07,.69,.49), side);
    vC = mix(aInk, aCol, kx);   // 글 단계 = 화면 글자·바탕 색 그대로 vC = mix(vC, mix(aCol, vec3(.42,.42,.97), .55), k1*(1.-k2)); vC = mix(vC, bc, k2*(.55 + .45*step(.25, aRnd)));
    vA = uV * mix(1., .8, kx) * (1. - .7*uS3);
    vec4 mv = modelViewMatrix*vec4(q,1.); gl_Position = projectionMatrix*mv;
    gl_PointSize = mix(uPx * 2.2, (1.5 + aRnd*1.3) * (10. / -mv.z), kx) * ${(Math.min(devicePixelRatio || 1, 2)).toFixed(1)}; }`,
  fragmentShader: `varying vec3 vC; varying float vA; void main(){ vec2 c = gl_PointCoord-.5; float d = dot(c,c); if(d>.25) discard; gl_FragColor = vec4(vC, vA*(1.-d*2.)); }` });
const pts = new THREE.Points(g, mat); scene.add(pts);
function colors(u, d) {
  const tot = Math.max(1, u + d), fu = u / tot, a = g.getAttribute('aCol');
  const C = { navy: new THREE.Color('#1d3557'), ind: new THREE.Color('#6d6cf7'), lt: new THREE.Color('#a9b7ff'), up: new THREE.Color('#2cc68f'), dn: new THREE.Color('#f06a55') };
  for (let i = 0; i < N; i++) { const r0 = aRnd[i]; const c = r0 < 0.12 ? (r0 / 0.12 < fu ? C.up : C.dn) : r0 < 0.4 ? C.ind : r0 < 0.62 ? C.lt : C.navy; a.setXYZ(i, c.r, c.g, c.b); }
  a.needsUpdate = true;
}
colors(1, 1);
// 글 자리 채우기(화면 크기가 바뀌면 다시)
const plane = () => { const h = 2 * cam.position.z * Math.tan((cam.fov * Math.PI) / 360); return { w: h * (hero.clientWidth / hero.clientHeight), h }; };
function place() {
  const s = sampleCopy(), P = plane(), a = g.getAttribute('aEnd'), p = g.getAttribute('position'), ink = g.getAttribute('aInk');
  if (!s.pts.length) return;
  for (let i = 0; i < N; i++) { const [x, y, cr, cg, cb] = s.pts[i % s.pts.length]; const j = i < s.pts.length ? 0 : 0.6;
    a.setXYZ(i, ((x + (Math.random() - .5) * j) / s.W - 0.5) * P.w, -((y + (Math.random() - .5) * j) / s.H - 0.5) * P.h, 0); ink.setXYZ(i, cr, cg, cb); }
  a.needsUpdate = true; ink.needsUpdate = true; p.copyArray(a.array); p.needsUpdate = true;
  U.uPx.value = (P.h / s.H) * (hero.clientHeight / P.h) * 1.0;   // 글 단계 점 크기(css px)
}
const ndc = new THREE.Vector3();
loop(r, scene, cam, (t) => {
  U.uT.value = t; easePointer(0.12);
  if (pointer.active) { ndc.set(pointer.x, pointer.y, 0.5).unproject(cam); const dir = ndc.sub(cam.position).normalize(), k = -cam.position.z / dir.z; U.uM.value.copy(cam.position).add(dir.multiplyScalar(k)); }
  const k = U.uS1.value; scene.rotation.y = (Math.sin(t * 0.25) * 0.12 + pointer.x * 0.12) * k; scene.rotation.x = pointer.y * 0.08 * k;   // 글 단계에선 글과 겹치게 정면
});
let C24 = { u: 0, d: 0 };
data.flash.then((d) => { const c = DFD.day24(d.items); colors(c.u, c.d); C24 = c;
  const tot = Math.max(1, c.u + c.d), mx = Math.max(1, c.u, c.d); U.uFu.value = c.u / tot; const H = mobile() ? 2.55 : 3.1; U.uHU.value = H * c.u / mx; U.uHD.value = H * c.d / mx; });
// 글이 다 올라온 뒤(움직임 끝) 자리 잡기
const settle = () => Promise.all(copyEl.querySelectorAll('.reveal').length ? [...copyEl.querySelectorAll('.reveal')].flatMap((e) => e.getAnimations().map((a) => a.finished.catch(() => {}))) : []);
await document.fonts.ready; await settle(); place();   // 글이 아직 투명해도 자리는 최종 위치(.reveal 은 transform 없음)
let rz; const replace = () => { clearTimeout(rz); rz = setTimeout(place, 200); };
addEventListener('resize', replace); document.fonts.addEventListener('loadingdone', replace); addEventListener('df-intro-done', () => setTimeout(replace, 1200), { once: true });
// ---------- 스크롤: 첫 화면을 고정한 채 글 → 입자 → 구 → 호재·악재 막대 → 흩어짐 ----------
gsap.registerPlugin(ScrollTrigger);
const sc = document.getElementById('sc'), nL = document.getElementById('nL'), nR = document.getElementById('nR');
const CAP = { en: [['Every story becomes a point.', 'The last 24 hours, gathered into one field.'], ['Then each one is judged.', 'Bullish to the left, bearish to the right — real 24h counts.']],
  ko: [['모든 소식은 하나의 점이 돼요.', '지난 24시간이 한 덩어리로 모였어요.'], ['그리고 하나하나 판정해요.', '호재는 왼쪽, 악재는 오른쪽 — 실제 24시간 개수예요.']] };
let ci = -1; const cap = (k) => { if (k === ci) return; ci = k; const c = (CAP[DFI.lang()] || CAP.en)[k]; sc.querySelector('b').textContent = c[0]; sc.querySelector('span').textContent = c[1]; };
DFI.onLang(() => { const k = ci; ci = -1; cap(Math.max(0, k)); setTimeout(place, 50); });
const tl = gsap.timeline({ scrollTrigger: { trigger: hero, start: 'top top', end: '+=240%', pin: true, scrub: 0.8, anticipatePin: 1 } });
tl.to(U.uV, { value: 1, duration: 0.03, ease: 'none' }, 0)                 // 입자가 글 자리에 켜지고
  .to(copyEl, { opacity: 0, duration: 0.035, ease: 'none' }, 0.005)          // 같은 순간 글은 꺼진다(입자가 글을 대신함)
  .to(U.uX, { value: 1, duration: 0.2, ease: 'power1.out' }, 0.02)           // 사방으로 부서져 흩어지고
  .to(U.uS1, { value: 1, duration: 0.33, ease: 'none' }, 0.1)                // 구로 모인다
  .fromTo(sc, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.12, onStart: () => cap(0) }, 0.18)
  .to(sc, { opacity: 0, y: -10, duration: 0.06, onComplete: () => cap(1), onReverseComplete: () => cap(0) }, 0.42)
  .to(sc, { opacity: 1, y: 0, duration: 0.08 }, 0.49)
  .to(U.uS2, { value: 1, duration: 0.3, ease: 'none' }, 0.45)
  .fromTo(['#nL', '#nR'], { opacity: 0 }, { opacity: 1, duration: 0.1 }, 0.68)
  .to({ v: 0 }, { v: 1, duration: 0.12, onUpdate() { const f = this.targets()[0].v; nL.querySelector('b').textContent = Math.round(C24.u * f); nR.querySelector('b').textContent = Math.round(C24.d * f); } }, 0.68)
  .to(['#sc', '#nL', '#nR'], { opacity: 0, duration: 0.08 }, 0.9)
  .to(U.uS3, { value: 1, duration: 0.12, ease: 'power1.in' }, 0.88);
const v3 = new THREE.Vector3();
gsap.ticker.add(() => { if (U.uS2.value <= 0) return; const put = (el, x, h) => { v3.set(x, U.uBY.value + h + 0.3, 0).applyMatrix4(scene.matrixWorld).project(cam);
  el.style.left = ((v3.x + 1) / 2 * hero.clientWidth) + 'px'; el.style.top = ((1 - v3.y) / 2 * hero.clientHeight) + 'px'; };
  put(nL, -U.uBX.value, U.uHU.value); put(nR, U.uBX.value, U.uHD.value); });
dispatchEvent(new Event('df-hx-ready'));
