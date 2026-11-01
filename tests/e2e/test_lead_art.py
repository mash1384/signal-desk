"""소식 그림(점묘화, art.js): 큰 소식 카드 — PC는 글 오른쪽, 휴대폰은 접힌 카드 아래 띠. 그림은 글 아래 층, 테마가 바뀌면 글자색으로 다시,
펼치면 휴대폰 띠는 숨고, 사진이면 출처 링크가 있다. 그림 파일은 같은 사이트에서만 받는다."""
from playwright.sync_api import expect

INK = """(sel) => { const c = document.querySelector(sel); if (!c) return null; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let n = 0, r = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 40) { n++; r += d[i - 3]; } return n ? [n, r / n] : [0, 0]; }"""


def test_lead_art(session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','ko');localStorage.setItem('df-theme','light')")
    urls = []
    page.on('request', lambda r: urls.append(r.url))
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(site_server + 'live/', wait_until='networkidle')
    pc = page.locator('#lead .ld > canvas.art')
    expect(pc).to_have_count(1)
    n, light = page.evaluate(INK, '#lead .ld > canvas.art')
    assert n > 1500, "점이 거의 없다(%d)" % n
    assert light < 90, "밝은 화면에서는 진한 글자색 점이어야 한다(%s)" % light
    # 그림은 글 아래 층: 제목 가운데를 누르면 제목(소식 단추)이 눌린다
    hit = page.evaluate("() => { const h = document.querySelector('#lead .ld h1').getBoundingClientRect(); return document.elementFromPoint(h.left + h.width * .8, h.top + h.height / 2).closest('.tx') !== null; }")
    assert hit, "그림이 글 위를 덮었다"
    art_urls = [u for u in urls if '/assets/art/' in u]
    assert art_urls and all(u.startswith(site_server.split('/signal-desk/')[0]) for u in art_urls), art_urls
    cr = page.locator('#lead .ld > .art-cr')
    if cr.count():
        expect(cr.locator('a').first).to_have_attribute('href', __import__('re').compile(r'^https://'))
        expect(cr).to_contain_text('사진')
    # 어두운 화면: 다시 그려 밝은 점
    page.locator('[data-theme-toggle]').first.click()
    expect(pc).to_have_count(1)
    page.wait_for_function("() => { const c = document.querySelector('#lead .ld > canvas.art'); if (!c) return false; const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; for (let i = 3; i < d.length; i += 4) if (d[i] > 40) return d[i - 3] > 150; return false; }")
    # 휴대폰: 접힌 카드 아래 띠, PC 그림은 없다
    page.set_viewport_size({"width": 390, "height": 900})
    band = page.locator('#lead > canvas.art')
    expect(band).to_have_count(1)
    expect(pc).to_have_count(0)
    box, title = band.bounding_box(), page.locator('.lead-title').bounding_box()
    assert box['y'] >= title['y'] + title['height'] - 2, "띠가 제목을 덮는다"
    page.locator('.lead-preview').click()
    expect(band).to_be_hidden()
    page.locator('.lead-preview').click()
    expect(page.locator('#lead > canvas.art')).to_be_visible()
