#!/usr/bin/env python3
"""경제지표(일정 페이지) 자료: 다가오는 발표, 지표별 과거 발표 기록, '과거에 비슷했을 때' 가격 흐름, AI 해석.

- 과거 값: ALFRED(FRED 발표 이력). 발표일마다 '그날 처음 공개된 값'을 그대로 쓴다(나중에 고쳐진 값이 아니라 그때 사람들이 본 숫자).
- 가격: 야후 일봉(S&P 500 · 나스닥 · 미국 10년물 · 달러지수 · 금 · 비트코인). 발표 전날 종가 기준 1일 · 1주 · 1달 뒤 변화.
- 비슷한 과거: 같은 지표의 과거 발표 중 '직전 대비 변화 · 1년 평균 대비 수준 · 최근 3번 흐름'이 지금과 가까운 회차.
  숫자는 모두 프로그램이 계산하고, AI(Gemma)는 그 숫자로 문장만 쓴다. 문장의 숫자는 입력에 있는 것만 허용.
- 다가오는 일정 · 예상치: Forex Factory 주간 일정(이번 주). 예상치는 발표 전에 저장해 두었다가 실제 값과 비교한다.

결과: ~/.signal/flash-branch/daily/econ.json → tg_publish 가 flash 브랜치로 올린다(사이트는 raw.githubusercontent 로 읽는다).
실행: python econ_brief.py            (한 번)
      python econ_brief.py --no-ai    (AI 문장 없이)
설치: ~/.signal/tgvenv/bin/python tools/econ_brief.py --install   (launchd com.signal.econ, 1시간마다, 로그 ~/.signal/econ.log)
"""

import csv
import shutil
import subprocess
import io
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

HOME = os.path.expanduser("~/.signal")
BRANCH = os.path.join(HOME, "flash-branch")
OUT = os.path.join(BRANCH, "daily", "econ.json")
CACHE = os.path.join(HOME, "econ")
STATE = os.path.join(CACHE, "state.json")
OLLAMA = os.environ.get("SIGNAL_OLLAMA", "http://localhost:11434")
MODEL = os.environ.get("SIGNAL_TG_MODEL", "gemma4:26b")
ET = ZoneInfo("America/New_York")
# FRED·ALFRED 는 서비스 이름을 밝힌 요청에 응답한다(브라우저 흉내 요청은 막힘). 야후는 브라우저 형식만 받는다.
UA = {"User-Agent": "delfona-econ/1.0 (+https://mash1384.github.io/signal-desk/)"}
UA_YAHOO = {"User-Agent": "Mozilla/5.0 delfona-econ"}
SINCE = "1990-01-01"
EVERY = 3600

# 지표: 키, FRED 시리즈, 변환(yoy 전년 대비 % · mom 전월 대비 % · diff 전월 대비 증감 · level 값 그대로 · saar 연율 성장률),
# 보조 변환, 영어 · 한국어 이름, 단위, 묶음, 발표 시각(동부), Forex Factory 제목(예상치 매칭), 소수 자리, 높을수록(hot = 물가·경기 과열 방향)
IND = [
    dict(k="cpi", fred="CPIAUCSL", t="yoy", sub="mom", en="CPI inflation", ko="소비자물가 상승률", unit="%", grp="prices", at=(8, 30),
         ff={"CPI y/y": "main", "CPI m/m": "sub"}, dec=1, hot=1),
    dict(k="core_cpi", fred="CPILFESL", t="yoy", sub="mom", en="Core CPI inflation", ko="근원 소비자물가 상승률", unit="%", grp="prices", at=(8, 30),
         ff={"Core CPI y/y": "main", "Core CPI m/m": "sub"}, dec=1, hot=1),
    dict(k="core_pce", fred="PCEPILFE", t="yoy", sub="mom", en="Core PCE inflation", ko="근원 PCE 물가 상승률", unit="%", grp="prices", at=(8, 30),
         ff={"Core PCE Price Index y/y": "main", "Core PCE Price Index m/m": "sub"}, dec=1, hot=1),
    dict(k="ppi", fred="PPIFIS", t="yoy", sub="mom", en="Producer prices (PPI)", ko="생산자물가 상승률", unit="%", grp="prices", at=(8, 30),
         ff={"PPI y/y": "main", "PPI m/m": "sub", "Core PPI m/m": "extra"}, dec=1, hot=1),
    dict(k="nfp", fred="PAYEMS", t="diff", sub=None, en="Jobs added (payrolls)", ko="비농업 고용 증가", unit="k", grp="jobs", at=(8, 30),
         ff={"Non-Farm Employment Change": "main"}, dec=0, hot=1),
    dict(k="unemp", fred="UNRATE", t="level", sub=None, en="Unemployment rate", ko="실업률", unit="%", grp="jobs", at=(8, 30),
         ff={"Unemployment Rate": "main"}, dec=1, hot=-1),
    dict(k="wages", fred="CES0500000003", t="yoy", sub="mom", en="Average hourly earnings", ko="평균 시급 상승률", unit="%", grp="jobs", at=(8, 30),
         ff={"Average Hourly Earnings m/m": "sub"}, dec=1, hot=1),
    dict(k="claims", fred="ICSA", t="level", sub=None, en="Initial jobless claims", ko="신규 실업수당 청구", unit="k", grp="jobs", at=(8, 30),
         ff={"Unemployment Claims": "main"}, dec=0, hot=-1, weekly=True),
    dict(k="jolts", fred="JTSJOL", t="level", sub=None, en="Job openings (JOLTS)", ko="구인 건수", unit="M", grp="jobs", at=(10, 0),
         ff={"JOLTS Job Openings": "main"}, dec=2, hot=1),
    dict(k="retail", fred="RSAFS", t="mom", sub=None, en="Retail sales", ko="소매판매", unit="%", grp="growth", at=(8, 30),
         ff={"Retail Sales m/m": "main", "Core Retail Sales m/m": "extra"}, dec=1, hot=1),
    dict(k="gdp", fred="GDPC1", t="saar", sub=None, en="GDP growth", ko="GDP 성장률", unit="%", grp="growth", at=(8, 30),
         ff={"Advance GDP q/q": "main", "Prelim GDP q/q": "main", "Final GDP q/q": "main", "GDP q/q": "main"}, dec=1, hot=1, quarterly=True),
]
BY = {x["k"]: x for x in IND}
GROUPS = [("prices", "Inflation", "물가"), ("jobs", "Jobs", "고용"), ("growth", "Growth", "성장")]
# 가격: 야후 기호, 이름, 표시 방식(pct 수익률 · bp 금리 변화)
ASSETS = [("^GSPC", "S&P 500", "S&P 500", "pct"), ("^IXIC", "Nasdaq", "나스닥", "pct"), ("BTC-USD", "Bitcoin", "비트코인", "pct"),
          ("^TNX", "US 10Y yield", "미국 10년물 금리", "bp"), ("DX-Y.NYB", "Dollar index", "달러지수", "pct"), ("GC=F", "Gold", "금", "pct")]
