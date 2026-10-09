"""업비트 상장 레이더 데이터.

공지 제목에서 종류·티커·마켓을 읽고, 원화(KRW) 마켓 상장마다 두 가지 가격 곡선을 만든다.
- 공지 직후: 공지 시각 기준 바이낸스 USDT 가격(공지 직전 1분 종가 = 0%), −30분 ~ +4시간
- 거래 개시 후: 업비트 원화 첫 1분봉 시가 = 0%, 0 ~ +24시간
과거분은 pipeline/static/listings_history.json(백필)에 있고, 새 공지는 매 실행에서 덧붙인다.
"""

import re
import time

from . import config, market, util

KINDS_LISTING = ("디지털 자산 추가", "신규 거래지원", "코인 추가", "신규 상장", "마켓 오픈", "거래 지원 예정")
MARKETS = {"KRW", "BTC", "USDT"}
# 법정화폐에 묶인 코인. 상장 직후 첫 체결이 튀어도 투기적 상장과 성격이 달라 해부도 집계에서 뺀다
STABLES = {"USDT", "USDC", "USDE", "PYUSD", "EURC", "JPYC", "USD1", "DAI", "FDUSD", "RLUSD", "USDS", "TUSD", "USDP", "BUSD", "GUSD", "USDG", "EURT", "XAUT", "PAXG"}

# 곡선 표본 지점(분). 앞쪽은 촘촘하게, 뒤로 갈수록 성기게
NOTICE_MINUTES = list(range(-30, 61)) + list(range(65, 241, 5))
TRADE_MINUTES = list(range(0, 61)) + list(range(65, 241, 5)) + list(range(270, 1441, 30))


def notice_kind(title):
    if "유의" in title:
        return "caution" if ("유의 종목" in title or "유의종목" in title) else "other"
    if "거래지원 종료" in title or "거래 지원 종료" in title:
        return "delisting"
    if any(k in title for k in KINDS_LISTING):
        return "listing"
    return "other"


def is_krw(title):
    return "KRW" in title or "원화" in title


def symbols(title):
    """제목에서 티커를 뽑는다. '(KRW, BTC 마켓)' 같은 마켓 괄호는 건너뛴다."""
    out = []
    for g in re.findall(r"\(([^()]*)\)", title):
        if "마켓" in g:
            continue
        for part in g.split(","):
            for w in part.split():
                if re.fullmatch(r"[A-Z0-9]{1,15}", w) and w not in MARKETS:
                    out.append(w)
    out += [w for w in re.findall(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{0,14})\(", title) if w not in MARKETS]
    seen = []
    for s in out:
        if s not in seen:
            seen.append(s)
    return seen


def parse_notice(n):
    title = n.get("title") or ""
    ts = util.parse_time(n.get("first_listed_at") or n.get("listed_at"))
    return {"uid": str(n.get("id")), "ts": ts, "title": title, "kind": notice_kind(title), "krw": is_krw(title),
            "symbols": symbols(title), "url": "https://upbit.com/service_center/notice?id=%s" % n.get("id")}


_TRADE_AT = re.compile(r"(\d{1,2})월\s*(\d{1,2})일\s*(\d{1,2})시(?:\s*(\d{1,2})분)?")


def trade_time_from_body(body, notice_ts):
    """본문의 '거래지원 개시 시점 … 10월 9일 18시 30분 예정'을 읽는다. 없으면 None."""
    text = re.sub(r"<[^>]+>", " ", body or "")
    text = re.sub(r"\s+", " ", text)
    i = text.find("개시")
    if i < 0:
        return None
    m = _TRADE_AT.search(text, i)
    if not m:
        return None
    year = util.kst(notice_ts).year
    mo, d, hh, mm = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4) or 0)
    try:
        ts = util.kst_to_ts(year, mo, d, hh, mm)
    except ValueError:
        return None
    if ts < notice_ts - 3600:  # 연말에 다음 해로 넘어가는 경우
        try:
            ts = util.kst_to_ts(year + 1, mo, d, hh, mm)
        except ValueError:
            return None
    return ts if ts - notice_ts < 7 * 86400 else None


# ---------- 시세 ----------

def _upbit_default(suffix):
    return util.http_json(config.UPBIT_CANDLES_BASE + suffix, retries=1)


