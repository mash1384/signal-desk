// 일정 화면 · 발표 순간 해설과 '지금 미국 경제'(국면 · 과거에 이런 때 · FOMC 확률).
// 자료: 발표 순간 = Worker /flash 의 release(Mac release_watch.py, 발표 1분 안팎), 국면 · 해설 = econ.json(regime · insight · fomc).
// 숫자는 모두 프로그램이 계산, 문장만 AI(DeepSeek).
// 차트 원칙(Datawrapper · EU 시각화 지침 · Stripe): 범례 대신 선 끝에 직접 이름표, 비교할 것은 같은 눈금(발표 대비 %), 전→후는 덤벨,
// 맥락은 회색 · 강조만 색, 최신 값 쪽(오른쪽)에 이름표, 숫자는 고정폭. 색만으로 뜻을 전하지 않게 이름 · 화살표를 함께.
import { T, L, esc } from './lk.js';

const FLASH = 'https://signal-scheduler.mash1384.workers.dev/flash';
const lc = () => (L() ? 'ko-KR' : 'en-GB');
const when = (ts) => new Intl.DateTimeFormat(lc(), { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(ts * 1000));
const hm = (ts) => new Intl.DateTimeFormat(lc(), { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(ts * 1000));
const pctS = (v, d = 1) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d) + '%';
const sgn = (v, u, d = 1) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d) + u;
const QC = { hot: '#d97706', stag: '#df4a3a', gold: '#0e9f6e', slow: '#5b7bb4' };
const MKC = { 'NQ=F': '#0d253d', BTC: '#c2410c', 'GC=F': '#4a6aa3' };   // 나스닥 · 비트코인 · 금(이름표와 같은 색)
const ANC = ['#0d253d', '#b45309', '#0f766e'];                         // 닮은 과거 1 · 2 · 3
const VS = { above: ['▲', 'above forecast', '예상보다 높음'], below: ['▼', 'below forecast', '예상보다 낮음'], inline: ['■', 'in line with forecast', '예상과 같음'] };
// AI 문장 속 수치를 굵게(훑어보기 쉽게) — 글은 먼저 이스케이프
const numHi = (s) => esc(s).replace(/([+−-]?\d[\d,.]*\s?(?:%p|%|bp|k|천 명))/g, '<b class="nm">$1</b>');

function canvasOf(cv, h) { const dpr = Math.min(devicePixelRatio || 1, 2), w = cv.clientWidth; cv.width = w * dpr; cv.height = h * dpr; cv.style.height = h + 'px'; const g = cv.getContext('2d'); g.scale(dpr, dpr); return [g, w]; }
const FONT = '11px "JetBrains Mono", ui-monospace, monospace', FONT_B = '600 11.5px Inter, Pretendard, system-ui, sans-serif';
// 선 끝 이름표: 세로로 겹치지 않게 밀어낸다
function spread(labels, minGap, lo, hi) {
  labels.sort((a, b) => a.y - b.y);
  for (let i = 1; i < labels.length; i++) if (labels[i].y - labels[i - 1].y < minGap) labels[i].y = labels[i - 1].y + minGap;
  const over = labels.length ? labels[labels.length - 1].y - hi : 0; if (over > 0) labels.forEach((l) => { l.y -= over; });
  labels.forEach((l) => { l.y = Math.max(lo, l.y); });
  return labels;
}

// ---------- 발표 순간 ----------
let REL = null;
export async function loadRelease() {
  try {
    if (window.DF_RELEASE) { const d = await (await fetch(window.DF_RELEASE + '?t=' + Date.now())).json(); return (REL = d.items || []); }
    const d = await (await fetch(FLASH, { cache: 'no-store' })).json();
    return (REL = (d.release && d.release.items) || []);
  } catch (e) { return REL || []; }
}
export const recent = (items) => (items || []).filter((r) => (window.DF_RELEASE || Date.now() / 1000 - r.ts < 48 * 3600) && r.ai);   // 미리보기(DF_RELEASE)는 지난 발표도

// 곧 발표(2시간 안): 발표되면 여기 해설이 바로 뜬다는 안내
export function soonHTML(doc) {
  const now = Date.now() / 1000, u = (doc.upcoming || []).find((e) => e.ts > now && e.ts - now < 2 * 3600 && (e.keys || []).length);
  if (!u) return '';
  return `<section class="box soon" aria-live="polite"><p class="rk"><span class="dot" aria-hidden="true"></span>${T('Coming up', '곧 발표')} · ${esc(when(u.ts))}</p>
    <h2 class="rh">${esc(L() ? u.ko : u.en)} <span class="mute2" data-until="${u.ts}"></span></h2>
    <p class="rp">${T('When the number lands, an explainer with the first market moves and FOMC odds appears here within about a minute.', '발표되면 1분 안팎으로 여기에 해설과 발표 직후 시장 · FOMC 확률 변화가 떠요.')}</p></section>`;
}

