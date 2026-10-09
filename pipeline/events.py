"""이벤트 리스크 데이터.

발표 종류마다 과거 회차의 BTC 15분·1시간 변동을 모아, 다가오는 발표에 "과거 흔들림 폭"을 붙인다.
과거 시각은 pipeline/static/events_history.json(백필: FRED 발표 일정 + 연준 FOMC 일정)에서,
이후 회차는 매주 캘린더(Forex Factory) 발표의 측정 반응을 state에 쌓아 늘린다.
"""

import os
import statistics

from . import config, market, util

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(HERE, "static", "events_history.json")

# (종류, 한국어 이름, 캘린더 제목들(소문자, 정확히 일치), 중요도)
KINDS = [
    ("cpi", "소비자물가(CPI)", ["cpi m/m", "cpi y/y", "core cpi m/m", "core cpi y/y"], 3),
    ("ppi", "생산자물가(PPI)", ["ppi m/m", "core ppi m/m", "ppi y/y"], 2),
    ("nfp", "고용보고서(비농업 고용·실업률)", ["non-farm employment change", "unemployment rate", "average hourly earnings m/m"], 3),
    ("pce", "PCE 물가", ["core pce price index m/m", "pce price index m/m", "core pce price index y/y"], 3),
    ("gdp", "GDP", ["advance gdp q/q", "prelim gdp q/q", "final gdp q/q", "gdp q/q"], 2),
    ("retail", "소매판매", ["retail sales m/m", "core retail sales m/m"], 2),
    ("claims", "신규 실업수당 청구", ["unemployment claims"], 2),
    ("fomc", "FOMC 금리 결정", ["federal funds rate", "fomc statement"], 3),
    ("fomc_press", "FOMC 기자회견", ["fomc press conference"], 3),
    ("minutes", "FOMC 의사록", ["fomc meeting minutes"], 3),
    ("ism_m", "ISM 제조업 PMI", ["ism manufacturing pmi"], 2),
    ("ism_s", "ISM 서비스업 PMI", ["ism services pmi"], 2),
]
NAME = {k: n for k, n, _, _ in KINDS}
LEVEL = {k: lv for k, _, _, lv in KINDS}
_BY_TITLE = {t: k for k, _, titles, _ in KINDS for t in titles}
MIN_SAMPLES = 8
SAME_EVENT_SEC = 1800


def kind_of(title):
    return _BY_TITLE.get((title or "").strip().lower())


def load_history():
    return util.read_json(HISTORY, {"kinds": {}, "moves": {}})


def accumulate(state, calendar_events):
    """지난 캘린더 발표의 측정 반응을 state['events_hist'] = {kind: {ts: {15m, 1h}}}에 쌓는다."""
    hist = state.setdefault("events_hist", {})
    for e in calendar_events:
        k = kind_of(e.get("title"))
        r = e.get("reaction") or {}
        if not k or "1h" not in r:
            continue
        hist.setdefault(k, {})[str(e["ts"])] = {"15m": r.get("15m"), "1h": r["1h"]}
    return hist


def _merged(kind, hist_static, acc):
    """같은 발표 회차(30분 이내)는 하나로. 정적 백필 값을 먼저 쓴다."""
    rows = []
    for t in hist_static["kinds"].get(kind, []):
        mv = hist_static["moves"].get(str(t))
        if mv and mv.get("1h") is not None:
            rows.append((t, mv))
    for ts, mv in (acc.get(kind) or {}).items():
        t = int(ts)
        if mv.get("1h") is not None and not any(abs(t - x) < SAME_EVENT_SEC for x, _ in rows):
            rows.append((t, mv))
    rows.sort()
    return rows


