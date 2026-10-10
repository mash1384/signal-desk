"""정적 페이지 생성. 서버 없이 GitHub Pages에서 그대로 열리는 HTML을 만든다."""

import html
import json
import os
import shutil

from . import config, util
from .impact import assets_for, subjects
from .moves import COINS as MOVE_COINS

OG_DEFAULT = False
HAS_BRIEF = False
ASSET_VER = "0"

B = config.SITE_BASE
WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

NAV = [("map", "map/", "뉴스 영향"), ("live", "live/", "라이브"), ("listings", "listings/", "상장 레이더"), ("events", "events/", "이벤트 리스크"),
       ("patterns", "patterns/", "패턴")]
TABBAR = ["map", "live", "listings", "events", "patterns"]
TAB_LABEL = {"map": "영향", "listings": "상장", "events": "이벤트"}

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
    "map": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 16.5h14"/><rect x="3.5" y="9" width="3" height="5" rx="0.8"/><rect x="8.5" y="4.5" width="3" height="6" rx="0.8"/><rect x="13.5" y="7" width="3" height="7.5" rx="0.8"/></svg>',
    "pulse": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M2.5 10.5h3l2-5 3.5 10 2-5h4.5"/></svg>',
    "rocket": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 16.5 7 12.5M10 3c3.5 1 6 3.5 7 7l-5.5 5.5-7-7zM12.5 7.5h.01"/><path d="M6.5 9.5 4 9l-1 2 3 .5M10.5 13.5l.5 2.5-2 1-.5-3"/></svg>',
    "clock": '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="6.8"/><path d="M10 6v4.2l2.8 1.8"/></svg>',
    "grid": '<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="3.5" y="3.5" width="5.5" height="5.5" rx="1.2"/><rect x="11" y="3.5" width="5.5" height="5.5" rx="1.2"/><rect x="3.5" y="11" width="5.5" height="5.5" rx="1.2"/><rect x="11" y="11" width="5.5" height="5.5" rx="1.2"/></svg>',
}
TAB_ICON = {"map": "map", "live": "pulse", "listings": "rocket", "events": "clock", "patterns": "grid"}


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
    tabs = "".join('<a class="tab" href="%s%s"%s>%s<span>%s</span></a>' % (B, p, ' aria-current="page"' if k == page else "", ICON[TAB_ICON[k]], TAB_LABEL.get(k, label))
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
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400..900&family=Geist+Mono:wght@400..600&family=Instrument+Serif&display=swap" rel="stylesheet">
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
      <a class="icon-btn nav__me" href="{B}me/" aria-label="마이"{me_cur}>{user}</a>
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
    <nav class="footer__nav" aria-label="푸터"><a href="{B}about/">소개·방법론</a><a href="{B}about/#sources">데이터 출처</a><a href="{B}patterns/">패턴</a><a href="{B}sitemap.xml">사이트맵</a></nav>
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
           search=ICON["search"], sun=ICON["sun"], moon=ICON["moon"], body=body, user=ICON["user"], me_cur=' aria-current="page"' if page == "me" else "",
           boot=json.dumps(boot, ensure_ascii=False).replace("</", "<\\/"))


# ---------------------------------------------------------------- 카드와 배지

def impact_badge(a):
    hd = a.get("headline")
    st = a.get("impact_status")
    if hd:
        d = "up" if hd["r"] >= 0 else "down"
        grade = hd.get("g")
        gcls = {"강": "s", "중": "m", "약": "w"}.get(grade, "w")
        adj = hd.get("adj")
        return ('<span class="ib ib--%s ib--g%s" title="기사 시각부터 %s 동안 %s %s">%s<b>%s %s</b> %s%s%s</span>'
                % (d, gcls, "1시간" if hd["win"] == "1h" else "15분", hd["asset"], "가격 변화에서 시장 몫을 뺀 값" if adj else "가격 변화(시장 전체 반응)",
                   ICON[d], hd["asset"], hd["win"], "시장 대비 " if adj else "", pct(hd["r"]), (" · " + grade) if grade else ""))
    if st == "skip":
        return ""
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
  {rx}
  <div class="fcard__foot">{badge}<span class="achips">{chips}</span></div>
  {pat}