export function releaseHTML(doc, rel) {
  if (!rel) return '';
  const a = rel.ai[L() ? 'ko' : 'en'] || {}, vals = Object.entries(rel.values || {});
  const vh = vals.map(([k, v]) => { const x = doc.by[k], s = VS[v.vs];
    return `<div class="rvi"><span class="n">${esc(x ? (L() ? x.ko : x.en) : k)}</span><b class="mono">${esc(v.disp[L() ? 0 : 1])}</b>
      <span class="w">${s ? `<span class="vs ${v.vs}">${s[0]} ${L() ? s[2] : s[1]}</span>` : ''}<span>${T('forecast', '예상')} <span class="mono">${esc(v.fc || '–')}</span></span><span>${T('previous', '직전')} <span class="mono">${esc(v.disp_prev[L() ? 0 : 1])}</span></span></span></div>`; }).join('');
  const fomc = rel.fomc && rel.fomc.decision ? `<div class="rvi"><span class="n">${T('FOMC decision', 'FOMC 결정')}</span><b>${{ hold: T('Hold', '동결'), cut: T('Cut', '인하'), hike: T('Hike', '인상') }[rel.fomc.decision]}</b>
      ${rel.fomc.lo != null ? `<span class="w mono">${rel.fomc.lo}–${rel.fomc.hi}%</span>` : ''}</div>` : '';
  const mk = Object.keys(rel.market || {}).length ? `<div class="rmk"><h3>${T('Markets around the release', '발표 전후 시장')} <span class="mute2">${T('% vs just before', '발표 직전 대비 %')}</span></h3>
    <p class="mxr" id="mxr" aria-live="polite"></p><canvas class="mxc" id="mxc" role="img" aria-label="${esc(Object.values(rel.market).map((m) => `${L() ? m.ko : m.en} ${m.d60 != null ? pctS(m.d60, 2) : ''}`).join(', '))}"></canvas></div>` : '';
  const od = rel.odds && rel.odds.rows && rel.odds.rows.length ? `<div class="rod"><h3>${T('Next FOMC odds', '다음 FOMC 확률')} <span class="mute2">Kalshi · ${T('before → 1 hour after', '발표 직전 → 1시간 뒤')}</span></h3>
    ${rel.odds.rows.map((r) => { const b = Math.round(r.before * 100), af = Math.round((r.after ?? r.before) * 100), d = af - b, lo = Math.min(b, af), hi = Math.max(b, af);
      return `<div class="db"><span class="dl">${esc(L() ? r.ko : r.en)}</span>
        <span class="dt" aria-hidden="true"><i class="g50"></i><i class="seg" style="inset-inline-start:${lo}%;width:${hi - lo}%"></i><i class="p0" style="inset-inline-start:${b}%"></i><i class="p1" style="inset-inline-start:${af}%"></i></span>
        <span class="dv mono">${b}% → <b>${af}%</b> <span class="${d > 0 ? 'upd' : d < 0 ? 'dnd' : ''}">${d > 0 ? '▲' : d < 0 ? '▼' : '■'}${Math.abs(d)}%p</span></span></div>`; }).join('')}
    <p class="dbk mute2"><span><i class="k0"></i>${T('just before', '발표 직전')}</span><span><i class="k1"></i>${T('1 hour after', '1시간 뒤')}</span></p></div>` : '';
  return `<section class="box rel" aria-labelledby="relh">
    <div class="rl">
      <p class="rk"><span class="dot" aria-hidden="true"></span>${T('Just released', '방금 발표')} · ${esc(L() ? rel.ko : rel.en)} · ${esc(when(rel.ts))}${rel.retro ? ` <span class="mute2">(${T('replay', '다시 보기')})</span>` : ''}</p>
      <h2 class="rh" id="relh">${esc(a.head || (L() ? rel.ko : rel.en))}</h2>
      <div class="rv">${vh}${fomc}</div>
      ${(a.s || []).length ? `<div class="rs">${a.s.map((s) => `<p>${numHi(s)}</p>`).join('')}</div>` : ''}
      ${a.next ? `<p class="rn"><b>${T('Next', '다음')}</b> ${esc(a.next)}</p>` : ''}
    </div>
    ${mk || od ? `<div class="rr">${mk}${od}</div>` : ''}
    <p class="fn rf">${a.by === 'ai' ? T('Explainer written by AI (DeepSeek) from the numbers shown here, then fact-checked against them. ', 'AI(DeepSeek)가 여기 보이는 숫자만 보고 쓰고, 다시 숫자와 대조해 확인한 해설이에요. ') : ''}${T('Market moves happened at the same time as the release — that does not prove the release caused them. Not investment advice.', '시장 움직임은 발표와 같은 시간에 있었던 일이에요. 발표 때문이라는 뜻은 아니에요. 투자 조언이 아니에요.')}</p>
  </section>`;
}

