// C1 · Briefing — 한 줄로 읽어 내려가는 구성(Stripe 문서·Linear 변경 기록처럼): 지금 경제 요약 → 다음 큰 발표 → 이번 주 일정 → 지표 카드 → 고른 지표 상세.
import { T } from '../l/lk.js?v=1017172142';
import * as C from './ck.js?v=1017172142';
import { mount } from './cc.js?v=1017172142';
mount((doc, S) => `<div class="wrap cal c1">
  <header class="ph"><h1>${T('Economic calendar', '경제 일정과 지표')}</h1><p>${T('What came out, what it means, and what prices did the last times it looked like this.', '무엇이 나왔고 무슨 뜻인지, 과거에 비슷했을 때 가격은 어땠는지.')}</p></header>
  <section class="box ov">${C.overviewHTML(doc)}</section>
  <div class="row2"><section class="box">${C.nextHTML(doc)}</section><section class="box"><h2 class="bh">${T('This week and next', '이번 주와 다음 주')}</h2><div class="schw">${C.scheduleHTML(doc, { from: -6, to: 14, sel: S.k })}</div></section></div>
  <section><h2 class="bh">${T('Indicators', '지표')}</h2><div class="brd">${C.boardHTML(doc, S.k)}</div></section>
  <section class="box" id="detail" aria-live="polite"></section>
</div>`);
