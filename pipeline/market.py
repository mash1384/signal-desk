"""시세·지표 데이터. 바이낸스가 막히면 코인베이스로 넘어간다."""

import json
import re
import time
from urllib.parse import quote

from . import config, util

_binance_host = None
_binance_dead = False


def _binance(path):
    global _binance_host, _binance_dead
    if _binance_dead:
        raise util.FetchError("binance unavailable")
    hosts = [_binance_host] if _binance_host else config.BINANCE_HOSTS
    for h in hosts:
        try:
            data = util.http_json(h + path, timeout=15, retries=1)
            _binance_host = h
            return data
        except util.FetchError as e:
            # 400은 심볼이 없다는 뜻이라 다른 호스트로 넘어가지 않는다
            if "HTTP 400" in str(e):
                raise
            continue
    _binance_dead = True
    raise util.FetchError("binance unavailable")


_BINANCE_INTERVAL = {60: "1m", 900: "15m", 3600: "1h", 86400: "1d"}


def candles(sym, interval, start, end):
    """[(open_ts, open, close)] 정렬 목록. 바이낸스 → 코인베이스 순서로 시도한다.
    sym은 config.ASSETS 키이거나, 업비트 공지에서 뽑은 임의 티커다."""
    info = config.ASSETS.get(sym, {"binance": sym + "USDT", "coinbase": None})
    out = {}
    if info.get("binance"):
        try:
            t = start
            while t < end:
                rows = _binance("/api/v3/klines?symbol=%s&interval=%s&startTime=%d&endTime=%d&limit=1000"
                                % (info["binance"], _BINANCE_INTERVAL[interval], t * 1000, end * 1000))
                if not rows:
                    break
                for r in rows:
                    out[int(r[0]) // 1000] = (float(r[1]), float(r[4]))
                t = int(rows[-1][0]) // 1000 + interval
                if len(rows) < 1000:
                    break
            if out:
                return sorted((k, v[0], v[1]) for k, v in out.items())
        except util.FetchError as e:
            util.log("binance candles failed", sym, e)
    if info.get("coinbase"):
        try:
            gran = interval
            span = gran * 300
            t = start
            while t < end:
                t2 = min(end, t + span)
                rows = util.http_json("%s/products/%s/candles?granularity=%d&start=%s&end=%s"
                                      % (config.COINBASE_HOST, info["coinbase"], gran, util.iso(t), util.iso(t2)), timeout=15, retries=1)
                for r in rows:  # [time, low, high, open, close, volume]
                    out[int(r[0])] = (float(r[3]), float(r[4]))
                t = t2
                time.sleep(0.15)
            return sorted((k, v[0], v[1]) for k, v in out.items())
        except util.FetchError as e:
            util.log("coinbase candles failed", sym, e)
    return []


def tickers():
    """24시간 시세. {sym: {price, chg, high, low, spark:[...]} }"""
    out = {}
    syms = [config.ASSETS[s]["binance"] for s in config.MARKET_ASSETS]
    try:
        rows = _binance("/api/v3/ticker/24hr?symbols=" + quote(json.dumps(syms, separators=(",", ":"))))
        by = {r["symbol"]: r for r in rows}
        for s in config.MARKET_ASSETS:
            r = by.get(config.ASSETS[s]["binance"])
            if r:
                out[s] = {"price": float(r["lastPrice"]), "chg": float(r["priceChangePercent"]), "src": "binance"}
    except util.FetchError as e:
        util.log("binance tickers failed", e)
    for s in config.MARKET_ASSETS:
        if s in out or not config.ASSETS[s].get("coinbase"):
            continue
        try:
            st = util.http_json("%s/products/%s/stats" % (config.COINBASE_HOST, config.ASSETS[s]["coinbase"]), retries=1)
            last, opn = float(st["last"]), float(st["open"])
            out[s] = {"price": last, "chg": (last / opn - 1) * 100 if opn else 0.0, "src": "coinbase"}
        except (util.FetchError, KeyError, ValueError) as e:
            util.log("coinbase stats failed", s, e)
    now = util.now_ts()
    for s in list(out):
        rows = candles(s, 3600, now - 25 * 3600, now)
        out[s]["spark"] = [round(c, 8) for _, _, c in rows[-24:]]
    return out


def upbit_prices(markets):
    if not markets:
        return {}
    rows = util.http_json(config.UPBIT_TICKER + "?markets=" + ",".join(markets), retries=1)
    return {r["market"]: float(r["trade_price"]) for r in rows}


def fx_usdkrw():
    data = util.http_json(config.FX_URL, retries=1)
    if data.get("result") != "success":
        raise util.FetchError("fx result " + str(data.get("result")))
    return {"rate": float(data["rates"]["KRW"]), "updated": int(data.get("time_last_update_unix") or 0)}


def fear_greed():
    data = util.http_json(config.FNG_URL, retries=1)
    rows = data.get("data") or []
    if not rows:
        raise util.FetchError("fng empty")
    return {
        "value": int(rows[0]["value"]),
        "label": rows[0]["value_classification"],
        "updated": int(rows[0]["timestamp"]),
        "history": [int(r["value"]) for r in rows][::-1],
    }


def kimchi(tick, fx):
    """국내(업비트) 가격 ÷ (해외 USDT 가격 × 원/달러) − 1, 단위 %."""
    markets = [config.ASSETS[s]["upbit"] for s in config.MARKET_ASSETS if config.ASSETS[s].get("upbit") and s in tick]
    krw = upbit_prices(markets)
    out = {}
    for s in config.MARKET_ASSETS:
        m = config.ASSETS[s].get("upbit")
        if m in krw and s in tick and tick[s]["price"] > 0:
            out[s] = {"krw": krw[m], "premium": (krw[m] / (tick[s]["price"] * fx["rate"]) - 1) * 100}
    return out


_IMPACT_KO = {"High": "상", "Medium": "중", "Low": "하"}


def calendar(now):
    """이번 주 경제 일정 중 미국·한국의 중요도 중 이상. 실제치는 이 소스에 없다."""
    rows = util.http_json(config.CALENDAR_URL, retries=1)
    out = []
    for r in rows:
        if r.get("country") not in ("USD", "KRW") or r.get("impact") not in ("High", "Medium"):
            continue
        ts = util.parse_time(r.get("date"))
        if ts is None:
            continue
        out.append({
            "id": "ev-" + util.short_hash(r["country"] + r["title"] + str(ts)),
            "title": r["title"],
            "country": r["country"],
            "ts": ts,
            "level": 3 if r["impact"] == "High" else 2,
            "level_ko": _IMPACT_KO[r["impact"]],
            "forecast": r.get("forecast") or "",
            "previous": r.get("previous") or "",
        })
    out.sort(key=lambda e: e["ts"])
    return out


def upbit_notices():
    data = util.http_json(config.UPBIT_NOTICES, retries=1)
    out = []
    for n in (data.get("data") or {}).get("notices") or []:
        title = n.get("title") or ""
        if "디지털 자산 추가" in title or "신규 거래지원" in title:
            kind = "listing"
        elif "유의 종목" in title or "유의종목" in title:
            kind = "caution"
        elif "거래지원 종료" in title or "거래 지원 종료" in title:
            kind = "delisting"
        else:
            continue
        ts = util.parse_time(n.get("first_listed_at") or n.get("listed_at"))
        if ts is None:
            continue
        syms = re.findall(r"\(([A-Z0-9]{2,10})\)", title)
        out.append({"uid": str(n.get("id")), "title": title, "kind": kind, "ts": ts, "symbols": syms[:4],
                    "url": "https://upbit.com/service_center/notice?id=%s" % n.get("id")})
    return out
