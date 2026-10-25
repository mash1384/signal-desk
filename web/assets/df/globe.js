// P5 다음 장면 · 지구(?br=4): 파형 입자가 흩어졌다 모여 거대한 입자 지구가 된다.
// 대륙은 촘촘한 입자, 바다는 옅은 입자, 둘레엔 대기 빛과 궤도 고리. 스크롤하면 지구가 돌아 테마별 도시(크립토=싱가포르, 나스닥=뉴욕, 경제=런던, AI=샌프란시스코)를 정면에 두고,
// 그 도시에서 빛기둥이 솟으며 그 분야 한 줄이 나온다. 제목 · 분야 한 줄은 브리핑(briefing.json, 하루 4번), 건수 · 호재악재는 themes.json.
// 브리핑이 없거나 48시간 넘게 묵었으면 themes.json 의 예전 요약을 그대로 쓴다.
import * as THREE from 'three';
import { Morph, COL, clamp, ss, sm, lerp, rnd, project, T, textPoints } from './pk.js';

const THEMES = { crypto: { name: ['Crypto', '크립토'], city: ['Singapore', '싱가포르'], lat: 1.35, lon: 103.8 }, nasdaq: { name: ['Nasdaq', '나스닥'], city: ['New York', '뉴욕'], lat: 40.7, lon: -74.0 },
  econ: { name: ['Economy', '경제'], city: ['London', '런던'], lat: 51.5, lon: -0.1 }, ai: { name: ['AI', 'AI'], city: ['San Francisco', '샌프란시스코'], lat: 37.8, lon: -122.4 } };
const ORDER = ['crypto', 'nasdaq', 'econ', 'ai'];
const D2R = Math.PI / 180;
// 다크 모드: 첫 페이지는 테마를 바꾸면 다시 불러오므로 처음 한 번만 본다
const DK = document.documentElement.dataset.theme === 'dark';

