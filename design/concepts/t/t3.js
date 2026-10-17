// T3 · Story — 한 줄로 읽어 내려가는 '테마 리포트'(모바일 먼저, 760px 단). 맨 위 큰 제목 = 요약 1번 문장, 그 아래 근거 소식 카드.
// 2~6번 문장은 이어지는 단락. 그다음 흐름 그래프 → 자산 표 → 섹터 → 주요 소식. 위에서부터 '무슨 일 → 얼마나 → 어디에'.
import * as K from './tk.js?v=1017172142';
import { store, esc } from '../l/lk.js?v=1017172142';
const app = document.getElementById('app'), S = K.initState();
let doc, assets = {}, bench = {}, chart = null;
const ko = () => DFI.lang() === 'ko';
async function render(soft) {
  doc = doc || await K.loadThemes(); const t = K.themeOf(doc, S.k); document.title = `${K.tn(S.k)} · Delfona`;
  const xs = K.pickStories(t, S.so, S.sec, S.chg), shown = S.more ? xs : xs.slice(0, 10), secName = S.sec && (t.sectors.find((s) => s.k === S.sec) || {});
  const list = `<section id="stories" class="blk"><h2 class="bh"><span>${ko() ? '주요 소식' : 'Key stories'}${K.filterChip(t, S)}</span>${K.sortSeg(S.so)}</h2>
    <ul class="srows">${shown.map(K.storyRow).join('') || `<li class="mute">${ko() ? '이 조건의 소식이 없어요.' : 'No stories for this filter.'}</li>`}</ul>${!S.more && xs.length > 10 ? `<button type="button" class="more" data-more>${ko() ? `더 보기 · ${xs.length - 10}건` : `Show ${xs.length - 10} more`}</button>` : ''}</section>`;
  if (soft) { app.querySelector('#stories').outerHTML = list; app.querySelector('#secs').innerHTML = K.sectorsHTML(t, S.sec); app.querySelectorAll('[data-chg]').forEach((b) => b.setAttribute('aria-pressed', String(+b.dataset.chg === S.chg))); K.fillPx(app); return; }
  const C = t.changes || [], c0 = C[0], made = new Date(doc.made * 1000).toLocaleTimeString(ko() ? 'ko-KR' : 'en-GB', { hour: '2-digit', minute: '2-digit' });
  app.innerHTML = `<div class="wrap t3"><div class="head">${K.tabsHTML(S.k)}</div>
    <header class="hero3"><p class="k">${ko() ? `${K.tn(S.k)} · 오늘 무엇이 달라졌나 · 최근 ${doc.base_days}일과 비교 · ${made} 기준` : `${K.tn(S.k)} · what changed today · vs the last ${doc.base_days} days · ${made}`}</p>
      <h1>${c0 ? esc(ko() ? c0.ko : c0.en) : (ko() ? '오늘은 평소와 다른 점이 눈에 띄지 않아요.' : 'Nothing stands out from the usual today.')}</h1>
      ${c0 && c0.ids.length ? `<button type="button" class="more" data-chg="0" aria-pressed="${S.chg === 0}">${ko() ? `이 변화의 소식 ${c0.ids.length}건 보기` : `See the ${c0.ids.length} stories`} →</button>` : ''}
      ${C.length > 1 ? `<div class="chs"><ol>${K.changesHTML(doc, Object.assign({}, t, { changes: C }), S.chg).match(/<ol>([\s\S]*)<\/ol>/)[1].split('</li>').slice(1).join('</li>')}</ol></div>` : ''}
      <p class="fn">${ko() ? `판정한 소식으로 프로그램이 센 숫자예요(AI 문장 아님). '평소' = 최근 ${doc.base_days}일이고, 기록이 쌓이면 7일로 늘어나요.` : `Counted by the program from judged stories (no AI). "Normal" = the last ${doc.base_days} days; it widens to 7 days as history builds up.`}</p></header>
    <section class="blk">${K.statusHTML(doc, t)}<div class="flow" id="flow"></div></section>
    <section class="blk"><h2 class="bh">${ko() ? '관련 자산' : 'Related assets'}</h2><div id="ast"><div class="skelt"></div><div class="skelt"></div></div></section>
    <section class="blk"><h2 class="bh">${ko() ? '섹터별 분포' : 'By sector'}</h2><div id="secs">${K.sectorsHTML(t, S.sec)}</div></section>
    ${S.k === 'econ' ? `<section class="blk"><h2 class="bh">${ko() ? '다음 주요 일정' : 'Coming up'}</h2><div id="evs"></div></section>` : ''}${list}</div>`;
  K.fillPx(app);
  const k = S.k;
  if (!bench[k]) bench[k] = await K.benchSeries(k); if (k !== S.k) return;
  if (chart) { try { chart.remove(); } catch (e) {} } chart = K.flowChart(app.querySelector('#flow'), doc, t, bench[k], { height: innerWidth < 640 ? 200 : 240 });
  if (!assets[k]) assets[k] = await K.loadAssets(k, t); if (k !== S.k) return;
  app.querySelector('#ast').innerHTML = K.assetsHTML(assets[k]); K.drawSparks(app, assets[k]);
  if (k === 'econ') app.querySelector('#evs').innerHTML = await K.eventsHTML();
}
K.wire(app, S, render); render(); DFI.onLang(() => render());
