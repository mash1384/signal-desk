// R3 · Impact — Perplexity Discover·Kalshi 참고. 맨 위 '지금' 한 장: 최근 6시간 가장 큰 소식 + 그 뒤 가격 흐름(크게).
// 아래 카드 격자: 세기 3은 두 칸, 카드마다 '소식 이후' 작은 그래프. 정렬·거르기(최신순·호재·악재·강도순); 최신순 밖에선 중립 소식은 '그 밖의 소식' 목록으로. 오른쪽: 많이 언급된 이슈·종목.
import { lwChart, store, start, day, counts, T, esc, line, altLine, pill, bars, chips, outlets, hm, ago, openSheet, THEMES, thName, pxChip, fillPx, newGate, loadK5, sinceChange, PRICED_ALL } from './lk.js';

import * as Y from './yk.js';
import { loadIndex, threadOf, briefHref } from './thr.js';
const app = document.getElementById('app');
app.innerHTML = `<div class="pstrip" id="ps" aria-label="Markets"></div><div class="wrap r3"><div class="ttrow"><div class="tt" id="tt" role="tablist"></div><button type="button" class="myonly" id="myonly" aria-pressed="false"><span class="st-ic" aria-hidden="true"></span><span></span></button></div>
  <section class="lead" id="lead"><div class="skel" style="height:280px"></div></section>
  <button type="button" class="newpill" id="np"></button>
  <section class="main"><div><h2 class="sec" id="gh"></h2><div class="grid" id="grid"></div><h2 class="sec" id="oh"></h2><ul class="other" id="other"></ul></div>
  <aside class="rail"><div class="box mybox" id="myb"></div><div class="box" id="tr"></div><div class="box" id="mk"></div></aside></section></div>`;
const $ = (id) => document.getElementById(id), S = { th: 'all', mine: false };
// 신호 정렬·거르기: 최신순(중립 포함 모든 소식) · 호재 · 악재 · 강도순(세기 → 보도 수 → 최신). 선택은 저장
const SORTS = { new: ['Latest', '최신순'], up: ['Bullish', '호재'], down: ['Bearish', '악재'], str: ['Strongest', '강도순'] };
let SO = (() => { try { return localStorage.getItem('df-sort') || 'new'; } catch (e) { return 'new'; } })(); if (!SORTS[SO]) SO = 'new';
const sSeg = () => `<span class="mseg sseg" role="group" aria-label="${T('Sort and filter', '정렬·거르기')}">${Object.keys(SORTS).map((k) => `<button type="button" data-sort="${k}" aria-pressed="${SO === k}">${SORTS[k][DFI.lang() === 'ko' ? 1 : 0]}</button>`).join('')}</span>`;
function pick(ys, lead) {
  const rest = ys.filter((x) => x !== lead);
  if (SO === 'up') return rest.filter((x) => x.v === '호재');
  if (SO === 'down') return rest.filter((x) => x.v === '악재');
  if (SO === 'str') return rest.filter((x) => x.v !== '중립').sort((a, b) => b.s - a.s || (b.n || 1) - (a.n || 1) || b.t - a.t);
  return rest;   // 최신순: 중립도 함께(가장 최근 소식이 바로 보이게)
}
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
  if (!el.isConnected) return;
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
  if (big) { g.fillStyle = '#5b6b82'; g.font = '500 11px "JetBrains Mono", monospace'; const lw = g.measureText(T('story', '소식')).width; g.fillText(T('story', '소식'), xs + 5 + lw > w ? xs - 5 - lw : xs + 5, 14); }
  const closed = pts[pts.length - 1][0] < Date.now() / 1000 - 1800 && M !== 'btc';
  if (lbl) { const ch = (last / base - 1) * 100; lbl.className = (after ? (ch >= 0 ? 'up' : 'down') : '') + ' chg mono'; lbl.dataset.chg = '1';
    lbl.textContent = after ? `${DFD.pct(ch)}${closed ? T(' · market closed', ' · 장 마감') : ''}` : T('no trading since', '이후 거래 없음'); }
}
const mSeg = () => `<span class="mseg" role="group" aria-label="${T('Chart market', '차트 기준')}">${Object.keys(MK).map((m) => `<button type="button" data-mkt="${m}" aria-pressed="${M === m}">${mName(m)}</button>`).join('')}</span>`;
function drawCharts() { app.querySelectorAll('.bigc[data-t]:not([data-on])').forEach((el) => { el.dataset.on = '1'; bigChart(el, +el.dataset.t); }); app.querySelectorAll('canvas[data-t]').forEach((cv) => chart(cv, +cv.dataset.t, false)); app.querySelectorAll('[data-mname]').forEach((e) => (e.textContent = mName())); }
const symOf = (it) => (it.coins || []).find((c) => PRICED_ALL.has(c)) || ((it.th || []).some((k) => k === 'crypto' || k === 'econ' || k === 'nasdaq') || it.mw ? 'BTC' : null);
function card(it, wide) {
  return `<button type="button" class="cd btnp ${wide ? 'w' : ''} ${store.fresh.has(it.id) ? 'new-in' : ''}" data-id="${it.id}"><span class="mt">${pill(it.v)}${bars(it)}<span class="ou">${ago(it.t)}</span></span><span class="ln">${esc(line(it))}</span>
    <span class="spw"><span class="spl mono"><span data-mname>${mName()}</span> <span data-chg></span></span><canvas class="sp" data-t="${it.t}" aria-hidden="true"></canvas></span><span class="mt">${pxChip(it)}${chips(it, 2, true)}<span class="ou">${outlets(it)}</span></span></button>`; }
