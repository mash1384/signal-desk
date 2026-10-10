"""시그널 보드(/map/) 데이터: 코인 24개마다 '지금 평소와 다른 것'을 네 가지로 잰다.

1. 시장 대비 움직임: 뉴스 영향(moves)의 자기 몫(실제 − β × 나머지 시장) 변화, 평소 흔들림 대비 z.
2. 업비트 거래대금: 최근 구간 원화 거래대금 ÷ 지난 7일 같은 길이 구간의 중앙값.
3. 김프 변화: 업비트 원화가 ÷ (바이낸스 USDT가 × 원/달러) − 1 의 구간 변화(%p).
4. 뉴스 양: 그 코인을 언급한 뉴스 수 ÷ 지난 며칠 같은 길이 구간 평균.
여기에 최근 72시간 업비트 거래 공지(상장·유의·상폐)를 더한다. 구간은 1시간·4시간·24시간.
"""
import math
import statistics
from concurrent.futures import ThreadPoolExecutor

from . import config, impact, util
from .moves import COINS, _mentions

WINDOWS = {"1h": 1, "4h": 4, "24h": 24}
# 움직임은 통계적으로 드물거나(z) 눈에 띄게 크면(절대값) 신호로 본다. 알트는 평소 흔들림이 커서 z만으로는 9% 이탈도 놓친다
THRESH = {"z": 2.0, "own": {"1h": 2.0, "4h": 3.5, "24h": 6.0}, "vol": 2.0, "kimp": {"1h": 0.8, "4h": 1.0, "24h": 1.5}, "news": 2.0, "news_min": 3}
NAME_KO = {"BTC": "비트코인", "ETH": "이더리움", "SOL": "솔라나", "XRP": "리플", "BNB": "BNB", "DOGE": "도지코인", "ADA": "카르다노", "LINK": "체인링크",
           "AVAX": "아발란체", "SUI": "수이", "DOT": "폴카닷", "LTC": "라이트코인", "TRX": "트론", "HBAR": "헤데라", "TAO": "비트텐서", "AAVE": "에이브",
           "UNI": "유니스왑", "NEAR": "니어", "APT": "앱토스", "ONDO": "온도", "ENA": "에테나", "PEPE": "페페", "ZEC": "지캐시", "FET": "페치"}


def _upbit_hours(market_code):
    """업비트 원화 1시간봉 [(시작 ts, 종가, 거래대금)] 오래된 것부터, 최근 200개."""
    rows = util.http_json(config.UPBIT_CANDLES_BASE + "minutes/60?market=%s&count=200" % market_code, retries=1)
    out = []
    for r in rows:
        t = util.parse_time(r["candle_date_time_utc"] + "Z")
        if t is not None:
            out.append((t, float(r["trade_price"]), float(r["candle_acc_trade_price"])))
    return sorted(out)


