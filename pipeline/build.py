"""정적 페이지 생성. 서버 없이 GitHub Pages에서 그대로 열리는 HTML을 만든다."""

import hashlib
import html
import json
import os
import re
import shutil

from . import config, judge, util
from . import listings as listings_mod
from .impact import assets_for, subjects
from .moves import COINS as MOVE_COINS

OG_DEFAULT = False
HAS_BRIEF = False
ASSET_VER = "0"

B = config.SITE_BASE
WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

NAV = [("map", "map/", "시그널 보드"), ("live", "live/", "라이브"), ("listings", "listings/", "상장 레이더"), ("events", "events/", "이벤트 리스크")]
TABBAR = ["map", "live", "listings", "events"]
TAB_LABEL = {"map": "시그널", "listings": "상장", "events": "이벤트"}

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
TAB_ICON = {"map": "map", "live": "pulse", "listings": "rocket", "events": "clock"}


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
    <div><span class="brand__word">SIGNAL<span class="brand__slash">/</span></span><p class="muted">상장·큰 발표·뉴스, 돈이 움직이는 순간을 지난 기록과 함께.</p></div>
    <nav class="footer__nav" aria-label="푸터"><a href="{B}about/">소개·방법론</a><a href="{B}about/#sources">데이터 출처</a><a href="{B}sitemap.xml">사이트맵</a></nav>
    <p class="footer__note">기사 저작권은 각 원문 매체에 있으며 SIGNAL은 제목·요약·원문 링크만 제공합니다. 시세와 과거 기록은 정보 제공용이며 투자 조언이 아닙니다. 지난 기록이 앞으로도 같다는 뜻은 아닙니다.</p>
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


def ai_tag(a):
    """로컬 AI가 사건으로 판정한 기사에만 붙는 작은 태그: '상장 · 호재 2'."""
    ai = a.get("ai")
    if not ai or ai.get("kind") != "event":
        return ""
    d = ai.get("dir")
    txt = judge.TYPE_KO.get(ai.get("type"), "기타")
    if d in ("bullish", "bearish"):
        txt += " · %s %d" % (judge.DIR_KO[d], ai.get("str") or 1)
    return '<span class="ait ait--%s" title="AI 판정(로컬 모델, 제목 기준): %s">%s</span>' % (
        {"bullish": "bull", "bearish": "bear"}.get(d, "neu"), h(judge.label(ai)), h(txt))


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
  <div class="fcard__foot">{ait}<span class="achips">{chips}</span></div>
</article>""".format(ait=ai_tag(a), id=h(a["id"]), cat=cat, assets=h(",".join(a.get("assets", []))), imp_n=a["importance"], t0=a["t0"],
                     catlabel=config.CATEGORY_LABEL.get(cat, cat), imp=imp, src=h(a["source_name"]), iso=util.iso(a["t0"]),
                     hm=md_hm(a["t0"]), lang=lang, href=article_path(a), title=h(a["title"]), body=body, chips=chips(a))


def feed_item(a):
    """클라이언트용 축약 JSON."""
    return {
        "id": a["id"], "t0": a["t0"], "title": a["title"], "src": a["source_name"], "lang": a.get("lang"),
        "cat": a["category"], "assets": a.get("assets", []), "imp": a["importance"], "etype": a.get("etype"),
        "sum": a.get("summary") or [], "ex": a.get("excerpt") or "", "llm": a.get("summary_by") == "llm",
        "h": a.get("headline"), "st": a.get("impact_status") or "measuring", "url": a["url"],
        "rx": rx_cells(a), "pt": a.get("pattern"),
        "ai": ({"t": judge.TYPE_KO.get(a["ai"].get("type"), "기타"), "d": a["ai"].get("dir"), "s": a["ai"].get("str"), "l": judge.label(a["ai"])}
               if (a.get("ai") or {}).get("kind") == "event" else None),
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
    """라이브 위쪽: 6시간 안에 큰 발표가 있으면 한 줄로 알린다."""
    up = [u for u in (ev or {}).get("upcoming", []) if now < u["ts"] <= now + 6 * 3600]
    if not up:
        return ""
    u = sorted(up, key=lambda x: (-x["level"], x["ts"]))[0]
    vs = ("평소보다 %.1f배 크게 흔들렸던 발표" % u["vs_normal"]) if u.get("vs_normal") else "지난 기록이 적은 발표"
    return ('<a class="risk" href="{B}events/"><span class="risk__k">곧 큰 발표</span><b>{name}</b><span class="risk__t"><time>{when}</time> · <span data-left="{ts}"></span></span><span class="risk__v">{vs}</span></a>'
            .format(B=B, name=h(u["name"]), when=hm(u["ts"]), ts=u["ts"], vs=vs))


def page_feed(articles, market, cal, imp, now, ev=None, dailies=None):
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
    {daily}
    {flash}
    <button class="new-pill" id="newPill" type="button" hidden></button>
    <div class="feed__list" id="feedList">
{cards}
    </div>
    <button class="btn btn--ghost feed__more" id="loadMore" type="button" hidden>더 보기</button>
  </section>
  <aside class="rail" aria-label="요약 정보">
    <section class="panel"><h2 class="panel__title">시장 온도</h2><div id="tempPanel" class="temp">{temp}</div></section>
    <section class="panel"><h2 class="panel__title">다가오는 일정 <a class="panel__more" href="{B}events/">이벤트 리스크</a></h2><ul class="mini-cal">{cal}</ul></section>
    {brief}
  </aside>
</div>""".format(now=now, now_hm=md_hm(now), cards=cards, cal=cal_html, B=B, temp=temp_panel(market), risk=risk_html(ev, now), flash=flash_html(), daily=daily_teaser(dailies, now),
           brief=('<section class="panel"><h2 class="panel__title">오늘의 시그널</h2><a class="brief-img" href="%sog/brief.jpg" target="_blank" rel="noopener"><img src="%sog/brief.jpg?v=%d" alt="오늘의 시그널 요약 이미지" width="1080" height="1080" loading="lazy"></a><p class="muted small">이미지를 길게 눌러 저장하거나 공유하세요.</p></section>' % (B, B, now)) if HAS_BRIEF else "")
    head = '<script type="module" src="%sassets/flash.js?v=%s"></script>' % (B, ASSET_VER) if config.TG_FEED else ""
    return shell("live", "라이브 — 크립토·AI·매크로 뉴스",
                 "국내외 속보를 실시간으로 한국어로 옮겨 호재·악재를 붙이고, 국내외 기사를 15분마다 모읍니다.", B + "live/", body, now, extra_head=head)


# ---------- 하루 정리 (tools/daily_brief.py가 만든 daily/*.json) ----------
DAILY_CATS = [("crypto", "크립토"), ("econ", "경제"), ("world", "세계정세"), ("ai", "AI 업계")]


def load_dailies():
    """flash/daily/*.json → 날짜 내림차순 목록. 형식이 다른 파일은 건너뛴다."""
    d = os.path.join(config.FLASH_DIR, "daily")
    out = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d), reverse=True):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", f):
                doc = util.read_json(os.path.join(d, f), None)
                if isinstance(doc, dict) and doc.get("v") == 1 and doc.get("date") == f[:-5] and doc.get("headline"):
                    out.append(doc)
    return out


def _day_label(date):
    y, m, d = (int(x) for x in date.split("-"))
    wd = WEEKDAY[util.kst(util.kst_to_ts(y, m, d, 12)).weekday()]
    return "%d월 %d일 (%s)" % (m, d, wd)


def daily_teaser(dailies, now):
    """라이브 맨 위: 가장 최근 하루 정리 한 장. 이틀 넘게 지난 정리는 띄우지 않는다."""
    if not dailies:
        return ""
    doc = dailies[0]
    if now - doc["end"] > 2 * 86400:
        return ""
    if doc["made"] < doc["end"]:
        when = "오늘 지금까지 정리(진행 중)"
    else:
        when = "어제 하루 정리" if now - doc["end"] < 86400 else "최근 하루 정리"
    b = doc["balance"]
    return """<a class="dl-teaser" href="{B}daily/{date}/">
      <span class="dl-teaser__k">{when} · {label}</span>
      <b class="dl-teaser__h">{head}</b>
      <span class="dl-teaser__v"><span class="up">호재 {u}</span><span class="down">악재 {d}</span><span class="dl-teaser__go">전체 보기 →</span></span>
    </a>""".format(B=B, date=doc["date"], when=when, label=_day_label(doc["date"]), head=h(doc["headline"]), u=b["호재"], d=b["악재"])


