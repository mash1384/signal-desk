"""라이브 '소식 후 가격'(2026-10-27 운영자: ETH 추가 · 버튼이 무엇인지 알게 이름표): 이름표가 보이고, ETH 를 누르면
카드 · 큰 차트가 바이낸스 ETH/USDT 로 그려진다. 고른 것은 다음 방문에도 남는다."""
import datetime as dt
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for


@pytest.mark.parametrize("width,lang,label", [(390, "ko", "소식 후 가격"), (1440, "en", "Price after news")])
def test_label_and_eth(browser, site_server, request, width, lang, label):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    ctx = browser.new_context(viewport={"width": width, "height": 900}, is_mobile=width < 900, service_workers="block")
    offline = Offline(site, flash, site_server)
    offline.attach(ctx)
    ctx.add_init_script("localStorage.setItem('df-lang', '%s'); localStorage.removeItem('df-mkt');" % lang)
    page = ctx.new_page()
    page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))   # 스냅샷 시각(카드가 24시간 안에 들도록)
    errors, pairs = [], []
    page.on("pageerror", lambda e, bag=errors: bag.append(str(e)))
    page.on("request", lambda r, bag=pairs: bag.append(parse_qs(urlsplit(r.url).query).get("symbol", [""])[0]) if "/klines" in r.url else None)
    try:
        page.goto(site_server + path_for("live/", site), wait_until="networkidle")
        seg = [s for s in page.locator(".ghl").all() if s.is_visible() and s.locator("[data-mkt]").count()][0]
        assert seg.inner_text().startswith(label), seg.inner_text()
        assert [b.inner_text() for b in seg.locator("[data-mkt]").all()][:2] == ["BTC", "ETH"]
        start = len(pairs)
        seg.locator("[data-mkt=eth]").click()
        page.wait_for_function("[...document.querySelectorAll('[data-mname]')].some(e => e.textContent === 'ETH')", timeout=5000)
        page.wait_for_timeout(800)
        assert "ETHUSDT" in pairs[start:], pairs[start:]
        assert page.evaluate("localStorage.getItem('df-mkt')") == "eth"
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), "no horizontal overflow"
        assert not errors, errors
    finally:
        ctx.close()
