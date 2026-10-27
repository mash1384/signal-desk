import datetime as dt
import json
import math
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
import pytest
from playwright.sync_api import sync_playwright
from tests.e2e.server import serve
from tests.e2e.network import Offline, VENDOR

PAGES = ["", "live/", "my/", "themes/crypto/", "brief/", "calendar/", "daily/", "about/"]
BASELINE = Path(__file__).parent / "baseline.json"


def pytest_addoption(parser):
    parser.addoption("--site", default=".qa/build/signal-desk")
    parser.addoption("--flash", default=".qa/snapshot/flash")
    parser.addoption("--matrix", choices=("full", "smoke"), default="full")
    parser.addoption("--capture-baseline", action="store_true")
    # strict: 접근성 기준선과 다르면 실패(고정 스냅샷 + 기준선을 만든 Mac Chrome 에서만 의미가 있다)
    # report: 최신 뉴스로 빌드하는 CI 에서는 요소 위치 · 이야기 ID 가 바뀌어 기준선 비교가 매번 달라지므로 경고로 출력만
    # zero: 기준선 없이 접근성 위반이 하나라도 있으면 실패(2026-10-19 위반 0 달성 후 — main 에 합치기 전 CI 와 매일 검사)
    parser.addoption("--a11y", choices=("strict", "report", "zero"), default="strict")
    # dark: 다크 모드(localStorage df-theme)로 같은 검사. 기준선은 밝은 화면 것이라 --a11y zero 와만 쓴다
    parser.addoption("--theme", choices=("light", "dark"), default="light")
    parser.addoption("--qa-report", default=".qa/e2e.json")
    parser.addoption("--browser-channel", default="chromium" if os.environ.get("CI") else "chrome")


def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames:
        cases = [(p, w, lang) for p in PAGES for w in (1440, 390, 320) for lang in ("ko", "en")]
        if metafunc.config.getoption("--matrix") == "smoke":
            cases = [("live/", 1440, "en"), ("calendar/", 390, "ko")]
        metafunc.parametrize("case", cases, ids=["%s-%s-%s" % (p or "landing", w, lang) for p, w, lang in cases])


@pytest.fixture(scope="session")
def qa(request):
    capture = request.config.getoption("--capture-baseline")
    if capture and BASELINE.exists():
        pytest.fail("baseline exists; automatic replacement forbidden")
    if capture and request.config.getoption("--matrix") != "full":
        pytest.fail("initial baseline requires the complete 48-case matrix")
    if request.config.getoption("--theme") == "dark" and (capture or request.config.getoption("--a11y") != "zero"):
        pytest.fail("--theme dark needs --a11y zero (the baseline is the light theme)")
    baseline = {} if capture else json.loads(BASELINE.read_text())
    state = {"cases": [], "capture": capture, "baseline": baseline, "start": time.monotonic()}
    yield state
    state["seconds"] = round(time.monotonic() - state.pop("start"), 3)
    report = Path(request.config.getoption("--qa-report"))
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({k: v for k, v in state.items() if k != "baseline"}, ensure_ascii=False, indent=2) + "\n")
    if capture:
        if len(state["cases"]) != 48 or any(r.get("incomplete") or r.get("errors") for r in state["cases"]):
            pytest.fail("incomplete matrix: refusing to create a baseline")
        measured = {p: max(r["bytes"] for r in state["cases"] if r["page"] == p) for p in PAGES}
        data = {"measured_bytes": measured, "budget_bytes": {p: math.ceil(v * 1.15) for p, v in measured.items()}, "axe": {r["key"]: r["axe"] for r in state["cases"]}, "measurement": "cold browser; local HTTP response bytes + mocked external response bytes; no production compression or live prices", "axe_version": "4.10.3"}
        BASELINE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


@pytest.fixture(scope="session")
def site_server(request):
    with serve(request.config.getoption("--site")) as base:
        yield base


@pytest.fixture(scope="session")
def browser(request):
    with sync_playwright() as p:
        channel = request.config.getoption("--browser-channel")
        # No browser download here. Missing Chrome/Chromium is a setup failure.
        b = p.chromium.launch(**({} if channel == "chromium" else {"channel": channel}))
        yield b
        b.close()


@pytest.fixture
def session_page(browser, site_server, request):
    context = browser.new_context(viewport={"width": 390, "height": 1000}, locale="en-US", timezone_id="Asia/Seoul", service_workers="block")
    offline = Offline(request.config.getoption("--site"), request.config.getoption("--flash"), site_server)
    offline.attach(context)
    page = context.new_page()
    failures, warnings = [], []

    def our_response(response):
        if response.status < 400:
            return
        url = urlsplit(response.url)
        own = url.netloc == urlsplit(site_server).netloc or (url.hostname == "mash1384.github.io" and url.path.startswith("/signal-desk/"))
        (failures if own else warnings).append({"status": response.status, "url": response.url})

    page.on("response", our_response)
    page.on("pageerror", lambda error: failures.append({"pageerror": str(error)}))
    page.clock.set_fixed_time(dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    page.set_default_timeout(12000)
    yield page, context, offline
    try:
        print("session external warnings", json.dumps(warnings))
        assert not failures, failures
        assert not offline.unmapped, offline.unmapped
    finally:
        context.close()


def axe_script(offline):
    row = offline.manifest["https://cdn.jsdelivr.net/npm/axe-core@4.10.3/axe.min.js"]
    return str(VENDOR / row["file"])
