// R3 · Impact — Perplexity Discover·Kalshi 참고. 맨 위 '지금' 한 장: 최근 6시간 가장 큰 소식 + 그 뒤 가격 흐름(크게).
// 아래 카드 격자: 세기 3은 두 칸, 카드마다 '소식 이후' 작은 그래프. 중립 소식은 아래 '그 밖의 소식' 짧은 목록으로. 오른쪽: 많이 언급된 코인.
import { lwChart, store, start, day, counts, T, esc, line, altLine, pill, bars, chips, outlets, hm, ago, openSheet, THEMES, thName, pxChip, fillPx, newGate, loadK5, sinceChange, PRICED_ALL } from './lk.js?v=1016172222';

const app = document.getElementById('app');
app.innerHTML = `<div class="wrap r3"><div class="tt" id="tt" role="tablist"></div>
  <section class="lead" id="lead"><div class="skel" style="height:280px"></div></section>
  <button type="button" class="newpill" id="np"></button>
  <section class="main"><div><h2 class="sec" id="gh"></h2><div class="grid" id="grid"></div><h2 class="sec" id="oh"></h2><ul class="other" id="other"></ul></div>
  <aside class="rail"><div class="box" id="tr"></div><div class="box" id="mk"></div></aside></section></div>`;
const $ = (id) => document.getElementById(id), S = { th: 'all' };
const gate = newGate($('np'), () => render(true));
const score = (x) => x.s * 3 + Math.min(x.n || 1, 4) * 1.5;
// ---------- 비교 차트: BTC · 나스닥100 · S&P500 (선택은 저장) ----------
const MK = { btc: { en: 'BTC', ko: 'BTC' }, nq: { en: 'Nasdaq 100', ko: '나스닥 100' }, es: { en: 'S&P 500', ko: 'S&P 500' } };
let M = (() => { try { return localStorage.getItem('df-mkt') || 'btc'; } catch (e) { return 'btc'; } })(); if (!MK[M]) M = 'btc';
const WK = 'https://signal-scheduler.mash1384.workers.dev/index-candles';
const sc = new Map();
function series(m, iv) {   // [[t, close]] 지난 며칠(5m) 또는 이틀(1m). 60초 보관
  const key = m + (m === 'btc' ? iv : '1m'), hit = sc.get(key); if (hit && Date.now() - hit.at < 60000) return hit.p;
  const p = (m === 'btc' ? fetch(`https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=${iv}&limit=1000`).then((r) => r.ok ? r.json() : null).then((k) => (k ? k.map((x) => [x[0] / 1000, +x[4]]) : null))
    : fetch(`${WK}?s=${m}&i=1m`).then((r) => r.ok ? r.json() : null).then((d) => (d && d.c ? d.c : null))).catch(() => null);
  sc.set(key, { at: Date.now(), p }); return p;
}
const mName = (m = M) => MK[m][DFI.lang() === 'ko' ? 'ko' : 'en'];
async function bigChart(el, t) {   // 맨 위 큰 차트: TradingView Lightweight Charts(포인터·터치 십자선)
  const all = await series(M, '1m'), lbl = el.parentElement.querySelector('[data-chg]'), pts = all ? all.filter((p) => p[0] >= t - 1800) : null;
  const r = lwChart(el, pts, t, { height: innerWidth < 900 ? 200 : 230 });
  if (lbl) { if (!r || r.change == null) { lbl.className = 'chg mono'; lbl.textContent = T('no trading since the story', '소식 이후 거래 없음'); } else { lbl.className = (r.change >= 0 ? 'up' : 'down') + ' chg mono'; lbl.textContent = DFD.pct(r.change) + (r.closed && M !== 'btc' ? T(' · market closed', ' · 장 마감') : ''); } }
}
async function chart(cv, t, big) {
  const all = await series(M, big ? '1m' : '5m'), lbl = cv.parentElement.querySelector('[data-chg]');
  const pre = big ? 1800 : 3600, pts = all ? all.filter((p) => p[0] >= t - pre) : null;
  if (!pts || pts.length < 3 || pts[0][0] > t + 600) { const ctx = cv.getContext('2d'); ctx.clearRect(0, 0, cv.width, cv.height); if (lbl) lbl.textContent = T('no data for this time', '이 시간 자료 없음'); cv.style.visibility = 'hidden'; return; }
  cv.style.visibility = '';
  const dpr = Math.min(devicePixelRatio || 1, 2), w = cv.clientWidth, h = cv.clientHeight; cv.width = w * dpr; cv.height = h * dpr; const g = cv.getContext('2d'); g.scale(dpr, dpr);
  const ys = pts.map((p) => p[1]), lo = Math.min(...ys), hi = Math.max(...ys), sp = hi - lo || 1, t0 = pts[0][0], t1 = Math.max(pts[pts.length - 1][0], t + 60);
  const X = (tt) => (tt - t0) / (t1 - t0 || 1) * (w - 2) + 1, Y = (y) => h - 6 - (y - lo) / sp * (h - 12);
  let i0 = pts.findIndex((p) => p[0] >= t); const after = i0 >= 0; if (!after) i0 = pts.length - 1;
  const base = pts[i0][1], last = ys[ys.length - 1], up = last >= base, col = up ? '#12b07c' : '#e5533f';
  g.lineWidth = big ? 2 : 1.5; g.strokeStyle = '#c3cad6'; g.beginPath(); pts.slice(0, i0 + 1).forEach((p, i) => (i ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1])))); g.stroke();
  if (after) { const grd = g.createLinearGradient(0, 0, 0, h); grd.addColorStop(0, up ? 'rgba(18,176,124,.18)' : 'rgba(229,83,63,.18)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.beginPath(); pts.slice(i0).forEach((p, i) => (i ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1])))); g.lineTo(X(pts[pts.length - 1][0]), h); g.lineTo(X(pts[i0][0]), h); g.closePath(); g.fillStyle = grd; g.fill();
    g.beginPath(); pts.slice(i0).forEach((p, i) => (i ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1])))); g.strokeStyle = col; g.stroke(); }
  const xs = X(t); g.strokeStyle = 'rgba(13,37,61,.35)'; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(xs, 4); g.lineTo(xs, h); g.stroke(); g.setLineDash([]);
  if (big) { g.fillStyle = '#5b6b82'; g.font = '500 11px "JetBrains Mono", monospace'; g.fillText(T('story', '소식'), xs + 5, 14); }
  const closed = pts[pts.length - 1][0] < Date.now() / 1000 - 1800 && M !== 'btc';
  if (lbl) { const ch = (last / base - 1) * 100; lbl.className = (after ? (ch >= 0 ? 'up' : 'down') : '') + ' chg mono'; lbl.dataset.chg = '1';
    lbl.textContent = after ? `${DFD.pct(ch)}${closed ? T(' · market closed', ' · 장 마감') : ''}` : T('no trading since', '이후 거래 없음'); }
}
const mSeg = () => `<span class="mseg" role="group" aria-label="${T('Chart market', '차트 기준')}">${Object.keys(MK).map((m) => `<button type="button" data-mkt="${m}" aria-pressed="${M === m}">${mName(m)}</button>`).join('')}</span>`;
function drawCharts() { app.querySelectorAll('.bigc[data-t]').forEach((el) => bigChart(el, +el.dataset.t)); app.querySelectorAll('canvas[data-t]').forEach((cv) => chart(cv, +cv.dataset.t, false)); app.querySelectorAll('[data-mname]').forEach((e) => (e.textContent = mName())); }
const symOf = (it) => (it.coins || []).find((c) => PRICED_ALL.has(c)) || ((it.th || []).some((k) => k === 'crypto' || k === 'econ' || k === 'nasdaq') || it.mw ? 'BTC' : null);
function card(it, wide) {
  return `<button type="button" class="cd btnp ${wide ? 'w' : ''} ${store.fresh.has(it.id) ? 'new-in' : ''}" data-id="${it.id}"><span class="mt">${pill(it.v)}${bars(it)}<span class="ou">${ago(it.t)}</span></span><span class="ln">${esc(line(it))}</span>
    <span class="spw"><span class="spl mono"><span data-mname>${mName()}</span> <span data-chg></span></span><canvas class="sp" data-t="${it.t}" aria-hidden="true"></canvas></span><span class="mt">${pxChip(it)}${chips(it, 2, true)}<span class="ou">${outlets(it)}</span></span></button>`; }
