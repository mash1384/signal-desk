"""운영자 Mac에서 매일 오전 9시(한국 시간): 지난 하루(전날 09:00 ~ 오늘 09:00, 세계 표준시 하루)의 속보·기사·시세를 모아 '하루 정리'를 만든다.

숫자·순위·개수는 이 프로그램이 계산하고, 로컬 Gemma는 그 자료로 '오늘의 한 줄', 'AI 리뷰', 분야별 한 문장만 쓴다.
AI 문장에 입력에 없는 숫자가 나오거나 '뉴스 때문에 올랐다' 같은 인과 표현·매매 권유가 나오면 버리고 다시 쓰게 한다.
결과는 ~/.signal/flash-branch/daily/<날짜>.json 에 두고, tg_publish.py가 flash 브랜치에 함께 올린다. 사이트 파이프라인이 /daily/ 페이지로 만든다.

설치: ~/.signal/tgvenv/bin/python tools/daily_brief.py --install   (launchd com.signal.daily, 매일 09:07, 로그 ~/.signal/daily.log)
수동: ~/.signal/tgvenv/bin/python tools/daily_brief.py [--date 2026-10-13] [--force] [--dry]
"""

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tg_publish as P  # noqa: E402

HOME = os.path.expanduser("~/.signal")
OUT = os.path.join(P.BRANCH_DIR, "daily")
SITE = "https://mash1384.github.io/signal-desk/"
BINANCE = "https://data-api.binance.vision/api/v3/klines"
MODEL = os.environ.get("SIGNAL_TG_MODEL", "gemma4:26b")
LABEL = "com.signal.daily"
KST = dt.timezone(dt.timedelta(hours=9))
COINS = "BTC ETH SOL XRP BNB DOGE ADA LINK AVAX SUI TON DOT LTC TRX HBAR TAO AAVE UNI NEAR APT ONDO ENA PEPE ZEC FET".split()
CATS = [("crypto", "크립토"), ("econ", "경제"), ("world", "세계정세"), ("ai", "AI 업계")]

CRYPTO_W = re.compile(r"비트코인|이더리움|코인|암호화폐|가상자산|가상화폐|스테이블|토큰|블록체인|디파이|채굴|ETF|BTC|ETH|솔라나|리플|NFT|웹3|온체인|고래|에어드랍|바이낸스|코인베이스|업비트|빗썸|하이퍼리퀴드")
AI_W = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])|인공지능|엔비디아|오픈AI|OpenAI|앤트로픽|Anthropic|GPU|반도체|딥마인드|제미나이|챗GPT|LLM|데이터센터|xAI|그록|TSMC")
ECON_W = re.compile(r"연준|금리|물가|CPI|PPI|고용|실업|GDP|국채|수익률|달러|환율|유가|원유|증시|주가|나스닥|S&P|다우|실적|EPS|매출|중앙은행|인플레|경기|소매판매|PMI|ECB|BOJ|일본은행|한국은행|BOE|관세|무역|채권")
CAUSAL = re.compile(r"(때문에|탓에|덕분에|영향으로|여파로|에 힘입어)[^.]{0,20}(올랐|내렸|상승|하락|급등|급락|반등)")
ADVICE = re.compile(r"매수하|매도하|사세요|파세요|추천|담아|비중을 늘|비중을 줄|진입하|손절")


def log(*a):
    print(time.strftime("%m-%d %H:%M:%S"), *a, flush=True)


def get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "signal-daily/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# ---------- 자료 모으기 ----------
def window(day):
    start = dt.datetime(day.year, day.month, day.day, 9, tzinfo=KST)
    return int(start.timestamp()), int((start + dt.timedelta(days=1)).timestamp())


def category(it):
    t = it["ko"]
    if it.get("coins") or (set(it.get("sectors") or []) - {"ai"}) or CRYPTO_W.search(t):
        return "crypto"
    if "ai" in (it.get("sectors") or []) or AI_W.search(t):
        return "ai"
    if it.get("kind") == "data" or ECON_W.search(t):
        return "econ"
    return "world"


