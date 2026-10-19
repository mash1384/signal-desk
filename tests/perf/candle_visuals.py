"""Capture unchanged representative/detail charts and their requested ranges."""
import argparse
import asyncio
import datetime as dt
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from tests.e2e.server import serve
from tests.perf.vitals import DEVICES, prepare
from tests.perf.visuals import compare


async def capture(args):
    from playwright.async_api import async_playwright
    rows = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**({} if args.channel == 'chromium' else {'channel': args.channel}))
        for stage, site in [('before', args.before), ('after', args.after)]:
            out = args.out / stage
            out.mkdir(parents=True, exist_ok=True)
            with serve(site) as base:
                for device, width in DEVICES.items():
                    for lang in ('ko', 'en'):
                        context, page, offline = await prepare(browser, base, site, args.flash, width, lang)
                        fixed = dt.datetime.fromtimestamp(offline.now, dt.timezone.utc)
                        await page.clock.install(time=fixed)
                        await page.clock.pause_at(fixed)
                        requests, errors = [], []
                        page.on('request', lambda r, bag=requests: bag.append(r.url) if '/klines?' in r.url else None)
                        page.on('pageerror', lambda e, bag=errors: bag.append(str(e)))
                        try:
                            await page.goto(base + 'live/', wait_until='networkidle')
                            await page.evaluate('document.fonts.ready')
                            await page.clock.run_for(5000)
                            await page.wait_for_timeout(300)
                            await page.wait_for_selector('#lead .bigc canvas')
                            await page.locator('#lead').screenshot(path=str(out / ('lead-' + device + '-' + lang + '.png')))
                            await page.locator('#lead [data-id]').first.click()
                            await page.wait_for_selector('#rx .lwc canvas')
                            await page.clock.run_for(1000)
                            await page.evaluate('document.fonts.ready')
                            await page.wait_for_timeout(300)
                            await page.locator('.sheet-in').screenshot(path=str(out / ('detail-' + device + '-' + lang + '.png')))
                            assert not errors and not offline.unmapped, (errors, offline.unmapped)
                            rows.append({'stage': stage, 'device': device, 'lang': lang,
                                         'story': await page.locator('#det h2').inner_text(),
                                         'range_labels': await page.locator('#rx .n').all_text_contents(),
                                         'requests': [parse_qs(urlsplit(url).query) for url in requests]})
                        finally:
                            await context.close()
        await browser.close()
    diff = compare(args.out / 'before', args.out / 'after', args.out / 'diff')
    pairs = [(a, b) for a in rows if a['stage'] == 'before' for b in rows
             if b['stage'] == 'after' and (a['device'], a['lang']) == (b['device'], b['lang'])]
    assert len(pairs) == 4
    for a, b in pairs:
        assert a['story'] == b['story'] and a['range_labels'] == b['range_labels'], ('visible candle range changed', a, b)
    report = {'ok': True, 'rows': rows, 'diff': diff}
    (args.out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': True, 'pairs': len(pairs), 'max_pixel_difference': max(r['over_8_ratio'] for r in diff)}))


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--before', type=Path, required=True)
    p.add_argument('--after', type=Path, required=True)
    p.add_argument('--flash', type=Path, default=Path('.qa/snapshot-r/flash'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--channel', default='chrome')
    asyncio.run(capture(p.parse_args()))


if __name__ == '__main__':
    main()
