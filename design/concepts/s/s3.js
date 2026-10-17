// S3 · Word (Raycast·Framer, 옛 '글자 속으로'): 화면이 물러나며 거대한 delfona 글자가 나타나고, 글자의 o 속으로 날아 들어가면 빛이 화면을 채운다
DFS.ready(() => {
  const hero = document.querySelector('.hero');
  const w = document.createElement('div'); w.className = 's-word';
  w.innerHTML = '<span>delf<em>o</em>na</span>';
  const css = document.createElement('style');
  css.textContent = `.s-word{position:absolute;left:0;right:0;top:0;height:100vh;height:100svh;z-index:7;display:grid;place-items:center;pointer-events:none;opacity:0;overflow:hidden}
  .s-word span{display:inline-block;position:relative}.s-word em{display:inline-block}
  .s-word span{font-size:min(24vw,330px);font-weight:800;letter-spacing:-.06em;line-height:1;background:linear-gradient(120deg,#533afd,#7aa7ff 45%,#2fd9c4 80%);-webkit-background-clip:text;background-clip:text;color:transparent;will-change:transform}
  .s-word em{font-style:normal}`;
  document.head.appendChild(css); hero.appendChild(w);
  const span = w.querySelector('span'), o = w.querySelector('em');
  // 변형(scale)에 영향받지 않는 offset 값으로 'o'의 가운데를 잡는다
  const setOrigin = () => gsap.set(span, { transformOrigin: `${o.offsetLeft + o.offsetWidth / 2}px ${o.offsetTop + o.offsetHeight * 0.6}px` });
  document.fonts && document.fonts.ready.then(() => { setOrigin(); ScrollTrigger.refresh(); });
  setOrigin();
  gsap.timeline({ scrollTrigger: { trigger: hero, start: 'top top', end: '+=200%', pin: true, scrub: .8, onRefresh: setOrigin } })
    .fromTo('.hero .wrap', { filter: 'blur(0px)' }, { scale: .9, opacity: 0, filter: 'blur(12px)', duration: .35, ease: 'power2.in' }, 0)
    .to('.mesh', { opacity: .25, duration: .35 }, 0)
    .fromTo(w, { opacity: 0 }, { opacity: 1, duration: .2 }, .2)
    .fromTo(span, { scale: .7, y: 40 }, { scale: 1, y: 0, duration: .25, ease: 'power2.out' }, .2)
    .to(span, { scale: 70, duration: .5, ease: 'power3.in' }, .5)
    .to(w, { opacity: 0, duration: .08 }, .94);
});
