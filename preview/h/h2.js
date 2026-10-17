// H2 · Price terrain — 비트코인 24시간 가격이 점으로 된 3D 산맥이 된다(앞쪽 가장자리가 실제 가격선, 뒤로 갈수록 잔물결로 흐려짐).
// 그 시각에 나온 BTC·시장 속보는 능선 위에 빛기둥으로 솟는다. 오프닝: 점들이 평평하게 깔렸다가 파도처럼 솟아오르고, 카메라가 미끄러져 들어온다.
import * as THREE from 'three';
import { renderer, loop, pointer, easePointer, revealCopy, reduce, mobile, data } from './kit.js';
const canvas = document.getElementById('gl'), r = renderer(canvas, { clear: 0xf7f9fc });
const scene = new THREE.Scene(); scene.fog = new THREE.Fog('#f7f9fc', 9, 22);
const cam = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
const NX = mobile() ? 110 : 200, NZ = mobile() ? 46 : 70, W = 12, D = 11;
const U = { uT: { value: 0 }, uRise: { value: reduce ? 1 : 0 }, uPrice: { value: null }, uMouse: { value: new THREE.Vector2(9, 9) } };
const pos = new Float32Array(NX * NZ * 3), uv = new Float32Array(NX * NZ * 2);
for (let j = 0, k = 0; j < NZ; j++) for (let i = 0; i < NX; i++, k++) { pos.set([(i / (NX - 1) - 0.5) * W, 0, (j / (NZ - 1)) * -D], k * 3); uv.set([i / (NX - 1), j / (NZ - 1)], k * 2); }
const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
const mat = new THREE.ShaderMaterial({ uniforms: U, transparent: true, depthWrite: false, vertexShader: `
  uniform float uT, uRise; uniform sampler2D uPrice; uniform vec2 uMouse; varying float vH; varying float vZ;
  void main(){ vec3 p = position; float back = uv.y; float price = texture2D(uPrice, vec2(clamp(uv.x - back*.06, 0., 1.), .5)).r;
    float wave = sin(uv.x*18. - uT*.8 + back*6.)*.06 + sin(uv.x*7. + uT*.5)*.05;
    float h = price*2.4*(1. - back*.55) + wave*(.15 + back*1.4);
    float rise = smoothstep(0., 1., clamp(uRise*1.6 - uv.x*.6 - back*.2, 0., 1.));
    float md = length((modelViewMatrix*vec4(p,1.)).xy - uMouse*vec2(4.,2.4)); h += exp(-md*md*.6)*.35*(1.-back);
    p.y = h * rise; vH = price; vZ = back;
    vec4 mv = modelViewMatrix*vec4(p,1.); gl_Position = projectionMatrix*mv; gl_PointSize = (mix(3.4, 1.6, back)) * (9. / -mv.z) * ${(Math.min(devicePixelRatio || 1, 2)).toFixed(1)}; }`,
  fragmentShader: `varying float vH; varying float vZ; void main(){ vec2 c = gl_PointCoord-.5; if(dot(c,c)>.25) discard;
    vec3 lo = vec3(.33,.30,.99), hi = vec3(.18,.80,.75); vec3 col = mix(lo, hi, vH); float a = mix(.95,.12,vZ);
    gl_FragColor = vec4(mix(col, vec3(.05,.15,.24), vZ*.35), a); }` });
const pts = new THREE.Points(g, mat); scene.add(pts);
// 앞쪽 가장자리 = 실제 가격선(굵은 선)
const lineMat = new THREE.LineBasicMaterial({ color: '#533afd', transparent: true, opacity: 0 });
let line = null; const pins = new THREE.Group(); scene.add(pins);
function priceTex(ps) { const lo = Math.min(...ps), hi = Math.max(...ps), n = 256, a = new Uint8Array(n * 4);
  for (let i = 0; i < n; i++) { const f = i / (n - 1) * (ps.length - 1), k = Math.floor(f), t = f - k, v = ps[k] * (1 - t) + ps[Math.min(ps.length - 1, k + 1)] * t; a[i * 4] = Math.round((v - lo) / (hi - lo || 1) * 255); a[i * 4 + 3] = 255; }
  const tx = new THREE.DataTexture(a, n, 1); tx.minFilter = tx.magFilter = THREE.LinearFilter; tx.needsUpdate = true; return { tx, lo, hi }; }
