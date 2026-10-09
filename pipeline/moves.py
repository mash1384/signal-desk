"""뉴스 영향(/map/) 데이터: 움직임에서 출발해 시장 몫을 빼고, 남은 자기 몫에 뉴스를 붙인다.

1. 시장 물결: 코인마다 '자기를 뺀 나머지 코인 시총 가중 지수'의 1분 로그 수익률.
2. 베타·평소 흔들림: 최근 30일 1시간 수익률로 코인 = α + β × 지수, 잔차 표준편차 = 평소 60분 흔들림.
3. 시장 몫 = β × 지수, 자기 몫 = 실제 − 시장 몫(24시간 누적).
4. 큰 움직임: 60분 자기 몫 변화가 평소 흔들림의 2.5배 이상인 구간을 겹치지 않게 큰 것부터.
5. 원인 후보: 시작 30분 전~5분 뒤 뉴스 중 그 코인을 제목에서 언급한 것. 1건 '유력', 여러 건 '복합'.
   시장 물결 자체의 큰 움직임(2배 이상)에는 거시·시장 전반 뉴스를 붙인다.
로그 수익률이라 시장 몫 + 움직임별 자기 몫 + 나머지 = 실제 등락이 정확히 맞는다.
"""
import math
import re
from concurrent.futures import ThreadPoolExecutor

from . import market, util

COINS = [
    ("BTC", "bitcoin", ["BTC", "비트코인", "bitcoin"]), ("ETH", "ethereum", ["ETH", "이더리움", "ethereum", "ether"]),
    ("SOL", "solana", ["SOL", "솔라나", "solana"]), ("XRP", "ripple", ["XRP", "리플", "ripple"]),
    ("BNB", "binancecoin", ["BNB", "바이낸스코인"]), ("DOGE", "dogecoin", ["DOGE", "도지코인", "dogecoin"]),
    ("ADA", "cardano", ["ADA", "카르다노", "에이다", "cardano"]), ("LINK", "chainlink", ["LINK", "체인링크", "chainlink"]),
    ("AVAX", "avalanche-2", ["AVAX", "아발란체", "avalanche"]), ("SUI", "sui", ["SUI", "수이"]),
    ("DOT", "polkadot", ["DOT", "폴카닷", "polkadot"]), ("LTC", "litecoin", ["LTC", "라이트코인", "litecoin"]),
    ("TRX", "tron", ["TRX", "트론", "tron"]), ("HBAR", "hedera-hashgraph", ["HBAR", "헤데라", "hedera"]),
    ("TAO", "bittensor", ["TAO", "비트텐서", "bittensor"]), ("AAVE", "aave", ["AAVE", "에이브"]),
    ("UNI", "uniswap", ["UNI", "유니스왑", "uniswap"]), ("NEAR", "near", ["NEAR", "니어프로토콜", "near protocol"]),
    ("APT", "aptos", ["APT", "앱토스", "aptos"]), ("ONDO", "ondo-finance", ["ONDO", "온도파이낸스", "ondo finance"]),
    ("ENA", "ethena", ["ENA", "에테나", "ethena"]), ("PEPE", "pepe", ["PEPE", "페페"]),
    ("ZEC", "zcash", ["ZEC", "지캐시", "zcash"]), ("FET", "fetch-ai", ["FET", "fetch.ai"]),
]
MARKET_WORDS = ["crypto market", "crypto majors", "가상자산 시장", "코인 시장", "암호화폐 시장", "fomc", "연준", "파월", "powell", "cpi", "inflation", "물가",
                "금리", "treasury", "국채", "tariff", "관세", "nasdaq", "나스닥", "뉴욕증시", "s&p 500", "달러 지수", "dollar index", "순유입", "순유출", "liquidat", "청산"]
WINDOW_MIN = 24 * 60
PRE_MIN = 70           # 창 시작 경계에서 움직임을 놓치지 않게 앞쪽을 더 본다
Z_COIN, Z_TIDE = 2.5, 2.0
SERIES_STEP = 5        # 화면용 시리즈 간격(분)


def _mentions(title, words):
    low = title.lower()
    for w in words:
        if re.fullmatch(r"[A-Z0-9]+", w):
            if re.search(r"(?<![A-Za-z0-9])" + w + r"(?![A-Za-z0-9])", title):
                return True
        elif w.lower() in low:
            return True
    return False


