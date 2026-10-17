// V3 · 해독 — 레이더 빛줄기가 원반 중심을 돌며 지나간 자리만 심볼을 '칠한다'(지나간 뒤 잠깐 뜨겁게 남는 빛 + 그레인 결).
// 한 바퀴 반 돌고 스프링으로 멈추면 빛 한 점이 고리를 끝에서 끝까지 달린다. 그 사이 아래 글자가 기호 → DELFONA, 숫자 → 실제 24시간 판정 수로 풀린다.
// 참고: Raycast 첫 화면의 그레인 빛띠, unseen.co·Lusion 의 글자 풀림·로딩 숫자, 레이더/오실로스코프.
import { engine, wrap, EASE, spring, reduce, mobile } from './vk.js?v=152829';
const FRAG = `
uniform float uA, uA0, uBeam, uPulse, uPulseI;
const float TAU = 6.2831853;
void main() {
  vec2 p = markP(); float px = 100. / uS;
  vec2 q = p - D0; float r = length(q), an = atan(q.y, q.x);
  float da = mod(an - uA0, TAU), swept = uA - uA0;                 // 이 각도까지 빛줄기가 지나갔나
  float painted = clamp((swept - da) / .05, 0., 1.) + step(TAU, swept);
  float behind = mod(uA - an, TAU);                                  // 빛줄기 뒤로 얼마나 떨어졌나
  float g = hash(gl_FragCoord.xy * .5 + floor(uTime * 24.));
  float beam = exp(-behind * 3.2) * exp(-r * .012) * uBeam * (.55 + .9 * g) + exp(-behind * 60.) * exp(-r * .006) * uBeam * .8;
  vec3 col = NIGHT + vec3(.25, .24, .75) * beam * .55 + vec3(.012, .016, .035) * exp(-r * .015);
  // 동심 눈금(아주 옅게)
  float ring = abs(fract(r / 12.) - .5) * 12.; col += vec3(.06, .07, .14) * (1. - smoothstep(0., px * 1.2, ring)) * exp(-r * .02) * uBeam * .5;
  float m = max(fill(sdDisc(p), px), fill(sdRing(p), px)) * min(painted, 1.);
  float hot = exp(-behind * 2.4) * uBeam;                            // 막 칠해진 곳은 잠깐 더 밝다
  vec3 LIGHT = vec3(2.4, 2.35, 2.25) + vec3(.3, .2, 1.4) * hot;
  // 고리 위를 달리는 빛 한 점(고리 각도 기준)
  vec2 qa = p - A0; float aa = atan(qa.y, qa.x), a1 = -2.36, a2 = .79;
  float pa = mix(a1, a2, uPulse), dpa = abs(aa - pa) * 31.;
  float pulse = exp(-dpa * dpa * .02) * exp(-max(abs(length(qa) - 31.) - 1.6, 0.) * .5) * uPulseI;
  col += vec3(.6, .6, 1.) * pulse * .9;
  col = mix(col, LIGHT, m); col += vec3(1.) * pulse * fill(sdRing(p), px) * 1.2;
  gl_FragColor = vec4(finish(col, p, px), 1.);
}`;
const A0 = Math.atan2(-1, -0.4); // 왼쪽 위에서 시작
const E = engine({ frag: FRAG, U: { uA: A0, uA0: A0, uBeam: 0, uPulse: 0, uPulseI: 0 } });
const S = E.S;
// 아래 글자(가운데일 때만 보이고, 비켜나면 사라진다)
const box = document.createElement('div'); box.className = 'dec'; box.setAttribute('aria-hidden', 'true'); box.innerHTML = '<b class="dw"></b><span class="dn"></span>'; E.hero.appendChild(box);
const GL = 'ΔΣ01/<>=+-#%*', word = 'DELFONA';
function decode(el, target, dur = 1.1) { const n = target.length, st = performance.now();
  return new Promise((res) => { const f = (now) => { const k = (now - st) / 1000 / dur; let s = '';
    for (let i = 0; i < n; i++) { const lock = k > 0.25 + (i / n) * 0.75; s += lock || target[i] === ' ' ? target[i] : GL[Math.floor(Math.random() * GL.length)]; }
    el.textContent = s; if (k < 1) requestAnimationFrame(f); else { el.textContent = target; res(); } }; requestAnimationFrame(f); }); }
let counts = '— · — · —';
DFD.flash().then((d) => { const c = DFD.day24(d.items); counts = `${c.u + c.d + (c.n || 0)} · ${c.u}▲ · ${c.d}▼`; }).catch(() => {});
const tl = gsap.timeline({ delay: 0.25 });
const TARGET = -Math.PI / 4, end = A0 + Math.PI * 2 + (((TARGET - A0) % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2); // 한 바퀴 넘게 돌아 고리(오른쪽 위)를 가리키며 멈춤
tl.to(S, { uBeam: 1, duration: 0.5, ease: EASE.out }, 0)
  .to(S, { uA: end, duration: 2.5, ease: EASE.inOut }, 0)
  .add(() => decode(box.querySelector('.dw'), word, 1.3), 0.4)
  .add(() => decode(box.querySelector('.dn'), (DFI.lang() === 'ko' ? '24시간 판정 ' : '24H JUDGED ') + counts, 1.2), 1.2)
  .fromTo(box, { opacity: 0 }, { opacity: 1, duration: 0.4, ease: EASE.out }, 0.35)
  .to(S, { uBeam: 0, duration: 0.9, ease: EASE.out }, 2.2)
  .fromTo(S, { uPulse: 0, uPulseI: 0 }, { uPulse: 1, duration: 1.0, ease: EASE.inOut }, 2.3)
  .to(S, { uPulseI: 1, duration: 0.2, ease: 'none' }, 2.3).to(S, { uPulseI: 0, duration: 0.3, ease: 'none' }, 3.0)
  .to(box, { opacity: 0, y: -10, duration: 0.4, ease: EASE.out }, 3.1);
wrap(E, tl, { reframeAt: 3.15 });