def _dl_item(it):
    v = it.get("v")
    cls = {"호재": "up", "악재": "down"}.get(v, "flat")
    tags = "".join('<span class="fl-tag">%s</span>' % h(c) for c in it.get("coins", []))
    tags += "".join('<span class="fl-tag fl-tag--sec">%s 섹터</span>' % h(judge_sector_name(s)) for s in it.get("sectors", []))
    tags += '<span class="fl-tag fl-tag--mw">시장 전체</span>' if it.get("mw") else ""
    link = it.get("link") or ""
    link_html = ('<a class="fl-link" href="%s" target="_blank" rel="noopener nofollow">관련 기사 ↗</a>' % h(link)) if link.startswith(("http://", "https://")) else ""
    n = '<span>%d곳 보도</span>' % it["n"] if it.get("n", 1) > 1 else ""
    return """<li class="fl-it{big}"><div class="fl-it__row"><span class="fl-v fl-v--{cls}">{v}</span><span class="fl-it__main">
      <span class="fl-it__ko">{ko}</span><span class="fl-it__meta"><time>{t}</time>{n}{tags}{link}</span></span></div></li>""".format(
        big=" is-big" if it.get("s", 0) >= 2 else "", cls=cls, v=h(v or ""), ko=h(it["ko"]), t=hm(it["t"]), n=n, tags=tags, link=link_html)


def _dl_news(a):
    link = a.get("link") or ""
    src = '<span>%s%s</span>' % (h(a.get("src", "")), (" 외 %d곳" % (a["n"] - 1)) if a.get("n", 1) > 1 else "")
    link_html = ('<a class="fl-link" href="%s" target="_blank" rel="noopener nofollow">기사 ↗</a>' % h(link)) if link.startswith(("http://", "https://")) else ""
    return """<li class="fl-it"><div class="fl-it__row"><span class="fl-v fl-v--flat">기사</span><span class="fl-it__main">
      <span class="fl-it__ko">{ko}</span><span class="fl-it__meta"><time>{t}</time>{src}{link}</span></span></div></li>""".format(
        ko=h(a["ko"]), t=hm(a["t"]), src=src, link=link_html)


SECTOR_KO = {"l1": "레이어1", "l2": "레이어2", "defi": "디파이", "ai": "AI", "meme": "밈", "rwa": "RWA·토큰화", "stable": "스테이블코인",
             "exchange": "거래소", "gamefi": "게임·NFT", "depin": "디핀", "privacy": "프라이버시", "infra": "인프라", "mining": "채굴", "prediction": "예측시장"}


def judge_sector_name(s):
    return SECTOR_KO.get(s, s)


def _pct(v):
    return ("+" if v > 0 else "−" if v < 0 else "") + "%.1f%%" % abs(v)


def page_daily(doc, prev, nxt, now):
    b, m = doc["balance"], doc["market"]
    tot = max(1, b["호재"] + b["악재"])
    cats = "".join('<li><span>{n}</span><span class="dl-mini"><i class="up" style="--w:{wu:.3f}"></i><i class="down" style="--w:{wd:.3f}"></i></span><span class="up">{u}</span><span class="down">{d}</span></li>'.format(
        n=name, u=c["호재"], d=c["악재"], wu=c["호재"] / max(1, c["호재"] + c["악재"]), wd=c["악재"] / max(1, c["호재"] + c["악재"]))
        for k, name in DAILY_CATS for c in [doc["by_cat"].get(k, {"호재": 0, "악재": 0})] if c["호재"] + c["악재"])
    secs = "".join('<li><span class="fl-tag fl-tag--sec">{n} 섹터</span><span class="up">호재 {u}</span><span class="down">악재 {d}</span></li>'.format(n=h(judge_sector_name(s)), u=u, d=d)
                   for s, u, d in doc.get("sectors", [])[:5])
    mk = ""
    if m.get("btc"):
        big = "".join('<div class="dl-big"><span>{c}</span><b class="{cls}">{v}</b></div>'.format(c=c, v=_pct(m[k]["chg"]), cls="up" if m[k]["chg"] >= 0 else "down")
                      for c, k in (("BTC", "btc"), ("ETH", "eth")) if m.get(k))
        mv = lambda xs, cls: " · ".join('%s <b class="%s">%s</b>' % (h(c), cls, _pct(v)) for c, v in xs) or "–"
        mk = """<section class="dl-card"><h2 class="dl-card__t">같은 날 시세</h2><div class="dl-bigs">{big}</div>
          <p class="dl-movers"><span>많이 오른</span>{up}</p><p class="dl-movers"><span>많이 내린</span>{down}</p>
          <p class="dl-card__note">한국 시간 오전 9시부터 다음 날 9시까지, 주요 코인 {n}개 기준. 소식 때문에 움직였다는 뜻은 아니에요.</p></section>""".format(
            big=big, up=mv(m.get("up", []), "up"), down=mv(m.get("down", []), "down"), n=m.get("n", 0))
    key = "".join(_dl_item(it) for it in doc["key"])
    sections = ""
    for k, name in DAILY_CATS:
        sec = doc["sections"].get(k) or {}
        rows = "".join(_dl_news(a) for a in sec.get("news", [])) + "".join(_dl_item(it) for it in sec.get("items", []))
        if not rows:
            continue
        sections += '<section class="dl-sec"><h3 class="dl-sec__t">{n}</h3>{say}<ol class="fl__list">{rows}</ol></section>'.format(
            n=name, say=('<p class="dl-sec__say">%s</p>' % h(sec["say"])) if sec.get("say") else "", rows=rows)
    sched = "".join('<li><time>{t}</time><span class="dl-ev__n">{n}{more}</span><span class="dl-ev__v">{vs}</span></li>'.format(
        t=hm(e["ts"]), n=h(e["title"]), more=(' <small>외 %d건</small>' % e["more"]) if e.get("more") else "",
        vs=("평소보다 %.1f배 크게 흔들렸던 발표" % e["vs"]) if e.get("vs") else ("예상 %s" % h(e["forecast"]) if e.get("forecast") else ""))
        for e in doc.get("schedule", []))
    pager = '<nav class="dl-pager" aria-label="다른 날">{p}<a href="{B}daily/">모든 정리</a>{n}</nav>'.format(
        B=B, p=('<a href="%sdaily/%s/">← %s</a>' % (B, prev, _day_label(prev))) if prev else "<span></span>",
        n=('<a href="%sdaily/%s/">%s →</a>' % (B, nxt, _day_label(nxt))) if nxt else "<span></span>")
    s0, s1 = doc["start"], doc["end"]
    body = """
<div class="wrap dl">
  <p class="dl__k">{label} 하루 정리 <span>한국 시간 {a} ~ {b}</span></p>
  {partial}
  <h1 class="dl__h">{head}</h1>
  {review}
  <div class="dl-grid">
    <section class="dl-card"><h2 class="dl-card__t">호재 vs 악재</h2>
      <div class="dl-bal"><b class="up">{u}</b><span class="dl-bal__bar"><i class="up" style="--w:{wu:.3f}"></i><i class="down" style="--w:{wd:.3f}"></i></span><b class="down">{d}</b></div>
      <ul class="dl-cats">{cats}</ul>
      {secs}
      <p class="dl-card__note">같은 소식은 하나로 묶어 셌어요. 중립 {nn}건은 빼고 셌어요.</p>
    </section>
    {mk}
  </div>
  <section class="dl-sec"><h2 class="dl-sec__t dl-sec__t--big">핵심 소식</h2><ol class="fl__list">{key}</ol></section>
  {sections}
  {sched}
  <p class="fl__note">AI 리뷰와 분야별 문장은 로컬 AI가 위 자료만 보고 썼어요. 숫자는 프로그램이 계산했고, 소식과 시세는 같은 날 있었던 일을 나란히 둔 것이에요. 투자 조언이 아니에요.</p>
  {pager}
</div>""".format(label=_day_label(doc["date"]), a=util.kst(s0).strftime("%-m/%-d %H:%M"), b=util.kst(s1).strftime("%-m/%-d %H:%M"),
                 head=h(doc["headline"]), review=('<section class="dl-review"><p class="dl-review__k">AI 리뷰</p><p>%s</p></section>' % h(doc["review"])) if doc.get("review") else "",
                 u=b["호재"], d=b["악재"], wu=b["호재"] / tot, wd=b["악재"] / tot, nn=b.get("중립", 0), cats=cats,
                 secs=('<ul class="dl-secs">%s</ul>' % secs) if secs else "", mk=mk, key=key, sections=sections,
                 sched=('<section class="dl-sec"><h2 class="dl-sec__t">오늘 볼 일정 <a class="panel__more" href="%sevents/">이벤트 리스크</a></h2><ul class="dl-ev">%s</ul></section>' % (B, sched)) if sched else "",
                 pager=pager, partial=('<p class="dl-partial">진행 중인 하루예요. %s까지 모인 자료로 정리했고, 오전 9시에 최종본으로 바뀌어요.</p>' % util.kst(doc["made"]).strftime("%-m/%-d %H:%M"))
                 if doc["made"] < doc["end"] else "")
    desc = (doc.get("review") or doc["headline"])[:150]
    return shell("daily", "%s 하루 정리 — %s" % (_day_label(doc["date"]), doc["headline"]), desc, B + "daily/%s/" % doc["date"], body, now)


