// SIGNAL 스케줄러.
// scheduled: 15분마다 pipeline 워크플로를 workflow_dispatch로 한 번 부른다. 토큰은 GITHUB_TOKEN 비밀 값.
// 업비트 공지 API는 GitHub 서버 IP를 막아서, 정해진 업비트 주소만 대신 받아 준다(열린 프록시가 아니다).
//   GET /upbit-notices          거래 공지 목록 첫 페이지 (2분 캐시)
//   GET /upbit-notice/<숫자 id>  공지 본문 (하루 캐시)
//   GET /upbit-candles?market=KRW-XXX[&to=ISO][&count=1~200]  원화 마켓 1분봉 (30초 캐시, 브라우저의 실시간 곡선용)
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

const bad = (msg) => new Response(msg, { status: 400, headers: CORS });

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
    if (pathname === '/') return new Response('SIGNAL scheduler: dispatches pipeline every 15 minutes\n', { headers: CORS });
    return new Response('not found', { status: 404, headers: CORS });
  },
};
