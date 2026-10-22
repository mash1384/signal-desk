// 가로로 넘기는 줄에 '더 있음' 표시(D3): 넘칠 때만 오른쪽 끝을 흐리게 + › 단추(누르면 한 화면만큼), 끝까지 가면 걷는다. lk.js가 필요할 때만 부른다.
import { T } from './lk.js';
const CSS = `.hs-more{-webkit-mask-image:linear-gradient(to right,#000 calc(100% - 56px),transparent);mask-image:linear-gradient(to right,#000 calc(100% - 56px),transparent)}
.hs-btn{position:absolute;z-index:3;width:30px;height:30px;margin-top:-15px;border-radius:99px;background:#fff;color:var(--primary);font:700 17px/1 system-ui,sans-serif;display:grid;place-items:center;box-shadow:0 1px 2px rgb(13 37 61/.12),0 4px 12px rgb(13 37 61/.14)}
:root[data-theme="dark"] .hs-btn{background:#18243a}
.hs-btn[hidden]{display:none}`;
export function init(sel) {
  const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  const seen = new Map();
  const fit = (sc, b) => { const host = b.parentElement, r = sc.getBoundingClientRect(), h = host.getBoundingClientRect(), over = sc.scrollWidth > sc.clientWidth + 4, end = sc.scrollLeft + sc.clientWidth >= sc.scrollWidth - 4;
    sc.classList.toggle('hs-more', over && !end); b.hidden = !over || end; b.style.left = (r.right - h.left - 36) + 'px'; b.style.top = (r.top - h.top + r.height / 2) + 'px'; };
  const scan = () => {
    for (const [sc, b] of seen) if (!sc.isConnected) { b.remove(); seen.delete(sc); }
    document.querySelectorAll(sel).forEach((sc) => {
      let b = seen.get(sc);
      if (!b) {
        if (sc.scrollWidth <= sc.clientWidth + 4) return;
        const host = sc.parentElement; if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
        b = document.createElement('button'); b.type = 'button'; b.className = 'hs-btn'; b.textContent = '›'; b.setAttribute('aria-label', T('Scroll for more', '옆으로 더 보기'));
        b.onclick = () => sc.scrollBy({ left: sc.clientWidth * 0.8, behavior: 'smooth' });
        sc.addEventListener('scroll', () => fit(sc, b), { passive: true }); host.appendChild(b); seen.set(sc, b);
      }
      fit(sc, b);
    });
  };
  let t = 0; const later = () => { clearTimeout(t); t = setTimeout(scan, 150); };
  scan(); addEventListener('resize', later); new MutationObserver(later).observe(document.body, { childList: true, subtree: true });
}
