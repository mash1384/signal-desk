"""첫 페이지 '지구' 장면의 테마별 AI 요약: 크립토 · 나스닥(미국 증시) · 경제 · AI.

지난 24시간 실시간 속보(flash.json, 판정된 소식)를 네 테마로 나누고, 기사 제목(articles.json)을 참고 자료로 더해
로컬 Gemma가 테마마다 문장 6개(한국어·영어 짝)와 오늘의 한 줄을 쓴다.
하루 정리와 같은 규칙: 자료에 없는 숫자 금지 · '~때문에 올랐다' 같은 인과 금지 · 매매 권유 금지. 어긴 문장은 빼고, 모자라면 다시 쓰게 한다.
건수(n·호재·악재)는 프로그램이 판정된 속보만으로 센다.

테마 화면(/themes/)용 숫자도 함께 만든다(프로그램이 계산, AI 아님): 1시간 단위 소식·호재·악재(hours), 섹터별 분포(sectors),
주요 소식(top), 자산별 언급(mentions), 요약 1~4번 문장의 근거 소식(refs).
자료는 판정 DB에서 지난 24시간을 같은 소식끼리 묶어 쓴다(flash.json 은 최근 400건이라 24시간이 안 된다). DB를 못 열면 flash.json 으로.

결과: ~/.signal/flash-branch/daily/themes.json → tg_publish가 flash 브랜치로 올린다(사이트는 raw.githubusercontent로 읽는다).
설치: ~/.signal/tgvenv/bin/python tools/theme_brief.py --install   (launchd com.signal.themes, 3시간마다, 로그 ~/.signal/themes.log)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~/.signal")
BRANCH = os.path.join(HOME, "flash-branch")
OUT = os.path.join(BRANCH, "daily", "themes.json")
OLLAMA = os.environ.get("SIGNAL_OLLAMA", "http://localhost:11434")
MODEL = os.environ.get("SIGNAL_TG_MODEL", "gemma4:26b")
ARTICLES = "https://mash1384.github.io/signal-desk/data/articles.json"
LABEL = "com.signal.themes"
EVERY = 3 * 3600

NAME = {"crypto": "크립토", "nasdaq": "나스닥·미국 증시", "econ": "경제", "ai": "AI"}
CRYPTO_W = re.compile(r"비트코인|이더리움|코인|가상자산|암호화폐|스테이블코인|거래소|ETF|토큰|블록체인|디파이|채굴|온체인|NFT|웹3")
STOCK_W = re.compile(r"나스닥|S&P|다우|미국 증시|뉴욕 증시|미 증시|미국 주식|빅테크|엔비디아|애플|테슬라|마이크로소프트|메타|아마존|알파벳|구글|반도체|기술주|주가|증시")
STOCK_EN = re.compile(r"Nasdaq|S&P|Dow|Wall Street|stocks?\b|equities|Nvidia|Apple|Tesla|Microsoft|Amazon|Alphabet|Meta\b|chipmakers?", re.I)
AI_W = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])|인공지능|오픈AI|OpenAI|앤트로픽|Anthropic|엔비디아|챗GPT|ChatGPT|LLM|딥시크|제미나이|데이터센터|xAI")
ECON_W = re.compile(r"연준|Fed|FOMC|CPI|PPI|물가|인플레이션|금리|국채|고용|실업|GDP|PCE|소매판매|달러화|달러 지수|달러지수|달러 강세|달러 약세|달러 가치|DXY|환율|엔화|위안화|원화|유로화|원/달러|원·달러|재무부|파월|관세|경기")   # 그냥 '달러'는 금액(1억 달러)에도 붙어 빼고 환율 낱말만

CAUSAL = re.compile(r"(때문에|탓에|덕분에|영향으로|여파로|에 힘입어|로 인해|으로 인해|에 따른|우려로|우려에|되며|하며|면서|전망에)[^.]{0,30}(올랐|내렸|상승|하락|급등|급락|반등|증발|매도세)")
EN_CAUSAL = re.compile(r"\b(because of|due to|thanks to|driven by|on the back of|amid|as|following|after)\b[^.]{0,40}\b(rose|fell|jumped|dropped|rallied|slid|surged|plunged|declined|sank|tumbled)"
                       r"|\b(rose|fell|jumped|dropped|rallied|slid|surged|plunged|declined|sank|tumbled)\b[^.]{0,30}\b(amid|as|due to|after|following)\b", re.I)
ADVICE = re.compile(r"매수하|매도하|사세요|파세요|추천|담아|비중을 늘|비중을 줄|진입하|손절|\bbuy\b|\bsell\b", re.I)
RULES = """반드시 지킬 것:
- 자료에 있는 사실과 숫자만 쓴다. 자료에 없는 숫자·이름을 만들지 않는다. 숫자는 자료에 적힌 모양 그대로 쓴다.
- 소식(무슨 일이 있었나)을 쓴다. 시세 움직임을 쓰더라도 소식과 한 문장에서 원인·결과로 묶지 않는다('~되며 하락했다', '~우려로 급락했다', '~에 따른', 'fell as/amid/due to ~' 모두 금지).
- 매매 권유 금지. 한국어 말투는 '~했다/~이다'."""


# ---------- 테마 화면용 분류(정규식, 한국어 한 줄 기준). 순서대로 처음 맞는 하나 ----------
SECT = {
    "crypto": [("btc", "비트코인", "Bitcoin", r"비트코인|BTC"), ("eth", "이더리움", "Ethereum", r"이더리움|ETH(?![A-Za-z])"),
               ("etf", "기관·ETF", "Institutions & ETFs", r"ETF|기관|재무|트레저리|마이크로스트래티지|스트래티지|블랙록"),
               ("reg", "규제·정책", "Regulation & policy", r"규제|법안|SEC|CFTC|금융위|과세|의회|당국|제재|소송|승인"),
               ("stable", "스테이블코인", "Stablecoins", r"스테이블코인|USDT|USDC|테더|서클"),
               ("exch", "거래소·상장", "Exchanges & listings", r"거래소|상장|바이낸스|코인베이스|업비트|빗썸|OKX|바이빗"),
               ("defi", "디파이·온체인", "DeFi & on-chain", r"디파이|DeFi|온체인|고래|청산|스테이킹|하이퍼리퀴드|Hyperliquid"),
               ("hack", "해킹·보안", "Hacks & security", r"해킹|탈취|도난|익스플로잇|보안|사기"),
               ("alt", "알트코인", "Altcoins", r".")],
    "nasdaq": [("semi", "반도체", "Semiconductors", r"엔비디아|AMD|TSMC|브로드컴|인텔|마이크론|퀄컴|ASML|반도체|칩"),
               ("big", "빅테크", "Big Tech", r"애플|마이크로소프트|아마존|알파벳|구글|메타|넷플릭스"),
               ("ev", "전기차·자동차", "EVs & autos", r"테슬라|전기차|자동차|리비안"),
               ("soft", "소프트웨어·AI", "Software & AI", r"오라클|세일즈포스|어도비|팔란티어|소프트웨어|클라우드|AI"),
               ("fin", "금융·크립토 주식", "Financials & crypto stocks", r"은행|JP모건|골드만|코인베이스|로빈후드|마이크로스트래티지|스트래티지"),
               ("earn", "실적", "Earnings", r"실적|매출|순이익|EPS|가이던스|분기"),
               ("idx", "지수·시장 전반", "Indices & market", r".")],
    "econ": [("fed", "금리·연준", "Rates & the Fed", r"연준|Fed|FOMC|금리|파월|기준금리|국채"),
             ("cpi", "물가", "Inflation", r"CPI|PPI|PCE|물가|인플레이션"),
             ("job", "고용", "Jobs", r"고용|실업|비농업|임금|일자리"),
             ("fx", "환율·달러", "FX & the dollar", r"달러화|달러 지수|달러지수|달러 강세|달러 약세|달러 가치|DXY|환율|엔화|위안화|원화|유로화|원/달러|원·달러"),
             ("cmd", "원자재", "Commodities", r"유가|원유|금값|금 |은 |구리|천연가스|OPEC"),
             ("trade", "관세·무역", "Tariffs & trade", r"관세|무역|수출|수입|공급망"),
             ("fiscal", "재정·성장", "Fiscal & growth", r".")],
    "ai": [("model", "모델·제품", "Models & products", r"모델|출시|챗GPT|ChatGPT|제미나이|클로드|Claude|그록|LLM|에이전트|오픈소스"),
           ("chip", "칩·데이터센터", "Chips & data centers", r"엔비디아|칩|반도체|GPU|데이터센터|TSMC|AMD|전력"),
           ("fund", "투자·자금", "Funding & deals", r"투자|유치|인수|기업가치|평가|자금|파이낸싱|IPO"),
           ("policy", "규제·정책", "Regulation & policy", r"규제|법안|정부|정책|저작권|소송|의회|EU"),
           ("biz", "기업·실적", "Companies & earnings", r".")],
}
SECT_RX = {k: [(a, b, c, re.compile(r)) for a, b, c, r in v] for k, v in SECT.items()}
# 종목 이름 → 기호(나스닥·AI 테마 자산 언급 세기)
TICK = {"엔비디아": "NVDA", "애플": "AAPL", "마이크로소프트": "MSFT", "아마존": "AMZN", "알파벳": "GOOGL", "구글": "GOOGL", "메타": "META", "테슬라": "TSLA",
        "브로드컴": "AVGO", "AMD": "AMD", "TSMC": "TSM", "팔란티어": "PLTR", "오라클": "ORCL", "넷플릭스": "NFLX", "코인베이스": "COIN", "스트래티지": "MSTR",
        "로빈후드": "HOOD", "인텔": "INTC", "마이크론": "MU", "퀄컴": "QCOM", "ASML": "ASML", "세일즈포스": "CRM", "어도비": "ADBE"}
ECON_ASSET = [("^TNX", r"국채|금리"), ("DX-Y.NYB", r"달러화|달러 지수|달러지수|달러 강세|달러 약세|달러 가치|DXY"), ("GC=F", r"금값|금 가격|금 선물|(?<![가-힣])금(?=[이은을,\s])"), ("CL=F", r"유가|원유|WTI|브렌트"), ("KRW=X", r"원화|원/달러|원·달러")]


def sector_of(k, ko):
    for key, *_ , rx in SECT_RX[k]:
        if rx.search(ko):
            return key
    return SECT_RX[k][-1][0]


def mentions(k, xs):
    """자산별 24시간 언급 수와 호재·악재(테마마다 자산 이름 기준이 다르다)."""
    M = {}
    for x in xs:
        ko = x.get("ko") or ""
        if k == "crypto":
            keys = x.get("coins") or []
        elif k == "econ":
            keys = [s for s, rx in ECON_ASSET if re.search(rx, ko)]
        else:
            keys = list(dict.fromkeys(t for n, t in TICK.items() if n in ko))
            if k == "ai":
                keys += [c for c in (x.get("coins") or []) if c in ("TAO", "FET", "RENDER", "WLD", "NEAR", "VIRTUAL")]
        for a in keys:
            m = M.setdefault(a, {"n": 0, "u": 0, "d": 0})
            m["n"] += 1
            m["u"] += x.get("v") == "호재"
            m["d"] += x.get("v") == "악재"
    return dict(sorted(M.items(), key=lambda kv: -kv[1]["n"])[:16])


def hours(xs, now):
    """지난 24시간을 1시간씩: [소식, 호재, 악재]. 0번이 가장 오래된 시간."""
    H = [[0, 0, 0] for _ in range(24)]
    for x in xs:
        i = int((x["t"] - (now - 86400)) // 3600)
        if 0 <= i < 24:
            H[i][0] += 1
            H[i][1] += x.get("v") == "호재"
            H[i][2] += x.get("v") == "악재"
    return H


def sectors(k, xs):
    out = []
    for key, ko, en, _ in SECT_RX[k]:
        ys = [x for x in xs if sector_of(k, x.get("ko") or "") == key]
        if ys:
            out.append({"k": key, "ko": ko, "en": en, "n": len(ys), "u": sum(x["v"] == "호재" for x in ys), "d": sum(x["v"] == "악재" for x in ys)})
    return sorted(out, key=lambda o: -o["n"])


def toks(s):
    return {w for w in re.findall(r"[A-Za-z]{2,}|\d[\d,.]*|[가-힣]{2,}", s or "")}


def refs(sentences, xs):
    """요약 1~4번 문장마다 근거가 된 소식 id(낱말·숫자가 가장 많이 겹치는 것, 겹침이 적으면 없음)."""
    out = []
    for s in sentences[:4]:
        a = toks(s)
        best = max(xs, key=lambda x: len(a & toks(x.get("ko"))), default=None)
        out.append(best["id"] if best and len(a & toks(best.get("ko"))) >= 3 else None)
    return out


def compact(x):
    return {k: x.get(k) for k in ("id", "t", "ko", "en", "v", "s", "n", "coins", "kind") if x.get(k) not in (None, "", [])} | {"sec": None}


def load_items(now):
    """지난 24시간 판정된 소식(같은 소식끼리 묶음). 판정 DB → 안 되면 flash.json."""
    try:
        sys.path.insert(0, HOME)
        import tg_publish as P
        con = P.db()
        xs = [it for it in P.stories(con, since=now - 86400 - 3600) if it["t"] >= now - 86400 and P.visible(it)]
        log("판정 DB에서 24시간 소식", len(xs))
        return xs, "db"
    except Exception as e:
        log("판정 DB 못 씀 → flash.json", type(e).__name__, str(e)[:120])
        flash = json.load(open(os.path.join(BRANCH, "flash.json")))
        return [x for x in flash.get("items", []) if x.get("t", 0) >= now - 86400 and x.get("ko")], "flash"



# ---------- '오늘 무엇이 달라졌나': 평소(최근 며칠)와 비교한 변화. 숫자도 문장도 프로그램이 만든다(AI 아님) ----------
TN = {"crypto": ("크립토", "crypto"), "nasdaq": ("나스닥", "Nasdaq"), "econ": ("경제", "economy"), "ai": ("AI", "AI")}


def history(now, days=7):
    """판정 DB의 줄(묶기 전) — 기준(최근 며칠, 지난 24시간 제외)과 오늘(지난 24시간). 기준 기간 내내 있던 채널만 써서 새로 넣은 채널이 '급증'처럼 보이지 않게."""
    sys.path.insert(0, HOME)
    import tg_publish as P
    con = P.db()
    J = "FROM msgs m JOIN ai a ON a.ch=m.ch AND a.id=m.id WHERE a.ko != ''"   # 판정된 줄만(msgs 에는 판정 안 한 예전 글도 있다)
    first = con.execute("SELECT MIN(m.t) " + J).fetchone()[0] or now
    start = max(now - (days + 1) * 86400, first + 6 * 3600)
    nd = int((now - 86400 - start) // 86400)
    if nd < 2:
        return None
    start = now - 86400 - nd * 86400
    rows = con.execute("""SELECT m.t, m.ch, a.ko, a.verdict, a.coins, a.sectors, a.kind FROM msgs m JOIN ai a ON a.ch=m.ch AND a.id=m.id
        WHERE m.t >= ? AND a.ko != '' AND a.kind IN (%s)""" % ",".join("?" * len(P.SHOW_KINDS)), (start, *P.SHOW_KINDS)).fetchall()
    old = {ch for ch, t in con.execute("SELECT m.ch, MIN(m.t) " + J + " GROUP BY m.ch") if t <= start + 6 * 3600}
    X = [{"t": r[0], "ko": r[2], "v": r[3], "coins": json.loads(r[4] or "[]"), "sectors": json.loads(r[5] or "[]"), "kind": r[6]} for r in rows if r[1] in old]
    return {"days": nd, "base": [x for x in X if x["t"] < now - 86400], "today": [x for x in X if x["t"] >= now - 86400]}


def changes(k, H, xs, now):
    """테마 k 의 변화 신호 목록(점수 높은 순, 최대 4개). xs = 오늘의 묶인 소식(근거 연결용)."""
    if not H:
        return []
    nm_ko, nm_en = TN[k]
    Tb, _ = buckets(H["base"], [])
    Tt, _ = buckets(H["today"], [])
    base, today, nd = Tb[k], Tt[k], H["days"]
    avg = lambda n: n / nd
    out = []
    ids = lambda ys: [y["id"] for y in sorted(ys, key=lambda y: -((y.get("s") or 1) * 3 + (y.get("n") or 1)))][:6]
    # 1) 테마 전체 소식량
    b = avg(len(base))
    if b >= 3:
        r = len(today) / b
        if r >= 1.4 or r <= 0.6:
            out.append({"k": "vol", "score": abs(r - 1) * 2, "tone": "flat",
                        "ko": f"오늘 {nm_ko} 소식이 평소(최근 {nd}일 평균)보다 {r:.1f}배 {'많아요' if r > 1 else '적어요'}.",
                        "en": f"{nm_en.capitalize()} news volume is {r:.1f}× {'above' if r > 1 else 'below'} normal (the {nd}-day average).", "ids": []})
    # 2) 섹터 급증 — 비율은 채널 글 수(기준과 같은 잣대), 문장 속 건수·판정은 묶인 소식 수(화면 숫자와 같게)
    for key, sko, sen, _ in SECT_RX[k]:
        if key == SECT_RX[k][-1][0]:
            continue
        tr = sum(sector_of(k, x["ko"]) == key for x in today)
        bn = avg(sum(sector_of(k, x["ko"]) == key for x in base))
        rel = [y for y in xs if sector_of(k, y.get("ko") or "") == key]
        if len(rel) < 3:
            continue
        r = tr / bn if bn > 0 else None
        if r is not None and r < 1.8:
            continue
        u, d = sum(y["v"] == "호재" for y in rel), sum(y["v"] == "악재" for y in rel)
        tone = "up" if u > d * 1.5 else "down" if d > u * 1.5 else "flat"
        out.append({"k": "sec", "score": (min(r, 6) if r else 2.5) + len(rel) / 5, "tone": tone,
                    "ko": (f"'{sko}' 소식이 평소의 {r:.1f}배로 늘었어요." if r else f"평소엔 거의 없던 '{sko}' 소식이 나왔어요.") + f" 오늘 {len(rel)}건 · 호재 {u} · 악재 {d}.",
                    "en": (f"'{sen}' news is running {r:.1f}× normal." if r else f"'{sen}' news, usually rare, is showing up.") + f" {len(rel)} today · {u} bullish · {d} bearish.", "ids": ids(rel)})
    # 3) 자산 언급 급증(같은 잣대)
    mt, mb = mentions(k, today), mentions(k, base)
    for a, m in mt.items():
        if a in ("USDT", "USDC"):
            continue
        rel = [y for y in xs if a in (y.get("coins") or []) or any(n in (y.get("ko") or "") for n, t in TICK.items() if t == a)
               or (k == "econ" and any(s == a and re.search(rx, y.get("ko") or "") for s, rx in ECON_ASSET))]
        bn = avg(mb.get(a, {"n": 0})["n"])
        r = m["n"] / bn if bn > 0 else None
        if len(rel) < (3 if r else 4) or (r is not None and r < 2):   # 평소 0이던 자산은 4건 이상일 때만
            continue
        nm = a.replace("^TNX", "미국 10년물 금리").replace("DX-Y.NYB", "달러 지수").replace("GC=F", "금").replace("CL=F", "유가").replace("KRW=X", "원/달러")
        nm_e = a.replace("^TNX", "the US 10-year yield").replace("DX-Y.NYB", "the dollar index").replace("GC=F", "gold").replace("CL=F", "oil").replace("KRW=X", "USD/KRW")
        u, d = sum(y["v"] == "호재" for y in rel), sum(y["v"] == "악재" for y in rel)
        tone = "up" if u > d * 1.5 else "down" if d > u * 1.5 else "flat"
        out.append({"k": "asset", "sym": a, "ratio": round(r, 2) if r else None, "n": len(rel), "score": (min(r, 6) if r else 2.5) + len(rel) / 5, "tone": tone,
                    "ko": (f"{nm} 언급이 평소의 {r:.1f}배예요." if r else f"평소엔 거의 없던 {nm} 언급이 늘었어요.") + f" 오늘 {len(rel)}건 · 호재 {u} · 악재 {d}.",
                    "en": (f"Mentions of {nm_e} are {r:.1f}× normal." if r else f"{nm_e[0].upper() + nm_e[1:]}, rarely mentioned, is coming up.") + f" {len(rel)} today · {u} bullish · {d} bearish.", "ids": ids(rel)})
    # 3b) 호재 비중이 평소와 다름(채널 글 기준 비중끼리 비교 — 비중이라 중복의 영향이 적다)
    ut, dt = sum(x["v"] == "호재" for x in today), sum(x["v"] == "악재" for x in today)
    ub, db = sum(x["v"] == "호재" for x in base), sum(x["v"] == "악재" for x in base)
    if ut + dt >= 10 and ub + db >= 20:
        ft, fb = ut / (ut + dt), ub / (ub + db)
        if abs(ft - fb) >= 0.15:
            hi = ft > fb
            out.append({"k": "mood", "score": 3 + abs(ft - fb) * 10, "tone": "up" if hi else "down",
                        "ko": f"호재 비중이 평소보다 {'높아요' if hi else '낮아요'}. 오늘 {ft * 100:.0f}% · 평소 {fb * 100:.0f}%(호재÷호재+악재).",
                        "en": f"The bullish share is {'higher' if hi else 'lower'} than usual: {ft * 100:.0f}% today vs {fb * 100:.0f}% normally (bullish ÷ bullish+bearish).",
                        "ids": ids([y for y in xs if y.get("v") == ("호재" if hi else "악재")])})
    # 4) 최근 3시간 분위기 뒤집힘(묶인 소식 기준)
    rec = [y for y in xs if y["t"] >= now - 3 * 3600 and y.get("v") != "중립"]
    pre = [y for y in xs if y["t"] < now - 3 * 3600 and y.get("v") != "중립"]
    if len(rec) >= 4 and len(pre) >= 8:
        fr, fp = sum(y["v"] == "호재" for y in rec) / len(rec), sum(y["v"] == "호재" for y in pre) / len(pre)
        if (fp >= 0.6 and fr <= 0.4) or (fp <= 0.4 and fr >= 0.6):
            up = fr > fp
            out.append({"k": "flip", "score": 6, "tone": "up" if up else "down",
                        "ko": f"최근 3시간은 {'호재' if up else '악재'} 쪽이에요(호재 {round(fr * len(rec))} · 악재 {len(rec) - round(fr * len(rec))}). 그 전 21시간은 {'악재' if up else '호재'}가 많았어요.",
                        "en": f"The last 3 hours lean {'bullish' if up else 'bearish'} ({round(fr * len(rec))} vs {len(rec) - round(fr * len(rec))}), after a {'bearish' if up else 'bullish'} 21 hours before.", "ids": ids(rec)})
    # 5) 여러 곳이 같이 보도한 소식
    wide = [y for y in xs if (y.get("n") or 1) >= 4]
    if wide:
        out.append({"k": "wide", "score": 1.5 + len(wide) / 3, "tone": "flat",
                    "ko": f"같은 소식을 4곳 이상이 보도한 건 {len(wide)}건이에요.", "en": f"{len(wide)} {'story was' if len(wide) == 1 else 'stories were'} reported by 4+ outlets.", "ids": ids(wide)})
    # 6) 큰 소식(세기 3)
    big = [y for y in xs if (y.get("s") or 0) >= 3]
    if big:
        u, d = sum(y["v"] == "호재" for y in big), sum(y["v"] == "악재" for y in big)
        out.append({"k": "big", "score": 1 + len(big) / 2, "tone": "up" if u > d else "down" if d > u else "flat",
                    "ko": f"세기 3(큰 소식)이 {len(big)}건이에요. 호재 {u} · 악재 {d}.", "en": f"{len(big)} high-impact {'story' if len(big) == 1 else 'stories'} (strength 3): {u} bullish, {d} bearish.", "ids": ids(big)})
    if not any(o["k"] == "vol" for o in out) and b >= 3:
        out.append({"k": "vol", "score": 0.5, "tone": "flat", "ko": f"오늘 {nm_ko} 소식량은 평소(최근 {nd}일)와 비슷해요.",
                    "en": f"{nm_en.capitalize()} news volume is about normal (vs the last {nd} days).", "ids": []})
    out.sort(key=lambda o: -o["score"])
    for o in out:
        o["score"] = round(o["score"], 2)
    return out


def log(*a):
    print(time.strftime("%m-%d %H:%M:%S"), *a, flush=True)


def get(url, timeout=60):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 delfona-themes"}), timeout=timeout))


def nums(s):
    return {n.replace(",", "").lstrip("+-") for n in re.findall(r"[+-]?\d[\d,]*(?:\.\d+)?", s)}


def ok_ko(v, src):
    return bool(v) and not (nums(v) - nums(src)) and not CAUSAL.search(v) and not ADVICE.search(v)


def ok_en(v):
    return bool(v) and not EN_CAUSAL.search(v) and not ADVICE.search(v)


def chat(system, user, n=2400):
    body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "10m", "options": {"temperature": 0.3, "num_ctx": 8192, "num_predict": n},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        t = json.loads(r.read())["message"]["content"]
    return json.loads(t[t.index("{"): t.rindex("}") + 1])


def buckets(items, arts):
    T = {k: [] for k in NAME}
    A = {k: [] for k in NAME}
    for x in items:
        ko = x.get("ko") or ""
        if x.get("coins") or CRYPTO_W.search(ko):
            T["crypto"].append(x)
        if STOCK_W.search(ko):
            T["nasdaq"].append(x)
        if ECON_W.search(ko) or (x.get("kind") == "data" and not x.get("coins")):
            T["econ"].append(x)
        if "ai" in (x.get("sectors") or []) or AI_W.search(ko):
            T["ai"].append(x)
    for a in arts:
        t, to = a.get("title") or "", a.get("title_orig") or ""
        if STOCK_W.search(t) or STOCK_EN.search(to):
            A["nasdaq"].append(a)
        if a.get("category") == "ai":
            A["ai"].append(a)
        elif a.get("category") == "crypto":
            A["crypto"].append(a)
        elif a.get("category") == "macro":
            A["econ"].append(a)
    return T, A


def pick(arr, n):
    return sorted(arr, key=lambda x: -((x.get("s") or 1) * 3 + (x.get("n") or 1) * 2 + (x.get("v") != "중립")))[:n]


def theme_source(k, xs, arts):
    u = sum(x["v"] == "호재" for x in xs)
    d = sum(x["v"] == "악재" for x in xs)
    L = [f"[{NAME[k]} · 지난 24시간 판정한 속보 {len(xs)}건 · 호재 {u} · 악재 {d}]"]
    L += [f"  ({x['v']}) {x['ko']}" + (f" [{x['n']}곳 보도]" if (x.get("n") or 1) > 1 else "") for x in pick(xs, 24)]
    seen, extra = set(), []
    for a in sorted(arts, key=lambda a: -(a.get("importance") or 0)):
        t = (a.get("title") or "").strip()
        if t and t[:18] not in seen:
            seen.add(t[:18])
            extra.append(f"  (기사 · {a.get('source_name', '')}) {t}")
        if len(extra) >= 10:
            break
    if extra:
        L.append("[참고: 같은 시간 주요 매체 기사 제목]")
        L += extra
    return "\n".join(L), u, d


def write_theme(k, src):
    system = f"""너는 전 세계 시장 소식을 요약하는 편집자다. 아래는 '{NAME[k]}' 테마의 지난 24시간 자료다(판정한 실시간 속보 + 주요 매체 기사 제목). 이 테마를 독자가 한 번에 이해하도록 요약한다.
