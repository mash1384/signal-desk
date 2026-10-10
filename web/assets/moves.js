// 뉴스 영향(/map/): 뉴스 하나 = 카드 한 장 = 문장 한 줄 + 막대 두 개.
// data/moves.json(15분마다)의 움직임 중 그 코인 뉴스와 연결된 것만 카드로, 나머지는 접어 둔다.
// 카드를 누르면 그 코인의 24시간 '실제 vs 시장대로였다면' 차트가 카드 안에서 열린다.
const S = window.SIGNAL || {};
const BASE = S.base || '/';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const NS = 'http://www.w3.org/2000/svg';
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (v, d = 1) => (v == null || !isFinite(v) ? '–' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(d)}%`);
const abs1 = (v) => `${Math.abs(v).toFixed(1)}%`;
const sg = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : '');
const two = (n) => String(n).padStart(2, '0');
const kd = (t) => new Date((t + 9 * 3600) * 1000);
const hm = (t) => { const d = kd(t); return `${two(d.getUTCHours())}:${two(d.getUTCMinutes())}`; };
const el = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
const niceStep = (x) => { const p = Math.pow(10, Math.floor(Math.log10(x))), f = x / p; return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * p; };
const NAME = { BTC: '비트코인', ETH: '이더리움', SOL: '솔라나', XRP: '리플', BNB: 'BNB', DOGE: '도지코인', ADA: '카르다노', LINK: '체인링크', AVAX: '아발란체', SUI: '수이',
  DOT: '폴카닷', LTC: '라이트코인', TRX: '트론', HBAR: '헤데라', TAO: '비트텐서', AAVE: '에이브', UNI: '유니스왑', NEAR: '니어', APT: '앱토스', ONDO: '온도', ENA: '에테나', PEPE: '페페', ZEC: '지캐시', FET: '페치' };

// '오늘 오후 3:12', '어제 밤 11:48' 처럼
function when(t, now) {
  const d = kd(t), n = kd(now);
  const day = Math.round((Date.UTC(n.getUTCFullYear(), n.getUTCMonth(), n.getUTCDate()) - Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())) / 86400000);
  const h = d.getUTCHours(), m = two(d.getUTCMinutes());
  const part = h < 6 ? '새벽' : h < 12 ? '오전' : h < 18 ? '오후' : '밤';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${day === 0 ? '오늘' : day === 1 ? '어제' : `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일`} ${part} ${h12}:${m}`;
}
const verb = (v, past = true) => (v >= 0 ? (past ? '올랐' : '오를') : (past ? '빠졌' : '빠질'));

// 큰 문장: 시장과 비교한 결과만. 작은 줄: 언제부터(뉴스 기준)
function sentence(e) {
  const o = e.size, m = e.market, a = o + m;
  if (Math.abs(m) < 0.3) return `시장은 그대로인데 혼자 ${abs1(o)} ${verb(o)}어요`;
  if (Math.sign(m) === Math.sign(o)) return `시장보다 ${abs1(o)} 더 ${verb(o)}어요`;
  if (Math.sign(a) === Math.sign(m)) return `시장보다 ${abs1(o)} 덜 ${verb(m)}어요`;
  return `시장은 ${verb(m)}는데 오히려 ${abs1(a)} ${verb(a)}어요`;
}
function timing(e) {
  const n = e.news[0], dur = Math.round((e.t1 - e.t0) / 60);
  const lead = !n ? '' : n.lead >= 2 ? `뉴스 ${n.lead}분 뒤부터` : n.lead >= -1 ? '뉴스와 거의 동시에' : `뉴스가 나오기 ${-n.lead}분 전부터`;
  return `${lead} ${dur}분 동안`;
}

