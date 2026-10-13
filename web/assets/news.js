// 속보: 실시간 속보 목록(거르기·더 보기)과 기사 목록(분야 거르기·더 보기).
const DF = window.DF;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const PAGE = 20;

let D = null, filter = 'all', shown = PAGE, seen = null;

function pick() {
  const xs = D.items;
  if (filter === 'big') return xs.filter((it) => it.s >= 2);
  if (filter === 'mine') { const m = new Set(DF.stars()); return xs.filter((it) => it.coins.some((c) => m.has(c))); }
  if (filter === 'all') return xs;
  return xs.filter((it) => it.v === filter);
}

function render() {
  const list = $('#flList'), more = $('#flMore');
  if (!D) return;
  const xs = pick();
  const empty = filter === 'mine' && !DF.stars().length
    ? `아직 담은 코인이 없어요. <a class="more" href="${DF.base}coins/">코인에서 별표 누르기</a>`
    : `최근 이틀 동안 ${{ all: '속보가', big: '큰 소식이', mine: '내 코인 소식이', 호재: '호재 소식이', 악재: '악재 소식이' }[filter]} 없었어요.`;
  list.innerHTML = xs.length ? xs.slice(0, shown).map((it) => DF.fi(it, seen)).join('') : `<li class="fl-empty">${empty}</li>`;
  more.hidden = xs.length <= shown;
  more.textContent = `더 보기 (${xs.length - shown}개 남음)`;
}

DF.onFlash((d, err, prev) => {
  if (!d) {
    $('#flUpd').textContent = err === 'off' ? '' : '속보를 불러오지 못했어요. 잠시 뒤 다시 확인해 주세요.';
    $('#flList').innerHTML = '<li class="fl-empty">지금은 속보를 불러올 수 없어요.</li>';
    return;
  }
  seen = prev ? new Set(prev.items.map((it) => it.id)) : null;
  D = d;
  $('#flUpd').textContent = DF.flashStatus(d) + ` · 지난 48시간 ${d.items.length}개`;
  render();
});

$('#flSeg').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  filter = b.dataset.v;
  shown = PAGE;
  seen = null;
  $$('#flSeg button').forEach((x) => x.setAttribute('aria-checked', String(x === b)));
  render();
});
$('#flMore').addEventListener('click', () => { shown += PAGE * 2; seen = null; render(); });
document.addEventListener('df:stars', () => { if (filter === 'mine') render(); });

// 기사: 분야 거르기와 40개씩 더 보기(목록은 미리 200개를 그려 둔다)
let cat = 'all', arShown = 40;
function arRender() {
  const rows = $$('#arList > li').filter((li) => cat === 'all' || li.dataset.cat === cat);
  $$('#arList > li').forEach((li) => { li.hidden = true; });
  rows.slice(0, arShown).forEach((li) => { li.hidden = false; });
  $('#arMore').hidden = rows.length <= arShown;
}
$('#arSeg').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  cat = b.dataset.c;
  arShown = 40;
  $$('#arSeg button').forEach((x) => x.setAttribute('aria-checked', String(x === b)));
  arRender();
});
$('#arMore').addEventListener('click', () => { arShown += 40; arRender(); });
arRender();
