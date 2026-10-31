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


BLOCK_PLAY = ("HTMLMediaElement.prototype.play = function () { return Promise.reject(new DOMException('blocked', 'NotAllowedError')); };"
              "new MutationObserver(() => document.querySelectorAll('video[autoplay]').forEach((v) => { v.removeAttribute('autoplay'); v.autoplay = false; }))"
              ".observe(document, {subtree: true, childList: true});")


def test_hero_scroll_scene_loads_when_video_cannot_play(browser, site_server, request):
    """2026-10-27 운영자 아이폰: 영상 자동 재생이 막히면(저전력 모드 등) 첫 화면 글이 스크롤해도 입자로 흩어지지 않았다.
    원인: '2.5초 뒤 장면 준비' 조건이 'GSAP 이 아직 없으면'이었는데, 아래 장면이 GSAP 을 먼저 불러 조건이 늘 거짓 → hx.js 를 아예 안 불렀다."""
    for video in (lambda route: route.continue_(), lambda route: route.abort()):
        ctx = landing(browser, site_server, request, video)
        ctx.add_init_script(BLOCK_PLAY + "window.__hx = 0; addEventListener('df-hx-ready', () => window.__hx++);")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e, bag=errors: bag.append(str(e)))
        try:
            page.goto(site_server, wait_until="domcontentloaded")
            page.wait_for_function("!document.getElementById('intro')", timeout=6000)
            page.wait_for_function("window.__hx === 1", timeout=15000)                      # 첫 화면 스크롤 장면(글 → 입자)이 준비됨
            assert not page.evaluate("document.documentElement.classList.contains('hx-wait')")
            assert not errors, errors
        finally:
            ctx.close()


def test_intro_plays_once_per_tab_and_not_after_social_login(browser, site_server, request):
    """10-31 운영자: 첫 연출을 건너뛰고 카카오로 가입하고 돌아오니 연출이 또 나왔다. 같은 탭에서 두 번째부터 · #auth= 로 돌아온 방문은 없다.
    판정은 페이지가 연출을 틀지 정한 값(window.DF_NOINTRO) — 영상 재생 여부와 무관하게."""
    ctx = landing(browser, site_server, request, lambda route: route.abort())
    skipped = "window.DF_NOINTRO === 1"
    try:
        page = ctx.new_page()
        page.goto(site_server, wait_until="domcontentloaded")
        assert not page.evaluate(skipped), "first visit shows the intro"
        page.goto("about:blank")                                    # 카카오로 나갔다가 같은 탭으로 돌아옴
        page.goto(site_server + "#auth=error&e=not_configured&p=kakao", wait_until="domcontentloaded")
        assert page.evaluate(skipped), "returning from login replays the intro"
        page.goto(site_server, wait_until="domcontentloaded")       # 같은 탭 · 그냥 다시 와도 없음
        assert page.evaluate(skipped), "intro replays in the same tab"
        fresh = ctx.new_page()                                      # 새 탭이라도 로그인에서 돌아온 주소면 없음
        fresh.goto(site_server + "#auth=ok&t=x", wait_until="domcontentloaded")
        assert fresh.evaluate(skipped), "#auth= visit in a new tab replays the intro"
        other = ctx.new_page()                                      # 새 탭 · 보통 첫 방문은 그대로 나온다
        other.goto(site_server, wait_until="domcontentloaded")
        assert not other.evaluate(skipped), "a new tab's first visit should still show the intro"
        forced = ctx.new_page()                                     # ?intro 는 언제나 튼다(확인용 주소)
        forced.goto(site_server + "?intro", wait_until="domcontentloaded")
        assert not forced.evaluate(skipped)
    finally:
        ctx.close()
