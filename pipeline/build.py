"""정적 페이지 생성. 서버 없이 GitHub Pages에서 그대로 열리는 HTML을 만든다."""

import html
import json
import os
import shutil

from . import config, util
from .impact import assets_for

OG_DEFAULT = False
HAS_BRIEF = False
ASSET_VER = "0"

B = config.SITE_BASE
WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

NAV = [("feed", "feed/", "피드"), ("markets", "markets/", "마켓"), ("calendar", "calendar/", "캘린더"),
       ("impact", "impact/", "임팩트"), ("predict", "predict/", "예측"), ("me", "me/", "마이")]
TABBAR = ["feed", "markets", "calendar", "predict", "me"]

CAL_KO = {
    "CPI m/m": "소비자물가지수(전월비)", "CPI y/y": "소비자물가지수(전년비)", "Core CPI m/m": "근원 소비자물가(전월비)",
    "Core CPI y/y": "근원 소비자물가(전년비)", "PPI m/m": "생산자물가지수(전월비)", "Core PPI m/m": "근원 생산자물가(전월비)",
    "Non-Farm Employment Change": "비농업 고용 변화", "Unemployment Rate": "실업률", "Unemployment Claims": "신규 실업수당 청구",
    "Average Hourly Earnings m/m": "평균 시간당 임금(전월비)", "Federal Funds Rate": "기준금리 결정", "FOMC Statement": "FOMC 성명",
    "FOMC Meeting Minutes": "FOMC 의사록", "FOMC Press Conference": "FOMC 기자회견", "Fed Chair Powell Speaks": "연준 의장 연설",
    "Retail Sales m/m": "소매판매(전월비)", "Core Retail Sales m/m": "근원 소매판매(전월비)", "Advance GDP q/q": "GDP 속보치(전분기비)",
    "Prelim GDP q/q": "GDP 잠정치(전분기비)", "Final GDP q/q": "GDP 확정치(전분기비)", "Core PCE Price Index m/m": "근원 PCE 물가(전월비)",
    "ISM Manufacturing PMI": "ISM 제조업 PMI", "ISM Services PMI": "ISM 서비스업 PMI", "JOLTS Job Openings": "JOLTS 구인건수",
    "ADP Non-Farm Employment Change": "ADP 민간고용 변화", "Prelim UoM Consumer Sentiment": "미시간대 소비자심리(예비)",
    "Revised UoM Consumer Sentiment": "미시간대 소비자심리(확정)", "CB Consumer Confidence": "콘퍼런스보드 소비자신뢰",
    "Empire State Manufacturing Index": "뉴욕 제조업지수", "Philly Fed Manufacturing Index": "필라델피아 제조업지수",
    "Crude Oil Inventories": "원유 재고", "Trade Balance": "무역수지", "Building Permits": "건축허가",
    "Prelim UoM Inflation Expectations": "미시간대 기대인플레이션(예비)", "Interest Rate Decision": "기준금리 결정",
}

_SPEAKS = __import__("re").compile(r"^(?:FOMC Member )?(.+?) Speaks$")


def cal_ko(title):
    """경제 일정 이름을 한국어로. 사전에 없으면 '연설' 패턴을 처리하고, 그래도 없으면 원문."""
    if title in CAL_KO:
        return CAL_KO[title]
    m = _SPEAKS.match(title)
    if not m:
        return title
    names = {"Trump": "트럼프", "Powell": "파월", "Waller": "월러", "Lagarde": "라가르드", "Bessent": "베선트", "Bowman": "보먼",
             "Jefferson": "제퍼슨", "Williams": "윌리엄스", "Barr": "바", "Cook": "쿡", "Goolsbee": "굴스비", "Kashkari": "카시카리"}
    who = m.group(1)
    for role, ko in (("President ", "대통령"), ("Fed Chair ", "연준 의장"), ("Fed Vice Chair ", "연준 부의장")):
        if who.startswith(role):
            name = who[len(role):]
            return "%s %s 연설" % (names.get(name, name), ko) if role == "President " else "%s %s 연설" % (ko, names.get(name, name))
    if title.startswith("FOMC Member"):
        return "FOMC 위원 %s 연설" % names.get(who, who)
    return "%s 연설" % names.get(who, who)


ICON = {
    "search": '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="m13.2 13.2 3.3 3.3"/></svg>',
    "sun": '<svg class="i-sun" viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="3.5"/><path d="M10 2.5v1.6M10 15.9v1.6M2.5 10h1.6M15.9 10h1.6M4.7 4.7l1.1 1.1M14.2 14.2l1.1 1.1M4.7 15.3l1.1-1.1M14.2 5.8l1.1-1.1"/></svg>',
    "moon": '<svg class="i-moon" viewBox="0 0 20 20" aria-hidden="true"><path d="M16 12.3A6.5 6.5 0 0 1 7.7 4a6.5 6.5 0 1 0 8.3 8.3Z"/></svg>',
    "out": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8 4H4.5v11.5H16V12M11 4h5v5M16 4l-7 7"/></svg>',
    "share": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 13V3.5M6.5 7 10 3.5 13.5 7M4 11v5.5h12V11"/></svg>',
    "star": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m10 2.8 2.2 4.6 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5L2.8 8.1l5-.7z"/></svg>',
    "up": '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 1.5 9 8.5H1z"/></svg>',
    "down": '<svg viewBox="0 0 10 10" aria-hidden="true"><path d="M5 8.5 1 1.5h8z"/></svg>',
    "home": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 9.5 10 4l7 5.5V16H12v-4H8v4H3z"/></svg>',
    "chart": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 16h14M5 13l3.5-4 3 2.5L16 6"/></svg>',
    "cal": '<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="4.5" width="14" height="12" rx="2"/><path d="M3 8.5h14M7 3v3M13 3v3"/></svg>',
    "vote": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 11h3v5H4zM8.5 7h3v9h-3zM13 4h3v12h-3z"/></svg>',
    "user": '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="7" r="3.2"/><path d="M3.8 16.5c.9-3 3.3-4.6 6.2-4.6s5.3 1.6 6.2 4.6"/></svg>',
}
TAB_ICON = {"feed": "home", "markets": "chart", "calendar": "cal", "predict": "vote", "me": "user"}


def h(text):
    return html.escape("" if text is None else str(text), quote=True)


def hm(ts):
    return util.kst(ts).strftime("%H:%M")


def md_hm(ts):
    return util.kst(ts).strftime("%m.%d %H:%M")


def pct(v, digits=2):
    if v is None:
        return "–"
    return ("+" if v >= 0 else "−") + ("%." + str(digits) + "f") % abs(v) + "%"


def price(p):
    if p is None:
        return "–"
    d = 0 if p >= 10000 else 2 if p >= 10 else 3 if p >= 1 else 4
    return ("{:,.%df}" % d).format(p)


def article_path(a):
    return "%sa/%s/" % (B, a["id"])


# ---------------------------------------------------------------- 공통 셸

