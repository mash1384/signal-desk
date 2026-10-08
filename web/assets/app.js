/* SIGNAL — 화면 동작
 * 서버가 만든 HTML 위에서 필터·실시간 시세·차트·투표·관심 종목을 붙인다.
 * 모션 원칙: 누름 0.96, UI 전환 300ms 이하, 키보드로 여는 검색창은 애니메이션 없음,
 * prefers-reduced-motion이면 이동·블러 없이 투명도만.
 */
(function () {
  'use strict';

  var S = window.SIGNAL || {};
  var BASE = S.base || '/';
  var $ = function (s, el) { return (el || document).querySelector(s); };
  var $$ = function (s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); };
  var reduced = function () { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; };
  var now = function () { return Math.floor(Date.now() / 1000); };
  var CAT = { crypto: '크립토', ai: 'AI', macro: '매크로' };
  var ICON = {
    up: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 1.5 9 8.5H1z"/></svg>',
    down: '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 8.5 1 1.5h8z"/></svg>'
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function pct(v, d) {
    if (v == null || isNaN(v)) return '–';
    return (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d == null ? 2 : d) + '%';
  }
  function price(p) {
    if (p == null) return '–';
    var d = p >= 10000 ? 0 : p >= 10 ? 2 : p >= 1 ? 3 : 4;
    return p.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function kst(ts) {
    var d = new Date((ts + 9 * 3600) * 1000);
    var p = function (n) { return String(n).padStart(2, '0'); };
    return { md: p(d.getUTCMonth() + 1) + '.' + p(d.getUTCDate()), hm: p(d.getUTCHours()) + ':' + p(d.getUTCMinutes()), day: d.getUTCDate() };
  }
  function mdhm(ts) { var k = kst(ts); return k.md + ' ' + k.hm; }
  function rel(ts) {
    var s = now() - ts;
    if (s < 60) return '방금';
    if (s < 3600) return Math.floor(s / 60) + '분 전';
    if (s < 86400) return Math.floor(s / 3600) + '시간 전';
    return mdhm(ts);
  }
  function store(key, fallback) {
    try { var v = JSON.parse(localStorage.getItem(key)); return v == null ? fallback : v; } catch (e) { return fallback; }
  }
  function save(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }

  async function getJSON(url, ms) {
    var ctl = new AbortController();
    var t = setTimeout(function () { ctl.abort(); }, ms || 8000);
    try {
      var res = await fetch(url, { signal: ctl.signal, cache: 'no-store' });
      if (!res.ok) throw new Error(res.status);
      return await res.json();
    } finally { clearTimeout(t); }
  }
  function dataUrl(name) { return BASE + 'data/' + name + '?t=' + Math.floor(Date.now() / 60000); }

  /* ---------- 토스트 ---------- */
  function toast(msg) {
    var ol = $('#toasts');
    if (!ol) return;
    var li = document.createElement('li');
    li.className = 'toast';
    li.textContent = msg;
    ol.appendChild(li);
    while (ol.children.length > 3) ol.firstElementChild.remove();
    setTimeout(function () { li.classList.add('is-leaving'); setTimeout(function () { li.remove(); }, 200); }, 2800);
  }

  /* ---------- 테마 ---------- */
  function initTheme() {
    var btn = $('#themeToggle');
    if (!btn) return;
    var sync = function () {
      var dark = document.documentElement.dataset.theme !== 'light';
      btn.setAttribute('aria-label', dark ? '라이트 모드로 전환' : '다크 모드로 전환');
    };
    sync();
    btn.addEventListener('click', function () {
      var root = document.documentElement;
      var next = root.dataset.theme === 'light' ? 'dark' : 'light';
      root.classList.add('no-transitions');
      root.dataset.theme = next;
      void root.offsetWidth;
      requestAnimationFrame(function () { root.classList.remove('no-transitions'); });
      try { localStorage.setItem('signal-theme', next); } catch (e) {}
      sync();
      if (flow) flow.refresh();
    });
  }

  /* ---------- 시간 표시 ---------- */
  function updateTimes() {
    $$('.fcard__meta time[data-ts]').forEach(function (el) {
      var ts = +el.dataset.ts;
      el.textContent = now() - ts < 86400 ? rel(ts) : mdhm(ts);
      el.title = mdhm(ts) + ' KST';
    });
    $$('.ib--wait[data-t0]').forEach(function (el) {
      var due = +el.dataset.t0 + 900 + 120;
      var left = due - now();
      el.textContent = left > 60 ? '반응 측정 중 · ' + Math.ceil(left / 60) + '분 후 첫 값' : '반응 측정 중 · 곧 반영';
    });
    $$('td[data-wait]').forEach(function (el) {
      var left = +el.dataset.wait + 120 - now();
      el.textContent = left > 3600 ? Math.ceil(left / 3600) + '시간 후' : left > 60 ? Math.ceil(left / 60) + '분 후' : '곧 반영';
    });
  }

  /* ---------- 관심 종목 ---------- */
  var watch = store('signal-watch', []);
  function setWatch(list) {
    watch = list.slice(0, 20);
    save('signal-watch', watch);
    syncWatch();
  }
  function syncWatch() {
    $$('.achip[data-asset]').forEach(function (b) {
      var on = watch.indexOf(b.dataset.asset) >= 0;
      b.setAttribute('aria-pressed', String(on));
      b.setAttribute('aria-label', b.dataset.asset + (on ? ' 관심 종목 해제' : ' 관심 종목 추가'));
    });
    $$('.fcard').forEach(function (c) {
      var as = (c.dataset.assets || '').split(',');
      c.classList.toggle('is-watch', as.some(function (a) { return a && watch.indexOf(a) >= 0; }));
    });
  }
  function initWatchChips() {
    document.addEventListener('click', function (e) {
      var b = e.target.closest('.achip[data-asset]');
      if (!b || b.closest('#watchCustom')) return;
      var sym = b.dataset.asset;
      if (watch.indexOf(sym) >= 0) {
        setWatch(watch.filter(function (s) { return s !== sym; }));
        toast(sym + '을(를) 관심 종목에서 뺐어요');
      } else {
        if (watch.length >= 20) { toast('관심 종목은 20개까지예요'); return; }
        setWatch(watch.concat([sym]));
        toast(sym + '을(를) 관심 종목에 넣었어요');
      }
      if (S.page === 'feed' && feed) feed.render(false);
    });
    syncWatch();
  }

  /* ---------- 공유 ---------- */
  function initShare() {
    document.addEventListener('click', async function (e) {
      var b = e.target.closest('[data-share]');
      if (!b) return;
      var url = location.href.split('#')[0];
      var title = document.title;
      if (navigator.share) {
        try { await navigator.share({ title: title, url: url }); } catch (err) {}
        return;
      }
      try { await navigator.clipboard.writeText(url); toast('링크를 복사했어요'); }
      catch (err) { toast('복사하지 못했어요. 주소창의 링크를 써 주세요'); }
    });
  }

  /* ---------- 시세 (스냅샷 → 실시간) ---------- */
  var market = S.market || null;
  var LIVE_HOSTS = ['https://data-api.binance.vision', 'https://api.binance.com'];
  var SYMS = ['BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'DOGE', 'ADA', 'LINK', 'AVAX', 'SUI', 'TON', 'DOT'];
  var liveHost = null;

  function tickerHTML(tick, kimp) {
    var items = SYMS.filter(function (s) { return tick[s]; }).map(function (s) {
      var t = tick[s], d = t.chg >= 0 ? 'up' : 'down';
      return '<span class="ticker__item" data-sym="' + s + '"><b>' + s + '</b><span class="px">' + price(t.price) + '</span><span class="chg ' + d + '">' + ICON[d] + ' ' + pct(t.chg) + '</span></span>';
    });
    if (kimp && kimp.BTC) items.push('<span class="ticker__item"><b>김프</b><span class="px">BTC ' + pct(kimp.BTC.premium) + '</span></span>');
    var html = items.join('');
    return html + html.replace(/class="ticker__item"/g, 'class="ticker__item" aria-hidden="true"');
  }
  async function liveTickers() {
    var q = '/api/v3/ticker/24hr?symbols=' + encodeURIComponent(JSON.stringify(SYMS.map(function (s) { return s + 'USDT'; })));
    var hosts = liveHost ? [liveHost] : LIVE_HOSTS;
    for (var i = 0; i < hosts.length; i++) {
      try {
        var rows = await getJSON(hosts[i] + q, 5000);
        liveHost = hosts[i];
        var out = {};
        rows.forEach(function (r) { out[r.symbol.replace(/USDT$/, '')] = { price: +r.lastPrice, chg: +r.priceChangePercent }; });
        return out;
      } catch (e) {}
    }
    return null;
  }
  function applyLive(tick) {
    SYMS.forEach(function (s) {
      var t = tick[s];
      if (!t) return;
      $$('[data-sym="' + s + '"]').forEach(function (el) {
        var px = $('.px', el);
        if (px) {
          var prev = parseFloat((px.textContent || '').replace(/[^0-9.]/g, ''));
          px.textContent = (el.tagName === 'TR' ? '$' : '') + price(t.price);
          if (!reduced() && prev && el.tagName === 'TR' && prev !== t.price) {
            px.classList.remove('flash-up', 'flash-down');
            void px.offsetWidth;
            px.classList.add(t.price > prev ? 'flash-up' : 'flash-down');
          }
        }
        var chg = $('.chg', el);
        if (chg) {
          var d = t.chg >= 0 ? 'up' : 'down';
          chg.className = el.tagName === 'TR' ? 'num chg ' + d : 'chg ' + d;
          chg.innerHTML = el.tagName === 'TR' ? pct(t.chg) : ICON[d] + ' ' + pct(t.chg);
        }
      });
    });
  }
  async function initTicker() {
    var track = $('#tickerTrack');
    var status = $('#feedStatus');
    if (!market) {
      try { market = await getJSON(dataUrl('market.json')); } catch (e) { market = null; }
    }
    if (market && track) track.innerHTML = tickerHTML(market.tickers || {}, market.kimp);
    var tick = async function () {
      if (document.hidden) return;
      var live = await liveTickers();
      if (live) {
        if (status && status.dataset.state !== 'live') {
          status.dataset.state = 'live';
          $('.ticker__label', status).textContent = 'LIVE';
          status.title = '크립토 시세: Binance 공개 API 실시간';
          if (track && !track.children.length) track.innerHTML = tickerHTML(live, market && market.kimp);
        }
        applyLive(live);
      } else if (status) {
        status.dataset.state = 'snapshot';
        $('.ticker__label', status).textContent = '시세';
        status.title = market ? '실시간 연결 실패 · ' + mdhm(market.at) + ' 수집값' : '시세를 불러오지 못했습니다';
      }
    };
    tick();
    setInterval(tick, 15000);
  }

  /* ---------- 스파크라인 ---------- */
  function drawSparks() {
    $$('svg.spark[data-points]').forEach(function (svg) {
      var pts = svg.dataset.points.split(',').map(Number).filter(function (n) { return !isNaN(n); });
      if (pts.length < 2) return;
      var vb = svg.viewBox.baseVal, w = vb.width, h = vb.height;
      var min = Math.min.apply(null, pts), max = Math.max.apply(null, pts), span = max - min || 1;
      var line = pts.map(function (v, i) { return (i / (pts.length - 1) * w).toFixed(1) + ',' + (h - 2 - (v - min) / span * (h - 4)).toFixed(1); }).join(' ');
      svg.classList.add(pts[pts.length - 1] > pts[0] ? 'up' : pts[pts.length - 1] < pts[0] ? 'down' : 'flat');
      svg.innerHTML = '<polyline points="' + line + '"/>';
    });
  }

  /* ---------- 피드 ---------- */
  var feed = null;
  function badgeHTML(it) {
    var hd = it.h;
    if (hd) {
      var d = hd.r >= 0 ? 'up' : 'down';
      var g = { '강': 's', '중': 'm' }[hd.g] || 'w';
      return '<span class="ib ib--' + d + ' ib--g' + g + '" title="기사 시각부터 ' + (hd.win === '1h' ? '1시간' : '15분') + ' 동안 ' + hd.asset + ' 가격 변화">' + ICON[d] +
        '<b>' + esc(hd.asset) + ' ' + hd.win + '</b> ' + pct(hd.r) + (hd.g ? ' · ' + hd.g : '') + '</span>';
    }
    if (it.st === 'failed') return '<span class="ib ib--na">반응 측정 불가</span>';
    return '<span class="ib ib--wait" data-t0="' + it.t0 + '">반응 측정 중</span>';
  }
  function cardHTML(it, i, isNew) {
    var lang = it.lang === 'en' && !it.llm ? '<span class="lang">EN</span>' : '';
    var body = it.sum && it.sum.length ? '<ul class="fcard__sum">' + it.sum.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul>'
      : it.ex ? '<p class="fcard__ex">' + esc(it.ex) + ' <span class="ex-label">원문 발췌</span></p>' : '';
    var chips = (it.assets || []).slice(0, 4).map(function (s) {
      return '<button class="achip" type="button" data-asset="' + esc(s) + '" aria-pressed="false">' + esc(s) + '</button>';
    }).join('');
    return '<article class="fcard' + (isNew ? ' enter' : '') + '" style="--i:' + i + '" data-id="' + esc(it.id) + '" data-cat="' + it.cat + '" data-assets="' + esc((it.assets || []).join(',')) +
      '" data-imp="' + it.imp + '" data-t0="' + it.t0 + '"><div class="fcard__meta"><span class="chip cat cat--' + it.cat + '">' + CAT[it.cat] + '</span>' +
      '<span class="imp" data-lv="' + it.imp + '" role="img" aria-label="중요도 ' + it.imp + '/3"><i></i><i></i><i></i></span><span class="src">' + esc(it.src) + '</span>' +
      '<time datetime="' + new Date(it.t0 * 1000).toISOString() + '" data-ts="' + it.t0 + '">' + mdhm(it.t0) + '</time>' + lang + '</div>' +
      '<h3 class="fcard__title"><a href="' + BASE + 'a/' + esc(it.id) + '/">' + esc(it.title) + '</a></h3>' + body +
      '<div class="fcard__foot">' + badgeHTML(it) + '<span class="achips">' + chips + '</span></div></article>';
  }

  function initFeed() {
    var list = $('#feedList');
    if (!list) return;
    var PAGE = 40;
    var f = Object.assign({ cat: 'all', major: false, strong: false, watch: false, ko: false }, store('signal-filters', {}));
    var items = null, shown = PAGE, pending = null, known = {};
    var more = $('#loadMore'), pill = $('#newPill');

    function controls() {
      $$('#catFilter [data-cat]').forEach(function (b) { b.setAttribute('aria-checked', String(b.dataset.cat === f.cat)); });
      $('#optMajor').checked = f.major; $('#optStrong').checked = f.strong; $('#optWatch').checked = f.watch; $('#optKo').checked = f.ko;
    }
    function isDefault() { return f.cat === 'all' && !f.major && !f.strong && !f.watch && !f.ko; }
    function filtered() {
      var out = items.filter(function (it) {
        if (f.cat !== 'all' && it.cat !== f.cat) return false;
        if (f.major && it.imp < 2) return false;
        if (f.strong && !(it.h && (it.h.g === '강' || it.h.g === '중'))) return false;
        if (f.ko && !(it.lang === 'ko' || it.llm)) return false;
        var mine = (it.assets || []).some(function (a) { return watch.indexOf(a) >= 0; });
        if (f.watch && !mine) return false;
        return true;
      });
      if (watch.length && !f.watch) {
        // 12시간 안의 관심 종목 기사는 위로 올린다
        var pin = out.filter(function (it) { return now() - it.t0 < 43200 && (it.assets || []).some(function (a) { return watch.indexOf(a) >= 0; }); });
        var ids = {};
        pin.forEach(function (it) { ids[it.id] = 1; });
        out = pin.concat(out.filter(function (it) { return !ids[it.id]; }));
      }
      return out;
    }
    function render(animate, freshIds) {
      if (!items) return;
      var rows = filtered();
      var slice = rows.slice(0, shown);
      list.innerHTML = slice.length ? slice.map(function (it, i) {
        return cardHTML(it, Math.min(i, 10), animate && (!freshIds || freshIds[it.id]));
      }).join('') : '<p class="empty">조건에 맞는 기사가 없어요. <button class="btn btn--ghost" type="button" id="clearFilters">필터 풀기</button></p>';
      more.hidden = rows.length <= shown;
      syncWatch();
      updateTimes();
    }
    feed = { render: render };

    async function load(first) {
      try {
        var data = await getJSON(dataUrl('feed.json'));
        if (first || !items) {
          items = data.items;
          items.forEach(function (it) { known[it.id] = 1; });
          if (!isDefault() || watch.length) render(false);
          more.hidden = filtered().length <= shown;
          return;
        }
        var fresh = data.items.filter(function (it) { return !known[it.id]; });
        if (fresh.length) {
          pending = data.items;
          pill.textContent = '새 시그널 ' + fresh.length + '건 보기';
          pill.hidden = false;
        } else {
          // 새 기사가 없어도 임팩트 측정값은 바뀌므로 조용히 갱신
          items = data.items;
          if (!isDefault() || shown > PAGE) render(false);
        }
      } catch (e) {}
    }

    controls();
    $('#catFilter').addEventListener('click', function (e) {
      var b = e.target.closest('[data-cat]');
      if (!b) return;
      f.cat = b.dataset.cat; shown = PAGE; save('signal-filters', f); controls(); render(true);
    });
    $('#catFilter').addEventListener('keydown', function (e) {
      if (['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight'].indexOf(e.key) < 0) return;
      e.preventDefault();
      var bs = $$('#catFilter [data-cat]');
      var i = bs.findIndex(function (b) { return b.dataset.cat === f.cat; });
      var n = bs[(i + (e.key === 'ArrowDown' || e.key === 'ArrowRight' ? 1 : -1) + bs.length) % bs.length];
      n.focus(); n.click();
    });
    [['optMajor', 'major'], ['optStrong', 'strong'], ['optWatch', 'watch'], ['optKo', 'ko']].forEach(function (p) {
      $('#' + p[0]).addEventListener('change', function (e) {
        f[p[1]] = e.target.checked; shown = PAGE; save('signal-filters', f);
        if (p[1] === 'watch' && f.watch && !watch.length) toast('마이 페이지나 기사 카드의 종목 버튼으로 관심 종목을 먼저 골라 주세요');
        render(true);
      });
    });
    list.addEventListener('click', function (e) {
      if (e.target.id !== 'clearFilters') return;
      f = { cat: 'all', major: false, strong: false, watch: false, ko: false }; save('signal-filters', f); controls(); render(true);
    });
    more.addEventListener('click', function () { shown += PAGE; render(false); });
    pill.addEventListener('click', function () {
      var freshIds = {};
      pending.forEach(function (it) { if (!known[it.id]) freshIds[it.id] = 1; known[it.id] = 1; });
      items = pending; pending = null; pill.hidden = true;
      render(true, freshIds);
      list.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });
    });
    load(true);
    setInterval(function () { if (!document.hidden) load(false); }, 60000);
  }

  /* ---------- 기사 차트 ---------- */
  async function candles(sym, start, end) {
    var span = (end - start) / 60;
    var iv = span <= 1000 ? 60 : 300;
    var ivName = iv === 60 ? '1m' : '5m';
    var hosts = LIVE_HOSTS;
    for (var i = 0; i < hosts.length; i++) {
      try {
        var rows = await getJSON(hosts[i] + '/api/v3/klines?symbol=' + sym + 'USDT&interval=' + ivName + '&startTime=' + start * 1000 + '&endTime=' + end * 1000 + '&limit=1000', 8000);
        if (rows.length) return { iv: iv, rows: rows.map(function (r) { return [Math.floor(r[0] / 1000), +r[1], +r[4]]; }) };
      } catch (e) {}
    }
    try {
      var g = 300, out = [], t = start;
      while (t < end && out.length < 600) {
        var t2 = Math.min(end, t + g * 300);
        var cb = await getJSON('https://api.exchange.coinbase.com/products/' + sym + '-USD/candles?granularity=' + g + '&start=' + new Date(t * 1000).toISOString() + '&end=' + new Date(t2 * 1000).toISOString(), 8000);
        cb.forEach(function (r) { out.push([r[0], r[3], r[4]]); });
        t = t2;
      }
      out.sort(function (a, b) { return a[0] - b[0]; });
      if (out.length) return { iv: g, rows: out };
    } catch (e) {}
    return null;
  }
  function initChart() {
    var fig = $('#artChart');
    if (!fig) return;
    var box = $('.chart__box', fig);
    var sym = fig.dataset.sym, t0 = +fig.dataset.t0;
    var start = t0 - 3600, end = Math.min(now(), t0 + 86400);
    box.textContent = '차트 불러오는 중…';
    candles(sym, start, end).then(function (data) {
      if (!data || data.rows.length < 3) { box.textContent = '가격 데이터를 불러오지 못했어요.'; return; }
      var draw = function () {
        var W = box.clientWidth || 600, H = box.clientHeight || 220, padL = 10, padR = 58, padT = 16, padB = 22;
        var rows = data.rows, closes = rows.map(function (r) { return r[2]; });
        var min = Math.min.apply(null, closes), max = Math.max.apply(null, closes), span = max - min || max * 0.001;
        var x = function (ts) { return padL + (ts - start) / (Math.max(end, t0 + 900) - start) * (W - padL - padR); };
        var y = function (v) { return padT + (1 - (v - min) / span) * (H - padT - padB); };
        var line = rows.map(function (r) { return x(r[0] + data.iv).toFixed(1) + ',' + y(r[2]).toFixed(1); }).join(' ');
        var marks = [[900, '15분'], [3600, '1시간'], [86400, '24시간']].filter(function (m) { return t0 + m[0] <= end; }).map(function (m) {
          var xx = x(t0 + m[0]).toFixed(1);
          return '<line class="cmark" x1="' + xx + '" x2="' + xx + '" y1="' + padT + '" y2="' + (H - padB) + '"/><text class="clabel" x="' + xx + '" y="' + (H - 6) + '" text-anchor="middle">' + m[1] + '</text>';
        }).join('');
        var xt = x(t0).toFixed(1);
        box.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" aria-hidden="true">' + marks +
          '<line class="ct0" x1="' + xt + '" x2="' + xt + '" y1="' + (padT - 6) + '" y2="' + (H - padB) + '"/><text class="clabel" x="' + xt + '" y="' + (padT - 4) + '" text-anchor="middle" style="fill:var(--accent-ink)">기사</text>' +
          '<polyline class="cline" points="' + line + '"/>' +
          '<text class="clabel" x="' + (W - padR + 6) + '" y="' + (padT + 8) + '">' + price(max) + '</text><text class="clabel" x="' + (W - padR + 6) + '" y="' + (H - padB) + '">' + price(min) + '</text></svg>';
      };
      draw();
      var rt;
      window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(draw, 120); });
    });
  }

  /* ---------- 투표 ---------- */
  var votes = store('signal-votes', {});
  function syncVotes() {
    $$('.vote[data-event]').forEach(function (v) {
      var mine = votes[v.dataset.event];
      $$('.vbtn', v).forEach(function (b) { b.setAttribute('aria-pressed', String(!!mine && mine.choice === b.dataset.choice)); });
    });
  }
  function initVotes() {
    document.addEventListener('click', function (e) {
      var b = e.target.closest('.vbtn');
      if (!b) return;
      var v = b.closest('.vote');
      var ts = +v.dataset.ts;
      if (now() >= ts) { toast('발표가 시작돼 투표가 마감됐어요'); return; }
      var title = v.dataset.title || (v.closest('.ev') ? $('.ev__title', v.closest('.ev')).textContent.trim() : '');
      votes[v.dataset.event] = { choice: b.dataset.choice, ts: ts, title: title, at: now() };
      save('signal-votes', votes);
      syncVotes();
      toast(b.dataset.choice === 'up' ? '‘위’에 투표했어요. 발표 1시간 뒤 채점돼요' : '‘아래’에 투표했어요. 발표 1시간 뒤 채점돼요');
      if (S.page === 'predict') renderRecord();
    });
    syncVotes();
  }
  async function gradeVotes() {
    var changed = false;
    var ids = Object.keys(votes);
    for (var i = 0; i < ids.length; i++) {
      var v = votes[ids[i]];
      if (v.result || now() < v.ts + 3600 + 120) continue;
      var data = await candles('BTC', v.ts - 60, v.ts + 3600 + 60);
      if (!data || data.iv !== 60) continue;
      var byT = {};
      data.rows.forEach(function (r) { byT[r[0]] = r; });
      var a = byT[Math.floor(v.ts / 60) * 60], b = byT[Math.floor((v.ts + 3600) / 60) * 60 - 60];
      if (!a || !b) continue;
      v.r = (b[2] / a[1] - 1) * 100;
      v.result = v.r >= 0 ? 'up' : 'down';
      changed = true;
    }
    if (changed) save('signal-votes', votes);
  }
  function renderRecord() {
    var box = $('#myRecord');
    if (!box) return;
    var list = Object.keys(votes).map(function (k) { return Object.assign({ id: k }, votes[k]); }).sort(function (a, b) { return b.ts - a.ts; });
    if (!list.length) { box.innerHTML = '<p class="muted">아직 투표하지 않았습니다. 진행 중인 투표에서 골라 보세요.</p>'; return; }
    var done = list.filter(function (v) { return v.result; });
    var hit = done.filter(function (v) { return v.result === v.choice; }).length;
    box.innerHTML = '<div class="record"><p class="record__score">' + (done.length ? Math.round(hit / done.length * 100) + '%' : '–') + '</p><p class="muted small">적중 ' + hit + ' / 채점 ' + done.length + ' · 포인트 ' + hit * 10 + '</p></div>' +
      '<div class="table-wrap"><table class="itable"><thead><tr><th scope="col">일정</th><th scope="col">내 선택</th><th scope="col">결과</th></tr></thead><tbody>' +
      list.map(function (v) {
        var res = v.result ? (v.result === v.choice ? '<span class="up">적중</span>' : '<span class="down">빗나감</span>') + ' <span class="muted small">BTC ' + pct(v.r) + '</span>'
          : now() < v.ts ? '<span class="muted">발표 전</span>' : '<span class="muted">채점 대기</span>';
        return '<tr><td>' + esc(v.title) + '<br><span class="muted small">' + mdhm(v.ts) + '</span></td><td>' + (v.choice === 'up' ? '위' : '아래') + '</td><td>' + res + '</td></tr>';
      }).join('') + '</tbody></table></div>';
  }
  function initPredict() {
    var box = $('#openPolls');
    if (!box) return;
    var evs = (S.calendar || []).filter(function (e) { return e.level === 3 && e.ts > now(); });
    box.innerHTML = evs.length ? evs.map(function (e) {
      return '<div class="poll"><p class="poll__title">' + esc(e.title_ko || e.title) + '</p><p class="muted small">' + mdhm(e.ts) + ' KST · ' + (e.country === 'USD' ? '미국' : '한국') + '</p>' +
        '<div class="vote" data-event="' + esc(e.id) + '" data-ts="' + e.ts + '" data-title="' + esc(e.title_ko || e.title) + '"><span class="muted small">발표 1시간 뒤 BTC는?</span><button class="vbtn" type="button" data-choice="up">위</button><button class="vbtn" type="button" data-choice="down">아래</button></div></div>';
    }).join('') : '<p class="muted">이번 주 남은 중요도 상 일정이 없어요. 다음 주 일정이 올라오면 열립니다.</p>';
    syncVotes();
    renderRecord();
    gradeVotes().then(renderRecord);
  }

  /* ---------- 마이 ---------- */
  function initMe() {
    var custom = $('#watchCustom');
    if (!custom) return;
    var preset = $$('#watchPick [data-asset]').map(function (b) { return b.dataset.asset; });
    var drawCustom = function () {
      custom.innerHTML = watch.filter(function (s) { return preset.indexOf(s) < 0; }).map(function (s) {
        return '<button class="achip achip--lg" type="button" data-remove="' + esc(s) + '" aria-label="' + esc(s) + ' 빼기">' + esc(s) + ' ✕</button>';
      }).join('');
    };
    drawCustom();
    custom.addEventListener('click', function (e) {
      var b = e.target.closest('[data-remove]');
      if (!b) return;
      setWatch(watch.filter(function (s) { return s !== b.dataset.remove; }));
      drawCustom();
    });
    $('#addSym').addEventListener('submit', function (e) {
      e.preventDefault();
      var inp = $('#symInput');
      var v = inp.value.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
      if (!v || v.length < 2) { toast('티커를 2~10자 영문·숫자로 입력해 주세요'); return; }
      if (watch.indexOf(v) >= 0) { toast('이미 있는 종목이에요'); return; }
      if (watch.length >= 20) { toast('관심 종목은 20개까지예요'); return; }
      setWatch(watch.concat([v]));
      inp.value = '';
      drawCustom();
      toast(v + '을(를) 추가했어요');
    });
    $('#resetLocal').addEventListener('click', function () {
      ['signal-watch', 'signal-votes', 'signal-filters'].forEach(function (k) { try { localStorage.removeItem(k); } catch (e) {} });
      watch = []; votes = {};
      syncWatch(); drawCustom();
      toast('이 기기의 설정과 투표 기록을 지웠어요');
    });
  }

  /* ---------- 검색 (애니메이션 없음) ---------- */
  function initSearch() {
    var box = $('#cmdk'), input = $('#cmdkInput'), list = $('#cmdkList');
    if (!box) return;
    var data = null, results = [], idx = 0, back = null;
    var mark = function (text, q) {
      var i = q ? text.toLowerCase().indexOf(q.toLowerCase()) : -1;
      return i < 0 ? esc(text) : esc(text.slice(0, i)) + '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' + esc(text.slice(i + q.length));
    };
    var run = function () {
      var q = input.value.trim(), ql = q.toLowerCase();
      if (!data) { list.innerHTML = '<li class="cmdk__empty">불러오는 중…</li>'; return; }
      results = data.filter(function (it) {
        return !q || it.title.toLowerCase().indexOf(ql) >= 0 || it.src.toLowerCase().indexOf(ql) >= 0 || (it.assets || []).some(function (a) { return a.toLowerCase() === ql; });
      }).slice(0, 14);
      idx = 0;
      list.innerHTML = results.length ? results.map(function (it, i) {
        return '<li class="cmdk__item" role="option" id="ck' + i + '" aria-selected="' + (i === 0) + '"><a href="' + BASE + 'a/' + esc(it.id) + '/"><i class="dot dot--' + it.cat + '"></i><span class="t">' + mark(it.title, q) + '</span><span class="m">' + esc(it.src) + ' · ' + kst(it.t0).hm + '</span></a></li>';
      }).join('') : '<li class="cmdk__empty">‘' + esc(q) + '’에 맞는 기사가 없어요. 다른 단어나 티커로 찾아보세요.</li>';
      input.setAttribute('aria-activedescendant', results.length ? 'ck0' : '');
    };
    var select = function (i) {
      var items = $$('.cmdk__item', list);
      if (!items.length) return;
      idx = (i + items.length) % items.length;
      items.forEach(function (el, n) { el.setAttribute('aria-selected', String(n === idx)); });
      items[idx].scrollIntoView({ block: 'nearest' });
      input.setAttribute('aria-activedescendant', 'ck' + idx);
    };
    var open = function () {
      back = document.activeElement;
      box.hidden = false;
      input.value = '';
      run();
      input.focus();
      if (!data) getJSON(dataUrl('feed.json')).then(function (d) { data = d.items; run(); }).catch(function () { list.innerHTML = '<li class="cmdk__empty">검색 데이터를 불러오지 못했어요.</li>'; });
    };
    var close = function () {
      if (box.hidden) return;
      box.hidden = true;
      if (back && back.focus) back.focus({ preventScroll: true });
    };
    $('#openSearch').addEventListener('click', open);
    input.addEventListener('input', run);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); select(idx + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); select(idx - 1); }
      else if (e.key === 'Enter' && results[idx]) { e.preventDefault(); location.href = BASE + 'a/' + results[idx].id + '/'; }
    });
    box.addEventListener('click', function (e) { if (e.target.matches('[data-close]')) close(); });
    document.addEventListener('keydown', function (e) {
      var typing = /INPUT|TEXTAREA|SELECT/.test((document.activeElement || {}).tagName || '');
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); box.hidden ? open() : close(); }
      else if (e.key === '/' && !typing && box.hidden) { e.preventDefault(); open(); }
      else if (e.key === 'Escape') close();
    });
  }

  /* ---------- 소개 페이지 흐름 캔버스 ---------- */
  var flow = null;
  function initFlow() {
    var canvas = $('#flowCanvas');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var w = 0, h = 0, colors = {}, running = false, visible = true, t = Math.random() * 100, last = 0;
    var target = { x: 0.7, y: 0.5, on: 0 }, pos = { x: 0.7, y: 0.5, on: 0, vx: 0, vy: 0, von: 0 };
    var fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    var read = function () {
      var probe = document.createElement('i');
      document.body.appendChild(probe);
      var cs = getComputedStyle(document.documentElement);
      var res = function (v) { probe.style.color = cs.getPropertyValue(v).trim(); return getComputedStyle(probe).color; };
      colors = { a: res('--accent'), b: res('--ai'), c: res('--macro'), light: document.documentElement.dataset.theme === 'light' };
      probe.remove();
    };
    var resize = function () {
      var dpr = Math.min(window.devicePixelRatio || 1, 2), r = canvas.getBoundingClientRect();
      w = r.width; h = r.height;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (!running) draw();
    };
    var draw = function () {
      ctx.clearRect(0, 0, w, h);
      var lines = w < 640 ? 16 : 26, step = w < 640 ? 10 : 8, cx = pos.x * w, cy = pos.y * h;
      for (var i = 0; i < lines; i++) {
        var k = i / (lines - 1), base = h * (0.35 + k * 0.55), amp = h * (0.05 + 0.07 * Math.sin(k * Math.PI));
        ctx.strokeStyle = k < 0.5 ? colors.a : k < 0.8 ? colors.c : colors.b;
        ctx.globalAlpha = (colors.light ? 0.28 : 0.2) + 0.35 * Math.pow(Math.sin(k * Math.PI), 3);
        ctx.beginPath();
        for (var x = -10; x <= w + 10; x += step) {
          var nx = x / w;
          var y = base + Math.sin(nx * 6.2 + t * 0.6 + k * 2.4) * amp + Math.sin(nx * 13.7 - t * 0.9 + k * 5.1) * amp * 0.28 + Math.cos(nx * 2.3 + t * 0.25 + k) * amp * 0.6;
          var dx = x - cx, dy = base - cy;
          y -= Math.exp(-((dx * dx) / (w * w * 0.02) + (dy * dy) / (h * h * 0.06))) * h * 0.09 * pos.on * (k - 0.3);
          if (x === -10) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    };
    var loop = function (ts) {
      if (!running) return;
      var dt = Math.min(0.033, last ? (ts - last) / 1000 : 0.016);
      last = ts; t += dt;
      [['x', 'vx'], ['y', 'vy'], ['on', 'von']].forEach(function (p) {
        var a = -60 * (pos[p[0]] - target[p[0]]) - 12 * pos[p[1]];
        pos[p[1]] += a * dt; pos[p[0]] += pos[p[1]] * dt;
      });
      draw();
      requestAnimationFrame(loop);
    };
    var start = function () { if (running || reduced() || !visible || document.hidden) return; running = true; last = 0; requestAnimationFrame(loop); };
    var stop = function () { running = false; };
    read(); resize();
    window.addEventListener('resize', resize);
    if (fine) {
      var hero = canvas.parentElement;
      hero.addEventListener('pointermove', function (e) { var r = canvas.getBoundingClientRect(); target.x = (e.clientX - r.left) / r.width; target.y = (e.clientY - r.top) / r.height; target.on = 1; });
      hero.addEventListener('pointerleave', function () { target.on = 0; });
    }
    new IntersectionObserver(function (en) { visible = en[0].isIntersecting; if (visible) start(); else stop(); }).observe(canvas);
    document.addEventListener('visibilitychange', function () { if (document.hidden) stop(); else start(); });
    start();
    flow = { refresh: function () { read(); if (!running) draw(); } };
  }

  /* ---------- 랜딩 ---------- */

  // 기사 시각 전후 가격선. 좌표는 0~W, 0~H 비율로 돌려준다
  function priceLine(rows, iv, from, to, W, H, pad) {
    var cl = rows.map(function (r) { return r[2]; });
    var min = Math.min.apply(null, cl), max = Math.max.apply(null, cl), span = max - min || max * 0.001;
    var x = function (ts) { return (ts - from) / (to - from) * W; };
    var y = function (v) { return H - pad - (v - min) / span * (H - pad * 2); };
    var pts = rows.map(function (r) { return [x(r[0] + iv), y(r[2])]; });
    return { pts: pts, x: x, y: y, at: function (ts) {
      var best = null;
      rows.forEach(function (r) { if (r[0] + iv <= ts) best = r; });
      return best ? [x(best[0] + iv), y(best[2])] : null;
    } };
  }

  // 차트를 왼쪽부터 드러낸다(한 번). 움직임 줄이기에서는 바로 보인다
  function revealChart(svg, ms) {
    if (!svg || reduced() || !svg.animate) return;
    svg.animate([{ clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0 0 0)' }], { duration: ms, easing: 'cubic-bezier(0.77, 0, 0.175, 1)' });
  }

  // 스크롤해서 화면에 들어온 요소를 한 번씩 드러낸다
  function initReveal() {
    var els = $$('[data-reveal]');
    if (!els.length || !('IntersectionObserver' in window)) return;
    document.documentElement.classList.add('reveal-on');
    var io = new IntersectionObserver(function (en) {
      en.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add('is-in');
        io.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.12 });
    els.forEach(function (el) { io.observe(el); });
  }

  // 첫 화면 숫자는 0에서 실제 값까지 한 번 올라간다
  function countUp() {
    if (reduced()) return;
    $$('.count[data-to]').forEach(function (el, i) {
      var to = +el.dataset.to, t0 = performance.now() + 600 + i * 100;
      el.textContent = '0';
      var step = function (t) {
        var k = Math.min(1, Math.max(0, (t - t0) / 1100));
        el.textContent = Math.round(to * (1 - Math.pow(1 - k, 4))).toLocaleString('ko-KR');
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }

  // 스크롤 고정 섹션: 진행도(0~1)에 따라 세 장면을 바꾸고, 장면 안의 그래픽도 진행도만큼 그린다
  function initStory() {
    var sec = $('#story');
    if (!sec || reduced()) return;
    var pin = $('.story__pin', sec), steps = $$('.story__steps li', sec), bar = $('.story__bar i', sec), sc = $$('.sc', sec);
    var chips = $$('.sc1__src li', sec), cards = $$('.sc1__feed li', sec), cnt = $('.sc1__count b', sec), total = +cnt.dataset.to || 0;
    var chart = $('.sc2__chart', sec), svg = $('svg', chart), t0tag = $('.sc2__t0', chart), marks = $$('.mk', chart);
    var run = $('.sc3__run', sec), zEl = $('.sc3__z b', sec), zMax = Math.abs(+zEl.dataset.z || 0), pos = +run.dataset.pos || 0, badge = $('.sc3__badge', sec);
    var info = (S.landing || {}).story;
    var clamp = function (v) { return Math.max(0, Math.min(1, v)); };
    var seg = function (p, a, b) { return clamp((p - a) / (b - a)); };
    var ease = function (t) { return 1 - Math.pow(1 - t, 3); };
    var markAt = [];
    if (info) {
      var from = info.ts - 1800, to = Math.min(now(), info.ts + 7200);
      candles(info.asset, from, to).then(function (d) {
        if (!d || d.rows.length < 3) return;
        var W = 600, H = 240, L = priceLine(d.rows, d.iv, from, to, W, H, 28);
        var line = L.pts.map(function (q, i) { return (i ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1); }).join(' ');
        var first = L.pts[0], last = L.pts[L.pts.length - 1], tx = L.x(info.ts);
        svg.innerHTML = '<path class="c-area" d="' + line + ' L' + last[0].toFixed(1) + ' ' + H + ' L' + first[0].toFixed(1) + ' ' + H + ' Z"/>' +
          '<line class="c-t0" x1="' + tx.toFixed(1) + '" x2="' + tx.toFixed(1) + '" y1="0" y2="' + H + '"/><path class="c-line" d="' + line + '"/>';
        var at = d.rows.filter(function (r) { return r[0] >= info.ts; });
        chart.classList.add(at.length && at[at.length - 1][2] >= at[0][1] ? 'is-up' : 'is-down');
        t0tag.style.left = (tx / W * 100).toFixed(2) + '%';
        markAt = marks.map(function (m) {
          var q = L.at(info.ts + (m.dataset.win === '1h' ? 3600 : 900));
          if (!q) { m.style.display = 'none'; return 2; }
          m.style.left = (q[0] / W * 100).toFixed(2) + '%';
          m.style.top = (q[1] / H * 100).toFixed(2) + '%';
          return q[0] / W;
        });
        update();
      });
    }
    var show = function (el, v) {
      el.style.opacity = v.toFixed(3);
      el.style.visibility = v < 0.01 ? 'hidden' : 'visible';
      el.style.transform = v < 1 ? 'translateY(' + ((1 - v) * 14).toFixed(1) + 'px)' : 'none';
      el.style.filter = v < 1 ? 'blur(' + ((1 - v) * 4).toFixed(2) + 'px)' : 'none';
    };
    var update = function () {
      var r = sec.getBoundingClientRect(), range = sec.offsetHeight - pin.offsetHeight;
      var p = clamp(-r.top / (range || 1));
      show(sc[0], 1 - seg(p, 0.3, 0.36));
      show(sc[1], Math.min(seg(p, 0.3, 0.36), 1 - seg(p, 0.63, 0.69)));
      show(sc[2], seg(p, 0.63, 0.69));
      var l1 = seg(p, 0.02, 0.28), l2 = seg(p, 0.37, 0.6), l3 = seg(p, 0.7, 0.92);
      chips.forEach(function (c, i) { var t = clamp(l1 * 2.4 - i * 0.12); c.style.opacity = t.toFixed(2); c.style.transform = 'translateY(' + ((1 - t) * 8).toFixed(1) + 'px)'; });
      cards.forEach(function (c, i) { var t = ease(clamp(l1 * 2 - 0.35 - i * 0.16)); c.style.opacity = t.toFixed(2); c.style.transform = 'translateY(' + ((1 - t) * -18).toFixed(1) + 'px)'; });
      cnt.textContent = Math.round(total * ease(l1)).toLocaleString('ko-KR');
      svg.style.clipPath = 'inset(0 ' + ((1 - l2) * 100).toFixed(2) + '% 0 0)';
      marks.forEach(function (m, i) { m.classList.toggle('is-on', markAt[i] != null && l2 >= markAt[i]); });
      run.style.transform = 'translateX(' + (ease(l3) * pos * 100).toFixed(2) + '%)';
      zEl.textContent = (zMax * ease(l3)).toFixed(1);
      badge.classList.toggle('is-on', l3 > 0.9);
      var on = p < 0.33 ? 0 : p < 0.66 ? 1 : 2;
      steps.forEach(function (li, i) { li.classList.toggle('is-on', i === on); });
      bar.style.transform = 'scaleX(' + p.toFixed(3) + ')';
    };
    var ticking = false;
    var onScroll = function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { ticking = false; update(); });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    update();
  }

  // 고정 섹션 공통: 섹션 안에서 진행도(0~1)를 계산해 넘긴다
  function pinScroll(sec, onP) {
    var pin = $('.pin', sec), ticking = false;
    var upd = function () {
      var r = sec.getBoundingClientRect(), range = sec.offsetHeight - pin.offsetHeight;
      onP(Math.max(0, Math.min(1, -r.top / (range || 1))));
    };
    var on = function () { if (ticking) return; ticking = true; requestAnimationFrame(function () { ticking = false; upd(); }); };
    window.addEventListener('scroll', on, { passive: true });
    window.addEventListener('resize', on);
    upd();
    return upd;
  }

  // 실측 사례: 세로 스크롤만큼 카드 줄을 가로로 민다. 섹션 높이 = 고정 영역 + 가로로 갈 거리
  function initHScroll() {
    var sec = $('#proofPin');
    if (!sec || reduced()) return;
    var vp = $('.hscroll__viewport', sec), track = $('.hscroll__track', sec), cards = $$('.proof', track);
    var bar = $('.hscroll__bar i', sec), count = $('.hscroll__count b', sec);
    if (cards.length < 2) return;
    sec.classList.add('is-pinned');
    var dist = 0;
    var size = function () {
      dist = Math.max(0, track.scrollWidth - vp.clientWidth);
      sec.style.height = ($('.pin', sec).offsetHeight + dist) + 'px';
    };
    size();
    var upd = pinScroll(sec, function (p) {
      track.style.transform = 'translateX(' + (-p * dist).toFixed(1) + 'px)';
      bar.style.transform = 'scaleX(' + p.toFixed(3) + ')';
      var k = Math.min(cards.length - 1, Math.round(p * (cards.length - 1)));
      count.textContent = (k < 9 ? '0' : '') + (k + 1);
    });
    window.addEventListener('resize', function () { size(); upd(); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { size(); upd(); });
  }

  // 유형별 순위: 막대가 하나씩 차오르고 왼쪽 숫자가 지금 차오르는 유형을 보여 준다
  function initRank() {
    var sec = $('#rankPin');
    if (!sec || reduced()) return;
    var rows = $$('.tbar[data-val]', sec);
    if (rows.length < 2) return;
    sec.classList.add('is-pinned');
    sec.style.height = 'calc(' + (100 + rows.length * 28) + 'svh)';
    var lab = $('.rank__label', sec), val = $('.rank__val', sec), nEl = $('.rank__n', sec), n = rows.length;
    var bars = rows.map(function (r) { return $('.tbar__track i', r); });
    var vs = bars.map(function (b) { return +getComputedStyle(b).getPropertyValue('--v') || 0; });
    pinScroll(sec, function (p) {
      var x = Math.min(n - 0.001, p * n * 1.08);
      var cur = Math.floor(x);
      rows.forEach(function (r, i) {
        var t = Math.max(0, Math.min(1, x - i));
        var e = 1 - Math.pow(1 - t, 3);
        bars[i].style.transform = 'scaleX(' + (e * vs[i]).toFixed(4) + ')';
        r.classList.toggle('is-on', i === cur);
        r.classList.toggle('is-done', i < cur);
      });
      var row = rows[cur], t2 = Math.max(0, Math.min(1, x - cur));
      lab.textContent = row.dataset.label;
      val.textContent = (+row.dataset.val * (1 - Math.pow(1 - t2, 3))).toFixed(2) + '%';
      nEl.textContent = '표본 ' + row.dataset.n + '건';
    });
  }

  // 문장: 진행도만큼 단어를 차례로 켠다
  function initSay() {
    var sec = $('#sayPin');
    if (!sec || reduced()) return;
    var words = $$('.sw', sec);
    sec.classList.add('is-pinned');
    sec.style.height = '220svh';
    pinScroll(sec, function (p) {
      var k = p * 1.15 * words.length;
      words.forEach(function (w, i) { w.classList.toggle('is-on', i < k); });
    });
  }

  // 첫 화면 미리보기: 기사를 고르면 그 기사의 가격 반응을 보여 준다.
  // 움직임을 허용하면 화면을 고정하고 스크롤로 넘긴다. 기사마다 가격선이 왼쪽부터 그려지고, 선이 15분·1시간 지점을 지날 때 그 반응이 켜진다.
  // 움직임 줄이기에서는 고정하지 않고 기사를 눌러 고른다
  function initDemo() {
    var root = $('#demo');
    var data = (S.landing || {}).demo || [];
    if (!root || !data.length) return;
    var sec = $('#demoPin');
    var items = $$('.demo__item', root), pane = $('#demoDetail'), cache = {};
    var scrub = !!sec && !reduced();
    var rev = 1, marks = [0, 1, 1, 1];
    var CL = { crypto: '크립토', ai: 'AI', macro: '매크로' };
    var WIN = [['15m', '15분'], ['1h', '1시간'], ['24h', '24시간']];
    var detailHTML = function (it) {
      var cells = WIN.map(function (w) {
        var v = it.rx[w[0]];
        if (v && v.r != null) {
          var z = v.z != null ? 'z ' + Number(v.z).toFixed(1).replace('-', '−') : '';
          return '<div><dt>' + w[1] + '</dt><dd class="' + (v.r >= 0 ? 'up' : 'down') + '">' + pct(v.r) + '</dd><span>' + z + (v.g ? ' · ' + esc(v.g) : '') + '</span></div>';
        }
        return '<div class="is-wait"><dt>' + w[1] + '</dt><dd>' + (v ? '측정 중' : '–') + '</dd><span>' + (v ? '곧 반영' : '기록 없음') + '</span></div>';
      }).join('');
      return '<div class="dd" data-sym="' + esc(it.asset) + '" data-t0="' + it.ts + '"><p class="dd__meta"><span class="chip cat cat--' + esc(it.cat) + '">' + (CL[it.cat] || esc(it.cat)) +
        '</span><span>' + esc(it.src) + ' · ' + mdhm(it.ts) + '</span></p><p class="dd__title">' + esc(it.t) + '</p><div class="dd__chart" aria-hidden="true"></div>' +
        '<dl class="dd__rx" aria-label="' + esc(it.asset) + ' 가격 반응">' + cells + '</dl><a class="dd__link" href="' + BASE + 'a/' + esc(it.id) + '/">기사와 차트 자세히 보기</a></div>';
    };
    var span = function (it) { var from = it.ts - 1800; return [from, Math.min(now(), it.ts + 7200)]; };
    // 가격선을 rev(0~1)만큼 드러내고, 지나간 시점의 반응을 켠다
    var applyReveal = function () {
      if (!scrub) return;
      var box = $('.dd__chart', pane), svg = box && $('svg', box), tag = box && $('.dd__tag', box);
      if (svg) svg.style.clipPath = 'inset(0 ' + ((1 - rev) * 100).toFixed(2) + '% 0 0)';
      if (tag) tag.classList.toggle('is-on', rev >= marks[0]);
      $$('.dd__rx > div', pane).forEach(function (c, k) { c.classList.toggle('is-lit', rev >= marks[k + 1] - 0.001); });
    };
    var draw = function (it) {
      var box = $('.dd__chart', pane);
      if (!box) return;
      var sp = span(it), from = sp[0], to = sp[1];
      var paint = function (d) {
        if (!box.isConnected) return;
        if (!d || d.rows.length < 3) { box.textContent = '차트를 불러오지 못했습니다'; return; }
        var W = 600, H = 168, L = priceLine(d.rows, d.iv, from, to, W, H, 18);
        var line = L.pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join(' ');
        var last = L.pts[L.pts.length - 1], first = L.pts[0];
        var r15 = it.rx['15m'] && it.rx['15m'].r;
        box.className = 'dd__chart ' + ((r15 != null ? r15 : (first[1] - last[1])) >= 0 ? 'is-up' : 'is-down');
        var tx = L.x(it.ts);
        var html = '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none"><path class="c-area" d="' + line + ' L' + last[0].toFixed(1) + ' ' + H + ' L' + first[0].toFixed(1) + ' ' + H + ' Z"/>' +
          '<line class="c-t0" x1="' + tx.toFixed(1) + '" x2="' + tx.toFixed(1) + '" y1="0" y2="' + H + '"/><path class="c-line" d="' + line + '"/></svg>' +
          '<span class="dd__tag" style="left:' + (tx / W * 100).toFixed(2) + '%">기사 시각</span>';
        box.innerHTML = html;
        if (scrub) applyReveal();
        else revealChart($('svg', box), 800);
      };
      if (cache[it.id]) paint(cache[it.id]);
      else candles(it.asset, from, to).then(function (d) { cache[it.id] = d; paint(d); });
    };
    var select = function (i) {
      items.forEach(function (b, j) {
        b.setAttribute('aria-pressed', j === i ? 'true' : 'false');
        b.parentNode.classList.toggle('is-cur', j === i);
      });
      var it = data[i], sp = span(it), len = sp[1] - sp[0];
      // 차트 가로축에서 기사 시각·15분·1시간 지점, 24시간은 선을 다 그린 뒤
      marks = [1800 / len, Math.min(1, 2700 / len), Math.min(1, 5400 / len), 1];
      pane.innerHTML = detailHTML(it);
      var dd = $('.dd', pane);
      if (reduced()) dd.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, easing: 'ease-out' });
      else dd.animate([{ opacity: 0, transform: 'translateY(8px)', filter: 'blur(4px)' }, { opacity: 1, transform: 'none', filter: 'blur(0px)' }], { duration: 300, easing: 'cubic-bezier(0.23, 1, 0.32, 1)' });
      applyReveal();
      draw(it);
    };

    if (scrub) {
      var pin = $('.pin', sec), step = $('.demo__step', root);
      var narrow = matchMedia('(max-width: 900px)');
      var count = function () { return narrow.matches ? Math.min(3, items.length) : items.length; };
      var START = 0.12, END = 0.96;
      sec.classList.add('is-pinned');
      root.classList.add('is-scrub');
      items.forEach(function (b) { var i = document.createElement('i'); i.className = 'demo__prog'; i.setAttribute('aria-hidden', 'true'); b.appendChild(i); });
      // 기사 하나에 화면 높이의 80%만큼 스크롤
      var size = function () { sec.style.height = Math.round(pin.offsetHeight + innerHeight * (0.35 + 0.8 * count())) + 'px'; };
      size();
      window.addEventListener('resize', size);
      var shown = -1;
      var upd = pinScroll(sec, function (p) {
        var n = count();
        var u = 1 - Math.pow(1 - Math.min(1, p / START), 3);
        root.style.transform = u < 1 ? 'perspective(1600px) rotateX(' + (14 * (1 - u)).toFixed(2) + 'deg) scale(' + (0.94 + 0.06 * u).toFixed(4) + ')' : 'none';
        root.style.opacity = (0.55 + 0.45 * u).toFixed(3);
        var q = Math.max(0, Math.min(1, (p - START) / (END - START))) * n;
        var i = Math.min(n - 1, Math.floor(q)), local = Math.min(1, q - i);
        if (i !== shown) { shown = i; select(i); }
        rev = Math.min(1, local / 0.75);
        applyReveal();
        items.forEach(function (b, j) {
          var bar = $('.demo__prog', b);
          bar.style.transform = 'scaleX(' + (j === i ? local : j < i ? 1 : 0).toFixed(3) + ')';
          bar.style.opacity = j < i ? '0.3' : '1';
        });
        step.textContent = '0' + (i + 1) + ' / 0' + n;
      });
      // 기사를 누르면 그 기사 구간으로 스크롤한다
      items.forEach(function (b, i) {
        b.addEventListener('click', function () {
          var top = sec.getBoundingClientRect().top + scrollY, range = sec.offsetHeight - pin.offsetHeight;
          scrollTo({ top: top + range * (START + (END - START) * (i + 0.8) / count()), behavior: 'smooth' });
        });
      });
      upd();
      return;
    }

    var cur = 0;
    items.forEach(function (b, i) {
      b.addEventListener('click', function () { if (i !== cur) { cur = i; select(i); } });
    });
    draw(data[0]);
  }

  function initCountdown() {
    var cnt = $('#calCount');
    if (!cnt || !+cnt.dataset.ts) return;
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var tick = function () {
      var left = +cnt.dataset.ts - now();
      if (left <= 0) { cnt.textContent = '발표 시각입니다'; return; }
      var d = Math.floor(left / 86400), hh = Math.floor(left % 86400 / 3600), mm = Math.floor(left % 3600 / 60), ss = Math.floor(left % 60);
      cnt.textContent = (d ? d + '일 ' : '') + pad(hh) + ':' + pad(mm) + ':' + pad(ss);
    };
    tick();
    setInterval(tick, 1000);
  }

  function initProofs() {
    var boxes = $$('.proof__chart[data-sym]');
    if (!boxes.length) return;
    var io = new IntersectionObserver(function (en) {
      en.forEach(function (e) {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        var box = e.target, sym = box.dataset.sym, t0 = +box.dataset.t0, from = t0 - 1800, to = Math.min(now(), t0 + 3600);
        candles(sym, from, to).then(function (d) {
          if (!d || d.rows.length < 3) { box.textContent = '차트를 불러오지 못했습니다'; return; }
          var L = priceLine(d.rows, d.iv, from, to, 300, 96, 6);
          var at = d.rows.filter(function (r) { return r[0] >= t0; });
          box.classList.add(at.length && at[at.length - 1][2] >= at[0][1] ? 'is-up' : 'is-down');
          var tx = L.x(t0).toFixed(1);
          box.innerHTML = '<svg viewBox="0 0 300 96" preserveAspectRatio="none"><line class="pc-t0" x1="' + tx + '" x2="' + tx + '" y1="0" y2="96"/><polyline class="pc-line" points="' +
            L.pts.map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ') + '"/></svg>';
          revealChart($('svg', box), 1100);
        });
      });
    }, { rootMargin: '0px 0px -10% 0px' });
    boxes.forEach(function (b) { io.observe(b); });
  }

  /* ---------- 시작 ---------- */
  function boot() {
    initTheme();
    initWatchChips();
    initShare();
    initSearch();
    initTicker();
    drawSparks();
    initFeed();
    initChart();
    initVotes();
    initPredict();
    initMe();
    initFlow();
    initReveal();
    countUp();
    initStory();
    initHScroll();
    initRank();
    initSay();
    initDemo();
    initCountdown();
    initProofs();
    updateTimes();
    setInterval(updateTimes, 30000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
