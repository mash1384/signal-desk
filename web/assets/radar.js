// 레이더: 위쪽 [상장 | 발표] 표시를 지금 보고 있는 구역에 맞춘다.
const links = [...document.querySelectorAll('.rd-nav a')];
const io = new IntersectionObserver((es) => {
  es.forEach((e) => {
    if (!e.isIntersecting) return;
    links.forEach((a) => (a.dataset.rd === e.target.id ? a.setAttribute('aria-current', 'true') : a.removeAttribute('aria-current')));
  });
}, { rootMargin: '-40% 0px -55% 0px' });
['lr', 'events'].forEach((id) => { const el = document.getElementById(id); if (el) io.observe(el); });
