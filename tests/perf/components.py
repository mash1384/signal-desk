"""Browser contracts for lazy charts and old article HTML with current assets."""
import argparse
import datetime as dt
import json
from pathlib import Path

from tests.e2e.network import Offline, VENDOR
from tests.e2e.server import serve

GEOMETRY = """() => Object.fromEntries(['header','.logo','#main','h1','footer','nav.tabs'].map(selector => {
  const el=document.querySelector(selector), r=el.getBoundingClientRect(), s=getComputedStyle(el);
  return [selector, {box:[r.x,r.y,r.width,r.height].map(n=>Math.round(n*10)/10),
    font:s.fontFamily,size:s.fontSize,line:s.lineHeight,color:s.color,background:s.backgroundColor}];
}))"""


def check(args):
    from playwright.sync_api import sync_playwright
    rows = []
    with serve(args.site) as base, sync_playwright() as pw:
        browser = pw.chromium.launch(**({} if args.channel == 'chromium' else {'channel': args.channel}))

        def session():
            context = browser.new_context(viewport={'width': 390, 'height': 1000}, timezone_id='Asia/Seoul', reduced_motion='reduce')
            offline = Offline(args.site, args.flash, base)
            context.route('**/*', offline.handle)
            context.add_init_script("localStorage.setItem('df-lang','ko');localStorage.setItem('df-my','[\"BTC\",\"ETH\",\"NVDA\"]')")
            page = context.new_page()
            page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
            return context, page, offline

        context, page, offline = session()
        requests, errors = [], []
        page.on('request', lambda req: requests.append(req.url))
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + 'calendar/', wait_until='networkidle')
        page.wait_for_function("document.querySelector('#hc')?.style.height")
        chart_requests = lambda: [u for u in requests if 'lightweight-charts' in u]
        assert not chart_requests(), ('offscreen chart downloaded eagerly', chart_requests())
        before = page.locator('#hc').bounding_box()
        assert before['height'] == 200
        page.locator('#hc').scroll_into_view_if_needed()
        page.wait_for_function("document.querySelector('#hc canvas')")
        after = page.locator('#hc').bounding_box()
        assert before['height'] == after['height'] and before['width'] == after['width'], (before, after)
        page.locator('[data-range="5y"]').click()
        page.wait_for_timeout(200)
        assert len(chart_requests()) == 1, chart_requests()
        assert not errors and not offline.unmapped, (errors, offline.unmapped)
        rows.append({'check': 'lazy', 'before_requests': 0, 'after_requests': 1, 'height': after['height']})
        context.close()

        context, page, offline = session()
        # Force language changes during each unresolved data stage. The
        # response delay is test-only; actual outgoing requests are counted.
        context.add_init_script("""(() => {
          const original=fetch;window.__themeStarts=[];
          window.fetch=async (...args)=>{
            const url=String(args[0]), slow=/themes\\.json|ticker\\/24hr|klines/.test(url);
            if(slow) __themeStarts.push(url);
            const response=await original(...args);
            if(slow) await new Promise(resolve=>setTimeout(resolve,500));
            return response;
          };
        })();""")
        requests, errors = [], []
        page.on('request', lambda req: requests.append(req.url))
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + 'themes/crypto/', wait_until='domcontentloaded')
        for pattern in ('themes.json', 'interval=1h', 'ticker/24hr'):
            page.wait_for_function('part => __themeStarts.some(url=>url.includes(part))', arg=pattern)
            page.locator('[data-lang="en"]').click()
            page.locator('[data-lang="ko"]').click()
        page.wait_for_function("document.querySelectorAll('#cards .acard:not(.skel)').length === 9")
        page.wait_for_timeout(600)
        counts = {'themes': sum('themes.json' in u for u in requests),
                  'ticker': sum('ticker/24hr' in u for u in requests),
                  'hour_candles': sum('interval=1h' in u for u in requests)}
        assert counts == {'themes': 1, 'ticker': 1, 'hour_candles': 10}, ('repeated theme request', counts)
        assert page.locator('html').get_attribute('lang') == 'ko'
        assert not errors and not offline.unmapped, (errors, offline.unmapped)
        rows.append({'check': 'theme-single-flight', 'requests_during_language_changes': counts})
        context.close()

        for old_site in args.old_site:
            # Match one real article; use its OLD HTML at the NEW site's URL.
            paths = sorted(p for p in (old_site / 'a').glob('*/index.html') if (args.site / p.relative_to(old_site)).is_file())
            assert paths, 'no common article for compatibility check'
            old = paths[-1]
            path = str(old.relative_to(old_site)).removesuffix('index.html')
            old_html = old.read_text()
            for lang in ('ko', 'en'):
                context, page, offline = session()
                context.add_init_script("localStorage.setItem('df-lang',%s)" % json.dumps(lang))
                context.route(base + path, lambda route, request, html=old_html: route.fulfill(body=html, content_type='text/html'))
                errors = []
                page.on('pageerror', lambda error, bag=errors: bag.append(str(error)))
                page.goto(base + path, wait_until='networkidle')
                page.evaluate('document.fonts.ready')
                assert page.locator('h1').inner_text().strip()
                assert page.locator('time[data-ts]').count() > 0
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert page.locator('html').get_attribute('lang') == lang
                other = 'en' if lang == 'ko' else 'ko'
                page.locator('[data-lang="%s"]' % other).click()
                assert page.locator('html').get_attribute('lang') == other, 'language switch failed for old HTML'
                page.evaluate('document.fonts.ready')
                expected_context, expected_page, _ = session()
                expected_context.add_init_script("localStorage.setItem('df-lang',%s)" % json.dumps(other))
                expected_page.goto(base + path, wait_until='networkidle')
                expected_page.evaluate('document.fonts.ready')
                actual, expected = page.evaluate(GEOMETRY), expected_page.evaluate(GEOMETRY)
                assert actual == expected, ('old HTML geometry/style changed', actual, expected)
                expected_context.close()
                axe = offline.manifest['https://cdn.jsdelivr.net/npm/axe-core@4.10.3/axe.min.js']['file']
                page.add_script_tag(path=str(VENDOR / axe))
                violations = page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations")
                assert not violations, violations
                assert not errors and not offline.unmapped, (errors, offline.unmapped)
                rows.append({'check': 'old-html-new-assets', 'source': str(old_site), 'article': path, 'lang': lang, 'axe': 0, 'geometry_matches_current': True})
                context.close()
        browser.close()
    return rows


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--flash', type=Path, default=Path('.qa/snapshot-r/flash'))
    parser.add_argument('--old-site', type=Path, action='append', default=[])
    parser.add_argument('--channel', default='chrome')
    parser.add_argument('--output', type=Path, default=Path('.qa/perf-components.json'))
    args = parser.parse_args()
    rows = check(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'ok': True, 'rows': rows}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == '__main__':
    main()
