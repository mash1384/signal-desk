// B3 · Morning — 뉴스레터처럼: 오늘의 큰 이야기 3개(크게) → 어제 하루 정리 → 나머지 이어지는 이야기(짧게).
import { T, esc } from '../l/lk.js?v=1017222057';
import * as B from './brk.js?v=1017222057';
import { mount } from './bc.js?v=1017222057';
mount((D, dy, S) => { const xs = B.pickList(D, S.f), top = xs.slice(0, 3), rest = xs.slice(3);
  return `<div class="wrap brf b3"><header class="ph"><h1>${T('Brief', '정리')}</h1><p>${T('Three stories to know now, yesterday in one page, and everything else still unfolding.', '지금 알아야 할 이야기 셋, 어제 하루 한 장, 그리고 아직 이어지는 나머지.')}</p><p class="fr">${B.fresh(D)}</p></header>
  ${B.filtHTML(D, S.f)}
  <section><h2 class="bh">${T('The big three', '지금 큰 이야기')}</h2><div class="top">${top.map((x) => B.cardHTML(x, D, { big: true })).join('')}</div></section>
  <div class="row"><section class="box dly">${B.dailyHTML(dy)}</section>
    <section class="box rest"><h2 class="bh">${T('Still unfolding', '아직 이어지는 이야기')}</h2><ul>${rest.map((x) => { const a = B.tx(x); return `<li><details><summary><span class="nm">${esc(a.title)}</span>${B.metaHTML(x)}${a.today ? `<span class="td">${esc(a.today.s)}</span>` : ''}</summary>${B.cardHTML(x, D)}</details></li>`; }).join('') || `<li class="mute">${T('Nothing else right now.', '지금은 더 없어요.')}</li>`}</ul></section></div></div>`; });
