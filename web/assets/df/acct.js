// 회원 화면(2026-10-28): 로그인 · 이메일 회원가입 · 비밀번호 찾기 · 계정 메뉴 · 내 계정(/account/). data.js 가 누를 때 · 로그인 표시가 있을 때 불러온다(head).
// 모양은 운영자가 10-23에 킵한 시안(docs/relay/mockups/auth) — 이번엔 이메일만(카카오 · 구글 · Apple 은 앱 등록 뒤).
// 서버: api.delfona.com/auth/*(worker/src/auth.js). 쿠키는 HttpOnly 라 이 코드는 로그인 여부를 서버 답으로만 안다.
const API = 'https://api.delfona.com', KEY = 'df-acct';
const SITEKEY = '';   // Turnstile 공개 키(운영자가 만들어 알려 줌). 비어 있으면 메일 보내기는 서버가 503 으로 막는다
const ko = () => document.documentElement.lang === 'ko';
const T = (k, e) => (ko() ? k : e);
const esc = DFD.esc;
const ICON = {
  logo: '<svg class="au-logo" viewBox="0 0 100 100" fill="currentColor" aria-hidden="true"><circle cx="46" cy="54" r="30"/><path d="M75.88 70.22 A32.6 32.6 0 1 0 29.78 24.12 A34 34 0 0 1 40.31 20.48 A29.4 29.4 0 0 1 79.52 59.69 A34 34 0 0 1 75.88 70.22 Z"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c1.2-3.6 4.1-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/></svg>',
  mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M4 7l8 6 8-6"/></svg>',
  out: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l5-5-5-5M15 12H4"/></svg>',
};

// ---------- 머리글(로그인 표시는 이 기기의 힌트 → 서버 /auth/me 로 한 번 확인) ----------
const hint = () => { try { const h = JSON.parse(localStorage.getItem(KEY) || 'null'); return h && typeof h.e === 'string' ? h : null; } catch (e) { return null; } };
function paint() {
  const box = document.querySelector('.hd .acct'); if (!box) return;
  const h = hint();
  document.documentElement.classList.toggle('acct-on', !!h);
  if (h) box.innerHTML = `<button type="button" class="av" data-acct="menu" aria-haspopup="menu" aria-label="${T('내 계정', 'Account')}">${esc(h.e.charAt(0).toUpperCase())}</button>`;
  else if (!box.querySelector('.acct-in')) box.innerHTML = `<button type="button" class="acct-in" data-acct="login">${T('로그인', 'Sign in')}</button><button type="button" class="acct-ic" data-acct="login" aria-label="${T('로그인', 'Sign in')}">${ICON.user}</button>`;
}
function set(user) { try { if (user) localStorage.setItem(KEY, JSON.stringify({ e: user.email })); else localStorage.removeItem(KEY); } catch (e) { /* 저장 못 하는 브라우저 */ } paint(); }
let checked = null;
export function head() {
  paint();
  DFI.onLang(paint);
  checked = checked || fetch(API + '/auth/me', { credentials: 'include', cache: 'no-store' })
    .then((r) => r.json().catch(() => ({})).then((j) => (r.status === 401 ? set(null) : r.ok ? set(j.user) : 0))).catch(() => {});   // 본문은 늘 읽는다(안 읽으면 요청이 끝나지 않은 채 남는다)
  return checked;
}

