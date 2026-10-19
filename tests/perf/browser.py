"""Offline performance contracts; separate from the short deployment gate."""
from collections import Counter
import argparse
import asyncio
import datetime as dt
import json
from pathlib import Path
import traceback
from urllib.parse import urlsplit

from tests.e2e.network import Offline
from tests.e2e.server import serve
from tests.e2e.test_polling import HIDE
from tests.perf.vitals import measure, is_data
from tests.perf.wire import serve_wire


def polling(args):
    from playwright.sync_api import sync_playwright
    rows = []
    with serve(args.site) as base, sync_playwright() as pw:
        browser = pw.chromium.launch(**({} if args.channel == 'chromium' else {'channel': args.channel}))
        for mode in ('modern', 'legacy', 'error', 'malformed', 'disconnect'):
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
            offline = Offline(args.site, args.flash, base, live_mode=mode)
            context.route('**/*', offline.handle)
            context.add_init_script("localStorage.setItem('df-lang','ko');localStorage.setItem('df-my','[\"BTC\",\"ETH\",\"NVDA\"]')")
            page = context.new_page()
            urls, errors = [], []
            page.on('request', lambda req, bag=urls: bag.append(req.url))
            page.on('pageerror', lambda error, bag=errors: bag.append(str(error)))
            fixed = dt.datetime.fromtimestamp(offline.now, dt.timezone.utc)
            page.clock.install(time=fixed)
            page.clock.pause_at(fixed)

            def worker_urls(bag=urls):
                return [u for u in bag if urlsplit(u).hostname == 'signal-scheduler.mash1384.workers.dev']

            steps = []

            pending = set()
            page.on('request', lambda r, bag=pending: bag.add(r) if urlsplit(r.url).hostname == 'signal-scheduler.mash1384.workers.dev' else None)
            page.on('requestfinished', lambda r, bag=pending: bag.discard(r))
            page.on('requestfailed', lambda r, bag=pending: bag.discard(r))

            def advance(minutes, target=page, steps=steps, pending=pending):
                for _ in range(minutes * 2):
                    target.clock.run_for(30000)
                    # 진행 중인 Worker 요청이 끝난 뒤 다음 30초로: 가짜 시계가 실제 응답보다 먼저 8초 제한을 넘겨 끊지 않게
                    for _ in range(100):
                        target.wait_for_timeout(50)
                        if not pending:
                            break
                    steps.append(len(worker_urls()))

            try:
                page.goto(base + 'live/', wait_until='networkidle')
                page.wait_for_function("!!document.querySelector('#ps .pv') && !['', '–', '—'].includes(document.querySelector('#ps .pv').textContent.trim()) && document.querySelectorAll('#grid [data-id]').length > 0")
                # 처음 요청이 다 나간 뒤에 센다: 컴퓨터가 바쁘면 첫 요청이 늦게 나가 '보이는 동안' 수에 섞였다(고장 주입 실행에서 21/20)
                stable, last_n = 0, -1
                for _ in range(50):
                    page.wait_for_timeout(100)
                    n = len(worker_urls())
                    stable = stable + 1 if n == last_n else 0
                    last_n = n
                    if stable >= 5:
                        break
                initial = len(worker_urls())
                minutes = 10 if mode in ('modern', 'legacy') else 1
                advance(minutes)
                visible = len(worker_urls()) - initial
                assert visible > 0, 'the visible tab stopped refreshing'
                if mode == 'modern':
                    assert visible <= 2 * minutes, ('Worker budget exceeded', visible, minutes, dict(Counter(urlsplit(u).path for u in worker_urls()[initial:])), 'per-step totals', steps, 'initial', initial)
                    assert all(urlsplit(u).path == '/live' for u in worker_urls()), worker_urls()
                else:
                    assert sum(urlsplit(u).path == '/live' for u in worker_urls()) == 1, 'failed feature probe must not repeat'
                    assert sum(urlsplit(u).path == '/flash' for u in worker_urls()) >= 2, 'legacy flash fallback absent'
                    assert sum(urlsplit(u).path == '/market' for u in worker_urls()) >= 2, 'legacy quote fallback absent'
                page.evaluate(HIDE, True)
                before_hidden = len(worker_urls())
                advance(10)
                hidden = len(worker_urls()) - before_hidden
                assert hidden == 0, ('hidden tab polled', hidden)
                page.evaluate(HIDE, False)
                page.wait_for_timeout(400)
                catchup = len(worker_urls()) - before_hidden
                # 404(legacy) · 형식 오류(malformed)는 묶음 요청을 끈 채로 기존 경로 3건, 일시 실패(error · disconnect)는 5분이 지나 묶음 요청을 1번 다시 시도 + 기존 3건
                expect = {'modern': 1, 'legacy': 3, 'malformed': 3, 'error': 4, 'disconnect': 4}[mode]
                assert catchup == expect, ('catch-up duplicated/missing', mode, catchup)
                assert not errors and not offline.unmapped, (errors, offline.unmapped)
                rows.append({'mode': mode, 'initial': initial, 'minutes': minutes, 'visible': visible,
                             'per_minute': visible / minutes, 'hidden_10_minutes': hidden, 'catchup': catchup})
                print(json.dumps(rows[-1]), flush=True)
            finally:
                context.close()
        browser.close()
    return rows


