"""Delfona 정적 사이트 빌더(2026-10-13 전면 개편).

메뉴: 지금(홈) · 속보 · 정리 · 코인 · 레이더. 실시간 속보·하루 정리는 운영자 Mac이 만든 자료(Worker /flash, flash 브랜치)를 쓰고,
시세·속보 목록처럼 자주 바뀌는 것은 브라우저 스크립트(web/assets/*.js)가 그린다. 옛 주소(live, daily, map, listings, events, me …)는 새 주소로 보낸다.
"""

import html
import json
import os
import re
import shutil

from . import config, judge, util
from . import listings as listings_mod

OG_DEFAULT = False
ASSET_VER = "0"

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



def next_big_event(ev, now, days=14):
    """다음 큰 발표 하나(중요도 높은 순, 같으면 빠른 순). 과거 흔들림 통계가 있는 것을 먼저."""
    up = [u for u in (ev or {}).get("upcoming", []) if now < u["ts"] <= now + days * 86400]
    if not up:
        return None
    return sorted(up, key=lambda u: (-u["level"], not (u.get("stats") or {}).get("abs1h"), u["ts"]))[0]



def related(a, articles, n=5):
    """같은 유형·자산의 이전 기사. 이전 기사만 고르므로 새 기사가 들어와도 페이지가 바뀌지 않는다."""
    older = [b for b in articles if b["t0"] <= a["t0"] and b["id"] != a["id"]]
    mine = set(a.get("assets", []))
    same = [b for b in older if (b.get("etype") == a.get("etype") != "other") or (mine & set(b.get("assets", [])))][:n]
    if len(same) < n:
        ids = {b["id"] for b in same}
        same += [b for b in older if b["category"] == a["category"] and b["id"] not in ids][: n - len(same)]
    return same


def events_section(ev, now):
    """레이더의 발표 쪽: 다음 큰 발표 하나 + 내 돈으로 환산 + 이번 주 일정 + 발표별 흔들림 순위. 계산기는 assets/events.js."""
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
    <h3 class="er-name">{name}</h3>
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
    return """
<section class="er" id="events" aria-labelledby="erTitle">
  <header class="rd-h">
    <p class="eyebrow">발표 레이더 · 미국 경제 발표, 한국 시간</p>
    <h2 id="erTitle">큰 발표가 나올 때, 비트코인은 얼마나 흔들릴까?</h2>
  </header>
  {hero}
  <section class="er-sec" aria-labelledby="erWeek"><h3 id="erWeek">이번 주 발표</h3><p class="er-sub">막대가 많을수록 발표 뒤 1시간 동안 평소보다 크게 흔들렸던 발표예요. 누르면 자세히 볼 수 있어요.</p>
    <ol class="er-sched">{sched}</ol></section>
  <section class="er-sec" aria-labelledby="erRank"><h3 id="erRank">어떤 발표가 가장 크게 흔들었나</h3><p class="er-sub">지난 기록에서 발표 뒤 1시간 동안 비트코인이 보통 움직인 폭(오르든 내리든)</p>
    <ol class="er-rank">{rank}</ol></section>
  <details class="lr-more"><summary>어떻게 쟀나요?</summary><ul class="lr-how">
    <li>발표 1분 전 가격과 1시간 뒤 가격을 비교한 Binance 비트코인 가격이에요. '평소'는 같은 요일·같은 시간대의 1시간이에요.</li>
    <li>발표 일정은 미국 통계청(FRED), 연준, Forex Factory에서 가져와요.</li>
    <li>지난 기록일 뿐이에요. 같은 시간에 다른 일이 겹쳤을 수 있고, 발표가 원인이라는 뜻은 아니에요. 투자 권유가 아니에요.</li>
  </ul></details>
</section>""".format(hero=hero_html, sched=sched, rank=rank or '<li class="er-none">기록이 쌓이는 중이에요.</li>')


def listings_section():
    """레이더의 상장 쪽: '새로 상장된 코인, 따라 사면 어떻게 됐나'. 숫자와 그림은 assets/listings.js가 data/listings.json으로 그린다."""
    proxy = config.UPBIT_NOTICES_PROXY[: -len("/upbit-notices")] if config.UPBIT_NOTICES_PROXY.endswith("/upbit-notices") else ""
    return """
<section class="lr" id="lr" data-src="{B}data/listings.json" data-proxy="{proxy}">
  <div id="lrLive" aria-live="polite"></div>
  <section class="lr-key" aria-labelledby="lrTitle">
    <p class="eyebrow">상장 레이더 · 업비트 원화 상장 <span id="lrN">–</span>건의 실제 기록</p>
    <h2 id="lrTitle">새로 상장된 코인, 따라 사면 어떻게 됐을까?</h2>
    <div class="lr-when" id="lrWhen" role="radiogroup" aria-label="언제 샀다면"></div>
    <p class="lr-big"><small>100명 중</small><span class="num" id="lrLoss">–</span><small>명이 하루 뒤 손해</small></p>
    <div class="lr-dots" id="lrDots" role="img"></div>
    <p class="lr-say" id="lrSay" aria-live="polite"></p>
  </section>
  <section class="lr-card" aria-labelledby="lrPathTitle">
    <h3 id="lrPathTitle">따라 산 뒤 가격은 보통 이렇게 됐어요</h3>
    <p class="lr-sub" id="lrPathSub"></p>
    <div class="lr-chart"><svg id="lrPath" role="img" aria-label="따라 산 뒤 가격의 보통 흐름"></svg></div>
    <ol class="lr-steps" id="lrSteps"></ol>
  </section>
  <section class="lr-recent" aria-labelledby="lrRecentTitle">
    <h3 id="lrRecentTitle">최근 상장</h3>
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
</section>""".format(B=B, proxy=h(proxy))


