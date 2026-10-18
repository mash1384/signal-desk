from pytest_bdd import given, when, then, parsers, scenarios
from playwright.sync_api import expect
from tests.e2e.test_matrix import path_for, SELECTORS
from tests.policy.scan import SOURCE

scenarios("../features/promises.feature")
ROUTES = {"live": "live/", "daily": "daily/", "theme": "themes/crypto/", "calendar": "calendar/", "my": "my/", "brief": "brief/"}


@given(parsers.parse("a visitor on the {name} page"), target_fixture="visitor")
def visitor(name, session_page, site_server, request):
    page, context, offline = session_page
    context.add_init_script("if (!localStorage.getItem('df-lang')) localStorage.setItem('df-lang','ko'); localStorage.setItem('df-my', JSON.stringify(['BTC','ETH','NVDA']));")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    route = ROUTES[name]
    page.goto(site_server + path_for(route, request.config.getoption("--site")), wait_until="networkidle")
    page.locator(SELECTORS[route][0]).first.wait_for(state="visible")
    assert not errors, errors
    assert not offline.unmapped, offline.unmapped
    return {"page": page, "site": site_server}


@when(parsers.parse('the visitor selects "{language}" and opens My assets'))
def language_move(visitor, language):
    p = visitor["page"]
    p.locator('[data-lang="%s"]' % language).click()
    p.locator('.tabs a[href$="my/"]').click()
    p.locator(".wl [data-asset]").first.wait_for()


@then(parsers.parse('the selected language is "{language}"'))
def language_saved(visitor, language):
    p = visitor["page"]
    expect(p.locator("html")).to_have_attribute("lang", language)
    assert p.evaluate("localStorage.getItem('df-lang')") == language


@then("the first market assets are BTC ETH NVDA")
def assets_first(visitor):
    p = visitor["page"]
    expect(p.locator("#ps [data-my]").first).to_be_visible()
    assert p.locator("#ps [data-my]").evaluate_all("es=>es.slice(0,3).map(e=>e.dataset.my)") == ["BTC", "ETH", "NVDA"]


@then("three insights are visible and the review is absent")
def daily_insights(visitor):
    p = visitor["page"]
    expect(p.locator(".ins2 li")).to_have_count(3)
    expect(p.locator(".rv")).to_have_count(0)


@then("a theme summary box is visible")
def theme_summary(visitor):
    expect(visitor["page"].locator(".tsum")).to_be_visible()
    assert len(visitor["page"].locator(".tsum").inner_text()) > 30


@then("upcoming releases are in one box")
def upcoming_box(visitor):
    p = visitor["page"]
    expect(p.locator(".schw")).to_have_count(1)
    expect(p.locator(".nxw")).to_have_count(1)
    assert p.locator(".schw").evaluate("e=>e.closest('.box') === document.querySelector('.nxw').closest('.box')")


def open_story(visitor):
    p = visitor["page"]
    p.locator("#grid [data-id]").first.click()
    expect(p.locator("#sheet")).to_have_class("sheet on")
    expect(p.locator("#det h2")).to_be_visible()
    return p


@when("the visitor opens a story and presses close")
def close_story(visitor):
    p = open_story(visitor)
    p.locator("#sheet button[data-close]").click()


@when("the visitor opens a story and presses Escape")
def escape_story(visitor):
    p = open_story(visitor)
    p.keyboard.press("Escape")


@then("the story dialog is hidden and marked hidden")
def dialog_hidden(visitor):
    p = visitor["page"]
    expect(p.locator("#sheet")).not_to_have_class("sheet on")
    expect(p.locator("#sheet")).to_have_attribute("aria-hidden", "true")


@when("the visitor moves through the history chart with arrow keys")
def keyboard_chart(visitor):
    p = visitor["page"]
    c = p.locator("#tlc")
    expect(c).to_have_attribute("tabindex", "0")
    visitor["before"] = p.locator("#tlf").inner_text()
    c.focus()
    c.press("Home")
    visitor["home"] = p.locator("#tlf").inner_text()
    c.press("ArrowRight")


@then("the chart's accessible readout changes")
def chart_changed(visitor):
    after = visitor["page"].locator("#tlf").inner_text()
    assert visitor["home"] != visitor["before"]
    assert after != visitor["home"]


@then("no Telegram source or link is visible")
def no_telegram(visitor):
    p = visitor["page"]
    assert not SOURCE.search(p.locator("body").inner_text())
    assert not any(SOURCE.search(u) for u in p.locator("a[href]").evaluate_all("es=>es.map(e=>e.href)"))


@then("the saved watchlist has BTC ETH NVDA")
def watchlist(visitor):
    assert visitor["page"].locator(".wl [data-asset]").evaluate_all("es=>es.map(e=>e.dataset.asset)") == ["BTC", "ETH", "NVDA"]


@when("the visitor selects the bullish filter")
def bullish(visitor):
    visitor["page"].locator('[data-sort="up"]').click()


@then("every grid story is bullish")
def bullish_only(visitor):
    p = visitor["page"]
    pills = p.locator("#grid .pill")
    assert pills.count() > 0
    assert all(t == "호재" for t in pills.all_text_contents())
    expect(p.locator('[data-sort="up"]')).to_have_attribute("aria-pressed", "true")


@when("the visitor selects a different indicator")
def indicator(visitor):
    p = visitor["page"]
    buttons = p.locator("[data-ind]")
    if not buttons.count():
        buttons = p.locator("button[data-k]")
    assert buttons.count() > 1, "indicator controls absent"
    visitor["indicator"] = buttons.nth(1).get_attribute("data-ind") or buttons.nth(1).get_attribute("data-k")
    buttons.nth(1).click()


@then("the selected indicator has a detail panel")
def indicator_detail(visitor):
    expect(visitor["page"].locator("#detail .dt")).to_have_attribute("data-k", visitor["indicator"])


@when("the visitor selects a thread")
def thread(visitor):
    visitor["page"].locator(".lane").first.click()


@then("the thread details are visible")
def thread_details(visitor):
    expect(visitor["page"].locator(".lane").first).to_have_attribute("aria-expanded", "true")
    expect(visitor["page"].locator(".inl").first).to_be_visible()
