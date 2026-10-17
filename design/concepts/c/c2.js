// C2 · Calendar + detail — Forex Factory 일정표 + Linear 받은편지함식 상세: 왼쪽 일정(날짜별, 고르면 오른쪽에 그 지표), 오른쪽 상세. 위에는 요약과 지표 줄.
import { T, esc } from '../l/lk.js?v=1017210046';
import * as C from './ck.js?v=1017210046';
import { mount } from './cc.js?v=1017210046';
const strip = (doc, S) => `<div class="chips" role="group" aria-label="${T('Indicators', '지표')}">${doc.indicators.map((x) => `<button type="button" class="chipb${S.k === x.k ? ' on' : ''}" data-ind="${x.k}" aria-pressed="${S.k === x.k}"><span>${esc(C.nm(x))}</span><b class="mono">${C.fv(x, x.latest.v)}</b><span class="mono a">${C.arrow(x.sit.dir)}</span></button>`).join('')}</div>`;
mount((doc, S) => `<div class="wrap cal c2">
  <div class="top"><section class="box ov">${C.overviewHTML(doc)}</section><section class="box">${C.nextHTML(doc)}</section></div>
  ${strip(doc, S)}
  <div class="split"><aside class="box side"><h2 class="bh">${T('Calendar', '일정')}</h2><div class="schw">${C.scheduleHTML(doc, { from: -10, to: 30, sel: S.k })}</div></aside>
    <section class="box" id="detail" aria-live="polite"></section></div>
</div>`);
