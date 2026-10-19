// 정리(Brief) 공통: 지금 이어지는 이야기(줄기) + 어제 하루 정리. 줄기는 Mac 이 30분마다(tools/story_threads.py), 하루 정리는 daily_brief.py.
// 줄기 문장은 AI(근거 소식 번호가 붙은 문장만, 숫자는 근거 소식에 있는 것만), 개수·날짜·호재/악재는 프로그램이 센 것.
import { T, L, esc, store, openSheet, pill, hm, ago } from './lk.js';

const DATA = DFD.data('daily/');
export const THEMES5 = [['all', 'All', '전체'], ['crypto', 'Crypto', '크립토'], ['nasdaq', 'Nasdaq', '나스닥'], ['econ', 'Economy', '경제'], ['ai', 'AI', 'AI'], ['world', 'World', '세계']];
let TH = null;
export async function loadThreads() {
  if (TH) return TH;
  const r = await fetch((window.DF_THREADS || DATA + 'threads.json') + '?t=' + Math.floor(Date.now() / 300000));
  if (!r.ok) throw new Error('threads ' + r.status);
  TH = await r.json();
  // 소식 상세 창(openSheet)이 같은 소식을 찾을 수 있게 store 에 넣는다
  Object.entries(TH.stories).forEach(([id, x]) => { if (!store.byId.has(id)) store.byId.set(id, Object.assign({ id, th: x.th || [] }, x)); });
  TH.list = TH.threads.filter((x) => x.ai);
  return TH;
}
// 가장 최근 하루 정리(이야기 엔진이 날짜를 적어 둔다 — 날짜를 추측해 없는 파일을 부르지 않게)
export async function loadDaily(D) {
  const d = D && D.daily_latest; if (!d) return null;
  try { const r = await fetch(DATA + d + '.json?t=' + Math.floor(Date.now() / 600000)); return r.ok ? await r.json() : null; } catch (e) { return null; }
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
// ---------- 타임라인(B2): 모든 줄이 같은 시간 축 ----------
// 축: 가장 오래된 줄의 시작 날 0시 ~ 지금. 날짜 눈금은 위에 한 번만.
export function axisOf(xs, D) {
  const t0 = Math.min(...xs.map((x) => x.first)), d = new Date(t0 * 1000); d.setHours(0, 0, 0, 0);
  const a0 = d.getTime() / 1000, a1 = D.made, days = [];
  for (const q = new Date(a0 * 1000); q.getTime() / 1000 < a1; q.setDate(q.getDate() + 1)) days.push(q.getTime() / 1000);
  return { a0, a1, days, X: (t) => Math.max(0, Math.min(100, ((t - a0) / Math.max(1, a1 - a0)) * 100)) };
}
const dshort = (t) => new Intl.DateTimeFormat(L() ? 'ko-KR' : 'en-GB', { month: 'numeric', day: 'numeric', weekday: 'short' }).format(new Date(t * 1000));
// 축 날짜는 짧게(한국어 '14일', 영어 '14 Oct'): 하루 칸이 좁아 긴 날짜는 겹친다
const dtiny = (t) => { const d = new Date(t * 1000); return L() ? `${d.getDate()}일` : new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' }).format(d); };
export function axisHTML(A) {
  return `<div class="axis" aria-hidden="true">${A.days.map((t) => `<span style="left:${A.X(t).toFixed(2)}%">${dtiny(t)}</span>`).join('')}</div>`;
}
// 줄 하나: 시작~마지막 소식까지 회색 막대, 소식마다 눈금, 최근 24시간만 강조색
export function trackHTML(x, D, A) {
  const its = x.ids.map((id) => D.stories[id]).filter(Boolean), cut = D.made - 86400;
  const l = A.X(x.first), r = A.X(x.last), c = Math.max(l, A.X(cut));
  return `<div class="track" aria-hidden="true">${A.days.map((t) => `<i class="g" style="left:${A.X(t).toFixed(2)}%"></i>`).join('')}
    <i class="bar" style="left:${l.toFixed(2)}%;width:${Math.max(0.6, r - l).toFixed(2)}%"></i>${x.last > cut ? `<i class="bar hot" style="left:${c.toFixed(2)}%;width:${Math.max(0.6, r - c).toFixed(2)}%"></i>` : ''}
    ${its.map((s) => `<i class="tk${s.s >= 2 ? ' b' : ''}${s.t > cut ? ' hot' : ''}" style="left:${A.X(s.t).toFixed(2)}%"></i>`).join('')}</div>`;
}
// 줄 머리: 회색 한 줄(소식 수 · 기간) + 새 소식이 있을 때만 강조색 점
export function laneMeta(x) {
  return `<span class="lm"><span>${T(`${x.n} stories · ${x.days} ${x.days > 1 ? 'days' : 'day'}`, `${x.n}건 · ${x.days}일`)}</span>${x.new24 ? `<span class="new"><i></i>${T(`${x.new24} new`, `새 소식 ${x.new24}`)}</span>` : ''}</span>`;
}
// 상세: 시각이 달린 세로 줄 목록(날짜별 묶음)
export function railHTML(x, D) {
  const its = x.ids.map((id) => [id, D.stories[id]]).filter(([, s]) => s).reverse(), cut = D.made - 86400;
  let html = '', last = '';
  for (const [id, s] of its) {
    const dk = new Date(s.t * 1000).toDateString();
    if (dk !== last) { html += `<li class="dh">${dshort(s.t)}</li>`; last = dk; }
    html += `<li><button type="button" class="ri${s.t > cut ? ' hot' : ''}" data-sid="${id}"><span class="t mono">${hm(s.t)}</span><span class="l">${esc(L() ? s.ko : s.en || s.ko)}</span>${s.v !== '중립' ? `<span class="v ${s.v === '호재' ? 'u' : 'dn'}">${T(s.v === '호재' ? 'Bullish' : 'Bearish', s.v)}</span>` : ''}</button></li>`;
  }
  return `<ol class="rail2">${html}</ol>`;
}
// 상세 카드(B2): 제목 · 회색 한 줄 · 지금까지 · 오늘 새로 · 세로 줄 목록
export function detailHTML2(x, D) {
  const a = tx(x);
  return `<article class="dt2" data-th="${x.id}"><p class="ths2">${x.th.map((k) => esc((THEMES5.find((q) => q[0] === k) || [k, k, k])[L() ? 2 : 1])).join(' · ')}</p>
    <h2>${esc(a.title)}</h2><p class="dm">${T(`${x.n} stories over ${x.days} ${x.days > 1 ? 'days' : 'day'}`, `${x.days}일 동안 소식 ${x.n}건`)}${x.u || x.d ? ` · ${T(`bullish ${x.u}, bearish ${x.d}`, `호재 ${x.u} · 악재 ${x.d}`)}` : ''}</p>
    <section class="sf"><h3>${T('So far', '지금까지')}</h3>${a.so_far.map((q) => `<p>${sentHTML(q)}</p>`).join('')}</section>
    ${a.today ? `<section class="sf td2"><h3><i></i>${T('New in the last 24 hours', '최근 24시간')}</h3><p>${sentHTML(a.today)}</p></section>` : ''}
    <section class="sf"><h3>${T('Every story', '소식 전체')}</h3>${railHTML(x, D)}</section></article>`;
}

// ---------- 그래프 후보(B2 안에서 비교): 6시간 칸 ----------
export function buckets(x, D, A, hrs = 6) {
  const W = hrs * 3600, n = Math.max(1, Math.ceil((A.a1 - A.a0) / W)), c = new Array(n).fill(0), hot = new Array(n).fill(0), cut = D.made - 86400;
  x.ids.forEach((id) => { const s = D.stories[id]; if (!s) return; const i = Math.min(n - 1, Math.floor((s.t - A.a0) / W)); c[i]++; if (s.t > cut) hot[i]++; });
  return { c, hot, n, W };
}
// 메타 한 줄(Particle·FieldRank 처럼 작은 고정폭): 소식 30 · 2일 · 새 5
export function metaMono(x) {
  return `<span class="mm">${T(`${x.n} stories`, `소식 ${x.n}`)}<i>·</i>${T(`${x.days}d`, `${x.days}일`)}${x.new24 ? `<i>·</i><b>${T(`${x.new24} new`, `새 ${x.new24}`)}</b>` : ''}</span>`;
}
// 후보 1 · 열지도(GitHub 활동 그래프): 6시간 칸을 한 가지 색 진하기로
const LV = (k) => (k <= 0 ? 0 : k === 1 ? 1 : k <= 3 ? 2 : k <= 6 ? 3 : 4);
export function heatHTML(x, D, A) {
  const B = buckets(x, D, A);
  return `<div class="heat" style="--n:${B.n}" aria-hidden="true">${B.c.map((k, i) => `<i class="l${LV(k)}" title="${k}"></i>`).join('')}</div>`;
}
export const heatLegend = () => `<span class="hlg">${T('Fewer', '적음')} <i class="l1"></i><i class="l2"></i><i class="l3"></i><i class="l4"></i> ${T('More', '많음')}</span>`;
// 후보 2 · 네모 쌓기(Extremists on Both Sides): 하루 칸에 소식 하나 = 네모 하나, 최근 24시간은 강조색
export function unitsHTML(x, D, A) {
  const cut = D.made - 86400, cols = A.days.map((t) => ({ t, xs: [] }));
  x.ids.forEach((id) => { const s = D.stories[id]; if (!s) return; let k = cols.length - 1; while (k > 0 && s.t < cols[k].t) k--; cols[k].xs.push(s); });
  return `<div class="units" style="--d:${A.days.length}" aria-hidden="true">${cols.map((c) => `<span class="uc">${c.xs.slice(0, 40).map((s) => `<i class="${s.t > cut ? 'hot' : ''}${s.s >= 2 ? ' b' : ''}"></i>`).join('')}${c.xs.length > 40 ? `<em>+${c.xs.length - 40}</em>` : ''}</span>`).join('')}</div>`;
}
// 후보 3 · 흐름선 + 분위기 막대(Ground News): 6시간 칸 소식 양을 선으로, 오른쪽에 호재·중립·악재 비율
export function moodHTML(x, D, A) {
  const B = buckets(x, D, A), mx = Math.max(1, ...B.c), W = 100, H = 22, X = (i) => (B.n === 1 ? 0 : (i / (B.n - 1)) * W), Y = (k) => H - 2 - (k / mx) * (H - 6);
  const pts = B.c.map((k, i) => `${X(i).toFixed(2)},${Y(k).toFixed(2)}`).join(' '), ci = Math.max(0, Math.floor((D.made - 86400 - A.a0) / B.W));
  const hotPts = B.c.map((k, i) => [i, k]).filter(([i]) => i >= ci).map(([i, k]) => `${X(i).toFixed(2)},${Y(k).toFixed(2)}`).join(' ');
  const z = x.n - x.u - x.d, pct = (v) => Math.round((v / Math.max(1, x.n)) * 100);
  return `<div class="mood"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true"><polyline class="ln" points="${pts}"/>${hotPts.includes(' ') ? `<polyline class="ln hot" points="${hotPts}"/>` : ''}</svg>
    <span class="mb2" role="img" aria-label="${T(`bullish ${pct(x.u)}%, neutral ${pct(z)}%, bearish ${pct(x.d)}%`, `호재 ${pct(x.u)}%, 중립 ${pct(z)}%, 악재 ${pct(x.d)}%`)}"><span class="bar3"><i class="u" style="width:${pct(x.u)}%"></i><i class="z" style="width:${pct(z)}%"></i><i class="dn" style="width:${pct(x.d)}%"></i></span>
    <span class="pl">${pct(z) >= 60 ? `<b>${T('Mostly neutral', '대부분 중립')}</b>` : x.d > x.u ? `<b class="dn">${T('Bearish', '악재')} ${pct(x.d)}%</b>` : x.u > x.d ? `<b class="u">${T('Bullish', '호재')} ${pct(x.u)}%</b>` : `<b>${T('Mixed', '반반')}</b>`}</span></span></div>`;
}

// 문장 + 근거 버튼(누르면 그 소식 상세)
export function sentHTML(q) {
  return `${esc(q.s)} ${q.refs.slice(0, 3).map((id, i) => `<button type="button" class="ref" data-sid="${id}" aria-label="${T('Open source story', '근거 소식 열기')} ${i + 1}">${i + 1}</button>`).join('')}`;
}
export function cardHTML(x, D, { big = false, open = false } = {}) {
  const a = tx(x);
  return `<article class="thc${big ? ' big' : ''}" data-th="${x.id}">
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
  return `<p class="k">${T('Latest daily brief', '최근 하루 정리')} <span>· ${esc(dy.date)}</span></p>
    ${L() ? `<h3>${esc(dy.headline || '')}</h3>${(dy.insights || []).length ? `<ol class="dins">${dy.insights.slice(0, 3).map((x) => `<li><b>${esc(x.t)}</b><span>${esc(x.s)}</span></li>`).join('')}</ol>` : `<p class="rv">${esc(dy.review || '')}</p>`}` : `<h3>${T('Daily brief', '하루 정리')} · ${esc(dy.date)}</h3><p class="rv">${T('The written summary is in Korean for now.', '')}</p>`}
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
