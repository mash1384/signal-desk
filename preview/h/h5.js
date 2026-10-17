// H5 · Liquid ink — 화면 전체가 천천히 흐르는 액체(실크) 셰이더. 남색·인디고·청록이 섞여 흐르고, 마우스가 지나간 자리에 물결이 번진다.
// 오프닝: 흰 화면 가운데 한 점에서 잉크가 퍼지며 화면을 물들인다. 아래에는 실제 속보가 흐르는 띠(티커)가 지나간다.
import * as THREE from 'three';
import { renderer, loop, pointer, easePointer, revealCopy, reduce, mobile, data } from './kit.js';
const canvas = document.getElementById('gl'), r = renderer(canvas, { clear: 0xf7f9fc });
r.setPixelRatio(Math.min(devicePixelRatio || 1, mobile() ? 1 : 1.25));
const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(50, 1, 0.1, 10); cam.position.z = 1;
const U = { uT: { value: 0 }, uR: { value: new THREE.Vector2(1, 1) }, uM: { value: new THREE.Vector2(0.7, 0.5) }, uV: { value: 0 }, uIn: { value: reduce ? 1 : 0 }, uBal: { value: 0 }, uFull: { value: 0 }, uDark: { value: 0 }, uSw: { value: 0 }, uHole: { value: 0 } };
const q = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({ uniforms: U, depthTest: false, vertexShader: 'varying vec2 vU; void main(){ vU = uv; gl_Position = vec4(position.xy, 0., 1.); }',
  fragmentShader: `precision highp float; varying vec2 vU; uniform float uT, uV, uIn, uBal, uFull, uDark, uSw, uHole; uniform vec2 uR, uM;
  vec2 hash(vec2 p){ p = vec2(dot(p,vec2(127.1,311.7)), dot(p,vec2(269.5,183.3))); return -1.+2.*fract(sin(p)*43758.5453); }
  float noise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f*f*(3.-2.*f);
    return mix(mix(dot(hash(i),f), dot(hash(i+vec2(1,0)),f-vec2(1,0)),u.x), mix(dot(hash(i+vec2(0,1)),f-vec2(0,1)), dot(hash(i+vec2(1,1)),f-vec2(1,1)),u.x),u.y); }
  float fbm(vec2 p){ float s = 0., a = .5; for(int i=0;i<5;i++){ s += a*noise(p); p = p*2.02 + 17.; a *= .5; } return s; }
  void main(){ vec2 a = vec2(uR.x/uR.y, 1.), p = vU*a, m = uM*a; float t = uT*.06 + uSw*.9;
    vec2 cc = .5*a, pc = p - cc; float pr = length(pc), sa = uSw*2.2*exp(-pr*2.2); p = cc + mat2(cos(sa),-sin(sa),sin(sa),cos(sa))*pc;
    vec2 d = p - m; float md = length(d); p += d/(md+.001) * sin(md*28. - uT*3.) * .012 * exp(-md*4.) * (.4+uV);
    vec2 q = vec2(fbm(p*1.6 + t), fbm(p*1.6 - t + 4.)); vec2 r2 = vec2(fbm(p*1.6 + 2.*q + vec2(1.7,9.2) + t*1.3), fbm(p*1.6 + 2.*q + vec2(8.3,2.8) - t));
    float f = fbm(p*1.6 + 2.2*r2);
    vec3 c1 = vec3(.051,.145,.239), c2 = vec3(.325,.227,.992), c3 = vec3(.18,.85,.77), c4 = vec3(.94,.96,1.);
    float ff = f*1.8 + .1; vec3 col = mix(c4, c2, smoothstep(-.35, .3, ff)); col = mix(col, c1, smoothstep(.25, .75, length(q)*1.6)); col = mix(col, c3, smoothstep(.1, .6, r2.x*1.6) * (.55 + uBal*.3));
    float sheen = pow(max(0., fbm(p*3. + r2*1.5 + t*2.)), 2.) * 2.2; col += sheen * vec3(.85,.92,1.) * .45;
    col = mix(col, mix(c1*.55, col*.55, .45), uDark);
    vec3 bg = vec3(.969,.976,.988);
    float edge = smoothstep(0., 1., (uIn*1.8 - length((vU - vec2(.72,.5))*a)) * 2.2);
    float side = smoothstep(.32, .62, vU.x), wide = step(.5, uR.x/uR.y); float sm = mix(.08, 1., side) * wide + (1.-wide) * smoothstep(.45, .85, vU.y);
    col = mix(bg, col, mix(edge * sm, 1., uFull));
    float hr = uHole*1.18, hd = length((vU-.5)*a), hole = smoothstep(hr - .03, hr + .015, hd);
    col = mix(bg, col, hole); col += exp(-abs(hd - hr)*38.) * vec3(.55,.6,1.) * .55 * step(.001, uHole) * hole;
    gl_FragColor = vec4(col, 1.); }` }));
