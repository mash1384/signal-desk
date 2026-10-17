// 테마 화면 공통: 크립토 · 나스닥 · 경제 · AI 한 테마를 깊게. 랜딩 지구 장면의 '상세판'.
// 자료: themes.json(3시간마다 Mac 에서 — AI 요약 6문장, 1시간 단위 호재·악재, 섹터, 주요·최근 소식, 자산 언급, 문장별 근거 소식)
//       시세 — 코인은 바이낸스, 주식·지수 선물·금리·달러·원자재는 우리 Worker /quotes(야후). 숫자는 모두 프로그램이 센 것, 문장만 AI.
import { T, L, esc, line, altLine, pill, bars, chips, outlets, hm, ago, openSheet, store, pxChip, fillPx, PRICED_ALL } from '../l/lk.js?v=1018063205';
export const THEME_KEYS = ['crypto', 'nasdaq', 'econ', 'ai', 'world'];
export const TNAME = { crypto: ['Crypto', '크립토'], nasdaq: ['Nasdaq', '나스닥'], econ: ['Economy', '경제'], ai: ['AI', 'AI'], world: ['World', '세계'] };
export const tn = (k) => TNAME[k][L() ? 1 : 0];
const WK = 'https://signal-scheduler.mash1384.workers.dev/quotes';
// 자산 목록: [기호, 출처(b=바이낸스, y=야후), 영문, 한글, 표시 방식]
export const ASSETS = {
  crypto: [['BTC', 'b', 'Bitcoin', '비트코인'], ['ETH', 'b', 'Ethereum', '이더리움'], ['SOL', 'b', 'Solana', '솔라나'], ['XRP', 'b', 'XRP', '리플'], ['BNB', 'b', 'BNB', 'BNB']],
  nasdaq: [['NQ=F', 'y', 'Nasdaq 100 futures', '나스닥 100 선물'], ['ES=F', 'y', 'S&P 500 futures', 'S&P 500 선물'], ['NVDA', 'y', 'Nvidia', '엔비디아'], ['AAPL', 'y', 'Apple', '애플'], ['MSFT', 'y', 'Microsoft', '마이크로소프트'],
    ['AMZN', 'y', 'Amazon', '아마존'], ['GOOGL', 'y', 'Alphabet', '알파벳'], ['META', 'y', 'Meta', '메타'], ['TSLA', 'y', 'Tesla', '테슬라'], ['AVGO', 'y', 'Broadcom', '브로드컴']],
  econ: [['^TNX', 'y', 'US 10-year yield', '미국 10년물 금리', 'pct'], ['^FVX', 'y', 'US 5-year yield', '미국 5년물 금리', 'pct'], ['DX-Y.NYB', 'y', 'US dollar index', '달러 지수'], ['GC=F', 'y', 'Gold', '금'],
    ['CL=F', 'y', 'WTI crude', 'WTI 유가'], ['KRW=X', 'y', 'USD/KRW', '원/달러', 'krw']],
  ai: [['NVDA', 'y', 'Nvidia', '엔비디아'], ['AMD', 'y', 'AMD', 'AMD'], ['TSM', 'y', 'TSMC', 'TSMC'], ['AVGO', 'y', 'Broadcom', '브로드컴'], ['MSFT', 'y', 'Microsoft', '마이크로소프트'],
    ['GOOGL', 'y', 'Alphabet', '알파벳'], ['META', 'y', 'Meta', '메타'], ['PLTR', 'y', 'Palantir', '팔란티어'], ['TAO', 'b', 'Bittensor', '비트텐서'], ['FET', 'b', 'Artificial Superintelligence', 'FET']],
  // 세계(전쟁·외교·에너지 등): 지정학 소식에 가장 먼저 반응하는 가격들
  world: [['CL=F', 'y', 'WTI crude', 'WTI 유가'], ['GC=F', 'y', 'Gold', '금'], ['DX-Y.NYB', 'y', 'US dollar index', '달러 지수'], ['^TNX', 'y', 'US 10-year yield', '미국 10년물 금리', 'pct'], ['BTC', 'b', 'Bitcoin', '비트코인']],
};
const YAHOO_OK = new Set(['NQ=F', 'ES=F', 'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'AVGO', 'AMD', 'TSM', 'PLTR', 'ORCL', 'NFLX', 'COIN', 'MSTR', 'HOOD', 'INTC', 'MU', 'ARM', 'SMCI', 'CRM', 'ADBE', 'QCOM', 'ASML']);
// 흐름 그래프 위에 겹치는 대표 가격
export const BENCH = { crypto: ['BTC', 'b', 'BTC'], nasdaq: ['NQ=F', 'y', T('Nasdaq 100 fut.', '나스닥 100 선물')], econ: ['^TNX', 'y', T('US 10Y', '미국 10년물')], ai: ['NVDA', 'y', 'NVDA'], world: ['CL=F', 'y', T('WTI crude', 'WTI 유가')] };
// ---------- 자료 ----------
let THEMES_DOC = null;
export async function loadThemes() {
  if (THEMES_DOC) return THEMES_DOC;
  const r = await fetch((window.DF_THEMES || 'https://raw.githubusercontent.com/mash1384/signal-desk/flash/daily/themes.json') + '?t=' + Math.floor(Date.now() / 60000));
  THEMES_DOC = await r.json();
  // 소식 상세 창(openSheet)이 같은 소식을 찾을 수 있게 store 에 넣어 둔다
  [...THEMES_DOC.themes, ...(THEMES_DOC.themes_x || [])].forEach((t) => [...(t.top || []), ...(t.latest || []), ...(t.more || [])].forEach((x) => { if (!store.byId.has(x.id)) store.byId.set(x.id, Object.assign({ th: [t.k] }, x)); }));
  return THEMES_DOC;
}
// 세계는 별도 칸(themes_x)에 있다(첫 화면 지구 장면은 기존 네 테마만 읽기 때문)
export const themeOf = (doc, k) => doc.themes.find((t) => t.k === k) || (doc.themes_x || []).find((t) => t.k === k) || { k, n: 0, u: 0, d: 0, s_ko: [], s_en: [], refs: [], hours: [], sectors: [], mentions: {}, top: [], latest: [], more: [], changes: [], changes_all: [] };
// 바이낸스: 24시간 시세 + 1시간 봉 24개(작은 그래프)
async function binance(syms) {
  const out = {}; if (!syms.length) return out;
  const put = (x) => { out[x.symbol.replace(/USDT$/, '')] = { p: +x.lastPrice, chg: +x.priceChangePercent, c: [] }; };
  // 한꺼번에 묻되, 바이낸스에 없는 코인이 하나라도 섞이면 묶음 전체가 거절되므로 그땐 하나씩
  try { const r = await fetch('https://data-api.binance.vision/api/v3/ticker/24hr?symbols=' + encodeURIComponent(JSON.stringify(syms.map((s) => s + 'USDT'))));
    if (!r.ok) throw 0; (await r.json()).forEach(put); }
  catch (e) { await Promise.all(syms.map(async (s) => { try { const r = await fetch(`https://data-api.binance.vision/api/v3/ticker/24hr?symbol=${s}USDT`); if (r.ok) put(await r.json()); } catch (x) {} })); }
  await Promise.all(Object.keys(out).map(async (s) => { try { const k = await (await fetch(`https://data-api.binance.vision/api/v3/klines?symbol=${s}USDT&interval=1h&limit=25`)).json(); out[s].c = k.map((x) => [x[0] / 1000, +x[4]]); } catch (e) {} }));
  return out;
}
async function yahoo(syms) {
  if (!syms.length) return {};
  // 모든 사용자가 같은 '전체 시세' 파일(1분 캐시)을 받고 필요한 것만
  try { const r = await fetch(WK.replace('/quotes', '/market') + '?i=1h'); if (!r.ok) return {}; const q = (await r.json()).q || {}; return Object.fromEntries(syms.filter((s) => q[s]).map((s) => [s, q[s]])); } catch (e) { return {}; }
}
// 이 테마의 자산 목록(고정 + 많이 언급된 것) → 시세까지
export async function loadAssets(k, t) {
  const base = ASSETS[k].map((a) => ({ sym: a[0], src: a[1], en: a[2], ko: a[3], fmt: a[4] || '' }));
  const have = new Set(base.map((a) => a.sym)), M = t.mentions || {};
  Object.keys(M).forEach((s) => { if (have.has(s) || base.length >= (k === 'crypto' ? 9 : 12)) return;
    if (k === 'crypto' && PRICED_ALL.has(s)) {   // 바이낸스 USDT 마켓이 있는 코인만(없는 코인을 물으면 요청이 거절된다)
      base.push({ sym: s, src: 'b', en: s, ko: s, fmt: '', extra: true }); have.add(s); }
    else if ((k === 'nasdaq' || k === 'ai') && YAHOO_OK.has(s)) { base.push({ sym: s, src: 'y', en: s, ko: s, fmt: '', extra: true }); have.add(s); } });
  const [b, y] = await Promise.all([binance(base.filter((a) => a.src === 'b').map((a) => a.sym)), yahoo(base.filter((a) => a.src === 'y').map((a) => a.sym))]);
  // 야후 '하루 변동'은 미국 장 밖에선 0 이거나 엉뚱해서, 1시간 봉에서 24시간 전 값과 비교해 직접 센다(바이낸스 24시간과 같은 뜻)
  Object.values(y).forEach((q) => { const c = q.c || [], now = Date.now() / 1000; if (c.length < 2) return; const last = c[c.length - 1][1];
    let ref = c[0]; for (const p of c) { if (p[0] <= now - 86400) ref = p; else break; } q.p = last; q.chg = ref[1] ? (last / ref[1] - 1) * 100 : null; q.dlt = last - ref[1]; q.c = c.filter((p) => p[0] >= now - 86400 - 3600); });
  return base.map((a) => Object.assign(a, { q: (a.src === 'b' ? b : y)[a.sym] || null, m: M[a.sym] || null })).filter((a) => a.q || !a.extra);
}
export async function benchSeries(k) {
  const [s, src] = BENCH[k];
  if (src === 'b') { try { const kl = await (await fetch(`https://data-api.binance.vision/api/v3/klines?symbol=${s}USDT&interval=1h&limit=25`)).json(); return kl.map((x) => [x[0] / 1000, +x[4]]); } catch (e) { return []; } }
  const q = (await yahoo([s]))[s]; return q ? q.c : [];
}
// ---------- 숫자 모양 ----------
export function fmtP(a) {
  const p = a.q && a.q.p; if (p == null) return '–';
  if (a.fmt === 'pct') return p.toFixed(3) + '%';
  if (a.fmt === 'krw') return p.toLocaleString('en-US', { maximumFractionDigits: 2 }) + (L() ? '원' : ' KRW');
  const d = p >= 1000 ? 0 : p >= 100 ? 2 : p >= 1 ? 2 : 4, usd = a.src === 'b' || (a.src === 'y' && /^[A-Z]{1,5}$/.test(a.sym));   // 주식·코인만 $ (지수·선물·달러 지수는 아님)
  return (usd ? '$' : '') + p.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
export const fmtC = (c) => (c == null ? '' : `<span class="${c > 0 ? 'up' : c < 0 ? 'down' : ''}">${DFD.pct(c, 2)}</span>`);
// 금리는 % 변동 대신 bp(0.01%p) 변동으로
export const fmtCh = (a) => { if (!a.q) return ''; if (a.fmt === 'pct' && a.q.dlt != null) { const bp = a.q.dlt * 100; return `<span class="${bp > 0 ? 'up' : bp < 0 ? 'down' : ''}">${bp > 0 ? '+' : bp < 0 ? '−' : ''}${Math.abs(bp).toFixed(1)}bp</span>`; } return fmtC(a.q.chg); };
// ---------- 작은 그래프(캔버스) ----------
export function spark(cv, pts, { up = null } = {}) {
  const r = cv.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2), W = Math.max(1, r.width), H = Math.max(1, r.height); cv.width = W * dpr; cv.height = H * dpr;
  const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H); const v = (pts || []).map((x) => x[1]).filter((x) => x != null); if (v.length < 2) return;
  const lo = Math.min(...v), hi = Math.max(...v), y = (x) => H - 2 - ((x - lo) / (hi - lo || 1)) * (H - 4), good = up ?? v[v.length - 1] >= v[0];
  g.beginPath(); v.forEach((p, i) => { const X = (i / (v.length - 1)) * W; i ? g.lineTo(X, y(p)) : g.moveTo(X, y(p)); });
  g.strokeStyle = good ? '#0e9f6e' : '#df4a3a'; g.lineWidth = 1.5; g.lineJoin = 'round'; g.stroke();
}
// ---------- 조각 ----------
// 테마 주소: 사이트에선 /themes/<k>/, 미리보기에선 ?t=<k>
const tHref = (k) => (window.DF_TBASE ? window.DF_TBASE + k + '/' : '?t=' + k);
export function tabsHTML(k) {
  return `<nav class="ttabs" role="tablist" aria-label="${T('Themes', '테마')}">${THEME_KEYS.map((x) => `<a role="tab" href="${tHref(x)}" data-theme="${x}" aria-selected="${x === k}">${tn(x)}</a>`).join('')}</nav>`;
}
export function statusHTML(doc, t) {
  const tot = Math.max(1, t.u + t.d), fu = t.u / tot;
  return `<p class="tstat"><span class="tnum"><b>${t.n}</b> ${T('stories in 24h', '건 · 지난 24시간')}</span><span class="tbal" role="img" aria-label="${T(`${t.u} bullish, ${t.d} bearish`, `호재 ${t.u}, 악재 ${t.d}`)}"><i class="u" style="width:${(fu * 100).toFixed(1)}%"></i><i class="d" style="width:${((1 - fu) * 100).toFixed(1)}%"></i></span>
    <span class="tnum"><b class="up">${t.u}</b> ${T('bullish', '호재')} · <b class="down">${t.d}</b> ${T('bearish', '악재')}</span></p>`;
}
export function summaryHTML(doc, t, { numbered = true } = {}) {
  const S = L() ? t.s_ko || [] : t.s_en || [], refs = t.refs || [];
  const made = new Date(doc.made * 1000), next = new Date((doc.next || doc.made + 10800) * 1000), f = (d) => d.toLocaleTimeString(L() ? 'ko-KR' : 'en-GB', { hour: '2-digit', minute: '2-digit' });
  const li = S.map((s, i) => { const id = refs[i]; const it = id && store.byId.get(id);
    return `<li>${numbered ? `<span class="n mono">${i + 1}</span>` : ''}<span class="s">${esc(s)}${it ? ` <button type="button" class="ref btnp" data-id="${id}" aria-label="${T('Open the source story', '근거 소식 열기')}">${T('Source', '근거')} ↗</button>` : ''}</span></li>`; }).join('');
  return `<div class="sum"><p class="k">${T('AI summary', 'AI 요약')} <span>· ${T(`updated ${f(made)} · next ${f(next)}`, `${f(made)} 갱신 · 다음 ${f(next)}`)}</span></p><ol>${li}</ol>
    <p class="fn">${T('Written by AI from judged stories and headlines. Counts are computed by the program. Not investment advice.', '판정한 속보와 기사 제목으로 AI가 쓴 요약이에요. 숫자는 프로그램이 셌어요. 투자 조언이 아니에요.')}</p></div>`;
}

// '오늘 무엇이 달라졌나' — 평소(최근 며칠)와 비교한 변화. 숫자도 문장도 프로그램이 만든다(AI 아님). 누르면 아래 소식이 그 신호의 소식만으로
const TONE = { up: ['▲', 'up'], down: ['▼', 'down'], flat: ['•', 'flat'] };
export function changesHTML(doc, t, cur) {
  const C = t.changes || [], nd = doc.base_days || 0;
  const made = new Date(doc.made * 1000), f = (d) => d.toLocaleTimeString(L() ? 'ko-KR' : 'en-GB', { hour: '2-digit', minute: '2-digit' });
  const li = C.map((c, i) => `<li><button type="button" class="chg btnp ${TONE[c.tone][1]}" data-chg="${i}" aria-pressed="${cur === i}" ${c.ids.length ? '' : 'disabled'}><span class="ic" aria-hidden="true">${TONE[c.tone][0]}</span><span class="s">${esc(L() ? c.ko : c.en)}</span>${c.ids.length ? `<span class="go">${T(`${c.ids.length} stories`, `소식 ${c.ids.length}건`)} →</span>` : ''}</button></li>`).join('');
  return `<div class="chs"><p class="k">${T('What changed today', '오늘 무엇이 달라졌나')} <span>· ${T(`vs the last ${nd} days · ${f(made)}`, `최근 ${nd}일과 비교 · ${f(made)} 기준`)}</span></p>
    ${C.length ? `<ol>${li}</ol>` : `<p class="mute">${T('Nothing stands out from the usual today.', '오늘은 평소와 다른 점이 눈에 띄지 않아요.')}</p>`}
    <p class="fn">${T(`Counted by the program from judged stories (no AI). "Normal" = the last ${nd} days; it widens to 7 days as history builds up.`, `판정한 소식으로 프로그램이 센 숫자예요(AI 문장 아님). '평소' = 최근 ${nd}일이고, 기록이 쌓이면 7일로 늘어나요.`)}</p></div>`;
}
// 24시간 흐름: 1시간 막대(위 호재 · 아래 악재) + 대표 가격선. Lightweight Charts
export function flowChart(el, doc, t, price, { height = 240 } = {}) {
  el.innerHTML = '<p class="lgd mono"></p><div class="lwbox"></div>'; const box = el.querySelector('.lwbox'), lgd = el.querySelector('.lgd'); box.style.height = height + 'px';
  const LW = window.LightweightCharts, off = -new Date().getTimezoneOffset() * 60, t0 = doc.made - 86400;
  const chart = LW.createChart(box, { autoSize: true, height, layout: { background: { color: 'transparent' }, textColor: '#7b8799', fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 11 },
    grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(13,37,61,.06)' } }, rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.1, bottom: 0.1 } }, leftPriceScale: { visible: false },
    timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true }, crosshair: { mode: 0 },
    handleScroll: { vertTouchDrag: true, mouseWheel: false, pressedMouseMove: false, horzTouchDrag: false }, handleScale: false });
  const hu = chart.addHistogramSeries({ priceScaleId: 'cnt', color: 'rgba(14,159,110,.75)', priceLineVisible: false, lastValueVisible: false });
  const hd = chart.addHistogramSeries({ priceScaleId: 'cnt', color: 'rgba(223,74,58,.7)', priceLineVisible: false, lastValueVisible: false });
  chart.priceScale('cnt').applyOptions({ scaleMargins: { top: 0.55, bottom: 0.02 }, visible: false });
  const H = t.hours || [], mx = Math.max(1, ...H.map((h) => Math.max(h[1], h[2])));
  hu.setData(H.map((h, i) => ({ time: t0 + i * 3600 + 1800 + off, value: h[1] }))); hd.setData(H.map((h, i) => ({ time: t0 + i * 3600 + 1800 + off, value: -h[2] })));
  chart.priceScale('cnt').applyOptions({ autoScale: false }); hu.applyOptions({ autoscaleInfoProvider: () => ({ priceRange: { minValue: -mx, maxValue: mx } }) }); hd.applyOptions({ autoscaleInfoProvider: () => ({ priceRange: { minValue: -mx, maxValue: mx } }) });
  let ln = null; const pts = (price || []).filter((p) => p[0] >= t0 - 3600);
  if (pts.length > 1) { ln = chart.addLineSeries({ color: '#0d253d', lineWidth: 2, priceLineVisible: false, lastValueVisible: true, crosshairMarkerRadius: 3 }); ln.setData(pts.map((p) => ({ time: p[0] + off, value: p[1] })));
    chart.priceScale('right').applyOptions({ scaleMargins: { top: 0.06, bottom: 0.5 } }); }
  chart.timeScale().fitContent();
  const name = BENCH[t.k][2], tf = (s) => new Date((s - off) * 1000).toLocaleTimeString(L() ? 'ko-KR' : 'en-GB', { hour: '2-digit', minute: '2-digit' });
  const idle = () => { const last = H[H.length - 1] || [0, 0, 0]; lgd.innerHTML = `<span>${T('Last hour', '최근 1시간')}</span> <b class="up">${T('bullish', '호재')} ${last[1]}</b> <b class="down">${T('bearish', '악재')} ${last[2]}</b>${pts.length ? ` · ${esc(name)} <b>${(+pts[pts.length - 1][1]).toLocaleString('en-US', { maximumFractionDigits: 2 })}</b>` : ''}`; };
  // 같은 칸·같은 값이면 범례를 다시 쓰지 않는다
  let key = null; const put = (k, html) => { if (k !== key) { key = k; lgd.innerHTML = html; } };
  key = 'idle'; idle();
  chart.subscribeCrosshairMove((p) => { if (!p || !p.time) { if (key !== 'idle') { key = 'idle'; idle(); } return; } const i = Math.floor((p.time - off - t0) / 3600), h = H[Math.max(0, Math.min(23, i))] || [0, 0, 0], pv = ln && p.seriesData.get(ln);
    put(i + ':' + (pv ? pv.value : ''), `<span>${tf(t0 + Math.max(0, i) * 3600 + off)}–${tf(t0 + (Math.max(0, i) + 1) * 3600 + off)}</span> <b>${h[0]} ${T('stories', '건')}</b> <b class="up">${T('bullish', '호재')} ${h[1]}</b> <b class="down">${T('bearish', '악재')} ${h[2]}</b>${pv ? ` · ${esc(name)} <b>${(+pv.value).toLocaleString('en-US', { maximumFractionDigits: 2 })}</b>` : ''}`); });
  return chart;
}
export const SORTS = { new: ['Latest', '최신순'], up: ['Bullish', '호재'], down: ['Bearish', '악재'], str: ['Strongest', '강도순'] };
export function sortSeg(cur) { return `<span class="mseg" role="group" aria-label="${T('Sort and filter', '정렬·거르기')}">${Object.keys(SORTS).map((k) => `<button type="button" data-sort="${k}" aria-pressed="${cur === k}">${SORTS[k][L() ? 1 : 0]}</button>`).join('')}</span>`; }
export function pickStories(t, so, sec, chg) {
  const all = new Map(); [...(t.latest || []), ...(t.top || []), ...(t.more || [])].forEach((x) => all.set(x.id, store.byId.get(x.id) || x));
  let xs = [...all.values()]; if (sec) xs = xs.filter((x) => x.sec === sec);
  if (chg != null && t.changes && t.changes[chg]) { const ids = new Set(t.changes[chg].ids); xs = xs.filter((x) => ids.has(x.id)); }
  if (so === 'up') xs = xs.filter((x) => x.v === '호재'); if (so === 'down') xs = xs.filter((x) => x.v === '악재');
  return so === 'str' ? xs.filter((x) => x.v !== '중립').sort((a, b) => b.s - a.s || (b.n || 1) - (a.n || 1) || b.t - a.t) : xs.sort((a, b) => b.t - a.t);
}
export function storyRow(it) {
  return `<li><button type="button" class="srow btnp" data-id="${it.id}"><span class="mt">${pill(it.v)}${bars(it)}<span class="ou">${ago(it.t)}${(it.n || 1) > 1 ? ' · ' + outlets(it) : ''}</span></span>
    <span class="ln">${esc(line(it))}</span><span class="mt">${pxChip(it)}${chips(it, 3, true)}</span></button></li>`;
}
export function assetsHTML(list, { compact = false } = {}) {
  const row = (a) => { const m = a.m; const tot = m ? Math.max(1, m.u + m.d) : 1;
    return `<tr><th scope="row"><b>${esc(L() ? a.ko : a.en)}</b><span class="sym mono">${esc(a.sym.replace('=F', '').replace('^', '').replace('-Y.NYB', 'Y'))}</span></th>
      <td class="p mono">${fmtP(a)}</td><td class="c mono">${fmtCh(a)}</td>${compact ? '' : `<td class="g"><canvas class="spk" data-sym="${esc(a.sym)}" aria-hidden="true"></canvas></td>`}
      <td class="m">${m ? `<span class="mono">${m.n}</span><span class="mb" aria-label="${T(`${m.u} bullish, ${m.d} bearish`, `호재 ${m.u}, 악재 ${m.d}`)}"><i class="u" style="width:${m.u / tot * 100}%"></i><i class="d" style="width:${m.d / tot * 100}%"></i></span>` : '<span class="mute2">–</span>'}</td></tr>`; };
  return `<table class="ast"><thead><tr><th scope="col">${T('Asset', '자산')}</th><th scope="col">${T('Price', '가격')}</th><th scope="col">${T('24h', '24시간')}</th>${compact ? '' : `<th scope="col"><span class="vh">${T('Chart', '그래프')}</span></th>`}<th scope="col">${T('Mentions', '언급')}</th></tr></thead><tbody>${list.map(row).join('')}</tbody></table>`;
}
export function drawSparks(root, list) { root.querySelectorAll('canvas.spk').forEach((cv) => { const a = list.find((x) => x.sym === cv.dataset.sym); if (a && a.q) spark(cv, a.q.c); }); }
export function sectorsHTML(t, cur) {
  const S = t.sectors || [], mx = Math.max(1, ...S.map((s) => s.n));
  return `<ul class="secs">${S.map((s) => `<li><button type="button" class="sec-b" data-sec="${s.k}" aria-pressed="${cur === s.k}"><span class="nm">${esc(L() ? s.ko : s.en)}</span><span class="bar" aria-hidden="true"><i class="u" style="width:${s.u / mx * 100}%"></i><i class="z" style="width:${(s.n - s.u - s.d) / mx * 100}%"></i><i class="d" style="width:${s.d / mx * 100}%"></i></span><span class="num mono">${s.n}</span></button></li>`).join('')}</ul>
    <p class="fn">${T('Green bullish · grey neutral · red bearish. Tap a sector to filter the stories.', '초록 호재 · 회색 중립 · 빨강 악재. 누르면 그 섹터 소식만 봐요.')}</p>`;
}
export async function eventsHTML() {
  try { const d = await (await fetch('https://mash1384.github.io/signal-desk/data/events.json')).json(), now = Date.now() / 1000;
    const xs = d.upcoming.filter((x) => x.ts > now).sort((a, b) => a.ts - b.ts).slice(0, 3);
    return `<ul class="evs">${xs.map((x) => `<li><span class="mono">${new Date(x.ts * 1000).toLocaleString(L() ? 'ko-KR' : 'en-GB', { month: 'short', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit' })}</span><b>${esc(L() ? x.title_ko || x.title : x.name_en || x.title)}</b>${'●'.repeat(x.level || 1)}</li>`).join('')}</ul>`; } catch (e) { return ''; }
}
export function wire(app, S, render) {
  app.addEventListener('click', (e) => {
    const th = e.target.closest('[data-theme]'); if (th) { e.preventDefault(); S.k = th.dataset.theme; S.sec = null; S.chg = null; history.pushState({ k: S.k }, '', tHref(S.k)); render(); return; }
    const so = e.target.closest('[data-sort]'); if (so) { S.so = so.dataset.sort; try { localStorage.setItem('df-sort', S.so); } catch (x) {} render(true); return; }
    const sc = e.target.closest('[data-sec]'); if (sc) { S.sec = S.sec === sc.dataset.sec ? null : sc.dataset.sec; S.chg = null; render(true); return; }
    const cg = e.target.closest('[data-chg]'); if (cg) { const i = +cg.dataset.chg; S.chg = S.chg === i ? null : i; S.sec = null; render(true); if (S.chg != null) document.getElementById('stories')?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }); return; }
    const mo = e.target.closest('[data-more]'); if (mo) { S.more = true; render(true); return; }
    const b = e.target.closest('[data-id]'); if (b) { const it = store.byId.get(b.dataset.id); if (it) openSheet(it); }
  });
}
export function initState() {
  const k = window.DF_THEME || new URLSearchParams(location.search).get('t'); let so = 'new'; try { so = localStorage.getItem('df-sort') || 'new'; } catch (e) {}
  return { k: THEME_KEYS.includes(k) ? k : 'crypto', so: SORTS[so] ? so : 'new', sec: null, chg: null, more: false };
}
export { fillPx };

export function filterChip(t, S) {
  if (S.sec) { const s = (t.sectors || []).find((x) => x.k === S.sec); return s ? ` <button type="button" class="secf" data-sec="${S.sec}">${esc(L() ? s.ko : s.en)} ×</button>` : ''; }
  if (S.chg != null && t.changes && t.changes[S.chg]) return ` <button type="button" class="secf" data-chg="${S.chg}">${T('This change', '이 변화의 소식')} ×</button>`;
  return '';
}