def page_daily_index(dailies, now):
    rows = "".join('<li><a href="{B}daily/{d}/"><span class="dl-idx__d">{label}</span><b>{head}</b><span class="dl-idx__v"><span class="up">호재 {u}</span><span class="down">악재 {dn}</span></span></a></li>'.format(
        B=B, d=x["date"], label=_day_label(x["date"]), head=h(x["headline"]), u=x["balance"]["호재"], dn=x["balance"]["악재"]) for x in dailies) \
        or '<li class="fl-empty">아직 정리가 없어요. 매일 오전 9시에 전날 하루를 정리해요.</li>'
    body = """
<div class="wrap dl">
  <h1 class="dl__h">하루 정리</h1>
  <p class="fl__sub">매일 오전 9시, 전날 하루(오전 9시 ~ 다음 날 9시)의 크립토·경제·세계정세·AI 업계 소식을 AI가 정리해요.</p>
  <ol class="dl-idx">{rows}</ol>
</div>""".format(rows=rows)
    return shell("daily", "하루 정리", "매일 오전 9시, 전날의 크립토·경제·세계정세·AI 업계 소식을 AI가 정리합니다.", B + "daily/", body, now)


def flash_html():
    """라이브 맨 위: 실시간 속보 묶음. 목록은 assets/flash.js가 Worker /flash 에서 30초마다 받아 그린다."""
    if not config.TG_FEED:
        return ""
    return """<section class="fl" id="fl" data-src="{src}" aria-labelledby="flTitle">
      <div class="fl__head">
        <h2 id="flTitle" class="fl__title"><span class="live-dot" aria-hidden="true"></span>실시간 속보</h2>
        <span class="fl__upd" id="flUpd">불러오는 중…</span>
      </div>
      <p class="fl__sub">국내외 속보를 AI가 바로 한국어로 옮기고, 같은 소식은 하나로 묶었어요.</p>
      <div class="fl__seg" role="radiogroup" aria-label="속보 거르기" id="flSeg">
        <button type="button" role="radio" aria-checked="true" data-v="all">전체</button>
        <button type="button" role="radio" aria-checked="false" data-v="호재">호재</button>
        <button type="button" role="radio" aria-checked="false" data-v="악재">악재</button>
        <button type="button" role="radio" aria-checked="false" data-v="big">큰 소식</button>
      </div>
      <ol class="fl__list" id="flList" aria-live="polite"></ol>
      <button class="btn btn--ghost fl__more" id="flMore" type="button" hidden>더 보기</button>
      <p class="fl__note">호재·악재는 로컬 AI가 소식 내용만 보고 붙인 일반적인 해석이에요. 가격이 그렇게 움직인다는 뜻은 아니에요.</p>
    </section>
    <h2 class="feed__sub">기사 <span>매체 {n}곳 · 15분마다</span></h2>""".format(src=h(config.TG_FEED), n=len(config.SOURCES))


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
    if a.get("summary"):
        lead = '<ol class="art__sum">%s</ol><p class="muted small">요약: AI가 원문 제목·발췌만으로 작성했습니다. 정확한 내용은 원문을 확인하세요.</p>' % "".join("<li>%s</li>" % h(s) for s in a["summary"])
    elif a.get("excerpt"):
        lead = '<blockquote class="art__ex"><p>%s</p><footer>원문 발췌 · %s</footer></blockquote>' % (h(a["excerpt"]), h(a["source_name"]))
    else:
        lead = '<p class="muted">요약이 아직 없습니다. 원문에서 내용을 확인하세요.</p>'
    orig = '<p class="art__orig" lang="en">%s</p>' % h(a["title_orig"]) if a["title_orig"] != a["title"] else ""
    rel = "".join('<li><a href="%s">%s</a><span class="muted">%s · %s</span></li>' % (article_path(r), h(r["title"]), h(r["source_name"]), md_hm(r["t0"])) for r in related) \
        or '<li class="muted">관련 기사가 없습니다.</li>'
    ai = a.get("ai")
    ai_line = ('<p class="art__ai"><span class="art__ai-k">AI 판정</span><b>%s</b><span class="muted small">운영자 Mac의 로컬 모델(Gemma 4)이 제목만 보고 판정했습니다. 틀릴 수 있습니다.</span></p>'
               % h(judge.label(ai))) if ai else ""
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
  {ai_line}
  <section class="art__related"><h2 class="h2">관련 기사</h2><ul class="rel">{rel}</ul></section>
