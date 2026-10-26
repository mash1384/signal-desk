import { sinceLimit } from './candles.js';
import { whenVisible } from './charts.js';
import { watchThreads } from './thr.js';
// 라이브 페이지 후보 공통: 실시간 속보 받기(30초마다), 테마 나누기, 카드·상세, 24시간 막대, 소식 이후 가격 변화
export const L = () => DFI.lang() === 'ko';
// 다크 모드: 캔버스 · 차트 색을 테마에 맞춘다(CSS 변수가 닿지 않는 곳)
export const dark = () => typeof document !== 'undefined' && document.documentElement.dataset.theme === 'dark';
export const tone = (a) => (dark() ? `rgba(232,238,246,${a})` : `rgba(13,37,61,${a})`);
export const ink = () => (dark() ? '#e8eef6' : '#0d253d');
// 그림 색(캔버스 · 차트): 밝은 색 그대로 쓰고 다크일 때만 바꾼다. 표에 없는 색은 그대로
const DK = { '#0d253d': '#e8eef6', '#533afd': '#a99dff', '#64748b': '#a3b2c7', '#7b8799': '#a3b2c7', '#8a96aa': '#8d9bb2', '#fff': '#111b2b', '#0e9f6e': '#3fd29b',
  '#df4a3a': '#ff8e80', '#087a55': '#3fd29b', '#c43a2c': '#ff8e80', '#c2410c': '#ff9a5c', '#4a6aa3': '#8fb0ea', '#b45309': '#f0a24a', '#0f766e': '#4fd1c5' };
