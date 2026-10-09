// 상장 레이더: 업비트 원화 상장의 과거 가격 곡선을 겹쳐 그린 '상장 해부도'와 거래 공지 목록.
// data/listings.json(15분마다 갱신)을 읽고, 진행 중인 상장은 스케줄러를 거쳐 업비트 1분봉을 30초마다 받아 실시간 곡선을 그린다.
// 새 공지는 페이지를 열어 둔 동안 1분마다 확인해 목록 맨 위에 띄운다(알림은 보내지 않는다).
const S = window.SIGNAL || {};
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (v, d = 1) => (v == null || !isFinite(v) ? '–' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d) + '%');
const two = (n) => (n < 10 ? '0' : '') + n;
const kst = (ts) => new Date((ts + 9 * 3600) * 1000);
const day = (ts) => { const d = kst(ts); return `${d.getUTCFullYear()}.${two(d.getUTCMonth() + 1)}.${two(d.getUTCDate())}`; };
const hm = (ts) => { const d = kst(ts); return `${two(d.getUTCMonth() + 1)}.${two(d.getUTCDate())} ${two(d.getUTCHours())}:${two(d.getUTCMinutes())}`; };
const dur = (min) => (min == null ? '–' : min < 60 ? `${Math.round(min)}분` : `${(min / 60).toFixed(min < 600 ? 1 : 0)}시간`);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const nowSec = () => Date.now() / 1000;
const KIND = { listing: '신규 상장', caution: '유의 종목', delisting: '거래지원 종료' };
const q = (arr, p) => { if (!arr.length) return null; const v = [...arr].sort((a, b) => a - b), i = (v.length - 1) * p, lo = Math.floor(i), hi = Math.min(lo + 1, v.length - 1); return v[lo] + (v[hi] - v[lo]) * (i - lo); };

