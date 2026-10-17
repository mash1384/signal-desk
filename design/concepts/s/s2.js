// S2 · Deck (Ramp): 흩어진 카드 세 장이 한 덱으로 모였다가, 3D로 기울어진 한 줄로 펼쳐진다
DFS.ready(() => {
  if (!DFS.desk()) return DFS.mobile();
  const hero = document.querySelector('.hero'), hr = hero.getBoundingClientRect(), ps = [1, 2, 3].map(DFS.P), rs = ps.map((p) => p.getBoundingClientRect());
  const c0 = { x: rs[0].left + rs[0].width / 2, y: rs[0].top + rs[0].height / 2 };
  const tw = innerWidth * 0.27, cx = [0.2, 0.5, 0.8].map((f) => innerWidth * f), cy = hr.top + innerHeight * 0.6;
  const cap = DFS.cap(hero, '13vh', ['Live, brief, price — side by side.', 'One glance, every signal.'], ['속보, 정리, 시세를 한 줄에.', '한눈에, 모든 신호.']);
  const tl = gsap.timeline({ scrollTrigger: { trigger: hero, start: 'top top', end: '+=180%', pin: true, scrub: .7 } })
    .fromTo(DFS.left(), { filter: 'blur(0px)' }, { x: -80, opacity: 0, filter: 'blur(8px)', duration: .35 }, 0)
    .to('.mesh', { opacity: .35, scale: 1.1, duration: 1, ease: 'none' }, 0);
  ps.forEach((p, i) => {
    const r = rs[i], mx = r.left + r.width / 2, my = r.top + r.height / 2;
    tl.to(p, { x: c0.x - mx + (i - 1) * 14, y: c0.y - my + (i - 1) * 10, rotation: (i - 1) * 4, scale: rs[0].width / r.width * 0.92, duration: .35, ease: 'power2.inOut' }, .05)
      .to(p, { x: cx[i] - mx, y: cy - my, rotation: 0, rotationY: (1 - i) * 16, z: i === 1 ? 60 : 0, scale: tw / r.width, duration: .5, ease: 'power3.inOut' }, .45);
  });
  tl.to(cap, { opacity: 1, duration: .2 }, .8);
});
