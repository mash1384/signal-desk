// B2 · Timeline — 모든 이야기가 같은 시간 축 위에(Linear 로드맵·The Verge StoryStream 참고): 줄마다 시작~지금 막대 하나, 소식은 눈금,
// 최근 24시간만 강조색 하나. PC는 오른쪽에 고른 이야기, 휴대폰은 그 줄 바로 아래 펼침.
import { T, esc } from '../l/lk.js?v=1017224009';
import * as B from './brk.js?v=1017224009';
import { mount } from './bc.js?v=1017224009';
const wide = () => matchMedia('(min-width: 1040px)').matches;
mount((D, dy, S) => {
  const xs = B.pickList(D, S.f); if (!xs.some((x) => x.id === S.sel)) S.sel = wide() ? xs[0] && xs[0].id : null;
  const cur = xs.find((x) => x.id === S.sel), A = xs.length ? B.axisOf(xs, D) : null;
  // 그래프 후보: window.DF_G = 'heat' | 'units' | 'mood' (없으면 지금 막대)
  const G = window.DF_G || 'heat', graph = (x) => (G === 'heat' ? B.heatHTML(x, D, A) : G === 'units' ? B.unitsHTML(x, D, A) : G === 'mood' ? B.moodHTML(x, D, A) : B.trackHTML(x, D, A));
  const meta = (x) => (G === 'bar' ? B.laneMeta(x) : B.metaMono(x));
  const lane = (x) => { const a = B.tx(x), on = x.id === S.sel;
    return `<li class="${on ? 'on' : ''}"><button type="button" class="lane g-${G}" data-pick="${x.id}" aria-expanded="${on}"><span class="hd2"><span class="nm">${esc(a.title)}</span>${meta(x)}</span>${graph(x)}</button>
      ${on && !wide() ? `<div class="inl">${B.detailHTML2(x, D)}</div>` : ''}</li>`; };
  return `<div class="wrap brf b2"><header class="ph"><h1>${T('Brief', '정리')}</h1><p>${T('Every ongoing story on one timeline. Pick one to read it.', '이어지는 이야기를 한 시간 축 위에. 하나를 고르면 읽을 수 있어요.')}</p><p class="fr">${B.fresh(D)}</p></header>
  ${B.filtHTML(D, S.f)}
  <div class="split"><section class="box lanes">${A ? `<div class="lhead g-${G}"><span class="lt">${T('Story', '이야기')}${G === 'heat' ? B.heatLegend() : ''}</span>${G === 'mood' ? `<span class="mh"><span>${T('Stories over time', '시간별 소식 양')}</span><span>${T('Mood', '분위기')}</span></span>` : B.axisHTML(A)}</div><ul>${xs.map(lane).join('')}</ul>` : `<p class="mute">${T('No ongoing stories in this theme right now.', '이 테마에는 지금 이어지는 이야기가 없어요.')}</p>`}</section>
    ${wide() ? `<div class="pane">${cur ? `<section class="box">${B.detailHTML2(cur, D)}</section>` : ''}${dy ? `<section class="box dly">${B.dailyHTML(dy)}</section>` : ''}</div>` : (dy ? `<section class="box dly">${B.dailyHTML(dy)}</section>` : '')}</div></div>`; });
