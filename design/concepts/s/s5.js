// S5 · Stack (Mercury·Revolut 카드 쌓기): 첫 화면이 뒤로 물러나며(작아지고 둥글어지고 어두워짐) 그 위로 큰 카드 세 장이 차례로 쌓인다
DFS.ready(() => {
  const hero = document.querySelector('.hero');
  const css = document.createElement('style');
  css.textContent = `.hero{position:sticky;top:var(--ht,0px);transform-origin:50% 0;will-change:transform}
  .stk{position:relative;z-index:5;padding:0 20px 10vh}
  .stk-card{position:sticky;top:12vh;width:100%;max-width:1180px;min-height:72vh;margin:0 auto 6vh;border-radius:32px;padding:clamp(28px,4vw,56px);display:grid;gap:28px;align-content:space-between;transform-origin:50% 0;will-change:transform;box-shadow:0 -20px 60px -30px rgb(13 37 61/.35)}
  @media(min-width:1000px){.stk-card{grid-template-columns:1fr 1.1fr;align-items:end}}
  .stk-card .k{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.7}
  .stk-card h3{margin-top:12px;font-size:clamp(34px,5vw,68px);font-weight:300;letter-spacing:-.045em;line-height:1.02}
  :lang(ko) .stk-card h3{font-weight:500}
  .stk-card p{margin-top:14px;font-size:17px;opacity:.75;max-width:30rem}
  .c1{background:#0d1f36;color:#fff}.c2{background:#533afd;color:#fff}.c3{background:#f6f9fc;color:#0d253d;box-shadow:0 0 0 1px #e3e8ee,0 -20px 60px -30px rgb(13 37 61/.3)}
  .stk-live{display:grid;gap:10px}.stk-live div{padding:14px 16px;border-radius:14px;background:rgb(255 255 255/.06);font-size:15px;line-height:1.45}
  .stk-live b{display:inline-block;margin-right:8px;font-size:12px}.stk-big{font-size:clamp(56px,9vw,120px);font-weight:300;letter-spacing:-.05em;line-height:1;font-variant-numeric:tabular-nums}`;
  document.head.appendChild(css);
  const sec = document.createElement('section'); sec.className = 'stk';
  const T = (en, ko) => DFI.lang() === 'ko' ? ko : en;
  sec.innerHTML = `<article class="stk-card c1"><div><p class="k">01 · Live</p><h3>${T('Every headline, judged as it lands.', '들어오는 모든 소식을, 바로 판정.')}</h3><p>${T('Positive or negative, how big, which coins, how many outlets.', '호재·악재, 크기, 관련 코인, 몇 곳이 보도했는지.')}</p></div><div class="stk-live" id="stkL"></div></article>
  <article class="stk-card c2"><div><p class="k">02 · Brief</p><h3>${T('Yesterday, on one page.', '어제를, 한 장으로.')}</h3><p>${T('Every morning at 09:00 KST. Numbers counted by software.', '매일 오전 9시. 숫자는 프로그램이 세요.')}</p></div><div><p class="stk-big" id="stkB">–</p><p id="stkBh"></p></div></article>
  <article class="stk-card c3"><div><p class="k">03 · Radar</p><h3>${T('Before the big release.', '큰 발표 전에.')}</h3><p>${T('How much Bitcoin moved the last times — and how long until the next one.', '지난번 비트코인이 얼마나 흔들렸는지, 다음까지 얼마나 남았는지.')}</p></div><div><p class="stk-big" id="stkR">–</p><p id="stkRn"></p></div></article>`;
  (hero.parentElement && hero.parentElement.classList.contains('pin-spacer') ? hero.parentElement : hero).after(sec);   // 고정(pin)된 첫 화면은 감싸는 상자 뒤에
  DFD.flash().then((d) => { document.getElementById('stkL').innerHTML = d.items.filter((x) => x.v !== '중립' && DFI.has(x)).slice(0, 3).map((x) => `<div><b class="${DFD.vcls(x.v)}">${DFI.v(x.v)}</b>${DFD.esc(DFI.line(x))}</div>`).join('');
    const c = DFD.day24(d.items); document.getElementById('stkB').innerHTML = `<span class="up" style="color:#9ef0c9">${c.u}</span> / <span style="color:#ffb1a6">${c.d}</span>`; });
  DFD.brief().then((b) => { document.getElementById('stkBh').textContent = DFI.line({ id: 'brief:' + b.date }) || b.headline; }).catch(() => {});
  DFD.nextEvent().then((u) => { if (!u) return; const s = Math.max(0, u.ts - Date.now() / 1000); document.getElementById('stkR').textContent = `${Math.floor(s / 3600)}h ${Math.floor(s % 3600 / 60)}m`;
    document.getElementById('stkRn').textContent = `${u.vs_normal ? u.vs_normal.toFixed(1) + '× ' : ''}${T('normal move after past releases', '지난 발표 뒤 평소 대비 흔들림')} · ${DFI.lang() === 'ko' ? u.name : ({ cpi: 'US CPI', ppi: 'US PPI', nfp: 'US Jobs Report', fomc: 'Fed Rate Decision', pce: 'US PCE', gdp: 'US GDP' }[u.kind] || u.title)}`; }).catch(() => {});
  // 첫 화면이 화면보다 길면(모바일) 아래 끝이 보일 때 멈추게
  const ht = () => document.documentElement.style.setProperty('--ht', Math.min(0, innerHeight - hero.offsetHeight) + 'px'); ht(); addEventListener('resize', ht);
  gsap.fromTo(hero, { scale: 1, borderRadius: 0, filter: 'brightness(1)' }, { scale: .92, borderRadius: 32, filter: 'brightness(.92)', ease: 'none', scrollTrigger: { trigger: sec, start: 'top bottom', end: 'top top', scrub: true } });
  gsap.to(hero, { opacity: 0, ease: 'none', scrollTrigger: { trigger: sec, start: 'top top', end: '+=60%', scrub: true } });
  const cards = [...sec.querySelectorAll('.stk-card')];
  cards.forEach((c, i) => { if (i === cards.length - 1) return;
    gsap.fromTo(c, { scale: 1, filter: 'brightness(1)' }, { scale: .93, filter: 'brightness(.94)', ease: 'none', scrollTrigger: { trigger: cards[i + 1], start: 'top bottom', end: 'top 12%', scrub: true } }); });
});