function main() {
  const root = $('#lst');
  if (!root) return;
  const proxy = root.dataset.proxy || '';
  const canvas = $('#lstCanvas'), ctx = canvas.getContext('2d'), tip = $('#lstTip'), chartBox = $('#lstChart');
  const view = { tab: 'trade', period: '2', bn: 'all', mode: 'all', kind: 'all', sel: null, hover: null, shown: 50 };
  let data = null, W = 0, H = 0, dpr = 1, agg = null, curves = [], liveCurves = {};
  const newUids = new Set();
  let watch = [];
  try { watch = JSON.parse(localStorage.getItem('signal-watch')) || []; } catch (e) { watch = []; }
  const css = getComputedStyle(document.documentElement);
  const col = (n) => css.getPropertyValue(n).trim() || '#888';
  let C = {};
  const readColors = () => { C = { text: col('--text'), text2: col('--text-2'), text3: col('--text-3'), line: col('--line'), accent: col('--accent'), up: col('--up'), down: col('--down') }; };
  readColors();
  new MutationObserver(() => { readColors(); draw(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  const alpha = (c, a) => (c.startsWith('oklch(') ? (c.includes('/') ? c.replace(/\/\s*[\d.]+\s*\)$/, `/ ${a})`) : c.replace(/\)$/, ` / ${a})`)) : c);

  // ---------- 고르기 ----------
  const key = () => (view.tab === 'trade' ? 'tc' : 'nc');
  const pass = (x) => {
    if (x.live || x.stable) return false;
    if (view.period !== 'all' && x.notice_ts < nowSec() - Number(view.period) * 365 * 86400) return false;
    if (view.bn === 'yes' && !x.binance) return false;
    if (view.bn === 'no' && x.binance) return false;
    if (view.mode !== 'all' && x.mode !== view.mode) return false;
    return true;
  };
  const compute = () => {
    curves = data.listings.filter((x) => x[key()] && pass(x));
    const by = {};
    curves.forEach((x) => x[key()].forEach(([off, v]) => { (by[off] = by[off] || []).push(v); }));
    const offs = Object.keys(by).map(Number).sort((a, b) => a - b);
    agg = offs.map((o) => ({ o, n: by[o].length, med: q(by[o], 0.5), lo: q(by[o], 0.25), hi: q(by[o], 0.75) }));
  };
  const medAt = (off) => { if (!agg || !agg.length) return null; let best = agg[0]; agg.forEach((a) => { if (Math.abs(a.o - off) < Math.abs(best.o - off)) best = a; }); return best.n >= 5 ? best.med : null; };

  // ---------- 축 ----------
  const XMIN = () => (view.tab === 'trade' ? 0 : -30), XMAX = () => (view.tab === 'trade' ? 1440 : 240);
  const PAD = { l: 52, r: 16, t: 14, b: 30 };
  const xs = (off) => {
    const w = W - PAD.l - PAD.r;
    if (view.tab === 'trade') return PAD.l + (Math.sqrt(Math.max(0, off)) / Math.sqrt(1440)) * w;
    // 공지 직후: 공지 전 30분은 왼쪽 15%, 공지 뒤 4시간은 제곱근 눈금
    if (off < 0) return PAD.l + (0.15 * (off + 30)) / 30 * w;
    return PAD.l + (0.15 + 0.85 * Math.sqrt(off) / Math.sqrt(240)) * w;
  };
  const YLO = Math.log(0.4), YHI = Math.log(4);
  const ys = (pctv) => { const v = clamp(Math.log(Math.max(0.01, 1 + pctv / 100)), YLO, YHI); return PAD.t + (1 - (v - YLO) / (YHI - YLO)) * (H - PAD.t - PAD.b); };
  const XT = () => (view.tab === 'trade'
    ? [[0, '개시'], [5, '5분'], [15, '15분'], [60, '1시간'], [240, '4시간'], [720, '12시간'], [1440, '24시간']]
    : [[-30, '−30분'], [0, '공지'], [5, '5분'], [15, '15분'], [60, '1시간'], [120, '2시간'], [240, '4시간']]);
  const YT = [-50, -20, 0, 25, 50, 100, 200];

  // ---------- 그리기 ----------
  function path(pts, live) {
    ctx.beginPath();
    pts.forEach(([o, v], i) => { const x = xs(o), y = ys(v); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
    if (!live) return;
  }
  function draw() {
    if (!data || !W) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    // 눈금
    ctx.font = '11px "Geist Mono", monospace';
    ctx.textAlign = 'right';
    YT.forEach((t) => {
      const y = ys(t);
      ctx.strokeStyle = t === 0 ? alpha(C.text3, 0.6) : alpha(C.text3, 0.18);
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(W - PAD.r, y); ctx.stroke();
      ctx.fillStyle = C.text3; ctx.fillText(t === 0 ? '0%' : pct(t, 0), PAD.l - 6, y + 4);
    });
    ctx.textAlign = 'center';
    XT().forEach(([o, l]) => {
      const x = xs(o);
      ctx.strokeStyle = alpha(C.text3, o === 0 ? 0.5 : 0.12);
      ctx.beginPath(); ctx.moveTo(x, PAD.t); ctx.lineTo(x, H - PAD.b); ctx.stroke();
      ctx.fillStyle = C.text3; ctx.fillText(l, x, H - PAD.b + 18);
    });
    // 과거 곡선
    ctx.lineWidth = 1;
    ctx.strokeStyle = alpha(C.text3, curves.length > 120 ? 0.14 : 0.22);
    curves.forEach((x) => { path(x[key()]); ctx.stroke(); });
    // 25~75% 범위와 중앙값
    const band = agg.filter((a) => a.n >= 5);
    if (band.length > 1) {
      ctx.beginPath();
      band.forEach((a, i) => { const x = xs(a.o), y = ys(a.hi); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
      [...band].reverse().forEach((a) => ctx.lineTo(xs(a.o), ys(a.lo)));
      ctx.closePath();
      ctx.fillStyle = alpha(C.text, 0.08);
      ctx.fill();
      ctx.beginPath();
      band.forEach((a, i) => { const x = xs(a.o), y = ys(a.med); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
      ctx.strokeStyle = C.text; ctx.lineWidth = 2; ctx.stroke();
    }
    // 고른 곡선·가리킨 곡선
    [view.hover, view.sel].forEach((u, i) => {
      const x = u && data.listings.find((y) => y.uid === u && y[key()]);
      if (!x) return;
      path(x[key()]); ctx.strokeStyle = i ? C.up : alpha(C.text2, 0.9); ctx.lineWidth = i ? 2.2 : 1.6; ctx.stroke();
    });
    // 진행 중 상장
    Object.entries(liveCurves).forEach(([sym, pts]) => {
      if (view.tab !== 'trade' || pts.length < 2) return;
      path(pts); ctx.strokeStyle = C.accent; ctx.lineWidth = 2.6; ctx.stroke();
      const [o, v] = pts[pts.length - 1];
      ctx.fillStyle = C.accent; ctx.beginPath(); ctx.arc(xs(o), ys(v), 4, 0, Math.PI * 2); ctx.fill();
      ctx.font = '700 12px Geist, Pretendard, sans-serif'; ctx.textAlign = 'left';
      ctx.fillText(sym, Math.min(xs(o) + 8, W - PAD.r - 40), ys(v) - 8);
    });
  }

  // ---------- 요약 ----------
  function stats() {
    const box = $('#lstStats');
    const ms = curves.map((x) => x.m || {});
    const pick = (k) => ms.map((m) => m[k]).filter((v) => v != null);
    const cell = (label, vals, fmt, extra) => {
      const n = vals.length, weak = n < 10;
      return `<div class="${weak ? 'is-weak' : ''}"><dt>${label}</dt><dd>${n ? fmt(vals) : '–'}</dd><span>${extra ? extra(vals) + ' · ' : ''}n=${n}${weak ? ' · 표본 적음' : ''}</span></div>`;
    };
    let html;
    if (view.tab === 'trade') {
      html = cell('24시간 안 고점', pick('peak24'), (v) => pct(q(v, 0.5)), (v) => `가운데 절반 ${pct(q(v, 0.25), 0)} ~ ${pct(q(v, 0.75), 0)}`)
        + cell('고점까지 걸린 시간', pick('peak_min'), (v) => dur(q(v, 0.5)), (v) => `${Math.round(v.filter((x) => x <= 15).length / v.length * 100)}%는 15분 안`)
        + cell('1시간 뒤', pick('r60'), (v) => pct(q(v, 0.5)), (v) => `${Math.round(v.filter((x) => x < 0).length / v.length * 100)}%는 개시가 아래`)
        + cell('24시간 뒤', pick('r1440'), (v) => pct(q(v, 0.5)), (v) => `${Math.round(v.filter((x) => x < 0).length / v.length * 100)}%는 개시가 아래`)
        + cell('고점 대비 24시간 뒤', pick('dd_from_peak'), (v) => pct(q(v, 0.5)));
    } else {
      const last = curves.map((x) => { const p = x.nc; return p && p.length ? p[p.length - 1][1] : null; }).filter((v) => v != null);
      html = cell('공지 후 60분 안 최고 상승(공지빔)', pick('notice_peak60'), (v) => pct(q(v, 0.5)), (v) => `가운데 절반 ${pct(q(v, 0.25), 0)} ~ ${pct(q(v, 0.75), 0)}`)
        + cell('공지 4시간 뒤', last, (v) => pct(q(v, 0.5)), (v) => `${Math.round(v.filter((x) => x < 0).length / v.length * 100)}%는 공지 전보다 아래`);
    }
    box.innerHTML = html;
    const c = data.counts || {};
    $('#lstAxis').textContent = view.tab === 'trade'
      ? '가로: 업비트 원화 첫 거래부터 24시간(앞쪽을 넓게 펼친 눈금) · 세로: 첫 1분봉 시가 대비 변화(로그 눈금, −60%~+300% 밖은 잘림) · 흰 선 = 중앙값, 띠 = 가운데 절반'
      : '가로: 공지 30분 전부터 4시간 뒤 · 세로: 공지 직전 1분 바이낸스 종가 대비 변화(로그 눈금) · 흰 선 = 중앙값, 띠 = 가운데 절반';
    $('#lstNote').textContent = `원화 상장 ${c.krw_listings || 0}건 중 ${c.excluded || 0}건은 거래 종료 등으로 시세가 없어 빠졌고, 스테이블코인 ${c.stable || 0}건은 성격이 달라 집계에서 뺐으며, 공지 제목에서 티커를 읽지 못한 ${c.no_ticker_titles || 0}건(2017년 초기 공지)도 빠졌습니다. 살아남은 코인만 남아 실제보다 좋게 보일 수 있습니다. 과거 상장의 가격 변화이며, 앞으로도 같다는 뜻은 아닙니다.`;
  }

  // ---------- 진행 중 상장 ----------
  function renderNow() {
    const box = $('#lstNow');
    const live = data.listings.filter((x) => x.live);
    if (!live.length) {
      const last = data.listings.find((x) => x.tc);
      box.innerHTML = last ? `<p class="lst__idle small muted">지금 진행 중인 원화 상장은 없습니다 · 최근 상장 <b>${esc(last.sym)}</b> (${day(last.notice_ts)})</p>` : '';
      return;
    }
    box.innerHTML = live.map((x) => {
      const pts = liveCurves[x.sym] || x.tc || [];
      const lastPt = pts.length ? pts[pts.length - 1] : null;
      const m = lastPt ? medAt(lastPt[0]) : null;
      const started = x.trade_ts && x.trade_ts <= nowSec();
      const status = !x.trade_ts ? '거래 개시 시각 확인 중' : started ? `거래 개시 후 ${dur((nowSec() - x.trade_ts) / 60)}` : `거래 개시 ${hm(x.trade_ts)} 예정`;
      return `<article class="lnow"><p class="lnow__k"><span class="live-dot" aria-hidden="true"></span>진행 중 상장 · ${esc(status)}</p>`
        + `<h2 class="lnow__t"><b>${esc(x.sym)}</b> ${esc(x.title)}</h2>`
        + `<dl class="lnow__v"><div><dt>공지</dt><dd>${hm(x.notice_ts)}</dd></div>`
        + `<div><dt>개시가 대비 지금</dt><dd class="${lastPt && lastPt[1] < 0 ? 'down' : 'up'}">${lastPt ? pct(lastPt[1]) : '–'}</dd></div>`
        + `<div><dt>같은 시점 과거 중앙값</dt><dd>${m == null ? '–' : pct(m)}</dd></div>`
        + `<div><dt>차이</dt><dd>${lastPt && m != null ? (lastPt[1] - m >= 0 ? '+' : '−') + Math.abs(lastPt[1] - m).toFixed(1) + '%p' : '–'}</dd></div></dl></article>`;
    }).join('');
  }
  async function pollLive() {
    if (!data || !proxy) return;
    const live = data.listings.filter((x) => x.live && x.trade_ts && x.trade_ts <= nowSec() && x.tbase);
    for (const x of live) {
      try {
        const res = await fetch(`${proxy}/upbit-candles?market=KRW-${encodeURIComponent(x.sym)}&count=200`);
        if (!res.ok) continue;
        const rows = await res.json();
        const by = new Map((x.tc || []).map(([o, v]) => [o, v]));
        rows.forEach((r) => {
          const t = Date.parse(r.candle_date_time_utc + 'Z') / 1000;
          const off = Math.round((t - x.trade_ts) / 60);
          if (off >= 0 && off <= 1440) by.set(off, (r.trade_price / x.tbase - 1) * 100);
        });
        liveCurves[x.sym] = [...by.entries()].sort((a, b) => a[0] - b[0]);
      } catch (e) {}
    }
    renderNow(); draw();
  }

  // ---------- 공지 목록 ----------
  function rows() {
    // 공지 하나에 코인이 여럿이면 첫 코인 기준으로 보여 주고 그 이름을 붙인다
    const byUid = new Map();
    data.listings.forEach((x) => { if (!byUid.has(x.uid)) byUid.set(x.uid, x); });
    const list = data.notices.filter((n) => view.kind === 'all' || n.kind === view.kind);
    $('#lstRows').innerHTML = list.slice(0, view.shown).map((n) => {
      const x = byUid.get(n.uid), m = (x && x.m) || {};
      const can = x && x.tc;
      const mine = (n.symbols || []).some((sym) => watch.includes(sym));
      return `<tr data-uid="${esc(n.uid)}" class="${view.sel === n.uid ? 'is-sel' : ''}${can ? ' is-pick' : ''}${mine ? ' is-watch' : ''}">`
        + `<td class="mono">${hm(n.ts)}${newUids.has(n.uid) ? ' <span class="lst__new">NEW</span>' : ''}</td>`
        + `<td><span class="lkind lkind--${esc(n.kind)}">${KIND[n.kind] || esc(n.kind)}${n.kind === 'listing' && n.krw ? ' · 원화' : ''}</span></td>`
        + `<td class="mono">${esc((n.symbols || []).join(', ') || '–')}</td>`
        + `<td class="lst__title"><a href="https://upbit.com/service_center/notice?id=${esc(n.uid)}" target="_blank" rel="noopener">${esc(n.title)}</a></td>`
        + `<td class="mono ${m.peak24 == null ? 'muted' : 'up'}">${m.peak24 == null ? (x && x.excluded ? '시세 없음' : '–') : ((n.symbols || []).length > 1 ? esc(x.sym) + ' ' : '') + pct(m.peak24)}</td>`
        + `<td class="mono ${m.r1440 == null ? 'muted' : m.r1440 >= 0 ? 'up' : 'down'}">${pct(m.r1440)}</td></tr>`;
    }).join('');
    $('#lstMore').hidden = list.length <= view.shown;
  }
  $('#lstMore').addEventListener('click', () => { view.shown += 100; rows(); });
  $('#lstRows').addEventListener('click', (e) => {
    if (e.target.closest('a')) return;
    const tr = e.target.closest('tr.is-pick');
    if (!tr) return;
    view.sel = view.sel === tr.dataset.uid ? null : tr.dataset.uid;
    rows(); draw();
    if (view.sel) $('#lstChart').scrollIntoView({ behavior: 'smooth', block: 'center' });
  });
  async function pollNotices() {
    if (!proxy || !data) return;
    try {
      const res = await fetch(`${proxy}/upbit-notices`);
      if (!res.ok) return;
      const j = await res.json();
      const known = new Set(data.notices.map((n) => String(n.uid)));
      ((j.data || {}).notices || []).forEach((n) => {
        const uid = String(n.id), t = n.title || '';
        if (known.has(uid)) return;
        const kind = /유의 ?종목/.test(t) ? 'caution' : /거래 ?지원 종료/.test(t) ? 'delisting' : /(디지털 자산 추가|신규 거래지원|신규 상장|코인 추가)/.test(t) ? 'listing' : null;
        if (!kind) return;
        const syms = [...t.matchAll(/\(([A-Z0-9]{1,15})\)/g)].map((m) => m[1]).filter((s) => !['KRW', 'BTC', 'USDT'].includes(s));
        data.notices.unshift({ uid, ts: Date.parse(n.first_listed_at || n.listed_at) / 1000, title: t, kind, krw: /KRW|원화/.test(t), symbols: syms });
        newUids.add(uid);
      });
      if (newUids.size) rows();
    } catch (e) {}
  }

  // ---------- 가리키기 ----------
  const nearest = (mx, my) => {
    let best = null;
    curves.forEach((x) => {
      const pts = x[key()];
      for (let i = 1; i < pts.length; i++) {
        const x0 = xs(pts[i - 1][0]), x1 = xs(pts[i][0]);
        if (mx < x0 || mx > x1) continue;
        const f = (mx - x0) / (x1 - x0 || 1), v = pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f, d = Math.abs(ys(v) - my);
        if (d < 10 && (!best || d < best.d)) best = { x, v, off: pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * f, d };
        break;
      }
    });
    return best;
  };
  canvas.addEventListener('mousemove', (e) => {
    const r = canvas.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
    const b = nearest(mx, my);
    const u = b ? b.x.uid : null;
    if (u !== view.hover) { view.hover = u; draw(); }
    if (!b) { tip.hidden = true; return; }
    tip.hidden = false;
    tip.innerHTML = `<b>${esc(b.x.sym)}</b> · ${day(b.x.notice_ts)}<br>${view.tab === 'trade' ? '개시 후' : '공지 후'} ${dur(Math.max(0, b.off))} <b class="${b.v >= 0 ? 'up' : 'down'}">${pct(b.v)}</b>`;
    tip.style.left = clamp(mx + 12, 0, W - 160) + 'px';
    tip.style.top = clamp(my - 44, 0, H - 50) + 'px';
  });
  canvas.addEventListener('mouseleave', () => { tip.hidden = true; if (view.hover) { view.hover = null; draw(); } });
  canvas.addEventListener('click', (e) => {
    const r = canvas.getBoundingClientRect();
    const b = nearest(e.clientX - r.left, e.clientY - r.top);
    view.sel = b ? b.x.uid : null;
    rows(); draw();
  });

  // ---------- 설정 ----------
  $$('.mseg__b', root).forEach((b) => b.addEventListener('click', () => {
    const k = ['tab', 'period', 'bn', 'mode', 'kind'].find((n) => b.dataset[n] != null);
    if (!k) return;
    view[k] = b.dataset[k];
    $$(`[data-${k}]`, root).forEach((x) => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
    if (k === 'kind') { view.shown = 50; rows(); return; }
    compute(); stats(); renderNow(); draw();
  }));

  const resize = () => {
    W = chartBox.clientWidth; H = chartBox.clientHeight; dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    draw();
  };
  new ResizeObserver(resize).observe(chartBox);

  (async () => {
    try {
      const res = await fetch(root.dataset.src + '?t=' + Math.floor(Date.now() / 60000), { cache: 'no-store' });
      data = await res.json();
    } catch (e) {
      $('#lstNote').textContent = '상장 데이터를 불러오지 못했습니다.';
      return;
    }
    compute(); stats(); renderNow(); rows(); resize();
    pollLive();
    setInterval(() => { if (!document.hidden) pollLive(); }, 30000);
    setInterval(() => { if (!document.hidden) pollNotices(); }, 60000);
  })();
}

main();
