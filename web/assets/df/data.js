// 속보 · 시세 · 하루 정리 · 다음 발표 받기
window.DFD = (() => {
  const data = path => (window.DF_ROOT || (window.DF_BASE || '../').replace(/assets\/df\/$/, '')) + 'data/' + path;
  const FLASH = 'https://api.delfona.com/flash';
  let livePending = null, liveValue = null, liveAt = 0, liveDisabled = false, liveRetryAt = 0;
  async function live() {
    if (!window.DF_LIVE || liveDisabled || Date.now() < liveRetryAt) return null;
    const pb = liveValue && stream.bundle(liveValue);
    if (pb) return pb;
    if (liveValue && Date.now() - liveAt < (stream.degraded() ? 59000 : 29000)) return liveValue;
    if (livePending) return livePending;
    liveAt = Date.now();
    livePending = (async () => {
      const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 8000);
      try {
        const response = await fetch(FLASH.replace('/flash', '/live'), {cache: 'no-store', signal: controller.signal});
        if (response.status === 404) { liveDisabled = true; return null; }
        if (!response.ok) throw new Error('live unavailable');
        const value = await response.json();
        if (value.v !== 1 || !Array.isArray(value.flash?.items) ||
            !value.market?.['1h']?.q || !value.market?.['5m']?.q ||
            !Array.isArray(value.indices?.nq?.c) || !Array.isArray(value.indices?.es?.c)) throw new Error('invalid live response');
        liveValue = value; return value;
      } catch (e) {
        if (e && e.message === 'invalid live response') liveDisabled = true; else liveRetryAt = Date.now() + 300000;
        liveValue = null; return null;
      } finally { clearTimeout(timer); livePending = null; }
    })();
    return livePending;
  }
  const SRC = globalThis.document?.currentScript?.src, stream = { healthy() {}, quiet() {}, degraded() {}, market() {}, bundle() {},   // r25: ws.js 가 채운다
    connect(on) { if (!stream.p && SRC && globalThis.WebSocket) stream.p = import(new URL('ws.js', SRC).href + new URL(SRC).search).then((m) => m.start(stream, FLASH, on), () => {}); } };
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const hm = (t) => { const d = new Date(t * 1000); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
  const pct = (v, d = 2) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d) + '%';
  const vcls = (v) => v === '호재' ? 'up' : v === '악재' ? 'down' : 'flat';
  // 20초 안 다시 부르면 같은 요청을 나눠 쓴다(첫 페이지는 3D 장면 둘이 따로 부른다). Worker 도 20초 캐시라 새로움은 같다
  let flashP = null, flashAt = 0;
  function flash() {
    if (flashP && Date.now() - flashAt < 20000) return flashP;
    flashAt = Date.now();
    return (flashP = (async () => { const bundle = await live(); return bundle ? bundle.flash : (await fetch(FLASH, { cache: 'no-store' })).json(); })().catch((e) => { flashP = null; throw e; }));
  }
  // 새 소식만 작게(보고 있을 때 5초마다, lk.js). 서버가 바쁘면 503 + Retry-After
  const flashNew = (after, signal) => fetch(FLASH + '/new?after=' + Math.max(0, Math.floor(after)), { cache: 'no-store', signal });
  const day24 = (items) => { const s = Date.now() / 1000 - 86400, xs = items.filter((x) => x.t >= s);
    return { all: xs.length, u: xs.filter((x) => x.v === '호재').length, d: xs.filter((x) => x.v === '악재').length, n: xs.filter((x) => x.v === '중립').length, big: xs.filter((x) => x.s >= 2).length }; };
  return { data, live, esc, hm, pct, vcls, flash, flashNew, day24, stream };
})();

// 영어 기본 + 한국어(data-t 영어 원문 ↔ KO 사전)
window.DFI = (() => {
  let LANG = /^ko/i.test(navigator.language) ? 'ko' : 'en', KO = {}, EN = {}, ENT = {}, subs = [];
  try { LANG = localStorage.getItem('df-lang') || LANG; } catch (e) {}
  const V = { en: { '호재': 'Bullish', '악재': 'Bearish', '중립': 'Neutral' }, ko: { '호재': '호재', '악재': '악재', '중립': '중립' } };
  const dk = () => document.documentElement.dataset.theme === 'dark';
  const apply = () => {
    document.documentElement.lang = LANG;
    document.querySelectorAll('[data-t]').forEach((el) => { const k = el.dataset.t, s = LANG === 'ko' && KO[k] != null ? KO[k] : EN[k]; if (el.hasAttribute('data-html')) el.innerHTML = s; else el.textContent = s; });
    document.querySelectorAll('[data-lang]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.lang === LANG)));
    document.querySelectorAll('[data-theme-toggle]').forEach((b) => b.setAttribute('aria-pressed', dk()));
    document.querySelector('meta[name=theme-color]')?.setAttribute('content', dk() ? '#0b1320' : '#fff');
    subs.forEach((f) => f(LANG));
  };
  const init = (ko) => {
    KO = { ac1: '로그인', ...ko }; document.querySelectorAll('[data-t]').forEach((el) => { EN[el.dataset.t] = el.hasAttribute('data-html') ? el.innerHTML : el.textContent; });
    // 언어 · 다크 모드 버튼: 같은 apply 로 글과 차트를 다시 그린다
    document.addEventListener('click', (e) => { const b = e.target.closest('[data-lang],[data-theme-toggle]'); if (!b) return;
      const v = b.dataset.lang || (dk() ? 'light' : 'dark'); if (b.dataset.lang) LANG = v; else document.documentElement.dataset.theme = v;
      try { localStorage.setItem(b.dataset.lang ? 'df-lang' : 'df-theme', v); } catch (x) {} apply(); });
    apply();
  };
  fetch((window.DF_BASE || '../') + 'en.json').then((r) => r.json()).then((m) => { ENT = m; subs.forEach((f) => f(LANG)); }).catch(() => {});
  const ago = (t) => { const s = Date.now() / 1000 - t, ko = LANG === 'ko'; return s < 60 ? (ko ? '방금' : 'just now') : s < 3600 ? (ko ? `${Math.floor(s / 60)}분 전` : `${Math.floor(s / 60)}m ago`) : s < 86400 ? (ko ? `${Math.floor(s / 3600)}시간 전` : `${Math.floor(s / 3600)}h ago`) : (ko ? `${Math.floor(s / 86400)}일 전` : `${Math.floor(s / 86400)}d ago`); };
  return { init, onLang: (f) => subs.push(f), lang: () => LANG, line: (it) => (LANG === 'en' ? it.en || ENT[it.id] || null : it.ko), has: (it) => LANG !== 'en' || !!(it.en || ENT[it.id]), v: (x) => V[LANG][x] || x, ago,
    outlets: (n) => (LANG === 'ko' ? (n > 1 ? `${n}곳 보도` : '단독 보도') : (n > 1 ? `${n} outlets` : 'single source')) };
})();

