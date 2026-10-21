import { mount } from './bc.js';
import { briefLayout } from './bv.js';
import { openSheet } from './lk.js';
mount((D,dy,S) => briefLayout(D,dy,S,matchMedia('(min-width: 1040px)').matches,window.DF_G || 'heat'));
// 브리핑(빌드 때 그린 맨 위 칸): 근거 단추 → 그 소식 상세 창, 시각은 보는 사람 시간대로
const bf = document.getElementById('bf');
if (bf) {
  let S = {}; try { S = JSON.parse(document.getElementById('bf-stories').textContent); } catch (e) { /* 근거 없이도 글은 보인다 */ }
  bf.addEventListener('click', (e) => { const b = e.target.closest('[data-bf]'); if (b && S[b.dataset.bf]) openSheet(S[b.dataset.bf]); });
  const hm = () => bf.querySelectorAll('time[data-ts]').forEach((t) => { t.textContent = new Date(+t.dataset.ts * 1000).toLocaleTimeString(DFI.lang() === 'ko' ? 'ko-KR' : 'en-GB', { hour: '2-digit', minute: '2-digit' }); });
  hm(); DFI.onLang(hm);
}
