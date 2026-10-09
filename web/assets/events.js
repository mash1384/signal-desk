// 이벤트 리스크: 위험 시계(레이더)와 발표 카드의 남은 시간.
// 시계 12시 방향이 지금, 시계 방향으로 24시간(또는 7일). 원의 크기 = 과거 같은 발표 뒤 BTC 1시간 변동폭 중앙값.
const S = window.SIGNAL || {};
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const two = (n) => (n < 10 ? '0' : '') + n;
const nowSec = () => Date.now() / 1000;
const left = (sec) => {
  if (sec <= 0) return '발표됨';
  const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60);
  return d ? `${d}일 ${h}시간 뒤` : h ? `${h}시간 ${m}분 뒤` : `${m}분 뒤`;
};
const hm = (ts) => { const d = new Date((ts + 9 * 3600) * 1000); return `${two(d.getUTCMonth() + 1)}.${two(d.getUTCDate())} ${two(d.getUTCHours())}:${two(d.getUTCMinutes())}`; };
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function main() {
  const box = $('#radar');
  const items = (S.radar || []).slice();
  let spanH = 24, W = 0, H = 0, dpr = 1, spots = [];
  const tick = () => { $$('[data-left]').forEach((el) => { el.textContent = left(Number(el.dataset.left) - nowSec()); }); };
  tick();
  setInterval(tick, 30000);
  if (!box) return;
  const canvas = $('#radarCanvas'), ctx = canvas.getContext('2d'), center = $('#radarCenter');
  const css = getComputedStyle(document.documentElement);
  const col = (n) => css.getPropertyValue(n).trim() || '#888';
  const alpha = (c, a) => (c.startsWith('oklch(') ? (c.includes('/') ? c.replace(/\/\s*[\d.]+\s*\)$/, `/ ${a})`) : c.replace(/\)$/, ` / ${a})`)) : c);

  function draw() {
    if (!W) return;
    const C = { text: col('--text'), text3: col('--text-3'), accent: col('--accent'), line: col('--line') };
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2 - 50;
    const now = nowSec(), end = now + spanH * 3600;
    // 시계 판: 시간 눈금
    ctx.strokeStyle = alpha(C.text3, 0.3); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy, R * 0.62, 0, Math.PI * 2); ctx.strokeStyle = alpha(C.text3, 0.12); ctx.stroke();
    const steps = spanH === 24 ? 24 : 7;
    ctx.font = '11px "Geist Mono", monospace'; ctx.textAlign = 'center'; ctx.fillStyle = C.text3;
    for (let i = 0; i < steps; i++) {
      const a = -Math.PI / 2 + (i / steps) * Math.PI * 2;
      const major = spanH === 24 ? i % 6 === 0 : true;
      ctx.strokeStyle = alpha(C.text3, major ? 0.5 : 0.2);
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * (R - (major ? 8 : 4)), cy + Math.sin(a) * (R - (major ? 8 : 4))); ctx.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); ctx.stroke();
      if (major) {
        const label = i === 0 ? '지금' : spanH === 24 ? `+${i}시간` : `+${i}일`;
        ctx.fillText(label, cx + Math.cos(a) * (R + 18), cy + Math.sin(a) * (R + 18) + 4);
      }
    }
    // 발표
    const meds = items.map((x) => x.med || 0);
    const maxMed = Math.max(0.2, ...meds);
    spots = [];
    items.filter((x) => x.ts >= now - 600 && x.ts <= end).forEach((x) => {
      const a = -Math.PI / 2 + ((x.ts - now) / (end - now)) * Math.PI * 2;
      const rr = x.level >= 3 ? R * 0.82 : R * 0.62;
      const px = cx + Math.cos(a) * rr, py = cy + Math.sin(a) * rr;
      const size = x.med ? 6 + 22 * Math.sqrt(x.med / maxMed) : 5;
      const c = x.level >= 3 ? C.accent : C.text3;
      ctx.fillStyle = alpha(c, x.med ? 0.22 : 0.12);
      ctx.strokeStyle = alpha(c, 0.9); ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(px, py, size, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      spots.push({ x: px, y: py, r: Math.max(size, 14), id: x.id });
    });
    // 지금 바늘
    ctx.strokeStyle = C.accent; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(cx, cy - R * 0.7); ctx.lineTo(cx, cy - R - 2); ctx.stroke();
    // 가운데: 다음 고위험 발표
    const next = items.filter((x) => x.ts > now).sort((a, b) => (b.level - a.level) || (a.ts - b.ts)).find((x) => x.level >= 3) || items.find((x) => x.ts > now);
    center.innerHTML = next
      ? `<p class="radar__k">다음 ${next.level >= 3 ? '고위험 ' : ''}발표</p><p class="radar__n">${esc(next.name)}</p><p class="radar__t">${hm(next.ts)} · ${left(next.ts - now)}</p>${next.med ? `<p class="radar__m">과거 1시간 중앙값 ±${next.med.toFixed(2)}%</p>` : ''}`
      : '<p class="radar__k">이 기간에 주요 발표가 없습니다</p>';
  }
  const resize = () => {
    W = box.clientWidth; H = W; dpr = Math.min(devicePixelRatio || 1, 2); // 좁은 화면에선 가운데 글이 판 아래로 빠져 상자가 정사각형이 아니다
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    draw();
  };
  new ResizeObserver(resize).observe(box);
  canvas.addEventListener('click', (e) => {
    const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    const hit = spots.find((s) => Math.hypot(s.x - x, s.y - y) <= s.r);
    if (!hit) return;
    const el = document.getElementById(hit.id);
    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.classList.add('is-flash'); setTimeout(() => el.classList.remove('is-flash'), 1200); }
  });
  canvas.addEventListener('mousemove', (e) => {
    const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    canvas.style.cursor = spots.some((s) => Math.hypot(s.x - x, s.y - y) <= s.r) ? 'pointer' : 'default';
  });
  $$('[data-span]').forEach((b) => b.addEventListener('click', () => {
    spanH = Number(b.dataset.span);
    $$('[data-span]').forEach((x) => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
    draw();
  }));
  setInterval(draw, 60000);
}

main();
