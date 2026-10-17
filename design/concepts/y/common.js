// Y1~Y3 공통 진행: 소식(라이브와 같은 /flash) + 내 자산 시세(60초) → 화면별 render
import * as Y from './yk.js?v=1017180212';
export function mount(render) {
  const app = document.getElementById('app'), S = { so: Y.initSort(), a: null, Q: {}, mv: [], th: null };
  const mine = () => Y.getMy();
  const items = () => { const my = mine().map((s) => Y.BY[s]).filter(Boolean), t0 = Date.now() / 1000 - 86400; return Y.store.items.filter((it) => it.t >= t0 && my.some((a) => Y.matches(it, a))); };
  let qAt = 0, busy = false;
  async function refreshQ(force) { if (busy || (!force && Date.now() - qAt < 60000)) return; busy = true; try { S.Q = await Y.loadQuotes(mine()); qAt = Date.now(); } finally { busy = false; } }
  async function draw(force) {
    if (!mine().length) { app.innerHTML = `<div class="wrap">${Y.emptyHTML()}</div>`; return; }
    if (force || !qAt) await refreshQ(true); S.mv = Y.moves(mine(), S.Q, Y.store.items); if (!S.th) S.th = await Y.loadThemes();
    render(app, S, mine(), items()); Y.fillPx(app); Y.drawSparks(app, S.Q);
  }
  app.addEventListener('click', (e) => {
    if (e.target.closest('[data-pick]')) { Y.openPicker(() => draw(true)); return; }
    if (e.target.closest('[data-go]')) { if (mine().length) draw(true); else Y.openPicker(() => draw(true)); return; }
    const so = e.target.closest('[data-sort]'); if (so) { S.so = so.dataset.sort; try { localStorage.setItem('df-sort', S.so); } catch (x) {} draw(); return; }
    const fa = e.target.closest('[data-asset]'); if (fa) { S.a = fa.dataset.asset === '*' ? null : fa.dataset.asset; draw(); return; }
    const b = e.target.closest('[data-id]'); if (b) { const it = Y.store.byId.get(b.dataset.id); if (it) Y.openSheet(it); }
  });
  // 고르는 중(빈 화면의 첫 고르기, 고르기 창)엔 다시 그리지 않는다 — 여러 개를 고른 뒤 '내 피드 보기'·'완료'로 넘어간다
addEventListener('df-my', () => { if (!document.getElementById('pickdlg')?.open && !app.querySelector('.empty-my')) draw(true); });
  Y.start(() => draw()); DFI.onLang(() => draw()); setInterval(() => { refreshQ().then(() => draw()); }, 60000);
  let rz, rzW = innerWidth; addEventListener('resize', () => { if (innerWidth === rzW) return; rzW = innerWidth; clearTimeout(rz); rz = setTimeout(() => Y.drawSparks(app, S.Q), 200); });
  return S;
}
export function feedHTML(S, my, items, { chips = true } = {}) {
  const xs = Y.sorted(S.a ? items.filter((it) => Y.matches(it, Y.BY[S.a])) : items.slice(), S.so).slice(0, 40);
  return `<h2 class="bh"><span>${Y.T('News on my assets', '내 자산 소식')} <span class="mono" style="font-weight:500;color:var(--faint)">${xs.length}</span></span>${Y.sortSeg(S.so)}</h2>
    ${chips ? `<div class="achips" role="group" aria-label="${Y.T('Filter by asset', '자산으로 거르기')}"><button type="button" class="achip" data-asset="*" aria-pressed="${!S.a}">${Y.T('All', '전체')}</button>${my.map((s) => `<button type="button" class="achip" data-asset="${s}" aria-pressed="${S.a === s}">${Y.esc(Y.short(s))}</button>`).join('')}</div>` : ''}
    <ul class="srows">${xs.map(Y.row).join('') || `<li class="mute">${Y.T('No stories here in the last 24 hours.', '지난 24시간 이 조건의 소식이 없어요.')}</li>`}</ul>`;
}
export const counts = (items, a) => { const xs = items.filter((it) => Y.matches(it, a)); return { n: xs.length, u: xs.filter((x) => x.v === '호재').length, d: xs.filter((x) => x.v === '악재').length, top: xs.filter((x) => x.v !== '중립').sort((p, q) => Y.score(q) - Y.score(p))[0] || xs[0] }; };
