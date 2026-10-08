// 첫 화면 3D: 뉴스 입자(노이즈)가 유리 프리즘을 지나면 대부분 흩어지고, 일부만 시그널 빛줄기가 된다.
// 스크롤하면 카메라가 프리즘을 돌아 빛줄기 하나를 따라가고, 그 빛줄기가 실제 BTC 가격선으로 펴진다.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { Line2 } from 'three/addons/lines/Line2.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { LineGeometry } from 'three/addons/lines/LineGeometry.js';

const clamp = (v) => Math.max(0, Math.min(1, v));
const seg = (p, a, b) => clamp((p - a) / (b - a));
const ease = (t) => t * t * (3 - 2 * t);

// oklch 같은 CSS 색을 sRGB로 바꾼다(캔버스에 한 번 칠해 읽는다)
function cssColor(str) {
  const c = document.createElement('canvas').getContext('2d');
  c.fillStyle = str;
  c.fillRect(0, 0, 1, 1);
  const d = c.getImageData(0, 0, 1, 1).data;
  return new THREE.Color().setRGB(d[0] / 255, d[1] / 255, d[2] / 255, THREE.SRGBColorSpace);
}

async function candles(sym, start, end) {
  const hosts = ['https://data-api.binance.vision', 'https://api.binance.com'];
  for (const h of hosts) {
    try {
      const r = await fetch(`${h}/api/v3/klines?symbol=${sym}USDT&interval=1m&startTime=${start * 1000}&endTime=${end * 1000}&limit=1000`);
      if (!r.ok) continue;
      const rows = await r.json();
      if (rows.length > 5) return rows.map((k) => [Math.floor(k[0] / 1000), +k[4]]);
    } catch (e) { /* 다음 주소로 */ }
  }
  return null;
}

