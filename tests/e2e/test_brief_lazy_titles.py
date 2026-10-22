"""7회차: 브리핑은 제목 뺀 이야기 자료(threads-core.json)만 처음 받고, 제목(threads-text.json)은 이야기를 열거나 언어를 바꿀 때 받는다.
보이는 화면은 그대로여야 한다 — 이야기 목록 제목, 소식 상세 창의 제목 · 영어 원문 줄(한국어 화면)."""
import pytest


def open_brief(session_page, site_server, width, lang="ko"):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','%s')" % lang)
    seen = []
    page.on("request", lambda r: seen.append(r.url.split("?")[0].rsplit("/", 1)[-1]))
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(site_server + "brief/", wait_until="networkidle")
    return page, seen


@pytest.mark.parametrize("width", [390, 1440])
def test_first_load_skips_titles_and_full_file(width, session_page, site_server):
    page, seen = open_brief(session_page, site_server, width)
    assert "threads-core.json" in seen
    assert "threads-text.json" not in seen and "threads.json" not in seen
    if width >= 1040:                                             # 미리 그린 PC 오른쪽 칸에도 제목이 있다
        assert page.locator(".pane .ri .l").first.inner_text().strip()


@pytest.mark.parametrize("width", [390, 1440])
def test_opening_a_story_brings_titles_and_original_line(width, session_page, site_server):
    page, seen = open_brief(session_page, site_server, width)
    page.locator(".lanes [data-pick]").nth(1).click()
    row = page.locator(".ri .l").first
    row.wait_for(state="visible")
    assert row.inner_text().strip()
    assert "threads-text.json" in seen
    page.locator(".ri[data-sid]").first.click()
    sheet = page.locator("#det")
    sheet.locator("h2").wait_for(state="visible")
    assert sheet.locator("h2").inner_text().strip()
    assert sheet.locator(".alt").count() == 1 and sheet.locator(".alt").inner_text().strip()   # 한국어 화면의 영어 원문 줄


def test_language_switch_renders_titles(session_page, site_server):
    page, seen = open_brief(session_page, site_server, 1440)
    page.locator('.lang [data-lang="en"]').first.click()
    row = page.locator(".pane .ri .l").first
    row.wait_for(state="visible")
    assert row.inner_text().strip() and "threads-text.json" in seen
