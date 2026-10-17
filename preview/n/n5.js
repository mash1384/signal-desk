// N5 · The day as a river — H5(흐르는 잉크) 다음 섹션.
// 첫 화면의 잉크가 빠져나간 자리에서, 지난 24시간이 한 줄기 잉크 강으로 흐른다.
// 강 폭 = 그 시간에 나온 소식 수, 물빛 = 호재·악재 쪽으로 기운 정도, 물 위의 점 하나하나 = 실제 소식.
// 스크롤하면 하늘에서 내려다본 하루 전체 → 강을 따라 24시간 전부터 지금까지 내려오며 그 시간의 큰 소식이 떠오르고 → 끝에서 다음 큰 발표까지 남은 길이 보인다.
import * as THREE from 'three';
import { renderer, loop, mobile, reduce, fonts, lerp, clamp, ss, EN } from './nkit.js';

const sec = document.getElementById('nx'), canvas = document.getElementById('nxgl'), lay = sec.querySelector('.rv-lay');
const r = renderer(canvas), scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(35, 1, 0.1, 400);
scene.fog = new THREE.Fog(0xf7f9fc, 40, 120);
const L = () => DFI.lang(), T = (en, ko) => L() === 'ko' ? ko : en;
const NOW = Date.now() / 1000, T0 = NOW - 86400;
const hm = (t) => { const d = new Date(t * 1000); return `${String(d.getHours()).padStart(2, '0')}:00`; };

// ---------- 강의 길: 25개 시각(24시간 전 … 지금)을 지나는 부드러운 곡선 ----------
const SPAN = 2.4, pts = [...Array(25)].map((_, h) => new THREE.Vector3((h - 12) * SPAN, 0, Math.sin(h * 0.45) * 3.4 + Math.sin(h * 0.17 + 1) * 2.2));
const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal');
// 앞으로(다음 발표까지) 이어지는 점선 길
const at = (u) => curve.getPointAt(clamp(u, 0, 1)), tan = (u) => curve.getTangentAt(clamp(u, 0, 1));
const side = (u) => { const t = tan(u); return new THREE.Vector3(-t.z, 0, t.x).normalize(); };

// ---------- 데이터 → 시간별 폭·기울기 ----------
const B = [...Array(24)].map(() => ({ n: 0, u: 0, d: 0 }));
let ITEMS = [], CARDS = [], ENT = {}, NEXT = null, BRIEF = null;
const widthAt = (u) => { const x = clamp(u * 24 - 0.5, 0, 23), i = Math.floor(x), f = x - i, a = B[i], b = B[Math.min(23, i + 1)], mx = Math.max(1, ...B.map((q) => q.n)); return 0.5 + 3.0 * lerp(a.n, b.n, f * f * (3 - 2 * f)) / mx; };
const netAt = (u) => { const x = clamp(u * 24 - 0.5, 0, 23), i = Math.floor(x), f = x - i, n = (q) => (q.u - q.d) / (q.u + q.d + 2); return lerp(n(B[i]), n(B[Math.min(23, i + 1)]), f); };

// ---------- 강(리본) ----------
const M = mobile() ? 360 : 640;
const rg = new THREE.BufferGeometry(), RU = { uT: { value: 0 }, uF: { value: 0 }, uIn: { value: 0 } };
function buildRibbon() {
  const pos = new Float32Array((M + 1) * 2 * 3), aU = new Float32Array((M + 1) * 2), aV = new Float32Array((M + 1) * 2), aN = new Float32Array((M + 1) * 2), aW = new Float32Array((M + 1) * 2), idx = [];
  for (let i = 0; i <= M; i++) { const u = i / M, p = at(u), s = side(u), w = widthAt(u), n = netAt(u);
    for (let k = 0; k < 2; k++) { const v = k ? 1 : -1, j = i * 2 + k; pos.set([p.x + s.x * v * w / 2, 0, p.z + s.z * v * w / 2], j * 3); aU[j] = u; aV[j] = v; aN[j] = n; aW[j] = w; }
    if (i < M) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } }
  rg.setAttribute('position', new THREE.BufferAttribute(pos, 3)); rg.setAttribute('aU', new THREE.BufferAttribute(aU, 1)); rg.setAttribute('aV', new THREE.BufferAttribute(aV, 1));
  rg.setAttribute('aN', new THREE.BufferAttribute(aN, 1)); rg.setAttribute('aW', new THREE.BufferAttribute(aW, 1)); rg.setIndex(idx); rg.computeBoundingSphere();
}
const NOISE = `vec2 hash(vec2 p){ p = vec2(dot(p,vec2(127.1,311.7)), dot(p,vec2(269.5,183.3))); return -1.+2.*fract(sin(p)*43758.5453); }
  float noise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f*f*(3.-2.*f); return mix(mix(dot(hash(i),f), dot(hash(i+vec2(1,0)),f-vec2(1,0)),u.x), mix(dot(hash(i+vec2(0,1)),f-vec2(0,1)), dot(hash(i+vec2(1,1)),f-vec2(1,1)),u.x),u.y); }
  float fbm(vec2 p){ float s = 0., a = .5; for(int i=0;i<4;i++){ s += a*noise(p); p = p*2.03 + 11.; a *= .5; } return s; }`;
