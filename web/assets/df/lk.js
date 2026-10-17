import { watchThreads } from './thr.js';
// 라이브 페이지 후보 공통: 실시간 속보 받기(30초마다), 테마 나누기, 카드·상세, 24시간 막대, 소식 이후 가격 변화
export const L = () => DFI.lang() === 'ko';
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
export const altLine = (it) => (L() ? it.en || '' : it.ko);
async function pull() {
  const d = await DFD.flash(); const seen = store.byId.size > 0;
  d.items.forEach((it) => { if (!store.byId.has(it.id)) { it.th = themesOf(it); store.byId.set(it.id, it); if (seen) store.fresh.add(it.id); } else Object.assign(store.byId.get(it.id), it, { th: themesOf(it) }); });
  store.items = [...store.byId.values()].sort((a, b) => b.t - a.t);
  store.subs.forEach((f) => f());
  setTimeout(() => store.fresh.clear(), 4000);
}
export function start(onData) { store.subs.push(onData); pull(); setInterval(pull, 30000); DFI.onLang(onData);
  fetch('https://mash1384.github.io/signal-desk/data/feed.json').then((r) => r.json()).then((d) => { store.feed = d.items || []; }).catch(() => {}); }
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
  g.globalAlpha = 1; g.fillStyle = 'rgba(13,37,61,.15)'; g.fillRect(0, mid, w, 1);
  return { B, bw };
}