function main() {
  const sec = document.getElementById('h3d');
  if (!sec) return;
  const pin = sec.querySelector('.pin');
  const canvas = sec.querySelector('canvas');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const small = () => innerWidth < 760;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  } catch (e) {
    sec.classList.add('no-webgl');
    return;
  }
  sec.classList.add('has-webgl');
  if (!reduced) sec.classList.add('is-pinned');

  const BG = cssColor('oklch(0.155 0.006 275)');
  const ACCENT = cssColor('oklch(0.92 0.2 120)');
  const NOISE = cssColor('oklch(0.72 0.01 275)');

  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = BG;
  scene.fog = new THREE.FogExp2(BG, 0.035);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);

  // 프리즘: 정삼각형 단면을 깊이 방향으로 뽑고 모서리를 둥글린다
  const R = 1.25;
  const shape = new THREE.Shape();
  for (let i = 0; i < 3; i++) {
    const a = Math.PI / 2 + (i * Math.PI * 2) / 3;
    const x = Math.cos(a) * R, y = Math.sin(a) * R;
    if (i) shape.lineTo(x, y); else shape.moveTo(x, y);
  }
  shape.closePath();
  const pg = new THREE.ExtrudeGeometry(shape, { depth: 1.5, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.08, bevelSegments: 6, curveSegments: 1 });
  pg.center();
  const glass = new THREE.MeshPhysicalMaterial({
    color: 0xffffff, metalness: 0, roughness: 0, transmission: 1, thickness: 1.2, ior: 1.62, dispersion: 7,
    iridescence: 0.5, iridescenceIOR: 1.3, clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 2.2, specularIntensity: 1,
    attenuationColor: new THREE.Color(0xdfe6ff), attenuationDistance: 4,
  });
  const prism = new THREE.Mesh(pg, glass);
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(pg, 30), new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.18 }));
  const prismGroup = new THREE.Group();
  prismGroup.add(prism, edges);
  prismGroup.rotation.set(0.12, -0.42, 0);
  scene.add(prismGroup);

  // 프리즘 뒤의 은은한 빛판: 유리가 이 빛을 굴절시켜 '유리'로 읽히게 한다(불투명 목록이라 굴절 패스에 들어간다)
  const glowTex = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 256;
    const g = c.getContext('2d'), gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, 'rgba(255,255,255,0.55)');
    gr.addColorStop(0.25, 'rgba(214,245,90,0.28)');
    gr.addColorStop(0.6, 'rgba(214,245,90,0.06)');
    gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const backdrop = new THREE.Mesh(new THREE.PlaneGeometry(9, 9), new THREE.MeshBasicMaterial({ map: glowTex, blending: THREE.AdditiveBlending, transparent: false, depthWrite: false, toneMapped: false }));
  backdrop.position.set(0.6, 0.1, -4.5);
  scene.add(backdrop);

  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(-4, 5, 6);
  scene.add(key);

  // 뉴스 입자: 점으로 그리고, 움직임은 셰이더에서 시드값으로 계산한다
  const makeParticles = (count) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(count * 3), 3));
    const seeds = new Float32Array(count * 4);
    for (let i = 0; i < count * 4; i++) seeds[i] = Math.random();
    g.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 4));
    return g;
  };
  const pUniforms = {
    uTime: { value: 0 }, uSig: { value: 0.07 }, uFade: { value: 1 }, uPx: { value: 1 },
    uNoise: { value: NOISE }, uAccent: { value: ACCENT },
  };
  const pMat = new THREE.ShaderMaterial({
    uniforms: pUniforms,
    // 투명 목록이 아니라 불투명 목록에서 그려야 유리 굴절 패스에 함께 비친다
    transparent: false, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */`
      uniform float uTime, uSig, uPx;
      attribute vec4 aSeed;
      varying float vAlpha; varying float vS;
      void main() {
        float speed = mix(0.55, 1.15, fract(aSeed.x * 7.13));
        float L = 19.0;
        float t = fract(aSeed.x + uTime * speed / L);
        float x = -11.0 + t * L;
        float sig = step(aSeed.w, uSig);
        vec2 lane = (vec2(aSeed.y, aSeed.z) * 2.0 - 1.0) * vec2(3.0, 2.2);
        float pre = smoothstep(-11.0, 0.0, x);
        vec2 off = lane * (1.0 - 0.72 * pre * pre);
        float post = clamp(x / 8.0, 0.0, 1.0);
        float a = smoothstep(0.0, 0.06, t);
        if (x > 0.0) {
          if (sig > 0.5) {
            off = vec2((aSeed.y - 0.5) * 1.6 * post, (aSeed.z - 0.5) * 0.5 * post);
            a *= (1.0 - smoothstep(0.85, 1.0, post)) * smoothstep(0.7, 1.6, x);
          } else {
            vec2 d = normalize(lane + 0.001);
            off = lane * 0.28 + d * post * 9.0 + vec2(sin(aSeed.x * 40.0 + x), cos(aSeed.y * 40.0 + x)) * post;
            a *= 1.0 - smoothstep(0.0, 0.3, post);
          }
        }
        a *= smoothstep(0.7, 1.6, abs(x));
        vS = (x > 0.0) ? sig : 0.0;
        vAlpha = a;
        vec4 mv = modelViewMatrix * vec4(x, off.x, off.y, 1.0);
        float size = mix(0.022, 0.052, fract(aSeed.y * 5.7)) * (vS > 0.5 ? 1.6 : 1.0);
        gl_PointSize = uPx * size / -mv.z;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uNoise, uAccent; uniform float uFade;
      varying float vAlpha; varying float vS;
      void main() {
        float m = 1.0 - smoothstep(0.15, 0.5, length(gl_PointCoord - 0.5));
        vec3 col = mix(uNoise * 0.6, uAccent * 1.5, vS);
        gl_FragColor = vec4(col * m * vAlpha * uFade, 1.0);
      }`,
  });
  const particles = new THREE.Points(makeParticles(small() ? 1400 : 3200), pMat);
  particles.frustumCulled = false;
  scene.add(particles);

  // 시그널 빛줄기: 프리즘 오른쪽에서 부채꼴로 나간다. 가운데 하나가 나중에 가격선이 된다
  const N = 140, X0 = 0.9, X1 = 8.4;
  const beamEnds = [-1.15, -0.55, 0, 0.6, 1.2];
  const beams = beamEnds.map((ye, i) => {
    const pts = [];
    for (let k = 0; k < N; k++) {
      const u = k / (N - 1);
      pts.push(X0 + u * (X1 - X0), ye * u, (i - 2) * 0.12 * u);
    }
    const geo = new LineGeometry();
    geo.setPositions(pts);
    const mat = new LineMaterial({ color: ACCENT, linewidth: i === 2 ? 3 : 1.6, transparent: true, opacity: i === 2 ? 0.95 : 0.55, blending: THREE.AdditiveBlending, depthWrite: false });
    const line = new Line2(geo, mat);
    line.computeLineDistances();
    scene.add(line);
    return { line, geo, mat, pts: Float32Array.from(pts) };
  });
  const hero = beams[2];
  let pricePts = null, t0x = null;
  const t0Line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, -1.6, 0), new THREE.Vector3(0, 1.6, 0)]),
    new THREE.LineDashedMaterial({ color: 0xffffff, dashSize: 0.08, gapSize: 0.08, transparent: true, opacity: 0 }));
  t0Line.computeLineDistances();
  scene.add(t0Line);

  const info = (window.SIGNAL && window.SIGNAL.landing && window.SIGNAL.landing.story) || null;
  if (info) {
    const from = info.ts - 1800, to = Math.min(Math.floor(Date.now() / 1000), info.ts + 7200);
    candles(info.asset, from, to).then((rows) => {
      if (!rows) return;
      const ps = rows.map((r) => r[1]);
      const lo = Math.min(...ps), hi = Math.max(...ps), span = hi - lo || 1;
      const out = new Float32Array(N * 3);
      for (let k = 0; k < N; k++) {
        const u = k / (N - 1);
        const ts = from + u * (to - from);
        let j = rows.findIndex((r) => r[0] >= ts);
        if (j < 0) j = rows.length - 1;
        out[k * 3] = X0 + u * (X1 - X0);
        out[k * 3 + 1] = ((rows[j][1] - lo) / span - 0.5) * 2.6;
        out[k * 3 + 2] = 0;
      }
      pricePts = out;
      t0x = X0 + ((info.ts - from) / (to - from)) * (X1 - X0);
      t0Line.position.x = t0x;
    });
  }

  // 카메라 경로: 정면 → 프리즘을 돌아 접근 → 가격선을 정면으로
  const keys = () => {
    const lift = H && H / W < 1.45 ? 0.9 : 0; // 세로가 짧은 폰은 프리즘을 더 위로
    return small()
    ? [{ p: 0, pos: [0.4, -0.2, 18], at: [0.8, -2.6 - lift, 0] }, { p: 0.5, pos: [2.8, 0.4, 14], at: [1.6, -2.0 - lift, 0] }, { p: 1, pos: [4.8, -0.4, 13.5], at: [4.7, -2.2 - lift, 0] }]
    : [{ p: 0, pos: [0, 0.4, 11], at: [-1.6, 0.1, 0] }, { p: 0.5, pos: [3.4, 1.3, 7.8], at: [1.2, 0.1, 0] }, { p: 1, pos: [5.4, 0.5, 8.8], at: [4.2, 0.1, 0] }];
  };
  const v3 = (a) => new THREE.Vector3(a[0], a[1], a[2]);
  const camAt = new THREE.Vector3();
  const pose = (p) => {
    const k = keys();
    let i = 0;
    while (i < k.length - 2 && p > k[i + 1].p) i++;
    const t = ease(clamp((p - k[i].p) / (k[i + 1].p - k[i].p)));
    camera.position.copy(v3(k[i].pos).lerp(v3(k[i + 1].pos), t));
    camAt.copy(v3(k[i].at).lerp(v3(k[i + 1].at), t));
  };

  // 후처리: 빛줄기에만 은은한 번짐
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.85, 0.55, 0.62);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  let W = 0, H = 0, dpr = Math.min(devicePixelRatio || 1, small() ? 1.5 : 2);
  const resize = () => {
    W = pin.clientWidth; H = pin.clientHeight;
    renderer.setPixelRatio(dpr);
    renderer.setSize(W, H, false);
    composer.setPixelRatio(dpr);
    composer.setSize(W, H);
    bloom.resolution.set(W * dpr * 0.5, H * dpr * 0.5);
    beams.forEach((b) => b.mat.resolution.set(W * dpr, H * dpr));
    pUniforms.uPx.value = H * dpr / (2 * Math.tan(THREE.MathUtils.degToRad(small() ? 40 : 32) / 2));
    camera.aspect = W / H;
    camera.fov = small() ? 40 : 32;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(pin);
  resize();

  // 커서를 따라 카메라가 살짝 움직인다(스프링)
  const aim = { x: 0, y: 0 }, look = { x: 0, y: 0, vx: 0, vy: 0 };
  if (matchMedia('(hover: hover) and (pointer: fine)').matches) {
    sec.addEventListener('pointermove', (e) => { aim.x = (e.clientX / innerWidth - 0.5); aim.y = (e.clientY / innerHeight - 0.5); });
    sec.addEventListener('pointerleave', () => { aim.x = 0; aim.y = 0; });
  }

  const caps = [...sec.querySelectorAll('[data-beat]')];
  const progress = () => {
    if (!sec.classList.contains('is-pinned')) return 0;
    const r = sec.getBoundingClientRect(), range = sec.offsetHeight - pin.offsetHeight;
    return clamp(-r.top / (range || 1));
  };
  const showEl = (el, v) => {
    el.style.opacity = v.toFixed(3);
    el.style.visibility = v < 0.01 ? 'hidden' : 'visible';
    el.style.transform = v < 1 ? `translateY(${((1 - v) * 16).toFixed(1)}px)` : 'none';
  };

  let time = 0, last = 0, frames = 0, slow = 0, running = false, visible = true;
  const frame = (ts) => {
    if (!running) return;
    const dt = Math.min(0.05, last ? (ts - last) / 1000 : 0.016);
    last = ts;
    time += dt;
    // 처음 40프레임이 느리면 화질을 낮춘다
    if (frames < 40) { frames++; if (dt > 0.026) slow++; if (frames === 40 && slow > 20) { dpr = 1; bloom.enabled = false; resize(); } }
    render(dt);
    requestAnimationFrame(frame);
  };
  const render = (dt) => {
    const p = progress();
    pose(p);
    look.vx += ((aim.x - look.x) * 30 - look.vx * 9) * dt; look.x += look.vx * dt;
    look.vy += ((aim.y - look.y) * 30 - look.vy * 9) * dt; look.y += look.vy * dt;
    camera.position.x += look.x * 0.6;
    camera.position.y -= look.y * 0.4;
    camera.lookAt(camAt);
    prismGroup.rotation.y = -0.42 + Math.sin(time * 0.25) * 0.08 + p * 0.5;
    prismGroup.rotation.x = 0.12 + Math.sin(time * 0.31) * 0.04;
    pUniforms.uTime.value = time;
    // 장면 1→2: 노이즈가 줄고 시그널 비율이 조금 늘어난다. 장면 3: 입자가 물러난다
    pUniforms.uSig.value = 0.06 + seg(p, 0.25, 0.55) * 0.05;
    pUniforms.uFade.value = 1 - seg(p, 0.7, 0.95) * 0.75;
    backdrop.material.opacity = 1; backdrop.material.color.setScalar(1 - seg(p, 0.6, 0.85) * 0.85);
    const morph = pricePts ? ease(seg(p, 0.6, 0.88)) : 0;
    beams.forEach((b, i) => {
      if (b === hero) return;
      b.mat.opacity = 0.55 * (1 - seg(p, 0.55, 0.75));
    });
    if (pricePts) {
      const out = new Float32Array(N * 3);
      for (let k = 0; k < N * 3; k++) out[k] = hero.pts[k] + (pricePts[k] - hero.pts[k]) * morph;
      hero.geo.setPositions(out);
      t0Line.material.opacity = 0.5 * seg(p, 0.8, 0.92);
    }
    caps.forEach((el) => {
      const [a, b, c, d] = el.dataset.beat.split(',').map(Number);
      showEl(el, Math.min(seg(p, a, b), 1 - seg(p, c, d)));
    });
    composer.render();
  };
  const start = () => { if (running || reduced || !visible || document.hidden) return; running = true; last = 0; requestAnimationFrame(frame); };
  const stop = () => { running = false; };
  new IntersectionObserver((en) => { visible = en[0].isIntersecting; if (visible) start(); else stop(); }).observe(sec);
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
  if (reduced) {
    // 움직임 줄이기: 한 장면만 그린다
    time = 6;
    render(0.016);
  } else {
    start();
  }
}

main();
