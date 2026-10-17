// 스크롤 후보 S1~S5 공통: O2 오프닝이 끝난 뒤(약 3.3초) 스크롤 장면을 붙인다. 오프닝 중 첫 스크롤이 오면 바로 붙인다.
window.DFS = (() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches, desk = () => innerWidth >= 1000;
  const st = document.createElement('style');
  st.textContent = `html,body{overflow-x:clip}.hero{overflow-x:clip}.scrolly .panel{transition:opacity 600ms ease!important}.scrolly .hero .rv{transition:none!important}
  .s-cap{position:absolute;left:0;right:0;z-index:6;text-align:center;pointer-events:none;opacity:0;padding:0 20px}
  .s-cap b{display:block;font-size:clamp(28px,4vw,52px);font-weight:300;letter-spacing:-.04em;line-height:1.1;color:var(--ink)}
  :lang(ko) .s-cap b{font-weight:500}.s-cap span{display:block;margin-top:8px;font-size:15px;color:var(--mute)}
  .s-prog{position:absolute;left:50%;bottom:28px;z-index:6;width:160px;height:3px;margin-left:-80px;border-radius:99px;background:rgb(13 37 61/.12);overflow:hidden;opacity:0}
  .s-prog i{display:block;height:100%;width:100%;background:var(--ink);transform-origin:left;transform:scaleX(0)}`;
  document.head.appendChild(st);
  function ready(fn) {
    if (reduce) return;
    let done = false;
    const go = () => { if (done) return; done = true; document.documentElement.classList.add('scrolly');
      document.querySelectorAll('.panel').forEach((p) => { p.classList.add('in'); p.style.transform = ''; });
      gsap.registerPlugin(ScrollTrigger); fn(); ScrollTrigger.refresh(); };
    setTimeout(go, 3300); addEventListener('wheel', go, { once: true, passive: true }); addEventListener('touchmove', go, { once: true, passive: true });
  }
  const cap = (parent, top, en, ko) => { const c = document.createElement('div'); c.className = 's-cap'; c.style.top = top;
    const set = () => { const k = DFI.lang() === 'ko'; c.innerHTML = `<b>${k ? ko[0] : en[0]}</b><span>${k ? ko[1] : en[1]}</span>`; }; set(); DFI.onLang(set); parent.appendChild(c); return c; };
  const prog = (parent) => { const p = document.createElement('div'); p.className = 's-prog'; p.innerHTML = '<i></i>'; parent.appendChild(p); return p; };
  const left = () => document.querySelector('.hero .wrap > div:first-child');
  const P = (n) => document.querySelector('.p' + n);
  // 모바일 공통: 고정 없이, 글은 위로 흐려지며 빠지고 카드는 들어올 때 떠오른다
  function mobile() {
    gsap.to(left(), { y: -60, opacity: .2, ease: 'none', scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true } });
    [1, 2, 3].forEach((n) => gsap.from(P(n), { y: 70, opacity: 0, rotationX: 18, transformPerspective: 800, ease: 'power3.out', duration: .9, scrollTrigger: { trigger: P(n), start: 'top 92%' } }));
    gsap.to('.mesh', { y: 120, ease: 'none', scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true } });
  }
  return { reduce, desk, ready, cap, prog, left, P, mobile };
})();
