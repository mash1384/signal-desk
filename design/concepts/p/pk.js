// 다음 섹션 후보 P1~P5 공통: H3 오프닝의 '입자' 언어를 그대로 잇는다.
// Morph: 입자 N개가 최대 5개의 '모양(stage)' 사이를 스크롤에 따라 오간다. 전환 중간에는 살짝 흩어졌다(burst) 다시 모인다.
import * as THREE from 'three';
export { renderer, loop, mobile, reduce, fonts, lerp, clamp, ss, EN, SECT } from '../n/nkit.js';
import { clamp, mobile } from '../n/nkit.js';

export const DPR = Math.min(devicePixelRatio || 1, 2);
export const COL = { navy: new THREE.Color('#1d3557'), ink: new THREE.Color('#0d253d'), ind: new THREE.Color('#6d6cf7'), lt: new THREE.Color('#a9b7ff'), up: new THREE.Color('#12b07c'), dn: new THREE.Color('#e5533f'), gray: new THREE.Color('#9aa7b8') };
export const sm = (x) => { x = clamp(x); return x * x * x * (x * (x * 6 - 15) + 10); };
export const rnd = (a = 1) => (Math.random() * 2 - 1) * a;

export class Morph {
  constructor(N, K = 5) {
    this.N = N; this.K = K; this.P = []; this.C = [];
    const g = this.g = new THREE.BufferGeometry();
    for (let k = 0; k < 5; k++) { const p = new Float32Array(N * 3), c = new Float32Array(N * 4); this.P.push(p); this.C.push(c);
      g.setAttribute('p' + k, new THREE.BufferAttribute(p, 3)); g.setAttribute('c' + k, new THREE.BufferAttribute(c, 4)); }
    const r = new Float32Array(N), b = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) { r[i] = Math.random(); const u = Math.random() * 2 - 1, th = Math.random() * 6.283, s = Math.sqrt(1 - u * u); b.set([s * Math.cos(th), u, s * Math.sin(th)], i * 3); }
    g.setAttribute('aR', new THREE.BufferAttribute(r, 1)); g.setAttribute('aB', new THREE.BufferAttribute(b, 3));
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3));
    this.U = { uS: { value: 0 }, uT: { value: 0 }, uSz: { value: 1 }, uBurst: { value: 0.9 }, uWob: { value: 0.03 }, uHiX: { value: 1e9 }, uHiW: { value: 0.5 }, uHiOn: { value: 0 }, uA: { value: 1 } };
    this.mat = new THREE.ShaderMaterial({ uniforms: this.U, transparent: true, depthWrite: false, vertexShader: `
      attribute vec3 p0, p1, p2, p3, p4, aB; attribute vec4 c0, c1, c2, c3, c4; attribute float aR;
      uniform float uS, uT, uSz, uBurst, uWob, uHiX, uHiW, uHiOn, uA; varying vec4 vC; varying float vH;
      float w(float k, float s){ return max(0., 1. - abs(s - k)); }
      void main(){
        float k = floor(uS), f = uS - k; float fi = clamp((f - aR * .28) / .72, 0., 1.); fi = fi * fi * fi * (fi * (fi * 6. - 15.) + 10.); float s = k + fi;
        vec3 p = p0 * w(0., s) + p1 * w(1., s) + p2 * w(2., s) + p3 * w(3., s) + p4 * w(4., s);
        vec4 c = c0 * w(0., s) + c1 * w(1., s) + c2 * w(2., s) + c3 * w(3., s) + c4 * w(4., s);
        p += aB * sin(3.14159 * fi) * uBurst * (.5 + aR);                                   // 전환 중간: 살짝 흩어졌다 모인다
        p += vec3(sin(uT * .7 + aR * 40.), cos(uT * .6 + aR * 31.), sin(uT * .5 + aR * 17.)) * uWob;   // 숨쉬기
        float hi = uHiOn * exp(-pow((p.x - uHiX) / uHiW, 2.)); vH = hi;
        vC = vec4(mix(c.rgb, c.rgb * 1.05 + .08, hi), c.a * uA * (1. + hi * .6));
        vec4 mv = modelViewMatrix * vec4(p, 1.); gl_Position = projectionMatrix * mv;
        gl_PointSize = max(1.2, uSz * (1.4 + aR * 1.4) * (1. + hi * .9) * (10. / -mv.z) * ${DPR.toFixed(1)}); }`,
      fragmentShader: `varying vec4 vC; varying float vH; void main(){ vec2 q = gl_PointCoord - .5; float d = dot(q, q); if (d > .25) discard; gl_FragColor = vec4(vC.rgb, vC.a * (1. - d * 2.6)); }` });
    this.points = new THREE.Points(g, this.mat); this.points.frustumCulled = false;
  }
  // stage k를 채운다: fn(i) → [x,y,z, r,g,b,a]
  set(k, fn) { const p = this.P[k], c = this.C[k], o = new Array(7);
    for (let i = 0; i < this.N; i++) { const v = fn(i, o); p[i * 3] = v[0]; p[i * 3 + 1] = v[1]; p[i * 3 + 2] = v[2]; c[i * 4] = v[3]; c[i * 4 + 1] = v[4]; c[i * 4 + 2] = v[5]; c[i * 4 + 3] = v[6]; }
    this.g.getAttribute('p' + k).needsUpdate = true; this.g.getAttribute('c' + k).needsUpdate = true; }
  copy(from, to) { this.P[to].set(this.P[from]); this.C[to].set(this.C[from]); this.g.getAttribute('p' + to).needsUpdate = true; this.g.getAttribute('c' + to).needsUpdate = true; }
}

