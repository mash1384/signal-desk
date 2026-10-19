import { recentLimit } from './candles.js';
import * as V from './rv.js';
import { SORTS, MK } from './rv.js';
// R3 · Impact — Perplexity Discover·Kalshi 참고. 맨 위 '지금' 한 장: 최근 6시간 가장 큰 소식 + 그 뒤 가격 흐름(크게).
// 아래 카드 격자: 세기 3은 두 칸, 카드마다 '소식 이후' 작은 그래프. 정렬·거르기(최신순·호재·악재·강도순); 최신순 밖에선 중립 소식은 '그 밖의 소식' 목록으로. 오른쪽: 많이 언급된 이슈·종목.
import { lwChart, store, start, day, T, esc, line, hm, openSheet, fillPx, newGate } from './lk.js';

import * as Y from './yk.js';
import { loadIndex, threadOf, briefHref } from './thr.js';
const app = document.getElementById('app');
if (!app.dataset.prerender) app.innerHTML = V.shell();
const $ = (id) => document.getElementById(id), S = { th: 'all', mine: false };
// 신호 정렬·거르기: 최신순(중립 포함 모든 소식) · 호재 · 악재 · 강도순(세기 → 보도 수 → 최신). 선택은 저장

let SO = (() => { try { return localStorage.getItem('df-sort') || 'new'; } catch (e) { return 'new'; } })(); if (!SORTS[SO]) SO = 'new';
const sSeg = () => V.sSeg(SO);
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

let M = (() => { try { return localStorage.getItem('df-mkt') || 'btc'; } catch (e) { return 'btc'; } })(); if (!MK[M]) M = 'btc';
const WK = 'https://signal-scheduler.mash1384.workers.dev/index-candles';
const sc = new Map();
function series(m, iv) {   // [[t, close]] 지난 며칠(5m) 또는 이틀(1m). 60초 보관
  const times = [...app.querySelectorAll(iv === '1m' ? '.bigc[data-t]' : 'canvas[data-t]')].map(el => +el.dataset.t);
  const earliest = Math.min(...times) - (iv === '1m' ? 1800 : 3600), limit = recentLimit(earliest, iv === '1m' ? 60 : 300);
  const key = m + (m === 'btc' ? iv + ':' + limit : '1m'), hit = sc.get(key); if (hit && Date.now() - hit.at < 60000) return hit.p;
  const p = (m === 'btc' ? fetch(`https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=${iv}&limit=${limit}&endTime=${Date.now()}`).then((r) => r.ok ? r.json() : null).then((k) => (k ? k.map((x) => [x[0] / 1000, +x[4]]) : null))
    : DFD.live().then(bundle => bundle ? bundle.indices[m] : fetch(`${WK}?s=${m}&i=1m`).then(r => r.ok ? r.json() : null)).then((d) => (d && d.c ? d.c : null))).catch(() => null);
  sc.set(key, { at: Date.now(), p }); return p;
}
const mName = (m = M) => V.mName(m);
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
const mSeg = () => V.mSeg(M);
function drawCharts() { app.querySelectorAll('.bigc[data-t]:not([data-on])').forEach((el) => { el.dataset.on = '1'; bigChart(el, +el.dataset.t); }); app.querySelectorAll('canvas[data-t]').forEach((cv) => chart(cv, +cv.dataset.t, false)); app.querySelectorAll('[data-mname]').forEach((e) => (e.textContent = mName())); }
function render(force) {
  if (!store.items.length && app.dataset.prerender) return;
  const all = day(); if (!force && !gate.check()) return;
  const my = Y.getMy().map((k) => Y.BY[k]).filter(Boolean), mineOf = (x) => my.some((a) => Y.matches(x, a));
  if (S.mine && !my.length) S.mine = false;
  const xs = all.filter((x) => gate.visible(x)), ys = xs.filter((x) => (S.th === 'all' || x.th.includes(S.th)) && (!S.mine || mineOf(x)));
  $('myonly').setAttribute('aria-pressed', String(S.mine)); $('myonly').lastChild.textContent = T('My assets only', '내 자산만'); $('myonly').hidden = !my.length;
  $('tt').innerHTML = V.tabsHTML(xs, S.th);
  const now = Date.now() / 1000, recent = ys.filter((x) => now - x.t < 6 * 3600 && x.v !== '중립').sort((a, b) => score(b) - score(a) || b.t - a.t);
  const lead = recent[0];
  if (lead) {
    const html = V.leadHTML(lead, M);
    // 같은 소식·같은 시장·같은 언어면 차트는 두고 글만 바꾼다(매번 새로 만들면 깜빡이고 십자선이 끊긴다). 5분이 지나면 가격을 새로 그린다.
    const lk = lead.id + '|' + M + '|' + DFI.lang(), L0 = $('lead'), old = L0.querySelector('.ld > .tx');
    if (!L0.dataset.k && app.dataset.prerender && L0.querySelector('[data-id]')?.dataset.id === lead.id && M === 'btc') { L0.dataset.k = lk; L0.dataset.at = Date.now(); }
    if (L0.dataset.k === lk && old && Date.now() - +L0.dataset.at < 300000) { const tmp = document.createElement('div'); tmp.innerHTML = html; const tx = tmp.querySelector('.ld > .tx'); const clean = old.cloneNode(true); clean.removeAttribute('data-thb'); clean.querySelectorAll('.thb').forEach(el => el.remove()); if (!clean.isEqualNode(tx)) old.replaceWith(tx); }
    else { L0.innerHTML = html; L0.dataset.k = lk; L0.dataset.at = Date.now(); } }
  else { $('lead').innerHTML = ''; $('lead').dataset.k = ''; }
  $('gh').innerHTML = `<span class="ghl"><span>${T('Signals', '신호')}</span>${sSeg()}</span>${mSeg()}`;
  const sig = pick(ys, lead).slice(0, 24);
  $('grid').innerHTML = sig.map((it) => V.card(it, it.s >= 3, M)).join('') || `<p class="mute">${SO === 'up' ? T('No bullish stories in this theme in the last 24 hours.', '최근 24시간 이 테마의 호재가 없어요.') : SO === 'down' ? T('No bearish stories in this theme in the last 24 hours.', '최근 24시간 이 테마의 악재가 없어요.') : T('No signals in this theme yet.', '이 테마의 신호가 아직 없어요.')}</p>`;
  // '그 밖의 소식'(중립 목록)은 최신순에선 이미 위에 섞여 있으므로 숨긴다
  const showOther = SO !== 'new'; $('oh').textContent = showOther ? T('Also reported', '그 밖의 소식') : ''; $('oh').hidden = !showOther; $('other').hidden = !showOther;
  $('other').innerHTML = !showOther ? '' : ys.filter((x) => x.v === '중립').slice(0, 20).map((it) => `<li><button type="button" data-id="${it.id}"><span class="tm mono">${hm(it.t)}</span><span>${esc(line(it))}</span></button></li>`).join('');
  drawCharts();
  fillPx(app);
  trending(xs, now);
}

