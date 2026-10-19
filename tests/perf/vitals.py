"""Three cold loads per page/device, CDP transfer sizes and buffered Web Vitals.

Local mode uses the same Offline transport as functional QA. Live mode only
performs public browser GETs and is never used as a deterministic CI baseline.
python -m tests.perf.vitals --site BUILD --flash SNAPSHOT --output REPORT
python -m tests.perf.vitals --live https://mash1384.github.io/signal-desk/ --output REPORT
"""
import argparse
import asyncio
from contextlib import ExitStack
import datetime as dt
import json
from pathlib import Path
import re
import statistics
import time
from urllib.parse import quote, urlsplit
import urllib.request

from tests.e2e.network import Offline
from tests.e2e.test_matrix import CONTENT, path_for
from tests.perf.wire import serve_wire

PAGES = ['', 'live/', 'my/', 'themes/crypto/', 'brief/', 'calendar/', 'daily/', 'about/']
DEVICES = {'pc': 1440, 'mobile': 390}
METRICS = ('lcp_ms', 'cls', 'requests', 'bytes', 'font_files', 'font_bytes', 'js_bytes')
OBSERVE = """(() => {
  window.__perf = {lcp:0, shifts:[], lcpElement:null};
  new PerformanceObserver(list => { for (const e of list.getEntries()) {
    __perf.lcp = e.startTime; __perf.lcpElement = e.element?.outerHTML?.slice(0,300) || e.url;
  }}).observe({type:'largest-contentful-paint',buffered:true});
  new PerformanceObserver(list => { for (const e of list.getEntries()) if (!e.hadRecentInput)
    __perf.shifts.push({at:e.startTime,value:e.value,sources:(e.sources||[]).map(s=>s.node?.id||s.node?.className||s.node?.nodeName)});
  }).observe({type:'layout-shift',buffered:true});
})();"""


def cls_value(shifts):
    """Maximum session window, at most 5s with gaps below 1s (not lifetime sum)."""
    best = total = 0.0
    first = last = None
    for entry in shifts:
        now = entry['at']
        if first is None or now - last >= 1000 or now - first >= 5000:
            first, total = now, 0.0
        total += entry['value']
        best, last = max(best, total), now
    return best


def is_data(url):
    u = urlsplit(url)
    return u.hostname in ('raw.githubusercontent.com', 'signal-scheduler.mash1384.workers.dev', 'data-api.binance.vision') or u.path.endswith('.json')


class Reply:
    """Adapt the existing synchronous offline fixtures to async interception."""
    def __init__(self, request):
        self.request, self.payload = request, None

    def continue_(self):
        self.payload = None

    def fulfill(self, **values):
        self.payload = values


async def transport(context, offline, delay=0, block=False, wire=False):
    async def handle(route):
        u = urlsplit(route.request.url)
        if u.hostname == 'signal-scheduler.mash1384.workers.dev' and u.path == '/e':   # 익명 통계 전송 — 측정에는 가짜 응답
            await route.fulfill(status=204, body=b'', headers={'access-control-allow-origin': '*'})
            return
        data = is_data(route.request.url)
        if data and block:
            await route.abort('blockedbyclient')
            return
        if data and delay:
            await asyncio.sleep(delay)
        if wire:
            target = route.request.url
            if urlsplit(target).netloc != offline.host:
                target = 'https://' + offline.host + '/_fixture?url=' + quote(target, safe='')
            await route.continue_(url=target)
            return
        reply = Reply(route.request)
        offline.handle(reply)
        if reply.payload is None:
            await route.continue_()
        else:
            await route.fulfill(**reply.payload)
    await context.route('**/*', handle)


async def prepare(browser, base, site=None, flash=None, width=390, lang='ko', delay=0, block=False, wire=False):
    context = await browser.new_context(viewport={'width': width, 'height': 1000}, device_scale_factor=1,
                                        locale='en-US', timezone_id='Asia/Seoul', service_workers='block', reduced_motion='reduce', ignore_https_errors=bool(site))
    await context.add_init_script("localStorage.setItem('df-lang', %s);localStorage.setItem('df-my',JSON.stringify(['BTC','ETH','NVDA']));" % json.dumps(lang))
    page = await context.new_page()
    offline = Offline(site, flash, base) if site else None
    if offline:
        await transport(context, offline, delay, block, wire)
        await page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    else:
        async def public_get_only(route):
            host = urlsplit(route.request.url).hostname
            if route.request.method != 'GET' or host in ('api.github.com', 'api.deepseek.com', 'api.telegram.org', 't.me'):
                await route.abort('blockedbyclient')
            else:
                await route.continue_()
        await context.route('**/*', public_get_only)
    return context, page, offline


