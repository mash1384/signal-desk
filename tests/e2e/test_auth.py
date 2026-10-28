"""회원 화면(2026-10-28, web/assets/df/acct.js): 머리글 로그인 단추 · 이메일 가입 · 로그인 · 비밀번호 찾기 · 내 계정.
서버는 가짜(tests/e2e/fake_auth.py). 서버 규칙 자체는 tests/worker/auth.test.mjs 가 본다 — 여기서는 화면이 답을 맞게 보여 주는지."""
import datetime as dt
import json

import pytest

from tests.e2e.fake_auth import CODE
from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for


@pytest.fixture
def make(browser, site_server, request):
    made = []

    def _make(width=390, lang="ko", signed_in=None, theme="light"):
        site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
        ctx = browser.new_context(viewport={"width": width, "height": 900}, is_mobile=width < 900, service_workers="block")
        offline = Offline(site, flash, site_server)
        offline.attach(ctx)
        hint = "localStorage.setItem('df-acct', %s);" % json.dumps(json.dumps({"e": signed_in})) if signed_in else "localStorage.removeItem('df-acct');"
        ctx.add_init_script("localStorage.setItem('df-lang', '%s'); localStorage.setItem('df-theme', '%s'); %s" % (lang, theme, hint))
        if signed_in:
            offline.auth.add(signed_in, "abcd1234", marketing=False)
            offline.auth.session = signed_in
        page = ctx.new_page()
        page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
        errors, auth_reqs = [], []
        page.on("pageerror", lambda e, bag=errors: bag.append(str(e)))
        page.on("request", lambda r, bag=auth_reqs: bag.append(r.url) if "/auth/" in r.url else None)
        go = lambda path="live/": page.goto(site_server + path_for(path, site), wait_until="networkidle")   # noqa: E731
        made.append(ctx)
        return page, offline, errors, auth_reqs, go

    yield _make
    for c in made:
        c.close()


def visible(page, sel):
    return [x for x in page.locator(sel).all() if x.is_visible()]


@pytest.mark.parametrize("width,lang,text", [(390, "ko", None), (1440, "en", "Sign in"), (320, "ko", None)])
def test_signed_out_header_has_login_and_costs_nothing(make, width, lang, text):
    page, offline, errors, auth_reqs, go = make(width, lang)
    go()
    page.wait_for_timeout(2000)
    btn = visible(page, "[data-acct=login]")
    assert len(btn) == 1
    if text:
        assert btn[0].inner_text() == text
    else:
        assert btn[0].text_content().strip() == "로그인", "icon button is named (hidden text)"
    assert auth_reqs == [], "signed-out visitors make no /auth request"
    assert not page.evaluate("[...document.querySelectorAll('script[src*=\"acct.js\"], link[href*=\"acct.css\"]')].length"), "screen code loads only on click"
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), "header fits"
    box = page.locator(".hd .acct").bounding_box()
    assert box["x"] + box["width"] <= width, box
    assert not errors, errors


def test_sign_up_with_email_code(make):
    page, offline, errors, _, go = make(390, "ko")
    go()
    visible(page, "[data-acct=login]")[0].click()
    page.click("[data-go=signup]")
    f = page.locator(".au form")
    f.locator("input[name=email]").fill("new@example.com")
    f.locator(".sm").click()
    page.wait_for_selector(".au .code:not([hidden])")
    assert "인증번호를 보냈어요" in page.locator(".au-msg").inner_text()
    assert page.locator(".au .cok").is_hidden()
    f.locator("input[name=code]").fill("111111")
    page.wait_for_function("document.querySelector('.au-msg').textContent.includes('4번')")
    assert page.locator(".au .cok").is_hidden()
    f.locator("input[name=code]").fill(CODE)
    page.wait_for_selector(".au .cok:not([hidden])")
    submit = f.locator(".mbtn")
    f.locator("input[name=password]").fill("abcdefgh")
    assert "8자 이상이어야" in page.locator(".pwrule").inner_text()
    f.locator("input[name=password]").fill("abcd1234")
    f.locator("input[name=password2]").fill("abcd1234")
    assert submit.is_disabled(), "required agreements first"
    for k in ("age14", "terms"):
        page.locator(f".agree input[name={k}] + .ck").click()
    assert submit.is_disabled()
    page.locator(".agree input[name=privacy] + .ck").click()
    assert submit.is_enabled()
    assert not page.locator(".agree input[name=all]").is_checked(), "marketing is still off"
    f.locator("input[name=password2]").fill("abcd12345")
    assert submit.is_disabled(), "confirm must match"
    f.locator("input[name=password2]").fill("abcd1234")
    submit.click()
    page.wait_for_selector(".acct .av")
    assert page.locator(".acct .av").inner_text() == "N"
    assert page.locator(".au-toast").inner_text() == "가입을 환영해요!"
    assert [b for p, b in offline.auth.calls if p == "/auth/code"][0]["ts"] == "fake-turnstile-token", "robot check token goes with the code request"
    sent = [b for p, b in offline.auth.calls if p == "/auth/signup"][0]
    assert sent["agree"] == {"age14": True, "terms": True, "privacy": True, "marketing": False}
    assert sent["lang"] == "ko" and sent["keep"] is True
    assert json.loads(page.evaluate("localStorage.getItem('df-acct')")) == {"e": "new@example.com"}
    assert not errors, errors


