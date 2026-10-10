"""파이프라인 한 번 실행: 수집 → 요약 → 시세 → 일정 → 임팩트 → 알림 → 빌드.

사용: python -m pipeline.run --prev <이전 배포 폴더> --out <새 배포 폴더>
이전 배포의 data/ 를 상태로 읽고, 새 폴더에 사이트 전체를 쓴다.
어느 단계가 실패해도 나머지는 계속하고, 실패한 데이터는 이전 값을 '지연'으로 표시해 쓴다.
"""

import argparse
import os
import shutil
import sys

from . import build, classify, collect, config, events as event_risk, impact, listings, mapdata, market, moves, notify, og, patterns, summarize, util


def load(prev):
    d = os.path.join(prev, "data") if prev else ""
    articles = util.read_json(os.path.join(d, "articles.json"), []) if prev else []
    state = util.read_json(os.path.join(d, "state.json"), {}) if prev else {}
    old_market = util.read_json(os.path.join(d, "market.json"), {}) if prev else {}
    if not isinstance(articles, list):
        articles = []
    # 분류 규칙이 바뀌어 지금은 거를 제목이 상태에 남아 있으면 정리한다
    articles = [a for a in articles if not any(a.get("title_orig", a.get("title", "")).startswith(p) for p in config.TITLE_BLOCK_PREFIX)]
    return articles, state, old_market


def notice_articles(notices, state, existing_ids, now):
    seen = state.setdefault("notices_seen", {})
    out, alerts = [], []
    kind_ko = {"listing": "신규 상장", "caution": "유의 종목 지정", "delisting": "거래 지원 종료"}
    for n in notices:
        if n["uid"] in seen or now - n["ts"] > config.INGEST_MAX_AGE_HOURS * 3600:
            seen.setdefault(n["uid"], now)
            continue
        seen[n["uid"]] = now
        aid = util.kst(n["ts"]).strftime("%Y%m%d") + "-up" + n["uid"]
        if aid in existing_ids:
            continue
        etype = "listing"
        art = {
            "id": aid, "source": "upbit-notice", "source_name": "업비트 공지", "lang": "ko", "url": n["url"],
            "url_key": n["url"], "title": n["title"], "title_orig": n["title"], "excerpt": "", "summary": [], "summary_by": None,
            "category": "crypto", "assets": n["symbols"], "importance": 3, "etype": etype,
            "tags": n["symbols"] + [kind_ko[n["kind"]]], "t0": n["ts"], "t0_estimated": False, "collected": now, "impact": {},
        }
        out.append(art)
        if now - n["ts"] < 2 * 3600:
            alerts.append({"key": "notice-" + n["uid"], "urgent": True, "once": True,
                           "text": "<b>[업비트 %s]</b> %s\n%s" % (kind_ko[n["kind"]], notify.esc(n["title"]), n["url"])})
    # 오래된 기록 정리
    state["notices_seen"] = {k: t for k, t in seen.items() if now - t < 14 * 86400}
    return out, alerts