# ---------- 틀 ----------
NAV = [("home", "", "지금"), ("news", "news/", "속보"), ("brief", "brief/", "정리"), ("coins", "coins/", "코인"), ("radar", "radar/", "레이더")]
ICON = {
    "search": '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="m13.2 13.2 3.3 3.3"/></svg>',
    "sun": '<svg class="theme-sun" viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="3.5"/><path d="M10 2.5v1.6M10 15.9v1.6M2.5 10h1.6M15.9 10h1.6M4.7 4.7l1.1 1.1M14.2 14.2l1.1 1.1M4.7 15.3l1.1-1.1M14.2 5.8l1.1-1.1"/></svg>',
    "moon": '<svg class="theme-moon" viewBox="0 0 20 20" aria-hidden="true"><path d="M16 12.3A6.5 6.5 0 0 1 7.7 4a6.5 6.5 0 1 0 8.3 8.3Z"/></svg>',
    "star": '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m10 2.8 2.2 4.6 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5L2.8 8.1l5-.7z"/></svg>',
    "home": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 10.5 12 4l8 6.5V20h-5.5v-5h-5v5H4z"/></svg>',
    "news": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 3 5 13.5h6L10 21l8-10.5h-6z"/></svg>',
    "brief": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="3.5" width="14" height="17" rx="2.5"/><path d="M8.5 8h7M8.5 12h7M8.5 16h4"/></svg>',
    "coins": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9.5" cy="9.5" r="5.5"/><path d="M14.6 7.8A5.5 5.5 0 1 1 8 15.3"/></svg>',
    "radar": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="M12 12 18 6"/></svg>',
}
MARK = ('<svg class="brand__mark" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="10" fill="var(--accent)"/>'
        '<circle cx="10.5" cy="21.5" r="2.6" fill="var(--on-accent)"/><path d="M10.5 14a7.5 7.5 0 0 1 7.5 7.5M10.5 8.5a13 13 0 0 1 13 13" fill="none" '
        'stroke="var(--on-accent)" stroke-width="2.6" stroke-linecap="round"/></svg>')
FNG_KO = {"Extreme Fear": "극단적 공포", "Fear": "공포", "Neutral": "중립", "Greed": "탐욕", "Extreme Greed": "극단적 탐욕"}


def shell(page, title, desc, path, body, now, og=None, robots="index,follow", head="", data=None):
    full_title = title if title.startswith(config.SITE_NAME) else "%s · %s" % (title, config.SITE_NAME)
    url = config.SITE_URL + path[len(B) - 1:] if path.startswith(B) else config.SITE_URL + "/"
    nav = "".join('<a href="%s%s"%s>%s</a>' % (B, p, ' aria-current="page"' if k == page else "", label) for k, p, label in NAV)
    tabs = "".join('<a href="%s%s"%s>%s<span>%s</span></a>' % (B, p, ' aria-current="page"' if k == page else "", ICON[k], label) for k, p, label in NAV)
    boot = {"base": B, "page": page, "flash": config.TG_FEED}
    if data:
        boot.update(data)
    og_meta = ""
    if og or OG_DEFAULT:
        og_meta = ('<meta property="og:image" content="%s">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
                   '<meta name="twitter:card" content="summary_large_image">') % h(og or config.SITE_URL + "/og/default.jpg")
    return """<!doctype html>
<html lang="ko" data-theme="light">
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
<meta name="theme-color" content="#f2f6f9" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#080f17" media="(prefers-color-scheme: dark)">
<link rel="icon" href="{B}assets/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link href="https://cdn.jsdelivr.net/gh/wanteddev/wanted-sans@v1.0.3/packages/wanted-sans/fonts/webfonts/variable/split/WantedSansVariable.min.css" rel="stylesheet">
<link rel="stylesheet" href="{B}assets/styles.css?v={ver}">
<script>(function(){{try{{var t=localStorage.getItem('df-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.dataset.theme=t;}}catch(e){{}}}})();</script>
</head>
<body class="p-{page}">
<a class="skip" href="#main">본문으로 건너뛰기</a>
<header class="hd">
  <div class="wrap hd__in">
    <a class="brand" href="{B}" aria-label="{site} 홈">{mark}<span>delfona</span></a>
    <nav class="nav" aria-label="주 메뉴">{nav}</nav>
    <div class="hd__end">
      <a class="hd__btc" href="{B}coins/btc/" data-live="BTC"><b data-live-p>–</b><span data-live-c></span></a>
      <button class="ibtn" id="openSearch" type="button" aria-label="검색 열기 (⌘K)">{search}</button>
      <button class="ibtn" id="themeBtn" type="button" aria-label="어두운 화면으로 바꾸기">{moon}{sun}</button>
    </div>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="ft">
  <div class="wrap ft__in">
    <a class="brand" href="{B}" aria-label="{site} 홈">{mark}<span>delfona</span></a>
    <nav aria-label="바닥 메뉴"><a href="{B}about/">소개·방법론</a><a href="{B}about/#sources">데이터 출처</a><a href="{B}sitemap.xml">사이트맵</a></nav>
    <p>Delfona는 소식과 지난 기록을 모아 보여 주는 서비스예요. 투자 조언이 아니며, 지난 기록이 앞으로도 같다는 뜻은 아니에요. 기사 저작권은 각 매체에 있고, 제목·요약·원문 링크만 보여 줘요.</p>
  </div>
</footer>
<nav class="tabbar" aria-label="아래 메뉴">{tabs}</nav>
<div class="cmdk" id="cmdk" hidden>
  <div class="cmdk__scrim" data-close></div>
  <div class="cmdk__panel" role="dialog" aria-modal="true" aria-label="검색">
    <div class="cmdk__in">{search}<input id="cmdkInput" type="search" placeholder="비트코인, ETF, CPI…" autocomplete="off" aria-controls="cmdkList" aria-label="검색어"></div>
    <div class="cmdk__list" id="cmdkList" role="listbox"></div>
  </div>
</div>
<script>window.DF={boot};</script>
<script src="{B}assets/app.js?v={ver}"></script>
{head}
</body>
</html>
""".format(title=h(full_title), desc=h(desc), robots=robots, url=h(url), ogtype="article" if page == "article" else "website", site=config.SITE_NAME,
           og_meta=og_meta, B=B, ver=ASSET_VER, head=head, page=page, nav=nav, tabs=tabs, mark=MARK, search=ICON["search"], sun=ICON["sun"], moon=ICON["moon"],
           body=body, boot=json.dumps(boot, ensure_ascii=False))


def script(name):
    return '<script type="module" src="%sassets/%s?v=%s"></script>' % (B, name, ASSET_VER)


def coin_name(sym):
    names = (config.ASSETS.get(sym) or {}).get("names") or []
    ko = [n for n in names if any("가" <= ch <= "힣" for ch in n)]
    return ko[0] if ko else sym


def coin_icon(sym, size=""):
    if os.path.isfile(os.path.join(WEB, "assets", "coins", sym + ".svg")):
        return '<span class="coin-ic"%s><img src="%sassets/coins/%s.svg" alt="" width="32" height="32" loading="lazy"></span>' % (size, B, sym)
    return '<span class="coin-ic"%s aria-hidden="true">%s</span>' % (size, h(sym[:4]))


def signed(v, d=2):
    return ("+" if v > 0 else "−" if v < 0 else "") + ("%." + str(d) + "f%%") % abs(v)