def test_terms_open_on_top_and_keep_what_was_typed(make):
    page, offline, errors, _, go = make(1440, "ko")
    go()
    visible(page, "[data-acct=login]")[0].click()
    page.click("[data-go=signup]")
    page.fill(".au input[name=email]", "keep@example.com")
    page.click(".agree [data-doc=terms]")
    page.wait_for_selector(".au-doc")
    assert "이용약관" in page.locator(".au-doc h2").inner_text()
    assert not page.locator(".agree input[name=terms]").is_checked(), "'보기' does not tick the box"
    page.keyboard.press("Escape")
    assert page.locator(".au-doc").count() == 0
    assert page.locator(".au:not(.au-doc)").count() == 1, "sign-up stays open"
    assert page.input_value(".au input[name=email]") == "keep@example.com"
    page.keyboard.press("Escape")
    page.wait_for_selector(".au", state="detached")
    assert not errors, errors


@pytest.mark.parametrize("email,expect", [("taken@example.com", "이미 가입된 이메일"), ("x@mailinator.com", "일회용 이메일")])
def test_sign_up_refusals_are_explained(make, email, expect):
    page, offline, errors, _, go = make(390, "ko")
    offline.auth.add("taken@example.com")
    go()
    visible(page, "[data-acct=login]")[0].click()
    page.click("[data-go=signup]")
    page.fill(".au input[name=email]", email)
    page.click(".au .sm")
    page.wait_for_function("document.querySelector('.au-msg').textContent.length > 0")
    assert expect in page.locator(".au-msg").inner_text()
    assert page.locator(".au .code").is_hidden()
    assert not errors, errors


def test_mail_not_ready_says_so(make):
    page, offline, errors, _, go = make(390, "en")
    offline.auth.mail_ready = False
    go()
    visible(page, "[data-acct=login]")[0].click()
    page.click("[data-go=signup]")
    page.fill(".au input[name=email]", "a@example.com")
    page.click(".au .sm")
    page.wait_for_function("document.querySelector('.au-msg').textContent.length > 0")
    assert page.locator(".au-msg").inner_text() == "Email verification is not ready yet."
    assert page.locator(".au .sm").is_enabled(), "can try again later"


def test_login_wrong_then_right_and_menu_logout(make):
    page, offline, errors, _, go = make(1440, "ko")
    offline.auth.add("me@example.com", "right1234")
    go()
    visible(page, "[data-acct=login]")[0].click()
    page.fill(".au input[name=email]", "me@example.com")
    page.fill(".au input[name=password]", "wrong1234")
    page.click(".au .mbtn")
    page.wait_for_function("document.querySelector('.au-msg').textContent.length > 0")
    assert page.locator(".au-msg").inner_text() == "이메일 또는 비밀번호가 맞지 않아요."
    page.fill(".au input[name=password]", "right1234")
    page.click(".au .mbtn")
    page.wait_for_selector(".acct .av")
    page.wait_for_selector(".au", state="detached")
    page.click(".acct .av")
    page.wait_for_selector(".amenu")
    assert "me@example.com" in page.locator(".amenu .who").inner_text()
    page.click(".amenu [data-out]")
    page.wait_for_selector("[data-acct=login]")
    assert offline.auth.session is None
    assert page.evaluate("localStorage.getItem('df-acct')") is None
    assert not errors, errors


def test_signed_in_hint_is_checked_once_and_dropped_when_server_says_signed_out(make):
    page, offline, errors, auth_reqs, go = make(390, "ko", signed_in="gone@example.com")
    offline.auth.session = None   # 다른 기기에서 비밀번호를 바꿔 이 기기 로그인이 풀린 상태
    go()
    page.wait_for_selector("[data-acct=login]", state="attached", timeout=5000)
    assert not page.evaluate("document.documentElement.classList.contains('acct-on')"), "login buttons visible again"
    assert [u for u in auth_reqs if u.endswith("/auth/me")] and len(auth_reqs) == 1, auth_reqs
    assert page.evaluate("localStorage.getItem('df-acct')") is None
    assert not errors, errors