const DKR = { '13,37,61': '232,238,246', '83,58,253': '169,157,255', '14,159,110': '63,210,155', '223,74,58': '255,142,128', '8,122,85': '63,210,155', '196,58,44': '255,142,128' };
export const col = (c) => (!dark() ? c : DK[c] || c.replace(/^rgba\((\d+,\d+,\d+),/, (m, k) => (DKR[k] ? `rgba(${DKR[k]},` : m)));
export const T = (en, ko) => (L() ? ko : en);
export const esc = (s) => DFD.esc(s);

// ---------- 테마 ----------
export const THEMES = [
  { k: 'all', en: 'All', ko: '전체' }, { k: 'crypto', en: 'Crypto', ko: '크립토' }, { k: 'nasdaq', en: 'Nasdaq', ko: '나스닥' },
  { k: 'econ', en: 'Economy', ko: '경제' }, { k: 'ai', en: 'AI', ko: 'AI' }, { k: 'world', en: 'World', ko: '세계' },
];
const RX = {
  crypto: /비트코인|이더리움|코인|가상자산|암호화폐|스테이블코인|거래소|토큰|블록체인|디파이|온체인|NFT|채굴|에어드랍|ETF/,
  nasdaq: /나스닥|S&P|다우|증시|주가|엔비디아|애플|테슬라|마이크로소프트|아마존|메타|알파벳|구글|반도체|기술주|실적|브로드컴|팔란티어|마이크론|TSMC|AMD/,
  econ: /연준|Fed|FOMC|CPI|PPI|물가|인플레이션|금리|국채|고용|실업|GDP|PCE|소매판매|환율|재무부|파월|관세|경기|유가|원유|달러화|달러 지수|DXY|국채 금리/,
  ai: /(?<![A-Za-z])AI(?![A-Za-z])|인공지능|오픈AI|OpenAI|앤트로픽|Anthropic|챗GPT|ChatGPT|LLM|딥시크|제미나이|데이터센터|xAI|그록/,
};
export function themesOf(it) {
  const ko = it.ko || '', out = [];
  if ((it.coins && it.coins.length) || RX.crypto.test(ko)) out.push('crypto');
  if (RX.nasdaq.test(ko)) out.push('nasdaq');
  if (RX.econ.test(ko) || (it.kind === 'data' && !(it.coins || []).length)) out.push('econ');
  if ((it.sectors || []).includes('ai') || RX.ai.test(ko)) out.push('ai');
  if (!out.length) out.push('world');
  return out;
}
export const thName = (k) => { const t = THEMES.find((x) => x.k === k); return t ? t[L() ? 'ko' : 'en'] : k; };
const KIND = { event: ['Event', '사건'], data: ['Data', '지표'], price_recap: ['Market move', '시세'], opinion: ['Remarks', '발언'] };
export const kindName = (k) => (KIND[k] || [k, k])[L() ? 1 : 0];

// ---------- 데이터 ----------
export const store = { items: [], byId: new Map(), feed: [], fresh: new Set(), subs: [] };
export const line = (it) => (L() ? it.ko : it.en || it.ko);
export const altLine = (it) => (L() ? it.en || '' : '');   // 영어 화면엔 한국어 원문을 덧붙이지 않는다
// 익명 이벤트 통계(합계만 · 쿠키 없음, 추적 거부면 안 보냄): 기사 열기 · 원문 이동 · 차트 조작 · 언어 전환
const STATS = 'https://signal-scheduler.mash1384.workers.dev/e';
export function track(ev, lang) {
  try { if (navigator.doNotTrack === '1' || navigator.globalPrivacyControl || !window.DF_PAGE) return;
    navigator.sendBeacon(`${STATS}?e=${ev}&k=${window.DF_PAGE}&l=${lang || (L() ? 'ko' : 'en')}&d=${matchMedia('(max-width: 899px)').matches ? 'm' : 'd'}`); } catch (e) {}
}
if (typeof addEventListener === 'function') {   // 빌드 때 미리 그리기(Node)에서는 건너뛴다
  // 원문 이동 · 언어 버튼(사용자가 누른 것만 — DFI.onLang 은 첫 로드에도 불려 세면 안 된다)
  addEventListener('click', (e) => { const t = e.target.closest ? e.target : null; if (!t) return;
    const a = t.closest('a[href^="http"]'); if (a && !a.href.startsWith(location.origin)) track('out');
    const b = t.closest('[data-lang]'); if (b) track('lang', b.dataset.lang === 'ko' ? 'ko' : 'en'); }, true);
}
let charted = false;
// 업데이트 지연 안내: 속보가 20분 넘게 안 바뀌면(정상이면 10분마다 생존 신호) 화면 아래에 떠 있는 작은 안내 — 자리를 밀지 않는다
function stale(at) {
  let el = document.getElementById('stale'); const old = at && Date.now() / 1000 - at > 1200;
  if (!old) { if (el) el.hidden = true; return; }
  if (!el) { el = document.createElement('p'); el.id = 'stale'; el.setAttribute('role', 'status'); document.body.appendChild(el); }
  el.textContent = T(`Updates delayed · last update ${hm(at)}`, `업데이트 지연 · 마지막 갱신 ${hm(at)}`); el.hidden = false;
}
function merge(items) {
  const seen = store.byId.size > 0;
  items.forEach((it) => { if (!store.byId.has(it.id)) { it.th = themesOf(it); store.byId.set(it.id, it); if (seen) store.fresh.add(it.id); } else Object.assign(store.byId.get(it.id), it, { th: themesOf(it) }); });
  store.items = [...store.byId.values()].sort((a, b) => b.t - a.t);
  store.subs.forEach((f) => f());
  setTimeout(() => store.fresh.clear(), 4000);
}
async function pull() {
  let d; try { d = await DFD.flash(); } catch (e) { return; }
  stale(d.at); merge(d.items);
}
// 속보 빠른 확인(2026-10-26): 화면을 보고 있으면 5초마다 '새 소식만' 받아 합친다. 창이 뒤에 있으면 쉬고(30초 전체 받기가 맡음), 숨기면 멈춘다.
// 서버가 바쁘다(503 · 429)고 하면 Retry-After 만큼, 다른 실패는 1분 쉰다. 마지막 소식보다 10분 앞부터 물어 늦게 판정된 소식도 놓치지 않는다
let fastBusy = false, fastNext = 0, fastOn = false;
const changed = (it) => { const o = store.byId.get(it.id); return !o || ['v', 's', 'n', 'ko', 'en', 'kind', 'link'].some((k) => (o[k] ?? '') !== (it[k] ?? '')); };
async function fast() {
  if (document.hidden || !document.hasFocus() || fastBusy || Date.now() < fastNext || !store.items.length) return;
  fastBusy = true;
  const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), 8000);   // 응답이 멈춰도 8초 뒤 풀고 1분 뒤 다시(R24-F1)
  try {
    const r = await DFD.flashNew(store.items[0].t - 600, ctl.signal);
    if (r.status === 503 || r.status === 429) { fastNext = Date.now() + (Number(r.headers.get('retry-after')) || 30) * 1000; return; }
    if (!r.ok) { fastNext = Date.now() + 60000; return; }
    const d = await r.json();
    // 새 소식뿐 아니라 이미 있는 소식의 판정 · 영어 · 보도 수가 바뀐 것도 합친다(R24-F2). 바뀐 게 없으면 다시 그리지 않는다
    if (Array.isArray(d.items) && d.items.some(changed)) { stale(d.at); merge(d.items); }
  } catch (e) { fastNext = Date.now() + 60000; } finally { clearTimeout(timer); fastBusy = false; }
}
// 주기 요청: 화면이 숨겨진 탭(다른 탭 · 최소화 · 잠금)에서는 쉬고, 다시 보이면 밀린 한 번을 바로 한다 — Worker 요청을 아낀다
export function every(fn, ms) {
  let last = Date.now();
  const run = () => { last = Date.now(); fn(); };
  setInterval(() => { if (!document.hidden && Date.now() - last >= ms * 0.9) run(); }, ms);
  document.addEventListener('visibilitychange', () => { if (!document.hidden && Date.now() - last >= ms) run(); });
}
export function start(onData) { store.subs.push(onData); pull(); every(pull, 30000); if (!fastOn) { fastOn = true; setInterval(fast, 5000); } DFI.onLang(onData);
  fetch((window.DF_ROOT || 'https://mash1384.github.io/signal-desk/') + 'data/related.json').then((r) => r.json()).then((d) => { store.feed = d.items || []; }).catch(() => {}); }
