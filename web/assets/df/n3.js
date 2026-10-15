// N3 · Inside one signal — H3(입자 로고) 다음 섹션.
// 실제 속보 하나를 여섯 겹 유리판으로 분해해 보여 준다: 들어옴 → 번역 → 판정 → 연결 → 교차 확인 → (맨 위) 우리가 보여 주는 카드.
// 스크롤하면 위에서 내려다본 카드 한 장이 비스듬히 기울며 층층이 벌어지고, 한 층씩 불이 켜진다. 다시 합쳐진 뒤 카메라가 물러나면 지난 24시간 실제 카드 수십 장이 펼쳐진다.
import * as THREE from 'three';
import { renderer, loop, mobile, reduce, fonts, wrap, rr, lerp, clamp, ss, KIND, SECT, SANS, KSANS, MONO, EN } from './nkit.js?v=202610151430';
import { makeFX, FX_NAMES } from './fx.js?v=202610151430';

const sec = document.getElementById('nx'), canvas = document.getElementById('nxgl');
const r = renderer(canvas), scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(32, 1, 0.1, 200);
const W = 1024, H = 640, PW = 4.0, PH = 2.5;
const L = () => DFI.lang();
const T = (en, ko) => L() === 'ko' ? ko : en;
const C = { ink: '#0d253d', ink2: '#273951', mute: '#6b7a90', line: 'rgba(13,37,61,.12)', up: '#0e9f6e', down: '#df4a3a', upS: '#e7f7f0', downS: '#fdeeec', ind: '#533afd' };
const vcol = (v) => v === '호재' ? C.up : v === '악재' ? C.down : C.mute;
const hm = (t) => { const d = new Date(t * 1000); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

// ---------- 판(plate) 그리기: 1024×640 캔버스 하나에 한 층 ----------
const LAB = [['01 · Incoming', '01 · 들어옴'], ['02 · Translated', '02 · 번역'], ['03 · Judged', '03 · 판정'], ['04 · Linked', '04 · 연결'], ['05 · Cross-checked', '05 · 교차 확인'], ['What you see', '보이는 카드']];
function frame(g, i, it, tint) {
  g.clearRect(0, 0, W, H); g.fillStyle = '#e4e8ee'; g.fillRect(0, 0, W, H);
  g.save();
  rr(g, 18, 18, W - 36, H - 36, 40); g.fillStyle = tint || 'rgba(255,255,255,.94)'; g.fill(); g.restore();
  rr(g, 18, 18, W - 36, H - 36, 40); g.lineWidth = 2; g.strokeStyle = C.line; g.stroke();
  g.font = `500 22px ${MONO}`; g.fillStyle = C.mute; g.textBaseline = 'alphabetic'; g.textAlign = 'left'; g.fillText(LAB[i][L() === 'ko' ? 1 : 0].toUpperCase(), 64, 86);
  g.textAlign = 'right'; g.fillText(hm(it.t), W - 64, 86); g.textAlign = 'left';
}
const line = (it, lang) => lang === 'ko' ? it.ko : (it.en || it.ko);
const GL = '▓▒░#%&*+=<>/\\|ABCDEFGHJKLMNPQRSTUVWXYZ0123456789';
function drawPlate(g, i, it, k = 1) {
  const ko = L() === 'ko', font = ko ? KSANS : SANS;
  if (i === 0) {   // 들어옴: 깨진 글자가 풀리며 원문 한 줄이 된다
    frame(g, 0, it); g.font = `400 34px ${MONO}`; g.fillStyle = C.ink2;
    const ls = wrap(g, line(it, L()), W - 128, 5); let n = 0; const tot = ls.join('').length;
    ls.forEach((s, j) => { let o = ''; for (const ch of s) { o += (n / tot < k || ch === ' ') ? ch : GL[(Math.random() * GL.length) | 0]; n++; } g.fillText(o, 64, 170 + j * 54); });
    g.font = `500 20px ${MONO}`; g.fillStyle = C.mute; g.fillText(T('WIRE · RECEIVED ', '속보 채널 · 수신 ') + hm(it.t) + (k < 1 ? '  ▌' : '  ✓'), 64, H - 70);
  } else if (i === 1) {   // 번역: 영어 크게, 한국어 아래
    frame(g, 1, it); g.font = `400 46px ${SANS}`; g.fillStyle = C.ink;
    const en = it.en || it.ko, a = wrap(g, en, W - 128, 3); a.forEach((s, j) => g.fillText(s, 64, 170 + j * 58));
    g.font = `500 30px ${KSANS}`; g.fillStyle = C.mute; wrap(g, it.ko, W - 128, 2).forEach((s, j) => g.fillText(s, 64, 200 + a.length * 58 + j * 42));
    g.font = `500 20px ${MONO}`; g.fillText('EN · 한국어', 64, H - 70);
  } else if (i === 2) {   // 판정: 호재/악재 큰 글씨 + 세기 1~3 + 종류
    const up = it.v === '호재'; frame(g, 2, it, up ? C.upS : C.downS);
    const s = 1 + 0.35 * Math.max(0, 1 - k) ; g.save(); g.translate(64, 300); g.scale(s, s); g.font = `300 150px ${font}`; g.fillStyle = vcol(it.v); g.globalAlpha = clamp(k * 1.6); g.fillText(DFI.v(it.v), 0, 0); g.restore();
    g.font = `500 22px ${MONO}`; g.fillStyle = C.mute; g.fillText(T('STRENGTH', '세기'), 64, 400);
    for (let b = 0; b < 3; b++) { rr(g, 64 + b * 92, 420, 80, 18, 9); g.fillStyle = b < (it.s || 1) && b / 3 < k ? vcol(it.v) : 'rgba(13,37,61,.1)'; g.fill(); }
    g.font = `500 22px ${MONO}`; g.fillStyle = C.mute; g.fillText(`${it.s || 1} / 3`, 370, 437);
    g.font = `500 30px ${font}`; g.fillStyle = C.ink2; g.fillText((KIND[L()] || KIND.en)[it.kind] || '', 64, 510);
    g.font = `500 18px ${MONO}`; g.fillStyle = C.mute; g.fillText(T('AI JUDGMENT · NOT INVESTMENT ADVICE', 'AI 판정 · 투자 조언 아님'), 64, H - 70);
  } else if (i === 3) {   // 연결: 코인·섹터 칩, 시장 전체 영향
    frame(g, 3, it); let x = 64, y = 150;
    const chip = (txt, bg, fg, big) => { g.font = `${big ? 600 : 500} ${big ? 44 : 32}px ${big ? SANS : font}`; const w = g.measureText(txt).width + (big ? 56 : 44), h = big ? 84 : 64;
      if (x + w > W - 64) { x = 64; y += h + 18; } rr(g, x, y, w, h, h / 2); g.fillStyle = bg; g.fill(); g.fillStyle = fg; g.fillText(txt, x + (big ? 28 : 22), y + h / 2 + (big ? 15 : 11)); x += w + 14; };
    const coins = it.coins.slice(0, 4), secs = it.sectors.slice(0, 3);
    coins.forEach((c) => chip(c, '#0d253d', '#fff', true)); if (coins.length) { x = 64; y += 102; }
    secs.forEach((s) => chip((SECT[s] || [s, s])[ko ? 1 : 0], '#eef0ff', C.ind));
    if (!coins.length && !secs.length) chip(T('Macro · all markets', '거시 · 시장 전체'), '#eef0ff', C.ind);
    g.font = `500 22px ${MONO}`; g.fillStyle = it.mw ? C.ind : C.mute; g.fillText(it.mw ? T('● MARKET-WIDE IMPACT', '● 시장 전체에 영향') : T('○ SPECIFIC ASSETS', '○ 특정 자산'), 64, H - 70);
  } else if (i === 4) {   // 교차 확인: 보도한 곳 수만큼 점, 하나로 묶임
    frame(g, 4, it); const n = Math.max(1, it.n || 1), cx = W / 2, cy = 300;
    g.strokeStyle = 'rgba(83,58,253,.35)'; g.lineWidth = 3;
    const pts = [...Array(Math.max(n, 3))].map((_, j, a) => [cx + Math.cos(j / a.length * 6.283 - 1.57) * 170, cy + Math.sin(j / a.length * 6.283 - 1.57) * 110]);
    pts.forEach(([px, py], j) => { const on = j < n && j / n < k * 1.2; if (on) { g.beginPath(); g.moveTo(px, py); g.lineTo(cx, cy); g.stroke(); }
      g.beginPath(); g.arc(px, py, 22, 0, 6.283); g.fillStyle = on ? C.ind : 'rgba(13,37,61,.08)'; g.fill(); });
    g.beginPath(); g.arc(cx, cy, 34, 0, 6.283); g.fillStyle = C.ink; g.fill();
    g.font = `400 52px ${font}`; g.fillStyle = C.ink; g.textAlign = 'center'; g.fillText(DFI.outlets(n), cx, 500); g.textAlign = 'left';
    g.font = `500 20px ${MONO}`; g.fillStyle = C.mute; g.fillText(T('SAME STORY → ONE CARD', '같은 소식 → 카드 하나'), 64, H - 70);
  } else summary(g, it, 0, 0, W, H, true, true);
}
// 맨 위 판 = 실제 화면에 보이는 카드 (아래 '벽'의 카드도 같은 모양)
function summary(g, it, x0, y0, w, h, bg, full) {
  const ko = L() === 'ko', font = ko ? KSANS : SANS; g.save(); g.translate(x0, y0); g.scale(w / W, h / H);
  if (bg !== false) { g.clearRect(0, 0, W, H); if (full) { g.fillStyle = '#0d1f36'; g.fillRect(0, 0, W, H); } g.save(); rr(g, 18, 18, W - 36, H - 36, 40); g.fillStyle = '#0d1f36'; g.fill(); g.restore(); }
  const up = it.v === '호재', dn = it.v === '악재';
  g.font = `600 24px ${font}`; const vt = DFI.v(it.v), vw = g.measureText(vt).width + 40; rr(g, 64, 62, vw, 46, 23); g.fillStyle = up ? 'rgba(46,214,150,.16)' : dn ? 'rgba(255,120,100,.16)' : 'rgba(255,255,255,.1)'; g.fill();
  g.fillStyle = up ? '#5ee6b4' : dn ? '#ff9d8e' : '#c4cede'; g.fillText(vt, 84, 94);
  g.font = `500 22px ${MONO}`; g.fillStyle = 'rgba(255,255,255,.55)'; g.textAlign = 'right'; g.fillText(hm(it.t), W - 64, 94); g.textAlign = 'left';
  g.font = `${ko ? 500 : 400} 50px ${font}`; g.fillStyle = '#fff'; wrap(g, line(it, L()), W - 128, 4).forEach((s, j) => g.fillText(s, 64, 200 + j * 64));
  g.font = `500 24px ${MONO}`; g.fillStyle = 'rgba(255,255,255,.6)';
  const tags = [...it.coins.slice(0, 3), ...it.sectors.slice(0, 2).map((s) => (SECT[s] || [s, s])[ko ? 1 : 0])].join(' · ');
  g.fillText([tags, DFI.outlets(it.n || 1)].filter(Boolean).join('   ·   '), 64, H - 74);
  for (let b = 0; b < 3; b++) { rr(g, W - 64 - (3 - b) * 34, H - 92, 26, 12, 6); g.fillStyle = b < (it.s || 1) ? (up ? '#5ee6b4' : dn ? '#ff9d8e' : '#c4cede') : 'rgba(255,255,255,.14)'; g.fill(); }
  g.restore();
}

// ---------- 장면 ----------
const root = new THREE.Group(); scene.add(root);
const geo = new THREE.PlaneGeometry(PW, PH); geo.rotateX(-Math.PI / 2);
// 판 모양: 투명 잘라내기 대신 실제 둥근 사각형 도형(가장자리가 화면 안티에일리어싱을 받아 매끈하다).
// 캔버스 안 카드 영역(가장자리 18px, 모서리 40px)과 정확히 같은 크기, UV는 판 전체 기준
const pgeo = (() => { const px = PW / W, m = 18 * px, rad = 40 * px, w = PW / 2 - m, h = PH / 2 - m, sh = new THREE.Shape();
  sh.moveTo(-w + rad, -h); sh.lineTo(w - rad, -h); sh.quadraticCurveTo(w, -h, w, -h + rad); sh.lineTo(w, h - rad); sh.quadraticCurveTo(w, h, w - rad, h);
  sh.lineTo(-w + rad, h); sh.quadraticCurveTo(-w, h, -w, h - rad); sh.lineTo(-w, -h + rad); sh.quadraticCurveTo(-w, -h, -w + rad, -h);
  const g = new THREE.ShapeGeometry(sh, 16), pos = g.getAttribute('position'), uv = g.getAttribute('uv');
  for (let i = 0; i < pos.count; i++) uv.setXY(i, pos.getX(i) / PW + 0.5, pos.getY(i) / PH + 0.5);
  g.rotateX(-Math.PI / 2); return g; })();
// 도착 모션 후보(?fx=1~5)
const FXK = 0;   // 도착 효과 없음(차분하게)
const FX = makeFX(FXK, { scene, PW, PH, mobile: mobile(), dpr: Math.min(devicePixelRatio || 1, 2) });
// 판 아래 그림자(흐린 둥근 사각형) — 위 판이 아래 판에 드리우는 그림자
const SHT = (() => { const c = document.createElement('canvas'); c.width = 256; c.height = 160; const g = c.getContext('2d'); g.filter = 'blur(14px)'; g.fillStyle = 'rgba(13,37,61,.55)'; g.beginPath(); g.roundRect(30, 30, 196, 100, 18); g.fill(); const t = new THREE.CanvasTexture(c); return t; })();
// 빛 훑기: 기울어진 흰 띠가 판 위를 한 번 지나간다
const SHEEN = (() => { const c = document.createElement('canvas'); c.width = 512; c.height = 320; const g = c.getContext('2d'); const gr = g.createLinearGradient(0, 0, 512, 0);
  gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(0.4, 'rgba(255,255,255,0)'); gr.addColorStop(0.5, 'rgba(255,255,255,.5)'); gr.addColorStop(0.6, 'rgba(255,255,255,0)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.setTransform(1, 0, -0.45, 1, 72, 0); g.fillStyle = gr; g.fillRect(-200, 0, 912, 320); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
// 빛 띠가 판 모양(둥근 모서리) 밖으로 새지 않게 가리는 마스크
const MASK = (() => { const c = document.createElement('canvas'); c.width = 512; c.height = 320; const g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 512, 320); g.fillStyle = '#fff'; g.beginPath(); g.roundRect(9, 9, 494, 302, 20); g.fill(); return new THREE.CanvasTexture(c); })();
// 판 글자 선명도: 데스크톱은 1.75배, 모바일은 1.25배 해상도로 그린다(좌표는 그대로 1024×640 기준)
const TS = mobile() ? 1.25 : 1.75, hi = (g) => { g.setTransform(TS, 0, 0, TS, 0, 0); return g; };
const plates = [...Array(6)].map((_, i) => { const c = document.createElement('canvas'); c.width = W * TS; c.height = H * TS; const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = r.capabilities.getMaxAnisotropy();
  const mat = new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }), U = FX.install(mat);
  const m = new THREE.Mesh(pgeo, mat); root.add(m);
  const sh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: SHT, transparent: true, depthWrite: false, toneMapped: false, opacity: 0 })); sh.scale.set(1.12, 1, 1.18); root.add(sh);
  // 판 테두리 빛(활성 층)
  const e = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(PW - 0.06, 0.001, PH - 0.06)), new THREE.LineBasicMaterial({ color: 0x533afd, transparent: true, opacity: 0 })); m.add(e);
  const st = SHEEN.clone(); st.needsUpdate = true; const sn = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: st, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0, toneMapped: false, alphaMap: MASK })); sn.position.y = 0.004; m.add(sn);
  return { m, sh, sn, U, c, g: c.getContext('2d'), tex, e, k: -1, x: 0, v: 0, f: 0, fv: 0, ly: 0, lv: 0, tgt: 0, t0: -1, sw: -9, px: 0, pf: 0 }; });
