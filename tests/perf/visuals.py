"""Fixed-data, fixed-clock screenshots and the actual DOM/canvas font corpus.

python -m tests.perf.visuals --site BUILD --flash SNAPSHOT --out DIRECTORY
python -m tests.perf.visuals --compare BEFORE AFTER --out DIRECTORY
"""
import argparse
import asyncio
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlsplit

from tests.e2e.server import serve
from tests.e2e.test_matrix import CONTENT, path_for
from tests.perf.vitals import PAGES, DEVICES, prepare

SEED = """(() => {
 let seed=731; Math.random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
 window.__canvasText=[]; const fill=CanvasRenderingContext2D.prototype.fillText;
 CanvasRenderingContext2D.prototype.fillText=function(text,...args){
   if (/Mono|Michroma/.test(this.font)) __canvasText.push({font:this.font,text:String(text)});
   return fill.call(this,text,...args);
 };
})();"""
KEEP_WEBGL_FRAME = """(() => {
 const context=HTMLCanvasElement.prototype.getContext;
 HTMLCanvasElement.prototype.getContext=function(type,options){
   return context.call(this,type,/^(webgl2?|experimental-webgl)$/.test(type)
     ? {...options,preserveDrawingBuffer:true} : options);
 };
})();"""
CORPUS = """() => {
 const rows=[];const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 while(walker.nextNode()) { const n=walker.currentNode,e=n.parentElement;
   if (!e || !e.getClientRects().length || !n.textContent.trim()) continue;
   const s=getComputedStyle(e);if(!/Mono|Michroma/.test(s.fontFamily)) continue;
   const text=s.textTransform==='uppercase'?n.textContent.toUpperCase():n.textContent;
   rows.push({font:s.fontFamily,weight:s.fontWeight,text,selector:e.id?'#'+e.id:e.tagName+'.'+e.className});
 } return {dom:rows,canvas:__canvasText};
}"""