def shell(page, title, desc, path, body, now, og=None, robots="index,follow", extra_head="", data=None):
    full_title = title if title.startswith(config.SITE_NAME) else "%s · %s" % (title, config.SITE_NAME)
    url = config.SITE_URL + path[len(B) - 1:] if path.startswith(B) else config.SITE_URL + "/"
    nav = "".join('<a class="nav__link" href="%s%s"%s>%s</a>' % (B, p, ' aria-current="page"' if k == page else "", label) for k, p, label in NAV)
    tabs = "".join('<a class="tab" href="%s%s"%s>%s<span>%s</span></a>' % (B, p, ' aria-current="page"' if k == page else "", ICON[TAB_ICON[k]], label)
                   for k, p, label in NAV if k in TABBAR)
    boot = {"base": B, "page": page}
    if data:
        boot.update(data)
    og_meta = ""
    if og or OG_DEFAULT:
        og_meta = ('<meta property="og:image" content="%s">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
                   '<meta name="twitter:card" content="summary_large_image">') % h(og or config.SITE_URL + "/og/default.jpg")
    return """<!doctype html>
<html lang="ko" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{ogtype}">
<meta property="og:site_name" content="{site}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
{og_meta}
<meta name="theme-color" content="#0d0d10">
<link rel="icon" href="{B}assets/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400..700&family=Geist+Mono:wght@400..600&family=Instrument+Serif&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{B}assets/styles.css?v={ver}">
<script>(function(){{try{{var t=localStorage.getItem('signal-theme');if(t)document.documentElement.dataset.theme=t;}}catch(e){{}}}})();</script>
{extra_head}
</head>
<body class="p-{page}">
<a class="skip-link" href="#main">본문으로 건너뛰기</a>
<div class="ticker" role="region" aria-label="시세">
  <div class="ticker__status" id="feedStatus" data-state="snapshot"><span class="dot" aria-hidden="true"></span><span class="ticker__label">시세</span></div>
  <div class="ticker__viewport"><div class="ticker__track" id="tickerTrack"></div></div>
</div>
<header class="nav" id="nav">
  <div class="nav__inner">
    <a class="brand" href="{B}" aria-label="SIGNAL 홈">
      <svg class="brand__mark" viewBox="0 0 28 28" aria-hidden="true"><rect x="0.5" y="0.5" width="27" height="27" rx="8" fill="currentColor"/><path d="M5 15h4l2.5-6 4 11 2.5-5H23" fill="none" stroke="var(--bg)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span class="brand__word">SIGNAL<span class="brand__slash">/</span></span>
    </a>
    <nav class="nav__links" aria-label="주 메뉴">{nav}</nav>
    <div class="nav__actions">
      <button class="search-btn" id="openSearch" type="button" aria-label="검색 (⌘K)">{search}<span class="search-btn__label">검색</span><kbd>⌘K</kbd></button>
      <button class="icon-btn" id="themeToggle" type="button" aria-label="라이트 모드로 전환">{sun}{moon}</button>
    </div>
  </div>
</header>
<main id="main" class="main">
{body}
</main>
<footer class="footer">
  <div class="wrap footer__inner">
    <div><span class="brand__word">SIGNAL<span class="brand__slash">/</span></span><p class="muted">해외 속보를 한국어로, 그리고 그 뉴스가 실제로 가격을 얼마나 움직였는지까지.</p></div>
    <nav class="footer__nav" aria-label="푸터"><a href="{B}about/">소개·방법론</a><a href="{B}about/#sources">데이터 출처</a><a href="{B}impact/">임팩트 리포트</a><a href="{B}sitemap.xml">사이트맵</a></nav>
    <p class="footer__note">기사 저작권은 각 원문 매체에 있으며 SIGNAL은 제목·요약·원문 링크만 제공합니다. 시세와 반응 수치는 정보 제공용이며 투자 조언이 아닙니다. 가격 반응은 상관을 측정한 값이고 인과를 뜻하지 않습니다.</p>
  </div>
</footer>
<nav class="tabbar" aria-label="하단 메뉴">{tabs}</nav>
<div class="cmdk" id="cmdk" hidden>
  <div class="cmdk__scrim" data-close></div>
  <div class="cmdk__panel" role="dialog" aria-modal="true" aria-label="검색">
    <div class="cmdk__input">{search}<input id="cmdkInput" type="search" placeholder="키워드, 티커, 매체 검색…" autocomplete="off" role="combobox" aria-expanded="true" aria-controls="cmdkList"><kbd>ESC</kbd></div>
    <ul class="cmdk__list" id="cmdkList" role="listbox"></ul>
  </div>
</div>
<ol class="toasts" id="toasts" aria-live="polite"></ol>
<script>window.SIGNAL={boot};</script>
<script src="{B}assets/app.js?v={ver}" defer></script>
</body>
</html>
""".format(title=h(full_title), desc=h(desc), robots=robots, url=h(url), ogtype="article" if page == "article" else "website",
           site=config.SITE_NAME, og_meta=og_meta, B=B, ver=ASSET_VER, extra_head=extra_head, page=page, nav=nav, tabs=tabs,
           search=ICON["search"], sun=ICON["sun"], moon=ICON["moon"], body=body,
           boot=json.dumps(boot, ensure_ascii=False).replace("</", "<\\/"))


# ---------------------------------------------------------------- 카드와 배지

def impact_badge(a):
    hd = a.get("headline")
    st = a.get("impact_status")
    if hd:
        d = "up" if hd["r"] >= 0 else "down"
        grade = hd.get("g")
        gcls = {"강": "s", "중": "m", "약": "w"}.get(grade, "w")
        return ('<span class="ib ib--%s ib--g%s" title="기사 시각부터 %s 동안 %s 가격 변화">%s<b>%s %s</b> %s%s</span>'
                % (d, gcls, "1시간" if hd["win"] == "1h" else "15분", hd["asset"], ICON[d], hd["asset"], hd["win"], pct(hd["r"]),
                   (" · " + grade) if grade else ""))
    if st == "failed":
        return '<span class="ib ib--na">반응 측정 불가</span>'
    return '<span class="ib ib--wait" data-t0="%d">반응 측정 중</span>' % a["t0"]


def chips(a):
    return "".join('<button class="achip" type="button" data-asset="%s" aria-pressed="false" aria-label="%s 관심 종목 추가">%s</button>' % (h(s), h(s), h(s))
                   for s in a.get("assets", [])[:4])


def card(a):
    cat = a["category"]
    lang = '<span class="lang">EN</span>' if a.get("lang") == "en" and a.get("summary_by") != "llm" else ""
    if a.get("summary"):
        body = '<ul class="fcard__sum">%s</ul>' % "".join("<li>%s</li>" % h(s) for s in a["summary"])
    elif a.get("excerpt"):
        body = '<p class="fcard__ex">%s <span class="ex-label">원문 발췌</span></p>' % h(a["excerpt"])
    else:
        body = ""
    imp = '<span class="imp" data-lv="%d" role="img" aria-label="중요도 %d/3"><i></i><i></i><i></i></span>' % (a["importance"], a["importance"])
    return """<article class="fcard" data-id="{id}" data-cat="{cat}" data-assets="{assets}" data-imp="{imp_n}" data-t0="{t0}">
  <div class="fcard__meta"><span class="chip cat cat--{cat}">{catlabel}</span>{imp}<span class="src">{src}</span><time datetime="{iso}" data-ts="{t0}">{hm}</time>{lang}</div>
  <h3 class="fcard__title"><a href="{href}">{title}</a></h3>
  {body}
  <div class="fcard__foot">{badge}<span class="achips">{chips}</span></div>
</article>""".format(id=h(a["id"]), cat=cat, assets=h(",".join(a.get("assets", []))), imp_n=a["importance"], t0=a["t0"],
                     catlabel=config.CATEGORY_LABEL.get(cat, cat), imp=imp, src=h(a["source_name"]), iso=util.iso(a["t0"]),
                     hm=md_hm(a["t0"]), lang=lang, href=article_path(a), title=h(a["title"]), body=body, badge=impact_badge(a), chips=chips(a))