def score(it):
    """핵심 소식 순위: 세기, 보도한 곳 수, 시장 전체, 판정 유무, 분야(크립토 투자자용이라 크립토 우선). 시세 해설은 낮춘다."""
    return (3 * it["s"] + 2 * min(it["n"], 4) + (2 if it["mw"] else 0) + (1 if it["v"] != "중립" else 0)
            - (3 if it["kind"] == "price_recap" else 0) + {"crypto": 3, "econ": 1, "ai": 1}.get(it.get("cat"), 0))


def slim(it):
    return {k: it[k] for k in ("t", "ko", "v", "s", "n", "coins", "sectors", "mw", "link") if k in it}


def market(day):
    """세계 표준시 하루 봉(=한국 09:00~09:00)의 등락."""
    t0 = int(dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc).timestamp()) * 1000
    out = {}
    for c in COINS:
        try:
            k = get_json(f"{BINANCE}?symbol={c}USDT&interval=1d&startTime={t0}&limit=1")
            if k and int(k[0][0]) == t0:
                o, cl = float(k[0][1]), float(k[0][4])
                out[c] = {"chg": round((cl / o - 1) * 100, 2), "close": cl}
        except Exception as e:
            log("시세 실패", c, type(e).__name__)
        time.sleep(0.1)
    alts = sorted(((c, v["chg"]) for c, v in out.items() if c not in ("BTC", "ETH")), key=lambda x: -x[1])
    return {"btc": out.get("BTC"), "eth": out.get("ETH"), "up": [list(x) for x in alts[:3] if x[1] > 0],
            "down": [list(x) for x in alts[::-1][:3] if x[1] < 0], "n": len(out)}


def schedule(end):
    """오늘(정리 발표 시각부터 24시간) 볼 경제 일정. 중요도 중 이상."""
    try:
        cal = get_json(SITE + "data/calendar.json?t=%d" % time.time()).get("events", [])
        ev = {u["ts"]: u for u in get_json(SITE + "data/events.json?t=%d" % time.time()).get("upcoming", [])}
    except Exception as e:
        log("일정 실패", type(e).__name__)
        return []
    rows = {}
    for e in sorted(cal, key=lambda e: (e["ts"], -e.get("level", 0))):
        if not (end <= e["ts"] < end + 86400 and e.get("level", 0) >= 2):
            continue
        k = (e["ts"], e.get("country"))
        if k in rows:                 # 같은 시각 같은 나라 발표(CPI 전월비·전년비 등)는 한 줄로
            rows[k]["more"] += 1
            continue
        u = ev.get(e["ts"]) or {}
        rows[k] = {"ts": e["ts"], "title": u.get("name") or e.get("title_ko") or e["title"], "country": e.get("country"), "level": e["level"],
                   "forecast": e.get("forecast") or "", "previous": e.get("previous") or "", "vs": u.get("vs_normal"), "more": 0}
    return list(rows.values())[:6]


def ai_articles(start, end):
    """사이트가 모은 기사 중 AI 업계 기사를 같은 소식끼리 묶어, 많이 다룬 순서로."""
    try:
        arts = get_json(SITE + "data/articles.json?t=%d" % time.time(), timeout=60)
    except Exception as e:
        log("기사 실패", type(e).__name__)
        return [], 0
    day = [a for a in arts if start <= a.get("t0", 0) < end]
    ai = [a for a in day if a.get("category") == "ai" and a.get("importance", 1) >= 2]
    if not ai:
        return [], len(day)
    vecs = P.embed([a["title"] for a in ai])
    groups = []
    for i, a in enumerate(ai):
        for g in groups:
            if max(sum(x * y for x, y in zip(vecs[i], vecs[j])) for j in g) >= P.SAME:
                g.append(i)
                break
        else:
            groups.append([i])
    groups.sort(key=lambda g: (-len({ai[j]["source_name"] for j in g}), -max(ai[j]["importance"] for j in g)))
    out = []
    for g in groups[:4]:
        a = ai[g[0]]
        out.append({"t": a["t0"], "title": a["title"], "n": len({ai[j]["source_name"] for j in g}), "link": a.get("url", ""), "src": a["source_name"]})
    return out, len(day)


