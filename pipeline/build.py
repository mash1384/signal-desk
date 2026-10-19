"""정적 페이지 생성. 서버 없이 GitHub Pages에서 그대로 열리는 HTML을 만든다."""

from contextvars import ContextVar
import hashlib
import html
import json
import os
import re
import shutil

from . import config, judge, util, prerender, public_data, article_bundle
from .impact import assets_for, subjects

OG_DEFAULT = False
_BUILD_VERSION = ContextVar("build_version", default=None)

B = config.SITE_BASE
WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


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


def h(text):
    return html.escape("" if text is None else str(text), quote=True)


def pct(v, digits=2):
    if v is None:
        return "–"
    return ("+" if v >= 0 else "−") + ("%." + str(digits) + "f") % abs(v) + "%"


def article_path(a):
    return "%sa/%s/" % (B, a["id"])


# ---------------------------------------------------------------- 공통 셸


# ---------------------------------------------------------------- 카드와 배지


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


# ---------------------------------------------------------------- 페이지들


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


SECTOR_KO = {"l1": "레이어1", "l2": "레이어2", "defi": "디파이", "ai": "AI", "meme": "밈", "rwa": "RWA·토큰화", "stable": "스테이블코인",
             "exchange": "거래소", "gamefi": "게임·NFT", "depin": "디핀", "privacy": "프라이버시", "infra": "인프라", "mining": "채굴", "prediction": "예측시장"}


def judge_sector_name(s):
    return SECTOR_KO.get(s, s)


def _pct(v):
    return ("+" if v > 0 else "−" if v < 0 else "") + "%.1f%%" % abs(v)


WIN_KO = {"15m": "15분", "1h": "1시간", "24h": "24시간"}


