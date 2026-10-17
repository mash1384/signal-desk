// R2 · Terminal — Linear 받은편지함·프로 데스크톱 앱 참고. 왼쪽: 보기·테마·코인 거르기(개수와 균형 막대), 가운데: 촘촘한 한 줄 목록(↑↓·J/K로 이동, / 로 검색),
// 오른쪽: 상세. 아래 상태 줄. 모바일은 목록 + 아래에서 올라오는 상세, 거르기는 위쪽 가로 칩.
import { store, start, day, counts, T, esc, line, pill, bars, chips, outlets, hm, ago, openSheet, THEMES, thName, pxChip, fillPx, newGate, detailHTML, fillRx } from './lk.js?v=1017215516';

const app = document.getElementById('app');
app.innerHTML = `<div class="r2"><aside class="side" id="side" aria-label="Filters"></aside>
  <section class="mid"><div class="bar"><label class="srch"><span aria-hidden="true">⌕</span><input id="q" type="search" autocomplete="off"><kbd>/</kbd></label></div>
    <button type="button" class="newpill" id="np"></button><ul class="lst" id="lst" role="listbox" tabindex="0"><li><div class="skel"></div></li><li><div class="skel"></div></li></ul>
    <p class="status mono" id="st"></p></section>
  <section class="det-pane"><div class="det" id="dp"></div></section></div>`;
