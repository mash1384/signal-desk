"""6회차(운영자): 브리핑 '분야별'은 한 칸에서 탭 · 앞뒤 단추로 넘기고, '최근 하루 정리'는 그 옆(모바일은 아래)에 — 이야기 목록 맨 끝이 아니다."""
import pytest


def visible_panels(page):
    return page.evaluate("[...document.querySelectorAll('#bf-dkt .bf-dp')].filter(e => e.offsetParent).map(e => e.id)")


@pytest.mark.parametrize("width", [390, 1440])
def test_one_desk_at_a_time_with_tabs_and_arrows(width, session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','ko')")
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(site_server + "brief/", wait_until="networkidle")
    tabs = page.locator(".bf-tabs [data-dk]")
    n = tabs.count()
    assert n >= 2
    first = visible_panels(page)
    assert len(first) == 1                                         # 보이는 분야는 하나
    page.locator(".bf-pv[data-step='1']").click()
    second = visible_panels(page)
    assert len(second) == 1 and second != first and tabs.nth(1).get_attribute("aria-selected") == "true"
    tabs.nth(n - 1).click()
    assert page.locator(".bf-pv[data-step='1']").is_disabled() and tabs.nth(n - 1).get_attribute("aria-selected") == "true"
    page.locator(".bf-pv[data-step='-1']").click()
    assert tabs.nth(n - 2).get_attribute("aria-selected") == "true"


@pytest.mark.parametrize("width", [390, 1440])
def test_daily_card_sits_next_to_desks_above_the_story_list(width, session_page, site_server):
    page, context, _ = session_page
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(site_server + "brief/", wait_until="networkidle")
    assert page.locator(".dly").count() == 1                       # 한 번만(목록 쪽에서 뺐다)
    y = page.evaluate("(() => { const r = (s) => document.querySelector(s).getBoundingClientRect(); return {dk: r('.bf-dk').top, dly: r('#bf-dly').top, lanes: r('.lanes').top, dkr: r('.bf-dk').right, dlyl: r('#bf-dly').left}; })()")
    assert y["dly"] < y["lanes"]
    if width >= 900:
        assert abs(y["dk"] - y["dly"]) < 2 and y["dlyl"] > y["dkr"]   # 나란히
    else:
        assert y["dly"] > y["dk"]
