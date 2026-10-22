"""좁은 머리글의 언어·테마 단추가 화면 안에서 실제로 눌린다."""
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("kind", ["live", "article"])
@pytest.mark.parametrize("lang", ["ko", "en"])
def test_compact_header_controls(kind, lang, session_page, site_server, request):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang', '%s')" % lang)
    if kind == "article":
        site = Path(request.config.getoption("--site"))
        article_id = json.loads((site / "data/articles.json").read_text())[0]["id"]
        path = "a/%s/" % article_id
    else:
        path = "live/"
    page.goto(site_server + path, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    for width in (320, 359, 360, 374, 375):
        page.set_viewport_size({"width": width, "height": 1000})
        for selector in ('[data-lang="en"]', '[data-lang="ko"]', '[data-theme-toggle]'):
            box = page.locator(selector).bounding_box()
            assert box and box["x"] >= 0 and box["x"] + box["width"] <= width, (width, selector, box)
        toggle = page.locator("[data-theme-toggle]")
        old = page.locator("html").get_attribute("data-theme")
        toggle.click()
        assert page.locator("html").get_attribute("data-theme") != old
