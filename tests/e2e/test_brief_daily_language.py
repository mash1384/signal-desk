"""브리핑 카드의 실제 언어 전환: 영어 유무·review 전용·HTML 이스케이프."""
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("width", [320, 1440])
@pytest.mark.parametrize("translation", ["absent", "empty", "insights", "review"])
def test_daily_card_language(width, translation, session_page, site_server, request):
    page, context, _ = session_page
    flash = Path(request.config.getoption("--flash"))
    threads = json.loads((flash / "daily/threads.json").read_text())
    day = threads["daily_latest"]
    doc = {"date": day, "made": threads["made"] + 1, "headline": "한국어 검수 제목",
           "insights": [{"t": "한국어 항목", "s": "한국어 설명"}], "counts": {"stories": 17}, "market": {}, "balance": {}}
    if translation != "absent":
        doc["en"] = {"headline": "", "insights": []}
    if translation == "insights":
        doc["en"] = {"headline": "English <img src=x onerror=alert(1)>",
                     "insights": [{"t": "<b>Safe title</b>", "s": "A & B"}]}
    if translation == "review":
        doc["en"] = {"review": "English review without insights."}
    context.route("**/daily/" + day + ".json*", lambda route: route.fulfill(json=doc))
    page.set_viewport_size({"width": width, "height": 1000})
    context.add_init_script("localStorage.setItem('df-lang','ko')")
    page.goto(site_server + "brief/", wait_until="networkidle")
    card = page.locator(".dly").first
    assert "한국어 검수 제목" in card.inner_text()
    page.locator('[data-lang="en"]').first.click()
    if translation in ("absent", "empty"):
        assert "in Korean for now" in card.inner_text()
    elif translation == "insights":
        assert "English <img src=x onerror=alert(1)>" in card.inner_text()
        assert card.locator(".dins li").count() == 1
        assert card.locator("img,script,.dins b b").count() == 0
    else:
        assert "English review without insights." in card.inner_text()
    assert card.locator("a.more").get_attribute("href").endswith("daily/" + day + "/")
    page.locator('[data-lang="ko"]').first.click()
    assert "한국어 검수 제목" in card.inner_text()
