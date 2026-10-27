"""속보 빠른 확인(2026-10-26, 운영자 "속보 속도가 가장 중요"): 화면을 보고 있으면 5초마다 Worker /flash/new 로 새 소식만 받아 합친다.
숨긴 탭에서는 묻지 않고, 서버가 503 + Retry-After 를 주면 그만큼 쉰다. 30초 전체 받기는 예비로 그대로."""
import datetime as dt

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for
from tests.e2e.test_polling import HIDE

FOCUS = "document.hasFocus = () => true; localStorage.setItem('df-lang','ko');"


def open_live(browser, site_server, request):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
    offline = Offline(site, flash, site_server)
    offline.attach(context)
    context.add_init_script(FOCUS)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.clock.install(time=dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    page.goto(site_server + path_for("live/", site), wait_until="networkidle")
    return context, page, offline, errors


def tick(page, seconds):
    for _ in range(seconds):
        page.clock.run_for(1000)
        page.wait_for_timeout(30)


def test_new_item_appears_within_seconds(browser, site_server, request):
    context, page, offline, errors = open_live(browser, site_server, request)
    try:
        tick(page, 2)
        offline.flash_new_extra.append({"id": "fast-check-1", "t": offline.now + 5, "ko": "빠른확인시험소식", "en": "fast check item", "v": "호재", "s": 2, "kind": "event", "coins": [], "sectors": [], "mw": False, "n": 1})
        tick(page, 7)                                                   # 5초 확인 한 번 + 여유
        page.wait_for_function("document.body.innerText.includes('빠른확인시험소식')", timeout=5000)
        assert offline.flash_new_calls, "page never asked /flash/new"
        assert all(a <= offline.now for a in offline.flash_new_calls), "asks from before the newest item (late judgments are not missed)"
        assert not errors, errors
    finally:
        context.close()


def test_hidden_tab_does_not_ask(browser, site_server, request):
    context, page, offline, errors = open_live(browser, site_server, request)
    try:
        page.evaluate(HIDE, True)
        before = len(offline.flash_new_calls)
        tick(page, 20)
        assert len(offline.flash_new_calls) == before, "hidden tab must not poll /flash/new"
    finally:
        context.close()


def test_retry_after_is_respected(browser, site_server, request):
    context, page, offline, errors = open_live(browser, site_server, request)
    try:
        offline.flash_new_status = 503                                   # 서버가 바쁨 + Retry-After: 60
        tick(page, 6)
        first = len(offline.flash_new_calls)
        assert first >= 1
        tick(page, 30)
        assert len(offline.flash_new_calls) == first, "must wait Retry-After (60 s) before asking again"
        offline.flash_new_status = None
        tick(page, 40)
        assert len(offline.flash_new_calls) > first, "resumes after Retry-After"
    finally:
        context.close()


def test_hung_request_recovers(browser, site_server, request):
    """R24-F1(Codex): /flash/new 응답이 끝나지 않으면 빠른 확인이 영영 멈췄다 → 8초 뒤 풀고 1분 뒤 다시 묻는다."""
    context, page, offline, errors = open_live(browser, site_server, request)
    hung = []
    context.route("**/flash/new*", lambda route: hung.append(route))           # 답하지 않는다
    try:
        tick(page, 6)
        assert len(hung) == 1
        tick(page, 75)                                                          # 8초 제한 + 1분 쉼
        assert len(hung) >= 2, "fast polling must recover after a hung request"
    finally:
        context.close()


def test_existing_item_update_is_merged(browser, site_server, request):
    """R24-F2(Codex): 이미 받은 소식의 판정이 바뀌면(새 id 가 없어도) 받아 둔다 — 다음에 다시 그릴 때 바뀐 내용이 보인다."""
    context, page, offline, errors = open_live(browser, site_server, request)
    item = {"id": "fast-upd-1", "t": offline.now + 5, "ko": "판정바뀜시험", "en": "", "v": "중립", "s": 1, "kind": "event", "coins": [], "sectors": [], "mw": False, "n": 1}
    try:
        offline.flash_new_extra.append(dict(item))
        tick(page, 7)
        page.wait_for_function("document.body.innerText.includes('판정바뀜시험')", timeout=5000)
        offline.flash_new_extra[:] = [dict(item, ko="판정바뀜시험완료", v="악재", n=3)]
        tick(page, 7)                                                    # 바뀐 내용을 받아 둔다(라이브 화면은 새 소식이 없으면 다시 그리지 않는 설계)
        offline.flash_new_extra[:] = [{"id": "fast-upd-2", "t": offline.now + 9, "ko": "다음소식", "en": "", "v": "중립", "s": 1, "kind": "event", "coins": [], "sectors": [], "mw": False, "n": 1}]   # 바뀐 소식은 앞 응답에만 있었다
        tick(page, 7)                                                    # 새 소식이 와서 다시 그릴 때 바뀐 판정이 보여야 한다
        page.wait_for_function("document.body.innerText.includes('다음소식') && document.body.innerText.includes('판정바뀜시험완료')", timeout=5000)
        assert not errors, errors
    finally:
        context.close()
