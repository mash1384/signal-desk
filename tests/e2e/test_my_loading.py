"""내 자산의 필수 모듈은 상위 모듈 다운로드가 끝나기를 기다리지 않는다."""
from collections import Counter
from pathlib import PurePosixPath
import time
from urllib.parse import urlsplit


def test_my_dependencies_start_before_parent_modules_finish(session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang','ko');localStorage.setItem('df-my',JSON.stringify(['BTC','ETH','NVDA']));")
    held, requested = [], []
    required = {"common.js", "candles.js", "charts.js"}
    page.on("request", lambda request: requested.append(PurePosixPath(urlsplit(request.url).path).name))
    for name in ("y2.js", "lk.js"):
        page.route("**/assets/df/" + name + "*", lambda route: held.append(route))
    try:
        page.goto(site_server + "my/", wait_until="commit")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and (len(held) < 2 or not required.issubset(requested)):
            page.wait_for_timeout(25)
        before_release = set(requested)
    finally:
        for route in held:
            route.continue_()
    page.wait_for_selector(".srow")
    assert len(held) == 2, "Both parent module responses must be held for the dependency-order check."
    assert required.issubset(before_release), {"late_dependencies": sorted(required - before_release)}
    assert page.locator(".wr").count() == 3
    counts = Counter(requested)
    assert all(counts[name] == 1 for name in required), "Preloaded modules must not download twice."