</div>""".format(B=B, cat=a["category"], catlabel=config.CATEGORY_LABEL[a["category"]], src=h(a["source_name"]), iso=util.iso(a["t0"]),
                 t0=a["t0"], when=util.kst(a["t0"]).strftime("%Y.%m.%d %H:%M"), title=h(a["title"]), orig=orig, lead=lead, url=h(a["url"]),
                 out=ICON["out"], share=ICON["share"], rel=rel, ai_line=ai_line, id=h(a["id"]))
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
<div class="wrap narrow"><header class="phead"><h1 class="phead__title">소개·방법론</h1><p class="muted">SIGNAL이 데이터를 모으고 계산하는 방법, 그리고 데이터 출처입니다.</p></header></div>
<div class="wrap narrow">
  <section class="panel"><h2 class="panel__title">어떻게 동작하나요</h2>
    <ol class="steps"><li>15분마다 국내외 매체 {nsrc}곳의 RSS와 업비트 공지를 수집하고 중복을 지웁니다.</li><li>키워드로 크립토·AI·매크로를 나누고 관련 코인을 찾습니다.</li><li>운영자 Mac의 로컬 AI(Gemma 4)가 기사마다 사건인지, 어떤 종류인지, 호재인지 악재인지 판정합니다.</li><li>업비트 상장 기록과 미국 경제 발표 일정은 지난 가격과 맞춰 "그때 어땠는지"를 계산합니다.</li><li>기사 본문은 저장하지 않습니다. 제목, 짧은 발췌 또는 요약, 원문 링크만 보여 줍니다.</li></ol>
  </section>
  <section class="panel" id="method"><h2 class="panel__title">계산 방법</h2>
    <ol class="steps">
      <li><span><b>시그널 보드</b>: 코인 24개마다 네 가지를 1시간·4시간·24시간 구간으로 잽니다. ① 시장 대비 움직임 = 실제 등락 − β × 그 코인을 뺀 나머지 코인(시총 가중)의 움직임(β와 평소 흔들림은 최근 30일 1시간 수익률 회귀). 평소 흔들림의 2배 이상이거나 1시간 2%·4시간 3.5%·24시간 6% 이상이면 신호. ② 업비트 원화 거래대금 ÷ 지난 7일 같은 길이 구간 중앙값이 2배 이상. ③ 김프(업비트 원화가 ÷ 바이낸스가 × 원/달러 − 1)가 1시간 0.8%p·4시간 1%p·24시간 1.5%p 이상 변함. ④ 전체 기사 중 그 코인 기사 비중이 평소의 2배 이상이고 3건 이상. 최근 72시간 업비트 상장·유의·상폐 공지도 함께 표시합니다.</span></li>
      <li><span><b>상장 레이더</b>: 업비트 원화 상장마다 거래 시작 첫 1분봉 시가를 기준으로 24시간 동안의 업비트 1분 가격을 모읍니다. '거래 시작 N분 뒤에 샀다면'은 그 분 종가에 사서 하루 뒤 종가에 판 수익에서 수수료(0.05%×2)를 뺀 값입니다. 시세가 없는 코인(상장 폐지 등)과 스테이블코인은 뺍니다.</span></li>
      <li><span><b>이벤트 리스크</b>: 과거 같은 발표마다 발표 직전 1분 바이낸스 BTC 종가 대비 15분·1시간 뒤 변화를 재고 그 절댓값의 중앙값·상위 10%를 보여 줍니다. ‘평소의 몇 배’는 이 중앙값 ÷ 최근 30일 발표가 없던 같은 UTC 시각 1시간 봉 절대 변동의 중앙값입니다. 과거 발표 시각은 FRED 일정이 있는 2025년 이후만 있어 월간 지표는 표본이 20건 안팎이고, 표본 8건 미만이면 수치를 숨깁니다.</span></li>
    </ol>
    <p class="muted small">모든 수치는 지난 기록이며 앞으로도 같다는 뜻이 아닙니다.</p>
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
      <li>실시간 속보: 국내외 공개 속보 채널. 운영자 Mac의 로컬 AI(Gemma 4)가 한국어 한 줄로 옮기고 호재·악재를 붙이며, 원문은 싣지 않습니다.</li>
    </ul>
  </section>
  <section class="panel"><h2 class="panel__title">유의 사항</h2><p>SIGNAL은 정보를 모아 보여 주는 서비스이며 투자 조언을 하지 않습니다. 과거 기록은 같은 시간대에 일어난 변화를 잰 값으로, 특정 뉴스나 발표가 가격을 움직였다는 뜻이 아닙니다.</p></section>
</div>""".format(rows="".join(src_rows), nsrc=len(config.SOURCES))
    return shell("about", "소개·방법론", "SIGNAL이 데이터를 모으고 계산하는 방법과 데이터 출처.", B + "about/", body, now)


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
    loss, med, nf = listings_mod.follow_stats((lst or {}).get("listings", []))
    if nf >= 30:
        lst_q = "거래 시작 10분 뒤 따라 샀다면 100명 중 %d명이 하루 뒤 손해" % round(loss * 100)
        lst_s = "가운데 값 %s · 업비트 원화 상장 %d건" % (pct(med, 1), nf)
    else:
        lst_q, lst_s = "업비트 상장 직후", "새로 상장된 코인이 지난번엔 어떻게 움직였는지 봅니다."
    return """
  <div class="bento">
    <a class="bx bx--feed" data-reveal style="--i:0" href="{B}live/">
      <div class="bx__head"><b class="bx__title">라이브</b><span class="mono-label">최근 24시간 {total}건</span></div>
      <p class="bx__desc">카테고리·관심 종목으로 걸러 봅니다. 새 기사가 들어오면 맨 위에 알려 줍니다.</p>
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
      <div class="bx__head"><b class="bx__title">상장 레이더</b><span class="mono-label">따라 사면?</span></div>
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


def next_big_event(ev, now, days=14):
    """다음 큰 발표 하나(중요도 높은 순, 같으면 빠른 순). 과거 흔들림 통계가 있는 것을 먼저."""
    up = [u for u in (ev or {}).get("upcoming", []) if now < u["ts"] <= now + days * 86400]
    if not up:
        return None
    return sorted(up, key=lambda u: (-u["level"], not (u.get("stats") or {}).get("abs1h"), u["ts"]))[0]


def landing_moments(lst, ev, now):
    """랜딩 '돈이 크게 움직이는 두 순간' 카드 두 장."""
    loss, med, n = listings_mod.follow_stats((lst or {}).get("listings", []))
    a = ('<a class="mom" data-reveal style="--i:0" href="{B}listings/"><p class="mom__k">상장 레이더</p>'
         '<p class="mom__q">새로 상장된 코인, 거래 시작 10분 뒤에 따라 샀다면</p>'
         '<p class="mom__big"><small>100명 중</small><b class="down">{l}</b><small>명이 하루 뒤 손해</small></p>'
         '<p class="mom__s">가운데 값 {m} · 업비트 원화 상장 {n}건 · 수수료 포함</p><span class="mom__go">상장 레이더 보기 →</span></a>').format(
        B=B, l=round(loss * 100), m=pct(med, 1), n=n) if n >= 30 else ""
    u = next_big_event(ev, now)
    if u:
        st = (u.get("stats") or {}).get("abs1h")
        line = ("발표 뒤 1시간 비트코인은 평소의 <b>%.1f배</b>로 흔들렸어요 · 보통 ±%s, 크면 ±%s" % (u["vs_normal"], pct(st["med"], 1).lstrip("+"), pct(st["p90"], 1).lstrip("+"))
                if st and u.get("vs_normal") else "지난 같은 발표 뒤 비트코인의 흔들림을 함께 보여 드려요")
        b = ('<a class="mom" data-reveal style="--i:1" href="{B}events/"><p class="mom__k">이벤트 리스크</p>'
             '<p class="mom__q">다음 큰 발표 · {name}</p>'
             '<p class="mom__big"><b class="mom__left" data-left="{ts}">{when}</b></p>'
             '<p class="mom__s">{line}</p><span class="mom__go">이벤트 리스크 보기 →</span></a>').format(
            B=B, name=h(u["name"]), ts=u["ts"], when=util.kst(u["ts"]).strftime("%m.%d %H:%M"), line=line)
    else:
        b = ""
    return a + b


def page_landing(articles, market, cal, imp, now, lst=None, ev=None):
    """첫 화면. 숫자와 기사는 모두 실제 수집·측정값이다."""
    day = [a for a in articles if now - a["t0"] < 86400]
    measured = sum(1 for a in articles if a.get("ai"))
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
    say_words = "뉴스는 매일 수백 건씩 쏟아집니다. 그중 [내 돈에 영향을 주는] 순간은 몇 번뿐입니다. SIGNAL은 그 순간을 [지난 기록과 함께] 보여 줍니다.".split(" ")
    say, hot = [], False
    for w in say_words:
        st = w.startswith("[")
        hot = hot or st
        say.append('<span class="sw%s">%s</span>' % (" sw--hot" if hot else "", h(w.strip("[]"))))
        if w.endswith("]"):
            hot = False
    rank0 = types[0] if types else None
    words = "돈이 움직이는 순간을 지난 기록으로".split(" ")
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
    moments = landing_moments(lst, ev, now)
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
          <div class="hero__cta"><a class="btn btn--accent btn--lg" href="{B}map/">시그널 보드 보기</a><a class="btn btn--ghost btn--lg" href="{B}live/">라이브 보기</a></div>
        </div>
      </div>
      <div class="hx__cap" data-beat="0.7,0.8,2,3"><span class="mono-label">{drop_note}</span><b>SIGNAL은 그 파문의<br>크기를 잽니다.</b></div>
    </div>
    <p class="hx__hint" data-beat="-1,0,0.02,0.06" aria-hidden="true">아래로 스크롤</p>
  </div>
</section>

<section class="hero hero--stats" aria-label="수집 현황">
  <div class="wrap">
    <dl class="hero__stats in" style="--s:{s3}">
      <div><dt>최근 24시간 기사</dt><dd class="count" data-to="{n24}">{n24}</dd></div>
      <div><dt>수집 매체</dt><dd class="count" data-to="{nsrc}">{nsrc}</dd></div>
      <div><dt>AI가 읽은 기사</dt><dd class="count" data-to="{measured}">{measured}</dd></div>
    </dl>
  </div>
</section>

<section class="lsec wrap moments" aria-labelledby="momTitle">
  <h2 class="lsec__title" id="momTitle" data-reveal>돈이 크게 움직이는 두 순간</h2>
  <p class="lsec__lede" data-reveal style="--i:1">지난 기록으로 미리 알아 두면 덜 잃습니다.</p>
  <div class="moments__grid">{moments}</div>
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
      <p class="mono-label outro__kicker">최근 24시간 기사 {n24}건 · 15분마다 갱신</p>
      <h2 class="outro__title" id="ctaTitle"><span class="ot__l ot__l--noise"><span>Noise out.</span></span><span class="ot__l ot__l--sig"><span><em class="ot__fill"{fill}>Signal</em> in.</span></span></h2>
      <div class="outro__foot">
        <p>회원가입 없이 무료로 씁니다. 투자 조언은 하지 않습니다.</p>
        <div class="outro__cta"><a class="btn btn--accent btn--lg" href="{B}map/">시그널 보드 보기</a><a class="btn btn--ghost btn--lg" href="{B}live/">라이브 보기</a></div>
      </div>
    </div>
  </div>
</section>""".format(
        now=now, now_hm=md_hm(now), B=B, title=title, s1=len(words) + 1, s2=len(words) + 2, s3=len(words) + 4, demo=demo_html,
        n24=len(day), nsrc=len(config.SOURCES), measured=measured, srcs=srcs, proof=proof, bars=bars, feats=bento(articles, market, cal, now, lst), say=" ".join(say), moments=moments, video_attr=video_attr, drop_note=h(drop_note), wall=wall, nsig=nsig, fill=fill,
        nproof=len(strong), nproof2="%02d" % len(strong),
        rank0_label=h(rank0["label"]) if rank0 else "–", rank0_val=pct(rank0["mean_abs"]).lstrip("+") if rank0 else "–",
        rank0_n=("표본 %d건" % rank0["n"]) if rank0 else "", **sc["fmt"])
    data = {"landing": {"demo": demo, "story": sc["js"]}}
    head3d = ('<link rel="preload" as="image" href="%sassets/hero/ripple-desktop.webp" media="(min-aspect-ratio: 4/5)">\n'
              '<link rel="preload" as="image" href="%sassets/hero/ripple-mobile.webp" media="(max-aspect-ratio: 4/5)">\n'
              '<script type="module" src="%sassets/hero.js?v=%s"></script>' % (B, B, B, ASSET_VER)) if video_ready else (
              '<script type="module" src="%sassets/hero.js?v=%s"></script>' % (B, ASSET_VER))
    return shell("home", "SIGNAL — 돈이 움직이는 순간을 지난 기록으로", "업비트 상장, 미국 큰 경제 발표, 크립토 뉴스까지. 돈이 크게 움직이는 순간을 지난 기록과 함께 보여 줍니다.",
                 B, body, now, extra_head=head3d, data=data)