def feed_item(a):
    """클라이언트용 축약 JSON."""
    return {
        "id": a["id"], "t0": a["t0"], "title": a["title"], "src": a["source_name"], "lang": a.get("lang"),
        "cat": a["category"], "assets": a.get("assets", []), "imp": a["importance"], "etype": a.get("etype"),
        "sum": a.get("summary") or [], "ex": a.get("excerpt") or "", "llm": a.get("summary_by") == "llm",
        "h": a.get("headline"), "st": a.get("impact_status") or "measuring", "url": a["url"],
    }


# ---------------------------------------------------------------- 페이지들

def page_feed(articles, market, cal, imp, now):
    top = articles[: config.HOME_RENDER_LIMIT]
    cards = "\n".join(card(a) for a in top) or '<p class="empty">아직 수집된 기사가 없습니다. 첫 수집이 끝나면 여기에 나타납니다.</p>'
    upcoming = [e for e in cal if e["ts"] >= now - 3600][:5]
    cal_html = "".join('<li><time data-ts="%d">%s</time><span class="ev-title">%s</span><span class="lv" data-lv="%d" aria-label="중요도 %s"><i></i><i></i><i></i></span></li>'
                       % (e["ts"], md_hm(e["ts"]), h(cal_ko(e["title"])), e["level"], e["level_ko"]) for e in upcoming) \
        or '<li class="muted">이번 주 남은 주요 일정이 없습니다.</li>'
    strong = "".join('<li><a href="%sa/%s/">%s</a><span class="ib ib--%s ib--g%s">%s %s %s</span></li>'
                     % (B, h(r["id"]), h(r["title"]), "up" if r["r"] >= 0 else "down", {"강": "s", "중": "m"}.get(r["g"], "w"), r["asset"], r["win"], pct(r["r"]))
                     for r in imp.get("strongest", [])[:5]) or '<li class="muted">측정이 쌓이면 표시됩니다.</li>'
    body = """
<div class="wrap layout3">
  <aside class="filters" aria-label="피드 필터">
    <div class="fgroup" role="radiogroup" aria-label="카테고리" id="catFilter">
      <button class="fbtn" type="button" role="radio" aria-checked="true" data-cat="all">전체</button>
      <button class="fbtn" type="button" role="radio" aria-checked="false" data-cat="crypto"><i class="dot dot--crypto"></i>크립토</button>
      <button class="fbtn" type="button" role="radio" aria-checked="false" data-cat="ai"><i class="dot dot--ai"></i>AI</button>
      <button class="fbtn" type="button" role="radio" aria-checked="false" data-cat="macro"><i class="dot dot--macro"></i>매크로</button>
    </div>
    <div class="fgroup fgroup--opts">
      <label class="switch"><input type="checkbox" id="optMajor"><span>주요 기사만</span></label>
      <label class="switch"><input type="checkbox" id="optStrong"><span>반응 강·중만</span></label>
      <label class="switch"><input type="checkbox" id="optWatch"><span>내 종목만</span></label>
      <label class="switch"><input type="checkbox" id="optKo"><span>한국어 기사만</span></label>
    </div>
  </aside>
  <section class="feed" aria-labelledby="feedTitle">
    <div class="feed__head">
      <h1 id="feedTitle" class="feed__title">실시간 시그널</h1>
      <p class="muted feed__upd">마지막 수집 <time data-ts="{now}">{now_hm}</time> · 15분마다 갱신</p>
    </div>
    <button class="new-pill" id="newPill" type="button" hidden></button>
    <div class="feed__list" id="feedList">
{cards}
    </div>
    <button class="btn btn--ghost feed__more" id="loadMore" type="button" hidden>더 보기</button>
  </section>
  <aside class="rail" aria-label="요약 정보">
    <section class="panel"><h2 class="panel__title">시장 온도</h2><div id="tempPanel" class="temp">{temp}</div></section>
    <section class="panel"><h2 class="panel__title">다가오는 일정 <a class="panel__more" href="{B}calendar/">전체</a></h2><ul class="mini-cal">{cal}</ul></section>
    <section class="panel"><h2 class="panel__title">최근 7일 강한 반응 <a class="panel__more" href="{B}impact/">리포트</a></h2><ul class="mini-strong">{strong}</ul></section>
    {brief}
  </aside>
</div>""".format(now=now, now_hm=md_hm(now), cards=cards, cal=cal_html, strong=strong, B=B, temp=temp_panel(market),
           brief=('<section class="panel"><h2 class="panel__title">오늘의 시그널</h2><a class="brief-img" href="%sog/brief.jpg" target="_blank" rel="noopener"><img src="%sog/brief.jpg?v=%d" alt="오늘의 시그널 요약 이미지" width="1080" height="1080" loading="lazy"></a><p class="muted small">이미지를 길게 눌러 저장하거나 공유하세요.</p></section>' % (B, B, now)) if HAS_BRIEF else "")
    return shell("feed", "실시간 시그널 피드",
                 "크립토·AI·매크로 뉴스를 실시간으로 모으고 기사마다 비트코인 가격 반응을 실측해 보여 줍니다.", B + "feed/", body, now)


def temp_panel(market):
    parts = []
    fng = market.get("fng")
    if fng:
        parts.append('<div class="temp__row"><span>공포·탐욕 지수</span><b>%d</b><span class="muted">%s</span></div>' % (fng["value"], h(fng["label"])))
    k = (market.get("kimp") or {}).get("BTC")
    if k:
        parts.append('<div class="temp__row"><span>BTC 김치 프리미엄</span><b>%s</b><span class="muted">업비트 기준</span></div>' % pct(k["premium"]))
    fx = market.get("fx")
    if fx:
        parts.append('<div class="temp__row"><span>원/달러</span><b>%s</b><span class="muted">일 1회 갱신</span></div>' % ("{:,.1f}".format(fx["rate"])))
    return "".join(parts) or '<p class="muted">지표를 불러오지 못했습니다.</p>'


