"""운영자 Mac에서 상시: 텔레그램 수집기(tg_collect.py)가 쌓은 글을 로컬 Gemma 4로 한국어 한 줄로 옮기고 호재·악재를 판정한다.

결과는 같은 DB(~/.signal/tg/tg.db)의 ai 표에 쌓는다. 원문은 그대로 두고, 사이트에 싣지 않는다.
판정 항목: 한국어 한 줄(ko), 종류(kind), 호재/악재/중립(verdict), 코인(coins), 섹터(sectors: 섹터 전체에 걸린 소식일 때만),
시장 전체(market_wide), 세기(strength 0~3).

설치: ~/.signal/tgvenv/bin/python tools/tg_judge.py --install   (launchd 상시 실행 com.signal.tgjudge, 로그 ~/.signal/tgjudge.log)
확인: ~/.signal/tgvenv/bin/python ~/.signal/tg_judge.py --tail 30
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~/.signal")
DB = os.path.join(HOME, "tg", "tg.db")
VENV_PY = os.path.join(HOME, "tgvenv", "bin", "python")
LABEL = "com.signal.tgjudge"
MODEL = os.environ.get("SIGNAL_TG_MODEL", "gemma4:26b")
OLLAMA = "http://localhost:11434"
V = 2                       # 프롬프트 버전. 바꾸면 새 글부터 새 버전으로 판정한다
WINDOW = 24 * 3600          # 이보다 오래된 글은 판정하지 않는다
IDLE = 5                    # 새 글이 없을 때 쉬는 시간(초)

KINDS = ["event", "data", "price_recap", "opinion", "promo", "notice", "unrelated"]
VERDICTS = ["호재", "악재", "중립"]
SECTORS = {
    "l1": "레이어1", "l2": "레이어2", "defi": "디파이", "ai": "AI", "meme": "밈", "rwa": "RWA·토큰화",
    "stable": "스테이블코인", "exchange": "거래소", "gamefi": "게임·NFT", "depin": "디핀", "privacy": "프라이버시",
    "infra": "인프라", "mining": "채굴", "prediction": "예측시장",
}
SYS = """너는 한국 크립토 투자자를 위한 속보 정리기다. 텔레그램 속보 한 건을 받아 JSON 한 개만 낸다. 설명 금지.

ko: 한국어 한 줄(최대 80자). 원문이 영어·중국어면 번역, 한국어면 다듬기. 핵심 사실만, 숫자·이름·티커는 그대로. 말투는 '~했다/~한다'. 홍보 문구·이모지·해시태그·출처 표기는 뺀다.
en: 같은 내용의 영어 한 줄(최대 120자). 뉴스 헤드라인 문체(현재형, 문장 끝 마침표 없이). 숫자·이름·티커는 그대로. 채널·매체 이름은 넣지 않는다.
  원문이 여러 소식을 묶은 브리핑이면 ko·en 모두 가장 중요한 소식 하나만 쓴다.
  속보 채널·매체 이름(코인니스, BlockBeats, Wu Blockchain, Watcher Guru, Lookonchain, Whale Alert, FinancialJuice 등)과 '~에 따르면'도 넣지 않는다.
kind:
  event = 가격을 움직일 수 있는 새 사실(상장·상장폐지, 해킹, 소송·제재, 규제·법안, 기관·정부 매수·매도, 대량 이동, ETF, 제휴·채택, 출시·업그레이드, 지정학 사건)
  data = 경제지표 발표(실제·예상치), 중앙은행 결정·발언
  price_recap = 가격·거래량·청산 정리, 차트·온체인 해설, 전망
  opinion = 인물 발언·칼럼·인터뷰(중앙은행 제외)
  promo = 이벤트·경품·에어드랍 안내·작은 프로젝트 홍보
  notice = 거래소의 일상 공지(점검, 입출금 일시 중단, 수수료·마진 조정)
  unrelated = 크립토·금융시장과 무관
