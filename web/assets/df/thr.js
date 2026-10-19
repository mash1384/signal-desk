// 이어지는 이야기 표시(라이브·테마·내 자산 공통): 소식 카드에 '이어지는 이야기 · N일째', 소식 상세 창에 '이 이야기 전체 보기' 링크.
// 자료: thread_index.json(Mac 이 30분마다, 소식 → 이야기 · 13KB 안팎). 카드 안에는 링크를 넣지 않는다(카드가 버튼이라 버튼 안 버튼이 된다).
const DATA = DFD.data('daily/thread_index.json');
let IDX = null, P = null, raf = 0;
export function loadIndex() {
  return P || (P = fetch((window.DF_THINDEX || DATA) + '?t=' + Math.floor(Date.now() / 600000)).then((r) => (r.ok ? r.json() : null)).catch(() => null).then((d) => (IDX = d)));
}
const ko = () => DFI.lang() === 'ko';
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const briefHref = (tid) => (window.DF_ROOT ? window.DF_ROOT + 'brief/' : '../br2/') + '?t=' + encodeURIComponent(tid);
export const threadOf = (sid) => (IDX && IDX.s[sid] ? { id: IDX.s[sid], t: IDX.t[IDX.s[sid]] } : null);
function fill() {
  raf = 0; if (!IDX) return;
  // 카드: 첫 번째 메타 줄(.mt) 끝에 작은 표시
  document.querySelectorAll('[data-id]:not([data-thb])').forEach((el) => {
    el.dataset.thb = '1'; const th = threadOf(el.dataset.id); if (!th || !th.t) return; const mt = el.querySelector('.mt'); if (!mt) return;
    mt.insertAdjacentHTML('beforeend', `<span class="thb" title="${esc(ko() ? th.t[0] : th.t[1])}">${ko() ? `이어지는 이야기 · ${th.t[2]}일째` : `Ongoing story · day ${th.t[2]}`}</span>`);
  });
  // 소식 상세 창: 이 이야기 전체 보기(정리 화면에서 그 이야기가 열린다)
  document.querySelectorAll('.thlink[data-sid]:not([data-done])').forEach((el) => {
    el.dataset.done = '1'; const th = threadOf(el.dataset.sid); if (!th || !th.t) return;
    el.innerHTML = `<a class="thl" href="${briefHref(th.id)}"><span class="k">${ko() ? `이어지는 이야기 · ${th.t[2]}일째 · 소식 ${th.t[3]}건` : `Ongoing story · day ${th.t[2]} · ${th.t[3]} stories`}</span>
      <b>${esc(ko() ? th.t[0] : th.t[1])}</b><span class="go">${ko() ? '이 이야기 전체 보기' : 'Read the whole story'} →</span></a>`;
  });
}
export function watchThreads() {
  loadIndex().then(() => { if (!IDX) return; fill(); new MutationObserver(() => { if (!raf) raf = requestAnimationFrame(fill); }).observe(document.body, { childList: true, subtree: true }); });
}
