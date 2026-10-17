import asyncio, json, sys
from playwright.async_api import async_playwright
BASE = sys.argv[1]
async def main():
    bad = []
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        for mob in (False, True):
            ctx = await b.new_context(viewport={'width': 390, 'height': 844} if mob else {'width': 1440, 'height': 900}, device_scale_factor=2 if mob else 1, has_touch=mob, is_mobile=mob)
            pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append('pageerror ' + str(e)))
            pg.on('console', lambda m: m.type == 'error' and errs.append('console ' + m.text))
            pg.on('requestfailed', lambda r: errs.append('reqfail ' + r.url[:100]))
            tag = 'mob' if mob else 'pc'
            await pg.goto(BASE + 'map/', wait_until='networkidle'); await pg.wait_for_timeout(500)
            if not pg.url.endswith('/themes/crypto/'): bad.append(f'{tag} map redirect -> {pg.url}')
            await pg.goto(BASE + 'listings/?x=1', wait_until='networkidle'); await pg.wait_for_timeout(500)
            if '/themes/crypto/' not in pg.url: bad.append(f'{tag} listings redirect -> {pg.url}')
            await pg.wait_for_selector('#flow .lwbox', timeout=20000); await pg.wait_for_selector('.acard:not(.skel)', timeout=20000); await pg.wait_for_timeout(1500)
            info = await pg.evaluate("""() => ({ title: document.title, sel: document.querySelector('.ttabs [aria-selected=true]')?.textContent, cards: document.querySelectorAll('.acard:not(.skel)').length,
               stories: document.querySelectorAll('#stories .srow').length, chg: document.querySelectorAll('.sbox li').length, secs: document.querySelectorAll('.sec-b').length,
               navcur: [...document.querySelectorAll('[aria-current=page]')].map(a => a.getAttribute('href')), flowH: Math.round(document.querySelector('#flow .lwbox').getBoundingClientRect().height),
               overflowX: document.documentElement.scrollWidth > innerWidth })""")
            print(tag, 'crypto', json.dumps(info, ensure_ascii=False))
            if not (info['cards'] >= 3 and info['stories'] >= 3 and info['secs'] >= 1 and info['flowH'] > 150) or info['overflowX']: bad.append(f'{tag} crypto content {info}')
            await pg.screenshot(path=f'/tmp/cq/th_{tag}_crypto.png', full_page=True)
            await pg.click('.ttabs [data-theme=nasdaq]'); await pg.wait_for_timeout(2500)
            i2 = await pg.evaluate("() => ({ url: location.pathname, sel: document.querySelector('.ttabs [aria-selected=true]')?.dataset.theme, title: document.title, cards: document.querySelectorAll('.acard:not(.skel)').length })")
            print(tag, 'nasdaq', i2)
            if not (i2['url'].endswith('/themes/nasdaq/') and i2['sel'] == 'nasdaq'): bad.append(f'{tag} tab {i2}')
            await pg.go_back(); await pg.wait_for_timeout(1500)
            i3 = await pg.evaluate("() => ({ url: location.pathname, sel: document.querySelector('.ttabs [aria-selected=true]')?.dataset.theme })"); print(tag, 'back', i3)
            if i3['sel'] != 'crypto': bad.append(f'{tag} back {i3}')
            await pg.click('#stories .srow'); await pg.wait_for_selector('.sheet.on', timeout=5000); await pg.wait_for_timeout(3000)
            sh = await pg.evaluate("() => ({ h: document.querySelector('#det h2, #det h3, #det .hl')?.textContent?.slice(0, 50), rx: document.querySelectorAll('#det .lwbox').length, txt: document.querySelector('#det').textContent.length })"); print(tag, 'sheet', sh)
            if sh['txt'] < 50: bad.append(f'{tag} sheet {sh}')
            await pg.screenshot(path=f'/tmp/cq/th_{tag}_sheet.png')
            await pg.keyboard.press('Escape')
            await pg.click('.lang [data-lang=ko]'); await pg.wait_for_timeout(1200)
            ko = await pg.evaluate("() => document.querySelector('#app').textContent.includes('지난 24시간')"); print(tag, 'ko', ko)
            if not ko: bad.append(f'{tag} ko')
            await pg.screenshot(path=f'/tmp/cq/th_{tag}_ko.png', full_page=True)
            for k in ('econ', 'ai'):
                await pg.goto(BASE + f'themes/{k}/', wait_until='networkidle'); await pg.wait_for_selector('#flow .lwbox', timeout=20000); await pg.wait_for_timeout(1500)
                n = await pg.evaluate("() => ({ sel: document.querySelector('.ttabs [aria-selected=true]')?.dataset.theme, stories: document.querySelectorAll('#stories .srow').length, cards: document.querySelectorAll('.acard:not(.skel)').length })"); print(tag, k, n)
                if n['sel'] != k or n['stories'] < 1: bad.append(f'{tag} {k} {n}')
            errs = [e for e in errs if 'favicon' not in e]
            print(tag, 'errors', errs[:6])
            if errs: bad.append(f'{tag} errors {errs[:3]}')
            await ctx.close()
        await b.close()
    print('BAD', bad) if bad else print('ALL OK')
    sys.exit(1 if bad else 0)
asyncio.run(main())
