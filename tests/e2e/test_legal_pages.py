"""이용약관 · 개인정보처리방침(10-31): 구글 로그인 공개(프로덕션)에 필요한 주소. 두 언어 · 문의 메일 · 바닥글 링크 · 좁은 화면."""
import pytest

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for


def page_for(browser, site_server, request, path, lang, width=390):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    ctx = browser.new_context(viewport={"width": width, "height": 900}, service_workers="block")
    Offline(site, flash, site_server).attach(ctx)
    ctx.add_init_script("localStorage.setItem('df-lang', '%s'); sessionStorage.setItem('df-intro', '1');" % lang)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site_server + path_for(path, site), wait_until="load")
    return ctx, page, errors


@pytest.mark.parametrize("path,ko,en", [("privacy/", "개인정보처리방침", "Privacy policy"), ("terms/", "이용약관", "Terms of service")])
@pytest.mark.parametrize("lang,width", [("ko", 320), ("en", 390), ("ko", 1440)])
def test_legal_page(browser, site_server, request, path, ko, en, lang, width):
    ctx, page, errors = page_for(browser, site_server, request, path, lang, width)
    try:
        h1 = page.locator("main h1").inner_text().strip()
        assert h1 == (ko if lang == "ko" else en), h1
        text = page.locator("main").inner_text()
        assert "support@delfona.com" in text
        assert ("시행일: 2026년 10월 31일" if lang == "ko" else "Effective: October 31, 2026") in text
        assert ("draft" not in text.lower()) and ("초안" not in text)
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        for href in ("terms/", "privacy/"):                       # 바닥글에서 두 페이지로 갈 수 있다
            assert page.locator("footer a[href$='%s']" % href).count() == 1
        assert not errors, errors
    finally:
        ctx.close()


@pytest.mark.parametrize("lang,labels", [("ko", ["이용약관", "개인정보처리방침"]), ("en", ["Terms", "Privacy"])])
def test_landing_footer_links(browser, site_server, request, lang, labels):
    ctx, page, errors = page_for(browser, site_server, request, "", lang)
    try:
        page.wait_for_timeout(1500)                                # 언어 글자 바꾸기(DFI.init) 뒤
        for href, label in zip(("terms/", "privacy/"), labels):
            a = page.locator("footer.ft a[href$='%s']" % href)
            assert a.count() == 1 and a.inner_text().strip() == label, (href, a.all_inner_texts())
        assert page.locator("footer.ft a[href='mailto:support@delfona.com']").count() == 1
        assert not errors, errors
    finally:
        ctx.close()
