"""D5: 제목 아래 날짜 이동은 발행된 이웃 날짜를 열고 양 끝에서는 비활성화한다."""
from pathlib import Path

from playwright.sync_api import expect


def test_daily_date_navigation(session_page, site_server, request):
    page, context, _ = session_page
    dates = sorted(p.name for p in (Path(request.config.getoption('site')) / 'daily').iterdir() if p.is_dir() and p.name[:4].isdigit())
    assert len(dates) >= 3
    context.add_init_script("localStorage.setItem('df-lang','ko');localStorage.setItem('df-theme','light')")
    for width in (390, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        page.goto(site_server + 'daily/' + dates[-2] + '/', wait_until='networkidle')
        nav = page.locator('header .date-nav')
        expect(nav).to_be_in_viewport()
        expect(nav.locator('time')).to_have_attribute('datetime', dates[-2])
        for lang, label in (('en', 'Previous'), ('ko', '이전 날')):
            page.locator('[data-lang="%s"]' % lang).first.click()
            page.locator('[data-theme-toggle]').first.click()
            expect(nav.locator('[rel=prev]')).to_contain_text(label)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        for direction, date in (('prev', dates[-3]), ('next', dates[-1])):
            href = nav.locator('[rel=%s]' % direction).get_attribute('href')
            assert href == page.locator('.pager2 a[href="%s"]' % href).get_attribute('href')
            nav.locator('[rel=%s]' % direction).click()
            page.wait_for_url('**/daily/' + date + '/')
            expect(page.locator('.date-nav time')).to_have_attribute('datetime', date)
            page.go_back(wait_until='networkidle')
    for date, selector in ((dates[0], ':first-child'), (dates[-1], ':last-child')):
        page.goto(site_server + 'daily/' + date + '/', wait_until='networkidle')
        expect(page.locator('.date-nav > ' + selector)).to_be_disabled()
