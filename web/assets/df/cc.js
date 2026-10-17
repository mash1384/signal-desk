// 일정 화면 동작(후보 C1~C3 공통): 자료 읽기, 지표 고르기, 자산·기간 바꾸기, 차트 그리기. 배치는 각 후보가 layout(doc, S) 로 정한다.
import { T } from './lk.js';
import * as C from './ck.js';

export function mount(layout) {
  const app = document.getElementById('app');
  const S = { k: null, asset: '^GSPC', range: '10y' };
  let doc = null;
  try { const q = new URLSearchParams(location.search); if (q.get('i')) S.k = q.get('i'); } catch (e) {}
  app.innerHTML = `<div class="wrap cal"><div class="skel"></div><div class="skel"></div></div>`;
  // 처음 고를 지표: 최근 7일 안에 나온 것 중 목록 앞쪽(중요한 것) → 없으면 가장 최근 발표
  const pick = () => { const now = Date.now() / 1000, rec = doc.indicators.filter((x) => now - x.latest.ts < 7 * 86400); return (rec[0] || [...doc.indicators].sort((a, b) => b.latest.ts - a.latest.ts)[0]).k; };
  function drawDetail() {
    const x = doc.by[S.k]; if (!x) return;
    const box = app.querySelector('#detail'); if (!box) return;
    box.innerHTML = C.detailHTML(doc, x, S);
    C.drawHistory(box.querySelector('#hc'), x, S.range);
    const cv = box.querySelector('#fan'); C.drawFan(cv, box.querySelector('#fl'), doc, x, S.asset); cv.dataset.w = cv.clientWidth;
  }
  function render() {
    if (!S.k || !doc.by[S.k]) S.k = pick();
    app.innerHTML = layout(doc, S);
    C.drawSparks(app, doc); drawDetail(); C.tickUntil(app);
  }
  function select(k, scroll) {
    if (!doc.by[k]) return; S.k = k;
    app.querySelectorAll('[data-ind]').forEach((b) => { const on = b.dataset.ind === k; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
    drawDetail();
    try { history.replaceState(null, '', '?i=' + k); } catch (e) {}
    if (scroll) { const d = app.querySelector('#detail'); if (d && d.getBoundingClientRect().top > innerHeight * 0.6) d.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }); }
  }
  app.addEventListener('click', (e) => {
    const ind = e.target.closest('[data-ind]'); if (ind) { select(ind.dataset.ind, true); return; }
    const a = e.target.closest('[data-asset]'); if (a) { S.asset = a.dataset.asset; drawDetail(); return; }
    const r = e.target.closest('[data-range]'); if (r) { S.range = r.dataset.range; app.querySelectorAll('[data-range]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.range === S.range))); C.drawHistory(app.querySelector('#hc'), doc.by[S.k], S.range); }
  });
  // 폭이 바뀔 때만 다시 그림(휴대폰 주소창 높이 변화는 무시)
  let rzT = 0, rzW = innerWidth;
  addEventListener('resize', () => { if (innerWidth === rzW) return; rzW = innerWidth; clearTimeout(rzT); rzT = setTimeout(() => { if (!doc) return; app.querySelectorAll('canvas[data-spark]').forEach((c) => { delete c.dataset.w; }); C.drawSparks(app, doc); const cv = app.querySelector('#fan'); if (cv) C.drawFan(cv, app.querySelector('#fl'), doc, doc.by[S.k], S.asset); }, 200); });
  C.loadEcon().then((d) => { doc = d; render(); }).catch(() => { app.innerHTML = `<div class="wrap cal"><p class="err">${T('Unable to load the economic data. Check your connection and reload the page.', '경제지표 자료를 불러오지 못했어요. 연결을 확인하고 새로 고침해 주세요.')}</p></div>`; });
  DFI.onLang(() => { if (doc) render(); });
}
