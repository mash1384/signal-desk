// 실시간 속보: 운영자 Mac이 묶은 속보(flash.json)를 Worker /flash 에서 30초마다 받아 그린다.
const $ = (s, r = document) => r.querySelector(s);
const root = $('#fl');
const POLL = 30000;
const PAGE = 12;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u || '') ? u : '');
const hms = (t) => new Date(t * 1000).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
const ago = (t) => {
  const s = Math.max(0, Date.now() / 1000 - t);
  if (s < 60) return '방금';
  if (s < 3600) return `${Math.floor(s / 60)}분 전`;
  if (s < 86400) return `${Math.floor(s / 3600)}시간 전`;
  return new Date(t * 1000).toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' });
};

let D = null, filter = 'all', shown = PAGE, seen = null;

function item(it) {
  const cls = it.v === '호재' ? 'up' : it.v === '악재' ? 'down' : 'flat';
  const tags = [...it.coins.map((c) => `<span class="fl-tag">${esc(c)}</span>`),
    ...it.sectors.map((s) => `<span class="fl-tag fl-tag--sec">${esc((D.sectors || {})[s] || s)} 섹터</span>`),
    ...(it.mw ? ['<span class="fl-tag fl-tag--mw">시장 전체</span>'] : [])].join('');
  const link = safeUrl(it.link);
  return `<li class="fl-it${it.s >= 2 ? ' is-big' : ''}${seen && !seen.has(it.id) ? ' is-new' : ''}" data-id="${esc(it.id)}">
    <div class="fl-it__row">
      <span class="fl-v fl-v--${cls}">${it.v}</span>
      <span class="fl-it__main">
        <span class="fl-it__ko">${esc(it.ko)}</span>
        <span class="fl-it__meta"><time datetime="${new Date(it.t * 1000).toISOString()}" data-t="${it.t}">${ago(it.t)}</time>${it.n > 1 ? `<span>${it.n}곳 보도</span>` : ''}${tags}${link ? `<a class="fl-link" href="${esc(link)}" target="_blank" rel="noopener nofollow">관련 기사 ↗</a>` : ''}</span>
      </span>
    </div>
  </li>`;
}

function pick() {
  const xs = D.items;
  if (filter === 'big') return xs.filter((it) => it.s >= 2);
  if (filter === 'all') return xs;
  return xs.filter((it) => it.v === filter);
}

function render() {
  const xs = pick();
  const list = $('#flList');
  list.innerHTML = xs.length ? xs.slice(0, shown).map(item).join('')
    : `<li class="fl-empty">최근 이틀 동안 ${filter === 'big' ? '큰 소식이' : filter === 'all' ? '속보가' : `${filter} 소식이`} 없었어요.</li>`;
  const more = $('#flMore');
  more.hidden = xs.length <= shown;
  more.textContent = `더 보기 (${xs.length - shown}개 남음)`;
  status();
}

function status() {
  const el = $('#flUpd');
  if (!D) return;
  const idle = Date.now() / 1000 - (D.last_got || D.at);
  el.classList.toggle('is-stale', idle > 900);
  el.textContent = idle > 900 ? `수집이 잠시 멈췄어요 · 마지막 ${ago(D.last_got || D.at)}` : `${ago(D.at)} 갱신`;
  root.querySelectorAll('time[data-t]').forEach((t) => { t.textContent = ago(+t.dataset.t); });
}

async function load() {
  try {
    const r = await fetch(root.dataset.src, { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    if (!d.items) throw new Error('bad');
    seen = D ? new Set(D.items.map((it) => it.id)) : null;
    D = d;
    render();
  } catch (e) {
    if (!D) $('#flUpd').textContent = '속보를 불러오지 못했어요';
  }
}

$('#flSeg').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  filter = b.dataset.v;
  shown = PAGE;
  root.querySelectorAll('#flSeg button').forEach((x) => x.setAttribute('aria-checked', String(x === b)));
  seen = null;
  render();
});
$('#flMore').addEventListener('click', () => { shown += PAGE * 2; seen = null; render(); });

load();
setInterval(() => { if (!document.hidden) load(); }, POLL);
setInterval(status, 15000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