def money(p):
    if p is None:
        return "–"
    if p >= 1000:
        return "${:,.0f}".format(p)
    if p >= 1:
        return "${:,.2f}".format(p)
    return "${:.6f}".format(p).rstrip("0")


def feed_item(a):
    """검색·속보 페이지용 축약 JSON."""
    ai = a.get("ai") if (a.get("ai") or {}).get("kind") == "event" else None
    return {"id": a["id"], "t0": a["t0"], "title": a["title"], "src": a["source_name"], "cat": a["category"], "assets": a.get("assets", []),
            "imp": a["importance"], "url": article_path(a), "ai": judge.label(ai) if ai else ""}


def ar_row(a, hidden=False):
    ai = a.get("ai") if (a.get("ai") or {}).get("kind") == "event" else None
    d = (ai or {}).get("dir")
    v = ('<span class="v v--%s">%s</span>' % ({"bullish": "up", "bearish": "down"}.get(d, "flat"), judge.DIR_KO.get(d, "중립"))) if d in ("bullish", "bearish") else ""
    return '<li data-cat="%s"%s><a href="%s"><span class="ar__t">%s</span><span class="ar__m">%s<span>%s</span><time datetime="%s" data-ts="%d">%s</time>%s</span></a></li>' % (
        a["category"], " hidden" if hidden else "", article_path(a), h(a["title"]), v, h(a["source_name"]), util.iso(a["t0"]), a["t0"], md_hm(a["t0"]),
        "".join('<span class="tag">%s</span>' % h(s) for s in a.get("assets", [])[:3]))


# ---------- 지금(홈) ----------
def page_home(articles, market, now, dailies, ev, lst, sig):
    tk = (market or {}).get("tickers") or {}
    fng = (market or {}).get("fng") or {}
    kimp = ((market or {}).get("kimp") or {}).get("BTC") or {}

    def pt(sym, label):
        t = tk.get(sym) or {}
        c = t.get("chg")
        return ('<a class="pt" href="{B}coins/{l}/" data-live="{s}"><span class="pt__k">{ic}{lab}</span><span class="pt__v" data-live-p>{p}</span>'
                '<span class="pt__s {cls}" data-live-c>{c}</span></a>').format(B=B, l=sym.lower(), s=sym, ic=coin_icon(sym, ' style="width:18px;height:18px"'), lab=label,
                                                                             p=money(t.get("price")), cls="up" if (c or 0) >= 0 else "down", c=signed(c) if c is not None else "")
    tiles = pt("BTC", "비트코인") + pt("ETH", "이더리움")
    if fng.get("value") is not None:
        tiles += '<div class="pt"><span class="pt__k">공포·탐욕 지수</span><span class="pt__v">%d</span><span class="pt__s muted">%s</span></div>' % (fng["value"], h(FNG_KO.get(fng.get("label"), fng.get("label") or "")))
    if kimp.get("premium") is not None:
        tiles += '<div class="pt"><span class="pt__k">김치 프리미엄</span><span class="pt__v">%s</span><span class="pt__s muted">업비트가 더 비싼 정도</span></div>' % signed(kimp["premium"], 1)

    rail = []
    if dailies:
        d = dailies[0]
        b = d["balance"]
        tot = max(1, b["호재"] + b["악재"])
        when = "오늘 지금까지" if d["made"] < d["end"] else ("어제" if now - d["end"] < 86400 else "최근")
        rail.append("""<a class="tile" href="{B}brief/{date}/"><span class="tile__k">{when} 하루 정리 · {label}<span class="more">보기</span></span>
      <span class="tile__h">{head}</span>
      <span class="bal"><span class="up">호재 {u}</span><span class="bal__bar"><i class="up" style="--w:{wu:.3f}"></i><i class="down" style="--w:{wd:.3f}"></i></span><span class="down">악재 {dn}</span></span></a>""".format(
            B=B, date=d["date"], when=when, label=_day_label(d["date"]), head=h(d["headline"]), u=b["호재"], dn=b["악재"], wu=b["호재"] / tot, wd=b["악재"] / tot))
    u = next_big_event(ev, now)
    if u:
        vs = u.get("vs_normal")
        rail.append("""<a class="tile" href="{B}radar/#events"><span class="tile__k">다음 큰 발표<span class="more">발표 레이더</span></span>
      <span class="tile__h">{name}</span><span class="tile__big" data-left="{ts}">–</span>
      <span class="tile__s">{when} · {say}</span></a>""".format(B=B, name=h(u["name"]), ts=u["ts"], when=_kst_label(u["ts"]),
                                                       say=("지난 발표 뒤 1시간, 비트코인은 평소의 %.1f배로 흔들렸어요" % vs) if vs else "지난 기록을 모으는 중이에요"))
    loss, med, n = listings_mod.follow_stats((lst or {}).get("listings", []))
    if n >= 30:
        rows = sorted([x for x in (lst or {}).get("listings", []) if x.get("trade_ts")], key=lambda x: -x["trade_ts"])
        last = rows[0] if rows else None
        rail.append("""<a class="tile" href="{B}radar/#lr"><span class="tile__k">업비트 신규 상장<span class="more">상장 레이더</span></span>
      <span class="tile__h">거래 시작 10분 뒤 따라 샀다면, 100명 중 <span class="down">{l}명</span>이 하루 뒤 손해였어요</span>
      <span class="tile__s">지난 상장 {n}건 · 가운데 값 {m} · 수수료 포함{last}</span></a>""".format(
            B=B, l=round(loss * 100), n=n, m=pct(med, 1), last=(" · 최근 %s(%s)" % (h(last["sym"]), util.kst(last["trade_ts"]).strftime("%-m/%-d"))) if last else ""))
    coins = [c for c in (sig or {}).get("coins", []) if (c.get("w") or {}).get("24h")]
    coins.sort(key=lambda c: -abs(c["w"]["24h"].get("act") or 0))
    if coins:
        mv = "".join("""<a href="{B}coins/{l}/">{ic}<span><b>{name}</b><small>{s}</small></span><span class="r {cls}">{a}<small class="muted">시장 대비 {o}</small></span></a>""".format(
            B=B, l=c["s"].lower(), ic=coin_icon(c["s"]), name=h(c.get("name") or c["s"]), s=c["s"], cls="up" if c["w"]["24h"]["act"] >= 0 else "down",
            a=signed(c["w"]["24h"]["act"], 1), o=signed(c["w"]["24h"].get("own") or 0, 1)) for c in coins[:5])
        rail.append('<section class="tile" aria-labelledby="mvT"><span class="tile__k" id="mvT">24시간 많이 움직인 코인<a class="more" href="%scoins/">전체 코인</a></span><div class="mv">%s</div></section>' % (B, mv))

    top = [a for a in articles if a["importance"] >= 3][:6] or articles[:6]
    d = util.kst(now)
    body = """
<div class="wrap">
  <section class="today">
    <p class="today__d rise">{date}</p>
    <h1 class="today__h rise" id="todayH">돈이 움직이는 소식을, 가장 먼저 쉽게</h1>
    <p class="today__sub" id="todaySub"></p>
    <div class="pulse rise" id="pulse" aria-label="지금 시세">{tiles}</div>
  </section>
  <div class="home">
    <section class="live" aria-labelledby="liveT">
      <div class="live__h"><h2 class="live__t" id="liveT"><span class="dot" aria-hidden="true"></span>실시간 속보</h2><span class="live__u" id="liveU">불러오는 중…</span></div>
      <p class="live__sub">국내외 속보를 AI가 바로 한국어로 옮기고 호재·악재를 붙여요.</p>
      <ol class="fl-list" id="liveList" aria-live="polite"><li class="fl-empty">속보를 불러오는 중이에요.</li></ol>
      <div class="live__f"><a class="more" href="{B}news/">속보 전체 보기</a></div>
    </section>
    <aside class="rail" aria-label="오늘 볼 것">{rail}</aside>
  </div>
  <section class="sec" aria-labelledby="arT"><div class="sec__h"><h2 id="arT">주요 기사</h2><a class="more" href="{B}news/#articles">기사 더 보기</a></div>
    <ol class="ar listbox">{arts}</ol></section>
</div>""".format(date="%d월 %d일 %s요일" % (d.month, d.day, WEEKDAY[d.weekday()]), tiles=tiles, B=B, rail="".join(rail), arts="".join(ar_row(a) for a in top))
    return shell("home", "Delfona — 돈이 움직이는 소식을 가장 먼저", "국내외 크립토·경제 속보를 AI가 바로 한국어로 옮기고 호재·악재를 붙여요. 하루 정리, 코인별 소식, 상장·발표 레이더까지.",
                 B, body, now, head=script("home.js"))


