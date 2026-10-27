"""누르는 동작이 실제로 되는지: 테마 페이지의 근거 · 정렬 · 섹터 · 소식 열기, 테마 탭.
2026-10-20 다크 모드가 <html data-theme> 을 붙인 뒤 테마 탭 찾기([data-theme])가 문서 전체에 걸려, 테마 페이지의 모든 누름이 오류로 끝났다."""
import datetime as dt

from tests.e2e.network import Offline


def open_page(browser, site_server, request, route, width=1440, theme="light", falling=False):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    context = browser.new_context(viewport={"width": width, "height": 1000}, service_workers="block")
    offline = Offline(site, flash, site_server)
    if falling:   # 가격이 계속 내리는 자료: 마지막 가격이 차트 맨 아래에 온다(가격표가 아래 끝에서 잘리는지 보려고)
        offline.series = lambda n, step=60, start=None: [[(offline.now - (n - 1) * step if start is None else start) + i * step, round(100 - i * .01, 2)] for i in range(n)]
    offline.attach(context)
    context.add_init_script("localStorage.setItem('df-lang','ko'); localStorage.setItem('df-theme','%s');"
                            "Object.defineProperty(navigator, 'doNotTrack', {get: () => '1'});" % theme)
    page = context.new_page()
    page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site_server + route, wait_until="networkidle")
    return context, page, errors


def sheet_title(page):
    page.locator("#sheet.on").wait_for(timeout=5000)
    return page.locator("#sheet h2").first.inner_text().strip()


def close_sheet(page):
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)


def test_theme_page_clicks(browser, site_server, request):
    for theme in ("light", "dark"):
        context, page, errors = open_page(browser, site_server, request, "themes/crypto/", theme=theme)
        try:
            page.locator(".sum .ref").first.wait_for(timeout=7000)
            page.locator(".sum .ref").first.click()                 # AI 요약의 근거
            assert sheet_title(page), "source story sheet is empty"
            close_sheet(page)
            page.locator("#stories [data-id]").first.click()        # 주요 소식
            assert sheet_title(page)
            close_sheet(page)
            page.locator("[data-sort]").nth(1).click()              # 정렬
            page.locator("[data-sec]").first.click()                # 섹터 고르기
            page.locator("[data-tk='nasdaq']").click()              # 테마 탭(주소도 바뀐다)
            page.wait_for_function("location.pathname.endsWith('/themes/nasdaq/')")
            assert page.locator("[data-tk='nasdaq'][aria-selected='true']").count() == 1
            assert not errors, (theme, errors)
        finally:
            context.close()


LABEL_ROWS = """() => [...document.querySelectorAll('#sheet .lwc .lwbox')].map((box) => {
  // 가격 눈금 칸(오른쪽 좁은 캔버스)에서 색이 진한 가로줄(= 마지막 가격표 바탕)의 위치: 칸의 위 · 아래 끝에 닿으면 잘린 것
  const cvs = [...box.querySelectorAll('canvas')].filter((c) => c.width && c.getBoundingClientRect().width < 120 && c.getBoundingClientRect().left > box.getBoundingClientRect().left + 100);
  for (const c of cvs) { const g = c.getContext('2d'); if (!g) continue; const d = g.getImageData(0, 0, c.width, c.height).data; let top = -1, bottom = -1;
    for (let y = 0; y < c.height; y++) { let n = 0;
      for (let x = 0; x < c.width; x++) { const k = (y * c.width + x) * 4, r = d[k], gg = d[k + 1], b = d[k + 2], a = d[k + 3];
        if (a > 200 && Math.max(r, gg, b) - Math.min(r, gg, b) > 60) n++; }
      if (n > c.width * 0.5) { if (top < 0) top = y; bottom = y; } }
    if (top >= 0) return { top, gap: c.height - 1 - bottom, h: c.height }; }
  return null; })"""


def test_story_sheet_price_tag_not_clipped(browser, site_server, request):
    # 상세 창의 작은 차트(높이 120): 계속 내린 가격의 마지막 가격표(바탕 높이 약 17px)가 아래 끝에서 잘리지 않는다. 소식 여러 개를 열어 본다
    context, page, errors = open_page(browser, site_server, request, "live/", width=390, falling=True)
    try:
        page.locator("#grid [data-id]").first.wait_for(timeout=7000)
        heights = []
        for i in range(min(8, page.locator("#grid [data-id]").count())):
            page.locator("#grid [data-id]").nth(i).click()
            try:
                page.locator("#sheet.on .lwc .lwbox canvas").first.wait_for(timeout=4000)
            except Exception:
                close_sheet(page)
                continue
            page.wait_for_timeout(500)
            heights += [r for r in page.evaluate(LABEL_ROWS) if r]
            close_sheet(page)
        assert heights, "no price tag measured"
        assert all(r["top"] > 0 and r["gap"] > 0 for r in heights), heights   # 위 · 아래 끝에 닿지 않는다
        assert not errors, errors
    finally:
        context.close()
