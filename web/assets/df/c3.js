// C3 · Dashboard — Trading Economics·블룸버그식 '숫자 먼저'.
// 순서: 발표 순간(방금 발표 · 곧 발표) → 지금 미국 경제(해설 · 국면 · 과거에 이런 때 · FOMC 확률) → 지표 카드 + 오른쪽 다음 발표 · 일정 → 지표 상세.
import { T } from './lk.js';
import * as C from './ck.js';
import * as E from './ek.js';
import { mount } from './cc.js';
let rel = null;
mount((doc, S) => `<div class="wrap cal c3">
  ${rel ? E.releaseHTML(doc, rel) : E.soonHTML(doc)}
  ${E.insightHTML(doc) || `<section class="box ov">${C.overviewHTML(doc)}</section>`}
  ${rel ? '' : C.justHTML(doc, S.k)}
  <div class="top"><section class="box"><div class="sh"><h2 class="bh">${T('Indicators', '지표')}</h2><span class="mute2" style="font-size:12.5px">${T('Tap one to see its history and what prices did after similar releases.', '하나를 누르면 기록과, 비슷했던 과거 발표 뒤 가격 흐름을 볼 수 있어요.')}</span></div>${C.boardHTML(doc, S.k)}</section>
    <aside class="rail"><section class="box">${C.nextHTML(doc)}</section><section class="box"><h2 class="bh">${T('Coming up', '다가오는 발표')}</h2><div class="schw">${C.scheduleHTML(doc, { from: 0, to: 21, sel: S.k })}</div></section></aside></div>
  <section class="box" id="detail" aria-live="polite"></section>
</div>`, {
  // 그린 뒤: 발표 전후 시장 · 그 뒤 12개월 · 1991년 이후 · FOMC 확률
  after: (root, doc) => { E.drawRelease(root, rel); E.drawRegime(root, doc); E.drawPaths(root, doc); E.drawTimeline(root, doc); E.drawFomc(root, doc); },
  resize: (root, doc) => { E.drawRelease(root, rel); E.drawRegime(root, doc); E.drawPaths(root, doc); E.drawTimeline(root, doc); E.drawFomc(root, doc); },
  // 발표 순간: 처음 한 번, 그리고 발표 2시간 전 ~ 발표 3시간 뒤에는 20초마다 다시 받는다
  live: (doc, rerender) => {
    const pull = () => E.loadRelease().then((items) => { const r = E.recent(items)[0] || null; if ((r && r.updated) !== (rel && rel.updated) || (r && r.id) !== (rel && rel.id)) { rel = r; rerender(); } });
    pull();
    setInterval(() => { const now = Date.now() / 1000; if ((doc.upcoming || []).some((u) => u.ts - now < 2 * 3600 && now - u.ts < 3 * 3600)) pull(); }, 20000);
  },
});
