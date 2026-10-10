"""패턴 데이터: 뉴스 무게 검색기, 내러티브 열지도, 기사별 '유사 뉴스 과거 패턴'.

모두 최근 30일 측정이 끝난 관련 기사(그 코인을 언급했거나 시장 전체 발표)로 계산한다. 코인 기사의 값은 시장 대비(시장 몫을 뺀) 변화다.
대표 코인은 기사의 대표 반응(headline) 코인, 없으면 측정된 첫 코인.
"""

import statistics

from . import config, impact

DAYS = 30
MIN_SIMILAR = 5
MIN_CELL = 3
ROWS = ["fomc", "cpi", "jobs", "etf", "listing", "hack", "regulation", "ai-model", "earnings", "other"]
COLS = ["BTC", "ETH", "SOL", "XRP", "ALT"]

# 검색어 동의어(한·영). 키를 넣으면 값들도 함께 찾는다
SYNONYMS = {
    "트럼프": ["trump"], "관세": ["tariff", "tariffs"], "해킹": ["hack", "hacked", "exploit", "탈취"], "etf": ["상장지수펀드"],
    "연준": ["fed", "fomc", "federal reserve", "파월", "powell"], "fomc": ["연준", "federal reserve"], "금리": ["rate", "rates"],
    "스테이블코인": ["stablecoin", "stablecoins"], "엔비디아": ["nvidia"], "규제": ["regulation", "regulator", "sec"],
    "업비트 상장": ["업비트", "디지털 자산 추가", "신규 거래지원"], "비트코인": ["bitcoin", "btc"], "이더리움": ["ethereum", "eth"],
    "오픈ai": ["openai"], "물가": ["cpi", "inflation", "인플레이션"],
}
SUGGEST = ["트럼프", "관세", "ETF", "해킹", "업비트 상장", "FOMC", "스테이블코인", "엔비디아"]


def _rep(a):
    imp = a.get("impact") or {}
    hd = a.get("headline") or {}
    sym = hd.get("asset") if hd.get("asset") in imp else next((s for s in imp if (imp[s].get("1h") or {}).get("r") is not None), None)
    if not sym:
        return None
    w = imp[sym]
    r1 = (w.get("1h") or {}).get("r")
    if r1 is None:
        return None
    return {"sym": sym, "r15": (w.get("15m") or {}).get("r"), "r1h": r1, "r24h": (w.get("24h") or {}).get("r"),
            "z": (w.get("1h") or {}).get("z"), "g": (w.get("1h") or {}).get("g"), "adj": bool((w.get("1h") or {}).get("adj"))}


def measured(articles, now):
    out = []
    for a in articles:
        if now - a["t0"] > DAYS * 86400:
            continue
        r = _rep(a)
        if r:
            out.append((a, r))
    return out


def _summary(rows):
    r1 = [r["r1h"] for _, r in rows]
    strong = sum(1 for _, r in rows if r.get("g") in ("강", "중"))
    big = max(rows, key=lambda x: abs(x[1]["r1h"]))
    return {"n": len(rows), "med": round(statistics.median(r1), 3), "abs_med": round(statistics.median([abs(x) for x in r1]), 3),
            "up": round(sum(1 for x in r1 if x > 0) / len(r1), 3), "strong": round(strong / len(rows), 3),
            "top": {"id": big[0]["id"], "title": big[0]["title"][:100], "sym": big[1]["sym"], "r1h": round(big[1]["r1h"], 3)}}


