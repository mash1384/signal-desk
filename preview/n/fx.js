// N3 카드 '도착' 모션 후보 5개. 판이 서랍에서 빠져 사용자 앞으로 날아올 때(fly) → 도착(arrive) → 머묾(update) → 돌아감(leave).
// 1 입자 조립 · 2 충격파 · 3 잔상 · 4 윤곽 빔 · 5 타일 뒤집기
import * as THREE from 'three';

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const eOut = (x) => 1 - Math.pow(1 - clamp(x), 3);
const eBack = (x) => { x = clamp(x); const c = 1.70158; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };

export const FX_NAMES = { 1: ['Particle assemble', '입자 조립'], 2: ['Shockwave', '충격파'], 3: ['Echo trail', '잔상'], 4: ['Border beam', '윤곽 빔'], 5: ['Tile flip', '타일 뒤집기'] };

export function makeFX(kind, { scene, PW, PH, mobile, dpr }) {
  // ---------- 판 재질에 공통 셰이더 끼우기: 녹아 사라짐/나타남, 물결(충격파), 위에서부터 드러남, 테두리 빔 ----------
  function install(mat) {
    const U = { uDis: { value: 1 }, uAmp: { value: 0 }, uWT: { value: 0 }, uImp: { value: new THREE.Vector2(0, PH * 0.3) }, uWipe: { value: 1 }, uBeam: { value: -1 }, uBeamA: { value: 0 }, uBase: { value: new THREE.Color(1, 1, 1) } };
    mat.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, U);
      sh.vertexShader = sh.vertexShader.replace('#include <common>', `#include <common>
        uniform float uAmp, uWT; uniform vec2 uImp; varying vec2 vLP;`).replace('#include <begin_vertex>', `#include <begin_vertex>
        vLP = position.xz; float dd = length(position.xz - uImp); float ph = dd * 5.5 - uWT * 15.;
        transformed.y += uAmp * sin(ph) * exp(-dd * .35) * exp(-uWT * 2.4) * step(ph, 0.);`);
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', `#include <common>
        uniform float uDis, uWipe, uBeam, uBeamA; uniform vec3 uBase; varying vec2 vLP;
        float hsh(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
        float vno(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f); return mix(mix(hsh(i), hsh(i+vec2(1,0)), f.x), mix(hsh(i+vec2(0,1)), hsh(i+vec2(1,1)), f.x), f.y); }
        float sdRR(vec2 p, vec2 b, float r){ vec2 q = abs(p) - b + r; return length(max(q, 0.)) + min(max(q.x, q.y), 0.) - r; }`).replace('#include <map_fragment>', `#include <map_fragment>
        if (uDis < .999) { float n = vno(vLP * 5.) * .65 + hsh(floor(vLP * 34.)) * .35; if (n > uDis) discard; diffuseColor.rgb = mix(diffuseColor.rgb, vec3(.42, .36, 1.), smoothstep(uDis - .09, uDis, n)); }
        if (uWipe < .999) { float wy = vLP.y / ${PH.toFixed(3)} + .5; float m = smoothstep(uWipe * 1.2, uWipe * 1.2 - .2, wy); diffuseColor.rgb = mix(uBase, diffuseColor.rgb, m); }
        if (uBeamA > .001) { float d = sdRR(vLP, vec2(${(PW / 2 - 0.075).toFixed(3)}, ${(PH / 2 - 0.075).toFixed(3)}), .15); float bm = smoothstep(.045, .0, abs(d + .03));
          float a = atan(vLP.y / ${PH.toFixed(3)}, vLP.x / ${PW.toFixed(3)}) / 6.2832 + .5; float h1 = fract(uBeam - a), h2 = fract(uBeam + .5 - a);
          float tr = max(1. - smoothstep(0., .34, h1), 1. - smoothstep(0., .34, h2)); float hd = min(h1, h2);
          vec3 bc = mix(vec3(.62, .58, 1.), vec3(.33, .23, .99), smoothstep(0., .1, hd)); bc = mix(bc, vec3(.18, .85, .77), smoothstep(.12, .34, hd));
          diffuseColor.rgb = mix(diffuseColor.rgb, bc, bm * tr * uBeamA); }`);
    };
    return U;
  }

  const S = { kind, t: 0 };
  // ---------- 1 입자 조립: 날기 시작하면 판이 입자로 부서지고, 입자들이 소용돌이치며 날아와 사용자 앞에서 다시 카드로 모인다 ----------
  const NP = mobile ? 3200 : 5200;
  let parts = null;
  if (kind === 1) {
    const g = new THREE.BufferGeometry(), aL = new Float32Array(NP * 3), aC = new Float32Array(NP * 3), aD = new Float32Array(NP), aR = new Float32Array(NP * 3);
    for (let i = 0; i < NP; i++) { aL.set([(Math.random() - 0.5) * (PW - 0.16), 0.01, (Math.random() - 0.5) * (PH - 0.16)], i * 3); aD[i] = Math.random(); aR.set([Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5], i * 3); }
    g.setAttribute('position', new THREE.BufferAttribute(aL, 3)); g.setAttribute('aC', new THREE.BufferAttribute(aC, 3)); g.setAttribute('aD', new THREE.BufferAttribute(aD, 1)); g.setAttribute('aR', new THREE.BufferAttribute(aR, 3));
    const U = { uM0: { value: new THREE.Matrix4() }, uM1: { value: new THREE.Matrix4() }, uK: { value: 0 }, uA: { value: 0 }, uT: { value: 0 } };
    parts = new THREE.Points(g, new THREE.ShaderMaterial({ uniforms: U, transparent: true, depthWrite: false, vertexShader: `attribute vec3 aC, aR; attribute float aD; uniform mat4 uM0, uM1; uniform float uK, uA, uT; varying vec3 vC; varying float vA;
      void main(){ float k = clamp((uK * 1.45 - aD * .45), 0., 1.); float e = 1. - pow(1. - k, 3.);
        vec3 s = (uM0 * vec4(position, 1.)).xyz, d = (uM1 * vec4(position, 1.)).xyz;
        vec3 p = mix(s, d, e) + aR * 3.2 * sin(3.1416 * e) + vec3(sin(uT * 3. + aD * 20.), cos(uT * 2.6 + aD * 13.), 0.) * .25 * sin(3.1416 * e);
        vC = aC; vA = uA; vec4 mv = modelViewMatrix * vec4(p, 1.); gl_Position = projectionMatrix * mv; gl_PointSize = (2.2 + aD * 2.2) * (13. / -mv.z) * ${dpr.toFixed(1)}; }`,
      fragmentShader: `varying vec3 vC; varying float vA; void main(){ vec2 c = gl_PointCoord - .5; if (dot(c, c) > .25) discard; gl_FragColor = vec4(vC, vA); }` }));
    parts.frustumCulled = false; parts.visible = false; scene.add(parts); parts.userData.U = U;
  }
  // ---------- 2 충격파: 도착하는 순간 카드가 젤리처럼 물결치고, 뒤로 고리 두 개가 퍼진다 ----------
  const rings = kind === 2 ? [0, 1].map(() => { const m = new THREE.Mesh(new THREE.RingGeometry(0.975, 1, 128), new THREE.MeshBasicMaterial({ color: 0x533afd, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide })); scene.add(m); return m; }) : [];
  // ---------- 3 잔상: 날아오는 궤적을 따라 색이 다른 잔상 다섯 장이 뒤따르다 도착하면 한 장으로 접힌다 ----------
  const GH = 6, hist = [], ghosts = kind === 3 ? [...Array(GH)].map((_, i) => { const c = new THREE.Color().lerpColors(new THREE.Color('#8f86ff'), new THREE.Color('#4fe0c4'), i / (GH - 1));
    const m = new THREE.Mesh(new THREE.PlaneGeometry(PW, PH).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0, depthWrite: false, alphaMap: null })); m.matrixAutoUpdate = false; m.renderOrder = -2; scene.add(m); return m; }) : [];
  // ---------- 5 타일 뒤집기: 카드가 작은 타일들로 나뉘어 뒷면(남보라)을 보이며 날아오다, 도착하면서 모서리부터 물결처럼 뒤집혀 앞면이 된다 ----------
  const TC = 12, TR = 8; let tiles = null;
  if (kind === 5) {
    const tw = PW / TC, th = PH / TR, geo = new THREE.PlaneGeometry(tw * 0.965, th * 0.94).rotateX(-Math.PI / 2);
    const ig = new THREE.InstancedBufferGeometry(); ig.index = geo.index; ig.attributes.position = geo.attributes.position;
    const aCell = new Float32Array(TC * TR * 2), aDel = new Float32Array(TC * TR);
    for (let y = 0; y < TR; y++) for (let x = 0; x < TC; x++) { const i = y * TC + x; aCell.set([x, y], i * 2); aDel[i] = (x / TC * 0.62 + y / TR * 0.38) * 0.6 + Math.random() * 0.05; }
    ig.setAttribute('aCell', new THREE.InstancedBufferAttribute(aCell, 2)); ig.setAttribute('aDel', new THREE.InstancedBufferAttribute(aDel, 1)); ig.instanceCount = TC * TR;
    const U = { uMap: { value: null }, uT: { value: 0 } };
    tiles = new THREE.Mesh(ig, new THREE.ShaderMaterial({ uniforms: U, side: THREE.DoubleSide, vertexShader: `attribute vec2 aCell; attribute float aDel; uniform float uT; varying vec2 vUv; varying float vF;
      void main(){ float k = clamp((uT - aDel) / .5, 0., 1.); float c = 1.70158; float e = 1. + (c + 1.) * pow(k - 1., 3.) + c * pow(k - 1., 2.);
        float ang = (1. - e) * 3.14159; vec3 p = position; float cy = cos(ang), sy = sin(ang); p = vec3(p.x, p.y * cy - p.z * sy, p.y * sy + p.z * cy);
        vec2 ctr = vec2((aCell.x + .5) * ${(PW / TC).toFixed(4)} - ${(PW / 2).toFixed(3)}, (aCell.y + .5) * ${(PH / TR).toFixed(4)} - ${(PH / 2).toFixed(3)});
        vec3 lp = vec3(position.x + ctr.x, 0., position.z + ctr.y); vUv = vec2(.5 + lp.x / ${PW.toFixed(3)}, .5 - lp.z / ${PH.toFixed(3)});
        p.x += ctr.x; p.z += ctr.y; p.y += sin(ang) * .35; vF = k;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.); }`,
      fragmentShader: `uniform sampler2D uMap; varying vec2 vUv; varying float vF; void main(){ vec4 c = texture2D(uMap, vUv); if (c.a < .5) discard;
        if (!gl_FrontFacing) { gl_FragColor = vec4(mix(vec3(.2, .14, .7), vec3(.33, .23, .99), vUv.x), 1.); return; } gl_FragColor = vec4(c.rgb, 1.);
#include <colorspace_fragment>
      }` }));
    tiles.visible = false; tiles.userData.U = U;
  }

  const PAL = ['#6d6cf7', '#8f9bff', '#533afd', '#1d3557', '#a9b3ff'].map((h) => new THREE.Color(h));
  const sample = (p) => { // 판 캔버스 색을 입자에 입힌다
    if (!parts) return; const d = p.g.getImageData(0, 0, p.c.width, p.c.height).data, a = parts.geometry.getAttribute('position'), c = parts.geometry.getAttribute('aC');
    for (let i = 0; i < NP; i++) { const u = a.getX(i) / PW + 0.5, v = a.getZ(i) / PH + 0.5, x = Math.min(p.c.width - 1, u * p.c.width | 0), y = Math.min(p.c.height - 1, v * p.c.height | 0), j = (y * p.c.width + x) * 4;
      let col = new THREE.Color(d[j] / 255, d[j + 1] / 255, d[j + 2] / 255);
      if (d[j + 3] < 128 || (d[j] + d[j + 1] + d[j + 2]) / 765 > 0.8) col = PAL[(Math.random() * PAL.length) | 0];   // 흰 바탕 부분은 브랜드 색 입자로(밝은 배경에서 보이게)
      c.setXYZ(i, col.r, col.g, col.b); }
    c.needsUpdate = true;
  };
  const baseOf = (p) => { const d = p.g.getImageData(60, p.c.height - 140, 1, 1).data; return new THREE.Color(d[0] / 255, d[1] / 255, d[2] / 255).convertSRGBToLinear(); };

  return {
    install,
    fly(p, t) {   // 날기 시작
      S.p = p; S.tf = t; S.ta = -1;
      if (kind === 1) { p.m.updateMatrixWorld(); parts.userData.U.uM0.value.copy(p.m.matrixWorld); sample(p); parts.visible = true; }
      if (kind === 3) { hist.length = 0; ghosts.forEach((g) => { g.material.alphaMap = p.tex; g.material.needsUpdate = true; }); }
      if (kind === 4) { p.U.uBase.value.copy(baseOf(p)); p.U.uWipe.value = 0; p.U.uBeamA.value = 1; p.U.uBeam.value = 0; }
      if (kind === 5) { tiles.userData.U.uMap.value = p.tex; p.m.add(tiles); tiles.visible = true; tiles.userData.U.uT.value = -1; }
    },
    arrive(p, t) { if (S.p === p) S.ta = t; if (kind === 2) { p.U.uWT.value = 0; } },
    leave(p) { if (S.p !== p) return; S.p = null; p.U.uDis.value = 1; p.U.uAmp.value = 0; p.U.uWipe.value = 1; p.U.uBeamA.value = 0; p.m.visible = true;
      if (parts) parts.visible = false; if (tiles) { tiles.visible = false; p.m.remove(tiles); } ghosts.forEach((g) => { g.material.opacity = 0; }); rings.forEach((r) => { r.material.opacity = 0; }); },
    update(t, cam, vR, vU, vB) {
      const p = S.p; if (!p) return; const sinceF = t - S.tf, sinceA = S.ta > 0 ? t - S.ta : -1, f = p.f;
      if (kind === 1) {   // 판은 부서졌다가(0.18초) 입자가 다 모이면 다시 나타난다
        p.m.updateMatrixWorld(); const U = parts.userData.U; U.uM1.value.copy(p.m.matrixWorld); U.uT.value = t; U.uK.value = clamp(sinceF / 1.05);
        p.U.uDis.value = sinceF < 0.2 ? 1 - sinceF / 0.2 : clamp((sinceF - 0.95) / 0.35);
        U.uA.value = sinceF < 0.95 ? 0.95 : clamp(1 - (sinceF - 0.95) / 0.35) * 0.95;
        if (sinceF > 1.4) parts.visible = false;
      }
      if (kind === 2) {   // 도착 직전 빠르게 다가오고, 닿는 순간 물결 + 고리
        if (sinceA >= 0) { p.U.uWT.value = sinceA; p.U.uAmp.value = 0.42;
          rings.forEach((r, i) => { const k = clamp((sinceA - i * 0.12) / 0.9); r.position.copy(p.m.position).addScaledVector(vB, -0.4); r.quaternion.copy(cam.quaternion);
            const s = (PW * 0.5) * (1 + eOut(k) * 0.85); r.scale.setScalar(s); r.material.opacity = k > 0 && k < 1 ? (1 - k) * 0.55 : 0; }); }
      }
      if (kind === 3) {   // 지난 프레임들의 위치를 잔상으로
        p.m.updateMatrixWorld(); hist.unshift(p.m.matrixWorld.clone()); if (hist.length > GH * 3 + 1) hist.pop();
        const fade = sinceA < 0 ? 1 : clamp(1 - sinceA / 0.35);
        ghosts.forEach((g, i) => { const h = hist[(i + 1) * 3] || hist[hist.length - 1]; if (!h) return; g.matrix.copy(h); g.matrixWorldNeedsUpdate = true;
          g.material.opacity = (0.42 - i * 0.06) * fade * clamp(sinceF / 0.12); });
        if (sinceA >= 0) { const k = clamp(sinceA / 0.25); p.m.scale.multiplyScalar(1 + Math.sin(k * Math.PI) * 0.05); }
      }
      if (kind === 4) {   // 날아오는 동안 빈 카드 테두리를 빛이 두 갈래로 돌고, 도착하면 내용이 위에서부터 차오른다
        p.U.uBeam.value = sinceF * 0.85; p.U.uBeamA.value = sinceA < 0 ? clamp(sinceF / 0.2) : clamp(1 - (sinceA - 0.4) / 0.5);
        p.U.uWipe.value = sinceA < 0 ? 0 : clamp(sinceA / 0.55);
      }
      if (kind === 5) {   // 날아오는 동안은 뒷면, 도착 무렵 모서리부터 뒤집힌다
        p.m.visible = true; p.U.uDis.value = 0;   // 원래 판은 숨기고 타일만
        tiles.userData.U.uT.value = sinceF - 0.45;
        if (sinceF > 0.45 + 0.6 + 0.55) { p.U.uDis.value = 1; tiles.visible = false; }
      }
    },
  };
}