def page_map(market, now):
    """시그널 보드(/map/). 코인 24개마다 시장 대비 움직임·업비트 거래대금·김프 변화·뉴스 양 중 평소와 다른 것을 보여 주고,
    누르면 그 코인의 24시간 '실제 vs 시장대로였다면'과 그 사이 뉴스를 펼친다. 그림은 assets/signals.js가 data/signals.json을 읽어 그린다."""
    icons = ",".join(sorted(f[:-4] for f in os.listdir(os.path.join(WEB, "assets", "coins")) if f.endswith(".svg")))
    body = """
<section class="sb wrap" id="sb" data-src="{B}data/signals.json" data-icons="{icons}" aria-labelledby="sbTitle">
  <header class="sb-hero">
    <p class="sb-asof" id="sbAsof"></p>
    <h1 class="sb-title" id="sbTitle">지금 평소와 다른 코인</h1>
    <p class="sb-lede" id="sbLede"></p>
  </header>
  <div class="sb-bar">
    <div class="sb-seg" role="group" aria-label="기간"><button type="button" data-w="1h" aria-pressed="false">1시간</button><button type="button" data-w="4h" aria-pressed="false">4시간</button><button type="button" data-w="24h" aria-pressed="true">24시간</button></div>
    <div class="sb-seg" role="group" aria-label="보기"><button type="button" data-f="flag" aria-pressed="true">신호 있는 코인</button><button type="button" data-f="all" aria-pressed="false">전체</button></div>
    <p class="sb-key"><i></i>평소와 다름</p>
  </div>
  <p class="sb-empty" id="sbEmpty" hidden>데이터를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요.</p>
  <div class="sb-board" role="table" aria-label="코인별 신호">
    <div class="sb-head" role="row"><span role="columnheader">코인</span><span role="columnheader">시장 대비 움직임</span><span role="columnheader">업비트 거래대금 <small>평소 대비</small></span><span role="columnheader">김프 변화</span><span role="columnheader">뉴스 양</span><span role="columnheader">왜? (그 코인 뉴스)</span></div>
    <div id="sbRows" role="rowgroup"></div>
  </div>
  <p class="sb-quiet" id="sbQuiet" hidden></p>
  <details class="sb-how">
    <summary>신호는 이렇게 정합니다</summary>
    <ol class="sb-steps">
      <li><span><b>시장 대비 움직임</b>실제 등락 − 시장대로였다면(그 코인을 뺀 나머지 코인 24개의 움직임 × 그 코인이 평소 시장을 따라가는 정도). 평소 흔들림의 2배를 넘거나, 1시간 2%·4시간 3.5%·24시간 6% 이상이면 신호.</span></li>
      <li><span><b>업비트 거래대금</b>최근 구간 원화 거래대금 ÷ 지난 7일 같은 길이 구간의 중앙값. 2배 이상이면 신호. 업비트 원화 마켓에 없는 코인은 비웁니다.</span></li>
      <li><span><b>김프 변화</b>업비트 원화 가격 ÷ (바이낸스 가격 × 원/달러) − 1 이 구간 동안 바뀐 정도. 1시간 0.8%p·4시간 1%p·24시간 1.5%p 이상이면 신호.</span></li>
      <li><span><b>뉴스 양</b>전체 기사 중 그 코인을 언급한 기사 비중이 평소의 2배 이상이고 3건 이상이면 신호. ‘왜?’ 칸에는 가격 정리 기사를 뺀 가장 중요한 그 코인 뉴스를 붙입니다.</span></li>
    </ol>
    <p class="sb-note">신호는 ‘평소와 다르다’는 뜻일 뿐 매수·매도 추천이 아니며, 뉴스는 같은 시간대의 연관이지 원인이라는 뜻이 아닙니다. <a href="{B}about/#method">계산 방법 자세히</a></p>
  </details>
</section>""".format(B=B, icons=icons)
    head = '<script type="module" src="%sassets/signals.js?v=%s"></script>' % (B, ASSET_VER)
    return shell("map", "시그널 보드 — 지금 평소와 다른 코인", "코인 24개의 시장 대비 움직임, 업비트 거래대금, 김프 변화, 뉴스 양 중 평소와 다른 것을 한눈에 보여 줍니다.", B + "map/", body, now, extra_head=head)