</article>""".format(rx=rx_html(a, 0), pat=pattern_html(a), id=h(a["id"]), cat=cat, assets=h(",".join(a.get("assets", []))), imp_n=a["importance"], t0=a["t0"],
                     catlabel=config.CATEGORY_LABEL.get(cat, cat), imp=imp, src=h(a["source_name"]), iso=util.iso(a["t0"]),
                     hm=md_hm(a["t0"]), lang=lang, href=article_path(a), title=h(a["title"]), body=body, badge=impact_badge(a), chips=chips(a))


def feed_item(a):
    """클라이언트용 축약 JSON."""
    return {
        "id": a["id"], "t0": a["t0"], "title": a["title"], "src": a["source_name"], "lang": a.get("lang"),
        "cat": a["category"], "assets": a.get("assets", []), "imp": a["importance"], "etype": a.get("etype"),
        "sum": a.get("summary") or [], "ex": a.get("excerpt") or "", "llm": a.get("summary_by") == "llm",
        "h": a.get("headline"), "st": a.get("impact_status") or "measuring", "url": a["url"],
        "rx": rx_cells(a), "pt": a.get("pattern"),
    }


def rx_cells(a):
    """대표 코인의 15분·1시간·24시간 반응. 아직이면 None(측정 예정 시각은 t0로 계산)."""
    syms = assets_for(a)
    if not syms or a.get("impact_status") == "skip":
        return None
    imp = a.get("impact") or {}
    sym = (a.get("headline") or {}).get("asset") or syms[0]
    w = imp.get(sym) or {}
    adj = dict(subjects(a)).get(sym, False)
    return {"s": sym, "adj": adj, **{k: (None if (w.get(k) or {}).get("r") is None else round(w[k]["r"], 3)) for k in ("15m", "1h", "24h")}}


def rx_html(a, now):
    rx = rx_cells(a)
    if not rx:
        return ""
    cells = []
    for k, label, sec in (("15m", "15분", 900), ("1h", "1시간", 3600), ("24h", "24시간", 86400)):
        v = rx[k]
        if v is not None:
            cells.append('<span class="rxc"><b>%s</b><em class="%s">%s</em></span>' % (label, "up" if v >= 0 else "down", pct(v)))
        elif a.get("impact_status") == "failed":
            cells.append('<span class="rxc is-na"><b>%s</b><em>–</em></span>' % label)
        else:
            cells.append('<span class="rxc is-wait"><b>%s</b><em data-due="%d">측정 중</em></span>' % (label, a["t0"] + sec))
    return '<div class="rxcells" aria-label="%s %s"><span class="rxcells__s">%s%s</span>%s</div>' % (
        h(rx["s"]), "시장 대비 반응" if rx["adj"] else "시장 전체 반응", h(rx["s"]), '<small>시장 대비</small>' if rx["adj"] else '<small>시장 전체</small>', "".join(cells))


def pattern_html(a):
    pt = a.get("pattern")
    if not pt:
        return ""
    if pt.get("n", 0) >= 5:
        v = ('<p class="fpat__v">%s 1시간 %s중앙값 <b class="%s">%s</b> · 상승 %d%% · 중·강 %d%% <span class="muted">(n=%d, 최근 30일)</span></p>'
             % (h(pt["sym"]), "시장 대비 " if pt.get("adj") else "", "up" if pt["med"] >= 0 else "down", pct(pt["med"]), round(pt["up"] * 100), round(pt["strong"] * 100), pt["n"]))
        top = pt.get("top") or {}
        if top.get("id"):
            v += '<p class="fpat__top small muted">가장 컸던 사례: <a href="%sa/%s/">%s</a> (%s %s)</p>' % (B, h(top["id"]), h(top["title"]), h(top["sym"]), pct(top["r1h"]))
    else:
        v = '<p class="fpat__v muted">표본 부족 (n=%d)</p>' % pt.get("n", 0)
    return '<details class="fpat"><summary>이런 뉴스는 보통 · %s · %s</summary>%s<p class="small muted">%s 관련 같은 유형 뉴스만 모았습니다. 같은 시간대의 가격 변화이며, 뉴스가 원인이라는 뜻은 아닙니다.</p></details>' % (
        h(pt["label"]), h(pt["sym"]), v, h(pt["sym"]))


# ---------------------------------------------------------------- 페이지들

def breaking_html(articles, now):
    """지금 터진 뉴스: 최근 60분 안에 반응이 중 이상이거나 아직 재는 중인 기사."""
    picks = []
    for a in articles:
        if now - a["t0"] > 3600:
            break
        hd = a.get("headline") or {}
        if hd.get("g") in ("강", "중") or (not hd and a.get("impact_status") not in ("failed", "skip") and a["importance"] >= 2):
            picks.append(a)
    if not picks:
        return '<p class="brk__none small muted">최근 60분 안에 크게 반응했거나 재는 중인 주요 뉴스가 없습니다.</p>'
    items = "".join('<li class="brk__i"><a href="{href}"><span class="brk__m"><span class="chip cat cat--{cat}">{cl}</span><time data-ts="{t0}">{hm}</time></span><b>{title}</b>{badge}</a></li>'.format(
        href=article_path(a), cat=a["category"], cl=config.CATEGORY_LABEL.get(a["category"], a["category"]), t0=a["t0"], hm=hm(a["t0"]), title=h(a["title"]),
        badge=impact_badge(a)) for a in picks[:8])
    return '<ol class="brk__list">%s</ol>' % items


def risk_html(ev, now):
    """다가오는 위험: 다음 6시간 안의 중요도 높은 발표 하나."""
    up = [u for u in (ev or {}).get("upcoming", []) if now < u["ts"] <= now + 6 * 3600]
    if not up:
        return ""
    u = sorted(up, key=lambda x: (-x["level"], x["ts"]))[0]
    st = u.get("stats") or {}
    num = ('과거 1시간 최대 ±%s · 중앙값 ±%s <span class="muted">(n=%d)</span>' % (pct(st["abs1h"]["max"]).lstrip("+"), pct(st["abs1h"]["med"]).lstrip("+"), st["n"])) if st.get("abs1h") else '<span class="muted">과거 통계 없음</span>'
    return ('<a class="risk" href="{B}events/#ev-{key}"><span class="risk__k">다가오는 위험</span><b>{name}</b><span class="risk__t"><time>{when}</time> · <span data-left="{ts}"></span></span><span class="risk__v">{num}</span></a>'
            .format(B=B, key=h(str(u.get("kind") or "x")) + "-" + str(u["ts"]), name=h(u["name"]), when=hm(u["ts"]), ts=u["ts"], num=num))


def page_feed(articles, market, cal, imp, now, ev=None):
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
      <h1 id="feedTitle" class="feed__title">라이브</h1>
      <p class="muted feed__upd">마지막 수집 <time data-ts="{now}">{now_hm}</time> · 15분마다 갱신</p>
    </div>
    {risk}
    <section class="brk" aria-labelledby="brkTitle"><h2 class="brk__title" id="brkTitle"><span class="live-dot" aria-hidden="true"></span>지금 터진 뉴스 <span class="muted small">최근 60분 · 반응 중 이상 또는 재는 중</span></h2>{brk}</section>
    <button class="new-pill" id="newPill" type="button" hidden></button>
    <div class="feed__list" id="feedList">
{cards}
    </div>
    <button class="btn btn--ghost feed__more" id="loadMore" type="button" hidden>더 보기</button>
  </section>
  <aside class="rail" aria-label="요약 정보">
    <section class="panel"><h2 class="panel__title">시장 온도</h2><div id="tempPanel" class="temp">{temp}</div></section>
    <section class="panel"><h2 class="panel__title">다가오는 일정 <a class="panel__more" href="{B}events/">이벤트 리스크</a></h2><ul class="mini-cal">{cal}</ul></section>
    <section class="panel"><h2 class="panel__title">최근 7일 강한 반응 <a class="panel__more" href="{B}patterns/">패턴</a></h2><ul class="mini-strong">{strong}</ul></section>
    {brief}
  </aside>
</div>""".format(now=now, now_hm=md_hm(now), cards=cards, cal=cal_html, strong=strong, B=B, temp=temp_panel(market), risk=risk_html(ev, now), brk=breaking_html(articles, now),
           brief=('<section class="panel"><h2 class="panel__title">오늘의 시그널</h2><a class="brief-img" href="%sog/brief.jpg" target="_blank" rel="noopener"><img src="%sog/brief.jpg?v=%d" alt="오늘의 시그널 요약 이미지" width="1080" height="1080" loading="lazy"></a><p class="muted small">이미지를 길게 눌러 저장하거나 공유하세요.</p></section>' % (B, B, now)) if HAS_BRIEF else "")
    return shell("live", "라이브 — 지금 터진 뉴스와 가격 반응",
                 "크립토·AI·매크로 뉴스를 실시간으로 모으고 기사마다 15분·1시간·24시간 가격 반응을 실측해 보여 줍니다.", B + "live/", body, now)


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
    subs = subjects(a)
    rows = []
    for sym, adj in subs:
        cells = []
        for win, secs in config.WINDOWS:
            v = imp.get(sym, {}).get(win)
            if v and v.get("r") is not None:
                g = v.get("g")
                sub = ('<span class="g g--%s">%s · z %.1f</span>' % ({"강": "s", "중": "m"}.get(g, "w"), g, v["z"])) if g else ""
                if v.get("adj") and v.get("raw") is not None:
                    sub += '<span class="art__raw">실제 %s · 시장 몫 %s</span>' % (pct(v["raw"]), pct(v.get("m") or 0))
                cells.append('<td class="%s"><b>%s</b>%s</td>' % ("up" if v["r"] >= 0 else "down", pct(v["r"]), sub))
            elif v:
                cells.append('<td class="muted">측정 불가</td>')
            else:
                cells.append('<td class="muted" data-wait="%d">측정 중</td>' % (a["t0"] + secs))
        rows.append("<tr><th scope=\"row\">%s<small>%s</small></th>%s</tr>" % (h(sym), "시장 대비" if adj else "시장 전체", "".join(cells)))
    crowd = a.get("crowd", 0)
    note = ('<p class="note">같은 시간(±30분)에 %s 관련 뉴스가 %d건 더 있었습니다. 이 값은 그 뉴스들이 함께 나눠 가진 움직임일 수 있습니다.</p>' % (h(subs[0][0]), crowd)) if crowd and subs else ""
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
    primary = subs[0][0] if subs else None
    if not subs:
        impact_sec = ('<p class="art__skip">이 뉴스는 코인 가격과 직접 관련된 내용이 아니어서 가격 반응을 재지 않았습니다.</p>'
                      '<p class="muted small">SIGNAL은 그 코인을 직접 언급한 뉴스와, 시장 전체를 움직이는 발표(FOMC·물가·고용, 크립토 ETF·규제·해킹·상장)만 잽니다. '
                      '같은 시간에 마침 가격이 움직였다고 관련 없는 뉴스에 숫자를 붙이지 않기 위해서입니다.</p>')
    else:
        anyadj = any(adj for _, adj in subs)
        expl = ("시장 대비 값은 실제 가격 변화에서 같은 시간 시장 전체(시총 상위 5개, 그 코인 제외)가 움직인 몫을 뺀 것입니다. "
                if anyadj else "시장 전체를 움직이는 발표라 BTC 가격 변화를 그대로 보여 줍니다. ")
        impact_sec = """<p class="muted small">기사 기준 시각부터의 변화입니다. {expl}z는 평소 흔들림 대비 몇 배인지이며 |z| 3 이상 강, 2 이상 중입니다.</p>
    <div class="table-wrap"><table class="itable"><thead><tr><th scope="col">코인</th><th scope="col">15분</th><th scope="col">1시간</th><th scope="col">24시간</th></tr></thead><tbody>{rows}</tbody></table></div>
    {note}{est}
    <figure class="chart" id="artChart" data-sym="{primary}" data-t0="{t0}">
      <div class="chart__box" role="img" aria-label="{primary} 가격, 기사 시각 전후"></div>
      <figcaption class="muted small">{primary} 1분봉 · 세로선이 기사 기준 시각 · 출처 Binance(실패 시 Coinbase)</figcaption>
    </figure>
    <p class="note">같은 시간에 일어난 일을 잰 값입니다. 이 기사가 가격을 움직였다는 뜻은 아닙니다.</p>
    {pat}
    {maplink}""".format(expl=expl, rows="".join(rows), note=note, est=est, primary=h(primary), t0=a["t0"],
                     pat=pattern_html(a).replace('<details class="fpat">', '<details class="fpat" open>'),
                     maplink=('<p class="art__maplink"><a href="%smap/?s=%s">뉴스 영향에서 %s 오늘 움직임 보기</a></p>' % (B, h(primary), h(primary))) if primary in {c[0] for c in MOVE_COINS} else "")
    body = """
<div class="wrap art">
  <nav class="crumbs" aria-label="경로"><a href="{B}live/">라이브</a><span aria-hidden="true">/</span><span>{catlabel}</span></nav>
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
    {impact_sec}  </section>
  <section class="art__related"><h2 class="h2">관련 기사</h2><ul class="rel">{rel}</ul></section>
</div>""".format(B=B, cat=a["category"], catlabel=config.CATEGORY_LABEL[a["category"]], src=h(a["source_name"]), iso=util.iso(a["t0"]),
                 t0=a["t0"], when=util.kst(a["t0"]).strftime("%Y.%m.%d %H:%M"), title=h(a["title"]), orig=orig, lead=lead, url=h(a["url"]),
                 out=ICON["out"], share=ICON["share"], rel=rel, impact_sec=impact_sec, id=h(a["id"]))
    desc = (a["summary"][0] if a.get("summary") else a.get("excerpt") or a["title"])[:150]
    og = "%s/og/%s.jpg" % (config.SITE_URL, a["id"]) if a.get("og") else None
    return shell("article", a["title"], desc, article_path(a), body, now, og=og, data={"article": feed_item(a)})


