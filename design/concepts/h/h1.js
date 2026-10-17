// H1 · Glass orb — 뒤에서 실제 속보 줄이 흐르고, 앞의 유리 구슬(굴절·무지개 반사)이 그 글자를 휘어 보이게 한다.
// 구슬 색은 지난 24시간 호재·악재 균형을 아주 옅게 띤다. 마우스를 따라 움직이고, 오프닝에서 물방울처럼 맺힌다.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { renderer, loop, pointer, easePointer, revealCopy, reduce, mobile, data } from './kit.js';
const canvas = document.getElementById('gl'), r = renderer(canvas);
r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 1.05;
const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(32, 1, 0.1, 100); cam.position.set(0, 0, 9);
scene.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture;
scene.background = new THREE.Color('#f7f9fc');
r.setClearColor('#f7f9fc', 1);
// 뒤의 속보 줄(캔버스 글자 텍스처 4줄, 줄마다 다른 속도)
const rows = [];
function rowTexture(items) {
  const c = document.createElement('canvas'), W = 4096, H = 160; c.width = W; c.height = H; const g = c.getContext('2d');
  g.fillStyle = '#f7f9fc'; g.fillRect(0, 0, W, H);   // 불투명해야 유리(투과)가 굴절시켜 보여 준다
  g.font = '600 64px Inter, Pretendard, sans-serif'; g.textBaseline = 'middle'; let x = 40;
  for (const it of items) {
    const v = DFI.v(it.v), t = DFI.line(it) || it.ko;
    g.fillStyle = it.v === '호재' ? '#7fd3b5' : it.v === '악재' ? '#f0a497' : '#c3cbd6'; g.font = '700 46px Inter, sans-serif'; g.fillText(v.toUpperCase(), x, H / 2); x += g.measureText(v.toUpperCase()).width + 24;
    g.fillStyle = '#9aa6b6'; g.font = '500 64px Inter, Pretendard, sans-serif'; g.fillText(t, x, H / 2); x += g.measureText(t).width + 120;
    if (x > W - 200) break;
  }
  const tex = new THREE.CanvasTexture(c); tex.wrapS = THREE.RepeatWrapping; tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8; return tex;
}
function buildRows(items) {
  rows.forEach((m) => scene.remove(m)); rows.length = 0;
  const xs = items.filter((it) => DFI.has(it));
  for (let i = 0; i < 6; i++) {
    const tex = rowTexture(xs.slice(i * 6).concat(xs.slice(0, i * 6)));
    const m = new THREE.Mesh(new THREE.PlaneGeometry(18, 18 * 160 / 4096), new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
    m.position.set(mobile() ? 0 : 3.2, (mobile() ? 3.2 : 2.2) - i * (mobile() ? 0.62 : 0.78), -2.2); m.userData.speed = (i % 2 ? -1 : 1) * (0.012 + i * 0.003); scene.add(m); rows.push(m);
    if (!reduce) gsap.from(m.position, { x: m.position.x + (i % 2 ? -6 : 6), duration: 1.6, ease: 'power3.out', delay: 0.15 + i * 0.07 });
  }
}
// 유리 구슬: 표면이 아주 느리게 출렁인다
const geo = new THREE.IcosahedronGeometry(1.35, 40);
const mat = new THREE.MeshPhysicalMaterial({ color: 0xffffff, metalness: 0, roughness: 0.03, transmission: 1, thickness: 1.6, ior: 1.42, iridescence: 0.75, iridescenceIOR: 1.25, iridescenceThicknessRange: [120, 480], clearcoat: 1, clearcoatRoughness: 0.05, attenuationColor: new THREE.Color('#eef2ff'), attenuationDistance: 8, envMapIntensity: 1.2 });
const U = { t: { value: 0 } };
mat.onBeforeCompile = (s) => { s.uniforms.uT = U.t; s.vertexShader = 'uniform float uT;\n' + s.vertexShader.replace('#include <begin_vertex>',
  '#include <begin_vertex>\n float w = sin(position.x*2.1+uT*0.9)*sin(position.y*2.4+uT*0.7)*sin(position.z*1.9+uT*1.1);\n transformed += normal * w * 0.07;'); };
const orb = new THREE.Mesh(geo, mat); scene.add(orb);
if (mobile()) orb.geometry.scale(0.62, 0.62, 0.62);
const ring = new THREE.Mesh(new THREE.TorusGeometry(2.05, 0.012, 16, 200), new THREE.MeshBasicMaterial({ color: '#533afd', transparent: true, opacity: 0.0 }));
ring.rotation.x = Math.PI * 0.42; scene.add(ring);
const base = () => mobile() ? new THREE.Vector3(0, 1.25, 0) : new THREE.Vector3(2.5, 0, 0);
orb.position.copy(base()); ring.position.copy(base()); orb.scale.setScalar(reduce ? 1 : 0.001);
const size = loop(r, scene, cam, (t) => {
  U.t.value = t; easePointer(0.05);
  const b = base(); orb.position.x = b.x + pointer.x * 0.35; orb.position.y = b.y + pointer.y * 0.25; ring.position.copy(orb.position);
  orb.rotation.y = t * 0.15 + pointer.x * 0.4; orb.rotation.x = pointer.y * 0.3; ring.rotation.z = t * 0.2;
  rows.forEach((m) => { m.material.map.offset.x += m.userData.speed * (reduce ? 0 : 1) * 0.1; });
});
// 오프닝: 물방울처럼 맺히고(탄성), 고리가 그려지고, 글이 들어온다
if (!reduce) {
  gsap.to(orb.scale, { x: 1, y: 1, z: 1, duration: 1.8, ease: 'elastic.out(1, 0.55)', delay: 0.35 });
  gsap.fromTo(cam.position, { z: 12 }, { z: 9, duration: 2.4, ease: 'power3.out' });
}
gsap.to(ring.material, { opacity: 0.35, duration: 1, delay: 1.4 });
revealCopy(0.9);
data.flash.then((d) => {
  buildRows(d.items); DFI.onLang(() => buildRows(d.items));
  const c = DFD.day24(d.items), bal = (c.u - c.d) / Math.max(1, c.u + c.d);
  mat.attenuationColor = new THREE.Color().lerpColors(new THREE.Color('#ffd9d2'), new THREE.Color('#d2f5e6'), 0.5 + bal * 2.5);
  const hud = document.getElementById('hud');
  const put = () => { hud.innerHTML = `<span class="up">${DFI.v('호재')} ${c.u}</span> · <span class="down">${DFI.v('악재')} ${c.d}</span> · ${DFI.lang() === 'ko' ? '지난 24시간' : 'last 24h'}`; };
  put(); DFI.onLang(put); gsap.to(hud, { opacity: 1, duration: 0.8, delay: 1.6 });
});
