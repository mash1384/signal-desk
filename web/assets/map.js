// 맵(SIGNAL Map): 뉴스 → 코인 관계도. 코인은 로고 배지, 뉴스는 점, 선은 그 뉴스 뒤 잰 가격 반응.
// 바탕은 WebGL 점 격자로, 코인 둘레가 등락만큼 빛나고 뉴스를 고르면 그 코인에서 파문이 번진다.
// 재생 대신 아래 막대(시간대별 뉴스 무게)를 끌어 구간을 고르고, ← → 로 무거운 뉴스를 차례로 본다.
// data/map.json(15분마다 갱신)을 1분마다 다시 읽고, 코인 시세는 바이낸스 공개 실시간 시세로 갱신한다.
const S = window.SIGNAL || {};
const BASE = S.base || '/';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
const WIN = { '1h': 3600, '6h': 21600, '24h': 86400, '7d': 604800 };
const WIN_KO = { '1h': '1시간', '6h': '6시간', '24h': '24시간', '7d': '7일' };
const BINS = { '1h': 12, '6h': 36, '24h': 48, '7d': 56 };
const CAT = { crypto: '크립토', ai: 'AI', macro: '매크로' };
const ETYPE = { fomc: 'FOMC·연준', cpi: '물가 지표', jobs: '고용 지표', etf: 'ETF', listing: '상장·상폐', hack: '해킹·사고',
  regulation: '규제·소송', 'ai-model': 'AI 모델·제품', earnings: '실적', other: '기타' };
const GRADE_OK = { all: () => true, mid: (g) => g === '중' || g === '강', strong: (g) => g === '강' };
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (v, d = 2) => (v == null || !isFinite(v) ? '–' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d) + '%');
const two = (n) => (n < 10 ? '0' : '') + n;
const kst = (ts) => { const d = new Date((ts + 9 * 3600) * 1000); return { mo: d.getUTCMonth() + 1, d: d.getUTCDate(), h: d.getUTCHours(), m: d.getUTCMinutes() }; };
const when = (ts) => { const k = kst(ts); return `${two(k.mo)}.${two(k.d)} ${two(k.h)}:${two(k.m)}`; };
const hhmm = (ts) => { const k = kst(ts); return `${two(k.h)}:${two(k.m)}`; };
const nowSec = () => Date.now() / 1000;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const hitR = (h) => (h['1h'] != null ? h['1h'] : h['15m'] != null ? h['15m'] : h['24h']);
const easeOut = (p) => 1 - Math.pow(1 - p, 3);
const easeInOut = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
const hash = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967296; };
const maxZ = (n) => n.h.reduce((m, h) => Math.max(m, Math.abs(h.z || 0)), 0);
const zNorm = (z) => clamp((z - 0.5) / 4.5, 0, 1);

// CSS 색(oklch 포함)을 [r,g,b](0~255)로 바꾼다
const probe = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
const rgbOf = (css) => { probe.clearRect(0, 0, 1, 1); probe.fillStyle = '#000'; probe.fillStyle = css; probe.fillRect(0, 0, 1, 1); const d = probe.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2]]; };
const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${clamp(a, 0, 1).toFixed(3)})`;

// ---------- 바탕 점 격자(WebGL) ----------
function makeField(canvas) {
  const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false, antialias: false });
  if (!gl) return null;
  const NS = 16, NW = 6;
  const vs = `
attribute vec2 a_pos;
uniform vec2 u_res; uniform float u_dpr; uniform float u_size;
uniform vec4 u_src[${NS}]; uniform vec4 u_wave[${NW}];
uniform vec3 u_base; uniform vec3 u_up; uniform vec3 u_down;
varying vec4 v_col;
void main() {
  vec2 p = a_pos;
  float up = 0.0, dn = 0.0, neu = 0.0;
  for (int i = 0; i < ${NS}; i++) {
    vec4 s = u_src[i];
    if (s.z <= 0.0) continue;
    vec2 d = p - s.xy;
    float g = exp(-dot(d, d) / (2.0 * s.z * s.z));
    neu += g;
    if (s.w > 0.0) up += g * s.w; else dn -= g * s.w;
  }
  for (int i = 0; i < ${NW}; i++) {
    vec4 w = u_wave[i];
    if (w.w == 0.0) continue;
    float d = length(p - w.xy);
    float g = exp(-pow((d - w.z) / 34.0, 2.0)) + 0.35 * exp(-pow((d - w.z * 0.62) / 26.0, 2.0));
    if (w.w > 0.0) up += g * w.w; else dn -= g * w.w;
  }
  float e = clamp(up + dn, 0.0, 1.0);
  vec3 tint = (up + dn) > 0.0001 ? (u_up * up + u_down * dn) / (up + dn) : u_base;
  vec3 col = mix(u_base, tint, clamp(e * 1.6, 0.0, 1.0));
  vec2 uv = p / u_res;
  float vig = smoothstep(0.0, 0.14, uv.x) * smoothstep(0.0, 0.14, 1.0 - uv.x) * smoothstep(0.0, 0.18, uv.y) * smoothstep(0.0, 0.18, 1.0 - uv.y);
  float a = (0.11 + 0.08 * clamp(neu, 0.0, 1.0) + 0.85 * e) * (0.3 + 0.7 * vig);
  v_col = vec4(col, a);
  gl_PointSize = u_size * u_dpr * (1.0 + 0.8 * e);
  gl_Position = vec4(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0, 0.0, 1.0);
}`;
  const fs = `