q.frustumCulled = false; scene.add(q);
let lastX = 0, lastY = 0;
loop(r, scene, cam, (t) => {
  U.uT.value = reduce ? 30 : t; easePointer(0.08);
  const mx = (pointer.x + 1) / 2, my = (pointer.y + 1) / 2; U.uM.value.set(mx, my);
  const v = Math.hypot(mx - lastX, my - lastY); U.uV.value += (Math.min(1, v * 40) - U.uV.value) * 0.08; lastX = mx; lastY = my;
  U.uR.value.set(canvas.clientWidth, canvas.clientHeight);
});
if (!reduce) gsap.to(U.uIn, { value: 1, duration: 2.6, ease: 'power2.inOut', delay: 0.2 });
revealCopy(1.1);
// 티커
data.flash.then((d) => { const c = DFD.day24(d.items); U.uBal.value = (c.u - c.d) / Math.max(1, c.u + c.d) * 4;
  const tk = document.getElementById('tk');
  const fill = () => { const xs = d.items.filter((it) => DFI.has(it) && it.v !== '중립').slice(0, 14);
    const row = xs.map((it) => `<span><b class="${DFD.vcls(it.v)}">${DFI.v(it.v)}</b>${DFD.esc(DFI.line(it))}</span>`).join('');
    tk.innerHTML = `<div class="tk-row">${row}${row}</div>`; };
  fill(); DFI.onLang(fill); gsap.to(tk, { opacity: 1, duration: 0.8, delay: 2.0 }); });

// ---------- 스크롤: 첫 화면을 고정한 채 잉크가 화면을 덮고 → 한 문장이 단어씩 켜지고 → 가운데 구멍으로 빠져나간다 ----------
gsap.registerPlugin(ScrollTrigger);
const hero = document.getElementById('hero'), st = document.getElementById('st'), sl = st.querySelector('.st-l'), sn = st.querySelector('.st-n');
const ST = { en: ['The world moves markets every minute.', 'Delfona tells you which way.'], ko: ['세상은 매 순간 시장을 움직여요.', 'Delfona는 그 방향을 알려 줘요.'] };
let words = [], wp = 0, C = null, np = 0;
const paint = () => { const n = words.length; words.forEach((w, i) => { w.style.opacity = 0.14 + 0.86 * Math.min(1, Math.max(0, wp * (n + 2) - i) / 2); }); };
const stats = () => { if (!C) return; const k = (v) => Math.round(v * np).toLocaleString();
  sn.innerHTML = DFI.lang() === 'ko' ? `지난 24시간 <b>${k(C.all)}</b>건 판정 · <b class="up">호재 ${k(C.u)}</b> · <b class="down">악재 ${k(C.d)}</b>`
    : `<b>${k(C.all)}</b> stories judged in 24h · <b class="up">${k(C.u)} positive</b> · <b class="down">${k(C.d)} negative</b>`; };
const fillSt = () => { const L = ST[DFI.lang()] || ST.en;
  sl.innerHTML = L.map((line, j) => `<span class="st-row${j ? ' em' : ''}">${line.split(' ').map((w) => `<span class="w">${w}</span>`).join(' ')}</span>`).join('');
  words = [...sl.querySelectorAll('.w')]; paint(); stats(); };
fillSt(); DFI.onLang(fillSt);
data.flash.then((d) => { C = DFD.day24(d.items); stats(); });
const tl = gsap.timeline({ scrollTrigger: { trigger: hero, start: 'top top', end: '+=260%', pin: true, scrub: 0.8, anticipatePin: 1 } });
tl.to('.copy', { y: -90, opacity: 0, filter: 'blur(10px)', duration: 0.2, ease: 'power2.in' }, 0)
  .to('#tk', { yPercent: 100, duration: 0.15, ease: 'power2.in' }, 0)
  .fromTo(hero, { '--wm': 1 }, { '--wm': 0, duration: 0.25 }, 0)
  .to(U.uFull, { value: 1, duration: 0.3, ease: 'power1.inOut' }, 0.02)
  .to(U.uDark, { value: 1, duration: 0.33, ease: 'power1.inOut' }, 0.1)
  .to(U.uSw, { value: 3, duration: 0.97, ease: 'none' }, 0)
  .fromTo(st, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.1 }, 0.3)
  .to({ v: 0 }, { v: 1, duration: 0.3, ease: 'none', onUpdate() { wp = this.targets()[0].v; paint(); } }, 0.32)
  .fromTo(sn, { opacity: 0 }, { opacity: 1, duration: 0.06 }, 0.56)
  .to({ v: 0 }, { v: 1, duration: 0.12, ease: 'power1.out', onUpdate() { np = this.targets()[0].v; stats(); } }, 0.56)
  .to(st, { opacity: 0, scale: 0.94, filter: 'blur(6px)', duration: 0.1, ease: 'power2.in' }, 0.74)
  .to(U.uHole, { value: 1, duration: 0.2, ease: 'power2.in' }, 0.78);
// 잉크가 어두워지면 머리말(로고·메뉴)을 흰색으로
gsap.ticker.add(() => document.body.classList.toggle('ink', U.uDark.value > 0.4 && U.uHole.value < 0.45));