// 층과 층 사이 세로 기둥(분해도 느낌)
const posts = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineDashedMaterial({ color: 0x8a96aa, dashSize: 0.06, gapSize: 0.06, transparent: true, opacity: 0 }));
{ const p = []; [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(([a, b]) => p.push(a * (PW / 2 - 0.05), 0, b * (PH / 2 - 0.05), a * (PW / 2 - 0.05), 1, b * (PH / 2 - 0.05))); posts.geometry.setAttribute('position', new THREE.Float32BufferAttribute(p, 3)); posts.computeLineDistances(); }
root.add(posts);

// 입자: 사방에서 맨 아래 판으로 빨려 들어오는 소식들(H3의 입자 언어를 잇는다)
const NP = mobile() ? 1400 : 2600, pS = new Float32Array(NP * 3), pE = new Float32Array(NP * 3), pR = new Float32Array(NP);
for (let i = 0; i < NP; i++) { const a = Math.random() * 6.283, b = Math.acos(Math.random() * 2 - 1), rad = 9 + Math.random() * 8;
  pS.set([Math.sin(b) * Math.cos(a) * rad, Math.cos(b) * rad * 0.6, Math.sin(b) * Math.sin(a) * rad], i * 3);
  pE.set([(Math.random() - 0.5) * PW * 0.9, 0, (Math.random() - 0.5) * PH * 0.9], i * 3); pR[i] = Math.random(); }
const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pS.slice(), 3)); pg.setAttribute('aS', new THREE.BufferAttribute(pS, 3)); pg.setAttribute('aE', new THREE.BufferAttribute(pE, 3)); pg.setAttribute('aR', new THREE.BufferAttribute(pR, 1));
const PU = { uT: { value: 0 }, uF: { value: 0 }, uY: { value: 0 } };
const parts = new THREE.Points(pg, new THREE.ShaderMaterial({ uniforms: PU, transparent: true, depthWrite: false, vertexShader: `attribute vec3 aS, aE; attribute float aR; uniform float uT, uF, uY; varying float vA; varying float vR;
  void main(){ float k = fract(uT*.18 + aR); float e = k*k*(3.-2.*k); vec3 p = mix(aS, aE + vec3(0., uY, 0.), e); float sw = (1.-e)*2.2*(aR-.5); p.xz = mat2(cos(sw),-sin(sw),sin(sw),cos(sw))*p.xz;
    vA = uF * smoothstep(0., .15, k) * (1. - smoothstep(.85, 1., k)); vR = aR; vec4 mv = modelViewMatrix*vec4(p,1.); gl_Position = projectionMatrix*mv; gl_PointSize = (1.4 + aR*1.6) * (14. / -mv.z) * ${Math.min(devicePixelRatio || 1, 2).toFixed(1)}; }`,
  fragmentShader: `varying float vA; varying float vR; void main(){ vec2 c = gl_PointCoord-.5; if(dot(c,c)>.25) discard; vec3 col = mix(vec3(.42,.42,.97), vec3(.11,.21,.34), step(.55, vR)); gl_FragColor = vec4(col, vA*.8); }` }));