function render(force) {
  const all = day(); if (!force && !gate.check()) return;
  const my = Y.getMy().map((k) => Y.BY[k]).filter(Boolean), mineOf = (x) => my.some((a) => Y.matches(x, a));
  if (S.mine && !my.length) S.mine = false;
  const xs = all.filter((x) => gate.visible(x)), ys = xs.filter((x) => (S.th === 'all' || x.th.includes(S.th)) && (!S.mine || mineOf(x)));
  $('myonly').setAttribute('aria-pressed', String(S.mine)); $('myonly').lastChild.textContent = T('My assets only', '내 자산만'); $('myonly').hidden = !my.length;
  LASTXS = xs; drawMy(xs, my);
  $('tt').innerHTML = THEMES.map((t) => { const n = t.k === 'all' ? xs.length : xs.filter((x) => x.th.includes(t.k)).length; return `<button type="button" role="tab" aria-selected="${S.th === t.k}" data-th="${t.k}">${t[DFI.lang() === 'ko' ? 'ko' : 'en']}<span class="c mono">${n}</span></button>`; }).join('');
  const now = Date.now() / 1000, recent = ys.filter((x) => now - x.t < 6 * 3600 && x.v !== '중립').sort((a, b) => score(b) - score(a) || b.t - a.t);
  const lead = recent[0];
  if (lead) {
    const html = `<div class="ld"><button type="button" class="tx btnp" data-id="${lead.id}"><p class="k">${T('Biggest story · last 6 hours', '가장 큰 소식 · 최근 6시간')}</p><h1>${esc(line(lead))}</h1>${altLine(lead) ? `<p class="alt">${esc(altLine(lead))}</p>` : ''}
      <p class="mt">${pill(lead.v)}${bars(lead)}${chips(lead, 3)}<span class="ou">${hm(lead.t)} · ${ago(lead.t)} · ${outlets(lead)}</span></p></button><div class="ch">${mSeg()}<p class="cl"><b data-mname>${mName()}</b> <span data-chg></span> <span class="mute2">${T('since the story', '소식 이후')}</span></p><div class="bigc" data-t="${lead.t}" role="img" aria-label="${T('Price around the story', '소식 전후 가격')}"></div>
      <p class="src">${M === 'btc' ? T('BTC/USDT · Binance', 'BTC/USDT · 바이낸스') : T('Index futures (trade ~23h a day) · Yahoo Finance', '지수 선물(하루 약 23시간 거래) · Yahoo Finance')}</p></div></div>`;
    // 같은 소식·같은 시장·같은 언어면 차트는 두고 글만 바꾼다(매번 새로 만들면 깜빡이고 십자선이 끊긴다). 5분이 지나면 가격을 새로 그린다.
    const lk = lead.id + '|' + M + '|' + DFI.lang(), L0 = $('lead'), old = L0.querySelector('.ld > .tx');
    if (L0.dataset.k === lk && old && Date.now() - +L0.dataset.at < 300000) { const tmp = document.createElement('div'); tmp.innerHTML = html; old.replaceWith(tmp.querySelector('.ld > .tx')); }
    else { L0.innerHTML = html; L0.dataset.k = lk; L0.dataset.at = Date.now(); } }
  else { $('lead').innerHTML = ''; $('lead').dataset.k = ''; }
  $('gh').innerHTML = `<span class="ghl"><span>${T('Signals', '신호')}</span>${sSeg()}</span>${mSeg()}`;
  const sig = pick(ys, lead).slice(0, 24);
  $('grid').innerHTML = sig.map((it) => card(it, it.s >= 3)).join('') || `<p class="mute">${SO === 'up' ? T('No bullish stories in this theme in the last 24 hours.', '최근 24시간 이 테마의 호재가 없어요.') : SO === 'down' ? T('No bearish stories in this theme in the last 24 hours.', '최근 24시간 이 테마의 악재가 없어요.') : T('No signals in this theme yet.', '이 테마의 신호가 아직 없어요.')}</p>`;
  // '그 밖의 소식'(중립 목록)은 최신순에선 이미 위에 섞여 있으므로 숨긴다
  const showOther = SO !== 'new'; $('oh').textContent = showOther ? T('Also reported', '그 밖의 소식') : ''; $('oh').hidden = !showOther; $('other').hidden = !showOther;
  $('other').innerHTML = !showOther ? '' : ys.filter((x) => x.v === '중립').slice(0, 20).map((it) => `<li><button type="button" data-id="${it.id}"><span class="tm mono">${hm(it.t)}</span><span>${esc(line(it))}</span></button></li>`).join('');
  drawCharts();
  fillPx(app);
  trending(xs, now);
  const c24 = counts(xs); $('mk').innerHTML = `<h3>${T('Last 24 hours', '지난 24시간')}</h3><p class="big3"><span><b class="mono">${c24.n}</b>${T('stories', '건')}</span><span><b class="mono up">${c24.u}</b>${T('bullish', '호재')}</span><span><b class="mono down">${c24.d}</b>${T('bearish', '악재')}</span></p>`;
}

