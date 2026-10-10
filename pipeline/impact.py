"""뉴스 임팩트 실측.

관련 있는 기사만 잰다: 그 코인을 직접 언급한 기사는 그 코인을, 코인 언급 없이 시장 전체를 움직이는 발표(FOMC·CPI·고용,
크립토 분야의 ETF·규제·해킹·상장)는 BTC를 잰다. 그 밖의 기사(AI 제품·일반 경제 등)에는 가격 반응을 붙이지 않는다.
코인 기사의 값은 시장 몫을 뺀 '시장 대비' 변화다: 실제 − β × (그 코인을 뺀 시총 상위 5개 시총 가중 바스켓).
β와 평소 흔들림은 최근 30일 1시간 수익률 회귀로 구한다. 시장 전체 발표의 BTC 값은 그 자체가 시장 반응이라 빼지 않는다.
상관을 잴 뿐 인과를 주장하지 않는다.
"""

import math

from . import config, market, util
from .moves import _recap

STATS_TTL = 6 * 3600
IMPACT_VERSION = 2
MARKET = ["BTC", "ETH", "XRP", "BNB", "SOL"]
DEFAULT_CAP = {"BTC": 1670e9, "ETH": 306e9, "XRP": 88e9, "BNB": 99e9, "SOL": 65e9}
MARKET_EVENTS = {"fomc", "cpi", "jobs"}
MARKET_EVENTS_CRYPTO = {"etf", "regulation", "hack", "listing"}
# 코인 시장 전체를 움직이는 거시 발표는 미국 것만(다른 나라 중앙은행·물가 발언은 빼고)
US_MACRO = ["fed", "fomc", "powell", "federal reserve", "u.s.", "us ", "american", "nonfarm", "payroll", "jobless", "pce", "cpi",
            "연준", "파월", "미국", "미 ", "美", "고용보고서", "비농업"]
_hourly = {}
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


def subjects(article):
    """반응을 잴 대상 [(코인, 시장 몫을 빼는지)]. 관련 없는 기사면 []."""
    if article.get("source") == "calendar":
        return [("BTC", False)]
    coins = list(article.get("assets") or [])[: config.MAX_ASSETS_PER_ARTICLE]
    # 가격 움직임을 정리·전망하는 기사("비트코인 가격, 8만 달러 지킬까")는 사건이 아니라 반응을 재지 않는다
    if coins and article.get("source") != "upbit-notice" and _recap(article.get("title_orig") or article.get("title") or ""):
        coins = []
    if coins:
        return [(c, True) for c in coins]
    e = article.get("etype")
    title = " " + (article.get("title_orig") or article.get("title") or "").lower() + " "
    if e in MARKET_EVENTS and any(w in title for w in US_MACRO):
        return [("BTC", False)]
    if article.get("category") == "crypto" and e in MARKET_EVENTS_CRYPTO:
        return [("BTC", False)]
    return []


def assets_for(article):
    return [s for s, _ in subjects(article)]


def relevant(article):
    return bool(subjects(article))


def _hour_closes(sym, now):
    if sym not in _hourly:
        _hourly[sym] = {t: c for t, _, c in market.candles(sym, 3600, now - 31 * 86400, now)}
    return _hourly[sym]


def _weights(sym, caps):
    w = {k: float((caps or {}).get(k) or DEFAULT_CAP[k]) for k in MARKET if k != sym}
    tot = sum(w.values())
    return {k: v / tot for k, v in w.items()}


def model(sym, cache, now, caps):
    """그 코인의 β와 1시간 잔차 표준편차(시장 몫을 뺀 평소 흔들림). 6시간마다 다시 구한다."""
    entry = cache.get(sym) or {}
    m = entry.get("model")
    if m and now - m.get("at", 0) < STATS_TTL:
        return m
    try:
        own = _hour_closes(sym, now)
        bask = {k: _hour_closes(k, now) for k in MARKET if k != sym}
    except Exception as e:
        util.log("model candles failed", sym, e)
        return None
    w = _weights(sym, caps)
    ts = sorted(t for t in own if all(t in bask[k] for k in w))[-721:]
    x, y = [], []
    for i in range(1, len(ts)):
        a, b = ts[i - 1], ts[i]
        if b - a != 3600 or own[a] <= 0:
            continue
        y.append(own[b] / own[a] - 1)
        x.append(sum(w[k] * (bask[k][b] / bask[k][a] - 1) for k in w))
    if len(x) < 200:
        return None
    mx, my = sum(x) / len(x), sum(y) / len(y)
    vx = sum((v - mx) ** 2 for v in x)
    beta = sum((u - mx) * (v - my) for u, v in zip(x, y)) / vx if vx else 1.0
    res = [v - my - beta * (u - mx) for u, v in zip(x, y)]
    sd = math.sqrt(sum(r * r for r in res) / (len(res) - 2))
    m = {"at": now, "beta": round(beta, 4), "sd1h": sd}
    cache.setdefault(sym, {})["model"] = m
    return m