// 발표 전후 시장: 세 자산을 '발표 직전 가격 대비 %' 한 눈금에. 발표 전은 옅게, 선 끝에 이름표, 포인터를 올리면 그 분의 세 값
export function drawRelease(root, rel) {
  const cv = root.querySelector('#mxc'); if (!cv || !rel || !rel.market) return;
  const ser = Object.entries(rel.market).map(([sym, m]) => ({ sym, name: L() ? m.ko : m.en, col: MKC[sym] || '#64748b',
    pts: m.pts.map(([t, p]) => [(t - rel.ts) / 60, (p / m.base - 1) * 100]).filter(([x]) => x >= -30 && x <= 90) })).filter((s) => s.pts.length > 2);
  if (!ser.length) return;
  const H = 230, [g, w] = canvasOf(cv, H), padL = 4, padR = w < 420 ? 92 : 112, top = 18, bot = 24, W = w - padL - padR;
  const ys = ser.flatMap((s) => s.pts.map((p) => p[1])); let lo = Math.min(-0.2, ...ys), hi = Math.max(0.2, ...ys); const pd = (hi - lo) * 0.08; lo -= pd; hi += pd;
  const X = (m) => padL + (m + 30) / 120 * W, Y = (v) => top + (1 - (v - lo) / (hi - lo)) * (H - top - bot);
  const step = (hi - lo) > 3 ? 1 : (hi - lo) > 1.2 ? 0.5 : 0.25;
  const rx = root.querySelector('#mxr');
  const draw = (cx) => {
    g.clearRect(0, 0, w, H);
    g.font = FONT; g.textBaseline = 'middle'; g.textAlign = 'start';
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) { const y = Math.round(Y(v)) + .5, zero = Math.abs(v) < 1e-9;
      g.strokeStyle = zero ? 'rgba(13,37,61,.35)' : 'rgba(13,37,61,.07)'; g.lineWidth = 1; g.beginPath(); g.moveTo(padL, y); g.lineTo(padL + W, y); g.stroke();
      if (!zero) { g.fillStyle = '#64748b'; g.fillText(pctS(v, step < 1 ? 2 : 0), padL + 2, y - 7); } }
    // 발표 시각 · 15분 · 60분 세로선
    const narrow = X(15) - X(0) < 70;   // 좁으면 +15분 이름표는 빼고 선만
    [[0, T('release', '발표') + ' ' + hm(rel.ts)], [15, narrow ? '' : '+15' + T('m', '분')], [60, '+60' + T('m', '분')]].forEach(([m, lab], i) => { const x = Math.round(X(m)) + .5;
      g.strokeStyle = i ? 'rgba(13,37,61,.12)' : 'rgba(13,37,61,.55)'; g.setLineDash(i ? [2, 3] : [4, 3]); g.beginPath(); g.moveTo(x, top - 4); g.lineTo(x, H - bot); g.stroke(); g.setLineDash([]);
      g.fillStyle = i ? '#64748b' : '#0d253d'; g.font = i ? FONT : FONT_B; g.textAlign = 'center'; g.fillText(lab, Math.min(Math.max(x, 34), padL + W - 30), H - 10); });
    g.textAlign = 'start'; g.font = FONT; g.fillStyle = '#64748b'; if (X(0) - padL > 80) g.fillText('−30' + T('m', '분'), padL, H - 10);
    // 선: 발표 전은 옅게
    ser.forEach((s) => { [[(p) => p[0] <= 0, 0.3], [(p) => p[0] >= 0, 1]].forEach(([f, al]) => { const pts = s.pts.filter(f); if (pts.length < 2) return;
      g.globalAlpha = al; g.strokeStyle = s.col; g.lineWidth = 2; g.lineJoin = 'round'; g.beginPath(); pts.forEach((p, j) => (j ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1])))); g.stroke(); });
      g.globalAlpha = 1; });
    // 선 끝 이름표
    spread(ser.map((s) => { const last = s.pts[s.pts.length - 1]; return { s, v: last[1], x: X(last[0]), y: Y(last[1]) }; }), 28, top, H - bot - 10).forEach((l) => {
      g.fillStyle = l.s.col; g.beginPath(); g.arc(l.x, Y(l.v), 3, 0, 7); g.fill(); g.font = FONT_B; g.fillText(l.s.name, l.x + 8, l.y - 6); g.font = FONT; g.fillText(pctS(l.v, 2), l.x + 8, l.y + 8); });
    // 포인터: 세로선 + 위 줄에 그 분의 세 값
    if (cx != null) { const m = Math.max(-30, Math.min(90, (cx - padL) / W * 120 - 30)), x = X(m); g.strokeStyle = 'rgba(13,37,61,.4)'; g.lineWidth = 1; g.beginPath(); g.moveTo(x + .5, top - 4); g.lineTo(x + .5, H - bot); g.stroke();
      const near = ser.map((s) => { let b = s.pts[0]; s.pts.forEach((p) => { if (Math.abs(p[0] - m) < Math.abs(b[0] - m)) b = p; }); return [s, b]; });
      near.forEach(([s, b]) => { g.fillStyle = '#fff'; g.strokeStyle = s.col; g.lineWidth = 2; g.beginPath(); g.arc(X(b[0]), Y(b[1]), 3.5, 0, 7); g.fill(); g.stroke(); });
      rx.innerHTML = `<span class="mono">${m < 0 ? '−' : '+'}${Math.abs(Math.round(m))}${T('m', '분')}</span>` + near.map(([s, b]) => `<span><i style="background:${s.col}"></i>${esc(s.name)} <b class="mono">${pctS(b[1], 2)}</b></span>`).join('');
    } else rx.innerHTML = `<span class="mute2">${T('Hover, drag or use the arrow keys to read each minute.', '그래프 위를 움직이거나(휴대폰은 누르고 끌기) 화살표 키로 분마다 값을 볼 수 있어요.')}</span>`;
  };
  draw(null);
  cv.style.touchAction = 'pan-y';
  const at = (e) => draw(e.clientX - cv.getBoundingClientRect().left);
  cv.onpointermove = at; cv.onpointerdown = at; cv.onpointerleave = () => { if (document.activeElement !== cv) draw(null); };
  // 키보드: 화살표 = 1분(Shift = 10분), Home/End = 처음/끝
  let km = 0; cv.tabIndex = 0;
  cv.onkeydown = (e) => { const st = e.shiftKey ? 10 : 1, k = { ArrowRight: km + st, ArrowLeft: km - st, Home: -30, End: 90 }[e.key]; if (k == null) return; e.preventDefault(); km = Math.max(-30, Math.min(90, k)); draw(X(km)); };
  cv.onfocus = () => draw(X(km)); cv.onblur = () => draw(null);
}

