// 뉴스 영향(/map/): data/moves.json(15분마다)을 읽어 그린다.
// 시장 물결(한 줄 요약) → 실제와 "시장만 따랐다면"의 차이(메인 차트) → 24시간 변동 영수증 → 오늘의 큰 움직임.
const S = window.SIGNAL || {};
const BASE = S.base || '/';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const NS = 'http://www.w3.org/2000/svg';
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (v, d = 2) => (v == null || !isFinite(v) ? '–' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(d)}%`);
const sg = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : '');
const two = (n) => String(n).padStart(2, '0');
const kd = (t) => new Date((t + 9 * 3600) * 1000);
const hm = (t) => { const d = kd(t); return `${two(d.getUTCHours())}:${two(d.getUTCMinutes())}`; };
const md = (t) => { const d = kd(t); return `${d.getUTCMonth() + 1}.${two(d.getUTCDate())}`; };
const LABEL = { likely: '유력', mixed: '복합', none: '연결 안 됨' };
const el = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
const linked = (e) => e.label === 'likely' || e.label === 'mixed';
const niceStep = (x) => { const p = Math.pow(10, Math.floor(Math.log10(x))), f = x / p; return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * p; };

function main() {
  const root = $('#im');
  if (!root) return;
  const ICONS = new Set((root.dataset.icons || '').split(','));
  const logo = (s) => (ICONS.has(s) ? `<img class="im-logo" src="${BASE}assets/coins/${s}.svg" alt="" width="18" height="18">` : `<span class="im-ph" aria-hidden="true">${esc(s.slice(0, 1))}</span>`);
  let D = null, coins = [], bySym = {}, allEv = [], geo = null;
  const state = { sym: null, ev: null, filter: 'news' };
  const T = (min) => D.t0 + min * 60;

  // ---------- 시장 물결 ----------
  function renderTide() {
    const t = D.tide;
    $('#imAsof').textContent = `${md(D.at)} ${hm(D.at)} KST 기준 · 최근 24시간 · 15분마다 갱신`;
    const n = $('#imTideNum'); n.textContent = pct(t.total); n.className = 'im-tide__num ' + sg(t.total);
    $('#imTideText').innerHTML = `시장 전체(시총 가중 ${coins.length}개)가 24시간 동안 <b>${pct(t.total)}</b> 움직였습니다. 알트는 보통 이 물결의 <b>${(t.medianAltBeta || 1).toFixed(1)}배</b>로 함께 움직이므로, 그만큼은 뉴스가 아니라 시장 몫입니다.`;
    const ln = allEv.filter(linked).length;
    $('#imTideStats').innerHTML = `<div><dt>평소보다 크게 움직인 구간</dt><dd>${allEv.length}<small>건</small></dd></div>
      <div><dt>그 코인 뉴스와 연결된 것</dt><dd>${ln}<small>건</small></dd></div>
      <div><dt>원인 뉴스를 찾지 못한 것</dt><dd>${allEv.length - ln}<small>건</small></dd></div>`;
    const svg = $('#imTideSvg'); svg.innerHTML = '';
    const W = svg.clientWidth || 600, H = 96, s = t.t, n0 = s.length - 1, M = D.minutes;
    const lo = Math.min(0, ...s), hi = Math.max(0, ...s), pad = (hi - lo) * 0.12 || 0.2;
    const X = (k) => (k / n0) * W, XM = (m) => (m / M) * W, Y = (v) => 8 + (1 - (v - lo + pad) / (hi - lo + 2 * pad)) * (H - 26);
    el('line', { x1: 0, x2: W, y1: Y(0), y2: Y(0), stroke: 'var(--line-strong)', 'stroke-dasharray': '2 3' }, svg);
    t.events.forEach((e) => el('rect', { x: XM(e.a), y: 0, width: Math.max(2, XM(e.e) - XM(e.a)), height: H - 18, fill: 'color-mix(in oklab, var(--text) 5%, transparent)', rx: 2 }, svg));
    el('path', { d: s.map((v, k) => `${k ? 'L' : 'M'}${X(k).toFixed(1)} ${Y(v).toFixed(1)}`).join(''), fill: 'none', stroke: 'var(--text)', 'stroke-width': 1.5, 'stroke-linejoin': 'round' }, svg);
    el('circle', { cx: X(n0), cy: Y(s[n0]), r: 3, fill: t.total >= 0 ? 'var(--up)' : 'var(--down)' }, svg);
    for (let h = 0; h <= 24; h += 6) { const tx = el('text', { x: XM(h * 60), y: H - 2, class: 'im-ax', 'text-anchor': h === 0 ? 'start' : h === 24 ? 'end' : 'middle' }, svg); tx.textContent = h === 24 ? '지금' : hm(T(h * 60)); }
  }

  // ---------- 코인 고르기 ----------
  function renderCoins() {
    $('#imCoins').innerHTML = coins.map((c) => `<button type="button" class="im-coin" data-s="${c.s}" aria-pressed="false" title="24시간 자기 몫 ${pct(c.own)}">${logo(c.s)}<b>${c.s}</b><span class="im-num ${sg(c.total)}">${pct(c.total, 1)}</span></button>`).join('');
  }

  // ---------- 메인 차트 ----------
  function renderChart() {
    const c = bySym[state.sym], svg = $('#imChartSvg');
    svg.innerHTML = '';
    const W = svg.clientWidth, H = svg.clientHeight, narrow = W < 560, M = D.minutes, st = D.step;
    const padL = 4, padR = narrow ? 40 : 48, padT = 26, padB = 22;
    const t = c.t, m = c.m, n0 = t.length - 1;
    let lo = Math.min(0, ...t, ...m), hi = Math.max(0, ...t, ...m);
    const span = hi - lo || 1; lo -= span * 0.08; hi += span * 0.08;
    const XM = (min) => padL + (Math.min(min, M) / M) * (W - padL - padR), X = (k) => XM(k * st), Y = (v) => padT + (1 - (v - lo) / (hi - lo)) * (H - padT - padB);
    geo = { X, Y, n0, W, padL, padR, padT, st };
    const stepV = niceStep((hi - lo) / 4);
    for (let v = Math.ceil(lo / stepV) * stepV; v <= hi; v += stepV) {
      const y = Y(v), zero = Math.abs(v) < 1e-9;
      el('line', { x1: padL, x2: W - padR, y1: y, y2: y, stroke: zero ? 'var(--line-strong)' : 'var(--line)' }, svg);
      const tx = el('text', { x: W - padR + 8, y: y + 4, class: 'im-ax' }, svg); tx.textContent = zero ? '0' : pct(v, stepV < 0.5 ? 1 : 0);
    }
    for (let h = 0; h <= 24; h += narrow ? 8 : 4) { const tx = el('text', { x: XM(h * 60), y: H - 4, class: 'im-ax', 'text-anchor': h === 0 ? 'start' : 'middle' }, svg); tx.textContent = h === 24 ? '지금' : hm(T(h * 60)); }
    c.events.forEach((e, i) => {
      const on = state.ev === i;
      const g = el('g', { class: 'im-pin', 'data-i': i, tabindex: 0, role: 'button', 'aria-label': `${i + 1}번 움직임 ${pct(e.size)}, ${LABEL[e.label]}` }, svg);
      el('rect', { x: XM(e.a), y: padT - 4, width: Math.max(3, XM(e.e) - XM(e.a)), height: H - padT - padB + 4, fill: on ? 'color-mix(in oklab, var(--accent) 12%, transparent)' : 'color-mix(in oklab, var(--text) 4%, transparent)' }, g);
      el('line', { x1: XM(e.a), x2: XM(e.a), y1: padT - 4, y2: H - padB, stroke: on ? 'var(--accent)' : 'color-mix(in oklab, var(--text) 24%, transparent)' }, g);
      el('rect', { x: XM(e.a) - 10, y: 0, width: 20, height: 18, rx: 6, fill: on ? 'var(--accent)' : 'color-mix(in oklab, var(--text) 11%, transparent)' }, g);
      const tx = el('text', { x: XM(e.a), y: 13, 'text-anchor': 'middle', fill: on ? 'var(--on-accent)' : 'var(--text)' }, g); tx.textContent = String(i + 1);
    });
    const fillPath = (pos) => {
      let d = '', open = false, back = [];
      const flush = () => { if (open) { d += back.reverse().join('') + 'Z'; open = false; back = []; } };
      for (let k = 0; k <= n0; k++) {
        if ((t[k] >= m[k]) === pos) { const x = X(k).toFixed(1); d += `${open ? 'L' : 'M'}${x} ${Y(t[k]).toFixed(1)}`; back.push(`L${x} ${Y(m[k]).toFixed(1)}`); open = true; } else flush();
      }
      flush();
      return d;
    };
    el('path', { d: fillPath(true), fill: 'var(--up-a)' }, svg);
    el('path', { d: fillPath(false), fill: 'var(--down-a)' }, svg);
    const line = (s) => s.map((v, k) => `${k ? 'L' : 'M'}${X(k).toFixed(1)} ${Y(v).toFixed(1)}`).join('');
    el('path', { d: line(m), fill: 'none', stroke: 'var(--mkt)', 'stroke-width': 1.5, 'stroke-dasharray': '5 4', 'stroke-linejoin': 'round' }, svg);
    el('path', { d: line(t), fill: 'none', stroke: 'var(--text)', 'stroke-width': 1.75, 'stroke-linejoin': 'round' }, svg);
    const gapUp = Y(t[n0]) < Y(m[n0]);
    const endLbl = (v, fill, dy) => { const tx = el('text', { x: X(n0) - 6, y: Y(v) + dy, class: 'im-ax', 'text-anchor': 'end', fill }, svg); tx.textContent = pct(v); };
    endLbl(t[n0], 'var(--text)', gapUp ? -8 : 16); endLbl(m[n0], 'var(--mkt)', gapUp ? 16 : -8);
    const cross = el('g', { opacity: 0 }, svg);
    el('line', { y1: padT - 4, y2: H - padB, stroke: 'color-mix(in oklab, var(--text) 30%, transparent)', class: 'cx' }, cross);
    el('circle', { r: 3.5, fill: 'var(--text)', class: 'ct' }, cross); el('circle', { r: 3, fill: 'var(--mkt)', class: 'cm' }, cross);
    geo.cross = cross;
    $('#imChartDesc').textContent = `${c.s} 최근 24시간: 실제 ${pct(c.total)}, 시장 몫 ${pct(c.market)}, 자기 몫 ${pct(c.own)}. 평소보다 크게 움직인 구간 ${c.events.length}개.`;
  }

  // ---------- 고른 움직임 ----------
  const lead = (n) => (n.lead > 0 ? `움직임 ${n.lead}분 전` : n.lead === 0 ? '움직임과 같은 분' : `움직임 ${-n.lead}분 뒤 보도`);
  function renderEvent() {
    const c = bySym[state.sym], box = $('#imEv');
    if (state.ev == null || !c.events[state.ev]) {
      box.innerHTML = c.events.length
        ? `<p class="im-empty">차트 위 번호를 누르면 그 움직임과 원인 후보 뉴스를 봅니다. ${c.s}는 최근 24시간에 평소보다 크게 움직인 구간이 <b>${c.events.length}개</b> 있습니다.</p>`
        : `<p class="im-empty">${c.s}는 최근 24시간 동안 <b>시장 몫을 빼면 평소 흔들림 안에서만</b> 움직였습니다. 대부분 시장 물결을 따른 하루입니다.</p>`;
      return;
    }
    const e = c.events[state.ev], dur = Math.round((e.t1 - e.t0) / 60);
    const news = e.news.length
      ? e.news.map((n) => `<a class="im-nrow" href="${BASE}a/${esc(n.id)}/"><span class="im-chip im-chip--${e.label}">${LABEL[e.label]}</span><span class="im-nrow__t">${esc(n.title)}</span><span class="im-nrow__m">${esc(n.src || '')} · ${lead(n)}</span></a>`).join('')
      : `<p class="im-empty"><span class="im-chip im-chip--none">연결 안 됨</span> SIGNAL이 모으는 매체에서 <b>${c.s}를 언급한 뉴스를 찾지 못했습니다.</b> 같은 시간대 다른 뉴스 ${e.nearby}건은 이 코인과 관련이 확인되지 않아 붙이지 않았습니다.</p>`;
    box.innerHTML = `<div class="im-ev"><div>
        <p class="im-ev__k"><span class="im-n">${state.ev + 1}</span>${md(e.t0)} ${hm(e.t0)}–${hm(e.t1)} · ${dur}분</p>
        <p class="im-ev__big ${sg(e.size)}">${pct(e.size)}</p>
        <p class="im-ev__sub">자기 몫 · 평소 60분 흔들림의 <b class="im-num">${Math.abs(e.z).toFixed(1)}배</b><br>같은 시간 시장 몫 <span class="im-num im-mk">${pct(e.market)}</span></p>
      </div><div class="im-news">${news}</div></div>`;
  }

  // ---------- 영수증 ----------
  function renderReceipt() {
    const c = bySym[state.sym];
    const evSum = c.events.reduce((a, e) => a + e.size, 0);
    const rows = [{ k: 'mk', label: '<b>시장 몫</b>', sub: `β ${c.beta.toFixed(2)} × 나머지 시장`, v: c.market }];
    c.events.forEach((e, i) => rows.push({ k: 'ev', i, label: `<span class="im-n">${i + 1}</span><span class="im-chip im-chip--${e.label}">${LABEL[e.label]}</span><span>${linked(e) && e.news[0] ? esc(e.news[0].title) : '원인 뉴스 없음'}</span>`, v: e.size }));
    rows.push({ k: 'rest', label: '<b>작은 움직임들</b>', sub: '평소 흔들림 안', v: c.own - evSum });
    let run = 0;
    const spans = rows.map((r) => { const a = run; run += r.v; return [a, run]; });
    const ext = [0, c.total, ...spans.flat()], lo = Math.min(...ext), hi = Math.max(...ext), pad = (hi - lo) * 0.04 || 0.1;
    const P = (v) => ((v - lo + pad) / (hi - lo + 2 * pad)) * 100;
    const bar = (a, b, cls) => `<span class="im-rtrack"><i class="im-raxis" style="left:${P(0)}%"></i><i class="im-rbar ${cls}" style="left:${P(Math.min(a, b))}%;width:${Math.max(0.4, Math.abs(P(b) - P(a)))}%"></i></span>`;
    $('#imRc').innerHTML = rows.map((r, j) => {
      const [a, b] = spans[j], cls = r.k === 'mk' ? 'im-m' : r.k === 'rest' ? 'im-rest' : sg(r.v) || 'im-m';
      const tag = r.k === 'ev' ? 'button' : 'div';
      return `<${tag} class="im-rrow ${r.k === 'ev' && state.ev === r.i ? 'is-sel' : ''}" ${r.k === 'ev' ? `type="button" data-i="${r.i}"` : ''}><span class="im-rrow__l">${r.label}${r.sub ? `<span class="im-rsub">${r.sub}</span>` : ''}</span>${bar(a, b, cls)}<span class="im-rv ${r.k === 'mk' ? 'im-mk' : r.k === 'rest' ? '' : sg(r.v)}">${pct(r.v)}</span></${tag}>`;
    }).join('') + `<div class="im-rrow im-rrow--total"><span class="im-rrow__l"><b>= 실제 24시간 등락</b></span>${bar(0, c.total, sg(c.total) || 'im-m')}<span class="im-rv ${sg(c.total)}">${pct(c.total)}</span></div>`;
    $('#imRcSub').textContent = `${c.s} · 위에서부터 더하면 실제 등락이 됩니다`;
  }

  // ---------- 오늘의 큰 움직임 ----------
  function renderMovers() {
    const list = allEv.filter((e) => state.filter === 'all' || linked(e)).sort((a, b) => Math.abs(b.size) - Math.abs(a.size)).slice(0, 10);
    const mx = Math.max(0.1, ...list.map((e) => Math.max(Math.abs(e.size), Math.abs(e.market))));
    const half = (v) => (Math.abs(v) / mx) * 50;
    const bar = (v, cls) => `<i class="${cls}" style="left:${v >= 0 ? 50 : 50 - half(v)}%;width:${half(v)}%"></i>`;
    $('#imMv').innerHTML = list.map((e) => {
      const why = linked(e) && e.news[0] ? esc(e.news[0].title) : `원인 뉴스 없음 · 같은 시간 뉴스 ${e.nearby}건`;
      return `<li><button type="button" class="im-mvi ${state.sym === e.sym && state.ev === e.i ? 'is-sel' : ''}" data-s="${e.sym}" data-i="${e.i}">
        ${logo(e.sym)}<span class="im-mvi__top"><b>${e.sym}</b><span>${md(e.t0)} ${hm(e.t0)} · 평소의 ${Math.abs(e.z).toFixed(1)}배</span></span><span class="im-mvi__v ${sg(e.size)}">${pct(e.size)}</span>
        <span class="im-mvi__bar" aria-hidden="true"><i class="im-zero"></i>${bar(e.market, 'im-m')}${bar(e.size, e.size >= 0 ? 'up' : 'down')}</span>
        <span class="im-mvi__why"><span class="im-chip im-chip--${e.label}">${LABEL[e.label]}</span><span>${why}</span></span></button></li>`;
    }).join('') || `<li class="im-empty" style="padding:12px 0">${state.filter === 'news' ? '최근 24시간에는 그 코인 뉴스와 연결된 큰 움직임이 없습니다.' : '최근 24시간에 평소보다 크게 움직인 구간이 없습니다.'}</li>`;
  }

  // ---------- 선택 ----------
  function select(sym, ev, scroll) {
    const coinChanged = sym !== state.sym;
    state.sym = sym; state.ev = ev;
    const c = bySym[sym];
    $$('#imCoins .im-coin').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.s === sym)));
    if (coinChanged) { const cb = $(`#imCoins .im-coin[data-s="${sym}"]`), box = $('#imCoins'); if (cb) box.scrollTo({ left: cb.offsetLeft - box.clientWidth / 2 + cb.clientWidth / 2, behavior: reduced ? 'auto' : 'smooth' }); }
    $('#imCoinId').innerHTML = `${logo(sym)}<div><h2 class="im-chead__sym">${sym}</h2><p class="im-sub">시장 민감도 β ${c.beta.toFixed(2)} · 평소 60분 흔들림 ±${c.sig60.toFixed(2)}%</p></div>`;
    $('#imCoinNums').innerHTML = `<div><dt>실제 24시간</dt><dd class="${sg(c.total)}">${pct(c.total)}</dd></div><span class="im-eq">=</span>
      <div><dt>시장 몫</dt><dd class="im-mk">${pct(c.market)}</dd></div><span class="im-eq">+</span>
      <div><dt>자기 몫</dt><dd class="${sg(c.own)}">${pct(c.own)}</dd></div>`;
    renderChart(); renderEvent(); renderReceipt(); renderMovers();
    const q = new URLSearchParams(); q.set('s', sym); history.replaceState(null, '', location.pathname + '?' + q);
    if (scroll && matchMedia('(max-width: 720px)').matches) $('.im-chartcard').scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
  }

  // ---------- 이벤트 ----------
  $('#imCoins').addEventListener('click', (e) => { const b = e.target.closest('[data-s]'); if (b) select(b.dataset.s, null); });
  $('#imMv').addEventListener('click', (e) => { const b = e.target.closest('[data-s]'); if (b) select(b.dataset.s, Number(b.dataset.i), true); });
  $('#imRc').addEventListener('click', (e) => { const b = e.target.closest('[data-i]'); if (b) select(state.sym, Number(b.dataset.i)); });
  $$('.im-seg button').forEach((b) => b.addEventListener('click', () => { state.filter = b.dataset.f; $$('.im-seg button').forEach((x) => x.setAttribute('aria-pressed', String(x === b))); renderMovers(); }));
  const chartBox = $('#imChart'), hover = $('#imHover');
  chartBox.addEventListener('click', (ev) => { const g = ev.target.closest('.im-pin'); if (g) select(state.sym, Number(g.dataset.i)); });
  chartBox.addEventListener('keydown', (ev) => { const g = ev.target.closest('.im-pin'); if (g && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); select(state.sym, Number(g.dataset.i)); } });
  chartBox.addEventListener('pointermove', (ev) => {
    if (!geo || ev.pointerType === 'touch') return;
    const r = $('#imChartSvg').getBoundingClientRect(), x = ev.clientX - r.left;
    const k = Math.max(0, Math.min(geo.n0, Math.round(((x - geo.padL) / (geo.W - geo.padL - geo.padR)) * (D.minutes / geo.st))));
    const c = bySym[state.sym], t = c.t[k], m = c.m[k], X = geo.X(k);
    geo.cross.setAttribute('opacity', 1);
    $('.cx', geo.cross).setAttribute('x1', X); $('.cx', geo.cross).setAttribute('x2', X);
    $('.ct', geo.cross).setAttribute('cx', X); $('.ct', geo.cross).setAttribute('cy', geo.Y(t));
    $('.cm', geo.cross).setAttribute('cx', X); $('.cm', geo.cross).setAttribute('cy', geo.Y(m));
    hover.innerHTML = `<span class="im-t">${md(D.t0)} ${hm(D.t0)} → ${hm(T(k * geo.st))} 누적</span><p><span>실제</span><b class="im-num">${pct(t)}</b></p><p><span>시장 몫</span><b class="im-num im-mk">${pct(m)}</b></p><p><span>자기 몫</span><b class="im-num ${sg(t - m)}">${pct(t - m)}</b></p>`;
    hover.hidden = false;
    const w = hover.offsetWidth;
    hover.style.transform = `translate(${Math.round(X + 14 + w > geo.W - geo.padR ? X - 14 - w : X + 14)}px, ${geo.padT}px)`;
  });
  chartBox.addEventListener('pointerleave', () => { hover.hidden = true; if (geo) geo.cross.setAttribute('opacity', 0); });
  let rt = 0;
  addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { if (D) { renderTide(); renderChart(); } }, 120); });
  new MutationObserver(() => { if (D) { renderTide(); renderChart(); } }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  // ---------- 불러오기 ----------
  const apply = (doc, first) => {
    D = doc;
    coins = D.coins.slice().sort((a, b) => b.cap - a.cap);
    bySym = Object.fromEntries(coins.map((c) => [c.s, c]));
    allEv = coins.flatMap((c) => c.events.map((e, i) => ({ ...e, sym: c.s, i })));
    renderTide(); renderCoins();
    let sym = state.sym, ev = state.ev;
    if (first) {
      const want = new URLSearchParams(location.search).get('s');
      if (want && bySym[want]) { sym = want; ev = null; }
      else {
        const top = allEv.filter(linked).sort((a, b) => Math.abs(b.size) - Math.abs(a.size))[0] || allEv.slice().sort((a, b) => Math.abs(b.size) - Math.abs(a.size))[0];
        sym = top ? top.sym : coins[0].s; ev = top ? top.i : null;
      }
    } else if (!bySym[sym]) { sym = coins[0].s; ev = null; } else if (ev != null && !bySym[sym].events[ev]) ev = null;
    select(sym, ev);
  };
  const load = async (first) => {
    try {
      const r = await fetch(root.dataset.src + '?t=' + Math.floor(Date.now() / 300000), { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      const doc = await r.json();
      if (!D || doc.at !== D.at) apply(doc, first);
      $('#imBody').hidden = false; $('#imEmpty').hidden = true;
      if (first && !reduced) ['.im-tide', '.im-coins', '.im-chartcard', '.im-receipt', '.im-movers', '.im-method'].forEach((s, k) => { const n = $(s); n.classList.add('im-rise'); n.style.animationDelay = `${k * 70}ms`; });
    } catch (e) {
      if (!D) { $('#imEmpty').hidden = false; }
    }
  };
  load(true);
  setInterval(() => { if (!document.hidden) load(false); }, 5 * 60 * 1000);
}

main();
