"""인트로 영상이 재생되지 않을 때(아이폰 저전력 모드 등): 2026-10-25 운영자 녹화 — 영상 대신 첫 화면이 나온 뒤
첫 스크롤에 '건너뛰기'가 다시 돌아 첫 화면이 지워졌다가 글이 다시 올라왔다. 건너뛴 뒤에는 아무것도 다시 돌지 않아야 한다."""
from tests.e2e.network import Offline


def landing(browser, site_server, request, video):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="ko-KR", service_workers="block")
    Offline(site, flash, site_server).attach(ctx)
    ctx.route("**/assets/df/c1.mp4*", video)
    return ctx


def test_stalled_video_falls_back_quickly(browser, site_server, request):
    ctx = landing(browser, site_server, request, lambda route: None)   # 영상 요청에 끝내 답하지 않는다(재생 요청은 걸린 채)
    try:
        page = ctx.new_page()
        page.goto(site_server, wait_until="domcontentloaded")
        page.wait_for_function("!document.getElementById('intro')", timeout=6000)   # 빈 인트로 화면을 오래 두지 않는다
    finally:
        ctx.close()


def test_first_scroll_after_video_fallback_does_not_replay_intro(browser, site_server, request):
    ctx = landing(browser, site_server, request, lambda route: route.abort())   # 영상을 못 받음 → 인트로 없이 첫 화면
    ctx.add_init_script("localStorage.setItem('df-lang','ko'); window.__done = 0; addEventListener('df-intro-done', () => window.__done++);")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(site_server, wait_until="domcontentloaded")
        page.wait_for_function("!document.getElementById('intro') && window.__done === 1", timeout=8000)   # 영상 없이 첫 화면으로
        page.wait_for_timeout(1300)                                                                     # 글 올라오기가 끝날 때까지
        page.evaluate("dispatchEvent(new Event('touchmove')); dispatchEvent(new Event('wheel'))")       # 첫 스크롤
        page.wait_for_timeout(250)
        running = page.evaluate("""[...document.querySelectorAll('.reveal, .hd .logo, .hd .nav, .hd .lang')]
            .flatMap(e => e.getAnimations()).filter(a => a.playState === 'running').length""")
        assert running == 0, "intro finish replayed on first scroll"
        assert page.evaluate("[...document.querySelectorAll('.reveal')].every(e => getComputedStyle(e).opacity === '1')")
        assert page.evaluate("window.__done") == 1
        assert not errors, errors
    finally:
        ctx.close()