// 오프닝 끝(입자가 위로 흩어짐)을 잇는 첫 모양: 화면 위쪽에 넓게 퍼진 옅은 구름
export function cloud(m, k, { w = 16, h = 7, y = 3.5, d = 6 } = {}) {
  m.set(k, (i, o) => { const r = Math.random(), c = r < 0.45 ? COL.navy : r < 0.75 ? COL.ind : COL.lt;
    o[0] = rnd(w / 2); o[1] = y + rnd(h / 2); o[2] = rnd(d / 2); o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = 0.35; return o; });
}

// 글자 → 점(캔버스에 그려 픽셀을 뽑는다). 반환: [{x,y}] (가운데 기준, 높이 hgt 월드 단위)
export function textPoints(text, { font = '300 220px Inter', hgt = 2, step = 3, align = 'center' } = {}) {
  const c = document.createElement('canvas'), g = c.getContext('2d'); g.font = font;
  const lines = String(text).split('\n'), lh = parseFloat(/(\d+)px/.exec(font)[1]) * 1.05, W = Math.ceil(Math.max(...lines.map((l) => g.measureText(l).width))) + 20, H = Math.ceil(lh * lines.length) + 20;
  c.width = W; c.height = H; g.font = font; g.fillStyle = '#000'; g.textBaseline = 'top'; g.textAlign = align === 'center' ? 'center' : 'left';
  lines.forEach((l, j) => g.fillText(l, align === 'center' ? W / 2 : 10, 10 + j * lh));
  const d = g.getImageData(0, 0, W, H).data, pts = [], sc = hgt / H;
  for (let y = 0; y < H; y += step) for (let x = 0; x < W; x += step) if (d[(y * W + x) * 4 + 3] > 120) pts.push({ x: (x - W / 2) * sc, y: -(y - H / 2) * sc });
  pts.W = W * sc; pts.H = H * sc; return pts;
}