# 1일 · 1주 · 1달(거래일 기준, 비트코인은 달력일)
HORIZONS = [("d1", 0, 0), ("w1", 4, 6), ("m1", 20, 29)]
K_SIMILAR = 12


def log(*a):
    print(time.strftime("%m-%d %H:%M:%S"), *a, flush=True)


def fetch(url, timeout=60, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA_YAHOO if "yahoo.com" in url else UA), timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            if i == tries - 1:
                raise
            log("retry", type(e).__name__, url[:90])
            time.sleep(3 * (i + 1))


def cached(name, fn, max_age=None):
    p = os.path.join(CACHE, name)
    if os.path.exists(p) and (max_age is None or time.time() - os.path.getmtime(p) < max_age):
        return open(p, encoding="utf-8").read()
    s = fn()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        f.write(s)
    os.replace(p + ".tmp", p)
    return s


# ---------- ALFRED: 발표일 목록과 그날 처음 공개된 값 ----------
def vintage_dates(sid):
    """발표 이력 페이지의 발표일(vintage) 목록. 하루 한 번만 새로 받는다."""
    def get():
        time.sleep(1.2)
        return fetch("https://alfred.stlouisfed.org/series/downloaddata?seid=" + sid)
    h = cached("vd-%s.html" % sid, get, max_age=20 * 3600)
    m = re.search(r'id="form_selected_vintage_dates".*?</select>', h, re.S)
    return sorted(d for d in re.findall(r'value="(\d{4}-\d\d-\d\d)"', m.group(0) if m else "") if d >= SINCE)


def back_days(ind):
    """발표일마다 함께 받을 과거 기간: 1년 평균(12회)과 전년 대비 계산에 필요한 만큼."""
    return 20 * 7 if ind.get("weekly") else (16 * 92 if ind.get("quarterly") else 27 * 31)


# ALFRED 는 한 요청에 발표일 12개까지만 값을 채워 준다
CH = 12


def vintages_values(ind, dates):
    """발표일마다 그날 공개된 최근 값들 {발표일: [(관측일, 값), ...]}. 12개씩 묶어 받고, 지난 묶음은 캐시."""
    sid, out = ind["fred"], {}
    for i in range(0, len(dates), CH):
        chunk = dates[i:i + CH]
        cosd = [(datetime.strptime(d, "%Y-%m-%d") - timedelta(days=back_days(ind))).strftime("%Y-%m-%d") for d in chunk]
        q = urllib.parse.urlencode({"id": ",".join([sid] * len(chunk)), "vintage_date": ",".join(chunk), "cosd": ",".join(cosd)})
        url = "https://alfred.stlouisfed.org/graph/alfredgraph.csv?" + q
        last = i + CH >= len(dates)

        def get(url=url):
            time.sleep(1.2)
            return fetch(url, timeout=90)
        text = cached("av-%s-%d-%s-%s.csv" % (sid, back_days(ind), chunk[0], chunk[-1]), get, max_age=6 * 3600 if last else None)
        rows = list(csv.reader(io.StringIO(text)))
        if not rows or not rows[0] or rows[0][0] != "observation_date":
            raise RuntimeError("ALFRED 응답 이상: %s %s" % (sid, text[:120]))
        heads = rows[0][1:]
        for j, hname in enumerate(heads):
            d = hname.rsplit("_", 1)[-1]
            vd = "%s-%s-%s" % (d[:4], d[4:6], d[6:8])
            series = [(r[0], float(r[j + 1])) for r in rows[1:] if len(r) > j + 1 and r[j + 1] not in ("", ".")]
            out[vd] = series
    return out


def transform(series, t):
    """관측값 목록 → (관측일, 지표값) 목록. 변환 방식에 맞춰 계산."""
    v = dict(series)
    keys = [d for d, _ in series]
    res = []
    for i, d in enumerate(keys):
        x = v[d]
        if t == "level":
            res.append((d, x))
        elif t == "diff" and i >= 1:
            res.append((d, x - v[keys[i - 1]]))
        elif t == "mom" and i >= 1 and v[keys[i - 1]]:
            res.append((d, (x / v[keys[i - 1]] - 1) * 100))
        elif t == "saar" and i >= 1 and v[keys[i - 1]]:
            res.append((d, ((x / v[keys[i - 1]]) ** 4 - 1) * 100))
        elif t == "yoy":
            y0 = (datetime.strptime(d, "%Y-%m-%d").replace(year=int(d[:4]) - 1)).strftime("%Y-%m-%d")
            if y0 in v and v[y0]:
                res.append((d, (x / v[y0] - 1) * 100))
    return res


def scale(ind, x):
    """화면 단위로: 고용·청구 건수는 천 명(k), 구인은 백만(M)."""
    if x is None:
        return None
    if ind["k"] == "claims":
        return x / 1000
    if ind["k"] == "jolts":
        return x / 1000
    return x


def releases(ind):
    """발표 기록: [{d 발표일, ts, period 관측월, v 지표값, sub 보조값, prev 직전 값(같은 날 공개된 고친 값), d3 3번 전 발표 대비, avg12 직전 12번 발표 평균}]"""
    dates = vintage_dates(ind["fred"])
    vals = vintages_values(ind, dates)
    out, seen = [], None
    for vd in dates:
        s = vals.get(vd) or []
        if not s:
            continue
        main = transform(s, ind["t"])
        if len(main) < 2:
            continue
        period = main[-1][0]
        # 새 관측이 나온 날만(고친 값만 바뀐 날은 건너뜀)
        if period == seen:
            continue
        seen = period
        sub = transform(s, ind["sub"]) if ind.get("sub") else []
        hh, mm = ind["at"]
        ts = int(datetime.strptime(vd, "%Y-%m-%d").replace(hour=hh, minute=mm, tzinfo=ET).timestamp())
        m = [scale(ind, x) for _, x in main]
        out.append({"d": vd, "ts": ts, "period": period, "v": m[-1], "prev": m[-2], "sub": scale(ind, sub[-1][1]) if sub and sub[-1][0] == period else None})
    # 1년 평균 · 최근 3번 흐름은 그동안 '처음 발표된 값'들로(ALFRED 는 발표일마다 최근 1년 반만 준다)
    for i, r in enumerate(out):
        r["avg12"] = statistics.mean(x["v"] for x in out[max(0, i - 12):i]) if i >= 6 else None
        r["d3"] = r["v"] - out[i - 3]["v"] if i >= 3 else None
    return out


# ---------- 가격 ----------
def prices():
    """야후 일봉 {기호: ([날짜], [종가])}. 3시간마다 새로."""
    out = {}
    p1 = int(datetime(1985, 1, 1, tzinfo=timezone.utc).timestamp())
    for sym, *_ in ASSETS:
        def get(sym=sym):
            return fetch("https://query1.finance.yahoo.com/v8/finance/chart/%s?period1=%d&period2=%d&interval=1d" % (urllib.parse.quote(sym), p1, int(time.time())))
        try:
            r = json.loads(cached("px-%s.json" % re.sub(r"\W", "_", sym), get, max_age=3 * 3600))["chart"]["result"][0]
        except Exception as e:
            log("가격 실패", sym, type(e).__name__, str(e)[:100])
            continue
        ts, cl = r.get("timestamp") or [], r["indicators"]["quote"][0].get("close") or []
        d, c = [], []
        for t, x in zip(ts, cl):
            if x is None:
                continue
            day = datetime.fromtimestamp(t, ET if sym != "BTC-USD" else timezone.utc).strftime("%Y-%m-%d")
            if d and d[-1] == day:
                c[-1] = x
                continue
            d.append(day)
            c.append(x)
        out[sym] = (d, c)
    return out


