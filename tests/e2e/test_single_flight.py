"""같은 자료는 한 번만 받는다: 내 자산에서 themes.json 이 늦게 와도(그 사이 첫 그리기 · 언어 적용 · 영어 사전 도착으로 여러 번 다시 그려도) 요청은 하나.
2026-10-20 CI 에서 147KB 파일을 한 번에 세 번 받아 용량 예산을 넘긴 일이 있었다(yk.js loadThemes 가 결과만 기억하고 진행 중 요청은 기억하지 않음)."""
import datetime as dt

import pytest

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_my_page_fetches_themes_once_while_pending(browser, site_server, request, lang):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    context = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
    offline = Offline(site, flash, site_server)
    context.route("**/*", offline.handle)
    held, dicts = [], []
    context.route("**/data/daily/themes.json*", lambda route: held.append(route))   # 붙잡아 두었다가 나중에 응답
    context.route("**/en.json*", lambda route: dicts.append(route))                # CI 처럼 영어 사전이 늦게 오게
    context.add_init_script("localStorage.setItem('df-lang', '%s'); localStorage.setItem('df-my', JSON.stringify(['BTC','ETH','NVDA']));"
                            "Object.defineProperty(navigator, 'doNotTrack', {get: () => '1'});" % lang)
    page = context.new_page()
    page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(site_server + path_for("my/", site), wait_until="load")
        for _ in range(50):                   # 첫 그리기가 themes.json 을 부를 때까지
            if held:
                break
            page.wait_for_timeout(100)
        assert held, "themes.json was never requested"
        for route in dicts:                   # themes.json 이 아직 안 온 사이 영어 사전 도착 → 다시 그리기
            offline.handle(route)
        page.wait_for_timeout(1000)
        count = len(held)
        for route in held:
            offline.handle(route)
        page.wait_for_timeout(800)
        assert dicts, "en.json was never requested"
        assert count == 1, "themes.json requested %d times while pending" % count
        assert page.locator("#feed [data-id]").count() > 0
        assert not errors, errors
    finally:
        context.close()


def test_landing_fetches_flash_once(browser, site_server, request):
    # 첫 페이지의 두 3D 장면(kit.js 위 장면 · p5.js 아래 장면)이 각자 속보를 불러 130KB 를 두 번 받았다(2026-10-20 CI).
    # 인트로를 건너뛰는 방문(다크 모드 · 사이트 안에서 온 방문)은 아래 장면까지 바로 불러온다
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
    offline = Offline(site, flash, site_server)
    context.route("**/*", offline.handle)
    context.add_init_script("localStorage.setItem('df-lang','en'); localStorage.setItem('df-theme','dark');"   # 다크는 인트로를 건너뛴다
                            "Object.defineProperty(navigator, 'doNotTrack', {get: () => '1'});")
    page = context.new_page()
    page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    urls, errors = [], []
    page.on("request", lambda r: urls.append(r.url))
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(site_server, wait_until="load")
        for _ in range(150):                  # 아래 장면(p5.js)과 그 자료(themes.json)까지 불러올 때까지
            if any("/data/daily/themes.json" in u for u in urls):
                break
            page.wait_for_timeout(100)
        assert any("/assets/df/p5.js" in u for u in urls), "lower scene never loaded"
        page.wait_for_timeout(1500)
        flashes = [u for u in urls if u.split("?")[0].endswith("workers.dev/flash")]
        assert len(flashes) == 1, flashes
        assert not errors, errors
    finally:
        context.close()
