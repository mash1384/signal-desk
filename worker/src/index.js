// SIGNAL 스케줄러.
// scheduled: 15분마다 pipeline 워크플로를 workflow_dispatch로 한 번 부른다. 토큰은 GITHUB_TOKEN 비밀 값.
// 업비트 공지 API는 GitHub 서버 IP를 막아서, 정해진 업비트 주소만 대신 받아 준다(열린 프록시가 아니다).
//   GET /upbit-notices          거래 공지 목록 첫 페이지 (2분 캐시)
//   GET /upbit-notice/<숫자 id>  공지 본문 (하루 캐시)
//   GET /upbit-candles?market=KRW-XXX[&to=ISO][&count=1~200]  원화 마켓 1분봉 (30초 캐시, 브라우저의 실시간 곡선용)
//   GET /quotes?s=NVDA,^TNX,…   테마 화면 시세(야후 spark 한 번에, 60초 캐시). 정해 둔 목록(QUOTES) 안의 종목만 — 아무 주소나 대신 받아 주는 통로가 되지 않게
//   GET /index-candles?s=nq|es&i=1m|5m  나스닥100·S&P500 선물 분봉(야후 차트, 60초 캐시). 정해진 두 종목만, 시각·종가만 돌려준다(브라우저의 '소식 이후' 그래프용)
//   GET /flash                  실시간 속보 묶음(운영자 Mac이 flash 브랜치에 올린 flash.json, 20초 캐시). raw.githubusercontent는 5분 캐시라 API로 받는다
// GET /: 상태 확인용 한 줄.
const UPBIT_NOTICES = 'https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=trade';
const UA = 'Mozilla/5.0 (compatible; SIGNAL-bot/1.0; +https://mash1384.github.io/signal-desk/about/)';
const CORS = { 'Access-Control-Allow-Origin': '*' };

async function dispatch(env) {
  const res = await fetch(`https://api.github.com/repos/${env.REPO}/actions/workflows/${env.WORKFLOW}/dispatches`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'signal-scheduler',
    },
    body: JSON.stringify({ ref: env.REF }),
  });
  if (res.status !== 204) throw new Error(`dispatch failed ${res.status}: ${(await res.text()).slice(0, 200)}`);
}

// 업스트림을 받아 그대로 돌려주고, 성공한 응답만 maxAge초 캐시한다
async function relay(ctx, cacheKey, upstream, maxAge) {
  const cache = caches.default;
  const key = new Request('https://signal-cache/' + cacheKey);
  const hit = await cache.match(key);
  if (hit) return hit;
  const up = await fetch(upstream, { headers: { Accept: 'application/json', 'User-Agent': UA } });
  const body = await up.text();
  const res = new Response(body, {
    status: up.status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': `max-age=${maxAge}`, 'X-Upstream-Status': String(up.status), ...CORS },
  });
  if (up.ok) ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}

async function flashFeed(env, ctx) {
  const cache = caches.default;
  const key = new Request('https://signal-cache/flash');
  const hit = await cache.match(key);
  if (hit) return hit;
  const up = await fetch(`https://api.github.com/repos/${env.REPO}/contents/flash.json?ref=flash`, {
    headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: 'application/vnd.github.raw+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'signal-scheduler' },
  });
  const res = new Response(up.ok ? up.body : JSON.stringify({ items: [], error: up.status }), {
    status: up.ok ? 200 : 502,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'max-age=20', ...CORS },
  });
  if (up.ok) ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}

const bad = (msg) => new Response(msg, { status: 400, headers: CORS });

