"""익명 방문 통계: 페이지 조회 1회, 기사 열기 이벤트, 추적 거부(DNT)면 아무것도 안 보냄 — 개인 식별값 없음."""
import datetime as dt

import pytest

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for


def visit(browser, site_server, request, route, dnt=False, action=None):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    context = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block")
    offline = Offline(site, flash, site_server)
    context.route("**/*", offline.handle)
    script = "localStorage.setItem('df-lang','ko');"
    if dnt:
        script += "Object.defineProperty(navigator, 'doNotTrack', {get: () => '1'});"
    context.add_init_script(script)
    page = context.new_page()
    # 시계를 스냅샷 시각에 고정한다(스냅샷이 하루 넘게 묵으면 '최근 24시간' 소식이 비어 기사를 열 수 없다)
    page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    try:
        page.goto(site_server + path_for(route, site), wait_until="networkidle")
        if action:
            action(page)
        page.wait_for_timeout(400)
        return offline.beacons
    finally:
        context.close()


@pytest.mark.parametrize("route,key", [("live/", "live"), ("daily/", "daily"), ("about/", "about")])
def test_page_view_counted_once(browser, site_server, request, route, key):
    beacons = visit(browser, site_server, request, route)
    views = [b for b in beacons if b.get("e") == "view"]
    assert len(views) == 1, beacons
    assert views[0] == {"e": "view", "k": key, "l": "ko", "d": "m"}       # 이 다섯 값뿐 — 식별값 없음


def test_story_open_event(browser, site_server, request):
    def open_story(page):
        page.locator("#grid [data-id]").first.click()
        page.locator("#sheet.on").wait_for()
    beacons = visit(browser, site_server, request, "live/", action=open_story)
    assert {"e": "open", "k": "live", "l": "ko", "d": "m"} in beacons, beacons


def test_do_not_track_sends_nothing(browser, site_server, request):
    assert visit(browser, site_server, request, "live/", dnt=True) == []


def test_language_event_only_on_click(browser, site_server, request):
    beacons = visit(browser, site_server, request, "live/")
    assert not [b for b in beacons if b.get("e") == "lang"], "page load must not count as a language change"
    beacons = visit(browser, site_server, request, "live/", action=lambda p: p.locator('[data-lang="en"]').first.click())
    assert {"e": "lang", "k": "live", "l": "en", "d": "m"} in beacons, beacons