def page_me(now):
    opts = "".join('<button class="achip achip--lg" type="button" data-asset="%s" aria-pressed="false">%s</button>' % (s, s) for s in config.MARKET_ASSETS)
    body = """
<div class="wrap narrow">
  <header class="phead"><h1 class="phead__title">마이</h1><p class="muted">설정은 이 브라우저에만 저장되고 서버로 보내지 않습니다.</p></header>
  <section class="panel"><h2 class="panel__title">관심 종목</h2><p class="muted small">고른 종목은 라이브의 ‘내 종목만’ 필터와 위쪽 정렬, 상장 레이더의 공지 강조에 쓰입니다. 최대 20개.</p>
    <div class="achips achips--wrap" id="watchPick">{opts}</div>
    <form class="addsym" id="addSym"><label class="sr-only" for="symInput">티커 직접 추가</label><input id="symInput" maxlength="10" placeholder="티커 직접 추가 (예: ARB)" autocomplete="off"><button class="btn btn--ghost" type="submit">추가</button></form>
    <div class="achips achips--wrap" id="watchCustom"></div>
  </section>
</div>""".format(opts=opts)
    return shell("me", "마이", "관심 종목 설정.", B + "me/", body, now, robots="noindex,follow")

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
    <ol class="steps"><li>15분마다 국내외 매체 {nsrc}곳의 RSS와 업비트 공지를 수집하고 중복을 지웁니다.</li><li>키워드로 크립토·AI·매크로를 나누고 관련 코인을 찾습니다.</li><li>그 코인을 직접 언급한 기사와 시장 전체를 움직이는 발표만 골라, 기사 시각 이후 15분·1시간·24시간 가격 변화를 1분봉으로 재고 시장 몫을 뺍니다.</li><li>기사 본문은 저장하지 않습니다. 제목, 짧은 발췌 또는 요약, 원문 링크만 보여 줍니다.</li></ol>
  </section>
  <section class="panel" id="method"><h2 class="panel__title">계산 방법</h2>
    <ol class="steps">
      <li><span><b>어떤 기사를 재나</b>: 제목·발췌에서 코인 24개 중 하나를 직접 언급한 기사는 그 코인을, 코인 언급이 없어도 FOMC·물가·고용 발표와 크립토 분야의 ETF·규제·해킹·상장 뉴스는 BTC를 잽니다. 그 밖의 기사(AI 제품, 일반 경제 등)에는 가격 반응을 붙이지 않습니다. 같은 시간에 마침 가격이 움직였다고 관련 없는 뉴스에 숫자를 붙이지 않기 위해서입니다.</span></li>
      <li><span><b>가격 반응</b>: 기사 기준 시각(t0, 원문 발행 시각과 수집 시각 중 이른 쪽)이 속한 1분봉 시가 대비 15분·1시간·24시간 뒤 1분봉 종가의 변화율. 코인 기사는 여기서 시장 몫(그 코인을 뺀 시총 상위 5개 바스켓의 같은 시간 변화 × 그 코인의 β, 최근 30일 1시간 회귀)을 뺀 ‘시장 대비’ 값을 보여 줍니다. 시장 전체 발표는 BTC 변화를 그대로 보여 줍니다.</span></li>
      <li><span><b>강도(z)</b>: 시장 대비 값 ÷ 시장 몫을 뺀 평소 흔들림(1시간 회귀 잔차 표준편차를 구간 길이에 맞춰 환산). 시장 전체 발표는 BTC 변화율 ÷ 같은 길이 봉 변화율의 표준편차(15분: 7일, 1시간: 30일, 24시간: 180일). |z| 3 이상 강, 2 이상 중, 그 외 약.</span></li>
      <li><span><b>뉴스 영향</b>: 코인 등락 = 시장 몫 + 자기 몫. 시장 몫은 그 코인을 뺀 나머지 코인(시총 가중 24개)의 1분 움직임 × 그 코인의 민감도 β(최근 30일 1시간 수익률 회귀). 60분 동안의 자기 몫이 평소 흔들림(같은 회귀의 잔차 표준편차)의 2.5배를 넘으면 큰 움직임으로 보고, 시작 30분 전~5분 뒤 그 코인을 제목(없으면 본문 첫머리)에서 언급한 뉴스를 원인 후보로 붙입니다(1건 유력, 여러 건 복합). 알트코인 소식이 많은 매체와 프로젝트 공식 블로그도 함께 모으며, 가격 예측·차트 분석 글은 뺍니다. 시장 전체 물결은 2배 기준에 거시·시장 전반 뉴스를 붙입니다.</span></li>
      <li><span><b>상장 해부도</b>: 업비트 원화 상장마다 첫 1분봉 시가를 0%로 둔 24시간 곡선, 공지 직전 1분 바이낸스 종가를 0%로 둔 공지 후 4시간 곡선. 시세가 없는 코인과 스테이블코인은 집계에서 뺍니다.</span></li>
      <li><span><b>이벤트 리스크</b>: 과거 같은 발표마다 발표 직전 1분 바이낸스 BTC 종가 대비 15분·1시간 뒤 변화를 재고 그 절댓값의 중앙값·상위 10%를 보여 줍니다. ‘평소의 몇 배’는 이 중앙값 ÷ 최근 30일 발표가 없던 같은 UTC 시각 1시간 봉 절대 변동의 중앙값입니다. 과거 발표 시각은 FRED 일정이 있는 2025년 이후만 있어 월간 지표는 표본이 20건 안팎이고, 표본 8건 미만이면 수치를 숨깁니다.</span></li>
      <li><span><b>패턴</b>: 최근 30일 측정이 끝난 관련 기사로만 계산합니다. 열지도 칸 = 기사가 잰 코인별 1시간 절대 변동(코인 기사는 시장 대비) ÷ 그 코인의 평소 1시간 흔들림의 중앙값. 칸 표본 3건, 비슷한 뉴스 요약 5건 미만이면 ‘표본 부족’으로 둡니다.</span></li>
    </ol>
    <p class="muted small">모든 수치는 같은 시간대에 일어난 변화를 잰 값이며 인과를 뜻하지 않습니다.</p>
  </section>
  <section class="panel" id="sources"><h2 class="panel__title">데이터 출처</h2>
    <div class="table-wrap"><table class="itable"><thead><tr><th scope="col">매체</th><th scope="col">분야</th><th scope="col">언어</th><th scope="col">최근 수집</th></tr></thead><tbody>{rows}</tbody></table></div>
    <ul class="srcs muted small">
      <li>크립토 시세·1분봉: Binance 공개 API(<a href="https://data-api.binance.vision" rel="nofollow">data-api.binance.vision</a>), 실패 시 Coinbase Exchange API</li>
      <li>국내 시세·공지: 업비트 공개 API</li>
      <li>공포·탐욕 지수: <a href="https://alternative.me/crypto/fear-and-greed-index/" rel="nofollow">alternative.me</a></li>
      <li>환율: <a href="https://www.exchangerate-api.com" rel="nofollow">Rates By Exchange Rate API</a></li>
      <li>경제 일정: <a href="https://www.forexfactory.com/calendar" rel="nofollow">Forex Factory</a>(이번 주), 과거 발표 시각은 <a href="https://fred.stlouisfed.org/releases/calendar" rel="nofollow">FRED 발표 일정</a>과 <a href="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm" rel="nofollow">연준 FOMC 일정</a></li>
      <li>업비트 공지는 GitHub 서버에서 막혀 Cloudflare 스케줄러를 거쳐 받습니다.</li>
    </ul>
  </section>
  <section class="panel"><h2 class="panel__title">유의 사항</h2><p>SIGNAL은 정보를 모아 보여 주는 서비스이며 투자 조언을 하지 않습니다. 가격 반응은 같은 시간대에 일어난 변화를 잰 값으로, 뉴스가 가격을 움직였다는 뜻이 아닙니다.</p></section>