// ---------- 맨 위 가격 띠(업계 표준: 숫자 먼저) · 오른쪽 '내 자산' 칸 ----------
const STRIP = ['BTC', 'ETH', 'NQ=F', 'ES=F', '^TNX', 'GC=F'];
let PQ = {}, pqAt = 0, MQ = {}, LASTXS = [];
async function loadStrip() {
  if (Date.now() - pqAt < 60000) return; pqAt = Date.now();
  const want = [...new Set([...STRIP, ...Y.getMy()])]; const q = await Y.loadQuotes(want); PQ = q; MQ = q; drawStrip(); drawMy(LASTXS, Y.getMy().map((k) => Y.BY[k]).filter(Boolean));
}
function drawStrip() {
  $('ps').innerHTML = `<div class="wrap pin">${STRIP.map((s) => { const a = Y.BY[s], q = PQ[s];
    return `<div class="pi"><span class="nm">${Y.esc(Y.nm(a))}</span><span class="mono pv">${Y.fmtP(a, q)}</span><span class="mono pc">${Y.fmtCh(a, q)}</span><canvas class="spk" data-sym="${Y.esc(s)}" aria-hidden="true"></canvas><button type="button" class="mystar ic" data-my="${s}" aria-pressed="${Y.hasMy(s)}" aria-label="${T(`Add ${s} to My assets`, `${s} 내 자산에 추가`)}"><span class="st-ic" aria-hidden="true"></span></button></div>`; }).join('')}</div>`;
  Y.drawSparks($('ps'), PQ);
}
function drawMy(xs, my) {
  const el = $('myb'); if (!el) return;
  if (!my.length) { el.innerHTML = `<h3>${T('My assets', '내 자산')}</h3><p class="mute3">${T('Star an asset to follow just its news.', '자산에 ☆를 누르면 그 소식만 따라가요.')}</p><div class="pop">${Y.POPULAR.slice(0, 6).map((s) => `<button type="button" class="pchip sm" data-my="${s}" aria-pressed="false"><b>${Y.esc(Y.short(s))}</b></button>`).join('')}</div>`; return; }
  el.innerHTML = `<h3><span>${T('My assets', '내 자산')}</span><a href="${window.DF_ROOT ? window.DF_ROOT + 'my/' : '../y2/'}">${T('Open', '열기')} →</a></h3><ul class="myl">${my.slice(0, 8).map((a) => { const q = MQ[a.sym], n = xs.filter((x) => Y.matches(x, a)).length;
    return `<li><span class="nm"><b>${Y.esc(Y.short(a.sym))}</b></span><span class="mono pv">${Y.fmtP(a, q)}</span><span class="mono pc">${Y.fmtCh(a, q)}</span><span class="nn" title="${T('stories in 24h', '24시간 소식')}">${n || ''}</span></li>`; }).join('')}</ul>
    <button type="button" class="more2" data-pick>${T('+ Add or remove', '+ 추가 · 빼기')}</button>`;
}
// 가격은 1분마다 띠·내 자산 칸만 고친다(본문을 다시 그리면 차트가 깜빡인다). 내 자산이 바뀌면 거르기 때문에 본문도 다시 그린다.
addEventListener('df-my', () => { pqAt = 0; if (!document.getElementById('pickdlg')?.open) { loadStrip(); render(true); } });