const river = new THREE.Mesh(rg, new THREE.ShaderMaterial({ uniforms: RU, transparent: true, depthWrite: false, side: THREE.DoubleSide,
  vertexShader: `attribute float aU, aV, aN, aW; uniform float uT; varying float vU, vV, vN, vW; varying vec3 vP;
    void main(){ vU = aU; vV = aV; vN = aN; vW = aW; vec3 p = position; p.y += sin(aU*90. - uT*1.2 + aV*1.5) * .05 + sin(aU*31. + uT*.6) * .06; vP = p; gl_Position = projectionMatrix*modelViewMatrix*vec4(p,1.); }`,
  fragmentShader: `precision highp float; uniform float uT, uF, uIn; varying float vU, vV, vN, vW; varying vec3 vP; ${NOISE}
    void main(){ float t = uT*.05; vec2 p = vec2(vU*46. - uT*.22, vV*vW*.42);
      vec2 q = vec2(fbm(p*.9 + t), fbm(p*.9 - t + 4.)); vec2 r2 = vec2(fbm(p*.9 + 2.*q + vec2(1.7,9.2) + t*1.3), fbm(p*.9 + 2.*q + vec2(8.3,2.8) - t));
      float f = fbm(p*.9 + 2.2*r2);
      vec3 c1 = vec3(.051,.145,.239), c2 = vec3(.325,.227,.992), c3 = vec3(.18,.85,.77), c4 = vec3(.94,.96,1.), up = vec3(.07,.69,.49), dn = vec3(.90,.33,.25);
      float ff = f*1.8 + .1; vec3 col = mix(c4, c2, smoothstep(-.35, .3, ff)); col = mix(col, c1, smoothstep(.25, .75, length(q)*1.6)); col = mix(col, c3, smoothstep(.1, .6, r2.x*1.6) * .35);
      col += pow(max(0., fbm(p*2.6 + r2*1.5 + t*2.)), 2.) * 2. * vec3(.85,.92,1.) * .45;
      // 강둑 빛: 그 시간에 호재(초록)·악재(빨강) 쪽으로 기운 만큼
      float bank = smoothstep(.5, .95, abs(vV)); col = mix(col, vN > 0. ? up : dn, bank * clamp(abs(vN)*2.2, 0., .85));
      float edge = 1. - smoothstep(.9, 1., abs(vV)); float a = edge * smoothstep(0., .015, vU) * (1. - smoothstep(uIn - .01, uIn, vU));
      gl_FragColor = vec4(col, a); }` }));
scene.add(river);
// 강 아래 그림자(바닥에서 살짝 뜬 느낌)
const shadow = new THREE.Mesh(rg, new THREE.ShaderMaterial({ uniforms: RU, transparent: true, depthWrite: false, vertexShader: `attribute float aV, aU; varying float vV, vU; void main(){ vV = aV; vU = aU; vec3 p = position; p.y = -.6; p.x += .5; p.z += .7; gl_Position = projectionMatrix*modelViewMatrix*vec4(p,1.); }`,
  fragmentShader: `uniform float uIn; varying float vV, vU; void main(){ gl_FragColor = vec4(.05,.1,.25, .07 * (1. - smoothstep(.3, 1., abs(vV))) * (1. - step(uIn, vU))); }` }));
shadow.renderOrder = -1; scene.add(shadow);

