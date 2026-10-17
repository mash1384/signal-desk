import { T, L, esc, store, start, line, pill, bars, ago, outlets, hm, openSheet, pxChip, fillPx, col } from './lk.js?v=e2db2637';
export { every } from './lk.js?v=e2db2637';
export { store, start, line, pill, bars, ago, outlets, hm, openSheet, pxChip, fillPx, esc, T, L };
const WK = 'https://signal-scheduler.mash1384.workers.dev/quotes';
const C = (s, en, ko, min = 1.2) => [s, 'crypto', en, ko, 'b', null, min];
const S = (s, en, ko, rx) => [s, 'stock', en, ko, 'y', rx, 1.5];
export const UNIVERSE = [
  C('BTC', 'Bitcoin', '비트코인', 0.8), C('ETH', 'Ethereum', '이더리움', 1.0), C('SOL', 'Solana', '솔라나'), C('XRP', 'XRP', '리플'), C('BNB', 'BNB', 'BNB'), C('DOGE', 'Dogecoin', '도지코인', 1.6),
  C('ADA', 'Cardano', '에이다'), C('LINK', 'Chainlink', '체인링크'), C('AVAX', 'Avalanche', '아발란체'), C('SUI', 'Sui', '수이'), C('TON', 'Toncoin', '톤코인'), C('HYPE', 'Hyperliquid', '하이퍼리퀴드', 1.6),
  C('TRX', 'Tron', '트론'), C('DOT', 'Polkadot', '폴카닷'), C('LTC', 'Litecoin', '라이트코인'), C('NEAR', 'NEAR', '니어'), C('APT', 'Aptos', '앱토스'), C('AAVE', 'Aave', '에이브'), C('UNI', 'Uniswap', '유니스왑'),
  C('ONDO', 'Ondo', '온도'), C('ENA', 'Ethena', '에테나'), C('TAO', 'Bittensor', '비트텐서', 1.6), C('FET', 'Artificial Superintelligence', 'FET', 1.6), C('PEPE', 'Pepe', '페페', 2), C('WLD', 'Worldcoin', '월드코인', 1.6), C('ARB', 'Arbitrum', '아비트럼'), C('OP', 'Optimism', '옵티미즘'),
  S('NVDA', 'Nvidia', '엔비디아', /엔비디아|nvidia|\bNVDA\b/i), S('AAPL', 'Apple', '애플', /애플|\bapple\b|\bAAPL\b/i), S('MSFT', 'Microsoft', '마이크로소프트', /마이크로소프트|microsoft|\bMSFT\b/i),
  S('AMZN', 'Amazon', '아마존', /아마존|amazon|\bAMZN\b/i), S('GOOGL', 'Alphabet', '알파벳(구글)', /알파벳|구글|alphabet|google|\bGOOGL?\b/i), S('META', 'Meta', '메타', /메타(?!마스크|버스|데이터|플래닛)|\bmeta platforms\b|\bMETA\b/), S('TSLA', 'Tesla', '테슬라', /테슬라|tesla|\bTSLA\b/i),
  S('AVGO', 'Broadcom', '브로드컴', /브로드컴|broadcom|\bAVGO\b/i), S('AMD', 'AMD', 'AMD', /\bAMD\b/), S('TSM', 'TSMC', 'TSMC', /TSMC|\bTSM\b/), S('PLTR', 'Palantir', '팔란티어', /팔란티어|palantir|\bPLTR\b/i),
  S('ORCL', 'Oracle', '오라클', /오라클|oracle|\bORCL\b/i), S('NFLX', 'Netflix', '넷플릭스', /넷플릭스|netflix|\bNFLX\b/i), S('COIN', 'Coinbase', '코인베이스', /코인베이스|coinbase|\bCOIN\b/), S('MSTR', 'Strategy', '스트래티지', /스트래티지|마이크로스트래티지|MicroStrategy|\bMSTR\b/),
  S('HOOD', 'Robinhood', '로빈후드', /로빈후드|robinhood|\bHOOD\b/i), S('INTC', 'Intel', '인텔', /인텔|intel|\bINTC\b/i), S('MU', 'Micron', '마이크론', /마이크론|micron|\bMU\b/), S('ARM', 'Arm', 'ARM', /\bArm Holdings\b|\bARM\b|암 홀딩스/), S('ASML', 'ASML', 'ASML', /ASML/),
  ['NQ=F', 'index', 'Nasdaq 100', '나스닥 100', 'y', /나스닥|nasdaq/i, 0.5], ['ES=F', 'index', 'S&P 500', 'S&P 500', 'y', /S&P|에스앤피/i, 0.4], ['YM=F', 'index', 'Dow Jones', '다우', 'y', /다우|\bdow\b/i, 0.4], ['^VIX', 'index', 'VIX', 'VIX(변동성)', 'y', /VIX|변동성 지수/i, 6],
  ['^TNX', 'macro', 'US 10Y yield', '미국 10년물 금리', 'y', /국채|금리|treasury|yield|\bFed\b|연준/i, 1.2], ['DX-Y.NYB', 'macro', 'Dollar index', '달러 지수', 'y', /달러 지수|달러지수|DXY|달러화|달러 강세|달러 약세|dollar/i, 0.3],
  ['GC=F', 'macro', 'Gold', '금', 'y', /금값|금 가격|금 선물|\bgold\b|(?<![가-힣])금(?=[이은을,\s])/i, 0.6], ['SI=F', 'macro', 'Silver', '은', 'y', /은값|은 가격|\bsilver\b/i, 1.0],
  ['CL=F', 'macro', 'WTI crude', 'WTI 유가', 'y', /유가|원유|WTI|브렌트|crude|\boil\b|OPEC/i, 1.0], ['KRW=X', 'macro', 'USD/KRW', '원/달러', 'y', /원\/달러|원·달러|원화|환율|\bKRW\b/i, 0.4], ['JPY=X', 'macro', 'USD/JPY', '엔/달러', 'y', /엔화|엔\/달러|일본은행|\bJPY\b|\byen\b|BOJ/i, 0.4],
].map(([sym, kind, en, ko, src, rx, min]) => ({ sym, kind, en, ko, src, rx, min }));
export const BY = Object.fromEntries(UNIVERSE.map((a) => [a.sym, a]));
export const nm = (a) => (L() ? a.ko : a.en);
export const short = (sym) => sym.replace('=F', '').replace('^', '').replace('-Y.NYB', 'Y').replace('=X', '');
export const KINDS = [['crypto', 'Crypto', '크립토'], ['stock', 'Stocks', '주식'], ['index', 'Indices', '지수'], ['macro', 'Rates · FX · Commodities', '금리·환율·원자재']];
export const POPULAR = ['BTC', 'ETH', 'SOL', 'NVDA', 'TSLA', 'AAPL', 'NQ=F', 'GC=F', '^TNX', 'KRW=X'];
const KEY = 'df-my';
export function getMy() {
  try { const v = JSON.parse(localStorage.getItem(KEY)); if (Array.isArray(v)) return v.filter((s) => BY[s]); } catch (e) {}
  try { const old = JSON.parse(localStorage.getItem('signal-watch')); if (Array.isArray(old) && old.length) { const v = old.map((s) => String(s).toUpperCase()).filter((s) => BY[s]); if (v.length) { setMy(v); return v; } } } catch (e) {}
  return [];
}
export function setMy(v) { try { localStorage.setItem(KEY, JSON.stringify([...new Set(v)].slice(0, 30))); } catch (e) {} dispatchEvent(new Event('df-my')); }
export const hasMy = (s) => getMy().includes(s);
export function toggleMy(s) { const v = getMy(); setMy(v.includes(s) ? v.filter((x) => x !== s) : [...v, s]); }
export function matches(it, a) {
  if (a.kind === 'crypto') return (it.coins || []).includes(a.sym);
  const txt = (it.ko || '') + ' ' + (it.en || ''); return a.rx ? a.rx.test(txt) : false;
}
export const storiesOf = (items, a) => items.filter((it) => matches(it, a));
export const score = (x) => (x.s || 1) * 3 + Math.min(x.n || 1, 4) * 1.5 + (x.v !== '중립' ? 1 : 0);
async function binance(syms, withSeries) {
  const out = {}; if (!syms.length) return out;
  const put = (x) => { out[x.symbol.replace(/USDT$/, '')] = { p: +x.lastPrice, chg: +x.priceChangePercent, c: [], m: [] }; };
  try { const r = await fetch('https://data-api.binance.vision/api/v3/ticker/24hr?symbols=' + encodeURIComponent(JSON.stringify(syms.map((s) => s + 'USDT')))); if (!r.ok) throw 0; (await r.json()).forEach(put); }
  catch (e) { await Promise.all(syms.map(async (s) => { try { const r = await fetch(`https://data-api.binance.vision/api/v3/ticker/24hr?symbol=${s}USDT`); if (r.ok) put(await r.json()); } catch (x) {} })); }
  if (withSeries) await Promise.all(Object.keys(out).map(async (s) => { try {
    const [h, m] = await Promise.all([fetch(`https://data-api.binance.vision/api/v3/klines?symbol=${s}USDT&interval=1h&limit=25`).then((r) => r.json()), fetch(`https://data-api.binance.vision/api/v3/klines?symbol=${s}USDT&interval=5m&limit=96`).then((r) => r.json())]);
    out[s].c = h.map((x) => [x[0] / 1000, +x[4]]); out[s].m = m.map((x) => [x[0] / 1000, +x[4]]); } catch (e) {} }));
  return out;
}
async function yahoo(syms) {
  if (!syms.length) return {};
  const get = async (i) => { try { const bundle = await DFD.live(); if (bundle) return bundle.market[i].q; const r = await fetch(`${WK.replace('/quotes', '/market')}?i=${i}`); return r.ok ? (await r.json()).q || {} : {}; } catch (e) { return {}; } };
  const [h, m] = await Promise.all([get('1h'), get('5m')]), now = Date.now() / 1000, out = {};
  syms.forEach((s) => { const c = (h[s] || {}).c || [], mm = (m[s] || {}).c || []; if (!c.length && !mm.length) return; const last = (mm.length ? mm : c)[(mm.length ? mm : c).length - 1][1];
    let ref = c[0] || mm[0]; for (const p of c) { if (p[0] <= now - 86400) ref = p; else break; }
    out[s] = { p: last, chg: ref && ref[1] ? (last / ref[1] - 1) * 100 : null, dlt: ref ? last - ref[1] : null, c: c.filter((p) => p[0] >= now - 86400 - 3600), m: mm, closed: mm.length ? now - mm[mm.length - 1][0] > 1800 : true }; });
  return out;
}
export async function loadQuotes(syms, withSeries = true) {
  const as = syms.map((s) => BY[s]).filter(Boolean);
  const [b, y] = await Promise.all([binance(as.filter((a) => a.src === 'b').map((a) => a.sym), withSeries), yahoo(as.filter((a) => a.src === 'y').map((a) => a.sym))]);
  return Object.assign({}, b, y);
}
export function moves(syms, Q, items) {
  const out = [], now = Date.now() / 1000;
  syms.forEach((s) => { const a = BY[s], q = Q[s]; if (!a || !q || !q.m || q.m.length < 12 || q.closed) return;
    const m = q.m, last = m[m.length - 1], i0 = m.findIndex((p) => p[0] >= last[0] - 15 * 60); if (i0 < 1) return;
    const ret = (last[1] / m[i0 - 1][1] - 1) * 100;
    const r15 = []; for (let i = 3; i < m.length - 3; i++) r15.push((m[i][1] / m[i - 3][1] - 1) * 100);
    const sd = Math.sqrt(r15.reduce((t, x) => t + x * x, 0) / Math.max(1, r15.length)) || 1e-9;
    if (Math.abs(ret) >= a.min && Math.abs(ret) / sd >= 3 && now - last[0] < 20 * 60) {
      const rel = storiesOf(items.filter((it) => it.t >= m[i0 - 1][0] - 45 * 60), a).sort((x, y) => score(y) - score(x));
      out.push({ sym: s, ret, z: Math.abs(ret) / sd, from: m[i0 - 1][0], to: last[0], stories: rel.slice(0, 4) }); } });
  return out.sort((x, y) => y.z - x.z);
}
export function fmtP(a, q) {
  if (!q || q.p == null) return '–'; const p = q.p;
  if (a.sym === '^TNX') return p.toFixed(3) + '%';
  if (a.sym === 'KRW=X') return p.toLocaleString('en-US', { maximumFractionDigits: 2 }) + (L() ? '원' : '');
  const d = p >= 1000 ? 0 : p >= 1 ? 2 : p >= 0.01 ? 4 : 8, usd = a.kind === 'crypto' || a.kind === 'stock';
  return (usd ? '$' : '') + p.toLocaleString('en-US', { minimumFractionDigits: Math.min(d, 2), maximumFractionDigits: d });
}
export function fmtCh(a, q) {
  if (!q || q.chg == null) return ''; if (a.sym === '^TNX' && q.dlt != null) { const bp = q.dlt * 100; return `<span class="${bp > 0 ? 'up' : bp < 0 ? 'down' : ''}">${bp > 0 ? '+' : bp < 0 ? '−' : ''}${Math.abs(bp).toFixed(1)}bp</span>`; }
  return `<span class="${q.chg > 0 ? 'up' : q.chg < 0 ? 'down' : ''}">${DFD.pct(q.chg, 2)}</span>`;
}
export function spark(cv, pts) {
  const r = cv.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2), W = Math.max(1, r.width), H = Math.max(1, r.height); cv.width = W * dpr; cv.height = H * dpr;
  const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H); const v = (pts || []).map((x) => x[1]).filter((x) => x != null); if (v.length < 2) return;
  const lo = Math.min(...v), hi = Math.max(...v), y = (x) => H - 2 - ((x - lo) / (hi - lo || 1)) * (H - 4);
  g.beginPath(); v.forEach((p, i) => { const X = (i / (v.length - 1)) * W; i ? g.lineTo(X, y(p)) : g.moveTo(X, y(p)); }); g.strokeStyle = v[v.length - 1] >= v[0] ? col('#0e9f6e') : col('#df4a3a'); g.lineWidth = 1.5; g.lineJoin = 'round'; g.stroke();
}
export const drawSparks = (root, Q) => root.querySelectorAll('canvas.spk').forEach((cv) => { const q = Q[cv.dataset.sym]; if (q) spark(cv, q.c); });
export function pickerHTML(cur) {
  const my = new Set(getMy());
  return `<div class="pick"><label class="psrch"><span aria-hidden="true">⌕</span><input type="search" id="pq" placeholder="${T('Search assets — BTC, Nvidia, gold…', '자산 찾기 — BTC, 엔비디아, 금…')}" autocomplete="off"></label>
    ${KINDS.map(([k, en, ko]) => `<section class="pk" data-kind="${k}"><h3>${L() ? ko : en}</h3><div class="pchips">${UNIVERSE.filter((a) => a.kind === k).map((a) => `<button type="button" class="pchip" data-my="${a.sym}" aria-pressed="${my.has(a.sym)}" data-name="${(a.en + ' ' + a.ko + ' ' + a.sym).toLowerCase()}"><b>${esc(short(a.sym))}</b><span>${esc(nm(a))}</span></button>`).join('')}</div></section>`).join('')}</div>`;
}
export function wirePicker(root) {
  root.addEventListener('input', (e) => { if (e.target.id !== 'pq') return; const q = e.target.value.trim().toLowerCase(); root.querySelectorAll('.pchip').forEach((b) => { b.hidden = q && !b.dataset.name.includes(q); }); root.querySelectorAll('.pk').forEach((s) => { s.hidden = ![...s.querySelectorAll('.pchip')].some((b) => !b.hidden); }); });
}
addEventListener('click', (e) => { const b = e.target.closest('[data-my]'); if (!b) return; e.preventDefault(); e.stopPropagation(); toggleMy(b.dataset.my); const on = hasMy(b.dataset.my);
  document.querySelectorAll(`[data-my="${CSS.escape(b.dataset.my)}"]`).forEach((x) => { x.setAttribute('aria-pressed', String(on)); }); }, true);