def _q(values, q):
    v = sorted(values)
    if not v:
        return None
    i = (len(v) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def stats_for(rows):
    if not rows:
        return {"n": 0}
    a1 = [abs(m["1h"]) for _, m in rows]
    a15 = [abs(m["15m"]) for _, m in rows if m.get("15m") is not None]
    up = sum(1 for _, m in rows if m["1h"] > 0)
    big = max(rows, key=lambda x: abs(x[1]["1h"]))
    return {
        "n": len(rows),
        "abs1h": {"med": round(statistics.median(a1), 3), "p90": round(_q(a1, 0.9), 3), "max": round(max(a1), 3)},
        "abs15": {"med": round(statistics.median(a15), 3), "p90": round(_q(a15, 0.9), 3), "max": round(max(a15), 3)} if a15 else None,
        "up": round(up / len(rows), 3),
        "biggest": {"ts": big[0], "r1h": big[1]["1h"]},
        "recent": [{"ts": t, "r1h": m["1h"]} for t, m in rows[-12:]],
    }


def hourly_baseline(now, event_times):
    """최근 30일, 발표가 없던 시간대의 BTC 1시간 봉 절대 변동 중앙값을 UTC 시각(0~23)별로."""
    rows = market.candles("BTC", 3600, now - 30 * 86400, now - 3600)
    busy = {t - t % 3600 for t in event_times}
    by = {}
    for t, o, c in rows:
        if o <= 0 or t in busy:
            continue
        by.setdefault(util.datetime_utc_hour(t), []).append(abs(c / o - 1) * 100)
    return {h: round(statistics.median(v), 4) for h, v in by.items() if len(v) >= 10}


def build(state, calendar_events, now):
    hist_static = load_history()
    acc = accumulate(state, calendar_events)
    stats = {k: stats_for(_merged(k, hist_static, acc)) for k in NAME}

    # 다가오는 발표: 이번 주 캘린더 + 백필에 있는 올해 남은 예정 시각
    upcoming = []
    for e in calendar_events:
        if e["ts"] < now - 2 * 3600 or e.get("level", 0) < 2:
            continue
        k = kind_of(e["title"])
        upcoming.append({"ts": e["ts"], "kind": k, "title": e["title"], "title_ko": e.get("title_ko") or e["title"],
                         "level": e["level"], "forecast": e.get("forecast") or "", "previous": e.get("previous") or "",
                         "reaction": e.get("reaction") or None, "src": "calendar"})
    for k, times in hist_static["kinds"].items():
        for t in times:
            if now - 2 * 3600 <= t <= now + 14 * 86400 and not any(u["kind"] == k and abs(u["ts"] - t) < SAME_EVENT_SEC for u in upcoming):
                upcoming.append({"ts": t, "kind": k, "title": NAME[k], "title_ko": NAME[k], "level": LEVEL[k], "forecast": "", "previous": "",
                                 "reaction": None, "src": "schedule"})
    # 같은 시각의 같은 종류(예: CPI m/m·y/y·근원)는 한 카드로 묶는다
    merged = {}
    for u in sorted(upcoming, key=lambda x: (x["ts"], -x["level"])):
        key = (u["kind"] or u["title"], u["ts"] // SAME_EVENT_SEC)
        if key in merged:
            m = merged[key]
            if u["src"] == "calendar" and u["title"] not in m["items"]:
                m["items"].append(u["title"])
                m["detail"].append({"title_ko": u["title_ko"], "forecast": u["forecast"], "previous": u["previous"]})
            continue
        u["items"] = [u["title"]] if u["src"] == "calendar" else []
        u["detail"] = [{"title_ko": u["title_ko"], "forecast": u["forecast"], "previous": u["previous"]}] if u["src"] == "calendar" else []
        u["name"] = NAME.get(u["kind"]) or u["title_ko"]
        merged[key] = u
    upcoming = sorted(merged.values(), key=lambda x: x["ts"])

    try:
        all_times = [t for ts in hist_static["kinds"].values() for t in ts] + [e["ts"] for e in calendar_events]
        base = hourly_baseline(now, all_times)
        state["events_baseline"] = {"at": now, "by_hour": base}
    except Exception as e:  # 시세가 막히면 지난 값을 쓴다
        util.log("event baseline failed", e)
        base = (state.get("events_baseline") or {}).get("by_hour") or {}
    for u in upcoming:
        st = stats.get(u["kind"]) if u["kind"] else None
        u["stats"] = st if st and st["n"] >= MIN_SAMPLES else ({"n": st["n"]} if st else None)
        b = base.get(util.datetime_utc_hour(u["ts"])) or base.get(str(util.datetime_utc_hour(u["ts"])))
        if st and st["n"] >= MIN_SAMPLES and b:
            u["vs_normal"] = round(st["abs1h"]["med"] / b, 2)
    return {"at": now, "min_samples": MIN_SAMPLES, "kinds": [{"kind": k, "name": NAME[k], "level": LEVEL[k], **stats[k]} for k in NAME],
            "upcoming": upcoming, "baseline_by_hour": base,
            "note": "과거 같은 발표 직후 BTC가 움직인 폭이며, 발표가 원인이라는 뜻은 아닙니다."}
