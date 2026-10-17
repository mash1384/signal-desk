// 정리 화면 동작(후보 B1~B3 공통): 자료 읽기, 거르기, 근거 소식 열기. 배치는 각 후보가 layout(D, dy, S) 로 정한다.
import { T } from './lk.js?v=cc3ed8eb';
import * as B from './brk.js?v=cc3ed8eb';
export function mount(layout) {
  const app = document.getElementById('app'), S = { f: 'all', sel: null };
  // ?t=이야기번호: 다른 화면의 '이 이야기 전체 보기'에서 들어오면 그 이야기를 연다
  let jump = null; try { jump = new URLSearchParams(location.search).get('t'); } catch (e) {} if (jump) S.sel = jump;
  let D = null, dy = null;
  app.innerHTML = '<div class="wrap brf"><div class="skel"></div><div class="skel"></div></div>';
  const render = () => { app.innerHTML = layout(D, dy, S); };
  B.wire(app, S, render);
  B.loadThreads().then((d) => Promise.all([d, B.loadDaily(d)])).then(([d, y]) => { D = d; dy = y; render();
    if (jump) { const el = app.querySelector(`[data-pick="${CSS.escape(jump)}"]`); if (el) el.scrollIntoView({ block: 'start', behavior: 'auto' }); } })
    .catch(() => { app.innerHTML = `<div class="wrap brf"><p class="err">${T('Unable to load the stories. Check your connection and reload the page.', '이야기를 불러오지 못했어요. 연결을 확인하고 새로 고침해 주세요.')}</p></div>`; });
  DFI.onLang(() => { if (D) render(); });
}
