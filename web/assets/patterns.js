// 패턴: 뉴스 무게 검색기와 내러티브 열지도 칸 열기. data/patterns.json(최근 30일 측정 완료 기사)을 이 페이지에서만 불러온다.
const S = window.SIGNAL || {};
const BASE = S.base || '/';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (v, d = 2) => (v == null || !isFinite(v) ? '–' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d) + '%');
const two = (n) => (n < 10 ? '0' : '') + n;
const hm = (ts) => { const d = new Date((ts + 9 * 3600) * 1000); return `${two(d.getUTCMonth() + 1)}.${two(d.getUTCDate())} ${two(d.getUTCHours())}:${two(d.getUTCMinutes())}`; };
const med = (a) => { if (!a.length) return null; const v = [...a].sort((x, y) => x - y), m = v.length >> 1; return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2; };
const LABEL = { fomc: 'FOMC·연준', cpi: '물가 지표', jobs: '고용 지표', etf: 'ETF', listing: '상장·상폐', hack: '해킹·사고', regulation: '규제·소송', 'ai-model': 'AI 모델·제품', earnings: '실적', other: '기타' };

function main() {
  const root = $('#ptp');
  if (!root) return;
  let data = null, loading = null;
  const load = () => loading || (loading = fetch(root.dataset.src + '?t=' + Math.floor(Date.now() / 600000)).then((r) => r.json()).then((j) => (data = j)));

  const row = (x) => `<li><a href="${BASE}a/${esc(x.id)}/">${esc(x.title)}</a><span class="ib ib--${x.r1h >= 0 ? 'up' : 'down'} ib--g${x.g === '강' ? 's' : x.g === '중' ? 'm' : 'w'}">${esc(x.s)} 1h ${pct(x.r1h)}${x.g ? ' · ' + esc(x.g) : ''}</span><time class="muted small">${hm(x.t)}</time></li>`;
  const summary = (items, title) => {
    if (items.length < (data.min_n || 5)) {
      return `<p class="ptp__h">${title} · 표본 부족 (n=${items.length})</p>${items.length ? `<ul class="mini-strong">${items.slice(0, 10).map(row).join('')}</ul>` : ''}`;
    }
    const r = items.map((x) => x.r1h), abs = r.map(Math.abs);
    const up = r.filter((v) => v > 0).length / r.length, strong = items.filter((x) => x.g === '강' || x.g === '중').length / items.length;
    const lo = Math.min(-0.5, ...r), hi = Math.max(0.5, ...r);
    const X = (v) => ((v - lo) / (hi - lo)) * 100;
    const dots = items.map((x) => `<a class="pdot ${x.r1h >= 0 ? 'up' : 'down'}" style="left:${X(x.r1h).toFixed(2)}%" href="${BASE}a/${esc(x.id)}/" title="${esc(x.title)} ${pct(x.r1h)}"></a>`).join('');
    const top = [...items].sort((a, b) => Math.abs(b.r1h) - Math.abs(a.r1h)).slice(0, 5);
    return `<p class="ptp__h">${title}</p>
      <dl class="ptp__stats"><div><dt>표본</dt><dd>${items.length}건</dd></div><div><dt>1시간 변동폭 중앙값</dt><dd>±${med(abs).toFixed(2)}%</dd></div><div><dt>1시간 등락 중앙값</dt><dd class="${med(r) >= 0 ? 'up' : 'down'}">${pct(med(r))}</dd></div><div><dt>상승 비율</dt><dd>${Math.round(up * 100)}%</dd></div><div><dt>중·강 비율</dt><dd>${Math.round(strong * 100)}%</dd></div></dl>
      <div class="pstrip" aria-label="기사별 1시간 등락 분포"><span class="pstrip__zero" style="left:${X(0).toFixed(2)}%"></span>${dots}</div>
      <p class="small muted pstrip__axis"><span>${pct(lo, 1)}</span><span>0</span><span>${pct(hi, 1)}</span></p>
      <p class="ptp__sub">가장 크게 움직인 사례</p><ul class="mini-strong">${top.map(row).join('')}</ul>
      <p class="small muted">${esc(data.note)}</p>`;
  };

  const search = async (qv) => {
    const out = $('#pqResult');
    const q = qv.trim().toLowerCase();
    if (!q) return;
    out.innerHTML = '<p class="muted small">찾는 중…</p>';
    await load();
    const terms = [q, ...((data.synonyms || {})[q] || [])];
    Object.entries(data.synonyms || {}).forEach(([k, vs]) => { if (vs.includes(q) && !terms.includes(k)) terms.push(k); });
    const hit = (t) => { const s = t.toLowerCase(); return terms.some((w) => (/^[a-z0-9&.\- ]+$/.test(w) ? new RegExp('(^|[^a-z0-9])' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '([^a-z0-9]|$)').test(s) : s.includes(w))); };
    const items = data.items.filter((x) => hit(x.title));
    out.innerHTML = summary(items, `“${esc(qv.trim())}”${terms.length > 1 ? ` <span class="muted small">(${terms.slice(1).map(esc).join(', ')} 포함)</span>` : ''} · 최근 ${data.days}일`);
  };
  $('#pqForm').addEventListener('submit', (e) => { e.preventDefault(); search($('#pq').value); });
  $$('[data-q]', root).forEach((b) => b.addEventListener('click', () => { $('#pq').value = b.dataset.q; search(b.dataset.q); }));

  // 열지도 기간 전환과 칸 열기
  let days = '7';
  $$('[data-days].mseg__b', root).forEach((b) => b.addEventListener('click', () => {
    days = b.dataset.days;
    $$('[data-days].mseg__b', root).forEach((x) => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
    $$('table.hmap', root).forEach((t) => { t.hidden = t.dataset.days !== days; });
    $('#hmCell').innerHTML = '';
  }));
  root.addEventListener('click', async (e) => {
    const b = e.target.closest('.hm__b');
    if (!b) return;
    await load();
    const since = data.at - Number(days) * 86400, cols = data.cols || [];
    const items = data.items.filter((x) => x.t >= since && (x.e === b.dataset.e || (b.dataset.e === 'other' && !LABEL[x.e])) &&
      (b.dataset.c === 'ALT' ? !cols.includes(x.s) : x.s === b.dataset.c));
    $('#hmCell').innerHTML = `<p class="ptp__h">${esc(LABEL[b.dataset.e] || b.dataset.e)} × ${b.dataset.c === 'ALT' ? '그 외 코인' : esc(b.dataset.c)} · 최근 ${days}일</p>`
      + (items.length ? `<ul class="mini-strong">${items.slice(0, 15).map(row).join('')}</ul>` : '<p class="small muted">이 칸은 기사별 대표 코인이 아닌 측정 코인 전체로 세어, 대표 코인 목록에는 없을 수 있습니다.</p>');
    $('#hmCell').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
  const q0 = new URLSearchParams(location.search).get('q');
  if (q0) { $('#pq').value = q0; search(q0); }
}

main();
