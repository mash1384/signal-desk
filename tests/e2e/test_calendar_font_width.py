"""일정 본문 폭은 대체 글꼴의 숫자 폭에 따라 줄었다 늘지 않아야 한다."""
import pytest


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_calendar_paragraph_width_survives_font_swap(lang, session_page, site_server):
    page, context, _ = session_page
    page.set_viewport_size({"width": 1440, "height": 1000})
    context.add_init_script("localStorage.setItem('df-lang', '%s')" % lang)
    page.goto(site_server + "calendar/", wait_until="networkidle")
    # 실시간 지표가 없는 날에도 같은 CSS 계약을 검사하도록 고정 본문을 쓴다.
    page.evaluate("""() => {
      const host=document.createElement('div'); host.className='it'; host.style.width='900px';
      const p=document.createElement('p'); p.id='font-width-probe'; p.textContent='지표 0 · Indicator 0';
      host.append(p); document.body.append(host);
    }""")
    assert page.evaluate('document.fonts.load(\'15.5px "Pretendard Variable"\', "0").then(f=>f.length>0)')
    page.evaluate("document.fonts.ready")
    paragraph = page.locator("#font-width-probe")
    paragraph.wait_for(state="visible")
    widths = paragraph.evaluate("""p => {
      const original=p.style.fontFamily;
      const final=p.getBoundingClientRect().width;
      p.style.fontFamily='monospace';
      const fallback=p.getBoundingClientRect().width;
      p.style.fontFamily=original;
      return {final,fallback,restored:p.getBoundingClientRect().width};
    }""")
    assert widths["final"] > 0
    assert abs(widths["fallback"] - widths["final"]) <= 0.02, widths
    assert widths["restored"] == widths["final"], widths