root.add(parts);

// 바닥: 점 격자(분해도의 작업대 느낌), 가운데에서 바깥으로 옅어진다
const FU = { uA: { value: 0 } };
const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40).rotateX(-Math.PI / 2), new THREE.ShaderMaterial({ uniforms: FU, transparent: true, depthWrite: false, vertexShader: 'varying vec2 vP; void main(){ vP = position.xz; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }',
  fragmentShader: `varying vec2 vP; uniform float uA; void main(){
    vec2 q = vP * 2.5; vec2 g = abs(fract(q) - .5); float r = length(g), w = fwidth(r) * 1.2; float d = 1. - smoothstep(.05 - w, .05 + w, r);
    float dens = length(fwidth(q)); d *= 1. - smoothstep(.12, .35, dens);   // 점이 한 픽셀보다 촘촘해지면 지운다
    vec2 q2 = vP * .5; vec2 g2 = abs(fract(q2) - .5); vec2 w2 = fwidth(q2) * 1.5; vec2 ln = 1. - smoothstep(vec2(0.), w2, g2); float l = max(ln.x, ln.y) * (1. - smoothstep(.04, .12, length(fwidth(q2))));
    float f = exp(-dot(vP, vP) * .018); gl_FragColor = vec4(vec3(.32, .38, .55), (d * .5 + l * .1) * f * uA); }` }));
