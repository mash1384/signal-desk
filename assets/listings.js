// 상장 레이더: 아무것도 모르는 사람도 바로 알 수 있게 메시지 하나 — '새로 상장된 코인, 따라 사면 대부분 손해'.
// data/listings.json(업비트 원화 상장 기록)으로 브라우저에서 계산한다. 진행 중 상장은 Worker 프록시로 30초마다 이어 그린다.
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (v, d = 1) => { if (v == null || !isFinite(v)) return '–'; const r = +v.toFixed(d); return (r > 0 ? '+' : r < 0 ? '−' : '') + Math.abs(r).toFixed(d) + '%'; };
const nowSec = () => Math.floor(Date.now() / 1000);
const kst = (t) => new Date((t + 9 * 3600) * 1000);
const md = (t) => { const d = kst(t); return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일`; };
const hm = (t) => { const d = kst(t); return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`; };
const dur = (m) => { m = Math.max(0, Math.round(m)); const h = Math.floor(m / 60), mm = m % 60; return (h ? h + '시간' : '') + (mm ? (h ? ' ' : '') + mm + '분' : (h ? '' : '0분')); };
const median = (a) => { const s = a.slice().sort((x, y) => x - y), n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : null; };
const quant = (a, q) => { const s = a.slice().sort((x, y) => x - y); return s[Math.floor(q * (s.length - 1))]; };

const FEE = 0.1;                                   // 업비트 원화 왕복 수수료 %(0.05%×2)
const WHEN = [[1, '1분 뒤'], [10, '10분 뒤'], [60, '1시간 뒤'], [180, '3시간 뒤']];
const KIND = { listing: '신규 상장', caution: '유의 종목', delisting: '거래지원 종료' };

const root = $('#lr');
if (root) main();