// 스크롤로 섹션 고정 + 0..1 진행(부드럽게)
export function pin(sec, len, onP) {
  gsap.registerPlugin(ScrollTrigger); const st = { P: 0, T: 0 };
  ScrollTrigger.create({ trigger: sec, start: 'top top', end: '+=' + len + '%', pin: true, anticipatePin: 1, onUpdate: (s) => { st.T = s.progress; } });
  st.step = (dt) => { st.P += (st.T - st.P) * Math.min(1, dt * 10); return st.P; };
  // ?go=1: 오프닝을 건너뛰고 이 섹션 처음으로(미리보기용)
  if (/go=1/.test(location.search)) addEventListener('load', () => setTimeout(() => { ScrollTrigger.refresh(); const t = ScrollTrigger.getAll().find((x) => x.trigger === sec); if (t) scrollTo(0, t.start + 2); }, 900));
  return st;
}
// 진행 P → stage 값: keys = 각 stage가 '완성'되는 진행 위치들(오름차순). 사이 구간에서 부드럽게 넘어간다(앞뒤 머묾)
export function stageOf(P, keys, hold = 0.35) {
  if (P <= keys[0]) return 0; for (let k = 0; k < keys.length - 1; k++) { const a = keys[k], b = keys[k + 1]; if (P < b) { const f = (P - a) / (b - a); return k + clamp((f - hold / 2) / (1 - hold)); } }
  return keys.length - 1;
}

// 3D 점 → 화면 좌표
const v3 = new THREE.Vector3();
export function project(cam, el, p) { v3.copy(p).project(cam); return [(v3.x + 1) / 2 * el.clientWidth, (1 - v3.y) / 2 * el.clientHeight, v3.z]; }

// 글(캡션) 바꾸기: 같은 단계면 그대로
export function captions(el, list) { let cur = -1; const L = () => DFI.lang() === 'ko' ? 1 : 0;
  const set = (k) => { if (k === cur) return; cur = k; const c = list[k]; if (!c) { el.innerHTML = ''; return; } el.innerHTML = `<b>${c[L()][0]}</b>${c[L()][1] ? `<span>${c[L()][1]}</span>` : ''}`; };
  DFI.onLang(() => { const k = cur; cur = -1; set(k); }); return set; }

export const T = (en, ko) => DFI.lang() === 'ko' ? ko : en;
export const line = (it, ENT) => DFI.lang() === 'ko' ? it.ko : (it.en || ENT[it.id] || it.ko);

// 캔버스에 그린 모양 → 점. fn(g, W, H)로 그린다. 반환 점 좌표는 가운데 기준, 가로 wid 월드 단위
export function drawPoints(fn, { W = 512, H = 512, wid = 1, step = 3 } = {}) {
  const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d'); g.fillStyle = '#000'; g.strokeStyle = '#000'; fn(g, W, H);
  const d = g.getImageData(0, 0, W, H).data, pts = [], sc = wid / W;
  for (let y = 0; y < H; y += step) for (let x = 0; x < W; x += step) if (d[(y * W + x) * 4 + 3] > 120) pts.push({ x: (x - W / 2) * sc, y: -(y - H / 2) * sc });
  return pts;
}
// 둥근 사각형 테두리 위의 점(t: 0..1 둘레)
export function rrEdge(t, w, h, r) {
  const L = [w - 2 * r, Math.PI * r / 2, h - 2 * r, Math.PI * r / 2, w - 2 * r, Math.PI * r / 2, h - 2 * r, Math.PI * r / 2], tot = L.reduce((a, b) => a + b); let d = t * tot, k = 0;
  while (k < 7 && d > L[k]) { d -= L[k]; k++; }
  const x0 = w / 2 - r, y0 = h / 2 - r, a = (q) => d / r + q;
  switch (k) { case 0: return [-x0 + d, h / 2]; case 1: return [x0 + r * Math.sin(a(0)), y0 + r * Math.cos(a(0))]; case 2: return [w / 2, y0 - d]; case 3: return [x0 + r * Math.cos(a(0)), -y0 - r * Math.sin(a(0))];
    case 4: return [x0 - d, -h / 2]; case 5: return [-x0 - r * Math.sin(a(0)), -y0 - r * Math.cos(a(0))]; case 6: return [-w / 2, -y0 + d]; default: return [-x0 - r * Math.cos(a(0)), y0 + r * Math.sin(a(0))]; }
}