def page_listings(now):
    """상장 레이더: '새로 상장된 코인, 따라 사면 어떻게 됐나'를 한 화면에. 숫자와 그림은 assets/listings.js가 data/listings.json으로 그린다."""
    proxy = config.UPBIT_NOTICES_PROXY[: -len("/upbit-notices")] if config.UPBIT_NOTICES_PROXY.endswith("/upbit-notices") else ""
    body = """
<div class="wrap lr" id="lr" data-src="{B}data/listings.json" data-proxy="{proxy}">
  <div id="lrLive" aria-live="polite"></div>
  <section class="lr-key" aria-labelledby="lrTitle">
    <p class="lr-eyebrow">업비트 원화 상장 <span id="lrN">–</span>건의 실제 기록</p>
    <h1 id="lrTitle">새로 상장된 코인,<br>따라 사면 어떻게 됐을까?</h1>
    <div class="lr-when" id="lrWhen" role="radiogroup" aria-label="언제 샀다면"></div>
    <p class="lr-big"><small>100명 중</small><span class="num" id="lrLoss">–</span><small>명이 하루 뒤 손해</small></p>
    <div class="lr-dots" id="lrDots" role="img"></div>
    <p class="lr-say" id="lrSay" aria-live="polite"></p>
  </section>
  <section class="lr-card" aria-labelledby="lrPathTitle">
    <h2 id="lrPathTitle">따라 산 뒤 가격은 보통 이렇게 됐어요</h2>
    <p class="lr-sub" id="lrPathSub"></p>
    <div class="lr-chart"><svg id="lrPath" role="img" aria-label="따라 산 뒤 가격의 보통 흐름"></svg></div>
    <ol class="lr-steps" id="lrSteps"></ol>
  </section>
  <section class="lr-recent" aria-labelledby="lrRecentTitle">
    <h2 id="lrRecentTitle">최근 상장</h2>
    <p class="lr-sub">거래 시작 10분 뒤에 샀다면 하루 뒤 결과(수수료 포함)</p>
    <ul id="lrRecent"></ul>
  </section>
  <details class="lr-more">
    <summary>업비트 거래 공지 전체 보기</summary>
    <p class="lr-sub">신규 상장·유의 종목·거래지원 종료 공지예요. 1분마다 새 공지를 확인해요.</p>
    <ul class="lr-notices" id="lrNotices"></ul>
    <button class="btn btn--ghost" id="lrMore" type="button" hidden>더 보기</button>
  </details>
  <details class="lr-more">
    <summary>어떻게 쟀나요?</summary>
    <ul class="lr-how">
      <li>2017년부터 업비트에 원화로 새로 올라온 코인의 실제 업비트 1분 가격이에요. 사고팔 때 수수료 0.05%씩을 뺐어요.</li>
      <li>거래 시작 시각은 공지에 적힌 시각이나, 없으면 첫 거래가 생긴 시각이에요. 스테이블코인은 뺐어요.</li>
      <li>상장 폐지돼 시세가 사라진 코인은 빠져 있어서, 실제는 이보다 나빴을 수 있어요.</li>
      <li>지난 기록일 뿐이고, 다음 상장도 같다는 뜻은 아니에요. 투자 권유가 아니에요.</li>
    </ul>
  </details>
</div>""".format(B=B, proxy=h(proxy))
    head = '<script type="module" src="%sassets/listings.js?v=%s"></script>' % (B, ASSET_VER)
    return shell("listings", "상장 레이더 — 새로 상장된 코인, 따라 사면?", "업비트에 새로 상장된 코인을 거래 시작 뒤에 따라 샀다면 하루 뒤 어떻게 됐는지, 실제 기록으로 보여 줍니다.",
                 B + "listings/", body, now, extra_head=head)


# 처음 보는 사람을 위한 한 줄 설명(무엇을 발표하는지)
EV_EXPLAIN = {
    "cpi": "미국 물가가 한 달 동안 얼마나 올랐는지 발표해요. 코인이 가장 크게 반응하는 발표 중 하나예요.",
    "ppi": "기업이 사들이는 물건 값(생산자 물가)이에요. 소비자 물가의 앞선 신호로 봐요.",
    "nfp": "미국에 일자리가 얼마나 늘었는지, 실업률은 몇 %인지 발표해요.",
    "pce": "미국 중앙은행(연준)이 가장 중요하게 보는 물가 지표예요.",
    "gdp": "미국 경제가 얼마나 성장했는지 발표해요.",
    "retail": "미국 사람들이 물건을 얼마나 샀는지(소비) 발표해요.",
    "claims": "매주 목요일 나오는 실업수당 신청 건수예요. 일자리 사정을 빨리 보여 줘요.",
    "fomc": "미국 중앙은행이 기준금리를 올릴지, 내릴지, 그대로 둘지 정해요. 가장 큰 발표예요.",
    "fomc_press": "금리 결정 30분 뒤 연준 의장이 기자회견을 해요. 말 한마디에 크게 흔들려요.",
    "minutes": "3주 전 금리 회의에서 어떤 이야기가 오갔는지 공개해요.",
    "ism_m": "미국 공장들의 경기를 묻는 설문 지수예요.",
    "ism_s": "미국 서비스 업체들의 경기를 묻는 설문 지수예요.",
}
WEEKDAY = "월화수목금토일"


def _kst_label(ts):
    d = util.kst(ts)
    return "%d월 %d일(%s) %s" % (d.month, d.day, WEEKDAY[d.weekday()], d.strftime("%H:%M"))


def _ev_name(name):
    return (name or "").replace("Fed Chairman ", "연준 의장 ").replace("Fed Chair ", "연준 의장 ")


def _shake(vs):
    """평소 대비 배수 → 흔들림 막대 5칸 중 몇 칸, 이름."""
    if not vs:
        return 0, ""
    n = max(1, min(5, round(vs)))
    return n, "평소의 %.1f배" % vs