def page_article(a, related, now):
    imp = a.get("impact") or {}
    rows = []
    for sym in assets_for(a):
        cells = []
        for win, secs in config.WINDOWS:
            v = imp.get(sym, {}).get(win)
            if v and v.get("r") is not None:
                g = v.get("g")
                cells.append('<td class="%s"><b>%s</b>%s</td>' % ("up" if v["r"] >= 0 else "down", pct(v["r"]),
                             ('<span class="g g--%s">%s · z %.1f</span>' % ({"강": "s", "중": "m"}.get(g, "w"), g, v["z"])) if g else ""))
            elif v:
                cells.append('<td class="muted">측정 불가</td>')
            else:
                cells.append('<td class="muted" data-wait="%d">측정 중</td>' % (a["t0"] + secs))
        rows.append("<tr><th scope=\"row\">%s</th>%s</tr>" % (h(sym), "".join(cells)))
    conc = a.get("concurrent", 0)
    note = ('<p class="note">같은 시간대(±15분)에 다른 주요 기사 %d건이 있었습니다. 반응이 이 기사 때문만은 아닐 수 있습니다.</p>' % conc) if conc else ""
    est = '<p class="note">원문 발행 시각이 없어 수집 시각을 기준으로 측정했습니다.</p>' if a.get("t0_estimated") else ""
    if a.get("summary"):
        lead = '<ol class="art__sum">%s</ol><p class="muted small">요약: AI가 원문 제목·발췌만으로 작성했습니다. 정확한 내용은 원문을 확인하세요.</p>' % "".join("<li>%s</li>" % h(s) for s in a["summary"])
    elif a.get("excerpt"):
        lead = '<blockquote class="art__ex"><p>%s</p><footer>원문 발췌 · %s</footer></blockquote>' % (h(a["excerpt"]), h(a["source_name"]))
    else:
        lead = '<p class="muted">요약이 아직 없습니다. 원문에서 내용을 확인하세요.</p>'
    orig = '<p class="art__orig" lang="en">%s</p>' % h(a["title_orig"]) if a["title_orig"] != a["title"] else ""
    rel = "".join('<li><a href="%s">%s</a><span class="muted">%s · %s</span></li>' % (article_path(r), h(r["title"]), h(r["source_name"]), md_hm(r["t0"])) for r in related) \
        or '<li class="muted">관련 기사가 없습니다.</li>'
    primary = assets_for(a)[0]
    body = """
<div class="wrap art">
  <nav class="crumbs" aria-label="경로"><a href="{B}feed/">피드</a><span aria-hidden="true">/</span><span>{catlabel}</span></nav>
  <header class="art__head">
    <div class="fcard__meta"><span class="chip cat cat--{cat}">{catlabel}</span><span class="src">{src}</span><time datetime="{iso}" data-ts="{t0}">{when} KST</time></div>
    <h1 class="art__title">{title}</h1>
    {orig}
  </header>
  <section class="art__body">{lead}
    <div class="art__actions">
      <a class="btn btn--accent" href="{url}" target="_blank" rel="noopener nofollow">원문 보기 {out}</a>
      <button class="btn btn--ghost" type="button" data-share>{share}공유</button>
    </div>
  </section>
  <section class="art__impact" aria-labelledby="impTitle">
    <h2 id="impTitle" class="h2">가격 반응 실측</h2>
    <p class="muted small">기사 기준 시각부터의 가격 변화입니다. z는 최근 같은 길이 구간의 평소 변동폭 대비 몇 배인지를 뜻합니다. |z| 3 이상 강, 2 이상 중.</p>
    <div class="table-wrap"><table class="itable"><thead><tr><th scope="col">자산</th><th scope="col">15분</th><th scope="col">1시간</th><th scope="col">24시간</th></tr></thead><tbody>{rows}</tbody></table></div>
    {note}{est}
    <figure class="chart" id="artChart" data-sym="{primary}" data-t0="{t0}">
      <div class="chart__box" role="img" aria-label="{primary} 가격, 기사 시각 전후"></div>
      <figcaption class="muted small">{primary} 1분봉 · 세로선이 기사 기준 시각 · 출처 Binance(실패 시 Coinbase)</figcaption>
    </figure>
    <p class="note">가격 반응은 같은 시간에 일어난 일을 잰 값입니다. 이 기사가 가격을 움직였다는 뜻은 아닙니다.</p>
  </section>
  <section class="art__related"><h2 class="h2">관련 기사</h2><ul class="rel">{rel}</ul></section>
</div>""".format(B=B, cat=a["category"], catlabel=config.CATEGORY_LABEL[a["category"]], src=h(a["source_name"]), iso=util.iso(a["t0"]),
                 t0=a["t0"], when=util.kst(a["t0"]).strftime("%Y.%m.%d %H:%M"), title=h(a["title"]), orig=orig, lead=lead, url=h(a["url"]),
                 out=ICON["out"], share=ICON["share"], rows="".join(rows), note=note, est=est, primary=h(primary), rel=rel)
    desc = (a["summary"][0] if a.get("summary") else a.get("excerpt") or a["title"])[:150]
    og = "%s/og/%s.jpg" % (config.SITE_URL, a["id"]) if a.get("og") else None
    return shell("article", a["title"], desc, article_path(a), body, now, og=og, data={"article": feed_item(a)})


def page_markets(market, now):
    tick = market.get("tickers") or {}
    kimp = market.get("kimp") or {}
    rows = []
    for s in config.MARKET_ASSETS:
        t = tick.get(s)
        if not t:
            continue
        k = kimp.get(s)
        spark = ",".join(str(x) for x in t.get("spark", []))
        rows.append('<tr data-sym="%s"><th scope="row"><span class="sym">%s</span></th><td class="num px">$%s</td><td class="num chg %s">%s</td><td class="num">%s</td><td class="num">%s</td><td class="sparkcell"><svg class="spark" data-points="%s" viewBox="0 0 120 32" preserveAspectRatio="none" aria-hidden="true"></svg></td></tr>'
                    % (s, s, price(t["price"]), "up" if t["chg"] >= 0 else "down", pct(t["chg"]),
                       ("₩" + "{:,.0f}".format(k["krw"])) if k else "–", pct(k["premium"]) if k else "–", spark))
    table = "".join(rows) or '<tr><td colspan="6" class="muted">시세를 불러오지 못했습니다.</td></tr>'
    fng = market.get("fng")
    fx = market.get("fx")
    fng_html = ('<div class="big">%d<span class="muted"> / 100</span></div><p class="muted">%s · alternative.me</p><svg class="spark spark--wide" data-points="%s" viewBox="0 0 240 48" preserveAspectRatio="none" aria-hidden="true"></svg><p class="muted small">최근 30일</p>'
                % (fng["value"], h(fng["label"]), ",".join(str(x) for x in fng["history"]))) if fng else '<p class="muted">불러오지 못했습니다.</p>'
    fx_html = ('<div class="big">%s<span class="muted"> 원</span></div><p class="muted">1달러 기준 · ExchangeRate-API · %s 갱신</p>' % ("{:,.2f}".format(fx["rate"]), md_hm(fx["updated"]))) if fx else '<p class="muted">불러오지 못했습니다.</p>'
    body = """
<div class="wrap">
  <header class="phead"><h1 class="phead__title">마켓</h1><p class="muted">크립토 시세는 브라우저에서 실시간으로 갱신됩니다. 마지막 서버 수집 <time data-ts="{now}">{now_hm}</time></p></header>
  <div class="mgrid">
    <section class="panel mtable-panel"><h2 class="panel__title">크립토 시세</h2>
      <div class="table-wrap"><table class="mtable" id="mtable"><thead><tr><th scope="col">자산</th><th scope="col" class="num">가격(USDT)</th><th scope="col" class="num">24시간</th><th scope="col" class="num">업비트(KRW)</th><th scope="col" class="num">김치 프리미엄</th><th scope="col">24시간 흐름</th></tr></thead><tbody>{rows}</tbody></table></div>
      <p class="muted small">김치 프리미엄 = 업비트 원화 가격 ÷ (해외 USDT 가격 × 원/달러) − 1. 환율이 하루 한 번 갱신돼 실제 체감과 다를 수 있습니다.</p>
    </section>
    <section class="panel"><h2 class="panel__title">공포·탐욕 지수</h2>{fng}</section>
    <section class="panel"><h2 class="panel__title">원/달러 환율</h2>{fx}</section>
    <section class="panel"><h2 class="panel__title">주가 지수</h2><p class="muted">나스닥·S&amp;P 500 지수는 데이터 소스(무료·유료)를 정한 뒤 추가합니다.</p></section>
  </div>
</div>""".format(now=now, now_hm=md_hm(now), rows=table, fng=fng_html, fx=fx_html)
    return shell("markets", "마켓", "크립토 시세, 김치 프리미엄, 공포·탐욕 지수, 원/달러 환율.", B + "markets/", body, now, data={"market": market})


