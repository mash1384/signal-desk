// 정리 화면 동작(후보 B1~B3 공통): 자료 읽기, 거르기, 근거 소식 열기. 배치는 각 후보가 layout(D, dy, S) 로 정한다.
import { T } from '../l/lk.js?v=1017215516';
import * as B from './brk.js?v=1017215516';
export function mount(layout) {
  const app = document.getElementById('app'), S = { f: 'all', sel: null };
  let D = null, dy = null;
  app.innerHTML = '<div class="wrap brf"><div class="skel"></div><div class="skel"></div></div>';
  const render = () => { app.innerHTML = layout(D, dy, S); };
  B.wire(app, S, render);
  Promise.all([B.loadThreads(), B.loadDaily()]).then(([d, y]) => { D = d; dy = y; render(); })
    .catch(() => { app.innerHTML = `<div class="wrap brf"><p class="err">${T('Unable to load the stories. Check your connection and reload the page.', '이야기를 불러오지 못했어요. 연결을 확인하고 새로 고침해 주세요.')}</p></div>`; });
  DFI.onLang(() => { if (D) render(); });
}