def vol_ratio(hours, now, w):
    """마지막으로 끝난 w시간 거래대금 ÷ 지난 7일 같은 길이 구간 중앙값. 진행 중인 시간봉은 뺀다."""
    done = [h for h in hours if h[0] + 3600 <= now]
    if len(done) < w + 24:
        return None, None
    vals = [v for _, _, v in done]
    cur = sum(vals[-w:])
    past = vals[:-w][-168:]
    sums = [sum(past[i:i + w]) for i in range(0, len(past) - w + 1, max(1, w // 2))]
    base = statistics.median(sums) if sums else 0
    return (round(cur / base, 2) if base > 0 else None), round(cur)


def _binance_price_at(c, doc, t):
    """moves 시리즈(5분, 24시간 누적 로그 수익률 %)로 시각 t의 바이낸스 가격을 되짚는다."""
    k = int(round((t - doc["t0"]) / (doc["step"] * 60)))
    n = len(c["t"]) - 1
    if 0 <= k - n <= 12:          # 시리즈 끝을 조금 넘으면(업비트 봉이 더 최신) 마지막 값으로
        k = n
    if -12 <= k < 0:              # 24시간 창 시작보다 조금 이르면 첫 값으로
        k = 0
    if k < 0 or k > n:
        return None
    return c["price"] / math.exp((c["t"][-1] - c["t"][k]) / 100)


def _own_change(c, doc, w):
    n = len(c["t"]) - 1
    k = max(0, n - int(w * 60 / doc["step"]))
    own_now, own_then = c["t"][n] - c["m"][n], c["t"][k] - c["m"][k]
    act = c["t"][n] - c["t"][k]
    mkt = c["m"][n] - c["m"][k]
    sd = c["sig60"] * math.sqrt(w)
    return round(own_now - own_then, 3), (round((own_now - own_then) / sd, 2) if sd else None), round(act, 3), round(mkt, 3)


def build(moves_doc, articles, listings_doc, fx, now):
    if not moves_doc or not moves_doc.get("coins"):
        raise RuntimeError("no moves")
    coins = {c["s"]: c for c in moves_doc["coins"]}
    words = {c[0]: c[2] for c in COINS}
    up_codes = {s: (config.ASSETS.get(s) or {}).get("upbit") for s in coins}

    def get(s):
        code = up_codes.get(s)
        if not code:
            return s, None
        try:
            return s, _upbit_hours(code)
        except Exception as e:
            util.log("upbit hours failed", s, e)
            return s, None
    with ThreadPoolExecutor(max_workers=4) as ex:
        hours = dict(ex.map(get, list(coins)))
    rate = (fx or {}).get("rate")

    recent = [a for a in articles if a.get("t0") and now - a["t0"] <= 8 * 86400]
    oldest = min([a["t0"] for a in articles if a.get("t0")] or [now])
    notices = [n for n in (listings_doc or {}).get("notices", []) if now - n.get("ts", 0) <= 72 * 3600 and n.get("kind") in ("listing", "caution", "delisting")]

    out = []
    for s, c in coins.items():
        mention = [a for a in recent if _mentions(a["title"] + " " + (a.get("title_orig") or ""), words[s])]
        mention.sort(key=lambda a: -a["t0"])
        hrs = hours.get(s)
        row = {"s": s, "name": NAME_KO.get(s, s), "price": c["price"], "cap": c["cap"], "beta": c["beta"], "upbit": bool(hrs), "w": {}}
        for wk, w in WINDOWS.items():
            own, z, act, mkt = _own_change(c, moves_doc, w)
            cell = {"own": own, "z": z, "act": act, "mkt": mkt, "sd": round(c["sig60"] * math.sqrt(w), 2)}
            if hrs:
                cell["volr"], cell["krw"] = vol_ratio(hrs, now, w)
                done = [h for h in hrs if h[0] + 3600 <= now]
                if rate and len(done) > w:
                    t1, p1 = done[-1][0] + 3600, done[-1][1]
                    t0_, p0 = done[-1 - w][0] + 3600, done[-1 - w][1]
                    b1, b0 = _binance_price_at(c, moves_doc, t1), _binance_price_at(c, moves_doc, t0_)
                    if b1 and b0:
                        k1, k0 = (p1 / (b1 * rate) - 1) * 100, (p0 / (b0 * rate) - 1) * 100
                        cell["kimp"], cell["dkimp"] = round(k1, 2), round(k1 - k0, 2)
            # 뉴스 양: 이 구간 전체 기사 중 이 코인 기사 비중 ÷ 그 전(최대 7일) 비중. 수집 매체가 늘어도 흔들리지 않게 비중으로 본다
            n_now = sum(1 for a in mention if now - a["t0"] <= w * 3600)
            all_now = sum(1 for a in recent if now - a["t0"] <= w * 3600) or 1
            span = min(7 * 86400, now - w * 3600 - oldest)
            n_prev = sum(1 for a in mention if w * 3600 < now - a["t0"] <= w * 3600 + span)
            all_prev = sum(1 for a in recent if w * 3600 < now - a["t0"] <= w * 3600 + span)
            share_prev = n_prev / all_prev if all_prev and span >= w * 3600 else None
            cell["news"] = n_now
            cell["newsb"] = round(share_prev * all_now, 2) if share_prev is not None else None     # 평소 비중이면 이번 구간 몇 건이었을지
            cell["newsr"] = round(n_now / cell["newsb"], 2) if cell["newsb"] else None
            flags = []
            if (z is not None and abs(z) >= THRESH["z"]) or abs(own) >= THRESH["own"][wk]:
                flags.append("move")
            if (cell.get("volr") or 0) >= THRESH["vol"]:
                flags.append("vol")
            if cell.get("dkimp") is not None and abs(cell["dkimp"]) >= THRESH["kimp"][wk]:
                flags.append("kimp")
            if n_now >= THRESH["news_min"] and (cell["newsr"] or 0) >= THRESH["news"]:
                flags.append("news")
            cell["flags"] = flags
            # '왜?' 칸: 이 구간(없으면 직전 24시간)의 사건 뉴스 중 가장 중요한 것. 가격 정리 기사는 뺀다
            pool = [a for a in mention if now - a["t0"] <= max(w, 24) * 3600 and not impact._recap(a.get("title_orig") or a["title"])]
            inwin = [a for a in pool if now - a["t0"] <= w * 3600]
            pick = sorted(inwin or pool, key=lambda a: (-a.get("importance", 1), -a["t0"]))[:1]
            cell["why"] = [{"id": a["id"], "title": a["title"], "src": a.get("source_name"), "t": a["t0"], "in": bool(inwin)} for a in pick]
            row["w"][wk] = cell
        row["notices"] = [{"title": n["title"], "kind": n["kind"], "ts": n["ts"]} for n in notices if s in (n.get("symbols") or [])]
        row["series"] = {"t": c["t"], "m": c["m"]}
        row["news"] = [{"id": a["id"], "title": a["title"], "src": a.get("source_name"), "t": a["t0"], "imp": a.get("importance", 1),
                        "recap": impact._recap(a.get("title_orig") or a["title"])} for a in mention if now - a["t0"] <= 86400][:40]
        out.append(row)
    return {"at": now, "t0": moves_doc["t0"], "minutes": moves_doc["minutes"], "step": moves_doc["step"], "fx": rate,
            "tide": {"total": moves_doc["tide"]["total"], "t": moves_doc["tide"]["t"]}, "thresh": THRESH, "coins": out}