def page_calendar(cal, now):
    days = {}
    for e in cal:
        days.setdefault(util.kst(e["ts"]).strftime("%Y-%m-%d"), []).append(e)
    wd = "월화수목금토일"
    sections = []
    for d, evs in sorted(days.items()):
        dt = util.kst(evs[0]["ts"])
        items = []
        for e in evs:
            past = e["ts"] < now
            react = e.get("reaction") or {}
            if react:
                rtxt = " · ".join('BTC %s <b class="%s">%s</b>' % (w, "up" if v >= 0 else "down", pct(v)) for w, v in react.items())
                rhtml = '<p class="ev__react">발표 후 %s</p>' % rtxt
            elif past and now - e["ts"] < 3 * 3600:
                rhtml = '<p class="ev__react muted">반응 측정 중</p>'
            else:
                rhtml = ""
            vote = ('<div class="vote" data-event="%s" data-ts="%d" data-title="%s"><span class="muted small">발표 1시간 뒤 BTC는?</span><button class="vbtn" type="button" data-choice="up">위</button><button class="vbtn" type="button" data-choice="down">아래</button></div>'
                    % (h(e["id"]), e["ts"], h(cal_ko(e["title"])))) if (not past and e["level"] == 3) else ""
            fc = []
            if e.get("forecast"):
                fc.append("예상 %s" % h(e["forecast"]))
            if e.get("previous"):
                fc.append("이전 %s" % h(e["previous"]))
            items.append("""<li class="ev{past}"><time class="ev__time" data-ts="{ts}">{hm}</time>
  <div class="ev__body"><p class="ev__title"><span class="flag">{country}</span>{title}<span class="lv" data-lv="{lv}" aria-label="중요도 {lvko}"><i></i><i></i><i></i></span></p>
  <p class="ev__orig muted small" lang="en">{orig}{fc}</p>{react}{vote}</div></li>""".format(
                past=" ev--past" if past else "", ts=e["ts"], hm=hm(e["ts"]), country="미국" if e["country"] == "USD" else "한국",
                title=h(cal_ko(e["title"])), lv=e["level"], lvko=e["level_ko"], orig=h(e["title"]),
                fc=(" · " + " · ".join(fc)) if fc else "", react=rhtml, vote=vote))
        sections.append('<section class="day"><h2 class="day__title">%s <span class="muted">%s요일</span></h2><ol class="evs">%s</ol></section>'
                        % (dt.strftime("%m.%d"), wd[dt.weekday()], "".join(items)))
    body = """
<div class="wrap">
  <header class="phead"><h1 class="phead__title">경제 캘린더</h1><p class="muted">이번 주 미국·한국의 중요도 중 이상 일정입니다. 시각은 한국 시간. 출처 Forex Factory 주간 일정.</p></header>
  {sections}
  <p class="muted small">중요도 상 일정은 발표 전까지 방향을 투표할 수 있습니다. 결과는 <a href="{B}predict/">예측</a>에서 확인합니다. 투표는 이 기기에만 저장됩니다.</p>
</div>""".format(sections="".join(sections) or '<p class="empty">일정을 불러오지 못했습니다.</p>', B=B)
    return shell("calendar", "경제 캘린더", "이번 주 미국·한국 주요 경제 일정과 발표 후 비트코인 반응.", B + "calendar/", body, now, data={"calendar": cal})


def page_impact(imp, now):
    types = imp.get("types") or []
    trows = "".join('<tr><th scope="row">%s</th><td class="num">%d</td><td class="num">%s</td><td class="num %s">%s</td><td class="num">%.0f%%</td></tr>'
                    % (h(t["label"]), t["n"], pct(t["mean_abs"]).lstrip("+"), "up" if t["mean"] >= 0 else "down", pct(t["mean"]), t["strong_share"] * 100) for t in types) \
        or '<tr><td colspan="5" class="muted">유형별 표본이 3건 이상 쌓이면 표시됩니다.</td></tr>'
    srows = "".join('<li><a href="%sa/%s/">%s</a><span class="ib ib--%s ib--g%s">%s %s %s · z %.1f</span><time class="muted small" data-ts="%d">%s</time></li>'
                    % (B, h(r["id"]), h(r["title"]), "up" if r["r"] >= 0 else "down", {"강": "s", "중": "m"}.get(r["g"], "w"), r["asset"], r["win"], pct(r["r"]), r["z"], r["t0"], md_hm(r["t0"]))
                    for r in imp.get("strongest") or []) or '<li class="muted">측정이 쌓이면 표시됩니다.</li>'
    body = """
<div class="wrap narrow">
  <header class="phead"><h1 class="phead__title">임팩트 리포트</h1><p class="muted">어떤 종류의 뉴스가 비트코인을 실제로 많이 움직였는지, 측정값으로 봅니다. 수집 이후 기사만 집계합니다.</p></header>
  <section class="panel"><h2 class="panel__title">유형별 BTC 1시간 반응</h2>
    <div class="table-wrap"><table class="itable"><thead><tr><th scope="col">유형</th><th scope="col" class="num">표본</th><th scope="col" class="num">평균 변동폭</th><th scope="col" class="num">평균 방향</th><th scope="col" class="num">강 비율</th></tr></thead><tbody>{trows}</tbody></table></div>
    <p class="muted small">평균 변동폭은 |수익률|의 평균, 평균 방향은 수익률의 평균입니다. 같은 시간대 다른 뉴스와 시장 전체 흐름이 섞여 있습니다.</p>
  </section>
  <section class="panel"><h2 class="panel__title">최근 7일 가장 강한 반응</h2><ul class="mini-strong">{srows}</ul></section>
  <section class="panel"><h2 class="panel__title">측정 방법</h2>
    <ol class="steps"><li>기사 기준 시각(t0) = 원문 발행 시각과 수집 시각 중 이른 쪽.</li><li>t0가 속한 1분봉 시가 대비, 15분·1시간·24시간 뒤 1분봉 종가의 변화율.</li><li>z = 변화율 ÷ 최근 같은 길이 봉 변화율의 표준편차(15분: 7일, 1시간: 30일, 24시간: 180일).</li><li>|z| ≥ 3 강, ≥ 2 중, 그 외 약.</li></ol>
  </section>
</div>""".format(trows=trows, srows=srows)
    return shell("impact", "임팩트 리포트", "뉴스 유형별 비트코인 가격 반응 실측 통계.", B + "impact/", body, now)