floor.position.y = -0.7; floor.renderOrder = -1; root.add(floor);

// 벽: 지난 24시간 실제 카드들(한 장의 큰 텍스처 아틀라스)
const wall = new THREE.Group(); root.add(wall);
const COLS = mobile() ? 5 : 9, ROWS = mobile() ? 9 : 7, CW = mobile() ? 384 : 512, CH = CW * H / W;
const atlas = document.createElement('canvas'); atlas.width = CW * COLS; atlas.height = CH * ROWS; const ag = atlas.getContext('2d');
const atex = new THREE.CanvasTexture(atlas); atex.colorSpace = THREE.SRGBColorSpace; atex.anisotropy = r.capabilities.getMaxAnisotropy();
const cells = [];
for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) {
  const cx = x - (COLS - 1) / 2, cy = y - (ROWS - 1) / 2; if (cx === 0 && cy === 0) continue;
  const t = atex.clone(); t.repeat.set(1 / COLS, 1 / ROWS); t.offset.set(x / COLS, 1 - (y + 1) / ROWS); t.needsUpdate = true;
  const m = new THREE.Mesh(pgeo, new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false, toneMapped: false, opacity: 0 }));
  m.position.set(cx * (PW + 0.35), 0, cy * (PH + 0.35)); m.userData = { x, y, d: Math.hypot(cx, cy * 1.4) }; wall.add(m); cells.push(m);
}

