// B1 · Stories — Particle·Ground News 식 이야기 목록: 줄기 카드가 위에서 아래로(최근에 움직인 순). PC는 오른쪽에 어제 하루 정리.
import { T } from '../l/lk.js?v=1017210046';
import * as B from './brk.js?v=1017210046';
import { mount } from './bc.js?v=1017210046';
mount((D, dy, S) => { const xs = B.pickList(D, S.f);
  return `<div class="wrap brf b1"><header class="ph"><h1>${T('Brief', '정리')}</h1><p>${T('The stories that keep moving — what happened so far and what was added today.', '며칠째 이어지는 이야기들 — 지금까지 무슨 일이 있었고, 오늘 무엇이 더해졌는지.')}</p><p class="fr">${B.fresh(D)}</p></header>
  ${B.filtHTML(D, S.f)}
  <div class="cols"><div class="list">${xs.map((x) => B.cardHTML(x, D)).join('') || `<p class="mute">${T('No ongoing stories in this theme right now.', '이 테마에는 지금 이어지는 이야기가 없어요.')}</p>`}</div>
    <aside class="rail"><section class="box dly">${B.dailyHTML(dy)}</section><section class="box how"><p><b>${T('How stories are built', '이야기는 이렇게 묶어요')}</b></p><p>${T('Stories about the same company, coin, country or event over several days are joined. Every sentence links to its source stories, and figures come only from them. AI writes the sentences; counts and dates are computed.', '같은 회사·코인·나라·사건을 다룬 소식을 며칠에 걸쳐 이어 묶어요. 문장마다 근거 소식이 달리고, 숫자는 근거에 있는 것만 써요. 문장은 AI, 개수와 날짜는 프로그램이 셌어요.')}</p></section></aside></div></div>`; });