async def delayed_and_blocked(args):
    from playwright.async_api import async_playwright
    rows = []
    with serve_wire(args.site, args.flash) as base:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(**({} if args.channel == 'chromium' else {'channel': args.channel}))
            if args.scenario in ('all', 'delay'):
                for lang in ('ko', 'en'):
                    for delay in (1, 2, 3):
                        row = await measure(browser, base, 'live/', 'mobile', args.site, args.flash, lang, delay=delay)
                        assert not row['errors'], row['errors']
                        assert row['cls'] <= .1, ('delayed live CLS', lang, delay, row['cls'])
                        rows.append({'check': 'delay', 'lang': lang, 'seconds': delay, 'cls': row['cls'], 'lcp_ms': row['lcp_ms']})
                        print(json.dumps(rows[-1]), flush=True)
            if args.scenario in ('all', 'blocked'):
                for name in ('live/', 'brief/', 'calendar/'):
                    for device in ('pc', 'mobile'):
                        for lang in ('ko', 'en'):
                            row = await measure(browser, base, name, device, args.site, args.flash, lang, block=True)
                            unexpected = [e for e in row['errors'] if not (e['kind'] == 'requestfailed' and is_data(e.get('url') or '') and e['error'].split('.')[0] == 'net::ERR_BLOCKED_BY_CLIENT')]
                            assert not unexpected, unexpected
                            assert row['content'] and all(row['content'].values()), ('blank prerender', name, device, lang, row['content'])
                            rows.append({'check': 'blocked', 'page': name, 'device': device, 'lang': lang, 'content': row['content']})
                            print(json.dumps(rows[-1]), flush=True)
            await browser.close()
    return rows


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--site', type=Path, required=True)
    p.add_argument('--flash', type=Path, default=Path('.qa/snapshot-r/flash'))
    p.add_argument('--output', type=Path, default=Path('.qa/perf-browser.json'))
    p.add_argument('--channel', default='chrome')
    p.add_argument('--scenario', choices=('all', 'polling', 'delay', 'blocked'), default='all')
    args = p.parse_args()
    report = {'ok': False, 'scenario': args.scenario, 'results': []}
    try:
        if args.scenario in ('all', 'polling'):
            report['results'].extend(polling(args))
        if args.scenario in ('all', 'delay', 'blocked'):
            report['results'].extend(asyncio.run(delayed_and_blocked(args)))
        assert report['results'], 'no checks ran'
        report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    return int(not report['ok'])


if __name__ == '__main__':
    raise SystemExit(main())
