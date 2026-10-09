"""맵(SIGNAL Map) 데이터.

코인 12개의 가격·등락·거래대금, 함께 움직이는 정도(7일 1시간 수익률 상관), 화면 위치,
최근 7일 뉴스와 코인별 측정 반응을 한 파일로 만든다. 위치는 지난 값과 섞어 매번 크게 흔들리지 않게 한다.
"""

import math

from . import config, market, util

WINDOW_DAYS = 7
LINK_MIN = 0.6
POS_KEEP = 0.8  # 지난 위치를 얼마나 유지할지


def hourly(syms, now):
    """{sym: [(open_ts, open, close)]} 최근 30일 1시간 봉."""
    out = {}
    for s in syms:
        rows = market.candles(s, 3600, now - 30 * 86400, now)
        if rows:
            out[s] = rows
    return out


def returns(rows, since):
    return {t: c / o - 1 for t, o, c in rows if t >= since and o > 0}


def corr(a, b):
    keys = sorted(set(a) & set(b))
    if len(keys) < 48:
        return None
    x = [a[k] for k in keys]
    y = [b[k] for k in keys]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxy = sum((p - mx) * (q - my) for p, q in zip(x, y))
    sx = math.sqrt(sum((p - mx) ** 2 for p in x))
    sy = math.sqrt(sum((q - my) ** 2 for q in y))
    return sxy / (sx * sy) if sx and sy else None


def layout(syms, cmat, prev):
    """BTC는 가운데. 반지름 = BTC와 덜 같이 움직일수록 바깥(1 − 상관), 각도 = 서로 비슷한 코인끼리 이웃하게(고전 MDS의 각도 순서)를
    유지한 채 둘레에 고르게 펼친다. 결정적이고, 지난 위치와 섞어 크게 흔들리지 않게 한다."""
    others = [s for s in syms if s != "BTC"]
    n = len(others)
    if not n:
        return {"BTC": [0.0, 0.0]}
    d2 = [[(1 - (cmat.get((a, b)) if cmat.get((a, b)) is not None else 0)) ** 2 if a != b else 0.0 for b in others] for a in others]
    rm = [sum(r) / n for r in d2]
    gm = sum(rm) / n
    bmat = [[-0.5 * (d2[i][j] - rm[i] - rm[j] + gm) for j in range(n)] for i in range(n)]

    def power(mat, avoid=None):
        v = [1.0 + 0.01 * i for i in range(n)]
        for _ in range(300):
            w = [sum(mat[i][j] * v[j] for j in range(n)) for i in range(n)]
            if avoid:
                dot = sum(w[i] * avoid[i] for i in range(n))
                w = [w[i] - dot * avoid[i] for i in range(n)]
            norm = math.sqrt(sum(x * x for x in w)) or 1
            v = [x / norm for x in w]
        return v
    v1 = power(bmat)
    v2 = power(bmat, v1)
    order = sorted(range(n), key=lambda i: math.atan2(v2[i], v1[i]))
    # ETH부터 시계 방향으로 고르게
    if "ETH" in others:
        k = order.index(others.index("ETH"))
        order = order[k:] + order[:k]
    far = [1 - (cmat.get(("BTC", s)) if cmat.get(("BTC", s)) is not None else 0) for s in others]
    lo, hi = min(far), max(far)
    pos = {"BTC": [0.0, 0.0]}
    for rank, i in enumerate(order):
        ang = -math.pi / 2 + 2 * math.pi * rank / n
        rad = 0.42 + 0.58 * ((far[i] - lo) / (hi - lo) if hi > lo else 0.5)
        x, y = rad * math.cos(ang), rad * math.sin(ang)
        p = prev.get(others[i])
        if p:
            x, y = POS_KEEP * p[0] + (1 - POS_KEEP) * x, POS_KEEP * p[1] + (1 - POS_KEEP) * y
        pos[others[i]] = [round(x, 4), round(y, 4)]
    return pos


def _chg(rows, now, hours):
    past = [c for t, o, c in rows if t + 3600 <= now - hours * 3600]
    if not past or not rows:
        return None
    return round((rows[-1][2] / past[-1] - 1) * 100, 3)