def reactions(px, day):
    """발표일 전날 종가 대비 1일 · 1주 · 1달 뒤 변화 {기호: {d1, w1, m1}}. 아직 그만큼 지나지 않았으면 빠진다."""
    import bisect
    res = {}
    for sym, name_en, name_ko, kind in ASSETS:
        if sym not in px:
            continue
        d, c = px[sym]
        i0 = bisect.bisect_left(d, day)
        if i0 == 0 or i0 >= len(d):
            continue
        base, r = c[i0 - 1], {}
        for h, n_tr, n_btc in HORIZONS:
            j = i0 + (n_btc if sym == "BTC-USD" else n_tr)
            if j < len(d):
                r[h] = round((c[j] - base) * 100, 1) if kind == "bp" else round((c[j] / base - 1) * 100, 2)
        if r:
            res[sym] = r
    return res


# ---------- 비슷한 과거 ----------
# 비교 기준: 직전 대비 변화 · 수준 · 1년 평균 대비 · 최근 3번 흐름(앞일수록 무겁게)
FEAT_W = [1.0, 0.8, 0.6, 0.6]


def features(r):
    if r["prev"] is None or r["avg12"] is None:
        return None
    return [r["v"] - r["prev"], r["v"], r["v"] - r["avg12"], r["d3"] if r["d3"] is not None else 0.0]


def similar(hist, i, k=K_SIMILAR):
    """hist[i] 와 가까운 과거 회차(그보다 앞선 것만). 특징마다 표준편차로 나눠 거리 계산."""
    f = [features(r) for r in hist]
    base = [x for x in f[:i] if x]
    if len(base) < 20 or not f[i]:
        return []
    nf = len(FEAT_W)
    sd = [statistics.pstdev([x[j] for x in base]) or 1 for j in range(nf)]
    cand = []
    for j in range(i):
        if not f[j]:
            continue
        dist = math.sqrt(sum((FEAT_W[m] * (f[i][m] - f[j][m]) / sd[m]) ** 2 for m in range(nf)))
        cand.append((dist, j))
    cand.sort()
    return [j for _, j in cand[:k]]


PATH_DAYS = 21


def path(px, day, sym):
    """발표 전날 종가를 0으로 두고 그 뒤 거래일(비트코인은 하루)마다 변화 — 최대 21칸. 금리는 bp, 나머지는 %."""
    import bisect
    if sym not in px:
        return None
    d, c = px[sym]
    i0 = bisect.bisect_left(d, day)
    if i0 == 0 or i0 >= len(d):
        return None
    base = c[i0 - 1]
    bp = sym == "^TNX"
    step = 1.4 if sym == "BTC-USD" else 1
    out = [0.0]
    for n in range(PATH_DAYS):
        j = i0 + int(round(n * step))
        if j >= len(d):
            break
        out.append(round((c[j] - base) * 100, 1) if bp else round((c[j] / base - 1) * 100, 2))
    return out


def band(paths):
    """같은 칸끼리 중앙값 · 10~90% 범위(칸마다 표본 5개 이상인 곳까지)."""
    med, lo, hi = [], [], []
    for i in range(PATH_DAYS + 1):
        xs = sorted(p[i] for p in paths if p and len(p) > i)
        if len(xs) < 5:
            break
        med.append(round(statistics.median(xs), 2))
        lo.append(xs[int(len(xs) * 0.1)])
        hi.append(xs[min(len(xs) - 1, int(len(xs) * 0.9))])
    return {"med": med, "lo": lo, "hi": hi}


def summarize(rows, sym, h):
    xs = [r["rx"][sym][h] for r in rows if sym in r.get("rx", {}) and h in r["rx"][sym]]
    if len(xs) < 5:
        return None
    xs.sort()
    return {"n": len(xs), "med": round(statistics.median(xs), 2), "up": round(sum(1 for x in xs if x > 0) / len(xs), 2),
            "lo": xs[max(0, int(len(xs) * 0.1))], "hi": xs[min(len(xs) - 1, int(len(xs) * 0.9))]}


def pct_rank(hist, v):
    """지난 10년 발표 중 지금 값 이하인 비율(0 = 10년 중 가장 낮음, 1 = 가장 높음)."""
    t0 = hist[-1]["ts"] - 10 * 365 * 86400
    xs = [r["v"] for r in hist if r["ts"] >= t0]
    return round(sum(1 for x in xs if x <= v) / len(xs), 2) if xs else None


def situation(ind, hist):
    """지금 상황을 말로: 직전 대비 · 최근 3번 흐름 · 지난 10년 중 위치."""
    r = hist[-1]
    ch = r["v"] - r["prev"]
    # 이보다 작은 변화는 '거의 같음'(잡음 수준을 방향으로 읽지 않게)
    eps = {"nfp": 25, "claims": 5, "jolts": 0.1}.get(ind["k"], 0.05)
    dirn = "up" if ch > eps else "down" if ch < -eps else "flat"
    tr = r["d3"]
    trend = None if tr is None else ("up" if tr > eps else "down" if tr < -eps else "flat")
    return {"dir": dirn, "chg": ch, "trend": trend, "rank10y": pct_rank(hist, r["v"]), "vs_avg12": r["v"] - r["avg12"] if r["avg12"] is not None else None}


# ---------- 다가오는 일정 · 예상치 ----------
def ff_week():
    try:
        return json.loads(cached("ff-week.json", lambda: fetch("https://nfs.faireconomy.media/ff_calendar_thisweek.json"), max_age=3 * 3600))
    except Exception as e:
        log("FF 실패", type(e).__name__, str(e)[:100])
        return []


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"fc": {}, "ai": {}}


def upcoming(ff, state):
    """이번 주 미국 발표(중요도 높음·중간). 우리 지표면 키를 붙이고, 예상치는 state 에 저장(발표 뒤 실제 값과 비교)."""
    title_to = {}
    for ind in IND:
        for t, role in ind["ff"].items():
            title_to[t.lower()] = (ind["k"], role)
    out = []
    for e in ff:
        if e.get("country") != "USD" or e.get("impact") not in ("High", "Medium"):
            continue
        try:
            ts = int(datetime.fromisoformat(e["date"]).timestamp())
        except Exception:
            continue
        key = title_to.get((e.get("title") or "").lower())
        item = {"ts": ts, "title": e.get("title"), "impact": e["impact"].lower(), "fc": e.get("forecast") or "", "prev": e.get("previous") or ""}
        if key:
            item["k"], item["role"] = key
            if item["fc"]:
                state["fc"].setdefault(key[0], {})["%s|%s" % (time.strftime("%Y-%m-%d", time.gmtime(ts)), key[1])] = item["fc"]
        out.append(item)
    return sorted(out, key=lambda x: x["ts"])