class EmptyMeasurement(ValueError):
    """측정 도구가 값을 못 받음(화면 내용은 있음)."""


async def measure(browser, base, name, device, site=None, flash=None, lang='ko', delay=0, block=False, throttle=True, daily_path=None):
    context, page, offline = await prepare(browser, base, site, flash, DEVICES[device], lang, delay, block, wire=bool(site))
    requests, errors = {}, []
    cdp = await context.new_cdp_session(page)
    await cdp.send('Network.enable')
    await cdp.send('Network.setCacheDisabled', {'cacheDisabled': True})
    if device == 'mobile' and throttle:
        await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 150, 'downloadThroughput': 200000,
                                                           'uploadThroughput': 93750, 'connectionType': 'cellular3g'})
    def sent(e):
        requests[e['requestId']] = {'url': e['request']['url'], 'type': e.get('type'), 'bytes': 0, 'finished': False}
    def received(e):
        row = requests.setdefault(e['requestId'], {})
        row.update(type=e['type'], status=e['response']['status'])
    def finished(e):
        requests[e['requestId']].update(bytes=e['encodedDataLength'], finished=True)
    cdp.on('Network.requestWillBeSent', sent)
    cdp.on('Network.responseReceived', received)
    cdp.on('Network.loadingFinished', finished)
    def failed(e):
        row = requests.get(e['requestId'], {})
        row['finished'] = True
        # Removing the reduced-motion intro intentionally cancels its video.
        if e['errorText'] != 'net::ERR_ABORTED' or row.get('type') != 'Media':
            errors.append({'kind': 'requestfailed', 'url': row.get('url'), 'error': e['errorText']})
    cdp.on('Network.loadingFailed', failed)
    page.on('pageerror', lambda e: errors.append({'kind': 'pageerror', 'error': str(e)}))
    await page.add_init_script(OBSERVE)
    try:
        path = path_for(name, site) if site else daily_path if name == 'daily/' else name
        await page.goto(base + path, wait_until='networkidle', timeout=60000)
        await page.evaluate('document.fonts.ready')
        if not block:
            await page.wait_for_function('targets => Object.entries(targets).every(([s,n]) => document.querySelectorAll(s).length >= n)', arg=CONTENT[name], timeout=15000)
        # Scroll-controlled/paused animations may never resolve finished.
        # Observe a fixed settling window, independent of animation state.
        await page.wait_for_timeout(2000)
        await page.wait_for_timeout(1000)
        # fonts.ready/networkidle can resolve before a delayed module inserts
        # more text. Require all CDP requests to finish before adding bytes.
        deadline, quiet = time.monotonic() + 25, time.monotonic()
        while time.monotonic() < deadline:
            pending = [r['url'] for r in requests.values() if not r['finished'] and r.get('type') != 'Media']
            if pending:
                quiet = time.monotonic()
            elif time.monotonic() - quiet >= 0.8:
                break
            await page.wait_for_timeout(100)
        else:
            errors.append({'kind': 'unfinished', 'urls': pending})
        await page.evaluate('document.fonts.ready')
        await page.wait_for_timeout(100)
        observed = await page.evaluate('window.__perf')
        rows = list(requests.values())
        http_errors = [{'kind': 'http', 'url': r['url'], 'status': r['status']} for r in rows if r.get('status', 0) >= 400]
        errors.extend(http_errors)
        if offline and offline.unmapped:
            errors.append({'kind': 'unmapped', 'urls': offline.unmapped})
        content = {selector: await page.locator(selector).count() for selector in CONTENT[name]}
        # 맞춤 대체 글꼴(pf.js) 상태: 어떤 기기 글꼴을 찾았고 실제로 불러졌는지
        observed['pf'] = await page.evaluate("[document.documentElement.dataset.pf||'', document.documentElement.dataset.pfs||'', ...[...document.fonts].filter(f=>f.family.includes('PF')).map(f=>f.status)]")
        result = {'page': name, 'path': path, 'device': device, 'width': DEVICES[device], 'lang': lang,
                  'lcp_ms': observed['lcp'], 'cls': cls_value(observed['shifts']), 'requests': len(rows),
                  'bytes': sum(r['bytes'] for r in rows), 'font_files': sum(r.get('type') == 'Font' for r in rows),
                  'font_bytes': sum(r['bytes'] for r in rows if r.get('type') == 'Font'),
                  'js_bytes': sum(r['bytes'] for r in rows if r.get('type') == 'Script'),
                  'content': content, 'errors': errors, 'resources': rows, 'observed': observed}
        # 테스트용 로컬 서버와의 연결 자체가 끊긴 회차(net::ERR_*)는 제품이 아니라 측정 장비 문제 — 다시 잰다(기록 남김).
        # 제품의 HTTP 오류(4xx/5xx, kind=http)는 여기에 해당하지 않는다
        # 연결 계열 오류만(일부러 막은 요청 ERR_BLOCKED_BY_CLIENT 는 '데이터 막힘' 시험의 정상 결과라 제외)
        infra = ('net::ERR_TOO_MANY_RETRIES', 'net::ERR_CONNECTION_RESET', 'net::ERR_CONNECTION_REFUSED', 'net::ERR_CONNECTION_CLOSED',
                 'net::ERR_EMPTY_RESPONSE', 'net::ERR_SSL_PROTOCOL_ERROR', 'net::ERR_TIMED_OUT')
        if not block and errors and all(e.get('kind') == 'requestfailed' and str(e.get('error', '')).startswith(infra)
                                        and urlsplit(e.get('url', '')).hostname in ('127.0.0.1', 'localhost') for e in errors):
            raise EmptyMeasurement('local test server connection failed: %s %s %s' % (name, device, errors[0]['error']))
        if not result['lcp_ms'] or not result['bytes']:
            empty = [k for k in ('lcp_ms', 'bytes') if not result[k]]
            # 화면 핵심 내용까지 비었으면 제품 문제 — 다시 재지 않는다
            if not any(content.values()):
                raise ValueError('empty performance measurement with empty page content: %s %s' % (name, empty))
            raise EmptyMeasurement('empty performance measurement: %s %s %s' % (name, device, empty))
        return result
    finally:
        await context.close()


