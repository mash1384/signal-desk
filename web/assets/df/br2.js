import { mount } from './bc.js';
import { briefLayout } from './bv.js';
import { openSheet } from './lk.js';
mount((D,dy,S) => briefLayout(D,dy,S,matchMedia('(min-width: 1040px)').matches,window.DF_G || 'heat'));
// 브리핑(빌드 때 그린 맨 위 칸): 근거 단추 → 그 소식 상세 창, 시각은 보는 사람 시간대로
const bf = document.getElementById('bf');
if (bf) {
  let S = {}; try { S = JSON.parse(document.getElementById('bf-stories').textContent); } catch (e) { /* 근거 없이도 글은 보인다 */ }
  bf.addEventListener('click', (e) => { const b = e.target.closest('[data-bf]'); if (b && S[b.dataset.bf]) openSheet(S[b.dataset.bf]); });
  const hm = () => bf.querySelectorAll('time[data-ts]').forEach((t) => { t.textContent = new Date(+t.dataset.ts * 1000).toLocaleTimeString(DFI.lang() === 'ko' ? 'ko-KR' : 'en-GB', { hour: '2-digit', minute: '2-digit' }); });
  hm(); DFI.onLang(hm);
  // 분야별 한 칸(6회차): 탭 · 앞뒤 단추 · 손가락으로 옆으로 밀기. 보이는 분야만 그린다
  const dt = document.getElementById('bf-dkt');
  if (dt) {
    const tabs = [...bf.querySelectorAll('.bf-tabs [data-dk]')], ps = [...dt.querySelectorAll('.bf-dp')], pv = [...bf.querySelectorAll('.bf-pv')], n = ps.length;
    let at = 0;
    const go = (i, focus) => { at = Math.min(n - 1, Math.max(0, i));
      ps.forEach((p, j) => p.classList.toggle('on', j === at)); tabs.forEach((t, j) => { t.setAttribute('aria-selected', j === at); t.tabIndex = j === at ? 0 : -1; });
      pv[0].disabled = at === 0; pv[1].disabled = at === n - 1;
      const t = tabs[at]; t.parentElement.scrollTo({ left: t.offsetLeft - 8, behavior: 'smooth' }); if (focus) t.focus(); };
    tabs.forEach((t, j) => (t.onclick = () => go(j)));
    pv.forEach((b) => (b.onclick = () => go(at + +b.dataset.step)));
    bf.querySelector('.bf-tabs').addEventListener('keydown', (e) => { const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0; if (d) { e.preventDefault(); go(at + d, true); } });
    let x0 = null, y0 = 0;
    dt.addEventListener('touchstart', (e) => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    dt.addEventListener('touchend', (e) => { if (x0 == null) return; const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0; x0 = null;
      if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.5) go(at + (dx < 0 ? 1 : -1)); }, { passive: true });
    go(0);
  }
}
// 소식 그림(점묘화, art.js): PC에서만, 한가할 때 — 빌드가 고른 그림(data-art)을 제목 옆 · 카드 위 띠에(자리는 CSS가 미리 비워 둠)
if (bf && bf.querySelector('[data-art]')) {
  const mq = matchMedia('(min-width: 900px)'); let A;
  const draw = () => { if (!mq.matches) { if (A) bf.querySelectorAll('.has-art').forEach(A.clear); return; }
    (A ? Promise.resolve(A) : import('./art.js' + new URL(import.meta.url).search).then((m) => { A = m; m.watch(draw); return m; })).then(() => {
      const w = bf.querySelector('.wrap'), h = document.getElementById('bf-h'), k = bf.querySelector('.bf-k'), nx = h && h.nextElementSibling;
      if (bf.dataset.artH && k && nx) A.load(bf.dataset.artH).then((m) => { const r = w.getBoundingClientRect(); A.paint(w, { x0: r.width * 0.5, x1: r.width - 4, y0: k.getBoundingClientRect().top - r.top - 6, y1: nx.getBoundingClientRect().top - r.top - 14 }, m, { ink: h }); });
      bf.querySelectorAll('.bf-c[data-art]').forEach((c) => A.load(c.dataset.art).then((m) => A.paint(c, { x0: 0, x1: c.clientWidth, y0: 0, y1: 179 }, m, { e: [0.12, 0.88, 0.08, 0.62], ink: c.querySelector('h3') })));
    }).catch(() => {}); };   // 그림이 없어도 글은 그대로
  (window.requestIdleCallback || ((f) => setTimeout(f, 300)))(draw); mq.addEventListener('change', draw);
}
// 용어 풀이(gl.js): 첫 화면을 다 그린 뒤 한가할 때 불러와 어려운 말에 점선 밑줄
if (bf) (window.requestIdleCallback || ((f) => setTimeout(f, 300)))(() => import('./gl.js' + new URL(import.meta.url).search).then((m) => m.glossarize(bf)));
