"""실시간 연결(r25, 운영자 "1,000명이 몰려도 무료로"): 연결이 건강하면 Worker 주기 요청(속보 · 전체 · 시세)이 0이고,
서버가 밀어 준 소식이 바로 화면에 뜬다. 빠진 번호 · 끊김 · 조용함이면 지금 방식으로 돌아가고, 장애가 5분 넘으면 느리게(Codex R25-D5).
가짜 연결은 tests/e2e/network.py Offline.ws(실제 서버에 붙지 않는다). 가짜 시계로 몇 분을 몇 초에 돌린다."""
import datetime as dt
from urllib.parse import urlsplit

import pytest

from tests.e2e.network import Offline
from tests.e2e.test_matrix import path_for
from tests.e2e.test_polling import HIDE

FOCUS = "document.hasFocus = () => true; localStorage.setItem('df-lang','ko'); localStorage.setItem('df-my','[\"BTC\",\"ETH\",\"NVDA\"]');"
WORKER = "signal-scheduler.mash1384.workers.dev"


def open_page(browser, site_server, request, route="live/", mode="serve"):
    site, flash = request.config.getoption("--site"), request.config.getoption("--flash")
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
    offline = Offline(site, flash, site_server)
    offline.ws_mode = mode
    offline.attach(context)
    context.add_init_script(FOCUS)
    page = context.new_page()
    errors, reqs = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: reqs.append(r.url))
    page.clock.install(time=dt.datetime.fromtimestamp(offline.now, dt.timezone.utc))
    page.goto(site_server + path_for(route, site), wait_until="networkidle")
    return context, page, offline, errors, reqs


def worker(reqs, start=0):
    """Worker 주기 요청(익명 통계 /e 제외)의 경로 목록"""
    return [urlsplit(u).path for u in reqs[start:] if urlsplit(u).hostname == WORKER and urlsplit(u).path != "/e"]


def tick(page, seconds, offline=None, every=60, step=1):
    """가짜 시계를 step 초씩(긴 장애 구간은 5초씩 — CI 시간). offline 을 주면 every 초마다 서버처럼 시세(지금 시각) · 생존 신호를 밀어 준다"""
    for s in range(step, seconds + 1, step):
        page.clock.run_for(1000 * step)
        page.wait_for_timeout(20)
        if offline is not None and s % every == 0:
            t = page.evaluate("Math.floor(Date.now() / 1000)")
            offline.push({"t": "market", **offline.bundle(t)})


def synced(page):
    return page.evaluate("DFD.stream.healthy()")


@pytest.mark.parametrize("route", ["live/", "my/"])
def test_healthy_stream_makes_zero_worker_polls(browser, site_server, request, route):
    context, page, offline, errors, reqs = open_page(browser, site_server, request, route)
    try:
        tick(page, 3)
        assert synced(page), "hello did not sync the stream"
        start = len(reqs)
        tick(page, 240, offline)                                           # 4분 — 5초 확인 48번 · 전체 받기 8번 · 시세 4번이 있었을 시간
        assert worker(reqs, start) == [], worker(reqs, start)
        assert synced(page)
        assert not errors and not offline.unmapped, (errors, offline.unmapped)
    finally:
        context.close()


def test_coin_prices_still_refresh_from_binance(browser, site_server, request):
    """R25-D2: 연결은 주식 · 지수 · 거시 시세만 대신한다. 코인 시세(바이낸스 직접)는 그대로 갱신돼야 한다"""
    context, page, offline, errors, reqs = open_page(browser, site_server, request, "my/")
    try:
        tick(page, 3)
        start = len(reqs)
        tick(page, 130, offline)
        assert any(urlsplit(u).hostname == "data-api.binance.vision" for u in reqs[start:]), "coin prices stopped"
        assert worker(reqs, start) == [], worker(reqs, start)
    finally:
        context.close()


def test_pushed_item_appears_without_asking(browser, site_server, request):
    context, page, offline, errors, reqs = open_page(browser, site_server, request)
    try:
        tick(page, 3)
        start = len(reqs)
        offline.push({"t": "flash", "at": offline.now + 2, "items": [{"id": "push-1", "t": offline.now + 1, "ko": "밀어받은시험소식", "en": "pushed item", "v": "악재", "s": 2, "kind": "event", "coins": [], "sectors": [], "mw": False, "n": 1}]})
        page.wait_for_function("document.body.innerText.includes('밀어받은시험소식')", timeout=3000)
        assert worker(reqs, start) == []
        assert not offline.flash_new_calls, "must not poll while the stream is healthy"
        assert not errors, errors
    finally:
        context.close()


