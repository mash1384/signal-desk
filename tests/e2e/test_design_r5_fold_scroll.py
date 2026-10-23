"""5회차 디자인(운영자 승인): D6 모바일 접기 · 더 보기, D3 가로 넘김 '더 있음' 표시와 PC 시세 카드 격자."""
import pytest


def open_page(session_page, site_server, path, width, lang="ko"):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','%s')" % lang)
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(site_server + path, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    return page


THEMES = ("crypto", "nasdaq", "econ", "ai", "world")


def desk_with_details(session_page, site_server, width):
    """세부 문장(.dkg)이 있는 테마를 고른다 — 그 회차 검사에서 세부가 모두 빠진 데스크는 접기 단추가 없는 게 맞다(실제 자료로 도는 원격 검사)."""
    for k in THEMES:
        page = open_page(session_page, site_server, "themes/%s/" % k, width)
        n = page.evaluate("(() => { const g = document.querySelector('.sum.dk > .dkg'); return g ? g.children.length : 0; })()")
        if n:
            return page
        assert page.locator(".sum.dk [data-fold]").count() == 0      # 세부가 없으면 단추도 없다
    return None


def test_desk_folds_on_mobile_and_opens(session_page, site_server):
    page = desk_with_details(session_page, site_server, 390)
    if page is None:
        return                                                     # 모든 테마에 세부가 없는 회차 — 위에서 '단추 없음'을 확인했다
    btn = page.locator(".sum.dk [data-fold]")
    assert btn.is_visible() and btn.get_attribute("aria-expanded") == "false"
    assert not page.locator(".sum.dk > .dkg").is_visible()
    btn.click()
    assert page.locator(".sum.dk > .dkg").is_visible() and btn.get_attribute("aria-expanded") == "true"
    btn.click()
    assert not page.locator(".sum.dk > .dkg").is_visible()


def test_desk_not_folded_on_desktop(session_page, site_server):
    page = desk_with_details(session_page, site_server, 1440)
    if page is None:
        return
    assert page.locator(".sum.dk > .dkg").is_visible()
    assert not page.locator(".sum.dk [data-fold]").is_visible()


@pytest.mark.parametrize("lang,word", [("ko", "더 보기"), ("en", "more stories")])
def test_brief_stories_show_five_then_all(lang, word, session_page, site_server):
    page = open_page(session_page, site_server, "brief/", 390, lang)
    total = page.locator(".lanes ul > li").count()
    assert total > 5
    shown = page.evaluate("[...document.querySelectorAll('.lanes ul > li')].filter(e => e.offsetParent).length")
    assert shown == 5
    more = page.locator(".lanes [data-more]")
    assert more.is_visible() and word in more.inner_text()
    more.click()
    assert page.evaluate("[...document.querySelectorAll('.lanes ul > li')].filter(e => e.offsetParent).length") == total
    assert page.locator(".lanes [data-more]").count() == 0


def test_brief_stories_all_on_desktop(session_page, site_server):
    page = open_page(session_page, site_server, "brief/", 1440)
    assert page.evaluate("[...document.querySelectorAll('.lanes ul > li')].every(e => e.offsetParent)")
    assert not page.locator(".lanes [data-more]").is_visible()


def test_scroll_hint_on_mobile_cards(session_page, site_server):
    page = open_page(session_page, site_server, "themes/crypto/", 390)
    btn = page.locator(".hs-btn").first
    btn.wait_for(state="visible", timeout=5000)          # 넘치는 줄이 있을 때만 sh.js를 늦게 부른다
    assert page.evaluate("document.querySelector('#cards').classList.contains('hs-more')")
    btn.click()
    page.wait_for_function("document.querySelector('#cards').scrollLeft > 100")


def test_desktop_cards_grid_without_hint(session_page, site_server):
    page = open_page(session_page, site_server, "themes/crypto/", 1440)
    page.wait_for_timeout(800)
    assert page.evaluate("(() => { const c = document.querySelector('#cards'); return getComputedStyle(c).display === 'grid' && c.scrollWidth <= c.clientWidth + 1; })()")
    assert page.evaluate("[...document.querySelectorAll('#cards .hs-btn, .strip .hs-btn')].every(b => b.hidden)")


# 030 교차 확인에서 찾은 두 문제(R5-F1 · F2)의 회귀: 숨긴 › 단추가 실제로 사라지는지, 펼친 상태가 언어 · 테마 전환 뒤에도 남는지
def test_scroll_hint_really_disappears_at_end_and_on_desktop(session_page, site_server):
    page = open_page(session_page, site_server, "themes/crypto/", 390)
    btn = page.locator(".hs-btn").first
    btn.wait_for(state="visible", timeout=5000)
    page.evaluate("(() => { const c = document.querySelector('#cards'); c.scrollLeft = c.scrollWidth; })()")
    page.wait_for_timeout(300)
    assert not btn.is_visible()                                   # 끝까지 넘기면 실제로 보이지 않는다
    page.evaluate("document.querySelector('#cards').scrollLeft = 0"); page.wait_for_timeout(300)
    assert btn.is_visible()
    page.set_viewport_size({"width": 1440, "height": 1000}); page.wait_for_timeout(600)
    assert page.evaluate("[...document.querySelectorAll('.hs-btn')].every(b => !b.offsetParent || getComputedStyle(b).display === 'none')")


def test_fold_state_survives_language_and_theme_switch(session_page, site_server):
    page = desk_with_details(session_page, site_server, 390)
    if page is None:
        return
    page.locator(".sum.dk [data-fold]").click()
    assert page.locator(".sum.dk > .dkg").is_visible()
    page.locator(".lang button[data-lang='en']").click(); page.wait_for_timeout(500)
    assert page.locator(".sum.dk > .dkg").is_visible() and page.locator(".sum.dk [data-fold]").get_attribute("aria-expanded") == "true"
    page.locator("[data-theme-toggle]").first.click(); page.wait_for_timeout(500)
    assert page.locator(".sum.dk > .dkg").is_visible()


def test_more_stories_survive_language_switch(session_page, site_server):
    page = open_page(session_page, site_server, "brief/", 390)
    total = page.locator(".lanes ul > li").count()
    page.locator(".lanes [data-more]").click()
    page.locator(".lang button[data-lang='en']").click(); page.wait_for_timeout(500)
    assert page.evaluate("[...document.querySelectorAll('.lanes ul > li')].filter(e => e.offsetParent).length") == total
