"""Offline browser transport: git snapshots + pinned static assets + small market fakes.
No route ever continues to a remote host. External failures are reported separately.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, parse_qsl, urlsplit

VENDOR = Path(__file__).parent / "vendor"


class Offline:
    def __init__(self, site, flash, base, live_mode='modern'):
        self.site, self.flash, self.base = Path(site), Path(flash), base
        self.live_mode = live_mode
        self.host = urlsplit(base).netloc
        self.now = json.loads((self.flash / "flash.json").read_text())["at"]
        self.manifest = json.loads((VENDOR / "manifest.json").read_text())
        self.unmapped = []
        self.flash_new_calls, self.flash_new_extra, self.flash_new_status = [], [], None
        self.beacons = []
        # 실시간 연결(r25) 가짜: 기본 'silent' = 열리지만 아무것도 안 보냄(동기화 안 됨 → 지금 방식 그대로).
        # 'serve' = hello(스냅샷 문서 전체 + 시세)를 보내고, 시험이 push() 로 다음 seq 메시지를 보낸다
        self.ws_mode, self.ws_open, self.ws_urls, self.ws_seq = "silent", [], [], 1
        for row in self.manifest.values():
            data = (VENDOR / row["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("vendor hash mismatch: " + row["file"])

    def series(self, n, step=60, start=None):
        start = self.now - (n - 1) * step if start is None else start
        return [[start + i * step, round(100 + i * .01, 2)] for i in range(n)]

    def market(self):
        syms = "NQ=F ES=F NVDA AAPL MSFT AMZN GOOGL META TSLA AVGO AMD TSM PLTR ^TNX ^FVX DX-Y.NYB GC=F CL=F KRW=X".split()
        return {"q": {s: {"p": 100.24, "chg": .24, "c": self.series(300, 300)} for s in syms}, "at": self.now}

    def bundle(self, at=None):
        at = self.now if at is None else at
        m = {**self.market(), "at": at}
        return {"market": {"1h": {**m, "i": "1h"}, "5m": {**m, "i": "5m"}},
                "indices": {"nq": {"c": self.series(1000), "at": at}, "es": {"c": self.series(1000), "at": at}}}

    def ws(self, ws):
        # WebSocket 은 route() 로 잡히지 않는다 — 모든 연결을 여기서 가짜로 받아 실제 서버에 붙지 않게 한다.
        # 주의: Playwright 동기 API 는 이 처리기 안에서 ws.close() 를 부르면 멈춘다 → 닫기는 시험 쪽에서 close_ws()
        self.ws_urls.append(ws.url)
        u = urlsplit(ws.url)
        if u.scheme != "wss" or u.netloc != "signal-scheduler.mash1384.workers.dev" or u.path != "/ws":
            self.unmapped.append(ws.url)
            return
        self.ws_open.append(ws)
        if self.ws_mode == "serve":
            ws.send(json.dumps({"t": "hello", "v": 2, "seq": self.ws_seq, "doc": json.loads((self.flash / "flash.json").read_text()), "market": self.bundle()}))

    def push(self, msg, skip=False):
        self.ws_seq += 2 if skip else 1
        for ws in self.ws_open:
            ws.send(json.dumps({**msg, "seq": self.ws_seq}))

    def close_ws(self):
        for ws in self.ws_open:
            ws.close()
        self.ws_open = []

    def attach(self, context):
        context.route("**/*", self.handle)
        context.route_web_socket(re.compile(r".*"), self.ws)

    def handle(self, route):
        req = route.request
        url = urlsplit(req.url)
        if url.netloc == self.host:
            route.continue_()
            return
        # 익명 방문 통계(Worker /e, sendBeacon POST · 이미지 GET)만 허용: 응답은 가짜로, 보낸 이벤트는 self.beacons 에 남긴다
        if url.hostname == "signal-scheduler.mash1384.workers.dev" and url.path == "/e":
            self.beacons.append(dict(parse_qsl(url.query)))
            route.fulfill(status=204 if req.method == "POST" else 200, body=b"", headers={"access-control-allow-origin": "*"})
            return
        if req.method != "GET":
            raise AssertionError("E2E forbids non-GET external request")
        headers = {"access-control-allow-origin": "*"}

        def file_response(path, mime="application/json"):
            if path.is_file():
                route.fulfill(body=path.read_bytes(), content_type=mime, headers=headers)
            else:
                route.fulfill(status=404, body="missing snapshot", headers=headers)

        def respond(doc):
            route.fulfill(json=doc, headers=headers)

        if req.url in self.manifest:
            row = self.manifest[req.url]
            file_response(VENDOR / row["file"], row["type"])
        elif url.hostname == "raw.githubusercontent.com" and url.path.startswith("/mash1384/signal-desk/flash/"):
            file_response(self.flash / url.path.split("/flash/", 1)[1])
        elif url.hostname == "mash1384.github.io" and url.path.startswith("/signal-desk/"):
            file_response(self.site / url.path.split("/signal-desk/", 1)[1])
        elif url.hostname == "signal-scheduler.mash1384.workers.dev":
            if url.path == "/live":
                if self.live_mode == 'disconnect':
                    route.abort()
                elif self.live_mode in ('legacy', 'error'):
                    route.fulfill(status=404 if self.live_mode == 'legacy' else 502, body='fixture unavailable', headers=headers)
                elif self.live_mode == 'malformed':
                    respond({'v': 1, 'flash': {'items': []}})
                else:
                    respond({'v': 1, 'flash': json.loads((self.flash / 'flash.json').read_text()),
                             'market': {'1h': self.market(), '5m': self.market()},
                             'indices': {'nq': {'c': self.series(1000)}, 'es': {'c': self.series(1000)}}})
            elif url.path == "/flash":
                file_response(self.flash / "flash.json")
            elif url.path == "/flash/new":
                # 속보 빠른 확인(2026-10-26): 보낸 after 를 남기고, 시험이 넣은 새 소식(flash_new_extra)까지 after 보다 새 것만
                after = float(dict(parse_qsl(url.query)).get("after", 0))
                self.flash_new_calls.append(after)
                if self.flash_new_status:
                    route.fulfill(status=self.flash_new_status, body="fixture unavailable", headers={**headers, "retry-after": "60"})
                    return
                doc = json.loads((self.flash / "flash.json").read_text())
                items = [it for it in self.flash_new_extra + doc["items"] if it.get("t", 0) > after]
                respond({"at": doc.get("at", self.now), "items": items})
            elif url.path in ("/market", "/quotes"):
                respond(self.market())
            elif url.path == "/index-candles":
                respond({"c": self.series(1000)})
            else:
                self.unmapped.append(req.url)
                route.fulfill(status=502, body="unmapped worker fixture", headers=headers)
        elif url.hostname == "data-api.binance.vision":
            q = parse_qs(url.query)
            if url.path.endswith("/ticker/24hr"):
                syms = json.loads(q["symbols"][0]) if "symbols" in q else [q.get("symbol", ["BTCUSDT"])[0]]
                data = [{"symbol": s, "lastPrice": "100.24", "priceChangePercent": "0.24"} for s in syms]
                respond(data if "symbols" in q else data[0])
            elif url.path.endswith("/klines"):
                n = int(q.get("limit", ["300"])[0])
                step = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}[q.get("interval", ["1m"])[0]]
                # Binance returns UTC-aligned candle opens >= startTime, not
                # a new time grid beginning at an arbitrary story second.
                start = ((int(q["startTime"][0]) + step * 1000 - 1) // (step * 1000)) * step if "startTime" in q else None
                # endTime selects a suffix of the same deterministic 1000-row
                # series, so overlapping chart points never depend on limit.
                points = self.series(1000, step)[-n:] if "endTime" in q else self.series(n, step, start)
                # The real API never emits future klines (the old fake did).
                if start is not None:
                    points = [p for p in points if p[0] <= self.now]
                respond([[t * 1000, str(p), str(p + 1), str(p - 1), str(p + .1), "10", (t + step) * 1000] for t, p in points])
            else:
                self.unmapped.append(req.url)
                route.fulfill(status=502, body="unmapped binance fixture", headers=headers)
        else:
            self.unmapped.append(req.url)
            route.fulfill(status=502, body="external fixture absent", headers=headers)
