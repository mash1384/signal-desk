import asyncio, json
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True, is_mobile=True, locale='ko-KR')
        pg = await ctx.new_page()
        await pg.add_init_script("localStorage.setItem('df-lang','ko');")
        await pg.goto('http://localhost:8001/concepts/r3/', wait_until='networkidle'); await pg.wait_for_timeout(4000)
        await pg.evaluate("""() => { window.__log = []; const ro = new ResizeObserver((es) => es.forEach((e) => __log.push((e.target.className || e.target.tagName) + ':' + Math.round(e.contentRect.width) + 'x' + Math.round(e.contentRect.height) + (e.target.tagName === 'H1' ? ' ' + getComputedStyle(e.target).fontSize + ' ' + e.target.textContent.slice(0, 20) : ''))));
          document.querySelectorAll('.ld, .ld h1, .ch').forEach((e) => ro.observe(e));
          const mo = new MutationObserver((ms) => ms.forEach((m) => __log.push('MUT ' + m.type + ' ' + (m.target.className || m.target.nodeName) + ' ' + (m.attributeName || ''))));
          mo.observe(document.querySelector('.ld h1'), { characterData: true, childList: true, subtree: true, attributes: true }); mo.observe(document.querySelector('.ld'), { attributes: true, childList: true }); }""")
        el = await pg.query_selector('.r3 .bigc .lwbox'); await el.scroll_into_view_if_needed(); await pg.wait_for_timeout(500); await pg.evaluate("__log = []")
        bb = await el.bounding_box(); cdp = await ctx.new_cdp_session(pg); y = bb['y'] + bb['height'] / 2
        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': bb['x'] + 10, 'y': y}]}); await pg.wait_for_timeout(700)
        for i in range(30):
            await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': bb['x'] + 10 + (bb['width'] - 20) * i / 29, 'y': y}]}); await pg.wait_for_timeout(30)
        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []}); await pg.wait_for_timeout(500)
        print(json.dumps(await pg.evaluate("__log"), ensure_ascii=False)[:300])
        for i in range(6):
            await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart' if i == 0 else 'touchMove', 'touchPoints': [{'x': bb['x'] + 10 + 50 * i, 'y': y}]}); await pg.wait_for_timeout(60)
            print(await pg.evaluate("""() => { const w = (s) => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().width) + '/' + e.scrollWidth : '-'; };
              return ['.ld', '.ld .ch', '.ld .mseg', '.ld .cl', '.ld .bigc', '.ld .lgd', '.ld .lwbox', '.ld .tv-lightweight-charts', '.ld .src'].map((s) => s + '=' + w(s)).join('  ') + ' contain=' + getComputedStyle(document.querySelector('.ld .lwbox')).contain + ' cols=' + getComputedStyle(document.querySelector('.ld')).gridTemplateColumns; }"""))
        print(await pg.evaluate("[...document.querySelectorAll('.ld .ch > *')].map(e => e.className + ' ' + Math.round(e.getBoundingClientRect().height)).join(' / ')"))
        await b.close()
asyncio.run(main())
