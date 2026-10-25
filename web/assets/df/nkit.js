// 다음 섹션(N3·N5) 공통: 렌더러, 화면에 보일 때만 그리기, 글꼴 준비, 캔버스 글자 줄바꿈
import * as THREE from 'three';
export const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
export const mobile = () => innerWidth < 900;
export const DPR = Math.min(devicePixelRatio || 1, 2);
const DK = document.documentElement.dataset.theme === 'dark';
export function renderer(canvas, clear = DK ? 0x0b1320 : 0xf7f9fc) {
  const r = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  r.setPixelRatio(Math.min(devicePixelRatio || 1, 2)); r.setClearColor(clear, 1); r.outputColorSpace = THREE.SRGBColorSpace;
  return r;
}
export function loop(el, r, scene, cam, tick, onSize) {
  let on = false, last = performance.now();
  new IntersectionObserver((e) => { on = e[0].isIntersecting; }, { rootMargin: '200px' }).observe(el);
  const size = () => { const w = el.clientWidth, h = el.clientHeight; r.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); onSize && onSize(w, h); };
  size(); addEventListener('resize', size);
  const D = window.__dfLoops && (window.__dfLoops[el.id || 'el'] = { on: false, frames: 0, calls: 0, points: 0, err: 0 });   // ?diag(첫 화면 진단)일 때만
  const f = (now) => { requestAnimationFrame(f); if (D) D.on = on; if (!on || document.hidden) { last = now; return; } const dt = Math.min(0.05, (now - last) / 1000); last = now; tick(now / 1000, dt); r.render(scene, cam);
    if (D) { D.frames++; D.calls = r.info.render.calls; D.points = r.info.render.points; if (D.frames % 60 === 1) D.err = r.getContext().getError(); } };
  requestAnimationFrame(f);
}
export const SANS = '"Pretendard Variable", Pretendard, system-ui, sans-serif', KSANS = '"Pretendard Variable", Pretendard, system-ui, sans-serif', MONO = '"JetBrains Mono", ui-monospace, monospace';
export async function fonts(text = '') {
  await Promise.all([document.fonts.load(`300 40px "Pretendard Variable"`), document.fonts.load(`600 40px "Pretendard Variable"`), document.fonts.load(`500 40px "Pretendard Variable"`, text || '가나다'), document.fonts.load(`400 20px "JetBrains Mono"`)].map((p) => p.catch(() => {})));
  await document.fonts.ready;
}
// 띄어쓰기 기준 줄바꿈(너무 긴 낱말은 글자 단위로), 최대 줄 수 넘으면 말줄임
export function wrap(ctx, text, maxW, maxLines = 3) {
  const out = []; let cur = '';
  const push = (w) => { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width <= maxW) { cur = t; return; } if (cur) out.push(cur); cur = '';
    if (ctx.measureText(w).width <= maxW) { cur = w; return; } let s = ''; for (const ch of w) { if (ctx.measureText(s + ch).width > maxW) { out.push(s); s = ''; } s += ch; } cur = s; };
  String(text || '').split(/\s+/).forEach(push); if (cur) out.push(cur);
  if (out.length > maxLines) { const l = out.slice(0, maxLines); let last = l[maxLines - 1]; while (last && ctx.measureText(last + '…').width > maxW) last = last.slice(0, -1); l[maxLines - 1] = last + '…'; return l; }
  return out;
}
export function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
export const lerp = (a, b, t) => a + (b - a) * t, clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x)), ss = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
export const KIND = { en: { event: 'Event', data: 'Data release', price_recap: 'Price move', opinion: 'Commentary' }, ko: { event: '사건', data: '지표 발표', price_recap: '시세 정리', opinion: '발언·의견' } };
export const SECT = { l1: ['Layer 1', '레이어1'], l2: ['Layer 2', '레이어2'], defi: ['DeFi', '디파이'], ai: ['AI', 'AI'], meme: ['Meme', '밈'], rwa: ['RWA', 'RWA·토큰화'], stable: ['Stablecoins', '스테이블코인'], exchange: ['Exchanges', '거래소'], gamefi: ['Gaming·NFT', '게임·NFT'], depin: ['DePIN', '디핀'], privacy: ['Privacy', '프라이버시'], infra: ['Infra', '인프라'], mining: ['Mining', '채굴'], prediction: ['Prediction', '예측시장'] };
export const EN = fetch((window.DF_BASE || '../') + 'en.json').then((r) => r.json()).catch(() => ({}));