verdict: 이 소식이 관련 코인(없으면 크립토 시장 전체) 가격에 일반적으로 어떻게 읽히는가.
  호재 예: 상장, 승인, 기관·정부 매수, 자금 유입, 제휴·채택, 규제 완화, 금리 인하 신호, 물가가 예상보다 낮음
  악재 예: 해킹·도난, 소송·제재·조사, 상장폐지·거래유의종목 지정·투자경고, 보유 코인 매도 계획, 코인의 대량 거래소 입금, 대량 언락,
    규제 강화, 금리 인상 신호, 물가가 예상보다 높음, 전쟁·공습 확대
  스테이블코인(USDT·USDC)이 거래소로 들어가는 건 매수 대기 자금이라 악재가 아니다(중립 또는 약한 호재).
  회담·논의·발언만 있고 결정이 없으면 중립. 어느 쪽도 아니거나 unrelated·promo·notice면 중립
coins: 소식이 직접 다루는 코인 티커(최대 3개, 대문자). 비트코인은 BTC. 회사·주식 티커는 넣지 않는다.
  개인 피해·강도·사기 사건에 쓰인 체인, 이벤트 상품으로 나열된 코인은 넣지 않는다. 없으면 []
sectors: 소식의 호재·악재가 '섹터 전체'에 걸릴 때만, 아래 키 중 최대 2개. 대부분의 소식은 []다.
  코인 하나·프로젝트 하나·회사 하나·거래소 하나의 소식이면 그 코인이 어느 섹터에 속하든 무조건 [] (그건 coins로 충분하다).
  섹터를 붙이는 경우: 여러 코인에 함께 적용되는 규제·정책·승인(예: 밈코인 ETF 승인, 프라이버시 코인 일괄 상장폐지),
  업종 전체의 큰 사건(예: 엔비디아 실적 → AI 토큰들, 스테이블코인 법안 통과 → 스테이블코인)
  l1 레이어1 | l2 레이어2 | defi 디파이(DEX·대출·무기한 선물 DEX) | ai AI 토큰(엔비디아·오픈AI 등 AI 산업 큰 소식 포함) | meme 밈코인
  rwa 실물자산 토큰화·토큰화 주식 | stable 스테이블코인 | exchange 거래소·거래소 토큰 | gamefi 게임·NFT | depin 디핀
  privacy 프라이버시 코인 | infra 오라클·브릿지·지갑·보안 | mining 비트코인 채굴 | prediction 예측시장
  예: '미 SEC, 디파이 규제 완화 지침' → ["defi"], '엔비디아 실적 예상 상회' → ["ai"], '한국, 스테이블코인 발행 법안 통과' → ["stable"]
  아님: '하이퍼리퀴드 HYPE 매입' → [], '고래가 UNI 매수' → [], 'JUP 보상 지급' → [], '거래소 하나 출금 지연' → [], '거래소가 AI 기능 출시' → []
market_wide: 크립토 시장 전체를 움직일 소식(미국 연준·물가·고용, 미국 정부·의회의 업계 전반 조치, 최대 거래소 사고, 큰 지정학 사건)이면 true
strength: 0=영향 없음 1=작음 2=눈에 띔(수억 달러, 주요 규제기관·대기업) 3=큼(ETF 승인·거절, 대형 해킹, 미국 정부의 큰 조치, 수십억 달러, 전쟁 확대)

형식: {"ko": "", "en": "", "kind": "", "verdict": "", "coins": [], "sectors": [], "market_wide": false, "strength": 0}"""

TICKER = re.compile(r"^[A-Z0-9]{2,10}$")
HAN = re.compile(r"[\u4e00-\u9fff]")
STOCKISH = {"NVDA", "TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "COIN", "MSTR", "HOOD", "CRCL", "USD", "KRW", "EUR", "JPY", "CNY",
            "AI", "ETF", "CPI", "PPI", "GDP", "FED", "FOMC", "SEC", "CFTC", "US", "USA", "EU", "UK", "IPO", "CEO", "DEFI", "NFT", "RWA", "DEX", "CEX"}


def log(*a):
    print(time.strftime("%m-%d %H:%M:%S"), *a, flush=True)


def db():
    con = sqlite3.connect(DB, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS ai(
        ch TEXT, id INTEGER, ko TEXT, kind TEXT, verdict TEXT, coins TEXT, sectors TEXT,
        market_wide INTEGER, strength INTEGER, model TEXT, v INTEGER, at INTEGER, ms INTEGER, PRIMARY KEY(ch, id))""")
    if "en" not in [r[1] for r in con.execute("PRAGMA table_info(ai)")]:
        con.execute("ALTER TABLE ai ADD COLUMN en TEXT")      # 영어 한 줄(사이트 영어 화면)
    return con