def test_reset_password(make):
    page, offline, errors, _, go = make(390, "ko")
    offline.auth.add("old@example.com", "old12345")
    go()
    visible(page, "[data-acct=login]")[0].click()
    page.click("[data-go=reset]")
    page.fill(".au input[name=email]", "nobody@example.com")
    page.click(".au .sm")
    page.wait_for_function("document.querySelector('.au-msg').textContent.length > 0")
    assert page.locator(".au-msg").inner_text() == "가입되지 않은 이메일이에요."
    assert page.locator(".au .cok").is_hidden() and page.locator(".au .newpw").is_hidden()
    page.fill(".au input[name=email]", "old@example.com")
    page.click(".au .sm")
    page.wait_for_selector(".au .code:not([hidden])")
    page.fill(".au input[name=code]", CODE)
    page.wait_for_selector(".au .newpw:not([hidden])")
    page.fill(".au input[name=password]", "new12345")
    page.fill(".au input[name=password2]", "new12345")
    page.click(".au .mbtn")
    page.wait_for_selector(".acct .av")
    assert "다른 기기는 로그아웃" in page.locator(".au-toast").inner_text()
    assert offline.auth.users["old@example.com"]["pw"] == "new12345"
    assert not errors, errors


@pytest.mark.parametrize("width,theme", [(390, "light"), (1440, "dark"), (320, "light")])
def test_account_page(make, width, theme):
    page, offline, errors, _, go = make(width, "ko", signed_in="acc@example.com", theme=theme)
    go("account/")
    page.wait_for_selector(".acc .me")
    assert page.locator(".acc .me b").inner_text() == "acc@example.com"
    assert page.get_attribute("meta[name=robots]", "content") == "noindex"
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    tg = page.locator(".acc .tg")
    assert tg.get_attribute("aria-checked") == "false"
    tg.click()
    page.wait_for_selector(".acc .tg.on")
    assert "동의함" in page.locator(".acc .cons").inner_text()
    assert offline.auth.users["acc@example.com"]["marketing"] is True
    page.click("[data-do=pw]")
    page.fill(".au input[name=current]", "nope1234")
    page.fill(".au input[name=password]", "next1234")
    page.fill(".au input[name=password2]", "next1234")
    page.click(".au .mbtn")
    page.wait_for_function("document.querySelector('.au-msg').textContent.length > 0")
    assert page.locator(".au-msg").inner_text() == "지금 비밀번호가 맞지 않아요."
    page.fill(".au input[name=current]", "abcd1234")
    page.click(".au .mbtn")
    page.wait_for_selector(".au", state="detached")
    assert offline.auth.users["acc@example.com"]["pw"] == "next1234"
    page.click("[data-do=del]")
    page.fill(".au input[name=password]", "next1234")
    page.click(".au .mbtn.danger")
    page.wait_for_selector(".acc .card.empty")
    assert "acc@example.com" not in offline.auth.users
    assert visible(page, "[data-acct=login]")
    assert not errors, errors


def test_account_page_signed_out_offers_login(make):
    page, offline, errors, _, go = make(390, "en")
    go("account/")
    page.wait_for_selector(".acc .card.empty .mbtn")
    page.click(".acc .card.empty .mbtn")
    page.wait_for_selector(".au input[name=email]")
    assert not errors, errors


def test_account_page_drops_a_stale_sign_in(make):
    page, offline, errors, _, go = make(390, "ko", signed_in="stale@example.com")
    offline.auth.session = None
    go("account/")
    page.wait_for_selector(".acc .card.empty .mbtn")
    assert page.evaluate("localStorage.getItem('df-acct')") is None
    page.wait_for_selector(".acct-ic", state="attached")
    assert not errors, errors


def test_signed_in_shows_initial_and_hides_login_from_first_paint(make):
    page, offline, errors, auth_reqs, go = make(390, "ko", signed_in="good@example.com")
    go()
    page.wait_for_selector(".acct .av")
    assert page.locator(".acct .av").inner_text() == "G"
    assert page.evaluate("document.documentElement.classList.contains('acct-on')")
    assert len([u for u in auth_reqs if u.endswith("/auth/me")]) == 1
    page.evaluate("document.querySelector('.hd .acct').innerHTML = '<button class=acct-ic>x</button>'")
    assert page.evaluate("getComputedStyle(document.querySelector('.acct-ic')).visibility") == "hidden", "with acct-on, login buttons never flash"
    assert not errors, errors