def _ols(y, x):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    vx = sum((a - mx) ** 2 for a in x)
    beta = sum((a - mx) * (b - my) for a, b in zip(x, y)) / vx if vx else 1.0
    alpha = my - beta * mx
    resid = [b - alpha - beta * a for a, b in zip(x, y)]
    sd = math.sqrt(sum(r * r for r in resid) / max(1, n - 2))
    var_y = sum((b - my) ** 2 for b in y) / n
    r2 = 1 - (sd * sd * (n - 2) / n) / var_y if var_y else 0
    return beta, sd, r2


def _detect(cum, sigma60, z_min):
    """cum: 누적 자기 몫(%) 1분 간격. 60분 변화가 평소의 z_min배 넘는 구간을 겹치지 않게 큰 것부터."""
    n = len(cum)
    if not sigma60:
        return []
    z = [0.0] * n
    for k in range(60, n):
        z[k] = (cum[k] - cum[k - 60]) / sigma60
    used = [False] * n
    out = []
    for k in sorted(range(n), key=lambda i: -abs(z[i])):
        if abs(z[k]) < z_min:
            break
        a = k - 60
        if a < 0 or any(used[a:k + 1]):
            continue
        tot = cum[k] - cum[a]
        onset = next(i for i in range(a, k + 1) if abs(cum[i] - cum[a]) >= 0.2 * abs(tot))
        tail = range(k, min(n, k + 31))
        e = max(tail, key=lambda i: cum[i]) if tot > 0 else min(tail, key=lambda i: cum[i])
        for i in range(max(0, onset - 15), min(n, e + 15)):
            used[i] = True
        out.append((onset, e))
    return sorted(out)


def _caps(prev):
    try:
        rows = util.http_json("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=100&ids=" + ",".join(c[1] for c in COINS))
        got = {r["id"]: r.get("market_cap") or 0 for r in rows}
        caps = {c[0]: float(got.get(c[1]) or 0) for c in COINS}
        if sum(1 for v in caps.values() if v > 0) >= len(COINS) - 2:
            return caps
    except Exception as e:  # 막히면 지난 값
        util.log("coingecko caps failed", e)
    old = {c["s"]: c.get("cap") for c in (prev or {}).get("coins", [])}
    return {c[0]: float(old.get(c[0]) or 0) for c in COINS}