// 서버 오류 코드 → 사람이 읽는 말
function say(j, status) {
  const e = j && j.error;
  if (e === 'code_wrong') return T(`인증번호가 맞지 않아요. ${j.left}번 더 넣을 수 있어요.`, `That code is not right. ${j.left} tries left.`);
  if (e === 'wait') return T(`${j.retry}초 뒤에 다시 보낼 수 있어요.`, `You can resend in ${j.retry}s.`);
  return ({
    email: T('이메일 주소를 확인해 주세요.', 'Check the email address.'),
    exists: T('이미 가입된 이메일이에요. 로그인하거나 비밀번호를 찾아 주세요.', 'This email is already registered. Sign in or reset your password.'),
    not_found: T('가입되지 않은 이메일이에요.', 'No account with this email.'),
    disposable: T('일회용 이메일로는 가입할 수 없어요.', 'Disposable email addresses are not allowed.'),
    bot: T('자동 확인에 실패했어요. 잠시 뒤 다시 시도해 주세요.', 'Automatic check failed. Please try again shortly.'),
    too_many: T('시도가 너무 많아요. 잠시 뒤 다시 해 주세요.', 'Too many attempts. Please try again later.'),
    code_expired: T('인증번호 시간이 지났어요. 새 번호를 받아 주세요.', 'The code expired. Get a new one.'),
    code_locked: T('5번 틀려서 이 번호는 쓸 수 없어요. 새 번호를 받아 주세요.', 'Too many wrong tries. Get a new code.'),
    password: T('비밀번호는 영문과 숫자를 섞어 8자 이상이에요.', 'Use 8+ characters with letters and numbers.'),
    agree: T('필수 항목에 동의해 주세요.', 'Please accept the required items.'),
    login: T('이메일 또는 비밀번호가 맞지 않아요.', 'Email or password is incorrect.'),
    mail: T('메일을 보내지 못했어요. 잠시 뒤 다시 해 주세요.', 'We could not send the email. Try again shortly.'),
    not_configured: T('지금은 메일 인증을 준비 중이에요.', 'Email verification is not ready yet.'),
    signed_out: T('로그인이 풀렸어요. 다시 로그인해 주세요.', 'You were signed out. Please sign in again.'),
  })[e] || (status === 0 ? T('연결이 불안정해요. 다시 시도해 주세요.', 'Connection problem. Please try again.') : T('잠시 문제가 생겼어요. 다시 시도해 주세요.', 'Something went wrong. Please try again.'));
}
async function api(path, body) {
  try {
    const r = await fetch(API + path, body === undefined ? { credentials: 'include', cache: 'no-store' }
      : { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lang: ko() ? 'ko' : 'en', ...body }) });
    return { status: r.status, ok: r.ok, j: await r.json().catch(() => ({})) };
  } catch (e) { return { status: 0, ok: false, j: {} }; }
}
const pwOk = (p) => p.length >= 8 && p.length <= 128 && /[a-zA-Z]/.test(p) && /[0-9]/.test(p);
const mailOk = (s) => /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(s.trim());

