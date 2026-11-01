// 소식 그림 고르기 — pipeline/art.py 와 같은 규칙(같은 예시로 tests/unit/test_art.py 가 두 쪽을 맞춰 본다)
const TAIL = '은는이가을를의에와과도만로서까부엔값산발측', HAN = /[가-힣]/, AN = /[A-Za-z0-9]/;
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
export function find(text, name, nots = []) {
  if (!text || !name) return -1;
  const ascii = /^[ -~]*$/.test(name), re = new RegExp(esc(name), (ascii && name.toUpperCase() !== name) ? 'gi' : 'g');
  for (let m; (m = re.exec(text));) {
    const a = m.index, b = a + m[0].length, p = text[a - 1] || '', n = text[b] || '';
    re.lastIndex = a + 1;
    if (ascii) { if ((p && AN.test(p)) || (n && AN.test(n))) continue; }
    else if ([...name].length <= 2 && (HAN.test(p) || (HAN.test(n) && !TAIL.includes(n)))) continue;
    if (nots.some((w) => text.slice(b).trimStart().startsWith(w))) continue;
    return a;
  }
  return -1;
}
export function entity(ix, ko = '', en = '') {
  let best = null;
  ix.e.forEach(([, kos, ens, pr, , nots = []], i) => kos.concat(ens).forEach((nm) => {
    let p = find(ko, nm, nots);
    if (p < 0) { p = find(en, nm, nots); p = p >= 0 ? p + ko.length + 1 : -1; }
    if (p < 0) return;
    const k = [-pr, p, -nm.length];
    if (!best || k[0] < best[0][0] || (k[0] === best[0][0] && (k[1] < best[0][1] || (k[1] === best[0][1] && k[2] < best[0][2])))) best = [k, i];
  }));
  return best ? best[1] : null;
}
export function seed(id) { let h = 2166136261; for (const c of new TextEncoder().encode(String(id))) h = Math.imul(h ^ c, 16777619) >>> 0; return h; }
export function pick(ix, ko, en = '', coins = [], id = '', avoid = []) {
  let i = entity(ix, ko, en);
  if (i == null) for (const c of coins || []) { const j = ix.sym[String(c).toUpperCase()]; if (j != null) { i = j; break; } }
  const ids = (i != null && ix.e[i][4].length) ? ix.e[i][4] : ix.fb, n = ids.length, s = seed(id);
  for (let k = 0; k < n; k++) { const x = ids[(s + k) % n]; if (!avoid.includes(x)) return x; }
  return ids[s % n];
}
let IX;
export const index = () => (IX ||= fetch(new URL('./art.json' + new URL(import.meta.url).search, import.meta.url)).then((r) => r.json()));
// 글씨 자리(그림 칸 근처 글자 줄) → 점을 옅게 할 정도(0~1, 22px 안에서 줄어듦) — 큰 소식 카드처럼 글과 그림이 겹치는 곳만 쓴다
export function under(host, z) {
  const r0 = host.getBoundingClientRect(), bx = [], tw = document.createTreeWalker(host, 4);
  while (tw.nextNode()) { const t = tw.currentNode; if (!t.textContent.trim()) continue; const rg = document.createRange(); rg.selectNodeContents(t);
    for (const q of rg.getClientRects()) { const b = [q.left - r0.left - 8, q.top - r0.top - 5, q.right - r0.left + 8, q.bottom - r0.top + 5]; if (b[2] > z.x0 - 22 && b[0] < z.x1 + 22 && b[3] > z.y0 - 22 && b[1] < z.y1 + 22) bx.push(b); } }
  return (x, y) => { let u = 0; for (const b of bx) u = Math.max(u, 1 - Math.min(1, Math.hypot(Math.max(b[0] - x, 0, x - b[2]), Math.max(b[1] - y, 0, y - b[3])) / 22)); return u; };
}