# FRED 발표 일정(올해·내년): 발표 묶음 → 우리 지표들, 이름, 중요도
REL = [(10, ["cpi", "core_cpi"], "Consumer prices (CPI)", "소비자물가(CPI)", "high"), (46, ["ppi"], "Producer prices (PPI)", "생산자물가(PPI)", "medium"),
       (50, ["nfp", "unemp", "wages"], "Jobs report", "고용 보고서", "high"), (54, ["core_pce"], "PCE inflation", "PCE 물가", "high"),
       (53, ["gdp"], "GDP", "GDP", "high"), (9, ["retail"], "Retail sales", "소매판매", "medium"), (180, ["claims"], "Jobless claims", "실업수당 청구", "medium"),
       (192, ["jolts"], "Job openings (JOLTS)", "구인 건수(JOLTS)", "medium")]
_MONTHS = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])}


def fred_calendar(rid, year):
    """FRED 발표 일정 페이지의 발표 시각(미국 중부시간 표기) 목록."""
    def get():
        time.sleep(1.2)
        return fetch("https://fred.stlouisfed.org/releases/calendar?rid=%d&y=%d" % (rid, year))
    html = cached("cal-%d-%d.html" % (rid, year), get, max_age=24 * 3600)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    lines = [l.strip() for l in re.sub(r"<[^>]+>", "\n", text).split("\n") if l.strip()]
    out = []
    for i, l in enumerate(lines):
        m = re.fullmatch(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) (\w+) (\d{1,2}), (\d{4})", l)
        if not m or int(m.group(3)) != year:
            continue
        tm = next((x for x in lines[i + 1:i + 4] if re.fullmatch(r"\d{1,2}:\d{2} [ap]m", x)), None)
        if not tm:
            continue
        hh, mm = map(int, tm[:-3].split(":"))
        hh = hh % 12 + (12 if tm.endswith("pm") else 0)
        out.append(int(datetime(year, _MONTHS[m.group(1)], int(m.group(2)), hh, mm, tzinfo=ZoneInfo("America/Chicago")).timestamp()))
    return out