</div>""".format(rows="".join(src_rows), nsrc=len(config.SOURCES))
    return shell("about", "소개·방법론", "SIGNAL이 뉴스를 모으고 가격 반응을 재는 방법과 데이터 출처.", B + "about/", body, now)


WIN_KO = {"15m": "15분", "1h": "1시간", "24h": "24시간"}
WIN_SEC = {"15m": 900, "1h": 3600, "24h": 86400}


def demo_items(articles, imp, now, n=5):
    """첫 화면 제품 미리보기에 쓸 실제 기사. 반응이 크게 잰 기사를 먼저, 모자라면 최근 측정 기사로 채운다."""
    by_id = {a["id"]: a for a in articles}
    picked = [by_id[r["id"]] for r in imp.get("strongest", []) if r["id"] in by_id]
    for a in articles:
        if len(picked) >= n:
            break
        if a.get("headline") and a not in picked and a.get("impact_status") != "skip":
            picked.append(a)
    out = []
    for a in picked[:n]:
        hd = a.get("headline") or {}
        asset = hd.get("asset") or (a.get("assets") or ["BTC"])[0]
        rx = {}
        for w in ("15m", "1h", "24h"):
            v = ((a.get("impact") or {}).get(asset) or {}).get(w)
            rx[w] = {"r": v["r"], "z": v.get("z"), "g": v.get("g")} if v and v.get("r") is not None else ({"due": a["t0"] + WIN_SEC[w]} if now < a["t0"] + WIN_SEC[w] else None)
        out.append({"id": a["id"], "t": a["title"], "src": a["source_name"], "cat": a["category"], "ts": a["t0"], "asset": asset, "adj": bool(hd.get("adj")),
                    "h": {k: hd.get(k) for k in ("asset", "win", "r", "g", "adj")} if hd else None, "rx": rx})
    return out


def demo_item_html(it, k):
    return ('<li><button class="demo__item" type="button" data-k="{k}" aria-pressed="{on}"><span class="di__meta"><span class="chip cat cat--{cat}">{cl}</span>'
            '<span class="di__src">{src} · {hm}</span></span><span class="di__t">{t}</span>{badge}</button></li>').format(
        k=k, on="true" if k == 0 else "false", cat=it["cat"], cl=config.CATEGORY_LABEL.get(it["cat"], it["cat"]), src=h(it["src"]), hm=hm(it["ts"]), t=h(it["t"]),
        badge=impact_badge({"headline": it["h"], "t0": it["ts"]}) if it["h"] else "")


def demo_detail_html(it):
    cells = []
    for w in ("15m", "1h", "24h"):
        v = it["rx"][w]
        if v and "r" in v:
            z = ("z %.1f" % v["z"]).replace("-", "−") if v.get("z") is not None else ""
            cells.append('<div><dt>{w}</dt><dd class="{d}">{r}</dd><span>{z}{g}</span></div>'.format(
                w=WIN_KO[w], d="up" if v["r"] >= 0 else "down", r=pct(v["r"]), z=z, g=(" · " + v["g"]) if v.get("g") else ""))
        else:
            cells.append('<div class="is-wait"><dt>{w}</dt><dd>{s}</dd><span>{n}</span></div>'.format(
                w=WIN_KO[w], s="측정 중" if v else "–", n="곧 반영" if v else "기록 없음"))
    return ('<div class="dd" data-sym="{asset}" data-t0="{ts}"><p class="dd__meta"><span class="chip cat cat--{cat}">{cl}</span><span>{src} · {when}</span></p>'
            '<p class="dd__title">{t}</p><div class="dd__chart" aria-hidden="true"></div>'
            '<dl class="dd__rx" aria-label="{asset} 가격 반응">{cells}</dl><a class="dd__link" href="{B}a/{id}/">기사와 차트 자세히 보기</a></div>').format(
        asset=h(it["asset"]), ts=it["ts"], cat=it["cat"], cl=config.CATEGORY_LABEL.get(it["cat"], it["cat"]), src=h(it["src"]), when=md_hm(it["ts"]),
        t=h(it["t"]), cells="".join(cells), B=B, id=h(it["id"]))


def bento(articles, market, cal, now, lst=None):
    day = [a for a in articles if now - a["t0"] < 86400]
    counts = [(c, sum(1 for a in day if a["category"] == c)) for c in ("crypto", "ai", "macro")]
    total = sum(n for _, n in counts) or 1
    share = "".join('<i class="cat-bar cat-bar--{c}" style="flex-grow:{n}"></i>'.format(c=c, n=n) for c, n in counts if n)
    legend = "".join('<li><i class="dot dot--{c}"></i>{l} <b>{n}</b></li>'.format(c=c, l=config.CATEGORY_LABEL[c], n=n) for c, n in counts)
    latest = "".join('<li><span class="chip cat cat--{c}">{l}</span><span>{t}</span></li>'.format(c=a["category"], l=config.CATEGORY_LABEL[a["category"]], t=h(a["title"])) for a in articles[:3])
    up = sorted([e for e in cal if e["ts"] > now], key=lambda e: e["ts"])[:3]
    cal_rows = "".join('<li><time>{d}</time><span>{t}</span><i class="lv lv--{lv}" aria-label="중요도 {lk}"></i></li>'.format(
        d=util.kst(e["ts"]).strftime("%m.%d %H:%M"), t=h(e.get("title_ko") or e["title"]), lv=e["level"], lk=h(e.get("level_ko", ""))) for e in up) \
        or '<li class="muted">이번 주에 남은 주요 발표가 없습니다</li>'
    kimp = market.get("kimp") or {}
    ks = [(s, kimp[s]["premium"]) for s in ("BTC", "ETH", "XRP", "SOL", "DOGE") if (kimp.get(s) or {}).get("premium") is not None]
    kmax = max([abs(v) for _, v in ks] or [1]) or 1
    kbars = "".join('<li><b>{s}</b><span class="kb"><i class="{d}" style="--v:{v:.3f}"></i></span><em class="{d}">{p}</em></li>'.format(
        s=s, d="up" if v >= 0 else "down", v=abs(v) / kmax, p=pct(v)) for s, v in ks) or '<li class="muted">김프 데이터를 기다리는 중입니다</li>'
    fng = market.get("fng") or {}
    fv = fng.get("value")
    hist = (fng.get("history") or [])[-30:]
    fbars = "".join('<i style="--v:%.2f;--k:%d"></i>' % (v / 100, k) for k, v in enumerate(hist))
    fng_ko = {"Extreme Fear": "극단적 공포", "Fear": "공포", "Neutral": "중립", "Greed": "탐욕", "Extreme Greed": "극단적 탐욕"}.get(fng.get("label"), fng.get("label") or "")
    nxt = up[0] if up else None
    watch_art = next((a for a in articles if "ETH" in a.get("assets", [])), None)
    ms = [x["m"] for x in (lst or {}).get("listings", []) if x.get("tc") and not x.get("stable") and not x.get("live") and x["m"].get("peak24") is not None]
    if len(ms) >= 10:
        pk = sorted(m["peak24"] for m in ms)[len(ms) // 2]
        dn = sum(1 for m in ms if (m.get("r1440") or 0) < 0) / len(ms)
        lst_q = "상장 직후 24시간 고점 중앙값 %s" % pct(pk, 0)
        lst_s = "%d건 중 %d%%는 하루 뒤 개시가 아래로 내려왔습니다." % (len(ms), round(dn * 100))
    else:
        lst_q, lst_s = "업비트 상장 해부도", "과거 원화 상장 직후 가격 곡선을 겹쳐 봅니다."
    return """
  <div class="bento">
    <a class="bx bx--feed" data-reveal style="--i:0" href="{B}live/">
      <div class="bx__head"><b class="bx__title">라이브</b><span class="mono-label">최근 24시간 {total}건</span></div>
      <p class="bx__desc">카테고리·반응 강도·관심 종목으로 걸러 봅니다. 새 기사가 들어오면 맨 위에 알려 줍니다.</p>
      <div class="catshare" aria-hidden="true">{share}</div>
      <ul class="catlegend">{legend}</ul>
      <ol class="bx__latest">{latest}</ol>
    </a>
    <a class="bx bx--cal" data-reveal style="--i:1" href="{B}events/">
      <div class="bx__head"><b class="bx__title">이벤트 리스크</b><span class="mono-label">다음 발표까지</span></div>
      <p class="bx__count" id="calCount" data-ts="{nts}">{ncount}</p>
      <ol class="mcal">{cal_rows}</ol>
      <p class="bx__desc">발표마다 과거에 BTC가 얼마나 흔들렸는지 함께 보여 줍니다.</p>
    </a>
    <a class="bx" data-reveal style="--i:2" href="{B}live/">
      <div class="bx__head"><b class="bx__title">김치 프리미엄</b><span class="mono-label">업비트 대비 해외</span></div>
      <ul class="mkimp">{kbars}</ul>
    </a>
    <a class="bx" data-reveal style="--i:3" href="{B}live/">
      <div class="bx__head"><b class="bx__title">공포·탐욕 지수</b><span class="mono-label">30일</span></div>
      <div class="mfng"><svg viewBox="0 0 120 66" aria-hidden="true"><path class="mfng__track" d="M10 60a50 50 0 0 1 100 0" pathLength="100"/><path class="mfng__fill" d="M10 60a50 50 0 0 1 100 0" pathLength="100" style="--v:{fv100}"/></svg><p><b>{fv}</b><span>{fng_ko}</span></p></div>
      <div class="mfng__hist" aria-hidden="true">{fbars}</div>
    </a>
    <a class="bx" data-reveal style="--i:4" href="{B}listings/">
      <div class="bx__head"><b class="bx__title">상장 레이더</b><span class="mono-label">업비트 원화 상장</span></div>
      <p class="bx__q">{lst_q}<span>{lst_s}</span></p>
    </a>
    <a class="bx" data-reveal style="--i:5" href="{B}me/">
      <div class="bx__head"><b class="bx__title">관심 종목</b><span class="mono-label">로그인 없이 저장</span></div>
      <div class="mwatch" aria-hidden="true"><span>BTC</span><span class="is-on">ETH ★</span><span>SOL</span><span>XRP</span></div>
      <p class="mwatch__card"><span class="chip">ETH</span><span>{wtitle}</span></p>
    </a>
  </div>""".format(B=B, total=len(day), share=share, legend=legend, latest=latest, nts=nxt["ts"] if nxt else 0,
                   ncount="--:--:--" if nxt else "예정 없음", cal_rows=cal_rows, kbars=kbars,
                   fv=fv if fv is not None else "–", fv100=fv if fv is not None else 0, fng_ko=h(fng_ko), fbars=fbars,
                   lst_q=lst_q, lst_s=lst_s,
                   wtitle=h(watch_art["title"]) if watch_art else "이더리움 관련 새 기사")


def story_data(articles, demo):
    """스크롤 고정 섹션에 쓸 실제 기사·반응값."""
    feed = "".join('<li style="--k:%d"><span class="chip cat cat--%s">%s</span><span class="sc1__t">%s</span><em>%s</em></li>'
                   % (k, a["category"], config.CATEGORY_LABEL[a["category"]], h(a["title"]), h(a["source_name"])) for k, a in enumerate(articles[:6]))
    src = "".join('<li style="--k:%d">%s</li>' % (k, h(x["name"])) for k, x in enumerate(config.SOURCES[:10]))
    f = demo[0] if demo else None
    wins = [(w, f["rx"][w]) for w in ("15m", "1h", "24h") if f and f["rx"].get(w) and "r" in f["rx"][w]] if f else []
    best = max(wins, key=lambda x: abs(x[1].get("z") or 0)) if wins else None
    z = abs(best[1].get("z") or 0) if best else 0
    pos = z / 4 if z <= 3 else 0.75 + min((z - 3) / 6, 1) * 0.25
    marks = "".join('<span class="mk" data-win="{w}"><i></i><span>{l} <b class="{d}">{r}</b></span></span>'.format(
        w=w, l=WIN_KO[w], d="up" if v["r"] >= 0 else "down", r=pct(v["r"])) for w, v in wins if w in ("15m", "1h"))
    if best:
        w, v = best
        badge = '<span class="ib ib--{d} ib--g{g}">{a} {w} {r} · {gr}</span>'.format(d="up" if v["r"] >= 0 else "down", g={"강": "s", "중": "m"}.get(v.get("g"), "w"),
                                                                                    a=h(f["asset"]), w=WIN_KO[w], r=pct(v["r"]), gr=h(v.get("g") or ""))
        cap = "기사 뒤 %s 동안의 움직임이 평소 같은 길이 변동폭의 %.1f배였습니다." % (WIN_KO[w], z)
    else:
        badge, cap = "", "반응이 측정되면 여기에 표시됩니다."
    fmt = {"sc_src": src, "sc_feed": feed, "sc_asset": h(f["asset"]) if f else "BTC", "sc_cat": f["cat"] if f else "crypto",
           "sc_cl": config.CATEGORY_LABEL.get(f["cat"], "") if f else "", "sc_title": h(f["t"]) if f else "", "sc_marks": marks,
           "sc_z": ("%.1f" % ((best[1].get("z") or 0) if best else 0)), "sc_cap": cap, "sc_pos": "%.3f" % min(pos, 1), "sc_badge": badge}
    js = {"asset": f["asset"], "ts": f["ts"]} if f else None
    return {"fmt": fmt, "js": js}


def hero_snapshot():
    """첫 화면 렌더에 쓴 고정 데이터(렌더 시점의 7일 BTC·뉴스 핀). 없으면 None."""
    path = os.path.join(WEB, "assets", "hero", "snapshot.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def outro_wall(day, rows=9):
    """마지막 섹션 배경: 최근 24시간 기사 제목을 줄줄이 흘린다. 가격을 크게 움직인 기사(강·중)는 스크롤하면 신호로 남는다."""
    sig = [a for a in day if (a.get("headline") or {}).get("g") in ("강", "중")][:12]
    rest = [a for a in day if a not in sig][:rows * 7 - len(sig)]
    pool = sorted(sig + rest, key=lambda a: util.short_hash(a["id"]))
    def item(a):
        hd = a.get("headline") if a in sig else None
        t = a["title"] if len(a["title"]) <= 64 else a["title"][:62].rstrip() + "…"
        tail = '<b>%s %s %s</b>' % (h(hd["asset"]), hd["win"], pct(hd["r"])) if hd else ""
        return '<span class="ow__i%s">%s%s</span>' % (" is-sig" if hd else "", h(t), tail)
    # 줄마다 글자 크기를 달리해 겹겹이 쌓인 깊이를 준다(1440px 기준 px)
    sizes = [24, 16, 36, 19, 15, 29, 17, 22, 32]
    out = []
    for r in range(rows):
        line = "".join(item(a) for a in pool[r::rows]) or ""
        # 같은 줄을 두 번 이어 붙여 끊김 없이 흐르게 한다. 큰 줄일수록 천천히
        fs = sizes[r % len(sizes)]
        out.append('<div class="ow__row" style="--t:%ds;--fs:%d"><div class="ow__track">%s%s</div></div>' % (60 + fs * 2 + (r * 7) % 15, fs, line, line))
    return "".join(out), len(sig)


def page_landing(articles, market, cal, imp, now, lst=None):
    """첫 화면. 숫자와 기사는 모두 실제 수집·측정값이다."""
    day = [a for a in articles if now - a["t0"] < 86400]
    measured = sum(1 for a in articles if a.get("headline"))
    demo = demo_items(articles, imp, now)
    strong = [r for r in imp.get("strongest", []) if r.get("g") in ("강", "중")][:6] or imp.get("strongest", [])[:6]
    types = (imp.get("types") or [])[:6]
    proof = "".join(
        '<article class="proof"><div class="proof__meta"><span class="ib ib--{d} ib--g{g}">{asset} {win} {adj}{r}{gl}</span><span class="muted small">z {z} · <time data-ts="{t0}">{when}</time></span></div>'
        '<h3 class="proof__title"><a href="{B}a/{id}/">{title}</a></h3>'
        '<div class="proof__chart" data-sym="{asset}" data-t0="{t0}" aria-hidden="true"></div></article>'.format(
            d="up" if r["r"] >= 0 else "down", g={"강": "s", "중": "m"}.get(r["g"], "w"), asset=h(r["asset"]), win=WIN_KO.get(r["win"], r["win"]), r=pct(r["r"]), adj="시장 대비 " if r.get("adj") else "",
            gl=(" · " + r["g"]) if r.get("g") else "", z=("%.1f" % r["z"]).replace("-", "−"), t0=r["t0"], when=md_hm(r["t0"]), B=B, id=h(r["id"]), title=h(r["title"]), i=i)
        for i, r in enumerate(strong)) or '<p class="muted">반응이 측정되면 실제 사례가 여기에 나타납니다.</p>'
    top_abs = max([t["mean_abs"] for t in types] or [1]) or 1
    bars = "".join(
        '<li class="tbar" data-label="{label}" data-val="{raw:.3f}" data-n="{n}"><span class="tbar__label">{label}</span><span class="tbar__track"><i style="--v:{v:.3f}"></i></span><span class="tbar__val">{val} <span class="muted">n={n}</span></span></li>'.format(
            label=h(t["label"]), v=t["mean_abs"] / top_abs, raw=t["mean_abs"], val=pct(t["mean_abs"]).lstrip("+"), n=t["n"]) for t in types) \
        or '<li class="muted">유형별 표본이 쌓이는 중입니다.</li>'
    sc = story_data(articles, demo)
    snap = hero_snapshot()
    # 파문 영상이 아직 없으면(렌더 워크플로 실행 전) 글자만 둔다
    video_ready = all(os.path.isfile(os.path.join(WEB, "assets", "hero", "ripple-%s.mp4" % v)) for v in ("desktop", "mobile"))
    video_attr = ' data-video="%sassets/hero/"' % B if video_ready else ""
    span_label = ("%s – %s" % (util.kst(snap["start"]).strftime("%m.%d"), util.kst(snap["end"]).strftime("%m.%d"))) if snap else ""
    drop_note = ("%s · 지난 뉴스 %d건의 실제 반응 크기로 떨어뜨린 파문" % (span_label, len(snap["pins"]))) if snap else "15분 · 1시간 · 24시간"
    wall, nsig = outro_wall(day)
    # 마지막 "Signal" 글자 안에도 첫 화면의 파문이 비친다
    fill = ' style="--fill:url(%sassets/hero/ripple-desktop.webp)"' % B if video_ready else ""
    say_words = "뉴스는 매일 수백 건씩 쏟아집니다. 그중 [가격을 실제로 움직인] 뉴스는 일부뿐입니다. SIGNAL은 그 일부를 [숫자로] 골라 보여 줍니다.".split(" ")
    say, hot = [], False
    for w in say_words:
        st = w.startswith("[")
        hot = hot or st
        say.append('<span class="sw%s">%s</span>' % (" sw--hot" if hot else "", h(w.strip("[]"))))
        if w.endswith("]"):
            hot = False
    rank0 = types[0] if types else None
    words = "뉴스 뒤의 가격 반응까지 한눈에".split(" ")
    title = " ".join('<span class="w" style="--s:%d">%s</span>' % (i + 1, h(w)) for i, w in enumerate(words))
    srcs = "".join('<li style="--j:%d">%s</li>' % (k, h(x["name"])) for k, x in enumerate(config.SOURCES[:8]))
    demo_html = """
  <div class="wrap in" style="--s:{sd}">
    <div class="demo" id="demo">
      <div class="demo__inner">
        <div class="demo__bar"><b class="demo__brand">SIGNAL</b><span class="demo__tabs" aria-hidden="true"><span class="is-on">전체</span><span>크립토</span><span>AI</span><span>매크로</span></span><span class="demo__step" aria-hidden="true"></span><span class="demo__live"><span class="live-dot" aria-hidden="true"></span>실시간</span></div>
        <div class="demo__body">
          <ol class="demo__list" aria-label="반응이 큰 최근 기사">{items}</ol>
          <div class="demo__detail" id="demoDetail">{detail}</div>
        </div>
      </div>
    </div>
  </div>""".format(sd=len(words) + 3, items="".join(demo_item_html(it, k) for k, it in enumerate(demo)), detail=demo_detail_html(demo[0])) if demo else ""
    body = """