function main() {
  const proxy = root.dataset.proxy || '';
  let data = null, L = [], k = 10, shown = 20, liveCurves = {};
  const newUids = new Set();
  const at = (l, o) => { const v = l.tcm.get(o); return v == null ? null : v; };
  // 거래 시작 o분 뒤에 사서 h분 뒤 판 수익(수수료 포함)
  const ret = (l, o, h) => { const a = at(l, o), b = at(l, h); return a == null || b == null ? null : ((1 + b / 100) / (1 + a / 100) - 1) * 100 - FEE; };
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------- 지금 상장 중 ----------
  function live() {
    const box = $('#lrLive');
    const xs = data.listings.filter((x) => x.live);
    if (!xs.length) {
      const last = data.listings.find((x) => x.tc);
      box.innerHTML = last ? `<p class="lr-idle">지금 진행 중인 상장은 없어요 · 가장 최근 상장은 <b>${esc(last.sym)}</b>(${md(last.trade_ts || last.notice_ts)})</p>` : '';
      return;
    }
    const pk = median(L.map((l) => l.m.peak_min).filter((v) => v != null));
    box.innerHTML = xs.map((x) => {
      const pts = liveCurves[x.sym] || x.tc || [];
      const started = x.trade_ts && x.trade_ts <= nowSec();
      if (!started) {
        return `<article class="lr-live"><p class="lr-live__tag"><i></i>곧 거래 시작</p>
          <h2 class="lr-live__t">${esc(x.sym)} · ${x.trade_ts ? `${hm(x.trade_ts)} 거래 시작 예정 (${dur((x.trade_ts - nowSec()) / 60)} 남음)` : '거래 시작 시각 확인 중'}</h2>
          <p class="lr-live__say">지난 상장 코인은 거래가 시작되면 <b>보통 ${dur(pk)} 만에 최고점</b>을 찍고 내려왔어요. 따라 사기 전에 아래 기록을 먼저 보세요.</p></article>`;
      }
      const last = pts.length ? pts[pts.length - 1] : null, peak = pts.length ? Math.max(...pts.map((p) => p[1])) : null;
      const t10 = new Map(pts).get(10), f10 = last && t10 != null ? ((1 + last[1] / 100) / (1 + t10 / 100) - 1) * 100 - FEE : null;
      return `<article class="lr-live"><p class="lr-live__tag"><i></i>지금 상장 중</p>
        <h2 class="lr-live__t">${esc(x.sym)} · 거래 시작 ${dur((nowSec() - x.trade_ts) / 60)}째</h2>
        <dl class="lr-live__row"><div><dt>시작가 대비 최고</dt><dd class="up">${pct(peak)}</dd></div><div><dt>시작가 대비 지금</dt><dd class="${last && last[1] < 0 ? 'down' : 'up'}">${last ? pct(last[1]) : '–'}</dd></div></dl>
        ${f10 == null ? '' : `<p class="lr-live__say">거래 시작 10분 뒤에 샀다면 지금 <b class="${f10 >= 0 ? 'up' : 'down'}">${pct(f10)}</b>예요. 지난 상장 코인은 이 시점부터 하루가 될 때까지 <b>보통 더 내렸어요.</b></p>`}</article>`;
    }).join('');
  }
  async function pollLive() {
    if (!proxy) return;
    const xs = data.listings.filter((x) => x.live && x.trade_ts && x.trade_ts <= nowSec() && x.tbase);
    for (const x of xs) {
      try {
        const res = await fetch(`${proxy}/upbit-candles?market=KRW-${encodeURIComponent(x.sym)}&count=200`);
        if (!res.ok) continue;
        const rows = await res.json();
        const by = new Map((x.tc || []).map(([o, v]) => [o, v]));
        rows.forEach((r) => {
          const off = Math.round((Date.parse(r.candle_date_time_utc + 'Z') / 1000 - x.trade_ts) / 60);
          if (off >= 0 && off <= 1440) by.set(off, (r.trade_price / x.tbase - 1) * 100);
        });
        liveCurves[x.sym] = [...by.entries()].sort((a, b) => a[0] - b[0]);
      } catch (e) {}
    }
    live();
  }

  // ---------- 핵심: 따라 사면 ----------
  function key() {
    const rs = L.map((l) => ret(l, k, 1440)).filter((v) => v != null);
    const lossN = Math.round(rs.filter((v) => v <= 0).length / rs.length * 100);
    $('#lrWhen').innerHTML = WHEN.map(([o, t]) => `<button type="button" role="radio" data-k="${o}" aria-checked="${o === k}">거래 시작 ${t}</button>`).join('');
    $('#lrLoss').textContent = lossN;
    const dots = $('#lrDots');
    dots.setAttribute('aria-label', `100명 중 ${lossN}명 손해, ${100 - lossN}명 이익`);
    dots.innerHTML = Array.from({ length: 100 }, (_, i) => `<i class="${i >= lossN ? 'is-win' : ''}"></i>`).join('');
    const w = WHEN.find((x) => x[0] === k)[1];
    $('#lrSay').innerHTML = `거래가 시작되고 <b>${w}</b>에 사서 하루 들고 있었다면, 100명 중 <b>${lossN}명이 손해</b>를 봤어요. 가운데 값은 <b class="down">${pct(median(rs))}</b>예요.`;
  }
  $('#lrWhen').addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; k = +b.dataset.k; key(); path(); });

  // ---------- 따라 산 뒤 보통 흐름(산 가격 = 0) ----------
  function path() {
    const svg = $('#lrPath'), W = svg.clientWidth, H = svg.clientHeight;
    if (W < 100) return;
    const offs = [...new Set(L.flatMap((l) => [...l.tcm.keys()]))].filter((o) => o >= k && o <= 1440).sort((a, b) => a - b);
    const P = offs.map((o) => { const v = L.map((l) => { const r = ret(l, k, o); return r == null ? null : r + FEE; }).filter((x) => x != null); return { o, m: median(v), lo: quant(v, 0.25), hi: quant(v, 0.75), n: v.length }; }).filter((p) => p.n >= 30);
    if (!P.length) return;
    const m = { l: 6, r: 10, t: 24, b: 22 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
    const span = 1440 - k, xs = (o) => m.l + Math.sqrt((o - k) / span) * iw;   // 처음이 중요해 가로축은 제곱근
    const lo = Math.min(0, ...P.map((p) => p.lo)) - 2, hi = Math.max(0, ...P.map((p) => p.hi)) + 2;
    const ys = (v) => m.t + (1 - (v - lo) / (hi - lo)) * ih;
    const line = 'M' + P.map((p) => `${xs(p.o).toFixed(1)},${ys(p.m).toFixed(1)}`).join('L');
    const area = 'M' + P.map((p) => `${xs(p.o).toFixed(1)},${ys(p.hi).toFixed(1)}`).join('L') + 'L' + P.slice().reverse().map((p) => `${xs(p.o).toFixed(1)},${ys(p.lo).toFixed(1)}`).join('L') + 'Z';
    const end = P[P.length - 1], one = P.find((p) => p.o >= k + 60) || end;
    const pin = (p, txt) => `<circle class="pin ${p.m < 0 ? 'is-low' : ''}" cx="${xs(p.o)}" cy="${ys(p.m)}" r="4.5"/><text class="lab" x="${Math.min(W - 92, xs(p.o) - 24)}" y="${ys(p.m) + 20}">${txt}</text>`;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.innerHTML = `<path class="band" d="${area}"/><line class="zero" x1="${m.l}" x2="${m.l + iw}" y1="${ys(0)}" y2="${ys(0)}"/>
      <text class="ax" x="${m.l}" y="${ys(0) - 8}">산 가격</text><path class="med" d="${line}"/>${pin(one, '1시간 뒤 ' + pct(one.m, 0))}${pin(end, '하루 뒤 ' + pct(end.m, 0))}
      ${[[k, '샀을 때'], [k + 60, '+1시간'], [k + 360, '+6시간'], [1440, '하루 뒤']].filter(([o]) => o <= 1440).map(([o, t]) => `<text class="ax" x="${xs(o)}" y="${H - 4}" text-anchor="${o === k ? 'start' : o === 1440 ? 'end' : 'middle'}">${t}</text>`).join('')}`;
    const w = WHEN.find((x) => x[0] === k)[1];
    $('#lrPathSub').textContent = `거래 시작 ${w}에 산 가격을 0으로 놓고, 지난 상장 ${L.length}건의 가운데 값을 이었어요. 옅은 띠는 절반이 지나간 범위예요.`;
    const pk = L.map((l) => l.m.peak_min).filter((v) => v != null), dd = L.map((l) => l.m.dd_from_peak).filter((v) => v != null);
    $('#lrSteps').innerHTML = `<li><span>거래가 시작되면 <b>보통 ${dur(median(pk))} 만에 최고점</b>을 찍어요. 소식을 듣고 들어갈 때쯤엔 이미 지나 있어요.</span></li>
      <li><span>그 뒤로는 내려와요. <b>하루 뒤엔 최고점보다 ${pct(median(dd), 0)}</b>였어요.</span></li>
      <li><span>그래서 따라 사면 <b>대부분 비싸게 사게 돼요.</b></span></li>`;
  }

  // ---------- 최근 상장 ----------
  function recent() {
    const rows = L.slice().sort((a, b) => b.trade_ts - a.trade_ts).slice(0, 10);
    $('#lrRecent').innerHTML = rows.map((l) => {
      const r = ret(l, 10, 1440);
      return `<li><span class="c">${esc(l.sym)}<small>${md(l.trade_ts)} 상장</small></span><span class="m">시작가 대비 최고 ${pct(l.m.peak24, 0)}</span>
        <span class="r ${r > 0 ? 'up' : 'down'}">${r == null ? '–' : pct(r)}<small>${r == null ? '' : r > 0 ? '이익' : '손해'}</small></span></li>`;
    }).join('');
  }

  // ---------- 업비트 공지(접어 둠) ----------
  function notices() {
    const list = data.notices;
    $('#lrNotices').innerHTML = list.slice(0, shown).map((n) => `<li><time>${md(n.ts)} ${hm(n.ts)}</time>
      <span class="lr-kind lr-kind--${esc(n.kind)}">${KIND[n.kind] || esc(n.kind)}</span>${newUids.has(String(n.uid)) ? '<span class="lr-new">NEW</span>' : ''}
      <a href="https://upbit.com/service_center/notice?id=${esc(n.uid)}" target="_blank" rel="noopener">${esc(n.title)}</a></li>`).join('');
    $('#lrMore').hidden = list.length <= shown;
  }
  $('#lrMore').addEventListener('click', () => { shown += 50; notices(); });
  async function pollNotices() {
    if (!proxy) return;
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
        data.notices.unshift({ uid, ts: Date.parse(n.first_listed_at || n.listed_at) / 1000, title: t, kind });
        newUids.add(uid);
      });
      if (newUids.size) notices();
    } catch (e) {}
  }

  (async () => {
    try {
      data = await (await fetch(root.dataset.src + '?t=' + Math.floor(Date.now() / 60000), { cache: 'no-store' })).json();
    } catch (e) {
      $('#lrSay').textContent = '상장 기록을 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.';
      return;
    }
    L = data.listings.filter((l) => l.tc && !l.live && l.m && !l.stable).map((l) => ({ ...l, tcm: new Map(l.tc) }));
    $('#lrN').textContent = L.length;
    live(); key(); path(); recent(); notices();
    let raf; new ResizeObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(path); }).observe($('#lrPath'));
    pollLive();
    setInterval(() => { if (!document.hidden) pollLive(); }, 30000);
    setInterval(() => { if (!document.hidden) pollNotices(); }, 60000);
    if (reduced()) root.classList.add('is-static');
  })();
}
