"""운영자 Mac에서 15분마다: 사이트에 올라온 새 기사를 로컬 모델(Ollama의 Gemma 4)로 판정해 `llm` 브랜치에 올린다.

파이프라인(pipeline/judge.py)이 다음 실행 때 그 파일을 읽어 기사에 붙인다. Mac이 꺼져 있으면 사이트는 키워드 규칙으로 돌아간다.
프롬프트는 과거 기사 1천 건에 정답을 달아 검증한 v2(제목만 봄)에 TON만 더한 것이다.

설치: python3 tools/judge_live.py --install   (~/.signal 로 복사하고 launchd에 15분 간격으로 등록)
수동 실행: python3 ~/.signal/judge_live.py
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

SITE = os.environ.get("SIGNAL_SITE", "https://mash1384.github.io/signal-desk/")
REPO = "https://github.com/mash1384/signal-desk.git"
MODEL = os.environ.get("SIGNAL_JUDGE_MODEL", "gemma4:26b")
OLLAMA = "http://localhost:11434"
HOME = os.path.expanduser("~/.signal")
CACHE = os.path.join(HOME, "judgments.json")
BRANCH_DIR = os.path.join(HOME, "llm-branch")
LOCK = os.path.join(HOME, "judge.lock")
LABEL = "com.signal.judge"
KEEP = 4 * 86400          # 이보다 오래된 기사는 판정하지 않는다
PER_RUN = int(os.environ.get("SIGNAL_JUDGE_PER_RUN", 120))   # 한 번에 판정할 최대 건수(밀리면 다음 실행에서 이어서)

COINS = "BTC ETH SOL XRP BNB DOGE ADA LINK AVAX SUI TON DOT LTC TRX HBAR TAO AAVE UNI NEAR APT ONDO ENA PEPE ZEC FET".split()
KINDS = ["event", "price_recap", "opinion", "promo", "unrelated"]
TYPES = ["listing", "hack", "etf", "legal", "regulation", "treasury", "flow", "partnership", "development", "macro", "other"]
SYS = """너는 한국 크립토 트레이더를 위한 뉴스 신호 분류기다. 기사 제목만 보고 JSON 한 개만 출력한다. 설명 금지.

coins: 기사가 '직접 다루는' 코인. 아래 목록에 있고 제목에 그 코인 이름이나 티커가 직접 나올 때만(최대 3개). 비트코인 보유·이동·ETF·채굴이면 BTC.
  지나가듯 나온 코인, 목록에 없는 토큰은 넣지 않는다. 거래소·회사 기사에 그 회사 토큰(BNB 등)을 넣지 않는다.
목록: """ + " ".join(COINS) + """
market_wide: 특정 코인이 아니라 코인 시장 전체를 움직일 사건(미국 연준·물가·고용 발표, 미국 정부·의회·규제기관의 업계 전반 조치, 최대 거래소의 큰 사고)이면 true. 다른 나라 규제, 개별 회사 소식은 false
kind:
  event = 가격을 움직일 수 있는 새 사실(상장, 승인·거절, 해킹, 소송·판결, 규제·법안, 기관·기업 매수, 대량 이동, 제휴·채택, 업그레이드·출시)
  price_recap = 가격·거래량·지표 정리, 전망·예측, 차트·온체인 분석, 고래 동향 해설, 자금 흐름 통계
  opinion = 인물 발언, 칼럼, 해설, 인터뷰
  promo = 광고·보도자료: 프리세일, 이벤트·경품, 작은 프로젝트의 출시·펀딩·제휴, 목록에 없는 토큰의 거래소 상장
  unrelated = 코인과 무관
type: kind가 event일 때만 하나. listing(상장·상장폐지·거래쌍 추가) hack(해킹·익스플로잇·도난) etf(ETF 신청·승인·연기·보유) legal(소송·판결·기소·조사·제재)
  regulation(법안·규제·정부 정책) treasury(기업·정부의 매수·보유) flow(대량 이동·매도·압류·언락) partnership(제휴·채택·결제 도입) development(업그레이드·메인넷·제품 출시)
  macro(미국 거시 지표·금리) other. event가 아니면 ""
direction: coins(없으면 시장 전체) 가격에 일반적으로 어떻게 읽히는가. bearish 예: 해킹·도난, 소송·제재·조사, 대량 물량 거래소 이동·매도, 규제 강화, 상장 폐지, 승인 연기. bullish 예: 승인·상장, 기관 매수·자금 유입, 파트너십·채택, 규제 완화. 둘 다 아니면 neutral
strength: 사건이라면 예상 영향 크기. 1=작음(소액, 지역 이슈, 일상적 발표) 2=눈에 띔(수억 달러 규모, 주요 규제기관·대기업) 3=큼(ETF 승인·거절, 대형 거래소 해킹, 미국 정부의 큰 조치, 수십억 달러). 사건이 아니면 0