<section class="hx" id="hx" data-theme="dark"{video_attr} aria-labelledby="heroTitle">
  <div class="pin hx__pin">
    <canvas class="hx__canvas" aria-hidden="true"></canvas>
    <div class="hx__scrim" aria-hidden="true"></div>
    <div class="wrap hx__layer">
      <div class="hx__top" data-beat="-1,0,0.04,0.1">
        <p class="hero__live in" style="--s:0"><span class="live-dot" aria-hidden="true"></span>실시간 수집 중 · 마지막 <time data-ts="{now}">{now_hm}</time></p>
        <span class="mono-label hx__tag in" style="--s:1">News → Price reaction</span>
      </div>
      <div class="hx__slot"><p class="hx__word in" style="--s:1" aria-hidden="true"><span>SIG</span><span>NAL</span></p></div>
      <div class="hx__copy" data-beat="-1,0,0.04,0.1">
        <h1 class="hx__title in" id="heroTitle" style="--s:3">모든 뉴스는<br>파문을 남깁니다</h1>
        <div class="hx__side in" style="--s:4">
          <p class="hx__sub">크립토·AI·매크로 뉴스가 나온 뒤 <span class="nw">15분·1시간·24시간</span> 동안 가격이 얼마나 움직였는지 재서 보여 줍니다.</p>
          <div class="hero__cta"><a class="btn btn--accent btn--lg" href="{B}map/">뉴스 영향 보기</a><a class="btn btn--ghost btn--lg" href="{B}live/">라이브 보기</a></div>
        </div>
      </div>
      <div class="hx__cap" data-beat="0.7,0.8,2,3"><span class="mono-label">{drop_note}</span><b>SIGNAL은 그 파문의<br>크기를 잽니다.</b></div>
    </div>
    <p class="hx__hint" data-beat="-1,0,0.02,0.06" aria-hidden="true">아래로 스크롤</p>
  </div>
</section>

<section class="hero hero--preview" id="demoPin" aria-label="제품 미리보기">
  <div class="pin demo-pin">
{demo}
  </div>
</section>
<section class="hero hero--stats" aria-label="수집 현황">
  <div class="wrap">
    <dl class="hero__stats in" style="--s:{s3}">
      <div><dt>최근 24시간 기사</dt><dd class="count" data-to="{n24}">{n24}</dd></div>
      <div><dt>수집 매체</dt><dd class="count" data-to="{nsrc}">{nsrc}</dd></div>
      <div><dt>반응을 잰 기사</dt><dd class="count" data-to="{measured}">{measured}</dd></div>
    </dl>
  </div>
</section>

<div id="how" class="how">
<section class="story" id="story" aria-labelledby="howTitle">
  <div class="story__pin">
    <div class="wrap story__grid">
      <div class="story__text">
        <h2 class="lsec__title" id="howTitle">How we measure</h2>
        <ol class="story__steps">
          <li class="is-on"><span class="story__n">01</span><b>Collect</b><p>국내외 {nsrc}개 매체를 15분마다 모으고, 중복과 공지성 기사를 거른 뒤 크립토·AI·매크로로 나눕니다.</p></li>
          <li><span class="story__n">02</span><b>Measure</b><p>기사 시각부터 15분·1시간·24시간 뒤 가격을 1분봉으로 잽니다.</p></li>
          <li><span class="story__n">03</span><b>Score</b><p>평소 변동폭의 몇 배였는지(z)로 약·중·강을 매깁니다. 같은 시간대의 변화일 뿐, 뉴스가 원인이라는 뜻은 아닙니다.</p></li>
        </ol>
        <div class="story__bar" aria-hidden="true"><i></i></div>
      </div>
      <div class="story__stage" aria-hidden="true">
        <div class="story__screen">
          <div class="sc sc1">
            <p class="sc__label"><span class="live-dot"></span>{nsrc}개 매체에서 수집 중</p>
            <ul class="sc1__src">{sc_src}</ul>
            <ol class="sc1__feed">{sc_feed}</ol>
            <p class="sc1__count"><b data-to="{n24}">{n24}</b><span>최근 24시간 기사</span></p>
          </div>
          <div class="sc sc2">
            <p class="sc__label">기사 시각 기준 {sc_asset} 가격</p>
            <div class="sc2__card"><span class="chip cat cat--{sc_cat}">{sc_cl}</span><b>{sc_title}</b></div>
            <div class="sc2__chart"><svg viewBox="0 0 600 240" preserveAspectRatio="none"></svg><span class="sc2__t0">기사 시각</span>{sc_marks}</div>
          </div>
          <div class="sc sc3">
            <p class="sc__label">평소 변동폭과 비교</p>
            <p class="sc3__z">z <b data-z="{sc_z}">0.0</b></p>
            <p class="sc3__cap">{sc_cap}</p>
            <div class="sc3__scale"><span>약</span><span>중</span><span>강</span><div class="sc3__run" data-pos="{sc_pos}"><i></i></div></div>
            <p class="sc3__badge">{sc_badge}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