def aggregate(runs):
    out = []
    for name in PAGES:
        for device in DEVICES:
            rows = [r for r in runs if r['page'] == name and r['device'] == device]
            if rows:
                out.append({'page': name, 'device': device, 'runs': len(rows),
                            **{key: statistics.median(r[key] for r in rows) for key in METRICS}})
    return out


def network_metrics(resources):
    """CDP also emits data: image events; they are not network requests."""
    rows = [r for r in resources if urlsplit(r['url']).scheme in ('http', 'https')]
    return {'requests': len(rows), 'bytes': sum(r['bytes'] for r in rows),
            'font_files': sum(r.get('type') == 'Font' for r in rows),
            'font_bytes': sum(r['bytes'] for r in rows if r.get('type') == 'Font'),
            'js_bytes': sum(r['bytes'] for r in rows if r.get('type') == 'Script')}


def summarize(report):
    for row in report['runs']:
        row.update(network_metrics(row['resources']))
    report['medians'] = aggregate(report['runs'])
    report['method']['requests'] = 'HTTP(S) requests only; data: URLs excluded; failed requests retained'
    return report


async def with_remeasure(sample, log, where, tries=3):
    """빈 측정(내용 있는 화면)만 최대 tries 번까지 다시 잰다. 다시 잰 기록은 log 에 남기고, 끝까지 비면 실패."""
    for retry in range(tries):
        try:
            return await sample()
        except EmptyMeasurement as e:
            log.append(dict(where, reason=str(e)))
            print('REMEASURE', str(e), flush=True)
            if retry == tries - 1:
                raise


