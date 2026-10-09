// 맵(SIGNAL Map): 코인은 원, 뉴스는 분야 출발점에서 날아와 부딪히는 빛, 잰 반응은 파문.
// data/map.json(15분마다 갱신)을 1분마다 다시 읽고, 코인 가격은 바이낸스 공개 실시간 시세로 갱신한다.
// 아래 시간 막대로 지난 7일을 다시 볼 수 있다. 같은 내용을 '목록으로 보기'에서 표로도 볼 수 있다.
const S = window.SIGNAL || {};
const BASE = S.base || '/';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const WIN = { '1h': 3600, '6h': 21600, '24h': 86400, '7d': 604800 };
const WIN_KO = { '1h': '1시간', '6h': '6시간', '24h': '24시간', '7d': '7일' };
const CAT = { crypto: '크립토', ai: 'AI', macro: '매크로' };
const ETYPE = { fomc: 'FOMC·연준', cpi: '물가 지표', jobs: '고용 지표', etf: 'ETF', listing: '상장·상폐', hack: '해킹·사고',
  regulation: '규제·소송', 'ai-model': 'AI 모델·제품', earnings: '실적', other: '기타' };
const GRADE_OK = { all: () => true, mid: (g) => g === '중' || g === '강', strong: (g) => g === '강' };
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pct = (v, d = 2) => (v == null || !isFinite(v) ? '–' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d) + '%');
const two = (n) => (n < 10 ? '0' : '') + n;
const kst = (ts) => { const d = new Date((ts + 9 * 3600) * 1000); return { mo: d.getUTCMonth() + 1, d: d.getUTCDate(), h: d.getUTCHours(), m: d.getUTCMinutes() }; };
const when = (ts) => { const k = kst(ts); return `${two(k.mo)}.${two(k.d)} ${two(k.h)}:${two(k.m)}`; };
const nowSec = () => Date.now() / 1000;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const hitR = (h) => (h['1h'] != null ? h['1h'] : h['15m'] != null ? h['15m'] : h['24h']);

