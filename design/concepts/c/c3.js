// C3 · Dashboard — Trading Economics·블룸버그식 '숫자 먼저': 위 요약 + 오른쪽 다음 발표·일정, 가운데 지표 카드 전체, 아래 상세(2열: 기록 | 과거에 비슷했을 때).
import { T } from '../l/lk.js?v=1017215516';
import * as C from './ck.js?v=1017215516';
import { mount } from './cc.js?v=1017215516';
mount((doc, S) => `<div class="wrap cal c3">
  ${C.justHTML(doc, S.k)}
  <div class="top"><section class="box ov">${C.overviewHTML(doc)}</section>
    <aside class="rail"><section class="box">${C.nextHTML(doc)}</section><section class="box"><h2 class="bh">${T('Coming up', '다가오는 발표')}</h2><div class="schw">${C.scheduleHTML(doc, { from: 0, to: 21, sel: S.k })}</div></section></aside></div>
  <section class="box"><div class="sh"><h2 class="bh">${T('Indicators', '지표')}</h2><span class="mute2" style="font-size:12.5px">${T('Tap one to see its history and what prices did after similar releases.', '하나를 누르면 기록과, 비슷했던 과거 발표 뒤 가격 흐름을 볼 수 있어요.')}</span></div>${C.boardHTML(doc, S.k)}</section>
  <section class="box" id="detail" aria-live="polite"></section>
</div>`);