let P = null;
data.klines.then((ps) => {
  if (!ps) ps = Array.from({ length: 96 }, (_, i) => 83000 + Math.sin(i / 7) * 500 + i * 3);
  P = priceTex(ps); U.uPrice.value = P.tx;
  const v = ps.map((p, i) => new THREE.Vector3((i / (ps.length - 1) - 0.5) * W, (p - P.lo) / (P.hi - P.lo || 1) * 2.6, 0.02));
  line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(v), lineMat); scene.add(line);
  data.flash.then((d) => pinsFrom(d, ps));
});
function pinsFrom(d, ps) {
  const t1 = Date.now() / 1000, t0 = t1 - 24 * 3600;
  const seen = new Set(), xs = d.items.filter((it) => it.t > t0 && it.v !== '중립' && (it.s >= 2 || it.coins.includes('BTC') || it.mw)).filter((it) => { const b = Math.floor((it.t - t0) / 5400); if (seen.has(b)) return false; seen.add(b); return true; }).slice(0, 12);
  xs.forEach((it, i) => { const u = (it.t - t0) / (t1 - t0), k = Math.round(u * (ps.length - 1)), y = (ps[k] - P.lo) / (P.hi - P.lo || 1) * 2.6;
    const col = it.v === '호재' ? '#12b07c' : '#e5533f';
    const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.007, 0.007, 1.4, 6), new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.8 }));
    beam.position.set((u - 0.5) * W, y + 0.7, 0.02); beam.scale.y = 0.001; pins.add(beam);
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.055, 16, 16), new THREE.MeshBasicMaterial({ color: col })); dot.position.set(beam.position.x, y + 1.4, 0.02); dot.scale.setScalar(0.001); pins.add(dot);
    dot.userData = { it, base: y + 1.4 };
    gsap.to(beam.scale, { y: 1, duration: 0.9, ease: 'power3.out', delay: (reduce ? 0 : 2.0) + i * 0.08 });
    gsap.to(beam.position, { y: y + 0.7, duration: 0.9, delay: (reduce ? 0 : 2.0) + i * 0.08 });
    gsap.to(dot.scale, { x: 1, y: 1, z: 1, duration: 0.6, ease: 'back.out(3)', delay: (reduce ? 0 : 2.4) + i * 0.08 });
  });
  window.__pins = xs;
}
// 마우스를 올린 빛기둥의 소식을 띄운다
const ray = new THREE.Raycaster(), mv = new THREE.Vector2(), tip = document.getElementById('tip');
addEventListener('pointermove', (e) => { mv.set(e.clientX / innerWidth * 2 - 1, -(e.clientY / innerHeight * 2 - 1)); ray.setFromCamera(mv, cam);
  const hit = ray.intersectObjects(pins.children.filter((o) => o.userData.it), false)[0];
  if (hit) { const it = hit.object.userData.it; tip.innerHTML = `<b class="${DFD.vcls(it.v)}">${DFI.v(it.v)}</b> ${DFD.esc(DFI.line(it) || it.ko)}<small>${DFI.ago(it.t)}</small>`; tip.style.left = e.clientX + 14 + 'px'; tip.style.top = e.clientY + 14 + 'px'; tip.classList.add('on'); document.body.style.cursor = 'pointer'; }
  else { tip.classList.remove('on'); document.body.style.cursor = ''; } }, { passive: true });
const camBase = () => mobile() ? new THREE.Vector3(0, 5.2, 9.5) : new THREE.Vector3(2.4, 4.4, 8.2);
cam.position.copy(camBase()).add(new THREE.Vector3(0, 2.5, 5));
loop(r, scene, cam, (t) => {
  U.uT.value = t; easePointer(0.05); U.uMouse.value.set(pointer.x, pointer.y);
  const b = camBase(); cam.position.x += (b.x + pointer.x * 0.6 - cam.position.x) * 0.04; cam.position.y += (b.y + pointer.y * 0.3 - cam.position.y) * 0.04; cam.position.z += (b.z - cam.position.z) * 0.035;
  cam.lookAt(mobile() ? 0 : 2.0, mobile() ? -1.4 : 0.6, -3);
  pins.children.forEach((o) => { if (o.userData.base) o.position.y = o.userData.base + Math.sin(t * 2 + o.position.x) * 0.04; });
});
gsap.to(U.uRise, { value: 1, duration: 2.6, ease: 'power2.inOut', delay: 0.2 });
gsap.to(lineMat, { opacity: 0.9, duration: 1, delay: 1.8 });
revealCopy(1.0);
DFD.prices(['BTC']).then((p) => { const hud = document.getElementById('hud'), put = () => { hud.innerHTML = `BTC ${DFD.money(p.BTC.p)} <span class="${p.BTC.c >= 0 ? 'up' : 'down'}">${DFD.pct(p.BTC.c)}</span> · ${DFI.lang() === 'ko' ? '빛기둥 = 그 시각의 소식' : 'Beams = news at that moment'}`; }; put(); DFI.onLang(put); gsap.to(hud, { opacity: 1, duration: 0.8, delay: 2.4 }); }).catch(() => {});
