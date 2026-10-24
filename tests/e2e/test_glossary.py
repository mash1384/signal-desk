"""용어 풀이(web/assets/df/gl.js, 운영자 2026-10-24): 어려운 말에 점선 밑줄 → 모바일은 누르면, PC는 마우스를 올리면(키보드는 초점) 풀이 창.
브리핑(빌드 때 그린 글)은 실제 자료라 어떤 말이 있는지 모르므로, 풀이할 말이 하나라도 있으면 밑줄이 있어야 한다는 식으로 본다.
테마 데스크는 합성 브리핑으로 고정한다."""
import json

TERMS_KO = ("연준", "WTI", "PCE", "FOMC", "국채", "선물", "ETF", "CPI", "VIX", "스테이블코인", "토큰화")
TERMS_EN = ("Fed", "WTI", "PCE", "FOMC", "Treasury", "futures", "ETF", "CPI", "VIX", "stablecoin", "basis points")


def open_brief(browser, site_server, offline_cls, site, flash, lang, mobile):
    ctx = browser.new_context(viewport={"width": 390 if mobile else 1440, "height": 900}, is_mobile=mobile, has_touch=mobile, locale="ko-KR", service_workers="block")
    offline = offline_cls(site, flash, site_server)
    ctx.route("**/*", offline.handle)
    ctx.add_init_script("localStorage.setItem('df-lang', %s)" % json.dumps(lang))
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site_server + "brief/", wait_until="domcontentloaded")
    return ctx, page, errors


def visible_gl(page):
    page.wait_for_function("document.querySelectorAll('#bf .gl').length > 0", timeout=8000)
    return page.locator("#bf .gl:visible")


def test_brief_terms_tap_on_mobile(browser, site_server, request):
    from tests.e2e.network import Offline
    ctx, page, errors = open_brief(browser, site_server, Offline, request.config.getoption("--site"), request.config.getoption("--flash"), "ko", True)
    try:
        text = page.locator("#bf").inner_text()
        if not any(t in text for t in TERMS_KO):
            return                                                   # 이 회차 글에 풀이할 말이 없으면 볼 것이 없다(밑줄도 없어야 한다)
        gl = visible_gl(page)
        assert gl.count() > 0
        first = gl.first
        word = first.inner_text()
        first.tap()
        pop = page.locator("#glpop")
        pop.wait_for(state="visible")                                 # 풀이 문장은 처음 열 때 불러온다
        assert pop.is_visible() and first.get_attribute("aria-expanded") == "true"
        assert len(pop.inner_text()) > len(word) + 10                 # 제목 + 풀이 문장
        box, vw = pop.bounding_box(), page.viewport_size["width"]
        assert box["x"] >= 0 and box["x"] + box["width"] <= vw         # 화면 밖으로 나가지 않는다
        first.tap()                                                   # 다시 누르면 닫힘
        assert not pop.is_visible()
        first.tap(); pop.wait_for(state="visible"); page.locator("#bf h1").tap()                      # 바깥을 누르면 닫힘
        assert not pop.is_visible() and first.get_attribute("aria-expanded") == "false"
        # 칸마다 같은 말은 한 번만
        dup = page.evaluate("""[...document.querySelectorAll('#bf [data-gl]')].some(el => { const k = [...el.querySelectorAll('.gl')].map(b => b.dataset.g); return new Set(k).size !== k.length; })""")
        assert not dup
        assert not errors, errors
    finally:
        ctx.close()


def test_brief_terms_hover_and_keyboard_on_pc_and_english(browser, site_server, request):
    from tests.e2e.network import Offline
    ctx, page, errors = open_brief(browser, site_server, Offline, request.config.getoption("--site"), request.config.getoption("--flash"), "en", False)
    try:
        text = page.locator("#bf").inner_text()
        if not any(t in text for t in TERMS_EN):
            return                                                   # 영어 글에 풀이할 말이 없는 회차(밑줄도 없어야 한다)
        page.wait_for_function("[...document.querySelectorAll('#bf .gl')].some(b => b.offsetParent)", timeout=8000)
        gl = page.locator("#bf .gl:visible")
        first = gl.first
        first.hover()
        pop = page.locator("#glpop")
        pop.wait_for(state="visible")
        assert first.get_attribute("data-gll") == "en"
        assert not any("가" <= ch <= "힣" for ch in pop.inner_text())   # 영어 화면엔 영어 풀이
        page.mouse.move(5, 5)                                         # 떼면 닫힘
        assert not pop.is_visible()
        first.focus(); page.keyboard.press("Shift+Tab"); page.keyboard.press("Tab")   # 키보드로 오면 열림(focus-visible)
        pop.wait_for(state="visible")
        page.keyboard.press("Escape")
        assert not pop.is_visible()
        assert not errors, errors
    finally:
        ctx.close()


def test_theme_desk_terms(session_page, site_server):
    page, context, offline = session_page
    context.add_init_script("localStorage.setItem('df-lang', 'ko')")
    now = int(offline.now)
    read = {"state": "연준이 금리를 그대로 둘 가능성이 커졌고 PCE 물가가 변수예요. 연준은 다음 달 회의를 앞두고 있어요.", "refs": [],
            "drivers": [{"s": "WTI가 다시 올랐어요.", "refs": []}], "shift": [], "links": [], "watch": []}
    brief = {"v": 1, "made": now - 60, "next": now + 3600, "ko": {"headline": "제목"}, "en": {"headline": "Title"}, "stories": {},
             "desks": {"crypto": {"ko": read, "en": {"state": "The Fed is likely to hold.", "refs": [], "drivers": [], "shift": [], "links": [], "watch": []}, "at": now}}}
    page.route("**/daily/briefing.json*", lambda r: r.fulfill(body=json.dumps(brief, ensure_ascii=False), content_type="application/json"))
    page.goto(site_server + "themes/crypto/", wait_until="domcontentloaded")
    page.wait_for_selector(".tsum .dks .gl")
    words = page.locator(".tsum .dks .gl").all_inner_texts()
    assert words == ["연준", "PCE"]                                    # 한 칸에서 '연준'은 처음 한 번만
    page.locator(".tsum .dks .gl").first.click()
    page.locator("#glpop").wait_for(state="visible")
    assert "미국 중앙은행" in page.locator("#glpop").inner_text()


def test_terms_and_definitions_line_up():
    """표기(gl.js)와 풀이 문장(gl-d.js)은 같은 순서의 두 파일이다. 개수가 어긋나면 엉뚱한 풀이가 뜬다."""
    import ast, pathlib, re
    root = pathlib.Path(__file__).resolve().parents[2] / "web/assets/df"
    def arr(name, var):
        s = (root / name).read_text(encoding="utf-8")
        return ast.literal_eval(re.search(r"const %s = (\[.*?\n\]);" % var, s, re.S).group(1))
    forms, defs = arr("gl.js", "G"), arr("gl-d.js", "D")
    assert len(forms) == len(defs) > 0
    assert all(len(f) == 2 and f[0] and f[1] for f in forms)
    assert all(len(d) == 2 and d[0] and d[1] for d in defs)
    assert all(any("가" <= c <= "힣" for c in d[0]) and not any("가" <= c <= "힣" for c in d[1]) for d in defs)
