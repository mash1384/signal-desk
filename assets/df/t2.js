import * as K from './tk.js?v=40f2d0b9';
const app = document.getElementById('app'), S = K.initState();
let doc, bf, assets = {}, bench = {}, chart = null;
const pending = new Map();
function once(key, load) {
  if (!pending.has(key)) pending.set(key, Promise.resolve().then(load).finally(() => pending.delete(key)));
  return pending.get(key);
}
const ko = () => DFI.lang() === 'ko';
const side = (t) => K.deskHTML(bf, S.k) || ((t.s_ko || []).length ? K.summaryHTML(doc, t) : K.changesHTML(doc, t, S.chg));
async function render(soft) {
  if (!doc) { [doc, bf] = await Promise.all([once('themes', () => K.loadThemes()), once('briefing', () => K.loadBriefing())]); K.useBriefingStories(bf); }
  const t = K.themeOf(doc, S.k); document.title = `${K.tn(S.k)} · Delfona`;
  const xs = K.pickStories(t, S.so, S.sec, S.chg), shown = S.more ? xs : xs.slice(0, 12);
  const grid = `<section id="stories"><h2 class="bh"><span>${ko() ? '주요 소식' : 'Key stories'}${K.filterChip(t, S)}</span>${K.sortSeg(S.so)}</h2>
    <ul class="srows sgrid">${shown.map(K.storyRow).join('') || `<li class="mute">${ko() ? '이 조건의 소식이 없어요.' : 'No stories for this filter.'}</li>`}</ul>${!S.more && xs.length > 12 ? `<button type="button" class="more" data-more>${ko() ? `더 보기 · ${xs.length - 12}건` : `Show ${xs.length - 12} more`}</button>` : ''}</section>`;
  if (soft) { app.querySelector('#stories').outerHTML = grid; app.querySelector('#secs').innerHTML = K.sectorsHTML(t, S.sec);  K.fillPx(app); return; }
  app.innerHTML = `<div class="wrap t2"><div class="head">${K.tabsHTML(S.k)}${K.statusHTML(doc, t)}</div>
    <section class="strip" aria-label="${ko() ? '관련 자산' : 'Related assets'}"><div class="cards" id="cards" tabindex="0">${'<div class="acard skel"></div>'.repeat(5)}</div></section>
    <div class="two"><div class="col"><section class="box flow"><h2 class="bh"><span>${ko() ? '지난 24시간 흐름' : 'Last 24 hours'}</span><span class="mute2 mono" style="font-size:12px">${ko() ? '막대 = 시간당 호재·악재 · 선 = ' : 'bars = bullish/bearish per hour · line = '}${K.benchName(S.k)}</span></h2><div id="flow"></div></section>
      <section class="box"><h2 class="bh">${ko() ? '섹터별 분포' : 'By sector'}</h2><div id="secs">${K.sectorsHTML(t, S.sec)}</div></section>${S.k === 'econ' ? `<section class="box"><h2 class="bh">${ko() ? '다음 주요 일정' : 'Coming up'}</h2><div id="evs"></div></section>` : ''}</div>
      <section class="box sbox tsum">${side(t)}</section></div>${grid}</div>`;
  K.fillPx(app);
  (window.requestIdleCallback || ((f) => setTimeout(f, 300)))(() => import('./gl.js' + new URL(import.meta.url).search).then((m) => m.glossarize(app.querySelector('.tsum'))));   // 데스크 글의 어려운 말에 풀이
  const k = S.k;
  if (!bench[k]) bench[k] = await once('bench:' + k, () => K.benchSeries(k)); if (k !== S.k) return;
  if (chart) { try { chart.remove(); } catch (e) {} } chart = K.flowChart(app.querySelector('#flow'), doc, t, bench[k], { height: innerWidth < 640 ? 210 : 280 });
  if (!assets[k]) assets[k] = await once('assets:' + k, () => K.loadAssets(k, t)); if (k !== S.k) return;
  app.querySelector('#cards').innerHTML = assets[k].map((a) => `<div class="acard"><p class="nm"><b>${DFD.esc(ko() ? a.ko : a.en)}</b>${a.m ? `<span class="mono">${a.m.n}${ko() ? '건' : ''}</span>` : ''}</p><p class="pr mono">${K.fmtP(a)}</p><p class="ch mono">${K.fmtCh(a)}</p><canvas class="spk" data-sym="${DFD.esc(a.sym)}" aria-hidden="true"></canvas></div>`).join('');
  K.drawSparks(app, assets[k]);
  if (k === 'econ') app.querySelector('#evs').innerHTML = await K.eventsHTML();
}
K.wire(app, S, render); render(); DFI.onLang(() => render());
addEventListener('popstate', () => { const m = location.pathname.match(/themes\/([a-z]+)\/?$/); const k = m ? m[1] : new URLSearchParams(location.search).get('t'); if (k && K.THEME_KEYS.includes(k) && k !== S.k) { S.k = k; S.sec = null; S.chg = null; render(); } });
