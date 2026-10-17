// T1 · Briefing — Perplexity 금융 첫 화면처럼 '읽는 요약'이 주인공. 왼쪽 넓게 AI 요약 6문장(번호, 근거 소식 연결) · 오른쪽 24시간 흐름 그래프.
// 그 아래 왼쪽 주요 소식(정렬·섹터 거르기) · 오른쪽 자산 시세와 섹터 분포(경제는 다음 일정).
import * as K from './tk.js?v=1017222057';
const app = document.getElementById('app'), S = K.initState();
let doc, assets = {}, bench = {}, chart = null;
async function render(soft) {
  doc = doc || await K.loadThemes(); const t = K.themeOf(doc, S.k);
  document.title = `${K.tn(S.k)} · Delfona`;
  const xs = K.pickStories(t, S.so, S.sec, S.chg), shown = S.more ? xs : xs.slice(0, 12), secName = S.sec && (t.sectors.find((s) => s.k === S.sec) || {});
  const storiesBox = `<section class="box"><h2 class="bh"><span>${K.TNAME[S.k][1] && DFI.lang() === 'ko' ? '주요 소식' : 'Key stories'}${K.filterChip(t, S)}</span>${K.sortSeg(S.so)}</h2>
    <ul class="srows">${shown.map(K.storyRow).join('') || `<li class="mute">${DFI.lang() === 'ko' ? '이 조건의 소식이 없어요.' : 'No stories for this filter.'}</li>`}</ul>${!S.more && xs.length > 12 ? `<button type="button" class="more" data-more>${DFI.lang() === 'ko' ? `더 보기 · ${xs.length - 12}건` : `Show ${xs.length - 12} more`}</button>` : ''}</section>`;
  if (soft) { app.querySelector('#stories').outerHTML = `<div id="stories">${storiesBox}</div>`; app.querySelector('#secs').innerHTML = K.sectorsHTML(t, S.sec); app.querySelector('.sbox').innerHTML = K.changesHTML(doc, t, S.chg); K.fillPx(app); return; }
  app.innerHTML = `<div class="wrap t1"><div class="head">${K.tabsHTML(S.k)}${K.statusHTML(doc, t)}</div>
    <div class="top"><section class="box sbox">${K.changesHTML(doc, t, S.chg)}</section><section class="box flow"><h2 class="bh"><span>${DFI.lang() === 'ko' ? '지난 24시간 흐름' : 'Last 24 hours'}</span><span class="mute2 mono" style="font-size:12px">${DFI.lang() === 'ko' ? '막대 = 시간당 소식 · 선 = ' : 'bars = stories per hour · line = '}${K.BENCH[S.k][2]}</span></h2><div id="flow"></div></section></div>
    <div class="bot"><div id="stories">${storiesBox}</div>
      <aside class="rail"><section class="box"><h2 class="bh">${DFI.lang() === 'ko' ? '관련 자산' : 'Related assets'}</h2><div id="ast"><div class="skelt"></div><div class="skelt"></div><div class="skelt"></div></div><p class="fn">${S.k === 'crypto' ? 'Binance' : DFI.lang() === 'ko' ? '야후 파이낸스(지연될 수 있음) · 언급 = 24시간 소식 수' : 'Yahoo Finance (may be delayed) · mentions = stories in 24h'}</p></section>
        <section class="box"><h2 class="bh">${DFI.lang() === 'ko' ? '섹터별 분포' : 'By sector'}</h2><div id="secs">${K.sectorsHTML(t, S.sec)}</div></section>
        ${S.k === 'econ' ? `<section class="box"><h2 class="bh">${DFI.lang() === 'ko' ? '다음 주요 일정' : 'Coming up'}</h2><div id="evs"></div></section>` : ''}</aside></div></div>`;
  K.fillPx(app);
  const k = S.k;
  if (!bench[k]) bench[k] = await K.benchSeries(k); if (k !== S.k) return;
  if (chart) { try { chart.remove(); } catch (e) {} } chart = K.flowChart(app.querySelector('#flow'), doc, t, bench[k], { height: innerWidth < 640 ? 200 : 250 });
  if (!assets[k]) assets[k] = await K.loadAssets(k, t); if (k !== S.k) return;
  app.querySelector('#ast').innerHTML = K.assetsHTML(assets[k]); K.drawSparks(app, assets[k]);
  if (k === 'econ') app.querySelector('#evs').innerHTML = await K.eventsHTML();
}
K.wire(app, S, render); render(); DFI.onLang(() => render());
