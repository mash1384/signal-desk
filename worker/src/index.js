// SIGNAL 스케줄러.
// scheduled: 15분마다 pipeline 워크플로를 workflow_dispatch로 한 번 부른다. 토큰은 GITHUB_TOKEN 비밀 값(이 저장소의 Actions 쓰기 권한만).
// GET /upbit-notices: 업비트 거래 공지 목록을 받아 그대로 돌려준다. 이 주소 하나만 대신 받는다(열린 프록시가 아니다).
// GET /: 상태 확인용 한 줄.
const UPBIT_NOTICES = 'https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=trade';

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

async function upbitNotices(ctx) {
  const cache = caches.default;
  const key = new Request('https://signal-cache/upbit-notices');
  const hit = await cache.match(key);
  if (hit) return hit;
  const up = await fetch(UPBIT_NOTICES, {
    headers: { Accept: 'application/json', 'User-Agent': 'Mozilla/5.0 (compatible; SIGNAL-bot/1.0; +https://mash1384.github.io/signal-desk/about/)' },
  });
  const body = await up.text();
  const res = new Response(body, {
    status: up.status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'max-age=120', 'X-Upstream-Status': String(up.status) },
  });
  if (up.ok) ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatch(env));
  },
  async fetch(req, env, ctx) {
    const { pathname } = new URL(req.url);
    if (req.method !== 'GET') return new Response('method not allowed', { status: 405 });
    if (pathname === '/upbit-notices') return upbitNotices(ctx);
    if (pathname === '/') return new Response('SIGNAL scheduler: dispatches pipeline every 15 minutes\n');
    return new Response('not found', { status: 404 });
  },
};