// ---------- 물 위의 점: 실제 소식 하나하나 ----------
const dg = new THREE.BufferGeometry(), DU = { uT: { value: 0 }, uFocus: { value: 0 }, uIn: { value: 0 } };
const dots = new THREE.Points(dg, new THREE.ShaderMaterial({ uniforms: DU, transparent: true, depthWrite: false,
  vertexShader: `attribute vec3 aC; attribute float aS, aU, aR; uniform float uT, uFocus, uIn; varying vec3 vC; varying float vA;
    void main(){ vec3 p = position; p.y += .25 + aS*.18 + sin(uT*1.4 + aR*30.)*.06; float near = exp(-pow((aU - uFocus)*14., 2.));
      vC = aC; vA = step(aU, uIn) * mix(.75, 1., near); vec4 mv = modelViewMatrix*vec4(p,1.); gl_Position = projectionMatrix*mv;
      gl_PointSize = min(26., (2.2 + aS*1.5) * (1. + near*.5) * (17. / -mv.z)) * ${Math.min(devicePixelRatio || 1, 2).toFixed(1)}; }`,
  fragmentShader: `varying vec3 vC; varying float vA; void main(){ vec2 c = gl_PointCoord-.5; float d = length(c); if(d>.5) discard; float core = smoothstep(.3,.24,d), halo = (1.-smoothstep(.0,.5,d))*.45; vec3 col = mix(vC, vec3(1.), smoothstep(.12,.0,d)*.6); gl_FragColor = vec4(col, vA*max(core, halo)); }` }));
scene.add(dots);
function buildDots() {
  const xs = ITEMS, n = xs.length, pos = new Float32Array(n * 3), aC = new Float32Array(n * 3), aS = new Float32Array(n), aU = new Float32Array(n), aR = new Float32Array(n);
  const col = { '호재': new THREE.Color('#12b07c'), '악재': new THREE.Color('#e5533f'), '중립': new THREE.Color('#aab4c4') };
  xs.forEach((x, i) => { const u = clamp((x.t - T0) / 86400), p = at(u), s = side(u), w = widthAt(u), o = (Math.random() - 0.5) * w * 0.75;
    pos.set([p.x + s.x * o, 0, p.z + s.z * o], i * 3); const c = col[x.v] || col['중립']; aC.set([c.r, c.g, c.b], i * 3); aS[i] = x.s || 1; aU[i] = u; aR[i] = Math.random(); });
  dg.setAttribute('position', new THREE.BufferAttribute(pos, 3)); dg.setAttribute('aC', new THREE.BufferAttribute(aC, 3)); dg.setAttribute('aS', new THREE.BufferAttribute(aS, 1));
  dg.setAttribute('aU', new THREE.BufferAttribute(aU, 1)); dg.setAttribute('aR', new THREE.BufferAttribute(aR, 1)); dg.computeBoundingSphere();
}

// ---------- 앞으로 가는 점선 길 + 다음 큰 발표(문) ----------
const fut = new THREE.Group(); scene.add(fut);
let gateP = new THREE.Vector3();
function buildFuture() {
  const end = at(1), tg = tan(1), hrs = NEXT ? clamp((NEXT.ts - NOW) / 3600, 2, 96) : 24, len = 5 + Math.sqrt(hrs) * 1.1;
  const ps = [...Array(40)].map((_, i) => { const k = i / 39; return end.clone().add(tg.clone().multiplyScalar(k * len)).add(new THREE.Vector3(0, 0, Math.sin(k * 3) * 1.2 * k)); });
  const lg = new THREE.BufferGeometry().setFromPoints(ps), ln = new THREE.Line(lg, new THREE.LineDashedMaterial({ color: 0x533afd, dashSize: 0.35, gapSize: 0.3, transparent: true, opacity: 0.7 })); ln.computeLineDistances(); fut.add(ln);
  gateP = ps[39].clone();
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.5, 0.56, 64).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x533afd, transparent: true, side: THREE.DoubleSide })); ring.position.copy(gateP).add(new THREE.Vector3(0, 0.02, 0)); fut.add(ring); fut.userData.ring = ring;
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 3.2, 12), new THREE.MeshBasicMaterial({ color: 0x533afd, transparent: true })); beam.position.copy(gateP).add(new THREE.Vector3(0, 1.6, 0)); fut.add(beam);
  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.2, 24, 12), new THREE.MeshBasicMaterial({ color: 0x533afd, transparent: true })); tip.position.copy(gateP).add(new THREE.Vector3(0, 3.2, 0)); fut.add(tip);
}
// '지금' 표시: 강 끝에서 맥박
const nowDot = new THREE.Mesh(new THREE.SphereGeometry(0.2, 32, 16), new THREE.MeshBasicMaterial({ color: 0x0d253d })); scene.add(nowDot);
const nowRing = new THREE.Mesh(new THREE.RingGeometry(0.4, 0.48, 64).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x533afd, transparent: true, side: THREE.DoubleSide })); scene.add(nowRing);

