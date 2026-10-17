// 인트로가 끝나고 글이 다 올라온 뒤(약 1.6초 + 브라우저가 한가할 때) 아래 장면(three.js 파형 등)을 불러온다.
// 인트로·착지·글 올라오기 동안 메인 스레드와 GPU 를 비워 두기 위해서다.
addEventListener('df-intro-done', () => {
  const go = () => import('../p/p5.js?v=171531');
  setTimeout(() => ('requestIdleCallback' in window ? requestIdleCallback(go, { timeout: 1500 }) : go()), 1600);
}, { once: true });