# ---------- 속보 ----------
def page_news(articles, now):
    rows = "".join(ar_row(a, hidden=i >= 40) for i, a in enumerate(articles[:200]))
    body = """
<div class="wrap">
  <header class="ph"><h1 class="rise">속보</h1><p class="rise">국내외 속보를 AI가 바로 한국어로 옮기고 호재·악재를 붙였어요. 같은 소식은 하나로 묶었어요.</p></header>
  <div class="seg" role="radiogroup" aria-label="속보 거르기" id="flSeg">
    <button type="button" role="radio" aria-checked="true" data-v="all">전체</button><button type="button" role="radio" aria-checked="false" data-v="호재">호재</button><button type="button" role="radio" aria-checked="false" data-v="악재">악재</button><button type="button" role="radio" aria-checked="false" data-v="big">큰 소식</button><button type="button" role="radio" aria-checked="false" data-v="mine">내 코인</button>
  </div>
  <p class="note" id="flUpd">불러오는 중…</p>
  <div class="listbox" style="margin-top:10px"><ol class="fl-list" id="flList" aria-live="polite"><li class="fl-empty">속보를 불러오는 중이에요.</li></ol></div>
  <button class="btn btn--ghost fl-more" id="flMore" type="button" hidden>더 보기</button>
  <p class="note">호재·악재는 로컬 AI가 소식 내용만 보고 붙인 일반적인 해석이에요. 가격이 그렇게 움직인다는 뜻은 아니에요.</p>

  <section class="sec" id="articles" aria-labelledby="arT">
    <div class="sec__h"><h2 id="arT">기사</h2><span class="note" style="margin:0">매체 {n}곳 · 15분마다</span></div>
    <div class="seg" role="radiogroup" aria-label="기사 분야" id="arSeg">
      <button type="button" role="radio" aria-checked="true" data-c="all">전체</button><button type="button" role="radio" aria-checked="false" data-c="crypto">크립토</button><button type="button" role="radio" aria-checked="false" data-c="ai">AI</button><button type="button" role="radio" aria-checked="false" data-c="macro">경제</button>
    </div>
    <ol class="ar listbox" id="arList" style="margin-top:12px">{rows}</ol>
    <button class="btn btn--ghost fl-more" id="arMore" type="button">기사 더 보기</button>
  </section>
</div>""".format(n=len(config.SOURCES), rows=rows)
    return shell("news", "속보 — 국내외 속보를 한국어로, 호재·악재와 함께", "국내외 크립토·경제·세계 속보를 AI가 바로 한국어로 옮기고 호재·악재를 붙여요. 기사 57곳도 함께 모아요.",
                 B + "news/", body, now, head=script("news.js"))


# ---------- 코인 ----------
def coin_rows(sig):
    by = {c["s"]: c for c in (sig or {}).get("coins", [])}
    order = sorted(config.ASSETS, key=lambda s: -((by.get(s) or {}).get("cap") or 0))
    return order, by


def page_coins(sig, now):
    order, by = coin_rows(sig)
    rows = []
    for s in order:
        c = by.get(s) or {}
        act = ((c.get("w") or {}).get("24h") or {}).get("act")
        rows.append("""<div class="cl__row" data-live="{s}">{ic}<a class="cl__n" href="{B}coins/{l}/"><b>{name}</b><small>{s}</small></a>
      <span class="cl__news" data-news="{s}">–</span>
      <span class="cl__p"><b data-live-p>{p}</b><small class="{cls}" data-live-c>{a}</small></span>
      <button class="star" type="button" data-star="{s}" aria-pressed="false" aria-label="{name} 내 코인에 담기">{star}</button></div>""".format(
            s=s, l=s.lower(), B=B, ic=coin_icon(s), name=h(coin_name(s)), p=money(c.get("price")), cls="up" if (act or 0) >= 0 else "down",
            a=signed(act) if act is not None else "", star=ICON["star"]))
    body = """
<div class="wrap">
  <header class="ph"><h1 class="rise">코인</h1><p class="rise">별표를 누르면 '내 코인'으로 담겨요. 지금 화면 위쪽 시세와 속보의 '내 코인' 거르기에 함께 보여요.</p></header>
  <div class="cl">{rows}</div>
  <p class="note">시세는 바이낸스 달러(USDT) 가격, 등락은 24시간 기준이에요. 오늘 소식 수는 지난 24시간 속보에서 그 코인을 다룬 것이에요.</p>
</div>""".format(rows="".join(rows))
    return shell("coins", "코인 — 시세와 오늘 소식", "주요 코인 25개의 시세와 지난 24시간 호재·악재 소식을 한눈에.", B + "coins/", body, now)