export const day = () => { const s = Date.now() / 1000 - 86400; return store.items.filter((x) => x.t >= s); };
export const counts = (xs) => ({ n: xs.length, u: xs.filter((x) => x.v === '호재').length, d: xs.filter((x) => x.v === '악재').length });

// ---------- 시간 ----------
export const hm = (t) => DFD.hm(t);
export const ago = (t) => DFI.ago(t);

// ---------- 조각 ----------
export const pill = (v) => `<span class="pill ${DFD.vcls(v)}">${DFI.v(v)}</span>`;
export const bars = (it) => `<span class="st ${DFD.vcls(it.v)}" title="${T('Strength', '세기')} ${it.s}/3">${[0, 1, 2].map((b) => `<i class="${b < it.s ? 'on' : ''}"></i>`).join('')}</span>`;
export const chips = (it, n = 3, skipPx = false) => [...(it.coins || []).filter((c, i) => !(skipPx && c === (it.coins || []).find((x) => PX_SET.has(x)))).slice(0, n).map((c) => `<span class="chip">${c}</span>`), ...(it.th || []).filter((k) => k !== 'world' && !(k === 'crypto' && (it.coins || []).length)).slice(0, 2).map((k) => `<span class="chip th">${thName(k)}</span>`)].join('');
export const outlets = (it) => DFI.outlets(it.n || 1);