function render(force) {
  const all = day(); if (!force && !gate.check()) return;
  const xs = all.filter((x) => gate.visible(x)), ys = xs.filter((x) => S.th === 'all' || x.th.includes(S.th));
  $('tt').innerHTML = THEMES.map((t) => { const n = t.k === 'all' ? xs.length : xs.filter((x) => x.th.includes(t.k)).length; return `<button type="button" role="tab" aria-selected="${S.th === t.k}" data-th="${t.k}">${t[DFI.lang() === 'ko' ? 'ko' : 'en']}<span class="c mono">${n}</span></button>`; }).join('');
  const now = Date.now() / 1000, recent = ys.filter((x) => now - x.t < 6 * 3600 && x.v !== '중립').sort((a, b) => score(b) - score(a) || b.t - a.t);
  const lead = recent[0];
  if (lead) {
    $('lead').innerHTML = `<div class="ld"><button type="button" class="tx btnp" data-id="${lead.id}"><p class="k">${T('Biggest story · last 6 hours', '가장 큰 소식 · 최근 6시간')}</p><h1>${esc(line(lead))}</h1>${altLine(lead) ? `<p class="alt">${esc(altLine(lead))}</p>` : ''}
      <p class="mt">${pill(lead.v)}${bars(lead)}${chips(lead, 3)}<span class="ou">${hm(lead.t)} · ${ago(lead.t)} · ${outlets(lead)}</span></p></button><div class="ch">${mSeg()}<p class="cl"><b data-mname>${mName()}</b> <span data-chg></span> <span class="mute2">${T('since the story', '소식 이후')}</span></p><div class="bigc" data-t="${lead.t}" role="img" aria-label="${T('Price around the story', '소식 전후 가격')}"></div>
      <p class="src">${M === 'btc' ? T('BTC/USDT · Binance', 'BTC/USDT · 바이낸스') : T('Index futures (trade ~23h a day) · Yahoo Finance', '지수 선물(하루 약 23시간 거래) · Yahoo Finance')}</p></div></div>`; }
  else $('lead').innerHTML = '';
  $('gh').innerHTML = `<span>${T('Signals', '신호')}</span>${mSeg()}`; $('oh').textContent = T('Also reported', '그 밖의 소식');
  const sig = ys.filter((x) => x.v !== '중립' && x !== lead).slice(0, 24);
  $('grid').innerHTML = sig.map((it) => card(it, it.s >= 3)).join('') || `<p class="mute">${T('No signals in this theme yet.', '이 테마의 신호가 아직 없어요.')}</p>`;
  $('other').innerHTML = ys.filter((x) => x.v === '중립').slice(0, 20).map((it) => `<li><button type="button" data-id="${it.id}"><span class="tm mono">${hm(it.t)}</span><span>${esc(line(it))}</span></button></li>`).join('');
  drawCharts();
  fillPx(app);
  const cnt = {}; xs.filter((x) => now - x.t < 3 * 3600).forEach((x) => (x.coins || []).forEach((c) => { cnt[c] = (cnt[c] || 0) + 1; }));
  $('tr').innerHTML = `<h3>${T('Trending coins · 3h', '많이 언급된 코인 · 3시간')}</h3>` + Object.entries(cnt).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([c, n], i) => `<p class="q"><span class="rk mono">${i + 1}</span><b>${c}</b><span class="mono">${n}</span></p>`).join('');
  const c24 = counts(xs); $('mk').innerHTML = `<h3>${T('Last 24 hours', '지난 24시간')}</h3><p class="big3"><span><b class="mono">${c24.n}</b>${T('stories', '건')}</span><span><b class="mono up">${c24.u}</b>${T('bullish', '호재')}</span><span><b class="mono down">${c24.d}</b>${T('bearish', '악재')}</span></p>`;
}
app.addEventListener('click', (e) => { const mk = e.target.closest('[data-mkt]'); if (mk) { M = mk.dataset.mkt; try { localStorage.setItem('df-mkt', M); } catch (x) {} render(true); return; }
  const t = e.target.closest('[data-th]'); if (t) { S.th = t.dataset.th; render(true); return; } const b = e.target.closest('[data-id]'); if (b) openSheet(store.byId.get(b.dataset.id)); });
start(() => render(false)); DFI.onLang(() => render(true));
let rzT = 0; addEventListener('resize', () => { clearTimeout(rzT); rzT = setTimeout(() => app.querySelectorAll('canvas[data-t]').forEach((cv) => chart(cv, +cv.dataset.t, false)), 200); });   // 작은 그래프는 크기가 바뀌면 다시 그린다(큰 차트는 라이브러리가 맞춘다)