def test_missing_seq_reconnects_for_a_full_snapshot(browser, site_server, request):
    """R25-D1: 번호가 빠지면(보내다 실패 · 연결 순간 변경) 끊고 다시 연결해 hello(전체)를 받는다"""
    context, page, offline, errors, reqs = open_page(browser, site_server, request)
    try:
        tick(page, 3)
        first = len(offline.ws_urls)
        offline.push({"t": "beat", "at": offline.now}, skip=True)
        page.wait_for_timeout(200)
        assert not synced(page), "a gap must not count as healthy"
        tick(page, 31)                                                     # 동기화됐던 연결은 1~30초에 흩어 다시
        assert len(offline.ws_urls) == first + 1
        assert synced(page)
    finally:
        context.close()


@pytest.mark.parametrize("route", ["live/", "my/"])
def test_server_close_falls_back_to_polling_then_slows_after_5_minutes(browser, site_server, request, route):
    """끊기면 바로 지금 방식(5초 확인)으로. 연결이 5분 넘게 안 돌아오면 5초 확인을 끄고 Worker 요청을 탭당 분당 약 2번으로(R25-D5).
    Hub 가 돌아오면 늦어도 약 7.5분 안에 다시 동기화(조용한 연결 150초 + 5번 실패 뒤 5분 쉼)"""
    context, page, offline, errors, reqs = open_page(browser, site_server, request, route)
    try:
        tick(page, 3)
        assert synced(page)
        offline.ws_mode = "silent"                                         # 다시 연결돼도 hello 가 없다(Hub 장애)
        offline.close_ws()
        tick(page, 12)
        assert offline.flash_new_calls, "fallback polling did not start"
        tick(page, 300, step=5)                                            # 장애 5분
        start, calls = len(reqs), len(offline.flash_new_calls)
        tick(page, 300, step=5)                                            # 그다음 5분
        assert len(offline.flash_new_calls) == calls, "5-second checks must stop after 5 minutes of outage"
        seen = worker(reqs, start)
        assert len(seen) <= 12, seen                                       # 장애 중 탭당 5분 12번 이하(전체 1분 · 시세 2분 주기, 지금 방식 그대로면 약 70)
        assert any(p in ("/live", "/flash") for p in seen), "news still refreshes (slowly) during the outage"
        offline.ws_mode = "serve"                                          # Hub 복구 → 다음 다시 연결에서 동기화
        tick(page, 700, offline, step=5)                                           # 실제 Hub 처럼 매분 메시지(없으면 150초마다 조용함 → 다시 연결 순간에 걸릴 수 있다)
        assert synced(page), "stream did not come back after the outage"
    finally:
        context.close()


def test_hidden_tab_with_stream_makes_no_requests(browser, site_server, request):
    context, page, offline, errors, reqs = open_page(browser, site_server, request)
    try:
        tick(page, 3)
        page.evaluate(HIDE, True)
        start = len(reqs)
        tick(page, 300, offline, step=5)
        assert worker(reqs, start) == [], worker(reqs, start)
    finally:
        context.close()


def test_stale_market_push_is_not_used(browser, site_server, request):
    """R25-D2: 연결은 살아 있어도(생존 신호만 옴) 시세가 150초 넘게 안 바뀌면 지금 방식으로 시세를 묻는다"""
    context, page, offline, errors, reqs = open_page(browser, site_server, request, "my/")
    try:
        tick(page, 3)
        start = len(reqs)
        for _ in range(4):                                                 # 4분 동안 beat 만
            tick(page, 60)
            offline.push({"t": "beat", "at": offline.now})
        assert synced(page)
        assert any(p in ("/market", "/live") for p in worker(reqs, start)), worker(reqs, start)
        assert not offline.flash_new_calls, "news stays on the stream"
    finally:
        context.close()


def test_delay_notice_works_when_only_market_messages_arrive(browser, site_server, request):
    """R25-F2: 속보 전달만 멈추고 시세 알람은 계속 오면, 시세 메시지의 문서 시각으로 '업데이트 지연'을 띄운다"""
    context, page, offline, errors, reqs = open_page(browser, site_server, request)
    try:
        tick(page, 3)
        assert not page.locator("#stale:visible").count()
        old = offline.now - 1500                                          # 마지막 문서가 25분 전
        offline.push({"t": "market", "at": old, **offline.bundle(offline.now + 3)})
        page.wait_for_selector("#stale:visible", timeout=3000)
        assert synced(page), "the socket itself is fine"
    finally:
        context.close()


def test_messages_without_hello_do_not_keep_a_connection_alive(browser, site_server, request):
    """hello 없이 다른 메시지만 오는 연결은 150초 뒤 버리고 다시 연결한다(그렇지 않으면 영영 동기화 못 하고 붙어 있다)"""
    context, page, offline, errors, reqs = open_page(browser, site_server, request, mode="silent")
    try:
        tick(page, 3)
        first = len(offline.ws_urls)
        tick(page, 200, offline, every=20)                                 # 20초마다 시세만(hello 없음)
        assert len(offline.ws_urls) > first, "a connection that never synced must be replaced"
        assert not synced(page)
    finally:
        context.close()