def baselines(series):
    """코인별 평소 1시간 절대 변동 중앙값(%), 최근 30일."""
    out = {}
    for s, rows in series.items():
        v = sorted(abs(c / o - 1) * 100 for t, o, c in rows if o > 0)
        if len(v) >= 100:
            out[s] = round(v[len(v) // 2], 4)
    return out


def news(articles, now):
    """최근 7일 뉴스와 맵 코인별 측정 반응. 측정 전 뉴스는 pending으로 둔다."""
    assets = set(config.MARKET_ASSETS)
    out = []
    for a in articles:
        if now - a["t0"] > WINDOW_DAYS * 86400:
            continue
        hits = []
        for sym, win in (a.get("impact") or {}).items():
            if sym not in assets:
                continue
            h = {"s": sym}
            zmax = None
            for w in ("15m", "1h", "24h"):
                v = win.get(w) or {}
                if v.get("r") is not None:
                    h[w] = round(v["r"], 3)
                    if v.get("z") is not None and (zmax is None or abs(v["z"]) > abs(zmax)):
                        zmax = v["z"]
                        h["g"] = v.get("g")
            if zmax is not None:
                h["z"] = round(zmax, 2)
                hits.append(h)
        pending = not hits and now - a["t0"] < 26 * 3600
        if not hits and not pending:
            continue
        row = {"id": a["id"], "t": a["t0"], "c": a["category"], "e": a.get("etype") or "other", "src": a.get("source_name"),
               "title": a["title"][:140], "h": hits}
        if pending:
            row["p"] = 1
        pt = a.get("pattern")
        if pt:  # 유사 뉴스 과거 패턴(patterns.attach_similar가 먼저 붙인다)
            row["pt"] = {k: pt[k] for k in ("label", "sym", "n", "med", "up", "strong") if k in pt}
        out.append(row)
    out.sort(key=lambda x: x["t"])
    return out


def build(articles, snap, now, prev):
    tick = snap.get("tickers") or {}
    # 시세가 살아 있는 코인만 그린다(거래가 멈춘 심볼은 시세 띠에서도 빠진다)
    syms = [s for s in config.MARKET_ASSETS if s in tick] or list(config.MARKET_ASSETS)
    try:
        series = hourly(syms, now)
    except Exception as e:
        util.log("map candles failed", e)
        series = {}
    since = now - WINDOW_DAYS * 86400
    rets = {s: returns(r, since) for s, r in series.items()}
    cmat, links = {}, []
    for i, a in enumerate(syms):
        for b in syms[i + 1:]:
            c = corr(rets.get(a, {}), rets.get(b, {}))
            if c is not None:
                cmat[(a, b)] = cmat[(b, a)] = c
                if c >= LINK_MIN:
                    links.append({"a": a, "b": b, "c": round(c, 3)})
    prev_pos = {x["s"]: x["pos"] for x in (prev or {}).get("assets", []) if x.get("pos")}
    syms = [s for s in syms if s in series]
    pos = layout(syms, cmat, prev_pos) if "BTC" in syms else prev_pos
    base = baselines(series)
    assets = []
    for s in syms:
        t = tick.get(s) or {}
        rows = series.get(s) or []
        assets.append({"s": s, "price": t.get("price"), "qv": t.get("qv"), "pos": pos.get(s),
                       "chg": {"1h": _chg(rows, now, 1), "6h": _chg(rows, now, 6), "24h": t.get("chg") if t.get("chg") is not None else _chg(rows, now, 24),
                               "7d": _chg(rows, now, 168)},
                       "base1h": base.get(s),
                       # 다시 보기에서 노드 색을 그 시각 기준으로 칠하기 위한 7일 1시간 종가
                       "closes": [[t0, round(c, 8)] for t0, o, c in rows if t0 >= since]})
    if not series and prev:
        old_base = {x["s"]: x["base1h"] for x in prev.get("assets", []) if x.get("base1h")}
        return {**prev, "at": now, "stale": True, "news": news(articles, now)}, old_base
    return {"at": now, "window_days": WINDOW_DAYS, "link_min": LINK_MIN, "assets": assets, "links": links, "news": news(articles, now),
            "note": "같은 시간대의 가격 변화이며, 뉴스가 원인이라는 뜻은 아닙니다."}, base
