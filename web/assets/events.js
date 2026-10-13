// 이벤트 리스크: 남은 시간, 그리고 '내 돈으로 보면' 계산기(넣은 돈 × 레버리지 × 과거 흔들림 폭).
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const nowSec = () => Date.now() / 1000;
const left = (sec) => {
  if (sec <= 0) return '발표됨';
  const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60);
  return d ? `${d}일 ${h}시간 남음` : h ? `${h}시간 ${m}분 남음` : `${Math.max(1, m)}분 남음`;
};
const won = (v) => '±' + Math.round(v).toLocaleString('ko-KR') + '원';

function tick() { $$('[data-left]').forEach((el) => { el.textContent = left(Number(el.dataset.left) - nowSec()); }); }
tick();
setInterval(tick, 30000);

const calc = $('#erCalc');
if (calc) {
  const med = +calc.dataset.med, p90 = +calc.dataset.p90, mx = +calc.dataset.max;
  const amt = $('#erAmt');
  let lev = 1;
  const read = () => Math.min(1e12, Math.max(0, Number(String(amt.value).replace(/[^\d]/g, '')) || 0));
  const render = () => {
    const a = read();
    $('#erMed').textContent = won(a * med / 100 * lev);
    $('#erP90').textContent = won(a * p90 / 100 * lev);
    const worst = mx * lev;
    $('#erNote').innerHTML = lev === 1
      ? `가장 크게 흔들렸던 날(±${mx.toFixed(1)}%)이었다면 1시간 만에 <b>${won(a * mx / 100)}</b>이 움직였어요.`
      : `${lev}배라 흔들림도 ${lev}배예요. 가장 크게 흔들렸던 날이었다면 1시간 만에 원금의 <b>±${worst.toFixed(0)}%</b>가 움직였어요.${worst >= 50 ? ' <b class="down">강제 청산될 수 있는 크기예요.</b>' : ''}`;
  };
  amt.addEventListener('input', () => {
    const v = read();
    amt.value = v ? v.toLocaleString('ko-KR') : '';
    render();
  });
  $$('[data-lev]', calc).forEach((b) => b.addEventListener('click', () => {
    lev = +b.dataset.lev;
    $$('[data-lev]', calc).forEach((x) => x.setAttribute('aria-checked', String(x === b)));
    render();
  }));
  render();
}