# 처음 보는 사람을 위한 한 줄 설명(무엇을 발표하는지)
WEEKDAY = "월화수목금토일"


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
    자료는 브라우저가 themes.json(Mac 이 6시간마다) · Binance · Worker /market 에서 받는다."""
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


# ---------------------------------------------------------------- Delfona 고정 페이지(소식 상세 · 하루 정리 · 소개 · 404)
# 서버에서 만들어 두는 페이지. 메뉴·안내 문구는 영·한 둘 다 넣고 문서 언어로 하나만 보인다(st.css).
# 소식 본문(제목·발췌)은 원문 언어 그대로, 하루 정리 문장은 한국어(로컬 AI가 한국어로 쓴다)

LOGO = ('<svg viewBox="0 0 100 100" fill="currentColor" aria-hidden="true"><circle cx="46" cy="54" r="30"/><path d="M75.88 70.22 A32.6 32.6 0 1 0 29.78 24.12 '
        'A34 34 0 0 1 40.31 20.48 A29.4 29.4 0 0 1 79.52 59.69 A34 34 0 0 1 75.88 70.22 Z"/></svg>')
DF_NAV = [("live", "live/", "n1", "Live", "Live", "live"), ("my", "my/", "n5", "My assets", "My", "my"), ("themes", "themes/", "n2", "Themes", "Themes", "th"),
          ("brief", "brief/", "n3", "Brief", "Brief", "br"), ("calendar", "calendar/", "n4", "Calendar", "Calendar", "ca")]
CAT_EN = {"crypto": "Crypto", "ai": "AI", "macro": "Macro"}
DAILY_EN = {"crypto": "Crypto", "econ": "Economy", "world": "World", "ai": "AI industry"}
SECTOR_EN = {"l1": "Layer 1", "l2": "Layer 2", "defi": "DeFi", "ai": "AI", "meme": "Meme", "rwa": "RWA", "stable": "Stablecoins", "exchange": "Exchanges",
             "gamefi": "Gaming & NFT", "depin": "DePIN", "privacy": "Privacy", "infra": "Infrastructure", "mining": "Mining", "prediction": "Prediction markets"}
KIND_EN = {"event": "Event", "price_recap": "Price recap / outlook", "opinion": "Opinion / analysis", "promo": "Promotional", "unrelated": "Not market-related"}
TYPE_EN = {"listing": "Listing", "hack": "Hack", "etf": "ETF", "legal": "Lawsuit / enforcement", "regulation": "Regulation / policy", "treasury": "Corporate / government buying",
           "flow": "Large transfer / selling", "partnership": "Partnership / adoption", "development": "Development / launch", "macro": "US macro", "other": "Other"}
V_EN = {"호재": "Bullish", "악재": "Bearish", "중립": "Neutral"}
V_CLS = {"호재": "u", "악재": "dn"}
WIN_EN = {"15m": "15 min", "1h": "1 hour", "24h": "24 hours"}
G_EN = {"강": "strong", "중": "medium", "약": "weak"}
DAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def L(en, ko, tag="span", cls=""):
    """영·한 문구(이미 이스케이프한 HTML) 둘 다. 보이는 쪽은 문서 언어가 정한다."""
    c = ' class="%s"' % cls if cls else ""
    return '<%s data-l="en"%s>%s</%s><%s data-l="ko"%s>%s</%s>' % (tag, c, en, tag, tag, c, ko, tag)


def ts_html(ts, f="full"):
    """시각. 처음엔 한국 시간으로 쓰고, 브라우저가 보는 사람의 현지 시각으로 바꾼다(st.js)."""
    k = util.kst(ts)
    txt = k.strftime("%H:%M") if f == "hm" else k.strftime("%Y.%m.%d %H:%M") + " KST"
    return '<time datetime="%s" data-ts="%d"%s>%s</time>' % (util.iso(ts), ts, ' data-f="hm"' if f == "hm" else "", txt)


def day_en(date):
    y, m, d = (int(x) for x in date.split("-"))
    k = util.kst(util.kst_to_ts(y, m, d, 12))
    return "%s, %s %d" % (DAY_EN[k.weekday()], k.strftime("%b"), d)


def df_page(cur, title, desc, path, body, og=None, robots="index,follow", ogtype="website"):
    """Delfona 머리글(로고 · 메뉴 · EN/한국어) + 본문 + 바닥글 + 아래 탭."""
    url = config.SITE_URL + "/" + path
    nav = "".join('<a href="%s%s" data-t="%s"%s>%s</a>' % (B, p, t, ' aria-current="page"' if k == cur else "", en) for k, p, t, en, _, _ in DF_NAV)
    tabs = "".join('<a href="%s%s"%s><i class="ti %s"></i><span data-t="%s">%s</span></a>' % (B, p, ' aria-current="page"' if k == cur else "", ic, t, short)
                   for k, p, t, _, short, ic in DF_NAV)
    img = og or (config.SITE_URL + "/og/default.jpg" if OG_DEFAULT else "")
    og_meta = ('<meta property="og:image" content="%s">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
               '<meta name="twitter:card" content="summary_large_image">\n') % h(img) if img else ""
    full = title if title.endswith(config.SITE_NAME) else "%s · %s" % (title, config.SITE_NAME)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<script>try{{document.documentElement.lang=localStorage.getItem('df-lang')||(/^ko/i.test(navigator.language)?'ko':'en')}}catch(e){{}}</script>
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
{og}<meta name="theme-color" content="#ffffff">
<link rel="icon" href="{B}assets/icon.svg" type="image/svg+xml">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="{B}assets/fonts/subsets.css?v={V}">
<link rel="stylesheet" href="{B}assets/df/lk.css?v={V}">
<link rel="stylesheet" href="{B}assets/df/st.css?v={V}">
</head>
<body class="pg-st">
<header class="hd"><div class="wrap">
  <a class="logo" href="{B}">{logo}<span class="wm">Delfona</span></a>
  <nav class="nav" aria-label="Menu">{nav}</nav>
  <div class="lang" role="group" aria-label="Language"><button type="button" data-lang="en" aria-pressed="true">EN</button><button type="button" data-lang="ko" aria-pressed="false">한국어</button></div>
</div></header>
<main id="main">
{body}
</main>
<footer class="ft"><div class="wrap">
  <nav aria-label="Footer"><a href="{B}about/">{f1}</a><a href="{B}about/#sources">{f2}</a><a href="{B}sitemap.xml">{f3}</a></nav>
  <p>{note}</p>
</div></footer>
<nav class="tabs" aria-label="Menu">{tabs}</nav>
<script>window.DF_BASE = '{B}assets/df/'; window.DF_ROOT = '{B}';</script>
<script src="{B}assets/df/data.js?v={V}"></script>
<script>DFI.init({{ n1: '라이브', n2: '테마', n3: '정리', n4: '일정', n5: '내 자산' }});</script>
<script src="{B}assets/df/st.js?v={V}"></script>
</body>
</html>
""".format(title=h(full), desc=h(desc), robots=robots, url=h(url), ogtype=ogtype, site=config.SITE_NAME, og=og_meta, B=B, V=df_ver(), logo=LOGO,
           nav=nav, tabs=tabs, body=body, f1=L("About &amp; method", "소개·방법론"), f2=L("Sources", "데이터 출처"), f3=L("Sitemap", "사이트맵"),
           note=L("Delfona shows headlines, short excerpts and links only — articles belong to their publishers. Prices and past records are for information, not investment advice; the past may not repeat.",
                  "기사 저작권은 각 매체에 있으며 Delfona는 제목·짧은 발췌·원문 링크만 보여 줘요. 시세와 지난 기록은 정보일 뿐 투자 조언이 아니에요. 지난 흐름이 다시 온다는 뜻도 아니에요."))


def verdict_en(ai):
    if not ai:
        return ""
    if ai["kind"] != "event":
        return KIND_EN.get(ai["kind"], "")
    parts = ["Event", TYPE_EN.get(ai.get("type"), "Other")]
    if ai.get("dir") in ("bullish", "bearish"):
        parts.append(ai["dir"].capitalize())
    if ai.get("str"):
        parts.append("strength %d" % ai["str"])
    return " · ".join(parts)