async def run(args):
    from playwright.async_api import async_playwright
    start, runs, remeasured = time.monotonic(), [], []
    with ExitStack() as stack:
        base = args.live.rstrip('/') + '/' if args.live else stack.enter_context(serve_wire(args.site, args.flash, args.compression))
        daily_path = None
        if args.live:
            with urllib.request.urlopen(base + 'sitemap.xml', timeout=30) as response:
                dates = re.findall(r'/daily/(\d{4}-\d{2}-\d{2})/', response.read().decode())
            if not dates:
                raise ValueError('live sitemap has no dated daily page')
            daily_path = 'daily/' + max(dates) + '/'
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(**({} if args.channel == 'chromium' else {'channel': args.channel}))
            for name in args.pages:
                for device in args.devices:
                    for attempt in range(args.runs):
                        # Linux 헤드리스 Chromium 은 드물게 LCP 항목을 내지 않는다(2026-10-19 CI 1회, 로컬 Chrome 12회 재현 안 됨).
                        # 내용이 있는 화면의 빈 측정만 같은 회차를 최대 2번 다시 재고, 다시 잰 사실은 보고서에 남긴다
                        row = await with_remeasure(lambda name=name, device=device: measure(browser, base, name, device, None if args.live else args.site, args.flash,
                                                                    args.lang, args.delay_data, args.block_data, daily_path=daily_path),
                                                   remeasured, {'page': name, 'device': device, 'attempt': attempt + 1})
                        row['attempt'] = attempt + 1
                        runs.append(row)
                        print(json.dumps(dict({k: row[k] for k in ('page', 'device', 'attempt') + METRICS}, pf=row['observed'].get('pf')), ensure_ascii=False), flush=True)
                        if row['cls'] > 0.05:   # 어떤 요소가 밀렸는지 로그에 바로 남긴다(원인 추적용)
                            big = sorted(row['observed']['shifts'], key=lambda e: -e['value'])[:5]
                            print('SHIFT', name, device, json.dumps([[round(e['at']), round(e['value'], 4), e['sources']] for e in big], ensure_ascii=False), flush=True)
            await browser.close()
    return {'remeasured': remeasured, 'method': {'version': 5, 'cold_context': True, 'cache_disabled': True, 'reduced_motion': True, 'viewport_height': 1000,
                       'mobile_network': {'latency_ms': 150, 'download_bytes_per_second': 200000, 'upload_bytes_per_second': 93750},
                       'transfer': 'CDP Network.loadingFinished.encodedDataLength (body + response headers)',
                       'local_transport': 'Public GETs without fixtures' if args.live else 'Offline fixtures over real local TLS sockets (not route.fulfill); no external network',
                       'local_compression': 'server-provided (no override)' if args.live else args.compression + ' (text/JSON/JS/SVG only; gzip level 6, mtime 0)',
                       'cls': 'maximum session window (gap <1s, duration <5s), excludes recent input', 'lang': args.lang,
                       'mode': 'live' if args.live else 'local', 'site': str(args.live or args.site), 'flash': str(args.flash),
                       'delay_data_seconds': args.delay_data, 'blocked_data': args.block_data},
            'seconds': round(time.monotonic() - start, 3), 'medians': aggregate(runs), 'runs': runs}


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--site', type=Path)
    p.add_argument('--flash', type=Path, default=Path('.qa/snapshot-r/flash'))
    p.add_argument('--live')
    p.add_argument('--from-raw', type=Path, help='recompute network totals from saved CDP evidence without resampling')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runs', type=int, default=3)
    p.add_argument('--lang', choices=('ko', 'en'), default='ko')
    p.add_argument('--pages', nargs='+', default=PAGES)
    p.add_argument('--devices', nargs='+', choices=tuple(DEVICES), default=list(DEVICES))
    p.add_argument('--channel', default='chrome')
    p.add_argument('--compression', choices=('gzip', 'identity'), default='gzip')
    p.add_argument('--delay-data', type=float, default=0)
    p.add_argument('--block-data', action='store_true')
    p.add_argument('--details', type=Path, help='keep full per-resource evidence here; primary report retains per-run metrics')
    args = p.parse_args()
    if sum(bool(v) for v in (args.site, args.live, args.from_raw)) != 1 or args.runs < 1:
        p.error('exactly one of --site/--live/--from-raw and positive --runs are required')
    report = summarize(json.loads(args.from_raw.read_text()) if args.from_raw else asyncio.run(run(args)))
    if args.details:
        args.details.parent.mkdir(parents=True, exist_ok=True)
        args.details.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        for row in report['runs']:
            del row['resources']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return int(any(row['errors'] for row in report['runs']))


if __name__ == '__main__':
    raise SystemExit(main())