def clean_text(text):
    """링크·해시태그 꼬리·연속 공백을 걷어 모델에 줄 본문만 남긴다."""
    t = re.sub(r"https?://\S+", "", text or "")
    t = re.sub(r"(?m)^\s*(#\S+\s*)+$", "", t)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{2,}", "\n", t)).strip()[:1500]


def normalize(j):
    """모델 출력 → 저장 형식. 틀린 값은 버리거나 안전한 쪽으로 고친다. 고칠 수 없으면 None."""
    if not isinstance(j, dict) or j.get("kind") not in KINDS or not str(j.get("ko") or "").strip():
        return None
    kind = j["kind"]
    quiet = kind in ("unrelated", "promo", "notice")
    verdict = j.get("verdict") if j.get("verdict") in VERDICTS and not quiet else "중립"
    coins = []
    for c in j.get("coins") or []:
        c = str(c).strip().upper().lstrip("$")
        if TICKER.match(c) and c not in STOCKISH and c not in coins:
            coins.append(c)
    sectors = [s for s in dict.fromkeys(j.get("sectors") or []) if s in SECTORS][:2]
    if kind not in ("event", "data", "opinion"):     # 시세 해설·홍보·공지에는 섹터를 붙이지 않는다
        sectors = []
    try:
        st = max(0, min(3, int(j.get("strength") or 0)))
    except (TypeError, ValueError):
        st = 0
    if quiet:
        st = 0
    return {"ko": " ".join(str(j["ko"]).split())[:120], "en": " ".join(str(j.get("en") or "").split())[:180], "kind": kind, "verdict": verdict, "coins": coins[:3],
            "sectors": [] if verdict == "중립" else sectors, "market_wide": bool(j.get("market_wide")) and not quiet and st >= 2, "strength": st}


def ask(ch, lang, text):
    body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "30m",
            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 450},
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": f"채널: {ch} ({lang})\n원문:\n{text}"}]}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.loads(r.read())["message"]["content"]
    return json.loads(out[out.index("{"): out.rindex("}") + 1])


def langs():
    sys.path.insert(0, HOME)
    try:
        import tg_collect
        return {n: l for n, _, l in tg_collect.CHANNELS}
    except ImportError:
        return {}


def todo(con, k=20):
    """아직 판정 안 한 최근 글, 새 글부터."""
    return con.execute("""SELECT m.ch, m.id, m.text FROM msgs m LEFT JOIN ai a ON a.ch=m.ch AND a.id=m.id
        WHERE a.id IS NULL AND m.t >= ? ORDER BY m.t DESC LIMIT ?""", (int(time.time()) - WINDOW, k)).fetchall()


def judge_one(con, lang, ch, mid, text):
    body = clean_text(text)
    t0 = time.time()
    if len(body) < 8:
        r = {"ko": "", "en": "", "kind": "unrelated", "verdict": "중립", "coins": [], "sectors": [], "market_wide": False, "strength": 0}
    else:
        r = normalize(ask(ch, lang.get(ch, "?"), body))
        if r and HAN.search(r["ko"]):          # 중국어 원문의 한자가 남으면 한 번 더
            r = normalize(ask(ch, lang.get(ch, "?"), body + "\n\n(주의: ko에 한자·중국어를 남기지 말고 전부 한국어로 옮겨라)")) or r
        if r is None:
            r = {"ko": "", "en": "", "kind": "unrelated", "verdict": "중립", "coins": [], "sectors": [], "market_wide": False, "strength": 0}
            log("판정 형식 오류", ch, mid)
    con.execute("INSERT OR REPLACE INTO ai(ch, id, ko, kind, verdict, coins, sectors, market_wide, strength, model, v, at, ms, en) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ch, mid, r["ko"], r["kind"], r["verdict"], json.dumps(r["coins"]), json.dumps(r["sectors"]),
                 int(r["market_wide"]), r["strength"], MODEL, V, int(time.time()), int((time.time() - t0) * 1000), r.get("en", "")))
    con.commit()
    return r


