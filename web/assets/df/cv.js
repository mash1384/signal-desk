// Shared browser/build markup.
import { T } from './lk.js';
import * as C from './ck.js';
import * as E from './ek.js';
export const calendarLayout = (doc, S, rel = null) => `<div class="wrap cal c3">
  ${rel ? E.releaseHTML(doc, rel) : E.soonHTML(doc)}
  ${E.insightHTML(doc) || `<section class="box ov">${C.overviewHTML(doc)}</section>`}
  <div class="top"><section class="box"><div class="sh"><h2 class="bh">${T('Indicators', '지표')}</h2><span class="mute2" style="font-size:12.5px">${T('Tap one to see its history and what prices did after similar releases.', '하나를 누르면 기록과, 비슷했던 과거 발표 뒤 가격 흐름을 볼 수 있어요.')}</span></div>${(doc.indicators || []).length ? C.boardHTML(doc, S.k) : `<p class="mute2" id="ind-empty" role="status">${T('Indicator data is not available right now (the data source may be under maintenance). The release schedule below is still current.', '지금은 지표 자료를 받지 못했어요(자료 출처 점검 중일 수 있어요). 다가오는 발표 일정은 그대로 볼 수 있어요.')}</p>`}</section>
    <aside class="rail"><section class="box"><h2 class="bh">${T('Coming up', '다가오는 발표')}</h2><div class="nxw">${C.nextHTML(doc)}</div><div class="schw"${(doc.indicators || []).length ? '' : ` tabindex="0" role="region" aria-label="${T('Upcoming releases', '다가오는 발표')}"`}>${C.scheduleHTML(doc, { from: 0, to: 21, sel: S.k })}</div></section></aside></div>
  <section class="box" id="detail" aria-live="polite"></section>
</div>`;