app.addEventListener('click', (e) => {
  if (e.target.closest('#myonly')) { S.mine = !S.mine; render(true); return; }
  if (e.target.closest('[data-pick]')) { Y.openPicker(() => { pqAt = 0; loadStrip(); render(true); }); return; } const so = e.target.closest('[data-sort]'); if (so) { SO = so.dataset.sort; try { localStorage.setItem('df-sort', SO); } catch (x) {} render(true); return; }
  const mk = e.target.closest('[data-mkt]'); if (mk) { M = mk.dataset.mkt; try { localStorage.setItem('df-mkt', M); } catch (x) {} render(true); return; }
  const t = e.target.closest('[data-th]'); if (t) { S.th = t.dataset.th; render(true); return; } const b = e.target.closest('[data-id]'); if (b) openSheet(store.byId.get(b.dataset.id)); });
start(() => render(false)); loadStrip(); setInterval(loadStrip, 60000); DFI.onLang(() => { drawStrip(); render(true); });
let rzT = 0, rzW = innerWidth; addEventListener('resize', () => { if (innerWidth === rzW) return; rzW = innerWidth; clearTimeout(rzT); rzT = setTimeout(() => app.querySelectorAll('canvas[data-t]').forEach((cv) => chart(cv, +cv.dataset.t, false)), 200); });   // 작은 그래프는 크기가 바뀌면 다시 그린다(큰 차트는 라이브러리가 맞춘다)

// ---------- 많이 언급된 이슈·종목(최근 3시간) ----------
// 종목: '내 자산' 목록(코인 · 주식 · 지수 · 금리·환율·원자재)에 있는 것만 센다(AI 판정의 coins 칸엔 회사 · NFT · 엉뚱한 글자가 섞여 들어오기도 해서).
// 기업: 상장 안 된 주요 AI 회사는 이름으로. 이슈: 며칠째 이어지는 이야기(정리 화면의 줄기)에 붙은 소식 수.
const ENT = [['Anthropic', '앤트로픽', /앤트로픽|anthropic/i], ['OpenAI', '오픈AI', /오픈\s?AI|openai/i], ['xAI', 'xAI', /\bxAI\b/], ['SpaceX', '스페이스X', /스페이스\s?X|spacex/i]];
const KIND = { crypto: ['Coin', '코인'], stock: ['Stock', '주식'], index: ['Index', '지수'], macro: ['Market', '시장 지표'], co: ['Company', '기업'], issue: ['Ongoing story', '이어지는 이야기'] };
let lastTr = null;
function trending(xs, now) {
  lastTr = [xs, now];
  const cnt = new Map(), add = (k, o) => { const c = cnt.get(k) || Object.assign({ n: 0 }, o); c.n++; cnt.set(k, c); };
  xs.filter((x) => now - x.t < 3 * 3600).forEach((it) => {
    const txt = (it.ko || '') + ' ' + (it.en || '');
    Y.UNIVERSE.forEach((a) => { if (Y.matches(it, a)) add(a.sym, { kind: a.kind, label: Y.short(a.sym), sub: a.kind === 'crypto' || a.kind === 'stock' ? Y.nm(a) : '' , full: Y.nm(a) }); });
    ENT.forEach(([en, ko, rx]) => { if (rx.test(txt)) add('e:' + en, { kind: 'co', label: T(en, ko) }); });
    const th = threadOf(it.id); if (th && th.t) add('t:' + th.id, { kind: 'issue', label: T(th.t[1], th.t[0]), href: briefHref(th.id) });
  });
  const rows = [...cnt.values()].map((c) => (c.kind === 'index' || c.kind === 'macro' ? Object.assign(c, { label: c.full }) : c))
    .sort((a, b) => b.n - a.n || (a.kind === 'issue') - (b.kind === 'issue')).slice(0, 6);
  const row = (c, i) => { const kd = T(...KIND[c.kind]) + (c.sub ? ' · ' + esc(c.sub) : ''), inner = `<span class="rk mono">${i + 1}</span><span class="nm2"><b>${esc(c.label)}</b><span class="kd">${kd}</span></span><span class="mono">${c.n}</span>`;
    return c.href ? `<a class="q" href="${c.href}">${inner}</a>` : `<p class="q">${inner}</p>`; };
  $('tr').innerHTML = `<h3>${T('Most mentioned · 3h', '많이 언급된 이슈·종목 · 3시간')}</h3>` + (rows.map(row).join('') || `<p class="mute">${T('Nothing stands out in the last 3 hours.', '최근 3시간 눈에 띄는 이슈가 없어요.')}</p>`);
}
// 이야기 색인은 따로 늦게 온다 → 오면 한 번 다시 센다
loadIndex().then(() => { if (lastTr) trending(...lastTr); });
