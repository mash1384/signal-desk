// T2 · Dashboard — 블룸버그·야후 마켓처럼 '숫자 먼저'. 맨 위 자산 띠(가로로 미는 카드: 가격 · 24시간 · 작은 그래프),
// 그 아래 2열: 왼쪽 24시간 흐름 그래프(크게) + 섹터 분포 / 오른쪽 AI 요약. 맨 아래 주요 소식(카드 격자).
import * as K from './tk.js';
const app = document.getElementById('app'), S = K.initState();
let doc, bf, assets = {}, bench = {}, chart = null;
// Translation initialization can rerender while the first data requests are
// still pending. Share those requests as well as the completed values below.
const pending = new Map();
function once(key, load) {
  if (!pending.has(key)) pending.set(key, Promise.resolve().then(load).finally(() => pending.delete(key)));
  return pending.get(key);
}
const ko = () => DFI.lang() === 'ko';
// 오른쪽 칸: 분야 전문가 판독(브리핑). 없으면 예전 AI 요약, 그것도 없으면 '평소 대비 변화' 신호
const side = (t) => K.deskHTML(bf, S.k) || ((t.s_ko || []).length ? K.summaryHTML(doc, t) : K.changesHTML(doc, t, S.chg));
async function render(soft) {
  if (!doc) [doc, bf] = await Promise.all([once('themes', () => K.loadThemes()), once('briefing', () => K.loadBriefing())]);
  const t = K.themeOf(doc, S.k); document.title = `${K.tn(S.k)} · Delfona`;
  const xs = K.pickStories(t, S.so, S.sec, S.chg), shown = S.more ? xs : xs.slice(0, 12);
  const grid = `<section id="stories"><h2 class="bh"><span>${ko() ? '주요 소식' : 'Key stories'}${K.filterChip(t, S)}</span>${K.sortSeg(S.so)}</h2>
    <ul class="srows sgrid">${shown.map(K.storyRow).join('') || `<li class="mute">${ko() ? '이 조건의 소식이 없어요.' : 'No stories for this filter.'}</li>`}</ul>${!S.more && xs.length > 12 ? `<button type="button" class="more" data-more>${ko() ? `더 보기 · ${xs.length - 12}건` : `Show ${xs.length - 12} more`}</button>` : ''}</section>`;
  if (soft) { app.querySelector('#stories').outerHTML = grid; app.querySelector('#secs').innerHTML = K.sectorsHTML(t, S.sec);  K.fillPx(app); return; }
  app.innerHTML = `<div class="wrap t2"><div class="head">${K.tabsHTML(S.k)}${K.statusHTML(doc, t)}</div>
    <section class="strip" aria-label="${ko() ? '관련 자산' : 'Related assets'}"><div class="cards" id="cards" tabindex="0">${'<div class="acard skel"></div>'.repeat(5)}</div></section>
    <div class="two"><div class="col"><section class="box flow"><h2 class="bh"><span>${ko() ? '지난 24시간 흐름' : 'Last 24 hours'}</span><span class="mute2 mono" style="font-size:12px">${ko() ? '막대 = 시간당 호재·악재 · 선 = ' : 'bars = bullish/bearish per hour · line = '}${K.BENCH[S.k][2]}</span></h2><div id="flow"></div></section>
      <section class="box"><h2 class="bh">${ko() ? '섹터별 분포' : 'By sector'}</h2><div id="secs">${K.sectorsHTML(t, S.sec)}</div></section>${S.k === 'econ' ? `<section class="box"><h2 class="bh">${ko() ? '다음 주요 일정' : 'Coming up'}</h2><div id="evs"></div></section>` : ''}</div>
      <section class="box sbox tsum">${side(t)}</section></div>${grid}</div>`;
  K.fillPx(app);
  const k = S.k;
  if (!bench[k]) bench[k] = await once('bench:' + k, () => K.benchSeries(k)); if (k !== S.k) return;
  if (chart) { try { chart.remove(); } catch (e) {} } chart = K.flowChart(app.querySelector('#flow'), doc, t, bench[k], { height: innerWidth < 640 ? 210 : 280 });
  if (!assets[k]) assets[k] = await once('assets:' + k, () => K.loadAssets(k, t)); if (k !== S.k) return;
  app.querySelector('#cards').innerHTML = assets[k].map((a) => `<div class="acard"><p class="nm"><b>${DFD.esc(ko() ? a.ko : a.en)}</b>${a.m ? `<span class="mono">${a.m.n}${ko() ? '건' : ''}</span>` : ''}</p><p class="pr mono">${K.fmtP(a)}</p><p class="ch mono">${K.fmtCh(a)}</p><canvas class="spk" data-sym="${DFD.esc(a.sym)}" aria-hidden="true"></canvas></div>`).join('');
  K.drawSparks(app, assets[k]);
  if (k === 'econ') app.querySelector('#evs').innerHTML = await K.eventsHTML();
}
K.wire(app, S, render); render(); DFI.onLang(() => render());
// 뒤로 가기: 주소의 테마로 돌아간다
addEventListener('popstate', () => { const m = location.pathname.match(/themes\/([a-z]+)\/?$/); const k = m ? m[1] : new URLSearchParams(location.search).get('t'); if (k && K.THEME_KEYS.includes(k) && k !== S.k) { S.k = k; S.sec = null; S.chg = null; render(); } });
