// Y3 · 자산 집중형 — 트레이딩뷰·로빈후드처럼 자산 하나를 깊게. 위 칩으로 고르고(전체 = 요약), 큰 그래프에 소식 표시(점 색 = 호재/악재) + 그 자산 소식.
import * as Y from './yk.js?v=1018053947';
import { mount, feedHTML, counts } from './common.js?v=1018053947';
let chart = null;
mount((app, S, my, items) => {
  if (S.a && !my.includes(S.a)) S.a = null;
  const chips = `<div class="achips big" role="tablist" aria-label="${Y.T('Asset', '자산')}"><button type="button" role="tab" class="achip" data-asset="*" aria-selected="${!S.a}" aria-pressed="${!S.a}">${Y.T('Overview', '한눈에')}</button>${my.map((s) => { const q = S.Q[s]; return `<button type="button" role="tab" class="achip" data-asset="${s}" aria-selected="${S.a === s}" aria-pressed="${S.a === s}">${Y.esc(Y.short(s))} <span class="mono">${q && q.chg != null ? DFD.pct(q.chg, 1) : ''}</span></button>`; }).join('')}<button type="button" class="achip add" data-pick>+ ${Y.T('Edit', '편집')}</button></div>`;
  if (!S.a) {
    const rows = my.map((s) => { const a = Y.BY[s], q = S.Q[s], c = counts(items, a);
      return `<li><button type="button" class="orow" data-asset="${s}"><span class="nm"><b>${Y.esc(Y.short(s))}</b><span>${Y.esc(Y.nm(a))}</span></span><canvas class="spk" data-sym="${Y.esc(s)}" aria-hidden="true"></canvas><span class="mono pr">${Y.fmtP(a, q)}</span><span class="mono">${Y.fmtCh(a, q)}</span><span class="ct">${c.n ? `${c.n}${Y.T('', '건')} · <b class="up">${c.u}</b>/<b class="down">${c.d}</b>` : '–'}</span></button></li>`; }).join('');
    app.innerHTML = `<div class="wrap y3"><div class="yh"><h1>${Y.T('My assets', '내 자산')}</h1></div>${chips}
      ${S.mv.length ? `<section class="alerts">${Y.alertsHTML(S.mv)}</section>` : ''}
      <section><h2 class="bh">${Y.T('What matters for you today', '오늘 내 자산에 중요한 소식')}</h2>${Y.topHTML(items)}</section>
      <section class="box"><h2 class="bh">${Y.T('All my assets', '내 자산 전체')}<span class="mute2" style="font-size:12px;font-weight:500">${Y.T('price · 24h · stories (bull/bear)', '가격 · 24시간 · 소식(호재/악재)')}</span></h2><ul class="orows">${rows}</ul></section></div>`;
    return;
  }
  const a = Y.BY[S.a], q = S.Q[S.a], c = counts(items, a), mv = S.mv.find((m) => m.sym === S.a);
  app.innerHTML = `<div class="wrap y3"><div class="yh"><h1>${Y.T('My assets', '내 자산')}</h1></div>${chips}
    <section class="box focus"><div class="fh"><div><p class="fn2"><b>${Y.esc(Y.short(S.a))}</b> ${Y.esc(Y.nm(a))}</p><p class="big"><span class="mono">${Y.fmtP(a, q)}</span> <span class="mono">${Y.fmtCh(a, q)}</span>${q && q.closed && a.src === 'y' ? ` <span class="cl">${Y.T('market closed', '장 마감')}</span>` : ''}</p></div>
      <p class="ct">${Y.T('24h', '24시간')} ${c.n}${Y.T(' stories', '건')} · <b class="up">${c.u}</b> ${Y.T('bull', '호재')} · <b class="down">${c.d}</b> ${Y.T('bear', '악재')}</p></div>
      <div class="bigc" id="bigc"></div><p class="lg"><i class="u"></i>${Y.T('bullish story', '호재 소식')} <i class="d"></i>${Y.T('bearish story', '악재 소식')} <i class="n"></i>${Y.T('neutral', '중립')}</p></section>
    ${mv ? `<section class="alerts">${Y.alertsHTML([mv])}</section>` : ''}
    <section class="box">${feedHTML(S, my, items, { chips: false })}</section></div>`;
  // 큰 그래프: 지난 24시간(코인 5분봉 · 야후 5분봉 있으면 그것, 없으면 1시간) + 소식 표시
  const pts = (q && (q.m && q.m.length > 20 ? q.m : q.c)) || [], el = document.getElementById('bigc'); if (chart) { try { chart.remove(); } catch (e) {} chart = null; }
  if (pts.length > 1 && window.LightweightCharts) { const off = -new Date().getTimezoneOffset() * 60;
    // autoSize는 상자 크기를 따라가므로 높이를 상자에 못 박는다(내용이 높이를 정하면 크기가 계속 바뀔 수 있음)
    el.style.height = (innerWidth < 640 ? 220 : 300) + 'px';
    chart = LightweightCharts.createChart(el, { autoSize: true, layout: { background: { color: 'transparent' }, textColor: '#7b8799', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 },
      grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(13,37,61,.06)' } }, rightPriceScale: { borderVisible: false }, timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false }, crosshair: { mode: 0 },
      handleScroll: { vertTouchDrag: true, mouseWheel: false, pressedMouseMove: false, horzTouchDrag: false }, handleScale: false });
    const ser = chart.addAreaSeries({ lineColor: '#0d253d', topColor: 'rgba(83,58,253,.14)', bottomColor: 'rgba(83,58,253,0)', lineWidth: 2, priceLineVisible: false });
    const data = pts.filter((p) => p[0] >= Date.now() / 1000 - 86400).map((p) => ({ time: p[0] + off, value: p[1] })); ser.setData(data);
    const t0 = data.length ? data[0].time - off : 0, st = items.filter((it) => Y.matches(it, a) && it.t >= t0).sort((x, y) => x.t - y.t);
    const snap = (t) => { let best = data[0].time; for (const d of data) { if (d.time - off <= t) best = d.time; else break; } return best; };
    ser.setMarkers(st.map((it) => ({ time: snap(it.t), position: it.v === '악재' ? 'belowBar' : 'aboveBar', color: it.v === '호재' ? '#0e9f6e' : it.v === '악재' ? '#df4a3a' : '#9aa7b8', shape: 'circle', size: it.s >= 2 ? 1 : 0.6 }))
      .reduce((acc, m) => { if (!acc.some((x) => x.time === m.time && x.color === m.color)) acc.push(m); return acc; }, []));
    chart.timeScale().fitContent(); }
  else el.innerHTML = `<p class="mute">${Y.T('No chart data right now.', '지금은 그래프 자료가 없어요.')}</p>`;
});
