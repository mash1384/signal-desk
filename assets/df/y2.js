import * as Y from './yk.js?v=e2db2637';
import { mount, feedHTML, counts } from './common.js?v=e2db2637';
mount((app, S, my, items) => {
  const wl = my.map((s) => { const a = Y.BY[s], q = S.Q[s], c = counts(items, a);
    return `<li><button type="button" class="wr" data-asset="${S.a === s ? '*' : s}" aria-pressed="${S.a === s}"><span class="nm"><b>${Y.esc(Y.short(s))}</b><span>${Y.esc(Y.nm(a))}</span></span><canvas class="spk" data-sym="${Y.esc(s)}" aria-hidden="true"></canvas><span class="pq"><span class="mono">${Y.fmtP(a, q)}</span><span class="mono ch">${Y.fmtCh(a, q)}</span></span><span class="nn mono" title="${Y.T('stories in 24h', '24시간 소식')}">${c.n || ''}</span></button></li>`; }).join('');
  app.innerHTML = `<div class="wrap y2"><div class="main"><div class="yh"><div><h1>${Y.T('My assets', '내 자산')}</h1><p>${Y.T(`${items.length} stories on your ${my.length} assets in 24h`, `자산 ${my.length}개 · 지난 24시간 소식 ${items.length}건`)}</p></div></div>
      ${S.mv.length ? `<section class="alerts">${Y.alertsHTML(S.mv)}</section>` : ''}
      <section class="box">${Y.daySummaryHTML(my, items, S.th)}</section>
      <section><h2 class="bh">${Y.T('What matters for you today', '오늘 내 자산에 중요한 소식')}</h2>${Y.topHTML(items)}</section>
      <section class="box" id="feed">${feedHTML(S, my, items, { chips: false })}</section></div>
    <aside class="rail"><section class="box wl"><h2 class="bh"><span>${Y.T('Watchlist', '관심목록')}</span><button type="button" class="btn s" data-pick>${Y.T('Edit', '편집')}</button></h2><ul>${wl}</ul><p class="fn">${Y.T('Tap an asset to see only its news.', '자산을 누르면 그 자산 소식만 봐요.')}</p></section></aside></div>`;
});