// ---------- 지금 미국 경제 ----------
const qName = (r, k) => { const q = r.quads.find((x) => x.k === k); return q ? (L() ? q.ko : q.en) : k; };
const ym = (s) => new Intl.DateTimeFormat(lc(), { year: 'numeric', month: 'short', timeZone: 'UTC' }).format(new Date(s + '-01T00:00:00Z'));
const ymS = (s) => s.slice(0, 4) + '.' + (+s.slice(5));

export function insightHTML(doc) {
  const r = doc.regime, ins = doc.insight && doc.insight[L() ? 'ko' : 'en'];
  if (!r || !ins) return '';
  const c = r.current, at = new Intl.DateTimeFormat(lc(), { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(doc.insight.at * 1000));
  // 국면 지도(투자 시계식 산점도): 가로 = 고용 흐름, 세로 = 물가 흐름, 최근 12개월 궤적 + 지금 점. 칸 이름은 모서리에 옅게
  const quad = `<figure class="rgm"><canvas class="rgc" id="rgc" role="img" aria-label="${T('Regime map', '국면 지도')}: ${esc(qName(r, c.q))}, ${T('last 12 months', '최근 12개월')}"></canvas>
    <figcaption class="mute2"><b class="rgn">${T('Now', '지금')}: ${T('CPI', '물가')} <span class="mono">${c.cpi.toFixed(1)}%</span> (${T('vs 3 releases ago', '3번 전보다')} <span class="mono">${sgn(c.dcpi, '%p', 2)}</span>) · ${T('payroll gains, 3-release avg', '고용 증가 3번 평균')} <span class="mono">${c.nfp3}k</span> (${T('the 3 before', '그 앞 3번')} <span class="mono">${c.nfp3p}k</span>)</b>
      ${T('Across: payroll momentum. Up: CPI momentum. Dots: last 12 months.', '가로 = 고용 흐름, 세로 = 물가 흐름, 점 = 최근 12개월.')}</figcaption></figure>`;
  const an = (r.analogs || []).map((a, i) => { const f = a.after || {};
    return `<li class="an"><p class="anh"><i class="sw" style="background:${ANC[i]}" aria-hidden="true"></i><b>${esc(ym(a.ym))}</b><span class="mute2">${esc(qName(r, a.q))}</span></p>
      ${a.after ? `<p class="anv"><b class="mono ${f.spx > 0 ? 'up' : 'down'}">${pctS(f.spx)}</b><span>${T('S&P 500, 12 months on', 'S&P 500 · 12개월 뒤')}</span></p>
      <p class="anp"><span class="pl"><i class="${f.rec ? 'on' : ''}" aria-hidden="true"></i>${f.rec ? T('Recession followed', '경기침체 있었음') : T('No recession', '경기침체 없었음')}</span><span class="pl">${T('Fed funds', '기준금리')} <b class="mono">${sgn(f.ff / 100, '%p', 2)}</b></span></p>` : ''}
      <p class="ant mono">${T('then', '그때')} · ${T('CPI', '물가')} ${a.cpi.toFixed(1)}% · ${T('jobs', '고용')} ${a.nfp3}k · ${T('unemp.', '실업률')} ${a.un.toFixed(1)}%</p></li>`; }).join('');
  const s = r.rare && r.rare.after, b = r.after_all;
  const row = (label, k, fmt, upWord) => { if (!s || !s[k] || !b || !b[k]) return ''; const f = (x) => `<b class="mono">${fmt(x.med)}</b><span class="mute2">${Math.round(x.up * x.n)}/${x.n} ${upWord}</span>`;
    return `<tr><th scope="row">${label}</th><td>${f(s[k])}</td><td>${f(b[k])}</td></tr>`; };
  const tbl = s && b ? `<div class="tw" tabindex="0" role="region" aria-label="${T('Comparison table', '비교 표')}"><table class="cmp"><thead><tr><th scope="col"><span class="sr">${T('Measure', '항목')}</span></th><th scope="col">${T('After this mix', '이 조합 뒤')}<span class="mute2">${s.n}${T(' months', '개월')}</span></th><th scope="col">${T('Typical', '평소')}<span class="mute2">${b.n}${T(' months', '개월')}</span></th></tr></thead><tbody>
    ${row('S&amp;P 500', 'spx', (v) => pctS(v), T('rose', '상승'))}${row(T('10-year yield', '10년물 금리'), 'y10', (v) => sgn(v, 'bp', 0), T('rose', '상승'))}
    ${row(T('Fed funds', '기준금리'), 'ff', (v) => sgn(v, 'bp', 0), T('higher', '인상'))}${row(T('CPI inflation', '물가 상승률'), 'cpi', (v) => sgn(v, '%p', 2), T('higher', '높아짐'))}
    <tr><th scope="row">${T('Recession within 12m', '12개월 안 경기침체')}</th><td><b class="mono">${Math.round(s.rec * s.n)}/${s.n}</b></td><td><b class="mono">${Math.round(b.rec * b.n)}/${b.n}</b></td></tr></tbody></table></div>
    <p class="fn">${T('Medians over the next 12 months. Small numbers are counts of months.', '그 뒤 12개월 중앙값. 작은 글씨는 달 수예요.')}</p>` : '';
  const f = doc.fomc && doc.fomc.now, fo = f ? `<div class="fo"><h3>${T('Next FOMC odds', '다음 FOMC 확률')} <span class="mute2">Kalshi · ${T('last 30 days', '최근 30일')}${c.ff != null ? ` · ${T('Fed funds now', '지금 기준금리')} <span class="mono">${c.ff.toFixed(2)}%</span>` : ''}</span></h3>
    <canvas class="foc" id="foc" role="img" aria-label="${esc(f.outcomes.filter((o) => (o.p || 0) >= 0.03).map((o) => `${L() ? o.ko : o.en} ${Math.round(o.p * 100)}%`).join(', '))}"></canvas></div>` : '';
  const P = r.paths;
  return `<section class="box ins" aria-labelledby="insh">
    <header class="ih"><p class="ovk">${T('The US economy now', '지금 미국 경제')} <span>· ${T('AI analysis (DeepSeek), fact-checked', 'AI 해설(DeepSeek) · 숫자 대조 확인')} · ${esc(at)}</span></p>
      <h2 class="insh" id="insh">${esc(ins.head)}</h2></header>
    <div class="ig">
      <div class="it">${ins.s.map((x) => `<p>${numHi(x)}</p>`).join('')}
</div>
      <div class="iv">${quad}</div>
    </div>

    ${P && P.like ? `<div class="pa"><h3>${T('After the closest past months: the S&P 500 over 12 months', '지금과 가장 닮은 과거, 그 뒤 12개월 S&P 500')} <span class="mute2">${T('month-end, start = 0%', '달 끝 종가 · 시작 = 0%')}</span></h3>
      <canvas class="pac" id="pac" role="img" aria-label="${esc((r.analogs || []).map((a) => `${ym(a.ym)} ${a.after ? pctS(a.after.spx) : ''}`).join(', '))}"></canvas>
      <ul class="ans">${an}</ul></div>` : ''}
    <div class="ib">
      <div class="tl"><h3>${T('Since 1991, month by month', '1991년부터 지금까지, 달마다')} <span class="mute2">${T('first-published values', '처음 발표된 값 기준')}</span></h3>
        <canvas class="tlc" id="tlc" role="img" aria-label="${T('CPI inflation and payroll gains since 1991, with recessions and months like now', '1991년 이후 물가 · 고용 흐름과 경기침체, 지금과 비슷했던 달')}"></canvas>
        <p class="tlf" id="tlf" aria-live="polite"></p>
        <p class="lgnd"><span><i class="lc"></i>${T('CPI inflation', '소비자물가 상승률')}</span><span><i class="lb"></i>${T('Payroll gains, 3-release avg', '고용 증가(3번 평균)')}</span><span><i class="rc"></i>${T('Recession', '경기침체')}</span><span><i class="rr"></i>${T('Same mix as now', '지금과 비슷한 조합')}</span></p></div>
      <div><h3>${T('After this mix vs a typical month', '이 조합 뒤 12개월 vs 평소')}</h3>${tbl}${fo}</div>
    </div>
    <p class="fn">${T('Regime: CPI inflation vs 3 releases earlier, and the payroll 3-release average vs the 3 before, using values as first published. Market and rate moves are what happened in the following 12 months — samples are small and this is not a forecast or investment advice. Text by AI (DeepSeek) from these numbers only.',
      '국면: 소비자물가 상승률이 3번 전 발표보다 높아졌는지, 고용 증가 3번 평균이 그 앞 3번보다 커졌는지(그때 처음 발표된 값). 시장 · 금리는 그 뒤 12개월에 실제로 있었던 일이에요. 표본이 적고 예측이 아니에요. 투자 조언이 아니에요. 문장은 AI(DeepSeek)가 이 숫자만 보고 썼어요.')}</p>
  </section>`;
}

// 그 뒤 12개월 S&P 500: 닮은 달 3개(색 · 선 끝 이름표) + 비슷한 조합 가운데 절반(옅은 띠) + 평소 중앙값(회색 점선)
export function drawPaths(root, doc) {
  const cv = root.querySelector('#pac'), r = doc.regime; if (!cv || !r || !r.paths) return;
  const P = r.paths, an = (r.analogs || []).map((a, i) => ({ a, col: ANC[i], p: P.analogs[a.ym] })).filter((x) => x.p);
  const H = 230, [g, w] = canvasOf(cv, H), padL = 4, padR = w < 420 ? 104 : 136, top = 12, bot = 22, W = w - padL - padR;
  const all = [...an.flatMap((x) => x.p), ...(P.like ? [...P.like.p25, ...P.like.p75] : []), ...(P.typical ? P.typical.p50 : [])];
  let lo = Math.min(0, ...all), hi = Math.max(0, ...all); const pd = (hi - lo) * 0.06; lo -= pd; hi += pd;
  const X = (k) => padL + k / 12 * W, Y = (v) => top + (1 - (v - lo) / (hi - lo)) * (H - top - bot), step = (hi - lo) > 50 ? 20 : 10;
  g.font = FONT; g.textBaseline = 'middle'; g.textAlign = 'start';
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) { const y = Math.round(Y(v)) + .5; g.strokeStyle = v === 0 ? 'rgba(13,37,61,.35)' : 'rgba(13,37,61,.07)'; g.lineWidth = 1; g.beginPath(); g.moveTo(padL, y); g.lineTo(padL + W, y); g.stroke();
    g.fillStyle = '#64748b'; if (v !== 0) g.fillText(pctS(v, 0), padL + 2, y - 7); }
  g.textAlign = 'center'; (W < 360 ? [0, 6, 12] : [0, 3, 6, 9, 12]).forEach((k) => g.fillText(k === 0 ? T('then', '그때') : '+' + k + T('m', '개월'), Math.min(Math.max(X(k), 18), padL + W - 22), H - 8)); g.textAlign = 'start';
  if (P.like) { g.fillStyle = 'rgba(83,58,253,.12)'; g.beginPath(); P.like.p75.forEach((v, k) => (k ? g.lineTo(X(k), Y(v)) : g.moveTo(X(k), Y(v)))); for (let k = 12; k >= 0; k--) g.lineTo(X(k), Y(P.like.p25[k])); g.closePath(); g.fill(); }
  if (P.typical) { g.strokeStyle = '#64748b'; g.lineWidth = 1.5; g.setLineDash([4, 4]); g.beginPath(); P.typical.p50.forEach((v, k) => (k ? g.lineTo(X(k), Y(v)) : g.moveTo(X(k), Y(v)))); g.stroke(); g.setLineDash([]); }
  an.forEach((x) => { g.strokeStyle = x.col; g.lineWidth = 2.2; g.lineJoin = 'round'; g.beginPath(); x.p.forEach((v, k) => (k ? g.lineTo(X(k), Y(v)) : g.moveTo(X(k), Y(v)))); g.stroke(); });
  const labs = [...an.map((x) => ({ name: ymS(x.a.ym), v: x.p[12], col: x.col })),
    ...(P.typical ? [{ name: T('typical', '평소 중앙값'), v: P.typical.p50[12], col: '#64748b' }] : []),
    ...(P.like ? [{ name: T(`like now (${P.like.n})`, `비슷한 조합 ${P.like.n}개월`), v: P.like.p50[12], col: '#533afd' }] : [])].map((l) => Object.assign(l, { y: Y(l.v) }));
  spread(labs, 26, top + 6, H - bot - 8).forEach((l) => { g.fillStyle = l.col; g.beginPath(); g.arc(X(12), Y(l.v), 2.6, 0, 7); g.fill();
    g.font = FONT_B; g.fillText(l.name, X(12) + 8, l.y - 6); g.font = FONT; g.fillText(pctS(l.v), X(12) + 8, l.y + 7); });
}

