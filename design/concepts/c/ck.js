// 일정(경제지표) 화면 공통: 다가오는 발표, 지금 경제 한눈에(AI), 지표 카드, 지표 상세(긴 그래프 · 지난 발표 표 · 과거에 비슷했을 때).
// 자료: econ.json(Mac 에서 1시간마다 — ALFRED 발표 당일 값, 야후 일봉, Forex Factory 예상치, FRED·연준 일정). 숫자는 모두 프로그램, 문장만 AI.
import { T, L, esc } from '../l/lk.js?v=1017185452';

export const ECON_URL = 'https://raw.githubusercontent.com/mash1384/signal-desk/flash/daily/econ.json';
let DOC = null;
export async function loadEcon() {
  if (DOC) return DOC;
  const r = await fetch((window.DF_ECON || ECON_URL) + '?t=' + Math.floor(Date.now() / 300000));
  if (!r.ok) throw new Error('econ ' + r.status);
  DOC = await r.json();
  DOC.by = Object.fromEntries(DOC.indicators.map((x) => [x.k, x]));
  return DOC;
}
export const nm = (x) => (L() ? x.ko : x.en);
const lc = () => (L() ? 'ko-KR' : 'en-GB');

// ---------- 숫자 ----------
export function fv(x, v, { signed = false } = {}) {
  if (v == null) return '–';
  const sg = signed && v > 0 ? '+' : '';
  if (x.k === 'nfp' || x.k === 'claims') { const n = Math.round(v * 1000); return sg + (L() ? n.toLocaleString('en-US') + (x.k === 'nfp' ? '명' : '건') : n.toLocaleString('en-US')); }
  if (x.k === 'jolts') return sg + (L() ? Math.round(v * 100).toLocaleString('en-US') + '만 건' : v.toFixed(2) + 'M');
  return sg + v.toFixed(x.dec) + '%';
}
export function fchg(x, v) {
  if (v == null) return '–';
  if (x.unit === '%') return (v > 0 ? '+' : v < 0 ? '−' : '±') + Math.abs(v).toFixed(x.dec) + (L() ? '%p' : ' pt');
  return fv(x, v, { signed: true }).replace('-', '−');
}
export const fpx = (v, kind) => (v == null ? '–' : kind === 'bp' ? (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(0) + 'bp' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(1) + '%');
// 기간(관측월) → '2026년 9월' · 'Sep 2026', 주간은 '10월 10일 주'
export function period(x, p) {
  const d = new Date(p + 'T00:00:00Z');
  if (x.k === 'claims') return new Intl.DateTimeFormat(lc(), { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(d) + (L() ? ' 주' : ' wk');
  if (x.k === 'gdp') return L() ? `${d.getUTCFullYear()}년 ${Math.floor(d.getUTCMonth() / 3) + 1}분기` : `Q${Math.floor(d.getUTCMonth() / 3) + 1} ${d.getUTCFullYear()}`;
  return new Intl.DateTimeFormat(lc(), { year: 'numeric', month: 'short', timeZone: 'UTC' }).format(d);
}
export const day = (ts, o = {}) => new Intl.DateTimeFormat(lc(), { month: 'short', day: 'numeric', weekday: 'short', ...o }).format(new Date(ts * 1000));
export const hm = (ts) => new Intl.DateTimeFormat(lc(), { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(ts * 1000));
export const ymd = (s) => new Intl.DateTimeFormat(lc(), { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }).format(new Date(s + 'T00:00:00Z'));
export function until(ts) {
  const s = ts - Date.now() / 1000, d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (s <= 0) return T('released', '발표됨');
  if (d >= 1) return T(`in ${d}d ${h}h`, `${d}일 ${h}시간 뒤`);
  if (h >= 1) return T(`in ${h}h ${m}m`, `${h}시간 ${m}분 뒤`);
  return T(`in ${m}m`, `${m}분 뒤`);
}
// 방향을 말로(색만으로 뜻을 전하지 않게): 물가는 '더 뜨거움/식음', 고용은 '강해짐/약해짐'
export function dirWord(x, dir) {
  if (dir === 'flat' || !dir) return T('about the same', '거의 같음');
  const hot = (dir === 'up') === (x.hot > 0);
  if (x.grp === 'prices') return hot ? T('hotter', '더 뜨거워짐') : T('cooler', '식음');
  if (x.grp === 'jobs') return hot ? T('stronger', '강해짐') : T('weaker', '약해짐');
  return hot ? T('faster', '빨라짐') : T('slower', '느려짐');
}
export const arrow = (dir) => (dir === 'up' ? '▲' : dir === 'down' ? '▼' : '■');
const RANK = (r) => (r == null ? '' : r >= 0.8 ? T('high for the past 10 years', '10년 중 높은 편') : r <= 0.2 ? T('low for the past 10 years', '10년 중 낮은 편') : T('middle of the past 10 years', '10년 중 중간'));

// ---------- 조각: 지금 경제 한눈에(AI) ----------
export function overviewHTML(doc) {
  const o = doc.overview && doc.overview[L() ? 'ko' : 'en'];
  const at = new Intl.DateTimeFormat(lc(), { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(doc.made * 1000));
  if (!o) return `<p class="mute">${T('The AI summary appears after the next update.', 'AI 요약은 다음 갱신 때 나와요.')}</p>`;
  const g = doc.groups;
  return `<p class="ovk">${T('The US economy now', '지금 미국 경제')} <span>· ${T('AI summary', 'AI 요약')} · ${at}</span></p>
    <h2 class="ovh">${esc(o.head)}</h2>
    <ul class="ovl">${o.s.map((s, i) => `<li><span class="g">${esc(g[i] ? (L() ? g[i].ko : g[i].en) : '')}</span><span>${esc(s)}</span></li>`).join('')}</ul>
    <p class="fn">${T('Written by AI from the numbers below only. Not investment advice.', 'AI가 아래 숫자만 보고 쓴 요약이에요. 투자 조언이 아니에요.')}</p>`;
}

// ---------- 조각: 일정 ----------
const IMP = (i) => `<span class="imp ${i}" aria-label="${i === 'high' ? T('High impact', '중요도 높음') : T('Medium impact', '중요도 중간')}">${i === 'high' ? T('High', '중요') : T('Med', '보통')}</span>`;
// 발표된 일정이면 우리 지표의 실제 값(그날 발표분)
function actualOf(doc, ev) {
  const out = [];
  for (const k of ev.keys || []) { const x = doc.by[k]; if (x && Math.abs(x.latest.ts - ev.ts) < 3 * 3600) out.push(x); }
  return out;
}
export function nextEvent(doc) { const now = Date.now() / 1000; return doc.upcoming.find((e) => e.ts > now && e.impact === 'high' && (e.keys || []).length) || doc.upcoming.find((e) => e.ts > now); }
export function nextHTML(doc) {
  const e = nextEvent(doc); if (!e) return '';
  const fc = (e.items || []).filter((i) => i.fc);
  return `<div class="nx"><p class="k">${T('Next big release', '다음 큰 발표')}</p><p class="t">${esc(L() ? e.ko || e.en : e.en)}</p>
    <p class="w"><span class="mono">${day(e.ts)} ${hm(e.ts)}</span> · <b data-until="${e.ts}">${until(e.ts)}</b></p>
    ${fc.length ? `<p class="f">${fc.map((i) => `${esc(i.title)} ${T('forecast', '예상')} <b class="mono">${esc(i.fc)}</b>`).join(' · ')}</p>` : ''}</div>`;
}
export function scheduleHTML(doc, { from = -7, to = 21, sel = null } = {}) {
  const now = Date.now() / 1000, xs = doc.upcoming.filter((e) => e.ts >= now + from * 86400 && e.ts <= now + to * 86400);
  const byDay = new Map();
  xs.forEach((e) => { const k = new Date(e.ts * 1000).toDateString(); if (!byDay.has(k)) byDay.set(k, []); byDay.get(k).push(e); });
  let html = '';
  for (const [, es] of byDay) {
    const past = es[0].ts < now - 3 * 3600;
    html += `<li class="dg${past ? ' past' : ''}"><p class="dh">${day(es[0].ts)}${new Date(es[0].ts * 1000).toDateString() === new Date().toDateString() ? ` <span class="today">${T('Today', '오늘')}</span>` : ''}</p><ul>`;
    for (const e of es) {
      const act = actualOf(doc, e), k = (e.keys || [])[0], main = (e.items || []).filter((i) => !i.role || i.role === 'main');
      const fcs = main.map((i) => i.fc).filter(Boolean), prevs = main.map((i) => i.prev).filter(Boolean);
      const val = act.length ? act.map((x) => `<b class="mono">${fv(x, x.latest.v)}</b>`).join(' · ') : '';
      html += `<li><button type="button" class="ev${k && doc.by[k] ? '' : ' nok'}${sel && k === sel ? ' on' : ''}" ${k && doc.by[k] ? `data-ind="${k}"` : 'disabled'} aria-pressed="${!!(sel && k === sel)}">
        <span class="tm mono">${hm(e.ts)}</span><span class="nm">${esc(L() ? e.ko || e.en : e.en)} ${IMP(e.impact)}</span>
        <span class="vals">${val ? `<span class="a">${T('Actual', '실제')} ${val}</span>` : ''}${fcs.length ? `<span>${T('Fcst', '예상')} <span class="mono">${esc(fcs[0])}</span></span>` : ''}${prevs.length && !val ? `<span>${T('Prev', '이전')} <span class="mono">${esc(prevs[0])}</span></span>` : ''}</span></button></li>`;
    }
    html += '</ul></li>';
  }
  return `<ol class="sch">${html || `<li class="mute">${T('No scheduled releases in this window.', '이 기간에 예정된 발표가 없어요.')}</li>`}</ol>
    <p class="fn">${T('Times in your time zone. Forecasts from Forex Factory for this week only.', '시각은 내 시간대 기준이에요. 예상치는 이번 주 것만 있어요(Forex Factory).')}</p>`;
}

// ---------- 조각: 방금 나온 지표(최근 4일) ----------
const VS = { above: ['▲', 'above forecast', '예상보다 높음'], below: ['▼', 'below forecast', '예상보다 낮음'], inline: ['■', 'in line', '예상과 같음'] };
export function justHTML(doc, sel) {
  const now = Date.now() / 1000, xs = doc.indicators.filter((x) => x.latest.ts <= now && now - x.latest.ts < 4 * 86400).slice(0, 5);
  if (!xs.length) return '';
  return `<section class="just" aria-label="${T('Just released', '방금 나온 지표')}"><p class="k">${T('Just released', '방금 나온 지표')}</p><div class="jl">${xs.map((x) => {
    const L0 = x.latest, v = VS[L0.vs], sv = VS[L0.vs_sub];
    const note = v ? `${v[0]} ${L() ? v[2] : v[1]} <span class="mono">${esc(L0.fc)}</span>` : sv ? `${T('m/m', '전월 대비')} <span class="mono">${L0.sub.toFixed(x.dec)}%</span> · ${sv[0]} ${L() ? sv[2] : sv[1]}` : `${arrow(x.sit.dir)} ${T('vs previous', '직전 대비')} <span class="mono">${fchg(x, x.sit.chg)}</span>`;
    return `<button type="button" class="jt${sel === x.k ? ' on' : ''}" data-ind="${x.k}" aria-pressed="${sel === x.k}"><span class="n">${esc(nm(x))}</span><b class="mono">${fv(x, L0.v)}</b><span class="w">${note}</span><span class="d">${day(L0.ts, { weekday: undefined })}</span></button>`; }).join('')}</div></section>`;
}

// ---------- 조각: 지표 카드 ----------
export function cardHTML(x, sel) {
  const s = x.sit, fc = x.latest.fc;
  return `<button type="button" class="ic${sel === x.k ? ' on' : ''}" data-ind="${x.k}" aria-pressed="${sel === x.k}">
    <span class="h"><span class="n">${esc(nm(x))}</span><span class="p">${period(x, x.latest.period)}</span></span>
    <span class="v mono">${fv(x, x.latest.v)}</span>
    <span class="c"><span class="mono">${arrow(s.dir)} ${fchg(x, s.chg)}</span> <span class="w">${dirWord(x, s.dir)}</span></span>
    ${fc ? `<span class="fc">${T('Forecast', '예상')} <span class="mono">${esc(fc)}</span></span>` : ''}
    <canvas class="sp" data-spark="${x.k}" aria-hidden="true"></canvas>
    <span class="rk" title="${RANK(s.rank10y)}"><i style="inset-inline-start:${Math.round((s.rank10y ?? 0.5) * 100)}%"></i></span><span class="rkl">${RANK(s.rank10y)}</span></button>`;
}
export function boardHTML(doc, sel) {
  return doc.groups.map((g) => `<section class="grp" aria-label="${esc(L() ? g.ko : g.en)}"><h3>${esc(L() ? g.ko : g.en)}</h3><div class="ics">${doc.indicators.filter((x) => x.grp === g.k).map((x) => cardHTML(x, sel)).join('')}</div></section>`).join('');
}
// 작은 그래프(지난 5년, 화면 폭이 바뀔 때만 다시 그림)
export function drawSparks(root, doc) {
  root.querySelectorAll('canvas[data-spark]').forEach((cv) => {
    const x = doc.by[cv.dataset.spark]; if (!x) return;
    const w = cv.clientWidth, h = cv.clientHeight; if (!w || !h || +cv.dataset.w === w) return; cv.dataset.w = w;
    const dpr = Math.min(devicePixelRatio || 1, 2); cv.width = w * dpr; cv.height = h * dpr; const g = cv.getContext('2d'); g.scale(dpr, dpr);
    const t0 = Date.now() - 5 * 365 * 864e5, pts = x.long.filter((p) => Date.parse(p[0]) >= t0 && p[1] != null), v = pts.map((p) => p[1]);
    if (v.length < 2) return;
    const lo = Math.min(...v), hi = Math.max(...v), Y = (y) => h - 3 - ((y - lo) / (hi - lo || 1)) * (h - 6);
    g.beginPath(); v.forEach((y, i) => { const X = (i / (v.length - 1)) * w; i ? g.lineTo(X, Y(y)) : g.moveTo(X, Y(y)); }); g.strokeStyle = '#0d253d'; g.lineWidth = 1.25; g.lineJoin = 'round'; g.stroke();
    g.fillStyle = '#533afd'; g.beginPath(); g.arc(w - 2, Y(v[v.length - 1]), 2.5, 0, 7); g.fill();
  });
}

// ---------- 지표 상세 ----------
export const RANGES = [['5y', 5, '5Y', '5년'], ['10y', 10, '10Y', '10년'], ['all', 99, 'All', '전체']];
export function detailHTML(doc, x, S) {
  const L0 = x.latest, ai = x.ai && x.ai[L() ? 'ko' : 'en'], fc = L0.fc, sub = L0.sub;
  const asset = doc.assets.find((a) => a.sym === S.asset) || doc.assets[0];
  return `<div class="dt" data-k="${x.k}">
    <header class="dth"><p class="k">${esc(nm(x))} · ${period(x, L0.period)}</p>
      <p class="big"><span class="mono">${fv(x, L0.v)}</span> <span class="c mono">${arrow(x.sit.dir)} ${fchg(x, x.sit.chg)}</span></p>
      <p class="meta">${T('Released', '발표')} ${ymd(L0.d)} · ${T('previous', '직전')} <span class="mono">${fv(x, L0.prev)}</span>${fc ? ` · ${T('forecast', '예상')} <span class="mono">${esc(fc)}</span>` : ''}${sub != null && x.sub ? ` · ${T('month on month', '전월 대비')} <span class="mono">${sub.toFixed(x.dec)}%</span>${L0.fc_sub ? ` (${T('fcst', '예상')} <span class="mono">${esc(L0.fc_sub)}</span>)` : ''}` : ''}</p></header>
    ${ai ? `<div class="ai"><p class="k">${T('What it means', '무슨 뜻인가')} <span>· AI</span></p>${ai.map((s) => `<p>${esc(s)}</p>`).join('')}</div>` : ''}
    <section class="hist"><div class="sh"><h3>${T('History', '지난 흐름')}</h3><span class="mseg" role="group" aria-label="${T('Range', '기간')}">${RANGES.map(([k, , en, ko]) => `<button type="button" data-range="${k}" aria-pressed="${S.range === k}">${L() ? ko : en}</button>`).join('')}</span></div>
      <div class="hc" id="hc"></div><p class="fn">${T(`${x.n} releases since ${ymd(x.since)} · value as first published each time`, `${ymd(x.since)}부터 발표 ${x.n}번 · 매번 처음 발표된 값`)}</p></section>
    <section class="sim"><div class="sh"><h3>${T('When it looked like this before', '과거에 비슷했을 때')}</h3></div>
      <p class="lead">${esc(x.past && x.past[L() ? 'ko' : 'en'] || '')}</p>
      <div class="assets" role="tablist" aria-label="${T('Asset', '자산')}">${doc.assets.map((a) => `<button type="button" role="tab" data-asset="${a.sym}" aria-selected="${a.sym === asset.sym}">${esc(L() ? a.ko : a.en)}</button>`).join('')}</div>
      <div class="fanw"><p class="fl" id="fl"></p><canvas class="fan" id="fan" aria-label="${T('Price paths after similar past releases', '비슷했던 과거 발표 뒤 가격 경로')}" role="img"></canvas>
        <p class="lgnd"><i class="s"></i>${T('each similar case', '비슷했던 회차 하나하나')} <i class="m"></i>${T('their median', '그 중앙값')} <i class="b"></i>${T('usual range, all releases', '평소 범위(모든 발표)')}</p></div>
      ${statsHTML(doc, x, asset)}
      <details class="cases"><summary>${T(`See the ${x.similar.length} similar releases`, `비슷했던 ${x.similar.length}번 보기`)}</summary><ul>${x.similar.map((c) => `<li><span class="mono">${ymd(c.d)}</span><span>${period(x, c.period)}</span><span class="mono">${fv(x, c.v)}</span><span class="mute2">${T('prev', '직전')} <span class="mono">${fv(x, c.prev)}</span></span><span class="mono r">${fpx(c.rx[asset.sym] && c.rx[asset.sym].w1, asset.kind)}</span></li>`).join('')}</ul>
        <p class="fn">${T('Last column: 1 week later.', '마지막 칸: 1주 뒤 변화.')}</p></details>
      <p class="fn">${esc(L() ? doc.note_ko : doc.note_en)} ${T('Similar = closest past releases by change from the previous print, level, gap to the 12-release average and 3-release trend.', '비슷함 = 직전 대비 변화 · 수준 · 최근 12번 평균과의 차이 · 최근 3번 흐름이 가까운 과거 발표.')}</p></section>
    <section class="tbl"><div class="sh"><h3>${T('Recent releases', '최근 발표')}</h3></div><div class="tw"><table><thead><tr><th scope="col">${T('Released', '발표일')}</th><th scope="col">${T('Period', '기간')}</th><th scope="col" class="r">${T('Actual', '실제')}</th><th scope="col" class="r">${T('Forecast', '예상')}</th><th scope="col" class="r">${T('Previous', '직전')}</th><th scope="col" class="r">${T('S&P 500 that day', 'S&P 500 당일')}</th><th scope="col" class="r">${T('Bitcoin that day', '비트코인 당일')}</th></tr></thead>
      <tbody>${x.rows.slice(0, 12).map((r) => `<tr><td class="mono">${ymd(r.d)}</td><td>${period(x, r.period)}</td><td class="r mono b">${fv(x, r.v)}</td><td class="r mono">${esc(r.fc || '–')}</td><td class="r mono">${fv(x, r.prev)}</td><td class="r mono">${pxCell(r.rx['^GSPC'], 'pct')}</td><td class="r mono">${pxCell(r.rx['BTC-USD'], 'pct')}</td></tr>`).join('')}</tbody></table></div></section>
  </div>`;
}
const pxCell = (r, kind) => { const v = r && r.d1; return v == null ? '–' : `<span class="${v > 0 ? 'up' : v < 0 ? 'down' : ''}">${fpx(v, kind)}</span>`; };
function statsHTML(doc, x, a) {
  const st = x.stats[a.sym] || {}, H = [['d1', '1 day', '1일'], ['w1', '1 week', '1주'], ['m1', '1 month', '1달']];
  const cell = (s) => (s ? `<b class="mono ${s.med > 0 ? 'up' : s.med < 0 ? 'down' : ''}">${fpx(s.med, a.kind)}</b><span class="mono">${T('up', '오름')} ${Math.round(s.up * s.n)}/${s.n}</span>` : '<span class="mute2">–</span>');
  return `<div class="tw"><table class="stt"><thead><tr><th scope="col">${T('After', '발표 뒤')}</th><th scope="col">${T('Similar cases · median', '비슷했던 회차 · 중앙값')}</th><th scope="col">${T('All releases · median', '모든 발표 · 중앙값')}</th></tr></thead>
    <tbody>${H.map(([h, en, ko]) => `<tr><th scope="row">${L() ? ko : en}</th><td>${cell(st[h] && st[h].sim)}</td><td>${cell(st[h] && st[h].all)}</td></tr>`).join('')}</tbody></table></div>`;
}

// 긴 그래프(Lightweight Charts, 상자 높이 고정)
let HC = null;
export function drawHistory(el, x, range) {
  if (HC) { try { HC.remove(); } catch (e) {} HC = null; }
  if (!el || !window.LightweightCharts) return;
  const yrs = RANGES.find((r) => r[0] === range)[1], t0 = Date.now() - yrs * 365.25 * 864e5;
  const data = x.long.filter((p) => p[1] != null && Date.parse(p[0]) >= t0).map((p) => ({ time: p[0], value: p[1] }));
  const seen = new Set(), dd = data.filter((d) => !seen.has(d.time) && seen.add(d.time));
  el.style.height = (innerWidth < 640 ? 200 : 240) + 'px';
  HC = LightweightCharts.createChart(el, { autoSize: true, layout: { background: { color: 'transparent' }, textColor: '#7b8799', fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 11, attributionLogo: false },
    grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(13,37,61,.06)' } }, rightPriceScale: { borderVisible: false }, timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
    crosshair: { mode: 1, vertLine: { color: 'rgba(13,37,61,.4)', labelBackgroundColor: '#0d253d' }, horzLine: { color: 'rgba(13,37,61,.2)', labelBackgroundColor: '#0d253d' } },
    handleScroll: { vertTouchDrag: true, mouseWheel: false, pressedMouseMove: false, horzTouchDrag: false }, handleScale: false,
    localization: { locale: lc(), priceFormatter: (v) => fv(x, v) } });
  const s = HC.addLineSeries({ color: '#0d253d', lineWidth: 2, priceLineVisible: false, crosshairMarkerRadius: 3 });
  s.setData(dd);
  if (x.k === 'nfp') s.applyOptions({ autoscaleInfoProvider: (o) => { const r = o(); if (!r) return r; const lo = Math.max(r.priceRange.minValue, -1500), hi = Math.min(r.priceRange.maxValue, 1500); return { priceRange: { minValue: lo, maxValue: hi } }; } });
  HC.timeScale().fitContent();
}

// 과거에 비슷했을 때: 발표 뒤 한 달 경로(캔버스, 높이 고정, 폭이 바뀔 때만 다시 그림)
export function drawFan(cv, lab, doc, x, sym) {
  const P = x.paths[sym], a = doc.assets.find((q) => q.sym === sym), bp = a.kind === 'bp';
  const w = cv.clientWidth, h = cv.clientHeight; if (!w || !h) return;
  const dpr = Math.min(devicePixelRatio || 1, 2); cv.width = w * dpr; cv.height = h * dpr; const g = cv.getContext('2d'); g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
  if (!P) { lab.textContent = T('Not enough history for this asset.', '이 자산은 기록이 부족해요.'); return; }
  const sims = P.sim.filter(Boolean), all = P.all_band, sb = P.sim_band;
  const vals = [...sims.flat(), ...all.lo, ...all.hi]; let lo = Math.min(0, ...vals), hi = Math.max(0, ...vals); const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
  const N = 21, L0 = 40, R = 8, top = 8, bot = 22, X = (i) => L0 + (i / N) * (w - L0 - R), Y = (v) => top + (1 - (v - lo) / (hi - lo || 1)) * (h - top - bot);
  g.font = '10.5px "JetBrains Mono", monospace'; g.fillStyle = '#8a96aa'; g.textBaseline = 'middle';
  const step = niceStep((hi - lo) / 4);
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) { g.strokeStyle = Math.abs(v) < step / 2 ? 'rgba(13,37,61,.28)' : 'rgba(13,37,61,.06)'; g.beginPath(); g.moveTo(L0, Y(v)); g.lineTo(w - R, Y(v)); g.stroke(); g.fillText(fpx(v, a.kind).replace('.0%', '%'), 2, Y(v)); }
  g.textBaseline = 'alphabetic'; [[0, T('release', '발표')], [5, T('1w', '1주')], [21, T('1m', '1달')]].forEach(([i, t]) => { g.fillText(t, Math.min(X(i), w - R - g.measureText(t).width), h - 6); });
  // 평소 범위(모든 발표 10~90%)
  if (all.lo.length > 1) { g.beginPath(); all.hi.forEach((v, i) => (i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)))); for (let i = all.lo.length - 1; i >= 0; i--) g.lineTo(X(i), Y(all.lo[i])); g.closePath(); g.fillStyle = 'rgba(138,150,170,.16)'; g.fill(); }
  // 비슷했던 회차 하나하나
  sims.forEach((p) => { g.beginPath(); p.forEach((v, i) => (i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)))); g.strokeStyle = 'rgba(83,58,253,.28)'; g.lineWidth = 1; g.stroke(); });
  // 중앙값
  if (sb.med.length > 1) { g.beginPath(); sb.med.forEach((v, i) => (i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)))); g.strokeStyle = '#533afd'; g.lineWidth = 2.5; g.lineJoin = 'round'; g.stroke(); }
  const m = sb.med[Math.min(sb.med.length - 1, 21)], am = all.med[Math.min(all.med.length - 1, 21)];
  lab.innerHTML = `${esc(L() ? a.ko : a.en)} · ${T('1 month later, median', '1달 뒤 중앙값')} <b class="mono">${fpx(m, a.kind)}</b> <span class="mute2">(${T('usual', '평소')} <span class="mono">${fpx(am, a.kind)}</span> · ${T('similar', '비슷한 회차')} ${sims.length}${T('', '번')})</span>`;
}
function niceStep(x) { const p = Math.pow(10, Math.floor(Math.log10(x || 1))), n = x / p; return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * p; }

// 남은 시간 표시는 1분마다 글자만 바꾼다(배치 그대로)
export function tickUntil(root) { setInterval(() => root.querySelectorAll('[data-until]').forEach((e) => { e.textContent = until(+e.dataset.until); }), 60000); }