# ---------- AI 문장 ----------
SYS = """너는 한국 크립토 투자자를 위한 '하루 정리' 편집자다. 아래 자료만 보고 JSON 한 개만 낸다. 설명 금지.

headline: 하루를 요약하는 한국어 한 줄(45자 이내). 가장 중요한 흐름 1~2개.
review: 'AI 리뷰' 3~4문장. 어떤 소식이 많았고, 호재·악재 중 어느 쪽이 우세했으며, 어떤 분야(섹터)가 두드러졌는지, 오늘 무엇을 지켜볼지.
crypto, econ, world, ai: 분야별 한 문장(60자 이내). 자료에 그 분야 소식이 없으면 "".

반드시 지킬 것:
- 자료에 있는 사실과 숫자만 쓴다. 자료에 없는 숫자·가격·이름을 만들지 않는다.
- 뉴스가 가격을 움직였다고 쓰지 않는다('~때문에 올랐다/내렸다' 금지). 소식과 시세는 '같은 날 있었던 일'로만 나란히 쓴다.
- 사라·팔아라 같은 매매 권유를 하지 않는다.
- 소식 개수를 말할 때 '강세·약세·상승·하락' 같은 시세 표현을 쓰지 않는다('AI 섹터는 호재가 많았다'처럼 쓴다).
- 말투는 '~했다/~이다'.

형식: {"headline": "", "review": "", "crypto": "", "econ": "", "world": "", "ai": ""}"""


def brief_input(doc):
    L = []
    b = doc["balance"]
    L.append(f"[하루 집계] 묶은 소식 {doc['counts']['stories']}건 · 호재 {b['호재']}건 · 악재 {b['악재']}건")
    for k, name in CATS:
        c = doc["by_cat"].get(k, {})
        L.append(f"  {name}: 호재 {c.get('호재', 0)} · 악재 {c.get('악재', 0)}")
    if doc["sectors"]:
        L.append("[섹터] " + ", ".join(f"{doc['sector_names'][s]} 호재 {u}·악재 {d}" for s, u, d in doc["sectors"]))
    L.append("[핵심 소식]")
    for it in doc["key"]:
        L.append(f"  ({it['v']}) {it['ko']}" + (f" [{it['n']}곳 보도]" if it["n"] > 1 else ""))
    for k, name in CATS:
        xs = doc["sections"][k].get("news", []) + doc["sections"][k]["items"]
        if xs:
            L.append(f"[{name}]")
            for it in xs:
                L.append(f"  ({it.get('v', '-')}) {it.get('ko') or it.get('title')}")
    m = doc["market"]
    if m.get("btc"):
        L.append(f"[시세, 같은 날] BTC {m['btc']['chg']:+.2f}% · ETH {m['eth']['chg']:+.2f}%" if m.get("eth") else f"[시세] BTC {m['btc']['chg']:+.2f}%")
        if m["up"]:
            L.append("  많이 오른 코인: " + ", ".join(f"{c} {v:+.2f}%" for c, v in m["up"]))
        if m["down"]:
            L.append("  많이 내린 코인: " + ", ".join(f"{c} {v:+.2f}%" for c, v in m["down"]))
    if doc["schedule"]:
        L.append("[오늘 볼 일정]")
        for e in doc["schedule"]:
            L.append(f"  {dt.datetime.fromtimestamp(e['ts'], KST):%H:%M} {e['title']}")
    return "\n".join(L)


def numbers(s):
    return {n.replace(",", "").lstrip("+-") for n in re.findall(r"[+-]?\d[\d,]*(?:\.\d+)?", s)}


def check(out, src):
    """문제 있는 필드 이름 목록. 입력에 없는 숫자, 인과 표현, 매매 권유."""
    allowed = numbers(src)
    bad = []
    for k in ("headline", "review", "crypto", "econ", "world", "ai"):
        v = str(out.get(k) or "")
        if not v and k in ("headline", "review"):
            bad.append(k)
        elif (numbers(v) - allowed) or CAUSAL.search(v) or ADVICE.search(v):
            bad.append(k)
    if len(str(out.get("headline") or "")) > 60:
        bad.append("headline")
    return sorted(set(bad))