def page_events(ev, now):
    """이벤트 리스크: 다음 큰 발표 하나 + 내 돈으로 환산 + 이번 주 일정 + 발표별 흔들림 순위."""
    ev = ev or {"upcoming": [], "kinds": []}
    hero = next_big_event(ev, now)
    hero_html = '<p class="er-none">앞으로 2주 안에 잡힌 큰 발표가 없어요.</p>'
    if hero:
        st = (hero.get("stats") or {})
        a1 = st.get("abs1h")
        recent = st.get("recent") or []
        ups = sum(1 for r in recent if r["r1h"] >= 0)
        mx = max([abs(r["r1h"]) for r in recent] or [1]) or 1
        bars = "".join('<li class="{d}" title="{dt} {r}"><i style="--v:{v:.3f}"></i></li>'.format(
            d="up" if r["r1h"] >= 0 else "down", v=abs(r["r1h"]) / mx, dt=util.kst(r["ts"]).strftime("%Y.%m.%d"), r=pct(r["r1h"])) for r in recent)
        span_dates = ('<p class="er-bars__x"><span>%s</span><span>%s</span></p>' % (util.kst(recent[0]["ts"]).strftime("%Y.%m"), util.kst(recent[-1]["ts"]).strftime("%Y.%m"))) if recent else ""
        n_sh, sh_label = _shake(hero.get("vs_normal"))
        big = ("발표 뒤 1시간, 비트코인은 <b>평소보다 %.1f배</b> 크게 흔들렸어요" % hero["vs_normal"]) if hero.get("vs_normal") else "지난 같은 발표 뒤 비트코인의 흔들림을 모으는 중이에요"
        calc = ""
        if a1:
            calc = """<div class="er-calc" id="erCalc" data-med="{med}" data-p90="{p90}" data-max="{mx}">
      <p class="er-calc__q">내 돈으로 보면</p>
      <div class="er-calc__in"><label for="erAmt">비트코인에 넣은 돈</label><div class="er-amt"><input id="erAmt" inputmode="numeric" value="1,000,000" aria-describedby="erAmtUnit"><span id="erAmtUnit">원</span></div>
        <div class="er-lev" role="radiogroup" aria-label="레버리지"><button type="button" role="radio" data-lev="1" aria-checked="true">현물</button><button type="button" role="radio" data-lev="2" aria-checked="false">2배</button><button type="button" role="radio" data-lev="5" aria-checked="false">5배</button><button type="button" role="radio" data-lev="10" aria-checked="false">10배</button></div></div>
      <dl class="er-calc__out"><div><dt>보통 흔들린 폭</dt><dd id="erMed">–</dd></div><div><dt>크게 흔들린 때(10번 중 1번)</dt><dd id="erP90">–</dd></div></dl>
      <p class="er-calc__note" id="erNote"></p>
    </div>""".format(med=a1["med"], p90=a1["p90"], mx=a1["max"])
        past = ('<div class="er-past"><p class="er-past__t">지난 {n}번, 발표 뒤 1시간</p><ol class="er-bars" aria-label="지난 {n}번 발표 뒤 1시간 비트코인 변화">{bars}</ol>{sx}'
                '<p class="er-past__s">오른 날 {u}번 · 내린 날 {d}번 · 방향은 그때그때 달라요</p></div>').format(n=len(recent), bars=bars, sx=span_dates, u=ups, d=len(recent) - ups) if recent else ""
        hero_html = """<article class="er-hero">
    <p class="er-tag">다음 큰 발표</p>
    <h2 class="er-name">{name}</h2>
    <p class="er-what">{what}</p>
    <p class="er-when"><b class="er-left" data-left="{ts}">–</b><span>{when} · 한국 시간</span></p>
    <p class="er-big">{big}</p>
    {calc}{past}
  </article>""".format(name=h(hero["name"]), what=h(EV_EXPLAIN.get(hero.get("kind") or "", "")), ts=hero["ts"], when=_kst_label(hero["ts"]), big=big, calc=calc, past=past)
    # 이번 주 일정: 같은 시각 발표는 한 줄로
    up = [u for u in ev.get("upcoming", []) if now - 2 * 3600 <= u["ts"] <= now + 8 * 86400]
    slots = {}
    for u in up:
        slots.setdefault(u["ts"], []).append(u)
    rows, last_day = [], None
    for ts in sorted(slots):
        g = sorted(slots[ts], key=lambda u: (-u["level"], -(u.get("vs_normal") or 0)))
        top = g[0]
        day = util.kst(ts).strftime("%m%d")
        if day != last_day:
            d = util.kst(ts)
            rows.append('<li class="er-day">%d월 %d일 %s요일</li>' % (d.month, d.day, WEEKDAY[d.weekday()]))
            last_day = day
        vs = max([u.get("vs_normal") or 0 for u in g]) or None
        n_sh, sh_label = _shake(vs)
        names = h(_ev_name(top["name"])) + ((" 외 %d개" % (len(g) - 1)) if len(g) > 1 else "")
        what = EV_EXPLAIN.get(top.get("kind") or "", "")
        detail = "".join('<li><b>%s</b>%s</li>' % (h(_ev_name(u["name"])), (" · 예상 %s · 이전 %s" % (h(u["forecast"]), h(u["previous"]))) if u.get("forecast") else "") for u in g)
        react = ""
        if ts <= now:
            r = (top.get("reaction") or {}).get("1h")
            react = ('<span class="er-react %s">발표 뒤 1시간 %s</span>' % ("up" if r >= 0 else "down", pct(r))) if r is not None else '<span class="er-react muted">발표됨 · 결과 재는 중</span>'
        rows.append("""<li class="er-row{past}"><details><summary>
      <time>{t}</time><span class="er-row__n">{names}</span>
      <span class="er-shake" data-n="{ns}" title="{sl}" aria-label="흔들림 {sl}"><i></i><i></i><i></i><i></i><i></i></span>
      <span class="er-row__s">{sl2}{react}</span></summary>
      <div class="er-row__d">{what}<ul>{detail}</ul></div></details></li>""".format(
            past=" is-past" if ts <= now else "", t=util.kst(ts).strftime("%H:%M"), names=names, ns=n_sh, sl=h(sh_label or "기록 없음"),
            sl2=h(sh_label) if sh_label else '<span class="muted">과거 기록 없음</span>', react=react,
            what=('<p>%s</p>' % h(what)) if what else "", detail=detail))
    sched = "".join(rows) or '<li class="er-none">앞으로 1주일 동안 잡힌 주요 발표가 없어요.</li>'
    # 발표별 흔들림 순위
    ks = sorted([k for k in ev.get("kinds", []) if k.get("abs1h") and k.get("n", 0) >= 8], key=lambda k: -k["abs1h"]["med"])
    top = max([k["abs1h"]["med"] for k in ks] or [1]) or 1
    rank = "".join('<li><span class="er-rank__n">{n}</span><span class="er-rank__bar"><i style="--v:{v:.3f}"></i></span><span class="er-rank__v">±{m}</span></li>'.format(
        n=h(k["name"]), v=k["abs1h"]["med"] / top, m=pct(k["abs1h"]["med"], 1).lstrip("+")) for k in ks)
    body = """
<div class="wrap er">
  <header class="er-head">
    <p class="er-eyebrow">미국 경제 발표 일정 · 한국 시간</p>
    <h1>큰 발표가 나올 때,<br>비트코인은 얼마나 흔들릴까?</h1>
  </header>
  {hero}
  <section class="er-sec" aria-labelledby="erWeek"><h2 id="erWeek">이번 주 발표</h2><p class="er-sub">막대가 많을수록 발표 뒤 1시간 동안 평소보다 크게 흔들렸던 발표예요. 누르면 자세히 볼 수 있어요.</p>
    <ol class="er-sched">{sched}</ol></section>
  <section class="er-sec" aria-labelledby="erRank"><h2 id="erRank">어떤 발표가 가장 크게 흔들었나</h2><p class="er-sub">지난 기록에서 발표 뒤 1시간 동안 비트코인이 보통 움직인 폭(오르든 내리든)</p>
    <ol class="er-rank">{rank}</ol></section>
  <details class="lr-more"><summary>어떻게 쟀나요?</summary><ul class="lr-how">
    <li>발표 1분 전 가격과 1시간 뒤 가격을 비교한 Binance 비트코인 가격이에요. '평소'는 같은 요일·같은 시간대의 1시간이에요.</li>
    <li>발표 일정은 미국 통계청(FRED), 연준, Forex Factory에서 가져와요.</li>
    <li>지난 기록일 뿐이에요. 같은 시간에 다른 일이 겹쳤을 수 있고, 발표가 원인이라는 뜻은 아니에요. 투자 권유가 아니에요.</li>
  </ul></details>
</div>""".format(hero=hero_html, sched=sched, rank=rank or '<li class="er-none">기록이 쌓이는 중이에요.</li>')
    head = '<script type="module" src="%sassets/events.js?v=%s"></script>' % (B, ASSET_VER)
    return shell("events", "이벤트 리스크 — 큰 발표 때 비트코인은 얼마나 흔들릴까", "다음 미국 큰 경제 발표에서 비트코인이 과거에 얼마나 흔들렸는지, 내 돈 기준으로 보여 줍니다.", B + "events/", body, now, extra_head=head)


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


def sitemap(articles, now, dailies=()):
    urls = [("", now), ("live/", now), ("my/", now)] + [("themes/%s/" % k, now) for k in THEME_PAGES] + [("brief/", now), ("calendar/", now), ("about/", now)]
    urls += [("daily/%s/" % d["date"], d["made"]) for d in dailies]
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


def page_landing_df():
    """첫 페이지(Delfona): 입자 로고 첫 화면 + '신호 하나의 속' 3D 섹션. 정적 틀(web/df_landing.html)에 주소·버전만 채운다.
    내용(속보·24시간 개수·카드)은 브라우저가 Worker /flash 에서 실시간으로 받아 그린다."""
    with open(os.path.join(WEB, "df_landing.html"), encoding="utf-8") as f:
        tpl = f.read()
    og = ""
    if OG_DEFAULT:
        og = ('<meta property="og:image" content="%s/og/default.jpg">\n<meta property="og:image:width" content="1200">\n'
              '<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">') % config.SITE_URL
    return tpl.replace("{{B}}", B).replace("{{V}}", df_ver()).replace("{{URL}}", config.SITE_URL + "/").replace("{{OG}}", og)


def page_live_df():
    """라이브(Delfona R3 · 임팩트): 큰 소식 + 소식 이후 가격 차트, 테마 탭, 카드. 정적 틀(web/df_live.html)에 주소·버전만 채운다.
    소식·가격은 브라우저가 Worker /flash · /index-candles 와 Binance 에서 실시간으로 받아 그린다."""
    with open(os.path.join(WEB, "df_live.html"), encoding="utf-8") as f:
        tpl = f.read()
    return tpl.replace("{{B}}", B).replace("{{V}}", df_ver()).replace("{{URL}}", config.SITE_URL + "/")