def _spans(intervals, gap=6 * 3600):
    """겹치거나 가까운 구간을 합친다(멀리 떨어진 기사 때문에 한 달치를 받지 않게)."""
    out = []
    for lo, hi in sorted(intervals):
        if out and lo <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


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


def measure(articles, vol_cache, now, caps=None):
    """측정할 수 있는 모든 기사·대상·구간을 채운다. 1분봉은 자산별로 가까운 구간끼리 묶어 한 번에 받는다."""
    todo = []
    for a in articles:
        if not relevant(a):          # 규칙이 바뀌어 관련 없어진 기사도 반응을 지운다
            if a.get("impact_status") != "skip":
                a["impact"], a["impact_status"], a["headline"] = {}, "skip", None
            continue
        if a.get("impact_status") in ("done", "failed"):
            continue
        p = _pending(a, now)
        if p:
            todo.append((a, p))
    if not todo:
        return 0
    adj_of = {}
    need = {}
    for a, pend in todo:
        adj = dict(subjects(a))
        for sym, _win, secs in pend:
            iv = (a["t0"] - 120, a["t0"] + secs + 180)
            need.setdefault(sym, []).append(iv)
            if adj.get(sym):
                for k in MARKET:
                    if k != sym:
                        need.setdefault(k, []).append(iv)
    minute = {}
    for sym, ivs in need.items():
        book = {}
        for lo, hi in _spans(ivs):
            try:
                for ts, o, c in market.candles(sym, 60, (lo // 60) * 60, min(now, hi)):
                    book[ts] = (o, c)
            except Exception as e:
                util.log("candles failed", sym, e)
        minute[sym] = book
        util.log("candles", sym, len(book))
    filled = 0
    for a, pend in todo:
        imp = a["impact"]
        adj = dict(subjects(a))
        missed = False
        for sym, win, secs in pend:
            book = minute.get(sym) or {}
            start = (a["t0"] // 60) * 60
            end = ((a["t0"] + secs) // 60) * 60 - 60
            if not (start in book and end in book and book[start][0] > 0):
                missed = True
                # 일시 장애로 영구 실패가 되지 않도록, 6시간이 지나고 8번 넘게 못 잰 경우에만 포기한다
                if now - (a["t0"] + secs) > 6 * 3600 and a.get("impact_tries", 0) >= 8:
                    imp.setdefault(sym, {})[win] = {"r": None, "z": None, "g": None}
                continue
            raw = book[end][1] / book[start][0] - 1
            mdl = model(sym, vol_cache, now, caps) if adj.get(sym) else None
            if mdl:
                w = _weights(sym, caps)
                if not all(start in minute.get(k, {}) and end in minute.get(k, {}) and minute[k][start][0] > 0 for k in w):
                    missed = True
                    continue
                mk = mdl["beta"] * sum(w[k] * (minute[k][end][1] / minute[k][start][0] - 1) for k in w)
                ex = raw - mk
                sd = mdl["sd1h"] * math.sqrt(secs / 3600)
                z = round(ex / sd, 2) if sd else None
                imp.setdefault(sym, {})[win] = {"r": round(ex * 100, 3), "raw": round(raw * 100, 3), "m": round(mk * 100, 3), "z": z,
                                                "g": grade(z) if z is not None else None, "adj": True}
            else:
                sd = volatility(sym, vol_cache, now).get(win)
                z = round(raw / sd, 2) if sd else None
                imp.setdefault(sym, {})[win] = {"r": round(raw * 100, 3), "raw": round(raw * 100, 3), "z": z, "g": grade(z) if z is not None else None, "adj": False}
            filled += 1
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
                return {"asset": sym, "win": win, "r": v["r"], "g": v["g"], "adj": bool(v.get("adj"))}
    return None


def concurrency(articles):
    """기준 시각 ±15분 안의 다른 주요 기사 수."""
    major = sorted((a["t0"], a["id"]) for a in articles if a.get("importance", 1) >= 2)
    for a in articles:
        a["concurrent"] = sum(1 for t, i in major if i != a["id"] and abs(t - a["t0"]) <= config.CONCURRENT_EVENT_SECONDS)
    # 같은 코인을 다룬 다른 기사가 ±30분 안에 몇 건인지(반응을 여러 기사가 나눠 갖는 정도)
    by = {}
    for x in articles:
        for sym in assets_for(x):
            by.setdefault(sym, []).append((x["t0"], x["id"]))
    for x in articles:
        subs = assets_for(x)
        x["crowd"] = max([sum(1 for t, i in by.get(s, []) if i != x["id"] and abs(t - x["t0"]) <= 1800) for s in subs] or [0])


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
                    best = (sym, win, v["z"], v["r"], v["g"], bool(v.get("adj")))
        if best:
            rows.append({"id": a["id"], "title": a["title"], "asset": best[0], "win": best[1], "z": best[2], "r": best[3], "g": best[4], "adj": best[5], "t0": a["t0"]})
    rows.sort(key=lambda r: -abs(r["z"]))
    return rows[:limit]