def ask(src, note=""):
    body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "10m",
            "options": {"temperature": 0.2, "num_ctx": 8192, "num_predict": 800},
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": src + (("\n\n" + note) if note else "")}]}
    req = urllib.request.Request(P.OLLAMA + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        txt = json.loads(r.read())["message"]["content"]
    return json.loads(txt[txt.index("{"): txt.rindex("}") + 1])


def write_ai(doc):
    src = brief_input(doc)
    best, note = None, ""
    for attempt in range(3):
        try:
            out = ask(src, note)
        except Exception as e:
            log("AI 문장 실패", type(e).__name__, str(e)[:120])
            continue
        bad = check(out, src)
        if best is None or len(bad) < len(best[1]):
            best = (out, bad)
        if not bad:
            break
        note = ("앞선 답의 " + ", ".join(bad) + " 에 자료에 없는 숫자나 '때문에 올랐다' 같은 표현, 매매 권유가 있었다(또는 비어 있었다). "
                "자료에 있는 사실과 숫자만으로 다시 써라.")
    out, bad = best or ({}, ["headline", "review"])
    for k in bad:                     # 끝까지 문제 있는 문장은 싣지 않는다
        out[k] = ""
    doc["headline"] = " ".join(str(out.get("headline") or "").split()) or (doc["key"][0]["ko"] if doc["key"] else "")
    doc["review"] = " ".join(str(out.get("review") or "").split())
    for k, _ in CATS:
        doc["sections"][k]["say"] = " ".join(str(out.get(k) or "").split())
    doc["ai_dropped"] = bad


# ---------- 하루 정리 ----------
def make(day):
    start, end = window(day)
    con = P.db()
    items = P.stories(con, start, end)
    items = [it for it in items if start <= it["t"] < end]
    shown = [it for it in items if P.visible(it)]
    for it in shown:
        it["cat"] = category(it)
    balance = {"호재": sum(it["v"] == "호재" for it in shown), "악재": sum(it["v"] == "악재" for it in shown),
               "중립": sum(it["v"] == "중립" for it in shown)}
    by_cat = {k: {"호재": sum(it["v"] == "호재" and it["cat"] == k for it in shown),
                  "악재": sum(it["v"] == "악재" and it["cat"] == k for it in shown),
                  "n": sum(it["cat"] == k for it in shown)} for k, _ in CATS}
    sec = {}
    for it in shown:
        for s in it["sectors"]:
            u, d = sec.get(s, (0, 0))
            sec[s] = (u + (it["v"] == "호재"), d + (it["v"] == "악재"))
    sectors = sorted(([s, u, d] for s, (u, d) in sec.items()), key=lambda x: -(x[1] + x[2]))[:6]
    ranked = sorted(shown, key=lambda it: (-score(it), it["t"]))
    key = ranked[:5]
    used = {id(it) for it in key}
    sections = {}
    for k, _ in CATS:
        xs = [it for it in ranked if it["cat"] == k and id(it) not in used][:3]
        sections[k] = {"say": "", "items": [slim(it) for it in xs]}
    ai_news, n_articles = ai_articles(start, end)
    if ai_news:
        tr = translate([a["title"] for a in ai_news])
        for a, ko in zip(ai_news, tr):
            a["ko"] = ko or a["title"]
        sections["ai"]["news"] = [{"ko": a["ko"], "n": a["n"], "link": a["link"], "src": a["src"], "t": a["t"]} for a in ai_news[:3]]
        sections["ai"]["items"] = sections["ai"]["items"][:2]      # AI 업계는 업계 기사가 먼저, 속보는 둘까지
    doc = {"v": 1, "date": day.isoformat(), "start": start, "end": end, "made": int(time.time()), "model": MODEL,
           "counts": {"stories": len(shown), "flashes": sum(it["n"] for it in items), "articles": n_articles},
           "balance": balance, "by_cat": by_cat, "sectors": sectors, "sector_names": __import__("tg_judge").SECTORS,
           "key": [slim(it) for it in key], "sections": sections, "market": market(day), "schedule": schedule(end)}
    write_ai(doc)
    return doc


def translate(titles):
    """AI 업계 기사 제목을 한국어 한 줄로(이미 한국어면 다듬기만)."""
    if not titles:
        return []
    body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "10m", "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 600},
            "messages": [{"role": "system", "content": "기사 제목들을 자연스러운 한국어 한 줄로 옮긴다(이미 한국어면 다듬기만). 회사·제품 이름은 그대로. "
                          "JSON 배열 하나만 낸다. 예: [\"…\", \"…\"]"},
                         {"role": "user", "content": json.dumps(titles, ensure_ascii=False)}]}
    try:
        req = urllib.request.Request(P.OLLAMA + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            txt = json.loads(r.read())["message"]["content"]
        arr = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
        return [str(x).strip() for x in arr][: len(titles)] + [""] * max(0, len(titles) - len(arr))
    except Exception as e:
        log("번역 실패", type(e).__name__)
        return [""] * len(titles)


def save(doc):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, doc["date"] + ".json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)            # tg_publish가 다음 차례(1분 안)에 flash 브랜치로 올린다
    return path


def due(now=None):
    """정리해야 할 날짜들: 다 끝난 가장 최근 하루와, 빠진 그 전 이틀(맥이 꺼져 있던 날)."""
    now = dt.datetime.fromtimestamp(now or time.time(), KST)
    last = (now - dt.timedelta(hours=9)).date() - dt.timedelta(days=1)
    return [last - dt.timedelta(days=k) for k in (2, 1, 0)]


def run(force=False, only=None, dry=False):
    days = [only] if only else due()
    if "--preview" in sys.argv:          # 끝나지 않은 오늘 하루를 지금까지 자료로 미리 정리(오전 9시에 최종본으로 바뀐다)
        days = [due()[-1] + dt.timedelta(days=1)]
        force = True
    for day in days:
        path = os.path.join(OUT, day.isoformat() + ".json")
        if os.path.exists(path) and not force:
            try:
                old = json.load(open(path))
            except (OSError, ValueError):
                old = {}
            if old.get("made", 0) >= old.get("end", 0):    # 하루가 끝난 뒤 만든 최종본이면 그대로 둔다(진행 중 미리보기는 다시 만든다)
                continue
        start, end = window(day)
        con = P.db()
        have, first = con.execute("""SELECT COUNT(*), MIN(m.t) FROM msgs m JOIN ai a ON a.ch=m.ch AND a.id=m.id
            WHERE m.t >= ? AND m.t < ? AND a.ko != ''""", (start, end)).fetchone()
        if (have < 150 or first is None or first > start + 3 * 3600) and not only and "--preview" not in sys.argv:   # 판정이 적거나 하루 앞부분이 빈 날은 건너뛴다
            log("자료 부족, 건너뜀", day, have)
            continue
        t = time.time()
        doc = make(day)
        if dry:
            print(json.dumps({k: doc[k] for k in ("headline", "review", "balance", "by_cat", "sectors", "market", "ai_dropped")}, ensure_ascii=False, indent=1))
            for it in doc["key"]:
                print(" 핵심", it["v"], it["ko"])
            for k, name in CATS:
                print(" [%s] %s" % (name, doc["sections"][k]["say"]))
                for it in doc["sections"][k]["items"] + doc["sections"][k].get("news", []):
                    print("    ", it.get("v", "기사"), it["ko"][:70])
            print(" 일정", [(e["title"], e["forecast"]) for e in doc["schedule"]])
        else:
            log("하루 정리", day, "→", save(doc), "%.0fs" % (time.time() - t), "빠진 AI 문장:", doc["ai_dropped"])


def install():
    for f in ("daily_brief.py", "tg_publish.py", "tg_judge.py", "tg_collect.py"):
        src = os.path.join(HERE, f)
        if os.path.abspath(src) != os.path.join(HOME, f):
            shutil.copy2(src, os.path.join(HOME, f))
    dst = os.path.join(HOME, "daily_brief.py")
    py = os.path.join(HOME, "tgvenv", "bin", "python")
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
    with open(plist, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{py}</string><string>{dst}</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>7</integer></dict>
  <key>StandardOutPath</key><string>{HOME}/daily.log</string>
  <key>StandardErrorPath</key><string>{HOME}/daily.log</string>
</dict></plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    for _ in range(10):
        if subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", plist], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    log("설치 완료:", plist, "(매일 09:07, 맥이 잠들어 있었으면 깨어날 때 실행)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--install" in a:
        install()
    else:
        only = dt.date.fromisoformat(a[a.index("--date") + 1]) if "--date" in a else None
        run(force="--force" in a, only=only, dry="--dry" in a)