// 1991년부터: 위 = 소비자물가 상승률 선, 아래 = 고용 증가 3번 평균 막대, 회색 = 경기침체, 보라 = 지금과 비슷한 조합, 닮은 달 이름표, 오른쪽 끝 = 지금
export function drawTimeline(root, doc) {
  const cv = root.querySelector('#tlc'), r = doc.regime; if (!cv || !r) return;
  const ms = r.months.filter((m) => m[3] != null), H = 210, [g, w] = canvasOf(cv, H), n = ms.length, padR = 40, W = w - padR, bw = W / n, like = new Set();
  ((r.rare && r.rare.episodes) || []).forEach((e) => { for (const m of ms) if (m[0] >= e.from && m[0] <= e.to) like.add(m[0]); });
  like.add(ms[n - 1][0]);
  const top = 36, ch = 90, by0 = 160, bh = 28;   // 물가 칸(top~top+ch) · 고용 칸(0 기준선 by0, 위아래 bh)
  const cpis = ms.map((m) => m[3]), lo = Math.min(0, ...cpis), hi = Math.max(...cpis), Yc = (v) => top + (1 - (v - lo) / (hi - lo || 1)) * ch;
  const clip = (v) => Math.max(-400, Math.min(400, v)), Yn = (v) => by0 - clip(v) / 400 * bh;
  ms.forEach((m, i) => { if (m[2]) { g.fillStyle = 'rgba(13,37,61,.08)'; g.fillRect(i * bw, top - 8, Math.ceil(bw), by0 + bh - top + 10); } if (like.has(m[0])) { g.fillStyle = 'rgba(83,58,253,.18)'; g.fillRect(i * bw, top - 8, Math.max(2, Math.ceil(bw)), by0 + bh - top + 10); } });
  g.strokeStyle = 'rgba(13,37,61,.07)'; g.lineWidth = 1; [2, 4, 6].filter((v) => v <= hi).forEach((v) => { g.beginPath(); g.moveTo(0, Yc(v) + .5); g.lineTo(W, Yc(v) + .5); g.stroke(); });
  g.strokeStyle = 'rgba(13,37,61,.25)'; g.beginPath(); g.moveTo(0, by0 + .5); g.lineTo(W, by0 + .5); g.stroke();
  g.font = FONT; g.textBaseline = 'middle'; g.textAlign = 'start'; g.fillStyle = '#64748b'; [2, 4, 6].filter((v) => v <= hi).forEach((v) => g.fillText(v + '%', W + 6, Yc(v))); g.fillText('0', W + 6, by0);
  ms.forEach((m, i) => { const v = m[4]; g.fillStyle = v >= 0 ? 'rgba(8,122,85,.62)' : 'rgba(196,58,44,.7)'; const y = Yn(v); g.fillRect(i * bw, Math.min(y, by0), Math.max(1, bw - (bw > 2 ? 0.5 : 0)), Math.abs(y - by0) || 1); });
  g.strokeStyle = '#0d253d'; g.lineWidth = 1.6; g.lineJoin = 'round'; g.beginPath(); ms.forEach((m, i) => (i ? g.lineTo(i * bw + bw / 2, Yc(m[3])) : g.moveTo(bw / 2, Yc(m[3])))); g.stroke();
  // 직접 이름표: 선 · 막대가 무엇인지, 닮은 달(맨 위 줄), 지금(점 옆)
  (r.analogs || []).forEach((a, k) => { const i = ms.findIndex((m) => m[0] === a.ym); if (i < 0) return; const x = i * bw + bw / 2;
    g.fillStyle = ANC[k]; g.font = FONT_B; const t = ymS(a.ym), tw = g.measureText(t).width; g.fillText(t, Math.min(Math.max(0, x - tw / 2), W - tw), top - 18); g.fillRect(x - .5, top - 10, 1.5, 6); });
  const cx = (n - 1) * bw + bw / 2, cy = Yc(ms[n - 1][3]); g.fillStyle = '#533afd'; g.beginPath(); g.arc(cx, cy, 4.5, 0, 7); g.fill(); g.strokeStyle = '#fff'; g.lineWidth = 2; g.stroke();
  g.fillStyle = '#533afd'; g.font = FONT_B; g.textAlign = 'end'; g.fillText(T('now ', '지금 ') + ms[n - 1][3].toFixed(1) + '%', cx - 8, cy - 12); g.textAlign = 'start';
  g.fillStyle = '#64748b'; g.font = FONT; const step = w < 420 ? 10 : 5;
  ms.forEach((m, i) => { const y = +m[0].slice(0, 4); if (m[0].endsWith('-01') && y % step === 0) { const x = i * bw, tw = g.measureText(y).width; g.fillText(y, Math.min(Math.max(0, x - tw / 2), W - tw), H - 6); } });
  const tip = root.querySelector('#tlf'), say = (m, now) => `${ym(m[0])}${now ? ' (' + T('now', '지금') + ')' : ''} · ${T('CPI', '물가')} ${m[3].toFixed(1)}% · ${T('jobs', '고용')} ${m[4]}k · ${qName(r, m[1])}${m[2] ? ' · ' + T('recession', '경기침체') : ''}${like.has(m[0]) && !now ? ' · ' + T('like now', '지금과 비슷한 조합') : ''}`;
  tip.textContent = say(ms[n - 1], true);
  cv.style.touchAction = 'pan-y';
  cv.onpointermove = (e) => { const i = Math.max(0, Math.min(n - 1, Math.floor((e.clientX - cv.getBoundingClientRect().left) / bw))); tip.textContent = say(ms[i], i === n - 1); };
  cv.onpointerdown = cv.onpointermove;
  // 키보드: 화살표 = 한 달(Shift = 1년), Home/End = 처음/지금
  let ki = n - 1; cv.tabIndex = 0;
  cv.onkeydown = (e) => { const st = e.shiftKey ? 12 : 1, k = { ArrowRight: ki + st, ArrowLeft: ki - st, Home: 0, End: n - 1 }[e.key]; if (k == null) return; e.preventDefault(); ki = Math.max(0, Math.min(n - 1, k)); tip.textContent = say(ms[ki], ki === n - 1); };
}