def page_coin(sym, sig, articles, lst, now):
    c = ((sig or {}).get("coins") and {x["s"]: x for x in sig["coins"]}.get(sym)) or {}
    w = (c.get("w") or {}).get("24h") or {}
    name = coin_name(sym)
    facts = []
    if w:
        facts.append('<div><dt>24시간 등락</dt><dd class="%s">%s<small>시장 전체를 뺀 몫 %s</small></dd></div>' % ("up" if (w.get("act") or 0) >= 0 else "down", signed(w.get("act") or 0), signed(w.get("own") or 0)))
        if w.get("volr") is not None:
            facts.append('<div><dt>업비트 거래대금</dt><dd>평소의 %.1f배<small>지난 7일 같은 시간대와 비교</small></dd></div>' % w["volr"])
        if w.get("kimp") is not None:
            facts.append('<div><dt>김치 프리미엄</dt><dd>%s<small>업비트가 해외보다 비싼 정도</small></dd></div>' % signed(w["kimp"], 1))
    ups = [x for x in (lst or {}).get("listings", []) if x.get("sym") == sym and x.get("trade_ts")]
    if ups:
        x = max(ups, key=lambda x: x["trade_ts"])
        facts.append('<div><dt>업비트 원화 상장</dt><dd>%s<small>거래 시작일</small></dd></div>' % util.kst(x["trade_ts"]).strftime("%Y.%m.%d"))
    arts = [a for a in articles if sym in a.get("assets", [])][:12]
    body = """
<div class="wrap" data-coin="{s}">
  <div class="cp-head rise">{ic}<div><h1>{name}</h1><small>{s} · <a class="more" href="{B}coins/">전체 코인</a></small></div>
    <button class="star" type="button" data-star="{s}" aria-pressed="false" aria-label="{name} 내 코인에 담기" style="margin-inline-start:auto">{star}</button></div>
  <div data-live="{s}"><p class="cp-price" data-live-p>{p}</p><p class="cp-chg {cls}" data-live-c>{a}</p></div>
  <div class="cp-chart" id="cpChart" data-sym="{s}" role="img" aria-label="{name} 24시간 가격과 이 코인 소식이 나온 때"></div>
  <p class="note">점은 이 코인을 다룬 속보가 나온 때예요(초록 호재 · 빨강 악재 · 회색 중립).</p>
  {facts}
  <section class="sec" aria-labelledby="cfT"><div class="sec__h"><h2 id="cfT">이 코인 속보</h2></div>
    <div class="listbox"><ol class="fl-list" id="coinFlash"><li class="fl-empty">속보를 불러오는 중이에요.</li></ol></div></section>
  <section class="sec" aria-labelledby="caT"><div class="sec__h"><h2 id="caT">관련 기사</h2></div>
    <ol class="ar listbox">{arts}</ol></section>
</div>""".format(s=sym, B=B, ic=coin_icon(sym), name=h(name), star=ICON["star"], p=money(c.get("price")), cls="up" if (w.get("act") or 0) >= 0 else "down",
                 a=signed(w["act"]) if w.get("act") is not None else "", facts=('<dl class="cp-facts sec">%s</dl>' % "".join(facts)) if facts else "",
                 arts="".join(ar_row(a) for a in arts) or '<li class="fl-empty">최근 30일 동안 이 코인을 다룬 기사가 없어요.</li>')
    return shell("coins", "%s(%s) — 시세와 오늘 소식" % (name, sym), "%s(%s)의 24시간 가격, 이 코인을 다룬 속보와 호재·악재, 관련 기사." % (name, sym),
                 B + "coins/%s/" % sym.lower(), body, now, head=script("coin.js"))


# ---------- 하루 정리 ----------
def _fi(it):
    v = it.get("v") or "중립"
    cls = {"호재": "up", "악재": "down"}.get(v, "flat")
    tags = "".join('<span class="tag">%s</span>' % h(c) for c in it.get("coins", []))
    tags += "".join('<span class="tag tag--line">%s 섹터</span>' % h(judge_sector_name(s)) for s in it.get("sectors", []))
    tags += '<span class="tag tag--line">시장 전체</span>' if it.get("mw") else ""
    link = it.get("link") or ""
    link = ('<a href="%s" target="_blank" rel="noopener nofollow">관련 기사</a>' % h(link)) if link.startswith(("http://", "https://")) else ""
    n = '<span>%d곳 보도</span>' % it["n"] if it.get("n", 1) > 1 else ""
    return '<li class="fi%s"><span class="v v--%s">%s</span><div><span class="fi__t">%s</span><span class="fi__m"><time>%s</time>%s%s%s</span></div></li>' % (
        " is-big" if it.get("s", 0) >= 2 else "", cls, h(v), h(it["ko"]), hm(it["t"]), n, tags, link)


def _fi_news(a):
    link = a.get("link") or ""
    src = '<span>%s%s</span>' % (h(a.get("src", "")), (" 외 %d곳" % (a["n"] - 1)) if a.get("n", 1) > 1 else "")
    link = ('<a href="%s" target="_blank" rel="noopener nofollow">기사</a>' % h(link)) if link.startswith(("http://", "https://")) else ""
    return '<li class="fi"><span class="v v--flat">기사</span><div><span class="fi__t">%s</span><span class="fi__m"><time>%s</time>%s%s</span></div></li>' % (h(a["ko"]), hm(a["t"]), src, link)


