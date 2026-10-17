// 오프닝 후보 O1~O3 공통 조각: 제목 낱말 올리기, 패널 차례로 넣기, 숫자 계기판, '다시 보기' 버튼
window.DFO = (() => {
  const $ = (s) => document.querySelector(s);
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const css = document.createElement('style');
  css.textContent = `h1 .w{display:inline-block;opacity:0;transform:translateY(.35em);filter:blur(8px)}
  h1.go .w{opacity:1;transform:none;filter:none;transition:opacity 700ms cubic-bezier(.23,1,.32,1),transform 700ms cubic-bezier(.23,1,.32,1),filter 700ms cubic-bezier(.23,1,.32,1)}
  .odo-wrap{display:inline-flex;align-items:flex-start;line-height:1}.odo-wrap>span{display:inline-block;height:1em;line-height:1}.odo{overflow:hidden}
  .odo .col{display:flex;flex-direction:column;transition:transform 1100ms cubic-bezier(.22,1,.36,1)}.odo .col i{font-style:normal;height:1em;line-height:1}
  .replay{position:fixed;right:16px;bottom:16px;z-index:90;height:34px;padding:0 14px;border-radius:99px;background:#0d253d;color:#fff;font:600 12.5px/1 Inter,system-ui,sans-serif;box-shadow:0 8px 24px -10px rgb(0 0 0/.5);cursor:pointer;border:0}
  .pre-hide .hero .kick,.pre-hide .hero .sub,.pre-hide .hero .btns,.pre-hide .hero .proof{opacity:0!important;transform:translateY(16px)!important}`;
  document.head.appendChild(css);
  function words() {
    const h = document.querySelector('h1');
    if (!h.querySelector('.w')) {
      const walk = (node) => [...node.childNodes].forEach((n) => {
        if (n.nodeType === 3) { const f = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach((w) => { if (!w) return; if (/^\s+$/.test(w)) f.appendChild(document.createTextNode(w)); else { const sp = document.createElement('span'); sp.className = 'w'; sp.textContent = w; f.appendChild(sp); } });
          n.replaceWith(f); } else if (n.nodeType === 1 && n.tagName !== 'BR') walk(n); });
      walk(h);
    }
    h.classList.remove('go'); [...h.querySelectorAll('.w')].forEach((w, i) => { w.style.transitionDelay = (i * 80) + 'ms'; });
    requestAnimationFrame(() => requestAnimationFrame(() => h.classList.add('go')));
  }
  function odo(el) {
    const t = el.textContent.trim(); if (!/\d/.test(t)) return;
    el.classList.add('odo-wrap');
    el.innerHTML = [...t].map((ch) => /\d/.test(ch) ? `<span class="odo"><span class="col" data-d="${ch}">${'0123456789'.split('').map((d) => `<i>${d}</i>`).join('')}</span></span>` : `<span>${ch}</span>`).join('');
    requestAnimationFrame(() => requestAnimationFrame(() => el.querySelectorAll('.col').forEach((c, i) => { c.style.transitionDelay = i * 60 + 'ms'; c.style.transform = `translateY(-${c.dataset.d}em)`; })));
  }
  const panels = () => [...document.querySelectorAll('.panel')];
  function showPanels(gap = 140, from = 0) { panels().slice(from).forEach((p, i) => setTimeout(() => p.classList.add('in'), i * gap)); }
  function heroRest(delay = 0) { setTimeout(() => { document.documentElement.classList.remove('pre-hide'); document.querySelectorAll('.hero .rv').forEach((el) => el.classList.add('in')); }, delay); }
  function nums(delay = 0) { setTimeout(() => ['pr1', 'pr2', 'pr3', 'cp'].forEach((id) => { const el = document.getElementById(id); if (el) odo(el); }), delay); }
  function replay() { const b = document.createElement('button'); b.className = 'replay'; b.type = 'button'; b.textContent = '↻ Replay intro'; b.onclick = () => location.reload(); document.body.appendChild(b); }
  return { reduce, words, odo, panels, showPanels, heroRest, nums, replay, $ };
})();
