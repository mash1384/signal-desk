import { T } from './lk.js?v=e2db2637';
import * as B from './brk.js?v=e2db2637';
export function mount(layout) {
  const app = document.getElementById('app'), S = { f: 'all', sel: null };
  let jump = null; try { jump = new URLSearchParams(location.search).get('t'); } catch (e) {} if (jump) S.sel = jump;
  let D = null, dy = null;
  if (!app.dataset.prerender) app.innerHTML = '<div class="wrap brf"><div class="skel"></div><div class="skel"></div></div>';
  let hydrated = false, noTxt = false;
  const same = () => { const m = app.querySelector('[data-brief-snapshot]'); return !!m && !S.sel && S.f === 'all' &&
    m.dataset.briefSnapshot === `${D.made}|${(dy && dy.made) || ''}|${DFI.lang()}|${matchMedia('(min-width: 1040px)').matches ? 1 : 0}`; };
  const render = () => { const keep = !hydrated && app.dataset.prerender && same(); hydrated = true;
    if (!keep && !B.hasText() && !noTxt && (S.sel || matchMedia('(min-width: 1040px)').matches)) { B.loadText().then(render, () => { noTxt = true; render(); }); return; }   // 제목을 못 받으면 제목 없이라도 그린다(다시 돌지 않게)
    if (!keep) app.innerHTML = layout(D, dy, S); B.fitAxis(app); const ds = document.getElementById('bf-dly');
    if (ds && dy && (ds.dataset.live || ds.dataset.d !== `${dy.date}|${Math.round(dy.made || 0)}`)) { ds.innerHTML = B.dailyHTML(dy); ds.dataset.live = 1; } };
  let fitT = 0; const refit = () => { clearTimeout(fitT); fitT = setTimeout(() => B.fitAxis(app), 80); };
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(refit).observe(app); else addEventListener('resize', refit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(refit);
  B.wire(app, S, render);
  ['pointerover', 'pointerdown', 'focusin'].forEach((ev) => app.addEventListener(ev, () => { if (D) B.loadText().catch(() => {}); }, { once: true, passive: true }));   // 누를 낌새가 보이면 미리
  app.addEventListener('click', e => { if (!D) { e.preventDefault(); e.stopImmediatePropagation(); } }, true);
  B.loadThreads().then((d) => Promise.all([d, B.loadDaily(d)])).then(([d, y]) => { D = d; dy = y; render();
    if (jump) { const el = app.querySelector(`[data-pick="${CSS.escape(jump)}"]`); if (el) el.scrollIntoView({ block: 'start', behavior: 'auto' }); } })
    .catch(() => { if (!app.dataset.prerender) app.innerHTML = `<div class="wrap brf"><p class="err">${T('Unable to load the stories. Check your connection and reload the page.', '이야기를 불러오지 못했어요. 연결을 확인하고 새로 고침해 주세요.')}</p></div>`; });
  DFI.onLang(() => { if (D) render(); });
}