// ---------- 데이터 ----------
let IT = null, WALL = [], ALL = 0;
const pick = (items, en) => {
  let xs = items.filter((x) => x.v !== '중립').map((x) => ({ ...x, en: en[x.id] || null })); if (xs.some((x) => x.en)) xs = xs.filter((x) => x.en);   // 영어·한국어 둘 다 있는 소식만
  const sc = (x) => (x.en ? 6 : 0) + Math.min(x.n || 1, 3) * 2 + (x.coins.length ? 3 : 0) + (x.sectors.length ? 2 : 0) + (x.s || 1) + (x.kind === 'event' ? 1 : 0) - (Date.now() / 1000 - x.t) / 7200;
  return xs.sort((a, b) => sc(b) - sc(a));
};
function paintAll() {
  if (!IT) return;
  plates.forEach((p, i) => { p.k = -1; drawPlate(hi(p.g), i, IT, i === 0 || i === 2 || i === 4 ? 0 : 1); p.tex.needsUpdate = true; });
  ag.clearRect(0, 0, atlas.width, atlas.height);
  let n = 0; for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) { const cx = x - (COLS - 1) / 2, cy = y - (ROWS - 1) / 2; if (cx === 0 && cy === 0) continue; const it = WALL[n++ % Math.max(1, WALL.length)]; if (it) summary(ag, it, x * CW, y * CH, CW, CH); }
  atex.needsUpdate = true; cells.forEach((m) => { m.material.map.needsUpdate = true; });
}
// 벽 카드: 영어 화면이면 영어 줄이 있는 소식부터, 모자라면 나머지(한국어 줄)로 채운다 — 비어 보이지 않게
const wallOf = (items, since, en) => { const pool = items.filter((x) => x.id !== IT.id && x.t >= since), pri = L() === 'ko' ? pool : [...pool.filter((x) => en[x.id]), ...pool.filter((x) => !en[x.id])];
  return pri.slice(0, COLS * ROWS).map((x) => ({ ...x, en: en[x.id] || null })); };
