// L3 · Pulse — 레이더 위에 소식이 점으로 찍힌다. 가운데 = 지금, 바깥으로 갈수록 오래된 소식(1·6·24시간 고르기).
// 다섯 구역 = 테마, 점 크기 = 세기, 색 = 호재·악재. 스윕이 돌고, 새 소식은 파문을 내며 나타난다. 옆(모바일은 아래)에 같은 소식 목록.
import { store, start, day, counts, T, esc, line, pill, bars, chips, outlets, hm, ago, openSheet, THEMES, thName, L } from './lk.js?v=1017210046';

const app = document.getElementById('app'), SEC = ['crypto', 'nasdaq', 'econ', 'ai', 'world'];
app.innerHTML = `<div class="wrap l3"><section class="top"><div><h1 data-x="t"></h1><p class="sub"><span class="livedot"></span><span id="upd"></span></p></div><div class="seg" id="rng"></div></section>
  <section class="grid"><div class="radar card"><canvas id="cv"></canvas><div class="tip" id="tip"></div><div class="leg" id="leg"></div></div><div class="feed card"><header id="fh"></header><div class="lst" id="lst"></div></div></section></div>`;
const $ = (id) => document.getElementById(id), cv = $('cv'), g = cv.getContext('2d');
const S = { span: 6, hover: null, sel: null }, born = new Map();
const hash = (s) => { let h = 2166136261; for (const c of s) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return ((h >>> 0) % 10000) / 10000; };
let pts = [], W = 0, H = 0, R = 0, cx = 0, cy = 0;
function layout() { const dpr = Math.min(devicePixelRatio || 1, 2); W = cv.clientWidth; H = cv.clientHeight; cv.width = W * dpr; cv.height = H * dpr; g.setTransform(dpr, 0, 0, dpr, 0, 0); R = Math.min(W, H) / 2 - 34; cx = W / 2; cy = H / 2; }
function place() {
  const now = Date.now() / 1000; pts = [];
  day().filter((x) => now - x.t <= S.span * 3600).forEach((it) => { const k = SEC.indexOf(it.th[0]), a0 = -Math.PI / 2 + k * 2 * Math.PI / 5, a = a0 + (0.12 + hash(it.id) * 0.76) * 2 * Math.PI / 5;
    const r = 18 + Math.sqrt((now - it.t) / (S.span * 3600)) * (R - 18); pts.push({ it, x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r, s: 2.6 + it.s * 2.2 }); });
}
function frame(t) {
  requestAnimationFrame(frame); if (!W) return; g.clearRect(0, 0, W, H);
  // 고리·구역
  g.lineWidth = 1; [0.25, 0.5, 0.75, 1].forEach((f, i) => { g.strokeStyle = i === 3 ? 'rgba(13,37,61,.18)' : 'rgba(13,37,61,.08)'; g.beginPath(); g.arc(cx, cy, 18 + Math.sqrt(f) * (R - 18), 0, 7); g.stroke(); });
  SEC.forEach((k, i) => { const a = -Math.PI / 2 + i * 2 * Math.PI / 5; g.strokeStyle = 'rgba(13,37,61,.08)'; g.beginPath(); g.moveTo(cx + Math.cos(a) * 18, cy + Math.sin(a) * 18); g.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); g.stroke();
    const am = a + Math.PI / 5; g.fillStyle = '#5b6b82'; g.font = `600 12px ${getComputedStyle(document.body).fontFamily}`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(thName(k), cx + Math.cos(am) * (R + 18), cy + Math.sin(am) * (R + 18)); });
  // 스윕
  const sw = (t / 1000 * 0.6) % (Math.PI * 2) - Math.PI / 2; const grd = g.createConicGradient ? g.createConicGradient(sw - 0.6, cx, cy) : null;
  if (grd) { grd.addColorStop(0, 'rgba(83,58,253,0)'); grd.addColorStop(0.095, 'rgba(83,58,253,.13)'); grd.addColorStop(0.0955, 'rgba(83,58,253,0)'); grd.addColorStop(1, 'rgba(83,58,253,0)'); g.fillStyle = grd; g.beginPath(); g.arc(cx, cy, R, 0, 7); g.fill(); }
  g.strokeStyle = 'rgba(83,58,253,.35)'; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(sw) * R, cy + Math.sin(sw) * R); g.stroke();
  // 점
  const now = performance.now();
  pts.forEach((p) => { const v = p.it.v, col = v === '호재' ? '18,176,124' : v === '악재' ? '229,83,63' : '138,150,170', hl = S.hover === p.it.id || S.sel === p.it.id;
    let ang = Math.atan2(p.y - cy, p.x - cx) - sw; ang = ((ang % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI); const lit = Math.max(0, 1 - (2 * Math.PI - ang) / 1.2) * 0; const flash = ang > 2 * Math.PI - 0.5 ? (ang - (2 * Math.PI - 0.5)) / 0.5 : 0;
    g.fillStyle = `rgba(${col},${v === '중립' ? 0.45 : 0.85})`; g.beginPath(); g.arc(p.x, p.y, p.s * (1 + flash * 0.35) + (hl ? 2 : 0), 0, 7); g.fill();
    if (hl) { g.strokeStyle = `rgba(${col},.9)`; g.lineWidth = 2; g.beginPath(); g.arc(p.x, p.y, p.s + 6, 0, 7); g.stroke(); g.lineWidth = 1; }
    const b = born.get(p.it.id); if (b) { const k = (now - b) / 1600; if (k < 1) { g.strokeStyle = `rgba(${col},${1 - k})`; g.beginPath(); g.arc(p.x, p.y, p.s + k * 26, 0, 7); g.stroke(); } else born.delete(p.it.id); } });
  // 가운데 '지금'
  g.fillStyle = '#0d253d'; g.beginPath(); g.arc(cx, cy, 5, 0, 7); g.fill(); const pk = (t / 1000 * 0.8) % 1; g.strokeStyle = `rgba(13,37,61,${0.5 * (1 - pk)})`; g.beginPath(); g.arc(cx, cy, 5 + pk * 14, 0, 7); g.stroke();
}
function row(it) { return `<button type="button" class="r ${store.fresh.has(it.id) ? 'new-in' : ''} ${S.sel === it.id ? 'on' : ''}" data-id="${it.id}"><span class="m">${pill(it.v)}${bars(it)}<span class="tm mono">${hm(it.t)}</span></span><span class="ln">${esc(line(it))}</span><span class="f">${chips(it, 2)}<span class="ou">${outlets(it)}</span></span></button>`; }
function render() {
  app.querySelector('[data-x="t"]').textContent = T('Signal pulse', '신호 레이더');
  $('upd').textContent = T(`Live · centre is now, rings go back ${S.span}h`, `실시간 · 가운데가 지금, 바깥은 ${S.span}시간 전`);
  $('rng').innerHTML = [1, 6, 24].map((h) => `<button type="button" data-h="${h}" aria-pressed="${S.span === h}">${h}${T('h', '시간')}</button>`).join('');
  store.fresh.forEach((id) => born.set(id, performance.now()));
  layout(); place();
  const xs = day().filter((x) => x.t > Date.now() / 1000 - S.span * 3600), c = counts(xs);
  $('fh').innerHTML = `<b>${T(`Last ${S.span}h`, `최근 ${S.span}시간`)}</b><span class="mono">${c.n}</span><span class="mono up">${c.u}↑</span><span class="mono down">${c.d}↓</span>`;
  $('lst').innerHTML = xs.slice(0, 80).map(row).join('') || `<p class="empty">–</p>`;
  $('leg').innerHTML = `<span><i class="u"></i>${T('Bullish', '호재')}</span><span><i class="d"></i>${T('Bearish', '악재')}</span><span><i class="n"></i>${T('Neutral', '중립')}</span><span class="sz">${T('size = strength', '크기 = 세기')}</span>`;
}
const near = (e) => { const rc = cv.getBoundingClientRect(), x = e.clientX - rc.left, y = e.clientY - rc.top; let best = null, bd = 14 * 14; pts.forEach((p) => { const d = (p.x - x) ** 2 + (p.y - y) ** 2; if (d < bd) { bd = d; best = p; } }); return best; };
cv.addEventListener('pointermove', (e) => { const p = near(e), tip = $('tip'); S.hover = p ? p.it.id : null; cv.style.cursor = p ? 'pointer' : 'default';
  if (p) { tip.innerHTML = `<span class="m">${pill(p.it.v)}<span class="mono">${hm(p.it.t)}</span></span>${esc(line(p.it))}`; tip.style.transform = `translate(${Math.min(p.x + 14, cv.clientWidth - 260)}px,${p.y + 12}px)`; tip.classList.add('on'); } else tip.classList.remove('on');
  app.querySelectorAll('.r').forEach((r) => r.classList.toggle('hv', r.dataset.id === S.hover)); });
cv.addEventListener('pointerleave', () => { S.hover = null; $('tip').classList.remove('on'); });
cv.addEventListener('click', (e) => { const p = near(e); if (p) { S.sel = p.it.id; openSheet(p.it); } });
app.addEventListener('click', (e) => { const h = e.target.closest('[data-h]'); if (h) { S.span = +h.dataset.h; render(); return; } const r = e.target.closest('.r'); if (r) { S.sel = r.dataset.id; openSheet(store.byId.get(r.dataset.id)); } });
app.addEventListener('pointerover', (e) => { const r = e.target.closest('.r'); S.hover = r ? r.dataset.id : S.hover; });
addEventListener('resize', () => { layout(); place(); });
start(render); requestAnimationFrame(frame);
