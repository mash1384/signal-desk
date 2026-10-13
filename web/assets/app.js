// Delfona 공통: 테마, 실시간 시세, 내 코인(별표), 실시간 속보 받기, 검색.
(() => {
  const DF = (window.DF = window.DF || {});
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const safeUrl = (u) => (/^https?:\/\//i.test(u || '') ? u : '');
  DF.esc = esc;

  // ---------- 숫자·시간 ----------
  DF.money = (p) => {
    if (p == null || !isFinite(p)) return '–';
    if (p >= 1000) return '$' + Math.round(p).toLocaleString('en-US');
    if (p >= 1) return '$' + p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return '$' + p.toPrecision(4).replace(/0+$/, '');
  };
  DF.signed = (v, d = 2) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d) + '%';
  DF.ago = (t) => {
    const s = Math.max(0, Date.now() / 1000 - t);
    if (s < 60) return '방금';
    if (s < 3600) return `${Math.floor(s / 60)}분 전`;
    if (s < 86400) return `${Math.floor(s / 3600)}시간 전`;
    return new Date(t * 1000).toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' });
  };
  const left = (sec) => {
    if (sec <= 0) return '발표됨';
    const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60);
    return d ? `${d}일 ${h}시간 남음` : h ? `${h}시간 ${m}분 남음` : `${Math.max(1, m)}분 남음`;
  };
  function tick() {
    $$('[data-left]').forEach((el) => { el.textContent = left(Number(el.dataset.left) - Date.now() / 1000); });
    $$('time[data-ago]').forEach((el) => { el.textContent = DF.ago(+el.dataset.ago); });
  }

  // ---------- 테마 ----------
  function initTheme() {
    const btn = $('#themeBtn');
    if (!btn) return;
    const label = () => btn.setAttribute('aria-label', document.documentElement.dataset.theme === 'dark' ? '밝은 화면으로 바꾸기' : '어두운 화면으로 바꾸기');
    label();
    btn.addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      // 테마를 바꾸는 순간 모든 색 전환이 한꺼번에 일어나지 않게 잠깐 끈다
      const st = document.createElement('style');
      st.textContent = '*,*::before,*::after{transition:none!important}';
      document.head.appendChild(st);
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('df-theme', next); } catch (e) {}
      getComputedStyle(document.body).opacity;
      requestAnimationFrame(() => st.remove());
      label();
    });
  }

  // ---------- 내 코인 ----------
  const STAR = 'df-stars';
  DF.stars = () => { try { return JSON.parse(localStorage.getItem(STAR)) || []; } catch (e) { return []; } };
  function setStars(list) {
    try { localStorage.setItem(STAR, JSON.stringify(list)); } catch (e) {}
    syncStars();
    document.dispatchEvent(new CustomEvent('df:stars', { detail: list }));
  }
  function syncStars() {
    const s = new Set(DF.stars());
    $$('[data-star]').forEach((b) => b.setAttribute('aria-pressed', String(s.has(b.dataset.star))));
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-star]');
    if (!b) return;
    const s = DF.stars(), k = b.dataset.star, i = s.indexOf(k);
    i >= 0 ? s.splice(i, 1) : s.push(k);
    setStars(s);
  });

  // ---------- 실시간 시세(바이낸스 24시간 시세, 30초마다) ----------
  const HOSTS = ['https://data-api.binance.vision', 'https://api.binance.com'];
  async function livePrices() {
    const syms = [...new Set($$('[data-live]').map((el) => el.dataset.live))];
    if (!syms.length) return;
    const q = encodeURIComponent(JSON.stringify(syms.map((s) => s + 'USDT')));
    for (const host of HOSTS) {
      try {
        const r = await fetch(`${host}/api/v3/ticker/24hr?symbols=${q}`);
        if (!r.ok) continue;
        const rows = await r.json();
        const by = Object.fromEntries(rows.map((x) => [x.symbol.replace(/USDT$/, ''), x]));
        $$('[data-live]').forEach((el) => {
          const x = by[el.dataset.live];
          if (!x) return;
          const p = +x.lastPrice, c = +x.priceChangePercent;
          const pe = $('[data-live-p]', el), ce = $('[data-live-c]', el);
          if (pe) pe.textContent = DF.money(p);
          if (ce) { ce.textContent = DF.signed(c); ce.classList.toggle('up', c >= 0); ce.classList.toggle('down', c < 0); }
        });
        return;
      } catch (e) { /* 다음 주소로 */ }
    }
  }
  DF.refreshLive = livePrices;

  // ---------- 실시간 속보(Worker /flash, 30초마다) ----------
  const subs = [];
  DF.onFlash = (fn) => { subs.push(fn); if (DF.flashData) fn(DF.flashData, null); if (!DF._flashOn) startFlash(); };
  function startFlash() {
    DF._flashOn = true;
    if (!DF.flash) { subs.forEach((fn) => fn(null, 'off')); return; }
    const load = async () => {
      try {
        const r = await fetch(DF.flash, { cache: 'no-store' });
        if (!r.ok) throw new Error(r.status);
        const d = await r.json();
        if (!Array.isArray(d.items)) throw new Error('bad');
        const prev = DF.flashData;
        DF.flashData = d;
        subs.forEach((fn) => fn(d, null, prev));
      } catch (e) {
        if (!DF.flashData) subs.forEach((fn) => fn(null, 'error'));
      }
    };
    load();
    setInterval(() => { if (!document.hidden) load(); }, 30000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
  }
  DF.flashStatus = (d) => {
    if (!d) return '속보를 불러오지 못했어요';
    const idle = Date.now() / 1000 - (d.last_got || d.at);
    return idle > 900 ? `수집이 잠시 멈췄어요 · 마지막 ${DF.ago(d.last_got || d.at)}` : `${DF.ago(d.at)} 갱신`;
  };
  // 코인 페이지가 있는 코인만 링크로
  const KNOWN = new Set(['BTC','ETH','SOL','XRP','BNB','DOGE','ADA','LINK','AVAX','SUI','TON','DOT','LTC','TRX','HBAR','TAO','AAVE','UNI','NEAR','APT','ONDO','ENA','PEPE','ZEC','FET']);
  DF.fi = (it, seen) => {
    const cls = it.v === '호재' ? 'up' : it.v === '악재' ? 'down' : 'flat';
    const S = (DF.flashData && DF.flashData.sectors) || {};
    const tags = [...it.coins.map((c) => (KNOWN.has(c) ? `<a class="tag" href="${DF.base}coins/${esc(c.toLowerCase())}/">${esc(c)}</a>` : `<span class="tag">${esc(c)}</span>`)),
      ...it.sectors.map((s) => `<span class="tag tag--line">${esc(S[s] || s)} 섹터</span>`),
      ...(it.mw ? ['<span class="tag tag--line">시장 전체</span>'] : [])].join('');
    const link = safeUrl(it.link);
    return `<li class="fi${it.s >= 2 ? ' is-big' : ''}${seen && !seen.has(it.id) ? ' is-new' : ''}"><span class="v v--${cls}">${esc(it.v)}</span><div>
      <span class="fi__t">${esc(it.ko)}</span>
      <span class="fi__m"><time data-ago="${it.t}">${DF.ago(it.t)}</time>${it.n > 1 ? `<span>${it.n}곳 보도</span>` : ''}${tags}${link ? `<a href="${esc(link)}" target="_blank" rel="noopener nofollow">관련 기사</a>` : ''}</span></div></li>`;
  };
  // 코인 목록: 지난 24시간 소식 수
  function newsCounts(d) {
    const cells = $$('[data-news]');
    if (!cells.length || !d) return;
    const since = Date.now() / 1000 - 86400, cnt = {};
    d.items.filter((it) => it.t >= since).forEach((it) => it.coins.forEach((c) => {
      const x = (cnt[c] ||= { u: 0, d: 0, n: 0 });
      x.n++; if (it.v === '호재') x.u++; if (it.v === '악재') x.d++;
    }));
    cells.forEach((el) => {
      const x = cnt[el.dataset.news];
      el.innerHTML = x ? `소식 ${x.n} · <span class="up">호재 ${x.u}</span> · <span class="down">악재 ${x.d}</span>` : '<span class="muted">오늘 소식 없음</span>';
    });
  }

  // ---------- 검색(⌘K) ----------
  function initSearch() {
    const box = $('#cmdk'), input = $('#cmdkInput'), list = $('#cmdkList'), open = $('#openSearch');
    if (!box) return;
    let items = null, sel = 0, last = null;
    const coins = [['BTC','비트코인'],['ETH','이더리움'],['SOL','솔라나'],['XRP','리플'],['BNB','바이낸스코인'],['DOGE','도지코인'],['ADA','에이다'],['LINK','체인링크'],['AVAX','아발란체'],['SUI','수이'],['TON','톤코인'],['DOT','폴카닷'],['LTC','라이트코인'],['TRX','트론'],['HBAR','헤데라'],['TAO','비트텐서'],['AAVE','에이브'],['UNI','유니스왑'],['NEAR','니어프로토콜'],['APT','앱토스'],['ONDO','온도파이낸스'],['ENA','에테나'],['PEPE','페페'],['ZEC','지캐시'],['FET','페치']];
    const pages = [['지금', ''], ['속보', 'news/'], ['하루 정리', 'brief/'], ['코인', 'coins/'], ['상장 레이더', 'radar/#lr'], ['발표 레이더', 'radar/#events'], ['소개·방법론', 'about/']];
    const show = () => {
      last = document.activeElement;
      box.hidden = false; input.value = ''; render(); input.focus();
      if (!items) fetch(DF.base + 'data/feed.json?t=' + Math.floor(Date.now() / 60000)).then((r) => r.json()).then((d) => { items = d.items || []; render(); }).catch(() => { items = []; });
    };
    const hide = () => { box.hidden = true; if (last) last.focus(); };
    const render = () => {
      const q = input.value.trim().toLowerCase();
      let rows = [];
      if (!q) rows = pages.map(([t, u]) => ({ t, s: '바로 가기', u: DF.base + u }));
      else {
        rows = coins.filter(([s, n]) => s.toLowerCase().includes(q) || n.includes(q)).map(([s, n]) => ({ t: `${n} ${s}`, s: '코인', u: `${DF.base}coins/${s.toLowerCase()}/` }));
        rows = rows.concat((items || []).filter((a) => a.title.toLowerCase().includes(q) || a.src.toLowerCase().includes(q) || a.assets.some((x) => x.toLowerCase() === q))
          .slice(0, 30).map((a) => ({ t: a.title, s: `${a.src} · ${DF.ago(a.t0)}`, u: a.url })));
      }
      sel = 0;
      list.innerHTML = rows.length ? rows.map((r, i) => `<a role="option" href="${esc(r.u)}" aria-selected="${i === 0}"><b>${esc(r.t)}</b><small>${esc(r.s)}</small></a>`).join('')
        : `<p class="cmdk__empty">'${esc(input.value)}'에 맞는 코인이나 기사가 없어요. 다른 낱말로 찾아보세요.</p>`;
    };
    const move = (d) => {
      const opts = $$('[role="option"]', list);
      if (!opts.length) return;
      sel = (sel + d + opts.length) % opts.length;
      opts.forEach((o, i) => o.setAttribute('aria-selected', String(i === sel)));
      opts[sel].scrollIntoView({ block: 'nearest' });
    };
    open.addEventListener('click', show);
    box.addEventListener('click', (e) => { if (e.target.closest('[data-close]')) hide(); });
    input.addEventListener('input', render);
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); box.hidden ? show() : hide(); return; }
      if (box.hidden) return;
      if (e.key === 'Escape') hide();
      else if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
      else if (e.key === 'Enter') { const o = $$('[role="option"]', list)[sel]; if (o) { e.preventDefault(); location.href = o.href; } }
    });
  }

  function boot() {
    initTheme();
    syncStars();
    initSearch();
    tick();
    setInterval(tick, 15000);
    livePrices();
    setInterval(() => { if (!document.hidden) livePrices(); }, 30000);
    if ($('[data-news]')) DF.onFlash((d) => newsCounts(d));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