def page_predict(cal, now):
    body = """
<div class="wrap narrow">
  <header class="phead"><h1 class="phead__title">방향 예측</h1><p class="muted">중요 경제 발표 1시간 뒤 비트코인이 발표 시점보다 위일지 아래일지 고릅니다. 포인트만 있고 돈이 걸리지 않습니다.</p></header>
  <section class="panel"><h2 class="panel__title">진행 중인 투표</h2><div id="openPolls" class="polls"><p class="muted">불러오는 중…</p></div></section>
  <section class="panel"><h2 class="panel__title">내 기록</h2><div id="myRecord"><p class="muted">아직 투표하지 않았습니다.</p></div></section>
  <section class="panel"><h2 class="panel__title">커뮤니티 심리·랭킹</h2><p class="muted">여러 사람의 투표를 모으려면 서버 DB가 필요해 3단계에서 연결합니다. 지금은 이 기기의 기록만 보여 줍니다.</p></section>
</div>"""
    return shell("predict", "방향 예측", "경제 발표 후 비트코인 방향 맞히기.", B + "predict/", body, now, data={"calendar": cal})


def page_me(now):
    opts = "".join('<button class="achip achip--lg" type="button" data-asset="%s" aria-pressed="false">%s</button>' % (s, s) for s in config.MARKET_ASSETS)
    tg = os.environ.get("TELEGRAM_CHANNEL_URL", "")
    tg_html = ('<a class="btn btn--accent" href="%s" target="_blank" rel="noopener">텔레그램 채널 구독</a>' % h(tg)) if tg else '<p class="muted">알림 채널은 준비 중입니다.</p>'
    body = """
<div class="wrap narrow">
  <header class="phead"><h1 class="phead__title">마이</h1><p class="muted">설정은 이 브라우저에만 저장되고 서버로 보내지 않습니다.</p></header>
  <section class="panel"><h2 class="panel__title">관심 종목</h2><p class="muted small">고른 종목과 관련된 기사가 피드 위쪽에 오고, 피드의 ‘내 종목만’ 필터에 쓰입니다. 최대 20개.</p>
    <div class="achips achips--wrap" id="watchPick">{opts}</div>
    <form class="addsym" id="addSym"><label class="sr-only" for="symInput">티커 직접 추가</label><input id="symInput" maxlength="10" placeholder="티커 직접 추가 (예: ARB)" autocomplete="off"><button class="btn btn--ghost" type="submit">추가</button></form>
    <div class="achips achips--wrap" id="watchCustom"></div>
  </section>
  <section class="panel"><h2 class="panel__title">알림</h2>{tg}</section>
  <section class="panel"><h2 class="panel__title">데이터</h2><button class="btn btn--ghost" type="button" id="resetLocal">이 기기의 설정·투표 기록 지우기</button></section>
</div>""".format(opts=opts, tg=tg_html)
    return shell("me", "마이", "관심 종목과 설정.", B + "me/", body, now, robots="noindex,follow")


def page_about(health, now):
    src_rows = []
    for s in config.SOURCES:
        st = health.get(s["id"], {})
        ok = st.get("ok")
        status = ('<span class="ok">정상</span>' if not st.get("error") else '<span class="down">오류</span>') if ok or st.get("error") else '<span class="muted">대기</span>'
        src_rows.append("<tr><th scope=\"row\">%s</th><td>%s</td><td>%s</td><td>%s</td></tr>" % (h(s["name"]), config.CATEGORY_LABEL.get(s["hint"], "자동 분류"), "한국어" if s["lang"] == "ko" else "영어", status))
    body = """
<div class="wrap narrow"><header class="phead"><h1 class="phead__title">소개·방법론</h1><p class="muted">SIGNAL이 뉴스를 모으고 가격 반응을 재는 방법, 그리고 데이터 출처입니다.</p></header></div>
<div class="wrap narrow">
  <section class="panel"><h2 class="panel__title">어떻게 동작하나요</h2>
    <ol class="steps"><li>15분마다 국내외 매체 RSS와 업비트 공지를 수집하고 중복을 지웁니다.</li><li>키워드로 크립토·AI·매크로를 나누고 관련 코인을 찾습니다.</li><li>기사 시각 이후 15분·1시간·24시간 가격 변화를 1분봉으로 재고, 평소 변동폭 대비 강도를 매깁니다.</li><li>기사 본문은 저장하지 않습니다. 제목, 짧은 발췌 또는 요약, 원문 링크만 보여 줍니다.</li></ol>
  </section>
  <section class="panel" id="sources"><h2 class="panel__title">데이터 출처</h2>
    <div class="table-wrap"><table class="itable"><thead><tr><th scope="col">매체</th><th scope="col">분야</th><th scope="col">언어</th><th scope="col">최근 수집</th></tr></thead><tbody>{rows}</tbody></table></div>
    <ul class="srcs muted small">
      <li>크립토 시세·1분봉: Binance 공개 API(<a href="https://data-api.binance.vision" rel="nofollow">data-api.binance.vision</a>), 실패 시 Coinbase Exchange API</li>
      <li>국내 시세·공지: 업비트 공개 API</li>
      <li>공포·탐욕 지수: <a href="https://alternative.me/crypto/fear-and-greed-index/" rel="nofollow">alternative.me</a></li>
      <li>환율: <a href="https://www.exchangerate-api.com" rel="nofollow">Rates By Exchange Rate API</a></li>
      <li>경제 일정: <a href="https://www.forexfactory.com/calendar" rel="nofollow">Forex Factory</a></li>
    </ul>
  </section>
  <section class="panel"><h2 class="panel__title">유의 사항</h2><p>SIGNAL은 정보를 모아 보여 주는 서비스이며 투자 조언을 하지 않습니다. 가격 반응은 같은 시간대에 일어난 변화를 잰 값으로, 뉴스가 가격을 움직였다는 뜻이 아닙니다.</p></section>
</div>""".format(rows="".join(src_rows))
    return shell("about", "소개·방법론", "SIGNAL이 뉴스를 모으고 가격 반응을 재는 방법과 데이터 출처.", B + "about/", body, now)