def page_article(a, rel, now):
    lang = a.get("lang") or "ko"
    cat = a["category"]
    src = h(a["source_name"])
    if a.get("summary"):
        lead = '<section class="box2"><h2>%s</h2><ol class="sum2" lang="ko">%s</ol><p class="fn2">%s</p></section>' % (
            L("Summary", "요약"), "".join("<li>%s</li>" % h(s) for s in a["summary"]),
            L("Written by AI from the headline and excerpt only. Check the original for details.", "AI가 원문 제목·발췌만 보고 썼어요. 정확한 내용은 원문을 확인하세요."))
    elif a.get("excerpt"):
        lead = '<section class="box2"><h2>%s</h2><p class="quote2" lang="%s">%s</p><p class="fn2" data-source-name="%s">%s</p></section>' % (
            L("From the source", "원문 발췌"), lang, h(a["excerpt"]), src,
            L("A short excerpt only — the full story is at %s." % src, "짧은 발췌만 실었어요. 전체 기사는 %s에서 볼 수 있어요." % src))
    else:
        lead = '<p class="fn2" data-source-name="%s">%s</p>' % (src, L("No excerpt yet — read the story at %s." % src, "아직 발췌가 없어요. %s에서 기사를 확인하세요." % src))
    orig = '<p class="orig" lang="%s">%s</p>' % (lang, h(a["title_orig"])) if a.get("title_orig") and a["title_orig"] != a["title"] else ""
    ai = a.get("ai")
    verdict = ""
    if ai and judge.label(ai):
        dcls = {"bullish": "u", "bearish": "dn"}.get(ai.get("dir"), "n")
        verdict = '<section class="box2"><h2>%s</h2><div class="verdict"><span class="tag %s">%s</span></div><p class="fn2">%s</p></section>' % (
            L("AI verdict", "AI 판정"), dcls, L(h(verdict_en(ai)), h(judge.label(ai))),
            L("A local AI model read the headline only. It can be wrong.", "로컬 AI 모델이 제목만 보고 판정했어요. 틀릴 수 있어요."))
    hd = a.get("headline")
    move = ""
    if hd and hd.get("r") is not None:
        r = hd["r"]
        val = '<b class="%s">%s</b>' % ("up" if r > 0 else "down" if r < 0 else "", pct(r))
        g_en, g_ko = (" · %s" % G_EN.get(hd["g"], ""), " · 반응 %s" % h(hd["g"])) if hd.get("g") else ("", "")
        move = '<section class="box2"><h2>%s</h2><p class="mk2"><span>%s</span></p><p class="fn2">%s</p></section>' % (
            L("Price after the story", "소식 이후 가격"),
            L("%s, %s after: %s%s%s" % (h(hd["asset"]), WIN_EN.get(hd["win"], h(hd["win"])), val, " vs market" if hd.get("adj") else "", g_en),
              "%s %s 뒤: %s%s%s" % (h(hd["asset"]), WIN_KO.get(hd["win"], h(hd["win"])), "시장 대비 " if hd.get("adj") else "", val, g_ko)),
            L("Measured from the story's time. Other things may have happened at the same time — this doesn't mean the story moved the price.",
              "소식 시각부터 잰 값이에요. 같은 시간에 다른 일이 겹쳤을 수 있고, 소식이 가격을 움직였다는 뜻은 아니에요."))
    rows = "".join('<li><a href="%s"><b lang="%s">%s</b><span data-source-name="%s">%s · %s</span></a></li>' % (article_path(r), r.get("lang") or "ko", h(r["title"]), h(r["source_name"]), h(r["source_name"]), ts_html(r["t0"]))
                   for r in rel)
    related_html = ('<section class="box2"><h2>%s</h2><ul class="rl">%s</ul></section>' % (L("Related stories", "관련 소식"), rows)) if rows else ""
    body = """<div class="wrap st">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="{B}live/">{live}</a><span aria-hidden="true">/</span><span>{cat}</span></nav>
  <header>
    <div class="meta"><span class="tag">{cat}</span><span data-source-name="{src}">{src}</span>{when}</div>
    <h1 lang="{lang}">{title}</h1>
    {orig}
  </header>
  {lead}
  <div class="acts"><a class="btn2 p" data-source-name="{src}" href="{url}" target="_blank" rel="noopener nofollow">{read} ↗</a><button class="btn2 g" type="button" data-copy><span class="lb">{copy}</span><span class="ok" role="status">{copied}</span></button></div>
  {verdict}
  {move}
  {related}
  <nav class="nextl" aria-label="More">
    <a href="{B}live/"><b>{nl1}</b><span>{nl1d}</span></a>
    <a href="{B}brief/"><b>{nl2}</b><span>{nl2d}</span></a>
  </nav>
</div>""".format(B=B, live=L("Live", "라이브"), cat=L(CAT_EN.get(cat, h(cat)), h(config.CATEGORY_LABEL.get(cat, cat))), src=src, when=ts_html(a["t0"]), lang=lang,
                 title=h(a["title"]), orig=orig, lead=lead, url=h(a["url"]), read=L("Read at %s" % src, "%s에서 원문 보기" % src),
                 copy=L("Copy link", "링크 복사"), copied=L("Link copied", "복사했어요"), verdict=verdict, move=move, related=related_html,
                 nl1=L("Live", "라이브"), nl1d=L("Breaking news as it lands, with prices after", "지금 나오는 속보와 그 뒤 가격"),
                 nl2=L("Brief", "정리"), nl2d=L("Stories that have run for days, on one timeline", "며칠째 이어지는 이야기를 한 시간 축에"))
    desc = (a["summary"][0] if a.get("summary") else a.get("excerpt") or a["title"])[:150]
    og = "%s/og/%s.jpg" % (config.SITE_URL, a["id"]) if a.get("og") else None
    return article_bundle.article_html(df_page("live", a["title"], desc, article_path(a)[len(B):], body, og=og, ogtype="article"))