Promise.all([DFD.flash(), EN]).then(async ([d, en]) => {
  const s = Date.now() / 1000 - 86400, xs = pick(d.items, en); IT = xs[0]; ALL = d.items.filter((x) => x.t >= s).length;
  WALL = wallOf(d.items, s, en);
  await fonts(IT.ko + WALL.map((x) => x.ko).join(''));
  paintAll(); setCount(); DFI.onLang(() => { WALL = wallOf(d.items, s, en); paintAll(); setCount(); });
});

// ---------- 글(왼쪽 단계 목록·끝 문구) ----------
const STEPS = [['A headline lands.', 'From live wires worldwide, in any language — within seconds.', '소식이 들어와요.', '전 세계 실시간 속보 채널에서, 어떤 언어든 몇 초 안에.'],
  ['Read in your language.', 'Translated into English and Korean, side by side.', '읽기 쉬운 말로.', '영어와 한국어로 바로 번역해요.'],
  ['Positive or negative.', 'Called for markets by AI, with a strength from 1 to 3.', '호재인지 악재인지.', 'AI가 시장 기준으로 판정하고, 세기를 1~3으로 매겨요.'],
  ['Who it touches.', 'Coins, sectors, and whether it moves the whole market.', '어디에 닿는지.', '관련 코인·섹터, 시장 전체에 영향인지.'],
  ['How many reported it.', 'The same story from several outlets becomes one card.', '몇 곳이 보도했는지.', '여러 곳에서 나온 같은 소식은 카드 하나로 묶어요.']];
const ol = sec.querySelector('.nx-steps'), endc = sec.querySelector('.nx-end');
const setSteps = () => { ol.innerHTML = STEPS.map((s, i) => `<li><span class="n">0${i + 1}</span><div><b>${L() === 'ko' ? s[2] : s[0]}</b><p>${L() === 'ko' ? s[3] : s[1]}</p></div><i></i></li>`).join(''); };
const setCount = () => { endc.querySelector('b').innerHTML = T(`One of <em>${ALL || '–'}</em> signals judged in the last 24 hours.`, `지난 24시간, 이렇게 판정한 <em>${ALL || '–'}</em>건 중 하나.`); };
setSteps(); setCount(); DFI.onLang(() => { setSteps(); lastA = -1; });
sec.querySelector('.nx-k').textContent = ''; const setK = () => { sec.querySelector('.nx-k').textContent = T('Inside one signal', '신호 하나의 속'); setCount(); }; setK(); DFI.onLang(setK);

// ---------- 스크롤 → 상태 ----------
let P = 0, PT = 0, lastA = -1; const tgt = new THREE.Vector3(), off = { x: 0, y: 0 };
// 단계: 스크롤이 판 i의 구간(act∈[i,i+1))에 들어오면 그 판이 '튀어나온다'. 움직임 자체는 스크롤이 아니라 스프링 물리(시간)로 — 살짝 지나쳤다 돌아오는 반동.
// 앞 판이 거의 들어가야 다음 판이 나온다(두 장이 동시에 나오지 않는다).
const P0 = 0.17, PS = 0.118, ST0 = 0.15, ST1 = 0.76;
const sm = (x) => { x = clamp(x); return x * x * x * (x * (x * 6 - 15) + 10); };
const spring = (o, kx, kv, target, k, c, dt) => { const n = 2, h = dt / n; for (let q = 0; q < n; q++) { o[kv] += (k * (target - o[kx]) - c * o[kv]) * h; o[kx] += o[kv] * h; } };
// 스크롤을 멈추면 가장 가까운 단계 한가운데에 멈춘다
const SNAP = [0, 0.165, ...[0, 1, 2, 3, 4].map((i) => P0 + PS * (i + 0.51)), 0.985, 1];
gsap.registerPlugin(ScrollTrigger);
ScrollTrigger.create({ trigger: sec, start: 'top top', end: '+=' + (mobile() ? 520 : 600) + '%', pin: true, anticipatePin: 1, onUpdate: (st) => { PT = st.progress; },
  snap: /nosnap/.test(location.search) ? undefined : { snapTo: SNAP, duration: { min: 0.25, max: 0.7 }, delay: 0.12, ease: 'power2.inOut', directional: false } });
