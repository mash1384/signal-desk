// L2 · Board — 테마 다섯 칸(크립토·나스닥·경제·AI·세계)이 나란히 실시간으로 흐른다. 칸 머리에 24시간 호재·악재 균형.
// 맨 위 '지금 가장 센 소식' 한 줄. 모바일은 칸을 옆으로 넘긴다(탭과 함께).
import { store, start, day, counts, T, esc, line, pill, bars, chips, outlets, hm, ago, openSheet, THEMES, thName } from './lk.js?v=1017224009';

const app = document.getElementById('app'), COLS = THEMES.filter((t) => t.k !== 'all').map((t) => t.k);
app.innerHTML = `<div class="wrap l2"><section class="top"><div><h1 data-x="t"></h1><p class="sub"><span class="livedot"></span><span id="upd"></span></p></div><div class="kpi" id="kpi"></div></section>
  <button type="button" class="hero" id="hero"></button>
  <nav class="ctabs" id="ctabs"></nav><section class="board" id="board">${COLS.map((k) => `<div class="col" data-k="${k}"><header></header><div class="items"></div></div>`).join('')}</section></div>`;
const $ = (id) => document.getElementById(id);
const balance = (c) => { const t = Math.max(1, c.u + c.d); return `<div class="bal"><i class="u" style="width:${c.u / t * 100}%"></i><i class="d" style="width:${c.d / t * 100}%"></i></div>`; };
function card(it) {
  return `<button type="button" class="it ${store.fresh.has(it.id) ? 'new-in' : ''} ${it.v === '호재' ? 'vu' : it.v === '악재' ? 'vd' : ''}" data-id="${it.id}"><span class="m">${pill(it.v)}${bars(it)}<span class="tm mono">${hm(it.t)}</span></span>
    <span class="ln">${esc(line(it))}</span><span class="f">${chips(it, 2)}<span class="ou">${outlets(it)}</span></span></button>`;
}
function render() {
  const xs = day(), c = counts(xs);
  app.querySelector('[data-x="t"]').textContent = T('Live board', '실시간 보드');
  $('upd').textContent = T(`Live · ${new Date().toLocaleTimeString('en-GB')}`, `실시간 · ${new Date().toLocaleTimeString('ko-KR')}`);
  $('kpi').innerHTML = `<span class="mono">${c.n}</span> ${T('stories in 24h', '건 · 24시간')} · <span class="mono up">${c.u}</span> ${T('bullish', '호재')} · <span class="mono down">${c.d}</span> ${T('bearish', '악재')}`;
  const top = xs.filter((x) => x.t > Date.now() / 1000 - 6 * 3600).sort((a, b) => (b.s * 3 + (b.n || 1)) - (a.s * 3 + (a.n || 1)) || b.t - a.t)[0];
  $('hero').dataset.id = top ? top.id : ''; $('hero').innerHTML = top ? `<span class="k">${T('Biggest in the last 6 hours', '최근 6시간 가장 큰 소식')}</span><span class="ln">${esc(line(top))}</span><span class="m">${pill(top.v)}${bars(top)}${chips(top, 3)}<span class="ou">${ago(top.t)} · ${outlets(top)}</span></span>` : '';
  $('ctabs').innerHTML = COLS.map((k, i) => `<button type="button" data-go="${i}">${thName(k)}</button>`).join('');
  COLS.forEach((k) => { const col = app.querySelector(`.col[data-k="${k}"]`), ys = xs.filter((x) => x.th.includes(k)), cc = counts(ys);
    col.querySelector('header').innerHTML = `<div class="h"><b>${thName(k)}</b><span class="mono">${cc.n}</span></div>${balance(cc)}<p class="bn"><span class="up">${cc.u}↑</span> <span class="down">${cc.d}↓</span></p>`;
    col.querySelector('.items').innerHTML = ys.slice(0, 60).map(card).join('') || `<p class="empty">–</p>`; });
}
app.addEventListener('click', (e) => { const b = e.target.closest('[data-id]'); if (b && b.dataset.id) { openSheet(store.byId.get(b.dataset.id)); return; }
  const g = e.target.closest('[data-go]'); if (g) { const col = app.querySelectorAll('.col')[+g.dataset.go]; $('board').scrollTo({ left: col.offsetLeft - 16, behavior: 'smooth' }); } });
$('board').addEventListener('scroll', () => { const i = Math.round($('board').scrollLeft / (app.querySelector('.col').offsetWidth + 12)); app.querySelectorAll('[data-go]').forEach((b, j) => b.setAttribute('aria-pressed', String(j === i))); }, { passive: true });
start(render);
