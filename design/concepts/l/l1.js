// L1 · Stream — 시간축을 따라 흐르는 목록 + 오른쪽 고정 상세(데스크톱). 위에 24시간 막대(눌러서 시간대 고르기)
import { store, start, day, counts, T, esc, line, pill, bars, chips, outlets, hm, drawHist, detailHTML, fillRx, openSheet, segHTML, L } from './lk.js?v=1017162450';

const app = document.getElementById('app');
app.innerHTML = `<div class="wrap l1">
  <section class="top"><div><h1 data-x="title"></h1><p class="sub"><span class="livedot"></span><span id="upd"></span></p></div>
    <div class="kpi" id="kpi"></div></section>
  <section class="histc"><canvas id="hist"></canvas><div class="hl"><span id="h0"></span><span id="hsel"></span><span id="h1"></span></div></section>
  <section class="fl"><div class="seg" id="seg"></div><div class="seg" id="vf"></div><label class="tg"><input type="checkbox" id="strong"><span></span></label></section>
  <section class="cols"><div class="list" id="list"></div><aside class="side"><div class="det card" id="side"></div></aside></section></div>`;
const S = { th: 'all', v: 'all', strong: false, hour: null, sel: null };
const wide = () => innerWidth >= 1100;
const $ = (id) => document.getElementById(id);
function filtered() {
  const now = Date.now() / 1000; return day().filter((x) => (S.th === 'all' || x.th.includes(S.th)) && (S.v === 'all' || x.v === S.v) && (!S.strong || x.s >= 2)
    && (S.hour == null || Math.floor((x.t - (now - 86400)) / 3600) === S.hour));
}
function render() {
  const xs = day(), c = counts(xs);
  app.querySelector('[data-x="title"]').textContent = T('Live signals', '실시간 신호');
  $('upd').textContent = T(`Updated ${new Date().toLocaleTimeString('en-GB')} · refreshes every 30s`, `${new Date().toLocaleTimeString('ko-KR')} 갱신 · 30초마다 새로고침`);
  $('kpi').innerHTML = `<div><b class="mono">${c.n}</b><span>${T('stories · 24h', '건 · 24시간')}</span></div><div><b class="mono up">${c.u}</b><span>${T('bullish', '호재')}</span></div><div><b class="mono down">${c.d}</b><span>${T('bearish', '악재')}</span></div>`;
  $('seg').innerHTML = segHTML(S.th, xs);
  $('vf').innerHTML = [['all', T('All', '전체')], ['호재', T('Bullish', '호재')], ['악재', T('Bearish', '악재')]].map(([k, n]) => `<button type="button" data-v="${k}" aria-pressed="${S.v === k}">${n}</button>`).join('');
  app.querySelector('.tg span').textContent = T('Strong only', '센 소식만');
  drawHist($('hist'), xs.filter((x) => S.th === 'all' || x.th.includes(S.th)), { sel: S.hour });
  $('h0').textContent = T('24h ago', '24시간 전'); $('h1').textContent = T('Now', '지금');
  $('hsel').innerHTML = S.hour == null ? T('Tap the bars to pick an hour', '막대를 눌러 시간대를 골라요') : `${hm(Date.now() / 1000 - 86400 + S.hour * 3600)}–${hm(Date.now() / 1000 - 86400 + (S.hour + 1) * 3600)} · <button type="button" id="hclr">${T('Clear', '해제')}</button>`;
  const ys = filtered(); let lastH = '';
  $('list').innerHTML = ys.length ? ys.map((it) => { const hh = hm(it.t).slice(0, 2) + ':00', head = hh !== lastH ? `<p class="hh mono">${hh}</p>` : ''; lastH = hh;
    return `${head}<button type="button" class="row ${store.fresh.has(it.id) ? 'new-in' : ''} ${S.sel === it.id ? 'on' : ''}" data-id="${it.id}"><span class="tm mono">${hm(it.t)}</span><span class="dot ${it.v === '호재' ? 'u' : it.v === '악재' ? 'd' : ''}"></span>
      <span class="bd"><span class="ln">${esc(line(it))}</span><span class="mt">${pill(it.v)}${bars(it)}${chips(it)}<span class="ou">${outlets(it)}</span></span></span></button>`; }).join('') : `<p class="empty">${T('Nothing here for this filter.', '이 조건의 소식이 없어요.')}</p>`;
  if (wide()) { if (!S.sel || !ys.find((x) => x.id === S.sel)) S.sel = (ys.find((x) => x.s >= 2) || ys[0] || {}).id; showSide(); }
}
function showSide() { const it = store.byId.get(S.sel), side = $('side'); if (!it) { side.innerHTML = ''; return; }
  if (side.dataset.id !== it.id || side.dataset.l !== DFI.lang()) { side.dataset.id = it.id; side.dataset.l = DFI.lang(); side.innerHTML = detailHTML(it); fillRx(it, side); }
  app.querySelectorAll('.row').forEach((r) => r.classList.toggle('on', r.dataset.id === S.sel)); }
app.addEventListener('click', (e) => {
  const b = e.target.closest('[data-th]'); if (b) { S.th = b.dataset.th; render(); return; }
  const v = e.target.closest('[data-v]'); if (v) { S.v = v.dataset.v; render(); return; }
  if (e.target.id === 'hclr') { S.hour = null; render(); return; }
  const r = e.target.closest('.row'); if (r) { S.sel = r.dataset.id; if (wide()) showSide(); else openSheet(store.byId.get(r.dataset.id)); }
});
$('strong').addEventListener('change', (e) => { S.strong = e.target.checked; render(); });
$('hist').addEventListener('click', (e) => { const rc = e.target.getBoundingClientRect(), h = Math.floor((e.clientX - rc.left) / rc.width * 24); S.hour = S.hour === h ? null : Math.max(0, Math.min(23, h)); render(); });
addEventListener('resize', () => drawHist($('hist'), day().filter((x) => S.th === 'all' || x.th.includes(S.th)), { sel: S.hour }));
start(render);