def _dl_row(it, news=False):
    v = "기사" if news else it.get("v") or "중립"
    tag = '<span class="tag n">%s</span>' % L("Story", "기사") if news else '<span class="tag %s">%s</span>' % (V_CLS.get(v, "n"), L(V_EN.get(v, h(v)), h(v)))
    meta = [ts_html(it["t"], "hm")]
    n = it.get("n", 1)
    if news:
        meta.append("<span>%s%s</span>" % (h(it.get("src", "")), L(" +%d more" % (n - 1), " 외 %d곳" % (n - 1)) if n > 1 else ""))
    elif n > 1:
        meta.append("<span>%s</span>" % L("%d outlets" % n, "%d곳 보도" % n))
    if not news:
        meta += ["<span>%s</span>" % h(c) for c in it.get("coins", [])]
        meta += ["<span>%s</span>" % L(h(SECTOR_EN.get(s, s)), h(judge_sector_name(s))) for s in it.get("sectors", [])]
        if it.get("mw"):
            meta.append("<span>%s</span>" % L("Whole market", "시장 전체"))
    link = it.get("link") or ""
    if link.startswith(("http://", "https://")):
        meta.append('<a href="%s" target="_blank" rel="noopener nofollow">%s ↗</a>' % (h(link), L("Source", "원문")))
    return '<li class="%s"><div class="it">%s<span class="ko" lang="ko">%s</span><span class="mt2">%s</span></div></li>' % (
        "big" if it.get("s", 0) >= 2 else "", tag, h(it["ko"]), "".join(meta))


