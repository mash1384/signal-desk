// 용어 풀이(2026-10-24 운영자): 브리핑 · 테마 데스크 글의 어려운 말에 점선 밑줄 → 모바일은 누르면, PC는 마우스를 올리면(키보드는 초점) 풀이 창.
// 풀이는 고정 문장(AI 아님). 칸(문단)마다 처음 나온 말에만 붙인다. 페이지가 한가해진 뒤 불러오고, 풀이 문장(gl-d.js)은 창을 처음 열 때 불러온다(첫 화면 무게에 안 들어가게).
// [한국어 표기들, 영어 표기들] — 풀이 문장은 gl-d.js(같은 순서, 처음 열 때 불러온다)
const G = [
  [['현물 ETF'], ['spot ETF', 'spot bitcoin ETF', 'spot ether ETF']],
  [['ETF', '상장지수펀드'], ['ETF']],
  [['PCE'], ['PCE']],
  [['CPI', '소비자물가'], ['CPI', 'consumer prices']],
  [['PPI', '생산자물가'], ['PPI', 'producer prices']],
  [['WTI'], ['WTI']],
  [['브렌트'], ['Brent']],
  [['연준'], ['Fed', 'Federal Reserve']],
  [['FOMC'], ['FOMC']],
  [['기준금리'], ['policy rate']],
  [['금리 동결'], ['rate hold', 'hold rates']],
  [['국채'], ['Treasury', 'Treasuries']],
  [['10년물', '10년 만기'], ['10-year']],
  [['5년물', '5년 만기'], ['5-year']],
  [['30년물', '30년 만기'], ['30-year']],
  [['bp'], ['bp', 'basis points', 'basis point']],
  [['%p'], ['percentage point', 'percentage points']],
  [['선물'], ['futures']],
  [['나스닥100'], ['Nasdaq 100', 'Nasdaq-100']],
  [['S&P500', 'S&P 500'], ['S&P 500', 'S&P500']],
  [['다우'], ['Dow']],
  [['VIX'], ['VIX']],
  [['달러 지수'], ['dollar index']],
  [['CDS'], ['CDS']],
  [['토큰화'], ['tokenization', 'tokenized']],
  [['스테이블코인'], ['stablecoin', 'stablecoins']],
  [['순유입'], ['net inflow', 'net inflows']],
  [['순유출'], ['net outflow', 'net outflows']],
  [['스테이킹'], ['staking']],
  [['디파이'], ['DeFi']],
  [['청산'], ['liquidation', 'liquidations']],
  [['레버리지'], ['leverage']],
  [['펀딩비'], ['funding rate']],
  [['시가총액'], ['market cap', 'market capitalization']],
  [['유동성'], ['liquidity']],
  [['위험자산'], ['risk assets']],
  [['안전자산'], ['safe haven', 'safe-haven']],
  [['빅테크'], ['Big Tech']],
  [['호르무즈'], ['Hormuz']],
  [['관세'], ['tariff', 'tariffs']],
  [['GDP'], ['GDP']],
  [['비농업 고용'], ['nonfarm payrolls', 'payrolls']],
  [['IPO'], ['IPO']],
  [['공매도'], ['short selling', 'short sellers']],
  [['반감기'], ['halving']],
];
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
function table(lang) {
  const by = new Map(), forms = [];
  G.forEach((g, i) => (lang === 'ko' ? g[0] : g[1]).forEach((f) => { by.set(f, i); forms.push(f); }));
  forms.sort((a, b) => b.length - a.length);
  const alt = (xs) => xs.map(esc).join('|') || '(?!)';
  // 한국어: 앞이 한글 · 영문이 아닐 때만(‘선물’이 다른 낱말 속에서 잡히지 않게). 숫자 뒤는 괜찮다(‘20.4bp’, ‘0.2%p’) — 숫자로 시작하는 말(‘10년물’)만 숫자 뒤를 막는다.
  // 영어: 대소문자를 그대로(‘fed’ 같은 동사를 연준으로 보지 않게), 낱말 경계.
  const re = lang === 'ko'
    ? new RegExp(`(?<![가-힣A-Za-z0-9])(${alt(forms.filter((f) => /^\d/.test(f)))})|(?<![가-힣A-Za-z])(${alt(forms.filter((f) => !/^\d/.test(f)))})`, 'g')
    : new RegExp(`(?<![A-Za-z0-9])(${alt(forms)})(?![A-Za-z0-9])`, 'g');
  return { by, re };
}
const T = { ko: table('ko'), en: table('en') };
const SEL = '.bf-3 li > span, .bf-rg p, .bf-c > p[data-l], .bf-dp p, .bf-box li > span, .sum.dk .dks, .sum.dk .dkg li';
// 칸마다 처음 나온 말에만 밑줄 단추. 이미 한 칸은 건너뛴다(다시 그려도 두 번 안 붙는다)
export function glossarize(root) {
  if (!root) return;
  root.querySelectorAll(SEL).forEach((el) => {
    if (el.dataset.gl) return;
    el.dataset.gl = '1';
    const lang = (el.closest('[lang]') || document.documentElement).lang === 'en' ? 'en' : 'ko', { by, re } = T[lang], seen = new Set();
    const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: (n) => (n.parentElement.closest('button, a, .gl') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
    const nodes = []; for (let n = walk.nextNode(); n; n = walk.nextNode()) nodes.push(n);
    nodes.forEach((n) => {
      const s = n.nodeValue; let last = 0, out = null; re.lastIndex = 0;
      for (let m = re.exec(s); m; m = re.exec(s)) {
        const w = m[1] || m[2], i = by.get(w);
        if (i == null || seen.has(i) || (i === 1 && seen.has(0))) continue;   // ‘현물 ETF’를 풀었으면 같은 칸의 ‘ETF’는 건너뛴다
        seen.add(i); out = out || document.createDocumentFragment();
        out.append(s.slice(last, m.index));
        const b = document.createElement('button'); b.type = 'button'; b.className = 'gl'; b.dataset.g = i; b.dataset.gll = lang; b.setAttribute('aria-expanded', 'false'); b.textContent = w;
        out.append(b); last = m.index + w.length;
      }
      if (out) { out.append(s.slice(last)); n.replaceWith(out); }
    });
  });
  setup();
}
// 풀이 창 하나(문서에 하나만). 모바일: 누르면 열고 다시 누르거나 바깥을 누르면 닫는다. PC: 마우스를 올리면 열고 떼면 닫는다. 키보드: 초점 · Esc
let pop = null, cur = null, ready = false, dp = null;
const defs = () => (dp = dp || import('./gl-d.js' + new URL(import.meta.url).search).then((m) => m.D, () => { dp = null; return []; }));
const hover = () => matchMedia('(hover: hover) and (pointer: fine)').matches;
function show(b) {
  const g = G[+b.dataset.g]; if (!g) return;
  if (cur && cur !== b) cur.setAttribute('aria-expanded', 'false');
  cur = b; b.setAttribute('aria-expanded', 'true');
  defs().then((D) => { if (cur === b && D[+b.dataset.g]) place(b, g, D[+b.dataset.g]); });   // 풀이 문장을 받는 사이 닫혔거나 다른 말로 옮겼으면 그리지 않는다
}
function place(b, g, d) {
  if (!pop) { pop = document.createElement('div'); pop.className = 'glpop'; pop.id = 'glpop'; pop.setAttribute('role', 'tooltip'); document.body.appendChild(pop); }
  b.setAttribute('aria-describedby', 'glpop');
  const en = b.dataset.gll === 'en', title = en ? g[1][0] : g[0][0];
  pop.innerHTML = '<b></b><span></span>'; pop.firstChild.textContent = title; pop.lastChild.textContent = en ? d[1] : d[0];
  pop.hidden = false;
  // 시안 A(docs/relay/mockups/gl2): 내용만큼만 넓은 짙은 말풍선. 말 바로 아래, 말 시작점보다 조금 왼쪽에서 시작, 화살표는 말 가운데. 아래 탭 막대에 가리면 위로
  pop.style.left = '0px'; pop.style.top = '0px';
  const r = b.getBoundingClientRect(), w = pop.offsetWidth, t = document.querySelector('.tabs');
  const floor = t && t.offsetHeight ? Math.min(innerHeight, t.getBoundingClientRect().top) : innerHeight;
  const left = Math.max(16, Math.min(r.left - 12, innerWidth - w - 16));
  const below = r.bottom + 9 + pop.offsetHeight + 8 < floor;
  pop.style.left = left + 'px'; pop.style.top = (below ? r.bottom + 9 : Math.max(8, r.top - pop.offsetHeight - 9)) + 'px';
  pop.style.setProperty('--ax', Math.max(12, Math.min(w - 12, r.left + r.width / 2 - left)) + 'px');
  pop.classList.toggle('dk', !!b.closest('.bf-rg'));
  pop.classList.toggle('up', !below);
}
function hide() { if (pop) pop.hidden = true; if (cur) { cur.setAttribute('aria-expanded', 'false'); cur.removeAttribute('aria-describedby'); } cur = null; }
function setup() {
  if (ready) return; ready = true;
  document.addEventListener('click', (e) => {
    const b = e.target.closest('.gl');
    if (b) { e.preventDefault(); if (cur === b && !hover()) hide(); else show(b); return; }
    if (!e.target.closest('.glpop')) hide();
  });
  document.addEventListener('mouseover', (e) => { const b = e.target.closest('.gl'); if (b && hover()) show(b); });
  document.addEventListener('mouseout', (e) => { const b = e.target.closest('.gl'); if (b && hover() && !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('.gl') === b)) hide(); });
  document.addEventListener('focusin', (e) => { const b = e.target.closest && e.target.closest('.gl'); if (b && e.target.matches(':focus-visible')) show(b); });
  document.addEventListener('focusout', (e) => { if (e.target.closest && e.target.closest('.gl') === cur) hide(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && cur) { const b = cur; hide(); b.focus(); } });
  addEventListener('scroll', () => { if (cur) hide(); }, { passive: true });
  addEventListener('resize', () => { if (cur) hide(); });
}
