// B2 · Timeline — 날짜를 가로로, 이야기를 세로로: 줄마다 점 줄(소식 하나 = 점). 줄을 누르면 아래(휴대폰)·오른쪽(PC)에 그 이야기.
import { T, esc } from '../l/lk.js?v=1017210046';
import * as B from './brk.js?v=1017210046';
import { mount } from './bc.js?v=1017210046';
mount((D, dy, S) => { const xs = B.pickList(D, S.f); if (!xs.some((x) => x.id === S.sel)) S.sel = xs[0] && xs[0].id; const cur = xs.find((x) => x.id === S.sel);
  return `<div class="wrap brf b2"><header class="ph"><h1>${T('Brief', '정리')}</h1><p>${T('Every ongoing story on one timeline. Pick one to read it.', '이어지는 이야기를 한 줄 시간 위에. 하나를 고르면 읽을 수 있어요.')}</p><p class="fr">${B.fresh(D)}</p></header>
  ${B.filtHTML(D, S.f)}
  <div class="split"><section class="box lanes"><ul>${xs.map((x) => { const a = B.tx(x); return `<li><button type="button" class="lane${x.id === S.sel ? ' on' : ''}" data-pick="${x.id}" aria-pressed="${x.id === S.sel}"><span class="nm">${esc(a.title)}</span>${B.metaHTML(x)}<span class="sw">${B.stripHTML(x, D)}</span></button></li>`; }).join('')}</ul></section>
    <div class="pane">${cur ? B.cardHTML(cur, D, { big: true, open: true }) : ''}${dy ? `<section class="box dly">${B.dailyHTML(dy)}</section>` : ''}</div></div></div>`; });
