const C = new Map(), sm = (a, b, t) => Math.max(0, Math.min(1, (t - a) / (b - a)));
export function load(id) {
  if (!C.has(id)) C.set(id, fetch(new URL('../art/' + id + '.bin', import.meta.url)).then((r) => r.arrayBuffer()).then((b) => {
    const d = new DataView(b), w = d.getUint8(2), h = d.getUint8(3), n = d.getUint16(6, true), px = new Uint8Array(w * h), raw = new Uint8Array(b, 8 + n);
    for (let i = 0; i < w * h; i++) px[i] = i & 1 ? raw[i >> 1] & 15 : raw[i >> 1] >> 4;
    return { w, h, f: d.getUint8(4), y: d.getUint8(5) / 100, cr: JSON.parse(new TextDecoder().decode(new Uint8Array(b, 8, n))), px };
  }));
  return C.get(id);
}
export function clear(host) { host.querySelectorAll(':scope > .art, :scope > .art-cr').forEach((e) => e.remove()); host.classList.remove('has-art'); }
export function paint(host, z, m, o = {}) {
  clear(host);
  const W = host.clientWidth, H = host.clientHeight, dpr = Math.min(devicePixelRatio, 2), cv = document.createElement('canvas');
  if (!W || !H || z.x1 - z.x0 < 40 || z.y1 - z.y0 < 40) return;
  const X = o.grid ? 0 : z.x0, Y = o.grid ? 0 : z.y0, CW = o.grid ? W : z.x1 - z.x0, CH = o.grid ? H : z.y1 - z.y0;   // 격자가 없으면 그림 칸만큼만
  cv.className = 'art'; cv.setAttribute('aria-hidden', 'true'); cv.width = CW * dpr; cv.height = CH * dpr; cv.style.cssText = `left:${X}px;top:${Y}px;width:${CW}px;height:${CH}px`;
  const g = cv.getContext('2d'), dk = document.documentElement.dataset.theme === 'dark', ink = (getComputedStyle(o.ink || host).color.match(/\d+/g) || [13, 37, 61]).slice(0, 3).join(',');
  g.scale(dpr, dpr); g.translate(-X, -Y);
  const under = o.u ? o.u(host, z) : () => 0;   // 글씨 자리(artm.js under, 큰 소식만)
  const dot = (x, y, r, a) => { g.fillStyle = `rgba(${ink},${a})`; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); };
  const base = dk ? 0.09 : 0.08;
  if (o.grid) for (let y = 5; y < H; y += 10) for (let x = 5; x < W; x += 10) if (x < z.x0 || x > z.x1 || y < z.y0 || y > z.y1) dot(x, y, 0.9, base);
  const sub = m.f & 2 ? 1 : 2, sc = 10 / sub, cols = Math.floor((z.x1 - z.x0) / sc), rows = Math.floor((z.y1 - z.y0) / sc), [a, b, c, d] = o.e || [sub > 1 ? 0.42 : 0.12, 0.9, 0.1, 0.85];
  const fit = m.f & 1 || (m.h > m.w * 1.1 && cols > rows * 1.6);   // 로고 · 지구, 그리고 세로 사진을 가로로 긴 띠에 넣을 때는 자르지 않고 통째로
  const k = fit ? Math.min(cols / m.w, rows / m.h) : Math.max(cols / m.w, rows / m.h), ox = (m.w - cols / k) / 2, oy = (m.h - rows / k) * (fit ? 0.5 : m.y);
  for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
    const fx = (x + 0.5) / cols, fy = (y + 0.5) / rows, px = z.x0 + (x + 0.5) * sc, py = z.y0 + (y + 0.5) * sc, sx = Math.floor(ox + (x + 0.5) / k), sy = Math.floor(oy + (y + 0.5) / k);
    const e = sm(0, a, fx) ** 1.4 * sm(1, b, fx) * sm(0, c, fy) * sm(1, d, fy);
    const v = (sx < 0 || sy < 0 || sx >= m.w || sy >= m.h ? 0 : (m.px[sy * m.w + sx] / 15) ** 1.3) * e * (1 - 0.45 * under(px, py));
    const on = x % sub === sub >> 1 && y % sub === sub >> 1, b0 = on ? 0.9 : 0, r = b0 + v * (sc * (sub > 1 ? 0.46 : 0.4) - b0);
    if (r < 0.35) continue;
    dot(px, py, r, on && v < 0.02 ? base * (o.grid ? 1 : e) : base + (sub > 1 ? 0.03 + v * 0.41 : v * 0.3));
  }
  host.classList.add('has-art'); host.prepend(cv);
  if (m.cr.length) {
    const p = document.createElement('p');
    p.className = 'art-cr'; p.style.cssText = `right:${W - z.x1 + 10}px;top:${z.y1 - 22}px`; p.append(window.DFI && DFI.lang() !== 'ko' ? 'Photo ' : '사진 ');
    m.cr.forEach(([t, u], i) => p.append(i ? ' · ' : '', Object.assign(document.createElement('a'), { href: u, target: '_blank', rel: 'noopener', textContent: t })));
    host.append(p);
  }
}
export function watch(f) {
  let t; const go = () => { clearTimeout(t); t = setTimeout(f, 150); };
  new MutationObserver(go).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'lang'] }); addEventListener('resize', go);
}
