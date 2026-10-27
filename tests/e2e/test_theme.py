"""다크 모드 버튼: 모든 페이지에서 누르면 바뀌고(저장 · 버튼 상태 · 주소창 색), 다시 누르면 돌아온다. 첫 칠하기 전에 저장값을 따른다."""
import datetime as dt

import pytest

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for

STATE = """() => [document.documentElement.dataset.theme, localStorage.getItem('df-theme'),
  document.querySelector('[data-theme-toggle]').getAttribute('aria-pressed'), document.querySelector('meta[name=theme-color]').content]"""


def open_page(browser, site_server, request, route, saved=None):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    context = browser.new_context(viewport={"width": 390, "height": 900}, service_workers="block", reduced_motion="reduce")
    offline = Offline(site, flash, site_server)
    offline.attach(context)
    script = "Object.defineProperty(navigator, 'doNotTrack', {get: () => '1'});"
    if saved:
        script += "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('df-theme', '%s'); }" % saved
    context.add_init_script(script)
    page = context.new_page()
    page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site_server + path_for(route, site), wait_until="networkidle")
    return context, page, errors


def click(page, route):
    if route == "":   # 첫 페이지는 3D 색을 처음 그릴 때 정하므로 다시 불러온다
        with page.expect_navigation():
            page.locator("[data-theme-toggle]").click()
        page.wait_for_load_state("networkidle")
    else:
        page.locator("[data-theme-toggle]").click()


@pytest.mark.parametrize("route", ["", "live/", "my/", "themes/crypto/", "brief/", "calendar/", "daily/", "about/"])
def test_toggle_round_trip(browser, site_server, request, route):
    context, page, errors = open_page(browser, site_server, request, route, saved="light")
    try:
        assert page.evaluate(STATE)[:3] == ["light", "light", "false"]
        click(page, route)
        assert page.evaluate(STATE) == ["dark", "dark", "true", "#0b1320"]
        click(page, route)
        assert page.evaluate(STATE) == ["light", "light", "false", "#fff"]
        assert not errors, errors
    finally:
        context.close()


@pytest.mark.parametrize("route", ["", "live/", "my/", "themes/crypto/", "brief/", "calendar/", "daily/", "about/", "404.html"])
def test_saved_theme_is_set_before_any_stylesheet(request, route):
    # 첫 칠하기 전에 정해야 밝은 화면이 번쩍이지 않는다: 머리의 테마 스크립트가 모든 CSS 보다 앞에 있어야 한다
    from pathlib import Path
    site = Path(request.config.getoption("--site"))
    html = (site / (path_for(route, str(site)) if route != "404.html" else route)).joinpath("index.html") if route != "404.html" else site / route
    text = html.read_text(encoding="utf-8")
    head = text[:text.index("</head>")]
    script = head.find("document.documentElement.dataset.theme=localStorage.getItem('df-theme')")
    first_css = min(i for i in (head.find('rel="stylesheet"'), head.find("<style")) if i >= 0)
    assert 0 <= script < first_css, (route, script, first_css)


def test_saved_dark_is_applied(browser, site_server, request):
    context, page, errors = open_page(browser, site_server, request, "brief/", saved="dark")
    try:
        assert page.evaluate("document.documentElement.dataset.theme") == "dark"
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        assert bg == "rgb(11, 19, 32)", bg
        assert not errors, errors
    finally:
        context.close()
