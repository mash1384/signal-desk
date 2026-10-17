// V2 · 림 라이트 — 심볼을 '물건'으로: 검은 유광 원반과 금속 고리. 처음엔 어둠 속에서 빛 하나가 뒤를 돌며 가장자리(림)와 고리의 반짝임만 보이다가
// 키 라이트가 켜지며 형태가 드러난다. 이후 마우스가 광원(폰은 천천히 저절로 돈다). 참고: Resend 첫 화면의 검은 유광 큐브, Rive 의 림 라이트 다이얼, 애플 제품 공개 영상의 빛 훑기.
import { engine, wrap, EASE, reduce, fine, mobile } from './vk.js?v=152829';
const FRAG = `
uniform float uLa, uLi, uKey, uLz;
vec3 shade(vec3 n, vec3 base, float gloss, float specK, vec3 L) {
  vec3 V = vec3(0., 0., 1.), H = normalize(L + V);
  float dif = max(dot(n, L), 0.), sp = pow(max(dot(n, H), 0.), gloss), fr = pow(1. - max(n.z, 0.), 3.);
  return base * (.06 + dif * uKey) + vec3(1.) * sp * specK * uLi + vec3(.42, .4, 1.) * fr * (.25 + .9 * uLi) * smoothstep(-.2, .6, dot(normalize(n.xy + 1e-4), L.xy))
    + vec3(.55, .58, .75) * fr * .35 * uKey;                          // 둘레 전체에 옅은 테두리 빛 — 원반과 틈이 갈라져 보이게
}
void main() {
  vec2 p = markP(); float px = 100. / uS;
  vec3 L = normalize(vec3(cos(uLa), sin(uLa), uLz));
  // 배경: 광원 쪽으로 기운 아주 옅은 빛 웅덩이
  vec2 lp = D0 + vec2(cos(uLa), sin(uLa)) * 40.;
  vec3 col = NIGHT + vec3(.05, .055, .12) * exp(-length(p - lp) * .028) * (.3 + .7 * uLi) + vec3(.02, .025, .05) * exp(-length(p - D0) * .02) * uKey;
  // 원반 그림자(고리와 원반 사이 틈이 더 어둡게)
  col *= 1. - .5 * exp(-max(length(p - D0) - 30., 0.) * .25) * uKey;
  // 원반: 낮은 돔 모양 법선
  vec2 q = (p - D0) / 30.; float z = sqrt(max(1. - dot(q, q), 0.));
  vec3 nD = normalize(vec3(q * 1.1, z + .12));
  vec3 cD = shade(nD, vec3(.075, .085, .12), 90., 1.6, L);
  // 고리: 띠 단면이 둥근 관처럼
  float rA = length(p - A0), tt = clamp((rA - 31.) / 1.6, -1., 1.); vec2 rd = (p - A0) / max(rA, 1e-3);
  vec3 nR = normalize(vec3(rd * tt * .95, sqrt(max(1. - tt * tt * .9, 0.))));
  vec3 cR = shade(nR, vec3(.78, .8, .9), 34., 2.4, L);
  col = mix(col, cD, fill(sdDisc(p), px));
  col = mix(col, cR, fill(sdRing(p), px));
  gl_FragColor = vec4(finish(col, p, px), 1.);
}`;
const E = engine({ frag: FRAG, U: { uLa: Math.PI * 1.05, uLi: 0, uKey: 0, uLz: 0.35 } });
const S = E.S;
// 화면 y 가 아래로 커지므로 각도 -π/4 = 오른쪽 위
const tl = gsap.timeline({ delay: 0.3 });
tl.to(S, { uLi: 1, duration: 0.8, ease: EASE.out }, 0)
  .to(S, { uLa: Math.PI * 1.05 + Math.PI * 2 * 0.85 + Math.PI * 0.2, duration: 2.6, ease: EASE.inOut }, 0)
  .to(S, { uKey: 1, uLz: 0.75, duration: 1.3, ease: EASE.inOut }, 1.6);
wrap(E, tl, { reframeAt: 2.9 });
// 대기: 마우스 = 광원 방향(심볼 중심 기준), 터치 기기는 아주 천천히 저절로
let aim = null; if (fine) addEventListener('pointermove', (e) => { const P = E.place(), r = E.hero.getBoundingClientRect(); aim = Math.atan2(e.clientY - r.top - P.y, e.clientX - r.left - P.x); }, { passive: true });
E.tick((t) => { if (tl.progress() < 1) return; const goal = aim ?? (S.uLa + 0.0035); let d = ((goal - S.uLa + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI; S.uLa += d * (aim == null ? 1 : 0.05); });
