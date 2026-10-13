// 코인 페이지: 24시간 가격(바이낸스 15분봉)과 그 위에 이 코인 속보가 나온 때, 이 코인 속보 목록.
const DF = window.DF;
const $ = (s) => document.querySelector(s);
const box = $('#cpChart');
const SYM = box.dataset.sym;
const HOSTS = ['https://data-api.binance.vision', 'https://api.binance.com'];
let K = null, F = [];

async function klines() {
  for (const h of HOSTS) {
    try {
      const r = await fetch(`${h}/api/v3/klines?symbol=${SYM}USDT&interval=15m&limit=96`);
      if (r.ok) return (await r.json()).map((k) => [k[0] / 1000, +k[4]]);
    } catch (e) { /* 다음 주소로 */ }
  }
  return null;
}

function draw() {
  if (!K || !K.length) { box.innerHTML = '<p class="fl-empty">가격을 불러오지 못했어요.</p>'; return; }
  const W = box.clientWidth, H = box.clientHeight, m = { l: 0, r: 56, t: 10, b: 22 };
  const t0 = K[0][0], t1 = K[K.length - 1][0];
  const ps = K.map((k) => k[1]), lo = Math.min(...ps), hi = Math.max(...ps), pad = (hi - lo) * 0.08 || hi * 0.01;
  const xs = (t) => m.l + ((t - t0) / (t1 - t0)) * (W - m.l - m.r);
  const ys = (p) => m.t + (1 - (p - (lo - pad)) / (hi - lo + 2 * pad)) * (H - m.t - m.b);
  const line = K.map((k, i) => `${i ? 'L' : 'M'}${xs(k[0]).toFixed(1)},${ys(k[1]).toFixed(1)}`).join('');
  const area = `${line}L${xs(t1).toFixed(1)},${H - m.b}L${xs(t0).toFixed(1)},${H - m.b}Z`;
  const at = (t) => { let j = K.findIndex((k) => k[0] >= t); if (j < 0) j = K.length - 1; return K[j][1]; };
  const marks = F.filter((it) => it.t >= t0 && it.t <= t1 + 900).map((it) => {
    const c = it.v === '호재' ? 'up' : it.v === '악재' ? 'down' : 'flat';
    return `<circle class="mk ${c}" cx="${xs(Math.min(it.t, t1)).toFixed(1)}" cy="${ys(at(it.t)).toFixed(1)}" r="5"><title>${DF.esc(it.v + ' · ' + it.ko)}</title></circle>`;
  }).join('');
  const fmt = (t) => new Date(t * 1000).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false });
  box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true"><path class="ar-fill" d="${area}"/><path class="ln" d="${line}"/>${marks}
    <text class="ax" x="${W - m.r + 8}" y="${ys(hi) + 4}">${DF.money(hi)}</text><text class="ax" x="${W - m.r + 8}" y="${ys(lo) + 4}">${DF.money(lo)}</text>
    <text class="ax" x="0" y="${H - 4}">${fmt(t0)}</text><text class="ax" x="${W - m.r}" y="${H - 4}" text-anchor="end">지금</text></svg>`;
}

DF.onFlash((d) => {
  const list = $('#coinFlash');
  if (!d) { list.innerHTML = '<li class="fl-empty">지금은 속보를 불러올 수 없어요.</li>'; return; }
  F = d.items.filter((it) => it.coins.includes(SYM));
  list.innerHTML = F.length ? F.slice(0, 20).map((it) => DF.fi(it)).join('') : '<li class="fl-empty">최근 이틀 동안 이 코인을 다룬 속보가 없었어요.</li>';
  draw();
});
klines().then((k) => { K = k; draw(); });
let raf;
addEventListener('resize', () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); });
setInterval(() => { if (!document.hidden) klines().then((k) => { if (k) { K = k; draw(); } }); }, 60000);
