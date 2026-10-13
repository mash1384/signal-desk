// 지금(홈): 실시간 속보 8개, 최근 6시간 흐름 한 줄, 내 코인 시세 칸.
const DF = window.DF;
const $ = (s) => document.querySelector(s);
const esc = DF.esc;

function headline(d) {
  const since = Date.now() / 1000 - 6 * 3600;
  const xs = d.items.filter((it) => it.t >= since);
  const u = xs.filter((it) => it.v === '호재').length, n = xs.filter((it) => it.v === '악재').length;
  const el = $('#todayH');
  if (u + n < 5) return;
  const say = n > u * 1.2 ? '악재 소식이 더 많았어요' : u > n * 1.2 ? '호재 소식이 더 많았어요' : '호재와 악재가 비슷했어요';
  el.textContent = `최근 6시간, ${say}`;
  $('#todaySub').innerHTML = `<span class="up">호재 ${u}</span> · <span class="down">악재 ${n}</span> <span class="muted">· 지난 6시간 속보 ${xs.length}개 기준</span>`;
}

let seen = null;
DF.onFlash((d, err) => {
  const list = $('#liveList'), upd = $('#liveU');
  if (!d) {
    upd.textContent = err === 'off' ? '' : '불러오지 못했어요';
    list.innerHTML = '<li class="fl-empty">지금은 속보를 불러올 수 없어요. 잠시 뒤 다시 확인해 주세요.</li>';
    return;
  }
  upd.textContent = DF.flashStatus(d);
  upd.classList.toggle('is-stale', /멈췄/.test(upd.textContent));
  const xs = d.items.slice(0, 8);
  list.innerHTML = xs.length ? xs.map((it) => DF.fi(it, seen)).join('') : '<li class="fl-empty">최근 이틀 동안 속보가 없었어요.</li>';
  seen = new Set(d.items.map((it) => it.id));
  headline(d);
});

// 내 코인: 별표한 코인을 시세 칸 뒤에 붙인다
function myTiles() {
  const box = $('#pulse');
  box.querySelectorAll('.pt[data-mine]').forEach((el) => el.remove());
  const have = new Set([...box.querySelectorAll('[data-live]')].map((el) => el.dataset.live));
  const add = DF.stars().filter((s) => !have.has(s)).slice(0, 8);
  box.insertAdjacentHTML('beforeend', add.map((s) => `<a class="pt" data-mine href="${DF.base}coins/${esc(s.toLowerCase())}/" data-live="${esc(s)}">
    <span class="pt__k">★ ${esc(s)}</span><span class="pt__v" data-live-p>–</span><span class="pt__s" data-live-c></span></a>`).join(''));
  if (add.length) DF.refreshLive();
}
myTiles();
document.addEventListener('df:stars', myTiles);