def page_daily(doc, prev, nxt, now):
    b, m = doc["balance"], doc["market"]
    tot = max(1, b["호재"] + b["악재"])
    cats = ""
    for k, name in DAILY_CATS:
        c = doc["by_cat"].get(k) or {}
        u, d = c.get("호재", 0), c.get("악재", 0)
        if u + d:
            cats += ('<li><span>{n}</span><span class="bar" role="img" aria-label="{u} / {d}"><i class="u" style="width:{wu:.1f}%"></i><i class="dn" style="width:{wd:.1f}%"></i></span>'
                     '<span class="c"><span class="up">+{u}</span> / <span class="down">−{d}</span></span></li>').format(
                n=L(DAILY_EN[k], name), u=u, d=d, wu=100 * u / (u + d), wd=100 * d / (u + d))
    sg = lambda v, c, sign: '<span class="%s">%s%d</span>' % (c, sign, v) if v else "0"
    secs = " · ".join("%s %s/%s" % (L(h(SECTOR_EN.get(s, s)), h(judge_sector_name(s))), sg(u, "up", "+"), sg(d, "down", "−"))
                      for s, u, d in doc.get("sectors", [])[:5])
    mk = ""
    if m.get("btc"):
        big = "".join('<div><span>{c}</span><b class="{cls}">{v}</b></div>'.format(c=c, v=_pct(m[k]["chg"]), cls="up" if m[k]["chg"] > 0 else "down" if m[k]["chg"] < 0 else "")
                      for c, k in (("BTC", "btc"), ("ETH", "eth")) if m.get(k))
        mv = lambda xs, cls: " · ".join('%s <b class="%s">%s</b>' % (h(c), cls, _pct(v)) for c, v in xs) or "–"
        mk = """<section class="box2"><h2>{t}</h2><div class="mk2">{big}</div>
      <p class="mv2">{lu} {up}</p><p class="mv2">{ld} {down}</p>
      <p class="fn2">{note}</p></section>""".format(
            t=L("Prices that day", "같은 날 시세"), big=big, lu=L("Top gainers", "많이 오른"), ld=L("Top losers", "많이 내린"),
            up=mv(m.get("up", []), "up"), down=mv(m.get("down", []), "down"),
            note=L("9:00 to 9:00 Korea time (00:00–00:00 UTC), %d major coins. Listed side by side — not a claim the news moved them." % m.get("n", 0),
                   "한국 시간 오전 9시부터 다음 날 9시까지, 주요 코인 %d개 기준. 소식 때문에 움직였다는 뜻은 아니에요." % m.get("n", 0)))
    sections = ""
    for k, name in DAILY_CATS:
        sec = doc["sections"].get(k) or {}
        rows = "".join(_dl_row(a, news=True) for a in sec.get("news", [])) + "".join(_dl_row(it) for it in sec.get("items", []))
        if rows:
            sections += '<section class="box2"><h2>%s</h2>%s<ol class="il">%s</ol></section>' % (
                L(DAILY_EN[k], name), ('<p class="say2" lang="ko">%s</p>' % h(sec["say"])) if sec.get("say") else "", rows)
    sched = "".join('<li><div class="it"><span class="tag n">{t}</span><span class="ko">{n}{more}</span><span class="mt2">{vs}</span></div></li>'.format(
        t=ts_html(e["ts"], "hm"), n=h(e["title"]), more=L(" +%d more" % e["more"], " 외 %d건" % e["more"]) if e.get("more") else "",
        vs=L("Past releases moved BTC %.1f× more than usual" % e["vs"], "평소보다 %.1f배 크게 흔들렸던 발표" % e["vs"]) if e.get("vs")
        else L("Forecast %s" % h(e["forecast"]), "예상 %s" % h(e["forecast"])) if e.get("forecast") else "")
        for e in doc.get("schedule", []))
    label_ko, label_en = _day_label(doc["date"]), day_en(doc["date"])
    pager = '<nav class="pager2" aria-label="Other days">{p}<a href="{B}brief/">{all}</a>{n}</nav>'.format(
        B=B, all=L("Brief", "정리"),
        p=('<a href="%sdaily/%s/">← %s</a>' % (B, prev, L(day_en(prev), _day_label(prev)))) if prev else "<span></span>",
        n=('<a href="%sdaily/%s/">%s →</a>' % (B, nxt, L(day_en(nxt), _day_label(nxt)))) if nxt else "<span></span>")
    partial = ""
    if doc["made"] < doc["end"]:
        partial = '<p class="partial2">%s</p>' % L("Day still in progress — built from what arrived by %s. The final version comes at 9:00 Korea time." % ts_html(doc["made"], "hm"),
                                                  "진행 중인 하루예요. %s까지 모인 자료로 정리했고, 오전 9시에 최종본으로 바뀌어요." % ts_html(doc["made"], "hm"))
    body = """<div class="wrap st wide dl2">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="{B}brief/">{brief}</a><span aria-hidden="true">/</span><span>{label}</span></nav>
  <header>
    <p class="stk">{k} <span>{range}</span></p>
    <h1 lang="ko">{head}</h1>
  </header>
  <p class="enonly" data-l="en">This daily recap is written in Korean by a local AI model. Menus and labels switch with the language button.</p>
  {partial}
  {insights}
  {review}
  <div class="grid2">
    <section class="box2"><h2>{bt}</h2>
      <div class="nums2"><span class="u">{lu} <b>{u}</b></span><span class="dn">{ld} <b>{d}</b></span><span>{ln} <b>{nn}</b></span></div>
      <div class="bal2" role="img" aria-label="{u} / {d}"><i class="u" style="width:{wu:.1f}%"></i><i class="dn" style="width:{wd:.1f}%"></i></div>
      <ul class="cats2">{cats}</ul>
      {secs}
      <p class="fn2">{bnote}</p>
    </section>
    {mk}
  </div>
  <section class="box2"><h2>{kt}</h2><ol class="il">{key}</ol></section>
  {sections}
  {sched}
  <p class="fn2">{note}</p>
  {pager}
</div>""".format(B=B, brief=L("Brief", "정리"), label=L(label_en, label_ko), k=L("Daily recap", "하루 정리"),
                 range=L("%s – %s KST" % (util.kst(doc["start"]).strftime("%b %-d %H:%M"), util.kst(doc["end"]).strftime("%b %-d %H:%M")),
                         "한국 시간 %s ~ %s" % (util.kst(doc["start"]).strftime("%-m/%-d %H:%M"), util.kst(doc["end"]).strftime("%-m/%-d %H:%M"))),
                 head=h(doc["headline"]), partial=partial,
                 # 핵심 3가지가 있으면 AI 리뷰는 같은 사건을 되풀이해서 싣지 않는다(옛 정리에만)
                 review=('<section class="box2"><h2>%s</h2><p class="rv" lang="ko">%s</p></section>' % (L("AI review", "AI 리뷰"), h(doc["review"]))) if doc.get("review") and not doc.get("insights") else "",
                 insights=('<section class="ins2" aria-label="%s"><h2>%s <span>%s</span></h2><ol>%s</ol></section>' % (
                     h("Insights"), L("Three things that mattered", "그날의 핵심 3가지"), L("AI (DeepSeek) · checked against the source stories", "AI(DeepSeek) · 원문 소식과 대조 확인"),
                     "".join('<li><span class="n mono">%d</span><b lang="ko">%s</b><p lang="ko">%s</p></li>' % (i + 1, h(x.get("t", "")), h(x.get("s", ""))) for i, x in enumerate(doc["insights"][:3]))))
                 if doc.get("insights") else "",
                 bt=L("Bullish vs bearish", "호재 vs 악재"), lu=L("Bullish", "호재"), ld=L("Bearish", "악재"), ln=L("Neutral", "중립"),
                 u=b["호재"], d=b["악재"], nn=b.get("중립", 0), wu=100 * b["호재"] / tot, wd=100 * b["악재"] / tot, cats=cats,
                 secs=('<p class="mv2">%s %s</p>' % (L("Sectors", "섹터"), secs)) if secs else "",
                 bnote=L("The same story is counted once. Neutral stories are left out of the bars.", "같은 소식은 하나로 묶어 셌어요. 중립은 막대에서 뺐어요."), mk=mk,
                 kt=L("Key stories", "핵심 소식"), key="".join(_dl_row(it) for it in doc["key"]), sections=sections,
                 sched=('<section class="box2"><h2>%s</h2><ol class="il">%s</ol></section>' % (L("Schedule that day", "그날 볼 일정"), sched)) if sched else "",
                 note=L("The review and section notes were written by a local AI model from the material above only. Numbers are computed by the program. News and prices from the same day are shown side by side, not as cause and effect. Not investment advice.",
                        "AI 리뷰와 분야별 문장은 로컬 AI가 위 자료만 보고 썼어요. 숫자는 프로그램이 계산했고, 소식과 시세는 같은 날 있었던 일을 나란히 둔 것이에요. 투자 조언이 아니에요."),
                 pager=pager)
    desc = (doc.get("review") or doc["headline"])[:150]
    return df_page("brief", "%s 하루 정리 — %s" % (label_ko, doc["headline"]), desc, "daily/%s/" % doc["date"], body)


