// V1~V3 공통: 입자 없이 셰이더 한 장(전체 화면 삼각형)으로 그리는 일식 심볼 오프닝.
// 심볼은 marks2 N3 와 같은 기하를 거리장(SDF)으로: 원반 c(46,54) r30 + 고리 = 원 A c(53,47) r31 의 굵기 3.2 띠에서 원 c(46,54) r34 안쪽을 뺀 것.
// 흐름: 어두운 첫 화면에서 연출 → 심볼이 옆(폰은 위)으로 비켜나며 글이 들어옴 → 스크롤하면 하늘이 밝아지고(낮) 심볼이 헤더 로고 자리로 날아가 합쳐진다.
export const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
export const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
export const mobile = () => innerWidth < 900;
export function bez(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const X = (t) => ((ax * t + bx) * t + cx) * t, Y = (t) => ((ay * t + by) * t + cy) * t, dX = (t) => (3 * ax * t + 2 * bx) * t + cx;
  return (x) => { if (x <= 0) return 0; if (x >= 1) return 1; let t = x; for (let i = 0; i < 8; i++) { const e = X(t) - x, d = dX(t); if (Math.abs(e) < 1e-6 || !d) break; t -= e / d; }
    let lo = 0, hi = 1; for (let i = 0; i < 20 && Math.abs(X(t) - x) > 1e-6; i++) { if (X(t) < x) lo = t; else hi = t; t = (lo + hi) / 2; } return Y(t); };
}
export const EASE = { out: bez(0.23, 1, 0.32, 1), inOut: bez(0.77, 0, 0.175, 1) };
export function spring(D = 1.4, bounce = 0.2) {
  const z = 1 - bounce, w = (2 * Math.PI * 1.6) / D, wd = w * Math.sqrt(Math.max(1e-4, 1 - z * z));
  return (p) => { if (p >= 1) return 1; const t = p * D; return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t)); };
}
export const GLSL = `
precision highp float;
uniform vec2 uRes; uniform float uTime, uS, uDay, uDpr; uniform vec2 uC;
const vec2 D0 = vec2(46., 54.), A0 = vec2(53., 47.);
vec2 markP() { vec2 f = gl_FragCoord.xy; f.y = uRes.y - f.y; return (f - uC) / uS * 100. + 50.; }
float sdDisc(vec2 p) { return length(p - D0) - 30.; }
float sdRing(vec2 p) { return max(abs(length(p - A0) - 31.) - 1.6, 34. - length(p - D0)); }
float fill(float d, float px) { return clamp(0.5 - d / px, 0., 1.); }
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float noise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y); }
float fbm(vec2 p) { float v = 0., a = .5; for (int i = 0; i < 5; i++) { v += a * noise(p); p = p * 2.03 + 17.1; a *= .5; } return v; }
vec3 aces(vec3 x) { return clamp((x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14), 0., 1.); }
const vec3 NIGHT = vec3(.012, .016, .028), DAY = vec3(.969, .976, .988), NAVY = vec3(.051, .145, .239);
// 낮 화면: 남색 단색 심볼
vec3 dayMark(vec2 p, float px) { float m = max(fill(sdDisc(p), px), fill(sdRing(p), px)); return mix(DAY, NAVY, m); }
// 낮으로: 고리 한가운데(빛이 남은 자리)에서 새벽빛이 둥글게 번져 화면을 덮는다. 경계는 부드럽고 살짝 밝다.
float dawn() { vec2 c = uC + (vec2(74.9, 25.1) - 50.) / 100. * uS; vec2 f = gl_FragCoord.xy; f.y = uRes.y - f.y;
  float soft = .35 * uRes.y, R = uDay * (length(uRes) + soft); return smoothstep(R, R - soft, length(f - c)); }
vec3 finish(vec3 night, vec2 p, float px) { float k = dawn(); vec3 n = aces(night);
  vec3 c = mix(n, dayMark(p, px), k) + vec3(.35, .32, .6) * k * (1. - k) * .5;
  return c + (hash(gl_FragCoord.xy + fract(uTime * 7.) * 91.) - .5) * mix(.045, .006, k); }
`;
export function engine({ frag, U = {} }) {
  const hero = document.getElementById('hero'), cv = document.createElement('canvas'); cv.className = 'vgl'; cv.setAttribute('aria-hidden', 'true'); hero.prepend(cv);
  document.body.classList.add('dk');
  const gl = cv.getContext('webgl', { antialias: false, premultipliedAlpha: false, powerPreference: 'high-performance' });
  const sh = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o); if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o)); return o; };
  const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, 'attribute vec2 a; void main(){ gl_Position = vec4(a, 0., 1.); }')); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, GLSL + frag)); gl.linkProgram(pr);
  if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
  gl.useProgram(pr); const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(pr, 'a'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const S = Object.assign({ uDay: 0 }, U), L = { k: 0, h: 0 }, ul = {};
  const u = (n) => (n in ul ? ul[n] : (ul[n] = gl.getUniformLocation(pr, n)));
  let W = 0, H = 0, dpr = 1;
  const size = () => { dpr = Math.min(devicePixelRatio || 1, mobile() ? 1.5 : 2); W = hero.clientWidth; H = hero.clientHeight; cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); gl.viewport(0, 0, cv.width, cv.height); };
  size(); addEventListener('resize', size);
  // 심볼 자리(css px): 가운데 → 옆(k) → 헤더 로고(h)
  const logo = document.querySelector('.hd .logo svg');
  function place() {
    const m = mobile(), c0 = { x: W / 2, y: H * (m ? 0.4 : 0.5), s: Math.min(W * (m ? 0.62 : 0.4), H * 0.5) };
    const c1 = m ? (() => { const s = Math.min(W * 0.7, H * 0.4); return { x: W / 2, y: 72 + (H * 0.57 - 72) / 2, s }; })() : { x: W / 2 + Math.min(330, W * 0.24), y: H / 2, s: Math.min(H * 0.6, W * 0.4) };
    const r = logo.getBoundingClientRect(), hr = hero.getBoundingClientRect(), c2 = { x: r.left + r.width / 2 - hr.left, y: r.top + r.height / 2 - hr.top, s: r.width };
    const k = L.k, h = L.h, lerp = (a, b, t) => a + (b - a) * t;
    const a = { x: lerp(c0.x, c1.x, k), y: lerp(c0.y, c1.y, k), s: lerp(c0.s, c1.s, k) };
    return { x: lerp(a.x, c2.x, h), y: lerp(a.y, c2.y, h), s: lerp(a.s, c2.s, h) };
  }
  let on = true; new IntersectionObserver((e) => { on = e[0].isIntersecting; }).observe(hero);
  const t0 = performance.now(), ticks = [];
  function frame(now) {
    requestAnimationFrame(frame); if (!on || document.hidden) return;
    const t = (now - t0) / 1000; ticks.forEach((f) => f(t));
    const P = place();
    gl.uniform2f(u('uRes'), cv.width, cv.height); gl.uniform1f(u('uTime'), t); gl.uniform1f(u('uDpr'), dpr);
    gl.uniform2f(u('uC'), P.x * dpr, P.y * dpr); gl.uniform1f(u('uS'), P.s * dpr);
    for (const k in S) { const v = S[k]; if (typeof v === 'number') gl.uniform1f(u(k), v); else if (v.length === 2) gl.uniform2f(u(k), v[0], v[1]); else gl.uniform3f(u(k), v[0], v[1], v[2]); }
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  requestAnimationFrame(frame);
  return { S, L, hero, cv, tick: (f) => ticks.push(f), place };
}
// 글 들어오기(심볼이 비켜난 뒤)
export function revealCopy(delay) {
  const els = document.querySelectorAll('.reveal');
  if (reduce) { gsap.to(els, { opacity: 1, duration: 0.4, delay: 0.1, onStart: () => els.forEach((e) => { e.style.transform = 'none'; e.style.filter = 'none'; }) }); return; }
  gsap.to(els, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.9, ease: EASE.out, stagger: 0.07, delay });
}
// 연출 타임라인 공통 마무리: 비켜나기 + 글, 클릭·키·휠이면 빨리 감기, 스크롤 장면(낮 + 헤더로 날아가기)
export function wrap(E, tl, { reframeAt }) {
  tl.to(E.L, { k: 1, duration: 1.1, ease: EASE.inOut }, reframeAt);
  revealCopy(reframeAt + 0.45);
  const ff = () => { if (tl.progress() < 1) tl.timeScale(5); };
  ['pointerdown', 'keydown', 'wheel', 'touchstart'].forEach((ev) => addEventListener(ev, ff, { once: true, passive: true }));
  if (reduce) tl.progress(1);
  gsap.registerPlugin(ScrollTrigger);
  const hd = document.body;
  const st = gsap.timeline({ scrollTrigger: { trigger: E.hero, start: 'top top', end: '+=110%', pin: true, scrub: 0.7, anticipatePin: 1 } });
  let dk = true; E.tick(() => { const d = E.S.uDay < 0.55; if (d !== dk) { dk = d; hd.classList.toggle('dk', d); } }); // 스크럽이 늦게 따라와도 헤더 색이 맞게 매 프레임 확인
  st.to('.copy', { y: -60, opacity: 0, duration: 0.3, ease: 'none' }, 0)
    .to(E.S, { uDay: 1, duration: 0.6, ease: 'none' }, 0.05)
    .to(E.L, { h: 1, duration: 0.55, ease: EASE.inOut }, 0.4)
    .to(E.cv, { opacity: 0, duration: 0.06, ease: 'none' }, 0.94)
    .fromTo('.hd .logo svg', { opacity: 0 }, { opacity: 1, duration: 0.06, ease: 'none', immediateRender: true }, 0.94); // 날아온 심볼이 헤더 로고가 된다
  // 스크롤 중에는 연출을 끝 상태로
  ScrollTrigger.create({ trigger: E.hero, start: 'top+=5 top', onEnter: () => { if (tl.progress() < 1) tl.progress(1); } });
}
export const T = (en, ko) => (DFI.lang() === 'ko' ? ko : en);