// ---------- 맨 위 가격 띠(업계 표준: 숫자 먼저) · 오른쪽 '내 자산' 칸 ----------
const STRIP = ['BTC', 'ETH', 'NQ=F', 'ES=F', '^TNX', 'GC=F'];
let PQ = {}, pqAt = 0;
async function loadStrip() {
  if (Date.now() - pqAt < 60000) return; pqAt = Date.now();
  const want = [...new Set([...STRIP, ...Y.getMy()])]; const q = await Y.loadQuotes(want); PQ = q; drawStrip();
}
// 가격 띠: 내 자산(☆)을 앞에, 기본 시장(BTC · ETH · 지수 · 금리 · 금)은 그 뒤에 — 오른쪽의 '내 자산' 칸은 이 띠와 겹쳐서 없앴다
function drawStrip() {
  const syms = [...new Set([...Y.getMy(), ...STRIP])].filter((s) => Y.BY[s]);
  $('ps').innerHTML = `<div class="wrap pin">${syms.map((s) => { const a = Y.BY[s], q = PQ[s];
    return `<div class="pi"><span class="nm">${Y.esc(Y.nm(a))}</span><span class="mono pv">${Y.fmtP(a, q)}</span><span class="mono pc">${Y.fmtCh(a, q)}</span><canvas class="spk" data-sym="${Y.esc(s)}" aria-hidden="true"></canvas><button type="button" class="mystar ic" data-my="${s}" aria-pressed="${Y.hasMy(s)}" aria-label="${T(`Add ${s} to My assets`, `${s} 내 자산에 추가`)}"><span class="st-ic" aria-hidden="true"></span></button></div>`; }).join('')}</div>`;
  Y.drawSparks($('ps'), PQ);
}
// 가격은 1분마다 띠만 고친다(본문을 다시 그리면 차트가 깜빡인다). 내 자산이 바뀌면 거르기 때문에 본문도 다시 그린다.
addEventListener('df-my', () => { pqAt = 0; if (!document.getElementById('pickdlg')?.open) { loadStrip(); render(true); } });

app.addEventListener('click', (e) => {
  if (e.target.closest('#myonly')) { S.mine = !S.mine; render(true); return; }
  if (e.target.closest('[data-pick]')) { Y.openPicker(() => { pqAt = 0; loadStrip(); render(true); }); return; } const so = e.target.closest('[data-sort]'); if (so) { SO = so.dataset.sort; try { localStorage.setItem('df-sort', SO); } catch (x) {} render(true); return; }
  const mk = e.target.closest('[data-mkt]'); if (mk) { M = mk.dataset.mkt; try { localStorage.setItem('df-mkt', M); } catch (x) {} render(true); return; }
  const t = e.target.closest('[data-th]'); if (t) { S.th = t.dataset.th; render(true); return; } const b = e.target.closest('[data-id]'); if (b && store.byId.has(b.dataset.id)) openSheet(store.byId.get(b.dataset.id)); });
start(() => render(false)); loadStrip(); Y.every(loadStrip, 60000); DFI.onLang(() => { drawStrip(); render(true); });
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