def page_landing(articles, market, imp, now):
    """첫 화면: 브랜드·모션 그래픽·실데이터 증거. 숫자는 모두 실제 수집·측정값이다."""
    day = [a for a in articles if now - a["t0"] < 86400]
    n24 = len(day)
    measured = sum(1 for a in articles if a.get("headline"))
    shares = {c: sum(1 for a in day if a["category"] == c) for c in ("crypto", "ai", "macro")}
    total = sum(shares.values()) or 1
    share_pct = {c: round(v * 100 / total) for c, v in shares.items()}
    strong = [r for r in imp.get("strongest", []) if r.get("g") in ("강", "중")][:3] or imp.get("strongest", [])[:3]
    latest = [{"title": a["title"], "src": a["source_name"], "cat": a["category"]} for a in articles[:4]]
    btc = (market.get("tickers") or {}).get("BTC") or {}
    types = (imp.get("types") or [])[:6]
    proof = "".join(
        '<article class="proof"><div class="proof__meta"><span class="ib ib--{d} ib--g{g}">{asset} {win} {r}{gl}</span><span class="muted small">z {z:.1f} · <time data-ts="{t0}">{when}</time></span></div>'
        '<h3 class="proof__title"><a href="{B}a/{id}/">{title}</a></h3>'
        '<div class="proof__chart" data-sym="{asset}" data-t0="{t0}" aria-hidden="true"></div></article>'.format(
            d="up" if r["r"] >= 0 else "down", g={"강": "s", "중": "m"}.get(r["g"], "w"), asset=h(r["asset"]), win=r["win"], r=pct(r["r"]),
            gl=(" · " + r["g"]) if r.get("g") else "", z=r["z"], t0=r["t0"], when=md_hm(r["t0"]), B=B, id=h(r["id"]), title=h(r["title"]))
        for r in strong) or '<p class="muted">측정이 쌓이면 실제 사례가 여기에 나타납니다.</p>'
    top_abs = max([t["mean_abs"] for t in types] or [1]) or 1
    bars = "".join(
        '<li class="tbar"><span class="tbar__label">{label}</span><span class="tbar__track"><i style="--v:{v:.3f}"></i></span><span class="tbar__val">{val} <span class="muted">n={n}</span></span></li>'.format(
            label=h(t["label"]), v=t["mean_abs"] / top_abs, val=pct(t["mean_abs"]).lstrip("+"), n=t["n"]) for t in types) \
        or '<li class="muted">유형별 표본이 쌓이는 중입니다.</li>'
    flow_cards = "".join('<div class="fc" style="--k:%d"><i class="dot dot--%s"></i><span>%s</span><em>%s</em></div>' % (i, a["cat"], h(a["title"][:46]), h(a["src"])) for i, a in enumerate(latest))
    s0 = strong[0] if strong else None
    body = """
<section class="lhero" aria-labelledby="lheroTitle">
  <canvas class="lhero__canvas" id="sphereCanvas" aria-hidden="true"></canvas>
  <div class="wrap lhero__inner">
    <div class="lhero__copy">
      <p class="eyebrow eyebrow--live reveal-in" style="--d:0"><span class="live-dot" aria-hidden="true"></span>LIVE · 15분마다 수집 · 마지막 <time data-ts="{now}">{now_hm}</time></p>
      <h1 class="lhero__title" id="lheroTitle"><span class="w" style="--d:1">Noise</span> <span class="w" style="--d:2">out,</span><br><span class="w" style="--d:3"><em>Signal</em></span> <span class="w" style="--d:4">in.</span></h1>
      <p class="lhero__lede reveal-in" style="--d:5">크립토·AI·매크로 뉴스를 모으고, 뉴스마다 비트코인이 <b>실제로 얼마나 움직였는지</b> 잽니다. 감이 아니라 측정값으로.</p>
      <div class="lhero__actions reveal-in" style="--d:6"><a class="btn btn--accent btn--lg" href="{B}feed/">피드 열기 <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 10h10m-4-4 4 4-4 4"/></svg></a><a class="btn btn--ghost btn--lg" href="{B}impact/">임팩트 리포트</a></div>
      <dl class="lhero__stats reveal-in" style="--d:7">
        <div><dt>최근 24시간 기사</dt><dd><span class="count" data-to="{n24}">{n24}</span></dd></div>
        <div><dt>수집 매체</dt><dd><span class="count" data-to="{nsrc}">{nsrc}</span></dd></div>
        <div><dt>반응 측정 기사</dt><dd><span class="count" data-to="{measured}">{measured}</span></dd></div>
      </dl>
    </div>
    <div class="lhero__legend reveal-in" style="--d:8" aria-label="그래픽 설명">
      <p class="mono-label">SIGNAL FIELD · 최근 24시간</p>
      <ul><li><i class="dot dot--crypto"></i>크립토 {pc}%</li><li><i class="dot dot--ai"></i>AI {pa}%</li><li><i class="dot dot--macro"></i>매크로 {pm}%</li></ul>
      <p class="muted small">점 하나가 기사 하나의 자리입니다. 펄스는 뉴스가 가격선에 닿는 모습을 나타냅니다.</p>
      <p class="lhero__btc"><span class="muted small">BTC</span> <b id="heroBtc">{btc}</b> <span id="heroBtcChg" class="{bdir}">{bchg}</span></p>
    </div>
  </div>
  <a class="lhero__scroll" href="#how" aria-label="아래로">SCROLL<i></i></a>
</section>

<section class="flow" id="how" aria-labelledby="flowTitle">
  <div class="flow__sticky">
    <div class="wrap flow__inner">
      <div class="flow__text">
        <p class="mono-label">HOW IT WORKS</p>
        <h2 class="lsec__title" id="flowTitle">뉴스가 시그널이 되기까지</h2>
        <ol class="flow__steps">
          <li data-step="0"><b>01 수집</b><p>국내외 {nsrc}개 매체를 15분마다 모으고, 중복과 공지성 기사를 걸러 크립토·AI·매크로로 나눕니다.</p></li>
          <li data-step="1"><b>02 측정</b><p>기사 시각을 기준으로 15분·1시간·24시간 뒤 가격을 1분봉으로 잽니다.</p></li>
          <li data-step="2"><b>03 시그널</b><p>평소 변동폭의 몇 배였는지(z)로 강·중·약을 매깁니다. 상관이지 인과는 아닙니다.</p></li>
        </ol>
      </div>
      <div class="flow__stage" aria-hidden="true">
        <div class="flow__cards">{flow_cards}</div>
        <div class="flow__chartbox"><svg class="flow__chart" id="flowChart" viewBox="0 0 400 160" preserveAspectRatio="none"></svg><span class="flow__t0">기사 시각</span></div>
        <div class="flow__gauge">
          <svg viewBox="0 0 200 116"><path class="g-track" d="M20 100a80 80 0 0 1 160 0"/><path class="g-fill" id="flowGaugeFill" d="M20 100a80 80 0 0 1 160 0" pathLength="100"/><g class="g-needle" id="flowNeedle"><line x1="100" y1="100" x2="100" y2="34"/><circle cx="100" cy="100" r="5"/></g></svg>
          <p class="flow__z"><b id="flowZ">z 0.0</b><span>{s0label}</span></p>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="lsec wrap" aria-labelledby="proofTitle">
  <p class="mono-label">PROOF · 최근 7일</p>
  <h2 class="lsec__title" id="proofTitle">실제로 잰 반응</h2>
  <p class="lsec__lede muted">평소보다 크게 움직인 순간들입니다. 차트의 세로선이 기사 시각입니다.</p>
  <div class="proofs">{proof}</div>
</section>

<section class="lsec wrap" aria-labelledby="typesTitle">
  <div class="lsplit">
    <div><p class="mono-label">IMPACT REPORT</p><h2 class="lsec__title" id="typesTitle">어떤 뉴스가<br>더 크게 움직였나</h2><p class="lsec__lede muted">이벤트 유형별 BTC 1시간 평균 변동폭. 측정이 쌓일수록 정확해집니다.</p><a class="btn btn--ghost" href="{B}impact/">리포트 전체 보기</a></div>
    <ol class="tbars" id="tbars">{bars}</ol>
  </div>
</section>

<section class="lsec wrap" aria-labelledby="featTitle">
  <p class="mono-label">FEATURES</p>
  <h2 class="lsec__title" id="featTitle">매일 들어올 이유</h2>
  <div class="feats">
    <a class="feat feat--wide" href="{B}feed/"><span class="feat__vis feat__vis--feed" aria-hidden="true"><i></i><i></i><i></i></span><b>실시간 피드</b><p>카테고리·반응 강도·내 종목으로 걸러 보고, 새 기사가 오면 바로 알려 줍니다.</p></a>
    <a class="feat" href="{B}calendar/"><span class="feat__vis feat__vis--cal" aria-hidden="true"><i>FOMC</i><i>CPI</i><i>고용</i></span><b>경제 캘린더</b><p>발표 후 BTC 반응까지 기록합니다.</p></a>
    <a class="feat" href="{B}predict/"><span class="feat__vis feat__vis--vote" aria-hidden="true"><i class="up">위</i><i class="down">아래</i></span><b>방향 예측</b><p>발표 1시간 뒤 방향을 맞혀 보세요. 돈은 걸리지 않습니다.</p></a>
    <a class="feat" href="{B}markets/"><span class="feat__vis feat__vis--kimp" aria-hidden="true"><b>{kimp}</b><small>BTC 김프</small></span><b>마켓·김프</b><p>12개 코인, 김치 프리미엄, 공포·탐욕.</p></a>
    <a class="feat" href="{B}me/"><span class="feat__vis feat__vis--star" aria-hidden="true"><i>★</i></span><b>관심 종목</b><p>내 코인 기사를 위로 올려 줍니다.</p></a>
  </div>
</section>

<section class="lcta" aria-labelledby="ctaTitle">
  <div class="lcta__marquee" aria-hidden="true"><div class="lcta__track"><span>BITCOIN</span><span>·</span><span>FOMC</span><span>·</span><span>INFERENCE</span><span>·</span><span>ETF</span><span>·</span><span>CPI</span><span>·</span><span>STABLECOIN</span><span>·</span><span>BITCOIN</span><span>·</span><span>FOMC</span><span>·</span><span>INFERENCE</span><span>·</span><span>ETF</span><span>·</span><span>CPI</span><span>·</span><span>STABLECOIN</span><span>·</span></div></div>
  <div class="wrap lcta__inner">
    <h2 class="lcta__title" id="ctaTitle">노이즈는 걸렀습니다.<br><em>시그널</em>만 보세요.</h2>
    <a class="btn btn--accent btn--lg" href="{B}feed/">피드 열기</a>
    <p class="muted small">회원가입 없음 · 무료 · 투자 조언이 아닙니다</p>
  </div>
</section>""".format(
        now=now, now_hm=md_hm(now), B=B, n24=n24, nsrc=len(config.SOURCES), measured=measured,
        pc=share_pct["crypto"], pa=share_pct["ai"], pm=share_pct["macro"],
        btc=("$" + price(btc["price"])) if btc.get("price") else "–", bdir="up" if btc.get("chg", 0) >= 0 else "down", bchg=pct(btc.get("chg")) if btc else "",
        flow_cards=flow_cards, s0label=("예: " + h(s0["title"][:30]) + ("…" if len(s0["title"]) > 30 else "") + " · " + s0["asset"] + " " + s0["win"]) if s0 else "측정 대기",
        proof=proof, bars=bars, kimp=pct(((market.get("kimp") or {}).get("BTC") or {}).get("premium")))
    data = {"landing": {"shares": shares, "spark": btc.get("spark") or [], "z": s0["z"] if s0 else 0, "g": s0["g"] if s0 else None}}
    return shell("home", "SIGNAL — 뉴스가 움직인 가격까지", "크립토·AI·매크로 뉴스를 모으고, 뉴스마다 비트코인 가격이 실제로 얼마나 움직였는지 실측해 보여 줍니다.",
                 B, body, now, data=data)


