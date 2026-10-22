"""방법론 공유 링크는 선택한 언어의 보이는 내용으로 이동한다."""
import pytest


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_about_method_anchor(lang, session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang', '%s')" % lang)
    page.goto(site_server + "about/#method", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    target = page.locator("#method")
    assert target.count() == 1
    assert target.is_visible()
    assert target.locator("h2:visible").count() == 1
    assert page.evaluate("scrollY > 0")