def build(articles, now, prev=None):
    end = (now // 60) * 60
    start1 = end - (WINDOW_MIN + PRE_MIN + 2) * 60
    syms = [c[0] for c in COINS]

    def fetch(sym):
        return sym, market.candles(sym, 60, start1, end), market.candles(sym, 3600, end - 31 * 86400, end)
    with ThreadPoolExecutor(max_workers=6) as ex:
        got = list(ex.map(fetch, syms))
    m1 = {s: {t: c for t, _, c in a} for s, a, _ in got if a}
    h1 = {s: {t: c for t, _, c in b} for s, _, b in got if b}
    syms = [s for s in syms if s in m1 and s in h1]
    caps = _caps(prev)
    syms = [s for s in syms if caps.get(s, 0) > 0]
    if len(syms) < 8:
        raise RuntimeError("too few coins %d" % len(syms))
    words = {c[0]: c[2] for c in COINS}

    t1 = sorted(set.intersection(*[set(m1[s]) for s in syms]))
    th = sorted(set.intersection(*[set(h1[s]) for s in syms]))[-721:]
    t1 = [t for t in t1 if t < end][-(WINDOW_MIN + PRE_MIN + 1):]
    if len(t1) < WINDOW_MIN + PRE_MIN:
        raise RuntimeError("short minute series %d" % len(t1))
    r1 = {s: [math.log(m1[s][t1[i]] / m1[s][t1[i - 1]]) for i in range(1, len(t1))] for s in syms}
    rh = {s: [math.log(h1[s][th[i]] / h1[s][th[i - 1]]) for i in range(1, len(th))] for s in syms}
    total_cap = sum(caps[s] for s in syms)
    w = {s: caps[s] / total_cap for s in syms}

    def loo(R, s):
        ws = {k: v / (1 - w[s]) for k, v in w.items() if k != s}
        n = len(R[s])
        return [sum(R[k][i] * ws[k] for k in ws) for i in range(n)]

    k0 = len(t1) - 1 - WINDOW_MIN          # r1 인덱스로 24시간 창 시작
    T0 = t1[k0] + 60                       # 창 시작 시각(첫 1분봉 종가 직후)
    news = [a for a in articles if a.get("t0") and a["t0"] >= T0 - 2 * 3600]

    def attach(ev, sym):
        st = T0 + ev["a"] * 60
        win = [a for a in news if st - 1800 <= a["t0"] <= st + 300]
        if sym:
            hit = [a for a in win if _mentions(a["title"], words[sym])]
        else:
            hit = [a for a in win if a.get("category") == "macro" or a.get("etype") in ("fomc", "cpi", "jobs") or _mentions(a["title"], MARKET_WORDS)]
        hit.sort(key=lambda a: abs(st - a["t0"]))
        ev["label"] = "likely" if len(hit) == 1 else "mixed" if hit else "none"
        ev["news"] = [{"id": a["id"], "title": a["title"], "src": a.get("source_name"), "lead": round((st - a["t0"]) / 60)} for a in hit[:4]]
        ev["nearby"] = len(win)
        ev["t0"], ev["t1"] = st, T0 + ev["e"] * 60

    coins = []
    for s in syms:
        mh = loo(rh, s)
        beta, sd_h, r2 = _ols(rh[s], mh)
        sig60 = sd_h * 100
        mk1 = loo(r1, s)
        cum_t, cum_m, cum_o_pre = [0.0], [0.0], [0.0]
        for i in range(k0 - PRE_MIN, len(r1[s])):
            own = (r1[s][i] - beta * mk1[i]) * 100
            cum_o_pre.append(cum_o_pre[-1] + own)
            if i >= k0:
                cum_t.append(cum_t[-1] + r1[s][i] * 100)
                cum_m.append(cum_m[-1] + beta * mk1[i] * 100)
        evs = []
        for a, e in _detect(cum_o_pre, sig60, Z_COIN):
            a, e = a - PRE_MIN, e - PRE_MIN
            if a < 0:
                continue
            own = (cum_t[e] - cum_m[e]) - (cum_t[a] - cum_m[a])
            ev = {"a": a, "e": e, "size": round(own, 3), "z": round(own / sig60, 2), "market": round(cum_m[e] - cum_m[a], 3)}
            attach(ev, s)
            evs.append(ev)
        coins.append({"s": s, "cap": caps[s], "beta": round(beta, 3), "r2": round(r2, 3), "sig60": round(sig60, 3), "price": m1[s][t1[-1]],
                      "total": round(cum_t[-1], 3), "market": round(cum_m[-1], 3), "own": round(cum_t[-1] - cum_m[-1], 3),
                      "t": [round(cum_t[i], 3) for i in range(0, len(cum_t), SERIES_STEP)] + ([round(cum_t[-1], 3)] if (len(cum_t) - 1) % SERIES_STEP else []),
                      "m": [round(cum_m[i], 3) for i in range(0, len(cum_m), SERIES_STEP)] + ([round(cum_m[-1], 3)] if (len(cum_m) - 1) % SERIES_STEP else []),
                      "events": evs})

    # 시장 물결: 전체 시총 가중 지수
    idx1 = [sum(r1[s][i] * w[s] for s in syms) * 100 for i in range(len(r1[syms[0]]))]
    idxh = [sum(rh[s][i] * w[s] for s in syms) for i in range(len(rh[syms[0]]))]
    mh_ = sum(idxh) / len(idxh)
    sig_idx = math.sqrt(sum((x - mh_) ** 2 for x in idxh) / (len(idxh) - 1)) * 100
    pre, cum_idx = [0.0], [0.0]
    for i in range(k0 - PRE_MIN, len(idx1)):
        pre.append(pre[-1] + idx1[i])
        if i >= k0:
            cum_idx.append(cum_idx[-1] + idx1[i])
    tide_ev = []
    for a, e in _detect(pre, sig_idx, Z_TIDE):
        a, e = a - PRE_MIN, e - PRE_MIN
        if a < 0:
            continue
        ev = {"a": a, "e": e, "size": round(cum_idx[e] - cum_idx[a], 3), "z": round((cum_idx[e] - cum_idx[a]) / sig_idx, 2)}
        attach(ev, None)
        tide_ev.append(ev)
    betas = sorted(c["beta"] for c in coins if c["s"] != "BTC")
    return {"at": now, "t0": T0, "minutes": WINDOW_MIN, "step": SERIES_STEP, "coins": coins,
            "tide": {"t": [round(cum_idx[i], 3) for i in range(0, len(cum_idx), SERIES_STEP)], "total": round(cum_idx[-1], 3), "events": tide_ev,
                     "sig60": round(sig_idx, 3), "medianAltBeta": round(betas[len(betas) // 2], 2) if betas else None},
            "params": {"zCoin": Z_COIN, "zTide": Z_TIDE, "lookback": "30일 1시간", "newsWindow": [-30, 5]}}