<section class="lsec wrap how-static" aria-labelledby="howTitle2">
  <h2 class="lsec__title" id="howTitle2" data-reveal>How we measure</h2>
  <p class="lsec__lede" data-reveal style="--i:1">감으로 고른 ‘중요 뉴스’가 아니라, 기사가 나온 뒤 실제 가격 변화를 기준으로 보여 줍니다.</p>
  <ol class="steps3">
    <li data-reveal style="--i:0"><span class="steps3__n">01</span><b>Collect</b><p>국내외 {nsrc}개 매체를 15분마다 모으고, 중복과 공지성 기사를 거른 뒤 크립토·AI·매크로로 나눕니다.</p><ul class="steps3__src" aria-label="수집 매체 일부">{srcs}</ul></li>
    <li data-reveal style="--i:1"><span class="steps3__n">02</span><b>Measure</b><p>기사 시각을 기준으로 15분·1시간·24시간 뒤 가격을 1분봉으로 잽니다.</p>
      <div class="steps3__time" aria-hidden="true"><i class="is-t0"></i><span>기사</span><i></i><span>15분</span><i></i><span>1시간</span><i></i><span>24시간</span></div></li>
    <li data-reveal style="--i:2"><span class="steps3__n">03</span><b>Score</b><p>평소 변동폭의 몇 배였는지(z)로 약·중·강을 매깁니다. 같은 시간대의 변화일 뿐, 뉴스가 원인이라는 뜻은 아닙니다.</p>
      <div class="steps3__scale" aria-hidden="true"><span>약 <small>|z| 2 미만</small></span><span>중 <small>2–3</small></span><span>강 <small>3 이상</small></span></div></li>
  </ol>
</section>

</div>

<section class="hscroll" id="proofPin" aria-labelledby="proofTitle">
  <div class="pin hscroll__pin">
    <div class="wrap hscroll__head">
      <div><h2 class="lsec__title" id="proofTitle">최근 7일, 크게 움직인 순간</h2><p class="lsec__lede">반응이 컸던 기사 {nproof}건입니다. 차트의 점선이 기사 시각입니다.</p></div>
      <p class="hscroll__count" aria-hidden="true"><b>01</b> / {nproof2}</p>
    </div>
    <div class="hscroll__viewport"><div class="hscroll__track proofs">{proof}</div></div>
    <div class="wrap"><div class="hscroll__bar" aria-hidden="true"><i></i></div></div>
  </div>
</section>

<section class="rank" id="rankPin" aria-labelledby="typesTitle">
  <div class="pin rank__pin">
    <div class="wrap lsplit">
      <div class="rank__side"><h2 class="lsec__title" id="typesTitle">어떤 뉴스가 더 크게 움직였나</h2><p class="lsec__lede">이벤트 유형별 BTC 1시간 평균 변동폭입니다. 측정이 쌓일수록 정확해집니다.</p>
        <div class="rank__now" aria-hidden="true"><span class="mono-label">유형</span><b class="rank__label">{rank0_label}</b><b class="rank__val">{rank0_val}</b><span class="rank__n">{rank0_n}</span></div>
        <a class="btn btn--ghost rank__more" href="{B}patterns/">패턴에서 더 보기</a></div>
      <ol class="tbars" id="tbars">{bars}</ol>
    </div>
  </div>
</section>

<section class="lsec wrap" aria-labelledby="featTitle">
  <h2 class="lsec__title" id="featTitle" data-reveal>매일 확인할 것들</h2>
  <p class="lsec__lede" data-reveal style="--i:1">아래 숫자는 모두 지금 수집된 실제 데이터입니다.</p>
{feats}
</section>

<section class="say" id="sayPin" aria-label="SIGNAL이 하는 일">
  <div class="pin say__pin"><div class="wrap"><p class="say__text">{say}</p></div></div>
</section>

<section class="outro" id="outro" data-theme="dark" aria-labelledby="ctaTitle">
  <div class="pin outro__pin">
    <div class="outro__wall" aria-hidden="true">{wall}</div>
    <div class="outro__veil" aria-hidden="true"></div>
    <div class="wrap outro__body">
      <p class="mono-label outro__kicker">최근 24시간 기사 {n24}건 · 가격을 크게 움직인 기사 {nsig}건</p>
      <h2 class="outro__title" id="ctaTitle"><span class="ot__l ot__l--noise"><span>Noise out.</span></span><span class="ot__l ot__l--sig"><span><em class="ot__fill"{fill}>Signal</em> in.</span></span></h2>
      <div class="outro__foot">
        <p>회원가입 없이 무료로 씁니다. 투자 조언은 하지 않습니다.</p>
        <div class="outro__cta"><a class="btn btn--accent btn--lg" href="{B}map/">뉴스 영향 보기</a><a class="btn btn--ghost btn--lg" href="{B}live/">라이브 보기</a></div>
      </div>
    </div>
  </div>
</section>""".format(
        now=now, now_hm=md_hm(now), B=B, title=title, s1=len(words) + 1, s2=len(words) + 2, s3=len(words) + 4, demo=demo_html,
        n24=len(day), nsrc=len(config.SOURCES), measured=measured, srcs=srcs, proof=proof, bars=bars, feats=bento(articles, market, cal, now, lst), say=" ".join(say), video_attr=video_attr, drop_note=h(drop_note), wall=wall, nsig=nsig, fill=fill,
        nproof=len(strong), nproof2="%02d" % len(strong),
        rank0_label=h(rank0["label"]) if rank0 else "–", rank0_val=pct(rank0["mean_abs"]).lstrip("+") if rank0 else "–",
        rank0_n=("표본 %d건" % rank0["n"]) if rank0 else "", **sc["fmt"])
    data = {"landing": {"demo": demo, "story": sc["js"]}}
    head3d = ('<link rel="preload" as="image" href="%sassets/hero/ripple-desktop.webp" media="(min-aspect-ratio: 4/5)">\n'
              '<link rel="preload" as="image" href="%sassets/hero/ripple-mobile.webp" media="(max-aspect-ratio: 4/5)">\n'
              '<script type="module" src="%sassets/hero.js?v=%s"></script>' % (B, B, B, ASSET_VER)) if video_ready else (
              '<script type="module" src="%sassets/hero.js?v=%s"></script>' % (B, ASSET_VER))
    return shell("home", "SIGNAL — 뉴스 뒤의 가격 반응까지", "크립토·AI·매크로 뉴스를 모으고, 기사마다 비트코인 가격이 실제로 얼마나 움직였는지 재서 보여 줍니다.",
                 B, body, now, extra_head=head3d, data=data)


def page_map(market, now):
    """뉴스 영향(/map/). 시장 물결 → 실제와 '시장만 따랐다면'의 차이 → 24시간 변동 영수증 → 오늘의 큰 움직임.
    그림은 assets/moves.js가 data/moves.json(pipeline/moves.py)을 읽어 그린다."""
    icons = ",".join(sorted(f[:-4] for f in os.listdir(os.path.join(WEB, "assets", "coins")) if f.endswith(".svg")))
    body = """
<section class="im wrap" id="im" data-src="{B}data/moves.json" data-icons="{icons}" aria-labelledby="imTitle">
  <header class="im-hero">
    <p class="im-asof" id="imAsof"></p>
    <h1 class="im-title" id="imTitle">오늘 뉴스에 반응한 코인</h1>
    <p class="im-lede" id="imLede"></p>
  </header>
  <p class="im-empty-page" id="imEmpty" hidden>데이터를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요.</p>
  <ol class="im-cards" id="imCards" aria-label="뉴스에 반응한 움직임"></ol>
  <details class="im-more" id="imMore">
    <summary><span id="imMoreTitle">뉴스 없이 크게 움직인 코인</span><span class="im-more__hint">원인 뉴스를 찾지 못한 움직임 · 그 전 24시간 소식은 참고로만</span></summary>
    <ol class="im-quiet" id="imQuiet"></ol>
  </details>
  <details class="im-how">
    <summary>어떻게 쟀나요</summary>
    <ol class="im-steps">
      <li><span><b>시장대로였다면</b>그 코인을 뺀 나머지 코인 24개(시총 가중)가 같은 시간에 움직인 만큼 × 그 코인이 평소 시장을 따라가는 정도(최근 30일).</span></li>
      <li><span><b>혼자 움직인 만큼</b>실제 − 시장대로였다면. 60분 동안 평소 흔들림의 2.5배를 넘으면 ‘크게 움직였다’고 봅니다.</span></li>
      <li><span><b>원인 뉴스</b>움직임 시작 30분 전부터 5분 뒤까지 나온 뉴스 중 그 코인을 직접 언급한 것(제목, 없으면 본문 첫머리). 여러 건이면 어느 것 때문인지 확실하지 않다고 표시합니다.</span></li>
    </ol>
    <p class="im-note">같은 시간대의 통계적 연관이며 인과를 보장하지 않습니다. <a href="{B}about/#method">계산 방법 자세히</a></p>
  </details>
  <template id="imDetailTpl">
    <div class="im-detail">
      <div class="im-legend" aria-hidden="true"><span><i class="im-lg im-lg--actual"></i>실제</span><span><i class="im-lg im-lg--market"></i>시장대로였다면</span><span><i class="im-lg im-lg--event"></i>이 움직임</span></div>
      <div class="im-chart"><svg role="img"></svg><div class="im-hover" hidden></div></div>
      <p class="im-day"></p>
    </div>
  </template>
</section>""".format(B=B, icons=icons)
    head = '<script type="module" src="%sassets/moves.js?v=%s"></script>' % (B, ASSET_VER)
    return shell("map", "뉴스 영향 — 오늘 뉴스에 반응한 코인", "오늘 어떤 뉴스 뒤에 어떤 코인이 시장보다 얼마나 더 움직였는지 한 줄로 보여 줍니다.", B + "map/", body, now, extra_head=head)


def page_listings(now):
    """상장 레이더: 업비트 거래 공지 목록 + 상장 해부도. 그림과 목록은 assets/listings.js가 data/listings.json을 읽어 그린다."""
    proxy = config.UPBIT_NOTICES_PROXY[: -len("/upbit-notices")] if config.UPBIT_NOTICES_PROXY.endswith("/upbit-notices") else ""
    seg = lambda name, opts, on: "".join(
        '<button type="button" class="mseg__b" data-{n}="{v}" aria-pressed="{p}">{l}</button>'.format(n=name, v=v, l=l, p="true" if v == on else "false")
        for v, l in opts)
    body = """
