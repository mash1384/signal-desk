// 정리 화면 동작(후보 B1~B3 공통): 자료 읽기, 거르기, 근거 소식 열기. 배치는 각 후보가 layout(D, dy, S) 로 정한다.
import { T } from './lk.js';
import * as B from './brk.js';
export function mount(layout) {
  const app = document.getElementById('app'), S = { f: 'all', sel: null };
  // ?t=이야기번호: 다른 화면의 '이 이야기 전체 보기'에서 들어오면 그 이야기를 연다
  let jump = null; try { jump = new URLSearchParams(location.search).get('t'); } catch (e) {} if (jump) S.sel = jump;
  let D = null, dy = null;
  if (!app.dataset.prerender) app.innerHTML = '<div class="wrap brf"><div class="skel"></div><div class="skel"></div></div>';
  let hydrated = false;
  // 미리 그린 화면(빌드 때)과 같은 자료 · 같은 언어 · 같은 폭이면 첫 렌더는 건너뛴다 — 같은 내용을 새로 그리면 그 시점이 LCP 로 다시 잡힌다
  const same = () => { const m = app.querySelector('[data-brief-snapshot]'); return !!m && !S.sel && S.f === 'all' &&
    m.dataset.briefSnapshot === `${D.made}|${(dy && dy.made) || ''}|${DFI.lang()}|${matchMedia('(min-width: 1040px)').matches ? 1 : 0}`; };
  const render = () => { const keep = !hydrated && app.dataset.prerender && same(); hydrated = true; if (!keep) app.innerHTML = layout(D, dy, S); B.fitAxis(app); const ds = document.getElementById('bf-dly');
    // 빌드 때 그린 칸(영 · 한 둘 다)과 같은 자료면 손대지 않는다 — 다시 그리면 그 시점이 LCP로 잡힌다. 다른 자료면 그 뒤로는 브라우저가 그린다
    if (ds && dy && (ds.dataset.live || ds.dataset.d !== `${dy.date}|${Math.round(dy.made || 0)}`)) { ds.innerHTML = B.dailyHTML(dy); ds.dataset.live = 1; } };
  // 날짜 축 다시 맞추기(폭 · 글꼴)
  let fitT = 0; const refit = () => { clearTimeout(fitT); fitT = setTimeout(() => B.fitAxis(app), 80); };
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(refit).observe(app); else addEventListener('resize', refit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(refit);
  B.wire(app, S, render);
  app.addEventListener('click', e => { if (!D) { e.preventDefault(); e.stopImmediatePropagation(); } }, true);
  B.loadThreads().then((d) => Promise.all([d, B.loadDaily(d)])).then(([d, y]) => { D = d; dy = y; render();
    if (jump) { const el = app.querySelector(`[data-pick="${CSS.escape(jump)}"]`); if (el) el.scrollIntoView({ block: 'start', behavior: 'auto' }); } })
    .catch(() => { if (!app.dataset.prerender) app.innerHTML = `<div class="wrap brf"><p class="err">${T('Unable to load the stories. Check your connection and reload the page.', '이야기를 불러오지 못했어요. 연결을 확인하고 새로 고침해 주세요.')}</p></div>`; });
  DFI.onLang(() => { if (D) render(); });
}
