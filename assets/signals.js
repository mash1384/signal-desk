// 시그널 보드(/map/): data/signals.json(15분마다)을 읽어 코인마다 평소와 다른 것 네 가지와 '왜?'를 그린다.
// 줄을 누르면 그 코인의 24시간 '실제 vs 시장대로였다면' 차트와 그 사이 뉴스를 펼친다.
const S = window.SIGNAL || {};
const BASE = S.base || '/';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const NS = 'http://www.w3.org/2000/svg';
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const sgn = (v, d = 1, u = '%') => (v == null || !isFinite(v) ? '–' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(d)}${u}`);
const dir = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : '');
const two = (n) => String(n).padStart(2, '0');
const kd = (t) => new Date((t + 9 * 3600) * 1000);
const hm = (t) => { const d = kd(t); return `${two(d.getUTCHours())}:${two(d.getUTCMinutes())}`; };
const el = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
const niceStep = (x) => { const p = Math.pow(10, Math.floor(Math.log10(x))), f = x / p; return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * p; };
const WK = { '1h': '1시간', '4h': '4시간', '24h': '24시간' };
const FLAGS = ['move', 'vol', 'kimp', 'news'];
const NOTICE = { listing: '업비트 상장', caution: '업비트 유의 지정', delisting: '업비트 상장 폐지' };
const ago = (t, now) => { const m = Math.max(1, Math.round((now - t) / 60)); return m < 60 ? `${m}분 전` : m < 1440 ? `${Math.floor(m / 60)}시간 전` : `${Math.floor(m / 1440)}일 전`; };
const won = (v) => (v >= 1e12 ? `${(v / 1e12).toFixed(1)}조원` : v >= 1e8 ? `${Math.round(v / 1e8).toLocaleString('ko-KR')}억원` : `${Math.round(v / 1e4).toLocaleString('ko-KR')}만원`);

function main() {
  const root = $('#sb');
  if (!root) return;
  const ICONS = new Set((root.dataset.icons || '').split(','));
  const logo = (s) => `<span class="sb-logo" aria-hidden="true">${ICONS.has(s) ? `<img src="${BASE}assets/coins/${s}.svg" alt="" width="22" height="22">` : `<span>${esc(s.slice(0, 1))}</span>`}</span>`;
  const state = { w: '24h', f: 'flag', open: null };
  let D = null;

  // ---------- 칸 하나 ----------
  const meter = (x) => `<span class="sb-meter" aria-hidden="true"><i style="width:${Math.round(Math.max(0.04, Math.min(1, x)) * 100)}%"></i></span>`;
  function cells(c) {
    const w = c.w[state.w], f = new Set(w.flags), th = D.thresh;
    const zx = w.z != null ? Math.abs(w.z) / 4 : 0;
    const move = `<div class="sb-cell sb-cell--move ${f.has('move') ? 'is-flag' : ''}" role="cell"><span class="sb-cell__k">시장 대비</span>
      <span class="sb-cell__v ${dir(w.own)}">${sgn(w.own)}</span>
      <span class="sb-cell__s">평소 ±${(w.sd || 0).toFixed(1)}% · 실제 ${sgn(w.act)}</span>${meter(Math.max(zx, Math.abs(w.own) / th.own[state.w] / 2))}</div>`;
    const vol = !c.upbit || w.volr == null
      ? `<div class="sb-cell is-na" role="cell"><span class="sb-cell__k">거래대금</span><span class="sb-cell__v">${c.upbit ? '–' : '업비트 없음'}</span></div>`
      : `<div class="sb-cell ${f.has('vol') ? 'is-flag' : ''}" role="cell"><span class="sb-cell__k">거래대금</span><span class="sb-cell__v">${w.volr.toFixed(1)}배</span>
        <span class="sb-cell__s">${won(w.krw)}</span>${meter(w.volr / 4)}</div>`;
    const kimp = w.dkimp == null
      ? `<div class="sb-cell is-na" role="cell"><span class="sb-cell__k">김프 변화</span><span class="sb-cell__v">${c.upbit ? '–' : '업비트 없음'}</span></div>`
      : `<div class="sb-cell ${f.has('kimp') ? 'is-flag' : ''}" role="cell"><span class="sb-cell__k">김프 변화</span><span class="sb-cell__v">${sgn(w.dkimp, 2, '%p')}</span>
        <span class="sb-cell__s">현재 ${sgn(w.kimp, 2)}</span>${meter(Math.abs(w.dkimp) / th.kimp[state.w] / 2)}</div>`;
    const news = `<div class="sb-cell ${f.has('news') ? 'is-flag' : ''}" role="cell"><span class="sb-cell__k">뉴스 양</span><span class="sb-cell__v">${w.news}건</span>
      <span class="sb-cell__s">${w.newsb != null ? `평소 ${w.newsb < 1 ? w.newsb.toFixed(1) : Math.round(w.newsb)}건` : '비교 기록 없음'}</span>${meter(w.newsr ? w.newsr / 4 : 0)}</div>`;
    return move + vol + kimp + news;
  }
  function why(c) {
    const w = c.w[state.w];
    const nt = (c.notices || [])[0];
    const notice = nt ? `<span class="sb-notice is-${nt.kind}">${NOTICE[nt.kind] || '업비트 공지'} · ${ago(nt.ts, D.at)}</span>` : '';
    const n = w.why[0];
    if (!n) return `<div class="sb-why" role="cell">${notice}<span class="sb-why__none">${notice ? '' : `최근 24시간 ${esc(c.s)} 뉴스 없음`}</span></div>`;
    return `<div class="sb-why" role="cell">${notice}<span class="sb-why__t">${esc(n.title)}</span><span class="sb-why__m">${esc(n.src || '')} · ${ago(n.t, D.at)}${n.in ? '' : ` · ${WK[state.w]} 이전 소식`}</span></div>`;
  }
  const score = (c) => { const w = c.w[state.w]; return w.flags.length * 100 + Math.min(99, Math.abs(w.z || 0) * 10 + (w.volr || 0) * 5 + (c.notices.length ? 20 : 0)); };

  function render() {
    const w = state.w;
    const coins = D.coins.slice().sort((a, b) => score(b) - score(a) || b.cap - a.cap);
    const flagged = coins.filter((c) => c.w[w].flags.length || c.notices.length);
    const list = state.f === 'flag' ? flagged : coins;
    const t = D.tide.total;
    $('#sbAsof').textContent = `${kd(D.at).getUTCMonth() + 1}월 ${kd(D.at).getUTCDate()}일 ${hm(D.at)} 기준 · 15분마다 갱신`;
    $('#sbTitle').innerHTML = flagged.length ? `지금 평소와 다른 코인 <em>${flagged.length}개</em>` : '지금은 모든 코인이 평소 범위 안이에요';
    $('#sbLede').innerHTML = `시장 전체는 24시간 동안 <b class="${dir(t)}">${sgn(t)}</b>. 최근 ${WK[w]} 동안 코인 ${D.coins.length}개의 시장 대비 움직임 · 업비트 거래대금 · 김프 변화 · 뉴스 양 중 평소와 다른 것에 표시했어요.`;
    $('#sbRows').innerHTML = list.map((c) => {
      const f = new Set(c.w[w].flags);
      return `<div class="sb-row ${c.w[w].flags.length ? '' : 'is-dim'}" data-s="${c.s}" role="row">
        <button type="button" class="sb-row__main" aria-expanded="false" aria-controls="sbd-${c.s}">
          <div class="sb-coin" role="cell">${logo(c.s)}<span class="sb-coin__id"><b>${esc(c.name)}</b><span>${c.s}<span class="sb-flags" aria-label="신호 ${f.size}개">${FLAGS.map((k) => `<i class="${f.has(k) ? 'on' : ''}"></i>`).join('')}</span></span></span></div>
          ${cells(c)}${why(c)}
        </button>
        <div class="sb-detail" id="sbd-${c.s}" hidden></div>
      </div>`;
    }).join('');
    const quiet = $('#sbQuiet');
    if (state.f === 'flag') {
      quiet.hidden = false;
      quiet.innerHTML = `${flagged.length ? `나머지 ${coins.length - flagged.length}개 코인은 평소 범위 안이에요.` : `최근 ${WK[w]}에는 평소와 다른 코인이 없어요.`} <button type="button" data-all>전체 ${coins.length}개 보기</button>`;
    } else quiet.hidden = true;
    if (state.open && $(`.sb-row[data-s="${state.open}"]`)) toggle(state.open, true); else state.open = null;
  }

  // ---------- 펼친 상세 ----------
  function detail(c, box) {
    const now = D.at;
    const news = (c.news || []).filter((n) => n.t >= D.t0);
    box.innerHTML = `<div><div class="sb-legend" aria-hidden="true"><span><i class="sb-lg sb-lg--actual"></i>실제</span><span><i class="sb-lg sb-lg--market"></i>시장대로였다면</span><span><i class="sb-lg sb-lg--news"></i>${esc(c.s)} 뉴스</span></div>
        <div class="sb-chart"><svg role="img" aria-label="${esc(c.s)} 최근 24시간 실제 등락과 시장대로였다면"></svg><div class="sb-tip" hidden></div></div>
        <p class="sb-sum">24시간 동안 실제 <b class="${dir(c.w['24h'].act)}">${sgn(c.w['24h'].act, 2)}</b> = 시장대로였다면 <b>${sgn(c.w['24h'].mkt, 2)}</b> + 시장 대비 <b class="${dir(c.w['24h'].own)}">${sgn(c.w['24h'].own, 2)}</b> · 시장을 따라가는 정도 ${c.beta.toFixed(2)}배</p></div>
      <div class="sb-news"><h3>최근 24시간 ${esc(c.name)} 뉴스 ${news.length}건</h3>${news.length ? `<ol>${news.map((n, i) => `<li><a href="${BASE}a/${esc(n.id)}/" data-i="${i}" class="${n.recap ? 'recap' : ''}"><time>${hm(n.t)}</time><span class="t">${esc(n.title)}</span><span class="m">${esc(n.src || '')}${n.recap ? ' · 가격 정리 기사' : ''}</span></a></li>`).join('')}</ol>` : '<p class="sb-news__none">최근 24시간 이 코인을 언급한 뉴스가 없습니다.</p>'}</div>`;
    const svg = $('svg', box), tip = $('.sb-tip', box);
    const W = svg.clientWidth, H = svg.clientHeight, M = D.minutes, st = D.step;
    const padL = 2, padR = 46, padT = 10, padB = 40;
    const t = c.series.t, m = c.series.m, n0 = t.length - 1;
    let lo = Math.min(0, ...t, ...m), hi = Math.max(0, ...t, ...m);
    const span = hi - lo || 1; lo -= span * 0.1; hi += span * 0.1;
    const XM = (min) => padL + (Math.max(0, Math.min(min, M)) / M) * (W - padL - padR), X = (k) => XM(k * st), XT = (ts) => XM((ts - D.t0) / 60);
    const Y = (v) => padT + (1 - (v - lo) / (hi - lo)) * (H - padT - padB);
    const stepV = niceStep((hi - lo) / 3);
    for (let v = Math.ceil(lo / stepV) * stepV; v <= hi; v += stepV) {
      const y = Y(v), zero = Math.abs(v) < 1e-9;
      el('line', { x1: padL, x2: W - padR, y1: y, y2: y, stroke: zero ? 'var(--line-strong)' : 'var(--line)' }, svg);
      const tx = el('text', { x: W - padR + 8, y: y + 4, class: 'sb-ax' }, svg); tx.textContent = zero ? '0' : sgn(v, stepV < 0.5 ? 1 : 0);
    }
    for (let h = 0; h <= 24; h += W < 480 ? 8 : 4) { const tx = el('text', { x: XM(h * 60), y: H - 4, class: 'sb-ax', 'text-anchor': h === 0 ? 'start' : h === 24 ? 'end' : 'middle' }, svg); tx.textContent = h === 24 ? '지금' : hm(D.t0 + h * 3600); }
    const wmin = { '1h': 60, '4h': 240, '24h': 1440 }[state.w];
    if (wmin < M) el('rect', { x: XM(M - wmin), y: padT, width: XM(M) - XM(M - wmin), height: H - padT - padB, fill: 'color-mix(in oklab, var(--accent) 10%, transparent)' }, svg);
    const line = (s) => s.map((v, k) => `${k ? 'L' : 'M'}${X(k).toFixed(1)} ${Y(v).toFixed(1)}`).join('');
    el('path', { d: line(m), fill: 'none', stroke: 'var(--mkt)', 'stroke-width': 1.5, 'stroke-dasharray': '5 4', 'stroke-linejoin': 'round' }, svg);
    el('path', { d: line(t), fill: 'none', stroke: 'var(--text)', 'stroke-width': 1.75, 'stroke-linejoin': 'round' }, svg);
    // 뉴스 점: 차트 아래 한 줄. 중요한 뉴스일수록 크고 진하게
    const laneY = H - padB + 14;
    el('line', { x1: padL, x2: W - padR, y1: laneY, y2: laneY, stroke: 'var(--line)' }, svg);
    news.forEach((n, i) => {
      const x = XT(n.t), r = n.imp >= 3 ? 5 : n.imp >= 2 ? 4 : 3;
      const g = el('g', { class: 'sb-ndot', 'data-i': i }, svg);
      el('line', { x1: x, x2: x, y1: padT, y2: laneY, stroke: 'color-mix(in oklab, var(--text) 8%, transparent)' }, g);
      el('circle', { cx: x, cy: laneY, r: r + 6, fill: 'transparent' }, g);
      el('circle', { cx: x, cy: laneY, r, fill: n.recap ? 'var(--text-3)' : 'var(--text-2)', opacity: n.recap ? 0.5 : 0.9 }, g);
    });
    const hot = (i) => { $$('.sb-news a', box).forEach((a) => a.classList.toggle('is-hot', a.dataset.i === String(i))); };
    svg.addEventListener('pointermove', (ev) => {
      const g = ev.target.closest('.sb-ndot');
      if (!g) { tip.hidden = true; hot(-1); return; }
      const n = news[+g.dataset.i], x = XT(n.t);
      tip.innerHTML = `<b>${esc(n.title)}</b><span>${hm(n.t)} · ${esc(n.src || '')}</span>`;
      tip.hidden = false;
      const w = tip.offsetWidth;
      tip.style.transform = `translate(${Math.round(Math.max(0, Math.min(W - w, x - w / 2)))}px, ${Math.round(laneY - tip.offsetHeight - 12)}px)`;
      hot(g.dataset.i);
    });
    svg.addEventListener('pointerleave', () => { tip.hidden = true; hot(-1); });
    svg.addEventListener('click', (ev) => {
      const g = ev.target.closest('.sb-ndot');
      if (!g) return;
      const a = $(`.sb-news a[data-i="${g.dataset.i}"]`, box);
      if (a) { hot(g.dataset.i); a.scrollIntoView({ block: 'nearest', behavior: reduced ? 'auto' : 'smooth' }); }
    });
  }
  function toggle(s, force) {
    $$('.sb-row').forEach((row) => {
      const on = row.dataset.s === s && (force || state.open !== s);
      const box = $('.sb-detail', row), btn = $('.sb-row__main', row);
      if (on && box.hidden) { box.hidden = false; detail(D.coins.find((c) => c.s === s), box); }
      if (!on) { box.hidden = true; box.innerHTML = ''; }
      row.classList.toggle('is-open', on); btn.setAttribute('aria-expanded', String(on));
    });
    state.open = $(`.sb-row.is-open`) ? s : null;
    const q = new URLSearchParams(); if (state.open) q.set('s', state.open); if (state.w !== '24h') q.set('w', state.w);
    history.replaceState(null, '', location.pathname + (q.toString() ? '?' + q : ''));
  }

  // ---------- 이벤트 ----------
  $('#sbRows').addEventListener('click', (ev) => { const b = ev.target.closest('.sb-row__main'); if (b) toggle(b.closest('.sb-row').dataset.s); });
  $$('.sb-seg button').forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.w) state.w = b.dataset.w; if (b.dataset.f) state.f = b.dataset.f;
    $$('.sb-seg button').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.w ? x.dataset.w === state.w : x.dataset.f === state.f)));
    render();
  }));
  $('#sbQuiet').addEventListener('click', (ev) => { if (ev.target.closest('[data-all]')) $('.sb-seg button[data-f="all"]').click(); });
  let rt = 0;
  addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { if (state.open) { const s = state.open; state.open = null; toggle(s, true); } }, 150); });
  new MutationObserver(() => { if (state.open) { const s = state.open; $$('.sb-detail').forEach((b) => { b.hidden = true; }); toggle(s, true); } }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  // ---------- 불러오기 ----------
  const load = async (first) => {
    try {
      const r = await fetch(root.dataset.src + '?t=' + Math.floor(Date.now() / 300000), { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      const doc = await r.json();
      if (!D || doc.at !== D.at) {
        D = doc;
        if (first) {
          const q = new URLSearchParams(location.search);
          if (WK[q.get('w')]) state.w = q.get('w');
          const want = q.get('s');
          if (want && D.coins.some((c) => c.s === want)) { state.open = want; if (!D.coins.find((c) => c.s === want).w[state.w].flags.length) state.f = 'all'; }
          $$('.sb-seg button').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.w ? x.dataset.w === state.w : x.dataset.f === state.f)));
        }
        render();
        if (first && state.open) { const row = $(`.sb-row[data-s="${state.open}"]`); if (row) row.scrollIntoView({ block: 'start' }); }
      }
      $('#sbEmpty').hidden = true;
      if (first && !reduced) $$('.sb-hero, .sb-bar, .sb-row').slice(0, 9).forEach((n, j) => { n.classList.add('sb-rise'); n.style.animationDelay = `${j * 50}ms`; });
    } catch (e) {
      if (!D) $('#sbEmpty').hidden = false;
    }
  };
  load(true);
  setInterval(() => { if (!document.hidden) load(false); }, 5 * 60 * 1000);
}

main();