precision mediump float;
varying vec4 v_col;
void main() {
  float d = length(gl_PointCoord - 0.5);
  gl_FragColor = vec4(v_col.rgb, v_col.a * smoothstep(0.5, 0.3, d));
}`;
  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
  let prog;
  try {
    prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
  } catch (e) { return null; }
  gl.useProgram(prog);
  const U = (n) => gl.getUniformLocation(prog, n);
  const u = { res: U('u_res'), dpr: U('u_dpr'), size: U('u_size'), src: U('u_src'), wave: U('u_wave'), base: U('u_base'), up: U('u_up'), down: U('u_down') };
  const buf = gl.createBuffer();
  const loc = gl.getAttribLocation(prog, 'a_pos');
  gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  let count = 0, W = 0, H = 0, dpr = 1;
  const src = new Float32Array(NS * 4), wave = new Float32Array(NW * 4);
  return {
    NS, NW,
    resize(w, h, d, gap) {
      W = w; H = h; dpr = d;
      canvas.width = Math.round(w * d); canvas.height = Math.round(h * d);
      const pts = [];
      const ox = (w % gap) / 2, oy = (h % gap) / 2;
      for (let y = oy; y <= h; y += gap) for (let x = ox; x <= w; x += gap) pts.push(x, y);
      count = pts.length / 2;
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(pts), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      gl.viewport(0, 0, canvas.width, canvas.height);
    },
    colors(base, up, down) { gl.uniform3f(u.base, ...base.map((v) => v / 255)); gl.uniform3f(u.up, ...up.map((v) => v / 255)); gl.uniform3f(u.down, ...down.map((v) => v / 255)); },
    draw(sources, waves, size) {
      src.fill(0); wave.fill(0);
      sources.slice(0, NS).forEach((s, i) => src.set([s.x, s.y, s.sigma, s.amp], i * 4));
      waves.slice(0, NW).forEach((w, i) => wave.set([w.x, w.y, w.r, w.amp], i * 4));
      gl.uniform2f(u.res, W, H); gl.uniform1f(u.dpr, dpr); gl.uniform1f(u.size, size);
      gl.uniform4fv(u.src, src); gl.uniform4fv(u.wave, wave);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.POINTS, 0, count);
    },
  };
}

function main() {
  const root = $('#mapx');
  if (!root) return;
  const frame = $('.mapx__frame', root), stage = $('#mapStage'), canvas = $('#mapCanvas'), ctx = canvas.getContext('2d');
  const panel = $('#mapPanel'), tip = $('#mapTip'), status = $('#mapStatus');
  const bCanvas = $('#mapBrushCanvas'), bctx = bCanvas.getContext('2d');
  const field = makeField($('#mapField'));
  let data = null, W = 0, H = 0, dpr = 1, narrow = false;
  const view = { win: '24h', cats: new Set(['crypto', 'ai', 'macro']), grade: 'all', range: null, sel: null, hover: null };
  const live = {};                 // sym -> {price, chg24}
  const cam = { x: 0, y: 0, k: 1 };
  let camTween = null, userCam = false;
  let graph = { coins: {}, news: [], ranked: [], links: [] };
  const posCache = new Map();      // 뉴스 id -> 마지막 자리(필터를 바꿔도 같은 뉴스는 같은 자리 근처에 남는다)
  const shown = new Map();         // 뉴스 id -> 처음 그린 시각(ms)
  const moves = new Map();         // 뉴스 id -> {fx, fy, at} 자리 옮김
  const pulses = [];               // 뉴스 → 코인으로 흐르는 빛(한 번)
  const waves = [];                // 코인에서 번지는 파문(한 번)
  let watch = [];
  try { watch = JSON.parse(localStorage.getItem('signal-watch')) || []; } catch (e) { watch = []; }

  // 색: 맵 틀은 테마와 상관없이 어둡다
  let C = {};
  const readColors = () => {
    const cs = getComputedStyle(frame);
    const v = (n) => cs.getPropertyValue(n).trim();
    C = { up: rgbOf(v('--up')), down: rgbOf(v('--down')), text: rgbOf(v('--text')), text2: rgbOf(v('--text-2')), text3: rgbOf(v('--text-3')),
      accent: rgbOf(v('--accent')), bg: rgbOf(v('--bg')), elev: rgbOf(v('--bg-elev')), dot: rgbOf('oklch(0.78 0.012 270)') };
    if (field) field.colors(C.dot, C.up, C.down);
    sprites.clear();
  };
  const sprites = new Map();
  const glow = (c) => {
    const key = c.join(',');
    if (sprites.has(key)) return sprites.get(key);
    const s = document.createElement('canvas'); s.width = s.height = 128;
    const g = s.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, rgba(c, 0.55)); gr.addColorStop(0.35, rgba(c, 0.18)); gr.addColorStop(1, rgba(c, 0));
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    sprites.set(key, s);
    return s;
  };

  // 코인 로고(흰색 단색 SVG)
  const icons = {};
  const icon = (sym) => {
    if (!icons[sym]) {
      const img = new Image();
      icons[sym] = { img, ok: false };
      img.onload = () => { icons[sym].ok = true; schedule(); };
      img.src = root.dataset.coins + sym + '.svg';
    }
    return icons[sym].ok ? icons[sym].img : null;
  };

  // ---------- 데이터 ----------
  const assets = () => (data ? data.assets.filter((a) => a.pos) : []);
  const bySym = (s) => assets().find((a) => a.s === s);
  const chgOf = (a) => (view.win === '24h' && live[a.s] && live[a.s].chg24 != null ? live[a.s].chg24 : a.chg[view.win]);
  const priceOf = (a) => (live[a.s] ? live[a.s].price : a.price);
  const span = () => { const t1 = nowSec(); return [t1 - WIN[view.win], t1]; };
  const passes = (n, useRange = true) => {
    const [a, b] = span();
    if (n.t <= a || n.t > b + 60 || !view.cats.has(n.c)) return false;
    if (useRange && view.range && (n.t < view.range[0] || n.t >= view.range[1])) return false;
    return true;
  };
  const measuredOK = (n) => !n.p && n.h.length && n.h.some((h) => GRADE_OK[view.grade](h.g));
  const linksOf = (n) => n.h.filter((h) => graph.coins[h.s]).map((h) => ({ s: h.s, h, z: Math.abs(h.z || 0), zn: zNorm(Math.abs(h.z || 0)), r: hitR(h) }));

  // ---------- 배치 ----------
  // 뉴스는 가장 크게 움직인 코인(대표 코인) 둘레에 해바라기 나선으로 놓인다: 반응이 클수록 코인에 가깝다.
  // 대표 코인 말고 다른 코인과의 반응은 옅은 선으로 잇는다. 코인 자리는 상관(BTC와 같이 움직이는 정도)으로 정하고,
  // 뉴스 무리가 겹치지 않도록 코인끼리 밀어낸다.
  const WORLD = 300, GOLD = Math.PI * (3 - Math.sqrt(5));
  function buildGraph() {
    const list = assets();
    const maxQ = Math.max(1, ...list.map((a) => a.qv || 0));
    const coins = {};
    list.forEach((a) => {
      const rad = Math.hypot(a.pos[0], a.pos[1]), ang = Math.atan2(a.pos[1], a.pos[0]);
      const rr = a.s === 'BTC' ? 0 : 0.52 + 0.48 * clamp((rad - 0.4) / 0.6, 0, 1);
      coins[a.s] = { a, ang, x: Math.cos(ang) * rr * WORLD, y: Math.sin(ang) * rr * WORLD, r: 15 + 21 * Math.sqrt((a.qv || 0) / maxQ), sat: [] };
    });
    const prevC = graph.coins || {};
    graph.coins = coins;
    const ranked = data.news.filter((n) => passes(n) && measuredOK(n)).sort((x, y) => maxZ(y) - maxZ(x) || y.t - x.t);
    const cap = narrow ? 36 : 72;
    const pick = ranked.slice(0, cap);
    if (view.sel && view.sel.kind === 'news' && !pick.some((n) => n.id === view.sel.id)) {
      const n = data.news.find((m) => m.id === view.sel.id);
      if (n && !n.p && n.h.length) pick.push(n);
    }
    const nodes = pick.map((n) => {
      const links = linksOf(n);
      if (!links.length) return null;
      const z = maxZ(n), top = links.slice().sort((p, q) => q.z - p.z)[0];
      return { n, id: n.id, links, z, zn: zNorm(z), r: 2.3 + 4.4 * zNorm(z), sign: top.r < 0 ? -1 : 1, home: top.s, x: 0, y: 0 };
    }).filter(Boolean);
    nodes.forEach((d) => coins[d.home].sat.push(d));
    // 나선 자리(코인 기준 상대 좌표). 코인 이름표가 있는 아래쪽 가까운 자리는 비운다.
    Object.values(coins).forEach((c) => {
      c.sat.sort((p, q) => q.z - p.z || q.n.t - p.n.t);
      const rot = c.a.s === 'BTC' ? -Math.PI / 2 : c.ang;
      let k = 0, maxR = c.r + 10;
      c.sat.forEach((d) => {
        for (;;) {
          const rad = c.r + 13 + 9.2 * Math.sqrt(k + 0.5), ang = rot + k * GOLD;
          k++;
          const ox = Math.cos(ang) * rad, oy = Math.sin(ang) * rad;
          const under = oy > 0 && Math.abs(ox) < c.r * 0.9 + 22 && oy < c.r + 30;
          if (under) continue;
          d.ox = ox; d.oy = oy; maxR = Math.max(maxR, rad + d.r);
          break;
        }
      });
      c.R = Math.max(maxR, c.r + 30) + 10;
    });
    // 코인 자리: BTC 무리와 겹치지 않게 바깥으로, 이웃 무리끼리도 밀어낸다
    const btc = coins.BTC;
    const others = Object.values(coins).filter((c) => c !== btc);
    const separate = () => { for (let it = 0; it < 80; it++) {
      for (let i = 0; i < others.length; i++) for (let j = i + 1; j < others.length; j++) {
        const a = others[i], b = others[j];
        const dx = b.x - a.x, dy = b.y - a.y, dist = Math.hypot(dx, dy) || 0.01, need = a.R + b.R + 16;
        if (dist < need) { const m = (need - dist) / 2, ux = dx / dist, uy = dy / dist; a.x -= ux * m; a.y -= uy * m; b.x += ux * m; b.y += uy * m; }
      }
      others.forEach((c) => {
        const dist = Math.hypot(c.x, c.y) || 1, need = (btc ? btc.R : 0) + c.R + 18;
        if (dist < need) { c.x *= need / dist; c.y *= need / dist; }
      });
    } };
    separate();
    // 화면 비율에 맞춰 가로(또는 세로)로 펼친다. 상관 배치의 방향은 그대로 두고 폭만 바꾼다.
    const box = Object.values(coins).reduce((b, c) => [Math.min(b[0], c.x - c.R), Math.min(b[1], c.y - c.R), Math.max(b[2], c.x + c.R), Math.max(b[3], c.y + c.R)], [Infinity, Infinity, -Infinity, -Infinity]);
    const p0 = pad(), want = (W - p0.l - p0.r) / Math.max(1, H - p0.t - p0.b), have = (box[2] - box[0]) / Math.max(1, box[3] - box[1]);
    const stretch = clamp((want / have) * 0.9, 0.85, 2.2);
    if (Math.abs(stretch - 1) > 0.05) { Object.values(coins).forEach((c) => { c.x *= stretch; }); separate(); }
    nodes.forEach((d) => { const c = coins[d.home]; d.x = c.x + d.ox; d.y = c.y + d.oy; });
    Object.entries(coins).forEach(([sym, c]) => {
      const p = prevC[sym];
      if (p && !reduced && Math.hypot(p.x - c.x, p.y - c.y) > 2) moves.set('coin:' + sym, { fx: p.x, fy: p.y, at: performance.now() });
    });
    // 자리가 바뀐 뉴스는 옮겨 가는 모습을 보여 준다
    const ms = performance.now();
    nodes.forEach((d) => {
      const c = posCache.get(d.id);
      if (c && !reduced && Math.hypot(c.x - d.x, c.y - d.y) > 2) moves.set(d.id, { fx: c.x, fy: c.y, at: ms });
      posCache.set(d.id, { x: d.x, y: d.y });
      if (!shown.has(d.id)) shown.set(d.id, reduced ? 0 : ms);
    });
    graph.news = nodes;
    graph.ranked = ranked;
    graph.rank = new Map(nodes.slice().sort((p, q) => q.z - p.z || q.n.t - p.n.t).map((d, i) => [d.id, i]));
  }

  // ---------- 카메라 ----------
  const pad = () => (narrow ? { t: 74, b: 14, l: 14, r: 14 } : { t: 84, b: 120, l: 40, r: 70 });
  const fitCam = () => {
    const pts = [...Object.values(graph.coins).map((c) => [c.x, c.y, Math.max(c.R || 0, c.r + 30)]), ...graph.news.map((d) => [d.x, d.y, d.r + 6])];
    if (!pts.length) return { x: 0, y: 0, k: 1 };
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    pts.forEach(([x, y, r]) => { x0 = Math.min(x0, x - r); y0 = Math.min(y0, y - r); x1 = Math.max(x1, x + r); y1 = Math.max(y1, y + r); });
    const p = pad();
    const k = clamp(Math.min((W - p.l - p.r) / (x1 - x0), (H - p.t - p.b) / (y1 - y0)), 0.35, 2.4);
    // 화면 여백(위 도구 막대·아래 시간 막대)을 빼고 남은 영역의 가운데에 맞춘다
    const cx = (x0 + x1) / 2 - ((p.l - p.r) / 2) / k, cy = (y0 + y1) / 2 - ((p.t - p.b) / 2) / k;
    return { x: cx, y: cy, k };
  };
  const moveCam = (to, animate = true) => {
    if (!animate || reduced) { Object.assign(cam, to); camTween = null; schedule(); return; }
    camTween = { from: { ...cam }, to, at: performance.now(), dur: 520 };
    schedule();
  };
  const sx = (x) => W / 2 + (x - cam.x) * cam.k;
  const sy = (y) => H / 2 + (y - cam.y) * cam.k;
  const wx = (px) => cam.x + (px - W / 2) / cam.k;
  const wy = (py) => cam.y + (py - H / 2) / cam.k;
  const rk = () => Math.pow(cam.k, 0.7);

  // ---------- 그리기 ----------
  let raf = 0;
  const schedule = () => { if (!raf) raf = requestAnimationFrame(frameTick); };
  function frameTick(ms) {
    raf = 0;
    let busy = false;
    if (camTween) {
      const p = clamp((ms - camTween.at) / camTween.dur, 0, 1), e = easeInOut(p);
      ['x', 'y', 'k'].forEach((k) => { cam[k] = camTween.from[k] + (camTween.to[k] - camTween.from[k]) * e; });
      if (p >= 1) camTween = null; else busy = true;
    }
    busy = draw(ms) || busy;
    if (busy) schedule();
  }

  const focusSet = () => {
    const f = view.hover || view.sel;
    if (!f) return null;
    const news = new Set(), coins = new Set();
    if (f.kind === 'news') {
      news.add(f.id);
      const d = graph.news.find((x) => x.id === f.id);
      if (d) d.links.forEach((l) => coins.add(l.s));
    } else if (f.kind === 'coin') {
      coins.add(f.id);
      graph.news.forEach((d) => { if (d.links.some((l) => l.s === f.id)) news.add(d.id); });
    }
    return { news, coins, kind: f.kind, id: f.id };
  };

  const nodePos = (d, ms) => {
    const m = moves.get(d.id);
    if (!m) return [d.x, d.y];
    const p = clamp((ms - m.at) / 600, 0, 1);
    if (p >= 1) { moves.delete(d.id); return [d.x, d.y]; }
    const e = easeInOut(p);
    return [m.fx + (d.x - m.fx) * e, m.fy + (d.y - m.fy) * e];
  };
  const ctrl = (x0, y0, x1, y1, seed) => {
    const mx = (x0 + x1) / 2, my = (y0 + y1) / 2, dx = x1 - x0, dy = y1 - y0;
    const bend = (seed - 0.5) * 0.5;
    return [mx - dy * bend, my + dx * bend];
  };
  const qpt = (x0, y0, cx, cy, x1, y1, t) => [(1 - t) * (1 - t) * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) * (1 - t) * y0 + 2 * (1 - t) * t * cy + t * t * y1];

  function draw(ms) {
    if (!data) return false;
    let busy = false;
    const f = focusSet();
    const k = rk();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const coins = graph.coins;
    const cpos = {};
    Object.entries(coins).forEach(([s, c]) => {
      const m = moves.get('coin:' + s);
      let x = c.x, y = c.y;
      if (m) {
        const p = clamp((ms - m.at) / 600, 0, 1), e = easeInOut(p);
        if (p >= 1) moves.delete('coin:' + s); else { busy = true; x = m.fx + (c.x - m.fx) * e; y = m.fy + (c.y - m.fy) * e; }
      }
      cpos[s] = [sx(x), sy(y), c.r * k];
    });

    // 같이 움직이는 코인 사이: 아주 옅은 선
    ctx.lineWidth = 1;
    data.links.forEach((l) => {
      const a = cpos[l.a], b = cpos[l.b];
      if (!a || !b) return;
      const s = clamp((l.c - data.link_min) / (1 - data.link_min), 0, 1);
      ctx.strokeStyle = rgba(C.text3, (f ? 0.02 : 0.05) + 0.06 * s);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    });

    // 뉴스 → 코인 선
    const npos = new Map();
    graph.news.forEach((d) => {
      const [x, y] = nodePos(d, ms);
      if (moves.has(d.id)) busy = true;
      const born = shown.get(d.id) || 0, ap = born ? clamp((ms - born) / 450, 0, 1) : 1;
      if (ap < 1) busy = true;
      npos.set(d.id, [sx(x), sy(y), d.r * k, easeOut(ap)]);
    });
    ctx.lineCap = 'round';
    const drawEdges = (on) => graph.news.forEach((d) => {
      const isOn = !!f && f.news.has(d.id);
      if (on !== isOn) return;
      const [x, y, , ap] = npos.get(d.id);
      d.links.forEach((l) => {
        if (f && f.kind === 'coin' && on && l.s !== f.id) return;
        if (!on && l.s === d.home) return;
        const [cx, cy, cr] = cpos[l.s];
        const col = l.r >= 0 ? C.up : C.down;
        const [qx, qy] = ctrl(x, y, cx, cy, hash(d.id + l.s));
        const base = on ? 0.9 : f ? 0.04 : 0.07 + 0.22 * l.zn;
        const g = ctx.createLinearGradient(x, y, cx, cy);
        g.addColorStop(0, rgba(col, base * 0.25 * ap)); g.addColorStop(1, rgba(col, base * ap));
        ctx.strokeStyle = g;
        ctx.lineWidth = (on ? 1.3 : 0.7) + (on ? 1.4 : 0.9) * l.zn;
        // 선 끝은 코인 테두리에서 멈춘다
        const ang = Math.atan2(cy - qy, cx - qx);
        const ex = cx - Math.cos(ang) * (cr + 5), ey = cy - Math.sin(ang) * (cr + 5);
        ctx.beginPath(); ctx.moveTo(x, y); ctx.quadraticCurveTo(qx, qy, ex, ey); ctx.stroke();
      });
    });
    drawEdges(false);
    drawEdges(true);

    // 흐르는 빛(고른 뉴스에서 코인으로 한 번)
    ctx.globalCompositeOperation = 'lighter';
    for (let i = pulses.length - 1; i >= 0; i--) {
      const p = pulses[i], t = (ms - p.at) / 650;
      if (t < 0) { busy = true; continue; }
      const d = graph.news.find((x) => x.id === p.id), c = cpos[p.s];
      if (!d || !c || t >= 1) {
        pulses.splice(i, 1);
        if (d && c && t >= 1) waves.push({ s: p.s, amp: p.amp, at: ms });
        continue;
      }
      busy = true;
      const [x, y] = npos.get(d.id);
      const [qx, qy] = ctrl(x, y, c[0], c[1], hash(d.id + p.s));
      const e = easeOut(t);
      for (let j = 0; j < 6; j++) {
        const tt = Math.max(0, e - j * 0.035);
        const [px, py] = qpt(x, y, qx, qy, c[0], c[1], tt);
        const s = (14 - j * 1.6) * (0.6 + 0.6 * Math.abs(p.amp));
        ctx.globalAlpha = (1 - j / 6) * (1 - t * 0.3);
        ctx.drawImage(glow(p.col), px - s, py - s, s * 2, s * 2);
      }
      ctx.globalAlpha = 1;
    }
    ctx.globalCompositeOperation = 'source-over';

    // 뉴스 점
    const placed = [];
    graph.news.forEach((d) => {
      const [x, y, r, ap] = npos.get(d.id);
      const dim = f && !f.news.has(d.id);
      const col = d.sign < 0 ? C.down : C.up;
      const hot = f && f.news.has(d.id) && f.kind === 'news';
      ctx.globalAlpha = (dim ? 0.22 : 1) * ap;
      if (d.zn > 0.45 && !dim) {
        ctx.globalCompositeOperation = 'lighter';
        const s = r * 3.6;
        ctx.drawImage(glow(col), x - s, y - s, s * 2, s * 2);
        ctx.globalCompositeOperation = 'source-over';
      }
      ctx.fillStyle = rgba(col, 0.55 + 0.45 * d.zn);
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
      if (d.zn > 0.6) { ctx.fillStyle = 'rgba(255,255,255,0.85)'; ctx.beginPath(); ctx.arc(x, y, Math.max(0.9, r * 0.32), 0, Math.PI * 2); ctx.fill(); }
      const rank = graph.rank.get(d.id);
      if (rank != null && rank < 5 && !dim && !placed.some(([px, py]) => Math.abs(px - x) < 22 && Math.abs(py - y) < 13)) {
        placed.push([x, y]);
        ctx.font = '600 9.5px "Geist Mono", monospace'; ctx.textAlign = 'left';
        ctx.fillStyle = rgba(C.text2, 0.85);
        ctx.fillText(two(rank + 1), x + r + 3, y - r - 1);
      }
      if (hot) {
        ctx.strokeStyle = rgba(C.text, 0.95); ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(x, y, r + 4, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.globalAlpha = 1;
    });

    // 코인 배지
    Object.entries(coins).forEach(([s, c]) => {
      const [x, y, r] = cpos[s];
      const chg = chgOf(c.a);
      const col = chg == null ? C.text3 : chg >= 0 ? C.up : C.down;
      const mag = chg == null ? 0 : clamp(Math.abs(chg) / 8, 0, 1);
      const dim = f && !f.coins.has(s);
      const on = f && f.kind === 'coin' && f.id === s;
      ctx.globalAlpha = dim ? 0.38 : 1;
      // 은은한 빛
      ctx.globalCompositeOperation = 'lighter';
      const gs = r * (2.1 + 1.2 * mag);
      ctx.globalAlpha = (dim ? 0.1 : 0.22 + 0.4 * mag);
      ctx.drawImage(glow(col), x - gs, y - gs, gs * 2, gs * 2);
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = dim ? 0.38 : 1;
      // 원판(유리 느낌: 위쪽이 살짝 밝다)
      const g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.45, r * 0.1, x, y, r);
      g.addColorStop(0, 'rgba(58,60,72,1)'); g.addColorStop(1, 'rgba(22,23,30,1)');
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = on ? rgba(C.text, 0.95) : 'rgba(255,255,255,0.14)'; ctx.lineWidth = on ? 1.5 : 1;
      ctx.stroke();
      // 둘레 막대: 등락폭(8%가 한 바퀴)
      const rr = r + 4.5;
      ctx.strokeStyle = 'rgba(255,255,255,0.07)'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(x, y, rr, 0, Math.PI * 2); ctx.stroke();
      if (mag > 0) {
        ctx.strokeStyle = rgba(col, 0.95); ctx.lineWidth = 2; ctx.lineCap = 'round';
        const a0 = -Math.PI / 2, a1 = a0 + (chg >= 0 ? 1 : -1) * Math.max(0.06, mag * Math.PI * 2);
        ctx.beginPath(); ctx.arc(x, y, rr, a0, a1, chg < 0); ctx.stroke();
      }
      // 로고
      const img = icon(s);
      const is = r * 1.02;
      if (img) ctx.drawImage(img, x - is / 2, y - is / 2, is, is);
      else { ctx.fillStyle = rgba(C.text, 0.9); ctx.font = `700 ${Math.round(clamp(r * 0.5, 9, 14))}px Geist, sans-serif`; ctx.textAlign = 'center'; ctx.fillText(s, x, y + 4); }
      // 이름표
      const ty = y + rr + 15;
      ctx.textAlign = 'center';
      ctx.font = '600 11.5px Geist, Pretendard, sans-serif';
      const t1 = s, t2 = pct(chg);
      ctx.font = '600 11px "Geist Mono", monospace';
      const w2 = ctx.measureText(t2).width;
      ctx.font = '700 11.5px Geist, Pretendard, sans-serif';
      const w1 = ctx.measureText(t1).width;
      const tw = w1 + 6 + w2;
      ctx.fillStyle = 'rgba(14,15,20,0.72)';
      roundRect(x - tw / 2 - 7, ty - 11, tw + 14, 18, 9); ctx.fill();
      ctx.textAlign = 'left';
      ctx.fillStyle = rgba(C.text, 0.95); ctx.fillText(t1, x - tw / 2, ty + 2);
      ctx.font = '600 11px "Geist Mono", monospace';
      ctx.fillStyle = chg == null ? rgba(C.text3, 1) : rgba(col, 1); ctx.fillText(t2, x - tw / 2 + w1 + 6, ty + 2);
      if (watch.includes(s)) { ctx.fillStyle = rgba(C.accent, 1); ctx.beginPath(); ctx.arc(x + r * 0.72, y - r * 0.72, 3.5, 0, Math.PI * 2); ctx.fill(); }
      ctx.globalAlpha = 1;
    });

    // 고른 뉴스: 코인 쪽 선 끝에 잰 값
    if (f && f.kind === 'news') {
      const d = graph.news.find((x) => x.id === f.id);
      if (d) {
        const [x, y] = npos.get(d.id);
        d.links.forEach((l) => {
          const [cx, cy, cr] = cpos[l.s];
          const [qx, qy] = ctrl(x, y, cx, cy, hash(d.id + l.s));
          let [px, py] = qpt(x, y, qx, qy, cx, cy, 0.55);
          if (Math.hypot(px - cx, py - cy) < cr + 22) {
            // 선이 짧으면(대표 코인 바로 옆) 값을 뉴스 점 바깥쪽에 붙인다
            const dx = x - cx, dy = y - cy, dd = Math.hypot(dx, dy) || 1;
            px = x + (dx / dd) * 26; py = y + (dy / dd) * 22;
          }
          const txt = `${pct(l.r)}${l.h.g ? ' · ' + l.h.g : ''}`;
          ctx.font = '600 11px "Geist Mono", Pretendard, monospace';
          const tw = ctx.measureText(txt).width;
          ctx.fillStyle = 'rgba(14,15,20,0.86)';
          roundRect(px - tw / 2 - 7, py - 10, tw + 14, 20, 10); ctx.fill();
          ctx.strokeStyle = rgba(l.r >= 0 ? C.up : C.down, 0.5); ctx.lineWidth = 1; ctx.stroke();
          ctx.fillStyle = rgba(l.r >= 0 ? C.up : C.down, 1); ctx.textAlign = 'center';
          ctx.fillText(txt, px, py + 4);
        });
      }
    }

    // 바탕 점 격자
    if (field) {
      const src = Object.entries(coins).map(([s, c]) => {
        const [x, y, r] = cpos[s];
        const chg = chgOf(c.a);
        const dim = f && !f.coins.has(s);
        const m = chg == null ? 0 : clamp(Math.abs(chg) / 6, 0, 1);
        return { x, y, sigma: r * 1.5 + 26, amp: (chg != null && chg < 0 ? -1 : 1) * (0.1 + 0.55 * m) * (dim ? 0.35 : 1) };
      });
      const wv = [];
      for (let i = waves.length - 1; i >= 0; i--) {
        const w = waves[i], p = (ms - w.at) / 1700;
        if (p >= 1) { waves.splice(i, 1); continue; }
        busy = true;
        const c = cpos[w.s];
        if (!c) continue;
        wv.push({ x: c[0], y: c[1], r: c[2] + 8 + easeOut(p) * 300, amp: w.amp * Math.pow(1 - p, 1.3) });
      }
      field.draw(src, wv, narrow ? 1.7 : 1.9);
    }
    return busy;
  }
  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  // ---------- 고르기·가리키기 ----------
  const pick = (px, py, touch) => {
    const k = rk(), slop = touch ? 12 : 4;
    let best = null;
    graph.news.forEach((d) => {
      const [x, y] = [sx(d.x), sy(d.y)];
      const dist = Math.hypot(x - px, y - py);
      if (dist <= Math.max(d.r * k + slop, touch ? 16 : 8) && (!best || dist < best.d)) best = { kind: 'news', id: d.id, d: dist };
    });
    if (best) return best;
    Object.entries(graph.coins).forEach(([s, c]) => {
      const dist = Math.hypot(sx(c.x) - px, sy(c.y) - py);
      if (dist <= c.r * k + 6 && (!best || dist < best.d)) best = { kind: 'coin', id: s, d: dist };
    });
    return best;
  };
  const sameSel = (a, b) => (!a && !b) || (a && b && a.kind === b.kind && a.id === b.id);
  const setHover = (h) => {
    const next = h ? { kind: h.kind, id: h.id } : null;
    if (sameSel(view.hover, next)) return;
    view.hover = next;
    $$('.mnews', panel).forEach((el) => el.classList.toggle('is-hot', !!next && el.dataset.pick === next.kind + ':' + next.id));
    showTip();
    schedule();
  };
  const showTip = () => {
    const h = view.hover;
    if (!h || !finePointer || sameSel(h, view.sel)) { tip.hidden = true; return; }
    let html = '', x = 0, y = 0;
    if (h.kind === 'news') {
      const d = graph.news.find((n) => n.id === h.id);
      if (!d) { tip.hidden = true; return; }
      const n = d.n;
      html = `<p class="mtip__meta">${esc(CAT[n.c] || '')} · ${esc(n.src || '')} · ${when(n.t)}</p><p class="mtip__t">${esc(n.title)}</p>`
        + `<p class="mtip__r">${d.links.slice().sort((a, b) => b.z - a.z).slice(0, 3).map((l) => `${esc(l.s)} <span class="${l.r >= 0 ? 'up' : 'down'}">${pct(l.r)}</span>${l.h.g ? ' ' + esc(l.h.g) : ''}`).join(' · ')}</p>`;
      x = sx(d.x); y = sy(d.y);
    } else {
      const c = graph.coins[h.id];
      if (!c) { tip.hidden = true; return; }
      const cnt = graph.ranked.filter((n) => n.h.some((x) => x.s === h.id)).length;
      html = `<p class="mtip__t">${esc(h.id)} <span class="${(chgOf(c.a) || 0) >= 0 ? 'up' : 'down'}">${pct(chgOf(c.a))}</span></p><p class="mtip__meta">${WIN_KO[view.win]} 등락 · 잰 뉴스 ${cnt}건 · 눌러서 보기</p>`;
      x = sx(c.x); y = sy(c.y) - c.r * rk();
    }
    tip.innerHTML = html;
    tip.hidden = false;
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    const left = clamp(x - tw / 2, 8, W - tw - 8), top = y - th - 16 < 70 ? y + 18 : y - th - 16;
    tip.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
  };

  const select = (s, opts = {}) => {
    const next = s ? { kind: s.kind, id: s.id } : null;
    if (sameSel(view.sel, next) && !opts.force) return;
    view.sel = next;
    if (next && next.kind === 'news') {
      if (!graph.news.some((d) => d.id === next.id)) { buildGraph(); }
      const d = graph.news.find((x) => x.id === next.id);
      if (d && !reduced) {
        const ms = performance.now();
        d.links.forEach((l, i) => pulses.push({ id: d.id, s: l.s, col: l.r >= 0 ? C.up : C.down, amp: (l.r >= 0 ? 1 : -1) * (0.8 + 0.4 * l.zn), at: ms + i * 90 }));
      }
      if (d && opts.center) {
        const [x, y] = [d.x, d.y];
        const p = pad();
        const vx = (W - p.l - p.r) / 2 + p.l, vy = (H - p.t - p.b) / 2 + p.t;
        const outside = sx(x) < p.l + 40 || sx(x) > W - p.r - 40 || sy(y) < p.t + 30 || sy(y) > H - p.b - 30;
        if (outside) moveCam({ x: x - (vx - W / 2) / cam.k, y: y - (vy - H / 2) / cam.k, k: cam.k });
      }
    }
    showTip(); renderPanel(); syncUrl(); schedule();
  };

  // 마우스: 끌어서 옮기기, Ctrl/⌘ + 휠(트랙패드 오므리기)로 확대. 터치는 페이지 스크롤을 막지 않도록 누르기만 받는다.
  let drag = null, tap = null;
  canvas.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'touch') { tap = { x: e.clientX, y: e.clientY, at: performance.now() }; return; }
    if (e.button !== 0) return;
    drag = { x: e.clientX, y: e.clientY, cx: cam.x, cy: cam.y, moved: false };
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove', (e) => {
    const r = canvas.getBoundingClientRect(), px = e.clientX - r.left, py = e.clientY - r.top;
    if (drag) {
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) > 4) { drag.moved = true; canvas.classList.add('is-drag'); setHover(null); }
      if (drag.moved) { camTween = null; userCam = true; cam.x = drag.cx - dx / cam.k; cam.y = drag.cy - dy / cam.k; schedule(); }
      return;
    }
    if (e.pointerType === 'touch') return;
    const h = pick(px, py, false);
    canvas.classList.toggle('is-hot', !!h);
    setHover(h);
  });
  const endDrag = (e) => {
    if (e.pointerType === 'touch') {
      // 누르기만 받는다(끌면 페이지가 스크롤된다)
      if (tap && Math.hypot(e.clientX - tap.x, e.clientY - tap.y) < 10 && performance.now() - tap.at < 600) {
        const r = canvas.getBoundingClientRect();
        const h = pick(e.clientX - r.left, e.clientY - r.top, true);
        select(h && sameSel(h, view.sel) ? null : h);
      }
      tap = null;
      return;
    }
    if (!drag) return;
    const moved = drag.moved;
    drag = null; canvas.classList.remove('is-drag');
    if (!moved) {
      const r = canvas.getBoundingClientRect();
      const h = pick(e.clientX - r.left, e.clientY - r.top, false);
      select(h && sameSel(h, view.sel) ? null : h);
    }
  };
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', () => { drag = null; tap = null; canvas.classList.remove('is-drag'); });
  canvas.addEventListener('pointerleave', () => { if (!drag) { setHover(null); canvas.classList.remove('is-hot'); } });
  canvas.addEventListener('wheel', (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    const r = canvas.getBoundingClientRect(), px = e.clientX - r.left, py = e.clientY - r.top;
    const bx = wx(px), by = wy(py);
    cam.k = clamp(cam.k * Math.exp(-e.deltaY * 0.01), 0.3, 4);
    cam.x = bx - (px - W / 2) / cam.k; cam.y = by - (py - H / 2) / cam.k;
    camTween = null; userCam = true; schedule();
  }, { passive: false });
  $$('[data-zoom]', root).forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.zoom === 'fit') { userCam = false; moveCam(fitCam()); return; }
    userCam = true;
    moveCam({ x: cam.x, y: cam.y, k: clamp(cam.k * (b.dataset.zoom === 'in' ? 1.35 : 1 / 1.35), 0.3, 4) });
  }));

  // 키보드: ← → 로 무거운 뉴스를 차례로, Esc로 풀기
  const order = () => graph.news.slice().sort((a, b) => b.z - a.z || b.n.t - a.n.t).map((d) => d.id);
  const step = (dir) => {
    const ids = order();
    if (!ids.length) return;
    const cur = view.sel && view.sel.kind === 'news' ? ids.indexOf(view.sel.id) : -1;
    const next = cur < 0 ? (dir > 0 ? 0 : ids.length - 1) : clamp(cur + dir, 0, ids.length - 1);
    if (next === cur) return;
    select({ kind: 'news', id: ids[next] }, { center: true });
  };
  stage.addEventListener('keydown', (e) => {
    if (e.target !== stage) return;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); step(1); }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); step(-1); }
    else if (e.key === 'Escape') select(null);
  });

  // ---------- 시간 막대(구간 고르기) ----------
  let bins = [], bDrag = null, BW = 0, BH = 0;
  const binsOf = () => {
    const [a, b] = span(), nb = BINS[view.win], w = (b - a) / nb;
    const out = Array.from({ length: nb }, (_, i) => ({ t0: a + i * w, t1: a + (i + 1) * w, v: 0, n: 0, up: 0, dn: 0 }));
    data.news.forEach((n) => {
      if (!passes(n, false) || !measuredOK(n)) return;
      const i = Math.floor((n.t - a) / w);
      if (i < 0 || i >= nb) return;
      const z = Math.min(6, maxZ(n));
      out[i].v += z; out[i].n += 1;
      const top = n.h.slice().sort((p, q) => Math.abs(q.z || 0) - Math.abs(p.z || 0))[0];
      if (top && hitR(top) < 0) out[i].dn += z; else out[i].up += z;
    });
    return out;
  };
  function drawBrush() {
    if (!data || !BW) return;
    bins = binsOf();
    bctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    bctx.clearRect(0, 0, BW, BH);
    const nb = bins.length, gap = nb > 40 ? 2 : 3, bw = (BW - gap * (nb - 1)) / nb;
    const mx = Math.max(1, ...bins.map((b) => b.v));
    const [a, b] = span();
    const sel = view.sel && view.sel.kind === 'news' ? data.news.find((n) => n.id === view.sel.id) : null;
    bins.forEach((bn, i) => {
      const x = i * (bw + gap), h = Math.max(2, (bn.v / mx) * (BH - 4));
      const inR = !view.range || (bn.t1 > view.range[0] && bn.t0 < view.range[1]);
      const hasSel = sel && sel.t >= bn.t0 && sel.t < bn.t1;
      const share = bn.v ? bn.up / bn.v : 0.5;
      const col = hasSel ? C.accent : share >= 0.5 ? C.up : C.down;
      bctx.fillStyle = bn.v ? rgba(col, inR ? (hasSel ? 1 : 0.32 + 0.5 * Math.abs(share - 0.5) * 2 * 0.6) : 0.1) : rgba(C.text3, inR ? 0.22 : 0.08);
      const y = BH - h;
      bctx.beginPath();
      const rr = Math.min(2, bw / 2);
      bctx.moveTo(x, BH); bctx.lineTo(x, y + rr); bctx.arcTo(x, y, x + rr, y, rr); bctx.lineTo(x + bw - rr, y); bctx.arcTo(x + bw, y, x + bw, y + rr, rr); bctx.lineTo(x + bw, BH); bctx.closePath();
      bctx.fill();
    });
    if (view.range) {
      const X = (t) => ((t - a) / (b - a)) * BW;
      const x0 = X(view.range[0]), x1 = X(view.range[1]);
      bctx.fillStyle = 'rgba(255,255,255,0.05)'; bctx.fillRect(x0, 0, x1 - x0, BH);
      bctx.fillStyle = rgba(C.text, 0.85);
      bctx.fillRect(x0 - 1, 0, 2, BH); bctx.fillRect(x1 - 1, 0, 2, BH);
    }
  }
  const brushLabel = () => {
    const lbl = $('#mapRangeLabel'), reset = $('#mapRangeReset');
    const total = graph.ranked.length, shownN = graph.news.length;
    const [a, b] = span();
    const head = view.range ? `<b>${when(view.range[0])} – ${hhmm(view.range[1])}</b>` : `<b>최근 ${WIN_KO[view.win]}</b>`;
    lbl.innerHTML = `${head} · 잰 뉴스 ${total}건${total > shownN ? ` 중 반응 큰 ${shownN}개` : ''}`;
    reset.hidden = !view.range;
    const ticks = 4, parts = [];
    for (let i = 0; i <= ticks; i++) { const t = a + ((b - a) * i) / ticks; parts.push(i === ticks ? '지금' : view.win === '7d' ? `${two(kst(t).mo)}.${two(kst(t).d)}` : hhmm(t)); }
    $('#mapAxis').innerHTML = parts.map((p) => `<span>${p}</span>`).join('');
    bCanvas.setAttribute('aria-valuetext', view.range ? `${when(view.range[0])}부터 ${when(view.range[1])}까지` : `최근 ${WIN_KO[view.win]} 전체`);
  };
  const tAt = (px) => { const [a, b] = span(); return a + clamp(px / BW, 0, 1) * (b - a); };
  const snap = (t) => { const [a, b] = span(), w = (b - a) / BINS[view.win]; return a + Math.round((t - a) / w) * w; };
  bCanvas.addEventListener('pointerdown', (e) => {
    const r = bCanvas.getBoundingClientRect();
    bDrag = { x: e.clientX - r.left, moved: false };
    bCanvas.setPointerCapture(e.pointerId);
  });
  bCanvas.addEventListener('pointermove', (e) => {
    if (!bDrag) return;
    const r = bCanvas.getBoundingClientRect(), x = e.clientX - r.left;
    if (Math.abs(x - bDrag.x) < 4 && !bDrag.moved) return;
    bDrag.moved = true;
    const t0 = snap(tAt(Math.min(x, bDrag.x))), t1 = snap(tAt(Math.max(x, bDrag.x)));
    if (t1 > t0) { view.range = [t0, t1]; drawBrush(); brushLabel(); }
  });
  bCanvas.addEventListener('pointerup', (e) => {
    if (!bDrag) return;
    const r = bCanvas.getBoundingClientRect();
    if (!bDrag.moved) {
      // 막대 하나를 누르면 그 칸만
      const [a, b] = span(), w = (b - a) / BINS[view.win];
      const i = Math.floor((tAt(e.clientX - r.left) - a) / w);
      const t0 = a + i * w, t1 = t0 + w;
      view.range = view.range && Math.abs(view.range[0] - t0) < 1 && Math.abs(view.range[1] - t1) < 1 ? null : [t0, t1];
    }
    bDrag = null;
    applyFilters();
  });
  bCanvas.addEventListener('keydown', (e) => {
    const [a, b] = span(), w = (b - a) / BINS[view.win];
    if (e.key === 'Escape') { view.range = null; applyFilters(); return; }
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();
    const dir = e.key === 'ArrowRight' ? 1 : -1;
    const cur = view.range || [b - w, b];
    const len = cur[1] - cur[0];
    let t0 = clamp(cur[0] + dir * w, a, b - len);
    view.range = [t0, t0 + len];
    applyFilters();
  });
  $('#mapRangeReset').addEventListener('click', () => { view.range = null; applyFilters(); });

  // ---------- 설정 ----------
  function applyFilters(refit = true) {
    if (!data) return;
    buildGraph();
    if (view.sel && view.sel.kind === 'news' && !graph.news.some((d) => d.id === view.sel.id)) view.sel = null;
    if (refit && !userCam) moveCam(fitCam());
    drawBrush(); brushLabel(); renderPanel(); renderList(); setStatus(); syncUrl(); schedule();
  }
  $$('.mseg__b', root).forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.win) { view.win = b.dataset.win; view.range = null; $$('[data-win]', root).forEach((x) => x.setAttribute('aria-pressed', x === b ? 'true' : 'false')); }
    if (b.dataset.grade) { view.grade = b.dataset.grade; $$('[data-grade]', root).forEach((x) => x.setAttribute('aria-pressed', x === b ? 'true' : 'false')); }
    if (b.dataset.cat) {
      const on = view.cats.has(b.dataset.cat);
      if (on && view.cats.size === 1) return;
      on ? view.cats.delete(b.dataset.cat) : view.cats.add(b.dataset.cat);
      b.setAttribute('aria-pressed', on ? 'false' : 'true');
    }
    userCam = false;
    applyFilters();
  }));
  const setStatus = () => {
    if (!data) return;
    const pend = data.news.filter((n) => n.p && passes(n, false)).length;
    status.textContent = `LIVE · ${hhmm(nowSec())} KST${pend ? ` · 반응 재는 중 ${pend}건` : ''}`;
  };

  // ---------- 패널 ----------
  panel.addEventListener('click', (e) => {
    const b = e.target.closest('[data-pick]');
    if (b) { const [kind, id] = b.dataset.pick.split(':'); select({ kind, id }, { center: true }); return; }
    const st = e.target.closest('[data-step]');
    if (st) { step(Number(st.dataset.step)); return; }
    if (e.target.closest('[data-close]')) select(null);
  });
  panel.addEventListener('pointerover', (e) => {
    if (!finePointer) return;
    const b = e.target.closest('[data-pick]');
    if (b) { const [kind, id] = b.dataset.pick.split(':'); view.hover = { kind, id }; schedule(); }
  });
  panel.addEventListener('pointerout', (e) => {
    if (!finePointer) return;
    const b = e.target.closest('[data-pick]');
    if (b && !b.contains(e.relatedTarget)) { view.hover = null; schedule(); }
  });
  const newsRow = (n, i) => {
    const top = n.h.slice().sort((a, b) => Math.abs(b.z || 0) - Math.abs(a.z || 0))[0];
    const r = top ? hitR(top) : null, z = maxZ(n);
    return `<li><button type="button" class="mnews" data-pick="news:${esc(n.id)}"><span class="mnews__n">${two(i + 1)}</span><span class="mnews__meta"><span class="chip cat cat--${esc(n.c)}">${CAT[n.c]}</span><span>${esc(n.src || '')} · ${when(n.t)}</span></span>`
      + `<span class="mnews__t">${esc(n.title)}</span>${top ? `<span class="mnews__r ${r >= 0 ? 'up' : 'down'}">${esc(top.s)} ${pct(r)}${top.g ? ' · ' + esc(top.g) : ''}${z ? ' · z ' + z.toFixed(1) : ''}</span>` : ''}</button></li>`;
  };
  const spark = (a) => {
    const cl = (a.closes || []).filter((p) => p[0] >= nowSec() - WIN['7d']);
    if (cl.length < 3) return '';
    const vw = 300, vh = 64, xs = cl.map((p) => p[0]), ys = cl.map((p) => p[1]);
    const x0 = xs[0], x1 = xs[xs.length - 1] || x0 + 1, lo = Math.min(...ys), hi = Math.max(...ys) || lo + 1;
    const X = (t) => ((t - x0) / (x1 - x0 || 1)) * vw, Y = (v) => vh - 4 - ((v - lo) / (hi - lo || 1)) * (vh - 8);
    const d = cl.map((p, i) => (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1)).join(' ');
    const marks = data.news.filter((n) => n.t >= x0 && n.h.some((h) => h.s === a.s && Math.abs(h.z || 0) >= 2))
      .map((n) => `<line x1="${X(n.t).toFixed(1)}" x2="${X(n.t).toFixed(1)}" y1="0" y2="${vh}" class="mspark__mark"/>`).join('');
    const up = ys[ys.length - 1] >= ys[0];
    return `<svg class="mspark ${up ? 'is-up' : 'is-down'}" viewBox="0 0 ${vw} ${vh}" preserveAspectRatio="none" aria-hidden="true">${marks}<path d="${d}"/></svg><p class="small muted">최근 7일 1시간 종가 · 세로선 = 중 이상 반응 뉴스</p>`;
  };
  function renderPanel() {
    if (!data) return;
    const sel = view.sel;
    let html = '';
    if (sel && sel.kind === 'coin') {
      const a = bySym(sel.id);
      if (!a) { view.sel = null; return renderPanel(); }
      const list = graph.ranked.filter((n) => n.h.some((h) => h.s === a.s)).sort((x, y) => {
        const zx = Math.abs((x.h.find((h) => h.s === a.s) || {}).z || 0), zy = Math.abs((y.h.find((h) => h.s === a.s) || {}).z || 0);
        return zy - zx;
      }).slice(0, 6);
      const price = priceOf(a);
      const chips = ['1h', '6h', '24h', '7d'].map((w) => {
        const v = w === '24h' && live[a.s] ? live[a.s].chg24 : a.chg[w];
        return `<span class="mchg"><b>${WIN_KO[w]}</b><em class="${v == null ? '' : v >= 0 ? 'up' : 'down'}">${pct(v)}</em></span>`;
      }).join('');
      html = `<div class="mpanel__head"><h2 class="mpanel__title"><img src="${root.dataset.coins}${esc(a.s)}.svg" alt="">${esc(a.s)}</h2><button type="button" class="mpanel__x" data-close aria-label="닫기">×</button></div>`
        + `<p class="mpanel__price">${price ? price.toLocaleString('en-US', { maximumFractionDigits: price < 1 ? 5 : 2 }) + ' USDT' : '–'}</p><div class="mchgs">${chips}</div>${spark(a)}`
        + (a.base1h ? `<p class="small muted">평소 1시간 변동폭(최근 30일 중앙값) ±${a.base1h.toFixed(2)}%</p>` : '')
        + `<h3 class="mpanel__sub">${view.range ? '고른 구간' : WIN_KO[view.win]} 동안 ${esc(a.s)}를 가장 크게 움직인 뉴스</h3>`
        + (list.length ? `<ol class="mlist">${list.map(newsRow).join('')}</ol>` : '<p class="muted small">이 기간에 잰 반응이 없습니다.</p>');
    } else if (sel && sel.kind === 'news') {
      const n = data.news.find((x) => x.id === sel.id);
      if (!n) { view.sel = null; return renderPanel(); }
      const ids = order(), idx = ids.indexOf(n.id);
      const rows = n.h.map((h) => `<tr><th scope="row">${esc(h.s)}</th>${['15m', '1h', '24h'].map((w) => `<td class="${h[w] == null ? 'muted' : h[w] >= 0 ? 'up' : 'down'}">${h[w] == null ? '측정 중' : pct(h[w])}</td>`).join('')}<td>${h.g ? esc(h.g) : '–'}${h.z != null ? ' <span class="muted">z ' + h.z.toFixed(1) + '</span>' : ''}</td></tr>`).join('');
      const pt = n.pt;
      const ptHtml = !pt ? '' : pt.n >= 5
        ? `<div class="mpat"><p class="mpat__k">이런 뉴스는 보통 · ${esc(pt.label)} · ${esc(pt.sym)} 1시간</p><p class="mpat__v">중앙값 <b class="${pt.med >= 0 ? 'up' : 'down'}">${pct(pt.med)}</b> · 상승 ${Math.round(pt.up * 100)}% · 중·강 ${Math.round(pt.strong * 100)}% <span class="muted">(n=${pt.n}, 최근 30일)</span></p></div>`
        : `<div class="mpat"><p class="mpat__k">이런 뉴스는 보통 · ${esc(pt.label)}</p><p class="mpat__v muted">표본 부족 (n=${pt.n})</p></div>`;
      html = (idx >= 0 ? `<div class="mpanel__step"><button type="button" data-step="-1" ${idx <= 0 ? 'disabled' : ''}>← 이전</button><span>반응 순위 ${idx + 1} / ${ids.length}</span><button type="button" data-step="1" ${idx >= ids.length - 1 ? 'disabled' : ''}>다음 →</button></div>` : '')
        + `<div class="mpanel__head"><p class="mpanel__meta"><span class="chip cat cat--${esc(n.c)}">${CAT[n.c]}</span>${esc(ETYPE[n.e] || '')} · ${esc(n.src || '')} · ${when(n.t)}</p><button type="button" class="mpanel__x" data-close aria-label="닫기">×</button></div>`
        + `<h2 class="mpanel__news">${esc(n.title)}</h2>`
        + `<table class="mtable"><thead><tr><th scope="col">코인</th><th scope="col">15분</th><th scope="col">1시간</th><th scope="col">24시간</th><th scope="col">강도</th></tr></thead><tbody>${rows}</tbody></table>`
        + ptHtml
        + `<p class="mpanel__links"><a href="${BASE}a/${esc(n.id)}/">기사와 차트 보기</a></p>`;
    } else {
      const list = graph.ranked.slice(0, 10);
      html = `<div class="mpanel__head"><h2 class="mpanel__title mpanel__title--s">${view.range ? '고른 구간에서' : '지금'} 가장 무거운 뉴스</h2></div>`
        + `<p class="small muted">${view.range ? `${when(view.range[0])} – ${hhmm(view.range[1])}` : WIN_KO[view.win]} 동안 잰 반응이 큰 순서 · 점이나 원을 누르면 자세히 봅니다. ← → 키로 차례로 볼 수 있습니다.</p>`
        + (list.length ? `<ol class="mlist">${list.map(newsRow).join('')}</ol>` : '<p class="muted small">이 기간에 보여 줄 뉴스가 없습니다.</p>');
    }
    panel.innerHTML = html;
  }

  // 목록으로 보기(같은 내용을 표로)
  let listTimer = 0;
  function renderList() {
    clearTimeout(listTimer);
    listTimer = setTimeout(() => {
      const box = $('#mapList');
      if (!box || !data) return;
      const coins = assets().map((a) => { const c = chgOf(a); return `<tr><th scope="row">${esc(a.s)}</th><td class="${c == null ? '' : c >= 0 ? 'up' : 'down'}">${pct(c)}</td></tr>`; }).join('');
      const news = graph.ranked.slice(0, 50).map((n) => {
        const top = n.h.slice().sort((a, b) => Math.abs(b.z || 0) - Math.abs(a.z || 0))[0];
        return `<li><a href="${BASE}a/${esc(n.id)}/">${esc(n.title)}</a> <span class="muted small">${when(n.t)} · ${top ? esc(top.s) + ' ' + pct(hitR(top)) + (top.g ? ' · ' + esc(top.g) : '') : ''}</span></li>`;
      }).join('');
      box.innerHTML = `<div class="mlistbox"><table class="mtable"><caption class="small muted">${WIN_KO[view.win]} 등락</caption><tbody>${coins}</tbody></table><ol class="mlistbox__news">${news || '<li class="muted">뉴스 없음</li>'}</ol></div>`;
    }, 120);
  }

  // ---------- 주소 ----------
  const syncUrl = () => {
    const q = new URLSearchParams();
    if (view.win !== '24h') q.set('win', view.win);
    if (view.sel) q.set('sel', view.sel.kind + ':' + view.sel.id);
    const s = q.toString();
    history.replaceState(null, '', location.pathname + (s ? '?' + s : ''));
  };

  // ---------- 크기 ----------
  const resize = () => {
    W = canvas.clientWidth; H = canvas.clientHeight; dpr = Math.min(devicePixelRatio || 1, 2);
    narrow = W < 640;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    if (field) field.resize(W, H, dpr, narrow ? 15 : 17);
    BW = bCanvas.clientWidth; BH = bCanvas.clientHeight;
    bCanvas.width = Math.round(BW * dpr); bCanvas.height = Math.round(BH * dpr);
    if (data) {
      buildGraph();
      if (!userCam) moveCam(fitCam(), false);
      drawBrush(); schedule();
    }
  };
  new ResizeObserver(resize).observe(stage);

  // ---------- 실시간 시세 ----------
  let ws = null, wsTimer = 0, liveTimer = 0;
  const connect = () => {
    if (!data || ws) return;
    const streams = assets().map((a) => a.s.toLowerCase() + 'usdt@miniTicker').join('/');
    try { ws = new WebSocket('wss://data-stream.binance.vision/stream?streams=' + streams); } catch (e) { return; }
    ws.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data).data;
        const s = d.s.replace(/USDT$/, ''), c = Number(d.c), o = Number(d.o);
        live[s] = { price: c, chg24: o ? (c / o - 1) * 100 : null };
        if (!liveTimer) liveTimer = setTimeout(() => { liveTimer = 0; schedule(); }, 1000);
      } catch (e) {}
    };
    ws.onclose = () => { ws = null; clearTimeout(wsTimer); if (!document.hidden) wsTimer = setTimeout(connect, 5000); };
  };
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { if (ws) ws.close(); } else { connect(); refresh(); }
  });

  // ---------- 불러오기 ----------
  async function refresh() {
    try {
      const res = await fetch(root.dataset.src + '?t=' + Math.floor(Date.now() / 60000), { cache: 'no-store' });
      if (!res.ok) throw new Error(res.status);
      const next = await res.json();
      const before = data ? new Set(graph.news.map((d) => d.id)) : null;
      data = next;
      applyFilters(!before);
      // 새로 잰 무거운 뉴스는 그 코인에서 파문을 한 번 낸다
      if (before && !reduced) {
        const ms = performance.now();
        graph.news.filter((d) => !before.has(d.id) && d.zn > 0.45).slice(0, 4).forEach((d, i) => d.links.forEach((l) => pulses.push({ id: d.id, s: l.s, col: l.r >= 0 ? C.up : C.down, amp: (l.r >= 0 ? 1 : -1) * (0.4 + 0.5 * l.zn), at: ms + i * 400 })));
        schedule();
      }
      $('#mapEmpty').hidden = true;
    } catch (e) {
      if (!data) $('#mapEmpty').hidden = false;
    }
  }

  (async () => {
    readColors();
    const q = new URLSearchParams(location.search);
    if (WIN[q.get('win')]) { view.win = q.get('win'); $$('[data-win]', root).forEach((x) => x.setAttribute('aria-pressed', x.dataset.win === view.win ? 'true' : 'false')); }
    resize();
    await refresh();
    if (!data) return;
    if (q.get('sel')) {
      const [kind, id] = q.get('sel').split(':');
      if (kind === 'news') {
        const n = data.news.find((x) => x.id === id);
        if (n) {
          // 고른 뉴스가 창 밖이면 창을 넓힌다
          if (n.t <= nowSec() - WIN[view.win]) { view.win = n.t > nowSec() - WIN['24h'] ? '24h' : '7d'; $$('[data-win]', root).forEach((x) => x.setAttribute('aria-pressed', x.dataset.win === view.win ? 'true' : 'false')); }
          if (!view.cats.has(n.c)) view.cats.add(n.c);
          view.sel = { kind, id };
          applyFilters();
          setTimeout(() => select({ kind, id }, { force: true, center: true }), reduced ? 0 : 500);
        }
      } else if (kind === 'coin' && graph.coins[id]) select({ kind, id });
    }
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(schedule);
    connect();
    setInterval(() => { if (!document.hidden) refresh(); }, 60000);
    setInterval(() => { if (!document.hidden) { setStatus(); } }, 30000);
  })();
}

main();
