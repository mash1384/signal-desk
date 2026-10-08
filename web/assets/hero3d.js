// 첫 화면 3D 지형: 최근 7일 BTC 1시간봉으로 산맥을 만든다. 높이는 변동성, 위에 떠 있는 빛줄기는 가격.
// 반응이 컸던 뉴스는 봉우리에 핀으로 꽂힌다. 스크롤하면 카메라가 낮게 날아가며 핀마다 멈추고, 끝에서 한 주 전체를 내려다본다.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { Line2 } from 'three/addons/lines/Line2.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { LineGeometry } from 'three/addons/lines/LineGeometry.js';

const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const seg = (p, a, b) => clamp((p - a) / (b - a));
const smooth = (t) => t * t * (3 - 2 * t);
const DAY = 86400, SPAN = 7 * DAY;
const L = 26, D = 14; // 지형 가로(시간) · 세로(깊이) 길이

function cssColor(str) {
  const c = document.createElement('canvas').getContext('2d');
  c.fillStyle = str; c.fillRect(0, 0, 1, 1);
  const d = c.getImageData(0, 0, 1, 1).data;
  return new THREE.Color().setRGB(d[0] / 255, d[1] / 255, d[2] / 255, THREE.SRGBColorSpace);
}

// 값 노이즈 + 프랙털 합: 실제 데이터 사이를 자연스러운 산 모양으로 채운다
function hash(x, y) { const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return s - Math.floor(s); }
function vnoise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x, y) { let s = 0, a = 0.5, f = 1; for (let i = 0; i < 5; i++) { s += a * vnoise(x * f, y * f); f *= 2.03; a *= 0.5; } return s; }
// 능선형 노이즈: 날카로운 산등성이와 골짜기가 생긴다
function ridged(x, y) { let s = 0, a = 0.55, f = 1; for (let i = 0; i < 5; i++) { let n = 1 - Math.abs(vnoise(x * f, y * f) * 2 - 1); n *= n; s += a * n; f *= 2.07; a *= 0.48; } return s; }

async function hourly(sym, start, end) {
  for (const h of ['https://data-api.binance.vision', 'https://api.binance.com']) {
    try {
      const r = await fetch(`${h}/api/v3/klines?symbol=${sym}USDT&interval=1h&startTime=${start * 1000}&endTime=${end * 1000}&limit=200`);
      if (!r.ok) continue;
      const rows = await r.json();
      if (rows.length > 24) return rows.map((k) => [Math.floor(k[0] / 1000) + 3600, +k[4]]);
    } catch (e) { /* 다음 주소 */ }
  }
  return null;
}