const PX_SET = new Set(['BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'DOGE', 'ADA', 'LINK', 'AVAX', 'SUI', 'TON', 'DOT', 'LTC', 'TRX', 'HBAR', 'TAO', 'AAVE', 'UNI', 'NEAR', 'APT', 'ONDO', 'ENA', 'PEPE', 'ZEC', 'FET', 'HYPE', 'WLD', 'ARB', 'OP', 'FIL']);
// ---------- 24시간 막대(15분 단위, 위=호재 아래=악재) ----------
export function drawHist(cv, xs, { sel = null, h = 64 } = {}) {
  const dpr = Math.min(devicePixelRatio || 1, 2), w = cv.clientWidth; cv.width = w * dpr; cv.height = h * dpr; const g = cv.getContext('2d'); g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
  const now = Date.now() / 1000, B = 96, bu = new Array(B).fill(0), bd = new Array(B).fill(0), bn = new Array(B).fill(0);
  xs.forEach((x) => { const k = Math.floor((x.t - (now - 86400)) / 900); if (k < 0 || k >= B) return; if (x.v === '호재') bu[k]++; else if (x.v === '악재') bd[k]++; else bn[k]++; });
  const mx = Math.max(3, ...bu.map((u, i) => Math.max(u + bn[i] / 2, bd[i] + bn[i] / 2))), bw = w / B, mid = h / 2;
  for (let i = 0; i < B; i++) { const x = i * bw + 0.5, ww = Math.max(1, bw - 1.2), hu = (bu[i] + bn[i] / 2) / mx * (mid - 3), hd = (bd[i] + bn[i] / 2) / mx * (mid - 3), dim = sel != null && Math.floor(i / 4) !== sel ? 0.28 : 1;
    g.globalAlpha = dim; g.fillStyle = '#12b07c'; g.fillRect(x, mid - hu, ww, hu); g.fillStyle = '#e5533f'; g.fillRect(x, mid + 1, ww, hd); }
  g.globalAlpha = 1; g.fillStyle = tone(.15); g.fillRect(0, mid, w, 1);
  return { B, bw };
}

// ---------- 소식 이후 가격 변화(바이낸스 1분 봉) ----------
const pxCache = new Map();
async function since(sym, t) {
  const key = sym + t; if (pxCache.has(key)) return pxCache.get(key);
  const p = fetch(`https://data-api.binance.vision/api/v3/klines?symbol=${sym}USDT&interval=1m&startTime=${(t - 60) * 1000}&limit=${sinceLimit(t - 60)}`).then((r) => r.ok ? r.json() : null).then((k) => (k && k.length ? k.map((x) => [x[0] / 1000, +x[4]]) : null)).catch(() => null);
  pxCache.set(key, p); return p;
}
const PRICED = new Set(['BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'DOGE', 'ADA', 'LINK', 'AVAX', 'SUI', 'TON', 'DOT', 'LTC', 'TRX', 'HBAR', 'TAO', 'AAVE', 'UNI', 'NEAR', 'APT', 'ONDO', 'ENA', 'PEPE', 'ZEC', 'FET', 'HYPE', 'WLD', 'ARB', 'OP', 'FIL']);

// ---------- 관련 기사(사이트 기사 목록에서 같은 코인·비슷한 제목, ±12시간) ----------
const bg = (s) => { s = (s || '').replace(/[^가-힣a-z0-9]/gi, '').toLowerCase(); const o = new Set(); for (let i = 0; i < s.length - 1; i++) o.add(s.slice(i, i + 2)); return o; };
function related(it) {
  const a = bg(it.ko); return store.feed.map((f) => { const b = bg(f.title); let j = 0; b.forEach((x) => { if (a.has(x)) j++; }); const sim = j / Math.max(1, Math.min(a.size, b.size));
    const coin = (f.assets || []).some((c) => (it.coins || []).includes(c)); return { f, s: sim + (coin ? 0.15 : 0) }; })
    .filter((x) => Math.abs(x.f.t0 - it.t) < 43200 && x.s >= 0.32).sort((p, q) => q.s - p.s).slice(0, 3).map((x) => x.f);
}

// ---------- 상세 ----------
export function detailHTML(it) {
  const rel = related(it), src = it.link ? (() => { try { return new URL(it.link).hostname.replace(/^www\./, ''); } catch (e) { return ''; } })() : '';
  return `<p class="meta">${pill(it.v)} ${bars(it)} <span>${kindName(it.kind)}</span><span>·</span><span class="mono">${hm(it.t)}</span><span>${ago(it.t)}</span><span>·</span><span>${outlets(it)}</span></p>
    <h2>${esc(line(it))}</h2>${altLine(it) ? `<p class="alt">${esc(altLine(it))}</p>` : ''}
    <div class="tags">${chips(it, 4)}${it.mw ? `<span class="chip th">${T('Market-wide', '시장 전체')}</span>` : ''}</div>
    <div class="mystars" data-sid="${it.id}"></div><div class="thlink" data-sid="${it.id}"></div>
    <h4>${T('Price since this story', '이 소식 이후 가격')}</h4><div class="rx" id="rx"><p class="empty" style="padding:10px 0">${T('Loading…', '불러오는 중…')}</p></div>
    ${rel.length ? `<h4>${T('Related articles', '관련 기사')}</h4><div class="rel">${rel.map((f) => `<a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.title)}<small>${esc(L() ? f.src : f.se || f.src)} · ${hm(f.t0)}</small></a>`).join('')}</div>` : ''}
    ${src ? `<a class="src" href="${esc(it.link)}" target="_blank" rel="noopener">${T('Original link', '원문 링크')} · ${esc(src)} ↗</a>` : ''}
    <p class="fn">${T('Verdict and strength are AI judgments, not investment advice. Price change shows what happened after the story, not that the story caused it.', '판정과 세기는 AI 판단이며 투자 조언이 아니에요. 가격 변화는 소식 이후 실제 움직임이고, 그 소식 때문이라는 뜻은 아니에요.')}</p>`;
}
export async function fillRx(it, root) {
  const box = root.querySelector('#rx'); if (!box) return;
  let syms = (it.coins || []).filter((c) => PRICED.has(c)).slice(0, 2); if (!syms.length) syms = ['BTC'];
  const res = await Promise.all(syms.map((s) => since(s, it.t)));
  const html = syms.map((s, i) => { const k = res[i]; if (!k || k.length < 3) return ''; const ch = (k[k.length - 1][1] / k[0][1] - 1) * 100, mins = Math.round((k[k.length - 1][0] - k[0][0]) / 60);
    return `<div class="rxc"><p class="h"><b>${s}</b><span class="v ${ch >= 0 ? 'up' : 'down'}">${DFD.pct(ch)}</span></p><canvas data-i="${i}"></canvas>
      <p class="n">${T(`${mins >= 60 ? Math.floor(mins / 60) + 'h ' : ''}${mins % 60}m since the story${(it.coins || []).includes(s) ? '' : ' · market reference'}`, `소식 이후 ${mins >= 60 ? Math.floor(mins / 60) + '시간 ' : ''}${mins % 60}분${(it.coins || []).includes(s) ? '' : ' · 시장 기준(BTC)'}`)}</p></div>`; }).join('');
  box.innerHTML = html || `<p class="empty" style="padding:10px 0">${T('No price data for this story.', '이 소식의 가격 자료가 없어요.')}</p>`;
  box.querySelectorAll('canvas').forEach((cv) => { const d = document.createElement('div'); d.className = 'lwc'; cv.replaceWith(d); const k = res[+cv.dataset.i]; lwChart(d, k.map((x) => [x[0], x[1]]), it.t, { height: 120 }); });
}
// 시트(모바일·작은 화면) 열기
export function openSheet(it) {
  track('open');
  const sh = document.getElementById('sheet'), det = document.getElementById('det'); det.innerHTML = detailHTML(it); sh.classList.add('on'); sh.setAttribute('aria-hidden', 'false'); fillRx(it, det);
  sh.querySelectorAll('[data-close]').forEach((b) => (b.onclick = () => { sh.classList.remove('on'); sh.setAttribute('aria-hidden', 'true'); }));
}
if (typeof document !== 'undefined') addEventListener('keydown', (e) => { if (e.key === 'Escape') { const sh = document.getElementById('sheet'); if (sh) { sh.classList.remove('on'); sh.setAttribute('aria-hidden', 'true'); } } });

// ---------- 필터 막대 ----------
export function segHTML(cur, xs) {
  return THEMES.map((t) => { const n = t.k === 'all' ? xs.length : xs.filter((x) => x.th.includes(t.k)).length; return `<button type="button" data-th="${t.k}" aria-pressed="${t.k === cur}">${t[L() ? 'ko' : 'en']}<span class="c">${n}</span></button>`; }).join('');
}


// ---------- 소식 이후 가격(목록용, 코인마다 5분 봉 한 번만 받아 쓴다) ----------
const k5 = new Map(); let k5at = 0;
export async function loadK5(syms) {
  const now = Date.now(); if (now - k5at > 60000) { k5.clear(); k5at = now; }
  await Promise.all([...new Set(syms)].filter((s) => PRICED_ALL.has(s) && !k5.has(s)).map((s) => { const p = fetch(`https://data-api.binance.vision/api/v3/klines?symbol=${s}USDT&interval=5m&limit=300`).then((r) => r.ok ? r.json() : null).then((k) => (k ? k.map((x) => [x[0] / 1000, +x[1], +x[4]]) : null)).catch(() => null); k5.set(s, p); return p; }));
}
export const PRICED_ALL = new Set(['BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'DOGE', 'ADA', 'LINK', 'AVAX', 'SUI', 'TON', 'DOT', 'LTC', 'TRX', 'HBAR', 'TAO', 'AAVE', 'UNI', 'NEAR', 'APT', 'ONDO', 'ENA', 'PEPE', 'ZEC', 'FET', 'HYPE', 'WLD', 'ARB', 'OP', 'FIL']);
export async function sinceChange(sym, t) {
  const k = await k5.get(sym); if (!k || !k.length || t < k[0][0]) return null;
  let i = k.findIndex((c) => c[0] > t) - 1; if (i < 0) i = k.length - 1; const p0 = k[Math.max(0, i)][1], p1 = k[k.length - 1][2]; return (p1 / p0 - 1) * 100;
}
// 목록에 '소식 이후' 칩을 채운다: [data-px="SYM|t"]
export async function fillPx(root) {
  const els = [...root.querySelectorAll('[data-px]')]; if (!els.length) return; await loadK5(els.map((e) => e.dataset.px.split('|')[0]));
  for (const e of els) { const [s, t] = e.dataset.px.split('|'), c = await sinceChange(s, +t); if (c == null) { e.remove(); continue; }
    e.className = 'pxc ' + (c >= 0 ? 'up' : 'down'); e.innerHTML = `${s} <b>${DFD.pct(c)}</b>`; e.title = T(`${s} since this story`, `이 소식 이후 ${s}`); }
}
export const pxChip = (it) => { const s = (it.coins || []).find((c) => PRICED_ALL.has(c)); return s ? `<span class="pxc" data-px="${s}|${it.t}">${s}</span>` : ''; };
// 새 소식은 바로 끼워 넣지 않고 'N개 새 소식' 버튼으로 알린다(읽던 곳이 밀리지 않게). 맨 위에 있으면 바로 반영.
export function newGate(btn, rerender) {
  let shown = new Set(store.items.map((x) => x.id)), ready = false;
  const check = () => { if (!ready) { shown = new Set(store.items.map((x) => x.id)); ready = store.items.length > 0; return true; }
    const fresh = store.items.filter((x) => !shown.has(x.id)); if (!fresh.length) return false;   // 바뀐 게 없으면 다시 그리지 않는다(차트·스크롤 유지)
    if (scrollY < 120) { fresh.forEach((x) => shown.add(x.id)); return true; }
    btn.textContent = T(`${fresh.length} new ${fresh.length > 1 ? 'stories' : 'story'} ↑`, `새 소식 ${fresh.length}개 ↑`); btn.classList.add('on'); return false; };
  btn.addEventListener('click', () => { store.items.forEach((x) => shown.add(x.id)); btn.classList.remove('on'); scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); rerender(true); });
  return { check, visible: (it) => shown.has(it.id) || !ready };
}

// ---------- 차트 십자선: PC는 포인터를 올리면, 휴대폰은 누르고 옆으로 끌면 그 시각·가격·소식 대비 변화가 뜬다 ----------
// m = { pts:[[t,v]], X(t), Y(v), tStory, base, dec } — 그래프를 다 그린 뒤 부른다
const fmtT = (t) => { const d = new Date(t * 1000), today = new Date().toDateString() === d.toDateString(), lc = DFI.lang() === 'ko' ? 'ko-KR' : 'en-GB';
  return new Intl.DateTimeFormat(lc, today ? { hour: '2-digit', minute: '2-digit' } : { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(d); };
export function crosshair(cv, m) {
  const g = cv.getContext('2d'), snap = g.getImageData(0, 0, cv.width, cv.height), dpr = cv.width / (cv.clientWidth || 1);
  const host = cv.parentElement; if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
  let tip = host.querySelector(':scope > .xtip'); if (!tip) { tip = document.createElement('div'); tip.className = 'xtip'; tip.setAttribute('aria-hidden', 'true'); host.appendChild(tip); }
  cv.style.touchAction = 'pan-y'; cv.style.cursor = 'crosshair';
  let hideT = 0, touchDrag = false;
  const clear = () => { g.putImageData(snap, 0, 0); tip.classList.remove('on'); };
  const show = (clientX) => {
    const rc = cv.getBoundingClientRect(), x = clientX - rc.left; if (x < 0 || x > rc.width) return clear();
    let best = 0, bd = 1e9; m.pts.forEach((p, i) => { const d = Math.abs(m.X(p[0]) - x); if (d < bd) { bd = d; best = i; } });
    const [t, v] = m.pts[best], px = m.X(t), py = m.Y(v);
    g.putImageData(snap, 0, 0); g.save(); g.scale(dpr, dpr);
    g.strokeStyle = tone(.45); g.lineWidth = 1; g.beginPath(); g.moveTo(px + .5, 0); g.lineTo(px + .5, rc.height); g.stroke();
    g.fillStyle = (dark() ? '#111b2b' : '#fff'); g.strokeStyle = ink(); g.lineWidth = 2; g.beginPath(); g.arc(px, py, 4, 0, 7); g.fill(); g.stroke(); g.restore();
    const after = t >= m.tStory, ch = (v / m.base - 1) * 100;
    tip.innerHTML = `<b class="mono">${fmtT(t)}</b><span class="mono">${v.toLocaleString('en-US', { maximumFractionDigits: m.dec ?? 2, minimumFractionDigits: m.dec ?? 2 })}</span>${after ? `<span class="mono ${ch >= 0 ? 'up' : 'down'}">${DFD.pct(ch)} ${T('vs story', '소식 대비')}</span>` : `<span class="b4">${T('before the story', '소식 전')}</span>`}`;
    tip.classList.add('on'); const tw = tip.offsetWidth, hostR = host.getBoundingClientRect(), left = rc.left - hostR.left + px;
    tip.style.transform = `translate(${Math.max(0, Math.min(hostR.width - tw, left - tw / 2))}px, ${rc.top - hostR.top - tip.offsetHeight - 6}px)`;
  };
  cv.addEventListener('pointermove', (e) => { if (e.pointerType === 'touch' && !touchDrag) return; clearTimeout(hideT); show(e.clientX); });
  cv.addEventListener('pointerdown', (e) => { if (e.pointerType !== 'touch') return; touchDrag = true; clearTimeout(hideT); show(e.clientX); });
  const end = (e) => { if (e.pointerType === 'touch') { touchDrag = false; hideT = setTimeout(clear, 1600); } else clear(); };
  cv.addEventListener('pointerleave', end); cv.addEventListener('pointerup', (e) => { if (e.pointerType === 'touch') end(e); }); cv.addEventListener('pointercancel', end);
  cv.addEventListener('click', (e) => { if (e.pointerType === 'touch' || matchMedia('(hover: none)').matches) { e.stopPropagation(); e.preventDefault(); } });   // 휴대폰에서 그래프를 눌렀을 땐 카드가 열리지 않게
}


// ---------- TradingView Lightweight Charts(오픈소스)로 '소식 전후' 차트 ----------
// 소식 전은 회색 선, 소식 후는 소식 시점 가격을 기준선으로 위는 초록·아래는 빨강. PC는 포인터, 휴대폰은 누르고 끌면 십자선과 시각·가격·소식 대비 변화.
// 화면에서 사라진 차트는 다음 차트를 만들 때 정리한다(크기 감시·그리기 루프가 쌓이지 않게)
const LIVE = [];
function sweep() { for (let i = LIVE.length - 1; i >= 0; i--) if (!LIVE[i].box.isConnected) { try { LIVE[i].chart.remove(); } catch (e) {} LIVE.splice(i, 1); } }
const TZ = () => -new Date().getTimezoneOffset() * 60;   // 라이브러리는 UTC로 그리므로 현지 시각으로 옮겨 준다
export function lwChart(el, pts, tStory, options = {}) {
  if (!pts || pts.length < 2) return drawLW(el, pts, tStory, options);
  const seen = new Set(), data = pts.filter(p => p[1] != null && !seen.has(Math.floor(p[0])) && seen.add(Math.floor(p[0])));
  if (!data.length) return drawLW(el, null, tStory, options);
  const first = data.find(p => Math.floor(p[0]) >= tStory), last = data[data.length - 1];
  const result = {change: first ? (last[1] / first[1] - 1) * 100 : null, closed: pts[pts.length - 1][0] < Date.now() / 1000 - 1800};
  el.innerHTML = '<div class="lgd"></div><div class="lwbox"></div>';
  el.querySelector('.lwbox').style.height = (options.height || 200) + 'px';
  whenVisible(el, () => Object.assign(result, drawLW(el, pts, tStory, options)), () => drawLW(el, null, tStory, options));
  return result;
}
function drawLW(el, pts, tStory, { height = 200, dec = 2, mark = null, vsLabel = null, preLabel = null } = {}) {
  if (!window.LightweightCharts || !pts || pts.length < 2) { el.innerHTML = `<p class="mute">${T('No price data for this time.', '이 시간의 가격 자료가 없어요.')}</p>`; return null; }
  const LC = window.LightweightCharts, off = TZ(), lc = DFI.lang() === 'ko' ? 'ko-KR' : 'en-GB';
  el.innerHTML = '<div class="lgd"></div><div class="lwbox"></div>'; const box = el.querySelector('.lwbox'), lgd = el.querySelector('.lgd'); box.style.height = height + 'px';
  const chart = LC.createChart(box, { autoSize: true, layout: { background: { type: 'solid', color: 'transparent' }, textColor: (dark() ? '#8d9bb2' : '#5f6c83'), fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 11, attributionLogo: false },
    grid: { vertLines: { visible: false }, horzLines: { color: tone(.06) } }, rightPriceScale: { borderVisible: false, scaleMargins: { top: Math.max(0.12, 20 / (height - 28)), bottom: Math.max(0.08, 13 / (height - 28)) } },   // 가격표(높이 약 19px)가 위 · 아래 끝에서 잘리지 않게 픽셀로 여백
    timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true, lockVisibleTimeRangeOnResize: true },
    crosshair: { mode: LC.CrosshairMode.Magnet, vertLine: { color: tone(.45), width: 1, style: 0, labelBackgroundColor: ink() }, horzLine: { color: tone(.25), width: 1, style: 2, labelBackgroundColor: ink() } },
    handleScroll: { mouseWheel: false, pressedMouseMove: false, horzTouchDrag: false, vertTouchDrag: true }, handleScale: false,
    localization: { locale: lc, timeFormatter: (t) => new Intl.DateTimeFormat(lc, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }).format(new Date(t * 1000)), priceFormatter: (v) => v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) } });
  sweep(); LIVE.push({ chart, box });
  const seen = new Set(), data = pts.filter((p) => p[1] != null && !seen.has(Math.floor(p[0])) && seen.add(Math.floor(p[0]))).map((p) => ({ time: Math.floor(p[0]) + off, value: p[1] }));
  let i0 = data.findIndex((d) => d.time >= tStory + off); const hasAfter = i0 >= 0; if (!hasAfter) i0 = data.length - 1;
  const base = data[i0].value;
  const pre = chart.addLineSeries({ color: (dark() ? '#4a5870' : '#b8c1ce'), lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: true });
  // '소식' 표시가 그래프 왼쪽 · 오른쪽 끝에 붙으면 글자가 잘린다 → 그쪽에 빈 칸(값 없는 시각)을 조금 둔다
  const step = data.length > 1 ? Math.max(1, data[1].time - data[0].time) : 60, padN = Math.ceil(data.length * 0.07) + 2;
  const padL = i0 < padN ? Array.from({ length: padN - i0 }, (_, k) => ({ time: data[0].time - (padN - i0 - k) * step })) : [];
  const padR = hasAfter && data.length - 1 - i0 < padN ? Array.from({ length: padN - (data.length - 1 - i0) }, (_, k) => ({ time: data[data.length - 1].time + (k + 1) * step })) : [];
  pre.setData([...padL, ...data.slice(0, i0 + 1)]);
  const post = chart.addBaselineSeries({ baseValue: { type: 'price', price: base }, topLineColor: '#12b07c', topFillColor1: 'rgba(18,176,124,.22)', topFillColor2: 'rgba(18,176,124,.02)',
    bottomLineColor: '#e5533f', bottomFillColor1: 'rgba(229,83,63,.02)', bottomFillColor2: 'rgba(229,83,63,.22)', lineWidth: 2, priceLineVisible: false });
  if (hasAfter) { post.setData([...data.slice(i0), ...padR]); post.setMarkers([{ time: data[i0].time, position: 'aboveBar', color: ink(), shape: 'arrowDown', text: mark || T('story', '소식') }]);
    post.createPriceLine({ price: base, color: tone(.35), lineWidth: 1, lineStyle: 2, axisLabelVisible: false }); }
  chart.timeScale().fitContent();
  // 범례 시각: 오늘이면 시:분만(좁은 화면에서 '소식 대비'가 잘리지 않게)
  const today = new Date(Date.now() + off * 1000).toISOString().slice(0, 10);
  const fmt = (t) => new Intl.DateTimeFormat(lc, new Date(t * 1000).toISOString().slice(0, 10) === today ? { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' } : { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }).format(new Date(t * 1000));
  // 범례는 항상 한 줄(시각 · 가격 · 소식 대비)로 같은 모양을 유지한다. 포인터가 없으면 최신 값.
  let shownT = null;
  const legend = (d) => { if (d.time === shownT) return; shownT = d.time; const after = hasAfter && d.time >= data[i0].time, ch = (d.value / base - 1) * 100;
    lgd.innerHTML = `<span class="mono">${fmt(d.time)}</span><b class="mono">${d.value.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec })}</b>${after ? `<span class="mono ${ch >= 0 ? 'up' : 'down'}">${DFD.pct(ch)} ${vsLabel || T('vs story', '소식 대비')}</span>` : `<span class="b4">${preLabel || T('before the story', '소식 전')}</span>`}`; };
  const last = data[data.length - 1]; legend(last);
  chart.subscribeCrosshairMove((p) => { if (!charted && p && p.time) { charted = true; track('chart'); } const v = p && p.time && p.seriesData ? p.seriesData.get(post) || p.seriesData.get(pre) : null; legend(v && v.value != null ? { time: p.time, value: v.value } : last); });
  return { chart, change: hasAfter ? (last.value / base - 1) * 100 : null, closed: pts[pts.length - 1][0] < Date.now() / 1000 - 1800 };
}
// 이어지는 이야기 표시(소식 카드 · 상세 창)
if (typeof document !== 'undefined') watchThreads();
// 접기 · 더 보기(D6), 가로 넘김 표시(D3 — 넘치는 줄이 있을 때만 sh.js)
export const FOLD = new Set();   // 펼친 것(테마 키 · 'lanes') — 언어 · 테마 전환으로 다시 그려도 유지
if (typeof document !== 'undefined') {
  addEventListener('click', (e) => { const f = e.target.closest('[data-fold]'); if (f) { const o = f.parentElement.classList.toggle('open'); FOLD[o ? 'add' : 'delete'](f.dataset.k); f.setAttribute('aria-expanded', o); f.textContent = o ? f.dataset.o : f.dataset.c; return; }
    const m = e.target.closest('[data-more]'); if (m) { FOLD.add('lanes'); m.previousElementSibling.classList.add('all'); m.remove(); } });
  const HS = '#cards,.box.wl ul,.pstrip .wrap.pin,#tt,.filt,nav.ttabs'; let hsT = 0, hsL = 0;
  const hs = () => { clearTimeout(hsT); hsT = setTimeout(() => { if (hsL || ![...document.querySelectorAll(HS)].some((e) => e.scrollWidth > e.clientWidth + 4)) return; hsL = 1; import('./sh.js' + new URL(import.meta.url).search).then((m) => m.init(HS)); }, 300); };
  addEventListener('load', hs); addEventListener('resize', hs); new MutationObserver(hs).observe(document.documentElement, { childList: true, subtree: true });
}