// ---------- 글(HTML): 시각 눈금, 큰 소식 카드, 위쪽 안내, 끝 카드 ----------
const ticks = [...Array(9)].map((_, i) => { const el = document.createElement('span'); el.className = 'rv-tick'; lay.appendChild(el); return { el, u: i / 8 }; });
const stems = new THREE.Group(); scene.add(stems);
const cap = sec.querySelector('.rv-cap'), hud = sec.querySelector('.rv-hud'), endc = sec.querySelector('.rv-end');
function buildCards() {
  lay.querySelectorAll('.rv-card').forEach((e) => e.remove()); stems.clear(); CARDS = [];
  for (let w = 0; w < 8; w++) {   // 3시간마다 가장 큰 소식 하나
    const a = T0 + w * 10800, b = a + 10800, xs = ITEMS.filter((x) => x.t >= a && x.t < b && x.v !== '중립' && (L() === 'ko' || ENT[x.id]));
    if (!xs.length) continue; const it = xs.sort((p, q) => ((q.s || 1) * 2 + (q.n || 1)) - ((p.s || 1) * 2 + (p.n || 1)))[0];
    const u = clamp((it.t - T0) / 86400), p = at(u), s = side(u), sd = w % 2 ? 1 : -1, anchor = p.clone().add(s.clone().multiplyScalar(sd * (widthAt(u) / 2 + 0.9))).add(new THREE.Vector3(0, 2.2, 0));
    const el = document.createElement('article'); el.className = 'rv-card';
    el.innerHTML = `<p class="m"><b class="${DFD.vcls(it.v)}">${DFI.v(it.v)}</b><span>${DFD.hm(it.t)} · ${DFI.outlets(it.n || 1)}</span></p><p class="t">${DFD.esc(L() === 'ko' ? it.ko : ENT[it.id])}</p>`;
    lay.appendChild(el);
    const g = new THREE.BufferGeometry().setFromPoints([p.clone().add(new THREE.Vector3(0, 0.3, 0)), anchor]); const ln = new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0x0d253d, transparent: true, opacity: 0 })); stems.add(ln);
    const pin = new THREE.Mesh(new THREE.SphereGeometry(0.09, 16, 8), new THREE.MeshBasicMaterial({ color: it.v === '호재' ? 0x12b07c : 0xe5533f, transparent: true })); pin.position.copy(p).add(new THREE.Vector3(0, 0.3, 0)); stems.add(pin);
    CARDS.push({ el, u, anchor, ln, pin });
  }
}
const setText = () => {
  const c = { n: ITEMS.length, u: ITEMS.filter((x) => x.v === '호재').length, d: ITEMS.filter((x) => x.v === '악재').length };
  cap.innerHTML = `<b>${T('The last 24 hours, as one river.', '지난 24시간을, 한 줄기 강으로.')}</b><span>${T('Width is how much news broke. Colour is which way it leaned. Every dot is a real story.', '폭은 소식의 양, 물빛은 호재·악재 쪽으로 기운 정도, 점 하나하나는 실제 소식이에요.')}</span>
    <p class="lg"><i class="w"></i>${T('more news', '소식 많음')}<i class="g"></i>${T('leaned positive', '호재 우세')}<i class="r"></i>${T('leaned negative', '악재 우세')}<i class="dt"></i>${c.n} ${T('stories', '건')}</p>`;
  const kinds = { cpi: 'US CPI', ppi: 'US PPI', nfp: 'US Jobs Report', fomc: 'Fed Rate Decision', pce: 'US PCE', gdp: 'US GDP' };
  const left = NEXT ? Math.max(0, NEXT.ts - NOW) : 0, lt = `${Math.floor(left / 86400) ? Math.floor(left / 86400) + T('d ', '일 ') : ''}${Math.floor(left % 86400 / 3600)}${T('h ', '시간 ')}${Math.floor(left % 3600 / 60)}${T('m', '분')}`;
  endc.innerHTML = `<div class="rv-now"><p class="k">${T('Now', '지금')}</p><b>${T('That was today.', '여기까지가 오늘이에요.')}</b>${BRIEF ? `<p class="br"><span>${T('Tomorrow 09:00 · daily brief', '내일 오전 9시 · 하루 정리')}</span>${DFD.esc(DFI.line({ id: 'brief:' + BRIEF.date }) || BRIEF.headline || '')}</p>` : ''}</div>
    ${NEXT ? `<div class="rv-next"><p class="k">${T('Next big release', '다음 큰 발표')}</p><b>${DFD.esc(L() === 'ko' ? NEXT.name : (kinds[NEXT.kind] || NEXT.title || NEXT.name))}</b><p class="cd">${lt}</p><p class="s">${NEXT.vs_normal ? `${T('Past releases moved Bitcoin', '지난 발표 때 비트코인 흔들림')} <em>${NEXT.vs_normal.toFixed(1)}×</em> ${T('a normal hour', '평소 대비')}` : ''}</p></div>` : ''}`;
  ticks.forEach((t) => { t.el.textContent = t.u === 1 ? T('Now', '지금') : hm(T0 + t.u * 86400); });
};
Promise.all([DFD.flash(), EN, DFD.nextEvent().catch(() => null), DFD.brief().catch(() => null)]).then(async ([d, en, nx, br]) => {
  ENT = en; NEXT = nx; BRIEF = br; ITEMS = d.items.filter((x) => x.t >= T0);
  ITEMS.forEach((x) => { const b = B[Math.min(23, Math.floor((x.t - T0) / 3600))]; b.n++; if (x.v === '호재') b.u++; if (x.v === '악재') b.d++; });
  buildRibbon(); buildDots(); buildFuture(); await fonts(ITEMS.map((x) => x.ko).join('').slice(0, 4000)); buildCards(); setText();
  DFI.onLang(() => { buildCards(); setText(); });
});
buildRibbon();

