"""과거 데이터 백필(한 번 실행). 결과는 pipeline/static/ 에 저장해 저장소에 넣는다.

사용:
  python3 -m pipeline.backfill listings   # 업비트 거래 공지 전체 + 원화 상장 곡선 (업비트가 GitHub를 막으므로 Mac에서)
  python3 -m pipeline.backfill events     # 미국 주요 발표 과거 시각(FRED·연준) + 발표 전후 BTC 변동

받은 응답은 /tmp/signal-backfill-cache.json 에 남겨, 중간에 끊겨도 다시 받지 않는다.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from . import config, listings, market, util

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
CACHE_PATH = "/tmp/signal-backfill-cache.json"
_cache = util.read_json(CACHE_PATH, {})


def cached(key, fn):
    if key in _cache:
        return _cache[key]
    val = fn()
    _cache[key] = val
    if len(_cache) % 20 == 0:
        util.write_json(CACHE_PATH, _cache)
    return val


def save_cache():
    util.write_json(CACHE_PATH, _cache)


# ---------- 업비트 상장 ----------

def all_notices():
    out = []
    for page in range(1, 200):
        url = "https://api-manager.upbit.com/api/v1/announcements?os=web&page=%d&per_page=20&category=trade" % page
        data = cached("list-%d" % page, lambda: util.http_json(url, retries=2))
        rows = (data.get("data") or {}).get("notices") or []
        out += rows
        if len(rows) < 20:
            break
        time.sleep(0.3)
    return out


def notice_body(uid):
    def get():
        time.sleep(0.3)
        d = util.http_json(config.UPBIT_NOTICE_DETAIL % uid, retries=2)
        return (d.get("data") or {}).get("body") or ""
    return cached("body-%s" % uid, get)


def upbit_fetch(suffix):
    # 앞선 실행이 'upc-<질의>'로 남긴 1분봉 캐시를 그대로 쓴다
    key = "upc-" + suffix.split("?", 1)[1] if suffix.startswith("minutes/1?") else "upd-" + suffix
    return cached(key, lambda: util.http_json(config.UPBIT_CANDLES_BASE + suffix, retries=2))


def backfill_listings():
    raw = all_notices()
    notices = [listings.parse_notice(n) for n in raw]
    notices = [n for n in notices if n["ts"]]
    notices.sort(key=lambda n: n["ts"])
    util.log("notices", len(notices))

    # 원화 상장은 코인마다 한 번: 같은 코인의 '시점 변경 안내' 같은 후속 공지는 첫 공지에 묶는다
    seen_any = {}
    entries = {}
    for n in notices:
        if n["kind"] != "listing":
            continue
        for sym in n["symbols"]:
            first_seen = seen_any.get(sym)
            if n["krw"]:
                key = sym
                prev = entries.get(key)
                if prev and n["ts"] - prev["notice_ts"] < 10 * 86400:
                    prev["uids"].append(n["uid"])
                    continue
                if prev:  # 오래전 상장 후 다시 상장된 코인은 따로 센다
                    key = "%s-%d" % (sym, n["ts"])
                entries[key] = {"sym": sym, "uid": n["uid"], "uids": [n["uid"]], "notice_ts": n["ts"], "title": n["title"],
                                "mode": "added" if first_seen and first_seen < n["ts"] - 86400 else "new"}
            seen_any.setdefault(sym, n["ts"])
    krw_titles = [n for n in notices if n["kind"] == "listing" and n["krw"]]
    no_sym = [n for n in krw_titles if not n["symbols"]]
    util.log("krw listing notices", len(krw_titles), "entries", len(entries), "without ticker", len(no_sym))

    out = []
    for i, e in enumerate(sorted(entries.values(), key=lambda x: x["notice_ts"])):
        body_ts = None
        for uid in e["uids"]:
            t = listings.trade_time_from_body(notice_body(uid), e["notice_ts"])
            if t:
                body_ts = t  # 후속 '변경 안내'가 있으면 마지막 값이 최종 시각
        tc, trade_ts, why = listings.trade_curve(e["sym"], e["notice_ts"], body_ts, fetch=upbit_fetch)
        nc = cached("bn-%s-%d" % (e["sym"], e["notice_ts"]), lambda: listings.notice_curve(e["sym"], e["notice_ts"]))
        rec = {"sym": e["sym"], "uid": e["uid"], "title": e["title"], "notice_ts": e["notice_ts"], "trade_ts": trade_ts,
               "mode": e["mode"], "notice": nc, "trade": tc}
        if why:
            rec["excluded"] = why
        out.append(rec)
        if i % 10 == 0:
            util.log("listing", i, e["sym"], util.iso(e["notice_ts"]), "trade" if tc else why, "binance" if nc else "-")
            save_cache()
    save_cache()
    keep = [{k: n[k] for k in ("uid", "ts", "title", "kind", "krw", "symbols")} for n in notices if n["kind"] in ("listing", "caution", "delisting")]
    doc = {"built": util.now_ts(), "notices": keep, "listings": out,
           "unparsed_krw_titles": [{"uid": n["uid"], "ts": n["ts"], "title": n["title"]} for n in no_sym]}
    os.makedirs(STATIC, exist_ok=True)
    util.write_json(os.path.join(STATIC, "listings_history.json"), doc)
    ok_t = sum(1 for r in out if r.get("trade"))
    ok_n = sum(1 for r in out if r.get("notice"))
    util.log("saved", len(out), "listings; trade curves", ok_t, "notice curves", ok_n)


# ---------- 미국 발표 ----------

FRED_RELEASES = {"cpi": 10, "ppi": 46, "nfp": 50, "pce": 54, "gdp": 53, "retail": 9, "claims": 180}
_CT = ZoneInfo("America/Chicago")
_MONTHS = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September",
                                           "October", "November", "December"])}


def fred_dates(rid, year):
    """FRED 발표 일정 페이지에서 (발표 시각 ts) 목록. 시각은 미국 중부시간으로 적혀 있다."""
    url = "https://fred.stlouisfed.org/releases/calendar?rid=%d&y=%d" % (rid, year)

    def get():
        time.sleep(1.2)  # robots.txt Crawl-delay: 1
        return util.http_get(url, timeout=40, retries=2).decode("utf-8", "ignore")
    html = cached("fred-%d-%d" % (rid, year), get)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    out = []
    for i, l in enumerate(lines):
        m = re.fullmatch(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) (\w+) (\d{1,2}), (\d{4})", l)
        if not m:
            continue
        tm = next((x for x in lines[i + 1:i + 4] if re.fullmatch(r"\d{1,2}:\d{2} [ap]m", x)), None)
        if not tm:
            continue
        hh, mm = map(int, tm[:-3].split(":"))
        hh = hh % 12 + (12 if tm.endswith("pm") else 0)
        dt = datetime(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)), hh, mm, tzinfo=_CT)
        out.append(int(dt.timestamp()))
    return out


def fomc_calendar():
    """연준 FOMC 일정 페이지에서 금리 결정(성명서, 오후 2시 동부시간)·기자회견(오후 2시 30분)·의사록 공개(오후 2시) 시각."""
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    html = cached("fed-calendar", lambda: util.http_get(url, timeout=40, retries=2).decode("utf-8", "ignore"))
    et = ZoneInfo("America/New_York")

    def at(ymd, hh, mm):
        return int(datetime(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:]), hh, mm, tzinfo=et).timestamp())
    decisions = sorted({at(d, 14, 0) for d in re.findall(r"/newsevents/pressreleases/monetary(\d{8})a\.htm", html)})
    # 기자회견은 금리 결정 당일 것만 센다(페이지의 다른 링크·자료 제외)
    days = {d for d in re.findall(r"/newsevents/pressreleases/monetary(\d{8})a\.htm", html)}
    press = sorted({at(d, 14, 30) for d in re.findall(r"/monetarypolicy/fomcpresconf(\d{8})\.htm", html) if d in days})
    minutes = []
    for mon, day, year in re.findall(r"Released (\w+) (\d{1,2}), (\d{4})", html):
        if mon in _MONTHS:
            minutes.append(int(datetime(int(year), _MONTHS[mon], int(day), 14, 0, tzinfo=et).timestamp()))
    return decisions, press, sorted(set(minutes))


def btc_move(ts):
    """발표 직전 1분 종가 대비 15분·1시간 뒤 BTC 변동(%)."""
    t0 = ts - ts % 60
    def get():
        rows = market.candles("BTC", 60, t0 - 120, t0 + 3660)
        return [[t, c] for t, _, c in rows]
    rows = cached("btc-%d" % t0, get)
    by = {t: c for t, c in rows}
    base = by.get(t0 - 60)
    if not base:
        return None
    out = {}
    for w, sec in (("15m", 900), ("1h", 3600)):
        c = by.get(t0 + sec - 60)
        if c:
            out[w] = round((c / base - 1) * 100, 4)
    return out or None


def backfill_events():
    now = util.now_ts()
    years = sorted({util.kst(now).year - 1, util.kst(now).year})
    kinds = {}
    for kind, rid in FRED_RELEASES.items():
        ts = []
        for y in years:
            ts += fred_dates(rid, y)
        kinds[kind] = sorted(set(ts))  # 올해 남은 예정 시각도 남겨 레이더에 쓴다
        util.log("fred", kind, len(kinds[kind]))
    decisions, press, minutes = fomc_calendar()
    kinds["fomc"], kinds["fomc_press"], kinds["minutes"] = decisions, press, minutes
    util.log("fomc", len(kinds["fomc"]), "press", len(kinds["fomc_press"]), "minutes", len(kinds["minutes"]))
    moves = {}
    for kind, tss in kinds.items():
        for t in tss:
            if t > now - 3700:  # 1시간 뒤 값이 확정된 과거 발표만
                continue
            mv = btc_move(t)
            if mv:
                moves[str(t)] = mv
            time.sleep(0.1)
    save_cache()
    doc = {"built": now, "source": "FRED release calendars (rid %s) and the federalreserve.gov FOMC calendar" % sorted(FRED_RELEASES.values()),
           "kinds": kinds, "moves": moves}
    util.write_json(os.path.join(STATIC, "events_history.json"), doc)
    util.log("saved events", {k: len(v) for k, v in kinds.items()}, "moves", len(moves))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what == "listings":
        backfill_listings()
    elif what == "events":
        backfill_events()
    else:
        print(__doc__)
        sys.exit(2)
