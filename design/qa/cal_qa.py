"""일정(경제지표) 후보 검사: 지표 고르기 · 자산 · 기간 · 언어 · 320px · 오류. 실행: python cal_qa.py <주소/> c1 c2 c3"""
import asyncio, json, sys
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
                await pg.goto(base + name + '/', wait_until='networkidle'); await pg.wait_for_selector('#detail .dt', timeout=20000)
                tag = f'{name}@{w}'
                # 지표 고르기
                await pg.click('[data-ind="claims"]'); await pg.wait_for_timeout(400)
                k = await pg.evaluate("document.querySelector('#detail .dt')?.dataset.k")
                if k != 'claims': bad.append(f'{tag} select {k}')
                # 자산 · 기간
                await pg.click('#detail [data-asset="BTC-USD"]'); await pg.wait_for_timeout(300)
                fl = await pg.evaluate("document.getElementById('fl').textContent")
                if '비트코인' not in fl and 'Bitcoin' not in fl: bad.append(f'{tag} asset {fl[:60]}')
                await pg.click('#detail [data-range="all"]'); await pg.wait_for_timeout(300)
                hc = await pg.evaluate("Math.round(document.getElementById('hc').getBoundingClientRect().height)")
                fan = await pg.evaluate("Math.round(document.getElementById('fan').getBoundingClientRect().height)")
                ox = await pg.evaluate("document.documentElement.scrollWidth > innerWidth")
                if ox: bad.append(f'{tag} overflowX')
                if hc < 150 or fan < 150: bad.append(f'{tag} chart heights {hc} {fan}')
                # 영어
                await pg.click('.lang [data-lang=en]'); await pg.wait_for_timeout(500)
                en = await pg.evaluate("document.querySelector('#detail').textContent")
                if 'What it means' not in en and 'When it looked like this before' not in en: bad.append(f'{tag} english')
                hangul = await pg.evaluate("[...document.querySelectorAll('#app *')].filter(e => e.children.length === 0 && /[가-힣]/.test(e.textContent)).map(e => e.textContent.slice(0, 40)).slice(0, 5)")
                if hangul: bad.append(f'{tag} hangul in EN {hangul}')
                await pg.click('.lang [data-lang=ko]'); await pg.wait_for_timeout(300)
                if w == 320: await pg.screenshot(path=f'/tmp/cq/{name}_320.png', full_page=True)
                print(tag, 'ok' if not errs else errs[:3], 'hc', hc, 'fan', fan, 'ox', ox, flush=True)
                if errs: bad.append(f'{tag} errors {errs[:2]}')
                await pg.close()
            await ctx.close()
        await b.close()
    print('BAD', bad) if bad else print('ALL OK'); sys.exit(1 if bad else 0)
asyncio.run(main())