function main() {
  const root = $('#im');
  if (!root) return;
  const ICONS = new Set((root.dataset.icons || '').split(','));
  const logo = (s, cls = '') => (ICONS.has(s) ? `<img class="im-logo ${cls}" src="${BASE}assets/coins/${s}.svg" alt="" width="40" height="40">` : `<span class="im-ph ${cls}" aria-hidden="true">${esc(s.slice(0, 1))}</span>`);
  let D = null, bySym = {}, open = null;

  // ---------- 막대 두 개: 시장대로였다면 vs 실제 ----------
  function bars(e, mx) {
    const a = e.size + e.market;
    const W = (v) => Math.max(1.5, (Math.abs(v) / mx) * 100);
    const row = (label, v, cls) => `<div class="im-bar"><span class="im-bar__k">${label}</span><span class="im-bar__track"><i class="im-bar__fill ${cls}" style="width:${W(v)}%"></i></span><span class="im-bar__v ${cls === 'im-b-mk' ? 'im-mk' : sg(v)}">${pct(v)}</span></div>`;
    return row('시장대로였다면', e.market, 'im-b-mk') + row('실제', a, a >= 0 ? 'im-b-up' : 'im-b-down');
  }

  function render() {
    const now = D.at;
    const coins = D.coins;
    bySym = Object.fromEntries(coins.map((c) => [c.s, c]));
    const all = coins.flatMap((c) => c.events.map((e, i) => ({ ...e, sym: c.s, i })));
    const linked = all.filter((e) => e.label === 'likely' || e.label === 'mixed').sort((x, y) => Math.abs(y.size) - Math.abs(x.size));
    const quiet = all.filter((e) => !(e.label === 'likely' || e.label === 'mixed')).sort((x, y) => Math.abs(y.size) - Math.abs(x.size));
    const t = D.tide.total;
    $('#imAsof').textContent = `${when(now, now)} 기준 · 최근 24시간 · 15분마다 갱신`;
    { const nc = new Set(linked.map((e) => e.sym)).size; $('#imTitle').textContent = linked.length ? `오늘 뉴스에 반응한 코인 ${nc}개${linked.length > nc ? ` · 움직임 ${linked.length}번` : ''}` : '오늘은 뉴스로 설명되는 큰 움직임이 없었어요'; }
    $('#imLede').innerHTML = `시장 전체는 24시간 동안 ${Math.abs(t) < 0.5 ? `거의 그대로였어요 <b class="${sg(t)}">${pct(t)}</b>` : `<b class="${sg(t)}">${pct(t)}</b> ${verb(t)}어요`}. 아래 카드는 그 흐름과 다르게, 뉴스 뒤에 혼자 더 움직인 코인입니다.`;

    const mx = Math.max(0.5, ...linked.map((e) => Math.max(Math.abs(e.market), Math.abs(e.size + e.market))));
    $('#imCards').innerHTML = linked.map((e, k) => {
      const n = e.news[0], extra = e.label === 'mixed' ? `<p class="im-card__warn">같은 시간 이 코인 뉴스가 ${e.news.length}건이라 어느 것 때문인지는 확실하지 않아요.</p>` : '';
      return `<li class="im-card" data-k="${k}">
        <div class="im-card__head">${logo(e.sym)}<div class="im-card__id"><b>${esc(NAME[e.sym] || e.sym)}</b><span>${e.sym}</span></div>
          <div class="im-card__num ${sg(e.size)}"><b>${pct(e.size)}</b><span>혼자 움직인 만큼</span></div></div>
        <p class="im-card__say">${esc(sentence(e))}</p><p class="im-card__when">${esc(timing(e))} · 같은 시간 시장 흐름 ${pct(e.market)}</p>
        <div class="im-bars">${bars(e, mx)}</div>
        ${extra}
        <a class="im-card__news" href="${BASE}a/${esc(n.id)}/"><span class="im-card__ntitle">${esc(n.title)}</span><span class="im-card__nmeta">${esc(n.src || '')} · ${when(e.t0 - n.lead * 60, now)}</span></a>
        <button type="button" class="im-card__more" aria-expanded="false" data-k="${k}">${esc(NAME[e.sym] || e.sym)} 24시간 흐름 보기</button>
        <div class="im-card__detail" hidden></div>
      </li>`;
    }).join('');
    root._linked = linked;

    $('#imMoreTitle').textContent = `뉴스 없이 크게 움직인 코인 ${quiet.length}건`;
    $('#imMore').hidden = !quiet.length;
    $('#imQuiet').innerHTML = quiet.slice(0, 30).map((e) => {
      const a = e.size + e.market;
      return `<li>${logo(e.sym, 'im-logo--s')}<span class="im-quiet__id"><b>${esc(NAME[e.sym] || e.sym)}</b><span>${when(e.t0, now)}</span></span>
        <span class="im-quiet__say">${esc(sentence(e))}${e.context && e.context[0] ? `<a class="im-quiet__ctx" href="${BASE}a/${esc(e.context[0].id)}/"><span>참고 · ${Math.round(e.context[0].ago)}시간 전 소식</span>${esc(e.context[0].title)}</a>` : ''}</span>
        <span class="im-quiet__v ${sg(a)}">${pct(a)}</span></li>`;
    }).join('');
    if (!linked.length) $('#imMore').open = true;
    if (open != null && linked[open]) toggle(open, true); else open = null;
  }

  // ---------- 카드 안 24시간 차트 ----------
  function drawDetail(box, e) {
    const c = bySym[e.sym];
    if (!box.firstChild) box.appendChild($('#imDetailTpl').content.cloneNode(true));
    const svg = $('svg', box), hover = $('.im-hover', box);
    svg.innerHTML = '';
    const W = svg.clientWidth, H = svg.clientHeight, M = D.minutes, st = D.step;
    const padL = 2, padR = 44, padT = 10, padB = 22;
    const t = c.t, m = c.m, n0 = t.length - 1;
    let lo = Math.min(0, ...t, ...m), hi = Math.max(0, ...t, ...m);
    const span = hi - lo || 1; lo -= span * 0.1; hi += span * 0.1;
    const XM = (min) => padL + (Math.min(min, M) / M) * (W - padL - padR), X = (k) => XM(k * st), Y = (v) => padT + (1 - (v - lo) / (hi - lo)) * (H - padT - padB);
    const stepV = niceStep((hi - lo) / 3);
    for (let v = Math.ceil(lo / stepV) * stepV; v <= hi; v += stepV) {
      const y = Y(v), zero = Math.abs(v) < 1e-9;
      el('line', { x1: padL, x2: W - padR, y1: y, y2: y, stroke: zero ? 'var(--line-strong)' : 'var(--line)' }, svg);
      const tx = el('text', { x: W - padR + 8, y: y + 4, class: 'im-ax' }, svg); tx.textContent = zero ? '0' : pct(v, stepV < 0.5 ? 1 : 0);
    }
    for (let h = 0; h <= 24; h += W < 480 ? 8 : 6) { const tx = el('text', { x: XM(h * 60), y: H - 4, class: 'im-ax', 'text-anchor': h === 0 ? 'start' : 'middle' }, svg); tx.textContent = h === 24 ? '지금' : hm(D.t0 + h * 3600); }
    el('rect', { x: XM(e.a), y: padT, width: Math.max(3, XM(e.e) - XM(e.a)), height: H - padT - padB, fill: 'color-mix(in oklab, var(--accent) 16%, transparent)' }, svg);
    const line = (s) => s.map((v, k) => `${k ? 'L' : 'M'}${X(k).toFixed(1)} ${Y(v).toFixed(1)}`).join('');
    el('path', { d: line(m), fill: 'none', stroke: 'var(--mkt)', 'stroke-width': 1.5, 'stroke-dasharray': '5 4', 'stroke-linejoin': 'round' }, svg);
    el('path', { d: line(t), fill: 'none', stroke: 'var(--text)', 'stroke-width': 1.75, 'stroke-linejoin': 'round' }, svg);
    const cross = el('g', { opacity: 0 }, svg);
    const cx = el('line', { y1: padT, y2: H - padB, stroke: 'color-mix(in oklab, var(--text) 30%, transparent)' }, cross);
    const ct = el('circle', { r: 3.5, fill: 'var(--text)' }, cross), cm = el('circle', { r: 3, fill: 'var(--mkt)' }, cross);
    $('.im-day', box).innerHTML = `24시간 전체로 보면 실제 <b class="${sg(c.total)}">${pct(c.total)}</b> = 시장대로였다면 <b class="im-mk">${pct(c.market)}</b> + 혼자 움직인 만큼 <b class="${sg(c.own)}">${pct(c.own)}</b>`;
    svg.onpointermove = (ev) => {
      if (ev.pointerType === 'touch') return;
      const r = svg.getBoundingClientRect();
      const k = Math.max(0, Math.min(n0, Math.round(((ev.clientX - r.left - padL) / (W - padL - padR)) * (M / st))));
      const x = X(k);
      cross.setAttribute('opacity', 1); cx.setAttribute('x1', x); cx.setAttribute('x2', x);
      ct.setAttribute('cx', x); ct.setAttribute('cy', Y(t[k])); cm.setAttribute('cx', x); cm.setAttribute('cy', Y(m[k]));
      hover.innerHTML = `<span class="im-t">${hm(D.t0 + k * st * 60)}까지</span><p><span>실제</span><b>${pct(t[k], 2)}</b></p><p><span>시장대로였다면</span><b class="im-mk">${pct(m[k], 2)}</b></p>`;
      hover.hidden = false;
      const w = hover.offsetWidth;
      hover.style.transform = `translate(${Math.round(x + 14 + w > W - padR ? x - 14 - w : x + 14)}px, 0)`;
    };
    svg.onpointerleave = () => { hover.hidden = true; cross.setAttribute('opacity', 0); };
  }
  function toggle(k, force) {
    const cards = $$('#imCards .im-card');
    cards.forEach((li, j) => {
      const on = j === k && (force || open !== k);
      const box = $('.im-card__detail', li), btn = $('.im-card__more', li);
      box.hidden = !on; btn.setAttribute('aria-expanded', String(on)); li.classList.toggle('is-open', on);
      if (on) drawDetail(box, root._linked[j]);
    });
    open = cards[k] && !$('.im-card__detail', cards[k]).hidden ? k : null;
  }
  $('#imCards').addEventListener('click', (ev) => { const b = ev.target.closest('.im-card__more'); if (b) toggle(Number(b.dataset.k)); });
  let rt = 0;
  addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { if (open != null) toggle(open, true); }, 120); });
  new MutationObserver(() => { if (open != null) toggle(open, true); }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  const load = async (first) => {
    try {
      const r = await fetch(root.dataset.src + '?t=' + Math.floor(Date.now() / 300000), { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      const doc = await r.json();
      if (!D || doc.at !== D.at) { D = doc; render(); }
      $('#imEmpty').hidden = true;
      if (first) {
        const want = new URLSearchParams(location.search).get('s');
        const k = want ? root._linked.findIndex((e) => e.sym === want) : -1;
        if (k >= 0) { toggle(k, true); $$('#imCards .im-card')[k].scrollIntoView({ block: 'center' }); }
        if (!reduced) $$('.im-hero, #imCards > li').slice(0, 6).forEach((n, j) => { n.classList.add('im-rise'); n.style.animationDelay = `${j * 70}ms`; });
      }
    } catch (e) {
      if (!D) $('#imEmpty').hidden = false;
    }
  };
  load(true);
  setInterval(() => { if (!document.hidden) load(false); }, 5 * 60 * 1000);
}

main();