def attach_similar(articles, now):
    """기사마다 같은 유형·같은 대표 코인(유형이 기타면 같은 분야·코인)의 과거 반응 요약을 a['pattern']에 붙인다."""
    pool = measured(articles, now)
    groups = {}
    for a, r in pool:
        e = a.get("etype") or "other"
        key = ((e, r["sym"]) if e != "other" else ("cat:" + a["category"], r["sym"])) + (r["adj"],)
        groups.setdefault(key, []).append((a, r))
    for a in articles:
        subs = impact.subjects(a)
        if now - a["t0"] > 3 * 86400 or not subs:
            a.pop("pattern", None)   # 관련 없는 기사에는 '이런 뉴스는 보통'을 붙이지 않는다
            continue
        hd = a.get("headline") or {}
        sym = hd.get("asset") or subs[0][0]
        adj = dict(subs).get(sym, False)
        e = a.get("etype") or "other"
        key = ((e, sym) if e != "other" else ("cat:" + a["category"], sym)) + (adj,)
        rows = [x for x in groups.get(key, []) if x[0]["id"] != a["id"]]
        label = config_label(e) if e != "other" else {"crypto": "크립토", "ai": "AI", "macro": "매크로"}.get(a["category"], a["category"])
        if len(rows) >= MIN_SIMILAR:
            a["pattern"] = {"label": label, "sym": sym, "adj": adj, **_summary(rows)}
        else:
            a["pattern"] = {"label": label, "sym": sym, "adj": adj, "n": len(rows)}


def config_label(etype):
    for k, label, _ in config.EVENT_TYPES:
        if k == etype:
            return label
    return "기타"


def heatmap(articles, base, now, days, base_res=None):
    """기사마다 측정된 모든 코인의 1시간 절대 변동을 그 코인의 평소 1시간 변동으로 나눈 배수. 칸 = 중앙값."""
    out = {}
    for since, until, tag in ((now - days * 86400, now, "cur"), (now - 2 * days * 86400, now - days * 86400, "prev")):
        cells = {}
        for a in articles:
            if not (since <= a["t0"] < until):
                continue
            e = a.get("etype") or "other"
            if e not in ROWS:
                e = "other"
            for sym, w in (a.get("impact") or {}).items():
                r1 = (w.get("1h") or {}).get("r")
                # 시장 대비 값은 시장 몫을 뺀 평소 흔들림으로, 시장 전체 반응은 평소 1시간 변동으로 나눈다
                b = (base_res or {}).get(sym) if (w.get("1h") or {}).get("adj") else base.get(sym)
                if r1 is None or not b:
                    continue
                col = sym if sym in COLS else "ALT"
                cells.setdefault((e, col), []).append(abs(r1) / b)
        out[tag] = cells
    rows = []
    for e in ROWS:
        row = {"e": e, "label": config_label(e), "cells": []}
        for c in COLS:
            v = out["cur"].get((e, c), [])
            pv = out["prev"].get((e, c), [])
            if len(v) < MIN_CELL:
                row["cells"].append({"c": c, "n": len(v)})
                continue
            cell = {"c": c, "n": len(v), "x": round(statistics.median(v), 2)}
            if len(pv) >= MIN_CELL:
                cell["prev"] = round(statistics.median(pv), 2)
            row["cells"].append(cell)
        rows.append(row)
    return rows


def build(articles, base, imp, now, base_res=None):
    pool = measured(articles, now)
    items = [{"id": a["id"], "t": a["t0"], "title": a["title"][:110], "c": a["category"], "e": a.get("etype") or "other",
              "s": r["sym"], "r15": None if r["r15"] is None else round(r["r15"], 3), "r1h": round(r["r1h"], 3),
              "r24h": None if r["r24h"] is None else round(r["r24h"], 3), "g": r.get("g"), "adj": r["adj"]} for a, r in pool]
    items.sort(key=lambda x: -x["t"])
    return {"at": now, "days": DAYS, "min_n": MIN_SIMILAR, "synonyms": SYNONYMS, "suggest": SUGGEST,
            "items": items, "heat": {"7": heatmap(articles, base, now, 7, base_res), "30": heatmap(articles, base, now, 30, base_res)}, "cols": COLS,
            "heaviest": [s for s in (imp.get("strongest") or []) if now - s["t0"] <= 7 * 86400][:10],
            "note": "같은 시간대의 가격 변화이며, 뉴스가 원인이라는 뜻은 아닙니다."}