def page_about(health, now):
    rows = []
    for s in config.SOURCES:
        st = health.get(s["id"], {})
        if st.get("error"):
            status = '<span class="bad2">%s</span>' % L("Error", "오류")
        elif st.get("ok"):
            status = '<span class="ok2">%s</span>' % L("OK", "정상")
        else:
            status = '<span class="wait2">%s</span>' % L("Waiting", "대기")
        cat = s["hint"]
        rows.append('<tr><th scope="row">%s</th><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            h(s["name"]), L(CAT_EN.get(cat, "Auto"), h(config.CATEGORY_LABEL.get(cat, "자동 분류"))),
            L("Korean", "한국어") if s["lang"] == "ko" else L("English", "영어"), status))
    n = len(config.SOURCES)
    en = """<section class="box2"><h2>What Delfona is</h2>
    <p>Delfona reads breaking news on crypto, the Nasdaq, the economy, AI and world affairs as it lands, labels each story bullish or bearish, and shows what prices did afterwards. It is built for people who want the market-moving part of the news without reading everything.</p>
    <ul>
      <li><b>Live</b> — breaking news in one line, with a price chart starting at the moment the story arrived.</li>
      <li><b>My assets</b> — pick coins, stocks or indices; see only their news, sudden-move alerts and a daily summary. Your picks stay in your browser.</li>
      <li><b>Themes</b> — crypto, Nasdaq, economy, AI and world: the last 24 hours of bullish/bearish flow, what changed versus usual, and related prices.</li>
      <li><b>Brief</b> — stories that run for days, laid on one timeline, with what happened so far and what today added.</li>
      <li><b>Calendar</b> — upcoming economic releases, the first-published value of past releases, and how prices moved after similar readings.</li>
    </ul></section>
  <section class="box2" id="method"><h2>How it works</h2>
    <ol>
      <li>Every few minutes we collect public real-time news feeds and the RSS of {n} outlets, and merge reports of the same story.</li>
      <li>A local AI model (Gemma 4, on the operator's Mac) writes a one-line summary and labels it bullish, bearish or neutral, with a strength from 1 to 3. It reads only the headline and short excerpt, and it can be wrong.</li>
      <li><b>Numbers come from programs, sentences from AI.</b> Prices, counts, changes and comparisons are computed by code. The AI writes only the wording, and sentences that contain numbers or causal claims are checked against the data; ones that fail are dropped.</li>
      <li><b>Price after a story</b> — measured from the story's timestamp using Binance one-minute prices (crypto) and Yahoo Finance (stocks, indices, commodities). Other events may overlap, so this is not proof of cause.</li>
      <li><b>Story threads</b> (Brief) — stories are grouped across days when they share specific people, companies or places and their wording is close.</li>
      <li><b>Similar past readings</b> (Calendar) — we compare a release's first-published value, its surprise and its recent trend with past releases (ALFRED vintage data), pick the nearest ones, and show what BTC and the Nasdaq did afterwards. Small samples are marked as such.</li>
      <li>We do not store article text. Pages show the headline, a short excerpt or summary, and a link to the original.</li>
    </ol></section>"""
    ko = """<section class="box2"><h2>Delfona는</h2>
    <p>Delfona는 크립토·나스닥·경제·AI·세계정세 속보를 나오는 대로 읽고 호재·악재를 판정해, 소식이 나온 뒤 가격이 어떻게 움직였는지 함께 보여 주는 서비스예요. 모든 뉴스를 읽지 않고도 시장을 움직이는 부분만 볼 수 있게 만들었어요.</p>
    <ul>
      <li><b>라이브</b> — 속보를 한 줄로, 소식이 나온 순간부터의 가격 차트와 함께.</li>
      <li><b>내 자산</b> — 코인·주식·지수를 골라 그 소식, 급변 알림, 하루 요약만. 고른 목록은 이 브라우저에만 저장돼요.</li>
      <li><b>테마</b> — 크립토·나스닥·경제·AI·세계: 지난 24시간 호재·악재 흐름, 평소와 달라진 점, 관련 시세.</li>
      <li><b>정리</b> — 며칠째 이어지는 이야기를 한 시간 축 위에, 지금까지와 오늘 더해진 것.</li>
      <li><b>일정</b> — 다가오는 경제 발표, 과거 발표의 처음 나온 값, 비슷한 값이 나왔을 때 가격 흐름.</li>
    </ul></section>
  <section class="box2" id="method"><h2>어떻게 동작하나요</h2>
    <ol>
      <li>몇 분마다 공개 실시간 뉴스 피드와 매체 {n}곳의 RSS를 모으고, 같은 소식은 하나로 묶어요.</li>
      <li>로컬 AI 모델(운영자 Mac의 Gemma 4)이 한 줄 요약을 쓰고 호재·악재·중립과 강도(1~3)를 붙여요. 제목과 짧은 발췌만 보고 판정하므로 틀릴 수 있어요.</li>
      <li><b>숫자는 프로그램이, 문장은 AI가.</b> 가격·개수·변화율·비교는 코드가 계산해요. AI는 문장만 쓰고, 숫자나 원인을 말하는 문장은 자료와 맞는지 검사해 틀리면 버려요.</li>
      <li><b>소식 이후 가격</b> — 소식 시각부터 Binance 1분 가격(크립토)과 Yahoo Finance(주식·지수·원자재)로 재요. 같은 시간에 다른 일이 겹칠 수 있어 원인이라는 증거는 아니에요.</li>
      <li><b>이야기 줄기</b>(정리) — 같은 인물·기업·장소를 다루고 표현이 가까운 소식을 여러 날에 걸쳐 묶어요.</li>
      <li><b>과거에 비슷했을 때</b>(일정) — 발표의 처음 나온 값, 예상과의 차이, 최근 흐름을 과거 발표(ALFRED 당시 값)와 비교해 가장 가까운 때를 고르고, 그 뒤 BTC·나스닥 흐름을 보여 줘요. 표본이 적으면 적다고 표시해요.</li>
      <li>기사 본문은 저장하지 않아요. 제목, 짧은 발췌나 요약, 원문 링크만 보여 줘요.</li>
    </ol></section>"""
    body = """<div class="wrap st ab">
  <header><p class="stk">Delfona</p><h1>{t}</h1></header>
  <div data-l="en" style="display:grid;gap:22px">{en}</div>
  <div data-l="ko" style="display:grid;gap:22px">{ko}</div>
  <section class="box2" id="sources"><h2 id="sources-h">{st}</h2>
    <div class="tw" tabindex="0" role="region" aria-labelledby="sources-h"><table><thead><tr><th scope="col">{c1}</th><th scope="col">{c2}</th><th scope="col">{c3}</th><th scope="col">{c4}</th></tr></thead><tbody>{rows}</tbody></table></div>
    <ul style="margin-top:14px">
      <li>{s1}: Binance (<a href="https://data-api.binance.vision" rel="nofollow">data-api.binance.vision</a>), Upbit</li>
      <li>{s2}: Yahoo Finance</li>
      <li>{s3}: <a href="https://alfred.stlouisfed.org" rel="nofollow">ALFRED</a> · <a href="https://fred.stlouisfed.org" rel="nofollow">FRED</a> (St. Louis Fed), <a href="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm" rel="nofollow">Federal Reserve</a>, <a href="https://www.forexfactory.com/calendar" rel="nofollow">Forex Factory</a></li>
      <li>{s4}</li>
    </ul>
  </section>
  <section class="box2"><h2>{dt}</h2><p>{dx}</p></section>
</div>""".format(t=L("About &amp; method", "소개·방법론"), en=en.replace("{n}", str(n)), ko=ko.replace("{n}", str(n)), st=L("Sources", "데이터 출처"),
                 c1=L("Outlet", "매체"), c2=L("Field", "분야"), c3=L("Language", "언어"), c4=L("Last fetch", "최근 수집"), rows="".join(rows),
                 s1=L("Crypto prices", "크립토 시세"), s2=L("Stocks, indices, commodities, FX", "주식·지수·원자재·환율"),
                 s3=L("Economic data and calendar", "경제 지표·일정"),
                 s4=L("Real-time headlines also come from public news feeds; we show a one-line summary, never the original post.",
                      "실시간 속보는 공개 뉴스 피드에서도 받아요. 원문은 싣지 않고 한 줄 요약만 보여 줘요."),
                 dt=L("Please note", "유의 사항"),
                 dx=L("Delfona gathers and organises information; it does not give investment advice. Past records measure what happened around the same time — they do not show that a story or release caused a price move, and the past may not repeat.",
                      "Delfona는 정보를 모아 정리해 보여 주는 서비스이며 투자 조언을 하지 않아요. 지난 기록은 같은 시간대에 있었던 변화를 잰 값일 뿐, 특정 소식이나 발표가 가격을 움직였다는 뜻이 아니고 앞으로도 같다는 뜻도 아니에요."))
    return df_page("", "About & method", "How Delfona collects news, labels it and measures prices afterwards — methods and data sources.", "about/", body)


