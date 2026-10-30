"""일정 페이지 글꼴(10-30 장애: AI 경제 요약의 드문 글자 하나로 CDN 글꼴 조각이 늘어 게시가 11시간 막힘).
빌드 때 만든 'DF Page Text' 한 파일이 본문 · 차트 글자를 다 맡아, 이 자료로는 CDN 한글 조각을 하나도 받지 않는다."""
import pytest

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for


@pytest.mark.parametrize("width,lang,theme", [(390, "ko", "light"), (390, "en", "dark"), (1440, "ko", "light")])
def test_calendar_needs_no_cdn_font_chunks(browser, site_server, request, width, lang, theme):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    ctx = browser.new_context(viewport={"width": width, "height": 1000}, is_mobile=width < 900, service_workers="block")
    Offline(site, flash, site_server).attach(ctx)
    ctx.add_init_script("localStorage.setItem('df-lang', '%s'); localStorage.setItem('df-theme', '%s');" % (lang, theme))
    page, fonts, errors = ctx.new_page(), [], []
    page.on("requestfinished", lambda r: r.resource_type == "font" and fonts.append(r.url))
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(site_server + path_for("calendar/", site), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.mouse.wheel(0, 4000)                      # 아래쪽 차트(캔버스 글자)까지 그리게
        page.wait_for_timeout(1500)
        page.evaluate("document.fonts.ready")
        cdn = [u for u in fonts if "cdn.jsdelivr.net" in u]
        assert not cdn, cdn
        assert any("/assets/fonts/page/calendar-" in u for u in fonts), fonts
        assert page.evaluate("getComputedStyle(document.body).fontFamily").startswith('"DF Page Text"')
        assert page.evaluate("document.fonts.check('16px \"DF Page Text\"', '경제')")
        assert not errors, errors
    finally:
        ctx.close()