<section class="lst wrap" id="lst" data-src="{B}data/listings.json" data-proxy="{proxy}" aria-labelledby="lstTitle">
  <header class="phead"><h1 class="phead__title" id="lstTitle">상장 레이더</h1>
    <p class="muted">업비트 원화 마켓 상장 직후 가격이 과거에 어떻게 움직였는지 겹쳐 보고, 지금 상장과 비교합니다.</p></header>
  <div class="lst__now" id="lstNow" aria-live="polite"></div>
  <section class="lst__anat panel" aria-labelledby="anatTitle">
    <div class="lst__bar">
      <h2 class="panel__title" id="anatTitle">상장 해부도</h2>
      <div class="mseg" role="group" aria-label="기준 시점">{tab}</div>
    </div>
    <div class="lst__filters">
      <div class="mseg" role="group" aria-label="기간">{period}</div>
      <div class="mseg" role="group" aria-label="바이낸스 상장 여부">{bn}</div>
      <div class="mseg" role="group" aria-label="상장 방식">{mode}</div>
    </div>
    <dl class="lst__stats" id="lstStats"></dl>
    <div class="lst__chart" id="lstChart"><canvas id="lstCanvas" aria-hidden="true"></canvas><div class="lst__tip" id="lstTip" hidden></div></div>
    <p class="lst__axis small muted" id="lstAxis"></p>
    <p class="lst__note small muted" id="lstNote"></p>
  </section>
  <section class="lst__notices panel" aria-labelledby="ntcTitle">
    <div class="lst__bar"><h2 class="panel__title" id="ntcTitle">업비트 거래 공지</h2><div class="mseg" role="group" aria-label="공지 종류">{kind}</div></div>
    <div class="lst__tablewrap"><table class="lst__table"><thead><tr><th scope="col">공지 시각</th><th scope="col">종류</th><th scope="col">코인</th><th scope="col">제목</th><th scope="col">거래 개시 후 24시간 고점</th><th scope="col">24시간 뒤</th></tr></thead><tbody id="lstRows"></tbody></table></div>
    <button class="btn btn--ghost lst__more" id="lstMore" type="button" hidden>더 보기</button>
  </section>
</section>""".format(B=B, proxy=h(proxy),
                     tab=seg("tab", [("trade", "거래 개시 후 · 업비트"), ("notice", "공지 직후 · 바이낸스")], "trade"),
                     period=seg("period", [("1", "최근 1년"), ("2", "최근 2년"), ("all", "전체")], "2"),
                     bn=seg("bn", [("all", "전체"), ("yes", "바이낸스 상장 코인"), ("no", "바이낸스 미상장")], "all"),
                     mode=seg("mode", [("all", "전체"), ("new", "업비트 첫 상장"), ("added", "원화 마켓 추가")], "all"),
                     kind=seg("kind", [("all", "전체"), ("listing", "신규 상장"), ("caution", "유의 종목"), ("delisting", "거래지원 종료")], "all"))
    head = '<script type="module" src="%sassets/listings.js?v=%s"></script>' % (B, ASSET_VER)
    return shell("listings", "상장 레이더 — 업비트 상장 해부도", "업비트 원화 상장 직후 가격이 과거에 어떻게 움직였는지 겹쳐 보고 지금 상장과 비교합니다.",
                 B + "listings/", body, now, extra_head=head)


def _ev_card(u, now):
    """다가오는 발표 카드 하나."""
    st = u.get("stats") or {}
    lv = "상" if u["level"] >= 3 else "중"
    det = "".join('<li><span>{t}</span><span class="muted">{f}{p}</span></li>'.format(
        t=h(d["title_ko"]), f=("예상 %s" % h(d["forecast"])) if d.get("forecast") else "", p=(" · 이전 %s" % h(d["previous"])) if d.get("previous") else "")
        for d in u.get("detail") or [])
    if st.get("abs1h"):
        a1, a15 = st["abs1h"], st.get("abs15") or {}
        bars = "".join('<i class="{d}" style="--v:{v:.3f}" title="{when} {r}"></i>'.format(
            d="up" if r["r1h"] >= 0 else "down", v=min(1, abs(r["r1h"]) / max(a1["max"], 0.01)), when=util.kst(r["ts"]).strftime("%Y.%m.%d"), r=pct(r["r1h"]))
            for r in st.get("recent") or [])
        vs = ('<span class="evr__vs">평소 같은 시간대의 <b>%.1f배</b></span>' % u["vs_normal"]) if u.get("vs_normal") else ""
        stats = """<div class="evr__stats">
  <div class="evr__max"><dt>과거 1시간 최대 폭</dt><dd>±{mx}</dd></div>
  <dl class="evr__grid"><div><dt>1시간 중앙값</dt><dd>±{m1}</dd></div><div><dt>1시간 90%</dt><dd>±{p1}</dd></div><div><dt>15분 중앙값</dt><dd>{m15}</dd></div><div><dt>상승 비율</dt><dd>{up}%</dd></div></dl>
  <div class="evr__bars" aria-label="최근 {nr}회 발표 1시간 변동">{bars}</div>
  <p class="small muted">최근 {n}회 발표 기준 BTC · 가장 컸던 날 {big} ({bigr}) {vs}</p></div>""".format(
            mx=pct(a1["max"]).lstrip("+"), m1=pct(a1["med"]).lstrip("+"), p1=pct(a1["p90"]).lstrip("+"),
            m15=("±" + pct(a15["med"]).lstrip("+")) if a15 else "–", up=round(st["up"] * 100), nr=len(st.get("recent") or []), bars=bars, n=st["n"],
            big=util.kst(st["biggest"]["ts"]).strftime("%Y.%m.%d"), bigr=pct(st["biggest"]["r1h"]), vs=vs)
    elif u.get("kind"):
        stats = '<p class="small muted evr__weak">표본 부족(n=%d) · 8회 이상 쌓이면 과거 흔들림 폭을 보여 줍니다.</p>' % (st.get("n") or 0)
    else:
        stats = '<p class="small muted evr__weak">과거 통계를 모으지 않는 일정입니다.</p>'
    after = ""
    if u["ts"] <= now and u.get("reaction"):
        after = '<p class="evr__after">발표 후 BTC ' + " · ".join('%s <b class="%s">%s</b>' % ("15분" if w == "15m" else "1시간", "up" if v >= 0 else "down", pct(v))
                                                             for w, v in u["reaction"].items()) + "</p>"
    elif u["ts"] <= now:
        after = '<p class="evr__after muted">발표 후 반응을 재는 중입니다.</p>'
    return """<article class="evr{past}" id="ev-{key}" data-ts="{ts}"><header class="evr__head"><span class="lvb lvb--{lvc}">{lv}</span>
  <h3 class="evr__name">{name}</h3><p class="evr__when"><time>{when}</time> · <span class="evr__left" data-left="{ts}"></span></p></header>
  {det}{stats}{after}</article>""".format(past=" is-past" if u["ts"] <= now else "", key=h(str(u.get("kind") or "x")) + "-" + str(u["ts"]), ts=u["ts"],
                                          lvc=u["level"], lv=lv, name=h(u["name"]), when=util.kst(u["ts"]).strftime("%m.%d(%a) %H:%M").replace("Mon", "월").replace("Tue", "화").replace("Wed", "수").replace("Thu", "목").replace("Fri", "금").replace("Sat", "토").replace("Sun", "일"),
                                          det=('<ul class="evr__det">%s</ul>' % det) if det else "", stats=stats, after=after)


def page_events(ev, now):
    """이벤트 리스크: 위험 시계(레이더) + 다가오는 발표의 과거 흔들림 폭."""
    ev = ev or {"upcoming": [], "kinds": []}
    up = [u for u in ev.get("upcoming", []) if u["ts"] >= now - 2 * 3600 and u["ts"] <= now + 8 * 86400]
    cards = "".join(_ev_card(u, now) for u in up) or '<p class="empty">다가오는 주요 발표가 없습니다.</p>'
    rows = "".join("<tr><th scope=\"row\">{n}</th><td>{c}</td><td>{m}</td><td>{p}</td><td>{x}</td><td>{u}</td></tr>".format(
        n=h(k["name"]), c=k["n"], m=("±" + pct(k["abs1h"]["med"]).lstrip("+")) if k.get("abs1h") else "–",
        p=("±" + pct(k["abs1h"]["p90"]).lstrip("+")) if k.get("abs1h") else "–", x=("±" + pct(k["abs1h"]["max"]).lstrip("+")) if k.get("abs1h") else "–",
        u=("%d%%" % round(k["up"] * 100)) if k.get("abs1h") else "–") for k in ev.get("kinds", []))
    radar = [{"ts": u["ts"], "name": u["name"], "level": u["level"], "id": "ev-%s-%d" % (u.get("kind") or "x", u["ts"]),
              "med": (u.get("stats") or {}).get("abs1h", {}).get("med") if (u.get("stats") or {}).get("abs1h") else None} for u in up]
    body = """
<div class="wrap evp">
  <header class="phead"><h1 class="phead__title">이벤트 리스크</h1><p class="muted">다가오는 미국 주요 발표에서 BTC가 과거에 얼마나 흔들렸는지 봅니다. 시각은 한국 시간.</p></header>
  <section class="evp__top">
    <div class="radar" id="radar"><canvas id="radarCanvas" aria-hidden="true"></canvas><div class="radar__center" id="radarCenter" aria-live="polite"></div></div>
    <div class="evp__legend">
      <div class="mseg" role="group" aria-label="레이더 범위"><button type="button" class="mseg__b" data-span="24" aria-pressed="true">다음 24시간</button><button type="button" class="mseg__b" data-span="168" aria-pressed="false">7일</button></div>
      <p class="small muted">시계 12시 방향이 지금이고, 시계 방향으로 시간이 흐릅니다. 원의 크기는 과거 같은 발표 뒤 BTC 1시간 변동폭의 중앙값입니다. 원을 누르면 그 발표 카드로 갑니다.</p>
      <p class="small muted">{note}</p>
    </div>
  </section>
  <section class="evp__cards">{cards}</section>
  <section class="panel evp__kinds"><h2 class="panel__title">발표 종류별 과거 흔들림(BTC 1시간)</h2>
    <div class="lst__tablewrap"><table class="mtable"><thead><tr><th scope="col">발표</th><th scope="col">표본</th><th scope="col">중앙값</th><th scope="col">90%</th><th scope="col">최대</th><th scope="col">상승 비율</th></tr></thead><tbody>{rows}</tbody></table></div>
    <p class="small muted">출처: FRED 발표 일정(CPI·PPI·고용·PCE·GDP·소매판매·실업수당), 연준 FOMC 일정, 이후 회차는 Forex Factory 주간 일정. ISM은 과거 일정을 받을 수 없어 매주 쌓이는 회차만 셉니다. 발표 직전 1분 종가 대비 바이낸스 BTC 변화입니다.</p></section>