// ---------- 소식 이후 가격 변화(바이낸스 1분 봉) ----------
const pxCache = new Map();
async function since(sym, t) {
  const key = sym + t; if (pxCache.has(key)) return pxCache.get(key);
  const p = fetch(`https://data-api.binance.vision/api/v3/klines?symbol=${sym}USDT&interval=1m&startTime=${(t - 60) * 1000}&limit=1000`).then((r) => r.ok ? r.json() : null).then((k) => (k && k.length ? k.map((x) => [x[0] / 1000, +x[4]]) : null)).catch(() => null);
  pxCache.set(key, p); return p;
}
function spark(cv, pts) {
  const dpr = Math.min(devicePixelRatio || 1, 2), w = cv.clientWidth, h = 56; cv.width = w * dpr; cv.height = h * dpr; const g = cv.getContext('2d'); g.scale(dpr, dpr);
  const ys = pts.map((p) => p[1]), lo = Math.min(...ys), hi = Math.max(...ys), sp = hi - lo || 1, up = ys[ys.length - 1] >= ys[0];
  const X = (i) => i / (pts.length - 1) * (w - 2) + 1, Y = (y) => h - 4 - (y - lo) / sp * (h - 8);
  g.strokeStyle = 'rgba(13,37,61,.18)'; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(0, Y(ys[0])); g.lineTo(w, Y(ys[0])); g.stroke(); g.setLineDash([]);
  const grd = g.createLinearGradient(0, 0, 0, h); grd.addColorStop(0, up ? 'rgba(18,176,124,.22)' : 'rgba(229,83,63,.22)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(X(i), Y(p[1])) : g.moveTo(X(i), Y(p[1])))); g.lineTo(X(pts.length - 1), h); g.lineTo(X(0), h); g.closePath(); g.fillStyle = grd; g.fill();
  g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(X(i), Y(p[1])) : g.moveTo(X(i), Y(p[1])))); g.strokeStyle = up ? '#12b07c' : '#e5533f'; g.lineWidth = 1.6; g.stroke();
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
    ${rel.length ? `<h4>${T('Related articles', '관련 기사')}</h4><div class="rel">${rel.map((f) => `<a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.title)}<small>${esc(f.src)} · ${hm(f.t0)}</small></a>`).join('')}</div>` : ''}
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
  const sh = document.getElementById('sheet'), det = document.getElementById('det'); det.innerHTML = detailHTML(it); sh.classList.add('on'); sh.setAttribute('aria-hidden', 'false'); fillRx(it, det);
  sh.querySelectorAll('[data-close]').forEach((b) => (b.onclick = () => { sh.classList.remove('on'); sh.setAttribute('aria-hidden', 'true'); }));
}
addEventListener('keydown', (e) => { if (e.key === 'Escape') { const sh = document.getElementById('sheet'); sh && sh.classList.remove('on'); } });

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
    g.strokeStyle = 'rgba(13,37,61,.45)'; g.lineWidth = 1; g.beginPath(); g.moveTo(px + .5, 0); g.lineTo(px + .5, rc.height); g.stroke();
    g.fillStyle = '#fff'; g.strokeStyle = '#0d253d'; g.lineWidth = 2; g.beginPath(); g.arc(px, py, 4, 0, 7); g.fill(); g.stroke(); g.restore();
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
export function lwChart(el, pts, tStory, { height = 200, dec = 2 } = {}) {
  if (!window.LightweightCharts || !pts || pts.length < 2) { el.innerHTML = `<p class="mute">${T('No price data for this time.', '이 시간의 가격 자료가 없어요.')}</p>`; return null; }
  const LC = window.LightweightCharts, off = TZ(), lc = DFI.lang() === 'ko' ? 'ko-KR' : 'en-GB';
  el.innerHTML = '<div class="lgd"></div><div class="lwbox"></div>'; const box = el.querySelector('.lwbox'), lgd = el.querySelector('.lgd'); box.style.height = height + 'px';
  const chart = LC.createChart(box, { autoSize: true, layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#8a96aa', fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 11, attributionLogo: false },
    grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(13,37,61,.06)' } }, rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } },
    timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true, lockVisibleTimeRangeOnResize: true },
    crosshair: { mode: LC.CrosshairMode.Magnet, vertLine: { color: 'rgba(13,37,61,.45)', width: 1, style: 0, labelBackgroundColor: '#0d253d' }, horzLine: { color: 'rgba(13,37,61,.25)', width: 1, style: 2, labelBackgroundColor: '#0d253d' } },
    handleScroll: { mouseWheel: false, pressedMouseMove: false, horzTouchDrag: false, vertTouchDrag: true }, handleScale: false,
    localization: { locale: lc, timeFormatter: (t) => new Intl.DateTimeFormat(lc, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }).format(new Date(t * 1000)), priceFormatter: (v) => v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) } });
  sweep(); LIVE.push({ chart, box });
  const seen = new Set(), data = pts.filter((p) => p[1] != null && !seen.has(Math.floor(p[0])) && seen.add(Math.floor(p[0]))).map((p) => ({ time: Math.floor(p[0]) + off, value: p[1] }));
  let i0 = data.findIndex((d) => d.time >= tStory + off); const hasAfter = i0 >= 0; if (!hasAfter) i0 = data.length - 1;
  const base = data[i0].value;
  const pre = chart.addLineSeries({ color: '#b8c1ce', lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: true });
  pre.setData(data.slice(0, i0 + 1));
  const post = chart.addBaselineSeries({ baseValue: { type: 'price', price: base }, topLineColor: '#12b07c', topFillColor1: 'rgba(18,176,124,.22)', topFillColor2: 'rgba(18,176,124,.02)',
    bottomLineColor: '#e5533f', bottomFillColor1: 'rgba(229,83,63,.02)', bottomFillColor2: 'rgba(229,83,63,.22)', lineWidth: 2, priceLineVisible: false });
  if (hasAfter) { post.setData(data.slice(i0)); post.setMarkers([{ time: data[i0].time, position: 'aboveBar', color: '#0d253d', shape: 'arrowDown', text: T('story', '소식') }]);
    post.createPriceLine({ price: base, color: 'rgba(13,37,61,.35)', lineWidth: 1, lineStyle: 2, axisLabelVisible: false }); }
  chart.timeScale().fitContent();
  // 범례 시각: 오늘이면 시:분만(좁은 화면에서 '소식 대비'가 잘리지 않게)
  const today = new Date(Date.now() + off * 1000).toISOString().slice(0, 10);
  const fmt = (t) => new Intl.DateTimeFormat(lc, new Date(t * 1000).toISOString().slice(0, 10) === today ? { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' } : { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }).format(new Date(t * 1000));
  // 범례는 항상 한 줄(시각 · 가격 · 소식 대비)로 같은 모양을 유지한다. 포인터가 없으면 최신 값.
  let shownT = null;
  const legend = (d) => { if (d.time === shownT) return; shownT = d.time; const after = hasAfter && d.time >= data[i0].time, ch = (d.value / base - 1) * 100;
    lgd.innerHTML = `<span class="mono">${fmt(d.time)}</span><b class="mono">${d.value.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec })}</b>${after ? `<span class="mono ${ch >= 0 ? 'up' : 'down'}">${DFD.pct(ch)} ${T('vs story', '소식 대비')}</span>` : `<span class="b4">${T('before the story', '소식 전')}</span>`}`; };
  const last = data[data.length - 1]; legend(last);
  chart.subscribeCrosshairMove((p) => { const v = p && p.time && p.seriesData ? p.seriesData.get(post) || p.seriesData.get(pre) : null; legend(v && v.value != null ? { time: p.time, value: v.value } : last); });
  return { chart, change: hasAfter ? (last.value / base - 1) * 100 : null, closed: pts[pts.length - 1][0] < Date.now() / 1000 - 1800 };
}
// 이어지는 이야기 표시(소식 카드 · 상세 창)
watchThreads();
