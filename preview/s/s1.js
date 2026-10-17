// S1 · Zoom (Apple·Linear): 첫 화면을 고정한 채, 글은 흐려지며 올라가고 옆 카드는 빠지고, 실시간 피드 카드가 화면 가운데로 커진다
DFS.ready(() => {
  if (!DFS.desk()) return DFS.mobile();
  const hero = document.querySelector('.hero'), p1 = DFS.P(1), r = p1.getBoundingClientRect(), hr = hero.getBoundingClientRect();
  const sc = Math.min(1.45, innerWidth * 0.6 / r.width), dx = innerWidth / 2 - (r.left + r.width / 2), dy = innerHeight * 0.58 - (r.top - hr.top + r.height / 2);
  const c = DFS.cap(hero, '12vh', ['Every signal, the moment it breaks.', 'Live, judged, de-duplicated.'], ['모든 신호를, 나오는 그 순간.', '실시간으로, 판정해서, 하나로 묶어서.']);
  gsap.timeline({ scrollTrigger: { trigger: hero, start: 'top top', end: '+=150%', pin: true, scrub: .7 } })
    .fromTo(DFS.left(), { filter: 'blur(0px)' }, { y: -140, opacity: 0, filter: 'blur(10px)', duration: .45, ease: 'power2.in' }, 0)
    .to(DFS.P(2), { x: -260, y: 240, rotation: -8, opacity: 0, duration: .5, ease: 'power2.in' }, 0)
    .to(DFS.P(3), { x: 300, y: 260, rotation: 8, opacity: 0, duration: .5, ease: 'power2.in' }, 0)
    .to(p1, { x: dx, y: dy, scale: sc, boxShadow: '0 60px 120px -40px rgba(13,37,61,.55)', duration: .9, ease: 'power3.inOut' }, .1)
    .to('.mesh', { scale: 1.25, y: -80, opacity: .55, duration: 1, ease: 'none' }, 0)
    .to(c, { opacity: 1, y: -10, duration: .3 }, .65);
});