def upbit_minutes(market_code, start, end, fetch=None):
    """업비트 원화 1분봉 {분 시작 ts: (시가, 종가)}. start~end 구간을 뒤에서부터 200개씩 받는다."""
    fetch = fetch or _upbit_default
    out = {}
    to = end
    for _ in range(40):
        rows = fetch("minutes/1?market=%s&count=200&to=%s" % (market_code, util.iso(to)))
        if not rows:
            break
        oldest = None
        for r in rows:
            t = util.parse_time(r["candle_date_time_utc"] + "Z")
            if t is None:
                continue
            if start <= t < end:
                out[t] = (float(r["opening_price"]), float(r["trade_price"]))
            oldest = t if oldest is None else min(oldest, t)
        if oldest is None or oldest <= start or len(rows) < 200:
            break
        to = oldest
        time.sleep(0.17)
    return out


def first_trade_day(market_code, notice_ts, fetch=None):
    """공지일 이후 처음 거래가 있었던 날(UTC 0시). 거래 개시가 며칠 미뤄진 경우도 찾는다."""
    fetch = fetch or _upbit_default
    rows = fetch("days?market=%s&count=14&to=%s" % (market_code, util.iso(notice_ts + 12 * 86400)))
    notice_day = notice_ts - notice_ts % 86400
    days = sorted(t for t in (util.parse_time(r["candle_date_time_utc"] + "Z") for r in rows or []) if t is not None and t >= notice_day)
    return days[0] if days else None


def binance_minutes(sym, start, end):
    rows = market.candles(sym, 60, start, end) if sym in config.ASSETS else _binance_raw(sym, start, end)
    return {t: (o, c) for t, o, c in rows}


