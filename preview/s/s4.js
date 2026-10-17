// S4 · Track (Stripe·Vercel): 글이 왼쪽으로 빠지고, 카드 세 장이 한 줄로 커져 세로 스크롤만큼 옆으로 흐른다(진행 막대와 단계 문구)
DFS.ready(() => {
  if (!DFS.desk()) return DFS.mobile();
  const hero = document.querySelector('.hero'), hr = hero.getBoundingClientRect(), ps = [1, 2, 3].map(DFS.P), rs = ps.map((p) => p.getBoundingClientRect());
  const W = innerWidth * 0.46, gap = innerWidth * 0.05, x0 = innerWidth * 0.27, cy = hr.top + innerHeight * 0.56;
  const caps = [['01 · Live', 'Every headline judged as it lands.'], ['02 · Brief', 'Yesterday on one page, every morning.'], ['03 · Price', 'Your coins, next to the news.']];
  const capsKo = [['01 · 속보', '들어오는 모든 소식을 바로 판정.'], ['02 · 정리', '매일 아침, 어제를 한 장으로.'], ['03 · 시세', '내 코인을, 소식 옆에서.']];
  const cap = DFS.cap(hero, '11vh', caps[0], capsKo[0]), pg = DFS.prog(hero);
  const setCap = (k) => { const c = (DFI.lang() === 'ko' ? capsKo : caps)[k]; cap.innerHTML = `<b>${c[0]}</b><span>${c[1]}</span>`; };
  const travel = 2 * (W + gap);
  const tl = gsap.timeline({ scrollTrigger: { trigger: hero, start: 'top top', end: '+=260%', pin: true, scrub: .7,
    onUpdate: (s) => { const p = Math.max(0, (s.progress - .25) / .75); pg.firstChild.style.transform = `scaleX(${p})`; setCap(Math.min(2, Math.floor(p * 3 * .999))); } } })
    .to(DFS.left(), { x: -innerWidth * 0.6, opacity: 0, duration: .25, ease: 'power2.in' }, 0)
    .to('.mesh', { x: -200, opacity: .5, duration: 1, ease: 'none' }, 0)
    .to([cap, pg], { opacity: 1, duration: .1 }, .2);
  ps.forEach((p, i) => { const r = rs[i], s = W / r.width;
    tl.to(p, { x: x0 + i * (W + gap) - (r.left + r.width / 2) + W / 2 - W / 2, y: cy - (r.top + r.height / 2), scale: s, rotation: 0, duration: .25, ease: 'power3.inOut' }, 0); });
  tl.to(ps, { x: `-=${travel}`, duration: .75, ease: 'none' }, .25);
});
