"""정리(줄기) 후보 검사: 거르기 · 근거 번호 → 소식 창 · 소식 모두 보기 · 영어 · 320px · 오류. 실행: python brief_qa.py <주소/> br1 br2 br3"""
import asyncio, sys
from playwright.async_api import async_playwright
async def main():
    base, pages, bad = sys.argv[1], sys.argv[2:], []
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        for w in (1440, 390, 320):
            mob = w < 900
            ctx = await b.new_context(viewport={'width': w, 'height': 844 if mob else 900}, device_scale_factor=2 if mob else 1, has_touch=mob, is_mobile=mob, locale='ko-KR')
            for name in pages:
                pg = await ctx.new_page(); errs = []
                pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
                await pg.goto(base + name + '/', wait_until='networkidle'); await pg.wait_for_selector('.th', timeout=20000)
                tag = f'{name}@{w}'
                n_all = await pg.evaluate("document.querySelectorAll('.th').length")
                # 거르기: 크립토
                await pg.click('[data-f="crypto"]'); await pg.wait_for_timeout(300)
                cnt = await pg.evaluate("+document.querySelector('[data-f=crypto] .c').textContent")
                if not (await pg.evaluate("document.querySelector('[data-f=crypto]').getAttribute('aria-pressed')") == 'true'): bad.append(f'{tag} filter state')
                await pg.click('[data-f="all"]'); await pg.wait_for_timeout(300)
                # 근거 번호 → 소식 창
                await pg.click('.th .ref'); await pg.wait_for_selector('.sheet.on', timeout=5000); await pg.wait_for_timeout(500)
                det = await pg.evaluate("document.querySelector('#det').textContent.length")
                if det < 30: bad.append(f'{tag} sheet empty')
                await pg.keyboard.press('Escape'); await pg.wait_for_timeout(400)
                # 소식 모두 보기
                if name != 'br2':
                    await pg.click('.th details summary'); await pg.wait_for_timeout(300)
                li = await pg.evaluate("document.querySelectorAll('.th details[open] .sts li').length")
                if li < 3: bad.append(f'{tag} story list {li}')
                ox = await pg.evaluate("document.documentElement.scrollWidth > innerWidth")
                if ox: bad.append(f'{tag} overflowX')
                # 영어
                await pg.click('.lang [data-lang=en]'); await pg.wait_for_timeout(500)
                hangul = await pg.evaluate("[...document.querySelectorAll('#app .th h3, #app .sofar p, #app .today p, #app .ph')].filter(e => /[가-힣]/.test(e.textContent)).map(e => e.textContent.slice(0, 40)).slice(0, 3)")
                if hangul: bad.append(f'{tag} hangul in EN {hangul}')
                await pg.click('.lang [data-lang=ko]'); await pg.wait_for_timeout(300)
                print(tag, 'threads', n_all, 'crypto', cnt, 'sheet', det, 'list', li, 'ox', ox, 'errors', errs[:2], flush=True)
                if errs: bad.append(f'{tag} errors {errs[:2]}')
                await pg.close()
            await ctx.close()
        await b.close()
    print('BAD', bad) if bad else print('ALL OK'); sys.exit(1 if bad else 0)
asyncio.run(main())