// 다음 FOMC 확률 30일(하루 종가): 칸마다 색 선 + 선 끝 이름표, 그 사이 큰 발표(CPI · 고용 · PCE · GDP)는 세로 점선
export function drawFomc(root, doc) {
  const cv = root.querySelector('#foc'), f = doc.fomc; if (!cv || !f || !f.now) return;
  const outs = f.now.outcomes.filter((o) => (o.p || 0) >= 0.03), cols = ['#0d253d', '#c43a2c', '#087a55', '#64748b'], H = 170, [g, w] = canvasOf(cv, H);
  const ser = outs.map((o, i) => ({ o, col: cols[i], pts: f.days[o.k] || [] })).filter((s) => s.pts.length), all = ser.flatMap((s) => s.pts); if (!all.length) return;
  const t0 = Math.min(...all.map((p) => p[0])), t1 = Math.max(...all.map((p) => p[0])), padR = w < 420 ? 88 : 104, top = 10, bot = 34, W = w - padR - 2;
  const X = (t) => 2 + (t - t0) / (t1 - t0 || 1) * W, Y = (p) => top + (1 - p) * (H - top - bot);
  g.font = FONT; g.textBaseline = 'middle'; g.textAlign = 'start'; g.fillStyle = '#64748b';
  [0, 0.5, 1].forEach((p) => { g.strokeStyle = 'rgba(13,37,61,.07)'; g.lineWidth = 1; g.beginPath(); g.moveTo(2, Y(p) + .5); g.lineTo(2 + W, Y(p) + .5); g.stroke(); g.fillText(Math.round(p * 100) + '%', 4, Y(p) + (p === 1 ? 8 : -7)); });
  const KEY = { cpi: 'CPI', nfp: T('Jobs', '고용'), core_pce: 'PCE', gdp: 'GDP' };
  doc.indicators.filter((x) => KEY[x.k] && x.latest.ts >= t0 - 43200 && x.latest.ts <= t1 + 43200).forEach((x) => { const xx = Math.round(X(Math.min(t1, Math.max(t0, x.latest.ts)))) + .5;
    g.strokeStyle = 'rgba(83,58,253,.45)'; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(xx, top); g.lineTo(xx, H - bot); g.stroke(); g.setLineDash([]);
    g.fillStyle = '#533afd'; g.textAlign = 'center'; g.font = FONT_B; g.fillText(KEY[x.k], Math.min(Math.max(xx, 14), 2 + W - 14), H - bot + 10); g.textAlign = 'start'; g.font = FONT; });
  ser.forEach((s) => { g.strokeStyle = s.col; g.lineWidth = 2; g.lineJoin = 'round'; g.beginPath(); s.pts.forEach((p, j) => (j ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1])))); g.stroke(); });
  spread(ser.map((s) => ({ s, v: s.pts[s.pts.length - 1][1], y: Y(s.pts[s.pts.length - 1][1]) })), 28, top + 6, H - bot - 8).forEach((l) => {
    g.fillStyle = l.s.col; g.beginPath(); g.arc(X(t1), Y(l.v), 3, 0, 7); g.fill(); g.font = FONT_B; g.fillText(L() ? l.s.o.ko : l.s.o.en, X(t1) + 8, l.y - 6); g.font = FONT; g.fillText(Math.round(l.v * 100) + '%', X(t1) + 8, l.y + 7); });
  const d = (t) => new Intl.DateTimeFormat(lc(), { month: 'short', day: 'numeric' }).format(new Date(t * 1000));
  g.fillStyle = '#64748b'; g.font = FONT; g.fillText(d(t0), 2, H - 8); const tw = g.measureText(d(t1)).width; g.fillText(d(t1), 2 + W - tw, H - 8);
}

