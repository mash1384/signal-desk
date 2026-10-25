"""첫 화면 아래 3D 장면(p5.js: 시간 파형 · 지구본 · 마지막 화면).
2026-10-25 아이폰 사파리: 인트로 끝 + 1.6초 + 한가할 때까지 기다리는 사이 빨리 스크롤하면 페이지가 호재/악재 막대 장면에서 끝나
'아래가 다 사라졌다'(운영자 보고). → 스크롤을 시작하면 바로 불러오고, 끝내 못 불러오면 빈 화면 대신 브리핑 안내를 띄운다."""
from tests.e2e.network import Offline


def open_landing(browser, site_server, request, block_p5=False):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="ko-KR", service_workers="block")
    ctx.route("**/*", Offline(site, flash, site_server).handle)
    asked = []
    def p5(route):
        asked.append(route.request.url)
        route.abort() if block_p5 else route.fallback()
    ctx.route("**/assets/df/p5.js*", p5)
    # 인트로가 끝났다는 신호를 막는다 — 스크롤만으로 아래 장면을 불러오는지 본다(예전 코드는 이 신호 없이는 끝내 안 불렀다)
    ctx.add_init_script("""localStorage.setItem('df-lang','ko'); const _d = window.dispatchEvent.bind(window);
      window.dispatchEvent = (e) => (e && e.type === 'df-intro-done') ? true : _d(e);""")
    page = ctx.new_page()
    page.goto(site_server, wait_until="load")
    return ctx, page, asked


def scroll_down(page, steps=8):
    for _ in range(steps):
        page.evaluate("scrollBy(0, innerHeight * 0.4)")
        page.wait_for_timeout(150)


def test_scrolling_loads_lower_scene_without_waiting_for_intro(browser, site_server, request):
    ctx, page, asked = open_landing(browser, site_server, request)
    try:
        page.wait_for_function("!!(window.gsap && window.ScrollTrigger)", timeout=15000)
        scroll_down(page)
        page.wait_for_function("document.documentElement.classList.contains('nx-on')", timeout=15000)
        assert any("/assets/df/p5.js" in u for u in asked)
        assert not page.locator("#nx .px-wait").is_visible() or page.evaluate("getComputedStyle(document.querySelector('#nx .px-wait')).opacity") == "0"
    finally:
        ctx.close()


def test_failed_lower_scene_shows_briefing_link_not_blank(browser, site_server, request):
    ctx, page, asked = open_landing(browser, site_server, request, block_p5=True)
    try:
        page.wait_for_function("!!(window.gsap && window.ScrollTrigger)", timeout=15000)
        scroll_down(page)
        page.wait_for_function("document.documentElement.classList.contains('nx-fail')", timeout=15000)
        page.locator("#nx").scroll_into_view_if_needed()
        box = page.locator("#nx .px-end")
        assert box.evaluate("e => getComputedStyle(e).opacity") == "1"
        assert "브리핑" in box.inner_text()
        assert box.locator("a.btn").is_visible()
    finally:
        ctx.close()


def test_early_scroll_waits_for_gsap_instead_of_failing(browser, site_server, request):
    """2026-10-25 아이폰(iOS 18.7, 영상 재생 안 됨 → GSAP 이 2.5초 뒤에야 옴): 그 전에 스크롤해서 아래 장면을 먼저 불러
    'gsap 없음'으로 멈췄다(진단: nx-fail, loops 없음). GSAP 이 늦게 와도 기다렸다가 장면이 떠야 한다."""
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="ko-KR", service_workers="block")
    offline = Offline(site, flash, site_server)
    ctx.route("**/*", offline.handle)
    held = []
    ctx.route("**/gsap.min.js*", lambda route: held.append(route))          # GSAP 을 붙잡아 둔다(아이폰처럼 늦게)
    ctx.add_init_script("localStorage.setItem('df-lang','ko')")
    page = ctx.new_page()
    try:
        page.goto(site_server, wait_until="domcontentloaded")
        page.wait_for_timeout(600)
        scroll_down(page)                                                      # GSAP 이 오기 전에 빠르게 내린다
        page.wait_for_timeout(800)
        assert not page.evaluate("document.documentElement.classList.contains('nx-fail')"), "lower scene ran before GSAP"
        for route in held:
            offline.handle(route)
        page.wait_for_function("document.documentElement.classList.contains('nx-on')", timeout=15000)
        assert not page.evaluate("document.documentElement.classList.contains('nx-fail')")
    finally:
        ctx.close()