def _binance_raw(sym, start, end):
    out = []
    t = start
    while t < end:
        try:
            rows = market._binance("/api/v3/klines?symbol=%sUSDT&interval=1m&startTime=%d&endTime=%d&limit=1000" % (sym, t * 1000, end * 1000))
        except util.FetchError:
            return []
        if not rows:
            break
        out += [(int(r[0]) // 1000, float(r[1]), float(r[4])) for r in rows]
        t = int(rows[-1][0]) // 1000 + 60
        if len(rows) < 1000:
            break
    return out


def _curve(minutes, origin, base, offsets):
    """origin 기준 분 오프셋마다 그 분까지의 마지막 종가로 % 변화. 거래가 없던 분은 직전 값을 이어 쓴다."""
    if not minutes or not base:
        return None
    keys = sorted(minutes)
    pts, j, last = [], 0, None
    for off in offsets:
        t = origin + off * 60
        if t > keys[-1] + 60:  # 아직 오지 않은 시각(진행 중 상장)은 비운다
            break
        while j < len(keys) and keys[j] <= t:
            last = minutes[keys[j]][1]
            j += 1
        if last is None:
            continue
        pts.append([off, round((last / base - 1) * 100, 3)])
    return pts or None


def notice_curve(sym, notice_ts):
    """공지 직후 바이낸스 곡선. 공지 당시 바이낸스에 없던 코인이면 None."""
    t0 = notice_ts - notice_ts % 60
    mins = binance_minutes(sym, t0 - 31 * 60, t0 + 241 * 60)
    before = [t for t in mins if t <= t0 - 60]
    if not before or min(mins) > t0 - 25 * 60:
        return None
    base = mins[max(before)][1]
    return {"base": base, "pts": _curve(mins, t0, base, NOTICE_MINUTES)}


def trade_curve(sym, notice_ts, body_trade_ts, fetch=None):
    """거래 개시 후 업비트 원화 곡선과 개시 시각. 시세가 없으면 (None, None, 사유).
    첫 거래일을 일봉으로 찾고, 그날부터 이틀치 1분봉에서 첫 거래 분을 잡는다(개시가 미뤄져도 24시간을 다 담는다)."""
    m = "KRW-" + sym
    try:
        day = first_trade_day(m, notice_ts, fetch)
        if day is None:
            return None, None, "시세 없음"
        mins = upbit_minutes(m, max(notice_ts - 120, day), day + 2 * 86400, fetch)
    except util.FetchError as e:
        return None, None, "시세 없음" if "HTTP 404" in str(e) else "시세 받기 실패"
    if not mins:
        return None, None, "시세 없음"
    first = min(mins)
    trade_ts, src = first, "candle"
    if body_trade_ts and abs(first - body_trade_ts) <= 1800:
        trade_ts, src = body_trade_ts - body_trade_ts % 60, "notice"
        if trade_ts not in mins:
            later = [t for t in mins if t >= trade_ts]
            trade_ts = min(later) if later else first
    base = mins[trade_ts][0]
    if trade_ts + 23 * 3600 > max(mins) and time.time() - trade_ts > 25 * 3600:
        return None, None, "시세 일부 없음"
    return {"base": base, "pts": _curve(mins, trade_ts, base, TRADE_MINUTES), "src": src}, trade_ts, None


def metrics(entry):
    """요약 지표 하나치. 곡선이 없으면 해당 값은 None."""
    m = {}
    nc = (entry.get("notice") or {}).get("pts")
    if nc:
        after = [v for off, v in nc if 0 <= off <= 60]
        m["notice_peak60"] = max(after) if after else None
    tc = (entry.get("trade") or {}).get("pts")
    if tc:
        vals = {off: v for off, v in tc}
        day = [(off, v) for off, v in tc if off <= 1440]
        peak_off, peak = max(day, key=lambda x: x[1])
        m.update({"peak24": peak, "peak_min": peak_off, "r60": vals.get(60), "r1440": vals.get(1440)})
        if vals.get(1440) is not None:
            m["dd_from_peak"] = round(((1 + vals[1440] / 100) / (1 + peak / 100) - 1) * 100, 3)
    return m


# ---------- 매 실행 ----------

import os  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(HERE, "static", "listings_history.json")


def _proxy_base():
    p = config.UPBIT_NOTICES_PROXY
    return p[: -len("/upbit-notices")] if p.endswith("/upbit-notices") else ""


def _body(uid):
    try:
        d = util.http_json(config.UPBIT_NOTICE_DETAIL % uid, retries=1)
    except util.FetchError:
        base = _proxy_base()
        if not base:
            raise
        d = util.http_json("%s/upbit-notice/%s" % (base, uid), retries=1)
    return (d.get("data") or {}).get("body") or ""


def _upbit_fetch(suffix):
    """업비트 시세 API는 GitHub에서도 열리지만, 막히면 1분봉만 스케줄러를 거쳐 받는다."""
    try:
        return util.http_json(config.UPBIT_CANDLES_BASE + suffix, retries=1)
    except util.FetchError as e:
        base = _proxy_base()
        if not base or "HTTP 404" in str(e) or not suffix.startswith("minutes/1?"):
            raise
        return util.http_json("%s/upbit-candles?%s" % (base, suffix.split("?", 1)[1]), retries=1)


def _refresh(e, now):
    """새 상장 하나의 곡선을 (다시) 계산한다. 공지 후 4시간·거래 개시 후 24시간이 지나면 확정."""
    if not e.get("notice_done"):
        nc = notice_curve(e["sym"], e["notice_ts"])
        e["notice"] = nc
        e["notice_done"] = now > e["notice_ts"] + 245 * 60 or nc is None and now > e["notice_ts"] + 3600
    if not e.get("trade_done"):
        if e.get("body_ts") is None and not e.get("body_tried"):
            try:
                e["body_ts"] = trade_time_from_body(_body(e["uid"]), e["notice_ts"])
            except util.FetchError as err:
                util.log("listing body failed", e["uid"], err)
            e["body_tried"] = True
        tc, trade_ts, why = trade_curve(e["sym"], e["notice_ts"], e.get("body_ts"), fetch=_upbit_fetch)
        e["trade"], e["trade_ts"] = tc, trade_ts
        if why:
            e["excluded"] = why
        else:
            e.pop("excluded", None)
        e["trade_done"] = bool(trade_ts and now > trade_ts + 24 * 3600 + 300) or (not tc and now > e["notice_ts"] + 3 * 86400)
    e["live"] = bool(e.get("trade_ts") and now < e["trade_ts"] + 24 * 3600) or (not e.get("trade_ts") and now < e["notice_ts"] + 6 * 3600)


def build(state, recent, now):
    """recent = 이번 실행에서 받은 공지(parse_notice 형식). 정적 백필에 새 공지를 더한 상장 레이더 데이터."""
    hist = util.read_json(HISTORY, {"notices": [], "listings": [], "built": 0})
    live = state.setdefault("listings_live", {})
    # 백필 때 아직 끝나지 않았던 상장(거래 개시 전이거나 24시간이 안 된 것)은 매 실행에서 마저 잰다
    built = hist.get("built") or 0
    unfinished = [r for r in hist["listings"] if now - r["notice_ts"] < 7 * 86400 and (not r.get("trade") or (r.get("trade_ts") or 0) + 86400 > built)]
    for r in unfinished:
        live.setdefault("%s-%s" % (r["sym"], r["uid"]), {k: r[k] for k in ("sym", "uid", "title", "notice_ts", "mode")})
    hist["listings"] = [r for r in hist["listings"] if r not in unfinished]
    known_uids = {n["uid"] for n in hist["notices"]}
    known_listing = {r["uid"] for r in hist["listings"]} | {e["uid"] for e in live.values()}
    hist_syms = {r["sym"]: r["notice_ts"] for r in hist["listings"]}
    for n in sorted(recent, key=lambda x: x["ts"] or 0):
        if n["kind"] != "listing" or not n["krw"] or n["uid"] in known_listing:
            continue
        for sym in n["symbols"]:
            key = "%s-%s" % (sym, n["uid"])
            same = [k for k, v in live.items() if v["sym"] == sym and abs(v["notice_ts"] - n["ts"]) < 10 * 86400]
            if key in live or same or (sym in hist_syms and abs(hist_syms[sym] - n["ts"]) < 10 * 86400):
                continue
            first = min([t for t in [hist_syms.get(sym)] if t] + [n["ts"]])
            live[key] = {"sym": sym, "uid": n["uid"], "title": n["title"], "notice_ts": n["ts"], "mode": "added" if first < n["ts"] - 86400 else "new"}
    for key, e in list(live.items()):
        if now - e["notice_ts"] > 400 * 86400:
            live.pop(key)
            continue
        if not (e.get("notice_done") and e.get("trade_done")):
            try:
                _refresh(e, now)
            except Exception as err:  # 한 코인 실패가 전체를 멈추지 않게
                util.log("listing refresh failed", key, err)
    rows = hist["listings"] + [{k: v for k, v in e.items() if k not in ("notice_done", "trade_done", "body_tried")} for e in live.values()]
    out = []
    for r in rows:
        x = {"sym": r["sym"], "uid": r["uid"], "title": r["title"], "notice_ts": r["notice_ts"], "trade_ts": r.get("trade_ts"),
             "mode": r.get("mode"), "binance": bool(r.get("notice")), "m": metrics(r)}
        if r["sym"] in STABLES:
            x["stable"] = 1
        if r.get("notice"):
            x["nc"] = r["notice"]["pts"]
        if r.get("trade"):
            x["tc"] = r["trade"]["pts"]
            x["tsrc"] = r["trade"].get("src")
            if r.get("live"):
                x["tbase"] = r["trade"]["base"]  # 진행 중 상장: 브라우저가 실시간 곡선을 이어 그릴 기준가
        if r.get("excluded"):
            x["excluded"] = r["excluded"]
        if r.get("live"):
            x["live"] = 1
        out.append(x)
    out.sort(key=lambda x: -x["notice_ts"])
    notices = {n["uid"]: n for n in hist["notices"]}
    for n in recent:
        if n["uid"] not in known_uids and n["kind"] in ("listing", "caution", "delisting"):
            notices[n["uid"]] = {k: n[k] for k in ("uid", "ts", "title", "kind", "krw", "symbols")}
    nl = sorted(notices.values(), key=lambda n: -n["ts"])
    return {"at": now, "listings": out, "notices": nl,
            "counts": {"krw_listings": len(out), "with_trade": sum(1 for x in out if x.get("tc")), "with_notice": sum(1 for x in out if x.get("nc")),
                       "stable": sum(1 for x in out if x.get("stable")),
                       "excluded": sum(1 for x in out if x.get("excluded")), "no_ticker_titles": len(hist.get("unparsed_krw_titles", []))},
            "note": "과거 상장의 가격 변화이며, 앞으로도 같다는 뜻은 아닙니다. 거래가 끝나 시세가 없는 코인은 빠져 있어 실제보다 좋게 보일 수 있습니다."}
