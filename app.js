/* SIGNAL — 인터랙션과 모션
 * 모션 원칙 (원글이 추천한 두 스킬에서 가져옴)
 * - 진입/퇴장은 ease-out, 화면 위 이동은 ease-in-out, 일정한 움직임은 linear
 * - 누름 피드백 scale(0.96), UI 트랜지션은 300ms 이하
 * - 키보드로 여는 커맨드 팔레트는 애니메이션 없음
 * - 장식용 마우스 추적은 스프링으로 보간
 * - prefers-reduced-motion이면 이동·스케일·블러를 빼고 불투명도만 남김
 */
(function () {
  'use strict';

  const D = window.SIGNAL_DATA;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const reduceMQ = window.matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  const mobileMQ = window.matchMedia('(max-width: 860px)');
  const reduced = () => reduceMQ.matches;

  const CAT_VAR = { crypto: '--crypto', ai: '--ai', macro: '--macro' };
  const COVER = {
    crypto: ['var(--crypto)', 'var(--accent)'],
    ai: ['var(--ai)', 'var(--macro)'],
    macro: ['var(--macro)', 'var(--ai)'],
  };
  const ARROW_UP = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 1.5 9 8.5H1z"/></svg>';
  const ARROW_DOWN = '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 8.5 1 1.5h8z"/></svg>';
  const CHEV = '<svg class="s-card__arrow" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 15 15 5M7 5h8v8"/></svg>';

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  /* ---------- 포맷 ---------- */
  function fmtPrice(p, unit) {
    if (unit === '%') return p.toFixed(3) + '%';
    let d = 2;
    if (p >= 10000) d = 0;
    else if (p >= 100) d = 2;
    else if (p >= 10) d = 2;
    else if (p >= 1) d = 3;
    else d = 4;
    return p.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  const fmtChg = (c) => (c >= 0 ? '+' : '') + c.toFixed(2) + '%';
  const dirOf = (c) => (c >= 0 ? 'up' : 'down');

  /* ---------- 시드 난수 (샘플 시계열용) ---------- */
  function rng(seedStr) {
    let h = 2166136261;
    for (const ch of seedStr) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
    return () => {
      h += 0x6d2b79f5;
      let t = h;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function sampleSeries(sym, last, chg, n = 48) {
    const r = rng(sym);
    const first = last / (1 + chg / 100);
    const out = [];
    let noise = 0;
    for (let i = 0; i < n; i++) {
      const k = i / (n - 1);
      noise = noise * 0.82 + (r() - 0.5) * 0.9;
      out.push(first + (last - first) * k + noise * last * 0.004 * (1 - k * 0.6));
    }
    out[n - 1] = last;
    return out;
  }

  /* ---------- 시장 상태 ---------- */
  const market = {
    crypto: D.crypto.map((c) => ({ ...c, price: c.base, series: sampleSeries(c.sym, c.base, c.chg) })),
    macro: D.macro.map((m) => ({ ...m, price: m.base, series: sampleSeries(m.sym, m.base, m.chg) })),
    live: false,
    seg: 'crypto',
  };

  async function fetchJSON(url, ms = 4500) {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), ms);
    try {
      const res = await fetch(url, { signal: ctl.signal });
      if (!res.ok) throw new Error(res.status);
      return await res.json();
    } finally {
      clearTimeout(t);
    }
  }

  const HOSTS = ['https://data-api.binance.vision', 'https://api.binance.com'];
  let liveHost = null;

  async function loadLiveTickers() {
    const syms = market.crypto.map((c) => c.live);
    const q = '/api/v3/ticker/24hr?symbols=' + encodeURIComponent(JSON.stringify(syms));
    const hosts = liveHost ? [liveHost] : HOSTS;
    for (const h of hosts) {
      try {
        const rows = await fetchJSON(h + q);
        liveHost = h;
        const bySym = Object.fromEntries(rows.map((r) => [r.symbol, r]));
        market.crypto.forEach((c) => {
          const r = bySym[c.live];
          if (!r) return;
          c.price = parseFloat(r.lastPrice);
          c.chg = parseFloat(r.priceChangePercent);
          c.series[c.series.length - 1] = c.price;
        });
        return true;
      } catch (e) {
        /* 다음 호스트 시도 */
      }
    }
    return false;
  }

  async function loadLiveSeries() {
    await Promise.all(
      market.crypto.slice(0, 8).map(async (c) => {
        try {
          const k = await fetchJSON(`${liveHost}/api/v3/klines?symbol=${c.live}&interval=30m&limit=48`);
          c.series = k.map((row) => parseFloat(row[4]));
          c.series[c.series.length - 1] = c.price;
        } catch (e) {
          /* 샘플 시계열 유지 */
        }
      })
    );
  }

  function setFeedStatus(live) {
    const el = $('#feedStatus');
    el.dataset.state = live ? 'live' : 'sample';
    $('.ticker__status-label', el).textContent = live ? 'LIVE' : 'SAMPLE';
    el.title = live ? '크립토 시세: Binance 공개 API 실시간 · 매크로: 샘플' : '실시간 연결 실패 — 모든 시세가 샘플 데이터입니다';
  }

  /* ---------- 티커 ---------- */
  function tickerItem(a, unit) {
    const dir = dirOf(a.chg);
    return `<span class="ticker__item" data-sym="${a.sym}"><b>${a.sym}</b><span class="px">${fmtPrice(a.price, unit || a.unit)}</span><span class="chg ${dir}">${dir === 'up' ? ARROW_UP : ARROW_DOWN}<span class="v">${fmtChg(a.chg)}</span></span></span>`;
  }
  function renderTicker() {
    const items = [...market.crypto, ...market.macro].map((a) => tickerItem(a)).join('');
    const track = $('#tickerTrack');
    // 두 벌을 이어 붙여 -50% 이동으로 끊김 없는 루프를 만든다
    track.innerHTML = items + items.replace(/class="ticker__item"/g, 'class="ticker__item" aria-hidden="true"');
  }

  function updateAssetDOM(a, prev) {
    const dir = dirOf(a.chg);
    const flash = a.price > prev ? 'flash-up' : a.price < prev ? 'flash-down' : '';
    $$(`[data-sym="${a.sym}"]`).forEach((el) => {
      const px = $('.px', el) || $('.quote__px', el);
      if (px) {
        px.textContent = (el.classList.contains('quote') && market.crypto.includes(a) ? '$' : '') + fmtPrice(a.price, a.unit);
        if (flash && !reduced()) {
          px.classList.remove('flash-up', 'flash-down');
          void px.offsetWidth;
          px.classList.add(flash);
        }
      }
      const chg = $('.chg', el) || $('.quote__chg', el);
      if (chg) {
        chg.classList.toggle('up', dir === 'up');
        chg.classList.toggle('down', dir === 'down');
        chg.innerHTML = (dir === 'up' ? ARROW_UP : ARROW_DOWN) + `<span class="v">${fmtChg(a.chg)}</span>`;
      }
      if (el.classList.contains('heat__cell')) {
        el.style.setProperty('--cell', heatColor(a.chg));
        const s = $('span', el);
        if (s) s.textContent = fmtChg(a.chg);
      }
      if (el.classList.contains('quote')) {
        const svg = $('.spark', el);
        if (svg) updateSpark(svg, a.series, dir);
      }
    });
  }

  /* ---------- 스파크라인 ---------- */
  function sparkPaths(series, w = 200, h = 44) {
    const min = Math.min(...series);
    const max = Math.max(...series);
    const span = max - min || 1;
    const pts = series.map((v, i) => [(i / (series.length - 1)) * w, h - 3 - ((v - min) / span) * (h - 6)]);
    const line = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
    return { line, area: `${line} L${w} ${h} L0 ${h} Z` };
  }
  function sparkSVG(series, dir) {
    const { line, area } = sparkPaths(series);
    return `<svg class="spark ${dir}" viewBox="0 0 200 44" preserveAspectRatio="none" aria-hidden="true"><path class="area" d="${area}"/><path class="line" d="${line}" vector-effect="non-scaling-stroke"/></svg>`;
  }
  function updateSpark(svg, series, dir) {
    const { line, area } = sparkPaths(series);
    $('.line', svg).setAttribute('d', line);
    $('.area', svg).setAttribute('d', area);
    svg.classList.toggle('up', dir === 'up');
    svg.classList.toggle('down', dir === 'down');
  }
  function primeSparks(root) {
    $$('.spark', root).forEach((svg) => {
      const p = $('.line', svg);
      // non-scaling-stroke라 실제 픽셀 길이를 넉넉히 잡는다
      const len = Math.ceil(p.getTotalLength() * 3) + 20;
      svg.style.setProperty('--len', len);
      revealObserver.observe(svg);
    });
  }

  /* ---------- 마켓 카드 + 히트맵 ---------- */
  function renderQuotes() {
    const list = market[market.seg].slice(0, 8);
    const isCrypto = market.seg === 'crypto';
    $('#quotes').innerHTML = list
      .map((a) => {
        const dir = dirOf(a.chg);
        return `<article class="quote" data-sym="${a.sym}">
          <div class="quote__sym"><span class="quote__badge">${esc(a.sym.slice(0, 3))}</span><div><b>${esc(a.sym)}</b><span>${esc(a.name)}</span></div></div>
          <span class="quote__chg ${dir}">${dir === 'up' ? ARROW_UP : ARROW_DOWN}<span class="v">${fmtChg(a.chg)}</span></span>
          <div class="quote__px">${isCrypto ? '$' : ''}${fmtPrice(a.price, a.unit)}</div>
          ${sparkSVG(a.series, dir)}
        </article>`;
      })
      .join('');
    primeSparks($('#quotes'));
  }

  function heatColor(chg) {
    const k = Math.min(Math.abs(chg) / 5, 1);
    const pct = Math.round(28 + k * 62);
    return `color-mix(in oklab, var(--${chg >= 0 ? 'up' : 'down'}) ${pct}%, var(--heat-neutral))`;
  }
  // 빈칸 없이 맞물리도록 손으로 정한 스팬 [데스크톱 c, r, 모바일 c, r] — 데스크톱 6열, 모바일 4열
  const HEAT_SPANS = {
    BTC: [3, 3, 4, 2], ETH: [3, 2, 2, 2], SOL: [2, 1, 2, 1], XRP: [2, 1, 2, 1], BNB: [2, 1, 2, 1], DOGE: [2, 1, 2, 1],
    ADA: [2, 1, 2, 1], LINK: [1, 1, 2, 1],
    SPX: [3, 2, 2, 2], NDX: [3, 2, 2, 2],
  };
  function heatSpan(a, seg) {
    const sp = HEAT_SPANS[a.sym] || (seg === 'macro' ? [2, 1, 2, 1] : [1, 1, 1, 1]);
    return `--c:${sp[0]}; --r:${sp[1]}; --mc:${sp[2]}; --mr:${sp[3]};`;
  }
  function renderHeat() {
    const seg = market.seg;
    const heat = $('#heat');
    heat.innerHTML = market[seg]
      .map((a, i) => {
        const big = ['BTC', 'ETH', 'SPX', 'NDX'].includes(a.sym);
        return `<div class="heat__cell${big ? ' lg' : ''}" data-sym="${a.sym}" style="${heatSpan(a, seg)} --cell:${heatColor(a.chg)}; --i:${i}" title="${esc(a.name)} ${fmtChg(a.chg)}">
          ${a.chg >= 0 ? ARROW_UP : ARROW_DOWN}<b>${esc(a.sym)}</b><span>${fmtChg(a.chg)}</span></div>`;
      })
      .join('');
    heat.classList.remove('is-in');
    revealObserver.observe(heat);
  }

  function initSegment() {
    const seg = $('#marketSeg');
    seg.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b || b.getAttribute('aria-selected') === 'true') return;
      $$('button', seg).forEach((x) => x.setAttribute('aria-selected', String(x === b)));
      seg.dataset.active = b.dataset.m === 'macro' ? '1' : '0';
      market.seg = b.dataset.m;
      renderQuotes();
      renderHeat();
    });
  }

  /* 실시간이면 주기적으로 다시 받고, 아니면 작은 무작위 틱을 흉내 낸다 */
  function startMarketLoop() {
    if (market.live) {
      setInterval(async () => {
        if (document.hidden) return;
        const prev = market.crypto.map((c) => c.price);
        const ok = await loadLiveTickers();
        if (ok) market.crypto.forEach((c, i) => updateAssetDOM(c, prev[i]));
      }, 15000);
    }
    setInterval(() => {
      if (document.hidden) return;
      const pool = market.live ? market.macro : [...market.crypto, ...market.macro];
      for (let n = 0; n < 3; n++) {
        const a = pool[Math.floor(Math.random() * pool.length)];
        const prev = a.price;
        const open = a.base / (1 + a.chg / 100);
        a.price = a.price * (1 + (Math.random() - 0.5) * 0.0016);
        a.chg = (a.price / open - 1) * 100;
        a.base = a.price;
        a.series.push(a.price);
        a.series.shift();
        updateAssetDOM(a, prev);
      }
    }, 2600);
  }

  /* ---------- 탭 (카테고리) ---------- */
  let currentCat = 'all';
  function placePill(list, pill) {
    const active = $('[aria-selected="true"]', list);
    if (!active) return;
    pill.style.width = active.offsetWidth + 'px';
    pill.style.transform = `translateX(${active.offsetLeft}px)`;
  }
  function initTabs() {
    const list = $('#catTabs');
    const pill = $('.tabs__pill', list);
    // 첫 배치는 애니메이션 없이
    pill.style.transition = 'none';
    placePill(list, pill);
    requestAnimationFrame(() => requestAnimationFrame(() => (pill.style.transition = '')));
    window.addEventListener('resize', () => placePill(list, pill));
    document.fonts && document.fonts.ready.then(() => placePill(list, pill));

    list.addEventListener('click', (e) => {
      const tab = e.target.closest('.tab');
      if (!tab) return;
      setCategory(tab.dataset.cat);
    });
    list.addEventListener('keydown', (e) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
      const tabs = $$('.tab', list);
      const i = tabs.findIndex((t) => t.getAttribute('aria-selected') === 'true');
      const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
      next.focus();
      setCategory(next.dataset.cat);
    });
  }
  function setCategory(cat, opts = {}) {
    if (cat === currentCat) return;
    currentCat = cat;
    const list = $('#catTabs');
    $$('.tab', list).forEach((t) => {
      const on = t.dataset.cat === cat;
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
    });
    placePill(list, $('.tabs__pill', list));
    $$('#bento .card').forEach((c) => {
      const dim = cat !== 'all' && c.dataset.cat !== cat;
      c.style.opacity = dim ? '0.3' : '';
      c.style.transition = 'opacity 250ms ease, box-shadow 150ms ease-out, transform 150ms ease-out';
    });
    renderStream(true);
    if (!opts.silent && window.scrollY < $('#top').offsetTop - 200) {
      toast(`${cat === 'all' ? '전체' : D.categories[cat].label} 시그널만 보고 있어요`, cat === 'all' ? null : cat);
    }
  }

  /* ---------- 벤토 ---------- */
  function coverStyle(cat) {
    const [c1, c2] = COVER[cat];
    return `--c1:${c1}; --c2:${c2}`;
  }
  function impactHTML(lv) {
    const label = { high: '영향도 높음', med: '영향도 보통', low: '영향도 낮음' }[lv];
    return `<span class="impact" data-lv="${lv}" role="img" aria-label="${label}"><i></i><i></i><i></i></span>`;
  }
  function kickerHTML(s) {
    return `<div class="card__kicker"><span class="chip cat-chip cat-chip--${s.cat}">${D.categories[s.cat].en}</span>${impactHTML(s.impact)}<span class="card__time">${s.time} KST</span></div>`;
  }
  function orbitArt() {
    const rings = [70, 120, 170, 220, 270].map((r) => `<circle class="ring" cx="300" cy="300" r="${r}"/>`).join('');
    return `<svg class="cover__art" viewBox="0 0 600 600" aria-hidden="true">${rings}
      <g class="orbit"><circle class="node" cx="300" cy="80" r="6"/><circle class="node" cx="520" cy="300" r="3.5"/></g>
      <g class="orbit orbit--rev"><circle class="node" cx="300" cy="180" r="4"/><circle class="node" cx="130" cy="300" r="5"/><circle class="node" cx="300" cy="570" r="3"/></g></svg>`;
  }
  const GLYPH = '<span class="card__glyph" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="M5 15 15 5M7 5h8v8"/></svg></span>';

  function renderBento() {
    const byId = Object.fromEntries(D.stories.map((s) => [s.id, s]));
    const feature = D.stories.find((s) => s.feature);
    const layout = [
      { s: feature, cls: 'card--feature' },
      { s: byId.s2, cls: 'card--tile card--block-ai' },
      { s: byId.s3, cls: 'card--tile card--block-macro' },
      { s: byId.s4, cls: 'card--wide' },
      { s: byId.s5, cls: 'card--wide' },
    ];
    $('#bento').innerHTML = layout
      .map(({ s, cls }, i) => {
        const isFeature = cls.includes('feature');
        const extra = isFeature
          ? `<div class="cover" style="${coverStyle(s.cat)}">${orbitArt()}</div><span class="cover__big" aria-hidden="true">${esc(s.tags[0])}</span>`
          : cls.includes('wide')
          ? `<div class="card__pattern" aria-hidden="true"></div>${GLYPH}`
          : GLYPH;
        return `<button class="card ${cls} reveal" data-id="${s.id}" data-cat="${s.cat}" style="transition-delay:${i * 60}ms">
          ${extra}
          <div class="card__body">${kickerHTML(s)}<h3 class="card__title">${esc(s.title)}</h3>${isFeature || cls.includes('wide') ? `<p class="card__sum">${esc(s.summary)}</p>` : ''}</div>
        </button>`;
      })
      .join('');
    $$('#bento .card').forEach((c) => revealObserver.observe(c));
  }

  /* 카드 스포트라이트: 포인터 위치를 CSS 변수로 */
  function initSpotlight() {
    if (!finePointer) return;
    document.addEventListener('pointermove', (e) => {
      const card = e.target.closest && e.target.closest('.card');
      if (!card) return;
      const r = card.getBoundingClientRect();
      card.style.setProperty('--mx', e.clientX - r.left + 'px');
      card.style.setProperty('--my', e.clientY - r.top + 'px');
    }, { passive: true });
  }

  /* ---------- 스트림 ---------- */
  let streamItems = D.stories.slice();
  let visibleCount = 8;
  function streamItemHTML(s, i, isNew) {
    return `<li class="s-item enter${isNew ? ' is-new' : ''}" style="--i:${i}; --c:var(${CAT_VAR[s.cat]})" data-cat="${s.cat}">
      <time class="s-item__time">${s.time}</time>
      <span class="s-item__dot" aria-hidden="true"></span>
      <button class="s-card" data-id="${s.id}">
        <div class="s-card__top"><span class="chip cat-chip cat-chip--${s.cat}">${D.categories[s.cat].en}</span>${impactHTML(s.impact)}<span class="card__time">${s.read}분 읽기</span>${CHEV}</div>
        <h3 class="s-card__title">${esc(s.title)}</h3>
        <p class="s-card__sum">${esc(s.summary)}</p>
        <div class="s-card__tags">${s.tags.map((t) => `<span class="tag">#${esc(t)}</span>`).join('')}</div>
      </button>
    </li>`;
  }
  function filtered() {
    return streamItems.filter((s) => currentCat === 'all' || s.cat === currentCat);
  }
  function renderStream(animate) {
    const list = filtered();
    const shown = list.slice(0, visibleCount);
    const el = $('#streamList');
    el.innerHTML = shown.length
      ? shown.map((s, i) => streamItemHTML(s, animate ? Math.min(i, 8) : 0)).join('')
      : '<li class="stream__empty">이 카테고리에 표시할 시그널이 없어요.</li>';
    if (!animate) $$('.s-item', el).forEach((li) => li.classList.remove('enter'));
    $('#loadMore').hidden = list.length <= visibleCount;
  }
  function initStream() {
    renderStream(false);
    $('#loadMore').addEventListener('click', () => {
      const before = filtered().slice(0, visibleCount).length;
      visibleCount += 6;
      const list = filtered().slice(before, visibleCount);
      const el = $('#streamList');
      el.insertAdjacentHTML('beforeend', list.map((s, i) => streamItemHTML(s, i)).join(''));
      $('#loadMore').hidden = filtered().length <= visibleCount;
    });

    // 몇 초 뒤 새 시그널이 도착한 것처럼 보여 준다
    const pill = $('#newPill');
    setTimeout(() => {
      $('#newPillText').textContent = `새 시그널 ${D.incoming.length}건`;
      pill.hidden = false;
      toast(`새 시그널 ${D.incoming.length}건이 도착했어요`, 'macro');
    }, 9000);
    pill.addEventListener('click', () => {
      pill.hidden = true;
      streamItems = [...D.incoming, ...streamItems];
      visibleCount += D.incoming.length;
      const el = $('#streamList');
      const fresh = D.incoming.filter((s) => currentCat === 'all' || s.cat === currentCat);
      el.insertAdjacentHTML('afterbegin', fresh.map((s, i) => streamItemHTML(s, i, true)).join(''));
      $('.stream__empty', el)?.remove();
      const top = $('#stream').getBoundingClientRect().top + window.scrollY - 80;
      if (window.scrollY > top) window.scrollTo({ top, behavior: reduced() ? 'auto' : 'smooth' });
    });
  }

  /* ---------- 레일 ---------- */
  function renderRail() {
    $('#trendList').innerHTML = D.trending
      .map((t, i) => {
        const dir = dirOf(t.d);
        return `<li><span class="trend__rank">${String(i + 1).padStart(2, '0')}</span><span class="trend__k">${esc(t.k)}<small>${t.n.toLocaleString('ko-KR')} 언급</small></span><span class="trend__d ${dir}">${dir === 'up' ? ARROW_UP : ARROW_DOWN}${Math.abs(t.d)}%</span></li>`;
      })
      .join('');
    $('#calList').innerHTML = D.calendar
      .map(
        (c) => `<li><div class="cal__date"><b>${c.d}</b>${c.w} ${c.t}</div><div><div class="cal__name">${esc(c.name)}</div>
        <div class="cal__meta"><i class="cat-dot cat-dot--${c.cat}" aria-hidden="true"></i>${D.categories[c.cat].label}<span class="stars" data-lv="${c.lv}" role="img" aria-label="중요도 ${c.lv}/3"><i></i><i></i><i></i></span></div></div></li>`
      )
      .join('');
  }

  /* ---------- AI 레이더 ---------- */
  function renderRadar() {
    const el = $('#radar');
    el.innerHTML = D.radar
      .map(
        (r) => `<article class="r-card">
        <div class="r-card__top"><span class="chip r-card__kind">${esc(r.kind)}</span><span class="mono-label">SIGNAL SCORE</span></div>
        <div class="r-card__row">
          <div class="ring-score" style="--s:${r.score}"><svg viewBox="0 0 72 72" aria-hidden="true"><circle class="bg" cx="36" cy="36" r="30" pathLength="100"/><circle class="fg" cx="36" cy="36" r="30" pathLength="100"/></svg><span>${r.score}</span></div>
          <div class="r-card__delta">${r.delta}<small>7일 변화</small></div>
        </div>
        <h3 class="r-card__title">${esc(r.title)}</h3>
        <p class="r-card__meta">${esc(r.meta)}</p>
        <p class="r-card__note">${esc(r.note)}</p>
      </article>`
      )
      .join('');
    $$('.r-card', el).forEach((c) => revealObserver.observe(c));

    const btns = $$('.scroller-ctrl .icon-btn');
    const sync = () => {
      btns[0].disabled = el.scrollLeft < 4;
      btns[1].disabled = el.scrollLeft + el.clientWidth >= el.scrollWidth - 4;
    };
    btns.forEach((b) =>
      b.addEventListener('click', () => {
        const step = ($('.r-card', el)?.offsetWidth || 320) + 12;
        el.scrollBy({ left: step * Number(b.dataset.dir), behavior: reduced() ? 'auto' : 'smooth' });
      })
    );
    el.addEventListener('scroll', sync, { passive: true });
    window.addEventListener('resize', sync);
    sync();
  }

  /* ---------- 리빌 옵저버 ---------- */
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const t = e.target;
        if (t.classList.contains('spark')) t.classList.add('is-drawn');
        else t.classList.add('is-in');
        revealObserver.unobserve(t);
        // 리빌이 끝나면 클래스를 걷어 내 hover·press 트랜지션이 원래 속도로 돌아오게 한다
        if (t.classList.contains('reveal')) {
          setTimeout(() => {
            t.classList.remove('reveal', 'is-in');
            t.style.transitionDelay = '';
          }, 1100 + (parseFloat(t.style.transitionDelay) || 0));
        }
      });
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.12 }
  );

  /* ---------- 드로어 ---------- */
  const drawer = $('#drawer');
  const panel = $('.drawer__panel', drawer);
  let lastFocus = null;

  function findStory(id) {
    return [...D.stories, ...D.incoming].find((s) => s.id === id);
  }
  function openDrawer(id) {
    const s = findStory(id);
    if (!s) return;
    const related = [...D.stories, ...D.incoming].filter((x) => x.cat === s.cat && x.id !== s.id).slice(0, 3);
    $('#drawerBody').innerHTML = `
      <div class="d-cover"><div class="cover" style="${coverStyle(s.cat)}">${orbitArt()}</div></div>
      <div class="d-content" style="--c:var(${CAT_VAR[s.cat]})">
        <div class="d-meta">${kickerHTML(s)}<span class="card__time">· ${s.read}분 읽기</span></div>
        <h2 class="d-title" id="drawerTitle">${esc(s.title)}</h2>
        <p class="d-sum"><b>TL;DR</b>${esc(s.summary)}</p>
        <div class="d-body">${s.body.map((p) => `<p>${esc(p)}</p>`).join('')}</div>
        <div class="s-card__tags">${s.tags.map((t) => `<span class="tag">#${esc(t)}</span>`).join('')}</div>
        ${related.length ? `<div class="d-related"><p class="mono-label">RELATED</p>${related.map((r) => `<button data-id="${r.id}">${esc(r.title)}<span>${r.time}</span></button>`).join('')}</div>` : ''}
        <p class="d-disclaimer">샘플 기사입니다. 실제 사건이나 수치가 아닙니다.</p>
      </div>`;
    $('#drawerBody').scrollTop = 0;
    if (!drawer.classList.contains('is-open')) lastFocus = document.activeElement;
    drawer.classList.add('is-open');
    drawer.setAttribute('aria-hidden', 'false');
    document.documentElement.style.overflow = 'hidden';
    panel.focus({ preventScroll: true });
  }
  function closeDrawer() {
    if (!drawer.classList.contains('is-open')) return;
    drawer.classList.remove('is-open');
    drawer.setAttribute('aria-hidden', 'true');
    document.documentElement.style.overflow = '';
    panel.style.transform = '';
    panel.style.transition = '';
    lastFocus && lastFocus.focus && lastFocus.focus({ preventScroll: true });
  }
  function initDrawer() {
    document.addEventListener('click', (e) => {
      const opener = e.target.closest('[data-id]');
      if (opener && !e.target.closest('.cmdk')) {
        openDrawer(opener.dataset.id);
        return;
      }
      if (e.target.closest('#drawer [data-close]')) closeDrawer();
    });
    // 포커스 가두기
    panel.addEventListener('keydown', (e) => {
      if (e.key !== 'Tab') return;
      const f = $$('button, a[href], input, [tabindex]:not([tabindex="-1"])', panel).filter((x) => !x.disabled);
      if (!f.length) return;
      const first = f[0];
      const last = f[f.length - 1];
      if (e.shiftKey && (document.activeElement === first || document.activeElement === panel)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    });

    // 모바일 바텀 시트: 손잡이를 끌어 내리면 닫힘. 거리 대신 속도로도 판정 (빠르게 튕기면 닫힘)
    const grab = $('.drawer__grab', drawer);
    let start = null;
    grab.addEventListener('pointerdown', (e) => {
      if (!mobileMQ.matches) return;
      start = { y: e.clientY, t: performance.now() };
      grab.setPointerCapture(e.pointerId);
      panel.style.transition = 'none';
    });
    grab.addEventListener('pointermove', (e) => {
      if (!start) return;
      let dy = e.clientY - start.y;
      if (dy < 0) dy = -Math.sqrt(-dy) * 2; // 위로는 저항을 준다
      panel.style.transform = `translateY(${dy}px)`;
    });
    const end = (e) => {
      if (!start) return;
      const dy = e.clientY - start.y;
      const v = dy / Math.max(1, performance.now() - start.t);
      start = null;
      panel.style.transition = '';
      if (dy > 120 || v > 0.11) closeDrawer();
      else panel.style.transform = '';
    };
    grab.addEventListener('pointerup', end);
    grab.addEventListener('pointercancel', end);
  }

  /* ---------- 커맨드 팔레트 ---------- */
  const cmdk = $('#cmdk');
  const cInput = $('#cmdkInput');
  let cResults = [];
  let cIndex = 0;
  let cmdkReturn = null;

  function highlight(text, q) {
    if (!q) return esc(text);
    const i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) return esc(text);
    return esc(text.slice(0, i)) + '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' + esc(text.slice(i + q.length));
  }
  function runSearch() {
    const q = cInput.value.trim();
    const ql = q.toLowerCase();
    const stories = [...D.incoming, ...D.stories].filter(
      (s) => !q || s.title.toLowerCase().includes(ql) || s.tags.some((t) => t.toLowerCase().includes(ql)) || D.categories[s.cat].label.includes(q) || s.cat.includes(ql)
    );
    const assets = [...market.crypto, ...market.macro].filter((a) => q && (a.sym.toLowerCase().includes(ql) || a.name.toLowerCase().includes(ql)));
    cResults = [
      ...assets.slice(0, 4).map((a) => ({ type: 'asset', a })),
      ...stories.slice(0, q ? 12 : 6).map((s) => ({ type: 'story', s })),
    ];
    cIndex = 0;
    let html = '';
    let idx = 0;
    if (assets.length) {
      html += '<li class="cmdk__group" role="presentation">ASSETS</li>';
      html += assets.slice(0, 4).map((a) => {
        const dir = dirOf(a.chg);
        return `<li class="cmdk__item" role="option" id="c${idx}" data-i="${idx++}" aria-selected="false"><span class="t"><b>${highlight(a.sym, q)}</b> · ${highlight(a.name, q)}</span><span class="m ${dir}">${fmtPrice(a.price, a.unit)} ${fmtChg(a.chg)}</span></li>`;
      }).join('');
    }
    const sl = cResults.filter((r) => r.type === 'story');
    if (sl.length) {
      html += `<li class="cmdk__group" role="presentation">${q ? 'SIGNALS' : 'LATEST SIGNALS'}</li>`;
      html += sl.map(({ s }) => `<li class="cmdk__item" role="option" id="c${idx}" data-i="${idx++}" aria-selected="false"><i class="cat-dot cat-dot--${s.cat}" aria-hidden="true"></i><span class="t">${highlight(s.title, q)}</span><span class="m">${s.time}</span></li>`).join('');
    }
    $('#cmdkList').innerHTML = html || `<li class="cmdk__empty">‘${esc(q)}’에 맞는 결과가 없어요. 다른 키워드로 찾아보세요.</li>`;
    selectResult(0);
  }
  function selectResult(i) {
    const items = $$('.cmdk__item', cmdk);
    if (!items.length) return;
    cIndex = (i + items.length) % items.length;
    items.forEach((el, n) => el.setAttribute('aria-selected', String(n === cIndex)));
    items[cIndex].scrollIntoView({ block: 'nearest' });
    cInput.setAttribute('aria-activedescendant', 'c' + cIndex);
  }
  function chooseResult(i) {
    const r = cResults[i];
    if (!r) return;
    closeCmdk(false);
    if (r.type === 'story') openDrawer(r.s.id);
    else {
      const seg = market.crypto.includes(r.a) ? 'crypto' : 'macro';
      if (market.seg !== seg) $(`#marketSeg [data-m="${seg}"]`).click();
      $('#markets').scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth' });
    }
  }
  function openCmdk() {
    cmdkReturn = document.activeElement;
    cmdk.hidden = false;
    cInput.value = '';
    runSearch();
    cInput.focus();
    document.documentElement.style.overflow = 'hidden';
  }
  function closeCmdk(restore = true) {
    if (cmdk.hidden) return;
    cmdk.hidden = true;
    if (!drawer.classList.contains('is-open')) document.documentElement.style.overflow = '';
    if (restore && cmdkReturn && cmdkReturn.focus) cmdkReturn.focus({ preventScroll: true });
  }
  function initCmdk() {
    $('#openSearch').addEventListener('click', openCmdk);
    cInput.addEventListener('input', runSearch);
    cInput.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); selectResult(cIndex + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); selectResult(cIndex - 1); }
      else if (e.key === 'Enter') { e.preventDefault(); chooseResult(cIndex); }
    });
    $('#cmdkList').addEventListener('click', (e) => {
      const it = e.target.closest('.cmdk__item');
      if (it) chooseResult(Number(it.dataset.i));
    });
    $('#cmdkList').addEventListener('pointermove', (e) => {
      const it = e.target.closest('.cmdk__item');
      if (it && Number(it.dataset.i) !== cIndex) selectResult(Number(it.dataset.i));
    });
    cmdk.addEventListener('click', (e) => { if (e.target.matches('[data-close]')) closeCmdk(); });

    document.addEventListener('keydown', (e) => {
      const typing = /INPUT|TEXTAREA/.test(document.activeElement?.tagName || '');
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        cmdk.hidden ? openCmdk() : closeCmdk();
      } else if (e.key === '/' && !typing && cmdk.hidden) {
        e.preventDefault();
        openCmdk();
      } else if (e.key === 'Escape') {
        if (!cmdk.hidden) closeCmdk();
        else closeDrawer();
      }
    });
  }

  /* ---------- 토스트 ---------- */
  function toast(msg, cat) {
    const ol = $('#toasts');
    const li = document.createElement('li');
    li.className = 'toast';
    li.innerHTML = (cat ? `<i class="cat-dot cat-dot--${cat}" aria-hidden="true"></i>` : '') + `<span>${esc(msg)}</span>`;
    ol.appendChild(li);
    while (ol.children.length > 3) ol.firstElementChild.remove();
    setTimeout(() => {
      li.classList.add('is-leaving');
      setTimeout(() => li.remove(), 200);
    }, 3200);
  }

  /* ---------- 테마 ---------- */
  function initTheme() {
    const btn = $('#themeToggle');
    const meta = $('meta[name="theme-color"]');
    const sync = () => {
      const dark = document.documentElement.dataset.theme !== 'light';
      btn.setAttribute('aria-label', dark ? '라이트 모드로 전환' : '다크 모드로 전환');
      meta.setAttribute('content', dark ? '#0d0d10' : '#fbfaf7');
    };
    sync();
    btn.addEventListener('click', () => {
      const root = document.documentElement;
      const next = root.dataset.theme === 'light' ? 'dark' : 'light';
      // 색상 트랜지션이 한꺼번에 번지지 않도록 전환 순간에만 끈다
      root.classList.add('no-transitions');
      root.dataset.theme = next;
      void root.offsetWidth;
      requestAnimationFrame(() => root.classList.remove('no-transitions'));
      try { localStorage.setItem('signal-theme', next); } catch (e) {}
      sync();
      flow && flow.refreshColors();
    });
  }

  /* ---------- 내비 스크롤 상태 ---------- */
  function initNav() {
    const nav = $('#nav');
    const onScroll = () => nav.classList.toggle('is-scrolled', window.scrollY > 8);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ---------- 시계 ---------- */
  function initClock() {
    const dateEl = $('#heroDate');
    const clockEl = $('#heroClock');
    const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
    const tick = () => {
      const kst = new Date(Date.now() + 9 * 3600 * 1000);
      const p = (n) => String(n).padStart(2, '0');
      dateEl.textContent = `${kst.getUTCFullYear()}.${p(kst.getUTCMonth() + 1)}.${p(kst.getUTCDate())} ${days[kst.getUTCDay()]}`;
      clockEl.textContent = `${p(kst.getUTCHours())}:${p(kst.getUTCMinutes())}`;
    };
    tick();
    setInterval(tick, 10000);
  }

  /* ---------- 숫자 카운트업 ---------- */
  function countUp() {
    const ease = (t) => 1 - Math.pow(1 - t, 4);
    $$('.count').forEach((el, i) => {
      const to = Number(el.dataset.to);
      if (reduced()) { el.textContent = to.toLocaleString('en-US'); return; }
      const dur = 1600;
      const t0 = performance.now() + 700 + i * 120;
      const step = (now) => {
        const k = Math.min(1, Math.max(0, (now - t0) / dur));
        el.textContent = Math.round(to * ease(k)).toLocaleString('en-US');
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }

  /* ---------- 게이지 (스프링 바늘) ---------- */
  function initGauge() {
    const value = 68;
    const fill = $('#gaugeFill');
    const needle = $('#gaugeNeedle');
    const out = $('#gaugeValue');
    const label = $('#gaugeLabel');
    const len = fill.getTotalLength();
    fill.style.strokeDasharray = len;
    fill.style.strokeDashoffset = len;
    const zone = value >= 75 ? '극단적 탐욕' : value >= 55 ? '탐욕' : value >= 45 ? '중립' : value >= 25 ? '공포' : '극단적 공포';
    const target = (value / 100) * 180 - 90;
    requestAnimationFrame(() => requestAnimationFrame(() => $('.pulse').classList.add('is-ready')));

    if (reduced()) {
      needle.style.transform = `rotate(${target}deg)`;
      fill.style.strokeDashoffset = len * (1 - value / 100);
      out.textContent = value;
      label.textContent = `공포·탐욕 지수 · ${zone}`;
      return;
    }
    // 장식용 바늘이라 스프링으로 살짝 출렁이게 (bounce 약하게)
    let x = -90, v = 0;
    const k = 120, c = 14;
    let last = null;
    const delay = performance.now() + 900;
    const frame = (now) => {
      if (now < delay) return requestAnimationFrame(frame);
      const dt = Math.min(0.032, last ? (now - last) / 1000 : 0.016);
      last = now;
      const a = -k * (x - target) - c * v;
      v += a * dt;
      x += v * dt;
      needle.style.transform = `rotate(${x}deg)`;
      const pct = Math.max(0, Math.min(1, (x + 90) / 180));
      fill.style.strokeDashoffset = len * (1 - pct);
      out.textContent = Math.round(pct * 100);
      if (Math.abs(v) > 0.05 || Math.abs(x - target) > 0.05) requestAnimationFrame(frame);
      else {
        needle.style.transform = `rotate(${target}deg)`;
        out.textContent = value;
        label.textContent = `공포·탐욕 지수 · ${zone}`;
      }
    };
    requestAnimationFrame(frame);
  }

  /* ---------- 브리프 폼 ---------- */
  function initBrief() {
    const form = $('#briefForm');
    const note = $('#briefNote');
    const input = $('#email');
    const defaultNote = note.textContent;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const ok = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(input.value.trim());
      form.classList.remove('is-error');
      note.classList.remove('is-error', 'is-ok');
      if (!ok) {
        void form.offsetWidth;
        form.classList.add('is-error');
        note.classList.add('is-error');
        note.textContent = '이메일 주소 형식을 확인해 주세요. 예: you@example.com';
        input.setAttribute('aria-invalid', 'true');
        input.focus();
        return;
      }
      input.removeAttribute('aria-invalid');
      note.classList.add('is-ok');
      note.textContent = '구독 신청을 받았어요. 데모라 실제 메일은 가지 않습니다.';
      $('.brief__btn-label', form).textContent = '신청 완료';
      input.value = '';
      toast('모닝 브리프 구독 신청 완료', null);
      setTimeout(() => {
        $('.brief__btn-label', form).textContent = '구독하기';
        note.classList.remove('is-ok');
        note.textContent = defaultNote;
      }, 5000);
    });
  }

  /* ---------- 히어로 캔버스: 흐르는 시그널 라인 ---------- */
  let flow = null;
  function initFlow() {
    const canvas = $('#flowCanvas');
    const ctx = canvas.getContext('2d');
    let w = 0, h = 0, dpr = 1;
    let colors = {};
    let running = false;
    let visible = true;
    let t = Math.random() * 100;
    // 장식용 포인터 추적은 스프링으로 따라오게
    const target = { x: 0.7, y: 0.5, on: 0 };
    const pos = { x: 0.7, y: 0.5, on: 0, vx: 0, vy: 0, von: 0 };

    function readColors() {
      const cs = getComputedStyle(document.documentElement);
      const probe = document.createElement('i');
      document.body.appendChild(probe);
      const resolve = (v) => {
        probe.style.color = cs.getPropertyValue(v).trim();
        return getComputedStyle(probe).color;
      };
      colors = { a: resolve('--accent'), b: resolve('--ai'), c: resolve('--macro'), light: document.documentElement.dataset.theme === 'light' };
      probe.remove();
    }
    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      const r = canvas.getBoundingClientRect();
      w = r.width; h = r.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (!running) draw();
    }
    function draw() {
      ctx.clearRect(0, 0, w, h);
      const lines = w < 640 ? 18 : 30;
      const step = w < 640 ? 10 : 8;
      const cx = pos.x * w;
      const cy = pos.y * h;
      ctx.lineWidth = 1;
      for (let i = 0; i < lines; i++) {
        const k = i / (lines - 1);
        const base = h * (0.38 + k * 0.5);
        const amp = h * (0.05 + 0.07 * Math.sin(k * Math.PI));
        const col = k < 0.5 ? colors.a : k < 0.8 ? colors.c : colors.b;
        ctx.strokeStyle = col;
        ctx.globalAlpha = (colors.light ? 0.28 : 0.2) + 0.35 * Math.pow(Math.sin(k * Math.PI), 3);
        ctx.beginPath();
        for (let x = -10; x <= w + 10; x += step) {
          const nx = x / w;
          let y = base
            + Math.sin(nx * 6.2 + t * 0.6 + k * 2.4) * amp
            + Math.sin(nx * 13.7 - t * 0.9 + k * 5.1) * amp * 0.28
            + Math.cos(nx * 2.3 + t * 0.25 + k) * amp * 0.6;
          // 포인터 근처에서 라인이 부풀어 오른다
          const dx = x - cx;
          const dy = base - cy;
          const d2 = (dx * dx) / (w * w * 0.02) + (dy * dy) / (h * h * 0.06);
          y -= Math.exp(-d2) * h * 0.09 * pos.on * (k - 0.3);
          x === -10 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    function spring(dt) {
      const k = 60, c = 12;
      for (const [p, vp] of [['x', 'vx'], ['y', 'vy'], ['on', 'von']]) {
        const a = -k * (pos[p] - target[p]) - c * pos[vp];
        pos[vp] += a * dt;
        pos[p] += pos[vp] * dt;
      }
    }
    let last = 0;
    function loop(now) {
      if (!running) return;
      const dt = Math.min(0.033, last ? (now - last) / 1000 : 0.016);
      last = now;
      t += dt;
      spring(dt);
      draw();
      requestAnimationFrame(loop);
    }
    function start() {
      if (running || reduced() || !visible || document.hidden) return;
      running = true;
      last = 0;
      requestAnimationFrame(loop);
    }
    function stop() { running = false; }

    readColors();
    resize();
    window.addEventListener('resize', resize);
    if (finePointer) {
      const hero = $('.hero');
      hero.addEventListener('pointermove', (e) => {
        const r = canvas.getBoundingClientRect();
        target.x = (e.clientX - r.left) / r.width;
        target.y = (e.clientY - r.top) / r.height;
        target.on = 1;
      });
      hero.addEventListener('pointerleave', () => (target.on = 0));
    }
    new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      visible ? start() : stop();
    }).observe(canvas);
    document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
    reduceMQ.addEventListener('change', () => (reduced() ? (stop(), draw()) : start()));
    start();
    return { refreshColors() { readColors(); if (!running) draw(); } };
  }

  /* ---------- 공용 SVG 그라디언트 ---------- */
  function injectDefs() {
    document.body.insertAdjacentHTML(
      'afterbegin',
      `<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
        <linearGradient id="gUp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--up)" stop-opacity=".28"/><stop offset="1" stop-color="var(--up)" stop-opacity="0"/></linearGradient>
        <linearGradient id="gDown" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--down)" stop-opacity=".28"/><stop offset="1" stop-color="var(--down)" stop-opacity="0"/></linearGradient>
      </defs></svg>`
    );
  }

  /* ---------- 시작 ---------- */
  async function boot() {
    injectDefs();
    initClock();
    initNav();
    initTheme();
    initTabs();
    renderBento();
    initSpotlight();
    renderTicker();
    renderQuotes();
    renderHeat();
    initSegment();
    initStream();
    renderRail();
    renderRadar();
    initDrawer();
    initCmdk();
    initBrief();
    $$('.reveal').forEach((el) => revealObserver.observe(el));
    countUp();
    initGauge();
    flow = initFlow();

    setFeedStatus(false);
    // 실시간 크립토 시세 시도. 실패하면 샘플 그대로
    market.live = await loadLiveTickers();
    if (market.live) {
      await loadLiveSeries();
      setFeedStatus(true);
      renderTicker();
      renderQuotes();
      renderHeat();
    }
    startMarketLoop();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