형식: {"coins": [], "market_wide": false, "kind": "", "type": "", "direction": "", "strength": 0}"""


def log(*a):
    print(time.strftime("%m-%d %H:%M:%S"), *a, flush=True)


def get_json(url, data=None, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json", "User-Agent": "signal-judge/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ask(title):
    body = {"model": MODEL, "stream": False, "think": False, "keep_alive": "10m",
            "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 100},
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": "제목: " + title}]}
    txt = get_json(OLLAMA + "/api/chat", body, timeout=300)["message"]["content"]
    j = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
    kind = j.get("kind") if j.get("kind") in KINDS else "unrelated"
    ev = kind == "event"
    try:
        st = max(0, min(3, int(j.get("strength") or 0)))
    except (TypeError, ValueError):
        st = 0
    return {"kind": kind, "coins": [c for c in j.get("coins") or [] if c in COINS][:3] if ev else [],
            "market_wide": bool(j.get("market_wide")) and ev, "type": (j.get("type") if j.get("type") in TYPES else "other") if ev else "",
            "direction": j.get("direction") if ev and j.get("direction") in ("bullish", "bearish", "neutral") else "neutral",
            "strength": st if ev else 0, "model": MODEL}


def git(*args, cwd=BRANCH_DIR):
    env = dict(os.environ, PATH="/usr/bin:/bin:/usr/sbin:/sbin:" + os.path.expanduser("~/.local/bin") + ":/opt/homebrew/bin")
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout


def publish(doc):
    """llm 브랜치에 커밋 하나만 두고 고쳐 쓴다(이력을 쌓지 않는다)."""
    if not os.path.isdir(os.path.join(BRANCH_DIR, ".git")):
        os.makedirs(BRANCH_DIR, exist_ok=True)
        git("init", "-q")
        git("remote", "add", "origin", REPO)
        git("checkout", "-q", "-b", "llm")
        git("config", "user.name", "signal-judge")
        git("config", "user.email", "signal-judge@users.noreply.github.com")
    with open(os.path.join(BRANCH_DIR, "judgments.json"), "w") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(BRANCH_DIR, "README.md"), "w") as f:
        f.write("운영자 Mac의 로컬 모델이 만든 기사 판정(tools/judge_live.py). 파이프라인이 읽는다. 사람이 고치지 않는다.\n")
    git("add", "-A")
    has_head = subprocess.run(["git", "rev-parse", "-q", "--verify", "HEAD"], cwd=BRANCH_DIR, capture_output=True).returncode == 0
    git("commit", "-q", *(["--amend"] if has_head else []), "-m", "judgments")
    git("push", "-q", "-f", "origin", "HEAD:llm")


def run():
    os.makedirs(HOME, exist_ok=True)
    # 이전 실행이 살아 있으면 건너뛴다(밀린 기사를 오래 판정하는 중일 수 있다)
    try:
        pid = int(open(LOCK).read().strip())
        if pid <= 0:
            raise ValueError
        os.kill(pid, 0)
        log("이전 실행이 아직 도는 중", pid)
        return
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        pass
    with open(LOCK, "w") as f:
        f.write(str(os.getpid()))
    try:
        cache = {}
        if os.path.exists(CACHE):
            cache = json.load(open(CACHE)).get("j", {})
        now = time.time()
        arts = get_json(SITE + "data/articles.json?t=%d" % now)
        live = {a["id"] for a in arts}
        todo = [a for a in arts if a["id"] not in cache and now - a.get("t0", 0) <= KEEP and a.get("source") not in ("upbit-notice", "calendar")]
        todo.sort(key=lambda a: -a.get("t0", 0))
        done = 0
        for a in todo[:PER_RUN]:
            try:
                cache[a["id"]] = ask(a.get("title_orig") or a["title"])
                done += 1
            except Exception as e:
                log("판정 실패", a["id"], str(e)[:120])
                if "Connection refused" in str(e):
                    break
        cache = {k: v for k, v in cache.items() if k in live}
        doc = {"v": 2, "model": MODEL, "at": int(now), "j": cache}
        json.dump(doc, open(CACHE, "w"), ensure_ascii=False)
        if done or not os.path.isdir(os.path.join(BRANCH_DIR, ".git")):
            publish(doc)
        log("판정", done, "남음", max(0, len(todo) - PER_RUN), "보관", len(cache), "%.0fs" % (time.time() - now))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


def install():
    os.makedirs(HOME, exist_ok=True)
    dst = os.path.join(HOME, "judge_live.py")
    shutil.copy2(os.path.abspath(__file__), dst)
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)
    # 파이프라인(02·17·32·47분 시작, 4~5분 걸림)이 올린 기사를 바로 판정해 다음 실행에 쓰이도록 09·24·39·54분
    times = "".join("<dict><key>Minute</key><integer>%d</integer></dict>" % m for m in (9, 24, 39, 54))
    with open(plist, "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>{dst}</string></array>
  <key>StartCalendarInterval</key><array>{times}</array>
  <key>StandardOutPath</key><string>{HOME}/judge.log</string>
  <key>StandardErrorPath</key><string>{HOME}/judge.log</string>
</dict></plist>
""")
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", plist], check=True)
    log("설치 완료:", dst, plist)


if __name__ == "__main__":
    if "--install" in sys.argv:
        install()
    else:
        run()