// ---------- 스크롤 → 카메라 ----------
let P = 0, PT = 0; const v3 = new THREE.Vector3(), cp = new THREE.Vector3(), lk = new THREE.Vector3(), oP = new THREE.Vector3(), oL = new THREE.Vector3(0, 0, 0);
gsap.registerPlugin(ScrollTrigger);
ScrollTrigger.create({ trigger: sec, start: 'top top', end: '+=' + (mobile() ? 560 : 640) + '%', pin: true, anticipatePin: 1, onUpdate: (s) => { PT = s.progress; } });
const proj = (p) => { v3.copy(p).project(cam); return [(v3.x + 1) / 2 * sec.clientWidth, (1 - v3.y) / 2 * sec.clientHeight, v3.z]; };
loop(sec, r, scene, cam, (t, dt) => {
  P += (PT - P) * (reduce ? 1 : Math.min(1, dt * 6));
  const mob = mobile(), w = sec.clientWidth, h = sec.clientHeight;
  const grow = ss(0.0, 0.12, P);                         // 강이 왼쪽(24시간 전)부터 흘러 차오름
  const dive = ss(0.13, 0.24, P) * (1 - ss(0.84, 0.95, P));  // 내려다보기 ↔ 강 따라가기
  const fU = clamp((P - 0.2) / 0.62);                    // 지금 보고 있는 시각(0=24시간 전, 1=지금)
  const endV = ss(0.86, 0.97, P);                         // 끝: 지금 + 다음 발표
  RU.uT.value = t; DU.uT.value = t; RU.uIn.value = DU.uIn.value = lerp(0.001, 1, grow) + 0.02; DU.uFocus.value = dive > 0.3 ? fU : -1;
  // 내려다보기 위치
  if (mob) { oP.set(-50, 30, 10); oL.set(8, 0, 0); } else { oP.set(-36, 19, 30); oL.set(7, -3, -5); }
  // 강 따라가기: 보고 있는 시각보다 조금 뒤·옆·위에서, 조금 앞을 본다
  const a = at(fU - 0.035), s = side(fU), ahead = at(fU + 0.03);
  cp.copy(a).add(s.clone().multiplyScalar(mob ? 9 : 8.5)).add(new THREE.Vector3(0, mob ? 7.5 : 5.2, 0)); lk.copy(ahead).add(new THREE.Vector3(0, 1.1, 0));
  // 끝 장면: 지금과 다음 발표 문을 함께
  const nowP = at(1), eP = nowP.clone().lerp(gateP.lengthSq() ? gateP : nowP, 0.5);
  const endCam = eP.clone().add(new THREE.Vector3(mob ? -6 : -4, mob ? 22 : 13, mob ? 22 : 16)), endLook = eP.clone().add(new THREE.Vector3(mob ? 0 : -1.5, mob ? -1 : 0.5, 0));
  const camP = oP.clone().lerp(cp, dive), lookP = oL.clone().lerp(lk, dive);
  if (P > 0.84) { camP.lerp(endCam, endV); lookP.lerp(endLook, endV); }
  cam.position.copy(camP); cam.lookAt(lookP);
  cam.setViewOffset(w, h, 0, mob ? -h * 0.06 * (1 - dive) : 0, w, h);
  // '지금' 점과 문
  nowDot.position.copy(nowP).add(new THREE.Vector3(0, 0.3, 0)); nowRing.position.copy(nowP).add(new THREE.Vector3(0, 0.05, 0)); const pk = (t * 0.6) % 1; nowRing.scale.setScalar(1 + pk * 1.6); nowRing.material.opacity = (1 - pk) * grow;
  nowDot.visible = grow > 0.95; fut.visible = P > 0.6; fut.children.forEach((c) => { if (c.material) c.material.opacity = (c.material.type === 'LineDashedMaterial' ? 0.7 : c === fut.userData.ring ? 1 - ((t * 0.5) % 1) : 1) * endV; });
  if (fut.userData.ring) fut.userData.ring.scale.setScalar(1 + ((t * 0.5) % 1) * 2.2);
  // 시각 눈금
  ticks.forEach((k) => { const [x, y, z] = proj(at(k.u).add(side(k.u).multiplyScalar(-(widthAt(k.u) / 2 + 0.7)))); const vis = (1 - dive) * (k.u <= RU.uIn.value ? 1 : 0) + dive * Math.exp(-(((k.u - fU) * 9) ** 2));
    k.el.style.transform = `translate(${x}px,${y}px) translate(-50%,-50%)`; k.el.style.opacity = z < 1 ? vis * (1 - endV * (k.u < 1 ? 1 : 0)) : 0; });
  // 큰 소식 카드: 지금 보고 있는 시각 근처만 떠오른다
  let best = -1, bn = 0; if (mob) CARDS.forEach((c, i) => { const n = Math.abs(c.u - fU); if (best < 0 || n < bn) { best = i; bn = n; } });
  CARDS.forEach((c, ci) => { const near = (mob && ci !== best ? 0 : 1) * Math.exp(-(((c.u - fU) * (mob ? 11 : 8)) ** 2)) * dive, [x, y, z] = proj(c.anchor), dist = cam.position.distanceTo(c.anchor);
    const sc = clamp((mob ? 10 : 11) / dist, 0.5, 1.12); c.el.style.opacity = z < 1 ? near : 0; const hw = (mob ? 118 : 150) * sc + 14, cx = clamp(x, hw, w - hw); c.el.style.transform = `translate(${cx}px,${y}px) translate(-50%,-100%) scale(${sc}) translateY(${(1 - near) * 24}px)`;
    c.el.style.zIndex = Math.round(near * 10); c.ln.material.opacity = near * 0.5; c.pin.material.opacity = Math.max(near, 0.0); c.pin.scale.setScalar(0.6 + near); });
  // 위쪽 안내(내려다볼 때) / 시각 표시(따라갈 때) / 끝 카드
  sec.style.setProperty('--cap', (ss(0.02, 0.08, P) * (1 - ss(0.13, 0.19, P))).toFixed(3));
  sec.style.setProperty('--hud', (dive * (1 - endV)).toFixed(3)); sec.style.setProperty('--end', ss(0.9, 0.97, P).toFixed(3));
  if (ITEMS.length && dive > 0.05) { const hr = Math.min(23, Math.floor(fU * 24)), b = B[hr], tt = T0 + hr * 3600;
    const txt = `${hm(tt)}–${hm(tt + 3600)} · ${b.n} ${T('stories', '건')} · <b class="up">${b.u} ${T('positive', '호재')}</b> · <b class="down">${b.d} ${T('negative', '악재')}</b>`; if (hud._t !== txt) { hud._t = txt; hud.innerHTML = txt; }
    hud.style.setProperty('--fu', fU.toFixed(3)); }
});
