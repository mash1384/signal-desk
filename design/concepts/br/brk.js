// 정리(Brief) 공통: 지금 이어지는 이야기(줄기) + 어제 하루 정리. 줄기는 Mac 이 30분마다(tools/story_threads.py), 하루 정리는 daily_brief.py.
// 줄기 문장은 AI(근거 소식 번호가 붙은 문장만, 숫자는 근거 소식에 있는 것만), 개수·날짜·호재/악재는 프로그램이 센 것.
import { T, L, esc, store, openSheet, pill, hm, ago } from '../l/lk.js?v=1017210046';

const RAW = 'https://raw.githubusercontent.com/mash1384/signal-desk/flash/daily/';
export const THEMES5 = [['all', 'All', '전체'], ['crypto', 'Crypto', '크립토'], ['nasdaq', 'Nasdaq', '나스닥'], ['econ', 'Economy', '경제'], ['ai', 'AI', 'AI'], ['world', 'World', '세계']];
let TH = null;
export async function loadThreads() {
  if (TH) return TH;
  const r = await fetch((window.DF_THREADS || RAW + 'threads.json') + '?t=' + Math.floor(Date.now() / 300000));
  if (!r.ok) throw new Error('threads ' + r.status);
  TH = await r.json();
  // 소식 상세 창(openSheet)이 같은 소식을 찾을 수 있게 store 에 넣는다
  Object.entries(TH.stories).forEach(([id, x]) => { if (!store.byId.has(id)) store.byId.set(id, Object.assign({ id, th: x.th || [] }, x)); });
  TH.list = TH.threads.filter((x) => x.ai);
  return TH;
}
// 어제(한국 시각) 하루 정리. 없으면 그 전날.
export async function loadDaily() {
  const kst = (d) => new Date(Date.now() + 9 * 3600e3 - d * 864e5).toISOString().slice(0, 10);
  for (const d of [1, 2, 3]) { try { const r = await fetch(RAW + kst(d) + '.json?t=' + Math.floor(Date.now() / 600000)); if (r.ok) return await r.json(); } catch (e) {} }
  return null;
}
const lc = () => (L() ? 'ko-KR' : 'en-GB');
export const tx = (x) => x.ai && x.ai[L() ? 'ko' : 'en'];
export const dayOf = (t) => new Intl.DateTimeFormat(lc(), { month: 'short', day: 'numeric', weekday: 'short' }).format(new Date(t * 1000));