async function main() {
  const sec = document.getElementById('h3d');
  if (!sec) return;
  const pin = sec.querySelector('.pin'), canvas = sec.querySelector('canvas');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const small = () => innerWidth < 760;
  let renderer;
  try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' }); }
  catch (e) { sec.classList.add('no-webgl'); return; }
  sec.classList.add('has-webgl');
  if (!reduced) sec.classList.add('is-pinned');
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;

  const BG = cssColor('oklch(0.145 0.006 275)');
  const BASE = cssColor('oklch(0.3 0.014 275)');
  const LINE = cssColor('oklch(0.62 0.012 275)');
  const ACCENT = cssColor('oklch(0.92 0.2 120)');

  const info = (window.SIGNAL && window.SIGNAL.landing && window.SIGNAL.landing.terrain) || { stops: [], now: Date.now() / 1000 };
  const tEnd = Math.floor(Date.now() / 1000), tStart = tEnd - SPAN;
  const xOf = (t) => ((t - tStart) / SPAN - 0.5) * L;

  // 데이터: 가격(0~1)과 변동성(0~약 1.3)을 시간 함수로
  const rows = await hourly('BTC', tStart - 3 * 3600, tEnd);
  let priceAt = () => 0.5, volAt = (t) => 0.25 + 0.5 * fbm(t / 40000, 3.3) - 0.2;
  if (rows) {
    const ps = rows.map((r) => r[1]);
    const lo = Math.min(...ps), hi = Math.max(...ps), span = hi - lo || 1;
    const ret = rows.map((r, i) => (i ? Math.abs(Math.log(r[1] / rows[i - 1][1])) : 0));
    const sm = ret.map((_, i) => { let s = 0, w = 0; for (let j = -9; j <= 9; j++) { const k = i + j; if (k < 0 || k >= ret.length) continue; const g = Math.exp(-(j * j) / 18); s += ret[k] * g; w += g; } return s / w; });
    const sorted = [...sm].sort((a, b) => a - b), p95 = sorted[Math.floor(sorted.length * 0.95)] || 1e-6;
    const lerpAt = (arr) => (t) => {
      const f = (t - rows[0][0]) / 3600, i = clamp(Math.floor(f), 0, arr.length - 2), u = clamp(f - i, 0, 1);
      return arr[i] + (arr[i + 1] - arr[i]) * u;
    };
    const pn = ps.map((p) => (p - lo) / span), vn = sm.map((v) => Math.min(1.35, v / p95));
    priceAt = lerpAt(pn); volAt = lerpAt(vn);
  }
  const stopX = info.stops.map((s) => xOf(s.t0));
  const heightAt = (x, z) => {
    const t = tStart + (x / L + 0.5) * SPAN;
    const v = clamp(volAt(t), 0, 1.35);
    const env = Math.exp(-((z / 4.2) ** 2));
    let h = 0.1 + 0.6 * priceAt(t) * Math.exp(-((z / 3.5) ** 2));
    h += (0.7 + 2.6 * Math.pow(v, 1.2)) * ridged(x * 0.3 + 5.3, z * 0.38 + 1.7) * env;
    h += (fbm(x * 0.2 + 7, z * 0.26) - 0.4) * 1.5 * (0.45 + 0.55 * Math.exp(-((z / 6) ** 2)));
    h += (fbm(x * 1.6, z * 1.6 + 3) - 0.5) * 0.1;
    stopX.forEach((sx) => { h += 0.35 * Math.exp(-((x - sx) ** 2) / 0.25 - (z * z) / 0.8); });
    h -= 0.9 * smooth(seg(Math.abs(z), 4.5, 7));
    return h;
  };
  const PZ = -5.2; // 가격 빛줄기는 산맥 뒤 하늘선처럼
  const priceY = (x) => 2.4 + 1.7 * priceAt(tStart + (x / L + 0.5) * SPAN);

  const scene = new THREE.Scene();
  scene.background = BG;
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 120);

  // 지형 메시
  const rx = small() ? 220 : 340, rz = small() ? 96 : 150;
  const geo = new THREE.PlaneGeometry(L, D, rx, rz);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position, vol = new Float32Array(pos.count);
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i);
    pos.setY(i, heightAt(x, z));
    vol[i] = clamp(volAt(tStart + (x / L + 0.5) * SPAN), 0, 1.35) * Math.exp(-((z / 2.6) ** 2)) * clamp(pos.getY(i) / 1.6, 0, 1.2);
  }
  geo.setAttribute('aVol', new THREE.BufferAttribute(vol, 1));
  geo.computeVertexNormals();
  const tUniforms = {
    uBg: { value: BG }, uBase: { value: BASE }, uLine: { value: LINE }, uAccent: { value: ACCENT },
    uFogD: { value: 0.034 }, uDay: { value: L / 7 }, uX0: { value: -L / 2 }, uScan: { value: -99 },
  };
  const terrain = new THREE.Mesh(geo, new THREE.ShaderMaterial({
    uniforms: tUniforms,
    vertexShader: /* glsl */`
      attribute float aVol;
      varying vec3 vW; varying vec3 vN; varying float vVol;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vW = w.xyz; vN = normalize(mat3(modelMatrix) * normal); vVol = aVol;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uBg, uBase, uLine, uAccent; uniform float uFogD, uDay, uX0, uScan;
      varying vec3 vW; varying vec3 vN; varying float vVol;
      float grid(float v) { float d = fwidth(v); float f = abs(fract(v - 0.5) - 0.5); return 1.0 - smoothstep(d * 0.35, d * 1.25, f); }
      void main() {
        vec3 n = normalize(vN);
        vec3 v = normalize(cameraPosition - vW);
        float diff = clamp(dot(n, normalize(vec3(-0.35, 0.9, 0.4))), 0.0, 1.0);
        float rim = pow(1.0 - clamp(dot(n, v), 0.0, 1.0), 3.0);
        vec3 col = uBase * (0.25 + 0.95 * diff) + uBase * rim * 0.8;
        float hot = smoothstep(0.22, 0.85, vVol);
        vec3 lc = mix(uLine, uAccent, hot);
        float minor = grid(vW.y * 6.0), major = grid(vW.y * 1.2);
        col += lc * (minor * (0.2 + 0.5 * hot) + major * (0.38 + 0.6 * hot));
        col += uLine * grid((vW.x - uX0) / uDay) * 0.10;
        col += uAccent * hot * 0.06;
        col *= mix(0.55, 1.0, smoothstep(-0.6, 1.8, vW.y));
        col += uAccent * 0.35 * exp(-pow((vW.x - uScan) * 2.2, 2.0)) * (0.2 + hot);
        float d = length(vW - cameraPosition);
        col = mix(col, uBg, 1.0 - exp(-d * d * uFogD * uFogD));
        gl_FragColor = vec4(col, 1.0);
      }`,
  }));
  scene.add(terrain);

  // 가격 빛줄기와 그 아래 옅은 막
  const NP = 300, pricePts = [];
  for (let i = 0; i < NP; i++) { const x = -L / 2 + (i / (NP - 1)) * L; pricePts.push(x, priceY(x), PZ); }
  const lineMats = [];
  const fatLine = (pts, color, width, opacity) => {
    const g = new LineGeometry(); g.setPositions(pts);
    const m = new LineMaterial({ color, linewidth: width, transparent: true, opacity, depthWrite: false });
    lineMats.push(m);
    const l = new Line2(g, m); l.computeLineDistances(); scene.add(l); return l;
  };
  fatLine(pricePts, ACCENT, 2.4, 1);
  // 뉴스 핀: 봉우리에서 가격선까지 세로선, 양 끝에 빛나는 점, 바닥에는 퍼지는 고리
  const dotTex = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,0.8)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(c);
  })();
  const pins = stopX.map((x) => {
    const y0 = heightAt(x, 0), y1 = y0 + 1.5;
    const stem = fatLine([x, y0, 0, x, y1, 0], 0xffffff, 1.2, 0.6);
    const dots = [y0, y1].map((y, j) => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTex, color: j ? ACCENT : 0xffffff, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
      s.position.set(x, y, 0); s.scale.setScalar(j ? 0.2 : 0.16); scene.add(s); return s;
    });
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.18, 0.22, 48), new THREE.MeshBasicMaterial({ color: ACCENT, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    ring.rotation.x = -Math.PI / 2; ring.position.set(x, y0 + 0.02, 0); scene.add(ring);
    return { x, y0, y1, dots, ring, stem, on: 0 };
  });
  // 지금: 가격선 오른쪽 끝
  const nowDot = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTex, color: ACCENT, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
  nowDot.position.set(L / 2, priceY(L / 2 - 0.001), PZ); scene.add(nowDot);

  // 카메라 동선: 들어가기 → 핀마다 멈춤 → 위로 올라 전체 보기
  const SLOTS = [[0.22, 0.34], [0.44, 0.56], [0.66, 0.78]];
  const plan = () => {
    const m = small();
    const k = [];
    const intro = m ? { pos: [-L / 2 + 0.2, 4.4, 7.2], at: [-L / 2 + 5.5, -0.6, -1.5] } : { pos: [-L / 2 - 2.2, 1.6, 6.6], at: [-L / 2 + 7.5, 1.7, -1] };
    k.push({ p: 0, ...intro });
    k.push({ p: 0.12, pos: [intro.pos[0] + 1.4, intro.pos[1] - 0.2, intro.pos[2] - 0.6], at: intro.at });
    pins.forEach((pn, i) => {
      const [a, b] = SLOTS[i] || SLOTS[SLOTS.length - 1];
      const mid = pn.y0 + 0.6;
      const dz = m ? 5.6 : 5.4, dx = m ? -0.8 : -3.4, dy = m ? 1.4 : 0.35, ay = m ? -1.3 : 0;
      k.push({ p: a, pos: [pn.x + dx, mid + dy, dz], at: [pn.x + 0.4, mid + ay, -1] });
      k.push({ p: b, pos: [pn.x + dx + 0.6, mid + dy + 0.15, dz - 0.4], at: [pn.x + 0.6, mid + ay, -1] });
    });
    const over = m ? { pos: [0.5, 14, 19], at: [0.5, -1.2, -1] } : { pos: [0.5, 8, 17], at: [0.5, 1.8, 0] };
    k.push({ p: 0.9, ...over });
    k.push({ p: 1, pos: [over.pos[0], over.pos[1] + 0.4, over.pos[2] + 0.4], at: over.at });
    return k;
  };
  const v3 = (a) => new THREE.Vector3(a[0], a[1], a[2]);
  const camAt = new THREE.Vector3();
  const pose = (p) => {
    const k = plan();
    let i = 0;
    while (i < k.length - 2 && p > k[i + 1].p) i++;
    const t = smooth(clamp((p - k[i].p) / (k[i + 1].p - k[i].p)));
    camera.position.copy(v3(k[i].pos).lerp(v3(k[i + 1].pos), t));
    camAt.copy(v3(k[i].at).lerp(v3(k[i + 1].at), t));
  };

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.45, 0.35, 0.78);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  let W = 0, H = 0, dpr = Math.min(devicePixelRatio || 1, small() ? 1.75 : 2);
  const resize = () => {
    W = pin.clientWidth; H = pin.clientHeight;
    renderer.setPixelRatio(dpr); renderer.setSize(W, H, false);
    composer.setPixelRatio(dpr); composer.setSize(W, H);
    bloom.resolution.set(W * dpr * 0.5, H * dpr * 0.5);
    lineMats.forEach((m) => m.resolution.set(W * dpr, H * dpr));
    camera.aspect = W / H; camera.fov = small() ? 46 : 36; camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(pin);
  resize();

  const aim = { x: 0, y: 0 }, look = { x: 0, y: 0, vx: 0, vy: 0 };
  if (matchMedia('(hover: hover) and (pointer: fine)').matches) {
    sec.addEventListener('pointermove', (e) => { aim.x = e.clientX / innerWidth - 0.5; aim.y = e.clientY / innerHeight - 0.5; });
    sec.addEventListener('pointerleave', () => { aim.x = 0; aim.y = 0; });
  }

  const caps = [...sec.querySelectorAll('[data-beat]')];
  const labels = [...sec.querySelectorAll('.tpin')];
  const progress = () => {
    if (!sec.classList.contains('is-pinned')) return 0;
    const r = sec.getBoundingClientRect(), range = sec.offsetHeight - pin.offsetHeight;
    return clamp(-r.top / (range || 1));
  };
  const show = (el, v) => {
    el.style.opacity = v.toFixed(3);
    el.style.visibility = v < 0.01 ? 'hidden' : 'visible';
  };
  const tmp = new THREE.Vector3();

  let time = 0, last = 0, frames = 0, slow = 0, running = false, visible = true;
  const render = (dt) => {
    const p = progress();
    pose(p);
    look.vx += ((aim.x - look.x) * 26 - look.vx * 8) * dt; look.x += look.vx * dt;
    look.vy += ((aim.y - look.y) * 26 - look.vy * 8) * dt; look.y += look.vy * dt;
    camera.position.x += look.x * 0.8 + Math.sin(time * 0.35) * 0.06;
    camera.position.y += -look.y * 0.5 + Math.sin(time * 0.5) * 0.04;
    camera.lookAt(camAt);
    // 바닥을 훑는 빛: 처음엔 왼쪽에서 오른쪽으로 천천히 지나가고, 스크롤 중에는 카메라 앞을 비춘다
    tUniforms.uScan.value = p < 0.02 ? -L / 2 + ((time * 2.2) % (L + 8)) - 4 : -99;
    pins.forEach((pn, i) => {
      const ph = (time * 0.7 + i * 0.33) % 1;
      // 지금 보고 있는 핀만 또렷하게
      const hw = SLOTS[i], active = hw && p > hw[0] - 0.04 && p < hw[1] + 0.04 ? 1 : 0;
      const anyActive = SLOTS.some((w) => p > w[0] - 0.04 && p < w[1] + 0.04) && p < 0.82;
      pn.on += ((anyActive ? active : 1) - pn.on) * Math.min(1, dt * 6);
      const k = 0.3 + 0.7 * pn.on;
      pn.ring.scale.setScalar(1 + ph * 2.2);
      pn.ring.material.opacity = 0.6 * (1 - ph) * k;
      pn.stem.material.opacity = 0.6 * k;
      pn.dots[0].material.opacity = k;
      pn.dots[1].material.opacity = (0.8 + 0.2 * Math.sin(time * 3 + i)) * k;
      pn.dots[1].scale.setScalar(0.2 + 0.08 * pn.on);
    });
    nowDot.scale.setScalar(0.32 + 0.08 * Math.sin(time * 4));
    caps.forEach((el) => {
      const [a, b, c, d] = el.dataset.beat.split(',').map(Number);
      const v = Math.min(seg(p, a, b), 1 - seg(p, c, d));
      show(el, v);
      el.style.transform = v < 1 ? `translateY(${((1 - v) * 16).toFixed(1)}px)` : 'none';
    });
    labels.forEach((el, i) => {
      const hw = SLOTS[i], pn = pins[i];
      if (!hw || !pn) { show(el, 0); return; }
      const v = Math.min(seg(p, hw[0] - 0.03, hw[0] + 0.02), 1 - seg(p, hw[1] - 0.02, hw[1] + 0.03));
      show(el, v);
      if (v > 0 && !small()) {
        tmp.set(pn.x, pn.y1, 0).project(camera);
        const sx = (tmp.x * 0.5 + 0.5) * W, sy = (-tmp.y * 0.5 + 0.5) * H;
        const lw = el.offsetWidth, lh = el.offsetHeight;
        el.style.left = clamp(sx + 28, 16, W - lw - 16) + 'px';
        el.style.top = clamp(sy - lh - 18, 16, H - lh - 16) + 'px';
      }
      el.style.transform = v < 1 ? `translateY(${((1 - v) * 10).toFixed(1)}px)` : 'none';
    });
    composer.render();
  };
  const frame = (ts) => {
    if (!running) return;
    const dt = Math.min(0.05, last ? (ts - last) / 1000 : 0.016);
    last = ts; time += dt;
    if (frames < 45) { frames++; if (dt > 0.026) slow++; if (frames === 45 && slow > 24) { dpr = 1; bloom.enabled = false; resize(); } }
    render(dt);
    requestAnimationFrame(frame);
  };
  const start = () => { if (running || reduced || !visible || document.hidden) return; running = true; last = 0; requestAnimationFrame(frame); };
  const stop = () => { running = false; };
  new IntersectionObserver((en) => { visible = en[0].isIntersecting; if (visible) start(); else stop(); }).observe(sec);
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
  sec.classList.add('is-ready');
  if (reduced) { time = 3; render(0.016); } else start();
}

main();
