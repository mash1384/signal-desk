// P5 다음 장면 후보(?br=1~5): 줌 아웃 끝의 파형 입자가 전부 흩어졌다가 모여, AI 하루 정리(실제 최신 정리)를 전하는 모양이 된다.
// 1 목소리 파형 · 2 입자 헤드라인 · 3 네 갈래가 하나로 · 4 요약하는 구 · 5 입자로 짜인 한 장
import * as THREE from 'three';
import { Morph, COL, clamp, ss, sm, lerp, rnd, textPoints, drawPoints, rrEdge, project, fonts, T } from './pk.js';
import { wrap } from '../n/nkit.js';
import { makeGlobe } from './globe.js';

export const BR_NAMES = { 1: ['Voice wave', '목소리 파형'], 2: ['Particle headline', '입자 헤드라인'], 3: ['Four streams', '네 갈래가 하나로'], 4: ['World globe', '지구 요약'], 5: ['Woven brief', '입자로 짜인 한 장'] };
const CATS = [['crypto', 'Crypto', '크립토'], ['econ', 'Economy', '경제'], ['world', 'World', '세계정세'], ['ai', 'AI', 'AI 업계']];

export function makeBrief(kind, { scene, sec, lay, mob, sample }) {
  if (kind === 4) { const g = makeGlobe({ scene, sec, lay, mob });   // 4는 지구(테마별 AI 요약)
    g.sample = (mm, n) => { const s0 = sample(n); mm.set(0, (i, o) => { o[0] = s0.p[i * 3]; o[1] = s0.p[i * 3 + 1]; o[2] = s0.p[i * 3 + 2]; o[3] = s0.c[i * 4]; o[4] = s0.c[i * 4 + 1]; o[5] = s0.c[i * 4 + 2]; o[6] = s0.c[i * 4 + 3]; return o; }); };
    return g; }
  const N = mob ? 9000 : 16000, m = new Morph(N); m.points.visible = false; m.U.uBurst.value = mob ? 5 : 8; m.U.uWob.value = 0.02; scene.add(m.points);
  const L = () => DFI.lang() === 'ko';
  // ---------- HTML: AI 정리 카드 ----------
  const box = document.createElement('div'); box.className = 'brx brx-' + kind; lay.appendChild(box);
  const css = document.createElement('style'); css.textContent = `
  .brx{position:absolute;left:0;top:0;opacity:0;pointer-events:none;color:var(--ink)}
  .brx .k{display:flex;gap:8px;align-items:center;font-family:var(--mono);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--primary)}
  .brx .k i{font-style:normal;color:var(--mute);letter-spacing:.04em}
  .brx h3{margin-top:10px;font-size:clamp(24px,2.6vw,38px);font-weight:400;letter-spacing:-.035em;line-height:1.18}:lang(ko) .brx h3{font-weight:600;letter-spacing:-.03em}
  .brx .rv{margin-top:14px;font-size:16.5px;line-height:1.62;color:var(--ink2)}.brx .rv span{opacity:.12;transition:opacity 260ms ease}.brx .rv span.on{opacity:1}
  .brx .mt{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:16px;font-family:var(--mono);font-size:12px;color:var(--mute)}.brx .mt b{color:var(--ink);font-weight:600}
  .brx .fn{margin-top:12px;font-size:12px;color:var(--mute)}
  .brx.card{padding:24px 26px 22px;border-radius:22px;background:rgb(255 255 255/.9);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);box-shadow:0 30px 70px -30px rgb(13 37 61/.42),0 0 0 1px rgb(13 37 61/.06)}
  .brx.center{text-align:center}.brx.center .k,.brx.center .mt{justify-content:center}
  .brl{position:absolute;left:0;top:0;opacity:0;white-space:nowrap;font-size:13px;color:var(--ink2);transform:translate(-50%,-50%)}.brl b{font-weight:600;color:var(--ink);margin-right:6px}
  @media(max-width:899px){.brx .rv{font-size:15px}.brx-5 .rv{font-size:13.5px;line-height:1.5}.brx-5 h3{font-size:21px}.brx-5 .mt{display:none}.brx.card{padding:18px 18px 16px}.brl{font-size:11.5px}}`; document.head.appendChild(css);
  let D = null, sents = [], labels = [];
  const fill = () => { if (!D) return; const day = new Date(D.date + 'T00:00:00Z'), dl = L() ? `${day.getUTCMonth() + 1}월 ${day.getUTCDate()}일` : day.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
    const head = L() ? D.headline : (DFI.line({ id: 'brief:' + D.date }) || D.headline);
    sents = (D.review || '').split(/(?<=[.!?。])\s+/).filter(Boolean);
    const b = D.balance || {}, mk = D.market && D.market.btc;
    box.innerHTML = `<p class="k">${T('AI daily brief', 'AI 하루 정리')}<i>· ${dl}</i></p><h3>${DFD.esc(head)}</h3><p class="rv">${sents.map((s) => `<span>${DFD.esc(s)}</span>`).join(' ')}</p>
      <p class="mt"><span><b>${(D.counts || {}).stories || '–'}</b> ${T('stories', '건')}</span><span class="up">${T('bullish', '호재')} <b class="up">${b['호재'] || 0}</b></span><span class="down">${T('bearish', '악재')} <b class="down">${b['악재'] || 0}</b></span>${mk ? `<span>BTC <b class="${mk.chg >= 0 ? 'up' : 'down'}">${mk.chg >= 0 ? '+' : '−'}${Math.abs(mk.chg).toFixed(2)}%</b></span>` : ''}</p>
      <p class="fn">${T('Written by AI from the day\'s judged news. Numbers are counted by software. Not investment advice.', '그날 판정한 소식을 바탕으로 AI가 썼어요. 숫자는 프로그램이 셌어요. 투자 조언이 아니에요.')}</p>`;
    labels.forEach((e, i) => { const c = CATS[i], s = (D.by_cat || {})[c[0]] || { n: 0 }; e.innerHTML = `<b>${L() ? c[2] : c[1]}</b>${s.n || 0}${T('', '건')} · <span class="up">${s['호재'] || 0}↑</span> <span class="down">${s['악재'] || 0}↓</span>`; }); };
  if (kind === 3 || kind === 5) labels = CATS.map(() => { const e = document.createElement('div'); e.className = 'brl'; lay.appendChild(e); return e; });
  DFI.onLang(() => { fill(); if (kind === 2 && D) buildHeadline(); });
  // ---------- 모양(stage 1) ----------
  const U0 = new Float32Array(N), U1 = new Float32Array(N), U2 = new Float32Array(N); for (let i = 0; i < N; i++) { U0[i] = Math.random(); U1[i] = Math.random(); U2[i] = Math.random(); }
  const W = mob ? 3.3 : 7.2, tmp = new THREE.Color();
  let balU = 0.5; const catOf = (i) => { if (!D) return 0; const ns = CATS.map((c) => ((D.by_cat || {})[c[0]] || { n: 0 }).n || 0), tot = ns.reduce((a, b) => a + b, 0) || 1; let q = U2[i] * tot; for (let k = 0; k < 4; k++) { if (q < ns[k]) return k; q -= ns[k]; } return 3; };
  const catBal = (k) => { const s = (D && D.by_cat || {})[CATS[k][0]] || {}; return (s['호재'] || 0) / Math.max(1, (s['호재'] || 0) + (s['악재'] || 0)); };
  let speak = 0;
  const shapes = {
    1: (i, o, t) => { // 목소리 파형: 세 겹 사인파 + 가장자리로 갈수록 잦아드는 포락선
      const layer = i % 3, x = (U0[i] * 2 - 1) * W, env = Math.exp(-(((x / W) * 1.7) ** 2)), amp = (mob ? 0.95 : 1.35) * (0.55 + 0.45 * speak);
      const f = [1.1, 1.7, 2.6][layer] / (mob ? 0.6 : 1), sp = [1.6, -2.1, 2.8][layer], ph = [0, 1.7, 3.4][layer];
      let y = env * amp * Math.sin(x * f + t * sp + ph) * (layer === 2 ? 0.6 : 1); const spark = U1[i] < 0.18;
      if (spark) y += (U2[i] - 0.5) * env * amp * 2.2; else y += (U2[i] - 0.5) * 0.05;
      const c = U1[i] > 0.9 ? (U2[i] < balU ? COL.up : COL.dn) : [COL.ind, COL.navy, COL.lt][layer];
      o[0] = x; o[1] = y + (mob ? 2.4 : 1.5); o[2] = (U2[i] - 0.5) * 0.4; o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = spark ? 0.35 : 0.85; return o; },
    3: (i, o, t) => { // 네 갈래: 분야별 흐름이 흘러와 한 점에서 합쳐진다(두께=소식 수, 색=호재·악재)
      const k = catOf(i), core = U1[i] < 0.12, M = mob ? new THREE.Vector2(0, 2.3) : new THREE.Vector2(-0.2, 0.2);
      if (core) { const a = U0[i] * 6.283 + t * (0.6 + U2[i]), r = 0.15 + Math.pow(U2[i], 2) * (mob ? 0.6 : 0.75); tmp.copy(COL.ind).lerp(COL.lt, U2[i]);
        o[0] = M.x + Math.cos(a) * r; o[1] = M.y + Math.sin(a) * r * 0.9; o[2] = rnd(0.2); o[3] = tmp.r; o[4] = tmp.g; o[5] = tmp.b; o[6] = 0.9; return o; }
      const s = (U0[i] + t * 0.07 * (0.7 + U2[i] * 0.6)) % 1, ns = ((D && D.by_cat || {})[CATS[k][0]] || { n: 1 }).n || 1, wid = 0.12 + 0.55 * Math.sqrt(ns / 200);
      let S, C1, C2; if (mob) { const xs = [-2.6, -0.87, 0.87, 2.6][k]; S = [xs, 6.8]; C1 = [xs, 5.0]; C2 = [xs * 0.25, 3.3]; } else { const ys = [2.7, 0.9, -0.9, -2.7][k]; S = [-9.5, ys]; C1 = [-5.6, ys]; C2 = [-2.6, ys * 0.25]; }
      const u = 1 - s, bx = u * u * u * S[0] + 3 * u * u * s * C1[0] + 3 * u * s * s * C2[0] + s * s * s * M.x, by = u * u * u * S[1] + 3 * u * u * s * C1[1] + 3 * u * s * s * C2[1] + s * s * s * M.y;
      const off = (U1[i] - 0.5) * 2 * wid * (1 - s * 0.85), g = Math.exp(-(((U1[i] - 0.5) * 3) ** 2));
      tmp.copy(COL.navy).lerp(COL.dn, (1 - catBal(k)) * 0.75).lerp(COL.up, catBal(k) * 0.75 * (U2[i] < catBal(k) ? 1 : 0.2));
      if (mob) { o[0] = bx + off; o[1] = by; } else { o[0] = bx; o[1] = by + off; } o[2] = rnd(0.15); o[3] = tmp.r; o[4] = tmp.g; o[5] = tmp.b; o[6] = 0.35 + 0.6 * g * Math.min(1, s * 4); return o; },
    4: (i, o, t) => { // 요약하는 구: 표면이 말하듯 물결치는 구 + 분야 고리 네 개
      const C = mob ? new THREE.Vector3(0, 2.6, 0) : new THREE.Vector3(-3.6, 0.1, 0), R = mob ? 1.75 : 2.35;
      if (U1[i] < 0.24) { const k = Math.floor(U1[i] / 0.06), a = U0[i] * 6.283 + t * (0.25 + k * 0.08) * (k % 2 ? -1 : 1), rr = R * (1.42 + k * 0.13), tl = [0.35, -0.5, 0.9, -1.15][k];
        let x = Math.cos(a) * rr, z = Math.sin(a) * rr, y = (U2[i] - 0.5) * 0.04; const y2 = y * Math.cos(tl) - z * Math.sin(tl), z2 = y * Math.sin(tl) + z * Math.cos(tl);
        tmp.copy(COL.lt).lerp(catBal(k) >= 0.5 ? COL.up : COL.dn, 0.35); o[0] = C.x + x; o[1] = C.y + y2; o[2] = C.z + z2; o[3] = tmp.r; o[4] = tmp.g; o[5] = tmp.b; o[6] = 0.45; return o; }
      const th = U0[i] * 6.283, ph = Math.acos(U2[i] * 2 - 1), d = 1 + 0.07 * Math.sin(3 * th + t * 1.2) * Math.sin(4 * ph - t) + speak * 0.06 * Math.sin(9 * th + t * 5) * Math.sin(6 * ph);
      const rot = t * 0.15, x0 = Math.sin(ph) * Math.cos(th), z0 = Math.sin(ph) * Math.sin(th), x = x0 * Math.cos(rot) - z0 * Math.sin(rot), z = x0 * Math.sin(rot) + z0 * Math.cos(rot);
      const patch = Math.sin(2 * th + ph * 3); tmp.copy(COL.navy).lerp(COL.ind, 0.5 + 0.5 * Math.cos(ph * 2)); if (patch > 0.55) tmp.lerp(U1[i] < 0.24 + balU * 0.76 ? COL.up : COL.dn, 0.55);
      o[0] = C.x + x * R * d; o[1] = C.y + Math.cos(ph) * R * d; o[2] = C.z + z * R * d; o[3] = tmp.r; o[4] = tmp.g; o[5] = tmp.b; o[6] = 0.35 + 0.55 * (0.5 + 0.5 * z); return o; },
  };
  // 2 · 입자 헤드라인(정적), 5 · 입자 카드(정적)는 한 번만 짓는다
  let HL = null;
  function buildHeadline() {
    const g = document.createElement('canvas').getContext('2d'), font = `700 120px "Pretendard Variable", Pretendard, Inter, sans-serif`; g.font = font;
    const head = L() ? D.headline : (DFI.line({ id: 'brief:' + D.date }) || D.headline), lines = wrap(g, head, mob ? 720 : 1500, 4);
    const pts = textPoints(lines.join('\n'), { font, hgt: 1, step: mob ? 4 : 3 }), ratio = pts.W / pts.H, hgt = Math.min(mob ? 4.2 : 3.6, (mob ? 6.4 : 14) / ratio), M = pts.length;
    m.set(1, (i, o) => { const p = pts[i % M], c = i % 7 === 0 ? COL.ind : COL.ink, dust = i >= M * 2;
      o[0] = p.x * hgt + rnd(0.01) + (dust ? rnd(1.5) : 0); o[1] = p.y * hgt + (mob ? 2.9 : 1.6) + (dust ? rnd(0.8) : 0); o[2] = rnd(dust ? 0.6 : 0.12); o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = dust ? 0.12 : 0.95; return o; });
    HL = { hgt, h: pts.H * hgt };
  }
  const CW = mob ? 7.4 : 9.6, CH = mob ? 13 : 5.8, BARX = mob ? -CW / 2 + 0.5 : CW / 2 - 4.1, BARW = mob ? CW - 1.0 : 3.6, barY = (k) => mob ? -CH / 2 + 0.55 + (3 - k) * 0.62 : CH / 2 - 1.5 - k * 0.95;
  function buildCard() {
    const ns = CATS.map((c) => ((D.by_cat || {})[c[0]] || { n: 0 }).n || 0), mx = Math.max(1, ...ns);
    m.set(1, (i, o) => { const q = U0[i]; let x, y, c = COL.ink, a = 0.88, z = rnd(0.04);
      if (q < 0.42) { const [ex, ey] = rrEdge(U1[i], CW, CH, 0.36); x = ex; y = ey; c = U2[i] < 0.12 ? COL.ind : COL.ink; }
      else if (q < 0.47) { x = -CW / 2 + 0.5 + U1[i] * (mob ? CW - 1 : CW * 0.44); y = CH / 2 - 0.62; c = COL.ind; a = 0.9; }   // 머리 아래 줄
      else if (q < 0.78) { const k = Math.min(3, Math.floor((q - 0.47) / 0.31 * 4)), s = ((D.by_cat || {})[CATS[k][0]] || {}), len = BARW * ns[k] / mx, bu = (s['호재'] || 0) / Math.max(1, (s['호재'] || 0) + (s['악재'] || 0));
        const f = U1[i]; x = BARX + f * len; y = barY(k) + (U2[i] - 0.5) * 0.16; c = f < bu ? COL.up : COL.dn; a = 0.92; }
      else { x = rnd(CW / 2 - 0.15); y = rnd(CH / 2 - 0.15); c = COL.lt; a = 0.12; z = rnd(0.2) - 0.1; }
      o[0] = x; o[1] = y; o[2] = z; o[3] = c.r; o[4] = c.g; o[5] = c.b; o[6] = a; return o; });
  }
  // 시작 모양(stage 0): 지금 화면의 파형 입자 그대로
  let primed = false;
  function prime() { const sm0 = sample(N); m.set(0, (i, o) => { o[0] = sm0.p[i * 3]; o[1] = sm0.p[i * 3 + 1]; o[2] = sm0.p[i * 3 + 2]; o[3] = sm0.c[i * 4]; o[4] = sm0.c[i * 4 + 1]; o[5] = sm0.c[i * 4 + 2]; o[6] = sm0.c[i * 4 + 3]; return o; }); primed = true; }
  // 가장 최근 하루 정리(최대 6일 전까지 거슬러 찾는다)
  const latest = async () => { for (let k = 0; k < 6; k++) { const r = await fetch(`https://raw.githubusercontent.com/mash1384/signal-desk/flash/daily/${new Date(Date.now() - k * 864e5).toISOString().slice(0, 10)}.json`).catch(() => null); if (r && r.ok) return r.json(); } throw 0; };
  latest().then(async (d) => { D = d; const b = d.balance || {}; balU = (b['호재'] || 0) / Math.max(1, (b['호재'] || 0) + (b['악재'] || 0)); await fonts(d.headline); fill();
    if (kind === 2) buildHeadline(); if (kind === 5) buildCard(); }).catch(() => {});
  // ---------- 매 프레임 ----------
  const camP = mob ? new THREE.Vector3(0, 0.6, 21) : new THREE.Vector3(0, 0.2, 15.5), camL = mob ? new THREE.Vector3(0, 0.6, 0) : new THREE.Vector3(0, 0, 0), v = new THREE.Vector3(), lk = new THREE.Vector3();
  return {
    update(BP, t, cam, look, hide) {
      if (BP <= 0 || !D) { m.points.visible = false; box.style.opacity = 0; labels.forEach((e) => (e.style.opacity = 0)); return 0; }
      if (!primed) prime(); m.points.visible = true;
      const go = sm(clamp(BP / 0.26)); hide(go);   // 첫 프레임부터 원래 파형은 숨기고 같은 자리의 입자로 바꿔 탄다
      // 말하는 중(문장이 켜지는 순간) 진폭이 커진다
      const rv = clamp((BP - 0.36) / 0.48), si = Math.floor(rv * sents.length), fr = rv * sents.length - si; speak = BP > 0.3 && rv < 1 ? 0.35 + 0.65 * Math.abs(Math.sin(t * 6.5)) * (1 - fr * 0.6) : 0.15;
      if (shapes[kind]) m.set(1, (i, o) => shapes[kind](i, o, t));
      m.U.uS.value = go; m.U.uT.value = t; m.U.uA.value = 1 - ss(0.95, 1, BP) * 0.6;
      // 카메라: 들판 위 → 정면
      v.copy(cam.position).lerp(camP, go); cam.position.copy(v); lk.copy(look).lerp(camL, go); cam.lookAt(lk); cam.updateMatrixWorld();
      // 글
      const w = sec.clientWidth, h = sec.clientHeight, show = ss(0.26, 0.34, BP) * (1 - ss(0.93, 0.97, BP));
      box.querySelectorAll('.rv span').forEach((e, j) => e.classList.toggle('on', j < rv * sents.length + 0.05));
      let x, y, bw;
      if (kind === 1 || kind === 2) { bw = Math.min(mob ? w - 36 : 760, w - 36); box.className = 'brx brx-' + kind + ' center'; x = (w - bw) / 2; const hh = box.querySelector('h3'); if (hh) hh.style.display = kind === 2 ? 'none' : '';
        v.set(0, kind === 1 ? (mob ? 2.4 : 1.5) - (mob ? 1.3 : 1.7) : (mob ? 2.9 : 1.6) - (HL ? HL.h / 2 : 1) - 0.35, 0); y = project(cam, sec, v)[1] + 10; }
      else if (kind === 3 || kind === 4) { box.className = 'brx brx-' + kind + ' card'; bw = mob ? w - 32 : Math.min(470, w * 0.36);
        if (mob) { x = 16; v.set(0, kind === 3 ? 2.3 - 0.9 : 2.6 - 2.4, 0); y = project(cam, sec, v)[1] + 8; } else { v.set(kind === 3 ? 1.2 : 0.4, 2.3, 0); const pp = project(cam, sec, v); x = Math.min(pp[0], w - bw - 40); y = pp[1]; } }
      else { box.className = 'brx brx-5'; const a = project(cam, sec, v.set(-CW / 2 + 0.5, CH / 2 - 0.22, 0)), b = project(cam, sec, v.set(mob ? CW / 2 - 0.5 : -CW / 2 + 0.5 + CW * 0.44, 0, 0)); x = a[0]; y = a[1]; bw = b[0] - a[0]; }
      box.style.width = bw + 'px'; box.style.transform = `translate(${x}px,${y + (1 - show) * 18}px)`; box.style.opacity = show;
      if (kind === 5) box.querySelector('.fn') && (box.querySelector('.fn').style.display = 'none');
      labels.forEach((e, k) => { if (kind === 3) { v.set(...(mob ? [[-2.6, -0.87, 0.87, 2.6][k], 7.4, 0] : [-9.3, [2.7, 0.9, -0.9, -2.7][k] + 0.55, 0])); } else { v.set(BARX, barY(k) + 0.3, 0); }
        const [lx, ly] = project(cam, sec, v); e.style.transform = kind === 5 ? `translate(${lx}px,${ly}px) translate(0,-50%)` : `translate(${lx}px,${ly}px) translate(${mob ? '-50%' : '0'},-50%)`;
        e.style.opacity = show; if (mob && kind === 3) e.style.whiteSpace = 'normal', e.style.width = '80px', e.style.textAlign = 'center'; });
      return go;
    },
  };
}
