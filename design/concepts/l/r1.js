// R1 · River — Followin·코인니스·Techmeme 참고. 테마 탭(위에 고정) → '지금 꼭 볼 소식' 3장 → 시간별로 흐르는 목록(소식 이후 가격 칩·몇 곳 보도)
// 오른쪽 고정 칸: 시세, 지금 많이 언급되는 코인, 테마별 24시간 균형. 새 소식은 'N개 새 소식' 버튼으로(읽던 자리가 밀리지 않게).
import { store, start, day, counts, T, esc, line, pill, bars, chips, outlets, hm, ago, openSheet, THEMES, thName, pxChip, fillPx, newGate, loadK5, PRICED_ALL } from './lk.js?v=1017145910';

const app = document.getElementById('app');
app.innerHTML = `<div class="tabsbar"><div class="wrap"><div class="tt" id="tt" role="tablist"></div><p class="upd"><span class="livedot"></span><span id="upd"></span></p></div></div>
<div class="wrap r1"><section class="must" aria-labelledby="mh"><h2 id="mh" class="sec"></h2><div class="mc" id="must"><div class="skel"></div><div class="skel"></div><div class="skel"></div></div></section>
  <section class="cols"><div><h2 class="sec" id="rh"></h2><button type="button" class="newpill" id="np"></button><ol class="river" id="river"><li><div class="skel"></div></li><li><div class="skel"></div></li></ol></div>
  <aside class="rail"><div class="box" id="mk"></div><div class="box" id="mv"></div><div class="box" id="bl"></div></aside></section></div>`;
const S = { th: 'all' }, $ = (id) => document.getElementById(id);
const gate = newGate($('np'), () => render(true));
const score = (x) => x.s * 3 + Math.min(x.n || 1, 4) * 1.5 + (x.v !== '중립' ? 1 : 0);
function row(it) {
  return `<li><button type="button" class="it ${store.fresh.has(it.id) ? 'new-in' : ''}" data-id="${it.id}"><span class="tm mono">${hm(it.t)}</span>
    <span class="bd"><span class="ln">${esc(line(it))}</span><span class="mt">${pill(it.v)}${bars(it)}${pxChip(it)}${chips(it, 2, true)}<span class="ou">${outlets(it)}</span></span></span></button></li>`;
}
async function rail(xs) {
  // 시세(24시간)
  const syms = ['BTC', 'ETH', 'SOL', 'XRP'];
  DFD.prices(syms).then((p) => { $('mk').innerHTML = `<h3>${T('Markets · 24h', '시세 · 24시간')}</h3>` + syms.map((s) => p[s] ? `<p class="q"><b>${s}</b><span class="mono">${DFD.money(p[s].p)}</span><span class="mono ${p[s].c >= 0 ? 'up' : 'down'}">${DFD.pct(p[s].c)}</span></p>` : '').join(''); }).catch(() => {});
  // 지금 많이 언급되는 코인(3시간)
  const now = Date.now() / 1000, cnt = {}; xs.filter((x) => now - x.t < 3 * 3600).forEach((x) => (x.coins || []).forEach((c) => { cnt[c] = (cnt[c] || 0) + 1; }));
  const top = Object.entries(cnt).sort((a, b) => b[1] - a[1]).slice(0, 6);
  $('mv').innerHTML = `<h3>${T('Most mentioned · 3h · price change', '많이 언급된 코인 · 3시간 · 가격 변화')}</h3>` + (top.length ? top.map(([c, n]) => `<p class="q"><b>${c}</b><span class="mono">${n}${T(' stories', '건')}</span><span class="pxc" data-px="${c}|${now - 3 * 3600}">${c}</span></p>`).join('') : `<p class="mute">–</p>`);
  fillPx($('mv'));
  // 테마별 균형
  $('bl').innerHTML = `<h3>${T('Balance · 24h', '호재·악재 · 24시간')}</h3>` + THEMES.filter((t) => t.k !== 'all').map((t) => { const c = counts(xs.filter((x) => x.th.includes(t.k))), tot = Math.max(1, c.u + c.d);
    return `<p class="bal"><span>${thName(t.k)}</span><span class="b"><i class="u" style="width:${c.u / tot * 100}%"></i><i class="d" style="width:${c.d / tot * 100}%"></i></span><span class="mono"><em class="up">${c.u}</em>·<em class="down">${c.d}</em></span></p>`; }).join('');
}
let railAt = 0;
function render(force) {
  const all = day(); if (!force && !gate.check()) { tabs(all); return; }
  const xs = all.filter((x) => gate.visible(x)), ys = xs.filter((x) => S.th === 'all' || x.th.includes(S.th));
  tabs(xs);
  $('upd').textContent = T(`Live · ${new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`, `실시간 · ${new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}`);
  $('mh').textContent = T('Must-read now', '지금 꼭 볼 소식'); $('rh').textContent = T('All stories', '모든 소식');
  const must = ys.filter((x) => x.t > Date.now() / 1000 - 3 * 3600).sort((a, b) => score(b) - score(a)).slice(0, 3);
  $('must').innerHTML = must.map((it) => `<button type="button" class="card btnp" data-id="${it.id}"><span class="mt">${pill(it.v)}${bars(it)}<span class="ou">${ago(it.t)}</span></span><span class="ln">${esc(line(it))}</span><span class="mt">${pxChip(it)}${chips(it, 2, true)}<span class="ou">${outlets(it)}</span></span></button>`).join('') || `<p class="mute">${T('Quiet for the last 3 hours.', '최근 3시간은 조용했어요.')}</p>`;
  let lastH = '';
  $('river').innerHTML = ys.map((it) => { const hh = hm(it.t).slice(0, 2), head = hh !== lastH ? `<li class="hh mono" aria-hidden="true">${hh}:00</li>` : ''; lastH = hh; return head + row(it); }).join('') || `<li class="mute">${T('No stories in this theme yet.', '이 테마의 소식이 아직 없어요.')}</li>`;
  fillPx($('river')); fillPx($('must'));
  if (Date.now() - railAt > 55000 || force) { railAt = Date.now(); rail(xs); }
}
function tabs(xs) { $('tt').innerHTML = THEMES.map((t) => { const n = t.k === 'all' ? xs.length : xs.filter((x) => x.th.includes(t.k)).length; return `<button type="button" role="tab" aria-selected="${S.th === t.k}" data-th="${t.k}">${t[DFI.lang() === 'ko' ? 'ko' : 'en']}<span class="c mono">${n}</span></button>`; }).join(''); }
app.addEventListener('click', (e) => { const t = e.target.closest('[data-th]'); if (t) { S.th = t.dataset.th; render(true); return; }
  const b = e.target.closest('[data-id]'); if (b) openSheet(store.byId.get(b.dataset.id)); });
start(() => render(false)); DFI.onLang(() => render(true));
