// Build-only entry point. stdin/stdout JSON; no browser, network, or writes.
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const input = JSON.parse(readFileSync(0, 'utf8'));
const RealDate = Date;
globalThis.Date = class extends RealDate {
  constructor(...args) { super(...(args.length ? args : [input.now * 1000])); }
  static now() { return input.now * 1000; }
};
globalThis.window = globalThis;
globalThis.DF_ROOT = input.root;
globalThis.DF_BASE = input.root + 'assets/df/';
Object.defineProperty(globalThis, 'navigator', {value: {language: 'en-US'}, configurable: true});
let language = 'en';
globalThis.localStorage = {getItem: key => key === 'df-lang' ? language : null};
globalThis.fetch = async url => {
  if (url === DF_BASE + 'en.json') return {json: async () => input.en};
  throw new Error('prerender forbids fetch: ' + url);
};
const boot = readFileSync(new URL('../web/assets/df/data.js', import.meta.url), 'utf8');
vm.runInThisContext(boot, {filename: 'data.js'});
const L = await import('../web/assets/df/lk.js');
const V = await import('../web/assets/df/rv.js');
const B = await import('../web/assets/df/bv.js');
const C = await import('../web/assets/df/ck.js');
const CV = await import('../web/assets/df/cv.js');
const E = await import('../web/assets/df/ek.js');
const out = {live: {}, brief: {}, calendar: {}};
for (const lang of ['en', 'ko']) {
  language = lang;
  vm.runInThisContext(boot, {filename: 'data.js'});
  await Promise.resolve(); await Promise.resolve();
  const xs = (input.flash.items || []).map(x => ({...x, th:L.themesOf(x)})).filter(x=>x.t >= input.now-86400).sort((a,b)=>b.t-a.t);
  const score = x => x.s * 3 + Math.min(x.n || 1, 4) * 1.5;
  const lead = xs.filter(x=>input.now-x.t<21600 && x.v!=='중립').sort((a,b)=>score(b)-score(a)||b.t-a.t)[0];
  out.live[lang] = V.shell({lead: lead ? V.leadHTML(lead) : '',tabs:V.tabsHTML(xs),
    cards:xs.filter(x=>x!==lead).slice(0,24).map(x=>V.card(x,x.s>=3)).join(''),
    head:`<span class="ghl"><span>${L.T('Signals','신호')}</span>${V.sSeg()}</span>${V.mSeg()}`});
  const threads = {...input.threads, list:input.threads.threads.filter(x=>x.ai)};
  // 화면 JS 가 같은 자료를 받으면 다시 그리지 않도록(같은 내용을 새로 그리면 그 시점이 LCP 로 다시 잡힌다) 무엇으로 그렸는지 남긴다
  const snap = (wide) => `<i hidden data-brief-snapshot="${input.threads.made}|${(input.daily && input.daily.made) || ''}|${lang}|${wide ? 1 : 0}"></i>`;
  for (const wide of [false,true]) out.brief[lang+'-'+(wide?'wide':'narrow')] = snap(wide) + B.briefLayout(threads, input.daily, {f:'all',sel:null}, wide);
  const doc = {...input.econ, by:Object.fromEntries(input.econ.indicators.map(x=>[x.k,x]))};
  const recent = doc.indicators.filter(x=>input.now-x.latest.ts<7*86400);
  const k = (recent[0] || [...doc.indicators].sort((a,b)=>b.latest.ts-a.latest.ts)[0]).k;
  const state = {k,asset:'^GSPC',range:'10y'};
  const rel = E.recent(input.flash.release?.items || [])[0] || null;
  out.calendar[lang] = CV.calendarLayout(doc,state,rel).replace('<div class="wrap cal c3">', `<div class="wrap cal c3" data-snapshot-made="${doc.made}" data-snapshot-lang="${lang}">`).replace('<section class="box" id="detail" aria-live="polite"></section>',
    '<section class="box" id="detail" aria-live="polite">'+C.detailHTML(doc,doc.by[k],state)+'</section>') + '<script type="application/json" id="prerender-release">' + JSON.stringify(rel).replaceAll('<', '\\u003c') + '</script>';
}
process.stdout.write(JSON.stringify(out));