// 지수 선물(거의 24시간 거래) — 뉴스 직후 반응을 보려면 정규장만 열리는 현물 지수보다 낫다
const INDEX = { nq: 'NQ=F', es: 'ES=F' };
async function indexCandles(ctx, s, i) {
  const cache = caches.default;
  const key = new Request(`https://signal-cache/index-${s}-${i}`);
  const hit = await cache.match(key);
  if (hit) return hit;
  const range = i === '1m' ? '2d' : '5d';
  const up = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(INDEX[s])}?interval=${i}&range=${range}`, { headers: { 'User-Agent': 'Mozilla/5.0', Accept: 'application/json' } });
  let out = { s, i, c: [] }, ok = up.ok;
  if (ok) {
    try {
      const r = (await up.json()).chart.result[0], ts = r.timestamp || [], cl = r.indicators.quote[0].close || [];
      out = { s, i, name: r.meta.shortName, price: r.meta.regularMarketPrice, prev: r.meta.chartPreviousClose, c: ts.map((t, k) => [t, cl[k]]).filter((x) => x[1] != null) };
    } catch (e) { ok = false; }
  }
  const res = new Response(JSON.stringify(out), { status: ok ? 200 : 502, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'max-age=60', ...CORS } });
  if (ok) ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}


// 테마 화면 시세: 지수 선물·대형주·금리·달러·원자재. 목록에 없는 기호는 받지 않는다
const QUOTES = new Set(['NQ=F', 'ES=F', 'YM=F', '^VIX', 'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'AVGO', 'AMD', 'TSM', 'PLTR', 'ORCL', 'NFLX', 'COIN', 'MSTR', 'HOOD', 'INTC', 'MU', 'ARM', 'SMCI', 'CRM', 'ADBE', 'QCOM', 'ASML',
  '^TNX', '^FVX', '^TYX', '^IRX', 'DX-Y.NYB', 'GC=F', 'SI=F', 'CL=F', 'NG=F', 'HG=F', 'KRW=X', 'JPY=X', 'EURUSD=X', 'CNY=X']);
async function quotes(ctx, list) {
  const syms = [...new Set(list)].sort(), cache = caches.default, key = new Request(`https://signal-cache/quotes-${encodeURIComponent(syms.join(','))}`);
  const hit = await cache.match(key); if (hit) return hit;
  const up = await fetch(`https://query1.finance.yahoo.com/v8/finance/spark?symbols=${encodeURIComponent(syms.join(','))}&range=5d&interval=1h`, { headers: { 'User-Agent': 'Mozilla/5.0', Accept: 'application/json' } });
  let out = { at: Math.floor(Date.now() / 1000), q: {} }, ok = up.ok;
  if (ok) {
    try {
      const d = await up.json();
      for (const s of syms) { const v = d[s]; if (!v || !(v.timestamp || []).length) continue;
        const ts = v.timestamp, cl = v.close || [];
        out.q[s] = { p: v.fulldayPrice ?? cl[cl.length - 1], chg: v.fulldayChangePercent ?? null, prev: v.previousClose ?? null, c: ts.map((t, k) => [t, cl[k]]).filter((x) => x[1] != null).slice(-48) }; }
    } catch (e) { ok = false; }
  }
  const res = new Response(JSON.stringify(out), { status: ok ? 200 : 502, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'max-age=60', ...CORS } });
  if (ok) ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatch(env));
  },
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const { pathname, searchParams } = url;
    if (req.method !== 'GET') return new Response('method not allowed', { status: 405 });
    if (pathname === '/upbit-notices') return relay(ctx, 'upbit-notices', UPBIT_NOTICES, 120);
    const m = pathname.match(/^\/upbit-notice\/(\d{1,9})$/);
    if (m) return relay(ctx, 'upbit-notice-' + m[1], `https://api-manager.upbit.com/api/v1/announcements/${m[1]}`, 86400);
    if (pathname === '/upbit-candles') {
      const market = searchParams.get('market') || '';
      const to = searchParams.get('to') || '';
      const count = Number(searchParams.get('count') || 200);
      if (!/^KRW-[A-Z0-9]{1,15}$/.test(market)) return bad('market must be KRW-XXX');
      if (to && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(to)) return bad('to must be YYYY-MM-DDTHH:MM:SSZ');
      if (!Number.isInteger(count) || count < 1 || count > 200) return bad('count must be 1-200');
      const q = `market=${market}&count=${count}` + (to ? `&to=${to}` : '');
      return relay(ctx, 'upbit-candles?' + q, `https://api.upbit.com/v1/candles/minutes/1?${q}`, 30);
    }
    if (pathname === '/flash') return flashFeed(env, ctx);
    if (pathname === '/index-candles') {
      const s = searchParams.get('s') || '', i = searchParams.get('i') || '5m';
      if (!INDEX[s]) return bad('s must be nq or es');
      if (i !== '1m' && i !== '5m') return bad('i must be 1m or 5m');
      return indexCandles(ctx, s, i);
    }
    if (pathname === '/quotes') {
      const list = (searchParams.get('s') || '').split(',').map((x) => x.trim()).filter(Boolean);
      if (!list.length || list.length > 30) return bad('s: 1–30 symbols');
      const badOne = list.find((x) => !QUOTES.has(x)); if (badOne) return bad('symbol not allowed: ' + badOne);
      return quotes(ctx, list);
    }
    if (pathname === '/') return new Response('SIGNAL scheduler: dispatches pipeline every 15 minutes\n', { headers: CORS });
    return new Response('not found', { status: 404, headers: CORS });
  },
};
