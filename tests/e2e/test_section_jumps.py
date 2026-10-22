"""D2: 모바일 구간 링크는 언어·테마 전환 뒤에도 보이는 목적지로 이동한다."""
import pytest
from playwright.sync_api import expect


@pytest.mark.parametrize("route,labels,targets", [
    ("calendar/", {"ko": ["지금 요약", "예정 발표", "지표"], "en": ["Now", "Releases", "Indicators"]}, ['#cal-summary', '#cal-upcoming', '#cal-indicators']),
    ("about/", {"ko": ["서비스 소개", "방법론", "데이터 출처"], "en": ["About", "Method", "Sources"]}, ['#about-intro', '#method', '#sources']),
])
def test_section_jumps(route, labels, targets, session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','ko');localStorage.setItem('df-theme','light')")
    page.goto(site_server + route, wait_until="networkidle")
    for lang in ("ko", "en", "ko"):
        page.locator('[data-lang="%s"]' % lang).first.click()
        page.locator('[data-theme-toggle]').first.click()
        links = page.locator('.jumpnav a')
        expect(links).to_have_count(3)
        for i, label in enumerate(labels[lang]):
            expect(links.nth(i)).to_contain_text(label)
            href = links.nth(i).get_attribute('href')
            assert href == targets[i]
            target = page.locator(href)
            expect(target).to_have_count(1)
            links.nth(i).click()
            expect(target).to_be_in_viewport()
            page.wait_for_function("s => { const t = document.querySelector(s).getBoundingClientRect().top; return t >= 60 && t < 100; }", arg=href)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.set_viewport_size({"width": 1440, "height": 1000})
    expect(page.locator('.jumpnav')).to_be_hidden()