export function makeGlobe({ scene, sec, lay, mob }) {
  const N = mob ? 22000 : 42000, m = new Morph(N); m.points.visible = false; m.U.uBurst.value = mob ? 5 : 8; m.U.uWob.value = 0.006; m.U.uSz.value = mob ? 0.85 : 0.9; scene.add(m.points);
  const L = () => (DFI.lang() === 'ko' ? 1 : 0);
  const R = mob ? 2.3 : 3.9, C = mob ? new THREE.Vector3(0, 3.5, 0) : new THREE.Vector3(-2.7, -0.55, 0);
  // ---- 대기 빛(지구 뒤 둥근 후광) ----
  const halo = new THREE.Mesh(new THREE.PlaneGeometry(R * 3.2, R * 3.2), new THREE.ShaderMaterial({ transparent: true, depthWrite: false, uniforms: { uA: { value: 0 } },
    vertexShader: 'varying vec2 vU; void main(){ vU = uv * 2. - 1.; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
    fragmentShader: `uniform float uA; varying vec2 vU; void main(){ float r = length(vU) * 1.6; float rim = exp(-pow((r - 1.01) * 16., 2.)) * .16 + smoothstep(1.4, 1., r) * .07 * step(1., r);
      float inner = 0.; gl_FragColor = vec4(vec3(.36,.33,.99), (rim + inner) * uA); }` }));
  halo.position.copy(C).add(new THREE.Vector3(0, 0, -R * 0.2)); halo.renderOrder = -3; scene.add(halo);
  // ---- 모양(?sh=globe|radar|cube|galaxy|bloom). 모두 같은 규칙: 몸체(0)·옅은 입자(1)·움직이는 고리/스윕(2)·테마 j 입자(3+j) ----
  const SH = (new URLSearchParams(location.search).get('sh') || 'globe').toLowerCase();
  const base = new Float32Array(N * 3), col = new Float32Array(N * 4), kindOf = new Uint8Array(N), seed = new Float32Array(N);
  let ready = false, ORI = null, ANCH = null;   // ORI[k] = [rotY, rotX] (테마 k를 정면에), ANCH[k] = 이름표 자리(물체 좌표)
  const setP = (i, x, y, z, c, a, k, sd = Math.random()) => { base[i * 3] = x; base[i * 3 + 1] = y; base[i * 3 + 2] = z; col[i * 4] = c.r; col[i * 4 + 1] = c.g; col[i * 4 + 2] = c.b; col[i * 4 + 3] = a; kindOf[i] = k; seed[i] = sd; };
  const vC = (v) => v === '호재' ? COL.up : v === '악재' ? COL.dn : COL.gray;
  const tmp = new THREE.Color();
  const aux = new Float32Array(N), U3 = (lat, lon) => { const cl = Math.cos(lat * D2R); return new THREE.Vector3(cl * Math.sin(lon * D2R), Math.sin(lat * D2R), cl * Math.cos(lon * D2R)); };
  const CITY = ORDER.map((k) => U3(THEMES[k].lat, THEMES[k].lon));
  // 소식이 날아오는 곳(아크 모션): 세계 주요 도시
  const SRC = [[35.7, 139.7], [37.6, 127.0], [22.3, 114.2], [31.2, 121.5], [19.1, 72.9], [25.2, 55.3], [50.1, 8.7], [48.9, 2.35], [55.8, 37.6], [-23.5, -46.6], [-33.9, 151.2], [43.7, -79.4], [19.4, -99.1], [-26.2, 28.0], [52.5, 13.4], [1.35, 103.8], [40.7, -74.0], [51.5, -0.1], [37.8, -122.4]].map(([a, b]) => U3(a, b));
  const MV = (new URLSearchParams(location.search).get('mv') || 'arcs').toLowerCase();
  function buildGlobe(d, W, H) {
    const land = (lat, lon) => { const x = Math.min(W - 1, (((lon + 540) % 360) / 360 * W) | 0), y = Math.min(H - 1, ((90 - lat) / 180 * H) | 0); return d[(y * W + x) * 4] > 128; };
    const put = (i, lat, lon, r, c, a, k, sd) => { const cl = Math.cos(lat * D2R); setP(i, cl * Math.sin(lon * D2R) * r, Math.sin(lat * D2R) * r, cl * Math.cos(lon * D2R) * r, c, a, k, sd); };
    // 대륙: 위도·경도 격자 위의 점(하프톤 지도처럼 가지런하게)
    const nLand = Math.floor(N * 0.8), pts = [], st = Math.sqrt(41253 * 0.3 / nLand);
    for (let lat = -82; lat <= 84; lat += st) { const dl = st / Math.max(0.12, Math.cos(lat * D2R)); for (let lon = -180 + ((lat / st) % 2) * dl * 0.5; lon < 180; lon += dl) if (land(lat, lon)) pts.push([lat, lon]); }
    for (let q = pts.length - 1; q > 0; q--) { const r = (Math.random() * (q + 1)) | 0; [pts[q], pts[r]] = [pts[r], pts[q]]; }
    let i = 0;
    for (const [lat, lon] of pts.slice(0, nLand)) { const pol = Math.abs(lat) > 60 ? 0.35 : 0; tmp.copy(COL.ink).lerp(COL.ind, pol + 0.18 * Math.random()); put(i++, lat, lon, R * 1.002, tmp, 0.82 - pol * 0.4, 0); }
    const nRing = Math.floor(N * 0.035); for (let q = 0; q < nRing; q++) { const a = Math.random() * 6.283, rr = R * (1.3 + Math.random() * 0.025); tmp.copy(COL.ind).lerp(COL.lt, Math.random()); setP(i++, Math.cos(a) * rr, rnd(0.008), Math.sin(a) * rr, tmp, 0.4, 2); }
    // 나머지: 테마 j 모션용 입자(실제 위치는 매 프레임 계산)
    const per = Math.floor((N - i) / 4); for (let j = 0; j < 4; j++) for (let q = 0; q < per && i < N; q++) { setP(i, 0, 0, 0, COL.ind, 0.9, 3 + j); aux[i] = Math.random(); i++; }
    while (i < N) setP(i++, 0, 0, 0, COL.lt, 0, 1);
    ORI = ORDER.map((k) => [(-THEMES[k].lon + 22) * D2R, (THEMES[k].lat * 0.8 - 8) * D2R]);
    ANCH = ORDER.map((k) => { const th = THEMES[k], cl = Math.cos(th.lat * D2R); return [cl * Math.sin(th.lon * D2R) * R * 1.12, Math.sin(th.lat * D2R) * R * 1.12, cl * Math.cos(th.lon * D2R) * R * 1.12]; });
  }
  // 지구 몸체(가림 구 · 경위선 · 그림자) — 입자 지구와 같이 돈다
  const gG = new THREE.Group(); scene.add(gG); gG.position.copy(C); gG.visible = false;
  const body = new THREE.Mesh(new THREE.SphereGeometry(R * 0.994, 96, 64), new THREE.ShaderMaterial({ transparent: true, uniforms: { uA: { value: 0 } },
    vertexShader: 'varying vec3 vN, vV; void main(){ vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position, 1.); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }',
    fragmentShader: `uniform float uA; varying vec3 vN, vV; void main(){ float l = clamp(dot(vN, normalize(vec3(-.5, .6, .7))), 0., 1.), fr = pow(1. - clamp(dot(vN, vV), 0., 1.), 2.5);
      vec3 c = mix(${DK ? 'vec3(.055,.08,.14), vec3(.11,.15,.25)' : 'vec3(.90,.92,.97), vec3(.995,.997,1.)'}, l); c = mix(c, ${DK ? 'vec3(.40,.36,.95), fr * .6' : 'vec3(.62,.6,1.), fr * .5'}); gl_FragColor = vec4(c, uA); }` }));   // 다크: 어두운 남색 몸체(빛 받는 쪽이 조금 밝게), 가장자리는 보라 빛
  body.renderOrder = -2; gG.add(body);
  { const g = []; for (let la = -75; la <= 75; la += 15) for (let lo = 0; lo < 360; lo += 3) { const a = U3(la, lo), b = U3(la, lo + 3); g.push(a.x, a.y, a.z, b.x, b.y, b.z); }
    for (let lo = 0; lo < 360; lo += 15) for (let la = -87; la < 87; la += 3) { const a = U3(la, lo), b = U3(la + 3, lo); g.push(a.x, a.y, a.z, b.x, b.y, b.z); }
    const lg = new THREE.BufferGeometry(); lg.setAttribute('position', new THREE.Float32BufferAttribute(g, 3)); lg.scale(R * 1.001, R * 1.001, R * 1.001);
    var grat = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: DK ? 0x8a7dff : 0x533afd, transparent: true, opacity: 0 })); grat.renderOrder = -1; gG.add(grat); }
  // 워드마크 'DELFONA'(stage 2): 글자 점 92% + 주변에 옅게 떠도는 점 8%
  let WM = false; document.fonts.load('400 200px Michroma').catch(() => {});   // 헤더 로고와 같은 글꼴
  // 점이 다 모인 마지막에는 같은 자리 · 같은 크기의 일반 글자로 바뀐다(2026-10-26 운영자). 점과 똑같이 그리도록 textPoints 와 같은 글꼴 · 자간 · 기준선
  const WFONT = '400 200px Michroma', WSP = 48;
  // 캔버스로 그린 글자는 아이폰에서 살짝 흐렸다(운영자) → 헤더 로고처럼 진짜 글자(웹 텍스트). 글자 폭 · 기준선을 한 번 재서 점 글자와 같은 자리 · 크기에 맞춘다
  const wcv = document.createElement('div'); wcv.className = 'wmx'; wcv.setAttribute('aria-hidden', 'true'); wcv.innerHTML = '<span>DELFONA</span><i></i>'; lay.appendChild(wcv);
  wcv.style.setProperty('--wm0', tmp.copy(COL.ink).getStyle()); wcv.style.setProperty('--wm2', tmp.copy(COL.ink).lerp(COL.ind, 0.65).getStyle());   // 점은 겹쳐 보여 더 진하다 — 글자는 0.8 대신 0.65 로 맞춤
  let WG = null, WR = null;   // 글자 크기 100px 일 때 폭(끝 자간 뺀 것) · 위 끝에서 기준선까지
  function wordRef() { if (WR) return WR; wcv.style.fontSize = '100px'; const sp = wcv.firstChild, pr = wcv.lastChild; WR = { adv: sp.getBoundingClientRect().width - 24, base: pr.offsetTop }; return WR; }
  function buildWord() { WM = true;
    const pts = textPoints('DELFONA', { font: WFONT, spacing: WSP + 'px', hgt: 1, step: mob ? 3 : 2 }),   // 헤더 로고 글자: Michroma 대문자, 자간 .24em
      M = pts.length, wid = mob ? 6.6 : 12.8, sc = wid / pts.W, cy = mob ? 0.95 : 0.35;
    { const g = document.createElement('canvas').getContext('2d'); g.font = WFONT; if ('letterSpacing' in g) g.letterSpacing = WSP + 'px'; const mm = g.measureText('DELFONA');
      const asc = mm.actualBoundingBoxAscent || 160, dsc = mm.actualBoundingBoxDescent || 40, pad = Math.ceil(200 * 0.12), W = Math.ceil(mm.width) + pad * 2, H = Math.ceil(asc + dsc) + pad * 2, s = wid / W;
      // 점 글자(월드): 글자 폭 = (재단 폭 - 끝 자간) · 기준선 = 캔버스 가운데에서 (pad + asc - H/2) 아래
      WG = { adv: (mm.width - WSP) * s, base: cy - (pad + asc - H / 2) * s, cy }; }
    m.set(2, (i, o) => { const dust = i % 13 === 0;
      if (dust) { const a = Math.random() * 6.283, r = (mob ? 3.2 : 6.5) * (0.6 + Math.random() * 0.8); o[0] = Math.cos(a) * r; o[1] = cy + Math.sin(a) * r * 0.45; o[2] = rnd(2); tmp.copy(COL.lt); o[6] = 0.16; }
      else { const p = pts[i % M], f = p.x / pts.W + 0.5; o[0] = p.x * sc + rnd(0.006); o[1] = p.y * sc + cy + rnd(0.006); o[2] = rnd(0.08); tmp.copy(COL.ink).lerp(COL.ind, clamp(f * 1.25 - 0.15) * 0.8); o[6] = 0.95; }
      o[3] = tmp.r; o[4] = tmp.g; o[5] = tmp.b; return o; });
  }
  // 모션용 계산 도우미
  const tA = new THREE.Vector3(), tB = new THREE.Vector3(), q3 = new THREE.Vector3();
  const tangent = (c) => { tA.set(0, 1, 0).cross(c).normalize(); if (tA.lengthSq() < 1e-6) tA.set(1, 0, 0); tB.copy(c).cross(tA).normalize(); };
  const onSphere = (c, d, th, r, out) => { tangent(c); const sd = Math.sin(d), cd = Math.cos(d); out.set(c.x * cd + (tA.x * Math.cos(th) + tB.x * Math.sin(th)) * sd, c.y * cd + (tA.y * Math.cos(th) + tB.y * Math.sin(th)) * sd, c.z * cd + (tA.z * Math.cos(th) + tB.z * Math.sin(th)) * sd).multiplyScalar(r); return out; };
  const slerpU = (a, b, s, out) => { const dd = clamp(a.dot(b), -1, 1), w = Math.acos(dd), sw = Math.sin(w) || 1; return out.set(0, 0, 0).addScaledVector(a, Math.sin((1 - s) * w) / sw).addScaledVector(b, Math.sin(s * w) / sw); };
  // 테마별 실제 소식(나이 h, 판정, 세기) — 레이더·은하·꽃에서 점 하나 = 소식 하나
  const stories = () => TH.themes.map((t) => t.pts);
  function buildRadar() {   // 레이더 다이얼: 바닥에 누운 원판. 네 사분면 = 테마. 가운데 = 지금, 바깥 = 24시간 전. 스윕이 돈다
    const Rd = R * (mob ? 1.2 : 1.02); let i = 0; const S = stories(), qa = (j) => j * Math.PI / 2 + Math.PI / 4;
    const nRing = Math.floor(N * 0.3), nGrid = Math.floor(N * 0.12), nSweep = Math.floor(N * 0.1);
    while (i < nRing) { const ring = 1 + (i % 4), a = Math.random() * 6.283, r = Rd * ring / 4 + rnd(0.012); setP(i++, Math.cos(a) * r, 0, Math.sin(a) * r, ring === 4 ? COL.ink : COL.navy, ring === 4 ? 0.85 : 0.4, 0); }
    while (i < nRing + nGrid) { const a = (i % 4) * Math.PI / 2, r = Math.random() * Rd; setP(i++, Math.cos(a) * r, 0, Math.sin(a) * r, COL.navy, 0.35, 0); }
    while (i < nRing + nGrid + nSweep) { const a = -Math.pow(Math.random(), 1.8) * 0.9, r = Math.sqrt(Math.random()) * Rd; setP(i++, a, 0, r, COL.ind, 0.55, 2, -a / 0.9); }
    const tot = S.reduce((n, a) => n + a.length, 0), per = Math.max(4, Math.floor((N - i - N * 0.08) / Math.max(1, tot)));
    S.forEach((pts, j) => pts.forEach(([h, v, st]) => { const a = qa(j) + rnd(0.62), r = Rd * (0.06 + 0.92 * Math.min(1, h / 24)), sz = 0.03 + st * 0.025;
      for (let q = 0; q < per && i < N; q++) { const c = vC(v); setP(i++, Math.cos(a) * r + rnd(sz), rnd(0.03) + Math.random() * 0.08 * st, Math.sin(a) * r + rnd(sz), c, v === '중립' ? 0.5 : 0.95, 3 + j); } }));
    while (i < N) { const a = Math.random() * 6.283, r = Math.sqrt(Math.random()) * Rd; setP(i++, Math.cos(a) * r, rnd(0.01), Math.sin(a) * r, COL.lt, 0.18, 1); }
    ORI = ORDER.map((_, j) => [qa(j) - Math.PI / 2 + 0.15, 58 * D2R]);   // 사분면 j가 화면 아래쪽(앞)으로
    ANCH = ORDER.map((_, j) => [Math.cos(qa(j)) * Rd * 1.12, 0.3, Math.sin(qa(j)) * Rd * 1.12]);
  }
  function buildCube() {   // 데이터 큐브: 옆면 네 개 = 테마. 면마다 그 테마의 24시간 막대그래프(시간별 소식 수, 색 = 호재·악재)
    const A = R * (mob ? 0.66 : 0.6); let i = 0; const S = stories();
    const nEdge = Math.floor(N * 0.22); const E = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
    while (i < nEdge) { const e = i % 12, t = Math.random() * 2 - 1; let x, y, z; if (e < 4) { [x, z] = E[e]; y = t; } else if (e < 8) { const [a, b] = E[e - 4], [c, d] = E[(e - 3) % 4]; y = -1; x = a + (c - a) * (t + 1) / 2; z = b + (d - b) * (t + 1) / 2; } else { const [a, b] = E[e - 8], [c, d] = E[(e - 7) % 4]; y = 1; x = a + (c - a) * (t + 1) / 2; z = b + (d - b) * (t + 1) / 2; }
      setP(i++, x * A, y * A, z * A, COL.ink, 0.9, 0); }
    // 면 j: 바깥 법선 방향 = 각도 j*90°
    const face = (j, u, v) => { const ang = j * Math.PI / 2, nx = Math.sin(ang), nz = Math.cos(ang), tx = Math.cos(ang), tz = -Math.sin(ang); return [nx * A + tx * u * A, v * A, nz * A + tz * u * A]; };
    const per = Math.floor((N - i - N * 0.12) / 4);
    S.forEach((pts, j) => { const bins = new Array(24).fill(0).map(() => ({ n: 0, u: 0, d: 0 })); pts.forEach(([h, v]) => { const b = bins[Math.min(23, Math.floor(24 - h))] || bins[0]; b.n++; if (v === '호재') b.u++; if (v === '악재') b.d++; });
      const mx = Math.max(1, ...bins.map((b) => b.n));
      for (let q = 0; q < per && i < N; q++) { const bi = q % 24, b = bins[bi], hh = b.n / mx, u = -0.88 + (bi + 0.15 + Math.random() * 0.7) / 24 * 1.76, v = -0.88 + Math.random() * hh * 1.7;
        const pu = (v + 0.88) / Math.max(0.01, hh * 1.7), c = b.n ? (pu < b.u / b.n ? COL.up : pu < (b.u + b.d) / b.n ? COL.dn : COL.gray) : COL.gray; const p = face(j, u, v); setP(i++, p[0], p[1], p[2], c, b.n ? 0.95 : 0.2, 3 + j); } });
    while (i < N) { const j = (Math.random() * 6) | 0, u = Math.random() * 2 - 1, v = Math.random() * 2 - 1, p = j < 4 ? face(j, u, v) : [u * A, (j === 4 ? 1 : -1) * A, v * A]; setP(i++, p[0], p[1], p[2], COL.lt, 0.16, 1); }
    ORI = ORDER.map((_, j) => [-j * Math.PI / 2 + 0.38, 16 * D2R]);
    ANCH = ORDER.map((_, j) => { const p = face(j, 0, 1.25); return p; });
  }
  function buildGalaxy() {   // 뉴스 은하: 팔 네 개 = 테마. 가운데 = 지금, 바깥으로 갈수록 오래된 소식. 팔은 천천히 돈다
    const Rg = R * (mob ? 1.25 : 1.08); let i = 0; const S = stories(), arm = (j, r) => j * Math.PI / 2 + r / Rg * 3.4;
    const nCore = Math.floor(N * 0.12), nDust = Math.floor(N * 0.3);
    while (i < nCore) { const r = Math.pow(Math.random(), 2.2) * Rg * 0.22, a = Math.random() * 6.283; tmp.copy(COL.ind).lerp(COL.lt, Math.random()); setP(i++, Math.cos(a) * r, rnd(0.18) * (1 - r / Rg * 3), Math.sin(a) * r, tmp, 0.9, 2); }
    while (i < nCore + nDust) { const j = i % 4, r = Rg * (0.15 + Math.pow(Math.random(), 0.8) * 0.85), a = arm(j, r) + rnd(0.32 * (0.4 + r / Rg)); tmp.copy(COL.navy).lerp(COL.ind, Math.random() * 0.5); setP(i++, Math.cos(a) * r, rnd(0.06), Math.sin(a) * r, tmp, 0.35, 0); }
    const tot = S.reduce((n, a) => n + a.length, 0), per = Math.max(4, Math.floor((N - i - N * 0.06) / Math.max(1, tot)));
    S.forEach((pts, j) => pts.forEach(([h, v, st]) => { const r = Rg * (0.18 + 0.8 * Math.min(1, h / 24)), a = arm(j, r) + rnd(0.13), sz = 0.03 + st * 0.03;
      for (let q = 0; q < per && i < N; q++) setP(i++, Math.cos(a) * r + rnd(sz), rnd(0.05), Math.sin(a) * r + rnd(sz), vC(v), v === '중립' ? 0.5 : 0.95, 3 + j); }));
    while (i < N) { const r = Math.random() * Rg * 1.1, a = Math.random() * 6.283; setP(i++, Math.cos(a) * r, rnd(0.1), Math.sin(a) * r, COL.lt, 0.14, 1); }
    ORI = ORDER.map((_, j) => [-(j * Math.PI / 2 + 0.5 * 3.4 / 1) + Math.PI / 2, 52 * D2R]);
    ANCH = ORDER.map((_, j) => { const r = Rg * 0.62, a = arm(j, r); return [Math.cos(a) * r, 0.45, Math.sin(a) * r]; });
  }
  function buildBloom() {   // 꽃: 꽃잎 네 장 = 테마. 꽃잎 길이 = 소식 수, 꽃잎 위 점 = 실제 소식(가운데 = 지금). 가운데엔 둥근 씨앗
    let i = 0; const S = stories(), mx = Math.max(...TH.themes.map((t) => t.n)), Lp = (j) => R * (mob ? 0.62 + 0.62 * Math.sqrt(TH.themes[j].n / mx) : 0.5 + 0.55 * Math.sqrt(TH.themes[j].n / mx));
    const petal = (j, s, w) => { const ang = j * Math.PI / 2 + Math.PI / 4, L = Lp(j), r = s * L, half = Math.sin(Math.PI * Math.min(1, s * 1.05)) * L * 0.34 * (1 - s * 0.35), y = Math.pow(s, 2) * L * 0.42;
      const ox = w * half, ca = Math.cos(ang), sa = Math.sin(ang); return [ca * r - sa * ox, y, sa * r + ca * ox]; };
    const nCore = Math.floor(N * 0.1), nEdge = Math.floor(N * 0.26), nFill = Math.floor(N * 0.22);
    while (i < nCore) { const u = Math.random() * 2 - 1, th = Math.random() * 6.283, s2 = Math.sqrt(1 - u * u), r = R * 0.28; tmp.copy(COL.ind).lerp(COL.lt, Math.random() * 0.5); setP(i++, s2 * Math.cos(th) * r, u * r * 0.7 + r * 0.2, s2 * Math.sin(th) * r, tmp, 0.85, 2); }
    while (i < nCore + nEdge) { const j = i % 4, s = Math.random(), p = petal(j, s, Math.random() < 0.5 ? -1 : 1); setP(i++, p[0], p[1], p[2], COL.ink, 0.85, 0); }
    while (i < nCore + nEdge + nFill) { const j = i % 4, s = Math.random(), p = petal(j, s, rnd(1)); tmp.copy(COL.navy).lerp(COL.ind, 0.5 * Math.random()); setP(i++, p[0], p[1], p[2], tmp, 0.25, 0); }
    const tot = S.reduce((n, a) => n + a.length, 0), per = Math.max(4, Math.floor((N - i) / Math.max(1, tot)));
    S.forEach((pts, j) => pts.forEach(([h, v, st]) => { const s0 = 0.12 + 0.85 * Math.min(1, h / 24), w0 = rnd(0.8);
      for (let q = 0; q < per && i < N; q++) { const p = petal(j, s0 + rnd(0.012 * st), w0 + rnd(0.05 * st)); setP(i++, p[0], p[1] + 0.02, p[2], vC(v), v === '중립' ? 0.5 : 0.95, 3 + j); } }));
    while (i < N) setP(i++, 0, 0, 0, COL.lt, 0, 1);
    ORI = ORDER.map((_, j) => [-(j * Math.PI / 2 + Math.PI / 4) - Math.PI / 2 + 0.2, 48 * D2R]);
    ANCH = ORDER.map((_, j) => petal(j, 1.08, 0));
  }
  const build = () => { if (SH === 'globe') { const img = new Image(); img.src = new URL('./land.png', import.meta.url).href;
      img.onload = () => { const cv = document.createElement('canvas'); cv.width = img.width; cv.height = img.height; const g = cv.getContext('2d'); g.drawImage(img, 0, 0); buildGlobe(g.getImageData(0, 0, cv.width, cv.height).data, cv.width, cv.height); ready = true; }; }
    else { ({ radar: buildRadar, cube: buildCube, galaxy: buildGalaxy, bloom: buildBloom }[SH] || buildRadar)(); ready = true; } };
  // ---- 글 ----
  const box = document.createElement('div'); box.className = 'glx'; lay.appendChild(box);
  const pins = ORDER.map(() => { const e = document.createElement('div'); e.className = 'glpin'; lay.appendChild(e); return e; });
  const css = document.createElement('style'); css.textContent = `
  .glx{position:absolute;left:0;top:0;width:min(480px,38vw);opacity:0;color:var(--ink)}
  .glx .k{font-family:var(--mono);font-size:11.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--primary)}
  .glx h2{margin-top:10px;font-size:clamp(30px,3.4vw,50px);font-weight:300;letter-spacing:-.045em;line-height:1.05}:lang(ko) .glx h2{font-weight:600;letter-spacing:-.04em;line-height:1.15}
  .wmx{position:absolute;left:0;top:0;opacity:0;pointer-events:none;white-space:nowrap;line-height:1;font-family:Michroma,var(--sans);font-weight:400;letter-spacing:.24em}.wmx span{background:linear-gradient(90deg,var(--wm0) 12%,var(--wm2) 92%);-webkit-background-clip:text;background-clip:text;color:transparent;-webkit-text-fill-color:transparent}.wmx i{display:inline-block;width:0;height:0;vertical-align:baseline}.glx .hl{margin-top:14px;padding-left:12px;border-left:2px solid var(--primary);font-size:16px;line-height:1.5;color:var(--ink2)}.glx .hl small{display:block;font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}
  .glx ol{list-style:none;padding:0;margin-top:20px}.glx li{padding:13px 0;border-top:1px solid var(--line);color:#8a96aa;transition:color 300ms ease}
  .glx li .h{display:flex;align-items:baseline;gap:10px}.glx li .h b{font-size:19px;font-weight:500;letter-spacing:-.02em}.glx li .h span{font-family:var(--mono);font-size:11.5px}
  .glx li .h i{margin-left:auto;font-style:normal;font-family:var(--mono);font-size:11px;color:var(--mute)}
  .glx li p:not(.h){max-height:0;overflow:hidden;opacity:0;font-size:15px;line-height:1.55;color:var(--ink2);transition:max-height 450ms var(--ease),opacity 300ms ease,margin 300ms ease}
  .glx li.on{color:var(--ink)}.glx li.on p:not(.h){max-height:300px;opacity:1;margin-top:8px}.glx li.on .h b{font-size:23px;font-weight:600}
  .glx .fn{margin-top:14px;font-size:11.5px;color:var(--mute)}
  .glpin{position:absolute;left:0;top:0;opacity:0;transform:translate(-50%,-100%);white-space:nowrap;padding:5px 10px 6px;border-radius:99px;background:#0d253d;color:#fff;font-size:12px;font-weight:600}
  .glpin span{font-family:var(--mono);font-weight:500;color:#a9b3ff;margin-left:6px}
  :root[data-theme="dark"] .glpin{background:#e8eef6;color:#0b1320} :root[data-theme="dark"] .glpin span{color:#4b3fd1}
  @media(max-width:899px){.glx{width:auto}.glx h2{font-size:23px}.glx .hl{display:none}.glx ol{margin-top:12px}.glx li{display:none;border:0;padding:0}.glx li.on{display:block}.glx li.on p:not(.h){max-height:340px;font-size:14px;line-height:1.55}.glx li .h b{font-size:20px}.glx .fn{display:none}}`;
  document.head.appendChild(css);
  let TH = null, act = -1;
  const hm = (s) => new Date(s * 1000).toLocaleTimeString(L() ? 'ko-KR' : 'en-GB', { hour: '2-digit', minute: '2-digit' });
  const fill = () => { if (!TH) return; const l = L(), hl = TH.headline[l ? 'ko' : 'en'];
    box.innerHTML = `<p class="k">${TH.bf ? T(`AI briefing · updated ${hm(TH.bf)}`, `AI 브리핑 · ${hm(TH.bf)} 기준`) : `${T('AI world brief · last 24h', 'AI 세계 요약 · 지난 24시간')} · ${TH.total}${T(' stories', '건')}`}</p>
      <h2>${T('Every issue on Earth,<br>summed up by AI.', '전 세계의 이슈를,<br>AI가 한 번에 요약해요.')}</h2>
      <p class="hl"><small>${T('Today, in one line', '오늘을 한 줄로')}</small>${DFD.esc(hl)}</p>
      <ol>${TH.themes.map((t) => `<li data-k="${t.k}"><p class="h"><b>${THEMES[t.k].name[l]}</b><span><span class="up">${t.u}↑</span> <span class="down">${t.d}↓</span></span><i>${SH === 'globe' ? THEMES[t.k].city[l] + ' · ' : ''}${t.n}${T(' stories', '건')}</i></p><p>${DFD.esc(t[l ? 'ko' : 'en'] || '')}</p></li>`).join('')}</ol>
      <p class="fn">${TH.bf ? T('Written by AI from market data and judged news — an interpretation, not investment advice.', '시장 자료와 판정한 소식으로 AI가 쓴 해석이에요. 투자 조언이 아니에요.') : T('Summaries written by AI from the last 24 hours of judged news. Not investment advice.', '지난 24시간 판정한 소식을 바탕으로 AI가 요약했어요. 투자 조언이 아니에요.')}</p>`;
    pins.forEach((e, j) => { const t = TH.themes[j]; e.innerHTML = `${THEMES[t.k].name[l]}<span>${t.n}</span>`; }); act = -1; };
  const TU = window.DF_THEMES || new URL('./themes.json', import.meta.url).href, VQ = '?v=' + Math.floor(Date.now() / 6e5);
  // 브리핑으로 제목 · 분야 판독을 덮는다(언어별로, 그 칸이 비었으면 예전 글 그대로)
  const mix = (d, bf) => { if (!bf || !bf.made || !bf.ko || Date.now() / 1000 - bf.made > 48 * 3600) return d;
    ['ko', 'en'].forEach((g) => { const h = bf[g] && bf[g].headline; if (h) d.headline[g] = h; });
    // 테마 데스크 첫 문단(state, 테마 화면과 같은 글) → 없으면 분야 한 줄(s). 한 줄은 검증에 걸리면 빠져 경제 · AI가 빈칸이 되곤 했다
    d.themes.forEach((t) => ['ko', 'en'].forEach((g) => { const st = bf.desks && bf.desks[t.k] && bf.desks[t.k][g] && bf.desks[t.k][g].state, x = bf[g] && bf[g].desks && bf[g].desks[t.k];
      if (st) t[g] = st; else if (x && x.s) t[g] = x.s; }));
    d.bf = bf.made; return d; };
  Promise.all([fetch(TU + VQ).then((r) => r.json()), fetch(TU.replace(/themes\.json$/, 'briefing.json') + VQ).then((r) => (r.ok ? r.json() : null)).catch(() => null)]).then(([d, bf]) => {
    TH = mix(d, bf); TH.themes.sort((a, b) => ORDER.indexOf(a.k) - ORDER.indexOf(b.k)); fill(); DFI.onLang(fill);
    // 빛기둥 색: 그 테마의 호재·악재 비율
    const tmp = new THREE.Color(); const recolor = () => { if (!ready) return setTimeout(recolor, 100);
      for (let i = 0; i < N; i++) if (kindOf[i] >= 3) { const t = TH.themes[kindOf[i] - 3], bu = t.u / Math.max(1, t.u + t.d); tmp.copy(COL.ind).lerp(seed[i] * 1.3 < bu ? COL.up : COL.dn, 0.55 + 0.4 * seed[i]); col.set([tmp.r, tmp.g, tmp.b, 0.9 - seed[i] * 0.5], i * 4); } };
    build(); if (SH === 'globe') recolor(); }).catch((e) => console.error(e));
  // ---- 매 프레임 ----
  const camP = mob ? new THREE.Vector3(0, 0.6, 21) : new THREE.Vector3(0, 0.2, 15.5), camL = mob ? new THREE.Vector3(0, 0.6, 0) : new THREE.Vector3(0, 0, 0), v = new THREE.Vector3(), lk = new THREE.Vector3();
  let rotY = 0, rotX = 0, spin = 0, tilt = 0, lastT = 0, dtS = 0.016;
  const rot = (x, y, z, out) => { const cy = Math.cos(rotY), sy = Math.sin(rotY), cx = Math.cos(rotX), sx = Math.sin(rotX); const x1 = x * cy + z * sy, z1 = -x * sy + z * cy; out[0] = x1; out[1] = y * cx - z1 * sx; out[2] = y * sx + z1 * cx; return out; };
  const o3 = [0, 0, 0];
  return {
    update(BP, t, cam, look, hide) {
      if (BP <= 0 || !ready || !TH || !ORI) { m.points.visible = false; box.style.opacity = 0; pins.forEach((e) => (e.style.opacity = 0)); halo.material.uniforms.uA.value = 0; return 0; }
      dtS = Math.min(0.05, Math.max(0.001, t - lastT)); lastT = t; if (!this.init0) { this.init0 = true; spin = ORI[0][0] + 0.9; tilt = ORI[0][1]; }
      m.points.visible = true; const go = sm(clamp(BP / 0.26)); hide(go);
      if (!this.primed) { this.primed = true; this.sample && this.sample(m, N); }
      // 테마 진행: 0.34~0.92를 네 칸으로
      const tp = clamp((BP - 0.3) / 0.48) * 4, k = Math.min(3, Math.floor(tp)), f = sm(clamp((tp - k) / 0.35));
      const j0 = Math.max(0, k - (f < 1 ? 1 : 0)), ff = k === 0 && tp < 0.35 ? 1 : f, idle = BP < 0.3;
      const tY = idle ? ORI[0][0] + 0.9 - t * 0.05 : lerp(ORI[j0][0], ORI[k][0], ff), tX = idle ? ORI[0][1] : lerp(ORI[j0][1], ORI[k][1], ff);
      const a60 = Math.min(1, dtS * 3.2); spin += (tY - spin) * a60; tilt += (tX - tilt) * a60; rotY = spin + Math.sin(t * 0.15) * 0.02; rotX = tilt;
      const on = idle ? 0 : clamp((tp - k) * 3) * (1 - ss(0.77, 0.81, BP)), cU = CITY[k], cosR = Math.cos(22 * D2R);
      const glb = SH === 'globe';
      m.set(1, (i, o) => { const kd = kindOf[i]; let bx = base[i * 3], by = base[i * 3 + 1], bz = base[i * 3 + 2], a = col[i * 4 + 3], cr = col[i * 4], cg = col[i * 4 + 1], cb = col[i * 4 + 2];
        if (glb && kd === 0 && MV === 'lift' && on > 0) {   // 3 · 솟아오름: 도시 주변 대륙 점들이 소식의 양만큼 부풀고 호재·악재 색으로 물든다
          const dd = (bx * cU.x + by * cU.y + bz * cU.z) / R; if (dd > cosR) { const w = Math.pow((dd - cosR) / (1 - cosR), 1.2) * on, th = TH.themes[k], bu = th.u / Math.max(1, th.u + th.d), sc = 1 + w * (0.16 + 0.2 * Math.min(1, th.n / 150)) * (0.88 + 0.12 * Math.sin(t * 2.4 - dd * 60));
            bx *= sc; by *= sc; bz *= sc; tmp.setRGB(cr, cg, cb).lerp(seed[i] < bu ? COL.up : COL.dn, Math.min(1, w * 2.6 + 0.25)); cr = tmp.r; cg = tmp.g; cb = tmp.b; a = Math.min(1, a + w); } }
        if (glb && kd >= 3) { const j = kd - 3, act2 = j === k ? on : 0;
          if (act2 <= 0) a = 0;
          else if (aux[i] < 0.06) { onSphere(CITY[j], aux[i] / 0.06 * 1.1 * D2R, seed[i] * 6.283, R * 1.006, q3); a *= act2 * (0.7 + 0.3 * Math.sin(t * 5)); bx = q3.x; by = q3.y; bz = q3.z; }   // 도시 점(가운데 빛)
          else if (MV === 'ripple') {   // 1 · 파문: 도시에서 표면을 따라 동심원이 퍼진다(소나처럼)
            const ring = Math.floor(aux[i] * 4), ph = (t * 0.28 + ring / 4) % 1; onSphere(CITY[j], ph * 30 * D2R + rnd(0.0015), seed[i] * 6.283, R * 1.007, q3); bx = q3.x; by = q3.y; bz = q3.z; a = Math.min(1, a * 1.6) * act2 * Math.pow(1 - ph, 1.1) * (ph < 0.05 ? ph / 0.05 : 1); }
          else if (MV === 'arcs') {   // 2 · 모여드는 소식: 세계 도시들에서 출발한 점들이 호를 그리며 테마 도시로 모인다
            const si = Math.floor(aux[i] * 8.999), src = SRC[(si * 2 + j) % SRC.length], sp = 0.18 + (si % 4) * 0.03, s = (seed[i] + t * sp) % 1, ang = Math.acos(clamp(src.dot(CITY[j]), -1, 1));
            if (ang < 0.05) a = 0; else { slerpU(src, CITY[j], s, q3); q3.multiplyScalar(R * (1.008 + Math.sin(Math.PI * s) * ang * 0.13)); bx = q3.x; by = q3.y; bz = q3.z; a = Math.min(1, a * 1.5) * act2 * Math.min(1, s * 8) * (0.45 + 0.55 * s); } }
          else { onSphere(CITY[j], 22 * D2R, seed[i] * 6.283, R * 1.01, q3); bx = q3.x; by = q3.y; bz = q3.z; a *= act2 * 0.45 * (0.6 + 0.4 * Math.sin(t * 3 + seed[i] * 30)); }   // 솟아오름: 둘레 고리
        }
        rot(bx, by, bz, o3); let x = o3[0], y = o3[1], z = o3[2];
        if (kd === 2) { if (glb) { const ra = t * 0.06 * (0.6 + seed[i]); const rx = bx * Math.cos(ra) - bz * Math.sin(ra), rz = bx * Math.sin(ra) + bz * Math.cos(ra), tl = 0.38; x = rx; y = -rz * Math.sin(tl) + by; z = rz * Math.cos(tl); }
          else if (SH === 'radar') { const ang = bx + t * 0.9, r = bz; rot(Math.cos(ang) * r, 0, Math.sin(ang) * r, o3); x = o3[0]; y = o3[1]; z = o3[2]; a *= 1 - seed[i] * 0.9; }
          else { a *= 0.7 + 0.3 * Math.sin(t * 2 + seed[i] * 20); } }
        if (!glb && kd >= 3) { const j = kd - 3, onn = BP < 0.34 ? 0.8 : j === k ? 1 : 0.2; a *= onn; if (j === k && !idle) y += 0.06 * Math.sin(t * 3 + seed[i] * 12); }
        if (!glb && (kd === 0 || kd === 1)) a *= 0.55 + 0.45 * clamp(0.5 + z / (R * 1.5));
        if (glb && kd === 0) a *= 0.55 + 0.45 * clamp(z / R * 1.6);   // 가장자리로 갈수록 살짝 옅게(입체감)
        o[0] = C.x + x; o[1] = C.y + y; o[2] = C.z + z; o[3] = cr; o[4] = cg; o[5] = cb; o[6] = a; return o; });
      const bodyA = ss(0.85, 1, go) * (1 - ss(0.78, 0.83, BP)); gG.visible = glb && go > 0.6 && bodyA > 0.002; gG.rotation.set(rotX, rotY, 0, 'XYZ'); body.material.uniforms.uA.value = bodyA; grat.material.opacity = bodyA * 0.07;
      // 마지막: 지구를 이루던 입자가 부드럽게 흩어졌다가 'Delfona' 글자로 다시 모인다
      const fin = ss(0.8, 0.95, BP); if (fin > 0 && !WM) buildWord();
      m.U.uS.value = WM && fin > 0 ? 1 + fin : go; m.U.uBurst.value = WM && fin > 0 ? (mob ? 1.4 : 2.2) : (mob ? 5 : 8); m.U.uWob.value = fin > 0.98 ? 0.012 : 0.006; m.U.uSz.value = (mob ? 0.85 : 0.9) * (1 + fin * (mob ? 0.25 : 0.45));
      // 점 글자 → 일반 글자(끝 부분에서 겹쳐 바꾼다)
      const tx = WM && WG ? ss(0.955, 0.985, BP) : 0;
      m.U.uT.value = t; m.U.uA.value = 1 - tx;
      halo.material.uniforms.uA.value = SH === 'globe' ? ss(0.15, 0.32, BP) * (1 - ss(0.78, 0.84, BP)) : 0;
      v.copy(cam.position).lerp(camP, go); cam.position.copy(v); lk.copy(look).lerp(camL, go); cam.lookAt(lk); cam.updateMatrixWorld();
      // 일반 글자 자리: 카메라를 마지막 자리로 옮긴 뒤에 잰다(그 전에는 앞 장면 카메라라 작고 엉뚱한 곳에 그려졌다)
      if (tx > 0) { const [xa, yb] = project(cam, sec, v.set(-WG.adv / 2, WG.base, 0)), [xb] = project(cam, sec, v.set(WG.adv / 2, WG.base, 0)), R = wordRef(), fs = (xb - xa) * 100 / R.adv;
        wcv.style.fontSize = fs + 'px'; wcv.style.transform = `translate(${xa}px,${yb - R.base * fs / 100}px)`; }
      wcv.style.opacity = tx;
      // 글
      const w = sec.clientWidth, h = sec.clientHeight, show = ss(0.25, 0.31, BP) * (1 - ss(0.77, 0.81, BP));
      if (act !== k) { act = k; box.querySelectorAll('li').forEach((e, j) => e.classList.toggle('on', j === k)); }
      if (mob) { const [, yb] = project(cam, sec, v.set(0, C.y - R - 0.25, 0)); box.style.left = '20px'; box.style.right = '20px'; box.style.transform = `translate(0,${Math.min(Math.max(yb + 6, h * 0.42), h - box.offsetHeight - 70) + (1 - show) * 16}px)`; }
      else { const [xr] = project(cam, sec, v.set(C.x + R * 1.12, 0, 0)); const bw = Math.min(480, w * 0.38); const x = Math.min(Math.max(xr + 20, w * 0.52), w - bw - 40); box.style.transform = `translate(${x}px,${h / 2 - box.offsetHeight / 2 + 20 + (1 - show) * 16}px)`; }
      box.style.opacity = show;
      // 도시 이름표: 지금 테마만
      ORDER.forEach((key, j) => { rot(ANCH[j][0], ANCH[j][1], ANCH[j][2], o3);
        v.set(C.x + o3[0], C.y + o3[1], C.z + o3[2]); const [x, y, z] = project(cam, sec, v); pins[j].style.transform = `translate(${x}px,${y - 6}px) translate(-50%,-100%)`;
        pins[j].style.opacity = z < 1 && (SH !== 'globe' || o3[2] > 0) ? (j === k ? 1 : 0) * show * clamp((tp - k) * 3) : 0; });
      return go;
    },
  };
}
