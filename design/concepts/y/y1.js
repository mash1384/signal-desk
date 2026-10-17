// Y1 · 카드형 — 야후 'My Portfolio'·로빈후드처럼 자산 카드가 먼저. 급변 띠 → 오늘 중요한 3건 → 자산 카드(가격·24시간·작은 그래프·호재/악재·가장 중요한 소식) → 내 자산 소식 전체.
import * as Y from './yk.js?v=1017145910';
import { mount, feedHTML, counts } from './common.js?v=1017145910';
mount((app, S, my, items) => {
  const cards = my.map((s) => { const a = Y.BY[s], q = S.Q[s], c = counts(items, a);
    return `<article class="acard"><div class="ah"><p><b>${Y.esc(Y.short(s))}</b><span>${Y.esc(Y.nm(a))}</span></p><button type="button" class="mystar ic" data-my="${s}" aria-pressed="true" aria-label="${Y.T(`Remove ${s} from My assets`, `${s} 내 자산에서 빼기`)}"><span class="st-ic" aria-hidden="true"></span></button></div>
      <p class="pr"><span class="mono">${Y.fmtP(a, q)}</span> <span class="mono ch">${Y.fmtCh(a, q)}</span>${q && q.closed && a.src === 'y' ? `<span class="cl">${Y.T('closed', '장 마감')}</span>` : ''}</p>
      <canvas class="spk" data-sym="${Y.esc(s)}" aria-hidden="true"></canvas>
      <p class="ct">${c.n ? `${Y.T('24h', '24시간')} <b>${c.n}</b>${Y.T(' stories', '건')} · <b class="up">${c.u}</b> ${Y.T('bull', '호재')} · <b class="down">${c.d}</b> ${Y.T('bear', '악재')}` : `<span class="mute2">${Y.T('No stories in 24h', '24시간 소식 없음')}</span>`}</p>
      ${c.top ? `<button type="button" class="tl btnp" data-id="${c.top.id}">${Y.pill(c.top.v)} <span>${Y.esc(Y.line(c.top))}</span></button>` : ''}</article>`; }).join('');
  app.innerHTML = `<div class="wrap y1"><div class="yh"><div><h1>${Y.T('My assets', '내 자산')}</h1><p>${Y.T(`${my.length} assets · ${items.length} stories in 24h`, `자산 ${my.length}개 · 지난 24시간 소식 ${items.length}건`)}</p></div><button type="button" class="btn s" data-pick>${Y.T('Edit assets', '자산 편집')}</button></div>
    ${S.mv.length ? `<section class="alerts" aria-label="${Y.T('Sudden moves', '급변')}">${Y.alertsHTML(S.mv)}</section>` : ''}
    <section><h2 class="bh">${Y.T('What matters for you today', '오늘 내 자산에 중요한 소식')}</h2>${Y.topHTML(items)}</section>
    <section><h2 class="bh">${Y.T('Assets', '자산')}</h2><div class="cards">${cards}</div></section>
    <section class="box">${feedHTML(S, my, items)}</section></div>`;
});
