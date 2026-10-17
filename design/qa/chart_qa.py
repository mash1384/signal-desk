import sys, json, asyncio
from playwright.async_api import async_playwright
# 차트 위로 포인터를 움직이며 범례·차트·카드·문서 높이가 바뀌는지, 크기 감시가 몇 번 일어나는지 잰다
WATCH = """() => { window.__rz = 0; const ro = new ResizeObserver((es) => { window.__rz += es.length; });
  document.querySelectorAll('.lgd, .lwbox, .bigc, .ld, #flow, .rxc, .lwc').forEach((e) => ro.observe(e)); window.__ro = ro; }"""
SNAP = """(sel) => { const q = (s) => [...document.querySelectorAll(s)].map((e) => Math.round(e.getBoundingClientRect().height * 10) / 10);
  const ch = document.querySelector(sel); const r = ch && ch.getBoundingClientRect();
  return { lgd: q('.lgd'), box: q('.lwbox'), ld: q('.ld'), top: r ? Math.round(r.top * 10) / 10 : null, doc: document.documentElement.scrollHeight, txt: [...document.querySelectorAll('.lgd')].map((e) => e.textContent).join(' | ') }; }"""
async def run(url, sel, mobile, label, sheet=False):
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        W = 360 if 'narrow' in label else 390
        ctx = await b.new_context(viewport={'width': W, 'height': 800} if mobile else {'width': 1440, 'height': 900}, device_scale_factor=2 if mobile else 1, has_touch=mobile, is_mobile=mobile, locale='ko-KR')
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        await pg.add_init_script("localStorage.setItem('df-lang','ko'); localStorage.setItem('df-my', JSON.stringify(['BTC','NQ=F','NVDA']));")
        await pg.goto(url, wait_until='networkidle'); await pg.wait_for_timeout(4000)
        if sheet:
            await pg.click('.cd[data-id] .ln'); await pg.wait_for_selector('.sheet.on', timeout=5000); await pg.wait_for_selector('.sheet.on .lwbox', timeout=30000); await pg.wait_for_timeout(1500)
        if 'y3' in url:
            await pg.click('[data-asset]:not([data-asset="*"])'); await pg.wait_for_timeout(2500)
        await pg.wait_for_selector(sel, timeout=20000); el = await pg.query_selector(sel)
        await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(800)
        await pg.evaluate(WATCH); await pg.wait_for_timeout(300); await pg.evaluate("window.__rz = 0")
        bb = await el.bounding_box(); s0 = await pg.evaluate(SNAP, sel); snaps = []
        if mobile:
            cdp = await ctx.new_cdp_session(pg); y = bb['y'] + bb['height'] * 0.5
            await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': bb['x'] + 10, 'y': y}]})
            await pg.wait_for_timeout(700)
            for i in range(30):
                await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': bb['x'] + 10 + (bb['width'] - 20) * i / 29, 'y': y}]}); await pg.wait_for_timeout(30)
                snaps.append(await pg.evaluate(SNAP, sel))
            await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        else:
            for pas in range(2):
                for i in range(40):
                    await pg.mouse.move(bb['x'] + 5 + (bb['width'] - 10) * i / 39, bb['y'] + bb['height'] * (0.3 + 0.4 * pas)); await pg.wait_for_timeout(15)
                    snaps.append(await pg.evaluate(SNAP, sel))
            await pg.mouse.move(5, 5)
        await pg.wait_for_timeout(300); s1 = await pg.evaluate(SNAP, sel); rz = await pg.evaluate("window.__rz")
        keys = ['lgd', 'box', 'ld', 'top', 'doc']
        var = {k: sorted({json.dumps(s[k]) for s in [s0] + snaps + [s1]}) for k in keys}
        changed = {k: v for k, v in var.items() if len(v) > 1}
        texts = len({s['txt'] for s in snaps})
        hint = any(w in json.dumps([s['txt'] for s in snaps + [s0, s1]], ensure_ascii=False) for w in ['포인터', '끌어', 'point or', 'drag'])
        ok = not changed and rz == 0 and not hint and texts > 1 and not errs
        print(json.dumps({'label': label, 'ok': ok, 'changed': changed, 'resize_events': rz, 'legend_texts_seen': texts, 'hint_text': hint, 'idle': s1['txt'][:90], 'errors': errs[:3]}, ensure_ascii=False), flush=True)
        await pg.screenshot(path=f'/tmp/cq/{label}.png'); await b.close(); return ok
async def main():
    base = sys.argv[1]; res = []
    for url, sel, mob, lab, sh in json.loads(sys.argv[2]):
        try: res.append(await run(base + url, sel, mob, lab, sh))
        except Exception as e: print(json.dumps({'label': lab, 'ok': False, 'error': str(e)[:300]})); res.append(False)
    sys.exit(0 if all(res) else 1)
asyncio.run(main())