def fomc_dates():
    """연준 FOMC 금리 결정 시각(성명서, 동부 오후 2시)."""
    try:
        html = cached("fomc.html", lambda: fetch("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"), max_age=24 * 3600)
    except Exception as e:
        log("FOMC 일정 실패", type(e).__name__)
        return []
    # 해마다 'YYYY FOMC Meetings' 아래 월 · 날짜 범위("27-28", "17-18*", "Jan 31-Feb 1"). 결정은 마지막 날
    out = set()
    parts = re.split(r"(\d{4}) FOMC Meetings", html)
    for j in range(1, len(parts) - 1, 2):
        year = int(parts[j])
        for mon, rng in re.findall(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<', parts[j + 1], re.S):
            mon = mon.split("/")[-1].strip()
            day = re.findall(r"\d+", rng)
            if mon in _MONTHS and day:
                out.add(int(datetime(year, _MONTHS[mon], int(day[-1]), 14, 0, tzinfo=ET).timestamp()))
    return sorted(out)


def schedule(now, days=40):
    """앞으로 40일의 발표(우리 지표 묶음 + FOMC)."""
    yrs = sorted({datetime.fromtimestamp(now, ET).year, datetime.fromtimestamp(now + days * 86400, ET).year})
    out = []
    for rid, keys, en, ko, imp in REL:
        for y in yrs:
            try:
                tss = fred_calendar(rid, y)
            except Exception as e:
                log("발표 일정 실패", rid, y, type(e).__name__)
                continue
            out += [{"ts": t, "keys": keys, "en": en, "ko": ko, "impact": imp} for t in tss if now - 7 * 86400 <= t <= now + days * 86400]
    out += [{"ts": t, "keys": ["fomc"], "en": "Fed rate decision (FOMC)", "ko": "연준 금리 결정(FOMC)", "impact": "high"}
            for t in fomc_dates() if now - 7 * 86400 <= t <= now + days * 86400]
    return sorted(out, key=lambda x: x["ts"])


def merge_schedule(ff_items, sched, now):
    """일정(묶음 단위)에 이번 주 Forex Factory 예상치·이전치를 붙인다. 우리 지표가 아닌 FF 일정은 '기타'로."""
    used = set()
    for ev in sched:
        ev["items"] = []
        for i, it in enumerate(ff_items):
            if it.get("k") in ev["keys"] and abs(it["ts"] - ev["ts"]) < 3 * 3600:
                ev["items"].append({"title": it["title"], "k": it["k"], "role": it["role"], "fc": it["fc"], "prev": it["prev"]})
                used.add(i)
    others = [{"ts": it["ts"], "keys": [], "en": it["title"], "ko": None, "impact": it["impact"], "items": [{"title": it["title"], "fc": it["fc"], "prev": it["prev"]}]}
              for i, it in enumerate(ff_items) if i not in used and it["impact"] == "high"]
    return sorted(sched + others, key=lambda x: x["ts"])


# ---------- 예상치(Forex Factory 문자열 → 우리 단위) ----------
def ff_value(ind, txt):
    m = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*([%KMB]?)", txt or "")
    if not m:
        return None
    x, u = float(m.group(1)), m.group(2)
    if ind["k"] in ("nfp", "claims"):
        return x if u == "K" else x / 1000 if u == "" else x * 1000 if u == "M" else None
    if ind["k"] == "jolts":
        return x if u == "M" else x / 1000 if u == "K" else None
    return x if u in ("%", "") else None


def vs_fc(ind, actual, fc_txt, dec):
    """실제 값과 예상치를 예상치의 자릿수로 맞춰 비교: 'above' · 'below' · 'inline' · None."""
    f = ff_value(ind, fc_txt)
    if actual is None or f is None:
        return None
    m = re.search(r"\.(\d+)", fc_txt or "")
    d = len(m.group(1)) if m else 0
    a = round(actual, d) if ind["unit"] == "%" else round(actual, 0 if ind["k"] in ("nfp", "claims") else 2)
    return "above" if a > f + 1e-9 else "below" if a < f - 1e-9 else "inline"


# ---------- 표시용 숫자 ----------
def fmt(ind, x, lang="ko", signed=False):
    """화면·AI 입력에 같은 모양으로 쓰는 값. 고용 · 청구는 명/건, 구인은 백만, 나머지는 %."""
    if x is None:
        return None
    sg = "+" if signed and x > 0 else ""
    if ind["k"] in ("nfp", "claims"):
        n = int(round(x * 1000))
        return sg + ("{:,}{}".format(n, "명" if ind["k"] == "nfp" else "건") if lang == "ko" else "{:,}".format(n))
    if ind["k"] == "jolts":
        return sg + ("{:,}만 건".format(int(round(x * 100))) if lang == "ko" else "{:.2f}M".format(x))
    return sg + "{:.{}f}%".format(x, ind["dec"])


def fmt_chg(ind, x, lang="ko"):
    if x is None:
        return None
    if ind["unit"] == "%":
        return ("{:+.{}f}%p" if lang == "ko" else "{:+.{}f} pt").format(x, ind["dec"])
    return fmt(ind, x, lang, signed=True)


def pct_s(x, kind="pct"):
    return None if x is None else ("{:+.0f}bp".format(x) if kind == "bp" else "{:+.1f}%".format(x))


# ---------- AI 해석(Gemma) ----------
ADVICE = re.compile(r"매수하|매도하|사세요|파세요|추천|담아|비중을 늘|비중을 줄|진입하|손절|\bbuy\b|\bsell\b", re.I)
FUTURE = re.compile(r"(할|될|오를|내릴|떨어질|이어질|커질|높아질|낮아질|올라갈|내려갈) (것|가능성)|전망이다|전망된다|\bwill\b|\blikely\b|\bexpect(s|ed)? to\b|\bset to\b", re.I)
CAUSE_PX = re.compile(r"(때문에|탓에|덕분에|영향으로|여파로|로 인해|으로 인해)[^.]{0,30}(올랐|내렸|상승|하락|급등|급락)|\b(because|due to|driven by)\b[^.]{0,40}\b(rose|fell|jumped|dropped|rallied|slid)", re.I)


def _norm(n):
    n = n.replace(",", "").lstrip("+-")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n.lstrip("0") or "0"


def nums(t):
    """글 속 숫자 집합(쉼표 · 부호 · 앞자리 0 · 소수 끝 0 무시: '09' = '9', '3.70' = '3.7')."""
    return {_norm(n) for n in re.findall(r"[+-]?\d[\d,]*(?:\.\d+)?", t)}


HANGUL = re.compile(r"[가-힣]")


def ok_text(t, src, lang="ko"):
    if lang == "en" and HANGUL.search(t):
        return False
    return bool(t) and not (nums(t) - nums(src)) and not ADVICE.search(t) and not FUTURE.search(t) and not CAUSE_PX.search(t)


def chat(system, user, n=900):
    body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "10m", "options": {"temperature": 0.3, "num_ctx": 8192, "num_predict": n},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        t = json.loads(r.read())["message"]["content"]
    return json.loads(t[t.index("{"): t.rindex("}") + 1])


SYS_IND = """너는 경제지표를 처음 보는 사람에게 설명하는 편집자다. 숫자 비교 문장은 이미 따로 있다. 너는 그 숫자가 '무슨 뜻인지'만 1~2문장으로 쓴다(자료가 한국어면 한국어, 영어면 영어). JSON 으로.
반드시 지킬 것:
- 값 · 퍼센트 · 연도 같은 숫자를 쓰지 않는다('지난 10년', '세 번'은 된다). 지표 이름을 괄호로 되풀이하지 않고, 영어를 괄호로 덧붙이지 않는다.
- '변화의 뜻' · '최근 3번 흐름' · '수준의 뜻'을 자연스럽게 풀어 쓴다. 뜻은 자료에 적힌 것만 쓰고 스스로 해석을 뒤집거나 더하지 않는다. 자료에 없는 뜻은 빼고 쓴다.
- 자료에 없는 비교 대상(다른 지표, 사람 수, 보조 수치의 변화 등)을 만들지 않는다.
- '10년 중 위치 77' 같은 숫자 순위는 쓰지 않는다.
- 한국어는 '~했어요/~예요' 말투. 영어는 짧고 평이하게. 괄호 풀이는 전문용어에만, 한 번, 짧게. 영어 문장에 한글을 넣지 않는다.
- 예(한국어): "물가 오름세가 세 번 연속 빨라졌고, 지난 10년과 비교해도 높은 편이에요."
- 예(English): "Inflation has sped up three releases in a row and is high compared with the past decade."
- 숫자는 자료에 적힌 문자열 그대로만 쓴다. 자료에 없는 숫자·사람·기관·사건을 만들지 않는다.
- 앞으로 어떻게 될지 예측하지 않는다('~할 것', '전망', 'will', 'likely' 금지). 사라·팔라는 말 금지. 가격 움직임을 원인으로 묶지 않는다.
- 쉬운 말로. 전문용어는 괄호로 짧게 풀어 쓴다.
- 출력: {"s": ["문장1", "문장2"]}"""

SYS_ALL = """너는 미국 경제를 처음 보는 사람에게 설명하는 편집자다. 묶음(물가 · 고용 · 성장)별 최신 지표와 그 뜻을 보고, 지금 경제가 어떤 흐름인지 해석해서 쓴다.
반드시 지킬 것:
- head: 지금 흐름을 한 줄로(20자 안팎, 숫자 없이). s: 물가 · 고용 · 성장 순서로 3문장. 각 문장은 그 묶음의 지표들이 같은 쪽을 가리키는지, 엇갈리는지를 말하고 대표 숫자는 1개만 쓴다.
- 뜻('변화의 뜻', '수준의 뜻')은 자료에 적힌 것만 쓰고 뒤집지 않는다. 숫자는 자료에 적힌 문자열 그대로만 쓴다.
- 예측하지 않는다('~할 것', '전망', 'will', 'likely' 금지). 사라·팔라는 말 금지.
- 자료가 한국어면 한국어('~해요' 말투), 영어면 영어로. 영어 문장에 한글을 넣지 않는다.
- 예(한국어): head "물가는 다시 뜨겁고, 고용은 식는 중" / s ["소비자물가가 3.7%로 예상보다 높았고 생산자물가도 오름세라, 물가 쪽은 다시 뜨거워지는 모습이에요.", ...]
- 예(English): head "Prices heat up while hiring cools" / s ["Consumer prices came in at 3.7%, above forecast, and producer prices are also climbing, so inflation is heating up again.", ...]
- 출력: {"head": "...", "s": ["물가", "고용", "성장"]}"""


DIR_KO = {"prices": ("물가가 더 빨리 오름(뜨거워짐)", "물가 오름세가 느려짐(식음)"), "jobs": ("고용이 강해짐", "고용이 약해짐"), "growth": ("경기가 빨라짐", "경기가 느려짐")}
DIR_EN = {"prices": ("prices rising faster (hotter)", "price growth slowing (cooler)"), "jobs": ("jobs market stronger", "jobs market weaker"), "growth": ("economy faster", "economy slower")}
LVL_KO = {"prices": ("물가가 높은 편", "물가가 낮은 편"), "jobs": ("고용이 강한 편", "고용이 약한 편"), "growth": ("성장이 빠른 편", "성장이 느린 편")}
LVL_EN = {"prices": ("inflation on the high side", "inflation on the low side"), "jobs": ("jobs market on the strong side", "jobs market on the weak side"), "growth": ("growth on the fast side", "growth on the slow side")}
FC_KO = {"above": "예상보다 높음", "below": "예상보다 낮음", "inline": "예상과 같음"}
FC_EN = {"above": "above forecast", "below": "below forecast", "inline": "in line with forecast"}


# 묶음 표현 대신 지표에 맞는 말(오를 때, 내릴 때)
DIR_IND = {"wages": (("임금이 더 빨리 오름", "임금 오름세가 느려짐"), ("wages rising faster", "wage growth slowing")),
           "retail": (("소비가 더 늘어남", "소비 증가세가 느려짐"), ("spending growing faster", "spending growth slowing"))}


def meaning(ind, x):
    """방향 · 수준의 뜻(프로그램이 정함). hot=-1 지표(실업률·청구)는 값이 낮을수록 고용이 강하다."""
    S, g = x["sit"], ind["grp"]
    d = S["dir"]
    dk = de = None
    if d in ("up", "down"):
        hot = (d == "up") == (ind["hot"] > 0)
        if ind["k"] in DIR_IND:
            dk, de = DIR_IND[ind["k"]][0][0 if hot else 1], DIR_IND[ind["k"]][1][0 if hot else 1]
        else:
            dk, de = DIR_KO[g][0 if hot else 1], DIR_EN[g][0 if hot else 1]
    r = S["rank10y"]
    lk = le = None
    if r is not None and (r >= 0.75 or r <= 0.25):
        hi = (r >= 0.75) == (ind["hot"] > 0)
        lk, le = LVL_KO[g][0 if hi else 1], LVL_EN[g][0 if hi else 1]
    return dk, de, lk, le


def facts_ind(ind, x, lang):
    L, S = x["latest"], x["sit"]
    dk, de, lk, le = meaning(ind, x)
    ko = lang == "ko"
    lvl = None if S["rank10y"] is None else ("높은 편" if S["rank10y"] >= 0.75 else "낮은 편" if S["rank10y"] <= 0.25 else "중간") if ko else \
        ("high" if S["rank10y"] >= 0.75 else "low" if S["rank10y"] <= 0.25 else "middle")
    main_name = {"yoy": ("전년 같은 달 대비", "year on year"), "mom": ("전월 대비", "month on month"), "diff": ("전월 대비 증감", "change on the month"),
                 "level": ("값", "level"), "saar": ("전 분기 대비 연율", "annualized, quarter on quarter")}[ind["t"]][0 if ko else 1]
    blk = {"기준" if ko else "basis": main_name, "이번" if ko else "this release": fmt(ind, L["v"], lang), "직전" if ko else "previous": fmt(ind, L["prev"], lang),
           "직전 대비" if ko else "change": fmt_chg(ind, S["chg"], lang)}
    if L.get("fc"):
        blk["예상치" if ko else "forecast"] = fmt(ind, ff_value(ind, L["fc"]), lang) if ff_value(ind, L["fc"]) is not None else L["fc"]
        v = vs_fc(ind, L["v"], L["fc"], ind["dec"])
        if v:
            blk["예상 대비" if ko else "vs forecast"] = (FC_KO if ko else FC_EN)[v]
    f = {"지표" if ko else "indicator": ind["ko"] if ko else ind["en"], "기간" if ko else "period": L["period"][:7], "본 수치" if ko else "headline": blk}
    if L.get("sub") is not None and ind.get("sub"):
        sb = {"기준" if ko else "basis": "전월 대비" if ko else "month on month", "이번" if ko else "this release": "{:.{}f}%".format(L["sub"], ind["dec"])}
        if L.get("fc_sub"):
            sb["예상치" if ko else "forecast"] = L["fc_sub"]
            v = vs_fc(ind, L["sub"], L["fc_sub"], ind["dec"])
            if v:
                sb["예상 대비" if ko else "vs forecast"] = (FC_KO if ko else FC_EN)[v]
        f["보조 수치" if ko else "second figure"] = sb
    f["변화의 뜻" if ko else "what the change means"] = dk if ko else de
    f["최근 3번 흐름" if ko else "trend over 3 releases"] = ({"up": "오름세", "down": "내림세", "flat": "제자리"} if ko else {"up": "rising", "down": "falling", "flat": "flat"}).get(S["trend"])
    f["지난 10년 중 수준" if ko else "level vs past 10 years"] = lvl
    f["수준의 뜻" if ko else "what the level means"] = lk if ko else le
    return {k: v for k, v in f.items() if v is not None}


BASIS = {"yoy": ("전년 대비", "year on year"), "mom": ("전월 대비", "month on month"), "saar": ("연율", "annualized")}


def has_final(word):
    """마지막 글자에 받침이 있나(조사 고르기). '%'는 '퍼센트'로 읽어 받침 없음."""
    ch = word.strip()[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    return ch in "0136789LMNlmn"


def cmp_word(a, b, dec):
    if a is None or b is None:
        return None
    a, b = round(a, dec), round(b, dec)
    return "above" if a > b else "below" if a < b else "inline"


KO_CMP = {"above": "높고", "below": "낮고", "inline": "같고"}
KO_END = {"above": "높아요", "below": "낮아요", "inline": "같아요"}
EN_CMP = {"above": "above", "below": "below", "inline": "in line with"}


def lead_line(ind, x, lang):
    """첫 문장(프로그램): 이번 값 · 직전 · 예상 비교. 같은 기준끼리만 비교한다."""
    L, ko = x["latest"], lang == "ko"
    v, pv = fmt(ind, L["v"], lang), fmt(ind, L["prev"], lang)
    dec = ind["dec"] if ind["unit"] == "%" else (0 if ind["k"] in ("nfp", "claims") else 2)
    cp = cmp_word(L["v"], L["prev"], dec)
    fcv = ff_value(ind, L.get("fc"))
    vf = vs_fc(ind, L["v"], L.get("fc"), ind["dec"]) if fcv is not None else None
    b = BASIS.get(ind["t"])
    sub_s = None
    if L.get("sub") is not None and ind.get("sub") and L.get("fc_sub"):
        vs = vs_fc(ind, L["sub"], L["fc_sub"], ind["dec"])
        if vs:
            sub_s = ("{:.{}f}%".format(L["sub"], ind["dec"]), L["fc_sub"], vs)
    if ko:
        name = ind["ko"] + ("({})".format(b[0]) if b else "")
        s1 = "{}{} {}{}.".format(name, "은" if has_final(ind["ko"]) else "는", v, "이었어요" if has_final(v) else "였어요")
        parts = []
        if cp:
            parts.append(("직전 {}보다".format(pv) if cp != "inline" else "직전 {}{}".format(pv, "과" if has_final(pv) else "와"), cp))
        if vf:
            fs_ = fmt(ind, fcv, lang)
            parts.append(("예상 {}보다".format(fs_) if vf != "inline" else "예상 {}{}".format(fs_, "과" if has_final(fs_) else "와"), vf))
        if parts:
            s1 += " " + ", ".join("{} {}".format(t, KO_CMP[c] if k < len(parts) - 1 else KO_END[c]) for k, (t, c) in enumerate(parts)) + "."
        if sub_s:
            s1 += " 전월 대비로는 {}로 예상 {}{}.".format(sub_s[0], sub_s[1], "보다 " + KO_END[sub_s[2]] if sub_s[2] != "inline" else ("과" if has_final(sub_s[1]) else "와") + " 같아요")
        return s1
    s1 = "{} came in at {}{}".format(ind["en"], v, " ({})".format(b[1]) if b else "")
    parts = []
    if cp:
        parts.append("{} the previous {}".format(EN_CMP[cp], pv))
    if vf:
        parts.append("{} the {} forecast".format(EN_CMP[vf], fmt(ind, fcv, lang)))
    s1 += (", " + " and ".join(parts) if parts else "") + "."
    if sub_s:
        s1 += " Month on month it was {}, {} the {} forecast.".format(sub_s[0], EN_CMP[sub_s[2]], sub_s[1])
    return s1


SYS_IND_EN = """You explain economic data to people seeing it for the first time. A sentence with the numbers already exists. Write only what the numbers MEAN, in 1-2 short plain English sentences. Output JSON.
Rules:
- No figures at all (values, percentages, years). Words like "three releases" or "the past 10 years" are fine.
- Use only the meanings given ("what the change means", "trend over 3 releases", "what the level means"). Never reverse or add an interpretation.
- Do not invent comparisons that are not in the data (other indicators, numbers of people, changes in the second figure).
- No forecasts ("will", "likely", "expected to"), no buy/sell advice, no claims that the data moved prices.
- English only. Do not repeat the indicator name in parentheses. No Korean characters.
- Example: {"s": ["Inflation has sped up three releases in a row and is high compared with the past decade."]}
- Output: {"s": ["sentence 1", "sentence 2"]}"""


SUB_TALK = re.compile(r"전월|월간|보다|month|예상|forecast|expected|than", re.I)


# 뜻(짧은 말) → 대체 문장
SENT = {"물가가 더 빨리 오름(뜨거워짐)": ("물가가 더 빨리 오르고 있어요", "Prices are rising faster"),
        "물가 오름세가 느려짐(식음)": ("물가 오름세가 느려지고 있어요", "Price growth is slowing"),
        "고용이 강해짐": ("고용이 강해지고 있어요", "The jobs market is getting stronger"), "고용이 약해짐": ("고용이 약해지고 있어요", "The jobs market is getting weaker"),
        "경기가 빨라짐": ("경기가 빨라지고 있어요", "The economy is speeding up"), "경기가 느려짐": ("경기가 느려지고 있어요", "The economy is slowing"),
        "임금이 더 빨리 오름": ("임금이 더 빨리 오르고 있어요", "Wages are rising faster"), "임금 오름세가 느려짐": ("임금 오름세가 느려지고 있어요", "Wage growth is slowing"),
        "소비가 더 늘어남": ("소비가 더 늘고 있어요", "Spending is growing faster"), "소비 증가세가 느려짐": ("소비 증가세가 느려지고 있어요", "Spending growth is slowing")}


def meaning_line(ind, x, lang):
    """AI 가 규칙을 지키지 못할 때 쓰는 뜻 문장(프로그램)."""
    dk, de, lk, le = meaning(ind, x)
    tr = x["sit"]["trend"]
    ko = lang == "ko"
    out = []
    if dk and dk in SENT:
        out.append(SENT[dk][0 if ko else 1])
    if tr:
        out.append(("최근 세 번은 " + {"up": "오름세", "down": "내림세", "flat": "제자리"}[tr] + "예요") if ko else
                   ("It has been " + {"up": "rising", "down": "falling", "flat": "flat"}[tr] + " over the last three releases"))
    if lk:
        out.append((lk + "이에요") if ko else ("That is " + le + " for the past 10 years"))
    return ". ".join(out) + "." if out else None


def ai_indicator(ind, x, state):
    key = "%s|%s|v10" % (ind["k"], x["latest"]["d"])
    if key in state["ai"]:
        return state["ai"][key]
    out = {}
    for lang in ("ko", "en"):
        src = json.dumps(facts_ind(ind, x, lang), ensure_ascii=False)
        for attempt in range(3):
            try:
                r = chat(SYS_IND if lang == "ko" else SYS_IND_EN, ("자료:\n" if lang == "ko" else "Data:\n") + src)
                ss = [str(t).strip() for t in r.get("s", []) if str(t).strip()][:2]
                # 뜻 문장에는 숫자 · 월간 비교 · 예상 비교를 쓰지 않는다(첫 문장이 정확히 맡는다)
                bad = [t for t in ss if not ok_text(t, src, lang) or (nums(t) - {"10", "3"}) or SUB_TALK.search(t)]
                if ss and not bad:
                    out[lang] = [lead_line(ind, x, lang), " ".join(ss)]
                    break
                log("AI 문장 거절", ind["k"], lang, attempt, (bad or ["개수"])[0][:90])
            except Exception as e:
                log("AI 실패", ind["k"], lang, type(e).__name__, str(e)[:100])
    for lang in ("ko", "en"):
        if lang not in out:
            m = meaning_line(ind, x, lang)
            out[lang] = [lead_line(ind, x, lang)] + ([m] if m else [])
            out["src_" + lang] = "program"
    out["at"] = int(time.time())
    state["ai"][key] = out
    return out


def ai_overview(inds, state):
    key = "all|v3|" + ",".join(x["k"] + x["latest"]["d"] for x in inds)
    if key in state["ai"]:
        return state["ai"][key]
    out = {}
    for lang in ("ko", "en"):
        names = {g: (ko if lang == "ko" else en) for g, en, ko in GROUPS}
        src = json.dumps({names[g]: [facts_ind(BY[x["k"]], x, lang) for x in inds if x["grp"] == g] for g, *_ in GROUPS}, ensure_ascii=False)
        for attempt in range(3):
            try:
                r = chat(SYS_ALL, ("최신 지표:\n" if lang == "ko" else "Latest indicators (write in English):\n") + src, n=1200)
                head, ss = str(r.get("head", "")).strip(), [str(t).strip() for t in r.get("s", [])][:3]
                bad = [t for t in [head] + ss if not ok_text(t, src, lang)]
                if head and len(ss) == 3 and not bad:
                    out[lang] = {"head": head, "s": ss}
                    break
                log("AI 개요 거절", lang, attempt, (bad or ["개수"])[0][:90])
            except Exception as e:
                log("AI 개요 실패", lang, type(e).__name__, str(e)[:100])
    if len(out) < 2:
        return None
    out["at"] = int(time.time())
    state["ai"] = {k: v for k, v in state["ai"].items() if not k.startswith("all|")}
    state["ai"][key] = out
    return out


def past_line(ind, x, lang):
    """'과거에 비슷했을 때' 한 문장(프로그램): S&P 500 1주 뒤 중앙값, 평소와 비교."""
    st = (x["stats"].get("^GSPC") or {}).get("w1") or {}
    a, s2 = st.get("all"), st.get("sim")
    if not a or not s2:
        return None
    diff = s2["med"] - a["med"]
    same = abs(diff) < 0.5 and abs(s2["up"] - a["up"]) < 0.15
    if lang == "ko":
        return "지금과 비슷했던 과거 {}번, S&P 500은 1주 뒤 중앙값 {}로 {}(평소 {}). 오른 경우 {}번 중 {}번.".format(
            s2["n"], pct_s(s2["med"]), "평소와 비슷했어요" if same else ("평소보다 좋았어요" if diff > 0 else "평소보다 약했어요"), pct_s(a["med"]),
            s2["n"], int(round(s2["up"] * s2["n"])))
    return "In the {} most similar past releases, the S&P 500 had a median {} a week later, {} (typical {}). It rose in {} of {}.".format(
        s2["n"], pct_s(s2["med"]), "about the same as usual" if same else ("better than usual" if diff > 0 else "weaker than usual"), pct_s(a["med"]),
        int(round(s2["up"] * s2["n"])), s2["n"])


# ---------- 조립 ----------
def build(no_ai=False):
    os.makedirs(CACHE, exist_ok=True)
    state = load_state()
    up = upcoming(ff_week(), state)
    px = prices()
    inds = []
    for ind in IND:
        try:
            hist = releases(ind)
        except Exception as e:
            log("지표 실패", ind["k"], type(e).__name__, str(e)[:160])
            continue
        if len(hist) < 30:
            log("기록 부족", ind["k"], len(hist))
            continue
        for r in hist:
            r["rx"] = reactions(px, r["d"])
        cur = len(hist) - 1
        sim = similar(hist, cur)
        allrows = hist[:cur]
        simrows = [hist[j] for j in sim]
        stats = {}
        for sym, *_ in ASSETS:
            for h, *_ in HORIZONS:
                a, s = summarize(allrows, sym, h), summarize(simrows, sym, h)
                if a or s:
                    stats.setdefault(sym, {})[h] = {"all": a, "sim": s}
        # 발표 뒤 한 달 경로: 비슷한 회차 하나하나 + 모든 회차의 중앙값·범위(평소)
        paths = {}
        for sym, *_ in ASSETS:
            sp = [path(px, hist[j]["d"], sym) for j in sim]
            ap = [path(px, r["d"], sym) for r in allrows]
            if sum(1 for p in sp if p) >= 5:
                paths[sym] = {"sim": sp, "sim_band": band(sp), "all_band": band(ap), "all_n": sum(1 for p in ap if p)}
        last = hist[-1]
        fc = state["fc"].get(ind["k"], {})
        dec = ind["dec"]

        def rnd(x, dd=dec):
            return None if x is None else round(x, dd + (2 if ind["unit"] == "%" else 1))
        inds.append({
            "k": ind["k"], "en": ind["en"], "ko": ind["ko"], "unit": ind["unit"], "grp": ind["grp"], "dec": dec, "hot": ind["hot"],
            "sub": ind.get("sub"), "n": len(hist), "since": hist[0]["d"],
            "latest": {"d": last["d"], "ts": last["ts"], "period": last["period"], "v": rnd(last["v"]), "prev": rnd(last["prev"]), "sub": rnd(last["sub"]),
                       "fc": fc.get(last["d"] + "|main"), "fc_sub": fc.get(last["d"] + "|sub"),
                       # 예상 대비(프로그램 판정: 예상치 자릿수로 맞춰 비교)
                       "vs": vs_fc(ind, last["v"], fc.get(last["d"] + "|main"), dec), "vs_sub": vs_fc(ind, last["sub"], fc.get(last["d"] + "|sub"), dec)},
            "sit": {k2: (rnd(v2) if k2 in ("chg", "vs_avg12") else v2) for k2, v2 in situation(ind, hist).items()},
            # 지난 발표 표(최근 24회) · 긴 그래프(전체, 관측월과 값)
            "rows": [{"d": r["d"], "ts": r["ts"], "period": r["period"], "v": rnd(r["v"]), "prev": rnd(r["prev"]), "sub": rnd(r["sub"]),
                      "fc": fc.get(r["d"] + "|main"), "rx": r["rx"]} for r in hist[-24:]][::-1],
            "long": [[r["period"], rnd(r["v"])] for r in hist],
            "similar": [{"d": hist[j]["d"], "period": hist[j]["period"], "v": rnd(hist[j]["v"]), "prev": rnd(hist[j]["prev"]), "rx": hist[j]["rx"]} for j in sim],
            "stats": stats, "paths": paths,
        })
        log("지표", ind["k"], "발표", len(hist), "최근", last["d"], last["period"], round(last["v"], 2), "비슷한 과거", len(sim))
    now = int(time.time())
    up = merge_schedule(up, schedule(now), now)
    for x in inds:
        ind = BY[x["k"]]
        x["disp"] = {"v": [fmt(ind, x["latest"]["v"]), fmt(ind, x["latest"]["v"], "en")], "prev": [fmt(ind, x["latest"]["prev"]), fmt(ind, x["latest"]["prev"], "en")],
                     "chg": [fmt_chg(ind, x["sit"]["chg"]), fmt_chg(ind, x["sit"]["chg"], "en")]}
        x["past"] = {"ko": past_line(ind, x, "ko"), "en": past_line(ind, x, "en")}
        if not no_ai:
            x["ai"] = ai_indicator(ind, x, state)
    overview = None if no_ai else ai_overview(inds, state)
    doc = {"v": 1, "made": now, "next": now + EVERY, "groups": [{"k": g, "en": e, "ko": k} for g, e, k in GROUPS],
           "assets": [{"sym": s, "en": e, "ko": k, "kind": kd} for s, e, k, kd in ASSETS], "horizons": [h for h, *_ in HORIZONS],
           "indicators": inds, "upcoming": up, "overview": overview, "model": MODEL,
           "note_en": "Past records, not a forecast. Values are as first published on release day. Price changes run from the close before the release.",
           "note_ko": "예측이 아니라 과거 기록이에요. 지표 값은 발표 당일 처음 공개된 숫자이고, 가격 변화는 발표 전날 종가 기준이에요."}
    with open(STATE + ".tmp", "w") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(STATE + ".tmp", STATE)
    return doc


LABEL = "com.signal.econ"


def install():
    dst = os.path.join(HOME, "econ_brief.py")
    shutil.copy2(os.path.abspath(__file__), dst)
    py = os.path.join(HOME, "tgvenv", "bin", "python")
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
    with open(plist, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{py}</string><string>{dst}</string></array>
  <key>StartInterval</key><integer>{EVERY}</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>{HOME}/econ.log</string>
  <key>StandardErrorPath</key><string>{HOME}/econ.log</string>
</dict></plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    for _ in range(10):
        if subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", plist], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    log("설치 완료:", plist, "(1시간마다)")


def main():
    if "--install" in sys.argv[1:]:
        install()
        return
    no_ai = "--no-ai" in sys.argv
    doc = build(no_ai)
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out + ".tmp", "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(out + ".tmp", out)
    log("완료", out, os.path.getsize(out) // 1024, "KB", "지표", len(doc["indicators"]), "일정", len(doc["upcoming"]))


if __name__ == "__main__":
    main()