// Turnstile(보이지 않는 로봇 확인): 메일을 보낼 때만 불러온다
let tsLoad = null;
function human() {
  if (!SITEKEY) return Promise.resolve('');
  tsLoad = tsLoad || new Promise((ok, no) => { const s = document.createElement('script'); s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'; s.async = true; s.onload = ok; s.onerror = () => { tsLoad = null; no(); }; document.head.appendChild(s); });
  return tsLoad.then(() => new Promise((ok) => {
    const box = document.createElement('div'); box.className = 'au-ts'; document.body.appendChild(box);
    const done = (tok) => { box.remove(); ok(tok || ''); };
    window.turnstile.render(box, { sitekey: SITEKEY, size: 'invisible', callback: done, 'error-callback': () => done(''), 'expired-callback': () => done(''), language: ko() ? 'ko' : 'en' });
  })).catch(() => '');
}

// ---------- 창(모바일은 아래에서 올라오는 시트, PC 는 가운데) ----------
let cssP = null;
const css = () => (cssP = cssP || new Promise((ok) => { const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = new URL('acct.css', import.meta.url).href; l.onload = ok; l.onerror = ok; document.head.appendChild(l); }));
let cur = null;
function close() {
  if (!cur) return;
  const { root, back, keydown } = cur; cur = null;
  document.removeEventListener('keydown', keydown);
  root.classList.add('out');
  setTimeout(() => root.remove(), matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 180);
  document.documentElement.classList.remove('au-lock');
  if (back && back.isConnected) back.focus();
}
async function sheet(html, label) {
  await css();
  const back = cur ? cur.back : document.activeElement;
  if (cur) { cur.root.remove(); document.removeEventListener('keydown', cur.keydown); cur = null; }
  const root = document.createElement('div'); root.className = 'au';
  root.innerHTML = '<div class="au-bg" data-x></div><div class="au-in" role="dialog" aria-modal="true" aria-label="' + esc(label) + '"><span class="au-grab" aria-hidden="true"></span><button type="button" class="au-x" data-x aria-label="' + T('닫기', 'Close') + '">×</button>' + html + '</div>';
  document.body.appendChild(root);
  document.documentElement.classList.add('au-lock');
  const keydown = (e) => {
    if (e.key === 'Escape') close();
    if (e.key === 'Tab') {   // 창 안에서만 돈다
      const f = [...root.querySelectorAll('button, input, a[href], [tabindex]:not([tabindex="-1"])')].filter((x) => !x.disabled && x.offsetParent !== null);
      if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f.at(-1).focus(); } else if (!e.shiftKey && document.activeElement === f.at(-1)) { e.preventDefault(); f[0].focus(); }
    }
  };
  document.addEventListener('keydown', keydown);
  root.addEventListener('click', (e) => { if (e.target.closest('[data-x]')) close(); });
  cur = { root, back, keydown };
  const first = root.querySelector('input:not([type=checkbox]), .mbtn'); if (first) first.focus({ preventScroll: true });
  return root.querySelector('.au-in');
}
const field = (name, type, ph, extra = '') => `<input name="${name}" type="${type}" placeholder="${esc(ph)}" aria-label="${esc(ph)}" ${extra}>`;
const msg = (el, text, good) => { el.textContent = text || ''; el.className = 'au-msg' + (good ? ' ok' : '') + (text ? ' on' : ''); };
function busy(btn, on) { btn.disabled = on; btn.classList.toggle('busy', on); }
function toast(text) {
  css().then(() => { const t = document.createElement('div'); t.className = 'au-toast'; t.setAttribute('role', 'status'); t.textContent = text; document.body.appendChild(t); setTimeout(() => t.classList.add('out'), 2600); setTimeout(() => t.remove(), 3000); });
}
const signedIn = (user, text) => { set(user); close(); toast(text); document.dispatchEvent(new CustomEvent('df-auth', { detail: user })); };

// ---------- 로그인 ----------
async function login(prefill = '') {
  const box = await sheet(ICON.logo + `<h2>${T('Delfona 로그인', 'Sign in to Delfona')}</h2><p class="sub">${T('관심 자산과 저장한 이야기를 어느 기기에서나 그대로.', 'Your watchlist and saved stories on every device.')}</p>
<form novalidate>${field('email', 'email', T('이메일 주소', 'Email address'), 'autocomplete="username" inputmode="email"')}${field('password', 'password', T('비밀번호', 'Password'), 'autocomplete="current-password"')}
<label class="keep"><input type="checkbox" name="keep" checked><span class="ck">${ICON.check}</span>${T('로그인 상태 유지', 'Keep me signed in')}</label>
<p class="au-msg" aria-live="polite"></p><button class="mbtn">${T('로그인', 'Sign in')}</button></form>
<p class="links"><button type="button" data-go="reset">${T('비밀번호 찾기', 'Forgot password?')}</button><span></span><button type="button" class="p" data-go="signup">${T('이메일로 회원가입', 'Sign up with email')}</button></p>`, T('로그인', 'Sign in'));
  const f = box.querySelector('form'), m = box.querySelector('.au-msg'), btn = f.querySelector('.mbtn');
  f.email.value = prefill; if (prefill) f.password.focus();
  box.querySelector('[data-go=reset]').onclick = () => reset(f.email.value);
  box.querySelector('[data-go=signup]').onclick = () => signup(f.email.value);
  f.onsubmit = async (e) => {
    e.preventDefault();
    if (!mailOk(f.email.value)) return msg(m, say({ error: 'email' }));
    if (!f.password.value) return msg(m, T('비밀번호를 넣어 주세요.', 'Enter your password.'));
    busy(btn, true);
    const r = await api('/auth/login', { email: f.email.value, password: f.password.value, keep: f.keep.checked });
    busy(btn, false);
    if (r.ok) signedIn(r.j.user, T('로그인했어요', 'Signed in')); else { msg(m, say(r.j, r.status)); f.password.select(); }
  };
}

// ---------- 인증번호 받기 + 확인(가입 · 비밀번호 찾기 공통) ----------
function codeFlow(box, purpose, onVerified) {
  const f = box.querySelector('form'), m = box.querySelector('.au-msg'), send = box.querySelector('.sm'), codeRow = box.querySelector('.code'), tm = box.querySelector('.tm'), okLine = box.querySelector('.cok');
  let timer = 0, gapT = 0, verified = false;
  const stop = () => { clearInterval(timer); clearInterval(gapT); };
  const left = (until, el, done) => { const tick = () => { const s = Math.max(0, Math.round((until - Date.now()) / 1000)); el(s); if (!s) done(); }; tick(); return setInterval(tick, 500); };
  send.onclick = async () => {
    if (!mailOk(f.email.value)) return msg(m, say({ error: 'email' }));
    busy(send, true); msg(m, '');
    const ts = await human();
    const r = await api('/auth/code', { email: f.email.value, purpose, ts });
    if (!r.ok) { busy(send, false); return msg(m, say(r.j, r.status)); }
    verified = false; okLine.hidden = true; codeRow.hidden = false; f.code.value = ''; f.code.disabled = false; f.code.focus();
    stop();
    timer = left(Date.now() + r.j.ttl * 1000, (s) => { tm.textContent = Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }, () => { clearInterval(timer); if (!verified) msg(m, say({ error: 'code_expired' })); });
    gapT = left(Date.now() + r.j.gap * 1000, (s) => { send.textContent = s ? T(`재전송 ${s}초`, `Resend ${s}s`) : T('재전송', 'Resend'); }, () => { clearInterval(gapT); busy(send, false); });
    msg(m, T('인증번호를 보냈어요. 메일함을 확인해 주세요.', 'We sent a code. Check your inbox.'), true);
  };
  f.code.oninput = async () => {
    const v = f.code.value.replace(/\D/g, '').slice(0, 6); f.code.value = v;
    if (v.length < 6 || verified) return;
    f.code.disabled = true;
    const r = await api('/auth/code/check', { email: f.email.value, purpose, code: v });
    if (r.ok) { verified = true; stop(); tm.textContent = ''; okLine.hidden = false; msg(m, ''); onVerified(); }
    else { f.code.disabled = false; f.code.select(); msg(m, say(r.j, r.status)); }
  };
  f.email.oninput = () => { if (verified || !codeRow.hidden) { verified = false; okLine.hidden = true; codeRow.hidden = true; stop(); busy(send, false); send.textContent = T('인증번호 받기', 'Get code'); onVerified(false); } };
  return { verified: () => verified, stop };
}
const codeBlock = () => `<div class="ln">${field('email', 'email', T('이메일 주소', 'Email address'), 'autocomplete="email" inputmode="email"')}<button type="button" class="sm">${T('인증번호 받기', 'Get code')}</button></div>
<div class="ln code" hidden>${field('code', 'text', T('인증번호 6자리', '6-digit code'), 'inputmode="numeric" autocomplete="one-time-code" maxlength="6"')}<span class="tm" aria-live="off"></span></div>
<p class="pwok cok" hidden>${ICON.check}${T('인증됐어요', 'Verified')}</p>`;
const pwBlock = (ph) => `${field('password', 'password', ph, 'autocomplete="new-password"')}<p class="pwrule">${T('영문 · 숫자 섞어 8자 이상', 'Letters + numbers, 8+')}</p>${field('password2', 'password', T('비밀번호 확인', 'Confirm password'), 'autocomplete="new-password"')}`;
function pwWatch(f) {
  const rule = f.querySelector('.pwrule');
  const upd = () => {
    const p = f.password.value;
    rule.innerHTML = !p ? T('영문 · 숫자 섞어 8자 이상', 'Letters + numbers, 8+') : pwOk(p) ? ICON.check + T('사용할 수 있어요', 'Looks good') : T('영문 · 숫자 섞어 8자 이상이어야 해요', 'Needs 8+ characters with letters and numbers');
    rule.className = 'pwrule' + (p ? (pwOk(p) ? ' ok' : ' bad') : '');
  };
  f.password.addEventListener('input', upd);
  return () => pwOk(f.password.value) && f.password.value === f.password2.value;
}

// ---------- 이메일 회원가입 ----------
const DOCS = { terms: ['이용약관', 'Terms of service'], privacy: ['개인정보 수집 · 이용', 'Privacy policy'] };
async function signup(prefill = '') {
  const row = (name, tag, ko_, en, view) => `<label><input type="checkbox" name="${name}"><span class="ck">${ICON.check}</span>${tag ? `<span class="tag${tag === 'o' ? ' opt' : ''}">${tag === 'o' ? T('선택', 'Optional') : T('필수', 'Required')}</span>` : ''}<span class="lb">${T(ko_, en)}</span>${view ? `<button type="button" class="vw" data-doc="${view}">${T('보기', 'View')}</button>` : ''}</label>`;
  const box = await sheet(`<h2>${T('이메일로 회원가입', 'Sign up with email')}</h2><p class="sub">${T('이메일로 받은 인증번호를 넣으면 바로 시작돼요.', 'Enter the code we email you and you are in.')}</p>
<form novalidate>${codeBlock()}${pwBlock(T('비밀번호', 'Password'))}
<div class="agree">${row('all', '', '모두 동의', 'Agree to all')}${row('age14', 'r', '만 14세 이상입니다', 'I am 14 or older')}${row('terms', 'r', '이용약관', 'Terms of service', 'terms')}${row('privacy', 'r', '개인정보 수집 · 이용', 'Privacy policy', 'privacy')}${row('marketing', 'o', '마케팅 정보 수신', 'Marketing emails')}</div>
<p class="au-msg" aria-live="polite"></p><button class="mbtn" disabled>${T('가입하기', 'Create account')}</button></form>
<p class="links"><button type="button" data-go="login">${T('이미 계정이 있어요 · 로그인', 'Have an account? Sign in')}</button></p>`, T('회원가입', 'Sign up'));
  const f = box.querySelector('form'), m = box.querySelector('.au-msg'), btn = f.querySelector('.mbtn');
  f.email.value = prefill;
  const pwGood = pwWatch(f);
  const req = ['age14', 'terms', 'privacy'], each = [...req, 'marketing'];
  const code = codeFlow(box, 'signup', () => ready());
  const ready = () => { btn.disabled = !(code.verified() && pwGood() && req.every((k) => f[k].checked)); };
  f.all.onchange = () => { each.forEach((k) => { f[k].checked = f.all.checked; }); ready(); };
  each.forEach((k) => { f[k].onchange = () => { f.all.checked = each.every((x) => f[x].checked); ready(); }; });
  f.password.addEventListener('input', ready); f.password2.addEventListener('input', ready);
  box.querySelectorAll('[data-doc]').forEach((b) => { b.onclick = (e) => { e.preventDefault(); doc(b.dataset.doc); }; });
  box.querySelector('[data-go=login]').onclick = () => { code.stop(); login(f.email.value); };
  f.onsubmit = async (e) => {
    e.preventDefault();
    if (f.password.value !== f.password2.value) return msg(m, T('비밀번호 확인이 달라요.', 'Passwords do not match.'));
    if (btn.disabled) return;
    busy(btn, true);
    const r = await api('/auth/signup', { email: f.email.value, code: f.code.value, password: f.password.value, keep: true,
      agree: { age14: f.age14.checked, terms: f.terms.checked, privacy: f.privacy.checked, marketing: f.marketing.checked } });
    busy(btn, false); ready();
    if (r.ok) { code.stop(); signedIn(r.j.user, T('가입을 환영해요!', 'Welcome to Delfona!')); } else msg(m, say(r.j, r.status));
  };
}

// ---------- 비밀번호 찾기 ----------
async function reset(prefill = '') {
  const box = await sheet(`<h2>${T('비밀번호 찾기', 'Reset password')}</h2><p class="sub">${T('가입한 이메일로 받은 인증번호를 넣고 새 비밀번호를 정해요.', 'Enter the code we email you, then choose a new password.')}</p>
<form novalidate>${codeBlock()}<div class="newpw" hidden>${pwBlock(T('새 비밀번호', 'New password'))}</div>
<p class="au-msg" aria-live="polite"></p><button class="mbtn" disabled>${T('비밀번호 바꾸기', 'Set new password')}</button></form>
<p class="links"><button type="button" data-go="login">${T('로그인으로 돌아가기', 'Back to sign in')}</button></p>`, T('비밀번호 찾기', 'Reset password'));
  const f = box.querySelector('form'), m = box.querySelector('.au-msg'), btn = f.querySelector('.mbtn'), np = box.querySelector('.newpw');
  f.email.value = prefill;
  const pwGood = pwWatch(f);
  const ready = () => { btn.disabled = !(code.verified() && pwGood()); };
  const code = codeFlow(box, 'reset', (on) => { np.hidden = on === false; if (on !== false) f.password.focus(); ready(); });
  f.password.addEventListener('input', ready); f.password2.addEventListener('input', ready);
  box.querySelector('[data-go=login]').onclick = () => { code.stop(); login(f.email.value); };
  f.onsubmit = async (e) => {
    e.preventDefault();
    if (f.password.value !== f.password2.value) return msg(m, T('비밀번호 확인이 달라요.', 'Passwords do not match.'));
    if (btn.disabled) return;
    busy(btn, true);
    const r = await api('/auth/reset', { email: f.email.value, code: f.code.value, password: f.password.value, keep: true });
    busy(btn, false); ready();
    if (r.ok) { code.stop(); signedIn(r.j.user, T('새 비밀번호로 바꿨어요. 다른 기기는 로그아웃됐어요.', 'Password changed. Other devices were signed out.')); } else msg(m, say(r.j, r.status));
  };
}

// ---------- 약관 보기(초안) ----------
// 가입 창 위에 한 겹 더 띄운다(가입 창에 넣던 값은 그대로)
function doc(kind) {
  const back = document.activeElement;
  const root = document.createElement('div'); root.className = 'au au-doc';
  root.innerHTML = `<div class="au-bg" data-x></div><div class="au-in" role="dialog" aria-modal="true" aria-label="${esc(T(...DOCS[kind]))}"><span class="au-grab" aria-hidden="true"></span><button type="button" class="au-x" data-x aria-label="${T('닫기', 'Close')}">×</button><h2>${T(...DOCS[kind])}</h2><div class="doc">${kind === 'terms' ? TERMS() : PRIVACY()}</div><button type="button" class="mbtn" data-x>${T('확인', 'OK')}</button></div>`;
  const shut = () => { document.removeEventListener('keydown', key, true); root.remove(); if (back && back.isConnected) back.focus(); };
  const key = (e) => { if (e.key === 'Escape') { e.stopImmediatePropagation(); shut(); } };
  root.addEventListener('click', (e) => { if (e.target.closest('[data-x]')) shut(); });
  document.addEventListener('keydown', key, true);
  document.body.appendChild(root);
  root.querySelector('.mbtn').focus({ preventScroll: true });
}
const TERMS = () => T(`<p class="draft">초안 — 정식 공개 전에 다듬습니다.</p>
<h3>1. 서비스</h3><p>Delfona 는 시장 소식과 소식 뒤 가격 움직임을 정리해 보여 주는 정보 서비스예요. 투자 조언이 아니며, 투자 판단과 결과는 이용자에게 있어요.</p>
<h3>2. 회원</h3><p>만 14세 이상 누구나 이메일로 가입할 수 있어요. 한 사람이 같은 메일함으로 여러 계정을 만들 수 없어요. 계정 정보는 본인이 안전하게 지켜 주세요.</p>
<h3>3. 금지</h3><p>자동 프로그램으로 대량 가입 · 수집하거나, 서비스를 방해하거나, 다른 사람인 척하는 행동은 할 수 없어요. 어기면 이용을 멈출 수 있어요.</p>
<h3>4. 변경 · 중단</h3><p>서비스 내용은 바뀌거나 멈출 수 있어요. 중요한 변경은 미리 알려 드려요.</p>
<h3>5. 탈퇴</h3><p>내 계정 화면에서 언제든 탈퇴할 수 있고, 탈퇴하면 계정 정보는 바로 지워져요.</p>`,
`<p class="draft">Draft — to be finalized before launch.</p><h3>Service</h3><p>Delfona summarizes market news and the price moves after it. It is information, not investment advice.</p>
<h3>Accounts</h3><p>Anyone 14 or older can sign up with an email. One account per mailbox. Keep your credentials safe.</p>
<h3>Not allowed</h3><p>Automated mass sign-ups or scraping, disrupting the service, or impersonation. We may suspend accounts that do this.</p>
<h3>Changes</h3><p>The service may change or stop; we announce important changes in advance.</p><h3>Leaving</h3><p>Delete your account anytime from the Account page; your account data is deleted right away.</p>`);
const PRIVACY = () => T(`<p class="draft">초안 — 정식 공개 전에 다듬습니다.</p>
<h3>모으는 것</h3><p>이메일 주소, 비밀번호(되돌릴 수 없는 형태로만 저장), 동의한 항목과 시각, 마케팅 수신 여부, 화면 언어.</p>
<h3>쓰는 곳</h3><p>로그인 · 계정 확인, 인증번호 · 보안 알림 메일, 마케팅 수신에 동의한 경우 새 기능 · 이벤트 안내.</p>
<h3>보관 기간</h3><p>탈퇴할 때까지. 탈퇴하면 바로 지워요. 인증번호는 최대 1시간, 로그인 기록은 만료되면 지워요.</p>
<h3>맡기는 곳</h3><p>메일 발송: Resend · 서버와 저장소: Cloudflare · 자동 가입 막기: Cloudflare Turnstile.</p>
<h3>하지 않는 것</h3><p>기기 추적, 광고용 정보 판매, 휴대폰 번호 수집은 하지 않아요. 방문 통계는 합계만 남기고 개인을 알아볼 수 있는 값은 저장하지 않아요.</p>`,
`<p class="draft">Draft — to be finalized before launch.</p><h3>What we collect</h3><p>Email, password (stored only as a one-way hash), what you agreed to and when, marketing preference, language.</p>
<h3>Why</h3><p>Sign-in, verification and security emails, and product news if you opted in.</p><h3>How long</h3><p>Until you delete your account. Codes are kept at most an hour; expired sessions are deleted.</p>
<h3>Processors</h3><p>Email: Resend · Servers and storage: Cloudflare · Bot protection: Cloudflare Turnstile.</p><h3>What we do not do</h3><p>No device tracking, no selling data, no phone numbers. Visit stats are totals only.</p>`);

// ---------- 계정 메뉴(첫 글자를 누르면) ----------
async function menu(anchor) {
  await css();
  const old = document.querySelector('.amenu'); if (old) { old.remove(); return; }
  const h = hint() || { e: '' };
  const m = document.createElement('div'); m.className = 'amenu'; m.setAttribute('role', 'menu');
  m.innerHTML = `<div class="who"><span>${esc(h.e)}</span></div><a role="menuitem" href="${window.DF_ROOT || '/'}account/">${ICON.user}${T('내 계정', 'Account')}<span class="plan">${T('무료', 'Free')}</span></a><div class="sep"></div><button type="button" role="menuitem" data-out>${ICON.out}${T('로그아웃', 'Sign out')}</button>`;
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect();
  m.style.top = Math.round(r.bottom + 8) + 'px';
  m.style.right = Math.max(8, Math.round(innerWidth - r.right)) + 'px';
  const off = (e) => { if (!m.contains(e.target) && e.target !== anchor) { m.remove(); document.removeEventListener('click', off, true); document.removeEventListener('keydown', esc_); } };
  const esc_ = (e) => { if (e.key === 'Escape') { m.remove(); anchor.focus(); document.removeEventListener('click', off, true); document.removeEventListener('keydown', esc_); } };
  setTimeout(() => { document.addEventListener('click', off, true); document.addEventListener('keydown', esc_); });
  m.querySelector('a').focus();
  m.querySelector('[data-out]').onclick = async () => { m.remove(); await api('/auth/logout', {}); set(null); toast(T('로그아웃했어요', 'Signed out')); document.dispatchEvent(new CustomEvent('df-auth', { detail: null })); };
}

export function open(mode, anchor) {
  // 머리글 단추는 각 화면 HTML 에 있고(data.js 는 누를 때 이 파일만 받는다), 로그인 쿠키는 delfona.com 용 — 옛 주소(github.io)에서 누르면 새 주소로 보낸다
  if (/github\.io$/.test(location.hostname)) { location.href = 'https://delfona.com' + location.pathname.replace(/^\/signal-desk/, '') + location.search; return; }
  if (mode === 'menu') return menu(anchor);
  if (mode === 'signup') return signup();
  if (mode === 'reset') return reset();
  return login();
}

// ---------- 내 계정(/account/) ----------
const day = (t) => { const d = new Date(t * 1000); return ko() ? `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}` : d.toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' }); };
export async function account(main) {
  await css();
  let user = null;
  const draw = () => {
    if (!user) {
      main.innerHTML = `<div class="acc"><h1>${T('내 계정', 'Account')}</h1><div class="card empty"><p>${T('로그인하면 계정 정보를 볼 수 있어요.', 'Sign in to see your account.')}</p><button type="button" class="mbtn" data-acct="login">${T('로그인', 'Sign in')}</button></div></div>`;
      return;
    }
    main.innerHTML = `<div class="acc"><h1>${T('내 계정', 'Account')}</h1>
<div class="card"><div class="me"><span class="av" aria-hidden="true">${esc(user.email.charAt(0).toUpperCase())}</span><div><b>${esc(user.email)}</b><span>${T(`${day(user.created)} 가입`, `Joined ${day(user.created)}`)}</span></div></div></div>
<div class="card"><h3>${T('로그인 방식', 'Sign-in method')}</h3><div class="row"><span class="lg">${ICON.mail}</span>${T('이메일 · 비밀번호', 'Email & password')}<button type="button" class="bt" data-do="pw">${T('비밀번호 변경', 'Change password')}</button></div></div>
<div class="card"><h3>${T('정보 수신', 'Email')}</h3><div class="row"><div>${T('마케팅 정보 수신', 'Marketing emails')}<small>${T('새 기능 · 이벤트 소식을 이메일로 받아요', 'New features and offers by email')}</small></div>
<button type="button" class="tg${user.marketing ? ' on' : ''}" role="switch" aria-checked="${user.marketing}" aria-label="${T('마케팅 정보 수신', 'Marketing emails')}" data-do="mk"></button></div>
<p class="cons">${user.marketing_at ? (user.marketing ? T(`${day(user.marketing_at)} 동의함`, `Agreed on ${day(user.marketing_at)}`) : T(`${day(user.marketing_at)} 거부함`, `Declined on ${day(user.marketing_at)}`)) : T('동의하지 않음', 'Not agreed')}</p></div>
<div class="card"><h3>${T('플랜', 'Plan')}</h3><div class="plan"><span class="pl">${T('무료', 'Free')}</span><span class="soon">${T('유료 플랜 준비 중', 'Pro coming soon')}</span></div></div>
<div class="lo"><button type="button" data-do="out">${T('로그아웃', 'Sign out')}</button><button type="button" data-do="all">${T('모든 기기에서 로그아웃', 'Sign out everywhere')}</button><button type="button" class="del" data-do="del">${T('회원 탈퇴', 'Delete account')}</button></div></div>`;
  };
  const load = async () => {
    const r = await api('/auth/me');
    user = r.ok ? r.j.user : null;
    if (r.status === 401) set(null); else if (user) set(user);
    draw();
  };
  main.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-do]'); if (!b || !user) return;
    const k = b.dataset.do;
    if (k === 'mk') {
      b.disabled = true;
      const r = await api('/auth/marketing', { on: !user.marketing });
      if (r.ok) { user = r.j.user; draw(); toast(user.marketing ? T('마케팅 정보 수신에 동의했어요', 'Subscribed to marketing emails') : T('마케팅 정보 수신을 껐어요', 'Unsubscribed from marketing emails')); } else { b.disabled = false; toast(say(r.j, r.status)); }
    }
    if (k === 'out' || k === 'all') {
      await api('/auth/logout', k === 'all' ? { all: true } : {}); set(null); user = null; draw();
      toast(k === 'all' ? T('모든 기기에서 로그아웃했어요', 'Signed out everywhere') : T('로그아웃했어요', 'Signed out'));
    }
    if (k === 'pw') pwChange();
    if (k === 'del') remove();
  });
  document.addEventListener('df-auth', () => load());
  DFI.onLang(() => draw());
  draw();   // 로그인 표시가 있으면 서버 답을 기다리는 동안 빈 칸 대신 안내
  if (hint()) main.innerHTML = `<div class="acc"><h1>${T('내 계정', 'Account')}</h1><div class="card empty"><p>${T('불러오는 중…', 'Loading…')}</p></div></div>`;
  await load();

  async function pwChange() {
    const box = await sheet(`<h2>${T('비밀번호 변경', 'Change password')}</h2><p class="sub">${T('바꾸면 이 기기만 로그인 상태로 남아요.', 'Other devices will be signed out.')}</p>
<form novalidate>${field('current', 'password', T('지금 비밀번호', 'Current password'), 'autocomplete="current-password"')}${pwBlock(T('새 비밀번호', 'New password'))}<p class="au-msg" aria-live="polite"></p><button class="mbtn">${T('바꾸기', 'Change')}</button></form>`, T('비밀번호 변경', 'Change password'));
    const f = box.querySelector('form'), m = box.querySelector('.au-msg'), btn = f.querySelector('.mbtn');
    const good = pwWatch(f);
    f.onsubmit = async (e) => {
      e.preventDefault();
      if (!good()) return msg(m, f.password.value !== f.password2.value ? T('비밀번호 확인이 달라요.', 'Passwords do not match.') : say({ error: 'password' }));
      busy(btn, true);
      const r = await api('/auth/password', { current: f.current.value, password: f.password.value });
      busy(btn, false);
      if (r.ok) { close(); toast(T('비밀번호를 바꿨어요. 다른 기기는 로그아웃됐어요.', 'Password changed. Other devices were signed out.')); }
      else msg(m, r.j.error === 'login' ? T('지금 비밀번호가 맞지 않아요.', 'Current password is incorrect.') : say(r.j, r.status));
    };
  }
  async function remove() {
    const box = await sheet(`<h2>${T('회원 탈퇴', 'Delete account')}</h2><p class="sub">${T('계정과 동의 기록이 바로 지워지고 되돌릴 수 없어요. 같은 이메일로 다시 가입할 수는 있어요.', 'Your account is deleted right away and cannot be restored. You can sign up again with the same email.')}</p>
<form novalidate>${field('password', 'password', T('비밀번호', 'Password'), 'autocomplete="current-password"')}<p class="au-msg" aria-live="polite"></p><button class="mbtn danger">${T('탈퇴하기', 'Delete my account')}</button></form>`, T('회원 탈퇴', 'Delete account'));
    const f = box.querySelector('form'), m = box.querySelector('.au-msg'), btn = f.querySelector('.mbtn');
    f.onsubmit = async (e) => {
      e.preventDefault();
      busy(btn, true);
      const r = await api('/auth/delete', { password: f.password.value });
      busy(btn, false);
      if (r.ok) { close(); set(null); user = null; draw(); toast(T('탈퇴했어요. 그동안 고마웠어요.', 'Your account was deleted.')); }
      else msg(m, r.j.error === 'login' ? T('비밀번호가 맞지 않아요.', 'Password is incorrect.') : say(r.j, r.status));
    };
  }
}