const $ = (id) => document.getElementById(id), S = { view: 'all', th: 'all', coin: null, q: '', sel: null };
const gate = newGate($('np'), () => render(true));
const wide = () => innerWidth >= 1100;
function list() {
  const q = S.q.trim().toLowerCase();
  return day().filter((x) => gate.visible(x) && (S.th === 'all' || x.th.includes(S.th)) && (!S.coin || (x.coins || []).includes(S.coin))
    && (S.view === 'all' || (S.view === 'strong' ? x.s >= 2 : x.v === S.view)) && (!q || (x.ko + ' ' + (x.en || '') + ' ' + (x.coins || []).join(' ')).toLowerCase().includes(q)));
}
function side(xs) {
  const now = Date.now() / 1000, cc = {}; xs.filter((x) => now - x.t < 6 * 3600).forEach((x) => (x.coins || []).forEach((c) => { cc[c] = (cc[c] || 0) + 1; }));
  const coins = Object.entries(cc).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const it = (attr, key, label, n, extra = '') => `<button type="button" class="f" ${attr}="${key}" aria-pressed="${(attr === 'data-th' ? S.th : attr === 'data-view' ? S.view : S.coin) === key}"><span>${label}</span>${extra}<span class="n mono">${n}</span></button>`;
  const bal = (ys) => { const c = counts(ys), t = Math.max(1, c.u + c.d); return `<span class="mb" aria-hidden="true"><i class="u" style="width:${c.u / t * 100}%"></i><i class="d" style="width:${c.d / t * 100}%"></i></span>`; };
  $('side').innerHTML = `<p class="lbl">${T('Views', '보기')}</p>${it('data-view', 'all', T('All stories', '모든 소식'), xs.length)}${it('data-view', 'strong', T('Strong only', '센 소식'), xs.filter((x) => x.s >= 2).length)}${it('data-view', '호재', T('Bullish', '호재'), counts(xs).u)}${it('data-view', '악재', T('Bearish', '악재'), counts(xs).d)}
    <p class="lbl">${T('Themes', '테마')}</p>${THEMES.map((t) => { const ys = t.k === 'all' ? xs : xs.filter((x) => x.th.includes(t.k)); return it('data-th', t.k, t[DFI.lang() === 'ko' ? 'ko' : 'en'], ys.length, bal(ys)); }).join('')}
    <p class="lbl">${T('Coins · 6h', '코인 · 6시간')}</p>${coins.map(([c, n]) => it('data-coin', c, `<span class="mono">${c}</span>`, n)).join('') || `<p class="mute">–</p>`}`;
}
function render(force) {
  const all = day(); if (!force && !gate.check()) return; const xs = all.filter((x) => gate.visible(x)), ys = list();
  side(xs);
  $('q').placeholder = T('Search stories, coins…', '소식·코인 검색…');
  $('lst').innerHTML = ys.map((it) => `<li role="option" aria-selected="${S.sel === it.id}" data-id="${it.id}" class="${store.fresh.has(it.id) ? 'new-in' : ''}"><span class="vg ${it.v === '호재' ? 'up' : it.v === '악재' ? 'down' : ''}" aria-label="${DFI.v(it.v)}">${it.v === '호재' ? '▲' : it.v === '악재' ? '▼' : '•'}</span>
    <span class="ln">${esc(line(it))}</span><span class="mt">${it.s >= 2 ? bars(it) : ''}${pxChip(it)}${(it.n || 1) > 1 ? `<span class="ou">${outlets(it)}</span>` : ''}<span class="tm mono">${hm(it.t)}</span></span></li>`).join('') || `<li class="empty">${S.q ? T(`No stories match “${esc(S.q)}”.`, `“${esc(S.q)}”에 맞는 소식이 없어요.`) : T('No stories for this filter.', '이 조건의 소식이 없어요.')}</li>`;
  fillPx($('lst'));
  const c = counts(ys); $('st').innerHTML = `<span class="livedot"></span> ${T('Live', '실시간')} · ${ys.length} ${T('shown', '건 표시')} · <span class="up">${c.u}▲</span> <span class="down">${c.d}▼</span> · ${T('↑↓ or J/K to move · / to search', '↑↓·J/K 이동 · / 검색')}`;
  if (wide()) { if (!S.sel || !ys.some((x) => x.id === S.sel)) S.sel = ys[0] && ys[0].id; select(S.sel, false); }
}
function select(id, scroll = true) {
  S.sel = id; app.querySelectorAll('#lst [role=option]').forEach((li) => li.setAttribute('aria-selected', String(li.dataset.id === id)));
  const li = app.querySelector(`#lst [data-id="${id}"]`); if (scroll && li) li.scrollIntoView({ block: 'nearest' });
  const it = store.byId.get(id); if (!it) return;
  if (wide()) { const dp = $('dp'); if (dp.dataset.id !== id || dp.dataset.l !== DFI.lang()) { dp.dataset.id = id; dp.dataset.l = DFI.lang(); dp.innerHTML = detailHTML(it); fillRx(it, dp); } } else if (scroll === 'open') openSheet(it);
}
app.addEventListener('click', (e) => {
  const f = e.target.closest('.f'); if (f) { if (f.dataset.th) S.th = f.dataset.th; if (f.dataset.view) S.view = f.dataset.view; if (f.dataset.coin) S.coin = S.coin === f.dataset.coin ? null : f.dataset.coin; render(true); return; }
  const li = e.target.closest('#lst [data-id]'); if (li) select(li.dataset.id, wide() ? false : 'open');
});
$('q').addEventListener('input', (e) => { S.q = e.target.value; render(true); });
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') { if (e.key === 'Escape') { e.target.blur(); } if (e.key === 'ArrowDown') { e.preventDefault(); e.target.blur(); move(1); } return; }
  if (e.key === '/') { e.preventDefault(); $('q').focus(); return; }
  if (['ArrowDown', 'j', 'J'].includes(e.key)) { e.preventDefault(); move(1); } else if (['ArrowUp', 'k', 'K'].includes(e.key)) { e.preventDefault(); move(-1); } else if (e.key === 'Enter' && !wide() && S.sel) openSheet(store.byId.get(S.sel));
});
function move(d) { const ids = [...app.querySelectorAll('#lst [data-id]')].map((x) => x.dataset.id); if (!ids.length) return; const i = Math.max(0, Math.min(ids.length - 1, ids.indexOf(S.sel) + d)); select(ids[i] || ids[0]); }
start(() => render(false)); DFI.onLang(() => render(true));
