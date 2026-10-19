"""숨겨진 탭에서는 주기 요청(Worker /flash · /market)을 멈추고, 다시 보이면 밀린 한 번만 바로 한다.
가짜 시계(page.clock)로 몇 분을 몇 초 만에 돌린다. 브라우저 탭 숨김은 document.hidden · visibilitychange 로 흉내 낸다."""
import datetime as dt
import time

import pytest

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for

HIDE = """(h) => {
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => h });
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => (h ? 'hidden' : 'visible') });
  document.dispatchEvent(new Event('visibilitychange'));
}"""


@pytest.mark.parametrize("route", ["live/", "my/"])
def test_hidden_tab_pauses_polling(browser, site_server, request, route):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
    # Keep every existing assertion against the currently deployed legacy routes.
    offline = Offline(site, flash, site_server, live_mode='legacy')
    context.route("**/*", offline.handle)
    context.add_init_script("localStorage.setItem('df-lang','ko'); localStorage.setItem('df-my', JSON.stringify(['BTC','ETH','NVDA']));")
    page = context.new_page()
    urls, pending = [], set()

    def started(req):
        urls.append(req.url)
        if 'workers.dev/' in req.url:
            pending.add(req)

    page.on("request", started)
    page.on("requestfinished", lambda req: pending.discard(req))
    page.on("requestfailed", lambda req: pending.discard(req))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.clock.install(time=dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    try:
        page.goto(site_server + path_for(route, site), wait_until="networkidle")

        def n(kind):
            return sum(1 for u in urls if "workers.dev/" + kind in u)

        def advance(minutes):
            # Drain real network responses between fake polling intervals.
            # Jumping five minutes while one response is still pending tests
            # an artificial five-minute outage instead of normal polling.
            for _ in range(minutes * 2):
                page.clock.run_for(30000)
                page.wait_for_timeout(50)
                deadline = time.monotonic() + 10
                while pending and time.monotonic() < deadline:
                    page.wait_for_timeout(25)
                assert not pending, 'polling fixture response did not finish'

        # 보이는 동안: 5분에 /flash 약 10번(30초), /market 약 5번(60초, 1h · 5m 두 개씩)
        f0, q0 = n("flash"), n("market")
        advance(5)
        seen_f, seen_q = n("flash") - f0, n("market") - q0
        assert seen_f >= 8, ("visible tab must keep polling /flash", seen_f)
        assert seen_q >= 4, ("visible tab must keep polling /market", seen_q)

        # 숨긴 10분: 요청 0
        page.evaluate(HIDE, True)
        f1, q1 = n("flash"), n("market")
        advance(10)
        assert (n("flash") - f1, n("market") - q1) == (0, 0), "hidden tab must not poll"

        # 다시 보이면: 밀린 한 번씩 바로(두 번 이상 몰아서 하지 않음)
        page.evaluate(HIDE, False)
        page.wait_for_timeout(600)
        assert n("flash") - f1 == 1, ("one catch-up /flash on return", n("flash") - f1)
        # 시세 한 번 갱신 = /market 두 개(1h · 5m)
        assert n("market") - q1 == 2, ("one catch-up quote refresh (1h + 5m) on return", n("market") - q1)

        # 그 뒤로는 다시 평소 주기
        f2 = n("flash")
        advance(2)
        assert 3 <= n("flash") - f2 <= 5, ("normal 30s cadence resumes", n("flash") - f2)
        assert not errors, errors
    finally:
        context.close()