EN_SYS = """For each numbered item you get a Korean market-news line and the original post. Write one English news headline per item (present tense, no final period, max 120 characters).
Take names, numbers and tickers from the original post when it is in English (exact spelling). Do not add facts. No channel or outlet names. Output JSON only: {"en": ["...", ...]} in the same order."""


def fill_en(con, k=8):
    """영어 줄이 없는 최근(48시간) 판정 → 한국어 줄을 영어로 옮겨 채운다. 채운 게 있으면 True."""
    rows = con.execute("""SELECT a.ch, a.id, a.ko, m.text FROM ai a JOIN msgs m ON m.ch=a.ch AND m.id=a.id
        WHERE a.ko != '' AND (a.en IS NULL OR a.en = '') AND m.t >= ? ORDER BY m.t DESC LIMIT ?""", (int(time.time()) - 2 * WINDOW, k)).fetchall()
    if not rows:
        return False
    body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "30m", "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 1200},
            "messages": [{"role": "system", "content": EN_SYS}, {"role": "user", "content": "\n\n".join(f"{i + 1}. ko: {r[2]}\n   original: {clean_text(r[3])[:300]}" for i, r in enumerate(rows))}]}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.loads(r.read())["message"]["content"]
    en = json.loads(out[out.index("{"): out.rindex("}") + 1]).get("en") or []
    if len(en) != len(rows):
        log("영어 채우기 개수 불일치", len(en), len(rows))
        return False
    for (ch, mid, _, _), e in zip(rows, en):
        con.execute("UPDATE ai SET en=? WHERE ch=? AND id=?", (" ".join(str(e).split())[:180], ch, mid))
    con.commit()
    return True


def run():
    con = db()
    lang = langs()
    log("판정 시작:", MODEL)
    done, last = 0, time.time()
    while True:
        rows = todo(con)
        if not rows:
            try:
                if not fill_en(con):          # 할 일이 없을 때 영어 줄이 빠진 최근 판정을 채운다
                    time.sleep(IDLE)
            except Exception as e:
                log("영어 채우기 실패", type(e).__name__, str(e)[:120])
                time.sleep(IDLE)
        for ch, mid, text in rows:
            try:
                judge_one(con, lang, ch, mid, text)
                done += 1
            except Exception as e:
                log("판정 실패", ch, mid, type(e).__name__, str(e)[:120])
                time.sleep(30 if "refused" in str(e) or "timed out" in str(e) else 2)
                break
        if time.time() - last >= 3600:
            log("지난 1시간 판정", done)
            done, last = 0, time.time()


def install():
    dst = os.path.join(HOME, "tg_judge.py")
    if os.path.abspath(__file__) != dst:
        shutil.copy2(os.path.abspath(__file__), dst)
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
    with open(plist, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{VENV_PY}</string><string>{dst}</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>{HOME}/tgjudge.log</string>
  <key>StandardErrorPath</key><string>{HOME}/tgjudge.log</string>
</dict></plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    for _ in range(10):
        if subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", plist], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    log("설치 완료:", plist)


def tail(k):
    con = db()
    rows = con.execute("""SELECT m.t, m.ch, a.verdict, a.kind, a.coins, a.sectors, a.market_wide, a.strength, a.ko
        FROM msgs m JOIN ai a ON a.ch=m.ch AND a.id=m.id ORDER BY m.t DESC LIMIT ?""", (k,)).fetchall()
    for t, ch, vd, kind, coins, sectors, mw, st, ko in reversed(rows):
        tags = json.loads(coins) + [SECTORS[s] + " 섹터" for s in json.loads(sectors)] + (["시장 전체"] if mw else [])
        print(time.strftime("%m-%d %H:%M", time.localtime(t)), f"[{ch[:14]}]", vd, "★" * st, kind, ("(" + ", ".join(tags) + ")") if tags else "", "·", ko)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--install" in a:
        install()
    elif "--tail" in a:
        i = a.index("--tail")
        tail(int(a[i + 1]) if len(a) > i + 1 and a[i + 1].isdigit() else 30)
    else:
        run()