def page_brief(doc, prev, nxt, now):
    b, m = doc["balance"], doc["market"]
    tot = max(1, b["호재"] + b["악재"])
    cats = "".join('<li><span>{n}</span><span class="bal__bar"><i class="up" style="--w:{wu:.3f}"></i><i class="down" style="--w:{wd:.3f}"></i></span><span class="up">{u}</span><span class="down">{d}</span></li>'.format(
        n=name, u=c["호재"], d=c["악재"], wu=c["호재"] / max(1, c["호재"] + c["악재"]), wd=c["악재"] / max(1, c["호재"] + c["악재"]))
        for k, name in DAILY_CATS for c in [doc["by_cat"].get(k, {"호재": 0, "악재": 0})] if c["호재"] + c["악재"])
    secs = "".join('<li><span class="tag tag--line">{n} 섹터</span><span class="up">호재 {u}</span><span class="down">악재 {d}</span></li>'.format(n=h(judge_sector_name(s)), u=u, d=d)
                   for s, u, d in doc.get("sectors", [])[:5])
    mk = ""
    if m.get("btc"):
        big = "".join('<div><dt>{c}</dt><dd class="{cls}">{v}</dd></div>'.format(c=c, v=signed(m[k]["chg"], 1), cls="up" if m[k]["chg"] >= 0 else "down")
                      for c, k in (("비트코인", "btc"), ("이더리움", "eth")) if m.get(k))
        mv = lambda xs, cls: " · ".join('%s <b class="%s">%s</b>' % (h(c), cls, signed(v, 1)) for c, v in xs) or "–"
        mk = """<section class="card bf-card"><h2 class="bf-card__t">같은 날 시세</h2><dl class="bf-big">{big}</dl>
          <p class="bf-mv"><span>많이 오른</span>{up}</p><p class="bf-mv"><span>많이 내린</span>{down}</p>
          <p class="note">한국 시간 오전 9시부터 다음 날 9시까지, 주요 코인 {n}개 기준. 소식 때문에 움직였다는 뜻은 아니에요.</p></section>""".format(
            big=big, up=mv(m.get("up", []), "up"), down=mv(m.get("down", []), "down"), n=m.get("n", 0))
    sections = ""
    for k, name in DAILY_CATS:
        sec = doc["sections"].get(k) or {}
        rows = "".join(_fi_news(a) for a in sec.get("news", [])) + "".join(_fi(it) for it in sec.get("items", []))
        if rows:
            sections += '<section class="sec"><div class="sec__h"><h2>{n}</h2></div>{say}<div class="listbox"><ol class="fl-list">{rows}</ol></div></section>'.format(
                n=name, say=('<p class="bf-say">%s</p>' % h(sec["say"])) if sec.get("say") else "", rows=rows)
    sched = "".join('<li><time>{t}</time><span><b>{n}</b>{more}<small>{vs}</small></span></li>'.format(
        t=hm(e["ts"]), n=h(e["title"]), more=(' 외 %d건' % e["more"]) if e.get("more") else "",
        vs=("평소보다 %.1f배 크게 흔들렸던 발표" % e["vs"]) if e.get("vs") else ("예상 %s" % h(e["forecast"]) if e.get("forecast") else ""))
        for e in doc.get("schedule", []))
    pager = '<nav class="bf-pager" aria-label="다른 날">{p}<a href="{B}brief/">모든 정리</a>{n}</nav>'.format(
        B=B, p=('<a href="%sbrief/%s/">← %s</a>' % (B, prev, _day_label(prev))) if prev else "<span></span>",
        n=('<a href="%sbrief/%s/">%s →</a>' % (B, nxt, _day_label(nxt))) if nxt else "<span></span>")
    partial = ('<p class="bf-partial">진행 중인 하루예요. %s까지 모인 자료로 정리했고, 오전 9시에 최종본으로 바뀌어요.</p>' % util.kst(doc["made"]).strftime("%-m/%-d %H:%M")) if doc["made"] < doc["end"] else ""
    body = """
<div class="wrap bf">
  <header class="ph"><p class="eyebrow rise">{label} 하루 정리 · 한국 시간 {a} ~ {b2}</p><h1 class="rise">{head}</h1>{partial}</header>
  {review}
  <div class="bf-grid">
    <section class="card bf-card"><h2 class="bf-card__t">호재 vs 악재</h2>
      <div class="bf-bal"><b class="up">{u}</b><span class="bal__bar"><i class="up" style="--w:{wu:.3f}"></i><i class="down" style="--w:{wd:.3f}"></i></span><b class="down">{d}</b></div>
      <ul class="bf-cats">{cats}</ul>{secs}
      <p class="note">같은 소식은 하나로 묶어 셌어요. 중립 {nn}건은 빼고 셌어요.</p></section>
    {mk}
  </div>
  <section class="sec"><div class="sec__h"><h2>핵심 소식</h2></div><div class="listbox"><ol class="fl-list">{key}</ol></div></section>
  {sections}
  {sched}
  <p class="note">AI 리뷰와 분야별 문장은 로컬 AI가 위 자료만 보고 썼어요. 숫자는 프로그램이 계산했고, 소식과 시세는 같은 날 있었던 일을 나란히 둔 것이에요. 투자 조언이 아니에요.</p>
  {pager}
</div>""".format(label=_day_label(doc["date"]), a=util.kst(doc["start"]).strftime("%-m/%-d %H:%M"), b2=util.kst(doc["end"]).strftime("%-m/%-d %H:%M"),
                 head=h(doc["headline"]), partial=partial,
                 review=('<section class="bf-review rise"><p class="bf-review__k">AI 리뷰</p><p>%s</p></section>' % h(doc["review"])) if doc.get("review") else "",
                 u=b["호재"], d=b["악재"], wu=b["호재"] / tot, wd=b["악재"] / tot, nn=b.get("중립", 0), cats=cats, secs=('<ul class="bf-secs">%s</ul>' % secs) if secs else "",
                 mk=mk, key="".join(_fi(it) for it in doc["key"]), sections=sections,
                 sched=('<section class="sec"><div class="sec__h"><h2>오늘 볼 일정</h2><a class="more" href="%sradar/#events">발표 레이더</a></div><ul class="bf-ev listbox">%s</ul></section>' % (B, sched)) if sched else "",
                 pager=pager)
    return shell("brief", "%s 하루 정리 — %s" % (_day_label(doc["date"]), doc["headline"]), (doc.get("review") or doc["headline"])[:150],
                 B + "brief/%s/" % doc["date"], body, now)


def page_brief_index(dailies, now):
    rows = "".join('<li><a href="{B}brief/{d}/"><span class="ar__m">{label}{p}</span><span class="ar__t">{head}</span><span class="ar__m"><span class="up">호재 {u}</span><span class="down">악재 {dn}</span></span></a></li>'.format(
        B=B, d=x["date"], label=_day_label(x["date"]), p=" · 진행 중" if x["made"] < x["end"] else "", head=h(x["headline"]), u=x["balance"]["호재"], dn=x["balance"]["악재"]) for x in dailies) \
        or '<li class="fl-empty">아직 정리가 없어요. 매일 오전 9시에 전날 하루를 정리해요.</li>'
    body = """
<div class="wrap">
  <header class="ph"><h1 class="rise">하루 정리</h1><p class="rise">매일 오전 9시, 전날 하루(오전 9시 ~ 다음 날 9시)의 크립토·경제·세계정세·AI 업계 소식을 AI가 정리해요.</p></header>
  <ol class="ar listbox">{rows}</ol>
</div>""".format(rows=rows)
    return shell("brief", "하루 정리", "매일 오전 9시, 전날의 크립토·경제·세계정세·AI 업계 소식을 AI가 정리해요.", B + "brief/", body, now)