// 줄기 머리 정보: N일째 · 소식 N건 · 호재/악재(글자로도)
export function metaHTML(x) {
  const days = T(`day ${x.days}`, `${x.days}일째`);
  return `<p class="tm"><span class="d">${days}</span><span>${T(`${x.n} stories`, `소식 ${x.n}건`)}</span>${x.u ? `<span class="u">${T('bullish', '호재')} ${x.u}</span>` : ''}${x.d ? `<span class="dn">${T('bearish', '악재')} ${x.d}</span>` : ''}${x.new24 ? `<span class="nw">${T(`+${x.new24} in 24h`, `24시간 +${x.new24}`)}</span>` : ''}</p>`;
}
// 날짜별 점 줄(소식 하나 = 점 하나, 색은 호재·악재·중립 + 크기는 세기). HTML 로 그려 점이 늘어나지 않게, 높이 고정.
export function stripHTML(x, D) {
  const its = x.ids.map((id) => D.stories[id]).filter(Boolean), t0 = its[0].t, t1 = Math.max(D.made, its[its.length - 1].t);
  const X = (t) => (((t - t0) / Math.max(1, t1 - t0)) * 100).toFixed(2);
  const days = []; const d = new Date(t0 * 1000); d.setHours(24, 0, 0, 0); for (; d.getTime() / 1000 < t1; d.setDate(d.getDate() + 1)) days.push(d.getTime() / 1000);
  const dots = its.map((s) => `<i class="${s.v === '호재' ? 'u' : s.v === '악재' ? 'dn' : 'z'}${s.s >= 2 ? ' b' : ''}" style="left:${X(s.t)}%" title="${esc(hm(s.t))} ${esc(L() ? s.ko : s.en || s.ko)}"></i>`).join('');
  return `<div class="strip" role="img" aria-label="${T(`${x.n} stories over ${x.days} days`, `${x.days}일에 걸친 소식 ${x.n}건`)}"><span class="base"></span>${days.map((t) => `<span class="dl" style="left:${X(t)}%"></span>`).join('')}${dots}</div>
    <p class="sl"><span>${dayOf(t0)}</span><span>${T('now', '지금')}</span></p>`;
}
// 문장 + 근거 버튼(누르면 그 소식 상세)
export function sentHTML(q) {
  return `${esc(q.s)} ${q.refs.slice(0, 3).map((id, i) => `<button type="button" class="ref" data-sid="${id}" aria-label="${T('Open source story', '근거 소식 열기')} ${i + 1}">${i + 1}</button>`).join('')}`;
}
export function cardHTML(x, D, { big = false, open = false } = {}) {
  const a = tx(x);
  return `<article class="th${big ? ' big' : ''}" data-th="${x.id}">
    <header><p class="ths">${x.th.map((k) => `<span>${esc((THEMES5.find((q) => q[0] === k) || [k, k, k])[L() ? 2 : 1])}</span>`).join('')}</p><h3>${esc(a.title)}</h3>${metaHTML(x)}</header>
    ${stripHTML(x, D)}
    <div class="sofar"><p class="k">${T('So far', '지금까지')}</p>${a.so_far.map((q) => `<p>${sentHTML(q)}</p>`).join('')}</div>
    ${a.today ? `<div class="today"><p class="k">${T('New in the last 24 hours', '최근 24시간 새로 붙은 것')}</p><p>${sentHTML(a.today)}</p></div>` : ''}
    <details${open ? ' open' : ''}><summary>${T(`All ${x.n} stories`, `소식 ${x.n}건 모두 보기`)}</summary><ol class="sts">${x.ids.slice().reverse().map((id) => { const s = D.stories[id]; return s ? `<li><button type="button" data-sid="${id}"><span class="t mono">${dayOf(s.t)} ${hm(s.t)}</span>${pill(s.v)}<span class="l">${esc(L() ? s.ko : s.en || s.ko)}</span></button></li>` : ''; }).join('')}</ol></details>
  </article>`;
}
export function filtHTML(D, cur) {
  const n = (k) => (k === 'all' ? D.list.length : D.list.filter((x) => x.th.includes(k)).length);
  return `<div class="filt" role="group" aria-label="${T('Theme', '테마')}">${THEMES5.filter(([k]) => k === 'all' || n(k)).map(([k, en, ko]) => `<button type="button" data-f="${k}" aria-pressed="${cur === k}">${L() ? ko : en}<span class="c mono">${n(k)}</span></button>`).join('')}</div>`;
}
export const pickList = (D, f) => (f === 'all' ? D.list : D.list.filter((x) => x.th.includes(f)));
// 어제 하루 정리(한국어만 있는 자료라 영어 화면에서는 숫자 요약만)
export function dailyHTML(dy) {
  if (!dy) return '';
  const b = dy.balance || {}, m = dy.market || {};
  return `<p class="k">${T('Yesterday in one page', '어제 하루 정리')} <span>· ${esc(dy.date)}</span></p>
    ${L() ? `<h3>${esc(dy.headline || '')}</h3><p class="rv">${esc(dy.review || '')}</p>` : `<h3>${T('Daily brief', '하루 정리')} · ${esc(dy.date)}</h3><p class="rv">${T('The written summary is in Korean for now.', '')}</p>`}
    <p class="nums"><span><b class="mono">${(dy.counts || {}).stories || 0}</b> ${T('stories', '건')}</span><span class="u"><b class="mono">${b['호재'] || 0}</b> ${T('bullish', '호재')}</span><span class="dn"><b class="mono">${b['악재'] || 0}</b> ${T('bearish', '악재')}</span>${m.btc ? `<span>BTC <b class="mono ${m.btc.chg >= 0 ? 'u' : 'dn'}">${m.btc.chg >= 0 ? '+' : ''}${m.btc.chg.toFixed(2)}%</b></span>` : ''}</p>
    <a class="more" href="${window.DF_ROOT || '../../'}daily/${esc(dy.date)}/">${T('Read the full daily brief', '하루 정리 전체 보기')} →</a>`;
}
export function wire(app, S, render) {
  app.addEventListener('click', (e) => {
    const f = e.target.closest('[data-f]'); if (f) { S.f = f.dataset.f; render(); return; }
    const s = e.target.closest('[data-sid]'); if (s) { const it = store.byId.get(s.dataset.sid); if (it) openSheet(it); return; }
    const t = e.target.closest('[data-pick]'); if (t) { S.sel = t.dataset.pick; render(); return; }
  });
}
export function fresh(D) { const m = Math.round((Date.now() / 1000 - D.made) / 60); return T(`Updated ${m < 60 ? m + ' min' : Math.round(m / 60) + ' h'} ago · every 30 min`, `${m < 60 ? m + '분' : Math.round(m / 60) + '시간'} 전 갱신 · 30분마다`); }