new MutationObserver(() => { document.querySelectorAll('.mystars[data-sid]:not([data-done])').forEach((el) => { el.dataset.done = '1'; const it = store.byId.get(el.dataset.sid); if (!it) return;
  const as = UNIVERSE.filter((a) => matches(it, a)).slice(0, 4); if (!as.length) return;
  el.innerHTML = `<p class="msk">${T('Add to My assets', '내 자산에 추가')}</p>` + as.map((a) => `<button type="button" class="mystar" data-my="${a.sym}" aria-pressed="${hasMy(a.sym)}"><span class="st-ic" aria-hidden="true"></span>${esc(short(a.sym))} <span>${esc(nm(a))}</span></button>`).join(''); }); }).observe(document.body, { childList: true, subtree: true });
export function openPicker(onDone) {
  let d = document.getElementById('pickdlg');
  if (!d) { d = document.createElement('dialog'); d.id = 'pickdlg'; d.className = 'pdlg'; document.body.appendChild(d); wirePicker(d);
    d.addEventListener('click', (e) => { if (e.target === d || e.target.closest('[data-close-pick]')) d.close(); }); }
  d.innerHTML = `<div class="pdin"><header><h2>${T('My assets', '내 자산')}</h2><p>${T('Pick what you hold or watch. Saved only in this browser.', '갖고 있거나 지켜보는 자산을 고르세요. 이 브라우저에만 저장돼요.')}</p><button type="button" class="x" data-close-pick aria-label="${T('Close', '닫기')}">×</button></header>${pickerHTML()}<footer><button type="button" class="btn p" data-close-pick>${T('Done', '완료')}</button></footer></div>`;
  d.onclose = () => onDone && onDone(); d.showModal(); d.querySelector('#pq').focus();
}
export function alertsHTML(mv) {
  return mv.map((m) => { const a = BY[m.sym], up = m.ret > 0;
    return `<div class="alert ${up ? 'up' : 'down'}" role="status"><p class="ah"><b>${esc(short(m.sym))}</b> ${esc(nm(a))} <span class="mono">${up ? '+' : '−'}${Math.abs(m.ret).toFixed(2)}%</span> <span class="w">${T(`in ${Math.round((m.to - m.from) / 60)} min · ${m.z.toFixed(1)}× its usual 15-min move`, `${Math.round((m.to - m.from) / 60)}분 · 평소 15분 흔들림의 ${m.z.toFixed(1)}배`)}</span></p>
      ${m.stories.length ? `<p class="as">${T('Stories in the same window', '같은 시간대 관련 소식')}</p><ul>${m.stories.map((it) => `<li><button type="button" class="btnp" data-id="${it.id}">${pill(it.v)} <span>${esc(line(it))}</span> <span class="ou">${hm(it.t)}</span></button></li>`).join('')}</ul>` : `<p class="as">${T('No related story yet in our feed — it may be flow-driven.', '아직 관련 소식이 없어요(수급일 수 있어요).')}</p>`}</div>`; }).join('');
}
export function topHTML(items, n = 3) {
  const xs = items.filter((x) => x.t >= Date.now() / 1000 - 86400 && x.v !== '중립').sort((a, b) => score(b) - score(a) || b.t - a.t).slice(0, n);
  if (!xs.length) return `<p class="mute">${T('Nothing big on your assets in the last 24 hours.', '지난 24시간 내 자산에 큰 소식이 없어요.')}</p>`;
  return `<ol class="top3">${xs.map((it, i) => `<li><button type="button" class="btnp" data-id="${it.id}"><span class="n mono">${i + 1}</span><span class="b"><span class="mt">${pill(it.v)}${bars(it)}<span class="ou">${ago(it.t)} · ${outlets(it)}</span></span><span class="ln">${esc(line(it))}</span><span class="tg">${assetTags(it)}</span></span></button></li>`).join('')}</ol>`;
}
export const assetTags = (it) => getMy().map((s) => BY[s]).filter((a) => a && matches(it, a)).slice(0, 3).map((a) => `<span class="atag">${esc(short(a.sym))}</span>`).join('');
export const SORTS = { new: ['Latest', '최신순'], up: ['Bullish', '호재'], down: ['Bearish', '악재'], str: ['Strongest', '강도순'] };
export const sortSeg = (cur) => `<span class="mseg" role="group" aria-label="${T('Sort and filter', '정렬·거르기')}">${Object.keys(SORTS).map((k) => `<button type="button" data-sort="${k}" aria-pressed="${cur === k}">${SORTS[k][L() ? 1 : 0]}</button>`).join('')}</span>`;
export function sorted(xs, so) {
  if (so === 'up') xs = xs.filter((x) => x.v === '호재'); if (so === 'down') xs = xs.filter((x) => x.v === '악재');
  return so === 'str' ? xs.filter((x) => x.v !== '중립').sort((a, b) => b.s - a.s || (b.n || 1) - (a.n || 1) || b.t - a.t) : xs.sort((a, b) => b.t - a.t);
}
export const row = (it) => `<li><button type="button" class="srow btnp" data-id="${it.id}"><span class="mt">${pill(it.v)}${bars(it)}<span class="ou">${ago(it.t)}${(it.n || 1) > 1 ? ' · ' + outlets(it) : ''}</span>${assetTags(it)}</span><span class="ln">${esc(line(it))}</span></button></li>`;
export function emptyHTML() {
  return `<section class="empty-my"><h1>${T('Follow what you own', '내 자산만 따라가 보세요')}</h1><p>${T('Pick a few assets. We’ll show only the news that touches them, flag sudden moves, and keep it in this browser.', '자산 몇 개만 고르면, 그 자산에 닿는 소식만 모아 보여 주고 급하게 움직일 때 알려 드려요. 이 브라우저에만 저장돼요.')}</p>
    <div class="pop">${POPULAR.map((s) => { const a = BY[s]; return `<button type="button" class="pchip" data-my="${s}" aria-pressed="${hasMy(s)}"><b>${esc(short(s))}</b><span>${esc(nm(a))}</span></button>`; }).join('')}</div>
    <div class="ea"><button type="button" class="btn p" data-go>${T('Show my feed', '내 피드 보기')}</button><button type="button" class="btn g" data-pick>${T('More assets', '더 많은 자산')}</button></div></section>`;
}
export function initSort() { let so = 'new'; try { so = localStorage.getItem('df-sort') || 'new'; } catch (e) {} return SORTS[so] ? so : 'new'; }
let TH = null;   // 한 번만 받는다: 동시에 여러 번 불려도(첫 그리기 · 언어 · 영어 사전 도착) 요청은 하나
export function loadThemes() { return TH || (TH = fetch(DFD.data('daily/themes.json') + '?t=' + Math.floor(Date.now() / 60000)).then((r) => r.json()).catch(() => ({ themes: [] }))); }
export function daySummaryHTML(my, items, th) {
  const day = items.filter((x) => x.t >= Date.now() / 1000 - 86400);
  const per = my.map((s) => { const a = BY[s], xs = day.filter((x) => matches(x, a));
    return { s, top: xs.slice().sort((p, q) => score(q) - score(p) || q.t - p.t)[0] }; }).filter((p) => p.top);
  const mine = new Set(my), sig = [];
  ((th && th.themes) || []).forEach((t) => (t.changes_all || []).forEach((c) => { if (c.k === 'asset' && mine.has(c.sym) && !sig.some((x) => x.sym === c.sym)) sig.push(c); }));
  const quiet = my.filter((s) => !per.some((p) => p.s === s));
  return `<div class="dsum"><p class="k">${T('My day in 30 seconds', '내 자산 하루 요약')} <span>· ${T('the biggest story on each asset, last 24 hours', '자산마다 가장 큰 소식 · 지난 24시간')}</span></p>
    ${per.length ? `<ul class="lean news">${per.slice(0, 6).map((p) => `<li><button type="button" class="btnp" data-id="${p.top.id}"><b>${esc(short(p.s))}</b>${pill(p.top.v)}<span class="hl">${esc(line(p.top))}</span><span class="mono tm">${ago(p.top.t)}</span></button></li>`).join('')}</ul>` : ''}
    ${sig.length ? `<p class="sub2">${T('Different from usual', '평소와 다른 점')}</p><ul class="sig">${sig.slice(0, 3).map((c) => `<li>${esc(L() ? c.ko : c.en)}</li>`).join('')}</ul>` : ''}
    ${quiet.length ? `<p class="qt">${T(`Quiet: ${quiet.map(short).join(', ')} — no stories in 24h.`, `조용함: ${quiet.map(short).join(', ')} — 24시간 소식 없음.`)}</p>` : ''}
    <p class="lk"><a href="${window.DF_ROOT || '../../'}daily/">${T('Full daily brief', '전체 하루 정리')} →</a></p></div>`;
}
