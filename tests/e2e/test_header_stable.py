"""머리글(2026-10-28 운영자: 랜딩 로그인 단추가 깨져 보임 · 한/영을 바꾸면 머리글 위치가 바뀜 · 다크 모드 마지막 문구에 박스).
- 한국어 ↔ 영어를 바꿔도 언어 · 테마 · 로그인 · 랜딩 주 단추의 자리와 폭이 그대로
- 로그인 단추는 폭마다 하나만 보이고, 아이콘 단추의 숨은 이름은 화면에 안 보인다(랜딩은 공용 lk.css 를 안 써서 따로 맞춤)
- 다크 모드 랜딩 마지막 문구 뒤에 박스가 없다"""
import pytest

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for

BOXES = "() => Object.fromEntries(['.hd .lang', '.hd .thm', '.hd .acct', '.hd .btn'].map((s) => { const e = document.querySelector(s); if (!e || !e.offsetWidth) return [s, null]; const b = e.getBoundingClientRect(); return [s, [Math.round(b.x), Math.round(b.width)]]; }))"


def open_page(browser, site_server, request, path, width, lang, theme="light"):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    ctx = browser.new_context(viewport={"width": width, "height": 900}, is_mobile=width < 900, service_workers="block")
    Offline(site, flash, site_server).attach(ctx)
    ctx.add_init_script("localStorage.setItem('df-lang', '%s'); localStorage.setItem('df-theme', '%s'); localStorage.removeItem('df-acct');" % (lang, theme))
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e, bag=errors: bag.append(str(e)))
    page.goto(site_server + path_for(path, site), wait_until="load")
    page.wait_for_timeout(5500 if path == "" else 1200)   # 랜딩은 첫 로고 연출이 끝난 뒤 머리글이 제자리에 선다
    return ctx, page, errors


@pytest.mark.parametrize("path,width", [("", 1440), ("live/", 1440), ("brief/", 1440), ("", 390), ("live/", 390), ("", 320)])
def test_header_does_not_move_when_language_changes(browser, site_server, request, path, width):
    seen = {}
    for lang in ("ko", "en"):
        ctx, page, errors = open_page(browser, site_server, request, path, width, lang)
        try:
            seen[lang] = page.evaluate(BOXES)
            visible = [b for b in page.locator(".hd [data-acct=login]").all() if b.is_visible()]
            assert len(visible) == 1, "one login button per width"
            hidden = page.locator(".hd .acct .vh")
            if hidden.count():
                box = hidden.bounding_box()
                assert box is None or (box["width"] <= 1 and box["height"] <= 1), "the icon button's name is not drawn"
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            acct = page.locator(".hd .acct").bounding_box()
            assert acct["x"] + acct["width"] <= width
            assert not errors, errors
        finally:
            ctx.close()
    assert seen["ko"] == seen["en"], seen


def test_landing_end_line_has_no_box_in_dark(browser, site_server, request):
    ctx, page, errors = open_page(browser, site_server, request, "", 1440, "ko", theme="dark")
    try:
        page.wait_for_function("document.querySelector('#nx')?.classList.contains('fin4')", timeout=15000)
        box = page.evaluate("(() => { const s = getComputedStyle(document.querySelector('#nx .px-end .box')); return [s.backgroundColor, s.boxShadow]; })()")
        assert box == ["rgba(0, 0, 0, 0)", "none"], box
        assert not errors, errors
    finally:
        ctx.close()


@pytest.mark.parametrize("path,width,lang", [(p, w, lang) for p in ("", "live/") for w in (900, 1024, 1180, 1200) for lang in ("ko", "en")])
def test_header_fits_at_medium_widths(browser, site_server, request, path, width, lang):
    ctx, page, errors = open_page(browser, site_server, request, path, width, lang)
    try:
        right = page.evaluate("Math.max(...[...document.querySelectorAll('.hd .wrap > *')].filter((e) => e.offsetWidth).map((e) => e.getBoundingClientRect().right))")
        assert right <= width, f"header ends at {right}px on a {width}px screen"
        assert not errors, errors
    finally:
        ctx.close()
