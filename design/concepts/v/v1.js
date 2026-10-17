// V1 · 개기일식 — 실제 일식 순서를 그대로: 흰 해가 뜨고 → 달이 왼쪽 아래에서 덮으며 해가 초승달로 줄고 → 마지막 빛이 '다이아몬드 반지'로 번쩍
// → 남색·보랏빛 코로나가 피어오르고 → 해의 테두리만 남아 고리가 되고 → 빛이 달 표면을 오른쪽 위부터 쓸어 원반이 밝아진다. 참고: 개기일식 사진 순서, Raycast 첫 화면의 빛+입자감(그레인), 21st.dev 다이아몬드 반지.
import { engine, wrap, EASE, reduce, fine } from './vk.js?v=152829';
const FRAG = `
uniform float uSun, uLimb, uBead, uCor, uFace; uniform vec2 uMoon, uPt;
void main() {
  vec2 p = markP(); float px = 100. / uS;
  vec2 B = D0 + uMoon; float rA = length(p - A0);
  float dSun = mix(rA - 31., abs(rA - 31.) - 1.6, uLimb);            // 해: 꽉 찬 원 → 테두리 띠
  float dMoon = length(p - B) - 34.;
  float sun = fill(dSun, px) * clamp(.5 + dMoon / px, 0., 1.) * uSun;
  // 하늘: 아주 어두운 남색, 심볼 뒤가 살짝 밝다
  vec2 f = gl_FragCoord.xy / uRes; vec3 col = NIGHT + vec3(.01, .014, .03) * exp(-length(p - D0) * .012);
  // 해 빛 번짐(달 밖에서만)
  float vis = smoothstep(-1.5, 3., dMoon);
  float inA = 1. - smoothstep(30., 31.5, rA);                        // 해 안쪽은 테두리만 남을 때 같이 꺼진다
  col += vec3(1., .86, .7) * .5 * exp(-max(rA - 31., 0.) * .11) * vis * uSun * (1. - .65 * uLimb) * (1. - inA * uLimb);
  // 코로나: 달 가장자리에서 뻗는 결(각도 방향 잡음)
  vec2 q = p - B; float r = length(q), an = atan(q.y, q.x) + uPt.x * .06;
  float st = fbm(vec2(an * 2.2 + 3., r * .025 - uTime * .04)) * fbm(vec2(an * 6.0, uTime * .03));
  float cor = exp(-max(r - 34., 0.) * mix(.09, .045, st)) * smoothstep(33.6, 35., r) * (.35 + 2.2 * st);
  col += mix(vec3(.42, .38, 1.), vec3(.85, .88, 1.), exp(-max(r - 34., 0.) * .25)) * cor * uCor;
  // 다이아몬드 반지: 고리 가운데(오른쪽 위)에서 한 번 번쩍, 가로·세로 빛살
  vec2 db = p - vec2(74.9, 25.1); vec2 dr = mat2(.707, -.707, .707, .707) * db;
  float bead = exp(-dot(db, db) * .06) * 2.2 + exp(-abs(dr.y) * 1.1 - abs(dr.x) * .045) * .9 + exp(-abs(dr.x) * 1.1 - abs(dr.y) * .045) * .6 + exp(-length(db) * .05) * .35;
  col += vec3(1., .96, .9) * bead * uBead;
  // 달 몸체(하늘보다 더 검다) → 빛이 쓸고 지나가며 원반이 밝아진다
  // 다 밝아지면 달 몸체는 하늘과 같은 색이 되어, 남는 건 원반·틈·고리(심볼 그대로)
  vec3 sky = NIGHT + vec3(.01, .014, .03) * exp(-length(p - D0) * .012);
  float moon = fill(dMoon, px); col = mix(col, mix(vec3(.004, .006, .011), sky, uFace), moon);
  float w = dot(p - D0, vec2(.7071, -.7071)), t = 30. - uFace * 68.;
  float face = fill(sdDisc(p), px) * smoothstep(t - 7., t, w);
  vec3 LIGHT = vec3(2.4, 2.35, 2.25);
  col = mix(col, LIGHT * (1. + .3 * smoothstep(t, t + 9., w) * (1. - uFace)), face);
  col = mix(col, LIGHT, sun);
  gl_FragColor = vec4(finish(col, p, px), 1.);
}`;
const E = engine({ frag: FRAG, U: { uSun: 0, uLimb: 0, uBead: 0, uCor: 0, uFace: 0, uMoon: [-50, 50], uPt: [0, 0] } });
const S = E.S, M = { x: -50, y: 50 };
const tl = gsap.timeline({ delay: 0.25, onUpdate: () => { S.uMoon = [M.x, M.y]; } });
tl.to(S, { uSun: 1, duration: 1.0, ease: EASE.out }, 0)
  .to(M, { x: 0, y: 0, duration: 2.1, ease: EASE.inOut }, 0.45)
  .to(S, { uLimb: 1, duration: 0.7, ease: EASE.inOut }, 2.2)
  .to(S, { uBead: 1, duration: 0.16, ease: EASE.out }, 2.42).to(S, { uBead: 0, duration: 1.2, ease: EASE.out }, 2.58)
  .to(S, { uCor: 1, duration: 0.6, ease: EASE.out }, 2.45).to(S, { uCor: 0.0, duration: 1.6, ease: EASE.inOut }, 3.1)
  .to(S, { uFace: 1, duration: 1.0, ease: EASE.inOut }, 3.0);
wrap(E, tl, { reframeAt: 3.7 });
if (fine) { const P = { x: 0, y: 0 }; addEventListener('pointermove', (e) => { P.x = e.clientX / innerWidth * 2 - 1; P.y = e.clientY / innerHeight * 2 - 1; }, { passive: true });
  E.tick(() => { S.uPt = [S.uPt[0] + (P.x - S.uPt[0]) * 0.04, S.uPt[1] + (P.y - S.uPt[1]) * 0.04]; }); }
