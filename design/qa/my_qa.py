"""내 자산(/my/)·라이브 가격 띠·메뉴 5칸·옛 /me/ 이동 검사. 실행: python my_qa.py <사이트 주소/>"""
import asyncio, json, sys
from playwright.async_api import async_playwright
BASE = sys.argv[1]
async def main():
    bad = []
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        for mob in (False, True):
            tag = 'mob' if mob else 'pc'
            ctx = await b.new_context(viewport={'width': 390, 'height': 844} if mob else {'width': 1440, 'height': 900}, device_scale_factor=2 if mob else 1, has_touch=mob, is_mobile=mob)
            pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append('pageerror ' + str(e)))
            pg.on('console', lambda m: m.type == 'error' and errs.append('console ' + m.text))
            # 1) 빈 상태 → 인기 자산 고르기 → 내 피드
            await pg.goto(BASE + 'my/', wait_until='networkidle'); await pg.wait_for_selector('.empty-my', timeout=20000)
            for s in ('BTC', 'NVDA', 'NQ=F'):
                btn = pg.locator(f'.empty-my [data-my="{s}"]')
                if await btn.count(): await btn.first.click()
                else: bad.append(f'{tag} no popular {s}')
            await pg.click('.empty-my [data-go]'); await pg.wait_for_timeout(5000)
            st = await pg.evaluate("""() => ({ my: JSON.parse(localStorage.getItem('df-my') || '[]'), empty: !!document.querySelector('.empty-my'), rows: document.querySelectorAll('.srows .srow').length,
              wl: document.querySelectorAll('.wl .wr').length, dsum: !!document.querySelector('.dsum'), cur: [...document.querySelectorAll('[aria-current=page]')].map(a => a.getAttribute('href')),
              tabs: document.querySelectorAll('.tabs a').length, nav: document.querySelectorAll('.nav a').length, ox: document.documentElement.scrollWidth > innerWidth })""")
            print(tag, 'my', json.dumps(st, ensure_ascii=False))
            if st['empty'] or st['wl'] != 3 or st['rows'] < 1 or not st['dsum'] or st['tabs'] != 5 or st['nav'] != 5 or st['ox'] or not all(h.endswith('/my/') for h in st['cur']): bad.append(f'{tag} my {st}')
            await pg.screenshot(path=f'/tmp/cq/my_{tag}.png', full_page=True)
            # 2) 고르기 창: ETH 추가 후 닫기
            await pg.click('[data-pick]'); await pg.wait_for_selector('#pickdlg[open]', timeout=5000)
            await pg.click('#pickdlg [data-my="ETH"]'); await pg.click('#pickdlg [data-close-pick]'); await pg.wait_for_timeout(3000)
            n = await pg.evaluate("() => document.querySelectorAll('.wl .wr').length"); print(tag, 'after pick', n)
            if n != 4: bad.append(f'{tag} picker {n}')
            # 3) 새로 고침해도 남아 있나
            await pg.reload(wait_until='networkidle'); await pg.wait_for_timeout(3000)
            n = await pg.evaluate("() => document.querySelectorAll('.wl .wr').length"); print(tag, 'reload', n)
            if n != 4: bad.append(f'{tag} reload {n}')
            # 4) 라이브: 가격 띠 · 내 자산 칸 · 내 자산만
            await pg.goto(BASE + 'live/', wait_until='networkidle'); await pg.wait_for_selector('.pi', timeout=20000); await pg.wait_for_timeout(4000)
            lv = await pg.evaluate("""() => ({ strip: document.querySelectorAll('#ps .pi').length, prices: [...document.querySelectorAll('#ps .pv')].map(e => e.textContent).join(' '), myonly: !document.getElementById('myonly').hidden,
              myb: document.querySelectorAll('#myb .myl li').length, mylink: document.querySelector('#myb h3 a')?.getAttribute('href'), cards: document.querySelectorAll('#grid .cd').length,
              cur: [...document.querySelectorAll('[aria-current=page]')].map(a => a.getAttribute('href')), ox: document.documentElement.scrollWidth > innerWidth })""")
            print(tag, 'live', json.dumps(lv, ensure_ascii=False))
            if lv['strip'] != 6 or '–' in lv['prices'] and lv['prices'].count('–') > 2 or not lv['myonly'] or lv['cards'] < 1 or lv['ox'] or not all(h.endswith('/live/') for h in lv['cur']): bad.append(f'{tag} live {lv}')
            if not mob and (lv['myb'] != 4 or not (lv['mylink'] or '').endswith('/my/')): bad.append(f'{tag} live rail {lv}')
            before = lv['cards']; await pg.click('#myonly'); await pg.wait_for_timeout(800)
            after = await pg.evaluate("() => document.querySelectorAll('#grid .cd').length"); print(tag, 'myonly', before, '->', after)
            await pg.screenshot(path=f'/tmp/cq/live_{tag}.png')
            # 가격 띠 ☆ 로 빼고 넣기
            await pg.click('#ps [data-my="ETH"]'); await pg.wait_for_timeout(300)
            has = await pg.evaluate("() => JSON.parse(localStorage.getItem('df-my')).includes('ETH')"); print(tag, 'star off -> has ETH', has)
            if has: bad.append(f'{tag} star toggle')
            # 5) 테마 메뉴 5칸
            await pg.goto(BASE + 'themes/ai/', wait_until='networkidle'); await pg.wait_for_timeout(1500)
            th = await pg.evaluate("() => ({ tabs: document.querySelectorAll('.tabs a').length, cur: [...document.querySelectorAll('[aria-current=page]')].map(a => a.getAttribute('href')) })"); print(tag, 'themes nav', th)
            if th['tabs'] != 5 or not all(h.endswith('/themes/') for h in th['cur']): bad.append(f'{tag} themes nav {th}')
            errs = [e for e in errs if 'favicon' not in e]; print(tag, 'errors', errs[:5])
            if errs: bad.append(f'{tag} errors {errs[:3]}')
            await ctx.close()
        # 6) 옛 /me/ 목록을 새 페이지가 가져오나
        ctx = await b.new_context(); pg = await ctx.new_page()
        await pg.add_init_script("if (!sessionStorage.getItem('x')) { sessionStorage.setItem('x', 1); localStorage.setItem('signal-watch', JSON.stringify(['BTC', 'SOL'])); }")
        await pg.goto(BASE + 'me/', wait_until='networkidle'); await pg.wait_for_timeout(4000)
        me = await pg.evaluate("() => ({ url: location.pathname, wl: [...document.querySelectorAll('.wl .wr .nm b')].map(e => e.textContent) })"); print('me ->', me)
        if not me['url'].endswith('/my/') or sorted(me['wl']) != ['BTC', 'SOL']: bad.append(f'me {me}')
        await b.close()
    print('BAD', bad) if bad else print('ALL OK')
    sys.exit(1 if bad else 0)
asyncio.run(main())