async def capture(args):
    from playwright.async_api import async_playwright
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    with serve(args.site) as base:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(**({} if args.channel == 'chromium' else {'channel': args.channel}))
            for name in args.pages:
                for device, width in DEVICES.items():
                    for lang in ('ko', 'en'):
                        context, page, offline = await prepare(browser, base, args.site, args.flash, width, lang)
                        await page.add_init_script(SEED)
                        if name == '':
                            # Preserve the last drawn pixels while the fake clock
                            # pauses rAF. No shader, scene or layout is changed.
                            await page.add_init_script(KEEP_WEBGL_FRAME)
                        fixed = dt.datetime.fromtimestamp(offline.now, dt.timezone.utc)
                        await page.clock.install(time=fixed)
                        await page.clock.pause_at(fixed)
                        errors, requests = [], []
                        page.on('pageerror', lambda e, bag=errors: bag.append(str(e)))
                        page.on('request', lambda r, bag=requests: bag.append(r.url))
                        try:
                            await page.goto(base + path_for(name, args.site), wait_until='networkidle')
                            await page.evaluate('document.fonts.ready')
                            await page.clock.run_for(5000)
                            await page.wait_for_timeout(400)
                            await page.wait_for_function('targets => Object.entries(targets).every(([s,n]) => document.querySelectorAll(s).length >= n)', arg=CONTENT[name])
                            if name == '':
                                await page.wait_for_function("window.ScrollTrigger?.getAll().length === 3 && document.querySelector('#nx canvas')")
                                await page.evaluate('document.fonts.ready')
                                await page.clock.run_for(1500)
                            # Scroll to each chart and back so lazy and eager variants have
                            # the same final contents; performance is measured separately.
                            height = await page.evaluate('document.documentElement.scrollHeight')
                            for y in range(0, height, 800):
                                await page.evaluate('(y) => scrollTo(0,y)', y)
                                await page.clock.run_for(100)
                                await page.wait_for_timeout(50)
                            await page.evaluate('scrollTo(0,0)')
                            await page.clock.run_for(1000)
                            await page.evaluate('document.fonts.ready')
                            await page.wait_for_timeout(300)
                            corpus = await page.evaluate(CORPUS)
                            key = (name.strip('/').replace('/', '-') or 'landing') + '-' + device + '-' + lang
                            before_height = await page.evaluate('document.documentElement.scrollHeight')
                            # Chrome's full-page capture temporarily changes the
                            # viewport used by GSAP's pinned scroll scenes. That
                            # can collapse 14,601px to 1,374px mid-capture. Capture
                            # landing viewports at explicit scroll positions.
                            await page.screenshot(path=str(args.out / (key + '.png')), full_page=name != '', animations='allow' if name == '' else 'disabled')
                            if name == '':
                                assert await page.evaluate('document.documentElement.scrollHeight') == before_height, 'capture changed pinned layout'
                                if args.landing_scenes:
                                    scenes = args.out / 'landing-scenes'
                                    scenes.mkdir(exist_ok=True)
                                    for scene, selector, progress in [('hero', 'hero', .5), ('wave', 'nx', .55), ('globe', 'nx', .86), ('logo', 'nx', .99)]:
                                        await page.evaluate("([id,p])=>{const t=ScrollTrigger.getAll().find(t=>t.trigger.id===id&&t.pin);scrollTo(0,t.start+p*(t.end-t.start))}", [selector, progress])
                                        await page.clock.run_for(2500)
                                        await page.wait_for_timeout(100)
                                        await page.screenshot(path=str(scenes / (key + '-' + scene + '.png')), animations='allow')
                                        assert await page.evaluate('document.documentElement.scrollHeight') == before_height, 'scene capture changed pinned layout'
                                    await page.evaluate('scrollTo(0,0)')
                                    await page.clock.run_for(1000)
                            assert not errors and not offline.unmapped, (errors, offline.unmapped)
                            raw = [u for u in requests if urlsplit(u).hostname == 'raw.githubusercontent.com']
                            if args.forbid_raw:
                                assert not raw, ('direct raw request', raw)
                            rows.append({'key': key, 'page': name, 'device': device, 'lang': lang, 'corpus': corpus,
                                         'raw_requests': raw, 'requests': requests,
                                         'content': {s: await page.locator(s).count() for s in CONTENT[name]},
                                         'height': await page.evaluate('document.documentElement.scrollHeight')})
                            print(key, flush=True)
                        finally:
                            await context.close()
            await browser.close()
    dest = args.out / 'capture.json'
    if dest.exists() and set(args.pages) != set(PAGES):
        previous = json.loads(dest.read_text())
        assert previous['clock'] == offline.now and previous['seed'] == 731
        rows = [r for r in previous['rows'] if r['page'] not in args.pages] + rows
    dest.write_text(json.dumps({'clock': offline.now, 'seed': 731, 'rows': rows}, ensure_ascii=False, indent=2) + '\n')


def compare(before, after, out):
    from PIL import Image, ImageChops
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(before.glob('*.png')):
        other = after / path.name
        if not other.exists():
            raise FileNotFoundError(other)
        a, b = Image.open(path).convert('RGB'), Image.open(other).convert('RGB')
        width, height = max(a.width, b.width), max(a.height, b.height)
        aa, bb = Image.new('RGB', (width, height), 'white'), Image.new('RGB', (width, height), 'white')
        aa.paste(a); bb.paste(b)
        diff = ImageChops.difference(aa, bb)
        red, green, blue = diff.split()
        histogram = ImageChops.lighter(ImageChops.lighter(red, green), blue).histogram()
        pixels = width * height
        changed = pixels - histogram[0]
        strong = pixels - sum(histogram[:9])
        diff.save(out / path.name)
        rows.append({'file': path.name, 'before_size': list(a.size), 'after_size': list(b.size),
                     'changed_ratio': changed / pixels, 'over_8_ratio': strong / pixels})
    if not rows:
        raise ValueError('no screenshots compared')
    (out / 'diff.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--site', type=Path)
    p.add_argument('--flash', type=Path, default=Path('.qa/snapshot-r/flash'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--compare', nargs=2, type=Path)
    p.add_argument('--pages', nargs='+', default=PAGES)
    p.add_argument('--channel', default='chrome')
    p.add_argument('--forbid-raw', action='store_true')
    p.add_argument('--landing-scenes', action='store_true', help='also capture pinned 3D scene viewports')
    args = p.parse_args()
    if args.compare:
        print(json.dumps(compare(*args.compare, args.out)))
    elif args.site:
        asyncio.run(capture(args))
    else:
        p.error('--site or --compare is required')


if __name__ == '__main__':
    main()