function main() {
  const root = $('#mapx');
  if (!root) return;
  const stage = $('#mapStage'), canvas = $('#mapCanvas'), ctx = canvas.getContext('2d');
  const panel = $('#mapPanel'), range = $('#mapRange'), clock = $('#mapClock');
  const playBtn = $('#mapPlay'), speedBtn = $('#mapSpeed'), liveBtn = $('#mapLive');
  let data = null, W = 0, H = 0, dpr = 1, raf = 0, lastFrame = 0;
  const view = { win: '24h', cats: new Set(['crypto', 'ai', 'macro']), grade: 'all', t: nowSec(), live: true, playing: false, speed: 1, sel: null };
  const live = {};            // sym -> {price, chg24}
  const flights = [];         // 날아가는 뉴스 빛
  const bursts = [];          // 부딪힌 순간의 파문
  let seen = new Set();       // 이미 날려 보낸 뉴스 id
  let geo = null;             // 화면 좌표
  let watch = [];
  try { watch = JSON.parse(localStorage.getItem('signal-watch')) || []; } catch (e) { watch = []; }

  const css = getComputedStyle(document.documentElement);
  const col = (name) => css.getPropertyValue(name).trim() || '#888';
  let C = {};
  const readColors = () => { C = { up: col('--up'), down: col('--down'), text: col('--text'), text2: col('--text-2'), text3: col('--text-3'), line: col('--line-strong'), accent: col('--accent'), bg: col('--bg'), elev: col('--bg-elev') }; };
  readColors();
  new MutationObserver(() => { readColors(); draw(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  const alpha = (c, a) => {
    if (c.startsWith('oklch(')) return c.includes('/') ? c.replace(/\/\s*[\d.]+\s*\)$/, `/ ${a})`) : c.replace(/\)$/, ` / ${a})`);
    if (c.startsWith('#') && c.length === 7) return c + Math.round(clamp(a, 0, 1) * 255).toString(16).padStart(2, '0');
    return c;
  };

  // ---------- 데이터 ----------
  const assets = () => (data ? data.assets.filter((a) => a.pos) : []);
  const bySym = (s) => assets().find((a) => a.s === s);
  const priceAt = (a, t) => {
    if (view.live && Math.abs(t - nowSec()) < 120 && live[a.s]) return live[a.s].price;
    const cl = a.closes || [];
    let p = null;
    for (let i = cl.length - 1; i >= 0; i--) { if (cl[i][0] + 3600 <= t) { p = cl[i][1]; break; } }
    if (p == null && t >= (data.at - 3600)) p = a.price;
    return p;
  };
  const chgAt = (a, t) => {
    if (view.win === '24h' && view.live && Math.abs(t - nowSec()) < 120) return live[a.s] ? live[a.s].chg24 : a.chg['24h'];
    if (view.live && Math.abs(t - nowSec()) < 120 && !live[a.s]) return a.chg[view.win];
    const p1 = priceAt(a, t), p0 = priceAt(a, t - WIN[view.win]);
    return p1 && p0 ? (p1 / p0 - 1) * 100 : a.chg[view.win];
  };
  // 뉴스는 시각 순으로 정렬돼 있어, 창의 양 끝을 이분 탐색으로 찾고 결과를 같은 조건이면 다시 쓴다
  const lowerBound = (t) => { let lo = 0, hi = data.news.length; while (lo < hi) { const m = (lo + hi) >> 1; if (data.news[m].t < t) lo = m + 1; else hi = m; } return lo; };
  let visKey = '', visVal = [];
  const visibleNews = () => {
    if (!data) return [];
    const t = Math.floor(view.t / 30) * 30;
    const key = t + '|' + view.win + '|' + [...view.cats].join(',') + '|' + view.grade + '|' + data.at;
    if (key === visKey) return visVal;
    const w = WIN[view.win], ok = GRADE_OK[view.grade];
    const out = [];
    for (let i = lowerBound(t - w), n = data.news.length; i < n; i++) {
      const x = data.news[i];
      if (x.t > t) break;
      if (view.cats.has(x.c) && (x.p ? view.grade === 'all' : x.h.some((h) => ok(h.g)))) out.push(x);
    }
    visKey = key; visVal = out;
    return out;
  };
  const maxZ = (n) => n.h.reduce((m, h) => Math.max(m, Math.abs(h.z || 0)), 0);

  // ---------- 좌표 ----------
  const layoutGeo = () => {
    const narrow = W < 640;
    const R = narrow ? Math.min(W * 0.43, H * 0.38) : Math.min(W * 0.36, H * 0.4);
    const cx = W / 2, cy = narrow ? H * 0.52 : H / 2;
    const hubs = narrow
      ? { crypto: { x: W * 0.13, y: H * 0.07 }, ai: { x: W * 0.87, y: H * 0.07 }, macro: { x: W * 0.88, y: H * 0.93 } }
      : { crypto: { x: W * 0.07, y: H * 0.5 }, ai: { x: W * 0.93, y: H * 0.24 }, macro: { x: W * 0.93, y: H * 0.76 } };
    const k = clamp(Math.min(W, H) / 640, 0.6, 1.25);
    const maxQ = Math.max(1, ...assets().map((a) => a.qv || 0));
    const nodes = {};
    assets().forEach((a) => {
      const r = ((narrow ? 10 : 12) + (narrow ? 15 : 22) * Math.sqrt((a.qv || 0) / maxQ)) * k;
      // 가운데(BTC) 주변에 파문이 들어갈 자리를 남기도록 반지름을 바깥으로 민다
      const rad = Math.hypot(a.pos[0], a.pos[1]), ang = Math.atan2(a.pos[1], a.pos[0]);
      const rr = a.s === 'BTC' ? 0 : 0.5 + 0.5 * clamp((rad - 0.4) / 0.6, 0, 1);
      nodes[a.s] = { x: cx + Math.cos(ang) * rr * R, y: cy + Math.sin(ang) * rr * R, r: Math.max(r, narrow ? 10 : 11) };
    });
    geo = { R, cx, cy, hubs, nodes, k };
  };

  // ---------- 그리기 ----------
  function draw(ts) {
    if (!data || !geo) return;
    const t = view.t, w = WIN[view.win], now = ts || performance.now();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const vis = visibleNews();
    const sel = view.sel;
    const selNews = sel && sel.kind === 'news' ? data.news.find((n) => n.id === sel.id) : null;
    const dim = !!selNews;
    // 같이 움직이는 코인 사이 선
    ctx.lineWidth = 1;
    data.links.forEach((l) => {
      const a = geo.nodes[l.a], b = geo.nodes[l.b];
      if (!a || !b) return;
      ctx.strokeStyle = alpha(C.text3, clamp((l.c - data.link_min) / (1 - data.link_min), 0, 1) * 0.28 + 0.04);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    });
    // 뉴스 → 코인 선(중 이상만), 파문
    const perNode = {};
    vis.forEach((n) => n.h.forEach((h) => { if (geo.nodes[h.s]) (perNode[h.s] = perNode[h.s] || []).push([n, h]); }));
    Object.entries(perNode).forEach(([s, list]) => {
      const nd = geo.nodes[s];
      list.sort((x, y) => Math.abs(y[1].z || 0) - Math.abs(x[1].z || 0));
      // 코인마다 반응이 큰 10개만 파문으로 그린다(많으면 원이 겹쳐 읽히지 않는다)
      list.slice(0, 10).forEach(([n, h]) => {
        const age = t - n.t, fresh = Math.exp(-age / (w * 0.4));
        const on = selNews && selNews.id === n.id;
        const z = Math.abs(h.z || 0), r = hitR(h);
        const c = r >= 0 ? C.up : C.down;
        if (z >= 2 || on) {
          const hub = geo.hubs[n.c];
          ctx.strokeStyle = on ? C.accent : alpha(c, (dim ? 0.06 : 0.22) * fresh + 0.03);
          ctx.lineWidth = on ? 2 : z >= 3 ? 1.4 : 1;
          ctx.beginPath();
          ctx.moveTo(hub.x, hub.y);
          ctx.quadraticCurveTo((hub.x + nd.x) / 2, (hub.y + nd.y) / 2 - 40, nd.x, nd.y);
          ctx.stroke();
        }
        const grow = Math.min(1, age / 1800);
        const rad = nd.r + 3 + Math.min(z, 6) * 4 * geo.k * (0.35 + 0.65 * grow);
        ctx.strokeStyle = on ? C.accent : alpha(c, (dim ? 0.06 : 0.42) * (0.2 + 0.8 * fresh));
        ctx.lineWidth = on ? 2.5 : z >= 3 ? 1.6 : 1;
        ctx.beginPath(); ctx.arc(nd.x, nd.y, rad, 0, Math.PI * 2); ctx.stroke();
      });
    });
    // 움직이는 파문(도착 순간)
    for (let i = bursts.length - 1; i >= 0; i--) {
      const b = bursts[i], p = (now - b.at) / 1600;
      if (p >= 1) { bursts.splice(i, 1); continue; }
      const nd = geo.nodes[b.s];
      if (!nd) continue;
      ctx.strokeStyle = alpha(b.c, 0.9 * (1 - p));
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(nd.x, nd.y, nd.r + (6 + Math.min(b.z, 6) * 6 * geo.k) * (1 - Math.pow(1 - p, 3)), 0, Math.PI * 2); ctx.stroke();
    }
    // 날아가는 빛
    for (let i = flights.length - 1; i >= 0; i--) {
      const f = flights[i], p = (now - f.at) / 1100;
      if (p < 0) continue;
      const hub = geo.hubs[f.c], nd = geo.nodes[f.s];
      if (!hub || !nd) { flights.splice(i, 1); continue; }
      if (p >= 1) { flights.splice(i, 1); bursts.push({ s: f.s, z: f.z, c: f.color, at: now }); continue; }
      const e = 1 - Math.pow(1 - p, 2), mx = (hub.x + nd.x) / 2, my = (hub.y + nd.y) / 2 - 40;
      const x = (1 - e) * (1 - e) * hub.x + 2 * (1 - e) * e * mx + e * e * nd.x;
      const y = (1 - e) * (1 - e) * hub.y + 2 * (1 - e) * e * my + e * e * nd.y;
      ctx.fillStyle = f.color;
      ctx.shadowColor = f.color; ctx.shadowBlur = 12;
      ctx.beginPath(); ctx.arc(x, y, 3.2, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;
    }
    // 코인
    assets().forEach((a) => {
      const nd = geo.nodes[a.s], chg = chgAt(a, t);
      const c = chg == null ? C.text3 : chg >= 0 ? C.up : C.down;
      const strength = chg == null ? 0 : clamp(Math.abs(chg) / 5, 0, 1);
      const selOn = sel && sel.kind === 'coin' && sel.id === a.s;
      ctx.fillStyle = C.bg;
      ctx.beginPath(); ctx.arc(nd.x, nd.y, nd.r, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = alpha(c, 0.14 + 0.5 * strength);
      ctx.fill();
      ctx.lineWidth = selOn ? 3 : 1.5;
      ctx.strokeStyle = selOn ? C.accent : alpha(c, 0.9);
      if (watch.includes(a.s) && !selOn) ctx.setLineDash([4, 3]);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = C.text;
      ctx.textAlign = 'center';
      ctx.font = `700 ${Math.round(clamp(nd.r * 0.62, 10, 15))}px Geist, Pretendard, sans-serif`;
      ctx.fillText(a.s, nd.x, nd.y + 4);
      ctx.font = `600 ${Math.round(11 * clamp(geo.k, 0.9, 1.1))}px "Geist Mono", monospace`;
      ctx.fillStyle = chg == null ? C.text3 : c;
      ctx.fillText(pct(chg), nd.x, nd.y + nd.r + 15);
    });
    // 뉴스 출발점
    ctx.textAlign = 'center';
    const cnt = { crypto: 0, ai: 0, macro: 0 }, pendN = { crypto: 0, ai: 0, macro: 0 };
    vis.forEach((n) => { if (n.p) pendN[n.c]++; else cnt[n.c]++; });
    Object.entries(geo.hubs).forEach(([cat, hp]) => {
      const on = view.cats.has(cat);
      const pend = pendN[cat];
      ctx.fillStyle = on ? alpha(C.accent, 0.9) : alpha(C.text3, 0.4);
      ctx.beginPath(); ctx.arc(hp.x, hp.y, 5, 0, Math.PI * 2); ctx.fill();
      ctx.font = '600 12px Pretendard, sans-serif';
      ctx.fillStyle = on ? C.text2 : C.text3;
      ctx.fillText(`${CAT[cat]} ${cnt[cat]}`, hp.x, hp.y + (hp.y > H * 0.9 ? -12 : 20));
      if (pend && !reduced) {
        const blink = 0.35 + 0.35 * Math.sin(now / 300);
        ctx.fillStyle = alpha(C.accent, blink);
        ctx.beginPath(); ctx.arc(hp.x + 11, hp.y - 8, 3, 0, Math.PI * 2); ctx.fill();
      }
    });
    lastFrame = now;
  }

  const loop = (ts) => {
    raf = 0;
    if (view.playing) {
      const dt = Math.min(0.1, (ts - (loop.prev || ts)) / 1000);
      advance(dt * 3600 * view.speed);
    }
    loop.prev = ts;
    draw(ts);
    if (view.playing || flights.length || bursts.length) raf = requestAnimationFrame(loop);
    else {
      loop.prev = 0;
      // 측정을 기다리는 뉴스가 있으면 출발점의 점만 천천히 깜빡인다(초당 7번만 그린다)
      if (vis0()) setTimeout(kick, 150);
    }
  };
  const vis0 = () => !reduced && data && visibleNews().some((n) => n.p);
  const kick = () => { if (!raf) raf = requestAnimationFrame(loop); };

  // 커서가 지나간 뉴스를 날려 보낸다
  const launch = (list) => {
    if (reduced) return;
    let k = 0;
    list.forEach((n) => {
      if (seen.has(n.id)) return;
      seen.add(n.id);
      n.h.forEach((h) => {
        if (!geo.nodes[h.s] || !view.cats.has(n.c) || !GRADE_OK[view.grade](h.g)) return;
        if (k++ > 18) return;
        const r = hitR(h);
        flights.push({ c: n.c, s: h.s, z: Math.abs(h.z || 0), color: r >= 0 ? C.up : C.down, at: performance.now() + k * 70 });
      });
    });
    kick();
  };

  // ---------- 시간 ----------
  const span = () => { const t1 = view.live ? nowSec() : Math.max(nowSec(), data.at); return [t1 - WIN['7d'], t1]; };
  const setRange = () => { const [a, b] = span(); range.value = String(Math.round(((view.t - a) / (b - a)) * 1000)); };
  const setClock = () => {
    clock.textContent = view.live ? `${when(view.t)} · 라이브` : `${when(view.t)} · 다시 보기 (${WIN_KO[view.win]} 창)`;
    liveBtn.setAttribute('aria-pressed', view.live ? 'true' : 'false');
  };
  const goTo = (t, keepPlaying) => {
    const [a, b] = span();
    const prev = view.t;
    view.t = clamp(t, a, b);
    view.live = view.t >= b - 60;
    if (!keepPlaying) { view.playing = false; playBtn.textContent = '▶'; playBtn.setAttribute('aria-label', '재생'); }
    if (view.t > prev && view.playing) launch(data.news.filter((n) => n.t > prev && n.t <= view.t));
    else seen = new Set(data.news.filter((n) => n.t <= view.t).map((n) => n.id));
    setRange(); setClock(); renderPanel(); renderList(); kick();
    syncUrl();
  };
  let uiAt = 0, panelAt = 0;
  const advance = (sec) => {
    const [, b] = span();
    const next = view.t + sec;
    if (next >= b) { goTo(b); return; }
    const prev = view.t;
    view.t = next;
    view.live = false;
    const list = [];
    for (let i = lowerBound(prev + 0.001), n = data.news.length; i < n && data.news[i].t <= next; i++) list.push(data.news[i]);
    if (list.length) launch(list);
    // 재생 중에는 시간 막대·시계는 초당 10번, 패널은 1초에 한 번만 고친다
    const ms = performance.now();
    if (ms - uiAt > 100) { uiAt = ms; setRange(); setClock(); }
    if (ms - panelAt > 1000) { panelAt = ms; renderPanel(); }
  };
  range.addEventListener('input', () => { const [a, b] = span(); goTo(a + (b - a) * (Number(range.value) / 1000)); });
  playBtn.addEventListener('click', () => {
    if (view.playing) { view.playing = false; playBtn.textContent = '▶'; playBtn.setAttribute('aria-label', '재생'); renderPanel(); return; }
    const [a, b] = span();
    if (view.t >= b - 60) goTo(a + 0.001);
    view.playing = true; playBtn.textContent = '❚❚'; playBtn.setAttribute('aria-label', '일시정지');
    kick();
  });
  speedBtn.addEventListener('click', () => { view.speed = view.speed === 1 ? 2 : view.speed === 2 ? 4 : 1; speedBtn.textContent = view.speed + '×'; });
  liveBtn.addEventListener('click', () => goTo(nowSec()));

  // ---------- 설정 ----------
  $$('.mseg__b', root).forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.win) { view.win = b.dataset.win; $$('[data-win]', root).forEach((x) => x.setAttribute('aria-pressed', x === b ? 'true' : 'false')); }
    if (b.dataset.grade) { view.grade = b.dataset.grade; $$('[data-grade]', root).forEach((x) => x.setAttribute('aria-pressed', x === b ? 'true' : 'false')); }
    if (b.dataset.cat) {
      const on = view.cats.has(b.dataset.cat);
      if (on && view.cats.size === 1) return;
      on ? view.cats.delete(b.dataset.cat) : view.cats.add(b.dataset.cat);
      b.setAttribute('aria-pressed', on ? 'false' : 'true');
    }
    setClock(); renderPanel(); renderList(); kick();
  }));

  // ---------- 선택 ----------
  const pick = (x, y) => {
    let best = null;
    Object.entries(geo.nodes).forEach(([s, nd]) => {
      const d = Math.hypot(nd.x - x, nd.y - y);
      if (d <= Math.max(nd.r + 6, 22) && (!best || d < best.d)) best = { s, d };
    });
    if (best) return { kind: 'coin', id: best.s };
    const hub = Object.entries(geo.hubs).find(([, hp]) => Math.hypot(hp.x - x, hp.y - y) < 26);
    if (hub) return { kind: 'hub', id: hub[0] };
    return null;
  };
  canvas.addEventListener('click', (e) => {
    const r = canvas.getBoundingClientRect();
    select(pick(e.clientX - r.left, e.clientY - r.top));
  });
  canvas.addEventListener('mousemove', (e) => {
    const r = canvas.getBoundingClientRect();
    canvas.style.cursor = pick(e.clientX - r.left, e.clientY - r.top) ? 'pointer' : 'default';
  });
  const select = (s) => {
    view.sel = s;
    root.classList.toggle('has-sel', !!s);
    panel.classList.toggle('is-open', !!s);
    renderPanel(); kick(); syncUrl();
  };
  const narrow = matchMedia('(max-width: 900px)');
  panel.addEventListener('click', (e) => {
    // 휴대폰: 접힌 시트의 제목 줄을 누르면 펼치고 접는다
    if (narrow.matches && e.target.closest('.mpanel__head') && !e.target.closest('[data-close]')) { panel.classList.toggle('is-open'); return; }
    const b = e.target.closest('[data-pick]');
    if (b) { const [kind, id] = b.dataset.pick.split(':'); select({ kind, id }); return; }
    const g = e.target.closest('[data-goto]');
    if (g) { goTo(Number(g.dataset.goto) + 3600); return; }
    if (e.target.closest('[data-close]')) select(null);
  });

  // ---------- 패널 ----------
  const newsRow = (n) => {
    const z = maxZ(n), top = n.h.slice().sort((a, b) => Math.abs(b.z || 0) - Math.abs(a.z || 0))[0];
    const r = top ? hitR(top) : null;
    return `<li><button type="button" class="mnews" data-pick="news:${esc(n.id)}"><span class="mnews__meta"><span class="chip cat cat--${esc(n.c)}">${CAT[n.c]}</span><span>${esc(n.src || '')} · ${when(n.t)}</span></span>`
      + `<span class="mnews__t">${esc(n.title)}</span>${top ? `<span class="mnews__r ${r >= 0 ? 'up' : 'down'}">${esc(top.s)} ${pct(r)}${top.g ? ' · ' + esc(top.g) : ''}${z ? ' · z ' + z.toFixed(1) : ''}</span>` : '<span class="mnews__r muted">측정 중</span>'}</button></li>`;
  };
  const spark = (a) => {
    const cl = (a.closes || []).filter((p) => p[0] + 3600 <= view.t && p[0] >= view.t - WIN['7d']);
    if (cl.length < 3) return '';
    const vw = 300, vh = 64, xs = cl.map((p) => p[0]), ys = cl.map((p) => p[1]);
    const x0 = xs[0], x1 = xs[xs.length - 1] || x0 + 1, lo = Math.min(...ys), hi = Math.max(...ys) || lo + 1;
    const X = (t) => ((t - x0) / (x1 - x0 || 1)) * vw, Y = (v) => vh - 4 - ((v - lo) / (hi - lo || 1)) * (vh - 8);
    const d = cl.map((p, i) => (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1)).join(' ');
    const marks = data.news.filter((n) => n.t >= x0 && n.t <= view.t && n.h.some((h) => h.s === a.s && Math.abs(h.z || 0) >= 2))
      .map((n) => `<line x1="${X(n.t).toFixed(1)}" x2="${X(n.t).toFixed(1)}" y1="0" y2="${vh}" class="mspark__mark"/>`).join('');
    const up = ys[ys.length - 1] >= ys[0];
    return `<svg class="mspark ${up ? 'is-up' : 'is-down'}" viewBox="0 0 ${vw} ${vh}" preserveAspectRatio="none" aria-hidden="true">${marks}<path d="${d}"/></svg><p class="small muted">최근 7일 1시간 종가 · 세로선 = 중 이상 반응 뉴스</p>`;
  };
  function renderPanel() {
    if (!data) return;
    const vis = visibleNews();
    const sel = view.sel;
    let html = '';
    if (sel && sel.kind === 'coin') {
      const a = bySym(sel.id);
      if (!a) { view.sel = null; return renderPanel(); }
      const list = vis.filter((n) => n.h.some((h) => h.s === a.s)).sort((x, y) => {
        const zx = Math.abs((x.h.find((h) => h.s === a.s) || {}).z || 0), zy = Math.abs((y.h.find((h) => h.s === a.s) || {}).z || 0);
        return zy - zx;
      }).slice(0, 5);
      const price = priceAt(a, view.t);
      const chips = ['1h', '6h', '24h', '7d'].map((w) => {
        const v = w === view.win ? chgAt(a, view.t) : (view.live ? a.chg[w] : null);
        return `<span class="mchg"><b>${WIN_KO[w]}</b><em class="${v == null ? '' : v >= 0 ? 'up' : 'down'}">${pct(v)}</em></span>`;
      }).join('');
      html = `<div class="mpanel__head"><h2 class="mpanel__title">${esc(a.s)}</h2><button type="button" class="mpanel__x" data-close aria-label="닫기">×</button></div>`
        + `<p class="mpanel__price">${price ? price.toLocaleString('en-US', { maximumFractionDigits: price < 1 ? 5 : 2 }) + ' USDT' : '–'}</p><div class="mchgs">${chips}</div>${spark(a)}`
        + (a.base1h ? `<p class="small muted">평소 1시간 변동폭(최근 30일 중앙값) ±${a.base1h.toFixed(2)}%</p>` : '')
        + `<h3 class="mpanel__sub">${WIN_KO[view.win]} 동안 ${esc(a.s)}를 가장 크게 움직인 뉴스</h3>`
        + (list.length ? `<ol class="mlist">${list.map(newsRow).join('')}</ol>` : '<p class="muted small">이 기간에 잰 반응이 없습니다.</p>');
    } else if (sel && sel.kind === 'news') {
      const n = data.news.find((x) => x.id === sel.id);
      if (!n) { view.sel = null; return renderPanel(); }
      const rows = n.h.map((h) => `<tr><th scope="row">${esc(h.s)}</th>${['15m', '1h', '24h'].map((w) => `<td class="${h[w] == null ? 'muted' : h[w] >= 0 ? 'up' : 'down'}">${h[w] == null ? '측정 중' : pct(h[w])}</td>`).join('')}<td>${h.g ? esc(h.g) : '–'}${h.z != null ? ' <span class="muted">z ' + h.z.toFixed(1) + '</span>' : ''}</td></tr>`).join('');
      const pt = n.pt;
      const ptHtml = !pt ? '' : pt.n >= 5
        ? `<div class="mpat"><p class="mpat__k">이런 뉴스는 보통 · ${esc(pt.label)} · ${esc(pt.sym)} 1시간</p><p class="mpat__v">중앙값 <b class="${pt.med >= 0 ? 'up' : 'down'}">${pct(pt.med)}</b> · 상승 ${Math.round(pt.up * 100)}% · 중·강 ${Math.round(pt.strong * 100)}% <span class="muted">(n=${pt.n}, 최근 30일)</span></p></div>`
        : `<div class="mpat"><p class="mpat__k">이런 뉴스는 보통 · ${esc(pt.label)}</p><p class="mpat__v muted">표본 부족 (n=${pt.n})</p></div>`;
      html = `<div class="mpanel__head"><p class="mpanel__meta"><span class="chip cat cat--${esc(n.c)}">${CAT[n.c]}</span>${esc(ETYPE[n.e] || '')} · ${esc(n.src || '')} · ${when(n.t)}</p><button type="button" class="mpanel__x" data-close aria-label="닫기">×</button></div>`
        + `<h2 class="mpanel__news">${esc(n.title)}</h2>`
        + (n.p ? '<p class="muted small">반응을 재는 중입니다. 15분 뒤부터 채워집니다.</p>' : `<table class="mtable"><thead><tr><th scope="col">코인</th><th scope="col">15분</th><th scope="col">1시간</th><th scope="col">24시간</th><th scope="col">강도</th></tr></thead><tbody>${rows}</tbody></table>`)
        + ptHtml
        + `<p class="mpanel__links"><a href="${BASE}a/${esc(n.id)}/">기사와 차트 보기</a><button type="button" class="linkbtn" data-goto="${n.t}">이 시각으로 돌려 보기</button></p>`;
    } else {
      const cat = sel && sel.kind === 'hub' ? sel.id : null;
      const list = vis.filter((n) => !n.p && (!cat || n.c === cat)).sort((x, y) => maxZ(y) - maxZ(x)).slice(0, 8);
      html = `<div class="mpanel__head"><h2 class="mpanel__title mpanel__title--s">${cat ? CAT[cat] + ' 뉴스' : '지금 가장 무거운 뉴스'}</h2>${cat ? '<button type="button" class="mpanel__x" data-close aria-label="닫기">×</button>' : ''}</div>`
        + `<p class="small muted">${WIN_KO[view.win]} 동안 잰 반응이 큰 순서 · 원을 누르면 그 코인, 뉴스를 누르면 그 뉴스를 봅니다.</p>`
        + (list.length ? `<ol class="mlist">${list.map(newsRow).join('')}</ol>` : '<p class="muted small">이 기간에 보여 줄 뉴스가 없습니다.</p>');
    }
    panel.innerHTML = html;
  }

  // 목록으로 보기(같은 내용을 표로)
  let listTimer = 0;
  function renderList() {
    clearTimeout(listTimer);
    listTimer = setTimeout(() => {
      const box = $('#mapList');
      if (!box || !data) return;
      const coins = assets().map((a) => { const c = chgAt(a, view.t); return `<tr><th scope="row">${esc(a.s)}</th><td class="${c == null ? '' : c >= 0 ? 'up' : 'down'}">${pct(c)}</td></tr>`; }).join('');
      const news = visibleNews().filter((n) => !n.p).sort((x, y) => maxZ(y) - maxZ(x)).slice(0, 50).map((n) => {
        const top = n.h.slice().sort((a, b) => Math.abs(b.z || 0) - Math.abs(a.z || 0))[0];
        return `<li><a href="${BASE}a/${esc(n.id)}/">${esc(n.title)}</a> <span class="muted small">${when(n.t)} · ${top ? esc(top.s) + ' ' + pct(hitR(top)) + (top.g ? ' · ' + esc(top.g) : '') : ''}</span></li>`;
      }).join('');
      box.innerHTML = `<div class="mlistbox"><table class="mtable"><caption class="small muted">${WIN_KO[view.win]} 등락</caption><tbody>${coins}</tbody></table><ol class="mlistbox__news">${news || '<li class="muted">뉴스 없음</li>'}</ol></div>`;
    }, 120);
  }

  // ---------- 주소 ----------
  const syncUrl = () => {
    const q = new URLSearchParams();
    if (!view.live) q.set('t', String(Math.round(view.t)));
    if (view.sel && view.sel.kind !== 'hub') q.set('sel', view.sel.kind + ':' + view.sel.id);
    const s = q.toString();
    history.replaceState(null, '', location.pathname + (s ? '?' + s : ''));
  };

  // ---------- 크기 ----------
  const resize = () => {
    W = stage.clientWidth; H = stage.clientHeight; dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    if (data) { layoutGeo(); draw(); }
  };
  new ResizeObserver(resize).observe(stage);

  // ---------- 실시간 시세 ----------
  let ws = null, wsTimer = 0, drawTimer = 0;
  const connect = () => {
    if (!data || ws) return;
    const streams = assets().map((a) => a.s.toLowerCase() + 'usdt@miniTicker').join('/');
    try { ws = new WebSocket('wss://data-stream.binance.vision/stream?streams=' + streams); } catch (e) { return; }
    ws.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data).data;
        const s = d.s.replace(/USDT$/, ''), c = Number(d.c), o = Number(d.o);
        live[s] = { price: c, chg24: o ? (c / o - 1) * 100 : null };
        // 그사이 다시 보기로 옮겼으면 시각을 건드리지 않는다
        if (view.live && !drawTimer) drawTimer = setTimeout(() => { drawTimer = 0; if (view.live) { view.t = nowSec(); draw(); } }, 500);
      } catch (e) {}
    };
    ws.onclose = () => { ws = null; clearTimeout(wsTimer); if (!document.hidden) wsTimer = setTimeout(connect, 5000); };
  };
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { if (ws) ws.close(); } else { connect(); refresh(); }
  });

  // ---------- 불러오기 ----------
  async function refresh() {
    try {
      const res = await fetch(root.dataset.src + '?t=' + Math.floor(Date.now() / 60000), { cache: 'no-store' });
      if (!res.ok) throw new Error(res.status);
      const next = await res.json();
      const fresh = data ? next.news.filter((n) => !data.news.some((m) => m.id === n.id && !m.p === !n.p)) : [];
      data = next;
      layoutGeo();
      if (view.live) { view.t = nowSec(); fresh.forEach((n) => seen.delete(n.id)); launch(fresh.filter((n) => !n.p)); }
      setRange(); setClock(); renderPanel(); renderList(); draw();
      $('#mapEmpty').hidden = true;
    } catch (e) {
      if (!data) $('#mapEmpty').hidden = false;
    }
  }

  (async () => {
    resize();
    await refresh();
    if (!data) return;
    const q = new URLSearchParams(location.search);
    if (q.get('sel')) { const [kind, id] = q.get('sel').split(':'); if (kind && id) view.sel = { kind, id }; }
    if (q.get('t')) goTo(Number(q.get('t')));
    else { seen = new Set(data.news.map((n) => n.id)); goTo(nowSec()); }
    connect();
    setInterval(() => { if (!document.hidden) refresh(); }, 60000);
    setInterval(() => { if (view.live && !document.hidden) { view.t = nowSec(); setRange(); setClock(); } }, 30000);
  })();
}

main();
