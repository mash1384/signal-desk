"""테마 흐름 그래프 자리: 차트가 오기 전 빈 칸(#flow:empty)의 높이가 차트가 들어온 뒤의 높이와 같아야 한다.
다르면 차트가 들어올 때 아래 상자가 밀리거나(CLS) 최종 화면이 달라진다(2026-10-21 릴레이 R2-4, web/df_themes.html)."""
import pytest


@pytest.mark.parametrize("width", [1440, 600, 390])
def test_empty_flow_slot_matches_chart(width, session_page, site_server):
    page, _, _ = session_page
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(site_server + "themes/crypto/", wait_until="networkidle")
    page.locator("#flow").scroll_into_view_if_needed()
    page.wait_for_function("document.querySelector('#flow .lwbox canvas')", timeout=10000)
    full, empty = page.evaluate("""() => { const f = document.querySelector('#flow'), e = document.createElement('div');
      e.id = 'flow'; f.id = 'flow-real'; f.after(e); const h = [f.getBoundingClientRect().height, e.getBoundingClientRect().height];
      e.remove(); f.id = 'flow'; return h; }""")
    assert empty > 0 and abs(full - empty) < 0.5, (width, full, empty)
