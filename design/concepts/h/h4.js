// H4 · Card constellation — 실제 속보가 새겨진 3D 카드 9장이 아래에서 한 장씩 날아와 공중에 부채꼴 궤도를 이룬다.
// 카드는 천천히 공전하며 숨쉬듯 떠 있고, 마우스를 따라 무리 전체가 기운다. 앞 카드는 또렷하고 뒤 카드는 흐려진다(안개 + 크기).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { renderer, loop, pointer, easePointer, revealCopy, reduce, mobile, data } from './kit.js';
const canvas = document.getElementById('gl'), r = renderer(canvas, { clear: 0xf7f9fc });
r.toneMapping = THREE.ACESFilmicToneMapping;
const scene = new THREE.Scene(); scene.fog = new THREE.Fog('#f7f9fc', 10, 20);
scene.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture;
const cam = new THREE.PerspectiveCamera(34, 1, 0.1, 100); cam.position.set(0, 0.3, 10);
scene.add(new THREE.AmbientLight(0xffffff, 0.6)); const dl = new THREE.DirectionalLight(0xffffff, 1.2); dl.position.set(3, 5, 6); scene.add(dl);
const group = new THREE.Group(); scene.add(group);
function face(it, dark) {
  const W = 720, H = 440, c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d');
  g.fillStyle = dark ? '#0d1f36' : '#ffffff'; g.fillRect(0, 0, W, H);
  const col = it.v === '호재' ? '#12b07c' : it.v === '악재' ? '#e5533f' : '#8b97a8';
  g.fillStyle = col + (dark ? '33' : '22'); roundRect(g, 40, 40, 170, 52, 12); g.fill();
  g.fillStyle = col; g.font = '700 30px Inter, Pretendard, sans-serif'; g.textBaseline = 'middle'; g.fillText(DFI.v(it.v), 62, 67);
  g.fillStyle = dark ? '#8fa3bd' : '#5b6b82'; g.font = '500 24px Inter, sans-serif'; g.textAlign = 'right'; g.fillText(DFI.ago(it.t), W - 40, 67); g.textAlign = 'left';
  g.fillStyle = dark ? '#ffffff' : '#0d253d'; g.font = '600 42px Inter, Pretendard, sans-serif'; g.textBaseline = 'alphabetic';
  wrap(g, DFI.line(it) || it.ko, 40, 160, W - 80, 54, 4);
  g.fillStyle = dark ? '#8fa3bd' : '#5b6b82'; g.font = '500 24px Inter, sans-serif'; g.fillText([DFI.outlets(it.n), ...it.coins.slice(0, 3)].join(' · '), 40, H - 40);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}
function roundRect(g, x, y, w, h, rr) { g.beginPath(); g.roundRect(x, y, w, h, rr); }
function wrap(g, text, x, y, mw, lh, max) { const words = text.split(' '); let line = '', n = 0;
  for (let i = 0; i < words.length; i++) { const tst = line + words[i] + ' '; if (g.measureText(tst).width > mw && line) { g.fillText(line, x, y); y += lh; line = words[i] + ' '; if (++n >= max - 1) { g.fillText(line.trim() + (i < words.length - 1 ? '…' : ''), x, y); return; } } else line = tst; }
  g.fillText(line, x, y); }
const cards = [];
function build(items) {
  cards.forEach((c) => group.remove(c.m)); cards.length = 0;
  const xs = items.filter((it) => DFI.has(it) && it.v !== '중립').slice(0, mobile() ? 6 : 9);
  xs.forEach((it, i) => {
    const dark = i % 3 === 0, geo = new THREE.BoxGeometry(2.4, 1.47, 0.05);
    const side = new THREE.MeshPhysicalMaterial({ color: dark ? '#0d1f36' : '#ffffff', roughness: 0.35, clearcoat: 1, clearcoatRoughness: 0.2 });
    const m = new THREE.Mesh(geo, side);
    const front = new THREE.Mesh(new THREE.PlaneGeometry(2.3, 1.4), new THREE.MeshBasicMaterial({ map: face(it, dark), toneMapped: false, fog: false })); front.position.z = 0.032; m.add(front);
    const n = xs.length, a = (i / n) * Math.PI * 2;
    cards.push({ m, a, i }); group.add(m);
    m.position.set(0, -6, 2); m.rotation.set(-1, 0, 0.6);
  });
  cards.forEach((c, i) => { const delay = reduce ? 0 : 0.35 + i * 0.12;
    gsap.to(c, { a: c.a, duration: 0.01 }); c.k = reduce ? 1 : 0; gsap.to(c, { k: 1, duration: 1.4, ease: 'expo.out', delay }); });
}
const R = () => mobile() ? 1.9 : 2.2;
const center = () => mobile() ? new THREE.Vector3(0, 1.7, 0) : new THREE.Vector3(3.3, 0, 0);
loop(r, scene, cam, (t) => {
  easePointer(0.05);
  const c0 = center(); group.position.lerp(c0, 0.1);
  group.rotation.y = pointer.x * 0.35; group.rotation.x = -pointer.y * 0.2 + 0.08;
  cards.forEach((c) => {
    const a = c.a + t * (reduce ? 0 : 0.12), rad = R();
    const tx = Math.sin(a) * rad * 1.1, tz = Math.cos(a) * rad * 0.9 - 1.6, ty = Math.sin(a * 2 + t * 0.6) * 0.25 + (c.i % 2 ? 0.35 : -0.35);
    const k = c.k ?? 1;
    c.m.position.set(THREE.MathUtils.lerp(0, tx, k), THREE.MathUtils.lerp(-6, ty, k), THREE.MathUtils.lerp(2, tz, k));
    c.m.rotation.set(THREE.MathUtils.lerp(-1, Math.sin(t * 0.4 + c.i) * 0.06, k), THREE.MathUtils.lerp(0, Math.sin(a) * 0.5, k), THREE.MathUtils.lerp(0.6, Math.sin(t * 0.3 + c.i) * 0.05, k));
    c.m.scale.setScalar(mobile() ? 0.6 : 0.74);
  });
});
revealCopy(1.2);
Promise.all([data.flash, document.fonts.ready]).then(([d]) => { build(d.items); DFI.onLang(() => build(d.items));
  const hud = document.getElementById('hud'), put = () => { hud.textContent = DFI.lang() === 'ko' ? '카드 = 방금 판정한 실제 속보' : 'Each card = a real headline, just judged'; }; put(); DFI.onLang(put); gsap.to(hud, { opacity: 1, duration: 0.8, delay: 2.2 }); });
