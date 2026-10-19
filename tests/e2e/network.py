"""Offline browser transport: git snapshots + pinned static assets + small market fakes.
No route ever continues to a remote host. External failures are reported separately.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

VENDOR = Path(__file__).parent / "vendor"


class Offline:
    def __init__(self, site, flash, base, live_mode='modern'):
        self.site, self.flash, self.base = Path(site), Path(flash), base
        self.live_mode = live_mode
        self.host = urlsplit(base).netloc
        self.now = json.loads((self.flash / "flash.json").read_text())["at"]
        self.manifest = json.loads((VENDOR / "manifest.json").read_text())
        self.unmapped = []
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

    def handle(self, route):
        req = route.request
        url = urlsplit(req.url)
        if url.netloc == self.host:
            route.continue_()
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