def page_404(now):
    body = '<div class="wrap narrow phead"><h1 class="phead__title">페이지를 찾을 수 없습니다</h1><p class="muted">30일이 지난 기사는 정리됩니다. <a href="%sfeed/">피드로 가기</a></p></div>' % B
    return shell("404", "페이지 없음", "페이지를 찾을 수 없습니다.", B + "404.html", body, now, robots="noindex")


def sitemap(articles, now):
    urls = [("", now), ("feed/", now), ("markets/", now), ("calendar/", now), ("impact/", now), ("about/", now)]
    urls += [("a/%s/" % a["id"], a["t0"]) for a in articles]
    body = "".join("<url><loc>%s/%s</loc><lastmod>%s</lastmod></url>" % (config.SITE_URL, p, util.iso(t)[:10]) for p, t in urls)
    return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % body


def related(a, articles, n=5):
    """같은 유형·자산의 이전 기사. 이전 기사만 고르므로 새 기사가 들어와도 페이지가 바뀌지 않는다."""
    older = [b for b in articles if b["t0"] <= a["t0"] and b["id"] != a["id"]]
    mine = set(a.get("assets", []))
    same = [b for b in older if (b.get("etype") == a.get("etype") != "other") or (mine & set(b.get("assets", [])))][:n]
    if len(same) < n:
        ids = {b["id"] for b in same}
        same += [b for b in older if b["category"] == a["category"] and b["id"] not in ids][: n - len(same)]
    return same


def build_site(out, articles, market, cal, imp, health, now):
    """out 디렉터리에 사이트 전체를 쓴다. 기존 data/와 og/는 호출자가 미리 채워 둔다."""
    global HAS_BRIEF, ASSET_VER
    digest = []
    for name in sorted(os.listdir(os.path.join(WEB, "assets"))):
        with open(os.path.join(WEB, "assets", name), "rb") as f:
            digest.append(util.short_hash(f.read().decode("latin-1")))
    ASSET_VER = util.short_hash("".join(digest))
    HAS_BRIEF = os.path.isfile(os.path.join(out, "og", "brief.jpg"))
    shutil.copytree(os.path.join(WEB, "assets"), os.path.join(out, "assets"), dirs_exist_ok=True)
    util.write_text(os.path.join(out, ".nojekyll"), "")
    util.write_text(os.path.join(out, "index.html"), page_landing(articles, market, imp, now))
    util.write_text(os.path.join(out, "feed", "index.html"), page_feed(articles, market, cal, imp, now))
    for a in articles:
        util.write_text(os.path.join(out, "a", a["id"], "index.html"), page_article(a, related(a, articles), now))
    util.write_text(os.path.join(out, "markets", "index.html"), page_markets(market, now))
    util.write_text(os.path.join(out, "calendar", "index.html"), page_calendar(cal, now))
    util.write_text(os.path.join(out, "impact", "index.html"), page_impact(imp, now))
    util.write_text(os.path.join(out, "predict", "index.html"), page_predict(cal, now))
    util.write_text(os.path.join(out, "me", "index.html"), page_me(now))
    util.write_text(os.path.join(out, "about", "index.html"), page_about(health, now))
    util.write_text(os.path.join(out, "404.html"), page_404(now))
    util.write_text(os.path.join(out, "sitemap.xml"), sitemap(articles, now))
    util.write_text(os.path.join(out, "robots.txt"), "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % config.SITE_URL)
    util.write_json(os.path.join(out, "data", "feed.json"), {"at": now, "items": [feed_item(a) for a in articles[: config.FEED_JSON_LIMIT]]})