// 국면 지도: 평면 네 칸(모서리 이름), 0 기준 십자선, 최근 12개월 궤적(옛것일수록 옅게), 지금 = 보라 점 + 이름표
export function drawRegime(root, doc) {
  const cv = root.querySelector('#rgc'), r = doc.regime; if (!cv || !r) return;
  const ms = r.months.filter((m) => m[5] != null && m[6] != null).slice(-12), n = ms.length; if (!n) return;
  const w0 = cv.clientWidth, H = Math.round(Math.min(320, Math.max(240, w0 * 0.78))), [g, w] = canvasOf(cv, H), pad = 14;
  const xs = ms.map((m) => m[6]), ys = ms.map((m) => m[5]);
  const xr = Math.max(100, ...xs.map(Math.abs)) * 1.32, yr = Math.max(0.6, ...ys.map(Math.abs)) * 1.32;   // 모서리 이름표와 점이 겹치지 않게 여유
  const X = (v) => pad + (Math.max(-xr, Math.min(xr, v)) + xr) / (2 * xr) * (w - 2 * pad), Y = (v) => pad + (1 - (Math.max(-yr, Math.min(yr, v)) + yr) / (2 * yr)) * (H - 2 * pad);
  const cx = X(0), cy = Y(0), cur = ms[n - 1];
  // 지금 칸만 아주 옅게
  const qx = cur[6] >= 0, qy = cur[5] >= 0; g.fillStyle = 'rgba(83,58,253,.05)'; g.fillRect(qx ? cx : pad, qy ? pad : cy, qx ? w - pad - cx : cx - pad, qy ? cy - pad : H - pad - cy);
  g.strokeStyle = 'rgba(13,37,61,.14)'; g.lineWidth = 1; g.strokeRect(pad + .5, pad + .5, w - 2 * pad - 1, H - 2 * pad - 1);
  g.strokeStyle = 'rgba(13,37,61,.28)'; g.beginPath(); g.moveTo(Math.round(cx) + .5, pad); g.lineTo(Math.round(cx) + .5, H - pad); g.moveTo(pad, Math.round(cy) + .5); g.lineTo(w - pad, Math.round(cy) + .5); g.stroke();
  // 모서리 칸 이름(지금 칸은 진하게)
  g.textBaseline = 'top'; const corner = (k, right, top) => { const on = k === cur[1]; g.font = on ? FONT_B : '500 11.5px Inter, Pretendard, system-ui, sans-serif'; g.fillStyle = on ? '#0d253d' : '#64748b';
    const t = qName(r, k), tw = g.measureText(t).width; g.fillText(t, right ? w - pad - 8 - tw : pad + 8, top ? pad + 8 : H - pad - 22); };
  corner('stag', false, true); corner('hot', true, true); corner('slow', false, false); corner('gold', true, false);
  // 축 이름(가운데 선 끝)
  g.font = FONT; g.fillStyle = '#64748b'; g.textBaseline = 'middle';
  const ax = T('jobs stronger →', '고용 강해짐 →'), axw = g.measureText(ax).width; g.fillText(ax, w - pad - 6 - axw, cy + 10);
  g.textBaseline = 'top'; g.fillText(T('↑ prices hotter', '↑ 물가 뜨거워짐'), cx + 6, pad + 8);
  // 궤적
  g.lineJoin = 'round';
  // 점을 그대로 지나는 부드러운 곡선(캣멀-롬), 옛것일수록 옅게
  const P = ms.map((m) => [X(m[6]), Y(m[5])]), at = (i) => P[Math.max(0, Math.min(n - 1, i))];
  for (let i = 1; i < n; i++) { const p0 = at(i - 2), p1 = at(i - 1), p2 = at(i), p3 = at(i + 1), a = (i / n) * 0.8 + 0.1;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6], c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    g.strokeStyle = `rgba(13,37,61,${a * 0.55})`; g.lineWidth = 1.6; g.beginPath(); g.moveTo(p1[0], p1[1]); g.bezierCurveTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1]); g.stroke(); }
  ms.forEach((m, i) => { if (i === n - 1) return; const a = (i / n) * 0.7 + 0.12; g.fillStyle = `rgba(13,37,61,${a})`; g.beginPath(); g.arc(X(m[6]), Y(m[5]), 2.6, 0, 7); g.fill(); });
  const px = X(cur[6]), py = Y(cur[5]); g.fillStyle = '#533afd'; g.beginPath(); g.arc(px, py, 6, 0, 7); g.fill(); g.strokeStyle = '#fff'; g.lineWidth = 2.5; g.stroke();
  g.font = FONT_B; g.fillStyle = '#533afd'; const lab = T('now', '지금'), lw = g.measureText(lab).width; g.textBaseline = 'middle'; g.fillText(lab, px + 10 + lw > w - pad ? px - 10 - lw : px + 10, py);
}