def market_snapshot(old, state, now):
    snap = {"at": now, "stale": []}
    try:
        snap["tickers"] = market.tickers()
        if not snap["tickers"]:
            raise util.FetchError("no tickers")
    except Exception as e:
        util.log("tickers failed", e)
        snap["tickers"] = old.get("tickers") or {}
        snap["stale"].append("tickers")
    try:
        snap["fx"] = market.fx_usdkrw()
    except Exception as e:
        util.log("fx failed", e)
        snap["fx"] = old.get("fx")
        snap["stale"].append("fx")
    try:
        snap["fng"] = market.fear_greed()
    except Exception as e:
        util.log("fng failed", e)
        snap["fng"] = old.get("fng")
        snap["stale"].append("fng")
    try:
        if not snap.get("fx") or not snap["tickers"]:
            raise util.FetchError("missing inputs")
        snap["kimp"] = market.kimchi(snap["tickers"], snap["fx"])
    except Exception as e:
        util.log("kimp failed", e)
        snap["kimp"] = old.get("kimp") or {}
        snap["stale"].append("kimp")
    alerts = []
    k = (snap.get("kimp") or {}).get("BTC")
    if k and "kimp" not in snap["stale"]:
        hist = [p for p in state.get("kimp_hist", []) if now - p[0] < 30 * 3600]
        hist.append([now, round(k["premium"], 3)])
        state["kimp_hist"] = hist
        ago = [p for p in hist if 3300 <= now - p[0] <= 4500]
        if ago and abs(k["premium"] - ago[0][1]) >= config.KIMP_ALERT_DELTA:
            alerts.append({"key": "kimp-%d" % (now // 3600), "urgent": True,
                           "text": "<b>[김치 프리미엄 급변]</b> BTC %.2f%% → %.2f%% (1시간)" % (ago[0][1], k["premium"])})
    return snap, alerts


def calendar_with_reactions(state, now):
    cached = state.get("calendar_cache") or []
    if cached and now - state.get("calendar_at", 0) < 3600:
        # 일정 소스는 잦은 호출을 막으므로 한 시간에 한 번만 받는다
        events = cached
    else:
        try:
            events = market.calendar(now)
            state["calendar_cache"], state["calendar_at"] = events, now
        except Exception as e:
            util.log("calendar failed", e)
            events = cached
            state["calendar_at"] = now - 2700  # 15분 뒤 다시 시도
    db = state.setdefault("events_db", {})
    for e in events:
        if e["level"] >= 2 and e["ts"] <= now:
            db.setdefault(e["id"], {"id": e["id"], "title": e["title"], "t0": e["ts"], "category": "macro", "source": "calendar",
                                    "assets": [], "importance": 3, "etype": classify.event_type(e["title"].lower(), "", "macro"), "impact": {}})
    state["events_db"] = {k: v for k, v in db.items() if now - v["t0"] < 60 * 86400}
    return events


def attach_reactions(events, state):
    db = state.get("events_db", {})
    for e in events:
        rec = db.get(e["id"])
        if not rec:
            continue
        btc = rec.get("impact", {}).get("BTC", {})
        e["reaction"] = {w: v["r"] for w, v in btc.items() if w in ("15m", "1h") and v.get("r") is not None}


def strong_alerts(articles, now):
    out = []
    for a in articles:
        hd = a.get("headline")
        if hd and hd.get("g") == "강" and now - a["t0"] < 3 * 3600 and not a.get("alerted"):
            a["alerted"] = True
            out.append({"key": "strong-" + a["id"], "urgent": True, "once": True,
                        "text": "<b>[강한 반응]</b> %s\n%s %s %+.2f%%\n%s%sa/%s/" % (notify.esc(a["title"]), hd["asset"], hd["win"], hd["r"],
                                                                              config.SITE_URL, "/", a["id"])})
    return out


def brief_alert(state, strongest_24h, now, out):
    t = util.kst(now)
    day = t.strftime("%Y-%m-%d")
    if not (7 <= t.hour < 10) or state.get("brief_day") == day or not strongest_24h:
        return [], None
    state["brief_day"] = day
    lines = ["<b>오늘의 시그널 · %s</b>" % t.strftime("%m.%d")]
    for i, r in enumerate(strongest_24h[:5]):
        lines.append('%d. <a href="%s/a/%s/">%s</a> (%s %+.2f%%)' % (i + 1, config.SITE_URL, r["id"], notify.esc(r["title"]), r["asset"], r["r"]))
    lines.append("가격 반응은 같은 시간대 변화를 잰 값이며 인과를 뜻하지 않습니다.")
    return [{"key": "brief-" + day, "urgent": False, "once": True, "text": "\n".join(lines)}], t.strftime("%m.%d")


def prune(articles, now):
    keep = [a for a in articles if now - a["t0"] <= config.KEEP_DAYS * 86400]
    keep.sort(key=lambda a: -a["t0"])
    return keep[: config.MAX_ARTICLES]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args(argv)
    now = util.now_ts()
    articles, state, old_market = load(args.prev)
    health = state.setdefault("health", {})
    util.log("loaded", len(articles), "articles")

    fresh = collect.collect(articles, health, now)
    util.log("collected", len(fresh))
    alerts = []
    recent_notices = []
    try:
        recent_notices = market.upbit_notices()
        notes, n_alerts = notice_articles(recent_notices, state, {a["id"] for a in articles}, now)
        fresh += notes
        alerts += n_alerts
        health["upbit-notice"] = {"name": "업비트 공지", "ok": now, "error": None, "added": len(notes)}
    except Exception as e:
        util.log("upbit notices failed", e)
        health["upbit-notice"] = {"name": "업비트 공지", "ok": None, "error": str(e)[:200], "failed_at": now}
    articles = prune(fresh + articles, now)

    summarize.summarize(articles)

    snap, k_alerts = market_snapshot(old_market, state, now)
    alerts += k_alerts

    events = calendar_with_reactions(state, now)

    vol = state.setdefault("vol_cache", {})
    # 측정 방식이 바뀐 기사는 반응을 처음부터 다시 잰다(관련 기사만, 코인 기사는 시장 대비)
    for a in articles:
        if a.get("impact_v") != impact.IMPACT_VERSION:
            if a.get("source") != "upbit-notice":
                a["assets"] = classify.extract_assets(a.get("title_orig") or a["title"], a.get("excerpt") or "")
            a.update({"impact": {}, "impact_status": "measuring", "impact_tries": 0, "headline": None, "impact_v": impact.IMPACT_VERSION})
            a.pop("pattern", None)
            a["og_has_impact"] = False
    prev_moves = util.read_json(os.path.join(args.prev, "data", "moves.json"), None) if args.prev else None
    caps = {c["s"]: c.get("cap") for c in (prev_moves or {}).get("coins", [])}
    impact.measure(articles, vol, now, caps)
    impact.measure(list(state.get("events_db", {}).values()), vol, now)
    attach_reactions(events, state)
    for e in events:
        e["title_ko"] = build.cal_ko(e["title"])
    impact.concurrency(articles)

    stat_pool = articles + list(state.get("events_db", {}).values())
    imp = {"at": now, "types": impact.type_stats(stat_pool), "strongest": impact.strongest(articles, now)}
    strongest_24h = impact.strongest(articles, now, days=1, limit=5)

    # 새 화면 데이터(맵·상장 레이더·이벤트 리스크·패턴). 하나가 실패하면 지난 파일을 그대로 쓴다
    prev_data = os.path.join(args.prev, "data") if args.prev else ""
    def prev_json(name):
        return util.read_json(os.path.join(prev_data, name), None) if prev_data else None
    extra = {}
    base = {}
    try:
        patterns.attach_similar(articles, now)
    except Exception as e:
        util.log("similar patterns failed", e)
    try:
        extra["map.json"], base = mapdata.build(articles, snap, now, prev_json("map.json"))
    except Exception as e:
        util.log("map build failed", e)
        extra["map.json"] = prev_json("map.json")
    try:
        extra["moves.json"] = moves.build(articles, now, prev_json("moves.json"))
    except Exception as e:
        util.log("moves build failed", e)
        extra["moves.json"] = prev_json("moves.json")
    try:
        extra["listings.json"] = listings.build(state, recent_notices, now)
    except Exception as e:
        util.log("listings build failed", e)
        extra["listings.json"] = prev_json("listings.json")
    try:
        extra["events.json"] = event_risk.build(state, events, now)
    except Exception as e:
        util.log("events build failed", e)
        extra["events.json"] = prev_json("events.json")
    try:
        if not base and extra.get("map.json"):
            base = {x["s"]: x["base1h"] for x in extra["map.json"].get("assets", []) if x.get("base1h")}
        base_res = {c["s"]: round(c["sig60"] * 0.6745, 4) for c in (extra.get("moves.json") or {}).get("coins", []) if c.get("sig60")}
        extra["patterns.json"] = patterns.build(articles, base, imp, now, base_res)
    except Exception as e:
        util.log("patterns build failed", e)
        extra["patterns.json"] = prev_json("patterns.json")

    alerts += strong_alerts(articles, now)
    b_alerts, brief_label = brief_alert(state, strongest_24h, now, args.out)
    alerts += b_alerts

    out = args.out
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    # 이미 만든 공유 카드는 살아 있는 기사 것만 옮긴다
    keep_ids = {a["id"] for a in articles}
    prev_og = os.path.join(args.prev, "og") if args.prev else ""
    if prev_og and os.path.isdir(prev_og):
        os.makedirs(os.path.join(out, "og"), exist_ok=True)
        for f in os.listdir(prev_og):
            if f in ("default.jpg", "brief.jpg") or f[:-4] in keep_ids:
                shutil.copy2(os.path.join(prev_og, f), os.path.join(out, "og", f))
    if not args.no_images:
        cam = og.Camera()
        try:
            og.render(cam, out, articles)
            if brief_label:
                og.render_brief(cam, out, brief_label, strongest_24h)
        finally:
            cam.close()
    build.OG_DEFAULT = os.path.isfile(os.path.join(out, "og", "default.jpg"))
    for a in articles:
        if a.get("og") and not os.path.isfile(os.path.join(out, "og", a["id"] + ".jpg")):
            a["og"] = False

    sent = notify.dispatch(alerts, state, now)
    util.log("alerts", len(alerts), "sent", sent)

    state["last_run"] = now
    data = os.path.join(out, "data")
    util.write_json(os.path.join(data, "articles.json"), articles)
    util.write_json(os.path.join(data, "state.json"), state)
    util.write_json(os.path.join(data, "market.json"), snap)
    util.write_json(os.path.join(data, "calendar.json"), {"at": now, "events": events})
    util.write_json(os.path.join(data, "impact.json"), imp)
    for name, doc in extra.items():
        if doc is not None:
            util.write_json(os.path.join(data, name), doc)
    build.build_site(out, articles, snap, events, imp, health, now, extra)
    util.log("built", len(articles), "articles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