const lis = () => [...ol.children];
const dirV = new THREE.Vector3();
// 마우스: 들어 보인 카드가 커서 쪽으로 살짝 기운다
const ptr = { x: 0, y: 0, tx: 0, ty: 0 };
addEventListener('pointermove', (e) => { ptr.tx = e.clientX / innerWidth * 2 - 1; ptr.ty = -(e.clientY / innerHeight * 2 - 1); }, { passive: true });
const vR = new THREE.Vector3(), vU = new THREE.Vector3(), vB = new THREE.Vector3(), mB = new THREE.Matrix4(), qP = new THREE.Quaternion(), qA = new THREE.Quaternion(), qB = new THREE.Quaternion(), qI = new THREE.Quaternion(), qS = new THREE.Quaternion();
const pOut = new THREE.Vector3(), pShow = new THREE.Vector3(), Y = new THREE.Vector3(0, 1, 0);
loop(sec, r, scene, cam, (t, dt) => {
  P += (PT - P) * (reduce ? 1 : Math.min(1, dt * 8));
  ptr.x += (ptr.tx - ptr.x) * Math.min(1, dt * 5); ptr.y += (ptr.ty - ptr.y) * Math.min(1, dt * 5);
  const mob = mobile();
  const ex = ss(0.05, 0.16, P) * (1 - ss(0.77, 0.86, P));              // 분해 정도
  const act = clamp((P - P0) / PS, 0, 4.999), inSteps = ss(ST0, 0.17, P) * (1 - ss(ST1 - 0.02, ST1 + 0.02, P));
  const back = ss(0.86, 0.97, P);                                        // 마지막: 물러나며 벽
  const el = lerp(87, mob ? 36 : 30, ex) * Math.PI / 180, az = lerp(0, mob ? -24 : -34, ex) * Math.PI / 180;
  // 카메라 먼저(들어 보일 자리가 카메라 기준이라서)
  const R = lerp(lerp(mob ? 15 : 8.6, mob ? 19 : 15.2, ex), mob ? 30 : 26, back);
  const top5 = plates[5].m.position.y; tgt.set(0, top5 * 0.52, 0);
  cam.position.set(Math.sin(az) * Math.cos(el) * R, tgt.y + Math.sin(el) * R, Math.cos(az) * Math.cos(el) * R); cam.lookAt(tgt);
  const w = sec.clientWidth, h = sec.clientHeight, shf = 1 - back;
  off.x = mob ? 0 : -w * 0.19 * shf; off.y = mob ? -h * 0.19 * shf : -h * 0.07 * ex; cam.setViewOffset(w, h, off.x, off.y, w, h); cam.updateMatrixWorld();
  vR.setFromMatrixColumn(cam.matrixWorld, 0); vU.setFromMatrixColumn(cam.matrixWorld, 1); vB.setFromMatrixColumn(cam.matrixWorld, 2);
  // 들어 보일 자리: 카메라 앞, 화면 폭의 44%(모바일 86%)를 차지하는 거리
  const tanH = Math.tan(cam.fov * Math.PI / 360), dShow = PW / ((mob ? 0.82 : 0.4) * 2 * tanH * cam.aspect);
  const bob = 0;
  pShow.copy(cam.position).addScaledVector(vB, -dShow).addScaledVector(vU, (mob ? -0.03 : -0.05) * dShow + bob);
  // 정면을 보는 방향(판의 앞면=카메라, 글 위쪽=화면 위) + 살짝 비스듬히 + 커서 따라 기울기
  mB.makeBasis(vR, vB, vU.clone().negate()); qP.setFromRotationMatrix(mB);
  // 서랍이 빠지는 방향: 카메라 쪽(수평), 데스크톱은 화면 오른쪽으로 조금 비껴서
  const pa = az; dirV.set(Math.sin(pa), 0, Math.cos(pa));
  const sp = lerp(0.012, mob ? 0.72 : 0.64, ex), G = mob ? 1.15 : 0.95, D = mob ? 1.7 : 2.3;
  const cur = inSteps > 0.5 ? Math.min(4, Math.floor(act)) : -1;
  // 판 i의 구간(act∈[i,i+1))을 스크롤 위치로 나눈다 — 빠르게 스크롤해도 카드가 스크롤을 그대로 따라온다(건너뛰지 않음).
  //   0~14% 서랍에서 수평으로 빠짐 → 12~36% 사용자 앞으로 다가와 정면 → 36~64% 머묾 → 64~88% 서랍 앞으로 돌아감 → 86~100% 쏙 들어감
  const xOf = (s) => sm(s / 0.14) * (1 - sm((s - 0.86) / 0.14)), fOf = (s) => sm((s - 0.12) / 0.24) * (1 - sm((s - 0.64) / 0.24));
  plates.forEach((p, i) => { const s = act - i, on = i < 5 && s >= 0 && s < 1; p.x = on ? xOf(s) * inSteps : 0; p.f = on ? fOf(s) * inSteps : 0; p.s = s; });
  const showing = Math.max(...plates.map((q) => q.f));
  let lift = 0;
  plates.forEach((p, i) => {
    const top = i === 5, y = i * sp + lift * ex, fc = p.f;
    pOut.set(dirV.x * D * p.x, y, dirV.z * D * p.x);
    // 위치: 서랍 앞 → 카메라 앞(곧게). 회전: 누운 판 → 정면(카메라와 평행)
    p.m.position.copy(pOut).lerp(pShow, fc);
    p.m.quaternion.copy(qI).slerp(qP, ss(0.05, 0.85, fc));
    // 그림자: 더미 안에서는 아래 판 위에, 정면일 때는 카드 뒤에 떠 있는 그림자
    if (fc > 0.02) { p.sh.position.copy(p.m.position).addScaledVector(vB, -0.35).addScaledVector(vU, -0.32).addScaledVector(vR, 0.12); p.sh.quaternion.copy(p.m.quaternion); p.sh.material.opacity = fc * 0.35; }
    else { p.sh.position.set(pOut.x + 0.08, y - 0.03, pOut.z + 0.14); p.sh.quaternion.identity(); p.sh.material.opacity = clamp(ex * 2) * (i ? 0.38 : 0.28) * (1 - back); }
    p.sn.material.opacity = 0;
    lift += p.x * G;   // 위 판들은 빈 자리만큼 들려 길을 비킨다(서로 뚫고 지나가지 않게)
    p.m.material.color.setScalar(fc > 0.5 ? 1 : lerp(1, top ? 0.86 : 0.8, showing));   // 정면 카드가 있는 동안 뒤 더미는 한 톤 가라앉는다
    // 움직이는 층(글자 풀림·판정 도장·점 연결): 카드가 정면에 다가오는 동안 재생
    if (i === 0 || i === 2 || i === 4) { const kk = P > 0.79 || cur > i ? 1 : cur < i ? 0 : clamp((p.s - 0.2) / 0.22);
      if (IT && (Math.abs(kk - p.k) > 0.03 || (kk === 1 && p.k !== 1) || (kk === 0 && p.k !== 0))) { p.k = kk; drawPlate(hi(p.g), i, IT, kk); p.tex.needsUpdate = true; } }
  });
  FX.update(t, cam, vR, vU, vB);
  posts.scale.y = Math.max(0.01, top5); posts.material.opacity = 0.45 * ex * (1 - showing * 0.6);
  PU.uT.value = t; PU.uF.value = ss(0.0, 0.05, P) * (1 - ss(0.08, 0.14, P)) * 0.6;   // 입자는 섹션 들어올 때만(카드 위에 점이 끼지 않게) PU.uY.value = 0;
  cells.forEach((m) => { const k = clamp(back * 1.6 - m.userData.d * 0.12); m.material.opacity = k * 0.95; m.position.y = -0.02 - (1 - k) * 0.8; });
  FU.uA.value = ex * (1 - back);
  const a = Math.min(4, Math.floor(act + 0.02)); if (a !== lastA && ol.children.length) { lastA = a; lis().forEach((li, i) => li.classList.toggle('on', i === a)); }
  lis().forEach((li, i) => { li.querySelector('i').style.transform = `scaleX(${sm(act - i).toFixed(3)})`; });
  sec.style.setProperty('--cp', (ss(0.02, 0.07, P) * (1 - ss(0.78, 0.84, P))).toFixed(3));
  sec.style.setProperty('--ep', ss(0.9, 0.98, P).toFixed(3));
});

// ---------- 후보 바꾸기(미리보기 전용) + ?go=1이면 첫 단계로 바로 이동 ----------
{
  if (/go=1/.test(location.search)) { const go = () => { const st = ScrollTrigger.getAll().find((x) => x.trigger === sec); if (!st) return; ScrollTrigger.refresh(); scrollTo(0, st.start + (P0 + PS * 0.51) * (st.end - st.start)); };
    addEventListener('load', () => setTimeout(go, 900)); }
}
