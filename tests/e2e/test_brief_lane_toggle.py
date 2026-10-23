"""이어지는 이야기 카드: 좁은 화면은 다시 누르면 접히고, PC는 오른쪽 칸에 고른 이야기를 계속 보여 준다(운영자 요청 2026-10-23)."""
import pytest


def open_brief(session_page, site_server, width):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','ko')")
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(site_server + "brief/", wait_until="networkidle")
    return page


@pytest.mark.parametrize("width", [390, 768])
def test_mobile_card_toggles_open_and_closed(width, session_page, site_server):
    page = open_brief(session_page, site_server, width)
    lane = lambda: page.locator(".lanes [data-pick]").nth(1)
    lane().click()
    page.locator(".lanes .inl").first.wait_for(state="visible")
    assert lane().get_attribute("aria-expanded") == "true"
    lane().click()
    page.wait_for_function("!document.querySelector('.lanes .inl')")
    assert lane().get_attribute("aria-expanded") == "false"
    lane().click()                                                  # 다시 열린다
    page.locator(".lanes .inl").first.wait_for(state="visible")
    page.locator(".lanes [data-pick]").nth(2).click()               # 다른 카드를 누르면 그 카드로 바뀐다
    assert page.locator(".lanes [data-pick]").nth(2).get_attribute("aria-expanded") == "true"
    assert page.locator(".lanes .inl").count() == 1


def test_desktop_keeps_selected_story_in_pane(session_page, site_server):
    page = open_brief(session_page, site_server, 1440)
    lane = lambda: page.locator(".lanes [data-pick]").nth(1)
    lane().click()
    page.wait_for_function("document.querySelectorAll('.lanes [data-pick]')[1].getAttribute('aria-expanded') === 'true'")   # 다시 그린 뒤(제목을 받아 온 뒤)
    page.locator(".pane .ri").first.wait_for(state="visible")
    first = page.locator(".pane").inner_text()
    lane().click()                                                  # 다시 눌러도 오른쪽 칸은 그대로(비지 않는다)
    page.wait_for_timeout(300)
    assert lane().get_attribute("aria-expanded") == "true"
    assert page.locator(".pane").inner_text() == first
    assert page.locator(".lanes .inl").count() == 0                 # PC는 카드 안에 펼치지 않는다
