// M1 인트로(최적화판).
// 1) 바로 시작: 인트로 틀과 autoplay 영상은 HTML 맨 위에 있어 페이지를 읽는 동안 재생이 시작된다(기다리지 않음).
//    무거운 것(three.js 장면, GSAP)은 인트로가 끝난 뒤에야 불러와 재생 중 끊김을 막는다(df-intro-done 이벤트).
// 2) 날아가기: 영상 속 로고 대신 '진짜 헤더 로고'(벡터)를 영상 마지막 장면과 같은 자리·크기로 키워 두고 원래 자리로 되돌린다(FLIP).
//    끝에서 바꿔 끼울 것이 없어 착지가 이어진다. 크기는 로그 공간으로 보간해 체감 속도가 고르게(48개 키프레임, transform 만 → 합성 단계).
// 3) 글은 opacity·transform 만(흐림 필터 애니메이션은 비싸서 뺌).
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const EOUT = 'cubic-bezier(0.23, 1, 0.32, 1)';
function bez(x1, y1, x2, y2) { const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  return (x) => { if (x <= 0) return 0; if (x >= 1) return 1; let lo = 0, hi = 1, t = x; for (let i = 0; i < 40; i++) { if (((ax * t + bx) * t + cx) * t < x) lo = t; else hi = t; t = (lo + hi) / 2; } return ((ay * t + by) * t + cy) * t; }; }
const FLY = bez(0.7, 0, 0.2, 1);
const done = () => dispatchEvent(new Event('df-intro-done'));
export async function intro(name, { flyAt = 4.32, base = '../mo/' } = {}) {
  const hd = document.querySelector('.hd'), logo = hd.querySelector('.logo'), rest = hd.querySelectorAll('.nav, .lang, .btn'), copy = document.querySelectorAll('.reveal');
  const showCopy = (delay = 0) => copy.forEach((e, i) => e.animate([{ opacity: 0, transform: 'translateY(14px)' }, { opacity: 1, transform: 'none' }], { duration: 900, delay: delay + i * 70, easing: EOUT, fill: 'both' }));
  const rp = document.querySelector('.replay'); if (rp) rp.onclick = () => location.reload();
  // 사이트 안의 다른 화면에서 넘어왔으면(같은 출처 referrer) 인트로 없이 바로 — 처음 들어올 때만 본다
  let inner = false; try { inner = !!document.referrer && new URL(document.referrer).origin === location.origin && !/[?&]intro\b/.test(location.search); } catch (e) {}
  if (reduce || inner) { showCopy(); done(); return; }
  // 인트로 틀·영상은 HTML 맨 위에 이미 있고 autoplay 로 바로 재생된다(이 모듈은 늦게 와도 된다).
  if (window.DF_NOINTRO) { showCopy(); done(); return; }
  const metaP = fetch(`${base}${name}.json`).then((r) => r.json()).catch(() => null);
  let ov = document.getElementById('intro');
  if (!ov) { ov = document.createElement('div'); ov.className = 'intro'; ov.id = 'intro'; ov.innerHTML = `<div class="ibg"></div><video muted playsinline autoplay preload="auto" src="${base}${name}.mp4"></video><button type="button" class="skip">Skip</button>`; document.body.appendChild(ov); }
  const v = ov.querySelector('video'), bg = ov.querySelector('.ibg');
  logo.style.opacity = '0'; rest.forEach((e) => { e.style.opacity = '0'; e.style.willChange = 'opacity'; });   // 층을 미리 만들어 둔다
  document.documentElement.classList.add('intro-on');
  const finishNoIntro = () => { ov.remove(); logo.style.opacity = ''; rest.forEach((e) => { e.style.opacity = ''; }); document.documentElement.classList.remove('intro-on'); showCopy(); done(); };
  let meta = null; metaP.then((m) => { meta = m; });
  let flown = false;
  const fly = async () => {
    if (flown) return; flown = true;
    if (!meta) meta = await Promise.race([metaP, new Promise((r) => setTimeout(() => r(null), 800))]);
    await Promise.race([document.fonts.load('15px Michroma'), new Promise((r) => setTimeout(r, 400))]);   // 헤더 글자가 제 글꼴인지
    if (!meta) { finishNoIntro(); return; }
    const vr = v.getBoundingClientRect(), side = Math.min(vr.width, vr.height), vx = vr.left + (vr.width - side) / 2, vy = vr.top + (vr.height - side) / 2;
    const [bx, by, bs] = meta.box; const t = logo.querySelector('svg').getBoundingClientRect(), lr = logo.getBoundingClientRect();
    const k = (bs * side) / t.width, dx = vx + bx * side - t.left, dy = vy + by * side - t.top;
    logo.style.transformOrigin = `${t.left - lr.left}px ${t.top - lr.top}px`; hd.style.zIndex = '90';
    const N = 48, kf = [];
    for (let i = 0; i <= N; i++) { const p = FLY(i / N), s = Math.exp(Math.log(k) * (1 - p)); kf.push({ transform: `translate(${dx * (1 - p)}px, ${dy * (1 - p)}px) scale(${s})` }); }
    // 영상 마지막 장면과 같은 자리에 헤더 로고를 켜고 같은 프레임에 영상을 숨긴다
    logo.style.opacity = '1'; const a = logo.animate(kf, { duration: 1050, easing: 'linear', fill: 'backwards' }); v.style.visibility = 'hidden';
    bg.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 650, delay: 280, easing: 'ease', fill: 'forwards' });
    showCopy(520);
    // 메뉴·언어·버튼은 착지한 뒤에 켠다(날아가는 도중에 새 합성 층이 생기면 로고가 다시 그려지며 한두 프레임 비는 문제)
    a.onfinish = () => {
      ov.remove(); hd.style.zIndex = ''; logo.style.transformOrigin = ''; document.documentElement.classList.remove('intro-on');
      rest.forEach((e, i) => { const f = e.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 420, delay: i * 40, easing: 'ease', fill: 'backwards' }); e.style.opacity = ''; f.onfinish = () => { e.style.willChange = ''; }; });
      done();
    };
  };
  // 영상 시간에 맞춰 날아가기(프레임 단위 콜백이 있으면 그걸로)
  if ('requestVideoFrameCallback' in v) { const cb = (now, md) => { if (md.mediaTime >= flyAt) fly(); else v.requestVideoFrameCallback(cb); }; v.requestVideoFrameCallback(cb); }
  else v.addEventListener('timeupdate', () => { if (v.currentTime >= flyAt) fly(); });
  v.addEventListener('ended', fly);
  const skip = () => { if (flown) return; try { v.currentTime = Math.max(0, (v.duration || 4.5) - 0.05); } catch (e) {} v.pause(); setTimeout(fly, 80); };
  ov.querySelector('.skip').onclick = skip; addEventListener('keydown', skip, { once: true }); addEventListener('wheel', skip, { once: true, passive: true }); addEventListener('touchmove', skip, { once: true, passive: true });
  if (v.paused && !v.ended) v.play().catch(finishNoIntro);
  if (v.ended || v.currentTime >= flyAt) fly();                    // 이 모듈이 늦게 와서 영상이 이미 끝났으면 바로
  else setTimeout(() => { if (v.paused && v.currentTime === 0) finishNoIntro(); }, 4000);   // 끝내 재생이 안 되면
}