# ---------- 레이더 ----------
def page_radar(ev, now):
    body = """
<div class="wrap rd">
  <header class="ph"><h1 class="rise">레이더</h1><p class="rise">돈이 크게 움직이는 두 순간을 지난 기록으로 보여 줘요. 새 코인이 상장될 때, 그리고 미국 큰 경제 발표가 나올 때.</p></header>
  <nav class="seg rd-nav" aria-label="레이더 고르기"><a href="#lr" aria-current="true" data-rd="lr">상장 레이더</a><a href="#events" data-rd="events">발표 레이더</a></nav>
  {lst}
  {evs}
</div>""".format(lst=listings_section(), evs=events_section(ev, now))
    return shell("radar", "레이더 — 새 코인 상장과 큰 경제 발표", "업비트 새 코인을 따라 샀다면 어땠는지, 미국 큰 발표 때 비트코인이 얼마나 흔들렸는지 실제 기록으로 보여 줘요.",
                 B + "radar/", body, now, head=script("listings.js") + script("events.js") + script("radar.js"))


# ---------- 기사 ----------
def page_article(a, rel, now):
    if a.get("summary"):
        lead = '<ul>%s</ul><p class="note">요약은 AI가 원문 제목·발췌만으로 썼어요. 정확한 내용은 원문에서 확인하세요.</p>' % "".join("<li>%s</li>" % h(s) for s in a["summary"])
    elif a.get("excerpt"):
        lead = '<p>%s</p><p class="note">원문 발췌 · %s</p>' % (h(a["excerpt"]), h(a["source_name"]))
    else:
        lead = '<p class="muted">요약이 아직 없어요. 원문에서 내용을 확인하세요.</p>'
    orig = '<p class="note" lang="en">%s</p>' % h(a["title_orig"]) if a.get("title_orig") and a["title_orig"] != a["title"] else ""
    ai = a.get("ai")
    ai_line = ('<p class="art__ai"><b>AI 판정</b> · %s<br><span class="note">로컬 AI(Gemma 4)가 제목만 보고 판정했어요. 틀릴 수 있어요.</span></p>' % h(judge.label(ai))) if ai else ""
    chips = "".join('<a class="tag" href="%scoins/%s/">%s</a>' % (B, s.lower(), h(s)) for s in a.get("assets", [])[:4] if s in config.ASSETS)
    body = """
<article class="wrap art">
  <p class="eyebrow"><a href="{B}news/#articles">기사</a> · {cat}</p>
  <h1>{title}</h1>{orig}
  <p class="art__m"><span>{src}</span><time datetime="{iso}">{when}</time>{chips}</p>
  <div class="art__body">{lead}</div>
  {ai}
  <p class="art__go"><a class="btn btn--primary" href="{url}" target="_blank" rel="noopener nofollow">원문 보기</a></p>
  <section class="sec"><div class="sec__h"><h2>관련 기사</h2></div><ol class="ar listbox">{rel}</ol></section>
</article>""".format(B=B, cat=config.CATEGORY_LABEL.get(a["category"], ""), title=h(a["title"]), orig=orig, src=h(a["source_name"]), iso=util.iso(a["t0"]),
                     when=util.kst(a["t0"]).strftime("%Y.%m.%d %H:%M"), chips=chips, lead=lead, ai=ai_line, url=h(a["url"]),
                     rel="".join(ar_row(r) for r in rel) or '<li class="fl-empty">관련 기사가 없어요.</li>')
    desc = (a["summary"][0] if a.get("summary") else a.get("excerpt") or a["title"])[:150]
    og = "%s/og/%s.jpg" % (config.SITE_URL, a["id"]) if a.get("og") else None
    return shell("article", a["title"], desc, article_path(a), body, now, og=og)


# ---------- 소개 ----------
def page_about(health, now):
    rows = []
    for s in config.SOURCES:
        st = health.get(s["id"], {})
        status = ('<span class="up">정상</span>' if not st.get("error") else '<span class="down">오류</span>') if st.get("ok") or st.get("error") else '<span class="muted">대기</span>'
        rows.append('<li><span><b>%s</b><small>%s · %s</small></span>%s</li>' % (h(s["name"]), config.CATEGORY_LABEL.get(s["hint"], "자동 분류"), "한국어" if s["lang"] == "ko" else "영어", status))
    body = """
<div class="wrap ab">
  <header class="ph"><h1 class="rise">Delfona 소개</h1><p class="rise">돌고래가 소리로 바닷속을 읽듯, Delfona는 쏟아지는 소식 속에서 돈이 움직이는 신호를 골라 쉬운 한국어로 보여 줘요.</p></header>
  <section class="card"><h2>어떻게 동작하나요</h2><ol class="ab-steps">
    <li>국내외 속보 채널을 실시간으로 받아, 운영자 Mac의 로컬 AI(Gemma 4)가 한국어 한 줄로 옮기고 호재·악재·코인·섹터를 붙여요. 같은 소식은 하나로 묶어요.</li>
    <li>국내외 매체 {n}곳의 기사를 15분마다 모으고, 기사마다 사건인지와 호재·악재를 판정해요.</li>
    <li>매일 오전 9시, 전날 하루를 정리해요. 숫자는 프로그램이 계산하고 AI는 문장만 써요.</li>
    <li>업비트 상장 기록과 미국 경제 발표 일정은 지난 가격과 맞춰 '그때 어땠는지'를 계산해요.</li>
    <li>기사·속보의 원문은 싣지 않아요. 우리가 쓴 한 줄, 요약, 원문 링크만 보여 줘요.</li></ol></section>
  <section class="card" id="method"><h2>계산 방법</h2><ol class="ab-steps">
    <li><b>상장 레이더</b>: 업비트 원화 상장마다 거래 시작 첫 1분봉 시가를 기준으로 24시간 동안의 업비트 1분 가격을 모아요. '거래 시작 N분 뒤에 샀다면'은 그 분 종가에 사서 하루 뒤 종가에 판 수익에서 수수료(0.05%×2)를 뺀 값이에요. 시세가 없는 코인과 스테이블코인은 뺐어요.</li>
    <li><b>발표 레이더</b>: 과거 같은 발표마다 발표 직전 1분 바이낸스 비트코인 종가 대비 1시간 뒤 변화를 재고, 그 크기의 가운데 값과 상위 10%를 보여 줘요. '평소의 몇 배'는 발표가 없던 같은 시각 1시간과 비교한 값이에요. 표본이 8건 미만이면 숨겨요.</li>
    <li><b>코인</b>: '시장 전체를 뺀 몫'은 실제 등락에서 시장 전체(그 코인을 뺀 나머지 코인의 시총 가중 움직임 × 그 코인의 민감도)를 뺀 값이에요. 거래대금은 지난 7일 같은 길이 구간의 가운데 값과 비교해요.</li>
    <li><b>호재·악재</b>: AI가 소식 내용만 보고 붙인 일반적인 해석이에요. 지난 기록상 뉴스 뒤 가격 변화는 평소와 크게 다르지 않았어요. 판정은 매매 신호가 아니에요.</li></ol></section>
  <section class="card" id="sources"><h2>데이터 출처</h2>
    <ul class="ab-src">{rows}</ul>
    <ul class="ab-steps" style="margin-top:14px">
      <li>실시간 속보: 국내외 공개 속보 채널. 원문은 싣지 않아요.</li>
      <li>시세·1분봉: Binance 공개 API, 국내 시세·공지: 업비트 공개 API(업비트 공지는 Cloudflare를 거쳐 받아요)</li>
      <li>공포·탐욕 지수: alternative.me · 환율: Exchange Rate API · 경제 일정: Forex Factory, FRED, 연준 FOMC 일정</li></ul></section>
  <section class="card"><h2>유의 사항</h2><p>Delfona는 정보를 모아 보여 주는 서비스이며 투자 조언을 하지 않아요. 지난 기록은 같은 시간대에 일어난 변화를 잰 값으로, 특정 뉴스나 발표가 가격을 움직였다는 뜻이 아니에요.</p></section>
</div>""".format(n=len(config.SOURCES), rows="".join(rows))
    return shell("about", "소개·방법론", "Delfona가 소식을 모으고 판정하고 계산하는 방법, 데이터 출처.", B + "about/", body, now)


