// B2 · 빛 가림 (Blender 렌더) — 어두운 하늘의 해를 검은 원반이 가리고, 빛 테 속에서 고리가 나온 뒤 해가 낮의 배경이 된다.
// 첫 화면 배경색을 영상과 같은 곡선으로 바꿔(Blender 와 같이 선형 공간에서 섞기) 영상 바깥도 함께 밝아진다.
import { hero, lin, srgb, inout } from './bk.js?v=155146';
const A = [14, 16, 22].map(lin), B = [247, 249, 252].map(lin);
hero({ name: 'b2', copyAt: 4.0, bg: (t) => { const f = t * 60 + 1, k = inout((f - 220) / 72), c = A.map((a, i) => srgb(a + (B[i] - a) * k)); return { css: `rgb(${c.join(',')})`, dark: k < 0.5 }; } });