</div>""".format(cards=cards, rows=rows, note=h(ev.get("note") or ""))
    head = '<script type="module" src="%sassets/events.js?v=%s"></script>' % (B, ASSET_VER)
    return shell("events", "이벤트 리스크 — 발표별 과거 흔들림", "다가오는 미국 주요 경제 발표에서 비트코인이 과거에 얼마나 흔들렸는지 봅니다.", B + "events/", body, now,
                 extra_head=head, data={"radar": radar})


def _heat_table(rows, cols, tag):
    head = "".join('<th scope="col">%s</th>' % ("그 외 코인" if c == "ALT" else c) for c in cols)
    body = []
    for r in rows:
        cells = []
        for c in r["cells"]:
            if c.get("x") is None:
                cells.append('<td class="hm hm--empty" title="표본 %d건">·</td>' % c["n"])
                continue
            x = c["x"]
            level = min(5, int(max(0, x - 0.5) / 0.5))
            arrow = ' <span class="hm__up" title="지난 기간 %.1f배보다 예민해짐">▲</span>' % c["prev"] if c.get("prev") and x >= c["prev"] * 1.3 else ""
            cells.append('<td class="hm hm--%d"><button type="button" class="hm__b" data-e="%s" data-c="%s"><b>%.1f배</b><span>n=%d</span>%s</button></td>'
                         % (level, h(r["e"]), h(c["c"]), x, c["n"], arrow))
        body.append('<tr><th scope="row">%s</th>%s</tr>' % (h(r["label"]), "".join(cells)))
    return '<table class="hmap" data-days="%s"%s><thead><tr><th scope="col">유형</th>%s</tr></thead><tbody>%s</tbody></table>' % (
        tag, "" if tag == "7" else " hidden", head, "".join(body))


def page_patterns(pt, now):
    """패턴: 뉴스 무게 검색기, 내러티브 열지도, 이번 주 가장 무거웠던 뉴스."""
    pt = pt or {"heat": {"7": [], "30": []}, "cols": [], "heaviest": [], "suggest": []}
    chips = "".join('<button type="button" class="achip" data-q="%s">%s</button>' % (h(x), h(x)) for x in pt.get("suggest", []))
    heavy = "".join('<li><a href="%sa/%s/">%s</a><span class="ib ib--%s ib--g%s">%s %s %s · z %.1f</span><time class="muted small">%s</time></li>'
                    % (B, h(r["id"]), h(r["title"]), "up" if r["r"] >= 0 else "down", {"강": "s", "중": "m"}.get(r.get("g"), "w"), h(r["asset"]), r["win"], pct(r["r"]),
                       r["z"], md_hm(r["t0"])) for r in pt.get("heaviest", [])) or '<li class="muted">측정이 쌓이면 표시됩니다.</li>'
    body = """
<div class="wrap ptp" id="ptp" data-src="{B}data/patterns.json">
  <header class="phead"><h1 class="phead__title">패턴</h1><p class="muted">이런 뉴스는 보통 얼마나 움직였는지, 최근 30일 측정값으로 찾아봅니다.</p></header>
  <section class="panel" aria-labelledby="pqTitle">
    <h2 class="panel__title" id="pqTitle">뉴스 무게 검색기</h2>
    <form class="ptp__form" id="pqForm" role="search"><label class="sr-only" for="pq">검색어</label><input id="pq" type="search" placeholder="예: 트럼프, 관세, ETF, 해킹" autocomplete="off"><button class="btn btn--accent" type="submit">찾기</button></form>
    <div class="ptp__chips">{chips}</div>
    <div class="ptp__result" id="pqResult" aria-live="polite"><p class="muted small">검색어를 넣거나 위 칩을 누르세요. 한·영 동의어도 함께 찾습니다.</p></div>
  </section>
  <section class="panel" aria-labelledby="hmTitle">
    <div class="lst__bar"><h2 class="panel__title" id="hmTitle">내러티브 열지도</h2><div class="mseg" role="group" aria-label="기간"><button type="button" class="mseg__b" data-days="7" aria-pressed="true">최근 7일</button><button type="button" class="mseg__b" data-days="30" aria-pressed="false">최근 30일</button></div></div>
    <p class="small muted">칸 = 그 유형 뉴스 뒤 1시간 변동폭(중앙값, 코인 뉴스는 시장 몫을 뺀 값)이 그 코인의 평소 1시간 흔들림의 몇 배였는지. 그 코인을 언급했거나 시장 전체 발표인 뉴스만 셉니다. 표본 3건 미만은 비웁니다. ▲ = 지난 7일보다 1.3배 이상 예민해짐. 칸을 누르면 기사 목록을 봅니다.</p>
    <div class="lst__tablewrap">{h7}{h30}</div>
    <div class="ptp__cell" id="hmCell" aria-live="polite"></div>
  </section>
  <section class="panel" aria-labelledby="hvTitle"><h2 class="panel__title" id="hvTitle">이번 주 가장 무거웠던 뉴스</h2><ul class="mini-strong">{heavy}</ul></section>
  <p class="small muted">{note} 측정 방법은 <a href="{B}about/">소개</a>에 있습니다.</p>
</div>""".format(B=B, chips=chips, heavy=heavy, note=h(pt.get("note") or ""),
                 h7=_heat_table(pt["heat"].get("7", []), pt.get("cols", []), "7"), h30=_heat_table(pt["heat"].get("30", []), pt.get("cols", []), "30"))
    head = '<script type="module" src="%sassets/patterns.js?v=%s"></script>' % (B, ASSET_VER)
    return shell("patterns", "패턴 — 이런 뉴스는 보통 얼마나 움직였나", "뉴스 유형·키워드별 과거 가격 반응을 측정값으로 찾아봅니다.", B + "patterns/", body, now, extra_head=head)


def redirect_page(new_path):
    url = B + new_path
    return """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>주소가 바뀌었습니다 · SIGNAL</title><meta name="robots" content="noindex">
<link rel="canonical" href="{full}"><meta http-equiv="refresh" content="0; url={url}">
<script>location.replace({js} + location.search + location.hash);</script></head>
<body><p>주소가 바뀌었습니다. <a href="{url}">새 주소로 이동</a></p></body></html>
""".format(full=h(config.SITE_URL + "/" + new_path), url=h(url), js=json.dumps(url))


def page_404(now):
    body = '<div class="wrap narrow phead"><h1 class="phead__title">페이지를 찾을 수 없습니다</h1><p class="muted">30일이 지난 기사는 정리됩니다. <a href="%slive/">라이브로 가기</a></p></div>' % B
    return shell("404", "페이지 없음", "페이지를 찾을 수 없습니다.", B + "404.html", body, now, robots="noindex")


def sitemap(articles, now):
    urls = [("", now), ("map/", now), ("live/", now), ("listings/", now), ("events/", now), ("patterns/", now), ("about/", now)]
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


def build_site(out, articles, market, cal, imp, health, now, extra=None):
    """out 디렉터리에 사이트 전체를 쓴다. 기존 data/와 og/는 호출자가 미리 채워 둔다.
    extra = 새 화면 데이터 {파일 이름: 문서}. 없으면 out/data/ 에서 읽는다."""
    if extra is None:
        extra = {n: util.read_json(os.path.join(out, "data", n), None) for n in ("map.json", "moves.json", "listings.json", "events.json", "patterns.json")}
    global HAS_BRIEF, ASSET_VER
    digest = []
    for name in sorted(os.listdir(os.path.join(WEB, "assets"))):
        if os.path.isdir(os.path.join(WEB, "assets", name)):
            continue
        with open(os.path.join(WEB, "assets", name), "rb") as f:
            digest.append(util.short_hash(f.read().decode("latin-1")))
    ASSET_VER = util.short_hash("".join(digest))
    HAS_BRIEF = os.path.isfile(os.path.join(out, "og", "brief.jpg"))
    shutil.copytree(os.path.join(WEB, "assets"), os.path.join(out, "assets"), dirs_exist_ok=True)
    util.write_text(os.path.join(out, ".nojekyll"), "")
    util.write_text(os.path.join(out, "index.html"), page_landing(articles, market, cal, imp, now, extra.get("listings.json")))
    util.write_text(os.path.join(out, "live", "index.html"), page_feed(articles, market, cal, imp, now, extra.get("events.json")))
    for a in articles:
        util.write_text(os.path.join(out, "a", a["id"], "index.html"), page_article(a, related(a, articles), now))
    util.write_text(os.path.join(out, "map", "index.html"), page_map(market, now))
    util.write_text(os.path.join(out, "listings", "index.html"), page_listings(now))
    util.write_text(os.path.join(out, "events", "index.html"), page_events(extra.get("events.json"), now))
    util.write_text(os.path.join(out, "patterns", "index.html"), page_patterns(extra.get("patterns.json"), now))
    # 바뀐 주소: 옛 주소는 새 주소로 바로 보낸다
    for old_path, new_path in (("feed", "live/"), ("markets", "map/"), ("calendar", "events/"), ("impact", "patterns/"), ("predict", "live/")):
        util.write_text(os.path.join(out, old_path, "index.html"), redirect_page(new_path))
    util.write_text(os.path.join(out, "me", "index.html"), page_me(now))
    util.write_text(os.path.join(out, "about", "index.html"), page_about(health, now))
    util.write_text(os.path.join(out, "404.html"), page_404(now))
    util.write_text(os.path.join(out, "sitemap.xml"), sitemap(articles, now))
    util.write_text(os.path.join(out, "robots.txt"), "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % config.SITE_URL)
    util.write_json(os.path.join(out, "data", "feed.json"), {"at": now, "items": [feed_item(a) for a in articles[: config.FEED_JSON_LIMIT]]})