THEME_PAGES = {
    "crypto": ("Crypto", "크립토 테마 — 지난 24시간 비트코인·이더리움·알트코인 소식의 호재·악재 흐름, 오늘 평소와 달라진 점, 관련 시세."),
    "nasdaq": ("Nasdaq", "나스닥 테마 — 지난 24시간 미국 기술주·지수 선물 소식의 호재·악재 흐름, 오늘 평소와 달라진 점, 관련 시세."),
    "econ": ("Economy", "경제 테마 — 지난 24시간 금리·물가·달러·원자재 소식의 호재·악재 흐름, 오늘 평소와 달라진 점, 다음 주요 일정."),
    "ai": ("AI", "AI 테마 — 지난 24시간 AI 기업·반도체 소식의 호재·악재 흐름, 오늘 평소와 달라진 점, 관련 시세."),
    "world": ("World", "세계 테마 — 지난 24시간 전쟁·외교·에너지·제재 소식의 호재·악재 흐름, 오늘 평소와 달라진 점, 유가·금·달러 시세."),
}


def page_themes_df(k):
    """테마(Delfona T2 · 대시보드): 자산 띠, 24시간 흐름, 섹터, '오늘 무엇이 달라졌나', 주요 소식. 정적 틀(web/df_themes.html).
    자료는 브라우저가 themes.json(Mac 이 3시간마다) · Binance · Worker /market 에서 받는다."""
    with open(os.path.join(WEB, "df_themes.html"), encoding="utf-8") as f:
        tpl = f.read()
    title, desc = THEME_PAGES[k]
    return (tpl.replace("{{TITLE}}", title).replace("{{DESC}}", h(desc)).replace("{{K}}", k)
            .replace("{{B}}", B).replace("{{V}}", df_ver()).replace("{{URL}}", config.SITE_URL + "/"))


def page_my_df():
    """내 자산(Delfona Y2 · 피드 + 관심 목록): 고른 자산의 소식, 급변 알림('왜 움직여?'), 하루 요약. 정적 틀(web/df_my.html).
    고른 자산은 브라우저(localStorage)에만 있고, 계산도 브라우저에서 한다(사용자가 늘어도 Mac 부담 없음)."""
    with open(os.path.join(WEB, "df_my.html"), encoding="utf-8") as f:
        tpl = f.read()
    return tpl.replace("{{B}}", B).replace("{{V}}", df_ver()).replace("{{URL}}", config.SITE_URL + "/")


def page_calendar_df():
    """일정(Delfona C3 · 대시보드): 방금 나온 지표, 지금 경제 요약(AI), 다가오는 발표, 지표 카드, 지표 상세(지난 흐름 · 과거에 비슷했을 때).
    자료는 브라우저가 econ.json(Mac 이 1시간마다, tools/econ_brief.py)을 flash 브랜치에서 읽는다."""
    with open(os.path.join(WEB, "df_calendar.html"), encoding="utf-8") as f:
        tpl = f.read()
    return tpl.replace("{{B}}", B).replace("{{V}}", df_ver()).replace("{{URL}}", config.SITE_URL + "/")


def page_brief_df():
    """정리(Delfona B2 · 타임라인 열지도): 며칠째 이어지는 이야기(줄기)를 한 시간 축 위에, 고르면 지금까지 · 최근 24시간 · 소식 전체.
    자료는 브라우저가 threads.json(Mac 이 30분마다, tools/story_threads.py)과 어제 하루 정리(daily_brief.py)를 flash 브랜치에서 읽는다."""
    with open(os.path.join(WEB, "df_brief.html"), encoding="utf-8") as f:
        tpl = f.read()
    return tpl.replace("{{B}}", B).replace("{{V}}", df_ver()).replace("{{URL}}", config.SITE_URL + "/")


def df_ver():
    """web/assets/df/ 파일 내용으로 만든 버전(바뀌면 브라우저가 새로 받는다)."""
    d = os.path.join(WEB, "assets", "df")
    h = hashlib.sha1()
    for n in sorted(os.listdir(d)):
        with open(os.path.join(d, n), "rb") as f:
            h.update(n.encode() + f.read())
    return h.hexdigest()[:8]


def stamp_df_imports(out):
    """assets/df/*.js 안의 서로 부르는 import 에도 같은 버전을 붙인다(옛 파일이 섞여 쓰이지 않게)."""
    d, v = os.path.join(out, "assets", "df"), df_ver()
    for n in os.listdir(d):
        if n.endswith(".js"):
            p = os.path.join(d, n)
            with open(p, encoding="utf-8") as f:
                src = f.read()
            new = re.sub(r"(from '\./[a-z0-9]+\.js)(\?v=[0-9a-z]+)?'", lambda m: "%s?v=%s'" % (m.group(1), v), src)
            if new != src:
                util.write_text(p, new)


def build_site(out, articles, market, cal, imp, health, now, extra=None):
    """out 디렉터리에 사이트 전체를 쓴다. 기존 data/와 og/는 호출자가 미리 채워 둔다.
    extra = 새 화면 데이터 {파일 이름: 문서}. 없으면 out/data/ 에서 읽는다."""
    if extra is None:
        extra = {n: util.read_json(os.path.join(out, "data", n), None) for n in ("map.json", "moves.json", "listings.json", "events.json")}
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
    stamp_df_imports(out)
    util.write_text(os.path.join(out, "index.html"), page_landing_df())
    dailies = load_dailies()
    util.write_text(os.path.join(out, "live", "index.html"), page_live_df())   # 옛 SIGNAL 라이브(page_feed)는 Delfona R3 로 바뀜
    for i, doc in enumerate(dailies):
        nxt = dailies[i - 1]["date"] if i > 0 else None
        prev = dailies[i + 1]["date"] if i + 1 < len(dailies) else None
        util.write_text(os.path.join(out, "daily", doc["date"], "index.html"), page_daily(doc, prev, nxt, now))
    # 정리: 새 정리(/brief/)가 목록을 대신한다. 날짜별 하루 정리(/daily/<날짜>/)는 그대로 둔다
    util.write_text(os.path.join(out, "brief", "index.html"), page_brief_df())
    util.write_text(os.path.join(out, "daily", "index.html"), redirect_page("brief/"))
    for a in articles:
        util.write_text(os.path.join(out, "a", a["id"], "index.html"), page_article(a, related(a, articles), now))
    # 테마: /themes/<k>/ (첫 화면은 크립토). 옛 시그널 보드·상장 레이더는 테마로 합쳐졌다
    for k in THEME_PAGES:
        util.write_text(os.path.join(out, "themes", k, "index.html"), page_themes_df(k))
    util.write_text(os.path.join(out, "themes", "index.html"), page_themes_df("crypto"))
    # 일정: 옛 이벤트 리스크(/events/)는 새 일정(/calendar/)으로 옮겼다
    util.write_text(os.path.join(out, "calendar", "index.html"), page_calendar_df())
    util.write_text(os.path.join(out, "events", "index.html"), redirect_page("calendar/"))
    # 바뀐 주소: 옛 주소는 새 주소로 바로 보낸다
    for old_path, new_path in (("feed", "live/"), ("markets", "themes/crypto/"), ("map", "themes/crypto/"), ("listings", "themes/crypto/"), ("impact", "live/"), ("patterns", "live/"), ("predict", "live/")):
        util.write_text(os.path.join(out, old_path, "index.html"), redirect_page(new_path))
    # 내 자산: 옛 /me/(관심 코인)는 /my/ 로 옮겼다. 옛 목록(localStorage 'signal-watch')은 새 페이지가 가져온다
    util.write_text(os.path.join(out, "my", "index.html"), page_my_df())
    util.write_text(os.path.join(out, "me", "index.html"), redirect_page("my/"))
    util.write_text(os.path.join(out, "about", "index.html"), page_about(health, now))
    util.write_text(os.path.join(out, "404.html"), page_404(now))
    util.write_text(os.path.join(out, "sitemap.xml"), sitemap(articles, now, dailies))
    util.write_text(os.path.join(out, "robots.txt"), "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % config.SITE_URL)
    util.write_json(os.path.join(out, "data", "feed.json"), {"at": now, "items": [feed_item(a) for a in articles[: config.FEED_JSON_LIMIT]]})