문장 6개를 쓴다: ① 가장 큰 소식 ② ③ ④ 그다음 중요한 서로 다른 소식들(각각 구체적으로, 회사·기관 이름과 숫자 포함) ⑤ 판정한 속보 중 호재·악재 어느 쪽이 많았는지(자료의 건수 사용) ⑥ 이 테마에서 눈여겨볼 점.
한국어 문장은 각각 35~70자. 영어는 같은 뜻으로 한 문장씩 짝을 맞춘다.
{RULES}
형식: {{"ko": ["", "", "", "", "", ""], "en": ["", "", "", "", "", ""]}}"""
    keep, dropped, note = [], [], ""
    for attempt in range(4):
        try:
            o = chat(system, src + note)
        except Exception as e:
            log(k, "AI 실패", type(e).__name__, str(e)[:120])
            continue
        pairs = list(zip(o.get("ko") or [], o.get("en") or []))
        good = [(a, b) for a, b in pairs if ok_ko(a, src) and ok_en(b)]
        bad = [a for a, b in pairs if (a, b) not in good]
        if len(good) > len(keep):
            keep, dropped = good, bad
        if len(good) >= 5:
            break
        note = "\n\n앞선 답에서 다음 문장은 규칙 위반이라 뺐다: " + " / ".join(bad[:4]) + "\n규칙을 지켜 다시 6문장을 써라."
    return keep, dropped


def run():
    t0 = time.time()
    now = time.time()
    items, origin = load_items(now)
    try:
        arts = get(ARTICLES + "?t=%d" % now, 90)
        arts = arts if isinstance(arts, list) else arts.get("articles") or arts.get("items") or []
        arts = [a for a in arts if a.get("t0", 0) >= now - 86400]
    except Exception as e:
        log("기사 못 받음(속보만으로 진행)", type(e).__name__)
        arts = []
    if len(items) < 30:
        log("자료 부족, 건너뜀", len(items))
        return
    T, A = buckets(items, arts)
    try:
        HIST = history(now)
    except Exception as e:
        log("기준 기간 못 만듦(변화 신호 없이)", type(e).__name__, str(e)[:120])
        HIST = None
    themes, dropped = [], {}
    for k in NAME:
        src, u, d = theme_source(k, T[k], A[k])
        keep, bad = write_theme(k, src) if T[k] else ([], [])
        dropped[k] = bad
        xs = sorted(T[k], key=lambda x: -x["t"])
        top = [compact(x) | {"sec": sector_of(k, x.get("ko") or "")} for x in pick(xs, 40)]
        themes.append({"k": k, "n": len(T[k]), "u": u, "d": d, "arts": len(A[k]), "ko": " ".join(a for a, _ in keep), "en": " ".join(b for _, b in keep),
                       "s_ko": [a for a, _ in keep], "s_en": [b for _, b in keep], "refs": refs([a for a, _ in keep], xs),
                       "hours": hours(xs, now), "sectors": sectors(k, xs), "mentions": mentions(k, xs), "top": top,
                       "latest": [compact(x) | {"sec": sector_of(k, x.get("ko") or "")} for x in xs[:40]], "changes_all": changes(k, HIST, xs, now)})
        themes[-1]["changes"] = themes[-1]["changes_all"][:4]   # 테마 화면은 상위 4개, 내 자산 화면은 자산 신호 전부(changes_all)
        th = themes[-1]; have = {x["id"] for x in th["top"] + th["latest"]}; byid = {x["id"]: x for x in xs}
        th["more"] = [compact(byid[i]) | {"sec": sector_of(k, byid[i].get("ko") or "")} for i in dict.fromkeys(i for c in th["changes_all"] for i in c["ids"]) if i not in have and i in byid]   # 신호가 가리키는 소식도 화면에서 열 수 있게
    hsrc = "\n".join(f"[{NAME[t['k']]}] {t['ko']}" for t in themes)
    hl = {"ko": "", "en": ""}
    for attempt in range(4):
        try:
            o = chat("너는 편집자다. 아래 테마별 요약을 보고 오늘 전 세계 흐름을 한 줄로 쓴다. ko: 40자 이내, en: 같은 뜻 80자 이내.\n" + RULES + '\n형식: {"ko": "", "en": ""}', hsrc, 300)
        except Exception as e:
            log("한 줄 실패", type(e).__name__)
            continue
        if ok_ko(o.get("ko", ""), hsrc) and ok_en(o.get("en", "")) and len(o.get("ko", "")) <= 60:
            hl = o
            break
    if not all(t["ko"] for t in themes if t["n"]) or not hl.get("ko"):
        log("요약이 비어 저장하지 않음", [t["k"] for t in themes if t["n"] and not t["ko"]], bool(hl.get("ko")))
        return
    doc = {"v": 2, "made": int(now), "next": int(now + EVERY), "from": int(now - 86400), "src": origin, "model": MODEL, "total": len(items), "articles": len(arts),
           "sect": {k: [[a, b, c] for a, b, c, _ in v] for k, v in SECT.items()}, "base_days": HIST["days"] if HIST else 0,
           "headline": {"ko": hl["ko"], "en": hl["en"]}, "themes": themes, "dropped": dropped}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + ".tmp", "w") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(OUT + ".tmp", OUT)          # tg_publish가 다음 차례(1분 안)에 flash 브랜치로 올린다
    log("테마 요약 저장", OUT, "%.0fs" % (time.time() - t0), {t["k"]: (t["n"], len(t["ko"])) for t in themes}, "뺀 문장:", sum(len(v) for v in dropped.values()))


def install():
    dst = os.path.join(HOME, "theme_brief.py")
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
  <key>StandardOutPath</key><string>{HOME}/themes.log</string>
  <key>StandardErrorPath</key><string>{HOME}/themes.log</string>
</dict></plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    for _ in range(10):
        if subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", plist], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    log("설치 완료:", plist, "(3시간마다)")


if __name__ == "__main__":
    if "--install" in sys.argv[1:]:
        install()
    else:
        run()
