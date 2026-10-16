// 시안 1·2·3 공통: 실시간 속보, 시세, 하루 정리, 다음 큰 발표를 받아 온다(모두 실제 데이터).
window.DFD = (() => {
  const FLASH = 'https://signal-scheduler.mash1384.workers.dev/flash';
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const ago = (t) => { const s = Date.now() / 1000 - t; return s < 60 ? '방금' : s < 3600 ? `${Math.floor(s / 60)}분 전` : s < 86400 ? `${Math.floor(s / 3600)}시간 전` : `${Math.floor(s / 86400)}일 전`; };
  const hm = (t) => { const d = new Date(t * 1000); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
  const money = (p) => p >= 1000 ? '$' + Math.round(p).toLocaleString('en-US') : p >= 1 ? '$' + p.toFixed(2) : '$' + p.toPrecision(4);
  const pct = (v, d = 2) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d) + '%';
  const vcls = (v) => v === '호재' ? 'up' : v === '악재' ? 'down' : 'flat';
  async function flash() { return (await fetch(FLASH, { cache: 'no-store' })).json(); }
  async function prices(syms = ['BTC', 'ETH', 'SOL', 'XRP']) {
    const r = await fetch('https://data-api.binance.vision/api/v3/ticker/24hr?symbols=' + encodeURIComponent(JSON.stringify(syms.map((s) => s + 'USDT'))));
    return Object.fromEntries((await r.json()).map((x) => [x.symbol.replace('USDT', ''), { p: +x.lastPrice, c: +x.priceChangePercent }]));
  }
  async function brief() {
    // 하루 정리 파일 이름은 세계 표준시 날짜(한국 09:00~09:00). 오늘 것(진행 중)이 없으면 어제 것
    const get = async (t) => { const r = await fetch(`https://raw.githubusercontent.com/mash1384/signal-desk/flash/daily/${new Date(t).toISOString().slice(0, 10)}.json`); if (!r.ok) throw 0; return r.json(); };
    try { return await get(Date.now()); } catch (e) { return get(Date.now() - 86400e3); }
  }
  async function nextEvent() {
    const d = await (await fetch('https://mash1384.github.io/signal-desk/data/events.json')).json(), now = Date.now() / 1000;
    return d.upcoming.filter((x) => x.ts > now).sort((a, b) => b.level - a.level || a.ts - b.ts)[0] || null;
  }
  async function market() { return (await fetch('https://mash1384.github.io/signal-desk/data/market.json')).json(); }
  const day24 = (items) => { const s = Date.now() / 1000 - 86400, xs = items.filter((x) => x.t >= s);
    return { all: xs.length, u: xs.filter((x) => x.v === '호재').length, d: xs.filter((x) => x.v === '악재').length, n: xs.filter((x) => x.v === '중립').length, big: xs.filter((x) => x.s >= 2).length }; };
  const left = (ts) => { const s = Math.max(0, ts - Date.now() / 1000), d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60); return d ? `${d}일 ${h}시간` : h ? `${h}시간 ${m}분` : `${m}분`; };
  return { esc, ago, hm, money, pct, vcls, flash, prices, brief, nextEvent, market, day24, left };
})();

// 시안 F1~F3 공통: 영어 기본 + 한국어 전환. data-t 요소의 영어 원문을 기억해 두고 KO 사전으로 바꾼다.
window.DFI = (() => {
  let LANG = /^ko/i.test(navigator.language) ? 'ko' : 'en', KO = {}, EN = {}, ENT = {}, subs = [];
  try { LANG = localStorage.getItem('df-lang') || LANG; } catch (e) {}
  const V = { en: { '호재': 'Positive', '악재': 'Negative', '중립': 'Neutral' }, ko: { '호재': '호재', '악재': '악재', '중립': '중립' } };
  const apply = () => {
    document.documentElement.lang = LANG;
    document.querySelectorAll('[data-t]').forEach((el) => { const k = el.dataset.t, s = LANG === 'ko' && KO[k] != null ? KO[k] : EN[k]; if (el.hasAttribute('data-html')) el.innerHTML = s; else el.textContent = s; });
    document.querySelectorAll('[data-lang]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.lang === LANG)));
    subs.forEach((f) => f(LANG));
  };
  const init = (ko) => {
    KO = ko; document.querySelectorAll('[data-t]').forEach((el) => { EN[el.dataset.t] = el.hasAttribute('data-html') ? el.innerHTML : el.textContent; });
    document.addEventListener('click', (e) => { const b = e.target.closest('[data-lang]'); if (!b) return; LANG = b.dataset.lang; try { localStorage.setItem('df-lang', LANG); } catch (x) {} apply(); });
    apply();
  };
  fetch((window.DF_BASE || '../') + 'en.json').then((r) => r.json()).then((m) => { ENT = m; subs.forEach((f) => f(LANG)); }).catch(() => {});
  const ago = (t) => { const s = Date.now() / 1000 - t, ko = LANG === 'ko'; return s < 60 ? (ko ? '방금' : 'just now') : s < 3600 ? (ko ? `${Math.floor(s / 60)}분 전` : `${Math.floor(s / 60)}m ago`) : s < 86400 ? (ko ? `${Math.floor(s / 3600)}시간 전` : `${Math.floor(s / 3600)}h ago`) : (ko ? `${Math.floor(s / 86400)}일 전` : `${Math.floor(s / 86400)}d ago`); };
  return { init, onLang: (f) => subs.push(f), lang: () => LANG, line: (it) => (LANG === 'en' ? it.en || ENT[it.id] || null : it.ko), has: (it) => LANG !== 'en' || !!(it.en || ENT[it.id]), v: (x) => V[LANG][x] || x, ago,
    outlets: (n) => (LANG === 'ko' ? (n > 1 ? `${n}곳 보도` : '단독 보도') : (n > 1 ? `${n} outlets` : 'single source')) };
})();