def page_404(now):
    body = """<div class="wrap st nf">
  <p class="code">404</p>
  <h1>{t}</h1>
  <p class="orig">{d}</p>
  <div class="acts"><a class="btn2 p" href="{B}live/">{a}</a><a class="btn2 g" href="{B}brief/">{b}</a></div>
</div>""".format(B=B, t=L("This page isn’t here", "페이지를 찾을 수 없어요"),
                 d=L("Stories older than 30 days are removed, and some addresses changed when the site was redesigned.", "30일이 지난 소식은 정리되고, 사이트를 새로 만들며 바뀐 주소도 있어요."),
                 a=L("Go to Live", "라이브로 가기"), b=L("Open Brief", "정리 보기"))
    return df_page("", "Page not found", "This page could not be found.", "404.html", body, robots="noindex")


def redirect_page(new_path):
    url = B + new_path
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Moved · {site}</title><meta name="robots" content="noindex">
<link rel="canonical" href="{full}"><meta http-equiv="refresh" content="0; url={url}">
<script>location.replace({js} + location.search + location.hash);</script></head>
<body><p>This page moved. 주소가 바뀌었어요. <a href="{url}">Go to the new page / 새 주소로 이동</a></p></body></html>
""".format(site=config.SITE_NAME, full=h(config.SITE_URL + "/" + new_path), url=h(url), js=json.dumps(url))


def df_ver():
    """web/assets/df/ 파일 내용으로 만든 버전(바뀌면 브라우저가 새로 받는다)."""
    if _BUILD_VERSION.get() is not None:
        return _BUILD_VERSION.get()
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


def build_site(out, articles, market, cal, imp, health, now, extra=None, prerendered=None):
    # One digest per build; never retain it across a later build/source edit.
    token = _BUILD_VERSION.set(df_ver())
    try:
        return _build_site(out, articles, market, cal, imp, health, now, extra, prerendered)
    finally:
        _BUILD_VERSION.reset(token)


def _build_site(out, articles, market, cal, imp, health, now, extra=None, prerendered=None):
    """out 디렉터리에 사이트 전체를 쓴다. 기존 data/와 og/는 호출자가 미리 채워 둔다.
    extra = 새 화면 데이터 {파일 이름: 문서}. 없으면 out/data/ 에서 읽는다."""
    if extra is None:
        extra = {n: util.read_json(os.path.join(out, "data", n), None) for n in ("map.json", "moves.json", "listings.json", "events.json")}
    if prerendered is None:
        # 첫 화면 미리 그리기는 속도 개선일 뿐 — 실패해도(Node 없음, 데이터 이상) 뉴스 배포는 멈추지 않고 브라우저 렌더로 돌아간다.
        # 실패는 로그에 남기고, main 에 합치기 전 검사(SIGNAL_PRERENDER_STRICT=1)에서는 실패로 다룬다.
        try:
            prerendered = prerender.render(B)
        except Exception as e:
            if os.environ.get("SIGNAL_PRERENDER_STRICT") == "1":
                raise
            util.log("prerender skipped", type(e).__name__, str(e)[:200])
            prerendered = {}
    shutil.copytree(os.path.join(WEB, "assets"), os.path.join(out, "assets"), dirs_exist_ok=True)
    public_data.copy_daily(config.FLASH_DIR, out)
    article_bundle.bundle(WEB, out)
    util.write_text(os.path.join(out, ".nojekyll"), "")
    stamp_df_imports(out)
    util.write_text(os.path.join(out, "index.html"), page_landing_df())
    dailies = load_dailies()
    util.write_text(os.path.join(out, "live", "index.html"), prerender.insert(page_live_df(), prerendered.get("live")))
    for i, doc in enumerate(dailies):
        nxt = dailies[i - 1]["date"] if i > 0 else None
        prev = dailies[i + 1]["date"] if i + 1 < len(dailies) else None
        util.write_text(os.path.join(out, "daily", doc["date"], "index.html"), page_daily(doc, prev, nxt, now))
    # 정리: 새 정리(/brief/)가 목록을 대신한다. 날짜별 하루 정리(/daily/<날짜>/)는 그대로 둔다
    util.write_text(os.path.join(out, "brief", "index.html"), prerender.insert(page_brief_df(), prerendered.get("brief"), responsive=True))
    util.write_text(os.path.join(out, "daily", "index.html"), redirect_page("brief/"))
    for a in articles:
        util.write_text(os.path.join(out, "a", a["id"], "index.html"), page_article(a, related(a, articles), now))
    # 테마: /themes/<k>/ (첫 화면은 크립토). 옛 시그널 보드·상장 레이더는 테마로 합쳐졌다
    for k in THEME_PAGES:
        util.write_text(os.path.join(out, "themes", k, "index.html"), page_themes_df(k))
    util.write_text(os.path.join(out, "themes", "index.html"), page_themes_df("crypto"))
    # 일정: 옛 이벤트 리스크(/events/)는 새 일정(/calendar/)으로 옮겼다
    util.write_text(os.path.join(out, "calendar", "index.html"), prerender.insert(page_calendar_df(), prerendered.get("calendar")))
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
    # 상세 창의 '관련 기사'용 가벼운 목록(제목 · 시각 · 매체 · 코인 · 주소만) — feed.json 의 1/3 안팎
    util.write_json(os.path.join(out, "data", "related.json"), {"at": now, "items": [{"t0": a["t0"], "title": a["title"], "src": a["source_name"], "assets": a.get("assets", []), "url": a["url"]}
                                                                                    for a in articles[: config.FEED_JSON_LIMIT]]})