def redirect_page(new_path):
    """옛 주소 → 새 주소. 새 주소에 #이 있으면 옛 주소의 #가 없을 때 그것을 쓴다."""
    path, _, frag = new_path.partition("#")
    url = B + path
    return """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>주소가 바뀌었어요 · Delfona</title><meta name="robots" content="noindex">
<link rel="canonical" href="{full}"><meta http-equiv="refresh" content="0; url={url}{hash}">
<script>location.replace({js} + location.search + (location.hash || {jh}));</script></head>
<body><p>주소가 바뀌었어요. <a href="{url}{hash}">새 주소로 가기</a></p></body></html>
""".format(full=h(config.SITE_URL + "/" + path), url=h(url), hash=h("#" + frag) if frag else "", js=json.dumps(url), jh=json.dumps("#" + frag if frag else ""))


def page_404(now):
    body = '<div class="wrap"><header class="ph"><h1>페이지를 찾을 수 없어요</h1><p>30일이 지난 기사는 정리돼요. <a class="more" href="%snews/">속보로 가기</a></p></header></div>' % B
    return shell("404", "페이지 없음", "페이지를 찾을 수 없어요.", B + "404.html", body, now, robots="noindex")


def sitemap(articles, now, dailies=()):
    urls = [("", now), ("news/", now), ("brief/", now), ("coins/", now), ("radar/", now), ("about/", now)]
    urls += [("coins/%s/" % s.lower(), now) for s in config.ASSETS]
    urls += [("brief/%s/" % d["date"], d["made"]) for d in dailies]
    urls += [("a/%s/" % a["id"], a["t0"]) for a in articles]
    body = "".join("<url><loc>%s/%s</loc><lastmod>%s</lastmod></url>" % (config.SITE_URL, p, util.iso(t)[:10]) for p, t in urls)
    return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % body


# ---------- 사이트 쓰기 ----------
def build_site(out, articles, market, cal, imp, health, now, extra=None):
    """out 디렉터리에 사이트 전체를 쓴다. 기존 data/와 og/는 호출자가 미리 채워 둔다.
    extra = 화면 데이터 {파일 이름: 문서}. 없으면 out/data/ 에서 읽는다."""
    if extra is None:
        extra = {n: util.read_json(os.path.join(out, "data", n), None) for n in ("listings.json", "events.json", "signals.json")}
    if extra.get("signals.json") is None:
        extra["signals.json"] = util.read_json(os.path.join(out, "data", "signals.json"), None)
    global ASSET_VER
    digest = []
    for name in sorted(os.listdir(os.path.join(WEB, "assets"))):
        if os.path.isfile(os.path.join(WEB, "assets", name)):
            with open(os.path.join(WEB, "assets", name), "rb") as f:
                digest.append(util.short_hash(f.read().decode("latin-1")))
    ASSET_VER = util.short_hash("".join(digest))
    shutil.copytree(os.path.join(WEB, "assets"), os.path.join(out, "assets"), dirs_exist_ok=True)
    util.write_text(os.path.join(out, ".nojekyll"), "")
    lst, ev, sig = extra.get("listings.json"), extra.get("events.json"), extra.get("signals.json")
    dailies = load_dailies()
    W = lambda p, html: util.write_text(os.path.join(out, p), html)
    W("index.html", page_home(articles, market, now, dailies, ev, lst, sig))
    W("news/index.html", page_news(articles, now))
    W("coins/index.html", page_coins(sig, now))
    for s in config.ASSETS:
        W("coins/%s/index.html" % s.lower(), page_coin(s, sig, articles, lst, now))
    for i, doc in enumerate(dailies):
        nxt = dailies[i - 1]["date"] if i > 0 else None
        prev = dailies[i + 1]["date"] if i + 1 < len(dailies) else None
        W("brief/%s/index.html" % doc["date"], page_brief(doc, prev, nxt, now))
        W("daily/%s/index.html" % doc["date"], redirect_page("brief/%s/" % doc["date"]))
    W("brief/index.html", page_brief_index(dailies, now))
    W("radar/index.html", page_radar(ev, now))
    for a in articles:
        W("a/%s/index.html" % a["id"], page_article(a, related(a, articles), now))
    W("about/index.html", page_about(health, now))
    W("404.html", page_404(now))
    # 바뀐 주소: 옛 주소는 새 주소로 바로 보낸다
    for old_path, new_path in (("live", "news/"), ("daily", "brief/"), ("map", "coins/"), ("me", "coins/"), ("listings", "radar/#lr"), ("events", "radar/#events"),
                               ("feed", "news/"), ("markets", "coins/"), ("calendar", "radar/#events"), ("impact", "news/"), ("patterns", "news/"), ("predict", "news/")):
        W("%s/index.html" % old_path, redirect_page(new_path))
    W("sitemap.xml", sitemap(articles, now, dailies))
    W("robots.txt", "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % config.SITE_URL)
    util.write_json(os.path.join(out, "data", "feed.json"), {"at": now, "items": [feed_item(a) for a in articles[: config.FEED_JSON_LIMIT]]})
