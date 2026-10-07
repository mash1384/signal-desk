"""뉴스 임팩트 실측.

기사 기준 시각 t0부터 15분·1시간·24시간 수익률을 재고,
최근 같은 길이 구간 수익률의 표준편차로 나눠 강도 점수를 낸다.
상관을 잴 뿐 인과를 주장하지 않는다.
"""

import math

from . import config, market, util

STATS_TTL = 6 * 3600
_STAT_SOURCE = {"15m": (900, 7 * 86400), "1h": (3600, 30 * 86400), "24h": (86400, 180 * 86400)}


def _sd(values):
    if len(values) < 20:
        return None
    m = sum(values) / len(values)
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var) if var > 0 else None


def volatility(sym, cache, now):
    """{window: sd} — 같은 길이 봉의 (종가/시가 − 1) 표준편차. 6시간마다 다시 계산한다."""
    entry = cache.get(sym)
    if entry and now - entry.get("at", 0) < STATS_TTL and entry.get("sd"):
        return entry["sd"]
    sd = {}
    for win, (interval, lookback) in _STAT_SOURCE.items():
        rows = market.candles(sym, interval, now - lookback, now - interval)
        rets = [c / o - 1 for _, o, c in rows if o > 0]
        val = _sd(rets)
        if val:
            sd[win] = val
    if sd:
        cache[sym] = {"at": now, "sd": sd}
    return sd


def grade(z):
    a = abs(z)
    if a >= config.GRADE_STRONG:
        return "강"
    if a >= config.GRADE_MEDIUM:
        return "중"
    return "약"


def assets_for(article):
    if article.get("category") == "crypto":
        base = ["BTC", "ETH"] if article.get("source") != "upbit-notice" else []
        extra = [a for a in article.get("assets", []) if a not in base]
        out = (extra + base)[: config.MAX_ASSETS_PER_ARTICLE]
        return out or ["BTC"]
    return ["BTC"]


def _pending(article, now):
    """아직 잴 수 있는 (자산, 구간) 목록. 데이터가 확정될 시간을 2분 더 기다린다."""
    out = []
    imp = article.setdefault("impact", {})
    for sym in assets_for(article):
        done = imp.get(sym, {})
        for win, secs in config.WINDOWS:
            if win in done:
                continue
            if now >= article["t0"] + secs + 120:
                out.append((sym, win, secs))
    return out


def measure(articles, vol_cache, now):
    """측정할 수 있는 모든 기사·자산·구간을 채운다. 1분봉은 자산별로 한 번에 받아 재사용한다."""
    todo = []
    for a in articles:
        if a.get("impact_status") in ("done", "failed"):
            continue
        p = _pending(a, now)
        if p:
            todo.append((a, p))
    if not todo:
        return 0
    need = {}
    for a, pend in todo:
        for sym, _win, secs in pend:
            lo, hi = need.get(sym, (a["t0"], a["t0"] + secs))
            need[sym] = (min(lo, a["t0"]), max(hi, a["t0"] + secs))
    minute = {}
    for sym, (lo, hi) in need.items():
        rows = market.candles(sym, 60, (lo // 60) * 60 - 120, min(now, hi + 180))
        minute[sym] = {ts: (o, c) for ts, o, c in rows}
        util.log("candles", sym, len(rows))
    filled = 0
    for a, pend in todo:
        imp = a["impact"]
        missed = False
        for sym, win, secs in pend:
            book = minute.get(sym) or {}
            start = (a["t0"] // 60) * 60
            end = ((a["t0"] + secs) // 60) * 60 - 60
            if start in book and end in book and book[start][0] > 0:
                ret = book[end][1] / book[start][0] - 1
                sd = volatility(sym, vol_cache, now).get(win)
                z = round(ret / sd, 2) if sd else None
                imp.setdefault(sym, {})[win] = {"r": round(ret * 100, 3), "z": z, "g": grade(z) if z is not None else None}
                filled += 1
            else:
                missed = True
                # 일시 장애로 영구 실패가 되지 않도록, 6시간이 지나고 8번 넘게 못 잰 경우에만 포기한다
                if now - (a["t0"] + secs) > 6 * 3600 and a.get("impact_tries", 0) >= 8:
                    imp.setdefault(sym, {})[win] = {"r": None, "z": None, "g": None}
        if missed:
            a["impact_tries"] = a.get("impact_tries", 0) + 1
        _finalize(a, now)
    return filled


def _finalize(a, now):
    imp = a.get("impact") or {}
    syms = assets_for(a)
    total = len(syms) * len(config.WINDOWS)
    have = sum(1 for s in syms for w, _ in config.WINDOWS if w in imp.get(s, {}))
    measured = [(s, w, v) for s in syms for w, v in imp.get(s, {}).items() if v.get("r") is not None]
    if have >= total:
        a["impact_status"] = "done" if measured else "failed"
    else:
        a["impact_status"] = "measuring"
    a["headline"] = headline(a)


def headline(a):
    """카드에 보일 대표 값: 주 자산의 1시간(없으면 15분) 반응."""
    imp = a.get("impact") or {}
    for sym in assets_for(a):
        for win in ("1h", "15m"):
            v = imp.get(sym, {}).get(win)
            if v and v.get("r") is not None:
                return {"asset": sym, "win": win, "r": v["r"], "g": v["g"]}
    return None


def concurrency(articles):
    """기준 시각 ±15분 안의 다른 주요 기사 수."""
    major = sorted((a["t0"], a["id"]) for a in articles if a.get("importance", 1) >= 2)
    for a in articles:
        a["concurrent"] = sum(1 for t, i in major if i != a["id"] and abs(t - a["t0"]) <= config.CONCURRENT_EVENT_SECONDS)


def type_stats(articles):
    """/impact 페이지용: 이벤트 유형별 BTC 1시간 반응 통계. 표본 3건 미만 유형은 뺀다."""
    labels = {k: label for k, label, _ in config.EVENT_TYPES}
    groups = {}
    for a in articles:
        v = (a.get("impact") or {}).get("BTC", {}).get("1h")
        if not v or v.get("r") is None or a.get("etype") in (None, "other"):
            continue
        groups.setdefault(a["etype"], []).append((v["r"], v["g"]))
    out = []
    for k, rows in groups.items():
        if len(rows) < 3:
            continue
        rs = [r for r, _ in rows]
        out.append({
            "type": k, "label": labels.get(k, k), "n": len(rows),
            "mean": round(sum(rs) / len(rs), 3),
            "mean_abs": round(sum(abs(r) for r in rs) / len(rs), 3),
            "strong_share": round(sum(1 for _, g in rows if g == "강") / len(rows), 3),
        })
    out.sort(key=lambda x: -x["mean_abs"])
    return out


def strongest(articles, now, days=7, limit=12):
    rows = []
    for a in articles:
        if now - a["t0"] > days * 86400:
            continue
        best = None
        for sym, wins in (a.get("impact") or {}).items():
            for win, v in wins.items():
                if v.get("z") is None or v.get("r") is None:
                    continue
                if best is None or abs(v["z"]) > abs(best[2]):
                    best = (sym, win, v["z"], v["r"], v["g"])
        if best:
            rows.append({"id": a["id"], "title": a["title"], "asset": best[0], "win": best[1], "z": best[2], "r": best[3], "g": best[4], "t0": a["t0"]})
    rows.sort(key=lambda r: -abs(r["z"]))
    return rows[:limit]
